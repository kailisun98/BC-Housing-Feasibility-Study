"""The block editor's placement, re-checked by the engine: the solver's own zones round-trip through the option
unchanged; a moved block is measured, not moved back; what breaks (an overlap, a zone past the plate, a unit too
small, a floor without a corridor) is named; what the program still lacks is listed; a run reproduces it."""

import json
import unittest
from datetime import date
from pathlib import Path

from ffm import layout, massing
from ffm.engine import evaluate, load_json

ROOT = Path(__file__).resolve().parent.parent
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
OPTION = load_json(ROOT / "options" / "998-e-19th-ave-what-if-funder-ready.json")
AS_OF = date(2026, 11, 3)


class Editor(unittest.TestCase):
    def setUp(self):
        self.L = evaluate(SITE, OPTION, AS_OF)
        self.m = massing.build(SITE, OPTION, self.L)
        self.solved = layout.solve(SITE, OPTION, self.L, self.m)
        self.zones = layout.zones_of(self.solved)

    def test_the_solvers_zones_round_trip_through_the_option(self):
        opt = dict(OPTION, layout={"zones": self.zones})
        lay = layout.solve(SITE, opt, self.L, self.m)
        self.assertTrue(lay["edited"])
        self.assertEqual(lay["units_placed"], self.solved["units_placed"])
        self.assertEqual([s["block"] for s in lay["shortfall"]], [s["block"] for s in self.solved["shortfall"]])
        self.assertEqual(lay["geometry"], [])
        self.assertEqual({c["id"]: c["status"] for c in lay["adjacencies"]}, {c["id"]: c["status"] for c in self.solved["adjacencies"]})
        self.assertIn("option.layout.zones (placed by hand)", lay["derived_from"])
        # the same option twice gives the same record: a run reproduces the placement
        again = layout.solve(SITE, dict(OPTION, layout={"zones": json.loads(json.dumps(self.zones))}), self.L, self.m)
        self.assertEqual(json.dumps(again, sort_keys=True), json.dumps(lay, sort_keys=True))

    def test_what_breaks_is_named_and_nothing_is_moved_back(self):
        z = json.loads(json.dumps(self.zones))
        p = self.solved["plate"]
        units = [u for u in z["1"] if u["block"] in layout.UNIT_KEYS]
        a, b = units[0], units[1]
        b["x"] = a["x"] + 1.0                       # two units overlapping
        a["w"] = round(a["w"] * 0.5, 2)             # one unit halved
        z["2"][2]["x"] = p["x"] + p["width_m"] - 1  # a block pushed past the plate
        z["3"] = [u for u in z["3"] if u["block"] != "corridor"]   # a floor without its corridor
        lay = layout.place_zones(SITE, OPTION, self.L, self.m, z)
        kinds = [g["kind"] for g in lay["geometry"]]
        for k in ("overlap", "undersized", "outside", "no_corridor"):
            self.assertIn(k, kinds, kinds)
        moved = next(u for u in lay["floors"][1]["zones"] if u["x"] == b["x"] and u["block"] == b["block"])
        self.assertEqual(moved["x"], b["x"])        # measured where it was put
        notes = " ".join(g["note"] for g in lay["geometry"])
        self.assertIn("level 2", notes)
        self.assertIn("overlap", notes)

    def test_a_removed_unit_shows_as_shortfall_and_an_extra_one_as_a_warning(self):
        z = json.loads(json.dumps(self.zones))
        three = [u for u in z["1"] if u["block"] == "three_bed_plus"]
        z["1"].remove(three[0])
        lay = layout.place_zones(SITE, OPTION, self.L, self.m, z)
        sf = next((s for s in lay["shortfall"] if s["block"] == "three_bed_plus"), None)
        self.assertEqual(sf["units"], 1)
        z["4"].append(dict(three[0], x=z["4"][-1]["x"] + z["4"][-1]["w"] + 30))   # far off, past the plate: counted, and said to be outside
        lay2 = layout.place_zones(SITE, OPTION, self.L, self.m, z)
        self.assertNotIn("three_bed_plus", [s["block"] for s in lay2["shortfall"]])
        self.assertTrue(any(g["kind"] == "outside" for g in lay2["geometry"]))

    def test_the_memo_section_says_it_was_placed_by_hand(self):
        lay = layout.solve(SITE, dict(OPTION, layout={"zones": self.zones}), self.L, self.m)
        md = "\n".join(layout.markdown(lay))
        self.assertIn("Placed by hand in the block editor", md)
        sheets = layout.sheets(lay, SITE, self.m, self.L)
        self.assertEqual(set(sheets), set(layout.SHEETS))


if __name__ == "__main__":
    unittest.main()
