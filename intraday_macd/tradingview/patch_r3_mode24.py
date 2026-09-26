# -*- coding: utf-8 -*-
"""patch_r3_mode24.py — R3: 在 R2 (只用模式 2 + 4) 之上調整模式 2 進區方式與買賣過濾, 模式 4 紅柱 = 可賣區。
套在 patch_r2_mode24.apply() 之後的主策略本體, 以及 R2 的 RSI 副圖 / 模式 4 副圖本體。

R3 改動 (針對 NVDA 2026-09-25 1 分鐘圖: 下跌途中兩次反彈買入被止損、之後的急升沒有買到):
  ④c 進可買區 / 可賣區方式 (m2EntryMd): 轉勢且到界 (R2) / RSI14 穿越 RSI28 (金叉 / 死叉) / 兩者任一 (R3 預設)
      — 急升時 RSI14 不會先跌到下界再轉勢, 只會由中間直接升穿 RSI28; 加入「金叉進區」才買得到
  ④c 穿越進區時的谷底 / 峰頂 = 最近 N 根 RSI14 的最低 / 最高 (m2SwingLen, 預設 10), 供結束規則「跌破谷底」用
  ④c 買入時要求 RSI14 > RSI28 (m2FastAbove, 預設開; 賣出要求 RSI14 < RSI28) — 下跌途中的反彈, 快線仍在慢線之下, 不買; 快線升穿慢線那一根也算「剛出現」
  ④e / ④f 模式 4 紅柱 (EMA9 向下) = 可賣區 (狀態); 整體賣點 = 處於模式 4 可賣區 且 模式 2 賣訊 (處於可賣區, 本根至少一個剛出現: 剛進可賣區 / EMA9 剛轉向下 / RSI14 剛跌破 RSI28)
  ⑨ 掃描 81 組 = 進區方式 {轉勢, 穿越, 任一} × 下界百分位 {5,10,20} × 結束規則 {3} × 模式 4 根數 {1,3,5}; 賣法與快慢線過濾用 ④c / ④f 現值
"""


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, n, old[:90])
    return s.replace(old, new)


ENTRY_OPTS = '["轉勢且到界 (R2)", "RSI14 穿越 RSI28 (金叉 / 死叉)", "兩者任一 (R3 預設)"]'
R3_INPUTS = ('m2EntryMd  = input.string("兩者任一 (R3 預設)", "進可買區 / 可賣區的方式 (R3)", options = ' + ENTRY_OPTS + ', group = gR2, tooltip = "轉勢且到界 (R2) = RSI14 梯度轉正且谷底到達下界 (買低); 穿越 = RSI14 升穿 RSI28 即進可買區 (跟動能, 急升時 RSI 不會先跌到下界); 兩者任一 = 兩種都算, R3 預設。可賣區用相反條件 (轉勢向下且到上界 / RSI14 跌破 RSI28)。", display = display.none)\n'
             'm2SwingLen = input.int(10, "穿越進區時, 谷底 / 峰頂取最近 N 根 RSI14 的最低 / 最高 (結束規則「跌破谷底」用)", minval = 2, maxval = 60, group = gR2, display = display.none)\n'
             'm2FastAbove = input.bool(true, "買入時要求 RSI14 > RSI28 (快線在慢線之上; 賣出要求 RSI14 < RSI28) — 過濾下跌途中的反彈 (R3 預設開)", group = gR2, tooltip = "下跌途中的反彈: RSI14 由谷底轉勢向上但仍在 RSI28 之下, 多數失敗。開啟後買入那一根必須 RSI14 > RSI28; RSI14 剛升穿 RSI28 那一根也算「剛出現買點」。賣出對稱: 要求 RSI14 < RSI28, 剛跌破也算剛出現。", display = display.none)\n')

