# First Read, reviewed from the operator's seat (AI role-play, 24 Nov 2026)

*A simulated review by an AI playing the director of operations and asset management at a mid-size BC non-profit. It is
not a practitioner's view and must not be quoted as one. Where it gives "typical" operating figures, they are the
role-play's assumptions. The reviewer's own run files were kept in a scratch folder outside the repository.*

## 1. Cases run

Every command used `--as-of 2026-11-24`.

| Case | What the tool said |
|---|---|
| A. 998 E 19th, funder-ready, as committed | Market tier $2,072 a home a month, RGI $1,126, deep $578. Operating cost $6,500 a home (placeholder), reserve $600 (placeholder), vacancy 3.7%. NOI $690,640. Subsidy to run: $0. Gap $20.8M (45%), "Needs more sources". |
| B. Same building with the operator's own figures (market $1,750, RGI $820, deep $520, operating $9,200 a home, staffing $85k) | NOI fell to $103,503 and supportable debt from $9.28M to $1.39M; the gap went from 45% to 63%. The table still says "Subsidy needed to run it: $0, the rents cover the running costs". |
| C. A supportive building: 60 studios, 24/7 staffing | Funders "not assessed", four supportive programs listed. NOI -$1,427,320. The $1.35M subsidy entered is unconfirmed, so it reads $77,320 short. Subsidy to run: $1,982 a home a month. Gap $23.5M (100%). "If the capital still missing were borrowed": $4,191 a home a month. |
| D. Case C with no operating figures | Subsidy needed to run it: **$110 a home a month**. Staffing is marked "not entered". |
| E. Case C with a confirmed 3-year subsidy of $1.5M and $23M of other grants | **"Likely."** A 40-year mortgage of $977,091 is sized on the subsidy. |
| F. 375 Glen Drive as proposed (163 homes, 25 supportive homes, an 80-bed shelter) | Read as `housing_type: independent`. No staffing flagged, NOI +$1,648,072, subsidy to run $0. The shelter program and the bed-space rule both read "Not for this option: … independent rental". |

## 2. The real workflow against the tool

| Step | Tool |
|---|---|
| 1. "Can you operate this?": who is housed, which program, which operating model | **Partly.** Stop 02 asks the kind of housing and the operator's name; answer 2 lists programs. The operator is a text field; nobody asks the operator anything. |
| 2. Check the unit mix against the waitlist and tenant profile | **Missing.** The mix comes from rules; no input for waitlist demand or the bedroom split by tier. |
| 3. Is the building operable: staff office, 24/7 desk, laundry, storage, garbage, lifts, accessible homes | **Missing or partly.** One core with one elevator, "services" (40 m² plus bicycles), amenity at 1.5 m² a home. No staff room, desk, laundry, tenant storage or program space. Accessible count tested; number of lifts not. |
| 4. Build the operating budget | **Partly.** Six inputs, one average rent per tier, opex as one number. Reserve and vacancy cannot be edited. |
| 5. Test the budget against debt service and the program's subsidy terms | **Partly.** Debt sized to 1.10 coverage at the posted 6.19%, BC Builds terms only. No subsidy term, no program operating funding for the deep tier, no stress test. |
| 6. Long-term view: reserve adequacy, cost vs rent growth, mortgage renewal, agreement end | **Missing.** One stabilised year only. |
| 7. A board paper on operator risk; sign the operating agreement | **Missing.** Open items name only the Manager or the Architect; issuing goes to the architect or the manager; no operator role. |

## 3. What is not working

### Real defects

1. **A short-term operating subsidy is capitalised into a 40-year mortgage, and the verdict turns "Likely"** (case E).
   `proforma.py` adds a confirmed subsidy to NOI before sizing debt, and there is no term field. The memo prints "Likely"
   beside "Net operating income -$1,427,320 a year" and "operating agreement, 3 years; confirmed". No lender would
   borrow for 40 years against a 3-to-5-year renewable agreement. The most dangerous output found.
2. **A mixed-program building is read as independent rental, so it shows no operating need** (case F). `housing_kind`
   treats an option as supportive only when every home is. Glen Drive (25 supportive homes, an 80-bed shelter) reads
   NOI +$1.65M and "Subsidy needed to run it: $0".
