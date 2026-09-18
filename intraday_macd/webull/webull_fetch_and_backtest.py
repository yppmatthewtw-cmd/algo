# -*- coding: utf-8 -*-
"""
webull_fetch_and_backtest.py — Webull OpenAPI 版: 抓 1 分鐘 K → 回測 (標的/參數讀 ../config.json, 預設 07709 HK_STOCK)
前置:
  1. Webull App → OpenAPI 申請 App Key / App Secret; 設環境變數 WEBULL_APP_KEY / WEBULL_APP_SECRET
  2. pip install webull-python-sdk-core webull-python-sdk-quotes webull-python-sdk-mdata webull-python-sdk-trade pandas numpy
  3. 歷史 K 線單次 count 有上限 (依文件約 800-1200), 多日需分段抓後合併
※ Webull App 本身無 Pine 式策略回測器; 「Webull 版」= OpenAPI 抓數據 + 本引擎回測 + OpenAPI 下單。
※ SDK 方法簽名依 webull-python-sdk 官方文件撰寫; 版本若有差異請對照修改 fetch_1min()。
用法:
  python webull_fetch_and_backtest.py                       # config 標的
  python webull_fetch_and_backtest.py --symbol 00700 --category HK_STOCK --sweep
  python webull_fetch_and_backtest.py --csv ../data/07709_1min.csv
"""
import argparse, os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pandas as pd
from macd_momentum_core import backtest, sweep, load_csv
from config_loader import CFG, params_from_config, describe

def fetch_1min(symbol: str, category: str, count: int, app_key: str, app_secret: str, region: str) -> pd.DataFrame:
    from webullsdkcore.client import ApiClient
    from webullsdkmdata.quotes.market_data import MarketData
    from webullsdkmdata.common.category import Category
    from webullsdkmdata.common.timespan import Timespan
    md = MarketData(ApiClient(app_key, app_secret, region))
    res = md.get_history_bar(symbol, getattr(Category, category).name, Timespan.M1.name, count=str(count))
    if res.status_code != 200: raise RuntimeError(f'get_history_bar 失敗: {res.status_code} {res.text}')
    js = res.json(); bars = js[0]['bars'] if isinstance(js, list) else js['bars']
    df = pd.DataFrame(bars).rename(columns={'time': 'datetime'})
    df['datetime'] = pd.to_datetime(df['datetime'])
    for c in ('open', 'high', 'low', 'close', 'volume'): df[c] = pd.to_numeric(df[c])
    return df[['datetime', 'open', 'high', 'low', 'close', 'volume']].sort_values('datetime')

def main():
    S, B = CFG['symbol'], CFG['backtest']
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbol', default=S['webull_symbol']); ap.add_argument('--category', default=S['webull_category']); ap.add_argument('--region', default=S['webull_region'])
    ap.add_argument('--count', type=int, default=1200)
    ap.add_argument('--app-key', default=os.environ.get('WEBULL_APP_KEY')); ap.add_argument('--app-secret', default=os.environ.get('WEBULL_APP_SECRET'))
    ap.add_argument('--csv'); ap.add_argument('--sweep', action='store_true')
    ap.add_argument('--min-bars', type=int); ap.add_argument('--min-area', type=float); ap.add_argument('--min-depth', type=float)
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(here, '..', B['data_dir']); out_dir = os.path.join(here, '..', B['out_dir'])
    os.makedirs(data_dir, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
    csv = a.csv or os.path.join(data_dir, f'{a.symbol}_1min.csv')
    if not a.csv:
        assert a.app_key and a.app_secret, '請設 WEBULL_APP_KEY / WEBULL_APP_SECRET'
        df = fetch_1min(a.symbol, a.category, a.count, a.app_key, a.app_secret, a.region); df.to_csv(csv, index=False); print(f'抓取 {len(df)} 根 1分K → {csv}')
    hk = a.category.startswith('HK')
    cfg = json.loads(json.dumps(CFG)); cfg['symbol']['market'] = 'HK' if hk else 'US'
    p = params_from_config(cfg, {'min_bars': a.min_bars, 'min_area_pct': a.min_area, 'min_depth_pct': a.min_depth})
    df = load_csv(csv, tz=cfg['session'][cfg['symbol']['market']]['tz'])
    print('標的:', a.symbol, a.category, '|', describe(cfg)); print('參數:', json.dumps(p.to_dict(), ensure_ascii=False))
    d, tr, st = backtest(df, p)
    print('回測:', json.dumps(st, ensure_ascii=False, indent=1, default=str))
    d.to_csv(os.path.join(out_dir, f'{a.symbol}_signals.csv')); tr.to_csv(os.path.join(out_dir, f'{a.symbol}_trades.csv'), index=False)
    if a.sweep:
        res = sweep(df, p, B['sweep_grid']); print(res.head(15).to_string(index=False)); res.to_csv(os.path.join(out_dir, f'{a.symbol}_sweep.csv'), index=False)

if __name__ == '__main__':
    main()
