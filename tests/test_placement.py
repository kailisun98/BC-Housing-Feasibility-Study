"""Placing the proposed mass (option.massing: anchor, shift, quarter turn) and choosing the lot's front face
(site.front_face: a street, a side or an edge), on the two committed case studies."""

import json
import math
import unittest
from datetime import date
from pathlib import Path

from ffm import boundary, massing
from ffm.engine import evaluate, load_json

ROOT = Path(__file__).resolve().parent.parent
AS_OF = date(2026, 10, 23)


def _load(site_id: str, option_id: str):
    site = load_json(ROOT / "sites" / f"{site_id}.json")
    option = load_json(ROOT / "options" / f"{option_id}.json")
    return site, option, evaluate(site, option, AS_OF)


def _ext(ring):
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


class Placement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site, cls.option, cls.ledger = _load("998-e-19th-ave", "998-e-19th-ave-as-approved")

    def build(self, spec=None, site=None):
        opt = dict(self.option)
        if spec is not None:
            opt["massing"] = spec
        return massing.build(site or self.site, opt, self.ledger)

    def test_default_is_the_committed_footprint(self):
        committed = json.loads((ROOT / "outputs" / "998-e-19th-ave" / "as-approved" / "massing.json").read_text(encoding="utf-8"))
        m = self.build()
        self.assertEqual(json.loads(json.dumps(m["masses"])), committed["masses"])
        self.assertNotIn("placement", m["masses"][0])
        # the default anchor named explicitly gives the same footprint
        p = self.build({"anchor": "front-left"})["masses"][0]
        self.assertEqual(p["footprint"], committed["masses"][0]["footprint"])
        self.assertFalse(p["placement"]["clamped"])

    def test_rear_right_anchor(self):
        m = self.build({"anchor": "rear-right"})
        p, box = m["masses"][0], m["masses"][0]["placement"]["box"]
        x0, y0, x1, y1 = _ext(p["footprint"])
        self.assertAlmostEqual(x1, box["x"] + box["w"], places=2)
        self.assertAlmostEqual(y1, box["y"] + box["d"], places=2)
        self.assertEqual(p["placement"]["anchor"], "rear-right")
        self.assertIn("option.massing", p["derived_from"])

    def test_shift_past_the_box_is_clamped_with_a_warning(self):
        m = self.build({"anchor": "front-left", "dx_m": 5.0, "dy_m": 50.0})
        p = m["masses"][0]
        box = p["placement"]["box"]
        x0, y0, x1, y1 = _ext(p["footprint"])
        self.assertTrue(p["placement"]["clamped"])
        self.assertLessEqual(x1, box["x"] + box["w"] + 1e-6)
        self.assertLessEqual(y1, box["y"] + box["d"] + 1e-6)
        self.assertGreaterEqual(x0, box["x"] - 1e-6)
        self.assertTrue(any("moved" in w and "inside the setback envelope" in w for w in m["warnings"]))

    def test_rotate_swaps_the_extents_where_it_fits(self):
        small = dict(self.option, gfa_m2=1800.0, storeys=6)      # a 300 m² plate: 25 x 12 turns to 12 x 25 inside 69.6 x 27.5
        base = massing.build(self.site, small, self.ledger)["masses"][0]
        m = massing.build(self.site, dict(small, massing={"rotate": True}), self.ledger)
        p = m["masses"][0]
        self.assertAlmostEqual(p["plate_width_m"], base["plate_depth_m"], places=2)
        self.assertAlmostEqual(p["plate_depth_m"], base["plate_width_m"], places=2)
        self.assertAlmostEqual(p["plate_width_m"] * p["plate_depth_m"], base["plate_width_m"] * base["plate_depth_m"], delta=0.5)
        x0, y0, x1, y1 = _ext(p["footprint"])
        self.assertAlmostEqual(x1 - x0, p["plate_width_m"], places=1)    # plate_width_m stays the x extent
        self.assertFalse(any("turned plate" in w for w in m["warnings"]))

    def test_rotate_that_does_not_fit_keeps_the_area(self):
        m = self.build({"rotate": True})
        p = m["masses"][0]
        self.assertAlmostEqual(p["plate_width_m"] * p["plate_depth_m"], p["plate_area_m2"], delta=1.0)
        self.assertTrue(any("turned plate" in w for w in m["warnings"]))

    def test_unknown_anchor(self):
        with self.assertRaises(ValueError):
            self.build({"anchor": "upstairs"})


