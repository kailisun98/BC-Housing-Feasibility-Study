"""The third simulated panel's defects (25 Nov 2026; docs/user-tests-2026-11-25/README.md), each as it was found and
as it reads now. Run: python -m unittest tests.test_panel3_fixes"""

import unittest
from datetime import date
from pathlib import Path

from ffm import layout, lookup, memo, proforma
from ffm.checks import non_residential_m2, operator_of, rezoning_approved_on
from ffm.engine import evaluate, load_json

ROOT = Path(__file__).resolve().parent.parent
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
OPTION = load_json(ROOT / "options" / "998-e-19th-ave-as-approved.json")
AS_OF = date(2026, 10, 23)


def money(option, site=SITE):
    L = evaluate(site, option, AS_OF)
    return L, proforma.build(site, option, L)


def tiers(pf):
    return {t["key"]: t["homes"] for t in pf["operating"]["page"]["tiers"]}


def line(pf, key):
    return next(x for x in pf["lines"] if x["key"] == key)


class RentsFollowTheHousing(unittest.TestCase):
    """#5: 78 supportive studios were priced at market rent; transitional homes were split 2 / 3 / 1."""

    def test_supportive_homes_pay_the_shelter_component(self):
        _, pf = money({**OPTION, "housing_type": "supportive", "units": {"studio": 60, "one_bed": 0, "two_bed": 0, "three_bed_plus": 0}})
        self.assertEqual(tiers(pf), {"market": 0, "rgi": 0, "deep_subsidy": 60})
        self.assertIn("shelter component of income assistance", line(pf, "rev_deep")["note"])

    def test_transitional_homes_are_rent_geared_to_income(self):
        _, pf = money({**OPTION, "housing_type": "transitional", "units": {"studio": 4, "one_bed": 2, "two_bed": 0, "three_bed_plus": 0}})
        self.assertEqual(tiers(pf), {"market": 0, "rgi": 6, "deep_subsidy": 0})
        self.assertIn("rent geared to income, as transitional housing is let", line(pf, "rev_rgi")["note"])

    def test_supportive_homes_beside_independent_ones_leave_the_market_tier(self):
        _, pf = money({**OPTION, "supportive_units": 25})
        t = tiers(pf)
        self.assertEqual(t["deep_subsidy"], 25)
        self.assertEqual(sum(t.values()), 105)


