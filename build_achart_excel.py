# -*- coding: utf-8 -*-
"""ndx_turning_TECHNICAL_INDICATOR.xlsx — A-Chart 格式 Excel 版
01表 = A0面板同組技術指標(MA5/10/20/50/100/200+BOLL+RSI14+MACD, 活公式) on dashboard真實OHLC 2020-2026
+ 三區zone + 轉折標記 + 當日訊號數; 02-05表 = 轉折/排行/lead矩陣/訊號明細"""
import pandas as pd, numpy as np, json, re, glob, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

SRC = '/root/.claude/uploads/0bed5a0b-c49b-533e-8899-bcd26a47a6bd/2d295034-Macro_dashboard_R15.12_0728_hk21.00.html'
OUT = 'ndx_turning_TECHNICAL_INDICATOR.xlsx'

h = open(SRC, encoding='utf-8').read()
m = re.search(r'const DATA=(\{)', h)
DATA, _ = json.JSONDecoder().raw_decode(h[m.start(1):])
ISO = [d['iso'] for d in DATA['dates']]
ta = DATA['ta']
N = len(ISO)
zone_map = {2: 'EASY', 1: 'UNCERTAIN', 0: 'HARD'}

tpM = pd.read_csv('data/turning_points_MAJOR.csv').iloc[1:].reset_index(drop=True)
league = json.load(open('data/league.json'))
full = json.load(open('data/families_full.json'))
sigs = []
for f in sorted(glob.glob('data/signals_*.csv')):
    s = pd.read_csv(f); s['family'] = f.split('signals_')[1].replace('.csv', '')
    sigs.append(s)
SIG = pd.concat(sigs, ignore_index=True)
SIG['date'] = SIG['date'].astype(str).str[:10]
FAMN = {'trend_momentum': '趨勢動能', 'volatility': '波動率', 'credit_breadth': '信用廣度',
        'volume': '量價', 'monthly_pillars': '月度支柱'}

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

wb = openpyxl.Workbook()

# ===== 00 說明 =====
ws = wb.active; ws.title = '00_說明'
rows0 = [
("ndx_turning_(TECHNICAL_INDICATOR) — A-Chart 格式 Excel 版 (2026-07-28)", ""),
("對應", "HTML版=Macro_dashboard R15.12 A-Chart 頁完整保留(B/C/D已移除)+A3.1訊號raster+A3.2排行榜+TURNS領先排名實裝。本Excel=同一數據的表格版。"),
("01表", "A0面板同組技術指標(活公式): dashboard內嵌真實NDX OHLC/成交量(2020-01-02..2026-07-27, 1649交易日) + MA5/10/20/50/100/200 + BOLL(20,2σ) + RSI14(Wilder) + MACD(12,26,9) + 三區制度zone(A1.8A Fable) + ZigZag轉折標記 + 當日領先訊號數(COUNTIF活算)。修改F欄(收盤)即全表重算。"),
("02-05表", "02=45個主要轉折(1999-2026, ±15%) | 03=34指標領先性排行(45轉折驗證) | 04=逐轉折×逐指標lead矩陣 | 05=全部2037個訊號日。"),
("驗證", "01表公式與dashboard預計算陣列交叉核對(sma200/rsi/macd末值一致, 見01表底部核對區); 34指標領先性經5個對抗性驗證agent重算(見前次交付03表)。"),
("限制", "01表軸=dashboard價格軸(2020起); 1999-2019轉折見02表, 完整日線見repo data/ndx_daily_spliced.csv。RSI/MACD前若干行為暖機期。"),
]
for i, (a, b) in enumerate(rows0, 1):
    ws.cell(row=i, column=1, value=a).font = F_T1 if i == 1 else Font(name=ARIAL, bold=True, size=9)
    c = ws.cell(row=i, column=2, value=b); c.font = F_TXT; c.alignment = Alignment(wrap_text=True, vertical='top')
ws.column_dimensions['A'].width = 14; ws.column_dimensions['B'].width = 150

# ===== 02 轉折點 (先建供01表查表) =====
ws2 = wb.create_sheet('02_轉折點45')
ws2.cell(row=1, column=1, value='主要轉折點 (ZigZag ±15%, 1999-2026) | 2020後14個落在01表軸內').font = F_T1
for c, hd in enumerate(['日期','類型','價位','其後走勢%','走勢迄'], 1):
    cell = ws2.cell(row=2, column=c, value=hd); cell.font = F_HDR; cell.fill = FILL_HDR
