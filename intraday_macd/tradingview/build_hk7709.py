# -*- coding: utf-8 -*-
"""build_hk7709.py — 由 SOXL 版三支發佈檔 (TV-1M-*_(09月20日; 21.59)) 產出港股 7709 版三支:
   HK7709-1m-dashboard_(mode 1-4)_(MM月DD日; HH:MM) / HK7709-1m-RSI-mode2_(…) / HK7709-1m-winrate-mode4_(…)

規則邏輯 (模式 1-4、四模式同時買、出場順序、81 組掃描) 與 SOXL 版完全相同, 只改:
  ⑤ 市場預設 港股 (0930-1200,1300-1600 · Asia/Hong_Kong, 有午休) · 午休前 11:50 起 / 收市前 15:45 起不開新倉 · 15:58 強平 · 可選 11:58 午休前平倉
  ② 港股整手下單 (每手股數向下取整; 不足一手不下單) · 手續費 0.05%/邊 (無印花稅: ETF / 槓桿反向產品豁免; 普通股票請自行加 0.1%)
  ① 指定日期的時區 +0800 · 主圖摘要多一個「商品 ≠ 7709」紅字警告 · 所有 SOXL / 美股 字眼

用法: STAMP="09月22日; 10:30" python3 build_hk7709.py
"""
import io, os, re, sys
from flatten_pine import verify
import make_paste_page
from build_hist_cross_rsi import HEADER, END_TAG

STAMP = os.environ['STAMP']
SRC_MAIN = 'TV-1M-dashboard_(mode 1-4)_(09月20日; 21.59).pine'
SRC_RSI  = 'TV-1M-RSI-mode2_(09月20日; 21.59).pine'
SRC_M4   = 'TV-1M-winrate-mode4_(09月20日; 21.59).pine'
OLD_STAMP = '09月20日; 21:59'
BAR = '// ' + '═' * 79 + '\n'


def body_of(path):
    lines = io.open(path, encoding='utf-8').read().rstrip('\n').split('\n')
    v = next(i for i, l in enumerate(lines) if l.startswith('//@version'))
    body = [l for l in lines[v:] if not l.startswith('// ═══ END OF FILE')]
    while body and body[-1].strip() == '':
        body.pop()
    return '\n'.join(body)


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, n, old[:80])
    return s.replace(old, new)


# ───────────────────────────── 主策略 ─────────────────────────────
name_main = f'HK7709-1m-dashboard_(mode 1-4)_({STAMP})'
s = body_of(SRC_MAIN)
s = s.replace(f'TV-1M-dashboard_(mode 1-4)_({OLD_STAMP})', name_main)
assert 'TV-1M-dashboard_(mode 1-4)_(' not in s
s = rep(s, 'commission_value = 0.03,', 'commission_value = 0.05,')
# ① 指定日期時區
s = rep(s, 'timestamp("19 Aug 2026 00:00 -0400")', 'timestamp("22 Aug 2026 00:00 +0800")')
s = rep(s, 'timestamp("19 Sep 2026 23:59 -0400")', 'timestamp("22 Sep 2026 23:59 +0800")')
s = rep(s, '免費約 5,000 根 ≈ 13 個美股交易日; Premium 約 20,000 根 ≈ 2 個半月)。一個月 1 分 K 約 8,200 根,',
           '免費約 5,000 根 ≈ 15 個港股交易日 (港股每日 330 根 1 分 K); Premium 約 20,000 根 ≈ 3 個月)。一個月 1 分 K 約 7,000 根,')
# ② 港股整手
s = rep(s, 'fixedQty  = input.float(1000,   "固定股數", step = 100,  group = gSZ, display = display.none)\n',
           'fixedQty  = input.float(1000,   "固定股數", step = 100,  group = gSZ, display = display.none)\n'
           'lotSize   = input.int(100, "每手股數 (港股整手下單: 股數向下取整到每手的倍數; 0 或 1 = 不取整)", minval = 0, group = gSZ, tooltip = "港股以「手」為單位, 7709 的每手股數請在 TradingView 報價欄 / 港交所網頁核對後填入 (常見 100 / 200 / 500 / 1000)。全部本金 = 本金 ÷ 收盤價 再向下取整到整手; 不足一手不下單。", display = display.none)\n')
s = rep(s, '// ※ 本金 100,000 寫在 strategy() 的 initial_capital;', '// ※ 本金 100,000 (HKD) 寫在 strategy() 的 initial_capital;')
s = rep(s, 'qty     = sizeMode == "全部本金" ? strategy.equity / close : sizeMode == "固定金額" ? fixedCash / close : fixedQty\n',
           'qtyRaw  = sizeMode == "全部本金" ? strategy.equity / close : sizeMode == "固定金額" ? fixedCash / close : fixedQty\n'
           'qty     = lotSize > 1 ? math.floor(qtyRaw / lotSize) * lotSize : qtyRaw   // 港股整手: 向下取整到每手股數的倍數\n')
