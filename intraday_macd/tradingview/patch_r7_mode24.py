# -*- coding: utf-8 -*-
"""patch_r7_mode24.py — R7: 模式 4 只有綠柱 (EMA9 向上) 才可持倉; 出現紅柱那一根立即以收盤價平倉。套在 patch_r6 之後。

R7 (取代 R6 的「剛轉向下才平倉、下一根開盤成交」):
  持倉中只要本根 EMA9 斜率 ≤ 0 (副圖紅柱) → strategy.close(…, immediately = true): 本根收盤價成交, 不等下一根開盤; 出場原因 M4紅柱
  排在所有出場之前 (賣訊 / 可買區結束 / 止損 / EOD 之前); 剛在本根開盤買入、本根即轉紅也會被平掉
  ⑨ 掃描同步: 該組的 EMA9 (1/3/5 根) 本根不向上 → 以本根收盤價 (含滑點) 立即平倉
"""


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, n, old[:90])
    return s.replace(old, new)


def apply_main(s):
    s = rep(s, 'm4ExitOnEnd = input.bool(true, "R6: 持倉中模式 4 離開可買區 (EMA9 剛轉向下) → 其它模式的買點失效 → 立即平倉 (M4區結束)", group = gR4, tooltip = "模式 4 是買入的閘門: EMA9 向上才可買。R6: 一旦 EMA9 轉向下 (斜率轉負, 副圖轉紅柱), 買入條件已不成立, 持倉不再等模式 2 賣訊, 直接平倉。與 ④c 的「可買區結束平倉」並列, 排在賣訊之後、固定止損之前。關掉 = 回到 R5 (只靠賣訊 / 可買區結束 / 收市)。", display = display.none)\n',
               'm4ExitOnEnd = input.bool(true, "R7: 只有綠柱 (EMA9 向上) 才可持倉; 出現紅柱那一根立即以收盤價平倉 (M4紅柱)", group = gR4, tooltip = "模式 4 是持倉的閘門: EMA9 向上 (綠柱) 才可買、才可持倉。R7: 持倉中只要本根 EMA9 斜率 ≤ 0 (副圖紅柱), 不等模式 2 賣訊、不等下一根開盤, 本根收盤價立即平倉 (strategy.close immediately = true), 出場原因 M4紅柱; 排在所有出場之前。剛在本根開盤買入、本根即轉紅也會被平掉。關掉 = 回到 R5 (只靠賣訊 / 可買區結束 / 收市)。", display = display.none)\n')
    s = rep(s, '''if sellSig and not eodBar and strategy.position_size > 0
    strategy.close("L", comment = sellCmt)
else if m2ExitOnEnd and m2BuyEnd and not eodBar and strategy.position_size > 0   // 整體出現了買點之後, 模式 2 可買區結束 → stop out
    strategy.close("L", comment = "M2區結束")
else if m4ExitOnEnd and m4DnStart and not eodBar and strategy.position_size > 0  // R6: 模式 4 離開可買區 (EMA9 剛轉向下) → 買點失效 → stop out
    strategy.close("L", comment = "M4區結束")
''', '''m4ExitNow = m4ExitOnEnd and useM4 and not m4Up and strategy.position_size > 0   // R7: 紅柱 (EMA9 斜率 ≤ 0) → 立即以本根收盤價平倉, 排在所有出場之前
if m4ExitNow
    strategy.close("L", comment = "M4紅柱", immediately = true)
else if sellSig and not eodBar and strategy.position_size > 0
    strategy.close("L", comment = sellCmt)
else if m2ExitOnEnd and m2BuyEnd and not eodBar and strategy.position_size > 0   // 整體出現了買點之後, 模式 2 可買區結束 → stop out
    strategy.close("L", comment = "M2區結束")
''')
    # ⑨ 掃描: 紅柱立即平倉 (本根收盤價), 取代 R6 的掛單出場
    s = rep(s, '''        posV1 = array.get(vPos, v1)
        upV   = iL == 0 ? m4UpA : iL == 1 ? m4UpB : m4UpC
        stV   = iL == 0 ? m4StA : iL == 1 ? m4StB : m4StC
        dnV   = iL == 0 ? m4DnA : iL == 1 ? m4DnB : m4DnC
''', '''        posV1 = array.get(vPos, v1)
        upV   = iL == 0 ? m4UpA : iL == 1 ? m4UpB : m4UpC
        stV   = iL == 0 ? m4StA : iL == 1 ? m4StB : m4StC
        dnV   = iL == 0 ? m4DnA : iL == 1 ? m4DnB : m4DnC
        // R7: 該組的 EMA9 本根不向上 (紅柱) → 立即以本根收盤價平倉 (與真單 immediately = true 同步; 含本根開盤才成交的倉)
        if m4ExitOnEnd and useM4 and not upV and posV1 == 1
            epR = array.get(vEntry, v1)
            xpR = close - slipTk * syminfo.mintick
            rR  = xpR / epR - 1.0 - 2.0 * commPct / 100.0
            array.set(vEq, v1, array.get(vEq, v1) * (1.0 + rR))
            array.set(vTr, v1, array.get(vTr, v1) + 1)
            if rR > 0
                array.set(vWin, v1, array.get(vWin, v1) + 1)
            array.set(vPos, v1, 0)
            array.set(vPend, v1, 0)
            posV1 := 0
''')
    s = rep(s, ' or (m4ExitOnEnd and useM4 and dnV) or eodBar or not inWindow)   // R6: 該組的 EMA9 剛轉向下也平倉\n', ' or eodBar or not inWindow)\n')
    s = rep(s, '(含 S-M4區&M2 或 ④f 選的賣法 / M2區結束 / M4區結束 / SL / EOD / 窗口結束)', '(含 M4紅柱 (R7, 本根收盤價) / S-M4區&M2 或 ④f 選的賣法 / M2區結束 / SL / EOD / 窗口結束)')
    # M4紅柱 在本根收盤成交, 但 strategy.position_size 要到下一根才歸零 → 成交標記改為本根標, 下一根不重複
    s = rep(s, 'justClosed = posSz <= 0 and posSz[1] >  0      // 賣單真正成交', 'justClosed = m4ExitNow or (posSz <= 0 and posSz[1] > 0 and not m4ExitNow[1])   // 賣單真正成交 (M4紅柱 本根收盤成交 → 標在本根; 下一根 position_size 才歸零, 不重複標)')
    s = rep(s, '" · M4 離開可買區平倉 " + (m4ExitOnEnd ? "開 (R6)" : "關")', '" · 紅柱立即平倉 " + (m4ExitOnEnd ? "開 (R7)" : "關")')
    s = rep(s, '"賣 (R6): " + (sellRuleI == 0', '"賣 (R7): 紅柱立即平倉; 其餘 " + (sellRuleI == 0')
    s = rep(s, '"===== R6 模式 2+4 回測 (RSI14 區 + EMA9, M4 離開可買區即平倉; 模式 1/3 "', '"===== R7 模式 2+4 回測 (RSI14 區 + EMA9, 紅柱立即平倉; 模式 1/3 "')
    assert 'm4DnStart and not eodBar' not in s and 'M4區結束' not in s
    return s


