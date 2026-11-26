# User test: architect, towers and supportive housing (25 Nov 2026)

Simulated reviewer (an AI role-play, not a practitioner) in the seat of an architect at a larger Vancouver practice: towers on transit sites, CD-1 rezonings, supportive housing and shelters for non-profits and BC Housing. Own server on port 8793. Runs I made: `outputs/1290-burrard-st/2026-11-25T18-26-11` (supportive, tower on a 3-storey podium, 18 storeys, 15,000 m²) and `outputs/3475-e-hastings-st/2026-11-25T18-34-20` (80-bed shelter, 6 storeys). Read: 375-glen-drive/as-proposed, 1010-expo-blvd/what-if-12-storey, 998-e-19th-ave/what-if-funder-ready, and the paper memo for three runs.

(Saved by the coordinating session from the reviewer's returned text: the harness does not let a subagent write files.)

## 1. Verdict

Not next week. The front half is honest and I would show it: the site lookup, the district's use table, answer 1 as three verdicts, "not assessed" on an unread CD-1, and open items that each name a person. The back half is what a client and BC Housing will actually look at: the plans, the core, the lifts, the area schedule and the supportive pro-forma. There it says things I cannot put my name to. An 18-storey tower's section has no tower in it, and its caption says "1,750 m² × 18 = 15,000 m²". The operator checklist passes "4 elevators" in a 7 × 7 m core that draws a scissor stair and no lift. A six-storey, 80-bed shelter passes as "a walk-up". Supportive studios are charged market rent. Tower studios have no door to the corridor. A BC Housing development manager would find any one of these in five minutes and stop trusting the rest. Fix the drawing arithmetic, tie the lifts to the core, and stop applying market rents to supportive homes. Then I would show it to a client as a first-read screen, with the plans labelled as a test fit.

## 2. The flow as walked

**Home, how and case pages.** The four-question pitch is clear. But the rule count changes from page to page: the home page says "checks the option against 144 rules" and also "84 rules"; the how page says "Five of the 144 rules"; the memo says "Clauses applied · 25 of 176 rules". The how page says the approved case has "eight" open items, then "seven" two paragraphs later, and its diagram shows nine nodes. The home hero gives outright as "9.9 m", and the text under it says "10.7 m". The how page also admits that "the construction cost is a figure for two- to four-unit buildings". That one line would end a client meeting about a tower. A practice weighing whether to put this in front of a client would stop at the mismatched counts, because they read as a site nobody maintains.

**01, 1290 Burrard St.** The lookup is fast, and CD-1 (587) is reported correctly: "by-law is not in the rules, so a rough envelope stands in". The new transit suggestion worked: "Yaletown - Roundhouse station is about 700 m ... tier 3 ... so confirm", with a "Use it" button. "Which street is the front?" came preset to **Burnaby St**, a street on the far side of Burrard; the tool's own plan labels the lot's short end Drake St. I changed the front to Burrard, but the memo's site notes still say "The yards are read from Burnaby St, the shorter street side". The by-law reader form is clear about what it does with a key (I did not enter one). The tool offers three different routes for the same job, though: that form at 01, "the architect's Site schedule can read it with Claude", and "save the site's CD-1 by-law into inbox/", a repository folder no user of the tool would know about.

**02, supportive housing in a tower.** I chose Supportive under "Who are the homes for?". A program brief appeared: front desk 12 m², staff office 15, staff washroom 4, program room 40, dining 138, laundry 55.2, harm reduction room 10. I chose Tower, and a podium-storeys field appeared. Manager mode has no tower-plate field; the memo later says "the tower plate a placeholder of 650 m²". Funder-ready gave 138 studios split "41 / 69 / 28 tiers", which is 41 supportive homes at market rent. The schematic section at 02 stayed a single slab with no podium after I picked a tower. For this CD-1, "What the lot takes" printed "Roughly: 8 storeys, 7,522 m² (FSR 3)" under the heading "Rough allowed, from the lot and the code". Those figures are the transit-area (TOA) tier-3 minimum, not anything read from the lot or the code. I entered my own 18 storeys, 62 m and 15,000 m². Homes jumped to 259 supportive studios with no warning about scale. Dining and laundry scaled up to 259 and 103.6 m², while the desk, staff office and harm reduction room stayed at 12, 15 and 10 m².

**03 and the run.** Step 03 says "Building cost ... Blank: the tool's wood-frame base." The run took 396 ms. Answer 1 reads well as three verdicts: "Outright Not assessed · By the Director's discretion Not assessed · By rezoning Not yet confirmed". Answer 2 correctly declined to test the Community Housing Fund and BC Builds, calling them "Not the test for this option". The money section still counts 78 homes at "$1,963 a month a home".

**3475 E Hastings St as a shelter.** The use table at 02 is the best new feature: "A shelter: ... Group Residence: conditional ... Social Service Centre: conditional ... a question for the City". The station note said honestly that Rupert is "about 2,289 m away" and that bus exchanges are not in the data, so I set tier 4 by hand. After I chose "A shelter", the tool said "Manager: enter the beds the operator plans", but Manager mode has no beds field. It exists only in Architect mode's Option schedule. Switching to Architect showed a blank option form: the kind of housing and the storeys I had chosen in Manager mode were not carried over. I re-entered the shelter there (80 beds, 6 storeys, 6,000 m²) and ran it.

**375 Glen Drive and 1010 Expo Blvd, Architect mode.** I read answer 1, the plans, the exits and the area schedule, and opened Edit blocks on the 1010 Expo tower. The operability checklist ("What an operator checks first") appears only in Operator mode, never in Architect mode.

**Paper memo** (1290 Burrard, 1010 Expo, 3475 shelter). It is clean and well ordered, but it carries every drawing defect below onto paper unchanged.

## 3. Defects, ranked by harm

1. **Supportive homes are priced at market rent.**
   - Reproduce: 1290 Burrard, step 02, Supportive, Funder-ready.
   - Expected: shelter-rate or rent-geared-to-income rents on every supportive home. The tool's own Supportive Housing Fund rule says "a resident on income assistance pays the maximum shelter component".
   - Saw: "41 / 69 / 28 tiers", then "78 market · 129 RGI · 52 deep subsidy", and in the money table "Market rent, 78 homes $1,837,368". Net operating income, the debt and the 76% gap all rest on it.
   - **Verified twice.**

2. **The checklist passes lifts that are neither drawn nor fit in the core.**
   - Reproduce: 1290 Burrard run, Operator mode.
   - Saw: "Elevators PASS 4 elevators for 259 homes on 18 storeys". The tower floors draw "One 7 × 7 m core ... holding a scissor stair": in the drawing, a 7 × 2.8 m scissor stair and two unlabelled 2.1 m strips, with no lift on any tower floor. The ground floor draws one lift-like box. On 375 Glen, "3 elevators" pass with one drawn. In the block editor, a 5 × 5 m core clears the editor's "core large enough for an elevator" check on a 12-storey, 120-home tower.
   - The lift count and the core size are never compared.
   - **Verified twice.**

3. **A six-storey shelter passes as a walk-up.**
   - Reproduce: 3475 E Hastings, shelter, 80 beds, 6 storeys.
   - Saw: "Elevators INFO no elevator: 6 storeys or fewer, a walk-up" (on screen and on paper), and "Accessible homes PASS 0 ... 0 wanted". The lift rule counts homes, not beds; Glen's 80 beds likewise add nothing to its 3 lifts.
   - Expected: a fail, with 80 people sleeping above grade, no lift and no accessible bed.
   - **Verified twice.**

4. **The section leaves out the tower, and its caption's arithmetic is false.**
   - Reproduce: 1290 Burrard, FIG 02 and paper Figure 2.
   - Saw: the podium drawn to 10.32 m and a single line to 62 m. The caption says "plate 1,750 m² × 18 = 15,000 m²" (that product is 31,500) and "a tower of 18 storeys on a 3-storey podium", which reads as 21 storeys. The stacking caption says "241 of 259 units on 18 floors of 67.5 × 25.93 m (1,750 m² each)".
   - The 3D view shows a tower; the section and the header do not.
   - **Verified twice** (on screen and on paper).

5. **Tower studios have no corridor access, and egress is measured through a home.**
   - Reproduce: 1290 Burrard, FIG 03 typical floor (levels 4 to 18), and the L4 view.
   - Saw: the corner studios touch only other studios. The "7.5 m" travel line starts at a door inside the neighbouring studio. Exits still read "pass". That is 2 homes a floor, 30 in all.
   - Seen in two views of one run.

6. **A CD-1 reads "Allowed outright: Yes" on an unverified draft and on the larger of two site areas.**
   - Reproduce: 375 Glen, R2.
   - Saw: FSR 6.90 "over 2,134.4 m², the site area the by-law fixes" passes, while the plan says "The City's parcel measures 1,926 m²" (FSR 7.65 on that). 1010 Expo shows the same pattern (2,690 m² parcel, 3,908 m² recorded).
   - The verdict line itself never says "unverified"; that sits two sections lower.
   - Expected: "Uncertain" until a person settles which area is the site.
   - **Verified twice** (two sites).

7. **A shelter is read as social housing and tested against the family-unit rule; its use is misread as needing a rezoning.**
   - Reproduce: 3475 shelter.
   - Saw: "80 beds, a shelter (social housing)". Open item C4 asks to "Enter the unit counts by bedroom type", and C5 asks for the share below the income limits. Paper answer 1 lists "A4 C-2 uses ... (over the outright limit: rezoning required)", although step 02 said the candidate uses are conditional, which means the Director's discretion, not a rezoning.
   - Seen once.

8. **The shelter's floor area is mostly empty, and nothing flags it.**
   - Same run.
   - Saw: "0 of 0 units". Every shelter room is on the ground floor, then "Typical floor (levels 2 to 6) · 808 m² spare". 6,000 m² for 80 beds is 75 m² a bed and raises no flag, yet it is costed at $39.2M.
   - Seen once.

9. **375 Glen is modelled as one slab, one tenure and one entry.**
   - Saw: two wings of 15 and 13 storeys drawn as one 38.5 × 25.5 m plate.
   - The secured-market wing is counted as "social housing · 99-year agreement", so the Community Housing Fund check fails on "market 54.6%". That failure is an artefact of lumping the two wings together.
   - Level 2 puts the 80-bed sleeping area (one 405 m² room, against the "at least 20 rooms" its own rule asks for) across a shared corridor from two 3-bed family homes.
   - One entry and one desk serve the shelter, the supportive homes and the rental homes.
   - Seen once.

10. **The area schedule does not tie to the floor area.**
    - 1290 Burrard: 15,049 m² gross against 15,000. 375 Glen: 15,032 against 14,729.
    - On podium and slab floors the schedule's floors run about 20 m² over the plate (1,770 against 1,750; 1,002 against 981.9).
    - **Verified twice.**

11. **Podium studios are 54 m²; tower studios are 36 m².** The unit depth is forced to 12.06 m on the podium ("st 58 m²" including partitions). This inflates the area per home and makes the podium home count wrong. Seen once.

12. **The memo says no operator is named when one is.** 1010 Expo: the proponent line names "operator BC Indigenous Housing Society", and The ask says "WHO OPERATES Not named". **Verified twice** (on screen and on paper).

13. **On paper, a not-assessed verdict is explained as clear.** In the paper's "Decided by" column, "Not assessed" sits next to "No rule stands in the way." Seen on 1290 Burrard (outright, funders) and 3475 (funders). **Verified twice.**

14. **The code basis is wrong for Vancouver, and high-building measures are missing.**
    - Rule D1 says the building falls under "the Vancouver Building By-law 2025", yet every exit check cites "BC Building Code 2024, Part 3".
    - The exit figures were "entered from recollection ... not read from the code text", yet the plans print a green "pass".
    - Nothing anywhere mentions high-building provisions, firefighter lifts or standpipes for an 18-storey tower.

15. **The front street is wrong.** 1290 Burrard defaults to "Burnaby St" as the front, and the memo's notes keep it after the user changes it. Seen twice.

16. **Smaller defects.**
    - 375 Glen comparison: "Family-unit requirement ... Not applicable · unit mix not given", while the mix is in the header.
    - "fetched 2026-11-26" appears on a run made on 25 Nov (a UTC date).

## 4. Interface problems, ranked

1. **Beds cannot be entered in Manager mode**, although Manager mode asks for them. Switching from Manager to Architect mid-option shows a blank Option schedule.
2. **Other people's work bleeds into your session.** The header showed "3475-e-hastings-st · a run issued to you by the manager", sent by someone else. Opening 375 Glen or 998 E 19th set `&compare=` to another reviewer's draft from minutes earlier. A site card read "This site has 1 memo: R1", which I never issued. Nothing records who issued a revision.
3. **The operability checklist is only in Operator mode**, so the architect who draws the plans never sees it.
4. **Opening a run silently resets "Rules as of"** to that run's date (17 Nov, 23 Oct). A new run started from there reads old rules unless you notice.
5. **Plan views disagree in orientation.** FIG 03 has the street at the bottom; the per-level views turn it 90° and put the street on the left.
6. **Program rooms are drawn as slivers.** The staff office, washroom and program room are 1 to 2 m wide, full-depth strips labelled "OT"; the harm reduction room has no label. "Desk sees the entry" passes because the desk is "beside" the entry. Nothing checks that the desk can see the lift lobby and the stair doors, which is what a supportive operator checks first.
7. **The block editor accepts overlaps.** A corridor dragged onto the core gave "Nothing broken on the ground floor".
8. **"SUGGESTED Funder-ready" stays on the card** after storeys, height and floor area are all marked "yours".
9. **The Revit panel prints the full local OneDrive path**, user folder included.

## 5. What works and I trust

- Answer 1 as three verdicts, and "Not assessed" for an unread CD-1 instead of a false yes.
- The use table at 02, with page references and "a question for the City" for a shelter.
- The nearest-station tier suggestion with "so confirm", and the honest note that the data has no bus exchanges.
- Answer 2 refusing to test supportive housing or shelters against the Community Housing Fund and BC Builds, and listing the Supportive Housing Fund, Reaching Home, the Emergency Shelter Program and HEARTH with how a project enters each.
- The UNVERIFIED tags, the parcel-area discrepancy notes, and the memo itself saying the wood-frame cost is wrong for 18 storeys.
- The block editor's exit mechanics: shrinking the core or breaking the corridor ring fails the exits and shows the clause and the numbers.
- Speed (under half a second a run), the fingerprint and the revision numbering.

## 6. Wish list (top five first)

1. **Size the core from the lift count and the stairs.** Draw the lifts with stretcher-size shafts, the lift lobby, the garbage chute and the electrical room, and fail the plan when they don't fit. **L**
2. **Supportive and shelter money on their own terms.** Shelter-rate or rent-geared-to-income rent on every supportive home, operating cost per bed, and no Community Housing Fund rent tiers unless the housing is independent rental. **M**
3. **Build the section and areas from the real podium and tower.** The area schedule should tie to the option within 0.5%, with the FSR exclusions shown. **M**
4. **Mixed buildings.** Allow more than one wing, tenure and entry on a site: a market wing, a social wing, and a shelter with its own entry and lift. **L**
5. **Operator checks that matter.** Desk sightlines to the entry, the lift lobby and the stair doors; the harm reduction room next to the desk; shelter washrooms per bed; sleeping rooms of no more than 4 beds; a lift for any shelter above grade. **M**
6. Tower separation (24 m) and limiting-distance checks against neighbouring buildings. **M**
7. A separate ground-floor height and podium floor-to-floor. **S**
8. Beds and tower-plate fields in Manager mode. **S**
9. Record who issued each revision, and send "issued to you" to a named person. **M**
10. One rule count on every page, and the Vancouver Building By-law as the code basis for Vancouver sites. **S**
11. A scale warning on supportive buildings over about 100 homes. **S**
