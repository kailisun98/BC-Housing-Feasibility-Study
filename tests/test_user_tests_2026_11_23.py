"""What the simulated user tests of 23 Nov 2026 found, pinned (docs/user-tests-2026-11-23/README.md).

Four role-played reviewers ran real Vancouver sites through the tool. The defects they shared: a grant counted from
a fund the option fails; "Likely" over a negative operating income; funder and family-unit fails on housing those
rules were never written for; a rezoning rule read where no rezoning is proposed; homes the plates do not hold left
off page one; a memo buried under other districts' rules; a wrong parcel returned silently.
"""

import copy
import json
import unittest
from datetime import date
from pathlib import Path

from ffm import layout, lookup, massing, memo, proforma
from ffm.checks import housing_kind, proposes_rezoning
from ffm.engine import evaluate, load_json

ROOT = Path(__file__).resolve().parent.parent
AS_OF = date(2026, 11, 23)
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
READY = load_json(ROOT / "options" / "998-e-19th-ave-what-if-funder-ready.json")


def by_id(ledger, rule_id):
    return next(r for r in ledger["results"] if r["rule_id"] == rule_id)


def open_ids(ledger):
    return [u["rule_id"] for u in ledger["summary"]["answers"]["unsure"]]


def all_deep(option):
    """The same building with every home at the deep-subsidy rent: deeper than the Community Housing Fund's mix."""
    o = copy.deepcopy(option)
    n = sum(v for v in o["units"].values() if v)
    o["rent_tiers_units"] = {"market": 0, "rgi": 0, "deep_subsidy": n}
    return o


class GrantsFollowTheFundersAnswer(unittest.TestCase):
    def test_a_failed_fund_contributes_nothing_and_the_line_says_why(self):
        o = all_deep(READY)
        L = evaluate(SITE, o, AS_OF)
        self.assertEqual(by_id(L, "bch.chf.eligibility")["status"], "fail")
        pf = proforma.build(SITE, o, L)
        self.assertEqual([g for g in pf["funding"]["grants"] if g.get("program") == "bch.chf.eligibility"], [])
        self.assertEqual(pf["funding"]["not_counted"][0]["program"], "bch.chf.eligibility")
        line = next(x for x in pf["lines"] if x["key"] == "grant_chf")
        self.assertEqual(line["value"], 0)
        self.assertIn("not counted", line["note"])
        self.assertIn("Not counted: Community Housing Fund grant", "\n".join(proforma.markdown(pf)))

    def test_a_passed_fund_is_counted_as_illustrative_with_the_closed_intake_said(self):
        L = evaluate(SITE, READY, AS_OF)
        pf = proforma.build(SITE, READY, L)
        g = next(g for g in pf["funding"]["grants"] if g.get("program") == "bch.chf.eligibility")
        self.assertTrue(g["illustrative"])
        self.assertIs(g["intake_open"], False)
        self.assertIn("no grant is committed or implied", g["note"])

    def test_a_deeper_mix_is_said_to_point_elsewhere_not_to_a_weaker_project(self):
        L = evaluate(SITE, all_deep(READY), AS_OF)
        r = by_id(L, "bch.chf.eligibility")
        self.assertIn("deeper affordability than this fund's mix", r["finding"])
        self.assertIn("ask BC Housing which program fits", r["action"])


class RentsThatDoNotCoverTheRunningCosts(unittest.TestCase):
    def test_a_negative_operating_income_is_never_likely(self):
        o = all_deep(READY)
        o["finance"] = {"land_cost_cad": 0, "equity_cad": 500_000_000, "other_grants_cad": 0}     # more money than the building costs
        L = evaluate(SITE, o, AS_OF)
        pf = proforma.build(SITE, o, L)
        self.assertLess(pf["operating"]["noi"], 0)
        self.assertLess(pf["gap"]["value"], 0)
        self.assertEqual(pf["verdict"]["word"], "unlikely")
        self.assertEqual(pf["verdict"]["operating_shortfall"], -pf["operating"]["noi"])
        self.assertIn("the rents do not cover the running costs", pf["verdict"]["why"][0])
        self.assertTrue(proforma.next_step(pf).startswith(proforma.OPERATING_FUNDER))
        md = "\n".join(proforma.markdown(pf))
        self.assertIn("- Surplus **$", md)
        self.assertNotIn("$-", md.split("| Line |")[0])


class HousingTheRulesWereNotWrittenFor(unittest.TestCase):
    def setUp(self):
        self.o = all_deep(READY)
        n = sum(v for v in self.o["units"].values() if v)
        self.o["units"] = {"studio": n, "one_bed": 0, "two_bed": 0, "three_bed_plus": 0}
        self.o["housing_type"] = "transitional"

    def test_the_kind_is_read_from_the_option(self):
        self.assertEqual(housing_kind(READY), "independent")
        self.assertEqual(housing_kind(self.o), "transitional")
        self.assertEqual(housing_kind({"units": {"studio": 40}, "supportive_units": 40}), "supportive")
        self.assertEqual(housing_kind({"units": {"studio": 40}, "supportive_units": 35}), "independent")

    def test_the_funders_answer_is_not_assessed_with_one_open_item(self):
        L = evaluate(SITE, self.o, AS_OF)
        self.assertEqual(by_id(L, "bch.chf.eligibility")["status"], "not_applicable")
        self.assertEqual(by_id(L, "bc.bcbuilds.eligibility")["status"], "not_applicable")
        f = L["summary"]["answers"]["funded"]
        self.assertEqual(f["verdict"], "not assessed")
        self.assertTrue(f["words"].startswith("Not assessed: the rules list 4 programs for transitional housing ("), f["words"])
        self.assertTrue(f["words"].endswith("and test none of their criteria"))
        names = [m["program"] for m in f["matches"]]
        self.assertIn("Reaching Home", names)
        self.assertNotIn("the Supportive Housing Fund", names)          # written for supportive housing, not transitional
        self.assertNotIn("the Indigenous Housing Fund", names)          # independent rental, and Indigenous-led
        self.assertIn("coverage.funders", open_ids(L))
        pf = proforma.build(SITE, self.o, L)
        self.assertEqual([g for g in pf["funding"]["grants"] if g.get("program")], [])

    def test_the_family_minimum_is_a_question_for_the_city_not_a_fail(self):
        r = by_id(evaluate(SITE, self.o, AS_OF), "cov.family_units")
        self.assertEqual(r["status"], "uncertain")
        self.assertIn("whether it applies to transitional housing is the City's to say", r["finding"])
        self.assertNotIn("add family units", r["action"])

    def test_the_scope_of_answer_2_is_said(self):
        f = evaluate(SITE, READY, AS_OF)["summary"]["answers"]["funded"]
        self.assertTrue(f["scope"].startswith("This screen tests the criteria of BC Builds and the Community Housing Fund."), f["scope"])
        self.assertIn("Would be, depending on an answer not given: the Indigenous Housing Fund", f["scope"])
        led = evaluate(SITE, dict(READY, indigenous_led=True), AS_OF)
        self.assertIn("Also written for this housing, listed and not tested: the Indigenous Housing Fund", led["summary"]["answers"]["funded"]["scope"])
        ihf = by_id(led, "bch.ihf.program")
        self.assertEqual(ihf["status"], "info")
        self.assertIn("Its homes are all rent geared to income; this option has 26 market-rent homes", ihf["finding"])
        self.assertEqual(by_id(evaluate(SITE, dict(READY, indigenous_led=False), AS_OF), "bch.ihf.program")["status"], "not_applicable")
        self.assertEqual(f["verdict"], "yes")                           # a listed program never moves the verdict


class NoRezoningProposed(unittest.TestCase):
    def test_what_counts_as_a_rezoning(self):
        self.assertTrue(proposes_rezoning({"rezoning_path": "CD-1 under the Interim Rezoning Policy"}))
        self.assertFalse(proposes_rezoning({"rezoning_path": "none: development permit DP-2020-00721 under the DEOD plan"}))
        self.assertFalse(proposes_rezoning({"rezoning_path": None}))
        self.assertFalse(proposes_rezoning({}))

    def test_a_development_permit_is_not_read_against_the_rezoning_family_rule(self):
        o = dict(READY, rezoning_path="none: development permit under the official development plan",
                 units={"studio": 50, "one_bed": 38, "two_bed": 0, "three_bed_plus": 0})
        r = by_id(evaluate(SITE, o, AS_OF), "cov.family_units")
        self.assertEqual(r["status"], "not_applicable")
        self.assertIn("No rezoning is proposed", r["finding"])
        self.assertIn("**Approval route: none: development permit", memo.markdown(evaluate(SITE, o, AS_OF)))

    def test_an_outright_scheme_lists_no_rezoning_rules_as_open(self):
        site = {"id": "t", "address": "a lot, Vancouver, BC", "municipality": "City of Vancouver", "zoning_district": "C-2A",
                "site_area_m2": 1200.0, "frontage_m": 30, "depth_m": 40, "keep_existing_buildings": False}
        o = {"id": "o", "tenure": "social_housing", "storeys": 6, "height_m": 19.8, "gfa_m2": 4200, "non_residential_gfa_m2": 420,
             "units": {"studio": 30, "one_bed": 10, "two_bed": 0, "three_bed_plus": 0}}
        L = evaluate(site, o, AS_OF)
        a = L["summary"]["answers"]["allowed"]
        self.assertEqual(a["outright"]["verdict"], "yes")
        self.assertEqual(a["by_rezoning"]["verdict"], "not needed")
        self.assertNotIn("cov.family_units", open_ids(L))
        self.assertNotIn("cov.irp.social_housing_rezoning", open_ids(L))
        self.assertIn("**By rezoning: not needed.**", memo.markdown(L))


class TheMemoPageOne(unittest.TestCase):
    def setUp(self):
        self.L = evaluate(SITE, READY, AS_OF)
        self.m = massing.build(SITE, READY, self.L)
        self.lay = layout.solve(SITE, READY, self.L, self.m)
        self.md = memo.markdown(self.L, self.m, layout=self.lay)

    def test_homes_the_plates_do_not_hold_are_an_open_item_and_said_beside_the_funders(self):
        self.assertLess(self.lay["units_placed"], self.lay["units_total"])
        items = memo.layout_open_items(self.lay)
        self.assertEqual(items[0]["title"], "Homes that do not fit the plates")
        self.assertIn("| Homes that do not fit the plates | Conditional |", self.md)
        self.assertIn(f"The first layout places {self.lay['units_placed']} of {self.lay['units_total']} homes", self.md.split("## 3.")[0])

    def test_other_districts_rules_are_counted_not_printed(self):
        self.assertNotIn("Written for ", self.md)
        self.assertIn("are written for other districts", self.md)
        self.assertIn("`ledger.json` lists them", self.md)

    def test_no_python_none_and_the_tool_says_whose_it_is(self):
        o = dict(READY)
        o.pop("proponent", None)
        md = memo.markdown(evaluate(SITE, o, AS_OF))
        self.assertIn("**Proponent:** not named", md)
        self.assertNotIn("None", md.split("## 1.")[0])
        self.assertIn("not affiliated with, reviewed by or a position of BC Housing", md)

    def test_open_items_carry_no_repository_or_stop_numbers(self):
        site = dict(SITE, zoning_district="I-2")
        md = memo.markdown(evaluate(site, READY, AS_OF))
        self.assertNotIn("inbox/", md.split("## Full ledger")[0])
        self.assertNotIn("stop 3", md.split("## Full ledger")[0])

    def test_a_run_with_no_massing_says_why(self):
        md = memo.markdown(self.L, massing_error="No road named 'Campbell Ave' adjoins the lot.")
        self.assertIn("| No massing or drawings in this memo | Uncertain |", md)
        self.assertIn("Campbell Ave", md)


