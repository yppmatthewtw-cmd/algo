# -*- coding: utf-8 -*-
"""indicators.py — 與 TradingView Pine 內建函式逐一對齊的指標實作。

對齊重點 (不對齊就無法跟 TradingView 的回測互相印證):
  · ta.rma  = Wilder 平滑 (alpha = 1/length), 不是 SMA 也不是一般 EMA
  · ta.atr  = RMA(true range), true range 含前一根收盤的跳空
  · ta.rsi  = RMA(上漲幅) / RMA(下跌幅)
  · ta.macd = EMA(fast) - EMA(slow), 訊號線 = EMA(該差值)
  · ta.supertrend 方向: -1 = 上升趨勢 (與 Pine 相同, 不是 +1)
  · ta.percentile_linear_interpolation = 線性插值百分位 (numpy 預設法)
"""
import numpy as np
import pandas as pd


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rma(s: pd.Series, n: int) -> pd.Series:
    """Pine ta.rma: 第一個值 = 前 n 個樣本的 SMA, 之後 alpha = 1/n 遞迴。pandas ewm 以第一個樣本起始, 暖身期會不同。"""
    v = s.to_numpy(dtype=float)
    out = np.full(len(v), np.nan)
    valid = np.flatnonzero(~np.isnan(v))
    if len(valid) >= n:
        first = valid[0]
        if first + n <= len(v):
            out[first + n - 1] = np.nanmean(v[first:first + n])
            a = 1.0 / n
            for i in range(first + n, len(v)):
                x = v[i] if not np.isnan(v[i]) else out[i - 1]
                out[i] = a * x + (1.0 - a) * out[i - 1]
    return pd.Series(out, index=s.index)


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def stdev(s: pd.Series, n: int) -> pd.Series:
    # Pine 的 ta.stdev 是母體標準差 (ddof = 0)
    return s.rolling(n, min_periods=n).std(ddof=0)


def true_range(h, l, c) -> pd.Series:
    pc = c.shift(1)
    return pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)


def atr(h, l, c, n: int = 14) -> pd.Series:
    return rma(true_range(h, l, c), n)


def rsi(c: pd.Series, n: int = 14) -> pd.Series:
    d = c.diff()
    return 100.0 - 100.0 / (1.0 + rma(d.clip(lower=0), n) / rma((-d).clip(lower=0), n))


def macd(c: pd.Series, fast=12, slow=26, sig=9):
    line = ema(c, fast) - ema(c, slow)
    signal = ema(line, sig)
    return line, signal, line - signal


def supertrend(h, l, c, mult=3.0, n=10):
    """回傳 (線, 方向); 方向 -1 = 上升趨勢, +1 = 下降趨勢 (與 Pine ta.supertrend 相同)。"""
    a = atr(h, l, c, n).to_numpy()
    hl2 = ((h + l) / 2.0).to_numpy()
    cl = c.to_numpy()
    up = hl2 + mult * a
    dn = hl2 - mult * a
    m = len(cl)
    U = np.full(m, np.nan)
    D = np.full(m, np.nan)
    dirn = np.ones(m)
    st = np.full(m, np.nan)
    for i in range(m):
        if np.isnan(a[i]):
            continue
        pu = U[i - 1] if i > 0 and not np.isnan(U[i - 1]) else up[i]
        pd_ = D[i - 1] if i > 0 and not np.isnan(D[i - 1]) else dn[i]
        U[i] = min(up[i], pu) if (i > 0 and cl[i - 1] < pu) else up[i]
        D[i] = max(dn[i], pd_) if (i > 0 and cl[i - 1] > pd_) else dn[i]
        prev = dirn[i - 1] if i > 0 else 1.0
        if i > 0 and not np.isnan(U[i - 1]) and cl[i] > U[i - 1]:
            dirn[i] = -1.0
        elif i > 0 and not np.isnan(D[i - 1]) and cl[i] < D[i - 1]:
            dirn[i] = 1.0
        else:
            dirn[i] = prev
        st[i] = D[i] if dirn[i] < 0 else U[i]
    return pd.Series(st, index=c.index), pd.Series(dirn, index=c.index)


def rolling_percentile(s: pd.Series, n: int, pct: float) -> pd.Series:
    """ta.percentile_linear_interpolation(s, n, pct) 的等價實作。"""
    v = s.to_numpy(dtype=float)
    m = len(v)
    out = np.full(m, np.nan)
    if m >= n:
        win = np.lib.stride_tricks.sliding_window_view(v, n)
        out[n - 1:] = np.nanpercentile(win, pct, axis=1)
    return pd.Series(out, index=s.index)


def crossover(a: pd.Series, b) -> pd.Series:
    b = pd.Series(b, index=a.index) if np.isscalar(b) else b
    return (a > b) & (a.shift(1) <= b.shift(1))


def crossunder(a: pd.Series, b) -> pd.Series:
    b = pd.Series(b, index=a.index) if np.isscalar(b) else b
    return (a < b) & (a.shift(1) >= b.shift(1))
