# -*- coding: utf-8 -*-
"""
macd_momentum_core.py — MACD 動能蓄積交叉策略 · 共用引擎 (三平台共用同一套訊號邏輯)

規則 (依用戶附圖):
  指標  : MACD(12,26,9), DIF=EMA12-EMA26, DEA=EMA9(DIF), HIST=DIF-DEA
          ※ 牛牛/Webull 圖上的 MACD 柱 = 2×(DIF-DEA); TradingView = 1×。本引擎一律用 1× 定義門檻。
  動能段: 同號 HIST 連續段。三個量度 (皆以 close 正規化為 %, 跨標的可用):
          bars  = 連續根數
          area  = Σ|HIST|/close×100   (%·根)
          depth = max|HIST|/close×100 (%)
          三者都 ≥ 門檻 → 該段「儲了足夠動能」(附圖圈起來的柱群)
  買點  : 剛結束的負動能段合格 + 完成K線上 DIF 上穿 DEA (附圖藍色直線) → 下一根開盤買入
  賣點  : 剛結束的正動能段合格 + DIF 下穿 DEA (附圖紅/橙直線)          → 下一根開盤賣出
  其他  : 長倉only, 單一持倉, 收市前強制平倉(intraday), 動能不足的交叉一律忽略
"""
from __future__ import annotations
import pandas as pd, numpy as np
from dataclasses import dataclass, asdict, field
from itertools import product

# ------------------------------------------------------------------ params
@dataclass
class Params:
    fast: int = 12
    slow: int = 26
    signal: int = 9
    min_bars: int = 4          # 動能段最少連續根數
    min_area_pct: float = 0.15 # 動能段面積門檻 (%·根)  Σ|hist|/close×100
    min_depth_pct: float = 0.04# 動能段深度門檻 (%)     max|hist|/close×100
    fill: str = 'next_open'    # 'next_open' (完成K後下一根開盤成交) | 'close' (訊號K收盤成交)
    commission_bps: float = 3.0 # 單邊手續費 (基點, 0.03%)
    slippage_ticks: float = 0.0 # 滑點 (以 tick 計)
    tick: float = 0.01
    session_open: str = '09:30'
    session_close: str = '16:00'
    lunch_start: str = '12:00'  # 港股午休 (美股設 None)
    lunch_end: str = '13:00'
    no_entry_after: str = '15:45' # 收市前不再開新倉
    eod_flat: str = '15:58'       # 此時間(含)之後第一根K強制平倉
    stop_loss_pct: float | None = None  # 可選: 固定止損% (None=關閉, 依原題不設)
    allow_short: bool = False    # 可選: 賣訊反手做空 (港股ETF通常不適用)

    def to_dict(self):
        return asdict(self)

# ------------------------------------------------------------------ indicators
def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def macd(close: pd.Series, fast=12, slow=26, signal=9):
    dif = ema(close, fast) - ema(close, slow)
    dea = ema(dif, signal)
    hist = dif - dea
    return dif, dea, hist

