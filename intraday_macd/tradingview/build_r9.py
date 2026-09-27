# -*- coding: utf-8 -*-
"""build_r9.py — R9: 由 R8 三支重組成兩支:
   R9_TV-1M-dashboard_(mode 2,4)_(MM月DD日; HH:MM)   主策略, 畫在主圖 (overlay): 模式 1 / 3 的 MACD 程式碼全部刪除, 只剩模式 2 + 4 的買賣; 表格 / 成交標記 / 持倉框都在主圖
   R9_TV-1M-RSI-winrate_(mode 2,4)_(MM月DD日; HH:MM)  一個副圖: 上半 RSI14 可買區 / 可賣區 (模式 2), 底部一條綠 / 紅色帶 = 模式 4 EMA9 斜率 (綠可買可持倉 / 紅立即平倉)
用法: STAMP="09月27日; 10:00" python3 build_r9.py   (需要 R8 三支已存在)
"""
import glob, io, os, re
from flatten_pine import verify
import make_paste_page
from build_hist_cross_rsi import END_TAG

STAMP = os.environ['STAMP']
SRC_MAIN = glob.glob('TV-1M-dashboard_(mode 1-4)_R8_mode2_4only_*.pine')[0]
SRC_RSI  = glob.glob('TV-1M-RSI-mode2_R8_mode2_4only_*.pine')[0]
SRC_M4   = glob.glob('TV-1M-winrate-mode4_R8_mode2_4only_*.pine')[0]
NAME_MAIN = f'R9_TV-1M-dashboard_(mode 2,4)_({STAMP})'
NAME_PANE = f'R9_TV-1M-RSI-winrate_(mode 2,4)_({STAMP})'
BAR = '// ' + '═' * 79 + '\n'


def lines_of(path):
    L = io.open(path, encoding='utf-8').read().rstrip('\n').split('\n')
    v = next(i for i, l in enumerate(L) if l.startswith('//@version'))
    return [l for l in L[v:] if not l.startswith('// ═══ END OF FILE')]


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, n, old[:90])
    return s.replace(old, new)


def find1(L, prefix):
    idx = [i for i, l in enumerate(L) if l.startswith(prefix)]
    assert len(idx) == 1, (prefix, idx)
    return idx[0]


def block(L, start_prefix, end_prefix):
    """從 start_prefix 那一行 (含) 到 end_prefix 那一行 (不含)"""
    a = find1(L, start_prefix)
    b = find1(L, end_prefix)
    assert b > a
    return L[a:b]


# ═════════════════════════════ 主策略 ═════════════════════════════
L = lines_of(SRC_MAIN)
old_name = re.search(r'^strategy\("([^"]+)"', '\n'.join(L), re.M).group(1)
out = []
strat = L[find1(L, 'strategy(')]
strat = strat.replace(old_name, NAME_MAIN).replace('overlay=false', 'overlay = true')
out += ['//@version=6', strat, '']
out += block(L, '// ─────────────────────────── ① 回測期間', '// ─────────────────────────── ③ MACD')          # ① + ②
out += ['newDay = dayofmonth != dayofmonth[1]   // 新交易日第一根 (④c 每日清空 / 掃描用)', '']
m2 = block(L, '// ─────────────────────────── ④c 模式 2', '// ─────────────────────────── ④d 模式 3')
m2 = [l for l in m2 if not re.match(r'^(matchWin |matchWinS |var int   liveWin|useM1 |useM3 )', l)]
m2 = [l.replace('gRF       = "④f R8 · 只用模式 2 + 4 決定買賣 (模式 1 / 3 已刪除, 不參與; 只做多)"', 'gRF       = "④f R9 · 賣出規則 (只做多; 模式 1 / 3 已完全刪除)"') for l in m2]
out += m2
ds = block(L, '// ─────────────────────────── ⑤ 顯示', '// ─────────────────────────── ⑥ 同號柱段')
ds = [l.replace('"橙框: 持倉期間框住 MACD 柱"', '"橙框: 持倉期間框住價格 K 線 (主圖)"') for l in ds if not l.startswith('showClusterBox')]
out += ds
out += block(L, '// ─────────────────────────── ⑦ 盤中時段', '// ─────────────────────────── ④e 模式 4')
out += ['// ── R9: 買入核心只剩模式 2 (模式 1 / 3 程式碼已刪除) ──',
        'buyCore = m2InBuy and m2BuyOK                          // 模式 2 處於可買區',
        'buyEvt  = m2BuyStart                                   // 本根剛進可買區 (模式 4 剛轉綠也算, 在 ④e 加上)',
        'sellSigM1 = false                                      // 舊規則已刪除', '']