class AnIndustrialDistrict(unittest.TestCase):
    def test_whether_housing_is_permitted_comes_first(self):
        # a district with no schedule in the rules (I-2): the open item asks the question first
        site = dict(SITE, zoning_district="I-2", lookup={"zoning_record": {"zoning_classification": "Industrial"}})
        L = evaluate(site, READY, AS_OF)
        item = next(u for u in L["summary"]["answers"]["unsure"] if u["rule_id"] == "coverage.district_schedule")
        self.assertTrue(item["action"].startswith("Manager: ask a City planner whether housing is permitted in I-2"))
        self.assertIn("industrial", L["summary"]["answers"]["allowed"]["outright"]["why"])

    def test_m1s_own_schedule_says_housing_is_not_a_use_it_allows(self):
        # M-1 was read from its PDF on 23 Nov 2026: having a schedule must not make housing read as allowed
        L = evaluate(dict(SITE, zoning_district="M-1"), READY, AS_OF)
        row = by_id(L, "cov.m1.outright_fsr")
        self.assertEqual(row["status"], "fail")
        self.assertIn("industrial district", row["finding"])
        self.assertTrue(row["action"].startswith("Manager: ask a City planner whether housing is permitted in M-1"))
        self.assertEqual(L["summary"]["answers"]["allowed"]["outright"]["verdict"], "no")


class TheNearestNumberOnTheStreet(unittest.TestCase):
    ROWS = [{"civic_number": n, "std_street": "STAINSBURY AV", "geo_point_2d": {"lat": 49.25, "lon": -123.06}} for n in (1851, 1995, 2001, 2037, 2110)]

    def test_the_nearest_civic_number_is_taken_not_the_streets_midpoint(self):
        self.assertEqual(lookup.nearest_civic(self.ROWS, 2009)["civic_number"], 2001)
        self.assertEqual(lookup.nearest_civic(self.ROWS, 1900)["civic_number"], 1851)

    def test_a_tie_goes_to_the_same_side_of_the_street(self):
        rows = [dict(self.ROWS[0], civic_number=n) for n in (2004, 2014)]
        self.assertEqual(lookup.nearest_civic(rows, 2009)["civic_number"], 2004)
        rows = [dict(self.ROWS[0], civic_number=n) for n in (2006, 2011)]     # 3 away and 2 away: the nearer one
        self.assertEqual(lookup.nearest_civic(rows, 2009)["civic_number"], 2011)

    def test_nothing_on_the_street_is_none(self):
        self.assertIsNone(lookup.nearest_civic([], 2009))

class TheOperatingPage(unittest.TestCase):
    """What it takes to run (23 Nov 2026, asked for by three of four simulated reviewers): the operator's own rents,
    running cost, support staffing and subsidy over the placeholders, and the subsidy needed a home a month."""

    def shelter(self, **ops):
        o = all_deep(READY)
        o["housing_type"] = "shelter"
        o["finance"] = {"land_cost_cad": 0, "equity_cad": 500_000_000, "other_grants_cad": 0}
        if ops:
            o["operations"] = ops
        L = evaluate(SITE, o, AS_OF)
        return proforma.build(SITE, o, L), sum(v for v in o["units"].values() if v)

    def test_entered_figures_stand_over_the_placeholders_and_say_so(self):
        pf, n = self.shelter(rent_deep_monthly_cad=0, operating_cost_per_unit_year_cad=9000, support_staffing_cad_year=1_000_000)
        p = pf["operating"]["page"]
        self.assertEqual(pf["operating"]["gross"], 0)
        self.assertEqual(pf["operating"]["vacancy"], 0)                      # a rent of $0 is a figure, not a blank
        self.assertEqual(p["operating_cost"], 9000 * n)
        self.assertEqual(p["operating_cost_from"], "entered")
        self.assertEqual(next(t for t in p["tiers"] if t["key"] == "deep_subsidy")["from"], "entered")
        self.assertEqual(p["net_before_subsidy"], -(9000 * n + pf["operating"]["reserve"] + 1_000_000))
        self.assertEqual(p["subsidy_to_run"], -p["net_before_subsidy"])
        self.assertEqual(p["subsidy_to_run_per_home_month"], round(p["subsidy_to_run"] / n / 12))
        self.assertFalse(next(x for x in pf["lines"] if x["key"] == "opex")["placeholder"])

    def test_staffing_is_never_assumed_for_supportive_housing(self):
        pf, _ = self.shelter(rent_deep_monthly_cad=2000)                      # rents cover the building; no staffing entered
        self.assertTrue(pf["operating"]["page"]["staffing_missing"])
        self.assertNotEqual(pf["verdict"]["word"], "likely")
        self.assertTrue(any("support staffing and who pays for it" in u for u in pf["verdict"]["unsure"]))
        o = dict(READY)                                                       # independent rental: none entered is none
        self.assertFalse(proforma.build(SITE, o, evaluate(SITE, o, AS_OF))["operating"]["page"]["staffing_missing"])

    def test_a_subsidy_counts_toward_a_loan_only_once_confirmed(self):
        ops = dict(rent_deep_monthly_cad=0, support_staffing_cad_year=1_000_000, operating_subsidy_cad_year=3_000_000)
        sought, _ = self.shelter(**ops)
        self.assertEqual(sought["funding"]["debt"]["supportable"], 0)
        self.assertEqual(sought["verdict"]["word"], "unsure")
        self.assertTrue(any("not yet confirmed" in w for w in sought["verdict"]["why"]))
        confirmed, _ = self.shelter(subsidy_confirmed=True, subsidy_term_years=40, **ops)      # a term that covers the loan (24 Nov 2026)
        self.assertGreater(confirmed["funding"]["debt"]["supportable"], 0)
        self.assertEqual(confirmed["verdict"]["word"], "likely")
        self.assertIsNone(confirmed["verdict"]["operating_shortfall"])

    def test_a_subsidy_too_small_still_leaves_a_shortfall(self):
        pf, _ = self.shelter(rent_deep_monthly_cad=0, support_staffing_cad_year=1_000_000, operating_subsidy_cad_year=100_000, subsidy_confirmed=True)
        self.assertEqual(pf["verdict"]["word"], "unlikely")
        self.assertEqual(pf["verdict"]["operating_shortfall"], -(pf["operating"]["page"]["net_before_subsidy"] + 100_000))

    def test_the_gap_financed_is_an_illustration_with_its_arithmetic(self):
        L = evaluate(SITE, READY, AS_OF)
        pf = proforma.build(SITE, READY, L)
        f = pf["operating"]["page"]["if_gap_financed"]
        self.assertEqual(f["loan"], pf["funding"]["debt"]["supportable"] + pf["gap"]["value"])
        self.assertEqual(f["subsidy_year"], max(0, f["annual_payment"] - pf["operating"]["noi"]))
        md = "\n".join(proforma.markdown(pf))
        self.assertIn("### What it takes to run, a year", md)
        self.assertIn("An illustration on this screen's mortgage terms, not a funder's financing", md)
        self.assertNotIn("$-", md.split("| Line |")[0])

    def test_with_nothing_entered_the_figures_are_as_before(self):
        L = evaluate(SITE, READY, date(2026, 10, 23))      # the committed run's own date
        pf = proforma.build(SITE, READY, L)
        committed = load_json(ROOT / "outputs" / "998-e-19th-ave" / "what-if-funder-ready" / "proforma.json")
        for key in ("capital", "gap"):
            self.assertEqual(pf[key], committed[key])
        self.assertEqual(pf["operating"]["noi"], committed["operating"]["noi"])
        self.assertEqual(pf["funding"]["total"], committed["funding"]["total"])

class ProgramsListedNotTested(unittest.TestCase):
    """The programs added on 23 Nov 2026 (rules/e_funding_programs.json, check program_match): each read from its own
    page, matched to the kind of housing, never moving a verdict."""

    def test_every_listed_program_cites_a_page_and_the_day_it_was_read(self):
        from ffm.rules_loader import load_rules, RULES_DIR
        listed = [r for r in load_rules(RULES_DIR) if r.check == "program_match"]
        self.assertGreaterEqual(len(listed), 9)
        for r in listed:
            v = r.version_on(AS_OF)
            self.assertIsNotNone(v, r.id)
            self.assertTrue(v.source.get("url", "").startswith("https://"), r.id)
            self.assertEqual(v.source.get("read_on"), "2026-11-23", r.id)
            self.assertTrue(v.params.get("what") and v.params.get("intake"), r.id)

    def test_supportive_housing_is_shown_its_programs_and_an_ended_one_is_not_a_door(self):
        L = evaluate(SITE, dict(all_deep(READY), housing_type="supportive", operator="A housing society"), AS_OF)
        f = L["summary"]["answers"]["funded"]
        names = [m["program"] for m in f["matches"] if not m["ended"]]
        self.assertIn("the Supportive Housing Fund", names)
        self.assertNotIn("Rapid Response to Homelessness", names)
        self.assertNotIn("Rapid Response to Homelessness", f["words"])
        item = next(u for u in L["summary"]["answers"]["unsure"] if u["rule_id"] == "coverage.funders")
        self.assertEqual(item["title"], "Programs for supportive housing: listed, not tested")
        md = memo.markdown(L)
        self.assertIn("Other programs written for this kind of housing, listed from their own pages and **not tested**:", md)
        self.assertIn("- **The Supportive Housing Fund**", md)

    def test_a_womens_program_waits_on_its_answer(self):
        o = dict(all_deep(READY), housing_type="transitional")
        m = lambda opt: {x["program"]: x for x in evaluate(SITE, opt, AS_OF)["summary"]["answers"]["funded"]["matches"]}
        self.assertTrue(m(o)["the Women's Transition Housing Fund"]["if"])
        self.assertEqual(m(dict(o, women_leaving_violence=True))["the Women's Transition Housing Fund"]["if"], [])
        self.assertNotIn("the Women's Transition Housing Fund", m(dict(o, women_leaving_violence=False)))

    def test_the_city_grant_is_for_vancouver_and_for_non_profits(self):
        self.assertEqual(by_id(evaluate(dict(SITE, municipality="Burnaby"), READY, AS_OF), "cov.chip.program")["status"], "not_applicable")
        self.assertEqual(by_id(evaluate(SITE, dict(READY, proponent_type="private_developer"), AS_OF), "cov.chip.program")["status"], "not_applicable")
        self.assertEqual(by_id(evaluate(SITE, READY, AS_OF), "cov.chip.program")["values"]["match"], True)

    def test_cmhcs_fund_is_closed_from_the_day_it_closed(self):
        r = by_id(evaluate(SITE, READY, AS_OF), "cmhc.ahf.readiness")
        self.assertIn("closed 19 Dec 2025", r["finding"])
        self.assertIn("continuous", by_id(evaluate(SITE, READY, date(2025, 6, 1)), "cmhc.ahf.readiness")["finding"])


