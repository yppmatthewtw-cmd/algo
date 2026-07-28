# -*- coding: utf-8 -*-
"""NDX 轉折點 × 領先指標 — 自足式 HTML (inline SVG, 雙主題, hover層)"""
import pandas as pd, numpy as np, json, glob, math, html as htmllib

OUT = 'ndx_turning_leading_indicators.html'

df = pd.read_csv('data/ndx_daily_spliced.csv'); df['date'] = pd.to_datetime(df['date'])
d = df.dropna(subset=['ndx']).reset_index(drop=True)
d['sma50'] = d['ndx'].rolling(50).mean()
d['sma200'] = d['ndx'].rolling(200).mean()
tpM = pd.read_csv('data/turning_points_MAJOR.csv'); tpM['date'] = pd.to_datetime(tpM['date'])
tpI = pd.read_csv('data/turning_points_INTER.csv'); tpI['date'] = pd.to_datetime(tpI['date'])
tpM = tpM.iloc[1:].reset_index(drop=True)  # drop 1999 warmup seed

sigs = []
for f in sorted(glob.glob('data/signals_*.csv')):
    fam = f.split('signals_')[1].replace('.csv','')
    s = pd.read_csv(f); s['family'] = fam
    sigs.append(s)
SIG = pd.concat(sigs, ignore_index=True) if sigs else pd.DataFrame(columns=['date','indicator','warn_type','family'])
SIG['date'] = pd.to_datetime(SIG['date'])

league = json.load(open('data/league.json')) if glob.glob('data/league.json') else {'rows': [], 'picked': []}
PICKED = league.get('picked', [])

date0, date1 = d['date'].iloc[0], d['date'].iloc[-1]
SPAN = (date1 - date0).days

def X(dt, w, pad_l=64, pad_r=14):
    return pad_l + (dt - date0).days / SPAN * (w - pad_l - pad_r)

def Ylog(p, h, lo, hi, pad_t=16, pad_b=22):
    return pad_t + (math.log(hi) - math.log(p)) / (math.log(hi) - math.log(lo)) * (h - pad_t - pad_b)

def polyline(dates, vals, w, h, lo, hi, step=1):
    pts = []
    for i in range(0, len(dates), step):
        v = vals.iloc[i] if hasattr(vals, 'iloc') else vals[i]
        if pd.notna(v):
            pts.append(f"{X(dates.iloc[i], w):.1f},{Ylog(v, h, lo, hi):.1f}")
    return ' '.join(pts)

W, H = 1180, 430
LO, HI = 900, 36000

svg = []
svg.append(f'<svg id="mainsvg" viewBox="0 0 {W} {H}" style="width:100%;height:auto;display:block">')
# gridlines + y ticks (log)
for yv in [1000, 2000, 4000, 8000, 16000, 32000]:
    yy = Ylog(yv, H, LO, HI)
    svg.append(f'<line x1="64" x2="{W-14}" y1="{yy:.1f}" y2="{yy:.1f}" class="grid"/>')
    svg.append(f'<text x="58" y="{yy+4:.1f}" class="tick" text-anchor="end">{yv:,}</text>')
for yr in range(2000, 2027, 2):
    xx = X(pd.Timestamp(f'{yr}-01-01'), W)
    svg.append(f'<line x1="{xx:.1f}" x2="{xx:.1f}" y1="16" y2="{H-22}" class="grid"/>')
    svg.append(f'<text x="{xx:.1f}" y="{H-6}" class="tick" text-anchor="middle">{yr}</text>')
