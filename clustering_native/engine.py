"""Four real estimators, compatible metrics and bounded subprocess execution.

Scientific imports are lazy. Missing dependencies cause an explicit error, never
an estimator substitution. No model pickle is loaded or emitted.
"""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import warnings
import queue
import threading
import time
from datetime import datetime, timezone
import uuid
import numpy as np
import pandas as pd
from .core import METHODS, budget_check, clean, write_json, WorkspaceTemp
from .dissimilarity import (gower_dissimilarity, validate_dissimilarity,
    pam_build_swap, ward_distance_guard, aligned_ari)
from .dissimilarity import silhouette_for_dissimilarity


def validate_config(method, config, n):
    if method not in METHODS:
        raise ValueError("Select exactly one supported method")
    common = {"metric"}
    allowed = {
        "kmeans": {"k", "init", "n_init", "algorithm", "random_state", "tol", "max_iter"},
        "hierarchical": {"k", "linkage"},
        "dbscan": {"eps", "min_samples"},
        "pam": {"k", "max_swaps"}}
    if set(config) != allowed[method] | common:
        raise ValueError(f"{method} config requires exactly {sorted(allowed[method] | common)}")
    metric = config["metric"]
    if metric not in {"euclidean", "manhattan", "gower"}:
        raise ValueError("Supported feature metrics: euclidean, manhattan, gower")
    if method == "kmeans" and metric != "euclidean":
        raise ValueError("K-means require Euclidean feature geometry")
    if method == "hierarchical":
        link = config["linkage"]
        if link not in {"ward", "single", "complete", "average"}:
            raise ValueError("Unsupported linkage")
        ward_distance_guard(link, metric)
    if "k" in config and (type(config["k"]) is not int or not 2 <= config["k"] < n):
        raise ValueError("k must be an integer between 2 and n-1")
    for k in ("n_init", "max_iter", "max_swaps", "min_samples"):
        if k in config and (type(config[k]) is not int or config[k] <= 0):
            raise ValueError(f"{k} requires a positive integer")
    for k in ("tol", "eps"):
        if k in config and (not np.isfinite(config[k]) or config[k] <= 0):
            raise ValueError(f"{k} must be positive finite")
    if "random_state" in config and (type(config["random_state"]) is not int or
                                    not 0 <= config["random_state"] < 2**32):
        raise ValueError("Explicit integer random_state required")
    if method == "kmeans" and (config["algorithm"] != "lloyd" or
                               config["init"] not in {"k-means++", "random"}):
        raise ValueError("Candidate implements Lloyd with explicit init, not Hartigan-Wong")


def geometry(df, schema, weights, metric, budget):
    budget_check(len(df), budget)
    if metric == "gower":
        D, metadata = gower_dissimilarity(df, schema, weights)
        return None, validate_dissimilarity(D), metadata
    if not all(s["type"] in {"numeric", "count"} for s in schema.values()):
        raise ValueError("Numeric geometry cannot use encoded nominal, ordinal or binary features")
    X = df.to_numpy(dtype=float)
    if not np.isfinite(X).all():
        raise ValueError("Missing/nonfinite numeric features; revise Stage 1 explicitly")
    # Positive weights apply to squared Euclidean or L1 contributions respectively.
    w = np.array([weights[c] for c in df], dtype=float)
    X = X * (np.sqrt(w) if metric == "euclidean" else w)
    D = np.zeros((len(X), len(X)), dtype=float)
    for i in range(len(X)-1):
        differences = X[i+1:]-X[i]
        distances = np.sqrt(np.sum(differences**2, axis=1)) if metric == "euclidean" else np.sum(np.abs(differences), axis=1)
        D[i, i+1:] = distances
        D[i+1:, i] = distances
    return X, validate_dissimilarity(D), {
        "weights": weights, "metric": metric, "weight_convention": "sqrt(w) Euclidean; w L1"}