class TheRestOfTheOpenList(unittest.TestCase):
    def test_who_operates_is_an_open_item_for_housing_that_runs_on_its_operator(self):
        o = dict(all_deep(READY), housing_type="shelter")
        self.assertIn("coverage.operator", open_ids(evaluate(SITE, o, AS_OF)))
        named = dict(o, operator="Another Society", proponent="A Church")
        ids = open_ids(evaluate(SITE, named, AS_OF))
        self.assertNotIn("coverage.operator", ids)
        self.assertIn("coverage.operator_agreement", ids)
        self.assertNotIn("coverage.operator_agreement", open_ids(evaluate(SITE, dict(named, land_tenure="lease_60_plus"), AS_OF)))
        self.assertNotIn("coverage.operator", open_ids(evaluate(SITE, READY, AS_OF)))            # independent rental: not asked

    def test_land_tenure_is_a_choice_read_before_the_sentence(self):
        chf = lambda **k: by_id(evaluate(SITE, dict(READY, **k), AS_OF), "bch.chf.eligibility")
        self.assertEqual(chf(land_tenure="lease_shorter")["status"], "fail")
        self.assertIn("shorter than the 60 years", chf(land_tenure="lease_shorter")["finding"])
        self.assertEqual(chf(land_tenure="to_confirm")["status"], "uncertain")
        self.assertEqual(chf(land_tenure="lease_60_plus")["status"], "pass")
        self.assertEqual(chf(land_tenure="lease_60_plus", land_tenure_plan="to confirm")["status"], "pass")    # the choice wins

    def test_a_street_built_to_its_lot_lines_gets_no_front_or_side_yard(self):
        from ffm.suggest import setbacks_for
        lot = {"site_area_m2": 1360.0, "frontage_m": 36.0, "depth_m": 37.7}
        self.assertGreater(setbacks_for(lot)["side"], 0)
        sb = setbacks_for(dict(lot, builds_to_lot_lines=True))
        self.assertEqual((sb["front"], sb["side"]), (0.0, 0.0))
        self.assertGreater(sb["rear"], 0)

    def test_home_sizes_are_the_architects_to_set(self):
        L = evaluate(SITE, READY, AS_OF)
        m = massing.build(SITE, READY, L)
        base = layout.solve(SITE, READY, L, m)
        o = dict(READY, unit_area_allowance=1.0)
        L2 = evaluate(SITE, o, AS_OF)
        tight = layout.solve(SITE, o, L2, massing.build(SITE, o, L2))
        self.assertGreater(tight["units_placed"], base["units_placed"])
        wild = dict(READY, unit_area_allowance=5)                                                  # out of range: ignored
        L3 = evaluate(SITE, wild, AS_OF)
        self.assertEqual(layout.solve(SITE, wild, L3, massing.build(SITE, wild, L3))["units_placed"], base["units_placed"])

    def test_the_projects_own_building_cost_stands_over_the_base(self):
        tall = dict(READY, storeys=11, height_m=36.3, non_residential_gfa_m2=1500)
        L = evaluate(SITE, tall, AS_OF)
        pf = proforma.build(SITE, tall, L)
        self.assertTrue(any("a hard cost for this building" in u and "11 storeys" in u and "not homes" in u for u in pf["verdict"]["unsure"]))
        own = dict(tall, finance={"hard_cost_per_m2_cad": 7000})
        pf2 = proforma.build(SITE, own, evaluate(SITE, own, AS_OF))
        self.assertEqual(pf2["capital"]["hard"], round(tall["gfa_m2"] * 7000))
        self.assertFalse(any("a hard cost for this building" in u for u in pf2["verdict"]["unsure"]))

    def test_bc_builds_published_loan_terms_are_shown_beside_the_illustration(self):
        pf = proforma.build(SITE, READY, evaluate(SITE, READY, AS_OF))
        t = pf["operating"]["page"]["if_gap_financed"]["on_program_terms"]
        self.assertEqual((t["rate_pct"], t["amortization_years"]), (4.55, 35))
        self.assertLess(t["annual_payment"], pf["operating"]["page"]["if_gap_financed"]["annual_payment"])
        self.assertIn("on BC Builds' published take-out terms", "\n".join(proforma.operating_markdown(pf)))

    def test_beds_give_a_figure_a_bed(self):
        o = dict(all_deep(READY), housing_type="shelter", beds=160, operations={"rent_deep_monthly_cad": 0, "support_staffing_cad_year": 2_000_000})
        p = proforma.build(SITE, o, evaluate(SITE, o, AS_OF))["operating"]["page"]
        self.assertEqual(p["subsidy_to_run_per_bed_month"], round(p["subsidy_to_run"] / 160 / 12))

    def test_the_memo_says_a_calibration_run_and_the_address_typed(self):
        site = dict(SITE, lookup={"typed": "320 E Hastings St", "civic_mismatch": True})
        md = memo.markdown(evaluate(site, dict(READY, as_built=True, operator="A housing society"), AS_OF))
        head = md.split("## 1.")[0]
        self.assertIn('Looked up as "320 E Hastings St"', head)
        self.assertIn("A calibration run against a completed project", head)
        self.assertIn("**Operator:** A housing society", head)

class TheLayoutRedesign(unittest.TestCase):
    """23 Nov 2026, from the architect's test: home types stacked in bays, an entry lobby, services below grade when
    the ground floor is full, no slivers, and a plate box that turns to a skewed lot's longest side."""

    def setUp(self):
        self.L = evaluate(SITE, READY, AS_OF)
        self.m = massing.build(SITE, READY, self.L)
        self.lay = layout.solve(SITE, READY, self.L, self.m)

    def test_the_same_home_type_stands_in_the_same_bay_floor_after_floor(self):
        self.assertEqual(self.lay["plate"]["stacking"], "bays")
        bays: dict = {}
        for fl in self.lay["floors"]:
            for z in fl["zones"]:
                if z.get("bay") and z.get("unit"):
                    bays.setdefault((z["bay"], round(z["x"], 1), round(z["y"], 1)), []).append((fl["level"], z["unit"]))
        tall = [v for v in bays.values() if len(v) >= 3]
        self.assertTrue(tall)
        order = list(layout.UNIT_KEYS)                              # largest first
        for stack in tall:
            kinds = [k for _, k in sorted(stack)]
            # a bay holds one type from the bottom up; where the program runs out it steps down to a smaller home, never up
            self.assertEqual(kinds, sorted(kinds, key=order.index), stack)
            self.assertGreaterEqual(kinds.count(kinds[0]), len(kinds) - 2, stack)

    def test_homes_do_not_overlap_and_the_family_homes_are_all_placed(self):
        for fl in self.lay["floors"]:
            zs = [z for z in fl["zones"] if z["block"] not in ("corridor", "core")]
            for i, a in enumerate(zs):
                for b in zs[i + 1:]:
                    apart = a["x"] + a["w"] <= b["x"] + 0.01 or b["x"] + b["w"] <= a["x"] + 0.01 or a["y"] + a["d"] <= b["y"] + 0.01 or b["y"] + b["d"] <= a["y"] + 0.01
                    self.assertTrue(apart, (fl["level"], a["block"], b["block"]))
        self.assertNotIn("three_bed_plus", [s["block"] for s in self.lay["shortfall"]])
        self.assertEqual(next(c for c in self.lay["adjacencies"] if c["id"] == "family_low")["status"], "pass")

    def test_the_ground_floor_has_a_lobby_the_entry_points_at(self):
        ground = self.lay["floors"][0]
        lobby = [z for z in ground["zones"] if z.get("entry")]
        self.assertEqual(len(lobby), 1)
        self.assertEqual((lobby[0]["block"], lobby[0]["side"]), ("design_space", "front"))
        self.assertAlmostEqual(layout._entry_x(self.lay, ground), lobby[0]["x"] + lobby[0]["w"] / 2)

    def test_services_stay_on_the_ground_floor_or_go_below_grade(self):
        levels = {fl["level"] for fl in self.lay["floors"] for z in fl["zones"] if z["block"] == "services"}
        self.assertLessEqual(levels, {0})
        self.assertNotIn("services", [s["block"] for s in self.lay["shortfall"]])

    def test_no_ground_floor_room_is_a_sliver(self):
        for fl in self.lay["floors"]:
            for z in fl["zones"]:
                if z["block"] in ("amenity", "services", "design_space"):
                    self.assertGreaterEqual(min(z["w"], z["d"]), 2.0 - 0.01, z)

    def test_the_editor_reads_the_stacked_plan_back_unchanged(self):
        opt = dict(READY, layout={"zones": layout.zones_of(self.lay)})
        back = layout.solve(SITE, opt, self.L, self.m)
        self.assertEqual(back["units_placed"], self.lay["units_placed"])
        self.assertEqual(back["geometry"], [])
        self.assertEqual({c["id"]: c["status"] for c in back["adjacencies"]}, {c["id"]: c["status"] for c in self.lay["adjacencies"]})

    def test_the_plate_box_turns_to_a_skewed_lots_long_side(self):
        from ffm import boundary
        import math
        # a parallelogram 60 m along its long side, 20 m across, its long sides at 40 degrees to the frontage
        c, s = math.cos(math.radians(40)), math.sin(math.radians(40))
        lot = [(0.0, 0.0), (60 * c, 60 * s), (60 * c - 20 * s, 60 * s + 20 * c), (-20 * s, 20 * c)]
        square = boundary.largest_rect(lot, 0.5)
        turned = boundary.turned_rect(lot, 0.5)
        self.assertAlmostEqual(turned["angle_deg"], 40.0, places=1)
        self.assertGreater(turned["area_m2"], 2 * square["area_m2"])
        self.assertGreater(turned["area_m2"], 0.9 * 60 * 20)
        # a rectangle square to its frontage is left alone
        self.assertEqual(boundary.turned_rect([(0, 0), (30, 0), (30, 40), (0, 40)], 0.5)["angle_deg"], 0.0)
        # brought back to the lot's frame, the turned box's centre is inside the lot
        cx, cy = boundary.rotate_pt((turned["x"] + turned["w"] / 2, turned["y"] + turned["d"] / 2), turned["angle_deg"])
        self.assertTrue(boundary.point_in((cx, cy), lot))

def _no_overlaps(case, lay):
    for fl in lay["floors"]:
        zs = [z for z in fl["zones"] if z["block"] not in ("corridor", "core")]
        for i, a in enumerate(zs):
            for b in zs[i + 1:]:
                apart = a["x"] + a["w"] <= b["x"] + 0.02 or b["x"] + b["w"] <= a["x"] + 0.02 or a["y"] + a["d"] <= b["y"] + 0.02 or b["y"] + b["d"] <= a["y"] + 0.02
                case.assertTrue(apart, (fl["level"], a["block"], b["block"], a, b))


def _bare(**more):
    site = {k: v for k, v in SITE.items() if k not in ("parcel", "osm", "front_face", "front_street", "lookup", "boundary_m")}
    site.update(more)
    return site


