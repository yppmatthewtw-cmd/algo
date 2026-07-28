# -*- coding: utf-8 -*-
"""把 NDX 轉折×領先指標數據移植入 Macro_dashboard R15.12 的 A-Chart 格式
保留 A-Chart 全部格式/layout/功能; 移除 B/B1/C 頁; 實裝原本停用的 TURNS 領先指標排名"""
import pandas as pd, numpy as np, json, re, glob

SRC = '/root/.claude/uploads/0bed5a0b-c49b-533e-8899-bcd26a47a6bd/2d295034-Macro_dashboard_R15.12_0728_hk21.00.html'
OUT = 'ndx_turning_TECHNICAL_INDICATOR.html'

h = open(SRC, encoding='utf-8').read()

# ---------- 1. parse DATA for date axis ----------
m = re.search(r'const DATA=(\{)', h)
dec = json.JSONDecoder()
DATA, _ = dec.raw_decode(h[m.start(1):])
ISO = [d['iso'] for d in DATA['dates']]
iso2idx = {s: i for i, s in enumerate(ISO)}
N = len(ISO)
def snap(iso):
    if iso in iso2idx: return iso2idx[iso]
    d = pd.Timestamp(iso)
    for k in range(1, 6):
        for cand in [(d + pd.Timedelta(days=k)), (d - pd.Timedelta(days=k))]:
            s = str(cand.date())
            if s in iso2idx: return iso2idx[s]
    return None

# ---------- 2. our data ----------
tpM = pd.read_csv('data/turning_points_MAJOR.csv').iloc[1:]
tpI = pd.read_csv('data/turning_points_INTER.csv').iloc[1:]
full = json.load(open('data/families_full.json'))
league = json.load(open('data/league.json'))
sigs = []
for f in sorted(glob.glob('data/signals_*.csv')):
    s = pd.read_csv(f); s['family'] = f.split('signals_')[1].replace('.csv', '')
    sigs.append(s)
SIG = pd.concat(sigs, ignore_index=True)
SIG['date'] = SIG['date'].astype(str).str[:10]

FAMN = {'trend_momentum': '趨勢動能', 'volatility': '波動率', 'credit_breadth': '信用廣度',
        'volume': '量價', 'monthly_pillars': '月度支柱'}

# per-indicator meta
IND_META = {}
for fam in full['families']:
    for ind in fam['indicators']:
        IND_META[ind['name']] = {'fam': fam['family'], 'warn': ind['warn_type'],
                                 'med': ind['median_lead'], 'verdict': ind['verdict'],
                                 'hits': ind['hits'], 'fp': ind['fp_rate']}

# LEAD_DB: turn iso -> list of {n,f,l,v} from per_turn
LEAD_DB = {}
for fam in full['families']:
    for ind in fam['indicators']:
        for pt in ind['per_turn']:
            if pt['lead_days'] is None: continue
            key = pt['turn_date']
            LEAD_DB.setdefault(key, []).append({
                'n': ind['name'], 'f': FAMN[fam['family']], 'l': pt['lead_days'],
                'u': '月' if fam['family'] == 'monthly_pillars' else 'd',
                'v': ind['verdict'], 't': pt['turn_type']})

# TURN_EVENTS: MAJOR + INTER (2020+), dims = 四族警訊密度(轉折前90td訊號數), note = top領先訊號
GRP = {'趨勢動能': 'm1', '波動率': 'm2', '信用廣度': 'm3', '月度支柱': 'm4', '量價': 'm4'}
sig_by_fam = {}
for _, r in SIG.iterrows():
    idx = snap(r['date'])
    if idx is None: continue
    sig_by_fam.setdefault((FAMN[r['family']], r['warn_type']), []).append(idx)

