# Architect B: the handoff (manager → architect → paper)

Tested 15 Nov 2026 on http://localhost:8765/app.html, in my own browser tab. The sites were 1022 Nelson St (a West End church site, DD) as the manager's site, then 4411 Brakenridge St (R1-1, a corner lot drawn as a 28-vertex "trapezoid") as the odd lot. I also ran the break tests. I read the three UX critiques only after the test.

**About the evidence.** The browser pane was mostly hidden, so screenshots often timed out or came back as tiny, scaled-down frames. Where a screenshot failed I read the page text and the DOM instead, and I quote it below. The screenshots that did work are under
`C:\Users\kaili\.claude\projects\C--Users-kaili-OneDrive---UBC-Desktop-M-Arch-02-Classes-ARCH-540-02-A2\92089211-b31d-4453-9797-a1394910ce98\tool-results\` (named `S-…` below). I rendered the PDF pages and the run's SVGs into the audit folder:
`C:\Users\kaili\AppData\Local\Temp\claude\f0a9407d4007a0ac\92089211-b31d-4453-9797-a1394910ce98\scratchpad\audit\` (named `A-…` below).

| Id | File |
|---|---|
| S-1 | `mcp-Claude_Browser-blob-1794804476395-kdiy4f.jpg`: blank manager mode, stop 1 |
| S-2 | `mcp-Claude_Browser-blob-1794804511654-w7fgxf.jpg`: "Found 1720 Larch St" after typing 1805 Larch St |
| S-3 | `mcp-Claude_Browser-blob-1794804623455-q374sm.jpg`: 1022 Nelson on the stage, programs card, Site card under the guide |
| S-4 | `mcp-Claude_Browser-blob-1794804681982-iwa5r3.jpg`: after Read the site, stop 4 open |
| S-5 | `mcp-Claude_Browser-blob-1794804763387-q97z7b.jpg`: the four answers for 1022 Nelson ("Allowed outright." in green) |
| S-6 | `mcp-Claude_Browser-blob-1794804779341-9fwpq1.jpg`: the Issue note form at the foot of the memo |
| S-7 | `mcp-Claude_Browser-blob-1794804849784-qsjvpe.jpg`: architect mode with `?run=1022-nelson-st/…`; the memo is 1022 Nelson, the Site card is 998 E 19th Ave |
| S-8 | `mcp-Claude_Browser-blob-1794804892192-dexhch.jpg`: reader mode on the same run |
| S-9 | `mcp-Claude_Browser-blob-1794805080763-k6fmrj.jpg`: 4411 Brakenridge on the stage (small) |
| S-10 | `mcp-Claude_Browser-blob-1794805156960-m67z56.jpg`: 4411 Brakenridge memo (small) |
| A-1 | `archB-1022-nelson-memo.pdf`: the downloaded PDF, 17 pages |
| A-2 | `archB-pdf-p1.png`, `archB-pdf-p5.png`, `archB-pdf-p14.png`: PDF page 1, page 5 (massing) and page 14 (inputs) |
| A-3 | `archB-brakenridge-massing.png`, `archB-brakenridge-siteplan.png`: the Brakenridge run's massing.svg and site-plan.svg as the architect receives them |

Runs I made: `outputs/1022-nelson-st/2026-11-15T21-52-11/` (issued, with `issues.json`), `outputs/4411-brakenridge-st/2026-11-15T21-58-53/` and `…-58-53-1/` (the double click). The PDF download left `C:\Users\kaili\Downloads\d2592dac-db16-42e0-a63d-5d21f9e043d2.tmp`, a complete 1.3 MB PDF that the browser never renamed. It can be deleted.

---

## 1. Manager mode on a fresh site

**Stop 1, find the site.** I typed my first church address, 1805 Larch St. The strip said "Found 1720 Larch St, Vancouver, BC: RT-8, 557.3 m². Check it, then use it." (S-2). The City's address list had no 1805, so Nominatim placed the point on the street ("geocoded as 'Larch Street, Kitsilano…'") and the tool then took the nearest parcel: another lot, another civic number and a corner on W 1st Ave. The only warning is that "FOUND AS" shows a different number in small print. A manager in a hurry presses "Use this site" and the whole memo is about the wrong lot. I then used 1022 Nelson St, which the City's list has: "Found 1022 Nelson St, Vancouver, BC: DD, 2,462.1 m²". *What I understood:* the district and the lot. *What I guessed:* that "DD" was fine. *What the stage told me:* nothing until "Use this site". Then I got a map, "LOT 2,462.1 m² · 61.7 × 39.9 m · A rectangle", "OWNER not given", and a NOT SURE line (S-3). One thing bothered me as a manager: the address box's placeholder is a full real address ("998 E 19th Ave, Vancouver, BC"). It reads as already filled in.

**The questions left to a person.** These are in the Site card, which opens under the guide. I answered as the manager would: Community Vision Not sure, transit area Not sure, bus stop Yes, water and sewer Yes, owner "The congregation (United Church)", owner type "church", tenure "to confirm". The radio groups have no accessible names, and the Area, Frontage and Depth inputs are named only by their placeholder "not sure".

**Stop 2, programs.** CHF and BC Builds were already ticked. I kept them because I did not know the other two. The stage printed each program's terms with sources, including "2025 call … cancelled Feb 2026". That was useful, but on the screen it was the longest card, and stage card 3 sat below it, out of view.

**Stop 3, read the site.** The strip said "7 rules speak to it before any option." The fold said "Read the district schedule with Claude (no outright schedule for DD in the stack; with a key)". A manager does not know what "the stack" is, so this reads as an optional extra and not as "the tool cannot tell you what this site allows." The stage listed five Uncertain items and two Info items. One of the Info items says "the church use is also DCL-exempt". That sentence is hard-coded in `ffm/checks.py:284` and appears on every site, including the Expo Blvd tower and the Brakenridge society lot.

**Stop 4, shape the option.** Funder-ready, then Suggest. The strip said "? storeys, no floor area, no units; 5 left to a person." Storeys, Height and GFA came back as "no rule in the stack derives this for DD: enter it", and the instruction under "Left to a person" was "**Manager**: enter the storeys, height and floor area the rezoning or the schedule sets." That is backwards: the one person who cannot answer is being asked. The block also showed raw keys ("Gfa M2", "Rent Tiers Units", "In Former Community Vision Area"), and it asked the Community Vision question a second time after I had answered it in the Site card. **Site control and developer partner were not offered at all on this site**, even though CLAUDE.md says stop 4 asks them. As a manager I guessed 6 storeys and 20 m and left GFA blank. "Use this option" accepted that and reported "with 3 of your own figures". Stage card 4 then read "6 storeys · 20 m · **null** m²".

**Stop 5, money in.** I left all three blank. The help line said land is carried at a nominal value because the owner is a church. That was right, and it was the clearest stop in the flow.

**Stop 6, run.** "Ran the rules as of 2026-11-15: R1, in 435 ms · wrote outputs/1022-nelson-st/…" (S-5).

**The four answers, read as the manager.**
1. *Allowed?* A green "**Allowed outright.** Outright under DD · no rezoning path stated". The manager reads this as a yes. It is not one. The stack has no DD schedule, so nothing could fail, and the absence of a rule is shown as a pass. FIG 06's own table says "Floor space ratio 3.92 … no schedule in the stack".
2. *Funders?* "No." BC Builds failed for want of a developer partner, and CHF failed on "site control 'None'". Neither question was ever put to me on this site, and the church owns the land, so site control is about as finalized as it gets.
3. *Unsure?* "Six open items, each with a named person": three for the architect, two "Manager: resolve the failing criteria", and one "Enter the unit counts by bedroom type" with no person named. Nothing about heritage. The rules folder has no heritage rule at all (`grep -i heritage rules/` gives 0), yet a church in the West End is the first place a planner looks for the Heritage Register.
4. *Money?* "Unsure. No floor area, so no capital cost." Meanwhile FIG 02 says "plate 1,607.8 m² × 6 = 9,646.8 m² (FSR 3.92)". The drawing knows the floor area and the money does not use it.

**The same answers, read as the architect who receives them.** I would not trust answer 1. I would discount answer 2 because it rests on two defaults nobody chose. The real open items for a DD church site are missing: what the DD sub-area allows, heritage, the existing church ("5 buildings now on the lot are left out" is only in the FIG 01 caption on screen), and which part of the lot is offered. FSR 3.92 at 65% coverage covers the whole lot, sanctuary included. Nothing in the memo says the massing assumes the church is demolished.

## 2. Issue to the architect

The Export bar's "Issue to the architect" opens an inline form (S-6): "A note for the reader who receives it", placeholder "What changed, and what you want checked", then Issue and Not now. I wrote the note a real manager would write: the board's deadline, my guessed 6 storeys, "I don't know DD", "the church owns the land and we'd partner with a builder", "is the church heritage?". The strip said "Issued R1 to the architect at 2026-11-15 21:53. They see it in their top bar." The note landed in `outputs/1022-nelson-st/2026-11-15T21-52-11/issues.json`.

**What the architect actually gets: nothing they can find.**
- I opened `?mode=architect` as a colleague would. It lands on the 998 E 19th Ave demo. **No chip came**, even after 17 s (longer than the 15 s poll). The reason is in the code: `app.js:4532` polls `/api/issues?site=${state.siteId}`, so the chip only fires for the site already on screen. The site picker lists only the sites saved in `sites/` (1010 Expo, 998), and the manager's flow never asked them to save 1022 Nelson. The run picker lists only 998's runs. The issued run is not reachable from any control.
- I then typed the URL by hand (`?mode=architect&run=1022-nelson-st/2026-11-15T21-52-11`), which nobody would know to do. The memo is 1022 Nelson, but **the Site card beside it is 998 E 19th Ave, RM-1, 2,316.7 m², with the 998 answers** (S-7; `state.siteId` = "998-e-19th-ave"). Running the rules from there would run the demo site under my client's name. The revision reads "a new revision", not R1. Still no chip, and **the manager's note appears nowhere on the page** (a search for "Church board wants" found nothing).
- Back in manager mode after a reload, "A saved site" again lists only 1010 Expo and 998. The manager cannot get back to the run they issued either.

**Is the handoff complete?** No. It writes a file that no screen reads. Even if the note had arrived, the inputs carry no site control, no developer partner and no tenure answer, and FIG 01 does not say which buildings stay. Here is what I would still have to ask the manager:
1. Which part of the lot is offered? (sanctuary kept or not; is the hall the site?)
2. Is the church on the Heritage Register, or does it have a heritage designation or agreement?
3. Site control: does the congregation own it outright, and is the board resolution done?
4. Developer partner: named, or only intended?
5. Where did 6 storeys and 20 m come from: a neighbour, a planner conversation, a guess?
6. The tenure plan: a lease to a society, or the church as operator?
7. Is this the address you meant? (The Larch St case shows the tool can silently pick a different lot.)

The tool could have asked items 3, 4, 6 and 7 itself, and the memo should carry the answers.

## 3. The PDF, page one cold, as a planner

Download PDF from reader mode said "Saved 1022-nelson-st_2026-11-15T21-52-11_a new revision_memo.pdf". The file has spaces in its name, "a new revision" in place of R1, and 17 pages (A-1, A-2).

Page 1 (A-2 p1): the title block shows Option, Revision "a new revision", Rules as of, Proponent, Site "DD · 2,462.1 m² · 61.7 × 39.9 m", Issued, Fingerprint. Then "The three answers":
- "Is it allowed outright? ✓ Yes. No rule stands in the way." A planner stops reading here. On a DD site the honest answer is "not assessed: no DD schedule in the rules". Printed as "Yes", with a tick, it is the most quotable and the most wrong line in the document.
- "Does the money work? Unsure … Every line and its source are in **the memo on screen**." There is no screen on paper.
- "What is still unsure? ✗ 6 open items", with references A1, B2, C3, C5, E1, E2.

**What I could cite:** each rule by reference and version (A1 `cov.irp.social_housing_rezoning · v 2023-11-01`, C5 the tree by-law with its schedule sections). I could also cite the sources with URLs (pp. 15–16), the fingerprint and rule hashes (p. 17), and the reproduce line. That is better than anything I get today.

**What I could not cite:**
- the "Yes" in row 1 (no rule decides it);
- the 6-storey, 20 m, 9,647 m² building on p. 5. It has no author, and the paper never says it was the manager's guess. The option name "Suggested, funder-ready: rule-derived" says the opposite;
- the existing buildings. The paper's FIG 1 caption drops the screen's "5 buildings now on the lot are left out";
- who prepared the memo, and the manager's note or question;
- the money. On paper there are no lines.

Page 14 prints the raw parcel ring as longitude and latitude pairs, plus "frontage_bearing_deg: 135.3", "rectangularity: 1". Those are inputs, but a planner reads them as noise.

## 4. Reader mode on the same run

It is not the memo "as on paper" (S-8):
- The paper says "1 The three answers", a Question | Answer | Decided by table with A1-style references. The screen has four answer cards and no references.
- The paper splits "allowed outright" from "allowed by rezoning". The screen has one "Allowed outright." card.
- The reader sees the status strip with a file path ("Opened a new revision, the run as of 2026-11-15 · outputs/1022-nelson-st/…") and a "a new revision" chip in the top bar.
- FIG 01 and FIG 03 keep their Plan / 3D and Plan / Axon toggles.
- The figures sit in a right-hand column beside the answers rather than after them.

It is a tidy screen memo, but a board member comparing it with the PDF on the table would think they were two different documents.

## 5. The odd lot: 4411 Brakenridge St

- **Stop 1:** "Found 4411 Brakenridge St, Vancouver, BC: R1-1, 776.6 m²", "LOT 776.6 m² · 22.7 × 34.2 m (the side along Brakenridge St)". Nothing yet says the lot is not a rectangle. The dimensions read like a survey.
- **Stage after "Use this site":** "776.6 m² · 22.7 × 34.2 m · Four sides with a rounded or cut corner, not square-cornered (90% of its 36.0 x 23.9 m bounding rectangle), 777 m2. The massing follows the polygon." That is two pairs of dimensions in one line, with "×" and "x" mixed. A manager cannot tell which pair is the lot. The memo's FIG 01 then calls the same lot a "**trapezoid, 28 corners**". Three different shape descriptions of one lot.
- **Equivalent rectangle:** explained only in the Notes textarea and the FIG 01 caption ("equivalent rectangle 22.7 × 34.2 m"). The manager is never told what it is for.
- **FIG 01 draws the real parcel:** yes. A-3 shows the City's polygon with the curved Edgar Crescent edge, the setback envelope following the lot lines, and the plate box inside. The plate box is a good answer for a first read.
  - **Corner-lot problem:** the setbacks are front 3.7, rear 6 and *sides 1.8* on all three remaining edges, including the flanking street. An exterior side yard on a corner lot is not an interior side yard.
  - **Export problem:** the exported `site-plan.svg` and `massing.svg` carry no street names, and in a non-browser renderer the plan checker's columns overprint ("no schedule in theinfock", "777 mSection across…"). Those are the files that go to the architect. Please check them in Illustrator and Revit's importer.
- **The corner-lot note:** it exists. "A corner lot: Mcmullen Ave also runs beside it … The frontage is taken on Brakenridge St (22.7 m); the front could instead be the 34.2 m side on Mcmullen Ave (a person put it there on four of the 39 corner and odd lots checked on 15 Nov 2026). Confirm which side is the front." But it lives **only in the Site card's Notes textarea and in the memo's Inputs → Site notes** (line 164 of `memo.md`). It is not on the stage. It is not an open item with a named person. No control lets anyone choose the front. A manager would not find it. If they did, "four of the 39 … checked on 15 Nov 2026" is the tool's own evaluation set leaking into a client document. They would not know that which side is the front decides the setbacks, the envelope and the massing.
- **Answers on this lot:** again "Allowed outright. Outright under R1-1" while every envelope row says "no rule in the stack derives this for R1-1". Funders "No", including CHF failing "unit mix market 25.0%, rgi 50.0%, deep_subsidy 25.0% is not 30/50/20", which is the split the tool itself suggested at stop 4. Money "Unsure. No floor area" while FIG 02 has 1,138.5 m² (FSR 1.47), and "Left to a person: floor area and unit count" although the option has 4 units. The proponent row reads "— (non profit society)".

## 6. Breaking it as a manager would

- **Refresh mid-way** (site used, programs chosen): everything was gone, with no "Leave site?" warning (`window.onbeforeunload` is null) and no resume. The run I had already issued was not offered either.
- **A Burnaby address** ("4949 Canada Way, Burnaby"): "Found Burnaby City Hall, 4949, Canada Way, Deer Lake, Burnaby: district not found, no parcel. Check it, then use it." "Use this site" worked, and the Site card then said **Municipality = "City of Vancouver"** for Burnaby City Hall. The flow carries on and would apply Vancouver's tree by-law, Community Vision policy and DCL rules to a Burnaby lot. Nothing says "outside the City of Vancouver; these rules do not apply."
- **"1,200,000" typed into Land:** this Chromium dropped the commas as I typed and stored 1200000 (`validity.valid` true). The run used "Land $1,200,000 … entered in the option's finance block". Typed commas are therefore fine here. I did not test pasting, or "$1.2M".
- **Run twice quickly** (two clicks on the top bar's Run): two folders, `2026-11-15T21-58-53` and `…-58-53-1`, as R1 and R2 with identical inputs. The revision counter now says R2 for something nobody revised.

---

## 7. My response to the UX critics' P0 and P1 issues

| Critic · issue | My view | Why, from my test |
|---|---|---|
| UX-1 P0-1: the tool fails its own suggestion and reads Not sure as no | **Agree** | On Brakenridge, CHF failed on the 1/2/1 split the tool suggested, and on 1022 Nelson it failed on "site control 'None'" for a question that **stop 4 never even asked**. That is worse than reading "Not sure" as no. |
| UX-1 P0-2: an incomplete option passes stop 4 and draws a building nobody entered | **Agree, and widen it** | With storeys and height entered and GFA blank, the memo says "No floor area" while FIG 02 states 9,646.8 m² and FSR 3.92. The engine has the area and the money ignores it. The fix should feed the massing GFA into the pro-forma, labelled "from the massing, not entered", instead of only blocking. |
| UX-1 P1-3: the stage contradicts the rail at stop 4 | **Agree, minor for me** | I saw "null m²" on stage card 4. For the handoff it matters less than the issues below. |
| UX-1 P1-4: the lookup result never reaches the stage | **Agree strongly** | This is how my 1805 Larch St became 1720 Larch St. The map preview, with "you typed 1805; the City has no such address, this is 1720", is the check that would have caught it. |
| UX-1 P1-5: "no schedule for RT-3" hidden in a parenthetical | **Agree, and it is P0 at the handoff** | The consequence is not only confusion at stop 4. Page 1 of the PDF prints "Allowed outright ✓ Yes" for a district the rules cannot read. |
| UX-2 P0-1: funders failed on figures the tool chose | **Agree** | Same as UX-1 P0-1. I would add that a church site with owned land is told "site control 'None'". |
| UX-2 P0-2: the PDF has no money lines and sends the board to a screen | **Agree** | Confirmed on page 1 of my PDF. A planner or treasurer cannot trace a single dollar on paper. |
| UX-2 P1-3: four "left to a person" lists, four counts | **Agree** | I saw "5 left to a person" (strip), the stage list, "Six open items" (answer 3) and "floor area and unit count" (stop 6). The corner-lot question is in none of them, which is the bigger gap. |
| UX-2 P1-4: the memo contradicts itself | **Agree** | My contradictions differ from the critic's but are the same kind: "Allowed outright" against "no schedule in the stack" in FIG 06; "No floor area" against FSR 3.92; and the church DCL sentence printed on a society lot. |
| UX-2 P1-5: two citation systems (ids on screen, A1 on paper) | **Agree** | When the planner writes "re C5", I need to find C5 on screen. Today I count rows. |
| UX-2 P1-6: Summary is not a summary, Reader is not the paper | **Agree** | Reader mode differs from the PDF in structure, numbering and even the number of answers (four on screen, "three answers" on paper). |
| UX-3 P0-1: the guide throws away keyboard focus | **Not my problem, but plausible** | My element references went stale after almost every action, which matches whole-guide re-rendering. I drove the page by references, so I could not judge the keyboard experience. |
| UX-3 P0-2: stop 5 disabled with a false reason, two Run buttons disagree | **Partly agree** | I entered storeys, so stop 5 was enabled for me. The silent double run from the top bar is real (R1 and R2 in the same second). |
| UX-3 P1-3: numbers silently coerced into "not sure" | **Disagree on the example, agree on the principle** | Typed "1,200,000" was stored as 1200000 in this Chromium. "$1.2M" and pasted text remain untested. Free-text owner type deciding nominal land is a real risk: I typed "church" and "society" exactly. A "Parish of …" would not match. |
| UX-3 P1-4: errors far from their cause | **Agree, low for the handoff** | The Burnaby case did not produce an error at all, which is the worse problem (section 6). |
| UX-3 P1-5: "not given" and 'None' put the blame in the wrong place | **Agree** | "PROPONENT — (non profit society)", "null m²" and "site control 'None'" all reached either the memo or the stage. |
| UX-3 P1-6: unsaved and stale states invisible, refresh loses the session | **Agree, and it is P0 for the handoff** | The unsaved site is exactly why the issued run is unreachable. The manager was never told that issuing an unsaved site gives the architect nothing to open. |

## 8. What they missed that matters at the handoff

1. **The issue reaches no one.** Element: Export bar → Issue → the top-bar chip. I issued R1 with a note (S-6). In architect mode there was no chip after 17 s, because the poll asks only for the site on screen (`app.js:4532`). The issued site was not in the site picker (never saved), its run was not in the run picker, and the note is shown nowhere, even when the run is opened by URL (S-7). This is the one feature built for the handoff, and it does not hand anything off.
2. **Architect mode shows one site's memo beside another site's form.** With `?run=1022-nelson-st/…` the memo is 1022 Nelson and the Site card is 998 E 19th Ave (S-7). "Run the rules" there would issue the demo site under my client's name.
3. **"Allowed outright ✓ Yes" when no district rule exists.** 1022 Nelson (DD) and 4411 Brakenridge (R1-1): green on screen (S-5), a tick on PDF page 1 (A-2 p1), with "No rule stands in the way" as the reason. For a planner this is the line that discredits the memo.
4. **Wrong parcel without a warning.** "1805 Larch St" became 1720 Larch St, a corner lot on another block (S-2). The lookup fell back to a street-level geocode and took the nearest parcel. The only signal was a different number under "FOUND AS".
5. **Burnaby is treated as Vancouver.** "Municipality: City of Vancouver" for Burnaby City Hall, and the flow continues.
6. **The corner-lot question never becomes an open item.** It is in the Notes textarea and the memo's Inputs section only (`memo.md` line 164), with eval-set wording, and there is no control to choose the front. The setbacks then treat the flanking street as an interior side yard (A-3).
7. **Existing buildings and heritage.** The screen says "5 buildings now on the lot are left out". The PDF drops that sentence. No rule covers the Heritage Register. On a church site, the massing silently assumes demolition of the sanctuary.
8. **Hard-coded demo text in a rule finding.** "the church use is also DCL-exempt" appears in every ledger (`ffm/checks.py:284`), including the society lot in Arbutus Ridge and the Expo tower.
9. **The run identity on paper.** "a new revision" in the PDF title block and file name for a run that is R1 on screen. Spaces in the file name.
10. **Stop 4 never asked site control or developer partner on 1022 Nelson**, yet both decide answer 2.

## 9. My top five changes, in priority order

**1. Make the issue a real handoff.**
- *What it lets us do:* the architect opens the tool and sees "1022 Nelson St · R1 · from the manager, 15 Nov 21:53", with the note. One click opens the memo with the right site and option loaded. Today I cannot find the run at all.
- *Change:* Issuing writes the run's site and option into `sites/` and `options/` if they are unsaved. The run folder already has them in `ledger.json` inputs, so this is deterministic. Before issuing, ask inline: "This site is not saved. Issuing saves it as `1022-nelson-st` so the architect can open it." The chip polls `/api/issues` across all sites (`?to=architect`), not only `state.siteId`. Clicking the chip loads the run *and* its site and option into the cards. The note is pinned above the title block as a quiet panel ("From the manager, 15 Nov 2026 21:53: …") with "Mark as read". The chip also offers a copyable link (`?mode=architect&run=…`) for email.
- *Guard:* opening any run sets the Site and Option cards to that run's inputs, or shows "The cards hold 998 E 19th Ave; the memo is 1022 Nelson St. Load this run's inputs?"

**2. Never print "allowed" where no rule can say so.**
- *What it lets us do:* the manager and the board read a true answer 1. The planner can cite page 1.
- *Change, in the engine (`memo.py` / the ledger summary):* when layer A has no schedule for the district, answer 1 is **"Not assessed: the rules have no DD schedule."** with status Uncertain, and an open item "Architect: read the DD schedule (or the sub-area's ODP) and enter the outright height, FSR and yards." Copy on paper: "Is it allowed outright? ? Not assessed. No DD schedule in the rules; the envelope on page 5 is the manager's figure, not a permitted one."
- *Same rule for the option:* the option name says who chose the figures: "Funder-ready; storeys and height entered by the manager". It never says "rule-derived" when three of the four envelope figures are typed.
- *Stop 4:* the instruction becomes "Architect: …" or "Leave blank: the architect will set it".

**3. Confirm the parcel before using it, and stay inside Vancouver.**
- *What it lets us do:* the manager catches a wrong lot or a wrong city at stop 1, before seven stops of work.
- *Change:* after a lookup, stage card 1 shows the parcel map at once, titled "Is this the parcel?" (as UX-1 P1-4 says). When the civic number found differs from the one typed, or the point came from a street-level geocode, use an amber line: "You typed 1805 Larch St. The City's address list has no 1805; the nearest parcel is **1720 Larch St**. Use it only if that is the site." The button reads "Yes, 1720 Larch St is the site".
- *Outside the City of Vancouver* (no zoning record and the geocoder's municipality is not Vancouver): "Burnaby is outside the City of Vancouver. The rules here are Vancouver's and the Province's; this tool cannot read a Burnaby site yet." Disable "Use this site", and never default `municipality` to "City of Vancouver".

**4. Put the site questions that change the drawing into the open items, with a control.**
- *What it lets us do:* the manager answers what they know (front street, sanctuary kept or not, site control, partner). I receive a memo whose massing matches the brief, and the questions they could not answer arrive with my name on them.
- *Change:*
  - **Corner lot:** stop 1 (and the stage) shows "Corner lot: which street is the front? [Brakenridge St] [Mcmullen Ave] [Not sure]". "Not sure" becomes an open item, "Architect: confirm the front with the City; it sets the yards", and the flanking side gets the exterior side-yard placeholder, labelled.
  - **Existing buildings:** "What stays on the lot? [Nothing] [Keep the existing building(s)] [Not sure]". "Keep" or "Not sure" puts the footprint in FIG 01 as retained, an open item in answer 3, and the sentence in the PDF caption.
  - **Site control and developer partner** are asked at stop 4 on every site (they were missing on 1022 Nelson), and a blank is Uncertain, never Fail.
  - **Heritage:** with no rule, a deterministic open item for owner type church or a pre-1940 building: "Architect: check the Vancouver Heritage Register for this address". Better, a layer-A rule from the City's open heritage dataset, cited like the others.
  - Remove the eval-set wording ("four of the 39 … 15 Nov 2026") from the site notes.

**5. One memo on paper and on screen, with its run identity.**
- *What it lets us do:* the board, the planner and I hold the same document. "Re C5" means the same thing everywhere. The treasurer can trace the gap on paper.
- *Change:*
  - Reader mode renders the paper's section model and references (UX-2 P1-5 and P1-6).
  - The PDF gets the money lines (UX-2 P0-2).
  - The title block adds "Prepared by: development manager · issued to: architect, 15 Nov 2026 21:53", and the issue note if the manager ticks "include my note".
  - A run opened by URL keeps its revision (R1), never "a new revision", and the file name is `1022-nelson-st_R1_2026-11-15_memo.pdf`.
  - The FIG 1 caption on paper keeps "5 buildings now on the lot are left out".
  - Raw polygon coordinates move to the reproduce appendix.
  - A run with identical inputs to the previous one within a minute is not a new revision: the second click is ignored while a run is in flight.

## 10. Better than what I use today; do not lose these in a redesign

1. **Every rule with its version, its clause and a numbered source, plus a fingerprint and a reproduce line.** PDF pp. 9–17. Today my feasibility memo cites "the zoning by-law" and a date. This cites "C5 · cov.trees.replacement · v 2023-01-01 · Schedule C (ss.5.1, 5.2, 6.2)", with a URL. A planner can check it and a later reader can tell whether it is still true.
2. **The open-items table with a named person and an action.** Even with its gaps, "Architect: obtain the arborist report and survey (every tree on the site, within 2 m of the boundary…)" is exactly the line I would write in a kick-off email. Keep it as the core of the handoff. Make it the place the corner-lot and heritage questions go.
3. **The City's own parcel, drawn with the envelope following its lines and the plate box inside** (A-3), plus the pro-forma's dated, cited assumptions (BCPI quarter, CMHC survey month, BoC series) with placeholders marked as placeholders. I usually start from a rectangle and a cost per square foot from memory. Both of these are more honest than that and should stay deterministic exactly as they are.
