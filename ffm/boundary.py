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
    oriented_ring(site)   the lot turned so the face `site.front_face` names is the street side, with the affine
                          transform (`rotate_deg`, `tx`, `ty`) that takes the old lot frame to the new one

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


# ---------------------------------------------------------------- which face is the front

ADJOIN_M = 15.0    # a road adjoins the lot where its centreline comes within half its width plus this of the lot line
SIDE_NORMALS = {"front": (0.0, -1.0), "rear": (0.0, 1.0), "left": (-1.0, 0.0), "right": (1.0, 0.0)}


def lot_corners(ring: list) -> list[Point]:
    """The corners a hand would draw (no curve segments): what massing records as `lot.corners`, and what
    `front_face: {"edge": i}` counts edges on (edge i runs from corner i to corner i + 1)."""
    return simplify([(float(p[0]), float(p[1])) for p in ring], 3.0, 0.5)


def _dist_seg(p: Point, a: Point, b: Point) -> tuple[float, Point]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    q = (a[0] + t * dx, a[1] + t * dy)
    return math.hypot(p[0] - q[0], p[1] - q[1]), q


def _dist_polyline(p: Point, pts: list[Point]) -> tuple[float, Point]:
    if len(pts) == 1:
        return math.dist(p, pts[0]), pts[0]
    return min((_dist_seg(p, pts[i], pts[i + 1]) for i in range(len(pts) - 1)), key=lambda r: r[0])


def _outward(a: Point, b: Point) -> Point:
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    return (dy / L, -dx / L)     # counter-clockwise ring: the outside is to the right of a -> b


FACING_COS = math.cos(math.radians(45))   # a road faces an edge where it lies within 45 degrees of the edge's outward normal


def _road_frontage(corners: list[Point], pts: list[Point], reach: float) -> list[tuple[float, float]]:
    """Per edge of the lot: (metres of the edge that face the road within `reach`, mean distance of those). A sample
    counts where the road's nearest point lies within 45 degrees of the edge's outward normal: before 17 Nov 2026 any
    point on the outward side counted, so on 609 Heatley Ave the stretch of Keefer St past the corner, diagonally off
    the Heatley frontage, gave that edge 16.4 m against the 15.2 m that actually face Keefer, and front_face
    {"street": "Keefer St"} kept Heatley as the front."""
    out = []
    n = len(corners)
    for i in range(n):
        a, b = corners[i], corners[(i + 1) % n]
        L = math.dist(a, b)
        nrm = _outward(a, b)
        k = max(2, int(L))     # a sample about every metre
        near, dsum = 0, 0.0
        for j in range(k):
            t = (j + 0.5) / k
            p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            d, q = _dist_polyline(p, pts)
            if d <= reach and (d < 1e-6 or (q[0] - p[0]) * nrm[0] + (q[1] - p[1]) * nrm[1] > FACING_COS * d):
                near += 1
                dsum += d
        out.append((L * near / k, dsum / near if near else math.inf))
    return out


def adjoining_roads(site: dict, corners: list[Point]) -> dict[str, list[list[Point]]]:
    """The named roads in `site.osm.roads` (stored in the lot frame) whose centreline comes within half the road's
    width plus ADJOIN_M of the lot outline, name -> its ways' points."""
    out: dict[str, list[list[Point]]] = {}
    n = len(corners)
    for rd in (site.get("osm") or {}).get("roads") or []:
        name, pts = rd.get("name"), [(float(p[0]), float(p[1])) for p in rd.get("points") or []]
        if not name or not pts:
            continue
        reach = float(rd.get("width_m") or 10.0) / 2 + ADJOIN_M
        d = min(_dist_seg(q, corners[i], corners[(i + 1) % n])[0] for q in pts for i in range(n))
        # a way that crosses an edge between its vertices: check the lot corners against the way as well
        d = min(d, min(_dist_polyline(c, pts)[0] for c in corners))
        if d <= reach:
            out.setdefault(name, []).append(pts)
    return out


