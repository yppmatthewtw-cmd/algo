# -*- coding: utf-8 -*-
"""make_paste_page.py — 把一個 .pine 檔包成「貼上工具」網頁: 一鍵複製全部程式碼 + 貼上後自我檢查清單。

背景: 用戶從檔案預覽視窗複製 .pine 時, 內容在 8192 bytes 處被截斷, TradingView 報 Missing closing parenthesis。
這個網頁把完整原始碼放在 <script type="text/plain"> 內, 用 JS 一次寫進剪貼簿, 不經過任何會截斷的預覽路徑。

用法: python3 make_paste_page.py <file.pine> <out.html>
"""
import io, json, re, sys

TEMPLATE = r"""<title>__TITLE__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  --bg:#F4F6F3;--surface:#FFFFFF;--ink:#17211C;--muted:#5D6B64;--line:#D9E0DB;
  --accent:#0E6F6B;--accent-ink:#FFFFFF;--accent-soft:#DDEEEC;
  --ok:#1E7F3E;--ok-soft:#DFF2E4;--warn:#9A6A0B;--warn-soft:#FBF0D3;--bad:#B3362A;--bad-soft:#F9E1DD;
  --code-bg:#0F1614;--code-ink:#D8E4DE;
  --sans:"IBM Plex Sans","PingFang TC","Microsoft JhengHei","Noto Sans TC",system-ui,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#0F1513;--surface:#171F1B;--ink:#E4EBE6;--muted:#95A59C;--line:#2A3630;
    --accent:#4CC3B8;--accent-ink:#06211E;--accent-soft:#163430;
    --ok:#5BCB7C;--ok-soft:#173824;--warn:#E3B24C;--warn-soft:#3A2E10;--bad:#F07A6C;--bad-soft:#40201B;
    --code-bg:#0A0F0D;--code-ink:#CDD9D2;
  }
}
:root[data-theme="dark"]{
  --bg:#0F1513;--surface:#171F1B;--ink:#E4EBE6;--muted:#95A59C;--line:#2A3630;
  --accent:#4CC3B8;--accent-ink:#06211E;--accent-soft:#163430;
  --ok:#5BCB7C;--ok-soft:#173824;--warn:#E3B24C;--warn-soft:#3A2E10;--bad:#F07A6C;--bad-soft:#40201B;
  --code-bg:#0A0F0D;--code-ink:#CDD9D2;
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.55;margin:0;padding-inline:16px;padding-block:28px 56px}
.wrap{max-width:900px;margin:0 auto;display:grid;gap:22px}
.eyebrow{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:500}
h1{font-family:var(--mono);font-size:clamp(20px,4.2vw,30px);font-weight:500;margin:4px 0 6px;letter-spacing:-.01em;text-wrap:balance;word-break:break-all}
h2{font-size:17px;font-weight:600;margin:0 0 10px}
p{margin:0}
.lead{color:var(--muted);max-width:68ch}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:18px 20px}
.hero{display:grid;gap:14px}
.actions{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
button{font:inherit;cursor:pointer;border-radius:8px;border:1px solid transparent;padding:12px 18px;font-weight:600}
button:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.primary{background:var(--accent);color:var(--accent-ink);font-size:17px;padding:14px 22px}
.secondary{background:var(--accent-soft);color:var(--ink);border-color:var(--line)}
.meta{font-family:var(--mono);font-size:13px;color:var(--muted);display:flex;flex-wrap:wrap;gap:6px 18px;font-variant-numeric:tabular-nums}
.status{min-height:24px;font-size:14px;padding:8px 12px;border-radius:6px;display:none}
.status.ok{display:block;background:var(--ok-soft);color:var(--ok)}
.status.bad{display:block;background:var(--bad-soft);color:var(--bad)}
.name{font-family:var(--mono);background:var(--accent-soft);padding:2px 6px;border-radius:4px;word-break:break-all}
ol.steps{margin:0;padding-left:0;list-style:none;display:grid;gap:12px;counter-reset:s}
ol.steps li{display:grid;grid-template-columns:30px 1fr;gap:12px;align-items:start}
ol.steps li::before{counter-increment:s;content:counter(s);width:28px;height:28px;border-radius:50%;background:var(--accent);color:var(--accent-ink);font-weight:600;display:grid;place-items:center;font-size:14px;margin-top:1px}
ol.steps b{font-weight:600}
.check{display:grid;gap:8px;margin-top:10px}
.check div{display:grid;grid-template-columns:auto 1fr;gap:10px;padding:10px 12px;border-radius:6px;background:var(--bg);font-size:14px}
.check .k{font-family:var(--mono);color:var(--muted);white-space:nowrap}
.check code{font-family:var(--mono);font-size:13px;word-break:break-all}
.warnbox{border-left:4px solid var(--warn);background:var(--warn-soft);padding:12px 14px;border-radius:6px;font-size:14px}
table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--muted);font-size:12px;letter-spacing:.04em;text-transform:uppercase}
td.m{font-family:var(--mono);font-size:13px}
.tablewrap{overflow-x:auto}
textarea{width:100%;height:62vh;min-height:320px;resize:vertical;background:var(--code-bg);color:var(--code-ink);border:1px solid var(--line);border-radius:8px;padding:14px;font-family:var(--mono);font-size:12.5px;line-height:1.5;white-space:pre;overflow:auto;tab-size:4}
textarea:focus-visible{outline:3px solid var(--accent)}
.small{font-size:13px;color:var(--muted)}
@media (prefers-reduced-motion: no-preference){ .status{transition:opacity .2s} }
</style>

<div class="wrap">
  <header class="hero">
    <div>
      <div class="eyebrow">TradingView · Pine Script v6 · 美股 1 分鐘 MACD 動能策略</div>
      <h1 id="scriptName">__NAME__</h1>
      <p class="lead">這一頁把整份程式碼一次寫進剪貼簿。從檔案預覽視窗複製會在 8 KB 處被截斷, 這裡不會。</p>
    </div>
    <div class="card">
      <div class="actions">
        <button class="primary" id="copyAll" type="button">複製全部程式碼</button>
        <button class="secondary" id="copyName" type="button">複製腳本名稱</button>
        <span class="meta"><span id="mLines">— 行</span><span id="mBytes">— KB</span><span>最後一行 = END OF FILE</span></span>
      </div>
      <div class="status" id="status" role="status" aria-live="polite" style="margin-top:12px"></div>
    </div>
  </header>

  <section class="card">
    <h2>貼上步驟</h2>
    <ol class="steps">
      <li><span><b>圖表週期切 1 分鐘</b>, 開美股標的 (例如 NASDAQ:NVDA)。</span></li>
      <li><span><b>按上面「複製全部程式碼」</b>。若瀏覽器擋住剪貼簿, 改點進下方黑色程式碼框 → Ctrl+A → Ctrl+C (Mac 用 ⌘)。</span></li>
      <li><span>打開 <b>Pine Editor</b>, 點進編輯區 → Ctrl+A 全選舊內容 → Ctrl+V 貼上。</span></li>
      <li><span><b>檢查最後一行</b>: 捲到最底, 行號要是 <span class="name" id="cLines">—</span>, 內容以 <span class="name">// ═══ END OF FILE ═══</span> 開頭。看不到這一行 = 貼上的內容被截斷, 回到第 2 步。</span></li>
      <li><span><b>Save</b> (Ctrl+S) → 名稱欄輸入 <span class="name" id="cName">__NAME__</span>。TradingView 預填的名稱可能少了結尾的 <span class="name">)</span>, 請補上; 「複製腳本名稱」按鈕貼的就是完整名稱。</span></li>
      <li><span><b>Add to chart</b> → 打開 Strategy Tester 看交易清單; 圖上右上角有報表。</span></li>
    </ol>
    <div class="check">
      <div><span class="k">第 1 行</span><code id="cFirst">—</code></div>
      <div><span class="k">第 __STRAT_LINE__ 行</span><code>strategy("__NAME__", shorttitle="__NAME__", …)</code></div>
      <div><span class="k">最後一行</span><code id="cLast">—</code></div>
    </div>
  </section>

  <section class="card">
    <h2>之前為什麼一直報 Missing closing parenthesis</h2>
    <p class="small" style="margin-bottom:10px">兩次報錯的位置, 都剛好落在貼上內容的第 8192 個 byte。檔案本身沒有語法問題, 是複製過程只帶走了前 8 KB, 最後一句從中間被切斷。</p>
    <div class="tablewrap">
    <table>
      <tr><th>版本</th><th>TradingView 報錯的行</th><th>那一行在原檔的 byte 位置</th><th>結論</th></tr>
      <tr><td class="m">(09.19;12:34)</td><td class="m">showClusterBox = input.bool(…</td><td class="m">8150 – 8245</td><td>8192 落在句子中間</td></tr>
      <tr><td class="m">(09.19;13:02)</td><td class="m">depthPctl = input.float(…</td><td class="m">7171 – 7289 (+ 編輯器頂端多出 13 行 ≈ 900 bytes)</td><td>8192 落在句子中間</td></tr>
    </table>
    </div>
    <div class="warnbox" style="margin-top:12px">整份檔案約 __KB__ KB, 任何只載入「前 8 KB」的預覽視窗都會截斷它。之後所有版本檔尾都有 END OF FILE 標記, 貼完看一眼最後一行就知道有沒有貼齊。</div>
  </section>

  <section class="card">
    <h2>完整程式碼 <span class="small">(備用: 點進框內 Ctrl+A → Ctrl+C)</span></h2>
    <textarea id="code" readonly spellcheck="false" aria-label="Pine Script 完整程式碼"></textarea>
  </section>
</div>

<script type="text/plain" id="pine-src">__SRC__</script>
<script>
(function(){
  var src = document.getElementById('pine-src').textContent;
  // <script type="text/plain"> 內的換行原樣保留; 只去掉包裝時多出的首尾換行
  src = src.replace(/^\n/, '').replace(/\n+$/, '') + '\n';
  var lines = src.split('\n'); if (lines[lines.length-1] === '') lines.pop();
  var bytes = new TextEncoder().encode(src).length;
  var name = __NAME_JSON__;
  document.getElementById('code').value = src;
  document.getElementById('mLines').textContent = lines.length + ' 行';
  document.getElementById('mBytes').textContent = (bytes/1024).toFixed(1) + ' KB';
  document.getElementById('cLines').textContent = lines.length;
  document.getElementById('cFirst').textContent = lines[0];
  document.getElementById('cLast').textContent = lines[lines.length-1];
  var st = document.getElementById('status');
  function show(ok, msg){ st.className = 'status ' + (ok ? 'ok' : 'bad'); st.textContent = msg; }
  function fallbackCopy(text){
    var ta = document.getElementById('code');
    if (text !== src) { ta = document.createElement('textarea'); ta.value = text; ta.setAttribute('readonly',''); ta.style.position='fixed'; ta.style.opacity='0'; document.body.appendChild(ta); }
    ta.focus(); ta.select(); ta.setSelectionRange(0, text.length);
    var ok = false; try { ok = document.execCommand('copy'); } catch(e) { ok = false; }
    if (ta !== document.getElementById('code')) document.body.removeChild(ta);
    return ok;
  }
  function copy(text, label){
    var done = function(){ show(true, '已複製 ' + label + ' ✓  → 到 Pine Editor 按 Ctrl+A 再 Ctrl+V, 然後檢查最後一行'); };
    var fail = function(){ show(false, '瀏覽器擋住了自動複製。請點進下方程式碼框, 按 Ctrl+A 再 Ctrl+C (Mac 用 ⌘), 內容一樣完整。'); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function(){ fallbackCopy(text) ? done() : fail(); });
    } else { fallbackCopy(text) ? done() : fail(); }
  }
  document.getElementById('copyAll').addEventListener('click', function(){ copy(src, '全部程式碼 (' + lines.length + ' 行, ' + bytes + ' bytes)'); });
  document.getElementById('copyName').addEventListener('click', function(){ copy(name, '腳本名稱 ' + name); });
})();
</script>
"""


