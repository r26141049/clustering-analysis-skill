# Clustering Analysis Skill — post4.dev3／Chat Repair R3

**正式發布判定：NOT READY。** 此包是獨立的開發測試版本，不得覆蓋 post3 或對外發布為正式 post4。

## 與 R2 相比的實際修正

1. **P4-07 / P4-18 — 實際指標衝突：** Stage 4 的候選證據由已批准結果及固定參數重抽樣產生，新增 Silhouette、ARI、群別 Jaccard 平均及最低群別平均對照。當最高 Silhouette 與最高穩定性候選不一致時，明確揭露衝突；不合併加權成新選群分數，也不自行修改最終模型。
2. **P4-13 — Jaccard 跨階段一致性：** Stage 3 預覽與 Stage 4 正式比較共用「先對各原始群彙總有效重抽樣、再等權彙總群組」規則；NA、失敗、雜訊與小群保留原值。Stage 4 不因這項報告更新而新增模型擬合。
3. **P4-02 / P4-08 — 前處理診斷：** Stage 1 報告新增實際數值的 P05/P95 區間相對原始全距、缺失減少量、類別眾數占比變化。此為**不重新擬合的描述性敏感性診斷**；任何替代插補、縮尾、刪除、權重變更仍須另有批准。
4. **P4-14 — 三種其他方法擴展驗收：** 新增 K-means、PAM 的 K 擴展，以及 DBSCAN 的 eps 擴展。每例確認未批准不得擬合、取得新 Stage 3 批准後舊模型及穩定性重用、只跑新增候選、結果確認 Gate 保留。Hierarchical 的 R2 測試保留。
5. **P4-15 — 最終授權資訊保護：** 修正 Stage 5 `delivery_confirmation.json` 曾將原始 Gate token 當作 `approved_manifest_payload_hash` 輸出的問題。R3 改輸出已批准 manifest 內容雜湊，並遮蔽確認事件中的 token/expiry；原始授權仍由內部 session 維護。
6. **報告一致性：** `analysis.md`、`analysis.qmd`、`analysis_offline.html` 都加入上述對照；Stage 1 前處理解釋放回 Stage 1 標題下，Stage 4 指標分析放在 Stage 4。

## 實際測試（所有數字均指實際執行）

- **87 項獨立測試 PASS（分批執行）**：R2 舊測試 78 項、新增 R3 9 項；包含新的三方法增量擴展，以及一個從 Stage 1 執行至 COMPLETE 的 Hierarchical/Gower 小型隔離研究。新增一個本機斷言至既有解釋測試。
- 新版小型 E2E 同時確認 Stage 5 ZIP 的授權資訊遮蔽，以及 `reproduce.py --verify` **實際回傳 0**。
- R2 先前完成的五方法 QA E2E 仍作為歷史證據；**沒有在 R3 全面重跑五個 E2E**，不可將上一版結果冒充 R3 的全部方法重新驗收。
- 曾嘗試將全部測試一次串接，執行到 DBSCAN 測試時超出 120 秒整批期限；之後已改為分批執行，每個個案有成功紀錄。早期 PAM 大型測試也曾超出 150 秒，縮小 QA fixture 後獨立通過。這**不證明**實際較大 PAM 或平台耗時問題已修好。
- 授權來源均為 `qa_fixture`，沒有任何真實使用者批准被偽造或覆蓋。

## 仍待完成（不得假稱 PASS）

- Work 原生安裝、自動銜接、聊天完整報告、附件顯示及 Token 全面遮蔽：`HOST_ACCEPTANCE_NOT_RUN`。
- 安裝 Quarto 時的真實轉譯：`NOT RUN`；無 Quarto 離線 HTML 已測試。
- 不同前處理策略的**經重新授權**敏感度研究、實際 Distance／Linkage 之多方案統計比較、所有選群指標衝突與邊界情境的系統性驗收。
- 本版五種設定完整 E2E 及嚴格重現重驗：只有一個小型 R3 E2E 已完成。
- Work 先前命令卡住的底層原因仍未知；本機有界鎖定與恢復無法取代平台診斷。
- 使用者已決定不修的最終狀態檔差異不列入本輪必修缺陷。

## 發布決策

**NOT READY**。本版可作下一輪本機修復基線，不得直接覆蓋已安裝的技能或發布 GitHub Release。
