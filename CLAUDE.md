# CLAUDE.md — Funding-Fit Memo

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
python -m ffm run --site sites/998-e-19th-ave.json --option options/998-e-19th-ave-as-approved.json --out outputs/998-e-19th-ave/2026-10-23 --as-of 2026-10-23
python -m ffm run --site sites/998-e-19th-ave.json --option options/998-e-19th-ave-as-approved.json --out outputs/998-e-19th-ave/2026-10-27 --as-of 2026-10-27 --previous outputs/998-e-19th-ave/2026-10-23/ledger.json
python -m ffm run --site sites/998-e-19th-ave.json --option options/998-e-19th-ave-what-if-5-storey.json --out outputs/998-e-19th-ave/what-if --as-of 2026-10-23 --previous outputs/998-e-19th-ave/2026-10-23/ledger.json
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

The page also runs on GitHub Pages (https://kailisun98.github.io/BC-Housing-Feasibility-Study/):
`python -m ffm pages` (`ffm/pages.py`) builds a static site whose `app.js` detects
`window.FFM_STATIC`, reads the committed runs from `data/` and runs the engine in Pyodide from
`engine/`. Published by the Actions workflow in `.github/workflows/pages.yml` on every push to
`main` (Pages is set to build from Actions; the old `gh-pages` branch is no longer used). The gh
CLI login on this machine has the `workflow` scope since 22 Oct 2026. Never let the pages build
copy office-template files; `pages.py` lists the run files it copies.

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
