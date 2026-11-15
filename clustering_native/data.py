"""Conservative semantic audit and explicitly approved preprocessing.

No automatic row deletion, encoding, imputation, scaling or role promotion.
"""
from __future__ import annotations
import copy
import re
import numpy as np
import pandas as pd
from .core import clean
from .dissimilarity import VALID_TYPES

ROLES = {"feature", "id", "supplementary", "exclude", "uncertain"}


def audit(df, dictionary=None):
    if len(df) < 3 or not len(df.columns) or df.columns.duplicated().any():
        raise ValueError("Need >=3 observations and unique, nonempty columns")
    if not all(isinstance(c, str) and c for c in df.columns):
        raise ValueError("Column names must be nonempty strings")
    dictionary = dictionary or {}
    if set(dictionary) - set(df):
        raise ValueError("Dictionary contains unknown columns")
    columns, numeric, categories, outliers, conflicts = [], {}, {}, {}, []
    for c in df:
        s = df[c]
        v = s.dropna()
        n = len(v)
        role, kind, uncertainty = "feature", "uncertain", []
        evidence = {"n": len(s), "valid_n": n, "unique_n": int(v.nunique()),
                    "missing_n": int(s.isna().sum()), "missing_pct": float(s.isna().mean()*100)}
        if re.search(r"(^id$|_id$|^id_|identifier)", c, flags=re.I):
            kind, role = "id", "id"
        elif re.search(r"(label|target|outcome|class|diagnosis)", c, re.I):
            role = "supplementary"
            uncertainty.append("Potential external label; keep outside model")
        if role == "feature" and (pd.api.types.is_datetime64_any_dtype(s) or
                                    re.search(r"date|日期", c, re.I)):
            kind = "date"
        elif kind != "id":
            if pd.api.types.is_numeric_dtype(s):
                if n and set(v.unique()).issubset({0, 1}):
                    kind = "uncertain"
                    uncertainty.append("Binary symmetry requires semantic decision")
                elif pd.api.types.is_integer_dtype(s):
                    kind = "uncertain"
                    uncertainty.append("Integer may be count, code, ordinal or continuous")
                elif n >= 10 and v.nunique() <= 10 and (pd.to_numeric(v) % 1 == 0).all():
                    kind = "uncertain"
                    uncertainty.append("Low-support integral-valued float may be encoded category/ordinal")
                else:
                    kind = "numeric"
            elif kind != "date":
                kind = "nominal"
                uncertainty.append("Ordinal order cannot be inferred from category labels")
        if n == 0:
            uncertainty.append("All missing; exclude or provide explicit handling")
        elif v.nunique() == 1:
            uncertainty.append("Constant; no discriminatory numeric range")
        if v.nunique() == len(df) and kind not in {"numeric", "date", "id"}:
            uncertainty.append("High cardinality; possible identifier")
        spec = dictionary.get(c, {})
        kind, role = spec.get("type", kind), spec.get("role", role)
        if role not in ROLES or kind not in VALID_TYPES | {"uncertain", "date", "id"}:
            raise ValueError(f"Unknown dictionary type/role for {c}")
        errors = validate_column(s, {**spec, "type": kind}, strict=False)
        conflicts += [{"column": c, "issue": e} for e in errors]
        if kind in {"numeric", "count"}:
            num = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan)
            q1, q3 = num.quantile([.25, .75])
            iqr = q3-q1
            flags = ((num < q1-1.5*iqr) | (num > q3+1.5*iqr)).fillna(False)
            outliers[c] = {"n": int(flags.sum()), "row_positions": np.flatnonzero(flags).tolist(),
                           "interpretation": "Potential IQR flags; retained, not proof of error"}
            numeric[c] = clean({"valid_n": num.count(), "mean": num.mean(), "median": num.median(),
                "sd": num.std(), "iqr": iqr, "min": num.min(), "max": num.max(), "range": num.max()-num.min()})
        elif role not in {"id", "supplementary"}:
            counts = s.value_counts(dropna=False)
            categories[c] = [{"level": None if pd.isna(level) else clean(level), "n": int(count),
                              "denominator": len(df), "pct": float(count/len(df)*100)}
                             for level, count in counts.items()]
        columns.append({"column": c, "storage_dtype": str(s.dtype), "statistical_type": kind,
            "role": role, "evidence": evidence, "uncertainty": uncertainty,
            "user_override": bool(spec), "dictionary": copy.deepcopy(spec)})
    id_cols = [x["column"] for x in columns if x["role"] == "id"]
    feature_cols = [x["column"] for x in columns if x["role"] == "feature"]
    corr_cols = [x["column"] for x in columns if x["role"] == "feature" and
                 x["statistical_type"] in {"numeric", "count"}]
    correlations = df[corr_cols].apply(pd.to_numeric, errors="coerce").corr(method="spearman") if corr_cols else pd.DataFrame()
    proposals = []
    for x in columns:
        c = x["column"]
        if x["evidence"]["missing_n"]:
            proposals.append({"column": c, "issue": f"{x['evidence']['missing_n']}/{len(df)} missing",
                "necessity": "Complete numeric methods require a decision; Gower may compare available pairs",
                "risk": "Imputation changes distances; deletion changes target population",
                "alternatives": ["retain pairwise for Gower", "approve imputation", "exclude feature"]})
        if x["uncertainty"]:
            proposals.append({"column": c, "issue": x["uncertainty"],
                "necessity": "Confirm statistical type and role before modelling",
                "risk": "Numeric codes may create artificial geometry", "alternatives": ["declare schema", "exclude feature"]})
        if c in numeric:
            proposals.append({"column": c, "issue": numeric[c], "necessity": "Review range and IQR for intended distance",
                "risk": "Scaling changes feature influence; range sensitive to extremes",
                "alternatives": ["none", "standard", "robust", "log1p when nonnegative"]})
    return clean({"n": len(df), "columns": columns, "numeric": numeric, "categories": categories,
        "outliers": outliers, "conflicts": conflicts, "proposals": proposals,
        "duplicates": {"full_rows": int(df.duplicated().sum()),
            "id_rows": int(df.duplicated(subset=id_cols).sum()) if id_cols else None,
            "feature_rows": int(df.duplicated(subset=feature_cols).sum()) if feature_cols else None},
        "association": {"method": "Spearman, numeric/count features only; pairwise complete",
                        "matrix": correlations.to_dict()},
        "structure_conclusion": "資訊不足；EDA 並未證明自然群組存在"})


