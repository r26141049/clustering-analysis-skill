# Clustering Analysis Skill R4H.1 — 最小聊天排版修復／交付驗收

- 基線：`Clustering_post4_R4H_DEVELOPMENT.zip`，原版不覆寫。
- 新版：`v1.0.0rc6.post4.dev12`，獨立 Skill 根目錄 `clustering-analysis-post4-r4h1-development`。
- 範圍：`R4H-VIS-LAYOUT-01`（Stage 4 真人看到圖片灰框、文字直排、大片空白）。**這是人機介面顯示異常；不能憑研究 PNG 正常就斷言平台根因或已修好。**

## 實作

1. 唯一正式對話圖表交付：`stage_attachments(stage=N)`，純文字 Markdown PNG 連結、每圖獨立佔一段；統計文字用獨立自然段落，禁止嵌圖、圖片卡、左右圖文並排及表格內放圖片。必須在各階段決策前交付全部真實 PNG。
2. 舊 `present_figures` CLI 改走完整 `attachment_batch`；保留 `start`／`limit` 合法性檢查，但不按舊頁數漏掉必交圖表。現在不向聊天公開介面返回 base64 圖像區塊。此為**展示 API 的刻意相容性變更**；模組內 `image_batch()` 保留，供舊版 Python 使用者，但不可用於聊天室圖表交付。
3. 清除 `figures.preview_assets()` 中與方案 B 衝突的 inline-first 操作指令；更新 SKILL／交互規範、Agent 指引，將早年 bridge 標明 HISTORY ONLY。
4. 文件與回傳值均明確區分：本機 PNG 驗證／連結建構 PASS，不等於聊天畫面出現或下載成功。
5. 全部統計模型、距離計算、原始研究、Hard Gate、Session 續行、Stage 5 Markdown／QMD／離線 HTML／ZIP 均未修改。

## 本機回歸證據

- `test_post4_r4h1_layout.py`：4/4 PASS（單欄純文字鏈結、無圖片時 fail-closed、預覽指示、舊 CLI 轉接）。
- `test_png_attachments.py`：3/3 PASS。
- `test_post4_r4f.py`：4/4 PASS。
- `test_post4_r4h.py`：5/5 PASS。
- `test_post4_r4g_session_persistence.py`：4/4 PASS，含 Stage 3→4 PAM/Gower 持久化與無重擬合。
- `test_post4_r4e.py`：候選增量擴展及 K-means Stage4 兩項 PASS；完整 DBSCAN Stage4 圖像案例**TIMEOUT／NOT VERIFIED**，不算 PASS。
- **合計 22 項獨立測試 PASS，1 項逾時**（僅上述實際執行之測試）。不代表全方法 E2E 已完成。
- 使用使用者研究的三張現存 Stage4 真實 PNG 執行純展示 smoke test：3 張解碼 PASS、SHA-256 與回傳收據一致、3 條單欄文字連結；**未重繪或重新擬合**。

## 真人驗收條件（待使用者確認）

1. 同一研究 Stage4 的統計文字以正常寬度換行，不再逐字直排或出現大面積占位空白。
2. 各 PNG 以獨立連結出現在當前階段、可逐張開啟／下載；未經真人確認不記 PASS。
3. Stage4 決策前即可讀到品質、穩定性、分群圖表；保存的 Hard Gate、候選品質與標籤均未變。

**狀態：R4H.1 DEVELOPMENT CANDIDATE；`R4H-VIS-LAYOUT-01 = OPEN / HOST_NOT_RUN`；不是正式 ACCEPTED。**
