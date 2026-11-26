"""The memo in tabs, Issue in the top bar, and stop 02 laid out again (26 Nov 2026, Kai: "too much scrolling... create
tabs which allow the architect to switch from the answers, the drawings/schedule, clauses, ledger, inputs... Issue
button should also be more visible on top", laid out by a UX designer's brief the same day).

The page has no build step and no browser in the test run, so these read the modules' text: the parts the memo is drawn
in, the tab ids each panel carries, the pieces that were retired, and where Issue lives. The behaviour (the WAI-ARIA
keys, the sticky strip, the widths at 1366 and 2000 px) was checked in the browser; the user-tests README says how."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ffm" / "ui"


def read(name):
    return (UI / name).read_text(encoding="utf-8")


def tab_ids():
    js = read("memo/tabs.js")
    block = js[js.index("export const TABS"):js.index("];", js.index("export const TABS"))]
    return re.findall(r'id: "([a-z]+)"', block)


class TheTabs(unittest.TestCase):
    def test_the_tabs_in_order(self):
        self.assertEqual(tab_ids(), ["operating", "answers", "comparison", "drawings", "clauses", "ledger", "inputs"])

    def test_every_panel_the_memo_draws_is_a_tab(self):
        memo = read("memo/memo.js")
        drawn = re.findall(r'class="memo-panel" id="panel-([a-z]+)" data-tab="([a-z]+)"', memo)
        self.assertTrue(drawn)
        for pid, tab in drawn:
            self.assertEqual(pid, tab)
            self.assertIn(tab, tab_ids())
        self.assertEqual({t for _, t in drawn}, set(tab_ids()))

    def test_the_tablist_follows_the_title_block(self):
        memo = read("memo/memo.js")
        self.assertIn('class="memo-tabs" id="memo-tabs" role="tablist"', memo)
        self.assertIn("renderTabs(memoEl", memo)
        self.assertLess(memo.index('class="card memo-head"'), memo.index('id="memo-tabs"'))
        self.assertLess(memo.index('id="memo-tabs"'), memo.index('class="memo-panels"'))

    def test_the_wai_aria_pattern(self):
        js = read("memo/tabs.js")
        for piece in ('role="tab"', "aria-selected", "aria-controls", '"tabpanel"', "aria-labelledby",
                      "ArrowRight", "ArrowLeft", "Home", "End", '"until-found"', "beforematch", "replaceState"):
            self.assertIn(piece, js, piece)

    def test_the_default_tab_is_the_operators_figures_or_the_answers(self):
        js = read("memo/tabs.js")
        self.assertIn('state.mode === "operator" ? "operating" : "answers"', js)
        self.assertIn('state.mode !== "reader"', js)   # the Reader keeps the long page

    def test_a_jump_selects_the_panel_it_points_into(self):
        memo = read("memo/memo.js")
        self.assertIn("const tab = tabOf(t);", memo)
        self.assertIn("selectTab(tab", memo)
        self.assertNotIn('setView("detailed")', memo)

    def test_the_drawings_refit_when_shown(self):
        self.assertIn('whenShown("drawings"', read("memo/memo.js"))
        self.assertIn("export function refitFigures()", read("figures/cards.js"))
        self.assertIn('selectTab("drawings"', read("figures/cards.js"))   # Massing and plans, and a resumed editor


class WhatWasRetired(unittest.TestCase):
    def test_no_view_switch_and_no_3d_preview_page(self):
        self.assertNotIn("view-switch", read("index.html"))
        for name in ("main.js", "modes.js", "runs.js", "tour.js", "figures/cards.js", "core/state.js"):
            js = read(name)
            for gone in ("setView(", "VIEW_KEY", "renderPreview3D(", "state.view"):
                self.assertNotIn(gone, js, f"{gone} in {name}")

    def test_no_css_for_the_old_body_or_the_views(self):
        css = read("app.css")
        for gone in (".memo-body", ".memo-rest", 'data-view="summary"', 'data-view="3d"', ".preview3d", ".view-switch"):
            self.assertNotIn(gone, css, gone)
        # the 920 px caps and the 460 px figure column that left the wide-screen gaps
        self.assertNotIn("\n.memo-ask { max-width: 920px; }", css)
        self.assertNotRegex(css, r"\n\.answers \{[^}]*max-width: 920px")
        self.assertNotIn("minmax(0, 1fr) 460px", css)

    def test_the_reader_reads_the_panels_in_the_papers_order(self):
        css = read("app.css")
        self.assertIn('[data-mode="reader"] .memo-panels, [data-mode="reader"] .memo-panel, [data-mode="reader"] .answers-grid { display: contents; }', css)
        self.assertIn('[data-mode="reader"] #panel-ledger > *, [data-mode="reader"] #panel-inputs .inputs-grid > * { order: 7; }', css)
        self.assertIn('[data-mode="reader"] .inputs-grid { display: contents; }', css)

    def test_the_engine_sheets_are_never_two_up(self):
        # a review the same evening: two to a row drew their 9 px labels at 6.9 px; only FIG 01 and FIG 02 pair
        css = read("app.css")
        self.assertIn(".figures > .figure.sheet, .figures > :not(.figure) { grid-column: 1 / -1; }", css)
        self.assertNotRegex(css, r"\.figures \{[^}]*columns: 2")

    def test_one_formats_note(self):
        html = read("index.html")
        self.assertEqual(html.count('class="export-note'), 1)


class IssueOnTop(unittest.TestCase):
    def test_issue_is_in_the_top_bar_not_the_title_block(self):
        html = read("index.html")
        bar = html[html.index('<div class="topbar-controls">'):html.index("</header>")]
        self.assertIn('id="issue-btn"', bar)
        self.assertIn('id="issue-pop"', bar)
        actions = html[html.index('id="export-actions"'):html.index('id="board-panel"')]
        self.assertNotIn("issue-btn", actions)
        self.assertNotIn('id="issue-panel"', html)

    def test_one_place_sets_its_state_and_says_why(self):
        js = read("issue.js")
        self.assertIn("export function syncIssueButton()", js)
        self.assertIn('btn.setAttribute("aria-disabled"', js)
        self.assertIn("Run again first:", js)
        self.assertIn("Issuing is recorded on the machine running First Read", js)
        # never the native disabled with its reason in a title (keyboard and touch could not reach it)
        self.assertNotIn('$("#issue-btn").disabled', js)
        for name in ("files.js", "runs.js", "main.js"):
            self.assertNotIn('$("#issue-btn").disabled', read(name), name)

    def test_again_only_after_an_issue(self):
        self.assertIn('(state.run.issues || []).length ? " again" : ""', read("issue.js"))

    def test_back_restores_every_layout(self):
        self.assertIn("MODES[mode]) setMode(mode", read("runs.js"))


class StopTwo(unittest.TestCase):
    def test_the_candidates_keep_one_order(self):
        self.assertIn('const CAND_ORDER = ["funder-ready", "outright", "benchmark"];', read("route-stage.js"))

    def test_the_decision_first_the_reference_aside(self):
        js = read("route-stage.js")
        card = js[js.index("function cardOption()"):js.index("function stageAside(")]
        for piece in ('id="stage-for"', 'id="stage-questions"', "lotLine(R.lot)", "figureBlock(o"):
            self.assertIn(piece, card, piece)
        # what the lot and the rules allow before any option is no longer a row of the card
        self.assertNotIn("<dt>What the lot takes</dt>", card)
        self.assertNotIn("<dt>What the rules ask here</dt>", card)
        self.assertIn('id="stage-aside"', js)

    def test_continue_is_always_in_reach(self):
        css = read("app.css")
        rules = re.findall(r"^\.stage-foot \{[^}]*\}", css, re.M)   # top-level rules, at every width
        self.assertTrue(any("position: sticky" in r for r in rules), rules)

    def test_row_02_names_the_suggestion(self):
        js = read("route-stage.js")
        self.assertIn("function optionPending()", js)
        self.assertIn("`Suggested: ${", js)
        self.assertIn("Waits for ", js)


if __name__ == "__main__":
    unittest.main()
