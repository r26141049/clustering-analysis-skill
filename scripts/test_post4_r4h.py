"""R4H regression: gated feature roles, evidence-backed EDA, and honest descriptions."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from clustering_native.cli import dispatch
from clustering_native.session import Session
from clustering_native.planning import multivariate_separation_hint
from clustering_native.posthoc import supplementary_exploration,render_numeric_comparisons
from clustering_native.method_rationale import NAMES


class R4HFocusedTests(unittest.TestCase):
    def yes(self,s,item,token):
        return s.respond(item,token,'A','qa-r4h-'+item+'-'+str(len(s.gate.state['events'])),source='qa_fixture')

    def test_stage1_role_gate_is_required_for_new_cli_studies(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            df=pd.DataFrame({'bill':[10.,12.,13.,15.,18.,20.,22.,25.,31.,40.],
                             'tip':[1.,2.,2.,3.,3.,4.,4.,5.,6.,7.],
                             'day':['A','A','A','A','B','B','B','B','B','B']})
            df.to_csv(p/'x.csv',index=False)
            created=dispatch({'action':'create','session':str(p/'study'),'csv':str(p/'x.csv')})
            self.assertEqual(created['phase'],'S1_ROLE_REVIEW')
            s=Session(p/'study')
            plan={'schema':{'bill':{'type':'numeric','role':'feature'},
                            'tip':{'type':'numeric','role':'supplementary'},
                            'day':{'type':'nominal','role':'feature'}},
                  'weights':{'bill':1,'day':1},'actions':{'bill':{},'day':{}}}
            with self.assertRaises(PermissionError):s.propose_preprocessing(plan)
            token=s.propose_feature_roles({'bill':'feature','tip':'supplementary','day':'feature'},
                    research_question='Compare bill and tip after partitioning',association_pairs=[['bill','tip']])
            with self.assertRaises(PermissionError):
                s.approve_feature_roles('bad-token',{'value':'APPROVE','stage':1,'item':'roles','response':'A',
                                'source':'qa_fixture','message_id':'r4h-fake'})
            self.yes(s,'roles',token)
            bad={'schema':{c:dict(spec) for c,spec in plan['schema'].items()},
                 'weights':{'bill':1,'tip':1,'day':1},'actions':{'bill':{},'tip':{},'day':{}}}
            bad['schema']['tip']['role']='feature'
            with self.assertRaises(PermissionError):s.propose_preprocessing(bad)
            token=s.propose_preprocessing(plan)
            self.yes(s,'preprocess',token)
            self.assertEqual(s.gate.state['phase'],'S2_REVIEW')
            self.assertEqual(list(s.model()),['bill','day'])
            self.assertEqual(s.state['approved_feature_roles']['roles']['tip'],'supplementary')
            s.revise(1,'Change clustering feature roles and rerun Stage 1 approval')
            self.assertEqual(s.gate.state['phase'],'S1_ROLE_REVIEW')
            self.assertNotIn('roles',s.gate.state['approvals'])
            self.assertNotIn('preprocess',s.gate.state['approvals'])
            with self.assertRaises(PermissionError):s.plan()

    def test_mst_hint_discriminates_three_separated_from_unimodal(self):
        rng=np.random.default_rng(22)
        a=pd.DataFrame(np.vstack([rng.normal([i*8,0],.25,size=(40,2)) for i in range(3)]),columns=['x','y'])
        b=pd.DataFrame(rng.normal(0,1,size=(120,2)),columns=['x','y'])
        plan={'schema':{c:{'type':'numeric','role':'feature'} for c in a},'weights':{'x':1,'y':1}}
        h=multivariate_separation_hint(a,plan)
        self.assertEqual(h['status'],'TENTATIVE_SEPARATION')
        self.assertEqual(h['tentative_regions'],3)
        self.assertIn('scale_dependence_warning',h)
        self.assertEqual(multivariate_separation_hint(b,plan)['status'],'INCONCLUSIVE')

    def test_stage3_draft_uses_prefit_three_region_evidence(self):
        from types import SimpleNamespace
        from clustering_native.planning import exploratory_draft
        rng=np.random.default_rng(22)
        df=pd.DataFrame(np.vstack([rng.normal([i*8,0],.25,size=(40,2)) for i in range(3)]),columns=['x','y'])
        plan={'schema':{c:{'type':'numeric','role':'feature'} for c in df},
              'actions':{c:{} for c in df},'weights':{c:1 for c in df}}
        study=SimpleNamespace(model=lambda:df,plan=lambda:plan,method=lambda:'kmeans',
            state={'assessment':{},'approved_eda':{'outliers':{}},'eda_handoff':{'visual':{}}})
        draft=exploratory_draft(study)
        self.assertEqual([c['k'] for c in draft['configs']],[2,3,4,5])
        self.assertIn('約 3 個分離區域',draft['search_rationale'])
        self.assertEqual(draft['parameter_sources'][1]['k']['source'],'data_diagnostic')

    def test_real_feature_names_on_eda_axes(self):
        from clustering_native.figures import eda_figures
        from clustering_native.workflow_evidence import geometry_figures
        from clustering_native.data import audit
        with tempfile.TemporaryDirectory() as td:
            df=pd.DataFrame({'total_bill':[10.,11.,12.,13.,14.,15.,16.,17.],
                             'tip':[1.,1.5,2.,1.9,2.5,3.,3.5,4.]})
            eda_figures(df,audit(df),td)
            s=(Path(td)/'eda_numeric.svg').read_text()
            self.assertIn('total_bill',s)
            self.assertIn('tip',s)
            self.assertNotIn('>F1<',s)
            self.assertNotIn('>F2<',s)
            geometry_figures(df,{c:{'type':'numeric','role':'feature'} for c in df},td)
            svg=(Path(td)/'eda_geometry.svg').read_text()
            self.assertIn('total_bill',svg)
            self.assertIn('tip',svg)

    def test_posthoc_numeric_and_association_are_observation_aligned(self):
        raw=pd.DataFrame({'x':[1.,2.,3.,4.,5.,6.],
                          'tip':[10.,20.,30.,40.,50.,60.],
                          'place':['A','A','B','B','A','B']})
        labels=np.array([0,0,0,1,1,1])
        txt=render_numeric_comparisons(raw,labels,['x'],['tip'])
        self.assertIn('`tip`',txt)
        self.assertIn('**未參與分群**',txt)
        self.assertIn('平均值最高',txt)
        txt=supplementary_exploration(raw,labels,['tip','place'],[['x','tip']])
        self.assertIn('Spearman',txt)
        self.assertIn('1.000',txt)
        self.assertIn('place',txt)
        self.assertEqual(NAMES['pam'],'K-medoids (PAM 演算法)')

if __name__=='__main__': unittest.main()
