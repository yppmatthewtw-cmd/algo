# -*- coding: utf-8 -*-
"""
backtest_cli.py — 用任何 1 分鐘 OHLCV CSV 跑回測 (三平台通用; 標的/時段/參數預設讀 config.json)
用法:
  python backtest_cli.py --csv data/HK_07709_1min.csv
  python backtest_cli.py --csv data/HK_07709_1min.csv --min-bars 5 --min-area 0.2 --min-depth 0.05
  python backtest_cli.py --csv data/HK_07709_1min.csv --sweep          # 門檻網格搜尋
  python backtest_cli.py --csv data/TQQQ_1min.csv --market US          # 臨時改美股時段
CSV 欄位: datetime, open, high, low, close, volume  (牛牛 time_key / Webull timestamp 亦可)
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from macd_momentum_core import backtest, sweep, load_csv
from config_loader import CFG, params_from_config, describe

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--out', default=CFG['backtest']['out_dir'])
    ap.add_argument('--market', choices=['HK', 'US'], help='臨時覆寫 config 的市場時段')
    ap.add_argument('--min-bars', type=int); ap.add_argument('--min-area', type=float); ap.add_argument('--min-depth', type=float)
    ap.add_argument('--fill', choices=['next_open', 'close']); ap.add_argument('--commission-bps', type=float)
    ap.add_argument('--stop', type=float, help='可選固定止損% (原題不設)')
    ap.add_argument('--sweep', action='store_true')
    a = ap.parse_args()
    cfg = json.loads(json.dumps(CFG))
    if a.market: cfg['symbol']['market'] = a.market
    p = params_from_config(cfg, {'min_bars': a.min_bars, 'min_area_pct': a.min_area, 'min_depth_pct': a.min_depth,
                                 'fill': a.fill, 'commission_bps': a.commission_bps, 'stop_loss_pct': a.stop})
    df = load_csv(a.csv)
    os.makedirs(a.out, exist_ok=True)
    print('標的(config):', describe(cfg))
    print(f'數據: {df.index[0]} → {df.index[-1]}  {len(df)} 根1分K, {len(set(df.index.date))} 個交易日')
    print('參數:', json.dumps(p.to_dict(), ensure_ascii=False))
    d, tr, st = backtest(df, p)
    print('\n===== 回測結果 =====')
    for k, v in st.items():
        print(f'  {k:18s}: {v:.3f}' if isinstance(v, float) else f'  {k:18s}: {v}')
    print(f'\n訊號: 買 {int(d.buy_sig.sum())} / 賣 {int(d.sell_sig.sum())} | 全部交叉: 上穿 {int(d.cross_up.sum())} / 下穿 {int(d.cross_dn.sum())} → 動能過濾後保留 {int(d.buy_sig.sum()+d.sell_sig.sum())}')
    base = os.path.splitext(os.path.basename(a.csv))[0]
    d.to_csv(f'{a.out}/{base}_signals.csv'); tr.to_csv(f'{a.out}/{base}_trades.csv', index=False)
    print(f'已輸出: {a.out}/{base}_signals.csv, {a.out}/{base}_trades.csv')
    if len(tr):
        print('\n最近 10 筆交易:'); print(tr.tail(10).to_string(index=False))
    if a.sweep:
        print('\n===== 門檻網格搜尋 (依總報酬排序, 前 15) =====')
        res = sweep(df, p, CFG['backtest']['sweep_grid'])
        print(res.head(15).to_string(index=False))
        res.to_csv(f'{a.out}/{base}_sweep.csv', index=False)
        print(f'已輸出: {a.out}/{base}_sweep.csv  (網格搜尋屬 in-sample, 請留一段樣本外驗證)')

if __name__ == '__main__':
    main()
