"""The architect's first layout: blocks from the option with their sources, a stacking that places every unit on
the real case without overlaps, adjacency rules read back honestly, the five sheets as well-formed SVG, the same
inputs the same layout, and a shallow corner lot drawn single-loaded rather than squeezed."""

import json
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from ffm import layout, massing
from ffm.engine import evaluate, load_json

ROOT = Path(__file__).resolve().parent.parent
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
OPTION = load_json(ROOT / "options" / "998-e-19th-ave-what-if-funder-ready.json")
AS_OF = date(2026, 11, 3)


def overlaps(a, b):
    return not (a["x"] + a["w"] <= b["x"] + 0.01 or b["x"] + b["w"] <= a["x"] + 0.01 or a["y"] + a["d"] <= b["y"] + 0.01 or b["y"] + b["d"] <= a["y"] + 0.01)


class Blocks(unittest.TestCase):
    def test_every_block_names_its_source(self):
        L = evaluate(SITE, OPTION, AS_OF)
        P = layout.blocks(OPTION, L)
        keys = {b["key"] for b in P["blocks"]}
        self.assertTrue({"studio", "one_bed", "two_bed", "three_bed_plus", "non_residential", "amenity", "services"} <= keys)
        units = {b["key"]: b for b in P["blocks"] if b["key"] in layout.UNIT_KEYS}
        self.assertEqual(units["two_bed"]["source"], "bch.design_guidelines.unit_areas")
        self.assertAlmostEqual(units["two_bed"]["net_m2_each"], round(67 * 1.10, 1))
        self.assertEqual(units["studio"]["count"], 24)
        self.assertEqual(P["units_total"], 88)
        self.assertEqual(P["parking"]["spaces"], 40)
        self.assertTrue(any(a["key"] == "partition_allowance" for a in P["assumptions"]))


class Stacking(unittest.TestCase):
    def setUp(self):
        self.L = evaluate(SITE, OPTION, AS_OF)
        self.m = massing.build(SITE, OPTION, self.L)
        self.lay = layout.solve(SITE, OPTION, self.L, self.m)

    def test_floors_match_the_massing_and_units_land_without_overlap(self):
        self.assertEqual(len(self.lay["floors"]), 5)
        for fl in self.lay["floors"]:
            zs = [z for z in fl["zones"] if z["block"] not in ("core", "corridor")]
            for i, a in enumerate(zs):
                for b in zs[i + 1:]:
                    self.assertFalse(overlaps(a, b), f"{a['label']} overlaps {b['label']} on {fl['name']}")
            p = self.lay["plate"]
            for z in fl["zones"]:
                self.assertGreaterEqual(z["x"], p["x"] - 0.02)
                self.assertLessEqual(z["x"] + z["w"], p["x"] + p["width_m"] + 0.02)
        self.assertEqual(self.lay["units_placed"] + sum(s.get("units", 0) for s in self.lay["shortfall"]), 88)
        self.assertGreater(self.lay["units_placed"], 55)   # a 1,400 m² plate over five floors holds most of the mix; the rest is said, not squeezed
        self.assertTrue(self.lay["shortfall"])
        self.assertIn("did not fit", next(c for c in self.lay["adjacencies"] if c["id"] == "units_both_sides")["note"])

    def test_the_rules_are_read_back_and_the_ground_floor_holds_the_other_uses(self):
        by = {c["id"]: c for c in self.lay["adjacencies"]}
        self.assertEqual(by["non_residential_street"]["status"], "pass", by["non_residential_street"]["note"])
        self.assertIn(by["services_lane"]["status"], ("pass", "conditional"))
        self.assertEqual(by["core_centre"]["status"], "pass")
        self.assertIn(by["family_low"]["status"], ("pass", "conditional"))
        ground = self.lay["floors"][0]
        nonres = [z for z in ground["zones"] if z["block"] == "non_residential"]
        self.assertTrue(nonres and any(z["side"] == "front" for z in nonres))   # its front on the street; a hall may run through to the lane
        self.assertTrue(any(z.get("accessible") for fl in self.lay["floors"] for z in fl["zones"]))
        fam = [fl["level"] for fl in self.lay["floors"] for z in fl["zones"] if z.get("unit") == "three_bed_plus"]
        studios = [fl["level"] for fl in self.lay["floors"] for z in fl["zones"] if z.get("unit") == "studio"]
        self.assertLessEqual(min(fam), min(studios))

    def test_deterministic(self):
        again = layout.solve(SITE, OPTION, evaluate(SITE, OPTION, AS_OF), massing.build(SITE, OPTION, self.L))
        self.assertEqual(json.dumps(again, sort_keys=True), json.dumps(self.lay, sort_keys=True))

    def test_the_option_can_override_a_rule(self):
        opt = dict(OPTION, layout={"adjacencies": [{"id": "family_low", "block": "three_bed_plus", "rule": "wherever they fit"}, {"id": "roof_garden", "block": "amenity", "rule": "a roof garden above the top floor"}]})
        lay = layout.solve(SITE, opt, self.L, self.m)
        ids = [c["id"] for c in lay["adjacencies"]]
        self.assertIn("roof_garden", ids)
        self.assertEqual(next(c for c in lay["adjacencies"] if c["id"] == "family_low")["rule"], "wherever they fit")

    def test_the_sheets_are_well_formed_svg_with_the_rules_date(self):
        S = layout.sheets(self.lay, SITE, self.m, self.L)
        self.assertEqual(set(S), set(layout.SHEETS))
        for name, text in S.items():
            root = ET.fromstring(text)
            self.assertTrue(root.tag.endswith("svg"), name)
            # each sheet says which rules it read; the stamp's hash stays in the ledger and off the drawing, as the UI
            # dropped it (17 Nov 2026); the date reads in words, "3 Nov 2026" (24 Nov 2026)
            self.assertIn(f"Rules as of {massing.date_words(self.lay['as_of'])}", text, name)
            self.assertNotIn(f"Rules as of {self.lay['as_of']}", text, name)
            self.assertNotIn(self.lay["stamp"], text, name)
        self.assertIn("front 3.7 m", S["site-plan"])
        self.assertIn("outright 10.7 m", S["elevations"])
        self.assertIn("Ground floor", S["plans"])

    def test_the_memo_section_lists_the_program_and_the_rules(self):
        md = "\n".join(layout.markdown(self.lay))
        self.assertIn("## Layouts derived from the option", md)
        self.assertIn("bch.design_guidelines.unit_areas", md)
        self.assertIn("plans.svg", md)
        self.assertIn("facing the street", md)


