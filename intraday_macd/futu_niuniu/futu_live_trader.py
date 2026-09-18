# -*- coding: utf-8 -*-
"""
futu_live_trader.py — 富途牛牛 OpenAPI 模擬盤/實盤執行器 (與回測引擎共用同一套訊號; 標的讀 ../config.json)
流程: 訂閱 1 分 K → 每根 K 完成時重算 MACD 動能訊號 → 有訊號即市價下單 → 收市前強平
安全預設: config trading.futu_trd_env = SIMULATE (模擬盤)。改 REAL 前請先在模擬盤跑數日。
用法:
  python futu_live_trader.py                          # config 標的, 模擬盤
  python futu_live_trader.py --code HK.00700 --qty 100
  python futu_live_trader.py --real --pwd 你的交易密碼   # 實盤
"""
import argparse, os, sys, time, json, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pandas as pd
from macd_momentum_core import compute_signals
from config_loader import CFG, params_from_config, describe

def main():
    S, T = CFG['symbol'], CFG['trading']
    ap = argparse.ArgumentParser()
    ap.add_argument('--code', default=S['futu_code']); ap.add_argument('--qty', type=int, default=T['qty'])
    ap.add_argument('--host', default=T['futu_host']); ap.add_argument('--port', type=int, default=T['futu_port'])
    ap.add_argument('--real', action='store_true', default=(T.get('futu_trd_env') == 'REAL')); ap.add_argument('--pwd', default=None)
    ap.add_argument('--min-bars', type=int); ap.add_argument('--min-area', type=float); ap.add_argument('--min-depth', type=float)
    a = ap.parse_args()
    from futu import (OpenQuoteContext, OpenSecTradeContext, TrdMarket, TrdEnv, TrdSide, OrderType, KLType, SubType, RET_OK, SecurityFirm)
    cfg = json.loads(json.dumps(CFG)); cfg['symbol']['market'] = 'US' if a.code.startswith('US.') else 'HK'
    p = params_from_config(cfg, {'min_bars': a.min_bars, 'min_area_pct': a.min_area, 'min_depth_pct': a.min_depth})
    eod_t = dt.datetime.strptime(p.eod_flat, '%H:%M').time()
    market = TrdMarket.US if a.code.startswith('US.') else TrdMarket.HK
    env = TrdEnv.REAL if a.real else TrdEnv.SIMULATE
    q = OpenQuoteContext(host=a.host, port=a.port)
    t = OpenSecTradeContext(filter_trdmarket=market, host=a.host, port=a.port, security_firm=SecurityFirm.FUTUSECURITIES)
    if a.real:
        ret, msg = t.unlock_trade(a.pwd); assert ret == RET_OK, msg
    ret, r = q.subscribe([a.code], [SubType.K_1M]); assert ret == RET_OK, r
    print(f'[{env}] {a.code} | {describe(cfg)} | qty {a.qty} | 參數 {json.dumps(p.to_dict(), ensure_ascii=False)}')
    pos = 0; last_bar = None
    def order(side):
        ret, r = t.place_order(price=0, qty=a.qty, code=a.code, trd_side=side, order_type=OrderType.MARKET, trd_env=env)
        print(dt.datetime.now(), 'ORDER', side, ret, r if ret != RET_OK else r[['order_id', 'order_status']].to_dict('records'))
        return ret == RET_OK
    while True:
        ret, k = q.get_cur_kline(a.code, num=400, ktype=KLType.K_1M)
        if ret != RET_OK: print('get_cur_kline 失敗', k); time.sleep(5); continue
        k = k.rename(columns={'time_key': 'datetime'}); k['datetime'] = pd.to_datetime(k['datetime'])
        done = k.set_index('datetime')[['open', 'high', 'low', 'close', 'volume']].iloc[:-1]  # 最後一根進行中, 只用已完成K
        if last_bar == done.index[-1]: time.sleep(2); continue
        last_bar = done.index[-1]
        row = compute_signals(done, p).iloc[-1]
        eod = dt.datetime.now().time() >= eod_t
        if pos == 1 and (eod or row['sell_sig']):
            if order(TrdSide.SELL): pos = 0; print(f'  ← SELL @{row["close"]:.3f} reason={"EOD" if eod else "MACD_SELL"} 前段 bars={int(row["prev_bars"])} area={row["prev_area"]:.3f} depth={row["prev_depth"]:.3f}')
        elif pos == 0 and row['buy_sig'] and row['entry_ok'] and not eod:
            if order(TrdSide.BUY): pos = 1; print(f'  → BUY  @{row["close"]:.3f} 前段 bars={int(row["prev_bars"])} area={row["prev_area"]:.3f} depth={row["prev_depth"]:.3f}')
        else:
            print(dt.datetime.now().strftime('%H:%M:%S'), f'bar {last_bar.time()} close={row["close"]:.3f} hist={row["hist"]:+.4f} 段={int(row["run_sign"])}x{int(row["run_bars"])} area={row["run_area"]:.3f} depth={row["run_depth"]:.3f} pos={pos}')
        time.sleep(2)

if __name__ == '__main__':
    main()