s = rep(s, 'if buySig and entryOK and strategy.position_size == 0   // 四模式同時出現買點\n'
           '    if sizeMode == "全部本金"\n'
           '        strategy.entry("L", strategy.long, comment = "BUY")          // 用 default_qty_type=percent_of_equity 100%\n'
           '    else\n'
           '        strategy.entry("L", strategy.long, qty = qty, comment = "BUY")\n',
           'if buySig and entryOK and strategy.position_size == 0 and qty > 0   // 四模式同時出現買點 (港股: 不足一手不下單)\n'
           '    strategy.entry("L", strategy.long, qty = qty, comment = "BUY")     // 股數已向下取整到整手 (全部本金 = 本金 ÷ 收盤價 取整手)\n')
# ⑤ 港股時段 + 午休
s = rep(s, 'mktPreset = input.string("美股", "市場預設 (一鍵套用時段+時區)"', 'mktPreset = input.string("港股", "市場預設 (一鍵套用時段+時區; 本版預設 港股)"')
s = rep(s, 'sessCust  = input.session("0930-1600", "自訂: 交易時段"', 'sessCust  = input.session("0930-1200,1300-1600", "自訂: 交易時段"')
s = rep(s, 'tzCust    = input.string("America/New_York", "自訂: 時區"', 'tzCust    = input.string("Asia/Hong_Kong", "自訂: 時區"')
s = rep(s, 'noEntry   = input.session("1545-1600", "收市前不開新倉時段", group = gS, display = display.none)\n'
           'eodSess   = input.session("1558-1600", "強制平倉時段 (不留隔夜倉)", group = gS, display = display.none)\n',
           'noEntry   = input.session("1150-1200,1545-1600", "不開新倉時段 (港股: 午休前 11:50 起 + 收市前 15:45 起)", group = gS, tooltip = "午休 12:00-13:00 沒有 K 線, 11:50 起不開新倉以免剛買入就要過午休; 13:00 起照常。", display = display.none)\n'
           'eodSess   = input.session("1558-1600", "強制平倉時段 (不留隔夜倉; 港股 16:00 收市, 15:58 收盤掛單 15:59 開盤成交)", group = gS, display = display.none)\n'
           'lunchFlat = input.bool(false, "午休前平倉 (11:58 平掉, 不留倉過午休; 預設關 = 持倉過午休)", group = gS, tooltip = "港股 12:00-13:00 午休。開啟後 11:58 那根收盤掛市價單, 11:59 開盤成交, 出場原因 午休。關閉 = 倉位過午休, 13:00 後照常按四模式 / 模式 2 區間規則出場。", display = display.none)\n'
           'lunchSess = input.session("1158-1200", "午休前平倉時段 (只在開啟午休前平倉時用)", group = gS, display = display.none)\n')
s = rep(s, 'eodBar    = isIntra and not na(time(timeframe.period, eodSess, tzStr))\n',
           'eodBar    = isIntra and not na(time(timeframe.period, eodSess, tzStr))\n'
           'lunchBar  = lunchFlat and isIntra and not na(time(timeframe.period, lunchSess, tzStr))   // 午休前平倉那一根 (預設關)\n')
s = rep(s, 'entryOK = inWindow and inSess and not blockNew and not eodBar\n', 'entryOK = inWindow and inSess and not blockNew and not eodBar and not lunchBar\n')
s = rep(s, 'if sellSig and not eodBar and strategy.position_size > 0\n', 'if sellSig and not eodBar and not lunchBar and strategy.position_size > 0\n')
s = rep(s, 'else if m2ExitOnEnd and m2BuyEnd and not eodBar and strategy.position_size > 0', 'else if m2ExitOnEnd and m2BuyEnd and not eodBar and not lunchBar and strategy.position_size > 0')
s = rep(s, 'if eodBar and strategy.position_size != 0\n    strategy.close_all(comment = "EOD")\n',
           'if eodBar and strategy.position_size != 0\n    strategy.close_all(comment = "EOD")\n'
           'if lunchBar and strategy.position_size != 0   // 午休前平倉 (⑤ 可選, 預設關)\n    strategy.close_all(comment = "午休")\n')
