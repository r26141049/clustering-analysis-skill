"""Descriptive selection evidence from approved fits; no automatic model winner.
Plots export exact machine-readable source values. No estimator is replaced.
"""
from __future__ import annotations
import copy,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .core import clean,digest,write_json
SOURCES={'data_diagnostic','research_purpose','exploratory_default','user_specified','methodological_limit'}
def validate_search_plan(method,configs,sources,rationale,boundaries,initialization):
    if not isinstance(sources,list) or len(sources)!=len(configs):raise ValueError('Every candidate requires parameter_sources')
    for config,entry in zip(configs,sources):
        if not isinstance(entry,dict) or set(entry)!=set(config):raise ValueError('Provenance must cover every and only candidate parameter')
        for param,origin in entry.items():
            if not isinstance(origin,dict) or set(origin)!={'source','rationale'} or origin['source'] not in SOURCES or not isinstance(origin['rationale'],str) or not origin['rationale'].strip():raise ValueError('Invalid or missing parameter source/rationale: '+param)
    if not isinstance(rationale,str) or not rationale.strip() or not isinstance(boundaries,str) or not boundaries.strip():raise ValueError('Explain search range and boundary limitations before permission')
    if method=='kmeans':
        if not isinstance(initialization,dict) or set(initialization)!={'seeds'}:raise ValueError('K-means requires an explicit initialization_plan seeds budget')
        seeds=initialization['seeds']
        if not isinstance(seeds,list) or not 2<=len(seeds)<=20 or any(type(i)is not int or not 0<=i<2**32 for i in seeds) or len(set(seeds))!=len(seeds):raise ValueError('Use 2..20 distinct explicit diagnostic seeds')
    elif initialization is not None:raise ValueError('Initialization restart fits apply only to K-means')
def validate_explanation(e,n,index):
    required={'chosen_reason','candidate_reasons','conflicts','limitations'}
    if not isinstance(e,dict) or not required<=set(e) or set(e)-required-{'retained_candidates'}:raise ValueError('Structured final explanation required')
    if any(not isinstance(e[k],str) or not e[k].strip() for k in required-{'candidate_reasons'}):raise ValueError('Explain choice, conflicts and limitations')
    if not isinstance(e['candidate_reasons'],dict) or set(e['candidate_reasons'])!={str(i) for i in range(n)} or any(not isinstance(v,str) or not v.strip() for v in e['candidate_reasons'].values()):raise ValueError('Explain retention/nonselection for every candidate')
    retained=e.get('retained_candidates',[])
    if not isinstance(retained,list) or any(type(i)is not int or not 0<=i<n for i in retained) or len(set(retained))!=len(retained):raise ValueError('Invalid parallel retained candidates')
    if index is not None and retained and index not in retained:raise ValueError('Chosen candidate must be among retained candidates')
def initialization_diagnostics(session,plan):
    if plan is None:return {'status':'NOT_APPLICABLE','runs':[]}
    from .engine import bounded_fit
    model=session.model();schema={c:session.plan()['schema'][c] for c in model};runs=[]
    cache=session.state.get('initialization_reuse') or {}
    allowed=cache.get('seeds')==plan['seeds']
    prior_runs={(r['candidate_index'],r['seed']):r for r in cache.get('runs',[]) if
                isinstance(r,dict) and 'candidate_index' in r and 'seed' in r}
    reused=0
    for i,result in enumerate(session.state['results']):
        for seed in plan['seeds']:
            config={**result['config'],'n_init':1,'random_state':seed}
            old = (prior_runs.get((i,seed)) if allowed and
                   i < len(cache.get('configs',[])) and
                   result['config']==cache['configs'][i] else None)
            if old is not None:
                runs.append(copy.deepcopy(old)); reused+=1; continue
            try:
                fit=bounded_fit(model,schema,session.plan()['weights'],'kmeans',config,session.gate.state['payloads']['candidates']['budget'])
                runs.append({'candidate_index':i,'seed':seed,'n_init':1,'inertia':fit['info']['wcss'],'n_iter':fit['info']['n_iter'],'converged':fit['info']['converged'],'labels':fit['labels'],'warnings':fit['warnings'],'error':None})
            except (ValueError,RuntimeError,TimeoutError,MemoryError) as exc:runs.append({'candidate_index':i,'seed':seed,'n_init':1,'inertia':None,'error':str(exc)})
    if cache: session.gate.event('initialization_seed_reuse',reused=reused,executed=len(runs)-reused)
    session.state.pop('initialization_reuse',None)
    return clean({'status':'COMPUTED','policy':'Explicit single-restart seed diagnostics, separate from native multi-start candidate fits; no global optimum claim','runs':runs})
