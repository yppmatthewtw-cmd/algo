# -*- coding: utf-8 -*-
"""build_r93.py — R9.3: 由 R9.2 兩支生成: 模式 4 「綠轉紅」敏感度調低約 10% (加入遲滯帶):
   綠→紅 不再是 斜率 ≤ 0 就轉, 而是 斜率 ≤ −(100 − 敏感度%)/100 × 最近 N 根平均斜率幅度 才轉 (預設 敏感度 90% → 帶寬 = 10% 平均幅度);
   紅→綠 仍是 斜率 > 0 (不變)。敏感度 100% = 與 R9.2 完全相同。主策略 / 掃描 81 組 / 副圖 三處同步。
用法: STAMP="09月28日; 10:00" python3 build_r93.py   (需要 R9.2 兩支已存在)"""
import glob, io, os, re
from flatten_pine import verify
import make_paste_page

STAMP = os.environ['STAMP']
SRC_MAIN = glob.glob('R9.2_TV-1M-dashboard_(mode 2,4)_*.pine')[0]
SRC_PANE = glob.glob('R9.2_TV-1M-RSI-winrate_(mode 2,4)_*.pine')[0]
NAME_MAIN = f'R9.3_TV-1M-dashboard_(mode 2,4)_({STAMP})'
NAME_PANE = f'R9.3_TV-1M-RSI-winrate_(mode 2,4)_({STAMP})'


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, n, old[:100])
    return s.replace(old, new)


def rename(src, new_name):
    old = re.search(r'^(?:strategy|indicator)\("([^"]+)"', src, re.M).group(1)
    assert src.count(old) == 4
    return src.replace(old, new_name)


def fix_count(src, old_n):
    n = src.count('\n')
    assert src.endswith('\n') and src.count(f'共 {old_n} 行') == 2, src.count(f'共 {old_n} 行')
    return src.replace(f'共 {old_n} 行', f'共 {n} 行'), n


SENS_INPUTS = [
    'm4RedSens = input.float(90, "R9.3 · 綠轉紅敏感度 % (100 = 斜率 ≤ 0 即轉紅, 同 R9.2; 90 = 減敏約 10%)", minval = 50, maxval = 100, step = 1, group = gR4, tooltip = "遲滯帶: 綠柱要轉紅, 斜率必須跌到 ≤ −(100 − 敏感度)/100 × 最近 N 根平均斜率幅度; 紅轉綠仍是斜率 > 0。90 = 斜率只是略為轉負 (幅度不到平均的 10%) 時仍算綠柱、不平倉; 100 = 與 R9.2 完全相同。", display = display.none)',
    'm4AbsLen  = input.int(20, "R9.3 · 平均斜率幅度取幾根 (遲滯帶的基準)", minval = 5, maxval = 200, group = gR4, display = display.none)',
]


def hyst_block(slope, avg, band, st, up, indent=''):
    """遲滯狀態機: slope > 0 → 綠; slope ≤ −band → 紅; 其間維持"""
    return [f'{avg} = ta.sma(math.abs({slope}), m4AbsLen)',
            f'{band} = (100.0 - m4RedSens) / 100.0 * {avg}',
            f'var bool {st} = false',
            f'if {slope} > 0',
            f'    {st} := true',
            f'else if {slope} <= -{band}',
            f'    {st} := false',
            f'{up} = {st}']


# ═══ 主策略 ═══
s = io.open(SRC_MAIN, encoding='utf-8').read()
s = rename(s, NAME_MAIN)
s = rep(s, 'R9.2 主策略 (畫在主圖; R9 改十二個月回測): 只做多', 'R9.3 主策略 (畫在主圖; 十二個月回測; R9.3 = 模式 4 綠轉紅減敏約 10%): 只做多')
s = rep(s, '//   模式 4 (④e): EMA9 斜率 > 0 = 綠柱 = 可買、可持倉; 斜率 ≤ 0 = 紅柱 = 不可持倉',
           '//   模式 4 (④e): EMA9 斜率 > 0 = 綠柱 = 可買、可持倉; R9.3: 綠柱要轉紅須斜率 ≤ −10% × 最近 20 根平均斜率幅度 (敏感度 90%, 可調; 100 = 斜率 ≤ 0 即轉紅, 同 R9.2); 紅柱 = 不可持倉')
L = s.split('\n')
i = next(k for k, l in enumerate(L) if l.startswith('m4ExitOnEnd = input.bool('))
L[i + 1:i + 1] = SENS_INPUTS
i = next(k for k, l in enumerate(L) if l.startswith('m4Up     = m4Slope > 0'))
L[i:i + 1] = hyst_block('m4Slope', 'm4SlopeAvg', 'm4RedBand', 'm4UpSt', 'm4Up     ') 
L[i + 7] = L[i + 7].rstrip() + '                                  // R9.3: 遲滯後的綠 / 紅 (敏感度 100 時 = m4Slope > 0)'
# 掃描 81 組: 1 / 3 / 5 根 各自的遲滯
i = next(k for k, l in enumerate(L) if l == 'm4UpA = m4Ema > m4Ema[1]')
assert L[i + 1] == 'm4UpB = m4Ema > m4Ema[3]' and L[i + 2] == 'm4UpC = m4Ema > m4Ema[5]'
new = ['// R9.3: 掃描各組 (1 / 3 / 5 根) 的斜率也套同一個遲滯帶']
for tag, k in (('A', 1), ('B', 3), ('C', 5)):
    new.append(f'm4Sl{tag} = m4Ema[{k}] == 0 ? 0.0 : (m4Ema - m4Ema[{k}]) / m4Ema[{k}] * 100.0')
    new += hyst_block(f'm4Sl{tag}', f'm4Av{tag}', f'm4Bd{tag}', f'm4St{tag}_', f'm4Up{tag}')
