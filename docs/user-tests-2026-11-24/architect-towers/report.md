# First Read, reviewed from a tower practice (AI role-play, 24 Nov 2026)

*A simulated review by an AI playing an associate at a large Vancouver practice working on 12 to 30 storey non-profit
and mixed-tenure towers. Not a practitioner's statement; never to be quoted as one. Run from the command line and the
local JSON API; the reviewer's files were kept in a scratch folder outside the repository.*

## 1. Sites and what the tool said

**Lookups.** Seven addresses tried; four refused `--out` (correct), but the "nearest parcel" offered was sometimes far
off: `3680 E Hastings St` → "1195 E Hastings St (M-1, 1357.8 m²)", about 4 km away; `5050 Joyce St` → "3250 Kingsway
(R1-1, 24320.8 m²)"; `1065 Harwood St` → "1055 Harwood St (CD-1 (852), 1605.3 m²)", while looking up 1055 Harwood
directly gave **RM-5A** for the same 1605.3 m² parcel. The zoning comes from the geocoded point, not the parcel.

Three sites kept:
- **5058 Joyce St**: CD-1 (662), 1,287.7 m², 40.2 × 32.0 m, beside Joyce–Collingwood station; re-run with
  `in_transit_oriented_area: true, toa_tier: 1` set by hand.
- **1055 Harwood St**: RM-5A, West End, 1,605.3 m², 40.2 × 39.9 m.
- **375 Glen Drive**: the committed CD-1 (819) case, read for reference.

**Suggestions.**
- Joyce without a tier: all three candidates the same 6 storeys, 4,321 m², 43 homes.
- Joyce at tier 1, funder-ready: **20 storeys, 66.0 m, 14,404 m², FSR 11.19, 145 homes**.
- Harwood: the same building three times, 5 storeys at FSR 1.00, **8 homes in 1,605 m²**; funders "no" (8 homes cannot
  split 30/50/20).

**Own options** (the API's `fixed` figures, then `ffm run`):
- Joyce, 12 storeys, FSR 5.0, 300 m² retail, 4.5 m ground floor: 61 homes derived, 57 placed; "not assessed / by
  rezoning not yet confirmed / not yet confirmed / needs more sources".
- Harwood at the Director's 2.20 FSR, 12 storeys, 3,532 m²: "Outright, under RM-5A: yes, with conditions"; 19 homes;
  funders "no".

## 2. The workflow against the tool

| Step | Tool | Notes |
|---|---|---|
| Pin the site and district | Partly | Good when the civic number is listed; otherwise a wrong "nearest" parcel and a district read from a point. |
| TOA tier from the station distance | Missing | Left "unsure" 150 m from a SkyTrain station; the tier rule is unverified. |
| Read the CD-1 by-law; choose the rezoning policy | Partly | CD-1 honestly "not assessed"; the reader needs a key and a saved PDF; no policy choice beyond Interim and TOA. |
| Test tower forms (podium + tower, plate vs height) | Missing / wrong | One extruded box; plate depth fixed at 21 m. |
| Core: stairs, lifts, scissor | Partly | Scissor stair exists; lifts never counted; cores oversized. |
| Area schedule and efficiency | Missing | No net-to-gross anywhere (open since the last panel). |
| Hand-off to the code consultant | Partly | `bcbc.exits` honestly "entered from recollection". |
| Hand-off to the cost consultant | Partly | The cost line says it was "NOT written for this building: 20 storeys", yet a gap and a verdict are printed on a quadplex rate. |
| Hand-off to the City's rezoning planner | Missing | No enquiry sheet; no tower separation, floor-plate limits, shadow or view cones. |
| Hand-off to Revit | Partly | Masses and blocks arrive as Mass DirectShapes, with defects below. |

## 3. What is not working

### Real defects

1. **TOA funder-ready ignores the tier's FSR.** Joyce at tier 1: "20 storeys, FSR 11.19 — plate 720 m² × 20 = 14,404 m²"
   where the tier allows 5.0, 2.2 times the protected density. `suggest.envelope_for` reads `tiers_storeys` only; the
   `tiers_fsr` cap sits in a branch a CD-1 site never reaches. The ledger says only "info … the option proposes 20", and
   the memo prices $94.1M and 145 homes.
2. **The mass's height differs from the height tested, without a warning.** Harwood's option says 37.0 m, answer 1 tests
   37.0 m, `massing.json` builds 39.6 m (12 × 3.3), and the taller mass goes to Revit. A warning prints only when the
   stated height is the larger.
3. **Revit floor plates ignore the taller ground floor.** `stage_masses` places plates at `k × floor_to_floor_m`;
   `massing.json` carries no ground-floor height while `layout.json` levels sit at 0, 4.5, 7.5…, so every plate is 1.5 m
   off its level with a 4.5 m retail floor. The model is in the lot frame: no shared coordinates, base point or true
   north. (Read from the code, not run in Revit.)
4. **Plates that hold few homes read "placed: all".** Harwood at 12 storeys: a 14.02 × 21.0 m plate in a 35 × 33.5 m
   envelope, a core of 11.21 × 11.4 m (43% of the plate), 19 homes in 3,532 m² (about 34% residential efficiency), "19
   of 19 units placed", egress "pass". The same floor area gives 34 homes at 6 storeys, 33 at 7, 24 at 9, 19 at 12; at
   17 storeys the suggestion says 45, the solver places 16 on a 9.89 m-wide plate. The suggestion assumes 0.78 net
   efficiency; the solver never reports what it achieved.
5. **Four stairs on a 537 m² plate.** Joyce level 2: two 2.2 × 11.4 m end stairs plus a 7.0 × 11.4 m central core read as
   two more: "4 exits, 2 required · travel 4.3 m"; about 24% of the plate is core, and no lift count.
6. **Zero yards break the envelope.** Joyce with 0 m front and side yards (a street-wall podium): "The setbacks leave no
   envelope inside the lot polygon that a rectangular plate fits; the equivalent rectangle is used", on an exact
   rectangle.
7. **Conditional approval labelled "Outright".** "Outright, under RM-5A: yes, with conditions … the Director of Planning
   may increase it". A planner reads "outright" as no discretion. RM-5's 50% coverage and 120° envelope are untested, yet
   "By rezoning: not needed" sounds settled.
8. **Lookup trust.** The "nearest" can be kilometres away; without `--out` the wrong lot's JSON prints to stdout and the
   warning only to stderr.
9. **Glen Drive's answers contradict each other**: "Outright, under CD-1 (819): yes" beside "By rezoning (M-1 to CD-1
   (819)…): not yet confirmed" for a site the CD-1 already rezoned. Massing warnings repeat two or three times.

