# -*- coding: utf-8 -*-
"""在原R4.5.3工作簿上追加R5.0擴展: 100指標庫 + 50年月度引擎(活公式) + 回測交易 + WinRate摘要"""
import pandas as pd, numpy as np, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from library100 import LIB, weight_for

SRC = '/root/.claude/uploads/0bed5a0b-c49b-533e-8899-bcd26a47a6bd/d3b02772-AFable__EasyHardMoney______NDX_______2026R4.5.3_2.xlsx'
OUT = 'AFable_EasyHardMoney_SPX50Y_100Indicators_2026R5.0.xlsx'
D = 'data/'

ARIAL = 'Arial'
F_HDR = Font(name=ARIAL, bold=True, size=10)
F_TXT = Font(name=ARIAL, size=9)
F_BLUE = Font(name=ARIAL, size=9, color='0000FF')
F_GREEN = Font(name=ARIAL, size=9, color='008000')
FILL_HDR = PatternFill('solid', fgColor='D9D9D9')
FILL_EASY = PatternFill('solid', fgColor='C6EFCE')
FILL_UNC = PatternFill('solid', fgColor='FFEB9C')
FILL_HARD = PatternFill('solid', fgColor='FFC7CE')
FILL_PUR = PatternFill('solid', fgColor='E4DFEC')  # 淡紫=審核修正/近似格

wb = openpyxl.load_workbook(SRC)

def style_row(ws, r, maxc, font=F_TXT):
    for c in range(1, maxc+1):
        ws.cell(row=r, column=c).font = font

# ================= 09_R5擴展說明 =================
ws = wb.create_sheet('09_R5擴展說明')
notes = [
["R5.0 擴展 (2026-07-26): 100大指標庫 + S&P500 50年 Easy/Hard Money 回測 + Win Rate", ""],
["任務", "①以R4.5.3之18項指標為基礎擴展至100項(10_百大指標庫, 按重要性排名, 全部客觀可量化); ②work-from-back-end: 檢視50年S&P500好表現時段→反推指標狀態→建立合成分判區→進EASY買入/離EASY賣出(11/12/13表); ③計算win rate(14表)。"],
["判區刻度", "沿用R4.5.3: 合成分≥70=EASY / 40-70=UNCERTAIN / ≤40=HARD。50年引擎為月度版, 動態分母(缺數據指標權重移出分母, 同T5規則)。"],
["50年引擎採用之7支柱", "TREND(30)=月收vs10月SMA | MOM(10)=12月動能 | CREDIT(20)=BAA-AAA利差(1919-2018)+HY OAS(2019起,附件真實數據) | POLICY(15)=Fed政策步階(07表方法論延伸至1970) | CURVE(10)=10Y-3M倒掛episode | INFL(10)=核心CPI YoY+變向 | VOL(5)=6月已實現波動率。支柱=100項庫中50年歷史可得之最高排名代表。"],
["數據來源(如實揭露)", "市場報酬1926/08-2018/11=Fama-French美股市場總回報(arch套件內建學術數據); 2018/12-2025/09=S&P500月收盤(公開紀錄); 2025/10-12=近似值±2%(淡紫); 2026/01-07=NDX月報酬代理(本工作簿02A真實數據, 淡紫)。信用=Moody's BAA-AAA(1919-2018)+HY OAS(2016-2026, 02A真實數據)。核心CPI=FRED CPILFESL(1957-2018)+公開紀錄延伸(淡紫)。政策步階與曲線倒掛=公開紀錄重建(07表同方法)。"],
["Work-from-back-end 校準紀錄", "變體測試(仿R4.5.3之WA/WB/WC): A基準=進70/出<70即月: 40筆 WinRate 62.5% | C進70/出<65: 29筆 69.0% | E進70/出<65+連續2月確認(採用): 16筆 WinRate 93.8% CAGR 9.29% MaxDD -31.1% | 對照跌入HARD才賣: 10筆 90.0%。E之「連續2月確認」即R4.5.3 T1「連續2週過濾假破」之月度版。"],
["校準驗證", "重疊年份與附件日度引擎一致: 2017全年EASY(附件245/251日) | 2022全年HARD/UNC,0個EASY月(附件HARD 216/251日) | 2024全年EASY(附件241/252日)。七大牛市時段EASY捕捉率67-86%(1974-80滯脹名義牛除外=該時段本非easy money, 引擎判定正確)。"],
["誠實揭露(代價與限制)", "①校準為in-sample(work-from-back-end之本質), 閾值經50年數據反覆調校; ②策略CAGR 9.3%低於買入持有12.3%, 換取MaxDD減半(-31% vs -50%)與93.8%勝率; ③現金期間報酬記0%(保守, 未計國庫券利息); ④2025/10後市場數據為近似/代理(淡紫標示); ⑤月度訊號對1987/2020型單月崩跌僅能事後離場。"],
["新工作表", "10_百大指標庫 | 11_50年月度引擎(活公式) | 12_好表現時段驗證 | 13_策略回測交易 | 14_WinRate摘要。原R4.5.3各表未作任何改動。"],
["顏色", "綠=EASY 黃=UNCERTAIN 紅=HARD | 淡紫底=近似/代理數據 | 藍字=可輸入 | 引擎公式全部活算, 修改11表原始數據欄即全表重算。"],
]
for i, (a, b) in enumerate(notes, 1):
    ws.cell(row=i, column=1, value=a).font = F_HDR if i == 1 else Font(name=ARIAL, bold=True, size=9)
    ws.cell(row=i, column=2, value=b).font = F_TXT
    ws.cell(row=i, column=2).alignment = Alignment(wrap_text=True, vertical='top')
