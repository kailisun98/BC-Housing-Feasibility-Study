"""Deterministic checks. Each takes (site, option, params) and returns a dict:

    status   one of pass, conditional, fail, uncertain, not_applicable, info
    finding  one sentence with the arithmetic shown
    values   the numbers used, so the memo and the massing can cite them
    action   what a person must do next, if anything (empty for pass/info)

No model is involved here. Same inputs, same output, every run.
"""

from __future__ import annotations

import re
from typing import Any, Callable

Site = dict[str, Any]
Option = dict[str, Any]
Params = dict[str, Any]
Result = dict[str, Any]

PASS, COND, FAIL, UNSURE, NA, INFO = "pass", "conditional", "fail", "uncertain", "not_applicable", "info"


def _r(status: str, finding: str, values: dict | None = None, action: str = "") -> Result:
    return {"status": status, "finding": finding, "values": values or {}, "action": action}


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _units_total(option: Option) -> int:
    u = option.get("units") or {}
    return int(sum(v for v in u.values() if v))


def smallest_split(mix: dict[str, float], tolerance: float, limit: int = 400) -> int:
    """The smallest unit count that some whole-number split lands within the tolerance of the mix (every tier at
    once): 10 for 30/50/20 at 2%. Pure; used by the fit check and by the suggestion so both say the same thing."""
    for n in range(1, limit + 1):
        if all(abs(round(n * s) / n - s) <= tolerance + 1e-9 for s in mix.values()) and sum(round(n * s) for s in mix.values()) == n:
            return n
    return limit


_smallest_split = smallest_split


def fsr(site: Site, option: Option) -> float | None:
    if site.get("site_area_m2") and option.get("gfa_m2"):
        return option["gfa_m2"] / site["site_area_m2"]
    return None


# ---------------------------------------------------------------- Layer A: zoning district

# What a district schedule permits depends on more than the district (17 Nov 2026, the schedules Kai saved): the
# tenure (RM-4, RM-3A: 3.00 for 100% social housing; C-2: 3.50 for a building with every home rental), the site's size
# and shape (RR-1, RR-2A/2B: a table by site area, depth and a corner's frontage), the Director's discretion (RM-5:
# up to 2.75, a conditional approval), formula increases (RM-3: by site coverage and parking) and, in a CD-1, a floor
# area fixed per sub-area (CD-1 (324)). `fsr_limit` and `height_limit` read all of it once, for the checks below and
# the suggester alike. A row of a table names the site conditions it needs; the most it allows is taken.
SOCIAL = "social_housing"
RENTAL_TENURES = ("social_housing", "secured_market_rental")


def _is_corner(site: Site) -> bool:
    return bool(site.get("corner_lot")) or bool(corner_streets(site))


def _row_fits(site: Site, option: Option, row: dict) -> bool:
    """A table row's conditions on the site (and, where it says so, the tenure)."""
    area = float(site.get("site_area_m2") or 0)
    W, D = lot_as_fronted(site)
    if row.get("min_site_area_m2") and area + 1e-9 < row["min_site_area_m2"]:
        return False
    if row.get("max_site_area_m2") and area > row["max_site_area_m2"] + 1e-9:
        return False
    if row.get("max_site_depth_m") and not (D and D <= row["max_site_depth_m"] + 1e-9):
        return False
    if row.get("min_frontage_m") and not (W and W + 1e-9 >= row["min_frontage_m"]):
        return False
    if row.get("max_frontage_m") and W > row["max_frontage_m"] + 1e-9:
        return False
    if row.get("corner") and not _is_corner(site):
        return False
    if row.get("social_housing") and option.get("tenure") != SOCIAL:
        return False
    if row.get("rental") and option.get("tenure") not in RENTAL_TENURES:
        return False
    # a row for "all other sites" (RR-2B s.3.1.1.6) excludes the sites another row names
    if any(_row_fits(site, option, u) for u in row.get("unless") or []):
        return False
    return True


def _best_row(site: Site, option: Option, rows: list[dict], key: str) -> dict | None:
    fits = [r for r in rows if r.get(key) is not None and _row_fits(site, option, r)]
    return max(fits, key=lambda r: r[key]) if fits else None


def fsr_limit(site: Site, option: Option, p: Params) -> dict[str, Any]:
    """The FSR a schedule's rule allows this site and option: `max` the most allowed without discretion (None where the
    site meets no row of the schedule's table), `words` how the schedule gets there, `discretionary` what the Director
    may allow above it and its clause, `increases` formula increases not computed here, `floor_area_cap` a CD-1's fixed
    floor area in m² (its `max` is then that area over the site), `short` why no figure applies."""
    tenure = option.get("tenure")
    out: dict[str, Any] = {"max": p.get("max_fsr"), "base": p.get("max_fsr"), "words": "", "discretionary": None, "discretionary_clause": None,
                           "increases": p.get("fsr_increases"), "floor_area_cap": None, "short": None}
    if p.get("fsr_table"):
        row = _best_row(site, option, p["fsr_table"], "max_fsr")
        if row is None:
            out.update({"max": None, "short": p.get("fsr_table_short") or "the site meets none of the schedule's rows (its area, depth or frontage is short)"})
            return out
        out.update({"max": row["max_fsr"], "words": f" for {row['label']}" if row.get("label") else ""})
    if p.get("sub_area_residential_floor_area_m2"):
        sub = str(site.get("cd1_sub_area") or "").strip().upper()
        cap = (p["sub_area_residential_floor_area_m2"] or {}).get(sub)
        if cap is None:
            caps = ", ".join(f"{k} {v:,.0f} m²" for k, v in p["sub_area_residential_floor_area_m2"].items())
            out.update({"max": None, "short": f"the by-law fixes the residential floor area by sub-area ({caps}) and the site's sub-area (cd1_sub_area) is not recorded"})
            return out
        area = float(p.get("fsr_site_area_m2") or site.get("site_area_m2") or 0)
        out.update({"floor_area_cap": float(cap), "sub_area": sub, "max": round(cap / area, 2) if area else None,
                    "words": f" (sub-area {sub}'s {cap:,.0f} m² of residential floor area)"})
    best = out["max"]
    if tenure in RENTAL_TENURES and p.get("max_fsr_rental") and (best is None or p["max_fsr_rental"] > best):
        r = p["max_fsr_rental"]
        if p.get("max_fsr_rental_corner") and _row_fits(site, option, p["max_fsr_rental_corner"]):
            r = max(r, p["max_fsr_rental_corner"]["max_fsr"])
        out.update({"max": r, "words": f" for a building with every home secured as rental ({p.get('rental_fsr_clause') or 'the schedule'}; {out['base']} otherwise)"})
    if tenure == SOCIAL and p.get("max_fsr_social_housing") and (out["max"] is None or p["max_fsr_social_housing"] > out["max"]):
        out.update({"max": p["max_fsr_social_housing"], "words": f" for 100% social housing ({p.get('social_housing_fsr_clause') or 'the schedule'}; {out['base']} otherwise)"})
    disc = p.get("max_fsr_discretionary")
    # the Director's increase can be open only to some sites (RR-3 s.3.1.1.4: a corner with 40.2 m and 1,470 m²)
    if disc and p.get("fsr_discretionary_when") and not _row_fits(site, option, p["fsr_discretionary_when"]):
        disc = None
    if disc:
        clause = p.get("fsr_discretionary_clause") or "the schedule"
        narrow = p.get("narrow_site")
        W, _ = lot_as_fronted(site)
        if narrow and W and W <= narrow["max_width_m"] + 1e-9:
            corner_ok = _is_corner(site) and float(site.get("site_area_m2") or 0) >= narrow.get("corner_min_site_area_m2", 0)
            cap = narrow["corner_max_fsr"] if corner_ok else narrow["max_fsr"]
            if cap < disc:
                disc, clause = cap, f"{clause}, at most {cap} on a site {narrow['max_width_m']} m wide or less ({narrow['clause']})"
        if out["max"] is None or disc > out["max"]:
            out.update({"discretionary": disc, "discretionary_clause": clause})
    return out