class TheOperatingFigures(unittest.TestCase):
    def test_a_vacancy_typed_as_a_percent_is_read_as_one(self):
        # #6: "2" was read as 200% and signed
        _, pf = money({**OPTION, "operations": {"vacancy_rate": 2}})
        page = pf["operating"]["page"]
        self.assertAlmostEqual(page["vacancy_rate"], 0.02)
        self.assertEqual(page["vacancy_from"], "entered")
        self.assertIn("typed as a percent", line(pf, "vacancy")["note"])
        vac = next(r for r in proforma.operating_rows(pf) if r["label"] == "Vacancy")
        self.assertIn("2.0%, entered", vac["note"])

    def test_no_more_than_half_the_rent_is_taken_for_vacancy(self):
        _, pf = money({**OPTION, "operations": {"vacancy_rate": 0.9}})
        self.assertEqual(pf["operating"]["page"]["vacancy_rate"], 0.5)

    def test_beds_beside_homes_have_a_running_cost_and_a_reserve(self):
        # #7: Glen Drive's 80 shelter beds carried no running cost or reserve
        _, without = money(OPTION)
        _, beds = money({**OPTION, "beds": 80, "operations": {"operating_cost_per_bed_year_cad": 10000}})
        p0, p1 = without["operating"]["page"], beds["operating"]["page"]
        self.assertEqual(p1["operating_cost"] - p0["operating_cost"], 800000)
        self.assertEqual(p1["reserve"] - p0["reserve"], 20 * 600)                  # twenty rooms of four
        self.assertIn("80 beds at $10,000 a bed a year (entered)", line(beds, "opex")["note"])
        row = next(r for r in proforma.operating_rows(beds) if r["label"] == "Operating cost")
        self.assertIn("and 80 beds at $10,000 a bed a year (entered)", row["note"])
        # one figure for the building's places, never the whole need once a home and again a bed
        self.assertIsNone(p1.get("subsidy_to_run_per_home_month"))
        self.assertNotIn("subsidy_to_run_per_bed_month", p1)

    def test_a_named_loan_is_repaid_from_the_same_income(self):
        # #8: a $3M loan was counted as a grant with the full mortgage still sized on the same income
        fin = {**(OPTION.get("finance") or {}), "land_cost_cad": 0}
        _, base = money({**OPTION, "finance": fin})
        loan = {"name": "A lender's loan", "kind": "loan", "amount_cad": 3000000, "status": "applied", "rate_pct": 5, "amortization_years": 25}
        _, with_loan = money({**OPTION, "finance": {**fin, "sources": [loan]}})
        page = with_loan["operating"]["page"]
        self.assertGreater(page["named_loan_service"], 0)
        self.assertEqual(page["named_loan_service"], round(3000000 * proforma.mortgage_constant(5.0, 25)))
        d0, d1 = line(base, "debt")["value"] or 0, line(with_loan, "debt")["value"] or 0
        self.assertLess(d1, d0 or 1)
        self.assertIn("repaid at 5.0% over 25 years", line(with_loan, "source_1")["note"])
        self.assertTrue(any(r["label"] == "Payments on the named loans" for r in proforma.operating_rows(with_loan)))

    def test_the_catalogue_hard_cost_is_a_placeholder(self):
        # #9: a 2- to 4-unit catalogue rate priced 15-storey towers and was missing from the placeholders
        _, pf = money(OPTION)
        self.assertTrue(line(pf, "hard_rate")["placeholder"])
        _, own = money({**OPTION, "finance": {**(OPTION.get("finance") or {}), "hard_cost_per_m2_cad": 5200}})
        self.assertFalse(line(own, "hard_rate")["placeholder"])

    def test_money_never_prints_minus_zero(self):
        self.assertEqual(proforma._money(-0.4), "$0")
        self.assertEqual(proforma._money(-52880), "-$52,880")


class TheDirectorsDiscretion(unittest.TestCase):
    """#4: RT-3's FSR 0.67 was sent to rezoning; s.3.1.1.2 lets the Director allow 1.00 for a non-profit multiple dwelling."""

    SITE = {"address": "609 Heatley Ave", "zoning_district": "RT-3", "site_area_m2": 565.0, "frontage_m": 37.2, "depth_m": 15.2, "municipality": "Vancouver"}
    OPT = {"id": "t", "tenure": "social_housing", "owner_type_at_completion": "non_profit_society", "rezoning_path": None, "storeys": 3, "height_m": 10.0,
           "gfa_m2": 0.67 * 565, "units": {"studio": 0, "one_bed": 2, "two_bed": 2, "three_bed_plus": 0}, "setbacks_m": {"front": 3, "rear": 3, "side": 1.2}}

    def test_the_fsr_is_within_what_the_director_may_allow(self):
        L = evaluate(self.SITE, self.OPT, date(2026, 11, 25))
        r = next(x for x in L["results"] if x["rule_id"] == "cov.rt3.outright_fsr")
        self.assertEqual(r["status"], "conditional")
        self.assertIn("the Director of Planning may increase it to at most 1.0 (s.3.1.1.2", r["finding"])

    def test_a_market_owner_gets_the_conditional_figure_only(self):
        L = evaluate(self.SITE, {**self.OPT, "tenure": "strata", "owner_type_at_completion": "private"}, date(2026, 11, 25))
        r = next(x for x in L["results"] if x["rule_id"] == "cov.rt3.outright_fsr")
        self.assertIn("s.3.1.1.1", r["finding"])


