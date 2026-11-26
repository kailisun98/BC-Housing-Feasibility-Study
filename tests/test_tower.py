"""A tower, and a suggestion its own plans can hold (17 Nov 2026, found on 3475 E Hastings St: 19 storeys of 688 m² were
drawn as a 51.5 × 13.4 m slab, 114 of 170 homes fit and every floor ran 22 m dead ends). Above six storeys the plate
keeps a tower's depth; a long corridor has a stair at each end; funder-ready derives only the homes the plans place;
a transit-oriented area's tier raises funder-ready to the height and density the City may not refuse."""

import unittest
from datetime import date

from ffm import layout, massing, suggest
from ffm.engine import evaluate

ON = date(2026, 11, 17)
PROGRAMS = ["bch.chf.eligibility", "bc.bcbuilds.eligibility"]
# a C-2 lot the size of 3475 E Hastings St, as a plain rectangle (the lookup's parcel is not committed)
SITE = {"id": "c2-tower-test", "address": "a C-2 lot by a bus exchange", "zoning_district": "C-2", "site_area_m2": 2174.9,
        "frontage_m": 58.5, "depth_m": 37.2, "in_transit_oriented_area": True, "toa_tier": 4, "owner_type": "municipality",
        "has_water_and_sewer": True, "context": {"street": {"name": "E Hastings St"}}}


def run(site, option):
    L = evaluate(site, option, ON)
    m = massing.build(site, option, L)
    return m, layout.solve(site, option, L, m)


class TowerPlate(unittest.TestCase):
    def test_a_tower_keeps_a_towers_depth_and_a_mid_rise_its_own(self):
        self.assertEqual(massing.plate_dims(688, 51.5, 29.0, 19), (688 / 21.0, 21.0))
        w, d = massing.plate_dims(688, 51.5, 29.0, 6)
        self.assertAlmostEqual(d, 688 / 51.5, places=6)   # a mid-rise still spreads across the box
        self.assertEqual(massing.plate_dims(688, 51.5, 15.0, 19)[1], 15.0)   # never deeper than the box


class FitAndExits(unittest.TestCase):
    def test_the_citys_figures_derive_only_homes_the_plans_place_and_every_floor_exits(self):
        S = suggest.suggest(SITE, PROGRAMS, ON, "funder-ready", fixed={"storeys": 19, "height_m": 61.6, "gfa_m2": 13071})
        o = S["option"]
        homes = sum(o["units"].values())
        m, lay = run(SITE, o)
        self.assertEqual(lay["units_placed"], homes)
        self.assertEqual(lay["shortfall"], [])
        self.assertEqual(sum(o["rent_tiers_units"].values()), homes)
        self.assertEqual(m["masses"][0]["plate_depth_m"], 21.0)
        self.assertEqual(lay["egress"]["status"], "pass", lay["egress"]["summary"])
        self.assertIn("the plans place", S["fields"]["units.one_bed"]["note"])

    def test_a_long_corridor_has_a_stair_at_each_end(self):
        o = suggest.suggest(SITE, PROGRAMS, ON, "funder-ready", fixed={"storeys": 19, "height_m": 61.6, "gfa_m2": 13071})["option"]
        _, lay = run(SITE, o)
        cores = sorted((z for z in lay["floors"][1]["zones"] if z["block"] == "core"), key=lambda z: z["x"])
        p = lay["plate"]
        self.assertEqual(len(cores), 3)
        self.assertAlmostEqual(cores[0]["x"], p["x"], places=2)
        self.assertAlmostEqual(cores[-1]["x"] + cores[-1]["w"], p["x"] + p["width_m"], places=2)
        # the core stands on the lane side: the street side's homes run past it
        self.assertGreater(cores[1]["y"], p["y"])


