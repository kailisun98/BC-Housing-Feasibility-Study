# Second simulated panel, 24 Nov 2026

**Four AI role-plays, not practitioners.** Three architects (a small-lot practice doing multiplexes and 3 to 6 storey
wood frame; a large practice doing towers on transit and CD-1 sites; a practice doing supportive, shelter, transition and
Indigenous-led housing) and a non-profit housing operator re-reviewed First Read after the first panel's fixes. Each ran
the tool from the command line and its JSON API on real public Vancouver addresses, in a scratch folder outside the
repository, and critiqued the user flows. Never quote these as practitioners' statements or credit them in the README.

Reports: `architect-small-lots/`, `architect-towers/`, `architect-supportive/`, `operator/`.

Note on timing: another session was editing the page and layout code while the panel ran (it committed `ec1a478` and
left more uncommitted). Every defect below was re-run on the code as it stands after that work, on the reviewers' own
input files; all twelve checked still reproduce.

## Verified defects, ranked by harm

| # | Defect | Seen by | Re-run result |
|---|---|---|---|
| 1 | **A short operating subsidy is borrowed against for 40 years and the money turns "likely".** A confirmed 3-year subsidy is added to NOI before debt is sized; no term field. | Operator | NOI -$1,427,320, debt $977,091, verdict *likely* |
| 2 | **The TOA candidate ignores the tier's FSR.** A tier-1 CD-1 site is derived at 20 storeys and FSR 11.19 where the tier protects 5.0; the memo prices it. | Towers | 20 storeys, 14,404 m², FSR 11.19 |
| 3 | **The front the tool picks flips the outright answer.** At 1130 Jervis the lookup's front applies RM-5B's narrow-site cap unnamed: *fail, rezoning required*; fronted on Jervis: *conditional to 2.75*. | Supportive | fail vs conditional, same building |
| 4 | **"Rezoning is required (none)"** beside "By rezoning: not needed": the fail branch reads `rezoning_path`, not `approval_route`. | Supportive | reproduced |
| 5 | **A building with supportive homes and shelter beds reads as independent rental** and needs no subsidy to run (Glen Drive: 25 supportive homes, an 80-bed shelter). | Operator | kind *independent*, NOI +$1.65M |
| 6 | **A shelter's operating page drops the operator's figures** ($2.4M staffing, $2.9M subsidy → null) and asks for a unit mix. | Supportive | staffing None, subsidy None |
| 7 | **The money is rosier the less is answered**: no rent tiers counts the CHF grant ($890,295, 28% gap); real tiers fail the mix, $0, 78%. | Small lots | reproduced |
| 8 | **Outright "yes" on a 2.5 m plate with no homes**, no warning; the envelope's own width (3.4 m) is lost to the 0.5 m grid. | Small lots | yes, 2.5 × 21.3 m, warnings [] |
| 9 | **RT-5's side yard is 1.5 m flat** where the schedule gives 10% of the width up to 15 m (0.76 m on a 7.6 m lot). The rule I wrote has the clause in its note and not in the test. | Small lots | min side 1.5 on a 7.6 m lot |
| 10 | **An envelope larger than the lot**: 138.02 × 32.82 m = 4,530 m² on 488 Kingsway's 2,850 m² polygon, with a false "no envelope" warning on rectangles. | Supportive, Towers | reproduced |
| 11 | **The mass is taller than the height tested**, silently when the stated height is the smaller (Harwood: 37.0 m tested, 39.6 m built and sent to Revit). Revit plates also ignore a taller ground floor. | Towers, Supportive | 37.0 vs 39.6, warnings [] |
| 12 | **A supportive building with no staffing still prints a bold subsidy** ($110 a home a month). | Operator | reproduced |
| 13 | **The money's next step names CMHC's Affordable Housing Fund**, closed 19 Dec 2025 by the tool's own rule; and for Province-funded supportive housing it shows a 100% capital gap. | Small lots, Supportive, Operator | reproduced |

Not re-run but specific enough to fix: the tower solver's 43% cores marked "placed: all" and four exits on a 537 m²
plate; zero yards breaking a rectangular envelope; a "nearest parcel" kilometres away and a district read from the
geocoded point instead of the parcel; the grant line calling $178,059 the 2025-26 rate; help text still quoting
half the fund's limit, $500 and the 2025 CHF limits; memo Sources listing every schedule in the stack; the corner-lot
note when `cross_street` is null; owner-type vocabularies that disagree.

## What the four agree the flows get wrong

