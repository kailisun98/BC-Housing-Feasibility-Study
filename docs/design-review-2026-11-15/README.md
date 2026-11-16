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

## The second pass, the same day (Kai: "all of the above")

- **States.** An edit to the site, the option or the money after a run puts a band over the memo ("The option changed
  after R1 … Run the rules again") and disables Issue until a new run; Save as… is an inline id field (and a name for
  an option) under the card, with the server's 409 for an id that exists; the browser asks before the page is left
  with unsaved work; the guide and the unsaved site and option live in the tab's session storage, and the blank stage
  offers "Resume where you were" after a refresh.
- **Setbacks are zoning.** The three setback fields are "read by a rule"; where no district yard rule tested them, an
  open item says so with the figures drawn and the architect named. Under the Building group the Option form derives
  the floor area the envelope allows at the storeys given and the height from storeys × floor to floor, each with a
  "Use it" button; what was typed stays until then.
- **One height, one orientation.** FIG 05 stands as tall as FIG 02 (the stated height), with the top floor level as
  a thin line; FIG 03, FIG 06 and the block editor draw the street at the bottom, as FIG 01 does.
- **The comparison for the meeting.** The Side by side card has a "Building and money" table (storeys, height, floor
  area, FSR, yards, homes asked and homes that fit the plate, family homes, capital, funding, gap, gap per home, gap
  as a share of capital, A less B), the two sections side by side, and the money in its one-line trade-off; the
  address bar names the run and the comparison (`?run=…&compare=…`) so a memo can be sent as a link; the past-run
  picker leads with the day the run was made; a comparison never crosses sites.
- **One citation system.** Every rule on screen carries its paper reference (A1, C5, F2) before its title: the
  clauses, the ledger, the open-items table (a Ref column) and the money table, where the source is a short link.
  Reader mode is in the paper's order: answers, comparison, clauses, massing, ledger.
- **Heritage and what stays on the lot.** Stop 1 asks whether the buildings on the lot stay (the Site card has the
  field); "not sure" is an open item for the manager and "yes" one for the architect, since the massing is drawn on a
  clear lot. A church owner adds "Heritage register and designation" with the architect named (the rules hold no
  heritage rule). The demo sites record that their lots are cleared.
- **The editors.** The block editor snaps a block's edges to the other blocks' edges and to the corridor faces, flags
  a unit drawn over or under the area the program carries, puts a block moved to another floor in the first free run
  (or says there is no room), and names its problems on the Apply button; the boundary editor reopens a drawn
  boundary exactly as saved, zooms the plan to the lot, has an edge table where a length can be typed from a survey,
  and offers to set the recorded site area to the drawn lot after "Use this boundary".
- **Revit.** The pyRevit script reads `layout.json` beside `massing.json` and builds a level per storey and a block
  per zone (named by floor, block and area); the lot's extent comes from its polygon, and the plan is dimensioned
  only when the lot has four sides. Not run against Revit in this pass.
- **The escalation index.** The money line names the quarter in force on the run date and the rule's newer
  observation, so the two figures in one memo are explained.
- **The manager's view.** The plans by program and the stacking (the architect's working drawings and the block
  editor) stay out of the manager's memo until the architect issues the run to them; a quiet card holds their place.

## Still open

- The L-shape class and the 0.95 rectangle line (the parcel labels do not settle them; `evals/parcels/README.md`).
- The corner lot's flanking street is still an interior side yard; the kept building's footprint is not drawn.
- FIG 01's lot is small inside 120 m of context.
- The Revit script's new levels and blocks have not been run against Revit.
