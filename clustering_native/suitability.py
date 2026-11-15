"""Evidence-specific exploratory suitability; recommendations are not fit rankings."""
import numpy as np
from .exploration import density_eda
from .core import clean

PURPOSES = {'exploratory_partition', 'representative_observations',
            'density_noise_exploration', 'hierarchy_exploration'}


def _density_interpretation(density, n, p):
    """Every geometry statement refers to measured values, with no pass thresholds."""
    if not density['computed']:
        return density.get('reason', 'Diagnostic unavailable')
    concentration = density['concentration']
    ranges = ', '.join(f"k={r['k_excluding_self']}: {r['min']:.6g}..{r['max']:.6g}"
                       for r in density['neighbors'])
    variation = ('Measured neighbor-radius distributions vary across observations' if
                 density['radius_variation_observed'] else
                 'Measured neighbor radii are constant across observations at all inspected k')
    return (f"{variation} ({ranges}); n={n}, p={p}; "
            f"pairwise-distance CV={concentration['cv']:.6g}, "
            f"P05={concentration['p05']:.6g}, P95={concentration['p95']:.6g}; "
            f"duplicate feature rows={density['duplicate_feature_rows']}. "
            'Dimension and distance concentration must be interpreted together; no universal cutoff, '
            'knee, epsilon, or natural-group claim follows from these values')


def _recommend(rows, purpose, finite, density, n, p):
    """Purpose-led research choices, not statistical superiority or a forced ranking."""
    by = {r['method']: r for r in rows}
    eligible = {m for m, r in by.items() if r['status'] in {'適合', '有條件適用'}}
    primary, secondary, reasons = [], [], {}
    if purpose not in PURPOSES:
        rationale = '研究目的尚不明確，沒有單一首選；先補充目的與幾何語義。'
    elif density.get('all_pairwise_zero') or density.get('equidistant_pairs'):
        rationale = '觀測全部相同或成對距離等距，沒有可支持首選分群方法的距離對比；不推薦單一方法。'
    elif purpose == 'representative_observations' and 'pam' in eligible:
        primary = ['pam']; secondary = ['hierarchical'] if 'hierarchical' in eligible else []
        rationale = f'n={n}, p={p}；研究要實際代表觀測，PAM的medoid符合目的；階層結構可作次選探索，但不直接保證代表性。'
    elif purpose == 'hierarchy_exploration' and 'hierarchical' in eligible:
        primary = ['hierarchical']; secondary = ['pam'] if 'pam' in eligible else []
        rationale = f'n={n}, p={p}；階層合併直接對應研究目的，需先聲明linkage與距離；樹不證明真實切點。'
    elif purpose == 'density_noise_exploration' and density['computed'] and 'dbscan' in eligible:
        primary = ['dbscan']; secondary = ['pam'] if 'pam' in eligible else []
        rationale = f'n={n}, p={p}；DBSCAN直接對應密度與雜訊探索目的，已有近鄰診斷；診斷未決定eps或證明密度群。'
    elif purpose == 'exploratory_partition' and finite and 'hierarchical' in eligible:
        primary = [m for m in ('hierarchical','pam','kmeans') if m in eligible]; secondary = []
        rationale = (f'n={n}, p={p}、有限數值幾何可用；一般探索目的沒有足以證成單一首選的證據；並列可行方法，歐氏Ward僅為可規劃選項，'
                     '不是已擬合的優勝者。PAM提供實際代表觀測，避免平方距離的放大；仍需選距離及群數。')
    else:
        rationale = '目前幾何、缺失或計算證據不足以支持單一首選；先釐清限制，可保留多種方法供使用者選擇。'
    for method, row in by.items():
        if method in primary:
            reasons[method] = '優先探索：' + rationale
        elif method in secondary:
            reasons[method] = '次優先探索：' + row['conditional_followup'] + '；' + row['risks']
        elif method == 'kmeans':
            reasons[method] = '未列優先：目的尚未限定中心型緊密切分；平方距離及初始化需要驗證。' + row['risks']
        elif method == 'dbscan':
            reasons[method] = ('未列優先：目的雖要求密度/雜訊探索，但目前幾何或診斷不足以支持此法。' if purpose == 'density_noise_exploration' else '未列優先：目前目的不是專以密度/雜訊為主，且近鄰描述未建立單一eps的穩健性。') + row['risks']
        else:
            reasons[method] = '未列優先：目前證據不支持其相對優勢。' + row['risks']
    return {'primary': primary, 'secondary': secondary, 'single_preferred': len(primary) == 1,
            'rationale': rationale, 'method_reasons': reasons,
            'ranking_scope': 'Purpose-led exploratory recommendation, not a fitted comparison or complete ranking',
            'user_has_final_choice': True, 'await_user_choice': True,
            'natural_groups_proven': False, 'model_fits': 0}


