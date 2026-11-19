---
name: clustering-analysis-post4-r4h41-development
description: R4H.4 actual EDA-anchored neighboring-K candidates and Stage 4 auto-execution of Stage 3 authorized fits and diagnostics; final-selection Hard Gate and legacy sessions retained. Development candidate; host acceptance pending.
---

# Clustering Analysis Skill v1.0.0rc6.post4.dev16（R4H.4.1 報告文字與授權狀態一致性修復開發版）

**開發候選，必要需求尚未全部完成；不可視為正式發布。**

四方法：K-means、K-medoids/Gower、DBSCAN、Hierarchical。不得加入 GMM。保留五階段及獨立研究 Gate，新研究在 Stage 3 核准候選、全資料擬合及重抽樣診斷預算，Stage 4 自動接續兩批已授權工作，保留最終選群 Hard Gate；舊研究仍維持原授權流程。測試使用明確 qa_fixture；不能當作真人批准。

使用本目錄 Python 套件；`python -m clustering_native --request request.json`。公開 CLI 遮罩內部 Token；正常使用者只看 A／B／C，不顯示 Token、期限、nonce 或內部摘要。新且真實觀察到的當前回答使用 respond_current，必須只有一個 pending proposal。禁止重送舊回答、猜測同意或手改 session。

Stage 1 自動 EDA，提供所有 PNG 與前處理差異後等待批准。Stage 1 批准後由公開續行入口立即執行 Stage 2 唯讀評估與方法選單。Stage 2 批准後自動建立 Stage 3 探索提案，不擬合；候選與預算必須批准才執行。取得 Stage 3 執行許可後，Stage 4 自動擬合核准的全資料候選並依同一授權執行 Silhouette／重抽樣 ARI 診斷，等待使用者進行獨立最終選群；舊 Session 保留原結果確認關卡。Stage 5 產報告、等待交付確認；批准後直接呈現 research_report 完整正文與檔案，不增加批准。

所有 Stage 圖表均以 `stage_attachments` 的完整 PNG **純文字連結**在決策前交付，SVG 保留。**禁止在聊天使用 `present_figures` 內嵌圖片、`![alt](...)` 圖像語法、HTML `<img>`、多欄／圖文同列／圖片卡片，亦不得把圖表連結或說明放入表格欄位。** 先用一般段落解釋統計證據，再讓每個真實 PNG 連結獨立佔一行，中間空一行，最後才提出當前 Hard Gate 決策。不得重繪或重擬合以修復展示。單純生成連結不構成使用者已成功開啟的證據。

**R4F 全研究真實圖表硬性規則（P4-ALL-VISUAL-01）：** Stage 1～5，包括聊天回答、研究報告、Markdown／QMD／離線 HTML，**只可展示當次真實觀測、核准模型、已保存標籤或統計計算產出的實際圖**。禁止網路圖像查詢、AsyncImage 示意圖、影像生成、模擬／合成散佈圖、任意圖形替代物，也禁止明知只有檔名卻宣稱圖片已顯示。即使要「輔助說明」也不能額外插入示意圖片；如無實際圖可用，說明限制並只列真正存在且可開啟的 PNG 附件，絕不補圖。輸出前核對 stage_attachments 的真實 PNG 路徑／收據及圖表與核准分析階段一致。Stage 4 真實分群圖在最終選擇之前交付；展示圖表不得觸發新模型擬合或逾越 Hard Gate。

**R4F 指標可讀性規則（P4-18-METRIC-02）：** Stage 3 預先宣告本次實際適用的指標時，必須先用一兩句繁體中文說明「在比較什麼」，再說明數值方向；不可只說「分離較好」「越高越好」。Silhouette 係以同群觀測距離與最近其他群距離檢查群內緊密和群間區隔；重抽樣 ARI 是原分群與重抽樣分群的共同觀測指派一致性，不是利用真實標籤驗證。Stage 4 再用實際結果解讀，維持 Stage 3／4 計算、輸出界線及已批准的指標集合。

