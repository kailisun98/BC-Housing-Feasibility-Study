"""Rule-derived suggestions: an option proposed from the site and the chosen programs, with the rule behind
every figure. Deterministic, standard library only, no model: the same site, date and programs give the same
suggestion every run, and a person accepts or replaces each figure before anything is run.

    suggest(site, programs, on) -> {
        "candidate": "funder-ready",                 the one built
        "candidates": [{"id", "title", "available", "why"}, ...]
        "option": {...},                             a complete option file, ready to run
        "fields": {"storeys": {"value", "rule_id", "note"}, "units.two_bed": {...}, ...}
        "unsure": [{"key", "why", "who"}, ...]       what the rules cannot settle and a person must
        "assumptions": [{"key", "value", "note"}]    the declared placeholders the derivation used
        "as_of": "...", "stamp": {...}
    }

Three candidates:
    outright      what the district allows as of right (layer A), or the SSMUH minimum on a small lot (B)
    benchmark     the staff benchmark under the Interim Rezoning Policy for social housing (A), where it applies
    funder-ready  the benchmark envelope with every figure the chosen programs read filled from their criteria (C to E)

The derivation walks the layers in order and records which rule set each figure; what no rule settles (a
transit-oriented tier, a CD-1 negotiation, site control, land tenure) is listed under "unsure" and left blank.
"""

from __future__ import annotations

import math
from datetime import date
from pathlib import Path
from typing import Any

from .checks import (LANE_TO_CENTRE_LINE_M, _schedule_c_required, corner_streets, district_setbacks, fsr_limit, height_limit, lot_as_fronted,
                     other_front, yard_minimums)
from .engine import evaluate
from .rules_loader import RULES_DIR, Rule, district_of, load_rules, stamp

# Declared placeholders, not rules: a person can change them, and the memo says they were used.
ASSUMPTIONS = {
    "floor_to_floor_m": (3.3, "usual for wood-frame residential; the committed options use it"),
    "setbacks_m": ({"front": 3.7, "rear": 6.0, "side": 3.0}, "not read from the district schedule; the committed options assume them on a 37 m deep lot, and a shallower or narrower lot gets them scaled down (front 12%, rear 20% of the depth, sides 8% of the frontage, each at most these)"),
    "net_efficiency": (0.78, "net residential floor area as a share of residential GFA; typical for a double-loaded corridor"),
    "design_allowance": (1.10, "units drawn 10% above the BC Housing minimum net areas"),
    "mix_shares": ({"studio": 0.20, "one_bed": 0.40, "two_bed": 0.32, "three_bed_plus": 0.08},
                   "a starting bedroom mix that clears the family-unit minimums; the person tunes it"),
}

MIX_KEYS = ("studio", "one_bed", "two_bed", "three_bed_plus")

# Bedroom mixes a manager can start from. Not rules: each is a starting point the family-unit minimums still apply to.
MIX_PRESETS = {
    "starting": {"shares": dict(ASSUMPTIONS["mix_shares"][0]), "note": "the tool's placeholder mix: clears the family-unit minimums with a margin"},
    "family": {"shares": {"studio": 0.10, "one_bed": 0.25, "two_bed": 0.45, "three_bed_plus": 0.20}, "note": "weighted to families: two in three homes have two or more bedrooms"},
    "seniors_singles": {"shares": {"studio": 0.35, "one_bed": 0.50, "two_bed": 0.15, "three_bed_plus": 0.0}, "note": "mostly studios and one-bedrooms for seniors and single people; the family-unit minimums will move some up"},
    "balanced": {"shares": {"studio": 0.25, "one_bed": 0.25, "two_bed": 0.40, "three_bed_plus": 0.10}, "note": "an even spread across the bedroom types"},
}

PLATE_GRID_M = 0.5   # the grid the plate box is found on inside a polygon envelope (as ffm.massing)


def check_mix(mix: Any) -> dict[str, float] | None:
    """A manager's bedroom shares, checked: a dict of studio / one_bed / two_bed / three_bed_plus, each 0 to 1, summing
    to 1 within 0.01 (a missing key counts as 0). None stays None. Raises ValueError with a plain message otherwise."""
    if mix is None:
        return None
    if not isinstance(mix, dict):
        raise ValueError("The unit mix must be a set of shares: studio, one_bed, two_bed, three_bed_plus.")
    extra = [k for k in mix if k not in MIX_KEYS]
    if extra:
        raise ValueError(f"The unit mix has unknown types: {', '.join(map(str, extra))}. Use studio, one_bed, two_bed, three_bed_plus.")
    out: dict[str, float] = {}
    for k in MIX_KEYS:
        v = mix.get(k, 0)
        if v is None:
            v = 0
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
            raise ValueError(f"The share for {k} must be a number between 0 and 1.")
        if v < 0 or v > 1:
            raise ValueError(f"The share for {k} must be between 0 and 1 (got {v}).")
        out[k] = float(v)
    total = sum(out.values())
    if abs(total - 1) > 0.01:
        raise ValueError(f"The unit mix shares must add up to 100% (they add up to {total * 100:.0f}%).")
    return out


FIXED_KEYS = ("storeys", "height_m", "gfa_m2")


DESCRIBES = ("housing_type", "building_type", "podium_storeys", "tower_plate_m2", "beds")


def check_fixed(fixed: Any) -> dict[str, Any]:
    """The manager's own figures the derivation carries on from, checked: storeys (a whole number), height_m and gfa_m2
    (positive numbers) and units (a count per bedroom type), each optional. None is {}. Raises ValueError with a plain
    message otherwise."""
    if fixed is None:
        return {}
    if not isinstance(fixed, dict):
        raise ValueError("The fixed figures must be a set: storeys, height_m, gfa_m2, units.")
    # what the manager said of the building (24 Nov 2026) travels with the figures and is not a figure to check here
    fixed = {k: v for k, v in fixed.items() if k not in DESCRIBES}
    extra = [k for k in fixed if k not in FIXED_KEYS + ("units",)]
    if extra:
        raise ValueError(f"Unknown fixed figures: {', '.join(map(str, extra))}. Use storeys, height_m, gfa_m2, units.")
    num = lambda v: not isinstance(v, bool) and isinstance(v, (int, float)) and v == v
    out: dict[str, Any] = {}
    for k in FIXED_KEYS:
        v = fixed.get(k)
        if v is None:
            continue
        if not num(v) or v <= 0 or (k == "storeys" and int(v) != v):
            raise ValueError(f"{k} must be a positive {'whole ' if k == 'storeys' else ''}number (got {v!r}).")
        out[k] = int(v) if k == "storeys" else float(v)
    units = fixed.get("units")
    if units is not None:
        if not isinstance(units, dict) or any(k not in MIX_KEYS for k in units):
            raise ValueError("The fixed units must be counts of studio, one_bed, two_bed, three_bed_plus.")
        u = {}
        for k, v in units.items():
            if v is None:
                continue
            if not num(v) or v < 0 or int(v) != v:
                raise ValueError(f"The count of {k} must be a whole number of 0 or more (got {v!r}).")
            u[k] = int(v)
        if u:
            out["units"] = u
    return out


def _pct(shares: dict[str, float]) -> str:
    return " / ".join(f"{shares[k] * 100:.0f}" for k in MIX_KEYS) + "%"


def _plate(site: dict, sb: dict[str, float]) -> dict[str, Any] | None:
    """The setback envelope's plate box, as ffm.massing finds it: the largest rectangle inside the lot polygon inset
    by the setbacks, else the equivalent rectangle less the yards. None when the site has neither, or when the yards
    leave nothing. The lot is turned to `site.front_face` where one is named, as the massing turns it."""
    try:
        from . import boundary
        ring = boundary.oriented_ring(site) or boundary.lot_ring(site)
        if ring:
            env_poly = boundary.inset(ring["ring"], sb)
            box = boundary.turned_rect(env_poly, PLATE_GRID_M) if env_poly else None      # as massing.build finds it for a suggestion
            if box and box.get("area_m2"):
                return {"w": round(box["w"], 1), "d": round(box["d"], 1), "area": round(box["area_m2"], 1),
                        "how": "the largest rectangle inside the lot polygon less the setbacks" + (", turned to the lot's longest side" if box.get("angle_deg") else "")}
    except Exception:
        pass
    W, D = lot_as_fronted(site)
    if not W or not D:
        return None
    w = W - 2 * float(sb.get("side", 0))
    d = D - float(sb.get("front", 0)) - float(sb.get("rear", 0))
    if w <= 0 or d <= 0:
        return None
    return {"w": round(w, 1), "d": round(d, 1), "area": round(w * d, 1), "how": "the frontage and depth less the setbacks"}


