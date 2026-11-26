# CLAUDE.md — First Read

The tool's name is "First Read" (decided by Kai on 23 Oct 2026 for the mid review; it replaced
"Lot by lot" from earlier that day, which replaced "Funding-Fit Memo"). Subtitle: "a funding-fit
memo for BC non-profit housing". Only visible names changed: the `ffm` module, the repository
name and the GitHub Pages URL stay. Do not revert the name without Kai saying so.

Context for Claude Code working in this repository on Kai's Windows machine.

## What this is

ARCH 540 Assignment 2 (UBC SALA, fall 2026). A deterministic feasibility screen for BC non-profit
housing: a cited, dated rule stack (`rules/*.json`) → engine (`ffm/`) → memo + ledger + version
stamp + rule-derived massing (`massing.json`, `massing.svg`) → Revit masses via a pyRevit script
(`revit/ffm_massing_pyrevit.py`). Mid review is Friday 23 Oct 2026; final review 10 Dec 2026.
`README.md` explains the design; `docs/pitch-outline.md` has the demo script.

The engine is pure Python 3.10+ standard library. Do not add dependencies to it. No language model
runs inside the engine, and that is a design decision, not an omission.

## Everyday commands

```powershell
python -m unittest -v                                   # 23 tests must pass
python -m ffm run --site sites/998-e-19th-ave.json --option options/998-e-19th-ave-as-approved.json --out outputs/998-e-19th-ave/as-approved --as-of 2026-10-23
python -m ffm run --site sites/998-e-19th-ave.json --option options/998-e-19th-ave-as-approved.json --out outputs/998-e-19th-ave/as-approved-rules-2026-10-27 --as-of 2026-10-27 --previous outputs/998-e-19th-ave/as-approved/ledger.json
python -m ffm run --site sites/998-e-19th-ave.json --option options/998-e-19th-ave-what-if-funder-ready.json --out outputs/998-e-19th-ave/what-if-funder-ready --as-of 2026-10-23 --previous outputs/998-e-19th-ave/as-approved/ledger.json
python -m ffm run --site sites/1010-expo-blvd.json --option options/1010-expo-blvd-as-permitted.json --out outputs/1010-expo-blvd/as-permitted --as-of 2026-10-23
python -m ffm run --site sites/1010-expo-blvd.json --option options/1010-expo-blvd-what-if-12-storey.json --out outputs/1010-expo-blvd/what-if-12-storey --as-of 2026-10-23 --previous outputs/1010-expo-blvd/as-permitted/ledger.json
python -m ffm ui                                        # the web UI at http://127.0.0.1:8765 (--port, --no-browser)
```

On this machine `python` is the Microsoft Store stub; use uv's interpreter (`uv python find 3.12`).

## The Revit step

State on 21 Oct 2026 (from `outputs/998-e-19th-ave/2026-10-23/ffm_revit_result.json`): the
replaced script ran headlessly on this machine with all five stages ok (links, masses, views,
annotations, sheet) plus the PDF and PNG exports, from the office template at Kai's instruction
(`FFM_TEMPLATE`). Fixes made against the live API, Revit 2026: element ids cast to `int` (IronPython
`long` is not JSON-serialisable); TextNote widths are paper feet; view templates detached before
showing masses; the axon cropped to the lot box in view coordinates (else its viewport spans the
whole model); the sheet laid out from the title block's bounding box with the scale chosen to fit
(1:500 on this title block); project information filled from the ledger; a 3 mm text type; one
label per label pair. Earlier background:

- The script has since been replaced with the version that also makes views, annotations, a sheet
  and exports (the local edits that chose the template and removed links were overwritten; the
  replacement takes `FFM_TEMPLATE` instead). Prefer Revit's own default metric template (leave
  `FFM_TEMPLATE` unset) over the office template: it is clean, ships title blocks, and carries no
  links. Use `FFM_TEMPLATE` only if the default is missing on this install.
- That office template belongs to Kai's former employer and links to a live office project. The
  brief forbids putting anyone's documents in the public repository without permission, so the
  `.rvt`, and any result JSON that names that template or its link paths, stay local: `.gitignore`
  now excludes `outputs/**/*.rvt`; before any commit, check `ffm_revit_result.json` for office paths
  and regenerate it from the default template. Ask Kai before using the office template at all.

Goal of the next run: prove the replaced script builds the masses and puts them on an annotated
sheet (axon, dimensioned plan, section with the benchmark lines, text blocks taken from
`ledger.json`), exports the sheet as PDF/PNG, and leaves a saved `.rvt` Kai can open for the demo.
Revit is only on this Windows machine; nothing here can be done in a cloud sandbox. The script runs
in five stages, each in its own transaction (masses, views, annotations, sheet, export); a failure
in a later stage is recorded in `ffm_revit_result.json` under `errors` with its traceback and the
earlier stages stand. Fix stage by stage; expect the sheet and export stages to need one or two
iterations against the live API (text-note placement, PDF export options differ by Revit year).

Preferred route, headless through the pyRevit CLI:

1. Check the tools: `where pyrevit` and `pyrevit env` (lists installed Revit years and the CLI
   version). If `pyrevit` is missing, pyRevit (with its CLI) installs from
   https://github.com/pyrevitlabs/pyRevit/releases — ask Kai before installing anything.
2. Make sure a fresh run exists: run the first `python -m ffm run ...` command above.
3. Set the environment variables and run, in PowerShell:
   ```powershell
   $env:FFM_MASSING_JSON = (Resolve-Path "outputs\998-e-19th-ave\2026-10-23\massing.json").Path
   $env:FFM_SAVE_AS      = (Join-Path (Split-Path $env:FFM_MASSING_JSON) "ffm_massing.rvt")
   $env:FFM_TEMPLATE     = "C:\Users\kaili\OneDrive - UBC\Desktop\Work\0000 Public Template\PUBLIC TEMPLATE.rte"   # Kai's choice, 21 Oct 2026
   $script = (Resolve-Path "revit\ffm_massing_pyrevit.py").Path
   pyrevit run "$script" --revit=2026
   ```
   Use the Revit year `pyrevit env` reports (2026 here). The script path must be absolute: the
   runner resolves it from a temp folder and a relative path exits 0 having run nothing. Leave
   `--purge` off, it deletes the run log. A run takes about a minute; the CLI prints the log path.
   Revit must be closed first (the `.rvt` is overwritten); if a Revit window is open, close it
   from the UI and answer No to saving the generated model.
4. Verify without opening Revit: read `outputs\998-e-19th-ave\2026-10-23\ffm_revit_result.json`.
   `ok` must be true; `stages` should read ok for masses, views, annotations and sheet; `built` must
   list two masses (`FFM proposed` 22.3 m, 6 storeys; `FFM outright` 9.9 m, 3 storeys), five floor
   plates, 4 + 4 model lines, three views, the annotations line, and sheet `FFM-01`; `exports` should
   name `ffm_sheet.pdf` and/or `ffm_sheet.png`; `saved_as` must point at an `.rvt` that now exists.
   `ffm_sheet_notes.json` holds the exact text placed on the sheet. Then run
   `python -m ffm memo --out outputs\998-e-19th-ave\2026-10-23` so the memo gains its
   "Built in Revit" section (with the sheet image if the PNG exported). Report stages, element ids,
   exports and the stamp back to Kai, and look at `ffm_sheet.png` yourself to check the layout
   (viewports not overlapping the text column, labels legible); adjust the placements in
   `stage_sheet` if needed.
5. If the result file is missing, read the pyRevit run log the CLI named; the script prints its
   traceback there. The usual causes: the Revit year flag does not match an installed Revit; a
   Revit dialog (unsigned add-in, journal recovery) blocking a headless start — in that case run
   it interactively instead (below); a path with spaces not quoted.

Interactive route (if the CLI is unavailable or blocked): Kai opens Revit, starts a new metric
project, and runs the script with pyRevit > Tools > Run (or pastes it into RevitPythonShell).
Set `FFM_MASSING_JSON` first in the shell Revit is launched from, or let the file dialog ask. The
script makes its own views with Mass visibility on and opens nothing, so tell Kai to open sheet
FFM-01 from the Project Browser. The script still writes `ffm_revit_result.json`, so the
verification step is the same.

Order of the whole job: UI first (docs/ui-brief.md), Revit step when Kai is at the machine with
Revit closed, then `python -m ffm memo` and the UI's Export panel will show the sheet.

Do not edit the script to need pyRevit-only modules at import time; it must also run in
RevitPythonShell and under `pyrevit run` (IronPython 2.7). No f-strings or type annotations in it.

## The UI (next piece of work)

`docs/ui-brief.md` is the brief: a local web app started with `python -m ffm ui`, no build step,
one `index.html` + JS + CSS under `ffm/ui/`, a small Python server with JSON endpoints, the memo
rendered from `ledger.json`, the massing SVG beside it, past runs and a compare table. The engine
is not touched. Read the brief before writing any UI code; it has the layout, the colours, the
endpoints, the two-day order of work and the definition of done.

State on 21 Oct 2026: both days' scope is built (`ffm/ui/server.py`, `index.html`, `app.js`,
`app.css`; `ui` subcommand in `cli.py`). Server with the brief's endpoints plus `/api/rules`,
`/api/diff` and `GET /api/runs/<site>/<folder>`; the memo pane (header, three answers, FIG 01 plan
and FIG 02 section drawn from `massing.json`, FIG 03 the Revit sheet when a result exists, What
changed, full ledger, inputs, sources, stamp); forms bound to the JSON with *Save as…*; *Open a past
run* and *Compare with…* (diff computed by the engine); the step strip; downloads and Print; the
Export to Revit panel with *Check Revit result* (which also rewrites the memo). Each Run writes
`outputs/<site>/<timestamp>/`. `docs/pitch-outline.md` has the UI version of the live run. Not
done: nothing launches Revit from the server (by design); no dark-mode polish pass.

Added 23 Oct 2026: FIG 01 carries a Plan | 3D segmented switch; the 3D view (`fig3d` in `app.js`)
is a dependency-free orbitable axonometric drawn from `massing.json`. A second case study,
`sites/1010-expo-blvd.json` with `options/1010-expo-blvd-as-permitted.json` and the run in
`outputs/1010-expo-blvd/2026-10-23/`, comes from public City pages (see README); it is a CD-1 site,
so the outright rules are not applicable and the memo's outright answer reads "not assessed" (since 15 Nov 2026;
before that it read "yes", an engine limitation noted in the site file).

Comparison demo (23 Oct 2026): `options/998-e-19th-ave-what-if-funder-ready.json` is the five-storey
what-if with every funder question answered (rent tiers 30/50/20, 5 accessible units, 60-year
agreement, 19 replacement trees, land tenure stated as settled), so its run in
`outputs/998-e-19th-ave/what-if-funder-ready/` reads by rezoning: yes, funders: yes, nothing outstanding.
Run folders are named by option, not date (`as-approved`, `as-approved-rules-2026-10-27`,
`what-if-funder-ready`; `as-permitted`, `what-if-12-storey`); the 5-storey what-if was deleted on
23 Oct 2026 as a duplicate of the funder-ready one.
The 998 site's transit-oriented answer is now No (nearest SkyTrain stations over 800 m; confirm on
the City's map). The home page's compare links ("or see two options compared", "Compare two options") open
`app.html?run=998-e-19th-ave/what-if-funder-ready&compare=998-e-19th-ave/as-approved`; when two runs are
compared, a Side by side card follows the title block with the two run pickers (`#tool-open`,
`#tool-compare`, moved there by `placeRunTools` in `app.js`, keeping focus) in a row over its A and B
columns, a one-line trade-off, the four answers, and only the rules whose status differs (the rest behind
a disclosure); then What changed. `compareKind` tells a change of rules (Revision, the delta) from two
options under the same rules ("What changed between the two options", no delta). The answer cards carry
no A | B strip any more. Opening a run that has a stored diff.json compares it with the run it was
recorded against when the list can tell which (`recordedAgainst`). The UI no longer shows the stamp's
hash: each memo on a site is a revision, R1, R2… (`noteRevisions` / `madeHere` / `rev` in `app.js`):
the committed base runs first, then those recorded against another (they have a diff.json), each by
as-of date and folder, then runs made in the tool in the order made. On 998 E 19th Ave: as-approved R1,
what-if-funder-ready R2, as-approved-rules-2026-10-27 R3; on 1010 Expo Blvd: as-permitted R1,
what-if-12-storey R2. The hash appears only in the memo's Rules fingerprint card; the engine's
memo.md/memo.html and the Revit Comments still carry it. Inputs carry marks (needed to run, read by a
rule, drawings only) and (i) explanations from `FIELD_META` in `app.js`; the memo has a
"Clauses applied" table (proposed, permitted or required, the ask) before the layered ledger.

PDF and the inputs rail (23 Oct 2026): Download PDF and Print both use `paperDocument(run)` in `app.js`,
a self-contained paper layout of the memo for a reviewer (title block; the three answers with the rules
that decide them; open items with who resolves them; the comparison; clauses; massing figures; the full
ledger by layer; inputs; numbered sources with URLs; how to reproduce it), with every rule referred to as
A1…E4. `POST /api/pdf` in `server.py` prints that HTML with a headless Edge or Chrome (`find_browser`,
`FFM_BROWSER` overrides) and returns the PDF; without a browser (501), or on GitHub Pages, the page
opens the same document in the print dialog. The preview server the Claude app starts cannot launch
Edge (its sandbox), so test the PDF against a server started from a shell (`python -m ffm ui`). The
step bar's "Hide inputs" button is gone: the rail folds with the chevron row at its top
(`#rail-toggle`, `showInputs`), remembered in localStorage (`ffm.inputs.collapsed`).

Context from OpenStreetMap (23 Oct 2026): `python -m ffm context --site sites/<id>.json [--radius 120]
[--center lat,lon]` (`ffm/osm.py`, standard library) locates the address with Nominatim, fetches
roads, buildings and trees from the Overpass API, converts them into the lot frame (front street
matched by name, frame nudged so the front and any cross street sit half a right-of-way outside the
lot lines, buildings on the lot itself omitted) and stores the block under the site's `osm` key. The
figures read that block; without it they fall back to a schematic context. The block carries the
ODbL attribution, which the figure caption and README repeat. Re-run the command to refresh; it
reuses the saved centre, so Nominatim is asked once per site.

