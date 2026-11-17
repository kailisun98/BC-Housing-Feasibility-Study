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

    def test_a_structural_grid_puts_every_unit_wall_on_the_module(self):
        opt = dict(OPTION, layout={"grid": {"bay_m": 6, "divide": 2}})
        lay = layout.solve(SITE, opt, self.L, self.m)
        p = lay["plate"]
        self.assertEqual(p["grid"], {"bay_m": 6.0, "divide": 2, "module_m": 3.0})
        units = [z for fl in lay["floors"] for z in fl["zones"] if z.get("unit")]
        self.assertTrue(units)
        for z in units:
            for v in (z["x"] - p["x"], z["w"]):
                self.assertAlmostEqual(v / 3.0, round(v / 3.0), places=6, msg=str(z))
        cores = [z for z in lay["floors"][0]["zones"] if z["block"] == "core"]
        for c in cores:   # the centre core and the end stairs (17 Nov 2026), every one on the module
            self.assertAlmostEqual((c["x"] - p["x"]) / 3.0, round((c["x"] - p["x"]) / 3.0), places=6)
        self.assertGreaterEqual(max(c["w"] for c in cores), 7.0)
        # the suggestion round-trips through the editor's form with nothing broken
        again = layout.solve(SITE, dict(OPTION, layout={"grid": {"bay_m": 6, "divide": 2}, "zones": layout.zones_of(lay)}), self.L, self.m)
        self.assertEqual(again["geometry"], [])
        self.assertEqual(again["units_placed"], lay["units_placed"])
        self.assertEqual(again["plate"]["grid"]["bay_m"], 6.0)
        # no grid, no cores: the layout of 3 Nov 2026, unchanged
        self.assertNotIn("grid", self.solved["plate"])
        self.assertIsNone(layout.grid_of({"layout": {"grid": {"bay_m": 40}}}))

    def test_the_architects_cores_stand_on_every_floor_and_the_program_goes_round_them(self):
        p = self.solved["plate"]
        cores = [{"x": p["x"] + 6, "y": p["y"], "w": 3, "d": p["depth_m"]}, {"x": p["x"] + 24, "y": p["y"], "w": 3, "d": p["depth_m"]}]
        lay = layout.solve(SITE, dict(OPTION, layout={"grid": {"bay_m": 6, "divide": 2}, "cores": cores}), self.L, self.m)
        for fl in lay["floors"]:
            got = sorted((z["x"], z["w"]) for z in fl["zones"] if z["block"] == "core")
            self.assertEqual(got, [(round(p["x"] + 6, 2), 3.0), (round(p["x"] + 24, 2), 3.0)])
            for z in fl["zones"]:
                if z["block"] in ("core", "corridor"):
                    continue
                for c in cores:
                    self.assertTrue(z["x"] + z["w"] <= c["x"] + 0.01 or c["x"] + c["w"] <= z["x"] + 0.01, (fl["level"], z))
        on_grid = dict(OPTION, layout={"grid": {"bay_m": 6, "divide": 2}})
        self.assertEqual(layout.place_zones(SITE, on_grid, self.L, self.m, layout.zones_of(lay))["geometry"], [])
        # on a grid a unit takes whole modules and is held to the BC Housing minimum with its partitions; without
        # one the same zones are measured against the gross area the program carries
        kinds = {g["kind"] for g in layout.place_zones(SITE, OPTION, self.L, self.m, layout.zones_of(lay))["geometry"]}
        self.assertEqual(kinds, {"undersized"})

    def test_the_fsr_room_says_how_many_more_levels_the_plate_can_take(self):
        cap = self.solved["capacity"]
        self.assertEqual(cap["fsr_limit"], 3.0)                      # the rezoning policy's benchmark on this site
        self.assertEqual(cap["rule_id"], "cov.irp.social_housing_rezoning")
        self.assertEqual((cap["storeys"], cap["plate_m2"], cap["levels_room"]), (5, 1400.0, 1))
        # a level more, as the editor adds it: a storey and a plate of floor area; the plate stays, the room is used up
        taller = dict(OPTION, storeys=6, gfa_m2=OPTION["gfa_m2"] + cap["plate_m2"])
        L2 = evaluate(SITE, taller, AS_OF)
        lay = layout.solve(SITE, taller, L2, massing.build(SITE, taller, L2))
        self.assertEqual(len(lay["floors"]), 6)
        self.assertEqual((lay["plate"]["width_m"], lay["plate"]["depth_m"]), (self.solved["plate"]["width_m"], self.solved["plate"]["depth_m"]))
        self.assertEqual(lay["capacity"]["levels_room"], 0)
        self.assertGreater(lay["units_placed"], self.solved["units_placed"])

    def test_design_space_commercial_and_a_cut_out_are_the_architects_own_blocks(self):
        z = json.loads(json.dumps(self.zones))
        p = self.solved["plate"]
        top = str(p["storeys"] - 1)
        z[top] = [u for u in z[top] if u["block"] in ("core", "corridor")]
        # the widest run of the street strip the cores leave free, now empty
        edges = [p["x"]] + [e for c in sorted((u for u in z[top] if u["block"] == "core"), key=lambda u: u["x"]) for e in (c["x"], c["x"] + c["w"])] + [p["x"] + p["width_m"]]
        x0, free = max(((edges[i], edges[i + 1] - edges[i]) for i in range(0, len(edges), 2)), key=lambda g: g[1])
        self.assertGreater(free, 18)
        y, d = p["y"], p["unit_depth_m"]
        z[top] += [{"block": "design_space", "x": x0, "y": y, "w": 6, "d": d}, {"block": "commercial", "x": x0 + 6, "y": y, "w": 6, "d": d},
                   {"block": "void", "x": x0 + 12, "y": y, "w": 6, "d": d}]
        lay = layout.place_zones(SITE, OPTION, self.L, self.m, z)
        self.assertFalse([g for g in lay["geometry"] if g["kind"] in ("bad_zone", "overlap", "outside")], lay["geometry"])
        labels = {u["block"]: u["label"] for u in lay["floors"][int(top)]["zones"]}
        self.assertEqual((labels["design_space"], labels["commercial"], labels["void"]), ("Design space", "Commercial", "Cut-out"))
        # a cut-out is not floor area: off the floor area the FSR reads, and not spare
        cut = round(6 * d, 1)
        self.assertEqual(lay["capacity"]["void_m2"], cut)
        self.assertAlmostEqual(lay["capacity"]["gfa_m2"], self.solved["capacity"]["gfa_m2"] - cut, places=1)
        self.assertEqual(lay["floors"][int(top)]["void_m2"], cut)
        self.assertEqual(lay["totals"]["void_m2"], cut)
        # no program asks for them, so nothing is short on their account
        self.assertFalse([s for s in lay["shortfall"] if s["block"] in ("design_space", "commercial", "void")])
        self.assertEqual(set(layout.sheets(lay, SITE, self.m, self.L)), set(layout.SHEETS))

    def test_the_plate_takes_the_dimensions_the_architect_set(self):
        opt = dict(OPTION, massing={"width_m": 48.0, "depth_m": 18.0})
        m = massing.build(SITE, opt, self.L)
        pm = next(x for x in m["masses"] if x["name"] == "proposed")
        self.assertEqual((pm["plate_width_m"], pm["plate_depth_m"], pm["plate_area_m2"]), (48.0, 18.0, 864.0))
        self.assertIn("option.massing.width_m", pm["derived_from"])
        lay = layout.solve(SITE, opt, self.L, m)
        self.assertEqual((lay["plate"]["width_m"], lay["plate"]["depth_m"]), (48.0, 18.0))
        self.assertEqual(lay["capacity"]["plate_m2"], 864.0)
        # a plate past what the setbacks leave is drawn at what they leave, and the massing says so
        big = massing.build(SITE, dict(OPTION, massing={"width_m": 500, "depth_m": 500}), self.L)
        bm = next(x for x in big["masses"] if x["name"] == "proposed")
        self.assertLessEqual(bm["plate_width_m"], big["envelope"]["width_m"] + 0.01)
        self.assertTrue(any("does not fit" in w for w in big["warnings"]))
        # no dimensions on the option: the plate the floor area and the storeys give, as before
        self.assertEqual(self.m["masses"][0]["plate_area_m2"], 1400.0)

    def test_the_memo_section_says_it_was_placed_by_hand(self):
        lay = layout.solve(SITE, dict(OPTION, layout={"zones": self.zones}), self.L, self.m)
        md = "\n".join(layout.markdown(lay))
        self.assertIn("Placed by hand in the block editor", md)
        sheets = layout.sheets(lay, SITE, self.m, self.L)
        self.assertEqual(set(sheets), set(layout.SHEETS))


if __name__ == "__main__":
    unittest.main()
