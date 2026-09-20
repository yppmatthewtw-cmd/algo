# -*- coding: utf-8 -*-
"""intraday_pattern.py — 把一段期間的日內走勢平均化, 並以「開盤後的檢查點」分類當日型態。

回答的問題:
  · 這段期間「平均的一天」長甚麼樣? (逐根 K 的平均 / 中位數路徑, 以當日開盤為 0%)
  · 以開盤後的檢查點為界, 當天走勢分成哪幾類? 每一類在檢查點之後怎麼走?
  · 開盤跳空 (gap up / gap down) 的日子有甚麼不同?
  · 檢查點出現「轉勢」的日子有甚麼不同?
  · 特定事件日 (FOMC / CPI / 盤前消息) 有甚麼不同? — 需自備事件檔

【檢查點會隨 K 線週期自動對齊 — 這件事很重要】
  使用者原本要的檢查點是 09:50-10:00。但 K 線只能在它自己的邊界上取值:
    1 分鐘圖  → 09:50-10:00 精確存在 (預設就用它)
    5 分鐘圖  → 09:50-10:00 精確存在
    10 分鐘圖 → 09:50-10:00 精確存在 (第三根 K)
    15 分鐘圖 → 09:50 不存在; 最接近的邊界是 09:45-10:00
    30 分鐘圖 → 09:50 不存在; 第一根 K 是 09:30-10:00, 第二根是 10:00-10:30
                → 等價檢查點 = 第二根 K (10:00-10:30), 開盤段 = 第一根 K (09:30-10:00)
  本程式會偵測 CSV 的實際週期, 自動把檢查點對齊到最近的 K 線邊界, 並在報告裡明講用了哪一段。
  要自己指定就用 --chk-start / --chk-end。

用法:
  python3 intraday_pattern.py --csv SOXL_30m.csv --days 30 --out ../reports
  python3 intraday_pattern.py --csv SOXL_30m.csv --days 30 --events events.csv --out ../reports

事件檔 (可選) 是一個 CSV, 至少要有 date 與 tag 兩欄; 一天可以有多行 (多個 tag):
  date,tag,note
  2026-09-17,FOMC,降息 25bp
  2026-09-11,CPI,核心通脹高於預期

所有時間都是紐約時間。價格用「該根 K 的開盤價」定位, 當日收盤用最後一根盤中 K 的收盤價。
"""
import argparse, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_backtest import load_csv, make_demo, add_session, NY

SESS_OPEN, SESS_CLOSE = 9 * 60 + 30, 16 * 60


def m2s(m: int) -> str:
    return f"{int(m) // 60:02d}:{int(m) % 60:02d}"


def s2m(s: str) -> int:
    return int(s[:2]) * 60 + int(s[3:])


def detect_tf(df: pd.DataFrame) -> int:
    """偵測 K 線週期 (分鐘): 取盤中相鄰 K 時間差的眾數。"""
    t = df[df.in_sess].index
    if len(t) < 3:
        return 1
    d = pd.Series(t).diff().dt.total_seconds().div(60).dropna()
    d = d[(d > 0) & (d <= 240)]
    return int(d.mode().iloc[0]) if len(d) else 1


def session_grid(df: pd.DataFrame) -> np.ndarray:
    """該資料實際存在的盤中 K 時點 (分鐘數), 由小到大。"""
    idx = df.index.tz_convert(NY)
    mins = np.array([t.hour * 60 + t.minute for t in idx.time])
    g = np.unique(mins[df.in_sess.to_numpy()])
    return g[(g >= SESS_OPEN) & (g < SESS_CLOSE)]


def align_checkpoint(grid: np.ndarray, want_start: int, want_end: int) -> tuple:
    """把想要的檢查點對齊到實際存在的 K 線邊界; 回傳 (開始, 結束, 是否有移動)。"""
    lo = grid[grid <= want_start]
    start = int(lo[-1]) if len(lo) else int(grid[0])
    hi = grid[grid >= want_end]
    end = int(hi[0]) if len(hi) else int(grid[-1])
    if end <= start:                       # 兩者落在同一根 K → 往後推一根
        nxt = grid[grid > start]
        end = int(nxt[0]) if len(nxt) else int(grid[-1])
    moved = (start != want_start) or (end != want_end)
    return start, end, moved


