# -*- coding: utf-8 -*-
"""NDX轉折點×領先指標 Excel: 方法論 + 轉折點 + 指標排行(活統計) + 逐轉折明細 + 訊號明細 + 日線趨勢線(活公式)"""
import pandas as pd, numpy as np, json, glob, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

OUT = 'NDX_TurningPoints_LeadingIndicators_2026.xlsx'
ARIAL = 'Arial'
F_T1 = Font(name=ARIAL, bold=True, size=12)
F_HDR = Font(name=ARIAL, bold=True, size=9)
F_TXT = Font(name=ARIAL, size=9)
F_GRN = Font(name=ARIAL, size=9, color='008000')
FILL_HDR = PatternFill('solid', fgColor='D9D9D9')
FILL_TOP = PatternFill('solid', fgColor='FFC7CE')
FILL_BOT = PatternFill('solid', fgColor='C6EFCE')
FILL_LEAD = PatternFill('solid', fgColor='C6EFCE')
FILL_CONF = PatternFill('solid', fgColor='FFEB9C')

fam_names = {'trend_momentum':'趨勢動能','volatility':'波動率','credit_breadth':'信用廣度','volume':'量價','monthly_pillars':'月度支柱'}

full = json.load(open('data/families_full.json'))
league = json.load(open('data/league.json'))
tpM = pd.read_csv('data/turning_points_MAJOR.csv').iloc[1:].reset_index(drop=True)
sigs = []
for f in sorted(glob.glob('data/signals_*.csv')):
    s = pd.read_csv(f); s['family'] = f.split('signals_')[1].replace('.csv','')
    sigs.append(s)
SIG = pd.concat(sigs, ignore_index=True)

wb = openpyxl.Workbook()

# ===== 00 方法論 =====
ws = wb.active; ws.title = '00_方法論'
rows0 = [
("NASDAQ 100 趨勢轉折 × 領先指標 分析 (2026-07-26)", ""),
("目標", "找出NDX趨勢轉折(見頂/見底)的領先指標: 客觀偵測45個主要轉折(1999-2026), 對五大指標族的量化規則逐一量測領先/滯後天數, 經對抗性驗證。"),
("轉折定義", "ZigZag演算法(無前視): 收盤自峰回落≥15%確認一個TOP, 自谷回升≥15%確認一個BOTTOM → 45個主要轉折(02表)。±8%版=163個中級轉折(輔助統計與假訊號判定)。"),
("數據", "①NDX真實日線2016-07-08..2026-07-10(原工作簿02A); ②1999-01..2016-07用Nasdaq Composite日報酬鏈接(arch套件學術數據, 重疊期625日報酬相關0.989); ③VIX 2014起; ④HY OAS/廣度/合成分 2016-07起(原工作簿); ⑤成交量1999-2016(Composite); ⑥月度七支柱1976-2026(前次50年引擎)。"),
("評估協定", "lead=訊號日−轉折日(交易日, 負=領先)。配對窗[轉折-90交易日, 轉折+5交易日], 取窗內最早訊號。假訊號=訊號後90交易日內無同向主要/中級轉折。判定: LEADING(中位lead<-5) / COINCIDENT(-5..+5) / CONFIRMING(>+5)。"),
("執行方式", "五個獨立分析agent(趨勢動能/波動率/信用廣度/量價/月度支柱)按同一協定計算 → 五個對抗性驗證agent獨立重算抽查(規則重現/lead重算/前視偏誤專查) → 通過後彙總。驗證結果見03表『驗證』欄。"),
("工作表", "01_指標排行(統計=活公式) | 02_轉折點45個 | 03_指標明細(全部規則+驗證) | 04_逐轉折lead明細 | 05_訊號明細(全部訊號日) | 06_日線與趨勢線(活公式SMA) "),
("核心結論", league.get('headline','見01表')),
("限制(誠實揭露)", "①主要轉折僅45個, 統計置信度有限; ②信用/廣度族只覆蓋2016後(12個主要轉折), 量價族只覆蓋1999-2016; ③規則參數為合理預設而非優化, 但仍屬in-sample檢視; ④「領先」為統計中位數, 個別轉折可能失效; ⑤2016年前價格為Composite代理。"),
]
for i, (a, b) in enumerate(rows0, 1):
    ws.cell(row=i, column=1, value=a).font = F_T1 if i == 1 else Font(name=ARIAL, bold=True, size=9)
    c = ws.cell(row=i, column=2, value=b); c.font = F_TXT; c.alignment = Alignment(wrap_text=True, vertical='top')
