"""Read-only, actual-value disclosure for approved Stage 1 preprocessing.

This module does not estimate, modify, or refit preprocessing or clustering.
Its input consists exclusively of already-approved raw/model snapshots, the
approved plan, and the fitted preprocessing record preserved in the session.
"""
from __future__ import annotations

import json
import math

import pandas as pd


NUMERIC_TYPES = {"numeric", "count"}


def _number(value):
    if value is None:
        return None
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) else None


def _format(value):
    numeric = _number(value)
    if numeric is not None:
        return f"{numeric:.6g}"
    return "—" if value is None else str(value)


def _cell(value):
    return str(value).replace("|", "｜").replace("\n", " ").replace("\r", " ")


def _summary_stats(series):
    nums = pd.to_numeric(series, errors="coerce")
    if not nums.notna().any():
        return None, None
    return _number(nums.mean()), _number(nums.std(ddof=0))


def preprocessing_evidence_rows(raw: pd.DataFrame, model: pd.DataFrame,
                                 plan: dict, fitted: dict) -> list[dict]:
    """Produce traceable, snapshot-based rows for CSV and readable report.

    Must not silently infer a fitted parameter from an approved *proposal*.
    A missing or mismatched fitted record is a report integrity error.
    """
    if list(raw.columns) != list(model.columns) or len(raw) != len(model):
        raise ValueError("Preprocessing disclosure requires row-aligned, same-feature raw/model snapshots")
    selected = list(model.columns)
    if set(selected) != set(fitted) or any(c not in plan.get("schema", {}) for c in selected):
        raise ValueError("Approved fitted preprocessing does not cover every model feature")
    if any(c not in plan.get("weights", {}) for c in selected):
        raise ValueError("Approved preprocessing weights are incomplete")
    out = []
    for col in selected:
        params = fitted[col]
        if not isinstance(params, dict) or not {"missing", "transform", "scale", "center", "divisor"}.issubset(params):
            raise ValueError("Missing fitted preprocessing parameters for " + str(col))
        method = params["scale"]
        if method not in {"none", "standard", "robust"} or params["transform"] not in {"none", "log1p"}:
            raise ValueError("Unrecognized fitted preprocessing for " + str(col))
        if params["missing"] not in {"retain", "median", "mode", "constant"}:
            raise ValueError("Unrecognized missingness handling for " + str(col))
        if method != "none" and (_number(params["center"]) is None or
                                    _number(params["divisor"]) is None or _number(params["divisor"]) <= 0):
            raise ValueError("Missing/invalid fitted scaling values for " + str(col))
        kind = plan["schema"][col]["type"]
        if method != "none" and kind not in NUMERIC_TYPES:
            raise ValueError("Non-numeric feature unexpectedly scaled: " + str(col))
        actions = plan.get("actions", {}).get(col, {})
        if (actions.get("missing", "retain") != params["missing"] or
            actions.get("transform", "none") != params["transform"] or
            actions.get("scale", "none") != method):
            raise ValueError("Approved plan and fitted preprocessing disagree for " + str(col))
        if params["missing"] in {"median", "mode", "constant"} and params.get("fill") is None:
            raise ValueError("Missing fitted imputation value for " + str(col))
        if kind in NUMERIC_TYPES:
            raw_mean, raw_sd = _summary_stats(raw[col])
            model_mean, model_sd = _summary_stats(model[col])
        else:
            raw_mean = raw_sd = model_mean = model_sd = None
        mapping = actions.get("mapping")
        out.append({
            "feature": col, "statistical_type": kind,
            "raw_missing_n": int(raw[col].isna().sum()),
            "model_missing_n": int(model[col].isna().sum()),
            "missing_policy": params["missing"],
            "fitted_fill": params.get("fill"),
            "approved_mapping": json.dumps(mapping, ensure_ascii=False) if mapping is not None else None,
            "transform": params["transform"], "scale": method,
            "fitted_center": _number(params["center"]) if method != "none" else None,
            "fitted_divisor": _number(params["divisor"]) if method != "none" else None,
            "approved_weight": plan["weights"][col],
            "raw_mean": raw_mean, "raw_population_sd": raw_sd,
            "model_mean": model_mean, "model_population_sd": model_sd,
        })
    return out