class WhoOperatesAndWhatIsNotHomes(unittest.TestCase):
    def test_the_operator_is_read_from_the_proponent_line(self):
        # #12: the front sheet said "Not named" beside "operator BC Indigenous Housing Society"
        o = load_json(ROOT / "options" / "1010-expo-blvd-as-permitted.json")
        self.assertEqual(operator_of(o), "BC Indigenous Housing Society")
        self.assertEqual(operator_of({"operations": {"signed": {"org": "Atira", "by": "A. Person"}}}), "Atira")
        self.assertEqual(operator_of({"operator": "Lookout", "proponent": "x; operator Other"}), "Lookout")

    def test_the_briefs_community_spaces_are_not_homes(self):
        # #13: a 450 m² hall and 900 m² of offices in the brief were invisible to C-2, BC Builds and the money
        o = {"non_residential_gfa_m2": 100, "program_brief": [{"label": "Hall", "area_m2": 450, "use": "community"},
                                                               {"label": "Offices", "area_m2": 900, "use": "community"},
                                                               {"label": "Lounge", "area_m2": 60}]}
        self.assertEqual(non_residential_m2(o), 1450)
        brief = layout.program_brief(o)
        self.assertEqual([b.get("use") for b in brief if b["label"] in ("Hall", "Offices")], ["community", "community"])


class LiftsAndExits(unittest.TestCase):
    def test_a_shelter_upstairs_needs_an_elevator(self):
        # #10: a six-storey, 80-bed shelter passed as "a walk-up"
        self.assertGreaterEqual(layout.lifts_needed(0, 6, beds=80)["lifts"], 1)
        self.assertGreaterEqual(layout.lifts_needed(0, 3, beds=40)["lifts"], 1)
        self.assertEqual(layout.lifts_needed(0, 1, beds=40)["lifts"], 0)
        self.assertEqual(layout.lifts_needed(4, 3)["lifts"], 0)

    def test_no_home_placed_reads_no_exit(self):
        # #11: "0 of 6 homes fit" beside "Egress … pass"
        e = layout._ground_egress([{"level": 0, "name": "Ground", "zones": []}], [])
        self.assertEqual(e["status"], "uncertain")


class ACornerLotTouchesItsCrossStreet(unittest.TestCase):
    """#14: 4250 Fraser St and 2475 E 5th Ave, both mid-block, were read as corner lots."""

    def way(self, name, pts):
        return {"type": "way", "tags": {"name": name, "highway": "residential"}, "geometry": [{"lon": x, "lat": y} for x, y in pts]}

    def test_the_distance_from_the_lot_to_a_street(self):
        lot = [(-123.1000, 49.2500), (-123.0998, 49.2500), (-123.0998, 49.2502), (-123.1000, 49.2502), (-123.1000, 49.2500)]
        centre = (-123.0999, 49.2501)
        near = self.way("Near St", [(-123.10005, 49.2495), (-123.10005, 49.2510)])     # about 4 m west of the lot
        far = self.way("Far St", [(-123.1010, 49.2495), (-123.1010, 49.2510)])          # about 73 m west
        self.assertLess(lookup.adjoins([near, far], "Near St", lot, centre), lookup.CROSS_FROM_LOT_M)
        self.assertGreater(lookup.adjoins([near, far], "Far St", lot, centre), lookup.CROSS_FROM_LOT_M)
        self.assertIsNone(lookup.adjoins([near], "Gone St", lot, centre))


