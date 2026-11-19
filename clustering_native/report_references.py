"""References limited to methods and metrics disclosed in this study.

Retain the provenance and caution of the historical audit without copying
out-of-scope methods into the user-facing Stage 5 attachment.
"""
from pathlib import Path

BASE = [
    ('K-means', 'Hartigan & Wong (1979)', 'Original K-means procedure differs from the Lloyd solver used in this Skill'),
    ('PAM / medoids', 'Kaufman & Rousseeuw (1990)', 'BUILD/SWAP does not prove global optimality'),
    ('Gower distance', 'Gower (1971)', 'Mixed-type similarities and pairwise-missing comparability must be disclosed'),
    ('Hierarchical / Ward', 'Ward (1963)', 'Standard Ward assumes a valid Euclidean variance interpretation'),
    ('DBSCAN', 'Ester et al. (1996)', 'Density/noise recovery depends on eps and min_samples'),
    ('Silhouette', 'Rousseeuw (1987)', 'Higher internal separation does not prove natural groups'),
    ('Adjusted Rand Index', 'Hubert & Arabie (1985)', 'Only aligned, comparable observation sets may be compared')]


def write_study_references(path, method=None, selected_metrics=None):
    lines=['# 本次研究採用的方法與指標：文獻定位', '',
           '此表依既有文獻稽核資料整理，僅涵蓋本次事先介紹的方法與指標；不是本輪重新查證原文的紀錄。', '',
           '| 相關主題 | 原始參考來源 | 適用限制 |', '|---|---|---|']
    method_topics={'kmeans':{'K-means'},'pam':{'PAM / medoids','Gower distance'},'dbscan':{'DBSCAN'},'hierarchical':{'Hierarchical / Ward','Gower distance'}}
    include=method_topics.get(method,set()) if method else {x[0] for x in BASE}
    include.add('Silhouette');include.add('Adjusted Rand Index')
    lines += ['| '+topic+' | '+source+' | '+caution+' |' for topic,source,caution in BASE if topic in include]
    lines += ['', '本研究的 ARI 是共同 ID 重抽樣一致性指標，並非外部驗證。']
    Path(path).write_text('\n'.join(lines)+'\n',encoding='utf-8')
