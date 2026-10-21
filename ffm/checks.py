"""Deterministic checks. Each takes (site, option, params) and returns a dict:

    status   one of pass, conditional, fail, uncertain, not_applicable, info
    finding  one sentence with the arithmetic shown
    values   the numbers used, so the memo and the massing can cite them
    action   what a person must do next, if anything (empty for pass/info)

No model is involved here. Same inputs, same output, every run.
"""

from __future__ import annotations

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


def fsr(site: Site, option: Option) -> float | None:
    if site.get("site_area_m2") and option.get("gfa_m2"):
        return option["gfa_m2"] / site["site_area_m2"]
    return None


# ---------------------------------------------------------------- Layer A: zoning district

def district_outright_fsr(site, option, p) -> Result:
    f = fsr(site, option)
    if f is None:
        return _r(UNSURE, "Floor space ratio cannot be computed: site area or gross floor area missing.",
                  action="Enter the site area and the option's gross floor area.")
    mx = p["max_fsr"]
    vals = {"fsr": round(f, 3), "max_fsr_outright": mx, "gfa_m2": option["gfa_m2"], "site_area_m2": site["site_area_m2"]}
    if f <= mx:
        return _r(PASS, f"FSR {f:.2f} ({option['gfa_m2']:,.0f} m² over {site['site_area_m2']:,.1f} m²) is within the outright maximum of {mx}.", vals)
    if option.get("rezoning_path"):
        return _r(UNSURE, f"FSR {f:.2f} exceeds the outright maximum of {mx}; it can proceed only by rezoning ({option['rezoning_path']}), where density is negotiated.",
                  vals, action="Architect and manager: confirm the rezoning path and the density staff will support.")
    return _r(FAIL, f"FSR {f:.2f} exceeds the outright maximum of {mx} and no rezoning path is stated.", vals,
              action="Reduce the floor area or state a rezoning path.")


def district_outright_height(site, option, p) -> Result:
    h = option.get("height_m")
    if h is None:
        return _r(UNSURE, "Height missing.", action="Enter the proposed height to the roof parapet in metres.")
    mx = p["max_height_m"]
    vals = {"height_m": h, "max_height_m_outright": mx, "storeys": option.get("storeys")}
    if h <= mx:
        return _r(PASS, f"Height {h} m is within the outright maximum of {mx} m.", vals)
    if option.get("rezoning_path"):
        return _r(UNSURE, f"Height {h} m exceeds the outright maximum of {mx} m; it can proceed only by rezoning ({option['rezoning_path']}), where height is negotiated.",
                  vals, action="Architect: confirm the height staff will support under the policy.")
    return _r(FAIL, f"Height {h} m exceeds the outright maximum of {mx} m and no rezoning path is stated.", vals,
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
    return _r(INFO, f"No minimum off-street parking applies citywide since June 2024; the option provides {option.get('parking_spaces', 'n/a')} vehicle and {option.get('bicycle_spaces', 'n/a')} bicycle spaces, which are set by the Parking By-law at the development permit stage.",
              {"parking_spaces": option.get("parking_spaces"), "bicycle_spaces": option.get("bicycle_spaces")})


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
        return _r(UNSURE, "The site is in a transit-oriented area but the tier is not recorded.", action="Record the TOA tier from the City's map.")
    st = option.get("storeys")
    vals = {"toa_tier": tier, "minimum_allowable_storeys": floors, "storeys": st}
    return _r(INFO, f"Tier {tier}: the City may not refuse at least {floors} storeys for this parcel; the option proposes {st}.", vals)


# ---------------------------------------------------------------- Layer C: City policies

def family_unit_share(site, option, p) -> Result:
    u = option.get("units") or {}
    total = _units_total(option)
    if total == 0:
        return _r(UNSURE, "Unit mix missing.", action="Enter the unit counts by bedroom type.")
    two_plus = int(u.get("two_bed", 0) or 0) + int(u.get("three_bed_plus", 0) or 0)
    three_plus = int(u.get("three_bed_plus", 0) or 0)
    s2, s3 = two_plus / total, three_plus / total
    vals = {"units_total": total, "two_plus_bed_units": two_plus, "two_plus_bed_share": round(s2, 4),
            "three_plus_bed_units": three_plus, "three_plus_bed_share": round(s3, 4),
            "min_two_plus_bed_share": p["min_two_plus_bed_share"], "min_three_plus_bed_share": p.get("min_three_plus_bed_share")}
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
    finding = "; ".join(parts) + "."
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
        return _r(INFO, "Social housing is exempt from development cost levies and from community amenity contributions in a rezoning; the church use is also DCL-exempt. The exemption's value is worth stating in the memo.",
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
    if option.get("proponent_type") not in p["eligible_proponent_types"]:
        fails.append(f"proponent type '{option.get('proponent_type')}' is not eligible")
    tiers = option.get("rent_tiers_units")
    total = _units_total(option)
    vals: dict[str, Any] = {"required_mix": p["mix"], "status": p["status"]}
    if tiers and total:
        shares = {k: (tiers.get(k, 0) or 0) / total for k in p["mix"]}
        vals["mix_shares"] = {k: round(v, 3) for k, v in shares.items()}
        off = {k: abs(shares[k] - p["mix"][k]) for k in p["mix"]}
        if any(v > p["mix_tolerance"] for v in off.values()):
            fails.append("unit mix " + ", ".join(f"{k} {_pct(shares[k])}" for k in p["mix"]) + " is not 30/50/20")
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
    if sc not in p["readiness_site_control"]:
        fails.append(f"site control '{sc}' does not meet the RFP's readiness bar")
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
        return _r(UNSURE, head + "fit cannot be confirmed without the " + "; ".join(unknown) + ". " + "; ".join(n[0].upper() + n[1:] for n in notes) + ".",
                  vals, action="Manager: supply the missing figures; the indicative grant at 2025-26 rates would be "
                  + (f"${vals['indicative_grant_cad']:,.0f} for {total} units." if total else "set by unit count."))
    return _r(PASS, head + "Fits the eligibility criteria: " + "; ".join(notes) + ".", vals)


def bc_builds_fit(site, option, p) -> Result:
    fails, unknown, notes = [], [], []
    if p["non_profit_must_team_with_developer"] and option.get("proponent_type") == "non_profit_society" and not option.get("developer_partner"):
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
        return _r(UNSURE, "BC Builds: fit cannot be confirmed without the " + "; ".join(unknown) + ". " + "; ".join(n[0].upper() + n[1:] for n in notes) + ".",
                  vals, action="Manager: state the below-market share and discount; BC Builds applies opportunity by opportunity, so check the current Property Opportunity Notices.")
    return _r(PASS, "BC Builds: fits the published criteria: " + "; ".join(notes) + ".", vals)


def info_only(site, option, p) -> Result:
    bits = [f"{k.replace('_', ' ')}: {v}" for k, v in p.items() if not isinstance(v, (dict, list))]
    return _r(INFO, "; ".join(bits) + ".", dict(p))


CHECKS: dict[str, Callable[[Site, Option, Params], Result]] = {
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
