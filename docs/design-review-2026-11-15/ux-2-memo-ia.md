# First Read: critique 2 of 3, information architecture and the memo as the output

Lens: the four answers, the open items, the money and its "every line" table, FIG 01 to 07, the ledger, rail against memo, guide stops against the Site/Option cards, the three views, the three modes, and what a board member or a funder's officer can follow and cite. Screenshot numbers are the evidence pack's (1 to 16). Code references are `ffm/ui/app.js` unless named.

---

## 1. Design-specificity verdict

The parts are specific to this job. The title block, R1/R2 revisions, verdict sentences with the status word, A1 to F7 references on paper, and "not sure" offered as a real answer all come from the drawing set and the referral report, not from a SaaS kit. Answer 01 on 998 E 19th ("Not outright. By rezoning: yes, with conditions.", screenshot 12) is the best single element in the tool.

The structure around those parts has grown by addition. There are four separate "left to a person" lists with four different counts. There are six numbering systems. The screen cites rule ids while the paper cites A1 refs. And the PDF, which is the thing the board actually reads, has no money lines: it sends the reader to "the memo on screen", which a board member never sees. The pieces are specific, but the way they fit together is not yet one memo.

---

## 2. Nielsen's ten heuristics (0 to 4)

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 2 | The status strip carries every action, which is good. But the 8 s lookup has no progress state, and stage card 04 reads "UNITS not set · TIERS not split" while the rail beside it lists 4 units and their tiers (screenshot 8 against the evidence notes). |
| 2 | Match with the real world | 3 | Memo, title block, revision and "not sure" are the users' own words. Mono rule ids (`bch.chf.eligibility`) on screen and "Outright / Benchmark / Funder-ready" are the engine's words, not theirs. |
| 3 | User control and freedom | 2 | Suggested / Mine per figure is excellent. But the Run button at stop 5 stays disabled while the status strip says "Run the rules when it reads right". A view stored in localStorage carries into Reader mode, where the switch to change it is hidden. |
| 4 | Consistency and standards | 1 | Four open-item lists with four counts (8, 7, 2, 2). Six numbering systems (stops 1 to 7, steps 1 to 4, stage 01 to 06, answers 01 to 04, FIG 01 to 07, paper sections and A1 refs). The Export footer's badge "4" collides with answer 4 and stop 4. The UI copy still says "three answers" in several places (view-switch titles, mode tooltip, status line). |
| 5 | Error prevention | 1 | The tool suggests a 1/2/1 tier split that its own fund rule then fails, and it reads the manager's "Not sure" on site control as `'None'` and fails it (screenshot 11). The tool creates the error it then reports. |
| 6 | Recognition over recall | 2 | Rule ids need a hover `title` to mean anything. A board member's "what is C5?" has no answer on screen. When the memo replaces the stage, the site facts found at stop 1 (map, owner, the "not sure" fields) leave the reading path. |
| 7 | Flexibility and efficiency | 3 | Modes, `?mode=`, `?run=`, Ctrl+Enter, past runs and Compare with are all good. Power is not the problem here. |
| 8 | Aesthetic and minimalist design | 1 | Summary is not a summary: the 20-row "Every line" table is open in every view. The CMHC source title prints in full on four consecutive rows (screenshot 14). Three or four full-wash status cards stack into a wall of red (screenshot 11). The walkthrough offer sits above the rail on every visit. |
| 9 | Recognize and recover from errors | 2 | "Type an address first." is clear. The funder failure, though, tells the manager that *their* site control is `'None'` and *their* mix is wrong, and both came from the tool. |
| 10 | Help and documentation | 3 | The walkthrough, the (i) buttons and the export note are good. There is no glossary for RGI, HILs, FSR, DCR, CD-1, SSMUH or TOA anywhere the board reads. |
| | **Total** | **20 / 40** | |

---

## 3. Cognitive load

Checklist (eight items):

