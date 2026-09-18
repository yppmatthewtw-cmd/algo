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
from macd_momentum_core import backtest, sweep, load_csv, auto_thresholds, is_intraday
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
    ap.add_argument('--auto-th', action='store_true', help='以柱高分佈自動定門檻 (換週期如日線必用)')
    ap.add_argument('--depth-pctl', type=float, default=60.0, help='自動門檻取第幾百分位')
    ap.add_argument('--capital', type=float, default=100000.0, help='本金 (報表金額損益用)')
    ap.add_argument('--tf', choices=['auto', '1min', '5min', 'daily'], default='auto',
                    help='K線週期預設 (auto=依數據自動判定, 日線會自動繞過盤中時段)')
    a = ap.parse_args()
    cfg = json.loads(json.dumps(CFG))
    if a.market: cfg['symbol']['market'] = a.market
    df = load_csv(a.csv)
    # 週期預設: 由數據自動判定, 避免 config 的 1min preset 把日線當成盤中 (時段過濾會濾掉全部日線K)
    detected_intraday = is_intraday(df.index)
    tf_key = a.tf if a.tf != 'auto' else ('daily' if not detected_intraday else (cfg.get('timeframe', {}).get('current') or '1min'))
    cfg.setdefault('timeframe', {})['current'] = tf_key
    p = params_from_config(cfg, {'min_bars': a.min_bars, 'min_area_pct': a.min_area, 'min_depth_pct': a.min_depth,
                                 'fill': a.fill, 'commission_bps': a.commission_bps, 'stop_loss_pct': a.stop})
    p.initial_capital = a.capital
    if a.auto_th:
        p = auto_thresholds(df, p, depth_pctl=a.depth_pctl)
    os.makedirs(a.out, exist_ok=True)
    print('標的(config):', describe(cfg))
    tf = '盤中' if p.intraday else '日線或以上 (自動繞過盤中時段/收市強平, 可持倉過夜)'
    print(f'數據: {df.index[0]} → {df.index[-1]}  {len(df)} 根K, {len(set(df.index.date))} 個交易日 | 週期: {tf_key} ({tf})')
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
        t2 = tr.copy()
        t2['ret%'] = (t2.ret * 100).round(2); t2['pnl$'] = t2.pnl.round(0); t2['權益'] = t2.equity_after.round(0)
        print(f'\n逐筆交易 (本金 {a.capital:,.0f}):')
        print(t2[['entry_time', 'exit_time', 'entry', 'exit', 'ret%', 'pnl$', '權益', 'reason']].to_string(index=False))
        print(f"\n期內交易 {len(tr)} 筆 · 總損益 {st['total_pnl']:,.0f} ({st['total_return_pct']:.2f}%) · 期末權益 {st['final_equity']:,.0f}")
    if a.sweep:
        print('\n===== 門檻網格搜尋 (依總報酬排序, 前 15) =====')
        res = sweep(df, p, CFG['backtest']['sweep_grid'])
        print(res.head(15).to_string(index=False))
        res.to_csv(f'{a.out}/{base}_sweep.csv', index=False)
        print(f'已輸出: {a.out}/{base}_sweep.csv  (網格搜尋屬 in-sample, 請留一段樣本外驗證)')

if __name__ == '__main__':
    main()