OLD_ZONE_MAIN = '''m2BuyStart  = turnUpF and reachLoF                     // 進入可買區 (單根事件)
m2SellStart = turnDnF and reachHiF                     // 進入可賣區 (單根事件)
'''
NEW_ZONE_MAIN = '''entTurn    = m2EntryMd != "RSI14 穿越 RSI28 (金叉 / 死叉)"   // 轉勢且到界 這一種進區方式是否啟用
entCross   = m2EntryMd != "轉勢且到界 (R2)"                  // 穿越 這一種進區方式是否啟用
swingLo    = ta.lowest(rsiF, m2SwingLen)               // 穿越進區時當作谷底 / 峰頂 (最近 N 根 RSI14 的最低 / 最高)
swingHi    = ta.highest(rsiF, m2SwingLen)
m2BuyTurn   = entTurn and turnUpF and reachLoF         // 轉勢且到界 進可買區
m2SellTurn  = entTurn and turnDnF and reachHiF
m2BuyStart  = m2BuyTurn or (entCross and xFSup)        // 進入可買區 (單根事件; R3: 轉勢到界 或 RSI14 升穿 RSI28)
m2SellStart = m2SellTurn or (entCross and xFSdn)       // 進入可賣區 (單根事件)
m2BuyOK    = not m2FastAbove or rsiF > rsiS            // R3 買入過濾: 快線在慢線之上
m2SellOK   = not m2FastAbove or rsiF < rsiS            // R3 賣出過濾: 快線在慢線之下
'''
OLD_ZONE_PANE = '''m2BuyStart  = turnUpF and reachLoF                     // 進入可買區
m2SellStart = turnDnF and reachHiF                     // 進入可賣區
'''
NEW_ZONE_PANE = '''entTurn    = m2EntryMd != "RSI14 穿越 RSI28 (金叉 / 死叉)"
entCross   = m2EntryMd != "轉勢且到界 (R2)"
swingLo    = ta.lowest(rsiF, m2SwingLen)
swingHi    = ta.highest(rsiF, m2SwingLen)
m2BuyTurn   = entTurn and turnUpF and reachLoF
m2SellTurn  = entTurn and turnDnF and reachHiF
m2BuyStart  = m2BuyTurn or (entCross and xFSup)        // 進入可買區 (R3: 轉勢到界 或 RSI14 升穿 RSI28)
m2SellStart = m2SellTurn or (entCross and xFSdn)       // 進入可賣區
'''
OLD_SET = '''if m2BuyStart                                          // 進入新區優先於現區結束
    m2State  := 1
    m2Trough := rsiF[1]
else if m2SellStart
    m2State := -1
    m2Peak  := rsiF[1]
'''
NEW_SET = '''if m2BuyStart                                          // 進入新區優先於現區結束
    m2State  := 1
    m2Trough := m2BuyTurn ? rsiF[1] : swingLo          // 轉勢進區 = 谷底在前一根; 穿越進區 = 最近 N 根最低
else if m2SellStart
    m2State := -1
    m2Peak  := m2SellTurn ? rsiF[1] : swingHi
'''
SELL0_OLD = '模式 2 可賣區 + 模式 4 向下 (兩者同時, 本根至少一個剛出現)'
SELL0_NEW = '模式 4 可賣區 (紅柱, EMA9 向下) + 模式 2 賣訊 (兩者同時, 本根至少一個剛出現)'


