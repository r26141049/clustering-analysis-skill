"""Bounded continuation of already authorized or strictly read-only work.

Never makes a user's method/final-model choice and never grants a Gate approval.
The single public respond_current entrypoint can call this after a fresh reply.
"""
from pathlib import Path
from .planning import exploratory_draft


def _candidate_review(session):
    """Stage 3 gives counts only; Stage 4 exposes quality and stability."""
    from .report_explanations import actual_metric_contrast
    results=session.state.get('results',[])
    evidence=session.state.get('diagnostics') or {}
    stable=evidence.get('stability') or session.state.get('stage3_stability') or []
    if not stable:
        return [{'candidate_index':i,'config':r['config'],
                 'groups':r['metrics'].get('clusters'),
                 'noise_n':r['info'].get('noise_n'),
                 'evaluation':'STAGE4_PENDING'} for i,r in enumerate(results)]
    if len(results)!=len(stable):
        raise PermissionError('Model/stability evidence incomplete')
    contrast=actual_metric_contrast(results,stable)
    return [{'candidate_index':row['candidate_index'], 'config':row['config'],
             'silhouette':row['silhouette'],
             'groups':results[row['candidate_index']]['metrics'].get('clusters'),
             'ari_mean_conditional':row['ari_mean'],
             'stability_failures':row['resample_failures']}
             for row in contrast['candidates']]


def auto_continue(session, max_steps=5):
    if type(max_steps) is not int or not 1 <= max_steps <= 6:
        raise ValueError('max_steps must be in 1..6')
    steps = []
    for _ in range(max_steps):
        phase = session.gate.state['phase']
        pending = [key for key,p in session.gate.state['proposals'].items()
                   if p['status'] == 'PENDING']
        if pending:
            return {'steps':steps,'stop':'USER_DECISION_REQUIRED',
                    'pending_items':pending,'phase':phase}
        if phase == 'S2_REVIEW':
            proposal = session.propose_method_choices()
            steps.append({'action':'propose_method_choices','phase':phase,
                          'options':proposal['options'],
                          'recommendation_priorities':proposal['recommendation_priorities'],
                          'priority_legend':proposal['priority_legend'],
                          'comparison_markdown':proposal['comparison_markdown'],
                          'assessment':session.state.get('assessment'),
                          'model_fits':0})
        elif phase == 'S3_PLAN':
            try:
                draft = exploratory_draft(session)
                session.propose_candidates(**draft)
            except (ValueError, MemoryError, PermissionError) as exc:
                return {'steps':steps,'stop':'PLAN_REVIEW_REQUIRED',
                        'reason':f'{type(exc).__name__}: {exc}',
                        'no_fit_performed':True, 'phase':session.gate.state['phase']}
            steps.append({'action':'propose_candidates','phase':phase,
                          'candidate_count':len(draft['configs']),
                          'configs':draft['configs'], 'rationale':draft['search_rationale'],
                          'budget':draft['budget'],'diagnostics_plan':draft['diagnostics_plan'],
                          'statistical_disclosure':session.gate.state['payloads']['candidates'].get('statistical_disclosure'),
                          'model_fits':0})
        elif phase in {'S3_EXECUTE', 'S4_EXECUTE'}:
            execution = session.fit_candidates()
            steps.append({'action':'fit_candidates','phase':phase,
                          'candidate_count':len(session.state['results']),
                          'stage4_stability_batches':len((session.state.get('diagnostics') or {}).get('stability',[])),
                          'model_fits':'approved full-data candidates and bound Stage 4 diagnostics' if session.state.get('diagnostics') else 'approved full-data candidates only',
                          'candidate_review':_candidate_review(session)})
        elif phase == 'S4_REVIEW':
            if session.state.get('diagnostics') is not None:
                return {'steps':steps,'stop':'FINAL_MODEL_DECISION_REQUIRED',
                        'phase':phase, 'selection_evidence':session.state['diagnostics'].get('selection_evidence'),
                        'candidate_review':_candidate_review(session),
                        'metric_contrast': session.state['diagnostics'].get('metric_contrast')}
            diagnostics = session.diagnose_approved()
            steps.append({'action':'diagnose_approved','phase':phase,
                          'candidate_count':len(session.state['results']),
                          'stability_reused':bool(session.state.get('stage3_stability_bound')),
                          'stage4_stability_batches':len(diagnostics.get('stability',[]))})
            return {'steps':steps,'stop':'FINAL_MODEL_DECISION_REQUIRED',
                    'phase':phase,'selection_evidence':diagnostics.get('selection_evidence'),
                    'candidate_review':_candidate_review(session),
                    'metric_contrast': diagnostics.get('metric_contrast')}
        elif phase == 'S5_READY':
            # Fresh sibling directory: never overwrite the analysis or old report.
            directory = session.directory.parent/(session.directory.name + '_report_revision_' +
                                                   str(session.gate.state['revision']))
            if directory.exists() and any(directory.iterdir()):
                return {'steps':steps,'stop':'REPORT_DESTINATION_REVIEW_REQUIRED',
                        'reason':'A report already exists at the default destination',
                        'phase':phase, 'destination':str(directory)}
            session.report(directory)
            steps.append({'action':'report','phase':phase,'destination':str(directory),
                          'report_files':['analysis.md','analysis.qmd','analysis_offline.html']})
        else:
            return {'steps':steps, 'stop': 'USER_DECISION_REQUIRED' if phase in
                    {'S1_REVIEW','S3_PERMISSION','S3_RESULTS','S4_RESULTS','S5_REVIEW'} else 'NO_ACTION_REQUIRED',
                    'phase':phase}
    return {'steps':steps,'stop':'STEP_LIMIT_REACHED','phase':session.gate.state['phase']}