def fit_one(df, schema, weights, method, config, budget):
    validate_config(method, config, len(df))
    X, D, metadata = geometry(df, schema, weights, config["metric"], budget)
    info, diagnostic_warnings = {}, []
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        if method == "kmeans":
            from sklearn.cluster import KMeans
            args = {k: v for k, v in config.items() if k not in {"k", "metric"}}
            m = KMeans(n_clusters=config["k"], **args).fit(X)
            labels = m.labels_
            info = {"solver": "Lloyd", "wcss": m.inertia_, "centroids_weighted_model_space": m.cluster_centers_,
                    "n_iter": m.n_iter_, "converged": m.n_iter_ < config["max_iter"]}
            if len(set(labels)) != config["k"]:
                raise ValueError("K-means returned fewer distinct clusters than approved K")
            if m.n_iter_ >= config["max_iter"]:
                diagnostic_warnings.append("Iteration limit reached; convergence not established")
        elif method == "hierarchical":
            from scipy.cluster.hierarchy import linkage, cut_tree
            from scipy.spatial.distance import squareform
            Z = linkage(X, method="ward", metric="euclidean") if config["linkage"] == "ward" else \
                linkage(squareform(D, checks=True), method=config["linkage"])
            labels = cut_tree(Z, n_clusters=[config["k"]]).ravel()
            info = {"linkage_matrix": Z, "cut_k": config["k"], "converged": True}
        elif method == "dbscan":
            from sklearn.cluster import DBSCAN
            m = DBSCAN(eps=config["eps"], min_samples=config["min_samples"], metric="precomputed").fit(D)
            labels = m.labels_
            noise = labels == -1
            core = np.zeros(len(df), dtype=bool)
            core[m.core_sample_indices_] = True
            info = {"core_n": int(core.sum()), "border_n": int((~core & ~noise).sum()),
                    "noise_n": int(noise.sum()), "noise_fraction": float(noise.mean()),
                    "point_type": np.where(noise, "noise", np.where(core, "core", "border")),
                    "noise_policy": "exclude noise from silhouette; noise retained in counts and stability", "converged": True}
        else:
            m = pam_build_swap(D, config["k"], max_swaps=config["max_swaps"])
            labels = m.labels
            info = {"medoid_positions": m.medoid_indices, "objective": m.objective,
                    "build_objective": m.build_objective, "swaps": m.swaps, "trajectory": m.trajectory,
                    "optimality": "1-swap local optimum, not guaranteed global", "converged": True}
        diagnostic_warnings += [f"{w.category.__name__}: {w.message}" for w in captured]
    labels = np.asarray(labels, dtype=int)
    use = labels != -1 if method == "dbscan" else np.ones(len(labels), dtype=bool)
    groups = len(set(labels[use]))
    metrics = {"clusters": groups, "silhouette": None,
               "silhouette_policy": "noise excluded" if method == "dbscan" else "all observations"}
    if 2 <= groups < int(use.sum()):
        metrics["silhouette"] = silhouette_for_dissimilarity(D[np.ix_(use, use)], labels[use])
    else:
        metrics["silhouette_reason"] = "Undefined: fewer than two clusters or all singleton observations"
    if method == "kmeans":
        metrics["wcss"] = info["wcss"]
    return clean({"method": method, "config": config, "labels": labels, "metrics": metrics,
                  "info": info, "distance_metadata": metadata, "warnings": diagnostic_warnings})


def bounded_fit(df, schema, weights, method, config, budget):
    """A separate process makes approved wall-clock timeout enforceable."""
    budget_check(len(df), budget, pam=method == "pam")
    validate_config(method, config, len(df))
    with WorkspaceTemp(prefix="clustering-fit-") as tmp:
        inp, out = Path(tmp)/"request.json", Path(tmp)/"result.json"
        write_json(inp, {"data": df.to_dict(orient="list"), "schema": schema,
            "weights": weights, "method": method, "config": config, "budget": budget})
        env = os.environ.copy()
        root = str(Path(__file__).resolve().parent.parent)
        env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
        env["OMP_NUM_THREADS"] = "1"
        try:
            p = subprocess.run([sys.executable, "-m", "clustering_native.worker", str(inp), str(out)],
                capture_output=True, text=True, encoding="utf-8", env=env,
                timeout=budget["seconds_per_fit"], check=False)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("Approved fit time exceeded; candidate terminated, no substitution") from exc
        if not out.exists():
            raise RuntimeError(f"Fit worker failed (exit {p.returncode}): {p.stderr[-2000:]}")
        result = json.loads(out.read_text(encoding="utf-8"))
        if "error" in result:
            raise RuntimeError(result["error"])
        if p.returncode != 0:
            raise RuntimeError("Worker returned nonzero status")
        return result