def text_boxes(svg: str):
    """Every unrotated text's box at 0.55 em a character (Plex Sans), and the sheet's size."""
    import re
    root = ET.fromstring(svg)
    W, H = float(root.get("width")), float(root.get("height"))
    out = []

    def walk(el, dx, dy, rot):
        tr = el.get("transform") or ""
        m = re.search(r"translate\(([-\d.]+)[ ,]+([-\d.]+)\)", tr)
        if m:
            dx, dy = dx + float(m.group(1)), dy + float(m.group(2))
        rot = rot or "rotate" in tr
        if el.tag.endswith("text") and not rot:
            t, size = "".join(el.itertext()), float(el.get("font-size") or 12)
            x, y, w = float(el.get("x")) + dx, float(el.get("y")) + dy, len("".join(el.itertext())) * size * 0.55
            a = el.get("text-anchor") or "start"
            x0 = x - (w / 2 if a == "middle" else w if a == "end" else 0)
            out.append((x0, y - size * 0.75, x0 + w, y + size * 0.22, t))
        for c in el:
            walk(c, dx, dy, rot)
    walk(root, 0, 0, False)
    return W, H, out


class SheetsReadAsDrawings(unittest.TestCase):
    """20 Nov 2026, an architect's review at 1600 px: no north arrow or scale bar, labels printed over each other and
    ran off the sheets, stacking labels cut mid-word, no stair, door or entry on the plans, the yards undimensioned on
    a polygon lot. Every text is measured: none runs past the sheet and none prints over another."""

    def sheets_for(self, site, option, on):
        L = evaluate(site, option, on)
        m = massing.build(site, option, L)
        return layout.sheets(layout.solve(site, option, L, m), site, m, L)

    def cases(self):
        glen = load_json(ROOT / "sites" / "375-glen-drive.json")
        expo = load_json(ROOT / "sites" / "1010-expo-blvd.json")
        return {"998": self.sheets_for(SITE, OPTION, AS_OF),
                "998-approved": self.sheets_for(SITE, load_json(ROOT / "options" / "998-e-19th-ave-as-approved.json"), date(2026, 10, 23)),
                "glen": self.sheets_for(glen, load_json(ROOT / "options" / "375-glen-drive-as-proposed.json"), date(2026, 11, 17)),
                "expo": self.sheets_for(expo, load_json(ROOT / "options" / "1010-expo-blvd-as-permitted.json"), date(2026, 10, 23))}

    def test_no_text_runs_off_a_sheet_or_over_another(self):
        for case, S in self.cases().items():
            for name, svg in S.items():
                W, H, boxes = text_boxes(svg)
                for b in boxes:
                    self.assertTrue(b[0] >= -0.5 and b[2] <= W + 0.5 and b[1] >= -0.5 and b[3] <= H + 0.5, f"{case} {name}: {b[4]!r} runs off the {W:.0f} × {H:.0f} sheet")
                for i, a in enumerate(boxes):
                    for b in boxes[i + 1:]:
                        self.assertFalse(a[0] < b[2] - 1 and b[0] < a[2] - 1 and a[1] < b[3] - 1 and b[1] < a[3] - 1, f"{case} {name}: {a[4]!r} over {b[4]!r}")

    def test_scale_bars_north_arrows_streets_and_level_marks(self):
        S = self.cases()["998-approved"]
        for name in ("plans", "site-plan", "elevations", "axon"):
            self.assertIn(">0</text>", S[name], name)                       # a two-half scale bar from 0
        for name in ("plans", "site-plan"):
            self.assertIn(">N</text>", S[name], name)                       # the context frame gives the bearing
            self.assertIn("E 19TH AVE · STREET SIDE", S[name], name)
        self.assertIn(">+3.3</text>", S["elevations"])                       # floor levels marked
        self.assertIn("+3.3 m</text>", S["stacking"])
        self.assertIn(">entry</text>", S["plans"])
        self.assertIn("stroke-width=\"0.5\" fill=\"none\"", S["plans"])    # the stairs' treads
        self.assertIn("The typical floor stands for", S["plans"])

    def test_the_elevations_labels_keep_apart_and_heights_keep_their_centimetres(self):
        S = self.cases()["998-approved"]
        W, H, boxes = text_boxes(S["elevations"])
        tall = [b for b in boxes if b[4] == "22.3 m"]
        bench = [b for b in boxes if b[4].startswith("benchmark")]
        self.assertEqual(len(tall), 2)
        for a, b in zip(tall, bench):
            self.assertGreaterEqual(abs(a[1] - b[1]), 11)                    # was printed one over the other
        self.assertEqual(layout._metres(88.45), "88.45")
        self.assertEqual(layout._metres(9.149999999), "9.15")
        self.assertEqual(layout._metres(36.6), "36.6")
        self.assertIn("88.45 m", self.cases()["expo"]["elevations"])

    def test_the_stacking_never_cuts_a_name(self):
        for case, S in self.cases().items():
            for full in ("Core (stair", "Two-bedroo", "Non-resi", "Corridc"):
                self.assertNotIn(f">{full}<", S["stacking"], case)

    def test_a_polygon_lots_yards_are_dimensioned_inside_the_lot(self):
        S = self.cases()["glen"]
        self.assertIn("front ", S["site-plan"])
        self.assertIn("rear ", S["site-plan"])
        self.assertIn('marker-end="url(#tick)"', S["site-plan"])


