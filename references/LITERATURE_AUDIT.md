# Clustering Analysis Skill v1.0 — 核心文獻核對紀錄

審查基準：使用者提供的 `論文(2).zip` 中 14 份 PDF；頁碼以 **PDF 由 1 開始的頁序** 為準，括號標示出版品頁碼（如可辨識）。本紀錄指向文獻中可核對的章節／公式，並非宣稱已逐頁完成所有理論與導出驗證。

狀態定義：**V（已核對核心依據）**；**C（條件性支持／需界定範圍）**；**P（尚待進一步文獻或實作核對）**；**D（使用者的產品設計要求，不宣稱有論文支持）**。同一文獻可涵蓋 V 與 C。

| 文獻 PDF | PDF 頁數 | 已定位內容（PDF 頁；出版頁） | 可支持的規則 | 不可擴張為 | 狀態 |
|---|---:|---|---|---|---|
| `hartigan1979.pdf` | 10 | PDF 3（p.101）最接近／次近中心與更新程序；PDF 1 書目 | K-means 演算法與中心更新的具體求解程序 | scikit-learn Lloyd 就是 Hartigan–Wong | V/C |
| `ward1963.pdf` | 10 | PDF 3（p.237）Objective Function 與 error-sum-of-squares | Ward 最小變異／群內平方和觀點 | 任何非歐氏 Gower 都可用 Ward | V/C |
| `KDD96-037.pdf` | 6 | PDF 2–4 `Eps`、`MinPts`、core/border/noise、density-reachability | DBSCAN 密度可達與雜訊概念，參數診斷必要性 | 任意資料都存在清楚的密度群、固定 eps 適用全部資料 | V/C |
| `kaufman1990.pdf` | 354 | PDF 42–43（pp.30–31）序位秩次；PDF 47–48（pp.35–36）Gower 式 (24)–(27)；PDF 115–116（pp.103–104）SWAP | 混合型距離、序位秩次轉換、PAM BUILD/SWAP | 任意整數編碼都可當連續數值；BUILD/SWAP 保證全域最佳 | V/C |
| `gower1971.pdf` | 16 | PDF 4（p.859）式 (1)–(2)，定性／定量／非對稱二元；PDF 5 | 各變數成對可比較時的加權平均相似度；數值型全距調整；非對稱二元雙零不計比較 | 所有二元變數都一定採雙零不計；所有缺失皆應當成 Unknown 類別 | V/C |
| `milligan1987.pdf` | 27 | PDF 4–5（pp.331–332）方法學回顧及分類法 | 以資料與目標選擇方法、重視驗證，而非只看演算法名稱 | 可以根據文獻給四種方法發通用適合性分數 | C |
| `milligan1988.pdf` | 24 | PDF 3（p.183）等權並非無條件必要；PDF 22（p.202）標準化實驗結論 | 變數尺度與標準化選擇會影響群組恢復能力 | 所有方法、所有情境都應先 Z-score，或研究中的 range 方法必然通用最好 | V/C |
| `rousseeuw1987.pdf` | 13 | PDF 3（p.55）人工分群與真結構的分別；PDF 4–5 silhouette 定義 | Silhouette 比較個體的群內／近鄰群差異 | 高 silhouette 就證明真有自然群組 | V/C |
| `calinski1974.pdf` | 28 | PDF 11 論述群數與群內／群間平方和 | CH 型群間／群內變異數比 | 非歐氏 Gower 的一般相似度矩陣可直接套用 sklearn CH | V/C |
| `davies1979.pdf` | 4 | PDF 1–3 群內散布／群間分離相對指標 | DB 分數的群內、群間分離概念 | 對任意非歐氏成對差異度都可用 sklearn DB | V/C |
| `tibshirani2001.pdf` | 13 | PDF 1（p.411）題名、摘要及 Gap 概念；PDF 2 涉及參考分布的進一步定義 | Gap 將觀察到的群內變異與參考分布比較 | 未定義混合型參考分布即可把 Gap 直接套用 Gower | **C/P**（此 PDF 文字擷取編碼異常，公式須以視覺稿復核） |
| `hennig2007.pdf` | 14 | PDF 4（p.261）Jaccard 公式及 bootstrap、max Jaccard 配對、原群消失概念 | 個別群組的 bootstrap 穩定性與 Jaccard matching | 直接把 80% 不放回 subsampling Jaccard 宣稱完整重現 Hennig 原論文方法 | **V/C** |
| `hubert1985.pdf` | 26 | PDF 8–9（約 p.200–201）相較於機會校正的 Rand 比較 | ARI 的 chance adjustment 背景 | 不同觀測集合或重複 IDs 的分割標籤可直接比較 | V/C |