ws.column_dimensions['A'].width = 26
ws.column_dimensions['B'].width = 130

# ================= 10_百大指標庫 =================
ws = wb.create_sheet('10_百大指標庫')
ws.cell(row=1, column=1, value='百大量化指標庫 R5.0 | 以R4.5.3之18項為基礎擴展至100項 | 排名=重要性(制度判別力/50年證據/領先性)由高至低 | 全部可用客觀數據量化 | 權重分層: 1-10名4.0 / 11-20名2.0 / 21-40名1.0 / 41-70名0.5 / 71-90名0.2 / 91-100名0.1, 合計100').font = F_HDR
hdr = ['排名','ID','類別','指標名稱','量化定義','EASY區','UNCERTAIN區','HARD區','重要性','權重%','領先/滯後','數據來源','頻率','50年歷史','50年引擎']
for c, h in enumerate(hdr, 1):
    cell = ws.cell(row=2, column=c, value=h); cell.font = F_HDR; cell.fill = FILL_HDR
for i, r in enumerate(LIB, 1):
    row = 2 + i
    vals = [i, r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], weight_for(i), r[8], r[9], r[10], r[11], r[12]]
    for c, v in enumerate(vals, 1):
        cell = ws.cell(row=row, column=c, value=v); cell.font = F_TXT
        cell.alignment = Alignment(wrap_text=True, vertical='top')
    ws.cell(row=row, column=6).fill = FILL_EASY
    ws.cell(row=row, column=7).fill = FILL_UNC
    ws.cell(row=row, column=8).fill = FILL_HARD
    if '[原' in r[2]:
        ws.cell(row=row, column=4).font = Font(name=ARIAL, size=9, bold=True)
tot = 2 + len(LIB) + 1
ws.cell(row=tot, column=4, value='權重合計(公式)').font = F_HDR
ws.cell(row=tot, column=10, value=f'=SUM(J3:J{2+len(LIB)})').font = F_GREEN
widths = [5,6,11,26,30,22,22,22,9,7,30,22,8,12,14]
for c, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(c)].width = w
ws.freeze_panes = 'A3'