class ThePlateBoxReachesTheYards(unittest.TestCase):
    """#17: the plate box was 11.5 × 17 m where the yards leave 12.2 × 17.4 (a 0.5 m grid)."""

    def test_a_box_off_the_grid_is_found_whole(self):
        from ffm import boundary
        box = boundary.largest_rect([(0, 0), (12.2, 0), (12.2, 17.4), (0, 17.4)], 0.5)
        self.assertAlmostEqual(box["w"], 12.2, delta=0.01)
        self.assertAlmostEqual(box["d"], 17.4, delta=0.01)

    def test_a_slanted_side_is_never_overhung(self):
        from ffm import boundary
        ring = [(0, 0), (20, 0), (16, 15), (0, 15)]
        box = boundary.largest_rect(ring, 0.5)
        for cx, cy in ((box["x"], box["y"]), (box["x"] + box["w"], box["y"]), (box["x"] + box["w"], box["y"] + box["d"]), (box["x"], box["y"] + box["d"])):
            nudge = (cx - 1e-3 if cx > box["x"] else cx + 1e-3, cy - 1e-3 if cy > box["y"] else cy + 1e-3)
            self.assertTrue(boundary.point_in(nudge, ring), (cx, cy))


class TheSectionCutsTheTower(unittest.TestCase):
    """#11: the section was cut where the podium stood alone; it now passes through every tier (figures/common.js)."""

    def test_the_cut_is_written_through_the_tiers(self):
        src = (ROOT / "ffm" / "ui" / "figures" / "common.js").read_text(encoding="utf-8")
        self.assertIn("cut where every tier stands", src)


class ApprovedAndPermitted(unittest.TestCase):
    """#16: the committed approved and permitted schemes are not asked for a rezoning again."""

    def test_the_date_in_words(self):
        self.assertEqual(rezoning_approved_on({"rezoning_approved_on": "2024-07-25"}), "25 Jul 2024")
        self.assertIsNone(rezoning_approved_on({}))

    def test_expo_goes_by_its_permit(self):
        site = load_json(ROOT / "sites" / "1010-expo-blvd.json")
        o = load_json(ROOT / "options" / "1010-expo-blvd-as-permitted.json")
        L = evaluate(site, o, AS_OF)
        a = L["summary"]["answers"]
        self.assertEqual(a["allowed"]["by_rezoning"]["verdict"], "not needed")
        self.assertNotIn("cov.family_units", [u["rule_id"] for u in a["unsure"]])

    def test_the_front_sheet_counts_the_homes_the_plans_hold(self):
        L = evaluate(SITE, OPTION, AS_OF)
        fs = memo.front_sheet(L, None, {"units_total": 105, "units_placed": 70})
        self.assertIn("70 of the 105 fit the first plans", fs["housed"])


class TheTowerSaysItsParts(unittest.TestCase):
    def test_the_storeys_in_all_then_the_parts(self):
        # #19: "a tower of 18 storeys on a 3-storey podium" read as 21
        from ffm import massing
        site = load_json(ROOT / "sites" / "375-glen-drive.json")
        o = load_json(ROOT / "options" / "375-glen-drive-as-proposed.json")
        o = {**o, "building_type": "tower", "podium_storeys": 3, "storeys": 18}
        L = evaluate(site, o, AS_OF)
        m = massing.build(site, o, L)
        label = next(x["label"] for x in m["masses"] if x.get("podium_storeys"))
        self.assertTrue(label.startswith("Proposed: 18 storeys, a 3-storey podium and a 15-storey tower"), label)


def bare(**kw):
    s = dict(SITE, **kw)
    for k in ("osm", "parcel", "boundary_m", "front_face", "lookup", "context"):
        s.pop(k, None)
    return s


READY = load_json(ROOT / "options" / "998-e-19th-ave-what-if-funder-ready.json")


def go(units, storeys, gfa, h, **kw):
    return dict(READY, building_type="ground_oriented", storeys=storeys, height_m=h, gfa_m2=gfa, residential_gfa_m2=gfa, non_residential_gfa_m2=0,
                units=dict({"studio": 0, "one_bed": 0, "two_bed": 0, "three_bed_plus": 0}, **units), rent_tiers_units=None, accessible_units=0,
                rezoning_path=None, approval_route="development_permit", **kw)


def solve(site, option):
    from ffm import massing
    L = evaluate(site, option, date(2026, 11, 25))
    return layout.solve(site, option, L, massing.build(site, option, L))


