# -*- coding: utf-8 -*-
"""open5_winrate.py — 只做開市頭 N 分鐘: 盤前上昇 / 下跌 → 順勢還是逆勢? 甚麼出場規則勝率最高?

回答的問題:
  · 盤前上昇的日子, 開市頭 5 分鐘【順勢做多】與【逆勢做空】哪一個勝率高? 期望值呢?
  · 盤前跌幅多大才值得做? (依盤前幅度分檔)
  · 出場規則怎麼訂: 固定時間出場 / 目標停利 / 停損 — 哪一組勝率最高, 哪一組期望值最高?
  · 勝率與期望值的取捨長甚麼樣?

【兩個必須先知道的前提】
1. 盤前資料預設不在 TradingView 匯出的 CSV 裡。要有盤前, 圖表必須先開「延長交易時段」
   (圖表設定 → 交易時段 → 勾選延長時段), 再 Export chart data。
   沒有盤前資料時, 本程式自動退回用【跳空】當代理: 09:30 開盤價相對前一交易日收盤的變動,
   並在報告中明講用了哪一種。兩者不同: 跳空只是盤前走勢的「最後結果」, 看不到盤前的路徑與反覆。
2. 單純追求最大勝率會得到一個沒用的答案。目標訂得夠小、停損放得夠寬, 勝率可以輕易超過 85%,
   但扣掉手續費與滑點後期望值是負的。本程式一律把【勝率】與【每筆期望值】並列, 並附 Wilson
   95% 信賴區間, 讓你在取捨曲線上自己挑點, 而不是被單一數字騙。

用法:
  python3 open5_winrate.py --csv SOXL_1m.csv --days 180 --out ../reports
  python3 open5_winrate.py --csv SOXL_1m_eth.csv --days 180 --premkt-from 04:00 --out ../reports
  python3 open5_winrate.py --demo --days 120 --out ../reports          # 合成資料, 只驗證流程

同一根 K 同時觸及目標與停損時, 一律當作【先觸及停損】(保守假設; 1 分 K 看不出先後)。
"""
import argparse, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_backtest import load_csv, make_demo, NY
from intraday_pattern import CSS, JS, _tbl, _chart_div, wilson, m2s, s2m, detect_tf

SESS_OPEN = 9 * 60 + 30


def prep(df: pd.DataFrame, premkt_from: str) -> pd.DataFrame:
    """每個交易日一行: 盤前訊號 + 開市窗口內的逐分鐘路徑所需欄位。"""
    idx = df.index.tz_convert(NY)
    d = pd.DataFrame(index=df.index)
    d["day"] = idx.normalize()
    d["min"] = [t.hour * 60 + t.minute for t in idx.time]
    d["reg"] = (d["min"] >= SESS_OPEN) & (d["min"] < 16 * 60)
    d["pre"] = (d["min"] >= s2m(premkt_from)) & (d["min"] < SESS_OPEN)
    return pd.concat([df, d], axis=1)


def daily(dfx: pd.DataFrame, win_min: int) -> tuple:
    rows, prev_close, has_eth = [], None, False
    for day, g in dfx.groupby("day"):
        reg = g[g.reg]
        if len(reg) < 300:                       # 半日市 / 資料不全
            continue
        pre = g[g.pre]
        o930 = float(reg.open.iloc[0])
        gap = np.nan if not prev_close else (o930 / prev_close - 1) * 100
        pre_pct = np.nan
        if len(pre) >= 5 and prev_close:
            has_eth = True
            pre_pct = (float(pre.close.iloc[-1]) / prev_close - 1) * 100
        w = reg[reg["min"] < SESS_OPEN + win_min]
        rows.append(dict(
            date=day.date(), prev_close=prev_close, open=o930, gap_pct=gap, premkt_pct=pre_pct,
            pre_bars=len(pre),
            w_high=float(w.high.max()), w_low=float(w.low.min()), w_close=float(w.close.iloc[-1]),
            highs=w.high.to_numpy(float), lows=w.low.to_numpy(float), closes=w.close.to_numpy(float),
            path=((w.close.to_numpy(float) / o930 - 1) * 100),
            day_close=float(reg.close.iloc[-1]),
        ))
        prev_close = float(reg.close.iloc[-1])
    return pd.DataFrame(rows), has_eth


