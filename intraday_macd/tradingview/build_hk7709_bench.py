# -*- coding: utf-8 -*-
"""build_hk7709_bench.py — 由 TW-1M-MULTI-(09月19日_23.35) 產出港股 7709 版「多策略同場比較」:
   HK7709-1m-benchmark_(MM月DD日; HH:MM).pine — 17 個策略 (13 個公認常見日內策略 + 2 個高勝率型 + 本專案四模式 2 個變體)
   在同一窗口 / 同一成本 / 同一港股時段下各跑一次, 主圖右上排名表比較 勝率 / 總報酬 / 最大回撤 / 獲利因子 / 捕獲率。
用法: STAMP="09月25日; 16:00" python3 build_hk7709_bench.py
"""
import io, os, re
from flatten_pine import verify
import make_paste_page
from build_hist_cross_rsi import END_TAG

STAMP = os.environ['STAMP']
SRC = 'TW-1M-MULTI-(09月19日_23.35).pine'
name = f'HK7709-1m-benchmark_({STAMP})'


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, n, old[:90])
    return s.replace(old, new)


lines = io.open(SRC, encoding='utf-8').read().rstrip('\n').split('\n')
v = next(i for i, l in enumerate(lines) if l.startswith('//@version'))
s = '\n'.join(l for l in lines[v:] if not l.startswith('// ═══ END OF FILE'))
s = s.replace('TW-1M-MULTI-(09月19日_23:35)', name)
assert 'TW-1M-MULTI' not in s
s = rep(s, 'commission_value = 0.03,', 'commission_value = 0.05,')
# ① 期間
s = rep(s, 'timestamp("2025-08-19T00:00:00")', 'timestamp("22 Aug 2026 00:00 +0800")')
s = rep(s, 'timestamp("2026-09-19T00:00:00")', 'timestamp("25 Sep 2026 23:59 +0800")')
s = rep(s, 'tickerHint = input.string("SOXL",', 'tickerHint = input.string("7709",')
# ② 港股時段 + 韓股時段 + 半日市 + 整手
s = rep(s, 'mktPre   = input.string("美股", "市場預設", options = ["美股", "港股", "自訂"]', 'mktPre   = input.string("港股", "市場預設 (本版 港股 7709)", options = ["港股", "美股", "自訂"]')
s = rep(s, 'sessCust = input.session("0930-1600", "自訂: 交易時段"', 'sessCust = input.session("0930-1200,1300-1600", "自訂: 交易時段"')
s = rep(s, 'tzCust   = input.string("America/New_York", "自訂: 時區"', 'tzCust   = input.string("Asia/Hong_Kong", "自訂: 時區"')
s = rep(s, 'noEntry  = input.session("1545-1600", "收市前不開新倉時段", group = gS, display = display.none)\n',
           'noEntry  = input.session("1150-1200,1545-1600", "不開新倉時段 (港股: 午休前 11:50 起 + 收市前 15:45 起)", group = gS, display = display.none)\n'
           'korOnly  = input.bool(true, "所有策略共用: 只在韓股交易時段開新倉 (7709 追蹤 SK Hynix; 韓股 09:00-15:30 KST = 08:00-14:30 HKT)", group = gS, tooltip = "與 HK7709-1m-dashboard ⑤ 同一條規則, 令比較公平: 14:30 後只剩莊家報價, 全部策略都不開新倉 (已有倉照各自規則出場)。關掉 = 全部策略 14:30 後照常開倉。", display = display.none)\n'
           'korSess  = input.session("1430-1600", "韓股收市後不開新倉的時段 (HKT)", group = gS, display = display.none)\n'
           'lotSize  = input.int(100, "真單: 每手股數 (港股整手下單; 0 或 1 = 不取整)", minval = 0, group = gS, display = display.none)\n')
