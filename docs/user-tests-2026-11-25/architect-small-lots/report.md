# User test, 25 Nov 2026: architect, small lots

This is a simulated review: an AI role-play of an architect at a small Vancouver practice who does multiplexes, townhouses and 3 to 6 storey wood frame for non-profits. It is not a practitioner's opinion and should not be quoted as one. I ran my own server on port 8792 and worked in my own browser tab. Lots: 609 Heatley Ave (RT-3, corner, lane), 2475 E 5th Ave (R1-1, 10.1 m lot), 4250 Fraser St (C-2A). Runs made: `outputs/609-heatley-ave/2026-11-25T18-25-46`, `…T18-33-12`, `…T18-40-24`, `outputs/4250-fraser-st/2026-11-25T18-37-33`, `outputs/2475-e-5th-ave/2026-11-25T18-39-50`.

(Saved by the coordinating session from the reviewer's returned text: the harness does not let a subagent write files.)

## 1. Verdict

I would not use it on a real lot next week, except as a fast parcel and use-table lookup. The lookup, the yards and the use tables with their pages are good, and the clause table is the right idea. But the tool gets wrong the one question I most need it for on a small RT lot: what the Director of Planning can approve. It sends a scheme 5 m² over the outright FSR to rezoning, while the schedule it cites lets the Director go to 0.75 (1.00 for non-profit-secured housing). Answer 1 also contradicts itself on every lot I ran: "Outright: No" sits beside "By rezoning: Not needed · the option is allowed outright". And the ground-oriented plans, the new feature that matters most to my practice, place 2 or 3 of 4 homes on lots where four obviously fit. The editor can also delete townhouses from every floor when I step back the top floor. I can't sign drawings that start from these numbers until the discretion route and the floor-area reconciliation are fixed.

## 2. The flow as I walked it

**Home and How pages.** The four questions are clear and the "dated, cited" claim is what an architect wants to hear. Trust breaks within a minute, though: the home page says the engine "checks the option against 144 rules" and then "84 rules in six layers". How it works says "Five of the 144 rules", and my memo said "29 of 176 rules". How it works lists the districts as "RM-3, RM-3A, RM-4, the RM-5 family, RT-3, R1-1, the C-2 family and the RR rental districts", which is stale against the RT-4 to RT-11, RM-6 to RM-12, FM-1, M-1 and DEOD the tool now holds. The demo's open items are "seven" in one place, "eight" in another, and nine nodes in the lanes diagram. I also noted the line "the construction cost is a figure for two- to four-unit buildings": honest, and fine for my 4-plexes, but it is also applied to 6-storey C-2A.

**01 The site (Manager), 609 Heatley.** The lookup took under 5 s: RT-3, 566.7 m², 37.2 × 15.2 m, the parcel on a map. The front defaulted to Keefer St (the short side) with no reason given, while the help text says to find the front in "the address the City lists", which is Heatley. The lane offer, "its centre line about 3.9 m past the rear lot line. Use it", is the feature I wanted. After I clicked it, though, the 3.9 m vanished from the screen, and no field anywhere (Site schedule included) lets me type the surveyed distance. When I switched the front to Heatley Ave, the offer still read "a lane runs behind the lot", although the rear would then be the interior side line (seen once).

**02 What the lot takes, 609 Heatley.** "The plate the yards leave: 11.5 × 17 m, 196 m² · yards front 3.7, rear 16.1, sides 1.5 m". The rear is right: 20.0 m less the 3.9 m to the lane's centre line, s.3.1.2.17. But 15.2 − 3.0 = 12.2 and 37.2 − 3.7 − 16.1 = 17.4, so the stated plate loses 16 m². "Outright: 3 storeys, 340 m² (FSR 0.6), about 4 homes" sits directly above "Multiple Dwelling is a conditional approval use … not allowed outright". The 1.00 FSR for a multiple dwelling with 25% non-profit secured units (s.3.1.1.2), which is in the tool's own rule file, appears nowhere. The SSMUH line ("at least 4 homes … 6 if a prescribed frequent bus stop is within 400 m") is correct. I chose Ground-oriented ("Use it"), but the plan note underneath still said "beside one stair (a walk-up)".

**03 Run.** The run took 363 ms. Answer 1 read "Not outright: within what the Director of Planning may allow. No rezoning needed", then "By rezoning Not needed · the option is allowed outright and proposes no rezoning", then "Allowed outright; no rezoning is proposed or needed". The title block called it "Suggested, funder-ready", although 02 had labelled the candidate "Outright".

**Architect mode: schedules, drawings, editor.** The Site schedule has no front-street row and no lane-distance row. The Option schedule said "no plate known yet: give the site its frontage and depth" with both given; after a run it offered "floor area up to 587 m² … Use it instead of 345", which is FSR 1.04 on a 0.60 district, with no FSR mentioned. In the drawings, FIG 03 Overview says "level 3, no homes", while the L3 floor picker shows a three-bedroom and a two-bedroom. The 3B runs through all three floors at 4.2 m wide, and "1 one-bedroom did not fit". In the editor I widened the plate to 11.5 m, stepped back L3 6 m on the street side, tried to put the 1B on L3, used Suggest a grid plan, kept options A (9.44 × 12) and B (11.5 × 10), applied B and ran again. B still placed 3 of 4.

**Boundary editor.** I typed edge 1 as 36 m and clicked Use this boundary. The plan redrew, but the memo got no stale band until I also clicked "Set the site area to the drawn lot, 554.7 m²". The caption kept "equivalent rectangle 15.23 × 36.97 m".

**Compare.** Run 18:33 against 18:25: the rule diff is clear ("RT-3 outright floor space ratio Pass → Fail"). The pickers, though, list three runs all named "Suggested, funder-ready" (one of them another user's).

**Second and third lots.** 4250 Fraser (C-2A) and 2475 E 5th (R1-1) are described under section 3.

**Paper memo.** I read it in an iframe, as the architect who signs later. It runs to about 108,000 characters. Its plans are not stamped as unchecked.

## 3. Defects, ranked by harm

1. **The Director's discretion is misread in RT-3** (verified twice). Repro: 609 Heatley, Architect, Option schedule, Floor area 380 (FSR 0.67), Run the rules. A second path: the block editor, plate 11.5 × 10, Apply (FSR 0.61). Expected: "By the Director's discretion: possible", since s.3.1.1.1 allows up to 0.75, and `cov.rt3.outright_fsr` carries `max_fsr_conditional` 0.75 and `max_fsr_affordable_multiple_dwelling` 1.0. Seen: "By the Director's discretion No · another limit is exceeded beyond what the Director may allow", "Not outright: rezoning required", and the next step "Reduce the density or state a rezoning path". On a non-profit RT lot that turns a DP into a rezoning on paper.

2. **Answer 1 contradicts itself** (verified on all three lots). Repro: any RT-3, R1-1 or C-2A run with approval route Not sure. Seen: "Outright No · the building is a conditional approval use" and "By rezoning Not needed · the option is allowed outright"; the footer "Allowed outright; no rezoning is proposed or needed"; the figure "Allowed today, no vote needed", which by the home page's own glossary means outright. The comparison card then reads 18:25 as "Allowed outright: Yes, with conditions", while 18:25's own memo says No (seen once).

3. **Rules cited but not applied in RT-3.** The source line of A4 quotes s.3.1.2.11 ("the third storey must be a partial storey not exceeding 50% of the storey below"), yet the tool draws and passes three full 113 m² floors (9.9 m, three equal plates in FIG 02, FIG 04 and the 3D). Site coverage of 45% (s.3.1.2.8) is in the rule's params, but FIG 06 says "Site coverage … no schedule in the stack · info". "What the lot takes" omits the s.3.1.1.2 FSR of 1.00 entirely.

4. **The floor area tested is not the floor area drawn** (verified on three runs). The FSR test reads plate × storeys; the area schedule measures blocks. 609 R1: 340 m² tested against 307 m² gross. 609 option B: 345 m² (fails) against 262 m² gross. 2475 E 5th: 374 m² against 231 m². Two smaller arithmetic problems: on 2475 E 5th, "FSR 1.00 (374 m² over 373.5 m²) is within the outright maximum of 1.0" is false (374/373.5 = 1.001). On 609, FSR is taken on the recorded 566.7 m², while the tool's own polygon is 562 m², on which 340 m² is 0.605; nothing flags it.

5. **The plate box is understated** (verified on three lots). 609: 11.5 × 17 against 12.2 × 17.4 from the stated yards. 2475 E 5th: 7 × 20.5 against 7.7 × 21.5 (144 against 166 m²). 4250 Fraser: 20 × 23.5 against 21.1 × 24.4. On a 10 m lot, 0.7 m is a stair.

6. **The ground-oriented solver drops homes** (verified twice). 609, ground-oriented, 113 m² plates: 3 of 4 placed; a 3B over three floors at 4.2 m wide; the 1B "did not fit"; 10 m² spare on L2 and L3. At 11.5 × 10: still 3 of 4, with 21 to 31 m² spare a floor. 2475 E 5th, a 10.1 m R1-1 lot taking the standard 4-plex: 2 of 4 placed, 56% net to gross. The exit line reads "2 exits, 1 required · uncertain", and the open item "2 of 3 floors do not pass the exit clauses (Level 2: 2 exits, 1 required)". The advice "Move or add a core in Edit blocks" is given for a scheme with no core.

7. **The block editor loses townhouses** (verified twice for the drop; 2 of 3 times for the step-back). Repro: 609 run, Edit blocks, step back from L3 up, street side 6 m. The 3B and 2B vanish from every floor (Ground 2 → 1, L2 2 → 0). On another try only their L3 parts went; Remove then deleted the lower floors. Dragging the One-bedroom onto stepped L3 made a "58.5 × 1 m" block running off the plate and removed the 3B and 2B from all floors ("The home runs through its floors: the change is made on each of them"). Undo recovers it. The tracker counts every floor of a townhouse as a home ("Three-bedroom+ … 3 of 1 · 2 over"). No control lets me make a home span floors, and a one-floor 3B is flagged "under its 9.5 m minimum width", a flat rule applied to a townhouse.

8. **Corner lots invented** (verified twice). 4250 Fraser and 2475 E 5th are both "a corner lot", and the front question offers "E 27th Ave" and "Kamloops St". FIG 01 and the map show both mid-block. 609 Heatley's front picker in "Place the mass" offers "E Georgia St", which the lot does not touch.

9. **Lane distances not checked.** 2475 E 5th: "centre line about 0.4 m past the rear lot line"; a 6.1 m lane puts it at least 3 m away. 4250 Fraser: 5.9 m. Neither is questioned, and only RT-3 uses the figure.

10. **C-2A yield and the benchmark** (4250 Fraser, once). Outright: 13 homes on 2,099 m², 12 placed, 34% net to gross. The two stairs stand 5.8 m apart, so the separation fails on all six floors, while 74 m² is spare a floor and a 58 m² 1B "did not fit". "Benchmark: 6 storeys, 8 homes", FSR 3.00, by "CD-1 under the Interim Rezoning Policy", is a rezoning to less than the outright 3.50, and was offered first. Then "Benchmark would give this same building here (the same storeys, height and floor area)", which is false: 1,799 against 2,099 m². The staff benchmark band (19.9 to 21.3 m) is drawn on a scheme that proposes no rezoning.

11. **The paper memo** (once). There is no "First layout from the rules · not yet checked by the architect" stamp on the plans (none of 108,000 characters), while the screen shows it. Its figures follow unsaved on-screen edits: after my boundary edit, the 18:33 paper printed "Setback envelope 11.5 × 16 m" and "envelope 16.5", against the run's 17. On a ground-oriented plan it prints apartment boilerplate: "Unit depth 4.1 m either side of a 1.8 m corridor; core bay 7.0 m", "core: at the centre of every floor … (pass)", "a core 7 m wide read as two 2.2 m stairs".

12. **Live editor state leaks into the memo** (once). Before Apply, FIG 06 read "Floor space ratio 0.61 … fail" while answer 1 of the same memo read A3 Pass.

13. **The 02 plan note ignores the building type** (verified twice). After Ground-oriented "Use it", it still says "walk-up" (609) and "along a corridor" (2475).

14. **The boundary edit does not make the memo stale** (once), until "Set the site area" is clicked.

15. **Dates are in UTC** (verified twice). Both FIG 01 captions say "fetched 2026-11-26" on 25 Nov.

16. **Drawing content.** FIG 05 shows a blank third floor and no doors for "each home its own door". FIG 06 names only "KEEFER ST" on a corner lot, with no Heatley and no lane, and gives two lot areas (562 and 566.7 m²).

## 4. Interface problems, ranked

1. **Mixed vocabulary in answer 1 and at 02.** The pill says "conditional approval", the sentence says "Director's discretion", the drawing says "Allowed today". Pick one set of words.
2. **Runs can't be told apart.** Every run is "Suggested, funder-ready" (the title block prints it twice), and I can't name an option in Architect mode without "Save option as…". The compare picker also lists another user's 609 run.
3. **Drawings at the wrong scale.** FIG 01 draws a 15 m lot in a neighbourhood frame; the "noon" and "2 pm" shadow labels sit under "extent 15.2 m". The 3D view is framed on the block, so the building covers a few percent of it and the Program colours are unreadable. The floor-picker plans are huge with roughly 4 px text.
4. **The editor's ergonomics.** The canvas is about 1,175 px tall with a small plate in it, so I scroll between program and canvas. Step-backs hide in a disclosure. The "From" select is not exposed as a control. Pressing Enter in the edge table folds it. The editor stays open after Run. The options table lacks mix, area, net to gross and cost.
5. **Density at 02.** One card holds the lot reading, nine rule rows, a candidate switch, four figures, "All 22 figures" and ten questions. Under the figures, "D3", "A4" and "A3" mean nothing to a reader at that stage.
6. **The issue chip** shows runs issued by anyone in the outputs folder ("998 E 19th Ave · a run issued to you by the operator").
7. **Help text written for RT-3 everywhere.** It says "RT-3 takes off the distance to its centre line" on C-2A and R1-1 lots too.

## 5. What works and I trust

- The lookup: parcel, district and lot on three of three addresses, in seconds, with the parcel on a map to confirm.
- RT-3 yards: the 20.0 m rear less the lane's centre line (16.1 m), and the 1.5 m side over 15.0 m width with the 10% rule below it; the C-2A 2.5 / 1.5 m yards. All match the cited sections.
- The use tables quoted with pages. A shelter is "a question for the City" naming Group Residence and Social Service Centre; a C-2A clinic is "Health Care Office: outright (p. 3)".
- The SSMUH minimum (4, or 6 near a frequent bus stop), and "does not apply" in C-2A.
- C-2A: rental 3.50 with 0.35 FSR of non-dwelling use at the street, carried into the option (210 m², 10%).
- The clause table (proposed / permitted / the ask, section numbers, versions), UNVERIFIED tags, and the reproduce command with the fingerprint.
- Shadows: 21 m at 10 am PDT for 9.9 m at the equinox is right for Vancouver's latitude and daylight time, and it is labelled a first reading.
- Undo (it recovered the lost townhouses), the stale band after Apply, Keep as an option, DXF, project north.

## 6. Wish list (top five first)

1. **Read the Director's figures as the discretion route's limits (M).** RT FSR 0.75 / 1.00, height relaxations and the C-2A non-dwelling relaxation, used in "What the lot takes", the editor's capacity line and answer 1. Name the clause in the next step.
2. **A real ground-oriented mode (L).** Draw a townhouse over two or three floors, with its own stair and entry; one-floor accessible homes at grade; stacked-townhouse and 2-over-2 templates. The solver should place four homes on a 10 m R1-1 lot and on 609 Heatley, and refuse to call a 3B a flat.
3. **One floor area (M).** The FSR test, the title block and the area schedule should read the same gross with the by-law's exclusions listed, and say which lot area (recorded or polygon) governs, with a warning when the answer flips between them.
4. **Survey inputs in the Site schedule (S).** Lane centre-line distance, front street, flanking street, the neighbours' front yards (RT-3's average front yard), and grades; plus plausibility checks on lane distance and corner detection.
5. **Name an option and compare the building (S).** A name field in Architect mode; the comparison and the editor's options table to show plate, homes placed, mix, net to gross and cost per home.
6. RT-3's partial third storey and 45% coverage tested; the C-2 family's side yard beside an R district, read from the zoning map rather than left untested (M).
7. On paper: the "not checked by the architect" stamp, a drawing list with scales, an architect-acceptance block, and only the run's own data printed (S).
8. A 4.5 m commercial ground floor by default in C-2 (S).
9. Elevations with entries; a code site plan naming every street and the lane (S).
10. DWG or IFC out, and Revit without the pyRevit CLI (L).
