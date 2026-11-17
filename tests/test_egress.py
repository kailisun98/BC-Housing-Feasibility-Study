"""Egress read back from the plates (rule `bcbc.exits`, BCBC 2024 Div B Part 3): the number of exits, their
separation, the travel distance from the farthest unit door and the dead-end corridor, floor by floor, on the
solver's layout and on placements drawn by hand."""

import unittest
from datetime import date
from pathlib import Path

from ffm import layout, massing
from ffm.engine import evaluate, load_json

ROOT = Path(__file__).resolve().parent.parent
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
OPTION = load_json(ROOT / "options" / "998-e-19th-ave-as-approved.json")
AS_OF = date(2026, 11, 16)


def unit(x, y, block="one_bed", w=6.0, d=9.04):
    return {"block": block, "x": x, "y": y, "w": w, "d": d}


class Egress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = evaluate(SITE, OPTION, AS_OF)
        cls.m = massing.build(SITE, OPTION, cls.L)
        cls.solved = layout.solve(SITE, OPTION, cls.L, cls.m)
        cls.p = cls.solved["plate"]
        cls.params = next(r for r in cls.L["results"] if r["rule_id"] == "bcbc.exits")["values"]

    def floor_with(self, zones, option=OPTION, level=1):
        """A hand placement: the solver's floors elsewhere, `zones` on `level`; returns the egress record and its floor."""
        z = layout.zones_of(self.solved)
        z[str(level)] = zones
        lay = layout.place_zones(SITE, option, self.L, self.m, z)
        return lay["egress"], lay["egress"]["floors"][level]

    def corridor(self, x0, x1):
        p = self.p
        return {"block": "corridor", "x": x0, "y": round(p["y"] + p["unit_depth_m"], 2), "w": round(x1 - x0, 2), "d": 1.8}

    def core(self, x, w=7.0):
        return {"block": "core", "x": x, "y": self.p["y"], "w": w, "d": self.p["depth_m"]}

    def test_the_record_has_the_shape_and_the_solver_is_read_honestly(self):
        eg = self.solved["egress"]
        self.assertEqual(eg["rule_id"], "bcbc.exits")
        self.assertTrue(eg["sprinklered"])
        self.assertTrue(eg["sprinklered_is_placeholder"])
        self.assertEqual(len(eg["floors"]), self.p["storeys"])
        for f in eg["floors"]:
            for k in ("level", "name", "exits", "exits_required", "separation_m", "separation_min_m", "farthest_travel_m", "travel_limit_m",
                      "farthest_unit", "dead_end_m", "dead_end_limit_m", "status", "notes"):
                self.assertIn(k, f)
            # a 69.6 m plate (17 Nov 2026): the centre core and an exit stair at each end of the corridor, four
            # stairs, the end ones 67.4 m apart, no dead end; before, one 7 m core left two stairs 4.8 m apart and
            # 22 m dead ends, and no floor could pass
            self.assertEqual(f["exits"], 4)
            self.assertAlmostEqual(f["separation_m"], 67.4, places=1)
            self.assertEqual(f["separation_min_m"], 9.0)
            self.assertEqual(f["dead_end_m"], 0.0)
            self.assertEqual(f["status"], "pass", f["notes"])
        self.assertEqual(eg["status"], "pass")
        md = "\n".join(layout.markdown(self.solved))
        self.assertIn("### Egress", md)
        self.assertIn("dead end 0.0 m of 6", md)

    def test_a_single_7m_core_on_a_30m_plate_has_two_stairs_too_close(self):
        x0 = self.p["x"]
        zones = [self.corridor(x0, x0 + 30), self.core(x0 + 11.5), unit(x0, self.p["y"]), unit(x0 + 22, self.p["y"])]
        _, f = self.floor_with(zones)
        self.assertEqual((f["exits"], f["exits_required"]), (2, 2))
        self.assertAlmostEqual(f["separation_m"], 4.8, places=2)
        self.assertIn(f["status"], ("conditional", "fail"))
        self.assertTrue(any("3.4.2.3" in n for n in f["notes"]), f["notes"])

    def test_a_second_core_20m_away_passes(self):
        x0, y0 = self.p["x"], self.p["y"]
        zones = [self.corridor(x0 + 7, x0 + 42), self.core(x0 + 11.5), self.core(x0 + 31.5),
                 unit(x0 + 18.5, y0), unit(x0 + 24.5, y0, "two_bed", w=7.0)]
        _, f = self.floor_with(zones)
        self.assertEqual(f["exits"], 4)
        self.assertGreaterEqual(f["separation_m"], f["separation_min_m"])
        self.assertFalse(any("3.4.2.3" in n for n in f["notes"]), f["notes"])
        self.assertLessEqual(f["dead_end_m"], 6.0)
        self.assertEqual(f["status"], "pass", f["notes"])

    def test_a_unit_50m_from_the_only_core_fails_travel_distance(self):
        x0, y0 = self.p["x"], self.p["y"]
        zones = [self.corridor(x0, x0 + 66), self.core(x0), unit(x0 + 54, y0)]
        _, f = self.floor_with(zones)
        self.assertGreater(f["farthest_travel_m"], 45)
        self.assertAlmostEqual(f["farthest_travel_m"], 50 + 0.9, places=1)   # 50 m along, half the corridor across
        self.assertEqual(f["farthest_unit"]["door"], [x0 + 57, round(y0 + 9.04, 2)])
        self.assertEqual(f["farthest_unit"]["exit"][0], x0 + 7)
        self.assertEqual(f["status"], "fail")
        self.assertTrue(any("3.4.2.5" in n for n in f["notes"]), f["notes"])
        svg = layout.svg_plans(layout.place_zones(SITE, OPTION, self.L, self.m, {**layout.zones_of(self.solved), "1": zones}))
        self.assertIn("Egress: exits", svg)
        self.assertIn('stroke-dasharray="4 2"', svg)

    def test_sprinklered_false_switches_the_travel_limit_to_30m(self):
        x0, y0 = self.p["x"], self.p["y"]
        zones = [self.corridor(x0, x0 + 50), self.core(x0), unit(x0 + 37, y0)]   # about 33 m of travel
        eg, f = self.floor_with(zones)
        self.assertEqual(f["travel_limit_m"], 45)
        self.assertFalse(any("3.4.2.5" in n for n in f["notes"]))
        eg2, f2 = self.floor_with(zones, option=dict(OPTION, sprinklered=False))
        self.assertFalse(eg2["sprinklered"])
        self.assertFalse(eg2["sprinklered_is_placeholder"])
        self.assertEqual(f2["travel_limit_m"], 30)
        self.assertEqual(eg2["limits"]["travel_limit_m"], 30)
        self.assertTrue(any("3.4.2.5" in n for n in f2["notes"]), f2["notes"])

    def test_a_floor_under_150m2_with_one_stair_passes_the_exit_count(self):
        # egress() is pure: a 12 x 12 m plate, one 4 m core (one stair), a short corridor, two studios
        plate = dict(self.p, x=0.0, y=0.0, width_m=12.0, depth_m=12.0)
        floor = {"level": 1, "name": "Level 2", "zones": [
            {"block": "core", "x": 0.0, "y": 0.0, "w": 4.0, "d": 12.0},
            {"block": "corridor", "x": 0.0, "y": 5.1, "w": 9.5, "d": 1.8},   # 5.5 m past the core: within 6 m
            {"block": "studio", "unit": "studio", "x": 4.0, "y": 0.0, "w": 8.0, "d": 5.1},
            {"block": "studio", "unit": "studio", "x": 4.0, "y": 6.9, "w": 8.0, "d": 5.1}]}
        eg = layout.egress([floor], plate, {}, self.params, True)
        f = eg["floors"][0]
        self.assertEqual((f["exits"], f["exits_required"]), (1, 1))
        self.assertIsNone(f["separation_min_m"])
        self.assertEqual(f["status"], "pass", f["notes"])
        self.assertEqual(eg["status"], "pass")

    def test_a_floor_without_a_corridor_is_uncertain(self):
        x0, y0 = self.p["x"], self.p["y"]
        _, f = self.floor_with([self.core(x0 + 11.5), unit(x0, y0), unit(x0 + 22, y0)])
        self.assertEqual(f["status"], "uncertain")
        self.assertIsNone(f["farthest_travel_m"])
        self.assertTrue(any("no corridor" in n for n in f["notes"]))

    def test_a_bare_floor_passes_with_a_note(self):
        _, f = self.floor_with([], level=0)
        self.assertEqual(f["status"], "pass")
        self.assertTrue(f["notes"])

    def test_before_the_rule_is_in_force_there_is_no_egress(self):
        L = evaluate(SITE, OPTION, date(2024, 1, 1))
        lay = layout.solve(SITE, OPTION, L, massing.build(SITE, OPTION, L))
        self.assertIsNone(lay["egress"])
        self.assertNotIn("Egress:", layout.svg_plans(lay))


if __name__ == "__main__":
    unittest.main()
