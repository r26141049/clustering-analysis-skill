# R4H.2 — 前處理研究報告揭露最小修復

- 版本：`v1.0.0rc6.post4.dev13`；基於 R4H.1 `dev12` 的獨立開發候選。
- 範圍：`R4H-S5-PREPROCESS-DISCLOSURE-01`（P1），以及 R4H.1 發現的內部 `__version__=dev11`／套件 `dev12` 不一致問題。
- 修改：`clustering_native/preprocessing_disclosure.py` 只讀核准的 Stage 1 `preprocessing_plan`、`fitted_preprocessing`、`raw_feature_snapshot`、`model_feature_snapshot`，在 Stage 5 報告新增實際處理敘述及逐欄前後統計對照。新增 `preprocessing_effect_summary.csv`，並在 `analysis.md`、`analysis.qmd`、`analysis_offline.html` 呈現同一份研究說明。
- 讀者可見內容：特徵與樣本數、是否刪除觀測、處理順序、缺失與插補、類別對照、log1p、Z-score（ddof=0）、Robust median/IQR 或未標準化、實際擬合中心與除數、距離權重、處理前後均值與母體標準差；且說明未做替代模型評估。
- 安全約束：缺少擬合紀錄、核准與擬合方案不一致、未對齊觀測時，拒絕生成失真研究說明。不更改模型、擬合資料、分群標籤、Hard Gate、Session 儲存、ARI 或聊天 PNG 附件展示。
- 回歸：`scripts/test_post4_r4h2_preprocessing_disclosure.py`；版本與完整報告核對詳見交付驗收報告。
- 真人聊天排版：`R4H-VIS-LAYOUT-01` 仍為 OPEN／HOST_NOT_RUN。其他已排入後續的 Stage 3／4 整併及 CH／DB 指標精簡不在本版修復範圍。
