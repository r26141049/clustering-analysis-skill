"""rc5 release accounting; historical applicability is separate from execution."""
from pathlib import Path
import ast,csv,hashlib,zipfile
STATES={'PASS','FAIL','ERROR','SKIP','NOT RUN'}
REQUIRED_EVIDENCE={'formal_installation','real_user_hard_gate_interaction','visual_qa','open_literature_validation', *{'chat_stage'+str(i)+'_visible' for i in range(1,6)}}
BASELINE_HASHES={'test_stat_reference.py':'d6fdb1e4ae2e8ac37e0d0e0a89790c38df582eb4754abb248f80b5aacfde39d5','test_prior_dryrun_regression.py':'f86a8f22d5bacb0a88b1facebefe32da278b4957a692021c4143e916e1fb2f9b'}
def required_manifest():
 root=Path(__file__).resolve().parents[1]/'tests';out={}
 for p in sorted(root.glob('test_*.py')):
  ids=[]
  for cls in ast.parse(p.read_text()).body:
   if isinstance(cls,ast.ClassDef):ids.extend(p.stem+'.'+cls.name+'.'+f.name for f in cls.body if isinstance(f,ast.FunctionDef) and f.name.startswith('test_'))
  if ids:out[p.name]=ids
 return out
REQUIRED_SUITES=tuple(required_manifest())
def historical_preservation(root):
 errors=[]
 try:
  with zipfile.ZipFile(root/'history/rc4_original_source_and_evidence.zip') as z:
   if z.testzip():errors.append('rc4 archive CRC failure')
   for name,h in BASELINE_HASHES.items():
    if hashlib.sha256(z.read('rc4/tests/'+name)).hexdigest()!=h:errors.append('Archived original baseline changed: '+name)
 except Exception as exc:errors.append('Historical archive error: '+str(exc))
 return errors

def evaluate(suites,static,required_evidence):
 root=Path(__file__).resolve().parents[1];hard=historical_preservation(root);missing=[];manifest=required_manifest();present={s['name']:s for s in suites}
 if static.get('status')!='PASS':hard.append('Static/source/package checks not PASS')
 for name,ids in manifest.items():
  if name not in present:missing.append('Required suite NOT RUN: '+name);continue
  suite=present[name]
  if suite.get('runner_status', 'COMPLETED') != 'COMPLETED':hard.append('Runner ERROR: '+name)
  if suite.get('exit_code', 0) not in (0, None):hard.append('Suite subprocess failed: '+name)
  if suite.get('loader_errors'):hard.append('Loader ERROR: '+name)
  for ident in ids:
   status=suite.get('tests',{}).get(ident,{}).get('status','NOT RUN')
   if status in {'FAIL','ERROR'}:hard.append(ident+': '+status)
   elif status!='PASS':missing.append(ident+': '+status)
 # The original applicable cases cannot disappear merely because the port is incomplete.
 with (root/'history/RC4_TEST_APPLICABILITY.csv').open() as f:history=list(csv.DictReader(f))
 if len(history)!=248:hard.append('Historical 248-case manifest is incomplete')
 ports={}
 port_path=root/'evidence/RC6_HISTORICAL_PORT.csv'
 if port_path.is_file():
  with port_path.open() as f:ports={r['rc4_case']:r['rc6_port_case'] for r in csv.DictReader(f)}
 # Evaluate current supplied outcomes, never stale historical PASS labels or the port CSV status.
 current={ident:record.get('status','NOT RUN') for suite in suites for ident,record in suite.get('tests',{}).items()}
 for row in history:
  if row['rc5_applicability']=='APPLICABLE':
   ident=ports.get(row['rc4_case']) or row['rc5_port_case']
   if not ident or current.get(ident)!='PASS':missing.append('Historical applicable case not verified: '+row['rc4_case'])
 for name in REQUIRED_EVIDENCE:
  if required_evidence.get(name)!='PASS':missing.append('Required external evidence incomplete: '+name)
 return {'release_status':'NOT ACCEPTED' if hard else 'INCOMPLETE' if missing else 'ACCEPTED','exit_code':1 if hard else 2 if missing else 0,'release_allowed':not hard and not missing,'hard_errors':hard,'missing_evidence':missing}


def release_check(summary):
    """Re-evaluate complete evidence; labels alone never authorize release."""
    if summary.get("format_version") != 2 or summary.get("runner_status") != "COMPLETED":
        return {"release_allowed": False, "exit_code": 3, "release_status": "NOT ACCEPTED", "reason": "Missing/invalid completed runner evidence"}
    data = summary.get("validation_inputs", {})
    if not isinstance(data, dict):
        return {"release_allowed": False, "exit_code": 3, "release_status": "NOT ACCEPTED", "reason": "Invalid validation inputs"}
    verdict = evaluate(data.get("suites", []), data.get("static", {}), data.get("required_evidence", {}))
    if summary.get("release_status") != "ACCEPTED" or summary.get("release_allowed") is not True or summary.get("exit_code") != 0:
        verdict["release_allowed"] = False
        verdict["exit_code"] = verdict["exit_code"] or 2
        if verdict["release_status"] == "ACCEPTED":
            verdict["release_status"] = "INCOMPLETE"
    return verdict
