"""Research outputs, raw-unit profiles and an honest Quarto fallback."""
from __future__ import annotations
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import numpy as np
import pandas as pd
from .core import clean, digest, file_hash, write_json
from .figures import eda_figures, result_figure, preview_assets


def profiles(raw, schema, labels):
    numeric, categorical = [], []
    groups = [("All observations", np.ones(len(raw), dtype=bool))] if labels is None else [
        ("Noise" if g == -1 else f"Cluster {g+1}", np.asarray(labels) == g) for g in sorted(set(labels))]
    for name, mask in groups:
        for c in raw:
            s = raw.loc[mask, c]
            if schema[c]["type"] in {"numeric", "count"}:
                a = pd.to_numeric(s, errors="coerce")
                numeric.append(clean({"group": name, "feature": c, "group_n": len(s),
                    "valid_n": int(a.count()), "missing_n": int(a.isna().sum()),
                    "mean": a.mean(), "median": a.median(), "sd": a.std(),
                    "q1": a.quantile(.25), "q3": a.quantile(.75)}))
            else:
                levels = schema[c].get("levels")
                counts = s.value_counts(dropna=False)
                ordered = levels if levels else [v for v in counts.index if not pd.isna(v)]
                for level in [*ordered, None]:
                    n = int(s.isna().sum()) if level is None else int((s == level).sum())
                    categorical.append({"group": name, "feature": c, "level": level,
                        "n": n, "denominator_all_in_group": len(s), "valid_denominator": int(s.count()),
                        "pct_all_in_group": 100*n/len(s) if len(s) else None})
    return numeric, categorical


