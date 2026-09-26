# -*- coding: utf-8 -*-
"""build_r2_mode24.py — 由 SOXL 版三支 (TV-1M-*_(09月20日; 21.59)) 產出 R2 變體 (只用模式 2 + 4 決定買賣):
   TV-1M-dashboard_(mode 1-4)_R2_mode2_4only_(MM月DD日; HH:MM) / TV-1M-RSI-mode2_R2_mode2_4only_(…) / TV-1M-winrate-mode4_R2_mode2_4only_(…)
用法: STAMP="09月26日; 10:00" python3 build_r2_mode24.py
"""
import io, os
from flatten_pine import verify
import make_paste_page
from build_hist_cross_rsi import HEADER, END_TAG
import patch_r2_mode24

STAMP = os.environ['STAMP']
SRC_MAIN = 'TV-1M-dashboard_(mode 1-4)_(09月20日; 21.59).pine'
SRC_RSI  = 'TV-1M-RSI-mode2_(09月20日; 21.59).pine'
SRC_M4   = 'TV-1M-winrate-mode4_(09月20日; 21.59).pine'
OLD_STAMP = '09月20日; 21:59'
SUF = 'R2_mode2_4only_'
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


name_main = f'TV-1M-dashboard_(mode 1-4)_{SUF}({STAMP})'
s = body_of(SRC_MAIN)
s = s.replace(f'TV-1M-dashboard_(mode 1-4)_({OLD_STAMP})', name_main)
assert 'TV-1M-dashboard_(mode 1-4)_(' not in s
s = patch_r2_mode24.apply(s)

hdr = HEADER
hdr = rep(hdr, '主策略 (dashboard): 模式 1 MACD 柱到上下界 + 模式 2 RSI 14/28 可買區 + 模式 3 敏感 MACD 金叉 + 模式 4 EMA9 斜率向上',
               'R2 主策略 (dashboard): 只用 模式 2 RSI 14/28 可買區 + 模式 4 EMA9 斜率 決定買賣 (模式 1 柱到界 / 模式 3 金叉 預設關閉, ④f 可加回)')
hdr = rep(hdr, '//  【本版規則 — 四個模式, 兩條合格條件】\n',
               '//  【R2 規則 — 只用模式 2 + 4】買 = 模式 2 處於可買區 且 模式 4 EMA9 向上, 且本根至少一個剛出現 (RSI14 剛轉勢進入可買區, 或 EMA9 剛轉向上)\n'
               '//   賣 (④f 可選, 預設對稱規則) = 模式 2 處於可賣區 且 EMA9 向下, 且本根至少一個剛出現 (剛進可賣區 / EMA9 剛轉向下); 另可選 剛進可賣區即賣 / 只靠可買區結束+收市 / 舊規則 (模式 1 賣訊在可賣區)\n'
               '//   持倉中可買區結束一律平倉 (M2區結束) · 15:58 收市強平 · 可選固定止損。模式 1 與 3 仍在副圖顯示 (柱、上下界、9/26/9 線與金叉), 但 ④f 預設不參與買賣; 打開開關即恢復四模式\n'
               '//  【原四模式定義 (保留, 供 ④f 加回時參考)】\n')
hdr = rep(hdr, '合格賣出 = 模式 1 賣訊 (昇到上界後淺綠 N 根完成, 有效 5 根) 在模式 2 可賣區內 (本根至少一個剛出現); 另有 可買區結束平倉 / 15:58 收市強平 / 可選固定止損\n',
               '合格賣出 (舊規則, R2 只在 ④f 選「舊規則」時用) = 模式 1 賣訊在模式 2 可賣區內; R2 預設賣 = M2 可賣區 + M4 向下; 另有 可買區結束平倉 / 15:58 收市強平 / 可選固定止損\n')
hdr = rep(hdr, 'S-M1&M2 (M1 賣訊在可賣區) / M2區結束 (可買區結束平倉)', 'S-M2&M4 (R2 預設: M2 可賣區 + M4 向下) 或 S-M2賣區 / S-M1&M2 (④f 選的賣法) / M2區結束 (可買區結束平倉)')
hdr = rep(hdr, '//  【參數掃描 (⑨)】81 組 (買N×買k × 賣N×賣k, k∈1/1.5/2) 每一組都套上同一套四模式買 (M1&M3 匹配 + M2 可買區 + M4 向上) / M1 賣訊在可賣區 + 可買區結束平倉 的規則, 排名結果可直接填回 ④\n',
               '//  【參數掃描 (⑨, R2)】81 組 = 模式 2 下界百分位∈5/10/20 (上界 = 100 − 下界) × 可買區結束規則∈破慢線或谷底/RSI14 轉下/RSI28 轉下 × 模式 4 斜率根數∈1/3/5 × 賣法∈M2&M4/進賣區即賣/只靠區結束, 每組都是 R2 規則 + 可買區結束平倉 + EOD, 最佳組合可填回 ④c / ④e / ④f\n')
