# Funding-Fit Memo

A deterministic feasibility screen for non-profit housing in British Columbia. Give it a site and a
building option; it returns a memo that answers three questions, a rule-derived massing, and a
version stamp that ties both to the exact rules used.

1. **Is it allowed?** Outright under the zoning district, and by rezoning under the City policy that applies.
2. **Does it fit the funders?** BC Housing Community Housing Fund, BC Builds, and the flags for CMHC and the predevelopment loan.
3. **What is still unsure, and who resolves it?** Every open item names the person and the document.

Every finding prints the arithmetic it used and links the clause it came from. No language model
runs inside the engine: same inputs and rule set, same memo, every time.

ARCH 540 Assignment 2 ("From a Real Workflow to a Working Tool"), UBC School of Architecture and
Landscape Architecture, fall 2026. Author: Kai (M.Arch). Built with Claude Code.

## Quick start

Python 3.10 or newer, standard library only.

```bash
# the as-approved option for 998 E 19th Ave, rules as of 23 Oct 2026
python -m ffm run --site sites/998-e-19th-ave.json \
                  --option options/998-e-19th-ave-as-approved.json \
                  --out outputs/998-e-19th-ave/2026-10-23 --as-of 2026-10-23

# the same option under the family-unit rule that takes effect 27 Oct 2026, diffed against the first run
python -m ffm run --site sites/998-e-19th-ave.json \
                  --option options/998-e-19th-ave-as-approved.json \
                  --out outputs/998-e-19th-ave/2026-10-27 --as-of 2026-10-27 \
                  --previous outputs/998-e-19th-ave/2026-10-23/ledger.json

python -m ffm rules --as-of 2026-10-27     # which version of each rule is in force
python -m ffm stamp                        # the version stamp alone
python -m ffm ui                           # the web UI: pick a site and option, run, read, export
python -m unittest -v                      # evaluation cases (evals/cases.md) and the memo tests
```

`python -m ffm ui` serves a one-page app at http://127.0.0.1:8765 from `ffm/ui/` (standard library
only, no build step): the site and option forms on the left, the memo on the right rendered from
`ledger.json`, downloads of the memo and the massing, and the Export to Revit instructions. Every
Run writes a normal run folder under `outputs/<site-id>/`, so anything done in the page can be
repeated from the command line. A two-minute **Walkthrough** (end of the step strip, offered once
on a first visit) spotlights each part of the page in order and can run the rules on the way.

### On the web

The same page runs on GitHub Pages at https://kailisun98.github.io/BC-Housing-Feasibility-Study/
with no server behind it. `python -m ffm pages --out _site` writes the committed runs as data
files, so past runs open at once, and ships the engine's own source files, which the page loads
into [Pyodide](https://pyodide.org) (CPython compiled to WebAssembly, about 10 MB from a CDN,
cached after the first visit). *Run the rules* then runs the identical code in the browser:
nothing is uploaded, and a browser run lives in the tab until you download its memo. Saving a
site or option downloads the JSON instead of writing it. The Revit step stays on a machine with
Revit. The engine itself remains dependency-free; Pyodide is only fetched by the web build.

Publishing is automatic: `.github/workflows/pages.yml` runs the tests, builds the site with
`python -m ffm pages --out _site` and deploys it to Pages on every push to `main`. To preview a
build locally, run the same command and serve the folder with `python -m http.server --directory
_site`.

Each run writes to `--out`:

| File | What it is |
|---|---|
| `memo.md`, `memo.html` | The memo: three answers, massing, change log, full ledger, inputs, sources, stamp. The HTML is self-contained and prints. |
| `ledger.json` | Machine-readable results: one record per rule with status, finding, numbers used, action, source, rule version. |
| `massing.json`, `massing.svg` | The rule-derived masses (proposed and outright) in metres; plan and section to scale. |
| `diff.json` | With `--previous`: what changed between two ledgers and whether the rule files changed. |

## The massing in Revit

`massing.json` is what the Revit script reads. `revit/ffm_massing_pyrevit.py` builds Mass-category
DirectShapes for the proposed and the outright envelopes, floor plates at every storey, and model
lines for the lot and the setback envelope; then it makes an axon, a dimensioned plan and a section
with the staff-benchmark lines, places them on sheet FFM-01 with text blocks taken from
`ledger.json` (the three answers, the open items, the massing numbers, the stamp), and exports the
sheet as PDF and PNG next to the `massing.json`. Each element carries the version stamp in its
Comments, so the box on screen can be traced to the memo that produced it. After it has run,
`python -m ffm memo --out <run folder>` adds a "Built in Revit" section to the memo with the sheet
image and the sheet text. It runs three ways:

```powershell
# headless, through the pyRevit CLI (creates a new metric project, builds, saves, closes)
$env:FFM_MASSING_JSON = (Resolve-Path "outputs\998-e-19th-ave\2026-10-23\massing.json").Path
$env:FFM_SAVE_AS      = (Join-Path (Split-Path $env:FFM_MASSING_JSON) "ffm_massing.rvt")
pyrevit run "revit\ffm_massing_pyrevit.py" --revit=2025 --purge
```

or inside Revit with pyRevit > Tools > Run (a dialog asks for `massing.json`), or pasted into
RevitPythonShell. Every mode writes `ffm_revit_result.json` (what was built, stage by stage, with
any errors) and `ffm_sheet_notes.json` (the sheet text) beside the `massing.json`, so the run can
be checked without opening Revit. (The Revit Public MCP is read-only,
which is why this is a script and not a connector.)

