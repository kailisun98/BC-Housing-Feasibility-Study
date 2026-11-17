"""The rule-derived suggestion: the real site should come back funder-ready and near the funder-ready what-if; a
CD-1 site mostly unsure; a small lot at the SSMUH minimum; the same inputs the same suggestion."""

import copy
import json
import unittest
from datetime import date
from pathlib import Path

from ffm import massing, suggest
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
        # since 16 Nov 2026 the rough envelope fills the figures (basis "envelope", no rule); the unsure item stays
        S = suggest.suggest(EXPO, PROGRAMS, AS_OF, "funder-ready")
        self.assertEqual(S["option"]["storeys"], 6)
        self.assertGreater(S["option"]["gfa_m2"], 0)
        for k in ("storeys", "height_m", "gfa_m2"):
            self.assertEqual(S["fields"][k]["basis"], "envelope")
            self.assertIsNone(S["fields"][k]["rule_id"])
            self.assertIn("not a permitted figure", S["fields"][k]["note"])
        self.assertIn("stand in until the schedule is read", next(u for u in S["unsure"] if u["key"] == "gfa_m2")["why"])
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


class Envelope(unittest.TestCase):
    def test_demo_site_envelope_from_the_schedule_capped_by_fsr(self):
        E = suggest.suggest(SITE, PROGRAMS, AS_OF, "funder-ready")["envelope"]
        self.assertEqual(set(E), {"storeys", "height_m", "gfa_m2", "plate_m2", "plate_w_m", "plate_d_m", "basis", "storeys_from", "gfa_from", "rule_ids", "note"})
        self.assertEqual(E["basis"], "schedule")
        self.assertEqual(E["storeys"], 3)
        self.assertAlmostEqual(E["height_m"], 9.9)
        self.assertAlmostEqual(E["plate_m2"], 69.6 * 27.5, places=0)
        self.assertEqual(E["gfa_m2"], round(1.2 * SITE["site_area_m2"], 0))
        self.assertIn("FSR governs", E["gfa_from"])
        self.assertIn("not a permission", E["note"])

    def test_cd1_envelope_is_the_wood_frame_standard(self):
        S = suggest.suggest(EXPO, PROGRAMS, AS_OF, "funder-ready")
        self.assertEqual(S["envelope"]["basis"], "wood_frame")
        self.assertEqual(S["envelope"]["storeys"], 6)
        self.assertEqual(S["option"]["gfa_m2"], S["envelope"]["gfa_m2"])

    def test_cd1_in_a_transit_oriented_area_takes_the_tier(self):
        site = copy.deepcopy(EXPO)
        site.update({"in_transit_oriented_area": True, "toa_tier": 3})
        S = suggest.suggest(site, PROGRAMS, AS_OF, "funder-ready")
        self.assertEqual(S["envelope"]["basis"], "toa")
        self.assertEqual(S["envelope"]["storeys"], 8)
        self.assertIn("bc.toa.minimum_density", S["envelope"]["rule_ids"])
        self.assertEqual(S["fields"]["storeys"]["value"], 8)
        self.assertEqual(S["fields"]["storeys"]["basis"], "envelope")

    def test_every_field_has_a_basis(self):
        for site in (SITE, EXPO):
            for key, f in suggest.suggest(site, PROGRAMS, AS_OF, "funder-ready")["fields"].items():
                self.assertIn(f["basis"], ("rule", "benchmark", "envelope", "placeholder"), key)


class Candidates(unittest.TestCase):
    def test_expo_funder_ready_is_available_and_benchmark_falls_back(self):
        S = suggest.suggest(EXPO, PROGRAMS, AS_OF, "benchmark")
        av = {c["id"]: c["available"] for c in S["candidates"]}
        self.assertTrue(av["funder-ready"])
        self.assertFalse(av["benchmark"])
        self.assertEqual(S["candidate"], "funder-ready")
        self.assertIn("Community Vision", S["candidate_note"])

    def test_no_note_when_the_asked_candidate_is_built(self):
        self.assertIsNone(suggest.suggest(SITE, PROGRAMS, AS_OF, "funder-ready")["candidate_note"])