# zigzag INTER (light, thin)
ptsI = [f"{X(r.date, W):.1f},{Ylog(r.price, H, LO, HI):.1f}" for r in tpI.itertuples()]
ptsI.append(f"{X(date1, W):.1f},{Ylog(d['ndx'].iloc[-1], H, LO, HI):.1f}")
svg.append(f'<polyline points="{" ".join(ptsI)}" class="zzI" fill="none"/>')
# price + SMAs
svg.append(f'<polyline points="{polyline(d["date"], d["ndx"], W, H, LO, HI, 2)}" class="price" fill="none"/>')
svg.append(f'<polyline points="{polyline(d["date"], d["sma50"], W, H, LO, HI, 3)}" class="sma50" fill="none"/>')
svg.append(f'<polyline points="{polyline(d["date"], d["sma200"], W, H, LO, HI, 3)}" class="sma200" fill="none"/>')
# zigzag MAJOR
ptsM = [f"{X(r.date, W):.1f},{Ylog(r.price, H, LO, HI):.1f}" for r in tpM.itertuples()]
ptsM.append(f"{X(date1, W):.1f},{Ylog(d['ndx'].iloc[-1], H, LO, HI):.1f}")
svg.append(f'<polyline points="{" ".join(ptsM)}" class="zzM" fill="none"/>')
# turn markers
for r in tpM.itertuples():
    xx, yy = X(r.date, W), Ylog(r.price, H, LO, HI)
    lbl = f"{r.date.date()} {'頂' if r.type=='TOP' else '底'} {r.price:,.0f} → {r.ensuing_move:+.1%}"
    if r.type == 'TOP':
        svg.append(f'<path d="M{xx:.1f},{yy-14:.1f} l-5.5,-9 l11,0 z" class="mkT"><title>{lbl}</title></path>')
    else:
        svg.append(f'<path d="M{xx:.1f},{yy+14:.1f} l-5.5,9 l11,0 z" class="mkB"><title>{lbl}</title></path>')
# direct labels
svg.append(f'<text x="{X(pd.Timestamp("2003-06-01"),W):.0f}" y="40" class="lbl" style="fill:var(--c-price)">NDX (2016前=Composite報酬鏈接)</text>')
svg.append(f'<text x="{X(pd.Timestamp("2003-06-01"),W):.0f}" y="56" class="lbl" style="fill:var(--c-s50)">50日均線</text>')
svg.append(f'<text x="{X(pd.Timestamp("2003-06-01"),W):.0f}" y="72" class="lbl" style="fill:var(--c-s200)">200日均線</text>')
svg.append(f'<text x="{X(pd.Timestamp("2003-06-01"),W):.0f}" y="88" class="lbl" style="fill:var(--c-zz)">ZigZag ±15% 主要趨勢線</text>')
# hover layer
svg.append(f'<line id="xh" x1="0" x2="0" y1="16" y2="{H-22}" class="xhair" style="display:none"/>')
svg.append(f'<circle id="xdot" r="3.5" class="xdot" style="display:none"/>')
svg.append(f'<rect x="64" y="16" width="{W-78}" height="{H-38}" fill="transparent" id="hoverpad"/>')
svg.append('</svg>')
MAIN_SVG = '\n'.join(svg)

# ---------- signal raster ----------
fam_names = {'trend_momentum':'趨勢動能','volatility':'波動率','credit_breadth':'信用廣度','volume':'量價','monthly_pillars':'月度支柱'}
rows_meta = [r for r in league.get('rows', []) if r['indicator'] in PICKED] if PICKED else []
RH = 26
RW, RHtot = 1180, 60 + RH * max(1, len(rows_meta))
rs = [f'<svg viewBox="0 0 {RW} {RHtot}" style="width:100%;height:auto;display:block">']
for r in tpM.itertuples():
    xx = X(r.date, RW)
    cls = 'vlT' if r.type == 'TOP' else 'vlB'
    rs.append(f'<line x1="{xx:.1f}" x2="{xx:.1f}" y1="34" y2="{RHtot-20}" class="{cls}"/>')
for yr in range(2000, 2027, 2):
    xx = X(pd.Timestamp(f'{yr}-01-01'), RW)
    rs.append(f'<text x="{xx:.1f}" y="{RHtot-4}" class="tick" text-anchor="middle">{yr}</text>')
rs.append(f'<text x="64" y="14" class="lblB">領先訊號時間對比 (紅虛線=主要頂, 綠虛線=主要底; 每列一個指標, 刻度=該指標訊號日)</text>')
for k, rm in enumerate(rows_meta):
    y0 = 42 + k * RH
    nm = rm['indicator']; fam = rm['family']
    ss = SIG[SIG['indicator'] == nm]
    lead = rm.get('median_lead')
    rs.append(f'<text x="60" y="{y0+5}" class="rowlbl" text-anchor="end">{htmllib.escape(nm[:20])} <tspan class="famchip">[{fam_names.get(fam,fam)}] 中位{lead:+.0f}d</tspan></text>')
    for s in ss.itertuples():
        if pd.isna(s.date): continue
        xx = X(s.date, RW)
        cls = 'tkT' if s.warn_type == 'TOP' else 'tkB'
        rs.append(f'<line x1="{xx:.1f}" x2="{xx:.1f}" y1="{y0-8}" y2="{y0+8}" class="{cls}"><title>{nm} | {s.date.date()} | {"頂部警訊" if s.warn_type=="TOP" else "底部警訊"}</title></line>')
