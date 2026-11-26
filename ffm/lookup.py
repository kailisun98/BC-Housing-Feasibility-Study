"""Find a site from an address: the point from Nominatim, the zoning district and the parcel polygon from the City
of Vancouver's open data, the lot's area and an equivalent rectangle from the polygon. The network parts are two
small functions; the geometry is pure, so it is tested without the network and runs in the browser build too.

    python -m ffm lookup "998 E 19th Ave, Vancouver, BC"

Sources: Nominatim (OpenStreetMap, ODbL); City of Vancouver Open Data Portal, datasets `zoning-districts-and-labels`
and `property-parcel-polygons` (Open Government Licence, Vancouver). The datasets' ids and fields were checked on
3 Nov 2026. Nothing here is a rule: the result is a proposed site file a person confirms.
"""

from __future__ import annotations

import json
import math
import re
import urllib.parse
import urllib.request
from typing import Any

from .osm import DEFAULT_RADIUS_M, MINOR, USER_AGENT, build as build_context, geocode, norm_name, overpass

COV_RECORDS = "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/{dataset}/records"
ZONING_DATASET = "zoning-districts-and-labels"
PARCEL_DATASET = "property-parcel-polygons"
ADDRESS_DATASET = "property-addresses"      # the City's own address points: civic_number, std_street, site_id, geo_point_2d
# Nominatim, as the fallback for an address the City's list lacks, is kept to Metro Vancouver: without this
# "609 heatley" is a street in South Carolina
NOMINATIM_VIEWBOX = "-123.45,49.00,-122.40,49.45"
STREET_STD = {"AVENUE": "AV", "AVE": "AV", "STREET": "ST", "BOULEVARD": "BLVD", "DRIVE": "DR", "ROAD": "RD", "PLACE": "PL",
              "CRESCENT": "CRES", "HIGHWAY": "HWY", "LANE": "LANE", "COURT": "CRT", "EAST": "E", "WEST": "W", "NORTH": "N", "SOUTH": "S"}
STREET_SUFFIXES = {"AV", "ST", "BLVD", "DR", "RD", "PL", "CRES", "HWY", "LANE", "CRT", "WAY", "MEWS", "DIVERSION", "CONNECTOR"}
# the surroundings from the City too: street centrelines, the 2009 LiDAR building footprints (with heights) and
# the public trees. Three requests of a second or so, against half a minute from the public Overpass server.
CITY_CONTEXT = {"streets": "public-streets", "buildings": "building-footprints-2009", "trees": "public-trees", "lanes": "lanes"}
CITY_ATTRIBUTION = "Contains information licensed under the Open Government Licence – Vancouver (streets, lanes, building footprints 2009, public trees)"
STREETUSE_HIGHWAY = {"arterial": "primary", "secondary arterial": "secondary", "collector": "tertiary", "residential": "residential",
                     "lane": "service", "private": "service", "leased": "service", "recreational": "path", "closed": "service"}
SOURCES = {
    "zoning": {"title": "City of Vancouver Open Data: zoning districts and labels", "url": "https://opendata.vancouver.ca/explore/dataset/zoning-districts-and-labels/"},
    "parcel": {"title": "City of Vancouver Open Data: property parcel polygons", "url": "https://opendata.vancouver.ca/explore/dataset/property-parcel-polygons/"},
    "context": {"title": "City of Vancouver Open Data: public streets, lanes, building footprints 2009, public trees (Open Government Licence – Vancouver)", "url": "https://opendata.vancouver.ca/explore/"},
    "geocode": {"title": "OpenStreetMap Nominatim", "url": "https://nominatim.openstreetmap.org/"},
    "address": {"title": "City of Vancouver Open Data: property addresses", "url": "https://opendata.vancouver.ca/explore/dataset/property-addresses/"},
}


def _get(url: str, params: dict) -> Any:
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def records_at(dataset: str, lat: float, lon: float, within_m: float = 3) -> list[dict]:
    """The dataset's records whose geometry lies within a few metres of the point."""
    res = _get(COV_RECORDS.format(dataset=dataset), {"where": f"within_distance(geom, geom'POINT({lon} {lat})', {within_m}m)", "limit": 3})
    return res.get("results") or []


def records_where(dataset: str, where: str, limit: int = 5) -> list[dict]:
    """The dataset's records matching an ODSQL where clause."""
    res = _get(COV_RECORDS.format(dataset=dataset), {"where": where, "limit": limit})
    return res.get("results") or []


def parse_address(address: str) -> dict[str, Any]:
    """'609 heatley', '998 E 19th Ave, Vancouver, BC' -> the civic number and the street as the City writes it
    ('HEATLEY', 'E 19TH AV'), plus a prefix for a like-match without the suffix. Pure."""
    head = address.split(",", 1)[0].strip()
    m = re.match(r"^\s*(\d+)\s*[-–]?\s*(.*)$", head)
    if not m:
        return {"civic_number": None, "street": "", "like": "", "suffix": None}
    number = int(m.group(1))
    words = [w for w in re.sub(r"[^A-Za-z0-9 ]", " ", m.group(2)).upper().split() if w not in ("VANCOUVER", "BC", "BRITISH", "COLUMBIA", "CANADA")]
    words = [STREET_STD.get(w, w) for w in words]
    suffix = words[-1] if words and words[-1] in STREET_SUFFIXES else None
    core = words[:-1] if suffix else words
    return {"civic_number": number, "street": " ".join(words), "like": " ".join(core), "suffix": suffix}


def city_geocode(address: str) -> dict[str, Any] | None:
    """The City's address point for a civic address, with the parcel it belongs to; None when the City's list has no
    such address (a wrong number, a street outside Vancouver, a new building)."""
    p = parse_address(address)
    if not p["civic_number"] or not p["like"]:
        return None
    like = p["like"].replace('"', "")
    rows = records_where(ADDRESS_DATASET, f'civic_number={p["civic_number"]} AND std_street like "{like}%"', 10)
    if not rows:
        return None
    if p["suffix"]:
        exact = [r for r in rows if str(r.get("std_street") or "").upper() == p["street"]]
        rows = exact or rows
    r = rows[0]
    pt = r.get("geo_point_2d") or {}
    if pt.get("lat") is None:
        return None
    return {"lat": float(pt["lat"]), "lon": float(pt["lon"]), "civic_number": r.get("civic_number"), "std_street": r.get("std_street"),
            "site_id": r.get("site_id"), "local_area": r.get("geo_local_area"),
            "display": f"{civic_address(r.get('civic_number'), r.get('std_street'))}, Vancouver, BC (City of Vancouver property address{', ' + r['geo_local_area'] if r.get('geo_local_area') else ''})"}


