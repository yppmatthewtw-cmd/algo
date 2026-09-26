# -*- coding: utf-8 -*-
"""patch_r4_mode24.py — R4: 模式 2 進區必須「碰過界」。
套在 patch_r3 之後 (主策略 apply_main / RSI 副圖 apply_rsi)。

R4 規則: 進可買區那一根之前 N 根內 (m2TouchLook, 預設 20) RSI14 必須碰過 (≤) 下界 (綠區), 否則不算模式 2 買點 (刪除);
        進可賣區之前 N 根內 RSI14 必須碰過 (≥) 上界 (紅區), 否則不算模式 2 賣點。
        「轉勢且到界」本來就要求谷底 / 峰頂在界外; 「RSI14 穿越 RSI28」進區 (R3 加入) 現在也要先碰過界才算。
"""


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, n, old[:90])
    return s.replace(old, new)


TOUCH_INPUT = 'm2TouchLook = input.int(20, "R4: 進區前 N 根內 RSI14 必須碰過下界 (可買區) / 上界 (可賣區), 否則不算模式 2 買 / 賣點", minval = 1, maxval = 200, group = gR2, tooltip = "R4: 沒有碰到下界 (綠區) 的可買區進入點一律刪除, 沒有碰到上界 (紅區) 的可賣區進入點一律刪除。轉勢進區本來就要求谷底 / 峰頂在界外; RSI14 升穿 / 跌破 RSI28 的進區也要在之前 N 根內碰過界才算。N 越小越嚴。", display = display.none)\n'


def _zone(s, main):
    s = rep(s, 'm2FastAbove = input.bool(', TOUCH_INPUT + 'm2FastAbove = input.bool(')
    s = rep(s, 'reachHiF   = nz(sinceHiF[1], 99999) < m2Reach\n', 'reachHiF   = nz(sinceHiF[1], 99999) < m2Reach\ntouchLoF   = nz(sinceLoF[1], 99999) < m2TouchLook     // R4: 之前 N 根內碰過下界 (綠區)\ntouchHiF   = nz(sinceHiF[1], 99999) < m2TouchLook     // R4: 之前 N 根內碰過上界 (紅區)\n')
    s = rep(s, 'm2BuyStart  = m2BuyTurn or (entCross and xFSup)', 'm2BuyStart  = m2BuyTurn or (entCross and xFSup and touchLoF)')
    s = rep(s, 'm2SellStart = m2SellTurn or (entCross and xFSdn)', 'm2SellStart = m2SellTurn or (entCross and xFSdn and touchHiF)')
    return s


def apply_main(s):
    s = _zone(s, True)
    s = rep(s, '''zReachLo0 = nz(ta.barssince(rsiF <= zLo0)[1], 99999) < m2Reach
zReachHi0 = nz(ta.barssince(rsiF >= zHi0)[1], 99999) < m2Reach
zReachLo1 = nz(ta.barssince(rsiF <= zLo1)[1], 99999) < m2Reach
zReachHi1 = nz(ta.barssince(rsiF >= zHi1)[1], 99999) < m2Reach
zReachLo2 = nz(ta.barssince(rsiF <= zLo2)[1], 99999) < m2Reach
zReachHi2 = nz(ta.barssince(rsiF >= zHi2)[1], 99999) < m2Reach
''', '''zSLo0 = nz(ta.barssince(rsiF <= zLo0)[1], 99999)
zSHi0 = nz(ta.barssince(rsiF >= zHi0)[1], 99999)
zSLo1 = nz(ta.barssince(rsiF <= zLo1)[1], 99999)
zSHi1 = nz(ta.barssince(rsiF >= zHi1)[1], 99999)
zSLo2 = nz(ta.barssince(rsiF <= zLo2)[1], 99999)
zSHi2 = nz(ta.barssince(rsiF >= zHi2)[1], 99999)
zReachLo0 = zSLo0 < m2Reach
zReachHi0 = zSHi0 < m2Reach
zReachLo1 = zSLo1 < m2Reach
zReachHi1 = zSHi1 < m2Reach
zReachLo2 = zSLo2 < m2Reach
zReachHi2 = zSHi2 < m2Reach
zTouchLo0 = zSLo0 < m2TouchLook                       // R4: 穿越進區也要先碰過界
zTouchHi0 = zSHi0 < m2TouchLook
zTouchLo1 = zSLo1 < m2TouchLook
zTouchHi1 = zSHi1 < m2TouchLook
zTouchLo2 = zSLo2 < m2TouchLook
zTouchHi2 = zSHi2 < m2TouchLook
''')
    s = rep(s, '''    rHi = iPz == 0 ? zReachHi0 : iPz == 1 ? zReachHi1 : zReachHi2
    bTn = iNz != 1 and turnUpF and rLo
    sTn = iNz != 1 and turnDnF and rHi
    bSt = bTn or (iNz != 0 and xFSup)
    sSt = sTn or (iNz != 0 and xFSdn)
''', '''    rHi = iPz == 0 ? zReachHi0 : iPz == 1 ? zReachHi1 : zReachHi2
    tLo = iPz == 0 ? zTouchLo0 : iPz == 1 ? zTouchLo1 : zTouchLo2
    tHi = iPz == 0 ? zTouchHi0 : iPz == 1 ? zTouchHi1 : zTouchHi2
    bTn = iNz != 1 and turnUpF and rLo
    sTn = iNz != 1 and turnDnF and rHi
    bSt = bTn or (iNz != 0 and xFSup and tLo)
    sSt = sTn or (iNz != 0 and xFSdn and tHi)
''')
    s = rep(s, '"===== R3 模式 2+4 回測 (RSI區 "', '"===== R4 模式 2+4 回測 (RSI區 碰界後 "')
    s = rep(s, '"買 (R3): M2 可買區"', '"買 (R4): M2 可買區 (碰過下界)"')
    s = rep(s, '"R3 M2 " + (liveIn == 0', '"R4 M2 碰界" + str.tostring(m2TouchLook) + " " + (liveIn == 0')
    s = rep(s, '(R3: M2 進區方式×下界P×結束規則 × M4 根數)', '(R4: M2 進區方式×下界P×結束規則 × M4 根數; 進區前 ' + '" + str.tostring(m2TouchLook) + "' + ' 根內要碰過界)')
    return s


def apply_rsi(s):
    return _zone(s, False)
