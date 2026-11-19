"""R4E: genuine Stage3/4 responsibility boundaries, delivery figures, and expansion reuse."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from clustering_native.session import Session


class R4EStageBoundary(unittest.TestCase):
    def study(self,root):
        rng=np.random.default_rng(13)
        X=np.vstack((rng.normal([-1.5,0],[.11,.09],size=(12,2)),
                     rng.normal([1.5,0],[.1,.09],size=(12,2))))
        df=pd.DataFrame(X,columns=['x','y'])
        df.to_csv(root/'dataset.csv',index=False)
        s=Session.create(root/'dataset.csv',root/'session')
        plan={'schema':{c:{'type':'numeric','role':'feature'} for c in df},
              'weights':{c:1 for c in df},'actions':{c:{} for c in df}}
        token=s.propose_preprocessing(plan)
        self.yes(s,'preprocess',token)
        self.yes(s,'method',s.propose_method('dbscan'))
        configs=[{'metric':'euclidean','eps':.27,'min_samples':3},
                 {'metric':'euclidean','eps':.38,'min_samples':3}]
        return s,configs
    def yes(self,s,item,token):
        return s.respond(item,token,'A','qa-r4e-'+item+str(len(s.gate.state['events'])),source='qa_fixture')
    def candidate_plan(self,configs):
        return dict(configs=configs,basis='exploratory-only',evidence='R4E bounded QA',
            budget={'max_rows':30,'memory_mb':256,'seconds_per_fit':8,'max_candidates':5},
            diagnostics_plan={'fraction':.8,'repeats':2,'seed':12,'policy':'fixed_full_data_preprocessing'},
            parameter_sources=[{k:{'source':'exploratory_default','rationale':'QA exploratory values'} for k in c}
                               for c in configs],
            search_rationale='Two reasonable eps candidates, no fixed natural K',
            boundary_limitations='Boundaries only, no global winner',initialization_plan=None)

    def test_stage4_executes_real_stability_and_delivers_actual_figures(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            s,configs=self.study(root)
            self.yes(s,'candidates',s.propose_candidates(**self.candidate_plan(configs)))
            s.fit_candidates()
            self.assertIsNone(s.state.get('stage3_stability_bound'))
            self.assertFalse(s.state.get('stage3_stability'))
            self.assertIsNone(s.state.get('diagnostics'))
            self.assertFalse(s.state.get('diagnostics_budget_consumed'))
            self.assertFalse((s.directory/'candidate_figures'/'candidate_quality.svg').exists())
            self.assertTrue((s.directory/'candidate_figures'/'stage3_candidate_preview.png').exists())
            from clustering_native.cli import dispatch
            with self.assertRaises(PermissionError):
                dispatch({'action':'stage_attachments','session':str(s.directory),'stage':4})
            self.yes(s,'results',s.gate.state['proposals']['results']['token'])
            output=s.diagnose_approved()
            self.assertEqual(len(output['stability']),2)
            self.assertTrue(any(e['action']=='stage4_stability_evaluated' for e in s.gate.state['events']))
            self.assertTrue((s.directory/'selection_evidence'/'candidate_partitions.png').is_file())
            self.assertTrue((s.directory/'selection_evidence'/'stability.png').is_file())
            batch=dispatch({'action':'stage_attachments','session':str(s.directory),'stage':4})
            self.assertIn('candidate_partitions.png',str(batch))
            explanation={'chosen_reason':'Geometry and noise review favors D2 in QA',
                         'candidate_reasons':{'0':'Alternative for comparison','1':'Selected reference'},
                         'conflicts':'Silhouette and ARI comparison is descriptive only',
                         'limitations':'Only two eps values tested; arbitrary exploratory range'}
            self.yes(s,'final',s.propose_final(1,'QA D2 final review',explanation))
            self.assertTrue((s.directory/'stage4_final_evidence'/'stage4_selected_partition.png').is_file())
            batch=dispatch({'action':'stage_attachments','session':str(s.directory),'stage':4})
            self.assertIn('stage4_selected_partition.png',str(batch))
            s.report(root/'report')
            report=(root/'report'/'analysis.md').read_text(encoding='utf-8')
            before,after=report.split('## Stage 4 — ',1)
            self.assertNotIn('重抽樣 ARI=',before)
            self.assertNotIn('Silhouette（越高通常越好） | 群數',before)
            self.assertIn('candidate_partitions.png',after)
            self.assertIn('stage4_selected_partition.png',after)
            self.assertIn('D1',after)
            self.assertIn('D2',after)
            self.assertIn('實際群組形狀與幾何研究發現',after)
            for img in ('selection_evidence/candidate_partitions.png','figures/stage4_selected_partition.png'):
                self.assertTrue((root/'report'/img).is_file())
            self.assertEqual((root/'report'/'analysis_offline.html').read_text().count('<details class="code-block">'),5)

    def test_kmeans_stage4_stability_and_initialization_without_duplicate_full_fits(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            x=np.concatenate((np.linspace(-3,-2.8,8),np.linspace(2.8,3,8)))
            df=pd.DataFrame({'x':x,'y':np.linspace(-.1,.1,16)})
            df.to_csv(root/'input.csv',index=False)
            s=Session.create(root/'input.csv',root/'study')
            plan={'schema':{c:{'type':'numeric','role':'feature'} for c in df},
                  'actions':{c:{} for c in df},'weights':{c:1 for c in df}}
            self.yes(s,'preprocess',s.propose_preprocessing(plan))
            self.yes(s,'method',s.propose_method('kmeans'))
            configs=[{'metric':'euclidean','k':k,'init':'k-means++','n_init':2,
                      'algorithm':'lloyd','random_state':7,'tol':1e-4,'max_iter':40}
                     for k in (2,3)]
            props=self.candidate_plan(configs)
            props['initialization_plan']={'seeds':[7,17]}
            self.yes(s,'candidates',s.propose_candidates(**props))
            s.fit_candidates()
            self.assertFalse(s.state.get('stage3_stability'))
            self.yes(s,'results',s.gate.state['proposals']['results']['token'])
            diagnostics=s.diagnose_approved()
            self.assertEqual(len(diagnostics['stability']),2)
            self.assertEqual(diagnostics['initialization']['status'],'COMPUTED')
            self.assertEqual(len(diagnostics['initialization']['runs']),4)
            self.assertTrue((s.directory/'selection_evidence'/'candidate_partitions.png').is_file())

    def test_authorized_incremental_extension_reuses_stage4_subsampling(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            s,configs=self.study(root)
            self.yes(s,'candidates',s.propose_candidates(**self.candidate_plan(configs)))
            s.fit_candidates();self.yes(s,'results',s.gate.state['proposals']['results']['token'])
            before=s.diagnose_approved()
            original=json.loads(json.dumps(before['stability']))
            new={'metric':'euclidean','eps':.5,'min_samples':3}
            source={k:{'source':'user_specified','rationale':'QA additional approved upper radius'} for k in new}
            proposal=s.propose_candidate_expansion([new],[source],'QA upper epsilon exploratory check')
            self.assertEqual(proposal['new_candidates'],1)
            self.assertEqual(s.gate.state['phase'],'S3_PERMISSION')
            self.assertEqual(s.state['results'],[])
            self.yes(s,'candidates',proposal['token']);s.fit_candidates()
            self.assertEqual(len(s.state['results']),3)
            self.assertFalse(s.state.get('stage3_stability'))
            self.yes(s,'results',s.gate.state['proposals']['results']['token'])
            after=s.diagnose_approved()
            self.assertEqual(after['stability'][:2],original)
            recent=[e for e in s.gate.state['events'] if e['action']=='stage4_stability_evaluated']
            self.assertEqual(recent[-1]['reused_batches'],2)
            self.assertEqual(recent[-1]['executed_batches'],1)

if __name__=='__main__': unittest.main()