def _face_edge(site: dict, corners: list[Point], ff: dict) -> tuple[int, Point, Point, list[Point]]:
    """The corner edge the front_face names: its index, the two ends of the face (for a street, the chord of the
    run of neighbouring edges that face it) and the corners along the face."""
    n = len(corners)
    if "edge" in ff:
        i = ff["edge"]
        if not isinstance(i, int) or isinstance(i, bool) or not 0 <= i < n:
            raise ValueError(f"front_face edge {i!r} is not an edge of the lot: it has {n} edges, numbered 0 to {n - 1} from lot.corners.")
        return i, corners[i], corners[(i + 1) % n], [corners[i], corners[(i + 1) % n]]
    if "side" in ff:
        want = SIDE_NORMALS.get(ff["side"])
        if want is None:
            raise ValueError(f"front_face side {ff['side']!r} is not one of front, rear, left, right.")
        best, best_score = 0, -math.inf
        for i in range(n):
            a, b = corners[i], corners[(i + 1) % n]
            nrm = _outward(a, b)
            dot = nrm[0] * want[0] + nrm[1] * want[1]
            score = dot * math.dist(a, b) if dot > 0.7 else dot - 10.0    # the longest edge that faces that way
            if score > best_score:
                best, best_score = i, score
        return best, corners[best], corners[(best + 1) % n], [corners[best], corners[(best + 1) % n]]
    if "street" in ff:
        roads = adjoining_roads(site, corners)
        name = str(ff["street"])
        match = next((k for k in roads if k.lower() == name.strip().lower()), None)
        if match is None:
            listed = ", ".join(sorted(roads)) or "none (fetch the context with python -m ffm context)"
            raise ValueError(f"No road named {name!r} adjoins the lot. The roads that adjoin it are: {listed}.")
        near = [0.0] * n
        for pts in roads[match]:
            for i, (m, _) in enumerate(_road_frontage(corners, pts, ADJOIN_M + 10.0)):
                near[i] = max(near[i], m)
        if max(near) <= 0:
            raise ValueError(f"{match} adjoins the lot but no lot line faces it; name the face with front_face side or edge instead.")
        best = max(range(n), key=lambda i: (round(near[i], 3), -i))
        # a street front drawn as several short edges (a kinked or gently curving property line): the run of
        # neighbouring edges that face the same road the same way is one face, and its chord the new x axis
        nb = _outward(corners[best], corners[(best + 1) % n])

        def joins(k: int) -> bool:
            nk = _outward(corners[k], corners[(k + 1) % n])
            L = math.dist(corners[k], corners[(k + 1) % n]) or 1.0
            return near[k] >= 0.5 * L and nk[0] * nb[0] + nk[1] * nb[1] > math.cos(math.radians(30))
        lo = hi = best
        while (lo - 1) % n != hi and joins((lo - 1) % n):
            lo = (lo - 1) % n
        while (hi + 1) % n != lo and joins((hi + 1) % n):
            hi = (hi + 1) % n
        run = [corners[k % n] for k in range(lo, lo + ((hi - lo) % n) + 2)]
        return best, corners[lo], corners[(hi + 1) % n], run
    raise ValueError("front_face must be {\"street\": name}, {\"side\": front|rear|left|right} or {\"edge\": index}.")


def _rot(theta_deg: float) -> tuple[float, float]:
    q = theta_deg / 90.0
    if abs(q - round(q)) < 1e-9:      # quarter turns exactly, so a rectangle stays a clean rectangle
        return [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)][int(round(q)) % 4]
    t = math.radians(theta_deg)
    return math.cos(t), math.sin(t)


