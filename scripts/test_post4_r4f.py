"""R4F actual-evidence-only presentation and planned-indicator interpretation."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
from clustering_native.education import planned_evidence, study_disclosure
from clustering_native.presentation import (REAL_RESEARCH_FIGURES_ONLY, attachment_batch,
                                              image_batch, offline_html)
from clustering_native.cli import dispatch

class R4FPresentationAndMetrics(unittest.TestCase):
    def test_silhouette_and_ari_explain_what_is_measured_before_direction(self):
        plan=planned_evidence('dbscan',[{'metric':'euclidean','eps':0.2,'min_samples':6}])
        self.assertIn('同群其他觀測的平均距離',plan['silhouette'])
        self.assertIn('最近其他群的平均距離',plan['silhouette'])
        self.assertIn('越高',plan['silhouette'])
        self.assertIn('原本全資料分群與重抽樣重新擬合',plan['resampling_ari'])
        self.assertIn('共同觀測',plan['resampling_ari'])
        self.assertIn('不是用真實群組標籤',plan['resampling_ari'])
        self.assertNotIn('wcss',plan)
        disclosure=study_disclosure('dbscan',[{'metric':'euclidean','eps':.2,'min_samples':6}],plan)
        self.assertIn('最近其他群',disclosure)
        self.assertIn('重抽樣重新擬合',disclosure)
        self.assertNotIn('Jaccard',disclosure)

    def test_study_specific_metrics_still_not_generic_catalog(self):
        for method,cfg in [('kmeans',{'metric':'euclidean','k':2}),
                           ('pam',{'metric':'gower','k':2}),
                           ('hierarchical',{'metric':'euclidean','k':2,'linkage':'ward'})]:
            evidence=planned_evidence(method,[cfg])
            self.assertIn('silhouette',evidence)
            self.assertIn('resampling_ari',evidence)
            self.assertNotIn('noise_fraction',evidence)
            self.assertTrue(all(len(value)>20 for value in evidence.values()))

    def test_session_figures_only_and_no_external_substitutes(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            # Synthetic fixtures used only by automated tests, not user research.
            rng=np.random.default_rng(9)
            x=pd.DataFrame({'x':rng.normal(size=20),'y':rng.normal(size=20)})
            csv=base/'input.csv'; x.to_csv(csv,index=False)
            session=base/'study'
            created=dispatch({'action':'create','session':str(session),'csv':str(csv)})
            self.assertIn('禁止網路圖片',created['image_source_policy'])
            output=dispatch({'action':'stage_attachments','session':str(session),'stage':1})
            self.assertGreaterEqual(output['attachment_count'],2)
            self.assertIn('禁止網路圖片',output['image_source_policy'])
            for receipt in output['receipts']:
                self.assertTrue(Path(receipt['path']).is_relative_to(session))
                self.assertTrue(Path(receipt['path']).is_file())
                self.assertEqual(len(receipt['sha256']),64)
                self.assertTrue(receipt['path'].endswith('.png'))
            first=output['receipts'][0]['path']
            displayed=dispatch({'action':'present_figures','session':str(session),'stage':1,
                                'start':0,'limit':1})
            self.assertIn('禁止網路圖片',displayed['image_source_policy'])
            self.assertEqual(displayed['receipts'][0]['path'],first)

    def test_offline_html_only_embeds_existing_local_png(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            Image.new('RGB',(5,5)).save(root/'real.png')
            html=offline_html('# Actual study\n\n![real](real.png)\n',root)
            self.assertIn('data:image/png;base64,',html)
            self.assertNotIn('<script',html)
            with self.assertRaises((ValueError,FileNotFoundError)):
                offline_html('# Study\n\n![outside](https://example.org/demonstration.png)\n',root)
            batch=attachment_batch([root/'real.png'],4)
            self.assertIn('禁止網路圖片',batch['image_source_policy'])
            self.assertIn('do not search for',batch['required_action'])

if __name__=='__main__': unittest.main()
