# Simulated user test (role-play by an AI reviewer), not a practitioner's statement

Persona: a development manager at a youth-serving non-profit (modelled on Covenant House Vancouver's public profile). I do not speak for that organisation. Every figure below is labelled **public record (URL)** or **my assumption**. Tested 23 Nov 2026, rules as of 2026-11-23, stamp `4227307d738e56fe`, engine 0.1.0.

**Not exercised:** the web UI (another reviewer had the browser), the PDF, Revit, "Ask Claude". This was the command line plus the generated `memo.md` and `proforma.json`. A real manager would never use a command line or edit JSON; everything I say about wording comes from the memo, and everything about effort is understated.

## Who I am and what I need

- I manage capital projects and funder applications for shelter, transitional and supportive housing for youth 16 to 24, and I report to a board.
- Before I ask the board for $200k to $500k of predevelopment money I need three things: can I build it here, which funder program is it shaped for and is that program open, and is the capital **and operating** gap one I can plausibly close.
- I need a two-page memo a volunteer board member can read cold, and a call list for Monday.

## Site A: the existing campus (575 Drake St / 1280 Seymour St, and 1302 Seymour St)

### Commands (repo as working directory; `PY` = the uv CPython 3.12 interpreter)

```powershell
$d = "docs\user-tests-2026-11-23\manager-covenant-house"
& $PY -m ffm lookup "575 Drake St, Vancouver, BC"   --out "$d\sites\575-drake-st.json"
& $PY -m ffm lookup "1302 Seymour St, Vancouver, BC" --out "$d\sites\1302-seymour-st.json"
& $PY -m ffm lookup "1280 Seymour St, Vancouver, BC" --out "$d\sites\1280-seymour-st.json"
& $PY -m ffm suggest --site "$d\sites\1280-seymour-st.json" --programs bch.chf.eligibility,bc.bcbuilds.eligibility --candidate outright|benchmark|funder-ready --as-of 2026-11-23 --out "$d\options\1280-seymour-st-suggest-<candidate>.json"
& $PY -m ffm run --site "$d\sites\1280-seymour-st.json" --option "$d\options\1280-seymour-st-as-built.json" --out "$d\runs\1280-seymour-st\as-built" --as-of 2026-11-23
& $PY -m ffm run --site "$d\sites\1302-seymour-st.json" --option "$d\options\1302-seymour-st-as-built.json" --out "$d\runs\1302-seymour-st\as-built" --as-of 2026-11-23
& $PY -m ffm run --site "$d\sites\1280-seymour-st.json" --option "$d\options\1280-seymour-st-suggest-funder-ready.json" --out "$d\runs\1280-seymour-st\suggest-funder-ready" --as-of 2026-11-23
```

### Inputs and their sources

| Input | Value | Label |
|---|---|---|
| 575 Drake (north site, now 1280 Seymour): FSR, height, beds, parking at rezoning | 5.15, 36 m, 75 shelter beds, 4 stalls | public record: public hearing deck 24 Jan 2017 (copy at https://www.sambuz.com/doc/cd-1-rezoning-application-530-575-drake-street-ppt-presentation-147112) |
| 530 Drake (south site, now 1302 Seymour): FSR, height, beds, parking | 3.05, 21 m, 14 shelter beds, none | same deck |
| 1280 Seymour as built | 10 storeys; 40 shelter units, most two-bed, up to 80 spaces; opened July 2022 | public record: https://news.gov.bc.ca/stories/new-housing-for-at-risk-youth-now-open-in-vancouver and https://news.gov.bc.ca/releases/2024HOUS0129-001153 |
| 1280 Seymour funding | CMHC National Housing Co-Investment Fund about $7.8M; BC Housing grant about $2.5M; BC Housing about $475,000 a year operating; about $23.66M donations | public record: same two pages |
| 1280 Seymour total cost | "$34 million" | public record, headline only, as returned by a web search: https://dailyhive.com/vancouver/1280-seymour-street-covenant-house-vancouver-youth-shelter |
| 1302 Seymour as built | 5 storeys, 28 units/beds, completed Feb 2019; BC Housing $5M; CMHC $5.1M | public record: https://news.gov.bc.ca/releases/2024HOUS0129-001153 ; https://www.cmhc-schl.gc.ca/media-newsroom/news-releases/2019/expansion-vancouver-shelter-provide-refuge-for-more-homeless-youth |
| 1302 Seymour private funds | about $10M | public record as summarised by a web search of https://news.gov.bc.ca/releases/2017MNGD0045-000773 (I did not read the release itself) |
| Floor areas | 4,312 m² and 1,630.5 m² | **my assumption**: rezoning FSR × the parcel area the lookup found (837.3 and 534.6 m²) |
| Units as entered | 40 and 28 **studios**, all "deep subsidy", all supportive | **my assumption**: the tool has no shelter bed, sleeping room or transitional unit type |
| Land $0; equity = donations; other grants = CMHC + BC Housing | | **my assumption** on how to place public figures into the tool's three money fields |
| Setbacks 0; floor to floor = height ÷ storeys | | **my assumption** |

The council report itself (council.vancouver.ca/20161213/documents/p2.pdf) returned HTTP 403 to an automated fetch. I did not retry; a person would have to save it.

### What the tool answered

| Question | 1280 Seymour as built | 1302 Seymour as built |
|---|---|---|
| Outright | not assessed (CD-1 (701) not in the rules) | not assessed (CD-1 (686) not in the rules) |
| By rezoning | **no** (family units fail: 0 of 40 two-bed+) | **no** (0 of 28) |
| Funders | does not meet CHF or BC Builds | same |
| Money | **Likely**, $12.6M "to spare"; capital $28.2M; NOI **−$52,880/yr** | **Likely**, $14.2M "to spare" (−134%); capital $10.65M; NOI −$37,016/yr |
| Layout | 40 of 40 placed, 3 empty floors | 23 of 28 placed; exits conditional |

### Tool vs public record

| | Tool | Public record | My read |
|---|---|---|---|
| "575 Drake St" | found **1280 Richards St**, a 2,647 m² strata parcel in DD | the building is addressed 1280 Seymour St today | Wrong parcel. The warning is only inside the JSON `notes`; the terminal printed `wrote …575-drake-st.json: DD, 2647.3 m²` |
| Zoning | CD-1 (701), CD-1 (686) | rezoned DD to CD-1 in 2017 | Correct and useful |
| Allowed by rezoning | no | Council approved both; both are built | **Wrong answer on a known case**, caused by the family-unit rule |
| Funder fit | fails CHF and BC Builds | funded by CMHC NHCF/AHF, BC Housing (Housing Innovation fund), donations | True but useless: none of the real programs exist in the tool |
| Capital, 1280 | $28.2M | about $34M reported | 17% low; plausible for a screen, though my floor area is derived |
| Capital, 1302 | $10.65M | the public sources named total at least $20M | Roughly half; I would not trust $4,839/m² downtown |
| Operating | $6,500/unit, no subsidy line, NOI negative | BC Housing pays about $475,000/yr at 1280 Seymour (about $11,900 per unit, subsidy alone) | The tool has no way to say this |
| Homes | 40 studios of 36 m² | 40 shelter units, most with two beds | Unit model does not fit |

## Site B: 4250 Fraser St (C-2A): HYPOTHETICAL

A real lot picked only for district and size (599.7 m², 21.1 × 28.4 m, corner of E 27th Ave). **It is not a plan of any organisation; nobody in this test controls the site; every program and money figure is my assumption.**

### Commands

```powershell
& $PY -m ffm lookup "4250 Fraser St, Vancouver, BC" --out "$d\sites\4250-fraser-st.json"
& $PY -m ffm suggest --site "$d\sites\4250-fraser-st.json" --programs bch.chf.eligibility,bc.bcbuilds.eligibility --candidate outright|benchmark|funder-ready --as-of 2026-11-23 --out "$d\options\4250-fraser-st-suggest-<candidate>.json"
& $PY -m ffm run --site "$d\sites\4250-fraser-st.json" --option "$d\options\4250-fraser-st-youth-transitional.json" --out "$d\runs\4250-fraser-st\youth-transitional" --as-of 2026-11-23
& $PY -m ffm run --site "$d\sites\4250-fraser-st.json" --option "$d\options\4250-fraser-st-suggest-funder-ready.json" --out "$d\runs\4250-fraser-st\suggest-funder-ready" --as-of 2026-11-23
```

### My board scheme (all my assumptions)

Six storeys, 19.8 m, 2,099 m² (the tool's own envelope, FSR 3.50); 300 m² of program and staff space at grade; 30 studios and 4 one-bedrooms, all supportive; 24 at the shelter rate, 10 rent-geared-to-income; no parking; 2 accessible homes; 60-year agreement; no developer partner; no site control; land $5,000,000, equity $2,000,000, other grants $0 (round placeholders, not a valuation).

### What the tool answered

| Question | My youth scheme | Tool's own "funder-ready" suggestion |
|---|---|---|
| Outright | **yes** (FSR 3.50 of 3.5, 19.8 m of 23.0 m) | yes |
| By rezoning | terminal says "no"; the memo prints no such line | terminal says "not yet confirmed" |
| Funders | fails both (tier split 0/29/71 is "not 30/50/20"; no partner; no site control) | not yet confirmed |
| Money | Needs more sources: capital $18.7M, funding $8.1M, gap $10.6M (57%) | Needs more sources: $13.7M for **14 homes**, gap $9.7M (71%) before land |
| Layout | **21 of 34 homes placed; egress fail on all 6 floors** | 14 of 14 placed; **egress fail on all 6 floors** |

### Tool vs what I know

| | Tool | What I know | My read |
|---|---|---|---|
| Zoning read | C-2A, rental mixed-use 3.50 FSR / 23 m outright, 0.35 FSR non-dwelling at the street | consistent with how these arterial sites are described | The most useful single line I got; I'd still have the architect confirm the schedule |
| Front yard | 0.6 m against a 2.5 m minimum, conditional, architect | fair | Good catch, right person |
| Family units | **Fail**, "add family units until both minimums are met" | an outright scheme is not a rezoning; a youth transitional building is not family housing | Wrong rule, wrong advice |
| Yield | 14 to 21 homes in 2,099 m² | a studio building of this size should hold many more | The plate solver, not the by-law, is limiting the program, and the headline does not say so |
| RGI rent | $1,073 a month per home (10 homes, $128,805/yr) | young people leaving shelter are on income assistance or entry wages | Rent assumed is far too high for this population |
| Operating | $6,500/unit/yr, no staffing, no subsidy | supportive housing runs on an operating agreement; staffing dominates | Missing the line that decides whether the building can open |
| Funders | CHF, BC Builds | supportive / transitional / youth programs, CMHC rapid-housing style capital, Reaching Home | Not the programs I would apply to |

## What I trust

- The lookup when the address is in the City's list: district, CD-1 number, parcel area, corner-lot warning. Fast and right three times out of four.
- "Not assessed" for a CD-1 it has no by-law for, instead of a guess. That is the honest answer and it names what to fetch.
- The C-2A outright reading with clause numbers, and the yard relaxation flag.
- That every pro-forma line shows its arithmetic and marks placeholders. I can see exactly where I disagree.
- The note that the CHF 2025 call was cancelled and no intake is open.
- "What stays on the lot" as an open item addressed to me.

## Findings

### P1

**P1-1. Grant money from a fund the project fails, and that is closed, is counted in the funding stack.**
Evidence: `runs/1280-seymour-st/as-built/memo.md` line 22 says CHF "does not meet the criteria" and "no intake is open now"; line 62 adds "Community Housing Fund grant $6,848,440"; line 39 concludes "**Likely.** … $12,639,932 to spare". Same in `runs/4250-fraser-st/youth-transitional/memo.md` lines 15 and 55 ($5,821,174, 72% of all funding shown), and in 1302 Seymour ($4,793,908).
Consequence: answer 2 and answer 4 contradict each other on one page. On my hypothetical the gap without that grant is $16.4M, not $10.6M. A board member would catch this and stop reading.
Instead: count a program's grant only when its check passes and an intake is open; otherwise show it as "not counted: $X if eligible".

**P1-2. No funder in the rule stack fits a youth supportive or transitional program, and the memo does not say so.**
Evidence: `python -m ffm rules --as-of 2026-11-23` layer E holds four rules: CHF, BC Builds, the predevelopment loan, CMHC AHF readiness (info only). The public record for this campus names CMHC's National Housing Co-Investment Fund, a BC Housing Housing Innovation grant, BC Housing's Shovel Ready Housing program, CMHC's Rapid Housing Initiative and Reaching Home (news.gov.bc.ca/releases/2024HOUS0129-001153). None is in the tool. The CHF check fails my scheme because 100% deep subsidy "is not 30/50/20" (1280 memo line 22), i.e. it is too affordable.
Consequence: answer 2 reads as "your project is not fundable" when it means "these two programs are for mixed-income rental". The action "Manager: resolve the failing criteria" (line 35) would have me add market units to a shelter.
Instead: a program-type question up front (independent rental / supportive / transitional / shelter), and when nothing in the stack fits, say "No program in this tool is designed for this use; ask BC Housing which supportive housing stream is open."

**P1-3. The family-unit rule is applied to shelters, to supportive youth housing and to a scheme that needs no rezoning; it turns two approved, built projects into "By rezoning: no".**
Evidence: 1280 as-built memo line 12 "**By rezoning … : no.**", line 15 "Only 0 of 40 units (0.0%) have two or more bedrooms, below the 35.0% minimum", line 32 "Change the unit mix: add family units until both minimums are met." Fraser memo line 24 prints the same fail under "Family-unit requirement **in rezonings**" although line 10 says outright: yes. I set `supportive_units` equal to all units; only the Downtown Eastside area-plan rule reads that field (`ffm/checks.py` lines 395 to 401).
Consequence: the tool gets a known public case wrong, and tells me to put three-bedroom homes in a youth crisis building.
Instead: not applicable (with the reason) when all homes are supportive, transitional or shelter, and when the option is outright; at most an open item, "Planner: confirm the family housing guidelines do not apply to this use."

**P1-4. No operating picture, and a building that loses money every year reads "Likely".**
Evidence: 1280 as-built memo line 42 "Net operating income **$-52,880 a year**", line 39 "**Likely.**" Operating cost is $6,500 per unit (placeholder, line 59), with no staffing or support-services line and no operating subsidy line. Public record: about $475,000 a year in BC Housing operating funding for that one building.
Consequence: for supportive housing the operating agreement is the feasibility question. The verdict looks only at capital.
Instead: an operating section with staffing, a "subsidy required per year" line, and a rule that negative NOI can never read "Likely".

**P1-5. `lookup "575 Drake St"` silently returned a different property.**
Evidence: `sites/575-drake-st.json` has `"id": "1280-richards-st"`, `"civic_mismatch": true`, a 2,647 m² parcel `BCS747` in DD. The only terminal output was `wrote …\575-drake-st.json: DD, 2647.3 m²`. The warning ("You typed 575; the City's address list has no such number on this street…") is inside the JSON `notes`.
Consequence: from the CLI I would have run a memo on someone else's condominium site, three times the size of mine.
Instead: print the mismatch to the terminal and refuse to write without confirmation. (The UI may already do this; not tested.)

### P2

**P2-1. Answer 1 says "yes" while the layout says the program does not fit and the exits fail; neither reaches the open-items table.** Fraser memo line 10 "yes"; line 73 "21 of 34 units placed"; line 98 "Egress … fail; 6 floors: 6 fail"; the table at lines 18 to 27 has no row for either. The tool's own funder-ready suggestion also fails egress on every floor. I'd want "13 homes not placed" and "exits" as open items for the architect, and the headline to read "allowed, but the program does not fit as drawn".

**P2-2. Yield is implausibly low and the suggestion does not flag it.** The suggester puts 14 homes in 2,099 m² (150 m² of building per home, about $979,000 per home at the tool's own cost). A studio-led supportive building is the obvious use of this lot and there is no way to ask for it from the CLI: the mix starts from the family split.

**P2-3. `suggest --candidate outright` on a CD-1 site returns the funder-ready option without saying so.** The terminal printed `funder-ready: 6 storeys, 19.8 m, 2941.0 m² GFA …`; `options/1280-seymour-st-suggest-outright.json` line 2 has `"id": "1280-seymour-st-suggested-funder-ready"`. All three candidates on that site are the same envelope. It should say "no outright candidate: the CD-1 by-law is not in the rules".

**P2-4. Terminal and memo disagree on the rezoning answer.** For the Fraser scheme the run printed `allowed outright: yes · by rezoning: no`; the memo prints no by-rezoning verdict at all, yet lists rezoning-policy rows (Community Vision map, family units) as open items. If outright is yes and no rezoning is asked for, those rows should not be there.

**P2-5. Cost base is a 2- to 4-unit wood-frame catalogue figure applied to a 10-storey downtown building.** 1280 memo line 48: "average of Quadplex 01 … Quadplex 02 … and Townhouse", $4,693/m². The rule file admits it; the memo's verdict does not carry the caveat. 1302 Seymour came out near half of the public funding total.

**P2-6. RGI rent is set from half the CHF income limit: $1,073 a month for a youth studio.** Fraser memo line 49. For a youth program I would enter rents myself; there is no field for it.

**P2-7. Shelter beds and sleeping rooms cannot be entered.** I had to call 40 two-bed shelter units "40 studios". The memo then drew three empty floors (levels 8 to 10, 1280 memo lines 111 to 113) where the real building has program and office space.

**P2-8. Open items mostly name a role, but several say only what, not who.** "Change the unit mix…" (no person); "Manager: resolve the failing criteria" (not an action). The Community Vision map and TOA map go to "Architect"; I would make that call to the City myself, and for a downtown CD-1 site the Community Vision question is noise.

### P3

- The memo is 96 KB of Markdown; Layer A alone is 60-odd "Not applicable: written for C-2 districts…" rows (from line 121). The board version must drop them (the README says the paper does; not verified here).
- A surplus is printed as "Gap **$-12,639,932** (-45% of the capital cost)" and "-134%". Say "surplus".
- "Schedule C requires 6 trees on a 837 m² site" on a zero-lot-line downtown building; harmless but adds a row.
- Open-item text refers to "stop 1", "stop 3", "inbox/": UI and repo jargon in a memo meant for a board.
- "Deep subsidy", "RGI", "HILs" are not glossed in `memo.md`.
- The site file written to the name I chose keeps a different `id` inside (`1280-richards-st`), so run folders and file names can drift apart.

## Crashes and confusing messages (verbatim)

No crash in any command. Confusing:

- `wrote docs\user-tests-2026-11-23\manager-covenant-house\sites\575-drake-st.json: DD, 2647.3 m²` (it was 1280 Richards St).
- After `--candidate outright`: `funder-ready: 6 storeys, 19.8 m, 2941.0 m² GFA, units {'studio': 6, 'one_bed': 12, 'two_bed': 9, 'three_bed_plus': 2}, tiers {'market': 9, 'rgi': 14, 'deep_subsidy': 6}, trees 6` (a Python dict in a message to a person).
- `allowed outright: not assessed · by rezoning: no · funders: no · money: likely` for a building that exists.
- "Note: The setbacks leave no envelope inside the lot polygon that a rectangular plate fits; the equivalent rectangle is used for the envelope." I do not know what I am supposed to do with that.
- Fetching `https://council.vancouver.ca/20161213/documents/p2.pdf`: `The server returned HTTP 403 Forbidden.` Not the tool's fault; noted, not retried.

## Would I take this memo to my board or to BC Housing?

No, not as it stands, for a youth supportive or transitional project.

To my board I would take **one paragraph** from it: the zoning read for the Fraser-type site (district, outright FSR and height with clause numbers, the yard relaxation, what stays on the lot). That is real value on day one.

To BC Housing I would take nothing: the memo tests my project against two programs it was never going to use and reports a failure.

What must change first, in order:

1. Stop counting grants from failed or closed programs (P1-1).
2. Ask what kind of housing this is, and switch off the family-unit rule and the 30/50/20 test when it is supportive, transitional or shelter; say plainly when no coded program fits (P1-2, P1-3).
3. Add an operating page: staffing, subsidy required, and never "Likely" on negative NOI (P1-4).
4. Put "program does not fit" and "exits fail" into the answers and the open items (P2-1).
5. Run the two Seymour buildings again and get "allowed by rezoning: yes, as Council approved" before showing it to anyone who knows them.

## Three lines to quote

- "It told me a building Council approved and that has been open since 2022 is not allowed, because a youth shelter has no three-bedroom units."
- "Answer two says the fund rejects us and is closed; answer four spends its $6.8 million anyway."
- "The zoning paragraph is worth having on day one. The funder and money pages are written for a different kind of housing than the one I build."

## Files

- Sites: `sites/1280-seymour-st.json`, `sites/1302-seymour-st.json`, `sites/4250-fraser-st.json`, `sites/575-drake-st.json` (the mis-lookup, kept as evidence).
- Options: `options/1280-seymour-st-as-built.json`, `options/1302-seymour-st-as-built.json`, `options/4250-fraser-st-youth-transitional.json`, and six `*-suggest-*.json`.
- Runs: `runs/1280-seymour-st/as-built/`, `runs/1280-seymour-st/suggest-funder-ready/`, `runs/1302-seymour-st/as-built/`, `runs/4250-fraser-st/youth-transitional/`, `runs/4250-fraser-st/suggest-funder-ready/`.

Sources used for the public record:
- [Province of BC, New housing for at-risk youth now open in Vancouver](https://news.gov.bc.ca/stories/new-housing-for-at-risk-youth-now-open-in-vancouver)
- [Province of BC release 2024HOUS0129-001153](https://news.gov.bc.ca/releases/2024HOUS0129-001153)
- [CMHC, Expansion of Vancouver shelter (2019)](https://www.cmhc-schl.gc.ca/media-newsroom/news-releases/2019/expansion-vancouver-shelter-provide-refuge-for-more-homeless-youth)
- [Public hearing deck, 530 & 575 Drake St (copy)](https://www.sambuz.com/doc/cd-1-rezoning-application-530-575-drake-street-ppt-presentation-147112)
- [Daily Hive, $34 million youth shelter](https://dailyhive.com/vancouver/1280-seymour-street-covenant-house-vancouver-youth-shelter)
- [Province of BC release 2017MNGD0045-000773](https://news.gov.bc.ca/releases/2017MNGD0045-000773)
