# Simulated reader test (role-play by an AI reviewer), not BC Housing's position

## Who I am and how such a memo reaches me

I am playing a development manager on the funder's side: the person who receives a society's early proposal, screens it against the program frameworks, and decides whether it earns a next conversation.
I did not use the tool. A proponent has emailed me the memo, probably with "we ran our site through First Read and it says we fit".
I give a document like this about five minutes on page one, and I am reading for three things: which program, who operates, and what the proponent is asking of us.

Everything below about BC Housing programs is from my general understanding or from public pages, and is marked "my understanding, to verify" where I could not confirm it. Nothing here speaks for BC Housing. I did not read the other reviewers' reports.

## Verdict per memo

| # | Memo | Verdict | One-line why |
|---|---|---|---|
| 1 | `outputs/998-e-19th-ave/what-if-funder-ready/memo.md` | **File** (as a site and zoning note), **bounce** as a funding case | Clean and honest about its sources, but "Meets the criteria" rests on a hypothetical resolution, the building holds 57 of the 88 homes the grant is counted on, and the gap is computed without an operating subsidy. |
| 2 | `docs/user-tests-2026-11-23/manager-first-united/runs/320-e-hastings-st/as-built/memo.md` | **Bounce** | An Indigenous-led deep-subsidy and supportive project tested against CHF and BC Builds only; says "does not meet", "by rezoning: no", and 58 of 103 homes placed, for a building that was approved, funded and built. |
| 3 | `docs/user-tests-2026-11-23/manager-covenant-house/runs/4250-fraser-st/youth-transitional/memo.md` | **Bounce** | Transitional youth housing is not a CHF or BC Builds product; the memo fails it on both, then counts $5.8M of CHF grant anyway; exits fail on all six floors but page one does not say so. |
| 4 | `docs/user-tests-2026-11-23/manager-covenant-house/runs/1280-seymour-st/as-built/memo.md` | **Bounce** | A shelter modelled as rental housing; "Likely" with negative net operating income is the single most misleading line in the five memos. |
| 5 | `docs/user-tests-2026-11-23/ui-walk/run-320-e-hastings/memo.md` | **Read, then send back** | The most honest funders answer ("not yet confirmed") and the best open-items table, but "Proponent: None", an "indicative grant … would be $17,634,733" in the open items, and no word on who lives there or who operates. |

## What I trust

- **The dating and the sourcing.** Every figure names its rule and its document, and the rule file admits what it could not fetch. I rarely get that from a proponent.
- **The intake status line.** "The Community Housing Fund's 2025 call was cancelled in February 2026, so no intake is open now" is on page one of every memo. A web search confirms the substance: Budget 2026 (17 Feb) ended the 2025 call and applications were not advanced.
- **The open-items table.** Named person, named document. This is the part I would actually use in a first call.
- **The declared placeholders.** "Placeholders in use: Soft costs, Contingency, Rent-geared-to-income, Operating cost, Replacement reserve" is said up front, and the 15% line is labelled "this tool's screening line, not a funder's rule".
- **"Not assessed"** where the stack has no schedule (DEOD, CD-1 (701)), instead of a guessed yes.
- **Zoning and City policy arithmetic.** Not my file, but it is the piece I would rely on a proponent having done.

What I do not trust: the funders verdict as a verdict, and any dollar figure below the capital cost line.

## Findings

### P1

**P1-1. The pro-forma omits the operating subsidy, so the "gap" is not a number I recognise.**
- Evidence: all five memos, section 4. Funding is "grants + equity + supportable debt", with debt sized as "the largest loan the net operating income carries" at 6.19% and a 1.10 coverage ratio (`f.mortgage`). The showcase reads "Gap $20,228,128 (44% of the capital cost)".
- Why it matters: my understanding, to verify, is that a CHF project is carried by a capital grant, repayable financing arranged through BC Housing, and an annual operating subsidy that covers the difference between tenant rents and operating cost plus debt service. Debt is not limited to what tenant rent alone supports. A proponent reading 44% will conclude the project is hopeless or go looking for $20M of equity that the program does not expect.
- What I want instead: two tables. A capital budget with sources and uses (grant, financing, equity, other contributions). An operating budget (rents by tier, operating cost, debt service) ending in "annual operating subsidy required, per unit per month". That last figure is what I compare across submissions. Label the current gap "shortfall if no operating subsidy were available".

