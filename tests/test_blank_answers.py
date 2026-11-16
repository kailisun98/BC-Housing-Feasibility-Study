"""A question the manager has not answered is uncertain, never a fail, and no finding prints a Python None
(15 Nov 2026, after a design review: a blank site control was printed as "site control 'None'" and failed the fund).
Also: when a unit count cannot split the fund's mix, the suggestion says so before the run does."""

import copy
import unittest
from datetime import date
from pathlib import Path

from ffm import suggest
from ffm.checks import smallest_split
from ffm.engine import evaluate, load_json

ROOT = Path(__file__).resolve().parent.parent
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
OPTION = load_json(ROOT / "options" / "998-e-19th-ave-what-if-funder-ready.json")
AS_OF = date(2026, 10, 23)
PROGRAMS = ["bch.chf.eligibility", "bc.bcbuilds.eligibility"]


def by_id(L, rule_id):
    return next(r for r in L["results"] if r["rule_id"] == rule_id)


class BlankAnswers(unittest.TestCase):
    def test_blank_site_control_and_partner_are_uncertain(self):
        o = copy.deepcopy(OPTION)
        o["site_control"] = None
        o["developer_partner"] = None
        L = evaluate(SITE, o, AS_OF)
        chf, bcb = by_id(L, "bch.chf.eligibility"), by_id(L, "bc.bcbuilds.eligibility")
        self.assertEqual(chf["status"], "uncertain")
        self.assertIn("site control in hand", chf["finding"])
        self.assertEqual(bcb["status"], "uncertain")
        self.assertIn("developer or builder partner", bcb["finding"])

    def test_an_answered_no_still_fails(self):
        o = copy.deepcopy(OPTION)
        o["site_control"] = "none"
        o["developer_partner"] = False
        L = evaluate(SITE, o, AS_OF)
        self.assertEqual(by_id(L, "bch.chf.eligibility")["status"], "fail")
        self.assertIn("site control (none) does not meet", by_id(L, "bch.chf.eligibility")["finding"])
        self.assertEqual(by_id(L, "bc.bcbuilds.eligibility")["status"], "fail")

    def test_no_finding_prints_a_python_none(self):
        o = copy.deepcopy(OPTION)
        for k in ("site_control", "developer_partner", "proponent_type", "rent_tiers_units", "accessible_units", "land_tenure_plan"):
            o[k] = None
        L = evaluate(SITE, o, AS_OF)
        for r in L["results"]:
            self.assertNotIn("'None'", r["finding"] + (r.get("action") or ""), r["rule_id"])
            self.assertNotIn("None ", r["finding"], r["rule_id"])


class SmallCounts(unittest.TestCase):
    def test_smallest_split_for_the_fund_mix(self):
        self.assertEqual(smallest_split({"market": .3, "rgi": .5, "deep_subsidy": .2}, .02), 10)

    def test_four_homes_cannot_meet_the_mix_and_the_suggestion_says_so(self):
        # a small RT-3 lot: the SSMUH minimum gives four homes, which no split lands on 30/50/20
        site = {"id": "small-lot", "address": "609 Heatley Ave, Vancouver, BC", "municipality": "City of Vancouver", "zoning_district": "RT-3",
                "site_area_m2": 566.7, "frontage_m": 37.2, "depth_m": 15.2, "in_former_community_vision_area": None, "in_transit_oriented_area": None,
                "frequent_bus_stop_within_400m": None, "has_water_and_sewer": True, "existing_trees_on_site": [], "owner_type": None, "land_tenure_plan": None}
        S = suggest.suggest(site, PROGRAMS, date(2026, 11, 15), "funder-ready")
        n = sum(v for v in S["option"]["units"].values() if v)
        self.assertEqual(n, 4)
        keys = [u["key"] for u in S["unsure"]]
        self.assertIn("unit_count_for_the_mix", keys)
        self.assertIn("10 homes", next(u for u in S["unsure"] if u["key"] == "unit_count_for_the_mix")["who"])
        self.assertIn("short", S["fields"]["rent_tiers_units.market"]["note"])
        # the run's finding says the same thing, so the Fail is one the manager was told about
        L = evaluate(site, S["option"], date(2026, 11, 15))
        self.assertIn("no split of 4 homes", by_id(L, "bch.chf.eligibility")["finding"])