def height_limit(site: Site, option: Option, p: Params) -> dict[str, Any]:
    """The height a schedule's rule allows: `max` and `storeys` without discretion (tenure, a transit-oriented area and
    the site's row of a table counted), `words`, and `discretionary` with its clause and whether it is for social
    housing only (RM-4 s.3.1.2.11) or for any building (RM-5 s.3.1.2.7)."""
    tenure = option.get("tenure")
    out: dict[str, Any] = {"max": p.get("max_height_m"), "storeys": p.get("max_storeys"), "base": p.get("max_height_m"), "words": "",
                           "discretionary": None, "discretionary_clause": None, "discretionary_social": False}
    if p.get("height_table"):
        row = _best_row(site, option, p["height_table"], "max_height_m")
        if row is not None:
            out.update({"max": row["max_height_m"], "storeys": row.get("max_storeys"), "words": f" for {row['label']}" if row.get("label") else ""})

    def lift(h, storeys, words):
        if h and (out["max"] is None or h > out["max"]):
            out.update({"max": h, "storeys": storeys, "words": words})

    if tenure in RENTAL_TENURES:
        lift(p.get("max_height_m_rental"), p.get("max_storeys_rental"),
             f" for a building with every home secured as rental ({p.get('rental_height_clause') or 'the schedule'}; {out['base']} m otherwise)")
    if tenure == SOCIAL:
        lift(p.get("max_height_m_social_housing"), p.get("max_storeys_social_housing"),
             f" for social housing ({p.get('social_housing_height_clause') or 'the schedule'}; {out['base']} m otherwise)")
    if site.get("in_transit_oriented_area") is True:
        lift(p.get("max_height_m_toa"), p.get("max_storeys_toa") or out["storeys"],
             f" in a transit-oriented area ({p.get('toa_height_clause') or 'the schedule'}; {out['base']} m otherwise)")
    var = p.get("max_height_m_social_housing_variance")
    if var and tenure == SOCIAL and (out["max"] is None or var > out["max"]):
        out.update({"discretionary": var, "discretionary_clause": p.get("social_housing_height_clause") or "the schedule", "discretionary_social": True})
    disc = p.get("max_height_m_discretionary")
    if disc and (out["max"] is None or disc > out["max"]) and (out["discretionary"] is None or disc > out["discretionary"]):
        out.update({"discretionary": disc, "discretionary_clause": p.get("height_discretionary_clause") or "the schedule", "discretionary_social": False})
    return out


def district_outright_fsr(site, option, p) -> Result:
    tenure = option.get("tenure")
    # a schedule that houses only rental (RR districts): any other tenure is not permitted, whatever its size
    if p.get("rental_only") and tenure not in RENTAL_TENURES:
        return _r(FAIL, f"Every home in this district must be secured as residential rental tenure ({p.get('rental_only_clause') or 'the schedule'}); "
                  f"this option's tenure is {str(tenure or 'not stated').replace('_', ' ')}.", {"tenure": tenure},
                  action="Choose social housing or secured rental, or a site in another district.")
    lim = fsr_limit(site, option, p)
    # a CD-1 by-law can fix the site area its FSR is computed on (CD-1 (819) s.5.1: the site before dedications)
    fixed = p.get("fsr_site_area_m2")
    area = fixed or site.get("site_area_m2")
    gfa = option.get("gfa_m2")
    if lim["floor_area_cap"] is not None:
        gfa = option.get("residential_gfa_m2") or gfa     # the by-law caps residential floor area
    f = gfa / area if (area and gfa) else None
    if lim["short"]:
        return _r(UNSURE, f"No floor space ratio applies yet: {lim['short']}.", {"fsr": round(f, 3) if f else None},
                  action="Architect: check the site against the schedule's site-size rows, or record what is missing.")
    if f is None:
        return _r(UNSURE, "Floor space ratio cannot be computed: site area or gross floor area missing.",
                  action="Enter the site area and the option's gross floor area.")
    mx = lim["max"]
    vals = {"fsr": round(f, 3), "max_fsr_outright": mx, "gfa_m2": gfa, "site_area_m2": area}
    over = f"{gfa:,.0f} m² over {area:,.1f} m²" + (", the site area the by-law fixes for its FSR" if fixed else "")
    if fixed:
        vals["fsr_site_area_fixed"] = True
    if mx != lim["base"] and lim["base"] is not None:
        vals["max_fsr_base"] = lim["base"]
    if lim["floor_area_cap"] is not None:
        vals["max_floor_area_m2"] = lim["floor_area_cap"]
    # a schedule's cap on the number of homes (R1-1 s.3.1.1.3: 8 when all are rental, else 6)
    units = _units_total(option)
    cap_units = (p.get("max_dwelling_units_rental") if tenure in RENTAL_TENURES else None) or p.get("max_dwelling_units")
    if cap_units and units > cap_units:
        vals["max_dwelling_units"] = cap_units
        return _r(FAIL if not option.get("rezoning_path") else UNSURE,
                  f"{units} homes exceed the schedule's {cap_units} for this form ({p.get('dwelling_units_clause') or 'the schedule'}); a larger building needs another district or a rezoning.",
                  vals, action="Reduce the homes to the schedule's cap or state a rezoning path.")
    # compared at two decimals, the precision a schedule and a referral report state an FSR to (Kai, 17 Nov 2026):
    # 14,729 m² on CD-1 (819)'s 2,134.4 m² is 6.9008, which the report gives as 6.90 against a maximum of 6.90
    if lim["floor_area_cap"] is not None and gfa <= lim["floor_area_cap"] + 1e-6:
        return _r(PASS, f"Residential floor area {gfa:,.0f} m² is within sub-area {lim['sub_area']}'s {lim['floor_area_cap']:,.0f} m², the most the by-law allows there (FSR {f:.2f} on {area:,.1f} m²).", vals)
    if lim["floor_area_cap"] is None and round(f, 2) <= mx:
        return _r(PASS, f"FSR {f:.2f} ({over}) is within the outright maximum of {mx}{lim['words']}.", vals)
    fs = f"{f:.2f}"
    said = f"the outright maximum of {mx}{lim['words']}"
    subject = f"FSR {fs}"
    if lim["floor_area_cap"] is not None:     # a by-law that fixes the floor area is read in m², not as an FSR
        subject = f"Residential floor area {gfa:,.0f} m²"
        said = f"sub-area {lim['sub_area']}'s {lim['floor_area_cap']:,.0f} m², the most the by-law allows there"
    if lim["discretionary"] and round(f, 2) <= lim["discretionary"]:
        vals["max_fsr_discretionary"] = lim["discretionary"]
        return _r(COND, f"{subject} exceeds {said}; the Director of Planning may increase it to at most {lim['discretionary']} ({lim['discretionary_clause']}), a discretionary approval, not assumed.",
                  vals, action=f"Architect: make the case for the increase under {lim['discretionary_clause']} with the development permit application.")
    if lim["increases"] and not option.get("rezoning_path"):
        return _r(UNSURE, f"{subject} exceeds the base of {mx}; the schedule's increases ({lim['increases']}) may reach it, and they are not computed here.",
                  vals, action="Architect: work out the schedule's increases for this site's coverage, area and parking, and enter the result as the option's floor area.")
    if option.get("rezoning_path"):
        return _r(UNSURE, f"{subject} exceeds {said}; it can proceed only by rezoning ({option['rezoning_path']}), where density is negotiated.",
                  vals, action="Architect and manager: confirm the rezoning path and the density staff will support.")
    return _r(FAIL, f"{subject} exceeds {said} and no rezoning path is stated.", vals,
              action="Reduce the floor area or state a rezoning path.")


