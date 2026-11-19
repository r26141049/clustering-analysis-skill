# Clustering Analysis Skill — post4 R4F 修復與驗收紀錄

**版本：** `1.0.0rc6.post4.dev9`（R4F Minimal Presentation & Metric Wording Candidate）  
**基線：** R4E `1.0.0rc6.post4.dev8`。獨立封裝、原版不覆寫。  
**狀態：** DEVELOPMENT CANDIDATE；Work 真人驗收與 Quarto 原生 render 未測，不宣稱正式 ACCEPTED。

## 修復範圍

### P4-ALL-VISUAL-01：全研究只使用真實圖像

- `SKILL.md` 與 `agents/openai.yaml` 明文禁止 Stage 1～5、聊天回覆與研究報告中自動插入示意圖、網路參考圖、模擬或生成圖。圖表不需要時不補位。
- `clustering_native.presentation` 對影像批次與附件批次回傳一致的「真實研究圖像來源規則」，並在附件處理指示中禁止找替代圖。`cli.dispatch` 同樣在 Stage 1 初始資料回應、階段附件及圖像預覽輸出此規則。
- `stage_attachments`／`present_figures` 限制檔案路徑在本次研究 Session 或其 Stage 5 研究資料夾中，不接受逃逸路徑／其他研究圖片。Stage 4 既有 hash 及保存標籤檢查保留。
- 離線 HTML 原有只內嵌當次本地有效 PNG、完整 PNG 位元與 Markdown/QMD 一致性驗證繼續保留；無法顯示則交付真實 PNG 附件而非示意素材。
- **範圍界線：** 此修復強化 Skill 的操作規範與附件來源驗證；不同對話平台的模型是否額外插圖仍需要真人查驗，不能以程式單元測試保證第三方 UI 行為。

### P4-18-METRIC-02：指標說明先交代衡量對象

- Stage 3 `planned_metric_evidence`／`statistical_disclosure` 的 Silhouette 解釋明確指出「同群平均距離」相對於「最近其他群平均距離」與高低方向；對 DBSCAN 說明排除雜訊導致不同候選樣本分母不一致。
- ARI 解釋為原本全資料分群和重抽樣重新擬合分群，在共同觀測上的群組指派一致性（校正隨機巧合），不用真實標籤驗證。
- 其他真正規劃使用的指標（例如群大小、WCSS、CH、DB、噪音比例、Linkage／Distance 比較）也補一句衡量目的與判讀限制。README 同步更新。
- **沒有更動** Silhouette／ARI 數學公式、模型擬合、抽樣次數、Hard Gate、Stage 3／4 分工、最終分群結果或 Stage 5 報告的 ZIP／HTML 格式。

## 本機測試結果

| 測試 | 本輪結果 |
|---|---|
| R4F 新增：指標意義、實際圖像來源、離線 HTML 外部圖片拒絕、依方法揭露指標 | 4 PASS |
| R4D 方法推薦與 eps 規劃回歸 | 7 PASS |
| R3 指標與文字說明回歸 | 5 PASS |
| R2 Hard Gate 回歸 | 6 PASS |
| 舊版報告相容 | 2 PASS |
| post3 工作流回歸 | 6 PASS |
| R4E Stage 4 實際重抽樣及真實圖片 | 1 PASS |
| R4E 授權後增量擴展穩定性重用 | 1 PASS |
| R4E K-means Stage 4 起點／重抽樣專項 | 1 PASS |
| R4C DBSCAN 五階段＋逐階段程式碼＋嚴格重現 | 1 PASS |
| R4C PAM/Gower 五階段＋逐階段程式碼＋嚴格重現 | 1 PASS |
| R4C Hierarchical/Gower 五階段＋逐階段程式碼＋嚴格重現 | 1 PASS |
| R4C Hierarchical/Ward 五階段＋逐階段程式碼＋嚴格重現 | 1 PASS |
| R4C K-means 五階段＋逐階段程式碼＋嚴格重現 | 1 PASS（日誌完整顯示 OK；工具呼叫通訊曾逾時，未單獨取得該次 shell 回傳碼） |
| Quarto 原生 render | NOT RUN |
| ChatGPT／Work 真人完整流程及「全程不插示意圖」 | NOT RUN |

**合計：** 38 項測試日誌顯示 PASS；其中 K-means 完整 E2E 的工具回報存在逾時不一致，依原始日誌 `Ran 1 test in 41.385s / OK` 列示，待真人驗收仍不能視為正式發布。

## 交付與保留

- Skill 內含所有原有正式方法、Stage 3／4 實質分工、Strict Reproduce、五個可收合 Python code block 的離線 HTML 產生器、PNG/SVG 與 manifest 驗證。
- 不修改使用者先前核准的 Two Moons Session、R4E 歷史版本或已有研究結果。
- 不再以示意圖填補聊天無法內嵌 PNG 的限制；由真實 Stage `stage_attachments` 提供 PNG。
