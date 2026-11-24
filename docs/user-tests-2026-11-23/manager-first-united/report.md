# Simulated user test (role-play by an AI reviewer), not a practitioner's statement

**Persona:** a development manager at a Downtown Eastside faith-based society redeveloping 320 East Hastings St with a partner Indigenous housing society. The persona is invented for ARCH 540; nothing here speaks for First United, Lu'ma Native Housing Society or any funder. Every figure is labelled **public record (URL)** or **my assumption**. Test date 23 Nov 2026, rules as of 2026-11-23, stamp `4227307d738e56fe`.

**How it was tested:** command line only, then reading `memo.md` and `proforma.json`. The web UI was **not** exercised (another reviewer had the browser). A real manager would not use a command line or edit JSON; everything below about "entering" a figure was done by editing a file, which I could not have done in the job.

## Who I am, and what I needed to know at the start

- I manage the redevelopment, the funders and the board; I am not an architect and I do not read by-laws for a living.
- At the start I needed four things: can we put four floors of services under seven floors of homes on our own lot without a rezoning; which funders pay for homes for Indigenous people at shelter and income-geared rents; what the society itself must raise; and who I have to phone first.
- I needed it in a form a volunteer board would vote pre-development money on.

---

## Site (a): 320 E Hastings St, the scheme as built

### Commands

```powershell
$py = "C:\Users\kaili\AppData\Roaming\uv\python\cpython-3.12.14-windows-x86_64-none\python.exe"
$d  = "docs\user-tests-2026-11-23\manager-first-united"
& $py -m ffm lookup "320 E Hastings St, Vancouver, BC" --out "$d\sites\320-e-hastings-st.lookup.json"
& $py -m ffm suggest --site "$d\sites\320-e-hastings-st.lookup.json" --programs bch.chf.eligibility,bc.bcbuilds.eligibility --candidate outright|benchmark|funder-ready --as-of 2026-11-23 --out "$d\options\320-e-hastings-st-suggest-<candidate>.json"
& $py -m ffm run --site "$d\sites\320-e-hastings-st.json" --option "$d\options\320-e-hastings-st-as-built.json" --out "$d\runs\320-e-hastings-st\as-built" --as-of 2026-11-23
#   the same for the options as-built-public-money, as-built-public-money-no-chf and suggest-funder-ready
```

### What the lookup found

- The right parcel, one lot: `438 Gore Ave`, site id 031308236, **1,362.3 m²**, DEOD. The architect's design rationale gives 1,362 m² (public record, quoted in search results from the City's Development Permit Board report, https://vancouver.ca/files/cov/320-ehastings.pdf, which refuses automated fetches and was not read). 438 Gore Ave is the homes' own entrance (public record, https://news.gov.bc.ca/releases/2023HOUS0151-001731). So the parcel is right and no assembly question arose.
- The message, verbatim: *"You typed 320; the City's address list has no such number on this street, and the nearest parcel is 438 Gore Ave. Use it only if that is the site."* Honest, but it named the site file `438-gore-ave`, and a manager who does not know the Gore Avenue address would stop here.
- District **DEOD**: the rule stack has no schedule for it.
- Owner, land tenure, transit area, Community Vision, bus stop: blank, as the tool says they will be.

### Inputs I entered (file `sites/320-e-hastings-st.json`, `options/320-e-hastings-st-as-built*.json`)

