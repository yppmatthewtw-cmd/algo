# -*- coding: utf-8 -*-
"""
webull_live_trader.py — Webull OpenAPI 實盤執行器 (與回測引擎共用同一套訊號; 標的讀 ../config.json)
流程: 每 5 秒拉最近 400 根 1分K → 只用已完成K線判定 → 有訊號即市價下單 → 收市前強平
※ config trading.webull_dry_run=true 時只印訊號不下單 (建議先觀察數日)。
※ 下單依 webull-python-sdk-trade 文件 (api.order.place_order_v2); 參數名請對照你的 SDK 版本。
用法:
  python webull_live_trader.py                    # config 標的, dry-run
  python webull_live_trader.py --live --qty 2000  # 真下單
"""
import argparse, os, sys, time, json, datetime as dt, uuid
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from macd_momentum_core import compute_signals
from config_loader import CFG, params_from_config, describe
from webull_fetch_and_backtest import fetch_1min

def main():
    S, T = CFG['symbol'], CFG['trading']
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbol', default=S['webull_symbol']); ap.add_argument('--category', default=S['webull_category']); ap.add_argument('--region', default=S['webull_region'])
    ap.add_argument('--qty', type=int, default=T['qty']); ap.add_argument('--account-id', default=os.environ.get('WEBULL_ACCOUNT_ID'))
    ap.add_argument('--app-key', default=os.environ.get('WEBULL_APP_KEY')); ap.add_argument('--app-secret', default=os.environ.get('WEBULL_APP_SECRET'))
    ap.add_argument('--live', action='store_true', help='真下單 (預設依 config webull_dry_run)')
    ap.add_argument('--min-bars', type=int); ap.add_argument('--min-area', type=float); ap.add_argument('--min-depth', type=float)
    a = ap.parse_args()
    dry = not a.live and T.get('webull_dry_run', True)
    hk = a.category.startswith('HK')
    cfg = json.loads(json.dumps(CFG)); cfg['symbol']['market'] = 'HK' if hk else 'US'
    p = params_from_config(cfg, {'min_bars': a.min_bars, 'min_area_pct': a.min_area, 'min_depth_pct': a.min_depth})
    eod_t = dt.datetime.strptime(p.eod_flat, '%H:%M').time()
    api = None
    if not dry:
        from webullsdkcore.client import ApiClient
        from webullsdktrade.api import API
        api = API(ApiClient(a.app_key, a.app_secret, a.region))
    def order(side):
        if dry: print(dt.datetime.now(), '[DRY-RUN] ORDER', side, a.qty, a.symbol); return True
        res = api.order.place_order_v2(a.account_id, {'client_order_id': uuid.uuid4().hex, 'side': side, 'tif': 'DAY', 'extended_hours_trading': False,
                                                      'instrument_type': 'EQUITY', 'symbol': a.symbol, 'market': 'HK' if hk else 'US', 'order_type': 'MARKET', 'quantity': str(a.qty)})
        print(dt.datetime.now(), 'ORDER', side, res.status_code, res.text[:200]); return res.status_code == 200
    print(f'{a.symbol} {a.category} | {describe(cfg)} | qty {a.qty} | dry_run={dry} | 參數 {json.dumps(p.to_dict(), ensure_ascii=False)}')
    pos = 0; last_bar = None
    while True:
        try: k = fetch_1min(a.symbol, a.category, 400, a.app_key, a.app_secret, a.region)
        except Exception as e: print('抓K失敗', e); time.sleep(10); continue
        done = k.set_index('datetime').iloc[:-1]
        if last_bar == done.index[-1]: time.sleep(5); continue
        last_bar = done.index[-1]
        row = compute_signals(done, p).iloc[-1]
        eod = dt.datetime.now().time() >= eod_t
        if pos == 1 and (eod or row['sell_sig']):
            if order('SELL'): pos = 0; print(f'  ← SELL @{row["close"]:.3f} reason={"EOD" if eod else "MACD_SELL"}')
        elif pos == 0 and row['buy_sig'] and row['entry_ok'] and not eod:
            if order('BUY'): pos = 1; print(f'  → BUY @{row["close"]:.3f} 前段 bars={int(row["prev_bars"])} area={row["prev_area"]:.3f} depth={row["prev_depth"]:.3f}')
        else:
            print(dt.datetime.now().strftime('%H:%M:%S'), f'bar {last_bar.time()} close={row["close"]:.3f} hist={row["hist"]:+.4f} 段={int(row["run_sign"])}x{int(row["run_bars"])} pos={pos}')
        time.sleep(5)

if __name__ == '__main__':
    main()
