# RC6-GATE-BRIDGE-01 — 修復說明與風險限制

- **版本**：1.0.0rc6.post2（獨立候選；NOT ACCEPTED，尚待真人實際安裝驗收）
- **來源案例**：360 筆極端值資料，Stage 1 `S1_REVIEW`；使用者詢問 `B：極端值為甚麼保留？` 後，再回答 `A`，執行端因沒有原生 `message_id` 而無法呼叫舊 `respond`。
- **根因**：既有 CLI `respond` 要求非空 `message_id`；上傳 ZIP 的 ChatGPT 操作入口未取得平台 message ID，執行端錯誤地把「可追溯參照」誤解為只能由平台簽發。既有 Gate 實際記錄本機使用者回覆參照，沒有驗證其平台簽章。
- **修復**：新增 CLI／Session `respond_observed(item,token,response)`，只供操作者已直接觀察本輪新使用者回覆、且沒有宿主可用 ID 時呼叫；產生單次本機收據 UUID，記錄 `AGENT_ASSERTED_NEW_USER_TURN_NOT_PLATFORM_VERIFIED` 與原回覆雜湊，再傳給既有 `respond`／Gate。舊 `respond` 完全保留，沒有擅自將 `message_id` 改為可任意略過。
- **拒絕條件**：無回覆、模糊或拒絕、不符當前 token／提案／階段／session、已消耗／過期 token、修訂失效、QA 混用，不得前進。`B：為甚麼保留？` 在本例為 CLARIFY，不是批准或資料修訂；只有明確要求修改才觸發修訂。候選模型仍不能在 Stage 1 授權後擬合。
- **限制**：本機 UUID 是單次接收事件的參照，不能證明是平台簽署的真人訊息，也不能防止惡意／錯誤代理用新事件重播舊文字。安全倚賴操作者必須確實觀察到新回覆；若無法滿足此條件應拒絕，不能使用此橋接。正式 Plugin 原生點擊驗證仍 NOT RUN。
- **不變項**：統計核心、六個 Gate、原本的 `Gate.approve`、Stage 1–5、PNG／SVG、接受範圍及既有研究資料。原 post1 RELEASE_ACCEPTANCE 僅作為歷史紀錄。

## 新帳號真人驗收步驟

1. 安裝 post2 Plugin Candidate，而不是在對話附上 ZIP；確認實際版本與路徑。
2. 上傳 `01_extreme_outliers_numeric.csv`，執行 Stage 1，確認沒有模型擬合並提供 PNG。
3. 詢問 `B：極端值為甚麼保留？`，應解釋而不消耗原核准；`status` 應仍 `S1_REVIEW`。
4. 新的一則使用者回覆 `A`，執行 `respond_observed` 並檢查 Gate APPROVE、`S2_REVIEW`、原方案雜湊不變。
5. 嘗試原 token 重放、拒絕文字、過期 token、跨 session、真正 B 修改，確認不會提前擬合，並留存成功／失敗 CLI 紀錄。
6. 完成後評估是否批准 post2；不得把本機自動測試當作真人點擊驗收。
