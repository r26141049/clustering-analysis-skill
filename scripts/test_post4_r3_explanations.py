"""R3 read-only evidence quality tests: never authorize or fit models."""
import unittest
import pandas as pd
from clustering_native.report_explanations import (
    actual_metric_contrast, render_metric_contrast,
    descriptive_preprocessing_sensitivity,
)


class StatisticalExplanationR3(unittest.TestCase):
    def test_observed_silhouette_vs_ari_conflict_is_reported(self):
        results=[{'config':{'k':2},'labels':[0,0,0,1,1,1], 'metrics':{'silhouette':.5}},
                 {'config':{'k':3},'labels':[0,0,1,1,2,2], 'metrics':{'silhouette':.6}}]
        stable=[{'failures':0,'runs':[{'ari':.85},{'ari':.75}]},
                {'failures':0,'runs':[{'ari':.4},{'ari':.3}]}]
        result=actual_metric_contrast(results,stable)
        self.assertEqual(result['conflicting_with_silhouette'],['重抽樣 ARI'])
        text=render_metric_contrast(result,1)
        for phrase in ['相互競爭','C1','C2','0.6000','指標衝突']:
            self.assertIn(phrase,text)
        self.assertNotIn('Jaccard',text)

    def test_runner_stage3_stage4_same_ari_policy(self):
        from clustering_native.runner import _candidate_review
        results=[{'config':{'k':2},'labels':[0,0,0,1,1,1],
                  'metrics':{'silhouette':.45,'clusters':2}}]
        stable=[{'failures':1,'runs':[{'ari':.7},{'ari':None},{'ari':.6}]}]
        class Stub:state={'results':results,'stage3_stability':stable}
        preview=_candidate_review(Stub())[0]
        contrast=actual_metric_contrast(results,stable)['candidates'][0]
        self.assertAlmostEqual(preview['ari_mean_conditional'],.65)
        self.assertEqual(preview['ari_mean_conditional'],contrast['ari_mean'])
        self.assertEqual(preview['stability_failures'],1)

    def test_missing_ari_not_zero_noise_retained(self):
        results=[{'config':{'eps':.5},'labels':[0,0,1,-1,-1],
                  'metrics':{'silhouette':.2}}]
        stable=[{'failures':1,'runs':[{'ari':None},{'ari':.3}]}]
        result=actual_metric_contrast(results,stable)['candidates'][0]
        self.assertEqual(result['noise_n'],2)
        self.assertEqual(result['ari_valid_repeats'],1)
        self.assertAlmostEqual(result['ari_mean'],.3)

    def test_inconsistent_evidence_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'Each candidate'):
            actual_metric_contrast([{'labels':[0,1]}],[])

    def test_observed_spend_range_and_imputation_only(self):
        raw=pd.DataFrame({'spend':[10.,20.,30.,40.,50.,1000000.,None],
                          'tier':['Bronze','Silver',None,'Gold','Bronze','Silver','Gold']})
        model=pd.DataFrame({'spend':[10.,20.,30.,40.,50.,1000000.,30.],
                            'tier':['Bronze','Silver','Bronze','Gold','Bronze','Silver','Gold']})
        text=descriptive_preprocessing_sensitivity(raw,model,{'actions':{},'weights':{}})
        self.assertIn('中央跨度／全距',text)
        self.assertIn('可能被極端值壓縮',text)
        self.assertIn('淨減少缺失 1 筆',text)
        self.assertIn('沒有更動前處理、重估分群',text)
        self.assertIn('需依 Stage 1／3',text)

if __name__=='__main__': unittest.main()
