# -*- coding: utf-8 -*-
"""build_release.py — 由「攤平版」Pine 檔產出一個新版本戳的發佈檔, 並在檔尾加上完整性標記。

為什麼要有檔尾標記:
  用戶把 .pine 貼進 TradingView 時, 曾兩次在「內容剛好 8192 bytes」的位置報 Missing closing parenthesis
  → 複製路徑 (檔案預覽視窗) 只載入前 8KB, 貼上的內容從中間被切斷。
  檔尾加一行固定註解後, 貼上後看最後一行就能判斷內容有沒有完整。

用法: python3 build_release.py <src.pine> <MM.DD;HH:MM>
  → 產出 <PREFIX>-(MM.DD;HH.MM).pine (檔名用 . 代替 :), strategy 標題 / shorttitle / 檔尾標記 全部同名。
"""
import io, os, re, sys
from flatten_pine import flatten, verify

END_TAG = '// ═══ END OF FILE ═══ {name} · 全檔共 {n} 行 · 看不到這一行 = 貼上的內容被截斷, 請用「貼上工具」網頁的【複製全部程式碼】 ═══'

HEADER = """\
// ═══════════════════════════════════════════════════════════════════════════════
//  {name}  ·  MACD 動能蓄積交叉策略 · 美股 1 分鐘回測版 · TradingView Pine Script v6
//  四處必須一致: strategy() 標題 = shorttitle = 檔名 = TradingView 腳本名稱 (Save 時輸入; 結尾的 ")" 不可漏)
//  本檔共 {n} 行; 最後一行是 "// ═══ END OF FILE ═══" → 貼上後若看不到那一行 = 內容被截斷 (檔案預覽視窗常只載入前 8KB)
//  正確貼法: 用「貼上工具」網頁按【複製全部程式碼】, 或下載 .pine 後用純文字編輯器開啟 → Ctrl+A → Ctrl+C
//
//  規則: 買 = 負動能段「儲夠」後 DIF 上穿 DEA (收盤確認) → 下一根開盤買; 賣 = 正動能段儲夠後 DIF 下穿 DEA → 下一根開盤賣
//        儲夠 = 同號柱連續根數 ≥ minBars 且 面積 Σ|hist|/close% ≥ minArea 且 深度 max|hist|/close% ≥ minDepth; 長倉 only
//  預設: 本金 100,000 · 最近 30 天 · 美股時段 09:30-16:00 America/New_York (DST 自動) · 15:45 後不開新倉 · 15:58 強制平倉
//  圖示: ▲藍三角+藍線 = 買單真正成交那一根 (訊號K的下一根開盤); ▼紅三角+紅線 = 賣單成交; 橙框 = 持倉期間 (框住 MACD 柱)
//  報表: 期內交易次數 / 每筆 P&L ($ 與 %) / 整段 Total P&L / 每日平均交易次數; 時段或時區設錯會直接指出
//  注意: TradingView 的 MACD 柱 = DIF−DEA (牛牛/Webull 顯示 2×), 門檻以 1× 定義; 手續費/滑點務必填真實值, 填 0 會嚴重高估
//  使用: 圖表週期切【1 分鐘】→ Pine Editor 貼上 → 檢查最後一行 → Save (輸入同名) → Add to chart → Strategy Tester
//  版本戳 (MM.DD;HH:MM) = 建置時間 HKT; 檔名以 . 代替 : (Windows 檔名不接受冒號); 本檔零延續行, 每個語句自成一行
// ═══════════════════════════════════════════════════════════════════════════════
"""


def build(src_path: str, stamp: str) -> str:
    src = io.open(src_path, encoding='utf-8').read()
    src = flatten(src)
    m = re.search(r'^strategy\("([A-Za-z0-9\-]+)-\((\d\d\.\d\d;\d\d:\d\d)\)"', src, re.M)
    if not m:
        sys.exit('找不到 strategy("PREFIX-(MM.DD;HH:MM)" …) 宣告')
    prefix, old = m.group(1), m.group(2)
    name = f'{prefix}-({stamp})'
    lines = src.split('\n')
    # 去掉舊表頭 (到 //@version 之前) 與舊的檔尾標記
    try:
        v = next(i for i, l in enumerate(lines) if l.startswith('//@version'))
    except StopIteration:
        sys.exit('找不到 //@version')
    body = [l for l in lines[v:] if not l.startswith('// ═══ END OF FILE')]
    while body and body[-1].strip() == '':
        body.pop()
    body = '\n'.join(body).replace(old, stamp)
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
    src_path, stamp = sys.argv[1], sys.argv[2]
    name, out = build(src_path, stamp)
    dst = os.path.join(os.path.dirname(os.path.abspath(src_path)), name.replace(':', '.') + '.pine')
    io.open(dst, 'w', encoding='utf-8', newline='\n').write(out)
    probs = verify(out)
    L = out.split('\n')
    print(f'{os.path.basename(dst)}: {out.count(chr(10))} 行, {len(out.encode())} bytes')
    print('  title/shorttitle:', re.search(r'strategy\("([^"]+)", shorttitle="([^"]+)"', out).groups())
    print('  最後一行:', L[-2][:60], '…')
    print('  驗證:', 'PASS ✓' if not probs else '\n  ' + '\n  '.join(probs))
    sys.exit(0 if not probs else 1)