在 Stage 2/3 決策前完整呈現 statistical_disclosure，加上實際資料、距離與 linkage 選擇理由。候選範圍須有依據，邊界最佳只能提議帶預算的新探索，不能自行擬合。Stage 4/5 不可增加未揭露的選群標準；Stage 3 payload 必須包含 planned_metric_evidence，Stage 4 機器比對實際使用的指標集合；異常須如實揭露。

研究敏感度比較：禁止在 Stage 4 或 Stage 5 偷偷嘗試新的插補、縮尾、刪除觀測或權重。如果要取得替代前處理的實際重擬合敏感度證據，應對**相同原始 CSV**另開一個獨立研究 Session，依 Stage 1～5 正式批准新前處理、同一方法與候選設定；兩份研究都取得 final 核准後，可呼叫 `compare_approved_studies`（輸入 reference_session、alternative_session、output_dir）生成唯讀配對 ARI、群大小、Silhouette 差及特徵更動報告。若有不同 K/eps 等參數，必須明確註明混雜，不得視為純前處理效果。此比較不計算任何新模型、不改動已完成的報告或批准。沒有兩個已批准研究時，只能提出待核准的敏感度研究計畫，不能宣稱已執行比較。

新研究的 Stage 3 只規劃並批准候選及兩批運算預算；Stage 4 先擬合全資料候選，隨即在 Stage 3 預先批准的診斷預算內自動執行有界重抽樣 ARI 穩定性評估、解釋 Silhouette 並呈現選群圖（包括候選分割、穩定性、品質、最終模型）。既有 R4D 已核准的 Stage 3 ARI 可唯讀重用，不可重複執行。不得在新研究中計算、展示或使用 Jaccard。使用公開 CLI 的 `respond_current` 接收唯一、真實且新送達的 A／B／C（方法選單使用實際選項，例如 4）後，自動執行後續已批准工作與唯讀規劃，停在下一個真正的研究決策。不可直接以 `respond` 代替公開續行入口，除非明確只做底層相容性測試。也可在中斷後使用 `auto_continue`（無新批准）接續不需授權步驟。

Stage 4 的候選上界問題應由使用者先確認擴展範圍與預算，再透過 `propose_candidate_expansion` 建立新 Stage 3 提案；歷史候選只在資料/方法/結果 hash 有效時重用，新的模型絕不可在批准前擬合。若前次已授權的候選 fit 批次已消耗但沒有結果，使用 `recover_interrupted_execution` 只重新建立待批准事項，絕不重送原執行授權。

CLI 公開輸出由 privacy 遮罩。真 Gate token、期限與 nonce 僅保存在內部狀態；使用者端只看研究決策與 A／B／C，不印出完整 token 或期限。Stage 3 預設候選是具預算限制的**探索提案**，不是自然 K 證明；若資料/幾何不足，須停止並解釋原因。Work 原生自動調度、安裝與真人驗收仍待測。詳見隨交付的驗收矩陣與 Release Readiness Report。遇到未實作需求，明確停止或說明，不以歷史 PASS 取代。

嚴格重現使用報告 reproduce.py --verify。失敗保留鑑識紀錄，不能改判成功。離線 HTML 無外部依賴；QMD 預設不再執行擬合。發布、覆寫已安裝版本及公開研究資料另須明確授權。Work 真人安裝及自動調度為 HOST_ACCEPTANCE_NOT_RUN。

歷史文件保存在 references，均不是 post4 驗收。既有數學核心與詳細操作 schema 見 references/OPERATOR_GUIDE.md 與 METHODOLOGY_AND_IMPLEMENTATION_SPEC.md；與此版本公開 UI 契約衝突時，以此文件優先。


## R4H Session 持久化及恢復（P4-SESSION-PERSISTENCE-01）

**適用於所有階段，包括新研究 Stage 4 最終選群及舊 Session 原有的 Stage 3/4 結果確認後續行。** 正常研究不要求使用者自行上傳或編輯 `session.json`。CLI 的 `create` 可不提供 `session`，系統自動在私有的持久化研究根目錄建立新 Session；後續呼叫可不提供 `session`，自動以最近正式選定的研究 Session 接續。宿主可設定 `CLUSTERING_STATE_ROOT` 為**跨回合確實保留的私有資料夾**；未設定時使用使用者私有的本機應用資料目錄（Unix `~/.local/share/clustering-analysis/research-sessions`，Windows `%LOCALAPPDATA%/ClusteringAnalysis/ResearchSessions`）。每次 CLI 調用後保存可驗證的 Session 快照；指定的舊執行目錄已消失時，只有同一研究 ID、原始資料 SHA-256 及原先目錄完全符合的備份才能接續。已寫入的核准 Token、實際回覆及候選結果保持不變；絕不由聊天文字推測批准、建立虛構 Session 或重跑候選擬合。