class TownhousesInColumns(unittest.TestCase):
    """#10: 3 of 4 homes on 609 Heatley and 2 of 4 on a 10 m lot; every home a full-height townhouse at 4.2 m, and the
    services' 10 m² taking a whole home's slice of every floor."""

    def test_a_ten_metre_lot_takes_its_four_plex(self):
        lay = solve(bare(zoning_district="R1-1", frontage_m=10.1, depth_m=37.2, site_area_m2=375.7),
                    go({"one_bed": 2, "two_bed": 2}, 3, 374, 11.0, setbacks_m={"front": 3.7, "rear": 6.0, "side": 1.2}))
        self.assertEqual(lay["units_placed"], 4)
        self.assertTrue(lay["plate"]["ground_oriented"]["back_to_back"])
        spans = {z["home"]: z["levels"] for fl in lay["floors"] for z in fl["zones"] if z.get("home")}
        self.assertTrue(any(lv[0] > 0 for lv in spans.values()))            # a home over another, by its own stair

    def test_the_services_no_longer_cost_a_home(self):
        lay = solve(bare(frontage_m=15.2, depth_m=36.6, site_area_m2=556.3), go({"two_bed": 2, "three_bed_plus": 2}, 3, 900, 10.0))
        self.assertEqual(lay["units_placed"], 4)
        self.assertTrue(any("shed in the yard" in w for w in lay["warnings"]))

    def test_a_home_left_over_says_how_much_the_homes_need(self):
        lay = solve(bare(zoning_district="RT-3", frontage_m=37.2, depth_m=15.2, site_area_m2=565.0),
                    go({"one_bed": 1, "two_bed": 2, "three_bed_plus": 1}, 3, 340, 10.0, setbacks_m={"front": 3.7, "rear": 3.0, "side": 1.5}))
        self.assertEqual(lay["units_placed"], 3)                   # 320 m² of homes in 340 m² of rows: 94%, not drawn whole
        self.assertTrue(any("homes asked for need 320 m²" in w for w in lay["warnings"]))

    def test_no_home_is_much_larger_than_it_asks_where_another_fits(self):
        lay = solve(bare(frontage_m=15.2, depth_m=36.6, site_area_m2=556.3), go({"one_bed": 4, "two_bed": 4}, 4, 1000, 13.2))
        self.assertEqual(lay["units_placed"], 8)
        self.assertEqual(max(lay["plate"]["ground_oriented"]["home_spans"]), 2)

    def test_the_exits_ask_for_part_9_not_a_core(self):
        lay = solve(bare(zoning_district="R1-1", frontage_m=10.1, depth_m=37.2, site_area_m2=375.7),
                    go({"one_bed": 2, "two_bed": 2}, 3, 374, 11.0, setbacks_m={"front": 3.7, "rear": 6.0, "side": 1.2}))
        items = memo.layout_open_items(lay)
        ex = next(i for i in items if i["title"].startswith("Exits"))
        self.assertIn("Part 9", ex["action"])
        self.assertNotIn("core", ex["action"].lower().replace("no common corridor", ""))
        js = (ROOT / "ffm" / "ui" / "memo" / "answers.js").read_text(encoding="utf-8")
        self.assertIn("Exits: the upper homes' own stairs (BC Building Code, Part 9)", js)


class FloorAreaTestedAgainstDrawn(unittest.TestCase):
    """#17: 340 m² tested beside 307 m² drawn, with nothing said."""

    def test_the_gap_is_an_open_item(self):
        lay = {"units_total": 4, "units_placed": 4, "shortfall": [], "floors": [{}] * 3, "totals": {"gfa_tested_m2": 340, "plates_m2": 340, "void_m2": 33},
               "area_schedule": {"totals": {"gross_m2": 307}}}
        it = next(i for i in memo.layout_open_items(lay) if i["title"] == "Floor area drawn under the floor area tested")
        self.assertIn("the rules test 340 m²", it["action"])
        self.assertIn("first plans draw 307 m²", it["action"])
        self.assertIn("33 m² of the plates is open", it["action"])
        lay["area_schedule"]["totals"]["gross_m2"] = 335
        self.assertFalse([i for i in memo.layout_open_items(lay) if i["title"].startswith("Floor area drawn")])
        js = (ROOT / "ffm" / "ui" / "memo" / "answers.js").read_text(encoding="utf-8")
        self.assertIn('"Floor area drawn under the floor area tested"', js)