hdr = rep(hdr, '版本戳 TV-1M-dashboard_(mode 1-4)_(MM月DD日; HH:MM)', '版本戳 TV-1M-dashboard_(mode 1-4)_R2_mode2_4only_(MM月DD日; HH:MM)')
hdr = rep(hdr, 'TV-1M-RSI-mode2', 'TV-1M-RSI-mode2_R2_mode2_4only', hdr.count('TV-1M-RSI-mode2'))
hdr = rep(hdr, 'TV-1M-winrate-mode4', 'TV-1M-winrate-mode4_R2_mode2_4only', hdr.count('TV-1M-winrate-mode4'))
n = hdr.count('\n') + s.count('\n') + 1 + 1
out = hdr.format(name=name_main, n=n) + s + '\n' + END_TAG.format(name=name_main, n=n) + '\n'
assert out.count('\n') == n
f_main = name_main.replace(':', '.') + '.pine'
io.open(f_main, 'w', encoding='utf-8', newline='\n').write(out)
print('wrote', f_main, n, 'lines; verify:', verify(out) or 'PASS')


def pane(src, old_prefix, new_prefix, header_body):
    name = f'{new_prefix}({STAMP})'
    body = body_of(src)
    body = body.replace(f'{old_prefix}({OLD_STAMP})', name)
    assert f'{old_prefix}(' not in body
    hb = header_body.rstrip('\n').split('\n')
    n_total = 2 + len(hb) + 1 + body.count('\n') + 1 + 1
    tail = f'//  四處必須一致: 標題 = shorttitle = 檔名 = TradingView 腳本名稱 (結尾的 ")" 不可漏); 本檔共 {n_total} 行, 最後一行是 END OF FILE\n'
    o = BAR + f'//  {name}  ·  ' + hb[0] + '\n' + ''.join('//  ' + l + '\n' for l in hb[1:]) + tail + BAR + body + '\n' + END_TAG.format(name=name, n=n_total) + '\n'
    assert o.count('\n') == n_total, (o.count('\n'), n_total)
    fn = name.replace(':', '.') + '.pine'
    io.open(fn, 'w', encoding='utf-8', newline='\n').write(o)
    print('wrote', fn, n_total, 'lines; verify:', verify(o) or 'PASS')
    return fn


rsi_hdr = '''R2 · 模式 2 (RSI 14/28 可買區 / 可賣區) 專用副圖 · 配合主策略 TV-1M-dashboard_(mode 1-4)_R2_mode2_4only 一起掛 (R2 買賣只用模式 2 + 4)
模式 2 是「狀態」, 不形成絕對買賣點: 下界 / 上界 = 最近 120 根 RSI14 的第 10 / 90 百分位 (可切固定 30/70)
進入可買區 = RSI14 梯度由 ≤0 轉 >0 (谷底在前一根) 且 谷底到達或低於下界; 一直持續直到「昇不上」= RSI14 跌破 RSI28, 或 RSI14 跌破進區時的谷底 (② 可改為只看 RSI14 / RSI28 轉勢); 每個交易日開始時清空
進入可賣區 = 相反 (梯度由 ≥0 轉 <0 且 峰頂到達或高於上界), 結束條件相反; 進入另一區直接取代現區
R2 的整體買點 = 進可買區 (▲) 或 EMA9 剛轉向上 時兩者都成立; 整體賣點 = 進可賣區 (▼) 或 EMA9 剛轉向下 時兩者都成立; 可買區結束 (×) 持倉一律平倉
顯示: 深棕粗線 RSI14 · 橙細線 RSI28 · 綠/紅細線 = 下界/上界 · 底色 淺藍 = 可買區 / 淺紅 = 可賣區 · ▲ 淺藍 = 進可買區 · ▼ 淺紅 = 進可賣區 · × = 區間結束 · 圓點 = 快慢線交叉
② 的 快慢線長度 / 下上界方式 / 百分位 / 到界回看根數 / 區間結束規則 / 每日清空 必須與主策略 ④c 一致; 這支不下單; plot 的 title 必須是常數字串'''
m4_hdr = '''R2 · 模式 4 (EMA9 斜率) 專用副圖 · 配合主策略 TV-1M-dashboard_(mode 1-4)_R2_mode2_4only 一起掛 (R2 買賣只用模式 2 + 4)
模式 4 條件: EMA9 現值比 N 根前高 (預設 N = 1, ② 可改) = 趨勢向上 → 可以買入; 斜率為負 = 不可買, 且 (R2 預設賣法) 與模式 2 可賣區同時成立時形成賣點
顯示: 斜率柱 (% 表示; 綠 >0 可買 / 紅 <0 不可) + 0 軸 + 底色; 由不可轉可買的那一根標「可買」; 右上統計窗內向上 K 數比例
② 的 EMA 長度 / 斜率根數必須與主策略 ④e 一致; 這支不下單, 真正的閘門在主策略 ④e / ④f'''
f_rsi = pane(SRC_RSI, 'TV-1M-RSI-mode2_', f'TV-1M-RSI-mode2_{SUF}', rsi_hdr)
f_m4  = pane(SRC_M4,  'TV-1M-winrate-mode4_', f'TV-1M-winrate-mode4_{SUF}', m4_hdr)
for fn, html in ((f_main, 'paste_TV-1M-dashboard-R2.html'), (f_rsi, 'paste_TV-1M-RSI-mode2-R2.html'), (f_m4, 'paste_TV-1M-winrate-mode4-R2.html')):
    make_paste_page.make(fn, html)
    h = io.open(html, encoding='utf-8').read()
    h = h.replace('1 分鐘日內策略 (市場預設 美股, Inputs 可切港股)', 'R2 · 只用模式 2 + 4 決定買賣 · 1 分鐘日內策略 (市場預設 美股)')
    io.open(html, 'w', encoding='utf-8', newline='\n').write(h)
