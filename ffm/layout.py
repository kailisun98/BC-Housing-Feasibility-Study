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
from pathlib import Path
from typing import Any

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
}

UNIT_KEYS = ("three_bed_plus", "two_bed", "one_bed", "studio")   # the order they are placed, bottom up
UNIT_LABEL = {"studio": "Studio", "one_bed": "One-bedroom", "two_bed": "Two-bedroom", "three_bed_plus": "Three-bedroom+"}

# The default adjacency rules, in plain words. Each names a block and what the solver does with it; the check
# reads the placed zones back and says whether the rule held.
ADJACENCIES = [
    {"id": "non_residential_street", "block": "non_residential", "rule": "on the ground floor, facing the street"},
    {"id": "amenity_entry", "block": "amenity", "rule": "on the ground floor, next to the entry"},
    {"id": "services_lane", "block": "services", "rule": "on the ground floor, away from the street"},
    {"id": "core_centre", "block": "core", "rule": "at the centre of every floor, the corridor through it"},
    {"id": "units_both_sides", "block": "units", "rule": "on both sides of the corridor, above whatever the ground floor gives to other uses"},
    {"id": "family_low", "block": "three_bed_plus", "rule": "on the lowest residential floors"},
    {"id": "accessible_core", "block": "accessible", "rule": "next to the core, on the lowest residential floor"},
]

# Drawing tones: the unit sizes in steps of the envelope blue, the common spaces in the paper greys, amenity and
# non-residential in the amber of a note; ink and muted as the massing drawing.
TONES = {
    "paper": "#ffffff", "ink": "#1f2933", "muted": "#5f6672", "rule": "#e1e5ea", "lot": "#f4f4f2",
    "studio": "#dbe9f8", "one_bed": "#b9d4f0", "two_bed": "#8fb8e3", "three_bed_plus": "#6b9fd4",
    "corridor": "#f4f4f2", "core": "#c9c9c5", "services": "#e2e2df", "amenity": "#f6e7c1", "non_residential": "#f0cf9a",
    "spare": "#ffffff", "envelope": "#c81e1e", "outright": "#8e8e8e", "benchmark": "#c77d14", "tree": "#9fb07f", "tree_line": "#7f9664",
    "accessible": "#245f9c",
}
BLOCK_LABEL = {"corridor": "Corridor", "core": "Core (stairs, elevator)", "services": "Services, bicycles", "amenity": "Amenity", "non_residential": "Non-residential", "spare": "Spare", **UNIT_LABEL}


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
        out.append({"key": k, "label": UNIT_LABEL[k], "count": n, "net_m2_each": net, "gross_m2_each": gross, "area_m2": round(gross * n, 1),
                    "source": (areas_rule or {}).get("rule_id") or "placeholder", "note": f"{n} × {net} m² net ({mins[k]} m² minimum + {int((allowance - 1) * 100)}%), {gross} m² gross with partitions"})
    nonres = float(option.get("non_residential_gfa_m2") or 0)
    if nonres:
        out.append({"key": "non_residential", "label": "Non-residential", "count": 1, "area_m2": round(nonres, 1), "source": "option.non_residential_gfa_m2", "note": "the option's non-residential floor area (childcare, a hall, shops)"})
    amen_per, _ = LAYOUT_ASSUMPTIONS["amenity_m2_per_unit"]
    amenity = round(max(40.0, amen_per * n_total), 1) if n_total else 0.0
    if amenity:
        out.append({"key": "amenity", "label": "Amenity", "count": 1, "area_m2": amenity, "source": "placeholder", "note": f"{amen_per} m² per unit, at least 40 m²"})
    serv_base, _ = LAYOUT_ASSUMPTIONS["services_base_m2"]
    bike_each, _ = LAYOUT_ASSUMPTIONS["bicycle_m2_per_space"]
    bikes = int(option.get("bicycle_spaces") or 0)
    services = round(serv_base + bikes * bike_each, 1)
    out.append({"key": "services", "label": "Services, bicycles", "count": 1, "area_m2": services, "source": "placeholder", "note": f"{serv_base:.0f} m² services + {bikes} bicycle spaces × {bike_each} m²"})
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


def _plate(massing: dict) -> tuple[dict, float, float, float, float, int, float]:
    pm = next((x for x in massing["masses"] if x["name"] == "proposed"), None)
    if pm is None:
        raise ValueError("The massing has no proposed mass to lay out.")
    ring = pm["footprint"]
    return pm, float(ring[0][0]), float(ring[0][1]), float(pm["plate_width_m"]), float(pm["plate_depth_m"]), int(pm["storeys"]), float(pm["floor_to_floor_m"])


