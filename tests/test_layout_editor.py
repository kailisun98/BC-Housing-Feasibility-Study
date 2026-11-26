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
        cores = [{"x": p["x"] + 6, "y": p["y"], "w": 3, "d": p["depth_m"]}, {"x": p["x"] + 24, "y": p["y"], "w": 6, "d": p["depth_m"]}]
        lay = layout.solve(SITE, dict(OPTION, layout={"grid": {"bay_m": 6, "divide": 2}, "cores": cores}), self.L, self.m)
        for fl in lay["floors"]:
            got = sorted((z["x"], z["w"]) for z in fl["zones"] if z["block"] == "core")
            self.assertEqual(got, [(round(p["x"] + 6, 2), 3.0), (round(p["x"] + 24, 2), 6.0)])
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

    def test_a_turned_mass_turns_its_footprint_and_keeps_its_plate(self):
        opt = dict(OPTION, massing={"width_m": 40.0, "depth_m": 16.0, "angle_deg": 20})
        m = massing.build(SITE, opt, self.L)
        pm = next(x for x in m["masses"] if x["name"] == "proposed")
        flat = next(x for x in massing.build(SITE, dict(OPTION, massing={"width_m": 40.0, "depth_m": 16.0}), self.L)["masses"] if x["name"] == "proposed")
        self.assertEqual(pm["angle_deg"], 20.0)
        self.assertEqual(pm["plate_origin"], flat["footprint"][0])
        self.assertNotEqual(pm["footprint"], flat["footprint"])
        # the same rectangle, turned about its centre: the sides keep their lengths, the centre stays
        side = lambda r, i: ((r[i][0] - r[i - 1][0]) ** 2 + (r[i][1] - r[i - 1][1]) ** 2) ** 0.5
        for i in range(4):
            self.assertAlmostEqual(side(pm["footprint"], i), side(flat["footprint"], i), delta=0.03)
        centre = lambda r: (sum(p[0] for p in r) / 4, sum(p[1] for p in r) / 4)
        self.assertAlmostEqual(centre(pm["footprint"])[0], centre(flat["footprint"])[0], delta=0.02)
        self.assertAlmostEqual(centre(pm["footprint"])[1], centre(flat["footprint"])[1], delta=0.02)
        # the plate and its blocks stay in the plate's own frame: the layout is the unturned one, and says it is turned
        lay = layout.solve(SITE, opt, self.L, m)
        ref = layout.solve(SITE, dict(opt, massing={"width_m": 40.0, "depth_m": 16.0}), self.L, massing.build(SITE, dict(opt, massing={"width_m": 40.0, "depth_m": 16.0}), self.L))
        self.assertEqual(lay["plate"]["angle_deg"], 20.0)
        self.assertEqual((lay["plate"]["x"], lay["plate"]["y"]), (ref["plate"]["x"], ref["plate"]["y"]))
        self.assertEqual(lay["floors"], ref["floors"])
        self.assertNotIn("angle_deg", ref["plate"])
        self.assertEqual(set(layout.sheets(lay, SITE, m, self.L)), set(layout.SHEETS))
        # a corner past the setback envelope is said, and nothing is moved back
        wide = massing.build(SITE, dict(OPTION, massing={"angle_deg": 45}), self.L)
        self.assertTrue(any("past the setback envelope" in w for w in wide["warnings"]), wide["warnings"])
        self.assertNotIn("angle_deg", self.m["masses"][0])

    def test_the_three_architects_fixes_of_23_november(self):
        z = json.loads(json.dumps(self.zones))
        base = layout.place_zones(SITE, OPTION, self.L, self.m, z)
        # the height is read beside the FSR: this scheme stands under the benchmark, and a level more would pass it
        cap = base["capacity"]
        self.assertEqual(cap["height_limit_m"], 21.3)
        self.assertLess(cap["height_m"], cap["height_limit_m"])
        self.assertGreater(cap["height_with_one_more"], cap["height_limit_m"])
        # commercial space is non-residential floor area: turning the non-residential blocks into it leaves nothing short
        self.assertNotIn("non_residential", [s["block"] for s in base["shortfall"]])
        for zs in z.values():
            for u in zs:
                if u["block"] == "non_residential":
                    u["block"] = "commercial"
        lay = layout.place_zones(SITE, OPTION, self.L, self.m, z)
        self.assertNotIn("non_residential", [s["block"] for s in lay["shortfall"]])
        rule = next(c for c in lay["adjacencies"] if c["id"] == "non_residential_street")
        self.assertNotEqual(rule["note"], "no non-residential space in the option")
        # a building of this height with no core large enough for an elevator is said, once
        self.assertNotIn("no_elevator", [g["kind"] for g in base["geometry"]])
        for zs in z.values():
            zs[:] = [u for u in zs if not (u["block"] == "core" and min(u["w"], u["d"]) >= layout.ELEVATOR_CORE_M)]
        bare = layout.place_zones(SITE, OPTION, self.L, self.m, z)
        lift = [g for g in bare["geometry"] if g["kind"] == "no_elevator"]
        self.assertEqual(len(lift), 1)
        self.assertIn("every floor", lift[0]["note"])

    def test_a_named_block_a_deep_home_and_a_stepped_mass(self):
        z = json.loads(json.dumps(self.zones))
        p = self.solved["plate"]
        # a name the architect gave a block is kept, and drawn on the plans
        nr = next(u for u in z["0"] if u["block"] == "non_residential")
        nr["name"] = "Community hall"
        lay = layout.place_zones(SITE, OPTION, self.L, self.m, z)
        self.assertIn("Community hall", [u.get("name") for u in lay["floors"][0]["zones"]])
        self.assertIn("Community hall", layout.sheets(lay, SITE, self.m, self.L)["plans"])
        self.assertIn("Community hall", [u.get("name") for u in layout.zones_of(lay)["0"]])
        # daylight: the solver's homes stand on a plate edge within the depth; one walled in by its neighbours and
        # the corridor has no window, and one deeper than the limit is counted
        self.assertEqual(lay["daylight"]["status"], "pass")
        unit = next(u for u in z["1"] if u["block"] in layout.UNIT_KEYS)
        unit.update(x=p["x"] + 20, y=p["y"] + 4, w=6, d=4)
        dark = layout.place_zones(SITE, OPTION, self.L, self.m, z)["daylight"]
        self.assertEqual((dark["status"], dark["no_window_wall"]), ("conditional", 1))
        unit.update(y=p["y"], d=layout.UNIT_DEPTH_MAX_M + 2)
        deep = layout.place_zones(SITE, OPTION, self.L, self.m, z)
        self.assertEqual((deep["daylight"]["deep_units"], deep["daylight"]["deepest_m"]), (1, layout.UNIT_DEPTH_MAX_M + 2))
        self.assertTrue(any(w.startswith("Daylight") for w in deep["warnings"]))
        # a courtyard beside a walled-in home is its window wall
        unit.update(x=p["x"] + 20, y=p["y"] + 4, w=6, d=4)
        z["1"].append({"block": "void", "x": p["x"] + 26, "y": p["y"] + 4, "w": 3, "d": 4})
        self.assertEqual(layout.place_zones(SITE, OPTION, self.L, self.m, z)["daylight"]["no_window_wall"], 0)
        # a stepped mass: tiers the 3D view stacks, the base footprint and the plate unchanged
        opt = dict(OPTION, massing={"steps": [{"from_level": 3, "front": 3, "left": 6}]})
        pm = massing.build(SITE, opt, self.L)["masses"][0]
        self.assertEqual([(t["from_level"], t["storeys"], t["width_m"], t["depth_m"]) for t in pm["tiers"]],
                         [(0, 3, pm["plate_width_m"], pm["plate_depth_m"]), (3, 2, round(pm["plate_width_m"] - 6, 2), round(pm["plate_depth_m"] - 3, 2))])
        self.assertEqual(pm["tiers"][1]["base_z"], round(3 * pm["floor_to_floor_m"], 2))
        self.assertAlmostEqual(pm["tiers"][0]["height_m"] + pm["tiers"][1]["height_m"], pm["height_m"], places=2)
        self.assertEqual(pm["footprint"], self.m["masses"][0]["footprint"])
        self.assertNotIn("tiers", self.m["masses"][0])
        # the elevations draw a floor the step-back's cut-outs take in from the face: nothing on a plan without them
        zs = json.loads(json.dumps(self.zones))
        top = str(p["storeys"] - 1)
        zs[top] = [u for u in zs[top] if u["block"] in ("core", "corridor")] + [{"block": "void", "step": True, "x": p["x"], "y": p["y"], "w": p["width_m"], "d": 3.0}]
        stepped = layout.place_zones(SITE, OPTION, self.L, self.m, zs)
        self.assertEqual(layout._step_insets(stepped["floors"][-1], stepped["plate"]), (3.0, 0.0, 0.0, 0.0))
        self.assertEqual(layout._step_insets(stepped["floors"][0], stepped["plate"]), (0.0, 0.0, 0.0, 0.0))
        self.assertNotEqual(layout.svg_elevations(stepped, self.m), layout.svg_elevations(layout.place_zones(SITE, OPTION, self.L, self.m, self.zones), self.m))

    def test_homes_keep_a_minimum_width_and_a_proportion(self):
        # the solver's homes on this plate already stand within both
        self.assertEqual(self.solved["proportions"]["status"], "pass")
        self.assertEqual({b["key"]: b["min_width_m"] for b in self.solved["program"] if b["key"] in layout.UNIT_KEYS}, layout.UNIT_MIN_WIDTH_M)
        # on a deep plate a home is as wide as its minimum and its depth ask, not its area over the depth alone
        deep = dict(OPTION, massing={"width_m": 69.6, "depth_m": 27.0})
        md = massing.build(SITE, deep, self.L)
        lay = layout.solve(SITE, deep, self.L, md)
        strip = lay["plate"]["unit_depth_m"]
        self.assertGreater(strip, 12)
        for fl in lay["floors"]:
            for z in fl["zones"]:
                if z.get("unit"):
                    self.assertGreaterEqual(z["w"] + 0.02, max(layout.UNIT_MIN_WIDTH_M[z["unit"]], strip / layout.UNIT_DEPTH_RATIO_MAX), z)
        self.assertEqual(lay["proportions"]["status"], "pass")
        # a home narrowed by hand is counted and said, never a failure
        z = json.loads(json.dumps(self.zones))
        unit = next(u for u in z["1"] if u["block"] == "two_bed")
        unit["w"] = 3.0
        hand = layout.place_zones(SITE, OPTION, self.L, self.m, z)
        self.assertEqual((hand["proportions"]["status"], hand["proportions"]["narrow_units"], hand["proportions"]["slender_units"]), ("conditional", 1, 1))
        self.assertTrue(any(w.startswith("Proportions") for w in hand["warnings"]))
        # and it is a problem to fix before issuing, as a home under its area is
        narrow = [g for g in hand["geometry"] if g["kind"] == "narrow"]
        self.assertEqual(len(narrow), 1)
        self.assertIn("3.0 m wide, under the 7.5 m", narrow[0]["note"])
        self.assertNotIn("narrow", [g["kind"] for g in layout.place_zones(SITE, OPTION, self.L, self.m, self.zones)["geometry"]])

    def test_small_rooms_are_rooms_and_the_solvers_own_plan_passes_its_own_check(self):
        # narrow rooms side by side across a strip's whole depth are gathered into one width, one behind another
        fl = {"zones": [
            {"block": "design_space", "x": 0.0, "y": 0.0, "w": 2.1, "d": 12.0, "side": "front"},
            {"block": "other", "label": "Front desk", "x": 2.1, "y": 0.0, "w": 1.0, "d": 12.0, "side": "front"},
            {"block": "other", "label": "Dining", "x": 3.1, "y": 0.0, "w": 6.0, "d": 12.0, "side": "front"},
            {"block": "studio", "unit": "studio", "x": 9.1, "y": 0.0, "w": 1.5, "d": 12.0, "side": "front"}]}
        before = [round(z["w"] * z["d"], 1) for z in fl["zones"]]
        layout._square_small_rooms(fl)
        lobby, desk, dining, home = fl["zones"]
        self.assertEqual((lobby["x"], lobby["w"], desk["x"], desk["w"]), (0.0, 3.1, 0.0, 3.1))     # one shared width
        self.assertEqual(lobby["y"], 0.0)                                                              # the first keeps the street
        self.assertAlmostEqual(desk["y"], lobby["d"], places=2)                                        # the next stands behind it
        self.assertAlmostEqual(lobby["d"] + desk["d"], 12.0, places=2)
        for z, a in zip(fl["zones"], before):
            self.assertAlmostEqual(z["w"] * z["d"], a, delta=0.1)                                      # every room keeps its area
        self.assertEqual((dining["w"], dining["d"], home["w"]), (6.0, 12.0, 1.5))                      # a wide room and a home are left alone
        # the solver's own floors, read back as a hand placement, break nothing (zones rounded to the centimetre)
        for site_f, opt_f, on in (("375-glen-drive", "375-glen-drive-as-proposed", date(2026, 11, 17)), ("998-e-19th-ave", "998-e-19th-ave-what-if-funder-ready", AS_OF)):
            s, o = load_json(ROOT / "sites" / f"{site_f}.json"), load_json(ROOT / "options" / f"{opt_f}.json")
            L = evaluate(s, o, on)
            m = massing.build(s, o, L)
            own = layout.solve(s, o, L, m)
            back = layout.place_zones(s, o, L, m, layout.zones_of(own))
            self.assertEqual([g["note"] for g in back["geometry"] if g["kind"] == "overlap"], [], site_f)
            self.assertFalse([z for fl2 in own["floors"] for z in fl2["zones"] if z["block"] == "other" and z["d"] > z["w"] and z["w"] < 1.5 and z["d"] > 8], site_f)

    def test_the_memo_section_says_it_was_placed_by_hand(self):
        lay = layout.solve(SITE, dict(OPTION, layout={"zones": self.zones}), self.L, self.m)
        md = "\n".join(layout.markdown(lay))
        self.assertIn("Placed by hand in the block editor", md)
        sheets = layout.sheets(lay, SITE, self.m, self.L)
        self.assertEqual(set(sheets), set(layout.SHEETS))


if __name__ == "__main__":
    unittest.main()
