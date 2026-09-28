# R1 – R9.3 手動回測批次 (統一 `r()` 前綴命名)

本資料夾是把這個 chat session 產生過的全部 10 個策略版本 (R1 基準 → R2–R8 逐步簡化 → R9 合併副圖 → R9.1/R9.2 回測周期調整 → R9.3 模式 4 減敏) 的 `.pine` 檔,**原封不動複製一份**、只改檔名前綴與檔內對應的 `strategy()`/`indicator()` 標題字串 (title = shorttitle = 檔名, 專案既有規則),方便你自己在 TradingView 手動回測、比較。

**除了名字字串, 每個檔案的程式邏輯、行數、其餘內容跟原始檔案逐字元相同** (已用 diff 逐檔核對, 只有 header 註解第一行 / `strategy()`or`indicator()` 的 title+shorttitle / 檔尾 `END OF FILE` 標記這 3 處字串換了新名字)。

## 怎麼用

- 每個版本一組 2 或 3 個檔案要**一起貼到同一張圖上** (Add to chart):
  - `r{n}_dashboard_...` = 主策略 (會真的下單、算 Total Return, 在 TradingView 用 Strategy Tester 分頁看)
  - R1–R8: 另外還有 `r{n}_RSI-mode2_...` (模式 2 副圖) + `r{n}_winrate-mode4_...` (模式 4 副圖), 兩個都要加
  - R9–R9.3: 副圖已合併成一個 `r{n}_RSI-winrate_...`, 只要加這一個
- 貼上方式跟之前一樣: Pine Editor → New blank script → 全選貼上 → Save (存檔名稱貼成跟檔案內 `strategy("...")` 裡的名字一模一樣,含冒號那個時間格式,不是檔名的句點版) → Add to chart。
- 檔尾若看不到 `// ═══ END OF FILE ═══` 那一行 = 貼上內容被截斷 (常見是檔案預覽視窗只載入前 8KB),請改用文字編輯器開啟整份 `.pine` 再複製。

## 對照表 (舊檔名 → 新檔名)

