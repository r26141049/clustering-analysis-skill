# post3 R2 — 正式發布前證據與限制（2026-11-16）

**版本：** `v1.0.0rc6.post3`（R2，文件整理修訂）；**狀態：RELEASE REVIEW CANDIDATE，尚未建立新的 GitHub Release。**

## 已核對的證據與範圍

- 原 `post3 R2` Source ZIP 與 Plugin ZIP 的 57 個共同檔案完全一致；額外 `.codex-plugin/plugin.json` 為 Plugin manifest。
- 原 R2 工程回歸 51/51 PASS；本次文件修訂後已以 `PYTHONPATH` 指定解壓來源根目錄重新執行，**51/51 PASS**；另外仍需對最終 Plugin ZIP 抽取副本驗證。
- 2026-11-16 312 筆缺失值正式研究（新研究驗收）：9 候選 × 20 次、80% 子抽樣、seed 17、單次 8 秒、`fixed_full_data_preprocessing`。Stage 4 為 **180/180 SUCCESS、0 TIMEOUT、0 ERROR**，9 個工作程序啟動；Stage 5 重新執行 **180/180 SUCCESS、9/9 候選嚴格重現 PASS、0 逐欄位差異**，`reproduce.py --verify` 結束碼 0。
- 新研究最終交付檔案 117/117 雜湊比對一致。Source 的 `clustering_native/engine.py`、`clustering_native/assets/reproduce.py`、`clustering_native/batch_worker.py` 與研究包內 `reproducibility/` 對應檔案完全一致。
- 驗收證據來源：`RC6_TIMEOUT01_Post3R2_Confirmed_COMPLETE_Evidence.zip`（**獨立提供，不內含於 Source／Plugin ZIP**），其中 `Final_Confirmed_Acceptance/final_acceptance_status.json`、`Stage5_Execution_Acceptance/stage5_independent_verification_audit.json`、`Stage5_RC6_TIMEOUT01_R2_Report/reproduction_result.json` 及逐候選比較。

## 缺口與發布界線

- **正式 Plugin host 安裝／啟用／版本來源綁定：NOT RUN／NOT VERIFIED**，工程 ZIP 解壓和本地 import 不等於 host 安裝。
- **post1 的 60 項功能矩陣不是 post3 重新跑過的 60/60 PASS**；舊版遺失的 33 項原測試史不冒稱 PASS。
- 新版未實作斷點續跑；不得無授權補跑，單次擬合時間與 Hard Gate 不變。
- post2 舊研究當時 11 次逾時與 Stage 5 嚴格驗證 FAIL 保持原歷史狀態。
- 研究交付中的本機 `respond_observed` 收據不等於平台認證互動；不宣稱真實 host 的原生決策 UI 已驗證。
- GitHub main 有經人工整理的 README 等素材，**不可用本來源 ZIP 直接覆蓋整個 main**；正式發布須另行批准，差異審核後才更新、建立 tag 與附件。

## 可發布判定

**工程功能與指定 312 筆研究回歸：PASS。**
**完整正式 Plugin host 安裝驗收：NOT VERIFIED。**
**GitHub 發布：PENDING USER APPROVAL。**

本文件是版本範圍的證據說明，既非新版授權 Gate，也不是替代平台安裝測試或歷史科學快照。
