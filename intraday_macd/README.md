# MACD 動能蓄積交叉策略 · 1 分鐘 intraday · 三平台版本

依附圖規則: **負動能段儲夠(藍圈紅柱)→ DIF 上穿 DEA(藍線)買入;正動能段儲夠(橙圈綠柱)→ DIF 下穿 DEA(紅線)賣出**。動能不足的交叉一律忽略。長倉 only,收市前強制平倉。

## 目錄

```
intraday_macd/
├── config.json                 ← 標的/時段/參數 都在這裡改 (預設 港股 07709)
├── config_loader.py
├── macd_momentum_core.py       ← 共用引擎: 指標/訊號/回測/網格搜尋 (三平台同一套邏輯)
├── backtest_cli.py             ← 任何 1 分鐘 CSV 直接回測
├── make_sample_data.py         ← 合成數據 (只用來自測引擎, 不是真實 07709)
├── tradingview/
│   ├── TW-1D-MACD-(MM.DD;HH.MM).pine       ← TradingView 【日線版】  本金100K / 一年 / 交易報表
│   ├── TW-1M-MACD-(MM.DD;HH.MM).pine     ← TradingView 【1分鐘版】 本金100K / 30天 / 盤中時段+收市強平
│   └── macd_momentum_1m.pine             ← 舊的 1 分鐘版 (已被 TW-1M-MACD 取代, 保留作對照)
├── futu_niuniu/
│   ├── futu_fetch_and_backtest.py        ← 牛牛 OpenAPI 抓 1 分 K → 回測
│   ├── futu_live_trader.py               ← 牛牛 模擬盤/實盤 執行器
│   └── futu_custom_indicator.txt         ← 牛牛 自定義指標公式 (圖上畫圈/線, 目視核對)
└── webull/
    ├── webull_fetch_and_backtest.py      ← Webull OpenAPI 抓 1 分 K → 回測
    ├── webull_live_trader.py             ← Webull 執行器 (預設 dry-run)
    └── webull_custom_indicator.txt       ← Webull 桌面版 自定義指標公式
```

## 規則量化(三版本一致)

| 項目 | 定義 |
|---|---|
| MACD | DIF = EMA12 − EMA26;DEA = EMA9(DIF);HIST = DIF − DEA |
| ⚠ 柱高刻度 | **牛牛 / Webull 圖上 MACD 柱 = 2×(DIF−DEA);TradingView = 1×**。三版本門檻一律以 1× 定義,對照牛牛圖讀數請除以 2 |
| 動能段 | 同號 HIST 連續段;三個量度(除以 close 轉成 %,跨標的可比):`bars` 連續根數、`area` Σ\|HIST\|/close×100、`depth` max\|HIST\|/close×100 |
| 儲夠動能 | bars ≥ `min_bars`(4) **且** area ≥ `min_area_pct`(0.15) **且** depth ≥ `min_depth_pct`(0.04) |
| 買 | 剛結束的**負**段合格 + 完成 K 上 DIF 上穿 DEA → **下一根開盤**買入 |
| 賣 | 剛結束的**正**段合格 + DIF 下穿 DEA → 下一根開盤賣出 |
| 時段 | 港股 09:30–12:00 / 13:00–16:00;15:45 後不開新倉;15:58 強平(config 可改) |
| 不設 | 止損(原題無;`stop_loss_pct` 可選開啟)、做空(`allow_short` 可選) |

門檻預設值是依附圖 30 秒線的柱高粗估(1 分鐘線柱高會更大),**請用真實數據跑 `--sweep` 校準**。

## 換標的

改 `config.json` 的 `symbol` 區塊即可(已附港股 00700 / 美股 TQQQ 範例);`market` 改 `US` 會自動切美股時段(無午休)。TradingView 版隨圖表 symbol。

## 先做回測(三條路)

**A. TradingView(最快)**:圖表切 1 分鐘 → 開 `HKEX:7709` → Pine Editor 貼上 `macd_momentum_1m.pine` → Add to chart → Strategy Tester。圖上會畫出合格段方框(藍/橙)與買賣直線(藍/紅),右上有即時「儲夠?」狀態表。

