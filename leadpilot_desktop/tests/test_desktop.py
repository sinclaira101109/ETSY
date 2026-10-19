import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from leadpilot_desktop import normalize_rows, csv_bytes, draft, SEGMENTS

class TestLeadPilotDesktop(unittest.TestCase):
 def test_segments_and_draft(self):
  self.assertGreaterEqual(len(SEGMENTS),5)
  msg=draft("Gift boutiques")
  self.assertIn("won't follow up",msg)
  self.assertIn("{company_name}",msg)
 def test_csv_roundtrip(self):
  rows=normalize_rows("Company,Email,Status\nGift Shop,hi@example.com,New\n")
  self.assertEqual(rows[0]["Company"],"Gift Shop")
  again=normalize_rows(csv_bytes(rows).decode("utf-8-sig"))
  self.assertEqual(again[0]["Email"],"hi@example.com")
 def test_missing_header_fails(self):
  with self.assertRaises(ValueError):
   normalize_rows("Email,Name\nhello@example.com,A\n")
if __name__=="__main__":unittest.main()