# ------------------------------------------------------------------ signals
def compute_signals(df: pd.DataFrame, p: Params) -> pd.DataFrame:
    """df: index=datetime (tz-naive local), cols open/high/low/close/volume. 回傳加上指標與訊號欄位的副本。
    動能段統計「僅用當根及之前資料」, 交叉在完成K線判定 → 無前視。"""
    d = df.copy()
    d['dif'], d['dea'], d['hist'] = macd(d['close'], p.fast, p.slow, p.signal)
    d['hist_pct'] = d['hist'] / d['close'] * 100.0
    n = len(d)
    hp = d['hist_pct'].values
    dif = d['dif'].values; dea = d['dea'].values
    # run tracking (current-sign run, evaluated BEFORE the cross bar updates it)
    run_sign = np.zeros(n, dtype=int); run_bars = np.zeros(n, dtype=int)
    run_area = np.zeros(n); run_depth = np.zeros(n)
    prev_bars = np.zeros(n, dtype=int); prev_area = np.zeros(n); prev_depth = np.zeros(n); prev_sign = np.zeros(n, dtype=int)
    cs, cb, ca, cd = 0, 0, 0.0, 0.0
    for i in range(n):
        h = hp[i]
        s = 1 if h > 0 else (-1 if h < 0 else 0)
        # stats of the run as it stood at the end of the previous bar (= the run that a cross on this bar terminates)
        prev_sign[i], prev_bars[i], prev_area[i], prev_depth[i] = cs, cb, ca, cd
        if s != 0 and s != cs:
            cs, cb, ca, cd = s, 1, abs(h), abs(h)
        elif s != 0:
            cb += 1; ca += abs(h); cd = max(cd, abs(h))
        run_sign[i], run_bars[i], run_area[i], run_depth[i] = cs, cb, ca, cd
    d['run_sign'] = run_sign; d['run_bars'] = run_bars; d['run_area'] = run_area; d['run_depth'] = run_depth
    d['prev_sign'] = prev_sign; d['prev_bars'] = prev_bars; d['prev_area'] = prev_area; d['prev_depth'] = prev_depth
    cross_up = (dif > dea) & (np.roll(dif, 1) <= np.roll(dea, 1)); cross_up[0] = False
    cross_dn = (dif < dea) & (np.roll(dif, 1) >= np.roll(dea, 1)); cross_dn[0] = False
    ok = lambda sign: (prev_sign == sign) & (prev_bars >= p.min_bars) & (prev_area >= p.min_area_pct) & (prev_depth >= p.min_depth_pct)
    d['cross_up'] = cross_up; d['cross_dn'] = cross_dn
    d['neg_ok'] = ok(-1); d['pos_ok'] = ok(1)
    d['buy_sig'] = cross_up & d['neg_ok'].values      # 藍色直線
    d['sell_sig'] = cross_dn & d['pos_ok'].values     # 紅/橙直線
    # 合格動能段標記 (供繪圖: 藍圈=負段, 橙圈=正段) — 標在交叉K, 段長=prev_bars
    d['neg_cluster_end'] = d['buy_sig']; d['pos_cluster_end'] = d['sell_sig']
    # session flags
    t = d.index.time
    def _t(s): return pd.Timestamp('2000-01-01 ' + s).time()
    in_sess = (t >= _t(p.session_open)) & (t < _t(p.session_close))
    if p.lunch_start and p.lunch_end:
        in_sess &= ~((t >= _t(p.lunch_start)) & (t < _t(p.lunch_end)))
    d['in_session'] = in_sess
    d['entry_ok'] = in_sess & (t < _t(p.no_entry_after))
    d['eod'] = t >= _t(p.eod_flat)
    return d

# ------------------------------------------------------------------ backtest
def backtest(df: pd.DataFrame, p: Params):
    d = compute_signals(df, p)
    trades = []
    pos = 0; entry_px = None; entry_time = None; qty_dir = 0
    equity = 1.0; eq = []
    fee = p.commission_bps / 1e4
    slip = p.slippage_ticks * p.tick
    idx = d.index; o = d['open'].values; c = d['close'].values
    days = d.index.date
    pending = None  # ('BUY'/'SELL'/'FLAT', reason) to execute at next open
    for i in range(len(d)):
        # 1) execute pending order at this bar's open
        if pending is not None and p.fill == 'next_open':
            side, reason = pending; pending = None
            if days[i] != days[i-1]:  # 跨日 → 不執行 (前一日已強平)
                side = None
            if side == 'BUY' and pos == 0:
                pos = 1; entry_px = o[i] + slip; entry_time = idx[i]
            elif side in ('SELL', 'FLAT') and pos == 1:
                px = o[i] - slip
                r = px / entry_px - 1 - 2 * fee
                trades.append({'entry_time': entry_time, 'exit_time': idx[i], 'entry': entry_px, 'exit': px, 'ret': r, 'bars': None, 'reason': reason})
                equity *= (1 + r); pos = 0
        # 2) evaluate signals on completed bar i
        row_sig_buy = d['buy_sig'].iat[i] and d['entry_ok'].iat[i]
        row_sig_sell = d['sell_sig'].iat[i]
        eod = d['eod'].iat[i] or (i + 1 < len(d) and days[i+1] != days[i]) or i == len(d) - 1
        stop_hit = pos == 1 and p.stop_loss_pct is not None and c[i] <= entry_px * (1 - p.stop_loss_pct / 100)
        if pos == 1 and (eod or stop_hit or row_sig_sell):
            reason = 'EOD' if eod else ('STOP' if stop_hit else 'MACD_SELL')
            if p.fill == 'close' or eod:
                px = c[i] - slip
                r = px / entry_px - 1 - 2 * fee
                trades.append({'entry_time': entry_time, 'exit_time': idx[i], 'entry': entry_px, 'exit': px, 'ret': r, 'bars': None, 'reason': reason})
                equity *= (1 + r); pos = 0
            else:
                pending = ('SELL', reason)
        elif pos == 0 and row_sig_buy and not eod:
            if p.fill == 'close':
                pos = 1; entry_px = c[i] + slip; entry_time = idx[i]
            else:
                pending = ('BUY', 'MACD_BUY')
        mark = equity * ((c[i] / entry_px) if pos == 1 else 1.0)
        eq.append(mark)
    tr = pd.DataFrame(trades)
    if len(tr):
        tr['bars'] = [(d.index.get_loc(b) - d.index.get_loc(a)) for a, b in zip(tr['entry_time'], tr['exit_time'])]
    d['equity'] = eq
    return d, tr, stats(tr, d)

