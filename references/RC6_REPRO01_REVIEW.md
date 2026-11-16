# RC6-REPRO-01 — post3 診斷修復歷史工程紀錄（初版時 NOT ACCEPTED）

## 證據與問題邊界

2026-11-16 真人 Stage 5 驗收：312 筆缺失值主研究、Hierarchical Ward H02 (K=3) 已獲使用者核准。`reproduce.py --verify` 在候選索引 0（H01，Ward K=2）的穩定性物件雜湊比較報錯；原診斷有 180 次子抽樣，其中 11 次逾時，H01 原紀錄 `repeat=11` 是單次 8 秒逾時。原始候選標籤與若干品質指標先前通過核對。

原 post2 驗證器於重新計算 stability 後，立即以 `digest(rerun) != digest(settings)` 中斷，沒有持久化 `rerun` 或逐欄位差異。因此 **已證實驗證器診斷資訊不足，但尚未證實雜湊不一致一定是逾時所致**。未提供這份 312 筆主研究的完整 Stage 5 驗證資料夾，無法獨立重演該失敗。

## 修復內容（僅診斷與證據保存）

- 修改 `clustering_native/assets/reproduce.py`，每組穩定性重新執行完 **先保存原樣 `candidate_XX_rerun.json`，再進行完整 SHA-256 比對**。
- 每組另存 `candidate_XX_comparison.json`：原始/重現雜湊、失敗數、逾時 repeat、逐 repeat 成功/逾時/失敗狀態與差異類型、最多 500 個逐欄位差異預覽（總差異數仍完整計數）。完整重現物件不截斷。
- 分類：`timeout_status_changed`、`execution_status_changed`、`stability_statistic_changed`（ARI/Jaccard）、`sample_indices_changed`、`repeat_index_changed`、`warnings_changed`、`error_details_changed`、`non_run_metadata_changed`。
- 將原始報告與重現當下的 Python/依賴版本及執行緒環境變數另存 `environment_comparison.json`；版本與環境線索僅供調查，不自動歸因。
- 每次執行分配獨立 `reproduction_audit/<UTC-runid>/`，避免覆蓋先前失敗證據。`reproduction_result.json` 對穩定性不一致標示 `FAIL` 並指向證據；意外錯誤標示 `ERROR`；完全一致才標示 `PASS`。
- `report.py` 新生成的研究報告 README 說明證據位置，版本與 `SKILL.md` 標頭同步修正至 post3。

## 明確不修改

- K-means、Hierarchical、DBSCAN、PAM/Gower 的模型擬合與統計公式。
- Stage 1–5 流程、Hard Gate、核准 token、使用者決策紀錄。
- 原始 `diagnostics.json`、`candidate_results.json`、snapshot 檔及其已存雜湊；檢查到 snapshot 被改動時仍直接拒絕執行。
- 原本完整物件 SHA-256 的嚴格一致性驗收；不自動忽略逾時、不把不一致當 PASS。
- 每次擬合 8 秒預算、重試次數、診斷批次、斷點續跑機制。這些尚屬 **RC6-TIMEOUT-01 待釐清事項**；增加預算或重新擬合必須另外授權。

## 測試結果與限制

- `scripts/test_repro_triage.py`：9/9 PASS，包含真實子程序執行的合成假驗證資料，檢查 FAIL 保留完整 rerun、差異定位、PASS 仍可達成、原始快照不變、篡改快照 Fail Closed。
- 既有 `test_compat01.py` 15/15 PASS、`test_gate_bridge01.py` 17/17 PASS、`test_png_attachments.py` 3/3 PASS；共 **44/44**。完整測試輸出另附在 Review Package。
- **未重跑 post1 原有 60 項必要功能矩陣，也未完成正式安裝或 312 筆真人重現驗證**；不得沿用舊版通過宣稱 post3 已驗收。
- 本候選的目的是讓下一次驗證失敗有足夠證據判定差異，不保證原 312 筆研究重現驗證變成 PASS。

## 312 筆原案的後續驗證

使用新的 post3 重新產生研究交付資料夾／重現腳本，並確保原研究的已核准科學快照不被重寫。對已發表的 post2 報告，不能直接覆寫原 ZIP 或偷偷替換報告中的重現程式；若僅作鑑識性驗證，須保留原始目錄及完整 SHA-256，另在**獨立副本**上使用新重現器並記錄變更來源。執行前依批准的驗證預算及現有授權範圍核對；未授權不得重跑研究擬合。失敗時讀 `reproduction_result.json` 的 `comparison_file` 與 `rerun_file`，重點核對 H01 `repeat=11` 與整體失敗計數。兩次完整科學結果若仍無法一致，狀態維持 FAIL。

## GitHub 發布注意

此 Source ZIP 以 post2 Source 基底建立，**可能不含 GitHub main 上另行更新的繁體中文 README、文獻格式或流程圖**。不得整份覆蓋 main。保留 post2 已發布 Pre-release/tag 與其檔案；post3 僅作獨立修復候選，真人確認前不要更新 README 主要下載連結，也不要標記 ACCEPTED。

## 後續驗收補充（2026-11-16，不改寫上列初版紀錄）

第一候選已於 312 筆真人研究差異鑑識中成功保存每次重現物件及逐欄位比較；原先 11 次逾時在鑑識重現中均成功，因此當時嚴格雜湊仍為 5/9 PASS。此證據建立了修復後的**差異可診斷性**，沒有將舊研究 FAIL 改判 PASS。其後 post3 R2 在獨立新研究 312 筆、9 候選、180 次子抽樣中完成嚴格重現 9/9 PASS；這是新的研究驗收，不是舊研究的追溯更正。詳見 `POST3_R2_RELEASE_READINESS.md`。