def apply_main(s):
    # ④c 新輸入 (放在 rsiF 計算之前)
    s = rep(s, 'rsiF       = ta.rsi(close, rsiFastLen)\n', R3_INPUTS + 'rsiF       = ta.rsi(close, rsiFastLen)\n')
    s = rep(s, OLD_ZONE_MAIN, NEW_ZONE_MAIN)
    s = rep(s, OLD_SET, NEW_SET)
    # 買入核心 / 事件: 快慢線過濾 + 升穿也算剛出現
    s = rep(s, 'buyCore = (not useM1 or m1Live) and (not useM3 or m3Live) and m2InBuy   // R2:', 'buyCore = (not useM1 or m1Live) and (not useM3 or m3Live) and m2InBuy and m2BuyOK   // R3: 加 RSI14 > RSI28 過濾; R2:')
    s = rep(s, 'buyEvt  = (useM1 and m1Buy) or (useM3 and m3Buy) or m2BuyStart   //', 'buyEvt  = (useM1 and m1Buy) or (useM3 and m3Buy) or m2BuyStart or (m2FastAbove and xFSup)   // R3: RSI14 剛升穿 RSI28 也算剛出現;')
    # ④e / ④f 賣法 0: 模式 4 可賣區 + 模式 2 賣訊
    s = rep(s, SELL0_OLD, SELL0_NEW, 3)
    s = rep(s, 'm4DnStart = useM4 and not m4Up and m4Up[1]            // 模式 4 由可買轉為不可的那一根 (EMA9 剛轉向下; 賣的「剛出現」)\n',
               'm4SellZone = useM4 and not m4Up                       // R3: 模式 4 紅柱 (EMA9 向下) = 可賣區 (狀態)\n'
               'm4DnStart = useM4 and not m4Up and m4Up[1]            // 模式 4 由可買轉為可賣區的那一根 (EMA9 剛轉向下; 賣的「剛出現」)\n')
    s = rep(s, 'sellSig  = sellRuleI == 0 ? (m2InSell and (not useM4 or not m4Up) and (m2SellStart or m4DnStart)) : sellRuleI == 1 ? m2SellStart : sellRuleI == 2 ? false : sellSigM1   // R2 合格賣點\n',
               'sellSig  = sellRuleI == 0 ? (m2InSell and m2SellOK and (not useM4 or m4SellZone) and (m2SellStart or m4DnStart or (m2FastAbove and xFSdn))) : sellRuleI == 1 ? (m2SellStart and m2SellOK) : sellRuleI == 2 ? false : sellSigM1   // R3 合格賣點: 模式 4 可賣區 且 模式 2 賣訊 (本根至少一個剛出現)\n')
    s = rep(s, 'sellCmt  = sellRuleI == 0 ? "S-M2&M4" :', 'sellCmt  = sellRuleI == 0 ? "S-M4區&M2" :')
    # ⑨ 掃描: 27 個區間狀態機 (進區方式 × 下界 × 結束規則), 網格改為 進區方式 × 下界 × 結束規則 × M4 根數
    s = rep(s, 'int NV = 81                                          // 3(下界百分位) × 3(結束規則) × 3(M4 根數) × 3(賣法)\nint NZ = 9                                           // 模式 2 區間狀態機: 3 個下界百分位 × 3 種結束規則\n',
               'int NV = 81                                          // 3(進區方式) × 3(下界百分位) × 3(結束規則) × 3(M4 根數); 賣法 / 快慢線過濾用 ④f / ④c 現值\nint NZ = 27                                          // 模式 2 區間狀態機: 3 種進區方式 × 3 個下界百分位 × 3 種結束規則\n')
    s = rep(s, '''for z = 0 to NZ - 1
    iPz = math.floor(z / 3)
    iEz = z % 3
    rLo = iPz == 0 ? zReachLo0 : iPz == 1 ? zReachLo1 : zReachLo2
    rHi = iPz == 0 ? zReachHi0 : iPz == 1 ? zReachHi1 : zReachHi2
    bSt = turnUpF and rLo
    sSt = turnDnF and rHi
''', '''for z = 0 to NZ - 1
    iNz = math.floor(z / 9)                            // 0 轉勢且到界 / 1 穿越 / 2 任一
    iPz = math.floor(z / 3) % 3
    iEz = z % 3
    rLo = iPz == 0 ? zReachLo0 : iPz == 1 ? zReachLo1 : zReachLo2
    rHi = iPz == 0 ? zReachHi0 : iPz == 1 ? zReachHi1 : zReachHi2
    bTn = iNz != 1 and turnUpF and rLo
    sTn = iNz != 1 and turnDnF and rHi
    bSt = bTn or (iNz != 0 and xFSup)
    sSt = sTn or (iNz != 0 and xFSdn)
''')
    s = rep(s, '''    if bSt
        st  := 1
        trZ := rsiF[1]
    else if sSt
        st  := -1
        pkZ := rsiF[1]
''', '''    if bSt
        st  := 1
        trZ := bTn ? rsiF[1] : swingLo
    else if sSt
        st  := -1
        pkZ := sTn ? rsiF[1] : swingHi
''')
    s = rep(s, '''        iP   = math.floor(v1 / 27)                 // Pine 的 / 永遠回傳 float, 不截斷 → 一定要 floor
        iE   = math.floor(v1 / 9) % 3
        iL   = math.floor(v1 / 3) % 3
        iS   = v1 % 3
        zi   = iP * 3 + iE
''', '''        iN   = math.floor(v1 / 27)                 // Pine 的 / 永遠回傳 float, 不截斷 → 一定要 floor
        iP   = math.floor(v1 / 9) % 3
        iE   = math.floor(v1 / 3) % 3
        iL   = v1 % 3
        zi   = iN * 9 + iP * 3 + iE
''')
    s = rep(s, '''        bSig  = inB and m13OK and (not useM4 or upV) and (bSt2 or m13Evt or (useM4 and stV))
        sSig  = iS == 0 ? (inS and (not useM4 or not upV) and (sSt2 or (useM4 and dnV))) : iS == 1 ? sSt2 : false
''', '''        bSig  = inB and m2BuyOK and m13OK and (not useM4 or upV) and (bSt2 or m13Evt or (useM4 and stV) or (m2FastAbove and xFSup))
        sSig  = sellRuleI == 0 ? (inS and m2SellOK and (not useM4 or not upV) and (sSt2 or (useM4 and dnV) or (m2FastAbove and xFSdn))) : sellRuleI == 1 ? (sSt2 and m2SellOK) : false   // 賣法 3 (舊規則) 掃描不模擬 → 視為不主動賣
''')
    s = rep(s, '''liveIs = sellRuleI <= 2 ? sellRuleI : -1
liveV  = (liveIp >= 0 and liveIl >= 0 and liveIs >= 0) ? liveIp * 27 + liveIe * 9 + liveIl * 3 + liveIs : -1
''', '''liveIn = m2EntryMd == "轉勢且到界 (R2)" ? 0 : m2EntryMd == "RSI14 穿越 RSI28 (金叉 / 死叉)" ? 1 : 2
liveV  = (liveIp >= 0 and liveIl >= 0) ? liveIn * 27 + liveIp * 9 + liveIe * 3 + liveIl : -1
''')
    s = rep(s, '''        iP2  = math.floor(vv / 27)
        iE2  = math.floor(vv / 9) % 3
        iL2  = math.floor(vv / 3) % 3
        iS2  = vv % 3
        pTxt = iP2 == 0 ? "P5" : iP2 == 1 ? "P10" : "P20"
        eTxt = iE2 == 0 ? "破慢線/谷底" : iE2 == 1 ? "14轉下" : "28轉下"
        lTxt = iL2 == 0 ? "1" : iL2 == 1 ? "3" : "5"
        sTxt = iS2 == 0 ? "M2&M4" : iS2 == 1 ? "進賣區" : "只區結束"
''', '''        iN2  = math.floor(vv / 27)
        iP2  = math.floor(vv / 9) % 3
        iE2  = math.floor(vv / 3) % 3
        iL2  = vv % 3
        pTxt = (iN2 == 0 ? "轉勢 " : iN2 == 1 ? "穿越 " : "任一 ") + (iP2 == 0 ? "P5" : iP2 == 1 ? "P10" : "P20")
        eTxt = iE2 == 0 ? "破慢線/谷底" : iE2 == 1 ? "14轉下" : "28轉下"
        lTxt = iL2 == 0 ? "1" : iL2 == 1 ? "3" : "5"
''')
    s = rep(s, '''            table.cell(rpt, 8, i2 + 2, pTxt + " / " + eTxt, text_size = sizeV, bgcolor = rBg)
            table.cell(rpt, 9, i2 + 2, lTxt + " / " + sTxt, text_size = sizeV, bgcolor = rBg)
''', '''            table.cell(rpt, 8, i2 + 2, pTxt, text_size = sizeV, bgcolor = rBg)
            table.cell(rpt, 9, i2 + 2, eTxt + " / " + lTxt, text_size = sizeV, bgcolor = rBg)
''')
    s = rep(s, '    table.cell(rpt, 8, 1, "M2 下界P/結束", text_size = sizeV, bgcolor = sBg)\n    table.cell(rpt, 9, 1, "M4根/賣法", text_size = sizeV, bgcolor = sBg)\n',
               '    table.cell(rpt, 8, 1, "M2 進區/下界P", text_size = sizeV, bgcolor = sBg)\n    table.cell(rpt, 9, 1, "結束/M4根", text_size = sizeV, bgcolor = sBg)\n')
    s = rep(s, '"掃描 81 組 (R2: M2 下界P×結束規則 × M4 根數×賣法) · 最大昇幅 "', '"掃描 81 組 (R3: M2 進區方式×下界P×結束規則 × M4 根數) · 最大昇幅 "')
    s = rep(s, '"現行 M2 " + (rsiBandMd == "固定: 30 / 70" ? "固定30/70" : "P" + str.tostring(rsiPctLo, "#") + "/" + str.tostring(rsiPctHi, "#")) + " " + (endModeA ? "破慢線/谷底" : endModeB ? "14轉下" : "28轉下") + " · M4 " + str.tostring(m4Look) + " 根 · 賣 " + sellCmt',
               '"現行 M2 " + (liveIn == 0 ? "轉勢 " : liveIn == 1 ? "穿越 " : "任一 ") + (rsiBandMd == "固定: 30 / 70" ? "固定30/70" : "P" + str.tostring(rsiPctLo, "#") + "/" + str.tostring(rsiPctHi, "#")) + " " + (endModeA ? "破慢線/谷底" : endModeB ? "14轉下" : "28轉下") + " · M4 " + str.tostring(m4Look) + " 根 · 賣 " + sellCmt + (m2FastAbove ? " · 快>慢過濾" : "")')
    s = rep(s, '"不在網格 (P∈5/10/20 · M4∈1/3/5 · 賣法≠舊規則)"', '"不在網格 (P∈5/10/20 · M4∈1/3/5)"')
    s = rep(s, '對 81 組「模式 2 下界百分位∈{5,10,20} (上界 = 100 − 下界) × 可買區結束規則∈{跌破慢線或谷底, RSI14 轉勢向下, RSI28 轉勢向下} × 模式 4 斜率根數∈{1,3,5} × 賣法∈{M2 可賣區 + M4 向下, 剛進可賣區即賣, 只靠區結束}」各跑一套虛擬回測 (每組都是 R2 規則: 買 = 該組的可買區 + 該組的 EMA9 向上 且本根至少一個剛出現 (④f 若加回模式 1 / 3 也一併要求); 另有可買區結束平倉 / EOD / 固定止損; 同樣下一根開盤成交、同樣時段、同樣手續費滑點), 以最後一根收盤 mark-to-market 排名。橙底列 = 現行 ④c / ④e / ④f 的組合 (④c 用固定 30/70 或百分位不在網格時顯示「不在網格」)。',
               '對 81 組「模式 2 進區方式∈{轉勢且到界, 穿越, 任一} × 下界百分位∈{5,10,20} (上界 = 100 − 下界) × 可買區結束規則∈{跌破慢線或谷底, RSI14 轉勢向下, RSI28 轉勢向下} × 模式 4 斜率根數∈{1,3,5}」各跑一套虛擬回測 (每組都是 R3 規則: 買 = 該組的可買區 + 該組的 EMA9 向上 + ④c 快慢線過濾 且本根至少一個剛出現; 賣 = ④f 現行賣法 (舊規則不模擬); 另有可買區結束平倉 / EOD / 固定止損; 同樣下一根開盤成交、同樣時段、同樣手續費滑點), 以最後一根收盤 mark-to-market 排名。橙底列 = 現行 ④c / ④e 的組合 (④c 用固定 30/70 或百分位不在網格時顯示「不在網格」)。')
    s = rep(s, 'gSW       = "⑨ 參數掃描 (R2: 模式 2 + 4 的 81 組)"', 'gSW       = "⑨ 參數掃描 (R3: 模式 2 進區方式 × 下界 × 結束規則 × 模式 4 根數)"')
    # prm 文字
    s = rep(s, '(sellRuleI == 0 ? "M2 可賣區 + M4 向下" :', '(sellRuleI == 0 ? "M4 可賣區 (紅柱) + M2 賣訊" :')
    s = rep(s, '"買 (R2): M2 可買區 + M4 向上"', '"買 (R3): M2 可買區" + (m2FastAbove ? " (RSI14>RSI28)" : "") + " + M4 向上"')
    s = rep(s, '④f 賣法改 M2&M4 同時; 要更鬆: 反之', '④f 賣法改 M4區&M2 同時 · ④c 進區方式改「轉勢且到界」 · 開快慢線過濾; 要更鬆: 反之 (進區方式改「任一」)')
    s = rep(s, '"R2 M2 " + (rsiBandMd == "固定: 30 / 70"', '"R3 M2 " + (liveIn == 0 ? "轉勢 " : liveIn == 1 ? "穿越 " : "任一 ") + (rsiBandMd == "固定: 30 / 70"')
    s = rep(s, '"===== R2 模式 2+4 回測 (RSI區+EMA9; 模式 1/3 "', '"===== R3 模式 2+4 回測 (RSI區 " + m2EntryMd + "; EMA9; 模式 1/3 "')
    s = rep(s, '(含 S-M2&M4 或 ④f 選的賣法 / M2區結束 / SL / EOD / 窗口結束)', '(含 S-M4區&M2 或 ④f 選的賣法 / M2區結束 / SL / EOD / 窗口結束)')
    s = rep(s, '"期內無交易 — 檢查 ⑤ 時段 / margin_long = 0 / ④c 可買區規則 (下界百分位、結束規則) / ④e 模式 4 / ⑨b 自動調參"', '"期內無交易 — 檢查 ⑤ 時段 / margin_long = 0 / ④c 可買區規則 (進區方式、下界百分位、結束規則、快慢線過濾) / ④e 模式 4"', 0) if False else s
    assert 'iS2' not in s and 'liveIs' not in s
    return s


