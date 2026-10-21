# Pitch outline for the mid review, Friday 23 Oct 2026

Eight minutes talking, two for the live run, the rest for questions. The demo is the argument;
keep the slides to the numbers the demo will show.

## 0. One sentence (10 s)

"I built a tool that tells a non-profit, before they spend money on design, whether a building is
allowed on their land and whether BC Housing would fund it, and shows its work."

## 1. The problem, from a real workflow (90 s)

- Where I saw it: feasibility work at practice, and in talking to the people who run church-land
  and society-led housing projects in Vancouver.
- The failure: the first drawing arrives before the first rule check. The checks that matter (zoning
  outright vs rezoning, the City's social-housing and family-unit policies, trees, and the funders'
  eligibility) live in different documents, owned by different people, read at different times.
- The cost: weeks of unpaid design, a scheme redrawn when a rule turns up late, or a project that
  simply stops. Nobody writes down which version of which rule they checked against.
- Why AI alone does not fix it: a chat answer is not citable, not repeatable and not dated. The
  firm needs the opposite of a guess.

## 2. What the tool is (60 s)

- Input: a site file and an option file (plain JSON, a page each).
- Output: a memo with three answers, a full ledger with the arithmetic and the clause for every
  finding, a massing in Revit from the same numbers, and a version stamp.
- Inside: a rule stack in five layers (district, province, City policy, design standards, funders),
  every rule dated and cited; a deterministic engine; no language model in the loop.

## 3. Live run (2 min) — see the script below

## 4. Why it is resilient (45 s)

- Better models do not make this unnecessary; they make the rule files easier to maintain. The
  value is the versioned, cited, local rule stack and the record it leaves, which no model ships.
- When a rule changes (the family-unit rule changes on Monday, 27 Oct), the tool shows the change
  and re-stamps the memo. That is the test the brief asks for: the same tool, a year on, still useful.

## 5. Evaluation (45 s)

- Typical: 998 E 19th Ave as approved. The tool reproduces the City's numbers: FSR 2.95 over 1.20,
  36% family units over 35%, 20 trees required against 17, $3,000 cash in lieu.
- Boundary: 280 m² vs 281 m² lots, 35.0% vs 33.3% family share, 400 m bus stop.
- Out of scope: SSMUH on an RM-1 site, a TOA exemption; the tool says why, not a wrong number.
- Repeated runs: byte-identical ledgers; 23 unit tests.

## 6. Users and the next seven weeks (45 s)

- Who tests it: a non-profit development manager, an architect who does feasibility work, a
  planner or funder reader. Sessions in weeks 3 to 6; the brief's permission rules apply.
- What changes after the sessions: the inputs they actually have, the questions they actually ask,
  and whether the memo earns trust in the room.
- By 10 Dec: more districts, the TOA map read automatically, a form instead of JSON, and the Revit
  script as a pyRevit button.

## 7. Ask (15 s)

"If you know a non-profit or an architect doing this work, I would like twenty minutes with them."

---

## Live run in the UI (2 min)

Start `python -m ffm ui` before the talk; the page opens with 998 E 19th Ave and the as-approved
option loaded. The script below has the same beats as the command-line one.

1. Set *Rules as of* to 2026-10-23 and press **Run the rules**. The three answers land in under a
   second; read them aloud: *Not outright. By rezoning: not yet confirmed.* · *Not yet confirmed.*
   · *Five open items, each with a named person.* Point at the stamp in the top bar.
2. In card 3, stop at the trees row (20 required, 17 left, $3,000) and open the Full ledger, Layer
   C, to click the by-law link.
3. FIG 01 and FIG 02 beside the answers: the grey outright box against the blue proposed one and
   the amber benchmark lines. Scroll to Export, press **Export to Revit**, then **Check Revit
   result**: FIG 03, the sheet Revit built from the same numbers, with the stamp in every element.
   (Run the pyRevit script on this run's massing.json beforehand, or open the 2026-10-23 run from
   *Open a past run*, which already carries one.)
4. Change the date to 2026-10-27, Run again, choose the earlier run under *Compare with…*: one
   rule, two version dates, a new stamp, in the *What changed* table.
5. If time: change 2-bed units to 20 in the form and Run: only the family-units row changes, to
   Fail, and the stamp does not. Then pick the *what-if* option and Run.

## Live-run script, command line (2 min)

1. `python -m ffm run --site sites/998-e-19th-ave.json --option options/998-e-19th-ave-as-approved.json --out outputs/demo --as-of 2026-10-23`
   Point at the terminal line: *allowed outright: no · by rezoning: not yet confirmed · funders: not yet confirmed*. Open `memo.html`.
2. Read the three answers aloud; stop at the trees line (20 required, 17 provided, $3,000) and click
   the by-law link to show the clause.
3. Scroll to the massing: the grey outright box (3 storeys, FSR 1.2) against the blue proposed
   (6 storeys, FSR 2.95) and the staff benchmark lines.
4. Switch to Revit, run the pyRevit script, pick `outputs/demo/massing.json`. The masses appear;
   click one and show the stamp in Comments.
5. Back in the terminal: `--as-of 2026-10-27 --previous outputs/demo/ledger.json --out outputs/demo2`.
   Open the new memo's *What changed* table: one rule, two version dates, a new stamp.
6. If time: run the *what-if* option. Trees go to pass, IRP goes to pass, BC Builds goes to pass,
   CHF stays uncertain until the owner confirms the lease — and the memo says exactly that.

## Likely questions, short answers

- *Isn't this just a checklist?* A checklist has no arithmetic, no dates and no record. This
  computes, cites and stamps, and the massing comes from the same numbers.
- *Who maintains the rules?* The person who maintains them today, by hand, in their head: the
  feasibility lead. The file format makes that work visible and shareable. Later, a model can draft
  rule updates from a by-law change for a person to approve.
- *Why Revit via a script?* The Revit MCP is read-only; a pyRevit script is what a firm can run
  today, and the geometry file is tool-neutral.
- *What about liability?* The memo is a screen, says so, and hands every judgement to a named
  person. It is designed to make the human check faster, not to replace it.
- *What is fake in the demo?* The red pine diameter and the setbacks are placeholders; the what-if
  option is hypothetical and labelled; everything else is from the City's referral report.
