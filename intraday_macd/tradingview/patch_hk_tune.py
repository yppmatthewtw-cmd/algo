# -*- coding: utf-8 -*-
"""patch_hk_tune.py — 港股 7709 版主策略的「後台自動調參」補丁 (由 build_hk7709.py 呼叫)。

改動:
  ⑨ 參數掃描 81 組改為 買N∈{1,2,3} × 買k∈{0.5,1,1.5} × M1/M3 匹配窗口∈{5,10,20} × 出場模式∈{現行, 追蹤止損, 止賺} (賣方 N/k 沿用 ④ 輸入)
  ⑨b 走動式自動調參: 每個新交易日開始, 以「之前 N 個交易日」81 組的虛擬績效選最佳組合 (至少 M 筆交易), 套到今日真單 (無前視); 初期不足 N 日用 ④/④c 手動值
  ⑤ 只在韓股交易時段開新倉 (7709 追蹤 SK Hynix; KRX 09:00-15:30 KST = 08:00-14:30 HKT), 14:30 後不開新倉 (可關)
  ⑨ 真單新增 追蹤止損 / 止賺 出場 (只在自動調參選到該出場模式時生效)
"""


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, n, old[:90])
    return s.replace(old, new)


def apply(s):
    # ── ④: 現行生效參數 (liveNb / liveKb / liveExit) 宣告在 minDepthB 之前; 門檻用生效值 ──
    s = rep(s, 'minDepthB = baseDepth * kBuy                                          // 買: 下跌動能深度門檻\n'
               'minAreaB  = thMode == "手動" ? minAreaIn * kBuy  : minDepthB * mbBuy  * areaFactor\n',
               '// ─── ⑨b 後台自動調參 (走動式, 無前視): 每個新交易日開始, 用「之前 N 個交易日」81 組虛擬回測 (⑨) 的績效選最佳組合套到今日真單 ───\n'
               'gAT      = "⑨b 後台自動調參 (走動式: 每日用之前 N 日最佳組合, 無前視)"\n'
               'autoTune = input.string("走動式: 每日套用之前 N 日最佳組合", "自動調參", options = ["走動式: 每日套用之前 N 日最佳組合", "關: 用 ④ / ④c 手動值"], group = gAT, tooltip = "走動式 = 每個交易日的第一根 K, 從 ⑨ 的 81 組 (買 N × 買 k × 匹配窗口 × 出場模式) 中選出「之前 N 個交易日」報酬最高、且至少有 M 筆交易的組合, 套到今日的真單; 今日的表現不會用來選今日的參數 (無前視)。回看日數不足時沿用 ④ / ④c 的手動值。關 = 全部用 ④ / ④c 手動值 (等於舊版)。", display = display.none)\n'
               'tuneDays = input.int(10, "回看幾個交易日 (港股一個月 ≈ 21 日; 10 = 半個月)", minval = 2, maxval = 30, group = gAT, display = display.none)\n'
               'tuneMinTr = input.int(2, "最佳組合在回看期內至少要有幾筆交易 (不足的組合不選; 全部不足則沿用上一組)", minval = 0, maxval = 20, group = gAT, display = display.none)\n'
               'trailPct = input.float(0.8, "出場模式「追蹤止損」: 由持倉期間最高價回落 % 即平倉", minval = 0.1, step = 0.1, group = gAT, tooltip = "1 分鐘 K 上 2 倍槓桿產品, 0.8% 約等於一段正常回調。太小會被雜訊掃出, 太大等於沒有。", display = display.none)\n'
               'tpPct    = input.float(1.2, "出場模式「止賺」: 由進場價升 % 即限價平倉 (限價單無滑點)", minval = 0.1, step = 0.1, group = gAT, display = display.none)\n'
               'var int   liveNb   = fadeBuy     // 現行生效的 買 N (自動調參會逐日改寫; 關閉時 = ④ 輸入)\n'
               'var float liveKb   = kBuy        // 現行生效的 買 k\n'
               'var int   liveExit = 0           // 現行生效的出場模式: 0 現行 / 1 追蹤止損 / 2 止賺\n'
               'var int   liveIdx  = -1          // 現行生效組合在 81 組網格中的編號 (-1 = 不在網格)\n'
               'autoOn   = autoTune != "關: 用 ④ / ④c 手動值"\n'
               'minDepthB = baseDepth * liveKb                                        // 買: 下跌動能深度門檻 (用現行生效 k)\n'
               'minAreaB  = thMode == "手動" ? minAreaIn * liveKb : minDepthB * mbBuy  * areaFactor\n')
    s = rep(s, 'matchWin   = input.int(5, "買: 模式 1 與模式 3 的買訊匹配窗口 (根)', 'matchWin   = input.int(5, "買: 模式 1 與模式 3 的買訊匹配窗口 (根; 自動調參開啟時由 ⑨b 逐日在 5/10/20 中選)')
    s = rep(s, 'matchWinS  = input.int(5, "賣: 模式 1 賣訊的有效根數', 'var int   liveWin  = matchWin    // 現行生效的 M1/M3 匹配窗口 (自動調參會逐日改寫)\nmatchWinS  = input.int(5, "賣: 模式 1 賣訊的有效根數')
    s = rep(s, 'm3Live     = m3Age < matchWin\n', 'm3Live     = m3Age < liveWin\n')
    s = rep(s, 'rawBuy  = useFade ? nFadeDn == fadeBuy  : crossUp', 'rawBuy  = useFade ? nFadeDn == liveNb   : crossUp')
    s = rep(s, 'momB    = kBuy  <= 0 or (segBars >= mbBuy  and segDepth >= minDepthB', 'momB    = liveKb <= 0 or (segBars >= mbBuy  and segDepth >= minDepthB')
    s = rep(s, 'm1Live  = m1Age < matchWin\n', 'm1Live  = m1Age < liveWin\n')
    # ── ⑤ 韓股時段 ──
    s = rep(s, 'lunchSess = input.session("1158-1200", "午休前平倉時段 (只在開啟午休前平倉時用)", group = gS, display = display.none)\n',
               'lunchSess = input.session("1158-1200", "午休前平倉時段 (只在開啟午休前平倉時用)", group = gS, display = display.none)\n'
               'korOnly   = input.bool(true, "只在韓股交易時段開新倉 (7709 追蹤 SK Hynix; 韓股 09:00-15:30 KST = 08:00-14:30 HKT, 之後只剩莊家報價)", group = gS, tooltip = "7709 是 SK Hynix 的 2 倍槓桿產品, 韓股收市 (14:30 HKT) 後標的不再變動, 產品價格只在莊家報價附近橫行, 動能訊號多為雜訊。開啟 = 14:30 後不開新倉 (已有倉照原規則出場)。", display = display.none)\n'
               'korSess   = input.session("1430-1600", "韓股收市後不開新倉的時段 (HKT)", group = gS, display = display.none)\n'
               'korFlat   = input.bool(false, "韓股收市時 (14:30) 平倉 (預設關 = 持倉到原規則出場)", group = gS, display = display.none)\n')
    s = rep(s, 'lunchBar  = lunchFlat and isIntra and not na(time(timeframe.period, lunchSess, tzStr))   // 午休前平倉那一根 (預設關)\n',
               'lunchBar  = lunchFlat and isIntra and not na(time(timeframe.period, lunchSess, tzStr))   // 午休前平倉那一根 (預設關)\n'
               'korBlock  = korOnly and isIntra and not na(time(timeframe.period, korSess, tzStr))       // 韓股收市後: 不開新倉\n'
               'korBar    = korFlat and korBlock and not korBlock[1]                                     // 韓股收市那一根 (可選平倉)\n')
    s = rep(s, 'entryOK = inWindow and inSess and not blockNew and not eodBar and not lunchBar\n', 'entryOK = inWindow and inSess and not blockNew and not korBlock and not eodBar and not lunchBar\n')
    # ── ⑨ 真單: 追蹤止損 / 止賺 (自動調參選到時) + 韓股收市平倉 ──
    s = rep(s, 'if useStop and strategy.position_size > 0\n    strategy.exit("SL", "L", stop = strategy.position_avg_price * (1 - stopPct / 100.0), comment = "SL")\n',
               'if useStop and strategy.position_size > 0\n    strategy.exit("SL", "L", stop = strategy.position_avg_price * (1 - stopPct / 100.0), comment = "SL")\n'
               'var float livePeak = na                                       // 持倉期間最高價 (含本根; 成交當根 = 該根最高)\n'
               'livePeak := strategy.position_size > 0 ? (na(livePeak) ? high : math.max(livePeak, high)) : na\n'
               'if liveExit == 1 and strategy.position_size > 0                // 出場模式 1: 追蹤止損 (本根收盤掛, 下一根起生效, 與 ⑨ 掃描同步)\n'
               '    strategy.exit("TS", "L", stop = livePeak * (1 - trailPct / 100.0), comment = "追蹤止損")\n'
               'if liveExit == 2 and strategy.position_size > 0                // 出場模式 2: 止賺限價\n'
               '    strategy.exit("TP", "L", limit = strategy.position_avg_price * (1 + tpPct / 100.0), comment = "止賺")\n'
               'if korBar and strategy.position_size != 0                      // 韓股收市平倉 (⑤ 可選, 預設關)\n'
               '    strategy.close_all(comment = "韓股收市")\n')
    # ── ⑮ 掃描: 整段重寫 (由 gSW 到迴圈結束) ──
    i0 = s.index('// ─────────────────────────── ⑮ 參數掃描')
    i1 = s.index('// ─────────────────────────── ⑩ 成交偵測')
    sweep = '''// ─────────────────────────── ⑮ 參數掃描 + 後台自動調參: 同一窗口 81 組 (買N × 買k × 匹配窗口 × 出場模式) 虛擬回測 ───────────────────────────
gSW       = "⑨ 參數掃描 (81 組; 自動調參的候選網格)"
showSweep = input.bool(true, "顯示參數掃描表 (主圖)", group = gSW, tooltip = "在同一回測窗口內, 對 81 組「買 N∈{1,2,3} × 買 k∈{0.5,1,1.5} × M1/M3 匹配窗口∈{5,10,20} × 出場模式∈{現行, 追蹤止損, 止賺}」各跑一套虛擬回測 (每組都套上同一套四模式買 / M1 賣訊在可賣區 + 可買區結束平倉 + EOD 的規則, 賣方 N/k 用 ④ 現行值; 同樣下一根開盤成交、同樣時段、同樣手續費滑點、同樣固定止損), 以最後一根收盤 mark-to-market 排名。k 以 ④ 的第 P 百分位基準為 1 倍。⑨b 自動調參就是每日在這 81 組裡挑「之前 N 日」最好的一組; 關掉自動調參時可把最佳組合手動填回 ④ / ④c。", display = display.none)
swpRows   = input.int(8, "列出前幾名 (本版 8, 表格矮一點, 與右邊摘要並列不重疊)", minval = 3, maxval = 30, group = gSW, display = display.none)
commPct   = input.float(0.05, "掃描用 · 單邊手續費 % (需與 strategy() 的 commission_value 一致)", minval = 0, step = 0.01, group = gSW, display = display.none)
slipTk    = input.int(2, "掃描用 · 單邊滑點 tick (需與 strategy() 的 slippage 一致)", minval = 0, group = gSW, display = display.none)
var float[] KGB    = array.from(0.5, 1.0, 1.5)      // 買 k 網格: 0.5 = 較鬆 (到界要求減半, 訊號多), 1 = 自動門檻, 1.5 = 舊版預設 (較嚴)
var int[]   WG     = array.from(5, 10, 20)          // M1/M3 匹配窗口網格 (根)
int NV = 81                                          // 3(買N) × 3(買k) × 3(窗口) × 3(出場模式)
var int[]   vPos   = array.new_int(NV, 0)
var int[]   vPend  = array.new_int(NV, 0)
var float[] vEntry = array.new_float(NV, na)
var float[] vEq    = array.new_float(NV, 1.0)
var int[]   vTr    = array.new_int(NV, 0)
var int[]   vWin   = array.new_int(NV, 0)
var int[]   vAge   = array.new_int(NV, 999)         // 每組自己的模式 1 買訊年齡 (模式 3 年齡、模式 2 區間狀態、模式 4 狀態全組共用)
var float[] vPeak  = array.new_float(NV, na)        // 每組持倉期間最高價 (追蹤止損用)
// 期內最大昇幅 (窗內盤中 K): 由窗內最低點到其後最高點; 買入持有 = 窗口第一根開盤 → 最後收盤
var float runMin  = na
var float maxRise = 0.0
var float winOpen = na
if inWindow and inSess
    runMin  := na(runMin) ? low : math.min(runMin, low)
    maxRise := math.max(maxRise, (high - runMin) / runMin * 100.0)
    if na(winOpen)
        winOpen := open
swBase = thMode == "手動" ? minDepthIn : autoDepth    // 掃描用深度基準: 不含 ④b 校準 k, 令 81 組結果與現行輸入無關 (校準關閉時 = baseDepth)
if showSweep or autoOn                                // 自動調參要用掃描結果, 表格關掉也要跑
    for v1 = 0 to NV - 1
        iNb  = math.floor(v1 / 27)                 // Pine 的 / 永遠回傳 float, 不截斷 → 一定要 floor
        iKb  = math.floor(v1 / 9) % 3
        iWn  = math.floor(v1 / 3) % 3
        iEx  = v1 % 3                              // 0 現行 / 1 追蹤止損 / 2 止賺
        Nb   = iNb + 1
        kb   = array.get(KGB, iKb)
        wn   = array.get(WG, iWn)
        // 1) 上一根收盤掛的單在本根開盤成交 (與真實策略同步), 含滑點與手續費
        pendV = array.get(vPend, v1)
        if pendV == 1
            array.set(vPos, v1, 1)
            array.set(vEntry, v1, open + slipTk * syminfo.mintick)
            array.set(vPeak, v1, na)
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
        // 1b) 固定止損 / 追蹤止損 / 止賺 (成交當根收盤才掛, 下一根起生效; 開盤跳空越過則以開盤成交; 止賺為限價單無滑點)
        if pendV != 1 and array.get(vPos, v1) == 1
            epS  = array.get(vEntry, v1)
            pkS  = array.get(vPeak, v1)
            float stpS = useStop ? epS * (1.0 - stopPct / 100.0) : na
            if iEx == 1 and not na(pkS)
                tsS = pkS * (1.0 - trailPct / 100.0)
                stpS := na(stpS) ? tsS : math.max(stpS, tsS)
            float xpS = na
            if not na(stpS) and low <= stpS
                xpS := math.min(open, stpS) - slipTk * syminfo.mintick
            if na(xpS) and iEx == 2
                tpS = epS * (1.0 + tpPct / 100.0)
                if high >= tpS
                    xpS := math.max(open, tpS)
            if not na(xpS)
                rS  = xpS / epS - 1.0 - 2.0 * commPct / 100.0
                array.set(vEq, v1, array.get(vEq, v1) * (1.0 + rS))
                array.set(vTr, v1, array.get(vTr, v1) + 1)
                if rS > 0
                    array.set(vWin, v1, array.get(vWin, v1) + 1)
                array.set(vPos, v1, 0)
                array.set(vPend, v1, 0)
        // 1c) 持倉期間最高價 (含本根), 供下一根的追蹤止損用 (與真單 livePeak 同步)
        if array.get(vPos, v1) == 1
            pk2 = array.get(vPeak, v1)
            array.set(vPeak, v1, na(pk2) ? high : math.max(pk2, high))
        // 2) 本根收盤評估訊號 → 掛到下一根開盤 (四模式同時, 與真單同一條規則; 賣 = 真單的 sellSig)
        posV1 = array.get(vPos, v1)
        dB   = swBase * kb
        aB   = thMode == "手動" ? minAreaIn * kb : dB * mbBuy * areaFactor
        okB  = kb <= 0 or (segBars >= mbBuy and segDepth >= dB and (not useArea or segArea >= aB))
        m1c  = (useFade ? nFadeDn == Nb : crossUp) and segSign == -1 and okB
        ageC = m1c ? 0 : math.min(array.get(vAge, v1) + 1, 999)
        array.set(vAge, v1, ageC)
        bSig = ageC < wn and m3Age < wn and m2InBuy and m4OK and (m1c or m3Buy or m2BuyStart or m4Start)
        if posV1 == 0 and bSig and entryOK
            array.set(vPend, v1, 1)
        else if posV1 == 1 and (sellSig or (m2ExitOnEnd and m2BuyEnd) or eodBar or lunchBar or korBar or not inWindow)
            array.set(vPend, v1, -1)

// ── ⑨b 走動式自動調參: 新交易日第一根, 快照 81 組權益; 用「最舊快照 → 現在」的報酬選最佳 (至少 tuneMinTr 筆), 套到今日真單 (由下一根起生效) ──
var matrix<float> eqHist = matrix.new<float>(NV, 0, na)   // 每欄 = 一個交易日開始時 81 組的權益快照
var matrix<float> trHist = matrix.new<float>(NV, 0, na)   // 同上, 累計筆數
var string tuneNote = "回看日數不足, 用 ④ / ④c 手動值"
var int    tuneDayN = 0
var float  tuneBestR = na
manNb  = fadeBuy
manIk  = math.abs(kBuy - 0.5) < 0.001 ? 0 : math.abs(kBuy - 1.0) < 0.001 ? 1 : math.abs(kBuy - 1.5) < 0.001 ? 2 : -1
manIw  = matchWin == 5 ? 0 : matchWin == 10 ? 1 : matchWin == 20 ? 2 : -1
manIdx = (manNb >= 1 and manNb <= 3 and manIk >= 0 and manIw >= 0) ? (manNb - 1) * 27 + manIk * 9 + manIw * 3 : -1   // 手動值在網格中的編號 (出場模式 = 現行)
if autoOn and liveIdx < 0                                   // 自動調參初期 (未選過) : 生效組合 = 手動值在網格中的位置 (表格橙底用)
    liveIdx := manIdx
if not autoOn
    liveNb   := fadeBuy
    liveKb   := kBuy
    liveWin  := matchWin
    liveExit := 0
    liveIdx  := manIdx
if autoOn and newDay and inWindow
    trF = array.new_float(NV, 0.0)
    for v3 = 0 to NV - 1
        array.set(trF, v3, array.get(vTr, v3))
    matrix.add_col(eqHist, matrix.columns(eqHist), array.copy(vEq))
    matrix.add_col(trHist, matrix.columns(trHist), trF)
    if matrix.columns(eqHist) > tuneDays + 1
        matrix.remove_col(eqHist, 0)
        matrix.remove_col(trHist, 0)
    tuneDayN += 1
    nc = matrix.columns(eqHist)
    if nc >= 2
        bestV = -1
        bestR = -1e9
        if liveIdx >= 0                                   // 現行組合先佔位: 其他組合要「嚴格」更好才換 (減少每日跳來跳去)
            e0L = matrix.get(eqHist, liveIdx, 0)
            if array.get(vTr, liveIdx) - matrix.get(trHist, liveIdx, 0) >= tuneMinTr
                bestV := liveIdx
                bestR := array.get(vEq, liveIdx) / e0L - 1.0
        for v4 = 0 to NV - 1
            e0 = matrix.get(eqHist, v4, 0)
            nTr = array.get(vTr, v4) - matrix.get(trHist, v4, 0)
            rr = array.get(vEq, v4) / e0 - 1.0
            if nTr >= tuneMinTr and rr > bestR
                bestR := rr
                bestV := v4
        if bestV >= 0
            liveIdx   := bestV
            liveNb    := math.floor(bestV / 27) + 1
            liveKb    := array.get(KGB, math.floor(bestV / 9) % 3)
            liveWin   := array.get(WG, math.floor(bestV / 3) % 3)
            liveExit  := bestV % 3
            tuneBestR := bestR * 100.0
            tuneNote  := "第 " + str.tostring(tuneDayN) + " 日 · 回看 " + str.tostring(nc - 1) + " 日最佳 #" + str.tostring(bestV) + " (回看期報酬 " + str.tostring(tuneBestR, "#.##") + "%)"
        else
            tuneNote  := "第 " + str.tostring(tuneDayN) + " 日 · 回看 " + str.tostring(nc - 1) + " 日內沒有組合達到 " + str.tostring(tuneMinTr) + " 筆交易, 沿用上一組"
    else
        tuneNote := "第 " + str.tostring(tuneDayN) + " 日 · 回看日數不足, 用 ④ / ④c 手動值"
exitName = liveExit == 1 ? "追蹤止損 " + str.tostring(trailPct, "#.#") + "%" : liveExit == 2 ? "止賺 " + str.tostring(tpPct, "#.#") + "%" : "現行"
liveTxt  = "買N" + str.tostring(liveNb) + " k" + str.tostring(liveKb, "#.#") + " 窗" + str.tostring(liveWin) + " 出場 " + exitName

'''
    s = s[:i0] + sweep + s[i1:]
    # ── 顯示文字: 用現行生效值 ──
    s = rep(s, '"模式1 下界 (買: 負柱先跌到這裡, k=" + str.tostring(kBuy, "#.#") + ")"', '"模式1 下界 (買: 負柱先跌到這裡, k=" + str.tostring(liveKb, "#.#") + ")"')
    s = rep(s, '    curOKB = kBuy  <= 0 or (curBars >= mbBuy  and curDepth >= minDepthB', '    curOKB = liveKb <= 0 or (curBars >= mbBuy  and curDepth >= minDepthB')
    s = rep(s, 'table.cell(prm, 1, 2, (kBuy <= 0 ? "不要求到界" : "k=" + str.tostring(kBuy, "#.#")', 'table.cell(prm, 1, 2, (liveKb <= 0 ? "不要求到界" : "k=" + str.tostring(liveKb, "#.#")')
    s = rep(s, '" 根≥" + str.tostring(mbBuy)) + " · 再淺紅 N=" + str.tostring(fadeBuy), text_size = sizeV)', '" 根≥" + str.tostring(mbBuy)) + " · 再淺紅 N=" + str.tostring(liveNb) + (autoOn ? " (自動調參生效值)" : ""), text_size = sizeV)')
    s = rep(s, '"買: M1 & M3 匹配 (窗口 " + str.tostring(matchWin) + " 根) + M2 可買區 + M4 向上"', '"買: M1 & M3 匹配 (窗口 " + str.tostring(liveWin) + " 根) + M2 可買區 + M4 向上"')
    s = rep(s, '(useFade ? "模式1 動能減弱: 買 " + str.tostring(fadeBuy) + " 根淺紅 / 賣 "', '(useFade ? "模式1 動能減弱: 買 " + str.tostring(liveNb) + " 根淺紅 / 賣 "')
    s = rep(s, '    table.cell(prm, 0, 10, "調整方向", text_size = sizeV, bgcolor = pBg)\n', '    table.cell(prm, 0, 10, "後台自動調參 (⑨b)", text_size = sizeV, bgcolor = pBg)\n')
    s = rep(s, '    table.cell(prm, 1, 10, "要更嚴 (少而準): M1 百分位↑ 倍數k↑ 根數↑ · M2 下界百分位↓ 上界百分位↑ · 匹配窗口↓ · M4 斜率根數↑ · 要更鬆: 反之", text_size = sizeV, text_color = color.gray)\n',
               '    table.cell(prm, 1, 10, (autoOn ? "走動式 回看 " + str.tostring(tuneDays) + " 日 · " + tuneNote + " → 今日 " + liveTxt : "關 (用 ④ / ④c 手動值: " + liveTxt + ")") + (korOnly ? " · 14:30 韓股收市後不開新倉" : ""), text_size = sizeV, text_color = autoOn ? color.blue : color.gray)\n')
    # 掃描表
    s = rep(s, '"掃描 81 組 (四模式買 / M1在可賣區賣) · 最大昇幅 "', '"掃描 81 組 (買N×買k×窗口×出場; 四模式買 / M1在可賣區賣) · 最大昇幅 "')
    s = rep(s, '    table.cell(rpt, 9, 1, "賣N/k", text_size = sizeV, bgcolor = sBg)\n', '    table.cell(rpt, 9, 1, "窗/出場", text_size = sizeV, bgcolor = sBg)\n')
    s = rep(s, '''        Nb2  = math.floor(vv / 27) + 1
        kb2  = array.get(KG, math.floor(vv / 9) % 3)
        Ns2  = math.floor(vv / 3) % 3 + 1
        ks2  = array.get(KG, vv % 3)
        isLive = Nb2 == fadeBuy and Ns2 == fadeSell and math.abs(kb2 - kBuy) < 0.001 and math.abs(ks2 - kSell) < 0.001
''', '''        Nb2  = math.floor(vv / 27) + 1
        kb2  = array.get(KGB, math.floor(vv / 9) % 3)
        wn2  = array.get(WG, math.floor(vv / 3) % 3)
        ex2  = vv % 3
        isLive = vv == liveIdx
''')
    s = rep(s, '''            table.cell(rpt, 9, i2 + 2, str.tostring(Ns2) + " / " + (ks2 <= 0 ? "不要求" : str.tostring(ks2, "#.#")), text_size = sizeV, bgcolor = rBg)
''', '''            table.cell(rpt, 9, i2 + 2, str.tostring(wn2) + " / " + (ex2 == 1 ? "追蹤" : ex2 == 2 ? "止賺" : "現行"), text_size = sizeV, bgcolor = rBg)
''')
    s = rep(s, '''    table.cell(rpt, 7, nShow + 2, "現行 買N" + str.tostring(fadeBuy) + "k" + str.tostring(kBuy, "#.#") + " 賣N" + str.tostring(fadeSell) + "k" + str.tostring(kSell, "#.#") + " → " + (liveRank > 0 ? "第 " + str.tostring(liveRank) + "/81" : "不在網格 (k∈1/1.5/2, N∈1-3)"), text_size = sizeV, bgcolor = sBg, text_halign = text.align_left)
''', '''    table.cell(rpt, 7, nShow + 2, (autoOn ? "自動調參 今日 " : "現行 ") + liveTxt + " → 全期第 " + (liveRank > 0 ? str.tostring(liveRank) + "/81" : "- (不在網格)") + " · 賣N" + str.tostring(fadeSell) + "k" + str.tostring(kSell, "#.#") + " 固定 · " + (autoOn ? tuneNote : "自動調參關"), text_size = sizeV, bgcolor = sBg, text_halign = text.align_left)
''')
    s = rep(s, '"M1 k" + str.tostring(kBuy, "#.#") + "/N" + str.tostring(fadeBuy) + " P" + str.tostring(depthPctl, "#")', '"M1 k" + str.tostring(liveKb, "#.#") + "/N" + str.tostring(liveNb) + " P" + str.tostring(depthPctl, "#")')
    s = rep(s, '" · 窗" + str.tostring(matchWin) + "/" + str.tostring(matchWinS), text_size = sizeV)', '" · 窗" + str.tostring(liveWin) + "/" + str.tostring(matchWinS) + (autoOn ? " · 自動調參" : ""), text_size = sizeV)')
    s = rep(s, 'str.tostring(kEff, "#.##"), str.tostring(kBuy, "#.#"), fadeBuy, str.tostring(kSell, "#.#"), fadeSell, str.tostring(maxRise, "#.##")', 'str.tostring(kEff, "#.##"), str.tostring(liveKb, "#.#"), liveNb, str.tostring(kSell, "#.#"), fadeSell, str.tostring(maxRise, "#.##")')
    s = rep(s, '(含 S-M1&M2 / M2區結束 / SL / EOD / 午休 / 窗口結束)', '(含 S-M1&M2 / M2區結束 / SL / 追蹤止損 / 止賺 / EOD / 午休 / 韓股收市 / 窗口結束)')
    s = rep(s, '另有 可買區結束平倉 / 15:58 收市強平 / 可選 11:58 午休前平倉 / 可選固定止損。', '另有 可買區結束平倉 / 15:58 收市強平 / 可選 11:58 午休前平倉 / 可選固定止損 / 自動調參選到的追蹤止損或止賺。')
    s = rep(s, '"期內無交易 — 檢查 ⑤ 時段 / margin_long = 0 / ④ 上下界 / ④c 匹配窗口與可買區規則"', '"期內無交易 — 檢查 ⑤ 時段 (韓股時段限制) / margin_long = 0 / ④ 上下界 / ④c 匹配窗口與可買區規則 / ⑨b 自動調參"')
    assert 'array.get(KG,' not in s and 'vAgeS' not in s and 'matchWinS' in s
    return s