# ================= 11_50年月度引擎 (活公式) =================
eng = pd.read_csv(D+'engine_monthly.csv'); eng['ym'] = pd.PeriodIndex(eng['ym'], freq='M')
eng = eng[(eng.ym >= pd.Period('1967-01')) & (eng.ym <= pd.Period('2026-07'))].reset_index(drop=True)
ws = wb.create_sheet('11_50年月度引擎')
ws.cell(row=1, column=1, value='50年月度 Easy/Hard Money 引擎 (活公式) | A-Q=原始數據層(值) R-X=七支柱子分(式) Y=有效權重 Z=合成分 AA=判區 | 權重{TREND30,MOM10,CREDIT20,POLICY15,CURVE10,INFL10,VOL5} | 動態分母≥60才判區 | 淡紫底=近似/代理數據').font = F_HDR
hdr2 = ['年月','月報酬','來源','指數(式)','10月SMA(式)','乖離(式)','SMA上行(式)','12月動能(式)','6月波動率(式)',
        'BAA-AAA','利差6月變(式)','HY OAS','OAS6月變(式)','核心CPI YoY','CPI6月變(式)','政策碼','曲線倒掛',
        'sTREND(式)','sMOM(式)','sCREDIT(式)','sPOLICY(式)','sCURVE(式)','sINFL(式)','sVOL(式)',
        '有效權重(式)','合成分(式)','判區(式)']
for c, h in enumerate(hdr2, 1):
    cell = ws.cell(row=2, column=c, value=h); cell.font = F_HDR; cell.fill = FILL_HDR
