# First Read: test by Architect A (options, ledger, drawings, editors, comparison, files, Revit)

Tested 15 Nov 2026 in my own browser tab (tab-2) at http://localhost:8765/app.html?mode=architect&run=998-e-19th-ave/as-approved. The viewport was 2270 × 1205 CSS px, and screenshots come back at 800 × 427, so most of my evidence is read from the page text. Screenshots that matter are listed at the end. Screenshots and zooms often timed out because the pane was not in front, and I worked from the page text when that happened.

What my test left on disk: runs R4, R5 and R6 under `outputs/998-e-19th-ave/2026-11-15T21-49-31/`, `…T21-52-31/` and `…T21-56-08/`; R3 under `outputs/1010-expo-blvd/2026-11-15T21-53-55/`; and one new option file, `options/998-e-19th-ave-archa-5st.json`, written by the tool's own Save option as…. That option carries a block layout with three overlaps, so delete it before a commit. I did not save any site file. I did not edit any repository file by hand.

Two harness notes, not product findings: the embedded browser does not support `window.prompt()` or `window.confirm()`. To get past Save option as… and the site switch, I replaced both in the page so they returned an answer, then clicked the real buttons. The finding that matters is that the tool relies on native dialogs at all (see below).

---

## Part 1. The test, as I would use it on a job

### 1. The demo run, read for a client (998 E 19th Ave, R1, as approved)

What I would hand over as it is:
- Answer 01, "Not outright. By rezoning: yes, with conditions.", and the Interim Rezoning Policy line ("22.3 m … above the staff benchmark of 19.9 to 21.3 m … negotiated with staff"). That is how I would say it to a society's board.
- The trees finding (20 required, 17 left, 3 short, $3,000 cash in lieu). It gives the number, the clause and the person who acts.
- The "Every line" table under answer 04. Each figure has its rule, its source and a placeholder flag.

What I would not trust, or would have to recompute by hand:
1. **The drawings and the answers describe different buildings.** FIG 03 and FIG 04 say "69 of 105 units on 6 floors … Did not fit: 17 one-bedroom (989 m²); 19 studio (745 m²)". The four answers, the CHF grant ($171,211 × 105) and the rent roll all use 105 units and 8,299 m². Nothing in answers 1 to 4 mentions that a third of the program does not fit the plate the tool drew. On a real job, this is the first thing I would be asked about.
2. **Height disagrees across the sheets.** FIG 02 draws 22.3 m (the option). FIG 05 draws "6 storeys × 3.3 m = 19.8 m to the top floor level; the option states 22.3 m". The section and the elevation of the same building are 2.5 m apart. The note explains why, but the client sees two heights.
3. **Setbacks are not zoning in this tool.** Front, rear and side are marked "(drawings only)". FIG 06 says "placeholder, not from the schedule" for every yard, and "Site coverage … no schedule in the stack". For RM-1 that means the yards are not checked at all, which answer 01 does not say.
4. **The hard cost basis.** $4,693/m² is "average of Quadplex 01, Quadplex 02 and Townhouse" from a 2- to 4-unit catalogue. It is applied to a six-storey Part 3 building, including the 1,250 m² of non-residential space. It is cited and flagged in the ledger, but the answer card does not say that the base is a different building type. I would replace it before showing any gap.
5. **The ledger contradicts itself.** "RM-1 outright floor space ratio: Uncertain" for "FSR 2.95 exceeds the outright maximum of 1.2". That is a plain no, not an unknown. Escalation reads ×1.0292 with "BCPI 109.2 (2026-04-01)" in the money table, but `f.escalation_bcpi` in the clauses table reads "latest value 109.4 … released 2026-10-29", in a memo dated "rules as of 2026-10-23".
6. **The sheets are not oriented the same way.** FIG 01: "the plan is drawn with the street at the bottom". FIG 03 and FIG 06: "street at the top". Within one set, I would not issue sheets with flipped plans.
7. **FIG 01 is too small to read the lot.** The 75.6 × 37.2 m lot is a small rectangle inside 120 m of OSM context (screenshot 2). The plan's job is the lot, its yards and the envelope; the context should be the background.

