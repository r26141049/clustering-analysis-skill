"""R4D regression: Stage 2 priorities, narrative, DBSCAN eps search, no new fits."""
import unittest
import numpy as np
import pandas as pd
from sklearn.datasets import make_moons
from sklearn.metrics import pairwise_distances
from clustering_native.dbscan_planning import propose_eps_candidates,assess_approved_eps_search
from clustering_native.method_rationale import summarize_visual_geometry,render_stage2_method_decision,render_stage2_method_comparison
from clustering_native.suitability import assess
from clustering_native.data import audit


def handoff():
    return {'visual':{'status':'OPERATOR_VISUAL_REVIEW_RECORDED',
        'observations': {
            'nonconvex':{'value':'observed','reason':'Two interleaved arcs, not convex blobs.'},
            'curved':{'value':'observed','reason':'Curved rising and falling trajectories.'},
            'unequal_density':{'value':'uncertain','reason':'Local spacing varies but is not proven.'},
            'isolated_regions':{'value':'uncertain','reason':'Sparse points might be noise.'},
            'coarse_fine_structure':{'value':'uncertain','reason':'No known hierarchy.'}}}}

class Stage2PriorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        x,_ = make_moons(n_samples=150, noise=.045, random_state=14)
        cls.df=pd.DataFrame(x,columns=['x','y'])
        cls.plan={'schema':{c:{'type':'numeric','role':'feature'} for c in cls.df},
                  'weights':{c:1 for c in cls.df},'actions':{c:{} for c in cls.df}}
        cls.assessment=assess(cls.df,cls.plan,audit(cls.df,cls.plan['schema']),
                              purpose='exploratory_partition',handoff=handoff())

    def test_priority_separate_from_order_and_feasibility(self):
        result=self.assessment
        tiers={r['method']:(r['recommendation_priority'],r['priority_tier']) for r in result['methods']}
        self.assertEqual(tiers['dbscan'],('優先建議',1))
        self.assertEqual(tiers['hierarchical'],('次優先考慮',2))
        self.assertTrue(all(r['recommendation_reason'] for r in result['methods']))
        self.assertTrue(result['recommendation']['await_user_choice'])
        self.assertEqual(result['recommendation']['model_fits'],0)
        self.assertEqual(result['methods'][0]['method'],'kmeans')  # menu order, not rank

    def test_human_narrative_not_raw_python_dict(self):
        rendered=render_stage2_method_decision(self.assessment,'dbscan')
        self.assertIn('兩條相互交錯',rendered)
        self.assertIn('為', '為')
        self.assertIn('局部密度連通',rendered)
        self.assertIn('優先建議',rendered)
        self.assertNotIn("{'nonconvex'",rendered)
        self.assertNotIn('Two interleaved arcs',rendered)
        self.assertIn('選項編號不是推薦排名',rendered)

    def test_uncertain_geometry_does_not_invent_moons(self):
        visual={'status':'UNREVIEWED','observations':{}}
        self.assertIn('沒有已確認',summarize_visual_geometry(visual))
        self.assertNotIn('兩條',summarize_visual_geometry(visual))

    def test_priority_menu_ids_match_eligible_options(self):
        assessment=dict(self.assessment)
        rows=[dict(row) for row in self.assessment['methods']]
        rows[0]['status']='不適合'
        assessment['methods']=rows
        preview=render_stage2_method_comparison(assessment,
                    {'1':'hierarchical','2':'dbscan','3':'pam'})
        self.assertIn('| 2 | DBSCAN | 優先建議',preview)
        self.assertIn('| —（本輪不可選） | K-means |',preview)
        self.assertNotIn("{'nonconvex'",preview)

class DBSCANDraftTests(unittest.TestCase):
    def test_data_driven_upper_tail_and_no_model_fit(self):
        X,_=make_moons(n_samples=420,noise=.05,random_state=7)
        D=pairwise_distances(X);np.fill_diagonal(D,np.inf)
        r=np.sort(D,axis=1)[:,4]
        draft=propose_eps_candidates(r,k=5)
        self.assertEqual(draft['model_fits'],0)
        self.assertTrue(draft['requires_stage3_approval'])
        sources={row['source'] for row in draft['candidates']}
        self.assertTrue({'P25','P50','P75','P90','P95'}<=sources)
        self.assertEqual(len(draft['candidates']),len({v['eps'] for v in draft['candidates']}))
        self.assertLessEqual(len(draft['candidates']),6)
        self.assertGreater(draft['candidates'][-1]['eps'],
                           next(c['eps'] for c in draft['candidates'] if c['source']=='P75'))

    def test_duplicate_radii_cannot_silently_invent_search(self):
        with self.assertRaises(ValueError):propose_eps_candidates(np.ones(100), k=5)

    def test_fragmentation_diagnostic_no_automatic_fit(self):
        def item(eps,groups,noise):
            labels=np.tile(np.arange(groups),10).tolist()+[-1]*noise
            return {'config':{'eps':eps,'min_samples':6},'metrics':{'clusters':groups},'labels':labels}
        review=assess_approved_eps_search([item(.07,22,30),item(.1,10,15),item(.13,8,8)])
        self.assertEqual(review['status'],'REVIEW_UPPER_EPS')
        self.assertTrue(review['requires_stage3_approval_for_more_fits'])
        self.assertEqual(review['new_fits_performed'],0)
        self.assertIn('Hard Gate',review['recommendation'])

if __name__=='__main__':unittest.main()
