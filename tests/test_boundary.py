"""The lot as a polygon: the ring in the lot frame, the setback envelope by inset, the plate box inside it, and
the massing built on them."""

import json
import math
import unittest
from datetime import date
from pathlib import Path

from ffm import boundary, engine, massing

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 10, 27)

RECT = [[0, 0], [30, 0], [30, 40], [0, 40]]
L_SHAPE = [[0, 0], [30, 0], [30, 20], [15, 20], [15, 40], [0, 40]]
FLAG = [[8, 0], [11, 0], [11, 15], [20, 15], [20, 35], [0, 35], [0, 15], [8, 15]]
TRIANGLE = [[0, 0], [60, 0], [0, 40]]


class Inset(unittest.TestCase):
    def test_rectangle_insets_to_the_rectangle_envelope(self):
        env = boundary.inset(RECT, {"front": 2, "rear": 3, "side": 1})
        self.assertEqual(env, [[1.0, 2.0], [29.0, 2.0], [29.0, 37.0], [1.0, 37.0]])

    def test_edge_kinds_follow_the_outward_normal(self):
        self.assertEqual(boundary.edge_kind((0, 0), (30, 0)), "front")    # the street edge, outward is -y
        self.assertEqual(boundary.edge_kind((30, 40), (0, 40)), "rear")
        self.assertEqual(boundary.edge_kind((30, 0), (30, 40)), "side")

    def test_l_shape_keeps_its_inner_corner(self):
        env = boundary.inset(L_SHAPE, {"front": 2, "rear": 3, "side": 1})
        self.assertEqual(len(env), 6)
        self.assertIn([14.0, 17.0], env)
        self.assertAlmostEqual(boundary.area(env), 28 * 15 + 13 * 20, places=1)

    def test_clockwise_input_is_turned(self):
        env = boundary.inset(list(reversed(RECT)), {"front": 2, "rear": 3, "side": 1})
        self.assertAlmostEqual(boundary.area(env), 28 * 35, places=1)

    def test_acute_tip_collapses_instead_of_folding(self):
        env = boundary.inset(TRIANGLE, {"front": 2, "rear": 2, "side": 2})
        self.assertIsNotNone(env)
        self.assertTrue(boundary.is_simple([tuple(p) for p in env]))
        self.assertLess(boundary.area(env), boundary.area(TRIANGLE))
        for p in env:
            self.assertTrue(boundary.point_in(tuple(p), [tuple(q) for q in TRIANGLE]))

    def test_setbacks_that_swallow_the_lot_give_none(self):
        self.assertIsNone(boundary.inset(RECT, {"front": 25, "rear": 25, "side": 1}))


class PlateBox(unittest.TestCase):
    def test_rectangle_box_is_the_rectangle(self):
        box = boundary.largest_rect(RECT, 0.5)
        self.assertEqual((box["x"], box["y"], box["w"], box["d"]), (0.0, 0.0, 30.0, 40.0))

    def test_l_shape_box_is_one_whole_wing(self):
        box = boundary.largest_rect(L_SHAPE, 0.5)
        self.assertIn((box["w"], box["d"]), [(15.0, 40.0), (30.0, 20.0)])    # the two wings are the same size
        self.assertEqual(box["area_m2"], 600.0)

    def test_flag_lot_box_is_the_body(self):
        box = boundary.largest_rect(FLAG, 0.5)
        self.assertEqual((box["x"], box["y"], box["w"], box["d"]), (0.0, 15.0, 20.0, 20.0))

    def test_triangle_box_lies_inside(self):
        box = boundary.largest_rect(TRIANGLE, 0.5)
        ring = [tuple(p) for p in TRIANGLE]
        for x, y in ((box["x"], box["y"]), (box["x"] + box["w"], box["y"]), (box["x"], box["y"] + box["d"]), (box["x"] + box["w"], box["y"] + box["d"])):
            self.assertTrue(boundary.point_in((x - 1e-6 if x else x + 1e-6, y - 1e-6 if y else y + 1e-6), ring), (x, y))