**P1-2. A CHF grant is counted on projects the same memo says fail CHF.**
- Evidence: Hastings as built, line 21 "does not meet the criteria" and line 63 "Community Housing Fund grant $17,634,733"; Fraser, line 15 fail and line 55 "$5,821,174"; Seymour, line 22 fail and line 62 "$6,848,440".
- Why it matters: the money answer contradicts the funders answer on the same page. On Seymour the phantom grant is part of why the verdict reads "Likely".
- What I want instead: grant $0 when the program check fails or is not confirmed, with a line "no program grant counted: the scheme does not meet the fund's screen". Where the check is uncertain (memo 5), show the stack with and without it.

**P1-3. Seymour: "Likely" with negative net operating income.**
- Evidence: Seymour lines 39–44. "**Likely.** The funding stack covers the capital cost with $12,639,932 to spare", next to "Net operating income **$-52,880 a year**" and "supportable debt $0".
- Why it matters: a building that loses money every year before any staffing cost is not likely by any reading. A 40-bed youth shelter does not charge $500 rent, is not 3.7% vacant, and does not operate on $6,500 a unit a year; my understanding is that 24/7 staffed shelter and supportive operations cost several times that and are funded by an operating agreement, not rent.
- What I want instead: a negative NOI forces the verdict to "does not carry itself: an operating funder is required" regardless of the capital stack. For shelter or supportive tenure, replace the rent model with "operating funding required: $X a year, source not identified".

**P1-4. The wrong programs are tested, and the headline does not say so.**
- Evidence: `rules/e_funding_programs.json` holds four rules: CHF, BC Builds, the Project Development Fund and CMHC's Affordable Housing Fund. Hastings as built (operated by an Indigenous housing society, 35 supportive homes), Fraser (youth transitional) and Seymour (shelter) all read "**Does not meet the criteria of BC Builds and the Community Housing Fund**" with the action "Manager: resolve the failing criteria or target another program".
- Why it matters: the answer to "Does it fit the funders?" is "you asked the wrong two". The real Hastings project was publicly funded. A board reading this memo would conclude it was unfundable.
- What I want instead: lead with the target population and tenure, then name the program family it points to. "This is supportive / Indigenous-led / shelter housing. The tool does not hold the Indigenous Housing Fund, the Supportive Housing Fund or shelter program criteria; CHF and BC Builds are not the relevant test." Status "not assessed", not "fail". `PRODUCT.md` promises CHF and BC Builds only, so the memo should state that limit on page one.

**P1-5. "Meets the criteria of BC Builds and the Community Housing Fund" claims far more than was tested.**
- Evidence: showcase line 15. The CHF pass rests on three things: mix within tolerance, site control, construction start. The BC Builds pass states only "non-residential space is 15.7% of area, under the 30% cap" and the ground-breaking window.
- Why it matters:
  - Eligibility in a call is the floor. The rule file itself carries rated criteria (`rated_weights` 60/40, `rated_thresholds`), none of which the memo mentions. A proponent will read "meets the criteria" as "would be competitive".
  - The two programs serve different households. The 2023 CHF fact sheet says no layering or cross-subsidy from other BC Housing programs is permitted. "Meets both" invites a proponent to plan a stack that is not available.
  - The BC Builds pass on a 30/50/20 scheme says nothing about middle-income rents or the proponent's developer partner.
  - The site control is "council resolution", while the option notes at line 253 say "the tenure resolution does not exist". That caveat is 240 lines from the verdict.
- What I want instead: "Passes this tool's screen of 3 published CHF eligibility items (mix, site control, start date). Not assessed: need and demand, operator capacity, the rated criteria, budget reasonableness. No intake is open." One program per line, never joined by "and". Any hypothetical input repeated beside the verdict it produces.