inter_only = tpI[~tpI['date'].isin(set(tpM['date']))]
events = []
for src, kind in [(tpM, 'major'), (inter_only, 'inter')]:
    for _, r in src.iterrows():
        idx = snap(str(r['date']))
        if idx is None: continue
        dirn = 'top' if r['type'] == 'TOP' else 'bot'
        warn = 'TOP' if dirn == 'top' else 'BOTTOM'
        dims = {}
        fired = 0
        for famn, mk in [('趨勢動能', 'm1'), ('波動率', 'm2'), ('信用廣度', 'm3'), ('月度支柱', 'm4')]:
            cnt = sum(1 for si in sig_by_fam.get((famn, warn), []) if idx - 90 <= si <= idx)
            v = min(100, cnt * 20)
            dims[mk] = v
            if cnt > 0: fired += 1
        leads = sorted([x for x in LEAD_DB.get(str(r['date']), []) if x['t'] == r['type'] and x['l'] <= 0],
                       key=lambda x: x['l'])[:3]
        ltxt = ' · '.join(f"{x['n']}({x['l']:+d}{x['u']})" for x in leads) if leads else '窗內無領先訊號紀錄'
        note = f"其後 {float(r['ensuing_move']):+.1%} → {r['ensuing_end']} · 領先: {ltxt}"
        events.append({'idx': idx, 'iso': str(r['date']), 'dir': dirn, 'kind': kind,
                       'comp': fired * 25, 'dims': dims, 'note': note})
events.sort(key=lambda e: e['idx'])
peaks = sorted(set(e['idx'] for e in events if e['dir'] == 'top'))
troughs = sorted(set(e['idx'] for e in events if e['dir'] == 'bot'))

# raster indicators (picked, mapped 2020+)
SIGR = []
for nm in league['picked']:
    meta = IND_META[nm]
    rows = SIG[SIG['indicator'] == nm]
    idxs = sorted(set(i for i in (snap(d) for d in rows['date']) if i is not None))
    if not idxs: continue
    SIGR.append({'n': nm, 'f': FAMN[meta['fam']], 'w': meta['warn'],
                 'med': meta['med'], 'u': '月' if meta['fam'] == 'monthly_pillars' else 'd', 'idx': idxs})

LEAGUE_ROWS = sorted(
    [{'n': r['indicator'], 'f': FAMN[r['family']], 'w': r['warn_type'], 'v': r['verdict'],
      'med': r['median_lead'], 'hits': r['hits'], 'fp': r['fp_rate'],
      'u': '月' if r['family'] == 'monthly_pillars' else 'd'} for r in league['rows']],
    key=lambda x: x['med'])

print(f'events {len(events)} (major {sum(1 for e in events if e["kind"]=="major")}) peaks {len(peaks)} troughs {len(troughs)}; raster inds {len(SIGR)}; sig mapped {sum(len(s["idx"]) for s in SIGR)}')

# ---------- 3. HTML surgery ----------
# 3a. title
h = re.sub(r'<title>.*?</title>',
           '<title>ndx_turning_(TECHNICAL_INDICATOR) · A-Chart格式 · NDX轉折×領先指標 · 45轉折/34指標/2037訊號(經對抗性驗證) · 價格軸2020-01-02..2026-07-27</title>',
           h, count=1, flags=re.S)

# 3b. brand + remove B/B1/C tabs
h = h.replace('<span class="brand">必走週期 R15.12</span>', '<span class="brand">NDX轉折×領先指標 (A-Chart格式 R15.12)</span>')
h = h.replace('<span class="page-tab" data-pg="B">B-AI 動能</span><span class="page-tab" data-pg="B1">C-AI 動能(美國外)</span><span class="page-tab" data-pg="C">D·Sector</span>', '')

# 3c. remove pageB / pageB1 / pageC DOM (保留其後的 #tip / #fcTip)
iB = h.find('<div id="pageB"')
iC = h.find('<div id="pageC"')
pageC_end = h.find('</div>', h.find('<iframe id="sectorFrame">', iC)) + len('</div>')
assert 0 < iB < iC < pageC_end
h = h[:iB] + h[pageC_end:]
# 3d. stub loadSector / loadRotationExUS / loadRotation (cut ~550KB data blob)
iLS = h.find('function loadSector')
iPT = h.find("document.querySelectorAll('.page-tab')", iLS)
assert iLS > 0 and iPT > iLS
h = h[:iLS] + 'function loadSector(){} function loadRotationExUS(){} function loadRotation(){}\n ' + h[iPT:]