ws.column_dimensions['A'].width = 20; ws.column_dimensions['B'].width = 150

# ===== 02 轉折點 (先建, 供引用) =====
ws2 = wb.create_sheet('02_轉折點45個')
ws2.cell(row=1, column=1, value='主要轉折點 (ZigZag ±15%, 1999-2026) | 統計=活公式').font = F_T1
for c, h in enumerate(['日期','類型','價位','其後走勢%','走勢迄'], 1):
    cell = ws2.cell(row=2, column=c, value=h); cell.font = F_HDR; cell.fill = FILL_HDR
for i, r in tpM.iterrows():
    rr = 3 + i
    ws2.cell(row=rr, column=1, value=str(r['date'])).font = F_TXT
    tcell = ws2.cell(row=rr, column=2, value=r['type']); tcell.font = F_TXT
    tcell.fill = FILL_TOP if r['type'] == 'TOP' else FILL_BOT
    ws2.cell(row=rr, column=3, value=float(r['price'])).font = F_TXT
    mc = ws2.cell(row=rr, column=4, value=float(r['ensuing_move'])); mc.font = F_TXT; mc.number_format = '+0.0%'
    ws2.cell(row=rr, column=5, value=str(r['ensuing_end'])).font = F_TXT
last2 = 2 + len(tpM)
stats2 = [
    ('TOP數', f'=COUNTIF(B3:B{last2},"TOP")'), ('BOTTOM數', f'=COUNTIF(B3:B{last2},"BOTTOM")'),
    ('TOP後平均跌幅', f'=AVERAGEIF(B3:B{last2},"TOP",D3:D{last2})'),
    ('BOTTOM後平均升幅', f'=AVERAGEIF(B3:B{last2},"BOTTOM",D3:D{last2})'),
]
for j, (nm, fx) in enumerate(stats2):
    ws2.cell(row=last2+2+j, column=1, value=nm).font = F_HDR
    cell = ws2.cell(row=last2+2+j, column=3, value=fx); cell.font = F_GRN
    if '幅' in nm: cell.number_format = '+0.0%'
for c, w in enumerate([12,10,10,11,12], 1): ws2.column_dimensions[get_column_letter(c)].width = w
ws2.freeze_panes = 'A3'

# ===== 03 指標明細 =====
ws3 = wb.create_sheet('03_指標明細')
ws3.cell(row=1, column=1, value='全部指標: 客觀規則 + 領先性量測 + 對抗性驗證結果 | lead單位: 交易日(月度支柱族=月), 負=領先').font = F_T1
hdr3 = ['族','指標','警訊','量化規則','覆蓋','訊號數','TOP命中','BOT命中','中位lead','平均lead','假訊號率','判定','族驗證','備註']
for c, h in enumerate(hdr3, 1):
    cell = ws3.cell(row=2, column=c, value=h); cell.font = F_HDR; cell.fill = FILL_HDR
r3 = 3
for fam in full['families']:
    for ind in fam['indicators']:
        vals = [fam_names.get(fam['family'], fam['family']), ind['name'], ind['warn_type'], ind['rule'], ind['coverage'],
                ind['n_signals'], ind['hits'].split(' ')[0] if isinstance(ind.get('hits'), str) else f"{ind.get('tops_hit','')}/{ind.get('tops_evaluated','')}",
                ind['hits'].split(' ')[1] if isinstance(ind.get('hits'), str) else '',
                ind['median_lead'], ind['mean_lead'], ind['fp_rate'], ind['verdict'], fam['verified'], ind['notes']]
        for c, v in enumerate(vals, 1):
            cell = ws3.cell(row=r3, column=c, value=v); cell.font = F_TXT
            cell.alignment = Alignment(wrap_text=True, vertical='top')
        ws3.cell(row=r3, column=11).number_format = '0.0%'
        vcell = ws3.cell(row=r3, column=12)
        if ind['verdict'] == 'LEADING': vcell.fill = FILL_LEAD
        elif ind['verdict'] == 'CONFIRMING': vcell.fill = FILL_CONF
        r3 += 1
