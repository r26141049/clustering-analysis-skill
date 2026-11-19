import unittest,tempfile,base64
from pathlib import Path
from html.parser import HTMLParser
from PIL import Image
from clustering_native.presentation import offline_html
from clustering_native.privacy import public_output
from clustering_native.education import DISCLOSURE, study_disclosure, planned_evidence
from clustering_native.engine import validate_config
class Post4(unittest.TestCase):
 def test_mask_nested_private_fields(self):
  self.assertEqual(public_output({'token':'secret','pending':{'expires_at':'tomorrow','nonce':'x','stage':1}}),{'pending':{'stage':1}})
 def test_semantic_html_and_escaping(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);Image.new('RGB',(2,3)).save(p/'x.png')
   md='# Stage 1\n\n|a|b|\n|---|---|\n|1|2|\n\n```python\nprint("<script>evil</script>")\n```\n\n![plot](x.png)'
   html=offline_html(md,p)
   for marker in ['<h1>Stage 1</h1>','<table>','class="language-python"','&lt;script&gt;',base64.b64encode((p/'x.png').read_bytes()).decode()]:self.assertIn(marker,html)
   self.assertNotIn('<script>',html);self.assertNotIn('<pre>#',html)
 def test_traversal(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):offline_html('![x](../x.png)',d)
 def test_four_linkages_and_distance_guard(self):
  for linkage in ['single','complete','average','ward']:
   validate_config('hierarchical',dict(metric='euclidean',k=3,linkage=linkage),20)
  with self.assertRaises(ValueError):validate_config('hierarchical',dict(metric='gower',k=3,linkage='ward'),20)
 def test_before_decision_disclosures(self):
  configs=[{'metric':'gower','linkage':'average','k':3}]
  text=study_disclosure('hierarchical',configs,planned_evidence('hierarchical',configs))
  for word in ['Gower','Average','Silhouette','ARI','δ_ijk']:self.assertIn(word,text)
  for unused in ['Jaccard','K-means','Davies–Bouldin']:self.assertNotIn(unused,text)
 def test_unclosed_code_rejected(self):
  with self.assertRaises(ValueError):offline_html('```python\nx=1','.')
if __name__=='__main__':unittest.main()
