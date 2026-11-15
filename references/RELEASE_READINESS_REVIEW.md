# rc6 Plan B — Final Release Readiness Review

日期：2026-11-15（Asia/Taipei）。範圍：只更新驗收文件與發布審查；不重新擬合、不變更統計核心、Hard Gate 或版本，不產生 Hotfix。

## 最終建議：NOT ACCEPTED

Plan B 本輪真人展示驗收達到下列 PASS，整體仍缺少必要的回歸、歷史、封裝與實際安裝證據。不能以研究個案完成或局部測試通過代替整體發布批准。

| 本輪真人驗收 | 結果 | 證據邊界 |
|---|---|---|
| Stage 1～4 PNG 在各階段決策前主動交付 | PASS | 使用者本對話最終驗收，無需事後補交 |
| Stage 1 三張 EDA PNG 真人開啟 | PASS | eda_numeric / eda_geometry / eda_categories |
| Stage 2 方法診斷 PNG 真人開啟 | PASS | 依使用者階段層級確認；原交付含 approved geometry、neighbor diagnostic |
| Stage 3 候選結果 PNG 真人開啟 | PASS | candidate_quality |
| Stage 4 品質比較與穩定性 PNG 真人開啟 | PASS | 依使用者階段層級確認；不虛構其他單檔開啟回條 |
| Stage 5 離線 HTML 真人閱讀 | PASS | 使用者實際開啟，統計圖可讀，包含 final_partition 的 K=3 圖 |
| Stage 5 各 PNG 附件逐檔下載／開啟 | NOT VERIFIED | HTML 閱讀成功不等於每個 PNG 附件都另行開啟；不得擴張 PASS |
| 聊天直接內嵌 | historical FAIL | 保留；非 Plan B 發布必要項目，不宣稱修復 |
| 原生可點選決策按鈕 | UNFINISHED | 保留；Plan B 使用 A／B／C，不宣稱技術完成 |

本輪 Stage 1～4 階段層級 PASS 不回寫低階機器 receipt 為真人逐檔開啟；使用者證詞與檔案解碼、連結建構分開保存。Stage 5 離線 HTML 曾有下載障礙，另行重交後由使用者實際開啟成功；不將第一次下載交付改寫為從未發生問題。Stage 5 PNG 逐檔確認是否仍需補驗，依現行 mandatory all-stage PNG contract 判定，未經使用者豁免不得自行免除。

## 方法與統計核心

- pyproject.toml 與 clustering_native.__version__ 均為 1.0.0rc6。
- core.METHODS 恰為 kmeans、hierarchical、dbscan、pam。engine.validate_config 只有四方法設定分支；正式 runtime Python 源碼未找到 GaussianMixture/GMM/gmm 執行實作。GMM 從目前正式 runtime 移除的靜態檢查 PASS；不能延伸為未取得 ZIP 或歷史回歸全部通過。
- K-means Lloyd／明確初始化；Hierarchical linkage／metric；DBSCAN eps/min_samples；PAM BUILD/SWAP／Gower 的程式分支存在。此次沒有擬合四方法或執行演算法回歸，統計正確性依既有可取得證據判定，缺失不補造。

## Stage 1～5 與 Hard Gate

本輪 elliptical 個案六個不同使用者回合分別批准 preprocess、method、candidates、results、final、delivery；session phase=COMPLETE、complete=true。候選擬合在 candidates 批准後，例行診斷在 results 確認後；最終 K=3 與交付確認均獨立。這證明本輪正常批准路徑，不等於拒絕、模糊、過期、重放、跨階段／跨 session 等所有對抗案例均已驗收。

靜態審查確認 Gate.approve 保留 pending/status/revision/token/expiry 檢查，結構化決策、完整回覆重新判讀、拒絕／模糊不推進、used_message_ids 防重用及 QA/user provenance 不混用。此次未改任何門控程式。回合名稱是本機追溯紀錄，不宣稱具平台身分驗證能力。

## 測試與研究交付