m4 = block(L, '// ─────────────────────────── ④e 模式 4', '// ─────────────────────────── ⑧ 風控')
out += m4
out += block(L, '// ─────────────────────────── ⑧ 風控', '// ─────────────────────────── ⑮ 參數掃描')     # ⑧ + ⑨
sw = block(L, '// ─────────────────────────── ⑮ 參數掃描', '// ─────────────────────────── ⑩ 成交偵測')
sw = ['m13OK  = true                                                 // R9: 模式 1 / 3 已刪除' if l.startswith('m13OK ') else
      'm13Evt = false' if l.startswith('m13Evt ') else l for l in sw]
out += sw
fd = block(L, '// ─────────────────────────── ⑩ 成交偵測', '// ─────────────────────────── ⑪ 盤中統計')
skip_exact = {'    line.new(bar_index, hist, bar_index, 0.0, extend = extend.both, color = color.new(color.aqua, lineTransp), width = 1, style = line.style_dotted)',
              '    line.new(bar_index, hist, bar_index, 0.0, extend = extend.both, color = color.new(color.red, lineTransp), width = 1, style = line.style_dotted)',
              '    hHi  := hist', '    hLo  := hist', '    hBox  := na'}
fd2 = []
i = 0
while i < len(fd):
    l = fd[i]
    if l in skip_exact or l.startswith('var box   hBox  =') or l.startswith('var float hHi') or l.startswith('var float hLo') or l.startswith('    hBox := box.new('):
        i += 1
        continue
    if l.startswith('if not na(hBox) and'):
        i += 1
        while i < len(fd) and fd[i].startswith('    '):
            i += 1
        continue
    fd2.append(l)
    i += 1
assert not any('hist' in l and not l.lstrip().startswith('//') for l in fd2), [l for l in fd2 if 'hist' in l]
out += fd2
out += block(L, '// ─────────────────────────── ⑪ 盤中統計', '// ─────────────────────────── ⑫ 繪圖')
# ⑫ 繪圖: 只留 回測期間底色 + 主圖成交三角
out += ['// ─────────────────────────── ⑫ 繪圖 (主圖): 回測期間底色 + 成交三角; 模式 2 / 4 的圖形見 R9_TV-1M-RSI-winrate 副圖 ───────────────────────────',
        'bgcolor(inWindow ? color.new(color.blue, 94) : na, title = "回測期間底色")']
out += [l for l in L if l.startswith('plotshape(showFillMarks and justFilled, "買入成交(主圖)"') or l.startswith('plotshape(showFillMarks and justClosed, "賣出成交(主圖)"')]
assert len(out) >= 2 and out[-2].startswith('plotshape(') and out[-1].startswith('plotshape(')
out += ['']
# ⑬ 報表
rp = block(L, '// ─────────────────────────── ⑬ 報表', '// 訊號漏斗計數')
rp = [l.replace('"副圖顯示「觸發參數」表 (調整用)"', '"主圖顯示「觸發參數」表 (調整用)"').replace('"觸發參數表位置 (副圖; 預設與主圖摘要同靠右對齊)"', '"觸發參數表位置 (主圖)"').replace('options = ["右下", "右上", "左下", "左上"], group = gRP, display = display.none)', 'options = ["右下", "右上", "左下", "左上"], group = gRP, display = display.none)') for l in rp]
rp = [l.replace('rptPos   = input.string("右上",', 'rptPos   = input.string("右上",').replace('prmPos   = input.string("右上",', 'prmPos   = input.string("左下",') for l in rp]
rp = ['var table prm = table.new(posP, 2, 7, border_width = 1, frame_width = 1, frame_color = color.gray, force_overlay = true)   // 觸發參數 → 主圖' if l.startswith('var table prm') else l for l in rp]
out += rp
out += ['// 訊號計數 (回測窗內 + 盤中)',
        'var int cM2B  = 0', 'var int cM2Raw = 0', 'var int cBoth = 0', 'var int cS2   = 0', 'var int cSBoth = 0', 'var int cM4Dn  = 0', 'var int cM4Bar = 0', 'var int cM2BarB = 0', 'var int cM2BarS = 0',
        'if inWindow and inSess',
        '    cM2B  += m2BuyStart ? 1 : 0', '    cM2Raw += m2BuyRaw ? 1 : 0', '    cM2BarB += m2InBuy ? 1 : 0', '    cM2BarS += m2InSell ? 1 : 0', '    cBoth += buySig ? 1 : 0',
        '    cS2   += m2SellStart ? 1 : 0', '    cSBoth += sellSig ? 1 : 0', '    cM4Dn  += m4DnStart ? 1 : 0', '    cM4Bar += m4OK ? 1 : 0', '']
