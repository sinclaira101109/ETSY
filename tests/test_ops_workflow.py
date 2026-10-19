import csv
import tempfile
import unittest
from pathlib import Path
from ops_workflow import parse_tags, run

class WorkflowTest(unittest.TestCase):
 def test_tags(self):
  self.assertEqual(parse_tags("rose gift, towel flower; hostess gift"),["rose gift","towel flower","hostess gift"])
 def test_draft_only_and_source_unchanged(self):
  with tempfile.TemporaryDirectory() as root:
   base=Path(root);src=base/"in";src.mkdir()
   file=src/"test.csv"
   with file.open("w",encoding="utf-8",newline="") as stream:
    w=csv.DictWriter(stream,fieldnames=["title","tags","material"])
    w.writeheader();w.writerow({"title":"Towel Rose Gift Box","tags":"towel gift, rose box","material":"cotton"})
   original=file.read_bytes()
   folder,report=run(src,base/"out","TestShop")
   self.assertEqual(report["outbound_actions"],0)
   self.assertEqual(report["products_reviewed"],1)
   self.assertEqual(file.read_bytes(),original)
   self.assertTrue((folder/"sku_audit.csv").exists())
   self.assertIn("NEEDS_CONFIRMATION",(folder/"sku_audit.csv").read_text(encoding="utf-8-sig"))
   self.assertTrue((folder/"outreach_drafts.md").exists())
if __name__=="__main__":unittest.main()
