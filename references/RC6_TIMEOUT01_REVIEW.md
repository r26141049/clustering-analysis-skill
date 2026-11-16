# RC6-TIMEOUT-01 — post3 R2 工程修復及後續實測驗收（保留初版紀錄）

## 原始證據與已知範圍

- 原始 312 筆研究 Stage 4 共 180 次子抽樣，11 次超過核准的 8 秒單次上限。
- post3 第一候選重現時 11 次均轉為成功；成功對成功的 ARI/Jaccard 無發現差異，抽樣位置 180/180 一致。
- 9 組候選嚴格重現驗證 5 PASS / 4 FAIL；舊結果不可更改為 PASS。
- 原本每次 `bounded_fit()` 都以 `subprocess.run()` 啟動全新 Python，啟動及模組匯入同樣計入 8 秒。
- 原始逾時的當下沒有足夠 CPU 排程及階段耗時記錄，不能斷言唯一成因是冷啟動。

## 最小修復

1. 僅 `stability()` 使用新的 `StabilityFitBatch`，每個候選在單一執行批次中重複使用受監督的 Python 子程序；候選間不共享。
2. 每次子抽樣仍接受相同 `budget_check`、`validate_config`、相同授權 `seconds_per_fit`；首次啟動包含在第一次擬合上限內。
3. 子程序逾時時立刻 `kill` 並 `wait`；失敗的子抽樣仍記錄 `TimeoutError`，**不自動重試、不替補、不改寫結果**；下一次已核准的子抽樣才可重新啟動工作程序。
4. 增加 JSONL 時間稽核，包含候選及 repeat、工作程序是否重複使用、啟動秒數、完整單次耗時、計算秒數、結果寫出秒數、逾時階段與上限。稽核紀錄**與研究診斷 JSON 分離**，避免執行耗時的非決定性影響 SHA-256。
5. `Session.diagnose()` 將稽核寫到工作階段的 `fit_runtime_events.jsonl`，未來新建研究報告會附帶該實際日誌；`reproduce.py --verify` 在 `reproduction_audit/<run-id>/fit_runtime_events.jsonl` 保存重現執行耗時，不修改歷史快照。
6. 正式候選擬合 `bounded_fit()`、四種模型核心、Hard Gate、方法選擇、候選授權、穩定性演算法的公式/抽樣順序/輸出 schema 均保持不變。

## 工程測試

- 舊版 44 項專項測試保留。
- 新增執行器測試，含四方法冷/暖輸出一致、工作程序復用與隔離、逾時強制終止、無自動補跑、稽核與科學診斷隔離。
- 312 筆、3 變數、9 個階層式候選、每候選 20 次的**全新合成資料**壓力測試：180/180 成功、0 逾時、每候選一個工作程序。這不是原 312 筆研究重現驗收，也不能保證所有執行環境皆零逾時。
- 測試結果與 SHA-256 應以相應測試包 `TEST_SUMMARY.json`、`logs/` 為準，勿臆測已通過原 60 項功能全矩陣。

## 保留的缺口

- **未實作斷點續跑。** 中斷診斷批次後，現有一次性批次與授權消耗規則保持不變；不得無授權續跑。
- **沒有調整 8 秒上限。** 預算若需改變，須重新提交 Stage 3 實驗規劃並通過正式 Hard Gate。
- 目前工作程序隔離為每候選的批次生命週期，不承諾對所有外掛執行環境/Windows 裝置完成正式驗收。
- 舊 Stage 5 FAIL 及 11 次歷史逾時不可修改；新候選仍為 NOT ACCEPTED。
- 新版長時間診斷重現是否在正式安裝環境 PASS，仍待新研究的獨立驗收；不得拿合成工程測試代替。

## 後續原始 312 筆案例驗收（2026-11-16）

最初的「尚待正式研究驗收」係上述工程測試當時的狀態，後續已另行完成**獨立研究驗收**：312 筆原始研究資料、9 組 Hierarchical 候選、每候選 20 次、80% 子抽樣、seed=17、單次 8 秒、`fixed_full_data_preprocessing`。Stage 4 **180/180 SUCCESS、0 TIMEOUT、0 ERROR**；Stage 5 `python -u reproduce.py --verify` **exit=0、9/9 PASS、180/180 SUCCESS、0 欄位差異**。正式交付 117 個檔案雜湊亦符合記錄。完整證據在獨立 `RC6_TIMEOUT01_Post3R2_Confirmed_COMPLETE_Evidence.zip`，不隨 Plugin ZIP 內嵌。

**僅判定本次原始資料範圍的回歸驗收 PASS。** 未重驗 post1 60 項全部功能、正式 Plugin host 安裝、所有 OS／硬體與斷點續跑；保留舊 post2 的 11 次逾時與 FAIL，不宣稱所有未來研究零逾時。另詳 `POST3_R2_RELEASE_READINESS.md`。
