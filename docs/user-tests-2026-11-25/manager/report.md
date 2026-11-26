# User test: development manager, 25 Nov 2026

Reviewer seat: an AI role-play of a development manager at a Vancouver non-profit housing society (redevelops its own church or society land with housing over community space; also runs youth and transitional housing). Not a practitioner. Own server on port 8791, own browser tab, Manager mode throughout except one check in Architect mode.

Runs made: 3475 E Hastings St (C-2, R1 issued to the architect), 609 Heatley Ave (RT-3, transitional, R1 issued to the operator, then Draft 18:34 compared against it), 4250 Fraser St (C-2A, draft), plus look-ups of 3680 E Hastings St (wrong number) and 1290 Burrard St (CD-1).

(Saved by the coordinating session from the reviewer's returned text: the harness does not let a subagent write files.)

## 1. Verdict

I would not put a First Read memo in front of my board next week. I would use it as a private pre-screen, to get the use table, the yards and the program list for a site in ten minutes, and to write my questions for the architect. Four things stop me. First, the community hall and society offices I entered in the program brief are invisible to the zoning check, the funder check and the money, so on a church-type site it told me I need a rezoning I may not need. Second, reopening an issued revision does not bring back its inputs, so R2 cannot be "R1 plus one change". Third, answer 1 contradicts itself on the same screen ("Outright No" and "the option is allowed outright"). Fourth, transitional housing is costed with market and RGI rent tiers, and a memo where 0 of 6 homes fit the plans still prices 6 homes. Fix those and I would trust it as a first-pass memo.

## 2. The flow as I walked it

**Website (home, how, case).** The home page states the four questions well and the walkthrough link is the obvious next step. I lost trust on numbers: the home page says the engine "checks the option against 144 rules" and, further down, "84 rules in six layers"; the tool then says "Clauses applied · 26 of 176 rules". The How page says "The approved case has eight" open items, while the home page, the case page and the How page's own diagram text say seven. The How page sells "Three stops in the tool" and draws 1 site, 2 option, 3 run, 4 memo, with no money step, but the tool's third stop is "Money in, then run". The case page is the best page: one row of the memo with proposed against permitted and "the ask" sold me on the format.

**01 The site.** Wrong number (3680 E Hastings St): the card correctly refuses the far parcel ("You typed 3680 ... the parcel found is number 117, 3,563 civic numbers from 3680 ... more than a block away") and offers "Look up 3683 E Hastings St", which worked. But the green status bar above it says "Found 117 E Hastings St ... Check the parcel on the map, then use it." and the card is titled "Is this the parcel?". Mixed signals on the one screen where I need a clear no.

At 3475 E Hastings the lane suggestion ("a lane runs behind the lot, its centre line about 5.8 m past the rear lot line. Use it") is exactly right. The transit question was less useful: "The nearest SkyTrain station is Rupert, about 2,289 m away (the City's station data, which holds no bus exchanges ...)". This site's reason for being transit-oriented is the bus exchange, and the tool cannot see it. At 1290 Burrard the SkyTrain tier suggestion ("3 · SkyTrain, 800 m, as about 700 m from Yaletown - Roundhouse station ... so confirm") is good. Water and sewer comes pre-answered "Yes"; every other question defaults to "Not sure". At 609 Heatley, "Which street is the front?" defaulted to Keefer St with no reason given, although its own hint says to use "the address the City lists" (Heatley Ave). "Save site as…" says "Names sites/<id>.json, so the run can be repeated from the command line". That is developer language, and I did not save.

**02 The option.** "What the lot takes" is the most useful new panel: plate, yards and the use table read per building type with page cites. But at 3475 it says "Outright: 6 storeys, 7,612 m² (FSR 3.5), about 89 homes" and two lines later "an apartment building here is not allowed outright". At 609 Heatley it says the small-scale minimum is "6 if a prescribed frequent bus stop is within 400 m (not answered)", but 01 never asks that question.

The program brief hides under "WHAT IT RUNS ON > What it runs on · no brief: the amenity and services only". I would never have opened that disclosure to add a community hall. It re-collapsed after other edits. "Where" offers only "ground floor" or "upper floors", so I cannot put a church on level 1 and offices on level 2.

For transitional youth housing I changed homes from 4 to 8: storeys silently dropped from 3 to 2 and height from 9.9 to 6.6 m. The mix presets are Starting, Family, Seniors singles and Balanced, with no rooms or studios preset for transitional or supportive housing. "Derive with this mix" at 100% studios threw away my 8 homes and gave 6. The warning line read "this lot's envelope gives 4", then "gives 8", then "gives 6".

**03 Money in, then run.** "What are you asking for?" printing on the front sheet is right. The money fields are workable but unformatted (1500000 shows with no separators). "Land ($)" next to "The land's value ($)" took me two reads. "Other grants ($)" sits beside a separate "Capital sources" list, so there are two places to type the same grant. For transitional housing, "What it takes to run" opens by default with "Support staffing ... Never assumed", which is right. The confirmation checkbox "The operating subsidy is confirmed, with an agreement in hand" is good. Runs took about 350 ms.

**The memo.** The "The ask" front sheet reads like something my board would read. "Where the money comes from" lists each source with its status and keeps the land contribution "in kind · not in the funding total", which is correct. The defects are in section 3.

**Paper memo (iframe).** Clean typography. But the option is called "Suggested, funder-ready" on paper and the proponent is "— (non-profit society)"; the tool never asked my society's name. The "Short" memo for 3475 is about 6,900 px tall at screen width, roughly 6 to 7 printed pages. That is not a two-page board summary.

**Issuing.** Issuing to the architect worked: "Draft 18:27 is now R1, issued to the architect ... as Development manager", and the architect view shows my note under the title. Issuing to the operator worked, but with "To: The operator" selected the help text still says "the architect's layout here shows it", and the button above still reads "Mark issued to the architect" after the issue. My own manager view of R1 does not show the note I sent.

**Reopening and comparing.** There is no list of my projects. The issued 3475 R1 is not in "or a saved site", so I had to retype the address to find "This site has 2 memos". Compare (609 Heatley, R1 against Draft 18:34) gives a clear table with HOMES THAT FIT THE PLATE 0 → 4. But see defects 2 and 7.

**Phone (375 px).** The header is 263 px tall, a third of the screen. On the option step the program-brief table forces the page to scroll sideways (page width 437 px at 375). The memo page is about 21,900 px tall.

## 3. Defects, ranked by harm

1. **Program-brief community space is ignored by zoning, funders and money.** *Verified twice.* 3475 E Hastings St, Manager mode: answer the site questions, then at 02 add "Community hall and kitchen" 450 m² on the ground floor and "Society offices and youth drop-in" 900 m² on upper floors. At 03 set "Cost of the floors that are not homes" to 5,500 and their income to 60,000, then run. Expected: about 1,350 m² of non-dwelling use counted. Saw: A1 "FSR 3.00 exceeds the outright maximum of 0.75 (3.5 is open to a building with every home rental and 0.35 FSR of non-dwelling use at the street ... this option has 0 m², FSR 0.00)" and "By rezoning Needed". BC Builds reads "0 m² non-residential". Hard cost is exactly 6,525 m² × $4,693 × 1.0311, so the $5,500/m² was dropped. At 4250 Fraser St (C-2A), I added 350 m² of community space at grade. The tool added its own "non-residential 210 m²" on top of it, and BC Builds counted only the 210. The area schedule shows the hall, so the engine knows the space exists but never treats it as non-residential.
2. **Reopening a revision loses its inputs.** *Verified twice.* Open `?run=3475-e-hastings-st/2026-11-25T18-27-19` (or the site's "R1" link), then click "The option". Expected: R1's inputs. Saw: a fresh suggestion of 80 homes at FSR 3.50 (R1 had 74 homes at FSR 3.00), an empty brief, and approval route, operator and tenure blank. The site step shows owner "not sure". Same at 609 Heatley R1: 4 homes instead of 6, and approval route, site control and land "Not sure". The status even claims "The option changed after R1". Running again from there silently makes a different project.
3. **Answer 1 contradicts itself.** *Verified twice* (609 Heatley Ave; 4250 Fraser St). The memo shows "Outright No · the building is a conditional approval use", then "By rezoning Not needed · the option is allowed outright", the footer "Allowed outright; no rezoning is proposed or needed", and the heights figure "Allowed today, no vote needed". The comparison table says "Allowed outright: Yes, with conditions". At 3475 the heading reads "Approval route, no rezoning: CD-1 under the Interim Rezoning Policy". The reason for "By the Director's discretion: No" differs between screen ("another limit is exceeded beyond what the Director may allow") and paper ("a discretionary approval, never assumed").
4. **Homes that do not fit are still priced and funded.** 609 Heatley, transitional, ground-oriented, 6 studios: "0 of 6 homes fit the plate", the plans show empty floors with 104 m² "Spare", and in green "Egress: 0 exits, 0 required · pass". Capital, rents and funders all count 6. At 3475, 46 of 74 fit with 336 m² spare, and the money counts 74. Seen once at 0-of-6; the counting pattern appeared on three sites.
5. **The operating table does not add up when non-home floors earn income.** *Verified twice.* At 3475 the lines sum to $593,000 but "Left after running costs $653,000": the $60,000 income has no line. At 4250 Fraser the lines sum to $102,475 against $142,475 (the $40,000).
6. **Transitional housing is costed as Community Housing Fund rental.** 609 Heatley, transitional youth housing: "2 at market rent, 3 rent geared to income, 1 deep subsidy", with market at $1,963 a month. I could only override the deep-subsidy rent. The front sheet's "The amount" lists only capital; the operating subsidy, the real ask for this housing, is not on the front sheet.
7. **Compare and the run lists hide what changed.** I switched ground-oriented to apartment and named the operator. Compare says "R1 and Draft 18:34 propose the same building" and "Every rule reads the same", has no rows for building type or operator, and shows open items 9 → 8 without naming the one that closed. Every run on 609 Heatley is labelled "Suggested, funder-ready", four identical entries in "Open a memo".
8. **Figures that disagree inside one memo.** At 3475, C6 reads "Uncertain ... no tree survey is on file" while FIG 01 says "Trees: Schedule C asks 12, the plan leaves 12" and the plan checker says pass. The lot is "2,157 m²" in FIG 01 and the code site plan, and 2,174.9 m² everywhere else. At 609 Heatley the gap is "68% of the capital cost" in the heading and 69% on the front sheet. At 02 the "Land tenure ... settle the tenure" bullet stayed after I chose "Owned by the proponent".
9. **Wrong-address screen says yes and no at once.** 3680 E Hastings St: a green "Found ... then use it" bar sits over a refusal card titled "Is this the parcel?". Seen once.
10. **The small-scale bus-stop question is referenced but never asked** ("(not answered)" at 609 Heatley, 02). Seen once.
11. **Editing one figure silently changes others.** Homes 4 → 8 dropped storeys 3 → 2 (609 Heatley). Seen once.
12. **Sources with no status control.** "Money raised for them" and "Equity" appear as "entered, status not given", but there is no control to give a status. The chart legend repeats "Other grants" three times. Formatting: "$-336,265", "$-0", "1 homes".
13. **Issue form wording** stays on the architect after choosing the operator (see section 2). Seen once.
14. **Phone: the brief table forces sideways scrolling of the page.** Seen once.
15. **Shared machine, no identity.** "375 Glen Drive · a run issued to you by the operator" appeared in my top bar from another user, and other users' drafts appear in my lists. In a shared office that is a privacy and confusion problem. This may be partly a test-setup artefact, since several servers wrote to one folder.

## 4. Interface problems, ranked

1. **Length.** Neither the memo nor the "Short PDF" is the two pages a board reads. Lead with the front sheet, the four answers, the money bar and the top open items, and put everything else behind them.
2. **Disclosures re-collapse on every edit**, and refs (and focus) are lost because the page re-renders after each answer. The program brief's label, "What it runs on · no brief: the amenity and services only", does not say "add community or church space here".
3. **Step names disagree:** the stepper says "03 Run", the card says "Money in, then run", and the How page says three stops.
4. **The sticky status banner grows to two lines and covers the page title** after issuing.
5. **"2 option answers not sure · 1 site answer not sure"** does not name which answers; I want the list with links.
6. **Approval route offers rezoning, development permit or outright.** It has no "conditional use, Director's discretion", although 02 and answer 1 use that idea.
7. **"None, or not sure"** in the area-plan list merges two different answers, against the page's own "Not sure is a fine answer".
8. **Money inputs lack thousands separators**, and land and grants have duplicate entry routes.
9. **Mobile header** is a third of the screen; the notification pill wraps to two lines.
10. **"Suggested, funder-ready"** as the option's name on board paper; I need to name options myself.

## 5. What works and what I trust

- The address lookup's refusal of a far parcel, with the distance and the nearest real number offered.
- The lane and SkyTrain suggestions: each states the distance and its source, and says "so confirm" where the City's map rules.
- The use table at 02 by building type (apartment, ground-oriented, shelter, clinic), each with a page cite. A shelter is "a question for the City" rather than a guess.
- For transitional housing, the Community Housing Fund and BC Builds read "Not applicable" rather than Fail, and the other programs are listed with their intake status (CHF 2025 call cancelled, CHIP "no funding call is open").
- UNVERIFIED flags, labelled placeholders, sources with dates, and the fingerprint. The tool admits its cost base is a four-unit catalogue figure.
- The operating table's intent: support staffing never assumed, an unconfirmed subsidy as an open item, and "Subsidy needed ... $4,670 a home a month".
- The stale-run guard ("The inputs changed after this run: run the rules again before issuing it.") and the issue note that reaches the architect.

## 6. Wish list (top five first)

1. **A project list** of my sites, revisions and drafts, who each was issued to, and the notes. Reopening restores every input, so R2 is R1 plus a change. (L)
2. **Non-residential program as a first-class input:** church, community and office floors with use, floor, area, cost, income and their own funding, feeding the zoning check (non-dwelling FSR), the BC Builds 30% cap and the plans. (M)
3. **A true two-page board memo:** front sheet, four answers, money bar, top five open items; the rest as appendix. (M)
4. **A supportive and transitional mode:** rooms or beds, rent at shelter rate by default, a staffing model, the operating subsidy as the headline ask, and supportive-housing program criteria tested rather than listed. (L)
5. **A credible cost base for four- to six-storey buildings**, editable soft costs and contingency, and a ±10% sensitivity line on the gap. (M)
6. **Compare shows input differences** (building type, operator, brief, money) and names the open items opened and closed. Let me name options. (S)
7. **A proponent name field and a "population served" field** (youth, seniors, women) carried to the front sheet. (S)
8. **Bus exchanges in the transit suggestion, and the frequent-bus-stop question at 01.** (S)
9. **One consistent rule count and open-item count** across the site and the tool. (S)
10. **Signed-in identity for issuing**, so "issued to you" means me. (M)