def daily_features(df: pd.DataFrame, chk_start: int, chk_end: int, min_cover: float = 0.8) -> pd.DataFrame:
    idx = df.index.tz_convert(NY)
    day = pd.Series(idx.normalize(), index=df.index)
    mins = pd.Series([t.hour * 60 + t.minute for t in idx.time], index=df.index)
    sess = df[df.in_sess]
    rows, prev_close = [], None
    for d, g in sess.groupby(day[df.in_sess]):
        m = mins.loc[g.index]

        def px(mark, how="open"):
            sel = g[m == mark]
            if len(sel):
                return float(sel[how].iloc[0])
            after = g[m >= mark]
            return float(after[how].iloc[0]) if len(after) else np.nan

        o = float(g.open.iloc[0])
        p0, p1 = px(chk_start), px(chk_end)
        c = float(g.close.iloc[-1])
        post = g[m >= chk_end]
        rows.append(dict(
            date=d.date(), bars=len(g), prev_close=prev_close, open=o,
            gap_pct=np.nan if not prev_close else (o / prev_close - 1) * 100,
            leg1_pct=(p0 / o - 1) * 100,
            chk_pct=(p1 / p0 - 1) * 100,
            rest_pct=(c / p1 - 1) * 100,
            day_pct=(c / o - 1) * 100,
            mfe_pct=(post.high.max() / p1 - 1) * 100 if len(post) else np.nan,
            mae_pct=(post.low.min() / p1 - 1) * 100 if len(post) else np.nan,
            hi_time=g.high.idxmax().tz_convert(NY).strftime("%H:%M"),
            lo_time=g.low.idxmin().tz_convert(NY).strftime("%H:%M"),
            range_pct=(g.high.max() / g.low.min() - 1) * 100,
        ))
        prev_close = c
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    full = out.bars.mode().iloc[0]
    dropped = out[out.bars < full * min_cover]
    out = out[out.bars >= full * min_cover].reset_index(drop=True)   # 半日市 / 缺資料的日子剔除
    out.attrs["dropped"] = list(dropped.date.astype(str))
    out.attrs["bars_per_day"] = int(full)
    return out


def intraday_matrix(df: pd.DataFrame, dates, grid: np.ndarray) -> tuple:
    """每列一天, 值 = 相對當日開盤的 % 變化, 欄對齊到 grid。"""
    idx = df.index.tz_convert(NY)
    day = pd.Series(idx.normalize().date, index=df.index)
    mins = pd.Series([t.hour * 60 + t.minute for t in idx.time], index=df.index)
    keep, rows, used = set(dates), [], []
    for d, g in df[df.in_sess].groupby(day[df.in_sess]):
        if d not in keep:
            continue
        s = pd.Series(g.open.to_numpy(), index=mins.loc[g.index].to_numpy())
        s = s[~s.index.duplicated(keep="first")].reindex(grid).ffill().bfill()
        rows.append(((s / s.iloc[0] - 1) * 100).to_numpy())
        used.append(d)
    return np.array(rows), used


def kmeans(X: np.ndarray, k: int, seed: int = 0, iters: int = 120):
    """k-means++ 初始化的簡單 k-means (不引入額外相依套件)。"""
    rng = np.random.default_rng(seed)
    n = len(X)
    cent = [X[rng.integers(n)]]
    for _ in range(k - 1):
        d2 = ((X[:, None, :] - np.array(cent)[None]) ** 2).sum(-1).min(axis=1)
        p = d2 / d2.sum() if d2.sum() > 0 else np.full(n, 1 / n)
        cent.append(X[rng.choice(n, p=p)])
    C, lab = np.array(cent, dtype=float), np.full(n, -1)
    for _ in range(iters):
        new = np.argmin(((X[:, None, :] - C[None]) ** 2).sum(-1), axis=1)
        if (new == lab).all():
            break
        lab = new
        for j in range(k):
            if (lab == j).any():
                C[j] = X[lab == j].mean(0)
    order = np.argsort([-X[lab == j][:, -1].mean() if (lab == j).any() else 0 for j in range(k)])
    remap = {int(o): i for i, o in enumerate(order)}
    return np.array([remap[int(l)] for l in lab]), C[order]


