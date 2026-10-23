"""Rule-derived massing: turn the lot, the setbacks and the ledger's numbers into simple extrusions.

Two masses are produced so the memo can show the gap the rezoning has to close:

    outright   what the district schedule allows without rezoning (max FSR x site area, under the
               outright height), filled from the front setback back
    proposed   the option's gross floor area at its storey count, same envelope

Everything is a rectangle on a rectangular lot. That is deliberate: this is the feasibility stage,
and the point is that the numbers in the memo and the box in Revit are the same numbers.

Coordinates: metres, origin at the front-left lot corner, x along the frontage, y into the lot
(away from the street), z up. massing.json is what the pyRevit script reads.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


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

    env_w = W - 2 * float(sb.get("side", 0))
    env_d = D - float(sb.get("front", 0)) - float(sb.get("rear", 0))
    env_area = env_w * env_d
    env = {"polygon": _rect(sb.get("side", 0), sb.get("front", 0), env_w, env_d), "width_m": round(env_w, 2), "depth_m": round(env_d, 2), "area_m2": round(env_area, 1), "setbacks_m": sb}

    masses: list[dict[str, Any]] = []

    # Proposed mass: the option's GFA at its storey count.
    storeys = int(option.get("storeys") or 1)
    gfa = float(option.get("gfa_m2") or 0)
    plate = gfa / storeys if gfa else env_area
    if plate > env_area:
        warnings.append(f"Proposed plate of {plate:,.0f} m² exceeds the setback envelope of {env_area:,.0f} m²; the mass fills the envelope and the shortfall must go into more storeys or smaller setbacks.")
        plate = env_area
    depth = plate / env_w
    h = storeys * f2f
    parapet = option.get("height_m")
    if parapet and parapet > h:
        warnings.append(f"Option height {parapet} m exceeds {storeys} x {f2f} m = {h:.1f} m; the extra {parapet - h:.1f} m is parapet, roof structure or taller ground floor, and the mass uses the stated height.")
        h = float(parapet)
    masses.append({
        "name": "proposed", "label": f"Proposed: {storeys} storeys, FSR {gfa / area:.2f}" if gfa else f"Proposed: {storeys} storeys",
        "footprint": _rect(sb.get("side", 0), sb.get("front", 0), env_w, depth),
        "base_z": 0.0, "height_m": round(h, 2), "storeys": storeys, "floor_to_floor_m": f2f,
        "plate_area_m2": round(plate, 1), "gfa_m2": round(plate * storeys, 1), "fsr": round(plate * storeys / area, 3),
        "derived_from": ["option.gfa_m2", "option.storeys", "option.setbacks_m", "option.floor_to_floor_m"],
    })

    # Outright mass: what the schedule allows with no rezoning.
    max_fsr, max_h, used = _outright_params(results)
    if max_fsr and max_h:
        o_storeys = max(1, int(math.floor(max_h / f2f)))
        o_gfa = max_fsr * area
        o_plate = min(o_gfa / o_storeys, env_area)
        masses.append({
            "name": "outright", "label": f"Outright: FSR {max_fsr}, {max_h} m",
            "footprint": _rect(sb.get("side", 0), sb.get("front", 0), env_w, o_plate / env_w),
            "base_z": 0.0, "height_m": round(min(o_storeys * f2f, max_h), 2), "storeys": o_storeys, "floor_to_floor_m": f2f,
            "plate_area_m2": round(o_plate, 1), "gfa_m2": round(o_plate * o_storeys, 1), "fsr": round(o_plate * o_storeys / area, 3),
            "derived_from": used + ["option.setbacks_m", "option.floor_to_floor_m"],
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
        "lot": {"polygon": _rect(0, 0, W, D), "frontage_m": W, "depth_m": D, "area_m2": area, "street_side": "y = 0"},
        "envelope": env, "masses": masses, "policy_benchmark": bench, "trees": tree_note, "warnings": warnings,
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
    masses = {x["name"]: x for x in m["masses"]}
    hmax = max(x["height_m"] for x in m["masses"])
    if m.get("policy_benchmark") and m["policy_benchmark"].get("height_m"):
        hmax = max(hmax, m["policy_benchmark"]["height_m"][1])
    pad, gap = 48, 60
    scale = min(420 / W, 320 / D, 260 / max(hmax, 1))
    scale = max(scale, 3.0)
    plan_w, plan_h = W * scale, D * scale
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
        d = " ".join(f"{ox + x * scale:.1f},{oy + y * scale:.1f}" for x, y in pts)
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
    out.append(f'<text x="{ox}" y="{oy + plan_h + 16}" fill="{C["muted"]}">street (y = 0 is the top edge) · dashed = setback envelope {m["envelope"]["width_m"]} × {m["envelope"]["depth_m"]} m</text>')

    # Section
    out.append(f'<text x="{sx}" y="{pad - 4}" font-size="14" font-weight="600">Section across the frontage · heights in m</text>')
    out.append(f'<line x1="{sx}" y1="{sy}" x2="{sx + sec_w}" y2="{sy}" stroke="{C["ink"]}" stroke-width="1.5"/>')
    env_x0 = m["envelope"]["setbacks_m"].get("side", 0) * scale
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
