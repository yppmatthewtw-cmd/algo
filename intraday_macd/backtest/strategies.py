# -*- coding: utf-8 -*-
"""strategies.py — 13 個日內做多策略的進 / 出場訊號, 與 TradingView 版 TW-1M-MULTI 逐條對應。

約定 (與 Pine 版完全相同):
  · 訊號一律在該根 K 線【收盤】確認 → 由回測引擎在【下一根開盤】成交, 不會偷看未來
  · 只做多; 出場訊號、收市強平、固定止損三者任一成立即平倉
  · 第 13 個 (S13 隨機進場) 沒有出場訊號, 改由引擎用「固定持倉根數」平倉
"""
import numpy as np
import pandas as pd
import indicators as ta

NAMES = [
    "S01 MACD柱動能減弱", "S02 MACD DIF/DEA交叉", "S03 EMA 9/21 交叉", "S04 Supertrend 轉向",
    "S05 RSI 超賣回歸", "S06 布林下軌回歸", "S07 VWAP 偏離回歸", "S08 開盤區間突破",
    "S09 動能突破+量能", "S10 三EMA+ST共振", "S11 ATR標準化MACD", "S12 MACD柱背離",
    "S13 隨機進場(安慰劑)", "S14 MACD柱+RSI 雙訊號",
]

DEFAULTS = dict(
    fast=12, slow=26, sig=9, fade_buy=2, fade_sell=2, k_buy=1.0, k_sell=1.0,
    mb_buy=3, mb_sell=3, pct_len=250, depth_pct=50, area_fac=0.5, k_atr=0.35,
    ema_f=9, ema_m=21, ema_s=50, st_atr=10, st_mult=3.0,
    rsi_len=14, rsi_buy=30.0, rsi_exit=55.0, bb_len=20, bb_mult=2.0, vwap_k=1.5,
    orb_bars=15, brk_len=20, vol_mult=1.5, div_len=20, p_rand=0.004, hold_bars=30,
    # S14: 模式 1 用調高後的下跌動能門檻 (k 1.5 / 最少根數 4), 模式 2 = S05, 匹配窗口 5 根
    s14_k_buy=1.5, s14_mb_buy=4, s14_match_win=5, s14_rsi_sell="neutral",  # "neutral" = RSI 上穿 55; "overbought" = RSI 下穿 70
    rsi_ob=70.0,
)


def _segment_stats(hist: pd.Series, close: pd.Series, atr_s: pd.Series):
    """MACD 柱同號段的累積統計: 根數 / 面積 / 深度 (%, 以及 ATR 單位的深度)。

    「儲夠動能」就是用這三個數字判斷的 — 段夠長、跌得夠深、面積夠大, 才承認這是一段真正的下跌動能。
    """
    h = hist.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    a = atr_s.to_numpy(dtype=float)
    n = len(h)
    sign = np.zeros(n, dtype=int)
    bars = np.zeros(n, dtype=int)
    area = np.zeros(n)
    depth = np.zeros(n)
    depth_a = np.zeros(n)
    cs, cb, ca, cd, cda = 0, 0, 0.0, 0.0, 0.0
    for i in range(n):
        if np.isnan(h[i]) or c[i] == 0:
            sign[i], bars[i], area[i], depth[i], depth_a[i] = cs, cb, ca, cd, cda
            continue
        s = 1 if h[i] > 0 else (-1 if h[i] < 0 else 0)
        hp = abs(h[i]) / c[i] * 100.0
        ha = 0.0 if (np.isnan(a[i]) or a[i] == 0) else abs(h[i]) / a[i]
        if s != 0:
            if s != cs:
                cs, cb, ca, cd, cda = s, 1, hp, hp, ha
            else:
                cb += 1
                ca += hp
                cd = max(cd, hp)
                cda = max(cda, ha)
        sign[i], bars[i], area[i], depth[i], depth_a[i] = cs, cb, ca, cd, cda
    idx = hist.index
    return (pd.Series(sign, idx), pd.Series(bars, idx), pd.Series(area, idx),
            pd.Series(depth, idx), pd.Series(depth_a, idx))


