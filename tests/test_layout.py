"""The architect's first layout: blocks from the option with their sources, a stacking that places every unit on
the real case without overlaps, adjacency rules read back honestly, the five sheets as well-formed SVG, the same
inputs the same layout, and a shallow corner lot drawn single-loaded rather than squeezed."""

import json
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from ffm import layout, massing
from ffm.engine import evaluate, load_json

ROOT = Path(__file__).resolve().parent.parent
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
OPTION = load_json(ROOT / "options" / "998-e-19th-ave-what-if-funder-ready.json")
AS_OF = date(2026, 11, 3)


def overlaps(a, b):
    return not (a["x"] + a["w"] <= b["x"] + 0.01 or b["x"] + b["w"] <= a["x"] + 0.01 or a["y"] + a["d"] <= b["y"] + 0.01 or b["y"] + b["d"] <= a["y"] + 0.01)


class Blocks(unittest.TestCase):
    def test_every_block_names_its_source(self):
        L = evaluate(SITE, OPTION, AS_OF)
        P = layout.blocks(OPTION, L)
        keys = {b["key"] for b in P["blocks"]}
        self.assertTrue({"studio", "one_bed", "two_bed", "three_bed_plus", "non_residential", "amenity", "services"} <= keys)
        units = {b["key"]: b for b in P["blocks"] if b["key"] in layout.UNIT_KEYS}
        self.assertEqual(units["two_bed"]["source"], "bch.design_guidelines.unit_areas")
        self.assertAlmostEqual(units["two_bed"]["net_m2_each"], round(67 * 1.10, 1))
        self.assertEqual(units["studio"]["count"], 24)
        self.assertEqual(P["units_total"], 88)
        self.assertEqual(P["parking"]["spaces"], 40)
        self.assertTrue(any(a["key"] == "partition_allowance" for a in P["assumptions"]))