| Item | Result |
|---|---|
| One primary focus per screen | **Fail.** After a run the rail's stop 6 repeats the four answers beside the memo's four answers, so the same verdicts appear twice side by side (screenshot 11). Before the run, the stop 4 form and the stage card 04 both claim to be "the option" and disagree. |
| Chunking (about four items per group) | **Fail.** The open-items table runs to 7 rows. "Every line" runs to about 20. Stop 4 shows about 20 Suggested/Mine pairs plus an 8-question block. |
| Related things grouped | Pass. The ledger by layer A to F and the clauses worst-first are well grouped. |
| Clear visual hierarchy | **Partial.** The verdicts are clear. But the four answers get equal weight and three of them a full wash, so on 609 Heatley nothing stands out from the red. The money answer's four big figures read as KPI tiles, which DESIGN.md forbids. |
| One thing at a time | Pass for the guide (one stop open). Fails after the run, when guide, cards and memo are all live. |
| Minimal choices at each decision | **Fail** (counts below). |
| Low working-memory load | **Fail.** The reader has to hold a stop number, a stage number, an answer number, a FIG number and a rule id, and on paper translate the id to an A1 ref. The "left to a person" counts change from screen to screen. |
| Progressive disclosure | **Fail.** "Every line" is `<details open>` in every mode and view. Architect mode opens every ledger layer at once. |

Five of eight fail and one is partial.

Decision points with more than four visible options:

- **Top region, manager, before a run (screenshot 1):** wordmark link, Manager, Architect, Reader, rules date, Run the rules, Walkthrough link, Take the walkthrough, Not now, rail toggle. That is **10**, and two of them are primary-styled (Run the rules and Take the walkthrough). After a run, the Revision box and possibly the issue chip join.
- **Memo tools row:** Open a past run, Compare with…, Summary, Detailed, 3D preview: **5**. They are three different kinds of control (pick a run, pick a comparison, pick how much to show) sharing one row with nothing separating them.
- **Export bar:** Download PDF, Print, Export to Revit, Issue to the architect, More formats: **5 visible**, 8 with the fold (Memo as HTML, Markdown, massing.json). In manager mode only Download PDF matters, and it sits at the foot of the whole memo, after sources and the stamp.
- **Ledger:** Open all layers plus six layer disclosures (A to F): **7**, below a clauses table that already lists every rule.
- **Stop 4 (screenshots 8, 9):** 3 candidates, Derive again, about 20 Suggested/Mine pairs (about 40 buttons), and 8 three-way questions. This is the heaviest decision point in the product, and it is where the tool sets up its own funder failure.

---

## 4. Reading order for three readers