def simulate(r, side: int, tgt: float, stp: float, comm: float, slip_tk: float, mintick: float) -> tuple:
    """回傳 (報酬%, 出場原因)。side: +1 做多, -1 做空。tgt/stp <= 0 表示不設, 只做時間出場。
    保守假設: 同一根 K 同時觸及兩者, 算停損先到。"""
    slip = slip_tk * mintick
    entry = r["open"] + side * slip                       # 進場滑價往不利方向
    tp = entry * (1 + side * tgt / 100) if tgt > 0 else None
    sl = entry * (1 - side * stp / 100) if stp > 0 else None
    exit_px, why = None, "時間"
    for hi, lo in zip(r["highs"], r["lows"]):
        if sl is not None and ((side > 0 and lo <= sl) or (side < 0 and hi >= sl)):
            exit_px, why = sl, "停損"
            break
        if tp is not None and ((side > 0 and hi >= tp) or (side < 0 and lo <= tp)):
            exit_px, why = tp, "停利"
            break
    if exit_px is None:
        exit_px = r["closes"][-1]
    exit_px -= side * slip                                 # 出場滑價往不利方向
    ret = (exit_px / entry - 1) * 100 * side - 2 * comm
    return ret, why


def bucket(v, lo, hi):
    if not np.isfinite(v):
        return None
    if v >= hi:
        return "大幅上昇"
    if v >= lo:
        return "小幅上昇"
    if v > -lo:
        return "持平"
    if v > -hi:
        return "小幅下跌"
    return "大幅下跌"


def run_grid(f: pd.DataFrame, sig_col: str, lo: float, hi: float, tgts, stps, comm, slip, mintick, min_n: int):
    out = []
    f = f[f[sig_col].notna()].copy()
    f["bk"] = [bucket(v, lo, hi) for v in f[sig_col]]
    for bk, g in f.groupby("bk"):
        if len(g) < min_n:
            continue
        for dname, side_fn in (("順勢", lambda v: 1 if v > 0 else -1), ("逆勢", lambda v: -1 if v > 0 else 1)):
            for tgt in tgts:
                for stp in stps:
                    rets, whys = [], []
                    for _, r in g.iterrows():
                        s = side_fn(r[sig_col])
                        ret, why = simulate(r, s, tgt, stp, comm, slip, mintick)
                        rets.append(ret); whys.append(why)
                    a = np.array(rets)
                    n = len(a); w = int((a > 0).sum())
                    wl, wh = wilson(w, n)
                    win, loss = a[a > 0], a[a <= 0]
                    out.append(dict(
                        盤前=bk, 方向=dname, 停利=tgt if tgt > 0 else np.nan, 停損=stp if stp > 0 else np.nan,
                        筆數=n, 勝率=w / n * 100, 區間低=wl, 區間高=wh,
                        期望值=a.mean(), 中位=np.median(a),
                        平均賺=win.mean() if len(win) else np.nan,
                        平均蝕=loss.mean() if len(loss) else np.nan,
                        獲利因子=(win.sum() / -loss.sum()) if len(loss) and loss.sum() < 0 else np.nan,
                        合計=a.sum(),
                        停利出場=sum(1 for x in whys if x == "停利") / n * 100,
                        停損出場=sum(1 for x in whys if x == "停損") / n * 100,
                    ))
    return pd.DataFrame(out)


def fmt_grid(g: pd.DataFrame, cols=None) -> pd.DataFrame:
    g = g.copy()
    g["停利"] = g["停利"].map(lambda v: "—" if not np.isfinite(v) else f"{v:.2f}%")
    g["停損"] = g["停損"].map(lambda v: "—" if not np.isfinite(v) else f"{v:.2f}%")
    g["勝率"] = g.apply(lambda r: f"{r['勝率']:.0f}%  ({r['區間低']:.0f}–{r['區間高']:.0f})", axis=1)
    for c in ("期望值", "中位", "平均賺", "平均蝕", "合計"):
        g[c] = g[c].round(3)
    g["獲利因子"] = g["獲利因子"].round(2)
    for c in ("停利出場", "停損出場"):
        g[c] = g[c].round(0)
    keep = cols or ["盤前", "方向", "停利", "停損", "筆數", "勝率", "期望值", "獲利因子", "平均賺", "平均蝕", "停利出場", "停損出場"]
    return g[keep].set_index("盤前")