- 新研究：`{"action":"create","csv":"/absolute/input.csv"}`（原研究仍可顯式指定 `session`）。
- 唯讀查看目前研究：`{"action":"resume_current"}`；回傳階段、已記錄批准及尚待決定的項目，**不執行模型、不消耗批准、不推進階段**。
- 只有在取得**新的、真實觀察到的**使用者選項後才能呼叫 `{"action":"respond_current","response":"A"}`，沿用原 Gate 設計；不得將使用者安裝套件、詢問狀態或這份文檔視為 Stage 4（舊研究 Stage 3）結果確認。
- `session.json` 或備份遺失、研究識別不相符、原始資料雜湊不相符時，必須 fail closed，明確停止。不能把僅有的 Skill 安裝 ZIP 當成有歷史授權的 Session。
- **宿主限制**：套件只能保證**同一持久化磁碟根目錄**中的跨行程／跨回合恢復；若聊天或 Work 的執行環境全部銷毀且未保留此目錄，無法自動復原。此平台情境仍需真人驗收，不能宣稱已修復所有跨容器遷移。

## post4 A 類修復（dev4a 工程規則）

- 初始 K 探索在尚未擬合前，使用已核准資料的有界單變量直方圖線索、n、方法成本及預算；不能假定弱峰數等於真實群數。PAM 大樣本的保守上界須標示是計算限制。邊界或衝突需新 Stage 3 授權才能增加候選。
- Hierarchical 預設候選可一併提出**同 K** 不同 linkage（Gower/Single/Complete/Average 或 Euclidean/Ward/Average/Complete/Single）；數值資料另可提 Euclidean/Manhattan 配 Average 對照。新增候選都算入明確預算，批准前不得擬合。Stage 4 只比較實際批准的相同 K／距離／linkage 條件。
- Stage 3 必須在候選提案內綁定 planned_metric_evidence。Stage 4 使用選群指標前須比對既有宣告，未宣告不得使用為選群證據。
- 若需變更前處理後的實證敏感性，請另開**同一原始 CSV 的獨立研究**，完整批准 Stage 1～5 到 final 決策。研究都完成 final 後，可使用唯讀 `compare_approved_studies` CLI：`{ "action":"compare_approved_studies", "reference_session":"...", "alternative_session":"...", "output_dir":"..." }`。無相同原始輸入、相同方法、原始列順序可對齊或缺少正式批准時，必須拒絕。它產生 `approved_sensitivity.md`、`.json` 和 `feature_changes.csv`，不會重新擬合或編輯兩份研究。
- 本候選版僅表示 A 類已在本機補強；正式 post4 仍需完成 B 類及 Work Host 真人驗收。

## post4 B 類修復／驗收（R4B 本機候選）

- Stage 1～5 QMD/Markdown/HTML 的 Python 程式碼，從交付報告目錄直接執行時會自動載入 `reproducibility/clustering_native`，不要求外部設定 `PYTHONPATH`；須事先安裝 Python 依賴。
- Stage 4 報告程式碼只依已封存重抽樣結果呈現 ARI，本版只輸出 ARI 的穩定性，歷史研究檔仍保持原貌。
- 五個 QA 合成研究案例（K-means、K-medoids/Gower、DBSCAN、Hierarchical/Ward、Hierarchical/Gower/Average）均完成 Stage 1～5、五段程式碼獨立執行、QMD/HTML 一致與嚴格重現。QA 使用 `qa_fixture`，不冒充真人授權。
- Quarto CLI 在本地環境未安裝，原生 Quarto render 為 `NOT RUN`，但離線 HTML 已檢查。PAM 的高成本增量擴展批次在本輪逾時，不記 PASS。
- 研究報告中的程式碼為封存快照的**可執行唯讀重建與實際模組呼叫入口**，不會在閱讀時偷偷擬合。模型嚴格重新擬合與比對由 `reproduce.py --verify` 執行。
- post4 正式發布及 Work 真人驗收仍未完成，不得覆寫現有已安裝版本。

