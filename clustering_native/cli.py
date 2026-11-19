"""Agent-operated JSON interface; approved operations safely auto-continue."""
import argparse
import json
import sys
from .core import clean, digest


def continuation(phase):
    # Instructions to the operator/host; these do not execute any action or
    # waive an approval token. The current gate always governs transitions.
    return {
        'S1_ROLE_REVIEW': {'kind': 'USER_GATE', 'next': 'Review research purpose and proposed variable roles; approve role mapping before preprocessing; no model fit'},
        'S1_REVIEW': {'kind': 'USER_GATE_IF_PENDING', 'next': 'Present current preprocessing proposal and wait for its specific A/B/C; otherwise do Stage 1 diagnosis and propose_preprocessing'},
        'S2_REVIEW': {'kind': 'AUTO_READONLY_UNTIL_USER_METHOD_CHOICE', 'next': 'Run/read Stage 2 EDA handoff, assess_methods and propose_method_choices; deliver attachments; stop for a NEW method choice; no model fit'},
        'S3_PLAN': {'kind': 'AUTO_READONLY_UNTIL_CANDIDATE_GATE', 'next': 'Prepare candidate_guidance, method-dependent distance preflight and budget; call propose_candidates only if preflight passes; stop for a NEW execution approval; do not fit'},
        'S3_PERMISSION': {'kind': 'USER_GATE', 'next': 'Present current candidates and budget; wait for explicit new execution approval'},
        'S3_EXECUTE': {'kind': 'AUTHORIZED_WORK', 'next': 'Run fit_candidates within approved bounded budget once; stop for independent results confirmation'},
        'S3_RESULTS': {'kind': 'USER_GATE', 'next': 'Legacy study: present results and wait for a NEW independent results confirmation'},
        'S4_EXECUTE': {'kind': 'AUTHORIZED_WORK', 'next': 'New studies: execute authorized candidate fits and diagnostic batches, then stop for final K selection; old sessions may retain independent results confirmation'},
        'S4_RESULTS': {'kind': 'USER_GATE', 'next': 'Stage 4: present candidate execution records, require new independent results confirmation before resampling diagnostics'},
        'S4_REVIEW': {'kind': 'AUTHORIZED_DIAGNOSTICS_THEN_USER_GATE', 'next': 'Run diagnose_approved once using bound diagnostic plan, then propose_final and stop for final-model review'},
        'S5_READY': {'kind': 'AUTHORIZED_REPORT_THEN_USER_GATE', 'next': 'Generate report; present artifacts; stop for delivery confirmation'},
        'S5_REVIEW': {'kind': 'USER_GATE', 'next': 'Wait for independent final delivery confirmation'},
        'COMPLETE': {'kind': 'DONE', 'next': 'No new work authorized'},
    }.get(phase, {'kind': 'STOP_UNKNOWN_STATE', 'next': 'Inspect state without mutation'})


