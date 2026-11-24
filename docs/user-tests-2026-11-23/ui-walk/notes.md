# The manager's route in the browser, 23 Nov 2026

Simulated user test (walked by an AI reviewer), not a practitioner's statement. The three persona
reviewers worked from the command line; this is the one pass through the page itself, as a
development manager would meet it: `python -m ffm ui`, `app.html?mode=manager`, typing
"320 E Hastings St" (the First United redevelopment site). The run it made is in
`run-320-e-hastings/` beside this file. Nothing was saved into `sites/`, `options/` or `outputs/`.

## What happened, stop by stop

| Stop | What I did | What the page did |
|---|---|---|
| 01 | Typed `320 E Hastings St`, Enter | Found the right parcel (the church lot at Gore and Hastings, 1,362.3 m², 36.1 × 37.7 m) but named it **438 Gore Ave**, with an amber check: "You typed 320; the City's list has no such number on this street. This is the nearest parcel: use it only if it is the site." District DEOD, "no DEOD schedule in the rules: a rough envelope stands in". |
| 01 | Answered the eight questions (Community Vision: no; TOA: not sure; owner: a church; buildings stay: no; land held: owned by the society; front: E Hastings St; lane: yes) | Each answer took at once; the status line confirmed it. |
| 02 | Continue | Derived "funder-ready": 47 homes, 6 storeys, 19.8 m, FSR 3.39, all marked *rough*. |
| 02 | Storeys 6 → 11 | Homes fell from 47 to **31**; the floor area stayed 4,617 m²; "Continue waits for one figure: the height or the storeys". |
| 02 | Height 40 m, homes 103 | "Your 103 homes in 4,617 m² of floor area: about 45 m² a home, corridors and cores included." |
| 02 | FSR 7 | Refused: "9,536 m² on 11 floors is 867 m² a floor, more than the 770 m² the setbacks leave (28.5 × 27 m): plan 13 storeys or more, or less floor area." FSR 6 was accepted. |
| 03 | Run the rules | R1 in 449 ms, no console errors. Outright: not assessed. Funders: not yet confirmed. Eight open items. Money: needs more sources, a $23.2M gap, 43% of $53.4M. 86 of 103 homes fit the plate. |

## Findings

**P1. On a Downtown Eastside site the first answer is empty.** "Outright: not assessed" and
"No rezoning path stated" is all answer 1 says for DEOD. The stack has a Downtown Eastside
family rule (`cov.dtes.family_units`), but the page never asks whether the site is in an area
plan, so the city-wide 35% family rule was applied instead and passed. A manager on this site
learns nothing about what the area's own plan asks of the social housing share, and the open
item tells them to "save the DEOD schedule into inbox/", which is an instruction for whoever
maintains the tool, not for them.

**P1. The placeholder yards decide how big the building may be.** DEOD buildings sit on their
lot lines. The 3.7 / 6.0 / 3.0 m placeholder yards left a 28.5 × 27 m plate box, and that box
is what refused FSR 7 on 11 storeys and what left 17 homes unplaced. The manager's route has no
way to say "no yards here"; the refusal reads like a rule and is a default.

**P1. No way to say that four floors are not homes.** The scheme this site actually carries has
several floors of community services under the housing. The manager's route asks for homes,
storeys, height and FSR only. The memo then reads "Non-residential space is 0.0% of area, under
the 30% cap", the pro-forma spreads the whole floor area over the homes, and the plans give the
ground floor to housing.

**P2. Adding storeys took homes away.** 6 → 11 storeys with the floor area held turned 47 homes
into 31, with no sentence saying why (a slimmer plate places fewer). A manager reads that as a
fault.

**P2. The suggested program is a family building wherever it lands.** 20 studios, 40 one-bed,
33 two-bed, 10 three-bed and the 30/50/20 rent split arrive by default. The mix is behind
"the mix"; nothing at stop 02 asks who the homes are for.

**P2. The address the memo carries is not the address typed.** Everything after stop 01,
including the PDF title, says 438 Gore Ave. The check at stop 01 is honest, but a board would
not recognise its own site. Let the manager keep the name they typed.

**P3. "or read it with Claude at stop 3"** appears in the option card and in two open items.
There are three stops now and stop 3 is Run; Claude is in the architect's schedule.

**P3. "The site allows"** heads a list that is four *uncertain* and two *info*. It is what the
site's rules ask, not what the site allows.

**P3. The transit-area and tree items are handed to the architect**, though stop 01 says the
manager answers the transit question from the City's map.

**P3. At an 800 px pane the top bar wraps to two rows** (the mode switch above the date and the
revision). It reads, but the memo starts lower.

## What worked

The parcel check before "Use this site"; "not sure" as a normal answer with the person named;
figures that refuse the impossible in words with numbers in them; the homes-per-floor-area
sentence; the money drawn as a stack with the gap hatched; the note that the Community Housing
Fund has no open intake; 449 ms from Run to memo.