class Mix(unittest.TestCase):
    def test_presets_and_placeholder_source(self):
        m = suggest.suggest(SITE, PROGRAMS, AS_OF, "funder-ready")["mix"]
        self.assertEqual(set(m["presets"]), {"starting", "family", "seniors_singles", "balanced"})
        self.assertEqual(m["source"], "placeholder")
        self.assertEqual(m["shares"], m["presets"]["starting"]["shares"])
        self.assertEqual(m["allowance"], 1.10)
        self.assertEqual(m["unit_areas_m2"]["two_bed"], 67)
        for p in m["presets"].values():
            self.assertAlmostEqual(sum(p["shares"].values()), 1.0, places=6)
            self.assertTrue(p["note"])

    def test_your_shares_change_the_counts_and_the_note(self):
        base = suggest.suggest(SITE, PROGRAMS, AS_OF, "funder-ready")
        fam = suggest.suggest(SITE, PROGRAMS, AS_OF, "funder-ready", mix_shares=suggest.MIX_PRESETS["family"]["shares"])
        self.assertNotEqual(base["option"]["units"], fam["option"]["units"])
        self.assertEqual(fam["mix"]["source"], "yours")
        self.assertIn("your shares (10 / 25 / 45 / 20%)", fam["fields"]["units.studio"]["note"])
        self.assertEqual(fam["fields"]["units.studio"]["basis"], "rule")

    def test_family_minimums_still_hold_after_your_shares(self):
        S = suggest.suggest(SITE, PROGRAMS, AS_OF, "funder-ready", mix_shares=suggest.MIX_PRESETS["seniors_singles"]["shares"])
        u = S["option"]["units"]
        self.assertGreaterEqual((u["two_bed"] + u["three_bed_plus"]) / sum(u.values()), 0.35)
        self.assertIn("moved", S["fields"]["units.two_bed"]["note"])

    def test_a_bad_mix_raises(self):
        for bad in ({"studio": 0.5, "one_bed": 0.2}, {"studio": 1.2, "one_bed": -0.2}, {"loft": 1.0}, "half", {"studio": "x", "one_bed": 1}):
            with self.assertRaises(ValueError):
                suggest.suggest(SITE, PROGRAMS, AS_OF, "funder-ready", mix_shares=bad)


