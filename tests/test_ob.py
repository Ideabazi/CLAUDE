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
        # Allowed regions beyond the US; non-CXO titles never qualify
        self.assertEqual(self.show("li-0009")["stage"], "qualified")
        self.assertEqual(self.show("li-0009")["country"], "norway")
        self.assertEqual(self.show("li-0010")["disq_reason"], "title")

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

    def test_enforce_disqualifies_worked_contacts(self):
        self.run_ob("import-linkedin", "examples/sample_connections.csv")
        self.run_ob("qualify")
        research = Path(self.tmp.name) / "r.json"
        research.write_text(json.dumps([{"id": "li-0001", "stage": "nurture"}]))
        self.run_ob("research-in", str(research))
        # li-0001 has no location: fine for a fresh import, not for someone being worked
        self.run_ob("qualify", "--enforce")
        c = self.show("li-0001")
        self.assertEqual(c["stage"], "disqualified")
        self.assertEqual(c["disq_reason"], "geo-unknown")

    def test_apply_page_actions(self):
        self.run_ob("import-linkedin", "examples/sample_connections.csv")
        self.run_ob("qualify")
        acts = Path(self.tmp.name) / "a.json"
        acts.write_text(json.dumps([
            {"_id": "a2", "contact_id": "li-0002", "event": "hold", "note": "", "created_at": "2026-10-27T09:00:00Z"},
            {"_id": "a1", "contact_id": "li-0001", "event": "replied", "sentiment": "interested", "note": "call Thu", "created_at": "2026-10-27T08:00:00Z"},
            {"_id": "a3", "contact_id": "li-9999", "event": "won", "created_at": "2026-10-27T10:00:00Z"},
        ]))
        out = json.loads(self.run_ob("apply-actions", str(acts)).strip().splitlines()[-1])
        self.assertEqual(out["applied"], ["a1", "a2"])
        self.assertEqual(len(out["skipped"]), 1)
        self.assertEqual(self.show("li-0001")["stage"], "replied")
        self.assertEqual(self.show("li-0002")["stage"], "nurture")

    def test_page_sent_and_accepted(self):
        self.run_ob("import-linkedin", "examples/sample_connections.csv")
        self.run_ob("import-csv", "examples/sample_salesnav.csv", "--source", "salesnav")
        self.run_ob("qualify")
        research = Path(self.tmp.name) / "r.json"
        research.write_text(json.dumps([
            {"id": "li-0006", "signal": 3, "pain": 3, "capacity": 3,
             "messages": [{"step": 0, "channel": "linkedin_connect", "body": "note"},
                          {"step": 1, "channel": "linkedin_dm", "body": "dm"}]}]))
        self.run_ob("research-in", str(research))
        self.run_ob("approve", "li-0006")
        self.run_ob("plan", "--volume", "5", "--date", "2026-11-03")
        acts = Path(self.tmp.name) / "a.json"
        acts.write_text(json.dumps([
            {"_id": "s1", "contact_id": "li-0006", "event": "sent", "created_at": "2026-11-03T18:00:00Z"},
            {"_id": "s2", "contact_id": "li-0006", "event": "accepted", "created_at": "2026-11-04T18:00:00Z"},
        ]))
        out = json.loads(self.run_ob("apply-actions", str(acts)).strip().splitlines()[-1])
        self.assertEqual(out["applied"], ["s1", "s2"])
        c = self.show("li-0006")
        self.assertEqual(c["step"], 1)
        self.assertEqual(c["next_touch_due"], "2026-11-06")

    def test_backup_round_trip_through_dashboard(self):
        self.run_ob("import-linkedin", "examples/sample_connections.csv")
        self.run_ob("qualify")
        self.run_ob("log", "li-0001", "note", "--note", "has </script> in it")
        page = Path(self.tmp.name) / "page.html"
        self.run_ob("dashboard", "--artifact", "--out", str(page))
        fresh = os.environ | {"OB_DB": str(Path(self.tmp.name) / "fresh" / "t.db")}
        r = subprocess.run(OB + ["restore", str(page)], env=fresh, capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("5 contacts", r.stdout)
        r = subprocess.run(OB + ["show", "li-0001"], env=fresh, capture_output=True, text=True, cwd=ROOT)
        self.assertIn("</script>", json.loads(r.stdout)["touches"][0]["detail"])


if __name__ == "__main__":
    unittest.main()
