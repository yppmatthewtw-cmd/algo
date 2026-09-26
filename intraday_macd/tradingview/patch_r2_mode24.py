# -*- coding: utf-8 -*-
"""patch_r2_mode24.py — R2 變體: 關閉模式 1 / 3, 只用模式 2 (RSI 14/28 可買區 / 可賣區) + 模式 4 (EMA9 斜率) 形成整體買賣決定。
由 build_r2_mode24.py 套在 TV-1M-dashboard_(mode 1-4)_(09月20日; 21.59) 的本體上。

規則 (R2):
  買 = 模式 2 在可買區 且 模式 4 向上, 且本根至少一個剛出現 (剛進可買區, 或 EMA9 剛轉向上)
  賣 = ④f 可選: 模式 2 在可賣區 且 模式 4 向下 (兩者同時, 本根至少一個剛出現) [預設] / 剛進可賣區即賣 / 只靠可買區結束 + 收市 / 舊規則 (模式 1 賣訊在可賣區, 需開啟模式 1)
  另有 可買區結束平倉 (M2區結束) / 15:58 EOD / 可選固定止損 / 窗口結束
  ④f 可把模式 1 / 模式 3 重新加回買入條件 (預設關)
  ⑨ 掃描 81 組改為 模式 2 下界百分位 {5,10,20} × 可買區結束規則 {破慢線或谷底, RSI14 轉下, RSI28 轉下} × 模式 4 斜率根數 {1,3,5} × 賣法 {M2&M4 同時, 進可賣區即賣, 只靠區結束}
"""


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, n, old[:90])
    return s.replace(old, new)


SELL_OPTS = '["模式 2 可賣區 + 模式 4 向下 (兩者同時, 本根至少一個剛出現)", "模式 2 剛進入可賣區即賣", "只靠可買區結束 + 收市強平 (不主動賣)", "舊規則: 模式 1 賣訊在可賣區 (需開啟模式 1)"]'


