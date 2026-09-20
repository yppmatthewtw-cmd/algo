# -*- coding: utf-8 -*-
"""build_hist_cross_rsi.py — 由「攤平版」macd-hist,cross&rsi 三訊號 Pine 檔產出發佈檔 (表頭 + 檔尾完整性標記)。

用法: python3 build_hist_cross_rsi.py <src.pine> "TV-1M-macd-hist,cross&rsi_(09月20日; 01:30)"
  → 產出 <新名稱>.pine (檔名用 . 代替 :), strategy 標題 / shorttitle / 檔尾標記 全部同名。
"""
import io, os, re, sys
from flatten_pine import flatten, verify

END_TAG = '// ═══ END OF FILE ═══ {name} · 全檔共 {n} 行 · 看不到這一行 = 貼上的內容被截斷, 請用「貼上工具」網頁的【複製全部程式碼】 ═══'

HEADER = """\
// ═══════════════════════════════════════════════════════════════════════════════
//  {name}  ·  主策略 (dashboard): 模式 1 MACD 柱到上下界 + 模式 2 RSI 14/28 可買區 + 模式 3 敏感 MACD 金叉 + 模式 4 EMA9 斜率向上 · 1 分鐘 · 一個月回測 · Pine v6
//  四處必須一致: strategy() 標題 = shorttitle = 檔名 = TradingView 腳本名稱 (Save 時輸入; 結尾的 ")" 不可漏)
//  本檔共 {n} 行; 最後一行是 "// ═══ END OF FILE ═══" → 貼上後若看不到那一行 = 內容被截斷 (檔案預覽視窗常只載入前 8KB)
//  正確貼法: 用「貼上工具」網頁按【複製全部程式碼】, 或按【下載 .pine.txt】用純文字編輯器開啟 → Ctrl+A → Ctrl+C
//  ★ 看到 CE10244 "A strategy must contain at least one of the following: any strategy.*() … plot*() …" = 貼上的內容被截斷在 8 KB
//     (前 8 KB 只有表頭 + strategy() + Inputs, 第一個 plot 在很後面) — 這不是程式錯誤, 請改用貼上工具網頁複製, 貼完確認最後一行
//
//  【本版規則 — 四個模式, 兩條合格條件】
//   模式 1 (MACD 12/26/9 柱 + 上下界, ④): 副圖畫兩條線 — 上界 (紅) / 下界 (藍) = 最近 250 根 |柱| 的第 75 百分位 × 倍數 (買 1.5 / 賣 1.0; 可切手動);\n//       買訊 = 負柱段先「跌到下界」(段內最深柱 ≤ 下界, 根數 ≥ 4), 之後連續 2 根淺紅柱完成; 賣訊 = 正柱段先「昇到上界」, 之後連續 2 根淺綠完成。未到界的淺紅 / 淺綠不算 (可開灰色小三角對照)
//   模式 2 (RSI 14/28 可買區 / 可賣區, ④c — 狀態, 像模式 4, 不形成絕對買賣點; 舊的 cRSI 已刪除): 下界 / 上界 = 最近 120 根 RSI14 的第 10 / 90 百分位 (可切固定 30/70)\n//       進入可買區 = RSI14 梯度由 ≤0 轉 >0 (谷底在前一根) 且 谷底到達或低於下界; 可買區一直持續, 直到「昇不上」= RSI14 跌破 RSI28 (反彈後失守), 或 RSI14 跌破進區時的谷底 (反彈失敗) (④c 可改為只看 RSI14 / RSI28 轉勢); 每個交易日開始時清空\n//       進入可賣區 = 相反 (RSI14 梯度由 ≥0 轉 <0 且 峰頂到達或高於上界), 結束條件也相反; 進入另一區直接取代現區; 持倉中可買區結束 → 平倉 (M2區結束)
//   模式 3 (敏感 MACD 9/26/9 金叉, ④d): 快線 EMA 由 12 改 9 更敏感; DIF 上穿 DEA (金叉) → 模式 3 買訊。模式 3【不參與賣出】
//       ※「快線 cross 慢線」預設解讀為 DIF 上穿 DEA (中文常說的金叉, 與本專案 ④「快慢線交叉」同一定義); ④d 可切成 DIF 上穿 0 軸 (= EMA9 上穿 EMA26)
//   模式 4 (EMA9 斜率, ④e): EMA9 現值比 N 根前高 (預設 N=1) = 趨勢向上 → 可以買入; 斜率為負則不可。舊版的時段 / 開市方向條件已全部移除
//       模式 4 是「狀態」, 只限制買入, 不參與賣出; EMA9 以細綠線畫在主圖上, 斜率柱在 TV-1M-winrate-mode4 副圖
//   合格買入 = 四模式同時: 模式 1 與 3 的買訊在匹配窗口 (④c 預設 5 根) 內先後出現 + 買入那一根模式 2 處於可買區 + 模式 4 向上, 且本根至少一個模式剛出現 (M1 / M3 觸發, 或 剛進可買區, 或 EMA9 剛轉向上)
//   合格賣出 = 模式 1 賣訊 (昇到上界後淺綠 N 根完成, 有效 5 根) 在模式 2 可賣區內 (本根至少一個剛出現); 另有 可買區結束平倉 / 15:58 收市強平 / 可選固定止損
//
//  【副圖分工】一支 Pine 腳本只能佔一個副圖。模式 1 與 3 (MACD 尺度) 在本腳本副圖; 模式 2 (RSI 14/28 區) 在 TV-1M-RSI-mode2; 模式 4 (EMA9 斜率) 在 TV-1M-winrate-mode4; 三支一起 Add to chart, 同名設定要一致
//  【圖示】每個模式的每個買賣訊號 = 一條淺灰幼直線貫通主圖與副圖 (買 點線 / 賣 虛線, ⑧b 可關可調淡化); 模式 1 的 ▲ 淺藍買訊標在負柱底下, ▼ 淺紅賣訊標在正柱頂上; 模式 1 的上界 (紅) / 下界 (藍) 畫在柱上;\n//        副圖只畫模式 3 的 9/26/9 快慢線 (12/26/9 的 DIF/DEA 線已移除, 柱保留給模式 1); 模式 3 的金叉 ▲ / 死叉 ▼ (只顯示) 標在 9/26/9 交叉點; 每條線左邊都有線名標籤 (擠在 0 軸附近的會自動上下拉開, 不再互相疊住)
//  【版面】主圖右上一張合併表格: 左 7 欄 回測摘要 (藍, 預設不列逐筆交易, ⑦ maxRows 可開) + 右 7 欄 參數掃描 (紫, 列 8 名), 同一表格永不重疊; 副圖右上為觸發參數表
//        純顯示, 不影響策略買賣; 每條線左側有線名標籤。藍三角 B / 紅三角 S = 真正成交; 模式 2 的區間見 TV-1M-RSI-mode2 副圖
//        逐筆交易表出場原因: S-M1&M2 (M1 賣訊在可賣區) / M2區結束 (可買區結束平倉) / EOD (15:58 強平) / SL (止損) / 窗口結束
//  【參數掃描 (⑨)】81 組 (買N×買k × 賣N×賣k, k∈1/1.5/2) 每一組都套上同一套四模式買 (M1&M3 匹配 + M2 可買區 + M4 向上) / M1 賣訊在可賣區 + 可買區結束平倉 的規則, 排名結果可直接填回 ④\n//   ※ 本版修正: Pine 的 int / int 不截斷 (回傳 float), 舊版索引解碼只有整除的幾組真的在跑, 其餘顯示 0 筆 — 已改用 math.floor, 81 組全部有效
//  【回測期間】① 預設 方式 B 最近 30 天 (一個月); 亦可 方式 A 最近 21 個交易日 / 方式 C 指定起迄 — 全部在 Inputs 設定
//       ※ 1 分 K 一個月約 8,200 根, TradingView 依方案只載入 5,000-20,000 根 → 實際回測從圖表最左那根開始, 報表標題顯示實際起始日
//  【共用規則】只做多 · 全部本金 · 收盤確認下一根開盤成交 · 手續費 0.03%/邊 + 滑點 2 tick · 美股 09:30-16:00 NY · 15:45 後不開新倉 · 15:58 強平
//   margin_long = 0 (v6 預設 100% 會令全部本金下單被拒); 所有 ta.* 在全域無條件計算 (v6 的 and/or 是短路求值)
//  【使用】圖表切【SOXL · 1 分鐘】→ Pine Editor 貼上 → 檢查最後一行 → Save (輸入同名) → Add to chart → 主圖右上摘要 + 副圖右上參數表 + Strategy Tester
//  版本戳 TV-1M-dashboard_(mode 1-4)_(MM月DD日; HH:MM), 第二個括號 = 建置時間 HKT; 檔名以 . 代替 : (Windows 檔名不接受冒號); 本檔零延續行
// ═══════════════════════════════════════════════════════════════════════════════
"""