| Input | Value | Label |
|---|---|---|
| Storeys | 11 | public record (https://news.gov.bc.ca/releases/2023HOUS0151-001731) |
| Homes | 103 = 35 supportive + 68 rental prioritized for Indigenous people | public record (same; https://cmhc-schl.gc.ca/media-newsroom/news-releases/2023/canada-supports-103-new-affordable-homes-vancouver) |
| Community floors | floors 1 to 4, about 40,000 sq ft = 3,716 m² | public record (https://broadview.org/?p=62916; https://bcbusiness.ca/business/general/moving-first-forward/) |
| Unit types | all studios and one-bedrooms; entered 52 / 51 | types: public record (https://www.urbanyvr.com/?p=16166); the split is my assumption |
| Rents | 14 homes under $500 a month, the other 89 rent geared to income | public record (https://broadview.org/?p=62916) |
| Operator | Lu'ma Native Housing Society; First United runs floors 1 to 4 | public record (BC release above) |
| Approval route | development permit DP-2020-00721, DEOD Sub-area 1, Development Permit Board 25 Jan 2021, permit issued 15 Mar 2022; no rezoning | public record (search-result summaries of the City's Board report, minutes and Shape Your City page; the Shape Your City page returned 404 and the City PDFs were not fetched) |
| Parking | 12 stalls | public record (urbanYVR, 2020) |
| Residential floor area 5,764 m², total 9,480 m² (FSR 6.96), height 37.0 m | | **my assumption**: floor area, FSR and height are in the Board report I could not read |
| Share below HILs 1.0; setbacks 0 | | my assumption |
| Owner at completion, housing agreement term, accessible homes | left blank | not public |
| Money: BC Housing $28.4M (Indigenous Housing Fund $15.3M + Supportive Housing Fund $13.06M), CMHC Co-Investment $5.15M, City $6.73M (CHIP $4.83M + waivers), First United $24.4M (land and equity) + $9.6M still to raise | other grants $40.28M, equity $34.0M | public record (BC and CMHC releases, 6 Nov 2023); land entered as $0 is my assumption, the release does not split land from equity |
| Total cost | $65M (2021); "more than $64 million" combined funding (2023) | public record (BCBusiness; CMHC release) |

### What the tool answered (`runs/320-e-hastings-st/as-built/memo.md`)

1. **Allowed outright: not assessed** (no DEOD schedule). **By rezoning: no.**
2. **Funders: does not meet the criteria of BC Builds and the Community Housing Fund.**
3. Ten open items.
4. **Money: needs more sources**, capital $61.9M, funding $23.7M, gap $38.2M (62%). With the public money entered: **Likely**, $18.4M to spare (or $36.1M to spare, see P1-3).

### Tool vs public record

| Question | Tool | What actually happened (public record) | Verdict |
|---|---|---|---|
| Parcel | one lot, 1,362.3 m², DEOD | 1,362 m², DEOD Sub-area 1 | right |
| Allowed outright? | not assessed | approved by the Development Permit Board under the DEOD plan, no rezoning | no answer where I most needed one |
| By rezoning? | **no** (memo line 12) | there was no rezoning; 11 storeys with zero family homes were approved and built | wrong, and the wrong question |
| Family homes | fail: 0 of 68, 25% needed (line 14) | 103 studios and one-bedrooms, approved | the tool fails the project that was built |
| Supportive homes left out of the family count | yes, 35 left out, 68 counted | n/a | works as the rule file says |
| Funders | fails CHF (mix 0 / 86.4 / 13.6 is not 30/50/20) and BC Builds (39.2% non-residential over the 30% cap) | funded by the Indigenous Housing Fund, the Supportive Housing Fund, CMHC Co-Investment, City CHIP and a capital campaign | the tool has none of the five |
| Provincial grant | $17.6M ($171,211 x 103, from a fund it says the project fails and that is closed) | $28.4M ($276k a home) | not comparable |
| Federal, City, own money | nothing unless I type it | $5.15M, $6.73M, $24.4M + $9.6M | absent |
| Mortgage | $6.1M supportable | none is named in the announcements | cannot compare |
| Capital cost | $61.9M | $65M (2021); announced sources add up to $64.7M plus $9.6M to raise | within 5% to 17%, but see P2-1: on my guessed floor area and a quadplex cost rate |
| Homes that fit | 58 of 103 "placed"; 45 studios "did not fit" (line 101) | 103 built | partly my floor-area guess, partly the tool's unit sizes |
| Heritage | open item, architect | the replacement went to the Vancouver Heritage Commission (https://www.straight.com/news/first-united-church-indigenous-legacies-to-be-honoured-in-replacement-for-vancouver-downtown) | right item |

---

## Site (b): 877 E Hastings St. HYPOTHETICAL

A real parcel chosen only for its kind: M-1 on Hastings East, a corner, 1,419 m², four blocks west of the tool's own 1015 E Hastings St case. **It is not a plan of any organisation; I did not look up who owns it.** Every figure in the option is my assumption.

### Commands

```powershell
& $py -m ffm lookup "877 E Hastings St, Vancouver, BC" --out "$d\sites\877-e-hastings-st.lookup.json"
& $py -m ffm suggest --site "$d\sites\877-e-hastings-st.lookup.json" --programs bch.chf.eligibility,bc.bcbuilds.eligibility --candidate outright|funder-ready --as-of 2026-11-23 --out "$d\options\877-e-hastings-st-suggest-<candidate>.json"
& $py -m ffm run --site "$d\sites\877-e-hastings-st.json" --option "$d\options\877-e-hastings-st-intended-hypothetical.json" --out "$d\runs\877-e-hastings-st\intended-hypothetical" --as-of 2026-11-23
```

### Inputs (all my assumption)

10 storeys, 34 m, 7,096 m² (FSR 5.0): 1,900 m² of community services on two floors, 70 homes above (18 studio, 28 one-bed, 18 two-bed, 6 three-bed), rent tiers 21 / 35 / 14, a partner housing society as owner and operator of the homes, a 60-year agreement, 4 accessible homes, no site control, no land price. `area_plan: downtown_eastside` typed into the site file by hand.

### What the tool answered (`runs/877-e-hastings-st/intended-hypothetical/memo.md`)

- Lookup: exact address match, M-1, 38.1 x 37.3 m, corner with Campbell Ave. Good.
- `suggest`, **outright** candidate: *6 storeys, 19.8 m, 5,316 m², 56 homes*, with the note "the rule stack has no M-1 schedule".
- Run: outright **not assessed**; by rezoning **not yet confirmed** (only the transit map and the trees listed); funders **not yet confirmed** (land tenure, site control); money **needs more sources**, $46.4M before land, gap $26.2M.
- Downtown Eastside family target: **pass**, 24 of 70 (34.3%) against 25% (memo line 148), and the city-wide 35% rule correctly steps aside (line 149).
- Crash-like message on every run of this site: *"massing skipped: No road named 'Campbell Ave' adjoins the lot. The roads that adjoin it are: E Hastings St."* No massing, no plans, no drawings were written.

### Tool vs what I know of sites like this

| Question | Tool | Reality check | Verdict |
|---|---|---|---|
| Is housing allowed in M-1? | "not assessed"; the outright suggestion is six storeys of homes | M-1 is an industrial district (the lookup's own record says `zoning_classification: Industrial`); the tool's own precedent, 1015 E Hastings, needed a rezoning to CD-1 | misleading (P1-4) |
| Rezoning route | free text I typed, echoed back | the Downtown Eastside Plan's rezoning policy for Hastings East | nothing tested |
| Family target | 25% pass | as the rule file has it (marked unverified) | plausible |
| Money | CHF grant $12.0M counted while the fund is closed | n/a | see P1-3 |

---

## What I trust

- **The lookup.** It found the one right parcel under a different civic address, said so, and gave the area to the square metre.
- **"Not assessed" instead of "yes".** It did not pretend to know DEOD or M-1.
- **The supportive-homes exclusion** in the family count, and the city-wide family rule stepping aside inside the Downtown Eastside.
- **The arithmetic on show.** Every money line says what it multiplied; that is how I found everything below.
- **The closed-intake sentence**: "The Community Housing Fund's 2025 call was cancelled in February 2026, so no intake is open now." That is the sentence a board needs.
- **Heritage and "what stays on the lot"** as open items on a 1965 church site.

## Findings

### P1

**P1-1. On the project that was built, the memo says "By rezoning: no" and "does not fit the funders".**
Evidence: `runs/320-e-hastings-st/as-built/memo.md` lines 12, 14, 19 to 21. The "no" comes from `cov.dtes.family_units`, titled "family-unit target *in rezonings*", applied to a development-permit scheme with no rezoning; the funder "no" comes from testing the only two programs the tool has.
Consequence: had I taken this memo to my board, the answer on page one for the scheme that now stands at 320 East Hastings would have been no, no, and a $38M gap.
Want instead: (a) an approval route of "development permit under an official development plan", with rezoning rules switched off when there is no rezoning; (b) a family target that reads as a target to be discussed for supportive and single-adult Indigenous housing, not a fail with the action "add family units"; (c) the funder answer saying "the programs that fit this project are not in the tool" (next finding).

**P1-2. The funder layer does not contain the funding that built this project.**
Evidence: `rules/e_funding_programs.json` holds four entries: Community Housing Fund, BC Builds, the pre-development loan, CMHC AHF as a flag. Public record for 320 E Hastings: Indigenous Housing Fund $15.3M, Supportive Housing Fund $13.06M, CMHC Co-Investment $5.15M, City CHIP $4.83M, society equity and land $24.4M plus $9.6M to raise.
Consequence: for Indigenous-led, deep-subsidy and supportive housing, which is most of what gets built in the Downtown Eastside, question 2 can only ever answer about the wrong funds. The Community Housing Fund's 30% market-rent homes is exactly what this project was not. And the capital campaign for the community floors, which no housing program pays for, has no place at all.
Want instead: the Indigenous Housing Fund and the supportive stream as programs (with AHMA named as the partner), the City's CHIP grant, a "community space: who pays" line, and when the tiers entered look like deep subsidy, a sentence saying which program family the mix points to.

**P1-3. The pro-forma counts a grant from a fund the same memo says the project fails, and an empty program list means "all programs".**
Evidence: `ffm/proforma.py` lines 233 to 238: `targets = set(option.get("target_programs") or [])` then `not targets or ...`; nothing reads the check's status. `as-built/memo.md` line 63: "Community Housing Fund grant $17,634,733" under a section 2 that says the fund's criteria are not met and its intake is closed. With `target_programs: []` (`as-built-public-money/memo.md` line 44): "grants $57,914,733" = my $40.28M + $17.63M I never asked for, and "**Likely.** The funding stack covers the capital cost with $36,083,109 to spare." The same empty list also makes section 2 test both programs.
Consequence: a surplus on the board's page that includes $17.6M from a closed fund the project is ineligible for.
Want instead: a failed or closed program contributes $0 and the line says why; no programs chosen means no program grants.

**P1-4. An industrial lot gets a six-storey "outright" housing suggestion.**
Evidence: `suggest --candidate outright` on 877 E Hastings (M-1) prints "6 storeys, 19.8 m, 5316.0 m² GFA, units {...}" and writes `options/877-e-hastings-st-suggest-outright.json`; the caveat is "the rule stack has no M-1 schedule". The open item sends the *architect* to "read the yard clauses in the M-1 schedule". On DEOD the outright and funder-ready candidates wrote **identical** option files (`fc` reports no differences), and the printed label reads "funder-ready:" for the outright request.
Consequence: this is the purchase decision. "Not assessed" plus a drawn six-storey building reads to a manager as "probably fine". On land where homes are not a permitted use (my understanding of M-1, to be confirmed by a planner) the first answer should be "housing here needs a rezoning; talk to the City before you offer on the land".
Want instead: read the district's class (the lookup already has "Industrial") and say so in words; give no "outright" candidate where the stack has no schedule; address the open item to the manager and a City planner, not to an inbox folder.

### P2

**P2-1. The capital cost lands near the public figure for the wrong reasons.**
Evidence: `as-built/memo.md` lines 49 to 55: $4,693/m² is "average of Quadplex 01, Quadplex 02 and Townhouse", applied to 9,480 m² of 11-storey concrete with four floors of drop-in, dining and commercial kitchen; soft costs and contingency are placeholders; land $0. Result $61.9M against $65M (public, 2021) and about $74M of announced sources (public, 2023, land included). The floor area is my guess.
Consequence: I would be tempted to trust it because it is close. The community floors are costed as apartments and earn nothing; there is no fit-out, no temporary relocation of services during construction (public record: services moved to satellite sites, BCBusiness), no underground parking line.
Want instead: a separate cost rate and a separate funding line for non-residential floors, a concrete high-rise rate above six storeys, and a decant/relocation line for an operating service.

**P2-2. Rent-geared-to-income revenue is overstated for this population.**
Evidence: line 57: $1,146,364 a year over 89 homes, about $1,073 a month each, from "30% of a household income taken at 50% of the fund's income limit (placeholder)", a Community Housing Fund limit, on a project that is not in that fund. Supportive and single-adult tenants on income assistance pay about the $500 shelter rate (my understanding).
Consequence: the $6.1M "supportable debt" is not real, and the operating picture (support staffing for 35 supportive homes, the operating subsidy) is missing. Net income after a $6,500 placeholder operating cost says nothing about supportive housing.
Want instead: an RGI income I can set, a supportive-housing operating line, and "operating subsidy: who pays" as an open item.

**P2-3. The partnership has no place in the tool.**
Evidence: the option has one `proponent`, one `proponent_type`, one `owner_type_at_completion`; `developer_partner` means a BC Builds builder. No field for the housing operator, for who holds the homes (lease, air-space parcel, or ownership), or for the land owner as a third party to the funder. `land_tenure_plan` is free text: `ffm/checks.py` lines 581 to 583 pass anything that is not empty and does not contain the word "confirm". My sentence "How the housing floors are held by or leased to the operator is not public" passed.
Consequence: the single hardest set of agreements in a project like this (land owner, operator, funder, and the funder's security on the land) produces no open item, and a text box decides a funder criterion by a keyword.
Want instead: owner of land, owner of the homes at completion, operator, and the instrument between them as separate answers; open items "operating agreement" and "lease or air-space parcel" naming the two boards and the funder's lawyer.

**P2-4. Open items: three of the ones I would chase, and seven I would not, with the wrong people.**
Evidence: `as-built/memo.md` lines 26 to 35. Right: heritage, what stays on the lot, owner at completion and agreement term. Not useful here: 8 trees and an arborist on a lot-line-to-lot-line downtown site; the transit map; "save the DEOD schedule into inbox/ … or read it with Claude at stop 3" (software housekeeping addressed to an architect). Missing: the City's social-housing requirement for the district, the Development Permit Board itself, the operator agreement, the operating and support funding, relocation of services, the capital campaign, the Indigenous housing partner's own approvals. Nobody is named beyond "Manager" and "Architect": no City planner, no BC Housing development manager, no AHMA, no board.
Want instead: who at which organisation, and the first document to ask them for.

**P2-5. The Downtown Eastside Plan shows up as one number, typed by hand.**
Evidence: `area_plan` is not set by the lookup and has no input in the page (the project's own notes say so); a manager would never set it, and then the city-wide 35% + 5% rule applies in the Downtown Eastside. Once set, only the 25% family target appears. The plan's social-housing shares by sub-area do not appear in any memo I produced (the rule list has no DEOD or social-housing-share rule).
Consequence: the area plan's central housing rule for our district is absent, and its secondary one fails our project.
Want instead: the lookup sets the area plan from the address; the district's social-housing share is a rule; the family target is a pass/target/"discuss" by housing type.

**P2-6. The lookup's own answer breaks the run.**
Evidence, verbatim: "massing skipped: No road named 'Campbell Ave' adjoins the lot. The roads that adjoin it are: E Hastings St." The lookup wrote `front_face: {"street": "Campbell Ave"}` into `sites/877-e-hastings-st.lookup.json` itself; I did not touch it. Result: `runs/877-e-hastings-st/*` have no massing, layout or drawings, and the memo does not say why.
Want instead: do not write a front street the massing cannot find; if drawings are skipped, say so in the memo.

**P2-7. Contradictions between the summary line, section 2 and section 3.**
Evidence: `as-built-public-money-no-chf`: the command line prints "funders: yes"; memo line 19 says "No program the option targets has criteria the rules test"; line 33 lists "BC Builds … Fail" and CHF "Fail" as open items for programs the option does not target. On 877 the option targets only CHF, yet BC Builds appears as an open item.
Want instead: one list of programs in view, used by all three.

**P2-8. The memo is not board-ready as written.**
Evidence: `as-built/memo.md` is 98 KB and 272 lines; 64 ledger rows read "Not applicable. Written for C-2 districts; this site is zoned DEOD", each with a paragraph of another district's by-law. Eleven lines of egress ("4 exits, 2 required · separation 36.5 m") sit between the money and the ledger. Section 1 prints my free-text approval route inside the verdict: "By rezoning (none: development permit DP-2020-00721 …): no." Words a board will not have: HILs, RGI, DCR, "plate", "Schedule C", rule ids in backticks. "Gap $-36,083,109 (-58% of the capital cost)".
Consequence: pages one and two (the four answers and the open items) are close to board language; the file as a whole is not something I can forward. The UI's PDF may solve this (the project notes say it drops rules that do not apply); I did not see it.
Want instead: `memo.md` with the same two-page front and the not-applicable rules counted in one line.

### P3

- **P3-1.** "58 of 103 units placed … Studio × 45 did not fit" (line 101) is presented with the same weight as a rule. It rests on BC Housing minimum + 10% unit sizes and my floor-area guess; the building holds 103. It should say "at these unit sizes".
- **P3-2.** The site file is named after the parcel (`438-gore-ave`), not what I typed; I renamed it.
- **P3-3.** "Schedule C requires 8 trees" and `replacement_trees_proposed: 8` are suggested on lots with no trees recorded and full site coverage.
- **P3-4.** The social-housing exemption note says "the existing church use is also DCL-exempt" only if the word "church" is in the owner field (`ffm/checks.py` line 520); it fired here because of the society's name, by luck.
- **P3-5.** "Outright, under DEOD: not assessed. Not assessed: the rules have no DEOD schedule" repeats itself in one line.
- **P3-6.** Web sources: vancouver.ca (news page), dailyhive.com and connectcre.ca returned 403, shapeyourcity.ca/320-e-hastings-st 404; not retried; vancouver.ca PDFs not attempted. That is why floor area, FSR and height are my assumptions.

## Crashes and confusing messages, verbatim

- No crash: every command exited and wrote a memo.
- `massing skipped: No road named 'Campbell Ave' adjoins the lot. The roads that adjoin it are: E Hastings St.` (every run on 877 E Hastings; caused by the lookup's own `front_face`).
- `You typed 320; the City's address list has no such number on this street, and the nearest parcel is 438 Gore Ave. Use it only if that is the site.`
- `suggest --candidate outright` prints `funder-ready: 6 storeys, 19.8 m, …`.
- `allowed outright: not assessed · by rezoning: no · funders: yes · money: likely` for an option whose memo says no program was tested.
- `Architect: save the DEOD schedule into inbox/ and have its FSR, height and yards entered as rules (or read it with Claude at stop 3 and confirm its clauses).`

## Had I had this tool at the start

**Saved:** a day finding the parcel, its area and its district; an early, dated list that put heritage, "what stays on the lot", owner at completion and the agreement term in front of me; the habit of seeing every money line with its source, and a clear statement that a fund's intake is closed.

**Misled:** it would have told me the scheme was not allowed "by rezoning" when no rezoning was needed and the constraint was the DEOD plan it does not know; that the project did not fit "the funders" when the funds that fit were not in it; that I needed 25% family homes in a building of studios and one-bedrooms for single adults; that $17.6M was coming from a closed fund; that income-geared tenants would pay over $1,000 a month; and it would have said nothing about the operator agreement, the operating subsidy, the community floors' own money or moving the services out during construction. On the next site it would have drawn six storeys of homes on industrial land before telling me to ask whether homes are allowed there.

**Net:** as it stands I would use page one as a checklist of questions, not as answers, and I would not show the board the verdicts for a Downtown Eastside, Indigenous-led, mixed services-and-housing project.

## Three quotable lines

- "It found our lot under an address I did not know we had, and then told me the building we built was not allowed."
- "The funders it knows are not the funders who paid for this; for deep-subsidy Indigenous housing, question two is asking about the wrong cheque books."
- "'Not assessed' is honest. A six-storey suggestion drawn on top of 'not assessed' is not."

## Files

- Sites: `sites/320-e-hastings-st.lookup.json` (as found), `sites/320-e-hastings-st.json`, `sites/877-e-hastings-st.lookup.json`, `sites/877-e-hastings-st.json`
- Options: `options/320-e-hastings-st-as-built.json`, `-as-built-public-money.json`, `-as-built-public-money-no-chf.json`, `-suggest-{outright,benchmark,funder-ready}.json`; `options/877-e-hastings-st-intended-hypothetical.json`, `-suggest-{outright,funder-ready}.json`
- Runs: `runs/320-e-hastings-st/{as-built, as-built-public-money, as-built-public-money-no-chf, suggested-funder-ready}/`, `runs/877-e-hastings-st/{intended-hypothetical, suggested-funder-ready}/`
- Nothing outside this folder was created or edited.
