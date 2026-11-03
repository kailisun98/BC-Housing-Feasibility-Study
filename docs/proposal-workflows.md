# Proposal: three workflows, a cost layer, a Claude framework, and hosting

Written 3 Nov 2026 for Kai's approval. It answers the four questions from the 2 Nov session and lays out
the build in phases. Nothing here is built yet except the motion and audit fixes already on `main`.
Everything keeps the product's rule: the engine decides deterministically, every number cites its source,
and anything a model or a person proposes is marked as such until a person confirms it.

## 1. The three workflows

### Flow 1, the development manager: site in, approvable option and pro-forma out

A guided run, one input at a time, each with a **Suggested | Mine** toggle. "Suggested" is rule-derived
(section 2); "Mine" is the manager's own figure. The step strip becomes six stops:

| Stop | What happens | Where the numbers come from |
|---|---|---|
| 1 Find the site | Type an address. The tool geocodes it (Nominatim, already in `ffm/osm.py`), reads the **zoning district** and the **parcel polygon** from City of Vancouver Open Data, and the surroundings from OpenStreetMap. Lot area, frontage and depth are filled from the parcel; an odd-shaped parcel keeps its polygon and the tool reports the equivalent rectangle it will use until the massing takes polygons (phase 2). | City of Vancouver Open Data (`zoning-districts-and-labels`, `property-parcel-polygons`; dataset ids to verify), OSM. |
| 2 Choose the programs | Community Housing Fund, BC Builds, CMHC Affordable Housing Fund, the predevelopment loan: tick the ones in view. | `rules/e_funding_programs.json`. |
| 3 Read the site | The tool runs layers A to C on the site alone: outright FSR and height, the rezoning path and its benchmark, SSMUH and transit-oriented status, trees. This is the first memo, before any option exists. | The engine as it is. |
| 4 Shape the option | Storeys, floor area, unit mix, tenure, rent tiers, accessible units, trees to replace: each suggested from the rules for the chosen programs, each overridable. Three named candidates to start from: **Outright** (what the district allows as of right), **Benchmark** (the staff benchmark under the rezoning policy), **Funder-ready** (the largest option that passes every chosen program's criteria). | Section 2. |
| 5 Pro-forma | Capital cost, funding stack, operating budget, supportable debt, the gap, and the program thresholds it must clear. Marked **likely / unlikely / unsure** against each program's rated criteria. | Section 3. |
| 6 Issue | Save the option and the run as a revision, write an issue note, and the architect is told. | Section 5. |

Three views of the result sit on one switch: **Summary** (the three answers, the pro-forma's four
lines, the massing axon), **Detailed** (the full memo as today), **3D** (the site plan with dimension strings,
two sections, the axon, all from `massing.json`; later the parcel polygon).

### Flow 2, the architect: pro-forma in, layouts and drawings out

The architect opens the issued revision and sees the manager's option and pro-forma at the top.
Two tools, both deterministic and both saved into the option file so a run reproduces them:

- **Program and adjacencies, rules in.** Program blocks (units by type, amenity, non-residential, parking,
  circulation, services) with their areas from the option, and adjacency rules in plain words: *next to*,
  *above*, *on the ground floor*, *facing the street*, *away from*. A small stacking solver places the blocks
  on the plates in the envelope and draws the **stacking diagram**, **floor plans by program**, **preliminary
  elevations** (storeys × floor-to-floor, the unit module as the window rhythm, the benchmark and outright
  lines), and the **code site plan** (setbacks, envelope, tree protection circles from By-law 9958, FSR and
  coverage table).
- **Block editor, hands on.** The same blocks on the same plates, dragged into place in plan or axon; the
  engine re-checks areas, adjacencies and the envelope on every move and says what broke. The editor writes
  the same `layout` block into the option file as the solver does, so either path gives a reproducible run.
  (Built second; the solver first, since the editor's checks are the solver's rules.)

A tab switches **Plan | Axon** for both.

### Flow 3, the board, the planner, the funder: the issued set

Reader mode gains the architect's sheets: the code site plan, the elevations, the program plans, after the
three answers and before the ledger; the PDF gets them as numbered figures. Every sheet carries the revision
and the rules date.

### Issuing and notifications

"Issue" is a verb in the tool for the manager (to the architect) and the architect (to the board, planner
and funder). An issue is a dated note written beside the run; the page polls and shows a chip in the top bar
for the other roles: *R4 issued by the manager 3 min ago · Open*. Where it lives is section 5.

## 2. Rule-derived suggestions (build now)

A new engine module, `ffm/suggest.py`, pure standard library, deterministic: given a site, a date and the
chosen programs, it derives an option by walking the layers in order, and records the rule behind every
figure so the memo can cite it:

1. **Envelope** from layer A: outright FSR and height, or the rezoning benchmark where the site qualifies
   (RM-1 under the Interim Rezoning Policy: FSR and height from the staff benchmark; CD-1: whatever the
   manager enters, flagged unsure). Setbacks from the district schedule where encoded, else the option
   placeholders, flagged.
2. **Floor area and storeys** from the envelope: plate area × storeys within height, floor-to-floor 3.3 m,
   at most 85% of the plate as net residential (an efficiency placeholder, declared).
3. **Unit mix** from layers C, D and E: BC Housing minimum net areas (33 / 49 / 67 / 86 m²), the family
   rule (35% two-bed-plus, 5% three-bed), and the program's tier split (CHF 30 / 50 / 20), solved for the
   most units that satisfy all three; accessible units at the program's 5% minimum.
4. **Tenure, agreement, below-market share** from the program's criteria (60-year agreement, 100%
   secured rental, 20% below market).
