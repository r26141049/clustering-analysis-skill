"""B-class report snippets: self-contained execution and exact ARI aggregation."""
import ast
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from clustering_native.report_code import stage_block


class BReportFidelity(unittest.TestCase):
    def test_each_stage_snippet_is_valid_python_with_archived_module_bootstrap(self):
        for stage in range(1,6):
            code=stage_block(stage)
            self.assertIn('reproducibility',code)
            src=code.split('```python\n',1)[1].split('\n```',1)[0]
            compile(src,f'report_stage_{stage}.py','exec')

    def test_stage4_ari_matches_archived_repeats_without_package_install(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)
            code_dir=Path(__file__).resolve().parent.parent/'clustering_native'
            shutil.copytree(code_dir,out/'reproducibility'/'clustering_native',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            payloads={
                'config.json':{'preprocessing_plan':{'schema':{'x':{'type':'numeric'}}},'method':'kmeans'},
                'raw_feature_snapshot.json':{'x':[1,2,3,4]},
                'model_feature_snapshot.json':{'x':[1,2,3,4]},
                'candidate_results.json':[{'config':{'metric':'euclidean','k':2},'metrics':{'silhouette':.5},'labels':[0,0,1,1]}],
                'diagnostics.json':{'stability':[{'runs':[{'ari':.8},{'ari':None},{'ari':.4}], 'failures':1}]},
            }
            for name,value in payloads.items():
                (out/name).write_text(json.dumps(value),encoding='utf-8')
            code=stage_block(4).split('```python\n',1)[1].split('\n```',1)[0]
            env=__import__('os').environ.copy();env.pop('PYTHONPATH',None)
            result=subprocess.run([sys.executable,'-c',code],cwd=out,capture_output=True,text=True,env=env,timeout=25)
            self.assertEqual(result.returncode,0,result.stderr)
            observed=ast.literal_eval(result.stdout.strip())
            self.assertAlmostEqual(observed['ari_mean'],.6)
            self.assertEqual(observed['valid_repeats'],2)
            self.assertEqual(observed['failed_repeats'],1)
            self.assertNotIn('jaccard',result.stdout.lower())


if __name__=='__main__':unittest.main()