1. **The building model is one apartment type.** Every option becomes a double-loaded slab with a lift core: wrong for a
   sixplex (no ground-oriented homes, no home over two floors), wrong for a tower (no podium, plate fixed at 21 m deep,
   wood frame capped at six storeys in every suggestion), wrong for supportive housing and shelters (no desk, staff,
   clinic, dining, laundry; beds never placed). Three of four ranked a typology change first.
2. **The suggestion comes before the questions that should shape it.** The kind of housing, beds and the operator are
   asked at stop 02 after the option is derived; `suggest.py` never reads `housing_type`. The three candidates are one
   building on most sites.
3. **The money answer does not follow the program answer.** Answer 2 says the Province pays a supportive building's
   capital; answer 4 shows a 100% gap and sends the board to a closed fund. Operating risk is framed as a capital gap.
4. **The operator has no place in the flow.** `docs/user-flows.md` has no one who runs the building; the operating
   figures are entered by the manager just before Run; nothing asks, issues to or records the operator; reserve and
   vacancy cannot be edited; open items never name the operator.
5. **"Allowed" is answered before "what the lot takes".** Read-site gives no envelope; the envelope appears only once an
   option exists. Use permissibility (a shelter, a clinic) is never asked. "Outright" is printed over Director's
   discretion.
6. **Area and efficiency are invisible.** No net-to-gross, no area schedule, no lift count; a 34%-efficient plate passes.

## What they would add (merged, by size)

**Small:** subsidy term; per-bed operating page; withhold the subsidy figure without staffing; cap TOA at the tier FSR;
mass/tested height warning both ways; "no buildable plate" instead of yes; narrow-lot side yards; no grant the option
cannot get; drop closed funds from next steps; Outright / Conditional / Rezoning as three verdicts; confidential-address
mode for transition housing; editable reserve, vacancy and bad debt; lookup refuses a distant "nearest" and reads the
district from the parcel; a short memo for small sites.

**Medium:** envelope and yield on read-site (schedule homes vs SSMUH homes); an area schedule with net-to-gross; use
permissibility per district; a suggester that reads the kind of housing (all-studio supportive, beds for a shelter);
answer 4 following answer 2's program model; mixed-program buildings in components; TOA tier from the station distance;
podium plates and per-level heights through to Revit, with a base point and true north; lanes from City data; site
assembly; site by PID or by drawing a lot; a stress test and 60-year view; an Operator lane in open items.

**Large:** ground-oriented and tower typologies in the solver and the block editor; a program brief by housing type
(desk, staff, clinic, meals, laundry as blocks with adjacency rules); a construction-type switch (wood, mass timber,
concrete) setting storeys, floor height, cost basis and core; an operator flow (an operating request at stop 02, an
Operator mode, figures signed and dated, an Operator lane).

## What they trust

Every yard and FSR line cites its clause; CD-1 "not assessed" names the missing by-law; "listed, not tested" programs;
open items naming who to ask; the civic-number guard; supportive staffing never assumed; an unconfirmed subsidy holding
the verdict back; runs under half a second; respectful, accurate language about the people housed. The tower reviewer's
summary: honest about what it does not know, less careful about the numbers it makes up itself.

## What was fixed the same day

All thirteen verified defects, each with a test in `TheSecondPanelsDefects` (`tests/test_user_tests_2026_11_23.py`):

| # | Fix |
|---|---|
| 1 | `operations.subsidy_term_years`: a loan is sized on a confirmed subsidy only where its term covers the amortization; a building that runs on a shorter agreement reads at most "unsure", with its renewal as an open item. |
| 2 | The transit-oriented tier's FSR caps the derived floor area (`suggest.envelope_for`). Joyce at tier 1 now derives FSR 5.0, not 11.19. |
| 3 | On a corner lot where the other street as the front would allow the floor area, the density answer is uncertain, names the narrow-site cap and the other front's figure, and asks the City which street is the front (`checks._other_front_fsr`). |
| 4 | Over the outright limits, the finding reads the approval route: a permit route says a permit cannot approve it, never "(none)"; the by-rezoning answer reads "needed" (`checks._over_outright`, `engine.summarise`). |
| 5 | `checks.housing_parts`: supportive homes and shelter beds beside independent homes are parts of the building. Staffing is then asked for, programs and the bed-space rule apply to them, and an open item says the funders answer does not test them. Glen Drive's 80-bed shelter is now entered as `beds`. |
| 6 | A shelter counted in beds keeps the operator's staffing, subsidy and per-bed running cost, reports per bed, and no longer asks for a unit mix. |
| 7 | No Community Housing Fund grant is counted without rent tiers. **998 E 19th Ave as approved (R1) now reads a 56% gap ($30.5M), not 22%**: it has no tiers, so the fund's mix was never tested. |
| 8 | An envelope narrower or shallower than 5.0 m (`checks.MIN_ENVELOPE_M`, a declared placeholder) is no envelope: the outright answer reads "not yet confirmed". Where the option's own yards exceed the schedule's, the finding says so. |
| 9 | RT-3, RT-4, RT-5, RT-8 and RT-10 test the narrow-site side yard (10% of the width up to 15 m, 12 m for RT-10) as `side_yard_narrow`. |
| 10 | `boundary.inset` counts a corner on the lot line as inside, so zero yards no longer fall back to a rectangle larger than the lot. |
| 11 | The massing warns when the storeys need more height than the option states; `massing.json` carries `level_z_m`, which the Revit script uses for its floor plates. |
| 12 | With staffing missing, the subsidy needed is withheld and the table says why. |
| 13 | No program is named in the money's next step; supportive, transitional and shelter housing are pointed to their program's own capital route; the whole-gap borrowing illustration is not shown for them. |