def envelope_for(site: dict, rules: list[Rule], on: date, sb: dict[str, float], sb_rule: str | None = None) -> dict[str, Any]:
    """A rough allowed envelope from the site and the code, always: the most storeys the district's outright schedule
    lets in (else the Province's transit-oriented minimum for the tier, else the staff benchmark, else the wood-frame
    standard), and the plate the setbacks leave times the storeys, capped by the schedule's FSR where there is one.
    Rough, not a permission: the schedule, a rezoning or the Development Permit Board decides."""
    district = district_of(site)     # "CD-1 (324)" for a CD-1 site whose number is known: its own by-law's rules match
    area = float(site.get("site_area_m2") or 0)
    f2f, _ = ASSUMPTIONS["floor_to_floor_m"]
    r_fsr = _district_rule(rules, on, "district_outright_fsr", district)
    r_h = _district_rule(rules, on, "district_outright_height", district)
    p_wood = _params(rules, on, "bch.design_guidelines.unit_areas", district) or {}
    wood_max = int(p_wood.get("wood_frame_standard_max_storeys") or 6)
    p_toa = _params(rules, on, "bc.toa.minimum_density", district)
    p_irp = _params(rules, on, "cov.irp.social_housing_rezoning", district)
    tier = site.get("toa_tier")
    tier_storeys = None
    if site.get("in_transit_oriented_area") is True and tier not in (None, "") and p_toa:
        tier_storeys = (p_toa.get("tiers_storeys") or {}).get(str(tier).strip())
    fsr_cap = None
    rule_ids: list[str] = []
    if r_fsr and r_h and _social_height(site, r_h[1])[0] is not None:
        id_fsr, p_fsr = r_fsr
        id_h, p_h = r_h
        max_h, h_word = _social_height(site, p_h)     # the suggestion is 100% social housing (RM-4: the Director's variance)
        hl = height_limit(site, SOCIAL_PROBE, p_h)
        cap_storeys = hl["storeys"] if (hl["storeys"] and max_h == hl["max"]) else None
        storeys = min(int(math.floor(max_h / f2f)), wood_max)
        if cap_storeys:
            storeys = min(storeys, int(cap_storeys))
        basis = "schedule"
        storeys_from = (f"the most storeys of {f2f} m under {h_word} ({id_h}, {district})"
                        + (f", at most {cap_storeys} storeys" if cap_storeys else "")
                        + (f", capped at the wood-frame standard of {wood_max}" if storeys == wood_max else ""))
        s_fsr, _, s_cap = _social_fsr(site, p_fsr)
        if s_cap is not None:
            fsr_cap = (s_cap / area if area else 0.0, id_fsr, area)    # a CD-1 sub-area's fixed floor area, as an FSR on the site
        elif s_fsr is not None:
            fsr_cap = (s_fsr, id_fsr, float(p_fsr.get("fsr_site_area_m2") or area))   # a CD-1 can fix the area its FSR is on
        rule_ids = [id_h, id_fsr]
    elif tier_storeys:
        storeys = int(tier_storeys)
        basis = "toa"
        storeys_from = f"the Province's minimum allowable height in a tier {tier} transit-oriented area, {storeys} storeys (bc.toa.minimum_density); a floor the City must allow, not a cap"
        rule_ids = ["bc.toa.minimum_density"]
        # the tier's density with it (24 Nov 2026: a tier-1 CD-1 site was derived at 20 storeys and FSR 11.19, the plate
        # times the storeys, where the tier protects 5.0): above the tier's FSR is a rezoning's negotiation, not a figure
        # this screen derives
        t_fsr = (p_toa.get("tiers_fsr") or {}).get(str(tier).strip())
        if t_fsr:
            fsr_cap = (float(t_fsr), "bc.toa.minimum_density", area)
    elif p_irp and site.get("in_former_community_vision_area") is True:
        hi = p_irp["benchmark_height_m_high"]
        storeys = min(int(math.floor(hi / f2f)), wood_max)
        basis = "benchmark"
        storeys_from = f"the most storeys of {f2f} m inside the staff benchmark of up to {hi} m for social housing (cov.irp.social_housing_rezoning)"
        fsr_cap = (float(p_irp["benchmark_fsr"]), "cov.irp.social_housing_rezoning", area)
        rule_ids = ["cov.irp.social_housing_rezoning"]
    else:
        storeys = wood_max
        basis = "wood_frame"
        storeys_from = (f"no schedule for {district or 'this district'} in the rule stack, so the wood-frame standard of {wood_max} storeys "
                        "(bch.design_guidelines.unit_areas): a placeholder basis for what a non-profit usually builds, not a zoning limit")
        rule_ids = ["bch.design_guidelines.unit_areas"]
    if sb_rule:
        rule_ids.append(sb_rule)
    height = round(storeys * f2f, 1)
    plate = _plate(site, sb)
    sb_words = "the schedule's yards" if sb_rule else "the placeholder setbacks"
    gfa = None
    if plate:
        gfa = round(plate["area"] * storeys, 0)
        gfa_from = f"the plate the setbacks leave ({plate['how']}, {sb_words}), {plate['w']} × {plate['d']} m = {plate['area']:,.0f} m², × {storeys} storeys = {gfa:,.0f} m²"
    elif all(lot_as_fronted(site)):
        W, D = lot_as_fronted(site)
        gfa_from = (f"no plate to multiply: {sb_words} (front {sb.get('front', 0):g} m, rear {sb.get('rear', 0):g} m, sides {sb.get('side', 0):g} m) "
                    f"leave no envelope on a lot {W:g} m wide and {D:g} m deep as fronted")
    else:
        gfa_from = "no frontage, depth or lot polygon, so no plate to multiply"
    if fsr_cap and fsr_cap[2]:
        cap = round(fsr_cap[0] * fsr_cap[2], 0)
        if gfa is None or gfa > cap:
            gfa_from += (f"; capped by the FSR of {fsr_cap[0]} × the site area {fsr_cap[2]:,.0f} m² = {cap:,.0f} m² ({fsr_cap[1]}): the FSR governs" if gfa is not None
                         else f"; the FSR of {fsr_cap[0]} × the site area {fsr_cap[2]:,.0f} m² = {cap:,.0f} m² ({fsr_cap[1]})")
            gfa = cap
        else:
            gfa_from += f"; under the FSR of {fsr_cap[0]} × {fsr_cap[2]:,.0f} m² = {cap:,.0f} m² ({fsr_cap[1]}): the setbacks govern"
    return {
        "storeys": storeys, "height_m": height, "gfa_m2": gfa,
        "plate_m2": plate["area"] if plate else None, "plate_w_m": plate["w"] if plate else None, "plate_d_m": plate["d"] if plate else None,
        "basis": basis, "storeys_from": storeys_from, "gfa_from": gfa_from, "rule_ids": rule_ids,
        "note": (f"Rough allowed, not a permission: {storeys} storeys at {f2f} m ({height} m) and about {gfa:,.0f} m² of floor area. " if gfa is not None else
                 f"Rough allowed, not a permission: {storeys} storeys at {f2f} m ({height} m). ")
                + "Take it or keep your own; the district schedule, a rezoning or the permit decides what is allowed.",
    }


CANDIDATES = [
    {"id": "outright", "title": "Outright", "what": "what the district allows as of right"},
    {"id": "benchmark", "title": "Benchmark", "what": "the staff benchmark under the social housing rezoning policy"},
    {"id": "funder-ready", "title": "Funder-ready", "what": "the envelope the site gets (the benchmark where it applies, else the schedule, else the rough envelope) with every funder question answered"},
]


def setbacks_for(site: dict) -> dict[str, float]:
    """The placeholder setbacks, scaled to the lot: the committed figures (3.7 / 6.0 / 3.0 m) on a lot as deep as
    998 E 19th Ave, and no more than 12% of the depth in front, 20% behind and 8% of the frontage each side on a
    smaller one, so a shallow corner lot keeps a buildable envelope. Still a placeholder, declared as such."""
    base, _ = ASSUMPTIONS["setbacks_m"]
    W, D = lot_as_fronted(site)     # the lot as fronted: turned where site.front_face names another face
    if not W or not D:
        out = dict(base)
    else:
        out = {"front": round(min(base["front"], D * 0.12), 1), "rear": round(min(base["rear"], D * 0.20), 1), "side": round(min(base["side"], W * 0.08), 1)}
    # a street built to its lot lines (23 Nov 2026: the Downtown Eastside, a commercial street): where the site says so,
    # no front or side yard is assumed; the rear placeholder stays, for the lane. Still a placeholder, said as one.
    if site.get("builds_to_lot_lines") is True:
        out["front"], out["side"] = 0.0, 0.0
    return out


def _rule(rules: list[Rule], rule_id: str) -> Rule | None:
    return next((r for r in rules if r.id == rule_id), None)


def _params(rules: list[Rule], on: date, rule_id: str, district: str = "*") -> dict | None:
    """The params of a rule in force on the date and applying to the district, else None."""
    r = _rule(rules, rule_id)
    if r is None or not r.applies_to(district):
        return None
    v = r.version_on(on)
    return v.params if v else None


def _district_rule(rules: list[Rule], on: date, check: str, district: str) -> tuple[str, dict] | None:
    """The rule with this check that applies to the district and is in force (any district's schedule, once it
    is in the stack: RM-1 by hand, RT-3 once a reading of its schedule is confirmed). Returns (rule id, params)."""
    for r in rules:
        if r.check == check and r.applies_to(district) and "*" not in r.applies_to_districts:
            v = r.version_on(on)
            if v:
                return r.id, v.params
    return None


SOCIAL_PROBE = {"tenure": "social_housing"}     # every suggestion is 100% social housing


def street_floor_m2(site: dict, p_fsr: dict | None) -> int:
    """The non-dwelling floor area at the street a schedule's rental FSR asks for (C-2 s.3.1.1.1: 0.35 FSR), in whole
    m² on this lot; 0 where the schedule asks for none. The suggestion puts it on the ground floor so that it earns the
    figure it takes (23 Nov 2026: an all-residential suggestion took 3.5)."""
    need = (p_fsr or {}).get("rental_min_non_dwelling_fsr")
    area = float((p_fsr or {}).get("fsr_site_area_m2") or site.get("site_area_m2") or 0)
    return int(math.ceil(need * area - 1e-9)) if need and area else 0


