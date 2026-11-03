"""The feasibility-grade pro-forma: arithmetic over layer F (assumptions) and layer E (the programs), read from
the ledger so the version in force on the run date is the one used and the memo's stamp covers it.

    build(site, option, ledger) -> {
        "grade": "feasibility",                      not a lender's model, and the memo says so
        "capital":   hard, escalation, soft, contingency, land, total
        "operating": revenue by tier, vacancy, operating cost, reserve, net operating income
        "funding":   grants (from layer E), equity, supportable debt (NOI at the DCR), total
        "gap":       capital less funding, and as a share of capital
        "verdict":   {"word": "likely" | "unlikely" | "unsure", "why": [...], "unsure": [...]}
        "lines":     every figure with its rule id, its note and whether it is a placeholder, in memo order
    }

Every line prints its source: the rule id of the assumption it came from (layer F), the program (layer E), or the
option's own finance block (`option["finance"]`: land_cost_cad, equity_cad, other_grants_cad). A figure the
stack cannot settle (land on a private site, a rent type the tables do not give) is flagged and the verdict is
"unsure" rather than guessed. Standard library only; deterministic; runs in the browser.
"""

from __future__ import annotations

from typing import Any

UNIT_KEYS = ("studio", "one_bed", "two_bed", "three_bed_plus")
TIER_KEYS = ("market", "rgi", "deep_subsidy")
GAP_UNLIKELY_SHARE = 0.15   # a gap above this share of the capital cost reads "unlikely"; below it, "unsure"


def _layer(ledger: dict, layer: str) -> dict[str, dict]:
    """The ledger's results for a layer, by rule id, only those in force (not 'not_applicable')."""
    return {r["rule_id"]: r for r in ledger.get("results", []) if r.get("layer") == layer and r.get("status") != "not_applicable"}


def _units(option: dict) -> dict[str, int]:
    u = option.get("units") or {}
    return {k: int(u.get(k) or 0) for k in UNIT_KEYS}


def _tiers(option: dict, total: int) -> dict[str, int] | None:
    t = option.get("rent_tiers_units")
    if not t or not any(t.get(k) for k in TIER_KEYS):
        return None
    out = {k: int(t.get(k) or 0) for k in TIER_KEYS}
    if sum(out.values()) != total and total:
        # the tiers were typed for a different count: scale them to the units, largest remainder
        raw = {k: total * out[k] / max(1, sum(out.values())) for k in TIER_KEYS}
        out = {k: int(raw[k]) for k in TIER_KEYS}
        for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[: total - sum(out.values())]:
            out[k] += 1
    return out


def mortgage_constant(rate_pct: float, years: int) -> float:
    """Annual debt service per dollar borrowed, monthly payments."""
    i = rate_pct / 100 / 12
    n = years * 12
    if i <= 0:
        return 1 / years
    return 12 * i / (1 - (1 + i) ** -n)