# prm 表 (7 列): 取 R8 的 13 / 17 / 15 / 16 / 9 / 10 列內容重排
prm_src = block(L, 'if barstate.islast and showPrm', '// ── 參數掃描表 (主圖)')
def prm_row(n, col):
    pre = f'    table.cell(prm, {col}, {n}, '
    c = [l for l in prm_src if l.startswith(pre)]
    assert len(c) == 1, (n, col, len(c))
    return c[0]
r13a, r13b = prm_row(13, 0), prm_row(13, 1)
r17a, r17b = prm_row(17, 0), prm_row(17, 1)
r16a, r16b = prm_row(16, 0), prm_row(16, 1)
r9a, r9b = prm_row(9, 0), prm_row(9, 1)
r10a, r10b = prm_row(10, 0), prm_row(10, 1)
r16b = rep(r16b, '(sellRuleI == 3 ? " · M1 淺綠N根 " + str.tostring(cS1) : "") + ', '')
r16b = rep(r16b, ' + (sellRuleI == 3 ? " / S1 " + (s1Age >= 999 ? "-" : str.tostring(s1Age) + " 根前") : "")', '')
r16b = rep(r16b, '" → R2 賣點 "', '" → 賣點 "')
r16a = rep(r16a, '"賣 (R8): 紅柱立即平倉; 其餘 "', '"賣 (R9): 紅柱立即平倉; 其餘 "')
r10b = rep(r10b, '"R5 要更嚴 (少而準)', '"R9 要更嚴 (少而準)')
def renum(l, n):
    return re.sub(r'^    table\.cell\(prm, (\d), \d+, ', lambda m: f'    table.cell(prm, {m.group(1)}, {n}, ', l)
out += ['if barstate.islast and showPrm',
        '    table.clear(prm, 0, 0, 1, 6)',
        '    pBg = color.new(color.gray, 70)',
        '    table.cell(prm, 0, 0, "觸發參數 (Inputs ④c / ④e / ④f 調這裡; R9 只做多, 只有模式 2 + 4)", text_size = sizeV, text_color = color.white, bgcolor = color.new(color.blue, 40), text_halign = text.align_left)',
        '    table.cell(prm, 1, 0, "", text_size = sizeV, bgcolor = color.new(color.blue, 40))',
        '    table.merge_cells(prm, 0, 0, 1, 0)',
        renum(r13a, 1), renum(r13b, 1), renum(r17a, 2), renum(r17b, 2),
        '    table.cell(prm, 0, 3, "買 (R9, 只做多): M2 可買區 (RSI14 到下界後轉勢) + M4 綠柱, 本根至少一個剛出現", text_size = sizeV, bgcolor = pBg)',
        '    table.cell(prm, 1, 3, "M2 進區 " + str.tostring(cM2B) + " (轉勢向上 " + str.tostring(cM2Raw) + ") → 合格買點 " + str.tostring(cBoth) + "  (現況: M2 " + m2Zone + " / M4 " + (m4OK ? "綠柱 可買" : "紅柱 不可") + ")", text_size = sizeV, text_color = cBoth > 0 ? color.blue : color.gray)',
        renum(r16a, 4), renum(r16b, 4), renum(r9a, 5), renum(r9b, 5), renum(r10a, 6), renum(r10b, 6), '']
