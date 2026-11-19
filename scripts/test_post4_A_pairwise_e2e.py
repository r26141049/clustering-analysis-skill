"""True independently authorized alternative-representation studies (QA only)."""
import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from clustering_native.session import Session
from clustering_native.planning import exploratory_draft
from clustering_native.approved_sensitivity import compare_approved_studies

class ApprovedPreprocessingComparison(unittest.TestCase):
    def test_two_full_approved_studies_compare_readonly(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            data=pd.DataFrame({'x':[0.,.1,.2,3.,3.1,3.2,7.,7.1,7.2,11.,11.1,11.2],
                               'y':[0.,1.,2.,0.,1.,2.,0.,1.,2.,0.,1.,2.]})
            data.to_csv(root/'input.csv',index=False)
            built=[]
            for name,action in [('raw',{}),('scaled',{'scale':'standard'})]:
                s=Session.create(root/'input.csv',root/name)
                plan={'schema':{c:{'type':'numeric','role':'feature'} for c in data},
                      'actions':{c:action for c in data}, 'weights':{c:1 for c in data}}
                n=0
                def approve(item,token):
                    nonlocal n
                    n+=1
                    return s.respond(item,token,'A',f'qa-preprocess-{name}-{n}',source='qa_fixture')
                approve('preprocess',s.propose_preprocessing(plan))
                approve('method',s.propose_method('hierarchical'))
                draft=exploratory_draft(s)
                draft['configs']=draft['configs'][:2]
                draft['parameter_sources']=draft['parameter_sources'][:2]
                draft['diagnostics_plan']['repeats']=2
                approve('candidates',s.propose_candidates(**draft))
                s.fit_candidates()
                approve('results',s.gate.state['proposals']['results']['token'])
                s.diagnose_approved()
                exp={'chosen_reason':'QA sensitivity method comparison only',
                     'candidate_reasons':{'0':'Pre-specified candidate','1':'Alternative K retained in the study'},
                     'conflicts':'No best K inferred; experiment only',
                     'limitations':'QA synthetic data, not real user approval'}
                approve('final',s.propose_final(0,'QA approved chosen K',exp))
                s.report(root/(name+'_report'))
                self.assertEqual(s.gate.state['phase'],'S5_REVIEW')
                built.append(s)
            originals=[(p/'session.json').read_bytes() for p in (built[0].directory,built[1].directory)]
            comparison=compare_approved_studies(built[0].directory,built[1].directory,root/'sensitivity')
            self.assertEqual(comparison['comparison']['model_fits_performed_by_comparison'],0)
            self.assertEqual(comparison['comparison']['n_common_rows'],len(data))
            self.assertTrue(any(x['different_cells'] for x in comparison['comparison']['feature_changes']))
            self.assertEqual(originals,[ (p/'session.json').read_bytes() for p in (built[0].directory,built[1].directory)])
            self.assertTrue((root/'sensitivity'/'approved_sensitivity.md').is_file())
            self.assertTrue((root/'sensitivity'/'approved_sensitivity.json').is_file())
            with self.assertRaises(ValueError):
                compare_approved_studies(built[0].directory,built[0].directory,root/'invalid')

if __name__=='__main__':unittest.main()