for i, r in tpM.iterrows():
    rr = 3 + i
    ws2.cell(row=rr, column=1, value=str(r['date'])).font = F_TXT
    tc = ws2.cell(row=rr, column=2, value=r['type']); tc.font = F_TXT
    tc.fill = FILL_TOP if r['type'] == 'TOP' else FILL_BOT
    ws2.cell(row=rr, column=3, value=float(r['price'])).font = F_TXT
    mc = ws2.cell(row=rr, column=4, value=float(r['ensuing_move'])); mc.font = F_TXT; mc.number_format = '+0.0%'
    ws2.cell(row=rr, column=5, value=str(r['ensuing_end'])).font = F_TXT
for c, w in enumerate([12,10,10,11,12], 1): ws2.column_dimensions[get_column_letter(c)].width = w
ws2.freeze_panes = 'A3'

# ===== 05 訊號明細 (先建供01表COUNTIF) =====
ws5 = wb.create_sheet('05_訊號明細')
SIGs = SIG.sort_values('date').reset_index(drop=True)
ws5.cell(row=1, column=1, value=f'全部訊號日 ({len(SIGs)}筆) | 01表當日訊號數以COUNTIFS引用本表').font = F_T1
for c, hd in enumerate(['日期','指標','警訊','族'], 1):
    cell = ws5.cell(row=2, column=c, value=hd); cell.font = F_HDR; cell.fill = FILL_HDR
for i, r in SIGs.iterrows():
    rr = 3 + i
    ws5.cell(row=rr, column=1, value=r['date']).font = F_TXT
    ws5.cell(row=rr, column=2, value=r['indicator']).font = F_TXT
    wc = ws5.cell(row=rr, column=3, value=r['warn_type']); wc.font = F_TXT
    wc.fill = FILL_TOP if r['warn_type'] == 'TOP' else FILL_BOT
    ws5.cell(row=rr, column=4, value=FAMN.get(r['family'], r['family'])).font = F_TXT
for c, w in enumerate([11,30,8,10], 1): ws5.column_dimensions[get_column_letter(c)].width = w
ws5.freeze_panes = 'A3'
SIG_LAST = 2 + len(SIGs)

# ===== 01 A0技術指標 (活公式) =====
ws1 = wb.create_sheet('01_A0技術指標', 1)
ws1.cell(row=1, column=1, value='A0-Nasdaq 100 · dashboard真實OHLC(2020-01-02..2026-07-27) + A-Chart同組技術指標(活公式) | B-F=OHLC值 G=量 H-M=MA5/10/20/50/100/200 N-P=BOLL Q-T=RSI14(Wilder) U-X=MACD(12,26,9) Y=三區zone Z=轉折 AA/AB=當日頂/底訊號數(式)').font = F_T1
hdr1 = ['日期','開','高','低','收','量','MA5(式)','MA10(式)','MA20(式)','MA50(式)','MA100(式)','MA200(式)',
        'BOLL中(式)','BOLL上(式)','BOLL下(式)','漲U(式)','跌D(式)','AvgU14(式)','AvgD14(式)','RSI14(式)',
        'EMA12(式)','EMA26(式)','MACD(式)','Signal9(式)','Hist(式)','三區zone','轉折(式)','頂訊(式)','底訊(式)']
for c, hd in enumerate(hdr1, 1):
    cell = ws1.cell(row=2, column=c, value=hd); cell.font = F_HDR; cell.fill = FILL_HDR