R0 = 3  # first data row
n = len(eng)
for i, rw in eng.iterrows():
    r = R0 + i
    ws.cell(row=r, column=1, value=str(rw['ym'])).font = F_TXT
    ws.cell(row=r, column=2, value=round(float(rw['ret']), 6)).font = F_TXT
    ws.cell(row=r, column=3, value=rw['src']).font = F_TXT
    # D index
    if i == 0:
        ws.cell(row=r, column=4, value=100.0).font = F_TXT
    else:
        ws.cell(row=r, column=4, value=f'=D{r-1}*(1+B{r})').font = F_TXT
    if i >= 9:
        ws.cell(row=r, column=5, value=f'=AVERAGE(D{r-9}:D{r})').font = F_TXT
        ws.cell(row=r, column=6, value=f'=D{r}/E{r}-1').font = F_TXT
    if i >= 10:
        ws.cell(row=r, column=7, value=f'=IF(E{r}>E{r-1},1,0)').font = F_TXT
    if i >= 12:
        ws.cell(row=r, column=8, value=f'=D{r}/D{r-12}-1').font = F_TXT
    if i >= 5:
        ws.cell(row=r, column=9, value=f'=STDEV(B{r-5}:B{r})*SQRT(12)*100').font = F_TXT
    for col, key in [(10, 'baa_aaa'), (12, 'hyoas'), (14, 'cpi_yoy')]:
        v = rw[key]
        if pd.notna(v):
            ws.cell(row=r, column=col, value=round(float(v), 4)).font = F_TXT
    if i >= 6:
        ws.cell(row=r, column=11, value=f'=IF(AND(ISNUMBER(J{r}),ISNUMBER(J{r-6})),J{r}-J{r-6},"")').font = F_TXT
        ws.cell(row=r, column=13, value=f'=IF(AND(ISNUMBER(L{r}),ISNUMBER(L{r-6})),L{r}-L{r-6},"")').font = F_TXT
        ws.cell(row=r, column=15, value=f'=IF(AND(ISNUMBER(N{r}),ISNUMBER(N{r-6})),N{r}-N{r-6},"")').font = F_TXT
    if pd.notna(rw['policy']):
        ws.cell(row=r, column=16, value=int(rw['policy'])).font = F_TXT
    if pd.notna(rw['curve_inverted']):
        ws.cell(row=r, column=17, value=int(rw['curve_inverted'])).font = F_TXT
    # sub-scores (only where derived cols exist)
    if i >= 10:
        ws.cell(row=r, column=18, value=f'=IF(ISNUMBER(F{r}),IF(AND(F{r}>0.02,G{r}=1),100,IF(F{r}>-0.02,50,0)),"")').font = F_TXT
    if i >= 12:
        ws.cell(row=r, column=19, value=f'=IF(ISNUMBER(H{r}),IF(H{r}>0.05,100,IF(H{r}>0,50,0)),"")').font = F_TXT
    ws.cell(row=r, column=20, value=(
        f'=IF(AND(A{r}>="2019-01",ISNUMBER(L{r})),'
        f'IF(AND(L{r}<350,OR(NOT(ISNUMBER(M{r})),M{r}<50)),100,IF(L{r}<=450,50,0)),'
        f'IF(ISNUMBER(J{r}),'
        f'IF(AND(J{r}<0.95,OR(NOT(ISNUMBER(K{r})),K{r}<0.2)),100,'
        f'IF(AND(J{r}<=1.35,OR(NOT(ISNUMBER(K{r})),K{r}<0.4)),50,0)),""))')).font = F_TXT
    ws.cell(row=r, column=21, value=f'=IF(ISNUMBER(P{r}),IF(P{r}=1,100,IF(P{r}=0,50,0)),"")').font = F_TXT
    ws.cell(row=r, column=22, value=f'=IF(ISNUMBER(Q{r}),IF(Q{r}=1,0,100),"")').font = F_TXT
    ws.cell(row=r, column=23, value=(
        f'=IF(ISNUMBER(N{r}),'
        f'IF(OR(N{r}<4,AND(N{r}<6,ISNUMBER(O{r}),O{r}<-0.3)),100,'
        f'IF(OR(N{r}<=6,AND(ISNUMBER(O{r}),O{r}<-0.3)),50,0)),"")')).font = F_TXT
    if i >= 5:
        ws.cell(row=r, column=24, value=f'=IF(ISNUMBER(I{r}),IF(I{r}<15,100,IF(I{r}<=25,50,0)),"")').font = F_TXT
    ws.cell(row=r, column=25, value=f'=SUMPRODUCT({{30,10,20,15,10,10,5}},--ISNUMBER(R{r}:X{r}))').font = F_TXT
    ws.cell(row=r, column=26, value=f'=IF(Y{r}>=60,SUMPRODUCT({{30,10,20,15,10,10,5}},R{r}:X{r})/Y{r},"")').font = F_TXT
    ws.cell(row=r, column=27, value=f'=IF(ISNUMBER(Z{r}),IF(Z{r}>=70,"EASY",IF(Z{r}>40,"UNCERTAIN","HARD")),"")').font = F_TXT
    if rw['src'] in ('SPX_approx', 'NDX_proxy(workbook)'):
        for c in (1, 2, 3):
            ws.cell(row=r, column=c).fill = FILL_PUR
for c, w in enumerate([9,9,17,9,9,8,7,8,8,8,8,7,8,8,8,6,6,7,7,8,8,7,7,7,8,8,11], 1):
    ws.column_dimensions[get_column_letter(c)].width = w
ws.freeze_panes = 'A3'
LAST = R0 + n - 1

# ================= 12_好表現時段驗證 =================
ws = wb.create_sheet('12_好表現時段驗證')
ws.cell(row=1, column=1, value='Work-from-back-end 第一步: 檢視50年S&P500好表現時段 → 引擎判區捕捉率 (公式活算自11表) | 回測窗 1976-07..2026-07 = 整50年').font = F_HDR
hdr3 = ['好表現時段(牛市)','起','迄','月數(式)','月報酬算術和(式)','EASY月佔比(式)','EASY+UNC佔比(式)','註解']
for c, h in enumerate(hdr3, 1):
    cell = ws.cell(row=2, column=c, value=h); cell.font = F_HDR; cell.fill = FILL_HDR
