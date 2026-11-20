"""The pro-forma: arithmetic over layer F and layer E, every line with its source; the real case is 'likely' with
its grant and nominal land, a private site without a price is 'unsure', a thin funding stack is 'unlikely'; the
same inputs give the same numbers; the memo carries the section."""

import copy
import json
import unittest
from datetime import date
from pathlib import Path

from ffm import memo, proforma
from ffm.engine import evaluate, load_json

ROOT = Path(__file__).resolve().parent.parent
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
OPTION = load_json(ROOT / "options" / "998-e-19th-ave-what-if-funder-ready.json")
AS_OF = date(2026, 11, 3)


class LayerF(unittest.TestCase):
    def test_the_assumptions_are_in_the_ledger_as_information(self):
        L = evaluate(SITE, OPTION, AS_OF)
        F = [r for r in L["results"] if r["layer"] == "F"]
        self.assertEqual(len(F), 7)
        self.assertTrue(all(r["status"] == "info" for r in F))
        hc = next(r for r in F if r["rule_id"] == "f.hard_cost_base")
        self.assertEqual(hc["values"]["value_per_m2_cad"], 4693)
        self.assertIn("Class D", hc["finding"])
        self.assertNotIn("observations", next(r for r in F if r["rule_id"] == "f.escalation_bcpi")["values"])

    def test_placeholders_say_so_in_their_source(self):
        L = evaluate(SITE, OPTION, AS_OF)
        src = {r["rule_id"]: r["source"] for r in L["results"] if r["layer"] == "F"}
        self.assertTrue(src["f.soft_costs"].get("placeholder"))
        self.assertTrue(src["f.operating"].get("placeholder"))
        self.assertFalse(src["f.hard_cost_base"].get("placeholder"))


class RealCase(unittest.TestCase):
    def setUp(self):
        self.L = evaluate(SITE, OPTION, AS_OF)
        self.pf = proforma.build(SITE, OPTION, self.L)

    def test_an_earlier_run_date_uses_the_index_published_by_then(self):
        L = evaluate(SITE, OPTION, date(2026, 10, 23))
        pf = proforma.build(SITE, OPTION, L)
        self.assertAlmostEqual(pf["capital"]["escalation"], round(109.2 / 106.1, 4))   # the third quarter's index came out on 29 Oct; on 23 Oct the second quarter's is the latest published
        early = proforma.build(SITE, OPTION, evaluate(SITE, OPTION, date(2026, 5, 1)))
        self.assertFalse(early["available"])   # the mortgage and placeholder versions are not in force that early: said, not guessed

    def test_capital_cost_is_hard_escalated_plus_soft_contingency_and_nominal_land(self):
        c = self.pf["capital"]
        self.assertAlmostEqual(c["escalation"], round(109.4 / 106.1, 4))
        self.assertEqual(c["hard"], round(OPTION["gfa_m2"] * 4693 * c["escalation"]))
        self.assertEqual(c["soft"], round(c["hard"] * 0.25))
        self.assertEqual(c["contingency"], round(c["hard"] * 0.10))
        self.assertEqual(c["land"], 0)   # a church owner on a long lease
        self.assertEqual(c["total"], c["hard"] + c["soft"] + c["contingency"])

    def test_revenue_follows_the_tiers_and_the_debt_the_coverage_ratio(self):
        o, f = self.pf["operating"], self.pf["funding"]
        self.assertGreater(o["revenue"]["market"], 0)
        self.assertGreater(o["revenue"]["rgi"], 0)
        self.assertGreater(o["revenue"]["deep_subsidy"], 0)
        self.assertEqual(o["noi"], o["gross"] - o["vacancy"] - o["operating_cost"] - o["reserve"])
        k = proforma.mortgage_constant(6.19, 40)
        self.assertEqual(f["debt"]["supportable"], round(o["noi"] / 1.10 / k))
        self.assertEqual(f["grants"][0]["program"], "bch.chf.eligibility")
        n = sum(OPTION["units"].values())
        self.assertEqual(f["grants"][0]["value"], 171211 * n)

    def test_every_line_names_its_source_or_the_option(self):
        for ln in self.pf["lines"]:
            self.assertIn("note", ln)
            self.assertTrue(ln["rule_id"] or ln["note"], ln["key"])
        rules = {ln["rule_id"] for ln in self.pf["lines"] if ln["rule_id"]}
        self.assertTrue({"f.hard_cost_base", "f.escalation_bcpi", "f.rents", "f.mortgage", "bch.chf.eligibility"} <= rules)
        self.assertTrue(any(ln["placeholder"] for ln in self.pf["lines"]))

    def test_the_verdict_is_a_word_with_reasons(self):
        v = self.pf["verdict"]
        self.assertIn(v["word"], ("likely", "unlikely", "unsure"))
        self.assertTrue(v["why"])
        self.assertEqual(self.pf["gap"]["value"], self.pf["capital"]["total"] - self.pf["funding"]["total"])

    def test_deterministic(self):
        again = proforma.build(copy.deepcopy(SITE), copy.deepcopy(OPTION), evaluate(SITE, OPTION, AS_OF))
        self.assertEqual(json.dumps(again, sort_keys=True), json.dumps(self.pf, sort_keys=True))


