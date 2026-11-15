# rc6 Plan B 正式發布證據核對

日期：2026-11-15（Asia/Taipei）。建議：**NOT ACCEPTED**。

本次實際解壓並核對使用者提供的 Source、Plugin、Delivery 及研究 ZIP；原檔保持不變。未呼叫模型 fit、未重新執行五階段研究、未改已批准結果或統計核心，未產生 Hotfix 或新版本。下面區分 PASS／FAIL／NOT VERIFIED／NOT RUN；不以報告自稱 PASS 代替原始證據核對。

## 1. 總表與真正阻擋事項

| 項目 | 狀態 | 判定及發布影響 |
|---|---|---|
| Plan B 真人圖片與 A／B／C 正常流程 | PASS | 使用者確認、PDF流程順序與本輪紀錄互相支持；不再阻擋 |
| Source／Plugin共同內容與Delivery內嵌副本 | PASS | 41個檔案完全一致，內嵌兩ZIP位元組完全相同 |
| 四方法清單、GMM正式功能移除 | PASS | registry與設定分支只有四方法；runtime無GaussianMixture/GMM執行分支；拒絕GMM定向測試通過 |
| 四方法既有研究計算證據 | PASS（版本限定） | 快照／manifest／原始重現事件可核對；非所有rc6邊界回歸 |
| 本次Gate與方法設定定向測試 | PASS | 19項，exit 0；不代表Session/CLI完整失效回歸 |
| 本次附件測試 | PASS | 3項，exit 0；不當成人工顯示證據 |
| 完整四方法與Session/CLI安全回歸 | NOT VERIFIED | 原發布三包沒有完整tests/evidence/history，只含3項附件測試；仍是必要證據缺口 |
| 正式Plugin匯入／啟用 | NOT RUN | 交付原始PACKAGE_VERIFICATION亦記NOT RUN；本次未執行真實host安裝 |
| 正式Plugin已載入build與ZIP內容一致 | NOT VERIFIED | 可讀personal Skill核心一致，但無正式Plugin loader來源與build綁定 |
| 全部已安裝Skill檔案等同候選包 | FAIL | 核心相同，但5個文件已被本對話驗收更新，另增1份審查文件；不能宣稱全包雜湊相同 |
| 目前審查runtime相依範圍 | FAIL | Pillow=13.0.0，而pyproject要求Pillow>=9,<13；核心計算依賴版本在範圍內；不代表既有研究計算錯誤 |
| 原始聊天內嵌 | FAIL（歷史） | 非必要，不阻擋Plan B |
| 原生點選按鈕 | NOT RUN（未完成） | 非必要，不阻擋Plan B；文字流程已通過 |

真正剩餘阻擋為：(A)完整rc6四方法邊界／失敗及Session/CLI門控回歸證據尚未取得；(B)正式Plugin安裝／載入及build內容綁定未驗證；(C)目前可觀察環境不滿足已宣告Pillow範圍，尚無符合依賴的正式安裝驗證。Source／Plugin／Delivery三包本身一致性已解除「未取得」狀態，不再列缺包。文件更新差異已解釋，不當成演算法被改寫；但須區分現行文件與原候選封裝，不能偽稱全包一致。

## 2. 三包與版本逐位元核對

Source根目錄 clustering-analysis-python-native-rc6/ 的41個檔案，與Plugin的 skills/clustering-analysis-python-native-rc6/ 逐一相同，包含SKILL.md、pyproject、requirements、全部runtime、agents與references。Plugin另有.codex-plugin/plugin.json（manifest）；技能README包含在上述41個共同檔案中。Delivery包含兩個原ZIP、原Iris研究ZIP及驗收文件；它不是展開後重寫的另一份核心。

- Source pyproject／__version__：1.0.0rc6。
- Plugin manifest：1.0.0-rc.6，為同一rc6的不同版本字串格式；不是逐字相同的版本字串。沒有將其當成不同演算法版本，也不只靠名稱判內容相同。
- 三包CRC：PASS。Delivery PACKAGE_VERIFICATION宣告的三個子檔雜湊全部核對相符。

| 檔案 | SHA-256 |
|---|---|
| Clustering_rc6_Plan_B_Delivery_Reupload(2).zip | `36d600b3ae0e5c00d2cb2cc2a766c33ddd179433a817fb2c5164ba2661cf36d9` |
| Clustering_rc6_Plan_B_Plugin_Candidate(1).zip | `0a135e7f074411864b128604af7a107a0aaa17c04d58b5328f54327de2c2ccc4` |
| Clustering_rc6_Plan_B_Source(1).zip | `31e93ce23fe0d98597c5462d33893b0505862aadb719574fbe60e2dccd25311f` |