class SlimTower(unittest.TestCase):
    """A slim tower (17 Nov 2026: 19 storeys with no floor area typed, a 400 m² plate on 3475 E Hastings St): too short a
    corridor for a stair at each end, and the 7 m core's stairs 4.8 m apart against 9 m. A compact plate is laid out as
    a point tower, the homes round a corridor ringing the core, its scissor stair's doors on the core's opposite faces;
    a narrow one keeps its corridor and runs the core along it to hold a scissor stair. Contiguous stairs are not for a
    5 or 6 storey wood-frame building, so neither below seven storeys."""

    @classmethod
    def setUpClass(cls):
        cls.o = suggest.suggest(SITE, PROGRAMS, ON, "funder-ready", fixed={"storeys": 19, "height_m": 61.6})["option"]
        cls.L = evaluate(SITE, cls.o, ON)
        cls.m = massing.build(SITE, cls.o, cls.L)
        cls.lay = layout.solve(SITE, cls.o, cls.L, cls.m)
        # the point tower's own case (26 Nov 2026): its core now runs a shaft longer to hold the two elevators a 19-storey
        # tower wants (`lift_room`), which costs it the 21.8 × 21 m plate above (48 homes against the corridor's 55); on a
        # 25 × 21 m plate it still places more than the corridor would
        base = suggest.suggest(SITE, PROGRAMS, ON, "funder-ready", fixed={"storeys": 19, "height_m": 61.6, "gfa_m2": round(25 * 21.0 * 19)})["option"]
        cls.co = dict(base, units={k: v + (10 if k == "studio" else 0) for k, v in base["units"].items()})
        cls.cL = evaluate(SITE, cls.co, ON)
        cls.cm = massing.build(SITE, cls.co, cls.cL)
        cls.clay = layout.solve(SITE, cls.co, cls.cL, cls.cm)

    def test_the_slim_plate_holds_its_elevators_in_a_scissor_core(self):
        core = next(z for z in self.lay["floors"][1]["zones"] if z["block"] == "core")
        self.assertEqual(core.get("stairs"), "scissor")
        self.assertGreaterEqual(layout.lift_room(core), 2)
        self.assertEqual(next(i for i in self.lay["operability"]["items"] if i["key"] == "lifts")["status"], "pass")

    def test_a_compact_tower_is_a_point_tower_its_homes_round_the_core(self):
        p, eg = self.clay["plate"], self.clay["egress"]
        self.assertEqual(p["arrangement"], "point")
        self.assertGreaterEqual(min(p["unit_depth_m"], p["side_depth_m"]), layout.LAYOUT_ASSUMPTIONS["min_home_depth_m"][0])
        for fl in self.clay["floors"]:
            cores = [z for z in fl["zones"] if z["block"] == "core"]
            self.assertEqual(len(cores), 1, fl["name"])
            self.assertEqual(cores[0].get("stairs"), "scissor", fl["name"])
            self.assertEqual(layout.lift_room(cores[0]), 2, fl["name"])                              # two elevators
            self.assertEqual(sum(1 for z in fl["zones"] if z["block"] == "corridor"), 4, fl["name"])   # the ring
        typical = self.clay["floors"][len(self.clay["floors"]) // 2]
        self.assertEqual({z["side"] for z in typical["zones"] if z.get("unit")}, {"front", "rear", "left", "right"})
        self.assertEqual(self.clay["units_placed"], sum(self.co["units"].values()))
        # the doors on opposite faces: smoke goes round the 9.6 × 7 m core, 16.6 m, against 9
        self.assertEqual(eg["status"], "pass", eg["summary"])
        self.assertTrue(eg["scissor_stair"])
        self.assertIn("opposite faces", eg["summary"])
        self.assertIn("smoke-tight", eg["summary"])
        c = next(z for z in typical["zones"] if z["block"] == "core")
        for f in eg["floors"]:
            self.assertAlmostEqual(f["separation_m"], c["w"] + c["d"], places=1)
            self.assertLessEqual(f["dead_end_m"], f["dead_end_limit_m"] + 1e-6, f["notes"])
        self.assertIn("A point tower", layout.svg_plans(self.clay))

    def test_it_places_more_homes_than_the_corridor_would(self):
        slab = layout._solve(SITE, self.co, self.cL, self.cm, layout.blocks(self.co, self.cL), None)
        self.assertGreater(self.clay["units_placed"], slab["units_placed"])

    def test_the_block_editor_keeps_the_point_tower(self):
        again = layout.place_zones(SITE, self.co, self.cL, self.cm, layout.zones_of(self.clay))
        self.assertEqual(again["plate"]["arrangement"], "point")
        self.assertTrue(again["egress"]["scissor_stair"])
        self.assertEqual(again["egress"]["status"], "pass", again["egress"]["summary"])

    def test_a_narrow_tower_keeps_its_corridor_and_runs_the_core_along_it(self):
        # 14.5 m wide on a 21 m depth: longer than POINT_ASPECT_MAX, and too short a corridor for end stairs
        mn = {**self.m, "masses": [{**x, "plate_width_m": 14.5} if x["name"] == "proposed" else x for x in self.m["masses"]]}
        lay = layout.solve(SITE, self.o, self.L, mn)
        self.assertNotEqual(lay["plate"]["arrangement"], "point")
        cores = [z for z in lay["floors"][1]["zones"] if z["block"] == "core"]
        self.assertEqual([z.get("stairs") for z in cores], ["scissor"])
        sw = layout.LAYOUT_ASSUMPTIONS["stair_width_m"][0]
        self.assertGreaterEqual(cores[0]["w"] - sw + 1e-6, 9.0)
        self.assertEqual(lay["egress"]["status"], "pass", lay["egress"]["summary"])
        self.assertIn("along the corridor", lay["egress"]["summary"])

    def test_six_storeys_never_take_one_but_the_core_still_ends_the_dead_ends(self):
        m6 = {**self.m, "masses": [{**x, "storeys": 6} if x["name"] == "proposed" else x for x in self.m["masses"]]}
        lay = layout.solve(SITE, self.o, self.L, m6)
        cores = [z for z in lay["floors"][1]["zones"] if z["block"] == "core"]
        self.assertFalse(any(z.get("stairs") == "scissor" for z in cores))
        self.assertFalse(lay["egress"]["scissor_stair"])
        for f in lay["egress"]["floors"]:
            self.assertLessEqual(f["dead_end_m"], f["dead_end_limit_m"] + 1e-6, f["notes"])
            self.assertNotEqual(f["status"], "fail", f["notes"])   # the deep core's front-and-rear stairs: the architect's to draw


class TransitTier(unittest.TestCase):
    def test_tier_4_raises_funder_ready_to_twelve_storeys_and_fsr_four_by_the_toa_path(self):
        S = suggest.suggest(SITE, PROGRAMS, ON, "funder-ready")
        o = S["option"]
        self.assertEqual(o["storeys"], 12)
        self.assertAlmostEqual(o["gfa_m2"] / SITE["site_area_m2"], 4.0, places=2)
        self.assertIn("Transit-Oriented Areas Rezoning Policy", o["rezoning_path"])
        self.assertEqual(S["fields"]["storeys"]["rule_id"], "bc.toa.minimum_density")
        _, lay = run(SITE, o)
        self.assertEqual(lay["units_placed"], sum(o["units"].values()))

    def test_no_tier_recorded_stays_with_the_schedule_and_asks_for_it(self):
        site = dict(SITE, toa_tier=None)
        S = suggest.suggest(site, PROGRAMS, ON, "funder-ready")
        self.assertEqual(S["option"]["storeys"], 6)
        self.assertIn("toa_tier", [u["key"] for u in S["unsure"]])

    def test_outright_is_not_raised(self):
        self.assertEqual(suggest.suggest(SITE, PROGRAMS, ON, "outright")["option"]["storeys"], 6)


if __name__ == "__main__":
    unittest.main()