s = rep(s, 'or eodBar or not inWindow)', 'or eodBar or lunchBar or not inWindow)')
s = rep(s, '(含 S-M1&M2 / M2區結束 / SL / EOD / 窗口結束)', '(含 S-M1&M2 / M2區結束 / SL / EOD / 午休 / 窗口結束)')
s = rep(s, '另有 可買區結束平倉 / 15:58 收市強平 / 可選固定止損。', '另有 可買區結束平倉 / 15:58 收市強平 / 可選 11:58 午休前平倉 / 可選固定止損。')
# ④c 文字
s = rep(s, '固定 30 在 SOXL 1 分鐘圖上很少碰到 (RSI14 常常最低只到 32), 可買區會極少;', '固定 30 在 1 分鐘圖上未必碰得到 (視乎 7709 當月波幅, RSI14 有時最低只到 30 幾), 可買區會很少;')
# 商品警告
s = rep(s, 'tfOK = timeframe.period == tfExpect   //', 'symOK = syminfo.ticker == "7709"     // 本版為港股 7709 設計; 開錯商品時主圖摘要紅字提示 (不影響運算)\ntfOK = timeframe.period == tfExpect   //')
s = rep(s, 'warnTxt = not tfOK ? "⚠ 圖表週期 " + timeframe.period + " ≠ 設定 " + tfExpect : barsTot == 0 ?',
           'warnTxt = not tfOK ? "⚠ 圖表週期 " + timeframe.period + " ≠ 設定 " + tfExpect : not symOK ? "⚠ 商品 " + syminfo.ticker + " ≠ 7709" : barsTot == 0 ?')
s = rep(s, 'warnCol = (not tfOK or barsTot == 0) ? color.red', 'warnCol = (not tfOK or not symOK or barsTot == 0) ? color.red')
s = rep(s, '"===== 四模式回測 (柱到界+RSI區+金叉+EMA9) {0}', '"===== 港股 7709 四模式回測 (柱到界+RSI區+金叉+EMA9) {0}')
assert 'SOXL' not in s and '-0400' not in s, 'SOXL / -0400 殘留'

hdr = HEADER
hdr = rep(hdr, '主策略 (dashboard): 模式 1 MACD 柱到上下界', '港股 7709 · 主策略 (dashboard): 模式 1 MACD 柱到上下界')
hdr = rep(hdr, '另有 可買區結束平倉 / 15:58 收市強平 / 可選固定止損\n', '另有 可買區結束平倉 / 15:58 收市強平 / 可選 11:58 午休前平倉 / 可選固定止損\n')
hdr = rep(hdr, 'EOD (15:58 強平) / SL (止損) / 窗口結束', 'EOD (15:58 強平) / 午休 (11:58 午休前平倉, ⑤ 可選, 預設關) / SL (止損) / 窗口結束')
hdr = rep(hdr, '※ 1 分 K 一個月約 8,200 根,', '※ 港股 1 分 K 一個月約 7,000 根 (每日 330 根),')
hdr = rep(hdr, '//  【共用規則】只做多 · 全部本金 · 收盤確認下一根開盤成交 · 手續費 0.03%/邊 + 滑點 2 tick · 美股 09:30-16:00 NY · 15:45 後不開新倉 · 15:58 強平\n',
                '//  【共用規則】只做多 · 全部本金 (港股整手, ② 每手股數) · 收盤確認下一根開盤成交 · 手續費 0.05%/邊 (佣金 + 交易徵費, 不含印花稅: ETF / 槓桿反向產品豁免, 普通股票請加 0.1%) + 滑點 2 tick\n'
                '//   港股 09:30-12:00, 13:00-16:00 HKT (⑤ 市場預設 港股, 有午休) · 午休前 11:50 起 / 收市前 15:45 起不開新倉 · 15:58 強平 · 午休前平倉 ⑤ 可選 (預設關 = 持倉過午休)\n')
hdr = rep(hdr, '圖表切【SOXL · 1 分鐘】', '圖表切【HKEX:7709 · 1 分鐘】(開錯商品主圖摘要會紅字提示)')
hdr = rep(hdr, '版本戳 TV-1M-dashboard_(mode 1-4)_(MM月DD日; HH:MM)', '版本戳 HK7709-1m-dashboard_(mode 1-4)_(MM月DD日; HH:MM)')
hdr = rep(hdr, 'TV-1M-RSI-mode2', 'HK7709-1m-RSI-mode2', hdr.count('TV-1M-RSI-mode2'))
hdr = rep(hdr, 'TV-1M-winrate-mode4', 'HK7709-1m-winrate-mode4', hdr.count('TV-1M-winrate-mode4'))
assert 'TV-1M' not in hdr and 'SOXL' not in hdr
n = hdr.count('\n') + s.count('\n') + 1 + 1
out = hdr.format(name=name_main, n=n) + s + '\n' + END_TAG.format(name=name_main, n=n) + '\n'
assert out.count('\n') == n
f_main = name_main.replace(':', '.') + '.pine'
io.open(f_main, 'w', encoding='utf-8', newline='\n').write(out)
print('wrote', f_main, n, 'lines; verify:', verify(out) or 'PASS')


