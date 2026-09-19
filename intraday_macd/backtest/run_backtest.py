# -*- coding: utf-8 -*-
"""run_backtest.py — 讀 1 分鐘 K 線 CSV, 把 13 個策略跑一遍, 輸出每個策略的回測報告。

用法:
  python3 run_backtest.py --csv SOXL_1m.csv --days 30 --out ../reports
  python3 run_backtest.py --demo --days 30 --out ../reports      # 用合成資料驗證流程 (數字不是真實市場)

CSV 需要的欄位 (TradingView 匯出即可, 欄名不分大小寫):
  time / date, open, high, low, close, volume
time 可以是 ISO 字串或 Unix 秒數; 若不帶時區, 用 --tz 指定該檔資料本身的時區。
"""
import argparse, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strategies as S
from engine import Rules, run_one

NY = "America/New_York"


def load_csv(path: str, tz: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    tcol = next((c for c in ("time", "datetime", "date", "timestamp") if c in df.columns), None)
    if tcol is None:
        sys.exit("CSV 找不到時間欄 (time / datetime / date / timestamp)")
    t = df[tcol]
    if np.issubdtype(t.dtype, np.number):
        unit = "s" if t.max() < 1e11 else "ms"
        idx = pd.to_datetime(t, unit=unit, utc=True)
    else:
        idx = pd.to_datetime(t, utc=False)
        idx = idx.dt.tz_localize(tz) if idx.dt.tz is None else idx
        idx = idx.dt.tz_convert("UTC")
    df.index = idx.dt.tz_convert(NY) if hasattr(idx, "dt") else idx.tz_convert(NY)
    need = ["open", "high", "low", "close"]
    for c in need:
        if c not in df.columns:
            sys.exit(f"CSV 缺少欄位: {c}")
    if "volume" not in df.columns:
        df["volume"] = 0.0
    out = df[need + ["volume"]].astype(float).sort_index()
    return out[~out.index.duplicated(keep="last")]


def make_demo(days: int, seed: int = 7) -> pd.DataFrame:
    """合成 1 分鐘 K 線: 只為驗證程式流程, 波動特性接近槓桿 ETF, 但不是任何真實商品。"""
    rng = np.random.default_rng(seed)
    sessions = []
    day = pd.Timestamp.now(tz=NY).normalize()
    while len(sessions) < days:
        if day.dayofweek < 5:
            sessions.append(day)
        day -= pd.Timedelta(days=1)
    idx = []
    for d in reversed(sessions):
        idx += list(pd.date_range(d + pd.Timedelta(hours=9, minutes=30), periods=390, freq="1min", tz=NY))
    n = len(idx)
    vol = 0.0022 + 0.0016 * np.exp(-np.arange(390) / 60.0)
    step = rng.normal(0, np.tile(vol, n // 390 + 1)[:n]) + rng.normal(0, 0.0004, n)
    px = 30.0 * np.exp(np.cumsum(step))
    hi = px * (1 + np.abs(rng.normal(0, 0.0011, n)))
    lo = px * (1 - np.abs(rng.normal(0, 0.0011, n)))
    op = np.r_[px[0], px[:-1]]
    return pd.DataFrame(dict(open=op, high=np.maximum(hi, np.maximum(op, px)),
                             low=np.minimum(lo, np.minimum(op, px)), close=px,
                             volume=rng.lognormal(11, 0.6, n)), index=pd.DatetimeIndex(idx))


def add_session(df: pd.DataFrame, start="09:30", end="16:00", no_entry="15:45", eod="15:58") -> pd.DataFrame:
    t = df.index.tz_convert(NY).time
    to_min = lambda s: int(s[:2]) * 60 + int(s[3:])
    mins = np.array([x.hour * 60 + x.minute for x in t])
    df = df.copy()
    df["in_sess"] = (mins >= to_min(start)) & (mins < to_min(end))
    day = df.index.tz_convert(NY).normalize()
    df["new_sess"] = df.in_sess & (pd.Series(day, index=df.index) != pd.Series(day, index=df.index).shift(1))
    df["eod"] = df.in_sess & (mins >= to_min(eod))
    df["block_new"] = df.in_sess & (mins >= to_min(no_entry))
    return df


def apply_window(df: pd.DataFrame, days: int, start: str, end: str) -> pd.DataFrame:
    df = df.copy()
    if start or end:
        lo = pd.Timestamp(start, tz=NY) if start else df.index[0]
        hi = pd.Timestamp(end, tz=NY) if end else df.index[-1]
    else:
        hi = df.index[-1]
        lo = hi - pd.Timedelta(days=days)
    df["in_window"] = (df.index >= lo) & (df.index <= hi)
    df["entry_ok"] = df.in_window & df.in_sess & ~df.block_new & ~df.eod
    return df


def baselines(df: pd.DataFrame) -> dict:
    w = df[df.in_window & df.in_sess]
    if w.empty:
        return dict(bh=0.0, max_rise=0.0, bars=0, days=0, first=None, last=None)
    run_min = w.low.cummin()
    return dict(bh=(w.close.iloc[-1] / w.open.iloc[0] - 1.0) * 100.0,
                max_rise=((w.high - run_min) / run_min * 100.0).max(),
                bars=len(w), days=w.index.normalize().nunique(),
                first=w.index[0], last=w.index[-1])


def fmt(x, d=2, suffix=""):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:,.{d}f}{suffix}"


def build_report(results, base, rules, meta) -> str:
    rows = sorted(results, key=lambda r: -r.stats["total_ret"])
    L = []
    L.append(f"# 多策略同場回測報告 · {meta['symbol']} · {meta['tf']}")
    L.append("")
    L.append(f"- 資料來源: {meta['source']}")
    L.append(f"- 回測窗口: {base['first']} → {base['last']} ({base['days']} 個交易日 / {base['bars']:,} 根 K)")
    L.append(f"- 共用成本: 手續費 {rules.comm_pct}%/邊 · 滑點 {rules.slip_ticks} tick · "
             f"固定止損 {'開 ' + str(rules.stop_pct) + '%' if rules.use_stop else '關'}")
    L.append(f"- 共用規則: 只做多 · 全部本金 · 收盤確認下一根開盤成交 · 15:45 後不開新倉 · 15:58 強制平倉")
    L.append(f"- 基準: 買入持有 **{fmt(base['bh'])}%** · 期內最大昇幅 **{fmt(base['max_rise'])}%**")
    L.append("")
    L.append("## 一、策略比較表 (按總報酬排名)")
    L.append("")
    L.append("| 排名 | 策略 | 交易 | 勝率 | 總報酬% | 最大回撤% | 獲利因子 | 平均每筆% | 最佳/最差% | 平均持倉分 | 捕獲率% |")
    L.append("|---:|:---|---:|---:|---:|---:|---:|---:|:---:|---:|---:|")
    for i, r in enumerate(rows, 1):
        s = r.stats
        cap = s["total_ret"] / base["max_rise"] * 100.0 if base["max_rise"] else np.nan
        L.append(f"| {i} | {r.name} | {s['trades']} | {fmt(s['win_rate'],1,'%')} | {fmt(s['total_ret'])} | "
                 f"{fmt(s['max_dd'])} | {fmt(s['profit_factor'])} | {fmt(s['avg_ret'],3)} | "
                 f"{fmt(s['best'],1)} / {fmt(s['worst'],1)} | {fmt(s['avg_bars'],1)} | {fmt(cap,1)} |")
    L.append(f"| — | **B&H 買入持有** | 1 | — | **{fmt(base['bh'])}** | — | — | — | — | — | "
             f"{fmt(base['bh']/base['max_rise']*100 if base['max_rise'] else np.nan,1)} |")
    L.append("")
    placebo = next((r for r in rows if r.name.startswith("S13")), None)
    if placebo:
        rank = rows.index(placebo) + 1
        better = [r.name for r in rows[:rank - 1]]
        L.append(f"> **安慰劑判讀**: 隨機進場排第 {rank}。排在它上面的 {len(better)} 個策略才算在這段資料上有優勢:"
                 f" {', '.join(better) if better else '沒有'}。排在它下面的, 表現還不如亂買。")
        L.append("")
    L.append("## 二、逐策略明細")
    L.append("")
    for i, r in enumerate(rows, 1):
        s = r.stats
        L.append(f"### {i}. {r.name}")
        L.append("")
        L.append(f"| 指標 | 值 | 指標 | 值 |")
        L.append(f"|:---|---:|:---|---:|")
        L.append(f"| 交易次數 | {s['trades']} | 勝率 | {fmt(s['win_rate'],1,'%')} |")
        L.append(f"| 總報酬 | {fmt(s['total_ret'],2,'%')} | 最大回撤 | {fmt(s['max_dd'],2,'%')} |")
        L.append(f"| 獲利因子 | {fmt(s['profit_factor'])} | 期望值/筆 | {fmt(s['expectancy'],3,'%')} |")
        L.append(f"| 平均獲利筆 | {fmt(s['avg_win'],3,'%')} | 平均虧損筆 | {fmt(s['avg_loss'],3,'%')} |")
        L.append(f"| 最佳一筆 | {fmt(s['best'],2,'%')} | 最差一筆 | {fmt(s['worst'],2,'%')} |")
        L.append(f"| 平均持倉 | {fmt(s['avg_bars'],1)} 根 | 最長連勝/連敗 | {s['max_win_streak']} / {s['max_loss_streak']} |")
        L.append("")
        if s["trades"] >= 5:
            t = r.trades.copy()
            t["hour"] = pd.DatetimeIndex(t.entry_time).tz_convert(NY).hour
            byh = t.groupby("hour").agg(筆數=("ret_pct", "size"), 勝率=("ret_pct", lambda x: (x > 0).mean() * 100),
                                        合計報酬=("ret_pct", "sum"))
            L.append("分時段表現 (進場小時, 紐約時間):")
            L.append("")
            L.append("| 小時 | 筆數 | 勝率% | 合計報酬% |")
            L.append("|---:|---:|---:|---:|")
            for hh, row in byh.iterrows():
                L.append(f"| {hh:02d} | {int(row['筆數'])} | {row['勝率']:.1f} | {row['合計報酬']:.2f} |")
            L.append("")
        L.append("")
    L.append("## 三、怎麼讀這份報告")
    L.append("")
    L.append("1. **先看安慰劑那一行**。贏不過 S13 隨機進場的策略, 不必再調參數。")
    L.append("2. **交易次數少於 30 筆的勝率沒有統計意義**。30 筆時 ±18 個百分點都在誤差範圍內。")
    L.append("3. **獲利因子低於 1 就是賠錢**, 勝率再高也一樣 — 代表輸的那幾筆把贏的全吃掉。")
    L.append("4. **捕獲率**是總報酬除以期內最大昇幅。低於 20% 代表大部分行情沒吃到。")
    L.append("5. **一個月的結果不能當結論**。換一個月重跑, 排名大幅變動的策略就是在擬合雜訊。")
    return "\n".join(L)


def to_html(md: str, title: str) -> str:
    import html as _h
    body = []
    in_tbl = False
    for line in md.split("\n"):
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            if not in_tbl:
                body.append("<table>")
                in_tbl = True
                tag = "th"
            else:
                tag = "td"
            body.append("<tr>" + "".join(f"<{tag}>{_h.escape(c).replace('**','')}</{tag}>" for c in cells) + "</tr>")
            continue
        if in_tbl:
            body.append("</table>")
            in_tbl = False
        if line.startswith("### "):
            body.append(f"<h3>{_h.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            body.append(f"<h2>{_h.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            body.append(f"<h1>{_h.escape(line[2:])}</h1>")
        elif line.startswith("> "):
            body.append(f"<blockquote>{_h.escape(line[2:])}</blockquote>")
        elif line.startswith("- ") or line.startswith("1. ") or line[:2].isdigit():
            body.append(f"<p>{_h.escape(line.lstrip('-0123456789. '))}</p>")
        elif line.strip():
            body.append(f"<p>{_h.escape(line)}</p>")
    if in_tbl:
        body.append("</table>")
    css = ("body{font:14px/1.6 -apple-system,'PingFang TC','Microsoft JhengHei',sans-serif;max-width:1100px;"
           "margin:32px auto;padding:0 16px;color:#1a1a1a;background:#fff}"
           "h1{font-size:22px}h2{font-size:18px;margin-top:32px;border-bottom:2px solid #eee;padding-bottom:6px}"
           "h3{font-size:15px;margin-top:24px}table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13px}"
           "th,td{border:1px solid #ddd;padding:5px 8px;text-align:right}th{background:#f5f6f8;font-weight:600}"
           "td:nth-child(2),th:nth-child(2){text-align:left}blockquote{border-left:3px solid #f0a;margin:12px 0;"
           "padding:8px 14px;background:#fff7fb}"
           "@media(prefers-color-scheme:dark){body{background:#14161a;color:#e6e6e6}th{background:#22262d}"
           "th,td{border-color:#343a44}blockquote{background:#2a1b24}}")
    return f"<!doctype html><html lang='zh-Hant'><meta charset='utf-8'><title>{_h.escape(title)}</title>" \
           f"<meta name='viewport' content='width=device-width,initial-scale=1'><style>{css}</style>" + "\n".join(body) + "</html>"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--symbol", default="SOXL")
    ap.add_argument("--tf", default="1 分鐘")
    ap.add_argument("--tz", default=NY)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--start", default="")
    ap.add_argument("--end", default="")
    ap.add_argument("--comm", type=float, default=0.03)
    ap.add_argument("--slip", type=int, default=2)
    ap.add_argument("--stop", type=float, default=0.0, help="固定止損 %, 0 = 關閉")
    ap.add_argument("--out", default="../reports")
    a = ap.parse_args()

    if a.demo:
        df = make_demo(max(a.days, 5))
        source = "⚠ 合成示範資料 (非真實市場) — 只用來驗證程式流程"
    elif a.csv:
        df = load_csv(a.csv, a.tz)
        source = os.path.basename(a.csv)
    else:
        sys.exit("請給 --csv <檔案> 或 --demo")

    df = apply_window(add_session(df), a.days, a.start, a.end)
    base = baselines(df)
    if base["bars"] == 0:
        sys.exit("窗口內沒有盤中 K 線 — 檢查 --days / --start / --end 與資料時區")
    longs, exits = S.build_signals(df)
    rules = Rules(comm_pct=a.comm, slip_ticks=a.slip, use_stop=a.stop > 0, stop_pct=a.stop or 1.5)
    results = [run_one(df, longs[n], exits[n], n, rules) for n in S.NAMES]

    meta = dict(symbol=a.symbol, tf=a.tf, source=source)
    md = build_report(results, base, rules, meta)
    os.makedirs(a.out, exist_ok=True)
    stem = os.path.join(a.out, f"report_{a.symbol}_{a.days}d")
    open(stem + ".md", "w", encoding="utf-8").write(md)
    open(stem + ".html", "w", encoding="utf-8").write(to_html(md, f"{a.symbol} 多策略回測報告"))
    for r in results:
        if len(r.trades):
            r.trades.to_csv(os.path.join(a.out, f"trades_{r.name.split()[0]}.csv"), index=False)
    print(md.split("## 二、")[0])
    print(f"→ {stem}.md")
    print(f"→ {stem}.html")


if __name__ == "__main__":
    main()
