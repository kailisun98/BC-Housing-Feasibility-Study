---
version: 1
slug: "ffm-ui-home-html"
primary_target: "ffm/ui/home.html"
related_targets: []
---

# Surface brief: home page (ffm/ui/home.html)

Scope: the front door of Funding-Fit Memo, served at `/` locally and on GitHub Pages; the tool moves to
`/app.html` (source file stays `ffm/ui/index.html`). Visitor mode: Persuade.

Audience and job: practitioners first (non-profit development managers, feasibility architects); course
reviewers and board readers read over their shoulder. They should understand why feasibility checks come
late, believe the memo's answers are shown, cited and dated, and try it on the real case.

Action: three demonstration calls to action at the close: run the 998 E 19th Ave case with the
walkthrough (`app.html?tour=1`), watch a rule change (`app.html?run=…&compare=…`), read the memo it wrote
(`data/runs/998-e-19th-ave/2026-10-27/memo.html`). A quiet GitHub issue link asks for a 20-minute session.
"Open the tool" sits in the top bar.

Proof and content: only the committed 998 E 19th Ave runs (23 and 27 Oct 2026), the rule files and
massing.json. Week timings on the ruler are illustrative and labelled so; every finding is the tool's own.
No testimonials, adoption claims or pricing.

Constraints: visual world is the tool's Lotwise restyle (commit 9d805fc, recorded in DESIGN.md). The
`?tour` / `?run` / `?compare` deep links live in app.js (`followLink`); a wordmark link from the tool back
to the home page is still open.

## Direction contract

THESIS: The problem is time. A dated week ruler shows the rules that surface after design starts, pinned
where they bite; one switch collapses them to day one, where the memo states all six with status and owner.
It refuses the category default: headline, subcopy and button over a row of feature cards.

OWN-WORLD: Lotwise. Cool grey page #f5f6f8, white panels with a 1px #e1e5ea line and a whisper shadow, slate
ink #2c3e50, blue #2a6fb8 only for links and focus, amber #c77d14 for pending, status pills with a glyph
mark, IBM Plex Sans at 13px body, 18px titles and 11px keys, Plex Mono for weeks, ids and the double-rule stamp,
drawings on white paper with a title block, dark-ink buttons that lift on hover and sink on press.

STORY: Rules arrive late and cost redraws; they live in five layers owned by different people; the memo
answers them on day one with arithmetic, clause, date and owner; it re-stamps when a rule changes; try it.

FIRST VIEWPORT: Top bar (wordmark, anchors, Open the tool). The headline at DESIGN.md's 18px title size
on the left, one 13px paragraph on the right; the drawing sheet carries the viewport, title block and
stamp included, with room to spare at 1366x768 windowed. Kai kept DESIGN.md's rule against a 16px body
and large display type (Oct 2026), so the whole page sits at the tool's drafting density. Below, full width, a white drawing sheet: a Without / With the memo switch, the
WK 0 to WK 12 ruler, a design band with redraw marks, six findings hanging from their weeks in two lanes,
and a title block with site, as-of date and the stamp.

FORM: "Before the first drawing", third of my seven ranked structures, dealt by seed 3ea85d75.
Signature interaction: the switch FLIP-moves the six findings from their weeks into a day-one grid, where
each gains its status pill and who resolves it; 420 ms ease-out, instant under reduced motion.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