**P1-6. The grant and rent are counted on homes the tool's own plan cannot place.**
- Evidence: showcase line 70 "57 of 88 units placed"; line 51 "$171,211 per unit × 88". Memo 5: "86 of 103 units placed", grant × 103. Fraser: 21 of 34.
- Why it matters: page one says the scheme meets the funder and is allowed by rezoning; page three says a third of it does not fit the building. I would ask which is the proposal.
- What I want instead: an open item on page one, "31 of 88 homes do not fit the plates at the areas assumed", and the money run on both counts, or the option refused until they agree.

### P2

**P2-1. Design Guidelines: wrong edition, wrong reading of the areas.**
- Evidence: `bch.design_guidelines.unit_areas` cites "2019 edition; copy" hosted on a third-party site, with the note that the current edition "could not be fetched". The layout uses "53.9 m² net (49 m² minimum + 10%), 58.2 m² gross with partitions".
- Why it matters: my understanding, to verify, is that the guideline unit areas are targets a funder holds projects close to, because floor area is cost; a proponent who designs to "minimum + 10%" is proposing homes larger than the standard and paying for it. A search result reports a municipality adopting "BC Housing's 2026 guidelines" for unit sizes, which suggests a newer edition exists. The Hastings result is the proof: the tool places 58 of 103 homes in a building that holds 103.
- What I want instead: cite the current edition from bchousing.org, read by a person. Lay out at the target area with no uplift, and state the uplift as the architect's choice. Use the `wheelchair_unit_uplift` the rule already carries for the accessible homes; the layout draws them at standard size.

**P2-2. Accessibility is one number.**
- Evidence: `min_accessible_unit_share: 0.05`; the layout note "5 accessible units on level 2".
- Why it matters: my understanding, to verify, is that BC Building Code 2024 adaptable-dwelling requirements now apply to most new apartment homes, and the current Design Guidelines may ask for more than 5% accessible. A memo silent on adaptable homes misses area and cost.
- What I want instead: two lines, accessible share and adaptable share, each with edition and clause, or "not checked".

**P2-3. Rent definitions are looser than the program's.**
- Evidence: `f.rents`: RGI "at 30% of a household income taken, as a placeholder, at half the Community Housing Fund's low-to-moderate income limit"; the 30% tier labelled "market" and priced at the CMHC average; "Deep-subsidy rent … the shelter rate, $500 a month" for every unit size.
- Why it matters: per the 2023 CHF fact sheet, RGI rent follows BC Housing's RGI rent scale and the deep-subsidy tier is defined by Deep Subsidy Income Limits. My understanding is that RGI households sit under the Housing Income Limits, not under the low-and-moderate limit, so the placeholder income is too high. In the showcase it gives about $1,314 a home a month for RGI ($693,702 over 44 homes), well above what I would expect. The shelter rate rises with household size. The memo never names the Housing Income Limits as a CHF test at all; they appear only in the City's social housing definition.
- What I want instead: the tier called "affordable market (households under the low-and-moderate income limit)"; RGI priced from the HILs for the unit size with the rent scale cited; deep subsidy by household size; each still marked placeholder.

**P2-4. Hard cost basis I would reject on sight.**
- Evidence: `f.hard_cost_base`: "$4,693 per m² … average of Quadplex 01, Quadplex 02 and Townhouse", applied to an 11-storey Downtown Eastside building and a 10-storey tower. The rule's own verify note says a six-storey apartment "sits outside" the catalogue.
- Why it matters: three-storey wood-frame quadplex costs are not evidence for concrete or mass-timber high-rise with four floors of community space. Below-grade parking is listed as "not on the plates" and I see no cost for it. All-in the showcase comes to about $519,000 a home and about $6,500 per m², which is not absurd for six-storey wood frame, but the high-rise figures ($601,000 and $704,000 a home) are unsupported, in either direction.
- What I want instead: a cost basis by construction type, or a refusal above six storeys ("no cost basis for this building type; capital cost not estimated"). Parking, demolition and off-site works as explicit lines, even at "not estimated".