def apply_orientation(o: dict, pt) -> Point:
    """new = R(θ)·old + t, R(θ) = [[cos θ, −sin θ], [sin θ, cos θ]] (θ counter-clockwise, degrees)."""
    c, s = _rot(float(o["rotate_deg"]))
    x, y = float(pt[0]), float(pt[1])
    return (c * x - s * y + float(o["tx"]), s * x + c * y + float(o["ty"]))


def unapply_orientation(o: dict, pt) -> Point:
    """The inverse of apply_orientation: old = R(−θ)·(new − t). What the boundary editor does to a ring drawn in
    the turned frame before it is kept as `site.boundary_m`, which lot_ring reads in the frame as found."""
    c, s = _rot(float(o["rotate_deg"]))
    x, y = float(pt[0]) - float(o["tx"]), float(pt[1]) - float(o["ty"])
    return (c * x + s * y, -s * x + c * y)


def oriented_ring(site: dict) -> dict[str, Any] | None:
    """The lot turned so the face `site.front_face` names is the street side, or None where the site names none
    (then everything stays in the frame `lot_ring` gives).

    front_face is one of:
        {"street": "<road name>"}   a road in site.osm.roads that adjoins the lot; the lot edge that faces it
                                    over the most length becomes the front (ValueError, listing the adjoining
                                    roads, for a name that does not adjoin)
        {"side": "front"|"rear"|"left"|"right"}   the longest edge facing that way in the current frame
        {"edge": i}                 edge i of lot.corners (corner i to corner i + 1), as massing records them

    The base is the lot ring (`lot_ring`) or, on a plain lot, the frontage x depth rectangle. The chosen face
    a -> b of the counter-clockwise ring (one edge; for a street, the chord of the run of neighbouring edges that
    face it) is turned to run along +x, so the lot lies above it (y > 0); then the ring is shifted so the face's
    outermost corner sits on y = 0 and the lot's leftmost point on x = 0 (the new front-left corner).

    The transform, stored by massing in `lot.orientation` and to be applied by the page to everything stored in
    the old lot frame (site.osm roads, buildings, trees):

        new = R(θ)·old + t,   R(θ) = [[cos θ, −sin θ], [sin θ, cos θ]],   θ = rotate_deg, counter-clockwise,
        t = (tx, ty)

    Worked example: the plain 75.6 x 37.2 m lot with front_face {"side": "right"}. The right side runs from
    (75.6, 0) to (75.6, 37.2), direction +y, so θ = −90 and R = [[0, 1], [−1, 0]]: (x, y) -> (y, −x). That
    takes (75.6, 0) to (0, −75.6) and (0, 0) to (0, 0), so t = (0, 75.6). A point on the old front street at
    (30, −10) goes to (−10 + 0, −30 + 75.6) = (−10, 45.6): it now lies off the new left side, 45.6 m in from the
    new front. The new lot is 37.2 m along the front (frontage) and 75.6 m deep.
    """
    ff = site.get("front_face")
    if not ff:
        return None
    if not isinstance(ff, dict):
        raise ValueError("front_face must be a dict: {\"street\": name}, {\"side\": ...} or {\"edge\": index}.")
    base = lot_ring(site)
    W, D = float(site.get("frontage_m") or 0), float(site.get("depth_m") or 0)
    if base:
        ring = [(float(p[0]), float(p[1])) for p in base["ring"]]
        corners = lot_corners(ring)
    else:
        if not W or not D:
            raise ValueError("Site needs frontage_m and depth_m to choose a front face.")
        ring = corners = [(0.0, 0.0), (W, 0.0), (W, D), (0.0, D)]
    i, a, b, face = _face_edge(site, corners, ff)
    theta = round(-math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])), 6)
    if theta <= -180:
        theta += 360
    theta = theta + 0.0                       # no -0.0
    c, s = _rot(theta)
    rx = [c * x - s * y for x, y in ring]
    tx = round(-min(rx), 3) + 0.0
    ty = round(-min(s * x + c * y for x, y in face), 3) + 0.0     # the face's outermost corner on y = 0
    o = {"rotate_deg": theta, "tx": tx, "ty": ty}
    new_ring = [apply_orientation(o, p) for p in ring]
    new_corners = [apply_orientation(o, p) for p in corners]
    bb = bbox(new_ring)
    r2 = lambda pts: [[round(x, 2) + 0.0, round(y, 2) + 0.0] for x, y in pts]
    return {"ring": r2(new_ring), "corners": r2(new_corners), "orientation": o, "front_face": ff, "edge": i,
            "rectangle": base is None, "frontage_m": round(bb[2] - bb[0], 2), "depth_m": round(bb[3] - bb[1], 2),
            "source": base["source"] if base else "rectangle", "frame": base["frame"] if base else "lot",
            "note": (base["note"] + "; " if base else "") + f"turned so lot edge {i} is the front (front_face {ff})"}


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
    # a corner on the lot line counts as inside (24 Nov 2026: a zero front or side yard, a street-wall building, put the
    # corners exactly on the ring, the test called them outside, and the massing fell back to an equivalent rectangle
    # larger than the lot)
    if any(not (point_in(p, pts) or _on_edge(p, pts)) for p in out):
        return None
    return [[round(x, 2), round(y, 2)] for x, y in out]