# ───────────────────────────── 副圖 ─────────────────────────────
def pane(src, old_prefix, new_prefix, header_body):
    name = f'{new_prefix}({STAMP})'
    body = body_of(src)
    body = body.replace(f'{old_prefix}({OLD_STAMP})', name)
    assert old_prefix not in body
    body = rep(body, 'timestamp("19 Aug 2026 00:00 -0400")', 'timestamp("22 Aug 2026 00:00 +0800")')
    body = rep(body, 'timestamp("19 Sep 2026 23:59 -0400")', 'timestamp("22 Sep 2026 23:59 +0800")')
    hb = header_body.rstrip('\n').split('\n')
    n_total = 2 + len(hb) + 1 + body.count('\n') + 1 + 1
    tail = f'//  四處必須一致: 標題 = shorttitle = 檔名 = TradingView 腳本名稱 (結尾的 ")" 不可漏); 本檔共 {n_total} 行, 最後一行是 END OF FILE\n'
    o = BAR + f'//  {name}  ·  ' + hb[0] + '\n' + ''.join('//  ' + l + '\n' for l in hb[1:]) + tail + BAR + body + '\n' + END_TAG.format(name=name, n=n_total) + '\n'
    assert o.count('\n') == n_total, (o.count('\n'), n_total)
    fn = name.replace(':', '.') + '.pine'
    io.open(fn, 'w', encoding='utf-8', newline='\n').write(o)
    print('wrote', fn, n_total, 'lines; verify:', verify(o) or 'PASS')
    return fn


rsi_hdr = '''港股 7709 · 模式 2 (RSI 14/28 可買區 / 可賣區) 專用副圖 · 配合主策略 HK7709-1m-dashboard_(mode 1-4) 一起掛
模式 2 是「狀態」(像模式 4), 不形成絕對買賣點: 下界 / 上界 = 最近 120 根 RSI14 的第 10 / 90 百分位 (可切固定 30/70)
進入可買區 = RSI14 梯度由 ≤0 轉 >0 (谷底在前一根) 且 谷底到達或低於下界; 一直持續直到「昇不上」= RSI14 跌破 RSI28, 或 RSI14 跌破進區時的谷底 (② 可改為只看 RSI14 / RSI28 轉勢); 每個交易日開始時清空
進入可賣區 = 相反 (梯度由 ≥0 轉 <0 且 峰頂到達或高於上界), 結束條件相反; 進入另一區直接取代現區; 午休 12:00-13:00 沒有 K 線, 區間狀態直接跨過午休
顯示: 深棕粗線 RSI14 · 橙細線 RSI28 · 綠/紅細線 = 下界/上界 · 底色 淺藍 = 可買區 / 淺紅 = 可賣區 · ▲ 淺藍 = 進可買區 · ▼ 淺紅 = 進可賣區 · × = 區間結束 · 圓點 = 快慢線交叉
② 的 快慢線長度 / 下上界方式 / 百分位 / 到界回看根數 / 區間結束規則 / 每日清空 必須與主策略 ④c 一致; 這支不下單; plot 的 title 必須是常數字串'''
m4_hdr = '''港股 7709 · 模式 4 (EMA9 斜率) 專用副圖 · 配合主策略 HK7709-1m-dashboard_(mode 1-4) 一起掛
模式 4 唯一條件: EMA9 現值比 N 根前高 (預設 N = 1, ② 可改) = 趨勢向上 → 輸出可以買入; 斜率為負 = 不可
顯示: 斜率柱 (% 表示; 綠 >0 可買 / 紅 <0 不可) + 0 軸 + 底色; 由不可轉可買的那一根標「可買」; 右上統計窗內向上 K 數比例
② 的 EMA 長度 / 斜率根數必須與主策略 ④e 一致; 這支不下單, 真正的閘門在主策略 ④e (買入需四模式同時)'''
f_rsi = pane(SRC_RSI, 'TV-1M-RSI-mode2_', 'HK7709-1m-RSI-mode2_', rsi_hdr)
f_m4  = pane(SRC_M4,  'TV-1M-winrate-mode4_', 'HK7709-1m-winrate-mode4_', m4_hdr)

# ───────────────────────────── 貼上工具網頁 ─────────────────────────────
for fn, html in ((f_main, 'paste_HK7709-1m-dashboard.html'), (f_rsi, 'paste_HK7709-1m-RSI-mode2.html'), (f_m4, 'paste_HK7709-1m-winrate-mode4.html')):
    make_paste_page.make(fn, html)
    h = io.open(html, encoding='utf-8').read()
    h = rep(h, '1 分鐘日內策略 (市場預設 美股, Inputs 可切港股)', '港股 7709 · 1 分鐘日內策略 (市場預設 港股, 有午休)')
    h = rep(h, '開要測的標的 (例如 AMEX:SOXL)。', '開 HKEX:7709 (開錯商品主圖摘要會紅字提示)。')
    io.open(html, 'w', encoding='utf-8', newline='\n').write(h)
