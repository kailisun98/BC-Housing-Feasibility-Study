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
import urllib.parse
import urllib.request
from typing import Any

from .osm import USER_AGENT, geocode

COV_RECORDS = "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/{dataset}/records"
ZONING_DATASET = "zoning-districts-and-labels"
PARCEL_DATASET = "property-parcel-polygons"
SOURCES = {
    "zoning": {"title": "City of Vancouver Open Data: zoning districts and labels", "url": "https://opendata.vancouver.ca/explore/dataset/zoning-districts-and-labels/"},
    "parcel": {"title": "City of Vancouver Open Data: property parcel polygons", "url": "https://opendata.vancouver.ca/explore/dataset/property-parcel-polygons/"},
    "geocode": {"title": "OpenStreetMap Nominatim", "url": "https://nominatim.openstreetmap.org/"},
}


def _get(url: str, params: dict) -> Any:
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def records_at(dataset: str, lat: float, lon: float, within_m: float = 3) -> list[dict]:
    """The dataset's records whose geometry lies within a few metres of the point."""
    res = _get(COV_RECORDS.format(dataset=dataset), {"where": f"within_distance(geom, geom'POINT({lon} {lat})', {within_m}m)", "limit": 3})
    return res.get("results") or []


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

def lookup(address: str) -> dict[str, Any]:
    """A proposed site file for the address, with every field's source, for a person to confirm."""
    lat, lon, display = geocode(address)
    zoning = records_at(ZONING_DATASET, lat, lon)
    parcels = records_at(PARCEL_DATASET, lat, lon)
    return assemble(address, lat, lon, display, zoning, parcels)


def assemble(address: str, lat: float, lon: float, display: str, zoning: list[dict], parcels: list[dict]) -> dict[str, Any]:
    """The proposed site from the fetched records. Pure, so the browser build can fetch and hand the records in."""
    z = zoning[0] if zoning else {}
    p = parcels[0] if parcels else {}
    poly = (((p.get("geom") or {}).get("geometry") or {}).get("coordinates") or [[]])[0]
    metrics = parcel_metrics(poly) if len(poly) >= 3 else None
    district = z.get("zoning_district") or None
    cd1 = z.get("cd_1_number") or None
    notes = [f"Found by First Read on the address {address!r}: geocoded by Nominatim as {display!r}."]
    if district:
        notes.append(f"Zoning district {district}" + (f" (CD-1 by-law {cd1})" if cd1 else "") + " from the City's zoning districts dataset at that point.")
    else:
        notes.append("No zoning district found at that point in the City's dataset; enter it by hand.")
    if metrics:
        notes.append(f"Lot area {metrics['area_m2']:,.1f} m² from the parcel polygon ({metrics['vertices']} vertices" + (", a rectangle" if metrics["rectangular"] else ", not a rectangle: the frontage and depth are an equivalent rectangle with the same area") + f"); frontage taken as {metrics['frontage_from']}.")
    else:
        notes.append("No parcel polygon found at that point; enter the area, frontage and depth by hand.")
    notes.append("Transit-oriented area, the Community Vision map, water and sewer, trees and the owner are not in these datasets: answer them, or leave them 'not sure'.")
    civic = civic_address(p.get("civic_number"), p.get("streetname"))
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
        "existing_trees_on_site": [], "street_trees": {"count": None},
        "notes": " ".join(notes),
        "parcel": {"polygon_lonlat": poly, "civic_number": p.get("civic_number"), "streetname": p.get("streetname"),
                   "site_id": p.get("site_id"), "metrics": metrics, "source": SOURCES["parcel"]} if poly else None,
        "lookup": {"center": {"lat": lat, "lon": lon}, "geocoded_as": display, "zoning_record": {k: v for k, v in z.items() if k not in ("geom", "geo_point_2d")}},
        "sources": [SOURCES["geocode"], SOURCES["zoning"], SOURCES["parcel"]],
    }
    fields = {
        "zoning_district": {"value": district, "source": "zoning", "note": "the district polygon at the geocoded point"},
        "site_area_m2": {"value": site["site_area_m2"], "source": "parcel", "note": "from the parcel polygon"},
        "frontage_m": {"value": site["frontage_m"], "source": "parcel", "note": metrics["frontage_from"] if metrics else ""},
        "depth_m": {"value": site["depth_m"], "source": "parcel", "note": "the equivalent rectangle's other side" if metrics else ""},
        "has_water_and_sewer": {"value": True, "source": None, "note": "assumed for a City of Vancouver lot"},
    }
    return {"site": site, "fields": fields, "found": {"geocoded": bool(display), "zoning": bool(district), "parcel": bool(poly)}}


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