def validate_column(s, spec, strict=True):
    kind = spec.get("type")
    errors = []
    v = s.dropna()
    if kind in {"numeric", "count"}:
        num = pd.to_numeric(v, errors="coerce")
        if num.isna().any() or not np.isfinite(num.to_numpy(dtype=float)).all():
            errors.append("Non-numeric or nonfinite values conflict with declared numeric type")
        if kind == "count" and ((num < 0).any() or (num % 1 != 0).any()):
            errors.append("Counts must be nonnegative integers")
    if kind == "ordinal":
        levels = spec.get("levels", [])
        if len(levels) < 2 or len(set(levels)) != len(levels):
            errors.append("Ordinal requires explicit distinct ordered levels")
        elif not set(v).issubset(set(levels)):
            errors.append("Undeclared ordinal levels")
    if kind in {"binary_symmetric", "binary_asymmetric"}:
        pos, neg = spec.get("positive", 1), spec.get("negative", 0)
        if pos == neg or not set(v).issubset({pos, neg}):
            errors.append("Binary semantic levels conflict")
    if kind == "date" and pd.to_datetime(v, errors="coerce").isna().any():
        errors.append("Invalid dates require explicit correction or exclusion")
    if strict and errors:
        raise ValueError("; ".join(errors))
    return errors