def name_cluster(curve: np.ndarray) -> str:
    """給一條平均路徑一個看得懂的名字。"""
    end, mx, mn = curve[-1], curve.max(), curve.min()
    i_mx, i_mn = int(curve.argmax()), int(curve.argmin())
    half = len(curve) // 2
    if end > 0 and mn > -abs(end) * 0.5:
        return "單邊向上"
    if end < 0 and mx < abs(end) * 0.5:
        return "單邊向下"
    if i_mx < half and end < mx - abs(mx - mn) * 0.5:
        return "早段衝高後回吐"
    if i_mn < half and end > mn + abs(mx - mn) * 0.5:
        return "早段下殺後回升"
    return "區間震盪"


def classify(f: pd.DataFrame, chk_q: float, gap_hi: float, gap_lo: float) -> pd.DataFrame:
    f = f.copy()
    thr = float(np.nanquantile(f.chk_pct.abs(), chk_q))
    same = np.sign(f.chk_pct) == np.sign(f.leg1_pct)
    big = f.chk_pct.abs() >= thr
    f["chk_type"] = np.where(~big, "橫行", np.where(same, "延續", "轉勢"))
    f["gap_type"] = pd.cut(f.gap_pct, [-np.inf, -gap_hi, -gap_lo, gap_lo, gap_hi, np.inf],
                           labels=["大幅低開", "小幅低開", "平開", "小幅高開", "大幅高開"])
    f["leg1_dir"] = np.where(f.leg1_pct >= 0, "開盤上衝", "開盤下殺")
    f.attrs["chk_thr"] = thr
    return f


def agg(f: pd.DataFrame, by) -> pd.DataFrame:
    g = f.groupby(by, observed=True)
    return pd.DataFrame({
        "天數": g.size(),
        "檢查點後平均%": g.rest_pct.mean(),
        "檢查點後中位%": g.rest_pct.median(),
        "上漲比例%": g.rest_pct.apply(lambda x: (x > 0).mean() * 100),
        "平均最大昇%": g.mfe_pct.mean(),
        "平均最大跌%": g.mae_pct.mean(),
        "全日平均%": g.day_pct.mean(),
        "日振幅%": g.range_pct.mean(),
    }).round(2)


def wilson(k: int, n: int, z: float = 1.96) -> tuple:
    """勝率的 Wilson 95% 信賴區間 — 樣本少時用來提醒不要過度解讀。"""
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h) * 100, min(1.0, c + h) * 100)


# ═══════════════════════════ 報告 ═══════════════════════════
PAL_L = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
PAL_D = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"]

CSS = """
.viz{color-scheme:light;--s1:#fcfcfb;--s2:#f3f2ef;--tp:#0b0b0b;--ts:#52514e;--tm:#83817b;--ln:#e0ded8;
--c1:#2a78d6;--c2:#eb6834;--c3:#1baf7a;--c4:#eda100;--c5:#e87ba4;--pos:#008300;--neg:#e34948}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme=light])) .viz{color-scheme:dark;
--s1:#1a1a19;--s2:#232321;--tp:#fff;--ts:#c3c2b7;--tm:#8f8e86;--ln:#343330;
--c1:#3987e5;--c2:#d95926;--c3:#199e70;--c4:#c98500;--c5:#d55181;--pos:#5bcb7c;--neg:#e66767}}
:root[data-theme=dark] .viz{color-scheme:dark;--s1:#1a1a19;--s2:#232321;--tp:#fff;--ts:#c3c2b7;--tm:#8f8e86;--ln:#343330;
--c1:#3987e5;--c2:#d95926;--c3:#199e70;--c4:#c98500;--c5:#d55181;--pos:#5bcb7c;--neg:#e66767}
*{box-sizing:border-box}
body{margin:0;overflow-x:hidden;background:var(--s1);color:var(--tp);font:15px/1.6 -apple-system,"PingFang TC","Microsoft JhengHei","Noto Sans TC",system-ui,sans-serif;padding:28px 16px 64px}
.wrap{max-width:1000px;margin:0 auto;display:grid;grid-template-columns:minmax(0,1fr);gap:26px}
.wrap>*,.card,.tw,details{min-width:0}
h1{font-size:21px;margin:0 0 4px}h2{font-size:17px;margin:0 0 4px;padding-bottom:6px;border-bottom:1px solid var(--ln)}
h3{font-size:14px;margin:18px 0 6px;color:var(--ts)}
p{margin:0 0 8px}.muted{color:var(--ts);font-size:13.5px}
.card{background:var(--s2);border:1px solid var(--ln);border-radius:10px;padding:16px 18px}
.warn{border-left:4px solid var(--c4);background:var(--s2);padding:12px 14px;border-radius:6px;font-size:14px}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;min-width:520px;font-size:13px;font-variant-numeric:tabular-nums;margin:8px 0}
th,td{border-bottom:1px solid var(--ln);padding:6px 8px;text-align:right}
th{color:var(--ts);font-weight:600;font-size:11.5px;letter-spacing:.04em;text-transform:uppercase}
td:first-child,th:first-child{text-align:left}
.pos{color:var(--pos)}.neg{color:var(--neg)}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13px;margin:4px 0 2px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{width:14px;height:3px;border-radius:2px;display:inline-block}
.chart{position:relative}
svg{display:block;width:100%;height:auto;overflow:visible}
.tip{position:absolute;pointer-events:none;background:var(--s1);border:1px solid var(--ln);border-radius:6px;
padding:6px 9px;font-size:12px;box-shadow:0 2px 10px rgba(0,0,0,.14);opacity:0;transition:opacity .1s;white-space:nowrap;z-index:5}
details{margin-top:8px}summary{cursor:pointer;font-size:13px;color:var(--ts)}
"""

