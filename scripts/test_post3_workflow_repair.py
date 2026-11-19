"""Focused regression checks for bounded execution, no extra gates and early distance preflight."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from clustering_native.consent import classify
from clustering_native.cli import dispatch, continuation
from clustering_native.core import file_hash
from clustering_native.session import Session
from clustering_native import locking


class WorkflowRepair(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.csv = self.base/'input.csv'
        pd.DataFrame({
            'record_id': [f'p{i}' for i in range(12)],
            'age': [np.nan, *range(11)],
            'region': [None, *(['North', 'South'] * 5), 'North']
        }).to_csv(self.csv, index=False)
        self.directory = self.base/'session'
        self.session = Session.create(self.csv, self.directory)
        self.plan = {
            'schema': {
                'record_id': {'type': 'id', 'role': 'id'},
                'age': {'type': 'numeric', 'role': 'feature'},
                'region': {'type': 'nominal', 'role': 'feature'}},
            'actions': {'age': {'missing': 'retain'}, 'region': {'missing': 'retain'}},
            'weights': {'age': 1, 'region': 1}}

    def tearDown(self):
        self.tmp.cleanup()

    def approve_stage1(self, plan):
        token = self.session.propose_preprocessing(plan)
        result = dispatch({'action':'respond_observed','session':str(self.directory),
                           'item':'preprocess','token':token,'response':'A'})
        self.assertTrue(result['result']['advanced'])
        return result

    def test_approval_only_moves_one_gate_and_gives_continuation(self):
        r = self.approve_stage1(self.plan)
        self.assertEqual(r['phase'], 'S2_REVIEW')
        self.assertEqual(r['continuation']['kind'], 'AUTO_READONLY_UNTIL_USER_METHOD_CHOICE')
        s = Session(self.directory)
        self.assertIn('preprocess', s.gate.state['approvals'])
        self.assertNotIn('method', s.gate.state['approvals'])
        self.assertEqual(s.state['results'], [])

    def test_stage2_undefined_gower_preflight_disables_unsafe_options(self):
        self.approve_stage1(self.plan)
        result = dispatch({'action':'assess_methods','session':str(self.directory)})['result']
        self.assertEqual(result['gower_preflight']['status'], 'BLOCKED_UNDEFINED_PAIRS')
        self.assertEqual(result['gower_preflight']['undefined_pairs'], 11)
        rows = {r['method']:r for r in result['methods']}
        for method in ('pam','hierarchical','dbscan'):
            self.assertEqual(rows[method]['status'], '不適合')
        self.assertEqual(Session(self.directory).state['results'], [])
        with self.assertRaisesRegex(ValueError, 'No compatible options'):
            dispatch({'action':'propose_method_choices','session':str(self.directory)})
        self.assertEqual(Session(self.directory).gate.state['phase'], 'S2_REVIEW')

    def test_revised_stage1_median_makes_pairwise_distance_defined(self):
        plan = json.loads(json.dumps(self.plan))
        plan['actions']['age']['missing'] = 'median'
        self.approve_stage1(plan)
        result = dispatch({'action':'assess_methods','session':str(self.directory)})['result']
        self.assertEqual(result['gower_preflight']['status'], 'PASS')
        self.assertEqual(result['gower_preflight']['undefined_pairs'], 0)
        self.assertNotIn('method', Session(self.directory).gate.state['approvals'])

    def test_compact_gate_status_is_read_only(self):
        token = self.session.propose_preprocessing(self.plan)
        before = file_hash(self.directory/'session.json')
        result = dispatch({'action':'gate_status','session':str(self.directory)})
        after = file_hash(self.directory/'session.json')
        self.assertEqual(before, after)
        self.assertEqual(result['pending']['preprocess']['token'], token)
        self.assertEqual(result['phase'], 'S1_REVIEW')
        self.assertNotIn('model_data', result)

    def test_no_accidental_revision_from_long_conditional_caveat(self):
        answer='我明確批准目前提案。若 Token 過期或提案變更，請停止執行並重新取得批准。'
        self.assertEqual(classify(answer, 'preprocess')['value'], 'CLARIFY')
        self.assertEqual(classify('B', 'preprocess')['value'], 'REVISE')
        self.assertEqual(classify('請修改前處理方案', 'preprocess')['value'], 'REVISE')
        self.assertEqual(classify('A', 'preprocess')['value'], 'APPROVE')

    def test_lock_contention_is_bounded_without_mutation(self):
        lockfile = self.directory/'.session.lock'
        ready=threading.Event(); release=threading.Event()
        def blocker():
            with locking.session_lock(lockfile):
                ready.set()
                release.wait(3)
        t=threading.Thread(target=blocker, daemon=True)
        t.start(); self.assertTrue(ready.wait(3))
        original=file_hash(self.directory/'session.json')
        try:
            with patch.object(locking, 'LOCK_WAIT_SECONDS', .2):
                begin=time.monotonic()
                with self.assertRaisesRegex(TimeoutError,'Session lock busy'):
                    self.session.propose_preprocessing(self.plan)
                self.assertLess(time.monotonic()-begin, 2.0)
            self.assertEqual(original,file_hash(self.directory/'session.json'))
        finally:
            release.set(); t.join(3)
        # Same session becomes usable when sibling operation releases the lock.
        self.assertIsInstance(self.session.propose_preprocessing(self.plan),str)


if __name__ == '__main__':
    unittest.main(verbosity=2)
