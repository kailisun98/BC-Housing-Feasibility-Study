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

from .checks import _schedule_c_required
from .engine import evaluate
from .rules_loader import RULES_DIR, Rule, load_rules, stamp

# Declared placeholders, not rules: a person can change them, and the memo says they were used.
ASSUMPTIONS = {
    "floor_to_floor_m": (3.3, "usual for wood-frame residential; the committed options use it"),
    "setbacks_m": ({"front": 3.7, "rear": 6.0, "side": 3.0}, "not read from the district schedule; the committed options assume them on a 37 m deep lot, and a shallower or narrower lot gets them scaled down (front 12%, rear 20% of the depth, sides 8% of the frontage, each at most these)"),
    "net_efficiency": (0.78, "net residential floor area as a share of residential GFA; typical for a double-loaded corridor"),
    "design_allowance": (1.10, "units drawn 10% above the BC Housing minimum net areas"),
    "mix_shares": ({"studio": 0.20, "one_bed": 0.40, "two_bed": 0.32, "three_bed_plus": 0.08},
                   "a starting bedroom mix that clears the family-unit minimums; the person tunes it"),
}

CANDIDATES = [
    {"id": "outright", "title": "Outright", "what": "what the district allows as of right"},
    {"id": "benchmark", "title": "Benchmark", "what": "the staff benchmark under the social housing rezoning policy"},
    {"id": "funder-ready", "title": "Funder-ready", "what": "the benchmark envelope with every funder question answered"},
]


def setbacks_for(site: dict) -> dict[str, float]:
    """The placeholder setbacks, scaled to the lot: the committed figures (3.7 / 6.0 / 3.0 m) on a lot as deep as
    998 E 19th Ave, and no more than 12% of the depth in front, 20% behind and 8% of the frontage each side on a
    smaller one, so a shallow corner lot keeps a buildable envelope. Still a placeholder, declared as such."""
    base, _ = ASSUMPTIONS["setbacks_m"]
    W, D = float(site.get("frontage_m") or 0), float(site.get("depth_m") or 0)
    if not W or not D:
        return dict(base)
    return {"front": round(min(base["front"], D * 0.12), 1), "rear": round(min(base["rear"], D * 0.20), 1), "side": round(min(base["side"], W * 0.08), 1)}


def _rule(rules: list[Rule], rule_id: str) -> Rule | None:
    return next((r for r in rules if r.id == rule_id), None)


def _params(rules: list[Rule], on: date, rule_id: str, district: str = "*") -> dict | None:
    """The params of a rule in force on the date and applying to the district, else None."""
    r = _rule(rules, rule_id)
    if r is None or not r.applies_to(district):
        return None
    v = r.version_on(on)
    return v.params if v else None


def _largest_remainder(total: int, shares: dict[str, float]) -> dict[str, int]:
    raw = {k: total * s for k, s in shares.items()}
    out = {k: int(math.floor(v)) for k, v in raw.items()}
    left = total - sum(out.values())
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[:max(0, left)]:
        out[k] += 1
    return out


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


