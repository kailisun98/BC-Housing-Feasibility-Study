# Third simulated panel, 25 Nov 2026: the website and the tool, in the browser

**Five AI role-plays, not practitioners.** A development manager (a society redeveloping its own land, with youth and
transitional housing), an architect for small lots (multiplexes, townhouses, 3 to 6 storey wood frame), an architect for
towers, CD-1s, supportive housing and shelters, a non-profit operator, and a reader who is both a funder-side officer
and a board member. They cover both earlier panels' seats. Never quote these as practitioners' statements or credit
them in the README.

Unlike the first two panels, they walked the website and the tool in a browser, each on its own copy of the tool (ports
8791 to 8795) in its own tab, with Opus. Reports: `manager/`, `architect-small-lots/`, `architect-towers-supportive/`,
`operator/`, `funder-board-reader/`. The harness does not let a subagent write files, so the coordinating session saved
each report from the text the reviewer returned.

Two things about the setting, so the findings are read fairly:
- **One outputs folder for five servers.** Each reviewer saw the others' drafts in its run lists and "a run issued to
  you" chips from people it never met. That is an artefact of the test, but it points at a real gap: the tool records no
  identity, so "issued to you" means whoever opened the page.
- **Another session was changing the block editor and the layout while the panel ran** ("Block editor UX
  improvements": small rooms regrouped, a "Massing and plans" button). Some editor findings may describe that work in
  progress; they are marked.

The reviewers' runs (17 folders) were deleted afterwards; the committed runs are untouched by the panel.

## Verdicts

| Seat | Would use it next week? | What stops them |
|---|---|---|
| Development manager | As a private 10-minute pre-screen, not for the board | Community space in the brief is ignored; reopening R1 loses its inputs; answer 1 contradicts itself; transitional housing costed as rental |
| Architect, small lots | Only for the parcel and use-table lookup | The Director's discretion misread on RT-3; answer 1 contradicts itself; ground-oriented plans place 2 or 3 of 4 homes; the editor loses townhouses |
| Architect, towers and supportive | Not in front of a client or BC Housing | Supportive homes at market rent; lifts passed that are not drawn; a 6-storey shelter as a walk-up; the tower's section has no tower |
| Operator | Would not sign operating figures | Signed figures vanish on reopening; one budget for a shelter, supportive homes and rental; beds carry no running cost; a loan counted as a grant |
| Funder-side officer / board member | Officer: an intake checklist, not a pre-application. Board: would not vote | No decision stated; a 4-unit cost rate on towers, unmarked; approved rezonings asked again; the comparison's gain is a grant nobody offered |

All five trusted the same things: the lookup and its refusal of a far parcel, the use tables with their pages, "not
assessed" where the rules do not reach, open items with a named person, the UNVERIFIED and placeholder tags, the
programs listed with their intake, "illustrative: nobody has offered it", and the speed.

## Verified defects, ranked by harm

Each was re-run by the coordinating session from the reviewers' own run inputs (`ledger.json`) or read in the code,
before the runs were deleted.

| # | Defect | Seen by | Re-run |
|---|---|---|---|
| 1 | **Reopening a run loses its inputs.** The operator's signed figures, the capital sources and the manager's option come back blank or as a fresh suggestion; the next Run again silently runs a different project. Cause: `runs.syncInputsTo` loads the saved option file when the run's option id names one, not the run's own inputs; the manager's route re-derives at 02. | Operator, manager, towers | Confirmed: the manager's run after the operator's had no `operations` |
| 2 | **Supportive and transitional homes are priced as Community Housing Fund rental.** 1290 Burrard: 78 supportive studios at market rent ($1,837,368 a year); 609 Heatley transitional: 2 market, 3 RGI, 1 deep. | Towers, manager | Confirmed |
| 3 | **Answer 1 contradicts itself on a conditional use**: "Outright: No · the building is a conditional approval use" beside "By rezoning: Not needed · the option is allowed outright", and "Allowed today, no vote needed" in the drawing. Introduced with the use rules (piece 2). | Manager, small lots | Confirmed on 609 Heatley |
| 4 | **RT-3's Director's discretion is not read.** FSR 0.67 fails "no rezoning path", although s.3.1.1.1 lets the Director allow 0.75 and s.3.1.1.2 1.00 for a non-profit multiple dwelling; both figures are in the rule (`max_fsr_conditional`, `max_fsr_affordable_multiple_dwelling`), and `fsr_limit` returns no discretionary figure. | Small lots | Confirmed |
| 5 | **Community and office space in the program brief is not non-residential floor area.** 3475 E Hastings with a 450 m² hall and 900 m² of offices: C-2's rental FSR reads "this option has 0 m²" and fails; BC Builds counts 0 m²; the entered cost a m² for those floors is dropped. | Manager | Confirmed |
| 6 | **Lifts.** "Elevators PASS 4 elevators" on 1290 Burrard, whose tower floors draw a 7 × 7 m core holding a scissor stair and no lift; an 80-bed, 6-storey shelter reads "no elevator: a walk-up" (the rule counts homes, not beds). | Towers | Confirmed |
| 7 | **A mixed building's operating page.** Glen Drive's 80 beds carry no running cost or reserve ($8,500 × 163 homes only); the whole subsidy need is divided both per home ($1,408) and per bed ($2,868), as if each were the full cost; support staffing nets the debt to $0. | Operator, towers | Confirmed |
| 8 | **A capital source of kind "loan" is counted as funding and never repaid**, with the full mortgage still sized on the same net income. | Operator | Confirmed (code and a re-run) |
| 9 | **The hard cost is a 2- to 4-unit catalogue rate, applied to towers, and not marked a placeholder**; "Placeholders in use" lists only soft costs and contingency. Every gap rests on it. | Reader, towers, manager | Confirmed |
| 10 | **Homes that do not fit the plans are still priced and funded**: 609 Heatley transitional, "0 of 6" placed with "Egress … pass"; the ground-oriented solver places 3 of 4 on 609 Heatley and 2 of 4 on a 10 m R1-1 lot (2475 E 5th). | Manager, small lots | Confirmed |
| 11 | **The tower's section and caption**: "plate 1,750 m² × 18 = 15,000 m²" (31,500); the tower tier carries no plate area; the section draws the podium and a line. | Towers | Confirmed |
| 12 | **The operating table does not add up** when the floors that are not homes earn income: the income has no line (3475: rows sum to $593,000, "left" $653,000). | Manager | Confirmed |
| 13 | **Vacancy**: "2" is read as 200% and can be signed; the vacancy line always says "the CMHC survey's rate" even when the operator's own was entered. | Operator | Confirmed |
| 14 | **Corner lots invented**: a cross street within 60 m of the lot's centre makes a corner lot (4250 Fraser: E 27th Ave 51.9 m; 2475 E 5th: Kamloops St 34.5 m), though both are mid-block. | Small lots | Confirmed |
| 15 | **"Who operates: Not named"** where the option names the operator in its proponent line (Expo), and after the operator has signed with an organization. | Reader, towers, operator | Confirmed |
| 16 | **Approved rezonings are asked again**: 998 E 19th Ave "as approved by Council" reads "rezoning required … prepare the shadow and daylight case"; the tool has no "already decided" input. | Reader | Confirmed (no such input) |
| 17 | **The floor area tested is not the floor area drawn**, and the plate box is understated by the 0.5 m grid on a polygon: 609 Heatley tests 340 m² against 307 m² drawn; its plate box is 11.5 × 17 m where the yards leave 12.2 × 17.4. | Small lots, towers | Confirmed |
| 18 | **The website's figures are stale**: 144 and 84 rules against 176; seven and eight open items for the same memo; case.html's "the gap grows to 45%" (it falls) and its 2025-26 grant figure; the districts list on how.html; the operator absent from who.html and the walkthroughs. | All five | Confirmed (grep) |
| 19 | **Reading order and words in the memo**: the Reader layout puts the area schedule before answer 1 (no CSS order for it); The ask says "at 03, 'What are you asking for?'" to a board; on paper, "Not assessed" sits beside "No rule stands in the way". | Reader, manager, towers | Confirmed (code) |
| 20 | **The block editor loses townhouses** when the top floor is stepped back or a block is dropped onto a stepped floor: a home removed on one floor is removed on all (`syncHomes`). Undo recovers it. | Small lots | Reported twice; not re-run (the editor was being changed by another session) |
| 21 | **The short PDF is 6 to 8 pages**, about a third of it sources, and drops the operator's checks and the area schedule; the website promises two pages. | Reader, manager, operator | Confirmed (by design: it keeps the sources) |

Reported once and not re-run: the Burrard St lot's front preset to Burnaby St; dates in UTC ("fetched 2026-11-26" on 25
Nov); the 375 Glen comparison giving "unit mix not given" as a reason; the paper plans without the "not yet checked by
the architect" stamp; the C-2A benchmark offered below the outright FSR and called "the same building".