def district_outright_height(site, option, p) -> Result:
    h = option.get("height_m")
    if h is None:
        return _r(UNSURE, "Height missing.", action="Enter the proposed height to the roof parapet in metres.")
    lim = height_limit(site, option, p)
    mx, ms = lim["max"], lim["storeys"]
    st = option.get("storeys")
    vals = {"height_m": h, "max_height_m_outright": mx, "storeys": st}
    if ms:
        vals["max_storeys_outright"] = ms
    if mx != lim["base"]:
        vals["max_height_m_base"] = lim["base"]
    limit_words = f"{mx} m" + (f" and {ms} storeys" if ms else "") + lim["words"]
    over_storeys = bool(ms and st and st > ms)
    if h <= mx and not over_storeys:
        return _r(PASS, f"Height {h} m{f', {st} storeys,' if (ms and st) else ''} is within the outright maximum of {limit_words}.", vals)
    what = f"Height {h} m" + (f" and {st} storeys" if over_storeys else "")
    verb = "exceed" if over_storeys else "exceeds"
    # the Director of Planning's discretion to vary the height (RM-4 s.3.1.2.11: up to 19.9 m for 100% social housing;
    # RM-5 s.3.1.2.7: up to 58.0 m for any building): a conditional approval to ask for, never assumed
    var = lim["discretionary"]
    if var and h <= var:
        clause = lim["discretionary_clause"]
        vals["max_height_m_variance"] = var
        return _r(COND, f"{what} {verb} the outright maximum of {limit_words}; " + ("for 100% social housing " if lim["discretionary_social"] else "")
                  + f"the Director of Planning may vary it to at most {var} m ({clause}), a discretionary approval, not assumed.",
                  vals, action=f"Architect: ask for the height variance under {clause} with the development permit application.")
    if option.get("rezoning_path"):
        return _r(UNSURE, f"{what} {verb} the outright maximum of {limit_words}; it can proceed only by rezoning ({option['rezoning_path']}), where height is negotiated.",
                  vals, action="Architect: confirm the height staff will support under the policy.")
    return _r(FAIL, f"{what} {verb} the outright maximum of {limit_words} and no rezoning path is stated.", vals,
              action="Reduce the height or state a rezoning path.")


def rezoning_policy_social_housing(site, option, p) -> Result:
    if option.get("tenure") != "social_housing":
        return _r(NA, "The interim rezoning policy applies to 100% social housing; this option is not social housing.")
    inside = site.get("in_former_community_vision_area")
    if inside is None:
        return _r(UNSURE, "Whether the site is inside a former Community Vision area (Map 1 of the policy) is not confirmed.",
                  action="Architect: check Map 1 of the policy for this address.")
    if not inside:
        return _r(NA, "The site is outside the former Community Vision areas; social housing there is considered under the Affordable Housing Policies (1989) or an area plan.")
    h, f = option.get("height_m"), fsr(site, option)
    lo, hi, bf = p["benchmark_height_m_low"], p["benchmark_height_m_high"], p["benchmark_fsr"]
    note = []
    if h is not None and h > hi:
        note.append(f"height {h} m is above the staff benchmark of {lo} to {hi} m")
    if f is not None and f > bf:
        note.append(f"FSR {f:.2f} is at or above the benchmark of about {bf}")
    vals = {"benchmark_height_m": [lo, hi], "benchmark_fsr": bf, "height_m": h, "fsr": round(f, 3) if f else None}
    if note:
        return _r(COND, "Eligible for consideration as 100% social housing under the policy; " + "; ".join(note) + ". The policy sets no maximum, so the number is negotiated with staff.",
                  vals, action="Manager and architect: expect staff to test the scheme against the RM-4 benchmark; prepare the shadow and daylight case.")
    return _r(PASS, "Eligible for consideration as 100% social housing under the policy, within the staff benchmark.", vals)


def parking_minimums(site, option, p) -> Result:
    # a count not given is said so, not printed as None (17 Nov 2026: "the option provides None vehicle and None
    # bicycle spaces"; the key is present and null in a derived option, so get()'s default never applied)
    car, bike = option.get("parking_spaces"), option.get("bicycle_spaces")
    given = [f"{x} {what}" for x, what in ((car, "vehicle"), (bike, "bicycle")) if x is not None]
    provides = f"the option provides {' and '.join(given)} spaces" if given else "the option gives no parking count"
    return _r(INFO, f"No minimum off-street parking applies citywide since June 2024; {provides}. Bicycle spaces are set by the Parking By-law at the development permit stage.",
              {"parking_spaces": car, "bicycle_spaces": bike})


# ---------------------------------------------------------------- Layer B: provincial overrides

def ssmuh_minimum_units(site, option, p) -> Result:
    district = (site.get("zoning_district") or "").upper()
    area = site.get("site_area_m2")
    if area is None:
        return _r(UNSURE, "Lot area missing.", action="Enter the lot area.")
    if area >= p["exempt_lot_min_m2"]:
        return _r(NA, f"Lot of {area:,.0f} m² is at or above {p['exempt_lot_min_m2']:,} m²; SSMUH does not apply.", {"site_area_m2": area})
    if site.get("has_water_and_sewer") is False:
        return _r(NA, "Lot has no water or sewer service; SSMUH does not apply.")
    if site.get("in_transit_oriented_area") is True:
        return _r(NA, "The lot is inside a transit-oriented area, where the TOA rules prevail over SSMUH.")
    near = site.get("frequent_bus_stop_within_400m")
    if area <= p["small_lot_max_m2"]:
        base = p["units_small_lot"]
    else:
        base = p["units_large_lot"]
    vals = {"site_area_m2": area, "district": district, "base_units": base, "near_frequent_bus_stop": near}
    if near is None:
        return _r(UNSURE, f"At least {base} homes are permitted by lot size ({area:,.0f} m²); whether a prescribed frequent bus stop lies within {p['frequent_bus_distance_m']} m, which would raise this to {p['units_near_frequent_bus']}, is not confirmed.",
                  vals, action="Confirm the distance to the nearest prescribed frequent bus stop.")
    if near and area >= p["near_bus_min_lot_m2"]:
        vals["minimum_units"] = p["units_near_frequent_bus"]
        return _r(INFO, f"At least {p['units_near_frequent_bus']} homes must be permitted: lot {area:,.0f} m² within {p['frequent_bus_distance_m']} m of a frequent bus stop; no off-street parking minimum applies.", vals)
    vals["minimum_units"] = base
    return _r(INFO, f"At least {base} homes must be permitted on a lot of {area:,.0f} m².", vals)