def stats(tr: pd.DataFrame, d: pd.DataFrame) -> dict:
    if len(tr) == 0:
        return {'trades': 0}
    wins = tr[tr.ret > 0]; losses = tr[tr.ret <= 0]
    eqs = d['equity']; dd = (eqs / eqs.cummax() - 1).min()
    n_days = len(set(d.index.date))
    return {
        'trades': int(len(tr)), 'win_rate': float((tr.ret > 0).mean()),
        'avg_ret_pct': float(tr.ret.mean() * 100), 'median_ret_pct': float(tr.ret.median() * 100),
        'avg_win_pct': float(wins.ret.mean() * 100) if len(wins) else 0.0,
        'avg_loss_pct': float(losses.ret.mean() * 100) if len(losses) else 0.0,
        'profit_factor': float(wins.ret.sum() / abs(losses.ret.sum())) if len(losses) and losses.ret.sum() != 0 else float('inf'),
        'total_return_pct': float((eqs.iloc[-1] - 1) * 100), 'max_dd_pct': float(dd * 100),
        'avg_bars_held': float(tr.bars.mean()), 'days': n_days, 'trades_per_day': float(len(tr) / max(1, n_days)),
        'exit_reasons': tr.reason.value_counts().to_dict(),
    }

# ------------------------------------------------------------------ parameter sweep
def sweep(df: pd.DataFrame, base: Params, grid: dict) -> pd.DataFrame:
    keys = list(grid.keys()); rows = []
    for combo in product(*[grid[k] for k in keys]):
        p = Params(**{**base.to_dict(), **dict(zip(keys, combo))})
        _, tr, st = backtest(df, p)
        rows.append({**dict(zip(keys, combo)), **{k: v for k, v in st.items() if k != 'exit_reasons'}})
    out = pd.DataFrame(rows)
    return out.sort_values('total_return_pct', ascending=False).reset_index(drop=True)

# ------------------------------------------------------------------ io
def load_csv(path: str, tz: str | None = None) -> pd.DataFrame:
    """CSV 欄位: datetime(或 time_key/timestamp), open, high, low, close, volume. 回傳 index=datetime 之 DataFrame。"""
    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}
    tcol = next((cols[k] for k in ('datetime', 'time_key', 'timestamp', 'time', 'date') if k in cols), None)
    if tcol is None: raise ValueError('找不到時間欄 (datetime/time_key/timestamp)')
    df['datetime'] = pd.to_datetime(df[tcol])
    if df['datetime'].dt.tz is not None:
        df['datetime'] = df['datetime'].dt.tz_convert(tz or 'Asia/Hong_Kong').dt.tz_localize(None)
    df = df.rename(columns={cols.get('open','open'):'open', cols.get('high','high'):'high', cols.get('low','low'):'low',
                            cols.get('close','close'):'close', cols.get('volume','volume'):'volume'})
    df = df[['datetime','open','high','low','close','volume']].dropna(subset=['close']).sort_values('datetime')
    return df.set_index('datetime')