3. **"$110 a home a month" is printed in bold as the subsidy a supportive building needs when staffing is blank**
   (case D), beside a footnote saying a funder compares exactly that figure.
4. **Boilerplate that contradicts the inputs.** With every figure entered, the memo still says "Until they are entered,
   the rents and the running cost are placeholders" and "The rents and the running cost are placeholders until the
   operator's own are entered"; the reserve is listed as a placeholder and cannot be entered.
5. **Help text describes formulas the engine no longer uses.** `route-stage.js` and `fields.js` say a blank RGI rent is
   "30% of half the fund's income limit" (the engine uses 30% of 70% of the Housing Income Limits) and a blank deep rent
   is "$500" (the engine uses $500 / $695 / $769 by bedrooms); `fields.js` quotes the 2025 CHF limits ($85,870 /
   $138,770) where the rule in force has $90,560 / $146,270.
6. **Reserve and vacancy are fixed.** No override for the $600 reserve; vacancy is the CMHC market 3.7% applied to RGI
   and shelter-rate homes too, with no bad-debt line.
7. **The whole-capital-gap borrowing illustration** ($4,191 a home a month in case C) is shown for supportive housing,
   whose capital the same memo says the Province pays.
8. **Capital-side numbers that land on the operator:** no program operating funding line for the CHF deep tier (the
   reviewer's understanding, to verify); CHF debt at market terms; 1,100 m² of non-residential space with no running
   cost unless an income is entered; rents counted on 88 homes when 59 fit the plates.

### Flow problems

1. **The operator is not in the flow.** `docs/user-flows.md` has three readers, none of whom runs the building. The
   operating figures sit in a fold at stop 03, entered by the manager just before Run. Nothing asks the operator,
   issues to them, or records that they supplied the figures. `subsidy_source` is not in that fold at all.
2. **Open items never name the operator.** In case C the unconfirmed $1.35M subsidy, the project's biggest risk, does
   not appear in answer 3; only inside the money paragraph.
3. **Operating risk is framed as a capital-gap problem.** The next step for a supportive building is addressed to the
   development manager and driven by a 100% capital gap the memo says the Province would cover.

## 4. What should change, ranked

1. **Give the subsidy a term; stop sizing debt beyond it** (S). Benefits: board, lender, operator.
2. **Model mixed programs** (M): homes and beds in components (independent, supportive, shelter beds), each with its own
   kind, rents, staffing and program checks, and a combined operating page.
3. **Withhold or warn on the subsidy figure when staffing is missing** (S).
4. **Fix the stale copy and the placeholder boilerplate** (S): notes conditional on what was entered.
5. **Make reserve, vacancy and bad debt, property tax status and other income editable** (S).
6. **Add an operator flow** (M–L), at stop 02, when the mix and the kind of housing are set:
   (a) the manager issues an "operating request" to a named operator, with the mix, tiers, kind of housing and the
   layout's operability items; (b) an Operator mode showing only the operating page and the building items; (c) the
   operator marks the figures issued, signed and dated, and the memo says whose they are or that no operator has seen
   them; (d) an "Operator" lane in the open items: subsidy unconfirmed, agreement term, staffing model, reserve study.
7. **Operability rules in the layout** (M): staff office and desk for supportive housing, laundry, tenant storage,
   garbage room by homes, lifts by home count.
8. **A stress line and a 60-year view** (M): opex +10%, RGI rent -10%, a vacancy shock; cost vs rent growth; reserve
   balance; mortgage renewal against the agreement's end.
9. **Program operating terms** for the CHF deep tier and the Supportive Housing Fund operator agreement, read from BC
   Housing's documents (M).

## 5. What would make the reviewer distrust it

- The "Likely" in case E: one verdict like that on a 3-year agreement would end the tool's use with a board.
- Glen Drive's $0 subsidy for a building with a shelter in it.
- Help text that contradicts the engine.

What is earned: every line names its source; staffing is never assumed for supportive housing; an unconfirmed subsidy
visibly holds the verdict back; answer 2 is honest that programs are listed, not tested; the operating table is the
right shape for a first read and needs an operator to fill and sign it.