def build_report(session, destination):
    from .core import METHODS
    if session.method() not in METHODS or any(r.get("method") not in METHODS for r in session.state["results"]):
        raise ValueError("Unsupported method in report; legacy authorizations cannot be converted")
    out = Path(destination)
    out.mkdir(parents=True, exist_ok=True)
    model, plan = session.model(), session.plan()
    selected_cols = list(model)
    schema = {c: plan["schema"][c] for c in selected_cols}
    raw = session.raw()[selected_cols].copy()
    results = session.state["results"]
    # Final selection comes from the approved, checked payload, never an
    # independently editable cache field (Session also checks their equality).
    index = session.gate.state["payloads"]["final"]["candidate_index"]
    final = None if index is None else results[index]
    # A single DBSCAN group or all-noise are valid outcomes without a supported partition.
    has_partition = final is not None and final["metrics"]["clusters"] >= 2
    labels = np.asarray(final["labels"]) if has_partition else None
    ids = [f"Row {i+1}" for i in range(len(raw))]
    raw.to_csv(out/"raw_feature_snapshot.csv", index=False)
    model.to_csv(out/"model_feature_snapshot.csv", index=False)
    write_json(out/"raw_feature_snapshot.json", raw.to_dict(orient="list"))
    write_json(out/"model_feature_snapshot.json", model.to_dict(orient="list"))
    if has_partition:
        pd.DataFrame({"row_id": ids, "cluster": ["Noise" if x == -1 else f"Cluster {x+1}" for x in labels]}).to_csv(out/"cluster_assignments.csv", index=False)
    candidates = [{"candidate_index": i, "row_id": ids[j],
                   "exploratory_cluster": "Noise" if label == -1 else f"Cluster {label+1}"}
                  for i, r in enumerate(results) for j, label in enumerate(r["labels"])]
    pd.DataFrame(candidates).to_csv(out/"candidate_assignments.csv", index=False)
    pd.DataFrame([{"candidate_index": i, **r["config"], **r["metrics"]} for i, r in enumerate(results)]).to_csv(out/"candidate_metrics.csv", index=False)
    numeric, categorical = profiles(raw, schema, labels)
    pd.DataFrame(numeric, columns=["group", "feature", "group_n", "valid_n", "missing_n", "mean", "median", "sd", "q1", "q3"]).to_csv(out/"numeric_profiles_raw_units.csv", index=False)
    pd.DataFrame(categorical, columns=["group", "feature", "level", "n", "denominator_all_in_group", "valid_denominator", "pct_all_in_group"]).to_csv(out/"categorical_profiles.csv", index=False)
    processed_profiles, _ = profiles(model, schema, labels)
    pd.DataFrame(processed_profiles).to_csv(out/"numeric_profiles_model_space.csv", index=False)
    details = []
    for i, r in enumerate(results):
        info = dict(r["info"])
        if "medoid_positions" in info:
            info["medoid_rows"] = [{"row_id": ids[j], "raw_features": clean(raw.iloc[j].to_dict()),
                                     "model_features": clean(model.iloc[j].to_dict())} for j in info["medoid_positions"]]
        if "centroids_weighted_model_space" in info:
            # Euclidean geometry uses sqrt(weights) on the approved model features.
            info["centroids_approved_model_space"] = (np.asarray(info["centroids_weighted_model_space"])/
                np.sqrt([plan["weights"][c] for c in model])).tolist()
        details.append({"candidate_index": i, "info": info, "warnings": r["warnings"],
                        "distance_metadata": r["distance_metadata"]})
    write_json(out/"model_details.json", details)
    write_json(out/"candidate_results.json", results)
    write_json(out/"diagnostics.json", session.state["diagnostics"])
    write_json(out/"sensitivity_variants.json", session.state.get("sensitivity", []))
    write_json(out/"decision_log.json", session.gate.state["events"])
    replay_plan = {**plan, "schema": schema}
    from . import __version__
    config = {"version": __version__, "method": session.method(), "preprocessing_plan": replay_plan,
        "fitted_preprocessing": session.state["fitted_preprocessing"], "candidate_plan": session.gate.state["payloads"]["candidates"],
        "final_index": index, "has_final_partition": has_partition,
        "selected_k": final["metrics"]["clusters"] if has_partition else None,
        "rationale": session.gate.state["payloads"]["final"]["rationale"],
        "selection_explanation": session.gate.state["payloads"]["final"]["selection_explanation"],
        "original_input_sha256": session.state["input_sha256"],
        "snapshot_hashes": {f: file_hash(out/f) for f in ["raw_feature_snapshot.json", "model_feature_snapshot.json", "candidate_results.json", "diagnostics.json"]},
        "privacy": "Source identifiers and supplementary labels omitted; positional row IDs only; feature data remain sensitive"}
    write_json(out/"config.json", config)
    versions = {"python": sys.version, "platform": platform.platform()}
    for name in ("numpy", "pandas", "scipy", "scikit-learn"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "NOT INSTALLED"
    write_json(out/"environment.json", versions)
    root = Path(__file__).resolve().parent.parent
    shutil.copytree(root/"clustering_native", out/"reproducibility"/"clustering_native",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    assets = Path(__file__).resolve().parent/"assets"
    shutil.copyfile(root/"scripts"/"reproduce.py" if (root/"scripts"/"reproduce.py").exists() else assets/"reproduce.py", out/"reproduce.py")
    shutil.copyfile(root/"requirements.txt" if (root/"requirements.txt").exists() else assets/"requirements.txt", out/"requirements.txt")
    shutil.copyfile(root/"references"/"LITERATURE_AUDIT.md" if (root/"references"/"LITERATURE_AUDIT.md").exists() else assets/"LITERATURE_AUDIT.md", out/"references.md")
    from .data import audit
    aliases = eda_figures(raw, audit(raw, schema), out/"figures")
    result_figure(results, out/"figures"/"candidate_quality.svg")
    density_source = session.directory/"eda_figures"/"stage2_density.svg"
    if density_source.is_file():
        shutil.copyfile(density_source, out/"figures"/"stage2_density.svg")
    # Reuse actual Stage 4 evidence; never silently recompute fits or decisions here.
    bound_evidence = session.state["diagnostics"].get("selection_evidence")
    if not bound_evidence:
        raise PermissionError("rc5 report requires actual Stage 4 selection evidence")
    source_evidence = session.directory/"selection_evidence"
    for filename, expected in bound_evidence["hashes"].items():
        if not (source_evidence/filename).is_file() or file_hash(source_evidence/filename) != expected:
            raise PermissionError("Stage 4 selection evidence changed; review and regenerate before final approval")
    shutil.copytree(source_evidence,out/"selection_evidence")
    for geometry in session.state.get('geometry_paths', []):
        source=Path(geometry)
        for extension in ('.png','.svg'):
            if source.with_suffix(extension).is_file(): shutil.copyfile(source.with_suffix(extension), out/'figures'/source.with_suffix(extension).name)
    write_json(out/'eda_handoff.json', session.state.get('eda_handoff', {}))
    preview_paths = sorted((out/"figures").glob("*.svg")) + sorted((out/"selection_evidence").glob("*.svg"))
    previews = preview_assets(preview_paths)
    write_json(out/"figure_previews.json", previews)
    # These are actual retained files only, never reconstructed console transcripts.
    log_names = ("execution_events.jsonl", "execution_stdout.log", "execution_stderr.log")
    retained_logs=[]
    for name in log_names:
        source=session.directory/name
        if source.is_file():
            shutil.copyfile(source, out/name);retained_logs.append(name)
    write_json(out/"execution_log_status.json", {"status":"RETAINED" if retained_logs else "NOT RECORDED",
        "files":retained_logs, "scope":"Original analysis logs only; no transcript reconstructed. Reproduction logs, when actually run, are separate."})
    counts = {"All observations": len(raw)} if labels is None else {
        "Noise" if int(g) == -1 else f"Cluster {int(g)+1}": int(np.sum(labels == g)) for g in sorted(set(labels))}
    body = "# 分群分析研究報告\n\n"
    body += f"方法：`{session.method()}`；觀測數：{len(raw)}；模型特徵數：{len(model.columns)}。\n\n"
    body += (f"最終候選：{index+1}（程式索引 {index}）；群數：{config['selected_k']}。\n\n" if has_partition else
             "**沒有獲核准的最終分群結構（no-final-model）**。不提供正式群組指派；候選指派僅供探索。\n\n")
    body += "<!-- RC6_CURRENT_STATUS -->目前階段：Stage 5，等待使用者最終交付確認。<!-- /RC6_CURRENT_STATUS -->\n\n"
    body += ("已批准研究決策：保留上述最終候選。\n\n" if has_partition else
             "已批准研究決策：不選定最終分群模型，保留候選結果作探索。\n\n")
    body += "歷史階段的原始決策理由完整保存在 config.json 的 rationale 與 decision_log.json；其中的待批准用語屬當時紀錄，不代表目前流程狀態。\n\n"
    body += "分群具探索性；品質指標、輪廓與穩定性均不證明自然群組存在，也不支持因果推論。使用相同特徵描述群間差異並非獨立驗證；不提供天真的後選 p 值。\n\n"
    body += "群組／觀測數：`" + json.dumps(counts, ensure_ascii=False) + "`。\n\n"
    body += "原始單位與有效 n 見 numeric_profiles_raw_units.csv；變換後描述另存 numeric_profiles_model_space.csv。類別與序位分布見 categorical_profiles.csv，百分比分母為群內全部觀測，另列有效分母。\n\n"
    body += "![Numeric quality](figures/eda_numeric.svg)\n\n上圖保留原始值與潛在極端值；各欄使用自己的垂直尺度，正式模型沿用已批准的前處理。\n\n"
    body += "![Category quality](figures/eda_categories.svg)\n\n上圖呈現眾數頻率與缺失比例；數值欄的 top 不是群組或類別比例。資料專屬 EDA 不等同群組存在的證據。\n\n"
    body += "圖內欄位代號：" + "；".join(f"{v} = {k}" for k, v in aliases.items()) + "。圖表最多呈現前八欄；完整統計保留於 CSV。\n\n"
    body += "![Candidate quality](figures/candidate_quality.svg)\n\n上圖以實際候選的輪廓值、非雜訊群數與雜訊比例呈現品質及涵蓋率；未定義值不畫成零，不設定綜合排名。\n\n"
    if density_source.is_file():
        body += "![Stage 2 neighbor distances](figures/stage2_density.svg)\n\n此圖沿用 Stage 2 已計算的近鄰距離，沒有重跑診斷。k 排除自身；沒有從圖中自動選取 eps 或宣稱自然群組。\n\n"
    body += "候選指標：\n\n" + "\n".join(f"- 候選 {i+1}：`{json.dumps(r['metrics'], ensure_ascii=False)}`；警告：`{r['warnings']}`" for i, r in enumerate(results)) + "\n\n"
    body += "WCSS 下降不足以選 K；DBSCAN 雜訊不強制分群，輪廓計算排除雜訊。Gower 不套用歐氏 CH/DB。搜尋邊界需要人工審查，不自動擴展。\n\n"
    body += "穩定性：common-ID subsampling ARI／max-Jaccard；詳見 diagnostics.json，包括失敗次數、抽樣 ID、前處理政策。沒有通用及格門檻，也不冒稱 Hennig bootstrap。\n\n"
    body += "Hopkins、VAT、Gap、完整 Hennig bootstrap：尚未通過專門驗證，不在本次分析中提供。\n\n"
    body += "模型細節保留於 model_details.json：K-means 平均中心、PAM 實際 medoid、階層樹、DBSCAN 核心／邊界／雜訊。\n\n"
    body += "資料治理：匯出僅保留已選特徵及內部觀測代號；輔助標籤沒有加入模型，也不聲稱已完成外部獨立驗證。特徵本身仍可能敏感，對外分享需另行決定。\n\n"
    body += "原始分析執行日誌狀態見 execution_log_status.json；未保存時明列 NOT RECORDED，不以後續重現日誌冒充原始逐字稿。figure_previews.json 僅記錄真實圖片可用性，不宣稱客戶端已內嵌顯示；介面不支援時應提供圖片附件。\n\n"
    body += "來源：references.md 保留交接套件的文獻定位紀錄；本報告不聲稱重新核對未提供的原文 PDF。\n\n"
    ev = json.loads((out/"selection_evidence"/"selection_evidence.json").read_text())
    explanation = config["selection_explanation"]
    body += "## 候選選擇的完整證據\n\n"
    body += "探索範圍理由：" + config["candidate_plan"]["search_rationale"] + "\n\n"
    body += "邊界限制：" + config["candidate_plan"]["boundary_limitations"] + "\n\n"
    body += "| 候選 | 完整參數 | 群數 | Silhouette | 有效n | ARI平均 | 失敗次數 |\n|---|---|---:|---:|---:|---:|---:|\n"
    for row in ev["candidate_comparison"]:
        fmt=lambda v: "NA" if v is None else str(round(v,6)) if isinstance(v,float) else str(v)
        body += "| " + " | ".join([str(row["candidate_index"]+1),json.dumps(row["config"],ensure_ascii=False),str(row["actual_nonnoise_groups"]),fmt(row["silhouette"]),str(row["silhouette_effective_n"]),fmt(row["stability_ari"]["mean"]),str(row["resample_failures"])]) + " |\n"
    body += "\n逐參數來源、有效觀測集合雜湊、品質、群大小及失敗／NA均保存在 selection_evidence/candidate_comparison.csv 與 selection_evidence.json。\n\n"
    for figure in sorted((out/"selection_evidence").glob("*.svg")):
        body += f"![{figure.stem}](selection_evidence/{figure.name})\n\n"
    body += "圖表以各自 .plot_data.json 的實際值繪製；Undefined不補零。群組大小包含DBSCAN雜訊，群別Jaccard不把雜訊當候選群。\n\n"
    body += "實際搜尋邊界檢查：`" + json.dumps(ev.get("boundary_analysis", {}),ensure_ascii=False) + "`。指標極值不是最終選擇；若偏好候選位於邊界，須揭露並考慮另批搜尋。\n\n"
    if index is not None:
        body += "最終候選的邊界參數：`" + json.dumps(ev.get("boundary_analysis",{}).get("candidate_boundary_parameters",{}).get(str(index),[]),ensure_ascii=False) + "`。\n\n"
    body += "最終選擇理由：" + explanation["chosen_reason"] + "\n\n"
    for candidate,reason in explanation["candidate_reasons"].items():
        body += f"- 候選 {int(candidate)+1} 保留／未選原因：{reason}\n"
    body += "\n診斷衝突與取捨：" + explanation["conflicts"] + "\n\n限制：" + explanation["limitations"] + "\n\n"
    body += "K-means初始化圖是已批准的額外單次重啟敏感性，不代表已記錄sklearn內部每一次n_init；WCSS遞減不足以選K。階層圖保留實際linkage，切分敏感性與重抽樣不同；合併高度跳躍不證明自然群。PAM以實際觀測內部Row ID識別medoid；Gower不套歐氏CH/DB。DBSCAN排除雜訊後的Silhouette可能比較不同觀測集合，不能單看分數選參數。\n\n"
    numeric_table=pd.DataFrame(numeric)
    if not numeric_table.empty:
        body += "## 原始尺度群組描述\n\n| 群組 | 特徵 | 群內n | 原始有效n | 平均 | 中位數 | SD |\n|---|---|---:|---:|---:|---:|---:|\n"
        for row in numeric:
            body += "| "+" | ".join(str(row[k]) for k in ["group","feature","group_n","valid_n","mean","median","sd"])+" |\n"
        body += "\n完整四分位數與缺失分母見numeric_profiles_raw_units.csv；以上僅描述，不是獨立外部驗證。\n\n"
    import re
    from .presentation import offline_html
    def png_reference(match):
        path = out/match[2]
        png=path.with_suffix('.png')
        if not png.is_file():
            raise RuntimeError('PNG report image unavailable: '+str(png)+'; retain SVG and disclose presentation limitation')
        from .presentation import image_content
        image_content(png)
        return '!['+match[1]+']('+png.relative_to(out).as_posix()+')'
    body = re.sub(r'!\[([^\]]*)\]\(([^)]+\.svg)\)', png_reference, body)
    if (out/'figures'/'eda_geometry.png').is_file():
        body += '\n![Observed feature geometry](figures/eda_geometry.png)\n\nPairwise display covers at most four selected numeric features; all features remain in the model. No projection proves K.\n'
    body += '\n固定參數重抽樣只衡量這些參數下的條件穩定性，不含重新選參數的不確定性；fixed_full_data_preprocessing 不涵蓋完整前處理估計變異。Gower 各子樣本仍重新估計 range。不同觀測集合的品質分數不可直接視為同一母體的排名。\n'
    (out/'analysis_offline.html').write_text(offline_html(body, out), encoding='utf-8')
    (out/"analysis.md").write_text(body + "Quarto 狀態見 render_status.json；Markdown 可直接閱讀。\n", encoding="utf-8")
    qmd = ('---\ntitle: "Clustering research report"\nformat: html\njupyter: python3\n---\n\n' + body +
        '\n```{python}\nfrom pathlib import Path\nimport subprocess, sys\n'
        'subprocess.run([sys.executable, "reproduce.py", "--verify"], check=True)\n'
        'print(Path("reproduction_result.json").read_text(encoding="utf-8"))\n```\n')
    (out/"analysis.qmd").write_text(qmd, encoding="utf-8")
    quarto = shutil.which("quarto")
    render = {"status": "MARKDOWN_FALLBACK", "rendered": False, "reason": "Quarto CLI not installed"}
    if quarto:
        try:
            run = subprocess.run([quarto, "render", "analysis.qmd"], cwd=out, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=600)
            (out/"quarto_render.log").write_text(run.stdout+run.stderr, encoding="utf-8")
            ok = run.returncode == 0 and (out/"analysis.html").exists()
            render = {"status": "RENDERED" if ok else "MARKDOWN_FALLBACK", "rendered": ok,
                      "exit_code": run.returncode, "reason": None if ok else "CLI render failed; see log"}
        except subprocess.TimeoutExpired:
            render["reason"] = "Quarto render timed out; Markdown fallback retained"
    write_json(out/"render_status.json", render)
    (out/"README.md").write_text("# 閱讀與重現\n\n直接閱讀 analysis.md；analysis.qmd 僅含 Python。\n"
        "reproduce.py --verify 是開發端驗收入口，會以已核准快照重新擬合並比較結果；一般使用者由助理代為執行，不需安裝 R。\n"
        "本機執行需要 requirements.txt 中的 Python 依賴；Quarto 缺席時僅宣稱 Markdown 備援。\n"
        "config.json 記錄輸入雜湊、參數與已核准研究決策；decision_log.json 保存實際確認。\n", encoding="utf-8")
    # Cross-file count and consistency checks before proposing delivery.
    if sum(counts.values()) != len(raw) or len(candidates) != len(raw)*len(results):
        raise AssertionError("Cross-file count mismatch")
    if has_partition and len(pd.read_csv(out/"cluster_assignments.csv")) != len(raw):
        raise AssertionError("Assignment count mismatch")
    from .presentation import validate_report_images
    validate_report_images(out)
    hashes = {p.relative_to(out).as_posix(): file_hash(p) for p in sorted(out.rglob("*"))
              if p.is_file() and "__pycache__" not in p.relative_to(out).parts and ".clustering_tmp" not in p.relative_to(out).parts}
    manifest = {"status": "AWAITING_USER_DELIVERY_CONFIRMATION", "has_final_partition": has_partition,
        "counts": counts, "render": render, "hashes": hashes, "cross_file_qa": "PASS"}
    write_json(out/"manifest.json", manifest)
    return manifest
