# -*- coding: utf-8 -*-
"""build_r92.py — R9.2: 由 R9.1 兩支生成: 回測周期 三個月 → 十二個月 (365 天 / 252 個交易日 / 指定日期 2025-09-19 → 2026-09-19); 買賣規則完全不變。
   附帶: 方式 A 的 maxval 250 → 500, 交易日往回數的保護上限 400 → 600 天 (252 個交易日 ≈ 353 個日曆日, 舊上限會截斷)。
用法: STAMP="09月28日; 10:00" python3 build_r92.py   (需要 R9.1 兩支已存在)"""
import glob, io, os, re
from flatten_pine import verify
import make_paste_page

STAMP = os.environ['STAMP']
SRC_MAIN = glob.glob('R9.1_TV-1M-dashboard_(mode 2,4)_*.pine')[0]
SRC_PANE = glob.glob('R9.1_TV-1M-RSI-winrate_(mode 2,4)_*.pine')[0]
NAME_MAIN = f'R9.2_TV-1M-dashboard_(mode 2,4)_({STAMP})'
NAME_PANE = f'R9.2_TV-1M-RSI-winrate_(mode 2,4)_({STAMP})'


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, n, old[:100])
    return s.replace(old, new)


def rename(src, new_name):
    old = re.search(r'^(?:strategy|indicator)\("([^"]+)"', src, re.M).group(1)
    assert src.count(old) == 4
    return src.replace(old, new_name)


TIP_OLD_START = 'tooltip = "1 分 K 可載入的根數受 TradingView 方案限制'
TIP365 = ('1 分 K 可載入的根數受 TradingView 方案限制 (免費約 5,000 根 ≈ 13 個美股交易日; Premium 約 20,000 根 ≈ 2 個半月; Ultimate 約 40,000 根 ≈ 5 個月)。'
          '十二個月 1 分 K 約 98,000 根, 任何方案的圖表都載不齊, 直接掛在圖上只會回測到圖表最左邊那一根為止 (報表標題會顯示實際起始日); '
          '要跑滿十二個月請用 Strategy Tester 的 Deep Backtesting (Premium 以上) 指定日期範圍, 或改「指定日期」分成 4–5 段各跑約 2 個半月再加總。')

# ═══ 主策略 ═══
s = io.open(SRC_MAIN, encoding='utf-8').read()
s = rename(s, NAME_MAIN)
s = rep(s, 'R9.1 主策略 (畫在主圖; R9 改三個月回測): 只做多', 'R9.2 主策略 (畫在主圖; R9 改十二個月回測): 只做多')
s = rep(s, ' · 1 分鐘 · 三個月回測 · Pine v6', ' · 1 分鐘 · 十二個月回測 · Pine v6')
s = rep(s, '① 回測期間 (R9.1: 預設最近 90 天 = 三個月)', '① 回測期間 (R9.2: 預設最近 365 天 = 十二個月)')
s = rep(s, '"回測期間方式 (三選一; 本版預設三個月)"', '"回測期間方式 (三選一; 本版預設十二個月)"')
s = rep(s, '最近 N 個交易日 (本版預設 N=63 ≈ 三個月)', '最近 N 個交易日 (本版預設 N=252 ≈ 十二個月)')
s = rep(s, 'tradDays   = input.int(63, "方式 A · 最近 N 個交易日 (由圖表最後一根 K 往回數, 跳週六日; 63 ≈ 三個月)", minval = 1, maxval = 250,',
           'tradDays   = input.int(252, "方式 A · 最近 N 個交易日 (由圖表最後一根 K 往回數, 跳週六日; 252 ≈ 十二個月)", minval = 1, maxval = 500,')
s = rep(s, 'lookbackD  = input.int(90, "方式 B · 最近 N 天 (日曆, 由現在時間往回; 本版預設 90 = 三個月)"',
           'lookbackD  = input.int(365, "方式 B · 最近 N 天 (日曆, 由現在時間往回; 本版預設 365 = 十二個月)"')