def toa_status(site, option, p) -> Result:
    inside = site.get("in_transit_oriented_area")
    if inside is None:
        return _r(UNSURE, "Whether the site lies in one of Vancouver's 29 transit-oriented areas is not confirmed.",
                  action="Architect: check the City's transit-oriented areas map and record the tier.")
    if not inside:
        return _r(NA, "The site is outside the transit-oriented areas; no provincial minimum height applies.")
    tier = str(site.get("toa_tier") or "")
    floors = p["tiers_storeys"].get(tier)
    if floors is None:
        return _r(UNSURE, "The site is in a transit-oriented area but the tier is not recorded.", action="Manager: record the TOA tier from the City's map.")
    st = option.get("storeys")
    where = (p.get("tiers_where") or {}).get(tier)
    fsr = (p.get("tiers_fsr") or {}).get(tier)
    vals = {"toa_tier": tier, "minimum_allowable_storeys": floors, "minimum_allowable_fsr": fsr, "storeys": st}
    return _r(INFO, f"Tier {tier}{f' ({where})' if where else ''}: the City may not refuse at least {floors} storeys"
                    + (f" and an FSR of {fsr:g}" if fsr else "") + f" for this parcel; the option proposes {st if st is not None else 'no storey count'}.", vals)


# ---------------------------------------------------------------- Layer C: City policies

# Area plans that carry their own family-unit target, by the value of `site.area_plan`. A rule whose params name
# one (`area_plan`) applies only inside it; the city-wide rule (no `area_plan` param) steps aside there. Keep this
# in step with the rules in rules/c_city_policies.json that carry an `area_plan` param.
AREA_PLAN_FAMILY_TARGETS = {"downtown_eastside": "Downtown Eastside Plan"}


def family_unit_share(site, option, p) -> Result:
    plan, site_plan = p.get("area_plan"), (site or {}).get("area_plan")
    if plan:
        if site_plan != plan:
            return _r(NA, f"The site is not recorded inside the {AREA_PLAN_FAMILY_TARGETS.get(plan, plan)} area (site.area_plan); the city-wide family-unit rule applies.")
    elif site_plan in AREA_PLAN_FAMILY_TARGETS:
        return _r(NA, f"The site is inside the {AREA_PLAN_FAMILY_TARGETS[site_plan]} area, whose own family-unit target applies in place of the city-wide one.")
    u = option.get("units") or {}
    all_units = total = _units_total(option)
    if total == 0:
        return _r(UNSURE, "Unit mix missing.", action="Enter the unit counts by bedroom type.")
    two_plus = int(u.get("two_bed", 0) or 0) + int(u.get("three_bed_plus", 0) or 0)
    three_plus = int(u.get("three_bed_plus", 0) or 0)
    left_out = ""
    if p.get("exclude_supportive_units"):
        supportive = int(option.get("supportive_units") or 0)
        if 0 < supportive < total:
            total -= supportive
            left_out = f"; the {supportive} supportive homes are left out of the count, as the plan allows ({two_plus} of all {all_units} is {_pct(two_plus / all_units)})"
        elif option.get("supportive_units") is None:
            left_out = "; supportive homes are not stated on the option, so every home is counted (the plan leaves seniors and supportive housing out)"
    s2, s3 = two_plus / total, three_plus / total
    vals = {"units_total": total, "two_plus_bed_units": two_plus, "two_plus_bed_share": round(s2, 4),
            "three_plus_bed_units": three_plus, "three_plus_bed_share": round(s3, 4),
            "min_two_plus_bed_share": p["min_two_plus_bed_share"], "min_three_plus_bed_share": p.get("min_three_plus_bed_share")}
    if left_out:
        vals["units_all"] = all_units
        vals["two_plus_bed_share_of_all"] = round(two_plus / all_units, 4)
    parts, ok = [], True
    if s2 + 1e-9 >= p["min_two_plus_bed_share"]:
        parts.append(f"{two_plus} of {total} units ({_pct(s2)}) have two or more bedrooms, against a {_pct(p['min_two_plus_bed_share'])} minimum")
    else:
        ok = False
        parts.append(f"only {two_plus} of {total} units ({_pct(s2)}) have two or more bedrooms, below the {_pct(p['min_two_plus_bed_share'])} minimum")
    m3 = p.get("min_three_plus_bed_share")
    if m3 is not None:
        if s3 + 1e-9 >= m3:
            parts.append(f"{three_plus} ({_pct(s3)}) have three or more, against a {_pct(m3)} minimum")
        else:
            ok = False
            parts.append(f"only {three_plus} ({_pct(s3)}) have three or more, below the {_pct(m3)} minimum")
    finding = "; ".join(parts) + left_out + "."
    if ok:
        return _r(PASS, finding[0].upper() + finding[1:], vals)
    return _r(FAIL, finding[0].upper() + finding[1:], vals, action="Change the unit mix: add family units until both minimums are met.")


def social_housing_definition(site, option, p) -> Result:
    if option.get("tenure") != "social_housing":
        return _r(NA, "This option is not social housing; the definition does not apply.")
    issues, unknown = [], []
    share = option.get("share_below_hils")
    if share is None:
        unknown.append("share of units for households below the Housing Income Limits")
    elif share + 1e-9 < p["min_share_below_hils"]:
        issues.append(f"{_pct(share)} of units for households below HILs is under the {_pct(p['min_share_below_hils'])} minimum")
    owner = option.get("owner_type_at_completion")
    if owner is None:
        unknown.append("owner at completion")
    elif owner not in p["eligible_owner_types"]:
        issues.append(f"owner type '{owner}' is not a non-profit, co-op or government")
    yrs = option.get("housing_agreement_years")
    if yrs is None:
        unknown.append("housing agreement term")
    elif yrs < p["min_agreement_years"]:
        issues.append(f"housing agreement of {yrs} years is under the {p['min_agreement_years']}-year minimum")
    vals = {"share_below_hils": share, "owner_type_at_completion": owner, "housing_agreement_years": yrs}
    if issues:
        return _r(FAIL, "Does not meet the City's social housing definition: " + "; ".join(issues) + ".", vals, action="Revise the tenure terms.")
    if unknown:
        return _r(UNSURE, "Social housing definition cannot be confirmed: missing " + ", ".join(unknown) + ".", vals,
                  action="Manager: supply " + ", ".join(unknown) + ".")
    return _r(PASS, f"Meets the City's social housing definition: {_pct(share)} of units for households below HILs (minimum {_pct(p['min_share_below_hils'])}), owned by a {owner.replace('_', ' ')}, secured for {yrs} years.", vals)


