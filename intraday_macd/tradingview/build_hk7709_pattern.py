# -*- coding: utf-8 -*-
"""build_hk7709_pattern.py — 由 hk7709_pattern_src.pine 產出 HK7709-10m-pattern_(MM月DD日; HH:MM).pine + 貼上工具網頁。
用法: STAMP="09月22日; 14:30" python3 build_hk7709_pattern.py
"""
import io, os
from flatten_pine import verify
import make_paste_page
from build_hist_cross_rsi import END_TAG

STAMP = os.environ['STAMP']
name = f'HK7709-10m-pattern_({STAMP})'
BAR = '// ' + '═' * 79 + '\n'
hb = '''港股 7709 · 10 分鐘 · 過去一個月「平均的一天」(日內平均化 pattern) · 純顯示指標, 不下單
做法: 每個交易日按港股時段切成固定格 (09:30-12:00 = 15 格, 13:00-16:00 = 18 格, 每格 10 分鐘), 每格的收盤 / 最高 / 最低 / 開盤 都換成「相對當日 09:30 開盤價的 %」,
      再把最近 21 個完整交易日 (① 可改) 同一格疊起來取 平均 / 中位數 / 標準差 / 升日比例; 只計「收市那一格有資料」的整日, 今日未收市不算入
畫面: 橙線 = 「平均的一天」曲線, 同一條 pattern 按對應時間格在每一個交易日重覆 (預設最近 60 日 + 今日, 今日未到的格畫在右邊; ① 可切成滾動 = 每日只用之前 N 日, 無前視) · 灰虛線 = 今日 ±1σ · 藍線 = 今日實際路徑 · 0% 虛線 = 當日開盤 · 上午 / 下午 底色
      預設只畫曲線; ① 可另外開: 右上逐格表 (平均 / 中位 / 該格變動 / 升日比例) · 左下摘要藍框 (開→收、最高/最低、上午 / 午休跳空 / 下午、開盤跳空、最佳持有窗口) · 曲線上的高低點標籤 · 今日 ±1σ
用法: 圖表切【HKEX:7709 · 10 分鐘】→ 貼上 → Save (同名) → Add to chart; 圖表週期與 ① 每格分鐘數不一致時左下會紅字警告
注意: 平均路徑只是 21 日的平均, ±1σ 帶顯示個別日子的離散程度; 免費方案 10 分鐘 K 可載入約 5,000 根 ≈ 150 個交易日, 一個月足夠'''
src = io.open('hk7709_pattern_src.pine', encoding='utf-8').read().rstrip('\n').replace('STAMP', STAMP)
hbl = hb.split('\n')
n_total = 2 + len(hbl) + 1 + src.count('\n') + 1 + 1
tail = f'//  四處必須一致: 標題 = shorttitle = 檔名 = TradingView 腳本名稱 (結尾的 ")" 不可漏); 本檔共 {n_total} 行, 最後一行是 END OF FILE\n'
out = BAR + f'//  {name}  ·  ' + hbl[0] + '\n' + ''.join('//  ' + l + '\n' for l in hbl[1:]) + tail + BAR + src + '\n' + END_TAG.format(name=name, n=n_total) + '\n'
assert out.count('\n') == n_total
fn = name.replace(':', '.') + '.pine'
io.open(fn, 'w', encoding='utf-8', newline='\n').write(out)
print('wrote', fn, n_total, 'lines; verify:', verify(out) or 'PASS')
make_paste_page.make(fn, 'paste_HK7709-10m-pattern.html')
h = io.open('paste_HK7709-10m-pattern.html', encoding='utf-8').read()
h = h.replace('1 分鐘日內策略 (市場預設 美股, Inputs 可切港股)', '港股 7709 · 10 分鐘 · 一個月日內平均 pattern (指標)')
h = h.replace('<b>圖表週期切 1 分鐘</b>, 開要測的標的 (例如 AMEX:SOXL)。', '<b>圖表週期切 10 分鐘</b>, 開 HKEX:7709。')
io.open('paste_HK7709-10m-pattern.html', 'w', encoding='utf-8', newline='\n').write(h)
