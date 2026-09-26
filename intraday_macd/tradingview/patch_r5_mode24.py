# -*- coding: utf-8 -*-
"""patch_r5_mode24.py — R5: 模式 2 刪除 RSI28, 只保留 RSI14。套在 patch_r4 之後 (主策略 apply_main / RSI 副圖 apply_rsi)。

R5 模式 2 (只有 RSI14):
  進可買區 = RSI14 轉勢向上 且 谷底 ≤ 下界; 進可賣區 = RSI14 轉勢向下 且 峰頂 ≥ 上界 (R3/R4 的穿越進區、快慢線過濾、碰界回看全部隨 RSI28 移除)
  結束規則 (④c): 跌破進區谷底 [預設] / RSI14 轉勢向下 / 跌破 50 或跌破谷底 (可賣區相反)
  買 = 可買區 + 模式 4 EMA9 向上 (本根至少一個剛出現); 賣 = 模式 4 可賣區 + 模式 2 賣訊 (本根至少一個剛出現)
  ⑨ 掃描 81 組 = 下界百分位 {5,10,20} × 上界百分位 {80,90,95} × 結束規則 {3} × 模式 4 根數 {1,3,5}
"""
import re


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, n, old[:90])
    return s.replace(old, new)


def cut(s, start_marker, end_marker, new):
    i0 = s.index(start_marker)
    i1 = s.index(end_marker, i0)
    return s[:i0] + new + s[i1:]


ZONE_END = 'zoneEndMd  = input.string("RSI14 跌破進區時的谷底 (反彈失敗 = 昇不上)", "可買區何時結束 (可賣區用相反條件)", options = ["RSI14 跌破進區時的谷底 (反彈失敗 = 昇不上)", "RSI14 轉勢向下 (梯度轉負)", "RSI14 跌破 50, 或跌破進區谷底"], group = gR2, tooltip = "R5 只用 RSI14。可買區從進入那一根開始一直持續, 直到「昇不上」: 預設 = RSI14 跌破進區那一根的谷底 (反彈失敗); 另兩種: RSI14 轉勢向下 (區間最短, 一個小回落就結束), 或 RSI14 跌破 50 或跌破谷底。可賣區用相反條件 (升破峰頂 / 轉勢向上 / 升破 50 或升破峰頂)。進入另一區會直接取代現區; 區間可跨日, 預設每個交易日開始時清空。", display = display.none)\n'