def build(site: dict, option: dict, ledger: dict) -> dict[str, Any]:
    F = _layer(ledger, "F")
    E = _layer(ledger, "E")
    lines: list[dict] = []
    unsure: list[str] = []
    why: list[str] = []

    def line(key: str, label: str, value: Any, unit: str, rule: str | None, note: str = "", placeholder: bool = False) -> None:
        lines.append({"key": key, "label": label, "value": value, "unit": unit, "rule_id": rule, "note": note, "placeholder": placeholder})

    def P(rule_id: str) -> dict:
        return (F.get(rule_id) or {}).get("values") or {}

    def is_placeholder(rule_id: str) -> bool:
        return bool(((F.get(rule_id) or {}).get("source") or {}).get("placeholder"))

    missing = [rid for rid in ("f.hard_cost_base", "f.escalation_bcpi", "f.soft_costs", "f.land", "f.mortgage", "f.rents", "f.operating") if rid not in F]
    if missing:
        return {"grade": "feasibility", "available": False, "why": f"layer F is missing {', '.join(missing)} on this date", "lines": [], "verdict": {"word": "unsure", "why": ["the assumptions layer is incomplete"], "unsure": missing}}

    units = _units(option)
    n = sum(units.values())
    gfa = float(option.get("gfa_m2") or 0)
    fin = option.get("finance") or {}

    # ---------------- capital cost
    hc, esc, soft, land = P("f.hard_cost_base"), P("f.escalation_bcpi"), P("f.soft_costs"), P("f.land")
    rate_m2 = float(hc.get("value_per_m2_cad") or 0)
    base_period = hc.get("base_period")
    # the escalation factor: the last index published on or before the run date over the index at the hard-cost
    # base period (the observations are kept out of the ledger values, so they are read from the rule in force)
    obs = _observations(ledger, "f.escalation_bcpi")
    as_of = str(ledger.get("run", {}).get("as_of") or "")
    on_or_before = [p for p in obs if p <= _published_cutoff(as_of)] if as_of else list(obs)
    latest_period = max(on_or_before) if on_or_before else None
    latest = float(obs[latest_period]) if latest_period else 0.0
    base_index = float(obs.get(base_period) or 0) if base_period else 0.0
    factor = round(latest / base_index, 4) if latest and base_index else 1.0
    hard = round(gfa * rate_m2 * factor) if gfa else None
    line("hard_rate", "Hard cost base", rate_m2, "$/m²", "f.hard_cost_base", f"{hc.get('basis', '')}".split(";")[0], False)
    line("escalation", "Escalation to the latest index", factor, "×", "f.escalation_bcpi",
         f"BCPI {latest} ({latest_period}) over {base_index} ({base_period})" if base_index and latest else "index not on file for this date: no escalation applied")
    line("hard", "Hard cost", hard, "$", "f.hard_cost_base", f"{gfa:,.0f} m² × ${rate_m2:,.0f} × {factor}" if gfa else "no floor area")
    s_share, c_share = float(soft.get("soft_cost_share_of_hard") or 0), float(soft.get("contingency_share_of_hard") or 0)
    soft_cost = round(hard * s_share) if hard else None
    contingency = round(hard * c_share) if hard else None
    line("soft", "Soft costs", soft_cost, "$", "f.soft_costs", f"{s_share * 100:.0f}% of hard cost", is_placeholder("f.soft_costs"))
    line("contingency", "Contingency", contingency, "$", "f.soft_costs", f"{c_share * 100:.0f}% of hard cost", is_placeholder("f.soft_costs"))

    land_cost = fin.get("land_cost_cad")
    owner_type = str(site.get("owner_type") or "").lower().replace(" ", "_")
    nominal_types = [str(t).lower() for t in (land.get("nominal_lease_owner_types") or [])]
    if land_cost is not None:
        land_cost = float(land_cost)
        line("land", "Land", land_cost, "$", None, "entered in the option's finance block", False)
    elif owner_type and any(owner_type == t or owner_type.startswith(t) for t in nominal_types):
        land_cost = float(land.get("nominal_value_cad") or 0)
        line("land", "Land", land_cost, "$", "f.land", f"nominal: the owner is a {owner_type.replace('_', ' ')} and the tenure plan is a long lease or a transfer", False)
    else:
        land_cost = None
        line("land", "Land", None, "$", "f.land", "not settled: enter the assessed value or the agreed price in the option's finance block", False)
        unsure.append("land cost (the owner is not a church, a society or a government, and no price is entered)")

    capital = round(hard + soft_cost + contingency + (land_cost or 0)) if hard else None
    line("capital", "Capital cost", capital, "$", None, "hard + soft + contingency + land", False)

    # ---------------- operating
    rents, ops = P("f.rents"), P("f.operating")
    mr = rents.get("market_rent_monthly_cad") or {}
    tiers = _tiers(option, n)
    chf = (E.get("bch.chf.eligibility") or {}).get("values") or {}
    limits = (E.get("bch.chf.eligibility") and _chf_limits(ledger)) or {}
    rev: dict[str, Any] = {"market": None, "rgi": None, "deep_subsidy": None}
    note_rent = []
    if n:
        # market rent by unit type where the table has it, else the all-units average, flagged
        def market_rent(k: str) -> tuple[float, bool]:
            v = mr.get(k)
            if v:
                return float(v), False
            return float(mr.get("all_units") or 0), True

        if tiers:
            share = {k: tiers[k] / n for k in TIER_KEYS}
        else:
            share = {"market": 1.0, "rgi": 0.0, "deep_subsidy": 0.0}
            unsure.append("rent tiers (no market / RGI / deep-subsidy split on the option: all units priced at market)")
        market_total = 0.0
        flagged = False
        rgi_total = 0.0
        for k, cnt in units.items():
            r, fl = market_rent(k)
            flagged = flagged or (fl and cnt > 0)
            market_total += cnt * share["market"] * r * 12
            limit = limits.get("two_bed_plus" if k in ("two_bed", "three_bed_plus") else "under_two_bed")
            rgi_rent = (limit or 0) * float(rents.get("rgi_income_share_of_chf_limit") or 0) * float(rents.get("rgi_rent_share_of_income") or 0) / 12
            rgi_total += cnt * share["rgi"] * rgi_rent * 12
        deep = float(rents.get("deep_subsidy_rent_monthly_cad") or 0)
        deep_total = n * share["deep_subsidy"] * deep * 12
        rev = {"market": round(market_total), "rgi": round(rgi_total), "deep_subsidy": round(deep_total)}
        if flagged:
            note_rent.append("some unit types priced at the CMHC all-units average: the table has no figure for them")
        if share["rgi"] and not limits:
            unsure.append("rent-geared-to-income rents (the Community Housing Fund's income limits are not in force on this date)")
    line("rev_market", "Market rent", rev["market"], "$/yr", "f.rents",
         f"CMHC {rents.get('survey', '')}, {int(round((tiers or {}).get('market', n) if tiers else n))} units" + ("; " + note_rent[0] if note_rent else ""), False)
    line("rev_rgi", "Rent-geared-to-income", rev["rgi"], "$/yr", "f.rents",
         f"30% of a household income taken at {float(rents.get('rgi_income_share_of_chf_limit') or 0) * 100:.0f}% of the fund's income limit (placeholder)", True)
    line("rev_deep", "Deep-subsidy rent", rev["deep_subsidy"], "$/yr", "f.rents", f"the shelter rate, ${rents.get('deep_subsidy_rent_monthly_cad')} a month", False)
    gross = sum(v for v in rev.values() if v) if n else None
    vac = float(rents.get("vacancy_rate") or 0)
    vacancy = round(gross * vac) if gross else None
    opx = round(n * float(ops.get("operating_cost_per_unit_year_cad") or 0)) if n else None
    reserve = round(n * float(ops.get("replacement_reserve_per_unit_year_cad") or 0)) if n else None
    noi = round(gross - vacancy - opx - reserve) if gross is not None else None
    line("vacancy", "Vacancy", vacancy, "$/yr", "f.rents", f"{vac * 100:.1f}% of gross rent, the CMHC survey's rate", False)
    line("opex", "Operating cost", opx, "$/yr", "f.operating", f"${ops.get('operating_cost_per_unit_year_cad'):,} per unit", is_placeholder("f.operating"))
    line("reserve", "Replacement reserve", reserve, "$/yr", "f.operating", f"${ops.get('replacement_reserve_per_unit_year_cad'):,} per unit", is_placeholder("f.operating"))
    line("noi", "Net operating income", noi, "$/yr", None, "gross rent less vacancy, operating cost and reserve", False)

    # ---------------- funding
    grants: list[dict] = []
    targets = set(option.get("target_programs") or [])
    if "bch.chf.eligibility" in E and (not targets or "bch.chf.eligibility" in targets) and n:
        per = float(chf.get("provisional_grant_per_unit_cad") or 0)
        g = round(per * n)
        grants.append({"program": "bch.chf.eligibility", "label": "Community Housing Fund provisional grant", "value": g, "note": f"${per:,.0f} per unit × {n} (2025-26 provisional; the program is between calls)"})
        line("grant_chf", "Community Housing Fund grant", g, "$", "bch.chf.eligibility", f"${per:,.0f} per unit × {n}; indicative, the fund is between calls", False)
    other = fin.get("other_grants_cad")
    if other:
        grants.append({"program": None, "label": "Other grants (entered)", "value": float(other), "note": "the option's finance block"})
        line("grant_other", "Other grants", float(other), "$", None, "entered in the option's finance block", False)
    equity = float(fin.get("equity_cad") or 0)
    line("equity", "Equity", equity, "$", None, "entered in the option's finance block" if fin.get("equity_cad") is not None else "none entered", False)

    mtg = P("f.mortgage")
    rate, years, dcr = float(mtg.get("rate_pct") or 0), int(mtg.get("amortization_years") or 40), float(mtg.get("debt_coverage_ratio") or 1.1)
    k = mortgage_constant(rate, years)
    debt = round(max(0.0, noi) / dcr / k) if noi is not None and k else None
    service = round(debt * k) if debt else None
    line("debt", "Supportable debt", debt, "$", "f.mortgage", f"NOI over a {dcr:.2f} coverage ratio, at {rate}% over {years} years (annual service ${service:,.0f})" if debt is not None else "no net operating income to carry debt", False)
    funding = round(sum(g["value"] for g in grants) + equity + (debt or 0)) if capital is not None else None
    line("funding", "Funding", funding, "$", None, "grants + equity + supportable debt", False)

    gap = round(capital - funding) if capital is not None and funding is not None else None
    gap_share = round(gap / capital, 3) if gap is not None and capital else None
    line("gap", "Gap", gap, "$", None, "capital cost less funding; a negative gap is headroom", False)

    # ---------------- the verdict
    if capital is None:
        word = "unsure"
        why.append("no floor area, so no capital cost")
        unsure.insert(0, "floor area and unit count")
    elif land_cost is None:
        word = "unsure"
        why.append("the land cost is not settled")
    elif gap <= 0:
        word = "likely"
        why.append(f"the funding stack covers the capital cost with ${-gap:,.0f} to spare")
    elif gap_share is not None and gap_share > GAP_UNLIKELY_SHARE:
        word = "unlikely"
        why.append(f"the gap is ${gap:,.0f}, {gap_share * 100:.0f}% of the capital cost, more than the {GAP_UNLIKELY_SHARE * 100:.0f}% a feasibility screen can call close")
    else:
        word = "unsure"
        why.append(f"the gap is ${gap:,.0f}, {gap_share * 100:.0f}% of the capital cost: close enough to turn on the placeholders")
    placeholders = [l["label"] for l in lines if l["placeholder"]]
    if placeholders:
        why.append("placeholders in use: " + ", ".join(placeholders))

    return {
        "grade": "feasibility", "available": True,
        "inputs": {"units": units, "units_total": n, "gfa_m2": gfa or None, "rent_tiers_units": tiers, "finance": fin},
        "capital": {"hard": hard, "escalation": factor, "soft": soft_cost, "contingency": contingency, "land": land_cost, "total": capital},
        "operating": {"revenue": rev, "gross": gross, "vacancy": vacancy, "operating_cost": opx, "reserve": reserve, "noi": noi},
        "funding": {"grants": grants, "equity": equity, "debt": {"supportable": debt, "rate_pct": rate, "amortization_years": years, "dcr": dcr, "annual_service": service}, "total": funding},
        "gap": {"value": gap, "share_of_capital": gap_share},
        "verdict": {"word": word, "why": why, "unsure": unsure},
        "lines": lines,
        "as_of": ledger.get("run", {}).get("as_of"), "stamp": ledger.get("run", {}).get("stamp", {}).get("stamp"),
    }


