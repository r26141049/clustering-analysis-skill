"""Re-execute an approved report snapshot with auditable, fail-closed comparisons.

The original scientific snapshots and user approvals are read-only. Rerun outputs
and evidence are stored separately, even if the SHA-256 comparison fails.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
import platform
import sys
import traceback
import uuid

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT / "reproducibility"))


class StabilityMismatch(AssertionError):
    def __init__(self, candidate_index, evidence_file, rerun_file, summary):
        super().__init__(f"Candidate {candidate_index} stability differs; inspect {evidence_file}")
        self.candidate_index = candidate_index
        self.evidence_file = evidence_file
        self.rerun_file = rerun_file
        self.summary = summary


def record(event, **details):
    line = json.dumps({"time_utc": datetime.now(timezone.utc).isoformat(),
                       "event": event, **details}, ensure_ascii=False)
    with (ROOT / "reproduction_events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")
    print(line, flush=True)


def _preview(value):
    """Keep the delta readable; complete rerun is separately persisted."""
    serialized = json.dumps(value, ensure_ascii=False, default=str)
    return serialized if len(serialized) <= 240 else serialized[:237] + "..."


def _diff(expected, actual, path="$", limit=500):
    differences = []
    total = 0

    def emit(where, kind, old, new):
        nonlocal total
        total += 1
        if len(differences) < limit:
            differences.append({"path": where, "kind": kind,
                                "original": _preview(old), "rerun": _preview(new)})

    def compare(a, b, where):
        if type(a) is not type(b):
            emit(where, "type", a, b)
        elif isinstance(a, dict):
            for key in sorted(a.keys() | b.keys()):
                child = f"{where}.{key}"
                if key not in a:
                    emit(child, "added", None, b[key])
                elif key not in b:
                    emit(child, "missing", a[key], None)
                else:
                    compare(a[key], b[key], child)
        elif isinstance(a, list):
            if len(a) != len(b):
                emit(where + ".length", "length", len(a), len(b))
            for i in range(min(len(a), len(b))):
                compare(a[i], b[i], f"{where}[{i}]")
        elif a != b:
            emit(where, "value", a, b)

    compare(expected, actual, path)
    return {"total": total, "shown": len(differences),
            "truncated": total > len(differences), "differences": differences}


def _is_timeout(run):
    return "TimeoutError" in str(run.get("error") or "")


def _run_status(run):
    if not run.get("error"):
        return "SUCCESS"
    return "TIMEOUT" if _is_timeout(run) else "ERROR"


def compare_stability(original, rerun, candidate_index, config):
    """Diagnose exact differences; never convert differences into PASS."""
    from clustering_native.core import digest
    original_runs = original.get("runs", [])
    rerun_runs = rerun.get("runs", [])
    changed_runs = []
    categories = set()
    for pos in range(max(len(original_runs), len(rerun_runs))):
        if pos >= len(original_runs) or pos >= len(rerun_runs):
            categories.add("run_count_changed")
            changed_runs.append({"run_position": pos, "difference": "missing run"})
            continue
        a, b = original_runs[pos], rerun_runs[pos]
        if a == b:
            continue
        prior, newer = _run_status(a), _run_status(b)
        transitions = []
        if prior != newer:
            transitions.append("execution_status_changed")
            if "TIMEOUT" in (prior, newer):
                transitions.append("timeout_status_changed")
        if a.get("row_positions") != b.get("row_positions"):
            transitions.append("sample_indices_changed")
        if a.get("repeat") != b.get("repeat"):
            transitions.append("repeat_index_changed")
        if a.get("ari") != b.get("ari") or a.get("cluster_jaccard") != b.get("cluster_jaccard"):
            transitions.append("stability_statistic_changed")
        if a.get("warnings") != b.get("warnings"):
            transitions.append("warnings_changed")
        if a.get("error") != b.get("error") and prior == newer:
            transitions.append("error_details_changed")
        categories.update(transitions)
        changed_runs.append({"run_position": pos, "original_repeat": a.get("repeat"),
                             "rerun_repeat": b.get("repeat"), "original_status": prior,
                             "rerun_status": newer, "categories": transitions})
    original_digest, rerun_digest = digest(original), digest(rerun)
    differences = _diff(original, rerun)
    if differences["total"] and not categories:
        categories.add("non_run_metadata_changed")
    return {
        "verdict": "PASS" if original_digest == rerun_digest else "FAIL",
        "candidate_index": candidate_index, "candidate_config": config,
        "original_sha256": original_digest, "rerun_sha256": rerun_digest,
        "original_failures": original.get("failures"), "rerun_failures": rerun.get("failures"),
        "original_timeout_repeats": [r.get("repeat") for r in original_runs if _is_timeout(r)],
        "rerun_timeout_repeats": [r.get("repeat") for r in rerun_runs if _is_timeout(r)],
        "run_count_original": len(original_runs), "run_count_rerun": len(rerun_runs),
        "changed_runs": changed_runs, "categories": sorted(categories),
        "field_differences": differences,
        "interpretation_limit": ("A changed timeout status is evidence of a possible execution-environment effect, "
                                 "not proof that all numerical results reproduce.")
    }


def _runtime_info():
    info = {"python": sys.version, "platform": platform.platform(),
            "environment_threads": {n: os.environ.get(n) for n in
                ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}}
    for name in ("numpy", "pandas", "scipy", "scikit-learn"):
        try:
            info[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            info[name] = "NOT INSTALLED"
    return info


def main():
    from clustering_native.core import digest, file_hash, write_json
    from clustering_native.engine import bounded_fit, stability
    from clustering_native.data import preprocess
    import numpy as np
    import pandas as pd

    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    parser.parse_args()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    audit_dir = ROOT / "reproduction_audit" / run_id
    audit_dir.mkdir(parents=True, exist_ok=False)
    record("start", command="reproduce.py --verify", audit_dir=str(audit_dir.relative_to(ROOT)))
    write_json(ROOT / "reproduction_result.json", {"status": "RUNNING", "audit_dir": str(audit_dir.relative_to(ROOT))})
    original_environment_path = ROOT / "environment.json"
    original_environment = json.loads(original_environment_path.read_text(encoding="utf-8")) if original_environment_path.exists() else None
    write_json(audit_dir / "environment_comparison.json", {
        "original_report_environment": original_environment, "rerun_environment": _runtime_info(),
        "scope": "Environment metadata supports diagnosis, not numerical equivalence."})

    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    for name, expected_hash in config["snapshot_hashes"].items():
        if file_hash(ROOT / name) != expected_hash:
            raise ValueError(f"Snapshot changed: {name}")
    raw = pd.DataFrame(json.loads((ROOT / "raw_feature_snapshot.json").read_text(encoding="utf-8")))
    expected_model = pd.DataFrame(json.loads((ROOT / "model_feature_snapshot.json").read_text(encoding="utf-8")))
    plan = config["preprocessing_plan"]
    model, fitted = preprocess(raw, plan)
    pd.testing.assert_frame_equal(model, expected_model, check_dtype=False)
    expected = json.loads((ROOT / "candidate_results.json").read_text(encoding="utf-8"))
    diagnostics = json.loads((ROOT / "diagnostics.json").read_text(encoding="utf-8"))
    from clustering_native.selection_evidence import initialization_diagnostics
    from types import SimpleNamespace
    rows = []
    for i, candidate in enumerate(config["candidate_plan"]["configs"]):
        record("candidate_start", candidate_index=i)
        result = bounded_fit(model, plan["schema"], plan["weights"], config["method"], candidate,
                             config["candidate_plan"]["budget"])
        if result["labels"] != expected[i]["labels"]:
            raise AssertionError("Deterministic labels changed; inspect environment before acceptance")
        for key, val in expected[i]["metrics"].items():
            actual = result["metrics"][key]
            if isinstance(val, (int, float)):
                if not np.isclose(val, actual, rtol=1e-7, atol=1e-9):
                    raise AssertionError(f"Metric mismatch: {key}")
            elif actual != val:
                raise AssertionError(f"Metric contract mismatch: {key}")
        settings = diagnostics["stability"][i]
        rerun = stability(raw, model, plan, config["method"], result, config["candidate_plan"]["budget"],
                          settings["fraction"], settings["repeats"], settings["seed"], settings["preprocessing_policy"],
                          audit_path=audit_dir / "fit_runtime_events.jsonl", candidate_index=i)
        # Crucial post3 ordering: persist the full rerun BEFORE comparing hashes.
        rerun_file = audit_dir / f"candidate_{i:02d}_rerun.json"
        write_json(rerun_file, rerun)
        audit = compare_stability(settings, rerun, i, candidate)
        comparison_file = audit_dir / f"candidate_{i:02d}_comparison.json"
        write_json(comparison_file, audit)
        if audit["verdict"] != "PASS":
            record("stability_mismatch", candidate_index=i,
                   comparison_file=str(comparison_file.relative_to(ROOT)),
                   rerun_file=str(rerun_file.relative_to(ROOT)),
                   categories=audit["categories"])
            raise StabilityMismatch(i, str(comparison_file.relative_to(ROOT)),
                                    str(rerun_file.relative_to(ROOT)), audit)
        rows.append({"candidate": i, "verified": True})
        record("candidate_verified", candidate_index=i)
    if diagnostics.get("initialization") is not None:
        proxy = SimpleNamespace(model=lambda: model, plan=lambda: plan,
            state={"results": expected}, gate=SimpleNamespace(state={"payloads": {"candidates": config["candidate_plan"]}}))
        initialization = initialization_diagnostics(proxy, config["candidate_plan"].get("initialization_plan"))
        if digest(initialization) != digest(diagnostics["initialization"]):
            raise AssertionError("Initialization diagnostic reproduction differs")
    evidence_path = ROOT / "selection_evidence" / "selection_evidence.json"
    if evidence_path.exists():
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        for i, row in enumerate(evidence["candidate_comparison"]):
            if row["config"] != expected[i]["config"] or row["metrics"] != expected[i]["metrics"]:
                raise AssertionError("Selection evidence differs from scientific candidate data")
    write_json(ROOT / "reproduction_result.json", {"status": "PASS", "candidates": rows,
        "audit_dir": str(audit_dir.relative_to(ROOT)),
        "scope": "Approved snapshots; not installation or literature acceptance"})


if __name__ == "__main__":
    try:
        main()
        record("complete", status="PASS", exit_code=0)
    except Exception as exc:
        from clustering_native.core import write_json
        details = {"status": "FAIL" if isinstance(exc, StabilityMismatch) else "ERROR",
                   "error": f"{type(exc).__name__}: {exc}"}
        if isinstance(exc, StabilityMismatch):
            details.update({"stage": "stability", "candidate_index": exc.candidate_index,
                            "comparison_file": exc.evidence_file, "rerun_file": exc.rerun_file,
                            "categories": exc.summary["categories"]})
        write_json(ROOT / "reproduction_result.json", details)
        record("failure", **details, exit_code=1)
        raise