i = s.index(TIP_OLD_START); j = s.index('"', i + len('tooltip = "'))
s = s[:i] + 'tooltip = "' + TIP365 + s[j:]
s = rep(s, 'timestamp("19 Jun 2026 00:00 -0400")', 'timestamp("19 Sep 2025 00:00 -0400")')
s = rep(s, '    while cntD < tradDays and guardD < 400', '    while cntD < tradDays and guardD < 600   // R9.2: 252 個交易日 ≈ 353 個日曆日, 保護上限放寬到 600')
s = rep(s, '"買 (R9.1, 只做多):', '"買 (R9.2, 只做多):')
s = rep(s, '"賣 (R9.1): 紅柱立即平倉;', '"賣 (R9.2): 紅柱立即平倉;')
s = rep(s, '"R9.1 M2 RSI14 "', '"R9.2 M2 RSI14 "')
s = rep(s, '"===== R9.1 (三個月) 只做多', '"===== R9.2 (十二個月) 只做多')
assert '三個月' not in s and 'R9.1' not in s, [l[:80] for l in s.split('\n') if '三個月' in l or 'R9.1' in l]
f_main = NAME_MAIN.replace(':', '.') + '.pine'
io.open(f_main, 'w', encoding='utf-8', newline='\n').write(s)
print('wrote', f_main, s.count('\n'), 'lines; verify:', verify(s) or 'PASS')

# ═══ 副圖 ═══
p = io.open(SRC_PANE, encoding='utf-8').read()
p = rename(p, NAME_PANE)
p = rep(p, '  ·  R9.1 副圖 (回測期間預設三個月, 與主策略一致):', '  ·  R9.2 副圖 (回測期間預設十二個月, 與主策略一致):')
p = rep(p, '"回測期間方式 (三選一; 預設三個月)"', '"回測期間方式 (三選一; 預設十二個月)"')
p = rep(p, 'tradDays   = input.int(63, "方式 A · 最近 N 個交易日 (63 ≈ 三個月)", minval = 1, maxval = 250,',
           'tradDays   = input.int(252, "方式 A · 最近 N 個交易日 (252 ≈ 十二個月)", minval = 1, maxval = 500,')
p = rep(p, 'lookbackD  = input.int(90, "方式 B · 最近 N 天 (日曆; 90 = 三個月)"', 'lookbackD  = input.int(365, "方式 B · 最近 N 天 (日曆; 365 = 十二個月)"')
p = rep(p, 'timestamp("19 Jun 2026 00:00 -0400")', 'timestamp("19 Sep 2025 00:00 -0400")')
p = rep(p, '    while cntD < tradDays and guardD < 400', '    while cntD < tradDays and guardD < 600')
p = rep(p, '"R9.1 · 模式 2 RSI"', '"R9.2 · 模式 2 RSI"')
assert '三個月' not in p and 'R9.1' not in p
f_pane = NAME_PANE.replace(':', '.') + '.pine'
io.open(f_pane, 'w', encoding='utf-8', newline='\n').write(p)
print('wrote', f_pane, p.count('\n'), 'lines; verify:', verify(p) or 'PASS')

for fn, html, eyebrow in ((f_main, 'paste_R9.2-dashboard.html', 'R9.2 · 十二個月回測 · 只做多 · 模式 2 + 4 主策略 (主圖) · 1 分鐘日內策略 (市場預設 美股)'),
                          (f_pane, 'paste_R9.2-RSI-winrate.html', 'R9.2 · 模式 2 + 模式 4 合併副圖 (純顯示; 十二個月窗口)')):
    make_paste_page.make(fn, html)
    h = io.open(html, encoding='utf-8').read()
    h = h.replace('1 分鐘日內策略 (市場預設 美股, Inputs 可切港股)', eyebrow)
    io.open(html, 'w', encoding='utf-8', newline='\n').write(h)