def _block(with_newday):
    return ('rsiF       = ta.rsi(close, rsiFastLen)\n'
            'rsiPLo     = ta.percentile_linear_interpolation(rsiF, rsiPctLen, rsiPctLo)\n'
            'rsiPHi     = ta.percentile_linear_interpolation(rsiF, rsiPctLen, rsiPctHi)\n'
            'rsiLoBand  = rsiBandMd == "固定: 30 / 70" ? rsiFixLo : nz(rsiPLo, rsiFixLo)\n'
            'rsiHiBand  = rsiBandMd == "固定: 30 / 70" ? rsiFixHi : nz(rsiPHi, rsiFixHi)\n'
            'turnUpF    = rsiF > rsiF[1] and rsiF[1] <= rsiF[2]     // RSI14 梯度由 ≤0 轉 >0 (谷底在前一根, 本根收盤確認, 不重繪)\n'
            'turnDnF    = rsiF < rsiF[1] and rsiF[1] >= rsiF[2]     // RSI14 梯度由 ≥0 轉 <0 (峰頂在前一根)\n'
            'sinceLoF   = ta.barssince(rsiF <= rsiLoBand)           // 距上次 RSI14 到達 / 低於下界幾根\n'
            'sinceHiF   = ta.barssince(rsiF >= rsiHiBand)\n'
            'reachLoF   = nz(sinceLoF[1], 99999) < m2Reach          // 谷底那根 (或其前 m2Reach-1 根內) 曾到下界\n'
            'reachHiF   = nz(sinceHiF[1], 99999) < m2Reach\n'
            'm2BuyStart  = turnUpF and reachLoF                     // 進入可買區 (單根事件; R5 只看 RSI14: 轉勢向上且谷底到下界)\n'
            'm2SellStart = turnDnF and reachHiF                     // 進入可賣區 (單根事件)\n'
            'm2BuyOK    = true                                      // R5: 無快慢線過濾 (RSI28 已刪除)\n'
            'm2SellOK   = true\n'
            'endModeA   = zoneEndMd == "RSI14 跌破進區時的谷底 (反彈失敗 = 昇不上)"\n'
            'endModeB   = zoneEndMd == "RSI14 轉勢向下 (梯度轉負)"\n'
            'var int   m2State  = 0                                 // 1 = 可買區, -1 = 可賣區, 0 = 無\n'
            'var float m2Trough = na                                // 進入可買區那一根的谷底 (RSI14 值)\n'
            'var float m2Peak   = na                                // 進入可賣區那一根的峰頂\n'
            'buyEndRaw  = endModeA ? rsiF < m2Trough : endModeB ? turnDnF : (rsiF < 50 or rsiF < m2Trough)   // 「昇不上」\n'
            'sellEndRaw = endModeA ? rsiF > m2Peak   : endModeB ? turnUpF : (rsiF > 50 or rsiF > m2Peak)     // 相反: 「跌不下」\n'
            + ('newDay     = dayofmonth != dayofmonth[1]\n' if with_newday else '') +
            'if m2ResetDay and newDay\n'
            '    m2State := 0\n'
            'm2Prev     = m2State\n'
            'if m2BuyStart                                          // 進入新區優先於現區結束\n'
            '    m2State  := 1\n'
            '    m2Trough := rsiF[1]\n'
            'else if m2SellStart\n'
            '    m2State := -1\n'
            '    m2Peak  := rsiF[1]\n'
            'else if m2State == 1 and buyEndRaw\n'
            '    m2State := 0\n'
            'else if m2State == -1 and sellEndRaw\n'
            '    m2State := 0\n'
            'm2InBuy    = m2State == 1                              // 模式 2 的輸出只有兩種狀態: 可買區 / 可賣區\n'
            'm2InSell   = m2State == -1\n'
            'm2BuyEnd   = m2Prev == 1 and not m2InBuy               // 可買區結束 (含直接轉入可賣區) → 持倉要平\n'
            'm2SellEnd  = m2Prev == -1 and not m2InSell\n'
            'm2BuyRaw   = turnUpF                                   // 未到界的轉勢 (只用來計數比較)\n'
            'm2SellRaw  = turnDnF\n'
            'm2Zone     = m2InBuy ? "可買區" : m2InSell ? "可賣區" : "無"\n')


def _common(s, with_newday):
    s = re.sub(r'^rsiSlowLen = input\.int\(28,.*\n', '', s, count=1, flags=re.M)
    s = re.sub(r'^m2EntryMd  = input\.string\(.*\n', '', s, count=1, flags=re.M)
    s = re.sub(r'^m2SwingLen = input\.int\(10,.*\n', '', s, count=1, flags=re.M)
    s = re.sub(r'^m2TouchLook = input\.int\(20,.*\n', '', s, count=1, flags=re.M)
    s = re.sub(r'^m2FastAbove = input\.bool\(true,.*\n', '', s, count=1, flags=re.M)
    s = re.sub(r'^zoneEndMd  = input\.string\(.*\n', ZONE_END, s, count=1, flags=re.M)
    s = rep(s, 'rsiFastLen = input.int(14, "RSI 快線長度 (轉勢與到界都看它)"', 'rsiFastLen = input.int(14, "RSI 長度 (R5 只用這一條 RSI14; RSI28 已刪除)"')
    s = s.replace('模式 2 · RSI 14/28 可買區 / 可賣區 (與主策略 ④c 保持一致)', '模式 2 · RSI 14 可買區 / 可賣區 (與主策略 ④c 保持一致)')
    # 整段狀態機重寫
    i0 = s.index('rsiF       = ta.rsi(close, rsiFastLen)\n')
    i1 = s.index('\n', s.index('m2Zone     = ', i0)) + 1
    s = s[:i0] + _block(with_newday) + s[i1:]
    return s


