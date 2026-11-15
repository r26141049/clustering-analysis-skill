# RC6-COMPAT-01 最小修復與候選核對

候選：1.0.0rc6.post1；正式範圍：personal Skill；發布狀態：**NOT ACCEPTED — 歷史豁免待使用者正式批准**。本次只修method payload相容／驗證與候選版本，未改四方法solver、統計結果、Hard Gate、consent recognizer或CLI schema。

## 根因與合法schema

正常propose_method_choices()產生{options, assessment, model_hash, eda_hash}，批准回覆選擇保存在gate.approvals.method.decision.response；method()從綁定選單與已消耗的批准回覆解析選中方法。相容propose_method(method: str)只接受四個canonical方法名稱，產生{method, assessment, model_hash}，批准仍須獨立respond。兩者是已存在的格式，不是任意dict。

舊propose_method在已有批准時直接讀old['method']，遇合法options payload會KeyError。修復改為透過既有已批准decision解析方法，不補寫或重算舊payload／token。新增內部schema驗證：兩種欄位集合互斥且完整、assessment包含四個受支援方法各一次與合法status、options非空且不重複並屬可用方法、model/EDA綁定相符。缺少／錯型／未知值清楚ValueError；非批准或無scope仍由原Gate拒絕，不把任何內容當批准。

requested method先做白名單驗證，未知方法不得先撤銷合法scope。已批准方法變更時，保留原單方法入口既有語義：revise(2)撤銷方法及下游批准，回S2_REVIEW提出新待批准方案；同方法在S3_PLAN重提會明確phase拒絕。normal menu入口不改。舊token、revision與已消耗message ID不能重用，新方法批准只開S3_PLAN，不開執行權。

實際產品差異：session.py的propose_method、approve_method、method以及內部_validate_method_payload；__init__.py與pyproject.toml改候選版號；測試／文件更新。UNCHANGED_CORE_HASHES.json證明engine、dissimilarity、data、selection_evidence、core/Gate、consent及cli逐位元未變。

## 修復前／後測試

| 原始執行紀錄 | 結果 |
|---|---|
| 原run9兼容案例 | ERROR：KeyError('method')，完整21項runner exit1，紀錄保留 |
| 修復前本次run11：原4筆最小重現 | FAIL，KeyError('method')，exit1；沒有fit |
| 修復後run12：相同批准選單→相容方法變更路徑 | PASS，撤銷舊批准、revision+1、S2_REVIEW待新批准，舊token拒絕；新批准只到S3_PLAN，exit0 |
| run13：15項相容性／schema／拒絕／token／持久化／CLI | 全PASS，exit0 |
| run14：9項受影響Session／CLI回歸 | 全PASS，exit0 |

原run9斷言只要求PermissionError，沒有檢查舊介面本來支援的revise(2)行為。因此保留原檔與失敗記錄，修復後用明確較強的狀態／revision／撤銷／新批准／無fit斷言驗證同一路徑，而不是將任意例外當PASS。沒有宣稱原樣的assertRaises測試通過；沒有將KeyError加入允許例外。

run13涵蓋：正常menu格式、正式單方法格式、pending替換、兩格式缺必要欄位、同時有options/method、未知／空／重複選項、缺assessment／四方法row、錯model或EDA hash、錯status型態、未知requested method不撤銷舊scope、拒絕／模糊／未知回覆不批准、消耗token/message拒絕、同方法phase拒絕、stale Session重載、CLI相容修訂落盤。run14只重驗受影響的9個舊案例，沒有重跑四方法研究或無條件全部統計測試；只使用必要新合成fixture。

實際命令argv、cwd、時間、環境覆寫與退出碼在run11～14.json，stdout/stderr原樣保存。隔離Python沿用Pillow12.3.0，科學依賴符合既有宣告；全域環境未改。新的候選匯入與封裝核對命令另見PACKAGE_VERIFICATION.json／實際日誌。之前已通過Plan B PNG／HTML／A/B/C真人、四方法研究與Pillow驗收保留PASS。

## 新矩陣、交付與安裝

RC6_Functional_Coverage_Matrix.csv的60項必要需求均有可追溯PASS；歷史33項及適用性表仍HISTORICAL EVIDENCE LOST，沒有計入PASS或偽造原始case。獨立Gower矩陣保留新fixture身分，不冒稱原研究fixture。

Source、Plugin與Delivery依本候選重新封裝；Source所有檔案與Plugin skills目錄逐檔比較，Delivery內嵌副本逐位元比較。版本canonical為1.0.0rc6.post1；Plugin manifest採SemVer 1.0.0-rc.6.post.1，兩者對應同一RC6-COMPAT-01候選，以實際內容hash為準。正式personal Skill的runtime與候選source逐檔核對且實際從該安裝路徑匯入；文件更新另列，不將其與未變solver混為一談。

Plugin仍是可封裝候選，host安裝／啟用NOT RUN，非personal Skill發布條件。Source不包含快取、使用者研究資料、全域Python或Git資料；既有原ZIP與已批准研究不覆寫。

## 發布決策

RC6-COMPAT-01已通過修復驗證，沒有目前已知的必要功能失敗。**仍維持NOT ACCEPTED**，最後待決項是使用者正式批准HISTORICAL_WAIVER_FOR_APPROVAL.md：只豁免無法恢復的歷史追溯原件，採用新逐需求基準，不豁免必要功能。

本輪授權修復不被解讀為歷史豁免批准。所有文件與候選在批准前均保持NOT ACCEPTED；歷史inline FAIL與原生按鈕未完成保持，不再嘗試；原GMM功能記正式移除，不標PASS。

## 2026-11-15 使用者正式批准後的發布確認

使用者以A批准RC6-PLANB-HISTORY-WAIVER-20261115-COMPAT01，採用候選1.0.0rc6.post1的60項必要功能替代矩陣，歷史證據豁免僅限已遺失原件，不豁免功能測試。personal Skill Plan B發布驗收決策正式更新為**ACCEPTED**。批准前Source／Plugin／矩陣／豁免文字hash及對話原回覆均保存在RELEASE_ACCEPTANCE.json。批准後只同步文件狀態與回條，不修改runtime、研究結果或重跑測試。較早NOT ACCEPTED／pending段落保留為當時歷史紀錄，不代表現在狀態。原33項與清單、舊Gower fixture始終HISTORICAL EVIDENCE LOST，不算PASS；聊天inline歷史FAIL與按鈕未完成保留。Plugin host安裝NOT RUN／NOT VERIFIED，非personal Skill發布範圍。
