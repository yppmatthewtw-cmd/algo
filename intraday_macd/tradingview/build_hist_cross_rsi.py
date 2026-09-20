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
//  {name}  ·  MACD 柱動能減弱 + 敏感 MACD 金叉 + RSI 超賣回歸 三訊號策略 · 1 分鐘 · 一個月回測 · TradingView Pine Script v6
//  四處必須一致: strategy() 標題 = shorttitle = 檔名 = TradingView 腳本名稱 (Save 時輸入; 結尾的 ")" 不可漏)
//  本檔共 {n} 行; 最後一行是 "// ═══ END OF FILE ═══" → 貼上後若看不到那一行 = 內容被截斷 (檔案預覽視窗常只載入前 8KB)
//  正確貼法: 用「貼上工具」網頁按【複製全部程式碼】, 或按【下載 .pine.txt】用純文字編輯器開啟 → Ctrl+A → Ctrl+C
//  ★ 看到 CE10244 "A strategy must contain at least one of the following: any strategy.*() … plot*() …" = 貼上的內容被截斷在 8 KB
//     (前 8 KB 只有表頭 + strategy() + Inputs, 第一個 plot 在很後面) — 這不是程式錯誤, 請改用貼上工具網頁複製, 貼完確認最後一行
//
//  【本版規則 — 三個模式, 兩條合格條件】
//   模式 1 (MACD 12/26/9 柱動能減弱, ④): 負柱段先「儲夠下跌動能」(門檻倍數 k 1.5, 負柱段最少 4 根 — 已調高), 再連續 2 根淺紅柱完成 → 模式 1 買訊
//       賣訊 = 正柱段儲夠上昇動能後連續 2 根淺綠完成
//   模式 2 (RSI 超賣回歸 = S05, ④c): RSI(14) 上穿 30 → 模式 2 買訊; 賣訊 = RSI 上穿 55 (S05 原版) 或 下穿 70 (可選)
//   模式 3 (敏感 MACD 9/26/9 金叉, ④d): 快線 EMA 由 12 改 9 更敏感; DIF 上穿 DEA (金叉) → 模式 3 買訊。模式 3【不參與賣出】
//       ※「快線 cross 慢線」預設解讀為 DIF 上穿 DEA (中文常說的金叉, 與本專案 ④「快慢線交叉」同一定義); ④d 可切成 DIF 上穿 0 軸 (= EMA9 上穿 EMA26)
//   3a 合格買入 = 模式 1、2、3 的買訊【同時】成立 (匹配窗口 ④c 預設 5 根: 三者都在窗口內且本根至少一個剛觸發)
//   3b 合格賣出 = 模式 1 與 模式 2 的賣訊【同時】成立 (賣的匹配窗口 ④c 預設 5 根); 另有 15:58 收市強平 / 可選固定止損
//       ※ 模式 1 賣訊 (漲勢末段柱減弱) 與模式 2 的 S05 賣訊 (RSI 上穿 55, 漲勢初段) 常相隔很遠 → 多數出場會是收市強平。
//         想讓兩者靠近: ④c 把模式 2 賣訊改「下穿超買值 70」, 或放寬賣窗口。副圖參數表會顯示「賣: M1 幾筆 · M2 幾筆 → 同時幾筆」
//
//  【圖示】副圖最下方三條粗線 (⑧b): 模式 1 深綠 / 模式 2 棕 / 模式 3 紫, 各自【單獨運作】時的訊號: ○ (線同色) = 該模式買訊, × 紅 = 該模式賣訊; 副圖每一條線 (DIF / DEA / 柱 / 模式3 DIF DEA / 三條訊號線) 左邊都有線名標籤
//        純顯示, 不影響策略買賣; 右側有標籤。另有底部小圓點 / 菱形 / 方塊 = 模式 1 / 2 / 3 買訊; 藍三角 B = 真正成交
//        副圖另畫模式 3 的 DIF / DEA 細線 (半透明, ④d 可關); 逐筆交易表出場原因: S-M1&M2 / EOD / SL / 窗口結束
//  【參數掃描 (⑨)】81 組 (買N×買k × 賣N×賣k, k∈1/1.5/2) 每一組都套上同一套三訊號買 / 雙訊號賣規則, 排名結果可直接填回 ④
//  【回測期間】① 預設 方式 B 最近 30 天 (一個月); 亦可 方式 A 最近 21 個交易日 / 方式 C 指定起迄 — 全部在 Inputs 設定
//       ※ 1 分 K 一個月約 8,200 根, TradingView 依方案只載入 5,000-20,000 根 → 實際回測從圖表最左那根開始, 報表標題顯示實際起始日
//  【共用規則】只做多 · 全部本金 · 收盤確認下一根開盤成交 · 手續費 0.03%/邊 + 滑點 2 tick · 美股 09:30-16:00 NY · 15:45 後不開新倉 · 15:58 強平
//   margin_long = 0 (v6 預設 100% 會令全部本金下單被拒); 所有 ta.* 在全域無條件計算 (v6 的 and/or 是短路求值)
//  【使用】圖表切【SOXL · 1 分鐘】→ Pine Editor 貼上 → 檢查最後一行 → Save (輸入同名) → Add to chart → 主圖右上摘要 + 副圖右上參數表 + Strategy Tester
//  版本戳 TV-1M-macd-hist,cross&rsi_(MM月DD日; HH:MM), 括號內 = 建置時間 HKT; 檔名以 . 代替 : (Windows 檔名不接受冒號); 本檔零延續行
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