def _dispatch_existing(request):
    from .session import Session
    req = dict(request)
    action = req.pop("action")
    if action == 'compare_approved_studies':
        from .approved_sensitivity import compare_approved_studies
        if set(req) != {'reference_session','alternative_session','output_dir'}:
            raise ValueError('Comparison needs reference_session, alternative_session and output_dir only')
        return compare_approved_studies(req['reference_session'],req['alternative_session'],req['output_dir'])
    directory = req.pop("session")
    if action == "create":
        require_roles=req.pop('require_feature_roles', True)
        csv_path=req.pop('csv')
        dictionary=req.pop('dictionary',None)
        if type(require_roles) is not bool or req:
            raise ValueError('create accepts csv, dictionary and require_feature_roles only')
        s = Session.create(csv_path, directory, dictionary, require_role_confirmation=require_roles, stage4_candidate_execution=True, auto_stage4_diagnostics=True)
        role_info = None
        if require_roles:
            roles=s.suggested_feature_roles()
            # Proposed default may still contain uncertain categories. User MUST
            # edit them before a formally acceptable role proposal.
            if any(r=='uncertain' for r in roles.values()):
                role_info={'suggested_roles':roles,'action':'propose_feature_roles','note':'Resolve uncertainty and obtain new approval'}
            else:
                s.propose_feature_roles(roles)
                role_info={'suggested_roles':roles,'pending_token':s.gate.state['proposals']['roles']['token'],
                           'action':'respond_current','note':'Approve or revise roles; no preprocessing yet'}
        from .figures import preview_assets
        from .presentation import REAL_RESEARCH_FIGURES_ONLY
        previews = preview_assets([s.directory/"eda_figures"/x for x in ("eda_numeric.svg", "eda_categories.svg", "eda_geometry.svg")])
        return {"figure_previews": previews, "phase": s.gate.state["phase"], "eda": s.state["eda"],
                "figures": [str(s.directory/"eda_figures"/x) for x in ("eda_numeric.svg", "eda_categories.svg", "eda_geometry.svg")],
                "feature_role_review": role_info,
                "next": "Stage 1B: approve or revise actual feature roles before preprocessing" if require_roles else "Legacy: propose preprocessing",
                "image_source_policy": REAL_RESEARCH_FIGURES_ONLY}
    s = Session(directory)
    if action == "respond_current":
        pending = [(k,p) for k,p in s.gate.state['proposals'].items() if p['status']=='PENDING']
        if len(pending) != 1: raise PermissionError('A unique current decision is required')
        item, proposal = pending[0]
        if set(req) != {'response'}: raise ValueError('Exactly one fresh response required')
        result = s.respond_observed(item, proposal['token'], req['response'])
        followup = None
        if result.get('advanced'):
            from .runner import auto_continue
            followup = auto_continue(s)
        if s.gate.state['phase'] == 'COMPLETE':
            from pathlib import Path
            result = {'decision':result, 'research_report':(Path(s.state['report_directory'])/'analysis.md').read_text(encoding='utf-8')}
        return {'phase':s.gate.state['phase'], 'result':result,
                'auto_followup':followup,'continuation':continuation(s.gate.state['phase'])}
    handlers = {
        "respond": s.respond,
        "respond_observed": s.respond_observed,
        "record_visual_evidence": s.record_visual_evidence,
        "propose_method_choices": s.propose_method_choices,
        "candidate_guidance": s.candidate_guidance,
        "refresh_delivery": s.refresh_delivery,
        "diagnose_approved": s.diagnose_approved,
        "propose_feature_roles": s.propose_feature_roles,
        "approve_feature_roles": s.approve_feature_roles,
        "suggested_feature_roles": s.suggested_feature_roles,
        "propose_preprocessing": s.propose_preprocessing,
        "respond_stage1": s.respond_stage1,
        "assess_methods": s.assess_methods,
        "propose_method": s.propose_method,
        "approve_method": s.approve_method,
        "propose_candidates": s.propose_candidates,
        "propose_candidate_expansion": s.propose_candidate_expansion,
        "recover_interrupted_execution": s.recover_interrupted_execution,
        "permit_execution": s.permit_execution,
        "fit_candidates": s.fit_candidates,
        "confirm_results": s.confirm_results,
        "diagnose": s.diagnose,
        "sensitivity": s.sensitivity,
        "propose_final": s.propose_final,
        "approve_final": s.approve_final,
        "report": s.report,
        "confirm_delivery": s.confirm_delivery,
        "renew_confirmation": s.renew_confirmation,
        "revise": s.revise,
    }
    if action in {'present_figures', 'stage_attachments'}:
        stage = req.pop('stage')
        if type(stage) is not int or stage not in range(1,6): raise ValueError('Stage 1..5 required')
        from .figures import preview_assets
        from .presentation import REAL_RESEARCH_FIGURES_ONLY
        if stage == 1:
            paths = sorted((s.directory/'eda_figures').glob('eda_*.svg'))
        elif stage == 2:
            if 'preprocess' not in s.gate.state['approvals']: raise PermissionError('No current approved preprocessing')
            paths = sorted((s.directory/'approved_eda_figures').glob('*.svg')) + sorted((s.directory/'eda_figures').glob('stage2*.svg'))
        elif stage == 3:
            # Stage 3 is planning-only for new studies. There are intentionally
            # no post-fit figures until Stage 4; legacy sessions retain theirs.
            if s.gate.state.get('stage4_candidate_execution', False):
                paths = []
            else:
                if not s.state['results'] or 'results' not in s.gate.state['payloads']: raise PermissionError('No current fitted candidates')
                paths = sorted((s.directory/'candidate_figures').glob('*.svg'))
        elif stage == 4:
            if not s.state.get('diagnostics'): raise PermissionError('No current Stage 4 diagnostics')
            from .core import file_hash
            evidence=s.state['diagnostics'].get('selection_evidence',{})
            for name,expected in evidence.get('hashes',{}).items():
                if file_hash(s.directory/'selection_evidence'/name) != expected: raise PermissionError('Stage 4 image evidence changed')
            paths = sorted((s.directory/'selection_evidence').glob('*.svg'))
            selected=s.directory/'stage4_final_evidence'/'stage4_selected_partition.svg'
            if selected.is_file():
                expected=s.state.get('stage4_selected_partition_hash')
                if (not expected or file_hash(selected)!=expected or
                    file_hash(selected.with_suffix('.png'))!=s.state.get('stage4_selected_partition_png_hash')):
                    raise PermissionError('Stage 4 selected model image changed')
                paths.append(selected)
        else:
            from pathlib import Path
            if not s.state.get('report_directory'): raise PermissionError('No current report')
            out=Path(s.state['report_directory'])
            if __import__('json').loads((out/'manifest.json').read_text())['status'] == 'OBSOLETE_AFTER_REVISION':
                raise PermissionError('Obsolete report')
            paths=sorted((out/'figures').glob('*.svg'))+sorted((out/'selection_evidence').glob('*.svg'))
        # Never forward another session's image, a downloaded image, or a
        # symlink escaping the approved study/report tree as research evidence.
        from pathlib import Path
        allowed_root=(Path(s.state['report_directory']) if stage == 5 else s.directory).resolve()
        if any(not Path(path).resolve().is_relative_to(allowed_root) for path in paths):
            raise PermissionError('Research figures must originate within the current study')
        if stage == 3 and s.gate.state.get('stage4_candidate_execution', False):
            if action == 'stage_attachments' and req:
                raise ValueError('Stage 3 has no figure parameters')
            if action == 'present_figures' and set(req) - {'start','limit'}:
                raise ValueError('Unexpected legacy preview parameters')
            return {'phase':s.gate.state['phase'], 'stage':3, 'attachment_count':0,
                    'attachment_markdown':'', 'figure_status':'NOT_APPLICABLE_PLANNING_ONLY',
                    'explanation':'Stage 3 plans candidates without fitting. Stage 4 delivers actual candidate plots after authorization.'}
        previews=preview_assets(paths)
        pngs=[p['preview_path'] for p in previews if p['status']=='PNG_PREVIEW_READY']
        if action == 'stage_attachments':
            if req: raise ValueError('stage_attachments accepts only stage; all figures are mandatory')
            unavailable=[p for p in previews if p['status']!='PNG_PREVIEW_READY']
            if unavailable: raise ValueError('Required PNG attachments unavailable: '+str(unavailable))
            from .presentation import attachment_batch
            return {'phase':s.gate.state['phase'], 'image_source_policy': REAL_RESEARCH_FIGURES_ONLY, **attachment_batch(pngs, stage)}
        # R4H.1: redirect the legacy inline-image CLI to the same attachment
        # path. A multimodal response with adjacent caption text produced a
        # human-confirmed collapsed one-character-wide column in the host.
        # Keep 'start'/'limit' request compatibility but never omit a required
        # figure from stage-local delivery. No model calculation is performed.
        if set(req) - {'start', 'limit'}:
            raise ValueError('present_figures accepts legacy start/limit only')
        if ('start' in req and (type(req['start']) is not int or req['start'] < 0)) or (
            'limit' in req and (type(req['limit']) is not int or not 1 <= req['limit'] <= 4)
        ):
            raise ValueError('Invalid legacy pagination parameters')
        if len(pngs) != len(previews):
            raise ValueError('Required stage PNG unavailable; use stage_attachments after fixing delivery')
        from .presentation import attachment_batch
        batch = attachment_batch(pngs, stage)
        return {'phase':s.gate.state['phase'],
                'legacy_action_redirected': 'stage_attachments',
                'legacy_inline_image_content': 'DISABLED_FOR_CHAT_LAYOUT_SAFETY',
                'image_source_policy': REAL_RESEARCH_FIGURES_ONLY, **batch}
    if action == 'auto_continue':
        if req: raise ValueError('auto_continue requires only action and session')
        from .runner import auto_continue
        result = auto_continue(s)
        return {'phase':s.gate.state['phase'], 'auto_followup':result,
                'continuation':continuation(s.gate.state['phase'])}
    if action == "gate_status":
        gate = s.gate.state
        return {'phase': gate['phase'], 'revision': gate['revision'],
                'approvals': sorted(gate['approvals']),
                'pending': {key: {'stage': p['stage'], 'revision': p['revision'],
                                 'status': p['status'], 'expires_at': p['expires_at'],
                                 'token': p['token']} for key,p in gate['proposals'].items() if p['status'] == 'PENDING'},
                'continuation': continuation(gate['phase']),
                'message': 'Read-only snapshot, not proof that a prior A was submitted or accepted'}
    if action == "status":
        return {"phase": s.gate.state["phase"], "complete": s.gate.state["complete"],
                "revision": s.gate.state["revision"], "approvals": s.gate.state["approvals"],
                "tokens": {k: p["token"] for k, p in s.gate.state["proposals"].items() if p["status"] == "PENDING"},
                "pending_approvals": s.gate.state["proposals"],
                "results": s.state["results"], "diagnostics": s.state["diagnostics"],
                "continuation": continuation(s.gate.state["phase"])}
    if action == "density_diagnostic":
        from .engine import density_diagnostic
        s.gate.expect("S3_PLAN")
        if s.method() != "dbscan":
            raise ValueError("Density diagnostics available for selected DBSCAN only")
        model, plan = s.model(), s.plan()
        return density_diagnostic(model, {c: plan["schema"][c] for c in model}, plan["weights"], **req)
    if action not in handlers:
        raise ValueError("Unknown action")
    result = handlers[action](**req)
    if action in {'respond', 'respond_observed', 'respond_current', 'confirm_delivery'} and s.gate.state['phase'] == 'COMPLETE':
        from pathlib import Path
        result = {'decision':result, 'research_report':(Path(s.state['report_directory'])/'analysis.md').read_text(encoding='utf-8')}
    public = {"phase": s.gate.state["phase"], "result": result,
              "continuation": continuation(s.gate.state["phase"])}
    if action == 'fit_candidates':
        public['stage4_execution' if s.gate.state.get('stage4_candidate_execution', False) else 'stage3_execution'] = {
            'candidate_count':len(s.state['results']),
            'candidates':[{'candidate':('D' if s.method()=='dbscan' else 'C')+str(i+1),
                           'config':r['config'],'groups':r['metrics']['clusters'],
                           'noise_n':r['info'].get('noise_n')}
                          for i,r in enumerate(s.state['results'])],
            'stability_status':'COMPLETE' if s.state.get('diagnostics') else 'NOT_RUN_UNTIL_RESULTS_CONFIRMED_IN_STAGE4',
            'quality_decision':'STAGE4_ONLY'}
    return public



