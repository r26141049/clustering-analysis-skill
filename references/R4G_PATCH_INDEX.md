# R4G 修復索引（以 R4F dev9 為基線）

- clustering_native/session_store.py：新增持久化研究目錄、原子發布 Session 快照、依 session_id/資料 hash 查找與安全拒絕。
- clustering_native/cli.py：支援省略 session、自動現在研究、resume_current 唯讀續行、執行紀錄自動保存。
- clustering_native/session.py：跨目錄原始 EDA 圖表路徑驗證與重用。
- clustering_native/report.py：沿用由原始資料產生的實際幾何圖，不因搬移工作目錄而失效。
- SKILL.md、README.md、agents/openai.yaml：跨回合持久化宿主契約及安全界限。
- __init__.py、pyproject.toml：dev10/R4G 版號。
- scripts/test_post4_r4g_session_persistence.py：四項專項驗收。
- references/POST4_R4G_Session_Repair_and_Acceptance_Report.md：本輪測試及限制。

此版保留原有 R4F、R4E 及更早期文檔作歷史紀錄。
