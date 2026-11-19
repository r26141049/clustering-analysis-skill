# Clustering Analysis Skill — post4 R4B B 類本機驗收報告

**版本**：`v1.0.0rc6.post4.dev5`，基於 R4A 獨立修正。**正式發布：NOT READY**。本次使用 5 組合成資料、`qa_fixture` 測試授權；不是使用者真人批准，也沒有更動 post3/R4A。

## 一、驗收目標與結果

| 需求 | 判定 | 核對依據 | 尚待確認 |
|---|---|---|---|
| P4-10 四方法完整端到端 | **PASS_LOCAL** | K-means、PAM/Gower、DBSCAN、Hierarchical/Ward、Hierarchical/Gower/Average 共 5/5 Stage 1～5 均到 `COMPLETE` | 真實複雜資料與 Work host 另需驗收 |
| P4-11 嚴格重現與檔案完整性 | **PASS_LOCAL** | 五份 `reproduce.py --verify` 成功；五份報告 manifest 全部可核對；竄改候選結果時正確失敗 | 其他操作系統／套件版本仍需另測 |
| P4-13 Stage 3／4 重用 | **PASS_LOCAL_SCOPED** | R2 4/4 回歸 PASS；本輪 5/5 保存的 Stage 4 Jaccard 與正式選群證據一致；K-means、DBSCAN 增量擴展 PASS | 本輪單獨 PAM 增量擴展測試超時，不能記 PASS；階層不同特殊配置還可擴充測試 |
| P4-17 QMD 程式碼可執行及忠實性 | **PASS_LOCAL_SCOPED** | 五份報告每份 5 個 Python 區塊，總計 25 個都能從報告目錄直接執行；Stage 4 摘要吻合選群證據；QMD 與 Markdown 來源一致 | 程式碼是唯讀封存重建與模組呼叫，完整模型重新擬合仍須 `reproduce.py --verify`；原生 Quarto 未安裝，正式 render NOT RUN |
| P4-19 離線 HTML 備援 | **FALLBACK_PASS／QUARTO_NOT_RUN** | 五份 HTML 章節與程式碼對應 QMD/Markdown，圖片 data URI 內嵌並可解碼，無 Quarto 環境可閱讀 | Quarto CLI 安裝時的 `analysis.html` 路徑未實際跑過 |

## 二、本次發現並修正的缺陷

**B-REPORT-IMPORT-01（已修正，PASS_LOCAL）**：原報告 Python 區塊在設定開發者 `PYTHONPATH` 後可以執行，但讀者解壓 ZIP 在報告目錄執行時可能出現 `ModuleNotFoundError: clustering_native`。現在所有 Stage 的程式碼先確認並載入交付報告內的 `reproducibility/clustering_native`，不需要手動設定 `PYTHONPATH`；仍需要 Python 套件依賴。

**B-JACCARD-AGG-01（已修正，PASS_LOCAL）**：原 Stage 4 報告內的 Python 註解程式碼，可能把所有有效群／重抽樣 Jaccard 直接 pooled average，與正式選群證據採用的「各原始群先求有效重抽樣平均，再對群別等權平均」不一致。新增不等有效重抽樣次數測試（正確結果 0.4，錯誤 pooled mean 約 0.4667），修正後 Stage 4 程式碼與五份報告的正式保存結果一致。**沒有改動分群演算法或已核准模型結果**。

## 三、5 組完整端到端研究

| 方法／配置 | 完成 Stage 1～5 | 嚴格重現 | 各 Stage 程式碼獨立可執行 | PNG／QMD／HTML 一致 |
|---|---|---|---|---|
| K-means | PASS | PASS | 5/5 PASS | PASS（9 PNG） |
| PAM/Gower | PASS | PASS | 5/5 PASS | PASS（8 PNG） |
| DBSCAN | PASS | PASS | 5/5 PASS | PASS（9 PNG） |
| Hierarchical/Ward | PASS | PASS | 5/5 PASS | PASS（10 PNG） |
| Hierarchical/Gower/Average | PASS | PASS | 5/5 PASS | PASS（9 PNG） |

五組案例均採小規模合成資料、每候選 2 次穩定性重抽樣，屬工程驗收，不足以推論實際研究的穩定性或最佳 K。DBSCAN 案例同時包含可形成 2 群及僅形成 1 群的候選，研究選擇的是可分成 2 群的候選。

## 四、測試與未通過限制

- 5/5 完整隔離研究（已批准的六個 Gate 由 `qa_fixture` 模擬，不是使用者授權）。
- 5/5 修正版報告重建：每份 5 個 Python 區塊能從已解壓的報告目錄執行，**無需 `PYTHONPATH`**。
- 5/5 `reproduce.py --verify` 嚴格重現成功。
- 5/5 QMD/Markdown 程式碼一致；5/5 HTML 的 Python 區塊逐段一致；PNG 與 HTML 內嵌資料均檢查。
- 刻意修改 `candidate_results.json` 的 Silhouette 後，`reproduce.py --verify` 以非零 exit code 拒絕，保留失敗紀錄。
- 新增 B 類單元測試 **2/2 PASS**；再驗 R2 工作流重用 **4/4 PASS**、重現負向診斷 **9/9 PASS**、PNG 附件 **3/3 PASS**、基礎選群等單元測試 **16/16 PASS**。這些為分別執行的測試，不能當作單次合併執行的完成證據。
- **本輪耗時的 PAM 增量擴展回歸中止，未取得 PASS**。K-means 與 DBSCAN 同一腳本中的增量測試分別通過；R4A/R3 有歷史 PAM 擴展證據，但不可充作本輪 R4B 該項 PASS。
- **Quarto CLI 未安裝**，實際 `quarto render` 判定 `NOT RUN`。`analysis_offline.html` 仍通過。
- Work 原生安裝、自動銜接、直接顯示完整報告、實際聊天附件與 Token 隱藏：**HOST_ACCEPTANCE_NOT_RUN**。

## 五、發布決策與後續

**NOT READY**。B 類可在一般對話環境驗證的核心路徑已完成，並修正兩項報告程式碼缺陷；尚需 Quarto 原生渲染（可在備有 Quarto 的環境執行）及 Work 真人驗收。此 ZIP 為開發候選，禁止直接覆蓋已安裝 post3 或發布為正式 post4。

另外，QMD 的五段程式碼為可閱讀、可直接執行的封存資料核對與真正模組引用；它們不會在打開報告時再次觸發模型擬合。**完整模型再擬合與同一輸入檢核的嚴格路徑仍是 `reproduce.py --verify`**，這與教授要求的可重現性應明確區分。
