"""Agent-operated JSON interface. One action per invocation; never auto-advance."""
import argparse
import json
import sys
from .core import clean, digest


def dispatch(request):
    from .session import Session
    req = dict(request)
    action = req.pop("action")
    directory = req.pop("session")
    if action == "create":
        s = Session.create(req.pop("csv"), directory, req.pop("dictionary", None))
        from .figures import preview_assets
        previews = preview_assets([s.directory/"eda_figures"/x for x in ("eda_numeric.svg", "eda_categories.svg", "eda_geometry.svg")])
        return {"figure_previews": previews, "phase": s.gate.state["phase"], "eda": s.state["eda"],
                "figures": [str(s.directory/"eda_figures"/x) for x in ("eda_numeric.svg", "eda_categories.svg", "eda_geometry.svg")],
                "next": "Present EDA and a concrete preprocessing proposal; await A/B/C"}
    s = Session(directory)
    handlers = {
        "respond": s.respond,
        "record_visual_evidence": s.record_visual_evidence,
        "propose_method_choices": s.propose_method_choices,
        "candidate_guidance": s.candidate_guidance,
        "refresh_delivery": s.refresh_delivery,
        "diagnose_approved": s.diagnose_approved,
        "propose_preprocessing": s.propose_preprocessing,
        "respond_stage1": s.respond_stage1,
        "assess_methods": s.assess_methods,
        "propose_method": s.propose_method,
        "approve_method": s.approve_method,
        "propose_candidates": s.propose_candidates,
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
        from .presentation import image_batch
        if stage == 1:
            paths = sorted((s.directory/'eda_figures').glob('eda_*.svg'))
        elif stage == 2:
            if 'preprocess' not in s.gate.state['approvals']: raise PermissionError('No current approved preprocessing')
            paths = sorted((s.directory/'approved_eda_figures').glob('*.svg')) + sorted((s.directory/'eda_figures').glob('stage2*.svg'))
        elif stage == 3:
            if not s.state['results'] or 'results' not in s.gate.state['payloads']: raise PermissionError('No current fitted candidates')
            paths = sorted((s.directory/'candidate_figures').glob('*.svg'))
        elif stage == 4:
            if not s.state.get('diagnostics'): raise PermissionError('No current Stage 4 diagnostics')
            from .core import file_hash
            evidence=s.state['diagnostics'].get('selection_evidence',{})
            for name,expected in evidence.get('hashes',{}).items():
                if file_hash(s.directory/'selection_evidence'/name) != expected: raise PermissionError('Stage 4 image evidence changed')
            paths = sorted((s.directory/'selection_evidence').glob('*.svg'))
        else:
            from pathlib import Path
            if not s.state.get('report_directory'): raise PermissionError('No current report')
            out=Path(s.state['report_directory'])
            if __import__('json').loads((out/'manifest.json').read_text())['status'] == 'OBSOLETE_AFTER_REVISION':
                raise PermissionError('Obsolete report')
            paths=sorted((out/'figures').glob('*.svg'))+sorted((out/'selection_evidence').glob('*.svg'))
        previews=preview_assets(paths)
        pngs=[p['preview_path'] for p in previews if p['status']=='PNG_PREVIEW_READY']
        if action == 'stage_attachments':
            if req: raise ValueError('stage_attachments accepts only stage; all figures are mandatory')
            unavailable=[p for p in previews if p['status']!='PNG_PREVIEW_READY']
            if unavailable: raise ValueError('Required PNG attachments unavailable: '+str(unavailable))
            from .presentation import attachment_batch
            return {'phase':s.gate.state['phase'], **attachment_batch(pngs, stage)}
        batch=image_batch(pngs, **req)
        batch['unavailable']=[p for p in previews if p['status']!='PNG_PREVIEW_READY']
        return {'phase':s.gate.state['phase'], **batch}
    if action == "status":
        return {"phase": s.gate.state["phase"], "complete": s.gate.state["complete"],
                "revision": s.gate.state["revision"], "approvals": s.gate.state["approvals"],
                "tokens": {k: p["token"] for k, p in s.gate.state["proposals"].items() if p["status"] == "PENDING"},
                "pending_approvals": s.gate.state["proposals"],
                "results": s.state["results"], "diagnostics": s.state["diagnostics"]}
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
    return {"phase": s.gate.state["phase"], "result": result}



def record_execution(request, started, status, phase=None, error=None):
    """Actual CLI invocation events, never a reconstructed engine transcript."""
    from pathlib import Path
    from datetime import datetime, timezone
    if not isinstance(request, dict) or not isinstance(request.get('session'), str):
        return
    directory=Path(request['session'])
    if not (directory/'session.json').is_file():
        return
    event={'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),
           'action':request.get('action'),'status':status,'phase':phase,
           'scope':'CLI invocation only; not per-fit stdout', 'error':error}
    try:
        with (directory/'execution_events.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps(event,ensure_ascii=False)+'\n')
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
        result = dispatch(request)
        record_execution(request, started, "SUCCESS", result.get("phase"))
        print(json.dumps(clean(result), ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        record_execution(request, started, "ERROR", error=f"{type(exc).__name__}: {exc}")
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