class YardsLeaveNoEnvelope(unittest.TestCase):
    """609 Heatley Ave (RT-3, 37.2 x 15.2 m, a corner lot on Heatley Ave and Keefer St), as Kai decided on 17 Nov 2026:
    RT-3's 20.0 m rear yard (s.3.1.2.7) on a lot 15.2 m deep leaves no envelope with Heatley as the front. The suggestion
    says so and offers Keefer St as the front without switching it; the lane behind takes the distance to its centre
    line off the rear yard (s.3.1.2.17); the Director's variance (s.3.1.2.21) is an open item, never assumed; and the
    outright answer reads "not yet confirmed" instead of "yes"."""

    ON = date(2026, 11, 17)
    # the real parcel in its context frame and the City's street ways beside it, as the lookup stored them
    RING = [[38.42, 14.94], [1.45, 15.13], [1.36, -0.07], [38.33, -0.27]]
    ROADS = [{"name": "Heatley Ave", "width_m": 11.0, "points": [[47.0, -10.0], [-2.6, -10.0]]},
             {"name": "Heatley Ave", "width_m": 11.0, "points": [[97.2, -10.2], [47.0, -10.0]]},
             {"name": "Heatley Ave", "width_m": 11.0, "points": [[-2.6, -10.0], [-52.9, -9.6]]},
             {"name": "Keefer St", "width_m": 11.0, "points": [[47.0, -10.0], [46.4, -182.7]]},
             {"name": "Keefer St", "width_m": 11.0, "points": [[48.7, 131.7], [47.0, -10.0]]}]
    SITE = {"id": "609-heatley-ave", "address": "609 Heatley Ave, Vancouver, BC", "municipality": "City of Vancouver", "zoning_district": "RT-3",
            "site_area_m2": 566.7, "frontage_m": 37.2, "depth_m": 15.2, "has_water_and_sewer": True, "existing_trees_on_site": [],
            "keep_existing_buildings": False, "context": {"street": {"name": "Heatley Ave"}},
            "parcel": {"street": {"name": "Heatley Ave", "cross_street": {"name": "Keefer St"}}},
            "osm": {"frame": {"front_street": "Heatley Ave", "snapped_m": {"x": 0, "y": 0, "cross_street": {"name": "Keefer St", "side": "right"}}}}}

    def site(self, **extra):
        s = copy.deepcopy(self.SITE)
        for k, v in extra.items():
            if k == "lane_behind":
                s["context"]["lane_behind"] = v
            else:
                s[k] = v
        return s

    def test_the_suggestion_says_so_and_offers_the_other_front_without_switching(self):
        site = self.site()
        S = suggest.suggest(site, ["bch.chf.eligibility"], self.ON)
        o = S["option"]
        self.assertEqual(o["setbacks_m"]["rear"], 20.0)
        self.assertEqual(S["fields"]["setbacks_m.rear"]["rule_id"], "cov.rt3.setbacks")
        self.assertIsNone(S["fields"]["setbacks_m.front"]["rule_id"])            # RT-3 fixes no minimum front yard
        self.assertNotIn("front_face", site)                                    # offered, never switched
        self.assertIsNone(S["envelope"]["plate_m2"])
        self.assertIn("leave no envelope on a lot 37.2 m wide and 15.2 m deep", S["envelope"]["gfa_from"])
        y = next(u for u in S["unsure"] if u["key"] == "yards")
        self.assertIn("The RT-3 yards leave no envelope", y["why"])
        self.assertIn("With Keefer St as the front", y["why"])
        self.assertIn("12.2 × 13.5 m (165 m²)", y["why"])                     # 37.2 - 3.7 - 20.0 deep, 15.2 - 2 x 1.5 wide
        self.assertIn("12.2 × 16.6 m (202 m²) if a lane runs behind it (s.3.1.2.17", y["why"])
        self.assertIn("s.3.1.2.21", y["why"])
        self.assertIn("not assumed", y["why"])
        self.assertIn("choose the front of the corner lot at 01", y["who"])

    def test_the_outright_answer_is_not_yet_confirmed_and_the_open_item_names_the_ways_out(self):
        site = self.site()
        o = suggest.suggest(site, ["bch.chf.eligibility"], self.ON)["option"]
        L = evaluate(site, o, self.ON)
        r = next(x for x in L["results"] if x["rule_id"] == "cov.rt3.setbacks")
        self.assertEqual(r["status"], "uncertain")
        self.assertTrue(r["values"]["no_envelope"])
        self.assertEqual(r["values"]["other_front"]["street"], "Keefer St")
        self.assertEqual(r["values"]["other_front"]["envelope_m"], {"width": 12.2, "depth": 13.5})
        self.assertEqual(r["values"]["variance"]["clause"], "s.3.1.2.21")
        self.assertAlmostEqual(r["values"]["variance"]["rear_yard_for_plate_m"], 1.4, places=2)   # 15.2 - 1.8 - a 12 m plate
        out = L["summary"]["answers"]["allowed"]["outright"]
        self.assertEqual(out["verdict"], "not yet confirmed")                   # was "yes" at FSR 0.60 with no plate
        self.assertEqual(out["uncertain"], ["cov.rt3.setbacks"])
        self.assertNotIn("why", out)                                            # assessed, not "not assessed"
        item = next(u for u in L["summary"]["answers"]["unsure"] if u["rule_id"] == "cov.rt3.setbacks")
        self.assertIn("Keefer St", item["action"])
        from ffm import memo
        self.assertIn("**Outright, under RT-3: not yet confirmed.**", memo.markdown(L))

    def test_a_lane_behind_takes_the_centre_line_off_the_rear_yard(self):
        site = self.site(front_face={"street": "Keefer St"}, boundary_m=self.RING, osm={"roads": self.ROADS}, lane_behind=True)
        S = suggest.suggest(site, ["bch.chf.eligibility"], self.ON)
        o = S["option"]
        self.assertEqual(o["setbacks_m"], {"front": 3.7, "rear": 16.95, "side": 1.5})   # 20.0 less half a 6.1 m lane
        self.assertIn("s.3.1.2.17", S["fields"]["setbacks_m.rear"]["note"])
        self.assertIn("lane_to_centre_line_m", {a["key"] for a in S["assumptions"]})
        self.assertNotIn("yards", {u["key"] for u in S["unsure"]})
        L = evaluate(site, o, self.ON)
        r = next(x for x in L["results"] if x["rule_id"] == "cov.rt3.setbacks")
        self.assertEqual(r["status"], "pass")
        self.assertEqual(r["values"]["min_rear_yard_m"], 16.95)
        self.assertEqual(L["summary"]["answers"]["allowed"]["outright"]["verdict"], "yes")
        m = massing.build(site, o, L)
        self.assertAlmostEqual(m["lot"]["frontage_m"], 15.2, delta=0.1)       # the lot turned to Keefer St
        self.assertGreater(m["envelope"]["depth_m"], 15.5)                      # about 37 - 3.7 - 16.95
        self.assertGreater(m["masses"][0]["plate_area_m2"], 100)
        # the site's own distance to the centre line replaces the standard lane's
        site["context"]["lane_to_centre_line_m"] = 4.0
        self.assertEqual(suggest.suggest(site, ["bch.chf.eligibility"], self.ON)["option"]["setbacks_m"]["rear"], 16.0)
        # without a lane the full 20.0 m stands and the envelope is shallower, but still there
        site["context"]["lane_behind"] = False
        L2 = evaluate(site, suggest.suggest(site, ["bch.chf.eligibility"], self.ON)["option"], self.ON)
        self.assertEqual(L2["summary"]["answers"]["allowed"]["outright"]["verdict"], "yes")

    def test_a_lane_beside_the_heatley_front_does_not_rescue_it(self):
        # the lane reduction is for the rear; with Heatley as the front the yards still leave nothing, so it stays open
        L = evaluate(self.site(lane_behind=True), suggest.suggest(self.site(lane_behind=True), ["bch.chf.eligibility"], self.ON)["option"], self.ON)
        self.assertEqual(L["summary"]["answers"]["allowed"]["outright"]["verdict"], "not yet confirmed")

    def test_front_face_names_the_cross_street_and_the_lot_turns(self):
        # Keefer St's way past the corner lies diagonally off the Heatley frontage; it used to win that edge (16.4 m
        # "facing" against 15.2 m) and the lot stayed fronted on Heatley
        from ffm import boundary
        o = boundary.oriented_ring({"frontage_m": 37.2, "depth_m": 15.2, "boundary_m": self.RING, "osm": {"roads": self.ROADS},
                                    "front_face": {"street": "Keefer St"}})
        self.assertAlmostEqual(abs(o["orientation"]["rotate_deg"]), 90, delta=1)
        self.assertAlmostEqual(o["frontage_m"], 15.2, delta=0.1)
        self.assertAlmostEqual(o["depth_m"], 37.0, delta=0.3)


class ReadSite(unittest.TestCase):
    def test_reads_layers_a_to_c_without_an_option(self):
        R = suggest.read_site(SITE, AS_OF)
        ids = {r["rule_id"] for r in R["results"]}
        self.assertIn("cov.irp.social_housing_rezoning", ids)
        self.assertIn("cov.trees.replacement", ids)
        self.assertTrue(all(r["layer"] in "ABC" for r in R["results"]))


if __name__ == "__main__":
    unittest.main()
