"""R4H.2: report fidelity of fitted preprocessing; no default model refits here."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
from clustering_native.data import preprocess
from clustering_native.preprocessing_disclosure import (preprocessing_evidence_rows,
                                                       render_preprocessing_disclosure)


class R4H2PreprocessingDisclosure(unittest.TestCase):
    def test_actual_zscore_values_and_formula(self):
        raw=pd.DataFrame({'sepal_length_cm':[4.,5.,6.,7.],
                          'petal_length_cm':[1.,3.,5.,7.]})
        plan={'schema':{c:{'type':'numeric','role':'feature'} for c in raw},
              'actions':{c:{'scale':'standard','missing':'retain'} for c in raw},
              'weights':{c:1.0 for c in raw}}
        model,fitted=preprocess(raw,plan)
        rows=preprocessing_evidence_rows(raw,model,plan,fitted)
        self.assertEqual(len(rows),2)
        self.assertAlmostEqual(rows[0]['fitted_center'],5.5)
        self.assertAlmostEqual(rows[0]['fitted_divisor'],np.std([4.,5.,6.,7.],ddof=0))
        self.assertAlmostEqual(rows[1]['model_mean'],0.,places=12)
        self.assertAlmostEqual(rows[1]['model_population_sd'],1.,places=12)
        text=render_preprocessing_disclosure(raw,model,plan,fitted)
        self.assertIn('Z-score',text)
        self.assertIn('ddof=0',text)
        self.assertIn('5.5',text)
        self.assertIn('1.11803',text)
        self.assertIn('沒有刪除觀測',text)
        self.assertNotIn('Min-Max',text)
        self.assertEqual(len(raw),len(model))

    def test_other_preprocessing_not_falsely_reported_as_zscore(self):
        raw=pd.DataFrame({'bill':[1.,2.,3.,4.,None,22.],
                          'segment':['A','A','B','B','A','B']})
        plan={'schema':{'bill':{'type':'numeric','role':'feature'},
                        'segment':{'type':'nominal','role':'feature'}},
              'actions':{'bill':{'missing':'median','transform':'log1p','scale':'robust'},
                         'segment':{'mapping':[['A','Group A'],['B','Group B']]}},
              'weights':{'bill':1.5,'segment':1.0}}
        model,fitted=preprocess(raw,plan)
        text=render_preprocessing_disclosure(raw,model,plan,fitted)
        self.assertIn('Robust scaling',text)
        self.assertIn('IQR',text)
        self.assertIn('log1p',text)
        self.assertIn('中位數插補',text)
        self.assertIn('3',text)
        self.assertIn('Group A',text)
        self.assertIn('1.5',text)
        self.assertNotIn('**Z-score 標準化',text)
        rows=preprocessing_evidence_rows(raw,model,plan,fitted)
        self.assertEqual(rows[0]['raw_missing_n'],1)
        self.assertEqual(rows[0]['model_missing_n'],0)
        self.assertEqual(rows[0]['fitted_fill'],3.0)
        self.assertIsNone(rows[1]['fitted_center'])
        self.assertEqual(json.loads(rows[1]['approved_mapping']),[['A','Group A'],['B','Group B']])

    def test_no_scale_or_imputation_is_explicit_and_accurate(self):
        raw=pd.DataFrame({'x':[1.,2.,4.,8.], 'category':['A','A','B','B']})
        plan={'schema':{'x':{'type':'numeric','role':'feature'},
                        'category':{'type':'nominal','role':'feature'}},
              'actions':{'x':{},'category':{}},'weights':{'x':1,'category':1}}
        model,fitted=preprocess(raw,plan)
        text=render_preprocessing_disclosure(raw,model,plan,fitted)
        self.assertIn('均未進行標準化',text)
        self.assertNotIn('**Z-score 標準化',text)
        self.assertIn('保留（原始無缺失）',text)
        rows=preprocessing_evidence_rows(raw,model,plan,fitted)
        self.assertEqual(rows[0]['model_mean'],3.75)
        self.assertIsNone(rows[0]['fitted_center'])

    def test_missing_or_inconsistent_fitted_details_fail_closed(self):
        raw=pd.DataFrame({'x':[1.,2.,3.,4.]})
        plan={'schema':{'x':{'type':'numeric','role':'feature'}},
              'actions':{'x':{'scale':'standard'}},'weights':{'x':1}}
        model,fitted=preprocess(raw,plan)
        with self.assertRaisesRegex(ValueError,'does not cover'):
            preprocessing_evidence_rows(raw,model,plan,{})
        bad=dict(fitted);bad['x']=dict(fitted['x']);bad['x']['scale']='robust'
        with self.assertRaisesRegex(ValueError,'disagree'):
            preprocessing_evidence_rows(raw,model,plan,bad)
        with self.assertRaisesRegex(ValueError,'row-aligned'):
            preprocessing_evidence_rows(raw.iloc[:-1],model,plan,fitted)
        with self.assertRaisesRegex(ValueError,'invalid fitted scaling'):
            bad['x']['scale']='standard';bad['x']['divisor']=0
            preprocessing_evidence_rows(raw,model,plan,bad)

    def test_csv_fields_sufficient_for_external_reproduction(self):
        raw=pd.DataFrame({'x':[4.,5.,7.,9.]})
        plan={'schema':{'x':{'type':'numeric','role':'feature'}},
              'actions':{'x':{'scale':'standard'}},'weights':{'x':2.0}}
        model,fitted=preprocess(raw,plan)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'preprocessing_effect_summary.csv'
            pd.DataFrame(preprocessing_evidence_rows(raw,model,plan,fitted)).to_csv(p,index=False)
            saved=pd.read_csv(p)
            self.assertEqual(saved.loc[0,'scale'],'standard')
            self.assertAlmostEqual(saved.loc[0,'approved_weight'],2.)
            self.assertAlmostEqual(saved.loc[0,'fitted_center'],6.25)
            self.assertAlmostEqual(saved.loc[0,'model_population_sd'],1.)

    def test_package_and_report_versions_aligned(self):
        import tomllib
        from clustering_native import __version__
        package=Path(__file__).resolve().parent.parent
        pyproject=tomllib.loads((package/'pyproject.toml').read_text(encoding='utf-8'))
        self.assertEqual(__version__,pyproject['project']['version'])
        self.assertTrue(__version__.startswith('1.0.0rc6.post4.dev'))

    def test_snapshot_disclosure_renders_in_offline_html_and_qmd(self):
        from clustering_native.presentation import offline_html
        from clustering_native import report
        raw=pd.DataFrame({'sepal_length_cm':[4.,5.,6.,7.],
                          'petal_length_cm':[1.,3.,5.,7.]})
        plan={'schema':{c:{'type':'numeric','role':'feature'} for c in raw},
              'actions':{c:{'scale':'standard'} for c in raw},
              'weights':{c:1.0 for c in raw}}
        model,fitted=preprocess(raw,plan)
        disclosure=render_preprocessing_disclosure(raw,model,plan,fitted)
        with tempfile.TemporaryDirectory() as td:
            report_dir=Path(td)
            (report_dir/'analysis.md').write_text(disclosure,encoding='utf-8')
            (report_dir/'analysis_offline.html').write_text(offline_html(disclosure,report_dir),encoding='utf-8')
            (report_dir/'analysis.qmd').write_text('---\ntitle: "Research"\n---\n'+disclosure,encoding='utf-8')
            for name in ('analysis.md','analysis_offline.html','analysis.qmd'):
                text=(report_dir/name).read_text(encoding='utf-8')
                self.assertIn('實際執行的前處理與參數',text)
                self.assertIn('ddof=0',text)
                self.assertIn('sepal_length_cm',text)
            html=(report_dir/'analysis_offline.html').read_text(encoding='utf-8')
            self.assertIn('<table>',html)
            self.assertIn('<strong>',html)
            self.assertNotIn('<script',html)
        source=Path(report.__file__).read_text(encoding='utf-8')
        self.assertIn('body += render_preprocessing_disclosure(raw, model, plan,',source)
        self.assertIn('preprocessing_effect_summary.csv',source)
        self.assertIn('(out/\'analysis_offline.html\').write_text',source)


if __name__=='__main__':
    unittest.main()