**P2-5. Debt terms are a market lender's, not the program's.**
- Evidence: `f.mortgage`: posted conventional 5-year rate 6.19%, 40-year amortization, MLI Select 1.10 coverage.
- Why it matters: my understanding, to verify, is that take-out financing for these projects is arranged at lending rates well below the posted conventional rate and on program terms. The memo's own note calls 6.19% "the conservative ceiling", but the headline gap is computed at it.
- What I want instead: show debt at the ceiling and at an insured rate side by side, and say which the gap uses.

**P2-6. Program facts presented with more certainty than their sources.**
- `provisional_grant_per_unit_cad_2025_26: 171211` comes from webinar slides for a call that did not proceed. The memo's "indicative, the fund is between calls" is fair in the line table, but memo 5's open item ("the indicative grant at 2025-26 rates would be $17,634,733 for 103 units") reads as an expectation. My understanding is that grant levels have differed by unit size or region in past calls; a flat figure times units is a simplification.
- `mix_tolerance: 0.02` has no source I can see. It looks like the tool's own rounding rule and should be labelled so, like the 15% line.
- "site control (council resolution) meets the readiness bar": I would want the RFP's own wording before accepting a resolution or a letter of intent as site control.
- `min_lease_years_nominal: 60`: the 60-year term never appears on page one. My understanding is that it attaches to the operating agreement and the security on title as well as to any lease, which matters on church land.
- `bc.bcbuilds.eligibility` is dated 2024-02-13 but carries income limits ($143,900 / $212,240) that differ from the 2024 launch figures I found ($131,950 / $191,910). Either the date or the figures need a second version.
- "a non-profit must team with a developer or builder to propose" is stated as an absolute fail (Fraser line 14, Seymour line 21). 2024 material lists non-profits among eligible applicants and ties the 20%-at-20%-below-market requirement to projects with non-profit and First Nations partners. I would word it "the proposing team must show development and construction capacity".
- BC Builds works opportunity by opportunity, largely on public land. Memo 5's open item says so; the showcase "Pass" does not.
- `bch.pdf.predevelopment_loan` is sourced to a UBCM resolution response, not a BC Housing document, and the memo prints only "maximum loan: $250,000". It does not say it is a repayable loan, on what terms, or how a society comes to be offered one. I could not confirm any of it.

**P2-7. "Cancelled" is contested wording.**
- Evidence: every memo, "was cancelled in February 2026".
- Why it matters: public reporting says applicants were told the 2025 RFP "will not proceed" and applications "will not be advanced", while the Ministry disputed that the program was cancelled and said future cycles would come.
- What I want instead: "The 2025 call did not proceed (Budget 2026, February 2026); the program remains but no intake is open or scheduled." Also note that sector reporting refers to deferrals on the Indigenous Housing Fund; the memo should not imply that only CHF is affected.

### P3

- **Vacancy 3.7% on RGI and deep-subsidy homes** (`f.rents`). A market survey rate applied to non-market tiers with waiting lists; minor, but I would query it.
- **"By rezoning: no" on built projects** (Hastings line 12, Seymour line 12). The Hastings building went through a development permit; the City's family-unit rule is applied to supportive and shelter schemes. As-built runs should carry a banner: "calibration run against a completed project; fails here are limits of the rule set".
- **"Proponent: None (non profit society)"** (memo 5, line 4). A memo with no proponent should not issue.
- **Fraser egress** fails on all six floors (line 98) and is absent from the open items table.
- **Machine text in the reading path**: rule ids in backticks, `sprinklered: false`, "stop 3", "inbox/", "read it with Claude". Fine for the architect; not for me.
- **Length**: the ledger prints about fifty "Not applicable" zoning rows for other districts. `CLAUDE.md` says the page and the PDF now fold these; the `memo.md` I was sent does not.
- **"Does the money work? (feasibility grade)"**: "grade" is unclear. "Order of magnitude" is the term I know.

## What is missing that I always ask at first contact

None of the five memos carries these, and the tool has no input for most:

