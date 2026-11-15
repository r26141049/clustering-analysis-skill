"""RC6-COMPAT-01 synthetic regression; no estimator fitting or research reuse."""
import copy,json,shutil,sys,tempfile,unittest,subprocess,os
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
from clustering_native.session import Session
from clustering_native.core import file_hash
class Compatibility(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.csv=cls.root/'fixture.csv';pd.DataFrame({'x':[.1,.2,4.1,4.2],'y':[.2,.3,4.2,4.3]}).to_csv(cls.csv,index=False)
  s=Session.create(cls.csv,cls.root/'base');p={'schema':{c:{'type':'numeric','role':'feature'} for c in ['x','y']},'actions':{c:{} for c in ['x','y']},'weights':{'x':1,'y':1}};cls.plan=p;t=s.propose_preprocessing(p);s.respond('preprocess',t,'A','prep-fixture',source='qa_fixture');s.propose_method_choices()
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def fresh(self):
  p=self.root/self._testMethodName;shutil.copytree(self.root/'base',p);return Session(p)
 def choose(self,s,reply='1',mid='method-fixture'):
  return s.respond('method',s.gate.state['proposals']['method']['token'],reply,mid,source='qa_fixture')
 def assert_planning_only(self,s,method):
  n=Session(s.directory);self.assertEqual(n.method(),method);self.assertEqual(n.gate.state['phase'],'S3_PLAN');self.assertNotIn('candidates',n.gate.state['approvals']);self.assertEqual(n.state['results'],[])
  with patch('clustering_native.engine.bounded_fit') as fit:
   with self.assertRaises(PermissionError):n.fit_candidates()
   fit.assert_not_called()
 def test_00_original_failure_path_approved_menu_to_legacy_revision(self):
  s=self.fresh();old=s.gate.state['proposals']['method']['token'];self.choose(s);revision=s.gate.state['revision'];t=s.propose_method('pam');n=Session(s.directory);self.assertEqual(n.gate.state['phase'],'S2_REVIEW');self.assertEqual(n.gate.state['revision'],revision+1);self.assertNotIn('method',n.gate.state['approvals']);self.assertEqual(n.gate.state['payloads']['method']['method'],'pam');self.assertNotEqual(old,t)
  with self.assertRaises(PermissionError):n.respond('method',old,'1','fresh-but-stale-token',source='qa_fixture')
  n.respond('method',t,'A','new-pam-fixture',source='qa_fixture');self.assert_planning_only(n,'pam')
 def test_menu_schema_unchanged_and_normal_choice(self):
  s=self.fresh();self.assertEqual(set(s.gate.state['payloads']['method']),{'options','assessment','model_hash','eda_hash'});self.choose(s);self.assert_planning_only(s,'kmeans')
 def test_legacy_schema_approval_and_revision(self):
  s=self.fresh();t=s.propose_method('kmeans');self.assertEqual(set(s.gate.state['payloads']['method']),{'method','assessment','model_hash'});s.respond('method',t,'A','legacy-k',source='qa_fixture');self.assert_planning_only(s,'kmeans');new=s.propose_method('pam');self.assertNotEqual(t,new);self.assertNotIn('method',Session(s.directory).gate.state['approvals'])
 def test_pending_menu_replaced_by_legacy_invalidates_old_token(self):
  s=self.fresh();old=s.gate.state['proposals']['method']['token'];new=s.propose_method('pam')
  with self.assertRaises(PermissionError):s.respond('method',old,'1','stale-pending',source='qa_fixture')
  s.respond('method',new,'A','new-pending',source='qa_fixture');self.assert_planning_only(s,'pam')
 def test_missing_fields_both_schemas(self):
  s=self.fresh();menu=copy.deepcopy(s.gate.state['payloads']['method']);legacy={k:v for k,v in menu.items() if k in {'assessment','model_hash'}};legacy['method']='kmeans'
  for p in [menu,legacy]:
   for key in p:
    with self.subTest(schema='menu' if 'options' in p else 'legacy',missing=key):
     broken=copy.deepcopy(p);broken.pop(key)
     with self.assertRaises(ValueError):s._validate_method_payload(broken)
 def test_invalid_schema_values_and_conflicting_formats(self):
  s=self.fresh();p=copy.deepcopy(s.gate.state['payloads']['method']);cases=[None,{},dict(p,method='kmeans'),dict(p,options={}),dict(p,options={'1':'gmm'}),dict(p,options={'1':'kmeans','2':'kmeans'}),dict(p,assessment={}),dict(p,model_hash='other'),dict(p,eda_hash='other')]
  for bad in cases:
   with self.subTest(payload=str(bad)[:80]):
    with self.assertRaises(ValueError):s._validate_method_payload(bad)
  missing_row=copy.deepcopy(p);missing_row['assessment']['methods'].pop()
  with self.assertRaises(ValueError):s._validate_method_payload(missing_row)
  bad_status=copy.deepcopy(p);bad_status['assessment']['methods'][0]['status']=[]
  with self.assertRaises(ValueError):s._validate_method_payload(bad_status)
 def test_unknown_requested_method_cannot_revoke_existing_scope(self):
  s=self.fresh();self.choose(s);before=file_hash(s.directory/'session.json')
  for value in ['gmm','unknown','K-means','',None,{'method':'pam'}]:
   with self.subTest(value=value):
    with self.assertRaises(ValueError):s.propose_method(value)
    self.assertEqual(file_hash(s.directory/'session.json'),before)
  self.assert_planning_only(s,'kmeans')
 def test_legacy_unknown_payload_rejected(self):
  s=self.fresh();p=s.gate.state['payloads']['method'];base={'assessment':p['assessment'],'model_hash':p['model_hash']}
  for method in ['gmm',None,{},'']:
   with self.subTest(method=method):
    with self.assertRaises(ValueError):s._validate_method_payload(dict(base,method=method))
 def test_ambiguous_menu_reply_never_approves(self):
  s=self.fresh()
  for i,reply in enumerate(['A','也許可以','unknown-method']):
   r=self.choose(s,reply,'ambiguous-'+str(i));self.assertFalse(r['advanced']);self.assertNotIn('method',Session(s.directory).gate.state['approvals'])
 def test_rejection_never_approves(self):
  s=self.fresh();r=self.choose(s,'不同意，請不要執行');self.assertFalse(r['advanced']);self.assertNotIn('method',Session(s.directory).gate.state['approvals'])
 def test_same_consumed_token_refused_and_no_fit(self):
  s=self.fresh();old=s.gate.state['proposals']['method']['token'];self.choose(s)
  with self.assertRaises(PermissionError):s.respond('method',old,'1','new-replay',source='qa_fixture')
  self.assert_planning_only(s,'kmeans')
 def test_consumed_reply_cannot_authorize_revised_method(self):
  s=self.fresh();self.choose(s,mid='unique-choice');t=s.propose_method('pam')
  with self.assertRaises(PermissionError):s.respond('method',t,'A','unique-choice',source='qa_fixture')
  self.assertNotIn('method',Session(s.directory).gate.state['approvals'])
 def test_same_approved_method_call_is_explicit_phase_rejection(self):
  s=self.fresh();self.choose(s)
  with self.assertRaises(PermissionError):s.propose_method('kmeans')
  self.assert_planning_only(s,'kmeans')
 def test_stale_session_reload_before_revision(self):
  s=self.fresh();stale=Session(s.directory);self.choose(s);t=stale.propose_method('pam');n=Session(s.directory);self.assertEqual(n.gate.state['proposals']['method']['token'],t);self.assertNotIn('method',n.gate.state['approvals']);self.assertEqual(n.gate.state['phase'],'S2_REVIEW')
 def test_cli_compatibility_revision_persists(self):
  s=self.fresh();self.choose(s);req={'action':'propose_method','session':str(s.directory),'method':'pam'};p=subprocess.run([sys.executable,'-m','clustering_native'],input=json.dumps(req),text=True,capture_output=True,env=dict(os.environ,PYTHONPATH=str(ROOT)));self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(Session(s.directory).gate.state['phase'],'S2_REVIEW');self.assertNotIn('method',Session(s.directory).gate.state['approvals'])
if __name__=='__main__':unittest.main(verbosity=2)