Delivery內嵌Source與單獨Source均為31e93ce23fe0d98597c5462d33893b0505862aadb719574fbe60e2dccd25311f；Plugin均為0a135e7f074411864b128604af7a107a0aaa17c04d58b5328f54327de2c2ccc4。每個源檔雜湊列在evidence_results.json，不省略必要程式的比對證據。

### 可讀安裝副本

已讀取personal Skill實際檔案。相對候選Source，所有clustering_native程式及相依宣告逐位元相同。差異恰為本對話驗收文件更新：SKILL.md、PLAN_B_ACCEPTANCE.md、PNG_ATTACHMENT_DEFECT.md、RC6_WORKFLOW.md、ACCEPTANCE_MATRIX.csv，另增RELEASE_READINESS_REVIEW.md。這是實際檔案比對PASS（核心）及FAIL（全包完全相同），不是正式Plugin host載入證明。

必須補充的安裝證據：實際Plugin loader的安裝／啟用成功紀錄（非只有同名畫面），載入來源／build識別，以及其manifest、SKILL.md、pyproject／requirements、clustering_native必要程式的實際雜湊清單。可直接與本次已列的候選雜湊比對；不要求重做研究。

## 3. 原始測試證據與本次最小測試

三包列出的41個共同檔案中，只有scripts/test_png_attachments.py；沒有完整統計／Hard Gate測試程式、逐案例結果或history檔。Delivery舊狀態明列四方法完整回歸NOT RUN、Plugin啟用NOT RUN，並非已經存在完整PASS結果卻被忽略。未讀取或要求重新製作不存在於這些包內的報告。

本次增加的審查測試只在獨立暫存fixture上檢查Gate與設定，沒有將fixture當成真人批准：拒絕、模糊、偽造APPROVE配負面回覆、缺答、過期（mock時鐘）、跨session、跨stage、message重放、修訂失效、六階段授權與下游撤銷、payload竄改、非空字串非同意；另驗證四方法清單、GMM拒絕、Kmeans Lloyd、Ward/Gower拒絕、Ward合法設定、DBSCAN不接受K、PAM/Gower設定。19/19 PASS。三項原附件測試PASS。

這些是Gate及設定層測試，沒有驗證Session持久化競態、失敗候選預算消耗、報告刷新後失效、整個CLI錯誤路徑等所有整合情境。四種估計器邊界擬合測試本次NOT RUN，遵守禁止擬合限制。若已有外部完整結果，只需補上原檔與其版本／來源雜湊，不應要求重做；若確實沒有，後續才需另行授權最小相關fixture計算，不能在本次擅自執行。

### 實際命令、環境與退出碼

Python 3.12.14；numpy 2.3.5、pandas 2.2.3、scipy 1.17.0、scikit-learn 1.8.0、matplotlib 3.10.8、Pillow 13.0.0。完整命令argv、cwd、環境覆寫、時間與退出碼在actual_commands.json；stdout/stderr為原始日誌。audit_evidence.py的首次探索執行亦保存為後續正式recorded核對，不重建不存在的歷史日誌。

| 實際命令（詳見argv） | 範圍 | 退出碼 |
|---|---|---:|
| python audit_evidence.py | 包／快照／程式雜湊核對 | 0 |
| python test_targeted_no_fit.py | 19項Gate／設定定向測試 | 0 |
| python Source/scripts/test_png_attachments.py | 原3項附件測試 | 0 |
| python verify_stored_statistics.py | 六份報告儲存標籤指標與目標值重算 | 0 |

沒有執行reproduce.py或任何模型fit；既有reproduction事件是原研究紀錄，不冒稱本次執行。

## 4. 四方法研究證據與版本橋接