def _probe(site: dict, p_fsr: dict | None) -> dict:
    nonres = street_floor_m2(site, p_fsr)
    return {**SOCIAL_PROBE, "non_residential_gfa_m2": nonres} if nonres else SOCIAL_PROBE


def _social_fsr(site: dict, p_fsr: dict) -> tuple[float | None, str, float | None]:
    """The FSR a 100% social housing suggestion takes from a schedule (checks.fsr_limit: the schedule's social housing
    or rental figure, the site's row of a table, a CD-1 sub-area's fixed floor area), the words for it, and the floor
    area in m² where the by-law fixes one. None where no figure applies to the site (a sub-area not recorded)."""
    lim = fsr_limit(site, _probe(site, p_fsr), p_fsr)
    if lim["max"] is None:
        return None, lim["short"] or "no figure applies to this site", None
    if lim["floor_area_cap"] is not None:
        return float(lim["max"]), f"the floor area the by-law fixes{lim['words']}", lim["floor_area_cap"]
    return float(lim["max"]), f"the outright FSR of {lim['max']}{lim['words']}", None


def _social_height(site: dict, p_h: dict) -> tuple[float, str]:
    """The height a 100% social housing suggestion takes from a schedule, and the words for it: the most the Director of
    Planning may vary it to for social housing where the schedule says so (RM-4 s.3.1.2.11), a discretionary approval,
    else the outright maximum for this site and tenure (checks.height_limit)."""
    lim = height_limit(site, SOCIAL_PROBE, p_h)
    if lim["discretionary"] and lim["discretionary_social"]:
        return float(lim["discretionary"]), (f"the {lim['discretionary']} m the Director of Planning may allow for 100% social housing ({lim['discretionary_clause']}; "
                                             f"{lim['max']} m outright), a variance to ask for, not a right")
    if lim["max"] is None:      # a plan that gives this site no outright maximum (a sub-area not recorded, or none printed)
        if lim["discretionary"]:
            return float(lim["discretionary"]), (f"the {lim['discretionary']} m the Director of Planning may allow{lim['words']} ({lim['discretionary_clause']}); "
                                                 "the plan states no outright maximum there, so this is a discretion to ask for, not a right")
        return None, "no height applies until the site's sub-area is recorded"
    return float(lim["max"]), f"the outright maximum of {lim['max']} m{lim['words']}"


def _largest_remainder(total: int, shares: dict[str, float]) -> dict[str, int]:
    raw = {k: total * s for k, s in shares.items()}
    out = {k: int(math.floor(v)) for k, v in raw.items()}
    left = total - sum(out.values())
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[:max(0, left)]:
        out[k] += 1
    return out


# How many storeys the floor area the manager's homes need takes, where the envelope allows more: a plate of about this
# much (a double-loaded slab some 20 m deep and 25 m long), or the setback envelope's plate box where that is smaller.
# A placeholder, declared with the suggestion's notes; the manager's own storeys stand over it.
TARGET_PLATE_M2 = 500.0


def floor_area_for_homes(units: dict[str, int], mins: dict[str, float], allowance: float, efficiency: float) -> dict[str, Any]:
    """The floor area a set of homes needs, the inverse of `unit_mix`: each home at the BC Housing minimum plus the
    design allowance, over the net efficiency, plus the ground floor's amenity and services as the layout lays them
    (layout.blocks: 1.5 m² of amenity a home, at least 40 m², and 40 m² of services). Returns {gfa_m2, net_m2,
    residential_m2, amenity_m2, services_m2, how}. Pure."""
    from .layout import LAYOUT_ASSUMPTIONS    # layout imports this module's ASSUMPTIONS, so it is imported here
    n = sum(int(v or 0) for v in units.values())
    net = sum(int(units.get(k) or 0) * float(mins[k]) * allowance for k in MIX_KEYS if k in mins)
    res = net / efficiency if efficiency else net
    per, _ = LAYOUT_ASSUMPTIONS["amenity_m2_per_unit"]
    amenity = max(40.0, per * n) if n else 0.0
    services, _ = LAYOUT_ASSUMPTIONS["services_base_m2"]
    total = round(res + amenity + services)
    how = (f"{net:,.0f} m² net at the BC Housing minimums + {int(round((allowance - 1) * 100))}%, over a net efficiency of {efficiency * 100:.0f}%, "
           f"is {res:,.0f} m², plus {amenity:,.0f} m² of amenity and {services:,.0f} m² of services")
    return {"gfa_m2": float(total), "net_m2": round(net, 1), "residential_m2": round(res, 1), "amenity_m2": amenity, "services_m2": services, "how": how}


def plans_for(counts: dict[str, int], plate_w: float, plate_d: float, storeys: int, mins: dict[str, float]) -> dict | None:
    """The layout's own solver (ffm/layout.py) on a bare massing of `storeys` plates of plate_w × plate_d m, the ground
    floor's amenity and services first, as a run lays them; a low building tried as a walk-up too. None where there is
    nothing to lay out. Pure."""
    from . import layout   # layout reads this module's ASSUMPTIONS, so it is imported here, not at the top
    n = sum(int(v or 0) for v in counts.values())
    if not (plate_w > 0 and plate_d > 0 and storeys and n):
        return None
    ring = [[0.0, 0.0], [plate_w, 0.0], [plate_w, plate_d], [0.0, plate_d]]
    m = {"origin": "", "warnings": [], "masses": [{"name": "proposed", "footprint": ring, "plate_width_m": plate_w, "plate_depth_m": plate_d,
                                                  "storeys": int(storeys), "floor_to_floor_m": ASSUMPTIONS["floor_to_floor_m"][0],
                                                  "plate_area_m2": plate_w * plate_d, "gfa_m2": plate_w * plate_d * storeys}]}
    ledger = {"results": [{"rule_id": "bch.design_guidelines.unit_areas", "check": "unit_area_flags", "status": "info",
                           "values": {"min_net_area_m2": dict(mins)}}], "run": {"as_of": "", "stamp": {"stamp": ""}}}
    return layout.solve({}, {"units": dict(counts)}, ledger, m)


def homes_placed(counts: dict[str, int], plate_w: float, plate_d: float, storeys: int, mins: dict[str, float]) -> int:
    """How many of these homes the plans place (`plans_for`); all of them where there is no plate to test. Pure."""
    L = plans_for(counts, plate_w, plate_d, storeys, mins)
    return sum(int(v or 0) for v in counts.values()) if L is None else int(L["units_placed"])


def fit_to_plans(net_area_m2: float, mins: dict[str, float], family: dict | None, allowance: float, shares: dict[str, float],
                 plate_w: float, plate_d: float, storeys: int) -> tuple[dict[str, int], float, int, int]:
    """The homes `unit_mix` gives, cut to the most the plans place on the plate (17 Nov 2026: the floor area held 170
    homes at the minimums while the plans placed 114, and the money and the funders counted all 170). Returns the
    counts, the average area, how many the floor area alone held, and how many of the counts the plans place. A search
    on the net area keeps the mix and the family-unit minimums whole. Where no count places whole (20 Nov 2026, 609
    Heatley Ave: the three-bedroom home the family minimum asks fits no floor of a 9.4 × 12 m walk-up, so every count
    fell to zero), the floor area's count is kept and the placed number says how many of it the plans hold. Pure."""
    counts, avg = unit_mix(net_area_m2, mins, family, allowance, shares)
    alone = sum(counts.values())
    placed = homes_placed(counts, plate_w, plate_d, storeys, mins) if alone else 0
    if not alone or placed >= alone:
        return counts, avg, alone, alone
    lo, hi, best = 0.0, net_area_m2, None
    for _ in range(14):
        mid = (lo + hi) / 2
        c, a = unit_mix(mid, mins, family, allowance, shares)
        k = sum(c.values())
        if k and homes_placed(c, plate_w, plate_d, storeys, mins) >= k:
            lo, best = mid, (c, a)
        else:
            hi = mid
    if best is None:
        return counts, avg, alone, placed
    return best[0], best[1], alone, sum(best[0].values())


def toa_tier(site: dict, rules: list[Rule], on: date, district: str) -> dict | None:
    """The transit-oriented area tier the site records, with the Province's minimum allowable storeys and FSR for it
    (bc.toa.minimum_density); None outside one or with no tier recorded."""
    p = _params(rules, on, "bc.toa.minimum_density", district)
    tier = str(site.get("toa_tier") or "").strip()
    if not p or site.get("in_transit_oriented_area") is not True or tier not in (p.get("tiers_storeys") or {}):
        return None
    return {"tier": tier, "storeys": int(p["tiers_storeys"][tier]), "fsr": (p.get("tiers_fsr") or {}).get(tier), "where": (p.get("tiers_where") or {}).get(tier)}


def unit_mix(net_area_m2: float, mins: dict[str, float], family: dict | None, allowance: float, shares: dict[str, float]) -> tuple[dict[str, int], float]:
    """The most units the net area holds at the minimum areas (plus the design allowance) in the starting mix,
    moved toward family units until the family-unit minimums hold. Returns the counts and the average area used."""
    avg = sum(shares[k] * mins[k] * allowance for k in shares)
    n = int(math.floor(net_area_m2 / avg)) if avg else 0
    counts = _largest_remainder(n, shares)
    if family and n:
        s2, s3 = family.get("min_two_plus_bed_share", 0), family.get("min_three_plus_bed_share") or 0
        while (counts["two_bed"] + counts["three_bed_plus"]) / n + 1e-9 < s2 and counts["one_bed"] > 0:
            counts["one_bed"] -= 1
            counts["two_bed"] += 1
        while counts["three_bed_plus"] / n + 1e-9 < s3 and counts["two_bed"] > 0:
            counts["two_bed"] -= 1
            counts["three_bed_plus"] += 1
    return counts, round(avg, 1)