def solve(site: dict, option: dict, ledger: dict, massing: dict) -> dict[str, Any]:
    """Place the blocks on the proposed mass's plates, floor by floor, and say what held and what did not. Where
    the option carries a placement of its own (`layout.zones`, written by the block editor), that placement is
    re-checked instead, so a run reproduces what a person drew."""
    zones = (option.get("layout") or {}).get("zones")
    if zones:
        return place_zones(site, option, ledger, massing, zones)
    prog = blocks(option, ledger)
    pm, x0, y0, W, D, storeys, f2f = _plate(massing)
    corr, _ = LAYOUT_ASSUMPTIONS["corridor_width_m"]
    core_w, _ = LAYOUT_ASSUMPTIONS["core_bay_m"]
    warnings: list[str] = []
    if D < corr + 2 * 4.0:
        warnings.append(f"The plate is {D:.1f} m deep: too shallow for a double-loaded corridor (about 12 m); the units are drawn single-loaded on the street side and the depth is the limit.")
    strip = max(0.0, (D - corr) / 2) if D >= corr + 8.0 else max(0.0, D - corr)
    double = D >= corr + 8.0
    cx = x0 + (W - core_w) / 2            # the core bay
    seg_len = max(0.0, (W - core_w) / 2)  # a run of units on one side of the core
    corr_y = y0 + strip if double else y0 + strip   # the corridor behind the front strip

    floors: list[dict] = []
    for lv in range(storeys):
        zones = [
            {"block": "core", "label": BLOCK_LABEL["core"], "x": round(cx, 2), "y": round(y0, 2), "w": core_w, "d": round(D, 2), "area_m2": round(core_w * D, 1)},
            {"block": "corridor", "label": "Corridor", "x": round(x0, 2), "y": round(corr_y, 2), "w": round(W, 2), "d": corr, "area_m2": round(W * corr, 1), "through": "core"},
        ]
        # the four runs a floor offers: front-left, front-right (facing the street), rear-left, rear-right (the lane)
        runs = [{"side": "front", "end": "left", "x_edge": cx, "dir": -1, "y": y0, "left": seg_len},
                {"side": "front", "end": "right", "x_edge": cx + core_w, "dir": 1, "y": y0, "left": seg_len}]
        if double:
            runs += [{"side": "rear", "end": "left", "x_edge": cx, "dir": -1, "y": corr_y + corr, "left": seg_len},
                     {"side": "rear", "end": "right", "x_edge": cx + core_w, "dir": 1, "y": corr_y + corr, "left": seg_len}]
        floors.append({"level": lv, "name": "Ground floor" if lv == 0 else f"Level {lv + 1}", "z": round(lv * f2f, 2), "zones": zones, "runs": runs, "spare_m2": 0.0})

    def place(floor: dict, block: str, label: str, area: float, prefer: list[tuple[str, str]], extra: dict | None = None) -> float:
        """Put `area` of a block into the floor's runs, preferring the named (side, end) runs; returns what did not fit."""
        left = area
        order = [r for p in prefer for r in floor["runs"] if (r["side"], r["end"]) == p] + [r for r in floor["runs"] if (r["side"], r["end"]) not in prefer]
        for r in order:
            if left <= 0.05:
                break
            if r["left"] <= 0.05:
                continue
            width = min(r["left"], left / strip) if strip else 0
            if width <= 0.05:
                continue
            x = r["x_edge"] + (r["dir"] * (seg_len - r["left"])) + (0 if r["dir"] > 0 else -width)
            z = {"block": block, "label": label, "x": round(x, 2), "y": round(r["y"], 2), "w": round(width, 2), "d": round(strip, 2), "area_m2": round(width * strip, 1), "side": r["side"]}
            if extra:
                z.update(extra)
            floor["zones"].append(z)
            r["left"] -= width
            left -= width * strip
        return max(0.0, left)

    shortfall: list[dict] = []
    by_key = {b["key"]: b for b in prog["blocks"]}
    ground = floors[0]
    # the ground floor's other uses first, by their rules
    for key, prefer in (("non_residential", [("front", "left"), ("front", "right")]), ("amenity", [("front", "right"), ("front", "left")]), ("services", [("rear", "left"), ("rear", "right")])):
        b = by_key.get(key)
        if not b:
            continue
        rest = b["area_m2"]
        for fl in floors:   # a ground floor that is full spills upward, and the check will say so
            rest = place(fl, key, b["label"], rest, prefer)
            if rest <= 0.05:
                break
        if rest > 0.05:
            shortfall.append({"block": key, "label": b["label"], "area_m2": round(rest, 1)})

    # units: each one whole, in the first run with room for it, family units lowest and studios highest; the
    # accessible ones are the first placed, so they sit nearest the core on the lowest residential floor
    def place_unit(key: str, width: float, flagged: bool) -> bool:
        for fl in floors:
            runs = sorted(fl["runs"], key=lambda r: (r["side"] != "front", r["end"] != "left"))
            for r in runs:
                if r["left"] + 1e-9 < width:
                    continue
                x = r["x_edge"] + (r["dir"] * (seg_len - r["left"])) + (0 if r["dir"] > 0 else -width)
                fl["zones"].append({"block": key, "label": UNIT_LABEL[key], "x": round(x, 2), "y": round(r["y"], 2), "w": round(width, 2), "d": round(strip, 2),
                                    "area_m2": round(width * strip, 1), "side": r["side"], "unit": key, "accessible": flagged})
                r["left"] -= width
                return True
        return False

    accessible_left = int(option.get("accessible_units") or 0)
    for key in UNIT_KEYS:
        b = by_key.get(key)
        if not b or not strip:
            continue
        width = b["gross_m2_each"] / strip
        for _ in range(b["count"]):
            flagged = accessible_left > 0
            if place_unit(key, width, flagged):
                if flagged:
                    accessible_left -= 1
                continue
            sf = next((s for s in shortfall if s["block"] == key), None)
            if sf:
                sf["units"] += 1
                sf["area_m2"] = round(sf["area_m2"] + b["gross_m2_each"], 1)
            else:
                shortfall.append({"block": key, "label": UNIT_LABEL[key], "units": 1, "area_m2": b["gross_m2_each"]})

    # what is left on each floor is spare, drawn white
    for fl in floors:
        spare = 0.0
        for r in fl["runs"]:
            if r["left"] > 0.3:
                x = r["x_edge"] + (r["dir"] * (seg_len - r["left"])) + (0 if r["dir"] > 0 else -r["left"])
                fl["zones"].append({"block": "spare", "label": "Spare", "x": round(x, 2), "y": round(r["y"], 2), "w": round(r["left"], 2), "d": round(strip, 2), "area_m2": round(r["left"] * strip, 1), "side": r["side"]})
                spare += r["left"] * strip
        fl["spare_m2"] = round(spare, 1)
        del fl["runs"]

    plate = {"x": round(x0, 2), "y": round(y0, 2), "width_m": round(W, 2), "depth_m": round(D, 2), "storeys": storeys, "floor_to_floor_m": f2f, "double_loaded": double, "unit_depth_m": round(strip, 2)}
    return _assemble(site, option, ledger, massing, prog, plate, floors, shortfall, warnings, edited=False, geometry=[])