class TheCorridorAcrossThePlate(unittest.TestCase):
    """23 Nov 2026: on a plate deeper than it is wide the corridor is also run from the street to the lane."""

    def setUp(self):
        self.site = _bare(id="narrow", frontage_m=21.0, depth_m=32.0, site_area_m2=672.0)
        self.opt = dict(READY, id="narrow-option", storeys=6, height_m=19.8, gfa_m2=3000, residential_gfa_m2=3000, non_residential_gfa_m2=0,
                        units={"studio": 8, "one_bed": 12, "two_bed": 8, "three_bed_plus": 4}, accessible_units=2,
                        setbacks_m={"front": 2.5, "rear": 1.5, "side": 0.5})
        self.L = evaluate(self.site, self.opt, AS_OF)
        self.m = massing.build(self.site, self.opt, self.L)
        self.lay = layout.solve(self.site, self.opt, self.L, self.m)

    def test_a_deep_plate_takes_the_corridor_across_and_no_home_is_deeper_than_daylight(self):
        p = self.lay["plate"]
        self.assertGreater(p["depth_m"], p["width_m"])
        self.assertEqual((p["arrangement"], p.get("corridor")), ("cross", "across"))
        self.assertLessEqual(p["unit_depth_m"], 12.0)
        corridors = [z for z in self.lay["floors"][1]["zones"] if z["block"] == "corridor"]
        self.assertTrue(corridors and all(z["d"] > z["w"] for z in corridors))
        self.assertTrue(any("runs across the plate" in w for w in self.lay["warnings"]))
        along = layout._solve(self.site, self.opt, self.L, self.m, layout.blocks(self.opt, self.L), None)
        rank = lambda L: layout._STATUS_RANK[L["egress"]["status"]]                                  # chosen for more homes, or as many with better exits
        self.assertTrue(self.lay["units_placed"] > along["units_placed"] or (self.lay["units_placed"] == along["units_placed"] and rank(self.lay) < rank(along)))

    def test_everything_stays_on_the_plate_and_nothing_overlaps(self):
        p = self.lay["plate"]
        for fl in self.lay["floors"]:
            for z in fl["zones"]:
                self.assertGreaterEqual(z["x"], p["x"] - 0.02, z)
                self.assertGreaterEqual(z["y"], p["y"] - 0.02, z)
                self.assertLessEqual(z["x"] + z["w"], p["x"] + p["width_m"] + 0.02, z)
                self.assertLessEqual(z["y"] + z["d"], p["y"] + p["depth_m"] + 0.02, z)
        _no_overlaps(self, self.lay)

    def test_the_lobby_is_at_the_street_and_the_exits_are_read_the_same_both_ways(self):
        ground = self.lay["floors"][0]
        lobby = next(z for z in ground["zones"] if z.get("entry"))
        self.assertAlmostEqual(lobby["y"], self.lay["plate"]["y"], places=1)          # the street edge of the plate
        self.assertEqual(self.lay["egress"]["status"], "pass")
        # the plan kept through the block editor is read as the same arrangement, with the same exits and stairs
        back = layout.solve(self.site, dict(self.opt, layout={"zones": layout.zones_of(self.lay)}), self.L, self.m)
        self.assertEqual((back["plate"]["arrangement"], back["plate"].get("corridor")), ("cross", "across"))
        self.assertEqual(back["units_placed"], self.lay["units_placed"])
        self.assertEqual(back["egress"]["status"], self.lay["egress"]["status"])
        self.assertEqual([f["farthest_travel_m"] for f in back["egress"]["floors"]], [f["farthest_travel_m"] for f in self.lay["egress"]["floors"]])
        core = next(z for z in self.lay["floors"][1]["zones"] if z["block"] == "core" and z["d"] >= 7)
        stairs = layout._stair_boxes(core, self.lay["floors"][1]["zones"])
        self.assertTrue(stairs and all(s["x"] >= core["x"] - 0.01 and s["y"] >= core["y"] - 0.01 for s in stairs))
        self.assertIn("<svg", layout.svg_plans(self.lay))

    def test_a_plate_wider_than_deep_keeps_its_corridor_along_the_street(self):
        L = evaluate(SITE, READY, AS_OF)
        lay = layout.solve(SITE, READY, L, massing.build(SITE, READY, L))
        self.assertNotEqual(lay["plate"]["arrangement"], "cross")


class APlateInTwoParts(unittest.TestCase):
    """23 Nov 2026: where the envelope holds a second rectangle beside the plate box and the floor area asks for it,
    the plate takes it as a wing."""

    RING = [[0, 0], [60, 0], [60, 22], [26, 22], [26, 55], [0, 55]]      # a bar along the street and a wing behind its left end

    def setUp(self):
        self.site = _bare(id="l-lot", frontage_m=60.0, depth_m=55.0, site_area_m2=60 * 22 + 26 * 33.0, boundary_m=self.RING)
        self.opt = dict(READY, id="l-option", storeys=6, height_m=19.8, gfa_m2=8400, residential_gfa_m2=7800, non_residential_gfa_m2=600,
                        units={"studio": 30, "one_bed": 44, "two_bed": 30, "three_bed_plus": 10}, setbacks_m={"front": 3.0, "rear": 3.0, "side": 3.0})
        self.L = evaluate(self.site, self.opt, AS_OF)
        self.m = massing.build(self.site, self.opt, self.L)
        self.pm = self.m["masses"][0]

    def test_the_geometry_finds_a_wing_that_meets_the_box_and_draws_their_outline(self):
        from ffm import boundary
        box = boundary.largest_rect(self.RING, 0.5)
        wing = boundary.wing_rect(self.RING, box, 0.5)
        self.assertIsNotNone(wing)
        self.assertIn(wing["joins"], ("left", "right", "front", "rear"))
        self.assertAlmostEqual(box["area_m2"] + wing["area_m2"], boundary.area(self.RING), delta=1.0)     # an L is two rectangles
        outline = boundary.rects_outline([box, wing])
        self.assertEqual(len(outline), 6)
        self.assertAlmostEqual(boundary.area(outline), boundary.area(self.RING), delta=1.0)
        self.assertIsNone(boundary.wing_rect([(0, 0), (30, 0), (30, 40), (0, 40)], boundary.largest_rect([(0, 0), (30, 0), (30, 40), (0, 40)], 0.5), 0.5))

    def test_the_mass_takes_the_wing_when_the_floor_area_asks_and_counts_its_own_area(self):
        self.assertEqual(len(self.pm["parts"]), 2)
        self.assertEqual(len(self.pm["footprint"]), 6)
        both = sum(p["w"] * p["d"] for p in self.pm["parts"])
        self.assertAlmostEqual(self.pm["plate_area_m2"], both, delta=0.5)
        self.assertLess(self.pm["plate_area_m2"], self.pm["plate_width_m"] * self.pm["plate_depth_m"])      # not the rectangle round it
        self.assertAlmostEqual(self.pm["fsr"], both * 6 / self.site["site_area_m2"], places=2)
        self.assertTrue(any("takes a wing" in w for w in self.m["warnings"]))
        small = dict(self.opt, gfa_m2=4000)                                                                # fits the box alone
        self.assertNotIn("parts", massing.build(self.site, small, evaluate(self.site, small, AS_OF))["masses"][0])

    def test_each_part_is_laid_out_and_the_rest_is_a_cut_out(self):
        lay = layout.solve(self.site, self.opt, self.L, self.m)
        self.assertEqual(lay["plate"]["arrangement"], "wings")
        self.assertEqual(len(lay["plate"]["parts"]), 2)
        ground = lay["floors"][1]
        self.assertTrue(any(z["block"] == "void" for z in ground["zones"]))
        self.assertTrue(any(z.get("unit") and z.get("wing") for fl in lay["floors"] for z in fl["zones"]))
        self.assertTrue(any(z.get("unit") and not z.get("wing") for fl in lay["floors"] for z in fl["zones"]))
        self.assertGreaterEqual(sum(1 for z in ground["zones"] if z["block"] == "core"), 2)                # a core in each part
        self.assertAlmostEqual(lay["totals"]["floor_area_m2"], self.pm["plate_area_m2"] * 6, delta=6.0)
        _no_overlaps(self, lay)
        self.assertTrue(lay["egress"]["by_part"])
        self.assertLessEqual(max(float(p.get("unit_depth_m") or 0) for p in [lay["plate"]]), 12.0)
        for name in ("plans", "stacking", "site-plan"):
            self.assertIn("<svg", layout.sheets(lay, self.site, self.m, self.L)[name])

    def test_a_rectangular_lot_is_one_plate_as_before(self):
        L = evaluate(SITE, READY, AS_OF)
        self.assertNotIn("parts", massing.build(SITE, READY, L)["masses"][0])

