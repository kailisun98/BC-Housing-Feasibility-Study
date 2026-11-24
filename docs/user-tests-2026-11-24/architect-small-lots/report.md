# First Read, reviewed from a small-lot practice (AI role-play, 24 Nov 2026)

*A simulated review by an AI playing the principal of a 4-person Vancouver practice doing multiplexes, townhouses and
3 to 6 storey wood frame on R1-1, RT and RM lots for non-profits and co-ops. Not a practitioner's view; never to be
quoted as one. Rules as of 2026-11-24. The reviewer's run files were kept in a scratch folder outside the repository.*

## 1. Sites run

Lookup, then suggest (outright, benchmark, funder-ready), then run; also the local server's `/api/lookup`,
`/api/read-site`, `/api/suggest` (with `fixed.units`) and `/api/layout` (with hand-placed zones). Runs took about 0.4 s.

| Site | Suggestion (the three candidates were the same building) | Run |
|---|---|---|
| 1726 E 3rd Ave, RT-5, 7.6 × 30.5 m, 231.8 m² | 3 storeys, 139 m² (FSR 0.60), 1 three-bed home, plate 3.86 × 12.0 m | Outright yes; layout places 0 of 1; gap $520,463 (57%) |
| 4172 Prince Edward St, R1-1, 11.7 × 36.2 m, 422.8 m² | 3 storeys, 423 m² (FSR 1.00), 5 homes, plate 8.5 × 16.6 m | Outright yes; places 2 of 5; outright gap $763,275 (28%); funder-ready gap $2,152,602 (78%) |
| 1550 E 12th Ave, RM-11, 7.6 × 37.2 m, 283.6 m² | 4 storeys, 213 m² (FSR 0.75), 2 homes, plate 2.5 × 21.3 m | Outright yes; places 0 of 2 |

The civic-number guard works: "4170 Prince Edward St" warned, landed 2.7 km south, named 4172 as the nearest number and
refused `--out`; "1820 E 6th Ave" did the same and named 1819.

## 2. The workflow against the tool

| Step | Tool | Notes |
|---|---|---|
| 1. Address → district, lot size, lane, corner | Partly | District and parcel exact. A lane is never detected (only streets in the context), though it is the default East Van case. 1726 E 3rd was called "a corner lot: Commercial Drive also runs beside it, 53.2 m from the centre" with `cross_street` null; the lot is about 50 m from Commercial. |
| 2. Read the schedule | Partly | FSR, height and three yards tested and cited. Coverage, building depth, units a hectare, R1-1's courtyard rear yard and RT-5's narrow-lot side yard are notes, "not tested". |
| 3. Envelope on the lot, before any option | Missing in read-site | `/api/read-site` says "the option states no setbacks yet" and gives no envelope. |
| 4. Outright vs rezoning | Partly | "Yes" is printed for buildings that hold no homes. |
| 5. Yield: SSMUH homes vs the schedule | Partly | `bc.ssmuh.minimum_units` says at least 3 homes on 1726; the suggestion makes 1; nothing reconciles them. |
| 6. Units against BC Housing sizes | Covered, useful | "3 homes need about 365 m²; the outright FSR allows 139 m²" is the sentence to give a client. |
| 7. Assembly (two to five lots) | Missing | RM-11's "1.70 with at least 36.6 m of frontage" is never translated into "about five 7.6 m lots". |
| 8. Variations | Partly | Fast, but duplex + infill, front/back multiplex and a townhouse row cannot be expressed. |
| 9. Drawings a client sees | Misleading | See 3a. |
| 10. Money | Inconsistent | See 3d. |

## 3. What is not working

### Real defects