JS = r"""
function chart(el, spec){
  const W=920,H=300,ML=52,MR=118,MT=14,MB=30;
  const xs=spec.x, series=spec.series;
  let lo=Infinity,hi=-Infinity;
  series.forEach(s=>s.y.forEach(v=>{if(v==null)return;if(v<lo)lo=v;if(v>hi)hi=v;}));
  if(!isFinite(lo)){lo=-1;hi=1;}
  const pad=(hi-lo)*0.12||0.5; lo-=pad; hi+=pad;
  const px=i=>ML+(W-ML-MR)*(xs.length<2?0:i/(xs.length-1));
  const py=v=>MT+(H-MT-MB)*(1-(v-lo)/(hi-lo));
  const ns='http://www.w3.org/2000/svg';
  const svg=document.createElementNS(ns,'svg'); svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
  svg.setAttribute('role','img'); svg.setAttribute('aria-label',spec.title||'chart');
  const mk=(t,a)=>{const e=document.createElementNS(ns,t);for(const k in a)e.setAttribute(k,a[k]);return e;};
  const ticks=5;
  for(let i=0;i<=ticks;i++){
    const v=lo+(hi-lo)*i/ticks, y=py(v);
    svg.appendChild(mk('line',{x1:ML,x2:W-MR,y1:y,y2:y,stroke:'var(--ln)','stroke-width':1}));
    const t=mk('text',{x:ML-8,y:y+4,'text-anchor':'end',fill:'var(--tm)','font-size':11}); t.textContent=v.toFixed(2)+'%';
    svg.appendChild(t);
  }
  if(lo<0&&hi>0){svg.appendChild(mk('line',{x1:ML,x2:W-MR,y1:py(0),y2:py(0),stroke:'var(--ts)','stroke-width':1.5,'stroke-dasharray':'4 3'}));}
  const step=Math.max(1,Math.ceil(xs.length/8));
  xs.forEach((lab,i)=>{if(i%step&&i!==xs.length-1)return;
    const t=mk('text',{x:px(i),y:H-8,'text-anchor':'middle',fill:'var(--tm)','font-size':11}); t.textContent=lab; svg.appendChild(t);});
  if(spec.mark!=null){
    const i=xs.indexOf(spec.mark);
    if(i>=0){svg.appendChild(mk('line',{x1:px(i),x2:px(i),y1:MT,y2:H-MB,stroke:'var(--c4)','stroke-width':1.5,'stroke-dasharray':'3 3'}));
      const t=mk('text',{x:px(i),y:MT-2,'text-anchor':'middle',fill:'var(--c4)','font-size':11}); t.textContent='檢查點'; svg.appendChild(t);}
  }
  series.forEach(s=>{
    let d='',on=false;
    s.y.forEach((v,i)=>{if(v==null){on=false;return;} d+=(on?'L':'M')+px(i)+' '+py(v); on=true;});
    svg.appendChild(mk('path',{d,fill:'none',stroke:s.color,'stroke-width':2,'stroke-linejoin':'round','stroke-linecap':'round'}));
    let li=s.y.length-1; while(li>=0&&s.y[li]==null)li--;
    if(li>=0){const t=mk('text',{x:px(li)+8,y:py(s.y[li])+4,fill:'var(--ts)','font-size':11.5}); t.textContent=s.name; svg.appendChild(t);
      svg.appendChild(mk('circle',{cx:px(li),cy:py(s.y[li]),r:3.5,fill:s.color,stroke:'var(--s2)','stroke-width':2}));}
  });
  const cross=mk('line',{x1:0,x2:0,y1:MT,y2:H-MB,stroke:'var(--tm)','stroke-width':1,opacity:0});
  svg.appendChild(cross);
  el.appendChild(svg);
  const tip=document.createElement('div'); tip.className='tip'; el.appendChild(tip);
  svg.addEventListener('pointermove',ev=>{
    const r=svg.getBoundingClientRect(), vx=(ev.clientX-r.left)/r.width*W;
    let i=Math.round((vx-ML)/((W-ML-MR)/Math.max(1,xs.length-1)));
    i=Math.max(0,Math.min(xs.length-1,i));
    cross.setAttribute('x1',px(i)); cross.setAttribute('x2',px(i)); cross.setAttribute('opacity',1);
    tip.innerHTML='<b>'+xs[i]+'</b><br>'+series.map(s=>s.y[i]==null?'':`<span style="color:${s.color}">■</span> ${s.name} ${s.y[i].toFixed(2)}%`).filter(Boolean).join('<br>');
    tip.style.opacity=1;
    const lx=px(i)/W*r.width;
    tip.style.left=Math.min(r.width-tip.offsetWidth-6,Math.max(0,lx+12))+'px'; tip.style.top='8px';
  });
  svg.addEventListener('pointerleave',()=>{cross.setAttribute('opacity',0);tip.style.opacity=0;});
}
document.querySelectorAll('[data-chart]').forEach(el=>chart(el,JSON.parse(el.dataset.chart)));
"""