5. **Trees** from By-law 9958: the Schedule C minimum for the site area, less the trees retained, as the
   replacement count.
6. **What stays unsure**: the transit-oriented tier, a CD-1 negotiation, land tenure, DCC waivers. The
   suggestion names them and leaves them to the person, as the memo does today.

Each suggested field carries `{value, rule_id, note}`; the UI shows the rule beside the toggle. A suggestion
is never applied silently: the manager accepts it per field or types their own. Evaluation cases: the
998 E 19th Ave site should suggest an option that passes the funders (it should land near the funder-ready
what-if), the 1010 Expo Blvd site should come back mostly unsure (CD-1), a 280 m² lot should hit the SSMUH
minimum.

## 3. Costs and revenues: a sixth layer that refreshes itself

The best way to keep assumptions current is to treat them exactly like rules: a **layer F, assumptions**,
in `rules/f_assumptions.json`, every figure dated and cited, with versions, so the memo's stamp covers them
and a change shows as a change. Where a public body publishes machine-readable data, a `python -m ffm
refresh` command fetches it and writes a new dated version; where only a PDF exists, the command says what
to check and a person types the figure with its citation. No figure is ever silently invented.

| Assumption | Source | Refresh | How it is used |
|---|---|---|---|
| Hard cost base, $/m² by building type | BC Housing standardized housing designs, Class D costs (public catalogue, 2024) | By hand, when the catalogue updates; `verify` date | The base for capital cost |
| Escalation to today | Statistics Canada, Building Construction Price Index, Vancouver, residential (table 18-10-0135-01) via the WDS REST API | Automatic, quarterly | Escalates the base to the as-of date |
| Soft costs, contingency | A declared share of hard cost (placeholder until a practitioner gives a figure) | By hand | Capital cost |
| Land | Nominal lease where the owner is a church or municipality; else BC Assessment value entered by hand | By hand | Capital cost |
| Grants | CHF provisional grant per unit (already in layer E: $171,211 at 2025-26), BC Builds terms | With layer E | Funding stack |
| Mortgage rate and amortization | Bank of Canada Valet API (conventional 5-year series), CMHC insured terms | Automatic, daily | Supportable debt |
| Rents by tier | CMHC Rental Market Survey, Vancouver CMA, by bedroom count (annual data tables); HILs from BC Housing (already in layer E) | Annual table fetch; HILs by hand | Operating revenue; RGI and deep-subsidy rents from income limits |
| Operating cost per unit, vacancy | BC Housing operating benchmarks where published; else a declared placeholder | By hand | Operating budget |

The pro-forma module, `ffm/proforma.py`, is then arithmetic over layers E and F: capital cost = hard × escalation
+ soft + land; funding = grants + equity + supportable debt (from net operating income at the program's
debt-coverage ratio); the gap is what is left; the "likely" verdict compares the result with the program's
rated thresholds (CHF: development 35%, operations 25%, already in the rule file). Every line prints its
source. This is feasibility-grade, not a lender's model, and the memo says so.

Alternatives considered: a paid cost database (RSMeans, Altus) gives better hard costs but a licence and
no public citation; a model estimating costs from drawings is a guess with no source. Public data plus a
person's check wins on the product's own terms.

## 4. A framework for Claude in the loop (for approval; not built yet)

Odd-shaped sites, scanned surveys and unfamiliar districts are where a person today reads a document and
writes down facts. The framework gives that job to the model under the same discipline as everything else:
**the model proposes, a person confirms, the engine decides.**

Where it would help, in order of value:

1. **Reading a site.** Given the parcel polygon, a survey PDF or a photo of a site plan, propose the site
   file's fields: lot geometry and its equivalent rectangle, frontage street, easements, existing
   buildings, trees with species and diameter, slope notes. Structured output (tool use with a JSON
   schema matching `sites/*.json`), each field with a confidence and the evidence it came from.
2. **Reading a rule.** Given a by-law section or a program guide, propose a rule clause for `rules/`:
   parameters, section, effective date. This is the "extract rules, once, offline" step in the diagrams.
3. **Explaining.** Plain-language explanation of an open item for a board reader, generated from the
   ledger's own text, never from the model's knowledge.

Guardrails, all of them:
- Proposals land as `suggested` values with `source: "claude"`, a confidence, and the evidence excerpt;
  nothing enters the run until the person presses Confirm, and the memo prints "site facts confirmed by
  <name> on <date>" against each confirmed field.