swt = block(L, '// ── 參數掃描表 (主圖)', 'if barstate.islast and showRpt')
swt = [l.replace(' + (useM1 or useM3 ? " · 加回 M" + (useM1 ? "1" : "") + (useM3 ? "3" : "") : "")', '') for l in swt]
out += swt
rpt = block(L, 'if barstate.islast and showRpt', '// ─────────────────────────── ⑭ 收盤')
rpt = [l.replace('"R5 M2 RSI14 "', '"R9 M2 RSI14 "').replace(' + (useM1 ? " · M1 k" + str.tostring(kBuy, "#.#") + "/N" + str.tostring(fadeBuy) + " 窗" + str.tostring(matchWin) : "") + (useM3 ? " · M3 窗" + str.tostring(matchWin) : "")', '') for l in rpt]
rpt = ['    table.cell(rpt, 6, 3, "只做多 · 紅柱立即平倉 " + (m4ExitOnEnd ? "開" : "關"), text_size = sizeV)' if l.startswith('    table.cell(rpt, 6, 3, thMode') else l for l in rpt]
rpt = [l.replace(' + (targetTPD > 0 ? " (目標 " + str.tostring(targetTPD, "#") + ")" : "")', '') for l in rpt]
rpt = [l.replace(' + (useM1 or useM3 ? " (④f 已加回模式 1/3: 亦可放寬 ④ 上下界 / ④c 匹配窗口)" : "")', '') for l in rpt]
out += rpt
out += ['// ─────────────────────────── ⑭ 收盤把報表也輸出到 Pine Logs (方便複製) ───────────────────────────',
        'if barstate.islastconfirmedhistory and showRpt',
        '    log.info("===== R9 只做多 · 模式 2+4 回測 (RSI14 區 + EMA9 綠柱; 紅柱立即平倉; 模式 1/3 已刪除) {0} · {1} → {2} =====", syminfo.ticker, str.format_time(btStart, "yyyy-MM-dd", tzStr), str.format_time(btEnd, "yyyy-MM-dd", tzStr))',
        '    log.info("交易次數 {0} · 勝 {1} 負 {2} · 總損益 {3} ({4}%) · 本金 {5} · M2 P{6}/{7} · M4 {8} 根 · 賣 {9} · 期內最大昇幅 {10}% · 買入持有 {11}%", strategy.closedtrades, strategy.wintrades, strategy.losstrades, str.tostring(strategy.netprofit, "#,###.##"), str.tostring(strategy.netprofit / strategy.initial_capital * 100.0, "#.##"), str.tostring(strategy.initial_capital, "#,###"), str.tostring(rsiPctLo, "#"), str.tostring(rsiPctHi, "#"), m4Look, sellCmt, str.tostring(maxRise, "#.##"), str.tostring(na(winOpen) ? 0.0 : (close / winOpen - 1.0) * 100.0, "#.##"))']
out += [l for l in L[find1(L, '    if strategy.closedtrades > 0'):] if True]   # 逐筆 log 到檔尾 (3 行)
body = '\n'.join(out)
for bad in ('useM1', 'useM3', 'matchWin', 'hist', 'dif3', 'm1Buy', 'm3Buy', 'kEff', 'thMode', 'targetTPD', 'kBuy', 'fadeBuy', 'segSign', 'autoDepth', 'cUp', 'cS1', 'cM3B', 'm1Age', 'm3Age', 'hBox '):
    hits = [l for l in body.split('\n') if re.search(r'(?<![A-Za-z0-9_])' + re.escape(bad) + r'(?![A-Za-z0-9_])', re.sub(r'//.*$', '', l)) and not l.startswith('//')]
    assert not hits, (bad, hits[:3])

