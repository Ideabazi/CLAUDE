import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OB = [sys.executable, str(ROOT / "crm" / "ob.py")]


class CrmFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = os.environ | {"OB_DB": str(Path(self.tmp.name) / "t.db")}
        self.run_ob("init")

    def tearDown(self):
        self.tmp.cleanup()

    def run_ob(self, *args):
        r = subprocess.run(OB + list(args), env=self.env, capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def show(self, cid):
        return json.loads(self.run_ob("show", cid))

    def test_import_qualify_sequence(self):
        self.run_ob("import-linkedin", "examples/sample_connections.csv")
        self.run_ob("import-csv", "examples/sample_salesnav.csv", "--source", "salesnav")
        self.run_ob("qualify")
        # VP and Product Owner are not decision-makers; UK and 1200 employees fail geo/size
        self.assertEqual(self.show("li-0003")["stage"], "disqualified")
        self.assertEqual(self.show("li-0005")["stage"], "disqualified")
        self.assertEqual(self.show("li-0007")["disq_reason"], "geo")
        self.assertEqual(self.show("li-0008")["disq_reason"], "size")
        self.assertEqual(self.show("li-0006")["degree"], 2)

        research = Path(self.tmp.name) / "r.json"
        research.write_text(json.dumps([
            {"id": "li-0006", "signal": 3, "pain": 3, "capacity": 3,
             "messages": [{"step": 0, "channel": "linkedin_connect", "body": "note"},
                          {"step": 1, "channel": "linkedin_dm", "body": "dm"}]}]))
        self.run_ob("research-in", str(research))
        self.run_ob("approve", "li-0006")
        out = self.run_ob("plan", "--volume", "5", "--date", "2026-11-03")
        self.assertIn("li-0006", out)
        # Re-planning the same day must not start more contacts
        self.run_ob("plan", "--volume", "5", "--date", "2026-11-03")
        self.assertEqual(self.show("li-0006")["seq_started"], "2026-11-03")

        self.run_ob("log", "li-0006", "sent", "--at", "2026-11-03T09:00:00")
        c = self.show("li-0006")
        self.assertEqual(c["step"], 1)
        self.assertEqual(c["next_touch_due"], "2026-11-06")
        # DM is blocked until the invite is accepted
        self.assertIn("no reachable step", self.run_ob("plan", "--date", "2026-11-06", "--volume", "0"))
        self.run_ob("log", "li-0006", "accepted")
        self.assertIn("linkedin_dm", self.run_ob("plan", "--date", "2026-11-06", "--volume", "0"))

        self.run_ob("log", "li-0006", "replied", "--sentiment", "interested")
        self.assertEqual(self.show("li-0006")["stage"], "replied")
        self.assertIn("100%", self.run_ob("metrics"))


if __name__ == "__main__":
    unittest.main()