def apply_m4(s):
    s = rep(s, '"可賣", style = label.style_label_up', '"紅柱→平倉", style = label.style_label_up')
    s = rep(s, '② 模式 4 · EMA9 斜率為正 = 可以買入; 斜率為負 (紅柱) = 可賣區 (R3; 與主策略 ④e 一致)', '② 模式 4 · EMA9 斜率為正 = 可以買入 / 可持倉; 斜率為負 (紅柱) = 不可持倉, 立即平倉 (R7; 與主策略 ④e 一致)')
    s = rep(s, '③ 顯示: 斜率柱 (綠 = 向上可買 / 紅 = 可賣區) + 0 軸', '③ 顯示: 斜率柱 (綠 = 向上可買 / 紅 = 不可持倉, 立即平倉) + 0 軸')
    s = rep(s, 'title = "可買 / 可賣區 底色")', 'title = "可買 / 紅柱 (平倉) 底色")')
    s = rep(s, 'm4Up ? "現在向上 → 可買" : "現在向下 → 可賣區"', 'm4Up ? "現在向上 → 可買 / 可持倉" : "現在向下 → 不可持倉 (立即平倉)"')
    s = rep(s, '紅柱 (<0) = 可賣區 (R3: 要再加模式 2 賣訊才成整體賣點)', '紅柱 (≤0) = 不可持倉 (R7: 持倉中出現紅柱那一根立即以收盤價平倉)')
    return s