**Manager (manager mode, Detailed, screenshot 11).** Title block, then 01 Allowed outright (green), 02 "No." (red), 03 "Seven open items" (red), 04 money.
- **The thread breaks at 02.** The two Fail lines name a tier mix the manager never typed (the tool derived 1/2/1 from the fund's 30/50/20) and a site control of `'None'` the manager never chose (they chose Not sure). The manager now doubts the whole memo, not just one line.
- **It breaks again at the rail.** Stop 6 says "LEFT TO A PERSON: floor area and unit count; land cost" while answer 03 says seven open items. Which list is the to-do list?
- **Third break: the export.** To send the PDF the manager scrolls past figures, clauses, six ledger layers, inputs, sources and the stamp to find Download PDF in the footer.

**Architect (architect mode, screenshots 12 to 14).** Title block, the four answers, then FIG 01 to 07 two per row, clauses, ledger with every layer open.
- **The thread breaks inside answer 04.** "Every line" opens a 20-row financial table in the answers zone, between the verdicts and the drawings. The architect's material (figures, then clauses) starts a screen and a half further down.
- **Second break: comments come back in A1 refs.** When the planner comments on the PDF ("C5 is wrong"), nothing on screen says C5. The architect has to count rows in a layer to find it.
- **Third break: the stage disappears.** The stage's site card (parcel map, owner, the "not sure" fields) vanished when the memo landed. The only trace of the site is the Inputs list near the bottom.

**Board member (the PDF, cold).** Title block with the fingerprint, then the answers table (Question | Answer | Decided by), then open items, clauses, massing, ledger, inputs, sources, reproduce.
- **Page 1, row 1, the thread breaks.** "Is it allowed outright? Not outright", decided by "A3 RM-1 outright floor space ratio (uncertain)". How can a definite "no" be decided by an "uncertain"? The board member reads it as the tool not knowing.
- **Row 5 breaks it for good.** "Does the money work? Unlikely … Every line and its source are in the memo on screen." The board member has no screen. The $12.5M gap, the one number the treasurer will repeat in the meeting, cannot be traced on paper.
- **Page 2.** The open items are named by policy title ("Interim Rezoning Policy for Social Housing in Former Community Vision Areas"), not by the missing fact. "Who" and "what" are merged in one column, so the board cannot see at a glance that three of four items sit with the manager.

---

## 5. Strengths

1. **The answer card's grammar.** Each card has a question as heading, a verdict sentence with the operative words in the status ink, then lead-and-continuation findings. Screenshot 12, "Not outright. By rezoning: yes, with conditions.", answers the question in the order a planner would and keeps the condition in the same breath. It works because the verdict is a sentence, not a badge, so it survives a photocopier and a projector and can be quoted in board minutes.
2. **Money you can audit.** Every pro-forma line names the rule it came from, links the source, flags placeholders in amber, and dates the index ("BCPI 109.2 (2026-04-01) over 106.1"). Next to the verdict it says "more than the 15% a feasibility screen can call close", stating the threshold rather than hiding it. No spreadsheet a non-profit is handed does this. It is the strongest argument for the tool's positioning.
3. **The paper memo's reference system.** A1 to F7 for rules, S-numbers for sources, revisions R1/R2 like drawing issues, and a "how to reproduce" section make the PDF citable, the way a drawing set is citable by sheet and detail. It works because a planner can write "re C5" in a comment and the reference is stable across reprints. The weakness is that the screen does not speak this language yet (issue 5).

---

## 6. Priority issues

### P0-1. The tool fails the funders on figures it chose itself
**What.** Answer 02 on 609 Heatley (screenshot 11) reads "No." with CHF failing on "unit mix market 25.0%, rgi 50.0%, deep_subsidy 25.0% is not 30/50/20; site control 'None' does not meet the RFP's readiness bar." The 1/2/1 split was derived at stop 4 by the Funder-ready candidate (screenshot 9, rule `bch.chf.eligibility`, "30% of 4 units under the fund's 30/50/20 mix"). Site control was left Not sure, not set to None.

**Why.** To the manager, the memo blames them for the tool's arithmetic and misreports their answer. To the board, "No." is the headline of the meeting, and it is partly an artefact. This breaks the one promise the product makes, "say uncertain rather than guess" (PRODUCT.md principle 2).

**Fix.**
- **Engine, `ffm/checks.py` (the `chf_fit` check).** A null or not-sure `site_control` goes to `unknown` and never to `fails`, so the status is uncertain and the action reads "Manager: state site control (letter of intent, purchase agreement, council resolution)." Never print a Python `None` in a finding: add a test in `tests/` that greps findings for `'None'`.
- **`ffm/suggest.py` (funder-ready candidate).** When no integer split of n units lands within the fund's tolerance, do not suggest one silently. Add an unsure item and keep the candidate honest. Copy: "No split of 4 homes lands within 2 points of the fund's 30 / 50 / 20 mix; the closest, 1 / 2 / 1, is 25 / 50 / 25. The mix can be met from 10 homes." The finding in `chf_fit` uses the same sentence, so the Fail reads as a fact about size, not a mistake by the person.
- **UI, `renderGuide` stop 4.** When the suggestion carries that unsure item, the candidate segment reads "Funder-ready (not at this size)".

### P0-2. The PDF has no money lines, and sends the board to a screen it does not have
**What.** In `paperDocument`, the money row of the answers table ends "Every line and its source are in the memo on screen." No section of the paper memo carries `pf.lines`. Layer F appears in the paper ledger as rules, but not the arithmetic (hard × escalation + soft + contingency + land; NOI over DCR to debt; capital less funding to gap).

**Why.** The board and the funder's officer are the readers this answer exists for. The gap is the number they will quote, and on paper it cites nothing. This contradicts "every number links to the document it came from" in the memo's own disclaimer.

**Fix.**
- **`paperDocument`.** Add a section "The money, line by line" directly after the open items (before the comparison), built from `run.proforma.lines`. Columns: Ref (the F ref from `refOf`, or "option"), Line, Figure, How (the note), Source (S-number). Placeholders get a printed "placeholder" mark. The section closes with the caveat paragraph from `answerMoney`. The schedule ends with the subtraction set out as lines: Capital cost / less Funding / **Gap**.
- **Row copy.** Change the row's last sentence to "Every line, its rule and its source are in section 3."
- **Numbering.** Renumber `sn` so the sections that follow move up one.

### P1-3. Four "left to a person" lists, four counts
**What.**
- Status strip at stop 4: "8 left to a person" (screenshot 8).
- Rail stop 6: "LEFT TO A PERSON: floor area and unit count; land cost" (screenshot 11, from `pf.verdict.unsure`).
- Answer 03: "Seven open items".
- Answer 04: its own "Left to a person:" line.
- Stage card 04 (`stageOption`): "Left to a person: … Answer them in stop 4."

**Why.** The product's third answer, "what is unsure and who resolves it", is the manager's to-do list (user-flows.md, Flow 1 step 5). Three numbers for one list means none of them is trusted.

**Fix.**
- **One list, owned by the engine.** The pro-forma's unsure items join `L.summary.answers.unsure` with a `layer: "F"` tag and an action ("Manager: enter the land price or the assessed value"). Engine change: `ffm/proforma.py` returns them in a form `memo.py` and the ledger summary can merge. Answer 03 then counts everything, and answer 04's line becomes "Two of the open items in answer 3 are the money's: land cost; floor area."
- **Rail.** Stop 6 drops its own list. Copy: "7 open items, each with a named person: see answer 3 in the memo." Make it a link that scrolls to and focuses the answer 03 card.
- **Stop 4.** Rename the block "Answer now, or leave as not sure". Those are inputs; they become open items only if left blank.

### P1-4. The memo contradicts itself where a funder will look
**What.**
- **Paper answers table, row 1.** "Not outright" decided by "A3 … (uncertain)". The engine gives `cov.rm1.outright_fsr` the status Uncertain for "FSR 2.95 exceeds the outright maximum of 1.2" (memo.md, Layer A).
- **Escalation.** The money table prints ×1.0292, "BCPI 109.2 (2026-04-01)". The ledger's F row for `f.escalation_bcpi` prints "109.4 … escalation 1.031" in the same memo.
- **The grant.** Funding counts the CHF grant of $17,977,155 while answer 02 says the CHF fit is uncertain (998) or fails (609), and the fund is between calls.
- **Rents.** The as-approved run prices all 105 social units at market rent, which inflates NOI and the supportable debt. The memo states the fact but not which way it moves the gap.

**Why.** A funder's officer reads the ledger to check the summary. Two escalation figures, or a "no" decided by an "uncertain", read as sloppiness, and sloppiness discounts every other figure in the memo.

**Fix.**
- **Engine, outright checks.** When the option exceeds the outright limit, the outright status is fail with the rezoning path carried in the finding; the by-rezoning answer stays where it is. Copy: "Outright: no. FSR 2.95 against 1.2; the path is a rezoning (CD-1 under the Interim Rezoning Policy)."
- **Engine, the `assumption` check.** Print the value in force on the run's as-of date (the quarter `proforma` used), not the latest observation in the rule file.
- **`answerMoney`, Funding line.** Say the dependency: "grants $17,977,155 (Community Housing Fund, indicative: counted only if answer 2 is confirmed and the fund reopens)".
- **`ffm/proforma.py`, when tiers are null.** Have the verdict's `why` add a sentence. It is safe to state because the direction is fixed: rent-geared-to-income and deep-subsidy rents are at or below market, so NOI and supportable debt can only fall. Copy: "Every unit is priced at market until the tiers are set; setting them can only widen the gap."

### P1-5. Two citation systems: rule ids on screen, A1 refs on paper
**What.** On screen the money table, the clauses, the ledger and the figure captions cite `bch.chf.eligibility`, `f.rents` and `cov.irp.social_housing_rezoning` in mono (screenshots 13, 14). The paper cites E2, F6, A1 and S19. `refOf` and `srcNo` live only inside `paperDocument`. The "From" column of "Every line" repeats the full CMHC source title on four consecutive rows.

**Why.** The board and planners comment in refs ("re C5"). The manager and architect read ids. The memo is supposed to be one document in two renderings, and right now it is two documents.

**Fix.**
- **Shared helper.** Lift the numbering into `memoRefs(res, site, opt)` returning `{ref, src}` and call it from `renderMemo`, `answerAllowed`, `answerFunders`, `answerUnsure`, `answerMoney`, `renderClauses`, `renderLedger` and `paperDocument`. One source of truth, same order.
- **Screen display.** Every rule shows `<b class="ref">C5</b>` before its title, with the id kept as the secondary mono line it already is.
- **"Every line".** The "From" column becomes "F6 · S19" with the source linked once in the memo's Sources list; the full title stays in the link's `title`. That removes about 60% of the table's text.
- **Open-items table.** Gains a Ref column on screen as it has on paper.

### P1-6. The views and modes leak: Summary is not a summary, and Reader is not the paper
**What.**
- `answerMoney` writes `<details class="pf-lines" open>`, so the 20-row table is open in Summary, Detailed and Reader alike. The Summary tooltip says "the three answers and the massing".
- `setMode("reader")` hides `.memo-tools`, which holds the view switch, but never resets `state.view`. A browser that last used 3D preview opens Reader with `.answers` hidden (`app.css` line 765) and no visible way to get them back.
- The four big figures in `.pf-four` are a KPI-tile row, which DESIGN.md's "Don't build a dashboard" forbids.
- In manager mode Download PDF sits at the memo's foot.

**Why.** Reader mode is sold as "the memo alone, as on paper". It is neither the paper's order nor guaranteed to show the answers. Summary is the manager's projector view, and the projector shows a cost table.

**Fix.**
- **`applyModeToMemo`.** Set `.pf-lines` open only in architect mode, with the summary text "Every line, its rule and its source (20 lines)".
- **`setMode`.** For reader, call `setView("detailed", false)` before `applyModeToMemo`. Better still, give Reader the paper's section order: answers, open items, money lines, comparison, clauses, figures, ledger.
- **`.pf-four` becomes a schedule.** A four-row table with right-aligned figures in tabular numerals, laid out as the sum: Capital cost $54,114,027 / Funding (less) $41,591,718 / **Gap $12,522,309 · 23% of capital**, with NOI as the line that sets the debt.
- **Download PDF.** Once a run is on screen, mirror the button into the memo-tools row in manager and reader modes (one ink secondary button, right-aligned after the view switch). The footer keeps the rest.
- **Copy.** Fix "three answers" to "four answers" in the view-switch `title`s, the line 4714 status, the mode tooltips in `index.html`, and `MODES.manager`.

### P2-7. The guide and the cards ask the same questions, and the stage evaporates on Run
**What.**
- After stop 1 the Site card appears below the guide with every field (screenshot 7), including the Community Vision / transit Yes / No / Not sure that stop 4 asks again (screenshot 8).
- The status strip then sends the manager to the card: "The benchmark needs the Community Vision answer in the Site card."
- When the rules run, the stage's site card (parcel map, owner, the "not sure" list) and its programs card (each fund's terms and status, e.g. "2025 call cancelled Feb 2026") are replaced. Neither reappears in the memo. The programs' status reaches the reader only buried in a CHF finding.

