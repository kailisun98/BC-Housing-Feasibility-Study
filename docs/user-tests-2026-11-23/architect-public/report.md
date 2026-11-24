# Simulated user test (role-play by an AI reviewer), not a practitioner's statement

**Persona:** a project architect at a Vancouver practice that does early feasibility for non-profit housing clients (modelled on Public Architecture; nobody at the firm was consulted, and nothing here speaks for the firm, its clients or their plans).
**Tested:** First Read as it stands on 23 Nov 2026, command line only (`lookup`, `suggest`, `run`, `proforma`), reading `memo.md`, `ledger.json`, `massing.json`, `layout.json` and the SVG sheets. **The web UI, the block editor, the boundary editor, the PDF and the Revit script were not exercised**, so findings about "the memo" mean `memo.md` and the engine's sheets.
**Rules as of:** 2026-11-23, fingerprint `4227307d738e56fe` on every run.
**Sources I could not open:** `council.vancouver.ca/20220607/documents/rr13.pdf` returned 403 to one automated fetch; I did not retry. I did not try `bylaws.vancouver.ca`. So no district-schedule clause in the ledger was checked against its PDF by me; where I say a citation is consistent I mean internally, not that I read the by-law today.

## Who I am and what I need

- I get a site and a society on a Monday and owe them, by Friday, a one-page "what fits, what it needs from the City, what it needs from funders, what I don't know".
- I need the yield (homes by type, on a plate I believe), the planning route, and the two or three numbers that kill a scheme, each with the clause, so I can defend them in front of a board and a planner.
- I do not need drawings from a tool. I need a plate and a count I do not have to redo before I open Revit.

## What has improved since the 15 Nov architects' review

I read `docs/design-review-2026-11-15/architect-A…` and `architect-B…` first. Against their lists:

| Their finding | Today |
|---|---|
| CD-1 site read "Allowed outright" | Fixed. Both CD-1 (849) and R5-3 read "not assessed" with the reason and two open items (schedule missing, yards not checked). |
| Plans drawn street-up on some sheets, street-down on others | Fixed on plans, site plan and stacking. `massing.svg` still says "street (y = 0 is the top edge)" and draws the lot mirrored against `site-plan.svg` (P3-3). |
| Section and elevation 2.5 m apart | Fixed. The elevation prints "6 storeys × 3.3 m = 19.8 m to the top floor level (thin line), the 1.2 m above it parapet, roof or a taller ground floor". |
| Yards not zoning, never said in answer 1 | Half fixed. C-2A yards are now a rule (`cov.c2a.setbacks`); where there is no rule the open items say "Yards not checked". |
| A Python `None` in findings | Still one: every memo with no proponent opens "**Proponent:** None (non profit society)" (`memo.md` line 4). |
| A third of the program does not fit and answers 1 to 4 never say so | **Not fixed in `memo.md`.** Still the most important problem (P1-1). |
| 100% gap read "unlikely" with no homes | Not re-tested. |

## Site 1. 2001 Stainsbury Ave (Vienna House), a real project with a public record

A seven-storey, 123-home social housing building. The rezoning applicant named on the City's page is Public Architecture + Communication. It lets me set the tool against what was approved and announced.

### Inputs and where each came from