class FrontFace(unittest.TestCase):
    def test_side_right_on_the_demo_site(self):
        site, option, ledger = _load("998-e-19th-ave", "998-e-19th-ave-as-approved")
        m = massing.build(dict(site, front_face={"side": "right"}), option, ledger)
        lot, sb = m["lot"], option["setbacks_m"]
        self.assertEqual((lot["frontage_m"], lot["depth_m"]), (site["depth_m"], site["frontage_m"]))
        self.assertEqual(lot["front_face"], {"side": "right"})
        o = lot["orientation"]
        self.assertEqual(o, {"rotate_deg": -90.0, "tx": 0.0, "ty": 75.6})
        # the old right side lies on the new street line, and the front yard is measured from it
        self.assertAlmostEqual(boundary.apply_orientation(o, (site["frontage_m"], 10.0))[1], 0.0, places=6)
        x0, y0, x1, y1 = _ext(m["envelope"]["polygon"])
        self.assertAlmostEqual(y0, sb["front"], places=2)
        self.assertAlmostEqual(lot["depth_m"] - y1, sb["rear"], places=2)
        self.assertAlmostEqual(x0, sb["side"], places=2)
        self.assertIn("site.front_face", m["masses"][0]["derived_from"])

    def test_no_front_face_is_unchanged(self):
        site, option, ledger = _load("1010-expo-blvd", "1010-expo-blvd-as-permitted")
        self.assertIsNone(boundary.oriented_ring(site))
        m = massing.build(site, option, ledger)
        self.assertNotIn("orientation", m["lot"])

    def test_street_on_expo_turns_the_ring(self):
        site, option, ledger = _load("1010-expo-blvd", "1010-expo-blvd-as-permitted")
        self.assertEqual(site["osm"]["frame"]["front_street"], "Expo Boulevard")
        road = "Pacific Boulevard"
        s2 = dict(site, front_face={"street": road})
        m = massing.build(s2, option, ledger)
        o = m["lot"]["orientation"]
        self.assertNotEqual(o["rotate_deg"], 0.0)
        ring = m["lot"]["polygon"]
        self.assertGreaterEqual(min(p[1] for p in ring), -1.0)          # the lot stands on the new street line
        self.assertAlmostEqual(min(p[0] for p in ring), 0.0, places=1)
        bb = boundary.bbox(ring)
        self.assertAlmostEqual(m["lot"]["frontage_m"], bb[2] - bb[0], places=1)
        self.assertAlmostEqual(m["lot"]["depth_m"], bb[3] - bb[1], places=1)
        # a point on the road's centreline (stored in the old lot frame), alongside the lot, lands in front of it
        ways = [r for r in site["osm"]["roads"] if r.get("name") == road]
        lo, hi = bb[0], bb[2]
        pts = [boundary.apply_orientation(o, p) for w in ways for p in w["points"]]
        beside = [p for p in pts if lo <= p[0] <= hi]
        self.assertTrue(beside)
        self.assertLess(min(beside, key=lambda p: abs(p[1]))[1], 0.0)
        # the transform applied to the old ring gives the stored ring
        old = boundary.lot_ring(site)["ring"]
        for (x, y), (nx, ny) in zip(old, ring):
            ax, ay = boundary.apply_orientation(o, (x, y))
            self.assertLess(math.hypot(ax - nx, ay - ny), 0.02)

    def test_unknown_street_lists_the_adjoining_roads(self):
        site, _, _ = _load("1010-expo-blvd", "1010-expo-blvd-as-permitted")
        with self.assertRaises(ValueError) as cm:
            boundary.oriented_ring(dict(site, front_face={"street": "Main Street"}))
        msg = str(cm.exception)
        self.assertIn("Main Street", msg)
        self.assertIn("Expo Boulevard", msg)
        self.assertIn("Pacific Boulevard", msg)

    def test_edge_index(self):
        site, option, ledger = _load("998-e-19th-ave", "998-e-19th-ave-as-approved")
        m = massing.build(dict(site, front_face={"edge": 2}), option, ledger)     # edge 2 of the rectangle is the rear
        self.assertEqual(m["lot"]["orientation"], {"rotate_deg": 180.0, "tx": 75.6, "ty": 37.2})
        with self.assertRaises(ValueError):
            boundary.oriented_ring(dict(site, front_face={"edge": 9}))


if __name__ == "__main__":
    unittest.main()