| 版本 | 角色 | 新檔名 | 舊檔名 (原始出處) |
|---|---|---|---|
| R1 | dashboard (mode 1-4, 原始基準) | `r1_dashboard_(mode 1-4)_(09月20日; 21.59).pine` | `US_A_R1_strat_mode_1-4_(09月20日; 21.59).pine` |
| R1 | RSI 模式2 副圖 | `r1_RSI-mode2_(09月20日; 21.59).pine` | `US_A_R1_indict_mode_2_RSI_(09月20日; 21.59).pine` |
| R1 | winrate 模式4 副圖 | `r1_winrate-mode4_(09月20日; 21.59).pine` | `US_A_R1_indict_mode_4_winrate_(09月20日; 21.59).pine` |
| R2 | dashboard | `r2_dashboard_(mode 2,4)_(09月26日; 17.40).pine` | `US_A_R2_strat_mode_1-4_(09月26日; 17.40).pine` |
| R2 | RSI 模式2 副圖 | `r2_RSI-mode2_(mode 2,4)_(09月26日; 17.40).pine` | `US_A_R2_indict_mode_2_RSI_(09月26日; 17.40).pine` |
| R2 | winrate 模式4 副圖 | `r2_winrate-mode4_(mode 2,4)_(09月26日; 17.40).pine` | `US_A_R2_indict_mode_4_winrate_(09月26日; 17.40).pine` |
| R3 | dashboard | `r3_dashboard_(mode 2,4)_(09月26日; 21.11).pine` | `US_A_R3_strat_mode_1-4_(09月26日; 21.11).pine` |
| R3 | RSI 模式2 副圖 | `r3_RSI-mode2_(mode 2,4)_(09月26日; 21.11).pine` | `US_A_R3_indict_mode_2_RSI_(09月26日; 21.11).pine` |
| R3 | winrate 模式4 副圖 | `r3_winrate-mode4_(mode 2,4)_(09月26日; 21.11).pine` | `US_A_R3_indict_mode_4_winrate_(09月26日; 21.11).pine` |
| R4 | dashboard | `r4_dashboard_(mode 2,4)_(09月26日; 21.33).pine` | `US_A_R4_strat_mode_1-4_(09月26日; 21.33).pine` |
| R4 | RSI 模式2 副圖 | `r4_RSI-mode2_(mode 2,4)_(09月26日; 21.33).pine` | `US_A_R4_indict_mode_2_RSI_(09月26日; 21.33).pine` |
| R4 | winrate 模式4 副圖 | `r4_winrate-mode4_(mode 2,4)_(09月26日; 21.33).pine` | `US_A_R4_indict_mode_4_winrate_(09月26日; 21.33).pine` |
| R5 | dashboard | `r5_dashboard_(mode 2,4)_(09月26日; 21.53).pine` | `US_A_R5_strat_mode_1-4_(09月26日; 21.53).pine` |
| R5 | RSI 模式2 副圖 | `r5_RSI-mode2_(mode 2,4)_(09月26日; 21.53).pine` | `US_A_R5_indict_mode_2_RSI_(09月26日; 21.53).pine` |
| R5 | winrate 模式4 副圖 | `r5_winrate-mode4_(mode 2,4)_(09月26日; 21.53).pine` | `US_A_R5_indict_mode_4_winrate_(09月26日; 21.53).pine` |
| R6 | dashboard | `r6_dashboard_(mode 2,4)_(09月26日; 22.09).pine` | `US_A_R6_strat_mode_1-4_(09月26日; 22.09).pine` |
| R6 | RSI 模式2 副圖 | `r6_RSI-mode2_(mode 2,4)_(09月26日; 22.09).pine` | `US_A_R6_indict_mode_2_RSI_(09月26日; 22.09).pine` |
| R6 | winrate 模式4 副圖 | `r6_winrate-mode4_(mode 2,4)_(09月26日; 22.09).pine` | `US_A_R6_indict_mode_4_winrate_(09月26日; 22.09).pine` |
| R7 | dashboard | `r7_dashboard_(mode 2,4)_(09月26日; 22.25).pine` | `US_A_R7_strat_mode_1-4_(09月26日; 22.25).pine` |
| R7 | RSI 模式2 副圖 | `r7_RSI-mode2_(mode 2,4)_(09月26日; 22.25).pine` | `US_A_R7_indict_mode_2_RSI_(09月26日; 22.25).pine` |
| R7 | winrate 模式4 副圖 | `r7_winrate-mode4_(mode 2,4)_(09月26日; 22.25).pine` | `US_A_R7_indict_mode_4_winrate_(09月26日; 22.25).pine` |
| R8 | dashboard | `r8_dashboard_(mode 2,4)_(09月27日; 00.58).pine` | `US_A_R8_strat_mode_1-4_(09月27日; 00.58).pine` |
| R8 | RSI 模式2 副圖 | `r8_RSI-mode2_(mode 2,4)_(09月27日; 00.58).pine` | `US_A_R8_indict_mode_2_RSI_(09月27日; 00.58).pine` |
| R8 | winrate 模式4 副圖 | `r8_winrate-mode4_(mode 2,4)_(09月27日; 00.58).pine` | `US_A_R8_indict_mode_4_winrate_(09月27日; 00.58).pine` |
| R9 | dashboard (overlay) | `r9_dashboard_(mode 2,4)_(09月27日; 23.15).pine` | `US_A_R9_strat_mode_2-4_(09月27日; 23.15).pine` |
| R9 | RSI+winrate 合併副圖 | `r9_RSI-winrate_(mode 2,4)_(09月27日; 23.15).pine` | `US_A_R9_indict_mode_2-4_RSI-winrate_(09月27日; 23.15).pine` |
| R9.1 | dashboard (3 個月回測) | `r9.1_dashboard_(mode 2,4)_(09月28日; 09.34).pine` | `US_A_R9.1_strat_mode_2-4_(09月28日; 09.34).pine` |
| R9.1 | RSI+winrate 合併副圖 | `r9.1_RSI-winrate_(mode 2,4)_(09月28日; 09.34).pine` | `US_A_R9.1_indict_mode_2-4_RSI-winrate_(09月28日; 09.34).pine` |
| R9.2 | dashboard (12 個月回測) | `r9.2_dashboard_(mode 2,4)_(09月28日; 09.50).pine` | `US_A_R9.2_strat_mode_2-4_(09月28日; 09.50).pine` |
| R9.2 | RSI+winrate 合併副圖 | `r9.2_RSI-winrate_(mode 2,4)_(09月28日; 09.50).pine` | `US_A_R9.2_indict_mode_2-4_RSI-winrate_(09月28日; 09.50).pine` |
| R9.3 | dashboard (模式4 減敏 10%) | `r9.3_dashboard_(mode 2,4)_(09月28日; 10.10).pine` | `US_A_R9.3_strat_mode_2-4_(09月28日; 10.10).pine` |
| R9.3 | RSI+winrate 合併副圖 | `r9.3_RSI-winrate_(mode 2,4)_(09月28日; 10.10).pine` | `US_A_R9.3_indict_mode_2-4_RSI-winrate_(09月28日; 10.10).pine` |

備註: R2–R8 原始檔名裡的 `(mode 1-4)` 是從 R1 沿用下來的舊標籤 (其實 R2 開始已經只剩模式 2/4 在跑),這批重新命名時一併改標成準確的 `(mode 2,4)`,純粹是名稱更正,不影響任何程式邏輯。
