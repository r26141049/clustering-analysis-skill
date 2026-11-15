"""Presentation-only regression; never fits research models."""
import unittest
import tempfile
from pathlib import Path
from PIL import Image
from clustering_native.presentation import attachment_batch

class Attachments(unittest.TestCase):
    def test_all_stages_and_all_files(self):
        with tempfile.TemporaryDirectory() as d:
            paths=[Path(d)/'a space.png', Path(d)/'b.png']
            for p in paths: Image.new('RGB',(4,4)).save(p)
            for stage in range(1,6):
                r=attachment_batch(paths,stage)
                self.assertEqual(r['attachment_count'],2)
                self.assertEqual(r['attachment_delivery'],'NOT RUN')
                self.assertEqual(r['inline_display'],'UNVERIFIED')
                for p,receipt in zip(paths,r['receipts']):
                    self.assertIn('<sandbox:'+str(p)+'>',r['attachment_markdown'])
                    self.assertEqual(receipt['file_output'],'PASS')
                    self.assertEqual(receipt['attachment_user_opened'],'UNVERIFIED')
    def test_corrupt_and_missing_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.png';p.write_bytes(b'not png')
            with self.assertRaises(Exception):attachment_batch([p],1)
            with self.assertRaises(FileNotFoundError):attachment_batch([p.parent/'missing.png'],1)
    def test_invalid_stage(self):
        with self.assertRaises(ValueError):attachment_batch([],0)
if __name__=='__main__':unittest.main()
