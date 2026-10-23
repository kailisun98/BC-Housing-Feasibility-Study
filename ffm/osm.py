"""OpenStreetMap context for a site: the roads, buildings and trees around the lot, in the lot's own metres.

`python -m ffm context --site sites/<id>.json` locates the address with Nominatim (or takes a centre
given in the site file or on the command line), asks the Overpass API for everything within a radius,
turns it into the lot frame the massing uses (origin at the front-left lot corner, x along the
frontage, y into the lot) and writes the result under the site's "osm" key. The figures in the UI
read that block, so the page needs no network and the context is committed with the site.

Standard library only. Map data © OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright).
"""
from __future__ import annotations

import json
import math
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

NOMINATIM = "https://nominatim.openstreetmap.org/search"
OVERPASS = "https://overpass-api.de/api/interpreter"
USER_AGENT = "funding-fit-memo/0.1 (ARCH 540, UBC; https://github.com/kailisun98/BC-Housing-Feasibility-Study)"
ATTRIBUTION = "Map data © OpenStreetMap contributors, ODbL 1.0"
DEFAULT_RADIUS_M = 120.0

# pavement widths by highway class when OSM carries no width or lanes tag (metres)
ROAD_WIDTH_M = {
    "motorway": 24, "trunk": 20, "primary": 18, "secondary": 16, "tertiary": 14, "residential": 11,
    "unclassified": 10, "living_street": 8, "service": 5, "pedestrian": 4, "footway": 2, "cycleway": 2.5,
    "path": 1.5, "steps": 2, "track": 3,
}
MINOR = {"footway", "cycleway", "path", "steps", "track", "service", "pedestrian"}
ABBREV = {"e": "east", "w": "west", "n": "north", "s": "south", "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest",
          "ave": "avenue", "av": "avenue", "st": "street", "blvd": "boulevard", "rd": "road", "dr": "drive", "cres": "crescent",
          "pl": "place", "hwy": "highway", "ln": "lane", "ct": "court", "pkwy": "parkway"}


def _get(url: str, params: dict | None = None, data: str | None = None) -> Any:
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, data=data.encode("utf-8") if data else None,
                                 headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def geocode(address: str) -> tuple[float, float, str]:
    """The address as a point, from Nominatim (the result is saved in the site file, so this runs once).
    A parenthesis such as '(formerly 1050 Expo Blvd)' is dropped first and tried on its own second."""
    plain = re.sub(r"\s*\([^)]*\)", "", address).strip(" ,")
    tries = [plain]
    for inner in re.findall(r"\(([^)]*)\)", address):
        alt = re.sub(r"^(formerly|was|previously)\s+", "", inner.strip(), flags=re.I)
        tail = plain.split(",", 1)[1] if "," in plain else ""
        tries.append((alt + ("," + tail if tail else "")).strip())
    import time
    for i, q in enumerate(tries):
        if i:
            time.sleep(1.1)                             # Nominatim's usage policy: at most one request a second
        res = _get(NOMINATIM, {"q": q, "format": "jsonv2", "limit": 1})
        if res:
            return float(res[0]["lat"]), float(res[0]["lon"]), str(res[0].get("display_name", ""))
    raise ValueError(f"Nominatim found nothing for {address!r}; put context.center [lat, lon] in the site file or pass --center.")


def overpass(lat: float, lon: float, radius_m: float) -> tuple[list[dict], str]:
    q = (f"[out:json][timeout:60];("
         f'way(around:{radius_m:.0f},{lat:.6f},{lon:.6f})["highway"];'
         f'way(around:{radius_m:.0f},{lat:.6f},{lon:.6f})["building"];'
         f'node(around:{radius_m:.0f},{lat:.6f},{lon:.6f})["natural"="tree"];'
         f");out tags geom;")
    res = _get(OVERPASS, data="data=" + urllib.parse.quote(q))
    return res.get("elements", []), q


def norm_name(name: str) -> str:
    """'E 19th Ave' and 'East 19th Avenue' compare equal."""
    words = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower()).split()
    return " ".join(ABBREV.get(w, w) for w in words)


def _num(s: Any) -> float | None:
    if s is None:
        return None
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)", str(s))
    return float(m.group(1)) if m else None


def road_width(tags: dict) -> float:
    w = _num(tags.get("width"))
    if w:
        return w
    lanes = _num(tags.get("lanes"))
    if lanes:
        return lanes * 3.3
    return float(ROAD_WIDTH_M.get(tags.get("highway", ""), 8))


