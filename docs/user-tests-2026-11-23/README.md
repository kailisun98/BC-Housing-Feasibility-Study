# Simulated user tests, 23 Nov 2026

**These are role-plays by AI reviewers, not sessions with practitioners.** Nobody at Public
Architecture, Covenant House Vancouver, First United, Lu'ma Native Housing Society or BC Housing
was consulted, and nothing here is their view. Do not quote these as testimonials or credit them
in the README's practitioner list. They are a rehearsal for the real sessions: what a demanding
person in each seat would probably hit first.

Every site is a real Vancouver address. Figures are labelled public record (with the URL) or the
reviewer's assumption; the "hypothetical" sites are not anyone's plan. Rules as of 2026-11-23,
fingerprint `4227307d738e56fe`.

| Seat | Report | Sites run | How |
|---|---|---|---|
| Architect, modelled on Public Architecture | [architect-public/report.md](architect-public/report.md) | 2001 Stainsbury Ave (Vienna House, CD-1 (849), the firm's own rezoning); 6172 Fraser St (C-2A, hypothetical); 2225 W 8th Ave (R5-3, hypothetical) | command line |
| Development manager, modelled on Covenant House Vancouver | [manager-covenant-house/report.md](manager-covenant-house/report.md) | 1280 and 1302 Seymour St (the campus, as built); 4250 Fraser St (C-2A, hypothetical youth transitional) | command line |
| Development manager, modelled on First United | [manager-first-united/report.md](manager-first-united/report.md) | 320 E Hastings St (as built, DEOD); 877 E Hastings St (M-1, hypothetical) | command line |
| The manager's route in the page | [ui-walk/notes.md](ui-walk/notes.md) | 320 E Hastings St | browser, `?mode=manager` |
| Funder-side reader, modelled on BC Housing | [reader-bc-housing/report.md](reader-bc-housing/report.md) | read five finished memos, ran nothing | reading |

Each folder keeps its site files, option files and run folders, so any figure can be reproduced.
No command crashed in any test.

## What all of them trusted

- The lookup when the address is in the City's list: district, CD-1 number, parcel area (Vienna
  House within 0.1% of the public record; the First United lot to the square metre).
- "Not assessed" where the stack has no schedule, with the missing by-law named.
- The arithmetic: the architect recomputed every pro-forma line on two sites, right to the dollar.
- The open-items table, a named person and a named document. The funder-side reader called it the
  part worth keeping.
- The line that the Community Housing Fund has no open intake.

## What more than one of them found

1. **A grant from a fund the project fails is still counted in the money** (both managers, the
   funder reader; confirmed in `ffm/proforma.py` line 234, which never reads the check's status,
   and where an empty `target_programs` means every program). 1280 Seymour reads "Likely, $12.6M
   to spare" with $6.8M of it, and with a negative net operating income.
2. **The funders answer tests two programs and reports a fail for housing they were never for**
   (both managers, the funder reader). Supportive, transitional, shelter and Indigenous-led
   housing have no program in layer E; the memo says "does not meet" where it should say "not the
   relevant test".
3. **Built, approved projects read "by rezoning: no"** (both managers). The family-unit rule is
   applied to shelters, supportive homes, development-permit schemes and outright schemes.
4. **The answers fund and price homes the plates do not hold, and page one does not say so**
   (the architect, the funder reader, the Covenant House manager; first raised on 15 Nov). 93 of
   123 at Vienna House, 57 of 88 on the showcase memo, 58 of 103 at First United. The page's memo
   does carry it ("86 fit the plate") in the title block and as an open item; `memo.md` does not.
5. **No operating picture** (both managers, the funder reader): no staffing, no operating
   subsidy line, market debt terms, income-geared rent near $1,073 a month. The funder reader does
   not recognise the gap as a number a funder uses.
6. **A civic number the City's list lacks returns a different lot, and the command line says
   nothing** (the architect, the Covenant House manager). The page handles the same case with a
   visible check before "Yes, this is the site".
7. **Placeholder yards on streets built to the lot line** shrink the plate and the yield
   (the architect, the page walk).
8. **A mixed building has no place to stand**: community floors, an operator who is not the
   owner, non-dwelling floor area in the cost (the First United manager, the page walk).
9. **`suggest --candidate outright` returns the funder-ready option without saying so** where the
   stack has no schedule, including six storeys of homes on an industrial lot (all three users).
10. **`memo.md` is 95 KB**, most of it rules for other districts (everyone who read it).

## Found by one reviewer, worth a look

