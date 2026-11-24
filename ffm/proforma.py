"""The feasibility-grade pro-forma: arithmetic over layer F (assumptions) and layer E (the programs), read from
the ledger so the version in force on the run date is the one used and the memo's stamp covers it.

    build(site, option, ledger) -> {
        "grade": "feasibility",                      not a lender's model, and the memo says so
        "capital":   hard, escalation, soft, contingency, land, total
        "operating": revenue by tier, vacancy, operating cost, reserve, net operating income
        "funding":   grants (from layer E), equity, supportable debt (NOI at the DCR), total
        "gap":       capital less funding, and as a share of capital
        "verdict":   {"word": "likely" | "unlikely" | "unsure", "why": [...], "unsure": [...]}   (worded by VERDICT_WORDS)
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
# how the memo says what the 15% is (20 Nov 2026, a reviewer read it as a funder's threshold)
SCREEN_LINE = f"the {GAP_UNLIKELY_SHARE * 100:.0f}% line (this tool's screening line, not a funder's rule)"

# How the memo words each verdict (17 Nov 2026, Kai: "Unlikely" read as "will not be funded"; a gap past the screen's
# line is the development manager's cue to look for more sources). The key in proforma.json stays "unlikely", so the
# committed runs read the same; only the words a person sees change. The tool mirrors these in memo/answers.js.
VERDICT_WORDS = {"likely": "Likely", "unlikely": "Needs more sources", "unsure": "Unsure"}
# Written for whoever reads the memo, on screen or on paper (24 Nov 2026: "run again" and "at 03" were the tool's
# operator talking to a board).
MORE_SOURCES = ("Look for more sources as well: other grants (CMHC's Affordable Housing Fund among them), more equity, "
                "a land contribution or a partner. A revised memo counts what is found as other grants or equity.")
CLOSE_GAP = "Another source, or firmer figures for the placeholders, would settle it."
OPERATING_FUNDER = ("Find who pays to run it before the capital: an operating agreement or subsidy (for supportive, transitional or "
                    "shelter housing, the staffing as well), then a revised memo with the project's own rents, running costs and "
                    "subsidy. Until they are entered, the rents and the running cost are placeholders.")


def next_step(pf: dict) -> str | None:
    """What the verdict asks of the development manager: more sources for a gap past the screen's line; another
    source or firmer placeholders for a gap inside it; nothing when the stack covers the cost, or when a figure is
    missing (the memo's "Left to a person" names that one)."""
    v = (pf or {}).get("verdict") or {}
    gap, cap = ((pf or {}).get("gap") or {}).get("value"), (pf or {}).get("capital") or {}
    homes = ((pf or {}).get("inputs") or {}).get("units_total")
    if v.get("operating_shortfall"):
        return OPERATING_FUNDER
    if v.get("word") == "unlikely":
        return MORE_SOURCES
    if v.get("word") == "unsure" and homes and gap is not None and gap > 0 and cap.get("total") is not None and cap.get("land") is not None:
        return CLOSE_GAP
    return None


def _refs(ledger: dict) -> dict[str, str]:
    """The memo's references (A1 … F7), as engine.memo_refs and the page's memoRefs (ffm/ui/memo/memo.js) number them,
    so a line note's "F3" is the row the reader finds."""
    from .engine import memo_refs   # imported here: the engine module is the larger one, and this keeps the import light
    return memo_refs(ledger.get("results", []))


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


def build(site: dict, option: dict, ledger: dict, massing: dict | None = None) -> dict[str, Any]:
    """The pro-forma. With the run's `massing`, a floor area the option leaves blank is taken from the proposed mass
    (plate × storeys) and every line that uses it says so (15 Nov 2026: before, FIG 02 stated a floor area while
    answer 4 said there was none)."""
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
    gfa_from = "the option"
    if not gfa and massing and option.get("storeys"):
        proposed = next((x for x in (massing.get("masses") or []) if x.get("name") == "proposed"), None)
        if proposed and proposed.get("gfa_m2"):
            gfa = float(proposed["gfa_m2"])
            gfa_from = "the massing"
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
    # The project's own cost a square metre (`finance.hard_cost_per_m2_cad`, a cost consultant's figure) stands over the
    # catalogue base and is not escalated: it is already today's. Without one, a building the base was not written for
    # says so where the cost is read (23 Nov 2026: a 2- to 4-unit wood-frame figure priced an 11-storey concrete
    # building with four floors of community space, and landed near the public cost by coincidence).
    own_rate = fin.get("hard_cost_per_m2_cad")
    own_rate = float(own_rate) if isinstance(own_rate, (int, float)) and not isinstance(own_rate, bool) and own_rate > 0 else None
    storeys_n = int(option.get("storeys") or 0)
    nonres_m2 = float(option.get("non_residential_gfa_m2") or 0)
    # the floors that are not homes (community services, childcare, shops) at their own cost, with their own income
    # and their own money, where the manager has them (23 Nov 2026: four floors of community space were costed as
    # apartments, earned nothing, and the capital campaign that pays for such floors had no line)
    num = lambda k: float(fin[k]) if isinstance(fin.get(k), (int, float)) and not isinstance(fin.get(k), bool) and fin[k] > 0 else None
    nr_rate, nr_income, nr_funding = num("non_residential_cost_per_m2_cad"), num("non_residential_income_cad_year"), num("non_residential_funding_cad")
    nonres_m2 = min(nonres_m2, gfa) if gfa else nonres_m2
    outside_base = []
    if own_rate is None and gfa:
        if storeys_n > 6:
            outside_base.append(f"{storeys_n} storeys, above the six a wood frame reaches")
        if nonres_m2 and nr_rate is None:
            outside_base.append(f"{nonres_m2:,.0f} m² that is not homes, priced as if it were")
    if own_rate is not None:
        rate_m2, factor = own_rate, 1.0
    hard = round(gfa * rate_m2 * factor) if gfa else None
    hard_nonres = None
    if gfa and nonres_m2 and nr_rate is not None:
        hard_nonres = round(nonres_m2 * nr_rate)
        hard = round((gfa - nonres_m2) * rate_m2 * factor) + hard_nonres
    if outside_base:
        unsure.append("a hard cost for this building (" + "; ".join(outside_base) + "): the base is a small wood-frame catalogue figure, so enter a cost consultant's rate a square metre")
    line("hard_rate", "Hard cost base", rate_m2, "$/m²", None if own_rate is not None else "f.hard_cost_base",
         "entered: the project's own cost a square metre (the option's finance block), not escalated" if own_rate is not None
         else f"{hc.get('basis', '')}".split(";")[0] + ("; NOT written for this building: " + "; ".join(outside_base) if outside_base else ""), False)
    newest_period = max(obs) if obs else None
    newest = float(obs[newest_period]) if newest_period else None
    line("escalation", "Escalation to the index in force on the run date", factor, "×", "f.escalation_bcpi",
         (f"BCPI {latest} ({latest_period}, the last quarter published {BCPI_PUBLISHING_LAG_DAYS} days before the run date {as_of}) over {base_index} ({base_period})"
          + (f"; the rule's newest observation is {newest} ({newest_period}), published after that date" if newest_period and newest_period != latest_period else ""))
         if base_index and latest else "index not on file for this date: no escalation applied")
    line("hard", "Hard cost", hard, "$", None if own_rate is not None else "f.hard_cost_base",
         (f"{gfa:,.0f} m² × ${rate_m2:,.0f} × {factor}" + (" (floor area from the massing: the plate × the storeys, since the option gives none)" if gfa_from == "the massing" else "")) if gfa else "no floor area")
    if hard_nonres is not None:
        line("hard_nonres", "Of which, the floors that are not homes", hard_nonres, "$", None,
             f"entered: {nonres_m2:,.0f} m² × ${nr_rate:,.0f} a square metre (the option's finance block), not escalated; the homes' floors at the rate above", False)
    s_share, c_share = float(soft.get("soft_cost_share_of_hard") or 0), float(soft.get("contingency_share_of_hard") or 0)
    soft_cost = round(hard * s_share) if hard else None
    contingency = round(hard * c_share) if hard else None
    line("soft", "Soft costs", soft_cost, "$", "f.soft_costs", f"{s_share * 100:.0f}% of hard cost", is_placeholder("f.soft_costs"))
    line("contingency", "Contingency", contingency, "$", "f.soft_costs", f"{c_share * 100:.0f}% of hard cost", is_placeholder("f.soft_costs"))

    land_cost = fin.get("land_cost_cad")
    owner_type = str(site.get("owner_type") or "").lower().replace(" ", "_")
    nominal_types = [str(t).lower() for t in (land.get("nominal_lease_owner_types") or [])]
    ref = _refs(ledger)
    if land_cost is not None:
        land_cost = float(land_cost)
        line("land", "Land", land_cost, "$", None, "entered in the option's finance block", False)
    elif owner_type and any(owner_type == t or owner_type.startswith(t) for t in nominal_types):
        land_cost = float(land.get("nominal_value_cad") or 0)
        # why the land is $0, in words (20 Nov 2026: a reviewer read "$0" as a missing figure)
        line("land", "Land", land_cost, "$", "f.land",
             f"nominal: the owner is a {owner_type.replace('_', ' ')}, and this screen carries the land of a church, a society or a government "
             f"at ${land_cost:,.0f} on a long lease or a transfer ({ref.get('f.land', 'f.land')})", False)
    else:
        land_cost = None
        line("land", "Land", None, "$", "f.land", "not settled: enter the assessed value or the agreed price in the option's finance block", False)
        unsure.append("land cost (the owner is not a church, a society or a government, and no price is entered)")

    capital = round(hard + soft_cost + contingency + (land_cost or 0)) if hard else None
    line("capital", "Capital cost", capital, "$", None, "hard + soft + contingency + land" + ("; no land price yet, so this is the cost before land" if land_cost is None else ""), False)

    # ---------------- operating
    rents, ops = P("f.rents"), P("f.operating")
    mr = rents.get("market_rent_monthly_cad") or {}
    tiers = _tiers(option, n)
    chf = (E.get("bch.chf.eligibility") or {}).get("values") or {}
    limits = (E.get("bch.chf.eligibility") and _chf_limits(ledger)) or {}
    rev: dict[str, Any] = {"market": None, "rgi": None, "deep_subsidy": None}
    note_rent = []
    # Rents by BC Housing's own estimating method (`f.rgi_rents`, read from the Housing Income Limits and the fund's call
    # documents on 23 Nov 2026): they stand over the declared placeholder (half the fund's income limit) wherever that
    # rule is in force on the run date (from 1 Dec 2025, so on every date the rent table itself is in force).
    rg = P("f.rgi_rents")
    hil_rgi = {k: v for k, v in (rg.get("rgi_rent_monthly_cad") or {}).items() if v}
    hil_deep_month = {k: v for k, v in (rg.get("deep_subsidy_rent_monthly_cad") or {}).items() if v} if isinstance(rg.get("deep_subsidy_rent_monthly_cad"), dict) else {}
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
        deep_total = 0.0
        deep_flat = float(rents.get("deep_subsidy_rent_monthly_cad") or 0) * 12
        hil_deep = {k: float(v) * 12 for k, v in hil_deep_month.items()}
        for k, cnt in units.items():
            r, fl = market_rent(k)
            flagged = flagged or (fl and cnt > 0)
            market_total += cnt * share["market"] * r * 12
            limit = limits.get("two_bed_plus" if k in ("two_bed", "three_bed_plus") else "under_two_bed")
            rgi_rent = (limit or 0) * float(rents.get("rgi_income_share_of_chf_limit") or 0) * float(rents.get("rgi_rent_share_of_income") or 0) / 12
            if k in hil_rgi:                       # BC Housing's own estimate, where the Housing Income Limits are in force
                rgi_rent = float(hil_rgi[k])
            rgi_total += cnt * share["rgi"] * rgi_rent * 12
            deep_total += cnt * share["deep_subsidy"] * float(hil_deep.get(k, deep_flat))
        rev = {"market": round(market_total), "rgi": round(rgi_total), "deep_subsidy": round(deep_total)}
        if flagged:
            note_rent.append("some unit types priced at the CMHC all-units average: the table has no figure for them")
        if share["rgi"] and not limits and not hil_rgi:
            unsure.append("rent-geared-to-income rents (the Community Housing Fund's income limits are not in force on this date)")
    # The operator's own figures (`option.operations`, 23 Nov 2026: three of four simulated reviewers asked for an
    # operating page; the rents and the running cost were placeholders nobody could replace, and supportive housing had
    # no staffing or subsidy line at all). A figure entered stands over the layer F placeholder and the line says so;
    # nothing is invented where none is entered.
    opsin = option.get("operations") or {}

    def entered(key: str) -> float | None:
        v = opsin.get(key)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    tier_homes = {k: (tiers or {}).get(k, 0) for k in TIER_KEYS} if tiers else {"market": n, "rgi": 0, "deep_subsidy": 0}
    tier_from = {"market": "rule", "rgi": "rule" if hil_rgi else "placeholder", "deep_subsidy": "rule"}
    for k, key in (("market", "rent_market_monthly_cad"), ("rgi", "rent_rgi_monthly_cad"), ("deep_subsidy", "rent_deep_monthly_cad")):
        own = entered(key)
        if own is not None and n:
            rev[k] = round(tier_homes[k] * own * 12)
            tier_from[k] = "entered"
    said = lambda k, key, otherwise: (f"entered: ${entered(key):,.0f} a month × {tier_homes[k]:g} homes (the option's operating figures)"
                                      if tier_from[k] == "entered" else otherwise)
    line("rev_market", "Market rent", rev["market"], "$/yr", None if tier_from["market"] == "entered" else "f.rents",
         said("market", "rent_market_monthly_cad", f"CMHC {rents.get('survey', '')}, {int(round((tiers or {}).get('market', n) if tiers else n))} units" + ("; " + note_rent[0] if note_rent else "")), False)
    hil_note = (f"30% of an income of {float(rg.get('rgi_income_share_of_hil') or 0) * 100:.0f}% of the Housing Income Limit ({rg.get('hils_area', '')}), the way BC Housing's call documents "
                f"estimate it: ${hil_rgi.get('one_bed', 0):,.0f} a month for one bedroom or less, ${hil_rgi.get('two_bed', 0):,.0f} for two, ${hil_rgi.get('three_bed_plus', 0):,.0f} for three; "
                "an estimate, so enter the operator's own rent when there is one") if hil_rgi else ""
    line("rev_rgi", "Rent-geared-to-income", rev["rgi"], "$/yr", None if tier_from["rgi"] == "entered" else ("f.rgi_rents" if hil_rgi else "f.rents"),
         said("rgi", "rent_rgi_monthly_cad", hil_note or f"30% of a household income taken at {float(rents.get('rgi_income_share_of_chf_limit') or 0) * 100:.0f}% of the fund's low- and moderate-income limit (placeholder; "
                                             "the fund's income-geared tenants are under the Housing Income Limits, which are lower, so enter the operator's own rent)"),
         tier_from["rgi"] == "placeholder")
    line("rev_deep", "Deep-subsidy rent", rev["deep_subsidy"], "$/yr", None if tier_from["deep_subsidy"] == "entered" else ("f.rgi_rents" if hil_deep_month else "f.rents"),
         said("deep_subsidy", "rent_deep_monthly_cad",
              (f"the income assistance shelter allowance, ${hil_deep_month.get('one_bed', 0):,.0f} a month for one bedroom or less and ${hil_deep_month.get('two_bed', 0):,.0f} for two; "
               f"${hil_deep_month.get('three_bed_plus', 0):,.0f} for three, 30% of the deep-subsidy income limit") if hil_deep_month
              else f"the shelter rate, ${rents.get('deep_subsidy_rent_monthly_cad')} a month"), False)
    gross = sum(v for v in rev.values() if v) if n else None
    vac = float(rents.get("vacancy_rate") or 0)
    vacancy = round(gross * vac) if gross is not None else None      # a rent of $0 (a shelter) is a figure, not a blank
    own_opx = entered("operating_cost_per_unit_year_cad")
    per_opx = own_opx if own_opx is not None else float(ops.get("operating_cost_per_unit_year_cad") or 0)
    opx = round(n * per_opx) if n else None
    reserve = round(n * float(ops.get("replacement_reserve_per_unit_year_cad") or 0)) if n else None
    # support staffing: the cost that decides whether supportive, transitional or shelter housing can open. Entered or
    # absent, never assumed; where that kind of housing has none entered, the verdict below cannot read "likely".
    staffing = round(entered("support_staffing_cad_year")) if entered("support_staffing_cad_year") is not None and n else None
    from .checks import housing_kind, HOUSING_WORDS
    kind = housing_kind(option)
    staffing_missing = bool(n) and kind != "independent" and staffing is None
    noi = round(gross - vacancy - opx - reserve - (staffing or 0) + (nr_income or 0)) if gross is not None else None
    if nr_income:
        line("nonres_income", "Income from the floors that are not homes", round(nr_income), "$/yr", None, "entered: rent or a contribution to running costs from the non-residential space (the option's finance block)", False)
    # an operating subsidy, as the manager has it: counted toward what a lender would lend against only once confirmed
    subsidy = round(entered("operating_subsidy_cad_year")) if entered("operating_subsidy_cad_year") is not None and n else None
    subsidy_confirmed = bool(subsidy) and opsin.get("subsidy_confirmed") is True
    line("vacancy", "Vacancy", vacancy, "$/yr", "f.rents", f"{vac * 100:.1f}% of gross rent, the CMHC survey's rate", False)
    line("opex", "Operating cost", opx, "$/yr", None if own_opx is not None else "f.operating",
         f"entered: ${per_opx:,.0f} per home a year (the option's operating figures)" if own_opx is not None else f"${ops.get('operating_cost_per_unit_year_cad'):,} per unit",
         own_opx is None and is_placeholder("f.operating"))
    line("reserve", "Replacement reserve", reserve, "$/yr", "f.operating", f"${ops.get('replacement_reserve_per_unit_year_cad'):,} per unit", is_placeholder("f.operating"))
    line("staffing", "Support staffing", staffing, "$/yr", None,
         "entered in the option's operating figures" if staffing is not None else
         (f"not entered: {HOUSING_WORDS[kind]} runs on staffing this screen does not estimate" if staffing_missing else "none entered"), False)
    line("noi", "Net operating income", noi, "$/yr", None, "gross rent less vacancy, operating cost, reserve and support staffing, before any operating subsidy", False)
    line("subsidy", "Operating subsidy", subsidy, "$/yr", None,
         (f"entered{': ' + str(opsin.get('subsidy_source')) if opsin.get('subsidy_source') else ''}; "
          + ("confirmed, so a lender's loan is sized with it" if subsidy_confirmed else "not yet confirmed, so no loan is sized on it")) if subsidy else "none entered", False)

    # ---------------- funding
    grants: list[dict] = []
    targets = set(option.get("target_programs") or [])
    # A program's grant is counted only where the option does not fail the program (23 Nov 2026, three simulated user
    # tests: a memo said "does not meet the criteria" in answer 2 and counted the fund's $17.6M in answer 4). A fail or a
    # not-applicable counts nothing and the line says what the figure would have been; a pass or a not-yet-confirmed is
    # counted as illustrative, and the verdict below says when it leans on a fund with no open intake.
    not_counted: list[dict] = []
    chf_grant = None
    if "bch.chf.eligibility" in E and (not targets or "bch.chf.eligibility" in targets) and n:
        per = float(chf.get("provisional_grant_per_unit_cad") or 0)
        g = round(per * n)
        chf_res = E.get("bch.chf.eligibility") or {}
        chf_status = chf_res.get("status")
        intake_open = ((chf_res.get("values") or {}).get("intake") or {}).get("open")
        if chf_status in ("fail", "not_applicable"):
            reason = ("the option does not meet the fund's criteria (answer 2)" if chf_status == "fail"
                      else "the fund is not the program for this kind of housing (answer 2)")
            not_counted.append({"program": "bch.chf.eligibility", "label": "Community Housing Fund grant", "value": g, "why": reason})
            line("grant_chf", "Community Housing Fund grant", 0, "$", "bch.chf.eligibility",
                 f"not counted: {reason}; ${per:,.0f} per unit × {n} = ${g:,.0f} is what the 2025-26 provisional rate would give if it did", False)
        else:
            chf_grant = {"value": g, "confirmed": chf_status == "pass", "intake_open": intake_open}
            cond = "" if chf_status == "pass" else "; counted on the condition that the criteria still to confirm are met (answer 2)"
            closed = "; no intake is open, so no grant is committed or implied" if intake_open is False else ""
            grants.append({"program": "bch.chf.eligibility", "label": "Community Housing Fund grant (illustrative)", "value": g,
                           "illustrative": True, "confirmed": chf_status == "pass", "intake_open": intake_open,
                           "note": f"${per:,.0f} per unit × {n} (2025-26 provisional rate, from a call that did not proceed){cond}{closed}"})
            line("grant_chf", "Community Housing Fund grant", g, "$", "bch.chf.eligibility",
                 f"${per:,.0f} per unit × {n}; illustrative, at the 2025-26 provisional rate{cond}{closed}", False)
    if nr_funding:
        grants.append({"program": None, "label": "Money for the floors that are not homes (entered)", "value": nr_funding, "note": "a capital campaign, a grant or a partner's contribution (the option's finance block)"})
        line("nonres_funding", "Money for the floors that are not homes", nr_funding, "$", None, "entered: a capital campaign, a grant or a partner's contribution toward the non-residential space", False)
    other = fin.get("other_grants_cad")
    if other:
        grants.append({"program": None, "label": "Other grants (entered)", "value": float(other), "note": "the option's finance block"})
        line("grant_other", "Other grants", float(other), "$", None, "entered in the option's finance block", False)
    equity = float(fin.get("equity_cad") or 0)
    line("equity", "Equity", equity, "$", None, "entered in the option's finance block" if fin.get("equity_cad") is not None else "none entered", False)

    mtg = P("f.mortgage")
    rate, years, dcr = float(mtg.get("rate_pct") or 0), int(mtg.get("amortization_years") or 40), float(mtg.get("debt_coverage_ratio") or 1.1)
    k = mortgage_constant(rate, years)
    noi_for_debt = (noi + (subsidy if subsidy_confirmed else 0)) if noi is not None else None
    debt = round(max(0.0, noi_for_debt) / dcr / k) if noi_for_debt is not None and k else None
    service = round(debt * k) if debt else None
    # the debt in plain words (20 Nov 2026): what the coverage ratio and the amortization mean, not only their figures
    line("debt", "Supportable debt", debt, "$", "f.mortgage",
         (f"the largest loan the net operating income carries: the lender wants net income {dcr:.2f} times the loan payment "
          f"(the debt coverage ratio), at {rate}% repaid over {years} years (the amortization), ${service or 0:,.0f} a year in payments")
         if debt is not None else "no net operating income to carry debt", False)
    funding = round(sum(g["value"] for g in grants) + equity + (debt or 0)) if capital is not None else None
    line("funding", "Funding", funding, "$", None, "grants + equity + supportable debt", False)

    gap = round(capital - funding) if capital is not None and funding is not None else None
    gap_share = round(gap / capital, 3) if gap is not None and capital else None
    line("gap", "Gap", gap, "$", None, f"capital cost less funding; a negative gap is headroom, and a gap above {SCREEN_LINE} "
         "of the capital cost reads Needs more sources", False)

    # ---------------- the verdict
    if capital is None:
        word = "unsure"
        why.append("no floor area, so no capital cost")
        unsure.insert(0, "floor area and unit count")
    elif not n:
        # no homes entered: no rent, no debt and no grant can be counted, so the gap is the whole capital cost and
        # says nothing about the funders (17 Nov 2026: Expo as permitted read a 100% gap as a verdict)
        word = "unsure"
        why.append(f"the option has no homes entered, so there is no rent, debt or grant to set against the ${capital:,.0f} capital cost")
        unsure.insert(0, "the unit mix (homes by type: studio, one-, two- and three-bedroom)")
    elif land_cost is None and gap_share is not None and gap_share > GAP_UNLIKELY_SHARE:
        # a land price can only add to the cost: a gap already past the line before it is past the line (20 Nov 2026:
        # it read "unsure: the land cost is not settled" with a 49% gap)
        word = "unlikely"
        why.append(f"the gap is ${gap:,.0f}, {gap_share * 100:.0f}% of the cost before any land price, more than {SCREEN_LINE}; a land price would only widen it")
    elif land_cost is None:
        word = "unsure"
        why.append("the land cost is not settled" + (f": before any land price the gap is ${gap:,.0f}, {gap_share * 100:.0f}% of the cost" if gap and gap > 0 and gap_share is not None
                                                    else f": before any land price the funding covers the cost with ${-gap:,.0f} to spare" if gap is not None else ""))
    elif gap <= 0:
        word = "likely"
        why.append(f"the funding stack covers the capital cost with ${-gap:,.0f} to spare")
    elif gap_share is not None and gap_share > GAP_UNLIKELY_SHARE:
        word = "unlikely"
        why.append(f"the gap is ${gap:,.0f}, {gap_share * 100:.0f}% of the capital cost, more than {SCREEN_LINE}")
    else:
        word = "unsure"
        why.append(f"the gap is ${gap:,.0f}, {gap_share * 100:.0f}% of the capital cost, inside {SCREEN_LINE}: close enough to turn on the placeholders")
    # A stack that covers the cost only with a grant nobody has offered is not "likely" (23 Nov 2026): where the fund
    # has no open intake, or its criteria are not yet confirmed, and the cost is not covered without it, the verdict
    # is unsure and says how much rests on the grant.
    if word == "likely" and chf_grant and (chf_grant["intake_open"] is False or not chf_grant["confirmed"]) and gap + chf_grant["value"] > 0:
        word = "unsure"
        because = "a fund with no open intake" if chf_grant["intake_open"] is False else "a fund whose criteria are not yet confirmed"
        why[-1] = (f"the funding covers the capital cost only with an illustrative Community Housing Fund grant of ${chf_grant['value']:,.0f}, from {because}; "
                   f"without it the gap is ${gap + chf_grant['value']:,.0f}")
    # Rents that do not cover the running costs: no capital stack makes that building likely (23 Nov 2026: a shelter
    # entered as built read "Likely, $12.6M to spare" over a net operating income of -$52,880 a year).
    # The operating page (23 Nov 2026): what runs the building each year, the subsidy it needs to break even before any
    # loan, and, as an illustration only, the subsidy it would need if the capital still missing were borrowed on layer
    # F's mortgage terms. A funder's own financing terms differ; the figure is this screen's arithmetic, per home per
    # month, so two options can be compared.
    after_subsidy = (noi + (subsidy or 0)) if noi is not None else None
    to_run = max(0, -noi) if noi is not None else None
    financed = None
    if noi is not None and gap is not None and gap > 0 and k and n:
        loan = (debt or 0) + max(0, gap)
        pay = round(loan * k)
        need = max(0, pay - noi)
        financed = {"loan": loan, "annual_payment": pay, "subsidy_year": need, "per_home_month": round(need / n / 12),
                    "rate_pct": rate, "amortization_years": years}
        # the same loan on a program's own published terms, where the option is in that program and the rule carries them
        # (BC Builds' take-out financing, read from its page): a funder-side reader said debt on market terms is not the
        # number a program uses. The year's rate is the run's; a year past the table takes its last.
        bcb = E.get("bc.bcbuilds.eligibility") or {}
        terms = (bcb.get("values") or {}).get("takeout_financing")
        if terms and bcb.get("status") in ("pass", "uncertain", "conditional") and (not targets or "bc.bcbuilds.eligibility" in targets):
            table = terms.get("rate_pct") or {}
            yr = str(ledger.get("run", {}).get("as_of") or "")[:4]
            r2 = table.get(yr) or (table[max(table)] if table else None)
            if r2:
                k2 = mortgage_constant(float(r2), int(terms.get("amortization_years") or 35))
                pay2 = round(loan * k2)
                need2 = max(0, pay2 - noi)
                financed["on_program_terms"] = {"program": "BC Builds", "rule_id": "bc.bcbuilds.eligibility", "rate_pct": float(r2), "amortization_years": int(terms.get("amortization_years") or 35),
                                                "annual_payment": pay2, "subsidy_year": need2, "per_home_month": round(need2 / n / 12)}
    page = {
        "housing_type": kind,
        "tiers": [{"key": t, "label": {"market": "Market rent", "rgi": "Rent geared to income", "deep_subsidy": "Deep subsidy"}[t], "homes": tier_homes[t],
                   "rent_year": rev[t], "rent_month_per_home": round(rev[t] / tier_homes[t] / 12) if rev[t] is not None and tier_homes[t] else None,
                   "from": tier_from[t]} for t in TIER_KEYS] if n else [],
        "gross": gross, "vacancy": vacancy, "operating_cost": opx, "operating_cost_per_home": round(per_opx) if n else None,
        "operating_cost_from": "entered" if own_opx is not None else ("placeholder" if is_placeholder("f.operating") else "rule"),
        "reserve": reserve, "support_staffing": staffing, "staffing_missing": staffing_missing,
        "net_before_subsidy": noi, "subsidy": subsidy, "subsidy_confirmed": subsidy_confirmed, "subsidy_source": opsin.get("subsidy_source") or None,
        "net_after_subsidy": after_subsidy, "debt_service": service,
        "after_debt_service": (noi_for_debt - (service or 0)) if noi_for_debt is not None else None,
        "subsidy_to_run": to_run, "subsidy_to_run_per_home_month": round(to_run / n / 12) if to_run is not None and n else None,
        "if_gap_financed": financed,
    }
    # a shelter or shared rooms counted in beds as well as homes: the subsidy a bed a month, beside the one a home
    beds = option.get("beds")
    if isinstance(beds, (int, float)) and not isinstance(beds, bool) and beds > 0:
        page["beds"] = int(beds)
        page["subsidy_to_run_per_bed_month"] = round(to_run / beds / 12) if to_run is not None else None
    # Rents and subsidy that do not cover the running costs: no capital stack makes that building likely (a shelter
    # entered as built read "Likely, $12.6M to spare" over a net operating income of -$52,880 a year).
    operating_shortfall = -after_subsidy if (after_subsidy is not None and after_subsidy < 0 and n) else None
    if operating_shortfall:
        word = "unlikely"
        why.insert(0, f"the rents do not cover the running costs: the building is ${operating_shortfall:,.0f} a year short before any loan payment"
                      + ("" if staffing is not None else " or support staffing") + (f", after the ${subsidy:,.0f} operating subsidy entered" if subsidy else "")
                      + ", so it needs an operating funder whatever the capital stack shows")
    elif subsidy and not subsidy_confirmed and noi is not None and noi < 0:
        # the running costs are met only by a subsidy nobody has confirmed: said, and never "likely"
        why.append(f"the running costs are covered only with an operating subsidy of ${subsidy:,.0f} a year that is not yet confirmed")
        if word == "likely":
            word = "unsure"
    if staffing_missing:
        unsure.append(f"support staffing and who pays for it ({HOUSING_WORDS[kind]} runs on an operating agreement; none is entered)")
        why.append(f"no support staffing is entered for {HOUSING_WORDS[kind]}, so the running costs here are the building's alone")
        if word == "likely":
            word = "unsure"
    for x in not_counted:
        why.append(f"no {x['label']} is counted: {x['why']}")
    if gfa and gfa_from == "the massing":
        why.append(f"the floor area, {gfa:,.0f} m², is the massing's (plate × storeys), not a figure in the option")
    placeholders = [l["label"] for l in lines if l["placeholder"]]
    if placeholders:
        why.append("placeholders in use: " + ", ".join(placeholders))

    return {
        "grade": "feasibility", "available": True,
        "inputs": {"units": units, "units_total": n, "gfa_m2": gfa or None, "gfa_from": gfa_from if gfa else None, "rent_tiers_units": tiers, "finance": fin},
        "capital": {"hard": hard, "escalation": factor, "soft": soft_cost, "contingency": contingency, "land": land_cost, "total": capital},
        "operating": {"revenue": rev, "gross": gross, "vacancy": vacancy, "operating_cost": opx, "reserve": reserve, "support_staffing": staffing,
                      "noi": noi, "subsidy": subsidy, "page": page},
        "funding": {"grants": grants, "not_counted": not_counted, "equity": equity, "debt": {"supportable": debt, "rate_pct": rate, "amortization_years": years, "dcr": dcr, "annual_service": service}, "total": funding},
        "gap": {"value": gap, "share_of_capital": gap_share},
        "verdict": {"word": word, "why": why, "unsure": unsure, "operating_shortfall": operating_shortfall},
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
    L.append(f"**{VERDICT_WORDS.get(v['word'], v['word'].capitalize())}.** " + " ".join(w[0].upper() + w[1:] + "." for w in v["why"]))
    L.append("")
    nxt = next_step(pf)
    if nxt:
        L.append(f"**For the development manager:** {nxt}")
        L.append("")
    L.append(f"- Capital cost **{_money(c['total'])}**: hard {_money(c['hard'])} (escalated ×{c['escalation']}), soft {_money(c['soft'])}, contingency {_money(c['contingency'])}, land {_money(c['land'])}.")
    L.append(f"- Net operating income **{_money(o['noi'])} a year**: rent {_money(o['gross'])} less vacancy {_money(o['vacancy'])}, operating cost {_money(o['operating_cost'])} and reserve {_money(o['reserve'])}"
             + (f" and support staffing {_money(o['support_staffing'])}" if o.get("support_staffing") is not None else "") + ".")
    L.append(f"- Funding **{_money(f['total'])}**: grants {_money(sum(x['value'] for x in f['grants']))}, equity {_money(f['equity'])}, supportable debt {_money(f['debt']['supportable'])} "
             f"at {f['debt']['rate_pct']}% repaid over {f['debt']['amortization_years']} years, the loan the lender sizes so net income is {f['debt']['dcr']:.2f} times the payment.")
    # a negative gap is a surplus and is said so (23 Nov 2026: "Gap $-12,639,932 (-45% of the capital cost)")
    if g["value"] is not None and g["value"] < 0:
        L.append(f"- Surplus **{_money(-g['value'])}**" + (f" ({-g['share_of_capital'] * 100:.0f}% of the capital cost)" if g.get("share_of_capital") is not None else "") + ": the funding counted is more than the cost.")
    else:
        L.append(f"- Gap **{_money(g['value'])}**" + (f" ({g['share_of_capital'] * 100:.0f}% of the capital cost)" if g.get("share_of_capital") is not None else "") + ".")
    for x in f.get("not_counted") or []:
        L.append(f"- Not counted: {x['label']} ({_money(x['value'])} at the provisional rate), because {x['why']}.")
    if v["unsure"]:
        L.append("- Left to a person: " + "; ".join(v["unsure"]) + ".")
    L.append("")
    L.extend(operating_markdown(pf))
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


FROM_WORDS = {"entered": "entered", "placeholder": "placeholder", "rule": "the rules' figure"}


def operating_rows(pf: dict) -> list[dict]:
    """The operating page as rows {label, value ($ a year, None where not entered), note, kind}: income by rent tier,
    the running costs, what is left, the subsidy entered, the loan payment, and the two subsidy figures a funder reads
    (to run the building; and, as an illustration, if the capital still missing were borrowed). `kind` is "income",
    "cost", "result" or "ask", for the page and the memo to set apart. Pure; the page's memo/answers.js reads the same
    `operating.page`."""
    p = ((pf or {}).get("operating") or {}).get("page")
    if not p or p.get("gross") is None:
        return []
    homes = ((pf.get("inputs") or {}).get("units_total")) or 0
    rows: list[dict] = []
    for t in p["tiers"]:
        if not t["homes"]:
            continue
        per = f"${t['rent_month_per_home']:,.0f} a month a home" if t.get("rent_month_per_home") is not None else "no rent figure"
        rows.append({"label": f"{t['label']}, {t['homes']:g} homes", "value": t["rent_year"], "note": f"{per} ({FROM_WORDS[t['from']]})", "kind": "income"})
    rows.append({"label": "Vacancy", "value": -(p["vacancy"] or 0), "note": "the CMHC survey's rate, on all tiers", "kind": "cost"})
    rows.append({"label": "Operating cost", "value": -(p["operating_cost"] or 0),
                 "note": f"${p['operating_cost_per_home']:,.0f} a home a year ({FROM_WORDS[p['operating_cost_from']]})", "kind": "cost"})
    rows.append({"label": "Replacement reserve", "value": -(p["reserve"] or 0), "note": "", "kind": "cost"})
    rows.append({"label": "Support staffing", "value": -p["support_staffing"] if p["support_staffing"] is not None else None,
                 "note": "entered" if p["support_staffing"] is not None else ("not entered, and this kind of housing runs on it" if p["staffing_missing"] else ""), "kind": "cost"})
    rows.append({"label": "Left after running costs", "value": p["net_before_subsidy"], "note": "before any operating subsidy or loan payment", "kind": "result"})
    if p["subsidy"]:
        rows.append({"label": "Operating subsidy entered", "value": p["subsidy"],
                     "note": (f"{p['subsidy_source']}; " if p.get("subsidy_source") else "") + ("confirmed" if p["subsidy_confirmed"] else "not yet confirmed"), "kind": "income"})
    rows.append({"label": "Loan payment", "value": -(p["debt_service"] or 0), "note": "on the loan the funding counts (the capital figures above)", "kind": "cost"})
    rows.append({"label": "Subsidy needed to run it", "value": p["subsidy_to_run"],
                 "note": (f"${p['subsidy_to_run_per_home_month']:,.0f} a home a month over {homes} homes"
                          + (f" (${p['subsidy_to_run_per_bed_month']:,.0f} a bed a month over {p['beds']} beds)" if p.get("beds") and p.get("subsidy_to_run_per_bed_month") is not None else "") + "; "
                          if p["subsidy_to_run"] else "none: the rents cover the running costs; ")
                         + "before any loan payment", "kind": "ask"})
    f = p.get("if_gap_financed")
    if f:
        rows.append({"label": "Subsidy needed if the capital still missing were borrowed", "value": f["subsidy_year"],
                     "note": f"${f['per_home_month']:,.0f} a home a month: the payment on ${f['loan']:,.0f} at {f['rate_pct']}% over {f['amortization_years']} years is ${f['annual_payment']:,.0f} a year. "
                             "An illustration on this screen's mortgage terms, not a funder's financing", "kind": "ask"})
        t = f.get("on_program_terms")
        if t:
            rows.append({"label": f"The same, on {t['program']}' published take-out terms", "value": t["subsidy_year"],
                         "note": f"${t['per_home_month']:,.0f} a home a month: {t['rate_pct']}% over {t['amortization_years']} years is ${t['annual_payment']:,.0f} a year. "
                                 "The program's page gives the rate; whether this project gets that loan is the program's to say", "kind": "ask"})
    return rows


def operating_markdown(pf: dict) -> list[str]:
    rows = operating_rows(pf)
    if not rows:
        return []
    L = ["### What it takes to run, a year", "", "| | A year | |", "|---|---:|---|"]
    for r in rows:
        bold = "**" if r["kind"] in ("result", "ask") else ""
        shown = _money(r["value"]) if r["value"] is not None else ("not entered" if "runs on it" in r["note"] else "none")
        L.append(f"| {bold}{r['label']}{bold} | {bold}{shown}{bold} | {r['note']} |")
    L.append("")
    L.append("> The rents and the running cost are placeholders until the operator's own are entered (the option's operating figures); "
             "support staffing and an operating subsidy are never assumed. A funder compares the subsidy a home a month.")
    L.append("")
    return L


def _money(x: Any) -> str:
    if x is None:
        return "not given"
    return f"-${-x:,.0f}" if x < 0 else f"${x:,.0f}"     # a loss reads -$52,880, never $-52,880