| 研究 | 版本 | 候選數 | 既有證據核對 | 與rc6候選差異 |
|---|---|---:|---|---|
| DBSCAN_Final_Research_Report(4)(2)／dbscan | 1.0.0rc6 | 8 | PASS：快照與91個manifest雜湊相符；重現結果及complete事件exit=0 | presentation.py、cli.py |
| Iris_Kmeans_Research_Report／kmeans | 1.0.0rc6 | 5 | PASS：快照與86個manifest雜湊相符；重現結果及complete事件exit=0 | presentation.py、cli.py |
| Breast_Cancer_Research_Report／hierarchical | 1.0.0rc5 | 7 | PASS：快照與82個manifest雜湊相符；重現結果及complete事件exit=0 | figures.py、cli.py、session.py、consent.py、__init__.py、report.py、acceptance.py、suitability.py、selection_evidence.py |
| Iris_rc5_Report／kmeans | 1.0.0rc5 | 9 | PASS：快照與86個manifest雜湊相符；重現結果及complete事件exit=0 | figures.py、cli.py、session.py、consent.py、__init__.py、report.py、acceptance.py、suitability.py、selection_evidence.py |
| Restaurant_Tips_PAM_Gower／pam | 1.0.0rc5 | 7 | PASS：快照與77個manifest雜湊相符；重現結果及complete事件exit=0 | figures.py、cli.py、session.py、consent.py、__init__.py、report.py、acceptance.py、suitability.py、selection_evidence.py |
| Elliptical_Final_Report／kmeans | 1.0.0rc6 | 5 | PASS：快照與90個manifest雜湊相符；重現結果及complete事件exit=0 | 無runtime差異 |

所有研究均保留raw_feature_snapshot、model_feature_snapshot、candidate_results、diagnostics及原始輸入雜湊；這是可重現建模特徵快照，並非原CSV（包含被排除ID／標籤）的完整副本。原CSV不在個別研究ZIP，不能還原或驗證被刻意排除資訊，屬來源追溯限制；不是憑此否定特徵快照計算驗收。

四個演算法核心engine.py、data.py、dissimilarity.py、core.py在rc5研究與本次候選間相同，可保留既有計算證據。rc5的session/consent、選群診斷與報告等檔有差異，因此rc5統計計算PASS不能延伸為rc6流程／輸出完整回歸PASS。rc6 Iris與DBSCAN報告的cli/presentation差異是Plan B附件修正前版本差異，也未隱藏。本輪Elliptical附帶核心完全相同，與PDF跨階段流程及真人確認合用。

既有重現結果不是只看PASS字樣：核對四個快照綁定、完整manifest、candidate_verified事件數與最後complete/exit_code=0、reproduce程式及環境。各歷史decision_log有5次user批准，不能據此擅稱六次交付確認皆已保存。DBSCAN與Breast Cancer另有USER_CONFIRMATION_RECORDED回條；Iris rc6、Iris rc5、Restaurant Tips此次提供的manifest仍為AWAITING_USER_DELIVERY_CONFIRMATION，缺少該包對應的最終交付確認回條／更新版。這不否定統計計算PASS，但這三份ZIP不能當作已完成六gate的獨立流程驗收證據；若要宣稱已完成，需其實際回條或更新版，不需重做分析。本輪Elliptical session另保留六個不同回合與COMPLETE狀態。

本次額外對六份報告的已存最終標籤，重算Silhouette（DBSCAN排除noise；PAM用Gower）、適用的CH/DB、K-means WCSS與PAM目標值，均PASS。這排除只信報告文字的問題，但不是重新驗證整個估計器或穩定性演算法。完整數值與有效n在stored_statistics_results.json。

## 5. Plan B 真人確認與PDF

PDF共12頁。逐頁文字擷取可見Stage1～4圖連結在各自A／B／C決策前，Stage3執行與結果確認分開，Stage5包含final_partition與HTML連結；視覺抽查第2及9頁與文字相符。PDF只能證明對話順序／連結存在，不能單獨證明成功開啟；可開啟、K=3圖正確、HTML可讀及文字選項正常的PASS來自使用者本輪明確真人證詞。兩者分別保留。

歷史Iris晚補交FAIL不回寫；聊天直接內嵌FAIL及原生按鈕NOT RUN（未完成）保留，二者不屬Plan B必要發布條件。三包內驗收文件是早期快照，不以其舊NOT RUN否定使用者後續已完成的圖片真人PASS；本審查補充文件是新證據，不重寫原ZIP。

## 6. 必要研究／文獻要求逐項判定