HDR_MAIN = f'''//  {NAME_MAIN}  ·  R9 主策略 (畫在主圖): 只做多 · 只用 模式 2 (RSI14 可買區) + 模式 4 (EMA9 綠柱) 決定買賣 · 模式 1 / 3 的 MACD 程式碼已全部刪除 · 1 分鐘 · 一個月回測 · Pine v6
//  四處必須一致: strategy() 標題 = shorttitle = 檔名 = TradingView 腳本名稱 (Save 時輸入; 結尾的 ")" 不可漏)
//  本檔共 {{n}} 行; 最後一行是 "// ═══ END OF FILE ═══" → 貼上後若看不到那一行 = 內容被截斷 (檔案預覽視窗常只載入前 8KB); 請用「貼上工具」網頁按【複製全部程式碼】
//
//  【R9 規則】只做多 (沒有任何淡倉指令)
//   模式 2 (④c): RSI14; 下界 / 上界 = 最近 120 根 RSI14 的第 10 / 90 百分位 (可切固定 30/70); 進可買區 = RSI14 轉勢向上且谷底 ≤ 下界; 進可賣區 = 轉勢向下且峰頂 ≥ 上界;
//       可買區結束 (④c 可選) = 跌破進區谷底 [預設] / RSI14 轉勢向下 / 跌破 50 或谷底; 每個交易日開始清空; 持倉中可買區結束 → 平倉 (M2區結束)
//   模式 4 (④e): EMA9 斜率 > 0 = 綠柱 = 可買、可持倉; 斜率 ≤ 0 = 紅柱 = 不可持倉 → 持倉中出現紅柱那一根本根收盤價立即平倉 (M4紅柱, immediately = true), 排在所有出場之前
//   買 = 模式 2 處於可買區 且 模式 4 綠柱, 且本根至少一個剛出現 (剛進可買區 / EMA9 剛轉綠) → 下一根開盤成交
//   出場順序: M4紅柱 (立即) → ④f 賣法 (預設 模式 4 可賣區 + 模式 2 賣訊; 實際排在紅柱之後幾乎不會先觸發) → M2區結束 → SL (預設關) → 15:58 EOD → 窗口結束
//   模式 1 (MACD 柱到界) 與模式 3 (9/26/9 金叉): 程式碼已刪除, 不計算、不顯示、不參與任何決定
//  【主圖】EMA9 細綠線 · 藍 / 紅三角 = 真正成交 · 淺色直線貫通 · 橙框 = 持倉期間 · 右上 回測摘要 + 81 組參數掃描 (合併一表) · 左下 觸發參數表
//  【副圖】模式 2 與模式 4 合併在一支 R9_TV-1M-RSI-winrate_(mode 2,4) 副圖: 上半 RSI14 + 上下界 + 區間底色 + ▲▼×, 底部一條綠 / 紅色帶 = 模式 4; 兩支一起 Add to chart, 同名設定要一致
//  【參數掃描 (⑨)】81 組 = 模式 2 下界百分位∈5/10/20 × 上界百分位∈80/90/95 × 結束規則 × 模式 4 斜率根數∈1/3/5, 每組都是 R9 規則 (含紅柱立即平倉), 橙底列 = 現行組合
//  【共用規則】只做多 · 全部本金 · 收盤確認下一根開盤成交 (M4紅柱 例外: 本根收盤價) · 手續費 0.03%/邊 + 滑點 2 tick · 美股 09:30-16:00 NY · 15:45 後不開新倉 · 15:58 強平 · margin_long = 0
//  【使用】圖表切【1 分鐘】→ Pine Editor 貼上 → 檢查最後一行 → Save (輸入同名) → Add to chart → 主圖右上摘要 + 左下參數表 + Strategy Tester
//  版本戳 R9_TV-1M-dashboard_(mode 2,4)_(MM月DD日; HH:MM), 括號內 = 建置時間 HKT; 檔名以 . 代替 : ; 本檔零延續行
'''
hdr = BAR + HDR_MAIN + BAR
n = hdr.count('\n') + body.count('\n') + 1 + 1
full = hdr.replace('{n}', str(n)) + body + '\n' + END_TAG.format(name=NAME_MAIN, n=n) + '\n'
assert full.count('\n') == n, (full.count('\n'), n)
f_main = NAME_MAIN.replace(':', '.') + '.pine'
io.open(f_main, 'w', encoding='utf-8', newline='\n').write(full)
print('wrote', f_main, n, 'lines; verify:', verify(full) or 'PASS')