class WhatTheReviewsRaisedAndWasLeft(unittest.TestCase):
    """23 Nov 2026, last pass: the items of the simulated reviews that no source document was needed for."""

    def test_an_approval_route_by_permit_reads_no_rezoning_rules(self):
        # within RM-1's outright figures (a permit cannot approve more than the schedule allows; 24 Nov 2026)
        o = dict(READY, approval_route="development_permit", storeys=3, height_m=9.9, gfa_m2=3300, residential_gfa_m2=3300, non_residential_gfa_m2=0,
                 units={"studio": 20, "one_bed": 18, "two_bed": 0, "three_bed_plus": 0})
        L = evaluate(SITE, o, AS_OF)
        self.assertEqual(by_id(L, "cov.family_units")["status"], "not_applicable")
        self.assertEqual(by_id(L, "cov.irp.social_housing_rezoning")["status"], "not_applicable")
        a = L["summary"]["answers"]["allowed"]
        self.assertEqual((a["by_rezoning"]["verdict"], a["approval_route"]), ("not needed", "development_permit"))
        self.assertIn("**By rezoning: not needed.**", memo.markdown(L))
        self.assertTrue(evaluate(SITE, dict(READY, approval_route="rezoning", rezoning_path=None), AS_OF)["summary"]["answers"]["allowed"]["by_rezoning"]["verdict"] != "not needed")

    def test_a_program_the_option_does_not_target_is_not_its_open_item(self):
        o = dict(READY, target_programs=["bch.chf.eligibility"], developer_partner=False)        # BC Builds would fail: no partner
        L = evaluate(SITE, o, AS_OF)
        self.assertEqual(by_id(L, "bc.bcbuilds.eligibility")["status"], "fail")
        self.assertNotIn("bc.bcbuilds.eligibility", open_ids(L))
        self.assertIn("bc.bcbuilds.eligibility", open_ids(evaluate(SITE, dict(o, target_programs=[]), AS_OF)))

    def test_every_open_item_that_someone_outside_settles_names_who_to_ask(self):
        o = dict(READY, site_control=None)
        items = {u["rule_id"]: u for u in evaluate(dict(SITE, in_transit_oriented_area=None), o, AS_OF)["summary"]["answers"]["unsure"]}
        self.assertIn("BC Housing, a development manager", items["bch.chf.eligibility"]["contact"])
        self.assertTrue(items["bch.chf.eligibility"]["action"].endswith(items["bch.chf.eligibility"]["contact"] + "."))
        self.assertTrue(items["bc.toa.minimum_density"]["action"].startswith("Manager: check the City's transit-oriented areas map"))

    def test_floors_that_are_not_homes_carry_their_own_cost_income_and_money(self):
        base = dict(READY, finance={})
        plain = proforma.build(SITE, base, evaluate(SITE, base, AS_OF))
        own = dict(READY, finance={"non_residential_cost_per_m2_cad": 3000, "non_residential_income_cad_year": 120000, "non_residential_funding_cad": 2_000_000})
        pf = proforma.build(SITE, own, evaluate(SITE, own, AS_OF))
        nr = READY["non_residential_gfa_m2"]
        self.assertEqual(next(x for x in pf["lines"] if x["key"] == "hard_nonres")["value"], round(nr * 3000))
        self.assertLess(pf["capital"]["hard"], plain["capital"]["hard"])
        self.assertEqual(pf["operating"]["noi"], plain["operating"]["noi"] + 120000)
        self.assertTrue(any(g["label"].startswith("Money for the floors that are not homes") and g["value"] == 2_000_000 for g in pf["funding"]["grants"]))

    def test_a_taller_ground_floor_lifts_the_floors_above_and_the_height(self):
        o = dict(READY, ground_floor_height_m=4.5, height_m=None)
        L = evaluate(SITE, o, AS_OF)
        m = massing.build(SITE, o, L)
        f2f = o["floor_to_floor_m"]
        self.assertAlmostEqual(m["masses"][0]["height_m"], o["storeys"] * f2f + (4.5 - f2f), places=2)
        lay = layout.solve(SITE, o, L, m)
        self.assertEqual(lay["plate"]["ground_floor_m"], 4.5)
        self.assertAlmostEqual(lay["floors"][1]["z"], 4.5, places=2)
        self.assertAlmostEqual(lay["floors"][2]["z"], 4.5 + f2f, places=2)
        self.assertIn("ground floor", layout.svg_elevations(lay, m))
        plain = layout.solve(SITE, READY, evaluate(SITE, READY, AS_OF), massing.build(SITE, READY, evaluate(SITE, READY, AS_OF)))
        self.assertNotIn("ground_floor_m", plain["plate"])

    def test_the_suggestion_says_when_two_candidates_are_one_building_and_why_storeys_cost_homes(self):
        from ffm.suggest import suggest
        site = _bare(id="c2a", zoning_district="C-2A", frontage_m=30.0, depth_m=40.0, site_area_m2=1200.0, in_former_community_vision_area=False)
        s = suggest(site, ["bch.chf.eligibility"], AS_OF, "funder-ready")
        self.assertIn("would give this same building here", s["same_building_note"])
        tall = suggest(site, ["bch.chf.eligibility"], AS_OF, "funder-ready", fixed={"storeys": int(s["option"]["storeys"]) + 4})
        why = next(u for u in tall["unsure"] if u["key"] == "storeys")
        self.assertIn("a slimmer floor holds fewer homes", why["why"])

    def test_the_memo_file_explains_its_words_and_the_massing_drawing_has_the_street_at_the_bottom(self):
        L = evaluate(SITE, READY, AS_OF)
        m = massing.build(SITE, READY, L)
        md = memo.markdown(L, m, proforma=proforma.build(SITE, READY, L))
        words = md.split("## Words in this memo")[1].split("## ")[0]
        for term in ("**FSR**", "**RGI**", "**Deep subsidy**", "**Rezoning**"):
            self.assertIn(term, words)
        self.assertIn("street side at the bottom", massing.svg(m))

    def test_the_community_housing_funds_2026_limits_are_bc_housings_own(self):
        from ffm.rules_loader import load_rules, RULES_DIR
        chf = next(r for r in load_rules(RULES_DIR) if r.id == "bch.chf.eligibility")
        now, before = chf.version_on(AS_OF), chf.version_on(date(2025, 6, 1))
        self.assertEqual(now.params["low_moderate_income_limits_cad"]["under_two_bed"], 90560)
        self.assertEqual(before.params["low_moderate_income_limits_cad"]["under_two_bed"], 85870)
        self.assertEqual(now.params["deep_subsidy_income_limits_cad"]["under_two_bed"], 24596)
        self.assertTrue(now.source["verified"])
        self.assertIn("tolerance", now.params["not_read_from_bc_housing"])

    def test_a_church_in_a_societys_name_is_not_a_church_owner(self):
        named = by_id(evaluate(dict(SITE, owner_type="society", owner="First Example Church Community Society"), READY, AS_OF), "cov.dcl_cac_social_housing")
        self.assertNotIn("existing church use", named["finding"])
        self.assertIn("existing church use", by_id(evaluate(dict(SITE, owner_type="church"), READY, AS_OF), "cov.dcl_cac_social_housing")["finding"])

class WhatBCHousingsDocumentsSay(unittest.TestCase):
    """23 Nov 2026: BC Housing's PDFs were downloaded with Kai's say-so and read; these are the figures that came out."""

    @staticmethod
    def _rule(rid):
        from ffm.rules_loader import load_rules, RULES_DIR
        return next(r for r in load_rules(RULES_DIR) if r.id == rid)

    def test_the_grant_a_home_follows_bc_housings_fiscal_year(self):
        chf = self._rule("bch.chf.eligibility")
        self.assertEqual(chf.version_on(date(2026, 2, 1)).params["provisional_grant_per_unit_cad_2025_26"], 171211)
        self.assertEqual(chf.version_on(AS_OF).params["provisional_grant_per_unit_cad"], 178059)
        v = by_id(evaluate(SITE, READY, AS_OF), "bch.chf.eligibility")["values"]
        self.assertEqual((v["provisional_grant_per_unit_cad"], v["grant_fiscal_year"]), (178059, "2026-27"))
        self.assertEqual(by_id(evaluate(SITE, READY, date(2026, 2, 1)), "bch.chf.eligibility")["values"]["provisional_grant_per_unit_cad"], 171211)
        self.assertNotIn("grant", chf.version_on(AS_OF).params["not_read_from_bc_housing"])

    def test_income_geared_rents_come_from_the_housing_income_limits(self):
        r = self._rule("f.rgi_rents").version_on(AS_OF)
        self.assertEqual(r.params["housing_income_limits_cad"], {"studio": 58000, "one_bed": 58000, "two_bed": 72000, "three_bed_plus": 86000})
        self.assertEqual(r.params["rgi_rent_monthly_cad"]["two_bed"], round(72000 * 0.7 * 0.3 / 12))
        self.assertTrue(r.source["verified"])
        L = evaluate(SITE, READY, AS_OF)
        pf = proforma.build(SITE, READY, L)
        rgi = next(x for x in pf["lines"] if x["key"] == "rev_rgi")
        self.assertEqual((rgi["rule_id"], rgi["placeholder"]), ("f.rgi_rents", False))
        self.assertIn("Housing Income Limit", rgi["note"])
        tiers, n = READY["rent_tiers_units"], sum(READY["units"].values())
        want = sum(c * tiers["rgi"] / n * r.params["rgi_rent_monthly_cad"][k] * 12 for k, c in READY["units"].items())
        self.assertEqual(pf["operating"]["revenue"]["rgi"], round(want))
        deep = sum(c * tiers["deep_subsidy"] / n * r.params["deep_subsidy_rent_monthly_cad"][k] * 12 for k, c in READY["units"].items())
        self.assertEqual(pf["operating"]["revenue"]["deep_subsidy"], round(deep))
        self.assertEqual(next(t for t in pf["operating"]["page"]["tiers"] if t["key"] == "rgi")["from"], "rule")


    def test_a_rent_the_operator_entered_still_stands_over_the_estimate(self):
        o = dict(READY, operations={"rent_rgi_monthly_cad": 900})
        pf = proforma.build(SITE, o, evaluate(SITE, o, AS_OF))
        self.assertEqual(pf["operating"]["revenue"]["rgi"], round(READY["rent_tiers_units"]["rgi"] * 900 * 12))

    def test_the_unit_areas_are_confirmed_and_the_edition_is_archived(self):
        ua = self._rule("bch.design_guidelines.unit_areas")
        now = ua.version_on(date(2026, 11, 23))
        self.assertEqual(now.params["min_net_area_m2"], ua.version_on(AS_OF).params["min_net_area_m2"])
        self.assertEqual((now.params["four_bed_net_area_m2"], now.params["min_wheelchair_accessible_share"]), (112, 0.05))
        self.assertTrue(now.source["verified"])
        row = by_id(evaluate(SITE, READY, date(2026, 11, 23)), "bch.design_guidelines.unit_areas")
        # BC Housing's page gives the 2019 edition as the standard (Kai, 24 Nov 2026): the stamp on the PDF is noted in
        # the source, and the finding raises nothing about it
        self.assertEqual(now.params["edition_status"], "current")
        self.assertNotIn("archived", row["finding"])
        self.assertIn("archived", now.source["verify"])
        self.assertIn("three-bedroom 86, four-bedroom 112 m²", row["finding"])
        self.assertFalse(row.get("action"))
        self.assertNotIn("archived", by_id(evaluate(SITE, READY, date(2026, 10, 23)), "bch.design_guidelines.unit_areas")["finding"])

    def test_a_shelters_beds_are_sized_and_nothing_else_is(self):
        o = dict(READY, housing_type="shelter", beds=60)
        row = by_id(evaluate(SITE, o, AS_OF), "bch.shelter.bed_space")
        self.assertEqual((row["status"], row["values"]["sleeping_area_min_m2"], row["values"]["rooms_min"]), ("info", 276.0, 15))
        self.assertEqual(by_id(evaluate(SITE, dict(o, beds=None), AS_OF), "bch.shelter.bed_space")["status"], "info")
        home = by_id(evaluate(SITE, READY, AS_OF), "bch.shelter.bed_space")
        self.assertEqual(home["status"], "not_applicable")
        self.assertTrue(home["finding"].startswith("Not for this option"))

    def test_the_supportive_housing_fund_says_who_owns_the_building(self):
        o = dict(READY, housing_type="supportive")
        row = by_id(evaluate(SITE, o, AS_OF), "bch.shf.program")
        self.assertIn("The building is owned by the Provincial Rental Housing Corporation", row["finding"])
        self.assertIn("Rents: rent geared to income for every home", row["finding"])
        self.assertIn("rather than by a society's grant application", row["finding"])
        shelter = by_id(evaluate(SITE, dict(READY, housing_type="shelter"), AS_OF), "bch.esp.program")
        self.assertIn("running a shelter, not building one", shelter["finding"])

    def test_every_figure_read_from_a_pdf_names_its_file_and_pages(self):
        for rid in ("bch.chf.eligibility", "bc.bcbuilds.eligibility", "bch.shf.program", "bch.wthf.program", "bch.esp.program", "bch.hearth.program",
                    "f.rgi_rents", "bch.shelter.bed_space"):
            src = self._rule(rid).version_on(date(2026, 11, 23)).source
            self.assertIn("inbox/bc-housing-2026-11-23/", json.dumps(src.get("read_from")), rid)
            self.assertEqual(src.get("read_on"), "2026-11-23", rid)

