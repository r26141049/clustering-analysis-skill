"""Explicit, bounded, read-only candidate planning; makes proposals, not models.

The automatic draft is an *exploratory proposal*, never evidence of a natural
number of groups or permission to fit. It must be approved at the existing
Stage 3 execution gate.
"""
from __future__ import annotations
import numpy as np
from .core import budget_check



def interpret_distance_linkage(session, metric, method, linkage=None):
    """Data-grounded reasons for a proposed (not validated) distance/linkage."""
    model=session.model()
    plan=session.plan()
    types={c:plan['schema'][c]['type'] for c in model}
    missing={c:int(model[c].isna().sum()) for c in model if model[c].isna().any()}
    outliers=session.state.get('approved_eda',{}).get('outliers',{})
    total_outlier_flags=sum(int(row.get('n',0)) for row in outliers.values() if isinstance(row,dict))
    visual=session.state.get('eda_handoff',{}).get('visual',{})
    if metric=='gower':
        reason=('Gower 用於不同測量層級的特徵及逐對有效觀測比較；'
                f'本次特徵型態：{", ".join(f"{c}（{t}）" for c,t in types.items())}；缺失觀測：{", ".join(f"{c} {n}筆" for c,n in missing.items()) if missing else "沒有"}。'
                '數值欄按全距標準化，極端值可能壓縮一般資料的差異；'
                '必須通過無未定義距離的預檢。'
                + ('本輪所有 '+str(len(plan['weights']))+' 個特徵的 w_k 均為 1（等權重）；'
                   if all(float(x)==1 for x in plan['weights'].values()) else
                   '本輪實際權重 w_k：'+', '.join(f'{k}={v}' for k,v in plan['weights'].items())+'；')
                + 'δ_ijk 表示兩筆觀測在特徵 k 的差異，O_ij 是共同可比較特徵；'
                  '數值差異按全距縮放，名目類別相同為 0、不同為 1。')
    elif metric=='manhattan':
        reason=(f'本次特徵皆為有限數值（{list(model.columns)}），可另外規劃 Manhattan（加權 L1）作探索性距離對照。'
                '它對單點差異採絕對值而非平方，但仍受特徵尺度及權重影響；'
                '與 Euclidean 的數值相差，不代表某一種距離必然比較好。')
    else:
        reason=(f'本次特徵皆為有限數值（{list(model.columns)}），因此可規劃 Euclidean。'
                f'已記錄 IQR 極端值標記總數={total_outlier_flags}；'
                '若變數尺度、權重或極端值不合理，歐氏距離比較可能失真。')
    linkage_reason=None
    if method=='hierarchical':
        selected=linkage or ('average' if metric=='gower' else 'ward')
        choices={
            'single':'Single 取跨群最近觀測點；能保留部分非凸連通結構，但容易 chaining、橋接與離群點影響。',
            'complete':'Complete 取跨群最遠觀測點；偏好緊密群組，可能切斷拉長或彎曲的群。',
            'average':'Average 取跨群所有觀測對的平均距離；為 Single/Complete 折衷，但不保證恢復自然群形。',
            'ward':'Ward 最小化群內平方和增加，要求適當的 Euclidean 幾何；偏緊密，可能受尺度及極端值影響。'
        }
        if selected not in choices or (selected=='ward' and metric!='euclidean'):
            raise ValueError('Linkage and feature distance are not compatible')
        linkage_reason=(f'本次候選 Linkage={selected}、Distance={metric}。'+choices[selected]+
            '此為資料型態、幾何與方法特性支持的條件性理由；'
            '只有在相同 K/距離下實際批准其他 linkage 擬合後，才有對照證據。'
            '尚未比較前不得宣稱此 linkage 表現最好。')
    from .method_rationale import summarize_visual_geometry
    geometry=summarize_visual_geometry(visual)
    return {'metric':reason,'linkage':linkage_reason,'visual':geometry,
            'interpretation':'只是擬合前的統計規劃依據，不是演算法比較勝負'}