class LotRing(unittest.TestCase):
    def test_no_parcel_no_ring(self):
        self.assertIsNone(boundary.lot_ring({"frontage_m": 30, "depth_m": 40}))

    def test_drawn_boundary_wins(self):
        r = boundary.lot_ring({"boundary_m": list(reversed(RECT)), "parcel": {"polygon_lonlat": [[0, 0], [1, 0], [1, 1]]}})
        self.assertEqual(r["source"], "drawn")
        self.assertGreater(boundary.signed_area([tuple(p) for p in r["ring"]]), 0)

    def test_parcel_in_the_context_frame_lands_on_the_lot(self):
        # a 30 x 40 m lot centred on the context centre, frontage along a street bearing 90 (east): the ring's
        # corners should come back near (0,0)-(30,40) once the frame is reconstructed
        lat0, lon0 = 49.25, -123.1
        k_lat, k_lon = 110540.0, 111320.0 * math.cos(math.radians(lat0))
        corners_en = [(-15, -20), (15, -20), (15, 20), (-15, 20)]
        ring = [[lon0 + e / k_lon, lat0 + n / k_lat] for e, n in corners_en]
        site = {"frontage_m": 30, "depth_m": 40, "parcel": {"polygon_lonlat": ring},
                "osm": {"center": {"lat": lat0, "lon": lon0}, "frame": {"x_axis_bearing_deg": 90.0, "snapped_m": {"x": 0, "y": 0}}}}
        r = boundary.lot_ring(site)
        self.assertEqual(r["frame"], "context")
        self.assertEqual(boundary.bbox(r["ring"]), [0.0, 0.0, 30.0, 40.0])

    def test_parcel_without_a_frame_is_turned_to_its_frontage(self):
        lat0, lon0 = 49.25, -123.1
        k_lat, k_lon = 110540.0, 111320.0 * math.cos(math.radians(lat0))
        corners_en = [(-20, -15), (20, -15), (20, 15), (-20, 15)]     # 40 along east, 30 north
        ring = [[lon0 + e / k_lon, lat0 + n / k_lat] for e, n in corners_en]
        r = boundary.lot_ring({"frontage_m": 40, "depth_m": 30, "parcel": {"polygon_lonlat": ring}})
        self.assertEqual(r["frame"], "bearing")
        bb = boundary.bbox(r["ring"])
        self.assertAlmostEqual(bb[2] - bb[0], 40.0, delta=0.2)
        self.assertAlmostEqual(bb[3] - bb[1], 30.0, delta=0.2)


class MassingOnAPolygon(unittest.TestCase):
    def setUp(self):
        self.site = json.loads((ROOT / "sites" / "1010-expo-blvd.json").read_text(encoding="utf-8"))
        self.option = json.loads((ROOT / "options" / "1010-expo-blvd-as-permitted.json").read_text(encoding="utf-8"))
        self.ledger = engine.evaluate(self.site, self.option, AS_OF)

    def test_expo_lot_is_its_parcel(self):
        m = massing.build(self.site, self.option, self.ledger)
        self.assertEqual(m["lot"]["source"], "parcel")
        self.assertEqual(m["lot"]["frame"], "context")
        self.assertGreater(len(m["lot"]["polygon"]), 10)
        self.assertEqual(m["lot"]["shape"]["class"], "irregular")
        self.assertIn("box", m["envelope"])
        self.assertTrue(any("polygon measures" in w for w in m["warnings"]))     # 2,712 against the recorded 3,908

    def test_masses_stand_inside_the_plate_box(self):
        m = massing.build(self.site, self.option, self.ledger)
        box = m["envelope"]["box"]
        for mass in m["masses"]:
            for x, y in mass["footprint"]:
                self.assertGreaterEqual(x, box["x"] - 0.01)
                self.assertLessEqual(x, box["x"] + box["w"] + 0.01)
                self.assertGreaterEqual(y, box["y"] - 0.01)
                self.assertLessEqual(y, box["y"] + box["d"] + 0.01)
            self.assertLessEqual(mass["plate_area_m2"], box["area_m2"] + 0.1)

    def test_drawn_boundary_replaces_the_parcel(self):
        site = dict(self.site, boundary_m=[[0, 0], [78.2, 0], [78.2, 50], [0, 50]])
        m = massing.build(site, self.option, self.ledger)
        self.assertEqual(m["lot"]["source"], "drawn")
        self.assertEqual(m["lot"]["shape"]["class"], "rectangle")
        self.assertEqual(m["lot"]["bbox"], [0.0, 0.0, 78.2, 50.0])

    def test_rectangle_site_is_unchanged(self):
        site = json.loads((ROOT / "sites" / "998-e-19th-ave.json").read_text(encoding="utf-8"))
        option = json.loads((ROOT / "options" / "998-e-19th-ave-as-approved.json").read_text(encoding="utf-8"))
        m = massing.build(site, option, engine.evaluate(site, option, AS_OF))
        self.assertNotIn("bbox", m["lot"])
        self.assertEqual(len(m["lot"]["polygon"]), 4)
        self.assertNotIn("box", m["envelope"])


if __name__ == "__main__":
    unittest.main()