def apply_rsi(s):
    s = rep(s, '// 全部 ta.* 在全域無條件計算 (Pine v6 的 and / or 是短路求值)\n', R3_INPUTS.replace('(R3)", options', '(R3; 與主策略 ④c 一致)", options').replace('m2FastAbove = input.bool(true, "買入時要求 RSI14 > RSI28 (快線在慢線之上; 賣出要求 RSI14 < RSI28) — 過濾下跌途中的反彈 (R3 預設開)"', 'm2FastAbove = input.bool(true, "買入時要求 RSI14 > RSI28 (只影響 ▲▼ 標記的顏色深淺: 快線在慢線之上的可買區才是深色; 與主策略 ④c 一致)"') + '// 全部 ta.* 在全域無條件計算 (Pine v6 的 and / or 是短路求值)\n')
    s = rep(s, OLD_ZONE_PANE, NEW_ZONE_PANE)
    s = rep(s, OLD_SET, NEW_SET)
    s = rep(s, 'm2Zone     = m2InBuy ? "可買區" : m2InSell ? "可賣區" : "無"\n', 'm2BuyOK    = not m2FastAbove or rsiF > rsiS\nm2SellOK   = not m2FastAbove or rsiF < rsiS\nm2Zone     = m2InBuy ? (m2BuyOK ? "可買區 (快>慢, 可買)" : "可買區 (快<慢, 等升穿)") : m2InSell ? (m2SellOK ? "可賣區 (快<慢, 可賣)" : "可賣區 (快>慢, 等跌破)") : "無"\n')
    return s