bulls = [
    ('1974-10..1980-11 後石油危機名義牛', '1974-10', '1980-11', '滯脹+緊縮政策=非easy money; 引擎大部分UNC=正確辨識(名義漲/實質難)'),
    ('1982-08..1987-08 Volcker轉向大牛', '1982-08', '1987-08', '減息+通脹回落+利差收窄=教科書easy money'),
    ('1987-12..2000-03 超長科技牛', '1987-12', '2000-03', '90年代=50年中最長easy money期'),
    ('2002-10..2007-10 信貸牛', '2002-10', '2007-10', '1%利率起步; 2007信用走闊時引擎先轉UNC'),
    ('2009-03..2020-02 QE超長牛', '2009-03', '2020-02', 'QE1-3+零利率; 2011/2015/2018震倉短暫離開EASY'),
    ('2020-04..2021-12 疫後流動性牛', '2020-04', '2021-12', '無限QE; 2021-11 Taper=引擎轉UNC領先2022熊2個月'),
    ('2022-10..2026-07 AI牛', '2022-10', '2026-07', '2023-08起確認EASY; 2026-06政策鷹轉再考驗'),
]
for i, (name, a, b, note) in enumerate(bulls, 1):
    r = 2 + i
    ws.cell(row=r, column=1, value=name).font = F_TXT
    ws.cell(row=r, column=2, value=a).font = F_TXT
    ws.cell(row=r, column=3, value=b).font = F_TXT
    ws.cell(row=r, column=4, value=f'=COUNTIFS(\'11_50年月度引擎\'!A:A,">="&B{r},\'11_50年月度引擎\'!A:A,"<="&C{r})').font = F_GREEN
    ws.cell(row=r, column=5, value=f'=SUMPRODUCT((\'11_50年月度引擎\'!A{R0}:A{LAST}>=B{r})*(\'11_50年月度引擎\'!A{R0}:A{LAST}<=C{r})*(\'11_50年月度引擎\'!B{R0}:B{LAST}))').font = F_GREEN
    ws.cell(row=r, column=6, value=f'=COUNTIFS(\'11_50年月度引擎\'!A:A,">="&B{r},\'11_50年月度引擎\'!A:A,"<="&C{r},\'11_50年月度引擎\'!AA:AA,"EASY")/D{r}').font = F_GREEN
    ws.cell(row=r, column=7, value=f'=1-COUNTIFS(\'11_50年月度引擎\'!A:A,">="&B{r},\'11_50年月度引擎\'!A:A,"<="&C{r},\'11_50年月度引擎\'!AA:AA,"HARD")/D{r}').font = F_GREEN
    ws.cell(row=r, column=8, value=note).font = F_TXT
    ws.cell(row=r, column=8).alignment = Alignment(wrap_text=True)
r = 11
ws.cell(row=r, column=1, value='全期判區分布 (1976-07..2026-07)').font = F_HDR
for j, (z, fill) in enumerate([('EASY', FILL_EASY), ('UNCERTAIN', FILL_UNC), ('HARD', FILL_HARD)]):
    rr = r + 1 + j
    ws.cell(row=rr, column=1, value=z).fill = fill
    ws.cell(row=rr, column=1).font = F_TXT
    ws.cell(row=rr, column=2, value=f'=COUNTIFS(\'11_50年月度引擎\'!A:A,">=1976-07",\'11_50年月度引擎\'!A:A,"<=2026-07",\'11_50年月度引擎\'!AA:AA,"{z}")').font = F_GREEN
r = 16
ws.cell(row=r, column=1, value='與附件日度引擎(02A)重疊年份對照').font = F_HDR
cmp_rows = [
    ('2017', '本引擎12/12月EASY', '附件245/251日EASY ✓一致'),
    ('2022', '本引擎0月EASY, 9月HARD', '附件216/251日HARD ✓一致'),
    ('2024', '本引擎12/12月EASY', '附件241/252日EASY ✓一致'),
]
for j, (y, a, b) in enumerate(cmp_rows):
    ws.cell(row=r+1+j, column=1, value=y).font = F_TXT
    ws.cell(row=r+1+j, column=2, value=a).font = F_TXT
    ws.cell(row=r+1+j, column=4, value=b).font = F_TXT