### 2. Change the option, run, compare with R1

I changed the id to `998-e-19th-ave-archa-5st` and set storeys to 5, studios from 30 to 18 and the front setback from 3.7 to 6.0 m. Height and GFA did not follow storeys: after storeys = 5 they still read 22.3 m and 8,299 m². **I had to compute GFA by hand** (1,383 m² × 5 = 6,915), residential GFA (6,915 − 1,250.4 = 5,664.6) and a height (18.8 m). The tool knows the plate (it draws it), yet it makes me do the multiplication. Ctrl+Enter and the top-bar Run both work. The run took 331 ms and wrote `outputs/998-e-19th-ave/2026-11-15T21-49-31/` as R4.

The result:
- Answer 01 dropped the Interim Rezoning Policy condition, because 18.8 m is inside the benchmark. Correct, and the reason is clear.
- Money: the gap went from $12,522,309 (23%) to $8,066,558 (18%).
- FIG 03: "51 of 93 units … Did not fit: 2 two-bedroom; 31 one-bedroom; 9 studio". **42 of my 93 units do not fit**, and the answers still price and fund 93.
- The 6 m front setback reached FIG 01 and FIG 06 ("Setback envelope 69.6 × 25.2 m"). No rule read it, so the comparison never mentions it.

Compare with R1 (screenshot 3). The Side by side card gives:
- one line: "93 units against 105, 5 storeys against 6, 18.8 m high against 22.3, 6,915 m² of floor area against 8,299";
- an answers table with four rows: Allowed outright, By rezoning, Fits the funders, Open items;
- "1 of 21 rules read differently" (IRP Conditional → Pass);
- a second table, "What changed between the two options", with seven rows of "numbers changed".

**It is not what I need to argue a trade-off in a meeting.** The meeting is about "we lose a storey and 12 homes, we gain the benchmark and $4.5M of gap". The comparison has **no money row at all**: no capital cost, gap, gap per home ($119k against $87k, which I worked out by hand), grant, or cost per m². It has no "units that fit the plate" row (51 against 69). It has no setbacks. It has no drawings side by side: no section of A over B, no stacking A beside B. The two rule tables repeat each other.

Smaller points:
- The past-run picker reads "R4 · 2026-10-23 · Arch A test… · 2026-11-15T21-49-31". The date shown is the rules date, not the day I ran it, and the run is named by a timestamp folder.
- The browser URL stayed at `?run=998-e-19th-ave/as-approved` through R4, R5 and R6, so I cannot send a colleague a link to R5.
- Today is 15 Nov, but "Rules as of" stayed on 2026-10-23 from the demo, and every new run read October rules without saying so near the button.

### 3. Edit blocks on FIG 03

The editor opens in place with floor buttons (Ground, L2 to L5), "Add a block…", the plate as a canvas, "Apply to the option" and "Back to the solver's" (screenshots 4 and 5). What I did and what happened:

- **Move:** I dragged a two-bedroom on L4 about 4 m left into the core. After the debounce, the status read "Fail: Core (stairs, elevator) and Two-bedroom overlap on level 4" and "Fail: Corridor and Two-bedroom overlap on level 4". Those are my words, and good. The block also moved about 0.2 m down: there is no snap to the unit module or the grid line, so a small hand wobble becomes a corridor overlap.
- **Resize:** I pulled the right handle. The selection line read "Two-bedroom · 12.8 × 9.04 m, 116 m²". **Nothing flagged a 116 m² two-bedroom**: the engine checks only undersized units. The program line still read "26 two-bedroom 2,070 m²", so the resize did not reach the areas.
- **Move to another floor:** the "to floor" select (sent L4 → L3) keeps x and y, so the unit lands on top of two three-bedrooms and the core. The result was three Fails (screenshot 6). I would expect it to drop into the first free run, or at least to be told where the room is on that floor.
- **The summary line ignores the geometry:** "51 of 93 units placed … · 2 rules hold, 4 conditional" sat right under three Fails.
- **Apply to the option** accepted a layout with three overlaps without a question: "69 blocks on 5 floors written into the option as layout.zones."
- **Run again (R5):** FIG 03 is titled "PLACED BY HAND" and lists "broken: Core (stairs, elevator) and Two-bedroom overlap on level 3" and the two others. **Answers 1 to 4 do not mention them**: "Three open items", the same as before. So the engine tells me what broke in my words, but only on the sheet. The memo I would issue says nothing.
- After Save option as…, the Option form shows nothing that tells me this option carries hand-placed blocks, broken ones included.
- The "to floor" select was not found by the accessibility search (`find "to floor"` returned only the label text), so I could reach it only by coordinates.

