# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two primary users, served equally, with a third reading over their shoulder:

- **A non-profit development manager** deciding, before any money goes to design, whether a site
  and a building option are allowed and fundable. They read the memo, act on the open items, and
  carry it into conversations with the owner, the City and the funders.
- **An architect doing feasibility work** for that non-profit: runs options, needs the ledger with
  its arithmetic and clauses, the rule-derived massing, and the handoff into Revit.
- **A volunteer board** (and, at the review, planners or funder readers) who trust things that
  look like a careful memo and will not read a dashboard.

Situation: BC non-profit housing on church land or society-led sites in Vancouver, at the moment
the first drawing is about to be made. The checks that matter live in different documents, owned
by different people, read at different times; the cost of a missed rule is weeks of unpaid design
or a project that stops.

## Product Purpose

A deterministic feasibility screen. Given a site file and a building option, it answers three
questions in order, with the arithmetic and the clause for every finding:

1. Is it allowed? Outright under the zoning district, and by rezoning under the City policy that
   applies.
2. Does it fit the funders? BC Housing Community Housing Fund, BC Builds, with flags for CMHC and
   the predevelopment loan.
3. What is still unsure, and who resolves it? Every open item names the person and the document.

It also derives a massing from the same numbers (proposed against outright), puts it on an
annotated Revit sheet through a pyRevit script, and stamps everything with a version hash of the
rule set in force on the as-of date, so two memos can be told apart and a rule change shows up as
a change.

Success, confirmed 22 Oct 2026: practitioners in the user sessions trust the memo enough to act on
it and cite it; the tool reproduces the City's numbers on real cases and shows rule changes
honestly, as a record; a practice runs its own feasibility sites through it after the course.

## Positioning

A cited, dated, local rule stack that a feasibility lead can read and maintain, with no language
model in the loop: same inputs and rule set give the same memo, every time, and every number links
to the document it came from. A chat answer is not citable, repeatable or dated; a checklist has
no arithmetic, no dates and no record. Better models make the rule files easier to maintain; they
do not replace the record this tool leaves.

## Operating Context

- Inputs are plain JSON, a page each: `sites/*.json`, `options/*.json`. Rules live in
  `rules/*.json`, one file per layer (district, province, City policy, design standards, funders),
  every rule dated and cited.
- Outputs per run: `memo.md`, `memo.html`, `ledger.json`, `massing.json`, `massing.svg`,
  `diff.json`, under `outputs/<site-id>/<run>/`. The Revit script adds the model, the sheet
  exports and `ffm_revit_result.json`.
- Three ways to use it: the command line (`python -m ffm run`), the local web UI
  (`python -m ffm ui`), and the same page on GitHub Pages with the engine running in the browser.
- The Revit step runs on a Windows machine with Revit 2026 and pyRevit; headless through the
  pyRevit CLI, or interactively inside Revit.
- Documents the users already work with: City of Vancouver referral reports, the Zoning and
  Development By-law and district schedules, the Interim Rezoning Policy, the Protection of Trees
  By-law, BC Housing RFPs and design guidelines, BC Builds opportunity notices.
- Rituals: an ARCH 540 mid review (23 Oct 2026) and final review (10 Dec 2026) at UBC SALA; user
  sessions with practitioners in between; the demo move of running as of one date, then another,
  and comparing.

## Capabilities and Constraints

- Statuses are a fixed vocabulary: pass, conditional, fail, uncertain, not applicable, info.
  "Uncertain" is the honest outcome of a missing input or a judgement that belongs to a person;
  the UI offers "not sure" as a normal choice, never a checkbox.
- The engine (`ffm/engine.py`, `ffm/checks.py`, `rules/`) is pure standard-library Python 3.10+
  and stays dependency-free. The UI formats; it never calculates a rule. The web build loads the
  engine into Pyodide rather than reimplementing anything.
- Every number on screen comes from `ledger.json` or `massing.json`.
- Known placeholders are declared, not hidden: the red pine diameter, the setbacks in the option
  files, null rent tiers and accessible units; the what-if option is hypothetical and says so.
- Public repository, public data only. Nothing from a private client file; real practitioner
  sites are run locally and only shareable substitutes are committed. Anything built from the
  office Revit template stays local.
- No launching of Revit from the web server; the export is instructions plus a result check.
- Undecided: the TOA tier is read from the City's map by a person, not the tool; more districts,
  automatic map reading and a pyRevit button are planned for December, not promised.

## Brand Commitments

None beyond the UI brief (`docs/ui-brief.md`), confirmed 22 Oct 2026. The name is "First Read",
subtitled "a funding-fit memo for BC non-profit housing" (decided 23 Oct 2026 for the mid review; it
replaced "Lot by lot", which had replaced "Funding-Fit Memo" earlier that day); the document it writes
is "the memo". The voice is plain sentences: "not sure" rather than "N/A", buttons that say what they do.
No logo, no external identity to honour. The brief's visual direction (serif, sans, mono; paper
and ink; one accent; six status colours used only for status) is the committed world for the UI
and lives there, not here.

## Evidence on Hand

- The 998 E 19th Ave case (as approved by Council, 25 Jul 2024) from the City's public referral
  report and the Shape Your City page, in `sites/` and `options/`, with three committed runs under
  `outputs/998-e-19th-ave/` and a Revit sheet built from it (local only).
- Evaluation cases in `evals/cases.md` and 25 unit tests: typical, boundary, out-of-scope,
  repeated runs, version switch.
- The rule sources themselves, cited in `rules/*.json` with `verify` notes where a figure must be
  re-checked.
- Absent, and not to be fabricated: practitioner testimonials and credits (added after the user
  sessions, with consent), real client sites, pricing, adoption claims.

## Product Principles

1. Show the work. Every finding prints its numbers and links its clause; the memo is the
   product and the UI is a reading room for it.
2. Say "uncertain" rather than guess, and hand every judgement to a named person.
3. Date and stamp everything, so a rule change is visible and an old memo stays reproducible.
4. Keep the engine small, local and dependency-free; a firm must be able to maintain the rules by
   hand.
5. Nothing confidential in the repository, ever; permission before anyone's documents are used.

## Accessibility & Inclusion

Readers include a volunteer board and reviewers on a projector: the page must read at 1366 px
and print cleanly. Status is always written in words, never colour alone. No further
product-specific requirement has been established.