# 3e. insert paneSigR + paneRank after paneGN
anchor = '<div class="row-resizer" data-above="paneGN" data-below="pane21"></div>'
new_panes = '''<div class="row-resizer" data-above="paneGN" data-below="paneSigR"></div>
      <div id="paneSigR" class="lpane lpane-sigr">
        <div class="subpane-head" data-pane="paneSigR">
          <input type="checkbox" class="pane-master" id="pmSigR" title="顯示/隱藏本面板" checked><span class="sp-caret">▾</span><span class="sp-title">A3.1 · 領先訊號 Raster (12入選指標×訊號日 · 經對抗性驗證)</span>
          <span class="sp-meta">紅=頂部警訊 · 綠=底部警訊 · 虛線=轉折(粗=±15%主要, 細=±8%中期) · 來源 ndx_turning_leading_indicators</span>
          <span class="lpane-readout" id="rdSigR">—</span>
        </div>
        <canvas id="chSigR"></canvas>
      </div>
      <div class="row-resizer" data-above="paneSigR" data-below="paneRank"></div>
      <div id="paneRank" class="lpane lpane-rank collapsed">
        <div class="subpane-head" data-pane="paneRank">
          <input type="checkbox" class="pane-master" id="pmRank" title="顯示/隱藏本面板" checked><span class="sp-caret">▾</span><span class="sp-title">A3.2 · 領先指標排行榜 (34指標 · 1999-2026 45個轉折驗證)</span>
          <span class="sp-meta">中位lead越負越領先 · LEADING=領先 / CONFIRMING=滯後確認</span>
          <span class="lpane-readout"></span>
        </div>
        <div class="rank-scroll"><table class="rank-tbl"><thead><tr><th>#</th><th>指標</th><th>族</th><th>警訊</th><th>判定</th><th>中位lead</th><th>命中</th><th>FP率</th></tr></thead><tbody id="rankBody"></tbody></table></div>
      </div>
      <div class="row-resizer" data-above="paneRank" data-below="pane21"></div>'''
assert anchor in h
h = h.replace(anchor, new_panes, 1)

# 3f. CSS additions
css = '''
.lpane-sigr{flex:1.2 1 0;min-height:150px}
.lpane-rank{flex:1 1 0;min-height:120px;max-height:300px;display:flex;flex-direction:column}
.rank-scroll{overflow:auto;flex:1}
.rank-tbl{border-collapse:collapse;font-size:10px;width:100%}
.rank-tbl th,.rank-tbl td{padding:2px 6px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap;color:var(--txt-1)}
.rank-tbl th{position:sticky;top:0;background:var(--bg-side);color:var(--txt-2);z-index:2}
.rank-lead{color:var(--green);font-weight:700}.rank-conf{color:var(--amber)}.rank-weak{color:var(--txt-3)}
#turnRankPanel{position:absolute;right:8px;top:30px;z-index:9;background:var(--bg-panel);border:1px solid var(--line-2);border-radius:6px;padding:6px 8px;font-size:10px;max-width:290px;box-shadow:0 4px 14px rgba(0,0,0,.18);display:none}
#turnRankPanel .trp-h{font-weight:700;color:var(--txt-0);margin-bottom:3px;font-size:10.5px}
#turnRankPanel .trp-r{display:flex;gap:6px;justify-content:space-between;color:var(--txt-1);line-height:1.5}
#turnRankPanel .trp-l{font-family:var(--mono);font-weight:700}
'''
h = h.replace('</style>\n</head>', css + '</style>\n</head>', 1)

# 3g. replace TURN_EVENTS literal
iTE = h.find('const TURN_EVENTS=')
jTE = h.find('];', iTE) + 2
te_js = 'const TURN_EVENTS=' + json.dumps(events, ensure_ascii=False, separators=(',', ':')) + ';'
h = h[:iTE] + te_js + h[jTE:]

# 3g2. 修補收合排除清單: 點 TURNS/SMA 切換不應收合面板 (原版點 turn-tgl 會誤觸收合)
h = h.replace("e.target.closest('button,select,a,.lp-spx-badge')",
              "e.target.closest('button,select,a,.lp-spx-badge,.turn-tgl,.sma-tgl,.ind-chip,.pane-master')")