## R4C 九項修正：報告與決策控制

- Stage 1～4 僅輸出各階段診斷、圖表、待批准計畫和 checkpoint；不得自行呼叫完整 report、Quarto 或研究 ZIP 重現交付。Stage 5 才產出正式完整研究報告。
- Stage 3 的 Linkage 比較 K 依初始探索範圍低／中／高位置而非任意固定一點；控制對照不能宣稱比較過各 Linkage 的最佳 K，完整比較須另批授權。
- 只顯示本次方法實際使用或已批准的選群指標；Stage 3 說明判讀方向，Stage 4 報告 Silhouette 與 ARI 的衝突。
- Stage 4 正文先回答測了哪些 K、選哪個 K／方法組合、為什麼，Stage 5 應有逐群描述及群間比較；只列已批准方法及候選。
- QMD／離線 HTML 各階段 Python 程式碼須可收合；Markdown 仍保留原始完整程式碼。

## R4D 真人驗收修正（五項）

- **P4-S2-PRIORITY-01：** Stage 2 的正式比較須使用 `assessment.methods[].recommendation_priority`、`priority_tier`、`recommendation_reason` 與 `recommendation`；顯示四方法推薦優先度、理由及「可執行≠適合形狀」。`propose_method_choices().recommendation_priorities` 可直接做決策介面，但選項數字 1～4 不是排名。允許同級並列，Hard Gate 最終選擇仍由使用者決定。
- **P4-S2-REPORT-RATIONALE-01：** Stage 5 的 Stage 2 章節需基於經核准的 Stage 1 幾何狀態與當時的 Stage 2 評估，說明觀察、所選方法相較其他方法的適合性，以及不確定性。不得將英語 `observations` dictionary、JSON 或內部推理狀態直接印進研究正文。原始證據保留在獨立 JSON；不可借用事後的 Stage 4 勝選結果補寫事前理由。
- **P4-DBSCAN-EPS-01：** Stage 3 在讀取實際 k-neighbor 距離後提出有界 eps 搜尋，涵蓋 P25／P50／P75 及 P90／P95 以防上界過窄；有資料支持時可額外提出一個啟發式轉折值，但不得稱為已證明 knee。顯示所有實際 eps 與來源。Stage 4 使用已批准的群數與雜訊趨勢提出上界審查，不能擅自新增模型擬合；既有 `propose_candidate_expansion`、Hard Gate 與結果重用原則完全保留。
- **P4-README-METRIC-01、P4-README-DBSCAN-01：** README 以白話解釋適用指標、方向、`min_samples` 自身計數、k-neighbor 排除自身、分位數到實際 eps 的轉換及擴展限制。README 可以說明全部受支援指標，但各次研究報告只列實際規劃／使用的指標。
- 本輪修復不得修改既有研究模型、批准或歷史報告；四種方法、Stage 1～5、重現驗證、PNG、QMD／HTML 程式碼收合都必須維持。Work Host／原生 Quarto 轉譯仍需另行驗收。

## R4E 歷史階段界線與圖像要求（僅供舊 Session，R4H.3 新研究以新版規範為準）