class Verdicts(unittest.TestCase):
    def test_a_private_site_without_a_price_is_unsure_on_land(self):
        # a gap inside the line before any land price: the land decides it
        site = dict(SITE, owner_type="private", owner="a numbered company")
        opt = dict(OPTION, finance={"equity_cad": 18_000_000})
        pf = proforma.build(site, opt, evaluate(site, opt, AS_OF))
        self.assertIsNone(pf["capital"]["land"])
        self.assertLessEqual(pf["gap"]["share_of_capital"], proforma.GAP_UNLIKELY_SHARE)
        self.assertEqual(pf["verdict"]["word"], "unsure")
        self.assertTrue(pf["verdict"]["why"][0].startswith("the land cost is not settled: before any land price the gap is $"), pf["verdict"]["why"][0])
        self.assertTrue(any("land" in u for u in pf["verdict"]["unsure"]))

    def test_a_gap_past_the_line_before_any_land_price_needs_more_sources(self):
        # 20 Nov 2026: a 44% gap read "unsure: the land cost is not settled"; a land price can only widen it
        site = dict(SITE, owner_type="private", owner="a numbered company")
        pf = proforma.build(site, OPTION, evaluate(site, OPTION, AS_OF))
        self.assertIsNone(pf["capital"]["land"])
        self.assertGreater(pf["gap"]["share_of_capital"], proforma.GAP_UNLIKELY_SHARE)
        self.assertEqual(pf["verdict"]["word"], "unlikely")
        why = pf["verdict"]["why"][0]
        self.assertRegex(why, r"^the gap is \$[\d,]+, \d+% of the cost before any land price, more than the 15% line \(this tool's screening line, not a funder's rule\)")
        self.assertTrue(any("land" in u for u in pf["verdict"]["unsure"]))       # still left to a person
        self.assertEqual(proforma.next_step(pf), proforma.MORE_SOURCES)
        self.assertIn("**Needs more sources.**", "\n".join(proforma.markdown(pf)))
        cap = next(ln for ln in pf["lines"] if ln["key"] == "capital")
        self.assertIn("before land", cap["note"])

    def test_the_line_notes_say_what_they_mean(self):
        L = evaluate(SITE, OPTION, AS_OF)
        lines = {ln["key"]: ln for ln in proforma.build(SITE, OPTION, L)["lines"]}
        land_ref = proforma._refs(L)["f.land"]
        self.assertEqual(land_ref[0], "F")
        self.assertEqual(lines["land"]["note"], f"nominal: the owner is a church, and this screen carries the land of a church, a society or a government at $0 on a long lease or a transfer ({land_ref})")
        self.assertIn("this tool's screening line, not a funder's rule", lines["gap"]["note"])
        self.assertIn("the lender wants net income 1.10 times the loan payment", lines["debt"]["note"])
        self.assertIn("repaid over 40 years (the amortization)", lines["debt"]["note"])

    def test_a_price_in_the_finance_block_settles_the_land(self):
        site = dict(SITE, owner_type="private")
        opt = dict(OPTION, finance={"land_cost_cad": 4_000_000, "equity_cad": 500_000})
        pf = proforma.build(site, opt, evaluate(site, opt, AS_OF))
        self.assertEqual(pf["capital"]["land"], 4_000_000)
        self.assertEqual(pf["funding"]["equity"], 500_000)
        self.assertNotIn("unsure", [u[:6] for u in pf["verdict"]["unsure"] if "land" in u])

    def test_no_grant_and_market_only_reads_unlikely_or_likely_by_the_gap(self):
        opt = dict(OPTION, target_programs=["bc.bcbuilds.eligibility"], rent_tiers_units=None)
        pf = proforma.build(SITE, opt, evaluate(SITE, opt, AS_OF))
        self.assertEqual(pf["funding"]["grants"], [])
        self.assertIn(pf["verdict"]["word"], ("unlikely", "likely", "unsure"))
        if pf["gap"]["value"] > pf["capital"]["total"] * proforma.GAP_UNLIKELY_SHARE:
            self.assertEqual(pf["verdict"]["word"], "unlikely")

    def test_no_homes_entered_is_unsure_on_the_unit_mix_not_a_gap(self):
        # 17 Nov 2026: Expo as permitted, floor area but no unit mix, read a 100% gap as "unlikely"
        opt = dict(OPTION, units={"studio": None, "one_bed": None, "two_bed": None, "three_bed_plus": None}, rent_tiers_units=None)
        pf = proforma.build(SITE, opt, evaluate(SITE, opt, AS_OF))
        self.assertIsNotNone(pf["capital"]["total"])
        self.assertEqual(pf["verdict"]["word"], "unsure")
        self.assertIn("no homes entered", pf["verdict"]["why"][0])
        self.assertTrue(pf["verdict"]["unsure"][0].startswith("the unit mix"))
        self.assertIsNone(proforma.next_step(pf))   # no "look for more sources" for a building with no homes

    def test_no_floor_area_is_unsure(self):
        opt = dict(OPTION, gfa_m2=None, units={"studio": None, "one_bed": None, "two_bed": None, "three_bed_plus": None})
        pf = proforma.build(SITE, opt, evaluate(SITE, opt, AS_OF))
        self.assertIsNone(pf["capital"]["total"])
        self.assertEqual(pf["verdict"]["word"], "unsure")