class ACd1LotAndAKey(unittest.TestCase):
    """24 Nov 2026 (Kai): on a CD-1 site the person can give a key and the by-law's PDF and have the tool read it."""

    UI = Path(__file__).resolve().parent.parent / "ffm" / "ui"

    def test_the_site_card_has_a_place_for_it_only_on_a_cd1_lot_the_rules_do_not_hold(self):
        stage = (self.UI / "route-stage.js").read_text(encoding="utf-8")
        self.assertIn("function cd1Slot(site)", stage)
        self.assertIn('if (!/^CD-1/.test(d)) return "";', stage)
        self.assertIn("${siteFacts(site)}${cd1Slot(site)}", stage)
        self.assertIn("cd1.replaceWith(keepCd1)", stage)             # a chosen PDF survives a re-render of the card

    def test_the_form_is_drawn_once_and_says_the_city_refuses_a_programs_download(self):
        claude = (self.UI / "claude.js").read_text(encoding="utf-8")
        self.assertIn('$("#stage-cd1-slot")', claude)
        self.assertIn('if (schedSlot && onStage) schedSlot.innerHTML = "";', claude)
        self.assertIn("The City's site refuses a program's download", claude)
        self.assertIn("https://cd1-bylaws.vancouver.ca/index.htm", claude)      # a CD-1 with no number is sent to the index
        self.assertEqual(claude.count('id="sched-file"'), 1)

    def test_the_open_item_points_at_it(self):
        site = dict(SITE, zoning_district="CD-1 (999)", cd1_bylaw_number=999)
        item = next(u for u in evaluate(site, READY, AS_OF)["summary"]["answers"]["unsure"] if "CD-1 (999)" in (u.get("title") or u.get("finding") or ""))
        self.assertIn("give a key and the by-law's PDF and have the tool read it", item["action"])

class TheSchedulesKaiSaved(unittest.TestCase):
    """24 Nov 2026: seventeen by-law PDFs Kai saved by hand (inbox/city-2026-11-23/) read into layer A."""

    ON = date(2026, 11, 23)

    def _run(self, district, option=None, **site):
        s = dict(SITE, zoning_district=district, **site)
        s.pop("osm", None)
        return evaluate(s, option or READY, self.ON)

    def test_the_rt_districts_read_have_their_own_figures_and_no_unverified_item(self):
        want = {"RT-4": (0.6, 10.7, 3), "RT-4A": (0.6, 10.7, 3), "RT-5": (0.6, 10.7, 3), "RT-7": (1.0, 11.5, 3), "RT-8": (0.5, 10.7, 2),
                "RT-10": (0.4, 10.7, 2), "RT-11": (0.6, 10.7, 2)}
        for d, (fsr, h, st) in want.items():
            L = self._run(d)
            slug = "cov." + d.lower().replace("-", "").rstrip("a") if d != "RT-4A" else "cov.rt4"
            f, hh = by_id(L, slug + ".outright_fsr"), by_id(L, slug + ".outright_height")
            self.assertEqual((f["source"]["verified"], hh["values"]["max_height_m_outright"], hh["values"]["max_storeys_outright"]), (True, h, st), d)
            self.assertNotIn("coverage.schedule_unverified", open_ids(L), d)

            if d != "RT-7":
                self.assertEqual(f["values"]["max_fsr_outright"], fsr, d)
        from ffm.rules_loader import load_rules, RULES_DIR
        self.assertFalse([r.id for r in load_rules(RULES_DIR) if r.id.startswith("cov.rt.")])      # the from-memory family rule is gone

    def test_rt7_caps_the_homes_and_rt8_has_no_rear_yard_to_test(self):
        self.assertIn("exceed the schedule's 8", by_id(self._run("RT-7"), "cov.rt7.outright_fsr")["finding"])
        yards = by_id(self._run("RT-8"), "cov.rt8.setbacks")
        self.assertNotIn("min_rear_yard_m", {k for k, v in yards["values"].items() if v is not None})

    def test_a_site_takes_its_row_of_a_frontage_table(self):
        small = dict(READY, gfa_m2=600, residential_gfa_m2=600, storeys=3, height_m=9.9)
        wide = by_id(self._run("RM-9A", small, frontage_m=30.0, depth_m=30.0, site_area_m2=900.0), "cov.rm9a.outright_fsr")
        narrow = by_id(self._run("RM-9A", small, frontage_m=14.0, depth_m=40.0, site_area_m2=560.0), "cov.rm9a.outright_fsr")
        self.assertEqual((wide["values"]["max_fsr_outright"], narrow["values"]["max_fsr_outright"]), (2.0, 0.7))
        self.assertEqual(by_id(self._run("RM-9", small, frontage_m=13.0, depth_m=40.0, site_area_m2=520.0), "cov.rm9.outright_fsr")["values"]["max_fsr_outright"], 1.2)
        self.assertEqual(by_id(self._run("RM-9B", small, frontage_m=10.0, depth_m=40.0, site_area_m2=400.0), "cov.rm9b.outright_fsr")["values"]["max_fsr_outright"], 0.7)
        self.assertEqual(by_id(self._run("RM-10", small, frontage_m=41.0, depth_m=30.0, site_area_m2=1230.0), "cov.rm10.outright_fsr")["values"]["max_fsr_outright"], 2.6)
        self.assertEqual(by_id(self._run("RM-11", small, frontage_m=30.0, depth_m=40.0, site_area_m2=1200.0), "cov.rm11.outright_fsr")["values"]["max_fsr_outright"], 0.75)

    def test_rm7_and_rm7a_differ_only_in_the_rear_yard(self):
        a, b = by_id(self._run("RM-7"), "cov.rm7.setbacks"), by_id(self._run("RM-7A"), "cov.rm7a.setbacks")
        self.assertIsNone(a["values"].get("min_rear_yard_m"))
        self.assertEqual(b["values"]["min_rear_yard_m"], 1.8)

    def test_the_oppenheimer_plan_asks_for_the_sub_area_then_reads_it(self):
        L = self._run("DEOD")
        f = by_id(L, "cov.deod.outright_fsr")
        self.assertEqual(f["status"], "uncertain")
        self.assertIn("1 Main/Hastings, 2 Cordova Street", f["finding"])
        self.assertTrue(f["action"].startswith("Manager or architect: find the lot on the plan's sub-area map"))
        one = self._run("DEOD", odp_sub_area="1")
        self.assertEqual(by_id(one, "cov.deod.outright_fsr")["values"]["max_fsr_outright"], 3.0)          # social housing, s.4.5.1
        self.assertEqual(by_id(one, "cov.deod.outright_height")["values"]["max_height_m_outright"], 30.0)
        two = self._run("DEOD", odp_sub_area="2")
        self.assertEqual(by_id(two, "cov.deod.outright_fsr")["status"], "conditional")                   # 1.0, to 11.0 by discretion
        self.assertEqual(by_id(two, "cov.deod.outright_height")["status"], "conditional")                # 15 m, to 100 m by discretion
        three = self._run("DEOD", odp_sub_area="3", in_transit_oriented_area=True)
        self.assertEqual(by_id(three, "cov.deod.outright_height")["values"]["max_height_m_outright"], 30.0)
        four = by_id(self._run("DEOD", odp_sub_area="4"), "cov.deod.outright_height")
        self.assertEqual(four["status"], "conditional")
        self.assertIn("No outright maximum height applies in sub-area 4 (Alexander/Powell)", four["finding"])

    def test_the_suggester_stands_on_every_one_of_them(self):
        from ffm.suggest import suggest
        for d, extra in (("RT-8", {}), ("RM-9A", {}), ("RM-12", {}), ("FM-1", {}), ("DEOD", {}), ("DEOD", {"odp_sub_area": "1"}), ("DEOD", {"odp_sub_area": "4"}), ("M-1", {})):
            s = suggest(_bare(id="x", zoning_district=d, frontage_m=40.0, depth_m=37.0, site_area_m2=1480.0, **extra), ["bch.chf.eligibility"], self.ON, "outright")
            self.assertTrue(s["option"].get("storeys"), d)
        m1 = suggest(_bare(id="x", zoning_district="M-1", frontage_m=40.0, depth_m=37.0, site_area_m2=1480.0), ["bch.chf.eligibility"], self.ON, "outright")
        self.assertIn("industrial district", next(u for u in m1["unsure"] if u["key"] == "use")["why"])
        deod = suggest(_bare(id="x", zoning_district="DEOD", frontage_m=40.0, depth_m=37.0, site_area_m2=1480.0), ["bch.chf.eligibility"], self.ON, "outright")
        self.assertTrue(any(u["key"] == "odp_sub_area" for u in deod["unsure"]))

    def test_every_schedule_read_names_its_file_and_pages(self):
        from ffm.rules_loader import load_rules, RULES_DIR
        read = [r for r in load_rules(RULES_DIR) if "inbox/city-2026-11-23/" in json.dumps(r.version_on(self.ON).source if r.version_on(self.ON) else {})]
        self.assertEqual(len(read), 51)
        for r in read:
            src = r.version_on(self.ON).source
            self.assertTrue(src["verified"] and "page" in src["read_from"], r.id)