class WalkUp(unittest.TestCase):
    """20 Nov 2026, 609 Heatley Ave fronted on Keefer St: three storeys on a 9.44 × 12 m plate. The corridor plan's 7 m
    core bay and 1.8 m corridor left no strip a home fits in; a low building on a plate one exit may serve is also laid
    out as a walk-up, one stair and no elevator, every home off its landing, and the Part 9 basis is said."""

    MINS = {"studio": 33, "one_bed": 49, "two_bed": 67, "three_bed_plus": 86}

    def solve(self, w, d, storeys, units):
        ring = [[0.0, 0.0], [w, 0.0], [w, d], [0.0, d]]
        m = {"origin": "", "warnings": [], "masses": [{"name": "proposed", "footprint": ring, "plate_width_m": w, "plate_depth_m": d, "storeys": storeys,
                                                      "floor_to_floor_m": 3.3, "plate_area_m2": w * d, "gfa_m2": w * d * storeys}]}
        ledger = {"results": [{"rule_id": "bch.design_guidelines.unit_areas", "check": "unit_area_flags", "status": "info", "values": {"min_net_area_m2": self.MINS}}],
                  "run": {"as_of": "", "stamp": {"stamp": ""}}}
        return layout.solve({}, {"units": units}, ledger, m), m, ledger

    def test_a_small_low_plate_is_a_walk_up_off_one_stair(self):
        lay, m, ledger = self.solve(9.44, 12.0, 3, {"studio": 1, "one_bed": 0, "two_bed": 2, "three_bed_plus": 0})
        self.assertEqual(lay["plate"]["arrangement"], "walkup")
        self.assertEqual(lay["units_placed"], 3)                       # before: the corridor plan placed none of them
        for fl in lay["floors"]:
            stairs = [z for z in fl["zones"] if z["block"] == "core"]
            self.assertEqual(len(stairs), 1)
            self.assertEqual((stairs[0]["w"], stairs[0]["d"], stairs[0].get("stairs")), (2.6, 5.5, "single"))
            self.assertEqual(stairs[0]["x"], lay["floors"][0]["zones"][0]["x"])    # the stair stands in the same place on every floor
            self.assertTrue(any(z["block"] == "corridor" and z["label"] == "Landing" for z in fl["zones"]))
            for z in fl["zones"]:
                if z.get("unit"):
                    self.assertEqual(z["d"], 12.0)                     # every home the plate's full depth, its door on the landing
        self.assertNotIn("amenity", {b["key"] for b in lay["program"]})   # no indoor amenity room in a building this small
        self.assertTrue(any("Part 9" in w and "placeholder" in w for w in lay["warnings"]), lay["warnings"])
        self.assertIn("walkup_one_exit", {a["key"] for a in lay["assumptions"]})
        self.assertEqual(next(c for c in lay["adjacencies"] if c["id"] == "core_centre")["status"], "pass")

    def test_the_exits_read_one_stair_against_a_small_floor(self):
        lay, m, ledger = self.solve(9.44, 12.0, 3, {"studio": 1, "one_bed": 0, "two_bed": 2, "three_bed_plus": 0})
        L = evaluate(ShallowLot.SITE, {"id": "o", "units": {"studio": 1, "two_bed": 2}, "storeys": 3, "height_m": 9.9, "gfa_m2": 340, "tenure": "social_housing"}, AS_OF)
        eg = layout.egress(lay["floors"], lay["plate"], {"blocks": []}, next(r for r in L["results"] if r["rule_id"] == "bcbc.exits")["values"], True)
        self.assertEqual(eg["status"], "pass")
        self.assertTrue(all(f["exits"] == 1 and f["exits_required"] == 1 for f in eg["floors"]))

    def test_a_floor_two_exits_must_serve_keeps_the_corridor_plan(self):
        lay, *_ = self.solve(31.2, 10.4, 3, {"studio": 2, "one_bed": 3, "two_bed": 3, "three_bed_plus": 1})   # 324 m², over 150
        self.assertNotEqual(lay["plate"]["arrangement"], "walkup")
        lay, *_ = self.solve(9.44, 12.0, 4, {"studio": 1, "one_bed": 0, "two_bed": 2, "three_bed_plus": 0})   # four storeys: Part 3
        self.assertNotEqual(lay["plate"]["arrangement"], "walkup")

    def test_the_sheets_draw_the_walk_up(self):
        lay, m, ledger = self.solve(9.44, 12.0, 3, {"studio": 1, "one_bed": 0, "two_bed": 2, "three_bed_plus": 0})
        lay["outright"] = {}
        site = {"id": "s", "site_area_m2": 566.7}
        led = {"results": ledger["results"], "summary": {"answers": {"allowed": {"outright": {"verdict": "yes"}, "by_rezoning": {"verdict": "yes"}, "rezoning_path": None}}}}
        m["lot"] = {"frontage_m": 15.2, "depth_m": 37.2, "area_m2": 566.7, "polygon": [[0, 0], [15.2, 0], [15.2, 37.2], [0, 37.2]]}
        m["envelope"] = {"setbacks_m": {"front": 3.7, "rear": 20.0, "side": 1.5}, "polygon": [[1.5, 3.7], [13.7, 3.7], [13.7, 17.2], [1.5, 17.2]], "width_m": 12.2, "depth_m": 13.5}
        m["masses"][0].update(fsr=0.6, height_m=9.9)
        S = layout.sheets(lay, site, m, led)
        for text in S.values():
            ET.fromstring(text)
        self.assertIn("walk-up", S["plans"])
        md = "\n".join(layout.markdown(lay))
        self.assertIn("a walk-up", md)