| 原始要求 | 已有證據 | 尚缺證據 | 狀態 | 是否必要發布條件 |
|---|---|---|---|---|
| Kmeans Lloyd及明確初始化、WCSS | 原碼、Iris/楕圓快照及歷史重現、儲存標籤WCSS重算 | 完整邊界／失敗回歸 | PASS（研究計算）；NOT VERIFIED（完整回歸） | 是；不能混同Hartigan-Wong |
| Ward僅歐氏、linkage與切樹保留 | Breast rc5研究及相同engine、拒絕Gower+Ward定向測試 | rc6 Session／診斷整合邊界回歸 | PASS（舊計算與相容性）；NOT VERIFIED（整合） | 是 |
| DBSCAN核心／邊界／noise、silhouette有效集合 | rc6 Two Moons快照與重現，儲存silhouette重算 | 全noise／單群等完整回歸結果 | PASS（研究）；NOT VERIFIED（邊界） | 是 |
| PAM BUILD/SWAP、Gower混合語義 | Restaurant rc5快照、目標值重算、相同核心 | tie、無可比較pair、ordinal/binary/constant/weights等可追溯邊界回歸 | PASS（研究）；NOT VERIFIED（邊界） | 是 |
| 各指標距離相容、不把NA當0 | 現有四方法報告與指標重算 | 無效／失敗情境完整案例結果 | PASS（現有數據）；NOT VERIFIED（完整邊界） | 是 |
| 同ID ARI／max-Jaccard、失敗／null、固定前處理限制 | 歷史diagnostics及重現日誌、報告命名與限制、核心一致 | 含失敗／消失群／ID重排邊界的原測試結果 | PASS（歷史研究）；NOT VERIFIED（完整邊界） | 是 |
| 搜尋來源、邊界、逐候選取捨、無強制贏家 | config/candidate_plan、selection_explanation、報告 | 四方法所有分支研究輸出的完整回歸 | PASS（提供研究）；NOT VERIFIED（未覆蓋分支） | 是；不得新增任意合成評分 |
| 原始尺度profile、有效分母、隱私ID排除、報告一致性 | 所有研究manifest無差異、profile與快照存在 | 不同型態／缺失案例完整回歸 | PASS（提供研究）；NOT VERIFIED（未覆蓋分支） | 是 |
| 文獻核心定位與方法限制 | LITERATURE_AUDIT有Hartigan/Ward/Ester/Kaufman/Gower/Rousseeuw/CH/DB/Hubert定位及V/C限制 | 本次未含其全部原文PDF，不能新增逐頁複核PASS | PASS（既有定位紀錄核對）；NOT VERIFIED（重新原文複核） | 必須有方法依據與誠實限制；規格未要求每次發布重讀全部原文，不另作籠統阻擋 |
| Hennig with-replacement bootstrap完整重現 | 未提供該功能；現行明列不同程序 | 原文完整實作核對未做 | NOT RUN | 否；未宣稱提供時不要求新增 |
| Gap／Hopkins／VAT專門驗證 | 本版未提供結果或通用閾值，保留待研究 | 專門原文／公式核對未做 | NOT RUN | 否；不列本版阻擋 |
| Podani等未提供擴充理論 | 未提供擴充功能 | 擴充文獻驗證未做 | NOT RUN | 否；不新增要求 |
| 不以後選p值／品質／穩定性證明自然群或因果 | 報告及規格明確限制 | 未發現本輪違反 | PASS | 是 |
| Python QMD／MD、PNG/SVG、離線HTML、誠實Quarto狀態 | manifest與真人驗收 | Quarto實際render未執行 | PASS（fallback）；NOT RUN（Quarto） | fallback足夠，不要求安裝Quarto |

沒有以籠統「文獻不完整」單獨否決；剩餘研究缺口均連結至既有四方法規格的未覆蓋邊界／整合測試，不要求發展新演算法。

## 7. 下一步分工與結論

1. 可直接核對：三包CRC／雜湊／版本、四方法與GMM移除、各研究快照與既有重現／manifest、計算核心版本橋接、PDF順序及既有真人證詞——已完成上述核對。
2. 已補最小測試：19項Gate／設定、3項附件、六份已存分群指標／目標值重算，命令環境退出碼均保存。
3. 尚需的最小測試證據：Session／CLI持久化／scope／失效整合負向測試與四方法原規格邊界回歸。若原結果另有保存，只需提供原檔；本次ZIP未含，不要求重製已存在證據。本輪不執行需要fit的部分。
4. 需真人／安裝端證據：正式Plugin匯入啟用與實際載入build／檔案雜湊、依賴版本。Plan B圖片與A／B／C真人確認已足夠，不再要求重驗。
5. 當前環境Pillow不符宣告，應在符合既有相依範圍的正式環境提供安裝與最小附件驗證；本次不改依賴宣告、不安裝、不產生Hotfix。

**仍不建議Plan B ACCEPTED，維持NOT ACCEPTED。** 這是剩餘必要測試／安裝證據與環境合規問題，不是圖片驗收失敗，也不是三包內容不同。既有PASS研究及真人驗收全部保留。
