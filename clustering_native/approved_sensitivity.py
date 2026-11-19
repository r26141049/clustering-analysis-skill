"""Read-only sensitivity comparison of *independently approved* research runs.

This module never estimates alternative models, modifies sessions, or treats an
unapproved preprocessing proposal as usable evidence. Comparing a genuine
alternative requires completing its own Stage 1--5 authorization workflow.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score
from .core import digest, write_json


def _validated_study(path):
    from .session import Session
    study = Session(path)
    gate = study.gate.state
    if gate['phase'] not in {'S5_REVIEW', 'COMPLETE'}:
        raise PermissionError('Only Stage 5 studies with an approved final choice can be compared')
    required = {'preprocess', 'method', 'candidates', 'results', 'final'}
    if not required.issubset(gate['approvals']):
        raise PermissionError('Study lacks independently approved research decisions')
    if not study.state.get('results') or study.state.get('final_index') is None:
        raise PermissionError('No approved final partition in research session')
    # This establishes that the saved analysis input has not been replaced.
    study._integrity()
    return study


def compare_approved_studies(reference_path, alternative_path, destination):
    """Produce observed model-sensitivity evidence from two authorized runs.

    The same immutable original CSV and method are required. The feature
    representation must *actually differ*; otherwise a model random-seed
    comparison must not be advertised as preprocessing sensitivity.
    """
    first = _validated_study(reference_path)
    second = _validated_study(alternative_path)
    if first.directory == second.directory:
        raise ValueError('The alternative must be a separate approved study')
    if first.state['input_sha256'] != second.state['input_sha256']:
        raise ValueError('Original input hashes differ; comparison would not be paired')
    if first.method() != second.method():
        raise ValueError('Preprocessing sensitivity requires the same approved method')
    original, alternate = first.model(), second.model()
    if len(original) != len(alternate):
        raise ValueError('Different retained row counts: paired ARI is invalid without a proven row-ID mapping')
    if list(original.columns) != list(alternate.columns):
        raise ValueError('Feature sets/order differ; run separate method comparison, not paired preprocessing sensitivity')
    source_plan = first.plan(); second_plan = second.plan()
    if digest(source_plan) == digest(second_plan) and digest(first.state['model_data']) == digest(second.state['model_data']):
        raise ValueError('Identical approved preprocessing: no alternative sensitivity design exists')
    a = first.state['results'][first.state['final_index']]
    b = second.state['results'][second.state['final_index']]
    labels_a = np.asarray(a['labels']); labels_b = np.asarray(b['labels'])
    if len(labels_a) != len(labels_b) or len(labels_a) != len(original):
        raise ValueError('Selected candidate label alignment is invalid')
    changes = []
    for name in original.columns:
        x, y = original[name], alternate[name]
        same = x.eq(y) | (x.isna() & y.isna())
        changes.append({
            'feature': name,
            'different_cells': int((~same).sum()),
            'original_missing_n': int(x.isna().sum()),
            'alternative_missing_n': int(y.isna().sum()),
            'original_type': source_plan['schema'][name]['type'],
            'alternative_type': second_plan['schema'][name]['type'],
            'weight_original': source_plan['weights'][name],
            'weight_alternative': second_plan['weights'][name],
        })
    all_results = {
        'comparison': 'independently approved preprocessing sensitivity; NO additional model fits',
        'reference': {'input_sha256': first.state['input_sha256'],
                      'model_hash': first.state['model_hash'], 'method': first.method(),
                      'final_index': first.state['final_index'], 'config': a['config']},
        'alternative': {'input_sha256': second.state['input_sha256'],
                        'model_hash': second.state['model_hash'], 'method': second.method(),
                        'final_index': second.state['final_index'], 'config': b['config']},
        'same_candidate_config': a['config'] == b['config'],
        'n_common_rows': len(original), 'feature_changes': changes,
        'paired_label_ari': float(adjusted_rand_score(labels_a, labels_b)),
        'reference_cluster_sizes': {str(v): int(np.count_nonzero(labels_a == v)) for v in sorted(set(labels_a))},
        'alternative_cluster_sizes': {str(v): int(np.count_nonzero(labels_b == v)) for v in sorted(set(labels_b))},
        'silhouette_reference': a['metrics'].get('silhouette'),
        'silhouette_alternative': b['metrics'].get('silhouette'),
        'silhouette_delta_alternative_minus_reference': (
            float(b['metrics']['silhouette'] - a['metrics']['silhouette'])
            if a['metrics'].get('silhouette') is not None and b['metrics'].get('silhouette') is not None else None),
        'model_fits_performed_by_comparison': 0,
        'scope_limitations': [
            'Both sessions were independently authorized; this comparison cannot authorize any fit.',
            'ARI compares the same row positions only; label names are arbitrary.',
            'Different candidate configurations confound preprocessing with parameter changes.' if a['config'] != b['config']
            else 'Same selected candidate configuration; preprocessing effects are observed, not causal.',
            'Each study may use its own distance scale, so differences in silhouette are not a controlled causal estimate.',
            'No independent holdout validation or formal uncertainty interval is implied.',
        ],
    }
    out = Path(destination).resolve()
    if out.exists():
        raise FileExistsError('Use a new comparison output directory, never overwrite an existing analysis')
    out.mkdir(parents=True)
    write_json(out/'approved_sensitivity.json', all_results)
    pd.DataFrame(changes).to_csv(out/'feature_changes.csv', index=False)
    codeword = '可比較' if a['config'] == b['config'] else '參數不同（混雜）'
    lines = [
        '# 經獨立批准研究的前處理敏感性比較', '',
        '此報告唯讀比較兩個完成必要研究批准的 Session，**不新擬合模型，也沒有代替任何授權**。', '',
        f"- 共同觀測數：{len(original)}；方法：`{first.method()}`；候選設定：{codeword}。",
        f"- 配對群組 ARI：{all_results['paired_label_ari']:.4f}（描述性一致性，非穩定性重抽樣）。",
        f"- 原始／替代 Silhouette：{all_results['silhouette_reference']} ／ {all_results['silhouette_alternative']}。",
        f"- 原始／替代群大小：{all_results['reference_cluster_sizes']} ／ {all_results['alternative_cluster_sizes']}。", '',
        '| 特徵 | 更動儲存格 | 原始缺失 | 替代缺失 | 原始權重 | 替代權重 |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for row in changes:
        lines.append('| '+ ' | '.join(str(row[k]).replace('|','／') for k in
            ['feature','different_cells','original_missing_n','alternative_missing_n','weight_original','weight_alternative'])+' |')
    lines += ['', '## 限制', ''] + ['- '+t for t in all_results['scope_limitations']]
    (out/'approved_sensitivity.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return {'output_dir': str(out), 'comparison': all_results, 'files': ['approved_sensitivity.json','approved_sensitivity.md','feature_changes.csv']}
