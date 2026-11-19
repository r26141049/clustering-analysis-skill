# Clustering Analysis Skill — R4H 修補與驗收紀錄

**開發候選版本**：`v1.0.0rc6.post4.dev11`（R4H；非正式 ACCEPTED）  
**基線**：原始 `Clustering_post4_R4G_DEVELOPMENT.zip`；保留原版、不從零建立、不重擬合原已核准研究。  
**修補範圍**：研究設計／通用解釋／對外名稱，保留 R4G 持久化、R4E Stage 3／4 分工、Hard Gate 與舊報告重現。

## 九項需求與實際實作

| ID | 修補內容 | 程式／報告結果 | 本輪驗證 |
|---|---|---|---|
| P4-S1-FEATURE-ROLE-GATE-01 | Stage 1B 變數角色獨立授權 | 新 CLI 研究預設進入 `S1_ROLE_REVIEW`，角色 `feature/supplementary/id/exclude`；另行批准前處理；改角色需撤銷下游批准 | 新增 gate／修訂測試 PASS |
| P4-S1-EDA-VARIABLE-LABEL-01 | EDA 真實變數標籤 | `figures.py` 與 `workflow_evidence.py` 使用原始欄名，不輸出 F1/F2 | 檔案 SVG／PNG 測試 PASS |
| P4-S2-GOWER-SYMBOL-01 | Gower 權重與差異符號 | Stage 2 對話與報告解釋 `w_k`、`δ_ijk`、可比較集合；全部權重為 1 時明示等權重；否則列實際權重 | 報告整合 PASS |
| P4-S2-METHOD-REASON-01 | 方法推薦依據 | 非全數值的混合資料且 Gower 可用時，對 K-medoids 給出具體適用性優先理由；不宣稱擬合後優勝 | R4D Stage 2 7 測試 PASS |
| P4-S3-EDA-ADAPTIVE-K-01 | 自適應候選 K | 使用有界、未擬合的多變量 MST 間隙 EDA，區分三個明顯分離區域與沒有分離證據；檢查尺度依賴並與運算預算結合；最終需候選 Hard Gate | 三群／無明顯群／候選計畫測試 PASS |
| P4-S4-MEDOID-VIS-01 | 真實 medoid 解釋 | 取消 medoid 原始列號 Y 軸散佈圖；另存真實 medoid 特徵／群組人數並列於 Stage 4 | K-medoids E2E PASS |
| P4-S5-NUMERIC-DIFFERENCE-01 | 通用數值與事後分析 | 根據已核准群標籤輸出群間均值、中位數、SD、IQR、大小及特徵角色限制；補充變數合併與指定 Spearman；不自動做迴歸 | 群間差異單元＋報告 E2E PASS |
| P4-S5-METHOD-TEXT-01 | 不混用 DBSCAN/PAM 術語 | 幾何報告僅在 DBSCAN 情境使用密度連通文字；其他方法使用多維距離限制 | K-medoids E2E 文本驗證 PASS |
| P4-ALL-KMEDOIDS-NAMING-01 | 對外名稱 K-medoids | Stage 2～5、README、SKILL 對外顯示 K-medoids（PAM 演算法）；內部 `pam` ID 與計算實作不變 | 舊 PAM/Gower Session 與重現 PASS |

## 重要的相容性與研究限制

1. **新研究**：JSON CLI `create` 預設啟用獨立 Stage 1B 角色 Hard Gate。必須先確認角色，才能提出前處理；使用者不得把建議當成自動批准。
2. **舊研究**：既有 R4G Session 可讀取；Python `Session.create` 保持舊研究 API 預設，或 JSON CLI 明確傳入 `require_feature_roles: false` 做舊流程兼容。後者不是新研究建議流程，也不能憑空新增舊角色批准。歷史 R4G CLI 測試僅做明確的相容性參數更新，驗證原持久化行為。
3. 自適應 MST 分離線索只對 **18～500 筆、最多 15 特徵**執行，遇到缺失或不可比較距離時保留 `INCONCLUSIVE/NOT_ASSESSED`；即使提示 K=3，也不是推定自然最佳群數，仍須 Stage 4 指標與授權。
4. Stage 5 的數值／類別比較皆為描述性研究；事後指定的變數關聯使用 Spearman，不是條件迴歸、因果估計或顯著性聲明。未另行核准的變數不參與模型。
5. R4G 的 Session 恢復與平台持久化要求不變；若宿主清除整個持久化資料，不能假造批准。
6. 繼續禁止研究示意圖／網路圖片；研究圖表只能由本次真實觀測與批准結果產生。

## 本輪實測（只列真正執行）

| 範圍 | 結果 | 證據 |
|---|---|---|
| R4H 新增測試（5 項） | **5 PASS** | `scripts.test_post4_r4h`；包括角色 Hard Gate、失效授權、三群／無群 EDA、Stage 3 參數規劃、真實標籤及 posthoc |
| R4F 圖表來源與指標說明（4 項） | **4 PASS** | `scripts.test_post4_r4f` |
| R4G Session 持久化與恢復（4 項） | **4 PASS** | `scripts.test_post4_r4g_session_persistence`，舊入口明示相容旗標 |
| R4E Stage 4／增量擴展（3 項） | **3 PASS** | `scripts.test_post4_r4e` |
| R4D Stage 2／DBSCAN eps（7 項） | **7 PASS** | `scripts.test_post4_r4d` |
| 合計不重複專項測試 | **23 PASS** | 執行日誌保存在開發交接包 |
| 新 Stage 1B→Stage 5 K-medoids／Gower 小型 E2E | **PASS** | 實際 20 筆混合型測試資料、兩組候選、2 次重抽樣、事後分析 CSV／完整報告 |
| 嚴格重現 `reproduce.py --verify` | **PASS，兩候選均 verified** | `r4h_reproduce_pam.log` |
| 解壓後匯入、ZIP CRC/結構 | 待封裝後核對 | 封裝測試結果另見下方交付校驗 |
| 原本的大型一次性全套測試 | **TIMEOUT／未驗證完成** | `r4h_regression_01.log`；不可計 PASS |
| 五種方法各自完整 R4H E2E | **NOT RUN（僅本輪 K-medoids 完整 E2E）** | 不繼承舊版 PASS 為本輪結果 |
| ChatGPT／Work 真人授權與跨回合、原生 Quarto | **NOT RUN** | 須使用者後續真人驗收 |

## 實證來源與未更動範圍

本輪 PAM/Gower 測試資料為程式化小型 QA fixture，**不是**使用者先前核准的 244 筆 Restaurant Tips 研究重跑。原研究結果沒有被改寫或重新擬合。舊版已核准研究 ZIP／HTML 的檔案不因本輪修改而回溯變動。

**本輪判定**：R4H 開發候選可進入真人研究驗收，**NOT ACCEPTED** 為正式 post4 發行版。
