---
version: 4
slug: "ffm-ui-home-html"
primary_target: "ffm/ui/home.html"
related_targets: ["ffm/ui/home.css", "ffm/ui/home.js", "ffm/ui/hero-memo.jpg", "ffm/ui/hero-memo-790.jpg"]
---

# Surface brief: home page (ffm/ui/home.html)

Scope: the front door of Funding-Fit Memo, served at `/` locally and on GitHub Pages; the tool is
`/app.html` (source file `ffm/ui/index.html`). Visitor mode: Persuade, read like a short paper: the visitor
should be able to browse it by its four sections and read any one of them comfortably.

Audience and job: practitioners first (non-profit development managers, feasibility architects); course
reviewers and board readers read over their shoulder. They should understand why feasibility checks come
late, see how the tool works (the massing and the Revit sheet included) and how one of the memo's rows reads,
and try it on the real case.

Action: one label per destination, the same in the hero and the close. "Run the real case with a
walkthrough" (`app.html?tour=1`) is the page's one dark button; "See two options compared"
(`app.html?run=998-e-19th-ave/what-if-funder-ready&compare=998-e-19th-ave/as-approved`) is a plain link beside
it; the close adds "Read the approved case's memo" (`data/runs/998-e-19th-ave/as-approved/memo.html`). The
top bar's "Open the tool" is a secondary button. The footer asks, through a GitHub issue link, for a
20-minute session.

Proof and content: only the committed 998 E 19th Ave runs, the rule files and what the tool prints. The hero
image is a capture of the tool's own as-approved memo (provenance in a comment beside the img); its three
findings are set in type under it, from that run's answers. The rule count is dated (as of 23 Oct 2026).
No testimonials, adoption claims or pricing. Open: the "$200,000 to $500,000" pre-development figure has no
cited source yet; Kai to supply one or the page to drop the range.

Constraints: visual world is the tool's (DESIGN.md). `hero-memo.jpg` keeps its name: `server.py` serves it and
`pages.py` copies it, as they do `hero-memo-790.jpg`, the same capture at half size for phones (srcset). The
`?tour` / `?run` / `?compare` deep links live in app.js (`followLink`).

## Direction contract (revised 23 Oct 2026: the critique fixes)

THESIS: Will this scheme be allowed, and will a funder back it? The page answers the way the memo does: the
problem, how it works, one row of the memo, then the real case, each section a heading and a short paragraph
at reading size with the least material that carries it.

OWN-WORLD: the tool's. Cool grey page, white panels with a 1px line and a whisper shadow, slate ink, blue only
for links and focus, amber for what is pending, status pills with a glyph mark, Plex Mono for ids, dark-ink
buttons.

QUIET: one sheet of white paper below the hero (the memo row) and nothing else boxed. The stages are dots on a
hairline, the memo's stage noting that it reads layers A to E; the rule layers a plain table; the steps three
columns under hairlines. One dark button on the page; the alternatives are plain links.

SEGMENTS (Kai, 23 Oct 2026: the page still read as one chunk): the sections alternate between the page grey
and a slate band run edge to edge (`--band` #e7eef5, the page's own hue one shade deeper, with its own line
and group tones; white paper keeps its cool rules on it). A beige band was tried first and replaced at Kai's
request for a more complementary palette: it shared Amber's hue, so it read as pending and dulled the amber
marks; on slate, amber is the one warm note. The problem and the memo row sit on the band; the hero, how it works and the real case on
the grey; the footer follows under a hairline. Sections carry 56px top and bottom (44px on a phone).

REVISIONS: the page never shows a stamp's hash; the rules are named by revision (R1, R2…), as in the tool.

READING: labels and the memo row keep the tool's drafting density (13px, 11px keys); running prose, the steps
included, is 14px on a 1.6 leading and a 52ch measure (about 68 characters); the headline is 22px (20px on a
phone), section headings 18px. The top bar's anchors mark the
section the reader is in, the last one at the foot of the page; on a phone they take a second row of a bar
that no longer sticks.

FIRST VIEWPORT: Top bar (wordmark, anchors, Open the tool). The headline and lede on the left with the button,
the compare link and the engine's download note; the memo itself on the right, captured from the tool from
its title down, its three findings in type under it.

FINISH: the critique and audit fixes were checked at 1366 and 390 px, light and dark (no contrast failures, no
overflow, 44px touch targets on a coarse pointer, section tracking to the last anchor, 68 characters a line,
the 78 KB image on phones) on 23 Oct 2026.