def _envelope(site: dict, candidate: str, rules: list[Rule], on: date, fields: dict, unsure: list, rough: dict | None = None) -> dict[str, Any]:
    """Storeys, height, FSR and GFA for the candidate, from layer A (or B on a small lot); with neither, the rough
    envelope (`envelope_for`) fills them, each field marked basis "envelope" and citing no rule."""
    district = district_of(site)     # "CD-1 (324)" for a CD-1 site whose number is known: its own by-law's rules match
    area = float(site.get("site_area_m2") or 0)
    f2f, _ = ASSUMPTIONS["floor_to_floor_m"]
    out: dict[str, Any] = {"storeys": None, "height_m": None, "gfa_m2": None, "fsr": None}
    r_fsr = _district_rule(rules, on, "district_outright_fsr", district)
    r_h = _district_rule(rules, on, "district_outright_height", district)
    p_fsr, id_fsr = (r_fsr[1], r_fsr[0]) if r_fsr else (None, None)
    p_h, id_h = (r_h[1], r_h[0]) if r_h else (None, None)
    p_irp = _params(rules, on, "cov.irp.social_housing_rezoning", district)
    p_ssmuh = _params(rules, on, "bc.ssmuh.minimum_units", district)
    p_wood = _params(rules, on, "bch.design_guidelines.unit_areas", district) or {}
    wood_max = int(p_wood.get("wood_frame_standard_max_storeys") or 6)

    in_cv = site.get("in_former_community_vision_area")
    irp_ok = p_irp is not None and in_cv is True

    if candidate in ("benchmark", "funder-ready") and irp_ok:
        hi, bf = p_irp["benchmark_height_m_high"], p_irp["benchmark_fsr"]
        storeys = min(int(math.floor(hi / f2f)), wood_max)
        out.update({"storeys": storeys, "height_m": round(storeys * f2f, 1), "fsr": bf, "gfa_m2": round(bf * area, 0)})
        fields["storeys"] = {"value": storeys, "rule_id": "cov.irp.social_housing_rezoning", "basis": "benchmark", "note": f"the most storeys of {f2f} m inside the staff benchmark of {p_irp['benchmark_height_m_low']} to {hi} m" + (f", capped at the wood-frame standard of {wood_max}" if storeys == wood_max else "")}
        fields["height_m"] = {"value": out["height_m"], "rule_id": "cov.irp.social_housing_rezoning", "basis": "benchmark", "note": f"{storeys} storeys × {f2f} m, inside the benchmark"}
        fields["gfa_m2"] = {"value": out["gfa_m2"], "rule_id": "cov.irp.social_housing_rezoning", "basis": "benchmark", "note": f"the benchmark FSR of about {bf} × the site area {area:,.0f} m²"}
        fields["rezoning_path"] = {"value": "CD-1 under the Interim Rezoning Policy for Social Housing", "rule_id": "cov.irp.social_housing_rezoning", "basis": "benchmark", "note": "the site is inside a former Community Vision area and the option is 100% social housing"}
        return out
    if candidate in ("benchmark", "funder-ready") and not irp_ok:
        if in_cv is None and p_irp is not None:
            unsure.append({"key": "in_former_community_vision_area", "why": "whether the site is inside a former Community Vision area (Map 1 of the policy) decides whether the benchmark applies", "who": "Architect: check Map 1 for this address"})
        # fall through to outright
    max_fsr, fsr_word, floor_cap = _social_fsr(site, p_fsr) if p_fsr else (None, "", None)
    if p_fsr and p_fsr.get("housing_not_permitted"):      # an industrial schedule (M-1): the use comes before any envelope
        unsure.append({"key": "use", "why": p_fsr["housing_not_permitted"], "who": "Manager: ask a City planner whether housing is permitted here at all, before any design work"})
    if p_h and max_fsr is not None and _social_height(site, p_h)[0] is None:
        max_fsr = None
    if p_fsr and p_h and max_fsr is None:
        # the schedule's figure needs a fact the site does not carry yet (a CD-1 sub-area): said, and the rough envelope stands in
        unsure.append({"key": "cd1_sub_area" if p_fsr.get("sub_area_residential_floor_area_m2") else "odp_sub_area" if p_fsr.get("by_sub_area") else "gfa_m2", "why": f"{id_fsr}: {fsr_word}",
                       "who": "Architect: find the site on the by-law's map and record it"})
    if p_fsr and p_h and max_fsr is not None:
        # every suggestion is 100% social housing: where the schedule gives social housing its own FSR and lets the
        # Director vary the height for it (RM-4 s.3.1.1.3 and s.3.1.2.11), those are the figures, the height a variance;
        # a CD-1 that fixes a sub-area's floor area (CD-1 (324)) gives that area
        max_h, h_word = _social_height(site, p_h)
        hl = height_limit(site, SOCIAL_PROBE, p_h)
        cap_storeys = hl["storeys"] if (hl["storeys"] and max_h == hl["max"]) else None
        storeys = min(int(math.floor(max_h / f2f)), wood_max)
        if cap_storeys:
            storeys = min(storeys, int(cap_storeys))
        fsr_area = float(p_fsr.get("fsr_site_area_m2") or area)    # a CD-1 by-law can fix the site area its FSR is computed on
        gfa = round(floor_cap, 0) if floor_cap is not None else round(max_fsr * fsr_area, 0)
        plate_words = ""
        if floor_cap is not None and (rough or {}).get("gfa_m2") is not None and rough["gfa_m2"] < gfa:
            # a fixed floor area can exceed what the storeys stack on the plate (CD-1 (324) sub-area B: 23,600 m² for a
            # 91 m tower, at the wood-frame standard's 6 storeys): the plate times the storeys governs, and the note says so
            gfa = round(rough["gfa_m2"], 0)
            plate_words = f"; at {storeys} storeys the plate the yards leave holds {gfa:,.0f} m², which governs"
        out.update({"storeys": storeys, "height_m": round(min(storeys * f2f, max_h), 1), "fsr": round(gfa / area, 2) if (floor_cap is not None and area) else max_fsr, "gfa_m2": gfa})
        if street_floor_m2(site, p_fsr) and max_fsr > float(p_fsr.get("max_fsr") or 0):
            out["non_residential_gfa_m2"] = street_floor_m2(site, p_fsr)
            out["non_residential_rule"] = id_fsr
        fields["storeys"] = {"value": storeys, "rule_id": id_h, "basis": "rule", "note": f"the most storeys of {f2f} m under {h_word}" + (f", at most {cap_storeys} storeys" if cap_storeys else "")
                             + (f", capped at the wood-frame standard of {wood_max}" if storeys == wood_max and max_h > wood_max * f2f else "")}
        fields["height_m"] = {"value": out["height_m"], "rule_id": id_h, "basis": "rule", "note": f"{storeys} storeys × {f2f} m, under {h_word}"}
        fields["gfa_m2"] = {"value": gfa, "rule_id": id_fsr, "basis": "rule",
                            "note": fsr_word + plate_words if floor_cap is not None else f"{fsr_word} × the site area {fsr_area:,.0f} m²" + (" the by-law fixes for its FSR" if p_fsr.get("fsr_site_area_m2") else "")}
        fields["rezoning_path"] = {"value": None, "rule_id": id_fsr, "basis": "rule", "note": "outright: no rezoning" + ("; the height is the Director's variance for social housing, asked for with the development permit" if max_h != hl["max"] else "")}
        # a transit-oriented area's tier raises funder-ready to the height and density the City may not refuse, by a
        # rezoning under the TOA policy (17 Nov 2026: 3475 E Hastings St, tier 4 beside the Kootenay Loop, a 12-storey
        # minimum, was still offered C-2's outright 6)
        t = toa_tier(site, rules, on, district) if candidate == "funder-ready" else None
        if t and t["storeys"] > storeys:
            st = t["storeys"]
            g = round(t["fsr"] * area, 0) if t["fsr"] and area else None
            box = (rough or {}).get("plate_m2")
            held = round(box * st, 0) if box else None
            if g is None or (held is not None and held < g):
                g = held
            where = f" ({t['where']})" if t["where"] else ""
            out.update({"storeys": st, "height_m": round(st * f2f, 1), "fsr": round(g / area, 2) if g and area else t["fsr"], "gfa_m2": g})
            fields["storeys"] = {"value": st, "rule_id": "bc.toa.minimum_density", "basis": "toa",
                                 "note": f"the minimum allowable height in a tier {t['tier']} transit-oriented area{where}: {st} storeys the City may not refuse; above {district}'s outright {storeys}, by rezoning"}
            fields["height_m"] = {"value": out["height_m"], "rule_id": "bc.toa.minimum_density", "basis": "toa", "note": f"{st} storeys × {f2f} m"}
            fields["gfa_m2"] = {"value": g, "rule_id": "bc.toa.minimum_density", "basis": "toa",
                                "note": (f"the tier's minimum allowable FSR of {t['fsr']:g} × the site area {area:,.0f} m²" if t["fsr"] else f"the plate × {st} storeys")
                                        + (f"; the plate the setbacks leave holds {held:,.0f} m² at {st} storeys, which governs" if held is not None and t["fsr"] and held < t["fsr"] * area else "")}
            fields["rezoning_path"] = {"value": "CD-1 under the Transit-Oriented Areas Rezoning Policy", "rule_id": "bc.toa.minimum_density", "basis": "toa",
                                       "note": f"the site is in a tier {t['tier']} transit-oriented area; the City's TOA rezoning policy is the path above the district schedule"}
        elif candidate == "funder-ready" and site.get("in_transit_oriented_area") is True and not str(site.get("toa_tier") or "").strip():
            unsure.append({"key": "toa_tier", "why": "the site is in a transit-oriented area, and its tier sets the height and density the City may not refuse",
                           "who": "Manager: record the tier from the City's TOA map at 01"})
        return out
    if p_ssmuh and area and area < p_ssmuh["exempt_lot_min_m2"] and site.get("has_water_and_sewer") is not False and site.get("in_transit_oriented_area") is not True:
        near = site.get("frequent_bus_stop_within_400m")
        base = p_ssmuh["units_small_lot"] if area <= p_ssmuh["small_lot_max_m2"] else p_ssmuh["units_large_lot"]
        n = p_ssmuh["units_near_frequent_bus"] if (near and area >= p_ssmuh["near_bus_min_lot_m2"]) else base
        out.update({"ssmuh_units": n})
        fields["ssmuh_minimum_units"] = {"value": n, "rule_id": "bc.ssmuh.minimum_units", "note": f"at least {n} homes on a lot of {area:,.0f} m²" + ("" if near is not None else "; a frequent bus stop within 400 m would raise this to 6")}
        if near is None:
            unsure.append({"key": "frequent_bus_stop_within_400m", "why": "a prescribed frequent bus stop within 400 m raises the SSMUH minimum to six homes", "who": "Confirm the distance to the nearest prescribed frequent bus stop"})
        unsure.append({"key": "gfa_m2", "why": f"the rule stack holds no floor-area or height schedule for {district}; the SSMUH rule sets a minimum number of homes, not an envelope", "who": "Architect: read the district schedule and enter FSR and height"})
        fields["rezoning_path"] = {"value": None, "rule_id": "bc.ssmuh.minimum_units", "note": "outright under the provincial minimum"}
        return out
    # no schedule and no benchmark: the rough envelope from the setbacks and the code stands in, labelled as rough
    rough = rough or {}
    if rough.get("storeys"):
        st, h, g = rough["storeys"], rough.get("height_m"), rough.get("gfa_m2")
        out.update({"storeys": st, "height_m": h, "gfa_m2": g})
        why = rough.get("storeys_from") or ""
        fields["storeys"] = {"value": st, "rule_id": None, "basis": "envelope", "note": f"rough: {why}; not a permitted figure"}
        fields["height_m"] = {"value": h, "rule_id": None, "basis": "envelope", "note": f"rough: {st} storeys × {f2f} m; not a permitted figure"}
        if g is not None:
            fields["gfa_m2"] = {"value": g, "rule_id": None, "basis": "envelope", "note": f"rough: the plate the setbacks leave, {rough['plate_w_m']} × {rough['plate_d_m']} m, × {st} storeys; not a permitted figure"}
    unsure.append({"key": "gfa_m2", "why": (f"the rule stack holds nothing from {district}'s by-law: a CD-1 site's limits are whatever its by-law and rezoning set" if district.upper().startswith("CD-1")
                                             else f"the rule stack has no {district or 'district'} schedule")
                   + ("; the rough envelope figures (the plate the setbacks leave times the storeys) stand in until the schedule is read" if rough.get("storeys") else ""),
                   "who": "Architect: read the district schedule and enter the storeys, height and floor area it permits (the architect's Site schedule can read it with Claude)" + ("" if rough.get("storeys") else ". Left blank, the memo says the envelope was not assessed and draws no building")})
    fields["rezoning_path"] = {"value": None, "rule_id": None, "note": "not derived: enter the path the site takes"}
    return out


