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
CITY_CONTEXT = {"streets": "public-streets", "buildings": "building-footprints-2009", "trees": "public-trees"}
CITY_ATTRIBUTION = "Contains information licensed under the Open Government Licence – Vancouver (streets, building footprints 2009, public trees)"
STREETUSE_HIGHWAY = {"arterial": "primary", "secondary arterial": "secondary", "collector": "tertiary", "residential": "residential",
                     "lane": "service", "private": "service", "leased": "service", "recreational": "path", "closed": "service"}
SOURCES = {
    "zoning": {"title": "City of Vancouver Open Data: zoning districts and labels", "url": "https://opendata.vancouver.ca/explore/dataset/zoning-districts-and-labels/"},
    "parcel": {"title": "City of Vancouver Open Data: property parcel polygons", "url": "https://opendata.vancouver.ca/explore/dataset/property-parcel-polygons/"},
    "context": {"title": "City of Vancouver Open Data: public streets, building footprints 2009, public trees (Open Government Licence – Vancouver)", "url": "https://opendata.vancouver.ca/explore/"},
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
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = {k: pool.submit(records_within, ds, lat, lon, radius_m) for k, ds in CITY_CONTEXT.items()}
        return {k: f.result() for k, f in futs.items()}


def street_name_from_hblock(hblock: Any) -> str:
    """'700 HEATLEY AV' as the streets dataset writes a block becomes 'Heatley Ave'."""
    words = str(hblock or "").split()
    while words and words[0].replace("-", "").isdigit():
        words.pop(0)
    civic = civic_address("0", " ".join(words)) if words else ""
    return civic[2:] if civic.startswith("0 ") else civic


def city_elements(streets: list[dict], buildings: list[dict], trees: list[dict]) -> list[dict]:
    """The City's records in the shape the context builder reads (Overpass elements: ways with a geometry of
    lat/lon points and tags; nodes for trees). Pure. Streets carry a highway class from their use and their name
    from the block; buildings their height above ground; trees their species and a crown from their height."""
    out: list[dict] = []
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
    no road comes within 60 m. Pure."""
    lat0, lon0 = center_latlon
    P = project(lat0, lon0)
    want = norm_name(street_name or "")
    best = None
    for e in elements or []:
        tags = e.get("tags") or {}
        if e.get("type") != "way" or "highway" not in tags or not e.get("geometry"):
            continue
        pts = [P(g["lon"], g["lat"]) for g in e["geometry"]]
        name = tags.get("name", "")
        rank = 0 if want and norm_name(name) == want else (1 if name and tags.get("highway") not in MINOR else 2)
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
    if best is None or best[0][1] > 60:
        return None
    return {"bearing_deg": round(best[1], 1), "name": best[2] or None, "matched_by_name": best[0][0] == 0, "distance_m": round(best[0][1], 1)}


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
    elements, q, source, note = None, "", "osm", ""
    if context:
        c = _parcel_center(parcels, address) or (lat, lon)
        try:
            recs = city_records(c[0], c[1], radius_m)
            if recs["streets"]:
                elements, source = city_elements(recs["streets"], recs["buildings"], recs["trees"]), "city"
                q = f"City of Vancouver Open Data within {radius_m:.0f} m: " + ", ".join(f"{len(recs[k])} {k}" for k in recs)
        except (OSError, ValueError) as e:
            note = f"The City's context datasets could not be fetched ({e})."
        if elements is None:
            try:
                elements, q = overpass(c[0], c[1], radius_m)
            except (OSError, ValueError) as e:
                note += f" The OpenStreetMap context could not be fetched either ({e}); run python -m ffm context later."
    res = assemble(address, lat, lon, display, zoning, parcels, elements, radius_m, q, source)
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
             elements: list[dict] | None = None, radius_m: float = DEFAULT_RADIUS_M, query: str = "", source: str = "osm") -> dict[str, Any]:
    """The proposed site from the fetched records. Pure, so the browser build can fetch and hand the records in.
    With context `elements` around the parcel (the City's, converted by city_elements, or Overpass's), the frontage
    is the side parallel to the parcel's street and the site gets its `osm` context block, credited to `source`;
    without them the longer side is called the frontage, to confirm."""
    z = zoning[0] if zoning else {}
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
    notes = [f"Found by First Read on the address {address!r}: " + (f"the City's property address {display!r}." if "property address" in display else f"geocoded by Nominatim as {display!r}.")]
    if district:
        notes.append(f"Zoning district {district}" + (f" (CD-1 by-law {cd1})" if cd1 else "") + " from the City's zoning districts dataset at that point.")
    else:
        notes.append("No zoning district found at that point in the City's dataset; enter it by hand.")
    if metrics:
        front_how = (f"the side along {street['name']}" + ("" if street["matched_by_name"] else ", the nearest road") + f" from OpenStreetMap, {street['distance_m']} m away") if street else metrics["frontage_from"]
        notes.append(f"Lot area {metrics['area_m2']:,.1f} m² from the parcel polygon ({metrics['vertices']} vertices" + (", a rectangle" if metrics["rectangular"] else ", not a rectangle: the frontage and depth are an equivalent rectangle with the same area") + f"); frontage taken as {front_how}.")
    else:
        notes.append("No parcel polygon found at that point; enter the area, frontage and depth by hand.")
    notes.append("Transit-oriented area, the Community Vision map, water and sewer, trees and the owner are not in these datasets: answer them, or leave them 'not sure'.")
    site = {
        "id": _slug(civic or address),
        "address": f"{civic}, Vancouver, BC" if civic else (display.split(", Metro Vancouver")[0] if display else address),
        "municipality": "City of Vancouver",
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
                   "site_id": p.get("site_id"), "metrics": metrics, "street": street, "source": SOURCES["parcel"]} if poly else None,
        "lookup": {"center": {"lat": lat, "lon": lon}, "geocoded_as": display, "zoning_record": {k: v for k, v in z.items() if k not in ("geom", "geo_point_2d")}},
        "sources": [SOURCES["address"] if "property address" in display else SOURCES["geocode"], SOURCES["zoning"], SOURCES["parcel"]],
    }
    if site["context"] is None:
        del site["context"]
    # the surroundings, as python -m ffm context stores them, so the plan draws the real streets and buildings
    if elements and metrics:
        try:
            block = build_context(site, elements, center, radius_m, query, display)
            if source == "city":
                block["source"] = "City of Vancouver Open Data: public streets, building footprints 2009, public trees"
                block["attribution"] = CITY_ATTRIBUTION
                block["licence_url"] = "https://opendata.vancouver.ca/pages/licence/"
                site["sources"].append(SOURCES["context"])
            else:
                site["sources"].append({"title": "OpenStreetMap contributors, ODbL (the roads, buildings and trees drawn around the lot)", "url": "https://www.openstreetmap.org/copyright"})
            site["osm"] = block
        except ValueError as e:
            site["notes"] += f" The context was not placed: {e}"
    fields = {
        "zoning_district": {"value": district, "source": "zoning", "note": "the district polygon at the geocoded point"},
        "site_area_m2": {"value": site["site_area_m2"], "source": "parcel", "note": "from the parcel polygon"},
        "frontage_m": {"value": site["frontage_m"], "source": "parcel", "note": (f"the side along {street['name']}" if street and street.get("name") else metrics["frontage_from"]) if metrics else ""},
        "depth_m": {"value": site["depth_m"], "source": "parcel", "note": "the equivalent rectangle's other side" if metrics else ""},
        "has_water_and_sewer": {"value": True, "source": None, "note": "assumed for a City of Vancouver lot"},
    }
    return {"site": site, "fields": fields, "found": {"geocoded": bool(display), "zoning": bool(district), "parcel": bool(poly), "context": bool(site.get("osm"))}}


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
