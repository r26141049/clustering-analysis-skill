"""R4H.1 safe chat output regression; never refits scientific models."""
import re
import tempfile
import unittest
from pathlib import Path

from PIL import Image
import pandas as pd

from clustering_native.cli import dispatch
from clustering_native.figures import preview_assets
from clustering_native.presentation import attachment_batch


class R4H1ChatLayout(unittest.TestCase):
    def test_all_stage_links_are_independent_plain_text_and_unverified(self):
        with tempfile.TemporaryDirectory() as folder:
            files = [Path(folder)/name for name in ('quality and sizes.png', 'stability.png', 'selected.png')]
            for file in files:
                Image.new('RGB', (40, 25)).save(file)
            for stage in range(1, 6):
                batch = attachment_batch(files, stage)
                self.assertEqual(batch['attachment_count'], 3)
                self.assertEqual(batch['chat_layout_contract']['presentation'], 'single_column_plain_markdown_links')
                self.assertEqual(batch['chat_layout_contract']['image_embedding'], 'PROHIBITED_IN_CHAT')
                self.assertEqual(batch['attachment_delivery'], 'NOT RUN')
                self.assertEqual(batch['inline_display'], 'UNVERIFIED')
                self.assertNotIn('data:image', str(batch))
                self.assertNotIn('![', batch['attachment_markdown'])
                self.assertNotIn('<img', batch['attachment_markdown'])
                self.assertNotIn('|', batch['attachment_markdown'])
                paragraphs = batch['attachment_markdown'].split('\n\n')
                self.assertEqual(len(paragraphs), 3)
                for paragraph, file, receipt in zip(paragraphs, files, batch['receipts']):
                    self.assertEqual(paragraph.count(']('), 1)
                    self.assertIn('<sandbox:'+str(file.resolve())+'>', paragraph)
                    self.assertEqual(receipt['file_output'], 'PASS')
                    self.assertEqual(receipt['attachment_user_opened'], 'UNVERIFIED')
                    self.assertEqual(len(receipt['sha256']), 64)

    def test_no_files_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'No validated stage PNGs'):
            attachment_batch([], 4)

    def test_preview_instructions_are_no_longer_inline_first(self):
        with tempfile.TemporaryDirectory() as folder:
            svg = Path(folder)/'study.svg'
            png = Path(folder)/'study.png'
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="30"/>')
            Image.new('RGB', (40, 30)).save(png)
            records = preview_assets([svg])
            self.assertEqual(records[0]['status'], 'PNG_PREVIEW_READY')
            self.assertIn('stage_attachments', records[0]['operator_action'])
            self.assertNotIn('functions.image', records[0]['operator_action'])
            self.assertNotIn('inline Markdown image', records[0]['operator_action'])

    def test_legacy_cli_does_not_expose_multimodal_image_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            csv=root/'observations.csv'
            pd.DataFrame({'bill':[5., 6., 7., 8., 9., 10., 11., 12.],
                          'day':['Mon','Tue','Mon','Wed','Tue','Thu','Wed','Fri']}).to_csv(csv,index=False)
            study=root/'study'
            dispatch({'action':'create','session':str(study),'csv':str(csv)})
            attachments=dispatch({'action':'stage_attachments','session':str(study),'stage':1})
            legacy=dispatch({'action':'present_figures','session':str(study),'stage':1,
                             'start':0,'limit':1})
            self.assertEqual(legacy['legacy_action_redirected'], 'stage_attachments')
            self.assertEqual(legacy['legacy_inline_image_content'], 'DISABLED_FOR_CHAT_LAYOUT_SAFETY')
            self.assertNotIn('content', legacy)
            self.assertNotIn('data:image/png;base64,', str(legacy))
            self.assertEqual(legacy['attachment_count'], attachments['attachment_count'])
            self.assertEqual(legacy['attachment_markdown'], attachments['attachment_markdown'])
            self.assertEqual([r['sha256'] for r in legacy['receipts']],
                             [r['sha256'] for r in attachments['receipts']])
            self.assertEqual(dispatch({'action':'status','session':str(study)})['phase'], 'S1_ROLE_REVIEW')

if __name__ == '__main__':
    unittest.main()