def build(f, grid, sig_col, has_eth, meta) -> str:
    P = []
    src_txt = ("盤前實際走勢 (" + meta["premkt_from"] + " → 09:30, 需圖表開啟延長交易時段)") if has_eth \
        else "跳空代理 (09:30 開盤 vs 前一交易日收盤) — 匯出的 CSV 裡沒有盤前 K 線"
    P.append(f"<h1>{meta['symbol']} · 只做開市頭 {meta['win_min']} 分鐘</h1>")
    P.append(f"<p class='muted'>資料 {meta['source']} · {meta['n']} 個交易日 · {meta['first']} → {meta['last']} · "
             f"{meta['tf']} 分鐘 K · 成本 {meta['comm']}%/邊 + 滑點 {meta['slip']} tick</p>")
    P.append(f"<p class='muted'><b>盤前訊號來源:</b> {src_txt}</p>")
    if not has_eth:
        P.append("<div class='warn'><b>沒有盤前 K 線, 用跳空代理。</b>兩者不同: 跳空只是盤前走勢的最後結果, "
                 "看不到盤前的路徑與反覆。要真正的盤前訊號, 到圖表設定 → 交易時段 → 勾選【延長交易時段】, "
                 "再 Export chart data 重跑。</div>")
    if meta["n"] < 100:
        P.append(f"<div class='warn'><b>樣本 {meta['n']} 天太少。</b>再切成 5 檔 × 2 方向 × 多組出場, 每格剩不到 10 筆。"
                 "下面每個勝率都附 Wilson 95% 區間, 你會看到區間寬到沒有資訊量。這種分析至少要 1 年, 2-3 年才穩。</div>")

    P.append("""<div class='card'><h2>① 先看清楚: 勝率不是目標</h2>
<p>把停利訂得夠小、停損放得夠寬, 勝率一定高 — 因為小幅波動幾乎必然先碰到近的那一邊。但每次賺一點點、
輸一次吃掉十次, 扣掉成本後期望值是負的。下表兩欄要一起看:</p>
<p><b>勝率</b> = 賺錢的筆數比例。<b>期望值</b> = 每筆平均賺多少 % (已扣手續費與滑點)。
只有<b>期望值為正</b>的組合才有意義; 在期望值為正的前提下, 再挑勝率高的, 那才是「最大勝率」的正確問法。</p></div>""")

    if len(grid) == 0:
        P.append("<div class='card'><p>樣本不足, 沒有任何一檔達到最低筆數要求。</p></div>")
    else:
        pos = grid[grid["期望值"] > 0].sort_values("勝率", ascending=False)
        P.append("<div class='card'><h2>② 期望值為正的組合中, 勝率最高的前 15 組</h2>"
                 "<p class='muted'>這才是「如何做到最大勝率」的答案。括號是 Wilson 95% 信賴區間 — "
                 "區間下緣低於 50% 就代表這個勝率跟擲銅板分不開。</p>"
                 + (_tbl(fmt_grid(pos.head(15)), "盤前") if len(pos) else
                    "<p>這段資料裡<b>沒有任何一組期望值為正</b>。這本身就是結論: 在這段期間、這個成本之下, "
                    "開市頭幾分鐘的順勢或逆勢都不划算。</p>") + "</div>")

        best = grid.sort_values("期望值", ascending=False)
        P.append("<div class='card'><h2>③ 期望值最高的前 15 組</h2>"
                 "<p class='muted'>期望值決定長期賺賠, 勝率只決定心理舒適度。兩張表的第一名通常不是同一組。</p>"
                 + _tbl(fmt_grid(best.head(15)), "盤前") + "</div>")

        hi = grid.sort_values("勝率", ascending=False)
        P.append("<div class='card'><h2>④ 單純勝率最高的前 10 組 (不管期望值)</h2>"
                 "<p class='muted'>放這張表是為了讓你看見陷阱: 勝率最高的那幾組, 期望值那一欄長甚麼樣。</p>"
                 + _tbl(fmt_grid(hi.head(10)), "盤前") + "</div>")

        # 取捨圖: 勝率 vs 期望值, 順勢 / 逆勢兩條
        xs, ser = [], []
        for dname, col in (("順勢", "var(--c1)"), ("逆勢", "var(--c2)")):
            sub = grid[grid["方向"] == dname].sort_values("勝率")
            if len(sub) == 0:
                continue
            ser.append(dict(name=dname, y=sub["期望值"].round(3).tolist(), color=col))
            xs = [f"{v:.0f}%" for v in sub["勝率"]] if len(sub["勝率"]) > len(xs) else xs
        if ser:
            ln = min(len(s["y"]) for s in ser)
            for s in ser:
                s["y"] = s["y"][:ln]
            P.append("<div class='card'><h2>⑤ 勝率與期望值的取捨</h2>"
                     "<p class='muted'>橫軸是勝率 (由低到高), 縱軸是每筆期望值 %。線往右下走 = 勝率愈高、期望值愈差, "
                     "那就是被小停利大停損騙了。</p>"
                     + _chart_div("勝率 vs 期望值", xs[:ln], ser) + "</div>")

        by = grid.groupby(["盤前", "方向"]).agg(組數=("筆數", "size"), 平均期望值=("期望值", "mean"),
                                              最佳期望值=("期望值", "max"), 平均勝率=("勝率", "mean")).round(3)
        P.append("<div class='card'><h2>⑥ 依盤前幅度分檔的總覽</h2>"
                 "<p class='muted'>每一檔 × 方向, 在所有出場組合上的平均表現。用來看「盤前上昇該順勢還是逆勢」這個大方向。</p>"
                 + _tbl(by, "盤前 / 方向") + "</div>")

    # 每日明細
    cols = ["date", "premkt_pct", "gap_pct", "open", "w_high", "w_low", "w_close"]
    hdr = ["日期", "盤前%", "跳空%", "09:30 開盤", f"窗內最高", "窗內最低", f"+{meta['win_min']}分收盤"]
    tr = []
    for _, r in f.iterrows():
        tds = []
        for c in cols[1:]:
            v = r[c]
            if c.endswith("_pct"):
                cls = ' class="pos"' if np.isfinite(v) and v > 0 else (' class="neg"' if np.isfinite(v) and v < 0 else "")
                tds.append(f"<td{cls}>{'—' if not np.isfinite(v) else f'{v:.2f}'}</td>")
            else:
                tds.append(f"<td>{v:.2f}</td>")
        tr.append(f"<tr><td>{r['date']}</td>{''.join(tds)}</tr>")
    P.append("<div class='card'><h2>⑦ 每日明細</h2><details><summary>展開 / 收起</summary><div class='tw'><table><tr>"
             + "".join(f"<th>{h}</th>" for h in hdr) + "</tr>" + "".join(tr) + "</table></div></details></div>")

    P.append(f"""<div class='card'><h2>⑧ 方法與限制</h2>
<p><b>進場</b>: 09:30 開盤價, 加一個滑點往不利方向。<b>出場</b>: 窗口內先觸及停利或停損就出, 都沒碰到就在
第 {meta['win_min']} 分鐘收盤出。同一根 K 同時觸及兩者, 一律算<b>停損先到</b> (1 分 K 看不出先後, 保守處理)。</p>
<p><b>成本</b>: 每邊 {meta['comm']}% 手續費 + {meta['slip']} tick 滑點, 進出各一次。開市頭幾分鐘是全日價差最闊、
滑點最大的時候, 實際成交多半比這裡假設的差。</p>
<p><b>沒有涵蓋</b>: 真實的排隊與部分成交; 開盤集合競價的跳動; 停牌; 借券成本 (做空那一半);
盤前流動性不足造成的假訊號。</p>
<p><b>怎麼用結論</b>: 先確認期望值為正的組合存不存在。存在的話, 看它的筆數與信賴區間夠不夠硬,
再換另一段期間重跑一次 — 換期間就翻盤的組合是在擬合雜訊。</p></div>""")
    body = "\n".join(P)
    return (f"<!doctype html><html lang='zh-Hant'><meta charset='utf-8'>"
            f"<title>{meta['symbol']} 開市頭 {meta['win_min']} 分鐘勝率分析</title>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<style>{CSS}</style><body class='viz'><div class='wrap'>{body}</div><script>{JS}</script></body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv"); ap.add_argument("--demo", action="store_true")
    ap.add_argument("--symbol", default="SOXL"); ap.add_argument("--tz", default=NY)
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--start", default=""); ap.add_argument("--end", default="")
    ap.add_argument("--win-min", type=int, default=5, help="開市後做幾分鐘")
    ap.add_argument("--premkt-from", default="04:00", help="盤前訊號起算時間 (需 CSV 含延長時段)")
    ap.add_argument("--lo", type=float, default=0.5, help="小幅 / 持平 的分界 %")
    ap.add_argument("--hi", type=float, default=1.5, help="大幅 / 小幅 的分界 %")
    ap.add_argument("--comm", type=float, default=0.03); ap.add_argument("--slip", type=int, default=2)
    ap.add_argument("--min-n", type=int, default=8, help="一檔至少要有幾天才納入")
    ap.add_argument("--out", default="../reports")
    a = ap.parse_args()

    if a.demo:
        df = make_demo(max(a.days, 30)); source = "⚠ 合成示範資料 — 只驗證流程, 數字不代表任何真實商品"
    elif a.csv:
        df = load_csv(a.csv, a.tz); source = os.path.basename(a.csv)
    else:
        sys.exit("請給 --csv <檔案> 或 --demo")

    hi_t = df.index[-1] if not (a.start or a.end) else pd.Timestamp(a.end or df.index[-1], tz=NY)
    lo_t = pd.Timestamp(a.start, tz=NY) if a.start else hi_t - pd.Timedelta(days=a.days)
    df = df[(df.index >= lo_t) & (df.index <= hi_t)]
    if df.empty:
        sys.exit("窗口內沒有資料")
    tf = detect_tf(df.assign(in_sess=True))
    dfx = prep(df, a.premkt_from)
    f, has_eth = daily(dfx, a.win_min)
    if f.empty:
        sys.exit("窗口內沒有完整的交易日")
    sig_col = "premkt_pct" if has_eth else "gap_pct"
    mintick = 0.01
    tgts = [0.0, 0.10, 0.15, 0.25, 0.40, 0.60]
    stps = [0.0, 0.15, 0.25, 0.40, 0.60, 1.00]
    grid = run_grid(f, sig_col, a.lo, a.hi, tgts, stps, a.comm, a.slip, mintick, a.min_n)

    meta = dict(symbol=a.symbol, source=source, n=len(f), first=str(f.date.iloc[0]), last=str(f.date.iloc[-1]),
                win_min=a.win_min, comm=a.comm, slip=a.slip, tf=tf, premkt_from=a.premkt_from)
    html = build(f, grid, sig_col, has_eth, meta)
    os.makedirs(a.out, exist_ok=True)
    stem = os.path.join(a.out, f"open{a.win_min}_{a.symbol}_{len(f)}d")
    open(stem + ".html", "w", encoding="utf-8").write(html)
    if len(grid):
        grid.to_csv(stem + "_grid.csv", index=False)
    print(f"{a.symbol} · {len(f)} 個交易日 · 訊號來源 {'盤前實際走勢' if has_eth else '跳空代理 (CSV 無盤前 K 線)'}")
    if len(grid):
        pos = grid[grid["期望值"] > 0]
        print(f"組合共 {len(grid)} 組, 其中期望值為正 {len(pos)} 組")
        if len(pos):
            print(pos.sort_values('勝率', ascending=False).head(5)[
                ["盤前","方向","停利","停損","筆數","勝率","期望值","獲利因子"]].round(2).to_string(index=False))
        else:
            print("※ 沒有任何一組期望值為正 — 這本身就是結論")
    print(f"→ {stem}.html")


if __name__ == "__main__":
    main()