class TheSecondPanelsDefects(unittest.TestCase):
    """24 Nov 2026: the defects four simulated reviewers (three architects and an operator) found, re-run and fixed."""

    FIX = Path(__file__).resolve().parent / "fixtures"

    def _pf(self, site, option):
        L = evaluate(site, option, AS_OF)
        return proforma.build(site, option, L, massing.build(site, option, L)), L

    def test_a_short_subsidy_is_never_borrowed_against(self):
        ops = {"support_staffing_cad_year": 1_150_000, "operating_cost_per_unit_year_cad": 9800, "operating_subsidy_cad_year": 1_500_000, "subsidy_confirmed": True}
        o = dict(READY, housing_type="supportive", supportive_units=88, finance={"land_cost_cad": 0, "other_grants_cad": 60_000_000})
        short, _ = self._pf(SITE, dict(o, operations=dict(ops, subsidy_term_years=3)))
        self.assertEqual(short["operating"]["page"]["subsidy_lends"], False)
        self.assertNotEqual(short["verdict"]["word"], "likely")
        self.assertTrue(any("depends on its renewal" in w for w in short["verdict"]["why"]))
        self.assertIn("shorter than the loan's amortization", next(x for x in short["lines"] if x["key"] == "subsidy")["note"])
        unknown, _ = self._pf(SITE, dict(o, operations=ops))                      # no term entered: no loan on it either
        self.assertFalse(unknown["operating"]["page"]["subsidy_lends"])
        long, _ = self._pf(SITE, dict(o, operations=dict(ops, subsidy_term_years=40)))
        self.assertTrue(long["operating"]["page"]["subsidy_lends"])
        self.assertGreater(long["funding"]["debt"]["supportable"], short["funding"]["debt"]["supportable"] or 0)

    def test_supportive_homes_and_shelter_beds_in_a_rental_building_are_seen(self):
        o = dict(READY, supportive_units=25, beds=80)
        pf, L = self._pf(SITE, o)
        page = pf["operating"]["page"]
        self.assertEqual(page["housing_type"], "independent")
        self.assertTrue(page["staffing_missing"])
        self.assertEqual(page["staffed_parts"], {"supportive": 25, "shelter": 80})
        self.assertIsNone(page["subsidy_to_run"])                                # withheld, not printed
        self.assertIn("coverage.funders_parts", open_ids(L))
        self.assertEqual(by_id(L, "bch.shelter.bed_space")["status"], "info")
        self.assertNotEqual(by_id(L, "bch.shf.program")["status"], "not_applicable")
        self.assertIn("not given: the support staffing is not entered", "\n".join(proforma.operating_markdown(pf)))

    def test_a_shelter_counted_in_beds_keeps_the_operators_figures(self):
        o = dict(READY, housing_type="shelter", beds=60, units={k: 0 for k in READY["units"]}, rent_tiers_units=None,
                 operations={"support_staffing_cad_year": 2_400_000, "operating_subsidy_cad_year": 2_900_000, "operating_cost_per_unit_year_cad": 4000})
        pf, _ = self._pf(SITE, o)
        page = pf["operating"]["page"]
        self.assertEqual((page["support_staffing"], page["subsidy"], page["operating_cost"]), (2_400_000, 2_900_000, 240_000))
        self.assertEqual(page["subsidy_to_run_per_bed_month"], round(2_640_000 / 60 / 12))
        self.assertIsNone(page["subsidy_to_run_per_home_month"])
        self.assertNotIn("the unit mix", " ".join(pf["verdict"]["unsure"]))

    def test_no_grant_is_counted_without_rent_tiers_and_no_closed_fund_is_named(self):
        pf, _ = self._pf(SITE, dict(READY, rent_tiers_units=None))
        self.assertEqual(sum(g["value"] for g in pf["funding"]["grants"] if g.get("program") == "bch.chf.eligibility"), 0)
        self.assertIn("rent tiers are not entered", pf["funding"]["not_counted"][0]["why"])
        self.assertNotIn("Affordable Housing Fund", proforma.MORE_SOURCES)
        self.assertNotIn("Affordable Housing Fund", (self.UI / "memo" / "answers.js").read_text(encoding="utf-8").split("export function moneyNext")[1].split("\n}\n")[0])
        grant = next(x for x in self._pf(SITE, READY)[0]["lines"] if x["key"] == "grant_chf")
        self.assertIn("2026-27 provisional rate", grant["note"])

    UI = Path(__file__).resolve().parent.parent / "ffm" / "ui"

    def test_supportive_housing_is_sent_to_its_programs_route_not_to_grants(self):
        o = dict(READY, housing_type="supportive", supportive_units=88, operations={"support_staffing_cad_year": 10_000})
        pf, _ = self._pf(SITE, o)
        self.assertTrue(proforma.next_step(pf).startswith("For supportive housing, the capital comes by the program's own route"))
        self.assertIsNone(pf["operating"]["page"]["if_gap_financed"])

    def test_a_permit_route_over_the_limits_needs_a_rezoning_and_never_prints_none(self):
        o = dict(READY, approval_route="development_permit", rezoning_path="none")
        L = evaluate(SITE, o, AS_OF)
        fsr = by_id(L, "cov.rm1.outright_fsr")
        self.assertEqual(fsr["status"], "fail")
        self.assertNotIn("(none)", fsr["finding"])
        self.assertIn("cannot approve more than the schedule allows", fsr["finding"])
        self.assertEqual(L["summary"]["answers"]["allowed"]["by_rezoning"]["verdict"], "needed")
        self.assertIn("**By rezoning: needed.**", memo.markdown(L))

    def test_a_corner_lot_whose_front_decides_the_density_is_uncertain_and_says_why(self):
        site = load_json(self.FIX / "1130-jervis-st.json")
        o = dict(READY, housing_type="transitional", storeys=6, height_m=18.3, gfa_m2=2200, residential_gfa_m2=2200, non_residential_gfa_m2=0,
                 units={"studio": 0, "one_bed": 12, "two_bed": 12, "three_bed_plus": 0}, approval_route="development_permit", rezoning_path="none")
        r = by_id(evaluate(site, o, AS_OF), "cov.rm5b.outright_fsr")
        self.assertEqual(r["status"], "uncertain")
        self.assertIn("at most 2.0", r["finding"])
        self.assertIn("With Jervis St as the front", r["finding"])
        self.assertTrue(r["action"].startswith("Manager: ask the City which street is the front"))

    def test_a_lot_too_narrow_for_a_home_is_not_allowed_outright(self):
        site = _bare(id="narrow", zoning_district="RM-11", frontage_m=7.6, depth_m=37.2, site_area_m2=282.7)
        o = dict(READY, storeys=4, height_m=13.2, gfa_m2=213, residential_gfa_m2=213, non_residential_gfa_m2=0, units={"studio": 2, "one_bed": 0, "two_bed": 0, "three_bed_plus": 0},
                 setbacks_m={"front": 3.7, "rear": 6.1, "side": 2.1}, rezoning_path=None, approval_route=None)
        L = evaluate(site, o, AS_OF)
        self.assertEqual(by_id(L, "cov.rm11.setbacks")["status"], "uncertain")
        self.assertIn("less than the 5 m a home needs", by_id(L, "cov.rm11.setbacks")["finding"])
        self.assertEqual(L["summary"]["answers"]["allowed"]["outright"]["verdict"], "not yet confirmed")

    def test_a_narrow_rt_lots_side_yard_is_a_share_of_its_width(self):
        from ffm.checks import yard_minimums
        from ffm.rules_loader import load_rules, RULES_DIR
        p = next(r for r in load_rules(RULES_DIR) if r.id == "cov.rt5.setbacks").version_on(AS_OF).params
        self.assertEqual(yard_minimums(_bare(id="x", frontage_m=7.6, depth_m=30.5), p)[0]["side"], 0.76)
        self.assertEqual(yard_minimums(_bare(id="x", frontage_m=20.0, depth_m=30.5), p)[0]["side"], 1.5)

    def test_a_transit_tier_caps_the_derived_density(self):
        from ffm.suggest import suggest
        site = _bare(id="toa", zoning_district="CD-1", frontage_m=40.2, depth_m=32.0, site_area_m2=1287.7, in_transit_oriented_area=True, toa_tier="1")
        o = suggest(site, ["bch.chf.eligibility"], AS_OF, "funder-ready")["option"]
        self.assertLessEqual(round(o["gfa_m2"] / 1287.7, 2), 5.0)

    def test_a_zero_yard_envelope_stays_inside_the_lot(self):
        from ffm import boundary
        ring = [[0, 0], [40, 0], [40, 32], [0, 32]]
        env = boundary.inset(ring, {"front": 0, "rear": 6, "side": 0})
        self.assertIsNotNone(env)
        self.assertAlmostEqual(boundary.area(env), 40 * 26, delta=1)

    def test_a_mass_taller_than_the_height_tested_says_so(self):
        o = dict(READY, storeys=12, height_m=37.0, floor_to_floor_m=3.3)
        m = massing.build(SITE, o, evaluate(SITE, o, AS_OF))
        self.assertTrue(any("above the option's height of 37.0 m" in w for w in m["warnings"]))
        g = dict(READY, ground_floor_height_m=4.5)
        prop = massing.build(SITE, g, evaluate(SITE, g, AS_OF))["masses"][0]
        self.assertEqual(prop["level_z_m"][:3], [0.0, 4.5, 4.5 + READY["floor_to_floor_m"]])

