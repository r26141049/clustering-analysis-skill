"""RC6-TIMEOUT-01: persistent bounded worker; strict immutable science output."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from clustering_native.engine import StabilityFitBatch, bounded_fit, stability
from clustering_native.core import digest


class TimeoutRegression(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.log = Path(self.temp.name)/'fit_runtime_events.jsonl'
        self.data = pd.DataFrame({'x':[-2.0,-2.1,-2.2,-1.8,-1.9,-2.3,2.,2.1,2.2,1.8,1.9,2.3],
                                  'y':[-2.0,-2.1,-1.9,-2.2,-1.8,-2.3,2.0,2.1,2.2,1.8,1.9,2.3]})
        self.schema={name:{'type':'numeric'} for name in self.data.columns}
        self.weights={name:1. for name in self.data.columns}
        self.config={'metric':'euclidean', 'linkage':'ward','k':2}
        self.budget={'memory_mb':128,'seconds_per_fit':8,'max_rows':100,'max_candidates':9}
        self.plan={'schema':self.schema,'weights':self.weights}
    def tearDown(self):
        self.temp.cleanup()
    def events(self):
        return [json.loads(line) for line in self.log.read_text(encoding='utf-8').splitlines()] if self.log.exists() else []
    def test_persistent_worker_matches_one_shot_exactly(self):
        reference=bounded_fit(self.data,self.schema,self.weights,'hierarchical',self.config,self.budget)
        with StabilityFitBatch(self.budget,audit_path=self.log,candidate_index=2) as batch:
            r1=batch.fit(self.data,self.schema,self.weights,'hierarchical',self.config,repeat=0)
            r2=batch.fit(self.data,self.schema,self.weights,'hierarchical',self.config,repeat=1)
            self.assertEqual(batch.launch_count,1)
            self.assertEqual(reference,r1)
            self.assertEqual(reference,r2)
        es=self.events()
        self.assertEqual([e['status'] for e in es],['SUCCESS','SUCCESS'])
        self.assertEqual([e['reused_worker'] for e in es],[False,True])
        self.assertEqual([e['repeat'] for e in es],[0,1])
        self.assertTrue(all(e['elapsed_seconds'] <= self.budget['seconds_per_fit'] for e in es))
        self.assertTrue(all('worker_compute_seconds' in e for e in es))
    def test_stability_audit_separate_from_digest(self):
        model=bounded_fit(self.data,self.schema,self.weights,'hierarchical',self.config,self.budget)
        args=(self.data,self.data,self.plan,'hierarchical',model,self.budget,.8,3,17,'fixed_full_data_preprocessing')
        a=stability(*args,audit_path=self.log,candidate_index=0)
        b=stability(*args,audit_path=None,candidate_index=0)
        self.assertEqual(digest(a),digest(b))
        self.assertEqual(len(a['runs']),3)
        self.assertTrue(all('elapsed_seconds' not in x for x in a['runs']))
        self.assertEqual(len(self.events()),3)
    def test_timeout_kills_worker_and_preserves_no_retry(self):
        limited=dict(self.budget,seconds_per_fit=0.001)
        with StabilityFitBatch(limited,audit_path=self.log) as batch:
            for repeat in (0,1):
                with self.assertRaisesRegex(TimeoutError,'Approved fit time exceeded'):
                    batch.fit(self.data,self.schema,self.weights,'hierarchical',self.config,repeat=repeat)
                self.assertIsNone(batch.proc)
            self.assertEqual(batch.launch_count,2)
        es=self.events()
        self.assertEqual([e['status'] for e in es],['TIMEOUT','TIMEOUT'])
        self.assertEqual([e['repeat'] for e in es],[0,1])
    def test_failed_validation_no_worker_launched(self):
        with StabilityFitBatch(self.budget,audit_path=self.log) as batch:
            with self.assertRaises(ValueError):
                batch.fit(self.data,self.schema,self.weights,'hierarchical',dict(self.config,k=0))
            self.assertEqual(batch.launch_count,0)
    def test_research_result_shape_unchanged_for_fast_worker(self):
        model=bounded_fit(self.data,self.schema,self.weights,'hierarchical',self.config,self.budget)
        x=stability(self.data,self.data,self.plan,'hierarchical',model,self.budget,.8,2,7,
                    'fixed_full_data_preprocessing',audit_path=self.log)
        self.assertEqual(set(x),{'name','fraction','repeats','seed','preprocessing_policy',
            'gower_range_policy','noise_policy','disappeared_cluster_policy','pass_threshold','runs','failures'})
        self.assertEqual(x['failures'],0)
        self.assertEqual(set(x['runs'][0]),{'repeat','row_positions','ari','warnings','error'})
    def test_all_four_methods_preserve_oneshot_outputs(self):
        configs = {
            'kmeans': {'metric':'euclidean','k':2,'init':'k-means++','n_init':3,
                       'algorithm':'lloyd','random_state':17,'tol':1e-4,'max_iter':100},
            'hierarchical': self.config,
            'dbscan': {'metric':'euclidean','eps':0.7,'min_samples':2},
            'pam': {'metric':'euclidean','k':2,'max_swaps':50},
        }
        with StabilityFitBatch(self.budget,audit_path=self.log) as batch:
            for method, config in configs.items():
                with self.subTest(method=method):
                    cold=bounded_fit(self.data,self.schema,self.weights,method,config,self.budget)
                    warm=batch.fit(self.data,self.schema,self.weights,method,config)
                    self.assertEqual(cold,warm)
            self.assertEqual(batch.launch_count,1)

    def test_worker_not_reused_between_batches(self):
        with StabilityFitBatch(self.budget) as left:
            left.fit(self.data,self.schema,self.weights,'hierarchical',self.config)
            pid1=left.proc.pid
        with StabilityFitBatch(self.budget) as right:
            right.fit(self.data,self.schema,self.weights,'hierarchical',self.config)
            pid2=right.proc.pid
            self.assertNotEqual(pid1,pid2)

if __name__=='__main__': unittest.main(verbosity=2)
