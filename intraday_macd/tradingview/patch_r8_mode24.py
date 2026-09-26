# -*- coding: utf-8 -*-
"""patch_r8_mode24.py — R8: 刪除模式 1 / 模式 3 (不再參與任何買賣決定, 預設也不顯示); 明確只做多。套在 patch_r7 之後 (主策略)。
  ④f 的「加回模式 1 / 3」開關刪除 (程式內固定 false); 賣法選項刪除「舊規則 (模式 1 賣訊)」
  模式 1 的上下界線 / ▲▼ / 直線、模式 3 的 DIF/DEA 線 / 金叉死叉標記 預設全部關閉 (④ / ④d 仍可打開純對照, 不影響買賣)
  買 = 模式 2 可買區 + 模式 4 綠柱; 賣 = R7 紅柱立即平倉 / 可買區結束 / 收市; 只做多, 沒有任何 strategy.short
"""


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, n, old[:90])
    return s.replace(old, new)


def apply_main(s):
    s = rep(s, 'gRF       = "④f R2 · 只用模式 2 + 4 決定買賣 (模式 1 / 3 預設關閉)"\n', 'gRF       = "④f R8 · 只用模式 2 + 4 決定買賣 (模式 1 / 3 已刪除, 不參與; 只做多)"\n')
    s = rep(s, 'useM1     = input.bool(false, "買入條件加回模式 1 (柱到界後淺紅 N 根, 5 根內有效) — R2 預設關", group = gRF, display = display.none)\n', 'useM1     = false     // R8: 模式 1 已刪除, 永不參與買賣 (保留變數只為下游程式碼)\n')
    s = rep(s, 'useM3     = input.bool(false, "買入條件加回模式 3 (9/26/9 金叉, 5 根內有效) — R2 預設關", group = gRF, display = display.none)\n', 'useM3     = false     // R8: 模式 3 已刪除, 永不參與買賣\n')
    s = rep(s, ', "舊規則: 模式 1 賣訊在可賣區 (不需開啟 ④f 模式 1; 該開關只影響買入)"]', ']')
    s = rep(s, '"賣: 模式 1 賣訊的有效根數 (只在 ④f 選「舊規則」時用)"', '"賣: 模式 1 賣訊的有效根數 (R8: 模式 1 已刪除, 此值不用)"')
    s = rep(s, 'gTH        = "④ 模式 1 · MACD 柱上下界 (跌到下界 / 昇到上界 才有訊號)"', 'gTH        = "④ 模式 1 · MACD 柱上下界 (R8: 已刪除, 不參與買賣; 以下只是純對照顯示, 預設關)"')
    s = rep(s, 'showBand1  = input.bool(true, "副圖畫出模式 1 的上界 (紅線) / 下界 (藍線)"', 'showBand1  = input.bool(false, "副圖畫出模式 1 的上界 (紅線) / 下界 (藍線) (R8 純對照, 預設關)"')
    s = rep(s, 'gR3        = "④d 模式 3 · 敏感 MACD (9/26/9) 金叉 (R2 預設不參與; ④f 開啟後只參與買入)"', 'gR3        = "④d 模式 3 · 敏感 MACD (9/26/9) 金叉 (R8: 已刪除, 不參與買賣; 以下只是純對照顯示, 預設關)"')
    s = rep(s, 'showM3     = input.bool(true, "副圖畫出模式 3 的 DIF (橙, 粗) / DEA (青, 細)"', 'showM3     = input.bool(false, "副圖畫出模式 3 的 DIF (橙, 粗) / DEA (青, 細) 與金叉死叉標記 (R8 純對照, 預設關)"')
    s = rep(s, 'showLanes = input.bool(true, "模式 1 訊號標在 MACD 柱上', 'showLanes = input.bool(false, "(R8 純對照, 預設關) 模式 1 訊號標在 MACD 柱上')
    s = rep(s, 'if showVL and inWindow and (m1Buy or m2BuyStart or m3Buy)\n', 'if showVL and inWindow and (m2BuyStart or (showLanes and m1Buy) or (showM3 and m3Buy))   // R8: 模式 1 / 3 的直線只在對照顯示打開時畫\n')
    s = rep(s, 'if showVL and inWindow and (m1Sell or m2SellStart or m3SellSolo)\n', 'if showVL and inWindow and (m2SellStart or (showLanes and m1Sell) or (showM3 and m3SellSolo))\n')
    s = rep(s, '"===== R7 模式 2+4 回測 (RSI14 區 + EMA9, 紅柱立即平倉; 模式 1/3 " + (useM1 or useM3 ? "部分加回" : "關閉") + ")', '"===== R8 只做多 · 模式 2+4 回測 (RSI14 區 + EMA9, 紅柱立即平倉; 模式 1/3 已刪除)')
    s = rep(s, '"買 (R5): M2 可買區 (RSI14 到下界後轉勢) + M4 向上"', '"買 (R8, 只做多): M2 可買區 (RSI14 到下界後轉勢) + M4 綠柱"')
    s = rep(s, '"賣 (R7): 紅柱立即平倉; 其餘 " + (sellRuleI == 0', '"賣 (R8): 紅柱立即平倉; 其餘 " + (sellRuleI == 0')
    assert 'input.bool(false, "買入條件加回' not in s
    return s