R0 = 3
for i in range(N):
    r = R0 + i
    ws1.cell(row=r, column=1, value=ISO[i]).font = F_TXT
    for c, key in [(2,'open'),(3,'high'),(4,'low'),(5,'close'),(6,'vol')]:
        v = ta[key][i]
        if v is not None:
            ws1.cell(row=r, column=c, value=round(float(v),2)).font = F_TXT
    for c, n in [(7,5),(8,10),(9,20),(10,50),(11,100),(12,200)]:
        if i >= n-1:
            ws1.cell(row=r, column=c, value=f'=AVERAGE(E{r-n+1}:E{r})').font = F_TXT
    if i >= 19:
        ws1.cell(row=r, column=13, value=f'=I{r}').font = F_TXT
        ws1.cell(row=r, column=14, value=f'=I{r}+2*STDEV(E{r-19}:E{r})').font = F_TXT
        ws1.cell(row=r, column=15, value=f'=I{r}-2*STDEV(E{r-19}:E{r})').font = F_TXT
    if i >= 1:
        ws1.cell(row=r, column=16, value=f'=MAX(E{r}-E{r-1},0)').font = F_TXT
        ws1.cell(row=r, column=17, value=f'=MAX(E{r-1}-E{r},0)').font = F_TXT
    if i == 14:
        ws1.cell(row=r, column=18, value=f'=AVERAGE(P{R0+1}:P{r})').font = F_TXT
        ws1.cell(row=r, column=19, value=f'=AVERAGE(Q{R0+1}:Q{r})').font = F_TXT
    elif i > 14:
        ws1.cell(row=r, column=18, value=f'=(R{r-1}*13+P{r})/14').font = F_TXT
        ws1.cell(row=r, column=19, value=f'=(S{r-1}*13+Q{r})/14').font = F_TXT
    if i >= 14:
        ws1.cell(row=r, column=20, value=f'=IF(S{r}=0,100,100-100/(1+R{r}/S{r}))').font = F_TXT
    if i == 11: ws1.cell(row=r, column=21, value=f'=AVERAGE(E{R0}:E{r})').font = F_TXT
    elif i > 11: ws1.cell(row=r, column=21, value=f'=E{r}*2/13+U{r-1}*11/13').font = F_TXT
    if i == 25: ws1.cell(row=r, column=22, value=f'=AVERAGE(E{R0}:E{r})').font = F_TXT
    elif i > 25: ws1.cell(row=r, column=22, value=f'=E{r}*2/27+V{r-1}*25/27').font = F_TXT
    if i >= 25: ws1.cell(row=r, column=23, value=f'=U{r}-V{r}').font = F_TXT
    if i == 33: ws1.cell(row=r, column=24, value=f'=AVERAGE(W{r-8}:W{r})').font = F_TXT
    elif i > 33: ws1.cell(row=r, column=24, value=f'=W{r}*2/10+X{r-1}*8/10').font = F_TXT
    if i >= 33: ws1.cell(row=r, column=25, value=f'=W{r}-X{r}').font = F_TXT
    zc = ws1.cell(row=r, column=26, value=zone_map.get(DATA['ehmZoneA'][i], '')); zc.font = F_TXT
    if DATA['ehmZoneA'][i] == 2: zc.fill = FILL_BOT
    elif DATA['ehmZoneA'][i] == 0: zc.fill = FILL_TOP
    ws1.cell(row=r, column=27, value=f"=IFERROR(INDEX('02_轉折點45'!B:B,MATCH(A{r},'02_轉折點45'!A:A,0)),\"\")").font = F_TXT
    ws1.cell(row=r, column=28, value=f'=COUNTIFS(\'05_訊號明細\'!A:A,A{r},\'05_訊號明細\'!C:C,"TOP")').font = F_TXT
    ws1.cell(row=r, column=29, value=f'=COUNTIFS(\'05_訊號明細\'!A:A,A{r},\'05_訊號明細\'!C:C,"BOTTOM")').font = F_TXT
LAST1 = R0 + N - 1
# 核對區: 與dashboard預計算陣列比對
chk = LAST1 + 2
ws1.cell(row=chk, column=1, value='核對區(dashboard預計算值 vs 本表公式, 末交易日)').font = F_HDR
checks = [('MA200', 12, ta['sma200'][N-1]), ('RSI14', 20, ta['rsi'][N-1]), ('MACD', 23, ta['macd'][N-1]), ('Signal', 24, ta['macdSig'][N-1])]
for j, (nm, col, dashv) in enumerate(checks):
    ws1.cell(row=chk+1+j, column=1, value=nm).font = F_TXT
    ws1.cell(row=chk+1+j, column=2, value=round(float(dashv), 2)).font = F_TXT
    L = get_column_letter(col)
    ws1.cell(row=chk+1+j, column=3, value=f'={L}{LAST1}').font = F_GRN
    ws1.cell(row=chk+1+j, column=4, value=f'=IF(ABS(B{chk+1+j}-C{chk+1+j})<MAX(0.6,ABS(B{chk+1+j})*0.002),"一致✓","偏差!")').font = F_GRN