def below_market_rental_policy(site, option, p) -> Result:
    if option.get("tenure") == "social_housing":
        return _r(NA, "The below-market rental policy applies to 100% secured market rental rezonings; social housing is governed by the social housing definition instead.")
    if option.get("tenure") != "secured_market_rental":
        return _r(NA, "Applies only to 100% secured rental rezonings.")
    share, disc = option.get("below_market_floor_area_share"), option.get("below_market_discount")
    if share is None or disc is None:
        return _r(UNSURE, "Below-market floor area share or rent discount not stated.", action="Manager: state the share of floor area and the discount to CMHC average rent.")
    vals = {"below_market_floor_area_share": share, "below_market_discount": disc}
    if share + 1e-9 >= p["min_below_market_floor_area_share"] and disc + 1e-9 >= p["min_discount_to_cmhc_average"]:
        return _r(PASS, f"{_pct(share)} of floor area at {_pct(disc)} below CMHC average rent meets the 20% at 20% policy; a {p['covenant_years']}-year covenant applies.", vals)
    return _r(FAIL, f"{_pct(share)} of floor area at {_pct(disc)} below CMHC average rent does not meet the 20% at 20% policy.", vals, action="Increase the below-market share or the discount.")


def _schedule_c_required(area: float, p: Params) -> int:
    for lo, hi, n in p["schedule_c_min_trees_by_site_area_m2"]:
        if lo <= area <= hi:
            return n
    if area > 3250:
        extra = int((area - 3250) // p["over_3250_extra_tree_per_m2"])
        return p["over_3250_base_trees"] + extra
    return p["schedule_c_min_trees_by_site_area_m2"][0][2]


def _schedule_a_barrier(dbh_cm: float, p: Params) -> float:
    table = p["schedule_a_barrier_m_by_dbh_cm"]
    for d, m in table:
        if dbh_cm <= d:
            return m
    return table[-1][1]


def tree_replacement(site, option, p) -> Result:
    area = site.get("site_area_m2")
    if area is None:
        return _r(UNSURE, "Site area missing.", action="Enter the site area.")
    required = _schedule_c_required(area, p)
    trees = site.get("existing_trees_on_site") or []
    retained = [t for t in trees if t.get("status") == "retain"]
    removed = [t for t in trees if t.get("status") == "remove"]
    proposed = int(option.get("replacement_trees_proposed") or 0)
    after = len(retained) + proposed
    shortfall = max(0, required - after)
    cash = shortfall * p["cash_in_lieu_per_tree_cad"]
    barriers = []
    for t in retained:
        if t.get("dbh_cm"):
            barriers.append({"tree": t.get("id"), "dbh_cm": t["dbh_cm"], "barrier_m": _schedule_a_barrier(t["dbh_cm"], p)})
    vals = {"site_area_m2": area, "schedule_c_required": required, "existing": len(trees), "retained": len(retained),
            "removed": len(removed), "replacements_proposed": proposed, "trees_after": after, "shortfall": shortfall,
            "cash_in_lieu_cad": cash, "protection_barriers": barriers, "survey_scope": p["survey_scope"]}
    if not trees:
        return _r(UNSURE, f"Schedule C requires {required} trees on a {area:,.0f} m² site; no tree survey is on file.",
                  vals, action="Architect: obtain the arborist report and survey (" + p["survey_scope"] + ").")
    base = (f"Schedule C requires {required} trees on {area:,.0f} m²; the option keeps {len(retained)} of {len(trees)} and plants {proposed}, "
            f"leaving {after}")
    if shortfall == 0:
        return _r(PASS, base + ", which meets the minimum.", vals)
    return _r(COND, base + f", a shortfall of {shortfall}: plant {shortfall} more at the by-law setbacks or pay ${cash:,.0f} cash in lieu; the final count is set at the development permit.",
              vals, action="Architect: find room for the missing trees (1 m from side lines, 1.5 m from the building, 2.5 m apart) or budget the cash in lieu.")


def dcl_cac(site, option, p) -> Result:
    if option.get("tenure") == "social_housing":
        church = "church" in str(site.get("owner_type") or "").lower() or "church" in str(site.get("owner") or "").lower()
        return _r(INFO, "Social housing is exempt from development cost levies and from community amenity contributions in a rezoning"
                  + ("; the existing church use is also DCL-exempt" if church else "") + ". The exemption's value is worth stating in the memo.",
                  {"dcl_exempt": True, "cac_exempt": True})
    return _r(INFO, "Development cost levies apply at the City's current rates; confirm the rate schedule before the pro forma.", {"dcl_exempt": False})


# ---------------------------------------------------------------- Layer D: code and design standards (flags)

def unit_area_flags(site, option, p) -> Result:
    total = _units_total(option)
    res = option.get("residential_gfa_m2")
    mins = p["min_net_area_m2"]
    vals = {"min_net_area_m2": mins}
    if total and res:
        avg = res / total
        vals["average_gross_area_per_unit_m2"] = round(avg, 1)
        return _r(INFO, f"BC Housing minimum net unit areas are studio {mins['studio']}, one-bedroom {mins['one_bed']}, two-bedroom {mins['two_bed']}, three-bedroom {mins['three_bed_plus']} m²; the option averages {avg:.0f} m² gross per unit, so net areas should be checked at the plan stage.", vals)
    return _r(INFO, "BC Housing minimum net unit areas apply if BC Housing funds the project.", vals)


def code_basis_flags(site, option, p) -> Result:
    st = option.get("storeys") or 0
    part3 = st > p["part9_max_storeys"]
    vals = {"storeys": st, "part": 3 if part3 else "9 (if building area under 600 m²)"}
    msg = (f"{st} storeys puts the building under Part 3 of the BC Building Code 2024 and the Vancouver Building By-law 2025; "
           if part3 else f"{st} storeys may qualify for Part 9 if the building area is under 600 m²; ")
    msg += f"wood frame is standard to {6} storeys and encapsulated mass timber is permitted to {p['mass_timber_max_storeys_vbbl']} under the VBBL; seismic changes apply to permits from {p['seismic_vbbl_from']}."
    return _r(INFO, msg, vals)


# ---------------------------------------------------------------- Layer E: funding programs

def chf_fit(site, option, p) -> Result:
    fails, unknown, notes = [], [], []
    if not option.get("proponent_type"):
        unknown.append("the proponent type (" + ", ".join(t.replace("_", " ") for t in p["eligible_proponent_types"]) + ")")
    elif option.get("proponent_type") not in p["eligible_proponent_types"]:
        fails.append(f"proponent type ({str(option.get('proponent_type')).replace('_', ' ')}) is not eligible")
    tiers = option.get("rent_tiers_units")
    total = _units_total(option)
    vals: dict[str, Any] = {"required_mix": p["mix"], "status": p["status"]}
    if tiers and total:
        shares = {k: (tiers.get(k, 0) or 0) / total for k in p["mix"]}
        vals["mix_shares"] = {k: round(v, 3) for k, v in shares.items()}
        off = {k: abs(shares[k] - p["mix"][k]) for k in p["mix"]}
        if any(v > p["mix_tolerance"] for v in off.values()):
            msg = "unit mix " + ", ".join(f"{k.replace('_', ' ')} {_pct(shares[k])}" for k in p["mix"]) + " is not 30/50/20"
            if total < _smallest_split(p["mix"], p["mix_tolerance"]):
                msg += (f" (no split of {total} homes lands within {_pct(p['mix_tolerance'])} of it; "
                        f"{_smallest_split(p['mix'], p['mix_tolerance'])} homes is the smallest count that can)")
            fails.append(msg)
        else:
            notes.append("unit mix matches 30/50/20 within tolerance")
    else:
        unknown.append("rent-tier split (market / rent-geared-to-income / deep subsidy units)")
    acc = option.get("accessible_units")
    if acc is None:
        unknown.append("accessible unit count (5% minimum)")
    elif total and acc / total + 1e-9 < p["min_accessible_unit_share"]:
        fails.append(f"{acc} accessible units is under 5% of {total}")
    tenure_plan = (option.get("land_tenure_plan") or site.get("land_tenure_plan") or "")
    if "confirm" in tenure_plan.lower() or not tenure_plan:
        unknown.append(f"land tenure (lease of at least {p['min_lease_years_nominal']} years at nominal value, or ownership)")
    sc = option.get("site_control")
    bar = ", ".join(s.replace("_", " ") for s in p["readiness_site_control"])
    if sc is None or sc == "":
        # not answered is not the same as none: a blank is uncertain (15 Nov 2026; before, a blank was a fail printed as 'None')
        unknown.append(f"site control in hand ({bar})")
    elif sc not in p["readiness_site_control"]:
        fails.append(f"site control ({str(sc).replace('_', ' ')}) does not meet the RFP's readiness bar ({bar})")
    else:
        notes.append(f"site control ({sc.replace('_', ' ')}) meets the readiness bar")
    notes.append(f"construction must be able to start within {p['readiness_construction_start_months_after_award']} months of award")
    vals.update({"fails": fails, "unknown": unknown, "notes": notes,
                 "provisional_grant_per_unit_cad": p["provisional_grant_per_unit_cad_2025_26"],
                 "indicative_grant_cad": (p["provisional_grant_per_unit_cad_2025_26"] * total) if total else None})
    head = "Community Housing Fund: "
    notes.append(f"program status: {p['status']}")
    if fails:
        return _r(FAIL, head + "does not fit: " + "; ".join(fails) + ".", vals, action="Manager: resolve the failing criteria or target another program.")
    if unknown:
        said = "; ".join(notes)   # one sentence, capitalised once ("; Construction must…" was each note's capital)
        return _r(UNSURE, head + "fit cannot be confirmed without the " + "; ".join(unknown) + ". " + (said[:1].upper() + said[1:] + "." if said else ""),
                  vals, action="Manager: supply the missing figures; the indicative grant at 2025-26 rates would be "
                  + (f"${vals['indicative_grant_cad']:,.0f} for {total} units." if total else "set by unit count."))
    return _r(PASS, head + "fits the eligibility criteria: " + "; ".join(notes) + ".", vals)


def bc_builds_fit(site, option, p) -> Result:
    fails, unknown, notes = [], [], []
    if p["non_profit_must_team_with_developer"] and option.get("proponent_type") == "non_profit_society":
        partner = option.get("developer_partner")
        if partner is None or partner == "":
            unknown.append("non-profit's developer or builder partner (the program requires one; say whether there is one)")
        elif not partner:
            fails.append("a non-profit must team with a developer or builder to propose")
    share, disc = option.get("below_market_unit_share"), option.get("below_market_discount")
    if share is None or disc is None:
        unknown.append("share of units at least 20% below market")
    elif share + 1e-9 < p["min_below_market_unit_share"] or disc + 1e-9 < p["min_discount_to_market"]:
        fails.append(f"{_pct(share)} of units at {_pct(disc)} below market does not meet 20% at 20%")
    gfa, nonres = option.get("gfa_m2"), option.get("non_residential_gfa_m2") or 0
    if gfa:
        nr = nonres / gfa
        if nr > p["max_non_residential_share"]:
            fails.append(f"non-residential space is {_pct(nr)} of area, above the 30% cap")
        else:
            notes.append(f"non-residential space is {_pct(nr)} of area, under the 30% cap")
    lo, hi = p["ground_breaking_months_after_land_letter"]
    notes.append(f"ground must break within {lo} to {hi} months of the conditional land contribution letter")
    vals = {"fails": fails, "unknown": unknown, "notes": notes, "tenant_income_limits_cad": p["tenant_income_limits_cad"], "submission": p["submission"]}
    if fails:
        return _r(FAIL, "BC Builds: does not fit: " + "; ".join(fails) + ".", vals, action="Manager: resolve the failing criteria.")
    if unknown:
        # the notes are one sentence, capitalised once (17 Nov 2026: each was, so it read "…under the 30% cap; Ground
        # must break…"), and the action asks for what is actually missing, not always the below-market share
        said = "; ".join(notes)
        asks = (["say whether a developer or builder partner is in place"] if any("partner" in u for u in unknown) else []) \
            + (["state the below-market share and discount"] if any("below market" in u for u in unknown) else [])
        return _r(UNSURE, "BC Builds: fit cannot be confirmed without the " + "; ".join(unknown) + ". " + (said[:1].upper() + said[1:] + "." if said else ""),
                  vals, action=f"Manager: {' and '.join(asks) or 'supply what is missing'}; BC Builds applies opportunity by opportunity, so check the current Property Opportunity Notices.")
    return _r(PASS, "BC Builds: fits the published criteria: " + "; ".join(notes) + ".", vals)


def param_words(k: str, v: Any) -> str:
    """A rule parameter in words, as the memo prints it: the key without its unit suffix, the figure with its unit, an
    identifier as written (17 Nov 2026: "max loan cad: 250000", "rate pct: 6.19"). Pure; the page's paramWords
    (ffm/ui/core/util.js) is the same rule."""
    words = lambda s: re.sub(r"\bm2\b", "m²", re.sub(r"\bmin\b", "minimum", re.sub(r"\bmax\b", "maximum", s.replace("_", " "))))
    if isinstance(v, bool):
        return f"{words(k)}: {'yes' if v else 'no'}"
    if not isinstance(v, (int, float)) or re.search(r"(^|_)(id|vector|table|series|coordinate|code)$", k):
        return f"{words(k)}: {v}"
    num = lambda x: f"{x:,.0f}" if float(x).is_integer() else f"{x:,.3f}".rstrip("0").rstrip(".")
    if re.search(r"_cad(_\d{4}(_\d{2})?)?$", k):
        return f"{words(re.sub(r'_cad(_\d{4}(_\d{2})?)?$', '', k))}: ${num(v)}"
    if k.endswith("_pct"):
        return f"{words(k[:-4])}: {num(v)}%"
    # the unit token can sit mid-key too ("max_height_m_outright": "maximum height m outright: 10.7"); it moves to the
    # figure wherever it is
    if re.search(r"_m2(_|$)", k):
        return f"{words(re.sub(r'_m2(?=_|$)', '', k))}: {num(v)} m²"
    if re.search(r"_m(_|$)", k):
        return f"{words(re.sub(r'_m(?=_|$)', '', k))}: {num(v)} m"
    if re.search(r"(share|rate)(_of_\w+)?$", k) and 0 < v < 1:
        return f"{words(k)}: {num(round(v * 100, 1))}%"
    return f"{words(k)}: {num(v)}"


def info_only(site, option, p) -> Result:
    # an encoder's note to self ("criteria_note": … "pull from cmhc.ca/ahf before encoding") stays in the values, out
    # of the finding the memo prints
    bits = [param_words(k, v) for k, v in p.items() if v is not None and not isinstance(v, (dict, list)) and not re.search(r"(^|_)notes?$", k)]
    return _r(INFO, "; ".join(bits) + ".", dict(p))


# Where a schedule reduces the rear yard by the distance to a lane's ultimate centre line (RT-3 s.3.1.2.17) and the site
# says a lane runs behind but not how far its centre line is: half a standard 6.1 m (20 ft) City lane. A placeholder,
# not a rule: the ultimate centre line moves where the City plans a widening, and `site.context.lane_to_centre_line_m`
# replaces it. The suggester declares it among its assumptions.
LANE_TO_CENTRE_LINE_M = 3.05


def lot_as_fronted(site: Site) -> tuple[float, float]:
    """The lot's frontage and depth as the site is fronted: the lot turned to `site.front_face` where one is named
    (`boundary.oriented_ring`), else `frontage_m` and `depth_m`. Zeros where neither is known."""
    W, D = float(site.get("frontage_m") or 0), float(site.get("depth_m") or 0)
    if site.get("front_face"):
        try:
            from .boundary import oriented_ring
            o = oriented_ring(site)
            if o:
                return float(o["frontage_m"]), float(o["depth_m"])
        except (ValueError, KeyError, TypeError):
            pass
    return W, D


def corner_streets(site: Site) -> list[str]:
    """The two streets of a corner lot as the lookup named them (the parcel's street and its cross street, else the
    context frame's), or [] where the lookup found one street."""
    st = (site.get("parcel") or {}).get("street") or {}
    names = [st.get("name"), (st.get("cross_street") or {}).get("name")]
    if not all(names):
        fr = (site.get("osm") or {}).get("frame") or {}
        names = [fr.get("front_street"), ((fr.get("snapped_m") or {}).get("cross_street") or {}).get("name")]
    if not all(names) or names[0].strip().lower() == names[1].strip().lower():
        return []
    return [str(n) for n in names]


def other_front(site: Site) -> str | None:
    """On a corner lot, the street the site does not take as its front, or None: a lot on one street, or a front the
    architect named by side or edge (`site.front_face`), which a person has already chosen."""
    streets = corner_streets(site)
    if not streets:
        return None
    ff = site.get("front_face")
    if ff and not (isinstance(ff, dict) and ff.get("street")):
        return None
    cur = ((ff or {}).get("street") or site.get("front_street") or ((site.get("context") or {}).get("street") or {}).get("name") or streets[0])
    others = [s for s in streets if s.strip().lower() != str(cur).strip().lower()]
    return others[0] if len(others) == 1 else None


def yard_minimums(site: Site, p: Params) -> tuple[dict[str, float | None], dict | None]:
    """A schedule's minimum yards for this site: the rear reduced by the distance to the lane's ultimate centre line
    where the schedule says so (`rear_yard_lane_reduction`, the clause) and the site has a lane behind
    (`site.context.lane_behind`, with `lane_to_centre_line_m` or LANE_TO_CENTRE_LINE_M). Returns the minimums and the
    reduction applied (None where there is none)."""
    mins = {k: p.get(f"min_{k}_yard_m") for k in ("front", "rear", "side")}
    ctx = site.get("context") or {}
    if not (p.get("rear_yard_lane_reduction") and mins["rear"] is not None and ctx.get("lane_behind") is True):
        return mins, None
    dist = ctx.get("lane_to_centre_line_m")
    given = isinstance(dist, (int, float)) and not isinstance(dist, bool) and dist >= 0
    to_cl = float(dist) if given else LANE_TO_CENTRE_LINE_M
    lane = {"clause": p["rear_yard_lane_reduction"], "to_centre_line_m": to_cl, "given": given, "rear_yard_m": mins["rear"]}
    mins["rear"] = round(max(0.0, float(mins["rear"]) - to_cl), 2)
    return mins, lane


def _m(x: float) -> str:
    return f"{x:.1f}"


def _no_envelope(site, option, p, mins, lane, eff, W, D, short, vals) -> Result:
    """The yards the option keeps (at least the schedule's) leave no plate on the lot as fronted. Uncertain, never a
    fail: the other street as the front of a corner lot, a lane behind, or the Director's variance may leave one, and the
    finding gives each one's numbers (decided with Kai, 17 Nov 2026, on 609 Heatley Ave)."""
    district = site.get("zoning_district") or "the district"
    w_left, d_left = W - 2 * eff["side"], D - eff["front"] - eff["rear"]
    which = []
    if d_left <= 0:
        which.append(f"a front yard of {eff['front']:g} m and a rear yard of {eff['rear']:g} m on a lot {D:g} m deep"
                     + (f" (the {lane['rear_yard_m']:g} m rear yard less {lane['to_centre_line_m']:g} m to the lane's centre line, {lane['clause']})" if lane else ""))
    if w_left <= 0:
        which.append(f"two side yards of {eff['side']:g} m on a lot {W:g} m wide")
    finding = f"The {district} yards leave no envelope on this lot as fronted: {' and '.join(which)}."
    if short:
        finding += f" The option's own setbacks sit inside them ({'; '.join(short)})."
    ways: list[str] = []
    asks: list[str] = []
    vals.update({"no_envelope": True, "lot_as_fronted_m": {"frontage": round(W, 2), "depth": round(D, 2)},
                 "envelope_m": {"width": round(max(0.0, w_left), 2), "depth": round(max(0.0, d_left), 2)}})
    # the other street as the front: the lot turned a quarter, the same yards (a front yard the schedule fixes, else the
    # most it can ask)
    other = other_front(site)
    if other:
        f_alt = mins["front"] if mins["front"] is not None else (p.get("max_front_yard_m") if p.get("max_front_yard_m") is not None else eff["front"])
        rear_base = lane["rear_yard_m"] if lane else mins["rear"] or 0
        w2, d2 = D - 2 * eff["side"], W - float(f_alt) - float(rear_base)
        alt = {"street": other, "frontage_m": round(D, 2), "depth_m": round(W, 2), "front_yard_m": f_alt,
               "envelope_m": {"width": round(max(0.0, w2), 2), "depth": round(max(0.0, d2), 2)}}
        if w2 > 0 and d2 > 0:
            words = (f"With {other} as the front the lot is about {D:.1f} m wide and {W:.1f} m deep, and the same yards"
                     + (f" (a front yard of up to {f_alt:g} m)" if mins["front"] is None and p.get("max_front_yard_m") is not None else "")
                     + f" leave about {_m(w2)} × {_m(d2)} m ({w2 * d2:,.0f} m²)")
            if p.get("rear_yard_lane_reduction"):
                d3 = d2 + LANE_TO_CENTRE_LINE_M
                alt["envelope_with_lane_m"] = {"width": round(w2, 2), "depth": round(d3, 2)}
                words += f"; {_m(w2)} × {_m(d3)} m ({w2 * d3:,.0f} m²) if a lane runs behind it ({p['rear_yard_lane_reduction']}, {LANE_TO_CENTRE_LINE_M:g} m to a standard lane's centre line)"
            ways.append(words + ".")
            asks.append(f"choose the front of the corner lot at 01 (the schedule does not say which street a corner site fronts; confirm it with the City), and if {other} is the front, say whether a lane runs behind it")
        else:
            ways.append(f"With {other} as the front the same yards leave no envelope either ({_m(max(0.0, w2))} × {_m(max(0.0, d2))} m).")
        vals["other_front"] = alt
    # a lane behind the lot as fronted, where the site has not said and it would leave a plate
    ctx = site.get("context") or {}
    if p.get("rear_yard_lane_reduction") and not lane and ctx.get("lane_behind") is None and mins["rear"] is not None:
        d_lane = D - eff["front"] - (float(mins["rear"]) - LANE_TO_CENTRE_LINE_M)   # the schedule's rear yard, reduced
        if d_lane > 0 and w_left > 0:
            ways.append(f"If a lane runs behind the lot, {p['rear_yard_lane_reduction']} takes {LANE_TO_CENTRE_LINE_M:g} m off the rear yard and leaves about {_m(w_left)} × {_m(d_lane)} m.")
            asks.append("say whether a lane runs behind the lot")
    # the Director of Planning's variance for affordable housing, stated as a question for the City, never assumed
    var = p.get("affordable_variance")
    if var:
        clause = var.get("clause") if isinstance(var, dict) else str(var)
        needs = var.get("needs") if isinstance(var, dict) else ""
        words = f"Or ask the Director of Planning to vary the yards under {clause}" + (f" ({needs})" if needs else "")
        if option.get("tenure") == "social_housing":
            words += "; this option is social housing, which can meet that"
        from .massing import PLATE_MIN_DEPTH_M
        room = D - eff["front"]
        if d_left <= 0 < room and w_left > 0:
            depth = min(PLATE_MIN_DEPTH_M, room)
            rear_max = room - depth
            words += f". On this front a rear yard of at most {rear_max:.1f} m (against {mins['rear']:g} m) leaves a plate {depth:.1f} m deep"
            vals["variance"] = {"clause": clause, "rear_yard_for_plate_m": round(rear_max, 2), "plate_depth_m": round(depth, 2)}
        else:
            vals["variance"] = {"clause": clause}
        ways.append(words + "; the variance is the City's to grant, not assumed here.")
        asks.append(f"or ask the Director of Planning about a variance under {clause}")
    finding += (" " + " ".join(ways)) if ways else " The yards must change before a building fits."
    action = ("Manager or architect: " + "; ".join(asks) + ".") if asks else "Architect: the yards must change before a building fits; state the relaxation to ask for."
    return _r(UNSURE, finding, vals, action=action)


def district_setbacks(site, option, p) -> Result:
    """A district schedule's minimum yards against the option's setbacks: pass where the option keeps them,
    conditional where it sits inside one (a relaxation to ask for), info where the option states none, uncertain where
    the yards leave no envelope on the lot as fronted (values `no_envelope`; the outright answer reads "not yet
    confirmed" then, and the finding gives the other front, the lane and the variance with their numbers). The rear
    minimum is reduced for a lane behind where the schedule says so (`yard_minimums`)."""
    mins, lane = yard_minimums(site, p)
    sb = option.get("setbacks_m") or {}
    vals = {f"min_{k}_yard_m": v for k, v in mins.items()} | {f"setback_{k}_m": sb.get(k) for k in mins}
    if lane:
        vals["lane_reduction"] = lane
    lane_words = (f", the {lane['rear_yard_m']:g} m rear yard less {lane['to_centre_line_m']:g} m to the lane's centre line under {lane['clause']}"
                  + ("" if lane["given"] else ", a standard lane assumed")) if lane else ""
    said = "; ".join(f"{k} {v} m" + (lane_words if k == "rear" else "") for k, v in mins.items() if v is not None) or "no minimum yards given"
    if not any(v is not None for v in sb.values()):
        return _r(INFO, f"The schedule's minimum yards are {said}; the option states no setbacks yet.", vals)
    short = [f"{k} {sb[k]} m against a {mins[k]} m minimum" for k in mins if mins[k] is not None and sb.get(k) is not None and sb[k] + 1e-9 < mins[k]]
    W, D = lot_as_fronted(site)
    eff = {k: max(float(sb.get(k) or 0), float(mins[k] or 0)) for k in mins}
    if W > 0 and D > 0 and (D - eff["front"] - eff["rear"] <= 0 or W - 2 * eff["side"] <= 0):
        return _no_envelope(site, option, p, mins, lane, eff, W, D, short, vals)
    if short:
        var = p.get("affordable_variance")
        clause = (var.get("clause") if isinstance(var, dict) else str(var)) if var else None
        return _r(COND, f"The option sits inside the schedule's minimum yards: {'; '.join(short)}. A relaxation is needed or the envelope moves in.",
                  vals, action="Architect: move the mass to the minimum yards or state the relaxation to ask for"
                  + (f" (the Director of Planning may vary the yards for affordable housing under {clause})." if clause else "."))
    return _r(PASS, f"The option's setbacks keep the schedule's minimum yards ({said}).", vals)


def assumption(site, option, p) -> Result:
    """Layer F: a dated, cited assumption the pro-forma reads. Always information; the finding is the assumption's
    own summary, and the values carry the figures so the pro-forma cites the rule by id."""
    vals = {k: v for k, v in p.items() if k not in ("summary", "observations")}
    return _r(INFO, (p.get("summary") or "assumption") + ".", vals)


CHECKS: dict[str, Callable[[Site, Option, Params], Result]] = {
    "district_setbacks": district_setbacks,
    "assumption": assumption,
    "district_outright_fsr": district_outright_fsr,
    "district_outright_height": district_outright_height,
    "rezoning_policy_social_housing": rezoning_policy_social_housing,
    "parking_minimums": parking_minimums,
    "ssmuh_minimum_units": ssmuh_minimum_units,
    "toa_status": toa_status,
    "family_unit_share": family_unit_share,
    "social_housing_definition": social_housing_definition,
    "below_market_rental_policy": below_market_rental_policy,
    "tree_replacement": tree_replacement,
    "dcl_cac": dcl_cac,
    "unit_area_flags": unit_area_flags,
    "code_basis_flags": code_basis_flags,
    "chf_fit": chf_fit,
    "bc_builds_fit": bc_builds_fit,
    "info_only": info_only,
}