### Flow problems

- **Suggestions are wood frame and stop at six storeys** (`wood_max`); over RM-5D's 58 m or a CD-1's 91 m the tool
  offers 6 storeys.
- **The three candidates are one building** on both sites; the Director's discretionary 2.20 FSR on RM-5A is never
  derived.
- **The CLI's `suggest` has no `--storeys/--gfa`**; without the API's `fixed`, `ffm run` gives "0 of 0 units".
- **No TOA tier from the station distance**, though the station dataset is already used in `evals/parcels`.
- **No podium + tower.** Step-backs exist only in the block editor; the suggestion, section, elevations and solver treat
  one box.

## 4. What should change, ranked

1. **Cap the TOA envelope at the tier FSR; warn whenever the mass height differs from the tested height** (S).
2. **An efficiency line and an area schedule**: homes by type and floor, net / gross / core / circulation, net-to-gross,
   as CSV and on the page; flag below about 70% (M).
3. **A construction-type switch** (wood to 6, encapsulated mass timber to 18, concrete) setting the storey cap,
   floor-to-floor, cost basis and core; tower-plate logic (550–750 m², one core with a scissor stair, lifts by home
   count as a declared placeholder) (L).
4. **Podium + tower** in the option and the suggester with per-level heights, carried through `massing.json` to Revit,
   levels and plates from one list (M).
5. **TOA tier from the station distance**, marked unconfirmed until the City's map is checked; verify
   `bc.toa.minimum_density` against B.C. Reg. 265/2023 (S/M).
6. **Approval-route wording**: Outright, Conditional (Director / DP Board), Rezoning as three verdicts (S).
7. **Revit**: a base point from the parcel's lon/lat, true north, unit type and area parameters on blocks or Areas/Rooms
   (M).
8. **Lookup**: refuse a "nearest" more than about 50 m away; take the district from the parcel polygon; warnings to
   stdout too (S).
9. **A planner's sheet**: tower separation, floor-plate limits, site coverage, and the tests not run (M).

## 5. What would make the reviewer stop

- A suggested FSR 11.19 on a TOA site with a $94M pro-forma and no flag.
- Revit plates and levels that disagree; a mass taller than the height checked.
- "19 of 19 placed" and "egress: pass" on a building that is 43% core: green marks on bad geometry are worse than none.

Done well: CD-1 "not assessed" with the missing by-law named; the scissor stair cited by clause; the cost line saying
in the table it was not written for this building; the `--accept-nearest` refusal; open items naming who to ask. It is
honest about what it does not know, and less careful about the numbers it makes up itself.
