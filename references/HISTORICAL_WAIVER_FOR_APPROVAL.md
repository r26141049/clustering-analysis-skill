# 歷史證據豁免與替代驗收 — 待使用者正式批准

提案識別：RC6-PLANB-HISTORY-WAIVER-20261115；本次綁定候選1.0.0rc6.post1（RC6-COMPAT-01修復），personal Skill範圍。

請批准：將已清除的原33項測試／assertions、歷史適用性／移植清單及原Stage3 Gower fixture永久記為HISTORICAL EVIDENCE LOST，不計PASS、不重建虛構清單、不再要求搜尋；正式採用本交付的RC6_Functional_Coverage_Matrix.csv逐需求替代驗收基準及其可核實證據。

風險：無法證明與所有早期assertions完全等價，也無法恢復每一個原fixture或逐版本結果；現行需求／fixture未捕捉的歷史回歸風險仍存在。緩解措施是保存候選原碼hash、替代測試原碼／環境／命令／stdout／stderr／退出碼、四方法研究計算證據、獨立手算Gower、Hard Gate與Session/CLI負向及持久化測試、Plan B真人證詞。

豁免不涵蓋任何現行必要功能失敗、不改Hard Gate、不把qa_fixture當真人、不升級獨立Plugin安裝，也不清除inline歷史FAIL及按鈕未完成紀錄。RC6-COMPAT-01現已按相容性與相關回歸通過，不透過豁免放行缺陷。

必要功能矩陣60項目前均有PASS證據；歷史豁免仍為PENDING USER APPROVAL。本輪同意修復與提出豁免不等於批准本豁免。使用者批准前發布狀態NOT ACCEPTED；批准後才可記錄personal Skill Plan B ACCEPTED建議，Plugin仍僅候選包、未經獨立host安裝驗收。
