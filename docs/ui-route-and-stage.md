# The route and the stage: design brief for the tool's inputs, 16 Nov 2026

Confirmed by Kai on 16 Nov 2026, after an `/impeccable audit` and critique of the tool the same day (technical audit
14/20, heuristics 24/40; the snapshot is `.impeccable/critique/2026-11-17T04-06-13Z__ffm-ui-index-html.md`). The
problem it answers: the inputs rail did three jobs at once (a seven-stop wizard, a Site form of about 18 fields and an
Option form of about 40, and a progress tracker) in a 36% column, while what each input found landed in the other
column, off-screen. With stop 4 open the rail was 4,966 px tall with 102 buttons; facts were asked twice and shown three
times. Kai's choices: the route and the stage first; three stops; the architect's inputs as schedules in the left
column; Claude in architect mode only; the site's reading visible, the programs' terms and the money assumptions folded.

Not built yet. Nothing in the engine changes.

## 1. Job and audience

- **Development manager:** arrives at a blank tool with an address and a board date. Not a planner; wants the four
  answers, the open items with names, and a PDF, without a form.
- **Architect:** arrives on a run (a link or an issued note); loops edit, run, compare, Revit.
- **Reader:** unchanged, apart from the empty state: with no `?run=`, "No memo is open; ask for a link" instead of
  placeholder verdicts and an instruction to run.

The surface is operated, not read: scanability and one decision at a time outrank expression.

## 2. Outcome and proof

- From an address to an issued memo in three decisions; one card on screen at a time; no fact asked twice.
- The manager's route is never taller than the window; one filled button per screen.
- After a run, Download PDF sits above the fold at 1366 × 768.
- The product's truths carry through: "not sure" is a normal answer with a named person; every figure cites its rule
  or says it is rough or a placeholder; the parcel check on the map stays the flow's peak.

## 3. Direction

No new visual world: DESIGN.md stands. The inputs take the drawing set's own device, the **schedule**, and numbering
becomes the mono "01" keys only (no badge numbers on cards or on Export; the step bar goes).

The thesis: **the left column is what you work from; the right is what it says.**

| Mode | Left column | Right |
|---|---|---|
| Manager | **Route**: three read-only rows, 220 px | **Stage**: one card, its input above its finding |
| Architect | **Schedules**: Site \| Option | the memo |
| Reader | none | the memo, 980 px column |

### The manager

```
ROUTE                      │ STAGE
● 01  The site             │ 01 · THE SITE
○ 02  The option           │ Where is the site?
○ 03  Run                  │ [609 Heatley Ave                    ][Look up]
─────                      │ or a saved site ▾ · or the demo case
Then the memo,             │
the PDF, issuing           │ WHAT YOU GET: the memo's title block, labels only
                           │ 01 Allowed? · 02 Funders? · 03 Open items · 04 Money
```

**01 The site.** Look up, then the parcel check (the map beside the district, lot and street; **Use this site** is
the filled button). A district with no schedule says so in one line ("No RT-3 schedule in the rules: a rough envelope
stands in; the architect confirms it"), with no Claude in this mode. Then, in the same card:

```
WHAT THE OPEN DATA COULD NOT TELL     YES  NO  NOT SURE   WHO ANSWERS
Former Community Vision area           ○   ○      ●        you · Map 1
Transit-oriented area  (tier, if yes)  ○   ●      ○        you · City TOA map
Water and sewer                        ●   ○      ○        you
Buildings on the lot stay              ○   ○      ●        you, then the architect
Front street            (corner lots only: the two streets)
Owner type ▾  ·  Land tenure plan [to confirm]
```

"Frequent bus stop" leaves the manager's questions (no rule reads it) and stays in the architect's schedule. Footer:
**Continue to the option →**, and a quiet "Keep as a site file…". Done, the route row reads
"✓ 609 Heatley Ave · RT-3 · 37.2 × 15.2 m".

**02 The option.** A context line (address · district · lot). **FOR**: the programs as toggles, the Community Housing
Fund and BC Builds on by default, their published terms behind "terms ▸". **What the site allows**: the A to C reading
as a short pill list, run by itself when the stop opens ("Read the site" is no longer a stop). **START FROM**:
Funder-ready (the default) · Outright · Benchmark · Saved ▾, with the reason printed under any candidate that cannot be
built. Then the four-figure block:

```
┌ STOREYS │ HEIGHT  │ FSR │ HOMES ┐
│   6     │ 19.8 m  │ 3.0 │ 109   │   rough / placeholder tags where they apply
└─────────┴─────────┴─────┴───────┘
```

A figure is clicked to type one's own (it then carries a "yours" mark; the Suggested | Mine switch is not on this
block). Homes opens the mix (a preset and four shares). "All 21 figures ▸" opens today's grouped table, which keeps
Suggested | Mine. **What the rules leave to you**: developer partner, site control and tenure, as three rows of the same
schedule. Footer: **Continue to the run →**.

