"""R2 gate and continuation regression. No real-user approval is simulated."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from clustering_native.session import Session
from clustering_native.runner import auto_continue
from clustering_native.planning import exploratory_draft
from clustering_native.core import digest


class R2Unit(unittest.TestCase):
    def test_no_approval_ever_generated_by_runner(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            pd.DataFrame({'x':[1.,2.,4.,8.,9.,10.], 'y':[1.,3.,2.,8.,9.,11.]}).to_csv(folder/'raw.csv',index=False)
            s=Session.create(folder/'raw.csv',folder/'session')
            before=dict(s.gate.state['approvals'])
            result=auto_continue(s)
            self.assertEqual(result['stop'],'USER_DECISION_REQUIRED')
            self.assertEqual(before,s.gate.state['approvals'])
            self.assertEqual(s.state['results'],[])

    def test_bound_expansion_reuses_original_only_after_new_gate(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            df=pd.DataFrame({'x':[0.,.2,.4, 5.,5.2,5.4, 10.,10.2,10.4,
                                  15.,15.2,15.4,20.,20.2,20.4,25.,25.2,25.4],
                             'y':[0.,.1,.2,5.,5.1,5.2,10.,10.1,10.2,
                                  15.,15.1,15.2,20.,20.1,20.2,25.,25.1,25.2]})
            df.to_csv(folder/'raw.csv',index=False)
            s=Session.create(folder/'raw.csv',folder/'session')
            plan={'schema':{c:{'type':'numeric','role':'feature'} for c in df},
                  'actions':{c:{} for c in df},'weights':{c:1 for c in df}}
            counter=0
            def yes(item,token):
                nonlocal counter
                counter+=1
                return s.respond(item,token,'A',f'fixture-r2-{counter}',source='qa_fixture')
            self.assertEqual(auto_continue(s)['phase'],'S1_REVIEW')
            yes('preprocess',s.propose_preprocessing(plan))
            auto=auto_continue(s)
            self.assertEqual(auto['phase'],'S2_REVIEW')
            self.assertEqual(auto['stop'],'USER_DECISION_REQUIRED')
            self.assertIn('method',s.gate.state['payloads'])
            yes('method',s.propose_method('hierarchical'))
            # If direct method entrypoint is used, new call must propose Stage 3.
            proposal=auto_continue(s)
            self.assertEqual(proposal['phase'],'S3_PERMISSION')
            self.assertGreater(len(s.gate.state['payloads']['candidates']['configs']),2)
            self.assertEqual(s.state['results'],[])
            # Make it an intentionally small fixed Stage 3 scope, to test actual expansion.
            s.revise(3,'QA: limit initial subset before new scoped approval')
            p=exploratory_draft(s)
            p['configs']=p['configs'][:2]
            p['parameter_sources']=p['parameter_sources'][:2]
            p['budget']['max_candidates']=5
            p['diagnostics_plan']['repeats']=2
            yes('candidates',s.propose_candidates(**p))
            self.assertEqual(s.gate.state['phase'],'S3_EXECUTE')
            auto=auto_continue(s)
            self.assertEqual(auto['phase'],'S3_RESULTS')
            self.assertEqual(len(s.state['results']),2)
            yes('results',s.gate.state['proposals']['results']['token'])
            auto=auto_continue(s)
            self.assertEqual(auto['phase'],'S4_REVIEW')
            self.assertIsNotNone(s.state['diagnostics'])
            old_results_hash=digest(s.state['results'])
            old_events=(folder/'session'/'fit_runtime_events.jsonl').read_text(encoding='utf-8')
            old_event_lines=len(old_events.splitlines())
            new_cfg={'metric':'euclidean','k':4,'linkage':'ward'}
            origins={k:{'source':'exploratory_default','rationale':'QA: boundary trigger; not natural K'} for k in new_cfg}
            revised=dict(p['budget']);revised['max_candidates']=5
            response=s.propose_candidate_expansion([new_cfg],[origins],
                'The highest assessed silhouette is at the tested upper K boundary', budget=revised)
            self.assertEqual(response['status'],'WAITING_NEW_STAGE3_EXECUTION_APPROVAL')
            self.assertEqual(s.gate.state['phase'],'S3_PERMISSION')
            self.assertEqual(s.state['results'],[])
            self.assertNotIn('candidates',s.gate.state['approvals'])
            self.assertEqual(len((folder/'session'/'fit_runtime_events.jsonl').read_text().splitlines()),old_event_lines)
            # Wrong stage cannot execute anything, and the new gate must be explicitly approved.
            with self.assertRaises(PermissionError): s.fit_candidates()
            yes('candidates',response['token'])
            auto=auto_continue(s)
            self.assertEqual(auto['phase'],'S3_RESULTS')
            self.assertEqual(len(s.state['results']),3)
            self.assertEqual(digest(s.state['results'][:2]),old_results_hash)
            self.assertIsNone(s.state.get('candidate_reuse_archive'))
            relevant=[e for e in s.gate.state['events'] if e['action']=='candidate_incremental_execution']
            self.assertEqual(relevant[-1]['reuse_count'],2)
            self.assertEqual(relevant[-1]['new_fit_count'],1)
            relevant=[e for e in s.gate.state['events'] if e['action']=='candidate_stability_incremental_execution']
            self.assertEqual(relevant[-1]['reused'],2)
            self.assertEqual(relevant[-1]['new_stability_batches'],1)
            self.assertEqual(len((folder/'session'/'fit_runtime_events.jsonl').read_text().splitlines())-old_event_lines,2)
            # Stage 4 still not entered without independent results confirmation.
            self.assertNotIn('results',s.gate.state['approvals'])

    def test_interrupted_batch_recovery_never_reuses_old_authorization(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            frame=pd.DataFrame({'x':[0.,0.2,0.5,4.,4.2,4.5,8.,8.2,8.5],
                                'y':[0.,.1,.2,4.,4.1,4.2,8.,8.1,8.2]})
            frame.to_csv(folder/'raw.csv',index=False)
            s=Session.create(folder/'raw.csv',folder/'session')
            plan={'schema':{c:{'type':'numeric','role':'feature'} for c in frame},
                  'actions':{c:{} for c in frame},'weights':{c:1 for c in frame}}
            s.respond('preprocess',s.propose_preprocessing(plan),'A','qa-recovery-1',source='qa_fixture')
            s.respond('method',s.propose_method('hierarchical'),'A','qa-recovery-2',source='qa_fixture')
            draft=exploratory_draft(s)
            draft['configs']=draft['configs'][:2]
            draft['parameter_sources']=draft['parameter_sources'][:2]
            token=s.propose_candidates(**draft)
            s.respond('candidates',token,'A','qa-recovery-3',source='qa_fixture')
            s.state['candidate_batch_consumed']=token
            s.save()  # Simulate a killed executor after durable budget consumption.
            with self.assertRaises(PermissionError):
                s.fit_candidates()
            recovery=s.recover_interrupted_execution('QA fault injection after consumption')
            self.assertTrue(recovery['original_execution_not_retried'])
            self.assertEqual(s.gate.state['phase'],'S3_PERMISSION')
            self.assertEqual(s.state['results'],[])
            self.assertNotIn('candidates',s.gate.state['approvals'])
            self.assertNotEqual(token,recovery['token'])
            with self.assertRaises(PermissionError):
                s.permit_execution(token,dict(value='APPROVE',stage=3,item='candidates',
                    response='A',source='qa_fixture',message_id='qa-recovery-old'))
            self.assertEqual(auto_continue(s)['stop'],'USER_DECISION_REQUIRED')

    def test_planner_fail_closed_on_invalid_data(self):
        from clustering_native.planning import exploratory_draft
        # No silent fit or permission if too few observations.
        class Stub:
            def model(self):return pd.DataFrame({'x':[1.,2.,3.]})
            def plan(self):return {'schema':{'x':{'type':'numeric'}},'weights':{'x':1}}
            def method(self):return 'kmeans'
            state={}
        with self.assertRaisesRegex(ValueError,'At least five'):
            exploratory_draft(Stub())

if __name__=='__main__':unittest.main()
