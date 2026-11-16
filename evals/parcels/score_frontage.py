"""Score a frontage guess against the edges a person marked on the label page.

    python evals/parcels/score_frontage.py [--cache streets-cache.json]

The guess is the rule the tool uses for a site (`lookup.street_bearing`: the parcel side along the street the parcel
is named for), applied to the label page's edges: for each parcel, the City's `public-streets` centrelines within
reach of the parcel are fetched (one request per parcel, plain User-Agent, cached when --cache is given), the ones
named as the address is (`lookup.parse_address`) are kept, lanes left out, and the edge between two of the page's
corners whose midpoint lies nearest to that street is the guess; with no street of that name in reach, the edge nearest
any street. The cross street is guessed as the edge nearest the nearest street of another name, if one comes within
12 m. Prints one line per parcel and the totals.
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from ffm.lookup import parse_address, project  # noqa: E402

UA = {"User-Agent": "First-Read-survey/0.1", "Accept": "application/json"}
STREETS = "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/public-streets/records"
WORDS = {"AVENUE": "AV", "AVE": "AV", "STREET": "ST", "DRIVE": "DR", "ROAD": "RD", "CRESCENT": "CRES", "BOULEVARD": "BLVD", "PLACE": "PL"}


def norm(name: str | None) -> str:
    s = re.sub(r"^[\d-]+\s+", "", str(name or "").upper()).strip()
    return " ".join(WORDS.get(w, w) for w in s.split())


def fetch_streets(lon: float, lat: float, radius_m: float, cache: dict, cache_path: Path | None) -> list[dict]:
    key = f"{lon:.6f},{lat:.6f},{radius_m:.0f}"
    if key not in cache:
        params = {"where": f"within_distance(geom, geom'POINT({lon} {lat})', {radius_m:.0f}m)", "limit": 80, "select": "hblock,streetuse,geom"}
        url = STREETS + "?" + urllib.parse.urlencode(params)
        res: dict = {}
        for _ in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                    res = json.load(r)
                break
            except (urllib.error.URLError, TimeoutError, ValueError):
                time.sleep(2)
        cache[key] = res.get("results", [])
        if cache_path:
            cache_path.write_text(json.dumps(cache), encoding="utf-8")
        time.sleep(0.2)
    return cache[key]


def seg_dist(p, a, b) -> float:
    (ax, ay), (bx, by), (px, py) = a, b, p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def line_dist(p, line) -> float:
    return min(seg_dist(p, line[i], line[i + 1]) for i in range(len(line) - 1))


def edge_midpoint(pts, corners, e):
    """Edge e (1-based) runs from corners[e-1] to corners[e % n] along the published ring; its midpoint by length."""
    a, b = corners[e - 1], corners[e % len(corners)]
    path = [pts[a]]
    i = a
    while i != b:
        i = (i + 1) % len(pts)
        path.append(pts[i])
    total = sum(math.dist(path[k], path[k + 1]) for k in range(len(path) - 1))
    acc, half = 0.0, total / 2
    for k in range(len(path) - 1):
        d = math.dist(path[k], path[k + 1])
        if acc + d >= half:
            t = (half - acc) / d if d else 0
            return (path[k][0] + t * (path[k + 1][0] - path[k][0]), path[k][1] + t * (path[k + 1][1] - path[k][1]))
        acc += d
    return path[-1]


def guess_for(label: dict, parcel: dict, cache: dict, cache_path: Path | None) -> dict:
    ring = parcel["ring_lonlat"][0]
    lon0 = sum(q[0] for q in ring) / len(ring)
    lat0 = sum(q[1] for q in ring) / len(ring)
    to_m = project(lat0, lon0)          # metres from the centroid; takes (lon, lat)
    pts = [to_m(q[0], q[1]) for q in ring]
    corners = label["corners"]
    n = len(corners)
    mids = {e: edge_midpoint(pts, corners, e) for e in range(1, n + 1)}
    area = parcel["metrics"]["area_m2"]
    radius = 60 + math.sqrt(area)
    streets = []
    for s in fetch_streets(lon0, lat0, radius, cache, cache_path):
        g = (s.get("geom") or {}).get("geometry") or {}
        parts = [g["coordinates"]] if g.get("type") == "LineString" else (g.get("coordinates", []) if g.get("type") == "MultiLineString" else [])
        for part in parts:
            streets.append((norm(s.get("hblock")), s.get("streetuse"), [to_m(x, y) for x, y in part]))
    want = norm(parse_address(label.get("address") or "")["street"])
    roads = [s for s in streets if s[1] != "Lane"]
    named = [s for s in roads if s[0] == want] if want else []

    def nearest_edge(lines):
        best = None
        for e, m in mids.items():
            d = min(line_dist(m, ln[2]) for ln in lines)
            if best is None or d < best[0]:
                best = (round(d, 1), e)
        return best

    guess = nearest_edge(named) if named else None
    fallback = nearest_edge(roads) if roads else None
    others = [s for s in roads if s[0] != want]
    cross = None
    if others:
        best = None
        for ln in others:
            d = min(line_dist(m, ln[2]) for m in mids.values())
            if best is None or d < best[0]:
                best = (d, ln)
        if best and best[0] < 12:
            cross = nearest_edge([best[1]])
    truth = [f["edge"] for f in label.get("frontage_edges", []) if f["role"] == "frontage"]
    cross_truth = [f["edge"] for f in label.get("frontage_edges", []) if f["role"] == "cross_street"]
    return {"address": label["address"], "street": want, "named_streets": len(named), "edges": n,
            "guess": (guess or fallback), "by": "named street" if guess else ("nearest street" if fallback else None),
            "truth": truth, "cross_guess": cross, "cross_truth": cross_truth}


def main() -> None:
    cache_path = None
    if "--cache" in sys.argv:
        cache_path = Path(sys.argv[sys.argv.index("--cache") + 1])
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path and cache_path.exists() else {}
    labels = json.loads((HERE / "labels.json").read_text(encoding="utf-8"))
    uncertain = json.loads((HERE / "uncertain.json").read_text(encoding="utf-8"))
    by_id = {p["site_id"]: p for p in uncertain["parcels"]}
    n = ok = n_cross = ok_cross = 0
    for L in labels["labels"]:
        r = guess_for(L, by_id[L["site_id"]], cache, cache_path)
        mark = ""
        if r["truth"]:
            n += 1
            hit = bool(r["guess"]) and r["guess"][1] == r["truth"][0]
            ok += hit
            mark = "=" if hit else "X"
        if r["cross_truth"]:
            n_cross += 1
            ok_cross += bool(r["cross_guess"]) and r["cross_guess"][1] in r["cross_truth"]
        print(f'{r["address"]:26} {r["street"]:16} guess {str(r["guess"][1] if r["guess"] else None):4} ({r["by"] or "no street in reach"}) '
              f'marked {r["truth"]} cross guess {r["cross_guess"][1] if r["cross_guess"] else None} marked {r["cross_truth"]} {mark}')
    print()
    print(f"frontage: {ok} of {n} marked edges guessed right; cross street: {ok_cross} of {n_cross}")


if __name__ == "__main__":
    main()