def building_height(tags: dict) -> float | None:
    h = _num(tags.get("height")) or _num(tags.get("building:height"))
    if h:
        return h
    levels = _num(tags.get("building:levels"))
    if levels:
        return levels * 3.2
    return None


# ---------------------------------------------------------------- geometry: lat/lon -> east/north -> lot frame

def _projector(lat0: float, lon0: float):
    k_lat = 110540.0
    k_lon = 111320.0 * math.cos(math.radians(lat0))
    return lambda lat, lon: ((lon - lon0) * k_lon, (lat - lat0) * k_lat)


def _nearest_on_polyline(pts: list[tuple[float, float]], p: tuple[float, float]):
    """(distance, nearest point, unit direction of that segment)."""
    best = (float("inf"), pts[0], (1.0, 0.0))
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        if L2 == 0:
            continue
        t = max(0.0, min(1.0, ((p[0] - x1) * dx + (p[1] - y1) * dy) / L2))
        q = (x1 + t * dx, y1 + t * dy)
        d = math.hypot(p[0] - q[0], p[1] - q[1])
        if d < best[0]:
            L = math.sqrt(L2)
            best = (d, q, (dx / L, dy / L))
    return best


def lot_frame(center_en: tuple[float, float], street_pts: list[tuple[float, float]], W: float, D: float) -> dict:
    """The lot frame from the front street: y runs from the street into the lot, x along the frontage to the
    right of someone standing on the street looking in; the origin is the front-left corner, placed so the
    lot's centre sits on the geocoded point."""
    _, q, d = _nearest_on_polyline(street_pts, center_en)
    n = (-d[1], d[0])                                   # a perpendicular to the street
    if (center_en[0] - q[0]) * n[0] + (center_en[1] - q[1]) * n[1] < 0:
        n = (-n[0], -n[1])                              # pointing from the street toward the lot
    y_axis = n
    x_axis = (n[1], -n[0])                              # the viewer's right, looking along y
    origin = (center_en[0] - W / 2 * x_axis[0] - D / 2 * y_axis[0], center_en[1] - W / 2 * x_axis[1] - D / 2 * y_axis[1])
    bearing = (math.degrees(math.atan2(x_axis[0], x_axis[1])) + 360) % 360   # from north, clockwise
    return {"origin_en": origin, "x_axis": x_axis, "y_axis": y_axis, "x_axis_bearing_deg": round(bearing, 1), "street_distance_m": round(_nearest_on_polyline(street_pts, center_en)[0], 1)}


def to_lot(frame: dict, en: tuple[float, float]) -> list[float]:
    vx, vy = en[0] - frame["origin_en"][0], en[1] - frame["origin_en"][1]
    return [round(vx * frame["x_axis"][0] + vy * frame["x_axis"][1], 1), round(vx * frame["y_axis"][0] + vy * frame["y_axis"][1], 1)]


def _centroid(poly: list[list[float]]) -> tuple[float, float]:
    n = len(poly)
    return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)


def _clip_polyline(pts: list[list[float]], centre: tuple[float, float], R: float) -> list[list[list[float]]]:
    """The runs of a polyline that come within R of the centre (a segment counts if either end does)."""
    runs: list[list[list[float]]] = []
    cur: list[list[float]] = []
    inside = [math.hypot(p[0] - centre[0], p[1] - centre[1]) <= R for p in pts]
    for i, p in enumerate(pts):
        keep = inside[i] or (i > 0 and inside[i - 1]) or (i + 1 < len(pts) and inside[i + 1])
        if keep:
            cur.append(p)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return [r for r in runs if len(r) > 1]