# ═════════════════════════════ 副圖: RSI14 (模式 2) + 模式 4 色帶 ═════════════════════════════
P = lines_of(SRC_RSI)
old_pane = re.search(r'^indicator\("([^"]+)"', '\n'.join(P), re.M).group(1)
ps = '\n'.join(P).replace(old_pane, NAME_PANE)
ps = rep(ps, 'gR2        = "② 模式 2 · RSI 14 可買區 / 可賣區 (與主策略 ④c 保持一致)"', 'gR2        = "② 模式 2 · RSI 14 可買區 / 可賣區 (與主策略 ④c 保持一致)"')
# 模式 4 輸入 + 計算 (放在 ③ 顯示之前)
ps = rep(ps, '// ─────────────────────────── ③ 顯示 ───────────────────────────\n',
           '// ─────────────────────────── ②b 模式 4 · EMA9 斜率 (與主策略 ④e 保持一致) ───────────────────────────\n'
           'gR4      = "②b 模式 4 · EMA9 斜率 (與主策略 ④e 保持一致)"\n'
           'm4EmaLen = input.int(9, "EMA 長度", minval = 1, group = gR4, display = display.none)\n'
           'm4Look   = input.int(1, "斜率取幾根: EMA 現值 − N 根前的值 > 0 = 向上 (1 = 逐根比較)", minval = 1, maxval = 30, group = gR4, display = display.none)\n'
           'm4Ema    = ta.ema(close, m4EmaLen)\n'
           'm4Slope  = m4Ema[m4Look] == 0 ? 0.0 : (m4Ema - m4Ema[m4Look]) / m4Ema[m4Look] * 100.0\n'
           'm4Up     = m4Slope > 0                                 // 綠柱 = 可買、可持倉; 紅柱 = 不可持倉 (主策略立即平倉)\n'
           '\n'
           '// ─────────────────────────── ③ 顯示 ───────────────────────────\n')
ps = rep(ps, 'p0    = plot(0, "0", color = color.new(color.gray, 90), display = display.pane)\n',
           'p0    = plot(0, "0", color = color.new(color.gray, 90), display = display.pane)\n'
           '// 模式 4 色帶: 副圖底部 (RSI 0 以下) 一條固定高度的柱, 綠 = EMA9 向上 (可買 / 可持倉), 紅 = 向下 (不可持倉, 主策略立即平倉)\n'
           'cM4Up = color.rgb(0, 130, 60)\n'
           'cM4Dn = color.rgb(200, 60, 60)\n'
           'plot(-4, "模式4 EMA9 斜率色帶 (綠可買 / 紅平倉)", style = plot.style_columns, histbase = -14, color = m4Up ? color.new(cM4Up, 15) : color.new(cM4Dn, 15), display = display.pane)\n'
           'if inWindow and m4Up and not m4Up[1]\n'
           '    label.new(bar_index, -4, "可買", style = label.style_label_down, color = color.new(cM4Up, 30), textcolor = color.white, size = size.tiny)\n'
           'if inWindow and not m4Up and m4Up[1]\n'
           '    label.new(bar_index, -14, "紅柱→平倉", style = label.style_label_up, color = color.new(cM4Dn, 30), textcolor = color.white, size = size.tiny)\n')
# 統計表: 加 3 列模式 4
ps = rep(ps, 'var int nBarAll = 0\n', 'var int nBarAll = 0\nvar int nBarUp4 = 0\nvar int nDn4 = 0\n')
ps = rep(ps, '    nBarAll += 1\n', '    nBarAll += 1\n    nBarUp4 += m4Up ? 1 : 0\n    nDn4 += (not m4Up and m4Up[1]) ? 1 : 0\n')
ps = rep(ps, 'var table tb = table.new(posT, 2, 7, border_width = 1, frame_width = 1, frame_color = color.gray)\n', 'var table tb = table.new(posT, 2, 10, border_width = 1, frame_width = 1, frame_color = color.gray)\n')
ps = rep(ps, '    table.clear(tb, 0, 0, 1, 6)\n', '    table.clear(tb, 0, 0, 1, 9)\n')
ps = rep(ps, '"模式 2 · RSI " + str.tostring(rsiFastLen) + " 可買區 / 可賣區 (R5 只用 RSI14)"', '"R9 · 模式 2 RSI" + str.tostring(rsiFastLen) + " 可買區 / 可賣區 + 模式 4 EMA" + str.tostring(m4EmaLen) + " 色帶"')
last_row = [l for l in ps.split('\n') if l.startswith('    table.cell(tb, 1, 6,')]
assert len(last_row) == 1
ps = rep(ps, last_row[0], last_row[0] + '\n'
           '    table.cell(tb, 0, 7, "模式 4 · EMA" + str.tostring(m4EmaLen) + " 斜率 (" + str.tostring(m4Look) + " 根)", text_size = size.tiny, text_color = color.white, bgcolor = m4Up ? cM4Up : cM4Dn)\n'
           '    table.cell(tb, 1, 7, (m4Up ? "現在綠柱 → 可買 / 可持倉" : "現在紅柱 → 不可持倉 (立即平倉)") + " · " + str.tostring(m4Slope, "#.####") + "%", text_size = size.tiny, text_color = color.white, bgcolor = m4Up ? cM4Up : cM4Dn)\n'
           '    table.cell(tb, 0, 8, "窗內 綠柱 K 數 / 全部 · 綠柱比例", text_size = size.tiny, bgcolor = hBg)\n'
           '    table.cell(tb, 1, 8, str.tostring(nBarUp4) + " / " + str.tostring(nBarAll) + " · " + str.tostring(nBarAll > 0 ? nBarUp4 * 100.0 / nBarAll : 0.0, "#.#") + "%", text_size = size.tiny)\n'
           '    table.cell(tb, 0, 9, "綠轉紅次數 (紅柱→平倉)", text_size = size.tiny, bgcolor = hBg)\n'
           '    table.cell(tb, 1, 9, str.tostring(nDn4), text_size = size.tiny, text_color = color.red)')