Also: the operator can enter the replacement reserve, the vacancy rate and the subsidy's term at stop 03, and who pays it;
the help text matches the engine (BC Housing's RGI estimate, the shelter allowance by bedrooms, the 2026 fund limits);
the grant line names the fiscal year its rate is for; the operating note says "the operator's own" when they are.

## Still open from this panel

Not built (each is a piece of work of its own): ground-oriented and tower typologies in the solver and the block
editor; a program brief by housing type (desk, staff, clinic, dining, laundry as blocks); an operator flow and an
Operator mode; the envelope and yield before an option; an area schedule with net-to-gross; use permissibility per
district; a suggester that reads the kind of housing; podium plates; a construction-type switch; TOA tier from the
station distance; lanes from City data; site assembly; a site by PID or a drawn lot; a stress test and 60-year view;
a confidential-address mode; Revit base point and true north; the lookup's distant "nearest" and its district read from
a point; memo Sources filtered to the rules that apply; a short memo for small sites.

Fingerprints after these fixes: d8114c4301640d47 (23 Oct), 9da6dabc8def1912 (27 Oct), c0cd775dd41c5779 (17 Nov). 373 tests.

## Built the next day: the operator flow, the program brief, two building types, the area schedule (24 Nov 2026)

Four of the larger requests above, at Kai's request. Every new figure is a declared placeholder listed in the layout's
`assumptions`.

- **The area schedule** (`layout.area_schedule`, in every `layout.json`; `area-schedule.csv` beside each run; a table and
  a CSV download under the drawings in every layout; a section in memo.md): homes by type and floor, the floor area by use
  (homes net of their partitions, circulation, cores, program, amenity, services, non-residential, spare), gross, and net
  to gross, flagged under 70%.
- **Building types** (`option.building_type`, asked at stop 02):
  - *Ground-oriented* (`layout._solve_ground_oriented`): rows of homes across the plate, each running up through its
    floors with its own door and stair; over three storeys they stack two storeys at a time; a deep plate takes a front
    and a rear building with a courtyard. No corridor, core or lift; amenity only from 12 homes. Exits: each home its own
    door; stacked upper homes are a Part 9 placeholder.
  - *Tower* (`massing` `tower`, `layout._solve_tower`): `podium_storeys` on the plate the floor area allows, and a tower
    plate of `tower_plate_m2` (650 m² placeholder) over it, each laid out with its own core and joined; the podium roof is a
    cut-out on the tower floors; the 3D view stacks the two tiers.
  - *Apartment* is the solver as it was.
- **Lifts by home count** (`layout.lifts_needed`): none for ground-oriented homes or a walk-up; one per 70 homes; at least
  two over six storeys (placeholders for an elevator analysis).
- **The program brief** (`option.program_brief`, `layout.program_brief`, `ffm/ui/brief.js`): the spaces a kind of housing
  runs on — supportive: a 24/7 desk by the entry, staff office and washroom, program room, kitchen and dining (in place of
  the amenity room), laundry, a harm reduction room; shelter: desk, staff office, sleeping rooms (four beds, 4.6 m² a bed,
  on the upper floors), washrooms, dining, laundry, lockers; transitional; and the parts of a mixed building. Editable at
  stop 02 and on the operator's desk. The suggester derives all studios for supportive housing and no homes for a shelter.
- **The operator flow** (`docs/user-flows.md` Flow 4): an Operator layout; the operator's desk with the operating figures,
  the brief and *What an operator checks first* (`layout.operability`); a signature (`operations.signed`) the memo prints;
  an Operator lane in answer 3 (`engine.operator_items`: figures not signed, subsidy not confirmed, a term shorter than the
  loan, the staffing); the manager can issue to the operator and the operator back.

The PDF (`paper.js`) prints them too, as their own section after the massing (`areasPaper`): the area schedule, the brief and what an operator checks first, with whose the operating figures are. Not done: the Revit script does not yet build the tower's two tiers as separate
masses (it reads `level_z_m`). Glen Drive as proposed now reads eight open items (the operator's two added).

## The gaps in what was built, closed (24 Nov 2026, later)

- **Accessible ground-oriented homes are drawn.** `_solve_ground_oriented` places each accessible home first, as a
  one-floor home at grade on the front row (the smallest type), with a home over it that runs up through the floors
  above, reached by its own stair (a garden flat under a townhouse). The warning that none were drawn now appears only
  when the front row's ground floor has no room left for one.
- **The building type is suggested.** `suggest.suggest_building_type(option)`: ground-oriented for at most
  `GROUND_ORIENTED_MAX_HOMES` (12) homes on at most three storeys, a tower from `TOWER_MIN_STOREYS` (12), an apartment
  building otherwise; supportive housing, transitional housing and shelters stay apartment buildings (a staffed entry).
  Both thresholds are declared placeholders. The suggestion returns it as `building_type_suggested`, offered and never
  applied unasked. Stop 02 shows it under "What kind of building?" with its reason and a *Use it* button
  (`typeOffer` in route-stage.js).
- **A home over several floors is edited as one.** `place_zones` keeps a zone's `home` and `levels`, counts the home
  once (on its entry floor), checks each floor's share of its area, asks for no corridor, core or lift on a
  ground-oriented plan, and reads the exits with `_ground_egress`; `zones_of` carries `home` and `levels`. In the block
  editor (`syncHomes` in editors/blocks.js), moving, resizing or removing a home on one floor does the same on every
  floor it spans. Checked in the browser: a home moved on the ground floor moved on floors 1 and 2.

## The memo as an ask (24 Nov 2026, piece 1 of the plan in `00 Research\First Read - wish list and plan.docx`)

Asked for by all four reviewers of the first panel (a front sheet, named capital sources) and by the second (three
verdicts, a short memo, Sources that list only what applies).

- **The front sheet.** Every memo opens on "The ask": who is housed (homes, beds, tenure, rent tiers), who operates (and
  whether the operating figures are signed), which program, the amount (the capital cost, what is asked of whom with its
  status, what is still to find), the decision wanted (`option.decision_sought`, asked at 03 as "What are you asking
  for?"), the answers in one line, and the top three open items, failures first. `memo.front_sheet` /
  `front_markdown` in the engine; `memo/front.js` (`frontOf`, `frontHtml`) on the page, first in the sheet index; the
  first thing after the title block on paper. It adds no figure of its own.
- **Three verdicts in answer 1.** `engine.routes` → `summary.answers.allowed.routes`: outright (the district's limits as
  written), by the Director's discretion (possible, not needed, none in the schedule, no; a discretionary approval is
  never assumed), by rezoning (as before). The `outright` and `by_rezoning` keys are unchanged. A building within the
  Director's discretion now reads "Not outright: within what the Director of Planning may allow", not "Outright, with
  conditions". Under answer 1 on screen, as three rows on paper, as one line in memo.md.
- **Capital sources with a status.** `option.finance.sources` [{name, kind, amount_cad, status}] (grant, equity, loan,
  land, other; committed, applied, assumed), rows at 03 under "Land, equity and other grants". Each is counted in the
  funding; a stack that closes only with sources not yet committed reads Unsure and says how much rests on them.
  `finance.land_value_cad`: above the land figure, the difference is the land owner's contribution, listed in kind and
  not counted. `proforma.funding.sources` is the contributions ledger (every source with its status: committed,
  applied, assumed, illustrative, entered, sized, in kind, not counted, to find), shown as "Where the money comes from"
  in answer 4, in memo.md and on paper.
- **A short memo.** `memo-short.md` beside every run, and "Short PDF" under More formats: the ask, the answers, the open
  items, the money and the sources; the clauses, drawings, ledger, inputs and reproduction notes stay in the full memo.
  On 998 E 19th Ave funder-ready: 25 KB against 68 KB as Markdown, 79 KB against 286 KB as paper HTML.
- **Sources** in memo.md list only the sources of the rules that apply here (the paper already did).

Checked in the browser on 998 E 19th Ave funder-ready: the front sheet, the three verdicts and the sources table on
screen and at phone width; a source, a land value and the decision entered at 03 and run (the CHIP grant shown as
applied for, the land owner's $6.0M in kind, still to find $18.7M); the short paper in a frame. No console errors.
Not checked: a PDF printed through the server's Edge (the paper HTML is the same one the PDF prints). The seven committed
runs were regenerated: every answer, gap and fingerprint is unchanged; ledgers gain `routes`, pro-formas the
contributions ledger, and each run a memo-short.md. 409 tests (`tests/test_memo_as_an_ask.py`).

## The site before an option (25 Nov 2026, piece 2 of the plan)

Both panels: "allowed" was answered before "what the lot takes", use permissibility was never asked, the transit tier
was left unsure 150 m from a SkyTrain station, lanes were never read, and the lookup offered a "nearest" parcel
kilometres away with the district read from the wrong point.

- **What the lot takes**, at 02, before any option (`suggest.lot_reading`, in `read_site`'s `lot`): the plate the yards
  leave (which yards are the schedule's and which placeholders), the building the schedule allows outright with the
  homes it holds at the starting mix, the provincial small-scale minimum beside it (`suggest.ssmuh_homes`: its zones,
  the exempt lot size, a transit-oriented area, water and sewer, the frequent bus stop), and the use table's word on an
  apartment building, ground-oriented homes, a shelter and a clinic. On 609 Heatley Ave (RT-3, the lane taken): a
  11.5 × 17 m plate, 3 storeys and 340 m², about 4 homes, beside the provincial minimum of 4.
- **Uses.** 32 new layer A rules (`cov.<district>.uses`, check `district_outright_use`), one per district or district
  group of the 17 schedules Kai saved, each read from the schedule's own use table (s.2.1) by a script that kept every
  row's wording and page; rows written for a building already on the site ("existing as of…", "retention of…",
  conversions) are left out. The check reads the option against it: an outright approval use passes; a conditional
  approval use is conditional and counts as the Director's discretion in answer 1's three verdicts; an apartment
  building the table does not list fails (a rezoning is the path); a shelter is always a question for the City (it may
  be a group residence, a social service centre or a care facility); an option that proposes a rezoning reads info (the
  rezoning sets the uses). What the tables say, among others: RT-4 and C-2A list no apartment building for a new
  building (C-2A only as a mixed-use residential building), R1-1 a Multiple Dwelling of at most 8 homes as conditional,
  RM-10 to RM-12 an "Apartment", RR-1 and RR-2 rental townhouses only, M-1 a social service centre and no housing.
  The Downtown-Eastside/Oppenheimer plan and the CD-1s have no use rule.
- **The district from the parcel.** The lookup reads the zoning at the parcel's centre (`extra.zoning_centre`), and says
  where the address's point fell in another district: 1065 Harwood St now comes back as 1055 Harwood St in RM-5A, with a
  note that the point fell in CD-1 (852).
- **A far "nearest" refused** (`lookup.refuse_nearest`): on another street, more than a block of civic numbers away
  (100), or more than 50 m from the City's nearest number on the same side of the street. Nothing is written or
  printed; the page offers "Look up 3683 E Hastings St" instead of "Use this site" (3680 E Hastings St had come back as
  117 E Hastings). The web build's own lookup now asks the City for the numbers near one it lacks, so it names the
  nearest too.
- **Suggested, never applied** (`site.suggested`): the transit-oriented tier from the nearest SkyTrain station in the
  City's station data (tiers 1 to 3 by the distance to the lot's nearest edge; 1290 Burrard St, about 700 m from
  Yaletown, is offered tier 3) and a lane behind the lot from the City's `lanes` dataset (the streets dataset holds
  none), with its distance to the rear lot line, which RT-3's lane clause reads. Each is offered under its question at
  01 with its reason and a Use it button. Past 800 m nothing is suggested, since a bus exchange's tiers 4 and 5 are not
  in the station data (3475 E Hastings St is tier 4 beside the Kootenay Loop, 2.3 km from a station); the question
  names the nearest station instead.
- The command line's lookup prints every suggestion and the district note on stderr; stdout stays the site's JSON, or
  nothing for a refused lookup.

Checked live against the City's data (3680 E Hastings, 1065 and 1055 Harwood, 3475 E Hastings, 609 Heatley, 998 E 19th,
2475 E 5th, 4250 Fraser, 1290 Burrard) and in the browser (the refusal and its button, the lane offer taken and the
rear yard following it, What the lot takes, a run with the conditional use in answer 1). Not checked: the web build's
lookup in the browser. The rule files changed, so the fingerprints moved: 7846c8b6a3414798 (23 Oct), 750597987a837e2e
(27 Oct), 7532496a9e6ef1ff (17 Nov); every committed run's answers, gaps and open items are unchanged (998, Expo and
Glen Drive have no use table). 423 tests (`tests/test_site_before_an_option.py`).

