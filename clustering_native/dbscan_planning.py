"""Bounded, read-only DBSCAN epsilon exploration from actual k-neighbor radii.

Never fits DBSCAN, infers natural cluster count or authorizes new candidates.
Quantiles and a *tentative* bend are deterministic exploratory proposals,
not universal thresholds or proven optimal parameter settings.
"""
from __future__ import annotations
import numpy as np


def propose_eps_candidates(radii, k: int, max_candidates: int = 6):
    values=np.asarray(radii, dtype=float)
    values=values[np.isfinite(values) & (values>0)]
    if values.size < 3 or not 1 <= k or max_candidates < 3:
        raise ValueError('Insufficient valid k-neighbor distances for bounded DBSCAN proposal')
    values.sort()
    reference=[('P25', .25), ('P50', .50), ('P75', .75), ('P90', .90), ('P95', .95)]
    rows=[{'source': label, 'eps': float(np.quantile(values, q)), 'quantile':q}
          for label,q in reference]
    # A possible bend based on the maximum normalized departure from the line
    # between P10 and P95. This is NOT a statistically validated elbow.
    preliminary=None
    if values.size >= 25 and float(values[-1]-values[0])>0:
        q10,q95=np.quantile(values,[.10,.95]); core=values[(values>=q10)&(values<=q95)]
        if len(core)>=12 and q95>q10:
            x=np.linspace(0.,1.,len(core))
            y=(core-core[0])/(core[-1]-core[0]) if core[-1]>core[0] else x
            gap=x-y
            i=int(np.argmax(gap))
            if .15 <= x[i] <= .92 and gap[i]>=.08:
                preliminary={'source':'可能轉折（探索性）','eps':float(core[i]),
                             'normalized_gap':round(float(gap[i]),5)}
    if preliminary is not None:
        # avoid near-duplicate values; don't artificially fill a six-candidate budget
        spread=float(rows[-1]['eps']-rows[0]['eps'])
        if spread>0 and all(abs(preliminary['eps']-r['eps'])>0.07*spread for r in rows):
            rows.append(preliminary)
    distinct=[]
    for row in sorted(rows, key=lambda r:r['eps']):
        if not distinct or not np.isclose(row['eps'], distinct[-1]['eps'],atol=1e-12,rtol=1e-7):
            distinct.append(row)
        elif row['source'].startswith('P'):
            # Keep the traceable percentile rather than the tentative bend.
            distinct[-1]=row
    if len(distinct)<2:
        raise ValueError('Neighborhood radii offer insufficient eps contrast; review data and min_samples')
    # If a future extension changes max_candidates, preserve upper-tail coverage.
    if len(distinct)>max_candidates:
        ranked=sorted(distinct,key=lambda r:(r['source'] not in ('P95','P90','P75','P50','P25'),
                              ['P95','P90','P75','P50','P25'].index(r['source'])
                              if r['source'] in ('P95','P90','P75','P50','P25') else 99))
        distinct=sorted(ranked[:max_candidates],key=lambda r:r['eps'])
    reasons=['由實際 k-distance 分布的 P25／P50／P75／P90／P95 計算初始參考值，並合併重複候選；上尾用於檢查半徑增加後碎群是否逐步連接。']
    if any(r['source']=='可能轉折（探索性）' for r in distinct):
        reasons.append('另外標示一個經有界曲線偏離診斷取得的可能轉折點；它不是被證明的 knee。')
    reasons.append('上尾值也可能過度合併群組；最終須同時檢查群數、雜訊、形狀及穩定性。')
    return {'neighbors_excluding_self':int(k),'candidates':distinct,
            'range':{'min':float(distinct[0]['eps']),'max':float(distinct[-1]['eps'])},
            'has_tentative_bend':any(r['source']=='可能轉折（探索性）' for r in distinct),
            'explanation':' '.join(reasons),'model_fits':0,'requires_stage3_approval':True}


def assess_approved_eps_search(results):
    """Descriptive search adequacy, not a candidate rank or extra fitted metric."""
    ordered=sorted([r for r in results if r.get('config',{}).get('eps') is not None],
                   key=lambda r:(r['config'].get('min_samples',0),r['config']['eps']))
    if len(ordered)<2:
        return {'status':'INSUFFICIENT_COMPARISON','requires_stage3_approval_for_more_fits':True}
    by_ms={}
    for r in ordered:by_ms.setdefault(r['config'].get('min_samples'),[]).append(r)
    trends=[]
    for ms, group in by_ms.items():
        if len(group)<2:continue
        counts=[int(r['metrics']['clusters']) for r in group]
        noise=[sum(1 for x in r['labels'] if x==-1)/len(r['labels']) for r in group]
        decrease=counts[-1]<counts[0]
        improving_noise=noise[-1]<noise[0]
        unresolved=(decrease and counts[-1]>2)
        trends.append({'min_samples':ms,'eps_min':float(group[0]['config']['eps']),
                       'eps_max':float(group[-1]['config']['eps']),
                       'groups_at_bounds':[counts[0],counts[-1]],
                       'noise_at_bounds':[round(noise[0],6),round(noise[-1],6)],
                       'observed_group_decrease':decrease,
                       'observed_noise_decrease':improving_noise,
                       'upper_boundary_may_need_review':unresolved})
    if not trends:
        return {'status':'MIN_SAMPLES_DIFFER_NO_DIRECT_TREND',
                'requires_stage3_approval_for_more_fits':True}
    review=any(t['upper_boundary_may_need_review'] for t in trends)
    return {'status':'REVIEW_UPPER_EPS' if review else 'DESCRIPTIVE_TRENDS_ONLY',
            'trends':trends,'needs_human_review':review,
            'recommendation':('同一 min_samples 下，eps 增加時群數仍下降；請根據 EDA 幾何與候選群組圖檢查是否仍碎群。'
                              '若要繼續探索，另提 eps 上界與擬合預算，經 Stage 3 Hard Gate 批准後才可執行。'
                              if review else
                              '檢查每個候選的群形、雜訊比例與分離／穩定性，不能只用群數或單一分數選擇。'),
            'requires_stage3_approval_for_more_fits':True,'new_fits_performed':0,
            'limitation':'描述性趨勢不是自然群數或最佳 eps 的判定規則'}
