# UI brief: a clean web front end for First Read

For Claude Code. Target: working and presentable by Thursday evening 22 Oct 2026, demoed Friday
23 Oct. Read `CLAUDE.md` and `README.md` first. The engine (`ffm/`) is finished and tested; the UI
calls it and never re-implements a rule.

## What it is

A local web app, started with one command, that walks a person through the basic steps —
pick a site, describe a building option, run the rules, read the memo — and ends with the option
to export: the memo as a file, and the massing to Revit, where it lands on an annotated sheet.

The memo is the product; the UI is a calm reading room for it. Think "a well-set document with a
form beside it", not "a dashboard". No gauges, no KPI tiles, no charts for their own sake. The
readers are a non-profit's development manager, an architect and a volunteer board; they trust
things that look like a careful memo, and the tool is sold on that first screen.

## Non-negotiables

- One command starts it: `python -m ffm ui` (opens `http://127.0.0.1:8765` in the default browser).
- No build step, no Node toolchain. One `index.html`, one JS file, one CSS file under `ffm/ui/`,
  served by a small Python server. Vanilla JS; if one tiny library helps (Preact from a CDN, or
  none), keep it to one. Must run from a fresh clone with Python alone.
- Server: standard library `http.server` with JSON endpoints, or Flask if already installed. The
  engine package stays dependency-free; any UI dependency goes in `requirements-ui.txt`, never into
  `ffm/engine.py` or `ffm/checks.py`.
- Every number on screen comes from `ledger.json` / `massing.json` produced by `ffm.engine` and
  `ffm.massing`. The UI formats; it never calculates a rule.
- Works offline. Web fonts may load from Google Fonts when online and must degrade to the system
  stack gracefully.
- Looks right at 1366 px (projector) and 1920 px; stacks sensibly at 1024. Prints the memo pane
  cleanly (`@media print` hides everything else).

## The flow (four steps, one page)

A slim step strip under the top bar: **1 Site · 2 Option · 3 Run and read · 4 Export**. It is
navigation and a sense of progress, not a locked wizard: the person can click any step. On a wide
screen the page is two panes: the left pane holds steps 1 and 2 (the inputs), the right pane holds
step 3 (the memo, with the massing drawing in a column of its own at ≥1600 px, otherwise below the
three answers). Step 4 is the action bar at the foot of the right pane and a short Export section.

Top bar: wordmark "First Read" (serif), the *rules as of* date picker, the **Run the rules**
button, and after a run the stamp in monospace with a copy button.

### Step 1, Site

Dropdown of the JSON files in `sites/` (address and zoning district), plus *New site*, which opens
the site fields: address, district, area, frontage, depth, in former Community Vision area, in
transit-oriented area (+ tier), frequent bus stop within 400 m, water and sewer, trees (a small
repeating row: species, DBH, retain/remove), owner, land tenure plan. Every yes/no fact is a
three-state control (**yes / no / not sure**), never a checkbox: *not sure* is what makes the
engine say *uncertain* instead of guessing, and the UI should make that feel like the honest,
normal choice.

### Step 2, Option

Dropdown of `options/` for the chosen site, plus *New option*. Fields in small groups:
*Building* (storeys, height, GFA, residential GFA, non-residential GFA, floor-to-floor, setbacks
front/rear/side), *Units* (studio, 1-bed, 2-bed, 3-bed+, with the total and the two-bed-plus share
shown live under the row), *Tenure* (social housing / secured market rental / other; share below
HILs; agreement years; owner at completion), *Funding* (target programs as checkboxes: CHF, BC
Builds; rent tiers market / RGI / deep subsidy; accessible units; below-market share and discount;
site control; land tenure plan), *Trees* (replacement trees proposed), *Rezoning path* (free
text; empty means "outright only"). *Save option as…* writes a new JSON into `options/` so every
run is reproducible from the command line; never overwrite the shipped examples silently.
Validation is light: numbers are numbers, blanks are allowed.

### Step 3, Run and read