def build(src_path: str, name: str):
    src = io.open(src_path, encoding='utf-8').read()
    src = flatten(src)
    m = re.search(r'^strategy\("([^"]+)"', src, re.M)
    if not m:
        sys.exit('找不到 strategy("…") 宣告')
    old = m.group(1)
    lines = src.split('\n')
    v = next(i for i, l in enumerate(lines) if l.startswith('//@version'))
    body = [l for l in lines[v:] if not l.startswith('// ═══ END OF FILE')]
    while body and body[-1].strip() == '':
        body.pop()
    body = '\n'.join(body).replace(old, name)
    body = re.sub(r'^(strategy\(.*)$', lambda mm: re.sub(r' {2,}', ' ', mm.group(1)), body, count=1, flags=re.M)
    body = body.replace('MACD動能日線回測', 'MACD動能回測')
    header_lines = HEADER.count('\n')
    n = header_lines + body.count('\n') + 1 + 1
    out = HEADER.format(name=name, n=n) + body + '\n' + END_TAG.format(name=name, n=n) + '\n'
    assert out.count('\n') == n, (out.count('\n'), n)
    return name, out


if __name__ == '__main__':
    src_path, name = sys.argv[1], sys.argv[2]
    name, out = build(src_path, name)
    dst = os.path.join(os.path.dirname(os.path.abspath(src_path)), name.replace(':', '.') + '.pine')
    io.open(dst, 'w', encoding='utf-8', newline='\n').write(out)
    probs = verify(out)
    L = out.split('\n')
    print(f'{os.path.basename(dst)}: {out.count(chr(10))} 行, {len(out.encode())} bytes')
    print('  title/shorttitle:', re.search(r'strategy\("([^"]+)", shorttitle="([^"]+)"', out).groups())
    print('  最後一行:', L[-2][:60], '…')
    print('  驗證:', 'PASS ✓' if not probs else '\n  ' + '\n  '.join(probs))
    sys.exit(0 if not probs else 1)