class InTheMemo(unittest.TestCase):
    def test_the_memo_carries_the_section_and_its_sources(self):
        L = evaluate(SITE, OPTION, AS_OF)
        pf = proforma.build(SITE, OPTION, L)
        md = memo.markdown(L, None, None, proforma=pf)
        self.assertIn("## 4. Does the money work?", md)
        self.assertIn("f.hard_cost_base", md)
        self.assertIn("(placeholder)", md)
        self.assertIn("Statistics Canada", md)   # the source list carries layer F
        html = memo.html_page(md)
        self.assertIn("Does the money work", html)


class Wording(unittest.TestCase):
    """17 Nov 2026: a gap past the screen's line reads "Needs more sources" with a next step for the development
    manager, never "Unlikely"; the key in proforma.json stays "unlikely"."""

    def _md(self, pf):
        return "\n".join(proforma.markdown(pf))

    def test_a_wide_gap_asks_the_manager_for_more_sources(self):
        L = evaluate(SITE, OPTION, AS_OF)
        pf = proforma.build(SITE, OPTION, L)
        self.assertEqual(pf["verdict"]["word"], "unlikely")   # the real funder-ready what-if: a gap past 15%
        md = self._md(pf)
        self.assertIn("**Needs more sources.**", md)
        self.assertIn("**For the development manager:** Look for more sources as well", md)
        self.assertNotIn("Unlikely", md)
        self.assertEqual(proforma.next_step(pf), proforma.MORE_SOURCES)

    def test_a_narrow_gap_names_another_source_and_a_missing_figure_names_nothing(self):
        pf = {"verdict": {"word": "unsure"}, "gap": {"value": 1_000_000}, "capital": {"total": 20_000_000, "land": 0}, "inputs": {"units_total": 60}}
        self.assertEqual(proforma.next_step(pf), proforma.CLOSE_GAP)
        self.assertIsNone(proforma.next_step(dict(pf, inputs={"units_total": 0})))   # no homes: the unit mix is the open item
        no_land = {"verdict": {"word": "unsure"}, "gap": {"value": 1_000_000}, "capital": {"total": 20_000_000, "land": None}}
        self.assertIsNone(proforma.next_step(no_land))
        covered = {"verdict": {"word": "likely"}, "gap": {"value": -5}, "capital": {"total": 20_000_000, "land": 0}}
        self.assertIsNone(proforma.next_step(covered))
        self.assertEqual(set(proforma.VERDICT_WORDS), {"likely", "unlikely", "unsure"})


if __name__ == "__main__":
    unittest.main()
