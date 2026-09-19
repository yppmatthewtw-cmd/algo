# -*- coding: utf-8 -*-
"""build_multi.py — 由「攤平版」多策略比較 Pine 檔產出發佈檔 (表頭 + 檔尾完整性標記)。

用法: python3 build_multi.py <src.pine> "TW-1M-MULTI-(09月19日_23:13)"
  → 產出 <新名稱>.pine (檔名用 . 代替 :), strategy 標題 / shorttitle / 檔尾標記 全部同名。
"""
import io, os, re, sys
from flatten_pine import flatten, verify

END_TAG = '// ═══ END OF FILE ═══ {name} · 全檔共 {n} 行 · 看不到這一行 = 貼上的內容被截斷, 請用「貼上工具」網頁的【複製全部程式碼】 ═══'

HEADER = """\
// ═══════════════════════════════════════════════════════════════════════════════
//  {name}  ·  多策略同場回測比較 · 1 分鐘 · TradingView Pine Script v6
//  四處必須一致: strategy() 標題 = shorttitle = 檔名 = TradingView 腳本名稱 (Save 時輸入; 結尾的 ")" 不可漏)
//  本檔共 {n} 行; 最後一行是 "// ═══ END OF FILE ═══" → 貼上後若看不到那一行 = 內容被截斷 (檔案預覽視窗常只載入前 8KB)
//  正確貼法: 用「貼上工具」網頁按【複製全部程式碼】, 或下載 .pine 後用純文字編輯器開啟 → Ctrl+A → Ctrl+C
//
//  【這支腳本做甚麼】
//   把 13 個常見的日內做多策略放在【同一個回測窗口、同一套手續費滑點、同一組交易時段與收市強平規則】下各跑一次,
//   主圖右上直接印出每個策略的回測 report (交易次數 / 勝率 / 總報酬 / 最大回撤 / 獲利因子 / 平均每筆 / 最佳最差 / 平均持倉 / 捕獲率),
//   按總報酬由高到低排名, 並附「買入持有」與「期內最大昇幅」兩條基準線 → 一眼看出哪一個方法在這一個月的 SOXL 上真的有優勢。
//   ③ 選中的那一個策略會下真單, TradingView 內建 Strategy Tester 因此顯示它的逐筆明細; 其餘 12 個同時做虛擬回測。
//
//  【13 個策略】S01 MACD柱動能減弱(本專案) · S02 MACD DIF/DEA交叉 · S03 EMA 9/21 交叉 · S04 Supertrend轉向 ·
//   S05 RSI超賣回歸 · S06 布林下軌回歸 · S07 VWAP偏離回歸 · S08 開盤區間突破 · S09 動能突破+量能 ·
//   S10 三EMA+Supertrend共振 · S11 ATR標準化MACD · S12 MACD柱背離 · S13 隨機進場(安慰劑基準)
//   ※ S13 是對照組: 任何排在隨機進場下面的策略, 在這段資料上等於沒有優勢 — 這是判讀本表最重要的一條線。
//
//  【共用規則 — 保證比較公平】
//   · 只做多, 每次全部本金, 不加碼 (pyramiding = 0)
//   · 訊號一律在 K 線收盤確認, 下一根開盤成交 (process_orders_on_close = false), 不會偷看未來
//   · 手續費 0.03%/邊 + 滑點 2 tick, 虛擬回測與真單用同一組數字 (② 可改, 改完要同步改 strategy() 那一行)
//   · 美股時段 09:30-16:00 America/New_York (DST 自動) · 15:45 後不開新倉 · 15:58 強制平倉, 不留隔夜倉
//   · ② 可一鍵開「所有策略共用固定止損」, 開了就 13 個策略一起用, 比較仍然公平
//   · margin_long = 0, margin_short = 0 ← Pine v6 預設 margin 100% 會令「全部本金」下單被拒 (0 交易)
//
//  【回測期間】① 預設 方式 B 最近 30 天 (一個月); 另有 方式 A 最近 N 個交易日 (預設 21) / 方式 C 指定起迄日期 — 全部在 Inputs 設定
//   ※ 1 分 K 一個月約 8,200 根, TradingView 依方案只載入 5,000-20,000 根 → 實際回測從圖表最左那根開始, 報表標題顯示實際起始日與實際根數
//
//  【怎麼用】圖表切【SOXL · 1 分鐘】→ Pine Editor 貼上 → 檢查最後一行 → Save (輸入同名) → Add to chart
//   → 看主圖右上的比較表 → 選出前列策略 → 回 ③ 把它設為下真單 → 看 Strategy Tester 的逐筆明細與權益曲線
//  【怎麼讀】捕獲率 = 該策略總報酬 ÷ 期內最大昇幅; 獲利因子 < 1 = 賠錢; 交易次數 < 30 的勝率沒有統計意義, 只能當參考
//  版本戳 TW-1M-MULTI-(MM月DD日_HH:MM), 括號內 = 建置時間 HKT; 檔名以 . 代替 : (Windows 檔名不接受冒號); 本檔零延續行, 每個語句自成一行
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
    try:
        v = next(i for i, l in enumerate(lines) if l.startswith('//@version'))
    except StopIteration:
        sys.exit('找不到 //@version')
    body = [l for l in lines[v:] if not l.startswith('// ═══ END OF FILE')]
    while body and body[-1].strip() == '':
        body.pop()
    body = '\n'.join(body).replace(old, name)
    body = re.sub(r'^(strategy\(.*)$', lambda mm: re.sub(r' {2,}', ' ', mm.group(1)), body, count=1, flags=re.M)
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
