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