NEAREST_CIVIC_SPAN = 150    # how far either side of the number typed the City's list is searched for the nearest one


def nearest_civic(rows: list[dict], number: int) -> dict | None:
    """Of the City's address points on one street, the one whose civic number is nearest the number typed (a tie goes to
    the same side of the street, then the lower number). Pure."""
    # the City's list keeps the civic number as text ("2001"); a number with a letter or a fraction is left out
    have = [(int(str(r["civic_number"]).strip()), r) for r in rows
            if str(r.get("civic_number") or "").strip().isdigit() and (r.get("geo_point_2d") or {}).get("lat") is not None]
    if not have:
        return None
    return min(have, key=lambda x: (abs(x[0] - number), (x[0] - number) % 2, x[0]))[1]


def city_nearest(address: str) -> dict[str, Any] | None:
    """Where the City's list has no such number on the street: its nearest number on that street, with the parcel it
    belongs to (23 Nov 2026: the geocoder's point for the street put "2009 Stainsbury Ave" on 1851 Stainsbury, a different
    district, and "3350 Kingsway" on 488 Kingsway). None where the street itself is not in the list."""
    # civic_number is a text field in the City's dataset, so a range is asked for as the list of numbers in it
    where = nearest_where(address)
    return nearest_from_rows(records_where(ADDRESS_DATASET, where, 100), address) if where else None


def geocode_vancouver(address: str) -> tuple[float, float, str]:
    """Nominatim, kept inside Metro Vancouver and preferring a building over a street; the address is tried as typed
    and then with ', Vancouver, BC' added."""
    import time
    tries = [address] if re.search(r"vancouver", address, re.I) else [address, address.rstrip(" ,") + ", Vancouver, BC"]
    for i, q in enumerate(tries):
        if i:
            time.sleep(1.1)
        res = _get("https://nominatim.openstreetmap.org/search", {"q": q, "format": "jsonv2", "limit": 5, "countrycodes": "ca", "viewbox": NOMINATIM_VIEWBOX, "bounded": 1})
        if res:
            number = (parse_address(address).get("civic_number"))
            best = next((r for r in res if number and str(r.get("display_name", "")).startswith(f"{number},")), None) or res[0]
            return float(best["lat"]), float(best["lon"]), str(best.get("display_name", ""))
    raise ValueError(f"Nothing in Metro Vancouver matched {address!r}; try the civic number, the street and its suffix (998 E 19th Ave).")


def _municipality_of(display: str) -> str | None:
    """The town in a Nominatim display name: the part just before 'Metro Vancouver Regional District', else the part
    before 'British Columbia'. Pure. 'Burnaby City Hall, 4949, Canada Way, Deer Lake, Burnaby, Metro Vancouver
    Regional District, British Columbia, V5G 1M2, Canada' -> 'Burnaby'."""
    parts = [x.strip() for x in str(display or "").split(",")]
    for marker in ("Metro Vancouver Regional District", "British Columbia"):
        if marker in parts:
            i = parts.index(marker)
            for cand in reversed(parts[:i]):
                if cand and not re.fullmatch(r"[A-Z]\d[A-Z] ?\d[A-Z]\d|\d+", cand):
                    return cand
    return None


def pick_parcel(parcels: list[dict], address: str) -> dict:
    """Among parcels near a point, the one whose civic number matches the address, else the first."""
    if not parcels:
        return {}
    number = parse_address(address).get("civic_number")
    if number is not None:
        for p in parcels:
            try:
                if int(str(p.get("civic_number") or "").strip()) == number:
                    return p
            except ValueError:
                continue
    return parcels[0]


def records_within(dataset: str, lat: float, lon: float, radius_m: float, max_pages: int = 4) -> list[dict]:
    """Every record of the dataset within the radius, a hundred at a time (the API's page), up to max_pages."""
    out: list[dict] = []
    for page in range(max_pages):
        res = _get(COV_RECORDS.format(dataset=dataset), {"where": f"within_distance(geom, geom'POINT({lon} {lat})', {radius_m:.0f}m)", "limit": 100, "offset": page * 100})
        rows = res.get("results") or []
        out.extend(rows)
        if len(rows) < 100 or len(out) >= int(res.get("total_count") or 0):
            break
    return out