s = rep(s, 'commPct  = input.float(0.03, "單邊手續費 %', 'commPct  = input.float(0.05, "單邊手續費 % (港股 7709: 佣金 + 徵費, 槓桿反向產品免印花稅)')
s = rep(s, 'eodBar   = isIntra and not na(time(timeframe.period, eodSess, tzStr))\n',
           'halfDay  = month(time, tzStr) == 12 and (dayofmonth(time, tzStr) == 24 or dayofmonth(time, tzStr) == 31)   // 港股半日市 12:00 收市\n'
           'eodBar   = isIntra and (not na(time(timeframe.period, eodSess, tzStr)) or (halfDay and not na(time(timeframe.period, "1158-1200", tzStr))))\n'
           'korBlock = korOnly and isIntra and not na(time(timeframe.period, korSess, tzStr))\n')
s = rep(s, 'entryOK  = inWindow and inSess and not blockNew and not eodBar\n', 'entryOK  = inWindow and inSess and not blockNew and not korBlock and not eodBar\n')
# ③ 17 個策略
NAMES = ['S01 MACD柱動能減弱', 'S02 MACD DIF/DEA交叉', 'S03 EMA 9/21 交叉', 'S04 Supertrend 轉向', 'S05 RSI 超賣回歸', 'S06 布林下軌回歸', 'S07 VWAP 偏離回歸', 'S08 開盤區間突破', 'S09 動能突破+量能', 'S10 三EMA+ST共振', 'S11 ATR標準化MACD', 'S12 MACD柱背離', 'S13 隨機進場(安慰劑)',
         'S14 四模式 (本專案, ④ 預設)', 'S15 四模式 寬鬆 (N1 k0.5 窗20)', 'S16 RSI2 Connors 日內', 'S17 EMA200趨勢+VWAP回踩']