def _run_counter(flag: pd.Series) -> pd.Series:
    """連續成立的根數; 中斷即歸零 (Pine 的 nFadeDn / nFadeUp)。"""
    f = flag.fillna(False).to_numpy()
    out = np.zeros(len(f), dtype=int)
    run = 0
    for i, v in enumerate(f):
        run = run + 1 if v else 0
        out[i] = run
    return pd.Series(out, index=flag.index)


def _age_since(flag: pd.Series) -> pd.Series:
    """距上一次成立過了幾根 (成立那根 = 0; 從未成立 = 999), 與 Pine 版的 m1Age / m2Age 相同。"""
    f = flag.fillna(False).to_numpy()
    out = np.full(len(f), 999, dtype=int)
    age = 999
    for i, v in enumerate(f):
        age = 0 if v else min(age + 1, 999)
        out[i] = age
    return pd.Series(out, index=flag.index)


def build_signals(df: pd.DataFrame, p: dict = None) -> tuple:
    """回傳 (longs, exits): 兩個 DataFrame, 欄 = 13 個策略, 值 = 該根收盤是否出訊號。

    df 需含 open/high/low/close/volume, 以及由引擎預先算好的 in_sess / new_sess 兩欄。
    """
    p = {**DEFAULTS, **(p or {})}
    o, h, l, c, v = df.open, df.high, df.low, df.close, df.volume
    in_sess, new_sess = df.in_sess, df.new_sess

    dif, dea, hist = ta.macd(c, p['fast'], p['slow'], p['sig'])
    atr = ta.atr(h, l, c, 14)
    e1, e2, e3 = ta.ema(c, p['ema_f']), ta.ema(c, p['ema_m']), ta.ema(c, p['ema_s'])
    _, st_dir = ta.supertrend(h, l, c, p['st_mult'], p['st_atr'])
    rsi = ta.rsi(c, p['rsi_len'])
    bb_b = ta.sma(c, p['bb_len'])
    bb_lo = bb_b - p['bb_mult'] * ta.stdev(c, p['bb_len'])
    vol_a = ta.sma(v, 20)
    don_h = h.rolling(p['brk_len']).max().shift(1)
    don_l = l.rolling(p['brk_len']).min().shift(1)
    p_low = l.rolling(p['div_len']).min().shift(1)
    p_high = h.rolling(p['div_len']).max().shift(1)
    h_low = hist.rolling(p['div_len']).min().shift(1)
    h_high = hist.rolling(p['div_len']).max().shift(1)

    # 每節重設的 VWAP (與 Pine 版自行累加的寫法一致)
    hlc3 = (h + l + c) / 3.0
    grp = new_sess.cumsum()
    pv = (hlc3 * v).where(in_sess, 0.0).groupby(grp).cumsum()
    vv = v.where(in_sess, 0.0).groupby(grp).cumsum()
    vwap = np.where(vv > 0, pv / vv.replace(0, np.nan), c)
    vwap = pd.Series(vwap, index=c.index)
    dev_a = ((c - vwap) / atr.replace(0, np.nan)).fillna(0.0)

    # 開盤區間 (每節前 orb_bars 根的高低)
    bar_no = in_sess.groupby(grp).cumsum()
    early = in_sess & (bar_no <= p['orb_bars'])
    orb_h = h.where(early).groupby(grp).cummax().ffill()
    orb_l = l.where(early).groupby(grp).cummin().ffill()
    orb_ready = in_sess & (bar_no > p['orb_bars']) & orb_h.notna()

    seg_sign, seg_bars, seg_area, seg_depth, seg_depth_a = _segment_stats(hist, c, atr)
    h_pct = (hist.abs() / c.replace(0, np.nan) * 100.0).fillna(0.0)
    auto_depth = ta.rolling_percentile(h_pct, p['pct_len'], p['depth_pct'])
    d_buy, d_sell = auto_depth * p['k_buy'], auto_depth * p['k_sell']
    a_buy = d_buy * p['mb_buy'] * p['area_fac']
    a_sell = d_sell * p['mb_sell'] * p['area_fac']
    n_fade_dn = _run_counter((hist < 0) & (hist > hist.shift(1)))
    n_fade_up = _run_counter((hist > 0) & (hist < hist.shift(1)))
    ok_buy = (p['k_buy'] <= 0) | ((seg_bars >= p['mb_buy']) & (seg_depth >= d_buy) & (seg_area >= a_buy))
    ok_sell = (p['k_sell'] <= 0) | ((seg_bars >= p['mb_sell']) & (seg_depth >= d_sell) & (seg_area >= a_sell))
    ok_buy_a = (p['k_atr'] <= 0) | ((seg_bars >= p['mb_buy']) & (seg_depth_a >= p['k_atr']))
    ok_sell_a = (p['k_atr'] <= 0) | ((seg_bars >= p['mb_sell']) & (seg_depth_a >= p['k_atr']))

    # 偽亂數: 與 Pine 版同一條公式, 同一根 K 永遠得到同一個值 → 結果可重現
    bi = np.arange(len(c), dtype=float)
    rnd = np.abs(np.sin(bi * 12.9898 + 78.233) * 43758.5453)
    rnd = pd.Series(rnd - np.floor(rnd), index=c.index)

    L, X = {}, {}
    L[0] = (n_fade_dn == p['fade_buy']) & (seg_sign == -1) & ok_buy
    X[0] = (n_fade_up == p['fade_sell']) & (seg_sign == 1) & ok_sell
    L[1], X[1] = ta.crossover(dif, dea), ta.crossunder(dif, dea)
    L[2], X[2] = ta.crossover(e1, e2), ta.crossunder(e1, e2)
    L[3] = (st_dir == -1) & (st_dir.shift(1) == 1)
    X[3] = (st_dir == 1) & (st_dir.shift(1) == -1)
    L[4], X[4] = ta.crossover(rsi, p['rsi_buy']), ta.crossover(rsi, p['rsi_exit'])
    L[5], X[5] = ta.crossover(c, bb_lo), ta.crossover(c, bb_b)
    L[6], X[6] = ta.crossover(dev_a, -p['vwap_k']), ta.crossover(dev_a, 0.0)
    orb_break = orb_ready & ta.crossover(c, orb_h)
    first_break = orb_break & (orb_break.groupby(grp).cumsum() == 1)
    L[7], X[7] = first_break, orb_ready & ta.crossunder(c, orb_l)
    L[8] = (c > don_h) & (v > vol_a * p['vol_mult']) & (c > e3)
    X[8] = ta.crossunder(c, e2) | ta.crossunder(c, don_l)
    stack = (e1 > e2) & (e2 > e3) & (st_dir == -1)
    L[9], X[9] = stack & ~stack.shift(1).fillna(False), (e1 < e2) | (st_dir == 1)
    L[10] = (n_fade_dn == p['fade_buy']) & (seg_sign == -1) & ok_buy_a
    X[10] = (n_fade_up == p['fade_sell']) & (seg_sign == 1) & ok_sell_a
    L[11], X[11] = (l <= p_low) & (hist > h_low), (h >= p_high) & (hist < h_high)
    L[12], X[12] = rnd < p['p_rand'], pd.Series(False, index=c.index)

    # S14 雙訊號: 模式 1 = S01 但下跌動能門檻調高; 模式 2 = S05; 買需兩者在匹配窗口內同時成立, 賣任一即賣
    d_buy14 = auto_depth * p['s14_k_buy']
    a_buy14 = d_buy14 * p['s14_mb_buy'] * p['area_fac']
    ok_buy14 = (p['s14_k_buy'] <= 0) | ((seg_bars >= p['s14_mb_buy']) & (seg_depth >= d_buy14) & (seg_area >= a_buy14))
    m1_buy = ((n_fade_dn == p['fade_buy']) & (seg_sign == -1) & ok_buy14).fillna(False)
    m2_buy = L[4].fillna(False)
    m1_age = _age_since(m1_buy)
    m2_age = _age_since(m2_buy)
    win = p['s14_match_win']
    L[13] = (m1_age < win) & (m2_age < win) & (m1_buy | m2_buy)
    m2_sell = X[4] if p['s14_rsi_sell'] == "neutral" else ta.crossunder(rsi, p['rsi_ob'])
    X[13] = X[0].fillna(False) | m2_sell.fillna(False)

    longs = pd.DataFrame({NAMES[i]: L[i].fillna(False).astype(bool) for i in range(14)})
    exits = pd.DataFrame({NAMES[i]: X[i].fillna(False).astype(bool) for i in range(14)})
    return longs, exits
