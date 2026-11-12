"""The lot as a polygon: where the site carries its parcel ring (from the City's open data) or a boundary the
architect drew, the massing works on that shape instead of the equivalent rectangle.

Three pure pieces, standard library only:

    lot_ring(site)        the ring in the lot frame (metres; x along the frontage, y into the lot, the street at
                          y < 0): `site.boundary_m` as drawn, else `site.parcel.polygon_lonlat` placed in the
                          site's context frame (`site.osm.frame`, the one the roads and buildings are drawn in),
                          else turned so its frontage runs along x with the street side assumed
    inset(ring, sb)       the setback envelope: every edge moved inward by its setback (front for an edge facing
                          the street, rear for one facing away, side for the rest), or None where the setbacks
                          swallow the shape
    largest_rect(poly)    the largest rectangle, aligned with the lot frame, inside a polygon: the plate box the
                          rectangular masses and the layout's plates are placed in

Coordinates follow massing.json: metres, origin at the front-left corner of the equivalent rectangle.
"""

from __future__ import annotations

import math
from typing import Any

from .lookup import project

Point = tuple[float, float]


# ---------------------------------------------------------------- the ring in the lot frame

def _open(ring: list) -> list[Point]:
    pts = [(float(p[0]), float(p[1])) for p in ring]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    return pts


def _context_frame(site: dict) -> dict | None:
    """The frame `ffm.osm.build` placed the context in, reconstructed from what the site file keeps of it: the
    centre point, the x axis bearing and the snap shifts. None where any of those is missing."""
    osm = site.get("osm") or {}
    frame, c = osm.get("frame") or {}, osm.get("center") or {}
    W, D = float(site.get("frontage_m") or 0), float(site.get("depth_m") or 0)
    if c.get("lat") is None or frame.get("x_axis_bearing_deg") is None or not W or not D:
        return None
    b = math.radians(float(frame["x_axis_bearing_deg"]))
    x_axis = (math.sin(b), math.cos(b))
    y_axis = (-x_axis[1], x_axis[0])
    sh = frame.get("snapped_m") or {}
    sx, sy = float(sh.get("x") or 0), float(sh.get("y") or 0)
    origin = (-W / 2 * x_axis[0] - D / 2 * y_axis[0] + sy * y_axis[0] + sx * x_axis[0],
              -W / 2 * x_axis[1] - D / 2 * y_axis[1] + sy * y_axis[1] + sx * x_axis[1])
    lat0, lon0 = float(c["lat"]), float(c["lon"])
    k_lat, k_lon = 110540.0, 111320.0 * math.cos(math.radians(lat0))     # as osm._projector
    return {"origin": origin, "x_axis": x_axis, "y_axis": y_axis, "lat0": lat0, "lon0": lon0, "k_lat": k_lat, "k_lon": k_lon}


def _to_lot(fr: dict, lon: float, lat: float) -> Point:
    e, n = (lon - fr["lon0"]) * fr["k_lon"], (lat - fr["lat0"]) * fr["k_lat"]
    vx, vy = e - fr["origin"][0], n - fr["origin"][1]
    return (vx * fr["x_axis"][0] + vy * fr["x_axis"][1], vx * fr["y_axis"][0] + vy * fr["y_axis"][1])


def lot_ring(site: dict) -> dict[str, Any] | None:
    """The lot's outline in the lot frame, with where it came from, or None for a site that has only the
    equivalent rectangle. `ring` is a list of [x, y] (metres), counter-clockwise, not closed."""
    drawn = site.get("boundary_m")
    if isinstance(drawn, list) and len(drawn) >= 3:
        ring = _ccw(_open(drawn))
        return {"ring": [[round(x, 2), round(y, 2)] for x, y in ring], "source": "drawn", "frame": "lot",
                "note": "the boundary as drawn in the tool, in the lot frame"}
    poly = (site.get("parcel") or {}).get("polygon_lonlat")
    if not poly or len(poly) < 3:
        return None
    ll = _open(poly)
    fr = _context_frame(site)
    if fr:
        pts = [_to_lot(fr, lon, lat) for lon, lat in ll]
        return {"ring": [[round(x, 2), round(y, 2)] for x, y in _ccw(pts)], "source": "parcel", "frame": "context",
                "note": "the City's parcel polygon in the site's context frame (the frame the streets and buildings are drawn in)"}
    # no context frame: turn the ring so its frontage runs along x; which long side is the street is not known
    # from the parcel alone, so the lower edge is taken as the front and the note says so
    lat0 = sum(p[1] for p in ll) / len(ll)
    lon0 = sum(p[0] for p in ll) / len(ll)
    P = project(lat0, lon0)
    en = [P(lon, lat) for lon, lat in ll]
    metrics = (site.get("parcel") or {}).get("metrics") or {}
    bearing = metrics.get("frontage_bearing_deg")
    if bearing is None:
        from .lookup import bounding_rectangle
        box = bounding_rectangle(en)
        bearing = box["bearing_deg"] if box["side_a_m"] >= box["side_b_m"] else (box["bearing_deg"] + 90) % 180
    th = -math.radians(float(bearing))
    c, s = math.cos(th), math.sin(th)
    rot = [(x * c - y * s, x * s + y * c) for x, y in en]
    x0, y0 = min(p[0] for p in rot), min(p[1] for p in rot)
    pts = [(x - x0, y - y0) for x, y in rot]
    return {"ring": [[round(x, 2), round(y, 2)] for x, y in _ccw(pts)], "source": "parcel", "frame": "bearing",
            "note": "the City's parcel polygon turned so the frontage runs along x; the street side is assumed to be the lower edge (no context frame on file)"}


