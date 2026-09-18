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
├── tradingview/macd_momentum_1m.pine     ← TradingView 版 (Pine v6 strategy, 內建回測器)
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
