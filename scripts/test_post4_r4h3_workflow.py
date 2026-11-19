"""R4H.3: Stage 3 is planning-only; Stage 4 hosts execution and model review.

QA-only decisions are synthetic and must never be mistaken for user approval.
"""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from clustering_native.cli import dispatch
from clustering_native.session import Session
from clustering_native.engine import fit_one
from clustering_native.education import planned_evidence
from clustering_native.core import Gate


class R4H3Workflow(unittest.TestCase):
    def yes(self, s, item, token):
        return s.respond(item, token, 'A', 'qa-r4h3-'+item+'-'+str(len(s.gate.state['events'])), source='qa_fixture')

    def create_to_candidate_plan(self, path):
        # 18 actual points in three compact regions, no drawn/simulated research evidence.
        raw=pd.DataFrame({'bill':[1.,1.1,1.2,1.3,1.4,1.5,4.,4.1,4.2,4.3,4.4,4.5,8.,8.1,8.2,8.3,8.4,8.5],
                          'tip':[2.,2.1,2.2,2.3,2.4,2.5,5.,5.1,5.2,5.3,5.4,5.5,9.,9.1,9.2,9.3,9.4,9.5]})
        raw.to_csv(path/'input.csv',index=False)
        # Historical R4H.3 workflow regression: explicitly create the legacy
        # results-gated Stage 4 variant; the new CLI creates R4H.4 auto mode.
        s=Session.create(path/'input.csv',path/'study',require_role_confirmation=False,
                         stage4_candidate_execution=True,auto_stage4_diagnostics=False)
        self.assertEqual(s.gate.state['phase'],'S1_REVIEW')
        self.assertTrue(s.gate.state['stage4_candidate_execution'])
        self.assertFalse(s.gate.state.get('stage4_auto_diagnostics',False))
        plan={'schema':{c:{'type':'numeric','role':'feature'} for c in raw},
              'weights':{c:1.0 for c in raw},'actions':{c:{} for c in raw}}
        self.yes(s,'preprocess',s.propose_preprocessing(plan))
        self.yes(s,'method',s.propose_method('pam'))
        configs=[{'metric':'euclidean','k':k,'max_swaps':15} for k in (2,3)]
        sources=[{k:{'source':'exploratory_default','rationale':'QA selected bounded scope'} for k in config}
                 for config in configs]
        props=dict(configs=configs,basis='exploratory-only',evidence='Exploratory real feature scatter; no natural K claim',
                   budget={'max_rows':30,'memory_mb':256,'seconds_per_fit':12,'max_candidates':5},
                   diagnostics_plan={'fraction':.8,'repeats':2,'seed':14,'policy':'fixed_full_data_preprocessing'},
                   parameter_sources=sources,search_rationale='K2 and K3: explicit short contrast',
                   boundary_limitations='Only these K values are evaluated',initialization_plan=None)
        token=s.propose_candidates(**props)
        return s,token

    def test_stage3_plan_only_and_stage4_real_fit_result_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            s,tok=self.create_to_candidate_plan(Path(temp))
            self.assertEqual(s.gate.state['phase'],'S3_PERMISSION')
            stage3=dispatch({'action':'stage_attachments','session':str(s.directory),'stage':3})
            self.assertEqual(stage3['attachment_count'],0)
            self.assertEqual(stage3['figure_status'],'NOT_APPLICABLE_PLANNING_ONLY')
            with self.assertRaises(PermissionError):s.fit_candidates()
            self.yes(s,'candidates',tok)
            self.assertEqual(s.gate.state['phase'],'S4_EXECUTE')
            with self.assertRaises(PermissionError):s.diagnose_approved()
            s.fit_candidates()
            self.assertEqual(s.gate.state['phase'],'S4_RESULTS')
            self.assertFalse((s.directory/'candidate_figures'/'stage3_candidate_preview.png').exists())
            self.assertEqual(len(s.state['results']),2)
            self.assertNotIn('calinski_harabasz',s.state['results'][0]['metrics'])
            self.assertNotIn('davies_bouldin',s.state['results'][0]['metrics'])
            with self.assertRaises(PermissionError):s.diagnose_approved()
            self.yes(s,'results',s.gate.state['proposals']['results']['token'])
            self.assertEqual(s.gate.state['phase'],'S4_REVIEW')
            self.assertNotIn('calinski_harabasz',s.gate.state['payloads']['candidates']['planned_metric_evidence'])
            self.assertNotIn('davies_bouldin',s.gate.state['payloads']['candidates']['planned_metric_evidence'])
            # A real fitted candidate is reused. Do not inflate test cost by
            # spawning subsampling child processes; verify the actual Stage4
            # diagnostics pipeline from fixed recorded QA resamples instead.
            def qa_stability(raw,model,plan,method,result,budget,fraction,repeats,seed,policy,**kwargs):
                return {'name':'common-ID subsampling ARI', 'runs':[{'repeat':i,'ari':.95,'error':None,
                       'row_positions':list(range(13))} for i in range(repeats)], 'failures':0}
            with patch('clustering_native.engine.stability',side_effect=qa_stability):
                diag=s.diagnose_approved()
            self.assertEqual(len(diag['stability']),2)
            evidence=json.loads((s.directory/'selection_evidence'/'selection_evidence.json').read_text())
            self.assertEqual(evidence['metric_disclosure_audit']['status'],'ALL_REPORTED_METRICS_PREDISCLOSED')
            for row in evidence['candidate_comparison']:
                self.assertNotIn('calinski_harabasz',row['metrics'])
                self.assertNotIn('davies_bouldin',row['metrics'])
            self.assertTrue((s.directory/'selection_evidence'/'quality_and_sizes.png').exists())
            self.assertTrue((s.directory/'selection_evidence'/'stability.png').exists())
            self.assertEqual(dispatch({'action':'stage_attachments','session':str(s.directory),'stage':4})['stage'],4)
            explanation={'chosen_reason':'QA group sizes and real feature pattern',
                         'candidate_reasons':{'0':'Insufficient description for third block','1':'Fits three observed blocks'},
                         'conflicts':'No accepted universal K threshold',
                         'limitations':'QA only, limited candidate range, sample small'}
            self.yes(s,'final',s.propose_final(1,'QA choose K3',explanation))
            s.report(Path(temp)/'report')
            text=(Path(temp)/'report'/'analysis.md').read_text()
            s3,s4=text.split('## Stage 4 — ',1)
            s3=s3.split('## Stage 3 — ',1)[1]
            self.assertIn('規劃與批准',s3)
            self.assertNotIn('實際群數',s3)
            self.assertIn('實際群數',s4)
            self.assertNotIn('Calinski–Harabasz',text)
            self.assertNotIn('Davies–Bouldin',text)
            metrics=(Path(temp)/'report'/'candidate_metrics.csv').read_text()
            self.assertNotIn('calinski_harabasz',metrics)
            self.assertNotIn('davies_bouldin',metrics)
            self.assertTrue((Path(temp)/'report'/'analysis_offline.html').exists())

    def test_stage4_expansion_needs_new_stage3_approval_and_reuses_models(self):
        from clustering_native.engine import bounded_fit
        with tempfile.TemporaryDirectory() as temp:
            s,tok=self.create_to_candidate_plan(Path(temp))
            self.yes(s,'candidates',tok)
            s.fit_candidates()
            self.yes(s,'results',s.gate.state['proposals']['results']['token'])
            def qa_stability(raw,model,plan,method,result,budget,fraction,repeats,seed,policy,**kwargs):
                return {'name':'common-ID subsampling ARI',
                        'runs':[{'repeat':i,'ari':.9,'error':None,'row_positions':list(range(13))}
                                for i in range(repeats)],'failures':0}
            with patch('clustering_native.engine.stability',side_effect=qa_stability):
                first=s.diagnose_approved()
            old=first['stability']
            new={'metric':'euclidean','k':4,'max_swaps':15}
            provenance={key:{'source':'user_specified','rationale':'QA authorized bounded expansion'}
                        for key in new}
            proposal=s.propose_candidate_expansion([new],[provenance],
                          'QA search range extension after reviewing Stage 4 candidates')
            self.assertEqual(s.gate.state['phase'],'S3_PERMISSION')
            self.assertEqual(s.state['results'],[])
            with self.assertRaises(PermissionError):s.fit_candidates()
            self.yes(s,'candidates',proposal['token'])
            self.assertEqual(s.gate.state['phase'],'S4_EXECUTE')
            with patch('clustering_native.engine.bounded_fit',wraps=bounded_fit) as spy:
                s.fit_candidates()
            self.assertEqual(spy.call_count,1, 'Previously approved full-data fits must be reused')
            self.assertEqual(s.gate.state['phase'],'S4_RESULTS')
            self.yes(s,'results',s.gate.state['proposals']['results']['token'])
            with patch('clustering_native.engine.stability',side_effect=qa_stability) as stab:
                updated=s.diagnose_approved()
            self.assertEqual(stab.call_count,1, 'Previously approved stability batches must be reused')
            self.assertEqual(updated['stability'][:2],old)
            self.assertEqual(len(updated['stability']),3)

    def test_existing_sessions_keep_their_serialized_gate_transitions(self):
        old=Gate().state
        gate=Gate(old)
        self.assertEqual(gate.TRANSITIONS['candidates'][2],'S3_EXECUTE')
        self.assertEqual(gate.TRANSITIONS['results'][1],'S3_RESULTS')
        new=Gate({**old,'stage4_candidate_execution':True})
        self.assertEqual(new.TRANSITIONS['candidates'][2],'S4_EXECUTE')
        self.assertEqual(new.TRANSITIONS['results'][1],'S4_RESULTS')
        self.assertEqual(gate.TRANSITIONS['results'][1],'S3_RESULTS')

    def test_removed_metrics_are_not_predisclosed_or_computed(self):
        from clustering_native.education import planned_evidence
        cfg={'metric':'euclidean','k':2,'init':'k-means++','n_init':2,'algorithm':'lloyd','random_state':17,
             'tol':1e-4,'max_iter':50}
        evidence=planned_evidence('kmeans',[cfg])
        self.assertEqual(set(evidence)&{'calinski_harabasz','davies_bouldin'},set())
        df=pd.DataFrame({'x':[-4,-3.9,-3.8,4,4.1,4.2],'y':[0.,.1,.2,0.,.1,.2]})
        plan={c:{'type':'numeric','role':'feature'} for c in df}
        out=fit_one(df,plan,{c:1.0 for c in df},'kmeans',cfg,
                    {'max_rows':30,'max_candidates':3,'seconds_per_fit':10,'memory_mb':256})
        self.assertIn('silhouette',out['metrics'])
        self.assertNotIn('calinski_harabasz',out['metrics'])
        self.assertNotIn('davies_bouldin',out['metrics'])

if __name__=='__main__':unittest.main()