def apply_m4(s):
    s = rep(s, '// ─────────────────────────── ② 模式 4 · EMA9 斜率為正 = 可以買入 (與主策略 ④e 一致)', '// ─────────────────────────── ② 模式 4 · EMA9 斜率為正 = 可以買入; 斜率為負 (紅柱) = 可賣區 (R3; 與主策略 ④e 一致)')
    s = rep(s, '// ─────────────────────────── ③ 顯示: 斜率柱 (綠 = 向上可買 / 紅 = 向下不可) + 0 軸', '// ─────────────────────────── ③ 顯示: 斜率柱 (綠 = 向上可買 / 紅 = 可賣區) + 0 軸')
    s = rep(s, 'bgcolor(m4Up ? color.new(cUp, 90) : color.new(cDn, 92), title = "可買 / 不可 底色")', 'bgcolor(m4Up ? color.new(cUp, 90) : color.new(cDn, 88), title = "可買 / 可賣區 底色")')
    s = rep(s, '''// 由不可轉為可買的那一根標一下 (只在回測窗內)
if inWindow and m4Up and not m4Up[1]
    label.new(bar_index, m4Slope, "可買", style = label.style_label_down, color = color.new(cUp, 30), textcolor = color.white, size = size.tiny)
''', '''// 由可賣區轉為可買的那一根標「可買」, 由可買轉為可賣區的那一根標「可賣」(只在回測窗內)
if inWindow and m4Up and not m4Up[1]
    label.new(bar_index, m4Slope, "可買", style = label.style_label_down, color = color.new(cUp, 30), textcolor = color.white, size = size.tiny)
if inWindow and not m4Up and m4Up[1]
    label.new(bar_index, m4Slope, "可賣", style = label.style_label_up, color = color.new(cDn, 30), textcolor = color.white, size = size.tiny)
''')
    s = rep(s, '"模式4 · EMA" + str.tostring(m4EmaLen) + " 斜率: 綠柱 (>0) = 趨勢向上可買入, 紅柱 (<0) = 不可"', '"模式4 · EMA" + str.tostring(m4EmaLen) + " 斜率: 綠柱 (>0) = 趨勢向上可買入, 紅柱 (<0) = 可賣區 (R3: 要再加模式 2 賣訊才成整體賣點)"')
    s = rep(s, 'm4Up ? "現在向上 → 可買" : "現在向下 → 不可"', 'm4Up ? "現在向上 → 可買" : "現在向下 → 可賣區"')
    s = rep(s, '"窗內 K 數 / 向上 K 數"', '"窗內 K 數 / 向上 (可買) K 數"')
    return s
