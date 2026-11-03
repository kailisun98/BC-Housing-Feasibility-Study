"""The refresh plan: a moved series appends a dated version and rewrites the summary; an unchanged one is reported
current; nothing is edited in place. Pure: fetched data is handed in, no network."""

import copy
import json
import unittest
from datetime import date
from pathlib import Path

from ffm import refresh

ROOT = Path(__file__).resolve().parent.parent
DOC = json.loads((ROOT / "rules" / "f_assumptions.json").read_text(encoding="utf-8"))


class Plan(unittest.TestCase):
    def test_unchanged_series_are_current_and_nothing_is_written(self):
        esc = next(r for r in DOC["rules"] if r["id"] == "f.escalation_bcpi")["versions"][-1]["params"]
        mtg = next(r for r in DOC["rules"] if r["id"] == "f.mortgage")["versions"][-1]["params"]
        bcpi = {"vector": esc["vector"], "observations": dict(esc["observations"]), "released": esc["released"]}
        boc = {"date": mtg["rate_date"], "value": mtg["rate_pct"], "label": "Conventional mortgage, 5-year"}
        rep = refresh.plan(copy.deepcopy(DOC), bcpi, boc, date(2026, 11, 3))
        self.assertEqual({i["status"] for i in rep["items"]}, {"current"})
        self.assertEqual(rep["new_versions"], {})
        self.assertTrue(any("CMHC" in n for n in rep["by_hand"]))

    def test_a_new_quarter_appends_a_version_dated_at_release(self):
        esc = next(r for r in DOC["rules"] if r["id"] == "f.escalation_bcpi")["versions"][-1]["params"]
        obs = dict(esc["observations"])
        obs["2026-10-01"] = 110.2
        rep = refresh.plan(copy.deepcopy(DOC), {"vector": esc["vector"], "observations": obs, "released": "2027-01-28"}, None, date(2027, 2, 1))
        nv = rep["new_versions"]["f.escalation_bcpi"]
        self.assertEqual(nv["effective_from"], "2027-01-28")
        self.assertEqual(nv["params"]["latest_value"], 110.2)
        self.assertEqual(nv["params"]["latest_period"], "2026-10-01")
        self.assertIn("110.2 in the fourth quarter of 2026", nv["params"]["summary"])
        self.assertIn("escalation 1.039", nv["params"]["summary"])
        doc = copy.deepcopy(DOC)
        written = refresh.apply(doc, rep["new_versions"])
        self.assertEqual(written, ["f.escalation_bcpi"])
        r = next(r for r in doc["rules"] if r["id"] == "f.escalation_bcpi")
        self.assertEqual(len(r["versions"]), 2)
        self.assertEqual(r["versions"][0]["params"]["latest_value"], 109.4)   # the old version is untouched

    def test_a_rate_change_appends_a_mortgage_version(self):
        rep = refresh.plan(copy.deepcopy(DOC), None, {"date": "2026-11-04", "value": 5.99, "label": "x"}, date(2026, 11, 5))
        nv = rep["new_versions"]["f.mortgage"]
        self.assertEqual(nv["effective_from"], "2026-11-04")
        self.assertEqual(nv["params"]["rate_pct"], 5.99)
        self.assertIn("5.99%", nv["params"]["summary"])
        self.assertEqual(next(i for i in rep["items"] if i["rule_id"] == "f.escalation_bcpi")["status"], "unreached")


if __name__ == "__main__":
    unittest.main()