The page also runs on GitHub Pages (https://kailisun98.github.io/BC-Housing-Feasibility-Study/):
`python -m ffm pages` (`ffm/pages.py`) builds a static site (since 3 Nov 2026 every page names its scripts and
styles with a hash of their contents, `site.css?v=…`, so a browser that cached the last deploy fetches the new
one; Pages serves with max-age=600 and Edge kept the old app.js past that; since 16 Nov 2026 the tool's ES
modules each carry their own hash through an import map, below) whose modules detect
`window.FFM_STATIC` (`core/state.js`), read the committed runs from `data/` and run the engine in Pyodide from
`engine/`. Published by the Actions workflow in `.github/workflows/pages.yml` on every push to
`main` (Pages is set to build from Actions; the old `gh-pages` branch is no longer used). The gh
CLI login on this machine has the `workflow` scope since 22 Oct 2026. Never let the pages build
copy office-template files; `pages.py` lists the run files it copies.

## The site and the brand (2 Nov 2026)

Kai asked for a landing site with fewer words, explained by diagrams and short blocks, after hamol.studio
(the pinned example) and prime-exits.bigly.studio, with several pages, the user flows mapped, the tool's UI
redesigned from those flows, and a brand package. State now:

- `docs/user-flows.md`: the three readers' flows (manager, architect, board/planner/funder) and the site map.
- The site, under `ffm/ui/`: `home.html` (served at `/`), `how.html`, `who.html`, `case.html`, `brand.html`,
  on `site.css` and `site.js`; dark ("the desk at night"), IBM Plex Sans 300 display type, numbered sections,
  the research document's diagrams redrawn in HTML (the gate, inputs to outputs, the tool logic, who reads
  which layer when, the flows). The hero's isometric massing is an SVG generated from
  `outputs/998-e-19th-ave/as-approved/massing.json` numbers (the generator was a scratch script; the SVG is
  inline in `home.html`). All numbers on the site come from the committed ledgers.
- The brand: `ffm/ui/brand.css` (tokens shared by site and tool), `ffm/ui/brand/` (mark, mark-tile,
  wordmark, lockup, lockup-stacked SVGs); `brand.html` is the guidelines page. The mark is the research
  diagrams' diamond on a five-stage timeline. `DESIGN.md` records the system.
- The tool: `index.html` links `brand.css` before `app.css` and carries the mark; the top bar is the ink
  chrome, Run the rules is signal blue, the steps are a progress line, Download PDF leads the export bar.
  `app.js` was not touched; its DOM contract (ids, `.steps a[data-step]`, `.panes`) is unchanged.
- `server.py` serves any `*.html|js|css|svg|jpg|png` beside it (and `brand/*`) by a whitelist pattern;
  `pages.py` copies `SITE_PAGES`, `SITE_FILES` and `brand/`. `home.css`, `home.js` and the hero JPEGs were
  deleted. `.claude/launch.json` in this folder starts the UI for the browser preview.
- Who is reading (2 Nov 2026, second pass): the tool's top bar carries a Manager · Architect · Reader switch
  (`#mode-switch` in `index.html`; `setMode`, `MODES`, `applyModeToMemo`, `initialMode` in `app.js`; the
  `[data-mode]` rules at the end of `app.css`). `?mode=` in a link picks it for a visitor (the site's flows and
  case page link that way), localStorage `ffm.mode` keeps it. Manager: the rail open with the cards collapsed,
  PDF leads Export. Architect: the forms open (selectSite/selectOption no longer collapse them), every ledger
  layer open, the figures beside the answers from 1280px, Export to Revit leads. Reader: the rail, steps, run
  controls, pickers, massing and Revit buttons hidden; the memo in a 980px reading column at 14px. The memo's
  answer headings are now the site's keys (a mono "01" and tracked caps) over a 24px light verdict; the memo
  title is 30px light; buttons are pills. The engine and the memo's content are the same in every mode.