# ---------------------------------------------------------------- geometry

def signed_area(pts: list[Point]) -> float:
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return s / 2


def area(pts: list) -> float:
    return abs(signed_area([(float(p[0]), float(p[1])) for p in pts]))


def _ccw(pts: list[Point]) -> list[Point]:
    return list(pts) if signed_area(pts) >= 0 else list(reversed(pts))


def bbox(pts: list) -> list[float]:
    xs = [float(p[0]) for p in pts]
    ys = [float(p[1]) for p in pts]
    return [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]


def point_in(pt: Point, ring: list[Point]) -> bool:
    x, y = pt
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def simplify(pts: list[Point], angle_tol_deg: float = 2.0, short_edge_m: float = 0.3) -> list[Point]:
    """Drop vertices where the outline barely turns and the vertex at either end of a very short edge, so a
    curve published as many segments insets as a few straight edges. Never below three vertices."""
    p = list(pts)
    changed = True
    while changed and len(p) > 3:
        changed = False
        n = len(p)
        for i in range(n):
            a, b, c = p[i - 1], p[i], p[(i + 1) % n]
            h1 = math.atan2(b[1] - a[1], b[0] - a[0])
            h2 = math.atan2(c[1] - b[1], c[0] - b[0])
            d = abs(math.degrees(h2 - h1)) % 360
            t = min(d, 360 - d)
            if t < angle_tol_deg or t > 180 - angle_tol_deg or math.dist(a, b) < short_edge_m:
                del p[i]
                changed = True
                break
    return p


def _segments_cross(a: Point, b: Point, c: Point, d: Point) -> bool:
    def orient(p, q, r):
        v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return o1 != o2 and o3 != o4 and 0 not in (o1, o2, o3, o4)


def is_simple(pts: list[Point]) -> bool:
    n = len(pts)
    for i in range(n):
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            if _segments_cross(pts[i], pts[(i + 1) % n], pts[j], pts[(j + 1) % n]):
                return False
    return True