old_names = '"S01 MACD柱動能減弱", "S02 MACD DIF/DEA交叉", "S03 EMA 9/21 交叉", "S04 Supertrend 轉向", "S05 RSI 超賣回歸", "S06 布林下軌回歸", "S07 VWAP 偏離回歸", "S08 開盤區間突破", "S09 動能突破+量能", "S10 三EMA+ST共振", "S11 ATR標準化MACD", "S12 MACD柱背離", "S13 隨機進場(安慰劑)"'
new_names = ', '.join('"%s"' % n for n in NAMES)
s = rep(s, 'NS     = 13\n', 'NS     = 17\n')
s = rep(s, old_names, new_names, 2)
s = rep(s, 'liveName = input.string("S01 MACD柱動能減弱", "用哪一個策略下真單', 'liveName = input.string("S14 四模式 (本專案, ④ 預設)", "用哪一個策略下真單')
# ④ 新增參數群組 (放在 gR 報表群組之前)
s = rep(s, 'gR = "⑤ 報表"\n', '''gP4 = "④d S14 / S15 · 本專案四模式 (與 HK7709-1m-dashboard ④/④c/④d/④e 同一套定義; S14 用這裡的值, S15 = 固定寬鬆版 N1 k0.5 窗20)"
fadeBuy4 = input.int(2, "S14 模式1 買: 淺紅 N 根", minval = 1, maxval = 10, group = gP4, display = display.none)
kBuy4    = input.float(1.5, "S14 模式1 買: 下界倍數 k (基準 = 最近 250 根 |柱| 第 75 百分位)", minval = 0, step = 0.1, group = gP4, display = display.none)
mbBuy4   = input.int(4, "S14/S15 模式1 買: 負柱段最少根數", minval = 1, group = gP4, display = display.none)
fadeSell4 = input.int(2, "S14/S15 模式1 賣: 淺綠 N 根", minval = 1, maxval = 10, group = gP4, display = display.none)
kSell4   = input.float(1.0, "S14/S15 模式1 賣: 上界倍數 k", minval = 0, step = 0.1, group = gP4, display = display.none)
mbSell4  = input.int(3, "S14/S15 模式1 賣: 正柱段最少根數", minval = 1, group = gP4, display = display.none)
pctLen4  = input.int(250, "模式1 上下界: 取樣根數", minval = 30, group = gP4, display = display.none)
depthPct4 = input.float(75, "模式1 上下界: 百分位", minval = 1, maxval = 99, step = 5, group = gP4, display = display.none)
win4     = input.int(5, "S14 M1/M3 匹配窗口 (根)", minval = 1, maxval = 60, group = gP4, display = display.none)
winS4    = input.int(5, "S14/S15 M1 賣訊有效根數", minval = 1, maxval = 60, group = gP4, display = display.none)
rsiPctLen4 = input.int(120, "模式2 RSI14/28: 下上界取樣根數 (第 10 / 90 百分位)", minval = 20, group = gP4, display = display.none)
m3Fast4  = input.int(9, "模式3 敏感 MACD 快線 (9/26/9 金叉)", minval = 1, group = gP4, display = display.none)
m4Len4   = input.int(9, "模式4 EMA 長度 (斜率 > 0 才可買)", minval = 1, group = gP4, display = display.none)
gP5 = "④e S16 / S17 · 高勝率型"
rsi2Len  = input.int(2, "S16: RSI 長度 (Connors RSI2)", minval = 2, group = gP5, display = display.none)
rsi2Buy  = input.float(10, "S16: 買入 — RSI2 低於", minval = 1, maxval = 50, group = gP5, display = display.none)
emaLong  = input.int(200, "S16/S17: 長期 EMA (趨勢濾網)", minval = 20, group = gP5, display = display.none)
rsi2ExMA = input.int(5, "S16: 出場 — 收盤升穿 N 根 SMA", minval = 2, group = gP5, display = display.none)

gR = "⑤ 報表"
''')
# ⑥ 四模式 + 高勝率型指標 (放在偽亂數之前)
s = rep(s, '// 偽亂數 (同一根 K 永遠得到同一個值 → 結果可重現)\n', '''// ── 本專案四模式 (S14 / S15): 定義與 HK7709-1m-dashboard 完全一致 ──
// 模式 1: 段統計用「上一根為止」的快照 (var 變數的 [1] = 本根更新前的值), 上下界基準 = 最近 N 根 |柱| 的第 P 百分位
qBase    = ta.percentile_linear_interpolation(hPct, pctLen4, depthPct4)
qSegSign = segSign[1]
qSegBars = segBars[1]
qSegDep  = segDepth[1]
qOkB     = kBuy4  <= 0 or (qSegBars >= mbBuy4  and qSegDep >= qBase * kBuy4)
qOkBL    = qSegBars >= mbBuy4 and qSegDep >= qBase * 0.5
qOkS     = kSell4 <= 0 or (qSegBars >= mbSell4 and qSegDep >= qBase * kSell4)
q1Buy    = nFadeDn == fadeBuy4 and qSegSign == -1 and qOkB
q1BuyL   = nFadeDn == 1 and qSegSign == -1 and qOkBL
q1Sell   = nFadeUp == fadeSell4 and qSegSign == 1 and qOkS
var int q1Age  = 999
var int q1AgeL = 999
var int qs1Age = 999
q1Age  := q1Buy  ? 0 : math.min(q1Age  + 1, 999)
q1AgeL := q1BuyL ? 0 : math.min(q1AgeL + 1, 999)
qs1Age := q1Sell ? 0 : math.min(qs1Age + 1, 999)
// 模式 2: RSI 14/28 可買區 / 可賣區 (狀態), 動態下上界 = 最近 N 根 RSI14 的第 10 / 90 百分位, 每日清空
rsiF     = ta.rsi(close, 14)
rsiS     = ta.rsi(close, 28)
rsiPLo   = ta.percentile_linear_interpolation(rsiF, rsiPctLen4, 10)
rsiPHi   = ta.percentile_linear_interpolation(rsiF, rsiPctLen4, 90)
rsiLoB   = nz(rsiPLo, 30.0)
rsiHiB   = nz(rsiPHi, 70.0)
turnUpF  = rsiF > rsiF[1] and rsiF[1] <= rsiF[2]
turnDnF  = rsiF < rsiF[1] and rsiF[1] >= rsiF[2]
sinceLoF = ta.barssince(rsiF <= rsiLoB)
sinceHiF = ta.barssince(rsiF >= rsiHiB)
reachLoF = nz(sinceLoF[1], 99999) < 1
reachHiF = nz(sinceHiF[1], 99999) < 1
xFSdn    = ta.crossunder(rsiF, rsiS)
xFSup    = ta.crossover(rsiF, rsiS)
m2BuyStart  = turnUpF and reachLoF
m2SellStart = turnDnF and reachHiF
var int   m2State  = 0
var float m2Trough = na
var float m2Peak   = na
qNewDay  = dayofmonth != dayofmonth[1]
if qNewDay
    m2State := 0
m2Prev   = m2State
if m2BuyStart
    m2State  := 1
    m2Trough := rsiF[1]
else if m2SellStart
    m2State := -1
    m2Peak  := rsiF[1]
else if m2State == 1 and (xFSdn or rsiF < m2Trough)
    m2State := 0
else if m2State == -1 and (xFSup or rsiF > m2Peak)
    m2State := 0
m2InBuy  = m2State == 1
m2InSell = m2State == -1
m2BuyEnd = m2Prev == 1 and not m2InBuy
// 模式 3: 敏感 MACD 9/26/9 金叉 (只參與買入)
[dif3, dea3, hist3] = ta.macd(close, m3Fast4, 26, 9)
m3Buy    = ta.crossover(dif3, dea3)
var int q3Age = 999
q3Age   := m3Buy ? 0 : math.min(q3Age + 1, 999)
// 模式 4: EMA9 斜率 > 0 才可買 (狀態; 剛轉向上那一根也算「剛出現」)
m4Ema    = ta.ema(close, m4Len4)
m4Up     = m4Ema > m4Ema[1]
m4Start  = m4Up and not m4Up[1]
// 高勝率型 (S16 / S17)
rsi2     = ta.rsi(close, rsi2Len)
emaL     = ta.ema(close, emaLong)
smaX     = ta.sma(close, rsi2ExMA)
vwXdn    = ta.crossunder(close, vwapV)

// 偽亂數 (同一根 K 永遠得到同一個值 → 結果可重現)
''')
# ⑦ 訊號
s = rep(s, 's13L = rndU < pRand\ns13X = false\n', '''s13L = rndU < pRand
s13X = false
// S14 四模式 (本專案): M1 與 M3 買訊都在窗口內 + M2 可買區 + M4 向上, 且本根至少一個剛出現; 賣 = M1 賣訊在可賣區 (有效 winS4 根), 或 可買區結束
s14L = q1Age < win4 and q3Age < win4 and m2InBuy and m4Up and (q1Buy or m3Buy or m2BuyStart or m4Start)
s14X = (qs1Age < winS4 and m2InSell and (q1Sell or m2SellStart)) or m2BuyEnd
// S15 四模式 寬鬆版: 淺紅 1 根 + k 0.5 + 窗口 20 (其餘同 S14)
s15L = q1AgeL < 20 and q3Age < 20 and m2InBuy and m4Up and (q1BuyL or m3Buy or m2BuyStart or m4Start)
s15X = s14X
// S16 Connors RSI2 日內版: 長期 EMA 之上 + RSI2 超賣 → 買; 收盤升穿短 SMA → 賣
s16L = close > emaL and rsi2 < rsi2Buy
s16X = close > smaX
// S17 EMA200 趨勢 + VWAP 回踩: 長期 EMA 之上, 本根低點碰到 VWAP 而收盤仍在 VWAP 之上且收高 → 買; 跌破 VWAP 或跌破長期 EMA → 賣
s17L = close > emaL and low <= vwapV and close > vwapV and close > close[1] and inSess
s17X = vwXdn or close < emaL
''')
s = rep(s, 'sigL = array.from(s01L, s02L, s03L, s04L, s05L, s06L, s07L, s08L, s09L, s10L, s11L, s12L, s13L)\nsigX = array.from(s01X, s02X, s03X, s04X, s05X, s06X, s07X, s08X, s09X, s10X, s11X, s12X, s13X)\n',
           'sigL = array.from(s01L, s02L, s03L, s04L, s05L, s06L, s07L, s08L, s09L, s10L, s11L, s12L, s13L, s14L, s15L, s16L, s17L)\nsigX = array.from(s01X, s02X, s03X, s04X, s05X, s06X, s07X, s08X, s09X, s10X, s11X, s12X, s13X, s14X, s15X, s16X, s17X)\n')