def _snap(frame: dict, roads: list[tuple[dict, list[tuple[float, float]]]], W: float, D: float) -> dict:
    """Nudge the frame so the lot sits where the streets say it does: a geocoded point is the address's building
    or parcel centroid, which on a corner lot is not the lot's centre. The front street's centreline goes to half
    a right-of-way in front of the lot line, and a cross street beside the lot to half a right-of-way past the
    side lot line. Right-of-way halves: 10 m (Vancouver's 66 ft streets) or more where the pavement is wider."""
    shifts = {"x": 0.0, "y": 0.0, "cross_street": None}
    def row_half(tags):
        return max(10.0, road_width(tags) / 2 + 3.0)
    # the front street: its nearest point to the lot centre, in lot coordinates
    front_tags, front_pts = roads[0]
    centre_lot = [W / 2, D / 2]
    lot_pts = [to_lot(frame, p) for p in front_pts]
    _, q, _ = _nearest_on_polyline([tuple(p) for p in lot_pts], tuple(centre_lot))
    want_y = -row_half(front_tags)
    shifts["y"] = round(q[1] - want_y, 1)                 # move the frame so the street lands at want_y
    frame = dict(frame, origin_en=(frame["origin_en"][0] + shifts["y"] * frame["y_axis"][0], frame["origin_en"][1] + shifts["y"] * frame["y_axis"][1]))
    # a cross street beside the lot: roughly perpendicular to x, passing within 20 m of a side lot line
    best = None
    for tags, pts in roads[1:]:
        if tags.get("highway") in MINOR or not tags.get("name"):
            continue
        lp = [to_lot(frame, p) for p in pts]
        for (x1, y1), (x2, y2) in zip(lp, lp[1:]):
            dx, dy = x2 - x1, y2 - y1
            L = math.hypot(dx, dy)
            if L < 5 or abs(dx) / L > 0.5:
                continue                                 # not steep enough in y to be a cross street
            if not (min(y1, y2) - 5 <= D / 2 <= max(y1, y2) + 5):
                continue                                 # does not pass beside the lot
            t = (D / 2 - y1) / dy if dy else 0.0
            x_at = x1 + t * dx
            for side, edge, sign in (("left", 0.0, -1), ("right", W, 1)):
                off = abs(x_at - edge)
                if off < 20 and (best is None or off < best[0]):
                    best = (off, side, sign, x_at, row_half(tags), tags.get("name"))
    if best:
        _, side, sign, x_at, rh, name = best
        want_x = -rh if side == "left" else W + rh
        shifts["x"] = round(x_at - want_x, 1)
        shifts["cross_street"] = {"name": name, "side": side}
        frame = dict(frame, origin_en=(frame["origin_en"][0] + shifts["x"] * frame["x_axis"][0], frame["origin_en"][1] + shifts["x"] * frame["x_axis"][1]))
    frame["snapped"] = shifts
    return frame


# ---------------------------------------------------------------- the whole thing

def build(site: dict, elements: list[dict], center: tuple[float, float], radius_m: float, query: str = "", geocoded_as: str = "") -> dict:
    """Turn Overpass elements into the site's `osm` block. Pure: no network, so it is testable."""
    W, D = float(site.get("frontage_m") or 0), float(site.get("depth_m") or 0)
    if not W or not D:
        raise ValueError("Site needs frontage_m and depth_m to place the context.")
    proj = _projector(center[0], center[1])
    ways = [e for e in elements if e.get("type") == "way" and e.get("geometry")]
    roads = [e for e in ways if "highway" in (e.get("tags") or {})]
    # the front street: the named way matching the site's street, else the nearest road that is not a path
    ctx = site.get("context") or {}
    want = norm_name((ctx.get("street") or {}).get("name") or (site.get("street_trees") or {}).get("street") or "")
    cands = []
    for e in roads:
        pts = [proj(g["lat"], g["lon"]) for g in e["geometry"]]
        if len(pts) < 2:
            continue
        d = _nearest_on_polyline(pts, (0.0, 0.0))[0]
        name = (e.get("tags") or {}).get("name", "")
        rank = 0 if want and norm_name(name) == want else (1 if name and e["tags"].get("highway") not in MINOR else 2)
        cands.append((rank, d, e, pts))
    if not cands:
        raise ValueError("No road within the radius; widen --radius or check the centre.")
    cands.sort(key=lambda c: (c[0], c[1]))
    rank, _, front, front_pts = cands[0]
    frame = lot_frame((0.0, 0.0), front_pts, W, D)
    frame = _snap(frame, [(front.get("tags") or {}, front_pts)] + [(c[2].get("tags") or {}, c[3]) for c in cands[1:]], W, D)
    front_name = (front.get("tags") or {}).get("name", "")
    keep_r = radius_m * 1.15
    centre_lot = (W / 2, D / 2)

    out_roads, out_buildings, out_trees, on_site = [], [], [], []
    for e in roads:
        pts = [to_lot(frame, proj(g["lat"], g["lon"])) for g in e["geometry"]]
        t = e.get("tags") or {}
        for run in _clip_polyline(pts, centre_lot, keep_r):
            out_roads.append({"id": e["id"], "name": t.get("name"), "highway": t.get("highway"), "width_m": round(road_width(t), 1), "points": run})
    for e in ways:
        t = e.get("tags") or {}
        if "building" not in t:
            continue
        poly = [to_lot(frame, proj(g["lat"], g["lon"])) for g in e["geometry"]]
        if len(poly) > 1 and poly[0] == poly[-1]:
            poly = poly[:-1]
        if len(poly) < 3:
            continue
        cx, cy = _centroid(poly)
        if math.hypot(cx - centre_lot[0], cy - centre_lot[1]) > keep_r:
            continue
        rec = {"id": e["id"], "name": t.get("name"), "building": t.get("building"), "height_m": building_height(t), "levels": _num(t.get("building:levels")), "polygon": poly}
        if 0 <= cx <= W and 0 <= cy <= D:
            on_site.append({k: rec[k] for k in ("id", "name", "building", "height_m")})   # the lot is being redeveloped: drawn no more
        else:
            out_buildings.append(rec)
    for e in elements:
        if e.get("type") == "node" and (e.get("tags") or {}).get("natural") == "tree":
            x, y = to_lot(frame, proj(e["lat"], e["lon"]))
            t = e.get("tags") or {}
            out_trees.append({"id": e["id"], "x": x, "y": y, "species": t.get("species") or t.get("genus"), "crown_m": _num(t.get("diameter_crown")) and _num(t.get("diameter_crown")) / 2})
    return {
        "source": "OpenStreetMap via Nominatim and the Overpass API",
        "attribution": ATTRIBUTION,
        "licence_url": "https://www.openstreetmap.org/copyright",
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "center": {"lat": round(center[0], 6), "lon": round(center[1], 6), "geocoded_as": geocoded_as},
        "radius_m": radius_m,
        "frame": {"origin": "front-left lot corner: the lot's centre starts on the centre point, then the frame is nudged so the front street "
                            "and any cross street sit half a right-of-way outside the lot lines (see snapped_m)",
                  "x_axis_bearing_deg": frame["x_axis_bearing_deg"], "front_street": front_name or None, "front_street_way": front["id"],
                  "front_street_matched_by_name": rank == 0, "snapped_m": frame.get("snapped")},
        "counts": {"roads": len(out_roads), "buildings": len(out_buildings), "trees": len(out_trees), "buildings_on_site_omitted": len(on_site)},
        "buildings_on_site_omitted": on_site,
        "roads": out_roads, "buildings": out_buildings, "trees": out_trees,
        "query": query,
    }


