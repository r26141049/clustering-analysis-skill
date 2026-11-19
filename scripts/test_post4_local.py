"""New local regression tests of the post4 recovery work."""
import unittest
import numpy as np
import pandas as pd
from clustering_native.report_code import stage_block
from clustering_native.report_explanations import (
    preprocessing_findings, dominant_feature_findings, selection_warnings)
from clustering_native.privacy import public_output


class LocalPost4Test(unittest.TestCase):
    def test_adjacency_snippets(self):
        for stage in range(1, 6):
            block = stage_block(stage)
            self.assertIn('```python', block)
            self.assertIn('config.json', block)
            self.assertIn('```', block)

    def test_purity_detects_one_categorical_column_dominating(self):
        frame=pd.DataFrame({'tier':['Bronze','Bronze','Silver','Silver'],
                            'amount':[1.,2.,3.,4.]})
        schema={'tier':{'type':'nominal'},'amount':{'type':'numeric'}}
        text=dominant_feature_findings(frame,[0,0,1,1],schema)
        self.assertIn('1.0000',text)
        self.assertIn('重要限制',text)

    def test_preprocessing_reports_missing_and_case(self):
        raw=pd.DataFrame({'region':['North','north',None], 'age':[10.,None,30.]})
        model=pd.DataFrame({'region':['North','north','North'], 'age':[10.,20.,30.]})
        plan={'weights':{'region':1,'age':1},'actions':{'region':{},'age':{}}}
        text=preprocessing_findings(raw,model,plan)
        self.assertIn('類別大小寫不一致',text)
        self.assertIn('可能人為增加相似性',text)

    def test_boundary_warning_favors_range_extension_not_auto(self):
        results=[{'config':{'k':2},'labels':[0,0,1,1],
                  'metrics':{'silhouette':.2}},
                 {'config':{'k':3},'labels':[0,1,2,2],
                  'metrics':{'silhouette':.4}}]
        self.assertIn('邊界警示',selection_warnings(results,1))
        self.assertIn('新的 Stage 3 授權',selection_warnings(results,1))

    def test_public_hide_auth_fields(self):
        value={'token':'badtoken', 'expires_at':'tomorrow',
               'decisions':[{'stage':3,'nonce':'x','expires_at':'time'}]}
        self.assertEqual(public_output(value),{'decisions':[{'stage':3}]})

if __name__=='__main__': unittest.main()