def _assemble(site, option, ledger, massing, prog, plate, floors, shortfall, warnings, edited, geometry) -> dict[str, Any]:
    """The layout record both paths return: the rules read back from the zones, the totals, the log."""
    checks = [_check(rule, floors, prog, shortfall) for rule in adjacencies_for(option)]
    placed_units = sum(1 for fl in floors for z in fl["zones"] if z.get("unit"))
    gross_plates = round(plate["width_m"] * plate["depth_m"] * plate["storeys"], 1)
    fsr_rule = _find(ledger["results"], check="district_outright_fsr")
    h_rule = _find(ledger["results"], check="district_outright_height")
    outright = {"fsr": (fsr_rule or {}).get("values", {}).get("max_fsr_outright"), "height_m": (h_rule or {}).get("values", {}).get("max_height_m_outright"),
                "rule_ids": [r["rule_id"] for r in (fsr_rule, h_rule) if r]}
    used = round(sum(z["area_m2"] for fl in floors for z in fl["zones"] if z["block"] != "spare"), 1)
    return {
        "site_id": site.get("id"), "option_id": option.get("id"), "as_of": ledger["run"]["as_of"], "stamp": ledger["run"]["stamp"]["stamp"],
        "units": "m", "origin": massing.get("origin"), "edited": edited,
        "plate": plate,
        "program": prog["blocks"], "parking": prog["parking"], "units_total": prog["units_total"], "units_placed": placed_units,
        "adjacencies": checks, "geometry": geometry, "floors": floors, "shortfall": shortfall, "outright": outright,
        "totals": {"plates_m2": gross_plates, "used_m2": used, "spare_m2": round(gross_plates - used, 1), "gfa_m2": massing["masses"][0].get("gfa_m2")},
        "assumptions": prog["assumptions"], "warnings": warnings + list(massing.get("warnings") or []),
        "derived_from": (["option.layout.zones (placed by hand)"] if edited else []) + ["option.units", "option.non_residential_gfa_m2", "option.accessible_units", "option.bicycle_spaces", "massing.masses[proposed]", "bch.design_guidelines.unit_areas"],
    }


# ---------------------------------------------------------------- a placement drawn by hand, re-checked

EDITABLE_BLOCKS = ("studio", "one_bed", "two_bed", "three_bed_plus", "non_residential", "amenity", "services", "core", "corridor")


def place_zones(site: dict, option: dict, ledger: dict, massing: dict, zones_by_level: dict | list) -> dict[str, Any]:
    """The block editor's placement: `zones_by_level` maps a level ("0", "1", …) to zones {block, x, y, w, d,
    accessible?}. The engine does not move anything: it measures every zone, reads the rules back, and lists
    what broke (a zone outside the plate, two zones overlapping, a unit smaller than its area, a floor without
    a corridor), and what the program still lacks. Same record as solve(), with `edited: true`."""
    prog = blocks(option, ledger)
    pm, x0, y0, W, D, storeys, f2f = _plate(massing)
    corr, _ = LAYOUT_ASSUMPTIONS["corridor_width_m"]
    double = D >= corr + 8.0
    strip = max(0.0, (D - corr) / 2) if double else max(0.0, D - corr)
    by_key = {b["key"]: b for b in prog["blocks"]}
    geometry: list[dict] = []
    warnings: list[str] = []
    levels = {int(k): v for k, v in (zones_by_level.items() if isinstance(zones_by_level, dict) else enumerate(zones_by_level))}
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
            zone = {"block": block, "label": BLOCK_LABEL.get(block, block), "x": x, "y": y, "w": w, "d": d, "area_m2": round(w * d, 1), "side": side}
            if block in UNIT_KEYS:
                zone["unit"] = block
                zone["accessible"] = bool(z.get("accessible"))
            if block == "corridor":
                zone["through"] = "core"
            zones.append(zone)
            # inside the plate?
            if x < x0 - 0.05 or y < y0 - 0.05 or x + w > x0 + W + 0.05 or y + d > y0 + D + 0.05:
                geometry.append({"kind": "outside", "level": lv, "block": block, "note": f"{zone['label']} at {x:.1f}, {y:.1f} m runs past the plate ({W:.1f} × {D:.1f} m) on {'the ground floor' if lv == 0 else f'level {lv + 1}'}"})
            if block in UNIT_KEYS and block in by_key and w * d + 0.5 < by_key[block]["gross_m2_each"]:
                geometry.append({"kind": "undersized", "level": lv, "block": block, "note": f"a {zone['label'].lower()} on {'the ground floor' if lv == 0 else f'level {lv + 1}'} is {w * d:.0f} m², under its {by_key[block]['gross_m2_each']:.0f} m² gross"})
        # overlaps: units and uses may not share floor area; the corridor and the core are the circulation and may cross each other only
        for i, a in enumerate(zones):
            for b in zones[i + 1:]:
                if {a["block"], b["block"]} == {"corridor", "core"}:
                    continue
                if not (a["x"] + a["w"] <= b["x"] + 0.01 or b["x"] + b["w"] <= a["x"] + 0.01 or a["y"] + a["d"] <= b["y"] + 0.01 or b["y"] + b["d"] <= a["y"] + 0.01):
                    geometry.append({"kind": "overlap", "level": lv, "block": a["block"], "note": f"{a['label']} and {b['label']} overlap on {'the ground floor' if lv == 0 else f'level {lv + 1}'}"})
        if zones and not any(z["block"] == "corridor" for z in zones) and any(z.get("unit") for z in zones):
            geometry.append({"kind": "no_corridor", "level": lv, "note": f"{'the ground floor' if lv == 0 else f'level {lv + 1}'} has units but no corridor"})
        if zones and not any(z["block"] == "core" for z in zones):
            geometry.append({"kind": "no_core", "level": lv, "note": f"{'the ground floor' if lv == 0 else f'level {lv + 1}'} has no core: the stairs and the elevator must land on every floor"})
        used = sum(z["area_m2"] for z in zones if z["block"] != "spare")
        floors.append({"level": lv, "name": "Ground floor" if lv == 0 else f"Level {lv + 1}", "z": round(lv * f2f, 2), "zones": zones, "spare_m2": round(max(0.0, W * D - used), 1)})

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
            placed = sum(z["area_m2"] for fl in floors for z in fl["zones"] if z["block"] == b["key"])
            if placed + 1.0 < b["area_m2"]:
                shortfall.append({"block": b["key"], "label": b["label"], "area_m2": round(b["area_m2"] - placed, 1)})
    plate = {"x": round(x0, 2), "y": round(y0, 2), "width_m": round(W, 2), "depth_m": round(D, 2), "storeys": storeys, "floor_to_floor_m": f2f, "double_loaded": double, "unit_depth_m": round(strip, 2)}
    return _assemble(site, option, ledger, massing, prog, plate, floors, shortfall, warnings, edited=True, geometry=geometry)


