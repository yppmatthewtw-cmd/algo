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


def crsi(c: pd.Series, domcycle: int = 20, vibration: int = 10):
    """cRSI v4 (whentotrade / Lars von Thienen) 與 Pine 版 ④c 逐項對齊:
    RSI 長度 = domcycle // 2 (ta.rma 平滑), torque = 2/(vibration+1), phasingLag = (vibration-1)//2,
    crsi = torque*(2*rsi - rsi[lag]) + (1-torque)*crsi[1] (Pine 的 nz(crsi[1]) 起始為 0)。"""
    n = max(2, domcycle // 2)
    d = c.diff()
    up, dn = rma(d.clip(lower=0), n), rma((-d).clip(lower=0), n)
    r = np.where(dn == 0, 100.0, np.where(up == 0, 0.0, 100.0 - 100.0 / (1.0 + up / dn.replace(0, np.nan))))
    r = pd.Series(r, index=c.index)
    torque = 2.0 / (vibration + 1)
    lag = max(0, (vibration - 1) // 2)
    x = (2.0 * r - r.shift(lag)).to_numpy(dtype=float)
    out = np.zeros(len(x))
    prev = 0.0
    for i in range(len(x)):
        xi = x[i]
        if np.isnan(xi):
            out[i] = np.nan
            continue
        prev = torque * xi + (1.0 - torque) * prev
        out[i] = prev
    return pd.Series(out, index=c.index)


def crsi_bands(cr: pd.Series, domcycle: int = 20, leveling: float = 10.0):
    """下界 / 上界 = 最近 domcycle*2 根 cRSI 的第 leveling / 100-leveling 百分位 (Pine 版預設的「百分位」算法)。"""
    mem = domcycle * 2
    return rolling_percentile(cr, mem, leveling), rolling_percentile(cr, mem, 100.0 - leveling)


def barssince(cond: pd.Series) -> pd.Series:
    """ta.barssince: 距上一次 cond 為真幾根 (那根 = 0); 從未為真 = NaN。"""
    v = cond.fillna(False).to_numpy(dtype=bool)
    out = np.full(len(v), np.nan)
    last = -1
    for i in range(len(v)):
        if v[i]:
            last = i
        if last >= 0:
            out[i] = i - last
    return pd.Series(out, index=cond.index)