**Why.** For the manager, two places to answer one question means doubt about which one counts. For the board, the most decision-relevant fact about a fund, that it has no open call, never gets a line of its own.

**Fix.**
- **`syncCards()`.** In manager mode keep the Site and Option cards hidden until a run exists. Stop 1's collapsed line gains "Every site field" (opens the card). Stop 4's answer controls stay the single place for those questions, and the Site card shows "answered at stop 4" beside them.
- **`renderMemo`.** Add a "Programs in view" row to the title block, from the E rules in `target_programs`: title, in force from, status. For example: "Community Housing Fund · between calls (2025 call cancelled Feb 2026)".
- **Site facts.** The site's owner and "not sure" fields join the FIG 01 caption, so the found site is still in the reading path after the stage goes.

### P3-8. Numbering collisions, and a red wash on a count
**What.**
- Badges "1" Site, "2" Option and "4" Export (`index.html` lines 73, 92, 131) sit alongside stops 1 to 7, stage 01 to 06, answers 01 to 04 and FIG 01 to 07.
- In manager mode, "4 Export" in the footer sits under "04 Does the money work?".
- Answer 03 takes the worst status's wash (`answerUnsure`: fail if any open item fails), and `<em>a named person</em>` is set in the fail ink (screenshot 11). Red lands on the words "a named person".