def zones_of(L: dict) -> dict[str, list[dict]]:
    """A layout's placement in the form the option keeps (`layout.zones`): the editor starts from the solver's."""
    out: dict[str, list[dict]] = {}
    for fl in L["floors"]:
        out[str(fl["level"])] = [{k: z[k] for k in ("block", "x", "y", "w", "d")} | ({"accessible": True} if z.get("accessible") else {})
                                 for z in fl["zones"] if z["block"] != "spare"]
    return out


def _check(rule: dict, floors: list[dict], prog: dict, shortfall: list[dict]) -> dict:
    """One adjacency rule read back from the placed zones: pass, conditional (held in part) or info (not in play)."""
    key = rule["block"]
    zones = [(fl, z) for fl in floors for z in fl["zones"]]
    out = {**rule, "status": "info", "note": ""}
    if key == "non_residential":
        zs = [(fl, z) for fl, z in zones if z["block"] == key]
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
        out.update(status="pass" if ok else "conditional", note="on the ground floor, lane side" if ok else ("on the ground floor but facing the street: the plate is single-loaded" if zs and all(fl["level"] == 0 for fl, _ in zs) else "services could not all stay on the ground floor"))
    elif key == "core":
        out.update(status="pass", note="one core bay at the centre of every floor, the corridor through it")
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
        ok = not small or max(fam) <= min(small) + 1
        out.update(status="pass" if ok else "conditional", note=f"three-bedroom units on levels {min(fam) + 1} to {max(fam) + 1}" + ("" if ok else ", above some smaller units"))
    elif key == "accessible":
        acc = [(fl, z) for fl, z in zones if z.get("accessible")]
        if not acc:
            out["note"] = "no accessible units stated on the option"
            return out
        lv = min(fl["level"] for fl, _ in acc)
        out.update(status="pass", note=f"{len(acc)} accessible units on {'the ground floor' if lv == 0 else f'level {lv + 1}'}, nearest the core")
    return out


# ---------------------------------------------------------------- the drawings

def _esc(s: Any) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _svg_open(w: float, h: float, title: str) -> list[str]:
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" font-family="IBM Plex Sans, Helvetica, Arial, sans-serif" font-size="12" fill="{TONES["ink"]}" role="img" aria-label="{_esc(title)}">',
            f'<rect width="100%" height="100%" fill="{TONES["paper"]}"/>']


def _legend(x: float, y: float, keys: list[str]) -> list[str]:
    out = []
    cx = x
    for k in keys:
        out.append(f'<rect x="{cx:.1f}" y="{y - 9:.1f}" width="12" height="12" fill="{TONES[k]}" stroke="{TONES["muted"]}" stroke-width="0.8"/>')
        out.append(f'<text x="{cx + 16:.1f}" y="{y + 1:.1f}" fill="{TONES["muted"]}" font-size="11">{_esc(BLOCK_LABEL.get(k, k))}</text>')
        cx += 16 + 7 * len(BLOCK_LABEL.get(k, k)) + 18
    return out


def _foot(lines: list[str], x: float, y: float) -> list[str]:
    return [f'<text x="{x:.1f}" y="{y + i * 16:.1f}" fill="{TONES["ink"]}">{_esc(ln)}</text>' for i, ln in enumerate(lines)]


def _stamp_line(L: dict) -> str:
    return f'Rules as of {L["as_of"]} · stamp {L["stamp"]} · derived by ffm from the option and the massing, not a design'


def svg_stacking(L: dict) -> str:
    """The stacking diagram: one bar per floor, top floor first, its length the plate and its segments the blocks
    in proportion to the area they take on that floor."""
    floors = L["floors"]
    pad, bar_h, gap = 48, 26, 8
    bar_w = 520
    n = len(floors)
    lines = [f'{L["units_placed"]} of {L["units_total"]} units placed on {n} floors of {L["plate"]["width_m"]} × {L["plate"]["depth_m"]} m ({L["plate"]["width_m"] * L["plate"]["depth_m"]:,.0f} m² each)',
             *(f'Did not fit: {s["label"]}{" × " + str(s["units"]) if s.get("units") else ""}, {s["area_m2"]:,.0f} m²' for s in L["shortfall"]),
             _stamp_line(L)]
    height = pad + 24 + n * (bar_h + gap) + 40 + 16 * len(lines) + 16
    out = _svg_open(pad + 80 + bar_w + pad, height, "Stacking diagram")
    out.append(f'<text x="{pad}" y="{pad - 4}" font-size="14" font-weight="600">Stacking · top floor first, each bar one plate</text>')
    keys = ["non_residential", "amenity", "services", "core", "corridor", "three_bed_plus", "two_bed", "one_bed", "studio", "spare"]
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
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bar_h}" fill="{TONES[k]}" stroke="{TONES["paper"]}" stroke-width="1"/>')
            if w > 34:
                cnt = sum(1 for z in fl["zones"] if z["block"] == k and z.get("unit"))
                out.append(f'<text x="{x + 4:.1f}" y="{y + bar_h / 2 + 4}" font-size="10" fill="{TONES["ink"]}">{_esc(BLOCK_LABEL.get(k, k))}{f" × {cnt}" if cnt else ""}</text>')
            x += w
    out += _legend(pad + 80, pad + 24 + n * (bar_h + gap) + 18, keys)
    out += _foot(lines, pad, pad + 24 + n * (bar_h + gap) + 48)
    out.append("</svg>")
    return "\n".join(out)