# 3h. late script before </body>
late = '''
<script>
/* ═══ NDX轉折×領先指標 移植層 (ndx_turning_leading_indicators → A-Chart) ═══ */
const OUR_DIM_META=[{k:'m1',label:'趨勢動能警訊',c:'#7C3AED'},{k:'m2',label:'波動率警訊',c:'#0EA5E9'},{k:'m3',label:'信用廣度警訊',c:'#D97706'},{k:'m4',label:'月度支柱警訊',c:'#0E8C5A'}];
const LEAD_DB=__LEAD_DB__;
const SIGR=__SIGR__;
const LEAGUE_ROWS=__LEAGUE_ROWS__;
window.SPX_PEAKS=__PEAKS__;
window.SPX_TROUGHS=__TROUGHS__;

/* 排行榜面板 */
(function(){ var tb=document.getElementById('rankBody'); if(!tb)return;
  tb.innerHTML=LEAGUE_ROWS.map(function(r,i){ var vc=r.v==='LEADING'?'rank-lead':(r.v==='CONFIRMING'?'rank-conf':'rank-weak');
    return '<tr><td>'+(i+1)+'</td><td>'+r.n+'</td><td>'+r.f+'</td><td>'+r.w+'</td><td class="'+vc+'">'+r.v+'</td><td style="font-family:var(--mono)">'+(r.med>0?'+':'')+r.med+r.u+'</td><td>'+r.hits+'</td><td>'+Math.round(r.fp*100)+'%</td></tr>'; }).join('');
})();

/* showTurnTip: 用我們的四族警訊 dims + 領先訊號 note */
showTurnTip=function(t,el){ var tip=document.getElementById('fcTip'); if(!tip)return;
  tip.innerHTML='<div class="fctip-h">'+(t.dir==='top'?'🔻 頂 · ':'🔺 底 · ')+t.iso+' · '+(t.kind==='major'?'主要(±15%)':'中期(±8%)')+'轉折 · ZigZag驗證</div>'+
    OUR_DIM_META.map(function(m){ var v=t.dims[m.k]||0; return '<div class="tdim"><span class="tdim-l">'+m.label+'</span><span class="tdim-bar"><i style="width:'+v+'%;background:'+m.c+'"></i></span><span class="tdim-v">'+v+'</span></div>'; }).join('')+
    '<div class="fctip-p">警訊族群 <b>'+(t.comp/25)+'</b>/4 已發 · '+t.note+'<br><span style="opacity:.6">警訊密度=轉折前90交易日該族訊號數×20(封頂100) · 詳見A3.2排行榜</span></div>';
  tip.style.display='block';
  var r=el.getBoundingClientRect(),tw=250,th=tip.offsetHeight;
  var left=r.left-tw-12; if(left<6)left=r.right+12; if(left+tw>window.innerWidth-6)left=window.innerWidth-tw-6;
  var top=r.top-8; if(top+th>window.innerHeight-6)top=window.innerHeight-th-6; if(top<6)top=6;
  tip.style.left=left+'px'; tip.style.top=top+'px';
};

/* analyzeTurns: 實裝原本停用的領先指標排名 (原註: 必走信號無時序資料) */
analyzeTurns=function(){
  var sel=[...state.selTurns]; state.leadRank={};
  var panel=document.getElementById('turnRankPanel');
  if(!panel){ panel=document.createElement('div'); panel.id='turnRankPanel';
    var host=document.getElementById('panePrice'); host.style.position='relative'; host.appendChild(panel); }
  if(!sel.length){ state.turnType=null; panel.style.display='none'; return; }
  var anyPeak=sel.some(function(i){return SPX_PEAKS.indexOf(i)>=0;});
  state.turnType=anyPeak?'peak':'trough';
  var wantT=anyPeak?'TOP':'BOTTOM';
  var best={};
  sel.forEach(function(idx){
    var iso=DATA.dates[idx]?DATA.dates[idx].iso:null; if(!iso)return;
    var rows=LEAD_DB[iso]||LEAD_DB[iso.slice(0,7)]||[];
    rows.forEach(function(r){ if(r.t!==wantT)return;
      if(!(r.n in best)||r.l<best[r.n].l) best[r.n]={n:r.n,f:r.f,l:r.l,u:r.u,v:r.v}; });
  });
  var rank=Object.values(best).sort(function(a,b){return a.l-b.l;}).slice(0,10);
  state.leadRank=best;
  var iso0=sel.map(function(i){return DATA.dates[i]?DATA.dates[i].iso:'';}).join(' · ');
  panel.innerHTML='<div class="trp-h">🎯 '+iso0+' '+(anyPeak?'頂':'底')+'轉折 · 領先指標排名 (實測lead)</div>'+
    (rank.length?rank.map(function(r,i){ return '<div class="trp-r"><span>'+(i+1)+'. '+r.n+' <span style="opacity:.6">['+r.f+']</span></span><span class="trp-l" style="color:'+(r.l<0?'var(--green)':'var(--amber)')+'">'+(r.l>0?'+':'')+r.l+r.u+'</span></div>'; }).join('')
      :'<div class="trp-r">此轉折在各指標配對窗內無訊號紀錄</div>')+
    '<div style="opacity:.55;margin-top:3px">負=領先轉折 · 資料: 45轉折×34指標驗證(1999-2026)</div>';
  panel.style.display='block';
};

/* A3.1 raster 繪製 */
function drawSigR(){ var cv=document.getElementById('chSigR'); if(!cv)return;
  var pane=document.getElementById('paneSigR'); if(pane&&(pane.classList.contains('collapsed')||pane.classList.contains('pane-hidden')))return;
  var o=setupCanvas(cv),ctx=o.ctx,w=o.w,hh=o.h; ctx.clearRect(0,0,w,hh);
  var si=startIdx(),n=visEnd()-si; if(n<2)return;
  var rows=SIGR.length, top=4, bot=12, rh=(hh-top-bot)/rows;
  var L=118;
  function xf(k){ return L+(k/(n-1))*(w-L-PAD.r); }
  /* turn vlines */
  TURN_EVENTS.forEach(function(t){ if(t.idx<si||t.idx>=si+n)return; var x=xf(t.idx-si);
    ctx.strokeStyle=t.dir==='top'?'rgba(200,51,44,.55)':'rgba(14,140,90,.55)';
    ctx.lineWidth=t.kind==='major'?1.4:.7; ctx.setLineDash([3,3]);
    ctx.beginPath(); ctx.moveTo(x,top); ctx.lineTo(x,hh-bot); ctx.stroke(); ctx.setLineDash([]); });
  var totalVis=0;
  SIGR.forEach(function(s,r){ var y0=top+r*rh, yc=y0+rh/2;
    if(r%2){ ctx.fillStyle='rgba(148,163,184,.07)'; ctx.fillRect(L,y0,w-L-PAD.r,rh); }
    ctx.fillStyle=getCSS('--txt-1'); ctx.font='8.5px sans-serif'; ctx.textAlign='left';
    var lbl=s.n.length>15?s.n.slice(0,14)+'…':s.n;
    ctx.fillText(lbl,3,yc+1);
    ctx.fillStyle=getCSS('--txt-3'); ctx.font='7.5px sans-serif';
    ctx.fillText('中位'+(s.med>0?'+':'')+s.med+s.u,3,yc+9);
    ctx.strokeStyle=s.w==='TOP'?'#C8332C':'#0E8C5A'; ctx.lineWidth=1.6;
    s.idx.forEach(function(ix){ if(ix<si||ix>=si+n)return; totalVis++; var x=xf(ix-si);
      ctx.beginPath(); ctx.moveTo(x,yc-rh*0.32); ctx.lineTo(x,yc+rh*0.32); ctx.stroke(); });
  });
  var rd=document.getElementById('rdSigR'); if(rd)rd.textContent='可視窗內訊號 '+totalVis+' 筆 · 12指標 · 轉折 '+TURN_EVENTS.filter(function(t){return t.idx>=si&&t.idx<si+n;}).length+' 個';
}
/* redraw 包裝: 保留原功能 + raster */
var __redraw0=redraw;
redraw=function(){ __redraw0(); requestAnimationFrame(drawSigR); };
setTimeout(function(){ drawSigR(); if(typeof updateTurnHint==='function')updateTurnHint(); },300);
window.addEventListener('resize',function(){ setTimeout(drawSigR,120); });
</script>
</body>'''
late = (late.replace('__LEAD_DB__', json.dumps(LEAD_DB, ensure_ascii=False, separators=(',', ':')))
            .replace('__SIGR__', json.dumps(SIGR, ensure_ascii=False, separators=(',', ':')))
            .replace('__LEAGUE_ROWS__', json.dumps(LEAGUE_ROWS, ensure_ascii=False, separators=(',', ':')))
            .replace('__PEAKS__', json.dumps(peaks)).replace('__TROUGHS__', json.dumps(troughs)))
h = h.replace('</body>', late, 1)

open(OUT, 'w', encoding='utf-8').write(h)
print('saved', OUT, f'{len(h)/1024:.0f}KB (原 {2330353/1024:.0f}KB)')
