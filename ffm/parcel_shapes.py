"""What shape is a parcel? Shape metrics and a plain classification for one parcel polygon, so the tool can say
"this lot is a flag lot" or "this is an L" before it lays out a building on an equivalent rectangle.

Input: the parcel as the City of Vancouver publishes it in `property-parcel-polygons` (Open Government Licence –
Vancouver): a GeoJSON geometry (Polygon or MultiPolygon), a list of [lon, lat] rings, or one ring; or the same in
metres already projected (`units="m"`). Pure standard library; no network.

Metrics: area, perimeter, vertex count after removing short edges (< 0.5 m) and collinear points (turn < 3 degrees),
the minimum-area bounding rectangle (sides, bearing, area; computed on the convex hull with `lookup.bounding_rectangle`,
whose edge-aligned search is exact for a convex ring), rectangularity = area / that rectangle's area, convexity =
area / convex hull area, aspect ratio, the number of rings, and, for the flag-lot test, the narrowest cross-section
found by sweeping lines across the parcel along both axes of that rectangle.

Classes (checked in this order; the thresholds are this module's own choices for a first read, not a City rule):
  multi_part      more than one outer ring
  rectangle       4 vertices and rectangularity >= 0.95
  near_rectangle  rectangularity >= 0.90
  flag_lot        a strip under 6 m wide and at least 6 m long, of near-constant width, at one end of the parcel,
                  stepping within 3 m to a body wider than 12 m
  trapezoid       4 vertices, rectangularity < 0.90
  l_shape         6 vertices, one reflex corner, convexity between 0.6 and 0.95
  irregular       anything else
`classify` also re-runs the decision with the thresholds and the simplification nudged a little and reports how many
of those runs agree (`confidence`) and the most common other answer (`alternative`), so a reader knows when to look.
"""

from __future__ import annotations

import math
from typing import Any

from .lookup import bounding_rectangle, project, ring_area

ANGLE_TOL_DEG = 3.0
SHORT_EDGE_M = 0.5
RECT_MIN = 0.95
NEAR_RECT_MIN = 0.90
L_CONVEXITY = (0.60, 0.95)
FLAG_POLE_MAX_M = 6.0
FLAG_BODY_MIN_M = 12.0
FLAG_POLE_MIN_LEN_M = 6.0
FLAG_POLE_RANGE_M = 1.5       # the pole's width may vary this much along its length
FLAG_STEP_M = 3.0             # the pole must widen to the body within this distance
CLASSES = ("rectangle", "near_rectangle", "trapezoid", "l_shape", "flag_lot", "irregular", "multi_part")

Point = tuple[float, float]


# ---------------------------------------------------------------- input

def _is_point(p: Any) -> bool:
    return isinstance(p, (list, tuple)) and len(p) >= 2 and all(isinstance(v, (int, float)) for v in p[:2])


def _rings_of(geom: Any) -> list[list[Point]]:
    """Every ring in the input as a list of (x, y), whatever the nesting: a GeoJSON geometry or Feature, a
    MultiPolygon's or Polygon's coordinates, a list of rings, or one ring."""
    if isinstance(geom, dict):
        if "geometry" in geom:
            return _rings_of(geom["geometry"])
        return _rings_of(geom.get("coordinates") or [])
    if not geom:
        return []
    if _is_point(geom[0]):
        return [[(float(p[0]), float(p[1])) for p in geom]]
    out: list[list[Point]] = []
    for g in geom:
        out.extend(_rings_of(g))
    return out


def _open(ring: list[Point]) -> list[Point]:
    return ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else list(ring)


def _looks_lonlat(rings: list[list[Point]]) -> bool:
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    return (all(-180 <= x <= 180 for x in xs) and all(-90 <= y <= 90 for y in ys)
            and max(xs) - min(xs) < 0.5 and max(ys) - min(ys) < 0.5)


def to_metres(geom: Any, units: str = "auto") -> tuple[list[list[Point]], dict[str, float] | None]:
    """The rings in local metres (east, north) and the projection's origin (None when the input was metres)."""
    rings = [_open(r) for r in _rings_of(geom)]
    rings = [r for r in rings if len(r) >= 3]
    if not rings:
        return [], None
    if units == "m" or (units == "auto" and not _looks_lonlat(rings)):
        return rings, None
    pts = [p for r in rings for p in r]
    lon0 = sum(p[0] for p in pts) / len(pts)
    lat0 = sum(p[1] for p in pts) / len(pts)
    P = project(lat0, lon0)
    return [[P(x, y) for x, y in r] for r in rings], {"lat": lat0, "lon": lon0}