**Why.** DESIGN.md: "Don't put a status colour on a … background that carries no status." A count of open items is not a verdict, and putting it in fail red makes the whole top of the memo red on any site with one failing funder.

**Fix.**
- **Badges.** Drop the badges on Site, Option and Export outside architect mode, where the step bar that justifies them is shown.
- **`answerUnsure`.** Give the card no wash (plain panel) and set the verdict in Ink. Copy: "Seven open items. Each names who resolves it." The per-row pills keep the status.
- **Who / what split.** Ask the engine for a `who` field on each unsure item (`memo.py` / the ledger summary) so the table and the paper split "Who" from "What to do". The board can then see the allocation, for example "Manager 3 · Architect 1 · Both 1".

---

## 7. Persona red flags

### Sam: screen reader, keyboard only
- **The guided path is unlabelled at its first step.** The address box's only name is its placeholder ("998 E 19th Ave, Vancouver, BC"), which disappears on typing. The seven stop headers are `<button>`s with no accessible name, so Sam hears "button, button, button…" down the product's main path.
- **Funders are announced by id.** The four program checkboxes are named "bch.chf.eligibility", "bc.bcbuilds.eligibility" and so on.
- **The run is announced with a file path.** After Run the rules, the live status reads "Ran the rules as of 2026-11-15: R1, in 271 ms - wrote outputs/609-heatley-ave/2026-11-15T21-36-32/". Whether focus moves to the memo was not observed. If it does not, Sam is left in the rail with the answers somewhere to the right.
- **Rule ids are unexplained.** They appear as `<code title="…">`. The `title` attribute is not reliably announced, so the meaning of `f.rents` is lost.
- **The "Every line" table is noisy.** About 20 rows; the CMHC source link's full title is read four times in a row, and the links list fills with near-duplicates.
- **Stop 4 is about 40 tab stops** of Suggested / Mine before the eight questions. Each pair needs a group name that includes the figure ("Storeys: Suggested or Mine").
- **The 3D preview's axonometric (`renderPreview3D`) turns by pointer drag only.** Unlike the memo's FIG 01 3D view, it has no arrow keys and no text alternative.
- **The Leaflet map adds zoom controls to the tab order** inside a box labelled only "The parcel on a map". It needs a text line after it giving the parcel's area and dimensions, which the `dl` beside it already has.
- **What works.** The Yes / No / Not sure radio group with one tab stop, status written as a word, h1 then h2 answers, and the walkthrough's focus trap with Esc.