def _fmt(v, d=2, suffix=""):
    return "—" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:,.{d}f}{suffix}"


def _tbl(dfa: pd.DataFrame, index_name="分類") -> str:
    h = "".join(f"<th>{c}</th>" for c in dfa.columns)
    rows = []
    for k, r in dfa.iterrows():
        tds = []
        for c in dfa.columns:
            v = r[c]
            cls = ""
            if isinstance(v, (int, float, np.floating)) and "%" in str(c) and "比例" not in str(c) and "振幅" not in str(c):
                cls = ' class="pos"' if v > 0 else (' class="neg"' if v < 0 else "")
            tds.append(f"<td{cls}>{_fmt(v) if isinstance(v,(float,np.floating)) else v}</td>")
        rows.append(f"<tr><td>{k}</td>{''.join(tds)}</tr>")
    return f"<div class='tw'><table><tr><th>{index_name}</th>{h}</tr>{''.join(rows)}</table></div>"


def _chart_div(title, xs, series, mark=None) -> str:
    import json
    leg = "".join(f'<span><i class="sw" style="background:{s["color"]}"></i>{s["name"]}</span>' for s in series)
    spec = json.dumps(dict(title=title, x=xs, series=series, mark=mark), ensure_ascii=False)
    return (f'<div class="legend">{leg}</div><div class="chart" data-chart=\'{spec.replace(chr(39), "&#39;")}\'></div>')


