"""A-class real fit/Stage 4 comparison of approved alternative distance/linkage."""
import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from clustering_native.planning import exploratory_draft
from clustering_native.session import Session

class ActualMethodContrasts(unittest.TestCase):
    def test_linkage_and_distance_contrast_are_real_and_predisclosed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            frame=pd.DataFrame({'x':[0.,.2,.4,1., 4.,4.2,4.5,5., 9.,9.2,9.4,10.],
                                'y':[0.,2.,1.,3.,0.,2.,1.,3.,0.,2.,1.,3.]})
            frame.to_csv(root/'input.csv',index=False)
            s=Session.create(root/'input.csv',root/'study')
            plan={'schema':{c:{'type':'numeric','role':'feature'} for c in frame},
                  'actions':{c:{} for c in frame},'weights':{c:1 for c in frame}}
            counter=0
            def yes(key, token):
                nonlocal counter
                counter+=1
                return s.respond(key,token,'A',f'qa-A-contrast-{counter}',source='qa_fixture')
            yes('preprocess',s.propose_preprocessing(plan))
            yes('method',s.propose_method('hierarchical'))
            draft=exploratory_draft(s)
            ea=[c for c in draft['configs'] if c['metric']=='euclidean' and c['linkage']=='average'][0]
            base=[c for c in draft['configs'] if c['metric']=='euclidean' and c['linkage']=='ward' and c['k']==ea['k']][0]
            ma=[c for c in draft['configs'] if c['metric']=='manhattan' and c['linkage']=='average'][0]
            sel=[draft['configs'].index(c) for c in (base,ea,ma)]
            draft['configs']=[draft['configs'][i] for i in sel]
            draft['parameter_sources']=[draft['parameter_sources'][i] for i in sel]
            draft['diagnostics_plan']['repeats']=2
            yes('candidates',s.propose_candidates(**draft))
            self.assertEqual(len(s.state['results']),0)
            s.fit_candidates()
            yes('results',s.gate.state['proposals']['results']['token'])
            s.diagnose_approved()
            evidence=json.loads((s.directory/'selection_evidence'/'selection_evidence.json').read_text())
            self.assertEqual(len(evidence['linkage_comparisons']),2)
            self.assertEqual(len(evidence['distance_comparisons']),2)
            self.assertEqual(evidence['metric_disclosure_audit']['status'],'ALL_REPORTED_METRICS_PREDISCLOSED')
            description={'chosen_reason':'QA chosen for cross-method evidence only',
                'candidate_reasons':{'0':'Compare Ward with other linkage','1':'Compare Average Euclidean',
                                      '2':'Compare Average Manhattan'},
                'conflicts':'Different distance/linkage may disagree; no automatic winner',
                'limitations':'Engineering test only, not research conclusion'}
            yes('final',s.propose_final(0,'QA baseline pre-authorized',description))
            s.report(root/'report')
            md=(root/'report'/'analysis.md').read_text(encoding='utf-8')
            self.assertIn('距離度量的已批准候選對照',md)
            self.assertIn('Distance／Linkage 的實際候選比較',md)
            self.assertIn('Manhattan',md)
            self.assertNotIn('指標事前揭露稽核',md)  # Technical JSON belongs in evidence artifact.
            self.assertEqual(evidence['metric_disclosure_audit']['status'],'ALL_REPORTED_METRICS_PREDISCLOSED')
            self.assertNotIn('Jaccard',md)

if __name__=='__main__':unittest.main()