def _on_edge(p: Point, pts: list, tol: float = 0.01) -> bool:
    """Whether a point lies on one of the polygon's edges, within `tol` metres."""
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2)) if L2 else 0.0
        if math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy)) <= tol:
            return True
    return False


def largest_rect(poly: list, step: float = 0.5, exclude: dict | None = None) -> dict[str, float] | None:
    """The largest rectangle aligned with the axes inside the polygon, found on a grid of `step` metres (the
    answer is good to about a step on each side). None for a polygon too small for one cell. `exclude` {x, y, w, d}:
    a rectangle the answer may not overlap (the plate box, when a second one is looked for beside it)."""
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
        if exclude:
            ry0, ry1 = y0 + r * step, y0 + (r + 1) * step
            if ry1 > exclude["y"] + 1e-6 and ry0 < exclude["y"] + exclude["d"] - 1e-6:
                inside = [inside[c] and not (x0 + (c + 1) * step > exclude["x"] + 1e-6 and x0 + c * step < exclude["x"] + exclude["w"] - 1e-6) for c in range(cols)]
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
    x, y, w, d = _grow(pts, x0 + c * step, y0 + r * step, w * step, hgt * step, step, exclude)
    return {"x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "d": round(d, 2), "area_m2": round(w * d, 1)}


def _rect_in(pts: list, x: float, y: float, w: float, d: float, exclude: dict | None) -> bool:
    """The rectangle stands inside the polygon: its edges, read every 0.25 m a hair inside, are inside, no vertex of the
    polygon is inside it, and it does not overlap `exclude`. Pure."""
    if exclude and x < exclude["x"] + exclude["w"] - 1e-6 and x + w > exclude["x"] + 1e-6 and y < exclude["y"] + exclude["d"] - 1e-6 and y + d > exclude["y"] + 1e-6:
        return False
    e = 1e-4
    nw, nd = max(2, int(w / 0.25) + 2), max(2, int(d / 0.25) + 2)
    xs = [x + e + (w - 2 * e) * i / (nw - 1) for i in range(nw)]
    ys = [y + e + (d - 2 * e) * j / (nd - 1) for j in range(nd)]
    edge = [(a, y + e) for a in xs] + [(a, y + d - e) for a in xs] + [(x + e, b) for b in ys] + [(x + w - e, b) for b in ys]
    if not all(point_in(p, pts) for p in edge):
        return False
    return not any(x + e < px < x + w - e and y + e < py < y + d - e for px, py in pts)


def _grow(pts: list, x: float, y: float, w: float, d: float, step: float, exclude: dict | None) -> tuple[float, float, float, float]:
    """The grid's answer pushed out to the polygon (25 Nov 2026, the small-lot architect: the plate box was 11.5 × 17 m
    where the yards leave 12.2 × 17.4): each side moves out by up to a step, as far as the rectangle stays inside,
    found by halving to a few millimetres. Twice round, since one side's room can depend on another's. Pure."""
    for _ in range(2):
        for side in ("left", "right", "front", "rear"):
            lo, hi = 0.0, step
            for _ in range(7):
                mid = (lo + hi) / 2
                cand = {"left": (x - mid, y, w + mid, d), "right": (x, y, w + mid, d),
                        "front": (x, y - mid, w, d + mid), "rear": (x, y, w, d + mid)}[side]
                if _rect_in(pts, *cand, exclude):
                    lo = mid
                else:
                    hi = mid
            if lo > 0:
                x, y, w, d = {"left": (x - lo, y, w + lo, d), "right": (x, y, w + lo, d),
                              "front": (x, y - lo, w, d + lo), "rear": (x, y, w, d + lo)}[side]
    return x, y, w, d


WING_MIN_SIDE_M = 9.8      # the shallowest wing homes are laid out in (a single-loaded corridor and one strip)
WING_MIN_AREA_M2 = 150.0   # a smaller leftover is not worth a second core
WING_MIN_JOINT_M = 3.0     # the wing meets the main plate along at least this much of a wall


def wing_rect(poly: list, box: dict, step: float = 0.5) -> dict[str, Any] | None:
    """A second rectangle inside the polygon beside the plate box: the largest one that does not overlap it, where it
    is big enough to hold homes and meets the box along a wall (23 Nov 2026: a plate was one rectangle, and on an L
    or a wedge of a lot the rest of the envelope stood empty). Returns {x, y, w, d, area_m2, joins} with `joins` the
    side of the box it stands on ("left", "right", "front", "rear"), or None."""
    r = largest_rect(poly, step, exclude=box)
    if not r or r["area_m2"] < WING_MIN_AREA_M2 or min(r["w"], r["d"]) < WING_MIN_SIDE_M:
        return None
    tol = step + 0.01
    over_y = min(r["y"] + r["d"], box["y"] + box["d"]) - max(r["y"], box["y"])
    over_x = min(r["x"] + r["w"], box["x"] + box["w"]) - max(r["x"], box["x"])
    if abs(r["x"] - (box["x"] + box["w"])) <= tol and over_y >= WING_MIN_JOINT_M:
        return {**r, "x": box["x"] + box["w"], "joins": "right"}       # closed up to the box where the grid left a step
    if abs(r["x"] + r["w"] - box["x"]) <= tol and over_y >= WING_MIN_JOINT_M:
        return {**r, "x": box["x"] - r["w"], "joins": "left"}
    if abs(r["y"] - (box["y"] + box["d"])) <= tol and over_x >= WING_MIN_JOINT_M:
        return {**r, "y": box["y"] + box["d"], "joins": "rear"}
    if abs(r["y"] + r["d"] - box["y"]) <= tol and over_x >= WING_MIN_JOINT_M:
        return {**r, "y": box["y"] - r["d"], "joins": "front"}
    return None


def rects_outline(rects: list[dict]) -> list[list[float]]:
    """The outline of rectangles that touch, as one ring (counter-clockwise from its lowest, then leftmost corner):
    an L, a T or a step. The rectangles are cut on each other's edges into cells, and the edges with a cell on one
    side only are chained. Pure; for two or three rectangles that meet along walls."""
    xs = sorted({round(v, 3) for r in rects for v in (r["x"], r["x"] + r["w"])})
    ys = sorted({round(v, 3) for r in rects for v in (r["y"], r["y"] + r["d"])})
    full = lambda i, j: 0 <= i < len(xs) - 1 and 0 <= j < len(ys) - 1 and any(
        r["x"] - 1e-6 <= xs[i] and xs[i + 1] <= r["x"] + r["w"] + 1e-6 and r["y"] - 1e-6 <= ys[j] and ys[j + 1] <= r["y"] + r["d"] + 1e-6 for r in rects)
    nxt: dict[tuple[float, float], tuple[float, float]] = {}
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            if not full(i, j):
                continue
            if not full(i, j - 1):
                nxt[(xs[i], ys[j])] = (xs[i + 1], ys[j])                 # along the bottom, going right
            if not full(i + 1, j):
                nxt[(xs[i + 1], ys[j])] = (xs[i + 1], ys[j + 1])         # up the right side
            if not full(i, j + 1):
                nxt[(xs[i + 1], ys[j + 1])] = (xs[i], ys[j + 1])         # along the top, going left
            if not full(i - 1, j):
                nxt[(xs[i], ys[j + 1])] = (xs[i], ys[j])                 # down the left side
    if not nxt:
        return []
    start = min(nxt, key=lambda p: (p[1], p[0]))
    ring, at = [start], nxt[start]
    while at != start and len(ring) <= len(nxt):
        ring.append(at)
        at = nxt[at]
    # drop the points that lie on a straight wall
    out = [p for k, p in enumerate(ring) if not ((ring[k - 1][0] == p[0] == ring[(k + 1) % len(ring)][0]) or (ring[k - 1][1] == p[1] == ring[(k + 1) % len(ring)][1]))]
    return [[round(x, 2), round(y, 2)] for x, y in out]


TURN_MIN_DEG = 2.0     # a longest edge this close to the frontage's direction is not worth turning to
TURN_GAIN = 1.10       # a turned plate box is taken only where it is at least this much larger


def rotate_pt(pt, deg: float) -> Point:
    """A point turned counter-clockwise about the origin (the same turn massing._turn makes about a centre)."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (pt[0] * c - pt[1] * s, pt[0] * s + pt[1] * c)


def turned_rect(poly: list, step: float = 0.5) -> dict[str, float] | None:
    """The plate box, tried twice: square to the frontage (`largest_rect`), and square to the polygon's longest edge
    (23 Nov 2026, from an architect's test: on a lot whose long sides run at an angle to its front, 2001 Stainsbury Ave
    read from Victoria Drive, the box square to the front was a third of the one along the lot line). The turned box
    is taken where it is at least 10% larger. Returns the box with `angle_deg`: 0, or the turn; a turned box's x, y,
    w, d are in the frame turned by minus that angle about the origin, and `rotate_pt(centre, angle_deg)` brings its
    centre back to the lot's frame."""
    base = largest_rect(poly, step)
    pts = _open(poly)
    if len(pts) < 3:
        return base
    n = len(pts)
    a, b = max(((pts[i], pts[(i + 1) % n]) for i in range(n)), key=lambda e: math.dist(e[0], e[1]))
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 90.0
    if ang > 45.0:
        ang -= 90.0
    if abs(ang) < TURN_MIN_DEG:
        return {**base, "angle_deg": 0.0} if base else None
    turned = largest_rect([list(rotate_pt(p, -ang)) for p in pts], step)
    if turned and (not base or turned["area_m2"] >= TURN_GAIN * base["area_m2"]):
        return {**turned, "angle_deg": round(ang, 2)}
    return {**base, "angle_deg": 0.0} if base else None


def shape_summary(ring: list) -> dict[str, Any] | None:
    """What shape the lot is, from ffm.parcel_shapes, reduced to what a reader needs."""
    try:
        from .parcel_shapes import classify
        c = classify([[list(p) for p in ring]], units="m")
    except (ValueError, ImportError):
        return None
    return {"class": c["class"], "note": c["note"], "rectangularity": round(c["rectangularity"], 3),
            "vertices": c["vertices"], "confidence": round(c["confidence"], 2), "alternative": c["alternative"]}