- 本次只重跑 scripts/test_png_attachments.py：3/3 PASS，檢查全階段附件建構、損壞／缺失檔拒絕及非法階段。這些不擬合模型，也不證明真人顯示或完整統計安全。
- quick_validate 已通過；只驗證技能結構，不等於實際插件匯入。
- 現有安裝副本缺少 tests/、evidence/、history/，以及 README 指向的 TEST_REPORT.md、NOT_RUN_TESTS.csv、FOUR_METHOD_REGRESSION.md、HUMAN_ACCEPTANCE_CHECKLIST.md 等。既有 ACCEPTANCE_MATRIX 的 I/V/L 歷史狀態不升級為本次 PASS；完整四方法與門控負向回歸 NOT VERIFIED。
- 本輪研究結果先前已執行 reproduce.py --verify，五個候選、100 次重抽與10次初始化均核對 PASS。本次只讀該結果與日誌，沒有重新執行。
- 已確認研究 manifest 狀態 USER_CONFIRMATION_RECORDED；90 個受綁定檔案雜湊全部匹配。研究交付內 reproducibility/clustering_native/*.py 與目前安裝核心逐檔一致。MD／Python QMD／內嵌圖 HTML、PNG/SVG、CSV、參數來源、逐候選取捨、原始單位 profile 與日誌存在。Quarto 未安裝，保留 honest fallback，不冒稱 rendered。

## Source／Plugin／Delivery ZIP

本對話可取得的是本輪 Stage 1～4 review ZIP、研究報告 ZIP 與離線 HTML 重交 ZIP。它們不是 rc6 軟體 Source／Plugin／Delivery 三包。

此工作區及已安裝技能中未取得正式三包，因此其版本、manifest、路徑、逐檔雜湊與相互內容一致性為 NOT VERIFIED，不能從舊文字宣稱完成。沒有讀取其他對話或未授權來源。也沒有為本審查新建三包或 Hotfix。實際 plugin-loader 匯入／安裝驗證仍 NOT RUN／未提供證據。

## 尚未完成的必要事項

1. 取得指定版本的 Source、Plugin、Delivery ZIP 與清單，逐檔核對版本／核心／必要資源一致性，驗證真實安裝載入。
2. 補齊可追溯的完整測試與歷史保留證據（含四方法、Hard Gate 負向與失效案例），核對缺失／跳過項目，不把本輪正常路徑當完整安全驗收。
3. 依 LITERATURE_AUDIT 與 ACCEPTANCE_MATRIX 完成仍屬必要的研究／文獻核對。未提供的 Gap、完整 Hennig bootstrap 等功能不能因不在本輪使用就宣稱通過；是否排除發布範圍須明確記錄。
4. 現行 all-stage PNG 規格下，Stage 5 個別 PNG 附件真人開啟仍未逐檔確認；Stage 1～4 已按使用者本輪階段層級確認 PASS，保留未指名單檔的證據粒度。
5. 發布自動驗收器 acceptance.py 仍使用舊 chat_stageN_visible 外部證據名稱，並依賴目前缺失的 tests/history/evidence。審查時必須依本 Plan B 文件解讀；不得以 historical inline FAIL 或未完成按鈕單獨阻擋 Plan B，也不得偽填舊欄位為 PASS 讓發布器通過。此證據契約對齊問題需另行處理，本次未改核心。

這些是證據不足／待核對，不等同已證實演算法有錯。使用者本輪確認的展示驗收均正式記錄；現階段仍不建議正式發布。

## 最新剩餘發布審查（Stage 5 final_partition.png 確認後）

當前覆寫：Plan B 圖片交付整體真人驗收 PASS；不再將 Stage 5 其餘個別 PNG 開啟列為發布阻擋。未指名逐檔紀錄維持原證據粒度，但依使用者產品層級明確決策完成本輪圖片驗收。前文該項阻擋僅為先前審查歷史。聊天 inline FAIL、按鈕 UNFINISHED 非必要項目。

### 1. 四方法與 Hard Gate 回歸證據

| 項目 | 當前判定 | 具體未完成事項 |
|---|---|---|
| 四方法 registry／設定分支、runtime GMM 移除 | 靜態 PASS | 不替代統計回歸 |
| K-means 本輪研究重現 | PASS（已存結果） | 此次不重新擬合 |
| K-means 完整邊界／失敗／相容性回歸 | NOT VERIFIED | 缺原始測試套件、逐案例結果與來源版本綁定 |
| Hierarchical 回歸 | NOT VERIFIED | 缺 linkage／距離相容、切樹與診斷的可追溯完整測試結果 |
| DBSCAN 回歸 | NOT VERIFIED | 缺全噪音／單群、核心／邊界／噪音及指標觀測集合的完整結果 |
| PAM／Gower 回歸 | NOT VERIFIED | 缺 BUILD/SWAP、tie、序位／二元／缺失／常數／權重完整結果 |
| Hard Gate 本輪六次正常批准 | PASS（個案） | 不是負向回歸 |
| Hard Gate 完整安全回歸 | NOT VERIFIED | 缺拒絕／模糊／缺答／過期／重放／錯誤階段與session／修訂撤銷／失敗預算案例逐項結果 |

目前安裝副本不含 tests/、evidence/、history/；README 提及的測試報告及歷史適用性檔也不在本次可取得檔案。這是證據缺口，不宣稱測試已 FAIL 或演算法出錯。不得重建歷史 PASS。

### 2. Source／Plugin／Delivery 三份 ZIP

三份正式軟體發布 ZIP 均未在本對話可取得來源中出現；每份版本、manifest、內容清單及共同核心／必要資源雜湊：NOT VERIFIED。本次研究結果 ZIP 不是軟體 Delivery ZIP。不得由檔名或舊文字代替比對，也不產生新包假冒原包。

### 3. 正式 Plugin 安裝與交付版本

本機技能 pyproject 與 __version__ 的 1.0.0rc6 一致，且本輪研究內附核心與該副本一致；這不證明正式 Plugin 已安裝或載入同一 build。缺正式 Plugin 安裝成功紀錄、安裝版本／build識別及可與 Plugin ZIP 對比的內容雜湊：NOT VERIFIED。單一版本字串相同不足以 PASS。

### 4. 研究／文獻逐項判定

- LITERATURE_AUDIT 的 Hartigan、Ward、Ester、Kaufman/Gower、Rousseeuw、CH、DB、Hubert：保留既有核心定位 V/C，不當成本輪重新逐頁核對原文或所有實作測試 PASS。完整可追溯回歸證據仍缺。
- Hennig：共同ID不放回 subsampling 的正確命名與限制已交付；完整 with-replacement bootstrap 非本版提供功能，其完整原文實作驗收為不適用於本版功能，不列為必須補做的新功能。
- Gap、Hopkins、VAT：本版不提供這些分析／固定閾值；專門驗證未完成保留，不要求為本版新增或擬合。若未來宣稱提供，需另行驗收。
- Podani 擴充、未宣稱的其他 linkage 理論擴充：本次不新增；保留待研究，不把未提供功能作發布必測功能。
- 使用者五階段／圖表／門控規格是產品要求，不假稱文獻定理。
- 原始單位profile、有效分母、MD／Python QMD／PNG與SVG／離線HTML、無天真後選p值、參數來源與逐候選取捨：本輪K-means研究交付可核對；跨四方法研究交付的完整回歸仍 NOT VERIFIED。
- Quarto渲染：本輪未安裝，誠實fallback符合規格；不是強制要求安裝Quarto的阻擋項目。

下表逐項列出既有 ACCEPTANCE_MATRIX 的非圖片規則；V 僅保留歷史記錄，I/L 不升級。不提供功能的條件規則排除本版適用範圍，其餘若缺測試證據則列 NOT VERIFIED，不能僅靠文字判通過。

| 規則 | 要求 | 歷史標記 | 本次發布證據判定 |
|---|---|---|---|
| S1-01 | 自動辨識儲存 dtype 與統計變數型態、分析角色，不以整數直接視為連續 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S1-02 | 不確定欄標記不確定、可修正，字典和實值衝突應阻止靜默確定 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S1-03 | 缺失 n/％、比例分母、完全缺失欄並列 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S1-04 | 重複 ID、完整列與去 ID 特徵重複應區分 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S1-05 | 極端值為潛在標記，禁止無同意刪除 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S1-06 | 尺度調整應根據距離、分布與研究目的而非固定 Z-score | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S1-07 | 僅在變數型態相容時採用關聯分析，不對所有欄位強制 Pearson | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S1-08 | 圖內英文、對話繁體中文、預設少量重點圖且圖和文字相鄰 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S1-09 | 前處理在核准前不動原始檔，使用分析副本 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S1-10 | A 核准才進 Stage 2，B/C 保持 Stage 1 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S2-01 | 四方法逐項提供 data-specific EDA 數值及理由 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S2-02 | 僅用 適合／有條件適用／不適合／資訊不足，沒有虛構量表 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S2-03 | 標準 K-means 只用有意義數值歐氏特徵 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S2-04 | 傳統 Ward 需歐氏幾何，不可默用 Gower + Ward | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S2-05 | DBSCAN 的密度、雜訊及 eps/min_samples 理由 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S2-07 | PAM 支援已定義合理差異度，Gower 的類別/ordinal/range 有明確設定 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S2-08 | 資訊不足時不得聲稱自然群存在、容許補診斷或停止 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S2-09 | 僅鎖定一方法，不執行跨方法競賽 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S2-10 | 更換方法若需重處理資料，返回 Stage 1 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S3-01 | 候選 K/參數清楚區分 EDA-supported 與 exploratory-only | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S3-02 | K-means 記錄 Lloyd/Hartigan 實作、n_init、seed、WCSS | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S3-03 | Hierarchical linkage 與 metric 相容，保留切樹與設定 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S3-04 | DBSCAN eps/min_samples 可探索，不指定 K；允許全雜訊 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S3-05 | DBSCAN 保存核心/邊界/雜訊而非假稱全為群 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S3-08 | PAM BUILD+SWAP 固定 tie rule、局部 1-swap 最優 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S3-09 | Gower nominal 用 exact-match，不能數值編碼 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S3-10 | Gower ordinal 明定 levels 和轉換約定 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S3-11 | Gower symmetric/asymmetric binary 分流，double-zero 適用性明確 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S3-12 | Gower 缺失做成對分母排除，無比較直接拒絕 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S3-13 | 常數 numeric 不除以零，政策與原因留紀錄 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S3-14 | 權重必須正值有限、覆蓋恰好核准的特徵 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S3-15 | 前後確認和範圍鎖定；候選模型失敗不能靜默替代 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S3-16 | O(n²) 記憶體估計及時間上限先核准 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S4-01 | 距離相容的 Silhouette（precomputed Gower）及無效群數處理 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S4-02 | 一群、全單例、全噪音等無效情況回缺失而非 0 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S4-03 | K-means WCSS 遞減不是選 K 充分條件 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S4-04 | CH/DB 不能對一般混合型 Gower 直接套 sklearn Euclidean實作 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S4-05 | DBSCAN noise 標籤/群數與輪廓適用性處理 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S4-07 | 整體 ARI 比較同一唯一 ID 集合且可重排 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S4-08 | subsample Jaccard 只在共同 ID 集合正確群組匹配 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S4-09 | 如稱 Hennig 2007 bootstrap：with-replacement + 原群誘導與最大 Jaccard | L | 不適用於本版未提供功能；限制與未驗證歷史保留 |
| S4-10 | 敏感性變體不得冒充正式資料或直接改寫核准參數 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S4-11 | 指標衝突不設任意複合評分、不強迫選最佳群 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S4-12 | 最優候選在搜尋邊界標示可擴範圍，但不可暗自擴 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S5-01 | 有 final model 時報告原始單位 numeric profile 與有效 n | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S5-02 | 類別頻數/比例、序位分布與比例分母正確 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S5-03 | PAM medoid 為實際 row、Kmeans centroid 是平均中心 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S5-04 | DBSCAN noise 不強制分到群 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S5-06 | 輔助標籤與模型特徵分開，避免資料洩漏 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S5-07 | 無最終 K 不產生冒充正式分類的 final assignments | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S5-08 | 不得用特徵再描述的天真 p 值宣稱獨立推論 | L | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S5-09 | Python-only QMD、MD、figures、CSV、config、environment 與 reference | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S5-10 | Quarto CLI 成功才可宣稱 rendered，否則 honest Markdown fallback | I | 本輪fallback合規；跨情境完整回歸未取得 |
| S5-11 | 報告、圖、CSV、群數及方法設定 cross-check | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S5-12 | 避免將敏感識別資訊不必要地輸出或發佈 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| S5-13 | 最後核准才算完成，修改早階段撤銷下游權限 | V | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |
| X-01 | Hopkins/VAT 在完成專門文獻前不得寫死判斷閾值 | L | 不適用於本版未提供功能；限制與未驗證歷史保留 |
| X-02 | Gap statistic 需要與資料型態相符的參考分布與選 K 規則 | L | 不適用於本版未提供功能；限制與未驗證歷史保留 |
| X-03 | 安裝啟動和完整使用者門控端到端與插件格式驗證 | I | NOT VERIFIED：完整測試／實證鏈未取得；保留原歷史標記 |

### 當前結論

**NOT ACCEPTED**。具體阻擋僅為：完整四方法與Hard Gate回歸證據不足；Source／Plugin／Delivery三包無法核對；正式Plugin載入版本與交付build無法對比；適用於正式四方法的必要研究驗收仍缺完整實證鏈。圖片交付、歷史內嵌FAIL、未完成按鈕、未提供的Gap／Hopkins／VAT／完整bootstrap及Quarto缺席均不另作阻擋理由。

要完成剩餘審查，需在本對話提供上述三包、對應完整測試／研究驗收報告與正式Plugin安裝版本證據；目前無法讀取其他對話的檔案。本次沒有擬合或修改核心，沒有新Hotfix。

## 2026-11-15 實際三包與研究附件核對更新

已取得並解壓本輪Source、Plugin、Delivery及五份歷史研究ZIP。舊「三包未取得」判定已由新證據取代：41個共同檔案與Delivery內嵌兩包雜湊一致PASS。19項不fit門控／設定測試及3項原附件測試PASS，六份儲存分群指標／目標值重算PASS；未重新擬合。rc5與rc6研究版本和程式差異分別保留，沒有冒稱相同版本完整回歸。圖片真人PASS保留。正式Plugin載入與build綁定未驗證；完整Session/CLI與四方法邊界回歸仍缺；目前Pillow13.0.0超出宣告<13，另需符合相依範圍的安裝證據。Iris rc6／rc5及PAM提供包仍待最後交付確認，不能據此宣稱六gate獨立流程PASS。最終建議NOT ACCEPTED。完整原始要求／既有證據／缺口／必要性及可追溯命令見FINAL_PACKAGE_REVIEW.md與本對話Release Readiness Review證據包。


---

# rc6 Plan B — 最後三項發布條件補證

日期：2026-11-15（Asia/Taipei）。本次只補測合成fixture及核對安裝／環境；不重新擬合任何已批准研究，不改分群演算法、runtime、依賴宣告或版本，不建立Hotfix。正式矩陣與本發布審查文件為唯一更新的技能檔案。

## 當前建議：NOT ACCEPTED

本次已解除Pillow隔離環境驗證缺口，並取得personal Skill的實體內容與實際Python匯入雜湊證據；新增的四方法、Session／CLI定向回歸已通過。不能將新定向測試冒稱為遺失的原始完整驗收套件。唯一仍屬既定正式驗收鏈的缺口是下列完整基線／驗收runner證據未能找回；不以獨立Plugin安裝未完成或全域Pillow13單獨否決personal Skill發布。

| 必要項目 | 當前狀態 | 精確範圍 |
|---|---|---|
| Plan B PNG、離線HTML、A／B／C真人驗收 | PASS | 沿用使用者已確認結果，不重驗不撤銷 |
| Source／Plugin／Delivery一致性 | PASS | 沿用上一輪41個共同檔案及子ZIP相同證據 |
| 原始rc5／rc6完整回歸與歷史基線找回 | NOT VERIFIED | 已搜尋本對話所有ZIP、巢狀ZIP及目前技能可取得的5個歷史版本，未找到原完整tests/history/evidence |
| 四方法合成邊界補測 | PASS | 17項，含Kmeans、Ward/Average、DBSCAN全noise／單群／core-border-noise、PAM與Gower語義及ARI |
| Session／CLI失敗與持久化補測 | PASS | 13項；修訂撤銷、重載、重放、失敗撤銷／預算消耗、輸入不可改、報告竄改及refresh失效、CLI拒絕／日誌 |
| 上輪19項Gate／設定及既有研究計算 | PASS | 保留上一輪版本限定證據，不重跑研究 |
| 原3項附件測試（Pillow12.3隔離環境） | PASS | 修正測試呼叫路徑後exit0；初始失敗日誌保留 |
| personal Skill已提供的來源與必要runtime內容 | PASS | skills.read回傳當前來源與skill_root，實體runtime與候選逐檔相同 |
| personal Skill實際Python模組匯入 | PASS | __file__、版本及17個必要模組雜湊已記錄 |
| 宿主內部自動選Skill的loader遙測 | NOT VERIFIED | 工具未暴露；不等同personal Skill實體不存在，不虛構loader事件 |
| 獨立Plugin host匯入／啟用 | NOT RUN | ZIP仍是Candidate；未測，不能宣稱正式Plugin已安裝 |
| Pillow隔離環境與宣告依賴範圍 | PASS | Pillow12.3.0，所有project宣告依賴版本符合範圍；全域13.0.0未變更 |
| PNG產生、解碼、附件建構 | PASS | 隔離Python實際產生640×480 PNG並完整解碼；非真人顯示證據 |

## 1. 找回原測試與補足缺口

archive_test_search.json列出12個外層／巢狀archive檢查。部分檔名命中evidence字串的是研究selection_evidence，不是測試套件。historical_search.json記錄本技能可取得的5個原始內容版本；均只有scripts/test_png_attachments.py，沒有完整統計／Hard Gate測試。範圍限於使用者已附檔案及本技能歷史，不搜尋其他個人技能或未授權對話。

原SKILL的工程驗收明列scripts/run_validation.py及scripts/release_check.py --summary evidence/validation_summary.json，要求原33項baselines保留；acceptance.py另依history/rc4_original_source_and_evidence.zip、RC4_TEST_APPLICABILITY.csv（248列）及當前逐案例狀態核對適用性。這些原檔／對應完整runner結果不在本次可取得來源中，因此為NOT VERIFIED，正式runner執行為NOT RUN；不能把30個新fixture測試數字當成原33基線或248適用性映射已恢復。此處不要求新增任何分群功能，也不要求重跑真人研究。

本次補測直接import未修改候選Source，另與安裝runtime逐檔一致。test_completion.py包含17個數值／方法測試與13個Session／CLI測試，使用8筆固定合成數值資料；另有微型名目／序位／二元／缺失fixture。Session fixture有qa_fixture來源標記，只驗證程式控制，不當成真人通過。錯誤注入用mock，沒有改產品程式或任何研究session。

四方法補測核對：Kmeans群數／WCSS、重複點群數失敗、迭代未收斂警告；Ward實際linkage、Average+Gower不套CH/DB；DBSCAN全noise／單群保持silhouette缺失及core/border/noise；PAM確定性tie、單swap局部性與小fixture窮舉參照；Gower名目不能當數值距離、明定完整ordinal等級、對稱／非對稱double-zero分母、pairwise缺失與常數略過、無可比pair拒絕、正權重、ARI唯一共同ID。

Session／CLI補測核對：reload保留gate/result、執行批准前不fit、solver失敗撤銷且落盤、執行回合不能再確認結果、超額diagnostics拒絕、diagnostics失敗仍消耗預算、同批不可重跑、Stage3修訂清除結果與圖片、舊Session transaction先重載再拒絕、輸入快照不可改、交付檔竄改拒絕、refresh使舊token失效、CLI錯誤退出及真實execution_events記錄。

### 原始錯誤與重驗（不刪除）

- run_2：30項首輪測試29 PASS、1 ERROR，exit1。錯誤是測試只接受PermissionError；產品在舊Session重載後以ValueError("Candidate results changed")安全拒絕，並沒有接受舊批准。test_completion_initial.py保存當時測試。僅將測試接受的安全拒絕例外改為PermissionError或ValueError，仍檢查重載後S3_PLAN狀態；run_5只重驗此項，PASS、exit0。30個不同案例最終均有PASS，但不宣稱修正後整套另跑30/30 exit0。
- run_4：附件測試的unittest discover呼叫漏設PYTHONPATH，ModuleNotFoundError、exit1；沒有進入產品測試。run_6明確設定候選Source路徑，原3項測試PASS、exit0。這是呼叫設定錯誤，不修改產品來消除失敗。
- 其餘run_0 venv建立、run_1 Pillow安裝、run_3環境／匯入、run_7歷史／雜湊核對均exit0。

完整argv／cwd／環境覆寫／耗時／退出碼在run_N.json；stdout與stderr均保存，不重建命令歷史。先前19個Gate／設定測試不重跑，仍由上一輪原始紀錄支持。

## 2. personal Skill與獨立Plugin的驗收標準

目前可驗證的實際操作載體是personal Skill：本對話可用技能來源為user/executor技能，skills.read回傳的根目錄與現有實體personal Skill一致；其Default interaction mode明訂pure Skill，操作本機clustering_native，不依賴MCP/OAuth或Plugin-UI部署。Plugin ZIP則有獨立.codex-plugin/plugin.json，描述為NOT ACCEPTED release candidate；不能只因存在該ZIP就說它已正式安裝。

personal Skill標準：確認provider提供的來源與實體根目錄、版本、必要runtime雜湊、依賴及可執行匯入。上述證據PASS。環境核對在隔離Python真正import安裝路徑，記錄clustering_native.__file__、__version__及17模組__file__/SHA256，均與候選Source相符。installation_evidence.json逐檔分開標示runtime與documentation/metadata；目前5份文件與候選不同，另有後續審查文件，均為本對話已授權驗收更新，不把它們混為統計runtime改動。

工具無法讀取宿主內部自動選用技能的完整遙測，也沒有獨立Plugin安裝／啟用回條或host載入build；保留NOT VERIFIED／NOT RUN。personal Skill發布不必強迫完成獨立Plugin流程；若要宣稱Plugin版本也正式安裝，仍需loader安裝／啟用成功及build／必要檔案雜湊回條。這不是僅憑同名畫面或使用者口述。

## 3. 隔離Pillow環境

實際命令：python -m venv --system-site-packages <workspace>/release_final/venv；venv/bin/python -m pip install --ignore-installed --no-deps --retries 0 --timeout 10 'Pillow>=9,<13'。安裝Pillow12.3.0 exit0。venv只讀沿用已符合範圍的科學套件，本地安裝Pillow；不是全依賴全新下載的容器，這點明確揭露。PIL.__file__在venv本地site-packages，sys.prefix與base_prefix不同；未寫全域Python。

依pyproject逐項檢查：numpy2.3.5、pandas2.2.3、scipy1.17.0、scikit-learn1.8.0、matplotlib3.10.8、Pillow12.3.0均符合既有specifier。原全域Pillow13.0.0不能被標成合規，但本次隔離環境已通過，故不再以全域13阻擋候選相容性驗證。未放寬<13或修改requirements。

環境／匯入／PNG證據見environment_and_import.json。未將命令匯入成功當成獨立Plugin loader成功；未將PNG解碼當成真人顯示。

## 最終判定與精確剩餘缺口

新增30個不同合成回歸案例有可追溯PASS，Pillow隔離相容PASS，personal Skill實體／程式載入比對PASS；已通過的真人與三包證據保持PASS。獨立Plugin安裝及宿主內部loader遙測仍未驗證，但不以此新增personal Skill發布條件。

**維持NOT ACCEPTED：既定完整驗收runner與原基線／歷史適用性證據仍無法取得或核對。** 此次30項補測覆蓋已指出的缺口，不能宣稱滿足未恢復的原33 baselines及適用性清單。下一步僅需找回原run_validation/release_check、原tests/history與其對應結果／版本；若另有原交付，可直接核對，不要求重新製作已存在報告。若原基線確已遺失，需另行明定可追溯替代測試清單與適用性，不能悄悄降低release checker或以PASS標籤繞過。無需重跑本輪研究，也不需要新增方法或修改演算法。

圖片聊天直接內嵌historical FAIL與原生按鈕未完成保留；二者非Plan B必要功能。全部原始研究與原Source/Plugin/Delivery ZIP未改動。


---

# rc6 Plan B 歷史回歸覆蓋收尾審查

日期：2026-11-15（Asia/Taipei）。正式交付範圍：**personal Skill**。結論：**NOT ACCEPTED**。

本次未重跑先前已通過的19／30項測試或任何已批准研究，未修改統計runtime、演算法、依賴或版本。只針對找回之具名引用的功能缺口，補6個新測試；全數PASS，exit0。既有真人PNG、離線HTML、文字選項、安裝核心雜湊及隔離Pillow12.3.0結果均維持PASS。獨立Plugin安裝仍NOT RUN，但非發布條件。

## 實際找回了什麼

已核對本對話可取得的rc6 Source／Plugin／Delivery、rc5／rc6研究內附程式、巢狀封裝與本技能可讀歷史。沿用上一輪12個archive與5個歷史內容版本的原始搜尋紀錄，沒有為了顯示新活動而重跑已通過測試。沒有提供rc4獨立Source或歷史archive；也不擅讀其他對話／其他個人技能。

1. 找回**23個具名測試引用**：來自候選references/ACCEPTANCE_MATRIX.csv。這些是case名稱與需求摘要／歷史V標記，**不是原始測試程式或可驗證逐case執行紀錄**，也不能證明它們屬原33項。
2. 從7份候選／研究內附acceptance.py找到兩個原檔的預期SHA256，已存recovered_hash_references.json。只找到hash不能還原檔案或assertions；不標為已找回原測試。
3. 原33項case清單、原248列歷史適用性表、rc6移植映射、原runner結果仍未取得。不能用23個引用計算「23/33已覆蓋」，也不能虛構其餘10項身分。

## 覆蓋分類（只對23個已知引用）

| 分類 | 數量 | 解釋 |
|---|---:|---|
| 原始測試已驗證 | 0 | 原test source／assertions／完整結果未取得，歷史V不冒充本次PASS |
| 替代測試已驗證 | 22 | 需求摘要之功能有已執行證據；非原始案例逐assertion等價證明 |
| 仍未覆蓋 | 1 | test_synthetic_data_gower_matches_prior_approved_stage3缺原fixture、當時plan及預期Gower值 |
| 正式不適用 | 不計入23個引用 | GMM功能已正式移除；其原case ID未知，僅記需求層級不適用，不捏造case數或PASS |

**原始33項與248項覆蓋率：不可計算。** 新30項、上輪19項、本次6項均不能直接相加宣稱原33已通過。完整逐引用表在Historical_Test_Coverage_Matrix.csv，列出版本資訊、需求、歷史標記、原件狀態、rc6適用性、替代函式與執行證據、等價性限制。

## 本次最小補測（全部是新測試）

| 新測試 | 對應功能引用 | 結果 |
|---|---|---|
| test_distinct_observation_sets_rejected | ARI不同觀測集合拒絕 | PASS |
| test_jaccard_hand_calculated_common_ids | 共同ID的最大Jaccard，兩個手算例 | PASS |
| test_silhouette_reference_on_fixed_partition | 固定標籤precomputed silhouette對sklearn | PASS |
| test_undefined_gower_rejected_by_model_entry | PAM／Average模型入口拒絕未定義Gower | PASS |
| test_native_n_init_forwarded | Kmeans實際n_init／Lloyd參數傳遞 | PASS |
| test_null_final_report_has_no_final_assignments | null final保留報告但不輸出正式分群名單 | PASS |

只為最後一項建立新的8筆合成Session fixture及必要程式狀態，不執行前輪測試函式或任何真人研究。數值案例同樣只用微型合成資料；沒有以mock模型結果冒充統計驗證。run_8.stderr包含CPU實體核心偵測警告／trace，測試仍完成6項OK、exit0；警告原樣保留，不隱藏。

實際命令argv／時間／cwd／退出碼在run_8.json，stdout/stderr逐字保存。執行器為release_final/venv/bin/python，Pillow12.3.0；其餘環境與所載runtime雜湊沿用environment_and_import.json。test_remaining_refs.py與所匯入的fixture模組均保存版本雜湊；新增測試不是原測試。既有30項的首輪測試例外設定錯誤與單項修正後PASS紀錄也保留，沒有洗掉歷史ERROR。

## 仍有必要條件未通過

1. **原33項基線的案例身分與斷言未知**：無法逐項確認仍適用者的版本／結果或全部建立等效測試，狀態NOT VERIFIED。需要原case清單、兩個原測試檔或含其內容的rc4／早期rc5歷史Source；提供既有原檔即可，不要求重新製作測試報告。
2. **歷史適用性／移植清單未知**：缺history/RC4_TEST_APPLICABILITY.csv及evidence/RC6_HISTORICAL_PORT.csv，不能逐case排除GMM或核對其他功能，狀態NOT VERIFIED。
3. **已知引用中的原Stage3 Gower回歸fixture仍缺**：test_synthetic_data_gower_matches_prior_approved_stage3的原資料／plan／預期值未取得。現有Restaurant Tips與新Gower手算測試不能冒稱同一fixture；狀態仍未覆蓋。

上述是具體可追溯資料缺口，不是要求恢復GMM或重新執行四份研究。沒有清單就無法證明最小替代集合已涵蓋所有原需求，因此不自行降低正式驗收條件。若後續提供原件，先以兩個預期hash與版本比對，再只處理尚未覆蓋案例；已通過項目不重跑。

## GMM與Plugin的範圍

GMM在rc5規格正式移除，在rc6四方法版不適用，既有GMM拒絕測試只證明入口拒絕，不等於GMM計算通過。無原case ID時不編造「移除N項」數字。

personal Skill為使用者確認的正式交付；可讀實體及實際Python import已PASS，文件更新與runtime分開比對。獨立Plugin未安裝／未驗收保持NOT RUN／NOT VERIFIED，不列為Plan B發布阻擋。圖片聊天直接內嵌historical FAIL、原生按鈕未完成保留，二者非必要條件。

**最終仍為NOT ACCEPTED，僅以上述三個歷史覆蓋缺口為剩餘理由。** 不將找不到的測試寫成PASS，不用新增測試數量替代原基線清單。


---

# rc6 Plan B 可追溯替代回歸驗收 — 本輪審查

日期：2026-11-15（Asia/Taipei）。正式範圍：personal Skill。**建議NOT ACCEPTED**，理由是新增補測發現現行必要相容介面的功能失敗，並非再以原始測試已遺失單獨否決。

## 歷史證據與新基準

依使用者本輪確認，原始33項與歷史適用性／移植清單、原Stage3 Gower fixture標為HISTORICAL EVIDENCE LOST。停止要求恢復原件與無限搜尋；不將它們寫成PASS。新矩陣按現行rc6規格逐需求建立，原33項數量不作新覆蓋率分母。GMM功能為正式規格移除，歷史GMM案例身分未知，不捏造case或移除數量。

本輪新基準尚待使用者正式批准歷史豁免，沒有自行豁免必要測試。原Source／Plugin／Delivery與統計runtime未改；只有正式矩陣與發布審查文件更新。已通過真人圖片、離線HTML、A/B/C、personal Skill匯入、隔離Pillow及三包一致性保留PASS，沒有重跑四份研究。

## 覆蓋矩陣的讀法

RC6_Functional_Coverage_Matrix.csv完整列出現有規格的每條要求及補充的相容／持久化／獨立Gower要求，分辨必測、非提供功能／非必要、測試原始證據、版本與範圍。它包含自動測試、既有研究數值重算、原碼審閱及真人確認；不把文件文字或歷史V標記當成自動測試PASS。rc5研究只在計算核心逐檔相同的範圍作佐證，不當rc6完整流程證明。

已保存的19項Gate／設定、30項合成邊界／Session、3項附件、6項具名功能補測及六份研究核對均引用原始結果，未重跑通過案例。本輪run9新增21項功能缺口測試：20 PASS、1 ERROR，exit1；ERROR是產品KeyError，相容性需求記FAIL，不透過改測試期待消除。run10只對此失敗進行最小獨立重現，exit1；沒有重跑20個PASS案例。

## 獨立Gower新fixture（PASS）

三筆資料：數值n=[0,10,5]；名目c=[a,b,a]；序位o=[low,high,mid]，完整levels=[low,mid,high]；非對稱二元b=[0,0,1]；常數numeric=[4,4,4]。權重n=2，其餘非恆定欄各1，常數欄weight=3但全局略過。

手算完整矩陣為[[0,1,0.5],[1,0,0.7],[0.5,0.7,0]]。例如第1/2筆的雙零b不計分母：分子2+1+1=4，分母2+1+1=4，距離1。第2/3筆分子1+1+0.5+1=3.5、分母5，距離0.7。測試直接使用這些獨立常數，不調用實作生成預期值。

將第3筆n設為missing後，手算矩陣為[[0,1,0.5],[1,0,5/6],[0.5,5/6,0]]；涵蓋成對缺失分母、名目、明定序位、非對稱雙零、正權重與常數略過，全部PASS。這是新可追溯測試，不宣稱重現已清除的歷史fixture。

## 實際功能失敗 RC6-COMPAT-01

現行SKILL明訂保留propose_method作legacy operator compatibility。透過propose_method_choices()/respond選1（Kmeans）後，已批准method payload為options/assessment/model_hash/eda_hash。相容介面propose_method('pam')直接讀old['method']，造成KeyError('method')。

run10用全新4筆合成資料，只走create／preprocessing／method，不fit任何模型；已單獨重現。來源session.py SHA256=26f5cb09abe18746b1059cc0681af87265f96f1d2c13d9bbe5fb595eadd2dced。失敗後phase仍S3_PLAN，批准方法仍kmeans，沒有越權執行或錯誤改方法；正常文字選單真人驗收不受此結果回寫。

必要期望是：若支援該方法修訂，應撤銷舊scope並提出待批准新方案；若當前階段不允許，應明確拒絕。兩者皆可，不能用未處理KeyError代替規定相容行為。本次沒有修復產品或改寬測試期待；因此必要功能尚非全PASS。

最小後續補驗：修正相容介面的payload處理後，僅重驗上述失敗路徑，並增加單方法舊payload與options新payload兩種安全分支，確認舊授權撤銷、無未批准fit、持久化後狀態一致。不要求重跑20個PASS案例或真人研究；本輪沒有擅自進行修補或產生Hotfix。

## 實際命令與環境

run9：隔離venv/bin/python rc6_replacement/test_functional_gaps.py，Ran21，20 PASS／1 ERROR，exit1。run10：同一隔離Python執行reproduce_compatibility.py，四筆最小fixture，KeyError可重現，exit1。原始stdout／stderr、argv／cwd／時間／環境覆寫保存；環境Pillow12.3.0及原科學依賴同前輪，所有實際匯入runtime SHA256仍與候選相同。新測試與fixture原碼也保存hash。

21項測試涵蓋：儲存型態／語義不確定、字典衝突、missing分母與全missing、三種重複、離群保留／前處理副本、顯式標準化轉換、相容關聯、排除ID/label、獨立Gower、拒絕編碼名目歐氏、row/memory預算、timeout錯誤、原始profile與ordinal／Noise分母、Stage1 B/C停留、四方法表／推薦／不fit、相容方法修訂（失敗）、候選來源必填、未批准敏感性拒絕、逐候選理由必填、並行CLI修訂持久化、最後交付確認同步MD/QMD/HTML。

## 發布與豁免建議

- 原歷史證據標記HISTORICAL EVIDENCE LOST且停止搜尋；其豁免草案在Historical_Evidence_Waiver_Draft.md，風險與範圍明列，**尚未批准／生效**。
- 就現行功能而言，大部分必要需求已有可追溯證據，但RC6-COMPAT-01實際FAIL，因此目前不能判定必要功能具備充分的全數通過覆蓋。這不是只剩歷史追溯缺口的情況。
- **NOT ACCEPTED**：本輪明確阻擋為RC6-COMPAT-01；歷史豁免仍待正式批准，新基準不私自替換正式發布規則。豁免不能涵蓋功能失敗。
- personal Skill為正式交付，獨立Plugin未安裝保留NOT RUN／NOT VERIFIED，非阻擋。歷史inline FAIL、原生按鈕未完成保留，非Plan B必要功能。

沒有要求恢復GMM、未驗證統計方法、Quarto或新增服務；沒有再要求提供已清除原33項。若功能失敗後續解決並取得歷史豁免批准，才可按新矩陣重新提出ACCEPTED建議。


# 歷史證據豁免草案 — 尚未批准，尚未生效

識別：RC6-PLANB-HISTORY-WAIVER-20261115。範圍只限正式personal Skill的歷史追溯資料。

建議豁免原始33項測試／assertions、歷史適用性及移植清單、原Stage3 Gower fixture的「必須恢復原件」要求；將它們永久標為HISTORICAL EVIDENCE LOST，不算PASS、不恢復虛構case、不計歷史覆蓋率，也不再要求搜尋已清除資料。

替代依據為RC6_Functional_Coverage_Matrix.csv中逐需求的現行測試／研究／真人證據，而非測試數量。這是提出的新驗收基準，須由使用者明確批准，不能只因同意提出方案就視為豁免已批准。

風險：無法再證明與早期所有assertions完全等價，無法回溯某項舊結果的具體fixture或逐版本轉移；未被現行需求與fixture捕捉的舊缺陷可能仍存在。已保存原碼／測試／命令／環境／原始日誌與SHA256，並用獨立手算Gower矩陣及四方法研究證據減輕風險，但不消除歷史不確定性。

此豁免不涵蓋任何現行必要功能FAIL或NOT VERIFIED，也不涵蓋RC6-COMPAT-01，不授權改演算法、不豁免Hard Gate、不升級Plugin安裝、不移除歷史inline FAIL。必要功能失敗必須另行處理並經定向測試通過。

目前存在RC6-COMPAT-01實際相容性失敗，因此不是「只剩歷史缺口」，本輪不建議用歷史豁免放行正式發布。草案供審閱，待功能缺口處理後再提出明確批准問題；尚未記錄任何豁免批准。


---

# RC6-COMPAT-01 最小修復與候選核對

候選：1.0.0rc6.post1；正式範圍：personal Skill；發布狀態：**NOT ACCEPTED — 歷史豁免待使用者正式批准**。本次只修method payload相容／驗證與候選版本，未改四方法solver、統計結果、Hard Gate、consent recognizer或CLI schema。

## 根因與合法schema

正常propose_method_choices()產生{options, assessment, model_hash, eda_hash}，批准回覆選擇保存在gate.approvals.method.decision.response；method()從綁定選單與已消耗的批准回覆解析選中方法。相容propose_method(method: str)只接受四個canonical方法名稱，產生{method, assessment, model_hash}，批准仍須獨立respond。兩者是已存在的格式，不是任意dict。

舊propose_method在已有批准時直接讀old['method']，遇合法options payload會KeyError。修復改為透過既有已批准decision解析方法，不補寫或重算舊payload／token。新增內部schema驗證：兩種欄位集合互斥且完整、assessment包含四個受支援方法各一次與合法status、options非空且不重複並屬可用方法、model/EDA綁定相符。缺少／錯型／未知值清楚ValueError；非批准或無scope仍由原Gate拒絕，不把任何內容當批准。

requested method先做白名單驗證，未知方法不得先撤銷合法scope。已批准方法變更時，保留原單方法入口既有語義：revise(2)撤銷方法及下游批准，回S2_REVIEW提出新待批准方案；同方法在S3_PLAN重提會明確phase拒絕。normal menu入口不改。舊token、revision與已消耗message ID不能重用，新方法批准只開S3_PLAN，不開執行權。

實際產品差異：session.py的propose_method、approve_method、method以及內部_validate_method_payload；__init__.py與pyproject.toml改候選版號；測試／文件更新。UNCHANGED_CORE_HASHES.json證明engine、dissimilarity、data、selection_evidence、core/Gate、consent及cli逐位元未變。

## 修復前／後測試

| 原始執行紀錄 | 結果 |
|---|---|
| 原run9兼容案例 | ERROR：KeyError('method')，完整21項runner exit1，紀錄保留 |
| 修復前本次run11：原4筆最小重現 | FAIL，KeyError('method')，exit1；沒有fit |
| 修復後run12：相同批准選單→相容方法變更路徑 | PASS，撤銷舊批准、revision+1、S2_REVIEW待新批准，舊token拒絕；新批准只到S3_PLAN，exit0 |
| run13：15項相容性／schema／拒絕／token／持久化／CLI | 全PASS，exit0 |
| run14：9項受影響Session／CLI回歸 | 全PASS，exit0 |

原run9斷言只要求PermissionError，沒有檢查舊介面本來支援的revise(2)行為。因此保留原檔與失敗記錄，修復後用明確較強的狀態／revision／撤銷／新批准／無fit斷言驗證同一路徑，而不是將任意例外當PASS。沒有宣稱原樣的assertRaises測試通過；沒有將KeyError加入允許例外。

run13涵蓋：正常menu格式、正式單方法格式、pending替換、兩格式缺必要欄位、同時有options/method、未知／空／重複選項、缺assessment／四方法row、錯model或EDA hash、錯status型態、未知requested method不撤銷舊scope、拒絕／模糊／未知回覆不批准、消耗token/message拒絕、同方法phase拒絕、stale Session重載、CLI相容修訂落盤。run14只重驗受影響的9個舊案例，沒有重跑四方法研究或無條件全部統計測試；只使用必要新合成fixture。

實際命令argv、cwd、時間、環境覆寫與退出碼在run11～14.json，stdout/stderr原樣保存。隔離Python沿用Pillow12.3.0，科學依賴符合既有宣告；全域環境未改。新的候選匯入與封裝核對命令另見PACKAGE_VERIFICATION.json／實際日誌。之前已通過Plan B PNG／HTML／A/B/C真人、四方法研究與Pillow驗收保留PASS。

## 新矩陣、交付與安裝

RC6_Functional_Coverage_Matrix.csv的60項必要需求均有可追溯PASS；歷史33項及適用性表仍HISTORICAL EVIDENCE LOST，沒有計入PASS或偽造原始case。獨立Gower矩陣保留新fixture身分，不冒稱原研究fixture。

Source、Plugin與Delivery依本候選重新封裝；Source所有檔案與Plugin skills目錄逐檔比較，Delivery內嵌副本逐位元比較。版本canonical為1.0.0rc6.post1；Plugin manifest採SemVer 1.0.0-rc.6.post.1，兩者對應同一RC6-COMPAT-01候選，以實際內容hash為準。正式personal Skill的runtime與候選source逐檔核對且實際從該安裝路徑匯入；文件更新另列，不將其與未變solver混為一談。

Plugin仍是可封裝候選，host安裝／啟用NOT RUN，非personal Skill發布條件。Source不包含快取、使用者研究資料、全域Python或Git資料；既有原ZIP與已批准研究不覆寫。

## 發布決策

RC6-COMPAT-01已通過修復驗證，沒有目前已知的必要功能失敗。**仍維持NOT ACCEPTED**，最後待決項是使用者正式批准HISTORICAL_WAIVER_FOR_APPROVAL.md：只豁免無法恢復的歷史追溯原件，採用新逐需求基準，不豁免必要功能。

本輪授權修復不被解讀為歷史豁免批准。所有文件與候選在批准前均保持NOT ACCEPTED；歷史inline FAIL與原生按鈕未完成保持，不再嘗試；原GMM功能記正式移除，不標PASS。


# 歷史證據豁免與替代驗收 — 待使用者正式批准

提案識別：RC6-PLANB-HISTORY-WAIVER-20261115；本次綁定候選1.0.0rc6.post1（RC6-COMPAT-01修復），personal Skill範圍。

請批准：將已清除的原33項測試／assertions、歷史適用性／移植清單及原Stage3 Gower fixture永久記為HISTORICAL EVIDENCE LOST，不計PASS、不重建虛構清單、不再要求搜尋；正式採用本交付的RC6_Functional_Coverage_Matrix.csv逐需求替代驗收基準及其可核實證據。

風險：無法證明與所有早期assertions完全等價，也無法恢復每一個原fixture或逐版本結果；現行需求／fixture未捕捉的歷史回歸風險仍存在。緩解措施是保存候選原碼hash、替代測試原碼／環境／命令／stdout／stderr／退出碼、四方法研究計算證據、獨立手算Gower、Hard Gate與Session/CLI負向及持久化測試、Plan B真人證詞。

豁免不涵蓋任何現行必要功能失敗、不改Hard Gate、不把qa_fixture當真人、不升級獨立Plugin安裝，也不清除inline歷史FAIL及按鈕未完成紀錄。RC6-COMPAT-01現已按相容性與相關回歸通過，不透過豁免放行缺陷。

必要功能矩陣60項目前均有PASS證據；歷史豁免仍為PENDING USER APPROVAL。本輪同意修復與提出豁免不等於批准本豁免。使用者批准前發布狀態NOT ACCEPTED；批准後才可記錄personal Skill Plan B ACCEPTED建議，Plugin仍僅候選包、未經獨立host安裝驗收。

## 2026-11-15 使用者正式批准後的發布確認

使用者以A批准RC6-PLANB-HISTORY-WAIVER-20261115-COMPAT01，採用候選1.0.0rc6.post1的60項必要功能替代矩陣，歷史證據豁免僅限已遺失原件，不豁免功能測試。personal Skill Plan B發布驗收決策正式更新為**ACCEPTED**。批准前Source／Plugin／矩陣／豁免文字hash及對話原回覆均保存在RELEASE_ACCEPTANCE.json。批准後只同步文件狀態與回條，不修改runtime、研究結果或重跑測試。較早NOT ACCEPTED／pending段落保留為當時歷史紀錄，不代表現在狀態。原33項與清單、舊Gower fixture始終HISTORICAL EVIDENCE LOST，不算PASS；聊天inline歷史FAIL與按鈕未完成保留。Plugin host安裝NOT RUN／NOT VERIFIED，非personal Skill發布範圍。
