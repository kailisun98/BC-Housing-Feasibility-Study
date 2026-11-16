# Design review of the tool, 15 Nov 2026

Three UX designers critiqued the tool in parallel, each with a lens (the first run and the manager's flow; the memo
and its information architecture; forms, states, errors, accessibility and the phone), from an evidence pack of
sixteen screenshots and a real walk through the seven stops on 609 Heatley Ave. Two architects then tested the tool
in the browser as they would on a job (one on options, the ledger, the drawings, the editors and the Revit handoff;
one on the manager-to-architect handoff, the PDF and an odd lot) and answered the designers' findings. The six files
here are their reports as written; the screenshot paths in them point at the reviewer's machine and are not in the
repository.

## What the review agreed on, and what changed the same day

Trust failures first, all fixed in the engine or the page:

- **Unanswered questions became fails.** A blank site control was printed as `site control 'None'` and failed the
  Community Housing Fund; a blank developer partner failed BC Builds. Now a blank is uncertain, with the question
  named (`ffm/checks.py`); no finding prints a Python `None` (`tests/test_blank_answers.py`).
- **The tool failed its own suggestion.** Four homes cannot split 30/50/20; the suggester now says so on the tier
  rows and in the "left to a person" list, and the fund's finding says the same thing (10 homes is the smallest
  count that can meet the mix).
- **"Allowed outright" where nothing was tested.** A district with no schedule in the rules (RT-3, DD, R1-1, CD-1) or
  a site outside the City of Vancouver read "Allowed outright" on screen and "✓ Yes" on page one of the PDF. Now the
  verdict is "not assessed", with the reason, and answer 3 carries an open item naming the architect
  (`ffm/engine.py`). The lookup reads the municipality from the point instead of assuming Vancouver, and warns.
- **The wrong parcel without a warning.** An address the City's list does not have (1805 Larch St) silently became
  the nearest parcel (1720). The lookup now flags the civic-number mismatch, the stage shows the found parcel on the
  map before "Use this site" ("Is this the parcel?"), and the button names the parcel it would take.
- **The drawings and the answers described different buildings.** Homes that do not fit the plate, and hand-placed
  blocks that overlap, now join answer 3 with the architect named, and the funding line says how many homes it
  counted against how many fit.
- **The handoff reached no one.** The architect's chip polled only the site on screen; an issued run on an unsaved
  site was unreachable. The chip now polls every site, opening the run loads its own site and option into the cards
  (unsaved), and the manager's note is pinned under the title block.
- **The PDF had no money lines.** A new section, "The money, line by line", with refs and placeholders marked.

Flow and clarity, in the manager's guide:

- The stage's option card showed "not set" beside a full suggestion; it now shows the suggestion with the manager's
  own figures over it until "Use this option", and blank envelope figures as "yours to enter".
- "Use this option" counted blank Mine rows as the manager's figures; now only typed figures count, and the status
  strip says what a blank envelope costs the run. The top bar's Run says why it has nothing to run instead of doing
  nothing, is marked disabled until a site and an option exist, and cannot run twice.
- The missing-schedule fact is said at stop 1 (under the district), at stop 3 (in the help line) and on the stage,
  not only in a fold's parenthetical; the "left to a person" line for the envelope names the architect.
- Stop 4's 21 rows are in four groups (envelope, homes, funder terms, drawing assumptions), the last two folded; the
  question keys read as words ("Storeys, height and floor area", not "Gfa M2").
- A corner lot asks which street is the front at stop 1 (the lookup's named street or the cross street); choosing
  swaps the frontage and depth and the massing follows.
- The guide keeps keyboard focus across its re-renders; the address box, the stop heads and the program checkboxes
  have accessible names; touch targets reach 44 px on a coarse pointer; the (i) buttons too.
- Answer 3 wears no status wash (a count is not a verdict) and splits who from what; "Every line" under the money
  answer opens by default only for the architect; Reader mode never lands in the 3D view; "three answers" reads
  "four answers" everywhere; a comparison never crosses sites; a run on a site that was never saved still gets its
  revision number.

## What the review raised and is still open

- The L-shape class and the 0.95 rectangle line (the parcel labels do not settle them; `evals/parcels/README.md`).
- The block editor has no snap, no oversize flag, and "to floor" drops a block on top of others; the boundary editor
  re-simplifies on every open and has no numeric entry; the Revit handoff carries the envelope but not the layout.
- The comparison has no money or drawings side by side; runs have no URL of their own; the past-run picker shows the
  rules date, not the run date.
- FIG 02 and FIG 05 state two heights for one building; FIG 01 draws the street at the bottom and FIG 03 and 06 at
  the top; FIG 01's lot is small inside 120 m of context.
- Setbacks are "drawings only" and no yard rule is checked; height, floor area and residential floor area do not
  follow storeys in the Option form.
- Save as… uses a browser prompt and does not warn before overwriting; a refresh loses the guide's state; a memo is
  never marked stale after its inputs change.
- No heritage rule; nothing asks what stays on the lot; the escalation index prints two values in one memo.
- Rule ids on screen against A1 refs on paper; Reader mode is not the paper's order.