BCPI_PUBLISHING_LAG_DAYS = 120   # a quarter's index is released about four months after the quarter begins


def _published_cutoff(as_of: str) -> str:
    """The latest quarter start whose index was published by the run date."""
    from datetime import date, timedelta
    try:
        return (date.fromisoformat(as_of) - timedelta(days=BCPI_PUBLISHING_LAG_DAYS)).isoformat()
    except ValueError:
        return as_of


def _observations(ledger: dict, rule_id: str) -> dict[str, float]:
    """The index series of a layer F rule, {period: value}. The ledger keeps the observations out of the values
    (they are long), so they come from the rule version in force on the run date; a ledger that carries them
    itself (a test, a browser run that embedded them) is read first."""
    for r in ledger.get("results", []):
        if r.get("rule_id") == rule_id:
            obs = (r.get("values") or {}).get("observations") or r.get("observations")
            if obs:
                return {k: float(v) for k, v in obs.items()}
    try:
        from .rules_loader import RULES_DIR, load_rules
        from datetime import date
        on = date.fromisoformat(ledger["run"]["as_of"])
        for rule in load_rules(RULES_DIR):
            if rule.id == rule_id:
                v = rule.version_on(on)
                obs = (v.params if v else {}).get("observations") or {}
                return {k: float(x) for k, x in obs.items()}
    except Exception:
        return {}
    return {}