def suggest(site: dict, programs: list[str] | None, on: date, candidate: str = "funder-ready",
            rules: list[Rule] | None = None, rules_dir: Path = RULES_DIR, mix_shares: dict | None = None,
            fixed: dict | None = None, _compare_fronts: bool = True) -> dict[str, Any]:
    """`fixed`: the manager's own storeys, height, floor area and unit counts. The suggestion's own figures stay in
    `fields` (what the rules derive); the option takes the manager's, and everything downstream (the homes from the
    floor area, the funders' tiers, the accessible count, the below-market share) follows them."""
    mine = check_mix(mix_shares)
    fixed_given = fixed
    fixed = check_fixed(fixed)
    rules = rules if rules is not None else load_rules(rules_dir)
    programs = list(programs or [])
    district = district_of(site)     # "CD-1 (324)" for a CD-1 site whose number is known: its own by-law's rules match
    area = float(site.get("site_area_m2") or 0)
    fields: dict[str, dict] = {}
    unsure: list[dict] = []
    assumptions = [{"key": k, "value": v, "note": n} for k, (v, n) in ASSUMPTIONS.items()]
    f2f, _ = ASSUMPTIONS["floor_to_floor_m"]
    sb = setbacks_for(site)
    # a confirmed district schedule's yards replace the placeholders, and the rows cite it
    r_sb = _district_rule(rules, on, "district_setbacks", district)
    sb_rule: str | None = None
    p_sb: dict = {}
    lane = None
    if r_sb:
        sb_rule, p_sb = r_sb
        # the schedule's minimums, the rear less the distance to a lane's centre line where the schedule says so and the
        # site has a lane behind (RT-3 s.3.1.2.17)
        mins, lane = yard_minimums(site, p_sb)
        sb = {k: float(mins[k]) if mins[k] is not None else sb[k] for k in ("front", "rear", "side")}
        if lane and not lane["given"]:
            assumptions.append({"key": "lane_to_centre_line_m", "value": LANE_TO_CENTRE_LINE_M,
                                "note": f"the distance from the rear property line to the lane's ultimate centre line, taken as half a standard 6.1 m City lane for {lane['clause']}; "
                                        "a planned widening moves it, so enter the site's own figure (context.lane_to_centre_line_m) where the City gives one"})
    eff, _ = ASSUMPTIONS["net_efficiency"]
    allowance, _ = ASSUMPTIONS["design_allowance"]
    shares = mine if mine is not None else dict(ASSUMPTIONS["mix_shares"][0])
    shares_words = f"your shares ({_pct(shares)})" if mine is not None else f"the starting shares ({_pct(shares)}, a placeholder)"
    # the kind of housing the manager said at 02 (24 Nov 2026: a supportive building was derived as a family mix with 12
    # replacement trees): supportive housing is studios unless the manager set the shares
    kind = str((fixed_given or {}).get("housing_type") or "").strip().lower()      # check_fixed keeps only the figures
    if mine is None and kind == "supportive":
        shares = {"studio": 1.0, "one_bed": 0.0, "two_bed": 0.0, "three_bed_plus": 0.0}
        shares_words = "all studios, as supportive housing is laid out (a placeholder; the operator's brief decides)"
    mix_basis = "rule" if mine is not None else "placeholder"

    # which candidates the site can take
    p_irp = _params(rules, on, "cov.irp.social_housing_rezoning", district)
    has_outright = _district_rule(rules, on, "district_outright_fsr", district) is not None or _params(rules, on, "bc.ssmuh.minimum_units", district) is not None
    cands = []
    for c in CANDIDATES:
        if c["id"] == "outright":
            ok, why = has_outright, "" if has_outright else (f"{district}'s by-law is not in the rule stack" if district.upper().startswith("CD-1 (")
                                                             else f"no outright schedule for {district or 'this district'} in the rule stack")
        elif c["id"] == "benchmark":
            ok = p_irp is not None and site.get("in_former_community_vision_area") is not False
            why = "" if ok else ("no social housing rezoning policy in the rule stack for this site" if p_irp is None else
                                 "the site is outside the former Community Vision areas, so the social housing benchmark does not apply")
        else:
            # funder-ready is always available: it takes whatever envelope the site gets and answers the funders
            ok, why = True, ""
        cands.append({**c, "available": ok, "why": why})
    candidate_note = None
    known = {c["id"]: c for c in cands}
    if candidate not in known:
        candidate_note = f"there is no candidate called {candidate!r}; built funder-ready instead"
        candidate = "funder-ready"
    elif not known[candidate]["available"]:
        fallback = "funder-ready"   # always available
        candidate_note = f"{known[candidate]['title']} was not built: {known[candidate]['why']}; built {known[fallback]['title'].lower()} instead"
        candidate = fallback

    rough = envelope_for(site, rules, on, sb, sb_rule)
    env = _envelope(site, candidate, rules, on, fields, unsure, rough)
    # the candidates that would give this same building (23 Nov 2026: three choices that were one building, with
    # nothing to say so): each other available candidate's envelope is derived, and the note names the ones that match
    same = []
    for c in cands:
        if c.get("available") and c["id"] != candidate:
            e2 = _envelope(site, c["id"], rules, on, {}, [], rough)
            c["same_building"] = (e2.get("storeys"), e2.get("height_m"), e2.get("gfa_m2")) == (env.get("storeys"), env.get("height_m"), env.get("gfa_m2"))
            if c["same_building"]:
                same.append(str(c.get("title") or c["id"]))
    same_note = (f"{' and '.join(same)} would give this same building here (the same storeys, height and floor area); between them only the rent tiers and the funders' answers change"
                 if same else None)
    gfa = env.get("gfa_m2")
    storeys = env.get("storeys")
    height = env.get("height_m")
    # the manager's own figures carry the derivation from here (17 Nov 2026: 176 homes on 13,071 m² ran with rent tiers
    # and accessible units split for the 99 homes of the suggestion's own 7,612 m², and the fund "failed" on that)
    gfa = fixed.get("gfa_m2", gfa)
    storeys = fixed.get("storeys", storeys)
    height = fixed.get("height_m", height)
    # the manager's homes with no floor area of theirs: the floor area follows the homes, capped by the envelope, and the
    # storeys follow the floor area (20 Nov 2026: 20 homes kept the envelope's 8,432 m²)
    from_homes = None
    p_areas_early = _params(rules, on, "bch.design_guidelines.unit_areas", district)
    if fixed.get("units") and not fixed.get("gfa_m2") and p_areas_early and sum(fixed["units"].values()):
        from_homes = floor_area_for_homes(fixed["units"], p_areas_early["min_net_area_m2"], allowance, eff)
        cap = env.get("gfa_m2")
        basis = (fields.get("gfa_m2") or {}).get("basis")
        allows = {"rule": "the outright FSR", "benchmark": "the staff benchmark", "toa": "the transit-oriented minimum",
                  "envelope": "the rough envelope (the plate the setbacks leave)"}.get(basis, "the envelope")
        need = from_homes["gfa_m2"]
        nh = sum(fixed["units"].values())
        capped = cap is not None and need > cap + 0.5
        gfa = float(cap) if capped else need
        from_homes.update({"capped": capped, "cap_m2": cap, "cap_from": allows if cap is not None else None,
                           "words": (f"{nh} homes need about {need:,.0f} m²; {allows} allows {cap:,.0f} m²" if capped else
                                     f"{nh} homes need about {need:,.0f} m²" + (f", within the {cap:,.0f} m² {allows} allows" if cap is not None else ", and no envelope in the rules caps it"))})
        if not fixed.get("storeys"):
            env_storeys = int(storeys or 1)
            box = float((rough or {}).get("plate_m2") or 0)
            per = min(box, TARGET_PLATE_M2) if box else TARGET_PLATE_M2
            storeys = max(1, min(env_storeys, int(math.ceil(gfa / per - 1e-9))))
            if not fixed.get("height_m"):
                height = round(storeys * f2f, 1)
            from_homes["storeys"] = storeys
            from_homes["words"] += (f"; on {storeys} storey{'s' if storeys != 1 else ''}, a plate of about {gfa / storeys:,.0f} m²"
                                    + (f" (the envelope allows {env_storeys})" if storeys < env_storeys else ""))
            if storeys < env_storeys:
                st_field = fields.get("storeys") or {}
                fields["storeys"] = {**st_field, "value": storeys,
                                     "note": f"the storeys the floor area your homes need takes, on a plate of at most about {per:,.0f} m² (a placeholder); "
                                             f"the envelope allows {env_storeys}: " + str(st_field.get("note") or "")}
                fields["height_m"] = {**(fields.get("height_m") or {}), "value": height, "note": f"{storeys} storeys × {f2f} m"}
        fields["gfa_m2"] = {"value": round(gfa), "rule_id": (fields.get("gfa_m2") or {}).get("rule_id") if capped else "bch.design_guidelines.unit_areas",
                            "basis": basis if capped else "rule", "note": from_homes["words"] + f" ({from_homes['how']})"}
        if capped:
            unsure.append({"key": "gfa_m2", "why": from_homes["words"], "who": "Manager: fewer homes, smaller ones, or a path to more floor area (a rezoning)"})

    # the non-dwelling floor area the schedule's figure asks for at the street comes off the homes' floor area
    nonres = int(env.get("non_residential_gfa_m2") or 0)
    # only where the floor area is the schedule's own outright figure: a transit-area rezoning or the manager's own
    # floor area is not that clause's building
    if not gfa or nonres >= gfa or fixed.get("gfa_m2") or (fields.get("gfa_m2") or {}).get("basis") != "rule":
        nonres = 0
    res_gfa = (gfa - nonres) if gfa else gfa

    # more storeys on the same floor area make every floor smaller, and a slimmer plate places fewer homes: said, so a
    # manager who raises the storeys is not left to wonder why the homes fell (23 Nov 2026, the page's own walk)
    own_st, rule_st = fixed.get("storeys"), env.get("storeys")
    if own_st and rule_st and gfa and not fixed.get("gfa_m2") and int(own_st) > int(rule_st):
        unsure.append({"key": "storeys", "why": f"{int(own_st)} storeys on the same {gfa:,.0f} m² of floor area make each floor about {gfa / int(own_st):,.0f} m², where {int(rule_st)} storeys made it "
                                                f"{gfa / int(rule_st):,.0f} m²: a slimmer floor holds fewer homes, so the homes can fall as the storeys rise",
                       "who": "Manager: raise the floor area with the storeys (the FSR figure), or keep the storeys the rules gave"})

    # the building
    option: dict[str, Any] = {
        "id": f"{site.get('id') or 'site'}-suggested-{candidate}",
        "name": f"Suggested, {candidate}: rule-derived as of {on.isoformat()}",
        "proponent": site.get("owner") or None,
        "proponent_type": "non_profit_society",
        "developer_partner": None,
        "tenure": "social_housing",
        "rezoning_path": fields.get("rezoning_path", {}).get("value"),
        "storeys": storeys, "height_m": height, "gfa_m2": gfa,
        "residential_gfa_m2": (gfa - nonres) if gfa else gfa, "non_residential_gfa_m2": nonres if gfa else None,
        "units": {"studio": None, "one_bed": None, "two_bed": None, "three_bed_plus": None},
        "rent_tiers_units": None, "share_below_hils": None, "max_rent_share_of_income": None,
        "owner_type_at_completion": "non_profit_society", "housing_agreement_years": None,
        "accessible_units": None, "below_market_unit_share": None, "below_market_discount": None,
        "site_control": None, "parking_spaces": None, "bicycle_spaces": None,
        "replacement_trees_proposed": None, "target_programs": programs,
        "floor_to_floor_m": f2f, "setbacks_m": dict(sb),
        "notes": f"Rule-derived suggestion ({candidate}) as of {on.isoformat()}; every figure cites its rule in the run's suggestion record. Placeholders: floor to floor {f2f} m, setbacks {sb['front']}/{sb['rear']}/{sb['side']} m, net efficiency {eff}, units {int((allowance - 1) * 100)}% above the BC Housing minimums.",
        "sources": [{"title": "Derived by First Read from the rule stack in force on the as-of date", "url": ""}],
    }
    # the manager's own height and storeys set the floor to floor, so the drawings draw the height they typed
    # (17 Nov 2026: 61.6 m for 19 storeys was drawn 62.7 m, at the placeholder 3.3 m, until a buried field was found)
    if fixed.get("height_m") and fixed.get("storeys"):
        ftf = fixed["height_m"] / fixed["storeys"]
        if 2.8 <= ftf <= 4.5:
            option["floor_to_floor_m"] = round(ftf, 2)
            option["notes"] = option["notes"].replace(f"Placeholders: floor to floor {f2f} m, ", f"Floor to floor {round(ftf, 2)} m, the manager's height ÷ storeys. Placeholders: ")
    fields["proponent_type"] = {"value": "non_profit_society", "rule_id": "bch.chf.eligibility", "note": "assumed a society; change for a co-operative, a municipal provider or a First Nation"}
    fields["tenure"] = {"value": "social_housing", "rule_id": "cov.social_housing_definition", "note": "100% social housing: exempt from levies and the path the rezoning policy takes"}
    fields["floor_to_floor_m"] = {"value": f2f, "rule_id": None, "note": "placeholder"}
    for k in ("front", "rear", "side"):
        if sb_rule and p_sb.get(f"min_{k}_yard_m") is None:
            # the schedule fixes no minimum for this yard (RT-3's front: the neighbours' average): the placeholder stands
            fields[f"setbacks_m.{k}"] = {"value": sb[k], "rule_id": None, "note": f"placeholder: {sb_rule} fixes no minimum {k} yard" + ("; scaled to this lot" if sb[k] < ASSUMPTIONS["setbacks_m"][0][k] else "")}
        elif sb_rule:
            fields[f"setbacks_m.{k}"] = {"value": sb[k], "rule_id": sb_rule, "note": "the schedule's minimum yard" + (
                f": {lane['rear_yard_m']:g} m less {lane['to_centre_line_m']:g} m to the lane's centre line ({lane['clause']}"
                + ("" if lane["given"] else ", a standard lane assumed") + ")" if k == "rear" and lane else "")}
        else:
            fields[f"setbacks_m.{k}"] = {"value": sb[k], "rule_id": None, "note": "placeholder, not read from the district schedule" + ("; scaled to this lot" if sb[k] < ASSUMPTIONS["setbacks_m"][0][k] else "")}
    if nonres:
        fields["non_residential_gfa_m2"] = {"value": nonres, "rule_id": env.get("non_residential_rule"),
                                            "note": f"the non-dwelling floor area at the street the schedule's rental FSR asks for ({nonres / float(site.get('site_area_m2') or 1):.2f} FSR); shops or services, yours to program"}
        fields["residential_gfa_m2"] = {"value": res_gfa, "rule_id": None, "note": f"the floor area less the {nonres:,.0f} m² of non-dwelling space at the street"}
    else:
        fields["non_residential_gfa_m2"] = {"value": option["non_residential_gfa_m2"], "rule_id": "bc.bcbuilds.eligibility", "note": "none suggested; BC Builds caps it at 30% of the floor area"}
        fields["residential_gfa_m2"] = {"value": gfa, "rule_id": None, "note": "all of the floor area, with no non-residential space"}

    # units, from layers C and D
    p_fam = _params(rules, on, "cov.family_units", district)
    p_areas = _params(rules, on, "bch.design_guidelines.unit_areas", district)
    if gfa and p_areas:
        counts, avg = unit_mix(res_gfa * eff, p_areas["min_net_area_m2"], p_fam, allowance, shares)
        # the homes are the ones the plans place on the plate the massing draws, not only what the floor area holds;
        # counts the manager typed are theirs, and the memo says what does not fit
        fit_words = ""
        if storeys and (rough or {}).get("plate_w_m") and not fixed.get("units"):
            from .massing import plate_dims   # massing builds on the checks this module imports
            bw, bd = float(rough["plate_w_m"]), float(rough["plate_d_m"])
            pw, pd = plate_dims(min(gfa / storeys, bw * bd), bw, bd, int(storeys))
            counts, avg, alone, placed = fit_to_plans(res_gfa * eff, p_areas["min_net_area_m2"], p_fam, allowance, shares, pw, pd, int(storeys))
            kept = sum(counts.values())
            if placed < kept:
                # no count places whole: the floor area's count stands and the plan is the architect's (20 Nov 2026)
                plans = plans_for(counts, pw, pd, int(storeys), p_areas["min_net_area_m2"]) or {}
                short = [s for s in plans.get("shortfall") or [] if s.get("units")]
                short_words = ", ".join(f"{s['units']} {s['label'].lower()} ({s['area_m2'] / s['units']:,.0f} m² each)" for s in short)
                how = {"walkup": "beside one stair (a walk-up)", "point": "round a point tower's core"}.get((plans.get("plate") or {}).get("arrangement"), "along a corridor")
                fit_words = (f"; the plans place {placed} of these {kept} on {int(storeys)} floors of {pw:.1f} × {pd:.1f} m {how}, and no smaller count places whole, "
                             f"so the floor area's {kept} are kept and the plan is the architect's")
                unsure.append({"key": "plan", "why": f"the floor area holds {kept} homes at these sizes, but the plans place {placed} on {int(storeys)} floors of {pw:.1f} × {pd:.1f} m {how}"
                                                    + (f": {short_words} did not fit" if short_words else "") + f"; the {kept} homes are kept",
                               "who": "Architect: lay out the plan in Edit blocks (a larger home across two floors, a wider plate) or change the mix"})
            elif alone > kept:
                fit_words = (f"; the floor area alone holds {alone} at these sizes, the plans place {kept} on {int(storeys)} floors "
                             f"of {pw:.1f} × {pd:.1f} m, so {kept} it is")
        option["units"] = counts
        n = sum(counts.values())
        # how many homes the family-unit minimums moved up from the shares
        base = _largest_remainder(n, shares) if n else counts
        moved = sum(max(0, counts[k] - base[k]) for k in ("two_bed", "three_bed_plus"))
        moved_words = (f"; the family-unit minimums (cov.family_units) moved {moved} home{'s' if moved != 1 else ''} to more bedrooms than {'your' if mine is not None else 'the starting'} shares gave"
                       if moved else "")
        for k, v in counts.items():
            fields[f"units.{k}"] = {"value": v, "rule_id": "bch.design_guidelines.unit_areas", "basis": mix_basis,
                                    "note": f"{n} units at an average {avg} m² net ({int((allowance - 1) * 100)}% over the BC Housing minimums) in {gfa * eff:,.0f} m² net, in {shares_words}; family minimums from cov.family_units" + moved_words + fit_words}
        if p_fam and n:
            two_plus = counts["two_bed"] + counts["three_bed_plus"]
            fields["units.two_bed"]["note"] = f"{two_plus} of {n} units ({two_plus / n * 100:.0f}%) have two or more bedrooms, against the {p_fam['min_two_plus_bed_share'] * 100:.0f}% minimum, in {shares_words}" + moved_words
            if p_fam.get("min_three_plus_bed_share"):
                fields["units.three_bed_plus"]["note"] = f"{counts['three_bed_plus']} of {n} ({counts['three_bed_plus'] / n * 100:.0f}%) have three or more, against the {p_fam['min_three_plus_bed_share'] * 100:.0f}% minimum, in {shares_words}" + moved_words
    else:
        n = 0
        if env.get("ssmuh_units"):
            n = int(env["ssmuh_units"])
            counts = _largest_remainder(n, shares)
            option["units"] = counts
            for k, v in counts.items():
                fields[f"units.{k}"] = {"value": v, "rule_id": "bc.ssmuh.minimum_units", "basis": mix_basis, "note": f"{n} homes, the provincial minimum, in {shares_words}"}
    # the manager's own counts, where given, stand over the derived ones; the tiers and the accessible units below
    # are split from the total the option actually holds
    if fixed.get("units"):
        derived = option["units"]
        option["units"] = {k: fixed["units"].get(k, derived.get(k) or 0) for k in MIX_KEYS}
        n = sum(option["units"].values())

    # tenure terms, from layer C
    p_soc = _params(rules, on, "cov.social_housing_definition", district)
    if p_soc:
        option["share_below_hils"] = p_soc["min_share_below_hils"]
        option["max_rent_share_of_income"] = p_soc["max_rent_share_of_income"]
        option["housing_agreement_years"] = p_soc["min_agreement_years"]
        fields["share_below_hils"] = {"value": p_soc["min_share_below_hils"], "rule_id": "cov.social_housing_definition", "note": "the City's minimum share of units for households below the Housing Income Limits"}
        fields["max_rent_share_of_income"] = {"value": p_soc["max_rent_share_of_income"], "rule_id": "cov.social_housing_definition", "note": "the rent ceiling for those units"}
        fields["housing_agreement_years"] = {"value": p_soc["min_agreement_years"], "rule_id": "cov.social_housing_definition", "note": "the housing agreement the City secures social housing by"}
        fields["owner_type_at_completion"] = {"value": "non_profit_society", "rule_id": "cov.social_housing_definition", "note": "an eligible owner under the definition"}

    # the programs, from layer E
    p_chf = _params(rules, on, "bch.chf.eligibility", district) if "bch.chf.eligibility" in programs else None
    p_bcb = _params(rules, on, "bc.bcbuilds.eligibility", district) if "bc.bcbuilds.eligibility" in programs else None
    if candidate == "funder-ready" and n:
        if p_chf:
            tiers = _largest_remainder(n, p_chf["mix"])
            option["rent_tiers_units"] = tiers
            # whole homes cannot always split the way the fund asks: say so here, before the run says Fail (15 Nov 2026)
            off = max(abs(tiers[k] / n - p_chf["mix"][k]) for k in p_chf["mix"])
            short = off > p_chf["mix_tolerance"] + 1e-9
            from .checks import smallest_split
            least = smallest_split(p_chf["mix"], p_chf["mix_tolerance"]) if short else None
            for k, v in tiers.items():
                note = f"{p_chf['mix'][k] * 100:.0f}% of {n} units under the fund's 30 / 50 / 20 mix"
                if short:
                    note += (f"; no split of {n} homes lands within {p_chf['mix_tolerance'] * 100:.0f} points of the mix, so the fund "
                             f"will read this as short; {least} homes is the smallest count that can meet it")
                fields[f"rent_tiers_units.{k}"] = {"value": v, "rule_id": "bch.chf.eligibility", "note": note}
            if short:
                unsure.append({"key": "unit_count_for_the_mix", "why": f"{n} homes cannot split {' / '.join(f'{int(s * 100)}' for s in p_chf['mix'].values())} within the fund's tolerance; the nearest split is "
                               + " / ".join(str(tiers[k]) for k in p_chf["mix"]) + f", which the fund's check will call short",
                               "who": (f"Manager: plan at least {least} homes, or ask BC Housing whether a smaller count can be read as meeting the mix" if n < least else
                                       f"Manager: plan a number of homes that splits the mix in whole homes ({least} is the smallest; {n} does not), or ask BC Housing how it reads a split this close")})
            acc = int(math.ceil(p_chf["min_accessible_unit_share"] * n))
            option["accessible_units"] = acc
            fields["accessible_units"] = {"value": acc, "rule_id": "bch.chf.eligibility", "note": f"the fund's {p_chf['min_accessible_unit_share'] * 100:.0f}% minimum of {n} units, rounded up"}
            below = (tiers["rgi"] + tiers["deep_subsidy"]) / n
            option["share_below_hils"] = round(max(option.get("share_below_hils") or 0, below), 2)
            fields["share_below_hils"] = {"value": option["share_below_hils"], "rule_id": "bch.chf.eligibility", "note": "the rent-geared-to-income and deep-subsidy units are all below the income limits"}
        if p_bcb:
            option["below_market_unit_share"] = round((option["rent_tiers_units"]["rgi"] + option["rent_tiers_units"]["deep_subsidy"]) / n, 2) if option.get("rent_tiers_units") else p_bcb["min_below_market_unit_share"]
            option["below_market_discount"] = p_bcb["min_discount_to_market"]
            fields["below_market_unit_share"] = {"value": option["below_market_unit_share"], "rule_id": "bc.bcbuilds.eligibility", "note": "at least 20% of units; here the non-market tiers" if option.get("rent_tiers_units") else "BC Builds' minimum share of units below market"}
            fields["below_market_discount"] = {"value": option["below_market_discount"], "rule_id": "bc.bcbuilds.eligibility", "note": "BC Builds' minimum discount to market rent"}
            if option.get("proponent_type") == "non_profit_society":
                unsure.append({"key": "developer_partner", "why": "BC Builds asks a non-profit to team with a developer or builder", "who": "Manager: say whether a partner is in place"})
        if p_chf:
            unsure.append({"key": "site_control", "why": "the fund's readiness bar needs a letter of intent, a purchase agreement, a council resolution or a finalized deal", "who": "Manager: record the site control in hand"})
            tenure_plan = site.get("land_tenure_plan") or ""
            if not tenure_plan or "confirm" in tenure_plan.lower():
                unsure.append({"key": "land_tenure_plan", "why": f"the fund needs a lease of at least {p_chf['min_lease_years_nominal']} years at nominal value, or ownership", "who": "Manager and owner: settle the tenure and write it down"})
    elif candidate == "funder-ready" and not n:
        unsure.append({"key": "rent_tiers_units", "why": "no unit count was derived, so the funders' tiers cannot be split", "who": "Manager: enter the floor area or the unit count first"})

    # trees, from layer C
    p_tree = _params(rules, on, "cov.trees.replacement", district)
    if p_tree and area:
        required = _schedule_c_required(area, p_tree)
        trees = site.get("existing_trees_on_site") or []
        retained = sum(1 for t in trees if t.get("status") == "retain")
        rep = max(0, required - retained)
        option["replacement_trees_proposed"] = rep
        fields["replacement_trees_proposed"] = {"value": rep, "rule_id": "cov.trees.replacement", "note": f"Schedule C asks {required} trees on {area:,.0f} m²; {retained} retained" + ("" if trees else " (no survey on file: all are replacements until one exists)")}
        if not trees:
            unsure.append({"key": "existing_trees_on_site", "why": "no tree survey is on file; the by-law needs every tree of 20 cm or more surveyed", "who": "Architect: obtain the arborist report and survey"})

    # the schedule's yards leave no envelope on the lot as fronted (17 Nov 2026, Kai, on 609 Heatley Ave): said plainly,
    # with the other street as the front, a lane behind and the Director's variance as the ways out, in the words the
    # memo's open item uses. The front is offered, never switched: a person chooses it at 01.
    if sb_rule:
        sb_version = (_rule(rules, sb_rule).version_on(on) if _rule(rules, sb_rule) else None)
        section = ((sb_version.source if sb_version else None) or {}).get("section")
        yards = district_setbacks(site, option, {**p_sb, "_section": section} if section else p_sb)
        if (yards.get("values") or {}).get("no_envelope"):
            unsure.append({"key": "yards", "why": yards["finding"].rstrip("."), "who": yards["action"].rstrip(".")})

    # what no rule settles
    if site.get("in_transit_oriented_area") is None:
        unsure.append({"key": "in_transit_oriented_area", "why": "inside a transit-oriented area the Province sets a minimum height by tier; the City's map decides", "who": "Architect: check the City's transit-oriented areas map"})
    if district.upper().startswith("CD-1") and _district_rule(rules, on, "district_outright_fsr", district) is None:
        # a CD-1 whose by-law is in the stack is read like any district; one that is not is said plainly (17 Nov 2026)
        unsure.append({"key": "zoning_district", "why": (f"{district}'s by-law is not in the rules, and a CD-1 site's limits are whatever its by-law and rezoning set"
                                                         if district.upper() != "CD-1" else "the site's CD-1 number is not recorded, so no CD-1 by-law can be matched to it"),
                       "who": "Architect: save the site's CD-1 by-law into inbox/ to have its rules entered" if district.upper() != "CD-1"
                              else "Manager: find the address again (the lookup records the CD-1 number) or enter it on the site"})

    # A corner lot read from its other street (23 Nov 2026: Vienna House, 2001 Stainsbury Ave, held 27 homes fronting
    # Victoria Drive, the lookup's choice, and 95 fronting Stainsbury). The same suggestion is derived with the other
    # street as the front; where the homes differ by 15% or more, both counts are said and the choice goes to a person.
    fronts = None
    alt = other_front(site) if _compare_fronts else None
    if alt and n:
        streets = corner_streets(site)
        cur = next((s for s in streets if s != alt), None)
        other_site = {k: v for k, v in site.items() if k != "front_face"}
        other_site["front_street"] = alt
        if streets and alt != streets[0]:
            other_site["front_face"] = {"street": alt}
        try:
            o2 = suggest(other_site, programs, on, candidate, rules=rules, mix_shares=mix_shares, fixed=fixed_given, _compare_fronts=False)["option"]
            n2 = sum(int(v or 0) for v in (o2.get("units") or {}).values())
            fronts = [{"street": cur, "homes": n, "gfa_m2": option.get("gfa_m2"), "current": True}, {"street": alt, "homes": n2, "gfa_m2": o2.get("gfa_m2"), "current": False}]
            if n2 and abs(n2 - n) / max(n, n2) >= 0.15:
                unsure.append({"key": "front_street", "why": f"which street is the front decides the plate: fronting {cur} this suggestion holds {n} homes, fronting {alt} it holds {n2}",
                               "who": "Architect: confirm the front from the survey or the address the City lists; Manager: choose it at 01 (Which street is the front?)"})
        except (ValueError, KeyError, TypeError):
            fronts = None      # the other front cannot be drawn from the streets on file: nothing to compare

    fields["target_programs"] = {"value": programs, "rule_id": None, "note": "the programs chosen"}
    fields["id"] = {"value": option["id"], "rule_id": None, "note": "named after the site and the candidate"}
    fields["name"] = {"value": option["name"], "rule_id": None, "note": ""}

    if fields.get("storeys", {}).get("basis") == "envelope":
        fields["residential_gfa_m2"]["basis"] = "envelope"
    for f in fields.values():
        f.setdefault("basis", "rule" if f.get("rule_id") else "placeholder")

    mix = {
        "shares": dict(shares), "source": "yours" if mine is not None else "placeholder",
        "presets": {k: {"shares": dict(v["shares"]), "note": v["note"]} for k, v in MIX_PRESETS.items()},
        "unit_areas_m2": dict((p_areas or {}).get("min_net_area_m2") or {}), "allowance": allowance,
    }
    label, falls_short = says_what_it_is(candidate, option, fields, p_chf, n)
    # what the manager said of the building travels with the option: the kind of housing, the building type and a
    # tower's podium (24 Nov 2026)
    for k in ("housing_type", "building_type", "podium_storeys", "tower_plate_m2", "beds"):
        if (fixed_given or {}).get(k) not in (None, ""):
            option[k] = fixed_given[k]
    if kind == "shelter":
        option["units"] = {k: 0 for k in (option.get("units") or {})} or option.get("units")
        option["rent_tiers_units"] = None
        unsure.append({"key": "beds", "why": "a shelter is counted in beds, not homes: the derived homes are set to none", "who": "Manager: enter the beds the operator plans"})
    return {
        "candidate": candidate, "candidate_note": candidate_note, "candidates": cands, "option": option, "fields": fields,
        "unsure": unsure, "assumptions": assumptions, "envelope": rough, "mix": mix,
        "label": label, "falls_short": falls_short, "floor_area_from_homes": from_homes, "fronts": fronts, "same_building_note": same_note,
        "as_of": on.isoformat(), "stamp": stamp(rules, on, rules_dir),
    }


