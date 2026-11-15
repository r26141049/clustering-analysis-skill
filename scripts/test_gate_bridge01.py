"""RC6-GATE-BRIDGE-01 regression: local receipt is operator assertion, not platform proof."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
from clustering_native.session import Session
from clustering_native.cli import dispatch
from clustering_native.consent import classify
from clustering_native.core import digest

class GateBridge(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.csv=self.root/'input.csv'
        pd.DataFrame({'record_id':['p'+str(i) for i in range(12)],
                      'x':[-130,115,8,205,-78,70,0,0.1,.2,.3,.4,.5],
                      'y':[110,-85,-95,12,4,75,0,0.2,.4,.6,.8,1.]}).to_csv(self.csv,index=False)
        self.s=Session.create(self.csv,self.root/'session')
        self.plan={'schema':{'record_id':{'type':'id','role':'id'},'x':{'type':'numeric','role':'feature'},'y':{'type':'numeric','role':'feature'}},
                   'actions':{'x':{},'y':{}}, 'weights':{'x':1,'y':1}}
        self.token=self.s.propose_preprocessing(self.plan)
    def tearDown(self): self.tmp.cleanup()
    def request(self, response, **kwargs):
        return dispatch({'action':'respond_observed','session':str(self.s.directory),
                         'item':'preprocess','token':self.token,'response':response,**kwargs})
    def test_explanation_B_then_new_A_advances_one_gate(self):
        with patch('clustering_native.engine.bounded_fit') as fit:
            first=self.request('B：極端值為甚麼保留？')
            self.assertFalse(first['result']['advanced'])
            self.assertEqual(first['result']['value'],'CLARIFY')
            n=Session(self.s.directory)
            self.assertEqual(n.gate.state['phase'],'S1_REVIEW')
            self.assertEqual(n.gate.state['proposals']['preprocess']['token'],self.token)
            self.assertNotIn('preprocess',n.gate.state['approvals'])
            ok=self.request('A')
            self.assertEqual(ok['phase'],'S2_REVIEW')
            self.assertTrue(ok['result']['advanced'])
            self.assertEqual(ok['result']['value'],'APPROVE')
            n=Session(self.s.directory)
            self.assertEqual(n.gate.state['phase'],'S2_REVIEW')
            self.assertIn('preprocess',n.gate.state['approvals'])
            self.assertEqual(n.gate.state['approvals']['preprocess']['payload_hash'],digest(n.gate.state['payloads']['preprocess']))
            fit.assert_not_called()
    def test_origin_local_and_not_platform_claim(self):
        response=self.request('A')['result']
        self.assertTrue(response['receipt']['message_id'].startswith('local-agent-observed:'))
        self.assertFalse(response['receipt']['platform_authenticated'])
        n=Session(self.s.directory)
        self.assertEqual(n.gate.state['approvals']['preprocess']['decision']['source'],'user')
        self.assertEqual(n.gate.state['approvals']['preprocess']['decision']['response'],'A')
        self.assertEqual(n.gate.state['approvals']['preprocess']['decision']['message_id'],response['receipt']['message_id'])
        receipts=[e for e in n.gate.state['events'] if e['action']=='local_reply_receipt']
        self.assertEqual(len(receipts),1)
        self.assertEqual(receipts[0]['provenance'],'AGENT_ASSERTED_NEW_USER_TURN_NOT_PLATFORM_VERIFIED')
        self.assertEqual(receipts[0]['response_hash'],digest('A'))
    def test_missing_reply_never_approves(self):
        for response in ['', '  ', None]:
            with self.subTest(response=response):
                with self.assertRaises(PermissionError): self.request(response)
        self.assertEqual(Session(self.s.directory).gate.state['phase'],'S1_REVIEW')
    def test_ambiguous_and_negative_no_advance(self):
        for txt in ['也許可以','不同意，請不要執行','A，但不要繼續','只想先問問題']:
            with self.subTest(txt=txt):
                # REJECT marks pending rejected; use a fresh isolated fixture each time.
                n=Session(self.s.directory)
                if n.gate.state['proposals']['preprocess']['status']!='PENDING':
                    self.token=n.renew_confirmation('preprocess')
                r=self.request(txt)
                self.assertFalse(r['result']['advanced'])
                self.assertEqual(r['phase'],'S1_REVIEW')
                self.assertNotIn('preprocess', Session(self.s.directory).gate.state['approvals'])
    def test_true_B_revision_revokes_and_requires_new_proposal(self):
        r=self.request('B')
        self.assertFalse(r['result']['advanced'])
        n=Session(self.s.directory)
        self.assertEqual(n.gate.state['phase'],'S1_REVIEW')
        self.assertNotIn('preprocess',n.gate.state['proposals'])
        with self.assertRaises(PermissionError): self.request('A')
        new=n.propose_preprocessing(self.plan)
        self.assertNotEqual(new,self.token)
        self.token=new
        self.assertTrue(self.request('A')['result']['advanced'])
    def test_stale_token_after_renew_refused(self):
        n=Session(self.s.directory)
        new=n.renew_confirmation('preprocess')
        self.assertNotEqual(new,self.token)
        with self.assertRaises(PermissionError):self.request('A')
        self.token=new
        self.assertTrue(self.request('A')['result']['advanced'])
    def test_cross_session_token_rejected(self):
        other=Session.create(self.csv,self.root/'other')
        other.propose_preprocessing(self.plan)
        with self.assertRaises(PermissionError):
            dispatch({'action':'respond_observed','session':str(other.directory),'item':'preprocess',
                     'token':self.token,'response':'A'})
        self.assertEqual(Session(other.directory).gate.state['phase'],'S1_REVIEW')
    def test_consumed_token_cannot_advance_again(self):
        self.request('A')
        with self.assertRaises(PermissionError):self.request('A')
        self.assertEqual(Session(self.s.directory).gate.state['phase'],'S2_REVIEW')
    def test_wrong_stage_item_rejected(self):
        with self.assertRaises(PermissionError):
            dispatch({'action':'respond_observed','session':str(self.s.directory),
                    'item':'results','token':self.token,'response':'A'})
    def test_qa_mixing_rejected(self):
        n=Session(self.s.directory)
        n.respond('preprocess',self.token,'A','qa-ref',source='qa_fixture')
        n.propose_method_choices()
        method_token=n.gate.state['proposals']['method']['token']
        with self.assertRaises(PermissionError):
            dispatch({'action':'respond_observed','session':str(self.s.directory),
                      'item':'method','token':method_token,'response':'1'})
    def test_expired_token_rejected(self):
        n=Session(self.s.directory)
        n.gate.state['proposals']['preprocess']['expires_at']='2000-01-01T00:00:00+00:00'
        # Legitimate expiry changes a token binding; reissue a matching expired token.
        p=n.gate.state['proposals']['preprocess'];p['token']=n.gate._token('preprocess',p)
        n.state['gate']=n.gate.state
        from clustering_native.core import write_json
        write_json(n.directory/'session.json',n.state)
        with self.assertRaises(PermissionError):
            dispatch({'action':'respond_observed','session':str(n.directory),
                'item':'preprocess','token':p['token'],'response':'A'})
    def test_old_explicit_message_id_route_unchanged(self):
        r=dispatch({'action':'respond','session':str(self.s.directory),
                'item':'preprocess','token':self.token,'response':'A','message_id':'trusted-external-turn'})
        self.assertEqual(r['phase'],'S2_REVIEW')
        self.assertNotIn('receipt',r['result'])
    def test_old_route_without_id_still_fails_closed(self):
        with self.assertRaises(TypeError):
            dispatch({'action':'respond','session':str(self.s.directory),
              'item':'preprocess','token':self.token,'response':'A'})
    def test_observed_rejects_extraneous_source_or_message_id(self):
        for extra in [{'source':'qa_fixture'},{'message_id':'forged'}]:
            with self.subTest(extra=extra):
                with self.assertRaises(TypeError):self.request('A',**extra)
    def test_new_receipt_for_method_choice_only_authorizes_planning(self):
        self.request('A')
        n=Session(self.s.directory)
        token=n.propose_method_choices()['token']
        with patch('clustering_native.engine.bounded_fit') as fit:
            r=dispatch({'action':'respond_observed','session':str(n.directory),
                        'item':'method','token':token,'response':'1'})
            self.assertTrue(r['result']['advanced'])
            self.assertEqual(r['phase'],'S3_PLAN')
            n=Session(n.directory)
            self.assertIn('method',n.gate.state['approvals'])
            self.assertNotIn('candidates',n.gate.state['approvals'])
            with self.assertRaises(PermissionError):n.fit_candidates()
            fit.assert_not_called()
    def test_local_receipt_reuse_across_gate_refused(self):
        first=self.request('A')['result']['receipt']['message_id']
        n=Session(self.s.directory)
        token=n.propose_method_choices()['token']
        with self.assertRaises(PermissionError):
            n.respond('method',token,'1',first,source='user')
        self.assertEqual(Session(n.directory).gate.state['phase'],'S2_REVIEW')

    def test_classification_B_question_vs_revision(self):
        self.assertEqual(classify('B：極端值為甚麼保留？','preprocess')['value'],'CLARIFY')
        self.assertEqual(classify('B','preprocess')['value'],'REVISE')
        self.assertEqual(classify('A','preprocess')['value'],'APPROVE')

if __name__=='__main__':unittest.main(verbosity=2)