**B. 牛牛 OpenAPI**:
```bash
pip install futu-api pandas numpy      # 並登入 OpenD
cd intraday_macd/futu_niuniu
python futu_fetch_and_backtest.py --sweep            # config 標的 HK.07709, 日期見 config.backtest
```

**C. Webull OpenAPI**:
```bash
pip install webull-python-sdk-core webull-python-sdk-quotes webull-python-sdk-mdata webull-python-sdk-trade
export WEBULL_APP_KEY=... WEBULL_APP_SECRET=...
cd intraday_macd/webull
python webull_fetch_and_backtest.py --sweep
```

抓到的 CSV 都在 `data/`,之後可直接 `python backtest_cli.py --csv data/HK_07709_1min.csv --sweep`。輸出:`sample_output/*_trades.csv`(逐筆)、`*_signals.csv`(每根 K 的指標/段統計/訊號)、`*_sweep.csv`(門檻網格)。

## 引擎已通過的檢查

- 因果性:截斷到訊號 K 重算,40 個訊號 0 個不一致(無前視)
- 買訊全部在上穿 K 且前段為負且合格;賣訊對稱
- 成交價 = 訊號 K 下一根開盤;無隔夜持倉;收市強平
- 合成數據 14 日:138 次上穿 → 動能過濾後 109 個買訊(過濾掉 29 個「小群」交叉)

## 誠實說明

- 本環境無法連外抓行情,所附 `SYNTHETIC_HK_1min.csv` 為**合成**數據,只證明引擎機制正確,**其回測數字沒有任何實戰意義**(合成序列偏均值回歸,會高估此類策略)。
- Webull OpenAPI SDK 方法簽名依官方文件撰寫,你安裝的版本若有差異,只需改 `fetch_1min()` / `order()` 兩處。
- 牛牛/Webull 的自定義指標只能畫訊號,不能回測或下單;變週期 `SUM/HHV` 若編譯失敗,檔內附固定窗口備用寫法。
- 07709 是 2× 槓桿 ETF,1 分鐘線滑點與買賣價差不可忽略,`commission_bps` / `slippage_ticks` 請按實際填。


---

# 日線版 (TradingView) — 本金 100K · 一年 · 交易報表

檔案 `tradingview/TW-1D-MACD-(MM.DD;HH.MM).pine`,已按要求預設好。**`strategy()` 標題、`shorttitle`、檔名三者一致**,都帶建置時間戳(HKT),方便在 TradingView 的 script 清單分辨版本;在 Pine Editor 按 Save 時輸入同一個名即可。

## 開始用

1. 圖表 symbol 設 **`HKEX:7709`**,週期切 **D(日線)**。
2. Pine Editor 貼上該 `.pine` 檔 → Save(名稱用檔名)→ **Add to chart**。
3. 圖上會看到:回測期間淡藍底色、**持倉期間橙框**、**真正成交**的買賣直線與 B/S 三角形,右下角**回測報表**。
4. 下方 **Strategy Tester** 有官方統計;**List of Trades** 分頁是完整逐筆清單(可匯出 CSV)。

## 已預設的三項

| 要求 | 設定位置 | 預設值 |
|---|---|---|
| ① 本金 100,000 | `strategy()` 的 `initial_capital`,或 設定→Properties→Initial capital | 100,000 |
| ② 回測期間一年 | 設定→Inputs→**① 回測期間** | 「最近 N 天」勾選 + 365 天(亦可取消勾選改用指定日期區間) |
| ③ 交易報表 | 圖上右下角表格 + Pine Logs + Strategy Tester | 見下 |

## 報表內容

**摘要列**:本金、**交易次數**、勝/負、勝率、**總損益 $**、**總損益 %**、期末權益、Profit Factor、毛利/毛損、最大回撤、當前門檻值。

**逐筆列**:每筆 `#`、進場日、出場日、進場價、出場價、**損益 $**、**損益 %**(綠賺紅蝕),預設顯示最近 25 筆(Inputs→⑦ 報表 可調至 60)。

另外收盤會把同一份報表寫進 **Pine Logs**(Pine Editor 下方 Pine Logs 分頁),方便整段複製貼出。

