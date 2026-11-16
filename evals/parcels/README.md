# Parcel shape survey, City of Vancouver

A survey of every parcel polygon the City of Vancouver publishes, classified by shape with `ffm/parcel_shapes.py`,
so the tool can say when a lot is not the rectangle its equivalent-rectangle massing assumes. Run on 11 Nov 2026
(Pacific time; the export finished at 2026-11-12T05:04:48Z).

## Files

- `shape-survey.json`: the record count (99,680), counts by class and by local area, the distributions of
  rectangularity, convexity, vertex count and area, the three project sites, and up to 25 examples for each class
  other than `rectangle` (site_id, the civic address where the record has one, else its `geo_point_2d`, the metrics
  and the ring in [lon, lat]). The examples are a sample: firm calls first, in a fixed order by a hash of the site_id.
  Nothing else is sampled; every count covers all 99,680 records.
- `uncertain.json`: 40 parcels the classifier is least sure of, each with its ring, metrics, best guess, runner-up,
  the reason, and a 120 x 120 SVG thumbnail (north up). `label` and `labels_by` are null for a person to fill.

## Counts (all 99,680 records, none failed)

With the thresholds of 15 Nov 2026 (checked against a person's labels, below); the 11 Nov counts in brackets.

| class | parcels | share | example |
|---|---:|---:|---|
| rectangle | 89,441 | 89.7% | 998 E 19th Ave (75.6 x 37.2 m) |
| near_rectangle | 5,135 (4,589) | 5.2% | 3301 E Pender St (92% of its bounding rectangle, 7 corners) |
| trapezoid | 2,476 (2,018) | 2.5% | 4950 Slocan St (a 28 m2 sliver, 53% of its bounding rectangle) |
| irregular | 2,387 (3,370) | 2.4% | 1588 SE Marine Drive (6 corners, 67% of its bounding rectangle); 1010 Expo Blvd |
| l_shape | 198 (219) | 0.2% | 3478 Anzio Drive (six corners, 91% of its hull) |
| flag_lot | 41 | 0.04% | 1610 Mclean Drive (a 1.9 m strip to a 20 m body) |
| multi_part | 2 | 0.002% | 1002 Station St (two pieces) |

Counts by local area are in `shape-survey.json`. The parcel records carry no local area, so each parcel's
`geo_point_2d` was placed in the City's `local-area-boundary` polygons; 69 points fall outside all 22 areas.

## What each class means

The metrics are computed in metres on a local projection (`lookup.project`). Corners are counted after dropping
edges under 0.5 m and points where the outline turns under 3 degrees. The bounding rectangle is the minimum-area one
(on the convex hull). Checked in this order:

- `multi_part`: more than one outer ring. Example: 1002 Station St.
- `rectangle`: four corners and area at least 95% of the bounding rectangle. Example: 998 E 19th Ave; 609 Heatley Ave.
- `trapezoid` with a cut corner (added 15 Nov 2026): five corners, convex (at least 97% of its hull), under 90% of
  the bounding rectangle: a four-sided lot whose street corner is rounded or bevelled, as on the crescents of
  Shaughnessy and Arbutus Ridge. Example: 4411 Brakenridge St.
- `near_rectangle`: at least 88% of the bounding rectangle (90% until 15 Nov 2026), whatever the corner count (a
  bevelled corner, a slight skew, a short jog). Example: 3301 E Pender St.
- `flag_lot`: lines swept across the parcel along both axes of its bounding rectangle find, at one end, a run at
  least 6 m long of single cross-sections under 6 m wide and of near-constant width (within 1.5 m), which widens
  within 3 m to a body over 12 m wide. Example: 2355 E 30th Ave.
- `trapezoid`: four corners, under 88% of the bounding rectangle (skewed four-sided lots, many at diagonal streets).
  Example: 2150 W 35th Ave.
- `l_shape`: six corners, exactly one inward, area between 60% and 95% of the convex hull. Example: 3478 Anzio Drive.
- `irregular`: anything else: triangles, curved frontages on crescents, many-sided lots. Example: 1010 Expo Blvd.

The thresholds are the module's own choices for a first read, not a City definition. The equivalent rectangle the
tool lays a building on is the bounding rectangle's two sides; for anything but `rectangle` it overstates the plate.

## Things a reader should know

- 89.7% of parcels are clean rectangles; the median rectangularity is 0.998 and 93% of parcels have four corners after simplifying.
- Curved lot lines (Shaughnessy, Dunbar, Arbutus Ridge crescents) are published as many short segments (up to
  2,336 points on one ring). Whether a gentle curve counts as one corner or several depends on the simplification,
  and that is where most of the uncertainty is.
- Some `flag_lot` strips are 1 to 2 m wide (1610 and 1616 Mclean Drive, 1405 Haro St, 735 E 22nd Ave): walkways or
  easement strips rather than driveways. The class says only that a narrow strip leads to a wider body.
- Only two records are MultiPolygons. 862 records have no `site_id`, 1,171 have no civic number and street, and 36
  site_ids appear on more than one record (the survey keys on the record, not the site_id).
- 1010 Expo Blvd's parcel (site_id 032354185) is 2,712 m2 here; `sites/1010-expo-blvd.json` carries 3,908 m2,
  derived from the development application's floor area and FSR. Which one is the development site is uncertain.

## The uncertain set and how to label it

Each parcel is classified once with the stated thresholds and then eleven more times with the thresholds nudged
(rectangularity lines +/- 0.015, convexity range wider and narrower, flag widths +/- 1 m and body +/- 2 m) and the
simplification tolerances halved and doubled. `confidence` is the share of those runs that agree. 3,857 parcels have
a confidence under 1. `uncertain.json` keeps the 40 lowest, at most six per pair of classes (and first three per pair,
so every boundary shows up): l_shape/irregular, irregular/trapezoid, rectangle/near_rectangle, near_rectangle/
trapezoid, l_shape/trapezoid, l_shape/near_rectangle, near_rectangle/irregular, flag_lot/l_shape, flag_lot/irregular.

Only lots a person could build on (12 Nov 2026). The first set of 40 held eighteen parcels that were not lots: three parks
(2303 Wall St, the park site on Trinity Street; 8288 Ash St, Ash Park; 498 Cardero St, Cardero Park), rights-of-way
(1725 E Broadway and 2600 Rupert St on the Clark Drive to Nanaimo corridor, 3598 E Kent Ave North on the CPR Marpole
line), three strata plans of standing buildings (1478 W Hastings St, 1350 W 8th Ave, 3437 Kingsway) and seven
untaxed remnants with no site_id (five in Southlands under RA-1, a Crown sliver in Sunset under M-2, a scrap of CD-1
by Wall St), and the two polygons of Rupert SkyTrain station's land at 2902 Hebb Ave. The survey now checks each candidate on the City's portal before it takes it: a nine-digit `site_id`
(strata plans are LMS, VAS, EPS or BCS numbers), a civic address, a `property-tax-report` record of legal type LAND
with a land value, a legal description that is not a park, a right-of-way, a road, a lane, a railway or an air-space
parcel, a point outside `parks-polygon-representation`, and no `rapid-transit-lines` or `rapid-transit-stations`
geometry intersecting the ring (Rupert Station's land at 2902 Hebb Ave is taxed as ordinary land and passed every
other test; Kai's note on the label page caught it). `uncertain.json` lists what it rejected while choosing
(`rejected_while_choosing`, 27 parcels: the eighteen above, three more strata plans, a second CPR piece, two air-space
parcels on Drake St, a Canada Line piece with no address, and the rest) and what the 11 Nov set lost
(`dropped_from_the_11_nov_set`); every kept parcel carries a
`lot` block with the zoning district at its point and the tax roll's legal type, year built and legal description,
which the label page prints under the address. Industrial lots (I-2, M-2) stay: a lot is a lot, and a reader can see
the zoning.

To label: open `label.html` in a browser (built from `uncertain.json` by `make_label_page.py`). Each parcel shows
its published outline, then the outline drawn over the real site (OpenStreetMap tiles, or Esri World Imagery with
the Aerial switch, each with its attribution; the maps load as you scroll), the classifier's guess and runner-up
and why it hesitated. Tick a class (or "other" with a note), put your initials in the header, and Download
labels.json; put the file beside `uncertain.json`. The draft stays in that browser until then. Or edit
`uncertain.json` by hand: set `label` to one of `rectangle`, `near_rectangle`, `trapezoid`, `l_shape`, `flag_lot`,
`irregular`, `multi_part` (or `"other: ..."`), and `labels_by` to your initials and the date. Leave a parcel null
if you cannot tell.

## Checked against a person's labels (15 Nov 2026)

`labels.json` is Kai's pass over the 40 (initials KS; read out of the label page's storage in the Claude app's
browser pane, the same object the Download button writes, checked by length and hash): 33 given a class, 4 "other"
with a note that the parcel itself looks wrong (2055 Glen Drive, 2938 W 39th Ave, 7500 Angus Drive, 3626 Main St),
3 left blank (1598 Matthews Ave, 61 E 27th Ave, 1112 W Pender St), and a frontage edge on 39 of them, a cross street
on 13. Three more carry a "double check this parcel" note with a class (1599 Glen Drive, 4465 W 3rd Ave, 3790
Cypress St); all seven are real taxable lots on the City's roll, and what is odd about each is noted at the end of this
section.

**Shapes** (`python evals/parcels/score_labels.py`; it classifies each labelled ring again with the current thresholds,
from the ring as `uncertain.json` stores it, rounded to 1e-7 degrees, which moves a knife-edge case or two: 1367
Devonshire Crescent is a rectangle at 0.9500 unrounded and nearly one at 0.9499 rounded). Of the 33 with a class, the
11 Nov call was right 8 times and its runner-up 22 times. Two changes to `ffm/parcel_shapes.py` follow from the labels
and take the score to 21 of 33:

- A five-cornered convex lot under the 0.90 line is a trapezoid with a cut corner, not irregular: six of six curved
  corner lots (4411 Brakenridge St, 1568 W 32nd Ave, 4788 Hudson St, 4326 Angus Drive, 3578 Quesnel Drive, 6488
  Nanaimo St) were called trapezoid.
- The near-rectangle line moves from 0.90 to 0.88: every four-cornered lot at 0.899 to 0.900 (3444 E 51st Ave, 2388
  Harrison Drive, 4366 and 4376 Quesnel Drive, 2141 Scarboro Ave, 2311 Burquitlam Drive) and five of nine
  six-cornered lots at 0.886 to 0.900 (2624 W 3rd Ave, 1423 Grant St, 450 SE Marine Drive, 4129 Quesnel Drive, 6891
  Laburnum St) were called near rectangle.

What the labels do not settle: the **L shape**. Of ten L guesses one was called an L (1928 Venables St); the rest were
"nearly a rectangle" or "irregular" at the same rectangularity and convexity (a notch of about 5% of the hull on 1644
Nelson St and 303 Vernon Drive reads as irregular, on 1423 Grant St as nearly a rectangle), so no metric in the module
separates them and the rule stays. The **rectangle line** stays at 0.95: of three four-cornered lots at 0.950 to 0.955,
one was called a rectangle (1367 Devonshire Crescent) and two nearly one (4890 Hudson St, 3864 W Broadway), all with a
rounded corner published as many points. City-wide the changes move 983 parcels out of irregular, 546 into near
rectangle and 458 into trapezoid; the table above has the new counts. `uncertain.json` is frozen as the labelled set
(its `best_guess` fields are the 11 Nov calls); `survey.py` run today would choose a different 40 near the new lines.

**Frontage** (`python evals/parcels/score_frontage.py [--cache <file>]`; one `public-streets` request per parcel): the
tool's rule, the parcel side along the street the parcel is named for, applied to the page's edges (the edge whose
midpoint is nearest the centreline of that street, lanes left out), guesses 34 of the 39 marked frontage edges. The
five misses: where the named street touches two edges because the corner is a curve (4411 Brakenridge St, 1598
Matthews Ave) Kai marks the straight edge and the rule takes the curve; on a corner lot whose long side is the address
street (4890 Hudson St) Kai marks the short side; 6891 Laburnum St's two Laburnum-side edges are swapped between
frontage and cross street; 4465 W 3rd Ave's polygon runs to within 3 m of the W 3rd centreline, so its nearest edge is
not its front (the parcel is one of the odd ones). The cross street, guessed as the edge nearest the nearest
other-named street within 12 m, is right 7 times of 13: Kai marks every other street-facing edge, lanes included, as
a cross street, so the second mark is not one edge.

**The parcels Kai flagged**: 2055 Glen Drive and 1599 Glen Drive are I-2 lots beside the Millennium Line guideway
(the line is off the ring; the transit check passed); 4465 W 3rd Ave (LOT H, plan LMP7635, 1996) is a six-cornered lot
whose outline reaches the street centreline on one side; 2938 W 39th Ave (LOT G, "except plan 19777") is a 452 m2 lot
with a 1991 house; 7500 Angus Drive (LOT 5 block 285, "PT OF", nothing built on the roll) is on the aerial a strip a
few metres wide running diagonally across the Marpole grid for several blocks, the old CPR Arbutus line (now the
Arbutus Greenway) by its line, which the lot checks miss because its legal description has none of the words and the
City taxes it as land: a strip test (narrowest cross-section under 3 m along most of its length) would catch it and is
not written yet; 1112 W Pender St ("that part of Lot 1", 1960) is on the aerial a wedge between a tower and the
street, a remnant, not a site on its own; 3790 Cypress St (LOT 2 block 42, 1912) is a ten-cornered First Shaughnessy
estate lot. The last two and the strip are lots on the roll but not development sites; whether any odd lot is one
stays a question for a person, and the memo's parcel warning says so.

## How it was run

The download and the survey scripts were kept outside the repository (the 53.6 MB export is not committed):

```powershell
# 1. the City's export endpoint, plain User-Agent "First-Read-survey/0.1"; 540 s for 53.6 MB
uv run python -I fetch.py <download-dir>
#    GET https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/property-parcel-polygons/exports/geojson
#    GET https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/local-area-boundary/exports/geojson
# 2. classify every feature with ffm.parcel_shapes.classify and write the two JSON files; about 40 s, plus the
#    lot checks for the uncertain candidates (five records requests each: property-tax-report by land_coordinate,
#    zoning-districts-and-labels and parks-polygon-representation at the point, rapid-transit-lines and -stations
#    intersecting the ring; cached in <download-dir>\developable-cache.json)
uv run python -I survey.py <repo> <download-dir>\parcels.geojson <download-dir>\local-areas.geojson <download-dir>\fetch-log.json evals\parcels
```

The classifier's tests: `python -m unittest tests.test_parcel_shapes`. The scores against the labels:
`python evals/parcels/score_labels.py` (no network) and `python evals/parcels/score_frontage.py --cache <file>`.

## Licence and attribution

Contains information licensed under the Open Government Licence – Vancouver
(https://opendata.vancouver.ca/pages/licence/). Datasets: `property-parcel-polygons` and `local-area-boundary`,
City of Vancouver Open Data Portal (https://opendata.vancouver.ca/explore/dataset/property-parcel-polygons/),
fetched 11 Nov 2026; `property-tax-report`, `zoning-districts-and-labels`, `parks-polygon-representation`,
`rapid-transit-lines` and `rapid-transit-stations` for the lot checks, 12 Nov 2026. The classes and thresholds are this project's, not the City's.
