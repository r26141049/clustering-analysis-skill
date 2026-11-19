# Clustering Analysis Skill R4G — Session 持久化／續行修復與驗收報告

- 版本：`v1.0.0rc6.post4.dev10`（R4G 開發候選；非正式 post4）
- 修復編號：`P4-SESSION-PERSISTENCE-01`（P0，Stage 3 → Stage 4 阻斷）
- 開發基線：使用者上傳的 R4F Skill ZIP，SHA-256 `d42aeabf7bd14564e87b3f274049a012c2f51875ed8c76db5ac3400ef2b086df`
- 原版 R4F 保留；此版不重擬合任何已核准的真人研究資料，也不建立虛構的真人批准。

## 1. 可重現的根因與修復範圍

原 R4F `Session.create()` 在研究工作目錄寫入 `input.original.csv` 和 `session.json`，但公開 `clustering_native.cli.dispatch()` 規定每次都提供相同 `session` 路徑，沒有目前研究的持久化定位機制。如果宿主在下一回合重新建立工作目錄，原路徑消失，雖然 Stage 1～3 曾有結果，CLI 不能識別其有效 Session；不能安全進入 Stage 4。**單靠上傳原 Skill 安裝 ZIP 並不包含研究授權或 Session 狀態**，因此原本中斷的實例無法由安裝檔本身恢復。

R4G 只修復這個 P0 工作階段銜接問題，不把改寫 Stage 3 圖表、調整 K 選擇、擬合新模型當作修復手段。

## 2. 實際修改

1. 新增 `clustering_native/session_store.py`：自動配置私有持久化根目錄，`CLUSTERING_STATE_ROOT` 可由宿主指定；預設 Unix 使用 `~/.local/share/clustering-analysis/research-sessions`，Windows 使用 `%LOCALAPPDATA%/ClusteringAnalysis/ResearchSessions`。
2. 新研究 `create` 可以省略 `session`，由持久化目錄建立獨立 ID；後續公開 CLI 呼叫亦可以省略 `session`，利用 `index.json` 找到目前正式選定研究，避免使用者自己尋找 `session.json`。
3. 新增唯讀 `resume_current`，只顯示階段、現有批准、待批准項目和已完成候選數，不自動確認結果、不消耗 token、不擬合模型。
4. 每次 CLI 操作後保留原始 CSV、Session、EDA 圖、候選及診斷產物的完整本機快照，使用不可覆蓋的新快照目錄，最後才原子更新索引。對原本在臨時目錄建立的研究，只允許**完全相同的原始目錄別名、同一 session_id 及輸入 SHA-256** 對應回快照；找不到則拒絕。
5. `Session.evidence_path()` 能在不修改原 Gate 授權 payload 的情況下解析原始 EDA 圖表的舊絕對路徑，並再依照已儲存的 SHA-256 驗證內容；Stage 5 報告引用同樣的實際圖表。
6. 如果原工作目錄和存檔後來同時存在且不一致，依 Gate 事件前綴判斷合法較新進度；可證實來源衝突則拒絕恢復，不默默回到舊 Gate。
7. `record_execution` 在使用自動 Session 時仍會產生 CLI 執行紀錄，並同步至最新可用存檔。
8. 本輪不修改 `clustering_native.engine` 的數學演算法、Silhouette／ARI 定義、候選內容、既有六個 Gate 或 Stage 5 ZIP／HTML 的版型。

## 3. 正式操作契約

初次建立研究（只需提供 CSV）：

```json
{"action":"create","csv":"/path/to/research.csv"}
```

任意回合唯讀接續：

```json
{"action":"resume_current"}
```

新且真實收到使用者的批准後，才可以：

```json
{"action":"respond_current","response":"A"}
```

**不要**用 `resume_current` 自動當作 `respond_current`；也不能從聊天歷史文字重建未保存的 Gate。若 Session 本身已遺失，使用者只能重啟合法的研究程序，或讓宿主提供先前真正保存的完整研究目錄。

## 4. 這次實際執行的回歸

| 測試 | 紀錄 |
|---|---|
| R4G 自動 Session 建立、讀取與不同 Python 行程重啟 | PASS |
| R4G 原工作目錄刪除後，在 Stage 3 結果確認 Gate 唯讀恢復 | PASS |
| R4G DBSCAN 的 Stage 3 → Stage 4，有效 QA Gate 才執行穩定性且不重新擬合 | PASS |
| R4G PAM/Gower 混合型資料同一情境的 Stage 3 → Stage 4 | PASS |
| R4G 缺失、篡改及不相符 Session 的安全阻擋；舊工作目錄重新出現後阻止回滾 | PASS |
| R4F 圖表政策及指標說明 | 4/4 PASS |
| RC6 相容性 | 15/15 PASS |
| RC2 Hard Gate 負向測試 | 6/6 PASS |
| Gate bridge 新／舊公開回覆 | 17/17 PASS |
| R4E 授權增量探索重用、K-means Stage 4 專項 | 2/2 PASS |
| R4E DBSCAN 全五階段報告 E2E 的本輪重跑 | TIMEOUT，**未計 PASS** |
| 五種方法完整嚴格重現重新跑過一輪 | NOT RUN（本輪未重新驗證） |
| ChatGPT / Work 宿主持久磁碟、安裝／跨真人回合 | NOT RUN |
| Quarto 原生轉譯 | NOT RUN |

R4G 四個新增測試用例在 `scripts/test_post4_r4g_session_persistence.py`，QA 決策使用獨立 `qa_fixture` 身分；CLI「直接觀察的新回答」測試僅屬本機介面驗證，不作真人 Gate 驗收聲明。

## 5. 尚未解決的宿主限制（不得誇大）

**本機持久化 PASS 不代表全平台跨容器 PASS。** 如果 ChatGPT／Work 在兩次回合之間沒有保留（或沒有把同一個）`CLUSTERING_STATE_ROOT` 掛回新環境，軟體無法取得保存的 Session；只有安裝 ZIP 並不足以還原先前的批准。這是宿主持久磁碟的整合／驗收要求，仍為 NOT RUN。裝回 R4G 也不能憑空救回先前 R4F 那次已遺失的 Session。

本輪其他先前登記的問題仍待後續修復：`P4-S3-EDA-ADAPTIVE-K-01`、`P4-S2-GOWER-SYMBOL-01`、`P4-S1-MATRIX-LABEL-01`。全研究示意圖禁令仍沿用 R4F 政策。

## 6. 驗收結論

`P4-SESSION-PERSISTENCE-01`：**LOCAL PASS / HOST ACCEPTANCE NOT RUN**。R4G 是可供安裝驗證的開發候選，不是正式 post4 發布版。只有當宿主保留同一個私有持久化根目錄時，才可以宣稱已成功跨回合接續。