def assess(model, plan, eda, purpose='exploratory_partition', handoff=None):
    n, p = model.shape
    types = {c: plan['schema'][c]['type'] for c in model}
    numeric = all(t in {'numeric', 'count'} for t in types.values())
    finite = numeric and np.isfinite(model.to_numpy(dtype=float)).all()
    flags = {c: v['n'] for c, v in eda['outliers'].items()}
    constants = [c for c in model if model[c].nunique(dropna=True) <= 1]
    density = density_eda(model, plan)
    evidence = {'n': n, 'p': p, 'types': types, 'remaining_missing': int(model.isna().sum().sum()),
                'numeric_ranges': eda['numeric'], 'iqr_flags': eda['outliers'], 'constants': constants,
                'duplicate_feature_rows': int(model.duplicated().sum()), 'purpose': purpose}
    if numeric and finite and p > 1:
        C = model.corr(method='spearman').to_numpy(); np.fill_diagonal(C, np.nan)
        evidence['max_abs_spearman'] = float(np.nanmax(np.abs(C))) if np.isfinite(C).any() else None
    rows = []
    for method in ('kmeans', 'hierarchical', 'dbscan', 'pam'):
        status, risks, follow = '適合', [], []
        if purpose not in PURPOSES:
            status = '資訊不足'; risks.append('Research purpose not supported/declared clearly'); follow.append('Clarify research purpose')
        elif method in {'kmeans'} and not finite:
            status = '不適合'; risks.append('Requires finite meaningful numeric geometry')
        elif method == 'dbscan':
            if density.get('all_pairwise_zero'):
                status = '不適合'; risks.append(density['reason'])
            elif numeric and not finite:
                status = '不適合'; risks.append('Remaining nonfinite/missing values prevent current Euclidean fitting')
            elif not density['computed']:
                status = '資訊不足'; risks.append(density['reason'])
            elif density.get('equidistant_pairs'):
                status = '不適合'; risks.append(_density_interpretation(density, n, p)); risks.append('Equal pairwise distances provide no density contrast for this representation')
            elif purpose == 'density_noise_exploration':
                status = '適合'; risks.append(_density_interpretation(density, n, p)); risks.append('Purpose supports density/noise exploration, not an inferred natural partition')
            else:
                status = '有條件適用'; risks.append(_density_interpretation(density, n, p)); risks.append('A single eps may merge regions or lose sparse observations; purpose does not prioritize noise')
            follow.append('Review measured radii, duplicates, dimension and concentration; specify geometry before any candidate plan; no automatic eps search')
        elif n < 3 or constants or model.isna().any().any():
            status = '有條件適用'; risks.append('Constant columns, small sample or pairwise missingness need explicit geometry review')
        elif method == 'kmeans':
            if any(flags.values()):
                status = '有條件適用'; risks.append(f'Observed IQR flags: {sum(flags.values())}; squared distances can move centers')
            follow.append('Review feature redundancy and compact-cluster interpretation; never assume equal natural groups')
        elif method == 'hierarchical':
            risks.append(f'Observed IQR flags: {sum(flags.values())}; Ward squared geometry is also sensitive to extremes'); risks.append('Choose linkage and metric: Ward Euclidean only; single chaining differs from average/complete')
            follow.append('Declare linkage before fitting; dendrogram does not establish a true cut')
        elif method == 'pam':
            risks.append('Metric still requires substantive meaning; range-scaled Gower remains sensitive to extremes')
            follow.append('Actual medoids match representative-observation exploration; bound quadratic distance and SWAP cost')
        if not risks:
            risks.append('No additional restriction observed in this EDA; model geometry and initialization still require an explicit plan')
        if not follow:
            follow.append('Resolve the stated compatibility issue before a method proposal')
        rows.append({'method': method, 'status': status, 'observed_eda_evidence': clean(evidence),
                     'compatibility': 'Exploratory use evaluated for declared purpose and observed data; not natural-group proof',
                     'risks': '; '.join(risks), 'conditional_followup': '; '.join(follow),
                     'recommendation_reason': f'Purpose={purpose}; n={n}, p={p}, missing={evidence["remaining_missing"]}; ' + '; '.join(risks)})
    result = {'methods': rows, 'density_diagnostic': density, 'structure_status': '資訊不足',
            'natural_groups_proven': False, 'purpose': purpose,
            'recommendation': _recommend(rows, purpose, finite, density, n, p)}

    handoff = handoff or {'visual': {'status':'UNREVIEWED','observations':{}}}
    visual = handoff.get('visual', {})
    observed = visual.get('observations', {})
    nonconvex = any(observed.get(k,{}).get('value') == 'observed' for k in ('nonconvex','curved'))
    linkages = {
        'ward':'Euclidean only; compact variance-minimizing groups; squared geometry sensitive to scale/extremes',
        'single':'Can follow curved connectivity; bridging/chaining and outliers must be examined',
        'complete':'Controls maximum distance; may split elongated/curved regions',
        'average':'Average dissimilarity compromise; no guarantee of recovering nonconvex structure'}
    for row in rows:
        row['computational_feasibility'] = {'status':'conditional' if row['status'] in {'資訊不足','不適合'} else 'feasible_with_budget',
            'basis':'Current feature/distance compatibility and explicit resource budget; not statistical suitability'}
        row['empirical_support'] = {'eda_hash': __import__('clustering_native.core',fromlist=['digest']).digest(handoff),
            'visual':visual, 'density_computed':density['computed'], 'natural_groups_proven':False}
        if row['method'] == 'hierarchical': row['linkage_suitability'] = linkages
    result['eda_handoff'] = handoff
    if nonconvex:
        for row in rows:
            if row['method'] in {'kmeans','pam','hierarchical'} and row['status'] != '不適合':
                row['status'] = '有條件適用'
                row['risks'] = row['risks'].replace('No additional restriction observed in this EDA; model geometry and initialization still require an explicit plan', 'Compact geometry requires explicit shape review') + '; Actual plot review reports nonconvex/curved geometry: centers/medoids do not imply shape recovery; Ward/complete may split curves, single may chain'
        if density['computed'] and finite and not density.get('all_pairwise_zero') and not density.get('equidistant_pairs') and purpose in {'exploratory_partition','density_noise_exploration'}:
            result['recommendation'].update(primary=['dbscan'],secondary=['hierarchical'],single_preferred=True,
                rationale='Actual plot review reports curved/nonconvex structure and bounded local-distance diagnostics are available. Prioritize DBSCAN exploration; single linkage is conditional on no bridging. Varying density can defeat one eps. No best method or two-group claim.')
            result['recommendation']['method_reasons'] = {
                'kmeans':'Squared-distance compact partition can split observed curves; feasible does not imply shape suitability',
                'pam':'Actual medoids do not recover arbitrary nonconvex shapes; distance/scale still matter',
                'hierarchical':'Single may follow connectivity subject to chaining; Ward/complete compactness is poorly matched; average is conditional',
                'dbscan':'Observed geometry plus measured neighbor radii supports priority exploration; inspect density variation, noise and bridges'}
    elif visual.get('status') == 'UNREVIEWED' and purpose == 'exploratory_partition':
        result['recommendation'].update(primary=[], secondary=[], single_preferred=False,
            rationale='Geometry plots have not been reviewed; computational feasibility alone cannot establish priority. Inspect exact-data scatter/pair plots or state why geometry is uninformative.')
        result['recommendation']['method_reasons'] = {r['method']:'No geometric priority established; '+r['risks'] for r in rows}
    for row in rows:
        row['recommendation_reason'] = result['recommendation']['method_reasons'][row['method']]
    result['geometry_review_status'] = visual.get('status','UNREVIEWED')
    return result
