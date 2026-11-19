"""Negative authorization and host-visible privacy coverage, qa_fixture only."""
import unittest
from datetime import timedelta
from clustering_native.core import Gate, utcnow
from clustering_native.privacy import public_output


class NegativeGateR2(unittest.TestCase):
    def setUp(self):
        self.g=Gate()
        self.token=self.g.propose('preprocess', {'draft':'fixture'},'S1_REVIEW','S1_REVIEW')
    def decision(self,response='A',message_id='qa-1',value='APPROVE',item='preprocess',stage=1):
        return {'value':value,'stage':stage,'item':item,'response':response,
                'source':'qa_fixture','message_id':message_id}
    def test_reject_and_ambiguous_do_not_advance(self):
        for response,value in [('C','REJECT'),('也許','CLARIFY'),('A，但不要執行','CLARIFY')]:
            with self.subTest(response=response):
                g=Gate(); token=g.propose('preprocess',{'draft':'fixture'},'S1_REVIEW','S1_REVIEW')
                ok=g.approve('preprocess',token,self.decision(response,value=value),
                             'S1_REVIEW','S2_REVIEW')
                self.assertFalse(ok)
                self.assertEqual(g.state['phase'],'S1_REVIEW')
                self.assertEqual(g.state['approvals'],{})
    def test_no_missing_wrong_cross_stage_or_stale(self):
        for token in (None,'invalid',self.token[:-1]+'x'):
            with self.subTest(token=token):
                with self.assertRaises(PermissionError):
                    self.g.approve('preprocess',token,self.decision(),
                                   'S1_REVIEW','S2_REVIEW')
                self.assertFalse(self.g.state['approvals'])
        with self.assertRaises(PermissionError):
            self.g.approve('preprocess',self.token,self.decision(stage=3),
                           'S1_REVIEW','S2_REVIEW')
        with self.assertRaises(PermissionError):
            self.g.approve('method',self.token,self.decision(item='method',stage=2),
                           'S2_REVIEW','S3_PLAN')
    def test_expired_even_if_self_consistent(self):
        p=self.g.state['proposals']['preprocess']
        p['expires_at']=(utcnow()-timedelta(seconds=1)).isoformat()
        p['token']=self.g._token('preprocess',p)
        with self.assertRaisesRegex(PermissionError,'expired'):
            self.g.approve('preprocess',p['token'],self.decision(),
                           'S1_REVIEW','S2_REVIEW')
        self.assertEqual(self.g.state['approvals'],{})
    def test_consumed_and_revision_invalidate(self):
        self.assertTrue(self.g.approve('preprocess',self.token,self.decision(),
                                      'S1_REVIEW','S2_REVIEW'))
        with self.assertRaises(PermissionError):
            self.g.approve('preprocess',self.token,self.decision(message_id='qa-2'),
                           'S1_REVIEW','S2_REVIEW')
        self.g.revise(1,'fixture scope change')
        self.assertFalse(self.g.state['approvals'])
        with self.assertRaises(PermissionError):
            self.g.approve('preprocess',self.token,self.decision(message_id='qa-3'),
                           'S1_REVIEW','S2_REVIEW')
    def test_study_references_do_not_introduce_unplanned_methods(self):
        from clustering_native.report_references import write_study_references
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'references.md'
            write_study_references(target)
            text=target.read_text(encoding='utf-8')
            self.assertIn('Gower',text)
            self.assertIn('Ward',text)
            self.assertIn('Silhouette',text)
            self.assertNotIn('Hennig',text)
            self.assertNotIn('bootstrap',text.lower())

    def test_public_nested_token_ttl_and_raw_digest_hide(self):
        value={'token':'secret','expires_at':'2026-11-18','authorization_scope':{'fits':10},
               'pending':{'nonce':'hidden','stage':3,'children':[{'token':'abc','k':5}]},
               'description':'Digest '+('a'*64)+' is internal'}
        text=str(public_output(value))
        self.assertNotIn('secret',text)
        self.assertNotIn('2026-11-18',text)
        self.assertNotIn('a'*64,text)
        self.assertNotIn('authorization_scope',text)
        self.assertIn("'k': 5",text)

if __name__=='__main__':unittest.main()