- The model never sees or writes a status; the engine computes pass, conditional, fail and uncertain
  from confirmed inputs only, so a model swap changes nothing in the ledger.
- Runs are reproducible from the saved site file; the model call is logged (model id, date, prompt
  hash) beside it.
- Public repository rules hold: a practitioner's survey is read locally and only the site file is kept.
- Evaluation: a held-out set of sites with hand-made site files; the proposal is scored field by field
  against them before any default changes.

Mechanics: `claude-sonnet-5-5` for extraction (cost and speed), `claude-fable-5-1` for the hardest
surveys if the eval shows it earns it; the Messages API with tool use for structured output, prompt
caching for the by-law text, PDFs sent as documents, images for plans. A `ffm/propose.py` module behind a
`FFM_CLAUDE_KEY` environment variable; without the key the Suggested toggle offers rule-derived values only.
Expected cost per site read: a few cents. Nothing runs on GitHub Pages; the model is called from the local
server or the hosted backend.

## 5. Hosting on kailisun.com

What I found: `kailisun.com` is served by **Wix** (nameservers `ns6.wixdns.net`, `ns7.wixdns.net`).
Wix hosts pages and its own Velo scripts; it cannot run the Python server, and its data collections are
not a fit for the run folders.

What works, in order of cost:

| Option | What it gives | Cost |
|---|---|---|
| **A subdomain to GitHub Pages** (`firstread.kailisun.com` → a CNAME in Wix's DNS) | The site and the tool as today, the engine in the browser, the committed runs; no issuing. | Free. |
| **A plus a tiny issue store**: Cloudflare Workers + D1 (or KV) behind `api.kailisun.com` | Issues and notifications shared across machines; the page polls it. The engine still runs in the browser. Needs a shared project passphrase so only the project's people can issue. | Free tier covers it (100k requests a day). |
| **The Python server hosted**: Fly.io, Render or Railway, `app.kailisun.com` | Everything the local server does (runs written to a folder, PDF printing, the Revit instructions), for several people at once. | Render free tier (sleeps when idle) or $7/month; Fly.io about $2 to $5/month; Railway $5/month. Plus a volume for the run folders, about $1/month. |
| A managed backend with accounts (Supabase, Firebase) | Logins, per-project permissions, live updates without polling. | Free tier, then about $25/month; a day of work to wire. |

Recommendation: A now (free, one DNS record), and the Cloudflare issue store when issuing is built (free,
no servers to keep). The hosted Python server only if the Revit hand-off or PDF printing must be shared.
Privacy: anything behind the issue store is still only public-source data unless Kai decides otherwise;
real practitioner sites stay local, as the brief requires.

## 6. Build order

| Phase | What | Depends on |
|---|---|---|
| 1 | `ffm/suggest.py` with tests; the guided six-stop manager flow with Suggested \| Mine; the site lookup from City Open Data; Summary \| Detailed \| 3D; issuing with local polling | **Built 3 Nov 2026** (approved the same day) |
| 2 | Layer F and `refresh`; `ffm/proforma.py` with tests; the Pro-forma stop and its view | **Built 3 Nov 2026.** The hard-cost base is the Province's Class D catalogue figure (2- to 4-unit designs; a six-storey figure should replace it); soft, contingency, operating and the RGI income are declared placeholders; StatCan and the Bank of Canada refresh by command; CMHC rents by hand from the data tables |
| 3 | Program blocks, adjacency rules, the stacking solver; stacking, plans, elevations, code site plan; Plan \| Axon; the board's sheets in reader mode and the PDF | **Built 3 Nov 2026** (`ffm/layout.py`: blocks from the option and layer D, seven adjacency rules in plain words that `option.layout.adjacencies` can override, a stacking solver that places every unit whole or says it did not fit, five SVG sheets with the stamp; FIG 03 to 06 in the tool with a Plan \| Axon tab, Figures 3 to 6 in the paper memo, a "Layouts" section in memo.md). The what-if on 998 E 19th Ave places 58 of its 88 units on five 1,400 m² plates: the rest is said, not squeezed |
| 4 | The block editor over the solver | **Built 3 Nov 2026**: "Edit blocks" on FIG 03 in architect mode; drag, resize, move between floors, add and remove, keyboard too; the engine measures every move (`layout.place_zones`) and names what broke; Apply writes `option.layout.zones`, which `solve()` re-checks instead of re-solving, so a run reproduces the hand placement and the memo says so |
| 5 | Hosting: the subdomain, then the Cloudflare issue store | Kai's DNS access |
| 6 | The Claude framework behind a key, with its eval set | **Built 3 Nov 2026** (`ffm/propose.py`, `propose` and `confirm` commands, Ask Claude in stop 1, a synthetic eval case). Waits on Kai's `FFM_CLAUDE_KEY` to run against the real RT-3 schedule, which the City's by-law site will not hand to a script: save the PDF, then `propose rule --from … --district RT-3`, then `confirm` |

Each phase lands as its own commit with its tests, and the site's "Who it's for" page is updated as the
flows grow.
