"""Piece 1 of the plan (25 Nov 2026): the memo as an ask. Three verdicts in answer 1, capital sources with a status and
the land owner's contribution, a front sheet shaped as an ask, a short memo, and Sources limited to the rules that apply."""

import copy
import tempfile
import unittest
from datetime import date
from pathlib import Path

from ffm import memo, proforma
from ffm.engine import evaluate, load_json, routes

ROOT = Path(__file__).resolve().parent.parent
AS_OF = date(2026, 10, 23)
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
READY = load_json(ROOT / "options" / "998-e-19th-ave-what-if-funder-ready.json")
APPROVED = load_json(ROOT / "options" / "998-e-19th-ave-as-approved.json")


def run(site=SITE, option=READY):
    L = evaluate(site, option, AS_OF)
    return L, proforma.build(site, option, L)


class ThreeVerdicts(unittest.TestCase):
    def test_the_routes_are_in_answer_1(self):
        L, _ = run()
        r = L["summary"]["answers"]["allowed"]["routes"]
        self.assertEqual(list(r), ["outright", "discretion", "rezoning"])
        self.assertEqual(r["outright"]["verdict"], "no")
        self.assertEqual(r["discretion"]["verdict"], "none in the schedule")   # RM-1 gives the Director nothing to reach 2.49
        self.assertEqual(r["rezoning"]["verdict"], L["summary"]["answers"]["allowed"]["by_rezoning"]["verdict"])

    def test_the_directors_discretion_is_not_outright(self):
        # RM-4 for 100% social housing: FSR 3.00 outright, height 10.7 m with the Director's variance to 19.9 m
        site = dict(SITE, zoning_district="RM-4")
        opt = dict(READY, storeys=4, height_m=15.0, gfa_m2=round(SITE["site_area_m2"] * 1.4))
        L, _ = run(site, opt)
        a = L["summary"]["answers"]["allowed"]
        self.assertEqual(a["outright"]["verdict"], "yes, with conditions")    # the key is unchanged
        self.assertEqual(a["routes"]["outright"]["verdict"], "no")
        self.assertEqual(a["routes"]["discretion"]["verdict"], "possible")
        self.assertTrue(a["routes"]["discretion"]["rules"])

    def test_within_the_limits_discretion_is_not_needed(self):
        out = routes({"outright": {"verdict": "yes"}, "by_rezoning": {"verdict": "not needed", "why": "x"}},
                     [{"rule_id": "a", "status": "pass", "values": {}}])
        self.assertEqual(out["discretion"]["verdict"], "not needed")
        self.assertEqual(out["outright"]["verdict"], "yes")


class CapitalSources(unittest.TestCase):
    def with_sources(self, *sources, **fin):
        o = copy.deepcopy(READY)
        o["finance"] = dict(o.get("finance") or {}, sources=list(sources), **fin)
        return run(option=o)[1]

    def test_named_sources_are_counted_with_their_status(self):
        base = run()[1]
        pf = self.with_sources({"name": "City CHIP grant", "kind": "grant", "amount_cad": 2_000_000, "status": "applied"},
                               {"name": "Society reserves", "kind": "equity", "amount_cad": 500_000, "status": "committed"})
        self.assertEqual(pf["funding"]["total"], base["funding"]["total"] + 2_500_000)
        rows = {r["label"]: r for r in pf["funding"]["sources"]}
        self.assertEqual(rows["City CHIP grant"]["status"], "applied")
        self.assertEqual(rows["Society reserves"]["status"], "committed")
        self.assertEqual(rows["Community Housing Fund grant"]["status"], "illustrative")
        self.assertEqual(rows["Still to find"]["value"], pf["gap"]["value"])
        self.assertEqual(pf["funding"]["uncommitted"], 2_000_000)

    def test_a_stack_closed_only_by_sources_not_committed_is_not_likely(self):
        gap = run()[1]["gap"]["value"]
        pf = self.with_sources({"name": "A foundation", "kind": "grant", "amount_cad": gap + 1_000_000, "status": "assumed"})
        self.assertEqual(pf["verdict"]["word"], "unsure")
        self.assertIn("not yet committed", " ".join(pf["verdict"]["why"]))

    def test_committed_sources_that_close_it_read_likely_unless_the_grant_is_illustrative(self):
        gap = run()[1]["gap"]["value"]
        chf = next(g["value"] for g in run()[1]["funding"]["grants"] if g["program"] == "bch.chf.eligibility")
        pf = self.with_sources({"name": "A foundation", "kind": "grant", "amount_cad": gap + chf + 1, "status": "committed"})
        self.assertEqual(pf["verdict"]["word"], "likely")

    def test_the_land_owners_contribution_is_in_kind(self):
        pf = self.with_sources(land_cost_cad=1, land_value_cad=6_000_000)
        rows = {r["label"]: r for r in pf["funding"]["sources"]}
        self.assertEqual(rows["The land owner's contribution"]["value"], 5_999_999)
        self.assertFalse(rows["The land owner's contribution"]["counted"])
        self.assertEqual(pf["funding"]["land_contribution"], 5_999_999)

    def test_a_bad_row_is_skipped_and_an_unknown_status_is_assumed(self):
        rows = proforma.named_sources({"sources": [{"name": "x", "amount_cad": "n/a"}, {"amount_cad": 10, "status": "promised", "kind": "gift"}]})
        self.assertEqual(rows, [{"name": "A source not named", "kind": "other", "amount": 10, "status": "assumed"}])