# ⑧ 引擎: 隔夜備援
s = rep(s, '    else if pn == 1 and (xs or eodBar or not inWindow)\n', '    else if pn == 1 and (xs or eodBar or newSess or not inWindow)   // newSess = 半日市等原因留倉到翌日, 第一根即平 (隔夜備援)\n')
# ⑨ 真單: 整手 + 隔夜備援
s = rep(s, 'if liveIdx >= 0 and entryOK and liveL and strategy.position_size == 0\n    strategy.entry("多", strategy.long, comment = liveName)\n',
           'qtyRaw = strategy.equity / close\nqtyL   = lotSize > 1 ? math.floor(qtyRaw / lotSize) * lotSize : qtyRaw   // 港股整手\nif liveIdx >= 0 and entryOK and liveL and strategy.position_size == 0 and qtyL > 0\n    strategy.entry("多", strategy.long, qty = qtyL, comment = liveName)\n')
s = rep(s, 'if liveIdx >= 0 and strategy.position_size > 0 and (liveX or eodBar)\n', 'if liveIdx >= 0 and strategy.position_size > 0 and (liveX or eodBar or newSess)\n')
# ⑩ 表
s = rep(s, 'var table rpt = table.new(posR, 11, 22,', 'var table rpt = table.new(posR, 11, 30,')
s = rep(s, '"多策略同場回測 · " + syminfo.ticker', '"港股 7709 多策略同場回測 (13 個公認策略 + 2 個高勝率型 + 本專案四模式 2 個變體) · " + syminfo.ticker')
s = rep(s, '" · 下真單 " + liveName', '" · 韓股時段限制 " + (korOnly ? "開" : "關") + " · 下真單 " + liveName')
s = rep(s, '"捕獲率 = 該策略總報酬 ÷ 期內最大昇幅; S13 隨機進場是安慰劑基準 — 排在它下面的策略等於沒有優勢"', '"捕獲率 = 該策略總報酬 ÷ 期內最大昇幅; S13 隨機進場是安慰劑基準 — 排在它下面的策略等於沒有優勢; 交易 < 30 筆的勝率沒有統計意義"')
s = rep(s, '③ 下真單的策略 (其餘 12 個同時做虛擬回測)', '③ 下真單的策略 (其餘 16 個同時做虛擬回測)')
s = rep(s, '⑦ 13 個策略的進 / 出場訊號', '⑦ 17 個策略的進 / 出場訊號')
s = rep(s, '⑧ 虛擬回測引擎 (13 個策略同時跑', '⑧ 虛擬回測引擎 (17 個策略同時跑')
assert 'SOXL' not in s and '-0400' not in s

