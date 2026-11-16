"""Independent synthetic 312-observation, 180-resample engineering stress fixture.

Never reads a user's study snapshots and never invokes authorization APIs.
This checks the runtime mechanism only, not Stage 5 scientific acceptance.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import time
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from clustering_native.engine import bounded_fit,stability
from clustering_native.core import digest


def run():
    rng=np.random.default_rng(20261116)
    centers=np.array([[-2.5,-2.,0.], [2.5,1.5,2.], [-.2,3.8,-1.]])
    X=np.vstack([rng.normal(c,.6,size=(104,3)) for c in centers])
    data=pd.DataFrame(X,columns=['x','y','z'])
    schema={c:{'type':'numeric'} for c in data}
    weights={c:1.0 for c in data}
    plan={'schema':schema,'weights':weights}
    budget={'memory_mb':128,'seconds_per_fit':8,'max_rows':312,'max_candidates':9}
    configs=[{'metric':'euclidean','linkage':method,'k':k} for method,k in
             [('ward',2),('ward',3),('ward',4),('ward',5),('ward',6),
              ('average',3),('average',5),('complete',3),('complete',5)]]
    with tempfile.TemporaryDirectory() as location:
        audit=Path(location)/'runtime_events.jsonl'
        result=[]
        start=time.perf_counter()
        for index,config in enumerate(configs):
            chosen=bounded_fit(data,schema,weights,'hierarchical',config,budget)
            diagn=stability(data,data,plan,'hierarchical',chosen,budget,.8,20,17,
                            'fixed_full_data_preprocessing',audit_path=audit,candidate_index=index)
            result.append(diagn)
        elapsed=time.perf_counter()-start
        events=[json.loads(line) for line in audit.read_text(encoding='utf-8').splitlines()]
        summary={'test_kind':'SYNTHETIC_ENGINEERING_ONLY', 'observations':312,
                 'candidates':len(configs), 'repeats_per_candidate':20,
                 'events':len(events), 'statuses':{s:sum(e['status']==s for e in events)
                    for s in ['SUCCESS','TIMEOUT','ERROR']},
                 'cold_worker_calls':sum(not e['reused_worker'] for e in events),
                 'elapsed_seconds':round(elapsed,3),
                 'candidate_digest_count':len([digest(x) for x in result]),
                 'audit_separated_from_science':all('elapsed_seconds' not in x for v in result for x in v['runs'])}
    if summary['events']!=180 or summary['statuses']['ERROR']:
        raise AssertionError(summary)
    print(json.dumps(summary,indent=2))

if __name__=='__main__': run()
