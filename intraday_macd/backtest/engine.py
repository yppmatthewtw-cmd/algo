# -*- coding: utf-8 -*-
"""engine.py — 逐根 K 線的回測引擎, 規則與 TradingView 版 TW-1M-MULTI 完全一致。

成交模型 (這是整份回測可不可信的關鍵):
  1. 訊號在第 t 根【收盤】確認
  2. 訂單在第 t+1 根【開盤】成交, 買進加滑點、賣出減滑點
  3. 兩邊各收一次手續費
  4. 固定止損在進場那一根之後才生效; 開盤已跌破止損價就以開盤成交 (不假設能剛好停在止損價)
只做多、每次投入全部本金、不加碼 — 所有策略共用同一套規則, 比較才公平。
"""
from dataclasses import dataclass, field
import numpy as np
import pandas as pd


@dataclass
class Rules:
    comm_pct: float = 0.03        # 單邊手續費 %
    slip_ticks: int = 2           # 單邊滑點 tick
    mintick: float = 0.01         # 最小跳動
    use_stop: bool = False
    stop_pct: float = 1.5
    hold_bars: int = 30           # 只有 S13 用
    fixed_hold_cols: tuple = ("S13 隨機進場(安慰劑)",)


@dataclass
class Result:
    name: str
    trades: pd.DataFrame
    equity: pd.Series
    stats: dict = field(default_factory=dict)


def run_one(df: pd.DataFrame, longs: pd.Series, exits: pd.Series, name: str, rules: Rules) -> Result:
    o = df.open.to_numpy(float)
    lo = df.low.to_numpy(float)
    cl = df.close.to_numpy(float)
    entry_ok = df.entry_ok.to_numpy(bool)
    eod = df.eod.to_numpy(bool)
    in_win = df.in_window.to_numpy(bool)
    L = longs.to_numpy(bool)
    X = exits.to_numpy(bool)
    n = len(o)
    slip = rules.slip_ticks * rules.mintick
    cost2 = 2.0 * rules.comm_pct / 100.0
    fixed_hold = name in rules.fixed_hold_cols

    eq = 1.0
    pos = 0
    pend = 0
    entry_px = 0.0
    entry_i = -1
    held = 0
    curve = np.full(n, 1.0)
    rows = []

    def close_trade(i, exit_px, reason):
        nonlocal eq, pos, pend, held
        r = exit_px / entry_px - 1.0 - cost2
        eq *= (1.0 + r)
        rows.append(dict(entry_i=entry_i, exit_i=i, entry_time=df.index[entry_i], exit_time=df.index[i],
                         entry_px=entry_px, exit_px=exit_px, ret_pct=r * 100.0, bars=held,
                         equity=eq, reason=reason))
        pos, pend, held = 0, 0, 0

    for i in range(n):
        if pend == 1:
            pos, entry_px, entry_i, held, pend = 1, o[i] + slip, i, 0, 0
        elif pend == -1:
            close_trade(i, o[i] - slip, "訊號")
        if rules.use_stop and pos == 1 and i > entry_i:
            stp = entry_px * (1.0 - rules.stop_pct / 100.0)
            if lo[i] <= stp:
                close_trade(i, min(o[i], stp) - slip, "止損")
        if pos == 1:
            held += 1
        curve[i] = eq * (cl[i] / entry_px - cost2) if pos == 1 else eq
        if pos == 0 and L[i] and entry_ok[i]:
            pend = 1
        elif pos == 1:
            want_exit = (held >= rules.hold_bars) if fixed_hold else bool(X[i])
            if want_exit or eod[i] or not in_win[i]:
                pend = -1

    trades = pd.DataFrame(rows)
    equity = pd.Series(curve, index=df.index)
    return Result(name=name, trades=trades, equity=equity, stats=summarise(trades, equity, df))


def summarise(trades: pd.DataFrame, equity: pd.Series, df: pd.DataFrame) -> dict:
    n = len(trades)
    ret = (equity.iloc[-1] - 1.0) * 100.0 if len(equity) else 0.0
    if n == 0:
        return dict(trades=0, win_rate=np.nan, total_ret=ret, max_dd=0.0, profit_factor=np.nan,
                    avg_ret=np.nan, best=np.nan, worst=np.nan, avg_bars=np.nan, expectancy=np.nan,
                    avg_win=np.nan, avg_loss=np.nan, max_win_streak=0, max_loss_streak=0)
    r = trades.ret_pct
    wins, losses = r[r > 0], r[r <= 0]
    dd = (1.0 - equity / equity.cummax()) * 100.0
    st = (r > 0).astype(int)
    streak_w = streak_l = cur_w = cur_l = 0
    for v in st:
        cur_w, cur_l = (cur_w + 1, 0) if v else (0, cur_l + 1)
        streak_w, streak_l = max(streak_w, cur_w), max(streak_l, cur_l)
    return dict(
        trades=n, win_rate=len(wins) / n * 100.0, total_ret=ret, max_dd=dd.max(),
        profit_factor=(wins.sum() / -losses.sum()) if len(losses) and losses.sum() < 0 else np.nan,
        avg_ret=r.mean(), best=r.max(), worst=r.min(), avg_bars=trades.bars.mean(),
        expectancy=r.mean(), avg_win=wins.mean() if len(wins) else np.nan,
        avg_loss=losses.mean() if len(losses) else np.nan,
        max_win_streak=streak_w, max_loss_streak=streak_l,
    )