# ---------------------------------------------------------------- geometry helpers, pure

def signed_area(pts: list[Point]) -> float:
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return s / 2


def point_in_ring(pt: Point, ring: list[Point]) -> bool:
    x, y = pt
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
    return inside


def split_parts(rings: list[list[Point]]) -> list[dict[str, Any]]:
    """Outer rings with their holes: a ring lying inside another ring is a hole of it (the first ring of a GeoJSON
    Polygon is its outer ring either way). Largest part first."""
    order = sorted(range(len(rings)), key=lambda i: -abs(signed_area(rings[i])))
    parts: list[dict[str, Any]] = []
    for i in order:
        r = rings[i]
        probe = (sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r))
        host = next((p for p in parts if point_in_ring(r[0], p["outer"]) and point_in_ring(probe, p["outer"])), None)
        if host is not None:
            host["holes"].append(r)
        else:
            parts.append({"outer": r, "holes": []})
    return parts


def perimeter(pts: list[Point]) -> float:
    return sum(math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))


def convex_hull(pts: list[Point]) -> list[Point]:
    """Andrew's monotone chain, counter-clockwise, no repeated point."""
    p = sorted(set(pts))
    if len(p) < 3:
        return p

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower: list[Point] = []
    for q in p:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], q) <= 0:
            lower.pop()
        lower.append(q)
    upper: list[Point] = []
    for q in reversed(p):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], q) <= 0:
            upper.pop()
        upper.append(q)
    return lower[:-1] + upper[:-1]


def _turn_deg(a: Point, b: Point, c: Point) -> float:
    """The absolute change of direction at b, in degrees (0 = straight on, 180 = doubling back)."""
    h1 = math.atan2(b[1] - a[1], b[0] - a[0])
    h2 = math.atan2(c[1] - b[1], c[0] - b[0])
    d = abs(math.degrees(h2 - h1)) % 360
    return min(d, 360 - d)


def simplify(pts: list[Point], angle_tol_deg: float = ANGLE_TOL_DEG, short_edge_m: float = SHORT_EDGE_M) -> list[Point]:
    """Drop the vertex at either end of an edge shorter than short_edge_m (the one whose loss changes the area
    least) and every vertex where the outline turns less than angle_tol_deg (or doubles back), until neither is
    left; never below three vertices."""
    p = list(pts)
    changed = True
    while changed and len(p) > 3:
        changed = False
        n = len(p)
        for i in range(n):
            a, b, c = p[i - 1], p[i], p[(i + 1) % n]
            t = _turn_deg(a, b, c)
            if t < angle_tol_deg or t > 180 - angle_tol_deg:
                del p[i]
                changed = True
                break
        if changed:
            continue
        n = len(p)
        for i in range(n):
            a, b = p[i], p[(i + 1) % n]
            if math.dist(a, b) < short_edge_m:
                ca = abs(signed_area(p[:i] + p[i + 1:]) - signed_area(p))
                j = (i + 1) % n
                cb = abs(signed_area(p[:j] + p[j + 1:]) - signed_area(p))
                del p[i if ca <= cb else j]
                changed = True
                break
    return p


def reflex_count(pts: list[Point]) -> int:
    """Corners turning against the ring's own direction (inward corners of an L)."""
    sgn = 1 if signed_area(pts) > 0 else -1
    n = len(pts)
    k = 0
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if cr * sgn < -1e-9:
            k += 1
    return k