## What the five agree the flows get wrong

1. **A revision is not what was issued.** Inputs do not come back, options cannot be named ("Suggested, funder-ready"
   four times), comparisons pick their own partner, "Rules as of" resets when a run opens, and nothing records who
   issued what. A board link must show what the sender saw.
2. **Supportive, transitional, shelter and mixed buildings still run on the independent-rental model**: CHF rent tiers,
   one budget, beds with no running cost, the Community Housing Fund's mix tested on a market wing, lifts counted by
   homes.
3. **Numbers inside one memo disagree**: answer 1's words, the floor area tested against drawn, homes priced against
   homes placed, the section's caption, the operating table's lines, the lot area in two figures.
4. **The board gets no decision and no two pages.** The ask is half "not stated"; the short PDF is long.
5. **What is already decided** (an enacted rezoning, a permit, a land agreement) has no place, so approved schemes read
   as proposals.

## What they would add (merged, by size)

**Small:** the hard cost marked a placeholder and shown as a range; the gap with and without uncommitted sources
everywhere; vacancy as a percent with bounds; the operator's name from the signature into "Who operates"; beds and the
tower plate in Manager mode; a name for each option; the frequent-bus-stop question at 01; one rule and open-item count
on the website; the operator on who.html and a walkthrough; no tool-step words ("at 03") in a reader's memo; a
two-page board PDF; glossary links at first use.

