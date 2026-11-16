# Evidence pack: First Read, the tool (ffm/ui/index.html + app.js + app.css), captured 15 Nov 2026

The tool is the web app at `ffm/ui/` in the repository `C:\Users\kaili\OneDrive - UBC\Desktop\M.Arch\02_Classes\ARCH 540\02 A2\BC Housing Feasibility Study`.
It is served locally at http://localhost:8765/app.html (python `ffm/ui/server.py`) and publicly at
https://kailisun98.github.io/BC-Housing-Feasibility-Study/app.html (static build, engine in Pyodide).
Modes: `?mode=manager|architect|reader`. The demo run: `?run=998-e-19th-ave/as-approved`.

Read first: `PRODUCT.md`, `DESIGN.md`, `docs/user-flows.md`, `docs/ui-brief.md`, `CLAUDE.md` (sections "The manager's stage",
"The lot as a polygon", "Phase 1", "Phase 3", "Phase 4", "Phases 2 and 6"). The UI is one `ffm/ui/index.html`, one
`ffm/ui/app.js` (large; grep for `renderGuide`, `renderStage`, `STAGE`, `answerMoney`, `renderSheets`, `openEditor`,
`FIELD_META`, `setMode`, `MODES`, `paperDocument`) and `ffm/ui/app.css` (the `[data-mode]` rules at the end).

## Screenshots (1440 x 900 unless noted; open each with the Read tool)

Manager mode, a walk from blank to a memo on a real public address (609 Heatley Ave, RT-3, 566.7 m2):

1. Blank landing, stop 1 open, the stage in the memo pane:
   C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803693448-2lx2fe.jpg
2. "Type an address first." after Look up the site with an empty box (red status strip):
   C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803710551-8zdqyz.jpg
3. The site found (district, lot, found as; "Use this site"); the stage has NOT changed yet:
   C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803730852-yhd2mn.jpg
4. After "Use this site": stop 2 open (four program checkboxes), the stage shows the parcel on an OpenStreetMap map with district, lot, street, owner, "not sure" fields; the Site card appears below the guide:
   C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803743159-47eq31.jpg
5. After "Use these programs": stop 3 (Read the site; "Read the district schedule with Claude" fold); stage card 02 lists each program's terms:
   C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803751355-8rnkie.jpg
6. After "Read the site": stop 4 open with Outright | Benchmark | Funder-ready and "Suggest from the rules":
   C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803764052-c3l629.jpg
7. Scrolled: the Site card (needed-to-run / read-by-a-rule / drawings-only marks, (i) buttons, Yes/No/Not sure segments) beside stage card 02 (programs) and 03 (the reading):
   C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803764052-89t2dl.jpg
8. After "Suggest from the rules" (Funder-ready): the suggestion list in the rail (Suggested | Mine per figure, rule id under each, "placeholder" in amber); status strip "Suggested, funder-ready: ? storeys, no floor area, 4 units; 8 left to a person":
   C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803778789-ssnloj.jpg
9. The same, scrolled (units and tiers):
   C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803778789-g5y1j8.jpg
10. Stop 5, Money in (land, equity, other grants; Run the rules):
    C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803800213-n3p1t0.jpg
11. After Run the rules: the memo (title block; 01 Allowed outright; 02 Funders: No; 03 Seven open items; stop 6 in the rail lists the four answers):
    C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803800213-wfyhtz.jpg

Architect mode on the demo run (998 E 19th Ave, as approved):

12. Top: the four step links, the Site form open, the memo's title block and answer 01:
    C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803833171-ouc18a.jpg
13. Scrolled: trees table in the rail, open items table and answer 04 (money: Unlikely, the gap) in the memo:
    C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803833172-9d0wxj.jpg
14. Scrolled: the Option form (building, units, tenure) beside the pro-forma lines table:
    C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803833172-a9ayj1.jpg

Reader mode on the demo run (the memo alone, 980 px column):

15. C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803833172-hn122i.jpg

Mobile (375 x 812), manager landing:

16. C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\mcp-Claude_Browser-blob-1794803833172-o9l4y6.jpg

## What the walk showed (facts, not judgments)