class StabilityFitBatch:
    """One supervised child for a candidate's entire approved subsampling batch.

    Calls still have the exact per-fit wall-clock cap. The first call includes
    child startup; later calls reuse loaded libraries. A timed-out process is
    killed and never reused; the next *scheduled* repeat may start a new child,
    but the failed repeat is never retried or substituted.

    Timing telemetry is saved separately from the scientific stability object
    to avoid introducing nondeterministic wall times into SHA-256 verification.
    """
    def __init__(self, budget, audit_path=None, candidate_index=None):
        self.budget = budget
        self.audit_path = Path(audit_path) if audit_path is not None else None
        self.candidate_index = candidate_index
        self.proc = None
        self.stdout_queue = None
        self.reader = None
        self.workspace = None
        self.temp = None
        self.stderr_handle = None
        self.launch_count = 0

    def __enter__(self):
        self.temp = WorkspaceTemp(prefix="clustering-stability-batch-")
        self.workspace = Path(self.temp.__enter__())
        return self

    def _log(self, **payload):
        if self.audit_path is None:
            return
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        event = {"event": "stability_fit_runtime", "recorded_utc": datetime.now(timezone.utc).isoformat(),
                 "candidate_index": self.candidate_index, "per_fit_cap_seconds": self.budget["seconds_per_fit"],
                 **payload}
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")

    def _reader(self, process, output_queue):
        try:
            for line in process.stdout:
                output_queue.put(line)
        finally:
            output_queue.put(None)

    def _spawn(self):
        root = str(Path(__file__).resolve().parent.parent)
        env = os.environ.copy()
        env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
        env["OMP_NUM_THREADS"] = "1"
        stderr_path = self.workspace / f"worker_{self.launch_count}.stderr.log"
        self.stderr_handle = stderr_path.open("w", encoding="utf-8")
        self.proc = subprocess.Popen([sys.executable, "-m", "clustering_native.batch_worker"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr_handle,
            text=True, encoding="utf-8", env=env, bufsize=1)
        self.stdout_queue = queue.Queue()
        self.reader = threading.Thread(target=self._reader,
                                       args=(self.proc, self.stdout_queue), daemon=True)
        self.reader.start()
        self.launch_count += 1

    def _stop(self):
        p = self.proc
        if p is not None:
            try:
                if p.poll() is None:
                    p.kill()
                p.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                pass
            for pipe in (p.stdin, p.stdout):
                if pipe:
                    try: pipe.close()
                    except OSError: pass
        if self.reader is not None:
            self.reader.join(timeout=2)
        if self.stderr_handle is not None:
            self.stderr_handle.close()
        self.proc = None
        self.reader = None
        self.stderr_handle = None
        self.stdout_queue = None

    def fit(self, df, schema, weights, method, config, *, repeat=None):
        budget_check(len(df), self.budget, pam=method == "pam")
        validate_config(method, config, len(df))
        started = time.monotonic()
        job_id = uuid.uuid4().hex
        request = self.workspace / f"{job_id}.request.json"
        output = self.workspace / f"{job_id}.result.json"
        phase = "serialize"
        worker_startup_seconds = 0.0
        reused_worker = self.proc is not None and self.proc.poll() is None
        try:
            write_json(request, {"data": df.to_dict(orient="list"), "schema": schema,
                "weights": weights, "method": method, "config": config, "budget": self.budget})
            if not reused_worker:
                self._stop()
                phase = "startup"
                worker_start = time.monotonic()
                self._spawn()
                remaining = float(self.budget["seconds_per_fit"]) - (time.monotonic() - started)
                if remaining <= 0:
                    raise queue.Empty()
                ready_line = self.stdout_queue.get(timeout=remaining)
                if ready_line is None or json.loads(ready_line).get("status") != "READY":
                    raise RuntimeError("Fit worker did not complete startup handshake")
                worker_startup_seconds = time.monotonic() - worker_start
            phase = "request"
            command = {"command": "fit", "input": str(request), "output": str(output), "job_id": job_id}
            self.proc.stdin.write(json.dumps(command, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
            phase = "response"
            remaining = float(self.budget["seconds_per_fit"]) - (time.monotonic() - started)
            if remaining <= 0:
                raise queue.Empty()
            reply_line = self.stdout_queue.get(timeout=remaining)
            if reply_line is None:
                raise RuntimeError("Persistent fit worker ended unexpectedly")
            reply = json.loads(reply_line)
            if reply.get("job_id") != job_id:
                raise RuntimeError("Fit-worker job ID mismatch; refusing stale response")
            if not reply.get("ok"):
                raise RuntimeError(reply.get("error", "Unknown fit-worker error"))
            if not output.is_file():
                raise RuntimeError("Fit-worker acknowledged without an output file")
            phase = "read_result"
            result = json.loads(output.read_text(encoding="utf-8"))
            if "error" in result:
                raise RuntimeError(result["error"])
            elapsed = time.monotonic() - started
            if elapsed > self.budget["seconds_per_fit"]:
                raise TimeoutError("Approved fit time exceeded; candidate terminated, no substitution")
            self._log(repeat=repeat, status="SUCCESS", reused_worker=reused_worker,
                      elapsed_seconds=elapsed, worker_startup_seconds=worker_startup_seconds,
                      worker_compute_seconds=reply.get("compute_seconds"),
                      worker_write_seconds=reply.get("write_seconds"), launch_count=self.launch_count)
            return result
        except (queue.Empty, TimeoutError) as exc:
            elapsed = time.monotonic() - started
            self._log(repeat=repeat, status="TIMEOUT", reused_worker=reused_worker,
                      elapsed_seconds=elapsed, phase_at_timeout=phase,
                      worker_startup_seconds=worker_startup_seconds,
                      launch_count=self.launch_count)
            self._stop()
            raise TimeoutError("Approved fit time exceeded; candidate terminated, no substitution") from exc
        except Exception as exc:
            self._log(repeat=repeat, status="ERROR", reused_worker=reused_worker,
                      elapsed_seconds=time.monotonic()-started, failure_type=type(exc).__name__,
                      phase_at_failure=phase, launch_count=self.launch_count)
            self._stop()
            raise
        finally:
            for path in (request, output):
                try: path.unlink(missing_ok=True)
                except OSError: pass

    def __exit__(self, *args):
        try:
            self._stop()
        finally:
            if self.temp is not None:
                self.temp.__exit__(*args)


def density_diagnostic(df, schema, weights, metric, min_samples, budget):
    if type(min_samples) is not int or not 2 <= min_samples <= len(df):
        raise ValueError("kNN diagnostic min_samples must be in [2,n]")
    _, D, _ = geometry(df, schema, weights, metric, budget)
    # Includes self distance, matching sklearn min_samples convention.
    knn = np.sort(D, axis=1)[:, min_samples-1]
    upper = D[np.triu_indices(len(D), 1)]
    return clean({"min_samples_including_self": min_samples,
                  "sorted_neighbor_distances": np.sort(knn),
                  "distance_quantiles": np.quantile(upper, [0, .25, .5, .75, 1]),
                  "interpretation": "Descriptive parameter evidence only; no universal eps or natural-cluster threshold"})


def stability(raw, model, plan, method, result, budget, fraction, repeats, seed, policy, *,
              audit_path=None, candidate_index=None):
    """Subsample observations and evaluate conditional partition stability by ARI.

    ARI compares labels only on the common sampled observation identifiers;
    DBSCAN noise remains a label. A failed resample is tracked separately.
    """
    from .data import preprocess
    if not 0 < fraction < 1 or type(repeats) is not int or repeats < 2:
        raise ValueError("Require 0<fraction<1 and at least two repeats")
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("Explicit valid subsampling seed required")
    if policy not in {"fixed_full_data_preprocessing", "refit_preprocessing"}:
        raise ValueError("Declare fixed or refit preprocessing")
    n = len(model)
    size = int(np.floor(n*fraction))
    if size < 3:
        raise ValueError("Subsample too small")
    schema = {c: plan["schema"][c] for c in model}
    labels = np.array(result["labels"])
    rng = np.random.default_rng(seed)
    rows = []
    with StabilityFitBatch(budget, audit_path=audit_path, candidate_index=candidate_index) as batch:
        for rep in range(repeats):
            ix = np.sort(rng.choice(n, size, replace=False))
            data = model.iloc[ix].copy() if policy == "fixed_full_data_preprocessing" else preprocess(raw.iloc[ix], plan)[0]
            try:
                fitted = batch.fit(data, schema, plan["weights"], method,
                                   copy.deepcopy(result["config"]), repeat=rep)
                new = fitted["labels"]
                ari = aligned_ari(ix.tolist(), labels[ix].tolist(), ix.tolist(), new)
                rows.append({"repeat": rep, "row_positions": ix.tolist(), "ari": ari,
                             "warnings": fitted["warnings"], "error": None})
            except (ValueError, RuntimeError, TimeoutError, MemoryError) as exc:
                rows.append({"repeat": rep, "row_positions": ix.tolist(), "ari": None,
                             "error": f"{type(exc).__name__}: {exc}"})
    return clean({"name": "common-ID subsampling ARI",
        "fraction": fraction, "repeats": repeats, "seed": seed, "preprocessing_policy": policy,
        "gower_range_policy": "Re-estimated on each subsample, including fixed transformed feature data",
        "noise_policy": "ARI retains noise as a label; all stability comparisons align common sampled IDs",
        "disappeared_cluster_policy": "null if original group absent on eligible common IDs",
        "pass_threshold": None, "runs": rows, "failures": sum(r["error"] is not None for r in rows)})

