"""R4H.4.1 report wording regression using archived actual Iris/Two-Moons runs.

Tests only archived read-only values; never refits the supplied research data.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
import numpy as np
import pandas as pd
from clustering_native.report_explanations import render_geometric_research_findings
from clustering_native.report_code import stage_block
from clustering_native.core import Gate
from clustering_native.session import Session
import test_post4_r4h4_final_repair as r4h4_fixture

DATA = Path(os.environ.get('CLUSTERING_TEST_ASSET_ROOT', '/mnt/data'))


def load_archived_result(path):
    if not path.is_file():
        raise unittest.SkipTest('Optional real-research ZIP is not available outside the acceptance workspace')
    with ZipFile(path) as z:
        prefix=next(name.rsplit('/',1)[0] for name in z.namelist() if name.endswith('/config.json') and name.count('/')==1)
        cfg=json.loads(z.read(prefix+'/config.json'))
        model=pd.DataFrame(json.loads(z.read(prefix+'/model_feature_snapshot.json')))
        results=json.loads(z.read(prefix+'/candidate_results.json'))
        info=results[cfg['final_index']].get('info',{})
        return cfg,model,results[cfg['final_index']]['labels'],info


class ReportConsistency(unittest.TestCase):
    def test_real_iris_model_coordinates_are_not_claimed_raw(self):
        cfg, model, labels, info = load_archived_result(DATA/'Iris_KMeans_Research_COMPLETE.zip')
        schema=cfg['preprocessing_plan']['schema']
        text=render_geometric_research_findings(model, labels, schema, cfg['method'], {}, info,
             cfg['fitted_preprocessing'])
        self.assertIn('建模特徵快照', text)
        self.assertIn('Z-score 標準化', text)
        self.assertIn('不可直接當成原始測量單位', text)
        self.assertNotIn('原始數值位置', text)
        self.assertIn('第 1 群（50 筆）',text)
        # Actual saved Z-score coordinates preserved in report summaries.
        x=model.loc[np.asarray(labels)==0,'sepal_length_cm']
        self.assertIn(f'{x.min():.3g}～{x.max():.3g}',text)

    def test_two_moons_no_scale_is_explicit(self):
        cfg,model,labels,info=load_archived_result(DATA/'Two_Moons_DBSCAN_Stage5_Research_REVIEW.zip')
        text=render_geometric_research_findings(model, labels, cfg['preprocessing_plan']['schema'],
             cfg['method'],{},info,cfg['fitted_preprocessing'])
        self.assertIn('未進行尺度標準化',text)
        self.assertNotIn('Z-score 標準化',text)
        self.assertIn('建模特徵快照', text)

    def test_mixed_feature_scale_and_transform_disclosure(self):
        model=pd.DataFrame({'log_feature':[1.,2.,3.,4.],'raw_feature':[10.,11.,20.,21.]})
        schema={c:{'type':'numeric'} for c in model}
        labels=[0,0,1,1]
        fitted={'log_feature':{'scale':'standard','transform':'log1p'},
                'raw_feature':{'scale':'none','transform':'none'}}
        desc=render_geometric_research_findings(model, labels,schema,'kmeans',{}, {}, fitted)
        self.assertIn('log1p 轉換 → Z-score 標準化',desc)
        self.assertIn('`raw_feature`：未進行尺度標準化',desc)

    def test_code_block_matches_per_session_authorization(self):
        new=stage_block(4,workflow='stage3_plan_stage4_auto_diagnostics')
        self.assertIn('without a separate result approval',new)
        self.assertIn('independent final-selection Hard Gate',new)
        self.assertNotIn('confirmed results separately',new)
        old=stage_block(4,workflow='stage3_plan_stage4_execution')
        self.assertIn('separate result approval',old)
        older=stage_block(4,workflow='legacy_stage3_execution_stage4_diagnostics')
        self.assertIn('legacy Stage 3',older)
        for block in (new,old,older):
            compile(block.split('```python\n',1)[1].split('\n```',1)[0],'<stage4>', 'exec')

    def test_report_preserves_operator_limitations_and_marks_final_approved(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)
            fixture=r4h4_fixture.R4H4Repair()
            study,token=fixture.new_case(path)
            fixture.yes(study,'candidates',token)
            fitted=study.fit_candidates()
            self.assertEqual(fitted['status'],'STAGE4_DIAGNOSTICS_COMPLETE')
            original='三次重抽樣不足以代表絕對穩定；提案非最終核准。'
            explanation={'chosen_reason':'QA fixture approval of K=3',
                         'candidate_reasons':{'0':'K2 comparison','1':'K3 comparison'},
                         'conflicts':'QA bounded','limitations':original}
            tok=study.propose_final(1,'QA approved final',explanation)
            fixture.yes(study,'final',tok)
            self.assertIn('final',study.gate.state['approvals'])
            out=path/'fresh_report'; study.report(out)
            config=json.loads((out/'config.json').read_text(encoding='utf-8'))
            body=(out/'analysis.md').read_text(encoding='utf-8')
            offline=(out/'analysis_offline.html').read_text(encoding='utf-8')
            qmd=(out/'analysis.qmd').read_text(encoding='utf-8')
            self.assertEqual(config['selection_explanation']['limitations'],original)
            self.assertEqual(config['workflow'],'stage3_plan_stage4_auto_diagnostics')
            for b in (body,offline,qmd):
                self.assertIn('最終選群授權狀態',b)
                self.assertIn('已經 Stage 4 獨立批准',b)
                self.assertIn('研究者原文中的「提案非最終核准」',b)
                self.assertIn('實際建模空間',b)
                self.assertNotIn('confirmed results separately',b)
                self.assertIn('without a separate result approval',b)
            self.assertNotIn('results',study.gate.state['approvals'])
            self.assertEqual(study.gate.state['phase'],'S5_REVIEW')
            self.assertNotIn('delivery',study.gate.state['approvals'])
            self.assertNotIn('qa_fixture',body)
            self.assertTrue((out/'figures'/'stage4_selected_partition.png').exists())

    def test_old_workflow_gate_untouched(self):
        old=Gate({**Gate().state,'stage4_candidate_execution':True})
        self.assertEqual(old.TRANSITIONS['results'][1],'S4_RESULTS')
        self.assertIn('results',old.PHASE_REQUIREMENTS['S4_REVIEW'])
        new=Gate({**Gate().state,'stage4_candidate_execution':True,'stage4_auto_diagnostics':True})
        self.assertNotIn('results',new.PHASE_REQUIREMENTS['S4_REVIEW'])


if __name__=='__main__': unittest.main(verbosity=2)