- The lookup's front street decides the yield: Vienna House places 23 homes fronting Victoria
  Drive and 93 fronting Stainsbury (architect, P1-2).
- C-2A reads "outright: yes" at FSR 3.5 with no non-dwelling floor area, though the clause the
  memo quotes requires 0.35 FSR of it (architect, P1-3; the quoted line is in the memo).
- 877 E Hastings: the lookup wrote a front street the massing could not find, so the run has no
  drawings (First United, P2-6).
- Program facts the funder reader could not confirm from public pages: the $171,211 grant per
  home, the ±2% mix tolerance, the BC Builds income limits and partner rule, the pre-development
  loan, the 2019 Design Guidelines copy. That report's table lists what was checked and where.
- "Cancelled" is contested wording for the 2025 call; "did not proceed" is safer.
- Wording that could be read as BC Housing's position, with replacements (funder reader).

## Limits of this exercise

- The reviewers are one model wearing four hats; they share blind spots, and their knowledge of
  each organisation is the public record only.
- Program facts marked "my understanding, to verify" are exactly that. None of the reviewers'
  claims about BC Housing programs was checked against a BC Housing document.
- Several approved figures (floor area, FSR and height at 320 E Hastings; floor areas at the
  Seymour buildings) are the reviewer's assumptions, because the City's PDFs refuse automated
  fetches. Comparisons that rest on them are marked in each report.
- The three users did not use the page; one walk of the manager's route did. The PDF, the block
  editor and the Revit step were not exercised.
- I checked a sample of the quoted evidence against the files (the Seymour memo lines, the
  pro-forma code, the C-2A line). I did not re-verify every line reference in the reports.

## What was fixed the same day

After the reviews, Kai asked for the problems to be fixed. Done in the engine, the command line and the page, with
`tests/test_user_tests_2026_11_23.py` pinning each (297 tests pass); the seven committed runs were regenerated.

| Finding | What the tool does now |
|---|---|
| A failed fund's grant counted | A program's grant is counted only where the option does not fail the program. A fail counts nothing and the line says what the figure would have been; a pass is "illustrative", and the verdict is "unsure" where the cost is covered only by a grant from a fund with no open intake. 375 Glen Drive as proposed moved from a 47% gap to 76% for this reason. |
| "Likely" over a negative operating income | Rents that do not cover the running costs read "Needs more sources" whatever the capital stack, and the next step is to find the operating funder. A negative gap is printed as a surplus; a loss as -$52,880. |
| Funders fail on housing they were not written for | A new input, the kind of housing (independent, supportive, transitional, shelter; asked at stop 02 as "Who are the homes for?"). For the last three the two programs read "not the test for this option", answer 2 reads "not assessed", and one open item sends the manager to BC Housing. A deep-subsidy mix that fails the 30/50/20 test is said to point to another program. Answer 2 states its scope: which programs were tested and which are not in the rules. |
| Family-unit rule on shelters, permits and outright schemes | Not applicable where the option states there is no rezoning ("none: development permit …"); a question for the City's planner, not "add family units", for supportive, transitional and shelter housing; dropped from the open items where the option is allowed outright and proposes no rezoning (answer 1 then says "By rezoning: not needed"). |
| Homes that do not fit, and exits, off page one | `memo.md` lists them in answer 3, says the count beside the funders' verdict, and the command line prints a note. |
| C-2 "outright: yes" at 3.5 with no shop floor | The 0.35 FSR of non-dwelling use is tested (`rental_min_non_dwelling_fsr` on the five C-2 schedules); short of it the base 2.5 stands and the finding says what 3.5 needs. The suggestion puts that floor area on the ground floor. |
| A wrong parcel returned silently | `lookup` prints a warning, names the City's nearest number on the same street as the other candidate (2001 for "2009 Stainsbury Ave"), and writes nothing without `--accept-nearest`. The page's parcel check shows the alternative too. |
| A front street the massing could not find | The lookup no longer writes one; a run with no massing says why in answer 3. |
| An industrial lot read "not assessed" beside a six-storey suggestion | The open item leads with "Manager: ask a City planner whether housing is permitted in M-1 … before any offer on the land". `suggest` says when the candidate asked for was not built, in words, not a Python dict. |
| "Meets the criteria", "cancelled", pre-approval wording | "Passes the eligibility items this screen checks", with what is not assessed; "did not proceed"; no dollar figure in an open item; a line on every memo that the tool is independent of BC Housing, the Province, CMHC and the City. |
| `memo.md` 95 KB, "Proponent: None", "inbox/", "stop 3" | Rules for other districts are counted in one line; "not named"; open items written for the person, not the repository. |
| Page wording | "The site allows" is "What the rules ask here"; an area-plan question at stop 01 (the Downtown Eastside target had no input); floor area that is not homes is one of the option's figures. |