| Input | Value | Label |
|---|---|---|
| Storeys, height, floor area, FSR | 7, 23.83 m, 10,254 m² net, 3.46 | public record (https://www.shapeyourcity.ca/2009-2037-stainsbury-ave) |
| Homes | 123 social housing | public record (same page) |
| Parking, bicycles | 35, 227 | public record (same page) |
| Zoning before and after | RS-1 to CD-1; approved by Council 28 Jul 2022 | public record (same page) |
| Policy considered under | Kensington-Cedar Cottage Community Vision, so "former Community Vision area: yes" | public record (same page) |
| Owner | City of Vancouver | public record (same page; BC Gov release below) |
| Unit mix | 29 studio, 37 one-bed, 35 two-bed, 16 three-bed, 6 four-bed | public record (https://news.gov.bc.ca/releases/2024HOUS0021-000204) |
| Rent tiers | 25 shelter rate, 61 rent geared to income, 37 affordable market | public record (same release) |
| Tenure | 60-year lease from the City to More Than a Roof Housing Society | public record (same release) |
| BC Housing money | $13.84M Community Housing Fund + $8.36M Cost Pressure Grant, about $22.2M; City "more than $13 million in combined land equity and waivers" | public record (same release) |
| Accessible homes | 12 | my assumption (the release says "ten per cent"; my rounding) |
| Share below HILs | 0.70 | my assumption (86 of 123 homes are RGI or shelter rate) |
| Four-bedroom homes | entered as three-bedroom+ (22 in all) | my assumption; the tool has no four-bedroom type |
| Setbacks 3.7 / 6.0 / 3.0 m, floor to floor 3.3 m | the tool's placeholders | my assumption (I did not have the approved yards) |
| Front street | Stainsbury Ave | my assumption as the architect (the lookup chose Victoria Drive) |
| Transit-oriented area, trees, bus stop | blank | not checked |
| Referral report figures 23.4 m and FSR 3.53 | not used | a web-search summary of `rr13.pdf` only; the PDF refused my fetch |

### Commands (repo root as working directory; `$py` is the uv CPython 3.12 path, `$d` is `docs\user-tests-2026-11-23\architect-public`)

```powershell
& $py -m ffm lookup "2009 Stainsbury Ave, Vancouver, BC" --out $d\sites\2009-stainsbury-ave.json   # returned 1851 Stainsbury Ave, R1-1 (kept under sites\_candidates)
& $py -m ffm lookup "2001 Stainsbury Ave, Vancouver, BC" --out $d\sites\2001-stainsbury-ave.json   # CD-1 (849), 2,966.7 m²
# hand edits to the site: Community Vision yes, owner City, front_face Stainsbury Ave (a copy as found is 2001-stainsbury-ave-as-looked-up.json)
& $py -m ffm suggest --site $d\sites\2001-stainsbury-ave.json --programs bch.chf.eligibility,bc.bcbuilds.eligibility --candidate <outright|benchmark|funder-ready> --as-of 2026-11-23 --out $d\options\2001-stainsbury-ave-suggest-<candidate>.json
& $py -m ffm run --site $d\sites\2001-stainsbury-ave.json --option $d\options\2001-stainsbury-ave-as-approved.json --out $d\runs\2001-stainsbury-ave\as-approved --as-of 2026-11-23
& $py -m ffm run --site $d\sites\2001-stainsbury-ave.json --option $d\options\2001-stainsbury-ave-what-if-6-storey.json --out $d\runs\2001-stainsbury-ave\what-if-6-storey --as-of 2026-11-23 --previous $d\runs\2001-stainsbury-ave\as-approved\ledger.json
& $py -m ffm run --site $d\sites\2001-stainsbury-ave.json --option $d\options\2001-stainsbury-ave-suggest-funder-ready.json --out $d\runs\2001-stainsbury-ave\suggest-funder-ready --as-of 2026-11-23
& $py -m ffm run --site $d\sites\2001-stainsbury-ave-as-looked-up.json --option $d\options\2001-stainsbury-ave-as-approved.json --out $d\runs\2001-stainsbury-ave\as-approved-front-as-looked-up --as-of 2026-11-23
```

### What the tool answered (as approved, front on Stainsbury)

- Outright under CD-1 (849): **not assessed** (by-law not in the rules). By rezoning: **not yet confirmed**; Interim Rezoning Policy *conditional* (23.83 m over the 19.9 to 21.3 m staff benchmark; FSR 3.46 over about 3.0).
- Funders: **meets the Community Housing Fund** (mix 37 / 61 / 25 "matches 30/50/20 within tolerance", site control finalized), with the note that the fund's 2025 call was cancelled.
- Money: **Needs more sources**; capital $66,985,133, grant $21,058,953, debt $15,215,478, gap $30,710,702 (46%).
- Massing: plate 1,312 m² × 7 = 9,184 m² (FSR 3.10) in a 64.0 × 20.5 m plate box.
- Layout: **93 of 123 homes placed**; 7 one-bedroom and 23 studios did not fit. Egress pass on all seven floors (4 exits, travel 13.8 m).

### Tool vs public record / my own check

| Item | Tool | Public record or my check | Verdict |
|---|---|---|---|
| Site area | 2,966.7 m² (City parcel polygon) | 10,254 m² ÷ 3.46 = 2,964 m² (my arithmetic on the application's figures) | Agrees within 0.1%. I trust the lookup's area. |
| District | CD-1 (849) | CD-1, rezoned from RS-1 (public record) | Agrees, and it found the by-law number. |
| FSR | 3.46 (10,254 ÷ 2,966.7 = 3.456) | 3.46 (public record) | Agrees. |
| Front street | Victoria Drive, the 35.5 m end | The building is addressed and named on Stainsbury Ave (public record); front on Stainsbury is my assumption | **Disagrees.** With the lookup's front, the same option places 23 of 123 homes on a 22.0 × 21.5 m plate (P1-2). |
| Address "2009 Stainsbury Ave" (the rezoning's own address) | 1851 Stainsbury Ave, R1-1, 3,393 m², a different lot | 2009 to 2037 Stainsbury is this site (public record) | **Wrong parcel**; warned only inside the notes field (P1-4). |
| Homes that fit at 7 storeys | 93 of 123 | 123 approved and announced (public record) | **Tool under-yields by 24%.** Two causes, both mine to verify: the plate box is 1,312 m² against the 1,465 m² per floor the approved floor area needs, and the tool sizes every home at the BC Housing minimum + 10% + 8%. |
| Floor area drawn | 9,184 m² (FSR 3.10) | 10,254 m² (public record) | 10% short; the memo says so in a note, but the code site plan prints "Floor space ratio 3.10" under an answer that says 3.46. |
| Suggested option (funder-ready) | 6 storeys, 8,900 m², FSR 3.0, 95 homes | 7 storeys, 10,254 m², 123 homes (public record) | A fair first guess from a policy benchmark: 77% of the approved homes. |
| Family homes | 57 of 123 (46.3%) two-bed+, pass | 35 + 16 + 6 = 57 (public record) | Agrees. Four-bedroom homes have no type of their own. |
| CHF mix | pass, 30.1 / 49.6 / 20.3 | 37 / 61 / 25 (public record) | Agrees; the tolerance did the right thing on a real mix. |
| BC Housing grant | $21,058,953 ($171,211 × 123), all labelled Community Housing Fund | $13.84M CHF + $8.36M Cost Pressure Grant = about $22.2M (public record) | Total within 5%, by coincidence of composition: the CHF line alone is 52% over what that fund put in. |
| Gap | $30.7M, 46%, "Needs more sources" | The project was financed and built; its total cost is not in the pages I read. The City's land and waivers (over $13M, public record) appear as $0 land and nothing else. | I cannot check the capital cost. The verdict is not wrong, but on a built project it shows how far the placeholders are from a real stack. |
| Hard cost | $4,693/m² × 1.0311 = $4,839/m² (about $450/sf) | The source is a 2- to 4-unit wood-frame catalogue; this is a seven-storey Passive House building in mass timber (public record). My assumption: materially higher. | The memo flags the base in the closing note, not in the answer. |
| Pro-forma arithmetic | all lines | I recomputed hard, soft, contingency, rent by tier, vacancy, NOI, payment (NOI ÷ 1.10), loan (monthly annuity, 480 payments at 6.19%), grant, gap | **All correct to the dollar.** |
| Cores and exits | one central core bay with two stairs and one lift, plus a stair at each end: 4 stairs | My check: a 64 m bar needs two stairs and, at 123 homes on seven storeys, two lifts | Over-provided on stairs, under on lifts; fine as a diagram, not as a plan. |

## Site 2. 6172 Fraser St: HYPOTHETICAL

I picked a real C-2A corner lot to test a district the rule stack has. **Nothing is known or implied about its owner or any plan for it; no client exists.** Every option figure is my assumption.

### Inputs

| Input | Value | Label |
|---|---|---|
| District, area, dimensions | C-2A, 881.1 m², 25.1 × 35.1 m, corner with E 46th Ave | the tool's lookup of City open data; not independently checked |
| My scheme | 6 storeys, 21.0 m (a 4.5 m shop floor and five floors), 3,080 m² (FSR 3.50), 300 m² commercial at grade, 34 homes (8 / 13 / 9 / 4), tiers 10 / 17 / 7, 2 accessible | my assumption |
| Setbacks | front 2.5, rear 1.5, side 2.0 m | the tool's suggestion |
| Site control, tenure, partner | letter of intent, 60-year lease, partner yes | my assumption (hypothetical) |

### Commands

```powershell
& $py -m ffm lookup "6172 Fraser St, Vancouver, BC" --out $d\sites\6172-fraser-st.json
& $py -m ffm suggest --site $d\sites\6172-fraser-st.json --programs bch.chf.eligibility,bc.bcbuilds.eligibility --candidate <outright|benchmark|funder-ready> --as-of 2026-11-23 --out $d\options\6172-fraser-st-suggest-<candidate>.json
& $py -m ffm run --site $d\sites\6172-fraser-st.json --option $d\options\6172-fraser-st-suggest-outright.json --out $d\runs\6172-fraser-st\suggest-outright --as-of 2026-11-23
& $py -m ffm run --site $d\sites\6172-fraser-st.json --option $d\options\6172-fraser-st-my-scheme.json --out $d\runs\6172-fraser-st\my-scheme --as-of 2026-11-23 --previous $d\runs\6172-fraser-st\suggest-outright\ledger.json
```

### What the tool answered

- All three candidates gave the same building: 6 storeys, 19.8 m, 3,084 m², 30 homes; only the rent tiers differ.
- My scheme: **Outright under C-2A: yes** (FSR 3.50 within 3.5, 21.0 m within 23.0 m, yards kept). **Meets BC Builds and the Community Housing Fund.** Money: needs more sources, gap $10,284,054 (51%) before land.
- Layout: **22 of 34 homes placed** on a 20.0 × 25.67 m plate; egress **conditional** on every floor (stairs 5.8 m apart, 9 m needed).

### Tool vs my own check

| Item | Tool | My check | Verdict |
|---|---|---|---|
| FSR | 3,080 ÷ 881.1 = 3.496 | same | Correct. |
| "Allowed outright: yes" at 3.50 | pass | The finding's own clause asks for "0.35 FSR of non-dwelling use at the street". My 300 m² is 0.34. The tool's own suggestion has **0 m²** of non-dwelling use and also reads "yes" (`runs/6172-fraser-st/suggest-outright/memo.md`, "Outright, under C-2A: yes"). The C-2 rule's source text says the tool "does not test the ground-floor share". Without it the stated fallback is 2.5, or the Director's relaxation for social housing (s.5.1 as the rule cites it), which is discretion, not outright. | **A yes that depends on a condition nobody tested** (P1-3). |
| Height | 21.0 m within 23.0 m | Could not open the schedule today | Internally consistent. |
| Side yards | 2.0 m both sides ("not given" in the site plan table) | The rule's own text: side yard 1.8 m only beside an R district. On a commercial street I build to the lot line. | The suggestion gives away 4 m of a 25 m frontage (P2-2). |
| Plate box | 20.0 × 30.0 m = 600 m² inside a 650 m² envelope | 25.0 − 4.0 = 21.0 m; 35.1 − 4.0 = 31.1 m | The 0.5 m grid search loses about a metre each way, 8% of a small lot (P2-3). |
| Homes that fit | 22 of 34; typical floor 2 two-bed + 3 one-bed on 513 m² (65% of the plate in homes, the rest drawn spare) | I over-programmed: 34 homes at these sizes need about 2,200 m² of unit area against 2,565 m² of upper floors. But I would get about 7 on a floor here by running the corridor front to back; the solver runs it parallel to the street on a 20 m frontage, with homes 11.94 m deep. | Right to object, wrong count. I would redraw (P2-1). |
| Ground floor | 300 m² shop across the whole street front; "entry" arrow into the shop; amenity in two pieces, one **0.86 m wide** (`layout.json` floor 0: amenity 0.86 × 11.94 m); 69 m² of "services, bicycles" on level 2 | A residential lobby on the street is missing; nobody carries 60 bicycles to level 2 | Not presentable (P2-4). |
| Egress | conditional, 5.8 m apart, "stairs at its front and rear ends could be 11.5 m apart: an arrangement for the architect to draw" | Correct and useful; that is the note I would write | Trust as a flag (the limits are "entered from recollection"). |
| Corner lot | the code site plan shows no flanking street | E 46th Ave is the flank (lookup notes) | The sheet drops what the lookup knew. |
| Commercial space in the money | 300 m² costed at the residential rate; no commercial rent | A shop pays rent and costs differently | Small here; say so on the line. |
| Pro-forma arithmetic | all lines | recomputed hard cost, tiers, NOI, payment, grant, gap | Correct. |

## Site 3 (short). 2225 W 8th Ave: HYPOTHETICAL, a district the stack lacks

Nothing is known or implied about the owner or any plan. The City's dataset returns **R5-3** (556 m², 15.2 × 36.5 m, corner with Yew St). The rule stack has RM-3, RM-3A and RM-4 schedules but no R3 or R5 districts; four of my address probes came back R3-2, R3-3 or R5-3.

```powershell
& $py -m ffm lookup "2225 W 8th Ave, Vancouver, BC" --out $d\sites\2225-w-8th-ave.json   # R5-3, 556.0 m²
& $py -m ffm suggest --site $d\sites\2225-w-8th-ave.json --programs bch.chf.eligibility,bc.bcbuilds.eligibility --candidate funder-ready --as-of 2026-11-23 --out $d\options\2225-w-8th-ave-suggest-funder-ready.json
& $py -m ffm run --site $d\sites\2225-w-8th-ave.json --option $d\options\2225-w-8th-ave-suggest-funder-ready.json --out $d\runs\2225-w-8th-ave\suggest-funder-ready --as-of 2026-11-23
```

| Item | Tool | My check |
|---|---|---|
| Outright | not assessed: "the rules have no R5-3 schedule" | Honest. |
| Suggested "funder-ready" option | 6 storeys, 1,908 m², FSR 3.43, **12 homes**, tiers 4 / 6 / 2 | 1,908 ÷ 12 = **159 m² of building per home**; capital $12,464,173 = $1.04M per home. The floor area is the envelope times the storeys; the homes are what the solver placed; nothing reconciles them (P2-5). |
| Funders | **Fail**: "unit mix market 33.3%, rgi 50.0%, deep subsidy 16.7% is not 30/50/20" | The candidate called funder-ready fails the fund it was derived for. The suggester did warn, in a sentence that contradicts itself (see verbatim messages). |
| Egress | conditional, exits 4.8 m apart | Plausible on a 12 m plate. |

## What I trust

1. **The lookup's parcel area and district when the address matches.** 2,966.7 m² against 2,964 m² from the public record, and CD-1 (849) with its number.
2. **"Not assessed" and the open items that come with it.** On CD-1 (849) and R5-3 the memo refuses to say yes, names the missing by-law and says the yards were not checked. That is what I would write.
3. **The arithmetic.** Every pro-forma line I recomputed on two sites was right to the dollar, and each line names its rule or says "placeholder".
4. **The family-unit and CHF-mix checks** on a real, announced mix.
5. **The egress flag on a narrow lot** and the sentence that goes with it.
6. **The stamp and the diff.** Same rules, same fingerprint on every run; the what-if's "What changed" table (IRP conditional to pass at 19.8 m) is the line I would read out at a meeting.

## Findings

### P1: would mislead a client or a board

**P1-1. The answers price and fund homes the tool's own plan cannot hold, and say nothing.**
Evidence: `runs/2001-stainsbury-ave/as-approved/memo.md`: section 2 "Meets the criteria of the Community Housing Fund", section 4 grant "$171,211 per unit × 123" and rent on 123 homes; under "Layouts derived from the option": "93 of 123 units placed… Did not fit on the plates: One-bedroom × 7 (407 m²); Studio × 23 (902 m²)". Section 3 (what is unsure) has no row for it. Same in `runs/6172-fraser-st/my-scheme/memo.md`: "Meets the criteria of BC Builds and the Community Housing Fund" with 34 homes funded and "22 of 34 units placed". The 15 Nov review raised this as its first item.
Consequence: a board reads "fits the funders" on a count the drawing below contradicts by a quarter to a third.
What I want: a line in answer 2 and a row in answer 3 ("30 of 123 homes are not on the plates: architect to resolve"), and a second pro-forma column at the placed count.

**P1-2. The front street the lookup picks decides the yield, and on this real corner site it picked the one that gives 19% of the approved homes.**
Evidence: `sites/2001-stainsbury-ave-as-looked-up.json` `front_street: "Victoria Drive"`; `runs/2001-stainsbury-ave/as-approved-front-as-looked-up/memo.md`: "plate 473 m² × 7 storeys = 3,311 m² (FSR 1.12)… a point tower… 23 of 123 units placed"; its `site-plan.svg` shows a 22.0 × 21.5 m square in a 1,938 m² envelope. `suggest` on the same file gave 2,838 m² and 27 homes; with the front on Stainsbury it gave 8,900 m² and 95. Two things compound: the plate box is a rectangle square to the chosen front, so on a lot whose long sides run at an angle to it the box collapses; and above six storeys the plate is held to about 21 m deep, so a seven-storey bar becomes a "point tower".
Consequence: a factor of four in yield from one field the manager is merely told to "confirm".
What I want: try both fronts and show both yields; align the plate box to the longest lot line, not the front; do not treat seven storeys as a tower.

**P1-3. "Allowed outright: yes" on C-2A at FSR 3.5 with the clause's own condition untested.**
Evidence: `runs/6172-fraser-st/suggest-outright/memo.md` section 1 says yes "(s.3.1.1.1(a), a mixed-use residential building with every home rental and 0.35 FSR of non-dwelling use at the street; 2.5 otherwise)" while the option has `non_residential_gfa_m2: 0` and BC Builds reads "Non-residential space is 0.0% of area". `ledger.json` `cov.c2a.outright_fsr` values: `max_fsr_outright 3.5, max_fsr_base 2.5`.
Consequence: an all-residential six-storey scheme is told it is outright at 3.5 when, on the tool's own citation, it is at 2.5 or at the Director's discretion.
What I want: test `non_residential_gfa_m2 ÷ site area ≥ 0.35`; below it, read 2.5 as the outright figure and the relaxation as conditional. And have `suggest` put the 0.35 on the ground floor.

**P1-4. A typed civic number that the City's list lacks returns a lot somewhere else, and the console does not say.**
Evidence (kept under `sites/_candidates/`): "2009 Stainsbury Ave" (the rezoning's own address) returned 1851 Stainsbury Ave, R1-1, 3,393 m²; "3350 Kingsway" returned 488 Kingsway (Mount Pleasant); "5750 Fraser St" returned 708 E 15th Ave. Console, verbatim: `wrote …\2009-stainsbury-ave.json: R1-1, 3393.1 m²`. The warning ("You typed 2009; the City's address list has no such number on this street, and the nearest parcel is 1851 Stainsbury Ave. Use it only if that is the site.") is only in the JSON's `notes`, and "nearest" appears to mean nearest to the street's geocoded point, not to the number typed. At least 10 of my 27 lookups came back as another lot (8 of the last 10, where I printed the flag). Some of the numbers I typed were guesses that may not exist; that is the case the tool must handle.
Consequence: a memo on the wrong parcel and the wrong district, with a tidy area.
What I want: print the mismatch on the console and refuse `--out` without a flag; pick the nearest civic number on that street, or return nothing.

### P2: I would have to redo the work

**P2-1. The plate solver is a single bar parallel to the street; I would redraw every plan.** On the 25 m Fraser lot it places 5 homes on a 513 m² floor and draws the rest "spare" (`plans.svg`, typical floor). On Stainsbury it stacks three-beds under two-beds under one-beds, so no party wall or wet wall lines up from floor to floor (`stacking.svg`: level 2 "Three-bedroom+ × 9", level 5 "Two-bedroom × 13", level 7 "One-bedroom × 18"), which is not how I would plan a wood or mass-timber building. One lift for 123 homes. No lobby, no refuse room, no parkade ramp. I want: the corridor tried both ways; unit types stacked in vertical bays; a lobby block; lifts by home count.

**P2-2. Placeholder side yards on a zero-lot-line street.** `options/6172-fraser-st-suggest-*.json` `setbacks_m.side: 2.0`; `site-plan.svg` table "Side yard · 2.0 m · not given · info". I want the suggestion to take 0 where the schedule asks for none, and the site to record what it adjoins.

**P2-3. The plate box loses about a metre each way to its 0.5 m grid** (`massing.json`, Fraser: envelope 650 m², box 20.0 × 30.0 = 600 m²). On an 881 m² lot that is a home per floor.

**P2-4. Slivers and stray blocks.** Amenity 0.86 m wide; bicycles on level 2 (Fraser `layout.json`, floors 0 and 1). A sheet with those on it does not go to a client.

**P2-5. The suggested floor area and the suggested homes are not reconciled.** W 8th: 1,908 m² for 12 homes. Stainsbury funder-ready: suggested 8,900 m² (a 1,483 m² plate) when the tool's own plate box is 1,312 m² ("Proposed: 6 storeys, FSR 3.00 — plate 1,312 m² × 6 storeys = 7,872 m² (FSR 2.65)" in `runs/2001-stainsbury-ave/suggest-funder-ready/memo.md`). The pro-forma then costs floor area nothing lives in. I want the suggestion cut to what the plates hold, both ways.

**P2-6. The districts I would bring most often are missing.** R3-2, R3-3 and R5-3 came back from the City's dataset on four low-rise apartment probes; the stack carries RM-3, RM-3A and RM-4. I cannot tell from the tool whether those RM schedules still apply anywhere. I want a coverage line per district: how many parcels in the City carry it today.

**P2-7. The three candidates are one building.** On Fraser, outright, benchmark and funder-ready are identical in storeys, height, floor area and homes; on Stainsbury likewise. I expected three options to argue between.

**P2-8. The hard cost base and the grant line sit in the headline unqualified.** $4,693/m² from a fourplex catalogue on a seven-storey building; the CHF line at $171,211 a home against $13.84M ÷ 123 = $112,520 a home announced from that fund for this building (public record). The closing note says "replace them", but the bold gap does not.

### P3: polish

- **P3-1.** `memo.md` is 93 to 96 KB and about 300 lines, because the full ledger prints 60 to 63 "Not applicable: Written for C-2 districts; this site is zoned CD-1 (849)" rows, each with a paragraph of source text. The 20 rules that apply are buried. Fold the rest into one counted line.
- **P3-2.** "**Proponent:** None (non profit society)" (line 4 of every memo with no proponent).
- **P3-3.** `massing.svg` caption "street (y = 0 is the top edge)" while every other sheet says "street at the bottom"; the lot is drawn mirrored between `massing.svg` and `site-plan.svg`.
- **P3-4.** Three sets of lot figures on one site: 83.5 × 35.5 m (site file), "91.42 × 43.21 m, 2,967 m²" (`massing.svg` title), "Lot polygon 2,943 m²" (`site-plan.svg`), against a site area of 2,966.7 m².
- **P3-5.** One floor-to-floor for every storey; my 4.5 m shop floor is drawn at 3.3 m in `elevations.svg`, and the C-2 height rule turns on a 5.2 m first storey.
- **P3-6.** No four-bedroom type (Vienna House has six: public record).
- **P3-7.** An already-enacted CD-1 still reads "By rezoning: not yet confirmed" against the Interim Rezoning Policy; the question there is conformity with the by-law.
- **P3-8.** The staff benchmark (19.9 to 21.3 m, FSR about 3.0) is cited from another site's referral report; say "from one precedent" in the finding, not only in the source.

## Crashes and confusing messages, verbatim

No command crashed. Every `lookup`, `suggest` and `run` completed.

1. `suggest --candidate outright` on a site with no schedule prints, with no explanation,
   `funder-ready: 6 storeys, 19.8 m, 8900.0 m² GFA, units {…}, tiers {'market': 29, 'rgi': 47, 'deep_subsidy': 19}, trees 25`
   and writes a file I named `…-suggest-outright.json` whose id is `2001-stainsbury-ave-suggested-funder-ready`. Same on R5-3. I asked for outright and got funder-ready silently.
2. `unsure · unit_count_for_the_mix: 12 homes cannot split 30 / 50 / 20 within the fund's tolerance; the nearest split is 4 / 6 / 2, which the fund's check will call short (Manager: plan at least 10 homes, or ask BC Housing whether a smaller count can be read as meeting the mix)`. Twelve is already at least ten.
3. `wrote …: R1-1, 3393.1 m²` for a different lot than the one typed (P1-4).
4. `wrote …: RM-3A, ? m²` for "2250 Wall St" (no parcel found); the "?" is the only sign.
5. "Proposed: 7 storeys, FSR 3.46 — plate 1,312 m² × 7 storeys = 9,184 m² (FSR 3.10)". Two FSRs in one line.
6. "Meets the criteria of the Community Housing Fund." followed by "The Community Housing Fund's 2025 call was cancelled in February 2026": correct, but the bold sentence is the one that gets quoted.

## Would I use this on a real feasibility, and for which step?

**Yes, for the first two hours; not for the page I hand over.**

- **Use:** the address-to-site step when the address matches (district, CD-1 number, area, corner flag); the rule screen as a checklist with clauses (IRP benchmark, family units, CHF mix and readiness, trees, TOA left open with a named owner); the stamp and the diff between two options.
- **Use with my own numbers typed in:** the pro-forma as a transparent calculator. Its arithmetic is right; its inputs are not mine yet.
- **Not yet:** yield. On the one site where I know the answer the plates hold 93 of 123 with the front I chose and 23 with the front the tool chose. I would not show a society a home count from this without drawing the plate myself.
- **Not at all, today:** the plans, stacking and elevations as client drawings. They are a fit test, and should say so more loudly than "not a design" in the foot line.

What would change my answer: P1-1 and P1-2 fixed, and the plate following the lot line.

## Three lines to quote

1. "It got the site area of a built project right to a tenth of a percent and the homes on it wrong by a quarter; I trust its reading and not yet its drawing."
2. "Every dollar in the pro-forma adds up and tells me where it came from; the inputs are still placeholders, and the bold number does not admit it."
3. "The best sentence in the memo is 'not assessed'. The worst is a 'yes' that depends on a clause the tool quotes and never tests."

## Files

- Sites: `sites/2001-stainsbury-ave.json` (edited), `sites/2001-stainsbury-ave-as-looked-up.json`, `sites/6172-fraser-st.json`, `sites/2225-w-8th-ave.json`; mismatched lookups kept as evidence in `sites/_candidates/`.
- Options: `options/2001-stainsbury-ave-as-approved.json`, `options/2001-stainsbury-ave-what-if-6-storey.json`, `options/6172-fraser-st-my-scheme.json`, and nine `…-suggest-<candidate>.json` files.
- Memos: `runs/2001-stainsbury-ave/as-approved/memo.md`, `runs/2001-stainsbury-ave/what-if-6-storey/memo.md`, `runs/2001-stainsbury-ave/suggest-funder-ready/memo.md`, `runs/2001-stainsbury-ave/as-approved-front-as-looked-up/memo.md`, `runs/6172-fraser-st/suggest-outright/memo.md`, `runs/6172-fraser-st/my-scheme/memo.md`, `runs/2225-w-8th-ave/suggest-funder-ready/memo.md`.
- The sheets were read by rendering the SVGs to PNG with a headless Edge into a scratch folder outside the repository. The Stainsbury plan and site-plan sheets were looked at from a first run with an assumed unit mix (102 of 123 placed); the option was then re-run with the public-record mix, and the stacking sheet and every figure quoted here are from that final run (93 of 123).
- Web pages opened: https://www.shapeyourcity.ca/2009-2037-stainsbury-ave and https://news.gov.bc.ca/releases/2024HOUS0021-000204.