def dispatch(request):
    """Resolve a durable study first, then publish the resulting checkpoint.

    No stage transition or user decision is inferred from a stored Session.
    Missing state always fails closed. ``session`` can be omitted when the
    stable root has exactly one explicitly selected current study.
    """
    from .session_store import allocate_study, preserve, resolve_session, saved_status
    if not isinstance(request, dict) or not isinstance(request.get('action'), str):
        raise ValueError('A JSON request with an action is required')
    action = request['action']
    if action == 'compare_approved_studies':
        return _dispatch_existing(request)
    req = dict(request)
    if action == 'create':
        if req.get('session') in (None, '', 'auto'):
            req['session'] = str(allocate_study())
        if 'csv' not in req:
            raise ValueError('Study creation needs the original CSV')
    else:
        req['session'] = str(resolve_session(req.get('session')))
    directory = req['session']
    try:
        if action == 'resume_current':
            from .session import Session
            s = Session(directory)
            return {'phase':s.gate.state['phase'], 'resume': saved_status(directory),
                    'continuation':continuation(s.gate.state['phase']),
                    'next':'Read-only resume; a pending decision still requires a fresh, directly observed user reply'}
        return _dispatch_existing(req)
    finally:
        # Capture even an interrupted operation that already committed a valid
        # Session state. This never marks the operation approved or successful.
        preserve(directory)



