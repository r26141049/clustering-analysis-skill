"""Traceable EDA handoff; visual interpretation is explicitly operator evidence.

No dataset-name rules, fitted cluster models, inferred best K or nonlinear-shape
classifier. Human/operator observations must cite current exact-data plots.
"""
from pathlib import Path
import numpy as np
from .core import clean, digest, file_hash

GEOMETRY = {'nonconvex', 'curved', 'unequal_density', 'isolated_regions', 'coarse_fine_structure'}


def geometry_figures(df, schema, directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    numeric = [c for c in df if schema.get(c, {}).get('role', 'feature') == 'feature'
               and schema.get(c, {}).get('type') in {'numeric', 'count'}]
    shown = numeric[:4]
    if len(shown) < 2:
        return []
    out = Path(directory); out.mkdir(parents=True, exist_ok=True)
    if len(shown) == 2:
        fig, ax = plt.subplots(figsize=(7, 5)); axes = np.array([[ax]])
        ax.scatter(df[shown[0]], df[shown[1]], s=10, alpha=.65)
        ax.set_aspect('equal', adjustable='datalim')
        ax.set(xlabel='F'+str(list(df).index(shown[0])+1), ylabel='F'+str(list(df).index(shown[1])+1))
    else:
        fig, axes = plt.subplots(len(shown), len(shown), figsize=(9, 9), squeeze=False)
        for i, y in enumerate(shown):
            for j, x in enumerate(shown):
                ax = axes[i,j]
                if i == j: ax.hist(df[x].dropna(), bins='auto', color='#387c94')
                else: ax.scatter(df[x], df[y], s=6, alpha=.45)
                if i == len(shown)-1: ax.set_xlabel('F'+str(list(df).index(x)+1))
                if j == 0: ax.set_ylabel('F'+str(list(df).index(y)+1))
    fig.suptitle('Observed feature geometry (no cluster labels)')
    fig.tight_layout()
    path = out/'eda_geometry.png'; fig.savefig(path.with_suffix('.svg')); fig.savefig(path, dpi=150); plt.close(fig)
    return [str(path)]


def summarize(df, eda, schema, model_hash=None, visual=None):
    numeric = df.select_dtypes(include='number')
    correlation = numeric.corr(method='spearman')
    pairs = [{'features':[str(correlation.columns[i]),str(correlation.columns[j])],
              'spearman':float(correlation.iloc[i,j])}
             for i in range(len(correlation)) for j in range(i) if np.isfinite(correlation.iloc[i,j])]
    return clean({'schema_version':1, 'n':len(df), 'features':list(df), 'p':len(df.columns),
        'types':{c:schema.get(c,{}).get('type','unknown') for c in df},
        'model_hash':model_hash, 'numeric_ranges':eda.get('numeric',{}), 'correlations':pairs,
        'missing':df.isna().sum().to_dict(), 'iqr_flags':eda.get('outliers',{}),
        'visual':visual or {'status':'UNREVIEWED','observations':{},'basis':[],
                            'limitations':'Geometry not yet visually reviewed; do not equate computability with suitability'},
        'uncertainty':'Marginal/pairwise projections do not establish full-dimensional groups or best K; no reduction required'})


def validate_visual(observations, basis, limitations, allowed_paths):
    if not isinstance(observations,dict) or set(observations) != GEOMETRY:
        raise ValueError('Explicit geometry observations required: '+str(sorted(GEOMETRY)))
    for value in observations.values():
        if not isinstance(value,dict) or value.get('value') not in {'observed','not_observed','uncertain'} or not isinstance(value.get('reason'),str) or not value['reason'].strip():
            raise ValueError('Every visual observation requires value and substantive reason')
    if not basis or not isinstance(limitations,str) or not limitations.strip():
        raise ValueError('Current plot basis and visual limitations required')
    allowed = {Path(p).resolve() for p in allowed_paths}
    records=[]
    for path in basis:
        path=Path(path).resolve(strict=True)
        if path not in allowed: raise ValueError('Visual evidence must cite current approved-model EDA plots')
        records.append({'path':str(path), 'sha256':file_hash(path)})
    return {'status':'OPERATOR_VISUAL_REVIEW_RECORDED','observations':observations,'basis':records,
            'limitations':limitations,'source':'operator interpretation of actual plots; not automated proof'}


def candidate_context(handoff, method, configs, density=None):
    visual=handoff.get('visual',{})
    if method == 'dbscan':
        scope={'eps':[c['eps'] for c in configs], 'min_samples':[c['min_samples'] for c in configs]}
        caution='eps must cite actual neighbor distances, min_samples includes self; inspect noise, bridges, fragmentation and sensitivity. No universal knee or best eps.'
    else:
        ks=[c['k'] for c in configs]; scope={'k_min':min(ks),'k_max':max(ks),'k_values':ks}
        caution='Explain coarse/fine hypotheses, both K limits and expansion triggers. Visual separation is not proof of K; no sample-size formula gives best K.'
    return {'eda_hash':digest(handoff),'n':handoff['n'],'p':handoff['p'], 'visual':visual,
            'search':scope, 'caution':caution, 'neighbor_diagnostic':density or {'computed':False,'reason':'No current Stage 2 diagnostic; do not invent eps evidence'}, 'scale_correlation_outlier_review':{
                k:handoff[k] for k in ('numeric_ranges','correlations','iqr_flags')},
            'expansion_triggers':['preferred boundary','unresolved upper-tail trend','conflicting evidence'],
            'parameter_origin_requirement':'Each key: data_diagnostic / research_purpose / methodological_limit / exploratory_default / user_specified, with rationale'}