## 圖示語意:只畫「真正成交」

| 圖示 | 意思 |
|---|---|
| ▲ 藍三角 + 藍直線 | 買單**真正成交**那一根(訊號 K 的下一根開盤) |
| ▼ 紅三角 + 紅直線 | 賣單**真正成交**那一根(含 MACD 賣訊 / 止損 / 窗口結束平倉) |
| ▭ 橙框 | **持倉期間**,由進場成交 K 框到出場成交 K,高度包住該段 MACD 柱;仍持倉會跟著最新 K 延伸 |

有訊號但沒成交的情況(已有倉時的買訊、無倉時的賣訊、回測窗外的訊號)**一律不畫**。舊版的「合格動能段框」改為 Inputs→⑧ 顯示 內的可選項,預設關閉。

標記畫在**成交 K** 而非訊號 K,比 MACD 交叉晚一根——這是設計如此,因為訂單在下一根開盤才成交,與 Strategy Tester 的 List of Trades 對得上。

## 兩個 TradingView 版本的差異

| | `TW-1D-MACD` 日線版 | `TW-1M-MACD` 1分鐘版 |
|---|---|---|
| 圖表週期 | D | 1 分鐘 |
| 回測期間預設 | 365 天 | **30 天**(1分K載入根數受方案限制) |
| 盤中時段 | 自動繞過 | **啟用**,⑤「市場預設」一鍵切 港股/美股/自訂 |
| 隔夜倉 | 可以持倉過夜 | **不留**:15:45 後不開新倉、15:58 強平 |
| 動能段最少根數 | 3 | 4 |
| 止損預設(若啟用) | 5% | 1% |
| 報表額外欄 | — | 交易日數、每日均交易、在市場時間 %、週期檢查 |

訊號邏輯(動能段門檻 + 交叉 + 下一根開盤成交 + 只畫真正成交)兩版完全相同。

### ⚠ 1 分鐘版換市場必做一步

`TW-1M-MACD` 的 **Inputs → ⑤ 盤中時段 → 市場預設** 要跟圖表商品相符:

| 市場 | 設定 | 交易時段 |
|---|---|---|
| 港股 | `港股` | 09:30–12:00 / 13:00–16:00 · Asia/Hong_Kong |
| 美股 | `美股` | 09:30–16:00 · America/New_York |
| 其他 | `自訂` | 自己填時段字串 + 時區 |

**設錯的後果是靜默的**:例如用港股設定跑 NVDA,美股的 K 線落在香港時間 21:30–04:00,跟 09:30–16:00 完全沒有重疊 → 每一根 K 都被判定為「非交易時段」→ 訊號照常產生但**一張單都不會成交,交易次數 0**。

報表會直接指出:「在市場時間」顯示紅色 0%、右上角顯示「⚠ 時段不符!」、並列出策略用的時區與該商品交易所時區的落差。

## 日線版與 1 分鐘版的三個差異(重要)

1. **沒有收市強平**:日線持倉會過夜,直到出現賣訊才平。盤中時段/午休/收市強平在日線自動繞過(程式用 `timeframe.isintraday` 判斷)。
2. **門檻刻度完全不同**:日線的 `|hist|/close` 比 1 分鐘大一個數量級(1 分鐘約 0.02–0.1%,日線約 0.5–2%)。所以日線版預設用**「自動(百分位)」門檻**——取近 250 根柱高的第 60 百分位當深度門檻,換標的、換週期都不用手調。想寫死就在 Inputs→④ 改成「手動」。
3. **回測窗結束會平倉**:令報表的總損益對應完整一年,不會留一筆未平倉扭曲數字。

## 同一套規則在本機跑(交叉驗證)

Python 引擎已支援日線(自動偵測 K 線週期,日線繞過時段邏輯):

```bash
python backtest_cli.py --csv data/HK_07709_daily.csv --auto-th --capital 100000
```

輸出會列出逐筆 `損益$ / 權益` 與「期內交易 N 筆 · 總損益 X (Y%) · 期末權益 Z」,格式與 Pine 報表一致。`--tf daily|1min|5min` 可強制指定週期預設(預設 auto 依數據判定)。
