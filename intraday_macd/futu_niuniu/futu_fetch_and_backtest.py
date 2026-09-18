# -*- coding: utf-8 -*-
"""
futu_fetch_and_backtest.py — 富途牛牛 (Futu OpenAPI / OpenD) 版: 抓 1 分鐘 K → 回測
標的/日期/參數預設讀 ../config.json (預設 HK.07709); 命令列可臨時覆寫。
前置:
  1. 安裝並登入 OpenD (牛牛 → 量化 → OpenD), 預設 127.0.0.1:11111
  2. pip install futu-api pandas numpy
  3. 港股歷史 1 分 K 需港股行情權限; 歷史 K 有每月額度
用法:
  python futu_fetch_and_backtest.py                       # 用 config 的標的與日期
  python futu_fetch_and_backtest.py --code HK.00700 --start 2026-09-01 --end 2026-09-18 --sweep
  python futu_fetch_and_backtest.py --csv ../data/HK_07709_1min.csv   # 已抓好的CSV
"""
import argparse, os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pandas as pd
from macd_momentum_core import backtest, sweep, load_csv
from config_loader import CFG, params_from_config, describe

def fetch_1min(code: str, start: str, end: str, host: str, port: int) -> pd.DataFrame:
    from futu import OpenQuoteContext, KLType, AuType, RET_OK
    ctx = OpenQuoteContext(host=host, port=port)
    frames = []; page_key = None
    try:
        while True:
            ret, data, page_key = ctx.request_history_kline(code, start=start, end=end, ktype=KLType.K_1M,
                                                            autype=AuType.QFQ, max_count=1000, page_req_key=page_key)
            if ret != RET_OK: raise RuntimeError(f'request_history_kline 失敗: {data}')
            frames.append(data)
            if page_key is None: break
    finally:
        ctx.close()
    df = pd.concat(frames, ignore_index=True)
    return df.rename(columns={'time_key': 'datetime'})[['datetime', 'open', 'high', 'low', 'close', 'volume']]

def main():
    S, B, T = CFG['symbol'], CFG['backtest'], CFG['trading']
    ap = argparse.ArgumentParser()
    ap.add_argument('--code', default=S['futu_code']); ap.add_argument('--market', default=S['market'], choices=['HK', 'US'])
    ap.add_argument('--start', default=B['start']); ap.add_argument('--end', default=B['end'])
    ap.add_argument('--host', default=T['futu_host']); ap.add_argument('--port', type=int, default=T['futu_port'])
    ap.add_argument('--min-bars', type=int); ap.add_argument('--min-area', type=float); ap.add_argument('--min-depth', type=float)
    ap.add_argument('--sweep', action='store_true'); ap.add_argument('--csv')
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(here, '..', B['data_dir']); out_dir = os.path.join(here, '..', B['out_dir'])
    os.makedirs(data_dir, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
    tag = a.code.replace('.', '_')
    csv = a.csv or os.path.join(data_dir, f'{tag}_1min.csv')
    if not a.csv:
        df = fetch_1min(a.code, a.start, a.end, a.host, a.port); df.to_csv(csv, index=False); print(f'抓取 {len(df)} 根 1分K → {csv}')
    cfg = json.loads(json.dumps(CFG)); cfg['symbol']['market'] = 'US' if a.code.startswith('US.') else a.market
    p = params_from_config(cfg, {'min_bars': a.min_bars, 'min_area_pct': a.min_area, 'min_depth_pct': a.min_depth})
    df = load_csv(csv)
    print('標的:', a.code, '|', describe(cfg)); print('參數:', json.dumps(p.to_dict(), ensure_ascii=False))
    d, tr, st = backtest(df, p)
    print('回測:', json.dumps(st, ensure_ascii=False, indent=1, default=str))
    d.to_csv(os.path.join(out_dir, f'{tag}_signals.csv')); tr.to_csv(os.path.join(out_dir, f'{tag}_trades.csv'), index=False)
    if a.sweep:
        res = sweep(df, p, B['sweep_grid']); print(res.head(15).to_string(index=False)); res.to_csv(os.path.join(out_dir, f'{tag}_sweep.csv'), index=False)

if __name__ == '__main__':
    main()