def _plan(out: list[str], L: dict, fl: dict, ox: float, oy: float, scale: float, title: str) -> None:
    p = L["plate"]
    out.append(f'<text x="{ox:.1f}" y="{oy - 8:.1f}" font-size="13" font-weight="600">{_esc(title)}</text>')
    out.append(f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{p["width_m"] * scale:.1f}" height="{p["depth_m"] * scale:.1f}" fill="{TONES["lot"]}" stroke="{TONES["ink"]}" stroke-width="1.2"/>')
    for z in fl["zones"]:
        x = ox + (z["x"] - p["x"]) * scale
        y = oy + (z["y"] - p["y"]) * scale
        w, d = z["w"] * scale, z["d"] * scale
        dash = ' stroke-dasharray="3 2"' if z["block"] == "spare" else ""
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{d:.1f}" fill="{TONES[z["block"]]}" stroke="{TONES["muted"]}" stroke-width="0.8"{dash}/>')
        if z.get("accessible"):
            out.append(f'<circle cx="{x + 7:.1f}" cy="{y + 7:.1f}" r="3.2" fill="{TONES["accessible"]}"/>')
        if w > 26 and d > 14:
            lab = {"three_bed_plus": "3b", "two_bed": "2b", "one_bed": "1b", "studio": "st", "corridor": "corridor", "core": "core", "services": "services", "amenity": "amenity", "non_residential": "non-res", "spare": "spare"}[z["block"]]
            out.append(f'<text x="{x + w / 2:.1f}" y="{y + d / 2 + 3.5:.1f}" font-size="9.5" text-anchor="middle" fill="{TONES["ink"]}">{lab}</text>')
    # dimension strings
    out.append(f'<line x1="{ox:.1f}" y1="{oy + p["depth_m"] * scale + 14:.1f}" x2="{ox + p["width_m"] * scale:.1f}" y2="{oy + p["depth_m"] * scale + 14:.1f}" stroke="{TONES["muted"]}" stroke-width="0.8"/>')
    out.append(f'<text x="{ox + p["width_m"] * scale / 2:.1f}" y="{oy + p["depth_m"] * scale + 26:.1f}" font-size="10" text-anchor="middle" fill="{TONES["muted"]}">{p["width_m"]} m · street side</text>')
    out.append(f'<line x1="{ox - 12:.1f}" y1="{oy:.1f}" x2="{ox - 12:.1f}" y2="{oy + p["depth_m"] * scale:.1f}" stroke="{TONES["muted"]}" stroke-width="0.8"/>')
    out.append(f'<text x="{ox - 16:.1f}" y="{oy + p["depth_m"] * scale / 2:.1f}" font-size="10" text-anchor="middle" fill="{TONES["muted"]}" transform="rotate(-90 {ox - 16:.1f} {oy + p["depth_m"] * scale / 2:.1f})">{p["depth_m"]} m</text>')


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


def svg_plans(L: dict) -> str:
    """Floor plans by program: the ground floor, a typical residential floor, the top floor where it differs."""
    p = L["plate"]
    levels = _typical_levels(L)
    pad = 48
    # one plan per row, each as wide as the sheet allows, so the drawing stays legible in a 400 px column
    scale = max(3.0, min(560 / p["width_m"], 200 / p["depth_m"]))
    pw, pd = p["width_m"] * scale, p["depth_m"] * scale
    row = pd + 64
    width = pad + 30 + pw + pad
    lines = [f'Unit depth {p["unit_depth_m"]} m either side of a {LAYOUT_ASSUMPTIONS["corridor_width_m"][0]} m corridor; core bay {LAYOUT_ASSUMPTIONS["core_bay_m"][0]} m;',
             f'partitions +{int((LAYOUT_ASSUMPTIONS["partition_allowance"][0] - 1) * 100)}% over net areas (declared placeholders). The rules read back from the plates are listed with the figure.',
             _stamp_line(L)]
    height = pad + 24 + len(levels) * row + 20 + 30 + 16 * len(lines) + 16
    out = _svg_open(max(width, 640), height, "Floor plans by program")
    out.append(f'<text x="{pad}" y="{pad - 4}" font-size="14" font-weight="600">Plans by program · metres, street at the top</text>')
    for i, lv in enumerate(levels):
        fl = L["floors"][lv]
        counts = {}
        for z in fl["zones"]:
            if z.get("unit"):
                counts[z["unit"]] = counts.get(z["unit"], 0) + 1
        title = fl["name"] + (": " + ", ".join(f'{n} {UNIT_LABEL[k].lower()}' for k, n in counts.items()) if counts else "") + (f' · {fl["spare_m2"]:,.0f} m² spare' if fl["spare_m2"] > 5 else "")
        _plan(out, L, fl, pad + 30, pad + 24 + i * row + 14, scale, title if len(title) < 80 else fl["name"])
    ly = pad + 24 + len(levels) * row + 14
    out += _legend(pad, ly, ["non_residential", "amenity", "services", "core", "corridor", "three_bed_plus", "two_bed", "one_bed", "studio", "spare"])
    out.append(f'<circle cx="{pad + 6}" cy="{ly + 18:.1f}" r="3.2" fill="{TONES["accessible"]}"/><text x="{pad + 16}" y="{ly + 22:.1f}" font-size="11" fill="{TONES["muted"]}">accessible unit</text>')
    out += _foot(lines, pad, ly + 46)
    out.append("</svg>")
    return "\n".join(out)


def svg_elevations(L: dict, massing: dict) -> str:
    """Front and side elevations: storeys × floor to floor, a window per unit as the rhythm, the ground floor's
    glazing where the non-residential space is, the outright height and the staff benchmark as lines."""
    p = L["plate"]
    f2f, n = p["floor_to_floor_m"], p["storeys"]
    H = f2f * n
    masses = {m["name"]: m for m in massing["masses"]}
    bench = massing.get("policy_benchmark") or {}
    out_h = (L.get("outright") or {}).get("height_m") or (masses.get("outright") or {}).get("height_m")
    hmax = max([H, out_h or 0] + ([bench["height_m"][1]] if bench.get("height_m") else []))
    pad = 48
    scale = max(3.0, min(380 / p["width_m"], 220 / hmax, 260 / p["depth_m"]))
    fw, sw, eh = p["width_m"] * scale, p["depth_m"] * scale, hmax * scale
    gap = 70
    width = pad + fw + gap + sw + pad
    lines = [f'{n} storeys × {f2f} m = {H:.1f} m to the top floor level' + (f'; the option states {masses["proposed"]["height_m"]} m' if masses.get("proposed", {}).get("height_m", H) > H + 0.05 else ""),
             (f'Outright maximum height {out_h} m, dashed grey' if out_h else "No outright height in the stack for this district"),
             *( [f'Staff benchmark {bench["height_m"][0]} to {bench["height_m"][1]} m, amber'] if bench.get("height_m") else []),
             f'Windows: one per unit on its side, {LAYOUT_ASSUMPTIONS["window_width_m"][0]} m wide, the unit module as the rhythm; a placeholder for the elevation study',
             _stamp_line(L)]
    height = pad + 24 + eh + 30 + 16 * len(lines) + 16
    out = _svg_open(max(width, 720), height, "Preliminary elevations")
    out.append(f'<text x="{pad}" y="{pad - 4}" font-size="14" font-weight="600">Elevations · metres</text>')
    base = pad + 24 + eh
    win_w, _ = LAYOUT_ASSUMPTIONS["window_width_m"]

    def elevation(ox: float, length: float, label: str, axis: str) -> None:
        out.append(f'<text x="{ox:.1f}" y="{pad + 14:.1f}" font-size="12" font-weight="600">{_esc(label)}</text>')
        out.append(f'<line x1="{ox - 10:.1f}" y1="{base:.1f}" x2="{ox + length + 10:.1f}" y2="{base:.1f}" stroke="{TONES["ink"]}" stroke-width="1.5"/>')
        out.append(f'<rect x="{ox:.1f}" y="{base - H * scale:.1f}" width="{length:.1f}" height="{H * scale:.1f}" fill="{TONES["lot"]}" stroke="{TONES["ink"]}" stroke-width="1.2"/>')
        for fl in L["floors"]:
            y_top = base - (fl["z"] + f2f) * scale
            y_floor = base - fl["z"] * scale
            if fl["level"]:
                out.append(f'<line x1="{ox:.1f}" y1="{y_floor:.1f}" x2="{ox + length:.1f}" y2="{y_floor:.1f}" stroke="{TONES["muted"]}" stroke-width="0.6"/>')
            # windows: the zones on the face this elevation looks at
            face = [z for z in fl["zones"] if (axis == "x" and z.get("side") == "front") or (axis == "y" and z["block"] not in ("corridor",) and z.get("side") in ("front", "rear"))]
            if axis == "x":
                for z in face:
                    cx = ox + (z["x"] - p["x"] + z["w"] / 2) * scale
                    if z["block"] in ("non_residential", "amenity"):
                        out.append(f'<rect x="{ox + (z["x"] - p["x"]) * scale + 2:.1f}" y="{y_top + 0.5 * scale:.1f}" width="{max(2, z["w"] * scale - 4):.1f}" height="{(f2f - 0.9) * scale:.1f}" fill="{TONES["studio"]}" stroke="{TONES["muted"]}" stroke-width="0.6"/>')
                    elif z.get("unit"):
                        out.append(f'<rect x="{cx - win_w * scale / 2:.1f}" y="{y_top + 0.9 * scale:.1f}" width="{win_w * scale:.1f}" height="{(f2f - 1.8) * scale:.1f}" fill="{TONES["two_bed"]}" stroke="{TONES["muted"]}" stroke-width="0.6"/>')
            else:
                # the side elevation sees the end unit of each strip: one window per strip, placed at its depth
                for side, yy in (("front", p["y"]), ("rear", p["y"] + p["depth_m"] - p["unit_depth_m"])):
                    if any(z.get("unit") and z.get("side") == side for z in fl["zones"]):
                        cx = ox + (yy - p["y"] + p["unit_depth_m"] / 2) * scale
                        out.append(f'<rect x="{cx - win_w * scale / 2:.1f}" y="{y_top + 0.9 * scale:.1f}" width="{win_w * scale:.1f}" height="{(f2f - 1.8) * scale:.1f}" fill="{TONES["two_bed"]}" stroke="{TONES["muted"]}" stroke-width="0.6"/>')
        if out_h:
            yo = base - out_h * scale
            out.append(f'<line x1="{ox - 10:.1f}" y1="{yo:.1f}" x2="{ox + length + 10:.1f}" y2="{yo:.1f}" stroke="{TONES["outright"]}" stroke-width="1" stroke-dasharray="5 3"/>')
            out.append(f'<text x="{ox + length + 12:.1f}" y="{yo + 4:.1f}" font-size="10" fill="{TONES["outright"]}">outright {out_h} m</text>')
        if bench.get("height_m"):
            for hv in bench["height_m"]:
                yb = base - hv * scale
                out.append(f'<line x1="{ox - 10:.1f}" y1="{yb:.1f}" x2="{ox + length + 10:.1f}" y2="{yb:.1f}" stroke="{TONES["benchmark"]}" stroke-width="1" stroke-dasharray="4 3"/>')
            out.append(f'<text x="{ox + length + 12:.1f}" y="{base - bench["height_m"][1] * scale + 4:.1f}" font-size="10" fill="{TONES["benchmark"]}">benchmark {bench["height_m"][0]}–{bench["height_m"][1]} m</text>')
        out.append(f'<text x="{ox + length + 12:.1f}" y="{base - H * scale + 4:.1f}" font-size="10" fill="{TONES["ink"]}">{H:.1f} m</text>')

    elevation(pad, fw, "Front elevation · from the street", "x")
    elevation(pad + fw + gap + 40, sw, "Side elevation · street at the left", "y")
    out += _foot(lines, pad, base + 30)
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
    scale = max(3.0, min(360 / (p["width_m"] + p["depth_m"] * cos), 260 / (p["storeys"] * p["floor_to_floor_m"] + p["depth_m"] * sin)))
    pad = 48
    width = pad + (p["width_m"] + p["depth_m"] * cos) * scale + pad
    height = pad + 24 + (p["storeys"] * p["floor_to_floor_m"] + p["depth_m"] * sin) * scale + 40 + 16 * 2 + 16
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
    out += _foot([f'{p["storeys"]} floors of {p["width_m"]} × {p["depth_m"]} m, lifted one storey apart to show the program', _stamp_line(L)], pad, base + 28)
    out.append("</svg>")
    return "\n".join(out)


def svg_site_plan(L: dict, site: dict, massing: dict, ledger: dict) -> str:
    """The code site plan: the lot, the yards with their dimensions, the setback envelope, the footprint, the
    retained trees' protection barriers where the site records positions, and the table a plan checker reads:
    FSR, coverage, height and yards against the schedule where the stack has one."""
    lot, env = massing["lot"], massing["envelope"]
    W, D = lot["frontage_m"], lot["depth_m"]
    sb = env["setbacks_m"]
    pm = next(m for m in massing["masses"] if m["name"] == "proposed")
    results = ledger["results"]
    pad = 48
    scale = max(3.0, min(380 / W, 300 / D))
    pw, pd = W * scale, D * scale
    foot = pm["plate_width_m"] * pm["plate_depth_m"]
    rows = [("Site area", f'{lot["area_m2"]:,.1f} m²', "", "")]
    fsr = _find(results, check="district_outright_fsr")
    rows.append(("Floor space ratio", f'{pm["fsr"]:.2f} ({pm["gfa_m2"]:,.0f} m²)', f'{fsr["values"].get("max_fsr_outright")} outright' if fsr else "no schedule in the stack", fsr["status"] if fsr else "info"))
    hgt = _find(results, check="district_outright_height")
    rows.append(("Height", f'{pm["height_m"]} m, {pm["storeys"]} storeys', f'{hgt["values"].get("max_height_m_outright")} m outright' if hgt else "no schedule in the stack", hgt["status"] if hgt else "info"))
    cov = _find(results, rule_id=None)
    cov_rule = next((r for r in results if r["rule_id"].endswith(".site_coverage") and r["status"] != "not_applicable"), None)
    rows.append(("Site coverage", f'{foot / lot["area_m2"] * 100:.0f}% ({foot:,.0f} m²)', f'{cov_rule["values"].get("max_site_coverage", 0) * 100:.0f}% maximum' if cov_rule else "no schedule in the stack", ("pass" if foot / lot["area_m2"] <= cov_rule["values"].get("max_site_coverage", 1) else "conditional") if cov_rule else "info"))
    yards = _find(results, check="district_setbacks")
    for k in ("front", "rear", "side"):
        mn = (yards or {}).get("values", {}).get(f"min_{k}_yard_m") if yards else None
        rows.append((f"{k.capitalize()} yard", f'{sb.get(k)} m', f'{mn} m minimum' if mn is not None else ("placeholder, not from the schedule" if not yards else "not given"), ("pass" if sb.get(k, 0) + 1e-9 >= mn else "conditional") if mn is not None else "info"))
    trees = massing.get("trees") or {}
    rows.append(("Trees", f'{trees.get("after", "?")} after development', f'Schedule C requires {trees.get("required", "?")}', "pass" if trees and (trees.get("shortfall") or 0) == 0 else "conditional") if trees else ("Trees", "no survey on file", "", "uncertain"))
    ans = ledger["summary"]["answers"]["allowed"]
    rows.append(("Allowed", f'outright: {ans["outright"]["verdict"]}' + (f'; by rezoning: {ans["by_rezoning"]["verdict"]}' if ans.get("rezoning_path") else ""), ans.get("rezoning_path") or "no rezoning path stated", ""))
    table_h = 20 + 18 * len(rows)
    height = pad + 24 + pd + 50 + table_h + 40
    width = max(pad + pw + 60 + 400, 760)
    out = _svg_open(width, height, "Code site plan")
    out.append(f'<text x="{pad}" y="{pad - 4}" font-size="14" font-weight="600">Code site plan · metres, street at the top</text>')
    ox, oy = pad + 30, pad + 24
    out.append(f'<rect x="{ox}" y="{oy}" width="{pw:.1f}" height="{pd:.1f}" fill="{TONES["lot"]}" stroke="{TONES["ink"]}" stroke-width="1.5"/>')
    ex, ey = ox + sb.get("side", 0) * scale, oy + sb.get("front", 0) * scale
    out.append(f'<rect x="{ex:.1f}" y="{ey:.1f}" width="{env["width_m"] * scale:.1f}" height="{env["depth_m"] * scale:.1f}" fill="none" stroke="{TONES["envelope"]}" stroke-width="1.2" stroke-dasharray="6 4"/>')
    fx, fy = ox + pm["footprint"][0][0] * scale, oy + pm["footprint"][0][1] * scale
    out.append(f'<rect x="{fx:.1f}" y="{fy:.1f}" width="{pm["plate_width_m"] * scale:.1f}" height="{pm["plate_depth_m"] * scale:.1f}" fill="{TONES["two_bed"]}" fill-opacity="0.55" stroke="{TONES["accessible"]}" stroke-width="1.2"/>')
    out.append(f'<text x="{fx + 6:.1f}" y="{fy + 14:.1f}" font-size="10" fill="{TONES["ink"]}">{pm["plate_width_m"]} × {pm["plate_depth_m"]} m, {pm["storeys"]} storeys</text>')
    # the yards, dimensioned
    dims = [(ox + pw / 2, oy, oy + sb.get("front", 0) * scale, f'front {sb.get("front")} m', True),
            (ox + pw / 2, oy + pd - sb.get("rear", 0) * scale, oy + pd, f'rear {sb.get("rear")} m', True),
            (oy + pd / 2, ox, ox + sb.get("side", 0) * scale, f'side {sb.get("side")} m', False),
            (oy + pd / 2, ox + pw - sb.get("side", 0) * scale, ox + pw, f'side {sb.get("side")} m', False)]
    for a, b1, b2, lab, vert in dims:
        if vert:
            out.append(f'<line x1="{a:.1f}" y1="{b1:.1f}" x2="{a:.1f}" y2="{b2:.1f}" stroke="{TONES["envelope"]}" stroke-width="0.8"/>')
            out.append(f'<text x="{a + 4:.1f}" y="{(b1 + b2) / 2 + 3:.1f}" font-size="9.5" fill="{TONES["envelope"]}">{_esc(lab)}</text>')
        else:
            out.append(f'<line x1="{b1:.1f}" y1="{a:.1f}" x2="{b2:.1f}" y2="{a:.1f}" stroke="{TONES["envelope"]}" stroke-width="0.8"/>')
            out.append(f'<text x="{(b1 + b2) / 2:.1f}" y="{a - 4:.1f}" font-size="9.5" text-anchor="middle" fill="{TONES["envelope"]}">{_esc(lab)}</text>')
    # trees with a position and a barrier
    ctx_trees = ((site.get("context") or {}).get("trees") or [])
    barriers = {b.get("tree"): b.get("barrier_m") for b in (trees.get("retained_barriers") or [])}
    drawn = 0
    for t in ctx_trees:
        if t.get("x") is None or t.get("y") is None:
            continue
        r = barriers.get(t.get("id"))
        cx, cy = ox + float(t["x"]) * scale, oy + float(t["y"]) * scale
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{max(3, 1.5 * scale / 2):.1f}" fill="{TONES["tree"]}" stroke="{TONES["tree_line"]}" stroke-width="0.8"/>')
        if r:
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{float(r) * scale:.1f}" fill="none" stroke="{TONES["tree_line"]}" stroke-width="0.8" stroke-dasharray="3 2"/>')
            drawn += 1
    out.append(f'<text x="{ox}" y="{oy + pd + 16:.1f}" font-size="11" fill="{TONES["muted"]}">lot {W} × {D} m · dashed red: setback envelope {env["width_m"]} × {env["depth_m"]} m · blue: footprint' + (f' · {drawn} protection barrier{"s" if drawn != 1 else ""} (By-law 9958, Schedule A)' if drawn else (' · retained trees have no surveyed position: barriers not drawn' if barriers else "")) + '</text>')
    # the table
    tx, ty = ox + pw + 60, oy
    out.append(f'<text x="{tx}" y="{ty + 12}" font-size="12" font-weight="600">What the plan checker reads</text>')
    cols = (0, 110, 250, 330)
    for i, (k, v, lim, st) in enumerate(rows):
        y = ty + 34 + i * 18
        out.append(f'<line x1="{tx}" y1="{y + 5}" x2="{tx + 380}" y2="{y + 5}" stroke="{TONES["rule"]}" stroke-width="0.8"/>')
        out.append(f'<text x="{tx + cols[0]}" y="{y}" font-size="11" fill="{TONES["muted"]}">{_esc(k)}</text>')
        out.append(f'<text x="{tx + cols[1]}" y="{y}" font-size="11">{_esc(v)}</text>')
        out.append(f'<text x="{tx + cols[2]}" y="{y}" font-size="11" fill="{TONES["muted"]}">{_esc(lim)}</text>')
        if st:
            colour = {"pass": "#2f7d4a", "conditional": "#9a6b00", "fail": "#c81e1e", "uncertain": "#a3640c", "info": "#5f6672"}.get(st, "#5f6672")
            out.append(f'<text x="{tx + cols[3]}" y="{y}" font-size="10.5" font-weight="600" fill="{colour}">{_esc(st)}</text>')
    out += _foot([_stamp_line(L)], pad, oy + pd + 50 + table_h)
    out.append("</svg>")
    return "\n".join(out)


SHEETS = ("stacking", "plans", "elevations", "axon", "site-plan")


def sheets(L: dict, site: dict, massing: dict, ledger: dict) -> dict[str, str]:
    return {"stacking": svg_stacking(L), "plans": svg_plans(L), "elevations": svg_elevations(L, massing), "axon": svg_axon(L), "site-plan": svg_site_plan(L, site, massing, ledger)}


def write(L: dict, site: dict, massing: dict, ledger: dict, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {"layout.json": out_dir / "layout.json"}
    paths["layout.json"].write_text(json.dumps(L, indent=2, ensure_ascii=False), encoding="utf-8")
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
    M.append(f"{p['storeys']} floors of {p['width_m']} × {p['depth_m']} m ({p['width_m'] * p['depth_m']:,.0f} m² each); {'a double-loaded corridor' if p['double_loaded'] else 'a single-loaded plate, the depth is the limit'}, units {p['unit_depth_m']} m deep; {L['units_placed']} of {L['units_total']} units placed.")
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
    for name, cap in (("stacking", "Stacking diagram"), ("plans", "Plans by program"), ("elevations", "Preliminary elevations"), ("axon", "The floors stacked"), ("site-plan", "Code site plan")):
        M.append(f"![{cap}]({name}.svg)")
        M.append("")
    M.append("`layout.json` carries the blocks, the rules and every zone's coordinates; placeholders are listed in it under `assumptions`.")
    M.append("")
    return M
