"""R3 incremental scope expansion on non-hierarchical methods. QA gate only."""
import copy
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from clustering_native.core import digest
from clustering_native.planning import exploratory_draft
from clustering_native.session import Session


class CrossMethodExpansionR3(unittest.TestCase):
    def run_extension(self, method):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            rng=np.random.default_rng(31)
            coordinates=np.vstack([rng.normal([k*5, k*3], [0.27,0.2],size=((5 if method=='pam' else 8),2)) for k in range(3)])
            data=pd.DataFrame(coordinates,columns=['x','y'])
            data.to_csv(p/'data.csv',index=False)
            s=Session.create(p/'data.csv',p/'study')
            plan={'schema':{c:{'type':'numeric','role':'feature'} for c in data},
                  'actions':{c:{} for c in data},'weights':{c:1 for c in data}}
            count=0
            def yes(item,token):
                nonlocal count
                count+=1
                return s.respond(item,token,'A',f'qa-R3-{method}-{count}',source='qa_fixture')
            yes('preprocess',s.propose_preprocessing(plan))
            yes('method',s.propose_method(method))
            draft=exploratory_draft(s)
            self.assertGreaterEqual(len(draft['configs']),2)
            first_two=copy.deepcopy(draft['configs'][:2])
            if len(draft['configs'])>=3:
                new=copy.deepcopy(draft['configs'][2])
                new_sources=copy.deepcopy(draft['parameter_sources'][2])
            elif method=='dbscan':
                new={**draft['configs'][-1],'eps':float(draft['configs'][-1]['eps'])*1.3}
                new_sources={**draft['parameter_sources'][-1],
                    'eps':{'source':'user_specified','rationale':'QA approved additional neighborhood radius'}}
            else:
                self.fail('Unexpected insufficient candidate search')
            if method == 'pam':
                for entry in first_two: entry['max_swaps']=3
                new['max_swaps']=3
            draft['configs']=first_two
            draft['parameter_sources']=draft['parameter_sources'][:2]
            draft['diagnostics_plan']['repeats']=2
            draft['budget']['max_candidates']=5
            yes('candidates',s.propose_candidates(**draft))
            s.fit_candidates()
            yes('results',s.gate.state['proposals']['results']['token'])
            s.diagnose_approved()
            old=digest(s.state['results'])
            result=s.propose_candidate_expansion([new],[new_sources],
                    'Explicit exploratory extension with no claim of natural K',
                    budget={**draft['budget'],'max_candidates':5})
            self.assertEqual(s.gate.state['phase'],'S3_PERMISSION')
            self.assertEqual(s.state['results'],[])
            with self.assertRaises(PermissionError): s.fit_candidates()
            yes('candidates',result['token'])
            s.fit_candidates()
            self.assertEqual(len(s.state['results']),3)
            self.assertEqual(digest(s.state['results'][:2]),old)
            audit=[x for x in s.gate.state['events'] if x['action']=='candidate_incremental_execution'][-1]
            self.assertEqual(audit['reuse_count'],2)
            self.assertEqual(audit['new_fit_count'],1)
            reuse=[x for x in s.gate.state['events'] if x['action']=='candidate_stability_incremental_execution'][-1]
            self.assertEqual(reuse['reused'],2)
            self.assertEqual(reuse['new_stability_batches'],1)
            self.assertEqual(s.gate.state['phase'],'S3_RESULTS')
            self.assertNotIn('results',s.gate.state['approvals'])

    def test_kmeans_authorized_incremental(self):
        self.run_extension('kmeans')

    def test_pam_authorized_incremental(self):
        self.run_extension('pam')

    def test_dbscan_authorized_parameter_extension(self):
        self.run_extension('dbscan')

if __name__=='__main__':unittest.main()