HEADER = f'''// ═══════════════════════════════════════════════════════════════════════════════
//  {name}  ·  港股 7709 · 多策略同場回測比較 · 1 分鐘 · 一個月 · TradingView Pine Script v6
//  四處必須一致: strategy() 標題 = shorttitle = 檔名 = TradingView 腳本名稱 (Save 時輸入; 結尾的 ")" 不可漏)
//  本檔共 {{n}} 行; 最後一行是 "// ═══ END OF FILE ═══" → 貼上後若看不到那一行 = 內容被截斷 (檔案預覽視窗常只載入前 8KB)
//  正確貼法: 用「貼上工具」網頁按【複製全部程式碼】, 或下載 .pine 後用純文字編輯器開啟 → Ctrl+A → Ctrl+C
//
//  【這支腳本做甚麼】回答「我這個 algo 的勝率 / 總回報, 跟其它公認的高勝率、高回報日內策略比, 在這一個月的 7709 上到底如何」
//   把 17 個只做多的日內策略放在【同一個回測窗口、同一套手續費滑點、同一組港股時段 / 韓股時段限制 / 收市強平規則】下各跑一次,
//   主圖右上印出每個策略的回測 report (交易次數 / 勝率 / 總報酬 / 最大回撤 / 獲利因子 / 平均每筆 / 最佳最差 / 平均持倉 / 捕獲率), 按總報酬排名,
//   並附「買入持有」與「期內最大昇幅」兩條基準線。③ 選中的那一個策略會下真單 (預設 S14 本專案四模式), 其餘 16 個同時做虛擬回測。
//
//  【17 個策略】S01 MACD柱動能減弱 · S02 MACD DIF/DEA交叉 · S03 EMA 9/21 交叉 · S04 Supertrend轉向 · S05 RSI超賣回歸 · S06 布林下軌回歸 ·
//   S07 VWAP偏離回歸 · S08 開盤區間突破 · S09 動能突破+量能 · S10 三EMA+Supertrend共振 · S11 ATR標準化MACD · S12 MACD柱背離 · S13 隨機進場(安慰劑基準) ·
//   S14 本專案四模式 (④d 的值 = HK7709-1m-dashboard ④/④c/④d/④e 預設: 模式 1 柱到界 N2 k1.5 + 模式 2 RSI14/28 可買區 + 模式 3 9/26/9 金叉 + 模式 4 EMA9 向上, 窗口 5) ·
//   S15 四模式寬鬆版 (淺紅 1 根, k 0.5, 窗口 20; 其餘同 S14) · S16 Connors RSI2 日內版 (EMA200 之上 RSI2 < 10 買, 收盤升穿 SMA5 賣; 公認高勝率) ·
//   S17 EMA200 趨勢 + VWAP 回踩 (低點碰 VWAP 收回其上買, 跌破 VWAP 或 EMA200 賣)
//   ※ S13 是對照組: 任何排在隨機進場下面的策略, 在這段資料上等於沒有優勢。※ S14 不含 dashboard ⑨b 的走動式自動調參 (那是逐日換參數, 這裡是固定參數的公平比較);
//     dashboard 真單 (自動調參) 的數字看它自己的 Strategy Tester, 再與本表對照。
//
//  【共用規則 — 保證比較公平】只做多 · 每次全部本金 (真單整手) · 不加碼 · 訊號收盤確認下一根開盤成交 · 手續費 0.05%/邊 + 滑點 2 tick ·
//   港股 09:30-12:00, 13:00-16:00 HKT · 午休前 11:50 起 / 14:30 韓股收市後 (② 可關) / 收市前 15:45 起不開新倉 · 15:58 強平 (12/24、12/31 半日市 11:58) · 留倉到翌日第一根即平 ·
//   ② 可一鍵開「所有策略共用固定止損」 · margin_long = 0
//  【回測期間】① 預設 方式 B 最近 30 天 (一個月); 港股 1 分 K 一個月約 7,000 根, TradingView 依方案只載入 5,000-20,000 根 → 實際起點見報表
//  【怎麼用】圖表切【HKEX:7709 · 1 分鐘】→ 貼上 → 檢查最後一行 → Save (同名) → Add to chart → 看主圖右上比較表 (橙底 = 下真單的那一個)
//  【怎麼讀】捕獲率 = 該策略總報酬 ÷ 期內最大昇幅; 獲利因子 < 1 = 賠錢; 交易次數 < 30 的勝率沒有統計意義, 只能當參考
//  版本戳 HK7709-1m-benchmark_(MM月DD日; HH:MM), 括號內 = 建置時間 HKT; 檔名以 . 代替 : ; 本檔零延續行
// ═══════════════════════════════════════════════════════════════════════════════
'''
n = HEADER.count('\n') + s.count('\n') + 1 + 1
out = HEADER.replace('{n}', str(n)) + s + '\n' + END_TAG.format(name=name, n=n) + '\n'
assert out.count('\n') == n, (out.count('\n'), n)
fn = name.replace(':', '.') + '.pine'
io.open(fn, 'w', encoding='utf-8', newline='\n').write(out)
print('wrote', fn, n, 'lines; verify:', verify(out) or 'PASS')
make_paste_page.make(fn, 'paste_HK7709-1m-benchmark.html')
h = io.open('paste_HK7709-1m-benchmark.html', encoding='utf-8').read()
h = h.replace('1 分鐘日內策略 (市場預設 美股, Inputs 可切港股)', '港股 7709 · 17 個策略同場比較 (勝率 / 總回報)')
h = h.replace('開要測的標的 (例如 AMEX:SOXL)。', '開 HKEX:7709。')
io.open('paste_HK7709-1m-benchmark.html', 'w', encoding='utf-8', newline='\n').write(h)