for c, w in enumerate([11]+[9]*24+[11,8,7,7], 1): ws1.column_dimensions[get_column_letter(c)].width = w
ws1.freeze_panes = 'B3'

# ===== 03 排行 =====
ws3 = wb.create_sheet('03_領先指標排行')
ws3.cell(row=1, column=1, value='34指標領先性排行 (45轉折×5族×對抗性驗證) | 中位lead越負越領先 | ⭐=A3.1 raster入選').font = F_T1
hdr3 = ['排名','指標','族','警訊','判定','中位lead','命中','FP率','⭐']
for c, hd in enumerate(hdr3, 1):
    cell = ws3.cell(row=2, column=c, value=hd); cell.font = F_HDR; cell.fill = FILL_HDR
rows_sorted = sorted(league['rows'], key=lambda x: x.get('median_lead', 0))
for i, r in enumerate(rows_sorted, 1):
    rr = 2 + i
    unit = '月' if r['family'] == 'monthly_pillars' else 'd'
    vals = [i, r['indicator'], FAMN.get(r['family'], r['family']), r['warn_type'], r['verdict'],
            f"{r['median_lead']:+.0f}{unit}", r['hits'], r['fp_rate'], '⭐' if r['indicator'] in league['picked'] else '']
    for c, v in enumerate(vals, 1):
        ws3.cell(row=rr, column=c, value=v).font = F_TXT
    ws3.cell(row=rr, column=8).number_format = '0.0%'
    if r['verdict'] == 'LEADING': ws3.cell(row=rr, column=5).fill = FILL_LEAD
    elif r['verdict'] == 'CONFIRMING': ws3.cell(row=rr, column=5).fill = FILL_CONF
for c, w in enumerate([5,28,9,7,12,9,15,8,4], 1): ws3.column_dimensions[get_column_letter(c)].width = w
ws3.freeze_panes = 'A3'

# ===== 04 lead矩陣 =====
ws4 = wb.create_sheet('04_逐轉折lead矩陣')
ws4.cell(row=1, column=1, value='主要轉折 × 指標 lead (交易日, 月度族=月, 負=領先, 空=無訊號/不在覆蓋期)').font = F_T1
all_inds = [(fam['family'], ind) for fam in full['families'] for ind in fam['indicators']]
ws4.cell(row=2, column=1, value='轉折日期').font = F_HDR; ws4.cell(row=2, column=1).fill = FILL_HDR
ws4.cell(row=2, column=2, value='類型').font = F_HDR; ws4.cell(row=2, column=2).fill = FILL_HDR
for c, (famk, ind) in enumerate(all_inds, 3):
    cell = ws4.cell(row=2, column=c, value=ind['name']); cell.font = F_HDR; cell.fill = FILL_HDR
    cell.alignment = Alignment(wrap_text=True, vertical='top')
lead_map = {}
for famk, ind in all_inds:
    for pt in ind['per_turn']:
        lead_map[(ind['name'], pt['turn_date'], pt['turn_type'])] = pt['lead_days']
for i, r in tpM.iterrows():
    rr = 3 + i
    ws4.cell(row=rr, column=1, value=str(r['date'])).font = F_TXT
    tc = ws4.cell(row=rr, column=2, value=r['type']); tc.font = F_TXT
    tc.fill = FILL_TOP if r['type'] == 'TOP' else FILL_BOT
    for c, (famk, ind) in enumerate(all_inds, 3):
        v = lead_map.get((ind['name'], str(r['date']), r['type']))
        if v is None and famk == 'monthly_pillars':
            v = lead_map.get((ind['name'], str(r['date'])[:7], r['type']))
        if v is not None:
            cell = ws4.cell(row=rr, column=c, value=v); cell.font = F_TXT
            if v < -5: cell.fill = FILL_LEAD
            elif v > 5: cell.fill = FILL_CONF
ws4.column_dimensions['A'].width = 11; ws4.column_dimensions['B'].width = 9
for c in range(3, 3 + len(all_inds)): ws4.column_dimensions[get_column_letter(c)].width = 10
ws4.freeze_panes = 'C3'

wb.save(OUT)
print('saved', OUT)