class TheFourFeatures(unittest.TestCase):
    """24 Nov 2026 (Kai): the operator flow, the program brief, ground-oriented and tower building types, the area schedule."""

    UI = Path(__file__).resolve().parent.parent / "ffm" / "ui"

    def _lay(self, site, o):
        L = evaluate(site, o, AS_OF)
        m = massing.build(site, o, L)
        lay = layout.solve(site, o, L, m)
        layout.sheets(lay, site, m, L)          # the drawings stand for every type
        return lay, m, L

    SMALL = None

    def small(self):
        s = dict(SITE, frontage_m=15.2, depth_m=36.6, site_area_m2=556.3)
        for k in ("osm", "parcel", "boundary_m"):
            s.pop(k, None)
        return s

    # ---- the area schedule
    def test_every_layout_carries_an_area_schedule_whose_floors_add_up(self):
        lay, _, _ = self._lay(SITE, READY)
        s = lay["area_schedule"]
        self.assertAlmostEqual(sum(r["gross_m2"] for r in s["floors"]), s["totals"]["gross_m2"], delta=1)
        self.assertEqual(s["totals"]["homes_total"], lay["units_placed"])
        self.assertAlmostEqual(s["totals"]["efficiency"], s["totals"]["m2"]["homes"] / s["totals"]["gross_m2"], places=2)
        csv = layout.area_schedule_csv(s).strip().split("\n")
        self.assertEqual(len(csv), len(s["floors"]) + 2)
        self.assertTrue(csv[0].startswith('"Floor","Homes"'))
        self.assertIn("### Area schedule", "\n".join(layout.markdown(lay)))
        js = (self.UI / "memo" / "operator.js").read_text(encoding="utf-8")
        self.assertIn("export function areaScheduleCsv", js)

    def test_a_plate_mostly_core_and_corridor_is_flagged(self):
        o = dict(READY, housing_type="supportive", supportive_units=60, units={"studio": 60, "one_bed": 0, "two_bed": 0, "three_bed_plus": 0})
        lay, _, _ = self._lay(SITE, o)
        self.assertTrue(lay["area_schedule"]["flag"])
        self.assertTrue(any("net to gross" in w for w in lay["warnings"]))

    # ---- ground-oriented homes
    def test_ground_oriented_homes_have_their_own_doors_and_no_core_corridor_or_lift(self):
        o = dict(READY, building_type="ground_oriented", storeys=3, height_m=10.0, gfa_m2=900, residential_gfa_m2=900, non_residential_gfa_m2=0,
                 units={"studio": 0, "one_bed": 0, "two_bed": 2, "three_bed_plus": 2}, rent_tiers_units=None, accessible_units=0)
        lay, _, _ = self._lay(self.small(), o)
        self.assertEqual(lay["plate"]["arrangement"], "ground_oriented")
        blocks = {z["block"] for fl in lay["floors"] for z in fl["zones"]}
        self.assertFalse(blocks & {"core", "corridor"})
        homes = [z for fl in lay["floors"] for z in fl["zones"] if z.get("home")]
        self.assertEqual(len({z["home"] for z in homes}), lay["units_placed"])
        self.assertTrue(all(z["levels"] == [0, 2] for z in homes))                       # townhouses, three floors
        self.assertEqual(lay["egress"]["status"], "pass")
        self.assertEqual(lay["operability"]["lifts"], 0)
        self.assertEqual(next(c for c in lay["adjacencies"] if c["id"] == "own_entry")["status"], "pass")
        self.assertEqual(lay["area_schedule"]["totals"]["homes_total"], lay["units_placed"])

    def test_over_three_storeys_they_stack_and_the_upper_homes_are_a_placeholder(self):
        o = dict(READY, building_type="ground_oriented", storeys=4, height_m=13.2, gfa_m2=1000, residential_gfa_m2=1000, non_residential_gfa_m2=0,
                 units={"studio": 0, "one_bed": 4, "two_bed": 4, "three_bed_plus": 0}, rent_tiers_units=None)
        lay, _, _ = self._lay(self.small(), o)
        self.assertEqual(lay["plate"]["ground_oriented"]["home_spans"], [2, 2])
        self.assertEqual(lay["plate"]["ground_oriented"]["homes"], "stacked townhouses")
        self.assertEqual(lay["egress"]["status"], "uncertain")
        self.assertIn("Part 9", lay["egress"]["summary"])

    # ---- a tower
    def test_a_tower_is_a_podium_and_a_tower_plate(self):
        o = dict(READY, building_type="tower", podium_storeys=4, storeys=18, height_m=59.4, gfa_m2=4 * 1400 + 14 * 650,
                 units={"studio": 50, "one_bed": 60, "two_bed": 40, "three_bed_plus": 10})
        lay, m, _ = self._lay(SITE, o)
        pm = m["masses"][0]
        self.assertEqual((pm["podium_storeys"], len(pm["tiers"])), (4, 2))
        self.assertAlmostEqual(pm["tower"]["area_m2"], 650, delta=15)
        self.assertEqual(lay["plate"]["arrangement"], "tower")
        self.assertEqual(len(lay["floors"]), 18)
        self.assertFalse(any(z["block"] == "void" for z in lay["floors"][0]["zones"]))
        self.assertTrue(any(z["label"] == "Podium roof" for z in lay["floors"][10]["zones"]))
        self.assertGreaterEqual(lay["operability"]["lifts"], 2)
        self.assertAlmostEqual(pm["gfa_m2"], 4 * pm["plate_area_m2"] + 14 * pm["tower"]["area_m2"], delta=2)

    def test_lifts_follow_the_homes(self):
        self.assertEqual(layout.lifts_needed(40, 3)["lifts"], 0)
        self.assertEqual(layout.lifts_needed(60, 5)["lifts"], 1)
        self.assertEqual(layout.lifts_needed(160, 5)["lifts"], 3)
        self.assertEqual(layout.lifts_needed(60, 12)["lifts"], 2)
        self.assertEqual(layout.lifts_needed(60, 12, ground_oriented=True)["lifts"], 0)

    # ---- the program brief
    def test_supportive_housing_gets_its_default_brief_with_the_desk_by_the_entry(self):
        o = dict(READY, housing_type="supportive", supportive_units=60, units={"studio": 60, "one_bed": 0, "two_bed": 0, "three_bed_plus": 0})
        lay, _, _ = self._lay(SITE, o)
        labels = [b["label"] for b in lay["program"] if b.get("brief")]
        self.assertIn("24/7 front desk", labels)
        self.assertNotIn("amenity", [b["key"] for b in lay["program"]])                  # dining replaces it
        items = {i["key"]: i["status"] for i in lay["operability"]["items"]}
        self.assertEqual((items["desk"], items["staff_office"], items["desk_entry"]), ("pass", "pass", "pass"))

    def test_a_shelter_lays_out_sleeping_rooms_above_the_ground_floor(self):
        o = dict(READY, housing_type="shelter", beds=60, storeys=3, height_m=10.0, gfa_m2=1500, residential_gfa_m2=1500, non_residential_gfa_m2=0,
                 units={k: 0 for k in READY["units"]}, rent_tiers_units=None)
        lay, _, _ = self._lay(SITE, o)
        sleep = [z for fl in lay["floors"] for z in fl["zones"] if z.get("label") == "Sleeping rooms"]
        self.assertTrue(sleep and all(fl["level"] > 0 for fl in lay["floors"] for z in fl["zones"] if z.get("label") == "Sleeping rooms"))
        self.assertAlmostEqual(sum(z["area_m2"] for z in sleep), 15 * 4 * 4.6 * 1.10, delta=2)

    def test_the_operators_own_brief_replaces_the_default(self):
        o = dict(READY, housing_type="supportive", program_brief=[{"label": "Clinic", "area_m2": 120, "where": "ground"}, {"label": "Desk", "area_m2": 10, "next_to": "entry"}])
        labels = [b["label"] for b in layout.blocks(o, evaluate(SITE, o, AS_OF))["blocks"] if b.get("brief")]
        self.assertEqual(labels, ["Clinic", "Desk"])

    def test_the_pages_default_brief_matches_the_engines(self):
        js = (self.UI / "brief.js").read_text(encoding="utf-8")
        for kind, items in layout.BRIEF_DEFAULTS.items():
            for it in items:
                self.assertIn(f'label: "{it["label"]}"', js, (kind, it["label"]))

    def test_supportive_housing_is_derived_as_studios(self):
        from ffm.suggest import suggest
        o = suggest(SITE, ["bch.chf.eligibility"], AS_OF, "funder-ready", fixed={"housing_type": "supportive", "building_type": "apartment"})["option"]
        self.assertEqual((o["units"]["one_bed"], o["units"]["two_bed"], o["units"]["three_bed_plus"]), (0, 0, 0))
        self.assertEqual((o["housing_type"], o["building_type"]), ("supportive", "apartment"))

    # ---- the operator flow
    def test_the_operator_has_a_lane_of_open_items_until_the_figures_are_signed(self):
        o = dict(READY, operator="A housing society", operations={"operating_subsidy_cad_year": 900_000, "rent_rgi_monthly_cad": 850})
        ids = open_ids(evaluate(SITE, o, AS_OF))
        self.assertIn("operator.figures", ids)
        self.assertIn("operator.subsidy", ids)
        item = next(u for u in evaluate(SITE, o, AS_OF)["summary"]["answers"]["unsure"] if u["rule_id"] == "operator.figures")
        self.assertTrue(item["action"].startswith("Operator (A housing society): "))
        signed = dict(o, operations=dict(o["operations"], subsidy_confirmed=True, subsidy_term_years=5, signed={"by": "R. Lee", "org": "A housing society", "on": "2026-11-24"}))
        L2 = evaluate(SITE, signed, AS_OF)
        self.assertNotIn("operator.figures", open_ids(L2))
        self.assertIn("operator.term", open_ids(L2))
        self.assertIn("**Operating figures:** signed by R. Lee of A housing society, 2026-11-24", memo.markdown(L2))
        self.assertNotIn("operator.figures", open_ids(evaluate(SITE, READY, AS_OF)))       # no operator in play

    def test_the_page_has_an_operator_layout_and_lane(self):
        self.assertIn('data-mode="operator"', (self.UI / "index.html").read_text(encoding="utf-8"))
        self.assertIn("operator: {", (self.UI / "modes.js").read_text(encoding="utf-8"))
        self.assertIn('["Operator", "The operator"]', (self.UI / "memo" / "lanes.js").read_text(encoding="utf-8"))
        self.assertIn('"operator"', (self.UI / "server.py").read_text(encoding="utf-8").split("ROLES = ")[1].split("\n")[0])
        self.assertIn("ISSUE_ALSO", (self.UI / "issue.js").read_text(encoding="utf-8"))

class ThePdfCarriesTheAreaScheduleAndTheChecks(unittest.TestCase):
    """24 Nov 2026 (Kai): the paper memo prints the area schedule, the brief and what an operator checks first."""

    def test_the_paper_has_its_own_numbered_section_for_them(self):
        js = (Path(__file__).resolve().parent.parent / "ffm" / "ui" / "paper.js").read_text(encoding="utf-8")
        self.assertIn("function areasPaper(run)", js)
        self.assertIn("areas: lay.area_schedule || lay.operability ? sn() : null", js)
        self.assertIn("Area schedule, and what an operator checks", js)
        self.assertLess(js.index("${s.massing ? `<section"), js.index("${s.areas ? `<section"))     # after the massing, before the words
        self.assertLess(js.index("${s.areas ? `<section"), js.index("${words}"))
        self.assertIn("function signedWords(run)", js)

class TheGapsInWhatWasBuilt(unittest.TestCase):
    """25 Nov 2026: accessible ground-oriented homes, the suggested building type, a multi-floor home in the editor."""

    UI = Path(__file__).resolve().parent.parent / "ffm" / "ui"

    def small(self):
        s = dict(SITE, frontage_m=15.2, depth_m=36.6, site_area_m2=556.3)
        for k in ("osm", "parcel", "boundary_m"):
            s.pop(k, None)
        return s

    GO = dict(READY, building_type="ground_oriented", storeys=3, height_m=10.0, gfa_m2=900, residential_gfa_m2=900, non_residential_gfa_m2=0,
              units={"studio": 0, "one_bed": 2, "two_bed": 2, "three_bed_plus": 0}, rent_tiers_units=None, accessible_units=1)

    def _lay(self, o):
        site = self.small()
        L = evaluate(site, o, AS_OF)
        m = massing.build(site, o, L)
        return layout.solve(site, o, L, m), (site, o, L, m)

    def test_an_accessible_home_is_one_floor_at_grade_with_a_home_over_it(self):
        lay, _ = self._lay(self.GO)
        acc = [z for fl in lay["floors"] for z in fl["zones"] if z.get("accessible")]
        self.assertEqual(len(acc), 1)
        self.assertEqual((acc[0]["levels"], acc[0]["entry"]), ([0, 0], "at grade"))
        over = [z for fl in lay["floors"][1:] for z in fl["zones"] if z.get("home") is not None and z["x"] == acc[0]["x"]]
        self.assertTrue(over and all(z["levels"] == [1, 2] for z in over))
        self.assertEqual(lay["area_schedule"]["totals"]["homes_total"], lay["units_placed"])
        self.assertTrue(any("garden flat under a townhouse" in w for w in lay["warnings"]))
        self.assertEqual(next(i for i in lay["operability"]["items"] if i["key"] == "accessible")["status"], "pass")

    def test_the_editors_placement_reads_a_home_over_several_floors_as_one_home(self):
        lay, (site, o, L, m) = self._lay(self.GO)
        zones = layout.zones_of(lay)
        self.assertTrue(any("home" in z and "levels" in z for z in zones["1"]))
        again = layout.place_zones(site, o, L, m, zones)
        self.assertEqual(again["units_placed"], lay["units_placed"])
        self.assertFalse([g for g in again["geometry"] if g["kind"] in ("no_core", "no_corridor", "no_elevator", "undersized", "narrow")])
        self.assertEqual(again["plate"]["arrangement"], "ground_oriented")
        self.assertTrue(again["egress"].get("ground_oriented"))

    def test_the_suggestion_offers_a_building_type_and_never_applies_it(self):
        from ffm.suggest import suggest, suggest_building_type
        self.assertEqual(suggest_building_type({"storeys": 3, "units": {"two_bed": 4}})[0], "ground_oriented")
        self.assertEqual(suggest_building_type({"storeys": 18, "units": {"studio": 150}})[0], "tower")
        self.assertEqual(suggest_building_type({"storeys": 6, "units": {"studio": 80}})[0], "apartment")
        self.assertEqual(suggest_building_type({"storeys": 3, "units": {"studio": 8}, "housing_type": "shelter"})[0], "apartment")
        s = suggest(SITE, ["bch.chf.eligibility"], AS_OF, "funder-ready")
        self.assertIn(s["building_type_suggested"]["value"], layout.BUILDING_TYPES)
        self.assertNotIn("building_type", s["option"])
        self.assertIsNone(suggest(SITE, ["bch.chf.eligibility"], AS_OF, "funder-ready", fixed={"building_type": "tower"})["building_type_suggested"])

    def test_the_page_offers_the_type_and_keeps_a_home_in_step_across_its_floors(self):
        stage = (self.UI / "route-stage.js").read_text(encoding="utf-8")
        self.assertIn("function typeOffer()", stage)
        self.assertIn("data-use-type", stage)
        ed = (self.UI / "editors" / "blocks.js").read_text(encoding="utf-8")
        self.assertIn("function syncHomes()", ed)
        self.assertIn("home: z.home, levels: [...z.levels]", ed)
        self.assertIn("if (syncHomes())", ed)


if __name__ == "__main__":
    unittest.main()
