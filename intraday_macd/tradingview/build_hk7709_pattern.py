# -*- coding: utf-8 -*-
"""build_hk7709_pattern.py — 由 hk7709_pattern_src.pine 產出 HK7709-10m-pattern_(MM月DD日; HH:MM).pine + 貼上工具網頁。
用法: STAMP="09月22日; 14:30" python3 build_hk7709_pattern.py
"""
import io, os
from flatten_pine import verify
import make_paste_page
from build_hist_cross_rsi import END_TAG

STAMP = os.environ['STAMP']
name = f'HK7709-mode5_1month-pattern({STAMP})'
BAR = '// ' + '═' * 79 + '\n'
hb = '''模式 5 · 港股 7709 過去一個月「平均的一天」曲線 (日內平均化 pattern) · 純顯示副圖, 不下單, 不參與四模式買賣 · 配合 HK7709-1m-dashboard_(mode 1-4) 一起掛
模式 5 標記: 每個交易日的開市 (09:30) 與收市 (16:00) 各畫一條粗黑直線並標時間; 開市到收市之間每半小時一條很淺的幼灰直線, 每整點以極小字標時間, 兩者都延伸到主圖 (② 可關); 14:30-16:00 HKT 黃色底色 (② 可改時段 / 關閉)\n直線由 TradingView 自動回收最舊的 (上限 500 條 ≈ 主圖+副圖各畫時約 19 個交易日; ② 關掉「延伸到主圖」可保留約 38 日)
做法: 每個交易日按港股時段切成固定格 (每格 = 圖表週期: 10 分鐘圖 = 15 + 18 格, 1 分鐘圖 = 150 + 180 格; ① 可指定), 每格的收盤 / 最高 / 最低 / 開盤 都換成「相對當日 09:30 開盤價的 %」,
      再把最近 21 個完整交易日 (① 可改) 同一格疊起來取 平均 / 中位數 / 標準差 / 升日比例; 只計「收市那一格有資料」的整日, 今日未收市不算入
畫面: 橙線 = 「平均的一天」曲線, 同一條 pattern 按對應時間格在每一個交易日重覆 (預設最近 60 日 + 今日, 今日未到的格畫在右邊; ① 可切成滾動 = 每日只用之前 N 日, 無前視) · 灰虛線 = 今日 ±1σ · 藍線 = 今日實際路徑 · 0% 虛線 = 當日開盤 · 上午 / 下午 底色
      預設只畫曲線; ① 可另外開: 右上逐格表 (平均 / 中位 / 該格變動 / 升日比例) · 左下摘要藍框 (開→收、最高/最低、上午 / 午休跳空 / 下午、開盤跳空、最佳持有窗口) · 曲線上的高低點標籤 · 今日 ±1σ
用法: 圖表 HKEX:7709, 1 分鐘或 10 分鐘皆可 (格數自動跟圖表週期) → 貼上 → Save (同名) → Add to chart; ① 指定了每格分鐘數而圖表週期不同時左下會紅字警告
注意: 平均路徑只是 21 日的平均, ±1σ 帶顯示個別日子的離散程度; 1 分鐘圖免費方案約 5,000 根 ≈ 15 個交易日 (不足 21 日時用實際有的天數), 10 分鐘圖足夠'''
src = io.open('hk7709_pattern_src.pine', encoding='utf-8').read().rstrip('\n').replace('STAMP', STAMP)
hbl = hb.split('\n')
n_total = 2 + len(hbl) + 1 + src.count('\n') + 1 + 1
tail = f'//  四處必須一致: 標題 = shorttitle = 檔名 = TradingView 腳本名稱 (結尾的 ")" 不可漏); 本檔共 {n_total} 行, 最後一行是 END OF FILE\n'
out = BAR + f'//  {name}  ·  ' + hbl[0] + '\n' + ''.join('//  ' + l + '\n' for l in hbl[1:]) + tail + BAR + src + '\n' + END_TAG.format(name=name, n=n_total) + '\n'
assert out.count('\n') == n_total
fn = name.replace(':', '.') + '.pine'
io.open(fn, 'w', encoding='utf-8', newline='\n').write(out)
print('wrote', fn, n_total, 'lines; verify:', verify(out) or 'PASS')
make_paste_page.make(fn, 'paste_HK7709-mode5-pattern.html')
h = io.open('paste_HK7709-mode5-pattern.html', encoding='utf-8').read()
h = h.replace('1 分鐘日內策略 (市場預設 美股, Inputs 可切港股)', '港股 7709 · 模式 5 · 一個月日內平均 pattern 曲線 (副圖指標)')
h = h.replace('<b>圖表週期切 1 分鐘</b>, 開要測的標的 (例如 AMEX:SOXL)。', '<b>圖表週期 1 分鐘或 10 分鐘</b>, 開 HKEX:7709。')
io.open('paste_HK7709-mode5-pattern.html', 'w', encoding='utf-8', newline='\n').write(h)
