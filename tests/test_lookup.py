"""The lookup's geometry, without the network: the real parcel polygon of 998 E 19th Ave as the City publishes it."""

import unittest

from ffm import lookup

# property-parcel-polygons, civic 998 E 19TH AV, fetched 3 Nov 2026
PARCEL_998 = [
    [-123.08489687064771, 49.25321534055158],
    [-123.0838586301182, 49.25320060903445],
    [-123.08384890432116, 49.25353522932474],
    [-123.08488645058618, 49.25354970057842],
    [-123.08489687064771, 49.25321534055158],
]


class ParcelMetrics(unittest.TestCase):
    def test_area_and_sides_match_the_referral_report(self):
        m = lookup.parcel_metrics(PARCEL_998)
        # the report: 2,810.7 m², 75.6 × 37.2 m
        self.assertAlmostEqual(m["area_m2"], 2810.7, delta=15)
        self.assertAlmostEqual(m["frontage_m"], 75.6, delta=0.6)
        self.assertAlmostEqual(m["depth_m"], 37.2, delta=0.4)
        self.assertTrue(m["rectangular"])
        self.assertEqual(m["vertices"], 4)

    def test_street_bearing_picks_the_frontage(self):
        along = lookup.parcel_metrics(PARCEL_998, street_bearing_deg=1.0)      # E 19th runs east-west
        across = lookup.parcel_metrics(PARCEL_998, street_bearing_deg=91.0)
        self.assertGreater(along["frontage_m"], along["depth_m"])
        self.assertLess(across["frontage_m"], across["depth_m"])
        self.assertEqual(along["frontage_from"], "the side parallel to the street")

    def test_an_odd_shape_gets_an_equivalent_rectangle(self):
        tri = [[-123.0, 49.0], [-123.0 + 0.0008, 49.0], [-123.0, 49.0 + 0.0004], [-123.0, 49.0]]
        m = lookup.parcel_metrics(tri)
        self.assertFalse(m["rectangular"])
        self.assertAlmostEqual(m["frontage_m"] * m["depth_m"], m["area_m2"], delta=m["area_m2"] * 0.005)   # the sides are rounded to 0.1 m

    def test_slug(self):
        self.assertEqual(lookup._slug("998 E 19th Ave"), "998-e-19th-ave")

    def test_civic_address_reads_like_a_person_wrote_it(self):
        self.assertEqual(lookup.civic_address("998", "E 19TH AV"), "998 E 19th Ave")
        self.assertEqual(lookup.civic_address(1010, "EXPO BLVD"), "1010 Expo Blvd")
        self.assertEqual(lookup.civic_address(None, "EXPO BLVD"), "")

    def test_the_street_decides_the_frontage(self):
        # 609 Heatley Ave: a 15.2 × 37.2 m parcel, its long side along Heatley Ave, which runs north-south
        parcel = [[-123.08996199873619, 49.2792120018887], [-123.089976239477, 49.27887771187751],
                  [-123.08976691960697, 49.27887376388247], [-123.08975269125037, 49.27920808084372], [-123.08996199873619, 49.2792120018887]]
        c = lookup.parcel_metrics(parcel)["center"]
        heatley = {"type": "way", "id": 1, "tags": {"highway": "residential", "name": "Heatley Avenue"},
                   "geometry": [{"lat": c["lat"] - 0.001, "lon": c["lon"] - 0.00028}, {"lat": c["lat"] + 0.001, "lon": c["lon"] - 0.00028}]}
        georgia = {"type": "way", "id": 2, "tags": {"highway": "residential", "name": "East Georgia Street"},
                   "geometry": [{"lat": c["lat"] - 0.00025, "lon": c["lon"] - 0.001}, {"lat": c["lat"] - 0.00025, "lon": c["lon"] + 0.001}]}
        s = lookup.street_bearing([heatley, georgia], (c["lat"], c["lon"]), "Heatley Ave")
        self.assertTrue(s["matched_by_name"])
        self.assertAlmostEqual(s["bearing_deg"], 90, delta=3)
        along = lookup.parcel_metrics(parcel, s["bearing_deg"])
        self.assertGreater(along["frontage_m"], along["depth_m"])          # 37.2 m on Heatley
        g = lookup.street_bearing([heatley, georgia], (c["lat"], c["lon"]), "E Georgia St")
        self.assertAlmostEqual(g["bearing_deg"], 0, delta=3)
        self.assertLess(lookup.parcel_metrics(parcel, g["bearing_deg"])["frontage_m"], 16)   # 15.2 m on Georgia
        self.assertIsNone(lookup.street_bearing([], (c["lat"], c["lon"]), "Heatley Ave"))

    def test_assemble_with_context_places_the_osm_block(self):
        parcels = [{"civic_number": "998", "streetname": "E 19TH AV", "geom": {"geometry": {"type": "Polygon", "coordinates": [PARCEL_998]}}}]
        c = lookup.parcel_metrics(PARCEL_998)["center"]
        road = {"type": "way", "id": 7, "tags": {"highway": "residential", "name": "East 19th Avenue"},
                "geometry": [{"lat": c["lat"] - 0.00027, "lon": c["lon"] - 0.002}, {"lat": c["lat"] - 0.00027, "lon": c["lon"] + 0.002}]}
        res = lookup.assemble("998 E 19th Ave", c["lat"], c["lon"], "998 East 19th Avenue, Vancouver", [{"zoning_district": "RM-1"}], parcels, [road], 120, "q")
        s = res["site"]
        self.assertIn("osm", s)
        self.assertEqual(s["osm"]["frame"]["front_street"], "East 19th Avenue")
        self.assertTrue(s["osm"]["frame"]["front_street_matched_by_name"])
        self.assertEqual(s["context"]["street"]["name"], "East 19th Avenue")
        self.assertAlmostEqual(s["frontage_m"], 75.6, delta=0.6)
        self.assertTrue(res["found"]["context"])

    def test_assemble_without_the_network(self):
        zoning = [{"zoning_district": "RM-1", "zoning_category": "RM", "cd_1_number": None}]
        parcels = [{"civic_number": "998", "streetname": "E 19TH AV", "site_id": "007998546", "geom": {"geometry": {"type": "Polygon", "coordinates": [PARCEL_998]}}}]
        res = lookup.assemble("998 E 19th Ave, Vancouver, BC", 49.253378, -123.084127, "Vancouver First Church of the Nazarene, 998, East 19th Avenue, Vancouver", zoning, parcels)
        s = res["site"]
        self.assertEqual(s["id"], "998-e-19th-ave")
        self.assertEqual(s["address"], "998 E 19th Ave, Vancouver, BC")
        self.assertEqual(s["zoning_district"], "RM-1")
        self.assertAlmostEqual(s["site_area_m2"], 2810.7, delta=15)
        self.assertTrue(res["found"]["parcel"])
        self.assertIsNone(s["in_transit_oriented_area"])


if __name__ == "__main__":
    unittest.main()
