"""The parcel-shape classifier, without the network: hand-made outlines in metres for each class, and the real parcel
rings of 998 E 19th Ave and 609 Heatley Ave as the City publishes them (copied from tests/test_lookup.py)."""

import unittest

from ffm import parcel_shapes as ps
from tests.test_lookup import PARCEL_998

# 609 Heatley Ave, property-parcel-polygons, as in tests/test_lookup.py (15.2 x 37.2 m)
PARCEL_609 = [[-123.08996199873619, 49.2792120018887], [-123.089976239477, 49.27887771187751],
              [-123.08976691960697, 49.27887376388247], [-123.08975269125037, 49.27920808084372], [-123.08996199873619, 49.2792120018887]]

SQUARE = [[0, 0], [20, 0], [20, 20], [0, 20], [0, 0]]
TRAPEZOID = [[0, 0], [30, 0], [20, 20], [0, 20]]
L_SHAPE = [[0, 0], [30, 0], [30, 15], [15, 15], [15, 30], [0, 30]]
# a 4 m pole, 20 m long, along one side of a 25 x 30 m body
FLAG_SIDE = [[0, 0], [4, 0], [4, 20], [25, 20], [25, 50], [0, 50]]
# the same pole in the middle of the body's front
FLAG_MIDDLE = [[10, 0], [14, 0], [14, 20], [25, 20], [25, 50], [0, 50], [0, 20], [10, 20]]
TWO_PARTS = [[[0, 0], [10, 0], [10, 10], [0, 10]], [[30, 0], [40, 0], [40, 10], [30, 10]]]
WITH_HOLE = [[[0, 0], [30, 0], [30, 30], [0, 30]], [[10, 10], [12, 10], [12, 12], [10, 12]]]


class Classes(unittest.TestCase):
    def test_square(self):
        r = ps.classify(SQUARE, units="m")
        self.assertEqual(r["class"], "rectangle")
        self.assertAlmostEqual(r["area_m2"], 400)
        self.assertAlmostEqual(r["perimeter_m"], 80)
        self.assertEqual(r["vertices"], 4)
        self.assertAlmostEqual(r["rectangularity"], 1.0)
        self.assertAlmostEqual(r["convexity"], 1.0)
        self.assertAlmostEqual(r["aspect_ratio"], 1.0)
        self.assertEqual(sorted(round(v, 6) for v in (r["equivalent_rectangle"]["side_a_m"], r["equivalent_rectangle"]["side_b_m"])), [20, 20])
        self.assertEqual(r["confidence"], 1.0)

    def test_collinear_points_and_short_edges_are_dropped(self):
        noisy = [[0, 0], [10, 0.1], [20, 0], [20, 20], [20.2, 20.1], [0, 20]]
        r = ps.classify(noisy, units="m")
        self.assertEqual(r["vertices_raw"], 6)
        self.assertEqual(r["vertices"], 4)
        self.assertEqual(r["class"], "rectangle")

    def test_trapezoid(self):
        r = ps.classify(TRAPEZOID, units="m")
        self.assertEqual(r["class"], "trapezoid")
        self.assertLess(r["rectangularity"], 0.90)

    def test_l_shape(self):
        r = ps.classify(L_SHAPE, units="m")
        self.assertEqual(r["class"], "l_shape")
        self.assertEqual(r["reflex_corners"], 1)
        self.assertAlmostEqual(r["convexity"], 675 / 787.5, places=3)

    def test_flag_lot_pole_at_the_side(self):
        r = ps.classify(FLAG_SIDE, units="m")
        self.assertEqual(r["class"], "flag_lot")
        self.assertAlmostEqual(r["flag"]["pole_width_m"], 4, delta=0.3)
        self.assertGreater(r["flag"]["body_width_m"], 12)
        self.assertAlmostEqual(r["narrowest_cross_section_m"], 4, delta=0.3)

    def test_flag_lot_pole_in_the_middle(self):
        r = ps.classify(FLAG_MIDDLE, units="m")
        self.assertEqual(r["class"], "flag_lot")
        self.assertIn("flag lot", r["note"])

    def test_two_rings_are_two_parts(self):
        r = ps.classify(TWO_PARTS, units="m")
        self.assertEqual(r["class"], "multi_part")
        self.assertEqual(r["outer_rings"], 2)
        self.assertAlmostEqual(r["area_m2"], 200)

    def test_a_hole_is_not_a_second_part(self):
        r = ps.classify(WITH_HOLE, units="m")
        self.assertEqual(r["outer_rings"], 1)
        self.assertEqual(r["holes"], 1)
        self.assertAlmostEqual(r["area_m2"], 896)

    def test_a_triangle_is_irregular(self):
        tri = [[-123.0, 49.0], [-123.0 + 0.0008, 49.0], [-123.0, 49.0 + 0.0004], [-123.0, 49.0]]
        self.assertEqual(ps.classify(tri)["class"], "irregular")


class RealParcels(unittest.TestCase):
    def test_998_e_19th_ave(self):
        r = ps.classify(PARCEL_998)
        self.assertEqual(r["class"], "rectangle")
        self.assertAlmostEqual(r["area_m2"], 2810.7, delta=15)
        sides = sorted((r["equivalent_rectangle"]["side_a_m"], r["equivalent_rectangle"]["side_b_m"]))
        self.assertAlmostEqual(sides[1], 75.6, delta=0.6)
        self.assertAlmostEqual(sides[0], 37.2, delta=0.4)

    def test_609_heatley_ave(self):
        r = ps.classify(PARCEL_609)
        self.assertEqual(r["class"], "rectangle")
        sides = sorted((r["equivalent_rectangle"]["side_a_m"], r["equivalent_rectangle"]["side_b_m"]))
        self.assertAlmostEqual(sides[1], 37.2, delta=0.4)
        self.assertAlmostEqual(sides[0], 15.2, delta=0.3)

    def test_geojson_geometry_is_accepted(self):
        r = ps.classify({"type": "Polygon", "coordinates": [PARCEL_998]})
        self.assertEqual(r["class"], "rectangle")
        self.assertEqual(r["rings"], 1)

    def test_thumbnail(self):
        svg = ps.thumbnail_svg(PARCEL_998)
        self.assertTrue(svg.startswith("<svg") and 'width="120"' in svg and "<path" in svg)


if __name__ == "__main__":
    unittest.main()
