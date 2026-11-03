"""The massing on a wide, shallow corner lot (609 Heatley Ave: 37.2 m along the street, 15.2 m deep): the plate keeps
a usable depth and gives up width, the setback placeholders scale to the lot, and the block stands at the street corner."""

import unittest
from datetime import date

from ffm import massing, suggest
from ffm.engine import evaluate

AS_OF = date(2026, 11, 2)
SITE = {"id": "609-heatley-ave", "address": "609 Heatley Ave, Vancouver, BC", "zoning_district": "RT-3", "site_area_m2": 566.7,
        "frontage_m": 37.2, "depth_m": 15.2, "has_water_and_sewer": True, "existing_trees_on_site": [],
        "osm": {"frame": {"front_street": "Heatley Ave", "snapped_m": {"x": 0, "y": 0, "cross_street": {"name": "Keefer St", "side": "right"}}}}}


class ShallowCornerLot(unittest.TestCase):
    def test_setbacks_scale_to_the_lot(self):
        sb = suggest.setbacks_for(SITE)
        self.assertEqual(sb, {"front": 1.8, "rear": 3.0, "side": 3.0})
        deep = suggest.setbacks_for({"frontage_m": 75.6, "depth_m": 37.2})
        self.assertEqual(deep, {"front": 3.7, "rear": 6.0, "side": 3.0})

    def test_plate_keeps_its_depth_and_sits_at_the_corner(self):
        option = {"id": "o", "name": "three storeys", "tenure": "social_housing", "storeys": 3, "height_m": 10.7, "gfa_m2": 700,
                  "units": {"studio": 2, "one_bed": 3, "two_bed": 3, "three_bed_plus": 1}, "target_programs": [],
                  "floor_to_floor_m": 3.3, "setbacks_m": suggest.setbacks_for(SITE)}
        L = evaluate(SITE, option, AS_OF)
        m = massing.build(SITE, option, L)
        p = m["masses"][0]
        self.assertAlmostEqual(m["envelope"]["depth_m"], 10.4, places=1)
        self.assertAlmostEqual(p["plate_depth_m"], 10.4, places=1)       # the whole envelope depth, not a 5 m strip
        self.assertAlmostEqual(p["plate_width_m"] * p["plate_depth_m"], 700 / 3, delta=1.0)
        self.assertLess(p["plate_width_m"], m["envelope"]["width_m"])    # width gave way instead
        self.assertEqual(p["at_street_corner"], "right")
        xs = [pt[0] for pt in p["footprint"]]
        self.assertAlmostEqual(max(xs), 37.2 - 3.0, places=1)           # against the cross-street side
        self.assertGreater(min(xs), 3.0)

    def test_a_deep_lot_is_unchanged(self):
        from ffm.engine import load_json
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        site = load_json(root / "sites" / "998-e-19th-ave.json")
        opt = load_json(root / "options" / "998-e-19th-ave-as-approved.json")
        m = massing.build(site, opt, evaluate(site, opt, date(2026, 10, 23)))
        p = m["masses"][0]
        self.assertAlmostEqual(p["plate_width_m"], 69.6, places=1)       # the full envelope width, as before
        self.assertAlmostEqual(p["plate_area_m2"], 1383.2, places=1)


if __name__ == "__main__":
    unittest.main()
