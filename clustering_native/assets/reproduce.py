"""Re-execute an approved report snapshot; no user-facing environment setup."""
from pathlib import Path
import argparse
import json
import sys
from datetime import datetime, timezone
import traceback
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT/"reproducibility"))


def record(event, **details):
    line = json.dumps({"time_utc": datetime.now(timezone.utc).isoformat(), "event": event, **details}, ensure_ascii=False)
    with (ROOT/"reproduction_events.jsonl").open("a", encoding="utf-8") as f:
        f.write(line+"\n")
    print(line, flush=True)


def main():
    from clustering_native.core import digest, file_hash, write_json
    from clustering_native.engine import bounded_fit, stability
    from clustering_native.data import preprocess
    import numpy as np
    import pandas as pd
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    parser.parse_args()
    record("start", command="reproduce.py --verify")
    write_json(ROOT/"reproduction_result.json", {"status": "RUNNING"})
    config = json.loads((ROOT/"config.json").read_text(encoding="utf-8"))
    for name, expected in config["snapshot_hashes"].items():
        if file_hash(ROOT/name) != expected:
            raise ValueError(f"Snapshot changed: {name}")
    raw = pd.DataFrame(json.loads((ROOT/"raw_feature_snapshot.json").read_text(encoding="utf-8")))
    expected_model = pd.DataFrame(json.loads((ROOT/"model_feature_snapshot.json").read_text(encoding="utf-8")))
    plan = config["preprocessing_plan"]
    model, fitted = preprocess(raw, plan)
    # Dtypes can change after JSON roundtrip, so compare numerical values/strings.
    pd.testing.assert_frame_equal(model, expected_model, check_dtype=False)
    expected = json.loads((ROOT/"candidate_results.json").read_text(encoding="utf-8"))
    diagnostics = json.loads((ROOT/"diagnostics.json").read_text(encoding="utf-8"))
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
                          settings["fraction"], settings["repeats"], settings["seed"], settings["preprocessing_policy"])
        if digest(rerun) != digest(settings):
            raise AssertionError("Stability reproduction differs; inspect dependency versions")
        rows.append({"candidate": i, "verified": True})
        record("candidate_verified", candidate_index=i)
    if diagnostics.get("initialization") is not None:
        proxy=SimpleNamespace(model=lambda:model, plan=lambda:plan,
            state={"results":expected}, gate=SimpleNamespace(state={"payloads":{"candidates":config["candidate_plan"]}}))
        initialization=initialization_diagnostics(proxy,config["candidate_plan"].get("initialization_plan"))
        if digest(initialization)!=digest(diagnostics["initialization"]):
            raise AssertionError("Initialization diagnostic reproduction differs")
    evidence_path=ROOT/"selection_evidence"/"selection_evidence.json"
    if evidence_path.exists():
        evidence=json.loads(evidence_path.read_text())
        for i,row in enumerate(evidence["candidate_comparison"]):
            if row["config"]!=expected[i]["config"] or row["metrics"]!=expected[i]["metrics"]:
                raise AssertionError("Selection evidence differs from scientific candidate data")
    write_json(ROOT/"reproduction_result.json", {"status": "PASS", "candidates": rows,
                                                "scope": "Approved snapshots; not installation or literature acceptance"})


if __name__ == "__main__":
    try:
        main()
        record("complete", status="PASS", exit_code=0)
    except Exception as exc:
        from clustering_native.core import write_json
        write_json(ROOT/"reproduction_result.json", {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})
        record("failure", status="ERROR", error=f"{type(exc).__name__}: {exc}", exit_code=1)
        raise