def apply(s):
    # ── ④f 開關 (放在 ④c 群組之後: matchWinS 那一行之後) ──
    s = rep(s, 'matchWinS  = input.int(5, "賣: 模式 1 賣訊的有效根數 — 淺綠 N 根完成後 N 根內若處於可賣區即成立"', 'matchWinS  = input.int(5, "賣: 模式 1 賣訊的有效根數 (只在 ④f 選「舊規則」時用)"')
    i = s.index('\n', s.index('matchWinS  = input.int(5,')) + 1
    s = s[:i] + ('gRF       = "④f R2 · 只用模式 2 + 4 決定買賣 (模式 1 / 3 預設關閉)"\n'
                 'useM1     = input.bool(false, "買入條件加回模式 1 (柱到界後淺紅 N 根, 5 根內有效) — R2 預設關", group = gRF, display = display.none)\n'
                 'useM3     = input.bool(false, "買入條件加回模式 3 (9/26/9 金叉, 5 根內有效) — R2 預設關", group = gRF, display = display.none)\n'
                 'sellRule  = input.string("模式 2 可賣區 + 模式 4 向下 (兩者同時, 本根至少一個剛出現)", "賣出規則", options = ' + SELL_OPTS + ', group = gRF, tooltip = "R2 的買 = 模式 2 在可買區 且 模式 4 EMA9 向上, 本根至少一個剛出現 (剛進可買區 / EMA9 剛轉向上)。賣的對稱規則 = 模式 2 在可賣區 且 EMA9 向下, 本根至少一個剛出現 (剛進可賣區 / EMA9 剛轉向下)。另外持倉中可買區結束一律平倉 (④c m2ExitOnEnd), 15:58 收市強平。", display = display.none)\n') + s[i:]
    # ── ⑥ 買入核心: 模式 1 / 3 受開關控制 ──
    s = rep(s, 'buyCore = m1Live and m3Live and m2InBuy                     // 模式 1、3 買訊都在窗口內 且 模式 2 處於可買區 (模式 4 閘門在 ④e 之後套上 → buySig)\n',
               'buyCore = (not useM1 or m1Live) and (not useM3 or m3Live) and m2InBuy   // R2: 模式 2 處於可買區; 模式 1 / 3 只在 ④f 開啟時才要求 (模式 4 閘門在 ④e 之後套上 → buySig)\n')
    s = rep(s, 'buyEvt  = m1Buy or m3Buy or m2BuyStart                      // 本根至少一個模式剛出現買點 (模式 4 剛轉向上也算, 在 ④e 加上)\n',
               'buyEvt  = (useM1 and m1Buy) or (useM3 and m3Buy) or m2BuyStart   // 本根至少一個「參與中」的模式剛出現買點 (模式 4 剛轉向上也算, 在 ④e 加上)\n')
    s = rep(s, 'sellSig = s1Live and m2InSell and (m1Sell or m2SellStart)   // 合格賣點: 模式 1 賣訊在有效根數內 且 模式 2 處於可賣區, 本根至少一個剛出現; 模式 3 不參與\n',
               'sellSigM1 = s1Live and m2InSell and (m1Sell or m2SellStart) // 舊規則 (④f 可選): 模式 1 賣訊在有效根數內 且 模式 2 處於可賣區; R2 的 sellSig 在 ④e 之後定義\n')
    # ── ④e: 模式 4 向下 + R2 賣訊 ──
    s = rep(s, 'buySig   = buyCore and m4OK and (buyEvt or m4Start)   // 四模式同時: M1 & M3 在窗口內 + M2 可買區 + M4 向上, 且本根至少一個剛出現\n',
               'm4DnStart = useM4 and not m4Up and m4Up[1]            // 模式 4 由可買轉為不可的那一根 (EMA9 剛轉向下; 賣的「剛出現」)\n'
               'buySig   = buyCore and m4OK and (buyEvt or m4Start)   // R2: M2 可買區 + M4 向上 (+ ④f 開啟的模式 1 / 3), 且本根至少一個剛出現\n'
               'sellRuleI = sellRule == "模式 2 可賣區 + 模式 4 向下 (兩者同時, 本根至少一個剛出現)" ? 0 : sellRule == "模式 2 剛進入可賣區即賣" ? 1 : sellRule == "只靠可買區結束 + 收市強平 (不主動賣)" ? 2 : 3\n'
               'sellSig  = sellRuleI == 0 ? (m2InSell and (not useM4 or not m4Up) and (m2SellStart or m4DnStart)) : sellRuleI == 1 ? m2SellStart : sellRuleI == 2 ? false : sellSigM1   // R2 合格賣點\n'
               'sellCmt  = sellRuleI == 0 ? "S-M2&M4" : sellRuleI == 1 ? "S-M2賣區" : sellRuleI == 2 ? "S-無" : "S-M1&M2"\n')
    # ── ⑨ 真單 ──
    s = rep(s, 'if buySig and entryOK and strategy.position_size == 0   // 四模式同時出現買點\n', 'if buySig and entryOK and strategy.position_size == 0   // R2: 模式 2 + 4 (+ ④f 加回的模式) 同時出現買點\n')
    s = rep(s, '    strategy.close("L", comment = "S-M1&M2")\n', '    strategy.close("L", comment = sellCmt)\n')
    # ── ⑮ 掃描: 整段重寫 ──
    i0 = s.index('// ─────────────────────────── ⑮ 參數掃描')
    i1 = s.index('// ─────────────────────────── ⑩ 成交偵測')
    sweep = '''// ─────────────────────────── ⑮ 參數掃描 (R2): 同一窗口 81 組 (模式 2 下界百分位 × 可買區結束規則 × 模式 4 斜率根數 × 賣法) 虛擬回測 ───────────────────────────
gSW       = "⑨ 參數掃描 (R2: 模式 2 + 4 的 81 組)"
showSweep = input.bool(true, "顯示參數掃描表 (主圖)", group = gSW, tooltip = "在同一回測窗口內, 對 81 組「模式 2 下界百分位∈{5,10,20} (上界 = 100 − 下界) × 可買區結束規則∈{跌破慢線或谷底, RSI14 轉勢向下, RSI28 轉勢向下} × 模式 4 斜率根數∈{1,3,5} × 賣法∈{M2 可賣區 + M4 向下, 剛進可賣區即賣, 只靠區結束}」各跑一套虛擬回測 (每組都是 R2 規則: 買 = 該組的可買區 + 該組的 EMA9 向上 且本根至少一個剛出現 (④f 若加回模式 1 / 3 也一併要求); 另有可買區結束平倉 / EOD / 固定止損; 同樣下一根開盤成交、同樣時段、同樣手續費滑點), 以最後一根收盤 mark-to-market 排名。橙底列 = 現行 ④c / ④e / ④f 的組合 (④c 用固定 30/70 或百分位不在網格時顯示「不在網格」)。", display = display.none)
swpRows   = input.int(8, "列出前幾名 (本版 8, 表格矮一點, 與左邊摘要並列不重疊)", minval = 3, maxval = 30, group = gSW, display = display.none)
commPct   = input.float(0.03, "掃描用 · 單邊手續費 % (需與 strategy() 的 commission_value 一致)", minval = 0, step = 0.01, group = gSW, display = display.none)
slipTk    = input.int(2, "掃描用 · 單邊滑點 tick (需與 strategy() 的 slippage 一致)", minval = 0, group = gSW, display = display.none)
int NV = 81                                          // 3(下界百分位) × 3(結束規則) × 3(M4 根數) × 3(賣法)
int NZ = 9                                           // 模式 2 區間狀態機: 3 個下界百分位 × 3 種結束規則
var int[]   vPos   = array.new_int(NV, 0)
var int[]   vPend  = array.new_int(NV, 0)
var float[] vEntry = array.new_float(NV, na)
var float[] vEq    = array.new_float(NV, 1.0)
var int[]   vTr    = array.new_int(NV, 0)
var int[]   vWin   = array.new_int(NV, 0)
// 期內最大昇幅 (窗內盤中 K): 由窗內最低點到其後最高點; 買入持有 = 窗口第一根開盤 → 最後收盤
var float runMin  = na
var float maxRise = 0.0
var float winOpen = na
if inWindow and inSess
    runMin  := na(runMin) ? low : math.min(runMin, low)
    maxRise := math.max(maxRise, (high - runMin) / runMin * 100.0)
    if na(winOpen)
        winOpen := open
// ── 9 個模式 2 區間狀態機 (全域無條件計算; 與 ④c 同一套定義, 只有下界百分位與結束規則不同) ──
zLo0 = nz(ta.percentile_linear_interpolation(rsiF, rsiPctLen, 5.0), rsiFixLo)
zHi0 = nz(ta.percentile_linear_interpolation(rsiF, rsiPctLen, 95.0), rsiFixHi)
zLo1 = nz(ta.percentile_linear_interpolation(rsiF, rsiPctLen, 10.0), rsiFixLo)
zHi1 = nz(ta.percentile_linear_interpolation(rsiF, rsiPctLen, 90.0), rsiFixHi)
zLo2 = nz(ta.percentile_linear_interpolation(rsiF, rsiPctLen, 20.0), rsiFixLo)
zHi2 = nz(ta.percentile_linear_interpolation(rsiF, rsiPctLen, 80.0), rsiFixHi)
zReachLo0 = nz(ta.barssince(rsiF <= zLo0)[1], 99999) < m2Reach
zReachHi0 = nz(ta.barssince(rsiF >= zHi0)[1], 99999) < m2Reach
zReachLo1 = nz(ta.barssince(rsiF <= zLo1)[1], 99999) < m2Reach
zReachHi1 = nz(ta.barssince(rsiF >= zHi1)[1], 99999) < m2Reach
zReachLo2 = nz(ta.barssince(rsiF <= zLo2)[1], 99999) < m2Reach
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
    iPz = math.floor(z / 3)
    iEz = z % 3
    rLo = iPz == 0 ? zReachLo0 : iPz == 1 ? zReachLo1 : zReachLo2
    rHi = iPz == 0 ? zReachHi0 : iPz == 1 ? zReachHi1 : zReachHi2
    bSt = turnUpF and rLo
    sSt = turnDnF and rHi
    st  = array.get(zState, z)
    if m2ResetDay and newDay
        st := 0
    prevZ = st
    trZ = array.get(zTrough, z)
    pkZ = array.get(zPeak, z)
    bEndZ = iEz == 0 ? (xFSdn or rsiF < trZ) : iEz == 1 ? turnDnF : turnDnS
    sEndZ = iEz == 0 ? (xFSup or rsiF > pkZ) : iEz == 1 ? turnUpF : turnUpS
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
// ── 模式 4 的 3 種斜率根數 (1 / 3 / 5) ──
m4UpA = m4Ema > m4Ema[1]
m4UpB = m4Ema > m4Ema[3]
m4UpC = m4Ema > m4Ema[5]
m4StA = m4UpA and not m4UpA[1]
m4StB = m4UpB and not m4UpB[1]
m4StC = m4UpC and not m4UpC[1]
m4DnA = not m4UpA and m4UpA[1]
m4DnB = not m4UpB and m4UpB[1]
m4DnC = not m4UpC and m4UpC[1]
m13OK  = (not useM1 or m1Live) and (not useM3 or m3Live)      // ④f 加回的模式 1 / 3 (預設關 → 恆真)
m13Evt = (useM1 and m1Buy) or (useM3 and m3Buy)
if showSweep
    for v1 = 0 to NV - 1
        iP   = math.floor(v1 / 27)                 // Pine 的 / 永遠回傳 float, 不截斷 → 一定要 floor
        iE   = math.floor(v1 / 9) % 3
        iL   = math.floor(v1 / 3) % 3
        iS   = v1 % 3
        zi   = iP * 3 + iE
        // 1) 上一根收盤掛的單在本根開盤成交 (與真實策略同步), 含滑點與手續費
        pendV = array.get(vPend, v1)
        if pendV == 1
            array.set(vPos, v1, 1)
            array.set(vEntry, v1, open + slipTk * syminfo.mintick)
            array.set(vPend, v1, 0)
        else if pendV == -1
            epV = array.get(vEntry, v1)
            xpV = open - slipTk * syminfo.mintick
            rV  = xpV / epV - 1.0 - 2.0 * commPct / 100.0
            array.set(vEq, v1, array.get(vEq, v1) * (1.0 + rV))
            array.set(vTr, v1, array.get(vTr, v1) + 1)
            if rV > 0
                array.set(vWin, v1, array.get(vWin, v1) + 1)
            array.set(vPos, v1, 0)
            array.set(vPend, v1, 0)
        // 1b) 固定止損 (與 strategy.exit 同步: 成交當根收盤才掛, 下一根起生效; 開盤跳空低於止損則以開盤成交)
        if useStop and pendV != 1 and array.get(vPos, v1) == 1
            epS  = array.get(vEntry, v1)
            stpS = epS * (1.0 - stopPct / 100.0)
            if low <= stpS
                xpS = math.min(open, stpS) - slipTk * syminfo.mintick
                rS  = xpS / epS - 1.0 - 2.0 * commPct / 100.0
                array.set(vEq, v1, array.get(vEq, v1) * (1.0 + rS))
                array.set(vTr, v1, array.get(vTr, v1) + 1)
                if rS > 0
                    array.set(vWin, v1, array.get(vWin, v1) + 1)
                array.set(vPos, v1, 0)
                array.set(vPend, v1, 0)
        // 2) 本根收盤評估訊號 → 掛到下一根開盤 (R2 規則, 與真單同一條)
        posV1 = array.get(vPos, v1)
        upV   = iL == 0 ? m4UpA : iL == 1 ? m4UpB : m4UpC
        stV   = iL == 0 ? m4StA : iL == 1 ? m4StB : m4StC
        dnV   = iL == 0 ? m4DnA : iL == 1 ? m4DnB : m4DnC
        inB   = array.get(zInBuy, zi)
        inS   = array.get(zInSell, zi)
        bSt2  = array.get(zBStart, zi)
        sSt2  = array.get(zSStart, zi)
        bSig  = inB and m13OK and (not useM4 or upV) and (bSt2 or m13Evt or (useM4 and stV))
        sSig  = iS == 0 ? (inS and (not useM4 or not upV) and (sSt2 or (useM4 and dnV))) : iS == 1 ? sSt2 : false
        if posV1 == 0 and bSig and entryOK
            array.set(vPend, v1, 1)
        else if posV1 == 1 and (sSig or (m2ExitOnEnd and array.get(zBEnd, zi)) or eodBar or not inWindow)
            array.set(vPend, v1, -1)
// 現行 ④c / ④e / ④f 在網格中的位置 (橙底列用)
liveIp = rsiBandMd == "固定: 30 / 70" ? -1 : (math.abs(rsiPctLo - 5) < 0.01 and math.abs(rsiPctHi - 95) < 0.01) ? 0 : (math.abs(rsiPctLo - 10) < 0.01 and math.abs(rsiPctHi - 90) < 0.01) ? 1 : (math.abs(rsiPctLo - 20) < 0.01 and math.abs(rsiPctHi - 80) < 0.01) ? 2 : -1
liveIe = endModeA ? 0 : endModeB ? 1 : 2
liveIl = m4Look == 1 ? 0 : m4Look == 3 ? 1 : m4Look == 5 ? 2 : -1
liveIs = sellRuleI <= 2 ? sellRuleI : -1
liveV  = (liveIp >= 0 and liveIl >= 0 and liveIs >= 0) ? liveIp * 27 + liveIe * 9 + liveIl * 3 + liveIs : -1

'''
    s = s[:i0] + sweep + s[i1:]
    # ── 掃描表 ──
    s = rep(s, '"掃描 81 組 (四模式買 / M1在可賣區賣) · 最大昇幅 "', '"掃描 81 組 (R2: M2 下界P×結束規則 × M4 根數×賣法) · 最大昇幅 "')
    s = rep(s, '    table.cell(rpt, 8, 1, "買N/k", text_size = sizeV, bgcolor = sBg)\n    table.cell(rpt, 9, 1, "賣N/k", text_size = sizeV, bgcolor = sBg)\n',
               '    table.cell(rpt, 8, 1, "M2 下界P/結束", text_size = sizeV, bgcolor = sBg)\n    table.cell(rpt, 9, 1, "M4根/賣法", text_size = sizeV, bgcolor = sBg)\n')
    s = rep(s, '''        Nb2  = math.floor(vv / 27) + 1
        kb2  = array.get(KG, math.floor(vv / 9) % 3)
        Ns2  = math.floor(vv / 3) % 3 + 1
        ks2  = array.get(KG, vv % 3)
        isLive = Nb2 == fadeBuy and Ns2 == fadeSell and math.abs(kb2 - kBuy) < 0.001 and math.abs(ks2 - kSell) < 0.001
''', '''        iP2  = math.floor(vv / 27)
        iE2  = math.floor(vv / 9) % 3
        iL2  = math.floor(vv / 3) % 3
        iS2  = vv % 3
        pTxt = iP2 == 0 ? "P5" : iP2 == 1 ? "P10" : "P20"
        eTxt = iE2 == 0 ? "破慢線/谷底" : iE2 == 1 ? "14轉下" : "28轉下"
        lTxt = iL2 == 0 ? "1" : iL2 == 1 ? "3" : "5"
        sTxt = iS2 == 0 ? "M2&M4" : iS2 == 1 ? "進賣區" : "只區結束"
        isLive = vv == liveV
''')
    s = rep(s, '''            table.cell(rpt, 8, i2 + 2, str.tostring(Nb2) + " / " + (kb2 <= 0 ? "不要求" : str.tostring(kb2, "#.#")), text_size = sizeV, bgcolor = rBg)
            table.cell(rpt, 9, i2 + 2, str.tostring(Ns2) + " / " + (ks2 <= 0 ? "不要求" : str.tostring(ks2, "#.#")), text_size = sizeV, bgcolor = rBg)
''', '''            table.cell(rpt, 8, i2 + 2, pTxt + " / " + eTxt, text_size = sizeV, bgcolor = rBg)
            table.cell(rpt, 9, i2 + 2, lTxt + " / " + sTxt, text_size = sizeV, bgcolor = rBg)
''')
    s = rep(s, '''    table.cell(rpt, 7, nShow + 2, "現行 買N" + str.tostring(fadeBuy) + "k" + str.tostring(kBuy, "#.#") + " 賣N" + str.tostring(fadeSell) + "k" + str.tostring(kSell, "#.#") + " → " + (liveRank > 0 ? "第 " + str.tostring(liveRank) + "/81" : "不在網格 (k∈1/1.5/2, N∈1-3)"), text_size = sizeV, bgcolor = sBg, text_halign = text.align_left)
''', '''    table.cell(rpt, 7, nShow + 2, "現行 M2 " + (rsiBandMd == "固定: 30 / 70" ? "固定30/70" : "P" + str.tostring(rsiPctLo, "#") + "/" + str.tostring(rsiPctHi, "#")) + " " + (endModeA ? "破慢線/谷底" : endModeB ? "14轉下" : "28轉下") + " · M4 " + str.tostring(m4Look) + " 根 · 賣 " + sellCmt + (useM1 or useM3 ? " · 加回 M" + (useM1 ? "1" : "") + (useM3 ? "3" : "") : "") + " → " + (liveRank > 0 ? "第 " + str.tostring(liveRank) + "/81" : "不在網格 (P∈5/10/20 · M4∈1/3/5 · 賣法≠舊規則)"), text_size = sizeV, bgcolor = sBg, text_halign = text.align_left)
''')
    # ── prm 表 ──
    s = rep(s, '"買: M1 & M3 匹配 (窗口 " + str.tostring(matchWin) + " 根) + M2 可買區 + M4 向上"', '"買 (R2): M2 可買區 + M4 向上" + (useM1 ? " + M1 (窗 " + str.tostring(matchWin) + ")" : "") + (useM3 ? " + M3 (窗 " + str.tostring(matchWin) + ")" : "") + (useM1 or useM3 ? "" : " (模式 1/3 關閉)")')
    s = rep(s, '"賣: M1 賣訊 (有效 " + str.tostring(matchWinS) + " 根) 在 M2 可賣區內"', '"賣 (R2): " + (sellRuleI == 0 ? "M2 可賣區 + M4 向下" : sellRuleI == 1 ? "剛進 M2 可賣區" : sellRuleI == 2 ? "不主動賣 (只靠區結束/收市)" : "M1 賣訊在 M2 可賣區 (舊)")')
    s = rep(s, '" (段要先到界) + 模式2 RSI14/28 可買區 + 模式3 金叉 + 模式4 EMA9向上 · 買需四者同時; 賣 = M1 在可賣區; 可買區結束平倉 · 窗口 "',
               '" (段要先到界; R2 " + (useM1 ? "已加回" : "已關閉") + ") + 模式2 RSI14/28 可買區 + 模式3 金叉 (R2 " + (useM3 ? "已加回" : "已關閉") + ") + 模式4 EMA9向上 · R2 買 = M2 可買區 + M4 向上; 賣 = " + sellCmt + "; 可買區結束平倉 · 窗口 "')
    s = rep(s, '"===== 四模式回測 (柱到界+RSI區+金叉+EMA9) {0}', '"===== R2 模式 2+4 回測 (RSI區+EMA9; 模式 1/3 " + (useM1 or useM3 ? "部分加回" : "關閉") + ") {0}')
    s = rep(s, '(含 S-M1&M2 / M2區結束 / SL / EOD / 窗口結束)', '(含 S-M2&M4 或 ④f 選的賣法 / M2區結束 / SL / EOD / 窗口結束)')
    s = rep(s, '"期內無交易 — 檢查 ⑤ 時段 / margin_long = 0 / ④ 上下界 / ④c 匹配窗口與可買區規則"', '"期內無交易 — 檢查 ⑤ 時段 / margin_long = 0 / ④c 可買區規則 (下界百分位、結束規則) / ④e 模式 4"')
    # ── 文字同步 (評審指出的過時文字) ──
    s = rep(s, '"買 · 下界倍數 k (下界 = 基準 × k; 本版 1.5 = 要求更深; 0 = 不要求到界, 每次淺紅 N 根都買)"', '"買 · 下界倍數 k (下界 = 基準 × k; 0 = 不要求到界, 每次淺紅 N 根都算模式 1 買訊; R2 需 ④f 加回模式 1 才影響買賣)"')
    s = rep(s, '設 0 = 不檢查, 每次淺綠 N 根都賣 (較早落車)。', '設 0 = 不檢查, 每次淺綠 N 根都算模式 1 賣訊 (R2 只在 ④f 選舊規則時才用來賣)。')
    s = rep(s, '"買: 模式 1 與模式 3 的買訊匹配窗口 (根) — 兩者在此根數內先後出現即算「同時」; 1 = 必須同一根"', '"買: 模式 1 與模式 3 的買訊匹配窗口 (根; 只在 ④f 加回模式 1 / 3 時用)"')
    s = rep(s, '四者同時且本根至少一個剛出現 → 合格買點。", display = display.none)', 'R2 預設買 = 模式 2 可買區 + 模式 4 向上 (本根至少一個剛出現); ④f 加回模式 1 / 3 後才要求它們在此窗口內。", display = display.none)')
    s = rep(s, 'tooltip = "賣出 = 模式 1 賣訊 (昇到上界後淺綠 N 根完成) 在有效根數內 且 模式 2 處於可賣區, 本根至少一個剛出現 (模式 1 剛觸發, 或 剛進入可賣區)。另有 可買區結束平倉 / 15:58 收市強平 / 可選固定止損。"', 'tooltip = "舊規則 (④f 選「舊規則」時才生效): 模式 1 賣訊在有效根數內 且 模式 2 處於可賣區。R2 預設賣 = 模式 2 可賣區 + 模式 4 向下, 見 ④f。另有 可買區結束平倉 / 15:58 收市強平 / 可選固定止損。"')
    s = rep(s, '"舊規則: 模式 1 賣訊在可賣區 (需開啟模式 1)"', '"舊規則: 模式 1 賣訊在可賣區 (不需開啟 ④f 模式 1; 該開關只影響買入)"')
    s = rep(s, '④d 模式 3: 敏感 MACD (9/26/9) 快線穿慢線 — 只參與買入, 不參與賣出 ───', '④d 模式 3: 敏感 MACD (9/26/9) 快線穿慢線 — R2 預設不參與買賣 (④f 開啟後只參與買入) ───')
    s = rep(s, 'gR3        = "④d 模式 3 · 敏感 MACD (9/26/9) 金叉 (只參與買入)"', 'gR3        = "④d 模式 3 · 敏感 MACD (9/26/9) 金叉 (R2 預設不參與; ④f 開啟後只參與買入)"')
    s = rep(s, '// 先拍一份快照, 供 ⑮ 參數掃描共用 (掃描寫在 ⑨ 之後, 但段統計在下面就會被更新)', '// 先拍一份快照供 momB / momS 用 (段統計在下面才更新)')
    s = rep(s, '④e 模式 4: EMA9 斜率為正 (趨勢向上) 才可以買入 — 只限制買入, 不參與賣出 ───', '④e 模式 4: EMA9 斜率為正 (趨勢向上) 才可以買入 — R2 預設賣法亦用 EMA9 向下 / 剛轉向下 ───')
    s = rep(s, 'gR4      = "④e 模式 4 · EMA9 斜率 (趨勢向上才可買; 只限制買入)"', 'gR4      = "④e 模式 4 · EMA9 斜率 (向上才可買; R2 預設賣法也要求 EMA9 向下)"')
    s = rep(s, '"啟用模式 4 (關掉 = 回到三模式)"', '"啟用模式 4 (關掉 = 只剩模式 2 決定買賣; 加回 ④f 的模式 1 / 3 時才是三模式)"')
    s = rep(s, '+ " · " + m3Def + " · 只參與買入", text_size = sizeV, text_color = m3Live ? color.green : color.gray)', '+ " · " + m3Def + (useM3 ? " · 只參與買入" : " · R2 不參與 (④f 可加回)"), text_size = sizeV, text_color = m3Live ? color.green : color.gray)')
    s = rep(s, '" → 四模式同時 " + str.tostring(cBoth) + "  (現況: M1 "', '" → " + (useM1 or useM3 ? "含加回模式 同時 " : "M2+M4 同時 ") + str.tostring(cBoth) + "  (現況: M1 "')
    s = rep(s, """"M1 淺綠N根 " + str.tostring(cS1) + " · M2 進可賣區 " + str.tostring(cS2) + " → 同時 " + str.tostring(cSBoth) + "  (現況: S1 " + (s1Age >= 999 ? "-" : str.tostring(s1Age) + " 根前") + " / M2 " + m2Zone + ") · 可買區結束平倉 \"""",
               """"M2 進可賣區 " + str.tostring(cS2) + " · M4 轉下 " + str.tostring(cM4Dn) + (sellRuleI == 3 ? " · M1 淺綠N根 " + str.tostring(cS1) : "") + " → R2 賣點 " + str.tostring(cSBoth) + "  (現況: M2 " + m2Zone + " / M4 " + (m4Up ? "向上" : "向下") + (sellRuleI == 3 ? " / S1 " + (s1Age >= 999 ? "-" : str.tostring(s1Age) + " 根前") : "") + ") · 可買區結束平倉 \"""")
    s = rep(s, 'var int cSBoth = 0\n', 'var int cSBoth = 0\nvar int cM4Dn  = 0\n')
    s = rep(s, '    cSBoth += sellSig ? 1 : 0\n', '    cSBoth += sellSig ? 1 : 0\n    cM4Dn  += m4DnStart ? 1 : 0\n')
    s = rep(s, '"要更嚴 (少而準): M1 百分位↑ 倍數k↑ 根數↑ · M2 下界百分位↓ 上界百分位↑ · 匹配窗口↓ · M4 斜率根數↑ · 要更鬆: 反之"', '"R2 要更嚴 (少而準): M2 下界百分位↓ 上界百分位↑ · M2 結束規則改「破慢線/谷底」 · M4 斜率根數↑ · ④f 賣法改 M2&M4 同時; 要更鬆: 反之 (M1 門檻 / 匹配窗口只在 ④f 加回模式 1/3 時有效)"')
    s = rep(s, """"M1 k" + str.tostring(kBuy, "#.#") + "/N" + str.tostring(fadeBuy) + " P" + str.tostring(depthPctl, "#") + " · M2 RSI" + str.tostring(rsiFastLen) + "/" + str.tostring(rsiSlowLen) + " · M3 " + str.tostring(m3Fast) + "/" + str.tostring(m3Slow) + (m3Def == "DIF 上穿 DEA (金叉)" ? "金叉" : "0軸") + " · 窗" + str.tostring(matchWin) + "/" + str.tostring(matchWinS), text_size = sizeV)""",
               """"R2 M2 " + (rsiBandMd == "固定: 30 / 70" ? "固定30/70" : "P" + str.tostring(rsiPctLo, "#") + "/" + str.tostring(rsiPctHi, "#")) + " " + (endModeA ? "破慢線/谷底" : endModeB ? "14轉下" : "28轉下") + " · M4 " + str.tostring(m4Look) + " 根 · 賣 " + sellCmt + (useM1 ? " · M1 k" + str.tostring(kBuy, "#.#") + "/N" + str.tostring(fadeBuy) + " 窗" + str.tostring(matchWin) : "") + (useM3 ? " · M3 窗" + str.tostring(matchWin) : ""), text_size = sizeV)""")
    s = rep(s, '再放寬 ④c 的 M1/M3 匹配窗口 (兩個買訊要在窗口內先後出現, 且那一根要在可買區、EMA9 向上) 或 ④ 上下界 (百分位↓ 倍數↓), 或改 ④c 可買區結束規則, 或拉長 ① 期間"', '再放寬 ④c 可買區規則 (下界百分位↑ / 結束規則改 RSI28 轉下) 或 ④e 模式 4 斜率根數, 或改 ④f 賣法, 或拉長 ① 期間" + (useM1 or useM3 ? " (④f 已加回模式 1/3: 亦可放寬 ④ 上下界 / ④c 匹配窗口)" : "")')
    s = rep(s, '"交易次數 {0} · 勝 {1} 負 {2} · 總損益 {3} ({4}%) · 本金 {5} · 校準k={6} · 買 k{7} N{8} · 賣 k{9} N{10} · 期內最大昇幅 {11}% · 買入持有 {12}%"', '"交易次數 {0} · 勝 {1} 負 {2} · 總損益 {3} ({4}%) · 本金 {5} · 校準k={6} · R2 M2 P{7}/{8} · M4 {9} 根 · 賣 {10} · 期內最大昇幅 {11}% · 買入持有 {12}%"')
    s = rep(s, 'str.tostring(kEff, "#.##"), str.tostring(kBuy, "#.#"), fadeBuy, str.tostring(kSell, "#.#"), fadeSell, str.tostring(maxRise, "#.##")', 'str.tostring(kEff, "#.##"), str.tostring(rsiPctLo, "#"), str.tostring(rsiPctHi, "#"), m4Look, sellCmt, str.tostring(maxRise, "#.##")')
    assert 'array.get(KG,' not in s and 'vAgeS' not in s and 'sellSigM1' in s
    return s