- Stop 1: the lookup took about 8 s with no progress indication beyond the status strip; the result shows DISTRICT RT-3, LOT 566.7 m2 37.2 x 15.2 m, FOUND AS, then a "Use this site" button. The stage (memo pane) does not change until "Use this site" is pressed; after that the stage shows the parcel on a map.
- The address textbox has no accessible name other than its placeholder ("998 E 19th Ave, Vancouver, BC"). The seven stop headers in the guide are `<button>`s with no accessible name. The four program checkboxes are named by rule id in the accessibility tree ("bch.chf.eligibility", "bc.bcbuilds.eligibility", ...); their visible labels are the rule titles.
- Stop 2 ticks two programs by default (CHF, BC Builds); the other two (PDF loan, CMHC AHF) unticked.
- Stop 3 "Read the site" produced 8 rules on the stage, 6 of them Uncertain, each with a person ("Architect: check Map 1 ...", "Manager: supply ...").
- Stop 4 "Suggest from the rules" with Funder-ready on an RT-3 site: Storeys, Height, GFA are placeholders ("no rule in the stack derives this for RT-3: enter it"); units 1/2/1/0 = 4 homes from the SSMUH minimum; tiers market 1 / RGI 2 / deep-subsidy 1; accessible 1; agreement 60 years; replacement trees 5; floor to floor 3.3 placeholder; setbacks 1.8 / 3 / 3 placeholders "scaled to this lot". A "LEFT TO A PERSON" block lists 8 questions (Community Vision area, bus stop, GFA, developer partner, site control, land tenure, trees, transit area) each with Yes / No / Not sure or a select. The stage card 04 reads "ENVELOPE not set · UNITS not set · TIERS not split · TENURE social housing · TREES not set" even though the rail lists 4 units and tiers.
- Stop 5 money: Land ($), Equity ($), Other grants ($) with "blank leaves the money unsure"; the Run the rules button there was disabled until the top-bar button was used (the top bar's Run the rules works at any time).
- The run: "Ran the rules as of 2026-11-15: R1, in 271 ms"; the memo replaced the stage. Answers: 01 "Allowed outright. Outright under RT-3 · no rezoning path stated"; 02 "No." with BC Builds failing (no developer partner) and CHF failing ("unit mix market 25.0%, rgi 50.0%, deep_subsidy 25.0% is not 30/50/20; site control 'None' does not meet the RFP's readiness bar") although the tool itself derived that mix from the fund's 30/50/20 rule on 4 units, and the person never set site control to None (they left it "Not sure"); 03 "Seven open items, each with a named person" (table: item, status, who/what); 04 "Unsure. No floor area, so no capital cost." with NOI $29,846, grants $684,844, debt $401,242, capital and gap "not given", an "Every line" table with ~20 rows each citing a rule id and a long source title (the CMHC source title repeats in full on 4 rows).
- The figures after the run: FIG 01 plan (lot polygon, envelope, plate box 30 x 9.5 m, context from City data, north arrow), FIG 02 section ("Proposed: 1 storeys: plate 285 m2 x 1 = 285 m2 (FSR 0.50), 3.3 m high"), FIG 03 plans by program ("1 of 4 units on 1 floors ... Did not fit: 1 two-bedroom; 2 one-bedroom"), FIG 04 stacking, FIG 05 elevations ("No outright height in the stack for this district"), FIG 06 code site plan. The rail's stop 6 shows Pass/Fail/Uncertain chips and "LEFT TO A PERSON: floor area and unit count; land cost".
- The run wrote `outputs/609-heatley-ave/2026-11-15T21-36-32/` (a timestamp folder; browser-test folders are deleted before commits).
- Architect mode on the demo run: four step links (Site, Option, Run and read, Export) replace the guide's progress line; the Site and Option forms open in the rail with every field, marks and (i) buttons; the memo shows answers then drawings two per row then the ledger; the trees table has 9 rows with DBH blank "unknown".
- Reader mode: the memo alone at 980 px with the mode switch dimmed and "Download PDF / Print".
- Mobile: the top bar stacks (mark, mode switch, rules date, Run the rules), then the status strip, the walkthrough offer, INPUTS and the guide; the memo/stage is below the fold.
- Top bar: "RULES AS OF" date input and "Run the rules (Ctrl+Enter)" are always visible; "REVISION R1" appears after a run.
- The "New here? A two-minute walkthrough" offer sits above the rail on every visit until "Not now".

## Standing constraints the critics must respect

- The engine is deterministic and standard-library; no language model inside it. Every number cites a rule; placeholders are declared. Do not propose hiding uncertainty or inventing figures.
- Three readers: manager (site in, memo out), architect (option in, ledger, massing, Revit out), board/planner/funder (PDF in). The flows are in docs/user-flows.md.
- Public data only; the UI runs with no build step (vanilla JS/CSS); it must keep working on GitHub Pages with the engine in Pyodide.
- Brand: DESIGN.md (IBM Plex, ink chrome, signal blue for Run the rules, verdict wording with a mark, no colour without a word).
