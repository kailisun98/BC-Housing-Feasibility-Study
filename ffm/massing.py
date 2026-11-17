"""Rule-derived massing: turn the lot, the setbacks and the ledger's numbers into simple extrusions.

Two masses are produced so the memo can show the gap the rezoning has to close:

    outright   what the district schedule allows without rezoning (max FSR x site area, under the
               outright height), filled from the front setback back
    proposed   the option's gross floor area at its storey count, same envelope

Every mass is a rectangle. That is deliberate: this is the feasibility stage, and the point is that the
numbers in the memo and the box in Revit are the same numbers. The lot is the equivalent rectangle unless
the site carries its parcel polygon or a drawn boundary (`ffm.boundary`): then the lot is that shape, the
setback envelope is the shape inset by the setbacks, and the masses stand in the largest rectangle inside
the envelope (the plate box).

The architect can move and turn the proposed mass inside the plate box (`option.massing`, see `place`) and choose
which face of the lot is the street side (`site.front_face`, see `boundary.oriented_ring`; the transform is stored
in `lot.orientation`). Without either, the masses stand where they always have.

Coordinates: metres, origin at the front-left lot corner, x along the frontage, y into the lot
(away from the street), z up. massing.json is what the pyRevit script reads.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from . import boundary


PLATE_MIN_DEPTH_M = 12.0   # a floor plate keeps at least this depth before it gives up any width (a double-loaded corridor)
PLATE_GRID_M = 0.5         # the grid the plate box is found on inside a polygon envelope


def _rect(x0: float, y0: float, w: float, d: float) -> list[list[float]]:
    return [[round(x0, 3), round(y0, 3)], [round(x0 + w, 3), round(y0, 3)],
            [round(x0 + w, 3), round(y0 + d, 3)], [round(x0, 3), round(y0 + d, 3)]]


def _find(results: list[dict], rule_id: str) -> dict | None:
    for r in results:
        if r["rule_id"] == rule_id:
            return r
    return None


def _outright_params(results: list[dict]) -> tuple[float | None, float | None, list[str]]:
    """Max outright FSR and height from whichever district rules fired."""
    fsr = height = None
    used: list[str] = []
    for r in results:
        if r.get("check") == "district_outright_fsr" and r["status"] != "not_applicable":
            fsr = r["values"].get("max_fsr_outright")
            used.append(r["rule_id"])
        if r.get("check") == "district_outright_height" and r["status"] != "not_applicable":
            height = r["values"].get("max_height_m_outright")
            used.append(r["rule_id"])
    return fsr, height, used


ANCHORS = {   # anchor -> (x: 0 left, 0.5 centre, 1 right; y: 0 front, 0.5 middle, 1 rear) within the plate box
    "front-left": (0, 0), "front": (0.5, 0), "front-right": (1, 0),
    "left": (0, 0.5), "centre": (0.5, 0.5), "right": (1, 0.5),
    "rear-left": (0, 1), "rear": (0.5, 1), "rear-right": (1, 1),
}


def place(spec: dict, plate_m2: float, w: float, d: float, box: dict, default_anchor: str,
          warnings: list[str]) -> tuple[list[list[float]], float, float, dict[str, Any]]:
    """Where the architect put the proposed plate (`option.massing`): against a side or corner of the plate box
    (`anchor`), shifted by `dx_m` (along the frontage) and `dy_m` (into the lot), turned a quarter (`rotate`: the
    w x d plate becomes d x w). The footprint never leaves the box: a rotated plate that does not fit is refit to the
    box keeping its area, and a shift past the box is clamped; each says so in `warnings`."""
    if not isinstance(spec, dict):
        raise ValueError("option.massing must be a dict: {anchor, dx_m, dy_m, rotate}.")
    anchor = spec.get("anchor") or default_anchor
    if anchor not in ANCHORS:
        raise ValueError(f"option.massing anchor {anchor!r} is not one of {', '.join(ANCHORS)}.")
    dx, dy = float(spec.get("dx_m") or 0), float(spec.get("dy_m") or 0)
    rotate = bool(spec.get("rotate"))
    bx, by, bw, bd = float(box["x"]), float(box["y"]), float(box["w"]), float(box["d"])
    if rotate:
        w, d = d, w
        if w > bw + 1e-6 or d > bd + 1e-6:
            was = (w, d)
            w = min(w, bw)
            d = plate_m2 / w if w else d
            if d > bd:
                d = bd
                w = min(bw, plate_m2 / d) if d else w
            warnings.append(f"The turned plate, {was[0]:.1f} × {was[1]:.1f} m, does not fit the {bw:.1f} × {bd:.1f} m plate box; "
                            f"it is refit to {w:.1f} × {d:.1f} m, keeping its {w * d:,.0f} m².")
    fx, fy = ANCHORS[anchor]
    x0 = bx + (bw - w if fx == 1 else (bw - w) / 2 if fx == 0.5 else 0.0) + dx
    y0 = by + (bd - d if fy == 1 else (bd - d) / 2 if fy == 0.5 else 0.0) + dy
    cx = min(max(x0, bx), bx + bw - w)
    cy = min(max(y0, by), by + bd - d)
    moved = math.hypot(cx - x0, cy - y0)
    clamped = moved > 1e-6
    if clamped:
        warnings.append(f"The mass was moved {moved:.1f} m back inside the setback envelope (the {bw:.1f} × {bd:.1f} m plate box): "
                        f"the shift of {dx:+.1f} m across and {dy:+.1f} m back from the {anchor} anchor took it past the box.")
        x0, y0 = cx, cy
    placement = {"anchor": anchor, "dx_m": round(dx, 2), "dy_m": round(dy, 2), "rotate": rotate, "clamped": clamped,
                 "box": {"x": round(bx, 2), "y": round(by, 2), "w": round(bw, 2), "d": round(bd, 2)}}
    return _rect(x0, y0, w, d), w, d, placement


def build(site: dict, option: dict, ledger: dict) -> dict[str, Any]:
    results = ledger["results"]
    W = float(site.get("frontage_m") or 0)
    D = float(site.get("depth_m") or 0)
    area = float(site.get("site_area_m2") or (W * D))
    sb = option.get("setbacks_m") or {"front": 0, "rear": 0, "side": 0}
    f2f = float(option.get("floor_to_floor_m") or 3.0)
    warnings: list[str] = []
    if not W or not D:
        raise ValueError("Site needs frontage_m and depth_m for the massing.")
    if abs(W * D - area) / area > 0.05:
        warnings.append(f"Lot is not a clean rectangle: frontage x depth = {W * D:,.0f} m² against a recorded {area:,.0f} m²; the plan uses the rectangle, the FSR uses the recorded area.")

    # the front face the architect chose (site.front_face): the lot turned so that face is the street side
    oriented = boundary.oriented_ring(site)
    if oriented and oriented["rectangle"]:
        W, D = oriented["frontage_m"], oriented["depth_m"]      # a plain lot: the rectangle turned, W and D swapped on a quarter turn

    # the lot: the equivalent rectangle, or the parcel polygon / drawn boundary where the site carries one
    lot = {"polygon": _rect(0, 0, W, D), "frontage_m": W, "depth_m": D, "area_m2": area, "street_side": "y = 0"}
    if oriented:
        lot.update({"front_face": oriented["front_face"], "orientation": oriented["orientation"], "front_edge": oriented["edge"]})
    ring = boundary.lot_ring(site)
    if ring and oriented:
        ring = {k: oriented[k] for k in ("ring", "source", "frame", "note")}
        W, D = oriented["frontage_m"], oriented["depth_m"]      # the oriented ring's bounding extent
        lot.update({"frontage_m": W, "depth_m": D})
    box = None   # the plate box: x, y, w, d of the rectangle the masses stand in
    if ring:
        poly_area = boundary.area(ring["ring"])
        # the corners a hand would draw: no curve segments (turned with the ring, so edge numbers stay the same)
        corners = [tuple(p) for p in oriented["corners"]] if oriented else boundary.simplify([tuple(p) for p in ring["ring"]], 3.0, 0.5)
        lot.update({"polygon": ring["ring"], "corners": [[round(x, 2), round(y, 2)] for x, y in corners],
                    "bbox": boundary.bbox(ring["ring"]), "source": ring["source"], "frame": ring["frame"],
                    "polygon_area_m2": round(poly_area, 1), "shape": boundary.shape_summary(ring["ring"]), "note": ring["note"]})
        if area and abs(poly_area - area) / area > 0.05:
            warnings.append(f"The lot polygon measures {poly_area:,.0f} m² against a recorded site area of {area:,.0f} m²; the FSR uses the recorded area, the plan the polygon. Check which is the development site.")
        env_poly = boundary.inset(ring["ring"], sb)
        box = boundary.largest_rect(env_poly, PLATE_GRID_M) if env_poly else None
        if not box:
            warnings.append("The setbacks leave no envelope inside the lot polygon that a rectangular plate fits; the equivalent rectangle is used for the envelope.")
    if box:
        env_w, env_d = box["w"], box["d"]
        env_area = boundary.area(env_poly)
        env = {"polygon": env_poly, "width_m": round(env_w, 2), "depth_m": round(env_d, 2), "area_m2": round(env_area, 1), "setbacks_m": sb,
               "box": box, "note": "the lot polygon inset by the setbacks (front for edges facing the street, rear for edges facing away, side for the rest); the plate box is the largest rectangle inside it"}
        plate_cap = box["area_m2"]
    else:
        env_w = W - 2 * float(sb.get("side", 0))
        env_d = D - float(sb.get("front", 0)) - float(sb.get("rear", 0))
        # yards wider or deeper than the lot leave nothing, never a negative plate (16 Nov 2026: RT-3's 20 m rear
        # yard on 609 Heatley Ave, 15.2 m deep, gave a -6.6 m envelope, a negative FSR and negative rects in the sheets)
        if env_d <= 0:
            warnings.append(f"The setbacks leave no envelope: a front yard of {float(sb.get('front', 0)):g} m and a rear yard of {float(sb.get('rear', 0)):g} m "
                            f"on a lot {D:g} m deep. The masses are drawn with no plate; the yards, or which street is the front, must change before one fits.")
        if env_w <= 0:
            warnings.append(f"The setbacks leave no envelope: two side yards of {float(sb.get('side', 0)):g} m on a lot {W:g} m wide. "
                            "The masses are drawn with no plate; the yards must change before one fits.")
        env_w, env_d = max(0.0, env_w), max(0.0, env_d)
        env_area = env_w * env_d
        env = {"polygon": _rect(sb.get("side", 0), sb.get("front", 0), env_w, env_d), "width_m": round(env_w, 2), "depth_m": round(env_d, 2), "area_m2": round(env_area, 1), "setbacks_m": sb}
        box = {"x": float(sb.get("side", 0)), "y": float(sb.get("front", 0)), "w": env_w, "d": env_d, "area_m2": round(env_area, 1)}
        plate_cap = env_area

    masses: list[dict[str, Any]] = []

    # Where a plate smaller than the plate box sits: it keeps a usable depth (a double-loaded floor wants about
    # 12 m; a shallow box gives what it has) and gives up width instead, so a wide, shallow lot gets a block,
    # not a strip. On a corner lot the block stands at the street corner: the side the cross street is on, read
    # from the site's context frame where one has been fetched.
    cross = (((site.get("osm") or {}).get("frame") or {}).get("snapped_m") or {}).get("cross_street") or {}
    at_right = cross.get("side") == "right"
    if oriented and oriented["orientation"]["rotate_deg"] != 0:
        # the lot was turned: the corner that matters is where the old front street now meets the new front.
        # The old street side's outward normal (0, -1) turns to (sin θ, -cos θ); it is on the right where sin θ > 0.7.
        at_right = math.sin(math.radians(oriented["orientation"]["rotate_deg"])) > 0.7

    def footprint(plate_m2: float) -> tuple[list[list[float]], float, float]:
        d = min(env_d, max(plate_m2 / env_w, min(env_d, PLATE_MIN_DEPTH_M))) if env_w else env_d
        w = min(env_w, plate_m2 / d) if d else env_w
        x0 = box["x"] + (env_w - w if at_right else 0.0)
        return _rect(x0, box["y"], w, d), w, d

    # Proposed mass: the option's GFA at its storey count. With no storey count the plate is drawn one storey high as
    # a placeholder, and the label and a warning say so (15 Nov 2026: a reviewer read it as a building someone chose).
    storeys_given = option.get("storeys") is not None
    storeys = int(option.get("storeys") or 1)
    if not storeys_given:
        warnings.append("The option gives no storey count: the proposed mass is drawn one storey high on the plate the setbacks leave, as a placeholder, not a building anyone chose.")
    gfa = float(option.get("gfa_m2") or 0)
    plate = gfa / storeys if gfa else plate_cap
    if plate > plate_cap:
        where = f"the plate box of {plate_cap:,.0f} m² (the largest rectangle inside the {env_area:,.0f} m² envelope)" if ring and env.get("box") else f"the setback envelope of {env_area:,.0f} m²"
        warnings.append(f"Proposed plate of {plate:,.0f} m² exceeds {where}; the mass fills it and the shortfall must go into more storeys, smaller setbacks or a plate that follows the lot line.")
        plate = plate_cap
    p_ring, p_w, depth = footprint(plate)
    placement = None
    if option.get("massing") is not None:
        p_ring, p_w, depth, placement = place(option["massing"], plate, p_w, depth, box, "front-right" if at_right else "front-left", warnings)
    h = storeys * f2f
    parapet = option.get("height_m")
    if parapet and parapet > h:
        warnings.append(f"Option height {parapet} m exceeds {storeys} x {f2f} m = {h:.1f} m; the extra {parapet - h:.1f} m is parapet, roof structure or taller ground floor, and the mass uses the stated height.")
        h = float(parapet)
    masses.append({
        "name": "proposed", "label": (f"Proposed: {storeys} storeys, FSR {gfa / area:.2f}" if gfa else f"Proposed: {storeys} storeys") if storeys_given else "Proposed: storeys not given, drawn at one storey as a placeholder",
        "footprint": p_ring, "plate_width_m": round(p_w, 2), "plate_depth_m": round(depth, 2), "at_street_corner": "right" if at_right else "left",
        "base_z": 0.0, "height_m": round(h, 2), "storeys": storeys, "floor_to_floor_m": f2f,
        "plate_area_m2": round(plate, 1), "gfa_m2": round(plate * storeys, 1), "fsr": round(plate * storeys / area, 3),
        "derived_from": ["option.gfa_m2", "option.storeys", "option.setbacks_m", "option.floor_to_floor_m"]
                        + (["option.massing"] if placement else []) + (["site.front_face"] if oriented else []),
    })
    if placement:
        masses[-1]["placement"] = placement

    # Outright mass: what the schedule allows with no rezoning.
    max_fsr, max_h, used = _outright_params(results)
    if max_fsr and max_h:
        o_storeys = max(1, int(math.floor(max_h / f2f)))
        # a CD-1 by-law can fix the site area its FSR is computed on (the check records it in its values)
        fixed = next((r["values"]["site_area_m2"] for r in results if r.get("check") == "district_outright_fsr"
                      and r["status"] != "not_applicable" and (r.get("values") or {}).get("fsr_site_area_fixed")), None)
        o_gfa = max_fsr * (fixed or area)
        o_plate = min(o_gfa / o_storeys, plate_cap)
        o_ring, o_w, o_d = footprint(o_plate)
        masses.append({
            "name": "outright", "label": f"Outright: FSR {max_fsr}, {max_h} m",
            "footprint": o_ring, "plate_width_m": round(o_w, 2), "plate_depth_m": round(o_d, 2), "at_street_corner": "right" if at_right else "left",
            "base_z": 0.0, "height_m": round(min(o_storeys * f2f, max_h), 2), "storeys": o_storeys, "floor_to_floor_m": f2f,
            "plate_area_m2": round(o_plate, 1), "gfa_m2": round(o_plate * o_storeys, 1), "fsr": round(o_plate * o_storeys / area, 3),
            "derived_from": used + ["option.setbacks_m", "option.floor_to_floor_m"] + (["site.front_face"] if oriented else []),
        })

    # Policy benchmark, if a rezoning policy fired.
    bench = None
    irp = _find(results, "cov.irp.social_housing_rezoning")
    if irp and irp["status"] in ("pass", "conditional"):
        v = irp["values"]
        bench = {"height_m": v.get("benchmark_height_m"), "fsr": v.get("benchmark_fsr"), "rule_id": irp["rule_id"], "source": irp.get("source", {})}

    # Trees: what the plan must leave room for.
    trees = _find(results, "cov.trees.replacement")
    tree_note = None
    if trees and trees["status"] != "not_applicable":
        v = trees["values"]
        tree_note = {"required": v.get("schedule_c_required"), "after": v.get("trees_after"), "shortfall": v.get("shortfall"),
                     "retained_barriers": v.get("protection_barriers", []), "rule_id": trees["rule_id"]}

    return {
        "units": "m", "origin": "front-left lot corner; x along frontage, y into the lot, z up",
        "site_id": site.get("id"), "option_id": option.get("id"), "as_of": ledger["run"]["as_of"], "stamp": ledger["run"]["stamp"]["stamp"],
        "lot": lot, "envelope": env, "masses": masses, "policy_benchmark": bench, "trees": tree_note, "warnings": warnings,
    }


# ---------------------------------------------------------------- SVG

# The drawing tones of the UI's figures (DESIGN.md): drawing ink and muted on white paper, envelope
# blue for the proposed mass, lane grey for the outright one, red for the setback envelope, amber for
# the staff benchmark. The SVG is the same drawing in the memo, the UI and the committed run folders.
DRAWING_COLOURS = {
    "paper": "#ffffff", "ink": "#1f2933", "muted": "#5f6672", "lot": "#f4f4f2",
    "envelope": "#c81e1e", "proposed": "#3c8cdc", "proposed_line": "#2a6fb8",
    "outright": "#bdbdbd", "outright_line": "#8e8e8e", "benchmark": "#c77d14",
}


def svg(m: dict[str, Any]) -> str:
    """Plan (left) and section (right) of the masses, to scale, with the numbers printed."""
    W, D = m["lot"]["frontage_m"], m["lot"]["depth_m"]
    bb = m["lot"].get("bbox") or [0, 0, W, D]    # a polygon lot can run past the equivalent rectangle
    bw, bd = bb[2] - bb[0], bb[3] - bb[1]
    masses = {x["name"]: x for x in m["masses"]}
    hmax = max(x["height_m"] for x in m["masses"])
    if m.get("policy_benchmark") and m["policy_benchmark"].get("height_m"):
        hmax = max(hmax, m["policy_benchmark"]["height_m"][1])
    pad, gap = 48, 60
    scale = min(420 / bw, 320 / bd, 260 / max(hmax, 1))
    scale = max(scale, 3.0)
    plan_w, plan_h = bw * scale, bd * scale
    sec_w, sec_h = W * scale, hmax * scale
    width = pad + plan_w + gap + sec_w + pad
    lines = []
    for x in m["masses"]:
        lines.append(f'{x["label"]}: plate {x["plate_area_m2"]:,.0f} m² × {x["storeys"]} = {x["gfa_m2"]:,.0f} m² (FSR {x["fsr"]:.2f}), {x["height_m"]} m high')
    if m.get("trees"):
        t = m["trees"]
        lines.append(f'Trees: Schedule C requires {t["required"]}, plan leaves {t["after"]} (shortfall {t["shortfall"]}); keep 1.0 m from side lines, 1.5 m from the building, 2.5 m apart')
    lines.append(f'Rules as of {m["as_of"]} · stamp {m["stamp"]} · generated by ffm, not a survey')
    height = pad + 24 + max(plan_h, sec_h) + 40 + len(lines) * 16 + 16
    ox, oy = pad, pad + 24
    sx, sy = pad + plan_w + gap, pad + 24 + max(plan_h, sec_h)  # section baseline

    def P(pts, fill, stroke, dash="", op=1.0):
        d = " ".join(f"{ox + (x - bb[0]) * scale:.1f},{oy + (y - bb[1]) * scale:.1f}" for x, y in pts)
        return f'<polygon points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" stroke-dasharray="{dash}" fill-opacity="{op}"/>'

    C = DRAWING_COLOURS
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}" font-family="IBM Plex Sans, Helvetica, Arial, sans-serif" font-size="12" fill="{C["ink"]}">',
           f'<rect width="100%" height="100%" fill="{C["paper"]}"/>',
           f'<text x="{ox}" y="{pad - 4}" font-size="14" font-weight="600">Plan · {m["site_id"]} · {m["lot"]["frontage_m"]} × {m["lot"]["depth_m"]} m, {m["lot"]["area_m2"]:,.0f} m²</text>',
           P(m["lot"]["polygon"], C["lot"], C["ink"]),
           P(m["envelope"]["polygon"], "none", C["envelope"], dash="6 4")]
    if "outright" in masses:
        out.append(P(masses["outright"]["footprint"], C["outright"], C["outright_line"], op=0.9))
    if "proposed" in masses:
        out.append(P(masses["proposed"]["footprint"], C["proposed"], C["proposed_line"], op=0.5))
    out.append(f'<text x="{ox}" y="{oy + plan_h + 16}" fill="{C["muted"]}">street (y = 0 is the top edge) · dashed = setback envelope{", plate box" if m["envelope"].get("box") and m["lot"].get("bbox") else ""} {m["envelope"]["width_m"]} × {m["envelope"]["depth_m"]} m</text>')

    # Section
    out.append(f'<text x="{sx}" y="{pad - 4}" font-size="14" font-weight="600">Section across the frontage · heights in m</text>')
    out.append(f'<line x1="{sx}" y1="{sy}" x2="{sx + sec_w}" y2="{sy}" stroke="{C["ink"]}" stroke-width="1.5"/>')
    env_x0 = ((m["envelope"].get("box") or {}).get("x", m["envelope"]["setbacks_m"].get("side", 0)) - bb[0]) * scale
    env_w = m["envelope"]["width_m"] * scale
    if "outright" in masses:
        o = masses["outright"]
        out.append(f'<rect x="{sx + env_x0:.1f}" y="{sy - o["height_m"] * scale:.1f}" width="{env_w:.1f}" height="{o["height_m"] * scale:.1f}" fill="{C["outright"]}" stroke="{C["outright_line"]}" stroke-width="1.5"/>')
        out.append(f'<text x="{sx + env_x0 + 6:.1f}" y="{sy - 6:.1f}" fill="{C["ink"]}">{o["label"]} · {o["storeys"]} storeys (grey)</text>')
    if "proposed" in masses:
        p = masses["proposed"]
        out.append(f'<rect x="{sx + env_x0:.1f}" y="{sy - p["height_m"] * scale:.1f}" width="{env_w:.1f}" height="{p["height_m"] * scale:.1f}" fill="{C["proposed"]}" fill-opacity="0.45" stroke="{C["proposed_line"]}" stroke-width="1.5"/>')
        for k in range(1, p["storeys"]):
            yk = sy - k * p["floor_to_floor_m"] * scale
            out.append(f'<line x1="{sx + env_x0:.1f}" y1="{yk:.1f}" x2="{sx + env_x0 + env_w:.1f}" y2="{yk:.1f}" stroke="{C["proposed_line"]}" stroke-width="0.6" stroke-opacity="0.6"/>')
        out.append(f'<text x="{sx + env_x0 + 6:.1f}" y="{sy - p["height_m"] * scale - 6:.1f}" fill="{C["proposed_line"]}" font-weight="600">{p["label"]} · {p["height_m"]} m</text>')
    b = m.get("policy_benchmark")
    if b and b.get("height_m"):
        lo, hi = b["height_m"]
        for hv, lab, dy in ((lo, f"staff benchmark {lo} m", 12), (hi, f"staff benchmark {hi} m", -3)):
            yv = sy - hv * scale
            out.append(f'<line x1="{sx}" y1="{yv:.1f}" x2="{sx + sec_w}" y2="{yv:.1f}" stroke="{C["benchmark"]}" stroke-width="1" stroke-dasharray="4 3"/>')
            out.append(f'<text x="{sx + sec_w - 4:.1f}" y="{yv + dy:.1f}" fill="{C["benchmark"]}" text-anchor="end" font-size="11">{lab}</text>')

    # Footer: the numbers and the stamp
    fy = pad + 24 + max(plan_h, sec_h) + 40
    for i, ln in enumerate(lines):
        out.append(f'<text x="{ox}" y="{fy + i * 16}" fill="{C["ink"]}">{_esc(ln)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write(m: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pj = out_dir / "massing.json"
    ps = out_dir / "massing.svg"
    pj.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    ps.write_text(svg(m), encoding="utf-8")
    return pj, ps