rs.append('</svg>')
RASTER_SVG = '\n'.join(rs)

# ---------- sub-panels: VIX, HY OAS, breadth ----------
def subpanel(col, label, lo, hi, logscale=False, w=1180, h=150, fmt='{:.0f}', hline=None):
    dd = d.dropna(subset=[col])
    s = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto;display:block">']
    def Y(v):
        if logscale:
            return 12 + (math.log(hi)-math.log(v))/(math.log(hi)-math.log(lo))*(h-32)
        return 12 + (hi-v)/(hi-lo)*(h-32)
    for r in tpM.itertuples():
        if r.date >= dd['date'].iloc[0]:
            xx = X(r.date, w)
            s.append(f'<line x1="{xx:.1f}" x2="{xx:.1f}" y1="12" y2="{h-20}" class="{ "vlT" if r.type=="TOP" else "vlB"}"/>')
    if hline is not None:
        s.append(f'<line x1="64" x2="{w-14}" y1="{Y(hline):.1f}" y2="{Y(hline):.1f}" class="hline"/>')
        s.append(f'<text x="{w-16}" y="{Y(hline)-4:.1f}" class="tick" text-anchor="end">{fmt.format(hline)}</text>')
    for tv in [lo, hi]:
        s.append(f'<text x="58" y="{Y(tv)+4:.1f}" class="tick" text-anchor="end">{fmt.format(tv)}</text>')
    pts = []
    for i in range(0, len(dd), 1):
        pts.append(f"{X(dd['date'].iloc[i], w):.1f},{Y(min(max(dd[col].iloc[i], lo), hi)):.1f}")
    s.append(f'<polyline points="{" ".join(pts)}" class="subline" fill="none"/>')
    s.append(f'<text x="66" y="24" class="lblB">{label}</text>')
    s.append('</svg>')
    return '\n'.join(s)

VIX_SVG = subpanel('vix', 'VIX (2014起) — 尖峰翻落=底部警訊, 低位擠壓後破位=頂部警訊', 10, 85, True, hline=35)
OAS_SVG = subpanel('hyoas', 'HY OAS bp (2016-07起, 原工作簿真實數據) — 4週走闊+50bp=頂部警訊, 峰值回落=底部警訊', 250, 900, True, hline=450)
BR_SVG = subpanel('breadth', '%成份股>200日線 (2016-07起) — 頂背離/先崩=頂部警訊, washout<30%後回升=底部警訊', 0.05, 1.0, False, fmt='{:.0%}', hline=0.30)

# ---------- zoom insets ----------
def inset(t0, t1, title, w=560, h=240):
    dd = d[(d['date'] >= t0) & (d['date'] <= t1)].reset_index(drop=True)
    lo, hi = dd['ndx'].min()*0.97, dd['ndx'].max()*1.03
    span = (dd['date'].iloc[-1] - dd['date'].iloc[0]).days
    def Xi(dt): return 46 + (dt - dd['date'].iloc[0]).days / span * (w-58)
    def Yi(p): return 12 + (hi-p)/(hi-lo)*(h-46)
    s = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto;display:block">']
    for r in tpM.itertuples():
        if t0 <= r.date <= t1:
            xx = Xi(r.date)
            s.append(f'<line x1="{xx:.1f}" x2="{xx:.1f}" y1="12" y2="{h-34}" class="{ "vlT" if r.type=="TOP" else "vlB"}"/>')
            s.append(f'<text x="{xx:.1f}" y="{h-22}" class="tick" text-anchor="middle">{r.date.date()}</text>')
    pts = ' '.join(f"{Xi(dd['date'].iloc[i]):.1f},{Yi(dd['ndx'].iloc[i]):.1f}" for i in range(len(dd)))
    s.append(f'<polyline points="{pts}" class="price" fill="none"/>')
    p50 = ' '.join(f"{Xi(dd['date'].iloc[i]):.1f},{Yi(dd['sma50'].iloc[i]):.1f}" for i in range(len(dd)) if pd.notna(dd['sma50'].iloc[i]) and lo < dd['sma50'].iloc[i] < hi)
    if p50: s.append(f'<polyline points="{p50}" class="sma50" fill="none"/>')
    ss = SIG[(SIG['date'] >= t0) & (SIG['date'] <= t1) & (SIG['indicator'].isin(PICKED))]
    seen_y = {}
    for sg in ss.itertuples():
        row = dd[dd['date'] == sg.date]
        if len(row) == 0: continue
        xx = Xi(sg.date); yy = Yi(row['ndx'].iloc[0])
        off = seen_y.get(round(xx/8), 0); seen_y[round(xx/8)] = off + 1
        if sg.warn_type == 'TOP':
            s.append(f'<path d="M{xx:.1f},{yy-8-off*9:.1f} l-4.5,-7 l9,0 z" class="mkT"><title>{sg.indicator} | {sg.date.date()} | 頂部警訊</title></path>')
        else:
            s.append(f'<path d="M{xx:.1f},{yy+8+off*9:.1f} l-4.5,7 l9,0 z" class="mkB"><title>{sg.indicator} | {sg.date.date()} | 底部警訊</title></path>')
    s.append(f'<text x="46" y="{h-6}" class="lblB">{title}</text>')
    s.append('</svg>')
    return '\n'.join(s)

