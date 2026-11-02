"""The rule-derived suggestion: the real site should come back funder-ready and near the funder-ready what-if; a
CD-1 site mostly unsure; a small lot at the SSMUH minimum; the same inputs the same suggestion."""

import copy
import json
import unittest
from datetime import date
from pathlib import Path

from ffm import suggest
from ffm.engine import evaluate, load_json

ROOT = Path(__file__).resolve().parent.parent
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
EXPO = load_json(ROOT / "sites" / "1010-expo-blvd.json")
AS_OF = date(2026, 10, 23)
PROGRAMS = ["bch.chf.eligibility", "bc.bcbuilds.eligibility"]


class FunderReady(unittest.TestCase):
    def setUp(self):
        self.S = suggest.suggest(SITE, PROGRAMS, AS_OF, "funder-ready")
        self.o = self.S["option"]

    def test_envelope_sits_inside_the_benchmark(self):
        self.assertEqual(self.o["storeys"], 6)
        self.assertLessEqual(self.o["height_m"], 21.3)
        self.assertAlmostEqual(self.o["gfa_m2"] / SITE["site_area_m2"], 3.0, places=2)
        self.assertEqual(self.S["fields"]["storeys"]["rule_id"], "cov.irp.social_housing_rezoning")
        self.assertIn("Interim Rezoning Policy", self.o["rezoning_path"])

    def test_unit_mix_clears_the_family_minimums(self):
        u = self.o["units"]
        n = sum(u.values())
        self.assertGreater(n, 60)
        self.assertGreaterEqual((u["two_bed"] + u["three_bed_plus"]) / n, 0.35)
        self.assertGreaterEqual(u["three_bed_plus"] / n, 0.05)

    def test_tiers_and_accessible_units_follow_the_fund(self):
        n = sum(self.o["units"].values())
        t = self.o["rent_tiers_units"]
        self.assertEqual(sum(t.values()), n)
        for k, share in (("market", .30), ("rgi", .50), ("deep_subsidy", .20)):
            self.assertLessEqual(abs(t[k] / n - share), 0.02)
        self.assertGreaterEqual(self.o["accessible_units"] / n, 0.05)

    def test_trees_cover_schedule_c(self):
        # 20 required on 2,811 m², one retained
        self.assertEqual(self.o["replacement_trees_proposed"], 19)

    def test_the_engine_reads_it_as_rezonable_and_the_funders_wait_only_on_people(self):
        L = evaluate(SITE, self.o, AS_OF)
        a = L["summary"]["answers"]
        self.assertEqual(a["allowed"]["outright"]["verdict"], "no")
        self.assertIn(a["allowed"]["by_rezoning"]["verdict"], ("yes", "yes, with conditions"))
        self.assertEqual(L["results"][[r["rule_id"] for r in L["results"]].index("cov.family_units")]["status"], "pass")
        self.assertEqual(L["results"][[r["rule_id"] for r in L["results"]].index("cov.trees.replacement")]["status"], "pass")
        # what is left is what a person settles: site control, tenure, the developer partner
        keys = {u["key"] for u in self.S["unsure"]}
        self.assertTrue({"site_control", "land_tenure_plan", "developer_partner"} <= keys)

    def test_every_figure_names_its_rule_or_says_placeholder(self):
        for key, f in self.S["fields"].items():
            self.assertIn("note", f, key)
        self.assertEqual(self.S["fields"]["units.two_bed"]["rule_id"], "bch.design_guidelines.unit_areas")
        self.assertIsNone(self.S["fields"]["setbacks_m.front"]["rule_id"])

    def test_deterministic(self):
        again = suggest.suggest(copy.deepcopy(SITE), list(PROGRAMS), AS_OF, "funder-ready")
        self.assertEqual(json.dumps(again["option"], sort_keys=True), json.dumps(self.o, sort_keys=True))


class OtherCandidates(unittest.TestCase):
    def test_outright_is_three_storeys_at_fsr_1_2(self):
        S = suggest.suggest(SITE, PROGRAMS, AS_OF, "outright")
        self.assertEqual(S["option"]["storeys"], 3)
        self.assertLessEqual(S["option"]["height_m"], 10.7)
        self.assertAlmostEqual(S["option"]["gfa_m2"] / SITE["site_area_m2"], 1.2, places=2)
        self.assertIsNone(S["option"]["rezoning_path"])
        self.assertIsNone(S["option"]["rent_tiers_units"])

    def test_benchmark_has_the_envelope_but_not_the_funder_fields(self):
        S = suggest.suggest(SITE, PROGRAMS, AS_OF, "benchmark")
        self.assertEqual(S["option"]["storeys"], 6)
        self.assertIsNone(S["option"]["accessible_units"])

    def test_cd1_site_comes_back_unsure_on_the_envelope(self):
        S = suggest.suggest(EXPO, PROGRAMS, AS_OF, "funder-ready")
        self.assertIsNone(S["option"]["gfa_m2"])
        keys = {u["key"] for u in S["unsure"]}
        self.assertIn("gfa_m2", keys)
        self.assertIn("zoning_district", keys)
        self.assertFalse(next(c for c in S["candidates"] if c["id"] == "outright")["available"])

    def test_small_lot_gets_the_ssmuh_minimum(self):
        small = {"id": "small", "address": "a small lot", "zoning_district": "R1-1", "site_area_m2": 280, "frontage_m": 10, "depth_m": 28,
                 "has_water_and_sewer": True, "in_transit_oriented_area": False, "frequent_bus_stop_within_400m": False, "existing_trees_on_site": []}
        S = suggest.suggest(small, [], AS_OF, "outright")
        self.assertEqual(S["fields"]["ssmuh_minimum_units"]["value"], 3)
        self.assertEqual(sum(S["option"]["units"].values()), 3)
        self.assertIn("gfa_m2", {u["key"] for u in S["unsure"]})


class ReadSite(unittest.TestCase):
    def test_reads_layers_a_to_c_without_an_option(self):
        R = suggest.read_site(SITE, AS_OF)
        ids = {r["rule_id"] for r in R["results"]}
        self.assertIn("cov.irp.social_housing_rezoning", ids)
        self.assertIn("cov.trees.replacement", ids)
        self.assertTrue(all(r["layer"] in "ABC" for r in R["results"]))


if __name__ == "__main__":
    unittest.main()