class TheFrontSheet(unittest.TestCase):
    def test_it_says_who_what_how_much_and_the_top_three(self):
        o = dict(READY, operator="Example Housing Society", decision_sought="Approve pre-development spending to a rezoning application")
        L, pf = run(option=o)
        fs = memo.front_sheet(L, pf)
        self.assertIn("88 homes", fs["housed"])
        self.assertIn("rent geared to income", fs["housed"])
        self.assertTrue(fs["operator"].startswith("Example Housing Society"))
        self.assertIn("Community Housing Fund", fs["programs"])
        self.assertEqual(fs["money"]["capital"], pf["capital"]["total"])
        self.assertEqual(fs["money"]["to_find"], pf["gap"]["value"])
        self.assertEqual(fs["decision"], o["decision_sought"])
        self.assertLessEqual(len(fs["open_items"]), 3)
        self.assertEqual([v["label"] for v in fs["verdicts"][:3]], ["Outright", "By the Director's discretion", "By rezoning"])

    def test_the_top_items_lead_with_a_fail(self):
        L, pf = run(option=APPROVED)
        items = L["summary"]["answers"]["unsure"]
        fs = memo.front_sheet(L, pf)
        if any(u["status"] == "fail" for u in items):
            self.assertEqual(fs["open_items"][0]["status"], "fail")
        self.assertEqual(fs["open_total"], len(items))

    def test_it_heads_the_memo(self):
        L, pf = run()
        md = memo.markdown(L, proforma=pf)
        self.assertLess(md.index("## The ask"), md.index("## 1. Is it allowed?"))
        self.assertIn("By the Director's discretion", md)
        self.assertIn("Where the money comes from", md)


class ShortMemoAndSources(unittest.TestCase):
    def test_the_short_memo_leaves_out_the_long_parts(self):
        L, pf = run()
        full, short = memo.markdown(L, proforma=pf), memo.markdown(L, proforma=pf, short=True)
        self.assertLess(len(short), len(full) / 2)
        self.assertNotIn("## Full ledger", short)
        self.assertIn("## The ask", short)
        self.assertIn("## Sources", short)

    def test_written_beside_every_run(self):
        L, pf = run()
        with tempfile.TemporaryDirectory() as d:
            memo.write(L, Path(d), proforma=pf)
            self.assertTrue((Path(d) / "memo-short.md").exists())

    def test_sources_are_the_rules_that_apply(self):
        L, pf = run()
        md = memo.markdown(L, proforma=pf)
        sources = md.split("## Sources", 1)[1].split("## Version stamp", 1)[0]
        # the RT-4 schedule is in the stack but not this RM-1 site's
        self.assertNotIn("RT-4", sources)


class ThePage(unittest.TestCase):
    UI = ROOT / "ffm" / "ui"

    def read(self, name):
        return (self.UI / name).read_text(encoding="utf-8")

    def test_the_front_sheet_is_a_twin_and_leads_the_memo(self):
        front = self.read("memo/front.js")
        for word in ("Who is housed", "Who operates", "Which program", "The amount", "The decision wanted"):
            self.assertIn(word, front)
        # (26 Nov 2026) the ask leads the Answers tab's grid, beside the answers where the tab is wide
        self.assertIn('<div class="answers-grid">${frontHtml(run)}<div class="answers">', self.read("memo/memo.js"))
        self.assertIn('["ask", ".memo-ask", "The ask"]', self.read("memo/memo.js"))

    def test_the_contribution_words_match(self):
        js = self.read("memo/answers.js")
        for status, word in proforma.CONTRIBUTION_STATUS_WORDS.items():
            self.assertIn(f'"{word}"', js, status)

    def test_the_paper_has_the_ask_and_a_short_version(self):
        js = self.read("paper.js")
        self.assertIn("export function paperDocument(run, { short = false, board = false, decision = null } = {})", js)
        self.assertIn("${askPaper}", js)
        self.assertIn("exportPdf(true)", self.read("main.js"))

    def test_the_board_memo_is_its_own_two_pages(self):
        # 26 Nov 2026: a two-page board memo beside the short and the full one; the decision first, the sources it cites
        js = self.read("paper.js")
        self.assertIn("The decision wanted</h2>", js)
        self.assertIn("Sources for these pages", js)
        self.assertIn('exportPdf("board"', self.read("main.js"))
        self.assertIn('id="pdf-board-btn"', self.read("index.html"))

    def test_stop_03_asks_for_the_sources_and_the_decision(self):
        js = self.read("route-stage.js")
        self.assertIn("function sourcesEditor(fin)", js)
        self.assertIn('data-key="decision_sought"', js)
        kinds = [k for k in proforma.SOURCE_KINDS]
        for k in kinds:
            self.assertIn(f'["{k}",', js)


if __name__ == "__main__":
    unittest.main()