Render from `ledger.json`, not from `memo.md`, so the UI can set it. Order, exactly as the
generated memo:

1. Header: address, option name, proponent, rules as of, stamp.
2. **The three answers** as three stacked cards. *Is it allowed?* (outright verdict, then the
   by-rezoning verdict with the path named), *Does it fit the funders?*, *What is still unsure, and
   who resolves it?* (a compact table: item, status, who/what). These three cards are the hero of
   the page. The verdict word is set large in the serif ("Not outright. By rezoning: not yet
   confirmed."); the supporting findings are body text beneath.
3. Massing: the SVG plan/section with the legend lines, labelled like figures (`FIG 01 Plan`,
   `FIG 02 Section`). If a Revit sheet export exists for this run (`ffm_sheet.png` or `.pdf` next
   to the ledger), show it here as `FIG 03 Revit sheet` with its element count and stamp.
4. *What changed since the previous run*, when a comparison run is selected.
5. Full ledger, grouped by layer A to E, collapsed by default; each row: rule title and version
   date, status, finding, numbers used, source link opening in a new tab.
6. Inputs, Sources, Version stamp.

Status words are always printed, with these colours behind a pill: pass `#15803d`, conditional
`#b45309`, fail `#b91c1c`, uncertain `#6d28d9`, not applicable `#6b7280`, info `#1d4ed8`. White
text on the pill.

Runs: each Run writes `outputs/<site-id>/<timestamp>/` through the engine; the UI lists earlier
runs for the site (reads existing folders on start) in a *Compare with…* dropdown, and shows the
`engine.diff` table when one is chosen. Demo move: run as of 2026-10-23, set the date to
2026-10-27, run, compare: one rule changes version and the stamp changes.

### Step 4, Export

An action bar: **Download memo (HTML)** · **Download memo (Markdown)** · **Print** ·
**Download massing.json** · **Export to Revit**.

*Export to Revit* opens a small panel, not a modal maze: the path of this run's `massing.json`
with a copy button; the two PowerShell lines to run it headlessly (from the README) with a copy
button; and the one-line interactive route (pyRevit > Tools > Run). Below that, a *Check Revit
result* button that re-reads `ffm_revit_result.json` for this run and, when found, shows what was
built (masses, plates, model lines, sheet, exports) and the sheet image. Do **not** launch Revit
from the web server by default: a one-to-three-minute Revit start inside a request is a demo risk.
If a *Build in Revit now* button is added at all, it is last, behind a confirmation, and streams
the pyRevit CLI output to the panel.

## Visual direction

Looked at on awwwards (21 Oct 2026) and taken from the pieces that fit a memo, not a campaign:

- **Two-Do** (twodo.design): a serif display voice for the human sentences, a sans for the
  interface, a mono for status and section labels set small in caps with letter-spacing; one colour
  per meaning and nothing decorative; status written in words; a warm near-black and a "paper"
  light mode. Borrow the three-voice typography and the single-purpose colour rule.
- **Streathers Daynes Smith** (law firm): one hue in two tones for the whole site, hairline rules,
  uppercase small nav labels, serif headlines with one italic word for warmth. Borrow the
  restraint: one hue family, hairlines, and the italic accent for the three verdicts.
- **Linear** (linear.app): two-tone text hierarchy (lead sentence in ink, continuation in grey),
  mono micro-labels like `FIG 0.1`, cards separated by hairlines rather than shadows. Borrow the
  figure labelling for the massing drawings and the ink/grey sentence hierarchy for findings.

The resulting system (superseded on 23 Oct 2026: Kai pinned the Lotwise massing app,
https://kailisun98.github.io/r1-1-massing/, as the visual precedent, and `DESIGN.md` now records the
system as shipped: IBM Plex Sans at 13 px, slate ink on a cool grey page, white panels, ink-filled
buttons, statuses as marked words. The layout, endpoints and definition of done below still hold):

- **Type**: serif for the memo's title, the three verdict sentences and section headings
  (Fraunces or Newsreader from Google Fonts; fallback Georgia); sans for everything interactive and
  for body text (Inter; fallback the system UI stack); mono for stamps, rule ids, section eyebrows
  and figure labels (IBM Plex Mono or JetBrains Mono; fallback ui-monospace). Scale: 40/28/20 px
  serif, 16 px body at 1.5 line height, 13 px form labels, 11 px mono eyebrows with 0.08 em
  tracking.
- **Colour, light first** (projectors and printed memos): paper `#FAF9F6`, ink `#1B1B1A`, grey
  `#6B6B66`, hairline `#E4E2DC`, card `#FFFFFF`. One accent, deep blue `#1D4ED8`, for interactive
  elements only. The six status colours above, used only for status. The massing drawing keeps
  its own tones (blue proposed, grey outright, amber benchmark). A dark mode is welcome if it costs
  nothing: warm near-black `#141311` with the same roles.
- **Surfaces**: cards on paper with a hairline border, 8 px radius, 20 to 24 px padding, no drop
  shadows. Section eyebrows in mono caps (`01 · IS IT ALLOWED`) above serif headings.
- **Density**: calm. One idea per card. Forms in a single column with generous label spacing;
  grouped under mono eyebrows, not boxed.
- **Motion**: one 150 ms fade when a run lands; nothing that outlasts the work. Respect
  `prefers-reduced-motion`.
- **Microcopy**: plain sentences. "Not sure" rather than "N/A". Buttons say what they do: *Run the
  rules*, *Download memo*, *Export to Revit*.
- **Empty state**: site and option preloaded with 998 E 19th Ave and one sentence of what Run
  will do; the three answer cards present but quiet until the first run.

## Endpoints (if `http.server`)

```
GET  /api/sites                 -> [{id, address, zoning_district, file}]
GET  /api/sites/<id>            -> site JSON
GET  /api/options?site=<id>     -> [{id, name, file}]
GET  /api/options/<id>          -> option JSON
POST /api/options               -> save a new option JSON (body: option); refuses to overwrite
POST /api/run                   -> body {site, option, as_of, previous_run?}; returns {run_id, ledger, massing, svg, diff?}
GET  /api/runs?site=<id>        -> past runs with as_of, stamp, verdicts
GET  /api/runs/<run_id>/<file>  -> memo.html | memo.md | ledger.json | massing.json | massing.svg | ffm_revit_result.json | ffm_sheet.png
```

Add `ui` as a subcommand in `ffm/cli.py`, with `--port` and `--no-browser`.

## Order of work (two days)

Day 1, Wed 21 Oct: server + `/api/run` + the memo pane rendering the three answers and the full
ledger from `ledger.json`, preloaded with 998 E 19th Ave, working end to end first; then the
option form bound to the JSON (read and write), the Run button, the step strip, the downloads.
Day 2, Thu 22 Oct: massing figures and the Revit result; past runs and the compare table; the
Export panel; print stylesheet; typography and spacing pass against the visual direction; walk
`docs/pitch-outline.md` against the UI and fix what stumbles.

Stop and ask before: adding a second dependency, changing anything in `ffm/engine.py`,
`ffm/checks.py` or `rules/*.json`, changing the memo's section order, or launching Revit from
the server.

## Definition of done for Friday

- `python -m ffm ui` opens the page; Run on the preloaded inputs shows the three answers in under
  a second with the correct verdicts (outright: no; by rezoning: not yet confirmed; funders: not
  yet confirmed) and the stamp `20e44f1445ecaff9` for as-of 2026-10-23.
- Changing the as-of date to 2026-10-27 and comparing shows one changed rule (`cov.family_units`)
  and a new stamp.
- Editing the unit mix in the form and re-running changes the family-units row and nothing else.
- The massing figures and all downloads work; the Export panel shows the Revit instructions, and
  the Revit result and sheet image appear when the result file exists.
- `python -m unittest` still passes, unchanged.
- It looks like a document someone cared about, in the typography and colour above.