def apply_main(s):
    s = _common(s, False)
    s = rep(s, 'gR2        = "④c 模式 2 · RSI 14/28 可買區 / 可賣區 (狀態)"', 'gR2        = "④c 模式 2 · RSI 14 可買區 / 可賣區 (狀態; R5 只用 RSI14)"')
    s = rep(s, ' or m2BuyStart or (m2FastAbove and xFSup)   // R3: RSI14 剛升穿 RSI28 也算剛出現;', ' or m2BuyStart   //')
    s = rep(s, '(m2SellStart or m4DnStart or (m2FastAbove and xFSdn))', '(m2SellStart or m4DnStart)')
    # ⑨ 掃描: 27 個狀態機 = 下界 {5,10,20} × 上界 {80,90,95} × 結束規則
    s = cut(s, 'zLo0 = nz(', '// ── 模式 4 的 3 種斜率根數', '''zLo0 = nz(ta.percentile_linear_interpolation(rsiF, rsiPctLen, 5.0), rsiFixLo)
zLo1 = nz(ta.percentile_linear_interpolation(rsiF, rsiPctLen, 10.0), rsiFixLo)
zLo2 = nz(ta.percentile_linear_interpolation(rsiF, rsiPctLen, 20.0), rsiFixLo)
zHi0 = nz(ta.percentile_linear_interpolation(rsiF, rsiPctLen, 80.0), rsiFixHi)
zHi1 = nz(ta.percentile_linear_interpolation(rsiF, rsiPctLen, 90.0), rsiFixHi)
zHi2 = nz(ta.percentile_linear_interpolation(rsiF, rsiPctLen, 95.0), rsiFixHi)
zReachLo0 = nz(ta.barssince(rsiF <= zLo0)[1], 99999) < m2Reach
zReachLo1 = nz(ta.barssince(rsiF <= zLo1)[1], 99999) < m2Reach
zReachLo2 = nz(ta.barssince(rsiF <= zLo2)[1], 99999) < m2Reach
zReachHi0 = nz(ta.barssince(rsiF >= zHi0)[1], 99999) < m2Reach
zReachHi1 = nz(ta.barssince(rsiF >= zHi1)[1], 99999) < m2Reach
zReachHi2 = nz(ta.barssince(rsiF >= zHi2)[1], 99999) < m2Reach
var int[]   zState  = array.new_int(NZ, 0)
var float[] zTrough = array.new_float(NZ, na)
var float[] zPeak   = array.new_float(NZ, na)
var bool[]  zInBuy  = array.new_bool(NZ, false)
var bool[]  zInSell = array.new_bool(NZ, false)
var bool[]  zBStart = array.new_bool(NZ, false)
var bool[]  zSStart = array.new_bool(NZ, false)
var bool[]  zBEnd   = array.new_bool(NZ, false)
for z = 0 to NZ - 1
    iPz = math.floor(z / 9)                            // 下界百分位 5 / 10 / 20
    iHz = math.floor(z / 3) % 3                        // 上界百分位 80 / 90 / 95
    iEz = z % 3                                        // 結束規則
    rLo = iPz == 0 ? zReachLo0 : iPz == 1 ? zReachLo1 : zReachLo2
    rHi = iHz == 0 ? zReachHi0 : iHz == 1 ? zReachHi1 : zReachHi2
    bSt = turnUpF and rLo
    sSt = turnDnF and rHi
    st  = array.get(zState, z)
    if m2ResetDay and newDay
        st := 0
    prevZ = st
    trZ = array.get(zTrough, z)
    pkZ = array.get(zPeak, z)
    bEndZ = iEz == 0 ? rsiF < trZ : iEz == 1 ? turnDnF : (rsiF < 50 or rsiF < trZ)
    sEndZ = iEz == 0 ? rsiF > pkZ : iEz == 1 ? turnUpF : (rsiF > 50 or rsiF > pkZ)
    if bSt
        st  := 1
        trZ := rsiF[1]
    else if sSt
        st  := -1
        pkZ := rsiF[1]
    else if st == 1 and bEndZ
        st := 0
    else if st == -1 and sEndZ
        st := 0
    array.set(zState, z, st)
    array.set(zTrough, z, trZ)
    array.set(zPeak, z, pkZ)
    array.set(zInBuy, z, st == 1)
    array.set(zInSell, z, st == -1)
    array.set(zBStart, z, bSt)
    array.set(zSStart, z, sSt)
    array.set(zBEnd, z, prevZ == 1 and st != 1)
''')
    s = rep(s, 'int NV = 81                                          // 3(進區方式) × 3(下界百分位) × 3(結束規則) × 3(M4 根數); 賣法 / 快慢線過濾用 ④f / ④c 現值\nint NZ = 27                                          // 模式 2 區間狀態機: 3 種進區方式 × 3 個下界百分位 × 3 種結束規則\n',
               'int NV = 81                                          // 3(下界百分位) × 3(上界百分位) × 3(結束規則) × 3(M4 根數); 賣法用 ④f 現值\nint NZ = 27                                          // 模式 2 區間狀態機: 3 個下界 × 3 個上界 × 3 種結束規則\n')
    s = rep(s, '''        iN   = math.floor(v1 / 27)                 // Pine 的 / 永遠回傳 float, 不截斷 → 一定要 floor
        iP   = math.floor(v1 / 9) % 3
        iE   = math.floor(v1 / 3) % 3
        iL   = v1 % 3
        zi   = iN * 9 + iP * 3 + iE
''', '''        iP   = math.floor(v1 / 27)                 // Pine 的 / 永遠回傳 float, 不截斷 → 一定要 floor
        iH   = math.floor(v1 / 9) % 3
        iE   = math.floor(v1 / 3) % 3
        iL   = v1 % 3
        zi   = iP * 9 + iH * 3 + iE
''')
    s = rep(s, '''        bSig  = inB and m2BuyOK and m13OK and (not useM4 or upV) and (bSt2 or m13Evt or (useM4 and stV) or (m2FastAbove and xFSup))
        sSig  = sellRuleI == 0 ? (inS and m2SellOK and (not useM4 or not upV) and (sSt2 or (useM4 and dnV) or (m2FastAbove and xFSdn))) : sellRuleI == 1 ? (sSt2 and m2SellOK) : false''',
               '''        bSig  = inB and m13OK and (not useM4 or upV) and (bSt2 or m13Evt or (useM4 and stV))
        sSig  = sellRuleI == 0 ? (inS and (not useM4 or not upV) and (sSt2 or (useM4 and dnV))) : sellRuleI == 1 ? sSt2 : false''')
    s = cut(s, 'liveIp = rsiBandMd', '\n// ─────────────────────────── ⑩ 成交偵測', '''liveIp = rsiBandMd == "固定: 30 / 70" ? -1 : math.abs(rsiPctLo - 5) < 0.01 ? 0 : math.abs(rsiPctLo - 10) < 0.01 ? 1 : math.abs(rsiPctLo - 20) < 0.01 ? 2 : -1
liveIh = rsiBandMd == "固定: 30 / 70" ? -1 : math.abs(rsiPctHi - 80) < 0.01 ? 0 : math.abs(rsiPctHi - 90) < 0.01 ? 1 : math.abs(rsiPctHi - 95) < 0.01 ? 2 : -1
liveIe = endModeA ? 0 : endModeB ? 1 : 2
liveIl = m4Look == 1 ? 0 : m4Look == 3 ? 1 : m4Look == 5 ? 2 : -1
liveV  = (liveIp >= 0 and liveIh >= 0 and liveIl >= 0) ? liveIp * 27 + liveIh * 9 + liveIe * 3 + liveIl : -1
''')
    s = rep(s, '''        iN2  = math.floor(vv / 27)
        iP2  = math.floor(vv / 9) % 3
        iE2  = math.floor(vv / 3) % 3
        iL2  = vv % 3
        pTxt = (iN2 == 0 ? "轉勢 " : iN2 == 1 ? "穿越 " : "任一 ") + (iP2 == 0 ? "P5" : iP2 == 1 ? "P10" : "P20")
        eTxt = iE2 == 0 ? "破慢線/谷底" : iE2 == 1 ? "14轉下" : "28轉下"
''', '''        iP2  = math.floor(vv / 27)
        iH2  = math.floor(vv / 9) % 3
        iE2  = math.floor(vv / 3) % 3
        iL2  = vv % 3
        pTxt = (iP2 == 0 ? "P5" : iP2 == 1 ? "P10" : "P20") + "/" + (iH2 == 0 ? "P80" : iH2 == 1 ? "P90" : "P95")
        eTxt = iE2 == 0 ? "破谷底" : iE2 == 1 ? "轉下" : "破50/谷底"
''')
    s = rep(s, '    table.cell(rpt, 8, 1, "M2 進區/下界P", text_size = sizeV, bgcolor = sBg)\n', '    table.cell(rpt, 8, 1, "M2 下界P/上界P", text_size = sizeV, bgcolor = sBg)\n')
    s = rep(s, '"掃描 81 組 (R4: M2 進區方式×下界P×結束規則 × M4 根數; 進區前 " + str.tostring(m2TouchLook) + " 根內要碰過界) · 最大昇幅 "', '"掃描 81 組 (R5: M2 下界P×上界P×結束規則 × M4 根數; 只用 RSI14) · 最大昇幅 "')
    s = rep(s, '"現行 M2 " + (liveIn == 0 ? "轉勢 " : liveIn == 1 ? "穿越 " : "任一 ") + (rsiBandMd', '"現行 M2 RSI14 " + (rsiBandMd')
    s = rep(s, '" " + (endModeA ? "破慢線/谷底" : endModeB ? "14轉下" : "28轉下") + " · M4 " + str.tostring(m4Look) + " 根 · 賣 " + sellCmt + (m2FastAbove ? " · 快>慢過濾" : "")', '" " + (endModeA ? "破谷底" : endModeB ? "轉下" : "破50/谷底") + " · M4 " + str.tostring(m4Look) + " 根 · 賣 " + sellCmt')
    s = rep(s, '"不在網格 (P∈5/10/20 · M4∈1/3/5)"', '"不在網格 (下界P∈5/10/20 · 上界P∈80/90/95 · M4∈1/3/5)"')
    s = rep(s, '"R4 M2 碰界" + str.tostring(m2TouchLook) + " " + (liveIn == 0 ? "轉勢 " : liveIn == 1 ? "穿越 " : "任一 ") + (rsiBandMd', '"R5 M2 RSI14 " + (rsiBandMd')
    s = rep(s, '" " + (endModeA ? "破慢線/谷底" : endModeB ? "14轉下" : "28轉下") + " · M4 " + str.tostring(m4Look) + " 根 · 賣 " + sellCmt + (useM1 ?', '" " + (endModeA ? "破谷底" : endModeB ? "轉下" : "破50/谷底") + " · M4 " + str.tostring(m4Look) + " 根 · 賣 " + sellCmt + (useM1 ?')
    s = rep(s, '"模式 2 · RSI " + str.tostring(rsiFastLen) + "/" + str.tostring(rsiSlowLen) + " 區"', '"模式 2 · RSI " + str.tostring(rsiFastLen) + " 區 (R5 只用 RSI14)"')
    s = rep(s, '"RSI" + str.tostring(rsiFastLen) + " " + str.tostring(rsiF, "#.#") + " / RSI" + str.tostring(rsiSlowLen) + " " + str.tostring(rsiS, "#.#") + " · 下界 "', '"RSI" + str.tostring(rsiFastLen) + " " + str.tostring(rsiF, "#.#") + " · 下界 "')
    s = rep(s, '"買 (R4): M2 可買區 (碰過下界)" + (m2FastAbove ? " (RSI14>RSI28)" : "") + " + M4 向上"', '"買 (R5): M2 可買區 (RSI14 到下界後轉勢) + M4 向上"')
    s = rep(s, '"R2 要更嚴 (少而準): M2 下界百分位↓ 上界百分位↑ · M2 結束規則改「破慢線/谷底」 · M4 斜率根數↑ · ④f 賣法改 M4區&M2 同時 · ④c 進區方式改「轉勢且到界」 · 開快慢線過濾; 要更鬆: 反之 (進區方式改「任一」) (M1 門檻 / 匹配窗口只在 ④f 加回模式 1/3 時有效)"', '"R5 要更嚴 (少而準): M2 下界百分位↓ 上界百分位↑ · M2 結束規則改「破谷底」 · M4 斜率根數↑ · ④f 賣法改 M4區&M2 同時; 要更鬆: 反之 (結束規則改「破50/谷底」) (M1 門檻 / 匹配窗口只在 ④f 加回模式 1/3 時有效)"')
    s = rep(s, '"期內無交易 — 檢查 ⑤ 時段 / margin_long = 0 / ④c 可買區規則 (進區方式、下界百分位、結束規則、快慢線過濾) / ④e 模式 4"', '"期內無交易 — 檢查 ⑤ 時段 / margin_long = 0 / ④c 可買區規則 (下界百分位、結束規則) / ④e 模式 4"')
    s = rep(s, '"===== R4 模式 2+4 回測 (RSI區 碰界後 " + m2EntryMd + "; EMA9; 模式 1/3 "', '"===== R5 模式 2+4 回測 (RSI14 區 + EMA9; 模式 1/3 "')
    s = rep(s, '對 81 組「模式 2 進區方式∈{轉勢且到界, 穿越, 任一} × 下界百分位∈{5,10,20} (上界 = 100 − 下界) × 可買區結束規則∈{跌破慢線或谷底, RSI14 轉勢向下, RSI28 轉勢向下} × 模式 4 斜率根數∈{1,3,5}」各跑一套虛擬回測 (每組都是 R3 規則: 買 = 該組的可買區 + 該組的 EMA9 向上 + ④c 快慢線過濾 且本根至少一個剛出現;', '對 81 組「模式 2 下界百分位∈{5,10,20} × 上界百分位∈{80,90,95} × 可買區結束規則∈{跌破谷底, RSI14 轉勢向下, 跌破 50 或谷底} × 模式 4 斜率根數∈{1,3,5}」各跑一套虛擬回測 (每組都是 R5 規則: 買 = 該組的可買區 (RSI14 到下界後轉勢) + 該組的 EMA9 向上 且本根至少一個剛出現;')
    s = rep(s, '橙底列 = 現行 ④c / ④e 的組合 (④c 用固定 30/70 或百分位不在網格時顯示「不在網格」)。', '橙底列 = 現行 ④c / ④e 的組合 (④c 用固定 30/70 或百分位不在網格時顯示「不在網格」)。R5 只用 RSI14。')
    s = rep(s, '結束規則改 RSI28 轉下', '結束規則改 破50/谷底')
    s = rep(s, '模式2 RSI14/28 可買區', '模式2 RSI14 可買區')
    s = rep(s, 'gSW       = "⑨ 參數掃描 (R3: 模式 2 進區方式 × 下界 × 結束規則 × 模式 4 根數)"', 'gSW       = "⑨ 參數掃描 (R5: 模式 2 下界P × 上界P × 結束規則 × 模式 4 根數)"')
    s = rep(s, 'and m2InBuy and m2BuyOK   // R3: 加 RSI14 > RSI28 過濾; R2:', 'and m2InBuy and m2BuyOK   // R5: m2BuyOK 恆真 (無 RSI28); R2:')
    for bad in ('xFSup', 'xFSdn', 'm2FastAbove', 'm2TouchLook', 'm2EntryMd', 'liveIn', 'swingLo', 'turnUpS', 'zTouch', 'iN2', 'rsiSlowLen', 'rsiS ', 'rsiS,', 'rsiS)'):
        assert bad not in s, bad
    return s