Checked in the browser: a regenerated memo, the new question at stop 02, and a transitional option run end to end.
Not checked: the PDF, the static (GitHub Pages) build, whose own lookup code was not changed, and the page's line
for the alternative address.

## Still open, and why

These need a source document, a design decision, or more than a day; none was guessed at.

- **Programs that are not in the rules** (Indigenous Housing Fund, Supportive Housing Fund, shelter funding, CMHC's
  capital programs, the City's grants). Each needs its published criteria read and cited before it can be a rule.
- **An operating page**: staffing, an operating-subsidy line, rents by population, debt on program terms. Asked for
  by three of four reviewers; a design of its own.
- **Costs by construction type**, a rate for non-residential floors, parking and relocation lines. The base is still
  a 2- to 4-unit wood-frame catalogue figure.
- **Program facts the funder-side reader could not confirm**: the $171,211 grant per home, the ±2% mix tolerance,
  the BC Builds income limits and partner rule, the pre-development loan, the Design Guidelines edition and whether
  "minimum + 10%" is the right reading. A person checks these against BC Housing's own documents.
- **The layout**: one bar parallel to the street, unit types not stacked, one lift, no lobby; a plate that follows
  the lot; the 0.5 m plate grid; seven storeys treated as a tower; the front street deciding the yield (Vienna House:
  23 homes or 93) with no both-ways comparison.
- **Yards**: placeholder yards on streets built to the lot line still shrink the plate, and the manager's route has
  no way to say "no yards here"; the site does not record its neighbours.
- **Unit types**: shelter beds and rooms, four-bedroom homes, a storey height per floor.
- **A partnership**: land owner, owner of the homes, operator and the instrument between them; land tenure is still
  a text box read by a keyword.
- **The area plan from the address**, the Downtown Eastside's social housing shares, and districts not in the stack
  (DEOD, M-1, R3, R5).
- **Smaller**: the three candidates are often one building; adding storeys can lower the homes with no sentence
  saying why; the memo keeps the parcel's address, not the one typed; answer 2 still joins two programs with "and".

The wish lists ([wish-lists.md](wish-lists.md)) are a separate matter: features, not defects.

## The operating page (added 23 Nov 2026, later the same day)

Three of the four reviewers asked for it. `option.operations` now carries the operator's own figures: the average
rent of each tier, the operating cost a home a year, support staffing a year, and an operating subsidy with who pays
it and whether it is confirmed. Each stands over the layer F placeholder and the line says "entered"; staffing and a
subsidy are never assumed. The memo prints "What it takes to run, a year": income by tier, the running costs, what is
left, the loan payment, the subsidy needed to run it a home a month, and, as an illustration on this screen's own
mortgage terms, the subsidy needed if the capital still missing were borrowed. The page asks for the figures at stop
03 ("What it takes to run") and shows the same table in answer 4.

How it changes the verdict: a subsidy counts toward a loan only once confirmed, and running costs met only by an
unconfirmed subsidy can read "Unsure" at best; supportive, transitional or shelter housing with no staffing entered
is never "Likely" and names staffing as left to a person. With nothing entered every committed figure is unchanged.

The PDF prints the same table under the money, line by line (checked: a PDF printed from the showcase memo).

Not done: debt is still on market terms (the illustration says so); costs by
construction type and the missing programs are as listed above. The rents the tool assumes for income-geared homes
are still a placeholder until someone enters the operator's.

## Programs added, and the rest of the open list (23 Nov 2026, evening)

### Programs for supportive, transitional, shelter and Indigenous-led housing

Nine programs are now in layer E, each read that day from its own page (the page and the date are on the rule):
BC Housing's Indigenous Housing Fund, Supportive Housing Fund, Women's Transition Housing Fund, HEARTH, the Emergency
Shelter Program and Rapid Response to Homelessness (ended: all its homes are built); the City's Community Housing
Incentive Program; Reaching Home's capital investments; Build Canada Homes. They are **listed, not tested**: each rule
records who the program is for, what it funds, how a project enters it and whether an intake is open, and the new
check (`program_match`) says only whether the option is the kind of housing it is written for. A listed program never
moves a verdict and never puts money in the pro-forma.

Answer 2 now names them: a supportive option reads "Not assessed: the rules list 4 programs for supportive housing
(...) and test none of their criteria", with one open item sending the manager to BC Housing's development staff. Two
new questions at stop 02 (Indigenous-led or partnered? for women and children leaving violence?) decide the two
programs that depend on them; unanswered, each is listed as "would be, depending on an answer not given".

Two things the pages corrected in the rules that were already there:
- **CMHC's Affordable Housing Fund closed on 19 Dec 2025** (its page: portal closed, all funding committed, pointing
  to Build Canada Homes). The rule said its intake was continuous; it has a second version from that date.