def fetch_for_site(site: dict, radius_m: float = DEFAULT_RADIUS_M, center: tuple[float, float] | None = None) -> dict:
    ctx = site.get("context") or {}
    geocoded_as = ""
    if center is None and ctx.get("center"):
        c = ctx["center"]
        center = (float(c["lat"]), float(c["lon"])) if isinstance(c, dict) else (float(c[0]), float(c[1]))
    prev = (site.get("osm") or {}).get("center") or {}
    if center is None and prev.get("lat") is not None:
        center, geocoded_as = (float(prev["lat"]), float(prev["lon"])), prev.get("geocoded_as", "")   # fetched before: no new geocoding
    if center is None:
        lat, lon, geocoded_as = geocode(site["address"])
        center = (lat, lon)
    elements, q = overpass(center[0], center[1], radius_m)
    return build(site, elements, center, radius_m, q, geocoded_as)


def dumps_site(site: dict) -> str:
    """The site file as JSON with short things on one line (number lists, flat little objects such as a tree
    or a source) so the hand-written part stays readable beside the map data."""
    def flat(v) -> bool:
        return v is None or isinstance(v, (bool, int, float, str))
    def enc(v, ind: str) -> str:
        if isinstance(v, dict):
            if v and all(flat(x) for x in v.values()):
                one = "{" + ", ".join(f"{json.dumps(k, ensure_ascii=False)}: {json.dumps(x, ensure_ascii=False)}" for k, x in v.items()) + "}"
                if len(one) <= 110:
                    return one
            if not v:
                return "{}"
            inner = ind + "  "
            return "{\n" + ",\n".join(f"{inner}{json.dumps(k, ensure_ascii=False)}: {enc(x, inner)}" for k, x in v.items()) + "\n" + ind + "}"
        if isinstance(v, list):
            if not v:
                return "[]"
            if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v):
                return "[" + ", ".join(json.dumps(x) for x in v) + "]"
            inner = ind + "  "
            return "[\n" + ",\n".join(inner + enc(x, inner) for x in v) + "\n" + ind + "]"
        return json.dumps(v, ensure_ascii=False)
    return enc(site, "") + "\n"