def record_execution(request, started, status, phase=None, error=None):
    """Actual CLI invocation events, never a reconstructed engine transcript."""
    from pathlib import Path
    from datetime import datetime, timezone
    if not isinstance(request, dict):
        return
    # A brand-new study without a session argument is not known until create
    # finishes; do not accidentally log its STARTED event into a prior study.
    if request.get('action') == 'create' and not request.get('session') and status == 'STARTED':
        return
    from .session_store import resolve_session, SessionUnavailable
    try:
        directory = resolve_session(request.get('session'))
    except (SessionUnavailable, FileNotFoundError, OSError, ValueError):
        return
    event={'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),
           'action':request.get('action'),'status':status,'phase':phase,
           'scope':'CLI invocation only; not per-fit stdout', 'error':error}
    try:
        with (directory/'execution_events.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps(event,ensure_ascii=False)+'\n')
        if status in ('SUCCESS','ERROR'):
            from .session_store import preserve
            preserve(directory)
    except OSError as exc:
        print('Execution log could not be retained: '+str(exc),file=sys.stderr)


def main():
    # A Windows pipe may default to a legacy code page; make the JSON protocol
    # explicitly UTF-8 so a UTF-8 consumer never receives corrupted Chinese.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", help="JSON request file; stdin when omitted")
    args = parser.parse_args()
    request = None
    from datetime import datetime, timezone
    started = datetime.now(timezone.utc).isoformat()
    try:
        if args.request:
            with open(args.request, encoding="utf-8-sig") as f:
                request = json.load(f)
        else:
            request = json.load(sys.stdin)
        record_execution(request, started, "STARTED")
        result = dispatch(request)
        record_execution(request, started, "SUCCESS", result.get("phase"))
        from .privacy import public_output
        print(json.dumps(clean(public_output(result, request)), ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        record_execution(request, started, "ERROR", error=f"{type(exc).__name__}: {exc}")
        print(json.dumps({"error": type(exc).__name__, "message": __import__("clustering_native.privacy", fromlist=["public_output"]).public_output(str(exc))}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