def render_preprocessing_disclosure(raw: pd.DataFrame, model: pd.DataFrame,
                                    plan: dict, fitted: dict) -> str:
    """Explain the *executed* preprocessing, not a generic option list."""
    rows = preprocessing_evidence_rows(raw, model, plan, fitted)
    n = len(raw)
    scale_set = {r["scale"] for r in rows}
    lines = ["### 實際執行的前處理與參數", "",
             (f"本次研究對 **{n} 筆觀測、{len(rows)} 個已核准分群特徵**執行下列處理；"
              f"原始特徵快照與建模快照均有 {n} 筆，**沒有刪除觀測**。"
              "未參與分群的識別碼、事後分析與排除欄位不列入距離計算。"), "",
             "**執行順序：** 缺失值處理 →（如有）類別值對照 →（如有）`log1p` 數值轉換 →（如有）尺度標準化。"
             "本表的參數取自實際擬合後封存的 `fitted_preprocessing`，不是僅引用前處理提案。", ""]
    if "standard" in scale_set:
        lines.append("**Z-score 標準化：** `z = (x − μ) / σ`；`μ` 為缺失處理及其他數值轉換後的特徵平均數，"
                     "`σ` 為同一階段使用 **ddof=0（母體公式）** 計算的標準差。")
    if "robust" in scale_set:
        lines.append("**Robust scaling：** `z = (x − median) / IQR`；中心為缺失處理及其他數值轉換後的中位數，"
                     "`IQR = Q3 − Q1`。")
    if all(r["scale"] == "none" for r in rows):
        lines.append("**尺度設定：** 本次所有分群特徵均未進行標準化。")
    if any(r["transform"] == "log1p" for r in rows):
        lines.append("**數值轉換：** `log1p(x) = ln(1 + x)`，在尺度標準化之前執行。")
    lines += ["", "| 分群特徵 | 缺失處理（原始→建模） | 其他轉換／類別對照 | 尺度 | 距離權重 |",
              "|---|---|---|---|---:|"]
    miss_names = {"retain": "保留", "median": "中位數插補", "mode": "眾數插補", "constant": "指定常數插補"}
    scale_names = {"none": "無", "standard": "Z-score", "robust": "Robust（中位數／IQR）"}
    for r in rows:
        miss = miss_names[r["missing_policy"]]
        if r["missing_policy"] != "retain":
            miss += f"（實際填補值 {_format(r['fitted_fill'])}）"
        elif r["raw_missing_n"] == 0:
            miss += "（原始無缺失）"
        miss += f"；{r['raw_missing_n']}→{r['model_missing_n']}"
        changes = []
        if r["approved_mapping"] is not None:
            changes.append("類別對照（完整設定見 config.json／對照 CSV）")
        if r["transform"] == "log1p":
            changes.append("log1p")
        lines.append("| " + " | ".join(map(_cell, [f"`{r['feature']}`", miss,
            "、".join(changes) if changes else "無",scale_names[r["scale"]],
            _format(r["approved_weight"])])) + " |")
    numeric = [r for r in rows if r["statistical_type"] in NUMERIC_TYPES]
    if numeric:
        lines += ["", "**數值特徵的前後對照（已保存的真實觀測）**", "",
                  "| 分群特徵 | 原始平均數 | 原始母體標準差 | 擬合中心值 | 擬合除數 | 建模平均數 | 建模母體標準差 |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for r in numeric:
            lines.append("| " + " | ".join(map(_cell, [f"`{r['feature']}`",
                _format(r["raw_mean"]), _format(r["raw_population_sd"]),
                _format(r["fitted_center"]), _format(r["fitted_divisor"]),
                _format(r["model_mean"]), _format(r["model_population_sd"])])) + " |")
        lines += ["", "原始統計量取自**處理前快照**；擬合中心值與除數則由**缺失處理及數值轉換後**的資料估計。"
                  "若未使用尺度標準化，中心與除數標示為「—」，不代表重新估計了參數。"
                  "建模後標準差同樣使用 `ddof=0`，未標準化的變數不應預期為 1。", ""]
    if any(r["approved_mapping"] is not None for r in rows):
        lines += ["**已批准的類別對照設定：**", ""]
        for r in rows:
            if r["approved_mapping"] is not None:
                lines.append(f"- `{r['feature']}`：`{r['approved_mapping']}`")
        lines.append("")
    lines += ["**可重現性：** 完整核准設定與實際擬合參數存於 `config.json`；"
              "逐欄核對資料存於 `preprocessing_effect_summary.csv`，前後觀測資料分別存於 "
              "`raw_feature_snapshot.csv` 和 `model_feature_snapshot.csv`。"
              "這些描述不構成替代前處理方法的效能比較；修改設定仍須重新取得 Stage 1 授權。", ""]
    return "\n".join(lines) + "\n"