def _envelope(site: dict, candidate: str, rules: list[Rule], on: date, fields: dict, unsure: list) -> dict[str, Any]:
    """Storeys, height, FSR and GFA for the candidate, from layer A (or B on a small lot)."""
    district = site.get("zoning_district") or ""
    area = float(site.get("site_area_m2") or 0)
    f2f, _ = ASSUMPTIONS["floor_to_floor_m"]
    out: dict[str, Any] = {"storeys": None, "height_m": None, "gfa_m2": None, "fsr": None}
    p_fsr = _params(rules, on, "cov.rm1.outright_fsr", district)
    p_h = _params(rules, on, "cov.rm1.outright_height", district)
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
        fields["storeys"] = {"value": storeys, "rule_id": "cov.irp.social_housing_rezoning", "note": f"the most storeys of {f2f} m inside the staff benchmark of {p_irp['benchmark_height_m_low']} to {hi} m" + (f", capped at the wood-frame standard of {wood_max}" if storeys == wood_max else "")}
        fields["height_m"] = {"value": out["height_m"], "rule_id": "cov.irp.social_housing_rezoning", "note": f"{storeys} storeys × {f2f} m, inside the benchmark"}
        fields["gfa_m2"] = {"value": out["gfa_m2"], "rule_id": "cov.irp.social_housing_rezoning", "note": f"the benchmark FSR of about {bf} × the site area {area:,.0f} m²"}
        fields["rezoning_path"] = {"value": "CD-1 under the Interim Rezoning Policy for Social Housing", "rule_id": "cov.irp.social_housing_rezoning", "note": "the site is inside a former Community Vision area and the option is 100% social housing"}
        return out
    if candidate in ("benchmark", "funder-ready") and not irp_ok:
        if in_cv is None and p_irp is not None:
            unsure.append({"key": "in_former_community_vision_area", "why": "whether the site is inside a former Community Vision area (Map 1 of the policy) decides whether the benchmark applies", "who": "Architect: check Map 1 for this address"})
        # fall through to outright
    if p_fsr and p_h:
        storeys = min(int(math.floor(p_h["max_height_m"] / f2f)), wood_max)
        out.update({"storeys": storeys, "height_m": round(min(storeys * f2f, p_h["max_height_m"]), 1), "fsr": p_fsr["max_fsr"], "gfa_m2": round(p_fsr["max_fsr"] * area, 0)})
        fields["storeys"] = {"value": storeys, "rule_id": "cov.rm1.outright_height", "note": f"the most storeys of {f2f} m under the outright maximum of {p_h['max_height_m']} m"}
        fields["height_m"] = {"value": out["height_m"], "rule_id": "cov.rm1.outright_height", "note": f"{storeys} storeys × {f2f} m, under {p_h['max_height_m']} m"}
        fields["gfa_m2"] = {"value": out["gfa_m2"], "rule_id": "cov.rm1.outright_fsr", "note": f"the outright FSR of {p_fsr['max_fsr']} × the site area {area:,.0f} m²"}
        fields["rezoning_path"] = {"value": None, "rule_id": "cov.rm1.outright_fsr", "note": "outright: no rezoning"}
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
    unsure.append({"key": "gfa_m2", "why": f"the rule stack has no outright schedule for {district or 'this district'}" + (": a CD-1 site's limits are whatever the rezoning sets" if district.upper().startswith("CD-1") else ""), "who": "Manager: enter the storeys, height and floor area the rezoning or the schedule sets"})
    fields["rezoning_path"] = {"value": None, "rule_id": None, "note": "not derived: enter the path the site takes"}
    return out