class Stacking(unittest.TestCase):
    def setUp(self):
        self.L = evaluate(SITE, OPTION, AS_OF)
        self.m = massing.build(SITE, OPTION, self.L)
        self.lay = layout.solve(SITE, OPTION, self.L, self.m)

    def test_floors_match_the_massing_and_units_land_without_overlap(self):
        self.assertEqual(len(self.lay["floors"]), 5)
        for fl in self.lay["floors"]:
            zs = [z for z in fl["zones"] if z["block"] not in ("core", "corridor")]
            for i, a in enumerate(zs):
                for b in zs[i + 1:]:
                    self.assertFalse(overlaps(a, b), f"{a['label']} overlaps {b['label']} on {fl['name']}")
            p = self.lay["plate"]
            for z in fl["zones"]:
                self.assertGreaterEqual(z["x"], p["x"] - 0.02)
                self.assertLessEqual(z["x"] + z["w"], p["x"] + p["width_m"] + 0.02)
        self.assertEqual(self.lay["units_placed"] + sum(s.get("units", 0) for s in self.lay["shortfall"]), 88)
        self.assertGreater(self.lay["units_placed"], 55)   # a 1,400 m² plate over five floors holds most of the mix; the rest is said, not squeezed
        self.assertTrue(self.lay["shortfall"])
        self.assertIn("did not fit", next(c for c in self.lay["adjacencies"] if c["id"] == "units_both_sides")["note"])

    def test_the_rules_are_read_back_and_the_ground_floor_holds_the_other_uses(self):
        by = {c["id"]: c for c in self.lay["adjacencies"]}
        self.assertEqual(by["non_residential_street"]["status"], "pass", by["non_residential_street"]["note"])
        self.assertIn(by["services_lane"]["status"], ("pass", "conditional"))
        self.assertEqual(by["core_centre"]["status"], "pass")
        self.assertIn(by["family_low"]["status"], ("pass", "conditional"))
        ground = self.lay["floors"][0]
        nonres = [z for z in ground["zones"] if z["block"] == "non_residential"]
        self.assertTrue(nonres and any(z["side"] == "front" for z in nonres))   # its front on the street; a hall may run through to the lane
        self.assertTrue(any(z.get("accessible") for fl in self.lay["floors"] for z in fl["zones"]))
        fam = [fl["level"] for fl in self.lay["floors"] for z in fl["zones"] if z.get("unit") == "three_bed_plus"]
        studios = [fl["level"] for fl in self.lay["floors"] for z in fl["zones"] if z.get("unit") == "studio"]
        self.assertLessEqual(min(fam), min(studios))

    def test_deterministic(self):
        again = layout.solve(SITE, OPTION, evaluate(SITE, OPTION, AS_OF), massing.build(SITE, OPTION, self.L))
        self.assertEqual(json.dumps(again, sort_keys=True), json.dumps(self.lay, sort_keys=True))

    def test_the_option_can_override_a_rule(self):
        opt = dict(OPTION, layout={"adjacencies": [{"id": "family_low", "block": "three_bed_plus", "rule": "wherever they fit"}, {"id": "roof_garden", "block": "amenity", "rule": "a roof garden above the top floor"}]})
        lay = layout.solve(SITE, opt, self.L, self.m)
        ids = [c["id"] for c in lay["adjacencies"]]
        self.assertIn("roof_garden", ids)
        self.assertEqual(next(c for c in lay["adjacencies"] if c["id"] == "family_low")["rule"], "wherever they fit")

    def test_the_sheets_are_well_formed_svg_with_the_stamp(self):
        S = layout.sheets(self.lay, SITE, self.m, self.L)
        self.assertEqual(set(S), set(layout.SHEETS))
        for name, text in S.items():
            root = ET.fromstring(text)
            self.assertTrue(root.tag.endswith("svg"), name)
            self.assertIn(self.lay["stamp"], text, name)
        self.assertIn("front 3.7 m", S["site-plan"])
        self.assertIn("outright 10.7 m", S["elevations"])
        self.assertIn("Ground floor", S["plans"])

    def test_the_memo_section_lists_the_program_and_the_rules(self):
        md = "\n".join(layout.markdown(self.lay))
        self.assertIn("## Layouts derived from the option", md)
        self.assertIn("bch.design_guidelines.unit_areas", md)
        self.assertIn("plans.svg", md)
        self.assertIn("facing the street", md)


class ShallowLot(unittest.TestCase):
    def test_a_shallow_corner_lot_is_single_loaded_and_says_so(self):
        site = {"id": "609-heatley-ave", "address": "609 Heatley Ave", "zoning_district": "RT-3", "site_area_m2": 566.7, "frontage_m": 37.2, "depth_m": 15.2,
                "has_water_and_sewer": True, "existing_trees_on_site": [], "osm": {"frame": {"snapped_m": {"cross_street": {"name": "Keefer St", "side": "right"}}}}}
        option = {"id": "o", "name": "three storeys", "tenure": "social_housing", "storeys": 3, "height_m": 10.7, "gfa_m2": 700,
                  "units": {"studio": 2, "one_bed": 3, "two_bed": 3, "three_bed_plus": 1}, "target_programs": [], "floor_to_floor_m": 3.3,
                  "setbacks_m": {"front": 1.8, "rear": 3.0, "side": 3.0}}
        L = evaluate(site, option, AS_OF)
        m = massing.build(site, option, L)
        lay = layout.solve(site, option, L, m)
        self.assertEqual(lay["plate"]["double_loaded"], True)    # 10.4 m deep: just enough for two strips
        self.assertEqual(len(lay["floors"]), 3)
        self.assertEqual(lay["units_placed"] + sum(s.get("units", 0) for s in lay["shortfall"]), 9)
        S = layout.sheets(lay, site, m, L)
        for text in S.values():
            ET.fromstring(text)


if __name__ == "__main__":
    unittest.main()