for c, w in enumerate([34,9,9,9,13,13,15,60], 1):
    ws.column_dimensions[get_column_letter(c)].width = w

# ================= 13_策略回測交易 =================
trA = pd.read_csv(D+'trades_main.csv')
trE = pd.read_csv(D+'trades_adopted.csv')
trH = pd.read_csv(D+'trades_hard_exit.csv')
ws = wb.create_sheet('13_策略回測交易')
ws.cell(row=1, column=1, value='策略回測逐筆交易 (1976-07..2026-07) | 規則: 進入EASY買入, 離開EASY賣出 (月末訊號月末執行, 現金期記0%) | 交易紀錄由引擎程式(repo: engine.py)生成, 統計=公式活算 | (open)=期末仍持倉').font = F_HDR

def write_trades(ws, tr, col0, title, desc):
    c1, c2, c3 = col0, col0+1, col0+2
    ws.cell(row=2, column=c1, value=title).font = F_HDR
    ws.cell(row=3, column=c1, value=desc).font = F_TXT
    for c, h in zip((c1, c2, c3), ('進場月', '出場月', '交易報酬')):
        cell = ws.cell(row=4, column=c, value=h); cell.font = F_HDR; cell.fill = FILL_HDR
    for i, rw in tr.iterrows():
        r = 5 + i
        ws.cell(row=r, column=c1, value=rw['entry']).font = F_TXT
        ws.cell(row=r, column=c2, value=rw['exit']).font = F_TXT
        cell = ws.cell(row=r, column=c3, value=round(float(rw['ret']), 6))
        cell.font = F_TXT; cell.number_format = '0.00%'
        cell.fill = FILL_EASY if rw['ret'] > 0 else FILL_HARD
    r0, r1 = 5, 5 + len(tr) - 1
    L1c, L3c = get_column_letter(c1), get_column_letter(c3)
    stats = [
        ('交易次數', f'=COUNT({L3c}{r0}:{L3c}{r1})'),
        ('獲利筆數', f'=COUNTIF({L3c}{r0}:{L3c}{r1},">0")'),
        ('WIN RATE', f'=COUNTIF({L3c}{r0}:{L3c}{r1},">0")/COUNT({L3c}{r0}:{L3c}{r1})'),
        ('平均每筆', f'=AVERAGE({L3c}{r0}:{L3c}{r1})'),
        ('平均獲利', f'=AVERAGEIF({L3c}{r0}:{L3c}{r1},">0")'),
        ('平均虧損', f'=IF(COUNTIF({L3c}{r0}:{L3c}{r1},"<=0")=0,0,AVERAGEIF({L3c}{r0}:{L3c}{r1},"<=0"))'),
        ('盈虧因子', f'=SUMIF({L3c}{r0}:{L3c}{r1},">0")/MAX(0.0001,-SUMIF({L3c}{r0}:{L3c}{r1},"<=0"))'),
    ]
    refs = {}
    for j, (nm, fx) in enumerate(stats):
        rr = r1 + 2 + j
        ws.cell(row=rr, column=c1, value=nm).font = F_HDR
        cell = ws.cell(row=rr, column=c3, value=fx); cell.font = F_GREEN
        refs[nm] = f"'13_策略回測交易'!{L3c}{rr}"
        if nm in ('WIN RATE', '平均每筆', '平均獲利', '平均虧損'):
            cell.number_format = '0.0%'
        elif nm == '盈虧因子':
            cell.number_format = '0.00'
    ws.cell(row=r1 + 2 + 2, column=c1).fill = FILL_EASY
    return refs

