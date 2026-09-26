# -*- coding: utf-8 -*-
"""patch_r6_mode24.py — R6: 模式 4 離開可買區 (EMA9 斜率轉負) → 其它模式的買點失效 → 持倉即平倉 (M4區結束)。套在 patch_r5 之後 (主策略)。
④e 新增 m4ExitOnEnd (預設開): 持倉中 EMA9 剛轉向下那一根收盤掛單平倉, 出場原因 M4區結束; 與 M2區結束 (可買區結束) 並列, 排在賣訊之後、固定止損之前。掃描 81 組同步。
"""


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, n, old[:90])
    return s.replace(old, new)


def apply_main(s):
    s = rep(s, 'useM4    = input.bool(true, "啟用模式 4 (關掉 = 只剩模式 2 決定買賣; 加回 ④f 的模式 1 / 3 時才是三模式)", group = gR4, display = display.none)\n',
               'useM4    = input.bool(true, "啟用模式 4 (關掉 = 只剩模式 2 決定買賣; 加回 ④f 的模式 1 / 3 時才是三模式)", group = gR4, display = display.none)\n'
               'm4ExitOnEnd = input.bool(true, "R6: 持倉中模式 4 離開可買區 (EMA9 剛轉向下) → 其它模式的買點失效 → 立即平倉 (M4區結束)", group = gR4, tooltip = "模式 4 是買入的閘門: EMA9 向上才可買。R6: 一旦 EMA9 轉向下 (斜率轉負, 副圖轉紅柱), 買入條件已不成立, 持倉不再等模式 2 賣訊, 直接平倉。與 ④c 的「可買區結束平倉」並列, 排在賣訊之後、固定止損之前。關掉 = 回到 R5 (只靠賣訊 / 可買區結束 / 收市)。", display = display.none)\n')
    s = rep(s, 'else if m2ExitOnEnd and m2BuyEnd and not eodBar and strategy.position_size > 0   // 整體出現了買點之後, 模式 2 可買區結束 → stop out\n    strategy.close("L", comment = "M2區結束")\n',
               'else if m2ExitOnEnd and m2BuyEnd and not eodBar and strategy.position_size > 0   // 整體出現了買點之後, 模式 2 可買區結束 → stop out\n    strategy.close("L", comment = "M2區結束")\n'
               'else if m4ExitOnEnd and m4DnStart and not eodBar and strategy.position_size > 0  // R6: 模式 4 離開可買區 (EMA9 剛轉向下) → 買點失效 → stop out\n    strategy.close("L", comment = "M4區結束")\n')
    s = rep(s, '        else if posV1 == 1 and (sSig or (m2ExitOnEnd and array.get(zBEnd, zi)) or eodBar or not inWindow)\n',
               '        else if posV1 == 1 and (sSig or (m2ExitOnEnd and array.get(zBEnd, zi)) or (m4ExitOnEnd and useM4 and dnV) or eodBar or not inWindow)   // R6: 該組的 EMA9 剛轉向下也平倉\n')
    s = rep(s, '(含 S-M4區&M2 或 ④f 選的賣法 / M2區結束 / SL / EOD / 窗口結束)', '(含 S-M4區&M2 或 ④f 選的賣法 / M2區結束 / M4區結束 / SL / EOD / 窗口結束)')
    s = rep(s, ') · 可買區結束平倉 " + (m2ExitOnEnd ? "開" : "關")', ') · 可買區結束平倉 " + (m2ExitOnEnd ? "開" : "關") + " · M4 離開可買區平倉 " + (m4ExitOnEnd ? "開 (R6)" : "關")')
    s = rep(s, '"賣 (R2): " + (sellRuleI == 0', '"賣 (R6): " + (sellRuleI == 0')
    s = rep(s, '"===== R5 模式 2+4 回測 (RSI14 區 + EMA9; 模式 1/3 "', '"===== R6 模式 2+4 回測 (RSI14 區 + EMA9, M4 離開可買區即平倉; 模式 1/3 "')
    return s