def preprocess(raw, plan):
    """Plan defines *every* role/type, selected features and per-feature actions."""
    if set(plan) != {"schema", "actions", "weights"}:
        raise ValueError("Plan requires exactly schema, actions, weights")
    schema, actions, weights = plan["schema"], plan["actions"], plan["weights"]
    if set(schema) != set(raw.columns):
        raise ValueError("Declare type and role for every input column")
    selected = [c for c, s in schema.items() if s.get("role") == "feature"]
    if not selected or set(actions) != set(selected) or set(weights) != set(selected):
        raise ValueError("Actions and weights must cover exactly selected features")
    if not all(type(w) in (int, float) and np.isfinite(w) and w > 0 for w in weights.values()):
        raise ValueError("Weights must be positive finite numeric values")
    for c, spec in schema.items():
        if spec.get("role") not in ROLES:
            raise ValueError(f"Invalid role: {c}")
        if spec.get("type") not in VALID_TYPES | {"date", "id", "uncertain"}:
            raise ValueError(f"Invalid statistical type: {c}")
        if spec.get("role") == "feature":
            if spec.get("type") not in VALID_TYPES:
                raise ValueError(f"Unresolved/non-model statistical type: {c}")
            validate_column(raw[c], spec)
    # Identifiers are audited but never used as model features or row keys.
    # Internal positional IDs remain unique even when source IDs repeat legally.
    out = raw[selected].copy(deep=True)
    fitted = {}
    for c in selected:
        a = actions[c]
        if set(a) - {"missing", "fill", "mapping", "transform", "scale"}:
            raise ValueError(f"Unknown preprocessing action for {c}")
        kind = schema[c]["type"]
        missing = a.get("missing", "retain")
        if missing not in {"retain", "median", "mode", "constant"}:
            raise ValueError("Unsupported missingness policy")
        val = None
        if missing == "median":
            if kind not in {"numeric", "count"}:
                raise ValueError("Median imputation requires numeric/count")
            val = pd.to_numeric(out[c]).median()
        elif missing == "mode":
            mode = out[c].mode(dropna=True)
            if mode.empty:
                raise ValueError("All-missing mode cannot be estimated")
            val = mode.iloc[0]
        elif missing == "constant":
            if "fill" not in a or pd.isna(a["fill"]):
                raise ValueError("Explicit nonmissing fill value required")
            val = a["fill"]
        if missing != "retain":
            if pd.isna(val):
                raise ValueError("Imputation estimate is undefined")
            out[c] = out[c].fillna(val)
        if "mapping" in a:
            # JSON maps stringify numeric keys; pair-list mapping preserves types.
            pairs = a["mapping"]
            if not isinstance(pairs, list):
                raise ValueError("Mapping must be a list of [source,target] pairs")
            mapping = dict(pairs)
            if len(mapping) != len(pairs) or not set(out[c].dropna()).issubset(mapping):
                raise ValueError("Mapping must cover observed values exactly without duplicate keys")
            out[c] = out[c].map(mapping)
        transform, scale = a.get("transform", "none"), a.get("scale", "none")
        if transform not in {"none", "log1p"} or scale not in {"none", "standard", "robust"}:
            raise ValueError("Unknown transformation or scaling")
        if (transform != "none" or scale != "none") and kind not in {"numeric", "count"}:
            raise ValueError("Do not scale encoded categories or ordinal levels")
        if kind in {"numeric", "count"}:
            out[c] = pd.to_numeric(out[c], errors="raise").astype(float)
            if transform == "log1p":
                if (out[c].dropna() < 0).any():
                    raise ValueError("log1p policy requires nonnegative values")
                out[c] = np.log1p(out[c])
        center, divisor = 0., 1.
        if scale != "none":
            center = out[c].mean() if scale == "standard" else out[c].median()
            divisor = out[c].std(ddof=0) if scale == "standard" else out[c].quantile(.75)-out[c].quantile(.25)
            if not np.isfinite(divisor) or divisor <= 0:
                raise ValueError("Undefined/zero scale; explicitly revise preprocessing")
            out[c] = (out[c]-center)/divisor
        validate_column(out[c], {**schema[c], "type": "numeric" if kind == "count" and
                        (scale != "none" or transform != "none") else kind})
        fitted[c] = clean({"missing": missing, "fill": val, "transform": transform,
                           "scale": scale, "center": center, "divisor": divisor})
    return out, fitted


def method_assessment(model, plan, eda):
    from .suitability import assess
    return assess(model, plan, eda)["methods"]