**a. Every small building is laid out as an apartment block.** At 4172 Prince Edward (a 5-home R1-1 multiplex) floor 0
holds a 7.0 × 9.2 m core, a 1.8 m corridor, an amenity room, a lobby and services; two one-beds are placed. At 1726 the
3.86 m plate is `arrangement: "double"`. At 1550 the plan says "too shallow for a double-loaded corridor" of a plate
2.5 m wide. Six ground-oriented homes placed by hand through `/api/layout` (two a floor, no corridor) were called broken:
`no_corridor` and `no_core` on every floor, a 40 m² amenity shortfall, services "taken below grade with the parking".
The suggester says to "lay out a larger home across two floors" in Edit blocks, but a block lives on one floor. A client
shown FIG 03 for 4172 would think the lot holds 2 homes.

**b. RT-5's side yard is wrong on a narrow lot.** `cov.rt5.setbacks` tests 1.5 m; its own note says 10% of the width up
to 15.0 m (s.3.1.2.5), 0.76 m on 1726. The envelope is 4.6 m wide where it should be about 6.1 m.

**c. "Outright: yes" with nothing buildable.** 1550 E 12th: yes, 4 storeys on a 2.5 m plate, 0 homes, `warnings: []`.
The memo says "a 2.5 × 27.0 m setback envelope" but the envelope polygon is 3.4 m wide; 2.5 m is the plate box after the
0.5 m grid, which cost 26% of the width here.

**d. The money reads rosier the less is answered.** On the same 5-home building, the outright option (no rent tiers)
counts a Community Housing Fund grant of $890,295 and a 28% gap; the funder-ready option (tiers 2/2/1) fails the mix,
counts $0 and shows 78%. The suggester already said 5 homes cannot split 30/50/20.

**e. Two contradictions in the money section.** The next step names "CMHC's Affordable Housing Fund", closed 19 Dec 2025
by its own rule; the grant line says "$178,059 … at the 2025-26 provisional rate" where $178,059 is 2026-27's.

**f. A program assumed where it makes no sense.** The 1-home RT-5 option carries an amenity room and services ("did
not fit: amenity"). `cov.social_housing_definition` passes ("owned by a non profit society, secured for 60 years") on
a lot whose owner is null, resting on the suggester's own placeholders without saying so.

### Flow problems

**g. No envelope before the option.** The first deliverable is what the lot takes; the tool only gets there after an
option is derived.

**h. Clauses that decide small lots are untested:** R1-1's courtyard rear yard, rear building and building limits; RT-5's
45% coverage, 45% depth and 74 homes a hectare (1.7 homes on 232 m², exactly where the SSMUH minimum of 3 overrides it;
one line in the memo should say so).

**i. Lane and corner left to guesswork.** The lane reduction took 1726's rear yard from 10.7 to 7.65 m once set by hand;
the false corner note would send the architect to the City with the wrong question.

**j. memo.md is 73 KB for a one-home lot.** A 4-unit co-op needs two pages.

## 4. What should change, ranked

1. **A ground-oriented typology in the solver and the block editor** (L): homes with their own entries over 2 to 3
   floors, one shared stair or none, no lift, amenity and services off below a home count, front and rear buildings
   with a courtyard.
2. **Fix the narrow-lot side yard** across the RT and RM schedules that have it; test coverage and building depth (S).
3. **"No buildable plate" instead of "yes"** under a minimum width or with 0 homes placed; report the envelope's own
   width, not the grid box (S).
4. **No grant counted that the suggester knows the option cannot get**; drop the closed CMHC fund from next steps (S).
5. **Envelope and yield on read-site**: envelope, coverage, schedule homes vs SSMUH homes, BC Housing-size homes (M).
6. **Assembly** with frontage thresholds shown as "N lots to unlock X" (M).
7. **Lanes from the City's lane data**; no corner claim when `cross_street` is null (S).
8. **A short memo** for small sites: answers, envelope, open items, the ledger as an appendix (S).

## 5. What would make the reviewer stop

- "Yes" over a 2.5 m, zero-home building, with the architect's name beside it.
- A lift core and a corridor drawn in a sixplex.
- Money that improves when information is withheld.

Worth keeping: the cited clause on every yard and FSR line, the civic-number guard, the "N homes need X m²; the FSR
allows Y" sentence, and runs fast enough to try ten variants a minute. The building model is the weak link under about
12 homes.