INSETS = [
    inset(pd.Timestamp('2019-10-01'), pd.Timestamp('2020-06-30'), '2020-02-19頂 / 03-20底: COVID崩跌'),
    inset(pd.Timestamp('2021-06-01'), pd.Timestamp('2022-04-30'), '2021-11-19頂: 2022熊市起點'),
    inset(pd.Timestamp('2022-08-01'), pd.Timestamp('2023-04-30'), '2022-12-28底: AI牛市起點'),
    inset(pd.Timestamp('2024-10-01'), pd.Timestamp('2025-08-31'), '2025-02-19頂 / 04-08底'),
]

# ---------- league table ----------
lt = ['<table class="tbl"><thead><tr><th>#</th><th>指標</th><th>族</th><th>警訊</th><th>判定</th><th>中位lead(交易日)</th><th>命中</th><th>假訊號率</th><th>覆蓋</th></tr></thead><tbody>']
for i, r in enumerate(sorted(league.get('rows', []), key=lambda x: x.get('median_lead', 0)), 1):
    star = ' ⭐' if r['indicator'] in PICKED else ''
    vc = {'LEADING':'vLead','COINCIDENT':'vCo','CONFIRMING':'vConf','WEAK':'vWeak'}.get(r.get('verdict',''), '')
    lt.append(f"<tr><td>{i}</td><td>{htmllib.escape(r['indicator'])}{star}</td><td>{fam_names.get(r['family'], r['family'])}</td>"
              f"<td>{r.get('warn_type','')}</td><td class='{vc}'>{r.get('verdict','')}</td>"
              f"<td class='num'>{r.get('median_lead',''):+.0f}</td><td>{htmllib.escape(str(r.get('hits','')))}</td>"
              f"<td class='num'>{r.get('fp_rate',0):.0%}</td><td>{htmllib.escape(str(r.get('coverage','')))}</td></tr>")
lt.append('</tbody></table>')
LEAGUE_HTML = '\n'.join(lt)

# turns table
tt = ['<table class="tbl"><thead><tr><th>日期</th><th>類型</th><th>價位</th><th>其後走勢</th><th>迄</th></tr></thead><tbody>']
for r in tpM.itertuples():
    cls = 'vlTt' if r.type == 'TOP' else 'vlBt'
    tt.append(f"<tr><td>{r.date.date()}</td><td class='{cls}'>{'頂 TOP' if r.type=='TOP' else '底 BOTTOM'}</td>"
              f"<td class='num'>{r.price:,.0f}</td><td class='num'>{r.ensuing_move:+.1%}</td><td>{r.ensuing_end}</td></tr>")
tt.append('</tbody></table>')
TURNS_HTML = '\n'.join(tt)

hover_data = [[str(d['date'].iloc[i].date()), round(float(d['ndx'].iloc[i]), 1)] for i in range(len(d))]

