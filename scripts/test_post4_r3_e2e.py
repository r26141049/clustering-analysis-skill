"""Small strict R3 Stage 1--5 QA with hash-bound metric contrasts and report."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from clustering_native.session import Session
from clustering_native.planning import exploratory_draft

class StageFiveReportR3(unittest.TestCase):
    def test_metric_conflicts_and_sensitivity_survive_real_stage_five(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            df=pd.DataFrame({'age':[20,21,22,23,40,41,42,43,60,61,62,63,80,81,82,83],
                             'spend':[10.,11.,12.,13.,40.,41.,42.,43.,70.,71.,72.,73.,100.,101.,102.,1e5],
                             'tier':['B']*4+['S']*4+['G']*4+['P']*4})
            df.to_csv(p/'input.csv',index=False)
            session=Session.create(p/'input.csv',p/'session')
            plan={'schema':{'age':{'type':'numeric','role':'feature'},
                            'spend':{'type':'numeric','role':'feature'},
                            'tier':{'type':'nominal','role':'feature'}},
                  'actions':{c:{} for c in df},'weights':{c:1 for c in df}}
            count=0
            def approve(item,token):
                nonlocal count
                count+=1
                return session.respond(item,token,'A',f'qa-post4-r3-{count}',source='qa_fixture')
            approve('preprocess',session.propose_preprocessing(plan))
            approve('method',session.propose_method('hierarchical'))
            draft=exploratory_draft(session)
            draft['configs']=draft['configs'][:2]
            draft['parameter_sources']=draft['parameter_sources'][:2]
            draft['diagnostics_plan']['repeats']=2
            approve('candidates',session.propose_candidates(**draft))
            session.fit_candidates()
            approve('results',session.gate.state['proposals']['results']['token'])
            diagnostics=session.diagnose_approved()
            self.assertIn('metric_contrast',diagnostics)
            self.assertEqual(len(diagnostics['metric_contrast']['candidates']),2)
            self.assertIn('metric_contrast',json.loads((p/'session'/'selection_evidence'/'selection_evidence.json').read_text()))
            selection={'chosen_reason':'QA: inspect actual silhouette and cluster stability without global optimality claim',
                       'candidate_reasons':{'0':'Smallest exploratory candidate retained for reference',
                                            '1':'Larger exploratory cut included as a sensitivity comparison'},
                       'conflicts':'No automatic winner; cluster purity and silhouette conflict can occur',
                       'limitations':'Two candidates and two resamples are an engineering fixture, not publication evidence'}
            approve('final',session.propose_final(0,'QA fixture confirms one exploratory candidate',selection))
            delivery=session.report(p/'report')
            analysis=(p/'report'/'analysis.md').read_text(encoding='utf-8')
            for marker in ('中央跨度／全距','候選品質與穩定性的實際比較',
                           '各群實際特徵與研究討論','Stage 5','群間比較'):
                self.assertIn(marker,analysis)
            qmd=(p/'report'/'analysis.qmd').read_text(encoding='utf-8')
            html=(p/'report'/'analysis_offline.html').read_text(encoding='utf-8')
            self.assertIn('候選品質與穩定性的實際比較',qmd)
            self.assertIn('候選品質與穩定性的實際比較',html)
            self.assertIn('<details class="code-block">',html)
            self.assertNotIn('Jaccard',html)
            self.assertEqual(qmd.count('```{python}'),5)
            self.assertTrue(approve('delivery',delivery['token'])['advanced'])
            self.assertEqual(session.gate.state['phase'],'COMPLETE')
            receipt=(p/'report'/'delivery_confirmation.json').read_text(encoding='utf-8')
            self.assertNotIn(delivery['token'],receipt)
            self.assertNotIn('expires_at',receipt)
            self.assertEqual(json.loads(receipt)['approved_manifest_payload_hash'],
                             __import__('clustering_native.core',fromlist=['digest']).digest(
                                 session.gate.state['payloads']['delivery']))
            replay=subprocess.run(
                [sys.executable,str(p/'report'/'reproduce.py'),'--verify'],
                cwd=p/'report',capture_output=True,text=True,timeout=65)
            self.assertEqual(replay.returncode,0,
                             msg='Strict reproduction failed: '+replay.stdout[-1200:]+replay.stderr[-800:])

if __name__=='__main__': unittest.main()