def _stats(values):
    good=[float(v) for v in values if v is not None and np.isfinite(v)]
    return {'valid_n':len(good),'null_n':len(values)-len(good),'mean':float(np.mean(good)) if good else None,'median':float(np.median(good)) if good else None,'min':min(good) if good else None,'max':max(good) if good else None,'values':values}
def build_selection_evidence(session):
    """No fitting: all inputs are actual stored candidate and approved diagnostic results."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from .figures import preview_assets
    from .dissimilarity import aligned_ari
    out=session.directory/'selection_evidence';out.mkdir(exist_ok=True)
    results=session.state['results'];method=session.method();diags=session.state['diagnostics'];payload=session.gate.state['payloads']['candidates'];table=[];sizes=[];medoids=[];tree_rows=[];cut_sensitivity=[]
    if len(results)!=len(diags.get('stability',[])) or len(results)!=len(payload['configs']):
        raise ValueError('Incomplete candidate/stability evidence; no silent truncation')
    for r,d in zip(results,diags['stability']):
        if len(d.get('runs',[]))!=payload['diagnostics_plan']['repeats']:
            raise ValueError('Incomplete resampling evidence')
        if len(r['labels'])!=len(session.model()):raise ValueError('Candidate label count mismatch')
    for i,(r,d) in enumerate(zip(results,diags['stability'])):
        labels=np.asarray(r['labels']);n=len(labels);noise=labels==-1;effective=~noise if method=='dbscan' else np.ones(n,dtype=bool);ari=_stats([x['ari'] for x in d['runs']]);sil=r['metrics']['silhouette'];row={'candidate_index':i,'config':r['config'],'parameter_sources':payload['parameter_sources'][i],'requested_k':r['config'].get('k'),'actual_nonnoise_groups':r['metrics']['clusters'],'total_n':n,'silhouette_effective_n':int(effective.sum()),'silhouette':sil,'silhouette_status':'DEFINED' if sil is not None else 'UNDEFINED','silhouette_observation_set_sha256':digest(np.flatnonzero(effective).tolist()),'noise_n':int(noise.sum()) if method=='dbscan' else None,'core_n':r['info'].get('core_n'),'border_n':r['info'].get('border_n'),'noise_fraction':r['info'].get('noise_fraction'),'objective':r['info'].get('wcss',r['info'].get('objective')),'metrics':{key:value for key,value in r['metrics'].items() if key not in {'calinski_harabasz','davies_bouldin'}},'stability_ari':ari,'resample_failures':d['failures'],'warnings':r['warnings']}
        table.append(row)
        for g in sorted(set(labels)):
            size=int((labels==g).sum());sizes.append({'candidate_index':i,'group':'Noise' if g==-1 else f'Cluster {int(g)+1}','n':size,'fraction':size/n})
            if g==-1:continue
        for j in r['info'].get('medoid_positions',[]):medoids.append({'candidate_index':i,'row_position_zero_based':j,'internal_row_id':f'Row {j+1}','actual_observation':True})
        if 'linkage_matrix' in r['info']:
            Z=np.asarray(r['info']['linkage_matrix']);k=r['config']['k'];tree_rows.append({'candidate_index':i,'k':k,'metric':r['config']['metric'],'linkage':r['config']['linkage'],'merge_height_k_to_k_minus_1':float(Z[n-k,2]),'linkage_sha256':digest(Z.tolist())})
    linkage_comparisons=[]
    distance_comparisons=[]
    if method=='hierarchical':
        # A K cut from a *different* dendrogram is not adjacent-cut
        # sensitivity. Keep these two kinds of evidence separate.
        grouped={}
        for i,r in enumerate(results):
            conf=r['config']; grouped.setdefault((conf['metric'],conf['linkage']), []).append((conf['k'],i))
        for (metric,linkage), observed in grouped.items():
            previous=None
            for k,i in sorted(observed):
                if previous is not None:
                    prior_k,j=previous
                    cut_sensitivity.append({'candidate_a':j,'candidate_b':i,
                        'ari_full_common_ids':aligned_ari(list(range(len(results[j]['labels']))),
                            results[j]['labels'],list(range(len(results[i]['labels']))),results[i]['labels']),
                        'same_metric':metric,'same_linkage':linkage,
                        'k_a':prior_k,'k_b':k,
                        'interpretation':'Adjacent observed cuts of same linkage/metric, NOT re-sampling stability'})
                previous=(k,i)
        by_cut={}
        for i,r in enumerate(results):
            conf=r['config']; by_cut.setdefault((conf['metric'],conf['k']),[]).append(i)
        # Distance comparisons are permitted only at identical K and
        # linkage; otherwise multiple methodological choices are confounded.
        by_linkage_cut={}
        for i,r in enumerate(results):
            conf=r['config'];by_linkage_cut.setdefault((conf['linkage'],conf['k']),[]).append(i)
        for (linkage,k),indices in sorted(by_linkage_cut.items()):
            if len({results[i]['config']['metric'] for i in indices})<2:
                continue
            for i in indices:
                current=results[i]
                distance_comparisons.append({'candidate_index':i,'linkage':linkage,'k':k,
                    'metric':current['config']['metric'],
                    'silhouette':current['metrics'].get('silhouette'),
                    'stability_ari_mean':table[i]['stability_ari']['mean'],
                    'others_same_linkage_and_k':[
                        {'candidate_index':j,'metric':results[j]['config']['metric'],
                         'paired_full_data_ari':aligned_ari(list(range(len(current['labels']))),current['labels'],
                             list(range(len(results[j]['labels']))),results[j]['labels'])}
                        for j in indices if j!=i],
                    'limitation':'Different distance scales mean silhouettes are descriptive, not causal evidence of a superior metric'})
        for (metric,k),ix in sorted(by_cut.items()):
            if len({results[i]['config']['linkage'] for i in ix})<2:
                continue
            for i in ix:
                a=results[i]
                linkage_comparisons.append({'candidate_index':i,'metric':metric,'k':k,
                    'linkage':a['config']['linkage'],'silhouette':a['metrics'].get('silhouette'),
                    'stability_ari_mean':table[i]['stability_ari']['mean'],
                    'min_nonnoise_group_size':min(int(np.count_nonzero(np.asarray(a['labels'])==g))
                        for g in set(a['labels']) if g!=-1),
                    'other_linkages_same_cut':[{
                        'candidate_index':j, 'linkage':results[j]['config']['linkage'],
                        'paired_full_data_ari':aligned_ari(list(range(len(a['labels']))),a['labels'],
                            list(range(len(results[j]['labels']))),results[j]['labels'])}
                        for j in ix if j!=i],
                    'interpretation':'Identical approved metric and K, different approved linkage; observational comparison, not proof of superiority'})
    ranges={}
    for param in ('k','eps','min_samples'):
        values=sorted({r['config'][param] for r in results if param in r['config']})
        if values:ranges[param]={'min':values[0],'max':values[-1],'values':values,'varied':len(values)>1}
    boundary_candidates={str(i):[param for param,span in ranges.items() if span['varied'] and r['config'].get(param) in (span['min'],span['max'])] for i,r in enumerate(results)}
    extrema=[]
    for metric,larger in [('silhouette',True)]:
        pairs=[(i,r['metrics'].get(metric)) for i,r in enumerate(results) if r['metrics'].get(metric) is not None]
        if pairs:
            target=(max if larger else min)(v for i,v in pairs);indices=[i for i,v in pairs if np.isclose(v,target,rtol=1e-12,atol=1e-12)]
            extrema.append({'metric':metric,'direction':'higher' if larger else 'lower','candidate_indices':indices,'boundary_parameters':{str(i):boundary_candidates[str(i)] for i in indices},'interpretation':'Descriptive metric extrema only, not model selection or statistical significance'})
    # P4-18: fail closed if this revision's Stage 4 selection evidence would
    # introduce an indicator absent from the approved Stage 3 specification.
    from .education import PLANNED_EVIDENCE
    planned=payload.get('planned_metric_evidence')
    actual={'silhouette','cluster_sizes','resampling_ari',
            'boundary_warning'}
    if any(r['objective'] is not None for r in table):
        actual.add('medoid_objective' if method=='pam' else 'wcss')
    if method=='dbscan': actual.add('noise_fraction')
    if tree_rows: actual.add('merge_heights')
    if cut_sensitivity: actual.add('cut_sensitivity')
    if linkage_comparisons: actual.add('linkage_comparison')
    if distance_comparisons: actual.add('distance_comparison')
    if payload.get('initialization_plan'): actual.add('initialization')
    if planned is not None:
        if not isinstance(planned,dict) or not actual.issubset(planned) or not set(planned).issubset(PLANNED_EVIDENCE):
            raise PermissionError('Undisclosed Stage 4 selection metric: revise Stage 3 and reauthorize before use')
        metric_disclosure_audit={'status':'ALL_REPORTED_METRICS_PREDISCLOSED',
            'planned':sorted(planned),'used':sorted(actual),
            'source':'approved Stage 3 candidates payload'}
    else:
        metric_disclosure_audit={'status':'LEGACY_PROSE_DISCLOSURE_ONLY',
            'used':sorted(actual),
            'limitation':'Historical Stage 3 payload has prose disclosure only; machine-validated predeclaration NOT established'}
    # Recommendation for *proposing* a new Stage 3 scope, not permission to fit.
    expansion=None
    silhouette_extrema=next((e for e in extrema if e['metric']=='silhouette'),None)
    if silhouette_extrema and 'k' in ranges and ranges['k']['varied']:
        kmax=ranges['k']['max']; kmin=ranges['k']['min']
        winners=silhouette_extrema['candidate_indices']
        if any(results[i]['config'].get('k')==kmax for i in winners):
            n=len(session.model())
            newks=list(range(kmax+1,min(kmax+2,n-1)+1))
            if newks:
                prototype=next(r['config'] for r in results if r['config']['k']==kmax)
                configs=[{**prototype,'k':int(k)} for k in newks]
                repeats=payload['diagnostics_plan']['repeats']
                seeds=len((payload.get('initialization_plan') or {}).get('seeds',[]))
                expansion={'trigger':'Silhouette maximum among assessed candidates occurs at upper K boundary',
                    'suggested_new_k':newks, 'suggested_configs':configs,
                    'additional_candidate_fits':len(configs),
                    'additional_subsampling_fits':len(configs)*repeats,
                    'additional_initialization_fits':len(configs)*seeds,
                    'requires_new_stage3_gate':True,
                    'no_fits_performed':True,
                    'interpretation':'K upper boundary is a search limitation, not evidence of a natural K'}
    from .dbscan_planning import assess_approved_eps_search
    dbscan_eps_review = (assess_approved_eps_search(results) if method=='dbscan'
                         else {'status':'NOT_APPLICABLE'})
    boundary_analysis={'parameter_ranges':ranges,'candidate_boundary_parameters':boundary_candidates,
        'quality_metric_extrema':extrema,'suggested_extension':expansion,
        'dbscan_eps_review':dbscan_eps_review,
        'action':'Disclose favored boundary candidates; any extra search needs revised Stage3 authorization'}
    from .report_explanations import actual_metric_contrast
    evidence={'method':method,'metric_contrast':actual_metric_contrast(results,diags['stability']),'boundary_analysis':boundary_analysis,'candidate_comparison':table,'cluster_sizes':sizes,'medoids':medoids,'merge_heights':tree_rows,'cut_sensitivity':cut_sensitivity,'linkage_comparisons':linkage_comparisons,'distance_comparisons':distance_comparisons,'metric_disclosure_audit':metric_disclosure_audit,'dbscan_eps_review':dbscan_eps_review,'initialization':diags['initialization'],'search_rationale':payload['search_rationale'],'boundary_limitations':payload['boundary_limitations'],'metric_caveats':['Internal comparisons do not prove natural groups.','No weighted composite or universal pass threshold.','NA values remain undefined.','DBSCAN silhouettes exclude noise and may compare different observation sets.','Fixed full-data preprocessing does not include preprocessing-estimation uncertainty.','Common-ID subsampling ARI is conditional stability.'],'interpretation':'由已核准候選及例行診斷產生；不自動選出優勝者。'}
    write_json(out/'selection_evidence.json',evidence)
    csvrows=[]
    for row in table:
        csvrows.append({k:v for k,v in row.items() if k not in {'config','metrics','stability_ari','parameter_sources','warnings'}}|{'parameters_json':json.dumps(row['config'],sort_keys=True),'parameter_sources_json':json.dumps(row['parameter_sources'],ensure_ascii=False),'ari_mean':row['stability_ari']['mean'],'ari_median':row['stability_ari']['median'],'ari_valid_n':row['stability_ari']['valid_n'],'ari_null_n':row['stability_ari']['null_n'],**row['metrics']})
    pd.DataFrame(csvrows).to_csv(out/'candidate_comparison.csv',index=False)
    for name,rows in [('cluster_sizes',sizes),('medoids',medoids),('merge_heights',tree_rows),('cut_sensitivity',cut_sensitivity),('linkage_comparisons',linkage_comparisons),('distance_comparisons',distance_comparisons)]:pd.DataFrame(rows).to_csv(out/f'{name}.csv',index=False)
    initial=diags['initialization']['runs'];pd.DataFrame([{k:v for k,v in x.items() if k not in {'labels','warnings'}} for x in initial]).to_csv(out/'initialization_diagnostics.csv',index=False)
    figures=[];x=list(range(1,len(results)+1))
    # Multiple distance/linkage variants at the same K must NOT be joined as
    # though they were successive cuts of one fitted model.
    competing_hierarchical = method=='hierarchical' and len({
        (r['config']['metric'],r['config']['linkage']) for r in results})>1
    axis=(x if competing_hierarchical else
          [r['config'].get('k',i+1) for i,r in enumerate(results)])
    xlabel=('Candidate index (see parameters)' if competing_hierarchical
            else 'Requested K' if method!='dbscan' else 'Candidate (proposal order)')
    def save(fig,name,source):
        for ext in ('png','svg'):fig.savefig(out/(name+'.'+ext),dpi=150,bbox_inches='tight')
        write_json(out/(name+'.plot_data.json'),source);figures.append(str(out/(name+'.svg')));plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,4));ys=[np.nan if r['silhouette'] is None else r['silhouette'] for r in table];(axs[0].scatter(axis,ys) if competing_hierarchical else axs[0].plot(axis,ys,'o-'));axs[0].set(xlabel=xlabel,ylabel='Mean silhouette',title='Undefined values are not zero')
    for xx,row in zip(axis,table):
        if row['silhouette'] is None:axs[0].annotate('Undefined',(xx,0),rotation=45)
    for i,xx in enumerate(axis):axs[1].scatter([xx]*sum(z['candidate_index']==i for z in sizes),[z['n'] for z in sizes if z['candidate_index']==i],color='#267c96',alpha=.65)
    axs[1].set(xlabel=xlabel,ylabel='Observations per group',title='Group sizes (noise included if present)');fig.tight_layout();save(fig,'quality_and_sizes',{'x':axis,'configs':[r['config'] for r in results], 'silhouette': [r['silhouette'] for r in table],'sizes':sizes,'mixed_candidate_axes':competing_hierarchical})
    # Stability visualization uses the *same* actual resampled ARI, no
    # second per-group metric or hidden diagnostic fit.
    fig,ax=plt.subplots(figsize=(6,4));valid=[r['stability_ari']['values'] for r in table]
    for i,vals in enumerate(valid):
        good=[v for v in vals if v is not None]
        if good: ax.boxplot([good],positions=[axis[i]],widths=.35,showmeans=True)
        else: ax.text(axis[i],0,'Undefined',rotation=90)
    ax.set(xlabel=xlabel,ylabel='Resampled ARI (higher = more consistent)',
           title='Approved common-ID resampling; failures retained')
    fig.tight_layout();save(fig,'stability',{'x':axis,'ari_values':valid,
        'failed_repeats':[r['resample_failures'] for r in table]})
    if method in {'kmeans','pam'}:
        fig,ax=plt.subplots(figsize=(6,4));obj=[t['objective'] for t in table];ax.plot(axis,obj,'o-');ax.set(xlabel='Requested K',ylabel='Inertia / WCSS' if method=='kmeans' else 'Sum of dissimilarities to medoids',title='Objective decrease alone cannot select K');save(fig,'objective',{'k':axis,'objective':obj})
    if initial:
        fig,ax=plt.subplots(figsize=(6,4))
        for i,xx in enumerate(axis):
            runs=[z for z in initial if z['candidate_index']==i];ax.scatter([xx]*len(runs),[np.nan if z['inertia'] is None else z['inertia'] for z in runs])
        ax.set(xlabel='Requested K',ylabel='Single-restart inertia',title='Explicit seed sensitivity (n_init=1 diagnostics)');save(fig,'initialization',initial)
    if method=='hierarchical':
        from scipy.cluster.hierarchy import dendrogram
        seen=set()
        for i,r in enumerate(results):
            Z=np.asarray(r['info']['linkage_matrix']);h=digest(Z.tolist())
            if h in seen:continue
            seen.add(h);fig,ax=plt.subplots(figsize=(8,4.5));dendrogram(Z,truncate_mode='lastp',p=20,leaf_rotation=90,leaf_font_size=8,ax=ax);ax.set(title=f'Actual {r["config"]["linkage"]} dendrogram (last 20 subtrees)',ylabel='SciPy linkage height');save(fig,f'dendrogram_{i}',{'candidate_index':i,'linkage_matrix':Z.tolist(),'truncation_lastp':20})
        fig,ax=plt.subplots(figsize=(6,4))
        by_geometry={}
        for row in tree_rows:
            by_geometry.setdefault((row['metric'],row['linkage']), []).append(row)
        for (distance,linkage),rows in sorted(by_geometry.items()):
            ordered=sorted(rows,key=lambda r:r['k'])
            ax.plot([z['k'] for z in ordered],
                    [z['merge_height_k_to_k_minus_1'] for z in ordered],
                    'o-',label=distance+'/'+linkage)
        ax.set(xlabel='K before merge to K-1',ylabel='SciPy linkage height',
               title='Only compare heights within SAME distance and linkage')
        if len(by_geometry)>1:ax.legend(fontsize=7)
        save(fig,'merge_heights',{'rows':tree_rows,
            'warning':'Height values across distance/linkage definitions are not commensurable'})
        fig,ax=plt.subplots(figsize=(6,4));ax.plot([z['candidate_b']+1 for z in cut_sensitivity],[z['ari_full_common_ids'] for z in cut_sensitivity],'o-');ax.set(xlabel='Second candidate in adjacent proposal pair',ylabel='Full-data ARI between cuts',title='Cut sensitivity, distinct from resampling');save(fig,'cut_sensitivity',cut_sensitivity)
    if method=='dbscan':
        fig,axs=plt.subplots(2,2,figsize=(10,7))
        for ms in sorted({r['config']['min_samples'] for r in results}):
            ix=sorted([i for i,r in enumerate(results) if r['config']['min_samples']==ms],key=lambda i:results[i]['config']['eps']);eps=[results[i]['config']['eps'] for i in ix]
            for ax,key in [(axs[0,0],'actual_nonnoise_groups'),(axs[0,1],'noise_fraction'),(axs[1,0],'silhouette'),(axs[1,1],'silhouette_effective_n')]:ax.plot(eps,[np.nan if table[i][key] is None else table[i][key] for i in ix],'o-',label=f'min_samples={ms}')
        for ax,title in zip(axs.ravel(),['Non-noise groups','Noise fraction','Silhouette (noise excluded)','Silhouette effective observations']):ax.set(xlabel='eps',ylabel=title,title=title);ax.legend()
        fig.tight_layout();save(fig,'dbscan_parameter_sensitivity',{'candidates':[{'config':r['config'],'metrics':t} for r,t in zip(results,table)]})
        fig,ax=plt.subplots(figsize=(7,4));bottom=np.zeros(len(results))
        for key,label in [('core_n','Core'),('border_n','Border'),('noise_n','Noise')]:
            values=np.array([t[key] for t in table]);ax.bar(x,values,bottom=bottom,label=label);bottom+=values
        ax.set(xlabel='Candidate',ylabel='Observations',title='Core / border / noise counts');ax.legend();save(fig,'dbscan_point_types',{'candidate_order':x,'core_n':[t['core_n'] for t in table],'border_n':[t['border_n'] for t in table],'noise_n':[t['noise_n'] for t in table]})
    if method=='pam':
        # Medoid row indices have no metric scale; the old scatter graph was
        # misleading. Save observed representative features and group size.
        source=session.raw()[list(session.model().columns)]
        for medoid in medoids:
            candidate=results[medoid['candidate_index']]
            pos=medoid['row_position_zero_based']
            medoid['observed_features']=clean(source.iloc[pos].to_dict())
            medoid['candidate_k']=candidate['config']['k']
            medoid['group_size']=int(np.sum(np.asarray(candidate['labels']) ==
                np.asarray(candidate['labels'])[pos]))
        write_json(out/'medoid_feature_table.json',medoids)
    # Actual saved labels, NOT new fits. Candidate partitions are Stage 4
    # evaluation evidence, not a premature Stage 3 'final' plot.
    from .figures import candidate_partition_grid
    partition = candidate_partition_grid(session.model(), results, out/'candidate_partitions.svg')
    if partition is not None:
        figures.append(str(partition))
    previews=preview_assets([Path(f) for f in figures]);write_json(out/'figure_previews.json',previews)
    return {'directory':str(out),'hashes':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.iterdir()) if f.is_file()},'source_sha256':digest(evidence),'figure_previews':previews,'candidate_count':len(results),'boundary_policy':payload['boundary_limitations'],'no_automatic_winner':True}
