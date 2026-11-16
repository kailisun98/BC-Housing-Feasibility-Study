# First Read: forms, states, errors, accessibility, responsive

Critic 3 of 3, 15 Nov 2026. Sources: the evidence pack, all sixteen screenshots, PRODUCT.md, DESIGN.md, docs/user-flows.md, `ffm/ui/index.html`, `ffm/ui/app.js` (renderForm / renderField / labelHtml / FIELD_META, renderGuideInto, answerControl, guideLookup, guideUseOptionNow, guideDone, runRules, answerMoney, setStatus, saveAs), `ffm/ui/app.css` (forms, guide, touch and breakpoint rules). No browser; where code and the evidence pack disagree I say so.

## 1. Design-specificity verdict

The forms are more specific than most tools in this class: a field says whether the engine needs it, a rule reads it, or only the drawings use it; "not sure" is a real amber answer and not an empty checkbox; every suggested figure sits next to its rule id. The way the page handles states doesn't match that care. The guide redraws itself with `innerHTML` on every click and drops keyboard focus. Disabled controls give the wrong reason. Bad numbers quietly turn into "not sure". Errors appear in a strip at the top of the page, away from the field that caused them. The money answer says "not given" for figures nobody was asked for. The tool is honest about the rules, but its own state messages aren't yet as reliable.

## 2. Nielsen's heuristics (0 to 4)

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 2 | The strip reports every action, but the 8 s lookup shows only a spinner dot with no stage, elapsed time or cancel. "edited, not saved" sits inside the folded card, so you can't see it. A memo is never marked stale after an edit. Stage card 04 says "UNITS not set" while the rail shows 4 units (shots 8, 9). |
| 2 | Match with the real world | 3 | Plain sentences and named people. But Python leaks into the copy ("site control 'None'", `'609 heatley'` repr quotes in the lookup error), and "not given" sounds as if the manager failed to supply a figure the engine actually couldn't compute. |
| 3 | User control and freedom | 2 | Change the site, Derive again and Suggested / Mine are all reversible. A refresh throws away the lookup, the programs, the reading, the suggestion and every Mine figure, with no warning. Clicking another candidate silently clears `guide.mine`. A running lookup can't be cancelled. |
| 4 | Consistency and standards | 2 | Two Yes / No / Not sure implementations: the Site form's radiogroup has a roving tabindex and arrow keys, the guide's `answerControl` has neither. The two Run buttons are enabled by different rules. Money and the policy-area answers can each be entered in two places on one screen. |
| 5 | Error prevention | 1 | `type="number"` turns "1,200,000" or "$1.2M" into a blank, so it reads as "not sure". The guide's share fields have no 0 to 1 check. `owner_type` is free text, and a regex on it decides whether land is nominal. The Run button isn't disabled while running, so a double click writes two output folders. "Save as…" overwrites without asking. |
| 6 | Recognition rather than recall | 3 | The marks, the legend's live counts and the rule ids beside each figure do the remembering for you. The (i) note disappears on the first scroll. A "Left to a person" answer sits far from the Site-card field it writes. |
| 7 | Flexibility and efficiency | 2 | Ctrl+Enter, three modes and saved sites and options all help. There's no keyboard path through the guide that keeps your place, and a phone user has to scroll back to the top to run. |
| 8 | Aesthetic and minimalist design | 2 | The stop-4 list is about 19 rows with two toggles each, plus 8 questions. The money table repeats a long CMHC source title in full on four rows. |
| 9 | Help users recognise and recover from errors | 1 | "Type an address first." shows in a red strip at the top (shot 2), and also for "609", which is already typed. No field is marked invalid. The disabled Run at stop 5 gives a false reason. A run error shows the raw `e.message`. |
| 10 | Help and documentation | 3 | A walkthrough, an (i) on every field and help lines under the actions. The (i) note isn't connected to its button for a screen reader. |
| | **Total** | **21 / 40** | |