def make(pine_path: str, out_path: str) -> None:
    src = io.open(pine_path, encoding='utf-8').read()
    assert '</script' not in src.lower() and '<!--' not in src, 'Pine 原始碼含 HTML 不安全序列'
    m = re.search(r'strategy\("([^"]+)", shorttitle="([^"]+)"', src)
    assert m and m.group(1) == m.group(2), 'strategy 標題與 shorttitle 不一致'
    name = m.group(1)
    kb = f'{len(src.encode()) / 1024:.1f}'
    strat_line = next(i for i, l in enumerate(src.split('\n'), 1) if l.startswith('strategy('))
    html = (TEMPLATE.replace('__TITLE__', name.split('-(')[0] + ' 貼上工具')
                    .replace('__NAME_JSON__', json.dumps(name, ensure_ascii=False))
                    .replace('__NAME__', name)
                    .replace('__KB__', kb)
                    .replace('__STRAT_LINE__', str(strat_line))
                    .replace('__SRC__', '\n' + src))
    io.open(out_path, 'w', encoding='utf-8', newline='\n').write(html)
    print(f'{out_path}: {len(html.encode())} bytes, 內嵌 {name} ({src.count(chr(10))} 行)')


if __name__ == '__main__':
    make(sys.argv[1], sys.argv[2])