def city_records(lat: float, lon: float, radius_m: float) -> dict[str, list[dict]]:
    """The three context datasets around a point, fetched side by side."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=len(CITY_CONTEXT)) as pool:
        futs = {k: pool.submit(records_within, ds, lat, lon, radius_m) for k, ds in CITY_CONTEXT.items()}
        return {k: f.result() for k, f in futs.items()}


def street_name_from_hblock(hblock: Any) -> str:
    """'700 HEATLEY AV' as the streets dataset writes a block becomes 'Heatley Ave'."""
    words = str(hblock or "").split()
    while words and words[0].replace("-", "").isdigit():
        words.pop(0)
    civic = civic_address("0", " ".join(words)) if words else ""
    return civic[2:] if civic.startswith("0 ") else civic


def city_elements(streets: list[dict], buildings: list[dict], trees: list[dict], lanes: list[dict] | None = None) -> list[dict]:
    """The City's records in the shape the context builder reads (Overpass elements: ways with a geometry of
    lat/lon points and tags; nodes for trees). Pure. Streets carry a highway class from their use and their name
    from the block; buildings their height above ground; trees their species and a crown from their height; lanes
    (the City's `lanes` dataset, 25 Nov 2026) are service ways tagged as OpenStreetMap tags a lane."""
    out: list[dict] = []
    for i, s in enumerate(lanes or []):
        geom = ((s.get("geom") or {}).get("geometry") or {})
        coords = geom.get("coordinates") or []
        if geom.get("type") == "MultiLineString":
            coords = [p for line in coords for p in line]
        if len(coords) >= 2:
            out.append({"type": "way", "id": 4_000_000 + i, "tags": {"highway": "service", "service": "alley"},
                        "geometry": [{"lat": float(p[1]), "lon": float(p[0])} for p in coords]})
    for i, s in enumerate(streets):
        geom = ((s.get("geom") or {}).get("geometry") or {})
        coords = geom.get("coordinates") or []
        if geom.get("type") == "MultiLineString":
            coords = [p for line in coords for p in line]
        if len(coords) < 2:
            continue
        use = str(s.get("streetuse") or "").strip().lower()
        hw = STREETUSE_HIGHWAY.get(use, "residential")
        name = "" if use == "lane" else street_name_from_hblock(s.get("hblock"))
        tags = {"highway": hw}
        if use == "lane":
            tags["service"] = "alley"     # as OpenStreetMap tags a lane, so lane_behind reads either source
        if name:
            tags["name"] = name
        out.append({"type": "way", "id": 1_000_000 + i, "tags": tags, "geometry": [{"lat": float(p[1]), "lon": float(p[0])} for p in coords]})
    for i, b in enumerate(buildings):
        geom = ((b.get("geom") or {}).get("geometry") or {})
        rings = geom.get("coordinates") or []
        if geom.get("type") == "MultiPolygon":
            rings = [r for poly in rings for r in poly[:1]]
        ring = rings[0] if rings else []
        if len(ring) < 3:
            continue
        h = b.get("hgt_agl") or b.get("avght_m") or b.get("maxht_m")
        tags = {"building": "yes"}
        if h:
            tags["height"] = str(round(float(h), 1))
        out.append({"type": "way", "id": 2_000_000 + i, "tags": tags, "geometry": [{"lat": float(p[1]), "lon": float(p[0])} for p in ring]})
    for i, t in enumerate(trees):
        geom = ((t.get("geom") or {}).get("geometry") or {})
        c = geom.get("coordinates") or []
        if len(c) < 2:
            continue
        tags = {"natural": "tree"}
        name = " ".join(w.capitalize() for w in str(t.get("common_name") or "").split())
        if name and name.lower() != "none":
            tags["species"] = name
        if t.get("height_m"):
            tags["diameter_crown"] = str(round(float(t["height_m"]) * 0.6, 1))   # a crown about six tenths of the height
        out.append({"type": "node", "id": 3_000_000 + i, "lat": float(c[1]), "lon": float(c[0]), "tags": tags})
    return out


# ---------------------------------------------------------------- geometry, pure

def project(lat0: float, lon0: float):
    """Metres east and north of a point, flat enough for one parcel: the metres per degree of latitude and
    longitude at that latitude on the WGS84 ellipsoid (the usual series, good to a few centimetres per hundred
    metres)."""
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    return lambda lon, lat: ((lon - lon0) * m_lon, (lat - lat0) * m_lat)


def ring_area(pts: list[tuple[float, float]]) -> float:
    """Shoelace area of a closed or open ring, in the ring's units squared."""
    if len(pts) < 3:
        return 0.0
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def bounding_rectangle(pts: list[tuple[float, float]]) -> dict[str, Any]:
    """The smallest rectangle around the ring among those aligned with one of its edges: its two sides, its
    bearing (degrees from east, counter-clockwise, of the first side) and its area."""
    best = None
    n = len(pts)
    for i in range(n):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
        if (x1, y1) == (x2, y2):
            continue
        ang = math.atan2(y2 - y1, x2 - x1)
        c, s = math.cos(-ang), math.sin(-ang)
        xs = [x * c - y * s for x, y in pts]
        ys = [x * s + y * c for x, y in pts]
        w, d = max(xs) - min(xs), max(ys) - min(ys)
        if best is None or w * d < best["area_m2"]:
            best = {"side_a_m": w, "side_b_m": d, "bearing_deg": math.degrees(ang) % 180, "area_m2": w * d}
    return best or {"side_a_m": 0, "side_b_m": 0, "bearing_deg": 0, "area_m2": 0}


def parcel_metrics(polygon_lonlat: list[list[float]], street_bearing_deg: float | None = None) -> dict[str, Any]:
    """Area, an equivalent rectangle (same area, the bounding rectangle's proportions) and which of its sides to
    call the frontage: the side parallel to the street where a street bearing is known, else the longer side,
    flagged to confirm. Coordinates are [lon, lat] rings as the City publishes them."""
    ring = [(float(p[0]), float(p[1])) for p in polygon_lonlat]
    if len(ring) > 1 and ring[0] == ring[-1]:
        ring = ring[:-1]
    lat0 = sum(p[1] for p in ring) / len(ring)
    lon0 = sum(p[0] for p in ring) / len(ring)
    P = project(lat0, lon0)
    pts = [P(lon, lat) for lon, lat in ring]
    area = ring_area(pts)
    box = bounding_rectangle(pts)
    scale = math.sqrt(area / box["area_m2"]) if box["area_m2"] else 1.0
    a, b = box["side_a_m"] * scale, box["side_b_m"] * scale
    bearing_a = box["bearing_deg"]
    bearing_b = (bearing_a + 90) % 180
    how = "the longer side, to confirm"
    frontage, depth = (a, b) if a >= b else (b, a)
    front_bearing = bearing_a if a >= b else bearing_b
    if street_bearing_deg is not None:
        def diff(x):
            d = abs((x - street_bearing_deg) % 180)
            return min(d, 180 - d)
        if diff(bearing_a) <= diff(bearing_b):
            frontage, depth, front_bearing = a, b, bearing_a
        else:
            frontage, depth, front_bearing = b, a, bearing_b
        how = "the side parallel to the street"
    rectangular = abs(box["area_m2"] - area) / area < 0.03 if area else False
    return {
        "area_m2": round(area, 1), "frontage_m": round(frontage, 1), "depth_m": round(depth, 1),
        "frontage_from": how, "frontage_bearing_deg": round(front_bearing, 1), "vertices": len(ring),
        "rectangular": rectangular, "bounding_rectangle_area_m2": round(box["area_m2"], 1),
        "center": {"lat": round(lat0, 6), "lon": round(lon0, 6)},
        "local_m": [[round(x, 2), round(y, 2)] for x, y in pts],
    }


# ---------------------------------------------------------------- the lookup

def street_bearing(elements: list[dict], center_latlon: tuple[float, float], street_name: str | None = None) -> dict[str, Any] | None:
    """The street in front of a parcel, from OpenStreetMap ways around its centre: the named road matching the
    parcel's street where there is one, else the nearest road that is not a path. Returns its bearing in the
    parcel_metrics frame (degrees from east, counter-clockwise, mod 180), its name and its distance; None when
    no road comes within 60 m. Since 15 Nov 2026 it also names the cross street of a corner lot (`cross_street`:
    the nearest other named road within 60 m that runs more than 45 degrees off the front street), so the site can
    say the front might be the other side. Checked against a person's frontage marks on 39 parcels
    (`evals/parcels/labels.json`): the named street's side was the front on 35; on the other four, all corner lots,
    the person put the front on the other street (the shorter side on 4890 Hudson St and 6891 Laburnum St, the
    longer on 4411 Brakenridge St and 1598 Matthews Ave; the sides' point counts and curvature say nothing either),
    so the tool keeps the named street and flags the corner rather than choosing. Pure."""
    lat0, lon0 = center_latlon
    P = project(lat0, lon0)
    want = norm_name(street_name or "")
    best = None
    ways: list[tuple[int, float, float, str]] = []     # (rank, distance, bearing, name) per way, at its nearest segment
    for e in elements or []:
        tags = e.get("tags") or {}
        if e.get("type") != "way" or "highway" not in tags or not e.get("geometry"):
            continue
        pts = [P(g["lon"], g["lat"]) for g in e["geometry"]]
        name = tags.get("name", "")
        rank = 0 if want and norm_name(name) == want else (1 if name and tags.get("highway") not in MINOR else 2)
        nearest = None
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            dx, dy = x2 - x1, y2 - y1
            l2 = dx * dx + dy * dy
            if l2 == 0:
                continue
            t = max(0.0, min(1.0, (-x1 * dx - y1 * dy) / l2))
            d = math.hypot(x1 + t * dx, y1 + t * dy)
            key = (rank, d)
            if best is None or key < best[0]:
                best = (key, math.degrees(math.atan2(dy, dx)) % 180, name)
            if nearest is None or d < nearest[0]:
                nearest = (d, math.degrees(math.atan2(dy, dx)) % 180)
        if nearest:
            ways.append((rank, nearest[0], nearest[1], name))
    if best is None or best[0][1] > 60:
        return None
    out = {"bearing_deg": round(best[1], 1), "name": best[2] or None, "matched_by_name": best[0][0] == 0, "distance_m": round(best[0][1], 1)}
    cross = None
    for rank, d, b, name in sorted(ways, key=lambda w: w[1]):
        if rank != 1 or d > 60 or norm_name(name) == norm_name(best[2] or ""):
            continue
        skew = abs(b - best[1]) % 180
        if min(skew, 180 - skew) > 45:
            cross = {"name": name, "distance_m": round(d, 1), "bearing_deg": round(b, 1)}
            break
    if cross:
        out["cross_street"] = cross
    return out


def corner_yard_front(street: dict | None, metrics: dict | None) -> str | None:
    """The street a corner lot's yards are read from, where it is not the address street: the cross street when its
    side of the lot is the shorter one. Kai, 20 Nov 2026, on 609 Heatley Ave (37.2 m along Heatley Ave, 15.2 m along
    Keefer St, RT-3): the building's long side is along Heatley, but the side by the neighbour is a side yard, since
    from Keefer St it is one; so the 20 m rear yard falls at the end away from Keefer and a plate fits, where reading
    the yards from Heatley left the 15.2 m depth under a 20 m rear yard. RT-3's own diagrams draw a corner site so: the
    front on the narrow end, the flanking street along the long side, the lane at the rear. The address frontage stays
    the named street's side (a person's frontage marks on 39 parcels put six corner lots' fronts on the longer, named
    street; moving those to the shorter side scored 30 of 39 against 35), so only the yards move. Pure."""
    if not street or not metrics or not street.get("cross_street"):
        return None
    front, depth = metrics.get("frontage_m"), metrics.get("depth_m")
    if not front or not depth or depth >= front - 0.5:
        return None
    return street["cross_street"]["name"]


# ---------------------------------------------------------------- what the lot's surroundings suggest (25 Nov 2026)

STATIONS_DATASET = "rapid-transit-stations"     # the City's SkyTrain stations: station, geo_point_2d (22 records on 25 Nov 2026)
# the transit-oriented area tiers around a SkyTrain station, as bc.toa.minimum_density's tiers_where says them; a test
# keeps the two the same. Bus exchanges (tiers 4 and 5) are not in the City's station data.
TOA_SKYTRAIN_BANDS = ((200, "1"), (400, "2"), (800, "3"))
TOA_BAND_WORDS = {"1": "within 200 m", "2": "200 to 400 m", "3": "400 to 800 m"}
NEAREST_MAX_NUMBERS = 100   # a "nearest" parcel more than a block of civic numbers from the one typed is refused
NEAREST_MAX_M = 50          # ... or more than this far from the City's nearest number on the street typed
LANE_BEYOND_REAR_M = 12     # a lane's centre line within this of the rear lot line, parallel to the front, is "behind"


def _metres(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    x, y = project(lat1, lon1)(lon2, lat2)
    return math.hypot(x, y)


def _ring_distance(poly_lonlat: list, lat: float, lon: float) -> float:
    """The distance in metres from a point to the nearest point of a lot's outline (0 inside it). Pure."""
    ring = [(float(p[0]), float(p[1])) for p in poly_lonlat]
    if len(ring) < 3:
        return _metres(lat, lon, ring[0][1], ring[0][0]) if ring else float("inf")
    P = project(lat, lon)
    pts = [P(a, b) for a, b in ring]
    inside = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if (y1 > 0) != (y2 > 0) and 0 < (x2 - x1) * (0 - y1) / ((y2 - y1) or 1e-12) + x1:
            inside = not inside
    if inside:
        return 0.0
    best = float("inf")
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        dx, dy = x2 - x1, y2 - y1
        l2 = dx * dx + dy * dy
        t = 0.0 if l2 == 0 else max(0.0, min(1.0, (-x1 * dx - y1 * dy) / l2))
        best = min(best, math.hypot(x1 + t * dx, y1 + t * dy))
    return best


def toa_from_stations(stations: list[dict], poly_lonlat: list | None, center: tuple[float, float]) -> dict[str, Any] | None:
    """The SkyTrain station nearest the lot, the distance to the lot's nearest edge, and the transit-oriented tier that
    distance falls in (TOA_SKYTRAIN_BANDS): a suggestion for a person to confirm on the Province's map, which measures
    from the station as it draws it. None with no stations. Pure."""
    best = None
    for s in stations or []:
        pt = s.get("geo_point_2d") or {}
        if pt.get("lat") is None:
            continue
        lat, lon = float(pt["lat"]), float(pt["lon"])
        d = _ring_distance(poly_lonlat, lat, lon) if poly_lonlat and len(poly_lonlat) >= 3 else _metres(center[0], center[1], lat, lon)
        if best is None or d < best[0]:
            best = (d, str(s.get("station") or "a station").strip())
    if best is None:
        return None
    d, name = best
    tier = next((t for limit, t in TOA_SKYTRAIN_BANDS if d <= limit), None)
    return {"station": name, "distance_m": round(d), "tier": tier}


def _nearest_vec(way: dict, P) -> tuple[float, float, float, float] | None:
    """A way's nearest point to the origin: (distance, x, y, bearing of that segment mod 180)."""
    pts = [P(g["lon"], g["lat"]) for g in way.get("geometry") or []]
    best = None
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        dx, dy = x2 - x1, y2 - y1
        l2 = dx * dx + dy * dy
        if l2 == 0:
            continue
        t = max(0.0, min(1.0, (-x1 * dx - y1 * dy) / l2))
        x, y = x1 + t * dx, y1 + t * dy
        d = math.hypot(x, y)
        if best is None or d < best[0]:
            best = (d, x, y, math.degrees(math.atan2(dy, dx)) % 180)
    return best


def lane_behind(elements: list[dict], center: tuple[float, float], front_name: str | None, depth_m: float | None) -> dict[str, Any] | None:
    """A lane behind the lot, from the streets around it: a lane (the City's streetuse "lane", OpenStreetMap's
    service=alley) roughly parallel to the front street, on the side away from it, its centre line within
    LANE_BEYOND_REAR_M of the rear lot line. Returns {distance_m from the lot's centre, to_centre_line_m from the rear
    line, bearing_deg}; None where there is none. Pure."""
    if not elements or not depth_m:
        return None
    P = project(center[0], center[1])
    want = norm_name(front_name or "")
    front = None
    for e in elements:
        tags = e.get("tags") or {}
        if e.get("type") == "way" and "highway" in tags and want and norm_name(tags.get("name", "")) == want:
            v = _nearest_vec(e, P)
            if v and (front is None or v[0] < front[0]):
                front = v
    if front is None:
        return None
    best = None
    for e in elements:
        tags = e.get("tags") or {}
        if e.get("type") != "way" or tags.get("service") != "alley":
            continue
        v = _nearest_vec(e, P)
        if not v:
            continue
        d, x, y, b = v
        skew = abs(b - front[3]) % 180
        if min(skew, 180 - skew) > 25 or x * front[1] + y * front[2] >= 0:     # not parallel, or on the street's side
            continue
        to_line = d - depth_m / 2
        if -3 <= to_line <= LANE_BEYOND_REAR_M and (best is None or d < best["distance_m"]):
            best = {"distance_m": round(d, 1), "to_centre_line_m": round(max(0.0, to_line), 1), "bearing_deg": round(b, 1)}
    return best


def refuse_nearest(typed: int | None, found: int | None, typed_street: str, found_street: str, gap_m: float | None) -> str | None:
    """Why a "nearest" parcel is not taken as the site, or None where it may be (23 Nov 2026, the second panel: 3680 E
    Hastings St came back as 1195 E Hastings St, about 4 km away; 5050 Joyce St as 3250 Kingsway). Pure."""
    if not typed or not found or typed == found:
        return None
    if typed_street and found_street and typed_street.upper() not in found_street.upper():
        return f"the parcel found is on {found_street.title()}, not on the street typed"
    if abs(typed - found) > NEAREST_MAX_NUMBERS:
        return f"the parcel found is number {found}, {abs(typed - found):,} civic numbers from {typed}: more than a block away"
    if gap_m is not None and gap_m > NEAREST_MAX_M:
        return f"the parcel found is {gap_m:,.0f} m from the City's nearest number on the street typed"
    return None


def nearest_from_rows(rows: list[dict], address: str, same_side: bool = False) -> dict[str, Any] | None:
    """city_nearest's answer from the address points it fetched (or the page fetched): the nearest number to the one
    typed on the same street; with `same_side`, the nearest odd number to an odd one, even to even. Pure."""
    p = parse_address(address)
    if not p["civic_number"] or not rows:
        return None
    if p["suffix"]:
        rows = [r for r in rows if str(r.get("std_street") or "").upper() == p["street"]] or rows
    if same_side:
        par = int(p["civic_number"]) % 2
        rows = [r for r in rows if str(r.get("civic_number") or "").strip().isdigit() and int(str(r["civic_number"]).strip()) % 2 == par]
    r = nearest_civic(rows, int(p["civic_number"]))
    if not r:
        return None
    pt = r["geo_point_2d"]
    return {"lat": float(pt["lat"]), "lon": float(pt["lon"]), "civic_number": r.get("civic_number"), "std_street": r.get("std_street"), "site_id": r.get("site_id")}


def nearest_where(address: str) -> str | None:
    """The where clause the City's address list is asked with for the numbers near the one typed (the page asks it too)."""
    p = parse_address(address)
    if not p["civic_number"] or not p["like"]:
        return None
    n = int(p["civic_number"])
    near = ", ".join(f'"{k}"' for k in range(max(1, n - NEAREST_CIVIC_SPAN), n + NEAREST_CIVIC_SPAN + 1))
    return f'std_street like "{p["like"].replace(chr(34), "")}%" AND civic_number in ({near})'


def lookup(address: str, context: bool = True, radius_m: float = DEFAULT_RADIUS_M) -> dict[str, Any]:
    """A proposed site file for the address, with every field's source, for a person to confirm. With `context`
    the streets, buildings and trees around the parcel come too, from the City's open data (a second or two),
    or from OpenStreetMap's Overpass API where the City has nothing (outside Vancouver; half a minute), so the
    figures draw the real surroundings and the frontage is the side on the street."""
    from concurrent.futures import ThreadPoolExecutor
    # the point: the City's own address list first (exact, and it names the parcel), Nominatim within Metro
    # Vancouver otherwise
    found = city_geocode(address)
    if found:
        lat, lon, display = found["lat"], found["lon"], found["display"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            fz = pool.submit(records_at, ZONING_DATASET, lat, lon)
            fp = pool.submit(records_where, PARCEL_DATASET, f'site_id="{found["site_id"]}"', 3) if found.get("site_id") else pool.submit(records_at, PARCEL_DATASET, lat, lon, 15)
            zoning, parcels = fz.result(), fp.result()
        if not parcels:
            parcels = records_at(PARCEL_DATASET, lat, lon, 15)
    else:
        lat, lon, display = geocode_vancouver(address)
        with ThreadPoolExecutor(max_workers=2) as pool:
            fz, fp = pool.submit(records_at, ZONING_DATASET, lat, lon), pool.submit(records_at, PARCEL_DATASET, lat, lon, 15)
            zoning, parcels = fz.result(), fp.result()
    # the district at the parcel's centre, not at the point the address landed on (25 Nov 2026: 1065 Harwood St read
    # CD-1 (852) from a point on the next lot, where its own parcel is RM-5A), the SkyTrain stations for the transit
    # tier, and, for a number the City's list lacks, its numbers near it on the street
    extra: dict[str, Any] = {}
    pc = _parcel_center(parcels, address)
    try:
        if pc:
            extra["zoning_centre"] = records_at(ZONING_DATASET, pc[0], pc[1])
        extra["stations"] = _get(COV_RECORDS.format(dataset=STATIONS_DATASET), {"limit": 100}).get("results") or []
        if not found and nearest_where(address):
            extra["nearest_rows"] = records_where(ADDRESS_DATASET, nearest_where(address), 100)
    except (OSError, ValueError):
        pass
    elements, q, source, note = None, "", "osm", ""
    if context:
        c = pc or (lat, lon)
        try:
            recs = city_records(c[0], c[1], radius_m)
            if recs["streets"]:
                elements, source = city_elements(recs["streets"], recs["buildings"], recs["trees"], recs.get("lanes")), "city"
                q = f"City of Vancouver Open Data within {radius_m:.0f} m: " + ", ".join(f"{len(recs[k])} {k}" for k in recs)
        except (OSError, ValueError) as e:
            note = f"The City's context datasets could not be fetched ({e})."
        if elements is None:
            try:
                elements, q = overpass(c[0], c[1], radius_m)
            except (OSError, ValueError) as e:
                note += f" The OpenStreetMap context could not be fetched either ({e}); run python -m ffm context later."
    res = assemble(address, lat, lon, display, zoning, parcels, elements, radius_m, q, source, extra=extra)
    if note.strip():
        res["site"]["notes"] += " " + note.strip()
    return res


def _parcel_center(parcels: list[dict], address: str = "") -> tuple[float, float] | None:
    p = pick_parcel(parcels, address)
    poly = (((p.get("geom") or {}).get("geometry") or {}).get("coordinates") or [[]])[0]
    if len(poly) < 3:
        return None
    m = parcel_metrics(poly)
    return (m["center"]["lat"], m["center"]["lon"])


def assemble(address: str, lat: float, lon: float, display: str, zoning: list[dict], parcels: list[dict],
             elements: list[dict] | None = None, radius_m: float = DEFAULT_RADIUS_M, query: str = "", source: str = "osm",
             extra: dict | None = None) -> dict[str, Any]:
    """The proposed site from the fetched records. Pure, so the browser build can fetch and hand the records in.
    With context `elements` around the parcel (the City's, converted by city_elements, or Overpass's), the frontage
    is the side parallel to the parcel's street and the site gets its `osm` context block, credited to `source`;
    without them the longer side is called the frontage, to confirm.

    `extra` (25 Nov 2026), each optional: `zoning_centre`, the zoning records at the parcel's centre (taken over the
    point's); `stations`, the City's SkyTrain stations (a transit tier is suggested from the nearest); `nearest_rows`,
    the City's address points near a number its list lacks (the nearest is named, and a far "nearest" parcel refused).
    What the records suggest goes in `site.suggested` {key: {value, why, source}}, offered to a person, never applied."""
    extra = extra or {}
    z_point = zoning[0] if zoning else {}
    z = (extra.get("zoning_centre") or [None])[0] or z_point
    zoning_at = "the parcel's centre" if extra.get("zoning_centre") else "the point the address was found at"
    p = pick_parcel(parcels, address)
    poly = (((p.get("geom") or {}).get("geometry") or {}).get("coordinates") or [[]])[0]
    civic = civic_address(p.get("civic_number"), p.get("streetname"))
    street_name = civic.split(" ", 1)[1] if civic and " " in civic else None
    metrics = parcel_metrics(poly) if len(poly) >= 3 else None
    center = (metrics["center"]["lat"], metrics["center"]["lon"]) if metrics else (lat, lon)
    street = street_bearing(elements, center, street_name) if (elements and metrics) else None
    if street:
        metrics = parcel_metrics(poly, street["bearing_deg"])
    district = z.get("zoning_district") or None
    cd1 = z.get("cd_1_number") or None
    if cd1 is not None:
        # the dataset may hand the number as 324, 324.0 or "324": an int where it is a whole number, else as written
        try:
            f = float(str(cd1).strip())
            cd1 = int(f) if f.is_integer() else str(cd1).strip()
        except ValueError:
            cd1 = str(cd1).strip() or None
    notes = [f"Found by First Read on the address {address!r}: " + (f"the City's property address {display!r}." if "property address" in display else f"geocoded by Nominatim as {display!r}.")]
    if district:
        notes.append(f"Zoning district {district}" + (f" (CD-1 by-law {cd1})" if cd1 else "") + f" from the City's zoning districts dataset at {zoning_at}."
                     + (f" A CD-1 district has no general schedule: its limits are in CD-1 by-law No. {cd1}." if cd1 else ""))
        other = z_point.get("zoning_district")
        if other and other != district:
            notes.append(f"The address's point fell in {other}" + (f" (CD-1 by-law {z_point.get('cd_1_number')})" if z_point.get("cd_1_number") else "")
                         + f"; the parcel itself is in {district}, which is the district used. A lot on a district line: confirm with the City's zoning map.")
    else:
        notes.append("No zoning district found at that point in the City's dataset; enter it by hand.")
    shape = None
    if metrics:
        # the distance is the lot's centre to the road's centre line, said so (17 Nov 2026: "from OpenStreetMap, 29.0 m
        # away" read as the side being 29 m off); the corners are counted once, by the shape classifier below, which
        # drops the in-line points the raw polygon carries (the raw count disagreed with "4 corners" in the next note)
        front_how = (f"the side along {street['name']}" + ("" if street["matched_by_name"] else ", the nearest road")
                     + f" (OpenStreetMap; its centre line {street['distance_m']} m from the lot's centre)") if street else metrics["frontage_from"]
        notes.append(f"Lot area {metrics['area_m2']:,.1f} m² from the parcel polygon" + (", a rectangle" if metrics["rectangular"] else ", not a rectangle: the frontage and depth are an equivalent rectangle with the same area") + f"; frontage taken as {front_how}.")
        yard_front = corner_yard_front(street, metrics)
        if yard_front:
            x = street["cross_street"]
            notes.append(f"A corner lot: the address faces {street['name']} along the lot's {metrics['frontage_m']} m side, and {x['name']} runs along "
                         f"its {metrics['depth_m']} m end. The yards are read from {x['name']}, the shorter street side, as a corner site's are: "
                         f"the lot is {metrics['frontage_m']} m deep from it, {street['name']} is the flanking street, and the side by the "
                         f"neighbour is a side yard, not a rear yard. Confirm with the City which street is the front: it sets the yards, the envelope and the massing.")
        elif street and street.get("cross_street"):
            x = street["cross_street"]
            notes.append(f"A corner lot: {x['name']} also runs beside it, {x['distance_m']} m from the centre. The frontage is taken on {street['name']} "
                         f"({metrics['frontage_m']} m); the front could instead be the {metrics['depth_m']} m side on {x['name']}. "
                         f"Confirm which side is the front: it sets the yards, the envelope and the massing.")
        try:
            from .parcel_shapes import classify   # imported here: parcel_shapes builds on this module
            c = classify([poly])
            shape = {"class": c["class"], "note": c["note"], "rectangularity": round(c["rectangularity"], 3), "vertices": c["vertices"],
                     "confidence": round(c["confidence"], 2), "alternative": c["alternative"]}
            if c["class"] != "rectangle":
                notes.append(c["note"] + (" The massing uses the polygon itself: the setback envelope follows the lot lines and the plate is the largest rectangle inside it." if c["class"] != "near_rectangle" else ""))
        except (ValueError, ImportError):
            shape = None
    else:
        notes.append("No parcel polygon found at that point; enter the area, frontage and depth by hand.")
    notes.append("Transit-oriented area, the Community Vision map, water and sewer, trees and the owner are not in these datasets: answer them, or leave them 'not sure'.")
    # the municipality is read from the point, never assumed (15 Nov 2026: a Burnaby address came back as the City of
    # Vancouver and the flow carried on with Vancouver's rules). The City's address list means Vancouver; a Nominatim
    # point is placed by the town in its display name.
    from_city_list = "property address" in display
    town = _municipality_of(display) if display and not from_city_list else None
    municipality = "City of Vancouver" if (from_city_list or not town or "vancouver" == town.lower()) else town
    typed_civic = parse_address(address).get("civic_number")
    found_civic = None
    try:
        found_civic = int(str(p.get("civic_number") or "").strip()) if p.get("civic_number") else None
    except ValueError:
        found_civic = None
    mismatch = bool(typed_civic and found_civic and typed_civic != found_civic)
    # A number the City's list does not have: the geocoder's parcel is one candidate (it found the church at 320 East
    # Hastings under its Gore Avenue address) and the nearest number on the same street is another (2001 for "2009
    # Stainsbury Ave"). The site keeps the first and names the second (23 Nov 2026); a first that is on another street,
    # more than a block of numbers away or far from the second is refused (25 Nov 2026).
    near = nearest_from_rows(extra.get("nearest_rows") or [], address) if mismatch else None
    near_words = civic_address(near.get("civic_number"), near.get("std_street")) if near else None
    if near_words and near_words.lower() == civic.lower():
        near_words = None
    # the distance is to the nearest number on the same side of the street (1065 Harwood St: 1055 next door, not 1066
    # across the street)
    side = nearest_from_rows(extra.get("nearest_rows") or [], address, same_side=True) if mismatch else None
    gap = None
    if side and metrics:
        gap = _metres(metrics["center"]["lat"], metrics["center"]["lon"], side["lat"], side["lon"])
    refused = refuse_nearest(typed_civic, found_civic, parse_address(address).get("like") or "", str(p.get("streetname") or ""), gap) if mismatch else None
    if refused:
        notes.insert(0, f"You typed {typed_civic}; the City's address list has no such number on this street, and the parcel the address was placed on, {civic}, is not taken: "
                        f"{refused}." + (f" The City's nearest number on that street is {near_words}: look that up if it is the lot." if near_words else " Try the address as the City lists the lot."))
    elif mismatch:
        notes.insert(0, f"You typed {typed_civic}; the City's address list has no such number on this street, and the nearest parcel is {civic}. Use it only if that is the site."
                        + (f" The City's nearest number on the street you typed is {near_words}: look that up if it is the lot." if near_words else ""))
    if municipality != "City of Vancouver":
        notes.insert(0, f"{municipality} is outside the City of Vancouver: the rule stack reads Vancouver's by-laws and policies, so the zoning answers will say not assessed.")
    site = {
        "id": _slug(civic or address),
        "address": f"{civic}, Vancouver, BC" if civic else (display.split(", Metro Vancouver")[0] if display else address),
        "municipality": municipality,
        "zoning_district": district,
        "site_area_m2": metrics["area_m2"] if metrics else None,
        "frontage_m": metrics["frontage_m"] if metrics else None,
        "depth_m": metrics["depth_m"] if metrics else None,
        "in_former_community_vision_area": None, "in_transit_oriented_area": None, "toa_tier": None,
        "frequent_bus_stop_within_400m": None, "has_water_and_sewer": True,
        "owner_type": None, "owner": None, "land_tenure_plan": None,
        "existing_trees_on_site": [], "street_trees": {"count": None, "street": (street or {}).get("name") or street_name},
        "context": {"street": {"name": (street or {}).get("name") or street_name}} if (street or street_name) else None,
        "notes": " ".join(notes),
        "parcel": {"polygon_lonlat": poly, "civic_number": p.get("civic_number"), "streetname": p.get("streetname"),
                   "site_id": p.get("site_id"), "metrics": metrics, "shape": shape, "street": street, "source": SOURCES["parcel"]} if poly else None,
        "lookup": {"center": {"lat": lat, "lon": lon}, "geocoded_as": display, "typed": address, "civic_typed": typed_civic, "civic_found": found_civic,
                   "civic_mismatch": mismatch, "outside_vancouver": municipality != "City of Vancouver", "zoning_at": zoning_at,
                   "zoning_record": {k: v for k, v in z.items() if k not in ("geom", "geo_point_2d")}},
        "sources": [SOURCES["address"] if "property address" in display else SOURCES["geocode"], SOURCES["zoning"], SOURCES["parcel"]],
    }
    if cd1:
        site["cd1_bylaw_number"] = cd1
    if near_words:
        site["lookup"]["nearest_on_street"] = f"{near_words}, Vancouver, BC"
    if refused:
        site["lookup"]["refused"] = refused
    if z_point.get("zoning_district") and z_point.get("zoning_district") != district:
        site["lookup"]["district_at_point"] = z_point.get("zoning_district")
    # what the surroundings suggest, offered to a person and never applied (25 Nov 2026): the transit tier from the
    # nearest SkyTrain station, a lane behind the lot from the streets
    suggested: dict[str, dict] = {}
    if "stations" in extra and municipality == "City of Vancouver":
        t = toa_from_stations(extra.get("stations") or [], poly if len(poly) >= 3 else None, center)
        src = "City of Vancouver Open Data: rapid transit stations"
        if t and t["tier"]:
            band = TOA_BAND_WORDS[t["tier"]]
            suggested["in_transit_oriented_area"] = {"value": True, "source": src,
                                                     "why": f"{t['station']} station is about {t['distance_m']} m from the lot's nearest edge"}
            suggested["toa_tier"] = {"value": int(t["tier"]), "source": src,
                                     "why": f"about {t['distance_m']} m from {t['station']} station, tier {t['tier']} ({band} of a SkyTrain station); the Province's map measures from the station as it draws it, so confirm"}
        # past 800 m nothing is suggested: a bus exchange's tiers 4 and 5 are not in the station data (3475 E Hastings St
        # is in tier 4 beside the Kootenay Loop, 2.3 km from Rupert station), so "no" would be a guess; the distance is kept
        if t:
            site["lookup"]["nearest_station"] = {"station": t["station"], "distance_m": t["distance_m"], "source": src}
    if elements and metrics and street:
        yf = corner_yard_front(street, metrics)
        lane = lane_behind(elements, center, yf or street.get("name"), metrics["frontage_m"] if yf else metrics["depth_m"])
        if lane:
            suggested["context.lane_behind"] = {"value": True, "source": "the streets around the lot" + (" (City of Vancouver Open Data: public streets)" if source == "city" else " (OpenStreetMap)"),
                                                "why": f"a lane runs behind the lot, its centre line about {lane['to_centre_line_m']} m past the rear lot line",
                                                "also": {"context.lane_to_centre_line_m": lane["to_centre_line_m"]}}
    if suggested:
        site["suggested"] = suggested
    # the area plan the rules hold, where the district itself says the lot is inside it: the Downtown-Eastside/Oppenheimer
    # District lies within the Downtown Eastside Plan's area (23 Nov 2026: a DEOD lot was read against the city-wide
    # family rule because nothing set the plan). Other districts inside the plan's area are left to the person.
    if str(district or "").upper().startswith("DEOD"):
        site["area_plan"] = "downtown_eastside"
        site["notes"] += " The district is DEOD, inside the Downtown Eastside Plan's area, so the Plan's family-unit target is read (area plan: confirm)."
    if metrics and corner_yard_front(street, metrics):
        # the engine turns the lot to front_face; the page's "Which street is the front?" reads front_street
        site["front_face"] = {"street": street["cross_street"]["name"]}
        site["front_street"] = street["cross_street"]["name"]
    if site["context"] is None:
        del site["context"]
    cross_front = site.get("front_face")
    # the surroundings, as python -m ffm context stores them, so the plan draws the real streets and buildings
    if elements and metrics:
        try:
            block = build_context(site, elements, center, radius_m, query, display)
            if source == "city":
                block["source"] = "City of Vancouver Open Data: public streets, lanes, building footprints 2009, public trees"
                block["attribution"] = CITY_ATTRIBUTION
                block["licence_url"] = "https://opendata.vancouver.ca/pages/licence/"
                site["sources"].append(SOURCES["context"])
            else:
                site["sources"].append({"title": "OpenStreetMap contributors, ODbL (the roads, buildings and trees drawn around the lot)", "url": "https://www.openstreetmap.org/copyright"})
            site["osm"] = block
        except ValueError as e:
            site["notes"] += f" The context was not placed: {e}"
    # a front the massing cannot find is not written (23 Nov 2026: 877 E Hastings St was given Campbell Ave as its front,
    # a street the context did not show adjoining the lot, and every run then drew nothing)
    if cross_front:
        from .boundary import oriented_ring
        try:
            oriented_ring(site)
        except ValueError:
            site.pop("front_face", None)
            site.pop("front_street", None)
            site["notes"] += (f" A corner lot: {cross_front['street']} may be the front the yards are read from, but the streets on file do not show it adjoining the lot, "
                              "so the front is left on the address street. Say which street is the front.")
    fields = {
        "zoning_district": {"value": district, "source": "zoning", "note": "the district polygon at the geocoded point"},
        "site_area_m2": {"value": site["site_area_m2"], "source": "parcel", "note": "from the parcel polygon"},
        "frontage_m": {"value": site["frontage_m"], "source": "parcel", "note": (f"the side along {street['name']}" if street and street.get("name") else metrics["frontage_from"]) if metrics else ""},
        "depth_m": {"value": site["depth_m"], "source": "parcel", "note": "the equivalent rectangle's other side" if metrics else ""},
        "has_water_and_sewer": {"value": True, "source": None, "note": "assumed for a City of Vancouver lot"},
    }
    return {"site": site, "fields": fields, "refused": refused,
            "found": {"geocoded": bool(display), "zoning": bool(district), "parcel": bool(poly), "context": bool(site.get("osm"))}}


def civic_address(number: Any, street: Any) -> str:
    """'998' and 'E 19TH AV' as the City writes them become '998 E 19th Ave'."""
    if not number or not street:
        return ""
    words = []
    for w in str(street).split():
        lw = w.lower()
        if lw in ("av", "ave"):
            words.append("Ave")
        elif lw in ("st", "rd", "dr", "blvd", "pl", "cres", "hwy") and not any(ch.isdigit() for ch in w):
            words.append({"st": "St", "rd": "Rd", "dr": "Dr", "blvd": "Blvd", "pl": "Pl", "cres": "Cres", "hwy": "Hwy"}[lw])
        elif len(w) == 1 and w.isalpha():
            words.append(w.upper())
        elif w[0].isdigit():
            words.append(lw)   # 19th, 2nd
        else:
            words.append(w.capitalize())
    return f"{number} {' '.join(words)}"


def _slug(s: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "-" for ch in s)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")[:60] or "site"
