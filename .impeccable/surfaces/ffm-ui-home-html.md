---
version: 2
slug: "ffm-ui-home-html"
primary_target: "ffm/ui/home.html"
related_targets: ["ffm/ui/home.css", "ffm/ui/home.js", "ffm/ui/hero-memo.jpg"]
---

# Surface brief: home page (ffm/ui/home.html)

Scope: the front door of Funding-Fit Memo, served at `/` locally and on GitHub Pages; the tool is
`/app.html` (source file `ffm/ui/index.html`). Visitor mode: Persuade, read like a short paper: the visitor
should be able to browse it by its four sections and read any one of them comfortably.

Audience and job: practitioners first (non-profit development managers, feasibility architects); course
reviewers and board readers read over their shoulder. They should understand why feasibility checks come
late, see what the memo answers and how one of its rows reads, and try it on the real case.

Action: the hero offers the tool with its walkthrough (`app.html?tour=1`) and two options compared
(`app.html?run=998-e-19th-ave/what-if-funder-ready&compare=998-e-19th-ave/as-approved`). The close repeats
them as Run / Compare / Read, Read opening the what-if's memo
(`data/runs/998-e-19th-ave/what-if-funder-ready/memo.html`). A quiet GitHub issue link asks for a 20-minute
session. "Open the tool" sits in the top bar.

Proof and content: only the committed 998 E 19th Ave runs, the rule files and what the tool prints. The hero
image is a capture of the tool's own as-approved memo (provenance in a comment beside the img). No
testimonials, adoption claims or pricing.

Constraints: visual world is the tool's (DESIGN.md). `hero-memo.jpg` keeps its name: `server.py` serves it and
`pages.py` copies it. The `?tour` / `?run` / `?compare` deep links live in app.js (`followLink`).

## Direction contract (revised 23 Oct 2026: the reading pass)

THESIS: Will this scheme be allowed, and will a funder back it? The page answers the way the memo does: the
problem, how it works, what the memo answers, then the real case, each section a heading, a short paragraph at
reading size, and one drawing sheet that carries its material.

OWN-WORLD: the tool's. Cool grey page, white panels with a 1px line and a whisper shadow, slate ink, blue only
for links and focus, amber for what is pending, status pills with a glyph mark, Plex Mono for ids and the
double-rule stamp, drawings on white paper with a figure block along the foot, dark-ink buttons.

READING: labels, cards and figures keep the tool's drafting density (13px, 11px keys); running prose is 14px on
a 1.6 leading and a 66-character measure; the headline is 22px (20px on a phone), section headings 18px.
Sections sit 64px apart (48px on a phone). The top bar's anchors mark the section the reader is in.

FIGURES: HTML in the drafting language, never pictures of it, so they reflow on a phone and their type stays at
the page's sizes. Fig 1: five stage cells with the memo's stage in ink, then the five rule layers as a table
with who reads them and when. Fig 2: three steps (you give it, run the rules, read the memo) with the loop
back. Fig 3: one row of the memo, each column's note under its value.

FIRST VIEWPORT: Top bar (wordmark, anchors, Open the tool). The headline and lede on the left with the two ways
in; the memo itself on the right, captured from the tool from its title down.

FINISH: the reading pass was audited (a11y, performance, theming, responsive, integrity) and its findings
implemented on 23 Oct 2026; DESIGN.md records the reading sizes.