def _chf_limits(ledger: dict) -> dict[str, float]:
    """The Community Housing Fund's low-to-moderate income limits, from the ledger's rule params where the check
    carried them, else from the rule file in force on the run date."""
    try:
        from .rules_loader import RULES_DIR, load_rules
        from datetime import date
        on = date.fromisoformat(ledger["run"]["as_of"])
        for rule in load_rules(RULES_DIR):
            if rule.id == "bch.chf.eligibility":
                v = rule.version_on(on)
                lim = (v.params if v else {}).get("low_moderate_income_limits_cad") or {}
                return {k: float(x) for k, x in lim.items() if isinstance(x, (int, float))}
    except Exception:
        pass
    return {}


def markdown(pf: dict) -> list[str]:
    """The memo's pro-forma section: four lines, the verdict, then every line with its source."""
    L: list[str] = []
    if not pf or not pf.get("available"):
        L.append("## 4. Does the money work?")
        L.append(f"Not computed: {pf.get('why') if pf else 'no pro-forma'}.")
        L.append("")
        return L
    v = pf["verdict"]
    c, o, f, g = pf["capital"], pf["operating"], pf["funding"], pf["gap"]
    L.append("## 4. Does the money work? (feasibility grade)")
    L.append(f"**{v['word'].capitalize()}.** " + " ".join(w[0].upper() + w[1:] + "." for w in v["why"]))
    L.append("")
    L.append(f"- Capital cost **{_money(c['total'])}**: hard {_money(c['hard'])} (escalated ×{c['escalation']}), soft {_money(c['soft'])}, contingency {_money(c['contingency'])}, land {_money(c['land'])}.")
    L.append(f"- Net operating income **{_money(o['noi'])} a year**: rent {_money(o['gross'])} less vacancy {_money(o['vacancy'])}, operating cost {_money(o['operating_cost'])} and reserve {_money(o['reserve'])}.")
    L.append(f"- Funding **{_money(f['total'])}**: grants {_money(sum(x['value'] for x in f['grants']))}, equity {_money(f['equity'])}, supportable debt {_money(f['debt']['supportable'])} at {f['debt']['rate_pct']}% over {f['debt']['amortization_years']} years, {f['debt']['dcr']:.2f} coverage.")
    L.append(f"- Gap **{_money(g['value'])}**" + (f" ({g['share_of_capital'] * 100:.0f}% of the capital cost)" if g.get("share_of_capital") is not None else "") + ".")
    if v["unsure"]:
        L.append("- Left to a person: " + "; ".join(v["unsure"]) + ".")
    L.append("")
    L.append("| Line | Figure | From | Note |")
    L.append("|---|---|---|---|")
    for ln in pf["lines"]:
        val = ln["value"]
        if ln["unit"] in ("$", "$/yr", "$/m²"):
            shown = _money(val) + ("" if ln["unit"] == "$" else (" a year" if ln["unit"] == "$/yr" else " per m²"))
        elif ln["unit"] == "×":
            shown = f"×{val}" if val is not None else "not given"
        else:
            shown = str(val) if val is not None else "not given"
        src = f"`{ln['rule_id']}`" if ln["rule_id"] else "the option"
        L.append(f"| {ln['label']} | {shown} | {src}{' (placeholder)' if ln['placeholder'] else ''} | {ln['note']} |")
    L.append("")
    L.append("> A feasibility screen, not a lender's model: hard costs from a Class D catalogue estimate escalated by the Statistics Canada index, rents from the CMHC survey, debt at the posted five-year rate under CMHC's coverage ratio. Placeholders are marked; replace them with the project's own budget before anyone relies on the gap.")
    L.append("")
    return L


def _money(x: Any) -> str:
    if x is None:
        return "not given"
    return f"${x:,.0f}"