## How it is organised

```
rules/      the rule stack, one JSON file per layer, every rule dated and cited
  a_zoning_district.json   RM-1 outright FSR and height; interim rezoning policy; parking
  b_provincial.json        SSMUH (Bill 44) minimum units; transit-oriented areas (Bill 47)
  c_city_policies.json     family units (two dated versions); social housing definition;
                           below-market rental; Protection of Trees By-law; DCL and CAC
  d_design_standards.json  BC Housing unit areas; code basis (flags, not checks)
  e_funding_programs.json  Community Housing Fund; BC Builds; predevelopment loan; CMHC AHF
sites/      one JSON per site (zoning, area, dimensions, trees, owner, tenure plan)
options/    one JSON per building option (storeys, GFA, unit mix, tenure, funder targets, setbacks)
ffm/        the engine: rules_loader (versions + stamp), checks (the arithmetic), engine (ledger + diff),
            massing (envelope + extrusions + SVG), memo (Markdown + HTML), cli
revit/      the pyRevit script
tests/      unittest cases; evals/cases.md explains them
docs/       the 150-word proposal and the pitch outline
```

### A rule, in one picture

```json
{
  "id": "cov.family_units",
  "title": "Family Room Housing Mix policy: minimum share of family units",
  "check": "family_unit_share",
  "applies_to_districts": ["*"],
  "versions": [
    {"effective_from": "1992-01-01", "effective_to": "2026-10-26",
     "params": {"min_two_plus_bed_share": 0.35, "min_three_plus_bed_share": null},
     "source": {"title": "...", "url": "...", "section": "..."}},
    {"effective_from": "2026-10-27",
     "params": {"min_two_plus_bed_share": 0.35, "min_three_plus_bed_share": 0.05},
     "source": {"title": "...", "url": "...", "section": "..."}}
  ]
}
```

The engine picks the version in force on the `--as-of` date, runs the named check, and records the
version date and source on the result. The **stamp** is a SHA-256 over all rule files plus the list
of versions in force, truncated to 16 characters; it appears on the memo, the massing and the Revit
elements. Change one number in one rule and the stamp changes.

Statuses: `pass`, `conditional` (allowed with a stated cost or action), `fail`, `uncertain` (an
input is missing or a judgement is a person's), `not_applicable` (the tool says why), `info`.

## Adding a site, an option or a rule

- A site or option is a JSON file; copy an existing one. Leave a field `null` if you do not know it
  and the engine will mark the dependent findings *uncertain* rather than guess.
- A rule is an entry in the right layer file with an `id`, a `check` from `ffm/checks.py`, and at
  least one dated version with `params` and a `source`. New check logic goes in `checks.py` and is
  registered in `CHECKS`. Add a test.
- To record a rule change, add a version with its `effective_from` and close the previous one with
  `effective_to`. Old memos stay reproducible because the old version is still in the file.

## What the engine does not do

It does not read PDFs, maps or by-laws for you; the rule files were transcribed by hand from the
cited documents and the `verify` notes say where a figure should be re-checked (the RM-1 schedule,
the TOA tier). It does not model shadows, parking layouts or pro formas. It does not decide: every
`uncertain` and `conditional` is handed to a named person.

## Data, permissions and credit

- The 998 E 19th Ave inputs come from the City of Vancouver's public referral report
  (council.vancouver.ca, 25 Jun 2024 agenda, RR 1) and the Shape Your City page. Nothing in this
  repository comes from a private client file.
- The *what-if* option is hypothetical and says so in its `notes`; none of its figures come from
  Catalyst Community Developments or the City.
- Placeholders that must be replaced before a real use: the red pine DBH (species named, diameter
  not, in the referral report) and the setbacks in the option files.
- Before any practitioner's own project is run through the tool, their permission is asked, and
  nothing confidential is committed here: real sites are run locally and only shareable substitute
  examples are kept in the repository. Practitioners who test the tool are credited below with
  their consent.

### Practitioners (credited with consent)

_To be added after the user sessions._

## Sources

The rule files carry their own citations. The main documents:

- City of Vancouver, referral report, rezoning of 998 E 19th Ave (11 Jun 2024): https://council.vancouver.ca/20240625/documents/rr1.pdf
- Interim Rezoning Policy for Social Housing, Seniors Housing, and Institutional, Cultural and Recreational Uses in Former Community Vision Areas: https://guidelines.vancouver.ca/policy-rezoning-former-community-visions-areas.pdf
- High-Density Housing for Families with Children Guidelines (1992) and the City's Housing options for families page (amendment effective 27 Oct 2026); Protection of Trees By-law 9958; Zoning and Development By-law (social housing definition): see `rules/c_city_policies.json`
- Province of BC, Small-Scale Multi-Unit Housing policy manual and Transit-Oriented Areas policy manual: see `rules/b_provincial.json`
- BC Housing, Community Housing Fund RFP #1070-2526-022 and program page; BC Builds program page; Design Guidelines and Construction Standards: see `rules/d_design_standards.json` and `rules/e_funding_programs.json`
- CMHC, Affordable Housing Fund: see `rules/e_funding_programs.json`

Licence: MIT for the code. The cited documents belong to their publishers.