for c, w in enumerate([9,24,7,46,16,7,8,8,8,8,8,12,11,34], 1): ws3.column_dimensions[get_column_letter(c)].width = w
ws3.freeze_panes = 'C3'

# ===== 01 指標排行 (活公式引用03) =====
ws1 = wb.create_sheet('01_指標排行', 1)
ws1.cell(row=1, column=1, value='領先指標排行榜 — 按中位lead排序(越負越領先) | 完整規則見03表 | ⭐=HTML raster入選').font = F_T1
hdr1 = ['排名','指標','族','警訊','判定','中位lead','命中率摘要','假訊號率','入選']
for c, h in enumerate(hdr1, 1):
    cell = ws1.cell(row=2, column=c, value=h); cell.font = F_HDR; cell.fill = FILL_HDR
rows_sorted = sorted(league['rows'], key=lambda x: x.get('median_lead', 0))
for i, r in enumerate(rows_sorted, 1):
    rr = 2 + i
    vals = [i, r['indicator'], fam_names.get(r['family'], r['family']), r['warn_type'], r['verdict'],
            r['median_lead'], r['hits'], r['fp_rate'], '⭐' if r['indicator'] in league['picked'] else '']
    for c, v in enumerate(vals, 1):
        cell = ws1.cell(row=rr, column=c, value=v); cell.font = F_TXT
    ws1.cell(row=rr, column=8).number_format = '0.0%'
    if r['verdict'] == 'LEADING': ws1.cell(row=rr, column=5).fill = FILL_LEAD
    elif r['verdict'] == 'CONFIRMING': ws1.cell(row=rr, column=5).fill = FILL_CONF
last1 = 2 + len(rows_sorted)
sm = [('LEADING指標數', f'=COUNTIF(E3:E{last1},"LEADING")'), ('CONFIRMING指標數', f'=COUNTIF(E3:E{last1},"CONFIRMING")'),
      ('LEADING之中位lead平均', f'=AVERAGEIF(E3:E{last1},"LEADING",F3:F{last1})')]
for j, (nm, fx) in enumerate(sm):
    ws1.cell(row=last1+2+j, column=2, value=nm).font = F_HDR
    ws1.cell(row=last1+2+j, column=6, value=fx).font = F_GRN
for c, w in enumerate([5,26,9,7,12,9,16,9,5], 1): ws1.column_dimensions[get_column_letter(c)].width = w
ws1.freeze_panes = 'A3'

# ===== 04 逐轉折 lead 明細 =====
ws4 = wb.create_sheet('04_逐轉折lead明細')
ws4.cell(row=1, column=1, value='每個主要轉折 × 每個指標的 lead(交易日/月度族=月) | 空=該轉折無訊號或不在覆蓋期 | 負=領先').font = F_T1
all_inds = []
for fam in full['families']:
    for ind in fam['indicators']:
        all_inds.append((fam['family'], ind))
turn_keys = [(str(r['date']), r['type']) for _, r in tpM.iterrows()]
ws4.cell(row=2, column=1, value='轉折日期').font = F_HDR; ws4.cell(row=2, column=1).fill = FILL_HDR
ws4.cell(row=2, column=2, value='類型').font = F_HDR; ws4.cell(row=2, column=2).fill = FILL_HDR
for c, (famk, ind) in enumerate(all_inds, 3):
    cell = ws4.cell(row=2, column=c, value=f"{ind['name']}"); cell.font = F_HDR; cell.fill = FILL_HDR
    cell.alignment = Alignment(wrap_text=True, vertical='top')
lead_map = {}
for famk, ind in all_inds:
    for pt in ind['per_turn']:
        lead_map[(ind['name'], pt['turn_date'], pt['turn_type'])] = pt['lead_days']
for i, (td, tt) in enumerate(turn_keys):
    rr = 3 + i
    ws4.cell(row=rr, column=1, value=td).font = F_TXT
    tc = ws4.cell(row=rr, column=2, value=tt); tc.font = F_TXT
    tc.fill = FILL_TOP if tt == 'TOP' else FILL_BOT
    for c, (famk, ind) in enumerate(all_inds, 3):
        v = lead_map.get((ind['name'], td, tt))
        if v is None and famk == 'monthly_pillars':
            v = lead_map.get((ind['name'], td[:7], tt))
        if v is not None:
            cell = ws4.cell(row=rr, column=c, value=v); cell.font = F_TXT
            if v < -5: cell.fill = FILL_LEAD
            elif v > 5: cell.fill = FILL_CONF
