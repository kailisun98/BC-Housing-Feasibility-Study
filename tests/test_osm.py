"""The OpenStreetMap context conversion, without the network: a street running east-west south of the
lot centre, a building north of it, a tree; the lot frame must put the street in front (y < 0),
the building behind (y > D) and x along the street."""
import unittest

from ffm import osm

LAT, LON = 49.2500, -123.0800
SITE = {"id": "t", "address": "x", "frontage_m": 40.0, "depth_m": 30.0, "street_trees": {"street": "E 19th Ave"}}


def _node(lat, lon):
    return {"lat": lat, "lon": lon}


class OsmFrame(unittest.TestCase):
    def test_frame_puts_the_street_in_front_and_the_rest_behind(self):
        dlat = 25 / 110540.0                                   # 25 m north/south
        dlon = 60 / (111320.0 * 0.6529)                        # 60 m east/west at this latitude
        elements = [
            {"type": "way", "id": 1, "tags": {"highway": "residential", "name": "East 19th Avenue"},
             "geometry": [_node(LAT - dlat, LON - dlon), _node(LAT - dlat, LON + dlon)]},
            {"type": "way", "id": 2, "tags": {"highway": "service"},
             "geometry": [_node(LAT + 2 * dlat, LON - dlon), _node(LAT + 2 * dlat, LON + dlon)]},
            {"type": "way", "id": 3, "tags": {"building": "house", "building:levels": "2"},
             "geometry": [_node(LAT + 1.2 * dlat, LON + 0.5 * dlon), _node(LAT + 1.2 * dlat, LON + 0.7 * dlon),
                          _node(LAT + 1.4 * dlat, LON + 0.7 * dlon), _node(LAT + 1.4 * dlat, LON + 0.5 * dlon), _node(LAT + 1.2 * dlat, LON + 0.5 * dlon)]},
            {"type": "way", "id": 4, "tags": {"building": "church", "name": "On the lot"},
             "geometry": [_node(LAT - 0.1 * dlat, LON - 0.1 * dlon), _node(LAT - 0.1 * dlat, LON + 0.1 * dlon),
                          _node(LAT + 0.1 * dlat, LON + 0.1 * dlon), _node(LAT + 0.1 * dlat, LON - 0.1 * dlon), _node(LAT - 0.1 * dlat, LON - 0.1 * dlon)]},
            {"type": "node", "id": 5, "tags": {"natural": "tree"}, "lat": LAT - 0.8 * dlat, "lon": LON},
        ]
        out = osm.build(SITE, elements, (LAT, LON), 120.0)
        self.assertEqual(out["frame"]["front_street"], "East 19th Avenue")
        self.assertTrue(out["frame"]["front_street_matched_by_name"])
        front = next(r for r in out["roads"] if r["id"] == 1)
        self.assertTrue(all(p[1] < 0 for p in front["points"]), front["points"])          # the street is in front
        self.assertAlmostEqual(abs(front["points"][0][1] - front["points"][1][1]), 0, places=0)  # and runs along x
        lane = next(r for r in out["roads"] if r["id"] == 2)
        self.assertTrue(all(p[1] > 30 for p in lane["points"]))                             # the service road is behind
        self.assertEqual(len(out["buildings"]), 1)
        self.assertEqual(out["buildings"][0]["height_m"], 6.4)
        self.assertTrue(all(p[1] > 30 for p in out["buildings"][0]["polygon"]))
        self.assertEqual(out["counts"]["buildings_on_site_omitted"], 1)                    # the church on the lot is left out
        self.assertEqual(out["buildings_on_site_omitted"][0]["name"], "On the lot")
        self.assertEqual(len(out["trees"]), 1)
        self.assertLess(out["trees"][0]["y"], 0)                                           # the tree stands in the street
        self.assertAlmostEqual(out["trees"][0]["x"], 20.0, delta=0.5)                      # and in line with the lot's centre

    def test_names_normalise(self):
        self.assertEqual(osm.norm_name("E 19th Ave"), osm.norm_name("East 19th Avenue"))
        self.assertEqual(osm.norm_name("Expo Blvd"), "expo boulevard")

    def test_short_number_lists_and_flat_objects_stay_on_one_line(self):
        text = osm.dumps_site({"a": [[1.5, -2], [3, 4]], "b": {"c": [1, 2, 3]}, "t": [{"id": "T1", "dbh_cm": None, "status": "retain"}]})
        self.assertIn("[1.5, -2]", text)
        self.assertIn("[1, 2, 3]", text)
        self.assertIn('{"id": "T1", "dbh_cm": null, "status": "retain"}', text)

    def test_corner_lot_snaps_to_the_cross_street(self):
        dlat = 25 / 110540.0
        dlon = 60 / (111320.0 * 0.6529)
        # the geocoded point sits 15 m east of the lot's true centre, so Windsor's centreline would cut the lot
        elements = [
            {"type": "way", "id": 1, "tags": {"highway": "residential", "name": "East 19th Avenue"},
             "geometry": [_node(LAT - dlat, LON - dlon), _node(LAT - dlat, LON + dlon)]},
            {"type": "way", "id": 2, "tags": {"highway": "residential", "name": "Windsor Street"},
             "geometry": [_node(LAT - 2 * dlat, LON + 0.25 * dlon), _node(LAT + 2 * dlat, LON + 0.25 * dlon)]},   # 15 m east of the centre
        ]
        out = osm.build(SITE, elements, (LAT, LON), 120.0)
        windsor = next(r for r in out["roads"] if r["id"] == 2)
        xs = sorted(set(round(p[0]) for p in windsor["points"]))
        self.assertEqual(xs, [50], xs)                      # W + 10 m: half a right-of-way past the right lot line
        self.assertEqual(out["frame"]["snapped_m"]["cross_street"], {"name": "Windsor Street", "side": "right"})


if __name__ == "__main__":
    unittest.main()
