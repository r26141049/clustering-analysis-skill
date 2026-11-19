# Clustering Analysis Skill post4 — R4E 集中修復與本機驗收

**版本**：`v1.0.0rc6.post4.dev8`；**狀態**：獨立開發候選，**未正式 ACCEPTED**。  
**基線**：`Clustering_post4_R4D_DEVELOPMENT.zip`，不覆寫 R4D 或既有 Two Moons 研究。  
**修復範圍**：`P4-S3S4-RESULT-BOUNDARY-01`、Stage 4 研究圖表交付、Stage 5 幾何討論，以及候選命名一致性；保留四方法、Hard Gate、研究附件與五段可執行 Python 程式碼。

## 一、本輪修復實作

| 項目 | 具體修改 | 本機判定 |
|---|---|---|
| Stage 3／4 實際執行界線 | `session.fit_candidates()` 只執行經 Stage 3 授權的**全資料候選擬合**；停止提前執行重抽樣。`diagnose()` 在 Stage 4、原先預先核准的 `diagnostics_plan` 內執行 ARI 重抽樣，保存實際執行事件與結果。候選的 Silhouette 在底層擬合時仍計算並封存，但**不在 Stage 3 的使用者評估表揭露**，於 Stage 4 統一分析。 | PASS_LOCAL；注意「Silhouette 底層計算時點未搬移」|
| Hard Gate 與擴展重用 | Stage 3 候選執行及結果確認仍是兩個獨立 Gate；Stage 4 未額外使用未批准的評估預算。新的增量候選須重新取得 Stage 3 授權；已完成的 Stage 4 ARI 批次在設定一致時直接重用，只執行新候選。R4D 舊版本已存的 Stage 3 ARI 具相容讀取路徑；未驗證對所有歷史狀態的完整升版遷移。 | PASS_LOCAL（新版本正向與重用案例） |
| Stage 3 圖像 | Stage 3 僅呈現候選的初步群數概覽，不提前顯示最終選群圖或穩定性圖。 | PASS_LOCAL |
| Stage 4 圖像 | 新增由**實際保存標籤**繪製的 `candidate_partitions.png/.svg`；同階段提供品質、穩定性、DBSCAN 參數敏感性等已批准圖。正式批准最終候選後，Stage 4 立即產生 `stage4_selected_partition.png/.svg`。Stage 5 引用同一張已核准的選群圖，校驗其 SHA-256 與標籤來源。 | PASS_LOCAL（2D 案例） |
| Stage 5 幾何解釋 | 若 Stage 1 已確認非凸／彎曲觀察，結合最終實際標籤、兩軸原始位置範圍、中位數差異、核心／邊界／雜訊數量等撰寫幾何討論；未確認的資料不擅自稱為彎月。若只是兩特徵投影，不聲稱涵蓋所有維度。 | PASS_LOCAL（R4D Two Moons 封存資料唯讀核對） |
| 候選名稱 | DBSCAN 對話／圖表／新研究正文使用 `D1…Dn`；其他三種方法使用 `C1…Cn`。保留原始核准理由與稽核紀錄，不竄改舊決策文字。 | PASS_LOCAL |

**安全界線**：R4E 不對未經批准的參數、距離、模型或前處理執行擬合。Stage 4 重抽樣仍屬 Stage 3 明示授權的計算計畫；發生超時時不以原批准自動重試。Stage 4 的輸出圖表是已有標籤的可視化，不新增模型。對已封存 Two Moons 資料本輪只做**唯讀檢查**。

## 二、已執行的測試

| 驗收項目 | 結果 | 備註 |
|---|---|---|
| 舊版快速功能與相容回歸 | **23/23 PASS** | `test_post4`（6）、`test_post4_local`（5）、`test_post4_r3_explanations`（5）、`test_post4_r4d`（7）|
| 新 Stage 3／4 真實階段與附件測試 | **PASS** | `test_post4_r4e.py::test_stage4_executes_real_stability_and_delivers_actual_figures`；驗證 Stage 3 無重抽樣、Stage 4 附件、最終模型圖、正文引用與離線 HTML 五段收合程式碼 |
| Stage 4 已核准增量擴展重用 | **PASS** | `test_post4_r4e.py::test_authorized_incremental_extension_reuses_stage4_subsampling`；舊 2 組重用、新 1 組才執行 |
| K-means Stage 4 穩定性及初始化診斷 | **PASS** | `test_post4_r4e.py::test_kmeans_stage4_stability_and_initialization_without_duplicate_full_fits` |
| DBSCAN 完整五階段與嚴格重現 | **PASS** | 單獨執行既有 R4C 五階段 E2E 測試 |
| PAM/Gower 完整五階段與嚴格重現 | **PASS** | 單獨執行既有 R4C 五階段 E2E 測試 |
| Hierarchical/Ward 完整五階段與嚴格重現 | **PASS** | 單獨執行既有 R4C 五階段 E2E 測試 |
| Hierarchical/Gower 完整五階段與嚴格重現 | **PASS** | 單獨執行既有 R4C 五階段 E2E 測試 |
| K-means 完整五階段嚴格重現 | **TIMEOUT／NOT VERIFIED** | E2E 已進入 `reproduce.py --verify` 子程序時逾時；不能列為 PASS；另有獨立 Stage 4 功能測試 PASS |
| Two Moons 420 筆封存資料唯讀對照 | **PASS** | 兩群各 204 筆、12 筆雜訊、原本 Stage 1 經確認的彎曲及非凸 EDA；不重擬合 |
| Quarto CLI 原生 render | **NOT RUN** | 離線 HTML 備援已由 DBSCAN 等 E2E 涵蓋 |
| ChatGPT/Work 真人介面與安裝 | **NOT RUN** | 必須由使用者在目標平台驗收 |

上述「各自 PASS」指單獨執行成功，不宣稱一個大批次所有測試都通過。逾時不視為 PASS。

## 三、特別揭露與後續驗收

1. **Silhouette 的計算時點**：R4E 保留 `engine.fit_one()` 的原有評估計算（避免更動四種統計核心與現有嚴格重現契約），但 Stage 3 **不再把它當成選群比較或呈現其數值**；Stage 4 才整理指標及作出判讀。ARI 的重抽樣計算則**確實從 Stage 3 移至 Stage 4**。若後續要求 Silhouette 也必須在計算層完全延後，應另列受控核心改版，不宜假稱本輪已做。
2. 兩數值維度以外的研究，圖中若採數值二維視圖，只視為描述性投影，並明示其他變數未顯示。沒有兩個可用數值欄位時不憑空生成分群散佈圖，仍保留群大小／品質／穩定性等相關圖。
3. 重新生成 Stage 5 不得偷改先前核准的模型、標籤或研究結果；舊版已完成交付應保留原始封存狀態。
4. 正式發布前應再真人測試 Two Moons 的 Stage 3／4 PNG 交付時機、選定模型的 Stage 4 PNG 及 Stage 5 敘述，並完成 Quarto 原生轉譯與 K-means 嚴格重現延遲診斷。

**結論**：本輪指定的階段界線及圖表／報告修復已形成可測試的 R4E 開發候選；**不是**正式發布版。
