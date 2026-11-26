"""The panels' last defects and flow items (26 Nov 2026): the money counts the homes the plans place (Kai: "placed homes
only"), a core holds the elevators its homes want, a mixed building's budget by part, and what is already decided.
Run: python -m unittest tests.test_panel3_flow"""

import unittest
from datetime import date
from pathlib import Path

from ffm import layout, massing, memo, proforma
from ffm.engine import evaluate, load_json

ROOT = Path(__file__).resolve().parent.parent
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
OPTION = load_json(ROOT / "options" / "998-e-19th-ave-as-approved.json")
GLEN = load_json(ROOT / "sites" / "375-glen-drive.json")
GLEN_O = load_json(ROOT / "options" / "375-glen-drive-as-proposed.json")
AS_OF = date(2026, 10, 23)


def run(site, option, on=AS_OF):
    L = evaluate(site, option, on)
    m = massing.build(site, option, L)
    lay = layout.solve(site, option, L, m)
    return L, m, lay, proforma.build(site, option, L, m, lay)


class TheMoneyCountsThePlacedHomes(unittest.TestCase):
    def test_r1_counts_the_70_its_plans_hold(self):
        L, m, lay, pf = run(SITE, OPTION)
        self.assertLess(lay["units_placed"], lay["units_total"])
        self.assertEqual(pf["inputs"]["units_total"], lay["units_placed"])
        self.assertEqual(pf["inputs"]["units_entered"], lay["units_total"])
        self.assertEqual(pf["inputs"]["homes_basis"], "placed")
        homes = next(ln for ln in pf["lines"] if ln["key"] == "homes")
        self.assertIn(f"the {lay['units_placed']} homes the first plans place, of the {lay['units_total']}", homes["note"])
        # the capital is the option's floor area: the same either way
        plain = proforma.build(SITE, OPTION, L, m)
        self.assertEqual(pf["capital"]["total"], plain["capital"]["total"])
        self.assertGreater(pf["gap"]["value"], plain["gap"]["value"])

    def test_without_plans_it_counts_the_homes_entered(self):
        L = evaluate(SITE, OPTION, AS_OF)
        pf = proforma.build(SITE, OPTION, L)
        self.assertEqual(pf["inputs"]["homes_basis"], "entered")
        self.assertEqual(pf["inputs"]["units_total"], 105)

    def test_answer_3_says_which_count_the_money_reads(self):
        L, m, lay, pf = run(SITE, OPTION)
        it = next(i for i in memo.layout_open_items(lay) if i["title"] == "Homes that do not fit the plates")
        self.assertIn(f"the money counts the {lay['units_placed']} placed", it["action"])
        js = (ROOT / "ffm" / "ui" / "memo" / "answers.js").read_text(encoding="utf-8")
        self.assertIn("the money counts the ${lay.units_placed} placed", js)


class ACoreHoldsItsElevators(unittest.TestCase):
    def test_room_by_the_core_length(self):
        self.assertEqual(layout.lift_room({"w": 7.0, "d": 7.0}), 1)
        self.assertEqual(layout.lift_room({"w": 7.0, "d": 10.83}), 2)       # a six-storey slab's core, across the corridor
        self.assertEqual(layout.lift_room({"w": 9.6, "d": 7.0}), 2)
        self.assertEqual(layout.lift_room({"w": 2.2, "d": 10.0}), 0)        # an end stair

    def test_r1_has_room_for_its_two_elevators(self):
        L, m, lay, pf = run(SITE, OPTION)
        self.assertEqual(next(i for i in lay["operability"]["items"] if i["key"] == "lifts")["status"], "pass")


class ABudgetByPart(unittest.TestCase):
    """Glen Drive: 109 homes, 25 supportive homes and 80 shelter beds, which ran on one budget."""

    PARTS = {"supportive": {"staffing_cad_year": 900000, "operating_subsidy_cad_year": 1200000, "subsidy_confirmed": True, "operating_cost_cad_year": 9000},
             "shelter": {"staffing_cad_year": 2400000, "operating_subsidy_cad_year": 2900000}}

    def test_each_part_has_its_own_row(self):
        o = dict(GLEN_O, operations=dict(GLEN_O.get("operations") or {}, parts=self.PARTS))
        L, m, lay, pf = run(GLEN, o, date(2026, 11, 17))
        page = pf["operating"]["page"]
        rows = {r["key"]: r for r in page["parts"]}
        self.assertEqual(set(rows), {"independent", "supportive", "shelter"})
        self.assertEqual(rows["shelter"]["places"], 80)
        self.assertEqual(rows["shelter"]["rent"], 0)
        self.assertEqual(rows["supportive"]["staffing"], 900000)
        self.assertEqual(rows["supportive"]["cost"], rows["supportive"]["places"] * 9000)
        self.assertEqual(page["support_staffing"], 3300000)
        self.assertEqual(page["subsidy"], 4100000)
        self.assertFalse(page["subsidy_confirmed"])                         # the shelter's agreement is not in hand
        self.assertFalse(page["staffing_missing"])
        net = sum(r["net"] for r in page["parts"])
        self.assertAlmostEqual(net, page["net_before_subsidy"] + page["subsidy"] - (page.get("nonres_income") or 0), delta=page["places"] if "places" in page else 5)
        self.assertIn("#### By part of the building", "\n".join(proforma.parts_markdown(pf)))

    def test_without_a_parts_own_staffing_the_staffing_stays_open(self):
        o = dict(GLEN_O, operations=dict(GLEN_O.get("operations") or {}, parts={"supportive": {"staffing_cad_year": 900000}}))
        L, m, lay, pf = run(GLEN, o, date(2026, 11, 17))
        self.assertTrue(pf["operating"]["page"]["staffing_missing"])
        self.assertIn("not entered for the shelter part", next(ln for ln in pf["lines"] if ln["key"] == "staffing")["note"])

    def test_a_single_kind_building_has_no_split(self):
        L, m, lay, pf = run(SITE, OPTION)
        self.assertNotIn("parts", pf["operating"]["page"])


class WhatIsAlreadyDecided(unittest.TestCase):
    def test_a_permit_issued_settles_its_items(self):
        site = load_json(ROOT / "sites" / "1010-expo-blvd.json")
        o = load_json(ROOT / "options" / "1010-expo-blvd-as-permitted.json")
        L = evaluate(site, o, AS_OF)
        a = L["summary"]["answers"]
        ids = [u["rule_id"] for u in a["unsure"]]
        self.assertNotIn("cov.trees.replacement", ids)
        self.assertNotIn("coverage.yards", ids)
        self.assertEqual([d["what"] for d in a["decided"]], ["permit"])
        self.assertIn("5 Feb 2025", a["decided"][0]["words"])
        fs = memo.front_sheet(L, None, None)
        self.assertTrue(any("development permit was issued" in d for d in fs["decided"]))

    def test_the_approved_rezoning_and_a_signed_land_agreement(self):
        o = dict(OPTION, land_tenure="lease_60_plus", land_agreement_signed_on="2024-09-30")
        a = evaluate(SITE, o, AS_OF)["summary"]["answers"]
        self.assertEqual([d["what"] for d in a["decided"]], ["rezoning", "land"])
        self.assertIn("a lease of 60 years or more", a["decided"][1]["words"])
        self.assertIn("30 Sep 2024", a["decided"][1]["words"])

    def test_the_page_draws_it(self):
        js = (ROOT / "ffm" / "ui" / "memo" / "front.js").read_text(encoding="utf-8")
        self.assertIn('row("Already decided"', js)


if __name__ == "__main__":
    unittest.main()