ws4.column_dimensions['A'].width = 11; ws4.column_dimensions['B'].width = 9
for c in range(3, 3+len(all_inds)): ws4.column_dimensions[get_column_letter(c)].width = 11
ws4.freeze_panes = 'C3'

# ===== 05 訊號明細 =====
ws5 = wb.create_sheet('05_訊號明細')
ws5.cell(row=1, column=1, value=f'全部訊號日 ({len(SIG)}筆) | 統計=活公式').font = F_T1
for c, h in enumerate(['日期','指標','警訊','族'], 1):
    cell = ws5.cell(row=2, column=c, value=h); cell.font = F_HDR; cell.fill = FILL_HDR
SIGs = SIG.sort_values('date').reset_index(drop=True)
for i, r in SIGs.iterrows():
    rr = 3 + i
    ws5.cell(row=rr, column=1, value=str(r['date'])[:10]).font = F_TXT
    ws5.cell(row=rr, column=2, value=r['indicator']).font = F_TXT
    wc = ws5.cell(row=rr, column=3, value=r['warn_type']); wc.font = F_TXT
    wc.fill = FILL_TOP if r['warn_type'] == 'TOP' else FILL_BOT
    ws5.cell(row=rr, column=4, value=fam_names.get(r['family'], r['family'])).font = F_TXT
last5 = 2 + len(SIGs)
for j, (nm, fx) in enumerate([('TOP警訊數', f'=COUNTIF(C3:C{last5},"TOP")'), ('BOTTOM警訊數', f'=COUNTIF(C3:C{last5},"BOTTOM")')]):
    ws5.cell(row=last5+2+j, column=1, value=nm).font = F_HDR
    ws5.cell(row=last5+2+j, column=3, value=fx).font = F_GRN
for c, w in enumerate([11,30,8,10], 1): ws5.column_dimensions[get_column_letter(c)].width = w
ws5.freeze_panes = 'A3'

# ===== 06 日線與趨勢線 (活公式) =====
dd = pd.read_csv('data/ndx_daily_spliced.csv')
dd = dd.dropna(subset=['ndx']).reset_index(drop=True)
ws6 = wb.create_sheet('06_日線與趨勢線')
ws6.cell(row=1, column=1, value='日線 + 趨勢線(活公式) | B=收盤(2016-07前=Composite鏈接) | C-F=活公式: SMA50/SMA200/距252日高/ZigZag轉折標記(查表) | 修改B欄即全表重算').font = F_T1
for c, h in enumerate(['日期','收盤','SMA50(式)','SMA200(式)','距252日高(式)','主要轉折(式)','來源'], 1):
    cell = ws6.cell(row=2, column=c, value=h); cell.font = F_HDR; cell.fill = FILL_HDR
R0 = 3
tp_lookup_start = R0
for i, r in dd.iterrows():
    rr = R0 + i
    ws6.cell(row=rr, column=1, value=str(r['date'])[:10]).font = F_TXT
    ws6.cell(row=rr, column=2, value=round(float(r['ndx']), 2)).font = F_TXT
    if i >= 49: ws6.cell(row=rr, column=3, value=f'=AVERAGE(B{rr-49}:B{rr})').font = F_TXT
    if i >= 199: ws6.cell(row=rr, column=4, value=f'=AVERAGE(B{rr-199}:B{rr})').font = F_TXT
    if i >= 251: ws6.cell(row=rr, column=5, value=f'=B{rr}/MAX(B{rr-251}:B{rr})-1').font = F_TXT
    ws6.cell(row=rr, column=6, value=f"=IFERROR(INDEX('02_轉折點45個'!B:B,MATCH(A{rr},'02_轉折點45個'!A:A,0)),\"\")").font = F_TXT
    ws6.cell(row=rr, column=7, value=r['src']).font = F_TXT
for c, w in enumerate([11,10,10,10,10,10,15], 1): ws6.column_dimensions[get_column_letter(c)].width = w
ws6.freeze_panes = 'A3'

wb.save(OUT)
print('saved', OUT)
