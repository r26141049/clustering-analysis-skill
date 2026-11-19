"""Predecision disclosures for the *selected* study, not a generic catalog.

All selection metrics MUST be stated before the Stage 3 execution gate.
"""
DISCLOSURE = """## Stage 2 方法概述
K-means：數值資料的群內平方和最小化；K-medoids（採 PAM 演算法）：用實際觀測作代表點、可使用 Gower；DBSCAN：密度連通與雜訊標記；Hierarchical：依距離與 Linkage 逐次合併觀測群。
距離衡量觀測之間的差異，Linkage 是階層式分群中決定群組如何合併的準則。是否適合須根據本次資料與方法決定。
"""

PLANNED_EVIDENCE = {
 'silhouette':'Silhouette（輪廓係數）：比較每筆觀測與同群其他觀測的平均距離（群內凝聚），以及與最近其他群的平均距離（群間區隔）。越高通常表示同群觀測較接近、不同群較容易區分；無法計算時為 NA。DBSCAN 排除雜訊後計算，各候選納入的觀測可能不同。',
 'cluster_sizes':'群組大小：各群包含多少筆觀測，用來檢查過小群、過度碎群與群數失衡；沒有固定越大越好的方向。',
 'resampling_ari':'ARI（調整 Rand 指數）：比較原本全資料分群與重抽樣重新擬合的分群，在共同觀測上的群組指派是否一致，並校正隨機巧合；越接近 1 越穩定，0 約為隨機一致水準，也可能低於 0。本研究不是用真實群組標籤評分。',
 'wcss':'WCSS／Inertia（群內平方和）：觀測到其所屬群中心的平方距離總和；越小代表群內更緊密，但通常隨 K 增加而下降，不能單獨決定 K。',
 'medoid_objective':'K-medoids 代表點不相似度總和：所有觀測到其群組代表點（medoid）的不相似度加總；在相同資料與距離定義下通常越小越好。',
 'noise_fraction':'DBSCAN 雜訊比例：未被指派到任何群組的觀測占全部資料的比例；太高可能代表參數過於嚴格，但沒有通用的越低越好規則。',
 'linkage_comparison':'Linkage 對照：在相同距離及 K 下，比較不同群組合併準則對分群結果的影響；沒有固定哪個 Linkage 一定較好。',
 'distance_comparison':'距離對照：在相同 Linkage 及 K 下，比較不同已批准距離定義造成的分群差異；不能將尺度不同的數值直接當成優劣。',
 'merge_heights':'階層合併高度：階層樹在兩群合併時的距離或代價，供檢查切割結構；意義取決於距離與 Linkage，沒有通用越高越好的方向。',
 'cut_sensitivity':'切割敏感性 ARI：在固定距離及 Linkage 下比較不同切割方案的群組指派一致性；越接近 1 越相似，但不代表較佳的 K。',
 'initialization':'K-means 多起點診斷：比較不同初始化下的模型結果是否一致；變動較小通常表示較不依賴起點，不是另一次選群準則。',
 'boundary_warning':'搜尋界限／小群警告：提醒得分最高候選是否位於 K 或 eps 搜尋邊界，以及是否產生極小群；屬審查訊號，不是額外的選群分數。',
}

def planned_evidence(method, configs):
    """Only indicators that can be used by the approved configurations."""
    names={'silhouette','cluster_sizes','resampling_ari','boundary_warning'}
    if method=='kmeans': names.update({'wcss','initialization'})
    if method=='pam': names.add('medoid_objective')
    if method=='dbscan': names.add('noise_fraction')
    if method=='hierarchical':
        names.add('merge_heights')
        if any(len({c.get('k') for c in configs if (c.get('metric'),c.get('linkage'))==(x.get('metric'),x.get('linkage'))})>1 for x in configs):
            names.add('cut_sensitivity')
        if any(len({c.get('linkage') for c in configs if (c.get('metric'),c.get('k'))==(x.get('metric'),x.get('k'))})>1 for x in configs):
            names.add('linkage_comparison')
        if any(len({c.get('metric') for c in configs if (c.get('linkage'),c.get('k'))==(x.get('linkage'),x.get('k'))})>1 for x in configs):
            names.add('distance_comparison')
    return {key:PLANNED_EVIDENCE[key] for key in PLANNED_EVIDENCE if key in names}


def study_disclosure(method, configs, evidence=None):
    """Human-readable descriptions appear only for methods and metrics actually used."""
    evidence=evidence or planned_evidence(method,configs)
    means={
       'kmeans':'本次選擇 K-means，以數值向量與群中心平方距離建立群組。',
       'pam':'本次選擇 K-medoids（以 PAM 演算法求解），由真實觀測 medoid 代表群組。',
       'dbscan':'本次選擇 DBSCAN，以 eps 與 min_samples 的鄰域密度形成群組，可能產生雜訊。',
       'hierarchical':'本次選擇凝聚式階層分群，逐次依 Linkage（群組合併準則）合併群組。',
    }
    lines=['## 本次研究方法與選群指標',means[method]]
    metrics=sorted({c.get('metric') for c in configs if c.get('metric')})
    definitions={'gower':'Gower：各有效特徵加權平均差異；數值特徵以全距標準化，類別相同為 0、不同為 1。公式 d(i,j)=Σ[k∈Oij] w_k δ_ijk / Σ[k∈Oij] w_k；其中 i、j 為觀測、k 為特徵、Oij 為兩者共同可比較的特徵集合、w_k 為權重、δ_ijk 為第 k 特徵的不相似度；數值特徵 δ_ijk=|x_ik−x_jk|/R_k（R_k 為全距），名目類別相同為 0、不同為 1。無共同有效特徵時距離未定義。',
       'euclidean':'Euclidean：觀測數值差平方加總後開根號，對尺度與極端值敏感。',
       'manhattan':'Manhattan：觀測數值絕對差的加權和，仍依賴尺度與權重。'}
    for m in metrics:lines.append(definitions.get(m,m))
    if method=='hierarchical':
        rules={'single':'Single：兩群最近觀測對的距離；容易形成鏈結。',
               'complete':'Complete：兩群最遠觀測對的距離；偏好緊密群。',
               'average':'Average：兩群所有跨群觀測對距離的平均；折衷準則。',
               'ward':'Ward：選擇增加群內平方和最少的合併；需適當的歐氏幾何，不能直接配 Gower。'}
        for linkage in sorted({c.get('linkage') for c in configs if c.get('linkage')}):
            lines.append('本次規劃 Linkage '+rules.get(linkage, linkage))
    lines.append('本次預先規劃的指標及判讀方向：')
    for key,desc in evidence.items():lines.append('- '+desc)
    lines.append('未使用的指標不列入本次報告；單一極值不證明自然或全域最佳群數。')
    return '\n\n'.join(lines)+'\n'
