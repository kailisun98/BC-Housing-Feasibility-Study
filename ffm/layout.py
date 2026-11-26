"""The architect's first layout, derived from the option: program blocks, adjacency rules in plain words, and a
stacking solver that places the blocks on the massing's floor plates; then the drawings a board reads.

    blocks(option, ledger)                  the program as blocks with areas, every figure saying where it came from
    ADJACENCIES                             the default rules, in plain words; option["layout"]["adjacencies"] overrides
    solve(site, option, ledger, massing)    the stacking: floors, zones, what did not fit, which rules hold
    svg_stacking / svg_plans / svg_elevations / svg_axon / svg_site_plan   the sheets, to scale, with the numbers
    write(layout, out_dir)                  layout.json and the five SVGs beside the ledger

Deterministic, standard library only, no model: the same option, massing and rules give the same layout. It is
a feasibility layout, not a design: a double-loaded corridor on each residential floor, a core bay at the plate's
centre, units as rectangles of their minimum net area plus a declared partition allowance, the non-residential
space on the ground floor facing the street, services on the lane side. What does not fit is listed, never
squeezed; what the rules cannot settle is flagged.

Coordinates as in massing.json: metres, origin at the front-left lot corner, x along the frontage, y into the lot
(the street is y = 0), z up.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .massing import MIDRISE_MAX_STOREYS, date_words
from .suggest import ASSUMPTIONS

# Declared placeholders of the layout, not rules: a person can change them and the memo says they were used.
LAYOUT_ASSUMPTIONS = {
    "partition_allowance": (1.08, "gross unit area over net: walls and the entry, 8% at this stage (the net areas already carry the suggestion's 10% design allowance)"),
    "corridor_width_m": (1.8, "a double-loaded corridor, the wider of the two usual widths"),
    "core_bay_m": (7.0, "one bay across the plate at its centre for two stairs, the elevator and risers"),
    "services_base_m2": (40.0, "mechanical, electrical, garbage and recycling on the ground floor"),
    "bicycle_m2_per_space": (1.0, "a bicycle space with its aisle share"),
    "amenity_m2_per_unit": (1.5, "indoor amenity, at least 40 m²; a placeholder until the operator's brief"),
    "parking_m2_per_space": (30.0, "a below-grade stall with its aisle share; not on the plates"),
    "window_width_m": (1.5, "one window per unit on the elevation, the unit module as the rhythm"),
    "stair_width_m": (2.2, "one exit stair's width along the core; a core at least one core bay wide holds two stairs at its ends"),
    "min_home_depth_m": (4.0, "the shallowest strip a point tower lays homes in, round its ringed core; a home this shallow runs long along the facade"),
    "max_home_depth_m": (12.0, "the deepest a home runs back from its window wall before the back of it has no daylight; a placeholder, and the reason a deep plate takes its corridor the other way or wants a courtyard"),
    "lobby_m2": (25.0, "an entry lobby on the street side of the ground floor, where the building is entered; a placeholder until the architect draws the entry"),
    "min_room_width_m": (2.0, "a leftover of a ground-floor room narrower than this along the strip is not drawn: the room is that much smaller and the notes say so"),
}

# A walk-up (20 Nov 2026, on 609 Heatley Ave: a 9.4 × 12 m plate of three storeys placed no homes, its 7 m core bay and
# 1.8 m corridor leaving no strip a home fits in). A building of at most three storeys on a plate of at most 600 m², the
# Part 9 limits in `bc.code_basis` (part9_max_storeys, part9_max_building_area_m2), is also laid out with one stair and
# no elevator, every home opening off the stair's landing, and the arrangement that places more homes is kept.
WALKUP_MAX_STOREYS = 3          # bc.code_basis: part9_max_storeys
WALKUP_MAX_PLATE_M2 = 600.0     # bc.code_basis: part9_max_building_area_m2
WALKUP_MAX_DEPTH_M = 16.0       # the homes run the plate's full depth; a deeper plate is the corridor plan's
WALKUP_ASSUMPTIONS = {
    "walkup_stair_m": ([2.6, 5.5], "a walk-up's one exit stair with its half landings, no elevator: about 2.6 m wide and 5.5 m long, on the street side of the plate"),
    "walkup_landing_m": (1.2, "the floor landing behind the stair, which every home's door opens onto"),
    "walkup_services_m2": (10.0, "garbage, recycling and meters in a walk-up, plus the bicycle spaces; no indoor amenity room in a building this small"),
    "walkup_one_exit": (True, "one exit stair is taken to serve a floor of at most 150 m² with an occupant load of at most 60 (bcbc.exits, BCBC 3.4.2.1, "
                              "a Part 3 clause); Part 9's own exit clauses (9.9.8) are not in the rules, so whether one exit serves the floor is a placeholder to confirm against the code"),
}

# Whether the floor areas are sprinklered: a Part 3 residential building over three storeys is sprinklered in
# practice, so the egress check assumes it; `option.sprinklered: false` switches the unsprinklered limits on.
SPRINKLERED_DEFAULT = True

UNIT_KEYS = ("three_bed_plus", "two_bed", "one_bed", "studio")   # the order they are placed, bottom up

# Declared placeholders, not rules, for a home's proportions (23 Nov 2026, Kai's figures to change): the least width
# along its window wall by type, and how many times as deep as it is wide a home may be. The solver sizes homes to
# them; a home drawn by hand under them is counted and said (`proportions`), never a failure.
UNIT_MIN_WIDTH_M = {"studio": 4.0, "one_bed": 5.5, "two_bed": 7.5, "three_bed_plus": 9.5}
UNIT_DEPTH_RATIO_MAX = 2.5
UNIT_LABEL = {"studio": "Studio", "one_bed": "One-bedroom", "two_bed": "Two-bedroom", "three_bed_plus": "Three-bedroom+"}

# The default adjacency rules, in plain words. Each names a block and what the solver does with it; the check
# reads the placed zones back and says whether the rule held.
ADJACENCIES = [
    {"id": "non_residential_street", "block": "non_residential", "rule": "on the ground floor, facing the street"},
    {"id": "amenity_entry", "block": "amenity", "rule": "on the ground floor, next to the entry"},
    {"id": "services_lane", "block": "services", "rule": "on the ground floor, away from the street"},
    {"id": "core_centre", "block": "core", "rule": "at the centre of every floor, the corridor through it"},
    {"id": "units_both_sides", "block": "units", "rule": "on both sides of the corridor, above whatever the ground floor gives to other uses"},
    {"id": "family_low", "block": "three_bed_plus", "rule": "from the lowest residential floor up, stacked in the same bays"},
    {"id": "accessible_core", "block": "accessible", "rule": "next to the core, on the lowest residential floor"},
]

# Drawing tones: the unit sizes in steps of the envelope blue, the common spaces in the paper greys, amenity and
# non-residential in the amber of a note; ink and muted as the massing drawing.
TONES = {
    "paper": "#ffffff", "ink": "#1f2933", "muted": "#5f6672", "rule": "#e1e5ea", "lot": "#f4f4f2",
    "studio": "#dbe9f8", "one_bed": "#b9d4f0", "two_bed": "#8fb8e3", "three_bed_plus": "#6b9fd4",
    "corridor": "#f4f4f2", "core": "#c9c9c5", "services": "#e2e2df", "amenity": "#f6e7c1", "non_residential": "#f0cf9a",
    "spare": "#ffffff", "envelope": "#c81e1e", "outright": "#8e8e8e", "benchmark": "#c77d14", "benchmark_text": "#8f5a0e", "tree": "#9fb07f", "tree_line": "#7f9664",
    "accessible": "#245f9c", "other": "#e6dfd0",
    # the architect's own blocks (17 Nov 2026): design space (a lobby, an atrium), commercial space, and a cut-out
    # (open to below, a notch, a courtyard: not floor area), which is how a plate takes a shape other than a rectangle
    "design_space": "#d9e6d2", "commercial": "#f3c9b5", "void": "#ffffff",
}
BLOCK_LABEL = {"corridor": "Corridor", "core": "Core (stairs, elevator)", "services": "Services, bicycles", "amenity": "Amenity", "non_residential": "Non-residential", "spare": "Spare",
               "design_space": "Design space", "commercial": "Commercial", "void": "Cut-out", **UNIT_LABEL}


def _find(results: list[dict], check: str | None = None, rule_id: str | None = None) -> dict | None:
    for r in results:
        if (rule_id and r["rule_id"] == rule_id) or (check and r.get("check") == check and r["status"] != "not_applicable"):
            return r
    return None


# ---------------------------------------------------------------- the program as blocks

def blocks(option: dict, ledger: dict) -> dict[str, Any]:
    """Every block with its area and where the area came from: the unit counts from the option, the net areas from
    layer D (BC Housing minimums, plus the suggestion's design allowance), the rest declared placeholders."""
    results = ledger["results"]
    areas_rule = _find(results, rule_id="bch.design_guidelines.unit_areas")
    mins = (areas_rule or {}).get("values", {}).get("min_net_area_m2") or {"studio": 33, "one_bed": 49, "two_bed": 67, "three_bed_plus": 86}
    allowance, _ = ASSUMPTIONS["design_allowance"]
    # the architect's own unit sizes (23 Nov 2026: a built scheme of 103 homes placed 58 at "the minimum + 10%"): a
    # factor on the BC Housing areas, 1.00 for the areas as published, kept between 0.8 and 1.5; blank is the 10%
    own = option.get("unit_area_allowance")
    if isinstance(own, (int, float)) and not isinstance(own, bool) and 0.8 <= float(own) <= 1.5:
        allowance = float(own)
    partition, _ = LAYOUT_ASSUMPTIONS["partition_allowance"]
    units = option.get("units") or {}
    out: list[dict] = []
    n_total = 0
    for k in UNIT_KEYS:
        n = int(units.get(k) or 0)
        if not n:
            continue
        n_total += n
        net = round(float(mins[k]) * allowance, 1)
        gross = round(net * partition, 1)
        out.append({"key": k, "label": UNIT_LABEL[k], "count": n, "net_m2_each": net, "gross_m2_each": gross, "min_gross_m2_each": round(float(mins[k]) * partition, 1), "min_width_m": UNIT_MIN_WIDTH_M[k], "area_m2": round(gross * n, 1),
                    "source": (areas_rule or {}).get("rule_id") or "placeholder", "note": f"{n} × {net} m² net ({mins[k]} m² minimum + {int((allowance - 1) * 100)}%), {gross} m² gross with partitions"})
    nonres = float(option.get("non_residential_gfa_m2") or 0)
    if nonres:
        out.append({"key": "non_residential", "label": "Non-residential", "count": 1, "area_m2": round(nonres, 1), "source": "option.non_residential_gfa_m2", "note": "the option's non-residential floor area (childcare, a hall, shops)"})
    amen_per, _ = LAYOUT_ASSUMPTIONS["amenity_m2_per_unit"]
    brief = program_brief(option)
    amenity = round(max(40.0, amen_per * n_total), 1) if n_total and not any(b["replaces_amenity"] for b in brief) else 0.0
    if amenity:
        out.append({"key": "amenity", "label": "Amenity", "count": 1, "area_m2": amenity, "source": "placeholder", "note": f"{amen_per} m² per unit, at least 40 m²"})
    serv_base, _ = LAYOUT_ASSUMPTIONS["services_base_m2"]
    bike_each, _ = LAYOUT_ASSUMPTIONS["bicycle_m2_per_space"]
    bikes = int(option.get("bicycle_spaces") or 0)
    services = round(serv_base + bikes * bike_each, 1)
    out.append({"key": "services", "label": "Services, bicycles", "count": 1, "area_m2": services, "source": "placeholder", "note": f"{serv_base:.0f} m² services + {bikes} bicycle spaces × {bike_each} m²"})
    # programs the architect added in the block editor (option.layout.extra_programs: [{label, area_m2}]), each a
    # block of its own kind "other" told apart by its label (16 Nov 2026)
    for ex in ((option.get("layout") or {}).get("extra_programs") or []):
        try:
            label, area = str(ex.get("label") or "").strip(), float(ex.get("area_m2") or 0)
        except (TypeError, ValueError, AttributeError):
            continue
        if label and area > 0:
            out.append({"key": "other", "label": label, "count": 1, "area_m2": round(area, 1), "source": "option.layout.extra_programs", "note": "a program the architect added in the block editor"})
    # the program brief (the operator's, or the housing type's default): named blocks of kind "other", with where they go
    for b in brief:
        out.append({"key": "other", "label": b["label"], "count": 1, "area_m2": b["area_m2"], "source": b["source"], "brief": True,
                    "next_to": b["next_to"], "where": b["where"], "note": b["note"] or ("the program brief" if b["source"] != "placeholder" else "the housing type's default brief, a placeholder")})
    park_each, _ = LAYOUT_ASSUMPTIONS["parking_m2_per_space"]
    stalls = int(option.get("parking_spaces") or 0)
    parking = {"spaces": stalls, "area_m2": round(stalls * park_each, 1), "where": "below grade, not on the plates", "source": "placeholder" if stalls else None}
    return {"blocks": out, "units_total": n_total, "parking": parking,
            "assumptions": [{"key": k, "value": v, "note": n} for k, (v, n) in LAYOUT_ASSUMPTIONS.items()]}


# ---------------------------------------------------------------- the solver

def adjacencies_for(option: dict) -> list[dict]:
    """The rules in force: the defaults, with the option's own `layout.adjacencies` replacing any by id or adding."""
    rules = [dict(r) for r in ADJACENCIES]
    for r in ((option.get("layout") or {}).get("adjacencies") or []):
        if not isinstance(r, dict) or not r.get("id"):
            continue
        hit = next((x for x in rules if x["id"] == r["id"]), None)
        if hit:
            hit.update(r)
        else:
            rules.append(dict(r))
    return rules


def grid_of(option: dict) -> dict | None:
    """The structural grid the architect chose in the block editor (`option.layout.grid`: {bay_m, divide}): the
    bay is the wall-to-wall width (6 m, 8 m), `divide` how many modules a bay holds (1 a whole bay, 2 half bays,
    4 quarters); the blocks' walls sit on the module, counted from the plate's left edge. None without one."""
    g = (option.get("layout") or {}).get("grid")
    if not isinstance(g, dict):
        return None
    try:
        bay = float(g.get("bay_m") or 0)
        divide = int(g.get("divide") or 2)
    except (TypeError, ValueError):
        return None
    if not 2.0 <= bay <= 12.0 or divide not in (1, 2, 4):
        return None
    return {"bay_m": round(bay, 2), "divide": divide, "module_m": round(bay / divide, 3)}


def _cores_of(option: dict, x0: float, y0: float, W: float, D: float) -> list[dict]:
    """The cores the architect placed (`option.layout.cores`: [{x, y, w, d}]), kept inside the plate: the stairs
    do not shift from level to level, so the solver stands them on every floor and lays the program round them."""
    out: list[dict] = []
    for c in ((option.get("layout") or {}).get("cores") or []):
        try:
            x, y, w, d = (float(c.get(k)) for k in ("x", "y", "w", "d"))
        except (TypeError, ValueError, AttributeError):
            continue
        x, y = max(x0, min(x, x0 + W)), max(y0, min(y, y0 + D))
        w, d = min(w, x0 + W - x), min(d, y0 + D - y)
        if w > 0.5 and d > 0.5:
            out.append({"x": x, "y": y, "w": w, "d": d})
    return sorted(out, key=lambda c: (c["x"], c["y"]))


def _plate(massing: dict) -> tuple[dict, float, float, float, float, int, float]:
    pm = next((x for x in massing["masses"] if x["name"] == "proposed"), None)
    if pm is None:
        raise ValueError("The massing has no proposed mass to lay out.")
    # a turned mass (`angle_deg`) keeps its plate in its own frame: the front-left corner before the turn
    ring = [pm["plate_origin"]] if pm.get("plate_origin") else pm["footprint"]
    # a plate is never negative (a massing.json from before 16 Nov 2026 can carry one where the yards exceeded the lot)
    return pm, float(ring[0][0]), float(ring[0][1]), max(0.0, float(pm["plate_width_m"])), max(0.0, float(pm["plate_depth_m"])), int(pm["storeys"]), float(pm["floor_to_floor_m"])


# A point tower's plate: no longer than this many times its width (a longer one reads as a slab, its corridor through
# it), and every strip of homes round the ring at least MIN_HOME_DEPTH_M deep.
POINT_ASPECT_MAX = 1.4


def _point_geometry(option: dict, massing: dict) -> dict | None:
    """A compact tower plate laid out as a point tower (17 Nov 2026): a core at the centre (a scissor stair, the
    elevators and the risers, `core_bay_m` square), a corridor ringing it, and the homes round that on all four
    sides, the street and lane strips taking the corners. Only above six storeys (the scissor stair: none in a 5 or 6
    storey wood-frame building, VBBL 2014 3.4.1.2.(3)), without a grid or cores the architect placed, on a plate no
    longer than POINT_ASPECT_MAX times its width with every strip at least `min_home_depth_m` deep. None otherwise.
    Pure."""
    pm, x0, y0, W, D, storeys, f2f = _plate(massing)
    if storeys <= MIDRISE_MAX_STOREYS or grid_of(option) is not None or _cores_of(option, x0, y0, W, D):
        return None
    if min(W, D) <= 0 or max(W, D) / min(W, D) > POINT_ASPECT_MAX + 1e-9:
        return None
    corr, _ = LAYOUT_ASSUMPTIONS["corridor_width_m"]
    cw = cd = LAYOUT_ASSUMPTIONS["core_bay_m"][0]
    iw, idp = cw + 2 * corr, cd + 2 * corr                 # the core and its ring
    ux, uy = (W - iw) / 2, (D - idp) / 2                   # the homes' depth beside it, and in front and behind
    if min(ux, uy) < LAYOUT_ASSUMPTIONS["min_home_depth_m"][0] - 1e-9:
        return None
    ix0, iy0 = x0 + ux, y0 + uy
    r2 = lambda v: round(v, 2)
    seg = lambda x, y, w, d: {"block": "corridor", "label": "Corridor", "x": r2(x), "y": r2(y), "w": r2(w), "d": r2(d), "area_m2": round(w * d, 1), "through": "core"}
    core = {"block": "core", "label": BLOCK_LABEL["core"], "x": r2(ix0 + corr), "y": r2(iy0 + corr), "w": cw, "d": cd, "area_m2": round(cw * cd, 1), "stairs": "scissor"}
    ring = [seg(ix0, iy0, iw, corr), seg(ix0, iy0 + idp - corr, iw, corr),                # in front of it and behind it
            seg(ix0, iy0 + corr, corr, cd), seg(ix0 + iw - corr, iy0 + corr, corr, cd)]   # beside it
    run = lambda side, end, axis, edge, at, depth, length: {"side": side, "end": end, "axis": axis, "edge": edge, "dir": 1, "at": at, "depth": depth, "len": length, "left": length}
    runs = [run("front", "left", "x", x0, y0, uy, W), run("rear", "left", "x", x0, y0 + D - uy, uy, W),
            run("left", "mid", "y", y0 + uy, x0, ux, D - 2 * uy), run("right", "mid", "y", y0 + uy, x0 + W - ux, ux, D - 2 * uy)]
    return {"core": core, "ring": ring, "runs": runs, "ux": ux, "uy": uy, "core_m": [cw, cd]}


def walkup_program(option: dict, prog: dict) -> dict:
    """A walk-up's program: the blocks less the indoor amenity room, the services at `walkup_services_m2` plus the
    bicycle spaces, and the walk-up's assumptions listed. Pure."""
    serv_m2, _ = WALKUP_ASSUMPTIONS["walkup_services_m2"]
    bike_each, _ = LAYOUT_ASSUMPTIONS["bicycle_m2_per_space"]
    bikes = int(option.get("bicycle_spaces") or 0)
    blocks_wu = []
    for b in prog["blocks"]:
        if b["key"] == "amenity":
            continue
        if b["key"] == "services":
            b = dict(b, area_m2=round(serv_m2 + bikes * bike_each, 1), note=f"{serv_m2:.0f} m² services in a walk-up + {bikes} bicycle spaces × {bike_each} m²")
        blocks_wu.append(b)
    return dict(prog, blocks=blocks_wu, assumptions=prog["assumptions"] + [{"key": k, "value": v, "note": n} for k, (v, n) in WALKUP_ASSUMPTIONS.items()])


def _walkup_geometries(option: dict, massing: dict, prog: dict, one_exit_m2: float = 150.0) -> list[dict]:
    """A low building's plate laid out as a walk-up (20 Nov 2026): one stair on the street side (`walkup_stair_m`), its
    landing behind it, and every home the plate's full depth with its door on the landing, so no corridor. Two
    arrangements, the stair standing in the same place on every floor: `either_side`, the stair at the middle of the
    frontage and one home each side of it; `one_end`, the stair at the left end and one home a floor beside it (a
    narrow plate's larger homes). Behind the landing, the ground floor's services. The program drops the indoor amenity
    room and takes `walkup_services_m2`, declared. Only at most WALKUP_MAX_STOREYS storeys on a plate of at most
    WALKUP_MAX_PLATE_M2 and WALKUP_MAX_DEPTH_M deep, and no larger than the floor area one exit may serve
    (`one_exit_m2`, bcbc.exits' two_exits_over_floor_area_m2): a larger floor needs two stairs, which is the corridor
    plan's. Without a grid or cores the architect placed. Pure."""
    pm, x0, y0, W, D, storeys, f2f = _plate(massing)
    if (storeys > WALKUP_MAX_STOREYS or W * D > min(WALKUP_MAX_PLATE_M2, one_exit_m2) + 1e-6 or D > WALKUP_MAX_DEPTH_M + 1e-6
            or grid_of(option) is not None or _cores_of(option, x0, y0, W, D)):
        return []
    (sw, sl), _ = WALKUP_ASSUMPTIONS["walkup_stair_m"]
    land, _ = WALKUP_ASSUMPTIONS["walkup_landing_m"]
    col = sl + land
    units = [b for b in prog["blocks"] if b["key"] in UNIT_KEYS]
    if not units or D < col + 0.5 or W < sw + 2.0:
        return []
    wprog = walkup_program(option, prog)
    r2 = lambda v: round(v, 2)
    out = []
    for layout, cx in (("either_side", x0 + (W - sw) / 2), ("one_end", x0)):
        stair = {"block": "core", "label": "Stair", "x": r2(cx), "y": r2(y0), "w": sw, "d": sl, "area_m2": round(sw * sl, 1), "stairs": "single"}
        landing = {"block": "corridor", "label": "Landing", "x": r2(cx), "y": r2(y0 + sl), "w": sw, "d": land, "area_m2": round(sw * land, 1), "through": "core"}
        run = lambda side, end, edge, d, at, depth, length, most=None: {"side": side, "end": end, "axis": "x", "edge": edge, "dir": d, "at": at, "depth": depth,
                                                                         "len": length, "left": length, **({"max_units": most} if most else {})}
        runs = []
        if layout == "either_side":
            runs += [run("front", "left", cx, -1, y0, D, cx - x0, 1), run("front", "right", cx + sw, 1, y0, D, x0 + W - cx - sw, 1)]
        else:
            runs.append(run("front", "right", cx + sw, 1, y0, D, W - sw, 1))
        if D - col > 0.5:
            runs.append(run("rear", "mid", cx, 1, y0 + col, D - col, sw))
        out.append({"kind": "walkup", "layout": layout, "zones": [stair, landing], "runs": runs, "prog": wprog, "stair_m": [sw, sl],
                    "homes_per_floor": 2 if layout == "either_side" else 1})
    return out


def ground_extra(option: dict, f2f: float) -> float:
    """How much taller the ground floor is than the floors above (`option.ground_floor_height_m`, 23 Nov 2026: a 4.5 m
    shop floor was drawn at the 3.3 m of the floors over it). 0 where none is given, or where it is not taller; a
    ground floor of 2.8 to 8 m is taken, anything else ignored."""
    try:
        g = float((option or {}).get("ground_floor_height_m") or 0)
    except (TypeError, ValueError):
        return 0.0
    return round(g - f2f, 2) if 2.8 <= g <= 8.0 and g > f2f + 0.01 else 0.0


def _floor_z(option: dict, lv: int, f2f: float) -> float:
    """A floor's height above the ground floor: the storeys under it, the ground floor at its own height."""
    return round(lv * f2f + (ground_extra(option, f2f) if lv >= 1 else 0.0), 2)


def _run_rect(r: dict, length: float) -> tuple[float, float, float, float]:
    """The rectangle the next `length` of a run takes, from where it is filled to, in its direction: along x a strip
    of the run's depth, along y (a point tower's sides) the same turned. Pure."""
    s = r["edge"] + r["dir"] * (r["len"] - r["left"] - r.get("far", 0.0)) + (0 if r["dir"] > 0 else -length)
    return (s, r["at"], length, r["depth"]) if r["axis"] == "x" else (r["at"], s, r["depth"], length)


def _far_rect(r: dict, length: float) -> tuple[float, float, float, float]:
    """The rectangle `length` of a run takes at its far end, the end it is filled toward (a corridor run across the
    plate puts the street's rooms at the street end of a strip, which a run filled from the core reaches last)."""
    off = r["len"] - r.get("far", 0.0) - length
    s = r["edge"] + r["dir"] * off + (0 if r["dir"] > 0 else -length)
    return (s, r["at"], length, r["depth"]) if r["axis"] == "x" else (r["at"], s, r["depth"], length)


def _t(z: dict) -> dict:
    """A zone with its x and y swapped: the plan as it reads with the plate turned a quarter (see `_solve`, `across`)."""
    return {**z, "x": z["y"], "y": z["x"], "w": z["d"], "d": z["w"]}


# ---------------------------------------------------------------- building types, the program brief, lifts (24 Nov 2026)

# What kind of building the option is (`option.building_type`). A second simulated panel found every option laid out as
# one double-loaded apartment slab: a sixplex got a lift core and a corridor, a tower a 21 m-deep bar, a supportive
# building no desk or staff room. "apartment" is the solver as it was; the other two are laid out by their own rules.
BUILDING_TYPES = ("apartment", "ground_oriented", "tower")
BUILDING_TYPE_WORDS = {"apartment": "an apartment building (homes off a corridor and a core)",
                       "ground_oriented": "ground-oriented homes (townhouses, a multiplex, stacked townhouses: each home its own door, no corridor or lift)",
                       "tower": "a tower (a podium and a tower plate over it, one core with a scissor stair and the lifts)"}

# Declared placeholders for the two new types and the lifts, not rules.
TYPOLOGY_ASSUMPTIONS = {
    "go_row_depth_m": (11.0, "a ground-oriented home's depth from its front wall to its back wall; a deeper plate takes a second row behind a courtyard"),
    "go_row_min_m": (7.5, "the shallowest row of ground-oriented homes; under it there is no second row"),
    "go_courtyard_m": (6.0, "the courtyard between a front and a rear building, which both rows' homes face"),
    "go_min_width_m": (4.2, "the narrowest a ground-oriented home is laid out, its stair included"),
    "go_amenity_homes": (12, "below this many ground-oriented homes no indoor amenity room is laid out, each home has its own outdoor space"),
    "go_services_m2": (10.0, "garbage, recycling and meters for ground-oriented homes, plus the bicycle spaces"),
    "tower_plate_m2": (650.0, "a tower's floor plate, within the 550 to 750 m² a single core with a scissor stair serves well"),
    "lift_homes_each": (70, "homes one elevator serves at this stage; BC Housing's guidelines ask for an elevator analysis, which this stands in for"),
    "lift_min_over_six": (2, "elevators in a building over six storeys at the least, so one can be out of service"),
}


def building_type(option: dict) -> str:
    """The option's building type, "apartment" where none is given or the word is not one of BUILDING_TYPES."""
    t = str((option or {}).get("building_type") or "").strip().lower()
    return t if t in BUILDING_TYPES else "apartment"


def lifts_needed(homes: int, storeys: int, ground_oriented: bool = False) -> dict[str, Any]:
    """The elevators a building of this many homes and storeys wants, a declared placeholder (24 Nov 2026: an operator's
    review asked for lifts by home count; the layout drew one whatever the homes). None for ground-oriented homes or a
    walk-up of at most three storeys (Part 9), one per `lift_homes_each` homes above that, at least two over six storeys."""
    each, _ = TYPOLOGY_ASSUMPTIONS["lift_homes_each"]
    floor_two, _ = TYPOLOGY_ASSUMPTIONS["lift_min_over_six"]
    if ground_oriented or storeys <= WALKUP_MAX_STOREYS or not homes:
        return {"lifts": 0, "words": "no elevator: " + ("each home has its own door at grade" if ground_oriented else f"{storeys} storeys or fewer, a walk-up")}
    n = max(1, math.ceil(homes / each))
    if storeys > MIDRISE_MAX_STOREYS:
        n = max(n, floor_two)
    return {"lifts": n, "words": f"{n} elevator{'s' if n != 1 else ''} for {homes} homes on {storeys} storeys: one per {each} homes"
                                 + (f", at least {floor_two} over {MIDRISE_MAX_STOREYS} storeys" if storeys > MIDRISE_MAX_STOREYS else "") + " (a placeholder for an elevator analysis)"}


# The program brief (`option.program_brief`): the spaces a kind of housing runs on beyond its homes, each a named block
# with an area and where it goes. A brief the option does not carry is the default for its housing type below, every
# figure a declared placeholder until the operator's own brief replaces it (24 Nov 2026: a supportive building had no
# desk, staff room, clinic or laundry, and a shelter no sleeping rooms).
BRIEF_DEFAULTS: dict[str, list[dict]] = {
    "supportive": [
        {"label": "24/7 front desk", "area_m2": 12, "next_to": "entry", "note": "staffed at all hours, beside the entry with a view of it and of the lift"},
        {"label": "Staff office", "area_m2": 15},
        {"label": "Staff washroom", "area_m2": 4},
        {"label": "Program room", "area_m2": 40, "note": "case planning, groups, life skills"},
        {"label": "Shared kitchen and dining", "per_home_m2": 1.0, "min_m2": 40, "replaces_amenity": True, "note": "meals that meet Canada's Food Guide (the Supportive Housing Program Framework's services)"},
        {"label": "Laundry", "per_home_m2": 0.4, "min_m2": 15},
        {"label": "Harm reduction room", "area_m2": 10, "note": "a room the operator can staff for overdose prevention, where its model includes one"},
    ],
    "transitional": [
        {"label": "Front desk", "area_m2": 10, "next_to": "entry"},
        {"label": "Staff office", "area_m2": 15},
        {"label": "Program room", "area_m2": 30},
        {"label": "Laundry", "per_home_m2": 0.4, "min_m2": 15},
    ],
    "shelter": [
        {"label": "24/7 front desk", "area_m2": 12, "next_to": "entry", "note": "24/7 access unless BC Housing approves otherwise (Emergency Shelter Program Framework)"},
        {"label": "Staff office", "area_m2": 15},
        {"label": "Sleeping rooms", "beds_per_room": 4, "per_bed_m2": 4.6, "where": "upper", "note": "four beds a room at most, 4.6 m² a bed space (Shelter Design Guidelines, rule bch.shelter.bed_space), plus 10% for the room's door and clearances"},
        {"label": "Washrooms and showers", "per_bed_m2": 0.6},
        {"label": "Dining", "per_bed_m2": 1.0, "min_m2": 30, "replaces_amenity": True},
        {"label": "Laundry", "per_bed_m2": 0.25, "min_m2": 12},
        {"label": "Lockers and storage", "per_bed_m2": 0.3},
    ],
}


def program_brief(option: dict) -> list[dict]:
    """The option's brief, or the default for its housing type, each item with its area worked out: a fixed area, or
    an area a home or a bed with a least area, or a shelter's sleeping rooms by beds. Items with no area are dropped.
    Every item says whether it is the operator's (`option.program_brief`) or the default placeholder. Pure."""
    from .checks import housing_kind, housing_parts
    own = option.get("program_brief")
    kind = housing_kind(option)
    parts = housing_parts(option)
    homes = sum(int((option.get("units") or {}).get(k) or 0) for k in UNIT_KEYS)
    beds = option.get("beds")
    beds = int(beds) if isinstance(beds, (int, float)) and not isinstance(beds, bool) and beds > 0 else 0
    if isinstance(own, list) and own:
        items, source = own, "option.program_brief"
    else:
        items = list(BRIEF_DEFAULTS.get(kind, []))
        # a shelter or supportive part of a mixed building takes the part's own spaces
        if kind == "independent" and "shelter" in parts:
            items += [dict(i, label=f"Shelter: {i['label']}") for i in BRIEF_DEFAULTS["shelter"]]
        if kind == "independent" and "supportive" in parts:
            items += [dict(i, label=f"Supportive: {i['label']}") for i in BRIEF_DEFAULTS["supportive"] if not i.get("replaces_amenity")]
        source = "placeholder"
    out = []
    for it in items:
        if not isinstance(it, dict) or not str(it.get("label") or "").strip():
            continue
        try:
            if it.get("beds_per_room"):
                rooms = math.ceil(beds / int(it["beds_per_room"])) if beds else 0
                area = rooms * int(it["beds_per_room"]) * float(it.get("per_bed_m2") or 4.6) * 1.10
                words = f"{rooms} rooms of up to {int(it['beds_per_room'])} beds for {beds} beds"
            elif it.get("per_bed_m2"):
                area = max(float(it.get("min_m2") or 0), beds * float(it["per_bed_m2"])) if beds else 0
                words = f"{float(it['per_bed_m2']):g} m² a bed × {beds} beds" + (f", at least {float(it['min_m2']):g} m²" if it.get("min_m2") else "")
            elif it.get("per_home_m2"):
                n = homes or beds
                area = max(float(it.get("min_m2") or 0), n * float(it["per_home_m2"])) if n else 0
                words = f"{float(it['per_home_m2']):g} m² a home × {n}" + (f", at least {float(it['min_m2']):g} m²" if it.get("min_m2") else "")
            else:
                area, words = float(it.get("area_m2") or 0), ""
        except (TypeError, ValueError):
            continue
        if area <= 0:
            continue
        out.append({"label": str(it["label"]).strip(), "area_m2": round(area, 1), "next_to": it.get("next_to"), "where": it.get("where") or "ground",
                    "replaces_amenity": bool(it.get("replaces_amenity")), "source": source, "note": "; ".join(x for x in (words, it.get("note") or "") if x)})
    return out


def _go_program(option: dict, prog: dict) -> dict:
    """The program of ground-oriented homes: no indoor amenity under `go_amenity_homes` homes, services at
    `go_services_m2` plus the bicycles, and the typology's assumptions listed."""
    serv, _ = TYPOLOGY_ASSUMPTIONS["go_services_m2"]
    few, _ = TYPOLOGY_ASSUMPTIONS["go_amenity_homes"]
    bike_each, _ = LAYOUT_ASSUMPTIONS["bicycle_m2_per_space"]
    bikes = int(option.get("bicycle_spaces") or 0)
    out = []
    for b in prog["blocks"]:
        if b["key"] == "amenity" and prog["units_total"] < few:
            continue
        if b["key"] == "services":
            # bicycles go in each home or its yard, not a shared room
            b = dict(b, area_m2=round(serv, 1), note=f"{serv:.0f} m² services for ground-oriented homes; the {bikes} bicycle spaces are in the homes and their yards")
        out.append(b)
    return dict(prog, blocks=out, assumptions=prog["assumptions"] + [{"key": k, "value": v, "note": n} for k, (v, n) in TYPOLOGY_ASSUMPTIONS.items() if k.startswith("go_")])


def _solve_ground_oriented(site: dict, option: dict, ledger: dict, massing: dict, prog: dict) -> dict[str, Any]:
    """Ground-oriented homes on the plate: rows of homes side by side across the plate's width, each home the row's
    depth and running up through its floors with its own door and stair (a townhouse); over three storeys the homes
    stack two storeys at a time (stacked townhouses, the upper one by its own stair). A plate deep enough for two rows
    and a courtyard takes a front and a rear building. No corridor, no core, no lift. The ground floor's other uses
    take a slice of the front row's ground floor; the floors above that slice hold one-floor homes where one fits."""
    pm, x0, y0, W, D, storeys, f2f = _plate(massing)
    prog = _go_program(option, prog)
    row_max, _ = TYPOLOGY_ASSUMPTIONS["go_row_depth_m"]
    row_min, _ = TYPOLOGY_ASSUMPTIONS["go_row_min_m"]
    court, _ = TYPOLOGY_ASSUMPTIONS["go_courtyard_m"]
    w_min, _ = TYPOLOGY_ASSUMPTIONS["go_min_width_m"]
    warnings: list[str] = []
    if D >= 2 * row_min + court:
        dr = min(row_max, (D - court) / 2)
        rows = [{"side": "front", "y": y0, "d": dr}, {"side": "rear", "y": y0 + D - dr, "d": dr}]
        court_d = D - 2 * dr
    else:
        dr = min(row_max, D)
        rows = [{"side": "front", "y": y0, "d": dr}]
        court_d = 0.0
        if D > dr + 0.5:
            warnings.append(f"The plate is {D:.1f} m deep; one row of homes {dr:.1f} m deep stands at the street, the {D - dr:.1f} m behind it is yard (two rows and a courtyard need {2 * row_min + court:g} m).")
    # the floors a home spans: all of them up to three; over three, pairs (stacked townhouses), an odd top floor of flats
    if storeys <= WALKUP_MAX_STOREYS:
        tiers = [(0, storeys)]
    else:
        tiers = [(a, min(a + 2, storeys)) for a in range(0, storeys, 2)]
    r2 = lambda v: round(v, 2)
    floors = [{"level": lv, "name": "Ground floor" if lv == 0 else f"Level {lv + 1}", "z": _floor_z(option, lv, f2f), "zones": [], "spare_m2": 0.0} for lv in range(storeys)]
    # each row's width left, tier by tier
    left = {(ri, ti): W for ri in range(len(rows)) for ti in range(len(tiers))}
    used_x = {(ri, ti): x0 for ri in range(len(rows)) for ti in range(len(tiers))}
    shortfall: list[dict] = []
    # the ground floor's other uses: a slice of the front row's ground floor each, at the street end; the floors over it
    # are taken by the tier above or left as spare
    for b in [b for b in prog["blocks"] if b["key"] in ("non_residential", "amenity", "services", "other")]:
        width = b["area_m2"] / rows[0]["d"]
        ri = len(rows) - 1 if b["key"] == "services" else 0
        if width > left[(ri, 0)] + 0.01:
            if b["key"] == "services":
                warnings.append(f"The {b['area_m2']:,.0f} m² of services do not fit the ground floor beside the homes: a shed in the yard, or below grade.")
            else:
                shortfall.append({"block": b["key"], "label": b["label"], "area_m2": round(b["area_m2"], 1)})
            continue
        x = used_x[(ri, 0)]
        floors[0]["zones"].append({"block": b["key"], "label": b["label"], "x": r2(x), "y": r2(rows[ri]["y"]), "w": r2(width), "d": r2(rows[ri]["d"]),
                                   "area_m2": round(b["area_m2"], 1), "side": rows[ri]["side"], **({"entry": True} if b.get("next_to") == "entry" else {})})
        used_x[(ri, 0)] += width
        left[(ri, 0)] -= width
        # the floors over a ground-only use in the first tier: as many as the tier spans less the ground, kept by
        # marking the slice as spare above (one-floor homes go there below if they fit)
        lo, hi = tiers[0]
        for lv in range(lo + 1, hi):
            floors[lv]["zones"].append({"block": "spare", "label": "Over the ground floor's other uses", "x": r2(x), "y": r2(rows[ri]["y"]), "w": r2(width), "d": r2(rows[ri]["d"]),
                                        "area_m2": round(width * rows[ri]["d"], 1), "side": rows[ri]["side"]})
    # the homes, the largest first, each in the first row and tier with room, ground tiers first
    queue = [b for b in prog["blocks"] if b["key"] in UNIT_KEYS]
    acc_left = int(option.get("accessible_units") or 0)
    hid = 0
    left_count = {b["key"]: int(b["count"]) for b in queue}
    # accessible homes first (25 Nov 2026: none were drawn, an accessible home needs its rooms on one floor at grade):
    # each a one-floor home on the front row's ground floor, the smallest type there is, with a home over it that runs
    # up through the floors above (a garden flat under a townhouse), where the storeys allow one
    lo0, hi0 = tiers[0]
    if acc_left and hi0 - lo0 > 1:
        for b in sorted(queue, key=lambda b: b["gross_m2_each"]):
            while acc_left and left_count[b["key"]]:
                width = max(w_min, b["gross_m2_each"] / rows[0]["d"])
                if width > left[(0, 0)] + 0.01:
                    break
                x = used_x[(0, 0)]
                hid += 1
                floors[0]["zones"].append({"block": b["key"], "label": b["label"], "x": r2(x), "y": r2(rows[0]["y"]), "w": r2(width), "d": r2(rows[0]["d"]),
                                           "area_m2": round(width * rows[0]["d"], 1), "side": rows[0]["side"], "home": hid, "levels": [0, 0], "entry": "at grade",
                                           "unit": b["key"], "accessible": True})
                left_count[b["key"]] -= 1
                acc_left -= 1
                # the home over it: the largest type left that fits this width through the floors above
                over = next((c for c in queue if left_count[c["key"]] and c["gross_m2_each"] / (rows[0]["d"] * (hi0 - 1)) <= width + 0.01), None)
                for lv in range(1, hi0):
                    z = {"block": over["key"] if over else "spare", "label": over["label"] if over else "Over the accessible home", "x": r2(x), "y": r2(rows[0]["y"]),
                         "w": r2(width), "d": r2(rows[0]["d"]), "area_m2": round(width * rows[0]["d"], 1), "side": rows[0]["side"]}
                    if over:
                        z.update({"home": hid + 1, "levels": [1, hi0 - 1], "entry": "by its own stair"})
                        if lv == 1:
                            z["unit"] = over["key"]
                    floors[lv]["zones"].append(z)
                if over:
                    hid += 1
                    left_count[over["key"]] -= 1
                used_x[(0, 0)] += width
                left[(0, 0)] -= width
    queue = [dict(b, count=left_count[b["key"]]) for b in queue]
    slots = [(ti, ri) for ti in range(len(tiers)) for ri in range(len(rows))]
    for b in queue:
        for _ in range(int(b["count"])):
            placed = False
            for ti, ri in slots:
                lo, hi = tiers[ti]
                span = hi - lo
                width = max(w_min, b["gross_m2_each"] / (rows[ri]["d"] * span))
                if width <= left[(ri, ti)] + 0.01:
                    x = used_x[(ri, ti)]
                    hid += 1
                    for lv in range(lo, hi):
                        z = {"block": b["key"], "label": b["label"], "x": r2(x), "y": r2(rows[ri]["y"]), "w": r2(width), "d": r2(rows[ri]["d"]),
                             "area_m2": round(width * rows[ri]["d"], 1), "side": rows[ri]["side"], "home": hid, "levels": [lo, hi - 1],
                             "entry": "at grade" if lo == 0 else "by its own stair"}
                        if lv == lo:
                            z["unit"] = b["key"]          # as the corridor solver marks a home (`_homes_on` reads the key)
                            # an accessible home needs its rooms on one floor at grade: only a one-floor home at grade counts
                            if acc_left and lo == 0 and span == 1:
                                z["accessible"] = True
                                acc_left -= 1
                        floors[lv]["zones"].append(z)
                    used_x[(ri, ti)] += width
                    left[(ri, ti)] -= width
                    placed = True
                    break
            if not placed:
                sf = next((s for s in shortfall if s["block"] == b["key"]), None)
                if sf:
                    sf["units"] += 1
                    sf["area_m2"] = round(sf["area_m2"] + b["gross_m2_each"], 1)
                else:
                    shortfall.append({"block": b["key"], "label": b["label"], "units": 1, "area_m2": b["gross_m2_each"]})
    if int(option.get("accessible_units") or 0) and acc_left:
        warnings.append(f"{acc_left} of the {int(option.get('accessible_units') or 0)} accessible homes are not drawn: each is a one-floor home at grade, "
                        "and the front row's ground floor has no room left for one.")
    elif int(option.get("accessible_units") or 0):
        warnings.append("The accessible homes are one-floor homes at grade on the front row, each with a home over it reached by its own stair (a garden flat under a townhouse).")
    # what is left in each row and tier is spare; the courtyard is a cut-out on every floor (open to the sky)
    for (ri, ti), rest in left.items():
        if rest > 0.3:
            lo, hi = tiers[ti]
            for lv in range(lo, hi):
                floors[lv]["zones"].append({"block": "spare", "label": "Spare", "x": r2(used_x[(ri, ti)]), "y": r2(rows[ri]["y"]), "w": r2(rest), "d": r2(rows[ri]["d"]),
                                            "area_m2": round(rest * rows[ri]["d"], 1), "side": rows[ri]["side"]})
    for fl in floors:
        if court_d > 0.3:
            fl["zones"].append({"block": "void", "label": "Courtyard", "x": r2(x0), "y": r2(y0 + rows[0]["d"]), "w": r2(W), "d": r2(court_d), "area_m2": round(W * court_d, 1), "side": "front"})
        elif D > dr + 0.3:
            fl["zones"].append({"block": "void", "label": "Yard", "x": r2(x0), "y": r2(y0 + dr), "w": r2(W), "d": r2(D - dr), "area_m2": round(W * (D - dr), 1), "side": "rear"})
        fl["spare_m2"] = round(sum(z["area_m2"] for z in fl["zones"] if z["block"] == "spare"), 1)
    homes_kind = "townhouses" if len(tiers) == 1 and storeys > 1 else ("stacked townhouses" if storeys > WALKUP_MAX_STOREYS else "one-floor homes")
    plate = {"x": r2(x0), "y": r2(y0), "width_m": r2(W), "depth_m": r2(D), "storeys": storeys, "floor_to_floor_m": f2f, "double_loaded": False, "unit_depth_m": r2(dr),
             "arrangement": "ground_oriented", "stacking": "homes",
             "ground_oriented": {"rows": len(rows), "row_depth_m": r2(dr), "courtyard_m": r2(court_d), "home_spans": [hi - lo for lo, hi in tiers], "homes": homes_kind}}
    if ground_extra(option, f2f):
        plate["ground_floor_m"] = round(f2f + ground_extra(option, f2f), 2)
    L = _assemble(site, option, ledger, massing, prog, plate, floors, shortfall, warnings, edited=False, geometry=[])
    # the corridor-and-core rules do not apply; what applies is that every home has a door of its own
    L["adjacencies"] = [c for c in L["adjacencies"] if c["id"] not in ("core_centre", "units_both_sides", "accessible_core", "amenity_entry")]
    upper = any(lo > 0 for lo, hi in tiers) or any(z.get("levels", [0])[0] > 0 for fl in floors for z in fl["zones"] if z.get("home"))
    L["adjacencies"].append({"id": "own_entry", "block": "units", "rule": "every home with a door of its own, no common corridor or lift", "status": "pass" if not upper else "conditional",
                             "note": ("each home's door is at grade and its stair inside it" if not upper else
                                      "the lower homes' doors are at grade; the upper homes are reached by their own stair, whose run and exit the architect draws")})
    L["egress"] = _ground_egress(L["floors"], tiers)
    return L


def _ground_egress(floors: list[dict], tiers: list[tuple[int, int]]) -> dict[str, Any]:
    """Exits for ground-oriented homes: each home its own door, its own stair inside it. A home over three storeys, or
    an upper home reached by its own stair, is a placeholder the architect confirms against Part 9 (9.9.9: egress from
    dwelling units), which the rules do not hold."""
    out = []
    for fl in floors:
        homes = sorted({z["home"] for z in fl["zones"] if z.get("home")})
        upper = any(z.get("home") and z["levels"][0] > 0 for z in fl["zones"])
        out.append({"level": fl["level"], "name": fl["name"], "exits": len(homes), "exits_required": 1 if homes else 0, "separation_m": None, "separation_min_m": None,
                    "farthest_travel_m": None, "travel_limit_m": None, "farthest_unit": None, "dead_end_m": None, "dead_end_limit_m": None,
                    "status": "uncertain" if upper else "pass",
                    "notes": (["each home on this floor reaches its own door; the upper homes do so by their own stair, to confirm against Part 9 (9.9.9), not in the rules"] if upper
                              else ["each home on this floor has its own door and stair; no common corridor"] if homes else [])})
    overall = "uncertain" if any(f["status"] == "uncertain" for f in out) else "pass"
    return {"rule_id": EGRESS_RULE, "sprinklered": False, "sprinklered_is_placeholder": True, "limits": {}, "floors": out, "status": overall, "scissor_stair": False, "ground_oriented": True,
            "summary": "Egress (ground-oriented homes): every home has its own door" + (" at grade" if overall == "pass" else "; the upper homes reach theirs by their own stair, a placeholder to confirm against Part 9")
                       + "; no common corridor, exit stair or lift."}


def _solve_tower(site: dict, option: dict, ledger: dict, massing: dict, prog: dict) -> dict[str, Any]:
    """A tower: the podium's floors on the podium plate and the tower's floors on the tower plate over it (massing's
    `tower`), each laid out as a plate of its own and joined, the ground around the tower plate on its floors a cut-out
    (the podium's roof). The podium takes the ground floor's uses and the homes it holds, the tower the rest. Without a
    podium the tower plate runs from the ground."""
    import copy
    pm = next(x for x in massing["masses"] if x["name"] == "proposed")
    tw = pm["tower"]
    P = int(pm.get("podium_storeys") or 0)
    S = int(pm["storeys"])

    def sub(r: dict, storeys: int) -> dict:
        mass = {k: v for k, v in pm.items() if k not in ("parts", "plate_origin", "angle_deg", "tower", "tiers")}
        mass.update(footprint=[[r["x"], r["y"]], [r["x"] + r["w"], r["y"]], [r["x"] + r["w"], r["y"] + r["d"]], [r["x"], r["y"] + r["d"]]],
                    plate_width_m=r["w"], plate_depth_m=r["d"], storeys=storeys)
        return {**massing, "masses": [mass] + [m for m in massing["masses"] if m["name"] != "proposed"]}

    if P <= 0:
        L = _solve_plate(site, option, ledger, sub(tw, S), prog)
        L["plate"]["tower"] = {**{k: tw[k] for k in ("x", "y", "w", "d")}, "from_level": 0}
        return L
    pod = {"x": float(pm["footprint"][0][0]), "y": float(pm["footprint"][0][1]), "w": float(pm["plate_width_m"]), "d": float(pm["plate_depth_m"])}
    A = _solve_plate(site, option, ledger, sub(pod, P), copy.deepcopy(prog))
    owed = {s["block"]: int(s["units"]) for s in A["shortfall"] if s.get("units")}
    prog_b = {**prog, "units_total": sum(owed.values()), "no_lobby": True, "accessible_units": 0,
              "blocks": [{**b, "count": owed[b["key"]], "area_m2": round(owed[b["key"]] * b["gross_m2_each"], 1)} for b in prog["blocks"] if b["key"] in UNIT_KEYS and owed.get(b["key"])]}
    B = _solve_plate(site, option, ledger, sub(tw, S - P), prog_b) if prog_b["units_total"] else None
    f2f = float(pm["floor_to_floor_m"])
    top = A["floors"][-1]["z"] + f2f
    floors = [dict(fl) for fl in A["floors"]]
    r2 = lambda v: round(v, 2)
    # the podium roof round the tower plate, on each tower floor: cut-outs, not floor area
    ring_voids = []
    for x, y, w, d in ((pod["x"], pod["y"], pod["w"], tw["y"] - pod["y"]), (pod["x"], tw["y"] + tw["d"], pod["w"], pod["y"] + pod["d"] - tw["y"] - tw["d"]),
                       (pod["x"], tw["y"], tw["x"] - pod["x"], tw["d"]), (tw["x"] + tw["w"], tw["y"], pod["x"] + pod["w"] - tw["x"] - tw["w"], tw["d"])):
        if w > 0.05 and d > 0.05:
            ring_voids.append({"block": "void", "label": "Podium roof", "x": r2(x), "y": r2(y), "w": r2(w), "d": r2(d), "area_m2": round(w * d, 1), "side": "front"})
    for i in range(S - P):
        lv = P + i
        zones = [dict(z) for z in (B["floors"][i]["zones"] if B else [])] + [dict(v) for v in ring_voids]
        if not B:
            zones.append({"block": "spare", "label": "Spare", "x": r2(tw["x"]), "y": r2(tw["y"]), "w": r2(tw["w"]), "d": r2(tw["d"]), "area_m2": round(tw["w"] * tw["d"], 1), "side": "front"})
        floors.append({"level": lv, "name": f"Level {lv + 1}", "z": round(top + i * f2f, 2), "zones": zones,
                       "spare_m2": (B["floors"][i]["spare_m2"] if B else round(tw["w"] * tw["d"], 1))})
    plate = dict(A["plate"], storeys=S, arrangement="tower",
                 tower={**{k: r2(tw[k]) for k in ("x", "y", "w", "d")}, "from_level": P, "arrangement": (B["plate"]["arrangement"] if B else None)})
    shortfall = [s for s in A["shortfall"] if not s.get("units")] + (list(B["shortfall"]) if B else [{**s} for s in A["shortfall"] if s.get("units")])
    warnings = [w for w in A["warnings"] + (B["warnings"] if B else []) if w not in (massing.get("warnings") or [])]
    warnings = list(dict.fromkeys(warnings))
    warnings.insert(0, f"A tower: {P} podium floor{'s' if P != 1 else ''} of {pod['w']:g} × {pod['d']:g} m, and {S - P} tower floors of {tw['w']:g} × {tw['d']:g} m ({tw['w'] * tw['d']:,.0f} m²) over them. "
                       "Each is laid out with its own core here; where the tower's core lands in the podium is the architect's to draw (one core runs through both).")
    L = _assemble(site, option, ledger, massing, prog, plate, floors, shortfall, warnings, edited=False, geometry=[])
    ea, eb = A.get("egress"), (B or {}).get("egress")
    if ea:
        per = list(ea["floors"]) + [dict(f, level=f["level"] + P, name=f"Level {f['level'] + P + 1}") for f in ((eb or {}).get("floors") or [])]
        overall = max((f["status"] for f in per), key=lambda s: _STATUS_RANK.get(s, 0)) if per else "pass"
        L["egress"] = {**ea, "floors": per, "status": overall,
                       "summary": f"The podium: {ea.get('summary') or ''}" + (f" The tower: {eb.get('summary') or ''}" if eb else "")}
    return L


# ---------------------------------------------------------------- the area schedule and what the operator runs

AREA_GROUPS = (("homes", "Homes (net, inside their walls)"), ("circulation", "Corridors, lobby, landings"), ("core", "Cores: stairs, elevators, shafts"),
               ("program", "Program spaces (desk, staff, dining, laundry, sleeping rooms)"), ("amenity", "Amenity"), ("services", "Services and bicycles"),
               ("non_residential", "Non-residential and commercial"), ("spare", "Spare (not yet used)"))
EFFICIENCY_FLOOR = 0.70    # a declared placeholder: below this share of homes in the floor area a plate is flagged


def _area_group(z: dict) -> str | None:
    b = z["block"]
    if b in UNIT_KEYS:
        return "homes"
    if b == "corridor" or (b == "design_space" and z.get("entry")):
        return "circulation"
    if b == "core":
        return "core"
    if b in ("other", "design_space"):
        return "program"
    if b in ("amenity", "services", "spare"):
        return b
    if b in ("non_residential", "commercial"):
        return "non_residential"
    return None      # a cut-out (void) is not floor area


def area_schedule(L: dict) -> dict[str, Any]:
    """The area schedule: for each floor, the homes by type and the floor area by use (homes net of their partitions,
    circulation, cores, program, amenity, services, non-residential, spare), the floor's gross area and its efficiency
    (the homes' net over the gross). A home over more than one floor counts once, on its entry floor, and its area on
    each floor it spans. Totals for the building and a flag where the efficiency is under EFFICIENCY_FLOOR. Pure."""
    partition, _ = LAYOUT_ASSUMPTIONS["partition_allowance"]
    rows = []
    for fl in L["floors"]:
        by = {g: 0.0 for g, _ in AREA_GROUPS}
        homes = {k: 0 for k in UNIT_KEYS}
        for z in fl["zones"]:
            g = _area_group(z)
            if not g:
                continue
            a = float(z["area_m2"])
            by[g] += a / partition if g == "homes" else a
            if z.get("unit"):
                homes[z["block"]] += 1
        walls = sum(float(z["area_m2"]) for z in fl["zones"] if z["block"] in UNIT_KEYS) - by["homes"]
        gross = sum(by.values()) + walls
        rows.append({"level": fl["level"], "name": fl["name"], "homes": {k: v for k, v in homes.items() if v}, "homes_total": sum(homes.values()),
                     "m2": {g: round(v, 1) for g, v in by.items()}, "partitions_m2": round(walls, 1), "gross_m2": round(gross, 1),
                     "efficiency": round(by["homes"] / gross, 3) if gross else None})
    tot = {g: round(sum(r["m2"][g] for r in rows), 1) for g, _ in AREA_GROUPS}
    walls = round(sum(r["partitions_m2"] for r in rows), 1)
    gross = round(sum(r["gross_m2"] for r in rows), 1)
    homes = {k: sum(r["homes"].get(k, 0) for r in rows) for k in UNIT_KEYS}
    eff = round(tot["homes"] / gross, 3) if gross else None
    built = [r for r in rows if r["gross_m2"]]
    return {"floors": rows, "totals": {"m2": tot, "partitions_m2": walls, "gross_m2": gross, "homes": {k: v for k, v in homes.items() if v}, "homes_total": sum(homes.values()),
                                       "efficiency": eff, "net_to_gross": eff},
            "efficiency_floor": EFFICIENCY_FLOOR, "flag": bool(eff is not None and eff < EFFICIENCY_FLOOR and sum(homes.values()) and built),
            "groups": [{"key": g, "label": lab} for g, lab in AREA_GROUPS],
            "note": (f"Homes are counted net of their partitions ({int(round((partition - 1) * 100))}% of a home's gross is its walls, shown apart); a home over more than one floor is "
                     "counted once, on its entry floor. Cut-outs (a courtyard, a podium roof) are not floor area. Efficiency is the homes' net over the gross; "
                     f"under {int(EFFICIENCY_FLOOR * 100)}% is flagged (a placeholder for what a cost consultant would query).")}


def area_schedule_csv(sched: dict) -> str:
    """The area schedule as CSV, a row a floor and a total row: the homes by type, then the areas by use in m²."""
    keys = [g for g, _ in AREA_GROUPS]
    head = ["Floor", "Homes"] + [UNIT_LABEL[k] for k in UNIT_KEYS] + [lab for _, lab in AREA_GROUPS] + ["Partitions", "Gross", "Efficiency"]
    lines = [",".join(f'"{h}"' for h in head)]
    for r in sched["floors"] + [{"name": "Total", "homes_total": sched["totals"]["homes_total"], "homes": sched["totals"]["homes"], "m2": sched["totals"]["m2"],
                                 "partitions_m2": sched["totals"]["partitions_m2"], "gross_m2": sched["totals"]["gross_m2"], "efficiency": sched["totals"]["efficiency"]}]:
        cells = [f'"{r["name"]}"', str(r["homes_total"])] + [str(r["homes"].get(k, 0)) for k in UNIT_KEYS] + [f"{r['m2'][k]:.1f}" for k in keys]
        cells += [f"{r['partitions_m2']:.1f}", f"{r['gross_m2']:.1f}", f"{r['efficiency']:.3f}" if r["efficiency"] is not None else ""]
        lines.append(",".join(cells))
    return "\n".join(lines) + "\n"


def operability(L: dict, option: dict) -> dict[str, Any]:
    """What an operator checks on the plans before saying it can run the building (24 Nov 2026, the operator's review):
    the elevators against the homes, the staffed spaces the housing type runs on, laundry, the services room against the
    homes, the accessible homes against BC Housing's 5%, and the amenity. Each item pass / missing / info with a note;
    the figures are this screen's placeholders, never an operator's standard."""
    from .checks import housing_kind, housing_parts
    kind = housing_kind(option)
    parts = housing_parts(option)
    zones = [z for fl in L["floors"] for z in fl["zones"]]
    labels = [str(z.get("label") or "").lower() for z in zones]
    homes = int(L.get("units_placed") or 0)
    p = L["plate"]
    go = p.get("arrangement") == "ground_oriented"
    lift = lifts_needed(int(L.get("units_total") or 0), int(p["storeys"]), ground_oriented=go)
    cores = [z for fl in L["floors"][:1] for z in fl["zones"] if z["block"] == "core" and min(z["w"], z["d"]) >= ELEVATOR_CORE_M - 1e-6]
    items = [{"key": "lifts", "label": "Elevators", "status": "info" if not lift["lifts"] else ("pass" if cores else "missing"),
              "note": lift["words"] + ("" if not lift["lifts"] or cores else "; no core on the ground floor is large enough to hold an elevator") + "."}]
    staffed = kind != "independent" or any(k != "independent" for k in parts)
    for want, words in (("desk", "a staffed front desk by the entry"), ("staff office", "a staff office")):
        if staffed:
            hit = any(want in l for l in labels)
            items.append({"key": want.replace(" ", "_"), "label": want.capitalize(), "status": "pass" if hit else "missing",
                          "note": f"{words} drawn" if hit else f"{words}: none on the plans (a supportive, transitional or shelter part runs on one)"})
    if staffed:
        desk = next((z for z in zones if "desk" in str(z.get("label") or "").lower()), None)
        entry = next((z for z in zones if z.get("entry")), None)
        if desk and entry:
            near = _touches(desk, entry, 0.6) or _gap(desk, entry) < 3.0
            items.append({"key": "desk_entry", "label": "Desk sees the entry", "status": "pass" if near else "missing",
                          "note": "the desk is beside the entry" if near else "the desk is not beside the entry: move it where it sees the door"})
    laundry = any("laundry" in l for l in labels)
    items.append({"key": "laundry", "label": "Laundry", "status": "pass" if laundry or go else "missing",
                  "note": "a shared laundry room drawn" if laundry else ("each home has its own" if go else "no shared laundry on the plans; in-suite laundry is the architect's and operator's choice to state")})
    serv = sum(float(z["area_m2"]) for z in zones if z["block"] == "services")
    need = 0.3 * homes
    items.append({"key": "services", "label": "Garbage, recycling and services", "status": "pass" if serv >= need or go else "missing",
                  "note": f"{serv:,.0f} m² of services for {homes} homes" + ("" if serv >= need or go else f"; about {need:,.0f} m² (0.3 m² a home, a placeholder) is what a garbage and recycling room for this many homes takes")})
    acc = sum(1 for z in zones if z.get("accessible"))
    want_acc = math.ceil(0.05 * homes) if homes else 0
    items.append({"key": "accessible", "label": "Accessible homes", "status": "pass" if acc >= want_acc else "missing",
                  "note": f"{acc} accessible homes drawn, {want_acc} wanted (BC Housing's 5% of {homes})"})
    amen = sum(float(z["area_m2"]) for z in zones if z["block"] == "amenity" or "dining" in str(z.get("label") or "").lower())
    items.append({"key": "amenity", "label": "Shared indoor space", "status": "info",
                  "note": f"{amen:,.0f} m² of amenity or dining, {amen / homes:.1f} m² a home" if homes and amen else "no shared indoor room drawn"})
    missing = [i for i in items if i["status"] == "missing"]
    return {"items": items, "lifts": lift["lifts"], "status": "missing" if missing else "pass",
            "summary": ("Operability: " + (", ".join(i["label"].lower() for i in missing) + " missing" if missing else "the items an operator checks first are on the plans")
                        + f"; {lift['words']}.")}


def solve(site: dict, option: dict, ledger: dict, massing: dict) -> dict[str, Any]:
    """Place the blocks on the proposed mass's plates, floor by floor, and say what held and what did not. Where
    the option carries a placement of its own (`layout.zones`, written by the block editor), that placement is
    re-checked instead, so a run reproduces what a person drew. A compact tower plate is laid out both ways, along a
    corridor and as a point tower (`_point_geometry`), and the one that places more homes with exits no worse is
    kept, the point tower on a tie."""
    zones = (option.get("layout") or {}).get("zones")
    if zones:
        return place_zones(site, option, ledger, massing, zones)
    prog = blocks(option, ledger)
    # the building types (24 Nov 2026): ground-oriented homes by their own rows; a tower as a podium and a tower plate
    pm_ = next((x for x in massing["masses"] if x["name"] == "proposed"), None) or {}
    if building_type(option) == "ground_oriented":
        return _solve_ground_oriented(site, option, ledger, massing, prog)
    if pm_.get("tower"):
        return _solve_tower(site, option, ledger, massing, prog)
    # a plate in two parts (massing: the plate box and a wing beside it) is laid out part by part and joined
    parts = pm_.get("parts")
    if parts and len(parts) == 2:
        return _solve_parts(site, option, ledger, massing, prog, parts)
    return _solve_plate(site, option, ledger, massing, prog)


def _solve_parts(site: dict, option: dict, ledger: dict, massing: dict, prog: dict, parts: list[dict]) -> dict[str, Any]:
    """A plate of two rectangles, the plate box and its wing (23 Nov 2026: a plate was one rectangle whatever the lot).
    Each part is laid out as a plate of its own, with its own core, corridor and exits: the main part takes the
    ground-floor uses and as many homes as it holds, the wing the homes that are left. The record is one plate, the
    rectangle round both, with the ground neither part covers as cut-outs (`void` zones, which are not floor area),
    so the sheets, the floor area and the block editor read it as any plate with a cut-out. The exits are read part by
    part, since each part has its own, and each floor carries the worse of the two."""
    import copy
    pm = next(x for x in massing["masses"] if x["name"] == "proposed")

    def sub(r: dict) -> dict:
        mass = {k: v for k, v in pm.items() if k not in ("parts", "plate_origin", "angle_deg")}
        mass.update(footprint=[[r["x"], r["y"]], [r["x"] + r["w"], r["y"]], [r["x"] + r["w"], r["y"] + r["d"]], [r["x"], r["y"] + r["d"]]],
                    plate_width_m=r["w"], plate_depth_m=r["d"])
        return {**massing, "masses": [mass] + [m for m in massing["masses"] if m["name"] != "proposed"]}

    A = _solve_plate(site, option, ledger, sub(parts[0]), copy.deepcopy(prog))
    owed = {s["block"]: int(s["units"]) for s in A["shortfall"] if s.get("units")}
    flagged = sum(1 for fl in A["floors"] for z in fl["zones"] if z.get("accessible"))
    prog_b = {**prog, "units_total": sum(owed.values()), "no_lobby": True, "accessible_units": max(0, int(option.get("accessible_units") or 0) - flagged),
              "blocks": [{**b, "count": owed[b["key"]], "area_m2": round(owed[b["key"]] * b["gross_m2_each"], 1)} for b in prog["blocks"] if b["key"] in UNIT_KEYS and owed.get(b["key"])]}
    B = _solve_plate(site, option, ledger, sub(parts[1]), prog_b)

    x0, y0 = min(p["x"] for p in parts), min(p["y"] for p in parts)
    x1, y1 = max(p["x"] + p["w"] for p in parts), max(p["y"] + p["d"] for p in parts)
    xs = sorted({round(v, 2) for p in parts for v in (p["x"], p["x"] + p["w"])})
    ys = sorted({round(v, 2) for p in parts for v in (p["y"], p["y"] + p["d"])})
    covered = lambda cx, cy: any(p["x"] - 0.01 <= cx <= p["x"] + p["w"] + 0.01 and p["y"] - 0.01 <= cy <= p["y"] + p["d"] + 0.01 for p in parts)
    voids: list[dict] = []
    for j in range(len(ys) - 1):
        run = None
        for i in range(len(xs) - 1):
            empty = not covered((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2)
            if empty and run is None:
                run = xs[i]
            if run is not None and (not empty or i == len(xs) - 2):
                end = xs[i + 1] if empty else xs[i]
                voids.append({"block": "void", "label": "Cut-out", "x": run, "y": ys[j], "w": round(end - run, 2), "d": round(ys[j + 1] - ys[j], 2),
                              "area_m2": round((end - run) * (ys[j + 1] - ys[j]), 1)})
                run = None
    mid = y0 + (y1 - y0) / 2
    floors: list[dict] = []
    for fa, fb in zip(A["floors"], B["floors"]):
        zones = [dict(z) for z in fa["zones"]] + [dict(z, wing=True) for z in fb["zones"]] + [dict(v) for v in voids]
        for z in zones:
            z["side"] = "front" if z["y"] + z["d"] / 2 < mid else "rear"
        floors.append({"level": fa["level"], "name": fa["name"], "z": fa["z"], "zones": zones, "spare_m2": round(fa["spare_m2"] + fb["spare_m2"], 1)})
    pa, pb = A["plate"], B["plate"]
    plate = {"x": round(x0, 2), "y": round(y0, 2), "width_m": round(x1 - x0, 2), "depth_m": round(y1 - y0, 2), "storeys": pa["storeys"], "floor_to_floor_m": pa["floor_to_floor_m"],
             "double_loaded": pa["double_loaded"], "unit_depth_m": pa["unit_depth_m"], "arrangement": "wings", "stacking": pa.get("stacking"),
             "parts": [{**{k: parts[i][k] for k in ("x", "y", "w", "d")}, "arrangement": p["arrangement"], **({"corridor": "across"} if p.get("corridor") == "across" else {}),
                        **({"joins": parts[i]["joins"]} if parts[i].get("joins") else {})} for i, p in enumerate((pa, pb))]}
    shortfall = [s for s in A["shortfall"] if not s.get("units")] + list(B["shortfall"])
    seen: list[str] = []
    for w in A["warnings"] + B["warnings"]:
        if w not in seen and w not in (massing.get("warnings") or []):
            seen.append(w)
    w_part = parts[1]
    seen.insert(0, f"The plate is in two parts: the plate box of {parts[0]['w']:g} × {parts[0]['d']:g} m and a wing of {w_part['w']:g} × {w_part['d']:g} m on its {w_part.get('joins', 'far')} side. "
                   "Each is laid out with its own core, corridor and exits; where they meet is the architect's to draw (one core may serve both).")
    L = _assemble(site, option, ledger, massing, prog, plate, floors, shortfall, seen, edited=False, geometry=[])
    ea, eb = A.get("egress"), B.get("egress")
    if ea and eb:
        per = []
        for fa, fb in zip(ea["floors"], eb["floors"]):
            worse = max((fa, fb), key=lambda f: (_STATUS_RANK.get(f["status"], 0), f.get("farthest_travel_m") or 0))
            per.append({**worse, "exits": fa["exits"] + fb["exits"], "notes": list(fa["notes"]) + [f"the wing: {n}" for n in fb["notes"]]})
        overall = max((f["status"] for f in per), key=lambda s: _STATUS_RANK.get(s, 0))
        L["egress"] = {**ea, "floors": per, "status": overall, "by_part": True,
                       "summary": f"{ea.get('summary') or ''} The wing, read with its own exits: {eb.get('summary') or ''}".strip()}
    return L


def _solve_plate(site: dict, option: dict, ledger: dict, massing: dict, prog: dict) -> dict[str, Any]:
    """One rectangular plate laid out the ways it can be, and the best kept (see `solve`)."""
    import copy
    slab = _solve(site, option, ledger, massing, prog, None)
    rank = lambda L: _STATUS_RANK.get((L.get("egress") or {}).get("status") or "pass", 0)
    # the corridor run across the plate, from the street to the lane (23 Nov 2026, from an architect's test: on a lot
    # 20 m wide and 26 m deep the corridor along the street served five homes a floor where one run back from the street
    # serves seven). Tried on a plate deeper than it is wide, and kept where it places more homes with exits no worse.
    # Not where the architect set a grid or cores, which are drawn for the plate as it stands.
    pm_ = next((x for x in massing["masses"] if x["name"] == "proposed"), None) or {}
    lay_spec = option.get("layout") or {}
    if float(pm_.get("plate_depth_m") or 0) > float(pm_.get("plate_width_m") or 0) + 0.5 and not lay_spec.get("grid") and not lay_spec.get("cores"):
        cross = _solve(site, option, ledger, massing, copy.deepcopy(prog), None, across=True)
        # more homes with exits no worse, or as many homes with better exits; and always where the corridor along the
        # street would leave homes deeper than daylight reaches and the corridor across does not (a 20 × 49 m plate
        # laid along the street "placed" homes 23.6 m deep and 3 m wide)
        deep_max, _ = LAYOUT_ASSUMPTIONS["max_home_depth_m"]
        too_deep = lambda L: float(L["plate"].get("unit_depth_m") or 0) > deep_max + 0.05
        if ((too_deep(slab) and not too_deep(cross))
                or (not (too_deep(cross) and not too_deep(slab)) and ((cross["units_placed"] > slab["units_placed"] and rank(cross) <= rank(slab))
                                                                      or (cross["units_placed"] == slab["units_placed"] and rank(cross) < rank(slab))))):
            slab = cross
    # a low building is also tried as a walk-up (`_walkup_geometries`); one is kept only where it places more homes, its
    # exits no worse, or where the corridor plan places none
    best = slab
    ev = (_find(ledger["results"], rule_id=EGRESS_RULE) or {}).get("values") or {}
    for wu in _walkup_geometries(option, massing, prog, float(ev.get("two_exits_over_floor_area_m2") or 150.0)):
        walk = _solve(site, option, ledger, massing, wu["prog"], wu)
        if walk["units_placed"] > best["units_placed"] and (rank(walk) <= rank(best) or best["units_placed"] == 0):
            best = walk
    if best is not slab:
        return best
    pt = _point_geometry(option, massing)
    if pt is None:
        return slab
    point = _solve(site, option, ledger, massing, prog, pt)
    return point if point["units_placed"] >= slab["units_placed"] and rank(point) <= rank(slab) else slab


# A declared placeholder: the least a room (not a home) measures along its strip. Rooms the solver laid narrower,
# side by side across the whole depth of the strip, are regrouped (`_square_small_rooms`).
ROOM_MIN_WIDTH_M = 2.4
_ROOMS = ("other", "services", "amenity", "design_space", "non_residential", "commercial")


def _square_small_rooms(fl: dict) -> None:
    """Small rooms as rooms, not slots (25 Nov 2026: a 12 m² front desk was drawn 1.0 m wide and 11.85 m deep, the
    strip's whole depth). Along a strip, neighbouring rooms narrower than ROOM_MIN_WIDTH_M are gathered until they
    are together that wide, and stand one behind another in that shared width, each as deep as its share: every
    room keeps its area, the first keeps the strip's outer face (the street side of the street strip, the lane side
    of the lane strip), and nothing else on the floor moves. In place."""
    strips: dict[tuple[float, float], list[dict]] = {}
    for z in fl["zones"]:
        if z["block"] in _ROOMS and z["d"] > z["w"]:
            strips.setdefault((round(z["y"], 2), round(z["d"], 2)), []).append(z)
    for (y, d), zs in strips.items():
        zs.sort(key=lambda z: z["x"])
        run: list[dict] = []
        for z in zs + [None]:
            touching = z is not None and run and abs(run[-1]["x"] + run[-1]["w"] - z["x"]) < 0.03
            if z is not None and z["w"] < ROOM_MIN_WIDTH_M and (not run or touching):
                run.append(z)
                continue
            # close the run: groups each at least the minimum wide, a short tail joining the group before it
            groups: list[list[dict]] = []
            cur: list[dict] = []
            for r in run:
                cur.append(r)
                if sum(q["w"] for q in cur) >= ROOM_MIN_WIDTH_M:
                    groups.append(cur)
                    cur = []
            if cur:
                if groups:
                    groups[-1] += cur
                else:
                    groups.append(cur)
            for g in groups:
                if len(g) < 2:
                    # A narrow room alone beside a wide one takes a corner of it: it widens to the minimum and
                    # shortens to its area, at the strip's outer face, and the wide room keeps its own area as two
                    # rectangles (its main part, and the piece behind the small room): an L on the plan.
                    s = g[0]
                    need = ROOM_MIN_WIDTH_M - s["w"]
                    left = next((n for n in zs if n is not s and abs(n["x"] + n["w"] - s["x"]) < 0.03), None)
                    right = next((n for n in zs if n is not s and abs(s["x"] + s["w"] - n["x"]) < 0.03), None)
                    nb = max((n for n in (left, right) if n and n["w"] >= ROOM_MIN_WIDTH_M + need + 1.0), key=lambda n: n["w"], default=None)
                    if nb is None or need <= 0:
                        continue
                    ds = round(s["w"] * d / ROOM_MIN_WIDTH_M, 2)
                    outer_first = s.get("side") != "rear"
                    nb["w"] = round(nb["w"] - need, 2)
                    if nb is left:
                        s["x"] = round(nb["x"] + nb["w"], 2)
                    else:
                        nb["x"] = round(nb["x"] + need, 2)
                    s["w"], s["d"], s["y"] = ROOM_MIN_WIDTH_M, ds, (y if outer_first else round(y + d - ds, 2))
                    piece = dict(nb, x=s["x"], w=ROOM_MIN_WIDTH_M, y=(round(y + ds, 2) if outer_first else y), d=round(d - ds, 2))
                    piece.pop("entry", None)
                    for q in (nb, s, piece):
                        if "area_m2" in q:
                            q["area_m2"] = round(q["w"] * q["d"], 1)
                    fl["zones"].append(piece)
                    continue
                gx, gw = g[0]["x"], round(sum(q["w"] for q in g), 2)
                outer_first = g[0].get("side") != "rear"        # the street strip fills from the street, the lane strip from the lane
                at = y if outer_first else y + d
                for i, q in enumerate(g):
                    share = round(d * q["w"] / gw, 2) if i < len(g) - 1 else round((y + d - at) if outer_first else (at - y), 2)
                    q["x"], q["w"], q["d"] = gx, gw, share
                    q["y"] = round(at, 2) if outer_first else round(at - share, 2)
                    at = at + share if outer_first else at - share
            run = [z] if (z is not None and z["w"] < ROOM_MIN_WIDTH_M) else []


def _solve(site: dict, option: dict, ledger: dict, massing: dict, prog: dict, point: dict | None, across: bool = False) -> dict[str, Any]:
    """One arrangement of the plates: along a corridor (`point` None), or the point tower `_point_geometry` drew.
    `across`: the corridor run from the street to the lane. The plate is laid out turned a quarter (its depth taken as
    its width), where everything below holds as written, and the record is turned back at the end (`_turn_back`):
    the strip nearest the lot's left side is this frame's "front", and the street is at the low end of x."""
    pm, x0, y0, W, D, storeys, f2f = _plate(massing)
    if across:
        x0, y0, W, D = y0, x0, D, W
    corr, _ = LAYOUT_ASSUMPTIONS["corridor_width_m"]
    core_w, _ = LAYOUT_ASSUMPTIONS["core_bay_m"]
    warnings: list[str] = []
    if D < corr + 2 * 4.0:
        warnings.append(f"The plate is {D:.1f} m deep: too shallow for a double-loaded corridor (about 12 m); the units are drawn single-loaded on the street side and the depth is the limit.")
    strip = max(0.0, (D - corr) / 2) if D >= corr + 8.0 else max(0.0, D - corr)
    double = D >= corr + 8.0
    corr_y = y0 + strip if double else y0 + strip   # the corridor behind the front strip

    # the structural grid (option.layout.grid) and the cores the architect placed (option.layout.cores): with
    # neither, the layout is the one of 3 Nov 2026, a 7 m core bay at the centre and blocks as wide as their area
    grid = grid_of(option)
    mod = grid["module_m"] if grid else None
    given = _cores_of(option, x0, y0, W, D)

    def q(width: float) -> float:
        """A width on the grid's module, rounded up; as it is without a grid."""
        return math.ceil(width / mod - 1e-6) * mod if mod else width

    # On a double-loaded plate the core stands on the lane side of the corridor, and the street side's homes run past
    # it; a corridor longer than the core and two dead ends gets an exit stair at each end (17 Nov 2026: a full-depth
    # core took a third of a tower's floor, and one centred core left 22 m dead ends on a 51.5 m slab, against the
    # 6 m of BCBC 3.3.1.9: no floor of 3475 E Hastings St could pass). The architect's own cores stand as drawn.
    stair_w, _ = LAYOUT_ASSUMPTIONS["stair_width_m"]
    ev = (_find(ledger["results"], rule_id=EGRESS_RULE) or {}).get("values") or {}
    dead_lim = float(ev.get("dead_end_max_m") or 6.0)
    # the exits' separation the floor needs (3.4.2.3), as egress() reads it: half the diagonal, not more than 9 m
    sep_need = round(min(float(ev.get("separation_min_m") or 9.0), float(ev.get("separation_share_of_diagonal") or 0.5) * math.hypot(W, D)), 2)
    core_y, core_d = (corr_y, D - strip) if double else (y0, D)
    if given:
        cores = given
    else:
        cw = min(W, q(core_w)) if grid else core_w
        cx = x0 + (round(max(0.0, (W - cw) / 2) / mod) * mod if grid else (W - cw) / 2)
        cores = [{"x": cx, "y": core_y, "w": cw, "d": core_d}]
        sw = q(stair_w) if grid else stair_w
        if W > cw + 2 * dead_lim + 2 * sw:
            # on a grid the far stair stands on the last module line it fits behind, so its walls are on the module
            rx = x0 + (math.floor((W - sw) / mod + 1e-6) * mod if grid else W - sw)
            cores = [{"x": x0, "y": core_y, "w": sw, "d": core_d}] + cores + [{"x": rx, "y": core_y, "w": sw, "d": core_d}]
        else:
            # too short a corridor for a stair at each end (17 Nov 2026, a 19 × 21 m tower plate: the 7 m core's
            # stairs 4.8 m apart against 9 m, and the corridor 6.04 m past it against a 6 m dead end):
            # - a corridor running past the core further than a dead end may: the core grows until it does not;
            # - a tower whose core stairs would stand closer than 3.4.2.3 asks: a scissor stair, two stairs interlocked
            #   in one shaft along the corridor, their doors at its two ends the separation apart. Contiguous stairs
            #   are not permitted in a 5 or 6 storey wood-frame building (VBBL 2014 3.4.1.2.(3)), so only above six
            #   storeys; below, the deep core's front-and-rear arrangement stays the architect's to draw (egress()).
            want, scissor = cw, False
            if W - cw > 2 * dead_lim + 1e-6:
                want = W - 2 * dead_lim
            if storeys > MIDRISE_MAX_STOREYS and want - sw + 1e-6 < sep_need and sep_need + sw <= W + 1e-6:
                want, scissor = max(want, sep_need + sw), True
            if want > cw + 1e-6:
                cw = min(W, q(want)) if grid else min(W, round(want + 0.005, 2))
                cx = x0 + (round(max(0.0, (W - cw) / 2) / mod) * mod if grid else (W - cw) / 2)
                cores = [{"x": cx, "y": core_y, "w": cw, "d": core_d, **({"stairs": "scissor"} if scissor else {})}]
    def band_runs(side: str, y: float) -> list[dict]:
        """The runs one strip offers: the lengths of it the cores leave free, each filled outward from a core. A run
        lies along x (`edge` where it is filled from, `at` the strip's y, `depth` the strip's): see _run_rect."""
        run = lambda end, edge, d, length: {"side": side, "end": end, "axis": "x", "edge": edge, "dir": d, "at": y, "depth": strip, "len": length, "left": length}
        spans: list[list[float]] = []
        for c in sorted(cores, key=lambda c: c["x"]):
            if c["y"] < y + strip - 0.05 and c["y"] + c["d"] > y + 0.05:
                if spans and c["x"] <= spans[-1][1] + 1e-6:
                    spans[-1][1] = max(spans[-1][1], c["x"] + c["w"])
                else:
                    spans.append([c["x"], c["x"] + c["w"]])
        if not spans:
            return [run("left", x0, 1, W)]
        out = [run("left", spans[0][0], -1, max(0.0, spans[0][0] - x0))]
        for a, b in zip(spans, spans[1:]):
            out.append(run("mid", a[1], 1, max(0.0, b[0] - a[1])))
        out.append(run("right", spans[-1][1], 1, max(0.0, x0 + W - spans[-1][1])))
        return out

    walkup = bool(point) and point.get("kind") == "walkup"
    if walkup:
        warnings = [w for w in warnings if "double-loaded corridor" not in w]
        warnings.append(f"A walk-up: one stair of {point['stair_m'][0]:g} × {point['stair_m'][1]:g} m on the street side and no elevator, every home the plate's full depth "
                        + ("either side of the stair" if point["homes_per_floor"] == 2 else "beside the stair, one a floor")
                        + ", its door on the landing; no indoor amenity room and services of "
                        + f"{WALKUP_ASSUMPTIONS['walkup_services_m2'][0]:g} m² (placeholders for a building this small). Part 9 of the BC Building Code covers a residential "
                        + f"building of at most {WALKUP_MAX_STOREYS} storeys and {WALKUP_MAX_PLATE_M2:,.0f} m² of building area (bc.code_basis); one exit is taken to serve a floor "
                        + "of at most 150 m² with an occupant load of at most 60 (bcbc.exits, 3.4.2.1, a Part 3 figure). Part 9's own exit clauses (9.9.8) are not in the rules: "
                        + "whether one stair serves these floors is a placeholder to confirm against the code.")
    floors: list[dict] = []
    for lv in range(storeys):
        if walkup:
            # the walk-up: the stair and its landing stand in the same place on every floor, the homes beside them
            floors.append({"level": lv, "name": "Ground floor" if lv == 0 else f"Level {lv + 1}", "z": _floor_z(option, lv, f2f),
                           "zones": [dict(z) for z in point["zones"]], "runs": [dict(r) for r in point["runs"]], "spare_m2": 0.0})
            continue
        if point:
            # the point tower: its core, the ring round it, and the four strips of homes round that
            zones = [dict(point["core"]), *(dict(z) for z in point["ring"])]
            runs = [dict(r) for r in point["runs"]]
            floors.append({"level": lv, "name": "Ground floor" if lv == 0 else f"Level {lv + 1}", "z": _floor_z(option, lv, f2f), "zones": zones, "runs": runs, "spare_m2": 0.0})
            continue
        zones = [{"block": "core", "label": BLOCK_LABEL["core"], "x": round(c["x"], 2), "y": round(c["y"], 2), "w": round(c["w"], 2), "d": round(c["d"], 2), "area_m2": round(c["w"] * c["d"], 1),
                  **({"stairs": "scissor"} if c.get("stairs") == "scissor" else {})} for c in cores]
        zones.append({"block": "corridor", "label": "Corridor", "x": round(x0, 2), "y": round(corr_y, 2), "w": round(W, 2), "d": corr, "area_m2": round(W * corr, 1), "through": "core"})
        # the runs a floor offers: on the street side, then (a double-loaded plate) on the lane side
        runs = band_runs("front", y0)
        if double:
            runs += band_runs("rear", corr_y + corr)
        floors.append({"level": lv, "name": "Ground floor" if lv == 0 else f"Level {lv + 1}", "z": _floor_z(option, lv, f2f), "zones": zones, "runs": runs, "spare_m2": 0.0})

    min_room, _ = LAYOUT_ASSUMPTIONS["min_room_width_m"]
    trimmed: list[tuple[str, float]] = []

    def place(floor: dict, block: str, label: str, area: float, prefer: list[tuple[str, str]], extra: dict | None = None, at: str | None = None, whole: float | None = None) -> float:
        """Put `area` of a block into the floor's runs, preferring the named (side, end) runs; returns what did not fit.
        `at` (the corridor across the plate only): "street" or "lane", the end of a strip the room must stand at; the
        runs that reach that end are taken first, and the room is put at that end of them."""
        left = area
        order = [r for p in prefer for r in floor["runs"] if (r["side"], r["end"]) == p] + [r for r in floor["runs"] if (r["side"], r["end"]) not in prefer]
        ends: dict[int, bool] = {}       # id(run) -> whether the room goes at the run's far end
        if across and at:
            def reach(r: dict) -> bool | None:
                lo = r["edge"] if r["dir"] > 0 else r["edge"] - r["len"]
                hi = r["edge"] + r["len"] if r["dir"] > 0 else r["edge"]
                if at == "street" and abs(lo - x0) < 0.05:
                    return r["dir"] < 0          # filled toward the street: its far end; filled from the street: its near end
                if at == "lane" and abs(hi - (x0 + W)) < 0.05:
                    return r["dir"] > 0
                return None
            near = [r for r in floor["runs"] if reach(r) is not None]
            ends = {id(r): bool(reach(r)) for r in near}
            order = near + [r for r in order if id(r) not in ends]
        for r in order:
            if left <= 0.05:
                break
            if r["left"] <= 0.05:
                continue
            width = min(r["left"], q(left / r["depth"])) if r["depth"] else 0
            if width <= 0.05:
                continue
            # the tail of a room that already has its main piece is not drawn as a sliver in another run (23 Nov 2026:
            # an amenity room 0.86 m wide): the room is that much smaller, and the warning says by how much
            if left < (whole or area) - 0.05 and width < min_room and block in ("amenity", "services", "design_space"):
                trimmed.append((label, round(left, 1)))
                left = 0.0
                break
            far = ends.get(id(r), False)
            x, y, w, d = _far_rect(r, width) if far else _run_rect(r, width)
            z = {"block": block, "label": label, "x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "d": round(d, 2), "area_m2": round(width * r["depth"], 1), "side": r["side"]}
            if extra:
                z.update(extra)
            floor["zones"].append(z)
            if far:
                r["far"] = r.get("far", 0.0) + width
            r["left"] -= width
            left -= width * r["depth"]
        return max(0.0, left)

    shortfall: list[dict] = []
    by_key = {b["key"]: b for b in prog["blocks"]}
    ground = floors[0]
    # the entry: a lobby on the street side of the ground floor (23 Nov 2026: a building with a shop across its whole
    # front had no way in, and the entry arrow pointed into the shop). Not in a walk-up, whose stair is its entry.
    lobby_m2, _ = LAYOUT_ASSUMPTIONS["lobby_m2"]
    if not walkup and prog["units_total"] and (strip or point) and not prog.get("no_lobby"):
        place(ground, "design_space", "Lobby (entry)", lobby_m2, [("front", "left"), ("front", "right")], {"entry": True}, at="street")
    # a brief's space that belongs beside the entry (a staffed desk) comes straight after the lobby, so it stands by it
    for b in [b for b in prog["blocks"] if b["key"] == "other" and b.get("next_to") == "entry"]:
        rest = place(ground, "other", b["label"], b["area_m2"], [("front", "left"), ("front", "right")], at="street")
        if rest > 0.05:
            shortfall.append({"block": "other", "label": b["label"], "area_m2": round(rest, 1)})
    # the ground floor's other uses, by their rules
    for key, prefer in (("non_residential", [("front", "left"), ("front", "right")]), ("amenity", [("front", "right"), ("front", "left")]), ("services", [("rear", "left"), ("rear", "right"), ("rear", "mid")])):
        b = by_key.get(key)
        if not b:
            continue
        rest = b["area_m2"]
        # a ground floor that is full spills upward, and the check will say so; except the services, which go below
        # grade with the parking instead of onto a floor of homes (23 Nov 2026: bicycle storage on level 2)
        for fl in (floors[:1] if key == "services" else floors):
            rest = place(fl, key, b["label"], rest, prefer, at="lane" if key == "services" else "street", whole=b["area_m2"])
            if rest <= 0.05:
                break
        if rest > 0.05 and key == "services":
            warnings.append(f"{rest:,.0f} m² of the services and bicycle storage do not fit on the ground floor; they are taken below grade with the parking, which is not on the plates.")
        elif rest > 0.05:
            shortfall.append({"block": key, "label": b["label"], "area_m2": round(rest, 1)})
    # the architect's own programs go on the ground floor facing the street, like the non-residential space
    for b in [b for b in prog["blocks"] if b["key"] == "other" and b.get("next_to") != "entry"]:
        rest = b["area_m2"]
        for fl in (floors[1:] + floors[:1] if b.get("where") == "upper" and len(floors) > 1 else floors):
            rest = place(fl, "other", b["label"], rest, [("front", "left"), ("front", "right")], at="street")
            if rest <= 0.05:
                break
        if rest > 0.05:
            shortfall.append({"block": "other", "label": b["label"], "area_m2": round(rest, 1)})

    # units: each one whole, in the first run with room for it, family units lowest and studios highest; the
    # accessible ones are the first placed, so they sit nearest the core on the lowest residential floor
    def unit_width(b: dict, depth: float) -> float:
        """How long a unit runs along a strip of this depth: its gross area over the depth; on a grid the nearest
        whole number of modules, as long as that keeps it at or over the BC Housing minimum with its partitions,
        otherwise the next module up."""
        width = b["gross_m2_each"] / depth
        # never narrower than the home's minimum width, nor so narrow that it is more than UNIT_DEPTH_RATIO_MAX times
        # as deep as it is wide (declared placeholders; 23 Nov 2026: on a 12 m strip a studio came out 3.2 m wide)
        # A walk-up's homes run the plate's full depth, lit at both ends: a different home, not held to these.
        least = 0.0 if walkup else max(float(b.get("min_width_m") or 0), depth / UNIT_DEPTH_RATIO_MAX)
        if mod:
            near = max(1, round(width / mod)) * mod
            width = near if near * depth + 0.5 >= b["min_gross_m2_each"] and near + 1e-6 >= least else q(max(width, least))
        else:
            width = max(width, least)
        return width

    def place_unit(key: str, b: dict, flagged: bool) -> bool:
        for fl in floors:
            runs = sorted(fl["runs"], key=lambda r: (r["side"] != "front", r["end"] != "left"))
            for r in runs:
                if r["depth"] <= 0:
                    continue
                # a walk-up's run holds the one home whose door is on the landing
                if r.get("max_units") is not None and r.get("units", 0) >= r["max_units"]:
                    continue
                width = unit_width(b, r["depth"])   # a point tower's strips differ in depth, so per run
                if r["left"] + 1e-9 < width:
                    continue
                x, y, w, d = _run_rect(r, width)
                fl["zones"].append({"block": key, "label": UNIT_LABEL[key], "x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "d": round(d, 2),
                                    "area_m2": round(width * r["depth"], 1), "side": r["side"], "unit": key, "accessible": flagged})
                r["left"] -= width
                r["units"] = r.get("units", 0) + 1
                return True
        return False

    for label, m2 in trimmed:
        warnings.append(f"{label}: {m2:g} m² less than its brief, a leftover too narrow to be a room ({min_room:g} m).")

    def by_floor() -> list[dict]:
        """The homes placed floor by floor, each whole in the first run with room: family homes lowest, studios highest
        (the arrangement of 3 Nov 2026). Returns the homes that did not fit, as shortfall rows."""
        short: list[dict] = []
        accessible_left = int(prog.get("accessible_units", option.get("accessible_units")) or 0)
        for key in UNIT_KEYS:
            b = by_key.get(key)
            if not b or not (strip or point):
                continue
            for _ in range(b["count"]):
                flagged = accessible_left > 0
                if place_unit(key, b, flagged):
                    if flagged:
                        accessible_left -= 1
                    continue
                sf = next((s for s in short if s["block"] == key), None)
                if sf:
                    sf["units"] += 1
                    sf["area_m2"] = round(sf["area_m2"] + b["gross_m2_each"], 1)
                else:
                    short.append({"block": key, "label": UNIT_LABEL[key], "units": 1, "area_m2": b["gross_m2_each"]})
        return short

    def in_bays() -> list[dict]:
        """The homes stacked in bays (23 Nov 2026, from an architect's test: three-bedrooms under two-bedrooms under
        one-bedrooms put no party wall or wet wall over another). Floors that offer the same runs share one plan: its
        slots are filled in the program's proportions, largest homes first, and the same home type stands in the same
        slot on every floor above. Where the program runs out of a type before the top, the slot takes a smaller home
        that fits, its near wall on the same line, or stays spare. Homes still left are placed wherever room remains."""
        left = {k: (by_key[k]["count"] if k in by_key else 0) for k in UNIT_KEYS}
        if not (strip or point) or not sum(left.values()):
            return []
        accessible_left = int(prog.get("accessible_units", option.get("accessible_units")) or 0)
        order = lambda fl: sorted(range(len(fl["runs"])), key=lambda i: (fl["runs"][i]["side"] != "front", fl["runs"][i]["end"] != "left"))
        sig = lambda fl: tuple((r["side"], r["end"], r["axis"], round(r["left"], 2), round(r.get("far", 0.0), 2), round(r["depth"], 2)) for r in fl["runs"])
        groups: list[list[dict]] = []
        for fl in floors:
            if groups and sig(groups[-1][0]) == sig(fl):
                groups[-1].append(fl)
            else:
                groups.append([fl])
        floors_left = len(floors)
        for group in groups:
            first = group[0]
            # the plan of this group of floors: per run, the slots [(home type, offset from where the run starts filling, width)]
            plan: list[tuple[int, str, float, float]] = []
            count = {k: 0 for k in UNIT_KEYS}
            for i in order(first):
                r = first["runs"][i]
                if r["depth"] <= 0:
                    continue
                at, room = r["len"] - r["left"] - r.get("far", 0.0), r["left"]
                while True:
                    # the home type the floors still owe most of, a floor, that fits what is left of the run
                    want = [(left[k] / floors_left - count[k], -UNIT_KEYS.index(k), k) for k in UNIT_KEYS
                            if left[k] / floors_left - count[k] > 1e-9 and unit_width(by_key[k], r["depth"]) <= room + 1e-9]
                    if not want:
                        break
                    # the largest of them first: where the plates run short, it is the small homes that go without a
                    # bay, as when the homes were placed floor by floor, never the family homes
                    k = min(want, key=lambda t: UNIT_KEYS.index(t[2]))[2]
                    w = unit_width(by_key[k], r["depth"])
                    plan.append((i, k, at, w))
                    count[k] += 1
                    at, room = at + w, room - w
            for fl in group:
                ends: dict[int, float] = {}
                for bay, (i, k, at, w) in enumerate(plan):
                    r = fl["runs"][i]
                    key = k if left[k] > 0 else next((s for s in UNIT_KEYS if left[s] > 0 and unit_width(by_key[s], r["depth"]) <= w + 1e-9), None)
                    if key is None:
                        continue      # nothing left that fits this bay on this floor: it stays spare
                    uw = unit_width(by_key[key], r["depth"])
                    s = r["edge"] + r["dir"] * at + (0 if r["dir"] > 0 else -uw)
                    x, y, zw, zd = (s, r["at"], uw, r["depth"]) if r["axis"] == "x" else (r["at"], s, r["depth"], uw)
                    flagged = accessible_left > 0
                    fl["zones"].append({"block": key, "label": UNIT_LABEL[key], "x": round(x, 2), "y": round(y, 2), "w": round(zw, 2), "d": round(zd, 2),
                                        "area_m2": round(uw * r["depth"], 1), "side": r["side"], "unit": key, "accessible": flagged, "bay": f"{i}.{bay}"})
                    if flagged:
                        accessible_left -= 1
                    left[key] -= 1
                    if uw < w - 0.3:      # a smaller home in a larger bay: the rest of the bay is spare, drawn so
                        gs = r["edge"] + r["dir"] * (at + uw) + (0 if r["dir"] > 0 else -(w - uw))
                        gx, gy, gw, gd = (gs, r["at"], w - uw, r["depth"]) if r["axis"] == "x" else (r["at"], gs, r["depth"], w - uw)
                        fl["zones"].append({"block": "spare", "label": "Spare", "x": round(gx, 2), "y": round(gy, 2), "w": round(gw, 2), "d": round(gd, 2),
                                            "area_m2": round((w - uw) * r["depth"], 1), "side": r["side"]})
                        fl["gap_m2"] = fl.get("gap_m2", 0.0) + (w - uw) * r["depth"]
                    ends[i] = max(ends.get(i, 0.0), at + w)
                # what a run has left is what lies past its last bay, used or not, so the bays above stay aligned
                last = {i: max(at + w for j, _, at, w in plan if j == i) for i in {j for j, *_ in plan}}
                for i, end in last.items():
                    fl["runs"][i]["left"] = max(0.0, fl["runs"][i]["len"] - end - fl["runs"][i].get("far", 0.0))
                    fl["runs"][i]["units"] = sum(1 for j, *_ in plan if j == i)
                floors_left -= 1
        # the homes the bays did not take go wherever a run still has room, as before; the rest did not fit
        short: list[dict] = []
        for key in UNIT_KEYS:
            for _ in range(left[key]):
                flagged = accessible_left > 0
                if place_unit(key, by_key[key], flagged):
                    if flagged:
                        accessible_left -= 1
                    continue
                sf = next((s for s in short if s["block"] == key), None)
                if sf:
                    sf["units"] += 1
                    sf["area_m2"] = round(sf["area_m2"] + by_key[key]["gross_m2_each"], 1)
                else:
                    short.append({"block": key, "label": UNIT_LABEL[key], "units": 1, "area_m2": by_key[key]["gross_m2_each"]})
        return short

    # Both arrangements are laid out on the same floors. The bays are kept unless they cost more than a home or 2% of
    # the program, whichever is more: walls and wet walls that line up are worth a home at a first layout, and the
    # warning says what the other arrangement would hold. The plate says which it is.
    import copy
    stacking = "by floor"
    if walkup:
        shortfall += by_floor()
    else:
        before = copy.deepcopy(floors)
        short_floor = by_floor()
        placed_floor = sum(1 for fl in floors for z in fl["zones"] if z.get("unit"))
        result_floor = floors
        floors = before
        short_bays = in_bays()
        placed_bays = sum(1 for fl in floors for z in fl["zones"] if z.get("unit"))
        if placed_bays >= placed_floor - max(1, round(0.02 * prog["units_total"])):
            shortfall += short_bays
            stacking = "bays"
            if placed_bays < placed_floor:
                warnings.append(f"The homes are stacked in bays, the same type above the same type; placed floor by floor with nothing lined up, the plates would hold {placed_floor} homes against {placed_bays}.")
        else:
            floors = result_floor
            shortfall += short_floor
            warnings.append(f"The homes are placed floor by floor, not stacked in bays: stacked, the plates held {placed_bays} homes against {placed_floor}.")

    # what is left on each floor is spare, drawn white
    for fl in floors:
        spare = fl.pop("gap_m2", 0.0)
        for r in fl["runs"]:
            if r["left"] > 0.3:
                x, y, w, d = _run_rect(r, r["left"])
                fl["zones"].append({"block": "spare", "label": "Spare", "x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "d": round(d, 2), "area_m2": round(r["left"] * r["depth"], 1), "side": r["side"]})
                spare += r["left"] * r["depth"]
        fl["spare_m2"] = round(spare, 1)
        del fl["runs"]
        _square_small_rooms(fl)

    plate = {"x": round(x0, 2), "y": round(y0, 2), "width_m": round(W, 2), "depth_m": round(D, 2), "storeys": storeys, "floor_to_floor_m": f2f, "double_loaded": double, "unit_depth_m": round(strip, 2),
             "arrangement": "double" if double else "single", "stacking": stacking}
    if walkup:
        plate.update(arrangement="walkup", double_loaded=False, unit_depth_m=round(D, 2), walkup={"layout": point["layout"], "stair_m": point["stair_m"],
                                                                                                 "homes_per_floor": point["homes_per_floor"]})
    elif point:
        # the homes' depth in front of and behind the ring (`unit_depth_m`, as the editor's street strip reads it)
        # and beside it (`side_depth_m`)
        plate.update(arrangement="point", double_loaded=False, unit_depth_m=round(point["uy"], 2), side_depth_m=round(point["ux"], 2), core_m=point["core_m"])
    if grid:
        plate["grid"] = grid
    deep_max, _ = LAYOUT_ASSUMPTIONS["max_home_depth_m"]
    if not point and strip > deep_max + 0.05 and any(z.get("unit") for fl in floors for z in fl["zones"]):
        warnings.append(f"The homes are {strip:.1f} m deep from their window wall, deeper than the {deep_max:g} m daylight is taken to reach: a plate this deep wants a courtyard or a narrower bar, "
                        "and the homes counted here are not ones anyone would build.")
    if ground_extra(option, f2f):
        plate["ground_floor_m"] = round(f2f + ground_extra(option, f2f), 2)
    L = _assemble(site, option, ledger, massing, prog, plate, floors, shortfall, warnings, edited=False, geometry=[])
    return _turn_back(L, option) if across else L


def _turn_back(L: dict, option: dict) -> dict:
    """A layout solved with the plate turned a quarter (`_solve`, `across`), put back in the plate's own frame: every
    zone's x and y swapped, each zone's side read again from where it stands (the street half of the plate is the
    front), the farthest unit's door and exit swapped, and the adjacency rules read back from the plan as it now
    stands. The exits were measured in the turned frame, where the corridor runs along x, and stand as measured."""
    p = L["plate"]
    p["x"], p["y"], p["width_m"], p["depth_m"] = p["y"], p["x"], p["depth_m"], p["width_m"]
    p.update(arrangement="cross", corridor="across")      # unit_depth_m stays: the homes' depth from their window wall, now measured across the plate
    mid = p["y"] + p["depth_m"] / 2
    for fl in L["floors"]:
        fl["zones"] = [_t(z) for z in fl["zones"]]
        for z in fl["zones"]:
            z["side"] = "front" if z["y"] + z["d"] / 2 < mid else "rear"
    for f in ((L.get("egress") or {}).get("floors") or []):
        u = f.get("farthest_unit")
        if u:
            u["x"], u["y"] = u["y"], u["x"]
            u["door"], u["exit"] = [u["door"][1], u["door"][0]], [u["exit"][1], u["exit"][0]]
    prog = {"blocks": L["program"], "units_total": L["units_total"]}
    L["adjacencies"] = [_check(rule, L["floors"], prog, L["shortfall"]) for rule in adjacencies_for(option)]
    L["warnings"].insert(0, f"The corridor runs across the plate, from the street to the lane: the plate is {p['depth_m']:g} m deep and {p['width_m']:g} m wide, and a corridor "
                            "run back from the street places more homes, or as many with better exits, than one along the street.")
    return L


def _assemble(site, option, ledger, massing, prog, plate, floors, shortfall, warnings, edited, geometry) -> dict[str, Any]:
    """The layout record both paths return: the rules read back from the zones, the totals, the log."""
    checks = [_check(rule, floors, prog, shortfall) for rule in adjacencies_for(option)]
    placed_units = sum(1 for fl in floors for z in fl["zones"] if z.get("unit"))
    gross_plates = round(plate["width_m"] * plate["depth_m"] * plate["storeys"], 1)
    fsr_rule = _find(ledger["results"], check="district_outright_fsr")
    h_rule = _find(ledger["results"], check="district_outright_height")
    outright = {"fsr": (fsr_rule or {}).get("values", {}).get("max_fsr_outright"), "height_m": (h_rule or {}).get("values", {}).get("max_height_m_outright"),
                "rule_ids": [r["rule_id"] for r in (fsr_rule, h_rule) if r]}
    used = round(sum(z["area_m2"] for fl in floors for z in fl["zones"] if z["block"] not in ("spare", "void")), 1)
    cut = round(sum(z["area_m2"] for fl in floors for z in fl["zones"] if z["block"] == "void"), 1)
    light = daylight(floors, plate)
    if light["status"] != "pass":
        warnings = list(warnings) + [light["note"]]
    shape = proportions(floors, plate)
    if shape["status"] != "pass":
        warnings = list(warnings) + [shape["note"]]
    exits_rule = _find(ledger["results"], rule_id=EGRESS_RULE)
    sprk = option.get("sprinklered")
    if sprk is None:
        sprk = (option.get("layout") or {}).get("sprinklered")
    eg = None
    if exits_rule and exits_rule.get("version_effective_from") and exits_rule.get("values"):
        eg = egress(floors, plate, prog, exits_rule["values"], SPRINKLERED_DEFAULT if sprk is None else bool(sprk))
        eg["sprinklered_is_placeholder"] = sprk is None
    turned = next((x.get("angle_deg") for x in massing["masses"] if x["name"] == "proposed"), None)
    if turned:
        plate["angle_deg"] = turned   # the mass is turned on the lot; the plate and its blocks are drawn in the plate's own frame
    plate.setdefault("building_type", building_type(option))
    L = {
        "site_id": site.get("id"), "option_id": option.get("id"), "as_of": ledger["run"]["as_of"], "stamp": ledger["run"]["stamp"]["stamp"],
        "units": "m", "origin": massing.get("origin"), "edited": edited,
        "plate": plate,
        "program": prog["blocks"], "parking": prog["parking"], "units_total": prog["units_total"], "units_placed": placed_units,
        "adjacencies": checks, "geometry": geometry, "egress": eg, "floors": floors, "shortfall": shortfall, "outright": outright,
        "capacity": capacity(site, massing, outright, cut),
        "daylight": light, "proportions": shape,
        "totals": {"plates_m2": gross_plates, "used_m2": used, "spare_m2": round(gross_plates - used - cut, 1), "gfa_m2": massing["masses"][0].get("gfa_m2"),
                   **({"void_m2": cut, "floor_area_m2": round(gross_plates - cut, 1)} if cut else {})},
        "assumptions": prog["assumptions"], "warnings": warnings + list(massing.get("warnings") or []),
        "derived_from": (["option.layout.zones (placed by hand)"] if edited else []) + (["option.layout.grid"] if plate.get("grid") else []) + ["option.units", "option.non_residential_gfa_m2", "option.accessible_units", "option.bicycle_spaces", "massing.masses[proposed]", "bch.design_guidelines.unit_areas"],
    }
    L["area_schedule"] = area_schedule(L)
    L["operability"] = operability(L, option)
    if L["area_schedule"]["flag"]:
        L["warnings"].append(f"The homes are {L['area_schedule']['totals']['efficiency'] * 100:.0f}% of the floor area (net to gross), under the {int(EFFICIENCY_FLOOR * 100)}% this screen flags: "
                             "cores, corridors or spare floor take more than a cost consultant would expect.")
    return L


# ---------------------------------------------------------------- how deep the homes run from their windows

# A declared placeholder, not a rule: past about this depth from its window wall a home has rooms without daylight.
# It stands in for the daylight study an architect makes; the layout says how many homes pass it, never fails on it.
UNIT_DEPTH_MAX_M = 10.0


def _wide_deep(z: dict, x0: float, y0: float, W: float, D: float, tol: float = 0.06) -> tuple[float, float]:
    """A home's width along its window wall and its depth from it: the wall is the street or lane side of the plate
    where the home stands on one (width along x), else a side of the plate (width along y), else its longer side; a
    home from the street side through to the lane side is lit at both ends and reads half its depth."""
    along_x = z["y"] <= y0 + tol or z["y"] + z["d"] >= y0 + D - tol
    along_y = z["x"] <= x0 + tol or z["x"] + z["w"] >= x0 + W - tol
    wide, deep = (z["w"], z["d"]) if along_x or not along_y else (z["d"], z["w"])
    if along_x and z["y"] <= y0 + tol and z["y"] + z["d"] >= y0 + D - tol:
        deep = deep / 2
    if not along_x and not along_y:
        wide, deep = max(z["w"], z["d"]), min(z["w"], z["d"])
    return wide, deep


def proportions(floors: list[dict], plate: dict) -> dict[str, Any]:
    """Every home's width along its window wall against the minimum for its type (UNIT_MIN_WIDTH_M), and its depth
    against UNIT_DEPTH_RATIO_MAX times that width. The window wall is the plate edge the home stands on: the street
    or lane side (its width runs along x), else a side of the plate (its width runs along y); a home on no edge is
    read on its longer side. Counted and said in `note`; conditional where any home is under, never a failure. Pure."""
    x0, y0, W, D = float(plate["x"]), float(plate["y"]), float(plate["width_m"]), float(plate["depth_m"])
    tol = 0.06
    narrow: list[tuple[str, float, float]] = []
    slender: list[float] = []
    # a walk-up's through homes and ground-oriented homes over several floors (their width is a townhouse's) are not held to these
    for fl in ([] if plate.get("arrangement") in ("walkup", "ground_oriented") else floors):
        for z in fl["zones"]:
            if not z.get("unit"):
                continue
            wide, deep = _wide_deep(z, x0, y0, W, D)
            least = UNIT_MIN_WIDTH_M.get(z["unit"])
            if least and wide + 0.05 < least:
                narrow.append((z["unit"], wide, least))
            if wide > 0 and deep / wide > UNIT_DEPTH_RATIO_MAX + 0.01:
                slender.append(deep / wide)
    bits = []
    if narrow:
        worst = min(narrow, key=lambda n: n[1] - n[2])
        bits.append(f"{len(narrow)} home{'s' if len(narrow) != 1 else ''} {'is' if len(narrow) == 1 else 'are'} narrower than the minimum for {'its' if len(narrow) == 1 else 'their'} type "
                    f"(the narrowest against its minimum: a {UNIT_LABEL[worst[0]].lower()} {worst[1]:.1f} m wide, {worst[2]:g} m asked)")
    if slender:
        bits.append(f"{len(slender)} home{'s' if len(slender) != 1 else ''} {'is' if len(slender) == 1 else 'are'} more than {UNIT_DEPTH_RATIO_MAX:g} times as deep as wide (up to {max(slender):.1f} times)")
    return {"min_width_m": dict(UNIT_MIN_WIDTH_M), "depth_ratio_max": UNIT_DEPTH_RATIO_MAX, "narrow_units": len(narrow), "slender_units": len(slender),
            "status": "conditional" if bits else "pass",
            "note": ("Proportions (placeholders, not rules): " + "; ".join(bits) + ". Wider homes, or a shallower plate.") if bits else ""}


def daylight(floors: list[dict], plate: dict) -> dict[str, Any]:
    """Every home's depth from its window wall, read from the zones: the wall is a plate edge the home stands on, or
    an edge it shares with a cut-out (a courtyard, a notch); a home that runs from the street side through to the lane
    side is lit from both and reads half its depth. Homes deeper than UNIT_DEPTH_MAX_M, and homes with no window wall
    at all, are counted and said in `note`; `status` is conditional where there are any. Pure."""
    x0, y0, W, D = float(plate["x"]), float(plate["y"]), float(plate["width_m"]), float(plate["depth_m"])
    tol = 0.06
    deep: list[float] = []
    dark = 0
    for fl in floors:
        voids = [z for z in fl["zones"] if z["block"] == "void"]
        for z in fl["zones"]:
            if not z.get("unit"):
                continue
            front, rear = z["y"] <= y0 + tol, z["y"] + z["d"] >= y0 + D - tol
            left, right = z["x"] <= x0 + tol, z["x"] + z["w"] >= x0 + W - tol
            for v in voids:
                span_x = min(z["x"] + z["w"], v["x"] + v["w"]) - max(z["x"], v["x"])
                span_y = min(z["y"] + z["d"], v["y"] + v["d"]) - max(z["y"], v["y"])
                if span_x > 0.5 and abs(v["y"] + v["d"] - z["y"]) <= tol:
                    front = True
                if span_x > 0.5 and abs(z["y"] + z["d"] - v["y"]) <= tol:
                    rear = True
                if span_y > 0.5 and abs(v["x"] + v["w"] - z["x"]) <= tol:
                    left = True
                if span_y > 0.5 and abs(z["x"] + z["w"] - v["x"]) <= tol:
                    right = True
            depths = ([z["d"] / (2 if front and rear else 1)] if front or rear else []) + ([z["w"] / (2 if left and right else 1)] if left or right else [])
            if not depths:
                dark += 1
            elif min(depths) > UNIT_DEPTH_MAX_M + tol:
                deep.append(min(depths))
    bits = []
    if deep:
        bits.append(f"{len(deep)} home{'s' if len(deep) != 1 else ''} run{'s' if len(deep) == 1 else ''} {max(deep):.1f} m from the window wall, past the {UNIT_DEPTH_MAX_M:g} m a home is usually lit to")
    if dark:
        bits.append(f"{dark} home{'s' if dark != 1 else ''} {'has' if dark == 1 else 'have'} no wall on the outside of the plate or on a cut-out, so no window")
    return {"limit_m": UNIT_DEPTH_MAX_M, "deep_units": len(deep), "deepest_m": round(max(deep), 2) if deep else None, "no_window_wall": dark,
            "status": "conditional" if bits else "pass",
            "note": ("Daylight (a placeholder for the architect's study, not a rule): " + "; ".join(bits) + ". A shallower plate, a courtyard cut out of it, or wider homes.") if bits else ""}


# ---------------------------------------------------------------- the floor space ratio left for another level

def capacity(site: dict, massing: dict, outright: dict, void_m2: float = 0.0) -> dict | None:
    """How much floor area the FSR still leaves, and how many more levels of the proposed plate that is: against
    the rezoning policy's benchmark FSR where one fired (the massing's `policy_benchmark`), else the district
    schedule's outright maximum; `fsr_limit` is None where the rules carry neither. The block editor reads it
    before it lets the architect add a level to place the rest of the program. Pure."""
    pm = next((x for x in massing["masses"] if x["name"] == "proposed"), None)
    try:
        area = float(site.get("site_area_m2") or 0)
    except (TypeError, ValueError):
        area = 0.0
    if not pm or area <= 0 or not pm.get("plate_area_m2"):
        return None
    bench = massing.get("policy_benchmark") or {}
    limit = frm = rule_id = None
    if isinstance(bench.get("fsr"), (int, float)) and bench["fsr"] > 0:
        limit, frm, rule_id = float(bench["fsr"]), "the rezoning policy's benchmark", bench.get("rule_id")
    elif isinstance(outright.get("fsr"), (int, float)) and outright["fsr"] > 0:
        limit, frm, rule_id = float(outright["fsr"]), "the district schedule's outright maximum", (outright.get("rule_ids") or [None])[0]
    # the cut-outs the architect drew (`void` zones) are not floor area: they come off the plates' total
    gfa, plate = max(0.0, float(pm["gfa_m2"]) - float(void_m2 or 0)), float(pm["plate_area_m2"])
    room = None if limit is None else round(limit * area - gfa, 1)
    # the height beside it, read the same way: the benchmark's upper height where the policy fired, else the outright
    # maximum (23 Nov 2026: a level added on the FSR alone took a test scheme past the benchmark height unsaid)
    h_limit = h_from = None
    bh = bench.get("height_m")
    bh = max((v for v in bh if isinstance(v, (int, float))), default=None) if isinstance(bh, (list, tuple)) else bh
    if isinstance(bh, (int, float)) and bh > 0:
        h_limit, h_from = float(bh), "the rezoning policy's benchmark"
    elif isinstance(outright.get("height_m"), (int, float)) and outright["height_m"] > 0:
        h_limit, h_from = float(outright["height_m"]), "the district schedule's outright maximum"
    height = {"height_m": float(pm["height_m"]), "height_limit_m": h_limit, "height_from": h_from,
              "height_with_one_more": round(float(pm["height_m"]) + float(pm.get("floor_to_floor_m") or 0), 2)} if pm.get("height_m") else {}
    return {**height, "site_area_m2": area, "storeys": pm["storeys"], "plate_m2": plate, "gfa_m2": gfa, "fsr": round(gfa / area, 3),
            "fsr_limit": limit, "limit_from": frm, "rule_id": rule_id, "room_m2": room,
            "levels_room": None if limit is None else max(0, int((room + 0.5) // plate)),
            "fsr_with_one_more": round((gfa + plate) / area, 3), **({"void_m2": round(float(void_m2), 1)} if void_m2 else {})}


# ---------------------------------------------------------------- egress, read back from the plates

EGRESS_RULE = "bcbc.exits"
_STATUS_RANK = {"pass": 0, "conditional": 1, "uncertain": 2, "fail": 3}


def _corridor_frame(c: dict) -> dict:
    """A corridor as its axis ("x" or "y", the longer side), its span along the axis and its centreline."""
    if c["w"] >= c["d"]:
        return {"axis": "x", "a0": c["x"], "a1": c["x"] + c["w"], "c0": c["y"] + c["d"] / 2, "zone": c}
    return {"axis": "y", "a0": c["y"], "a1": c["y"] + c["d"], "c0": c["x"] + c["w"] / 2, "zone": c}


def _touches(a: dict, b: dict, tol: float = 0.05) -> bool:
    return not (a["x"] + a["w"] < b["x"] - tol or b["x"] + b["w"] < a["x"] - tol or a["y"] + a["d"] < b["y"] - tol or b["y"] + b["d"] < a["y"] - tol)


def _ringed(core: dict, corridors: list[dict], tol: float = 0.05) -> bool:
    """Whether a corridor runs round a core: along both its left and right faces, and across its front or rear from
    one to the other (a point tower's ring). Pure."""
    over_y = lambda z: z["y"] < core["y"] + core["d"] - tol and z["y"] + z["d"] > core["y"] + tol
    left = any(abs(z["x"] + z["w"] - core["x"]) <= tol and over_y(z) for z in corridors)
    right = any(abs(z["x"] - (core["x"] + core["w"])) <= tol and over_y(z) for z in corridors)
    across = any(z["x"] <= core["x"] + tol and z["x"] + z["w"] >= core["x"] + core["w"] - tol
                 and (abs(z["y"] + z["d"] - core["y"]) <= tol or abs(z["y"] - (core["y"] + core["d"])) <= tol) for z in corridors)
    return left and right and across


def _gap(a: dict, b: dict) -> float:
    dx = max(0.0, b["x"] - (a["x"] + a["w"]), a["x"] - (b["x"] + b["w"]))
    dy = max(0.0, b["y"] - (a["y"] + a["d"]), a["y"] - (b["y"] + b["d"]))
    return dx + dy


def egress(L_floors: list[dict], plate: dict, prog: dict, params: dict, sprinklered: bool) -> dict[str, Any]:
    """The exits, read on the plan as it stands. A plate whose corridor runs across it (`plate.corridor` "across") is
    read turned a quarter, where the corridor lies along x as `_egress_along` expects, and the farthest unit's door and
    exit are turned back; every figure is a distance, so none changes."""
    if plate.get("corridor") != "across":
        return _egress_along(L_floors, plate, prog, params, sprinklered)
    turned = [{**fl, "zones": [_t(z) for z in fl["zones"]]} for fl in L_floors]
    eg = _egress_along(turned, {**plate, "x": plate["y"], "y": plate["x"], "width_m": plate["depth_m"], "depth_m": plate["width_m"]}, prog, params, sprinklered)
    for f in eg.get("floors") or []:
        u = f.get("farthest_unit")
        if u:
            u["x"], u["y"] = u["y"], u["x"]
            u["door"], u["exit"] = [u["door"][1], u["door"][0]], [u["exit"][1], u["exit"][0]]
    return eg


def _egress_along(L_floors: list[dict], plate: dict, prog: dict, params: dict, sprinklered: bool) -> dict[str, Any]:
    """The exits on every floor against BCBC 2024 Div B Part 3 (rule `bcbc.exits`): how many exits the floor
    needs and has (3.4.2.1), how far apart they are (3.4.2.3), how far the farthest unit door is from an exit
    along the corridor (3.4.2.4, 3.4.2.5), and how far a corridor runs past the last exit (3.3.1.9). Exits are the
    `core` zones: a core at least one core bay wide is read as two stairs at its ends along x, a narrower one as
    one stair (stair width a declared placeholder); a scissor stair in a core the corridor rings (a point tower) as
    two doors on its opposite faces, apart by half its perimeter. Travel is measured from the midpoint of a unit's edge on its
    corridor, along the corridor's axis (Manhattan), to the nearest core's edge on that corridor. Pure."""
    stair_w, _ = LAYOUT_ASSUMPTIONS["stair_width_m"]
    bay, _ = LAYOUT_ASSUMPTIONS["core_bay_m"]
    area_cap = float(params.get("two_exits_over_floor_area_m2", 150))
    load_cap = float(params.get("two_exits_over_occupant_load", 60))
    sep_cap = float(params.get("separation_min_m", 9))
    sep_share = float(params.get("separation_share_of_diagonal", 0.5))
    travel_limit = float(params.get("travel_limit_sprinklered_m" if sprinklered else "travel_limit_unsprinklered_m", 45 if sprinklered else 30))
    dead_limit = float(params.get("dead_end_max_m", 6))
    per_room = float(params.get("occupant_load_persons_per_sleeping_room", 2))
    rooms = params.get("sleeping_rooms_by_unit") or {"studio": 1, "one_bed": 1, "two_bed": 2, "three_bed_plus": 3}
    W, D = float(plate["width_m"]), float(plate["depth_m"])
    floor_area = W * D
    diag = (W * W + D * D) ** 0.5
    sep_min = round(min(sep_cap, sep_share * diag), 2)
    limits = {"two_exits_over_floor_area_m2": area_cap, "two_exits_over_occupant_load": load_cap, "separation_min_m": sep_cap,
              "separation_share_of_diagonal": sep_share, "travel_limit_m": travel_limit,
              "travel_limit_sprinklered_m": params.get("travel_limit_sprinklered_m"), "travel_limit_unsprinklered_m": params.get("travel_limit_unsprinklered_m"),
              "dead_end_max_m": dead_limit, "occupant_load_persons_per_sleeping_room": per_room, "sleeping_rooms_by_unit": dict(rooms),
              "stair_width_m": stair_w, "core_bay_m": bay}

    out_floors: list[dict] = []
    for fl in L_floors:
        zones = [z for z in fl["zones"] if z["block"] != "spare"]
        cores = [z for z in zones if z["block"] == "core"]
        corridors = [_corridor_frame(z) for z in zones if z["block"] == "corridor"]
        units = [z for z in zones if z.get("unit")]
        load = sum(per_room * float(rooms.get(z["unit"], 1)) for z in units)
        required = 2 if (floor_area > area_cap + 1e-9 or load > load_cap + 1e-9) else 1
        # the stairs: two at the ends of a core a bay wide or wider, one in a narrower core; a scissor stair in a core
        # the corridor rings (a point tower) has its doors on the core's opposite faces, and the separation is the way
        # smoke would go between them, round the fire-separated core (3.4.2.3.(3)): half its perimeter
        stairs: list[tuple[float, float, int]] = []
        round_core: dict[int, float] = {}
        for i, c in enumerate(cores):
            cy = c["y"] + c["d"] / 2
            if c.get("stairs") == "scissor" and _ringed(c, [z for z in zones if z["block"] == "corridor"]):
                stairs += [(c["x"], cy, i), (c["x"] + c["w"], cy, i)]
                round_core[i] = c["w"] + c["d"]
            elif c["w"] + 1e-6 >= bay:
                stairs += [(c["x"] + stair_w / 2, cy, i), (c["x"] + c["w"] - stair_w / 2, cy, i)]
            else:
                stairs.append((c["x"] + c["w"] / 2, cy, i))
        rec = {"level": fl["level"], "name": fl["name"], "exits": len(stairs), "exits_required": required,
               "separation_m": None, "separation_min_m": sep_min if required >= 2 else None,
               "farthest_travel_m": None, "travel_limit_m": travel_limit, "farthest_unit": None,
               "dead_end_m": None, "dead_end_limit_m": dead_limit, "status": "pass", "notes": []}
        notes = rec["notes"]
        out_floors.append(rec)
        if not zones or (not units and not corridors and not cores):
            notes.append("nothing that needs an exit is placed on this floor: egress not measured")
            continue
        if not units and not corridors:
            notes.append("no units and no corridor on this floor: travel and dead ends not measured")
        statuses: list[str] = []
        if not cores:
            notes.append("no core on this floor, so no exit stair: egress cannot be read (the geometry list names it)")
            rec["status"] = "uncertain"
            continue
        # 3.4.2.1: the number of exits
        if len(stairs) < required:
            statuses.append("fail")
            why = f"the floor area is {floor_area:,.0f} m² (over {area_cap:.0f})" if floor_area > area_cap else f"the occupant load is {load:.0f} (over {load_cap:.0f})"
            notes.append(f"{len(stairs)} exit{'s' if len(stairs) != 1 else ''} where {required} are required: {why} (3.4.2.1)")
        # 3.4.2.3: the separation of the two exits farthest apart
        if len(stairs) >= 2:
            apart = lambda a, b: round_core[a[2]] if a[2] == b[2] and a[2] in round_core else ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
            best = max(((apart(a, b), a, b) for i, a in enumerate(stairs) for b in stairs[i + 1:]), key=lambda t: t[0])
            rec["separation_m"] = round(best[0], 2)
            if required >= 2 and best[0] + 1e-6 < sep_min:
                one = best[1][2] == best[2][2]
                c = cores[best[1][2]]
                if one and c["d"] - stair_w + 1e-6 >= sep_min:
                    statuses.append("conditional")
                    notes.append(f"the two stairs are {best[0]:.1f} m apart, under the {sep_min:g} m required (3.4.2.3), read as two {stair_w} m stairs at the ends of a {c['w']:g} m core; "
                                 f"the core runs {c['d']:.1f} m deep, so stairs at its front and rear ends could be {c['d'] - stair_w:.1f} m apart: an arrangement for the architect to draw")
                else:
                    statuses.append("fail")
                    notes.append(f"the exits are {best[0]:.1f} m apart, under the {sep_min:g} m required (3.4.2.3: half the {diag:.1f} m diagonal, not more than {sep_cap:g} m)")
        # travel distance and dead ends need a corridor
        if units and not corridors:
            notes.append("units but no corridor on this floor: travel distance and dead ends cannot be read (the geometry list names it)")
            rec["status"] = "uncertain"
            continue
        if corridors:
            dead = 0.0
            for cf in corridors:
                on = [c for c in cores if _touches(c, cf["zone"])]
                if not on:
                    dead = max(dead, cf["a1"] - cf["a0"])
                    notes.append(f"a corridor of {cf['a1'] - cf['a0']:.1f} m reaches no core: all of it is a dead end")
                    continue
                spans = [(c["x"], c["x"] + c["w"]) if cf["axis"] == "x" else (c["y"], c["y"] + c["d"]) for c in on]
                dead = max(dead, min(s[0] for s in spans) - cf["a0"], cf["a1"] - max(s[1] for s in spans))
            rec["dead_end_m"] = round(max(0.0, dead), 2)
            if rec["dead_end_m"] > dead_limit + 1e-6:
                statuses.append("fail")
                notes.append(f"the corridor runs {rec['dead_end_m']:.1f} m past the last exit, over the {dead_limit:g} m a dead end may be (3.3.1.9)")
        # 3.4.2.5: the farthest unit door from its nearest exit
        far = None
        for u in units:
            cf = min(corridors, key=lambda f: _gap(u, f["zone"]))
            if cf["axis"] == "x":
                da = u["x"] + u["w"] / 2
                dc = u["y"] + u["d"] if (u["y"] + u["d"] / 2) < cf["c0"] else u["y"]
                door = (da, dc)
            else:
                da = u["y"] + u["d"] / 2
                dc = u["x"] + u["w"] if (u["x"] + u["w"] / 2) < cf["c0"] else u["x"]
                door = (dc, da)
            best = None
            on = [c for c in cores if _touches(c, cf["zone"])]
            for c in on:
                lo, hi = (c["x"], c["x"] + c["w"]) if cf["axis"] == "x" else (c["y"], c["y"] + c["d"])
                ea = da if lo <= da <= hi else (lo if da < lo else hi)
                dist = abs(da - ea) + abs(dc - cf["c0"])
                pt = (ea, cf["c0"]) if cf["axis"] == "x" else (cf["c0"], ea)
                if best is None or dist < best[0]:
                    best = (dist, pt)
            if best is None:   # the unit's corridor reaches no core: the nearest core edge, Manhattan, as a fallback
                for c in cores:
                    ex = min(max(door[0], c["x"]), c["x"] + c["w"])
                    ey = min(max(door[1], c["y"]), c["y"] + c["d"])
                    dist = abs(door[0] - ex) + abs(door[1] - ey)
                    if best is None or dist < best[0]:
                        best = (dist, (ex, ey))
            if far is None or best[0] > far[0]:
                far = (best[0], u, door, best[1])
        if far:
            d_, u, door, ex = far
            rec["farthest_travel_m"] = round(d_, 2)
            rec["farthest_unit"] = {"block": u["block"], "x": u["x"], "y": u["y"], "door": [round(door[0], 2), round(door[1], 2)], "exit": [round(ex[0], 2), round(ex[1], 2)]}
            if d_ > travel_limit + 1e-6:
                statuses.append("fail")
                notes.append(f"the farthest unit door is {d_:.1f} m from an exit along the corridor, over the {travel_limit:g} m for a{' sprinklered' if sprinklered else 'n unsprinklered'} floor area (3.4.2.5)")
        elif not units and corridors:
            notes.append("no units on this floor: travel distance measured from unit doors only, the other uses' travel is not measured")
        rec["status"] = max(statuses, key=lambda s: _STATUS_RANK[s]) if statuses else "pass"

    if any(f["status"] == "fail" for f in out_floors):
        overall = "fail"
    elif any(f["status"] == "uncertain" for f in out_floors):
        overall = "uncertain"
    elif any(f["status"] == "conditional" for f in out_floors):
        overall = "conditional"
    else:
        overall = "pass"
    scissor = next(((fl, z) for fl in L_floors for z in fl["zones"] if z.get("block") == "core" and z.get("stairs") == "scissor"), None)
    words = None
    if scissor:
        fl, z = scissor
        if _ringed(z, [c for c in fl["zones"] if c["block"] == "corridor"]):
            words = (f"the core's two exits are a scissor stair, its doors on the core's opposite faces, {float(z['w']) + float(z['d']):.1f} m apart "
                     f"as smoke would go round the core (3.4.2.3.(3))")
        else:
            words = f"the core's two exits are a scissor stair, its doors {float(z['w']) - stair_w:.1f} m apart along the corridor"
    return {"rule_id": EGRESS_RULE, "sprinklered": bool(sprinklered), "sprinklered_is_placeholder": True, "limits": limits,
            "floors": out_floors, "status": overall, "scissor_stair": bool(scissor),
            "summary": _egress_summary(out_floors, overall, sprinklered, travel_limit, dead_limit, scissor_words=words)}


def _egress_summary(floors: list[dict], overall: str, sprinklered: bool, travel_limit: float, dead_limit: float,
                    scissor_words: str | None = None) -> str:
    n = {s: sum(1 for f in floors if f["status"] == s) for s in ("pass", "conditional", "fail", "uncertain")}
    counts = ", ".join(f"{v} {k}" for k, v in n.items() if v)
    bits = []
    short = [f for f in floors if any("(3.4.2.1)" in n for n in f["notes"])]
    if short:
        bits.append(f"too few exits on {len(short)} floor{'s' if len(short) != 1 else ''}")
    sep = [f for f in floors if f["separation_m"] is not None and f["separation_min_m"] is not None and f["separation_m"] + 1e-6 < f["separation_min_m"]]
    if sep:
        bits.append(f"exits {min(f['separation_m'] for f in sep):.1f} m apart, at least {sep[0]['separation_min_m']:g} m needed, on {len(sep)} floor{'s' if len(sep) != 1 else ''}")
    tr = [f["farthest_travel_m"] for f in floors if f["farthest_travel_m"] is not None]
    if tr:
        # every figure carries its unit and says which side of it the limit is (17 Nov 2026: "travel 30.1 m of 45")
        bits.append(f"farthest travel {max(tr):.1f} m, limit {travel_limit:g} m")
    de = [f["dead_end_m"] for f in floors if f["dead_end_m"] is not None]
    if de and max(de) > dead_limit + 1e-6:
        bits.append(f"dead-end corridors up to {max(de):.1f} m, limit {dead_limit:g} m")
    if scissor_words:
        # the arrangement that made the separation, and what it asks of the drawing (VBBL 2014 3.4.4.4.(2), (3))
        bits.append(f"{scissor_words}; the two stairs need a smoke-tight fire separation between them, rated as the floors, with no openings")
    return (f"Egress ({'sprinklered' if sprinklered else 'unsprinklered'}, BCBC 2024 Part 3): {overall}; {len(floors)} floor{'s' if len(floors) != 1 else ''}: {counts}"
            + (f"; {'; '.join(bits)}" if bits else "") + ".")


def egress_line(f: dict) -> str:
    """One floor's egress in a line: exits, travel, separation, dead end against their limits."""
    parts = [f"{f['exits']} exit{'s' if f['exits'] != 1 else ''}, {f['exits_required']} required"]
    if f["farthest_travel_m"] is not None:
        parts.append(f"travel {f['farthest_travel_m']:.1f} m, limit {f['travel_limit_m']:g} m")
    if f["separation_min_m"] is not None and f["separation_m"] is not None:
        parts.append(f"separation {f['separation_m']:.1f} m, at least {f['separation_min_m']:g} m")
    if f["dead_end_m"] is not None:
        parts.append(f"dead end {f['dead_end_m']:.1f} m, limit {f['dead_end_limit_m']:g} m")
    return " · ".join(parts) + f" · {f['status']}"


# ---------------------------------------------------------------- a placement drawn by hand, re-checked

# A declared placeholder: the least a core measures, each way, to hold an elevator and its lobby beside the stairs.
# The solver's own cores are a core bay (7 m) wide; its end stairs are a stair's width and read as stairs alone.
ELEVATOR_CORE_M = 5.0

# `design_space` (a lobby, an atrium), `commercial` and `void` (a cut-out: open to below, a notch, a courtyard) are
# the architect's own: no program asks for them, so they are measured and drawn but never short; a void is not
# floor area, so it comes off the floor area the FSR is read on (`capacity`) and is never spare.
EDITABLE_BLOCKS = ("studio", "one_bed", "two_bed", "three_bed_plus", "non_residential", "amenity", "services", "core", "corridor", "other",
                   "design_space", "commercial", "void")


def place_zones(site: dict, option: dict, ledger: dict, massing: dict, zones_by_level: dict | list) -> dict[str, Any]:
    """The block editor's placement: `zones_by_level` maps a level ("0", "1", …) to zones {block, x, y, w, d,
    accessible?}. The engine does not move anything: it measures every zone, reads the rules back, and lists
    what broke (a zone outside the plate, two zones overlapping, a unit smaller than its area, a floor without
    a corridor), and what the program still lacks. Same record as solve(), with `edited: true`."""
    prog = blocks(option, ledger)
    # a walk-up kept through the block editor (its one stair) is read against the walk-up's program: no amenity room
    raw_levels = zones_by_level.values() if isinstance(zones_by_level, dict) else zones_by_level
    if any(isinstance(z, dict) and z.get("block") == "core" and z.get("stairs") == "single" for lv in raw_levels for z in (lv or [])):
        prog = walkup_program(option, prog)
    pm, x0, y0, W, D, storeys, f2f = _plate(massing)
    corr, _ = LAYOUT_ASSUMPTIONS["corridor_width_m"]
    double = D >= corr + 8.0
    strip = max(0.0, (D - corr) / 2) if double else max(0.0, D - corr)
    by_key = {b["key"]: b for b in prog["blocks"]}
    on_grid = grid_of(option) is not None
    geometry: list[dict] = []
    warnings: list[str] = []
    levels = {int(k): v for k, v in (zones_by_level.items() if isinstance(zones_by_level, dict) else enumerate(zones_by_level))}
    lift_missing: list[int] = []
    go = building_type(option) == "ground_oriented"
    floors: list[dict] = []
    for lv in range(storeys):
        raw = levels.get(lv) or []
        zones: list[dict] = []
        for i, z in enumerate(raw):
            try:
                block = str(z.get("block"))
                x, y, w, d = (round(float(z.get(k)), 2) for k in ("x", "y", "w", "d"))
            except (TypeError, ValueError):
                geometry.append({"kind": "bad_zone", "level": lv, "note": f"zone {i + 1} on {'the ground floor' if lv == 0 else f'level {lv + 1}'} has no usable coordinates and was ignored"})
                continue
            if block not in EDITABLE_BLOCKS or w <= 0 or d <= 0:
                geometry.append({"kind": "bad_zone", "level": lv, "note": f"zone {i + 1} ({block}) on {'the ground floor' if lv == 0 else f'level {lv + 1}'} is not a block the editor knows, or has no size, and was ignored"})
                continue
            side = "front" if (y + d / 2) < (y0 + D / 2) else "rear"
            zone = {"block": block, "label": (str(z.get("label") or "").strip() or "Other") if block == "other" else BLOCK_LABEL.get(block, block),
                    "x": x, "y": y, "w": w, "d": d, "area_m2": round(w * d, 1), "side": side}
            if block in UNIT_KEYS:
                zone["unit"] = block
                zone["accessible"] = bool(z.get("accessible"))
                # a ground-oriented home over several floors (25 Nov 2026): one home, counted on its entry floor
                lv_span = z.get("levels")
                if z.get("home") is not None and isinstance(lv_span, (list, tuple)) and len(lv_span) == 2:
                    zone.update({"home": z["home"], "levels": [int(lv_span[0]), int(lv_span[1])], "entry": "at grade" if int(lv_span[0]) == 0 else "by its own stair"})
                    if lv != int(lv_span[0]):
                        del zone["unit"]
            if block == "corridor":
                zone["through"] = "core"
            # the architect's own name for a block (a lobby, an atrium, a café), drawn in place of the block's kind
            name = str(z.get("name") or "").strip()[:40]
            if name:
                zone["name"] = name
            if block == "void" and z.get("step"):
                zone["step"] = True   # a cut-out the editor's step-back tool drew along an edge of an upper floor
            if z.get("bay"):
                zone["bay"] = str(z["bay"])     # the solver's bay, kept through the block editor so the stacking reads back
            if block == "design_space" and z.get("entry"):
                zone["entry"], zone["label"] = True, "Lobby (entry)"
            if block == "core" and z.get("stairs") in ("scissor", "single"):
                zone["stairs"] = z["stairs"]   # the solver's scissor stair, or a walk-up's one stair, kept through the block editor
                if z["stairs"] == "single":
                    zone["label"] = "Stair"
            zones.append(zone)
            # inside the plate?
            if x < x0 - 0.05 or y < y0 - 0.05 or x + w > x0 + W + 0.05 or y + d > y0 + D + 0.05:
                geometry.append({"kind": "outside", "level": lv, "block": block, "note": f"{zone['label']} at {x:.1f}, {y:.1f} m runs past the plate ({W:.1f} × {D:.1f} m) on {'the ground floor' if lv == 0 else f'level {lv + 1}'}"})
            # a unit too small: under its gross area, or (on a structural grid, where a unit takes whole modules)
            # under the BC Housing minimum with its partitions
            floor_m2 = by_key[block]["min_gross_m2_each" if on_grid else "gross_m2_each"] if block in UNIT_KEYS and block in by_key else None
            if floor_m2 is not None and zone.get("home") is not None:
                # a home over several floors carries its area across them: this floor holds its share
                floor_m2 = floor_m2 / (zone["levels"][1] - zone["levels"][0] + 1)
            if floor_m2 is not None and w * d + 0.5 < floor_m2:
                geometry.append({"kind": "undersized", "level": lv, "block": block, "note": f"a {zone['label'].lower()} on {'the ground floor' if lv == 0 else f'level {lv + 1}'} is {w * d:.0f} m², under its {floor_m2:.0f} m² {'minimum with partitions' if on_grid else 'gross'}"})
        # overlaps: units and uses may not share floor area; the corridor and the core are the circulation and may cross each other only
        for i, a in enumerate(zones):
            for b in zones[i + 1:]:
                if {a["block"], b["block"]} == {"corridor", "core"}:
                    continue
                # 2.5 cm of grace: the solver's own zones are rounded to the centimetre, and two rounded neighbours can
                # read a centimetre into each other (25 Nov 2026: the memo's own plan opened with two overlaps)
                if not (a["x"] + a["w"] <= b["x"] + 0.025 or b["x"] + b["w"] <= a["x"] + 0.025 or a["y"] + a["d"] <= b["y"] + 0.025 or b["y"] + b["d"] <= a["y"] + 0.025):
                    geometry.append({"kind": "overlap", "level": lv, "block": a["block"], "note": f"{a['label']} and {b['label']} overlap on {'the ground floor' if lv == 0 else f'level {lv + 1}'}"})
        if not go and zones and not any(z["block"] == "corridor" for z in zones) and any(z.get("unit") for z in zones):
            geometry.append({"kind": "no_corridor", "level": lv, "note": f"{'the ground floor' if lv == 0 else f'level {lv + 1}'} has units but no corridor"})
        if not go and zones and not any(z["block"] == "core" for z in zones):
            geometry.append({"kind": "no_core", "level": lv, "note": f"{'the ground floor' if lv == 0 else f'level {lv + 1}'} has no core: the stairs and the elevator must land on every floor"})
        # above a walk-up's height the building needs an elevator: a core large enough to hold one beside its stairs
        # on every floor (`elevator_core_m`, declared); a narrower core is read as an exit stair alone
        if not go and zones and storeys > WALKUP_MAX_STOREYS and not any(z["block"] == "core" and min(z["w"], z["d"]) + 1e-6 >= ELEVATOR_CORE_M for z in zones):
            lift_missing.append(lv)
        used = sum(z["area_m2"] for z in zones if z["block"] not in ("spare", "void"))
        cut = sum(z["area_m2"] for z in zones if z["block"] == "void")
        floors.append({"level": lv, "name": "Ground floor" if lv == 0 else f"Level {lv + 1}", "z": _floor_z(option, lv, f2f), "zones": zones, "spare_m2": round(max(0.0, W * D - used - cut), 1)})
        if cut:
            floors[-1]["void_m2"] = round(cut, 1)

    if lift_missing:
        n = len(lift_missing)
        geometry.append({"kind": "no_elevator", "level": lift_missing[0], "block": "core",
                         "note": f"no core large enough for an elevator on {'every floor' if n == storeys else f'{n} floor' + ('s' if n != 1 else '')}: a building of {storeys} storeys needs one, "
                                 f"in a core at least {ELEVATOR_CORE_M:g} m wide and deep (narrower cores are read as exit stairs alone)"})

    # what the program still lacks, and what was placed beyond it
    shortfall: list[dict] = []
    for b in prog["blocks"]:
        if b["key"] in UNIT_KEYS:
            n = sum(1 for fl in floors for z in fl["zones"] if z.get("unit") == b["key"])
            if n < b["count"]:
                shortfall.append({"block": b["key"], "label": b["label"], "units": b["count"] - n, "area_m2": round((b["count"] - n) * b["gross_m2_each"], 1)})
            elif n > b["count"]:
                warnings.append(f"{n - b['count']} more {b['label'].lower()} unit{'s' if n - b['count'] != 1 else ''} drawn than the option counts ({b['count']}): the option's unit mix is what the rules read")
        else:
            # an added program ("other") is told apart by its label
            # commercial space the architect drew is non-residential floor area: it counts toward that program
            same = ((lambda z: z["block"] == "other" and z["label"].strip().lower() == b["label"].strip().lower()) if b["key"] == "other"
                    else (lambda z: z["block"] in ("non_residential", "commercial")) if b["key"] == "non_residential" else (lambda z: z["block"] == b["key"]))
            placed = sum(z["area_m2"] for fl in floors for z in fl["zones"] if same(z))
            if placed + 1.0 < b["area_m2"] and b["key"] == "services":
                # services that do not fit at grade go below it with the parking, as the solver takes them
                warnings.append(f"{b['area_m2'] - placed:,.0f} m² of the services and bicycle storage are not on the ground floor; they are taken below grade with the parking, which is not on the plates.")
            elif placed + 1.0 < b["area_m2"]:
                shortfall.append({"block": b["key"], "label": b["label"], "area_m2": round(b["area_m2"] - placed, 1)})
    plate = {"x": round(x0, 2), "y": round(y0, 2), "width_m": round(W, 2), "depth_m": round(D, 2), "storeys": storeys, "floor_to_floor_m": f2f, "double_loaded": double, "unit_depth_m": round(strip, 2),
             "arrangement": "double" if double else "single",
             "stacking": "bays" if any(z.get("bay") for fl in floors for z in fl["zones"]) else "by hand"}
    # a plan kept from the solver's corridor across the plate: every corridor taller than it is wide, none ringing a core
    corrs_all = [z for fl in floors for z in fl["zones"] if z["block"] == "corridor"]
    if corrs_all and all(z["d"] > z["w"] for z in corrs_all):
        plate.update(arrangement="cross", corridor="across", unit_depth_m=round(max(0.0, (W - corr) / 2), 2))
    # a placement round a ringed core (the solver's point tower, kept or moved by hand) is still a point tower
    ring = next(((fl, z) for fl in floors for z in fl["zones"] if z["block"] == "core" and _ringed(z, [c for c in fl["zones"] if c["block"] == "corridor"])), None)
    if ring:
        c = ring[1]
        plate.update(arrangement="point", double_loaded=False, unit_depth_m=round(max(0.0, c["y"] - corr - y0), 2), side_depth_m=round(max(0.0, c["x"] - corr - x0), 2),
                     core_m=[c["w"], c["d"]])
    elif any(z["block"] == "core" and z.get("stairs") == "single" for fl in floors for z in fl["zones"]):
        plate.update(arrangement="walkup", double_loaded=False, unit_depth_m=round(D, 2))
    if go:
        homes = [z for fl in floors for z in fl["zones"] if z.get("home") is not None]
        plate.update(arrangement="ground_oriented", double_loaded=False, stacking="homes",
                     ground_oriented={"rows": len({z["y"] for z in homes}) or 1, "row_depth_m": round(max([z["d"] for z in homes] or [D]), 2), "courtyard_m": 0.0,
                                      "home_spans": sorted({z["levels"][1] - z["levels"][0] + 1 for z in homes}), "homes": "drawn by hand"})
    if grid_of(option):
        plate["grid"] = grid_of(option)
    # a home drawn narrower than its type's minimum width is a problem to fix, as a home under its area is (23 Nov
    # 2026, Kai); how deep it runs for its width stays a note (`proportions`). A walk-up's through homes are not held to it.
    if plate.get("arrangement") not in ("walkup", "ground_oriented"):
        for fl in floors:
            for z in fl["zones"]:
                least = UNIT_MIN_WIDTH_M.get(z.get("unit") or "")
                if least and _wide_deep(z, x0, y0, W, D)[0] + 0.05 < least:
                    where = "the ground floor" if fl["level"] == 0 else f"level {fl['level'] + 1}"
                    geometry.append({"kind": "narrow", "level": fl["level"], "block": z["block"],
                                     "note": f"a {z['label'].lower()} on {where} is {_wide_deep(z, x0, y0, W, D)[0]:.1f} m wide, under the {least:g} m a {z['label'].lower()} needs along its window wall"})
    L = _assemble(site, option, ledger, massing, prog, plate, floors, shortfall, warnings, edited=True, geometry=geometry)
    if go:
        L["egress"] = _ground_egress(L["floors"], [])
    return L


def zones_of(L: dict) -> dict[str, list[dict]]:
    """A layout's placement in the form the option keeps (`layout.zones`): the editor starts from the solver's."""
    out: dict[str, list[dict]] = {}
    for fl in L["floors"]:
        out[str(fl["level"])] = [{k: z[k] for k in ("block", "x", "y", "w", "d")} | ({"accessible": True} if z.get("accessible") else {}) | ({"label": z["label"]} if z["block"] == "other" else {})
                                 | ({"stairs": z["stairs"]} if z.get("stairs") in ("scissor", "single") else {})
                                 | ({"bay": z["bay"]} if z.get("bay") else {}) | ({"entry": True} if z.get("entry") else {})
                                 | ({"name": z["name"]} if z.get("name") else {}) | ({"step": True} if z.get("step") else {})
                                 | ({"home": z["home"], "levels": list(z["levels"])} if z.get("home") is not None and z.get("levels") else {})
                                 for z in fl["zones"] if z["block"] != "spare"]
    return out


def _check(rule: dict, floors: list[dict], prog: dict, shortfall: list[dict]) -> dict:
    """One adjacency rule read back from the placed zones: pass, conditional (held in part) or info (not in play)."""
    key = rule["block"]
    zones = [(fl, z) for fl in floors for z in fl["zones"]]
    out = {**rule, "status": "info", "note": ""}
    if key == "non_residential":
        zs = [(fl, z) for fl, z in zones if z["block"] in (key, "commercial")]
        if not zs:
            out["note"] = "no non-residential space in the option"
            return out
        ground = all(fl["level"] == 0 for fl, z in zs)
        street = any(z.get("side") == "front" for fl, z in zs)
        through = ground and street and any(z.get("side") == "rear" for fl, z in zs)
        ok = ground and street
        out.update(status="pass" if ok else "conditional",
                   note=("all of it on the ground floor, its front on the street" + (", running through to the lane side" if through else "")) if ok
                   else "some of it had to go above the ground floor: the ground plate is too small for the brief")
    elif key == "amenity":
        zs = [(fl, z) for fl, z in zones if z["block"] == key]
        if not zs:
            out["note"] = "no amenity in the program"
            return out
        ok = all(fl["level"] == 0 for fl, z in zs)
        out.update(status="pass" if ok else "conditional", note="on the ground floor beside the core, where the entry is" if ok else "part of the amenity is above the ground floor")
    elif key == "services":
        zs = [(fl, z) for fl, z in zones if z["block"] == key]
        ok = bool(zs) and all(fl["level"] == 0 and z.get("side") == "rear" for fl, z in zs)
        # why they face the street, from the plate itself (17 Nov 2026: "single-loaded" was said of a double-loaded plate)
        double = any(z.get("side") == "rear" for fl, z in zones)
        street_why = "the lane side has no room left beside the core" if double else "the plate is single-loaded"
        out.update(status="pass" if ok else "conditional", note="on the ground floor, lane side" if ok else (f"on the ground floor but facing the street: {street_why}" if zs and all(fl["level"] == 0 for fl, _ in zs) else "services could not all stay on the ground floor"))
    elif key == "core" and any(z["block"] == "core" and z.get("stairs") == "single" for fl, z in zones):
        st = next(z for fl, z in zones if z["block"] == "core" and z.get("stairs") == "single")
        out.update(status="pass", note=f"a walk-up: one {st['w']:g} × {st['d']:g} m stair on the street side of every floor, no elevator, its landing behind it")
    elif key == "units" and any(z["block"] == "core" and z.get("stairs") == "single" for fl, z in zones):
        out.update(status="pass", note="every home opens off the stair's landing, the plate's full depth, with no corridor")
        if shortfall:
            out.update(status="conditional", note=out["note"] + "; " + ", ".join(f"{s.get('units', '')} {s['label'].lower()} ({s['area_m2']:,.0f} m²) did not fit".replace("  ", " ") for s in shortfall) + ": more storeys, a larger plate or a smaller program")
        return out
    elif key == "core":
        n_cores = max((sum(1 for z in fl["zones"] if z["block"] == "core") for fl in floors), default=0)
        sc = next(((fl, z) for fl, z in zones if z["block"] == "core" and z.get("stairs") == "scissor"), None)
        ringed = bool(sc) and _ringed(sc[1], [z for z in sc[0]["zones"] if z["block"] == "corridor"])
        out.update(status="pass", note=(f"one {sc[1]['w']:g} × {sc[1]['d']:g} m core at the centre of every floor holding a scissor stair, the corridor round it and the homes round that"
                                        if ringed else f"one core at the centre of every floor, {sc[1]['w']:g} m along the corridor to hold a scissor stair, the corridor along it"
                                        if sc else "one core bay at the centre of every floor, the corridor through it")
                   + (", and an exit stair at each end of the corridor" if n_cores >= 3 else ""))
    elif key == "units":
        sides = {z.get("side") for fl, z in zones if z.get("unit")}
        ok = sides >= {"front", "rear"}
        out.update(status="pass" if ok else "conditional", note="units on both sides of the corridor" if ok else "units on the street side only: the plate is too shallow for a double-loaded corridor")
        if shortfall:
            out.update(status="conditional", note=out["note"] + "; " + ", ".join(f"{s.get('units', '')} {s['label'].lower()} ({s['area_m2']:,.0f} m²) did not fit".replace("  ", " ") for s in shortfall) + ": more storeys, a larger plate or a smaller program")
        return out
    elif key == "three_bed_plus":
        fam = [fl["level"] for fl, z in zones if z.get("unit") == "three_bed_plus"]
        small = [fl["level"] for fl, z in zones if z.get("unit") in ("studio", "one_bed")]
        if not fam:
            out["note"] = "no three-bedroom units in the mix"
            return out
        # stacked in bays (the zones carry `bay`): the rule holds where the three-bedroom bays start at the lowest floor
        # that has homes; placed floor by floor, where they sit under the smaller homes
        stacked = any(z.get("bay") for fl, z in zones if z.get("unit") == "three_bed_plus")
        if stacked:
            lowest = min(fl["level"] for fl, z in zones if z.get("unit"))
            bays = len({z["bay"] for fl, z in zones if z.get("unit") == "three_bed_plus" and z.get("bay")})
            ok = min(fam) <= lowest + 1
            out.update(status="pass" if ok else "conditional",
                       note=f"three-bedroom homes stacked in {bays} bay{'s' if bays != 1 else ''}, levels {min(fam) + 1} to {max(fam) + 1}" + ("" if ok else ", starting above the lowest floor of homes"))
            return out
        ok = not small or max(fam) <= min(small) + 1
        out.update(status="pass" if ok else "conditional", note=f"three-bedroom units on levels {min(fam) + 1} to {max(fam) + 1}" + ("" if ok else ", above some smaller units"))
    elif key == "accessible":
        acc = [(fl, z) for fl, z in zones if z.get("accessible")]
        if not acc:
            out["note"] = "no accessible units stated on the option"
            return out
        # where they are, floor by floor (17 Nov 2026: "7 accessible units on the ground floor" of a ground floor of 3 homes)
        by: dict[int, int] = {}
        for fl, _ in acc:
            by[fl["level"]] = by.get(fl["level"], 0) + 1
        where = lambda lv: "the ground floor" if lv == 0 else f"level {lv + 1}"
        lv = min(by)
        note = (f"{len(acc)} accessible unit{'s' if len(acc) != 1 else ''} on {where(lv)}, nearest the core" if len(by) == 1
                else f"{len(acc)} accessible units from {where(lv)} ({by[lv]} there) to {where(max(by))}, nearest the core")
        out.update(status="pass", note=note)
    return out


# ---------------------------------------------------------------- the drawings

def _esc(s: Any) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _svg_open(w: float, h: float, title: str) -> list[str]:
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" font-family="IBM Plex Sans, Helvetica, Arial, sans-serif" font-size="12" fill="{TONES["ink"]}" role="img" aria-label="{_esc(title)}">',
            f'<rect width="100%" height="100%" fill="{TONES["paper"]}"/>']


# Text is measured, not guessed, before it is placed (20 Nov 2026, an architect's review at 1600 px: labels printed over
# each other, ran off the sheet and were cut mid-word). IBM Plex Sans averages about 0.55 em a character; 0.6 is taken,
# so a measured label never runs longer than its box.
EM_PER_CHAR = 0.6

# Short names for the blocks where the full name does not fit its box, and the key that spells them out
BLOCK_SHORT = {"three_bed_plus": "3B", "two_bed": "2B", "one_bed": "1B", "studio": "ST", "core": "C", "corridor": "CR", "services": "SV",
               "amenity": "AM", "non_residential": "NR", "spare": "SP", "design_space": "DS", "commercial": "CM", "void": "V", "other": "OT"}


def _metres(x: float) -> str:
    """A height as the sheets print it: to the centimetre where the massing has one, rounded half up, trailing zeros
    dropped to one decimal (88.45 stays 88.45, where "{:.1f}" printed 88.5 or, for 88.449999…, 88.4; 22.3 stays 22.3;
    a floor at 9.15 m reads +9.15). Pure."""
    from decimal import ROUND_HALF_UP, Decimal
    d = Decimal(repr(round(float(x), 9))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s = f"{d:.2f}"
    return s[:-1] if s.endswith("0") else s


def _tw(text: Any, size: float) -> float:
    """A label's width in px at this font size, measured generously. Pure."""
    return len(str(text)) * size * EM_PER_CHAR


def _fit(options: list[str], room: float, size: float) -> str | None:
    """The first of the labels that fits `room` px at this size, or None. Pure."""
    return next((t for t in options if t and _tw(t, size) + 4 <= room), None)


def _legend(x: float, y: float, keys: list[str], max_w: float = 10_000.0, short: bool = False) -> tuple[list[str], float]:
    """The key: a swatch and the block's name (with its short name where the drawing uses one), wrapped to `max_w` px.
    Returns the elements and the height it took. Pure."""
    out: list[str] = []
    cx, cy, row = x, y, 18
    for k in keys:
        word = BLOCK_LABEL.get(k, k) + (f" · {BLOCK_SHORT[k]}" if short and k in BLOCK_SHORT else "")
        w = 16 + _tw(word, 11) + 14
        if cx > x and cx + w > x + max_w:
            cx, cy = x, cy + row
        out.append(f'<rect x="{cx:.1f}" y="{cy - 9:.1f}" width="12" height="12" fill="{TONES[k]}" stroke="{TONES["muted"]}" stroke-width="0.8"/>')
        out.append(f'<text x="{cx + 16:.1f}" y="{cy + 1:.1f}" fill="{TONES["muted"]}" font-size="11">{_esc(word)}</text>')
        cx += w
    return out, cy - y + row


def _foot(lines: list[str], x: float, y: float, max_w: float | None = None, size: float = 12) -> list[str]:
    """The notes under a sheet, one line each, wrapped to `max_w` px where given so none runs off the sheet."""
    if max_w:
        per = max(30, int(max_w / (size * EM_PER_CHAR)))
        lines = [ln2 for ln in lines for ln2 in (_wrap_words(ln, per) or [""])]
    return [f'<text x="{x:.1f}" y="{y + i * 16:.1f}" font-size="{size:g}" fill="{TONES["ink"]}">{_esc(ln)}</text>' for i, ln in enumerate(lines)]


def _foot_lines(lines: list[str], max_w: float, size: float = 12) -> int:
    """How many lines `_foot` takes for these notes at this width. Pure."""
    per = max(30, int(max_w / (size * EM_PER_CHAR)))
    return sum(len(_wrap_words(ln, per) or [""]) for ln in lines)


def _scale_bar(x: float, y: float, scale: float, max_px: float = 140.0) -> tuple[list[str], float]:
    """A two-half scale bar from (x, y), the bar's top-left: the longest round length that fits `max_px` at `scale` px
    a metre, its halves dark and light, labelled 0, the half and the whole in metres. Returns the elements and the
    width it took, its end label included. Pure."""
    L = next((v for v in (200, 100, 50, 20, 10, 5, 2, 1) if v * scale <= max_px), 1)
    w = L * scale
    half = f"{L / 2:g}"
    out = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w / 2:.1f}" height="5" fill="{TONES["ink"]}"/>',
           f'<rect x="{x + w / 2:.1f}" y="{y:.1f}" width="{w / 2:.1f}" height="5" fill="{TONES["paper"]}" stroke="{TONES["ink"]}" stroke-width="0.8"/>',
           f'<text x="{x:.1f}" y="{y + 16:.1f}" font-size="9.5" text-anchor="middle" fill="{TONES["muted"]}">0</text>',
           f'<text x="{x + w / 2:.1f}" y="{y + 16:.1f}" font-size="9.5" text-anchor="middle" fill="{TONES["muted"]}">{half}</text>',
           f'<text x="{x + w:.1f}" y="{y + 16:.1f}" font-size="9.5" text-anchor="middle" fill="{TONES["muted"]}">{L:g} m</text>']
    return out, w + _tw(f"{L:g} m", 9.5) / 2


def _north(cx: float, cy: float, bearing: float, r: float = 11.0) -> list[str]:
    """A north arrow at (cx, cy) on a sheet drawn with the street at the bottom: `bearing` is the bearing of the
    drawing's x axis (along the frontage) clockwise from north, and its up is the y axis, 90° anticlockwise of it, so
    north stands 90 - bearing degrees clockwise from up (as the page's northArrow, figures/common.js). The N stays
    upright beyond the tip. Pure."""
    rot = 90.0 - bearing
    t = math.radians(rot)
    d = r + 9
    nx, ny = cx + d * math.sin(t), cy - d * math.cos(t) + 4
    return [f'<g transform="rotate({rot:.1f} {cx:.1f} {cy:.1f})"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{TONES["paper"]}" stroke="{TONES["muted"]}" stroke-width="0.8"/>'
            f'<polygon points="{cx:.1f},{cy - r * 0.92:.1f} {cx + r * 0.42:.1f},{cy + r * 0.55:.1f} {cx:.1f},{cy + r * 0.2:.1f} {cx - r * 0.42:.1f},{cy + r * 0.55:.1f}" fill="{TONES["ink"]}"/></g>',
            f'<text x="{nx:.1f}" y="{ny:.1f}" font-size="11" font-weight="600" text-anchor="middle" fill="{TONES["ink"]}">N</text>']


def _spread(labels: list[tuple[float, str, str]], gap: float = 12.0, top: float = -1e9, bottom: float = 1e9) -> list[tuple[float, float, str, str]]:
    """Labels at their heights (y, text, colour) pushed apart so no two are closer than `gap` px, kept between `top`
    and `bottom`: returns (y wanted, y drawn, text, colour), in order down the sheet. Pure."""
    ls = sorted(labels, key=lambda t: t[0])
    ys = [max(top, y) for y, _, _ in ls]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + gap)
    over = ys[-1] - bottom if ys else 0
    if over > 0:
        ys = [y - over for y in ys]
        for i in range(len(ys) - 2, -1, -1):
            ys[i] = min(ys[i], ys[i + 1] - gap)
    return [(ls[i][0], ys[i], ls[i][1], ls[i][2]) for i in range(len(ls))]


def _stamp_line(L: dict) -> str:
    # the run's stamp stays in the ledger and the memo's title block; on the drawing it read as machine text, and so
    # did the ISO date (24 Nov 2026)
    return f'Rules as of {date_words(L["as_of"])} · drawn from the option and the massing, not a design'


def svg_stacking(L: dict) -> str:
    """The stacking diagram: one bar per floor, top floor first, its length the plate and its segments the blocks
    in proportion to the area they take on that floor."""
    floors = L["floors"]
    pad, bar_h, gap = 48, 26, 8
    bar_w = 520
    mark_w = 64          # the level marks to the right of the bars
    n = len(floors)
    f2f = float(L["plate"].get("floor_to_floor_m") or 0)
    lines = [f'{L["units_placed"]} of {L["units_total"]} units placed on {n} floors of {L["plate"]["width_m"]} × {L["plate"]["depth_m"]} m ({L["plate"]["width_m"] * L["plate"]["depth_m"]:,.0f} m² each)',
             *(f'Did not fit: {s["label"]}{" × " + str(s["units"]) if s.get("units") else ""}, {s["area_m2"]:,.0f} m²' for s in L["shortfall"]),
             "A segment too short for its name carries its short name from the key, or none; the levels at the right are each floor's height above the ground floor.",
             _stamp_line(L)]
    width = pad + 80 + bar_w + mark_w + pad
    keys = ["non_residential", "amenity", "services", "core", "corridor", "three_bed_plus", "two_bed", "one_bed", "studio", "spare"]
    legend, leg_h = _legend(pad, 0, keys, width - 2 * pad, short=True)
    bars_bottom = pad + 24 + n * (bar_h + gap)
    foot_y = bars_bottom + 18 + leg_h + 14
    height = foot_y + 16 * _foot_lines(lines, width - 2 * pad) + 16
    out = _svg_open(width, height, "Stacking diagram")
    out.append(f'<text x="{pad}" y="{pad - 4}" font-size="14" font-weight="600">Stacking · top floor first, each bar one plate</text>')
    out.append(f'<text x="{pad + 80 + bar_w + 8}" y="{pad + 14}" font-size="9.5" fill="{TONES["muted"]}">level</text>')
    order = {k: i for i, k in enumerate(keys)}
    for i, fl in enumerate(reversed(floors)):
        y = pad + 24 + i * (bar_h + gap)
        total = sum(z["area_m2"] for z in fl["zones"]) or 1
        x = pad + 80
        out.append(f'<text x="{pad}" y="{y + bar_h / 2 + 4:.1f}" font-size="11" fill="{TONES["muted"]}">{_esc(fl["name"])}</text>')
        agg: dict[str, float] = {}
        for z in fl["zones"]:
            agg[z["block"]] = agg.get(z["block"], 0) + z["area_m2"]
        for k in sorted(agg, key=lambda k: order.get(k, 99)):
            w = bar_w * agg[k] / total
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bar_h}" fill="{TONES.get(k, TONES["other"])}" stroke="{TONES["paper"]}" stroke-width="1"/>')
            # the full name where it fits, else the key's short name, else nothing (20 Nov 2026: "Core (stair",
            # "Two-bedroo" and "Non-resi" were cut mid-word)
            cnt = sum(1 for z in fl["zones"] if z["block"] == k and z.get("unit"))
            tail = f" × {cnt}" if cnt else ""
            lab = _fit([BLOCK_LABEL.get(k, k) + tail, BLOCK_SHORT.get(k, "") + tail, BLOCK_SHORT.get(k, "")], w - 4, 10)
            if lab:
                out.append(f'<text x="{x + 4:.1f}" y="{y + bar_h / 2 + 4}" font-size="10" fill="{TONES["ink"]}">{_esc(lab)}</text>')
            x += w
        # the level mark: the floor's height above the ground floor
        z = float(fl.get("z", fl["level"] * f2f) or 0)
        out.append(f'<line x1="{pad + 80 + bar_w + 2}" y1="{y + bar_h}" x2="{pad + 80 + bar_w + 8}" y2="{y + bar_h}" stroke="{TONES["muted"]}" stroke-width="0.8"/>')
        out.append(f'<text x="{pad + 80 + bar_w + 10}" y="{y + bar_h + 3:.1f}" font-size="9.5" fill="{TONES["muted"]}">+{_metres(z)} m</text>')
    out += _shift(legend, 0, bars_bottom + 18)
    out += _foot(lines, pad, foot_y, width - 2 * pad)
    out.append("</svg>")
    return "\n".join(out)


def _shift(elements: list[str], dx: float, dy: float) -> list[str]:
    """Elements drawn at an origin of (0, 0) moved to (dx, dy), as one group. Pure."""
    return [f'<g transform="translate({dx:.1f} {dy:.1f})">'] + elements + ["</g>"]


STATUS_TONE = {"pass": "#2f7d4a", "conditional": "#9a6b00", "fail": "#c81e1e", "uncertain": "#a3640c", "info": "#5f6672"}
TREAD_M = 0.28        # a tread's going, for drawing the stairs only
DOOR_M = 0.9          # a door leaf, for drawing only


def _stair_boxes(z: dict, zones: list[dict]) -> list[dict]:
    """The stairs drawn in a core zone, in plate metres: {x, y, w, d, kind, doors: [(x, y, face)]}, where `face` is the
    side of the box the door is on ("x0", "x1", "y0", "y1"). The stairs stand in the part of the core the corridor does
    not cross; a walk-up's one stair is the zone itself, its door on the landing; a scissor stair runs the core's width
    along the corridor, doors at its two ends (a point tower's on the faces the ring corridor passes); a core a bay wide
    holds a stair at each end, a narrower one a stair. Pure."""
    stair_w, _ = LAYOUT_ASSUMPTIONS["stair_width_m"]
    bay, _ = LAYOUT_ASSUMPTIONS["core_bay_m"]
    x, y, w, d = z["x"], z["y"], z["w"], z["d"]
    corrs = [c for c in zones if c["block"] == "corridor"]
    # a core on a corridor that runs across the plate (the corridor taller than it is wide, and no ring round the
    # core): the stairs as they stand with the plan turned a quarter, turned back, their doors on the faces that become
    crossing = [c for c in corrs if _touches(c, z)]
    if crossing and all(c["d"] > c["w"] for c in crossing) and not _ringed(z, corrs):
        face = {"x0": "y0", "x1": "y1", "y0": "x0", "y1": "x1"}
        return [{"x": b["y"], "y": b["x"], "w": b["d"], "d": b["w"], "kind": b["kind"], "doors": [(dy, dx, face[f]) for dx, dy, f in b["doors"]]}
                for b in _stair_boxes(_t(z), [_t(c) for c in zones])]
    # the corridor crossing the core along x: the stairs go in the core's longer part beside it
    y0, y1 = y, y + d
    for c in corrs:
        if c["x"] < x + w - 0.05 and c["x"] + c["w"] > x + 0.05 and c["y"] < y1 - 0.05 and c["y"] + c["d"] > y0 + 0.05:
            front, back = c["y"] - y0, y1 - (c["y"] + c["d"])
            if back >= front:
                y0 = c["y"] + c["d"]
            else:
                y1 = c["y"]
    face_y = "y0" if any(abs(c["y"] + c["d"] - y0) < 0.1 and c["x"] < x + w and c["x"] + c["w"] > x for c in corrs) else "y1"
    run = min(5.5, max(0.0, y1 - y0))
    if run < 1.0:
        return []
    by = y0 if face_y == "y0" else y1 - run
    if z.get("stairs") == "single":
        land = next((c for c in corrs if abs(c["y"] - (y + d)) < 0.1 or abs(c["y"] + c["d"] - y) < 0.1), None)
        face = "y1" if land is None or land["y"] >= y + d - 0.1 else "y0"
        return [{"x": x, "y": y, "w": w, "d": d, "kind": "switchback", "doors": [(x + 0.15, y + d if face == "y1" else y, face)]}]
    if z.get("stairs") == "scissor":
        sd = min(2.8, max(0.0, y1 - y0))
        ringed = _ringed(z, corrs)
        sy = y + (d - sd) / 2 if ringed else (y0 if face_y == "y0" else y1 - sd)
        doors = ([(x, sy + sd / 2 - DOOR_M / 2, "x0"), (x + w, sy + sd / 2 - DOOR_M / 2, "x1")] if ringed else
                 [(x + 0.15, sy if face_y == "y0" else sy + sd, face_y), (x + w - 0.15 - DOOR_M, sy if face_y == "y0" else sy + sd, face_y)])
        return [{"x": x, "y": sy, "w": w, "d": sd, "kind": "scissor", "doors": doors}]
    fy = by if face_y == "y0" else by + run
    if w + 1e-6 >= bay:
        ld = min(2.2, run)
        return [{"x": x, "y": by, "w": stair_w, "d": run, "kind": "switchback", "doors": [(x + 0.15, fy, face_y)]},
                {"x": x + w - stair_w, "y": by, "w": stair_w, "d": run, "kind": "switchback", "doors": [(x + w - 0.15 - DOOR_M, fy, face_y)]},
                {"x": x + w / 2 - 1.0, "y": by if face_y == "y0" else by + run - ld, "w": 2.0, "d": ld, "kind": "lift", "doors": []}]
    sw = min(w, stair_w + 0.4)
    return [{"x": x + (w - sw) / 2, "y": by, "w": sw, "d": run, "kind": "switchback", "doors": [(x + (w - sw) / 2 + 0.15, fy, face_y)]}]


def _draw_stair(out: list[str], s: dict, P, scale: float) -> None:
    """One stair in plan: its outline, the treads, the flights' divider (a switchback) or the crossing of two flights
    (a scissor stair), and an exit door on the corridor or landing side with its swing. `P(x, y)` gives sheet px."""
    x0, y0 = P(s["x"], s["y"] + s["d"])
    w, d = s["w"] * scale, s["d"] * scale
    out.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{d:.1f}" fill="{TONES["paper"]}" stroke="{TONES["ink"]}" stroke-width="0.9"/>')
    if s["kind"] == "lift":    # the elevator shaft, crossed
        out.append(f'<path d="M{x0:.1f} {y0:.1f}L{x0 + w:.1f} {y0 + d:.1f}M{x0:.1f} {y0 + d:.1f}L{x0 + w:.1f} {y0:.1f}" stroke="{TONES["muted"]}" stroke-width="0.6" fill="none"/>')
        return
    along_y = s["d"] >= s["w"]
    length, across = (s["d"], s["w"]) if along_y else (s["w"], s["d"])
    land = min(1.2, length / 4)
    step = TREAD_M * scale
    while step < 2.6:      # never denser than a line every 2.6 px
        step *= 2
    t = land * scale
    lines = []
    while t <= (length - land) * scale + 1e-6:
        if along_y:
            lines.append(f"M{x0:.1f} {y0 + t:.1f}h{w:.1f}")
        else:
            lines.append(f"M{x0 + t:.1f} {y0:.1f}v{d:.1f}")
        t += step
    if lines:
        out.append(f'<path d="{"".join(lines)}" stroke="{TONES["muted"]}" stroke-width="0.5" fill="none"/>')
    if s["kind"] == "scissor":
        out.append(f'<path d="M{x0:.1f} {y0:.1f}L{x0 + w:.1f} {y0 + d:.1f}M{x0:.1f} {y0 + d:.1f}L{x0 + w:.1f} {y0:.1f}" stroke="{TONES["ink"]}" stroke-width="0.7" fill="none"/>')
    elif along_y:
        out.append(f'<line x1="{x0 + w / 2:.1f}" y1="{y0 + land * scale:.1f}" x2="{x0 + w / 2:.1f}" y2="{y0 + d - land * scale:.1f}" stroke="{TONES["ink"]}" stroke-width="0.8"/>')
    else:
        out.append(f'<line x1="{x0 + land * scale:.1f}" y1="{y0 + d / 2:.1f}" x2="{x0 + w - land * scale:.1f}" y2="{y0 + d / 2:.1f}" stroke="{TONES["ink"]}" stroke-width="0.8"/>')
    r = min(DOOR_M, across * 0.45) * scale
    for (hx, hy, face) in s["doors"]:
        X, Y = P(hx, hy)
        # the leaf swings into the stair; the arc drawn as points, so no sweep flag can turn it the wrong way
        if face in ("y0", "y1"):
            sy = -1 if face == "y0" else 1          # y0 is the box's street-side face, the lower edge on the sheet
            pts = [(X + r * math.cos(a), Y + sy * r * math.sin(a)) for a in (i * math.pi / 12 for i in range(7))]
            out.append(f'<line x1="{X:.1f}" y1="{Y:.1f}" x2="{X + r:.1f}" y2="{Y:.1f}" stroke="{TONES["paper"]}" stroke-width="1.6"/>')
            out.append(f'<path d="M{X:.1f} {Y + sy * r:.1f}L{X:.1f} {Y:.1f}M' + "L".join(f"{a:.1f} {b:.1f}" for a, b in pts) + f'" stroke="{TONES["ink"]}" stroke-width="0.7" fill="none"/>')
        else:
            sx = 1 if face == "x0" else -1
            pts = [(X + sx * r * math.sin(a), Y - r * math.cos(a)) for a in (i * math.pi / 12 for i in range(7))]
            out.append(f'<line x1="{X:.1f}" y1="{Y:.1f}" x2="{X:.1f}" y2="{Y - r:.1f}" stroke="{TONES["paper"]}" stroke-width="1.6"/>')
            out.append(f'<path d="M{X + sx * r:.1f} {Y:.1f}L{X:.1f} {Y:.1f}M' + "L".join(f"{a:.1f} {b:.1f}" for a, b in pts) + f'" stroke="{TONES["ink"]}" stroke-width="0.7" fill="none"/>')


def _entry_x(L: dict, fl: dict) -> float:
    """Where the ground floor is entered from the street, in plate metres along x: a walk-up's stair, else the amenity
    on the street side (the entry it stands beside), else the core. Pure."""
    zs = fl["zones"]
    st = next((z for z in zs if z["block"] == "core" and z.get("stairs") == "single"), None)
    if st:
        return st["x"] + st["w"] / 2
    lobby = next((z for z in zs if z.get("entry")), None)
    if lobby:
        return lobby["x"] + lobby["w"] / 2
    am = next((z for z in zs if z["block"] == "amenity" and z.get("side") == "front"), None)
    if am:
        return am["x"] + am["w"] / 2
    core = next((z for z in zs if z["block"] == "core" and z["w"] >= 3), None) or next((z for z in zs if z["block"] == "core"), None)
    p = L["plate"]
    return core["x"] + core["w"] / 2 if core else p["x"] + p["width_m"] / 2


def _plan(out: list[str], L: dict, fl: dict, ox: float, oy: float, scale: float, title: str, eg: dict | None = None,
          street: str | None = None, room: float | None = None) -> None:
    p = L["plate"]
    room = room or 10_000.0
    out.append(f'<text x="{ox:.1f}" y="{oy - (22 if eg else 8):.1f}" font-size="13" font-weight="600">{_esc(title)}</text>')
    if eg:
        colour = STATUS_TONE.get(eg["status"], TONES["muted"])
        parts = egress_line(eg).split(" · ")
        # the line as long as the sheet allows: the trailing figures go first, the status stays
        words = next((" · ".join(parts[:k] + parts[-1:]) for k in range(len(parts) - 1, 0, -1) if _tw("Egress: " + " · ".join(parts[:k] + parts[-1:]), 10.5) <= room), parts[-1])
        out.append(f'<text x="{ox:.1f}" y="{oy - 7:.1f}" font-size="10.5" fill="{colour}">Egress: {_esc(words)}</text>')
    pw, pd = p["width_m"] * scale, p["depth_m"] * scale
    out.append(f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{pw:.1f}" height="{pd:.1f}" fill="{TONES["lot"]}" stroke="{TONES["ink"]}" stroke-width="1.2"/>')
    # the street is at the bottom of every plan in the set, as on FIG 01 (15 Nov 2026): the plate's y runs from the
    # street side, so a zone is drawn from the far edge down
    P = lambda x, y: (ox + (x - p["x"]) * scale, oy + (p["depth_m"] - (y - p["y"])) * scale)
    for z in fl["zones"]:
        x, y = P(z["x"], z["y"] + z["d"])
        w, d = z["w"] * scale, z["d"] * scale
        dash = ' stroke-dasharray="3 2"' if z["block"] == "spare" else ""
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{d:.1f}" fill="{TONES.get(z["block"], TONES["other"])}" stroke="{TONES["muted"]}" stroke-width="0.8"{dash}/>')
    # the stairs in the cores and their exit doors (20 Nov 2026: the plans showed no stair, door or entry)
    for z in fl["zones"]:
        if z["block"] == "core":
            for s in _stair_boxes(z, fl["zones"]):
                _draw_stair(out, s, P, scale)
    labels: list[tuple[float, float, float, float]] = []     # the zone labels' boxes, so the travel figure keeps clear
    for z in fl["zones"]:
        x, y = P(z["x"], z["y"] + z["d"])
        w, d = z["w"] * scale, z["d"] * scale
        if z.get("accessible"):
            out.append(f'<circle cx="{x + 7:.1f}" cy="{y + 7:.1f}" r="3.2" fill="{TONES["accessible"]}"/>')
        if d < 13 or z["block"] == "core":
            continue
        name = ("Landing" if z.get("label") == "Landing" else str(z.get("label") or "")) if z["block"] in ("corridor", "other") else BLOCK_LABEL.get(z["block"], z["block"])
        if z.get("name"):
            name = str(z["name"])      # the architect's own name for the block
        lab = _fit([name, BLOCK_SHORT.get(z["block"], "")], w, 9.5)
        if lab:
            out.append(f'<text x="{x + w / 2:.1f}" y="{y + d / 2 + 3.5:.1f}" font-size="9.5" text-anchor="middle" fill="{TONES["ink"]}">{_esc(lab)}</text>')
            tw = _tw(lab, 9.5)
            labels.append((x + w / 2 - tw / 2, y + d / 2 - 5, x + w / 2 + tw / 2, y + d / 2 + 5))
    # the farthest travel path: the unit's door, across to the corridor's axis, along it to the exit
    fu = (eg or {}).get("farthest_unit")
    if fu:
        px = lambda x: ox + (x - p["x"]) * scale
        py = lambda y: oy + (p["depth_m"] - (y - p["y"])) * scale
        (dx, dy), (ex, ey) = fu["door"], fu["exit"]
        corner = (dx, ey) if abs(dy - ey) <= abs(dx - ex) else (ex, dy)
        over = eg["farthest_travel_m"] > eg["travel_limit_m"] + 1e-6
        tone = TONES["envelope"] if over else TONES["ink"]
        out.append(f'<polyline points="{px(dx):.1f},{py(dy):.1f} {px(corner[0]):.1f},{py(corner[1]):.1f} {px(ex):.1f},{py(ey):.1f}" fill="none" stroke="{tone}" stroke-width="1.4" stroke-dasharray="4 2"/>')
        out.append(f'<circle cx="{px(dx):.1f}" cy="{py(dy):.1f}" r="2.4" fill="{tone}"/>')
        out.append(f'<path d="M {px(ex) - 3:.1f} {py(ey) - 3:.1f} L {px(ex) + 3:.1f} {py(ey) + 3:.1f} M {px(ex) - 3:.1f} {py(ey) + 3:.1f} L {px(ex) + 3:.1f} {py(ey) - 3:.1f}" stroke="{tone}" stroke-width="1.4"/>')
        mx, my = (px(corner[0]) + px(ex)) / 2, (py(corner[1]) + py(ey)) / 2
        fig = f'{eg["farthest_travel_m"]:.1f} m'
        half = _tw(fig, 10) / 2
        clear = lambda cx, cy: not any(a < cx + half and cx - half < c and b < cy + 2 and cy - 9 < e for a, b, c, e in labels)
        # beside the path where a zone's name is not; above it, below it, then by the door
        lx, ly = next(((cx, cy) for cx, cy in ((mx, my - 4), (mx, my + 13), (px(dx), py(dy) - 6), (px(dx), py(dy) + 13)) if clear(cx, cy)), (mx, my - 4))
        out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="10" text-anchor="middle" fill="{tone}" stroke="{TONES["paper"]}" stroke-width="2.5" paint-order="stroke">{fig}</text>')
    bottom = oy + pd
    # the entry, on the ground floor's street side
    if fl["level"] == 0:
        ex = P(_entry_x(L, fl), 0)[0]
        out.append(f'<path d="M{ex:.1f} {bottom + 20:.1f}V{bottom + 3:.1f}M{ex - 4:.1f} {bottom + 9:.1f}L{ex:.1f} {bottom + 3:.1f}L{ex + 4:.1f} {bottom + 9:.1f}" stroke="{TONES["ink"]}" stroke-width="1.4" fill="none"/>')
        out.append(f'<text x="{ex + 6:.1f}" y="{bottom + 19:.1f}" font-size="9.5" fill="{TONES["ink"]}">entry</text>')
    # the width, dimensioned, and the street named at its edge
    dy = bottom + 27
    out.append(f'<path d="M{ox:.1f} {dy:.1f}H{ox + pw:.1f}M{ox:.1f} {dy - 4:.1f}V{dy + 4:.1f}M{ox + pw:.1f} {dy - 4:.1f}V{dy + 4:.1f}" stroke="{TONES["muted"]}" stroke-width="0.8" fill="none"/>')
    out.append(f'<text x="{ox + pw / 2:.1f}" y="{dy + 12:.1f}" font-size="10" text-anchor="middle" fill="{TONES["muted"]}">{p["width_m"]} m</text>')
    st = f"{street} · street side" if street else "street side"
    out.append(f'<text x="{ox + pw / 2:.1f}" y="{dy + 25:.1f}" font-size="10" font-weight="600" letter-spacing="0.5" text-anchor="middle" fill="{TONES["muted"]}">{_esc(st.upper())}</text>')
    out.append(f'<line x1="{ox - 12:.1f}" y1="{oy:.1f}" x2="{ox - 12:.1f}" y2="{bottom:.1f}" stroke="{TONES["muted"]}" stroke-width="0.8"/>')
    out.append(f'<text x="{ox - 16:.1f}" y="{oy + pd / 2:.1f}" font-size="10" text-anchor="middle" fill="{TONES["muted"]}" transform="rotate(-90 {ox - 16:.1f} {oy + pd / 2:.1f})">{p["depth_m"]} m</text>')


def _homes_on(fl: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for z in fl["zones"]:
        if z.get("unit"):
            out[z["unit"]] = out.get(z["unit"], 0) + 1
    return out


def _homes_words(counts: dict[str, int]) -> str:
    return ", ".join(f"{n} {UNIT_LABEL[k].lower()}" for k, n in sorted(counts.items(), key=lambda kv: UNIT_KEYS.index(kv[0])))


def _levels_words(levels: list[int]) -> str:
    """Levels as a reader counts them, the ground floor as 1: "levels 2 to 5", "levels 2, 4 and 6", "level 3". Pure."""
    ns = sorted(lv + 1 for lv in levels)
    if len(ns) == 1:
        return f"level {ns[0]}"
    if ns == list(range(ns[0], ns[-1] + 1)):
        return f"levels {ns[0]} to {ns[-1]}"
    return "levels " + ", ".join(map(str, ns[:-1])) + f" and {ns[-1]}"


def _typical_levels(L: dict) -> list[int]:
    """Which floors to draw: the ground floor, one typical residential floor, and the top floor where it differs."""
    floors = L["floors"]
    if len(floors) == 1:
        return [0]
    sig = lambda fl: tuple(sorted((z["block"], round(z["area_m2"])) for z in fl["zones"]))
    typ = max(range(1, len(floors)), key=lambda i: sum(1 for fl in floors[1:] if sig(fl) == sig(floors[i])))
    levels = [0, typ]
    top = len(floors) - 1
    if top not in levels and sig(floors[top]) != sig(floors[typ]):
        levels.append(top)
    return levels


def typical_floor(L: dict) -> dict | None:
    """What the overview's typical floor stands for (20 Nov 2026): the levels above the ground floor with the same homes
    as it (`levels`, 0-based), and those that differ, grouped by their homes (`differ`: [{levels, homes}]), the top
    floor drawn on its own included. None for a building of one floor. Pure."""
    floors = L["floors"]
    drawn = _typical_levels(L)
    if len(drawn) < 2:
        return None
    typ = drawn[1]
    same = [fl["level"] for fl in floors[1:] if _homes_on(fl) == _homes_on(floors[typ])]
    differ: list[dict] = []
    for fl in floors[1:]:
        if fl["level"] in same:
            continue
        h = _homes_on(fl)
        g = next((g for g in differ if g["homes"] == h), None)
        if g:
            g["levels"].append(fl["level"])
        else:
            differ.append({"levels": [fl["level"]], "homes": h})
    return {"level": typ, "levels": same, "differ": differ}


def svg_plans(L: dict, bearing: float | None = None, street: str | None = None) -> str:
    """Floor plans by program: the ground floor, a typical residential floor, the top floor where it differs; the
    stairs, exit doors and the entry drawn, a scale bar, the street named at its edge, and a north arrow where the
    bearing of the plate's x axis is known (`bearing`, clockwise from north)."""
    p = L["plate"]
    levels = _typical_levels(L)
    pad = 48
    # one plan per row, each as wide as the sheet allows, so the drawing stays legible in a 400 px column
    # (a plate the yards left no width or depth, 16 Nov 2026, is scaled as if it were a metre: nothing divides by zero)
    scale = max(3.0, min(560 / max(p["width_m"], 1.0), 200 / max(p["depth_m"], 1.0)))
    pw, pd = p["width_m"] * scale, p["depth_m"] * scale
    eg = L.get("egress")
    head = 14 if eg else 0
    row = pd + 84 + head
    width = max(pad + 30 + pw + pad, 640)
    inner = width - 2 * pad
    point = p.get("arrangement") == "point"
    walkup = p.get("arrangement") == "walkup"
    corr_m = LAYOUT_ASSUMPTIONS["corridor_width_m"][0]
    typ = typical_floor(L)
    arrangement = (f'A point tower: homes {p["unit_depth_m"]} m deep in front and behind, {p.get("side_depth_m")} m beside, round a {corr_m} m corridor ringing the core;' if point else
                   (f'A walk-up: one stair of {(p.get("walkup") or {}).get("stair_m", [2.6, 5.5])[0]:g} × {(p.get("walkup") or {}).get("stair_m", [2.6, 5.5])[1]:g} m and no elevator, '
                    f'every home {p["unit_depth_m"]} m deep with its door on the stair\'s landing;') if walkup else
                   f'Unit depth {p["unit_depth_m"]} m either side of a {corr_m} m corridor; core bay {LAYOUT_ASSUMPTIONS["core_bay_m"][0]} m;')
    lines = [arrangement,
             f'partitions +{int((LAYOUT_ASSUMPTIONS["partition_allowance"][0] - 1) * 100)}% over net areas (declared placeholders). The rules read back from the plates are listed with the figure.',
             *([f'The typical floor stands for {_levels_words(typ["levels"])}'
                + (("; other floors differ: " + "; ".join(f'{_levels_words(x["levels"])}, {_homes_words(x["homes"]) or "no homes"}' for x in typ["differ"])) if typ["differ"] else ", every floor above the ground the same")
                + "."] if typ else []),
             "Stairs drawn with their treads and exit doors; a switchback stair's flights either side of its divider, a scissor stair's two flights crossed; the arrow is the entry from the street.",
             *(['Each home is a block of its area: in a shallow strip it runs long along the facade, where a design would turn the corner.'] if point else []),
             *([f'Egress (BC Building Code 2024, Part 3; figures to be verified): dashed, the farthest unit door to its exit along the corridor;',
                f'{"sprinklered (assumed, a placeholder)" if eg["sprinklered_is_placeholder"] and eg["sprinklered"] else ("sprinklered" if eg["sprinklered"] else "unsprinklered")}'
                + ('.' if (point or walkup) else f'; a core {LAYOUT_ASSUMPTIONS["core_bay_m"][0]:g} m wide read as two {LAYOUT_ASSUMPTIONS["stair_width_m"][0]} m stairs at its ends.'),
                *([("The scissor stair: two stairs interlocked in one shaft, its doors on the core's opposite faces, apart by the way round it; "
                    if point else "The scissor stair: two stairs interlocked in one shaft, its doors at the core's two ends; ")
                   + "a smoke-tight rated separation between them."]
                  if eg.get("scissor_stair") else []),
                *(["One stair serves each floor as the Part 3 figure allows a floor of 150 m² or less; Part 9's own exit clauses are not in the rules, a placeholder to confirm."] if walkup else [])]
               if eg else []),
             _stamp_line(L)]
    keys = ["non_residential", "amenity", "services", "core", "corridor", "three_bed_plus", "two_bed", "one_bed", "studio", "spare"]
    legend, leg_h = _legend(pad, 0, keys, inner, short=True)
    ly = pad + 24 + len(levels) * row + 14
    bar_y = ly + leg_h + 22
    foot_y = bar_y + 44
    height = foot_y + 16 * _foot_lines(lines, inner) + 16
    out = _svg_open(width, height, "Floor plans by program")
    out.append(f'<text x="{pad}" y="{pad - 4}" font-size="14" font-weight="600">Plans by program · metres, street at the bottom</text>')
    names = {0: "Ground floor"}
    for i, lv in enumerate(levels):
        fl = L["floors"][lv]
        homes = _homes_words(_homes_on(fl))
        if lv == 0:
            name = "Ground floor"
        elif typ and lv == typ["level"]:
            name = f"Typical floor ({_levels_words(typ['levels'])})" if len(typ["levels"]) > 1 else fl["name"]
        elif lv == len(L["floors"]) - 1:
            name = f"Top floor ({_levels_words([lv])})"
        else:
            name = fl["name"]
        names[lv] = name
        spare = f' · {fl["spare_m2"]:,.0f} m² spare' if fl["spare_m2"] > 5 else ""
        title = _fit([f"{name}: {homes}{spare}" if homes else f"{name}{spare}", f"{name}: {homes}" if homes else name, name], inner - 30, 13) or name
        _plan(out, L, fl, pad + 30, pad + 24 + i * row + 14 + head, scale, title,
              eg["floors"][lv] if eg and lv < len(eg["floors"]) else None, street=street, room=inner - 30)
    out += _shift(legend, 0, ly)
    out.append(f'<circle cx="{pad + 6}" cy="{ly + leg_h + 2:.1f}" r="3.2" fill="{TONES["accessible"]}"/><text x="{pad + 16}" y="{ly + leg_h + 6:.1f}" font-size="11" fill="{TONES["muted"]}">accessible unit</text>')
    bar, bw = _scale_bar(pad, bar_y, scale)
    out += bar
    if bearing is not None:
        out += _north(pad + bw + 40, bar_y + 2, bearing)
    out += _foot(lines, pad, foot_y, inner)
    out.append("</svg>")
    return "\n".join(out)


def _step_insets(fl: dict, p: dict) -> tuple[float, float, float, float]:
    """How far a floor stands in from the plate's street side, lane side, left and right: the depth of the
    step-back's cut-outs (`void` zones marked `step`) along each edge. Zeros on a floor without one."""
    f = r = l = rt = 0.0
    for z in fl["zones"]:
        if z["block"] != "void" or not z.get("step"):
            continue
        if z["w"] >= z["d"]:
            if abs(z["y"] - p["y"]) < 0.06:
                f = max(f, z["d"])
            elif abs(z["y"] + z["d"] - p["y"] - p["depth_m"]) < 0.06:
                r = max(r, z["d"])
        if z["d"] > z["w"] or z["w"] < p["width_m"] - 0.5:
            if abs(z["x"] - p["x"]) < 0.06 and z["d"] > z["w"]:
                l = max(l, z["w"])
            elif abs(z["x"] + z["w"] - p["x"] - p["width_m"]) < 0.06 and z["d"] > z["w"]:
                rt = max(rt, z["w"])
    return f, r, l, rt


def svg_elevations(L: dict, massing: dict) -> str:
    """Front and side elevations: storeys × floor to floor, a window per unit as the rhythm, the ground floor's
    glazing where the non-residential space is, the outright height and the staff benchmark as lines; the floor levels
    marked at the left and a scale bar under them. The labels at the right of each elevation are measured and pushed
    apart, and the sheet is as wide as they are (20 Nov 2026: "22.3 m" printed over "benchmark 19.9–21.3", the side's
    "benchmark 1…" ran off the sheet, and the notes were cut mid-word)."""
    p = L["plate"]
    f2f, n = p["floor_to_floor_m"], p["storeys"]
    g_extra = max(0.0, float(p.get("ground_floor_m") or f2f) - f2f)     # a taller ground floor lifts every level above it
    H = f2f * n + g_extra
    masses = {m["name"]: m for m in massing["masses"]}
    bench = massing.get("policy_benchmark") or {}
    out_h = (L.get("outright") or {}).get("height_m") or (masses.get("outright") or {}).get("height_m")
    # one height for one building: the elevation stands as tall as the section (the option's stated height where it
    # is taller than the storeys), with the top floor level marked inside it (15 Nov 2026)
    Hp = max(H, float((masses.get("proposed") or {}).get("height_m") or 0))
    hmax = max([Hp, out_h or 0] + ([bench["height_m"][1]] if bench.get("height_m") else []))
    pad = 48
    marks = 40           # the floor level marks, left of the front elevation
    scale = max(3.0, min(380 / max(p["width_m"], 1.0), 220 / max(hmax, 1.0), 260 / max(p["depth_m"], 1.0)))
    fw, sw, eh = p["width_m"] * scale, p["depth_m"] * scale, hmax * scale
    base = pad + 24 + eh

    # the labels at the right of an elevation, at their heights
    def right_labels() -> list[tuple[float, str, str]]:
        ls = [(base - Hp * scale + 4, f"{_metres(Hp)} m", TONES["ink"])]
        # the labels in the darker twin of their line's tone (24 Nov 2026: the line greys read at 3.3:1 as 10 px text);
        # the lines keep their tones
        if out_h:
            ls.append((base - out_h * scale + 4, f"outright {_metres(out_h)} m", TONES["muted"]))
        if bench.get("height_m"):
            ls.append((base - bench["height_m"][1] * scale + 4, f"benchmark {_metres(bench['height_m'][0])}–{_metres(bench['height_m'][1])} m", TONES["benchmark_text"]))
        return ls

    lab_w = max(_tw(t, 10) for _, t, _ in right_labels()) + 20
    gap = lab_w + 36
    width = max(pad + marks + fw + gap + sw + lab_w + pad, 720)
    inner = width - 2 * pad
    lines = [f'{_metres(Hp)} m high, as the section' + (f': {n} storeys × {f2f} m{f" with a ground floor of {_metres(p['ground_floor_m'])} m" if g_extra else ""} = {_metres(H)} m to the top floor level (thin line), the {_metres(Hp - H)} m above it parapet{"" if g_extra else ", roof or a taller ground floor"}' if Hp > H + 0.05
              else f': {n} storeys × {f2f} m' + (f", the ground floor {_metres(p['ground_floor_m'])} m" if g_extra else "")),
             (f'Outright maximum height {_metres(out_h)} m, dashed grey' if out_h else "No outright height in the stack for this district"),
             *([f'Staff benchmark {_metres(bench["height_m"][0])} to {_metres(bench["height_m"][1])} m, amber'] if bench.get("height_m") else []),
             f'Windows: one per unit on its side, {LAYOUT_ASSUMPTIONS["window_width_m"][0]} m wide, the unit module as the rhythm; a placeholder for the elevation study',
             "Floor levels at the left, metres above the ground floor.",
             _stamp_line(L)]
    bar_y = base + 30
    foot_y = bar_y + 40
    height = foot_y + 16 * _foot_lines(lines, inner) + 16
    out = _svg_open(width, height, "Preliminary elevations")
    out.append(f'<text x="{pad}" y="{pad - 4}" font-size="14" font-weight="600">Elevations · metres</text>')
    win_w, _ = LAYOUT_ASSUMPTIONS["window_width_m"]
    shop_h, win_h = max(0.0, f2f - 0.9) * scale, max(0.0, f2f - 1.8) * scale   # glazing below the floor above, never negative on a low storey

    def elevation(ox: float, length: float, label: str, axis: str) -> None:
        out.append(f'<text x="{ox:.1f}" y="{pad + 14:.1f}" font-size="12" font-weight="600">{_esc(label)}</text>')
        out.append(f'<line x1="{ox - 10:.1f}" y1="{base:.1f}" x2="{ox + length + 10:.1f}" y2="{base:.1f}" stroke="{TONES["ink"]}" stroke-width="1.5"/>')
        out.append(f'<rect x="{ox:.1f}" y="{base - Hp * scale:.1f}" width="{length:.1f}" height="{Hp * scale:.1f}" fill="{TONES["lot"]}" stroke="{TONES["ink"]}" stroke-width="1.2"/>')
        if Hp > H + 0.05:
            out.append(f'<line x1="{ox:.1f}" y1="{base - H * scale:.1f}" x2="{ox + length:.1f}" y2="{base - H * scale:.1f}" stroke="{TONES["muted"]}" stroke-width="0.6" stroke-dasharray="3 2"/>')
        below = (0.0, 0.0)
        for fl in L["floors"]:
            y_top = base - (fl["z"] + f2f) * scale
            y_floor = base - fl["z"] * scale
            # a stepped floor (the step-back's cut-outs along its edges) stands in from the face below: the strip it
            # gives up is cleared to the top of the building and its own face drawn, the roof of the floor below under it
            ins = _step_insets(fl, p)
            a, b = (ins[2], ins[3]) if axis == "x" else (ins[0], ins[1])
            top = base - Hp * scale if fl["level"] == len(L["floors"]) - 1 else y_top
            for cut, x_at, edge in ((a, ox - 1.5, ox + a * scale), (b, ox + length - b * scale, ox + length - b * scale)):
                if cut > 0.05:
                    out.append(f'<rect x="{x_at:.1f}" y="{top - 1.5:.1f}" width="{cut * scale + 1.5:.1f}" height="{y_floor - top + 1.5:.1f}" fill="{TONES["paper"]}"/>')
                    out.append(f'<line x1="{edge:.1f}" y1="{top:.1f}" x2="{edge:.1f}" y2="{y_floor:.1f}" stroke="{TONES["ink"]}" stroke-width="1.2"/>')
            if a > 0.05 or b > 0.05:
                out.append(f'<line x1="{ox + a * scale:.1f}" y1="{top:.1f}" x2="{ox + length - b * scale:.1f}" y2="{top:.1f}" stroke="{TONES["ink"]}" stroke-width="{1.2 if fl["level"] == len(L["floors"]) - 1 else 0}"/>')
            if fl["level"]:
                la, lb = min(a, below[0]), min(b, below[1])
                roof = a > below[0] + 0.05 or b > below[1] + 0.05
                out.append(f'<line x1="{ox + la * scale:.1f}" y1="{y_floor:.1f}" x2="{ox + length - lb * scale:.1f}" y2="{y_floor:.1f}" stroke="{TONES["ink"] if roof else TONES["muted"]}" stroke-width="{1.2 if roof else 0.6}"/>')
            below = (a, b)
            # windows: the zones on the face this elevation looks at
            face = [z for z in fl["zones"] if (axis == "x" and z.get("side") == "front") or (axis == "y" and z["block"] not in ("corridor",) and z.get("side") in ("front", "rear"))]
            if axis == "x":
                for z in face:
                    cx = ox + (z["x"] - p["x"] + z["w"] / 2) * scale
                    if z["block"] in ("non_residential", "amenity"):
                        out.append(f'<rect x="{ox + (z["x"] - p["x"]) * scale + 2:.1f}" y="{y_top + 0.5 * scale:.1f}" width="{max(2, z["w"] * scale - 4):.1f}" height="{shop_h:.1f}" fill="{TONES["studio"]}" stroke="{TONES["muted"]}" stroke-width="0.6"/>')
                    elif z.get("unit"):
                        out.append(f'<rect x="{cx - win_w * scale / 2:.1f}" y="{y_top + 0.9 * scale:.1f}" width="{win_w * scale:.1f}" height="{win_h:.1f}" fill="{TONES["two_bed"]}" stroke="{TONES["muted"]}" stroke-width="0.6"/>')
            else:
                # the side elevation sees the end unit of each strip: one window per strip, placed at its depth
                for side, yy in (("front", p["y"]), ("rear", p["y"] + p["depth_m"] - p["unit_depth_m"])):
                    if any(z.get("unit") and z.get("side") == side for z in fl["zones"]):
                        cx = ox + (yy - p["y"] + p["unit_depth_m"] / 2) * scale
                        out.append(f'<rect x="{cx - win_w * scale / 2:.1f}" y="{y_top + 0.9 * scale:.1f}" width="{win_w * scale:.1f}" height="{win_h:.1f}" fill="{TONES["two_bed"]}" stroke="{TONES["muted"]}" stroke-width="0.6"/>')
        if out_h:
            yo = base - out_h * scale
            out.append(f'<line x1="{ox - 10:.1f}" y1="{yo:.1f}" x2="{ox + length + 10:.1f}" y2="{yo:.1f}" stroke="{TONES["outright"]}" stroke-width="1" stroke-dasharray="5 3"/>')
        if bench.get("height_m"):
            for hv in bench["height_m"]:
                yb = base - hv * scale
                out.append(f'<line x1="{ox - 10:.1f}" y1="{yb:.1f}" x2="{ox + length + 10:.1f}" y2="{yb:.1f}" stroke="{TONES["benchmark"]}" stroke-width="1" stroke-dasharray="4 3"/>')
        # the labels, pushed apart where their lines sit close, a leader to the line where one moved
        lx = ox + length + 14
        for want, got, text, tone in _spread(right_labels(), gap=12.0, top=pad + 22, bottom=base + 4):
            if abs(got - want) > 0.5:
                out.append(f'<line x1="{ox + length + 10:.1f}" y1="{want - 4:.1f}" x2="{lx - 2:.1f}" y2="{got - 4:.1f}" stroke="{tone}" stroke-width="0.6"/>')
            out.append(f'<text x="{lx:.1f}" y="{got:.1f}" font-size="10" fill="{tone}">{_esc(text)}</text>')

    fx = pad + marks
    elevation(fx, fw, "Front elevation · from the street", "x")
    elevation(fx + fw + gap, sw, "Side elevation · street at the left", "y")
    # the floor levels, left of the front elevation: the ground at 0 and each floor above it
    seen: list[float] = []
    for fl in L["floors"]:
        y = base - fl["z"] * scale
        if seen and abs(seen[-1] - y) < 11:      # never closer than a line of type
            continue
        seen.append(y)
        out.append(f'<line x1="{fx - 14:.1f}" y1="{y:.1f}" x2="{fx - 10:.1f}" y2="{y:.1f}" stroke="{TONES["muted"]}" stroke-width="0.8"/>')
        mark = "±0.0" if not fl["level"] else "+" + _metres(fl["z"])
        out.append(f'<text x="{fx - 16:.1f}" y="{y + 3:.1f}" font-size="9" text-anchor="end" fill="{TONES["muted"]}">{mark}</text>')
    bar, _ = _scale_bar(fx, bar_y, scale)
    out += bar
    out += _foot(lines, pad, foot_y, inner)
    out.append("</svg>")
    return "\n".join(out)


def svg_axon(L: dict) -> str:
    """The floors stacked in a simple oblique axonometric, each zone drawn on its plate: the stacking as a reader
    sees it in three dimensions."""
    p = L["plate"]
    k = 0.5   # the oblique's depth factor
    ang = 0.5235987756  # 30 degrees
    import math
    cos, sin = math.cos(ang) * k, math.sin(ang) * k
    scale = max(3.0, min(360 / max(p["width_m"] + p["depth_m"] * cos, 1.0), 260 / max(p["storeys"] * p["floor_to_floor_m"] + p["depth_m"] * sin, 1.0)))
    pad = 48
    width = pad + (p["width_m"] + p["depth_m"] * cos) * scale + pad
    height = pad + 24 + (p["storeys"] * p["floor_to_floor_m"] + p["depth_m"] * sin) * scale + 40 + 16 * 3 + 16 + 30
    out = _svg_open(max(width, 640), height, "Axonometric of the stacked floors")
    out.append(f'<text x="{pad}" y="{pad - 4}" font-size="14" font-weight="600">Axonometric · the floors lifted apart, street at the front</text>')
    ox = pad
    base = pad + 24 + (p["storeys"] * p["floor_to_floor_m"] + p["depth_m"] * sin) * scale
    lift = p["floor_to_floor_m"] * scale * 1.0

    def pt(x: float, y: float, z: float) -> str:
        X = ox + (x - p["x"]) * scale + (p["depth_m"] - (y - p["y"])) * cos * scale
        Y = base - z * scale - (p["depth_m"] - (y - p["y"])) * sin * scale
        return f"{X:.1f},{Y:.1f}"

    for fl in L["floors"]:
        z = fl["level"] * lift / scale
        out.append(f'<polygon points="{pt(p["x"], p["y"], z)} {pt(p["x"] + p["width_m"], p["y"], z)} {pt(p["x"] + p["width_m"], p["y"] + p["depth_m"], z)} {pt(p["x"], p["y"] + p["depth_m"], z)}" fill="{TONES["lot"]}" stroke="{TONES["ink"]}" stroke-width="1"/>')
        for zn in sorted(fl["zones"], key=lambda q: -(q["y"] + q["d"])):
            out.append(f'<polygon points="{pt(zn["x"], zn["y"], z)} {pt(zn["x"] + zn["w"], zn["y"], z)} {pt(zn["x"] + zn["w"], zn["y"] + zn["d"], z)} {pt(zn["x"], zn["y"] + zn["d"], z)}" fill="{TONES[zn["block"]]}" stroke="{TONES["muted"]}" stroke-width="0.6"/>')
        out.append(f'<text x="{ox + (p["width_m"] + p["depth_m"] * cos) * scale + 6:.1f}" y="{base - z * scale - 2:.1f}" font-size="10" fill="{TONES["muted"]}">{_esc(fl["name"])}</text>')
    # an oblique keeps the frontage and the heights to scale, not the depth: the bar reads along the frontage
    bar, bw = _scale_bar(pad, base + 18, scale)
    out += bar
    out.append(f'<text x="{pad + bw + 12:.1f}" y="{base + 27:.1f}" font-size="9.5" fill="{TONES["muted"]}">along the frontage and in height; the depth is drawn at half</text>')
    out += _foot([f'{p["storeys"]} floors of {p["width_m"]} × {p["depth_m"]} m, lifted one storey apart to show the program', _stamp_line(L)], pad, base + 58,
                 max(width, 640) - 2 * pad)
    out.append("</svg>")
    return "\n".join(out)


def _wrap_words(text: str, width: int) -> list[str]:
    """A line of words broken at spaces into lines of at most `width` characters (a longer word stands alone). Pure."""
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    return lines + ([cur] if cur else [])


def _cuts(ring: list, at: float, axis: str) -> list[float]:
    """Where the line x = at (axis "x") or y = at (axis "y") crosses a polygon's edges: the other coordinate of each
    crossing, sorted. Pure."""
    hits = []
    n = len(ring)
    for i in range(n):
        (x1, y1), (x2, y2) = ring[i], ring[(i + 1) % n]
        a1, a2, b1, b2 = (x1, x2, y1, y2) if axis == "x" else (y1, y2, x1, x2)
        if (a1 - at) * (a2 - at) <= 0 and a1 != a2:
            hits.append(b1 + (at - a1) / (a2 - a1) * (b2 - b1))
    return sorted(hits)


def svg_site_plan(L: dict, site: dict, massing: dict, ledger: dict, bearing: float | None = None, street: str | None = None) -> str:
    """The code site plan: the lot, the yards dimensioned on the lot (a polygon lot's too, measured across at the
    envelope's middle), the setback envelope, the footprint, the retained trees' protection barriers where the site
    records positions, a scale bar, the street named at its edge, a north arrow where the bearing is known, and the
    table a plan checker reads: FSR, coverage, height and yards against the schedule where the stack has one. The
    table's columns are measured from what they hold, and the plan takes the sheet's width (20 Nov 2026: cells printed
    over the status column, a band of empty paper sat beside the plan, the side labels straddled the lot line, the
    lot's caption ran off the sheet and a polygon lot's yards had no dimension)."""
    lot, env = massing["lot"], massing["envelope"]
    W, D = lot["frontage_m"], lot["depth_m"]
    sb = env["setbacks_m"]
    pm = next(m for m in massing["masses"] if m["name"] == "proposed")
    results = ledger["results"]
    pad = 48
    bb = lot.get("bbox") or [0, 0, W, D]      # a polygon lot is drawn as itself, in its own extent
    polygon_lot = bool(lot.get("bbox"))
    bw, bd = max(bb[2] - bb[0], 1.0), max(bb[3] - bb[1], 1.0)
    foot = float(pm["plate_area_m2"]) if pm.get("parts") else pm["plate_width_m"] * pm["plate_depth_m"]      # a plate in two parts: its own area, not the rectangle round it
    rows = [("Site area", f'{lot["area_m2"]:,.1f} m²', "", "")]
    fsr = _find(results, check="district_outright_fsr")
    rows.append(("Floor space ratio", f'{pm["fsr"]:.2f} ({pm["gfa_m2"]:,.0f} m²)', f'{fsr["values"].get("max_fsr_outright")} outright' if fsr else "no schedule in the stack", fsr["status"] if fsr else "info"))
    hgt = _find(results, check="district_outright_height")
    rows.append(("Height", f'{pm["height_m"]} m, {pm["storeys"]} storeys', f'{hgt["values"].get("max_height_m_outright")} m outright' if hgt else "no schedule in the stack", hgt["status"] if hgt else "info"))
    cov_rule = next((r for r in results if r["rule_id"].endswith(".site_coverage") and r["status"] != "not_applicable"), None)
    area = float(lot["area_m2"] or 0) or 1.0
    rows.append(("Site coverage", f'{foot / area * 100:.0f}% ({foot:,.0f} m²)', f'{cov_rule["values"].get("max_site_coverage", 0) * 100:.0f}% maximum' if cov_rule else "no schedule in the stack", ("pass" if foot / area <= cov_rule["values"].get("max_site_coverage", 1) else "conditional") if cov_rule else "info"))
    yards = _find(results, check="district_setbacks")
    for k in ("front", "rear", "side"):
        mn = (yards or {}).get("values", {}).get(f"min_{k}_yard_m") if yards else None
        # with no yard rule in the stack the yards are the option's own figures, unchecked: the same Uncertain answer 3
        # gives coverage.yards (24 Nov 2026; this row read "placeholder · info" beside answer 3's "not checked")
        rows.append((f"{k.capitalize()} yard", f'{sb.get(k)} m', f'{mn} m minimum' if mn is not None else ("not checked: no yard rule in the rules" if not yards else "not given"), ("pass" if sb.get(k, 0) + 1e-9 >= mn else "conditional") if mn is not None else ("uncertain" if not yards else "info")))
    trees = massing.get("trees") or {}
    rows.append(("Trees", f'{trees.get("after", "?")} after development', f'Schedule C requires {trees.get("required", "?")}', "pass" if trees and (trees.get("shortfall") or 0) == 0 else "conditional") if trees else ("Trees", "no survey on file", "", "uncertain"))
    ans = ledger["summary"]["answers"]["allowed"]
    # the verdict and the path run long: they go under the table as lines of their own, not in its columns
    allowed = [f'Allowed outright: {ans["outright"]["verdict"]}' + (f'; by rezoning: {ans["by_rezoning"]["verdict"]}' if ans.get("rezoning_path") else ""),
               f'Path: {ans["rezoning_path"]}' if ans.get("rezoning_path") else "No rezoning path stated"]
    # the columns, each as wide as its widest cell at its own size, and a gutter between
    gut = 18
    widest = [max(_tw(r[i], 11) for r in rows) for i in range(3)] + [max(_tw(r[3], 10.5) for r in rows)]
    cols = (0, widest[0] + gut, widest[0] + widest[1] + 2 * gut, widest[0] + widest[1] + widest[2] + 3 * gut)
    table_w = cols[3] + widest[3]
    width = max(pad + table_w + pad, 680)
    inner = width - 2 * pad
    # project north (24 Nov 2026, Kai: "the plans should always show project north"; FIG 01 is drawn so, and this sheet
    # stood street-down beside it): the lot frame turned on the page by the quarter turn nearest north up. rot gives a
    # lot point's direction on the page (y down); the street's side of the lot faces street_dir on the page.
    q = project_turn(bearing)
    cq, sq = round(math.cos(math.radians(q))), round(math.sin(math.radians(q)))
    rot = lambda x, y: (cq * x + sq * y, sq * x - cq * y)
    box_c = [rot(x, y) for x, y in ((bb[0], bb[1]), (bb[2], bb[1]), (bb[2], bb[3]), (bb[0], bb[3]))]
    u0, v0 = min(c[0] for c in box_c), min(c[1] for c in box_c)
    pw_m, pd_m = max(max(c[0] for c in box_c) - u0, 1.0), max(max(c[1] for c in box_c) - v0, 1.0)
    street_dir = (-sq, cq)      # (0, 1) the bottom, (0, -1) the top, (-1, 0) the left, (1, 0) the right
    # the plan takes the sheet's width, at most 320 px tall, with room for the street's name on the side it is on
    scale = max(3.0, min((inner - 60 - (34 if street_dir[0] else 0)) / pw_m, 320 / pd_m))
    pw, pd = pw_m * scale, pd_m * scale
    ox = pad + 30 + max(0.0, (inner - 60 - pw) / 2)
    if street_dir[0] < 0:
        ox = max(ox, pad + 40)
    oy = pad + 24 + (30 if street_dir[1] < 0 else 0)
    allowed = [ln for a in allowed for ln in _wrap_words(a, max(40, int(inner / (11 * EM_PER_CHAR))))]
    # the caption under the lot, wrapped to the sheet
    trees_barriers = {b.get("tree"): b.get("barrier_m") for b in (trees.get("retained_barriers") or [])}
    ctx_trees = ((site.get("context") or {}).get("trees") or [])
    placed_trees = [t for t in ctx_trees if t.get("x") is not None and t.get("y") is not None]
    drawn = sum(1 for t in placed_trees if trees_barriers.get(t.get("id")))
    lot_words = ((f'Lot polygon {lot.get("polygon_area_m2", lot["area_m2"]):,.0f} m² ({(lot.get("shape") or {}).get("class", "polygon").replace("_", " ")}); dashed red: the setback envelope, '
                  f'dotted: the plate box {env["width_m"]} × {env["depth_m"]} m' if polygon_lot else f'Lot {W} × {D} m; dashed red: the setback envelope {env["width_m"]} × {env["depth_m"]} m')
                 + '; blue: the footprint' + (f'; {drawn} protection barrier{"s" if drawn != 1 else ""} (By-law 9958, Schedule A)' if drawn else ('; the retained trees have no surveyed position, so no barriers are drawn' if trees_barriers else "")) + '.')
    cap_lines = _wrap_words(lot_words, max(40, int(inner / (11 * EM_PER_CHAR))))
    street_y = oy + pd + (30 if street_dir == (0, 1) else 14)
    bar_y = street_y + 16
    cap_y = bar_y + 36
    ty = round(cap_y + 16 * len(cap_lines) + 8, 1)
    table_h = 34 + 18 * len(rows) + 10 + 16 * len(allowed)
    foot_y = ty + table_h + 14
    height = foot_y + 16 + 16
    out = _svg_open(width, height, "Code site plan")
    out.append(f'<text x="{pad}" y="{pad - 4}" font-size="14" font-weight="600">Code site plan · metres, {"project north up" if bearing is not None else "street at the bottom"}</text>')
    # a lot point on the sheet: turned to project north, then scaled from the turned extent's top-left
    T = lambda x, y: (ox + (rot(x, y)[0] - u0) * scale, oy + (rot(x, y)[1] - v0) * scale)
    pts = lambda ring: " ".join(f"{T(x, y)[0]:.1f},{T(x, y)[1]:.1f}" for x, y in ring)
    lot_ring = lot.get("polygon") or [[0, 0], [W, 0], [W, D], [0, D]]
    env_ring = env.get("polygon") or []
    out.append(f'<polygon points="{pts(lot_ring)}" fill="{TONES["lot"]}" stroke="{TONES["ink"]}" stroke-width="1.5"/>')
    if env_ring:
        out.append(f'<polygon points="{pts(env_ring)}" fill="none" stroke="{TONES["envelope"]}" stroke-width="1.2" stroke-dasharray="6 4"/>')
    if polygon_lot and (env.get("box") or {}).get("ring"):
        out.append(f'<polygon points="{pts(env["box"]["ring"])}" fill="none" stroke="{TONES["envelope"]}" stroke-width="0.8" stroke-dasharray="2 2"/>')    # a turned plate box
    elif polygon_lot and env.get("box"):
        bx = env["box"]
        box_ring = [[bx["x"], bx["y"]], [bx["x"] + bx["w"], bx["y"]], [bx["x"] + bx["w"], bx["y"] + bx["d"]], [bx["x"], bx["y"] + bx["d"]]]
        out.append(f'<polygon points="{pts(box_ring)}" fill="none" stroke="{TONES["envelope"]}" stroke-width="0.8" stroke-dasharray="2 2"/>')
    # the footprint as the massing has it: a rectangle, turned where the architect turned the mass
    out.append(f'<polygon points="{pts(pm["footprint"])}" fill="{TONES["two_bed"]}" fill-opacity="0.55" stroke="{TONES["accessible"]}" stroke-width="1.2"/>')
    fp_page = [T(x, y) for x, y in pm["footprint"]]
    fx, fy = min(p[0] for p in fp_page), min(p[1] for p in fp_page)     # its top-left on the sheet
    fp_words = (f'two parts, {pm["plate_area_m2"]:,.0f} m² a floor, {pm["storeys"]} storeys' if pm.get("parts") else
                f'{pm["plate_width_m"]} × {pm["plate_depth_m"]} m, {pm["storeys"]} storeys' + (f', turned {pm["angle_deg"]:g}°' if pm.get("angle_deg") else ""))
    fp_room = max(p[0] for p in fp_page) - fx
    if _tw(fp_words, 10) + 8 > fp_room:
        fp_words = _fit([fp_words, f'{pm["plate_width_m"]} × {pm["plate_depth_m"]} m', f'{pm["storeys"]} st.'], fp_room - 4, 10) or ""
    if fp_words:
        out.append(f'<text x="{fx + 6:.1f}" y="{fy + 14:.1f}" font-size="10" fill="{TONES["ink"]}" stroke="{TONES["paper"]}" stroke-width="2.5" paint-order="stroke">{_esc(fp_words)}</text>')
    # the yards, dimensioned on the lot: across the envelope's middle, from the lot line to the envelope line
    if env_ring:
        ex = [x for x, _ in env_ring]
        ey = [y for _, y in env_ring]
        mx, my = (min(ex) + max(ex)) / 2, (min(ey) + max(ey)) / 2
        lot_v, env_v = _cuts(lot_ring, mx, "x"), _cuts(env_ring, mx, "x")
        lot_h, env_h = _cuts(lot_ring, my, "y"), _cuts(env_ring, my, "y")
        dims = []
        if lot_v and env_v:
            dims.append(("front", (mx, lot_v[0]), (mx, env_v[0])))
            dims.append(("rear", (mx, env_v[-1]), (mx, lot_v[-1])))
        if lot_h and env_h:
            dims.append(("side", (lot_h[0], my), (env_h[0], my)))
            dims.append(("side", (env_h[-1], my), (lot_h[-1], my)))
        # a dimension runs up the sheet (its label beside it) or across it (its label by the side-label rule); street
        # down, the front and rear run up and the sides across, as before the turn
        upright = lambda a, b: abs(T(*a)[0] - T(*b)[0]) < abs(T(*a)[1] - T(*b)[1])
        across = [f"{k} {sb.get(k)} m" for k, a, b in dims if not upright(a, b)]
        side_w = max((_tw(t, 9.5) for t in across), default=0.0)
        env_page = [T(x, y)[0] for x, y in env_ring]
        env_px = max(env_page) - min(env_page)
        # the labels across: inside the envelope where both fit, else outside the lot where the sheet has room (not on
        # the street's side, where its name stands), else one above the other; never across the lot line
        outside_ok = not street_dir[0] and min(ox - pad, width - pad - (ox + pw)) >= side_w + 6
        side_mode = "inside" if 2 * side_w + 16 <= env_px else ("outside" if outside_ok else "stagger")
        for k, a, b in dims:
            (x1, y1), (x2, y2) = T(*a), T(*b)
            if abs(x1 - x2) + abs(y1 - y2) < 2:
                continue
            tone = TONES["envelope"]
            out.append(f'<path d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}" stroke="{tone}" stroke-width="0.8" fill="none" marker-start="url(#tick)" marker-end="url(#tick)"/>')
            lab = f"{k} {sb.get(k)} m"
            if upright(a, b):
                # beside the line, inside the lot
                out.append(f'<text x="{x1 + 4:.1f}" y="{(y1 + y2) / 2 + 3.5:.1f}" font-size="9.5" fill="{tone}" stroke="{TONES["paper"]}" stroke-width="2.5" paint-order="stroke">{_esc(lab)}</text>')
                continue
            left = min(x1, x2) < ox + pw / 2
            if side_mode == "outside":
                tx, anchor, ty_ = (min(x1, x2) - 4, "end", y1 + 3.5) if left else (max(x1, x2) + 4, "start", y1 + 3.5)
            else:
                tx, anchor = (max(x1, x2) + 4, "start") if left else (min(x1, x2) - 4, "end")
                ty_ = y1 - 4 if (left or side_mode == "inside") else y1 + 12
            out.append(f'<text x="{tx:.1f}" y="{ty_:.1f}" font-size="9.5" text-anchor="{anchor}" fill="{tone}" stroke="{TONES["paper"]}" stroke-width="2.5" paint-order="stroke">{_esc(lab)}</text>')
        out.insert(2, f'<defs><marker id="tick" viewBox="0 0 6 6" refX="3" refY="3" markerWidth="6" markerHeight="6" orient="auto"><path d="M3 0V6" stroke="{TONES["envelope"]}" stroke-width="1.2"/></marker></defs>')
    # trees with a position and a barrier
    for t in placed_trees:
        r = trees_barriers.get(t.get("id"))
        cx, cy = T(float(t["x"]), float(t["y"]))
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{max(3, 1.5 * scale / 2):.1f}" fill="{TONES["tree"]}" stroke="{TONES["tree_line"]}" stroke-width="0.8"/>')
        if r:
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{float(r) * scale:.1f}" fill="none" stroke="{TONES["tree_line"]}" stroke-width="0.8" stroke-dasharray="3 2"/>')
    # the street, named at its edge, on whichever side of the sheet the turn put it
    st = _esc((f"{street} · street side" if street else "street side").upper())
    street_text = f'font-size="10" font-weight="600" letter-spacing="0.5" text-anchor="middle" fill="{TONES["muted"]}"'
    rule = f'stroke="{TONES["muted"]}" stroke-width="0.8" stroke-dasharray="1 3"'
    if street_dir == (0, 1):
        out.append(f'<line x1="{ox:.1f}" y1="{oy + pd + 12:.1f}" x2="{ox + pw:.1f}" y2="{oy + pd + 12:.1f}" {rule}/>')
        out.append(f'<text x="{ox + pw / 2:.1f}" y="{street_y:.1f}" {street_text}>{st}</text>')
    elif street_dir == (0, -1):
        out.append(f'<line x1="{ox:.1f}" y1="{oy - 12:.1f}" x2="{ox + pw:.1f}" y2="{oy - 12:.1f}" {rule}/>')
        out.append(f'<text x="{ox + pw / 2:.1f}" y="{oy - 18:.1f}" {street_text}>{st}</text>')
    else:
        sx = ox - 12 if street_dir[0] < 0 else ox + pw + 12
        tx_, turn = (sx - 6, -90) if street_dir[0] < 0 else (sx + 6, 90)
        out.append(f'<line x1="{sx:.1f}" y1="{oy:.1f}" x2="{sx:.1f}" y2="{oy + pd:.1f}" {rule}/>')
        out.append(f'<text x="{tx_:.1f}" y="{oy + pd / 2:.1f}" transform="rotate({turn} {tx_:.1f} {oy + pd / 2:.1f})" {street_text}>{st}</text>')
    bar, bwid = _scale_bar(pad, bar_y, scale)
    out += bar
    if bearing is not None:
        out += _north(pad + bwid + 40, bar_y + 2, bearing - q)   # true north on the turned sheet
    for i, ln in enumerate(cap_lines):
        out.append(f'<text x="{pad}" y="{cap_y + i * 16:.1f}" font-size="11" fill="{TONES["muted"]}">{_esc(ln)}</text>')
    # the table
    tx = pad
    out.append(f'<text x="{tx}" y="{ty + 12:.1f}" font-size="12" font-weight="600">What the plan checker reads</text>')
    for i, (k, v, lim, stt) in enumerate(rows):
        y = ty + 34 + i * 18
        out.append(f'<line x1="{tx}" y1="{y + 5:.1f}" x2="{tx + table_w:.1f}" y2="{y + 5:.1f}" stroke="{TONES["rule"]}" stroke-width="0.8"/>')
        out.append(f'<text x="{tx + cols[0]:.1f}" y="{y:.1f}" font-size="11" fill="{TONES["muted"]}">{_esc(k)}</text>')
        out.append(f'<text x="{tx + cols[1]:.1f}" y="{y:.1f}" font-size="11">{_esc(v)}</text>')
        if lim:
            out.append(f'<text x="{tx + cols[2]:.1f}" y="{y:.1f}" font-size="11" fill="{TONES["muted"]}">{_esc(lim)}</text>')
        if stt:
            out.append(f'<text x="{tx + cols[3]:.1f}" y="{y:.1f}" font-size="10.5" font-weight="600" fill="{STATUS_TONE.get(stt, "#5f6672")}">{_esc(stt)}</text>')
    ay = ty + 34 + len(rows) * 18 + 14
    for i, ln in enumerate(allowed):
        weight = "" if i else ' font-weight="600"'
        out.append(f'<text x="{tx}" y="{ay + i * 16:.1f}" font-size="11"{weight}>{_esc(ln)}</text>')
    out += _foot([_stamp_line(L)], pad, foot_y, inner)
    out.append("</svg>")
    return "\n".join(out)


SHEETS = ("stacking", "plans", "elevations", "axon", "site-plan")


def project_turn(bearing: float | None) -> int:
    """The quarter turn, clockwise on the sheet, that brings a street-down drawing nearest north up: 0, 90, 180 or -90,
    and 0 where the bearing is not known. The page's projectTurn (figures/common.js) is the twin; FIG 01 and the code
    site plan turn by it. Pure."""
    if bearing is None:
        return 0
    t = ((float(bearing) - 90) % 360 + 540) % 360 - 180
    q = int(math.floor(t / 90 + 0.5)) * 90
    return q + 360 if q <= -180 else q


def lot_bearing(site: dict, massing: dict) -> float | None:
    """The bearing of the lot frame's x axis (along the frontage), clockwise from north, where the site's context frame
    gives it (`osm.frame.x_axis_bearing_deg`); a lot turned to another front (`lot.orientation`, θ anticlockwise) adds
    θ, as the page's siteContext does. None without a frame. Pure."""
    b = (((site or {}).get("osm") or {}).get("frame") or {}).get("x_axis_bearing_deg")
    if not isinstance(b, (int, float)) or isinstance(b, bool):
        return None
    turn = float((((massing or {}).get("lot") or {}).get("orientation") or {}).get("rotate_deg") or 0)
    return (float(b) + turn) % 360


def sheets(L: dict, site: dict, massing: dict, ledger: dict) -> dict[str, str]:
    from .checks import front_street
    bearing = lot_bearing(site, massing)
    street = front_street(site or {})
    # the plans are drawn in the plate's own frame: a mass turned anticlockwise by angle_deg turns its x axis with it
    angle = float(next((m.get("angle_deg") or 0 for m in massing.get("masses") or [] if m.get("name") == "proposed"), 0) or 0)
    plate_bearing = None if bearing is None else (bearing - angle) % 360
    return {"stacking": svg_stacking(L), "plans": svg_plans(L, plate_bearing, street), "elevations": svg_elevations(L, massing), "axon": svg_axon(L),
            "site-plan": svg_site_plan(L, site, massing, ledger, bearing, street)}


def write(L: dict, site: dict, massing: dict, ledger: dict, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {"layout.json": out_dir / "layout.json"}
    paths["layout.json"].write_text(json.dumps(L, indent=2, ensure_ascii=False), encoding="utf-8")
    if L.get("area_schedule"):
        paths["area-schedule.csv"] = out_dir / "area-schedule.csv"
        paths["area-schedule.csv"].write_text(area_schedule_csv(L["area_schedule"]), encoding="utf-8")
    for name, text in sheets(L, site, massing, ledger).items():
        p = out_dir / f"{name}.svg"
        p.write_text(text, encoding="utf-8")
        paths[p.name] = p
    return paths


def markdown(L: dict) -> list[str]:
    """The memo's layout section: the program, the stacking, the rules that held, what did not fit."""
    M: list[str] = []
    M.append("## Layouts derived from the option")
    p = L["plate"]
    wu = p.get("walkup") or {}
    go = p.get("ground_oriented") or {}
    shape = (f"ground-oriented {go.get('homes', 'homes')}, each with its own door, in {go.get('rows')} row{'s' if go.get('rows') != 1 else ''} {go.get('row_depth_m')} m deep"
             + (f" either side of a {go.get('courtyard_m')} m courtyard" if go.get("courtyard_m") else "") + ", no corridor or lift"
             if p.get("arrangement") == "ground_oriented" else
             f"a tower: a podium, and {p['storeys'] - p['tower']['from_level']} tower floors of {p['tower']['w']:g} × {p['tower']['d']:g} m over it"
             if p.get("arrangement") == "tower" else
             f"a point tower, the homes round a corridor ringing the core, {p['unit_depth_m']} m deep in front and behind and {p.get('side_depth_m')} m beside"
             if p.get("arrangement") == "point" else
             (f"a walk-up, one stair and no elevator, every home the plate's full depth ({p['unit_depth_m']} m) with its door on the stair's landing, "
              + ("one each side of the stair" if wu.get("homes_per_floor") == 2 else "one a floor beside the stair"))
             if p.get("arrangement") == "walkup" else
             f"{'a double-loaded corridor' if p['double_loaded'] else 'a single-loaded plate, the depth is the limit'}, units {p['unit_depth_m']} m deep")
    M.append(f"{p['storeys']} floors of {p['width_m']} × {p['depth_m']} m ({p['width_m'] * p['depth_m']:,.0f} m² each); {shape}; {L['units_placed']} of {L['units_total']} units placed.")
    if p.get("grid"):
        M.append(f"Laid out on a {p['grid']['bay_m']:g} m structural bay, the blocks' walls on a {p['grid']['module_m']:g} m module (`layout.grid` on the option, the architect's choice).")
    M.append("")
    M.append("| Block | Count | Area | From |")
    M.append("|---|---|---|---|")
    for b in L["program"]:
        M.append(f"| {b['label']} | {b['count']} | {b['area_m2']:,.0f} m² | {'`' + b['source'] + '`' if b['source'] != 'placeholder' else 'placeholder'}: {b['note']} |")
    if L["parking"]["spaces"]:
        M.append(f"| Parking | {L['parking']['spaces']} | {L['parking']['area_m2']:,.0f} m² | placeholder: {L['parking']['where']} |")
    M.append("")
    if L.get("edited"):
        M.append("Placed by hand in the block editor and re-checked by the engine; the option file carries the placement under `layout.zones`, so this run reproduces it.")
        M.append("")
    M.append("Adjacency rules, in plain words, read back from the plates:")
    M.append("")
    for c in L["adjacencies"]:
        M.append(f"- *{c['status']}* — {c['block'].replace('_', ' ')}: {c['rule']}. {c['note'][0].upper() + c['note'][1:] if c['note'] else ''}")
    for g in L.get("geometry") or []:
        M.append(f"- *broken* — {g['note']}.")
    if L["shortfall"]:
        M.append("")
        M.append("Did not fit on the plates: " + "; ".join(f"{s['label']}{' × ' + str(s['units']) if s.get('units') else ''} ({s['area_m2']:,.0f} m²)" for s in L["shortfall"]) + ". More storeys, a larger plate or a smaller program.")
    for w in L.get("warnings") or []:
        M.append(f"- Note: {w}")
    M.append("")
    eg = L.get("egress")
    if eg:
        M.append("### Egress")
        M.append("")
        M.append(f"{eg['summary']} Read against `{eg['rule_id']}` (BC Building Code 2024, Div B 3.4.2.1, 3.4.2.3, 3.4.2.5, 3.3.1.9; figures entered from recollection and to be verified against the code text). "
                 + ("Sprinklered is assumed (a declared placeholder; `sprinklered: false` on the option switches the limits). " if eg["sprinklered_is_placeholder"] else ("Sprinklered, as the option states. " if eg["sprinklered"] else "Unsprinklered, as the option states. "))
                 + f"Exits are the core zones, a core {LAYOUT_ASSUMPTIONS['core_bay_m'][0]:g} m wide or wider read as two {LAYOUT_ASSUMPTIONS['stair_width_m'][0]} m stairs at its ends (a placeholder); travel runs from a unit's door along the corridor to the nearest core.")
        M.append("")
        for f in eg["floors"]:
            M.append(f"- *{f['status']}* — {f['name']}: {egress_line(f).rsplit(' · ', 1)[0]}." + (" " + "; ".join(f["notes"])[0].upper() + "; ".join(f["notes"])[1:] + "." if f["notes"] else ""))
        M.append("")
    M += area_schedule_markdown(L)
    ob = L.get("operability")
    if ob:
        M.append("### What an operator checks first")
        M.append("")
        for i in ob["items"]:
            M.append(f"- *{i['status']}* — {i['label']}: {i['note']}")
        M.append("")
    for name, cap in (("stacking", "Stacking diagram"), ("plans", "Plans by program"), ("elevations", "Preliminary elevations"), ("axon", "The floors stacked"), ("site-plan", "Code site plan")):
        M.append(f"![{cap}]({name}.svg)")
        M.append("")
    M.append("`layout.json` carries the blocks, the rules and every zone's coordinates; placeholders are listed in it under `assumptions`.")
    M.append("")
    return M


def area_schedule_markdown(L: dict) -> list[str]:
    """The memo's area schedule: a row a floor, the homes and the areas by use, the totals and the efficiency."""
    s = L.get("area_schedule")
    if not s:
        return []
    keys = [g["key"] for g in s["groups"]]
    short = {"homes": "Homes", "circulation": "Circulation", "core": "Cores", "program": "Program", "amenity": "Amenity", "services": "Services", "non_residential": "Non-res.", "spare": "Spare"}
    used = [k for k in keys if s["totals"]["m2"][k]]
    M = ["### Area schedule", "", "| Floor | Homes | " + " | ".join(short[k] + " m²" for k in used) + " | Gross m² | Efficiency |",
         "|---|---:|" + "---:|" * len(used) + "---:|---:|"]
    for r in s["floors"] + [{"name": "**Total**", "homes_total": s["totals"]["homes_total"], "m2": s["totals"]["m2"], "gross_m2": s["totals"]["gross_m2"], "efficiency": s["totals"]["efficiency"]}]:
        M.append(f"| {r['name']} | {r['homes_total']} | " + " | ".join(f"{r['m2'][k]:,.0f}" for k in used) + f" | {r['gross_m2']:,.0f} | "
                 + (f"{r['efficiency'] * 100:.0f}%" if r["efficiency"] is not None else "") + " |")
    M.append("")
    M.append(s["note"] + (" **Flagged.**" if s["flag"] else "") + " The same table is `area-schedule.csv` beside this memo.")
    M.append("")
    return M