def edge_kind(a: Point, b: Point) -> str:
    """front for an edge whose outward side faces the street (y < 0), rear for one facing away, side otherwise;
    the ring is counter-clockwise, so the outward normal of a -> b is to its right."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    out_y = -dx / L          # right-hand normal (dy, -dx)/L, its y component
    if out_y < -0.7:
        return "front"
    if out_y > 0.7:
        return "rear"
    return "side"


def inset(ring: list, sb: dict | None) -> list[list[float]] | None:
    """The setback envelope of a counter-clockwise ring: each edge moved inward by the setback of its kind, the
    corners where consecutive moved edges meet. None where the result folds over itself or vanishes."""
    sb = sb or {}
    pts = simplify(_ccw(_open(ring)))
    n = len(pts)
    if n < 3:
        return None
    dist = {"front": float(sb.get("front") or 0), "rear": float(sb.get("rear") or 0), "side": float(sb.get("side") or 0)}
    lines = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        inward = (-dy / L, dx / L)
        s = dist[edge_kind(a, b)]
        lines.append(((a[0] + inward[0] * s, a[1] + inward[1] * s), (dx / L, dy / L)))

    def corners(ls: list) -> list[Point]:
        out: list[Point] = []
        k = len(ls)
        for i in range(k):
            (p1, d1), (p2, d2) = ls[i - 1], ls[i]
            cross = d1[0] * d2[1] - d1[1] * d2[0]
            if abs(cross) < 1e-9:
                out.append(p2)
                continue
            t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / cross
            out.append((p1[0] + d1[0] * t, p1[1] + d1[1] * t))
        return out

    # an edge that reverses direction once moved inward (the tip of an acute corner, a short edge between two
    # setbacks) has collapsed: it is dropped and its neighbours meet directly, until every edge still runs its way
    while len(lines) >= 3:
        out = corners(lines)
        k = len(lines)
        collapsed = []
        for i in range(k):
            a, b = out[i], out[(i + 1) % k]
            d = lines[i][1]
            run = (b[0] - a[0]) * d[0] + (b[1] - a[1]) * d[1]
            if run < 1e-6:
                collapsed.append((run, i))
        if not collapsed:
            break
        collapsed.sort()
        del lines[collapsed[0][1]]
    if len(lines) < 3:
        return None
    out = corners(lines)
    if signed_area(out) <= 1.0 or not is_simple(out):
        return None
    if any(not point_in(p, pts) for p in out):
        return None
    return [[round(x, 2), round(y, 2)] for x, y in out]


def largest_rect(poly: list, step: float = 0.5) -> dict[str, float] | None:
    """The largest rectangle aligned with the axes inside the polygon, found on a grid of `step` metres (the
    answer is good to about a step on each side). None for a polygon too small for one cell."""
    pts = _ccw(_open(poly))
    if len(pts) < 3:
        return None
    x0, y0, x1, y1 = bbox(pts)
    cols, rows = int((x1 - x0) / step), int((y1 - y0) / step)
    if cols < 1 or rows < 1:
        return None
    n = len(pts)
    best = (0.0, 0, 0, 0, 0)      # area, col, row, w, h in cells

    def spans(y: float) -> list[tuple[float, float]]:
        xs: list[float] = []
        for i in range(n):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
            if (ay > y) != (by > y):
                xs.append(ax + (y - ay) * (bx - ax) / (by - ay))
        xs.sort()
        return [(xs[k], xs[k + 1]) for k in range(0, len(xs) - 1, 2)]

    def cells_inside(sp: list[tuple[float, float]]) -> list[bool]:
        inside = [False] * cols
        for lo, hi in sp:
            c_lo = max(0, int(math.ceil((lo - x0) / step - 1e-9)))
            c_hi = min(cols - 1, int(math.floor((hi - x0) / step + 1e-9)) - 1)
            for c in range(c_lo, c_hi + 1):
                inside[c] = True
        return inside

    heights = [0] * cols
    # a cell counts only when it lies inside at both its bottom and its top edge (a hair in from each, so a row
    # through a vertex is read on either side of it), so the box never overhangs a slanted lot line
    eps = step * 0.01
    below = cells_inside(spans(y0 + eps))
    for r in range(rows):
        above = cells_inside(spans(y0 + (r + 1) * step - eps))
        inside = [below[c] and above[c] for c in range(cols)]
        below = cells_inside(spans(y0 + (r + 1) * step + eps))
        heights = [heights[c] + 1 if inside[c] else 0 for c in range(cols)]
        # the largest rectangle under the histogram of column heights ending at this row
        stack: list[int] = []
        for c in range(cols + 1):
            hc = heights[c] if c < cols else 0
            while stack and heights[stack[-1]] >= hc:
                top = stack.pop()
                hgt = heights[top]
                left = stack[-1] + 1 if stack else 0
                w = c - left
                a = w * hgt
                if a > best[0]:
                    best = (a, left, r - hgt + 1, w, hgt)
            stack.append(c)
    if best[0] <= 0:
        return None
    _, c, r, w, hgt = best
    return {"x": round(x0 + c * step, 2), "y": round(y0 + r * step, 2), "w": round(w * step, 2), "d": round(hgt * step, 2),
            "area_m2": round(w * hgt * step * step, 1)}


def shape_summary(ring: list) -> dict[str, Any] | None:
    """What shape the lot is, from ffm.parcel_shapes, reduced to what a reader needs."""
    try:
        from .parcel_shapes import classify
        c = classify([[list(p) for p in ring]], units="m")
    except (ValueError, ImportError):
        return None
    return {"class": c["class"], "note": c["note"], "rectangularity": round(c["rectangularity"], 3),
            "vertices": c["vertices"], "confidence": round(c["confidence"], 2), "alternative": c["alternative"]}
