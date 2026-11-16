# Clustering Analysis Skill — v1.0.0rc6.post3 (R2)

**狀態：發布前審查候選（尚未發布 GitHub Release；正式 Plugin host 安裝／啟用未驗證）。**

本版本支援五階段無監督分群研究及六道 Hard Gate，方法為 K-means、Hierarchical、DBSCAN、PAM/Gower。每階段應在取得批准前提供所需 **PNG 附件**與清楚的 **A／B／C 或編號決策**；聊天內嵌圖片與原生按鈕不是必要條件。

post3 的兩項修復：
- **RC6-REPRO-01**：`reproduce.py --verify` 保留完整重新計算物件與逐候選／逐子抽樣差異；嚴格雜湊不同仍 **FAIL**。
- **RC6-TIMEOUT-01**：Stage 4 穩定性診斷每候選共用受監督子程序，減少重複啟動成本；保留原核准單次擬合時限、逾時終止與不重試政策。執行耗時另寫入 JSONL，不污染科學結果的雜湊。

## 使用 ChatGPT

上傳本 Plugin ZIP 和需要分析的 CSV，然後貼上以下通用提示詞：

> 請先閱讀我上傳的 Clustering Analysis Skill 的 `SKILL.md` 與必要參考文件，使用它分析本次資料。請嚴格遵循 Stage 1～5 及 Hard Gate；每個需決策的階段都要先提供統計解釋、實際可下載的 PNG 圖表與清楚的 A／B／C 或編號選項，等待我明確批准後才繼續。請先完成 Stage 1 的資料診斷與前處理提案，然後停止等待我的決策，不得提前擬合模型。若工具、附件或驗證失敗，請據實回報，不得假裝成功或跳過檢查。

Skill 規格與操作契約分別見 `SKILL.md`、`references/RC6_WORKFLOW.md` 及 `references/OPERATOR_GUIDE.md`。如宿主不能執行程式或存取附件，需明確告知，不能只根據本 ZIP 聲稱已完成分析。

## 驗收與限制

- **工程測試**：post3 R2 的 51 項專項回歸通過；不等同 post1 歷史 60 項功能矩陣在 post3 全數重新驗證。
- **312 筆缺失值研究（獨立實測）**：9 組 Hierarchical 候選 × 20 次子抽樣，Stage 4 為 **180/180 SUCCESS、0 TIMEOUT**；Stage 5 重新驗證 **9/9 PASS、0 差異**，研究交付 117 個檔案雜湊符合紀錄。該驗收的原始證據保存在獨立 `RC6_TIMEOUT01_Post3R2_Confirmed_COMPLETE_Evidence.zip`，**不內嵌於本 Plugin ZIP**。
- **尚未驗證**：正式 Plugin host 安裝／來源綁定、所有支援環境的效能、post3 全 60 項歷史功能矩陣重跑；尚未實作中斷後斷點續跑。不能以本地測試代替正式安裝驗收。
- **歷史保留**：post1 個人 Skill 的 ACCEPTED、既有 post2 Pre-release、post2 研究原先 11 次逾時及 Stage 5 FAIL 均保持原紀錄；不回寫、不偽稱已修正舊研究。

發布前證據與限制詳見 `references/POST3_R2_RELEASE_READINESS.md`、`references/RC6_REPRO01_REVIEW.md`、`references/RC6_TIMEOUT01_REVIEW.md`。**尚未授權修改 GitHub 主線；GitHub 上既有經人工整理的 README 不應以此包整份覆蓋。**