- `P4-S3S4-RESULT-BOUNDARY-01`：Stage 3 執行批准後只進行全資料候選擬合，Stage 3 規劃及授權回應不得包含模型執行或 ARI、選群品質排名。候選設定（包含重抽樣率、次數、種子、政策、預算）必須先經 Stage 3 授權。Stage 4 的 `diagnose_approved` 在 `S4_REVIEW` 才執行已授權的重抽樣，保存事件與有效結果；不得新增全資料擬合，出錯後不得復用舊許可自動重試。增量擴展保留舊 Stage 4 穩定性批次，只對新批准候選評估。
- Stage 4 交付 `candidate_partitions.png`（僅實際二維可繪觀測，沒有虛構的 PCA）、`quality_and_sizes.png`、`stability.png` 及方法適用圖。最終候選批准後即交付 `stage4_selected_partition.png`，Stage 5 引用它，不延後才呈現。二維投影不等於整個混合變數空間。
- Stage 5 研究敘述須以已核准 EDA 幾何觀察、實際標籤與數值範圍為依據。不能憑所有二維資料都聲稱彎月或自然兩群；雜訊點不是額外一群。DBSCAN 候選名稱統一 `D1...Dn`，其餘方法 `C1...Cn`，原決策稽核原文維持不變。
- 新研究 Stage 3 不產生模型執行圖；移除固定 K 重複群數的冗餘預覽；候選執行、群組分布、品質與穩定性評估均屬 Stage 4，且全部圖在最終選擇前提供。僅對繪圖與文字進行重組不可變更已核准模型、資料或對照指標。

## R4F 最小修補驗收界線

- `P4-ALL-VISUAL-01`：整份研究及聊天輸出禁止使用與實際研究無關的任何示意圖；Stage 1～5 僅可使用由已完成資料／標籤生成、含可驗證路徑與雜湊的真實 PNG／SVG。圖像不足時提供現有附件，禁止額外搜尋或生成替代圖。
- `P4-18-METRIC-02`：只對本次已批准的指標說明其「衡量對象」及「方向」，維持 Stage 3 預先宣告、Stage 4 才進行品質與重抽樣評估的職責。
- Stage 5 現有 Markdown、QMD、內嵌離線 HTML、五段可收合 Python、研究 ZIP、Strict Reproduce、Hard Gate 與增量結果重用不可退化；舊版 R4E 保留。


## R4H — 新研究變數角色與事後分析（保留 R4G 兼容）

新的 JSON CLI `create` 預設進入 `S1_ROLE_REVIEW`，先顯示來源欄位及暫定角色，並透過 `propose_feature_roles`／`respond_current` 獲得獨立的 Stage 1B Hard Gate。角色必須包含每個來源欄位，選項為 `feature`、`supplementary`、`id`、`exclude`。此步驟不擬合模型，不改變原始 CSV；用戶可先修改建議，禁止視預設為授權。

只有批准角色後才能提出 `propose_preprocessing`，其 `schema[*].role` 必須逐欄符合批准紀錄，並在第二個 Stage 1 前處理 Hard Gate 後進入 Stage 2。既有 R4G Session 及 Python 程式可用 `require_feature_roles=false` 相容入口，不能偽造 role approval。變更已批准角色需回到 Stage 1 重新授權並使下游失效。

`propose_feature_roles` 可另外保存研究問題（`research_question`）及事先指定的關聯變數對（`association_pairs`）。事後分析變數不能參與建模距離、K 規劃或品質指標。Stage 5 使用原資料列位置與既有批准標籤對齊，輸出 `supplementary_values_by_cluster.csv`、事後群間數值／類別比較；只對事前指明的兩變數計算 Spearman，不自動做迴歸或因果聲明。

Stage 1 所有 EDA 軸與標籤必須顯示實際欄名，不得使用 F1/F2。Stage 3 對照真實多變量 EDA 連通間隙（MST，受資料量與尺度限制），與單變量線索及運算預算一起規劃候選 K；該線索不是已擬合模型或最佳群數的證據。Stage 4 不輸出 Medoid 列號散佈圖，改用真實代表觀測特徵及群組大小。

對外名稱固定為 K-medoids（本版以 PAM 演算法求解），內部方法 ID 維持 `pam`，以保存 R4G 資料相容與重現。全程禁止示意圖，Hard Gate 與 Session 持久化不變。


## R4H.2 已執行前處理揭露（R4H-S5-PREPROCESS-DISCLOSURE-01）