class ShallowLot(unittest.TestCase):
    SITE = {"id": "609-heatley-ave", "address": "609 Heatley Ave", "zoning_district": "RT-3", "site_area_m2": 566.7, "frontage_m": 37.2, "depth_m": 15.2,
            "has_water_and_sewer": True, "existing_trees_on_site": [], "osm": {"frame": {"snapped_m": {"cross_street": {"name": "Keefer St", "side": "right"}}}}}

    def test_a_shallow_corner_lot_is_single_loaded_and_says_so(self):
        site = self.SITE
        option = {"id": "o", "name": "three storeys", "tenure": "social_housing", "storeys": 3, "height_m": 10.7, "gfa_m2": 700,
                  "units": {"studio": 2, "one_bed": 3, "two_bed": 3, "three_bed_plus": 1}, "target_programs": [], "floor_to_floor_m": 3.3,
                  "setbacks_m": {"front": 1.8, "rear": 3.0, "side": 3.0}}
        L = evaluate(site, option, AS_OF)
        m = massing.build(site, option, L)
        lay = layout.solve(site, option, L, m)
        self.assertEqual(lay["plate"]["double_loaded"], True)    # 10.4 m deep: just enough for two strips
        self.assertEqual(len(lay["floors"]), 3)
        self.assertEqual(lay["units_placed"] + sum(s.get("units", 0) for s in lay["shortfall"]), 9)
        S = layout.sheets(lay, site, m, L)
        for text in S.values():
            ET.fromstring(text)

    def test_no_sheet_draws_a_negative_size_when_the_yards_leave_little_or_no_plate(self):
        # 609 Heatley Ave as the tool suggests it (16 Nov 2026): RT-3's 20 m rear yard on a lot 15.2 m deep gave a -6.6 m
        # envelope, and the plans, stacking, elevations and site plan drew rects of negative width or height (nine
        # console errors per memo). The plate is now zero, and every sheet draws without a negative size.
        option = {"id": "o", "name": "three storeys, four homes", "tenure": "social_housing", "storeys": 3, "height_m": 9.9, "gfa_m2": 340,
                  "units": {"studio": 1, "one_bed": 1, "two_bed": 1, "three_bed_plus": 1}, "target_programs": [], "floor_to_floor_m": 3.3}
        drawn = {"boundary_m": [[0, 0], [37.2, 0], [37.2, 15.2], [0, 15.2]]}   # the polygon path, which falls back to the rectangle
        for rear in (20.0, 12.0, 3.0):
            for extra in ({}, drawn):
                with self.subTest(rear=rear, polygon=bool(extra)):
                    site, opt = dict(self.SITE, **extra), dict(option, setbacks_m={"front": 1.8, "rear": rear, "side": 1.5})
                    L = evaluate(site, opt, AS_OF)
                    m = massing.build(site, opt, L)
                    self.assertGreaterEqual(m["envelope"]["depth_m"], 0)
                    for mass in m["masses"]:
                        self.assertGreaterEqual(mass["plate_depth_m"], 0, mass["name"])
                        self.assertGreaterEqual(mass["gfa_m2"], 0, mass["name"])
                    if rear == 20.0:
                        self.assertTrue(any("leave no envelope: a front yard of 1.8 m and a rear yard of 20 m" in w for w in m["warnings"]), m["warnings"])
                    S = layout.sheets(layout.solve(site, opt, L, m), site, m, L)
                    S["massing"] = massing.svg(m)
                    for name, text in S.items():
                        for el in ET.fromstring(text).iter():
                            for a in ("width", "height"):
                                v = el.get(a)
                                if v is not None and not v.endswith("%"):
                                    self.assertGreaterEqual(float(v), 0, f"{name}: <{el.tag.split('}')[-1]} {a}=\"{v}\">")


if __name__ == "__main__":
    unittest.main()