## 3. Cognitive load

The eight checks:

1. Single focus per view: **fails.** At stop 4 the page shows the tour offer, the mode switch, the date, two Run buttons, seven stop heads, three candidates, the suggestion list, eight questions, the Site card below, and a stage that disagrees with the rail.
2. Chunks of four or fewer: **fails.** See the counts below.
3. Clear grouping: **passes in the forms** (eyebrow groups with hairlines). **Fails in "Left to a person"**, which mixes site facts, option facts and items that have no control at all.
4. Visual hierarchy: **passes.** One signal-blue button, the ink primary in the rail, amber for pending.
5. One thing at a time: **mostly passes** (the guide). **Breaks** because the Site card opens under the guide after stop 1 and asks the same policy-area questions as stop 4.
6. Minimal choices per decision: **fails at stop 4.** Every figure is a two-way choice, so about 19 decisions are made before "Use this option".
7. Working memory: **fails.** After "Use this option", stop 5 says "Shape or pick an option first." You have to work out on your own that the blank Storeys row is the reason.
8. Progressive disclosure: **passes.** The Claude folds, the "Every line" table and the card summaries.

Decision points with more than four visible options:

| Decision point | Count |
|---|---|
| Site form | 5 groups. Identity 4, Lot 3, Policy areas 5, Trees (a table plus 1), Owner 4: about 17 controls before any tree row. With the legend and an (i) per field, about 30 interactive elements. |
| Option form (architect, shot 14) | 9 groups, about 31 fields |
| Suggestion list at stop 4 (shots 8, 9), RT-3 funder-ready | 19 rows (rezoning path, storeys, height, GFA, four unit types, three tiers, accessible, agreement, replacement trees, floor to floor, three setbacks, and a share row where a rule gives it). That is 38 toggles plus 4 inputs forced to Mine. |
| "Left to a person" at stop 4 | 8 items. 6 have controls (4 Yes / No / Not sure, 1 select, 1 text); GFA and trees have none. |
| Guide | 7 stops, always visible |
| Stop 4 head | 3 candidates plus a saved-option select plus Suggest |
| Stop 6 after the run (shot 11) | 4 answer rows plus "Left to a person" plus Run again |
| Top bar plus memo tools | 3 modes, date, Run, Walkthrough, 2 pickers, 3 views |

## 4. States inventory

Key: **present**, *missing or silent*.

