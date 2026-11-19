"""A-class fixes: data-grounded planning, linkage, pre-disclosure, sensitivity."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pandas as pd
from clustering_native.planning import bounded_eda_k_hints, exploratory_draft
from clustering_native.report_explanations import selection_warnings, render_approved_linkage_comparison
from clustering_native.selection_evidence import build_selection_evidence
from clustering_native.approved_sensitivity import compare_approved_studies


class PlanningAndWarnings(unittest.TestCase):
    def test_numerical_eda_hint_is_bounded_not_a_fitted_k(self):
        rng=np.random.default_rng(7)
        data=pd.DataFrame({'x':np.r_[rng.normal(-4,.6,60),rng.normal(4,.6,60)],
                           'y':rng.normal(0,1,120)})
        schema={c:{'type':'numeric'} for c in data}
        result=bounded_eda_k_hints(data,{'schema':schema})
        self.assertLessEqual(result['suggested_exploratory_upper_cap'],12)
        self.assertGreaterEqual(result['suggested_exploratory_upper_cap'],6)
        self.assertIn('單變量',result['uncertainty'])
        self.assertTrue(result['numeric_marginal_evidence'])

    def test_hierarchical_linkage_evidence_is_proposed_not_fitted(self):
        rng=np.random.default_rng(2)
        data=pd.DataFrame({'x':rng.normal(size=40),'y':rng.normal(size=40)})
        plan={'schema':{'x':{'type':'numeric'},'y':{'type':'numeric'}},
              'weights':{'x':1,'y':1}}
        class SessionStub:
            state={'approved_eda':{'outliers':{}},'eda_handoff':{},'assessment':{}}
            model=lambda self: data
            plan=lambda self: plan
            method=lambda self: 'hierarchical'
        draft=exploratory_draft(SessionStub())
        self.assertIn('exploratory-only',draft['basis'])
        self.assertIn('單變量',draft['search_rationale'])
        self.assertLessEqual(len(draft['configs']), draft['budget']['max_candidates'])
        self.assertIn('ward',{c['linkage'] for c in draft['configs']})
        self.assertIn('complete',{c['linkage'] for c in draft['configs']})
        self.assertIn('單變量',draft['evidence'])
        self.assertTrue(all(set(c)==set(src) for c,src in zip(draft['configs'],draft['parameter_sources'])))

    def test_mixed_gower_compares_non_ward_linkages_only(self):
        data=pd.DataFrame({'x':[1.,2.,3.,4.,5.,6.],
                           'category':['a','a','b','b','c','c']})
        plan={'schema':{'x':{'type':'numeric'},'category':{'type':'nominal'}},
              'weights':{'x':1,'category':1}}
        class SessionStub:
            state={'approved_eda':{'outliers':{}},'eda_handoff':{},
                   'assessment':{'gower_preflight':{'status':'PASS'}}}
            model=lambda self: data
            plan=lambda self: plan
            method=lambda self: 'hierarchical'
        draft=exploratory_draft(SessionStub())
        self.assertNotIn('ward',{c['linkage'] for c in draft['configs']})
        self.assertTrue({'average','complete','single'}<=set(c['linkage'] for c in draft['configs']))

    def test_small_groups_and_parameter_boundaries_disclosed(self):
        candidates=[{'config':{'eps':.15,'min_samples':3},
                     'labels':[0,0,0,0,1], 'metrics':{'silhouette':.8}},
                    {'config':{'eps':.5,'min_samples':3},
                     'labels':[0,0,0,1,1], 'metrics':{'silhouette':.4}}]
        report=selection_warnings(candidates,0)
        self.assertIn('下界 eps',report)
        self.assertIn('小群',report)
        self.assertIn('不能宣稱全域最佳',report)

    def test_linkage_summary_never_fakes_empirical_comparison(self):
        self.assertIn('沒有', render_approved_linkage_comparison([]))
        observed=[{'candidate_index':0,'metric':'gower','k':3,'linkage':'average',
                  'silhouette':.42,'stability_ari_mean':.7,'min_nonnoise_group_size':8},
                  {'candidate_index':1,'metric':'gower','k':3,'linkage':'complete',
                  'silhouette':.38,'stability_ari_mean':.73,'min_nonnoise_group_size':6}]
        t=render_approved_linkage_comparison(observed)
        self.assertIn('average',t)
        self.assertIn('complete',t)
        self.assertIn('不能',t)


class EmpiricalLinkageAudit(unittest.TestCase):
    def test_distinct_linkage_is_not_represented_as_cut_sensitivity(self):
        with tempfile.TemporaryDirectory() as t:
            model=pd.DataFrame({'x':[1,1.2,3,3.2,8,8.2], 'y':[0,.1,0,.1,0,.1]})
            configs=[{'metric':'euclidean','k':2,'linkage':'ward'},
                     {'metric':'euclidean','k':3,'linkage':'ward'},
                     {'metric':'euclidean','k':3,'linkage':'complete'}]
            labels=[[0,0,0,0,1,1],[0,0,1,1,2,2],[0,0,1,1,2,2]]
            results=[]
            for c,l in zip(configs,labels):
                results.append({'config':c,'labels':l,'metrics':{'clusters':c['k'], 'silhouette':.5},
                                'info':{'linkage_matrix':__import__('scipy.cluster.hierarchy',fromlist=['linkage']).linkage(model.to_numpy(),method=c['linkage']).tolist()},'warnings':[]})
            from clustering_native.education import PLANNED_EVIDENCE
            diag={'stability':[
                {'runs':[{'ari':.8}], 'failures':0}
                for l in labels], 'initialization':{'status':'NOT_APPLICABLE','runs':[]}}
            payload={'configs':configs,'parameter_sources':[{} for _ in configs],
                     'diagnostics_plan':{'repeats':1},'search_rationale':'QA',
                     'boundary_limitations':'QA', 'planned_metric_evidence':PLANNED_EVIDENCE}
            class Stub:
                directory=Path(t)
                state={'results':results, 'diagnostics':diag}
                gate=SimpleNamespace(state={'payloads':{'candidates':payload}})
                model=lambda self:model
                method=lambda self:'hierarchical'
            summary=build_selection_evidence(Stub())
            self.assertTrue(summary['no_automatic_winner'])
            import json
            record=json.loads((Path(t)/'selection_evidence'/'selection_evidence.json').read_text())
            # Same Ward dendrogram K=2 vs K=3, not Ward K=3 vs Complete K=3.
            self.assertEqual(len(record['cut_sensitivity']),1)
            self.assertEqual(len(record['linkage_comparisons']),2)
            self.assertEqual(record['metric_disclosure_audit']['status'],'ALL_REPORTED_METRICS_PREDISCLOSED')
            payload['planned_metric_evidence']={'silhouette':'only'}
            with self.assertRaisesRegex(PermissionError,'Undisclosed'):
                build_selection_evidence(Stub())


class SensitivityAuthorization(unittest.TestCase):
    def test_compare_rejects_incompatible_or_unapproved(self):
        from clustering_native.approved_sensitivity import _validated_study
        with tempfile.TemporaryDirectory() as tmp:
            # A directory without a real authorized session cannot pass.
            with self.assertRaises((FileNotFoundError,ValueError)):
                _validated_study(Path(tmp)/'missing')

    def test_no_fits_compare_only_independently_approved(self):
        from clustering_native import approved_sensitivity as mod
        class Fake:
            def __init__(self, path, changed):
                self.directory=Path(path)
                self.state={'input_sha256':'same-immutable','model_hash':'m'+str(changed),
                    'model_data':{'x':[1.,2.,3.,4.]},
                    'results':[{'labels':[0,0,1,1] if not changed else [0,1,0,1],
                        'config':{'k':2},'metrics':{'silhouette':.3 if not changed else .2}}],
                    'final_index':0}
                self._changed=changed
            def model(self):return pd.DataFrame({'x':[1.,2.,3.,4. if not self._changed else 4.5]})
            def method(self):return 'kmeans'
            def plan(self):return {'schema':{'x':{'type':'numeric'}},
                 'weights':{'x':1},'actions':{'x':{'scale':'standard' if self._changed else 'none'}}}
        with tempfile.TemporaryDirectory() as d:
            a,b=Fake(Path(d)/'a',False),Fake(Path(d)/'b',True)
            with patch.object(mod,'_validated_study',side_effect=[a,b]):
                answer=compare_approved_studies(a.directory,b.directory,Path(d)/'out')
            self.assertEqual(answer['comparison']['model_fits_performed_by_comparison'],0)
            self.assertEqual(answer['comparison']['n_common_rows'],4)
            self.assertTrue((Path(d)/'out'/'approved_sensitivity.md').exists())

if __name__=='__main__':unittest.main()