L[i:i + 3] = new
s = '\n'.join(L)
s = rep(s, '" 根) → " + (m4Up ? "向上, 可買" : "向下, 不可") + " · 窗內可買根數 "',
           '" 根; 綠轉紅減敏 " + str.tostring(100 - m4RedSens, "#") + "%, 帶 " + str.tostring(m4RedBand, "#.####") + "%) → " + (m4Up ? "綠, 可買" : "紅, 不可") + " · 窗內可買根數 "')
s = rep(s, '"買 (R9.2, 只做多):', '"買 (R9.3, 只做多):')
s = rep(s, '"賣 (R9.2): 紅柱立即平倉;', '"賣 (R9.3): 紅柱立即平倉 (減敏 " + str.tostring(100 - m4RedSens, "#") + "%);')
s = rep(s, '"R9.2 M2 RSI14 "', '"R9.3 M2 RSI14 "')
s = rep(s, '"===== R9.2 (十二個月) 只做多', '"===== R9.3 (十二個月; M4 綠轉紅減敏) 只做多')
s, n = fix_count(s, 629)
assert not [l for l in s.split('\n') if '"R9.2' in l or 'R9.2 M2' in l or 'R9.2_' in l], 'stale label'
f_main = NAME_MAIN.replace(':', '.') + '.pine'
io.open(f_main, 'w', encoding='utf-8', newline='\n').write(s)
print('wrote', f_main, n, 'lines; verify:', verify(s) or 'PASS')

# ═══ 副圖 ═══
p = io.open(SRC_PANE, encoding='utf-8').read()
p = rename(p, NAME_PANE)
p = rep(p, '  ·  R9.2 副圖 (回測期間預設十二個月, 與主策略一致):', '  ·  R9.3 副圖 (十二個月; 模式 4 綠轉紅減敏約 10%, 與主策略一致):')
L = p.split('\n')
i = next(k for k, l in enumerate(L) if l.startswith('m4Look   = input.int('))
L[i + 1:i + 1] = SENS_INPUTS
i = next(k for k, l in enumerate(L) if l.startswith('m4Up     = m4Slope > 0'))
L[i:i + 1] = hyst_block('m4Slope', 'm4SlopeAvg', 'm4RedBand', 'm4UpSt', 'm4Up     ')
L[i + 7] = L[i + 7].rstrip() + '                                  // R9.3 遲滯: 綠柱 = 可買、可持倉; 紅柱 = 立即平倉'
p = '\n'.join(L)
p = rep(p, '" 斜率 (" + str.tostring(m4Look) + " 根)", text_size = size.tiny, text_color = color.white, bgcolor = m4Up ? cM4Up : cM4Dn)',
           '" 斜率 (" + str.tostring(m4Look) + " 根; 綠轉紅減敏 " + str.tostring(100 - m4RedSens, "#") + "%)", text_size = size.tiny, text_color = color.white, bgcolor = m4Up ? cM4Up : cM4Dn)')
p = rep(p, '" · " + str.tostring(m4Slope, "#.####") + "%", text_size = size.tiny',
           '" · 斜率 " + str.tostring(m4Slope, "#.####") + "% / 轉紅門檻 −" + str.tostring(m4RedBand, "#.####") + "%", text_size = size.tiny')
p = rep(p, '"R9.2 · 模式 2 RSI"', '"R9.3 · 模式 2 RSI"')
p, n2 = fix_count(p, 208)
assert not [l for l in p.split('\n') if '"R9.2' in l or 'R9.2_' in l], 'stale label'
f_pane = NAME_PANE.replace(':', '.') + '.pine'
io.open(f_pane, 'w', encoding='utf-8', newline='\n').write(p)
print('wrote', f_pane, n2, 'lines; verify:', verify(p) or 'PASS')

for fn, html, eyebrow in ((f_main, 'paste_R9.3-dashboard.html', 'R9.3 · 模式 4 綠轉紅減敏 10% · 十二個月回測 · 只做多 · 模式 2 + 4 主策略 (主圖)'),
                          (f_pane, 'paste_R9.3-RSI-winrate.html', 'R9.3 · 模式 2 + 模式 4 合併副圖 (純顯示; 綠轉紅減敏 10%)')):
    make_paste_page.make(fn, html)
    h = io.open(html, encoding='utf-8').read()
    h = h.replace('1 分鐘日內策略 (市場預設 美股, Inputs 可切港股)', eyebrow)
    io.open(html, 'w', encoding='utf-8', newline='\n').write(h)
