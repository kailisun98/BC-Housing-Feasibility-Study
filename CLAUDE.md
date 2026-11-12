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
so the outright rules are not applicable and the memo's "outright: yes" is an engine limitation
noted in the site file, not a finding.

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
styles with a hash of their contents, `app.js?v=…`, so a browser that cached the last deploy fetches the new
one; Pages serves with max-age=600 and Edge kept the old app.js past that) whose `app.js` detects
`window.FFM_STATIC`, reads the committed runs from `data/` and runs the engine in Pyodide from
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

## Phase 1 of the workflows proposal (3 Nov 2026; `docs/proposal-workflows.md`)

Built and verified in the browser:
- `ffm/suggest.py`: rule-derived suggestions. `suggest(site, programs, on, candidate)` walks layers A to E and
  returns an option plus `fields` (value, rule_id, note per dotted key), `unsure` (what a person settles),
  `assumptions` (declared placeholders: floor to floor 3.3 m, setbacks 3.7/6.0/3.0, net efficiency 0.78,
  10% over the BC Housing minimums, a starting mix). Candidates: outright, benchmark, funder-ready. On
  998 E 19th Ave funder-ready gives 6 storeys, 19.8 m, FSR 3.0, 109 units, tiers 33/54/22, 19 trees.
  `read_site(site, on)` runs layers A to C with a bare social-housing probe. Tests in `tests/test_suggest.py`.
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
- The parcel survey (odd sites at city scale, `ffm/parcel_shapes.py`, `evals/parcels/`) and the polygon-aware
  massing and boundary editor are the next piece of work; see the proposal's item 5.

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
- `rules/f_assumptions.json`: soft costs 25%, contingency 10%, operating $6,500 and reserve $600 per unit,
  the RGI income at half the fund's limit are declared placeholders (`placeholder: true`); the hard-cost base
  is a 2- to 4-unit catalogue figure; bachelor, one-bedroom and three-bedroom rents are null until typed from
  the CMHC data tables.
