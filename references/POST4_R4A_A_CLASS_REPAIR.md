# post4.dev4／A 類修復驗收報告

**範圍：P4-02、07、08、14、16、18。完整 post4 仍為 NOT READY。**

本版從 `Clustering_post4_Chat_Repair_R3_DEVELOPMENT.zip` 獨立複製後開發；不覆寫 R3、post3 或現有安裝。

| ID | 本地狀態 | 實作 | 證據與界線 |
|---|---|---|---|
| P4-02 | PASS_LOCAL_SCOPED | 完整研究完成後可唯讀比較兩份獨立核准的替代前處理模型；計算配對 ARI、Silhouette、群大小、特徵更動 | 兩次真正 QA 隔離批准／報告流程整合 PASS。**沒有使用者核准的第二研究時，不可宣稱已完成其真實資料敏感度。** |
| P4-07 | PASS_LOCAL | 提示 Silhouette 上/下界、DBSCAN 不同有效分母、小群與指標衝突 | 假設案例及五階段報告測試 PASS；5% 只作提示非淘汰門檻 |
| P4-08 | PASS_LOCAL_SCOPED | 實際替代前處理對照，不僅描述原始全距；拒絕不同原始資料、未批准、無對齊列資料 | QA 的另兩份正式核准研究有實際模型差異；不在既有研究中偷改資料/重擬合 |
| P4-14 | PASS_LOCAL_SCOPED | 有界單變量峰數/樣本 n/方法成本生成探索上限，並保留已授權的 K/eps 增量提案；上界不是最佳 K | 結構線索及 Stage 3/4 gate 回歸 PASS；**此規劃是弱 EDA 線索，不能冒充可靠自然群數估計** |
| P4-16 | PASS_LOCAL | 同 K 的已批准不同 Linkage、Euclidean vs Manhattan／Average 進行實際擬合、報告對照；正確解釋最終選中方法；圖表避免混合異距離高度 | 真 Stage 1～5 QA 候選實際產出 linkage / distance 比較 PASS；Gower 無法直接用 Ward |
| P4-18 | PASS_LOCAL | Stage 3 payload 事前綁定指標說明，Stage 4 使用範圍機器稽核；歷史 payload 明示 legacy 警示 | 額外引入未事前宣告的指標會因 PermissionError 擋下；報告有稽核記錄 |

## 測試證據

- 核心相容性／授權：43/43 PASS（`regression_core.log`）。
- 舊報告與新 A 類快速測試：19/19 PASS（`regression_fast.log`）。
- R2 跨階段、增量與中斷恢復：4/4 PASS（`regression_r2.log`）。
- A 類方法比較 E2E 和 R3 五階段嚴格重現：2/2 PASS（`regression_final_e2e.log`）。
- 兩個獨立經 QA 批准的替代前處理研究之對照：1/1 PASS（`regression_pair.log`）。
- **合計 69 項獨立測試分批 PASS，並非一次完整執行 PASS。** 一次合併測試曾因執行時間限制中止，不能計為成功。

## 尚未證實／必須區分

- 替代研究仍需使用者為每個方案正式授權；不能在單一研究 session 中直接無授權重擬合。
- 弱 EDA hint 不支援自動宣稱最佳 K，隱含需要 Stage 4/重新授權的循環。
- R4A 尚未完成 B 類全面重跑（四方法、Quarto 已安裝路徑、交付檢查）。
- Work Host 原生安裝、實際對話的自動銜接與 Token 遮蔽仍 `HOST_ACCEPTANCE_NOT_RUN`。
- 使用者指定不修的最終狀態檔差異沒有更動。

**發布決策：NOT READY；此 ZIP 為獨立開發測試候選，不能以 post4 正式完成版發布。**