## 核對後必須修正／保留的規則

1. **二元變數分型**：Gower 與 Kaufman/Rousseeuw 區分對稱及非對稱二元；不能默默把所有 0/1 都當名目，亦不能將所有 0/0 排除。須依有無「共同缺席不構成相似」的語義明確決定，不能從兩個數值的外觀推斷。
2. **有序型變數**：Kaufman & Rousseeuw 的處理使用秩次後以全距調整。先前 Dry Run 以已知五個等級 `1..5` 映到 `0,.25,.5,.75,1`，是**明確定義的建模約定**；須在正式實作標記為採預先聲明的完整等級，與樣本中出現的不同等級秩次不是完全相同的選擇。不得把此約定寫成心理尺度等距的證明。
3. **樣本中沒有可比較的變數**：Gower 應回傳未定義／拒絕距離型演算法，不可把 0/0 當距離 0；常數數值列需事先訂明略過或其他政策。
4. **穩定性方法命名**：`fixed full-data preprocessing + subsampling ARI`、`refit preprocessing + subsampling ARI`、`common-ID subsampling Jaccard` 與 **Hennig 原文的 with-replacement bootstrap + max-Jaccard** 是不同程序。前者可合法報告，但不得混同原文。正式 Skill 若標為 Hennig 的 bootstrap 需專門驗收重複樣本與群組匹配。
6. **Ward + 距離相容**：Ward 最小變異法與一般 Gower 不得直接混用；若特定其他工具提供了「Ward 類似法」，必須另論證它的最佳化意義而不得混稱傳統 Ward。
7. **無自然群**：Silhouette、穩定性、CH、DB、Gap 都不是任何資料下的自然群組存在性證明；允許 `no supported final K`。
8. **Hopkins／VAT**：目前不在這 14 份核心 PDF 的完整、專門核對範圍；不能聲稱其閾值／解讀規則已驗證。

## 文獻來源與產品要求嚴格區分

以下皆屬 **D：使用者明確的產品設計規則**，不是從以上論文推導出的統計定理：五階段 Hard Gate、先確認再建模、同一次分析只選一種方法、圖內英文／解釋繁體中文、預設約兩張整合圖、完整變數型態與角色表、不能無同意修改資料、必須交付純 Python QMD／Markdown、不能冒充 Quarto CLI 已渲染。

## 尚未完成的文獻驗證

- **Tibshirani et al.（2001）**：需要逐頁視覺核對 Gap 公式、參考分布模擬、選 K 規則及應用條件，因原 PDF 的文字擷取無法可靠搜尋。
- **Hennig（2007）**：已核對公式與主要演算法，但尚須將完整 bootstrap 實作及失敗／群組消失計數和原文設定逐條對照。
- **Podani 等序位／混合型擴充、Murtagh & Legendre（2014）、Hopkins、VAT**：尚非目前 14 份 PDF 充分驗證來源，列待補充，不能假裝完成。
- 文獻與 Python 套件 API 的版本差異屬工程文件核對事項；不能冒稱上述 PDF 已證實某版 API 的具體行為。
