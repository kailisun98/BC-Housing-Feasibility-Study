# Operator review, 25 Nov 2026

An AI role-play of a non-profit's director of operations (supportive housing, a shelter, independent rental under BC Housing operating agreements). This is not a practitioner's review and must not be quoted or credited as one. I signed operating figures as "Test Operator" of "Example Housing Society": both names are invented. My own server ran on port 8794 in my own browser tab.

(Saved by the coordinating session from the reviewer's returned text: the harness does not let a subagent write files. Runs the reviewer made: `375-glen-drive/2026-11-25T18-24-15` (issued R4), `375-glen-drive/2026-11-25T18-26-13`, `998-e-19th-ave/2026-11-25T18-27-12`, `…18-27-55`, `…18-28-20` (issued R4), `…18-30-24`.)

## 1. Verdict

No, I would not sign operating figures in this next week. The operating table is a good start and its arithmetic holds: I recomputed every line on both sites. But what I sign does not survive. When I reopen my own signed, issued memo, the operator's desk is blank and says "not yet signed". The next Run again, by me or by the manager, silently replaces my rents, costs, staffing and subsidy with the screen's placeholders and drops my signature. On top of that, the model cannot describe the building I would run. Glen Drive gets one rent per tier, one operating cost, one staffing figure and one subsidy with one term across a shelter, 25 supportive homes and 138 independent homes. The 80 shelter beds carry no running cost or reserve at all. A loan entered as a capital source is counted as a grant with no repayment. Until the figures persist and each part of the building has its own budget, my name on this page would be on numbers I cannot defend.

## 2. The flow as I walked it

**Website (home, who, how).** The home page sells "four answers" to a board. The who page says "One memo, three kinds of reader" (development manager, architect, board/planner/funder) and describes "A switch in the tool's top bar, Manager, Architect or Reader". The operator is not there at all. The tool's top bar has an Operator pill, but no page says when the operator receives the memo, what they are asked to do, or that their signature appears on the paper. The "Who tests it" list names no operator session. The numbers also disagree: the home page says 84 rules in one place and 144 in another, the tool says "176 rules in force", and the who page says "OPEN ITEMS · 8" for a memo the home page says has "Seven open items".

**375 Glen Drive, as proposed, Operator mode.** The page first flashed 998 E 19th Ave while loading. Then the URL quietly gained `&compare=375-glen-drive/first-run`, and the banner read: "Opened R2, the memo as of 17 Nov 2026 · R2, rules as of 17 Nov 2026, against R1, rules as of 17 Nov 2026: 15 statuses differ, 3 new versions; 137 more … · Rules as of now reads 17 Nov 2026, this memo's date (it read 25 Nov 2026)". I could not tell what had happened. Further down, "What changed" contradicts itself: "rules as of 17 Nov 2026 against 17 Nov 2026 … R1 → R2 · the rule files changed; the difference is the site's inputs and the option's inputs".

My desk came first and was clear about intent: "What it takes to run this building … enter the building's own figures, sign them as yours, then Run again". I entered market $1,750, RGI $950 and deep $500 a month, operating $8,500 a home a year, staffing $3.7M a year, a subsidy of $3.9M a year for 5 years ("BC Housing: Supportive Housing Fund operator agreement and Emergency Shelter Program services agreement, 5-year terms, sought"), a reserve of $800 and vacancy of 0.02. I signed, then ran. The result:
- "Left after running costs −$2,753,356"
- "Subsidy needed to run it $2,753,356 · $1,408 a home a month over 163 homes; $2,868 a bed a month over 80 beds"
- "Loan payment $-0"
- the debt went from $22.2M to $0, and the gap from 77% to 100% ($96.2M)
- "Who operates: Not named; the operating figures are signed by Test Operator"

I issued it back with a note, and the manager's layout showed the note under the title. Then I reopened that R4 and ticked "The operating subsidy is confirmed". The desk was empty and said "not yet signed". Run again gave Draft 18:26 with CMHC rents, the $6,500 placeholder, no staffing, a $22.2M debt and a 77% gap. My figures were gone, with no warning (D1).

**998 E 19th Ave, what-if funder-ready, as independent rental.** To test the guard rails I typed vacancy "2" (an operator's natural way to say 2%) and signed. Nothing stopped me. The memo then read "Vacancy −$2,536,320 · the CMHC survey's rate, on all tiers" and "the building is $1,840,560 a year short" (D5, D6). I corrected it to 0.02. The desk still said "signed by Test Operator", so I ran again. The new draft was quietly "not yet signed: the memo reads them as the manager's or the screen's placeholders", although the table said "(entered)" on every line. I signed and ran again: three drafts for one typo. Then I issued it with a note. The plan checks flagged "Garbage, recycling and services MISSING 0 m²" and "Laundry MISSING", which was useful. "Accessible homes PASS 5 drawn, 3 wanted (BC Housing's 5% of 59)" counts the 59 homes drawn, while the rents and the grant count all 88.

**Manager mode at 03 on the 998 R4 I had just issued.** The route row read "The option 6 storeys · 105 homes · As approved by Council" for a five-storey, 88-home what-if. "What it takes to run" was entirely blank, inviting the manager to fill "the operator's rents and running costs, if you have them", with different hints from my desk ("Support staffing: Blank: none" against my "Never assumed"). I added a capital source ("Example Credit Union second loan", kind Loan, $3,000,000, Applied for) and "What are you asking for?", then ran. My figures were wiped again (D1, second time). The comparison said "every rule reads the same". The loan landed in "grants $18,669,192" with no payment (D2). "The decision wanted" printed my ask correctly on the front sheet.

**The paper memo and the short PDF.** The full paper version of my Glen R4 runs to about 38,000 px of screen height, dozens of printed pages, against the site's "Reads two pages". The operating table prints with the same wrong vacancy note and "$-0". The signature line, "Operating figures signed by Test Operator of Example Housing Society, 25 Nov 2026", is good. The short version is about 10,600 px. It keeps the rule-by-rule comparison with R1 but drops "What an operator checks first" and the area schedule, which are exactly the pages I would hand my board. My note to the manager is not printed in either.

## 3. Defects, ranked by harm

**D1. Reopening a signed run loses the operator's figures, and the next Run discards them silently.** Verified twice.
- Repro A: Operator mode, open `375-glen-drive/2026-11-25T18-24-15` (my signed R4) by URL. Every desk field is blank and the header reads "not yet signed". Tick "confirmed" and click Run again. Draft 18:26 shows "$2,049 a month a home (the rules' figure)", "$6,500 … PLACEHOLDER", "Support staffing not entered", debt $22,156,253.
- Repro B: Manager mode, open `998-e-19th-ave/2026-11-25T18-28-20`, go to 03 and add any capital source. Run again. Draft 18:30 shows the rules' rents, the $6,500 placeholder and "Who operates: Not named", and the Operator open item is gone.
- Cause seen in the page state: `state.option.operations` is absent after opening a run. The form loads the option file, not the run's inputs.
- Expected: the run's operating figures and signature reload. Or, at minimum, a warning that Run again will replace the operator's signed figures.

**D2. A capital source of kind "Loan" counts as a grant and is never repaid.** Verified once.
- Repro: Manager mode, 03, add the source "Example Credit Union second loan", kind Loan, $3,000,000, status Applied for. Run again.
- Seen: "grants $18,669,192 … debt $9,284,785", and the loan payment stays −$627,855, the full 1.10-coverage mortgage on the same NOI. The ledger line says "named source: a loan, applied for, not committed", but its payment goes nowhere.
- Expected: a rate and term for the loan, its payment set against the NOI, and the screen's mortgage reduced to match.

**D3. Shelter beds carry no running cost or reserve in a mixed building.** Verified twice (placeholder run and my run).
- Seen on Glen: operating cost −$1,059,500 = $6,500 × 163 homes, then −$1,385,500 = $8,500 × 163. Reserve $130,400 = $800 × 163. The 80 beds appear only in the per-bed subsidy line.
- The field's own hint says "a home a year; a bed a year for a shelter". `proforma.py` costs beds only when there are no homes.
- Expected: the beds costed at a per-bed figure, or a separate shelter line.

**D4. The building's subsidy is divided twice.** Verified twice (on screen and in the paper memo).
- Seen: "$1,408 a home a month over 163 homes; $2,868 a bed a month over 80 beds", both computed from the same $2,753,356.
- A funder reading per bed will take the whole building's deficit as the shelter's.
- Expected: a subsidy per part, or one rate, clearly labelled as the building's.

**D5. Vacancy accepts 2 (200%), and the figure can be signed.** Verified once.
- Repro: on 998, type "2" for vacancy, sign, then Run again.
- Seen: "Vacancy −$2,536,320", and the verdict became an operating shortfall. The field has no maximum and gives no warning.

**D6. The Vacancy row always says "the CMHC survey's rate, on all tiers".** Verified twice (Glen R4; 998 drafts 18:27 and 18:27:55; the paper repeats it).
- This happens even with 2% entered. The ledger says "entered: 2.0% of gross rent".
- The note is a fixed string in `proforma.py` (line 811) and `memo/answers.js` (line 296).

**D7. Staffing is netted into the debt NOI, so the whole building's debt drops to $0.** Verified once.
- Seen on Glen: debt went from $22.2M to $0 and the gap from 77% to 100%. The independent homes' rents, less their running costs, could still carry a loan, and support services run under their own agreement.
- The $3.9M subsidy against a $2.75M need leaves a $1.15M difference that appears nowhere: there is no "after subsidy" line.

**D8. The signature does not track the figures.** Verified once.
- After I edited vacancy, the desk kept "signed by Test Operator … 2026-11-25" until the run. The new draft was unsigned, with no message saying so.
- That draft's header says "the memo reads them as the manager's or the screen's placeholders" while every row reads "(entered)".

**D9. The operator who signs is never named as the operator.** Verified twice (both sites).
- "Who operates: Not named; the operating figures are signed by Test Operator". The organization I signed with is ignored.
- The Manager items "Who operates the homes … Name the operator" and "Parts of the building … enter their staffing and subsidy" stay open after I entered both.

**D10. "The staffing model and its cost" closes on a dollar figure alone.** Verified once. The item asks "who is on site, by shift", and I gave none.

**D11. The accessible-homes and service checks count drawn homes; the money counts all homes.** Verified twice.
- Seen: "7 wanted (5% of 134)" on Glen against 163 homes, and "3 wanted (5% of 59)" on 998 against 88.
- The rent roll includes 29 homes that the plans do not hold.

**D12. Negative money is formatted wrong.** Verified twice. "$-0" (the loan payment, and support staffing entered as 0) and "$-2,753,356" for the NOI.

**D13. The manager's route row is stale.** Verified once. On 998 R4 it read "6 storeys · 105 homes · As approved by Council" while the option was the 5-storey what-if.

## 4. Interface problems, ranked

1. **The operator has no place on the website, and no walkthrough in the tool.** who.html's flows, the "three kinds of reader" and the mode list omit the operator; `tour.js` has no operator tour.
2. **One budget for three buildings.**
   - The Ask reads "163 homes and 80 beds … 25 of them supportive homes: 89 at market rent". Are supportive homes in the market tier?
   - The deep-subsidy hint "0 for a shelter" would zero the 37 deep-subsidy homes in a mixed building.
   - One subsidy, one term and one funder cannot express a Supportive Housing Fund operator agreement beside an Emergency Shelter Program services agreement.
3. **Sign before seeing.** The order is enter, sign, run: I sign inputs, not the table and the checks they produce. Each correction costs a sign and a run, and leaves another draft.
4. **The opening banner and "What changed" are unreadable** (quoted in section 2), and the page auto-compares against R1 when I was sent R2.
5. **The program brief contradicts itself and is thin for a shelter.**
   - The heading says "no brief: the amenity and services only" over 13 shelter and supportive rows.
   - Missing: a kitchen or servery for a shelter that serves meals, a medical or nursing room, an intake room, a staff break room for the shelter, a separate shelter entrance, cart and pet storage, loading.
   - The checks pass "Desk" and "Staff office" once for a building that needs two of each. They do not test separate entries, washroom and shower ratios per bed, or a shelter floor shared with family homes: Level 2 holds the sleeping rooms and two 3-bed homes.
6. **The manager's 03 duplicates my fields with different hints and no lock**, so nothing shows they are the operator's signed figures.
7. **Run again moves in the top bar** as the revision label changes width (from "R2" to "Draft 18:27"). My first click missed.
8. **Issuing goes only to the development manager.** I could not copy the architect on the plan issues, and the note never reaches the paper.
9. **The short PDF drops the operator's checks** and keeps a long rule-by-rule comparison. The full paper is far from "two pages".
10. **Capital source statuses are only Committed / Applied for / Assumed.** There is no "conditional letter", no "intake closed", and no rate or term for a loan.
11. **Vacancy is entered as a share.** Accept "2%" or show the % beside the field.

## 5. What works and I trust

- The operating table's structure: rents by tier × homes, vacancy, operating cost, reserve, staffing, "Left after running costs", "Subsidy needed", per home a month. My hand checks matched to the dollar.
- The ledger cites entered figures ("entered: $1,750 a month × 89 homes").
- "Support staffing never assumed": the shelter and supportive parts cannot read "likely" without it.
- An unconfirmed subsidy sizes no debt and raises an Operator item: "Confirm the subsidy with its funder, in writing, with its term."
- The Operator lane in answer 3, and the issue note under the manager's title with name and time.
- "Where the money comes from" with honest statuses ("illustrative: nobody has offered it", "not counted").
- "Subsidy needed if the capital still missing were borrowed", and the same on BC Builds' take-out terms. These are the most useful operator lines on the page.
- The program list (Emergency Shelter Program, HEARTH, the Supportive Housing Fund, Reaching Home) with each one's route and intake.
- The paper's "Operating figures signed by … , 25 Nov 2026".
- The plan checks that found missing garbage, laundry and accessible homes.

## 6. Wish list (top five first)

1. **Operating figures persist with the run** and reload into the desk and 03. Make Run again refuse, or warn, before it replaces signed figures. (M)
2. **A budget per part.** Independent, supportive and shelter each get their own rents, operating cost (per home or per bed), staffing, subsidy, term and funder. Debt is sized on the rent-bearing part only. (L)
3. **Loans as loans.** Rate, term and payment against the NOI, and the screen's mortgage reduced to suit. (M)
4. **Input bounds.** Vacancy entered as a percent, from 0 to 25%. Warn on operating cost or reserve far from the placeholders and on staffing per bed outside a band. (S)
5. **A term view.** Years 1 to the subsidy's end and after it, with costs escalating against rents. What happens in year 6 when a 5-year agreement lapses? (M/L)
6. **Sign the result, not the inputs.** Tie the signature to the figures, and say plainly when an edit voids it. (S)
7. **Take the operator's name from the signature** into "Who operates" and close the Manager item. (S)
8. **An operating cost breakdown:** utilities, insurance, property tax, repairs, management, cleaning, security, and food for a shelter. (M)
9. **Plan checks for a mixed building:** entries and desks per part, shelter washroom ratios, a kitchen, a medical room, a staff room, and the shelter separated from family floors. (M)
10. **An operator page on who.html, and an operator walkthrough.** (S)
11. **A two-page operator PDF:** the front sheet, the operating table, the plan checks and the signature. (S)
12. **Rents by bedroom type within each tier.** (M)
