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
    original_raw=session.raw()
    raw = original_raw[selected_cols].copy()
    approved_roles=session.state.get('approved_feature_roles') if session.gate.state.get('role_gate_required') else None
    supplementary_cols=([c for c,role in approved_roles['roles'].items() if role=='supplementary']
                        if approved_roles else [])
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
    if supplementary_cols:
        supplement=original_raw[supplementary_cols].reset_index(drop=True).copy()
        supplement.insert(0,'cluster',[('Noise' if int(x)==-1 else f'Cluster {int(x)+1}') for x in labels]
                          if labels is not None else ['Unassigned']*len(supplement))
        supplement.insert(0,'row_id',ids)
        supplement.to_csv(out/'supplementary_values_by_cluster.csv',index=False)
        write_json(out/'approved_feature_roles.json',approved_roles)
    candidates = [{"candidate_index": i, "row_id": ids[j],
                   "exploratory_cluster": "Noise" if label == -1 else f"Cluster {label+1}"}
                  for i, r in enumerate(results) for j, label in enumerate(r["labels"])]
    pd.DataFrame(candidates).to_csv(out/"candidate_assignments.csv", index=False)
    pd.DataFrame([{"candidate_index": i, **r["config"], **{k:v for k,v in r["metrics"].items()
                 if k not in {"calinski_harabasz","davies_bouldin"}}} for i,r in enumerate(results)]).to_csv(out/"candidate_metrics.csv", index=False)
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
    # The authoritative audit remains in session.json.  Research artifacts
    # deliberately omit live authorization secrets and expiry metadata.
    from .privacy import public_output
    write_json(out/"decision_log.json", public_output(session.gate.state["events"]))
    replay_plan = {**plan, "schema": schema}
    from . import __version__
    config = {"version": __version__, "method": session.method(),
        "workflow": ("stage3_plan_stage4_auto_diagnostics" if session.gate.state.get('stage4_auto_diagnostics',False)
                     else "stage3_plan_stage4_execution" if session.gate.state.get('stage4_candidate_execution', False)
                     else "legacy_stage3_execution_stage4_diagnostics"),
        "preprocessing_plan": replay_plan,
        "fitted_preprocessing": session.state["fitted_preprocessing"], "candidate_plan": session.gate.state["payloads"]["candidates"],
        "final_index": index, "has_final_partition": has_partition,
        "selected_k": final["metrics"]["clusters"] if has_partition else None,
        "rationale": session.gate.state["payloads"]["final"]["rationale"],
        "selection_explanation": session.gate.state["payloads"]["final"]["selection_explanation"],
        "original_input_sha256": session.state["input_sha256"],
        "snapshot_hashes": {f: file_hash(out/f) for f in ["raw_feature_snapshot.json", "model_feature_snapshot.json", "candidate_results.json", "diagnostics.json"]},
        "privacy": "Source identifiers omitted; role-approved supplementary values are disclosed only for new gated studies; positional row IDs; feature data remain sensitive"}
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
    from .report_references import write_study_references
    write_study_references(out/"references.md", session.method(), config["candidate_plan"].get("planned_metric_evidence"))
    from .data import audit
    aliases = eda_figures(raw, audit(raw, schema), out/"figures")
    result_figure(results, out/"figures"/"candidate_quality.svg")
    if has_partition:
        source=session.directory/'stage4_final_evidence'/'stage4_selected_partition.svg'
        if source.is_file():
            if (file_hash(source)!=session.state.get('stage4_selected_partition_hash') or
                digest(final['labels'])!=session.state.get('stage4_selected_partition_source') or
                file_hash(source.with_suffix('.png'))!=session.state.get('stage4_selected_partition_png_hash')):
                raise PermissionError('Approved Stage 4 selected partition evidence is not intact')
            for ext in ('.svg','.png'):
                shutil.copyfile(source.with_suffix(ext),out/'figures'/source.with_suffix(ext).name)
        else:
            # An R4D legacy checkpoint may not have a Stage 4 final image;
            # derive exactly from its approved saved labels, without fitting.
            from .figures import selected_partition_figure
            selected_partition_figure(model, final, out/'figures'/'stage4_selected_partition.svg')
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
        source=session.evidence_path(geometry)
        for extension in ('.png','.svg'):
            if source.with_suffix(extension).is_file(): shutil.copyfile(source.with_suffix(extension), out/'figures'/source.with_suffix(extension).name)
    write_json(out/'eda_handoff.json', session.state.get('eda_handoff', {}))
    preview_paths = sorted((out/"figures").glob("*.svg")) + sorted((out/"selection_evidence").glob("*.svg"))
    previews = preview_assets(preview_paths)
    write_json(out/"figure_previews.json", previews)
    # These are actual retained files only, never reconstructed console transcripts.
    log_names = ("execution_events.jsonl", "execution_stdout.log", "execution_stderr.log", "fit_runtime_events.jsonl")
    retained_logs=[]
    for name in log_names:
        source=session.directory/name
        if source.is_file():
            shutil.copyfile(source, out/name);retained_logs.append(name)
    write_json(out/"execution_log_status.json", {"status":"RETAINED" if retained_logs else "NOT RECORDED",
        "files":retained_logs, "scope":"Original analysis logs only; no transcript reconstructed. Reproduction logs, when actually run, are separate."})
    counts = {"All observations": len(raw)} if labels is None else {
        "Noise" if int(g) == -1 else f"Cluster {int(g)+1}": int(np.sum(labels == g)) for g in sorted(set(labels))}
    from .education import study_disclosure
    from .report_code import stage_block
    from .report_explanations import (
        preprocessing_findings, dominant_feature_findings, selection_warnings,
        descriptive_preprocessing_sensitivity, render_metric_contrast,
        render_approved_linkage_comparison, render_approved_distance_comparison,
        render_cluster_profiles)
    from .planning import interpret_distance_linkage
    from .report_explanations import actual_metric_contrast
    plan_scope=config['candidate_plan']
    chosen_config=results[index]['config'] if index is not None else results[0]['config']
    contrast=actual_metric_contrast(results,session.state['diagnostics']['stability'])
    evidence=json.loads((out/'selection_evidence'/'selection_evidence.json').read_text(encoding='utf-8'))
    search_configs=plan_scope['configs']
    fmt=lambda v:'NA' if v is None else f'{float(v):.4f}'
    body='# 分群分析研究報告\n\n'
    body += '## 研究摘要\n\n'
    body += f'本研究包含 {len(raw)} 筆觀測與 {len(model.columns)} 個實際分群特徵；'
    if has_partition:
        chosen_groups=config['selected_k']
        display_name='K-medoids（PAM 演算法）' if session.method()=='pam' else session.method()
        body += f'已核准的模型為 **{display_name}**，最後形成 **{chosen_groups} 群**。' 
        body += '選群結論僅適用於已測試的參數與資料表示，不代表全域最佳群數。\n\n'
    else:
        body += '本輪未核准可解釋的最終分群模型，僅保存候選研究證據。\n\n'
    body += '<!-- RC6_CURRENT_STATUS -->目前階段：Stage 5，等待使用者最終交付確認。<!-- /RC6_CURRENT_STATUS -->\n\n'
    body += '## Stage 1 — 資料診斷與前處理\n\n'
    if approved_roles:
        body += '### 已核准的研究問題與變數角色\n\n'
        body += '**研究目的：** '+(approved_roles.get('research_question') or '通用探索性分群；未指定額外研究假說')+'\n\n'
        body += '| 原始變數 | 已核准角色 |\n|---|---|\n'
        display={'feature':'分群特徵','supplementary':'事後分析（不參與分群）',
                 'id':'識別碼','exclude':'排除'}
        for name,role in approved_roles['roles'].items():
            body += f'| `{name}` | {display[role]} |\n'
        body += '\n本表在獨立 Stage 1B 授權後確定；事後分析欄位不參與分群距離或選 K。\n\n'
    # Read only the approved fitted settings and archived observations.
    from .preprocessing_disclosure import preprocessing_evidence_rows, render_preprocessing_disclosure
    preprocessing_rows = preprocessing_evidence_rows(raw, model, plan, session.state["fitted_preprocessing"])
    pd.DataFrame(preprocessing_rows).to_csv(out/"preprocessing_effect_summary.csv", index=False)
    body += render_preprocessing_disclosure(raw, model, plan, session.state["fitted_preprocessing"])
    body += preprocessing_findings(raw,model,plan)
    body += descriptive_preprocessing_sensitivity(raw,model,plan)
    body += '本階段檢查資料缺失、極端值與類別分布，並沿用已批准的特徵及處理方案。\n\n'
    body += '![Numeric quality](figures/eda_numeric.svg)\n\n'
    body += '![Category quality](figures/eda_categories.svg)\n\n'
    if (out/'figures'/'eda_geometry.png').is_file():
        body += '![Observed feature geometry](figures/eda_geometry.svg)\n\n'
    body += '完整原始單位、有效樣本數與類別比例保留於 numeric_profiles_raw_units.csv 和 categorical_profiles.csv。\n\n'
    body += stage_block(1)
    body += '## Stage 2 — 分群方法、距離與合併準則\n\n'
    from .method_rationale import render_stage2_method_decision
    body += render_stage2_method_decision(session.state.get('assessment', {}), session.method())
    body += study_disclosure(session.method(),search_configs,plan_scope.get('planned_metric_evidence'))+'\n'
    reasons=interpret_distance_linkage(session,chosen_config['metric'],session.method(),chosen_config.get('linkage'))
    body += '**本次距離選擇理由：** '+reasons['metric']+'\n\n'
    if chosen_config['metric']=='gower':
        weights={c:plan['weights'][c] for c in model}
        body += ('**Gower 記號與實際權重：** `w_k` 為每個特徵的權重；'
                 '`δ_ijk` 為兩筆觀測在第 k 個特徵的差異；'
                 '`O_ij` 為兩筆觀測共同可比較的特徵集合。'
                 '數值差異以全距標準化，名目類別相同為 0、不同為 1。'
                 + ('本次所有 '+str(len(weights))+' 個分群特徵的 `w_k` 均為 **1**（等權重）。'
                    if all(float(v)==1 for v in weights.values()) else
                    '本次實際核准權重：'+', '.join(f'`{c}`={v}' for c,v in weights.items())+'。')
                 +'等權重不代表各特徵對結果的實際影響相同。\n\n')
    if session.method()=='hierarchical':
        body += '**本次 Linkage（群組合併準則）：** '+reasons['linkage']+'\n\n'
    # Geometry is already summarized in the method-choice rationale; avoid duplication.

    density_source=session.directory/'eda_figures'/'stage2_density.svg'
    if density_source.is_file():
        body += '![Stage 2 neighbor distances](figures/stage2_density.svg)\n\n'
    body += stage_block(2)
    body += '## Stage 3 — 候選參數規劃與批准\n\n'
    body += f'本次在 Stage 3 核准的候選設定共 **{len(results)} 組**；此階段僅規劃參數、範圍、診斷預算與授權，不使用模型執行結果決定群數。候選由 Stage 1 EDA 線索、資料特性及計算預算形成探索計畫。'
    visual=plan_scope.get('eda_context',{}).get('visual',{})
    if visual.get('status')=='OPERATOR_VISUAL_REVIEW_RECORDED':
        geometry_names={'nonconvex':'非凸形狀','curved':'彎曲走向',
                        'unequal_density':'密度不均','isolated_regions':'孤立區域',
                        'coarse_fine_structure':'粗細階層結構'}
        shown=[geometry_names.get(k,k) for k,v in visual.get('observations',{}).items()
               if v.get('value')=='observed']
        body += '已有經確認的 EDA 幾何觀察：'+('、'.join(shown) if shown else '未發現特定模式')+'；'
    else:
        body += '尚無正式確認的多變量群數幾何線索，'
    body += ('候選密度參數是探索範圍，不代表預先知道正確群數。' if session.method()=='dbscan'
             else '候選 K 是可供比較的探索範圍，**不是從 EDA 推導出的確定群數**。')
    body += ('近鄰距離分位數和可能轉折只提供 eps 的初步線索，不能證明最佳 eps。' if session.method()=='dbscan'
             else '單變量峰數及樣本量只能補充探索廣度，運算預算也不是統計上的 K 上界。')
    body += '已核准的詳細參數來源與搜索理由記錄於 config.json，可用於重現及稽核。\n\n'

    body += '| 候選 | 已核准參數 |\n|---|---|\n'
    for i,r in enumerate(results):
        params=', '.join(f'{key}={value}' for key,value in r['config'].items()
                         if key in ('k','metric','linkage','eps','min_samples'))
        prefix = 'D' if session.method()=='dbscan' else 'C'
        body += f'| {prefix}{i+1} | {params} |\n'
    body += '\nStage 3 的執行許可僅授權在 Stage 4 使用這份設定及核准預算；不得自動選出最佳 K。\n\n'
    body += stage_block(3)
    body += '## Stage 4 — 候選執行、品質評估與最終選群\n\n'
    if session.gate.state.get('stage4_auto_diagnostics',False):
        body += 'Stage 3 已明確授權候選全資料擬合及後續 Silhouette／重抽樣 ARI 診斷預算；Stage 4 自動連續執行已授權工作，無額外中途結果確認，最終模型仍須研究者獨立核准。\n\n'
    elif session.gate.state.get('stage4_candidate_execution', False):
        body += '這份較早的 Stage 4 Session 於全資料擬合後獨立確認候選結果，再執行已核准的 Silhouette／重抽樣 ARI 診斷。\n\n' 
    else:
        body += '這份舊版 Session 於 Stage 3 執行並確認全資料候選，Stage 4 接續核准的品質與穩定性診斷；歷史批准並未遷移或重新擬合。\n\n' 
    body += '| 候選 | 已核准參數 | 實際群數 | 雜訊數 |\n|---|---|---:|---:|\n'
    for i,r in enumerate(results):
        params=', '.join(f'{key}={value}' for key,value in r['config'].items()
                         if key in ('k','metric','linkage','eps','min_samples'))
        prefix = 'D' if session.method()=='dbscan' else 'C'
        body += f'| {prefix}{i+1} | {params} | {r["metrics"]["clusters"]} | {r["info"].get("noise_n","不適用")} |\n'
    body += '\n候選範圍僅反映本輪 EDA 線索與已批准計算預算；'
    body += ('不能由當次最大分數斷言唯一最佳 eps 或自然群數。\n\n'
             if session.method()=='dbscan' else
             '不能因為最大分數落於某個 K，就推論其他 K 已經失去研究價值。\n\n')

    ks=sorted({r['config'].get('k') for r in results if 'k' in r['config']})
    if ks:
        body += f'**實際比較的群數：** K={", ".join(map(str,ks))}，共 {len(results)} 組已核准候選。\n\n'
    else:
        body += f'**實際比較：** 共 {len(results)} 組已批准密度參數設定。\n\n'
    if has_partition:
        selected_row=contrast['candidates'][index]
        body += (f'**最終選擇：{"D" if session.method()=="dbscan" else "C"}{index+1}，{session.method()}，'
                 + ', '.join(f'{k}={v}' for k,v in chosen_config.items() if k in ('metric','k','linkage','eps','min_samples'))
                 + f'；Silhouette={fmt(selected_row["silhouette"])}，'
                 + f'重抽樣 ARI={fmt(selected_row["ari_mean"])}。**\n\n')
        body += '**選擇理由（核准紀錄）：** '+str(config['selection_explanation']['chosen_reason'])+'\n\n'
    else:
        body += '**本次未選出最終模型。** 所有候選僅作探索性比較。\n\n'
    body += render_metric_contrast(contrast,index, 'D' if session.method()=='dbscan' else 'C')
    body += selection_warnings(results,index)
    if session.method()=='dbscan':
        review=evidence.get('dbscan_eps_review',{})
        if review.get('status')=='REVIEW_UPPER_EPS':
            body += ('**DBSCAN 候選範圍檢查：** '
                     +review['recommendation']+' 這是待審查的探索提示，不會自行追加計算。\n\n')
        elif review.get('status')=='DESCRIPTIVE_TRENDS_ONLY':
            body += ('**DBSCAN 參數檢查：** 已比較相同 min_samples 下的不同 eps；'
                     '群數、雜訊與 Silhouette 須連同實際形狀一起判讀。\n\n')
    if session.method()=='hierarchical':
        if evidence.get('linkage_comparisons'):
            body += render_approved_linkage_comparison(evidence['linkage_comparisons'])
        if evidence.get('distance_comparisons'):
            body += render_approved_distance_comparison(evidence['distance_comparisons'])
    body += '### 必須保留的選群限制\n\n'
    body += '本次結論僅涵蓋上述已批准候選。若 Silhouette 與 ARI 支持不同候選，'
    body += '必須同時解釋分離品質、穩定性與群組大小的取捨；候選邊界須另行批准擴展。\n\n'
    if config['selection_explanation'].get('conflicts'):
        body += '**研究者記錄的取捨：** '+str(config['selection_explanation']['conflicts'])+'\n\n'
    if config['selection_explanation'].get('limitations'):
        # Preserve the approved operator's original wording; do not rewrite
        # historical consent records or change the final-selection payload.
        body += '**本次限制（研究者已批准紀錄原文）：** '+str(config['selection_explanation']['limitations'])+'\n\n'
    if has_partition:
        body += ('**最終選群授權狀態：** 上述已選候選已經 Stage 4 獨立批准，'
                 '不代表候選探索範圍以外的模型已獲核准。Stage 5 研究交付仍須另行確認。')
        if '提案非最終核准' in str(config['selection_explanation'].get('limitations','')):
            body += (' 研究者原文中的「提案非最終核准」保留作歷史紀錄；'
                     '本段以實際 Stage 4 核准紀錄為準，不應解讀成目前尚未核准最終選群。')
        body += '\n\n'
    body += '![Candidate quality](figures/candidate_quality.svg)\n\n'
    if (out/'selection_evidence'/'candidate_partitions.svg').is_file():
        body += '### 各候選實際分群形狀\n\n'
        body += '下圖呈現 Stage 4 擬合之候選的實際標籤，用於審查形狀、碎群及雜訊，不代表先驗真實群數。\n\n'
        body += '![Candidate partitions](selection_evidence/candidate_partitions.svg)\n\n'
    if has_partition and (out/'figures'/'stage4_selected_partition.svg').is_file():
        body += '### 最終選定模型的群組形狀\n\n'
        body += '此圖使用已核准的最終候選標籤繪製，沒有重新擬合模型。\n\n'
        body += '![Final approved partition](figures/stage4_selected_partition.svg)\n\n'
    for figure in sorted((out/'selection_evidence').glob('*.svg')):
        if figure.stem=='quality_and_sizes' or figure.stem=='stability':
            body += f'![{figure.stem}](selection_evidence/{figure.name})\n\n'
    if session.method()=='pam' and (out/'selection_evidence'/'medoid_feature_table.json').is_file():
        medoid_rows=json.loads((out/'selection_evidence'/'medoid_feature_table.json').read_text(encoding='utf-8'))
        body += '### K-medoids（PAM）真實代表觀測與群組大小\n\n'
        body += '以下為各候選實際 medoid 的原始欄位值；資料列號僅供追溯，不是距離或品質分數。\n\n'
        body += '| 候選 K | 代表觀測 | 群組大小 | 原始特徵值 |\n|---:|---|---:|---|\n'
        for row in medoid_rows:
            features=', '.join(f'{c}={v}' for c,v in row['observed_features'].items())
            body += f'| {row["candidate_k"]} | {row["internal_row_id"]} | {row["group_size"]} | {features} |\n'
        body += '\n'
    body += stage_block(4, workflow=config["workflow"])
    body += '## Stage 5 — 群組輪廓、研究討論與結論\n\n'
    body += render_cluster_profiles(raw,model,labels,schema)
    from .posthoc import render_numeric_comparisons, supplementary_exploration
    body += render_numeric_comparisons(original_raw, labels, selected_cols, supplementary_cols)
    if supplementary_cols and has_partition:
        body += supplementary_exploration(original_raw, labels, supplementary_cols,
                    approved_roles.get('association_pairs', []))
    from .report_explanations import render_geometric_research_findings
    body += render_geometric_research_findings(model, labels, schema, session.method(),
        session.state.get('eda_handoff',{}).get('visual',{}),
        final.get('info',{}) if final is not None else {},
        session.state['fitted_preprocessing'])
    if has_partition:
        body += dominant_feature_findings(model,labels,schema)
    body += '### 整體研究結論\n\n'
    body += (f'本次選定 {config["selected_k"]} 群。Stage 4 的核准標籤圖及群組輪廓提供觀測上的群間差異；'
             '對非凸資料還須檢視形狀與連通性，不宜僅用中心位置或中位數推斷群組結構。'
             '群組描述不是獨立外部驗證。' if has_partition else
             '本次未批准最終群組，不能主張已發現可解釋的顧客類型。')
    body += ' 研究結論不支持因果推論；小群、缺失值、特徵權重與候選範圍仍構成限制。\n\n'
    body += '### 可重現性與附件\n\n'
    body += '已核准模型、候選參數、逐次重抽樣、圖表來源和統計結果存於研究附件。'
    body += '在研究資料與 Python 依賴可用時，可以使用 `reproduce.py --verify` 核對保存的結果；'
    body += '完整執行稽核、雜湊與設定保存在 CSV、JSON 及 manifest 檔，並不直接鋪滿閱讀正文。\n\n'
    body += stage_block(5)
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
    (out/'analysis.md').write_text(body, encoding='utf-8')
    (out/'analysis_offline.html').write_text(offline_html(body, out), encoding='utf-8')
    qmd = '---\ntitle: "Clustering research report"\nformat:\n  html:\n    code-fold: true\n    code-summary: "展開 Python 程式碼"\njupyter: python3\nexecute:\n  eval: false\n---\n\n' + body.replace('```python', '```{python}')
    (out/'analysis.qmd').write_text(qmd, encoding='utf-8')
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
    (out/"README.md").write_text("# 閱讀與重現\n\n直接閱讀 analysis.md、analysis.qmd 或 analysis_offline.html；三者均有逐階段 Python 程式碼（閱讀預設不執行）。\n"
        "reproduce.py --verify 是開發端驗收入口，會以已核准快照重新擬合並比較結果；如有差異會在 reproduction_audit/ 保存完整重現診斷及逐欄位差異，仍判 FAIL，不會變更原始快照；一般使用者由助理代為執行，不需安裝 R。\n"
        "本機執行需要 requirements.txt 中的 Python 依賴；Quarto 缺席時 analysis_offline.html 為完整離線備援。\n"
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
