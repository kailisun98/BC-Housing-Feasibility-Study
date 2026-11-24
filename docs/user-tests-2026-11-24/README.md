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