def build_report(f, mat, dates, grid, chk_s, chk_e, moved, tf, meta, events=None, k=3) -> str:
    import json
    xs = [m2s(int(g)) for g in grid]
    n = len(f)
    parts = []
    parts.append(f"<h1>{meta['symbol']} 日內型態分析 · {tf} 分鐘 K</h1>")
    parts.append(f"<p class='muted'>資料來源 {meta['source']} · 窗口 {meta['first']} → {meta['last']} · "
                 f"{n} 個交易日 · 每日 {f.attrs.get('bars_per_day','?')} 根 K</p>")
    chk_note = (f"檢查點 <b>{m2s(chk_s)}-{m2s(chk_e)}</b>"
                + (f" (原本要的 09:50-10:00 在 {tf} 分鐘 K 上不存在, 已對齊到最近的 K 線邊界)" if moved
                   else " (與原本要的 09:50-10:00 完全一致)"))
    parts.append(f"<p class='muted'>{chk_note} · 開盤段 = 09:30 → {m2s(chk_s)} · 檢查點後 = {m2s(chk_e)} → 收盤</p>")
    if n < 40:
        parts.append(f"<div class='warn'><b>樣本太小, 結論只能當參考。</b>{n} 個交易日分成 3 到 5 類, 每類只有幾天。"
                     f"下面所有的「上漲比例」都附了 95% 信賴區間, 你會看到區間寬到幾乎沒有資訊量。"
                     f"要得到可用的結論, 至少要 6 個月 (約 125 個交易日), 一年更好。</div>")
    if f.attrs.get("dropped"):
        parts.append(f"<p class='muted'>已剔除 K 線數不足的日子 (半日市或資料缺漏): {', '.join(f.attrs['dropped'])}</p>")

    # ① 平均的一天
    mean_c, med_c = mat.mean(0).tolist(), np.median(mat, 0).tolist()
    parts.append("<div class='card'><h2>① 平均的一天</h2>"
                 "<p class='muted'>每一天都以當日 09:30 開盤價為 0%, 再把所有日子疊起來取平均與中位數。"
                 "中位數比平均穩健, 兩條差很遠代表少數幾天的大行情在拉動平均。</p>"
                 + _chart_div("平均日內路徑", xs,
                              [dict(name="平均", y=mean_c, color="var(--c1)"),
                               dict(name="中位數", y=med_c, color="var(--c2)")], mark=m2s(chk_s))
                 + f"<p class='muted'>收盤平均 {mean_c[-1]:.2f}% · 中位數 {med_c[-1]:.2f}% · "
                   f"日振幅平均 {f.range_pct.mean():.2f}%</p></div>")

    # ② 檢查點分類
    sec = ["<div class='card'><h2>② 以檢查點分類</h2>",
           f"<p class='muted'>比較開盤段 (09:30→{m2s(chk_s)}) 與檢查點段 ({m2s(chk_s)}→{m2s(chk_e)}) 的方向: "
           f"同向 = 延續, 反向 = 轉勢, 幅度小於門檻 = 橫行。門檻取樣本內 |檢查點變動| 的第 "
           f"{int(meta['chk_q']*100)} 百分位 = {f.attrs['chk_thr']:.3f}% (資料自己決定, 不是我先射箭)。</p>"]
    order = ["延續", "轉勢", "橫行"]
    ser, rows = [], []
    for i, t in enumerate([t for t in order if (f.chk_type == t).any()]):
        sel = np.array([d in set(f[f.chk_type == t].date) for d in dates])
        ser.append(dict(name=t, y=mat[sel].mean(0).tolist(), color=f"var(--c{i+1})"))
    a = agg(f, "chk_type").reindex([t for t in order if t in f.chk_type.values])
    for t in a.index:
        s = f[f.chk_type == t]
        lo, hi = wilson(int((s.rest_pct > 0).sum()), len(s))
        rows.append((t, f"{lo:.0f}–{hi:.0f}%"))
    a["上漲比例 95%區間"] = [r[1] for r in rows]
    sec.append(_chart_div("依檢查點分類的平均路徑", xs, ser, mark=m2s(chk_s)))
    sec.append(_tbl(a, "檢查點型態"))
    sec.append("</div>")
    parts.append("".join(sec))

    # ③ 跳空分類
    gf = f[f.gap_pct.notna()]
    if len(gf):
        gser, gi = [], 0
        for t in ["大幅高開", "小幅高開", "平開", "小幅低開", "大幅低開"]:
            s = gf[gf.gap_type == t]
            if len(s) == 0:
                continue
            sel = np.array([d in set(s.date) for d in dates])
            gser.append(dict(name=f"{t} ({len(s)})", y=mat[sel].mean(0).tolist(), color=f"var(--c{gi+1})"))
            gi += 1
        parts.append("<div class='card'><h2>③ 以開盤跳空分類</h2>"
                     f"<p class='muted'>跳空 = 09:30 開盤價相對前一交易日收盤的變動。分界 ±{meta['gap_lo']}% / ±{meta['gap_hi']}% "
                     f"(SOXL 是三倍槓桿, 分界比一般股票拉寬; --gap-lo / --gap-hi 可改)。</p>"
                     + _chart_div("依跳空分類", xs, gser[:5], mark=m2s(chk_s))
                     + _tbl(agg(gf, "gap_type"), "跳空型態") + "</div>")

    # ④ 資料自己分群
    if n >= k * 3:
        lab, C = kmeans(mat, k, seed=7)
        f = f.copy()
        f["cluster"] = [int(lab[dates.index(d)]) if d in dates else -1 for d in f.date]
        names = [name_cluster(C[j]) for j in range(k)]
        cser = [dict(name=f"{names[j]} ({int((lab==j).sum())})", y=C[j].tolist(), color=f"var(--c{j+1})") for j in range(k)]
        cl = agg(f[f.cluster >= 0], "cluster")
        cl.index = [f"{names[j]}" for j in cl.index]
        parts.append("<div class='card'><h2>④ 讓資料自己分群 (k-means)</h2>"
                     f"<p class='muted'>不預設任何型態, 直接把 {n} 條日內路徑丟進 k-means 分成 {k} 群, "
                     "每群的中心就是那一類的「平均走勢」。名稱是依中心線形狀自動命名的。</p>"
                     + _chart_div("各群的平均路徑", xs, cser, mark=m2s(chk_s))
                     + _tbl(cl, "群") + "</div>")

    # ⑤ 交叉表
    if len(gf):
        ct = pd.crosstab(gf.gap_type, gf.chk_type)
        ctr = pd.crosstab(gf.gap_type, gf.chk_type, values=gf.rest_pct, aggfunc="mean").round(2)
        parts.append("<div class='card'><h2>⑤ 跳空 × 檢查點 交叉表</h2>"
                     "<h3>天數</h3>" + _tbl(ct, "跳空 \\ 檢查點")
                     + "<h3>檢查點後平均報酬 %</h3>" + _tbl(ctr, "跳空 \\ 檢查點")
                     + "<p class='muted'>格子裡多半只有 1-3 天, 不要據此下任何結論; 這張表的用途是看樣本落在哪裡。</p></div>")

    # ⑥ 事件
    if events is not None and len(events):
        ev = events.merge(f, on="date", how="inner")
        if len(ev):
            ea = agg(ev, "tag")
            parts.append("<div class='card'><h2>⑥ 依事件分類</h2>"
                         "<p class='muted'>來自你提供的事件檔。一天可以有多個標籤, 各自計入。</p>"
                         + _tbl(ea, "事件標籤") + "</div>")
        else:
            parts.append("<div class='card'><h2>⑥ 依事件分類</h2><p class='muted'>事件檔的日期與窗口內的交易日沒有交集。</p></div>")
    else:
        parts.append("<div class='card'><h2>⑥ 依事件分類 (盤前消息 / 總經)</h2>"
                     "<p class='muted'>沒有提供事件檔, 這一節是空的。"
                     "用 <code>--events events.csv</code> 帶入即可, 欄位 date,tag,note。"
                     "FOMC / CPI / 非農 / 盤前財測這類標籤要自己整理 — 這個環境的對外連線被機構政策擋住, 我無法代抓新聞。</p></div>")

    # ⑦ 每日明細
    cols = ["date", "gap_pct", "leg1_pct", "chk_pct", "chk_type", "rest_pct", "day_pct", "range_pct", "hi_time", "lo_time"]
    hdr = ["日期", "跳空%", "開盤段%", "檢查點%", "型態", "檢查點後%", "全日%", "振幅%", "最高時點", "最低時點"]
    tr = []
    for _, r in f.iterrows():
        tds = []
        for c in cols[1:]:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cls = ' class="pos"' if v > 0 else (' class="neg"' if v < 0 else "")
                tds.append(f"<td{cls}>{_fmt(v)}</td>")
            else:
                tds.append(f"<td>{v}</td>")
        tr.append(f"<tr><td>{r['date']}</td>{''.join(tds)}</tr>")
    parts.append("<div class='card'><h2>⑦ 每日明細</h2><details open><summary>展開 / 收起</summary><div class='tw'><table><tr>"
                 + "".join(f"<th>{h}</th>" for h in hdr) + "</tr>" + "".join(tr) + "</table></div></details></div>")

    # ⑧ 怎麼讀
    parts.append("""<div class='card'><h2>⑧ 怎麼讀這份報告</h2>
<p>1. <b>先看樣本數。</b>每一類的天數低於 30, 上漲比例就沒有統計意義, 看信賴區間就知道。</p>
<p>2. <b>看中位數而不是平均。</b>一個月裡一兩天的大行情就能把平均拉到完全不同的方向。</p>
<p>3. <b>檢查點的用途是分流, 不是訊號。</b>它告訴你今天屬於哪一類, 進出場仍然要用你的 MACD / RSI 策略。</p>
<p>4. <b>換一段期間重跑。</b>換一個月結論就翻盤的分類, 是在擬合雜訊。</p>
<p>5. <b>這裡沒有涵蓋</b>: 盤前與盤後、停牌、拆股; 跳空用的是前一交易日的盤中收盤, 不是官方收盤價。</p></div>""")
    body = "\n".join(parts)
    return (f"<!doctype html><html lang='zh-Hant'><meta charset='utf-8'>"
            f"<title>{meta['symbol']} 日內型態 · {tf} 分鐘</title>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<style>{CSS}</style><body class='viz'><div class='wrap'>{body}</div>"
            f"<script>{JS}</script></body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv"); ap.add_argument("--demo", action="store_true")
    ap.add_argument("--symbol", default="SOXL"); ap.add_argument("--tz", default=NY)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--start", default=""); ap.add_argument("--end", default="")
    ap.add_argument("--chk-start", default="09:50"); ap.add_argument("--chk-end", default="10:00")
    ap.add_argument("--chk-q", type=float, default=0.40, help="檢查點「有動」的門檻: |變動| 的第幾百分位")
    ap.add_argument("--gap-lo", type=float, default=0.5); ap.add_argument("--gap-hi", type=float, default=1.5)
    ap.add_argument("--k", type=int, default=3, help="k-means 群數")
    ap.add_argument("--events", default=""); ap.add_argument("--demo-tf", type=int, default=10)
    ap.add_argument("--out", default="../reports")
    a = ap.parse_args()

    if a.demo:
        df = make_demo(max(a.days, 8))
        if a.demo_tf > 1:
            df = df.resample(f"{a.demo_tf}min").agg(dict(open="first", high="max", low="min", close="last", volume="sum")).dropna()
        source = f"⚠ 合成示範資料 ({a.demo_tf} 分鐘) — 只驗證流程, 數字不代表任何真實商品"
    elif a.csv:
        df = load_csv(a.csv, a.tz); source = os.path.basename(a.csv)
    else:
        sys.exit("請給 --csv <檔案> 或 --demo")

    df = add_session(df)
    tf = detect_tf(df)
    hi = df.index[-1] if not (a.start or a.end) else pd.Timestamp(a.end or df.index[-1], tz=NY)
    lo = pd.Timestamp(a.start, tz=NY) if a.start else hi - pd.Timedelta(days=a.days)
    df = df[(df.index >= lo) & (df.index <= hi)]
    if df.empty:
        sys.exit("窗口內沒有資料 — 檢查 --days / --start / --end 與資料時區")

    grid = session_grid(df)
    chk_s, chk_e, moved = align_checkpoint(grid, s2m(a.chk_start), s2m(a.chk_end))
    f = daily_features(df, chk_s, chk_e)
    if f.empty:
        sys.exit("窗口內沒有完整的交易日")
    f = classify(f, a.chk_q, a.gap_hi, a.gap_lo)
    mat, dates = intraday_matrix(df, list(f.date), grid)
    f = f[f.date.isin(dates)].reset_index(drop=True)

    events = None
    if a.events:
        events = pd.read_csv(a.events)
        events.columns = [c.strip().lower() for c in events.columns]
        events["date"] = pd.to_datetime(events["date"]).dt.date

    meta = dict(symbol=a.symbol, source=source, first=str(f.date.iloc[0]), last=str(f.date.iloc[-1]),
                chk_q=a.chk_q, gap_lo=a.gap_lo, gap_hi=a.gap_hi)
    html = build_report(f, mat, dates, grid, chk_s, chk_e, moved, tf, meta, events, a.k)
    os.makedirs(a.out, exist_ok=True)
    stem = os.path.join(a.out, f"intraday_{a.symbol}_{tf}m_{len(f)}d")
    open(stem + ".html", "w", encoding="utf-8").write(html)
    f.to_csv(stem + "_daily.csv", index=False)
    print(f"{a.symbol} · {tf} 分鐘 K · {len(f)} 個交易日 ({f.date.iloc[0]} → {f.date.iloc[-1]})")
    print(f"檢查點 {m2s(chk_s)}-{m2s(chk_e)}" + ("  ← 已對齊到 K 線邊界" if moved else "  ← 與原本要的一致"))
    print(agg(f, "chk_type").to_string())
    print(f"→ {stem}.html\n→ {stem}_daily.csv")


if __name__ == "__main__":
    main()