def apply_rsi(s):
    s = _common(s, True)
    s = re.sub(r'^showX      = input\.bool\(true,.*\n', '', s, count=1, flags=re.M)
    s = re.sub(r'^cSlow      = color\.rgb\(200, 120, 0\).*\n', '', s, count=1, flags=re.M)
    s = re.sub(r'^plot\(rsiS, "RSI28 \(慢\)".*\n', '', s, count=1, flags=re.M)
    s = rep(s, 'color = m2BuyOK ? cBuyTri : color.new(cBuyTri, 60),  size = size.small', 'color = cBuyTri,  size = size.small')
    s = rep(s, 'color = m2SellOK ? cSellTri : color.new(cSellTri, 60), size = size.small', 'color = cSellTri, size = size.small')
    s = cut(s, '// RSI14 / RSI28 交叉: 小圓點', '\n// 淺灰幼直線', '')
    s = rep(s, 'var float yS = na\n', '')
    s = rep(s, '    yF := rsiF\n    yS := rsiS\n', '    yF := rsiF\n')
    s = rep(s, 'var label lbS = na\n', '')
    s = rep(s, '    label.delete(lbF)\n    label.delete(lbS)\n', '    label.delete(lbF)\n')
    s = re.sub(r'^    lbS := label\.new\(.*\n', '', s, count=1, flags=re.M)
    s = rep(s, 'var int nXup = 0\nvar int nXdn = 0\n', '')
    s = rep(s, '    nXup += xFSup ? 1 : 0\n    nXdn += xFSdn ? 1 : 0\n', '')
    s = rep(s, '"模式 2 · RSI " + str.tostring(rsiFastLen) + "/" + str.tostring(rsiSlowLen) + " 可買區 / 可賣區"', '"模式 2 · RSI " + str.tostring(rsiFastLen) + " 可買區 / 可賣區 (R5 只用 RSI14)"')
    s = rep(s, '    table.cell(tb, 0, 1, "RSI14 / RSI28", text_size = size.tiny, bgcolor = hBg)\n', '    table.cell(tb, 0, 1, "RSI14", text_size = size.tiny, bgcolor = hBg)\n')
    s = rep(s, '    table.cell(tb, 1, 1, str.tostring(rsiF, "#.#") + " / " + str.tostring(rsiS, "#.#") + (rsiF > rsiS ? "  快>慢" : rsiF < rsiS ? "  快<慢" : "  快=慢"), text_size = size.tiny)\n', '    table.cell(tb, 1, 1, str.tostring(rsiF, "#.#"), text_size = size.tiny)\n')
    s = rep(s, '    table.cell(tb, 0, 6, "快慢線交叉 升穿 / 跌破 · 區間結束規則", text_size = size.tiny, bgcolor = hBg)\n', '    table.cell(tb, 0, 6, "區間結束規則", text_size = size.tiny, bgcolor = hBg)\n')
    s = re.sub(r'^    table\.cell\(tb, 1, 6, str\.tostring\(nXup\).*$', '    table.cell(tb, 1, 6, endModeA ? "跌破進區谷底" : endModeB ? "RSI14 轉勢向下" : "跌破 50 或谷底", text_size = size.tiny)', s, count=1, flags=re.M)   # 這是本體最後一行, 沒有換行
    s = rep(s, 'plot(rsiF, "RSI14 (快)"', 'plot(rsiF, "RSI14"')
    s = rep(s, '"模式2 · RSI" + str.tostring(rsiFastLen) + " ▲進可買區=到下界後轉勢向上 ▼進可賣區=到上界後轉勢向下 · 底色=區間"', '"模式2 · RSI" + str.tostring(rsiFastLen) + " (R5 只用這一條) ▲進可買區=到下界後轉勢向上 ▼進可賣區=到上界後轉勢向下 · 底色=區間"')
    for bad in ('rsiS ', 'rsiS)', 'rsiS,', 'xFSup', 'xFSdn', 'm2FastAbove', 'm2TouchLook', 'm2EntryMd', 'swingLo', 'turnUpS', 'nXup', 'lbS', 'cSlow', 'showX'):
        assert bad not in s, bad
    return s
