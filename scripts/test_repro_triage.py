"""RC6-REPRO-01: forensic replay must persist actual reruns without relaxing verification."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "clustering_native" / "assets" / "reproduce.py"
spec = importlib.util.spec_from_file_location("rc6_reproduce_triage", SOURCE)
triage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(triage)


def make_run(repeat, *, error=None, ari=0.9, positions=None):
    result = {"repeat": repeat, "row_positions": positions if positions is not None else [0, 2, 3],
              "ari": None if error else ari,
              "error": error}
    if not error:
        result["warnings"] = []
    return result


def make_stability(runs):
    return {"name": "common-ID subsampling ARI",
            "fraction": 0.8, "repeats": len(runs), "seed": 17,
            "preprocessing_policy": "fixed_full_data_preprocessing",
            "runs": runs, "failures": sum(r["error"] is not None for r in runs)}


class ReportDiff(unittest.TestCase):
    def test_identical_is_pass(self):
        obj = make_stability([make_run(0), make_run(1)])
        out = triage.compare_stability(obj, copy.deepcopy(obj), 0, {"k": 2})
        self.assertEqual(out["verdict"], "PASS")
        self.assertEqual(out["field_differences"]["total"], 0)
        self.assertEqual(out["changed_runs"], [])
    def test_timeout_turns_to_success_is_fail_and_attributed(self):
        old = make_stability([make_run(0), make_run(1, error="TimeoutError: Approved fit time exceeded")])
        new = make_stability([make_run(0), make_run(1, ari=0.84)])
        original = copy.deepcopy(old)
        report = triage.compare_stability(old, new, 0, {"linkage": "ward", "k": 2})
        self.assertEqual(report["verdict"], "FAIL")
        self.assertEqual(report["original_timeout_repeats"], [1])
        self.assertEqual(report["rerun_timeout_repeats"], [])
        self.assertIn("timeout_status_changed", report["categories"])
        self.assertIn("stability_statistic_changed", report["categories"])
        self.assertTrue(any(d["path"] == "$.runs[1].error" for d in report["field_differences"]["differences"]))
        self.assertEqual(old, original)
    def test_changed_ari_fails_even_if_both_runs_succeed(self):
        old = make_stability([make_run(0), make_run(1)])
        new = make_stability([make_run(0, ari=0.899), make_run(1)])
        report = triage.compare_stability(old, new, 0, {"k": 2})
        self.assertEqual(report["verdict"], "FAIL")
        self.assertIn("stability_statistic_changed", report["categories"])
        self.assertNotIn("timeout_status_changed", report["categories"])
    def test_changed_indices_and_repeat_are_reported(self):
        old = make_stability([make_run(0), make_run(1)])
        new = make_stability([make_run(0, positions=[1, 2, 3]), make_run(7)])
        report = triage.compare_stability(old, new, 2, {"k": 3})
        self.assertEqual(report["verdict"], "FAIL")
        self.assertIn("sample_indices_changed", report["categories"])
        self.assertIn("repeat_index_changed", report["categories"])
    def test_non_run_metadata_difference_is_not_suppressed(self):
        old = make_stability([make_run(0), make_run(1)])
        new = dict(old, fraction=0.9)
        report = triage.compare_stability(old, new, 0, {"k": 2})
        self.assertEqual(report["verdict"], "FAIL")
        self.assertIn("non_run_metadata_changed", report["categories"])
    def test_delta_truncation_keeps_correct_total(self):
        left, right = {"a": list(range(1000))}, {"a": [-1]*1000}
        delta = triage._diff(left, right, limit=8)
        self.assertEqual(delta["total"], 1000)
        self.assertEqual(delta["shown"], 8)
        self.assertTrue(delta["truncated"])


class ScriptIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.out = Path(self.temp.name)
        folder = self.out / "reproducibility" / "clustering_native"
        folder.mkdir(parents=True)
        shutil.copy2(ROOT / "clustering_native" / "core.py", folder / "core.py")
        (folder / "__init__.py").write_text("", encoding="utf-8")
        (folder / "data.py").write_text("def preprocess(raw, plan): return raw.copy(), {}\n", encoding="utf-8")
        (folder / "engine.py").write_text(
            "from pathlib import Path\nimport json\n"
            "ROOT=Path(__file__).resolve().parents[2]\n"
            "def bounded_fit(model,schema,weights,method,config,budget):\n"
            "    return json.loads((ROOT/'candidate_results.json').read_text())[0]\n"
            "def stability(raw,model,plan,method,result,budget,fraction,repeats,seed,policy,**kwargs):\n"
            "    return json.loads((ROOT/'stability_rerun.json').read_text())\n", encoding="utf-8")
        (folder / "selection_evidence.py").write_text(
            "def initialization_diagnostics(*args,**kwargs): return None\n", encoding="utf-8")
        shutil.copy2(SOURCE, self.out / "reproduce.py")
        self.original = make_stability([make_run(0), make_run(1, error="TimeoutError: Approved fit time exceeded")])
        self.actual = make_stability([make_run(0), make_run(1, ari=0.9)])
        raw = {"x": [0.0, 2.0, 5.0], "y": [1.0, 3.0, 6.0]}
        snapshot_map = {"raw_feature_snapshot.json": raw,
                        "model_feature_snapshot.json": raw,
                        "candidate_results.json": [{"labels": [0, 1, 1], "metrics": {"silhouette": 0.34},
                                                     "config": {"linkage": "ward", "k": 2}}],
                        "diagnostics.json": {"stability": [self.original], "initialization": None}}
        for filename, value in snapshot_map.items():
            self.write_json(filename, value)
        sha = {key: hashlib.sha256((self.out/key).read_bytes()).hexdigest() for key in snapshot_map}
        self.write_json("config.json", {"snapshot_hashes": sha, "method": "hierarchical",
            "preprocessing_plan": {"schema": {"x": {"type": "numeric"}, "y": {"type": "numeric"}},
                                    "weights": {"x": 1, "y": 1}},
            "candidate_plan": {"configs": [{"linkage": "ward", "k": 2}],
                               "budget": {"seconds_per_fit": 8}}})
        self.write_json("stability_rerun.json", self.actual)
        self.prior_hash = {name: hashlib.sha256((self.out/name).read_bytes()).hexdigest() for name in snapshot_map}
    def tearDown(self):
        self.temp.cleanup()
    def write_json(self, name, data):
        (self.out / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    def execute(self):
        return subprocess.run([sys.executable, "reproduce.py", "--verify"], cwd=self.out,
                              text=True, capture_output=True, timeout=30)
    def test_failure_preserves_rerun_diagnostics_and_original_snapshots(self):
        result = self.execute()
        self.assertNotEqual(result.returncode, 0)
        state = json.loads((self.out/"reproduction_result.json").read_text())
        self.assertEqual(state["status"], "FAIL")
        self.assertEqual(state["candidate_index"], 0)
        self.assertTrue((self.out/state["comparison_file"]).exists())
        self.assertTrue((self.out/state["rerun_file"]).exists())
        self.assertEqual(json.loads((self.out/state["rerun_file"]).read_text()), self.actual)
        self.assertEqual(json.loads((self.out/state["comparison_file"]).read_text())["verdict"], "FAIL")
        self.assertEqual({name: hashlib.sha256((self.out/name).read_bytes()).hexdigest() for name in self.prior_hash}, self.prior_hash)
        self.assertTrue((self.out/"reproduction_events.jsonl").is_file())
    def test_matching_rerun_passes_and_stores_evidence(self):
        self.write_json("stability_rerun.json", self.original)
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((self.out/"reproduction_result.json").read_text())
        self.assertEqual(state["status"], "PASS")
        self.assertEqual(len(state["candidates"]), 1)
        audit = list((self.out/state["audit_dir"]).glob("candidate_00_comparison.json"))
        self.assertEqual(len(audit), 1)
        self.assertEqual(json.loads(audit[0].read_text())["verdict"], "PASS")
    def test_changed_scientific_snapshot_fails_without_new_fit(self):
        self.write_json("diagnostics.json", {"stability": [make_stability([make_run(0), make_run(1)])]})
        result = self.execute()
        self.assertNotEqual(result.returncode, 0)
        state = json.loads((self.out/"reproduction_result.json").read_text())
        self.assertEqual(state["status"], "ERROR")
        self.assertIn("Snapshot changed", state["error"])
        self.assertEqual(list((self.out/"reproduction_audit").rglob("candidate_*_rerun.json")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
