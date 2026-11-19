"""Faithful computation instructions beside each stage's findings.

Every code block refers to the exported approved inputs, authentic engine
functions and configuration.  Quarto is non-executing by default; a complete
strict replay is available through reproduce.py --verify.
"""

COMMON = """import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Run snippets from the extracted research report directory. Load the exact
# archived implementation shipped with this report, without pip installation.
# Quarto disables evaluation by default; running a snippet is a new,
# descriptive calculation and is never a substitute for Stage 3 approval.
archive = Path('reproducibility').resolve()
if not (archive / 'clustering_native' / '__init__.py').is_file():
    raise FileNotFoundError('Run this code from the report directory containing reproducibility/clustering_native')
sys.path.insert(0, str(archive))
from clustering_native.core import digest
cfg = json.loads(Path('config.json').read_text(encoding='utf-8'))
plan = cfg['preprocessing_plan']
raw = pd.DataFrame(json.loads(Path('raw_feature_snapshot.json').read_text(encoding='utf-8')))
model = pd.DataFrame(json.loads(Path('model_feature_snapshot.json').read_text(encoding='utf-8')))
schema = {c: plan['schema'][c] for c in model}
results = json.loads(Path('candidate_results.json').read_text(encoding='utf-8'))
"""

STAGE_CODES = {
    1: COMMON + """from clustering_native.data import audit
# Full original-data auditing is retained in the Stage 1 session.
# This archived snapshot intentionally contains only selected features.
selected_feature_eda = audit(raw, schema)
preprocessing = json.loads(Path('config.json').read_text(encoding='utf-8'))['fitted_preprocessing']
print({'selected_n': len(model), 'features': list(model), 'fitted': preprocessing})
""",
    2: COMMON + """from clustering_native.suitability import assess
# Re-assessment is descriptive only.  It never fits a clustering model.
assessment = assess(model, plan, audit(model, schema))
print({'method': cfg['method'], 'suitability': assessment['methods']})
""".replace('from clustering_native.suitability import assess',
               'from clustering_native.suitability import assess\nfrom clustering_native.data import audit'),
    3: COMMON + """candidate_plan = cfg['candidate_plan']
# Planning only: these settings were explicitly approved before any fit.
# The archived results loaded above are NOT Stage 3 evidence.
configs = candidate_plan['configs']
print({'approved_candidate_count': len(configs),
       'configs': configs, 'budget': candidate_plan['budget'],
       'diagnostic_plan': candidate_plan['diagnostics_plan']})
""",
    4: COMMON + """from clustering_native.selection_evidence import _stats
# Review the saved full-data fits and the bounded stability diagnostics.
# Actual authorization sequence is documented by the archived workflow flag.
# Reading these values performs no new fit or approval.
saved = json.loads(Path('diagnostics.json').read_text(encoding='utf-8'))
for candidate_index, (result, outcome) in enumerate(zip(results, saved['stability'])):
    ari = _stats([run.get('ari') for run in outcome['runs']])
    print({'candidate_index': candidate_index, 'config': result['config'],
           'clusters': result['metrics'].get('clusters', len(set(result['labels']) - {-1})),
           'silhouette':result['metrics']['silhouette'],
           'ari_mean':ari['mean'], 'valid_repeats':ari['valid_n'],
           'failed_repeats':outcome['failures']})
# Pure replay of archived values: no fresh fit and no hidden model selection.
""",
    5: COMMON + """from clustering_native.report import profiles
index = cfg['final_index']
labels = None if index is None else results[index]['labels']
numeric, categorical = profiles(raw, schema, labels)
print({'numeric_profile_rows': len(numeric),
       'categorical_profile_rows': len(categorical)})
# The complete replay/verification entrypoint is: reproduce.py --verify
""",
}


def stage_block(stage, workflow=None):
    """Render source-backed code and the actual historical consent sequence.

    A legacy study must not be presented as an auto-continued study, and new
    studies must not inherit a formerly required intermediate result approval.
    """
    if stage not in STAGE_CODES:
        raise ValueError('Stage must be 1..5')
    code = STAGE_CODES[stage]
    if stage == 4:
        if workflow == 'stage3_plan_stage4_auto_diagnostics':
            note = ('# Workflow: Stage 3 approved fits and diagnostic budget together; '
                    'Stage 4 performed both without a separate result approval.\n'
                    '# An independent final-selection Hard Gate was still required.\n')
        elif workflow == 'stage3_plan_stage4_execution':
            note = ('# Workflow: Stage 4 candidate fits required a separate result '
                    'approval before the authorized diagnostics.\n')
        elif workflow == 'legacy_stage3_execution_stage4_diagnostics':
            note = ('# Workflow: legacy Stage 3 executed and confirmed candidate '
                    'fits before Stage 4 diagnostics.\n')
        else:
            note = '# Workflow: consult config.json for the archived authorization sequence.\n'
        code = code.replace('saved = json.loads(', note + 'saved = json.loads(', 1)
    return ('\n**本階段計算對應 Python（來源：已封存的研究輸入與模組）**\n\n'
            '```python\n'+code.rstrip()+'\n```\n\n')


def stage_code():
    """Historical appendix helper retained for compatibility, not auto-appended."""
    return '\n## 計算來源與逐階段 Python\n\n' + ''.join(
        f'### Stage {stage}\n\n{stage_block(stage)}' for stage in range(1, 6))