def _cross_sections(rings: list[list[Point]], bearing_deg: float, max_samples: int = 400) -> dict[str, Any]:
    """Sweep lines perpendicular to the bearing across the parcel; for each, the total length inside it and the
    number of separate pieces. Returns positions along the bearing from the start, widths and piece counts."""
    th = math.radians(bearing_deg)
    c, s = math.cos(th), math.sin(th)
    rot = [[(x * c + y * s, -x * s + y * c) for x, y in r] for r in rings]
    us = [p[0] for r in rot for p in r]
    u0, u1 = min(us), max(us)
    length = u1 - u0
    if length <= 0:
        return {"t": [], "w": [], "pieces": [], "length": 0.0}
    step = max(0.5, length / max_samples)
    t_list, w_list, k_list = [], [], []
    t = step / 2
    while t < length:
        u = u0 + t
        vs: list[float] = []
        for r in rot:
            n = len(r)
            for i in range(n):
                (ua, va), (ub, vb) = r[i], r[(i + 1) % n]
                if (ua > u) != (ub > u):
                    vs.append(va + (u - ua) * (vb - va) / (ub - ua))
        vs.sort()
        w = sum(vs[i + 1] - vs[i] for i in range(0, len(vs) - 1, 2))
        t_list.append(t)
        w_list.append(w)
        k_list.append(len(vs) // 2)
        t += step
    return {"t": t_list, "w": w_list, "pieces": k_list, "length": length}


def _flag_from_profile(prof: dict[str, Any], pole_max: float, body_min: float) -> dict[str, Any] | None:
    """A pole at either end of a sweep profile: the run of single-piece cross-sections narrower than pole_max that
    starts at the end, at least FLAG_POLE_MIN_LEN_M long, of near-constant width, then within FLAG_STEP_M a
    cross-section wider than body_min."""
    t, w, k = prof["t"], prof["w"], prof["pieces"]
    if len(t) < 4:
        return None
    best = None
    for idx in (list(range(len(t))), list(range(len(t) - 1, -1, -1))):
        run = []
        for i in idx:
            if w[i] < pole_max and k[i] == 1 and w[i] > 0:
                run.append(i)
            else:
                break
        if not run:
            continue
        run_len = abs(t[run[-1]] - t[run[0]]) + (t[1] - t[0])
        widths = [w[i] for i in run]
        # trim the first and last sample (a bevelled corner at the end) before judging the constancy
        core = widths[1:-1] if len(widths) > 4 else widths
        if run_len < FLAG_POLE_MIN_LEN_M or max(core) - min(core) > FLAG_POLE_RANGE_M:
            continue
        end_t = t[run[-1]]
        rest = idx[len(run):]
        step_ok = any(w[i] > body_min for i in rest if abs(t[i] - end_t) <= FLAG_STEP_M + 1e-9)
        body = max((w[i] for i in rest), default=0.0)
        if step_ok and body > body_min:
            cand = {"pole_width_m": sum(core) / len(core), "pole_length_m": run_len, "body_width_m": body}
            if best is None or cand["pole_width_m"] < best["pole_width_m"]:
                best = cand
    return best


# ---------------------------------------------------------------- metrics and class

def shape_metrics(geom: Any, units: str = "auto", angle_tol_deg: float = ANGLE_TOL_DEG,
                  short_edge_m: float = SHORT_EDGE_M) -> dict[str, Any]:
    """The shape metrics of one parcel (see the module docstring). Metres and square metres; the bearing of the
    bounding rectangle's first side in degrees counter-clockwise from east, as `lookup.bounding_rectangle` gives it."""
    rings, origin = to_metres(geom, units)
    if not rings:
        raise ValueError("no ring with three or more points")
    parts = split_parts(rings)
    main = parts[0]
    area = sum(ring_area(p["outer"]) - sum(ring_area(h) for h in p["holes"]) for p in parts)
    main_area = ring_area(main["outer"]) - sum(ring_area(h) for h in main["holes"])
    simple = simplify(main["outer"], angle_tol_deg, short_edge_m)
    hull = convex_hull(main["outer"])
    box = bounding_rectangle(hull)
    hull_area = ring_area(hull)
    a, b = box["side_a_m"], box["side_b_m"]
    long_side, short_side = max(a, b), min(a, b)
    main_rings = [main["outer"]] + main["holes"]
    sweeps = [_cross_sections(main_rings, box["bearing_deg"]), _cross_sections(main_rings, box["bearing_deg"] + 90)]
    # the narrowest cross-section away from the last metre at each end, where any pointed corner reads as a sliver
    narrow = min((w for pr in sweeps for t, w in zip(pr["t"], pr["w"]) if w > 0 and 1.0 <= t <= pr["length"] - 1.0),
                 default=min((w for pr in sweeps for w in pr["w"] if w > 0), default=0.0))
    return {
        "area_m2": main_area if len(parts) == 1 else area,
        "main_part_area_m2": main_area,
        "perimeter_m": perimeter(main["outer"]) + sum(perimeter(h) for h in main["holes"]),
        "vertices_raw": len(main["outer"]),
        "vertices": len(simple),
        "reflex_corners": reflex_count(simple),
        "min_rect": {"side_a_m": a, "side_b_m": b, "bearing_deg": box["bearing_deg"], "area_m2": box["area_m2"]},
        "rectangularity": main_area / box["area_m2"] if box["area_m2"] else 0.0,
        "convexity": main_area / hull_area if hull_area else 0.0,
        "aspect_ratio": long_side / short_side if short_side else float("inf"),
        "rings": len(rings),
        "outer_rings": len(parts),
        "holes": sum(len(p["holes"]) for p in parts),
        "narrowest_cross_section_m": narrow,
        "origin": origin,
        "_simple": simple,
        "_sweeps": sweeps,
    }


def _decide(m: dict[str, Any], vertices: int, reflex: int, rect_min: float = RECT_MIN, near_min: float = NEAR_RECT_MIN,
            conv: tuple[float, float] = L_CONVEXITY, pole_max: float = FLAG_POLE_MAX_M, body_min: float = FLAG_BODY_MIN_M) -> tuple[str, Any]:
    if m["outer_rings"] > 1:
        return "multi_part", None
    r = m["rectangularity"]
    if vertices == 4 and r >= rect_min:
        return "rectangle", None
    if r >= near_min:
        return "near_rectangle", None
    flag = None
    for prof in m["_sweeps"]:
        f = _flag_from_profile(prof, pole_max, body_min)
        if f and (flag is None or f["pole_width_m"] < flag["pole_width_m"]):
            flag = f
    if flag:
        return "flag_lot", flag
    if vertices == 4:
        return "trapezoid", None
    if vertices == 6 and reflex == 1 and conv[0] <= m["convexity"] <= conv[1]:
        return "l_shape", None
    return "irregular", None


def _note(cls: str, m: dict[str, Any], flag: Any) -> str:
    a, b = sorted((m["min_rect"]["side_a_m"], m["min_rect"]["side_b_m"]))
    box = f"{b:.1f} x {a:.1f} m bounding rectangle"
    base = f"{m['area_m2']:,.0f} m2"
    if cls == "multi_part":
        return f"{m['outer_rings']} separate pieces, {base} in all; the tool reads the largest ({m['main_part_area_m2']:,.0f} m2) only."
    if cls == "rectangle":
        return f"A rectangle, {base}, {box}."
    if cls == "near_rectangle":
        return f"Nearly a rectangle ({m['rectangularity']:.0%} of its {box}), {base}, {m['vertices']} corners."
    if cls == "flag_lot":
        return (f"A flag lot: a strip about {flag['pole_width_m']:.1f} m wide and {flag['pole_length_m']:.0f} m long leads to a body "
                f"about {flag['body_width_m']:.0f} m wide; {base}. The equivalent rectangle overstates the buildable plate.")
    if cls == "trapezoid":
        return f"Four sides but not square-cornered ({m['rectangularity']:.0%} of its {box}), {base}."
    if cls == "l_shape":
        return f"An L: six corners, one inward; {m['convexity']:.0%} of its convex hull, {base}."
    extra = f", {m['holes']} hole(s)" if m["holes"] else ""
    return f"Irregular: {m['vertices']} corners, {m['rectangularity']:.0%} of its {box}{extra}, {base}."


def classify(geom: Any, units: str = "auto") -> dict[str, Any]:
    """The parcel's metrics, its class, the equivalent rectangle (the minimum bounding rectangle's sides), a one-line
    note, and how firm the call is: `confidence` is the share of nudged re-runs (thresholds moved a little, the
    simplification tolerances halved and doubled) that give the same class; `alternative` is the most common other
    class among them, or None."""
    m = shape_metrics(geom, units)
    cls, flag = _decide(m, m["vertices"], m["reflex_corners"])
    runs: list[str] = []
    for kw in ({"rect_min": RECT_MIN - 0.015}, {"rect_min": RECT_MIN + 0.015},
               {"near_min": NEAR_RECT_MIN - 0.015}, {"near_min": NEAR_RECT_MIN + 0.015},
               {"conv": (L_CONVEXITY[0] - 0.04, L_CONVEXITY[1] + 0.02)}, {"conv": (L_CONVEXITY[0] + 0.04, L_CONVEXITY[1] - 0.02)},
               {"pole_max": FLAG_POLE_MAX_M + 1.0, "body_min": FLAG_BODY_MIN_M - 2.0},
               {"pole_max": FLAG_POLE_MAX_M - 1.0, "body_min": FLAG_BODY_MIN_M + 2.0}):
        runs.append(_decide(m, m["vertices"], m["reflex_corners"], **kw)[0])
    main = m["_simple"]
    rings, _ = to_metres(geom, units)
    outer = split_parts(rings)[0]["outer"]
    for at, se in ((ANGLE_TOL_DEG / 2, SHORT_EDGE_M / 2), (ANGLE_TOL_DEG * 2, SHORT_EDGE_M * 2), (ANGLE_TOL_DEG * 2, SHORT_EDGE_M / 2)):
        s = simplify(outer, at, se)
        runs.append(_decide(m, len(s), reflex_count(s))[0])
    agree = sum(1 for r in runs if r == cls)
    others: dict[str, int] = {}
    for r in runs:
        if r != cls:
            others[r] = others.get(r, 0) + 1
    alternative = max(others, key=others.get) if others else None
    # how far the deciding figures sit from the nearest threshold, in the units of the nudges (0 = on the line)
    margins = {"rectangularity_0.95": abs(m["rectangularity"] - RECT_MIN) / 0.015,
               "rectangularity_0.90": abs(m["rectangularity"] - NEAR_RECT_MIN) / 0.015}
    if m["vertices"] == 6:
        margins["convexity"] = min(abs(m["convexity"] - L_CONVEXITY[0]) / 0.04, abs(m["convexity"] - L_CONVEXITY[1]) / 0.02)
    if flag:
        margins["pole_width"] = abs(FLAG_POLE_MAX_M - flag["pole_width_m"]) / 1.0
        margins["body_width"] = abs(flag["body_width_m"] - FLAG_BODY_MIN_M) / 2.0
    out = {k: v for k, v in m.items() if not k.startswith("_")}
    out.update({
        "class": cls,
        "equivalent_rectangle": {"side_a_m": m["min_rect"]["side_a_m"], "side_b_m": m["min_rect"]["side_b_m"],
                                 "bearing_deg": m["min_rect"]["bearing_deg"]},
        "flag": flag,
        "note": _note(cls, m, flag),
        "confidence": agree / len(runs),
        "alternative": alternative,
        "margin": min(margins.values()),
        "simplified_m": [[round(x, 2), round(y, 2)] for x, y in main],
    })
    return out


def rounded(res: dict[str, Any]) -> dict[str, Any]:
    """A copy of a classify() result with the figures rounded for a report."""
    def r(v):
        if isinstance(v, float):
            return round(v, 3) if abs(v) < 10 else round(v, 1)
        if isinstance(v, dict):
            return {k: r(x) for k, x in v.items()}
        if isinstance(v, list):
            return [r(x) for x in v]
        return v
    return r(res)


def thumbnail_svg(geom: Any, size: int = 120, units: str = "auto", pad: int = 6) -> str:
    """The parcel drawn in a size x size box, north up, scaled to fit; holes and extra parts included."""
    rings, _ = to_metres(geom, units)
    if not rings:
        return ""
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    k = (size - 2 * pad) / span
    ox = pad + ((size - 2 * pad) - (max(xs) - min(xs)) * k) / 2
    oy = pad + ((size - 2 * pad) - (max(ys) - min(ys)) * k) / 2
    d = " ".join("M" + " L".join(f"{ox + (x - min(xs)) * k:.1f},{oy + (max(ys) - y) * k:.1f}" for x, y in r) + " Z" for r in rings)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<path d="{d}" fill="#d9e4ec" stroke="#1f3a4d" stroke-width="1.2" fill-rule="evenodd"/>'
            f'<text x="{size - 4}" y="12" font-size="9" text-anchor="end" font-family="sans-serif">N</text></svg>')