### 4. 1010 Expo Blvd, as permitted

I switched the site in the Site card (the site's options load with it) and ran. This was R3 on that site, 537 ms.

- **The run was silently compared against the other site.** The strip read "R3 against a new revision, As approved by Council, 25 Jul 2024: 7 statuses differ". The title block read "COMPARED WITH: A NEW REVISION, As approved by Council…". The Side by side card set the 29-storey Expo tower against the 998 E 19th six-storey, while the Compare picker read "Nothing" (screenshot 7). The comparison from my previous site carried over to a different site.
- **Answer 01 reads "Allowed outright."** for a 29-storey, 88.45 m tower on a CD-1 site. The site file's notes explain that this is an engine limitation ("no CD-1 outright schedule"), but the answer card states it as a finding.
- **Answer 04 reads "Unlikely. The gap is $151,374,523, 100% of the capital cost."** The option has no unit mix (FIG 03: "0 of 0 units on 29 floors", every level "spare"), so rent, debt and grant are all zero. The honest verdict is "not computed: no units in the option", not "unlikely".
- **FIG 01 and the polygon** (screenshot 8): "Lot from the City's parcel polygon: irregular, 85 corners, 2,690 m² (recorded site area 3,908 m²) … plate box, the largest rectangle inside it, 31.5 × 27.5 m, dotted". FIG 02 adds: "the FSR uses the recorded area, the plan the polygon. Check which is the development site." I like that sentence. But the lot is again small inside 150 m of context, and the dotted plate box is hard to see at that size.

**Edit boundary:**
- **The boundary changes before I touch it.** Opening the editor turned the 85-corner parcel into "16 corners · 2,676 m²". Simplification alone changed the area by 14 m².
- **The handles are crowded.** The editor does not zoom to the lot: 16 handles and 16 midpoint squares sit inside about 130 × 100 CSS px. The SE corners are 1 to 3 screen px apart, so I could not grab the one I meant with confidence.
- **Drag and add work.** I dragged the east corner out, and the area changed live (2,938 m²). I clicked a midpoint square and got 17 corners.
- **Use this boundary:** "boundary is the lot: 17 corners, 2,936 m², shape irregular; the masses stand in the 31.5 × 27 m plate box." FIG 01 became "BOUNDARY DRAWN BY HAND" at once (screenshot 9). The Site area field still read 3,908, and nothing offered to set it to the drawn 2,936. The answers above the figures were still R3's, computed on the parcel, with no stale marker: the sheets were already drawing a lot the memo had not read.
- **Reopening drifts again.** I reopened to find Back to the parcel and my 17-corner drawn lot showed as "13 corners · 2,939 m²". Each open re-simplifies. A boundary I typed from a survey would not survive two round trips.
- **There is no numeric entry.** I cannot type an edge length, a bearing or a coordinate from a survey plan. For a survey-driven lot, drag-only input is not a boundary tool.
- **Back to the parcel** works: "Back to the parcel polygon: 2,690 m². Run the rules to make the memo from it."

### 5. Save option as…, reopen, Export

- **Save option as…** calls `window.prompt()` (app.js line 1106). In this browser that threw, and the page showed the generic crash banner: "Something went wrong: prompt() is not supported.. Reload the page; saved sites, options and runs are files and are kept." (double full stop in the original; screenshot 10). In a normal browser it would be a native prompt that does not show the cleaned id and does not warn before overwriting (UX-3 P1-6 says the same). With the prompt answered, it wrote "Saved options/998-e-19th-ave-archa-5st.json".
- **Reopen from the picker:** I switched to as-approved (storeys 6), then back to mine. Storeys 5, height 18.8, GFA 6,915, front 6, studios 18 all came back, and FIG 03 kept "PLACED BY HAND". The round trip works. When I later came back to 998 E 19th Ave, the picker opened my test option first rather than the as-approved one.
- **Export to Revit:** this run's absolute `massing.json` path with a Copy button. The four PowerShell lines are already filled with this run's folder, `FFM_TEMPLATE` is commented out and optional, and `--revit=2026` comes with the instruction to use the year `pyrevit env` reports. There is an "Inside Revit" fallback and "Check Revit result". That is clear, and I could follow it on Monday.
- **What arrives in Revit:** `massing.json` (I read the R5 file) carries `lot`, `envelope`, two `masses` (proposed and outright, each with footprint, plate size, storeys, floor-to-floor, height, GFA, FSR and `derived_from`), trees and warnings. The script builds two masses, floor plates, model lines for the lot and envelope, three views, annotations and sheet FFM-01. It does **not** carry the program: `layout.json` (the blocks I placed by hand, unit types per floor, core, corridor) is written beside it, but nothing takes it into Revit. Levels per storey are not created (the script finds the template's lowest level). In the script, the lot dimensions index `lot[0]` to `lot[3]` as front-left, front-right and so on (lines 540 to 549). I did not run Revit, but on an 85-corner or 17-corner lot like Expo those four points are not the lot's extremes, so the plan dimensions are probably wrong there.
- **Could I take this into Revit on Monday?** For the envelope and the two masses, yes, and that is useful for a shadow study and the rezoning section. For the layout, no: I would redraw FIG 03 by hand.

### 6. Things a real job needs

- **A site outside Vancouver (tested).** On the 998 site I set Municipality to "City of Burnaby" and Zoning district to "RM3", and ran (R6). **Answer 01: "Allowed outright. By rezoning: yes, with conditions."** (screenshot 11). The Vancouver Protection of Trees By-law 9958 still applied, the rezoning path still read "CD-1 under the Interim Rezoning Policy for Social Housing", and the RM-1 rules went quietly to "Not applicable". The municipality field is read by nothing. An unknown district gives a green "Allowed outright". Of everything I found, this is the most dangerous output: a manager in Burnaby would take a green answer to a board.
- **Mixed-use ground floor (seen in the demo).** Non-residential GFA is an input. FIG 03 puts non-residential on the ground floor facing the street, then says "Some of it had to go above the ground floor: the ground plate is too small for the brief". The stacking shows non-residential, amenity and services on Level 2. That is honest, but it was not my design intent, and no control says "ground floor only, at this depth".
- **Two buildings on one lot, and a lane (looked for).** The option has one storeys, one height and one GFA. The massing places one plate at "the street corner". There is no second mass, podium or tower. A lane exists only in the site's prose notes ("a lane behind"); no field says which side is a lane, so "services away from the street" cannot know where the lane is.

---

## Part 2. Feedback to the three UX designers

### Your P0 and P1 issues, one by one

**UX-1, first run (manager's flow)**

| Issue | My view | Why, from my test |
|---|---|---|
| P0-1 The tool fails its own suggestion and reads "Not sure" as "no" | **Agree** | I did not run the guide, but I hit the same failure in architect mode. The ledger calls a plain exceedance "Uncertain" (FSR 2.95 against 1.2), and Expo's empty unit mix becomes "Unlikely, 100% gap". When the tool's status words do not mean what they say, I have to re-check every row. |
| P0-2 An incomplete option runs and draws a building nobody entered | **Agree** | Same pattern on my side: FIG 05 draws 19.8 m when the option says 22.3 m, and Expo draws 29 floors of "spare". A drawing the inputs did not ask for is worse than no drawing. |
| P1-3 The stage contradicts the rail | **Not my problem** | Manager mode only; I never see the stage. |
| P1-4 The lookup result never reaches the stage | **Not my problem**, with one note | The parcel check matters to me too: on Expo the City's ring is 2,690 m² against 3,908 m² recorded. Showing the ring before "Use this site" is right. |
| P1-5 "No RT-3 schedule" is in a parenthetical | **Agree, and it is worse than you found** | With no schedule for a district, the engine does not just stay quiet: it answers "Allowed outright" (Burnaby RM3, and Expo CD-1). Saying it at stop 1 is necessary, and the engine must also stop calling it allowed. |

**UX-2, memo and information architecture**

| Issue | My view | Why |
|---|---|---|
| P0-1 Fails the funders on figures it chose | **Agree** | Same root as UX-1 P0-1. |
| P0-2 The PDF has no money lines | **Agree** | I did not print the PDF, but "Every line" is the part of the screen I would hand a funder. If the paper drops it, the gap is uncited exactly where the board reads it. |
| P1-3 Four "left to a person" lists, four counts | **Agree, and there is a fifth** | FIG 03's "Did not fit: 42 units" and "broken: … overlap on level 3" never reach answer 03. The architect's open items live only under the drawings. |
| P1-4 The memo contradicts itself | **Agree** | Confirmed both: "Uncertain" for an exceedance, and BCPI 109.2 against 109.4 in one memo. Add FIG 02 against FIG 05 on height. |
| P1-5 Rule ids on screen, A1 refs on paper | **Agree** | I would also want the A1 refs on the sheets (FIG 06's table, the FIG 03 rule list), so a planner's "re C5" reaches the drawing too. |
| P1-6 Summary is not a summary; Reader is not the paper | **Partly not my problem** | Your fix keeps "Every line" open in architect mode, which is right for me. I have no view on Reader. |

**UX-3, forms, states, accessibility**

| Issue | My view | Why |
|---|---|---|
| P0-1 The guide drops keyboard focus | **Not my problem, in principle agree** | I did not use the guide. The same weakness shows in the block editor: the "to floor" select was not findable by name, so I drove it by coordinates. |
| P0-2 Stop 5 disabled with a false reason; two Run buttons | **Not my problem** | Architect mode has one Run, and it always ran. |
| P1-3 Numbers silently become "not sure" | **Agree** | GFA, height and setbacks are `type=number`. If I paste "6,915" from a spreadsheet and it becomes a blank, the engine reads it as uncertain. I did not try it, but those are the fields I copy from elsewhere. |
| P1-4 Errors far from their cause | **Agree** | The block editor's Fails print under the canvas, below the fold on a laptop. The Save option crash banner prints at the top of the page, away from the button. |
| P1-5 "not given" and 'None' blame the wrong person | **Agree** | Expo's "Unlikely, 100% gap" is the same failure: a missing input reported as a verdict. |
| P1-6 Unsaved and stale states invisible; `prompt()` for Save as | **Strongly agree** | I hit both. After Use this boundary, the figures drew a 2,936 m² lot while the answers above were still R3's, with no stale band. Save option as… crashed on `prompt()`. Add a third case: a comparison left over from another site (Expo against 998), with the picker reading "Nothing". |

### What you missed that matters to an architect

1. **The drawings and the answers are two different buildings.** (Screenshots 2 and 3; R1, R4, R5.) The layout solver places 69 of 105 (demo) or 51 of 93 (my option), and the answers, money and grant use the full count. Hand-placed overlaps ("broken: …") stay on FIG 03. None of you read the drawings against the answers, and that is the cross-check an architect is paid for.
2. **The municipality is not read; an unknown district is "Allowed outright".** (Screenshot 11, R6 Burnaby RM3; Expo CD-1.) This comes before any copy fix: the deterministic engine gives a confident green answer outside its coverage.
3. **Setbacks are "drawings only".** (Option form; FIG 06 "placeholder, not from the schedule".) Yards, coverage and envelope are zoning. Marking them drawings-only tells the manager they do not matter to "Is it allowed?".
4. **The option does not derive itself.** I typed storeys = 5, and GFA and height stayed at the six-storey figures until I did the arithmetic. A deterministic tool that knows the plate should offer storeys × plate = GFA, with my override.
5. **The comparison has no money and no drawings.** (Screenshot 3.) The trade-off a board decides is homes against gap; the table has neither.
6. **Comparisons carry over to another site.** (Screenshot 7.) Expo R3 was compared with 998 E 19th R1 and labelled "a new revision".
7. **The editors are not precise enough to hand to a client.**
   - Block editor: no snap; moving to another floor drops the unit on top of others; no oversize flag; resizing does not update the program areas; Apply accepts Fails.
   - Boundary editor: it re-simplifies on every open (85 → 16 corners, 17 → 13), the area drifts (2,690 → 2,676 → 2,936 → 2,939 m²), it does not zoom to the lot, there is no numeric survey entry, and it does not offer to update the site area.
8. **Run identity and the URL.** The past-run label shows the rules date, not the run date; the run is named by a timestamp; the URL never changes from `?run=…/as-approved`; "Rules as of" stays on the demo's date. I cannot cite or share "R5" from the address bar.
9. **The sheets are internally inconsistent.** FIG 01 has the street at the bottom while FIG 03 and FIG 06 have it at the top. FIG 02 is 22.3 m and FIG 05 is 19.8 m. These are the things a reviewer circles in red.
10. **The Revit handoff stops at the envelope.** Two masses and floor plates arrive. The layout (`layout.json`) and per-storey levels do not, and the lot dimensions in the script assume a four-corner lot.

### My top five changes, in priority order

**1. Make the answers read the drawings: a fit check that reaches answers 01 and 03.**
*What it would let me do:* hand over a memo whose four answers describe the building on the sheets, without auditing FIG 03 against answer 04 by hand.
*The change:*
- The engine adds one deterministic check to layer D, `layout.fit`, which reads `layout.json`. Units placed against units in the option, `shortfall`, `geometry` (overlap, outside, undersized, oversized), and plate against plate cap become a finding: Pass, Conditional for a shortfall, Fail for broken geometry.
- It appears in answer 03 with a person. Copy: "Architect: 42 of 93 homes do not fit the 69.6 × 19.87 m plate at 5 storeys (31 one-bedroom, 9 studio, 2 two-bedroom). Add a storey, deepen the plate, or reduce the program; the money below counts all 93."
- With hand-placed blocks: "Architect: the hand placement has 3 overlaps on level 3 (core, corridor, three-bedroom). Fix them in Edit blocks before issuing."
- Answer 04's Funding line says which count it used: "105 homes as entered; 69 fit the plate".
- No language model; it is arithmetic over files the run already writes.

**2. Gate on coverage: never "Allowed outright" for a place or district the stack does not cover.**
*What it would let me do:* use the tool in Burnaby, Surrey or on a CD-1 site without it lying, and know at once what I must check by hand.
*The change:*
- Rules in layers A and C carry `jurisdiction: "City of Vancouver"`, and the site's municipality is matched before any rule applies. Unmatched rules are listed "Not applicable: written for the City of Vancouver; this site is in the City of Burnaby."
- When no outright schedule matches the district, answer 01's verdict becomes "Not tested outright." in the Uncertain ink. Copy: "Not tested outright. The rules have no schedule for RM3 in the City of Burnaby (or for this CD-1 by-law). Architect: read the district schedule; the envelope, yards and height here are your figures, not a check."
- The same sentence opens answer 03 with the architect named. CD-1 sites get the same treatment until a CD-1 by-law is encoded.

**3. A comparison built for the meeting: money, fit and drawings, one site at a time.**
*What it would let me do:* argue "one storey less, 12 fewer homes, $4.5M less gap, inside the benchmark" from one card, with the sections side by side, without a calculator.
*The change:*
- The Side by side card gains a "Building and money" table above the rule rows. Each row shows A, B and the difference: Storeys; Height; GFA; FSR; Front, rear and side yards; Homes asked; Homes that fit the plate; Family homes (2-bed+, %); Capital cost; Funding; Gap; Gap per home; Gap as % of capital; Open items. Every figure comes from the two ledgers and pro-formas, with the money rows citing their F refs.
- The one-line trade-off includes money. Copy: "A, R4, against B, R1: 93 homes against 105 (51 against 69 fit the plate), 5 storeys against 6, 18.8 m against 22.3, gap $8.07M against $12.52M ($87k against $119k a home)."
- Below it, "Drawings side by side": FIG 02 with both sections overlaid in two inks on one height scale, and FIG 04 stacking A beside B.
- Compare with… lists only runs on the same site. Switching site clears the comparison and writes "Comparison cleared: R1 is on another site". The title block never says "a new revision" for a run from elsewhere.
- Each run gets its own URL (`?run=998-e-19th-ave/2026-11-15T21-52-31&compare=…/as-approved`, pushed with history), so "R5 against R1" is a link I can email. The picker label leads with the date it was run: "R5 · run 15 Nov 2026 · rules as of 23 Oct 2026 · Arch A test…".

**4. Let the option derive its own numbers, and treat setbacks as zoning.**
*What it would let me do:* test five options in ten minutes by changing storeys or yards, without redoing GFA, residential GFA and height by hand, and know when a yard is not checked.
*The change:*
- In the Option form, GFA, residential GFA and height get the guide's Suggested | Mine pattern, with the arithmetic and its source on the Suggested side. Copy: "Suggested 6,915 m² = plate 1,383 m² × 5 storeys (massing) · Mine". The same for height: "Suggested 18.8 m = 5 × 3.3 m + 2.3 m roof (placeholder)". Changing storeys or setbacks updates the Suggested values live; Mine stays put and is marked "yours, not the plate's".
- Setbacks change their mark from "drawings only" to "read by a rule" and get a check (`cov.<district>.setbacks`, the check `district_setbacks` that already exists for confirmed schedules). Where the stack has no yard rule, the finding is Uncertain, not silent. Copy in answer 01: "Yards not checked: no RM-1 yard rule in the stack; front 6.0, rear 6.0, side 3.0 m are placeholders."
- FIG 05 and FIG 02 draw one height. FIG 05's "to the top floor level" line becomes a dimension inside the elevation, not a second building height.

**5. Editors precise enough to issue from, and a handoff that carries them into Revit.**
*What it would let me do:* place a real unit plan and a surveyed lot in the tool, apply them only when they are sound, and open them in Revit as levels and blocks instead of redrawing FIG 03.
*The change:*
- Block editor:
  - Drags snap to 0.1 m and to the unit module (the block's own width) along the run; the y position snaps to the corridor face.
  - "to floor" places the block in the first free run on the target floor, or says "No room on L3: 19 m² spare, the unit needs 80 m²".
  - The selection line flags oversize against the program. Copy: "Two-bedroom · 12.8 × 9.04 m, 116 m²: 36 m² over the 80 m² the program carries".
  - Resizing updates the program areas.
  - With Fails present, Apply becomes "Apply with 3 problems", and the strip says "Applied with 3 overlaps on level 3; the memo will list them as open items."
  - The Option card's summary line gains "· blocks placed by hand (3 problems)".
- Boundary editor:
  - On open, the view zooms to the lot's bounding box plus 5 m.
  - The parcel's own vertices are kept, and "Simplify (85 → 16 corners, −14 m²)" is an explicit button, not automatic. A drawn boundary reopens exactly as saved.
  - A side table lists each edge with length and bearing, editable, so a survey can be typed.
  - After "Use this boundary", the strip offers "Set the site area to the drawn lot, 2,936 m²", which changes the recorded area only on click and cites "boundary drawn by hand".
- Stale state: any change after a run puts a band over the answers: "The site or option changed after R3: the figures show the new lot, the answers do not. Run the rules."
- Revit handoff:
  - `massing.json` gains a `levels` list (one per storey at floor-to-floor) and a `zones` list per level taken from `layout.json` (block, x, y, w, d, accessible). The pyRevit script creates the levels and one mass floor or generic block per zone, named "L3 · 2b · 80 m²".
  - Lot dimensions are taken from the bounding box, not `lot[0..3]`.
  - The Export panel says which of these the current run carries. Copy: "This massing carries 5 levels and 69 placed blocks."

### Things better than what I use today; keep them in any redesign

1. **Every figure carries its source, and a placeholder says it is one.** "Every line" names `f.soft_costs`, links the source, marks "PLACEHOLDER 25% of hard cost", and dates the index ("BCPI 109.2 (2026-04-01) over 106.1 (2024-07-01)"). My office's feasibility spreadsheet has none of this. Do not hide it behind a "simple" money card, and keep it open in architect mode.
2. **Findings are written in the words of the referral report and the site meeting.** "Height 22.3 m is above the staff benchmark of 19.9 to 21.3 m. The policy sets no maximum, so the number is negotiated with staff." "Core (stairs, elevator) and Two-bedroom overlap on level 3." "Did not fit: 31 one-bedroom (1,804 m²); more storeys, a larger plate or a smaller program." "The FSR uses the recorded area, the plan the polygon. Check which is the development site." These are the sentences I would write myself. Keep sentences, not badges, and keep the named person.
3. **The run is reproducible and lives in files.** Save option as… writes a JSON I can diff and re-run from the command line. Each run is a folder with the ledger, the layout, five SVG sheets and a `massing.json`. The Revit panel gives the exact PowerShell with this run's absolute paths. "What changed between the two options" lists rule by rule what moved and why. That is the audit trail a planner or funder asks for, and it should stay exactly this plain.

---

## Screenshots

All under `C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\`

1. The demo in architect mode, first view (four answers): `mcp-Claude_Browser-blob-1794804465755-h00wkl.jpg`
2. The demo, FIG 01 plan (lot small in context) and FIG 02 section: `mcp-Claude_Browser-blob-1794804500772-7jg42e.jpg`; zoom `mcp-Claude_Browser-blob-1794804534161-pma0ew.png`
3. Side by side, R4 (my 5-storey option) against R1; no money row: `mcp-Claude_Browser-blob-1794804617037-dralfz.jpg`
4. Block editor open, ground floor: `mcp-Claude_Browser-blob-1794804630255-exn56d.jpg`
5. Block editor, L4 before the edits: `mcp-Claude_Browser-blob-1794804643846-df62rq.jpg`
6. Block editor, the resized two-bedroom moved to L3 over the core and the three-bedrooms: `mcp-Claude_Browser-blob-1794804729110-bozo03.jpg`
7. 1010 Expo Blvd R3 compared with 998 E 19th Ave R1 ("a new revision"), "Allowed outright": `mcp-Claude_Browser-blob-1794804853155-okkmal.jpg`
8. Expo FIG 01, the parcel polygon and the plate box, and FIG 02: `mcp-Claude_Browser-blob-1794804867423-7d562m.jpg`
9. Expo after Use this boundary ("BOUNDARY DRAWN BY HAND", 17 corners, 2,936 m²): `mcp-Claude_Browser-blob-1794804922275-w87dwl.jpg`
10. Save option as… crash banner ("prompt() is not supported"): `mcp-Claude_Browser-blob-1794804768917-g80l2n.jpg`
11. Burnaby RM3 test (R6): "Allowed outright. By rezoning: yes, with conditions.": `mcp-Claude_Browser-blob-1794804979691-pq26rf.jpg`