# What the envelope a suggestion stands on is called, by the basis its storeys came from
ENVELOPE_WORDS = {"benchmark": "Benchmark", "rule": "Outright", "toa": "Transit-oriented minimum", "envelope": "Rough envelope"}


def says_what_it_is(candidate: str, option: dict, fields: dict, p_chf: dict | None, n: int) -> tuple[str | None, str | None]:
    """Where a candidate cannot deliver what its name promises (20 Nov 2026), a plain label for what was built and a
    sentence on what it falls short of; (None, None) where it delivers. Funder-ready promises the fund's mix: below the
    smallest count that can split 30 / 50 / 20 within the tolerance (`checks.smallest_split`), or with no homes at all,
    it falls short, and the label names the envelope it stands on instead ("Outright: 3 storeys, 4 homes"). Pure."""
    if candidate != "funder-ready" or not p_chf:
        return None, None
    from .checks import smallest_split
    least = smallest_split(p_chf["mix"], p_chf["mix_tolerance"])
    if n >= least:
        return None, None
    basis = (fields.get("storeys") or {}).get("basis")
    word = ENVELOPE_WORDS.get(basis) or ("Provincial minimum" if fields.get("ssmuh_minimum_units") else "Rough envelope")
    storeys = option.get("storeys")
    label = f"{word}: " + (f"{storeys} storeys, " if storeys else "") + (f"{n} home{'s' if n != 1 else ''}" if n else "no homes derived")
    mix = " / ".join(f"{int(round(s * 100))}" for s in p_chf["mix"].values())
    falls_short = (f"Funder-ready needs at least {least} homes for the {mix} mix; this lot's envelope gives {n}" if n
                   else f"Funder-ready needs at least {least} homes for the {mix} mix; no homes were derived from this lot's envelope")
    return label, falls_short


def read_site(site: dict, on: date, rules: list[Rule] | None = None, rules_dir: Path = RULES_DIR) -> dict[str, Any]:
    """The site alone against layers A to C, before any option exists: what it allows outright, which rezoning path
    it has, its transit and tree position. Run with a bare social-housing option so the policy rules speak; nothing
    is written."""
    probe = {"id": f"{site.get('id') or 'site'}-read", "name": "Reading the site", "tenure": "social_housing", "target_programs": []}
    L = evaluate(site, probe, on, rules=rules, rules_dir=rules_dir)
    keep = [r for r in L["results"] if r["layer"] in ("A", "B", "C") and r["status"] != "not_applicable"]
    return {"as_of": on.isoformat(), "stamp": L["run"]["stamp"], "results": keep, "site": site}