**Medium:** inputs and signatures restored with the run, and a warning before Run again replaces signed figures; the
Director's discretion figures read as the discretion route's limits (RT-3 0.75 / 1.00 and the like); non-residential
program as a first-class input (use, floor, area, cost, income, its own funding) counted by the zoning and funder checks;
loans with a rate and term; supportive and shelter money on their own terms (shelter-rate or RGI rents, operating cost
per bed); one floor area shared by the FSR test, the title block and the area schedule; a section and area schedule
built from the real podium and tower; "what is already decided on this site"; frozen, stamped revisions; RT-3's partial
third storey and 45% coverage tested; a term view of the operating agreement; survey inputs (lane distance, front and
flanking streets).

**Large:** a budget per part of a mixed building (rents, cost per home or bed, staffing, subsidy, term and funder each);
mixed buildings with more than one wing, tenure and entry; a core sized from the lift count and the stairs, with lifts
drawn; a real ground-oriented mode (townhouses over floors, stacked and 2-over-2 templates); a project list with
identity, so "issued to you" means a named person.

## What was fixed (25 Nov 2026)

Kai asked for the defects to be fixed. By number, as ranked above:

| # | Now | Where |
|---|---|---|
| 1 | **Fixed.** Opening a run restores the run's own option and site when they differ from the saved file, and the manager's route takes that option as used, so 02 does not derive a new one. Checked in the browser: a Glen Drive run reopened in Operator mode with its signature, its 2% vacancy, its per-bed cost and both capital sources. | `runs.js` `syncInputsTo`, `differs`, `openRun` |
| 2 | **Fixed.** Supportive homes are priced at the shelter component of income assistance (the deep-subsidy tier), transitional homes at rent geared to income; supportive homes beside independent ones leave the market tier. The suggester offers the same tiers. | `proforma.build` (`tier_basis`), `suggest.suggest` |
| 3 | **Fixed.** Within the Director's discretion is never "allowed outright": the by-rezoning "not needed" says the discretion, answer 1's route line follows the three verdicts, the drawing and the comparison say it too. A permit route on a lot whose outright answer is not yet confirmed now reads "No rezoning proposed: …", not "Allowed outright". | `engine.summarise`, `memo/answers.js`, `figures/envelope.js`, `memo/side-by-side.js` |
| 4 | **Fixed.** `fsr_limit` reads RT-3's s.3.1.1.1 (0.75) and s.3.1.1.2 (1.00 for social housing or a non-profit owner) as the Director's discretion: FSR 0.67 is conditional, not a fail. Stop 02's lot reading shows the figure before an option exists. | `checks.fsr_limit`, `NON_PROFIT_OWNERS`, `suggest.lot_reading` |
| 5 | **Fixed.** A brief item can be marked "not homes" (the brief editor's "For" column, `use: "community"`); `checks.non_residential_m2` counts it in C-2's rental FSR, BC Builds, the use check and the money, and the area schedule files it as non-residential. | `brief.js`, `checks.py`, `layout.py`, `proforma.py` |
| 6 | **Fixed.** Lifts count beds (rooms of four), and a shelter that sleeps people above the ground floor needs one. The count wanted is held against the room the first plans give: one elevator for each ground-floor core at least 5 m each way, as the core bay is declared (two stairs and one elevator). So every committed apartment run's operator checklist now reads elevators "missing" (two wanted, one core): a placeholder against a placeholder, said as such, and not an open item. | `layout.lifts_needed`, `operability` |
| 7 | **Fixed.** Beds beside homes carry a running cost (the operator's own a bed, `operations.operating_cost_per_bed_year_cad`, else a home's, said) and a reserve for each room of four; the subsidy need is one figure over the building's places, never per home and again per bed. The operating table's notes say so. | `proforma.build`, `operating_rows`, `memo/answers.js` |
| 8 | **Fixed.** A capital source of kind loan takes a rate and a term (the sources table at 03); its payment comes off the net income before the screen sizes its own mortgage, and the operating table has a row for it. | `proforma.named_sources`, `build`, `route-stage.js` `sourcesEditor` |
| 9 | **Fixed.** The catalogue hard cost is a placeholder until a cost a square metre is entered, so it is listed with the others. | `proforma.build` (`hard_rate`) |
| 10 | **Fixed** (second pass, the same evening). The ground-oriented solver packs homes in columns: a home takes the floors its area needs, drawn at most 30% over its type (`go_oversize_max`, a declared placeholder), and a smaller home stands over it by its own stair; services go in after the homes (a shed in the yard where none is left); a plate too shallow for a courtyard but deep enough for two rows takes them back to back; eight orders of placing (and, with accessible homes, a ninth: not first) are tried and the plan placing the most homes kept, then the most accessible homes, the most doors at grade and the least drawn over the program. A 10 m R1-1 lot now places its four-plex (two one-bedroom flats at grade, two-bedrooms over them; 1 of 4 before), the test lot 4 of 4 (3 before), four storeys 8 of 8. On a 609 Heatley-like lot 3 of 4 still: the four homes need 320 m² of the rows' 340 m² (94%), and the warnings say so. Stop 02 counts townhouses with this solver and says "as ground-oriented homes"; the exit item asks for Part 9 (9.9.9) instead of "move or add a core"; the plan sheet and the layout section describe the rows, not a corridor. No home placed reads no exit. The money still counts every home entered (answer 3 lists the shortfall). | `layout._solve_ground_oriented`, `suggest.plans_for(..., building)`, `memo.layout_open_items`, `memo/answers.js` |
| 11 | **Fixed.** A tower says its storeys in all, then the parts ("18 storeys, a 3-storey podium and a 15-storey tower"); memo.md and the figure captions multiply each plate by its own storeys; the section is cut where every tier stands, so a tower set to one side of its podium is drawn. Not tried in the browser on a tower run (no committed run is a tower). | `massing.build`, `memo.markdown`, `figures/cards.js` `plateWords`, `figures/common.js` `sectionCut` |
| 12 | **Fixed.** Income from the floors that are not homes has its row, and a subsidy has its "left after the subsidy" row, so the table adds up. | `proforma.operating_rows`, `memo/answers.js` |
| 13 | **Fixed.** A vacancy typed as a percent (2) reads as one, nothing over 50% is taken, and the row says when it was entered. | `proforma.build`, `operating_rows`, `fields.js` |
| 14 | **Fixed.** A corner lot only where the cross street's centre line comes within 12 m of the lot's own outline. | `lookup.adjoins`, `CROSS_FROM_LOT_M`, `assemble` |
| 15 | **Fixed.** Who operates is the option's operator, else the organization that signed the operating figures, else one named in the proponent line. Expo's two runs now name BC Indigenous Housing Society, and so gain the open item on the agreement between the City and the operator. | `checks.operator_of`, `engine`, `memo.front_sheet`, `memo/front.js` |
| 16 | **Fixed.** `option.rezoning_approved_on` (an ISO date; asked at 02 when the option goes by rezoning): by rezoning reads "approved" with the date, the rules written for a rezoning application leave the open items, the outright findings say the rezoning was approved and set no task, and the page, the paper and the drawing say so. `options/998-e-19th-ave-as-approved.json` carries 2024-07-25, the date its own name gives. `options/1010-expo-blvd-as-permitted.json` now states `approval_route: development_permit` (its permit of 5 Feb 2025 under CD-1 (324) as amended): outright yes, by rezoning not needed, the family mix no longer asked. | `checks.rezoning_approved_on`, `_over_outright`, `engine.summarise`, `memo.py`, `answers.js`, `paper.js`, `envelope.js`, `fields.js` |
| 17 | **Fixed.** The plate box found on the 0.5 m grid is pushed out to the polygon side by side, so it reaches the yards (Expo +3 m², Glen Drive +16 m²; homes placed unchanged). Where the floor area the plans draw is more than 5% (and 10 m²) under the floor area the rules test, answer 3 says so with both figures and why (the plates the yards leave, the open yard or courtyard), for the architect: "Floor area drawn under the floor area tested" (`layout` totals carry `gfa_tested_m2`). The rules still test the option's figure, as they should; none of the committed runs trips it. | `boundary._grow`, `_rect_in`, `memo.layout_open_items`, `memo/answers.js` |
| 18 | **Fixed.** home, how, case and who quote 176 rules (143 + 2 + 6 + 4 + 13 + 8), 44 districts and two CD-1 by-laws, R1's six open items, the 2026-27 grant ($18,696,195), the gap falling to 45% on R2, Expo's and Glen Drive's new readings; who.html has a fourth flow, the operator's, and the tool has an operator walkthrough (`OPERATOR_TOUR`). | `ffm/ui/*.html`, `site.css`, `tour.js` |
| 19 | **Fixed.** The reader reads the ask, then the answers, with the area schedule after the drawings; "at 03" is said only in Manager mode; on paper a "not assessed" answer gives its reason, the use table has its own words, and Figure 3 carries the first-layout stamp until issued back. | `app.css`, `memo/front.js`, `paper.js` |
| 20 | **Fixed** (after the "Block editor UX improvements" session finished). `syncHomes` carries only what the architect changed on the floor in view since the last snapshot: a home missing from a stepped floor, or from the floor a block was dropped on, is no longer read as removed everywhere, and a move goes to the other floors as a shift, so a stepped floor's shallower home does not flatten the full floors under it. A step-back that takes a townhouse's top floor shrinks its `levels` to the floors it keeps; a duplicated home is a block of its own; the program tracker counts a townhouse once, not once a floor ("4 over" on a program of four). Checked in the browser on three-storey townhouses: a front step of 8.5 m on the top floor kept the two homes it displaced on the floors under it, a nudge on the stepped floor moved the third home on all three floors, Delete removed it from all three and Undo brought it back. | `editors/blocks.js` `snapshot`, `syncHomes`, `rebuildSteps`, `duplicateSel`, `programTracker` |
| 21 | **The promise changed, not the PDF.** The short PDF keeps its sources; the site no longer promises "two pages": home, how and who say the memo opens on the ask and the four answers, and Flow 3 reads the front sheet, then the open items, where the short PDF stops. | `home.html`, `how.html`, `who.html` |

Also from this pass: answer 1 on an approved scheme reads "Not outright. By rezoning: approved, 25 Jul 2024", never
"rezoning required" beside "approved".

The "reported once" list, all done in the second pass:
- **Dates in UTC.** The context's fetch date is Vancouver's day, in words ("fetched 17 Nov 2026"; `figures/common.js` `fetchedOn`).
- **The Burrard St front.** The lookup keeps every road across the front street within 60 m and takes the first that
  runs along the lot (`street_bearing` `cross_streets`, `adjoins`): 1290 Burrard St now offers Drake St, its short end,
  not Burnaby St across Burrard (checked live). The yards are read from the shorter street side, Kai's corner rule, for
  a person to confirm at 01; picking another front replaces the lookup's sentence in the site's notes.
- **The C-2A benchmark.** Where the schedule allows at least the benchmark's floor area outright, Funder-ready keeps
  the outright building and Benchmark is not offered, with the reason (`suggest._outright_beats_benchmark`; 4250 Fraser
  St: 2,099 m² at FSR 3.50 outright against the benchmark's 1,799 m²). The staff benchmark band is drawn only where the
  option proposes a rezoning (`massing` `policy_benchmark`).
- **"Unit mix not given" in the Glen Drive comparison.** A rule that does not apply gives the ledger's own reason in the
  clause split (`memo/clauses.js` `splitValues`): here, the Downtown Eastside Plan's own target.
- The paper plans' first-layout stamp was done in the first pass (#19).

The committed runs were regenerated; the rule files did not change, so the fingerprints are the same (7846c8b6a3414798,
750597987a837e2e, 7532496a9e6ef1ff). R1 at 998 E 19th Ave: by rezoning approved, six open items (five from the rules,
one from the plans), a 56% gap. Glen Drive as proposed reads a 90% gap (77% before: its 25 supportive homes at the
shelter rate and its 80 beds' running costs), the CHF what-if 64% (56%). `375-glen-drive/first-run` is untouched.
449 tests (`tests/test_panel3_fixes.py` is new; the editor fix is in the page and was checked in the browser, as the
suite does not run the page's code). After the second pass: 461 tests; the committed runs regenerated again, every
answer, gap, open-item count and fingerprint the same. Checked in the browser: a four-plex on a 10 m lot (4 of 4, two
rows back to back, the Part 9 exit item, the plan's words), the Glen Drive comparison's reason, the fetch date in words.