### The board member reading the PDF cold (a volunteer treasurer, printed in black and white)
- **Page 1, row 1.** "Not outright", decided by a rule marked "uncertain" (P1-4). They assume the tool is unsure whether the building is allowed.
- **The money row.** It points to "the memo on screen" (P0-2). The treasurer cannot answer "where does $12.5M come from?" at the meeting.
- **No glossary.** RGI, HILs, FSR, DCR, CD-1, SSMUH, TOA and "staff benchmark" appear undefined. A five-line glossary at the end of section 1 of `paperDocument` would cover every abbreviation the answers table uses.
- **Open items are named by statute,** not by the missing fact, with who and what in one cell (P3-8). They cannot see that the manager owns most of the list.
- **Placeholders are only half visible.** They are marked in the money table that the PDF lacks; on paper they surface only as a sentence ("Placeholders in use: Soft costs, Contingency…"). Soft costs and contingency are 35% of the hard cost, and a treasurer should see that as a line.
- **Fund status is missing.** Nothing on page 1 says the Community Housing Fund has no open call. A board voting pre-development money against a grant that cannot currently be applied for needs that sentence on page 1 (P2-7).
- **No "what this asks of the board" line.** The memo should not recommend, but it can state facts deterministically: "Before pre-development money: 4 open items, 3 with the manager; the funding gap is unlikely to close at 23%." That is formatting of existing verdicts, not a new calculation.

---

## 8. Three provocative questions

1. **If the memo is the product and the PDF is the memo the board reads, why is the screen the canonical rendering?** Build `renderMemo` from the same section model as `paperDocument`, the paper's order and refs, with the screen adding only interaction. Then "Reader" is no longer a mode; it is the document.
2. **Is "What is still unsure" an answer, or the memo's closing action list?** Answer 3 sits between "does it fit the funders" and "does the money work", and it is the only answer that is not a verdict. It could close the memo instead, as "Before the next decision", signed with names and dates, so the PDF ends on what people must do rather than on a fingerprint.
3. **Should the tool be allowed to suggest an option it already knows fails?** A candidate named "Funder-ready" that the fund's own rule rejects at this size is the clearest trust failure in the walk. Either the suggester checks its output against layer E before offering it, or the candidate names what it is ("the fund's mix, rounded"). Which of those does a deterministic tool owe its user?
