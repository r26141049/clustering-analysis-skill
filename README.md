# Clustering Analysis v1.0.0rc6.post1

Research Workflow & Visualization Fix Edition。**ACCEPTED：personal Skill Plan B，歷史證據豁免已由使用者正式批准**。

只支援 K-means、Hierarchical、DBSCAN、PAM/K-medoids（適用時 Gower）。保留原 Stage 1–5 及六個必要 gate；方法選擇本身即批准進入規劃，沒有額外重複確認，也不授權擬合。統計 solver 不變，無必要降維、無新部署服務。

從 SKILL.md 啟動，當前操作契約為 references/RC6_WORKFLOW.md。完整改動、測試、限制及待驗收項目見 CHANGELOG.md、DEFECT_FIX_REPORT.md、TEST_REPORT.md、NOT_RUN_TESTS.csv、VISUALIZATION_TECHNICAL_NOTE.md、CODE_DIFF_SUMMARY.md、FOUR_METHOD_REGRESSION.md、HUMAN_ACCEPTANCE_CHECKLIST.md。

Plugin ZIP 包含 manifests、skills/.../SKILL.md、agents、完整本機 Python runtime 與 references/assets；封裝與抽取後 import 可自動驗證，正式 ChatGPT 匯入仍須真人驗收。無需部署 MCP/OAuth/Plugin UI。不要將工程驗證或 ZIP 完整性視為已安裝／正式通過。

history 保留原版與既有驗收；evidence 中帶 rc6 的紀錄是本次工程證據，其餘保留內容為歷史。未執行／跳過與真人未驗證均不計入 PASS。

目前發布決策與範圍以references/RELEASE_ACCEPTANCE.json為準。原33項與歷史清單維持HISTORICAL EVIDENCE LOST，沒有改成PASS；獨立Plugin安裝未驗收。
