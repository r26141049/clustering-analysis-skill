"""R4G P0 regression: real saved Session, exact identity, no synthetic approval."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from clustering_native.cli import dispatch
from clustering_native.session import Session
from clustering_native.session_store import SessionUnavailable, preserve


class DurableSessionAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.store=self.base/'persisted_store'
        self.patcher=patch.dict(os.environ, {'CLUSTERING_STATE_ROOT':str(self.store)})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        values=np.vstack((np.random.default_rng(10).normal([-2,0],.1,(12,2)),
                          np.random.default_rng(11).normal([2,0],.1,(12,2))))
        self.csv=self.base/'tips_like.csv'
        pd.DataFrame(values,columns=['x','y']).to_csv(self.csv,index=False)
        self.volatile=self.base/'temporary_execution'/'research'

    def plan(self):
        return {'schema':{c:{'type':'numeric','role':'feature'} for c in ('x','y')},
                'weights':{'x':1,'y':1},'actions':{'x':{},'y':{}}}

    def qa_approve(self,s,item,token):
        return s.respond(item,token,'A','qa-r4g-'+item+'-'+str(len(s.gate.state['events'])),source='qa_fixture')

    def build_stage3_results(self):
        s=Session.create(self.csv,self.volatile)
        self.qa_approve(s,'preprocess',s.propose_preprocessing(self.plan()))
        observations={k:{'value':'uncertain','reason':'No geometry inference from a two-sample QA figure'}
                      for k in ('nonconvex','curved','unequal_density','isolated_regions','coarse_fine_structure')}
        s.record_visual_evidence(observations,s.state['geometry_paths'],
                                 'Only figures from the currently approved research are used')
        self.qa_approve(s,'method',s.propose_method('dbscan'))
        configs=[{'metric':'euclidean','eps':.3,'min_samples':3},
                 {'metric':'euclidean','eps':.55,'min_samples':3}]
        kw={'configs':configs,'basis':'exploratory-only','evidence':'QA explicit 2-candidate budget',
            'budget':{'max_rows':30,'memory_mb':256,'seconds_per_fit':8,'max_candidates':5},
            'diagnostics_plan':{'fraction':.8,'repeats':2,'seed':19,'policy':'fixed_full_data_preprocessing'},
            'parameter_sources':[{k:{'source':'exploratory_default','rationale':'QA bounded candidate'} for k in c}
                                for c in configs],
            'search_rationale':'QA does not infer natural cluster counts',
            'boundary_limitations':'No global best candidate inferred','initialization_plan':None}
        self.qa_approve(s,'candidates',s.propose_candidates(**kw))
        s.fit_candidates()
        self.assertEqual(s.gate.state['phase'],'S3_RESULTS')
        self.assertEqual(len(s.state['results']),2)
        preserve(s.directory)
        return s

    def test_creation_without_session_path_survives_independent_dispatch(self):
        created=dispatch({'action':'create','csv':str(self.csv),'require_feature_roles':False})
        self.assertEqual(created['phase'],'S1_REVIEW')
        current=dispatch({'action':'resume_current'})
        self.assertEqual(current['phase'],'S1_REVIEW')
        # New Python process, no remembered in-memory Session object.
        run=subprocess.run([sys.executable,'-m','clustering_native'],
                           input=json.dumps({'action':'resume_current'}),
                           text=True,capture_output=True,env=dict(os.environ),check=False)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(json.loads(run.stdout)['phase'],'S1_REVIEW')
        self.assertEqual(current['resume']['approvals'],[])
        self.assertEqual(current['resume']['model_fits'],0)
        dispatch({'action':'propose_preprocessing','plan':self.plan()})
        current=dispatch({'action':'resume_current'})
        self.assertIn('preprocess',current['resume']['pending_decisions'])
        self.assertEqual(current['resume']['approvals'],[])
        # A genuinely fresh response, not a reload, advances to Stage 2.
        advanced=dispatch({'action':'respond_current','response':'A'})
        self.assertEqual(advanced['phase'],'S2_REVIEW')
        self.assertIn('preprocess',dispatch({'action':'resume_current'})['resume']['approvals'])

    def test_stage3_checkpoint_resumes_stage4_only_after_fresh_reply(self):
        s=self.build_stage3_results()
        old=Path(s.directory)
        sid=s.gate.state['session_id']
        originally_fitted=json.loads(json.dumps(s.state['results']))
        stale=self.base/'stale_original_copy'
        shutil.copytree(old,stale)
        shutil.rmtree(old)
        # Exact retired absolute path is allowed to match the saved origin.
        resumed=dispatch({'action':'resume_current','session':str(old)})
        self.assertEqual(resumed['phase'],'S3_RESULTS')
        self.assertEqual(resumed['resume']['session_id'],sid)
        self.assertEqual(resumed['resume']['approvals'],['candidates','method','preprocess'])
        self.assertIn('results',resumed['resume']['pending_decisions'])
        self.assertEqual(resumed['resume']['model_fits'],2)
        self.assertFalse((self.store/'research.json').exists())
        # A read-only attempt must not silently progress or run ARI.
        self.assertEqual(dispatch({'action':'resume_current'})['phase'],'S3_RESULTS')
        with self.assertRaises(PermissionError):
            dispatch({'action':'respond_current','response':'不同意，請不要執行'})
        self.assertEqual(dispatch({'action':'resume_current'})['phase'],'S3_RESULTS')
        # The restored approvals were QA fixtures; they may only be followed
        # by another explicitly marked QA decision, never fake user consent.
        from clustering_native.session_store import resolve_session
        from clustering_native.runner import auto_continue
        new=Session(resolve_session(str(old)))
        self.qa_approve(new,'results',new.gate.state['proposals']['results']['token'])
        followup=auto_continue(new)
        self.assertEqual(followup['stop'],'FINAL_MODEL_DECISION_REQUIRED')
        self.assertEqual(new.gate.state['phase'],'S4_REVIEW')
        self.assertEqual(new.gate.state['session_id'],sid)
        self.assertEqual(new.state['results'],originally_fitted)
        self.assertEqual(len(new.state['diagnostics']['stability']),2)
        self.assertEqual(new.gate.state['phase'],'S4_REVIEW')
        self.assertTrue((new.directory/'selection_evidence'/'candidate_partitions.png').is_file())
        self.assertTrue((new.directory/'approved_eda_figures'/'eda_geometry.png').is_file())
        # A stale original directory that reappears cannot roll Gate backward.
        shutil.copytree(stale,old)
        self.assertEqual(resolve_session(str(old)),new.directory)

    def test_pam_gower_stage3_to_stage4_checkpoint_does_not_refit(self):
        """Restaurant-Tips-like mixed numeric/nominal actual PAM/Gower path."""
        root=self.base
        df=pd.DataFrame({'total_bill':[10,11,12,13,24,25,26,27,38,39,40,41],
                         'tip':[1.,1.1,1.2,1.1,3.,3.1,3.2,3.,5.2,5.3,5.4,5.2],
                         'day':['Fri']*4+['Sat']*4+['Sun']*4})
        csv=root/'mixed_tips.csv';df.to_csv(csv,index=False)
        s=Session.create(csv,self.volatile)
        plan={'schema':{c:{'type':'nominal' if c=='day' else 'numeric','role':'feature'} for c in df},
              'actions':{c:{} for c in df}, 'weights':{c:1 for c in df}}
        self.qa_approve(s,'preprocess',s.propose_preprocessing(plan))
        self.qa_approve(s,'method',s.propose_method('pam'))
        configs=[{'metric':'gower','k':2,'max_swaps':20},
                 {'metric':'gower','k':3,'max_swaps':20}]
        spec={'configs':configs,'basis':'exploratory-only','evidence':'QA mixed-type study',
              'budget':{'max_rows':30,'memory_mb':256,'seconds_per_fit':8,'max_candidates':4},
              'diagnostics_plan':{'fraction':.8,'repeats':2,'seed':19,'policy':'fixed_full_data_preprocessing'},
              'parameter_sources':[{key:{'source':'exploratory_default','rationale':'QA bounded candidate'}
                                    for key in cfg} for cfg in configs],
              'search_rationale':'QA 2/3 candidates, no natural K claim',
              'boundary_limitations':'Only QA candidates','initialization_plan':None}
        self.qa_approve(s,'candidates',s.propose_candidates(**spec))
        s.fit_candidates()
        original=json.loads(json.dumps(s.state['results']))
        self.assertEqual(s.gate.state['phase'],'S3_RESULTS')
        preserve(s.directory)
        old=s.directory
        shutil.rmtree(old)
        checkpoint=dispatch({'action':'resume_current','session':str(old)})
        self.assertEqual(checkpoint['resume']['model_fits'],2)
        self.assertIn('results',checkpoint['resume']['pending_decisions'])
        from clustering_native.session_store import resolve_session
        from clustering_native.runner import auto_continue
        restored=Session(resolve_session(str(old)))
        self.assertEqual(restored.state['results'],original)
        self.qa_approve(restored,'results',restored.gate.state['proposals']['results']['token'])
        self.assertEqual(auto_continue(restored)['stop'],'FINAL_MODEL_DECISION_REQUIRED')
        self.assertEqual(restored.state['results'],original)
        self.assertEqual(len(restored.state['diagnostics']['stability']),2)
        self.assertTrue((restored.directory/'selection_evidence'/'quality_and_sizes.png').is_file())

    def test_missing_or_mismatched_checkpoint_never_recovers_approval(self):
        with self.assertRaises(SessionUnavailable):
            dispatch({'action':'resume_current'})
        s=self.build_stage3_results()
        preserve(s.directory)
        with self.assertRaises(SessionUnavailable):
            dispatch({'action':'resume_current','session':str(self.base/'unknown-study')})
        record=json.loads((self.store/'index.json').read_text())
        Path(record['studies'][record['current']]['snapshot'],'input.original.csv').write_text('tampered')
        with self.assertRaises(SessionUnavailable):
            dispatch({'action':'resume_current'})


if __name__ == '__main__':
    unittest.main()