- Audit fixes (2 Nov 2026, `/impeccable audit` 17/20): white text sits only on the deep signal (#2A6FB8); long
  buttons wrap under 560px; print blocks in app.css, site.css and brand.css use selectors that beat the dark-mode
  block; 44px mode switch and nav links on touch; the who-reads-what grid is a `role="group"`; prose on a wash
  takes the wash's ink via the never-flipped `--lt-*` constants in brand.css; the info popover lost its blue
  side bar; DESIGN.md's frontmatter now lists the site's tokens. Still open, by choice: the site's kickers and
  section numbers (the Hamol brief), the hero's 1.02 leading, and the stale `.impeccable/design.json` sidecar.
- Motion (2 Nov 2026, `/impeccable animate`; DESIGN.md "Motion" has the timings): the site hero's massing builds
  itself (clip-path rises in `site.css`); section reveals are fades with a short list stagger; the gate's early
  diamond rings once. In the tool: the mode switch's `.seg-thumb` slides (`placeModeThumb` in `app.js`); the
  Site and Option forms sit in a `.form-fold` grid row (index.html) that goes 0fr to 1fr instead of
  `display: none`; the answers land staggered; the rail column and the status wash ease. Every effect has a
  reduced-motion path. The preview pane throttles transitions while hidden, so measure after a wait.
- Not done: no screenshot of the tool is used anywhere (by design).
- Hero drawings on the inner pages (17 Nov 2026): `how.html`, `who.html` and `case.html` carry `hero page two` (the home
  page's two columns) with an inline SVG beside the text, each on the home hero's classes and motion (`hero-iso` plus
  `hero-hw` / `hero-who` / `hero-case`; site.js adds `.play` to the first `.hero-iso`): the option over the six exploded
  rule layers beside the R1 memo sheet; the memo three times, one sheet a reader, fanned from the mark's diamond on the
  five-stage timeline; the case's street elevation at 6.2 px to the metre with the outright line, the benchmark band and
  the twenty trees. Two things learned: an animated SVG `<g>` must not carry a `transform` attribute (the CSS animation's
  `transform: none` replaces it), so each who sheet's translate sits on an inner group; and the preview pane, hidden, runs
  the page as a background tab, where delayed CSS animations never leave their delay: finish them with
  `document.getAnimations().forEach(a => a.finish())` before a screenshot. The pane's `ffm-pages` server serves the
  `_site` folder named in its command line (a different scratchpad path than the session's own), so build there.
- Scroll motion (17 Nov 2026, after an /impeccable exploration; DESIGN.md "Motion" has the timings): the gate's early
  diamond travels back along the memo's row on a view timeline (`dia-travel`, `.marks` is a size container, the distance
  in `cqw`) and rings when site.js adds `.landed`; the logic diagram's twelve nodes carry `--i` (their reading order, also
  printed in the kind label) and arrive in that order; the who-reads-what memo cells carry `--r` and fill top to bottom;
  `.nav::after` is a scroll-timeline progress line; `@view-transition { navigation: auto }` crossfades the site's pages
  with `.nav` held still (app.html does not opt in). The hero foot's counter is now five section links (`aria-current`).

## Phase 1 of the workflows proposal (3 Nov 2026; `docs/proposal-workflows.md`)

Built and verified in the browser:
- `ffm/suggest.py`: rule-derived suggestions. `suggest(site, programs, on, candidate)` walks layers A to E and
  returns an option plus `fields` (value, rule_id, note per dotted key), `unsure` (what a person settles),
  `assumptions` (declared placeholders: floor to floor 3.3 m, setbacks 3.7/6.0/3.0, net efficiency 0.78,
  10% over the BC Housing minimums, a starting mix). Candidates: outright, benchmark, funder-ready. On
  998 E 19th Ave funder-ready gives 6 storeys, 19.8 m, FSR 3.0, 109 units, tiers 33/54/22, 19 trees.
  `read_site(site, on)` runs layers A to C with a bare social-housing probe. Tests in `tests/test_suggest.py`.
  `suggest(..., fixed={storeys, height_m, gfa_m2, units})` (17 Nov 2026) carries the derivation on from the
  manager's own figures: the homes follow the floor area typed, and the rent tiers, the accessible count and the
  below-market share follow the homes; `fields` keep the rules' own figures. The stage sends `fixed` on every
  derivation (`guide.js` `fixedFigures`), and a changed storeys, height, floor area or unit count re-derives. Found
  on 3475 E Hastings St (the City's 19-storey TOA application of 23 Feb 2026): 176 homes ran with tiers split for
  99 and the Community Housing Fund "failed" on the tool's arithmetic. With FSR 6.01 typed the tool now derives 170
  homes against the City's 176. `tests/test_suggest_fixed.py`. The FSR figure at 02 takes an FSR and writes the
  floor area (it opened a floor-area field under the word FSR). `bc.toa.minimum_density` has a 2026-11-17 version
  with the bus-exchange tiers 4 (12 storeys, 4.0) and 5 (8, 3.0), `verified: false` until B.C. Reg. 265/2023's
  schedule is read.
  A tower and plans that hold it (17 Nov 2026, second pass): above six storeys `massing.plate_dims` keeps a 21 m
  plate depth (PLATE_TOWER_DEPTH_M) and gives up width; `layout.solve` stands the core on the lane side of the
  corridor on a double-loaded plate (the street side's homes run past it) and, where the corridor is longer than the
  core and two 6 m dead ends, puts an exit stair at each end; `suggest.fit_to_plans` cuts the derived homes to what
  `homes_placed` (the layout's own solver on a bare massing) places, and the units' note says so. Funder-ready on a
  site with a recorded TOA tier is raised to the tier's storeys and FSR by the TOA rezoning path (`toa_tier`). On
  3475 E Hastings at the City's figures: 135 homes on a 32.8 × 21 m plate, all placed, exits pass on every floor
  (the City's 176 are smaller homes than BC Housing's minimums + 10%). On 998 E 19th Ave funder-ready now derives 99
  homes (the plate's), and exits pass with the end stairs. Stop 02's Continue waits while a figure is impossible
  (under 2.8 m a floor; a floor larger than the plate box): `figureProblems` in route-stage.js. `tests/test_tower.py`.
  Machine text out of the reading path (17 Nov 2026, third pass): the drawings' foot line is "Rules as of … · drawn
  from …, not a design / not a survey" (the stamp's hash stays in the ledger, as the UI dropped it); egress reads
  "4 exits, 2 required · travel 30.1 m, limit 45 m · separation …, at least 9 m" (`layout.egress_line`, answers.js
  `egressLine`); in Clauses applied a layer F row is the assumption's summary, the exits row (bcbc.exits) a sentence
  (`exitsWords`), and a `*_note` key never prints; `paramWords`/`param_words` move a mid-key unit ("max_height_m_
  outright") to the figure. FIG 02 draws each mass at its own footprint width and names the outright limit beside
  its storeys (`massing.outright_height_limit_m`, kept off the mass record so the committed massing.json compares).
  who.html's grid, stacked on a phone, drops its empty cells and labels each entry with its stage (`data-stage`).
  A scissor stair for a slim tower (17 Nov 2026): where the corridor is too short for a stair at each end, `solve`
  first lengthens the core until the corridor runs no further past it than a dead end may (any height: a 19-23.4 m
  plate had run 6-8 m dead ends), and above six storeys, where the core's stairs would stand closer than 3.4.2.3 asks
  (half the diagonal, not more than 9 m), runs it to that separation + one stair (11.2 m) as a scissor stair, its
  doors at the core's two ends (`stairs: "scissor"` on the core zone, kept through `zones_of`, `place_zones` and the
  block editor). Basis read from the Vancouver Building By-law 2014 text on bcpublications.ca, not yet BCBC 2024:
  3.4.4.4.(2)-(3) (a smoke-tight rated separation between the two stairs, no openings in it), 3.4.1.2.(3) (no
  contiguous stairs in a 5 or 6 storey wood-frame building, so only above six), 3.4.2.3.(3) (separation measured as
  smoke travels). The egress summary and FIG 05 say so. On 3475 E Hastings with no floor area typed (19 storeys,
  a 19.1 × 21 m plate): every floor passes, 48 homes against 55, since the 3.9 m left either side of the core on
  the lane side holds no home. `tests/test_tower.py` `SlimTower`.
  A point tower (17 Nov 2026, after the scissor stair): `solve` lays a compact tower plate out both ways, along a
  corridor (`_solve(..., None)`) and as a point tower (`_point_geometry`: above six storeys, no grid or architect's
  cores, sides within POINT_ASPECT_MAX 1.4 of each other, every strip at least `min_home_depth_m` 4.0 deep), and
  keeps the one that places more homes with exits no worse, the point tower on a tie. The point tower: a
  `core_bay_m`-square core at the centre holding a scissor stair, a corridor ringing it (four corridor zones), and
  the homes in four strips round that, the street and lane strips taking the corners (runs now carry `axis`,
  `edge`, `at`, `depth`; `_run_rect` turns a run's next length into a rectangle). egress() reads a scissor stair in
  a ringed core (`_ringed`) as doors on opposite faces, apart by half the core's perimeter as smoke goes round it
  (3.4.2.3.(3)): 14 m for 7 × 7. The plate record says `arrangement` ("double", "single", "point") with
  `side_depth_m` for a point tower; place_zones recognises an edited one. Homes per plate width (21 m deep, 19
  storeys, the default mix): 19.1-21 m the same both ways (the side strips beside the ring are too short for more than
  studios), 21.8 m 79 against 55, 23 m 91 against 66, 27 m 111 against 100; 3475 E Hastings with no floor area
  typed (19.1 m) stays a corridor plan with 48 homes. The homes are blocks of their area, so a shallow strip's home
  runs long along the facade (the plans say so).
- `ffm/lookup.py`: `lookup(address)` finds the point in the City's own `property-addresses` dataset first
  (`parse_address` turns "609 heatley" into civic number 609 and street "HEATLEY" for an ODSQL `like`; the
  record's `site_id` names the parcel, fetched by id) and only otherwise geocodes with Nominatim kept inside
  Metro Vancouver (`geocode_vancouver`: countrycodes, a bounded viewbox, a building preferred over a street,
  ", Vancouver, BC" tried second; without this "609 heatley" was a street in South Carolina and the full
  address once landed on the 300 block). The zoning district comes from `zoning-districts-and-labels` at the
  point and the parcel polygon from `property-parcel-polygons` (by `site_id`, else within 15 m with
  `pick_parcel` matching the civic number); `parcel_metrics` (pure) gives the area and an
  equivalent rectangle; `assemble` is pure so the browser build fetches and hands the records in. Since
  3 Nov 2026 it also fetches the surroundings around the parcel's centre and builds the site's `osm` block
  with `osm.build`: first from the City's own datasets (`public-streets`, `building-footprints-2009` with
  `hgt_agl` heights, `public-trees`; `city_records` pages them a hundred at a time in parallel threads and
  `city_elements` converts them to Overpass-shaped elements, about 2 s in all; the block's `source` and
  `attribution` then name the Open Government Licence – Vancouver), and only where the City has no streets
  from Overpass (half a minute). The figures draw the real context, and `street_bearing` (pure) takes the
  frontage as the parcel side parallel to the street the parcel is named for (OSM way matched by name, else
  the nearest road; 609 Heatley Ave: 37.2 m along Heatley, Keefer as the cross street). Overpass can take
  half a minute; the status strip says so. Tests in `tests/test_lookup.py` with the real parcel rings.
  Districts with no coded envelope (RT-3, CD-1) still show the storeys, height and GFA rows in the guide,
  set to Mine, so the manager can enter them and run. The suggestion's placeholder setbacks scale to the lot
  (`suggest.setbacks_for`: the committed 3.7 / 6.0 / 3.0 m capped at 12% and 20% of the depth and 8% of the
  frontage), and `massing.build` lays a plate smaller than the envelope at a usable depth (at least 12 m where
  the envelope allows, `PLATE_MIN_DEPTH_M`) giving up width instead, at the street corner the context frame
  names (`at_street_corner`); on 609 Heatley Ave (37.2 × 15.2 m, Keefer on the right) that turns a 5 m strip
  into a block at the corner. `tests/test_massing_shape.py`. `memo.markdown` prints "not given" for a blank site
  or option figure (`_n`) instead of failing on a `:,` format of None (`tests/test_memo_blanks.py`).
- CLI: `python -m ffm lookup "<address>" [--out]`, `python -m ffm suggest --site … --programs … [--candidate] [--out]`.
- Server: `GET /api/lookup?q=`, `POST /api/read-site`, `POST /api/suggest`, `GET /api/issues?site=`,
  `POST /api/runs/<site>/<folder>/issue` (writes `issues.json` in the run folder). The static build runs
  suggest and read-site in Pyodide and does the lookup's fetches in the browser; issuing needs the local server.
- The tool, manager mode: a "Start from an address" card at the top of the rail (`#guide`, `renderGuide` and
  the `guide*` functions in `app.js`) with six stops: find the site, choose the programs, read the site (the
  reading renders in the memo pane), shape the option (candidates; every figure Suggested | Mine with its rule;
  what is left to a person has its own control: Community Vision, transit area, bus stop, tenure, developer
  partner, site control), run, issue. A Summary | Detailed | 3D preview switch above the memo (`setView`,
  `renderPreview3D`: the plan with dimensions, the section and an orbitable axon, from the memo's own figure
  functions). "Issue to the architect" / "Issue to the board" in the Export bar; the page polls the local
  server every 15 s and shows an amber chip in the top bar for an issue addressed to the current role.
- Not built yet: hosting (phase 5). A restarted preview server is needed after editing `server.py`; the Claude
  app's preview does not reload Python.

## The manager's stage (11 Nov 2026): one way in, feedback per stop, cited money

- Manager mode opens blank: nothing loaded, stop 1 open. The demo case (998 E 19th Ave, as approved) comes
  only with `?run=`, `?tour=`, `?demo=1`, the "Load the demo case" button (`loadDemo`), or the architect and
  reader modes, which still land on it. `init()` decides (`wantsDemo`).
- Stop 1 is one way in at a time: "An address" (the lookup) or "A saved site" (`guide.way`); once a site is
  chosen the stop collapses to a line with "Change the site" (`guide.changing`). The Site and Option cards are
  hidden in manager mode until a site or an option exists (`syncCards()`, called from `refreshSummary`,
  `setMode`, `init`), so the guide and the cards never offer the same choice twice. Stop 4 offers the site's
  saved options in a select above "Or derive one from the rules".
- Before a run the memo pane is the stage (`renderStage`, routed from `renderQuiet` in manager mode; `STAGE`):
  one card per stop, the current stop marked, empty ones saying which stop fills them. 01 The site: the parcel
  on an OpenStreetMap map (Leaflet 1.9.4 from cdnjs, loaded only when a site is on the stage, OSM tiles with
  attribution; the parcel ring from `site.parcel.polygon_lonlat` when the lookup found one, else a marker at
  `site.lookup.center`), district, lot, street, owner, the "not sure" fields, the sources. 02 The programs:
  each chosen layer-E rule's `params` and `source` as the rule file has them (`server.list_rules` now returns
  `params` minus `observations`, and `source`). 03 The reading (A to C). 04 The option with its rule ids.
  05 The layer-F assumptions with their sources and the three figures that are the manager's. A signature
  (`stageSig`) stops a guide re-render from rebuilding the map for nothing; `renderSiteReading` defers to the
  stage in manager mode.
- The pro-forma's "Every line" table opens by default and its From column names the rule and links the
  source the ledger carries for it (title, section, URL); the option's own figures say so.
- Form rows (`.field-row`) wrap on narrow columns (`auto-fit, minmax(108px, 1fr)`) instead of squeezing three
  labels into 400 px; the (i) buttons sit on the label line.
- Architect mode: answers on top, then the drawings full width two per row (`[data-mode="architect"]
  .memo-body` / `.figures`), the plans sheet and the block editor spanning both columns, the ledger after.
- The committed Expo runs were regenerated on 11 Nov 2026 with the polygon massing (below); the 998 runs are
  unchanged (a rectangle). Browser-test runs (timestamp folders) are deleted before a commit, as before.

## The design review (15 Nov 2026): three UX critiques, two architects' tests, and what changed

`docs/design-review-2026-11-15/` holds the five reports and the evidence pack, and its README lists what changed
that day and what is still open. The engine changes a later session must know: a blank `site_control` or
`developer_partner` is uncertain, never a fail, and no finding prints a Python None (`tests/test_blank_answers.py`);
`checks.smallest_split` and the suggester say when a unit count cannot meet the fund's mix; `engine.summarise(results,
option, site)` returns `"not assessed"` for the outright verdict (and for by-rezoning outside the City of Vancouver)
with a `why`, and adds a `coverage.*` open item, when the stack has no schedule for the district or the site's
`municipality` is not Vancouver; `proforma.build(site, option, ledger, massing)` takes the floor area from the
massing when the option has none and says so; `massing.build` labels a mass drawn without a storey count as a
placeholder; `lookup.assemble` reads the municipality from the point and records `lookup.civic_mismatch` and
`lookup.outside_vancouver`; `server.list_issues(None)` lists every site's issues and `run_payload` carries `issues`.
In the page: the stage previews a found parcel before "Use this site"; `stageOption` shows the suggestion until it is
used (`guide.suggestionUsed`); `layoutOpenItems(run)` joins answer 3 and the paper; the paper has a money section;
`syncInputsTo` loads an unsaved site's inputs from the run; `focusKeyOf` keeps focus across guide re-renders;
`front_street` is a site answer that swaps frontage and depth on a corner lot; `scheduleFor(district)` says whether
the stack has a schedule; the rail's Run button carries `aria-disabled` until a site and an option exist.
The second pass the same day (the README in that folder lists it): `markStale`/`syncStaleBand` (a memo whose inputs
changed wears a band and Issue waits), `saveAs`/`saveNow` (an inline id field, no browser prompt), `saveDraft`/
`resumeDraft` (the guide and unsaved files in sessionStorage, "Resume where you were" on the blank stage),
`envelopeLive` (floor area and height derived under the Building group, "Use it"), `coverage.yards`,
`coverage.existing_buildings` and `coverage.heritage` open items in `engine.summarise` (the site field
`keep_existing_buildings`), the sheets and the block editor with the street at the bottom (`layout._plan`,
`svg_site_plan`, `renderEditor`), FIG 05 as tall as the section, `memoRefs`/`refOf` (A1 refs on screen) and the
reader's order by CSS `order`, the Side by side card's building-and-money table and two sections
(`run.compareProforma`, `compareLayout`, `compareMassing` from `attachCause`), `syncUrl`, `runLabel` with the run
date, the block editor's snapping/`freeSpot`/oversize flag, the boundary editor's edge table and "Set the site
area", the pyRevit script's levels and blocks from `layout.json`, and `.layout-sheet`/`.layout-wait` (the manager
sees the plans only once the architect has issued the run; `memo[data-issued-manager]`).

## The route and the stage (16 Nov 2026): the inputs rebuilt after an /impeccable audit

The audit that day (technical 14/20, heuristics 24/40; `.impeccable/critique/2026-11-17T04-06-13Z__ffm-ui-index-html.md`)
found the rail doing three jobs at once (a seven-stop accordion over a Site form of ~18 fields and an Option form of ~40)
while what each stop found landed in the other column. Kai confirmed `docs/ui-route-and-stage.md` and it is built:
- **One field list.** `FIELDS` in `app.js` holds every input once (`on`, `group`/`rowOf`, `type`, `need`, `reads` = the
  checks in `ffm/checks.py` that read it, `ref`, `info`, `ask` {stop, q, who, when}, `figure`, `money`). `SITE_FIELDS`,
  `OPTION_FIELDS` (`layoutOf`), `FIELD_META`, `GUIDE_FIELDS`, `FINANCE_FIELDS` and `ANSWERS` are views of it. A new input
  is one entry there; add its checks to `reads` so the schedule cites the right rules.
- **Manager:** the left column is the route (`renderRoute`, `#guide` is now a `nav.route`): three rows, 01 The site,
  02 The option, 03 Run, done rows carrying their decision. The memo pane is the stage (`renderStage`, `stageHtml`,
  `cardSite`, `cardOption`, `cardRun`, `wireStage`): one card, its input above what it found. `progress()` is the one
  source for what is decided (Run, the route, `syncRunButton`). Entering 02 reads the site and derives an option without
  a button (`enterOption`); the four-figure block edits `guide.mine` in place (`figureBlock`, `setFigure`); "All 21
  figures" keeps Suggested | Mine (`allFigures`); Continue applies the suggestion (`useSuggestion`, which replaced
  `guideUseOption`). The questions the open data could not answer are asked once, at 01 (`askTable(1)`: Community
  Vision, transit area and tier, water and sewer, owner type, buildings staying, land tenure, the front of a corner
  lot) and 02 (`askTable(2)`: developer partner, tenure, site control). After a run the route folds (`showInputs(false,
  false)`) and the memo takes the pane; a route row brings its card over the memo (`guide.over`, Back to R1). The map is
  kept across card renders by its `data-sig`. `guide.loading` became `guide.busy` {lookup, read, suggest, claude,
  schedule}; drafts carry `version: 3`, and an older draft's step 1–7 folds to 1–3 (`stopOf`).
- **Architect:** the left column holds the Site and Option schedules under two tabs (`#rail-tabs`, `setRailTab`,
  localStorage `ffm.rail.tab`): `renderForm` now draws Item | Value | Ref rows (`scheduleRow`, `controlFor`, `refsFor`);
  the Ref is the memo's own A1 count (`refNow`: before a run the engine's count over every rule in force, each layer
  by rule id, checked equal to a run's `memoRefs` on 36 rules). The (i) popovers, `labelHtml`, `renderField` and the
  Edit/Done collapse are gone. Claude lives here only (`renderClaude`, `wireClaude`: `#site-claude` at the Site
  schedule's head, `#claude-schedule-slot` under the district row when the rules have no schedule).
- **Chrome:** the step bar, `#guide-progress` and the walkthrough banner are gone (`--bars-h` 88px); the Walkthrough link
  ends the status line, dotted until seen. The manager's top-bar Run is hidden until a memo exists, then "Run again",
  live only when stale (`.btn-again`). The memo's action bar (`#export-actions`) moves into the title block
  (`placeActions`, called from `placeRunTools`; it must leave the memo before `#memo` is redrawn); Revit is hidden for
  the manager. Reader mode without a run shows "No memo is open" and the site's memos (`renderNoMemo`). Runs listed to a
  person are in revision order (`byRev`). The walkthrough has nine stops; `showTourStep` awaits a stop's `before`.
- Placeholders take `--muted` at full strength (5.8:1).
- The polish pass the same evening (the rest of the audit's list): `.issue-note` and `.stale-band` lost their 3px amber
  side stripe (a hairline and a wash all round); the 10.5px leftovers came up to the 11px floor; the export note has a
  68ch measure; a programme's terms (`dl.found-site.terms`) read in sentence case; the spinners hold still under reduced
  motion; coded values reach a sentence through `optWord(on, key, value)` (the field's own option label, so
  "non-profit society", never `non_profit_society`); `stagePrograms` prints booleans as yes/no; the run pickers list
  R1 first (`byRev`); the wordmark is the page's H1; the manager's Run again goes live the moment the memo is stale
  (`syncStaleBand` calls `syncRunButton`); the mode switch's thumb is re-measured by a ResizeObserver on the top bar;
  Leaflet loads with SRI (`LEAFLET_JS_SRI`, `LEAFLET_CSS_SRI`, cdnjs's own hashes); issue polling runs only while the
  tab is visible. `server.py`: static files carry an ETag and `no-cache` (an edit shows at once, an unchanged file is a
  304), and text (static files, API JSON, run files) is gzipped where the browser accepts it: app.js 421 KB → 126 KB
  on the wire. About 70 lines of CSS the rebuild orphaned (the seven-stop guide, the (i) popovers, the field rows,
  the old stage cards, `.answer-ctl`, `.sg-unsure`) are gone. Left by choice: ES modules (a separate piece of work),
  the 9.5px glyph in the status marks and the mode thumb's width transition (both in DESIGN.md), the chip's #ffe3a6.
- The 17 Nov 2026 critique's four tool P1s (`.impeccable/critique/2026-11-17T07-53-36Z__ffm-ui-index-html.md`):
  - **Edits after a run go stale.** A change at 02 after a run (a figure, "Use these three", an "All 21 figures" row,
    a new derivation) is applied to the option at once (`applyAfterRun` in route-stage.js, `useSuggestion({live:true})`
    in guide.js). So the memo is marked stale, Run again goes live and the route shows the new figures; the band waits
    for the memo while a card is over it (`syncStaleBand`). The replace guard now protects only an option the
    suggestion did not write (`guide.appliedOption`).
  - **Answer 3 at night.** `.answer[data-verdict="plain"]` takes `--panel`: `--paper` was never defined in the tool, so
    the card stayed white under light text. The map's zoom and tooltip take the drawing's `--c-paper` / `--c-drawink`.
  - **Impossible numbers.** The memo's Plate cell reads "no plate fits" instead of a negative width (`plateCell` in
    memo/memo.js), and the Height figure at 02 warns when the storeys at the floor-to-floor need more height.
  - **The route sticks.** `[data-mode="manager"] .inputs-body` is the sticky element (the route inside it was sticky
    in a box no taller than itself).

## The page as ES modules (16 Nov 2026): where each piece of the old app.js lives

`ffm/ui/app.js` (6,000 lines) is now native ES modules, still with no build step; `index.html` loads
`<script type="module" src="main.js">`. The code moved verbatim: every DOM id, storage key and URL parameter is as
before. Older sections that say "in `app.js`" mean the module below. Paths are under `ffm/ui/`:
- `main.js`: `init`, `followLink`, the error handlers. Nothing imports it.
- `core/`: `util.js` (`$`, `h`, `fmtNum`, `pill`, `setStatus`, `toast`, `getPath`/`setPath`, `copyText`); `state.js`
  (`STATIC` and the shared objects `state`, `guide`, `bnd`, `editor`, mutated in place, because a module cannot
  reassign another's binding; a top-level `let` stays in the module that writes it); `api.js` (`api`, `postJSON`,
  `staticApi`); `engine.js` (Pyodide and its shim); `lazy.js` (`loadPaper`, `loadBlocks`, `loadBoundary`, `loaded`).
- `fields.js` (`FIELDS` and its views, `optWord`, `cornerStreets`); `schedule.js` (the architect's schedules,
  `renderForm`, `refNow`, `syncCards`); `files.js` (site and option files, `saveAs`, `markStale`, drafts); `runs.js`
  (`runRules`, `openRun`, `applyCompare`, `rev`/`byRev`, `syncUrl`, `syncRunButton`).
- `route-stage.js` (the manager's route and cards: `renderRoute`, `renderStage`, `cardSite`/`cardOption`/`cardRun`,
  `wireStage`, `progress`, the Leaflet map); `guide.js` (`guideLookup`, `guideReadSite`, `guideSuggest`, `useSuggestion`).
- `memo/`: `memo.js` (`renderMemo`, `renderQuiet`, `renderNoMemo`, `placeRunTools`, `refOf`), `answers.js`,
  `clauses.js`, `ledger.js`, `side-by-side.js`, `changes.js` (What changed).
- `figures/`: `common.js` (palette, context, labels), `plan.js` (`figPlan`, and the boundary editor's handles and
  toolbar), `section.js`, `fig3d.js`, `cards.js` (`renderFigures`, `wireFigures`, the sheets, the mass placement,
  `renderPreview3D`).
- `revit.js`, `tour.js`, `issue.js`, `claude.js`, `modes.js` (`setMode`, `showInputs`, `setView`, the step strip).
- Loaded with `import()` on first use, so the manager's first load (28 modules) does not carry them:
  `editors/blocks.js` (the block editor), `editors/boundary.js` (its wiring and Use this boundary), `paper.js`
  (`paperDocument`, PDF, Print). Code that runs only while an editor is open calls it through `loaded`.

A new function goes in the module of the part it belongs to; import what it uses, and export it if another module
calls it. `tests/test_ui_modules.py` checks that main.js reaches every module, that every named import is exported,
and that the lazy modules are never imported statically. `server.py` serves the module folders (`MODULE_DIRS` in
`STATIC_PATH`). `pages.py` finds the modules from main.js (`module_graph`) and writes an import map that names each by
a hash of its own contents (`import_map`), so a deploy changes the URL of exactly the modules that changed and a
cached old module never runs beside a new one. One fix came with the split: `paperDocument` read its section
numbers before it declared them, so PDF and Print threw "Cannot access 's' before initialization" on every run with
money (the committed app.js had it too); the numbering now comes first.

Three defects found while testing the split, fixed the same day (none caused by it):
- Yards larger than the lot: `massing.build` clamps the equivalent-rectangle envelope at zero and warns which yards left no plate (609 Heatley Ave: RT-3's 20 m rear yard on a lot 15.2 m deep gave a -6.6 m envelope, a negative FSR in the memo and nine negative `<rect>`s per memo); `layout._plate` never takes a negative plate and the sheets' scales never divide by zero (`tests/test_layout.py`, `ShallowLot`).
- What the tool does when the yards leave no envelope (Kai's choice, 17 Nov 2026): `checks.district_setbacks` returns uncertain with `values.no_envelope` when the yards (at least the schedule's) leave no plate on the lot as fronted (`lot_as_fronted`). Its finding offers the corner lot's other street as the front with its numbers (`other_front`; offered, never switched), a lane behind, and the Director's variance (`affordable_variance`, s.3.1.2.21, an open item, never assumed). `engine.counts_outright` lets that result make the outright answer "not yet confirmed" (609 Heatley Ave read "yes" at FSR 0.60 with no plate). The suggester lists the same words as its `yards` item. RT-3's lane clause (`rear_yard_lane_reduction`, s.3.1.2.17) takes the distance to the lane's centre line off the rear yard where `site.context.lane_behind` is true: `context.lane_to_centre_line_m`, else `checks.LANE_TO_CENTRE_LINE_M` = 3.05 m (half a standard 6.1 m lane, a declared placeholder). The page asks "A lane behind the lot?" at 01. The page's "Which street is the front?" now sets `site.front_face {street}` instead of swapping frontage and depth. The swap had left the parcel polygon 11 m off the envelope. `boundary._road_frontage` counts a road only within 45° of an edge's normal, so `front_face {"street": "Keefer St"}` turns the lot (`tests/test_suggest.py`, `YardsLeaveNoEnvelope`).
- `paperDocument` (`paper.js`) prints "3 Compared with…" before "4 The money", as numbered; the template had them the other way round. Refs (A1…) unchanged.
- Static build: `loadStaticRun` (`core/api.js`) asks for `diff.json` only when `data/runs.json` lists the run with `has_diff`, so a base run logs no 404.

## The lot as a polygon (11 Nov 2026): odd sites, the parcel survey, the boundary editor

- `ffm/parcel_shapes.py` (written by a survey agent, reviewed): shape metrics and a class for one parcel
  polygon (rectangle, near_rectangle, trapezoid, l_shape, flag_lot, irregular, multi_part), a `confidence` from
  nudged re-runs and an `alternative`. `evals/parcels/` holds the survey of all 99,680 City parcels
  (`shape-survey.json`: 89.7% rectangles, 3.4% irregular, 2.0% trapezoids, 0.2% L shapes, 41 flag lots, 2
  multi-part; its README has the thresholds and what surprised the survey), `uncertain.json` (the 40 parcels
  the classifier is least sure of, thumbnails included, `label` and `labels_by` null for a person; since 12 Nov
  2026 every one is a taxable lot with an address, checked against the City's tax report, zoning and parks
  datasets and the rapid-transit lines and stations, so parks, rights-of-way, strata plans, air-space parcels,
  station land and untaxed remnants are kept out; the eighteen the first set held are listed in the file and the
  README), and
  `label.html` (built by `make_label_page.py`: a page to label them in a browser and download labels.json; the
  draft in the browser is keyed by site_id, so labels made before the refill carry over).
  The 53.6 MB export and the fetch/survey scripts stay outside the repository; the README says how it was run.
- `ffm/boundary.py`: `lot_ring(site)` gives the lot's outline in the lot frame from `site.boundary_m` (drawn in
  the tool) or `site.parcel.polygon_lonlat` placed in the site's context frame (`osm.center`, `frame.
  x_axis_bearing_deg`, `snapped_m`, reconstructed as `osm.build` made it) or, without a frame, turned so the
  frontage runs along x with the street side assumed. `inset(ring, setbacks)` moves each edge inward by its
  kind (front faces the street, rear faces away, side otherwise), dropping edges that collapse (acute tips,
  short edges); `largest_rect(polygon)` finds the plate box on a 0.5 m grid, a cell counting only when inside
  at its top and bottom edge so the box never overhangs a slanted line. `tests/test_boundary.py`.
- `massing.build`: with a ring, `lot` carries `polygon` (the ring), `corners` (simplified, what a hand would
  draw), `bbox`, `source` (parcel | drawn), `frame`, `polygon_area_m2`, `shape` and `note`; `envelope` is the
  inset polygon with `box` {x, y, w, d, area_m2}, and the masses stand in the box (`plate_cap` = its area, a
  warning when the plate exceeds it). A polygon area more than 5% off the recorded site area is a warning
  (1010 Expo: the parcel is 2,690 m² in the context frame against the 3,908 m² the application implies; the
  site file now carries the City's ring and says so). Rectangular sites are unchanged (no `bbox`, no `box`).
  `massing.svg`, `layout.svg_site_plan` and the UI's FIG 01, FIG 02 and the 3D view draw the polygon, the
  envelope and the dotted plate box on the polygon's own extent.
- The lookup records `parcel.shape` (class, note, confidence) for a found parcel; the manager's stage says it
  on the Lot line.
- The boundary editor (architect mode, FIG 01 plan, `bnd` in app.js): "Edit boundary" puts handles on the lot's
  corners (`lot.corners`); drag moves one, a square on an edge adds one, Delete removes the selected, the arrow
  keys nudge 0.5 m; "Use this boundary" writes `site.boundary_m` (site dirty, Save site as… keeps it) and
  rebuilds the massing, the layout and the sheets through `POST /api/layout` (`rerenderFigures`); "Back to the
  parcel" clears it. The next run reproduces the drawn lot and the memo says "boundary drawn by hand". The
  handles are wired to the SVG each time it is refitted (`wireBoundaryCanvas` from `fit`), because a refit
  replaces the element.
- Labelled (15 Nov 2026): `evals/parcels/labels.json` is Kai's pass over the 40 (33 classed, 4 "other", 3 blank,
  39 frontage edges). `score_labels.py` and `score_frontage.py` beside it score the classifier and the frontage
  rule; the labels moved the near-rectangle line to 0.88 and added the five-cornered convex trapezoid (8 → 21 of
  33 right; the frontage rule 35 of 39, the four misses corner lots where Kai put the front on the other street
  with nothing in the geometry to say so, so `lookup.street_bearing` now names the `cross_street` of a corner
  lot and the site's notes ask which side is the front). `uncertain.json` is frozen as the labelled set. The L
  rule is not settled by the labels (one of ten L guesses confirmed). Which of 2,712 and 3,908 m² is the Expo development
  site is a question for a person.

## The block editor rebuilt (17 Nov 2026): a grid, the program beside the plate, a suggested plan, linked cores

Kai found the editor clunky; `editors/blocks.js` was rewritten (the section below describes the first version).
- **Grid.** `option.layout.grid` {bay_m, divide}: the bay is wall to wall (6, 7.5, 8 m or 3 to 12), `divide` 1, 2 or 4
  (walls on whole, half or quarter bays), counted from the plate's left edge (`layout.grid_of`; the plate record
  carries `grid`). With a grid `layout.solve` gives a unit the nearest whole number of modules that keeps it at or
  over the BC Housing minimum with partitions (`min_gross_m2_each` on a program block), else the next module up;
  `place_zones` then reads `undersized` against that minimum, not the gross. `option.layout.cores` [{x, y, w, d}]
  stands the given cores on every floor and the runs go round them. Neither key: the layout of 3 Nov, unchanged.
- **Editor.** The program (`programHtml`, `programTracker`) sits beside the plate with placed and left to place; a row
  is dragged onto the plate (`placeAt`: the strip under the pointer, the nearest free place on the module) or clicked
  (`freeSpot`). A press on a block selects and drags in one gesture; walls go to a neighbour's wall within 0.4 m, else
  the module; a block dropped on the program is removed. Any change to a core is copied to every floor (`syncCores`,
  through `commit(core)`). `suggestPlan` asks the engine for a plan on the grid, round the cores once one was moved
  (`editor.coreMoved`); the editor opens on one when the option has no zones. Undo (`snapshot`, Ctrl+Z), Repeat this
  floor above, Clear the plates (cores and corridors stay). Apply writes `layout.zones` and `layout.grid`. A check's
  redraw waits for a drag to end (`editor.dragging`, `pendingRender`), and stale replies are dropped (`editor.seq`).

- **Changing a block's program, adding a level (same day).** The selection line's name is a select (`#ed-kind`): the
  block becomes another program where it stands, a unit taking that unit's width on the grid. `layout.capacity(site,
  massing, outright)` (in every layout record as `capacity`) gives the FSR room: against the rezoning policy's benchmark
  FSR where one fired, else the outright maximum, `fsr_limit` None with neither; `levels_room` is how many more plates
  fit (998 E 19th Ave what-if: FSR 2.49 of 3.0, one level). "+ Level" (`addLevel`, live only with room, or with no limit
  in the rules) adds a storey with the cores and corridor of the level under it; `withLevels` sends storeys, a plate more
  of `gfa_m2` and `residential_gfa_m2` and a floor more of `height_m` with every check, so the plate stays; Apply writes
  them into the option, redraws the Option schedule and marks the memo stale. Committed `layout.json` files predate
  `capacity`; the editor reads it from its first check.

- **Two fixes the same day.** (1) The boundary editor on a lot turned to a chosen front (`site.front_face`): the
  handles are in the turned frame the plan is drawn in, `site.boundary_m` is kept in the frame as found, so
  `editors/boundary.js` turns a saved ring on the way in (`toShown`) and back on the way out (`toStored`, the inverse of
  massing's `lot.orientation`; `boundary.unapply_orientation` is the engine's twin). Before, the shown ring was saved as
  it was and turned a second time: the lot jumped on Use this boundary. A boundary saved by the old code is wrong in the
  site file; "Back to the parcel" clears it. `tests/test_boundary.py`, `DrawnOnATurnedLot`. (2) Plans by program has a
  floor picker (`planFloor`, `floorPlanHtml`, `refreshPlanFloor` in `figures/cards.js`): Overview is the engine's sheet
  (ground, typical, top), any other button draws that floor from `layout.floors` in the page; the block editor's checks
  redraw it and write the sheet into `.plans-overview`.

- **The architect's own blocks, the plate's shape, the site behind it (17 Nov 2026, later).** Three block kinds no
  program asks for (`layout.EDITABLE_BLOCKS`): `design_space` (a lobby, an atrium), `commercial`, and `void` (a cut-out:
  open to below, a notch, a courtyard). They are measured and drawn, never short; a `void` is not floor area, so it
  comes off the floor area `layout.capacity` reads the FSR on (`void_m2`) and is never spare. Commercial is not counted
  toward `non_residential_gfa_m2`. The plate: `option.massing.width_m` / `depth_m` (`massing._given_plate`) set its
  dimensions, kept inside the plate box with a warning; without them the plate is GFA over storeys as before. In the
  editor: Plate W × D inputs and two dark handles on the plate's right and far edges (`setPlate`: width to the module,
  depth to 0.5 m, the program laid out again, cut-outs that still fit kept by `suggestPlan`), `withPlate` sends the
  dimensions and the floor area they give with every check, and Apply writes `massing.width_m/depth_m` and
  `gfa_m2` = plate × storeys less the cut-outs (a cut-out pins the plate's dimensions first). A plate is still a
  rectangle everywhere (massing, sheets, Revit): another shape is that rectangle with cut-outs. The canvas draws the
  site behind the plate (`viewOf`, `contextSvg`, from `figures/common.js` `siteContext`): streets, neighbours, trees, the
  property line dash-dot, the setback envelope red; the "site context" box (localStorage `ffm.ed.context`) puts it away
  and the plate fills the canvas again.

- **North up (17 Nov 2026, Kai: "plan needs to show north as up always").** FIG 01's plan (`figures/plan.js`) and the
  block editor's canvas are still drawn in the lot frame (the street along x) but turned as a whole so north is up the
  page, wherever the context gives the bearing of the x axis (`ctx.osm.bearing`): `turnOf`, `turnFrame` and `upright`
  in `figures/common.js` (the rotation, the larger frame and the `.plan-turn` group, and labels kept readable). The
  scale bar and the north arrow stay level. Pointers are read in the turned group's coordinates (`loc` in the block
  editor, `toLot` in the boundary editor). A site with no context frame has no bearing and stays street-down. The
  engine's own sheets (the Plans by program overview, the code site plan, the PDF's figures other than FIG 01) are
  still drawn with the street at the bottom, as are the floor picker's plans.

- **Turning the mass (17 Nov 2026).** `option.massing.angle_deg` (counter-clockwise in the lot frame, about the plate's
  centre; `massing._given_angle`, `_turn`) turns the proposed mass on the lot by any angle; the older `rotate` flag is
  still the quarter turn that swaps width and depth. The mass's `footprint` is then the turned outline (FIG 01's plan,
  the 3D view, `massing.svg`, the code site plan and the Revit masses draw it), with `angle_deg` and `plate_origin` (the
  plate's front-left corner before the turn); the plate and every block on it stay in the plate's own frame
  (`layout._plate` reads `plate_origin`, the layout's `plate.angle_deg` says it is turned), so a turn moves no block.
  Nothing is clamped: corners past the setback envelope are a massing warning. In the block editor: Turn ⟲ [°] ⟳
  (`setAngle`, 15° a click), the plate, grid and blocks in one group (`.ed-mass-turn`) turned over the site context,
  pointers read in that group; Apply writes the angle. FIG 01's "Place the mass" has a Turn (°) box and no longer drops
  the plate's `width_m`/`depth_m`. Not turned: the Plans by program sheets and the floor picker (the plate's own frame,
  by design), and the Revit script's floor blocks from `layout.json` (the masses turn, the blocks do not yet).

- **Five fixes from a three-architect run of the block editor (23 Nov 2026; a simulated review, on 998 E 19th Ave).**
  (1) `layout.capacity` also carries `height_m`, `height_limit_m` (the benchmark's upper height where the policy fired,
  else the outright maximum), `height_from` and `height_with_one_more`; the editor says an FSR or height overrun under
  the plate (`oversOf`, `.ed-over`), in the plate and add-level status lines and on the + Level tooltip. Nothing is
  blocked. (2) `commercial` zones count toward the non-residential program (`place_zones` shortfall, `_check`, the
  editor's `programTracker`). (3) The editor's grid defaults to quarter bays (`editor.divide` 4), so a studio is 4.5 m
  and a one-bedroom 6 m on a 6 m bay; a unit's program row shows the area it is drawn at. (4) `place_zones` adds one
  `no_elevator` geometry problem where a building over `WALKUP_MAX_STOREYS` has a floor with no core at least
  `ELEVATOR_CORE_M` (5 m, a declared placeholder) wide and deep. (5) A block added by click or Enter with no free place
  is not added (it used to land on the front-left corner over what stood there). Still open from that review: stepped
  massing, unit depth and daylight, naming and typing a block's size, copy and mirror, the editor closing on Run, the
  plate drifting after Auto with an added level, "Suggest a plan" in messages against the "Suggest a grid plan" button.

- **The rest of that review (23 Nov 2026).** (a) *Stepped massing.* The editor's "Step back the upper floors" (`setStep`,
  `rebuildSteps`, `editor.steps`: one entry {from_level, front, rear, left, right}) draws the step as cut-outs marked
  `step` along the named sides of every floor from that level up, shortens those floors' corridors (the zone keeps its
  own length in `full`), and takes the blocks standing in a strip off (back to the program). New blocks on a stepped
  floor are sized for the shallower strip (`bandsOf` gives `frontD`/`rearD`, `fitBand`). Apply writes
  `option.massing.steps`; `massing.build` then gives the proposed mass `tiers` (each its own outline, turned with the
  mass), which the 3D view stacks (`fig3d.js`). The floor area a step takes off is the cut-outs', so the FSR follows.
  The section, the elevations and the Revit masses still draw the unstepped box. A side step that meets an end stair
  is an overlap for the architect to resolve (the cores are the same on every floor). (b) *Daylight.* `layout.daylight`
  (in every layout as `daylight`): homes deeper than `UNIT_DEPTH_MAX_M` (10 m, a declared placeholder) from their
  window wall, and homes with no wall on a plate edge or a cut-out; conditional, never a failure; a note in the
  layout's warnings and a line under the plate. (c) A block takes a `name` (kept by the engine, drawn on the plans) and
  a typed width and depth. (d) Duplicate (Ctrl+D) and Mirror this floor (cores stay). (e) A re-rendered memo reopens an
  open editor on its floor in architect mode (`editor.resume`, `openEditor(resume)`). (f) Auto returns to the plate
  there was before one was set (`editor.base.auto`), so an added level no longer carries a stale plate. (g) Messages
  say "Suggest a grid plan", as the button.

- **Unit widths and proportions (23 Nov 2026; figures Kai accepted as placeholders).** `layout.UNIT_MIN_WIDTH_M` (studio
  4.0, one-bedroom 5.5, two-bedroom 7.5, three-bedroom 9.5 m along the window wall) and `UNIT_DEPTH_RATIO_MAX` (2.5: a
  home at most that many times as deep as wide). The solver's `unit_width` never sizes a home under either, with or
  without a grid (a walk-up's through homes are exempt); a program block carries `min_width_m`; the editor's `unitW`
  does the same. `layout.proportions` (in every layout as `proportions`) counts homes drawn narrower or more slender by
  hand: conditional, a note in the warnings and a line under the plate, never a geometry failure; the selection line
  says it for the block in hand. This changes the memo's own plan on deep plates (strips over about 10 m), so committed
  runs on such plates differ from a fresh run until they are regenerated. A home drawn by hand narrower than its minimum is also a `narrow` geometry problem in `place_zones` (it counts in Apply and in the memo's open item), the depth ratio stays a note. Of the committed runs only `375-glen-drive/as-proposed` and `375-glen-drive/first-run` hold homes under these widths (strips of 11.85 and 11.06 m); `as-proposed` was regenerated the same evening with the rest of the tree (a fresh run matches it file for file: studios 4.74 m, one-bedrooms 5.5 m, two-bedrooms 7.5 m, three-bedrooms 9.5 m, 144 of 163 homes); `first-run` is that site's frozen first revision under the earlier rules and is left as it was made. On a strip past 12.5 m the depth ask alone
  makes a studio as wide as a one-bedroom; the daylight note says the plate is too deep.

- **More of the block editor's open list (23 Nov 2026, late).** A block's `name` is carried onto a fresh plan's nearest
  block of the same kind on the same floor (`suggestPlan`). "Fit the plate to the turn" beside the turned-mass warning
  (`fitTurned`): the largest plate of the present proportions that stands inside the setback envelope when turned, at
  the middle of the plate box (`editor.anchor` = "centre", written as `option.massing.anchor`; a plate against a corner
  of the envelope puts a corner out at any angle). "Export DXF" (`dxfOf`): every floor's plate and blocks as closed
  polylines, a layer per block kind (`FR-…`), names and areas as text, metres, the floors side by side; made in the
  page from the editor's own state, so it needs no run. FIG 02's section cuts a stepped mass tier by tier
  (`figures/section.js`). The floor picker's plan is north up (`floorPlanHtml`: the site's bearing less the mass's own
  angle). Real mouse drags on the turned, north-up canvas were tested (a block dragged off onto the program, a studio
  dragged on). Still open: shadow and separation distances; a column grid in both directions and the parkade; the
  elevations and the Revit script for a stepped or turned mass (the Revit script cannot be tried without Revit); more
  than one step-back; comparing massing options inside the editor (runs compare in the Side by side card).

- **The last of the block editor's open list (24 Nov 2026).** *Step-backs:* `editor.steps` holds one a level (`stepAt`
  gives the deepest inset a side at a level; the form adds or replaces, each has Remove); the elevations draw a stepped
  floor in from the face below (`layout._step_insets`, from the cut-outs marked `step`). *Options to compare:* "Keep as
  an option to compare" stores the plan with its plate, turn, steps and levels (`editor.variants`, for this site and
  option, in the page only) and a table sets them beside what is on the plate now; Restore brings one back. *Shadows
  and separation:* the "shadows" box draws the mass's shadow at the equinox at 10 am, noon and 2 pm daylight time
  (`shadowsOf`: one box of the full height on flat ground, Vancouver's hour angles, the site's latitude; a first
  reading, not the City's shadow study); the status line gives the distance to the nearest neighbouring building and
  lot line (`ringGap`). *Structure and parking:* the canvas draws the grid across the plate too, with a column where
  the bays meet, and a "Parkade, a first count" line (stalls at the layout's 30 m² each, the levels that takes under
  what the setbacks leave, a 24 m ramp a level at 12.5%, stalls a bay at 2.6 m): placeholders, nothing is checked
  against them. *Revit:* `revit/ffm_massing_pyrevit.py` builds a stepped mass tier by tier (and its floor plates on
  the tier's outline), turns the floor blocks with a turned mass, names a block by its `name`, and builds nothing for a
  cut-out; it compiles, and has NOT been run in Revit since: run it on a stepped or turned scheme before relying on it.
  A lane-side step-back meets the cores where they stand on that edge, an overlap for the architect to resolve.

- **Project north, and FIG 01's two switches (24 Nov 2026).** Kai: a plan turned to true north stood 1.6° off the page
  on 375 Glen Drive and "looks weird"; "the plans should always show project north". `projectTurn(bearing)` in
  `figures/common.js` is the quarter turn nearest true north: FIG 01's plan, the block editor's canvas and the floor
  picker's plans are turned by it, so the building stays square to the sheet, and their north arrows show true north
  tilted by what is left (`northArrow(.., bearing - turn, ..)`). This replaces the true-north-up of 17 Nov. FIG 01's
  head has two switches, held in `VIEW3D` and read by both its views: **Shadows** (`sunShadows`, `massParts` in
  `common.js`: the equinox at 10 am, noon and 2 pm, the stepped mass tier by tier, on the ground in plan and in the
  axonometric; a first reading) and **Program** (the axonometric draws every floor's blocks as boxes in their tones in
  place of the plain mass, turned with it, the outright mass left out so the colours show; the plan draws the ground
  floor's blocks; a key under the drawing). `BLOCK_TONE` / `BLOCK_WORD` in `common.js` are the tones and words. The
  editor's shadows use the same function.

## Phase 4 (3 Nov 2026): the block editor over the solver

- Engine: `layout.solve()` returns `place_zones(...)` when the option carries `layout.zones` ({"0": [{block, x,
  y, w, d, accessible?}], "1": …}): nothing is moved, every zone is measured (area, side), the rules are read
  back as before, and `geometry` lists what broke (`outside` the plate, `overlap` between zones other than
  corridor × core, `undersized` unit under its gross area, `no_corridor`, `no_core`, `bad_zone`); `shortfall`
  is the program still lacking, extra units a warning. `edited: true`, `derived_from` names the zones, the
  memo section says "Placed by hand in the block editor"; `zones_of(L)` is the solver's placement in that form.
  `tests/test_layout_editor.py`.
- Server `POST /api/layout` {site, option, as_of} → {layout, sheets, massing} (nothing written); the shim's
  `ffm_layout` does the same in Pyodide, so the editor works on the web too.
- Tool: "Edit blocks" on FIG 03, the architect's tool: always rendered, hidden in manager and reader modes by
  CSS (`[data-mode="manager"] #edit-blocks`), so a mode switch after a run shows or hides it without a
  re-render (a JS gate at render time once left the architect without it); leaving architect mode closes an
  open editor; the figure head wraps so the button is not pushed out of the 400 px column (`openEditor`,
  `renderEditor`, `wireEditor`, `checkPlacement`,
  `applyEditor`): floor buttons, Add a block, the plate as an SVG canvas; click selects, drag moves, the right
  and bottom handles resize, arrows move 0.5 m (shift 2 m), Delete removes; "to floor" moves a block; a unit
  can be marked accessible. Every change is debounced 350 ms into `/api/layout`; the status lists what broke
  on this floor and the counts; the axon, stacking, elevations and site plan redraw from the same check. "Apply
  to the option" writes `state.option.layout.zones` (dirty, saved with the option; Run the rules reproduces it);
  "Back to the solver's" clears it. The plate's edges clamp the drag; the engine still reports `outside` for
  zones that arrive by file.

## Phase 3 of the workflows proposal (3 Nov 2026): the architect's first layout

- `ffm/layout.py`, standard library, deterministic. `blocks(option, ledger)`: units by type at the BC Housing
  minimum net areas (layer D) plus the suggestion's 10% design allowance and an 8% partition allowance
  (`LAYOUT_ASSUMPTIONS`, declared); non-residential from the option; amenity 1.5 m²/unit (at least 40 m²);
  services 40 m² plus 1 m² per bicycle space; parking 30 m² per stall below grade, reported not placed.
  `ADJACENCIES`: seven rules in plain words (non-residential on the ground floor facing the street; amenity on the
  ground floor by the entry; services on the lane side; one core bay at the centre; units both sides of the
  corridor; three-bedroom units lowest; accessible units nearest the core), overridden or extended by
  `option.layout.adjacencies` (matched by id). `solve(site, option, ledger, massing)`: the proposed mass's plate
  (`plate_width_m` × `plate_depth_m`, `storeys`) gets a 1.8 m corridor and a 7 m core bay per floor and four runs
  (front/rear × left/right); the ground floor takes the other uses first (a hall may run through to the lane);
  every unit is placed whole in the first run with room, family units bottom up to studios at the top, the
  accessible ones first; what does not fit goes to `shortfall`, never squeezed; spare run length is drawn white.
  `adjacencies` are read back from the zones as pass / conditional / info with a note. A plate under 9.8 m deep
  is single-loaded and says so. `L["outright"]` carries the schedule's maximum FSR and height for the elevation.
- Five sheets as SVG (`svg_stacking`, `svg_plans` with the ground, a typical and the top floor, `svg_elevations`
  front and side with a window per unit, `svg_axon` oblique stacked floors, `svg_site_plan` with the yards
  dimensioned, the envelope, the footprint, tree barriers where `site.context.trees` has positions, and a
  table against the schedule); `sheets()` returns them, `write()` puts `layout.json` and the five beside the
  ledger; `markdown()` is the memo's "Layouts derived from the option" section (`memo.html_page` now inlines
  any SVG in its `svgs` dict). `python -m ffm run` writes them; the server's `do_run` and `run_payload` carry
  `layout` and `sheets`; the static build runs the solver in Pyodide (`ffm_run` returns them) and fetches the
  files for committed runs. The tool shows FIG 03 Plans by program (Plan | Axon tab) with the rules as a list,
  FIG 04 Stacking, FIG 05 Elevations, FIG 06 Code site plan (`renderSheets`, `wireSheets`); the Revit sheet
  numbers after them; the paper memo has Figures 3 to 6. Tests in `tests/test_layout.py` (overlaps, counts,
  rules, SVG well-formedness, determinism, an override, the shallow corner lot).
- Flow fixes from the 3 Nov audit of all three modes: in manager mode the four step links give way to the
  guide's own progress (`#guide-progress`, "Stop n of 7 · title · k done"); the guide's stops are now 5 Money in
  (land, equity, other grants, before the run) → 6 Run the rules (the four answers as a list, Run again) → 7
  Issue, so one run answers everything; after a run on a stacked (≤1100 px) window the page scrolls to the memo;
  the architect's forms start folded on a stacked window; the export bar shows four actions and folds the
  three file formats behind "More formats"; the key box and the proposal box lost their 3 px side tab (a
  hairline and a faint amber wash instead); stop heads and inputs reach 40 to 44 px under a coarse pointer.

## Phases 2 and 6 of the workflows proposal (3 Nov 2026)

Phase 2, the cost layer and the pro-forma:
- `rules/f_assumptions.json` is **layer F**: seven dated, cited assumptions with the check `assumption`
  (always `info`; the ledger carries them, the stamp covers them, `engine.LAYER_ORDER` ends in F). Hard cost
  base $4,693/m² from the Province's Class D estimate for its standardized designs (Aug 2024; the catalogue is
  2- to 4-unit wood frame, so the source's `verify` says a six-storey figure should replace it); escalation
  from Statistics Canada table 18-10-0289-01 (Vancouver, residential, division composite, 2023=100; the
  observations sit in the rule params and are kept out of the ledger values); soft costs 25% and contingency
  10% (placeholders, `source.placeholder: true`); land nominal where the owner is a church, a society or a
  government, else entered; the Bank of Canada conventional 5-year rate (6.19%, series V80691335) with CMHC MLI
  Select's 1.10 coverage ratio and a 40-year amortization; CMHC rents (October 2025 survey: two-bedroom $2,363,
  all units $1,963, vacancy 3.7%; the other bedroom types are null until typed from the data tables), RGI at
  30% of an income taken at half the fund's limit (placeholder), the $500 shelter rate; operating $6,500 and
  reserve $600 per unit (placeholders). Nothing in it is invented silently: a placeholder says so in the memo.
- `ffm/proforma.py`: `build(site, option, ledger)` is arithmetic over layers F and E read from the ledger.
  Capital = hard × escalation + soft + contingency + land; the escalation uses the last quarter published by the
  run date (`BCPI_PUBLISHING_LAG_DAYS` = 120, so a memo as of 23 Oct 2026 uses the second quarter's index);
  revenue by tier from `rent_tiers_units`; NOI less vacancy, operating cost and reserve; funding = the CHF
  provisional grant (when targeted) + `option.finance.equity_cad` + supportable debt (NOI over the DCR at the
  mortgage constant); the gap; a verdict **likely / unlikely / unsure** (gap ≤ 0; gap above 15% of capital,
  `GAP_UNLIKELY_SHARE`; or a missing land price, floor area or an assumption not in force). `lines` carry every
  figure with its rule id, note and placeholder flag. `markdown(pf)` is the memo's section "4. Does the money
  work? (feasibility grade)". The option's `finance` block (land_cost_cad, equity_cad, other_grants_cad) is the
  manager's; the Option form has a Finance group. The real funder-ready what-if reads unlikely: $45.7M capital,
  $25.4M funding, a $20.3M gap. `tests/test_proforma.py`.
- `python -m ffm refresh [--write]` (`ffm/refresh.py`): fetches the StatCan series through the WDS
  (`getDataFromCubePidCoordAndLatestNPeriods`) and the Bank of Canada Valet series, reports moved / current /
  unreached, lists what is by hand (the Class D PDF, the CMHC tables, the placeholders), and with `--write`
  appends a new dated version (never edits one). `plan()` and `apply()` are pure; `tests/test_refresh.py`.
- `python -m ffm proforma --site … --option … [--as-of] [--json]` prints it; `run` writes `proforma.json`
  beside the ledger and the memo picks it up; the server's run payload and the static build carry `proforma`.
- The tool: a fourth answer card "Does the money work?" (`answerMoney` in `app.js`; verdict, the four lines,
  "Every line and its source" folded) in Summary and Detailed; the paper memo's answers table gets a row; the
  guide has **seven stops** (6 is Pro-forma: the five lines from the run, the three finance inputs, "Run again
  with these"; 7 is Issue).
- The money's words (17 Nov 2026, Kai): the key `verdict.word` stays likely / unlikely / unsure in `proforma.json`,
  but nothing a person reads says "Unlikely" any more. `proforma.VERDICT_WORDS` shows "unlikely" as **Needs more
  sources** and `proforma.next_step(pf)` adds a line for the development manager (more sources as well: other grants
  with CMHC's Affordable Housing Fund named, equity, a land contribution, a partner; then enter them and run again;
  for an "unsure" gap inside 15% with the land settled, "another source, or firmer placeholders"). The tool mirrors
  both (`MONEY_WORD`, `moneyNext` in `memo/answers.js`; the paper memo uses them) and the card reads
  `conditional`, no longer `fail`. The committed memos were rewritten with `python -m ffm memo --out <run>` (the
  ledgers untouched); home, case, how and who say "Needs more sources". An option with a floor area but no homes
  entered reads **unsure** ("no homes entered, so there is no rent, debt or grant to set against the capital cost",
  the unit mix left to a person) before any gap is read, and gets no next step: Expo as permitted had read a 100%
  gap as "unlikely". Its committed `proforma.json` was rebuilt from its own ledger and massing (only the verdict
  moved; the other six runs rebuild unchanged).
- The architect's money folds (17 Nov 2026, Kai: "too long … more of a developer's thing"): answer 4 keeps its
  verdict and puts the next step, the four figures, the reasons and the line table behind "Show the pro-forma ·
  capital, funding, gap" (`details.money-more`); the choice is kept (`ffm.architect.money`) and ledger layer F
  opens and folds with it (`wireMoneyFold`, `applyModeToMemo`). The line table is folded in every mode now.
- What changed folds the rules that apply to neither run (17 Nov 2026, Kai; `naChange` in `memo/changes.js`: every
  status present is not applicable): between the two Glen Drive runs 52 of 61 rows were districts added since. They
  sit in one `na-fold` row at the foot of the table; a status moving to or from not applicable (family units, fail →
  not applicable) stays in view. `changesPhrase` and the paper memo's comparison count and list the same way.
- Day or night by hand (17 Nov 2026): `#theme-btn` at the end of the top bar, `initTheme` / `setTheme` in
  `modes.js`, `ffm.theme` in localStorage applied by a one-line script in index.html's head; app.css repeats the
  night tokens under `:root[data-theme="dark"]` (brand.css already did for the statuses). The site pages stay dark.

Phase 6, Claude in the loop (the model proposes, a person confirms, the engine decides):
- `ffm/propose.py`, behind `FFM_CLAUDE_KEY` in the environment (never in the repository; `available()` is what
  the server reports at `GET /api/capabilities`; without the key every call raises `NoKey`). The official SDK is
  imported lazily, so the engine and tests stay standard library: `uv run --with anthropic python -m ffm
  propose …`. Model `claude-sonnet-5-5` as the proposal chose for extraction, `FFM_CLAUDE_MODEL` overrides.
  One strict tool per job (`propose_rule_clauses`, `propose_site_facts`): a list of items {key, value,
  confidence, evidence, section, page}; the beta Messages endpoint with `fallbacks: "default"` where the SDK
  knows it, the plain one otherwise; a `refusal` stop raises `Refused`, never silently empty. A PDF goes as a
  document block (cached), an image as an image, text inline.
- `propose_rule(document, district, url)` → a proposal with `source: "claude"` on every item and the call
  logged (model, date, prompt hash, usage, the document's name and sha256, never its bytes); `clauses_from`
  turns the items into engine rules: `cov.<district>.outright_fsr` (`district_outright_fsr`),
  `.outright_height` (with `max_storeys`), `.setbacks` (the new check `district_setbacks`: pass / conditional
  against the option's setbacks), `.site_coverage` (`info_only`). The base maximum is the outright figure; the
  Director's conditional increases travel in the source's `verify` note.
- `propose_site(site, document=None)` sends the site's public fields and the context frame (not the long
  `osm` block) plus an optional survey or plan; items: district, area, frontage, depth, frontage street, corner
  lot, lane behind, the equivalent-rectangle reasoning, easements / buildings / slope / trees notes.
- `python -m ffm confirm --proposal … --by "Name" [--only key,key]`: a person moves a rule proposal into
  `rules/a_zoning_district.json` (a new rule, or a new version of an existing id; the source title names the
  model and who confirmed it and when; `source.confirmed` records the proposal file and the confidence) or a
  site proposal into the site file (`site.confirmed[key] = {by, on, source, proposal, confidence, evidence}`).
  `suggest._district_rule` finds any district's outright and setback rules by check, so a confirmed RT-3
  schedule drives the suggestion (and replaces the placeholder setbacks, citing the rule). `tests/test_propose.py`
  runs it all on a stub model.
- Eval set: `evals/propose/<case>/document.* + expected.json`; `python -m ffm propose eval` scores field by
  field (`propose.score`). The first case is a synthetic RT-9 schedule (not a real district). The real RT-3
  schedule is not in the repo: `bylaws.vancouver.ca` refuses automated downloads, so a person saves the PDF and
  runs `propose rule --from <pdf> --district RT-3 --url <its address>`, then `confirm`.
- A person's own key (3 Nov 2026, "allow users to input their own tokens"): stops 1 and 3 hold a fold "Ask
  Claude …" with a key box (`renderKeyBox`, `KEY_STORE = "ffm.claude.key"` in localStorage, shown as its last
  four characters, "Forget it"). `callClaude(kind, args)` sends the key with each request to the local server
  (`api_key` in the body; `server._key_of` hands it to `propose` and never stores or logs it) or, on the web,
  calls the Messages API straight from the page (`CLAUDE_API`, header `anthropic-dangerous-direct-browser-access`)
  with the request the engine builds in Pyodide (`propose.browser_request`) and parses (`propose.browser_proposal`;
  the shim's `ffm_propose_request` / `ffm_proposal_from_response`). `GET /api/capabilities` says `accepts_key`
  and `writes_rules`. Without the SDK on the machine `propose._send` falls back to `_send_http` (urllib, the
  same request), so `python -m ffm ui` needs no extra package; API errors come back as the API's own words
  (a bad key: "authentication_error: invalid x-api-key", status 502 from the server).
- Stop 1: "Ask Claude about this site"; the proposal renders with confidence and evidence, each field has
  Confirm (a name is required: it goes on the site file), and "Confirm all". Stop 3: "Read the district
  schedule with Claude", open by itself when the stack has no outright schedule for the site's district
  (`list_rules` now carries `check`): a PDF chosen from disk goes base64 to `POST /api/propose/rule` (the server
  passes the bytes to the model and writes nothing but the proposal's log with the name and hash); the clauses
  render with their quotes; "Confirm all into the rules" under a name calls `POST /api/confirm` (→
  `propose.confirm` into `rules/a_zoning_district.json`), reloads the rules and asks for the site to be read
  again. On the web the schedule can be read but not confirmed (the rules are the published files).
- The site pages say six layers and 24 rules and assumptions from 25 sources (home.html, how.html).
- The committed runs under `outputs/` were regenerated on 3 Nov 2026 with layer F and the layouts (their
  original as-of dates kept): the fingerprint for 23 Oct 2026 is now `e51e3a0350b87718` (quoted on case.html)
  and for 27 Oct `83993057d297734a`. The local Revit result on the as-approved run still carries the old stamp
  `20e44f1445ecaff9`, so its section stays out of that memo until the pyRevit script is run again on the folder.

## The six-reviewer critique and its fixes (20 Nov 2026)

Kai asked for a re-critique with several opinions per part; six reviewers (a design director, a development manager,
an architect, a board/funder reader, a tester, the detector) wrote `.impeccable/critique/2026-11-18T23-07-55Z__*`
(tool 24/40, site 19/28), and Kai chose "everything found". Decisions Kai made: an option over the outright limits
**fails the outright test, with rezoning named as required**; the money is **drawn as a stack**; 609 Heatley Ave
**should fit** (below). What a later session must know:
- **Corner lots** (`lookup.corner_yard_front`): where the address street runs along the lot's longer side and a cross
  street along the shorter, the lookup sets `site.front_face` and `site.front_street` to the cross street. Kai's words:
  the building's long side is along Heatley, but the side by the neighbour is a side yard, as it is from Keefer St. So
  the yards are read from the short side (the 20 m RT-3 rear yard falls at the far end) while the address frontage
  stays the named street's (the 39 frontage labels put six corner fronts on the longer, named street; making the
  shorter side the frontage scored 30 of 39 against 35). 609 Heatley Ave: envelope 11.5 × 13.0 m, outright yes, FSR
  0.60, 340 m², a walk-up of 4 homes (3 placed).
- **Engine** (`checks.py`): exceeding the outright FSR, height or homes cap with a rezoning path is `fail` ("not allowed
  outright; rezoning is required (…)"), never an open item (`engine.answered_by_rezoning`); the by-rezoning answer is
  unchanged. The no-envelope yards finding leads with the consequence and a named task, clauses last. The funders answer
  has `funded.words` ("Meets the criteria of …") and `funded.intake` [{rule_id, program, open, note, more, status}];
  the CHF's cancelled 2025 call is `open: false`. `proforma`: a missing land price with a gap already over 15% before
  land reads unlikely; line notes explain land at $0 (F3), the 15% screening line and the 1.10 coverage.
  `suggest` returns `label` / `falls_short` (funder-ready under the fund's smallest split) and, with `fixed.units` and
  no gfa, `floor_area_from_homes` (the floor area follows the homes, capped at the envelope, storeys on plates of at
  most 500 m², a placeholder). `layout`: a building of at most 3 storeys on a plate of at most 150 m² is also tried as
  a **walk-up** (one 2.6 × 5.5 m stair, no lift, `WALKUP_ASSUMPTIONS`, one exit marked a placeholder) and kept where
  it places more homes; the sheets carry scale bars, north arrows, street names, stairs, doors and an entry, measured
  text (`SheetsReadAsDrawings` checks no overlap); heights print half-up (88.45 stays 88.45).
- **The committed runs were regenerated**: 998 now holds 84 rules (48 not applicable from the 17 Nov schedules), so its
  refs moved until they were counted over the rules that apply only (below); fingerprints 6e72488249c79837 (23 Oct) and
  6400258c88ac57c8 (27 Oct); homes placed 67 of 105 and exits pass (the solver already at HEAD). `375-glen-drive/
  first-run` was rerun with the rule files as at f3db4f1 (`git show f3db4f1:rules/…` into a scratch folder, `--rules`),
  keeping fingerprint 8a8459a0c650a9c2; with today's rules it would duplicate as-proposed. The site pages quote the new
  figures (seven open items on R1, 67 of 105).
- **Tool**: the walkthrough's Run stop opens the committed R1 (no run folder); Back/Forward move between runs
  (`followHistory`); drafts are removed only by Start fresh; stop 02 leads with Homes, refuses impossible figures and
  draws a small section; the block editor opens on the memo's own plan, works by keyboard, and has "Suggest a grid
  plan"; touch targets are 44px; the as-of date is labelled "Rules as of". **Memo**: the comparison follows the
  answers (`.memo-compare`, folded for the reader); new modules `memo/stack.js` (capital stack), `memo/lanes.js`
  (who resolves what), `memo/words.js` ("Words in this memo"), `figures/envelope.js` (answer 1's drawing); FIG 02 is
  Section A–A; dates read as words. **Site**: how.html gains the lanes (section 05) and drawn layer slabs; case.html the
  R1–R3 sections; claims sourced in the sentence; brand.html for designers. DESIGN.md records each.
- **References count only the rules that apply** (Kai, 20 Nov 2026): a result written for another district or not
  in force on the date takes no A1… number (`engine.takes_ref` / `memo_refs`, the page's `takesRef` / `memoRefs`;
  the engine marks such results `elsewhere: "district" | "date"`, and older ledgers are read by their finding). The
  schedule's pre-run count (`refNow`) numbers only the rules `appliesHere` keeps; the paper drops those rules from its
  ledger and source list with one line counting them. On 998 R1: the policy A1, the RM-1 outright FSR and height A3
  and A4, the trees C6 (the area-plan family rule in layer C still applies city-wide).

## The simulated user tests and their fixes (23 Nov 2026)

`docs/user-tests-2026-11-23/` holds four role-played reviews (an architect, two development managers, a funder-side
reader; AI role-plays, never to be quoted as practitioners or credited in the README), a browser walk, their wish
lists, and a README that lists what was fixed and what is still open. What a later session must know:
- **Housing type.** `option.housing_type` (independent, supportive, transitional, shelter; `checks.housing_kind`, which
  also reads an option whose homes are all `supportive_units` as supportive). For the last three `chf_fit` and
  `bc_builds_fit` return not applicable ("not the test for this option"), `engine.summarise` makes the funders verdict
  `"not assessed"` with a `coverage.funders` open item, and `family_unit_share` returns uncertain (the City's to say).
  The page asks it at stop 02 (`HOUSING_TYPES` in `fields.js`). `funded.scope` says which programs were tested.
- **No rezoning.** `checks.proposes_rezoning(option)`: a `rezoning_path` that is blank or begins "none" is not a
  rezoning. The family rule is then not applicable (where the path says "none…"), and an option allowed outright that
  proposes none gets `by_rezoning.verdict == "not needed"` with the rezoning-only rules left out of the open items.
- **Grants follow answer 2.** `proforma.build` counts the Community Housing Fund grant only where its check is not a
  fail or not applicable (`funding.not_counted` otherwise); a counted grant is `illustrative`, and "likely" becomes
  "unsure" where the cost is covered only by a grant from a fund with no open intake or unconfirmed criteria.
  `verdict.operating_shortfall` (rents under the running costs) forces "unlikely" and `OPERATING_FUNDER` as the next step.
- **C-2's rental FSR** needs `rental_min_non_dwelling_fsr` (0.35) of `non_residential_gfa_m2` over the site area;
  `fsr_limit` returns `rental_short` and the base figure otherwise; `suggest.street_floor_m2` puts it in the suggestion.
- **memo.md** carries `memo.layout_open_items` (the twin of the page's `layoutOpenItems`), prints only the rules
  `takes_ref` keeps, and takes `massing_error`. Wording: "passes the eligibility items this screen checks", "did not
  proceed" for a cancelled call, no "inbox/" or stop numbers in an action.
- **Lookup.** The City's `civic_number` is text: `city_nearest` asks for a range as a list of numbers. On a civic
  mismatch the geocoder's parcel stays the site and `lookup.nearest_on_street` names the other candidate; the CLI
  refuses `--out` without `--accept-nearest`. A cross-street front the context does not show adjoining is not written.
  The static build's own lookup (in the page) was not changed.
- The committed runs were regenerated (fingerprints cd95334f97a184b5 for 23 Oct, ed83d80023e8f142 for 27 Oct,
  ab455d78c14492b9 for 17 Nov; `375-glen-drive/first-run` untouched). Glen Drive as proposed now reads a 76% gap.
- **The operating page** (same day, later). `option.operations` {rent_market_monthly_cad, rent_rgi_monthly_cad,
  rent_deep_monthly_cad, operating_cost_per_unit_year_cad, support_staffing_cad_year, operating_subsidy_cad_year,
  subsidy_confirmed, subsidy_source}: each stands over the layer F placeholder (`proforma.build`, the line's rule id is
  then None and its note says "entered"). `operating.page` holds the table's figures; `proforma.operating_rows` /
  `operating_markdown` and the page's `operatingRows` / `operatingTable` (memo/answers.js) are twins. `noi` is now after
  support staffing and before any subsidy; a subsidy sizes debt only when confirmed; `staffing_missing` (supportive,
  transitional or shelter housing with none entered) and an unconfirmed subsidy both stop "likely". The inputs are
  `OPERATING_FIELDS` (`ops: true` in fields.js), a fold at stop 03 beside the money. `paper.js` prints the same rows
  (`opTable`, after the money's line table).
- **Sources and leftovers** (same day, final pass; the user-tests README has the list). `option.approval_route`
  (rezoning | development_permit | outright; `checks.approval_route`, `APPROVAL_ROUTES`): by permit or outright the
  rezoning-only rules are not applicable and `by_rezoning.verdict` is "not needed". `engine.summarise` drops open items
  of layer-E programs the option does not target and appends "Ask: <contact>." (`CONTACTS`, `contact_for`; the item
  carries `contact`). `finance.non_residential_cost_per_m2_cad` / `_income_cad_year` / `_funding_cad` are pro-forma
  lines (`hard_nonres`, `nonres_income`, `nonres_funding`). `option.ground_floor_height_m` adds to the height
  (`layout.ground_extra`, `plate.ground_floor_m`, absent when not set). `suggest` returns `same_building_note`.
  `memo.markdown` ends with "Words in this memo" (`GLOSSARY`). `massing.svg` has the street at the bottom.
  `bch.chf.eligibility` and `bc.bcbuilds.eligibility` have 2026-01-01 versions read from BC Housing's HTML pages
  (verified); `cmhc.ahf.readiness` says its intake closed 19 Dec 2025. BC Housing's PDFs (Housing Income Limits, Design
  Guidelines, the program frameworks) were **not** read: a download needs Kai's permission, and the browser pane
  answers a bchousing.org PDF link with a save dialog. Fingerprints now 8bc2390c7cd9cbdb (23 Oct), 00b916863ab4ff5b
  (27 Oct), 16df88bd0f50baba (17 Nov); gaps read 43%; 342 tests.
- **BC Housing's PDFs read** (same day, with Kai's permission; `inbox/bc-housing-2026-11-23/`, fourteen files, text
  extracted with `uv run --with pypdf`). New rules: `f.rgi_rents` (from 1 Dec 2025: Vancouver Housing Income Limits,
  RGI rent at 30% of 70% of the limit as the fund's 2023 call estimates it, deep-subsidy rent by bedroom; `proforma`
  reads it over `f.rents`' placeholder, line rule id `f.rgi_rents`) and `bch.shelter.bed_space` (check `shelter_beds`:
  4.6 m² a bed space, four beds a room; not applicable unless `housing_type` is shelter). New versions:
  `bch.chf.eligibility` from 1 Apr 2026 (`provisional_grant_per_unit_cad` 178,059, `grant_fiscal_year`; `checks._chf_grant`
  reads either key) and `bch.design_guidelines.unit_areas` from 23 Nov 2026 (verified; `edition_status: archived`, since
  BC Housing's own copy of the 2019 edition is stamped archived with no replacement named; four-bedroom 112 m²).
  `program_match` prints `owner` and `rents` where a rule has them (the Supportive Housing Fund's buildings are owned by
  the Province). Rules made earlier this session and never committed were edited in place, not re-versioned.
  Fingerprints now e270210b5ed562c7 (23 Oct), 7c057234c9d4da8d (27 Oct), 46276d4e929a2c2f (17 Nov); 998 as approved
  reads a 22% gap ($11.8M), funder-ready 45%; 95 rules; 350 tests. Not found in any of them: a cost per square metre
  by building type, the fund's mix tolerance, a replacement for the archived guidelines.
- **A CD-1 lot and a key; seventeen City schedules** (24 Nov 2026; the user-tests README has the table). The manager's
  site card shows the schedule form for a CD-1 lot the rules do not hold (`cd1Slot` in route-stage.js; `renderClaude`
  draws the one form into `#stage-cd1-slot` in manager mode, else `#claude-schedule-slot`; kept across card re-renders
  by its `data-sig`). The tool cannot fetch a CD-1 by-law: `cd1-bylaws.vancouver.ca` returns 403 to a program, as the
  other City hosts do. Layer A gained 51 verified rules from PDFs Kai saved (`inbox/city-2026-11-23/`): RT-4/4A, RT-5,
  RT-7, RT-8, RT-10, RT-11, RM-6, RM-7/7A, RM-8/8A, RM-9A, RM-9, RM-9B, RM-10, RM-11, RM-12, FM-1, M-1 and the
  Downtown-Eastside/Oppenheimer plan (district `DEOD`). `cov.rt.*` (from memory) now covers only RT-6 and the N
  variants. New in `checks.py`: `_for_sub_area` (a rule's `by_sub_area` table read by `site.odp_sub_area`; uncertain
  until it is recorded; asked at stop 01 for a DEOD lot), `housing_not_permitted` on a schedule (M-1: the FSR rule fails
  for housing), and a height rule whose maximum is None (sub-area 4: discretion only, conditional). `suggest` handles
  all three. The schedule generator was a scratch script; the rules file is the record. Fingerprints now
  53056660a42fb57b (23 Oct), 30cfd9b9ac04c178 (27 Oct), a3bef23d7edb36b9 (17 Nov); 146 rules; 361 tests.
- **Corrected by Kai, 24 Nov 2026** (this stands over the two bullets above where they differ): RT-6 and the N variants
  are not districts (the City's map has RT-1, 2, 3, 4, 4A, 5, 7, 8, 9, 10, 11), so `cov.rt.*` is deleted and no RT site is
  unverified; BC Housing's 2019 Design Guidelines are the standard (its page says so; the "archived" stamp is on the
  PDF only), so `edition_status` is `current` and the unit-areas finding raises nothing. 144 rules, five unverified.
  Fingerprints 31193259023b85e0 (23 Oct), 2c0cee962e81cc28 (27 Oct), 5cfd6a34b23f68ab (17 Nov). Kai saves by-law PDFs
  in `02 A2\00 Research`, beside the repo.
## The tool critique and audit of 24 Nov 2026, and its fixes

`.impeccable/critique/2026-11-24T18-33-25Z__ffm-ui-index-html.md` (26/40, three P1s). Kai chose: trust contradictions
first, **only issued runs get a number**, everything listed. What a later session must know:
- **Drafts.** A run made in the tool is a draft ("Draft 14:03") until marked issued; `noteRevisions` (runs.js) numbers
  committed runs, then runs made here in the order first issued (`issued_at`, the earliest in the folder's
  `issues.json`, which `server.list_runs` now returns). `isDraft`, `nextRev`, `runName`, `afterIssue` in runs.js. The
  Issue button reads "Mark issued to the architect / development manager"; the board is no longer offered (it reads the
  PDF). The web build's runs stay drafts.
- **Run guards.** `runRefused` (runs.js): the reader never runs; the manager's memo runs again only when stale (Ctrl+Enter
  and Enter on the aria-disabled Run again said "Nothing has changed since R1"). A "Rules as of" date off the memo's
  own marks it stale (`DATE_STALE` in files.js; back to the memo's date clears it unless an edit is pending), and the
  button reads "Run again as of 27 Oct 2026". `guide.optionSeen`: a saved site's first option counts at 02 only once
  02 was visited.
- **Stop 02's reading** shows "applies / needs your figures / not here" (`readingMark`), never status pills.
- **Title block:** the comparison's result and a jump in the Compared-with cell (`compareResult` in side-by-side.js,
  `changesPhrase` exported from changes.js); the sheet index "In this memo" (`MEMO_INDEX`, `indexMemo`, `wireJumps` in
  memo/memo.js); the view switch stays while comparing; the Export to Revit panel opens under its button
  (`placeActions` moves `#export-panel`, the footer hides while empty).
- **Plans** show in every layout with a "First layout from the rules · not yet checked by the architect" stamp until
  issued back to the manager (`.layout-stamp`); the `layout-wait` card is gone.
- **FIG 06 to project north** (`layout.project_turn`, twin of the page's `projectTurn`): the code site plan turns by the
  quarter turn nearest north, the street named on its side; 998 and Expo now have the street at the top, 375 Glen
  Drive's first-run on the right. Drawings' foot lines read the date in words (`massing.date_words`). All committed
  sheets, massing.svg files and memos were redrawn from their own JSON; `375-glen-drive/first-run/massing.svg` kept its
  geometry as made, only its date changed. Ledgers and fingerprints untouched.
- Copy: the money's next steps say "a revised memo counts…" (no "run again", no "at 03") in `proforma.MORE_SOURCES` /
  `OPERATING_FUNDER` and their twins in answers.js; "Proposed" (not "(simulated)"); the 15% line said by size; land
  tenure asked once, at 02, with one "Not sure"; the CD-1 and Oppenheimer schedule rows show only where they apply
  (`only` in fields.js); the architect's schedule says "the manager" for "you"; the Reader has its own walkthrough
  (`READER_TOUR`). One h1 a screen (the wordmark is a `p`).
- Also: the ledger stacks on a phone; Leaflet waits while a `?run=` link opens; `/api/issues` and `/api/diff` are not
  asked twice; tree ids and the elevations' limit labels meet contrast; the gap label fits its box; Side by side
  changes read off the printed figures, in points for percentages; the answers keep a 920px width.

## The second simulated panel (24 Nov 2026) and its fixes

`docs/user-tests-2026-11-24/`: three architects (small lots, towers, supportive housing) and a non-profit operator, AI
role-plays (never to be quoted or credited). Its README ranks the thirteen defects they found, all re-run and fixed the
same day, and lists what is still open. What a later session must know:
- `checks.housing_parts(option)`: the kinds of housing in a building with their counts (supportive homes from
  `supportive_units`, shelter beds from `beds`). `program_match`, `shelter_beds`, the proforma's staffing test and
  `engine.summarise` (`coverage.funders_parts`) read it; `housing_kind` still names the main kind.
- `checks._over_outright`: over an outright limit, the finding follows the approval route (rezoning / a permit that
  cannot approve it / none stated); a permit route over the limits makes `by_rezoning.verdict` "needed".
- `checks._other_front_fsr`: on a corner lot where the other front would allow the floor area (a narrow-site cap), the
  density answer is uncertain and asks the City which street is the front.
- `checks.MIN_ENVELOPE_M` (5.0 m, a declared placeholder): a narrower or shallower envelope is no envelope.
- `side_yard_narrow` {max_width_m, share, clause} on the RT setback rules; `yard_minimums` applies it.
- `proforma`: `operations.subsidy_term_years` (a loan on the subsidy only where the term covers the amortization);
  `operations.replacement_reserve_per_unit_year_cad` and `vacancy_rate`; a beds-only shelter counted per bed; the
  subsidy needed withheld where staffing is missing; no CHF grant without rent tiers; `PROGRAM_ROUTE` for supportive,
  transitional and shelter housing; `own_figures` on the page. The page's twins are in `memo/answers.js`.
- `boundary.inset` counts a corner on the lot line as inside (`_on_edge`). `massing` warns when the storeys need more
  height than stated, and the proposed mass carries `level_z_m`, which the Revit script uses for its plates.
- `suggest.envelope_for` caps a TOA tier's floor area at the tier's FSR.
- `options/375-glen-drive-as-proposed.json` carries `beds: 80` (the referral report's shelter). R1 at 998 E 19th Ave
  reads a 56% gap now (no rent tiers, so no grant). Fingerprints d8114c4301640d47 (23 Oct), 9da6dabc8def1912 (27 Oct),
  c0cd775dd41c5779 (17 Nov); 373 tests. `tests/fixtures/1130-jervis-st.json` is a public lookup kept for the corner test.

## The operator flow, the program brief, two building types and the area schedule (24 Nov 2026)

Built at Kai's request from the second panel's list (`docs/user-tests-2026-11-24/README.md`, last section, has the detail).
- `layout.py`: `BUILDING_TYPES` / `building_type(option)` ("apartment", "ground_oriented", "tower"); `_solve_ground_oriented`
  (rows, `home` ids and `levels` on each zone, `z["unit"]` the unit key on the entry floor only, `_ground_egress`);
  `_solve_tower` (reads massing's `tower` and `podium_storeys`, joins two `_solve_plate` results like `_solve_parts`);
  `TYPOLOGY_ASSUMPTIONS`; `lifts_needed`; `BRIEF_DEFAULTS` / `program_brief(option)` (brief items become `other` blocks with
  `brief`, `next_to` "entry" placed straight after the lobby, `where` "upper" starting above the ground floor; a dining item
  replaces the amenity block); `area_schedule` / `area_schedule_csv` / `area_schedule_markdown`; `operability(L, option)`.
  `_assemble` adds `area_schedule` and `operability` to every layout; `write` adds `area-schedule.csv`.
- `massing.py`: a tower's podium plate, `tower` rect, `podium_storeys` and two `tiers`.
- `suggest.py`: `DESCRIBES` keys pass `check_fixed` and travel to the option; supportive housing derives studios.
- `engine.operator_items`: the Operator lane (`operator.figures`, `.subsidy`, `.term`, `.staffing`), only where an operator
  is in play. `memo.py` prints "Operating figures: signed by …" from `operations.signed`.
- Page: `memo/operator.js` (the operator's desk, the area schedule table and its CSV twin), `brief.js` (the editor and the
  JS twin of `BRIEF_DEFAULTS`, a test keeps the labels equal), Operator mode in `modes.js` / `index.html` / app.css,
  `ISSUE_ALSO` in issue.js, the Operator lane in `memo/lanes.js`, `ROLES` in server.py, the stop-02 questions in
  fields.js (`building_type`, `podium_storeys`, `tower_plate_m2`; a question's `when(site, answerValue)` can read another
  answer). The PDF prints the area schedule, the brief and the checklist as a section after the massing (`paper.js`
  `areasPaper`, `signedWords`). 387 tests.
- Gaps closed the same day: accessible ground-oriented homes are one-floor homes at grade with a home over them
  (`left_count` in `_solve_ground_oriented`); `suggest.suggest_building_type` → `building_type_suggested` (offered at stop
  02 by `typeOffer`, never applied unasked; applying it automatically changed seven tests' towers); `place_zones` /
  `zones_of` keep `home` / `levels` (a home counted on its entry floor, no corridor/core/lift asked on a ground-oriented
  plan), and the block editor's `syncHomes` carries a change to a home onto every floor it spans. 391 tests.

## The memo as an ask (24 Nov 2026, piece 1 of Kai's plan)

The plan is `02 A2\00 Research\First Read - wish list and plan.docx` (six pieces; 2 is the site before an option).
`docs/user-tests-2026-11-24/README.md`, last section, has the detail.
- `engine.routes` / `by_discretion`: `allowed.routes` {outright, discretion, rezoning}, each {label, verdict, why, rules}.
  Discretion verdicts: possible, not needed, none in the schedule, no, not yet confirmed, not assessed. The old keys stay.
- `proforma`: `named_sources(fin)` reads `finance.sources`; `contributions(...)` → `funding.sources` (the contributions
  ledger), `funding.uncommitted`, `funding.land_contribution` (from `finance.land_value_cad`); `SOURCE_*` and
  `CONTRIBUTION_STATUS_WORDS` (twin `CONTRIBUTION_WORD` in memo/answers.js, a test keeps them equal); `sources_markdown`;
  `markdown(pf, short)`.
- `memo.front_sheet` / `front_markdown` (twin: `memo/front.js` `frontOf`, `frontHtml`, `routesHtml`, `amountWords`,
  `routeStatus`); `memo.markdown(..., short=True)`; `write` adds `memo-short.md`; Sources limited by `takes_ref`.
- Page: the front sheet before the answers (`.memo-ask`, first in `MEMO_INDEX`); `sourcesTable` in answer 4;
  `sourcesEditor` and the "What are you asking for?" field at 03 (route-stage.js); `finance.land_value_cad` and
  `decision_sought` in FIELDS; `paperDocument(run, {short})`, `exportPdf(short)`, `#pdf-short-btn`. 409 tests.

## The site before an option (25 Nov 2026, piece 2 of Kai's plan)

`docs/user-tests-2026-11-24/README.md`, last section, has the detail.
- `rules/a_zoning_district.json`: 32 `cov.<district>.uses` rules (check `district_outright_use`, params `uses` {use: {approval,
  as, page}}), generated from the schedules' use tables by a scratch script that quoted each row; the rules file is the
  record. `checks.district_outright_use`, `uses_for`, `APARTMENT_USES` / `GROUND_USES` / `SHELTER_USES` / `CLINIC_USES`. The
  check's name starts `district_outright`, so the outright answer and `isOutrightLimit` read it; `values.conditional_use`
  makes `engine.by_discretion` count it as the Director's discretion. RT-3, RM-4, R1-1 and C-2A sites now read outright
  "yes, with conditions" (a conditional use).
- `suggest.lot_reading` / `ssmuh_homes`: `read_site` returns `lot` {plate, yield, ssmuh, uses}; the page's `lotTakes` draws it
  at 02.
- `lookup`: `assemble(..., extra={zoning_centre, stations, nearest_rows})` (the caller fetches; `lookup()` and the web
  build's `staticLookup` in core/api.js both do); `refuse_nearest`, `nearest_from_rows(same_side)`, `nearest_where`,
  `toa_from_stations` (`TOA_SKYTRAIN_BANDS`, a test keeps them equal to `bc.toa.minimum_density`'s `tiers_where`),
  `lane_behind`, `city_elements(..., lanes)` (the City's `lanes` dataset; lanes tagged service=alley). `site.suggested`
  {key: {value, why, source, also}}, `lookup.refused`, `lookup.district_at_point`, `lookup.nearest_station`. The page:
  `siteOffer` under each stop-01 question, `#guide-lookup-nearest`. Fingerprints 7846c8b6a3414798 (23 Oct), 750597987a837e2e
  (27 Oct), 7532496a9e6ef1ff (17 Nov). 423 tests.

## Rules from the assignment brief (binding)

- Ask permission before using anyone's documents or data.
- Never put confidential drawings, client information or personal data in this repository or in an
  AI tool without permission. Everything here now comes from public City of Vancouver documents;
  keep it that way. Real practitioner sites are run locally and only shareable substitutes are
  committed.
- Credit practitioners in the README with their consent.
- The repo stays public where data allow.

## Known placeholders (say so, do not silently "fix")

- `sites/998-e-19th-ave.json`: red pine DBH 40 cm (species named in the referral report, diameter
  not); `in_transit_oriented_area` left null on purpose until the City's TOA map is checked.
- `options/*.json`: setbacks 3.7 / 6.0 / 3.0 m assumed; rent tiers and accessible units null in the
  as-approved option; the what-if option is hypothetical and labelled as such.
- RM-1 outright figures (FSR 1.20, 10.7 m) are cited from the referral report; verify against the
  consolidated district schedule when convenient.
- District schedules (16 Nov 2026, `rules/a_zoning_district.json`): RT-3 is read from Kai's saved PDF
  (`inbox/`, `source.verified: true`); the RT family (RT-4 to RT-11 bar RT-9), RM-3 and RM-3A are typed
  from recollection (`source.verified: false` plus a `verify` sentence) and raise `coverage.schedule_unverified`
  in `engine.summarise` until a person confirms them against the PDF. Districts not entered read "not assessed";
  CD-1 sites carry `cd1_bylaw_number` from the lookup.
- Each site picks its own schedule (17 Nov 2026): a CD-1 rule carries `applies_to_cd1` (the CD-1 number) and matches only
  a CD-1 site with that number (`site.cd1_bylaw_number`, else the number in "CD-1 (819)"; `rules_loader.cd1_number`,
  `district_of`, `Rule.applies_to_site`; in the page `cd1Of`, `districtOf`, `appliesHere` in `fields.js`); a CD-1 with no
  number matches none. `propose confirm` writes a CD-1's clauses that way (`cov.cd1_<n>.*`). A district or CD-1 not in
  the stack says so ("No I-2 schedule in the rules", "CD-1 (9999) is not in the rules", "A CD-1 site with no CD-1
  number"). RM-4 is now read from Kai's October 2026 PDF (multiple dwelling: FSR 1.45, 3.00 for 100% social housing
  `max_fsr_social_housing`; 10.7 m, the Director's 19.9 m for social housing `max_height_m_social_housing_variance` →
  conditional; yards 6.1/2.1/10.7 m `cov.rm4.setbacks`); the recalled 0.75 was wrong and RM-4N, not in that PDF, is out.
  CD-1 (819) (375 Glen Dr / 1015 E Hastings) is from the draft by-law in its referral report (`inbox/rr5.pdf`,
  `verified: false`, `unverified_because`; FSR 6.90 on the fixed 2,134.4 m², `fsr_site_area_m2`; 51.0 m).
  The City posts no PDF for CD-1 (819) (its CD-1 index lists 1015 East Hastings Street with no link), so it stays unverified.
  CD-1 (324) (By-law No. 7248, consolidated to No. 14009, 23 Apr 2024, `inbox/cd-1(324).PDF`, verified):
  `cov.cd1_324.floor_area` caps the residential floor area by sub-area (s.6.2 Table 1a: A 19,300 m², B 23,600 m²;
  `sub_area_residential_floor_area_m2`, read against `site.cd1_sub_area`, uncertain where it is not recorded) and
  `cov.cd1_324.outright_height` is 91 m (s.7.1). `sites/1010-expo-blvd.json` carries `cd1_bylaw_number` 324 and
  `cd1_sub_area` "B" (read off Schedule A), so Expo's outright answer is now assessed; its committed runs and `case.html` still
  say "not assessed" until they are regenerated. The checks read every schedule through `checks.fsr_limit` / `height_limit`
  (tenure, site-size tables, social-housing and rental figures, the Director's discretion as conditional, formula increases,
  unit caps, a sub-area's fixed floor area); the suggester takes its figures from them.
- Twelve more schedules read from the PDFs Kai saved into `inbox/` (17 Nov 2026; October 2026 consolidations, R1-1 June
  2026), 46 rules, all `verified: true` with `read_from` pages, written by a generator that found each clause's page in the
  extracted text: RM-3 (FSR 1.00 plus the formula increases, `fsr_increases` → uncertain above 1.00; 36.6 m; replaces the
  recollection rule, whose 10.7 m was wrong), RM-3A (3.00 and the Director's 19.9 m for 100% social housing), RM-5 family
  (`cov.rm5*`: 1.00, the Director's 1.50 / 2.20 / 2.75 as conditional, `narrow_site` caps; RM-5D 7.00 and 58.0 m with social
  housing), R1-1 multiplex (1.00, 8 homes rental / 6 otherwise, 11.5 m and 3 storeys), C-2, C-2B, C-2C, C-2C1 (a rental
  mixed-use building 3.50, 3.70 on a big corner, 19.8 m and 6 storeys; other tenures 0.75 with the Director's 2.50 / 2.50 /
  3.00 / 3.00), C-2A (3.50 rental, 2.50 other, 23.0 m, 27.5 m in a transit-oriented area), RR-1, RR-2A, RR-2B (rental only;
  `fsr_table` rows by site area, depth and a corner's frontage; RR-2B 3.00 and 27.5 m for social housing) and RR-3A, RR-3B/3C
  (2.40 / 3.40, the Director's +0.10 only on a big corner, 920 m² minimum). Side yards that apply only beside an R district
  are left untested (the site does not record its neighbours). The tool reads social housing and secured market rental as
  rental tenure. Only the RT family (bar RT-3) is still typed from memory.
- Also 16 Nov 2026: `bcbc.exits` (`rules/d_design_standards.json`, `verified: false`) is read by `layout.egress`
  into `L["egress"]`; `option.sprinklered` switches its limits. `option.massing` {anchor, dx_m, dy_m, rotate} and
  `site.front_face` {street | side | edge} place the mass and turn the lot (`massing.place`,
  `boundary.oriented_ring`; the page applies `lot.orientation` to the stored context). `option.layout.extra_programs`
  [{label, area_m2}] are the architect's own blocks (kind `other`). `suggest()` takes `mix_shares` and returns
  `envelope`, `mix` and `candidate_note`. An issue note carries `name`.
- Area-plan family target (17 Nov 2026): `cov.dtes.family_units` (`rules/c_city_policies.json`, `verified: false`, read
  from the 1015 East Hastings referral report, not the Plan) is the Downtown Eastside Plan's 25% two-bedroom-plus
  target; it applies only where a person set `site.area_plan` to `downtown_eastside`, leaves `option.supportive_units`
  out of the count (`exclude_supportive_units`), and the city-wide `cov.family_units` then reads not applicable
  (`checks.AREA_PLAN_FAMILY_TARGETS`, `tests/test_area_plan_family.py`). Neither field is in `FIELDS` yet, so the page
  has no input for them. Third case study: `sites/375-glen-drive.json` with
  `options/375-glen-drive-as-proposed.json` (the referral report's figures; the report PDF is `02 A2\rr5.pdf`, outside
  the repository) and the run in `outputs/375-glen-drive/as-proposed/`.
- `rules/f_assumptions.json`: soft costs 25%, contingency 10%, operating $6,500 and reserve $600 per unit,
  are declared placeholders (`placeholder: true`; the RGI income at half the fund's limit is overridden by
  `f.rgi_rents` from 1 Dec 2025); the hard-cost base
  is a 2- to 4-unit catalogue figure; bachelor, one-bedroom and three-bedroom rents are null until typed from
  the CMHC data tables.
