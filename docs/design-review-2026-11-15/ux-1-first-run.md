# UX critique 1 of 3: the first run and the manager's flow

Lens: onboarding, the seven-stop guide, the stage in the memo pane, the status strip, the moment of running the rules, and what a first-time development manager understands and feels at each step. Evidence: the sixteen screenshots in `audit/evidence.md` (numbered as there), PRODUCT.md, DESIGN.md, docs/user-flows.md, `ffm/ui/app.js` (`STAGE`, `renderStage`, `stageOption`, `renderGuideInto`, `guideDone`, `guideUseOptionNow`, `guideLookup`, `runRules`, `init`).

## 1. Design-specificity verdict

The memo is authored for this product and nobody else's: a title block with a revision, verdicts as marked words, an open-items table with a "Who / what" column, "Not sure" as a filled amber choice, a rule id under every suggested figure. Nobody would mistake that for a generic SaaS screen. The guide that leads to it is the generic part: an accordion wizard in a 400 px rail with numbered badges and checkmarks, which could sit in front of a mortgage application. And the stage, the best idea in the flow (the memo pane filling up stop by stop), currently looks like a list of six grey placeholders until stop 2, and later contradicts the rail.

## 2. Nielsen's ten heuristics

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 2 | The strip reports every action well, but the stage goes stale (card 04 says "ENVELOPE not set · UNITS not set · TIERS not split" while the rail lists 4 units and tiers, shot 8), and the top bar's Run the rules does nothing at all on a blank page, with no message (`runRules` returns early when there is no site or option). |
| 2 | Match with the real world | 3 | "Money in", "Funder-ready", "Left to a person" and "Not sure" are the manager's words; "layers A to C", `bc.ssmuh.minimum_units` under every row and "site control 'None'" (a Python `None` reaching the memo, shot 11) are not. |
| 3 | User control and freedom | 2 | "Change the site" is a good exit, but clicking another candidate (Outright, Benchmark, Funder-ready) wipes every Mine figure without a word (`guide.mine = {}` in the `.cands` handler), and clicking an open stop's head collapses the whole guide to no open stop (`guide.step = 0`). |
| 4 | Consistency and standards | 2 | Two Run the rules buttons behave differently: the top bar's runs with anything, stop 5's stays disabled (shot 10). Seven stops in the rail, six cards on the stage. The progress line said "5 done" while stop 4 still showed "4" and not a check (shot 11). |
| 5 | Error prevention | 1 | Use this option accepts blank storeys, height and floor area and reports "with 3 of your own figures" (shot 10 strip); the tool suggests a 1/2/1 tier split and then fails the fund on that same split; "Not sure" answers are read as "no" and "None" and produce two Fails. |
| 6 | Recognition rather than recall | 2 | The "not sure" questions live in three places at once (the stage's Not sure line, the Site card far below the guide, and the eight-item "Left to a person" block at stop 4), so the manager has to remember which ones they already answered and where. |
| 7 | Flexibility and efficiency | 2 | Ctrl+Enter, a saved site and a saved option are there, but a fresh address needs at least nine clicks through the stops (Look up, Use this site, Use these programs, Read the site, a candidate, Suggest, Use this option, Run) with no route that skips the parts with no decision in them. |
| 8 | Aesthetic and minimalist design | 2 | The blank first screen has three bands before any content (progress line, status strip, tour offer), run pickers and a Summary/Detailed/3D switch with nothing to pick or view, and six empty stage cards that repeat the rail. Stop 4 then has 21 figure rows and 8 questions in one column. |
| 9 | Help users recognise and recover from errors | 2 | "Type an address first." is plain, but it sits in a red strip 120 px above a field that gets no focus or invalid state; the Fail findings name the wrong cause (the tool's own split, an unanswered question) so the manager cannot act on them. |
| 10 | Help and documentation | 3 | The walkthrough, the help line under every stop, the (i) buttons and the cited source under every program term are well above the norm; the walkthrough offer itself is in the way (below). |
| | **Total** | **21 / 40** | |

## 3. Cognitive load

Failing items on the eight-point checklist:

- **Single focus: fail.** At stop 1 the eye has the stop, the walkthrough offer, the stage's "Load the demo case", the always-blue Run the rules and the mode switch all competing (shot 1). The one action that matters, the address field, is a 12.5 px field in the left third of the screen.
- **Chunking (no more than 4 per group): fail.** Stop 4 is one flat list of 21 Suggested | Mine rows (rezoning path through side setback) followed by 8 questions (shots 8, 9). Stage card 02 lists up to 7 terms per program, two programs deep.
- **Grouping: fail at stop 4.** Envelope, homes, rent tiers, funder terms, trees and drawing assumptions (floor to floor, setbacks) share one undivided list, and "Left to a person" mixes site facts (Community Vision area, transit area, bus stop, tenure, trees) with option facts (developer partner, site control).
- **Visual hierarchy: partial fail.** The memo pane is the largest thing on screen and says the least for the first two stops; the rail, where the work is, is set at help-text sizes.
- **One thing at a time: pass within the guide** (one stop open at a time, and the "one way in" segment at stop 1 is right), **fail on the page**: the Site card opens below the guide after stop 1 (shot 4) with every site field, so two input systems are on screen from stop 2.
- **No more than 4 visible options per decision: fail** at the points listed below.
- **Working memory across screens: fail.** What was answered "Not sure" at stop 1 has to be recalled at stop 4 and again when reading the memo's Fails; the rail's suggestion and the stage's card 04 disagree, so the manager has to keep both in mind and decide which one is true.
- **Progressive disclosure: partial pass.** The Claude folds and the stops collapse correctly; the empty pickers and view switch on a blank page, and the always-open "Every line" table after the run, do not wait.

Decision points with more than four visible options:

1. **First screen (shot 1):** about 20 controls you can act on: 3 modes, the rules date, Run the rules, Walkthrough, Take the walkthrough, Not now, the rail fold, An address / A saved site, the field, Look up the site, Ask Claude, seven stop heads, Open a past run, Compare with, Summary / Detailed / 3D preview, Load the demo case.
2. **Stop 2 (shot 4):** four programs plus Use these programs, with the Site card's own fields open beneath.
3. **Stop 4 before suggesting (shot 6):** a saved-option select where one exists, three candidates, Suggest from the rules.
4. **Stop 4 after suggesting (shots 8, 9):** 21 rows of two segments each, 8 three-way questions or selects, Derive again, Use this option: more than 70 targets.
5. **After the run (shot 11):** Summary / Detailed / 3D, two pickers, Run again, Issue, stop heads, the export bar, plus the memo's own disclosures.

## 4. The emotional journey of a first-time manager

| Moment | What they see | What they feel |
|---|---|---|
| Arrival (shot 1) | A dark bar with a blue Run the rules, three bands of instructions, a pane of grey cards. | Oriented but braced. "Seven stops" sounds like a form; the walkthrough offer says "this is harder than it looks." |
| Empty Look up (shot 2) | A red strip. | A small scold, quickly forgotten. |
| The lookup (8 s, shot 3) | A busy strip, then three lines in the rail: RT-3, 566.7 m², found as. The big pane does not change. | **First valley.** The tool has just done something impressive (the City's parcel, district and dimensions from one line of text) and shows it as small print. The reward is postponed behind "Use this site." |
| Use this site (shot 4) | The parcel on a real map, the district, the lot, a "Not sure" line, and the programs' published terms with their sources. | **First peak.** This is the product's promise come true: my site, on the City's data, cited. |
| Read the site (shots 5, 7) | Eight rules on the stage, six of them Uncertain, each naming a person. | Mixed. The named people are reassuring; six of eight Uncertain before any option, with "Manager: supply…" lines, reads like homework. The news that matters (the stack has no RT-3 schedule) is in a fold's parenthetical. |
| Suggest from the rules (shots 8, 9) | 21 rows, three of them amber "placeholder" with empty Mine boxes, 4 homes, 8 questions. | **Deepest valley.** "? storeys, no floor area" in the strip. A first-timer does not know what height to type for RT-3. The stage beside the rail says "not set" for things the rail says are set. Confidence drops: which side is right? |
| Use this option, Money in (shot 10) | The strip says "with 3 of your own figures"; stop 5 is greyed out and says "Shape or pick an option first." | Confusion. The tool says I'm done and not done in the same glance. The manager finds the top bar's Run the rules, which works, and feels they cheated. |
| The run (shot 11) | 271 ms, the memo replaces the stage: "Allowed outright." in green, then a red "No." for the funders. | A quick lift, then a drop. The Fail reasons are the tool's own split (1/2/1 against 30/50/20 on 4 homes) and a "None" for a question they answered "Not sure." Below, FIG 02 draws a one-storey, 285 m² building the manager never entered, while answer 04 says "No floor area." |
| End | Seven open items with named people; money "Unsure". | **Wary, not empowered.** The open-items table is the right ending and the brand's best moment, but by then the manager has caught the tool contradicting itself twice and will not take the memo to a board without checking every line. For a product whose success measure is "trust the memo enough to act on it and cite it", that is the wrong closing feeling. |

## 5. Strengths

1. **The stage as the memo before it is written.** One card per stop, filling as each stop answers (shots 4, 5): the parcel on the City's data, then the programs' terms with their sources and in-force dates, then the reading. It turns a wizard into a document taking shape, which is what the manager is actually making. It works because it shows each answer in the pane where the final answer will appear, so the run does not arrive as a surprise.
2. **The status strip's copy.** "Read the site as of 2026-11-15: 8 rules speak to it before any option." "The site is in the Site card below, unsaved, and on the map: answer the policy areas…" Every action gets one specific sentence that names what happened and what is next, in the voice PRODUCT.md asks for. It works because it replaces toasts, spinners and modal confirmations with one place to look.
3. **Suggested | Mine with the rule under the figure, and "placeholder" said out loud.** Shots 8 and 9 show the deterministic character at the point of decision rather than only in the ledger: every figure the manager accepts already carries its citation, and what no rule settles says "no rule in the stack derives this for RT-3: enter it". The flow is honest at the moment of choosing, not only afterwards. (The flaw is what happens after, below.)

## 6. Priority issues

### P0-1. The tool fails its own suggestion and reads "Not sure" as "no"
- **What:** Answer 02 "No." (shot 11). CHF fails on "unit mix market 25.0%, rgi 50.0%, deep_subsidy 25.0% is not 30/50/20", a split the tool derived at stop 4 from the fund's own rule on 4 homes (shot 9: "30% of 4 units under the fund's 30 / 50 / 20 mix"). It also fails on "site control 'None'" when the manager left site control at "Not sure". BC Builds fails on "a non-profit must team with a developer" when developer partner was left at "Not sure".
- **Why it matters:** Product principle 2 is "say uncertain rather than guess." Here an unanswered question becomes a Fail, and the tool's own suggestion becomes a Fail. The manager's first memo tells them "no" for reasons that are not true, and teaches them that the tool's suggestions cannot be trusted. That breaks the success measure in PRODUCT.md.
- **Fix:**
  - (a) In the engine's funder checks (`ffm/checks.py`, the CHF and BC Builds checks, so the UI still calculates nothing): a null `site_control` or `developer_partner` gives `uncertain`, not `fail`, with an action. Copy: "Site control not given. Manager: say which of letter of intent, purchase agreement, council resolution or finalized applies." Never format a null as `'None'`.
  - (b) In `ffm/suggest.py`: when the unit count cannot meet the mix within the fund's tolerance, the tier fields carry a note, and stop 4 shows it in the row's `.sg-note` in Uncertain Text. Copy: "4 homes cannot split 30 / 50 / 20 within the fund's 2% tolerance; the nearest is 1 / 2 / 1 (25 / 50 / 25), which the fund will read as short. More homes, or a word with BC Housing, settles it." The note travels into the memo as the finding's reason, so the Fail is at least one the manager was warned about.

### P0-2. An incomplete option passes stop 4, runs anyway, and draws a building nobody entered
- **What:** At stop 4 the Storeys, Height and GFA rows open on Mine with empty fields (`guide.mine[k] = ""` for the core rows in `renderGuideInto`). "Use this option" accepts the blanks and reports "with 3 of your own figures" (shot 10 strip; `guideUseOptionNow` counts `Object.keys(guide.mine)`, blanks included). Stop 5 then disables the money fields and its Run button because `guideDone()[4]` needs `storeys != null` (shot 10). The top bar's Run works anyway; the memo says "No floor area" and FIG 02 says "Proposed: 1 storeys … 285 m² (FSR 0.50)".
- **Why it matters:** The manager is told they are done, stopped, and then allowed through by a second button, and the result shows a massing they never chose next to an answer that says there is no floor area. It is the moment they stop believing the drawings.
- **Fix:**
  - In `guideUseOptionNow`, count only non-blank Mine figures. If storeys, height or GFA is blank, keep the option but say so on the button and in the strip. Button: "Use this option without an envelope". Strip, in Uncertain Text on the busy wash: "Storeys, height and floor area are blank, so the run will answer allowed and funders but not the money, and draws no building. Enter them at stop 4 to get all four answers."
  - Base stop 5 and 6 enabling on `state.option` existing, not on storeys, so the two Run buttons agree.
  - In `runRules`, when nothing can run, write to the strip rather than return silently: "Nothing to run yet: find a site at stop 1." (DESIGN.md: "Every action writes here.")
  - Engine side (`massing.build`, out of this lens but caused here): with no storeys, FIG 02's caption reads "No storeys given: no section drawn", never a 1-storey default.

### P1-3. The stage contradicts the rail at stop 4
- **What:** Stage card 04 (shot 8, and evidence) reads "ENVELOPE not set · UNITS not set · TIERS not split" while the rail lists 4 units, tiers 1/2/1 and 60 years. `stageOption` takes `state.option || S.option`, and after Use this site a blank `state.option` already exists, so the suggestion is never shown.
- **Why it matters:** The stage exists to tell the manager what the memo will be built from. When it disagrees with the rail, the manager has to decide which pane is lying, at the moment they are least sure of themselves.
- **Fix:** In `stageOption`, while `guide.suggestion` exists and has not been used, draw `S.option` with `guide.mine` merged in, and label it in the Candidate row: "Funder-ready, suggested · not yet in the Option card: Use this option at stop 4". After Use this option, draw `state.option` and drop the label. Blank Mine fields show as "<i>yours to enter</i>", not "not set".

### P1-4. The lookup's result never reaches the stage
- **What:** After an 8-second lookup, the result is three lines of small print in the rail (shot 3); the map and the facts appear only after "Use this site" (shot 4). The help text says "Check it, then use it", but the evidence to check (the parcel on a map) is withheld until after the commitment.
- **Why it matters:** This is the first moment the tool does something the manager could not do alone, and the first chance to catch a wrong parcel (the lookup once landed on the 300 block, per CLAUDE.md). Showing it small and late spends the flow's best moment of delight and lets a wrong parcel through.
- **Fix:** In `guideLookup`, on success, render stage card 01 from `guide.lookup.site` as a preview: the map with the parcel ring, the district, the lot. Card heading: "Is this the parcel?" Under the map, in Muted: "Found as 609 Heatley Ave, Vancouver, from the City's address list. If the outline is wrong, look up again or pick a saved site." Mirror the "Use this site" button there, so the yes is given while looking at the evidence. Add `guide.lookup` to the `stageSig` array in `renderStage` so the map redraws only when the found parcel changes.

### P1-5. The single most important fact about an RT-3 site is in a parenthetical
- **What:** That the rule stack has no outright schedule for RT-3 is told only in the summary of a closed fold at stop 3: "Read the district schedule with Claude (no outright schedule for RT-3 in the stack; with a key)" (shot 5). The manager then meets its consequences at stop 4 as three amber "placeholder" rows with empty boxes.
- **Why it matters:** It decides whether the tool can produce the envelope at all. A first-timer reads "with a key; optional" and skips it, then gets stuck at stop 4 with no idea what height RT-3 allows.
- **Fix:** Say it where the district is first found, and again at stop 3, as a sentence and not a fold summary.
  - Stop 1, in the found-site list under District (`renderGuideInto`, the `lk` block), in Uncertain Text: "The rules here have no RT-3 schedule yet. At stop 4 you will enter storeys, height and floor area yourself, or read the City's schedule with Claude at stop 3."
  - Stop 3's help line, above the button: "RT-3 has no outright schedule in the rules. The reading covers the rezoning policy, transit and trees; the envelope waits for you or for the schedule."
  - The fold summary becomes plain: "Read the RT-3 schedule with Claude (needs a key)".
  - In `guideReadSite`, the strip: "Read the site as of 2026-11-15: 8 rules speak to it. No RT-3 schedule in the rules: the envelope is yours to enter at stop 4."

### P2-6. The first screen asks for attention in six places before it asks for an address
- **What:** Shot 1: the progress line, the status strip and the walkthrough offer stack three bands above the work. The run pickers ("Open a past run", "Compare with…") and Summary / Detailed / 3D preview sit over an empty pane. Run the rules is the loudest thing on screen and does nothing. Six empty stage cards repeat the rail's stops in grey. On a phone (shot 16) the offer takes a third of the first viewport and the stage is below the fold.
- **Why it matters:** The flow's first instruction is one field. Everything else on the screen tells a first-timer that the job is bigger than it is.
- **Fix:**
  - In manager mode with no run and no runs for the site, hide `#open-run`, `#compare-run` and `#view-switch` (in `placeRunTools(false)` or a `[data-mode="manager"] .memo:not(.has-run)` rule in app.css).
  - Give `#run-btn` `aria-disabled="true"` and a title "Find a site and shape an option first" until `state.site && state.option`. It stays signal blue but at 45% opacity, per DESIGN.md's disabled rule.
  - Move the walkthrough offer out of its band and into the stage head, under "Load the demo case", as a quiet link: "or take the two-minute walkthrough". Drop "Not now"; the Walkthrough link at the end of the bar stays.
  - Collapse the empty stage cards into one list under the stage head: "02 The programs · 03 What the site allows · 04 The option · 05 The money · 06 The memo: each fills in as you reach its stop." Draw only the current card full size.

### P2-7. Stop 4 is a spreadsheet in a 400 px column
- **What:** 21 Suggested | Mine rows, each with a rule id in mono that wraps over three lines (`bc.ssmuh.minimum_u / nits`), then 8 questions (shots 8, 9).
- **Why it matters:** This is where the manager decides what the building is, and it is the least structured screen in the flow. The three rows that need them (storeys, height, GFA) look the same as the eighteen that do not.
- **Fix:** In `renderGuideInto`, group `GUIDE_FIELDS` under four keys and fold what needs no decision:
  - **Envelope** (rezoning path, storeys, height, GFA): always open, first.
  - **Homes** (unit mix, tiers, accessible): open, shown as one line per group ("4 homes: 1 studio, 2 one-bed, 1 two-bed · bc.ssmuh.minimum_units") with Mine opening the four fields.
  - **Funder terms** (agreement years, below-market share and discount, share below HILs): folded, with a one-line summary.
  - **Drawing assumptions** (replacement trees, floor to floor, setbacks): folded and keyed "placeholders", since they shape the drawings and not the answers.

  Move the site questions in "Left to a person" (Community Vision, transit area, bus stop, tenure, trees) to stop 3 under the reading that raised them, each beside its Uncertain finding. Only developer partner and site control stay at stop 4. Put the rule id on a line of its own in mono at 11 px, never wrapped mid-token (`overflow-wrap: anywhere` off; wrap at the dots as the paper memo does).

### P3-8. Stops 2 and 3 cost two clicks for one decision, and the stop heads are fragile
- **What:** "Read the site" (stop 3, shot 5) is a button with no input: the manager already chose everything it reads. A click on the open stop's head collapses the guide to no stop (`guide.step = 0`). Per the walk, the stop heads and the address field report no accessible name beyond the placeholder and the program checkboxes are named by rule id; these need checking in the accessibility tree.
- **Why it matters:** Each idle click is a moment of "what does this do?" for Jordan and friction for Alex, and an unlabelled field fails a screen-reader user at the first step.
- **Fix:** "Use these programs" reads the site at once (`guideReadSite` chained), and stop 3 opens on the reading with "Read it again" and the schedule fold. Its title becomes "What the site allows". A click on the open head goes to the next stop, not to none. Check the stop heads, the address field (`aria-label="Address"` if the wrapping label is not picked up) and the program checkboxes (named by their title spans) in the accessibility tree.

## 7. Persona red flags

**Jordan, first-time development manager.** Has an address, a board date, no zoning vocabulary.
- Stop 1: does not know whether to take the walkthrough or start; picks start because the field is right there. Fine.
- Stop 2: does not know what the PD loan or CMHC AHF are; leaves the defaults, which is the right outcome but by luck.
- Stop 3: six of eight findings are Uncertain with "Architect: check Map 1…" and "Manager: supply…". Jordan reads this as "I have failed six things" rather than "six questions with owners", because the wording comes before any reassurance.
- Stop 4: **breaks here.** Three amber placeholder rows with empty boxes ask for RT-3 storeys, height and floor area. Jordan has no basis for a number, does not know a schedule exists, leaves them blank, presses Use this option, is told "with 3 of your own figures", finds stop 5 disabled, and is stuck. If Jordan finds the top bar's Run, the memo says "No." to the funders for reasons Jordan cannot act on and draws a one-storey building Jordan never asked for.
- The memo: Jordan cannot tell which of the seven open items is theirs to resolve first, and has just caught the tool contradicting itself, so the PDF does not go to the board.

**Alex, power user** (an architect or an experienced manager doing a third site this week).
- Wants: paste an address, take the outright envelope, run, compare with funder-ready. Gets: at least nine clicks, two of them on stops with no decision (Use these programs, Read the site).
- Switching candidate wipes every Mine figure without warning (`guide.mine = {}`); Alex loses typed numbers.
- The top bar's Run works at any stop, so Alex skips the guide, and the guide falls out of step: the progress line says "5 done" while stop 4 shows "4" (shot 11).
- 21 rows with no keyboard route through Suggested | Mine (each is two buttons; no "accept all suggested", no tab-to-next-Mine).
- The walkthrough offer stays on screen every visit until "Not now"; it is stored, but on a new browser or after a cleared profile it is back above the work.
- Alex is the one who notices the 1/2/1 Fail and the `'None'` and stops recommending the tool to Jordan.

## 8. Three provocative questions

1. If every number has to cite a rule, why does the guide ask the manager for the three numbers no rule gives (storeys, height, floor area on RT-3) before it asks the cheaper question: "Do you have a height in mind, or should we read the schedule first?"
2. The stage is the memo before it is written. What if there were no stage and no memo, only one document: the memo's four answers drawn from the first stop, reading "Not sure: stop 4 settles this" and filling in as the manager goes, so the run is not an event but the moment the last "Not sure" with a number behind it turns into a verdict?
3. A first memo that says "No." to the funders is what the manager will remember. Should the tool refuse to say Fail on anything that depends on an answer the manager has not given, and show that run as a draft ("Draft, 3 questions open") instead of R1, so the first revision a board ever sees is one that someone actually finished?