1. **Need and demand**: who is on the waiting list, the local housing needs report, why this population on this site.
2. **Target population and tenure** stated in words (families, seniors, youth, people leaving homelessness), before any unit mix.
3. **Operator**: who operates, their portfolio, their experience with this population, their financial standing. Only Hastings names one, in the option title.
4. **Support services and operating funding**: who pays for staffing, under what agreement. Decisive for memos 2, 3 and 4.
5. **Municipal support**: any Council or staff position, fee or levy waivers, the City's own contribution.
6. **Indigenous partnership or ownership**, and whether the Indigenous Housing Fund is the better door.
7. **Readiness and schedule**: rezoning status, time to permit, a construction start date. The tool knows the 18-month requirement but never tests a date.
8. **Proponent's equity and other contributions**: land value contributed, cash, CMHC, the City. The showcase carries land at $0 without recording it as the church's contribution, which is the proponent's strongest card.
9. **Energy and carbon**: Step Code level and the funder's energy standard. Nothing in layers D or E.
10. **Who the development consultant and architect are**, and the ask: a pre-development loan, a place in the next call, or a conversation.

## Tone, form, and anything that reads as BC Housing's position

The disclaimer on line 7 ("not legal, planning or funding advice") is right and well placed. The phrases I would want reworded so nobody can quote them as a funder's view:

| Memo wording | Reword to |
|---|---|
| "Does it fit the funders?" | "Does it pass this tool's screen of published program criteria?" |
| "Meets the criteria of BC Builds and the Community Housing Fund." | "Passes the 3 CHF eligibility items this tool checks. Not a funding assessment." |
| "meets the readiness bar" | "is one of the forms of site control the tool reads the 2025 RFP as listing" |
| "Community Housing Fund grant $15,066,568" | "Illustrative grant at the 2025-26 provisional rate, from a call that did not proceed; no grant is committed or implied" |
| "the indicative grant at 2025-26 rates would be $17,634,733" | remove from the open items table |
| "BC Housing minimum net unit areas" | "BC Housing Design Guidelines target unit areas (edition, date)" |
| Section title "Layouts derived from the option", citing `bch.design_guidelines.unit_areas` as the source of each block | add "areas include a 10% allowance chosen by this tool, not by BC Housing" |

The repo name ("BC Housing Feasibility Study") and the subtitle "a funding-fit memo" both sit close to implying an association. A line on page one, "independent student tool; not affiliated with or reviewed by BC Housing, the Province or CMHC", would settle it.

## Program facts to verify

| Fact in the rule file or memo | What I checked | Result |
|---|---|---|
| CHF 2025 call cancelled February 2026 | Web search: sector press, UBCM, CHF BC, BCNPHA, news.gov.bc.ca | **Confirmed in substance.** Budget 17 Feb 2026; applicants told the RFP "will not proceed". Government disputes the word "cancelled". Sources differ on whether the intake opened in May or July 2025. |
| CHF mix 30 / 50 / 20 | Web search: 2023 CHF RFP fact sheet, 2025 provincial release | **Confirmed**: 30% affordable market, 50% RGI, 20% deep subsidy. |
| Mix tolerance ±2% | Rule file only | **No source found.** Treat as the tool's own. |
| Low-and-moderate income limits $85,870 / $138,770 (1 Mar 2025) | Web search | **Not confirmed.** A 2024 release gives $84,780 / $134,140; the 2025 figures are plausible successors. Limits may vary by community. |
| Provisional grant $171,211 per unit | Web search | **Not confirmed** by any BC Housing page. A third-party listing shows "$171,211 – $178,059" without saying per unit, which hints at more than one rate. |
| RGI and deep subsidy definitions | 2023 fact sheet via search | RGI by the RGI rent scale; deep subsidy by Deep Subsidy Income Limits; tenants from the Housing Registry. The tool's placeholders differ. |
| No stacking of CHF with other BC Housing programs | 2023 fact sheet via search | Fact sheet says no layering or cross-subsidy. **Verify for any future call.** |
| Accessible share 5%; 60-year term; site control forms; 18-month start | Not checked against the RFP | **To verify** against the RFP text, not the webinar slides. |
| BC Builds 20% of homes at 20% below market | Web search: 2024 releases and summaries | **Confirmed** for projects with non-profit and First Nations partners receiving grants. |
| BC Builds income limits $143,900 / $212,240 | Web search | **Not confirmed.** 2024 figures were $131,950 / $191,910. |
| BC Builds: non-profit must team with a developer | Web search | **Not confirmed as an absolute.** Non-profits are listed as eligible applicants in 2024 material. |
| Project Development Fund, loans to $250,000 | Web search | **Not confirmed.** No BC Housing page surfaced; the rule's source is a UBCM resolution response. |
| Design Guidelines unit areas 33 / 49 / 67 / 86 m² | Web search | **Not confirmed.** One result refers to "BC Housing's 2026 guidelines" for unit sizes, so the 2019 copy is likely superseded. |
| Indigenous Housing Fund, Supportive Housing Fund | Not in the rule file | **Missing.** |

