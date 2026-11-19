"""R4H.4 final gates + EDA anchored K, explicit QA fixtures only.

QA synthetic points are never represented as real research images.
"""
import tempfile,unittest,copy,os
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.datasets import load_iris
from clustering_native.planning import observed_projection_gap_hint,exploratory_draft
from clustering_native.session import Session
from clustering_native.cli import dispatch
from clustering_native.core import Gate

class DraftSession:
    def __init__(self,X,method='pam'):
        self.X=X; self._method=method
        self._plan={'schema':{c:{'type':'numeric'} for c in X},'weights':{c:1 for c in X}}
        self.state={'assessment':{'gower_preflight':{'status':'PASS'}},'eda_handoff':{}}
    def model(self):return self.X
    def plan(self):return self._plan
    def method(self):return self._method

class R4H4Repair(unittest.TestCase):
    def test_iris_prefit_visual_support_drives_k_neighborhood(self):
        bunch=load_iris(as_frame=True)
        X=bunch.data.rename(columns={'sepal length (cm)':'sepal_length_cm', 'sepal width (cm)':'sepal_width_cm',
          'petal length (cm)':'petal_length_cm','petal width (cm)':'petal_width_cm'})
        d=DraftSession(X)
        hint=observed_projection_gap_hint(X,d.plan())
        self.assertEqual(hint['status'],'TENTATIVE_VISUAL_REGIONS')
        self.assertEqual(hint['tentative_regions'],2)
        self.assertEqual(set(hint['features']),{'petal_length_cm','petal_width_cm'})
        draft=exploratory_draft(d)
        self.assertEqual([row['k'] for row in draft['configs']],[2,3])
        self.assertEqual(draft['basis'],'evidence-supported')
        self.assertIn('petal_length_cm',draft['search_rationale'])
        self.assertIn('petal_width_cm',draft['search_rationale'])

    def test_three_regions_and_inconclusive_have_distinct_plans(self):
        X=pd.DataFrame({'x':np.r_[np.arange(40)*.03-7,np.arange(40)*.03,np.arange(40)*.03+7],
                        'y':np.r_[np.arange(40)*.02-7,np.arange(40)*.02,np.arange(40)*.02+7]})
        triad=exploratory_draft(DraftSession(X))
        self.assertEqual([r['k'] for r in triad['configs']],[2,3,4])
        self.assertIn('約 3 個分離區域',triad['search_rationale'])
        flat=pd.DataFrame({'x':np.linspace(0,1,150),'y':np.mod(np.arange(150)*73,149)/149})
        ambiguous=exploratory_draft(DraftSession(flat))
        self.assertNotEqual([r['k'] for r in ambiguous['configs']],[2,3,4])
        self.assertIn('未取得足以定位',ambiguous['search_rationale'])
        self.assertEqual(ambiguous['basis'],'exploratory-only')

    def test_existing_session_still_requires_old_result_gate(self):
        old=Gate({**Gate().state,'stage4_candidate_execution':True})
        self.assertEqual(old.TRANSITIONS['results'][1],'S4_RESULTS')
        self.assertIn('results',old.PHASE_REQUIREMENTS['S4_REVIEW'])
        new=Gate({**Gate().state,'stage4_candidate_execution':True,'stage4_auto_diagnostics':True})
        self.assertNotIn('results',new.PHASE_REQUIREMENTS['S4_REVIEW'])
        self.assertNotIn('results',new.PHASE_REQUIREMENTS['S5_READY'])

    def yes(self,s,item,token):
        return s.respond(item,token,'A','qa-r4h4-'+item+'-'+str(len(s.gate.state['events'])),source='qa_fixture')

    def new_case(self,path):
        # QA fixture, never exported as user research evidence.
        raw=pd.DataFrame({'x':[-3,-2.9,-2.8,-2.7,-2.6,-2.5,0.,.1,.2,.3,.4,.5,3.,3.1,3.2,3.3,3.4,3.5],
                          'y':[-3,-2.9,-2.8,-2.7,-2.6,-2.5,0.,.1,.2,.3,.4,.5,3.,3.1,3.2,3.3,3.4,3.5]})
        raw.to_csv(path/'raw.csv',index=False)
        d=dispatch({'action':'create','session':str(path/'session'),'csv':str(path/'raw.csv'),'require_feature_roles':False})
        s=Session(path/'session');self.assertTrue(s.gate.state['stage4_auto_diagnostics'])
        plan={'schema':{c:{'type':'numeric','role':'feature'} for c in raw},'weights':{c:1. for c in raw},'actions':{c:{} for c in raw}}
        self.yes(s,'preprocess',s.propose_preprocessing(plan))
        self.yes(s,'method',s.propose_method('pam'))
        config=[{'metric':'euclidean','k':k,'max_swaps':20} for k in [2,3]]
        sources=[{p:{'source':'user_specified','rationale':'QA bounded scope'} for p in c} for c in config]
        proposal=s.propose_candidates(config,'exploratory-only','Three observed QA regions',
                    {'memory_mb':256,'seconds_per_fit':12,'max_rows':30,'max_candidates':4},
                    {'fraction':.8,'repeats':2,'seed':17,'policy':'fixed_full_data_preprocessing'},
                    sources,'QA approved K2,K3','Limited QA candidates only')
        return s,proposal

    def test_new_stage4_auto_executes_real_ari_without_result_gate(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td);s,tok=self.new_case(path)
            with self.assertRaises(PermissionError):s.fit_candidates()
            self.yes(s,'candidates',tok)
            out=s.fit_candidates()
            self.assertEqual(out['status'],'STAGE4_DIAGNOSTICS_COMPLETE')
            self.assertEqual(s.gate.state['phase'],'S4_REVIEW')
            self.assertNotIn('results',s.gate.state['approvals'])
            self.assertNotIn('results',s.gate.state['payloads'])
            self.assertEqual(len(s.state['diagnostics']['stability']),2)
            for ev in s.state['diagnostics']['stability']:
                self.assertEqual(len(ev['runs']),2)
            self.assertTrue((s.directory/'selection_evidence'/'stability.png').exists())
            with self.assertRaises(PermissionError):s.fit_candidates()
            with self.assertRaises(PermissionError):s.diagnose_approved()
            with self.assertRaises(PermissionError):s.confirm_results('fake',{} )
            explanation={'chosen_reason':'Three visually separated QA groups',
                 'candidate_reasons':{'0':'Fewer groups','1':'Three groups'},
                 'conflicts':'Candidates are limited','limitations':'QA small sample only'}
            token=s.propose_final(1,'QA K3',explanation)
            self.assertNotIn('final',s.gate.state['approvals'])
            self.assertEqual(s.gate.state['phase'],'S4_REVIEW')
            self.assertTrue(token)
            # User approval is indispensable even though Stage4 work auto-continued.
            self.yes(s,'final',token)
            self.assertEqual(s.gate.state['phase'],'S5_READY')
            s.report(path/'report')
            self.assertTrue((path/'report'/'analysis_offline.html').exists())

    def test_new_auto_stage4_extension_requires_fresh_scope_and_reuses_evaluations(self):
        from unittest.mock import patch
        from clustering_native.engine import bounded_fit,stability
        with tempfile.TemporaryDirectory() as td:
            path=Path(td);s,tok=self.new_case(path)
            self.yes(s,'candidates',tok)
            s.fit_candidates()
            before=copy.deepcopy(s.state['diagnostics']['stability'])
            new={'metric':'euclidean','k':4,'max_swaps':20}
            provenance={p:{'source':'user_specified','rationale':'QA bounded expansion'} for p in new}
            expansion=s.propose_candidate_expansion([new],[provenance],
                'Boundary comparison needs one more candidate')
            self.assertEqual(s.gate.state['phase'],'S3_PERMISSION')
            self.assertFalse(s.state['results'])
            with self.assertRaises(PermissionError):s.fit_candidates()
            self.yes(s,'candidates',expansion['token'])
            with patch('clustering_native.engine.bounded_fit',wraps=bounded_fit) as fit_spy, \
                 patch('clustering_native.engine.stability',wraps=stability) as ari_spy:
                output=s.fit_candidates()
            self.assertEqual(output['status'],'STAGE4_DIAGNOSTICS_COMPLETE')
            self.assertEqual(fit_spy.call_count,1)
            self.assertEqual(ari_spy.call_count,1)
            self.assertEqual(s.state['diagnostics']['stability'][:2],before)
            self.assertEqual(s.gate.state['phase'],'S4_REVIEW')
            self.assertNotIn('results',s.gate.state['approvals'])

    def test_results_integrity_bound_even_without_intermediate_approval(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td);s,tok=self.new_case(path)
            self.yes(s,'candidates',tok)
            s.fit_candidates()
            s.state['results'][0]['labels'][0]=999
            with self.assertRaises(PermissionError):s.diagnose_approved()
            self.assertEqual(s.gate.state['phase'],'S3_PLAN')

if __name__=='__main__': unittest.main()