class NoRezoningToBuildLess(unittest.TestCase):
    """The C-2A benchmark: FSR 3.0 by rezoning, offered first, where 3.50 is allowed outright."""

    def test_the_benchmark_is_not_offered_below_the_outright_limits(self):
        from ffm import suggest
        s = {"id": "t", "address": "a C-2A lot", "municipality": "Vancouver", "zoning_district": "C-2A", "site_area_m2": 599.7, "frontage_m": 18.3,
             "depth_m": 32.8, "in_former_community_vision_area": True}
        r = suggest.suggest(s, ["bch.chf.eligibility"], date(2026, 11, 25), "funder-ready")
        bm = next(c for c in r["candidates"] if c["id"] == "benchmark")
        self.assertFalse(bm["available"])
        self.assertIn("would build less", bm["why"])
        self.assertFalse(r["option"].get("rezoning_path"))
        self.assertEqual(r["option"]["gfa_m2"], 2099.0)                    # FSR 3.50 outright, not the benchmark's 1,799 m²

    def test_the_band_is_drawn_only_for_a_rezoning(self):
        from ffm import massing
        L = evaluate(SITE, OPTION, AS_OF)
        self.assertIsNotNone(massing.build(SITE, OPTION, L)["policy_benchmark"])
        o = {**OPTION, "rezoning_path": None, "rezoning_approved_on": None, "approval_route": "development_permit"}
        self.assertIsNone(massing.build(SITE, o, evaluate(SITE, o, AS_OF))["policy_benchmark"])


class TheCrossStreetRunsAlongTheLot(unittest.TestCase):
    """1290 Burrard St was offered Burnaby St, across Burrard, while its short end is on Drake St."""

    def way(self, name, pts):
        return {"type": "way", "tags": {"name": name, "highway": "secondary"}, "geometry": [{"lon": x, "lat": y} for x, y in pts]}

    def test_every_candidate_is_kept_and_the_nearest_is_offered(self):
        front = self.way("Main Rd", [(-123.1010, 49.25002), (-123.0990, 49.25002)])
        near = self.way("Far St", [(-123.10002, 49.2490), (-123.10002, 49.2510)])
        nearer = self.way("Near St", [(-123.09995, 49.2495), (-123.09995, 49.2505)])
        out = lookup.street_bearing([front, near, nearer], (49.2501, -123.0999), "Main Rd")
        self.assertEqual([c["name"] for c in out["cross_streets"]], ["Near St", "Far St"])
        self.assertEqual(out["cross_street"]["name"], "Near St")


class SmallerWords(unittest.TestCase):
    def test_a_fetched_date_is_vancouvers_day(self):
        js = (ROOT / "ffm" / "ui" / "figures" / "common.js").read_text(encoding="utf-8")
        self.assertIn('timeZone: "America/Vancouver"', js)
        self.assertIn("fetched: fetchedOn(o.fetched_at)", js)

    def test_a_rule_that_does_not_apply_says_why_in_a_comparison(self):
        js = (ROOT / "ffm" / "ui" / "memo" / "clauses.js").read_text(encoding="utf-8")
        self.assertIn('if (r.status === "not_applicable") return { proposed: r.finding', js)

    def test_the_site_promises_no_two_pages(self):
        for page in ("home.html", "how.html", "who.html"):
            self.assertNotIn("two pages", (ROOT / "ffm" / "ui" / page).read_text(encoding="utf-8").lower(), page)


if __name__ == "__main__":
    unittest.main()