I did not fetch bchousing.org pages directly.

## What page one should say to me

In this order, in half a page:

1. **Who and for whom**: proponent, operator, target population, number of homes by size, tenure.
2. **The site and its control**: address, owner, what the owner contributes, the form of site control in hand today (and "none" if none).
3. **Which program door, and its status**: one program named, why that one, "no intake open" if so, and which programs the tool does not hold.
4. **Planning status**: allowed outright or by which path, and the two or three approvals still needed, with dates.
5. **The numbers I compare**: total capital cost, cost per home and per m², capital contribution requested per home, annual operating subsidy required per home, proponent's equity and land. Each marked estimate or placeholder.
6. **What is not known**: the open items, each with a name.
7. **The ask**: what the proponent wants from this conversation.
8. **One line**: "Independent screening tool. Not reviewed by, and not a position of, any funder."

The ledger, the layouts and the egress table belong in an appendix I may never open.

## Three quotable lines

- "The memo tells me how the zoning arithmetic works to four decimal places and does not tell me who will live in the building or who will run it."
- "A screen that says 'Likely' over a negative operating income, and 'does not meet the funders' over a building the Province helped pay for, has the right structure and the wrong model of how we fund."
- "The open-items table is the part I would keep: a named person and a named document for every unknown is more than most first submissions give me."

Sources:
- [Future of Good: sector response to rescinded provincial funding](https://futureofgood.co/six-figure-costs-and-stalled-projects-bcs-non-profit-housing-sector-expresses-sorrow-at-rescinded-provincial-funding/)
- [UBCM: Community Housing Fund closure leaves projects stranded](https://www.ubcm.ca/node/106168)
- [CHF BC: sector leaders on the CHF suspension and Indigenous Housing Fund deferrals](https://www.chf.bc.ca/housing-sector-leaders-call-on-province-to-change-course-on-community-housing-fund-suspension-and-indigenous-housing-fund-deferrals)
- [The Tyee: BC affordable homes budget cuts](https://thetyee.ca/News/2026/07/07/BC-Affordable-Homes-Budget-Cuts/)
- [Province of BC release 2024HOUS0006 (income ranges)](https://news.gov.bc.ca/releases/2024HOUS0006-000188)
- [Province of BC release 2024HOUS0021 (BC Builds launch)](https://news.gov.bc.ca/releases/2024HOUS0021-000648)
- [UBCM BC Builds overview presentation, Feb 2024](https://www.ubcm.ca/sites/default/files/2024-02/Lisa%20Helps_Tuesday_130pm_Salon%20ABC_BC%20Builds%20Overview%20Presentation%20February%2012%202024.pdf)
- [CHF RFP fact sheet, 2023](https://ulidigitalmarketing.blob.core.windows.net/ulidcnc/sites/20/2023/08/CHF-RFP-Fact-Sheet_FINAL.pdf)
- [Province of BC release 2025HMA0047](https://news.gov.bc.ca/releases/2025HMA0047-000517)
- [FIPA: Port Moody and BC Housing's minimum unit sizes](https://fipa.bc.ca/nm/port-moody-to-make-bc-housings-minimum-unit-sizes-mandatory-tightening-family-friendly-housing-rules/)

Files read: `PRODUCT.md`, `rules/e_funding_programs.json`, `rules/d_design_standards.json`, `rules/f_assumptions.json`, and the five memos named above (fronts in full; ledger layers D to F, inputs and sources of the showcase memo; ledgers of the other four not read).
