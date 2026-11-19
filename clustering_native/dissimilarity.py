"""Reference-derived numerical primitives for the Python Native candidate.

Stage orchestration lives in session.py. Inputs must be explicitly approved upstream.
Dependencies for these primitives: numpy and pandas.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from typing import Mapping, Any
import numpy as np
import pandas as pd
# sklearn metric imports are lazy; Gower/PAM run with NumPy/Pandas only.

VALID_TYPES = {"numeric", "count", "nominal", "ordinal", "binary_symmetric", "binary_asymmetric"}


def gower_dissimilarity(df: pd.DataFrame, schema: Mapping[str, Mapping[str, Any]],
                        weights: Mapping[str, float] | None = None):
    """Gower/Kaufman-Rousseeuw-inspired dissimilarity with explicit type and policy.

    Numeric: absolute difference / observed range. Ordinal: (rank-1)/(M-1) for
    EXPLICIT ordered levels (treats rank steps as equal by convention). Nominal
    and symmetric binary: 0/1 mismatch. Asymmetric binary: double absence is
    not comparable; double presence scores zero difference.
    Pairwise missing values are excluded from both numerator and denominator.
    Numeric constant columns are excluded globally, with a warning in metadata.
    If a pair has no comparable variables, its dissimilarity is NaN; caller MUST
    refuse to fit methods that need a complete dissimilarity matrix.
    """
    if len(df) < 2 or not schema:
        raise ValueError("At least two rows and one schema feature required")
    if df.columns.duplicated().any():
        raise ValueError("Duplicate column names forbidden")
    if any(c not in df.columns for c in schema):
        raise ValueError("Schema contains unknown feature names")
    if weights is not None and set(weights) != set(schema):
        raise ValueError("Weights must cover exactly the approved features")
    ws = {c: 1.0 if weights is None else float(weights[c]) for c in schema}
    if not all(np.isfinite(w) and w > 0 for w in ws.values()):
        raise ValueError("Weights must be positive finite values")
    n = len(df)
    numer = np.zeros((n, n), dtype=float)
    denom = np.zeros((n, n), dtype=float)
    omissions = []
    for name, spec in schema.items():
        kind = spec.get("type")
        if kind not in VALID_TYPES:
            raise ValueError(f"Unsupported or missing statistical type: {name}")
        s = df[name]
        valid = s.notna().to_numpy(dtype=bool)
        pair = np.logical_and(valid[:, None], valid[None, :])
        w = ws[name]
        if kind in ("numeric", "count"):
            arr = pd.to_numeric(s, errors="raise").to_numpy(dtype=float, na_value=np.nan)
            nonmissing = arr[valid]
            if not np.isfinite(nonmissing).all():
                raise ValueError(f"Nonfinite numeric values in {name}")
            if len(nonmissing) == 0:
                omissions.append((name, "all missing")); continue
            ran = float(nonmissing.max() - nonmissing.min())
            if ran == 0:
                omissions.append((name, "constant numeric feature")); continue
            unit = np.abs(arr[:, None] - arr[None, :]) / ran
        elif kind == "ordinal":
            levels = spec.get("levels")
            if not isinstance(levels, (list, tuple)) or len(levels) < 2 or len(set(levels)) != len(levels):
                raise ValueError(f"Ordinal {name} must declare >=2 distinct ordered levels")
            mapping = {v: idx / (len(levels)-1) for idx, v in enumerate(levels)}
            unknown = set(s.dropna().unique()) - set(mapping)
            if unknown:
                raise ValueError(f"Ordinal {name} contains undeclared levels: {unknown}")
            rank = s.map(mapping).to_numpy(dtype=float, na_value=np.nan)
            unit = np.abs(rank[:,None] - rank[None,:])
        elif kind in ("binary_symmetric", "binary_asymmetric"):
            positive = spec.get("positive", 1)
            negative = spec.get("negative", 0)
            if positive == negative:
                raise ValueError("Binary values must differ")
            vals = set(s.dropna().unique())
            if not vals.issubset({positive, negative}):
                raise ValueError(f"Unexpected binary levels in {name}: {vals}")
            binary = s.map({negative:0, positive:1}).to_numpy(dtype=float, na_value=np.nan)
            unit = (binary[:,None] != binary[None,:]).astype(float)
            if kind == "binary_asymmetric":
                pair &= ~(np.logical_and(binary[:,None] == 0, binary[None,:] == 0))
        else:
            a = s.astype("object").where(s.notna(), "__PAIRWISE_MISSING__").to_numpy()
            unit = (a[:,None] != a[None,:]).astype(float)
        numer += np.where(pair, unit, 0.0) * w
        denom += pair * w
    D = np.full((n,n), np.nan, dtype=float)
    np.divide(numer, denom, out=D, where=denom>0)
    np.fill_diagonal(D,0.0)
    return D, {"omitted_features": omissions, "feature_names": list(schema),
               "weights": ws, "num_no_comparison_pairs": int(np.triu(denom==0,1).sum())}


def validate_dissimilarity(D: np.ndarray):
    D = np.asarray(D, dtype=float)
    if D.ndim != 2 or D.shape[0] != D.shape[1] or D.shape[0]<2:
        raise ValueError("D must be a square 2+ dissimilarity matrix")
    if not np.isfinite(D).all():
        raise ValueError("D contains NaN/inf, e.g. pairs with no comparable variables")
    if not np.allclose(D,D.T,atol=1e-10,rtol=0):
        raise ValueError("D must be symmetric")
    if not np.allclose(np.diag(D),0,atol=1e-10):
        raise ValueError("D diagonal must be zero")
    if (D < 0).any():
        raise ValueError("D must be nonnegative")
    return D


@dataclass
class PAMResult:
    medoid_indices: np.ndarray
    labels: np.ndarray
    objective: float
    build_objective: float
    swaps: int
    trajectory: tuple[float, ...]


def pam_build_swap(D: np.ndarray, k:int, max_swaps:int=200, atol:float=1e-11) -> PAMResult:
    """Deterministic greedy BUILD + best-improvement SWAP, O(k*n^3) demo reference.

    Check 1-swap local optimality; no claim of global optimality. Not suitable for
    unlimited production data sizes; production must apply resource checks.
    """
    D = validate_dissimilarity(D)
    n=len(D)
    if not isinstance(k,int) or not 2<=k<n:
        raise ValueError("PAM candidate k must be an integer in [2,n-1]")
    if max_swaps<=0:
        raise ValueError("max_swaps must be positive")
    medoids=[int(np.argmin(D.sum(axis=1)))]
    near=D[:,medoids[0]].copy()
    for _ in range(k-1):
        options=[(float(np.minimum(near,D[:,j]).sum()),j) for j in range(n) if j not in medoids]
        chosen=min(options)[1]
        medoids.append(chosen)
        near=np.minimum(near,D[:,chosen])
    build_cost=float(near.sum())
    trace=[build_cost]
    for swap_idx in range(max_swaps+1):
        old=trace[-1]
        best_cost=old
        best_swap=None
        for pos in range(k):
            remaining=np.delete(medoids,pos)
            nearest=D[:,remaining].min(axis=1)
            for candidate in range(n):
                if candidate in medoids: continue
                new=float(np.minimum(nearest,D[:,candidate]).sum())
                if new < best_cost-atol:
                    best_cost=new
                    best_swap=(pos,candidate)
        if best_swap is None:
            M=np.array(medoids,dtype=int)
            labs=D[:,M].argmin(axis=1)
            # When zero-distance duplicate medoids tie, force each medoid to own itself.
            for cluster_idx, row_idx in enumerate(M):
                labs[row_idx]=cluster_idx
            if not all(np.bincount(labs,minlength=k)):
                raise AssertionError("Empty cluster detected")
            objective=float(D[np.arange(n),M[labs]].sum())
            if not np.isclose(objective,trace[-1],atol=1e-9):
                raise AssertionError("Assignment and objective inconsistent")
            return PAMResult(M,labs,objective,build_cost,len(trace)-1,tuple(trace))
        if swap_idx>=max_swaps:
            raise RuntimeError("SWAP did not converge before the approved iteration limit")
        medoids[best_swap[0]]=best_swap[1]
        trace.append(best_cost)
    raise RuntimeError("Unexpected SWAP exit")


def assert_no_improving_single_swap(D:np.ndarray, medoids:np.ndarray, tol=1e-9):
    D=validate_dissimilarity(D)
    k=len(medoids)
    best=D[:,medoids].min(axis=1).sum()
    for position in range(k):
        retained=np.delete(medoids,position)
        nearest=D[:,retained].min(axis=1)
        for new in range(len(D)):
            if new in medoids: continue
            trial=np.minimum(nearest,D[:,new]).sum()
            if trial < best-tol:
                return False
    return True


def silhouette_for_dissimilarity(D:np.ndarray, labels: np.ndarray):
    D=validate_dissimilarity(D)
    labels=np.asarray(labels)
    if len(labels)!=len(D):
        raise ValueError("Label length mismatch")
    num_clusters=len(set(labels))
    if not 2<=num_clusters<len(labels):
        return None
    # Exact precomputed-distance silhouette definition; singleton scores are 0.
    # Independent sklearn equivalence tests remain in the scientific suite.
    groups = [np.flatnonzero(labels == g) for g in np.unique(labels)]
    scores = np.zeros(len(labels), dtype=float)
    for i in range(len(labels)):
        own = next(ix for ix in groups if i in ix)
        if len(own) == 1:
            continue
        a = D[i, own].sum()/(len(own)-1)
        b = min(D[i, ix].mean() for ix in groups if i not in ix)
        divisor = max(a, b)
        scores[i] = (b-a)/divisor if divisor > 0 else 0.
    return float(scores.mean())


def aligned_ari(ids_a, labels_a, ids_b, labels_b):
    """ARI on SAME unique observation IDs; ID order need not match."""
    if not (len(ids_a)==len(labels_a) and len(ids_b)==len(labels_b)):
        raise ValueError("IDs and labels length mismatch")
    if len(set(ids_a))!=len(ids_a) or len(set(ids_b))!=len(ids_b):
        raise ValueError("Duplicate observation IDs; resolve repeated sampling IDs first")
    if set(ids_a)!=set(ids_b):
        raise ValueError("ARI partitions are not on identical observation sets")
    lookup=dict(zip(ids_b,labels_b))
    from collections import Counter
    from math import comb
    a, b = list(labels_a), [lookup[i] for i in ids_a]
    n = len(a)
    if n < 2:
        return 1.
    cells = Counter(zip(a, b))
    count_a, count_b = Counter(a), Counter(b)
    index = sum(comb(v, 2) for v in cells.values())
    sum_a = sum(comb(v, 2) for v in count_a.values())
    sum_b = sum(comb(v, 2) for v in count_b.values())
    total = comb(n, 2)
    expected = sum_a*sum_b/total
    maximum = (sum_a+sum_b)/2
    return float((index-expected)/(maximum-expected)) if maximum != expected else 1.


def ward_distance_guard(linkage: str, metric: str):
    if linkage == "ward" and metric != "euclidean":
        raise ValueError("Ward minimum-variance linkage requires Euclidean feature geometry")
    return True