page = f"""<!-- built by build_html.py -->
<title>NDX 趨勢轉折 × 領先指標 (1999-2026)</title>
<style>
:root {{ --surface-1:#fcfcfb; --surface-2:#f4f4f2; --text-1:#0b0b0b; --text-2:#52514e; --grid:#e4e4e0;
  --c-price:#2a78d6; --c-s50:#eb6834; --c-s200:#1baf7a; --c-zz:#4a3aa7; --c-top:#c93a39; --c-bot:#008300; }}
@media (prefers-color-scheme: dark) {{ :root:where(:not([data-theme="light"])) {{ --surface-1:#1a1a19; --surface-2:#232322; --text-1:#fff; --text-2:#c3c2b7; --grid:#33332f;
  --c-price:#3987e5; --c-s50:#d95926; --c-s200:#199e70; --c-zz:#9085e9; --c-top:#e66767; --c-bot:#31a842; }} }}
:root[data-theme="dark"] {{ --surface-1:#1a1a19; --surface-2:#232322; --text-1:#fff; --text-2:#c3c2b7; --grid:#33332f;
  --c-price:#3987e5; --c-s50:#d95926; --c-s200:#199e70; --c-zz:#9085e9; --c-top:#e66767; --c-bot:#31a842; }}
body {{ background:var(--surface-1); color:var(--text-1); font-family:'PingFang TC','Microsoft JhengHei','Noto Sans TC',sans-serif; margin:0; padding:24px clamp(8px,3vw,40px); }}
h1 {{ font-size:1.35rem; margin:0 0 4px }} h2 {{ font-size:1.05rem; margin:26px 0 8px }}
.sub {{ color:var(--text-2); font-size:.85rem; margin-bottom:14px }}
.card {{ background:var(--surface-2); border-radius:10px; padding:12px 14px; margin-bottom:14px; overflow-x:auto }}
.grid {{ stroke:var(--grid); stroke-width:1 }}
.tick {{ fill:var(--text-2); font-size:11px }}
.price {{ stroke:var(--c-price); stroke-width:1.6 }}
.sma50 {{ stroke:var(--c-s50); stroke-width:1.3 }}
.sma200 {{ stroke:var(--c-s200); stroke-width:1.3 }}
.zzM {{ stroke:var(--c-zz); stroke-width:1.6; stroke-dasharray:7 4; opacity:.9 }}
.zzI {{ stroke:var(--c-zz); stroke-width:.8; opacity:.35 }}
.mkT {{ fill:var(--c-top) }} .mkB {{ fill:var(--c-bot) }}
.vlT {{ stroke:var(--c-top); stroke-width:1; stroke-dasharray:3 3; opacity:.65 }}
.vlB {{ stroke:var(--c-bot); stroke-width:1; stroke-dasharray:3 3; opacity:.65 }}
.tkT {{ stroke:var(--c-top); stroke-width:2 }} .tkB {{ stroke:var(--c-bot); stroke-width:2 }}
.lbl {{ font-size:12px; font-weight:600 }} .lblB {{ fill:var(--text-1); font-size:12px; font-weight:600 }}
.rowlbl {{ fill:var(--text-1); font-size:11px }} .famchip {{ fill:var(--text-2); font-size:10px }}
.subline {{ stroke:var(--c-price); stroke-width:1.2 }}
.hline {{ stroke:var(--c-top); stroke-width:1; stroke-dasharray:5 4; opacity:.6 }}
.xhair {{ stroke:var(--text-2); stroke-width:1; stroke-dasharray:2 3 }}
.xdot {{ fill:var(--c-price) }}
#tip {{ position:fixed; display:none; background:var(--surface-2); border:1px solid var(--grid); border-radius:6px; padding:6px 9px; font-size:12px; pointer-events:none; z-index:9 }}
.tbl {{ border-collapse:collapse; font-size:.82rem; width:100% }}
.tbl th,.tbl td {{ padding:5px 9px; border-bottom:1px solid var(--grid); text-align:left; white-space:nowrap }}
.tbl th {{ color:var(--text-2); font-weight:600 }}
.num {{ font-variant-numeric:tabular-nums }}
.vLead {{ color:var(--c-bot); font-weight:700 }} .vCo {{ color:var(--text-2) }} .vConf {{ color:var(--c-s50) }} .vWeak {{ color:var(--text-2) }}
.vlTt {{ color:var(--c-top); font-weight:600 }} .vlBt {{ color:var(--c-bot); font-weight:600 }}
.insets {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:14px }}
.note {{ font-size:.78rem; color:var(--text-2); line-height:1.55 }}
</style>
<h1>NASDAQ 100 趨勢轉折 × 領先指標 時間對比 (1999-2026)</h1>
<div class="sub">轉折定義: ZigZag ±15%=主要(45個) / ±8%=中級(163個), 演算法無前視 | 訊號規則全部客觀量化, 經對抗性驗證 | 數據: 原工作簿NDX真實日線(2016-07起) + Nasdaq Composite報酬鏈接(1999-2016, 重疊期日報酬相關0.989) + VIX(2014起) + HY OAS/廣度(2016起)</div>

<h2>主圖: NDX (對數刻度) + 多重趨勢線疊加</h2>
<div class="card">{MAIN_SVG}</div>

<h2>領先訊號 × 轉折時間對比 (訊號raster)</h2>
<div class="card">{RASTER_SVG}</div>

<h2>跨資產確認面板</h2>
<div class="card">{VIX_SVG}</div>
<div class="card">{OAS_SVG}</div>
<div class="card">{BR_SVG}</div>

<h2>四大轉折放大 (訊號時間標記)</h2>
<div class="insets">
<div class="card">{INSETS[0]}</div>
<div class="card">{INSETS[1]}</div>
<div class="card">{INSETS[2]}</div>
<div class="card">{INSETS[3]}</div>
</div>

<h2>領先指標排行榜 (中位lead越負越領先)</h2>
<div class="card">{LEAGUE_HTML}</div>

<h2>45個主要轉折點 (表格檢視)</h2>
<div class="card">{TURNS_HTML}</div>

<div class="note">方法論: ①ZigZag(±15%/±8%)客觀偵測頂底; ②每個指標由公式規則產生訊號日(嚴禁前視), 在轉折前90交易日至後5交易日窗口內配對; lead=訊號日−轉折日(交易日, 負=領先); ③假訊號=訊號後90交易日內無任何同向轉折; ④五族分析各由獨立agent計算並經對抗性驗證者重算抽查。⭐=入選訊號raster。限制: 2016年前無廣度/信用/合成分數據; VIX 2014年起; 量價族僅1999-2016; 主要轉折樣本45個, 統計置信度有限; 過去領先性不保證未來。</div>
<div id="tip"></div>
<script>
const HD = {json.dumps(hover_data)};
const svgEl = document.getElementById('mainsvg');
const pad = document.getElementById('hoverpad');
const xh = document.getElementById('xh'), xdot = document.getElementById('xdot'), tip = document.getElementById('tip');
const W = {W}, H = {H}, PADL = 64, PADR = 14, PT = 16, PB = 22;
const d0 = new Date(HD[0][0]).getTime(), d1 = new Date(HD[HD.length-1][0]).getTime();
const LO = {LO}, HI = {HI};
pad.addEventListener('mousemove', e => {{
  const r = svgEl.getBoundingClientRect();
  const fx = (e.clientX - r.left) / r.width * W;
  const t = d0 + (fx - PADL) / (W - PADL - PADR) * (d1 - d0);
  let lo = 0, hi = HD.length - 1;
  while (hi - lo > 1) {{ const m = (lo + hi) >> 1; (new Date(HD[m][0]).getTime() < t) ? lo = m : hi = m; }}
  const row = HD[Math.abs(new Date(HD[lo][0]).getTime() - t) < Math.abs(new Date(HD[hi][0]).getTime() - t) ? lo : hi];
  const px = PADL + (new Date(row[0]).getTime() - d0) / (d1 - d0) * (W - PADL - PADR);
  const py = PT + (Math.log(HI) - Math.log(row[1])) / (Math.log(HI) - Math.log(LO)) * (H - PT - PB);
  xh.setAttribute('x1', px); xh.setAttribute('x2', px); xh.style.display = 'block';
  xdot.setAttribute('cx', px); xdot.setAttribute('cy', py); xdot.style.display = 'block';
  tip.style.display = 'block'; tip.style.left = (e.clientX + 14) + 'px'; tip.style.top = (e.clientY - 10) + 'px';
  tip.innerHTML = row[0] + '<br><b>' + row[1].toLocaleString() + '</b>';
}});
pad.addEventListener('mouseleave', () => {{ xh.style.display = 'none'; xdot.style.display = 'none'; tip.style.display = 'none'; }});
</script>
"""
open(OUT, 'w').write(page)
print('saved', OUT, f'{len(page)/1024:.0f}KB, signals={len(SIG)}, picked={len(PICKED)}')
