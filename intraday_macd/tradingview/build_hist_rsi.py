# -*- coding: utf-8 -*-
"""build_hist_rsi.py — 由「攤平版」macd-hist&rsi 雙訊號 Pine 檔產出發佈檔 (表頭 + 檔尾完整性標記)。

用法: python3 build_hist_rsi.py <src.pine> "TV-1M-macd-hist&rsi_(09月19日; 23:55)"
  → 產出 <新名稱>.pine (檔名用 . 代替 :), strategy 標題 / shorttitle / 檔尾標記 全部同名。
"""
import io, os, re, sys
from flatten_pine import flatten, verify

END_TAG = '// ═══ END OF FILE ═══ {name} · 全檔共 {n} 行 · 看不到這一行 = 貼上的內容被截斷, 請用「貼上工具」網頁的【複製全部程式碼】 ═══'

HEADER = """\
// ═══════════════════════════════════════════════════════════════════════════════
//  {name}  ·  MACD 柱動能減弱 + RSI 超賣回歸 雙訊號策略 · 1 分鐘 · 一個月回測 · TradingView Pine Script v6
//  四處必須一致: strategy() 標題 = shorttitle = 檔名 = TradingView 腳本名稱 (Save 時輸入; 結尾的 ")" 不可漏)
//  本檔共 {n} 行; 最後一行是 "// ═══ END OF FILE ═══" → 貼上後若看不到那一行 = 內容被截斷 (檔案預覽視窗常只載入前 8KB)
//  正確貼法: 用「貼上工具」網頁按【複製全部程式碼】, 或下載 .pine 後用純文字編輯器開啟 → Ctrl+A → Ctrl+C
//  ★ 看到 CE10244 "A strategy must contain at least one of the following: any strategy.*() … plot*() …" = 貼上的內容被截斷在 8 KB
//     (前 8 KB 只有表頭 + strategy() + Inputs, 第一個 plot 在第 228 行) — 這不是程式錯誤, 請改用貼上工具網頁複製, 貼完確認最後一行
//
//  【本版規則 — 三條】
//   模式 1 (MACD 柱動能減弱, ④): 負柱段先「儲夠下跌動能」(夠超賣), 再連續 N 根淺紅柱 (柱仍為負但比前一根短) 完成 → 模式 1 買訊
//       本版把下跌動能門檻調高: 門檻倍數 k 由 1.0 → 1.5, 負柱段最少根數由 3 → 4 (④ 可再調)。賣訊 = 正柱段儲夠上昇動能後連續 N 根淺綠完成
//   模式 2 (RSI 超賣回歸 = 多策略比較版的 S05, ④c): RSI(14) 上穿 30 → 模式 2 買訊; 賣訊 = RSI 上穿 55 (S05 原版) 或 下穿 70 (可選)
//   買入 = 兩個模式的買訊【同時】成立才算合格; 賣出 = 模式 1 或 模式 2【任一】賣訊出現即刻平倉 (另有收市強平 / 可選固定止損)
//
//  【「同時」怎麼定義 — 匹配窗口 (④c matchWin, 預設 5 根)】
//   兩個買訊都是單根事件 (第 N 根淺紅完成的那一根 / RSI 上穿 30 的那一根), 要求剛好落在同一根幾乎不會發生。
//   所以: 任一買訊觸發後保持 N 根有效; 兩者同時有效、且本根至少有一個剛觸發 → 才是合格買點 (同一對訊號只觸發一次)。
//   設 1 = 必須同一根 (最嚴); 設大 = 較鬆。副圖參數表會即時顯示「模式1 幾筆 · 模式2 幾筆 → 同時幾筆」, 調窗口時直接看效果。
//
//  【圖示】副圖底部: 小圓點 = 模式 1 買訊 · 小菱形 = 模式 2 買訊 (兩者都只是訊號); 藍三角 B = 真正成交 (兩訊號匹配後下一根開盤)
//        逐筆交易表的「出場時間」後面標出場原因: S-M1 (模式 1 淺綠 N 根) / S-M2 (模式 2 RSI) / S-M1+M2 (同根) / EOD (收市強平) / SL (止損)
//  【參數掃描 (⑨)】81 組 (買N×買k × 賣N×賣k) 每一組都套上同一套 RSI 匹配與任一賣訊規則, 排名結果可直接填回 ④ 套用
//  【回測期間】① 預設 方式 B 最近 30 天 (一個月); 亦可 方式 A 最近 21 個交易日 / 方式 C 指定起迄 — 全部在 Inputs 設定
//       ※ 1 分 K 一個月約 8,200 根, TradingView 依方案只載入 5,000-20,000 根 → 實際回測從圖表最左那根開始, 報表標題顯示實際起始日
//
//  【共用規則】只做多 · 全部本金 · 收盤確認下一根開盤成交 (process_orders_on_close = false) · 手續費 0.03%/邊 + 滑點 2 tick
//   美股時段 09:30-16:00 America/New_York (DST 自動) · 15:45 後不開新倉 · 15:58 強制平倉 · margin_long = 0 (v6 預設 100% 會令全部本金下單被拒)
//   所有 ta.* 一律在全域無條件計算 — Pine v6 的 and / or 是短路求值, ta.* 放在條件後面會在被擋住的 K 上停止更新而產生假訊號
//  【使用】圖表切【SOXL · 1 分鐘】→ Pine Editor 貼上 → 檢查最後一行 → Save (輸入同名) → Add to chart → 主圖右上摘要 + 副圖右上參數表 + Strategy Tester
//  版本戳 TV-1M-macd-hist&rsi_(MM月DD日; HH:MM), 括號內 = 建置時間 HKT; 檔名以 . 代替 : (Windows 檔名不接受冒號); 本檔零延續行
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
