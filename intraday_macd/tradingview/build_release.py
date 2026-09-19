# -*- coding: utf-8 -*-
"""build_release.py — 由「攤平版」Pine 檔產出一個新版本戳的發佈檔, 並在檔尾加上完整性標記。

為什麼要有檔尾標記:
  用戶把 .pine 貼進 TradingView 時, 曾兩次在「內容剛好 8192 bytes」的位置報 Missing closing parenthesis
  → 複製路徑 (檔案預覽視窗) 只載入前 8KB, 貼上的內容從中間被切斷。
  檔尾加一行固定註解後, 貼上後看最後一行就能判斷內容有沒有完整。

用法: python3 build_release.py <src.pine> "<完整新名稱>"   例: "TW-1M-MACD-(09月19日_18:10)"
  → 產出 <新名稱>.pine (檔名用 . 代替 :), strategy 標題 / shorttitle / 檔尾標記 全部同名。
"""
import io, os, re, sys
from flatten_pine import flatten, verify

END_TAG = '// ═══ END OF FILE ═══ {name} · 全檔共 {n} 行 · 看不到這一行 = 貼上的內容被截斷, 請用「貼上工具」網頁的【複製全部程式碼】 ═══'

HEADER = """\
// ═══════════════════════════════════════════════════════════════════════════════
//  {name}  ·  MACD 動能蓄積交叉策略 · 1 分鐘回測版 (市場預設 美股, ⑤ 可一鍵切港股) · TradingView Pine Script v6
//  四處必須一致: strategy() 標題 = shorttitle = 檔名 = TradingView 腳本名稱 (Save 時輸入; 結尾的 ")" 不可漏)
//  本檔共 {n} 行; 最後一行是 "// ═══ END OF FILE ═══" → 貼上後若看不到那一行 = 內容被截斷 (檔案預覽視窗常只載入前 8KB)
//  正確貼法: 用「貼上工具」網頁按【複製全部程式碼】, 或下載 .pine 後用純文字編輯器開啟 → Ctrl+A → Ctrl+C
//
//  【本版關鍵參數 — 目標: 平均每日 5 筆交易】
//   ★ margin_long = 0, margin_short = 0   ← 修正 0 交易的真正原因: Pine v6 預設 margin 100%, 「全部本金」下單加上手續費/滑點會被拒
//   ★ 自動校準 目標每日交易次數 = 5       ← 每個交易日收盤結算昨日成交筆數, 低於目標×0.8 門檻係數 k 降 20%, 高於目標×1.3 升 20%
//   ★ 深度門檻百分位 60 → 50, 最少連續根數 4 → 3, 面積係數 0.6 → 0.5   ← 起始門檻先降一級, 再由自動校準逐日收斂
//   報表「門檻(現值)」列會顯示現行 k 值與近日均交易數; 手動模式或把目標設 0 即關閉校準
//
//  規則: 買 = 負動能段「儲夠」後 DIF 上穿 DEA (收盤確認) → 下一根開盤買; 賣 = 正動能段儲夠後 DIF 下穿 DEA → 下一根開盤賣
//        儲夠 = 同號柱連續根數 ≥ minBars 且 面積 Σ|hist|/close% ≥ minArea 且 深度 max|hist|/close% ≥ minDepth; 長倉 only
//  預設: 本金 100,000 · 最近 30 天 · 美股時段 09:30-16:00 America/New_York (DST 自動) · 15:45 後不開新倉 · 15:58 強制平倉
//  圖示 (主圖與副圖同步): ▲藍三角+藍直線 = 買單真正成交那一根 (訊號K的下一根開盤); ▼紅三角+紅直線 = 賣單成交; 幼點線貫通主圖與 MACD 副圖
//        橙框 = 持倉期間: 主圖框住該段價格 K 線, 副圖框住該段 MACD 柱 (force_overlay 把繪圖送到主圖, 策略本身仍在副圖)
//  版面: 回測摘要 + 逐筆交易表 → 主圖 (⑦ 可選位置); 副圖只留「觸發參數」表: 門檻現值 / 現段統計 / 交叉→合格漏斗 / 勝率, 調 ④ 即時看效果
//        兩表預設同靠右上, 直線對齊; 成交直線為幼點線 (width 1, dotted), 淡化程度由 ⑧ lineTransp 調 (預設 55%)
//  報表: 期內交易次數 / 每筆 P&L ($ 與 %) / 整段 Total P&L / 每日平均交易次數; 時段或時區設錯會直接指出
//  注意: TradingView 的 MACD 柱 = DIF−DEA (牛牛/Webull 顯示 2×), 門檻以 1× 定義; 手續費/滑點務必填真實值, 填 0 會嚴重高估
//  使用: 圖表週期切【1 分鐘】→ Pine Editor 貼上 → 檢查最後一行 → Save (輸入同名) → Add to chart → Strategy Tester
//  版本戳 (MM月DD日_HH:MM) = 建置時間 HKT; 檔名以 . 代替 : (Windows 檔名不接受冒號); 本檔零延續行, 每個語句自成一行
// ═══════════════════════════════════════════════════════════════════════════════
"""


def build(src_path: str, name: str) -> str:
    src = io.open(src_path, encoding='utf-8').read()
    src = flatten(src)
    m = re.search(r'^strategy\("([^"]+)"', src, re.M)
    if not m:
        sys.exit('找不到 strategy("…") 宣告')
    old = m.group(1)
    lines = src.split('\n')
    # 去掉舊表頭 (到 //@version 之前) 與舊的檔尾標記
    try:
        v = next(i for i, l in enumerate(lines) if l.startswith('//@version'))
    except StopIteration:
        sys.exit('找不到 //@version')
    body = [l for l in lines[v:] if not l.startswith('// ═══ END OF FILE')]
    while body and body[-1].strip() == '':
        body.pop()
    body = '\n'.join(body).replace(old, name)
    # strategy() 那一行: 收掉對齊用的多重空格 (純外觀)
    body = re.sub(r'^(strategy\(.*)$', lambda mm: re.sub(r' {2,}', ' ', mm.group(1)), body, count=1, flags=re.M)
    # 1 分鐘版殘留的「日線」字眼
    body = body.replace('MACD動能日線回測', 'MACD動能回測')
    # 兩段式: 先算行數, 再填進表頭與檔尾
    header_lines = HEADER.count('\n')
    n = header_lines + body.count('\n') + 1 + 1  # + END 行
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
