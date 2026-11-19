"""R4C new-scope real five-stage regression; QA fixture permissions only."""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
import pandas as pd
from clustering_native.session import Session
from clustering_native.education import planned_evidence,study_disclosure

class RealR4CStudies(unittest.TestCase):
    def run_research(self,method,metric,linkage=None):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            x=[0.,.1,.2,.3, 4.,4.1,4.2,4.3, 9.,9.1,9.2,9.3]
            y=[.0,.1,-.1,.05, .2,.3,.15,.1, -.1,.05,.1,.0]
            df=pd.DataFrame({'x':x,'y':y})
            if metric=='gower':df['tier']=['A']*4+['B']*4+['C']*4
            df.to_csv(root/'input.csv',index=False)
            s=Session.create(root/'input.csv',root/'session')
            plan={'schema':{c:{'type':'nominal' if c=='tier' else 'numeric','role':'feature'} for c in df},
                  'actions':{c:{} for c in df},'weights':{c:1 for c in df}}
            seq=0
            def approve(key,token):
                nonlocal seq
                seq+=1
                return s.respond(key,token,'A',f'qa-r4c-{method}-{seq}',source='qa_fixture')
            approve('preprocess',s.propose_preprocessing(plan))
            self.assertEqual(s.gate.state['phase'],'S2_REVIEW')
            with self.assertRaises((PermissionError,ValueError)):
                s.report(root/'too_early')
            approve('method',s.propose_method(method))
            self.assertEqual(s.gate.state['phase'],'S3_PLAN')
            with self.assertRaises((PermissionError,ValueError)):
                s.report(root/'too_early')
            configs=[]
            for k in (2,3):
                if method=='kmeans':
                    conf={'metric':'euclidean','k':k,'init':'k-means++','n_init':3,
                          'algorithm':'lloyd','random_state':17,'tol':1e-4,'max_iter':100}
                elif method=='pam':
                    conf={'metric':'gower','k':k,'max_swaps':30}
                elif method=='hierarchical':
                    conf={'metric':metric,'k':k,'linkage':linkage}
                else:
                    conf={'metric':'euclidean','eps':(.55 if k==2 else .75),'min_samples':2}
                configs.append(conf)
            sources=[{key:{'source':'exploratory_default','rationale':'QA bounded exploratory candidate, not a natural K claim'}
                      for key in conf} for conf in configs]
            proposal=dict(configs=configs,basis='exploratory-only',evidence='QA test only',
                budget={'max_rows':30,'memory_mb':256,'seconds_per_fit':8,'max_candidates':3},
                diagnostics_plan={'fraction':.8,'repeats':2,'seed':17,'policy':'fixed_full_data_preprocessing'},
                parameter_sources=sources,search_rationale='QA: predeclared k=2,3 or eps=.55,.75',
                boundary_limitations='Only test scope; no global optimum claim',
                initialization_plan={'seeds':[17,23]} if method=='kmeans' else None)
            token=s.propose_candidates(**proposal)
            self.assertNotIn('Jaccard',s.gate.state['payloads']['candidates']['statistical_disclosure'])
            with self.assertRaises((PermissionError,ValueError)):
                s.report(root/'too_early')
            approve('candidates',token)

            s.fit_candidates()

            approve('results',s.gate.state['proposals']['results']['token'])

            s.diagnose_approved()

            self.assertEqual(s.gate.state['phase'],'S4_REVIEW')
            evidence=json.loads((s.directory/'selection_evidence'/'selection_evidence.json').read_text())
            self.assertNotIn('cluster_jaccard',evidence)
            self.assertIn('ALL_REPORTED_METRICS_PREDISCLOSED',evidence['metric_disclosure_audit']['status'])
            for outcome in s.state['diagnostics']['stability']:
                self.assertTrue(all('cluster_jaccard' not in run for run in outcome['runs']))
            explanations={'chosen_reason':'QA: approved candidate C1; no global-optimum claim',
                          'candidate_reasons':{'0':'QA retained candidate','1':'QA compared alternative'},
                          'conflicts':'Researcher review necessary if quality and stability disagree',
                          'limitations':'Engineering QA fixture only'}
            approve('final',s.propose_final(0,'QA final chosen candidate',explanations))

            delivery=s.report(root/'report')

            report=root/'report'
            md=(report/'analysis.md').read_text(encoding='utf-8')
            html=(report/'analysis_offline.html').read_text(encoding='utf-8')
            qmd=(report/'analysis.qmd').read_text(encoding='utf-8')
            for text in (md,html,qmd):
                self.assertNotIn('Jaccard',text)
                self.assertIn('各群實際特徵與研究討論',text)
                self.assertIn('選群結果與決策依據',text)
            self.assertEqual(md.count('```python'),5)
            self.assertEqual(qmd.count('```{python}'),5)
            self.assertEqual(html.count('<details class="code-block">'),5)
            self.assertIn('code-fold: true',qmd)
            self.assertNotIn('<script',html)
            self.assertNotIn('指標事前揭露稽核：`',md)
            refs=(report/'references.md').read_text(encoding='utf-8')
            self.assertNotIn('Jaccard',refs)
            if method=='hierarchical':self.assertIn('Linkage',md)
            approve('delivery',delivery['token'])
            self.assertEqual(s.gate.state['phase'],'COMPLETE')
            for stage in range(1,6):
                from clustering_native.report_code import stage_block
                block=stage_block(stage)
                code=block.split('```python\n',1)[1].split('\n```',1)[0]
                out=subprocess.run([sys.executable,'-c',code],cwd=report,capture_output=True,text=True,timeout=30)
                self.assertEqual(out.returncode,0,f'stage{stage}: '+out.stderr[-500:])

            replay=subprocess.run([sys.executable,str(report/'reproduce.py'),'--verify'],cwd=report,
                                  capture_output=True,text=True,timeout=80)
            self.assertEqual(replay.returncode,0,'Strict reproduction: '+replay.stdout[-700:]+replay.stderr[-300:])
            return len(configs)

    def test_kmeans(self):self.run_research('kmeans','euclidean')
    def test_pam_gower(self):self.run_research('pam','gower')
    def test_dbscan(self):self.run_research('dbscan','euclidean')
    def test_hierarchical_ward(self):self.run_research('hierarchical','euclidean','ward')
    def test_hierarchical_gower(self):self.run_research('hierarchical','gower','average')

if __name__=='__main__': unittest.main()