- **BC Builds' page confirms** the income limits ($143,900 and $212,240), that a non-profit wanting to own and operate
  teams with a developer or builder, the 30% cap (of area and of capital cost) and the 12 to 18 months; and it
  publishes take-out financing terms (4.55% in 2026, 35 years, 1.1 coverage). The operating table now shows the
  subsidy on those terms beside the illustration on market terms: $926 a home a month against $1,229 on the showcase.

Read from a search summary and marked so on the rule, not from the document itself: who may apply to the Indigenous
Housing Fund and the dates of its 2023 call; CHIP's grant maximums; the Community Entity for Reaching Home in Greater
Vancouver. Not found on any page read: how a project enters the Supportive Housing Fund, the Women's Transition Housing
Fund or the shelter program; the rules say "not stated on the program page".

### The rest of the open list

| Open item | Now |
|---|---|
| Placeholder yards on streets built to the lot line | A question at stop 01, "Do buildings on this street stand on their lot lines?": yes drops the placeholder front and side yards where the rules have no yards for the district. |
| Home sizes fixed at the minimum + 10% | `unit_area_allowance` on the option (the architect's schedule): 1.00 lays the homes out at BC Housing's areas as published. |
| Shelter beds | `beds` on the option; the operating table gives the subsidy a bed a month as well. |
| A partnership has no place | "Who will operate the homes?" at stop 02; an open item where supportive, transitional or shelter housing names none, and another for the agreement where the operator is not the proponent. |
| Land tenure decided by a keyword | A choice at stop 02 (owned, a lease of 60 years or more, a shorter lease, an air-space parcel, still to settle), read before the typed sentence. |
| The area plan from the address | A DEOD lot is set inside the Downtown Eastside Plan by the lookup. |
| The front street decides the yield | On a corner lot the suggestion is derived both ways; where the homes differ by 15% or more it says both counts (Vienna House: 27 fronting Victoria Drive, 88 fronting Stainsbury) and hands the choice to a person. |
| The cost base on tall or mixed buildings | The project's own cost a square metre can be entered and stands over the base; without one, a building over six storeys or with floors that are not homes names the cost as left to a person. |
| Debt on market terms | BC Builds' published terms, as above. Other programs publish none on the pages read. |
| The address typed is lost | The memo says "Looked up as ..." under the title where the City lists the lot under another address. |
| As-built runs read as verdicts | `as_built` on the option heads the memo "A calibration run against a completed project". |

### Not done, and what each needs

- **Criteria of the listed programs** (so that answer 2 can test them): each program's request for proposals or
  framework. None is posted now; the Indigenous Housing Fund's is the first to read when it is.
- **A cost base by construction type, soft costs, operating cost and reserve**: a published source for each. They
  stay declared placeholders that a person can now override.
- **BC Housing's Design Guidelines, current edition**: the page moved into BC Housing's library and was not found;
  the 2019 copy stands, with the adaptable-housing and accessibility shares unread.
- **The Community Housing Fund's grant a home and its mix tolerance**: the next call's documents.
- **District schedules not in the stack** (DEOD and its social housing shares, M-1, R3, R5): the City's PDFs, which
  refuse automated downloads and are saved by hand.
- **The layout**: see the last section; stacking, a lobby and a turning plate are built, the rest is listed there.
- **Four-bedroom homes and a height per storey**: both run through the massing, the layout and the unit-area rule.
- **The static (GitHub Pages) build's own address lookup**, which does not name the nearest number on the street.
- Smaller: the three candidates are often one building; adding storeys can lower the homes with no sentence why.

## The layout (23 Nov 2026, last pass)

What the architect's review asked of the first layout, and what was built:

| Asked | Now |
|---|---|
| Unit types stacked, so walls and wet walls line up | Floors that offer the same runs share one plan: its bays are filled in the program's proportions, largest homes first, and the same home type stands in the same bay on every floor above. Where the program runs out of a type the bay steps down to a smaller home on the same wall line, or stays spare. Kept unless it costs more than one home or 2% of the program against the old floor-by-floor placing; the warning says the difference. |
| A way in | An entry lobby (25 m², a placeholder) on the street side of the ground floor; the entry arrow points at it. Not in a walk-up, whose stair is its entry. |
| Bicycles on level 2 | Services stay on the ground floor; what does not fit goes below grade with the parking and the notes say how much. Homes placed rose on most sites for this reason. |
| Slivers | A leftover of the amenity, the services or the lobby narrower than 2 m is not drawn; the room is that much smaller and the notes say so. |
| The plate on a skewed lot | The plate box is tried square to the frontage and square to the lot's longest side, and the turned one is taken where it is at least 10% larger. The masses are then drawn turned and the plans in the plate's own frame. |

Checked on the reviewers' sites: 998 E 19th Ave as approved places 70 of 105 homes (67 before), the what-if 59 of 88
(57), 6172 Fraser St 25 of 34 (22), Expo's 12 storeys 101 of 120 (100). Vienna House read from Victoria Drive, the
front the lookup chose, places 84 of 123 on a plate turned 45° along the lot, where it placed 23 on a square one;
from Stainsbury Ave it places 91, two fewer than before, because the lobby takes a bay. The block editor opens on the
stacked plan and reads it back unchanged.

Not built, each a larger piece of design work:
- **The corridor run the other way** on a narrow, deep lot (6172 Fraser St would hold about two more homes a floor).
  The solver, the egress check, the sheets and the block editor all take the corridor along the street.
- **A plate that is not a rectangle** (an L, a courtyard). A turned rectangle is as far as this goes.
- **Lifts by home count**: no rule in the stack says how many, and none was invented.
- **The 0.5 m plate grid**, which can lose up to half a metre a side on a polygon lot.
- **Seven or eight storeys read as a tower plate** (21 m deep). The threshold is where a wood frame stops; a
  mass-timber mid-rise wants its own.

## The corridor across the plate, and a plate in two parts (23 Nov 2026, after the layout pass)

**The corridor the other way.** On a plate deeper than it is wide the solver now also runs the corridor from the
street to the lane, and keeps that plan where it places more homes with exits no worse, where it places as many with
better exits, or where the corridor along the street would leave homes deeper than daylight reaches (12 m, a declared
placeholder; a 20 × 49 m plate laid along the street had "placed" homes 23.6 m deep and 3 m wide). The plan is solved
with the plate turned a quarter, where everything already holds, and turned back. The lobby and the street's rooms
stand at the street end of a strip, the services at the lane end. On 6172 Fraser St it places the same 25 of 34
homes, and every floor's exits pass where they were conditional.

**A plate in two parts.** Where the setback envelope holds a second rectangle beside the plate box (at least 9.8 m
across, 150 m², meeting the box along a wall) and the option's floor area does not fit the box alone, the plate takes
it as a wing: as far out as the floor area asks, never less than 150 m². The footprint is the outline of both, the
floor area and FSR are their own, and the layout lays each part out with its own core, corridor and exits, the main
part taking the ground-floor rooms and the wing the homes left over. The ground neither covers is a cut-out. An L of
a lot, 60 × 22 m along the street with a 26 × 33 m leg behind, takes a 20 × 49 m bar and a 26 × 16 m wing and places
75 of 114 homes with every floor's exits passing.

Checked: 332 tests; the Fraser and L-lot plans, stacking and site plan looked at as drawings; the L lot opened in the
page (plan, 3D, block editor, no errors). None of the seven committed runs changes arrangement: their lots are
rectangles or their plates fit one box.

Limits, said plainly:
- Each part of a two-part plate has its own core and stairs. One core serving both is what an architect would draw;
  the solver does not, and says so in the notes.
- Two parts at most, both rectangles square to the frontage. A courtyard, a U, or a wing on a turned plate is not built.
- The suggestion still counts homes on the plate box alone, so a suggested option does not ask for a wing by itself.
- The block editor shows and moves the blocks of these plans, but a block added there is placed as if the corridor
  ran along the street; and it reads a two-part plan's exits as one floor, which can differ from the part-by-part
  reading in the memo.
- The Revit script was not run on a two-part footprint.

## Sources read, and the review items no document was needed for (23 Nov 2026, final pass)

Asked for: everything blocked on a source document, and everything raised in the reviews and not yet addressed. The
first half is only partly done, and the list at the end of this section says exactly what is left.

### Read from BC Housing's own pages (HTML, 23 Nov 2026)

- **Community Housing Fund, a 2026 version** (`bch.chf.eligibility`, effective 1 Jan 2026, verified): the low and
  moderate income limits ($90,560 for homes under two bedrooms, $146,270 for two bedrooms and more), the deep-subsidy
  income limits ($24,596 and $30,745), the three tiers as the program page defines them and the 30 / 50 / 20 mix. The
  earlier version stays for earlier dates. `not_read_from_bc_housing` lists what the pages do not give: the grant per
  home and the tolerance on the mix.
- **BC Builds, a 2026 version** (verified) with the middle-income limits and the take-out financing terms.
- **CMHC Affordable Housing Fund**: the rule now says the intake closed on 19 Dec 2025.

### Built, because no document was needed

- **How it is approved.** `option.approval_route` (rezoning, development permit, outright; asked at stop 02 as "How
  will it be approved?"). By permit or outright, the rezoning-only rules are not applicable and the memo reads
  "By rezoning: not needed".
- **Open items.** A program the option does not target is no longer its open item. Each open item someone outside
  settles ends with who to ask. The transit-area and Community Vision items are addressed to the manager.
- **Floors that are not homes** carry their own cost a square metre, income and money raised
  (`finance.non_residential_*`), each a line in the pro-forma.
- **A taller ground floor** (`option.ground_floor_height_m`) lifts the floors above and the height.
- **Suggestions** say when two candidates are the same building here, and why more storeys can mean fewer homes.
- **memo.md** has "Words in this memo". **massing.svg** is drawn with the street at the bottom, like every other sheet.
- A site looked up with `--out` takes its id from the file name. A society with "church" in its name is no longer
  read as a church owner. The tree action differs on a street built to the lot lines. The top bar wraps on a narrow
  window. The RGI line names the Housing Income Limits as the figure to replace its placeholder.

Tests: `WhatTheReviewsRaisedAndWasLeft` in `tests/test_user_tests_2026_11_23.py` (342 tests in all). The seven
committed runs were regenerated: answers unchanged; gaps read 43% where they read 44%; fingerprints
8bc2390c7cd9cbdb (23 Oct), 00b916863ab4ff5b (27 Oct), 16df88bd0f50baba (17 Nov).

### Still blocked on a document, and which one

BC Housing publishes these as PDFs. None was downloaded (a download needs Kai's say-so), so nothing from them is in
the rules.

| What is still a placeholder or untested | The document |
| --- | --- |
| RGI rents by Housing Income Limit | Housing Income Limits, Dec 2025 |
| Unit areas, accessibility share, the cost base by building type | Design Guidelines and Construction Standards, and its Technical Bulletins |
| Criteria for supportive housing | Supportive Housing Fund program framework (2024) |
| Criteria for women's transition housing | Women's Transition Housing and Supports Program framework (2019) |
| Criteria and bed standards for shelters | Emergency Shelter Program framework (2018), Shelter Design Guidelines |
| HEART and HEARTH criteria | HEART and HEARTH program framework |
| BC Builds grant and financing terms in full | BC Builds Rental Supply Program framework |
| Community Housing Fund grant per home and the mix tolerance | the fund's program framework or call documents |

The City's by-law PDFs refuse automated fetches, so Kai saves them by hand into `inbox/`: the Downtown-Eastside
Oppenheimer ODP, the M-1 schedule, the R3 and R5 schedules, the RT family (still typed from memory), and the CD-1
by-laws of any site tested. The Altus cost guide was found only through a secondary summary and is not cited.

### Raised in the reviews and still not built

Lifts by number of homes; a shared core for a plate in two wings; courtyards; a plate-box grid finer than 0.5 m; the
depth threshold for a seven or eight storey tower; four-bedroom homes; shelter beds as a unit type; the static
build's own lookup (nearest number on the street); the Revit script on the new layouts (turned plates, wings). The
wish lists (`wish-lists.md`) are features asked for, not defects, and none was built in this pass.

## BC Housing's documents, read (23 Nov 2026, after Kai said to download them)

Fourteen PDFs from `www.bchousing.org/sites/default/files/media/documents/` are in `inbox/bc-housing-2026-11-23/`
(git-ignored; about 57 MB). Each rule that takes a figure from one names the file and the pages in `source.read_from`.

| Was blocked | What the document says | Where it went |
| --- | --- | --- |
| RGI rents by Housing Income Limit | Vancouver HILs in use from 1 Dec 2025: $58,000 (one bedroom or less), $72,000, $86,000, $107,500. The fund's 2023 call estimates RGI revenue on tenants averaging 70% of the limit | new rule `f.rgi_rents` (from 1 Dec 2025): $1,015, $1,260 and $1,505 a month; the pro-forma's RGI line is no longer a placeholder |
| Deep-subsidy rent | the shelter allowance ($500, $695); three bedrooms at 30% of the deep-subsidy income limit ($769) | the same rule, by bedroom count |
| Grant per home | $158,294 (2023-24), $171,211 (2025-26), $178,059 (2026-27), each a provisional approval | `bch.chf.eligibility`, a version from 1 Apr 2026 |
| The fund's other items | 5% accessible homes, a 60-year lease, a start within 18 months, non-residential space at most 30%: all in the 2023 call | confirmed on the 1 Jan 2026 version |
| The mix tolerance | no document read gives one | stays this tool's own 2-point rounding rule, and the rule says so |
| Unit areas and accessibility | 33 / 49 / 67 / 86 m² confirmed, four-bedroom 112 m², 5% wheelchair accessible, 12% and 5% uplifts, 60-year service life. **BC Housing's own copy of the 2019 edition is stamped archived**: not mandatory for new projects, no replacement named | `bch.design_guidelines.unit_areas`, a version from 23 Nov 2026; the finding says "archived" and tells the architect to ask which standard applies |
| Supportive housing | the Province's land company owns the building in full and pays the whole capital cost; a non-profit operates it on a 3 to 5 year agreement; every home rent geared to income; no cross-subsidy | `bch.shf.program` (owner, rents, how a project enters) |
| Women's transition housing | four streams with their stays; the Province owns what the fund builds; 30% of income in second-stage and long-term homes | `bch.wthf.program` |
| Shelters | BC Housing pays the running costs under a support services agreement; no rent; 24/7 access. Sleeping rooms: 4.6 m² a bed space, four beds a room at most | `bch.esp.program`; new rule `bch.shelter.bed_space` (check `shelter_beds`, reads `option.beds`) |
| HEART and HEARTH | operating money for sites in communities the Province picks; agreements up to three years; fixed rent at the shelter component in temporary housing, none in a shelter | `bch.hearth.program` |
| BC Builds in full | a grant of up to $225,000 a home for select non-profit projects (20% of homes at 20% below market for 35 years), rents at most 30% of the middle-income limit, no operating subsidy, leases up to 99 years | `bc.bcbuilds.eligibility`, the 1 Jan 2026 version |

The seven committed runs were regenerated. Every answer is the same; the money moved because RGI rents are lower
and the grant is higher: 998 E 19th Ave as approved, gap 22% ($11.8M, was 23%); funder-ready 45% (was 43%); Expo
12-storey 45% (was 43%); Glen Drive as proposed 77% (was 76%), what-if 56% (was 55%). Fingerprints: e270210b5ed562c7
(23 Oct), 7c057234c9d4da8d (27 Oct), 46276d4e929a2c2f (17 Nov). 95 rules, 350 tests
(`WhatBCHousingsDocumentsSay`).

### Still not resolved after reading them

- **The cost base by building type.** None of these documents gives a cost per square metre. The hard-cost base is
  still the Province's Class D figure for two- to four-unit buildings.
- **Which design standard applies now.** The 2019 edition is archived and BC Housing's page names no replacement.
  A person has to ask BC Housing.
- **Program criteria as tests.** The frameworks say how each program works, not a scored checklist; the supportive,
  transition, shelter and HEARTH programs are still listed, not tested. That is how the frameworks are written.
- **Downloaded, not read into the rules:** the Design Guidelines for women's safe homes and transition houses (2021),
  Technical Bulletins 2 to 4 (energy and construction, all archived with the guidelines).
- **The City's by-law PDFs** (the Downtown-Eastside Oppenheimer plan, M-1, R3, R5, the RT family, CD-1s) still
  have to be saved by hand into `inbox/`.
- **Operating cost, soft costs and contingency** are still declared placeholders: no public source was found.

## A CD-1 lot and a key, and the City schedules Kai saved (24 Nov 2026)

### A CD-1 site: give a key, and the tool reads its by-law

On the manager's site card, a CD-1 lot whose by-law the rules do not hold now shows "Have the tool read CD-1 (N)'s
by-law". It asks for an Anthropic key (kept in the browser only), links the by-law on the City's site, and takes the
saved PDF. The model proposes each limit with the sentence it came from; a named person confirms; the by-law is then
in the rules and the site is read under it. A CD-1 with no number recorded is sent to the City's CD-1 index.

The tool cannot fetch the PDF itself: `cd1-bylaws.vancouver.ca` answers a program with 403 (checked 24 Nov 2026), so
the PDF reaches the tool through the person. The form is the architect's own, drawn once in the page: on the stage
card in manager mode, under the district row in architect mode (`cd1Slot` in route-stage.js, `renderClaude` in
claude.js). Not tested with a live key: no call to the model was made. On the web build a reading can be made but not
confirmed, as before.

### Seventeen schedules read into the rules

Kai saved them into `02 A2\00 Research`; copies are in `inbox/city-2026-11-23/` (git-ignored). 51 rules, every one
verified with its file and pages:

| District | Read | Outright figures |
| --- | --- | --- |
| RT-4, RT-4A | May 2026 | FSR 0.60; 10.7 m, 3 storeys; yards 7.3 / 1.5 / 10.7 m |
| RT-5 | June 2026 | FSR 0.60 (0.75 by discretion); 10.7 m, 3 storeys |
| RT-7 | June 2026 | FSR 1.00; 8 homes if all rental, else 6; 11.5 m, 3 storeys |
| RT-8 | May 2026 | FSR 0.50 (0.75 by discretion); 10.7 m, 2 storeys; no rear yard set |
| RT-10 | May 2026 | FSR 0.40 (0.80 by discretion); 10.7 m, 2 storeys |
| RT-11 | June 2026 | FSR 0.60 (0.85 by discretion); 10.7 m, 2 storeys |
| RM-6 | Oct 2026 | FSR 1.00 (2.50); 12.2 m (64.0 m by discretion) |
| RM-7, RM-7A | Oct 2026 | townhouse: FSR 0.60 (1.20); 10.7 m, 3 storeys |
| RM-8, RM-8A | Oct 2026 | FSR 1.20; 11.5 m, 3 storeys |
| RM-9A, RM-9, RM-9B | Oct 2026 | FSR by frontage, 0.70 or 0.75 up to 2.00; 12.2 to 13.7 m, 4 storeys |
| RM-10 | Oct 2026 | FSR by frontage and area, 0.90 up to 2.60; 20.0 m |
| RM-11, RM-12 | Oct 2026 | FSR 1.70 (RM-11: with 36.6 m of frontage, else 0.75); 13.7 m |
| FM-1 | Oct 2026 | FSR 0.60 (1.50 by discretion); 10.7 m; yards not read |
| M-1 | Nov 2025 | housing is not a use the schedule allows (a dwelling only where essential to a business); 30.5 m |
| DEOD | May 2026 | the Oppenheimer plan, by sub-area: FSR 1.0 (3.0 for social housing in Main/Hastings; to 11.0 by discretion); 30 m or 15 m (to 100 m by discretion) |

Two things the reading turned up:

- **M-1 does not permit housing.** A schedule in the rules must not make an industrial lot read "allowed": the FSR
  rule fails for a housing option and tells the manager to ask a planner first (`housing_not_permitted`).
- **The Oppenheimer plan sets its limits by sub-area**, so a DEOD site is asked "Which sub-area?" at stop 01
  (`site.odp_sub_area`, `checks._for_sub_area`). Sub-area 4 has no maximum height printed, only a minimum of 15 m
  and the Director's 100 m; the tool says so instead of inventing one.

Still from memory (flagged in any memo that uses them): RT-6 and the N variants (RT-4N, RT-4AN, RT-5A, RT-5N,
RT-5AN, RT-10N, RT-11N), which were not among the files. R3 and R5 were not saved either.

The committed runs were regenerated; every answer and figure is the same. Fingerprints: 53056660a42fb57b (23 Oct),
30cfd9b9ac04c178 (27 Oct), a3bef23d7edb36b9 (17 Nov). 146 rules, 361 tests (`ACd1LotAndAKey`, `TheSchedulesKaiSaved`).

### Two corrections from Kai (24 Nov 2026)

- **RT-6 is not a district**, and neither are the N variants: the City's zoning map lists RT-1, 2, 3, 4, 4A, 5, 7, 8, 9,
  10 and 11 only. The family rule typed from memory (`cov.rt.*`) covered nothing that exists and is deleted, so no RT
  site carries an "unverified" item any more. Five rules remain unverified (CD-1 (819) twice, the code's exits, the
  transit tiers 4 and 5, the Downtown Eastside family target). Districts on the map with no schedule in the rules:
  RT-1, RT-2, RT-9, RM-2, RA-1, R3-1 to R3-3, R4-1, R5-1 to R5-4.
- **The 2019 Design Guidelines are the standard.** BC Housing's page gives that edition as the standard for what it
  funds; the "archived" stamp is on the PDF copy only. The rule says `edition_status: current`, the finding raises
  nothing, and the stamp is noted in the source.

144 rules. Fingerprints: 31193259023b85e0 (23 Oct), 2c0cee962e81cc28 (27 Oct), 5cfd6a34b23f68ab (17 Nov).