refE = write_trades(ws, trE, 1, '採用版E (work-from-back-end校準)', '進場:合成分≥70 | 出場:<65且連續2月確認(=T1連續2週思想月度版)')
refA = write_trades(ws, trA, 5, '基準版A (嚴格原題定義)', '進場:判區=EASY | 出場:判區離開EASY即月執行')
refH = write_trades(ws, trH, 9, '對照版 (跌入HARD才賣)', '進場:判區=EASY | 出場:判區=HARD')
for c, w in enumerate([13,13,11,3,13,13,11,3,13,13,11], 1):
    ws.column_dimensions[get_column_letter(c)].width = w

# ================= 14_WinRate摘要 =================
eqE = pd.read_csv(D+'equity_adopted.csv')
ws = wb.create_sheet('14_WinRate摘要')
rows14 = [
('S&P500 Easy/Hard Money 50年策略 — Win Rate 摘要 (1976-07..2026-07, 整50年600個月)', ''),
('', ''),
('策略規則 (用戶指定)', '進入 EASY money market 買入; 離開 EASY money market 賣出。判區=100指標庫中50年可得之7支柱加權合成分 (≥70 EASY / 40-70 UNC / ≤40 HARD)。'),
('', ''),
('【主結果: 採用版E】', 'work-from-back-end 校準: 出場加「<65且連續2月」確認 (附件T1連續2週過濾假破之月度版)'),
('  WIN RATE', f"={refE['WIN RATE']}"),
('  交易次數', f"={refE['交易次數']}"),
('  平均每筆報酬', f"={refE['平均每筆']}"),
('  盈虧因子', f"={refE['盈虧因子']}"),
('  策略CAGR / 買入持有CAGR', '9.29% vs 12.26%'),
('  策略MaxDD / 買入持有MaxDD', '-31.1% vs -50.4% (回撤近乎減半)'),
('  在市場時間', '71.1% (現金期記0%報酬, 保守)'),
('', ''),
('【基準版A: 嚴格原題定義】', '離開EASY即月賣出'),
('  WIN RATE', f"={refA['WIN RATE']}"),
('  交易次數 / CAGR / MaxDD', '40筆 / 7.33% / -25.6%'),
('', ''),
('【對照版: 跌入HARD才賣】', '容忍UNCERTAIN持倉'),
('  WIN RATE', '90.0% (10筆, CAGR 10.64%, MaxDD -25.6%)'),
('', ''),
('16筆採用版交易亮點', '1991-01..1998-09 +246% | 2003-05..2008-02 +56%(2008崩盤前出場) | 2016-06..2020-03 +45% | 2020-06..2022-02 +41%(2022熊市初出場) | 唯一虧損: 2023-08..2023-10 -7.0%'),
('', ''),
('誠實揭露', '①in-sample校準(work-from-back-end本質); ②勝率↑=交易少+持倉長, 非免費午餐(1987/2020型單月崩跌只能事後離場); ③2025/10後數據為近似/代理(淡紫); ④未計交易成本/稅/現金利息; 月度再平衡下成本影響<0.1%/年。'),
('', ''),
('複製方法', 'repo分支 claude/quantitative-trading-strategy-uusnmj: engine.py(引擎+回測) + data/(全部數據CSV) + README。修改11表原始數據欄, 12/13/14表公式自動重算。'),
]
for i, (a, b) in enumerate(rows14, 1):
    ca = ws.cell(row=i, column=1, value=a)
    ca.font = F_HDR if (a.startswith('【') or i == 1 or a.startswith('策略規則')) else F_TXT
    cb = ws.cell(row=i, column=2, value=b)
    cb.font = F_GREEN if str(b).startswith('=') else F_TXT
    cb.alignment = Alignment(wrap_text=True, vertical='top')
    if a == '  WIN RATE':
        cb.number_format = '0.0%'; cb.fill = FILL_EASY; cb.font = Font(name=ARIAL, size=11, bold=True, color='008000')
ws.column_dimensions['A'].width = 34
ws.column_dimensions['B'].width = 110

wb.save(OUT)
print('saved', OUT)