**Address lookup (stop 1)**
- **Empty:** an example placeholder. Clicking Look up gives "Type an address first." (shot 2), and it fires for any input under 4 characters (`q.length < 4` in `guideLookup`), so "609" is told to type an address. *The field is not marked; focus is not moved to it.*
- **Loading:** the button reads "Looking up…" and is disabled; the strip is busy with an amber spinner. *Nothing shows on the stage, nothing says which of the four fetches is running, there is no elapsed time and no cancel. Overpass can take half a minute and the copy only warns about it in CLAUDE.md. `renderGuide()` replaces the button and the input, so focus falls to `<body>` both when the lookup starts and when it ends.*
- **Success:** the found-site list plus a green strip (shot 3). *The stage doesn't change until "Use this site", and nothing says "preview, not yet used".*
- **Partial:** "not found: enter it" and "no parcel found" in the list; a marker instead of a ring on the stage. *Nothing says where to enter it (the Site card doesn't exist yet). An address in Burnaby or Surrey is inside Metro Vancouver, so it passes the geocoder and is then read against Vancouver rules. There is no "outside the City of Vancouver" state, and `municipality` is only an (i) note.*
- **Error:** a red strip reading "Lookup failed: Nothing in Metro Vancouver matched '…'", with Python repr quotes. *`guide.lookup = null` throws away a good earlier result because of one typo.*
- **Dirty:** *missing.* Edit the address after a successful lookup and the old result stays under the new text; "Use this site" then uses the old one.

**Suggestion (stop 4)**
- **Empty:** the candidates plus "Suggest from the rules". **Loading:** "Deriving…". **Success:** the rows with rule ids.
- **Partial:** amber "placeholder" rows, "—" values, Storeys / Height / GFA forced to Mine with an empty box. *An empty Mine box looks the same as a filled one at a glance.*
- **Error:** the strip only.
- **Dirty:** Mine figures are kept in `guide.mine`. *Clicking another candidate wipes them silently (`guide.mine = {}` in the `.cands` handler).*
- **Derived but not used:** *missing.* Stage card 04 reads "UNITS not set · TIERS not split" beside a rail that lists 4 units and the tiers (shots 8, 9).
- **Stale:** answering a site question asks you to "Derive again" in the strip only. *The list isn't marked as out of date.*
- **Applied:** "with 3 of your own figures". *It counts the three blank Mine rows as figures.*

**Run**
- **Not ready:** stop 5's Run is disabled with "Shape or pick an option first." (shot 10). *That reason is false: `guideDone()[4]` needs `option.storeys != null`, and Storeys was a blank Mine row.* The top-bar Run is never disabled, and *with no site or option `runRules` returns without a word.*
- **Loading:** "Running…" plus a busy strip; on the static build "Loading the engine…". *The button isn't disabled (`.btn.busy` keeps pointer events), so Ctrl+Enter or a second click starts a second run.*
- **Success:** a green strip with the revision, the time and the output folder; the page scrolls to the memo.
- **Error:** the strip with the raw `e.message`.
- **Stale:** *missing.* Edit the Site, the Option or Money in after R1 and the memo still looks current. Only the stop-6 help line mentions "Run again".

**Money answer (answer 04)**
- **Not computed:** "Not computed." plus the engine's reason. **Success:** Likely / Unlikely with four figures and the table (shot 13).
- **Partial:** "Unsure. No floor area, so no capital cost." This verdict is good. *But the Capital and Gap cells then read "not given", the hard line in the table is still multiplied out, and nothing links to the field that would fix it.*
- **Dirty:** *missing.* Typing a land figure after the run changes nothing on screen, and `fin-input` sets `optionDirty` without showing `#option-dirty`.
- **Loading:** none needed (it arrives with the run).

## 5. Strengths

1. **"Not sure" is a real answer, and the Site form does it properly.** `renderField` for a three-state field builds a `role="radiogroup"` with `aria-labelledby`, a roving tabindex and arrow keys, and Not sure fills amber with its own text. That makes PRODUCT.md's "uncertain is the honest outcome" a control a person can actually use, and it matches DESIGN.md's spec word for word. It's the right pattern; the problem is that the guide doesn't use it.
2. **The need legend explains what a blank costs.** "needed to run: 5 of 5 · read by a rule: 1 of 6 (a blank comes back as uncertain)" (shot 7) is a live count, it tells you what happens if you leave a field empty, and each mark has `sr-only` text. Most forms only say "required". This one says what the engine will do with your blank.
3. **Every figure carries its provenance, and replacing your edits is confirmed on the page.** Suggested | Mine with the rule id and a one-line note (shot 8) puts the citation at the field. `guideUseOptionNow` and `guideUseSite` ask "Replace the edited option" with a second click on the same button instead of a `confirm()` box, which keeps a keyboard user in place and tells them why.

## 6. Priority issues

### P0-1. The guide throws away keyboard focus on every interaction
- **What:** `renderGuide` → `renderGuideInto` sets `el.innerHTML` for the whole guide on every stop-head click, every Yes / No / Not sure in "Left to a person" (`wireGuide`: `takeAnswer` then `renderGuide(...)`), every Suggested / Mine click, the lookup start and end (`guideLookup`), Read, Suggest and Use. The element that had focus is destroyed and focus drops to `<body>`. Only the Mine path re-focuses its input. Pressing Enter in the address field (shot 1) loses focus twice. `renderGuide` restores the scroll position but not focus. Separately, the guide's `answerControl` renders `role="radio"` buttons with no tabindex management and no arrow keys, so all three are tab stops, which contradicts DESIGN.md "one tab stop on the chosen answer".
- **Why:** Sam can't complete stop 1 without hunting for where they are after each action. This is the main path through the tool, and it fails WCAG 2.4.3 Focus Order and 2.1.1 Keyboard in practice, plus 4.1.2 for the radio pattern.
- **Fix:** In `renderGuide`, before `renderGuideInto`, record `const key = document.activeElement && el.contains(document.activeElement) ? focusKey(document.activeElement) : null`, where `focusKey` returns `#id` or `[data-stop="n"]` / `[data-answer="k"][data-value="v"]` / `.sg-row[data-key="k"] [data-pick="p"]`. After rendering, `$(key, el)?.focus({ preventScroll: true })`. When a stop advances (`guideUseSite`, `guideReadSite`, `guideUseOption`), focus the new stop's head or first control. Replace `answerControl`'s tri with the same builder as `renderField`'s TRI (`tabindex="0"` only on the checked one, ArrowLeft / ArrowRight move and select). Better still, extract one `triControl(label, value, onChoose)` and use it in both places.

### P0-2. Stop 5 is disabled with a false reason, and the two Run buttons disagree
- **What:** Shot 10. After "Use this option" the strip says "Run the rules when it reads right". Stop 5 says "Shape or pick an option first.", the three Money fields are `disabled`, and its Run the rules is disabled. Meanwhile the top-bar Run works. The reason is `guideDone()[4]`, which needs `state.option.storeys != null`; Storeys was a Mine row left blank on an RT-3 site. `guideUseOptionNow` also reports "with 3 of your own figures" when all three were empty. When no site or option exists, `runRules()` returns silently.
- **Why:** The page contradicts itself on its single most important action. The manager takes "shape an option first" to mean the option didn't take. Disabled fields also hide what's missing from screen readers (WCAG 3.3.1, 3.3.2).
- **Fix:** One predicate, `readiness()`, returning `{ ok, missing: [{key, label, stop}] }`, used by stop 5, stop 6, the top bar and Ctrl+Enter. Leave the Money fields enabled whenever a site exists. Either let Run go ahead with blanks (the engine already says what it couldn't compute) or disable it with an adjacent, `aria-describedby`-linked line that names the field: "Storeys is blank (stop 4, Mine). Enter it, or the massing assumes one storey." Count only non-blank Mine values in the status ("with 0 of your own figures; 3 left blank: Storeys, Height, GFA"). In `runRules`, replace the silent `return` with `setStatus("Find a site at stop 1 first.", "error")`, and set `btn.disabled = true` while running.

### P1-3. Numbers are silently coerced into "not sure"
- **What:** `renderField` and `.fin-input` use `type="number"`. A browser returns `""` for "1,200,000", "$1.2M" or "30%", the handler stores `null`, and the field's own placeholder then says "not sure". The Land field at stop 5 even suggests a blank is acceptable ("blank leaves the mone…", cut off in shot 10). The guide's share rows (`share_below_hils`, `below_market_*` in `GUIDE_FIELDS`) have none of the form's 0 to 1 warning. `owner_type` is free text ("church, society…"), and the regex `/church|society|…/` in stop 5 silently decides whether land is nominal: "Parish of St Mark" or a typo puts the money answer into Unsure.
- **Why:** The tool is honest about uncertainty, so this is the worst place to create uncertainty the user didn't choose. WCAG 3.3.1 Error Identification, 3.3.3 Error Suggestion.
- **Fix:** Use `type="text" inputmode="decimal"` and a `parseAmount()` that strips `$`, commas and spaces and accepts `k` / `M`. On a parse failure set `aria-invalid="true"` and show an inline `<span class="help warn" id="…-err">` ("Not a number: write 1200000 or 1.2M"), referenced by `aria-describedby`, and keep the typed text. Add `share: true` handling to the guide's share rows. Make `owner_type` a select (church or faith society, non-profit society, co-op, First Nation, municipal, provincial, private, other). Placeholders must not carry instructions that get cut off: move "blank leaves the money answer unsure" into a help line under the field.

### P1-4. Errors appear far from their cause, in a polite region that scrolls off a phone
- **What:** `setStatus` / `toast` write every message, errors included, into `#status` (`role="status" aria-live="polite"`) at the top. Examples: "Type an address first." (shot 2), "Lookup failed: Nothing in Metro Vancouver matched '609 heatly'; …", "Could not read the site: …", and a run failure's raw `e.message`. Under 760 px `.bars { position: static }`, so on a phone the strip is several screens above stops 4 to 6.
- **Why:** The error isn't where the fix is, nothing is marked invalid, and a screen reader hears an error at the same politeness as "Programs chosen". WCAG 3.3.1, 4.1.3 Status Messages, 1.3.1.
- **Fix:** Give `setStatus(msg, kind, { field })` an option to also render the message under that field (`aria-invalid`, `aria-describedby`) and move focus to the field. For `kind === "error"`, use a separate `role="alert"` node. Copy: "Type a civic number and a street, e.g. 609 Heatley Ave." Strip Python repr from the server message (`lookup.py` line 116: use `{address}` instead of `{address!r}`). Under 760 px keep `#status` sticky (`position: sticky; top: 0`) or mirror the last message inside the open stop. Keep the previous `guide.lookup` when a new lookup fails.

### P1-5. The money answer's "not given", and the engine's 'None', put the blame in the wrong place
- **What:** `answerMoney` prints `money(null)` as "not given" for Capital and Gap (shots 11, 13), next to a verdict that correctly says "No floor area, so no capital cost". The funders answer reads "site control 'None' does not meet the RFP's readiness bar" when the manager chose Not sure (`answerControl` "Not sure" sends `null`, which Python prints as `None`). The CHF answer fails a 1 / 2 / 1 mix the tool derived from the fund's own 30 / 50 / 20 on 4 units, and the suggestion never warned that 4 units can't meet a 2% tolerance.
- **Why:** "not given" and 'None' read as the manager's omission or choice. This undermines trust in exactly the answer the board reads, and the honest cause is already known to the engine.
- **Fix:** `money(x, why)` → "not computed: no floor area" when `x == null` and `pf.verdict.why` names the cause. Add a button under the four figures, "Give the floor area", which opens stop 4 (or the Option form's GFA in architect mode) and focuses the input. In the engine finding, render `None` as "not given (answered Not sure)". In `suggest.py`'s note on the tier rows, say: "4 homes cannot meet 30 / 50 / 20 within 2%; the nearest split fails the fund's mix check". In the stage card 04, show the pending suggestion as "suggested, not used yet: 4 units" instead of "not set".

### P1-6. Unsaved and stale states are invisible, and a refresh loses the whole session
- **What:** `#site-dirty` and `#option-dirty` ("edited, not saved") live inside `.form-fold`. `guideUseOptionNow` calls `setCollapsed("option", true)`, which hides the note at the moment the option is new and unsaved, and the summary line (`optionSummary`) never says "unsaved". The stop-5 `fin-input` handler sets `optionDirty` but never unhides the note. There is no `beforeunload`, and `guide` (lookup, programs, reading, suggestion, `mine`, answers) is kept only in memory. Nothing marks a memo stale after a later edit. "Save site as…" / "Save option as…" use `window.prompt()`, transform the id silently, and don't check for an existing file.
- **Why:** Riley's refresh, or a mis-tap on the wordmark (a link to the home page), throws away ten minutes of answers without warning. A board could get a PDF of R1 after the inputs on screen had changed. WCAG 3.3.4 applies in spirit.
- **Fix:** Append `· <span class="dirty">unsaved</span>` in `siteSummary` / `optionSummary` when dirty. Add `addEventListener("beforeunload", e => { if (state.siteDirty || state.optionDirty || guide.lookup) e.preventDefault(); })`. Persist `guide` and the unsaved site and option to `sessionStorage` on each change and offer "Resume where you were" on load. After a run, set `state.runStale = true` in `onSiteChange` / `onOptionChange` / `fin-input` and put an amber band at the top of the memo: "The option changed after R1. Run again before you issue it." Disable Issue and Download PDF until you either run again or click "Use R1 as it is". Replace `prompt()` with an inline id field that shows the cleaned id as you type and asks before overwriting (server 409).

### P2-7. Touch, phone layout and target sizes
- **What:**
  - `.sg-pick .segbtn { min-height: 22px }` and `.answer-ctl .tri button { min-height: 24px }` are more specific than the coarse-pointer rule `.segbtn, .tri button { min-height: 44px }`, so on a phone the Suggested / Mine and the guide's Yes / No / Not sure stay at 22 to 24 px.
  - `.info-btn` is 16 px on desktop (fails WCAG 2.5.8's 24 px) and 28 px on touch.
  - Every input is 12.5 px, which makes iOS Safari zoom in on focus.
  - The Leaflet map (`L.map(box, { scrollWheelZoom: false })`) keeps one-finger dragging, so a thumb scrolling the stage pans the map instead.
  - Shot 16: the mode-switch thumb overhangs "Manager" (`placeModeThumb` measured before the web font loaded).
  - The tour offer, the status and the rail head push the first input to the lower third of the first screen, the memo is several screens down, and under 760 px the top-bar Run scrolls away.
- **Why:** Casey can't hit the controls reliably with one thumb, and the page zooms and pans under them. WCAG 2.5.8, 1.4.10.
- **Fix:** Add `@media (pointer: coarse) { .sg-pick .segbtn, .answer-ctl .tri button { min-height: 44px; } .info-btn { width: 44px; height: 44px; } }`. Use a 24 px hit area on fine pointers (a transparent `::before` pad). Use `font-size: 16px` on inputs under 760 px. Pass `dragging: !L.Browser.mobile, tap: false` to the map and add "Two fingers to move the map". Re-run `placeModeThumb` on `document.fonts.ready`. Under 760 px, hide the tour offer after the first stop and make a sticky bottom bar with "Stop n of 7" and the next action ("Run the rules" once ready).

### P2-8. Screen-reader semantics of the forms and the (i) notes
- **What:**
  - Form groups are `div.group` with an eyebrow, not `fieldset` / `legend`. Labelled rows ("Setbacks (m)", "Rent tiers (units)") are a bare `span` (`renderField` `f.row`), so the inputs announce as "Front", "Rear", "Market". The row mark there has no `sr-only` text, unlike `labelHtml`.
  - The evidence pack's tree named the stop-2 checkboxes by rule id and the stop heads as unnamed. The code labels them implicitly (`<label><input> <span>title</span></label>`; the stop head has text spans), so the tree may be wrong, but the Option form's program labels include `<code>bch.chf.eligibility</code>` inside the label, so the id is read aloud. The stop heads' done state is a "✓" glyph only.
  - `openInfo` appends a `role="note"` div at the end of `<body>` with `pointer-events: none`, not referenced by the button, and closes it on any scroll in the document. A screen-reader user hears "About Area, button, expanded" and nothing more.
  - `#stage-map` has an `aria-label` on a role-less div.
- **Why:** WCAG 1.3.1 Info and Relationships, 2.4.6 Headings and Labels, 4.1.2 Name, Role, Value.
- **Fix:**
  - `renderForm`: wrap each group in `<fieldset><legend class="eyebrow">`. A labelled row becomes `<fieldset class="field-row"><legend>Setbacks (m)</legend>`.
  - Use explicit `for` / `id` on the guide's address input and its checkboxes. Move the rule id out of the label into `<code id="…-rid">` referenced by `aria-describedby`.
  - Stop head: `aria-label="Stop 3 of 7, Read the site, done"` (or a `sr-only` "done"), and `aria-current="step"` on the open stop.
  - (i): insert the note right after the button, give it an id, set `aria-controls` plus `aria-describedby` on the button, and don't close it on scrolls that start inside the rail (or use the native `popover` attribute with `popovertarget`).
  - `#stage-map`: `role="img"` with an `aria-label` that states the district and lot, or `aria-hidden` with the text list beside it as the alternative.

## 7. Persona red flags

**Sam (screen reader, keyboard only)**
- Presses Enter in the address field. The guide re-renders and focus lands on `<body>`; Sam has to Tab from the top of the page (skip link, mode switch, date, Run, Walkthrough…) back into the rail, and does this after every stop.
- "Type an address first." comes as a polite status in the middle of other announcements. The field isn't marked invalid.
- In "Left to a person", each Yes / No / Not sure is three tab stops, and each choice drops focus again.
- The (i) notes are unreachable: "expanded", then silence.
- Setbacks announce as "Front, edit text, not sure". In the Option form a program checkbox reads its rule id aloud.
- At stop 5 the fields are disabled and skipped by Tab, so Sam never hears why. "Run the rules, dimmed" has no description.
- The money answer reads "Capital cost, not given", which Sam will take as their own omission.

**Riley (stress tester)**
- **Refresh mid-flow:** everything in the guide is gone, with no warning, no resume, and the stage blank again.
- **Address outside Vancouver:** "Lookup failed: Nothing in Metro Vancouver matched '…'", with Python quotes, and the earlier good result is erased. A Burnaby address passes as a Metro match with "district not found", and the tool goes on to read it against Vancouver rules with no blocking message.
- **No parcel polygon:** "no parcel found" in the list and a marker on the stage, but "Use this site" is offered with nowhere obvious to enter the lot until the Site card appears below. The run then uses an equivalent rectangle or nothing; the memo should say which.
- **Long note:** the Notes textarea has no limit and no counter, and its contents print in the memo's inputs and the PDF. Untested here, but `resize: vertical` and `min-height: 56px` mean a 2,000-word note grows the rail and pushes Save as… off screen.
- **Other:** "1,200,000" in Land becomes "not sure". "20" in a share Mine row becomes 2000%. Clicking Benchmark after typing Mine figures wipes them. A double Ctrl+Enter writes two timestamp folders and takes two revision numbers.

**Casey (phone, one-handed)**
- The first input is in the bottom third under the tour offer. Every input zooms the page on iOS.
- Suggested / Mine and the guide's Yes / No / Not sure are 22 to 24 px targets, and the (i) is 28 px.
- Scrolling past the stage map with a thumb pans the map instead.
- Errors appear in a strip that has scrolled off the top. Run the rules is in a bar that has scrolled away. The memo, which is what Casey came for, is below 19 suggestion rows and 8 questions.
- `window.prompt()` for "Save site as…" is a poor native dialog on mobile.
- The mode-switch thumb is misplaced over "Manager" on first paint (shot 16).

## 8. Provocative questions

1. If a blank number, a typo in a number and an honest "Not sure" all reach the engine as the same `null`, how is "the UI offers 'not sure' as a normal choice" any different from "the UI hides input errors as uncertainty"? Shouldn't the ledger record which kind of null it got?
2. Why does the manager decide Suggested or Mine 19 times before seeing any answer? Would the flow be more honest if it ran on the suggestion as it stands and asked only for the three or four figures the run says decide the verdict?
3. The memo is the product, so why can it be issued and printed after its inputs have changed on screen? Should a stale memo be allowed to look exactly like a current one?