**03 Run.** The option in figures; **Money in** (open when the land needs a price, folded when the owner type carries it
at a nominal value), with "Assumptions the money counts with ▸" folded inside it; **Run the rules**, the one filled
button (Ctrl+Enter works from this stop on).

**After the run.** The route folds to its 44 px strip and the memo takes the pane. The title block's row carries
**Download PDF** (leading), Issue to the architect, Print and More formats. The answers keep their staggered arrival.
Clicking a route row swaps the stage card in for the memo, with "Back to R1"; an edit puts the existing stale band on
the memo, and the next run is R2.

### The architect's left column

Two tabs, Site | Option. Each is a schedule:

```
ITEM | VALUE (edited in place) | REF (A1 / drawings / note) | WHO
```

Clicking a row's ref opens the rule's sentence under the row; this replaces the 57 (i) buttons and the "needed to run"
markers. Unanswered rows show the amber Not sure. **Claude lives here only**: "Odd lot? Ask Claude ▸" in the Site
schedule's head, and "Read the RT-3 schedule with Claude ▸" on the district row when the rules have no schedule; the key
box sits inside those folds. "Save as…" at the foot of each schedule.

## 4. Scope and boundaries

- **In:** the manager's flow; the architect's left column; the chrome (the step bar goes in every mode; the
  walkthrough offer goes; the status strip becomes one line with the Walkthrough link; in manager mode the top bar's Run
  is hidden until a run exists, then shows as a quiet "Run again", enabled only when the memo is stale); the memo head's
  action row; the reader's empty state; the phone and tablet layouts of all of it; the walkthrough rewritten from 15
  stops to about 8 that follow the route.
- **Untouched:** the engine and its outputs; the memo's body (answers, clauses, ledger, figures, Side by side, both
  editors, the paper document); the site pages and the brand; the links `?mode`, `?run`, `?compare`, `?tour`, `?demo`;
  the localStorage and sessionStorage keys (the resume draft adapted to three stops).
- **Anti-goals:** no modal wizard; no stepper of circles, progress bar or tiles; no new colour; no toast; never a
  pre-filled answer presented as a fact; never hiding "not sure".

## 5. States and ranges

Blank; Resume where you were; lookup loading (Overpass up to 30 s, and the card says so); no parcel, a civic-number
mismatch, outside Vancouver; a corner lot; no schedule, an unverified schedule, CD-1; a candidate that cannot be built;
a failed derivation; no saved sites or options; 4 homes (cannot meet 30/50/20); running, a failed run, done, stale;
issuing on the static build (disabled, with the reason). Ranges: addresses to about 45 characters; 0 to 8 open
questions; 2 to 4 programs; 21 figures.

## 6. Interaction and layout

- **1100 px and wider:** the route at 220 px, sticky; the stage card at most about 880 px, left-aligned; the parcel card
  puts the map at 55% beside its facts.
- **760 to 1100 px:** the route becomes a three-part line above the stage.
- **Under 760 px:** the route is one line, "01 of 03 · The site ▾"; the card comes first; the map sits directly under
  its button; the footer's filled button sticks to the bottom of the screen.
- **Feedback:** one sentence per action in the status line; cards swap with a 150 ms fade (none under reduced motion);
  focus moves to the card's heading when the stop changes.
- **Semantics:** the route is a nav named "Stops" with `aria-current="step"`; H1 is the address, or "A site, a funder,
  an option, a memo" on the blank stage; card headings are H2.

## 7. Constraints and open decisions

- No build step; vanilla JS; one page for the local server and GitHub Pages; the Pyodide path unaffected.
- **Prerequisite in the code:** one `FIELDS` registry replacing `SITE_FIELDS`, `OPTION_FIELDS`, `GUIDE_FIELDS`,
  `FINANCE_FIELDS`, `FIELD_META` and `ANSWERS`, each field carrying `ask: {stop, who}` and its `ref`. It drives the
  manager's question schedule, the four-figure block, "All 21 figures", the architect's schedules and the paper's
  inputs.
- One render function per card; one store with a derived `progress()` that gates Run, the route and the status line
  (this also fixes `syncRunButton`, which today treats the blank option as an option).
- After the build, DESIGN.md's Layout, Navigation, Input cards and Walkthrough sections are rewritten
  (`/impeccable document`).
- **Decided, not for a builder to change:** Funder-ready stays the default candidate; owner type and land tenure are
  the manager's; the frequent bus stop is the architect's; Download PDF leads the memo's action row.
- **Left to the build to propose:** how a schedule row edits in place (a plain input, or a click-to-edit cell); the
  exact copy of each card's question heading.