# 副圖底部標籤文字 (左側線名標籤) 不動; 表頭
pane_hdr = f'''//  {NAME_PANE}  ·  R9 副圖: 模式 2 (RSI14 可買區 / 可賣區) 與 模式 4 (EMA9 斜率色帶) 合併在同一個副圖 · 配合主策略 R9_TV-1M-dashboard_(mode 2,4) 一起掛 · 純顯示不下單
//  上半 (0-100): 深棕粗線 RSI14 · 綠/紅細線 = 下界/上界 (最近 120 根 RSI14 的第 10/90 百分位) · 底色 淺藍 = 可買區 / 淺紅 = 可賣區 · ▲ 進可買區 (轉勢向上且谷底到下界) · ▼ 進可賣區 · × 區間結束
//  底部 (0 以下) 一條色帶 = 模式 4: 綠 = EMA9 斜率 > 0 (可買 / 可持倉), 紅 = 斜率 ≤ 0 (不可持倉; 主策略持倉中出現紅柱那一根立即以收盤價平倉); 由紅轉綠標「可買」, 由綠轉紅標「紅柱→平倉」
//  ② 的 RSI 長度 / 下上界方式 / 百分位 / 到界回看 / 結束規則 / 每日清空 必須與主策略 ④c 一致; ②b 的 EMA 長度 / 斜率根數必須與主策略 ④e 一致; 右上表 = 兩個模式的現況與統計
//  四處必須一致: 標題 = shorttitle = 檔名 = TradingView 腳本名稱 (結尾的 ")" 不可漏); 本檔共 {{n}} 行, 最後一行是 END OF FILE
'''
phdr = BAR + pane_hdr + BAR
n2 = phdr.count('\n') + ps.count('\n') + 1 + 1
full2 = phdr.replace('{n}', str(n2)) + ps + '\n' + END_TAG.format(name=NAME_PANE, n=n2) + '\n'
assert full2.count('\n') == n2
f_pane = NAME_PANE.replace(':', '.') + '.pine'
io.open(f_pane, 'w', encoding='utf-8', newline='\n').write(full2)
print('wrote', f_pane, n2, 'lines; verify:', verify(full2) or 'PASS')
for fn, html, eyebrow in ((f_main, 'paste_R9-dashboard.html', 'R9 · 只做多 · 模式 2 + 4 主策略 (主圖) · 1 分鐘日內策略 (市場預設 美股)'), (f_pane, 'paste_R9-RSI-winrate.html', 'R9 · 模式 2 + 模式 4 合併副圖 (純顯示)')):
    make_paste_page.make(fn, html)
    h = io.open(html, encoding='utf-8').read()
    h = h.replace('1 分鐘日內策略 (市場預設 美股, Inputs 可切港股)', eyebrow)
    io.open(html, 'w', encoding='utf-8', newline='\n').write(h)