def suggest(site: dict, programs: list[str] | None, on: date, candidate: str = "funder-ready",
            rules: list[Rule] | None = None, rules_dir: Path = RULES_DIR) -> dict[str, Any]:
    rules = rules if rules is not None else load_rules(rules_dir)
    programs = list(programs or [])
    district = site.get("zoning_district") or ""
    area = float(site.get("site_area_m2") or 0)
    fields: dict[str, dict] = {}
    unsure: list[dict] = []
    assumptions = [{"key": k, "value": v, "note": n} for k, (v, n) in ASSUMPTIONS.items()]
    f2f, _ = ASSUMPTIONS["floor_to_floor_m"]
    sb = setbacks_for(site)
    eff, _ = ASSUMPTIONS["net_efficiency"]
    allowance, _ = ASSUMPTIONS["design_allowance"]
    shares, _ = ASSUMPTIONS["mix_shares"]

    # which candidates the site can take
    p_irp = _params(rules, on, "cov.irp.social_housing_rezoning", district)
    has_outright = _params(rules, on, "cov.rm1.outright_fsr", district) is not None or _params(rules, on, "bc.ssmuh.minimum_units", district) is not None
    cands = []
    for c in CANDIDATES:
        if c["id"] == "outright":
            ok, why = has_outright, "" if has_outright else f"no outright schedule for {district or 'this district'} in the rule stack"
        else:
            ok = p_irp is not None and site.get("in_former_community_vision_area") is not False
            why = "" if ok else "the site is outside the former Community Vision areas, so the social housing benchmark does not apply"
        cands.append({**c, "available": ok, "why": why})
    if candidate not in {c["id"] for c in cands}:
        candidate = "funder-ready"

    env = _envelope(site, candidate, rules, on, fields, unsure)
    gfa = env.get("gfa_m2")
    storeys = env.get("storeys")

    # the building
    option: dict[str, Any] = {
        "id": f"{site.get('id') or 'site'}-suggested-{candidate}",
        "name": f"Suggested, {candidate}: rule-derived as of {on.isoformat()}",
        "proponent": site.get("owner") or None,
        "proponent_type": "non_profit_society",
        "developer_partner": None,
        "tenure": "social_housing",
        "rezoning_path": fields.get("rezoning_path", {}).get("value"),
        "storeys": storeys, "height_m": env.get("height_m"), "gfa_m2": gfa,
        "residential_gfa_m2": gfa, "non_residential_gfa_m2": 0 if gfa else None,
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
    fields["proponent_type"] = {"value": "non_profit_society", "rule_id": "bch.chf.eligibility", "note": "assumed a society; change for a co-operative, a municipal provider or a First Nation"}
    fields["tenure"] = {"value": "social_housing", "rule_id": "cov.social_housing_definition", "note": "100% social housing: exempt from levies and the path the rezoning policy takes"}
    fields["floor_to_floor_m"] = {"value": f2f, "rule_id": None, "note": "placeholder"}
    for k in ("front", "rear", "side"):
        fields[f"setbacks_m.{k}"] = {"value": sb[k], "rule_id": None, "note": "placeholder, not read from the district schedule" + ("; scaled to this lot" if sb[k] < ASSUMPTIONS["setbacks_m"][0][k] else "")}
    fields["non_residential_gfa_m2"] = {"value": option["non_residential_gfa_m2"], "rule_id": "bc.bcbuilds.eligibility", "note": "none suggested; BC Builds caps it at 30% of the floor area"}
    fields["residential_gfa_m2"] = {"value": gfa, "rule_id": None, "note": "all of the floor area, with no non-residential space"}

    # units, from layers C and D
    p_fam = _params(rules, on, "cov.family_units", district)
    p_areas = _params(rules, on, "bch.design_guidelines.unit_areas", district)
    if gfa and p_areas:
        counts, avg = unit_mix(gfa * eff, p_areas["min_net_area_m2"], p_fam, allowance, shares)
        option["units"] = counts
        n = sum(counts.values())
        for k, v in counts.items():
            fields[f"units.{k}"] = {"value": v, "rule_id": "bch.design_guidelines.unit_areas", "note": f"{n} units at an average {avg} m² net ({int((allowance - 1) * 100)}% over the BC Housing minimums) in {gfa * eff:,.0f} m² net; family minimums from cov.family_units"}
        if p_fam:
            two_plus = counts["two_bed"] + counts["three_bed_plus"]
            fields["units.two_bed"]["note"] = f"{two_plus} of {n} units ({two_plus / n * 100:.0f}%) have two or more bedrooms, against the {p_fam['min_two_plus_bed_share'] * 100:.0f}% minimum"
            if p_fam.get("min_three_plus_bed_share"):
                fields["units.three_bed_plus"]["note"] = f"{counts['three_bed_plus']} of {n} ({counts['three_bed_plus'] / n * 100:.0f}%) have three or more, against the {p_fam['min_three_plus_bed_share'] * 100:.0f}% minimum"
    else:
        n = 0
        if env.get("ssmuh_units"):
            n = int(env["ssmuh_units"])
            counts = _largest_remainder(n, shares)
            option["units"] = counts
            for k, v in counts.items():
                fields[f"units.{k}"] = {"value": v, "rule_id": "bc.ssmuh.minimum_units", "note": f"{n} homes, the provincial minimum, in the starting mix"}

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
            for k, v in tiers.items():
                fields[f"rent_tiers_units.{k}"] = {"value": v, "rule_id": "bch.chf.eligibility", "note": f"{p_chf['mix'][k] * 100:.0f}% of {n} units under the fund's 30 / 50 / 20 mix"}
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

    # what no rule settles
    if site.get("in_transit_oriented_area") is None:
        unsure.append({"key": "in_transit_oriented_area", "why": "inside a transit-oriented area the Province sets a minimum height by tier; the City's map decides", "who": "Architect: check the City's transit-oriented areas map"})
    if district.upper().startswith("CD-1"):
        unsure.append({"key": "zoning_district", "why": "a CD-1 site's limits are whatever its rezoning set", "who": "Manager: read the CD-1 by-law for the site"})

    fields["target_programs"] = {"value": programs, "rule_id": None, "note": "the programs chosen"}
    fields["id"] = {"value": option["id"], "rule_id": None, "note": "named after the site and the candidate"}
    fields["name"] = {"value": option["name"], "rule_id": None, "note": ""}

    return {
        "candidate": candidate, "candidates": cands, "option": option, "fields": fields,
        "unsure": unsure, "assumptions": assumptions, "as_of": on.isoformat(), "stamp": stamp(rules, on, rules_dir),
    }


def read_site(site: dict, on: date, rules: list[Rule] | None = None, rules_dir: Path = RULES_DIR) -> dict[str, Any]:
    """The site alone against layers A to C, before any option exists: what it allows outright, which rezoning path
    it has, its transit and tree position. Run with a bare social-housing option so the policy rules speak; nothing
    is written."""
    probe = {"id": f"{site.get('id') or 'site'}-read", "name": "Reading the site", "tenure": "social_housing", "target_programs": []}
    L = evaluate(site, probe, on, rules=rules, rules_dir=rules_dir)
    keep = [r for r in L["results"] if r["layer"] in ("A", "B", "C") and r["status"] != "not_applicable"]
    return {"as_of": on.isoformat(), "stamp": L["run"]["stamp"], "results": keep, "site": site}