def multivariate_separation_hint(model, plan):
    """Prefit MST bridge diagnostics in real feature space; no candidate model fits.

    For numeric data test both original and robust-standardized views, flagging
    scale dependence. A bridge-gap is merely a candidate hypothesis, not K truth.
    """
    import pandas as pd
    from scipy.spatial.distance import pdist, squareform
    from scipy.sparse.csgraph import minimum_spanning_tree, connected_components
    from scipy.sparse import csr_matrix
    n=len(model)
    if n<18 or n>500 or len(model.columns)>15:
        return {'status':'NOT_ASSESSED','reason':'Diagnostic limited to 18..500 rows, 15 features'}
    schema={c:plan['schema'][c] for c in model}
    numeric=all(v['type'] in ('numeric','count') for v in schema.values())
    distances={}
    if numeric:
        X=model.apply(pd.to_numeric,errors='coerce').to_numpy(dtype=float)
        if not np.isfinite(X).all():
            return {'status':'NOT_ASSESSED','reason':'Missing numeric values; no implicit imputation'}
        med=np.median(X,axis=0)
        scale=np.subtract(*np.percentile(X,[75,25],axis=0))
        scale=np.where(scale>1e-12,scale,np.ptp(X,axis=0))
        scale=np.where(scale>1e-12,scale,1)
        distances['raw_numeric_distance']=squareform(pdist(X))
        distances['robust_scaled_numeric_distance']=squareform(pdist((X-med)/scale))
    else:
        from .dissimilarity import gower_dissimilarity
        try:
            D,_=gower_dissimilarity(model,schema,plan['weights'])
        except (ValueError,TypeError) as exc:
            return {'status':'NOT_ASSESSED','reason':f'Gower distance unavailable: {exc}'}
        if not np.isfinite(D).all():
            return {'status':'NOT_ASSESSED','reason':'Missing pairwise comparisons'}
        distances['mixed_gower_distance']=D
    found=[]
    for mode,D in distances.items():
        if float(np.max(D))<1e-9:continue
        positives=D[D>0]
        eps=min(float(np.min(positives))*1e-6,1e-8) if len(positives) else 1e-8
        A=np.where((D==0)&(~np.eye(n,dtype=bool)),eps,D)
        tree=minimum_spanning_tree(A).tocoo()
        if len(tree.data)!=n-1:continue
        order=np.argsort(tree.data)
        weights=np.asarray(tree.data)[order]
        rows=np.asarray(tree.row)[order];cols=np.asarray(tree.col)[order]
        for k in range(2,min(9,n//6)+1):
            boundary=n-k
            below=float(weights[boundary-1]);above=float(weights[boundary])
            ratio=above/max(below,1e-12)
            if ratio<4.0 or above<1e-6:continue
            adj=csr_matrix((np.ones(boundary,dtype=int),(rows[:boundary],cols[:boundary])),shape=(n,n))
            components,lab=connected_components(adj,directed=False)
            sizes=np.bincount(lab)
            if components==k and sizes.min()>=max(3,int(np.ceil(n*.06))):
                found.append({'regions':k,'gap_ratio':round(ratio,3),
                              'smallest_region':int(sizes.min()),'distance_definition':mode})
    if not found:
        return {'status':'INCONCLUSIVE','tested_distances':list(distances),
                'reason':'No large balanced multivariate connectivity bridge gaps'}
    best=max(found,key=lambda r:r['gap_ratio'])
    return {'status':'TENTATIVE_SEPARATION','tentative_regions':best['regions'],
            'bridge_gap_ratio':best['gap_ratio'],'smallest_region':best['smallest_region'],
            'distance_definition':best['distance_definition'],
            'scale_dependence_warning':'EDA separations depend on exploratory distance/scaling; verify actual plots',
            'interpretation':'A strong observed MST bridge suggests a *candidate* K, not a model or natural-group proof',
            'candidates':found}



def observed_projection_gap_hint(model, plan):
    """Prefit *observed* feature-space gaps, not a clustering estimator.

    Require two independent numeric feature projections to show the same
    partition of original row IDs. A univariate peak count, a single feature,
    or a failed MST heuristic is not sufficient to anchor K. No partition
    optimization, model fitting, Silhouette or stability evaluation occurs.
    """
    import pandas as pd
    from itertools import combinations
    n=len(model)
    if not 24 <= n <= 500 or len(model.columns)<2:
        return {'status':'INCONCLUSIVE','reason':'Need 24..500 observations and two numeric features'}
    numeric=[c for c in model if plan['schema'][c]['type'] in ('numeric','count')]
    if len(numeric)<2:
        return {'status':'INCONCLUSIVE','reason':'Fewer than two numeric projection axes'}
    candidates=[]
    for col in numeric[:15]:
        values=pd.to_numeric(model[col],errors='coerce').to_numpy(dtype=float)
        if not np.isfinite(values).all() or np.unique(values).size < 12:
            continue
        sorted_values=np.sort(values)
        differences=np.diff(sorted_values)
        spread=float(np.percentile(values,75)-np.percentile(values,25))
        positive=differences[differences>1e-10]
        if spread<1e-10 or not len(positive):continue
        typical=float(np.median(positive))
        min_group=max(4,int(np.ceil(n*.08)))
        plausible=[]
        for i,gap in enumerate(differences):
            if not min_group <= i+1 <= n-min_group:continue
            if gap < .23*spread or gap < 3.5*max(typical,1e-10):continue
            threshold=float((sorted_values[i]+sorted_values[i+1])/2)
            plausible.append((i+1,threshold,round(float(gap/spread),3)))
        if not plausible:continue
        # The largest 2 gaps can support three *ordered* separated regions;
        # retain a two-region hypothesis as a separate, lower-complexity option.
        plausible=sorted(plausible,key=lambda t:t[2],reverse=True)[:2]
        for k in (2,3):
            if len(plausible)<k-1:continue
            boundaries=sorted(plausible[:k-1], key=lambda t:t[1])
            labels=np.searchsorted([t[1] for t in boundaries],values,side='right')
            sizes=np.bincount(labels,minlength=k)
            if len(sizes)!=k or min(sizes)<min_group:continue
            candidates.append({'feature':col,'regions':k,'labels':labels,
                               'gap_ratios':[float(t[2]) for t in boundaries],
                               'group_sizes':sizes.tolist()})
    supports=[]
    for left,right in combinations(candidates,2):
        if left['feature']==right['feature'] or left['regions']!=right['regions']:
            continue
        # Agreement of *observed co-memberships*, invariant to group numbering.
        aa=left['labels']; bb=right['labels']; n=len(aa)
        ai=aa[:,None]==aa[None,:]; bi=bb[:,None]==bb[None,:]
        mask=np.triu(np.ones((n,n),dtype=bool),1)
        agreement=float((ai[mask]==bi[mask]).mean())
        if agreement<.90:continue
        supports.append({'regions':left['regions'],'features':[left['feature'],right['feature']],
                         'pairwise_agreement':round(agreement,4),
                         'group_sizes':[left['group_sizes'],right['group_sizes']],
                         'relative_gap_ratios':[left['gap_ratios'],right['gap_ratios']]})
    if not supports:
        return {'status':'INCONCLUSIVE','tested_numeric_features':numeric,
                'reason':'No concordant, substantial empty gaps across two observed numeric axes'}
    # Favor the simpler observed partition unless distinct gaps reliably support
    # a three-region structure; do not confuse region hints with optimal K.
    supports.sort(key=lambda r:(r['regions'],r['pairwise_agreement']),reverse=True)
    best=supports[0]
    return {'status':'TENTATIVE_VISUAL_REGIONS','tentative_regions':best['regions'],
            'features':best['features'],'pairwise_agreement':best['pairwise_agreement'],
            'group_sizes':best['group_sizes'],'relative_gap_ratios':best['relative_gap_ratios'],
            'distance_definition':'Observed feature-axis gaps in approved model representation; not a Gower/K-means fit',
            'limitations':'Projection gaps are EDA hypotheses; other features may overlap, and an optimal K is not proven',
            'other_supported_hypotheses':supports}


def bounded_eda_k_hints(model, plan):
    """Cheap, bounded *univariate* structure hints; no fitted clustering or K selection.

    These histograms can suggest a wider exploratory range, but coordinate
    marginals alone cannot establish multivariate modes or an optimal K.
    """
    numeric_details = []
    observed_peaks = []
    for col in model:
        if plan['schema'][col]['type'] not in {'numeric', 'count'}:
            continue
        values = np.asarray(__import__('pandas').to_numeric(model[col], errors='coerce'), dtype=float)
        values = values[np.isfinite(values)]
        if len(values) < 18 or np.unique(values).size < 8:
            continue
        q25, q75 = np.quantile(values, [.25, .75]); spread = float(q75-q25)
        if spread <= 0 or float(np.ptp(values)) <= 0:
            continue
        width = 2 * spread / np.cbrt(len(values))
        bins = int(np.clip(np.ceil(float(np.ptp(values))/max(width, np.finfo(float).eps)), 5, 24))
        freq, _ = np.histogram(values, bins=bins)
        if bins < 5:
            continue
        smooth = np.convolve(freq, [1, 2, 1], mode='same') / 4
        # Reject tiny fluctuations; a smoothed-bin local maximum is weak EDA,
        # not an estimate of multivariate number of natural clusters.
        prominent = [i for i in range(1, bins-1)
                     if smooth[i] > smooth[i-1] and smooth[i] >= smooth[i+1]
                     and smooth[i] >= .15*max(smooth) and freq[i] >= 2]
        numeric_details.append({'feature':col,'histogram_bins':bins,
                                'weak_univariate_peaks':len(prominent),
                                'n_valid':len(values)})
        observed_peaks.append(len(prominent))
    categorical = [{'feature':col,'levels':int(model[col].nunique(dropna=True))}
                   for col in model if plan['schema'][col]['type'] in {'nominal','ordinal','binary'}]
    n = len(model)
    # log2(n) provides a broad exploratory budget, not a natural K estimate.
    # Marginal peaks can increase breadth; bounded by data and fit budget.
    breadth = min(n-1, 12, max(5, int(np.ceil(np.log2(n))),
                                 2*max(observed_peaks, default=0)))
    multi=multivariate_separation_hint(model,plan)
    projection=observed_projection_gap_hint(model,plan)
    return {'n':n,'multivariate_separation':multi,'observed_projection_separation':projection,'numeric_marginal_evidence':numeric_details,
            'categorical_cardinalities':categorical,
            'suggested_exploratory_upper_cap':int(breadth),
            'uncertainty':'單變量直方圖的峰數不代表多變量自然群數；log2(n) 僅作探索廣度基準'}


def exploratory_draft(session):
    model = session.model()
    plan = session.plan()
    method = session.method()
    n = len(model)
    if n < 5:
        raise ValueError('At least five observations required for an automatic exploratory candidate draft')
    types = [plan['schema'][c]['type'] for c in model]
    finite_numeric = all(t in {'numeric', 'count'} for t in types) and np.isfinite(model.to_numpy(dtype=float)).all()
    metric = 'euclidean' if finite_numeric and method in ('kmeans','hierarchical','dbscan') else 'gower'
    if method == 'kmeans' and not finite_numeric:
        raise ValueError('K-means requires finite numeric data; return to Stage 1')
    assessment = session.state.get('assessment', {})
    preflight = assessment.get('gower_preflight', {})
    if metric == 'gower' and preflight.get('status') not in ('PASS', 'NOT_REQUIRED'):
        raise ValueError('Gower pairwise preflight is not verified; review before any candidate execution proposal')
    rationale_detail=interpret_distance_linkage(session,metric,method)
    structure_hints = bounded_eda_k_hints(model, plan)
    diagnostics = {'fraction':0.8, 'repeats': 5 if n <= 120 else 3,
                   'seed':17,'policy':'fixed_full_data_preprocessing'}
    budget = {'memory_mb':512,'seconds_per_fit':8,'max_rows':max(n,500),
              'max_candidates':8}
    budget_check(n,budget,pam=method=='pam')
    configs=[]
    if method != 'dbscan':
        # EDA anchors come from actual, concordant observed separations (or
        # independently strong MST bridges); fallback breadth is NOT an anchor.
        mst = structure_hints['multivariate_separation']
        visual = structure_hints['observed_projection_separation']
        if visual.get('status')=='TENTATIVE_VISUAL_REGIONS':
            separation=visual
        elif mst.get('status')=='TENTATIVE_SEPARATION':
            separation=mst
        else:
            separation={}
        center=int(separation['tentative_regions']) if separation else None
        resource_cap=min(10,n-1)
        if method == 'pam' and n > 100:
            resource_cap=min(resource_cap,5)  # fallback breadth only, never override observed K
        if center is not None:
            # A two-region split can be tested against K=3; for larger
            # observed counts include both immediate neighbors (budgeted).
            ks=sorted(set(k for k in (center-1,center,center+1) if 2 <= k < n))
        else:
            upper=max(2,min(structure_hints['suggested_exploratory_upper_cap'],resource_cap))
            ks=list(range(2,upper+1))
        if len(ks)>budget['max_candidates']:
            raise PermissionError('Observed K neighborhood exceeds candidate budget; request a revised Stage 3 budget')
        for k in ks:
            if method == 'kmeans':
                conf={'metric':metric,'k':k,'init':'k-means++','n_init':10,
                      'algorithm':'lloyd','random_state':17,'tol':1e-4,'max_iter':300}
            elif method == 'pam':
                conf={'metric':'gower','k':k,'max_swaps':100}
            else:
                conf={'metric':metric,'k':k,'linkage':'ward' if metric=='euclidean' else 'average'}
            configs.append(conf)
        if method == 'hierarchical':
            # Controlled linkage comparisons must not be mistaken for a fair
            # independent best-K search for every linkage. Choose several
            # reproducible anchors *inside the approved K span*, not one
            # arbitrary central K. No model is fitted during this planning.
            anchors=sorted(set([ks[0],ks[(len(ks)-1)//2],ks[-1]]))
            alternatives=([('gower','single'),('gower','complete')]
                          if metric=='gower' else
                          [('euclidean','average'),('euclidean','complete'),
                           ('euclidean','single'),('manhattan','average')])
            available=max(0,20-len(configs))
            proposed=[{'metric':other_metric,'k':int(k),'linkage':linkage}
                      for other_metric,linkage in alternatives for k in anchors]
            configs.extend(proposed[:available])
        anchor_details=(f'實際觀察的投影分離線索={structure_hints["observed_projection_separation"]}；'
                        f'MST 連通診斷={structure_hints["multivariate_separation"]}；')
        rationale=(f'第一輪候選 K={ks}；樣本數 n={n}。'+anchor_details+
                   (f'觀察到約 {center} 個分離區域，故以 K={center} 為探索中心並比較鄰近 K；'
                    if center is not None else
                    '未取得足以定位分離區域數的多變量證據，因此使用較廣的探索性預設 K；')+
                   f'單變量峰數={structure_hints["numeric_marginal_evidence"]}；'
                   f'方法的資源預算（無結構線索時的探索廣度上限={resource_cap}）'
                   '不會取代已觀察分離區域的中心 K。'
                   '投影空隙只表示可辨識區域，並非證明自然群數、最佳 K 或模型品質；'
                   '如果探索上界勝出，擴展仍需要新的使用者授權。'+
                   (f'階層連結對照另外採 K 錨點 {anchors}，且不得預先宣稱最佳 linkage。'
                    if method=='hierarchical' else ''))
    else:
        # Calculate *only* descriptive neighbor radii. No DBSCAN or model fit.
        from .engine import geometry
        from .selection_evidence import _stats
        X, D, details = geometry(model, {c:plan['schema'][c] for c in model},plan['weights'],metric,budget)
        k = min(5,n-1)
        idx=np.arange(n)
        D[idx,idx]=np.inf
        radius=np.sort(D,axis=1)[:,k-1]
        positive=radius[np.isfinite(radius) & (radius>0)]
        if len(positive)<3:
            raise ValueError('No finite positive nearest-neighbor radii support a DBSCAN exploratory eps proposal')
        from .dbscan_planning import propose_eps_candidates
        eps_plan=propose_eps_candidates(positive, k=k, max_candidates=6)
        configs=[{'metric':metric,'eps':row['eps'],'min_samples':k+1}
                 for row in eps_plan['candidates']]
        rationale=(f'在 Stage 3 唯讀距離檢查中，使用排除自身的第 {k} 近鄰距離（min_samples={k+1} 含自身）。'
                   +eps_plan['explanation']+
                   f'本次提出 {len(configs)} 組 eps，均為待核准探索值；'
                   '尚未擬合模型，也不能據此推定自然群數或唯一最佳 eps。'
                   '各分位數、轉折候選與不確定性另記在候選參數來源。')
    budget['max_candidates']=max(8,len(configs))
    rationale += ' 距離／連結理由：'+rationale_detail['metric']+' '+(rationale_detail['linkage'] or '')+' '+rationale_detail['visual']
    sources=[]
    for conf in configs:
        row={}
        for param in conf:
            source=('data_diagnostic' if (method=='dbscan' and param=='eps') or
                    (param=='k' and method!='dbscan' and
                     center is not None and conf['k'] in ks)
                    else 'exploratory_default')
            explanation = (rationale if source=='data_diagnostic' else
               interpret_distance_linkage(session,conf['metric'],method,conf.get('linkage'))['metric'] if param=='metric' else
               ('Linkage='+conf['linkage']+'：本輪使用由探索範圍低/中/高位置確定的共同 K 對照；'
                '僅可由實際模型品質、群大小、重抽樣穩定性解釋，不能預先聲稱優劣。')
                    if param=='linkage' else
               f'事前公布的有界探索參數 {param}；不代表資料支持唯一最優設定。')
            if param in ('metric','linkage'): source = 'methodological_limit'
            if method=='dbscan' and param=='eps':
                candidate_detail=eps_plan['candidates'][len(sources)]
                explanation=(f'距離來源 {candidate_detail["source"]}，eps={conf["eps"]:.6g}；'
                             +eps_plan['explanation']+
                             '僅是探索候選，須由 Stage 3 授權後才可擬合。')
            row[param]={'source':source,'rationale':explanation}
        sources.append(row)
    initialization={'seeds':[17,23]} if method=='kmeans' else None
    return dict(configs=configs, basis='evidence-supported' if method!='dbscan' and center is not None else 'exploratory-only', evidence=rationale,
        budget=budget, diagnostics_plan=diagnostics, parameter_sources=sources,
        search_rationale=rationale,
        boundary_limitations=('候選 K／eps 的上界為計算預算，不是自然群數上界；'
                              '邊界優勢、群組過小及品質與穩定性矛盾時，必須先取得新增授權。'),
        initialization_plan=initialization)
