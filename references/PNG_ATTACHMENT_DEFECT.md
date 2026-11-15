# RC6-PNG-ATTACH-001 — missing stage-local PNG attachment delivery

Priority: P0, independent of advanced inline display failure.
Human finding (2026-11-15): Iris/K-means Stage 1 explanations had no openable/downloadable PNG attachments. Transcript also omits individual PNG attachment links at subsequent stages; final ZIP does not satisfy stage-local delivery.

Cause: figure_previews paths and image-content output were treated as presentation, with attachments only a fallback. No mandatory all-figure attachment-link output existed.

Fix: stage_attachments CLI action validates all current stage PNGs and returns individual sandbox attachment links and separate construction/submission/opening/inline states. SKILL.md and workflow override older fallback-only instructions. Agent must emit all links before the stage decision. No automatic host submission or human-open proof is claimed.

Validation: three presentation-only unit tests PASS (all stages/all files, missing/corrupt PNGs, invalid stage); quick_validate PASS. Existing Iris CLI attachment checks: stages 1/2/3/4/5 produce 3/2/1/4/9 valid individual links. Session and report scientific CSV/JSON/manifest hashes unchanged. No fits or model diagnostics run. Historical stage-local delivery remains FAIL; repaired attachment opening is pending human acceptance. Advanced inline remains FAIL per user; no inline retries performed. No formal release acceptance inferred.


## 2026-11-15 本輪 Stage 1 真人回歸結果

RC6-PNG-ATTACH-001 的 Stage 1 準時附件交付／真人開啟子項：PASS。使用者在新資料正常流程確認 eda_numeric.png、eda_geometry.png、eda_categories.png 全部在前處理批准前主動提供，均可開啟查看真實圖表，無需補交，且交付期間未擅自擬合候選模型。

缺陷整體狀態：PARTIALLY VERIFIED；Stage 2～5 本輪逐檔真人開啟仍 NOT VERIFIED，不能將整個跨階段缺陷標為完全驗收關閉。先前 Iris 準時交付 FAIL 及直接內嵌 historical FAIL 保留。按鈕 UNFINISHED，Plan B 使用 A／B／C。此次為紀錄更新，沒有新 Hotfix 或模型／演算法／Hard Gate 變更。詳細發布界線見 PLAN_B_ACCEPTANCE.md。

## 2026-11-15 最終回歸更新

依使用者本輪最終證詞，Stage 1～4 PNG 準時交付與真人開啟在階段層級均為 PASS；Stage 5 離線 HTML 真人閱讀（含 K=3 圖）PASS。先前本輪 Stage 2～4 NOT VERIFIED 的狀態由此更新。跨階段缺陷保留部分驗收狀態：Stage 5 PNG 附件逐檔開啟未由 HTML 成功自動補為 PASS。歷史 FAIL 保留；未新增 Hotfix，未更動演算法／門控。整體發布界線見 RELEASE_READINESS_REVIEW.md。

## 2026-11-15 最終圖片交付驗收：PASS

使用者本輪再次明確確認 Stage 5 final_partition.png 已成功開啟，正確呈現 K-means、K=3 三群。結合先前 Stage 1～4 在決策前準時交付與真人開啟、Stage 5 離線 HTML 真人閱讀，依使用者明確驗收決策，rc6 Plan B 圖片交付整體驗收正式記為 PASS。這是產品層級真人驗收，不虛構其餘未指名 PNG 的逐檔開啟回條。

圖片交付不再列為本輪 Plan B 發布阻擋項目；先前 NOT VERIFIED 與部分驗收判定保留為歷史，當前結論以本段為準。直接內嵌聊天 historical FAIL、原生按鈕 UNFINISHED 原樣保留，二者非 Plan B 必要功能。Hard Gate 不變。

剩餘發布建議仍 NOT ACCEPTED，僅限四方法／門控回歸、三包及正式 Plugin 版本一致性、其餘必要研究驗收的證據缺口；詳見 RELEASE_READINESS_REVIEW.md 最新補充。

## 2026-11-15 實際三包與研究附件核對更新

已取得並解壓本輪Source、Plugin、Delivery及五份歷史研究ZIP。舊「三包未取得」判定已由新證據取代：41個共同檔案與Delivery內嵌兩包雜湊一致PASS。19項不fit門控／設定測試及3項原附件測試PASS，六份儲存分群指標／目標值重算PASS；未重新擬合。rc5與rc6研究版本和程式差異分別保留，沒有冒稱相同版本完整回歸。圖片真人PASS保留。正式Plugin載入與build綁定未驗證；完整Session/CLI與四方法邊界回歸仍缺；目前Pillow13.0.0超出宣告<13，另需符合相依範圍的安裝證據。Iris rc6／rc5及PAM提供包仍待最後交付確認，不能據此宣稱六gate獨立流程PASS。最終建議NOT ACCEPTED。完整原始要求／既有證據／缺口／必要性及可追溯命令見FINAL_PACKAGE_REVIEW.md與本對話Release Readiness Review證據包。

## 2026-11-15 使用者正式批准後的發布確認

使用者以A批准RC6-PLANB-HISTORY-WAIVER-20261115-COMPAT01，採用候選1.0.0rc6.post1的60項必要功能替代矩陣，歷史證據豁免僅限已遺失原件，不豁免功能測試。personal Skill Plan B發布驗收決策正式更新為**ACCEPTED**。批准前Source／Plugin／矩陣／豁免文字hash及對話原回覆均保存在RELEASE_ACCEPTANCE.json。批准後只同步文件狀態與回條，不修改runtime、研究結果或重跑測試。較早NOT ACCEPTED／pending段落保留為當時歷史紀錄，不代表現在狀態。原33項與清單、舊Gower fixture始終HISTORICAL EVIDENCE LOST，不算PASS；聊天inline歷史FAIL與按鈕未完成保留。Plugin host安裝NOT RUN／NOT VERIFIED，非personal Skill發布範圍。