- Stage 5 必須依據核准 `preprocessing_plan`、**實際執行的** `fitted_preprocessing` 及對齊的原始／模型快照，描述每一項分群特徵的角色、缺失值處理、實際插補值、類別對照、數值轉換、Z-score／Robust scaling／無標準化、擬合中心與除數、距離權重及處理前後可觀察的數值狀態。
- Z-score 使用 `ddof=0` 母體標準差；Robust scaling 使用 median 與 IQR。擬合中心／除數取自缺失處理和數值轉換**之後**的資料；不可混寫為原始平均數／標準差。
- `analysis.md`、`analysis.qmd`、`analysis_offline.html` 必須包含一致的研究方法說明；`preprocessing_effect_summary.csv` 供逐欄核對。`config.json` 及快照持續保留。
- 禁止補寫未實際執行的標準化、插補、模型、替代比較；擬合紀錄與核准設定不一致時報告應安全停止，不得補造數值。
- R4H.1 單欄純文字 PNG 附件政策、Hard Gate、Session 重建限制及全部演算法保持原樣；真人展示與跨方法全套驗收仍須獨立驗證。

## R4H.1 最小聊天排版修復（R4H-VIS-LAYOUT-01）

真人截圖顯示 Stage 4 有圖片灰框、說明被擠成逐字直排、大面積空白。已驗證研究 ZIP、PNG 解碼與 HTML 引用時，不得因此宣稱聊天端已修復。此版僅對聊天輸出入口做最小改動：

1. 強制 `stage_attachments(stage=N)` 回傳的全部真實 PNG 以**單欄普通 Markdown 文字連結**交付，每個連結單獨一段，不和圖表解釋形成並排容器；禁止聊天室中內嵌圖片與表格放圖。
2. 歷史 `present_figures` 入口轉接到完整的附件清單，保留舊版 `start`／`limit` 參數檢查但不會用它們省略任何必交 PNG；不再向聊天室回傳 Base64 image blocks。`image_batch()` 僅留作模組內部相容 API，並非使用者聊天展示路徑。
3. PNG／SVG 的實際統計圖檔、Stage 1～5 計算、Session、Hard Gate、批准的模型及 Stage 5 Markdown／QMD／離線 HTML／ZIP 一律不變。
4. 測試只能驗證連結文字結構、文件／CLI 路徑和 PNG 可解碼；平台端排版與用戶可下載須後續真人驗收，因此 `R4H-VIS-LAYOUT-01` 維持 `HOST_NOT_RUN`／`OPEN`，不得自動判 PASS。

若 references 內較早的說明提及 inline-first、Markdown 影像、或 functions.image 橋接，**以本 R4H.1 規則優先**；不再重試已知失敗的內嵌路徑。


**R4H.3（dev14）既有規範：** 新 CLI `create` 研究的 Stage 3 只有候選規劃與計算範圍 Hard Gate；已核准候選由 Stage 4 執行 (`S4_EXECUTE`)，停於獨立結果確認 (`S4_RESULTS`)，確認後才執行已預先授權的重抽樣 ARI 與品質比較。固定 K 候選群數長條圖完全不產生。Stage 4 正式選群僅保留 Silhouette、ARI、群組大小及方法適用的 WCSS/Medoid objective/DBSCAN 雜訊等，不計算或展示 Calinski–Harabasz、Davies–Bouldin。舊 R4H.2 Session 以原核准狀態唯讀相容，不把歷史批准自動轉成新流程。GitHub README 及流程圖依發布前待辦延後修改。


**R4H.4（dev15）起的新研究規範（R4H.4.1 保留）：** Stage 3 使用實際觀測的數值特徵空隙及一致性證據，或強烈的 MST 橋接線索，建立初步分離區域數，再優先規劃其鄰近 K；若沒有足夠證據則保留廣範圍探索。這些都是未擬合模型的 EDA，並非已證實的最佳 K。新 CLI `create` 研究將 Stage 3 的候選擬合與 Stage 4 Silhouette／80% 重抽樣 ARI 預算一次綁定授權，Stage 4 `fit_candidates` 完成後自動繼續已批准的 `diagnose_approved`；**不再設置中間結果確認 Hard Gate**，但最終 K 的 `propose_final`／`approve_final` 仍需要獨立使用者批准。新流程以 `stage4_auto_diagnostics=True` 與舊 Session 隔離，舊版授權紀錄不得自動遷移；任一失敗即停止，不得在舊授權下重試。GitHub README 與流程圖仍延後修改。
