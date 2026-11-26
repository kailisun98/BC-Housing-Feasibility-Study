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
# No program is named here (24 Nov 2026: this named CMHC's Affordable Housing Fund, closed on 19 Dec 2025 by the tool's
# own rule); answer 2 lists the programs with whether each is taking proposals.
MORE_SOURCES = ("Look for more sources as well: other grants (answer 2 lists the programs and whether each is taking proposals; a municipal "
                "grant, a capital campaign or a foundation), more equity, a land contribution or a partner. A revised memo counts what is found "
                "as other grants or equity.")
# Supportive, transitional and shelter housing reach capital by a program's own route, not by a gap a society fills
# (24 Nov 2026: answer 2 said the Supportive Housing Fund pays the capital and the Province owns the building, while
# answer 4 showed a 100% gap and sent the manager looking for grants).
PROGRAM_ROUTE = ("For {what}, the capital comes by the program's own route (answer 2 says how a project enters each, and what each pays for): "
                 "settle that route, who operates the building and the operating agreement first. The gap here is what a society would face outside that route.")
CLOSE_GAP = "Another source, or firmer figures for the placeholders, would settle it."
OPERATING_FUNDER = ("Find who pays to run it before the capital: an operating agreement or subsidy (for supportive, transitional or "
                    "shelter housing, the staffing as well), then a revised memo with the project's own rents, running costs and "
                    "subsidy.")
PLACEHOLDERS_LEFT = " Until they are entered, the rents and the running cost are placeholders."


def next_step(pf: dict) -> str | None:
    """What the verdict asks of the development manager: more sources for a gap past the screen's line; another
    source or firmer placeholders for a gap inside it; nothing when the stack covers the cost, or when a figure is
    missing (the memo's "Left to a person" names that one)."""
    v = (pf or {}).get("verdict") or {}
    gap, cap = ((pf or {}).get("gap") or {}).get("value"), (pf or {}).get("capital") or {}
    homes = ((pf or {}).get("inputs") or {}).get("units_total")
    page = ((pf or {}).get("operating") or {}).get("page") or {}
    if v.get("operating_shortfall"):
        return OPERATING_FUNDER + ("" if page.get("own_figures") else PLACEHOLDERS_LEFT)
    kind = page.get("housing_type")
    if kind and kind != "independent" and v.get("word") in ("unlikely", "unsure"):
        from .checks import HOUSING_WORDS
        return PROGRAM_ROUTE.format(what=HOUSING_WORDS.get(kind, kind))
    if v.get("word") == "unlikely":
        return MORE_SOURCES
    if v.get("word") == "unsure" and homes and gap is not None and gap > 0 and cap.get("total") is not None and cap.get("land") is not None:
        return CLOSE_GAP
    return None


# Capital sources a person names, each with its kind and status (25 Nov 2026): `option.finance.sources`
# [{name, kind, amount_cad, status}]. The words are the memo's; the page's memo/answers.js has the same tables.
SOURCE_KINDS = ("grant", "equity", "loan", "land", "other")
SOURCE_STATUSES = ("committed", "applied", "assumed")
SOURCE_KIND_WORDS = {"grant": "a grant", "equity": "equity", "loan": "a loan", "land": "land or a contribution in kind", "other": "another source"}
SOURCE_STATUS_WORDS = {"committed": "committed", "applied": "applied for, not committed", "assumed": "assumed, not yet asked for"}


def named_sources(fin: dict) -> list[dict]:
    """The named capital sources with an amount, each {name, kind, amount, status}: a kind or status not in the lists
    reads "other" and "assumed" (a source nobody has said is committed is not). Pure."""
    out = []
    for s in (fin or {}).get("sources") or []:
        if not isinstance(s, dict):
            continue
        try:
            amount = float(s.get("amount_cad"))
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        kind = str(s.get("kind") or "other").lower()
        status = str(s.get("status") or "assumed").lower()
        row = {"name": str(s.get("name") or "").strip() or "A source not named", "kind": kind if kind in SOURCE_KINDS else "other",
               "amount": round(amount), "status": status if status in SOURCE_STATUSES else "assumed"}
        # a loan's own terms, where given (rate_pct, amortization_years)
        for key in ("rate_pct", "amortization_years"):
            try:
                if row["kind"] == "loan" and s.get(key) not in (None, "") and float(s[key]) > 0:
                    row[key] = float(s[key]) if key == "rate_pct" else int(float(s[key]))
            except (TypeError, ValueError):
                pass
        out.append(row)
    return out


def _and_words(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1] if names else ""


def contributions(grants: list[dict], not_counted: list[dict], equity: float, fin: dict, debt: float | None,
                  land_gift: float | None, gap: float | None) -> list[dict]:
    """The contributions ledger (25 Nov 2026, a funder-side reader: "each line confirmed or sought"): every source the
    money counts, with its status, then what is shown and not counted, and what is still to find. Each row {label, kind,
    value, status, counted}. `status` is committed, applied, assumed, illustrative (a program's grant at its provisional
    rate, nobody has offered it), entered (a figure typed with no status), sized (the loan this screen sizes on the net
    income), in kind, not counted, or to find. Pure."""
    rows: list[dict] = []
    for g in grants:
        if g.get("named"):
            rows.append({"label": g["label"], "kind": g.get("kind") or "other", "value": g["value"], "status": g["status"], "counted": True})
        elif g.get("illustrative"):
            rows.append({"label": g["label"].replace(" (illustrative)", ""), "kind": "grant", "value": g["value"], "status": "illustrative", "counted": True})
        else:
            rows.append({"label": g["label"].replace(" (entered)", ""), "kind": "grant", "value": g["value"], "status": "entered", "counted": True})
    if equity:
        rows.append({"label": "Equity", "kind": "equity", "value": round(equity), "status": "entered", "counted": True})
    if debt:
        rows.append({"label": "Mortgage the net income carries", "kind": "loan", "value": debt, "status": "sized", "counted": True})
    if land_gift:
        rows.append({"label": "The land owner's contribution", "kind": "land", "value": land_gift, "status": "in kind", "counted": False})
    for x in not_counted:
        rows.append({"label": x["label"], "kind": "grant", "value": x["value"], "status": "not counted", "counted": False})
    if gap is not None and gap > 0:
        rows.append({"label": "Still to find", "kind": "gap", "value": gap, "status": "to find", "counted": False})
    return rows


CONTRIBUTION_STATUS_WORDS = {"committed": "committed", "applied": "applied for", "assumed": "assumed", "illustrative": "illustrative: nobody has offered it",
                             "entered": "entered, status not given", "sized": "sized by this screen", "in kind": "in kind",
                             "not counted": "not counted", "to find": "to find"}


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


def placed_units(layout: dict | None) -> dict[str, int] | None:
    """The homes the first plans place, by type (a home counted once, on its entry floor), or None without plans. Pure."""
    if not layout or not layout.get("floors"):
        return None
    out = {k: 0 for k in UNIT_KEYS}
    for fl in layout["floors"]:
        for z in fl.get("zones") or []:
            if z.get("unit") in out:
                out[z["unit"]] += 1
    return out


def build(site: dict, option: dict, ledger: dict, massing: dict | None = None, layout: dict | None = None) -> dict[str, Any]:
    """The pro-forma. With the run's `massing`, a floor area the option leaves blank is taken from the proposed mass
    (plate × storeys) and every line that uses it says so (15 Nov 2026: before, FIG 02 stated a floor area while
    answer 4 said there was none). With the run's `layout`, the rents, the running costs, the grant and the debt count
    the homes the first plans place, not every home entered (25 Nov 2026, Kai: "placed homes only"; R1 priced 105 homes
    on plans that hold 70); the floor area and its cost stay the option's."""
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
    entered_n = sum(units.values())
    placed = placed_units(layout)
    if placed is not None and sum(placed.values()) < entered_n:
        units = {k: min(units[k], placed.get(k, 0)) for k in UNIT_KEYS}
    n = sum(units.values())
    homes_basis = "placed" if n < entered_n else "entered"
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
    from .checks import non_residential_m2
    nonres_m2 = non_residential_m2(option)      # the brief's "not homes" spaces too (25 Nov 2026)
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
         else f"{hc.get('basis', '')}".split(";")[0] + ("; NOT written for this building: " + "; ".join(outside_base) if outside_base else "")
         + "; a placeholder until a cost consultant's rate for this building is entered",
         # a catalogue rate for 2- to 4-unit buildings stands under every gap: a placeholder, said as one (25 Nov 2026,
         # three reviewers: it priced 15-storey towers and was missing from "placeholders in use")
         own_rate is None)
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
    # Supportive and transitional homes are not the Community Housing Fund's tiers (25 Nov 2026, two reviewers: 78
    # supportive studios were priced at market rent, and transitional homes split 2 / 3 / 1): a supportive resident pays
    # the shelter component of income assistance, as the Supportive Housing Fund's own rule says; a transitional one rent
    # geared to income. Supportive homes beside independent ones (`supportive_units`) are taken out of the market tier.
    from .checks import housing_kind as _kind
    kind0 = _kind(option)
    sup_n = int(option.get("supportive_units") or 0)
    tier_basis = None
    if n and kind0 in ("supportive", "transitional"):
        only = "deep_subsidy" if kind0 == "supportive" else "rgi"
        tiers = {k: (n if k == only else 0) for k in TIER_KEYS}
        tier_basis = ("every home at the shelter component of income assistance, as supportive housing's residents pay" if kind0 == "supportive"
                      else "every home rent geared to income, as transitional housing is let")
    elif n and sup_n:
        base = dict(tiers) if tiers else {"market": n, "rgi": 0, "deep_subsidy": 0}
        moved = min(sup_n, base["market"])
        base["market"] -= moved
        base["deep_subsidy"] += moved
        tiers = base
        tier_basis = f"the {sup_n} supportive homes at the shelter component of income assistance, taken out of the market tier"
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
              else f"the shelter rate, ${rents.get('deep_subsidy_rent_monthly_cad')} a month") + (f"; {tier_basis}" if tier_basis and kind0 != "transitional" else ""), False)
    if tier_basis and kind0 == "transitional":
        lines[-2]["note"] += f"; {tier_basis}"        # the RGI line, written just before
    gross = sum(v for v in rev.values() if v) if n else None
    # a shelter counted in beds, with no homes (24 Nov 2026: a 60-bed shelter's $2.4M staffing and $2.9M subsidy were
    # dropped because the page counted homes only): its places are its beds, it collects no rent, and its running cost
    # is the operator's per bed where entered, else not estimated
    beds_in = option.get("beds")
    beds_n = int(beds_in) if isinstance(beds_in, (int, float)) and not isinstance(beds_in, bool) and beds_in > 0 else 0
    beds_only = not n and beds_n > 0
    places = n or beds_n
    if beds_only:
        gross = 0
    # vacancy and the reserve are the operator's to set (24 Nov 2026, the operator's review)
    own_vac = entered("vacancy_rate")
    # a vacancy typed as a percent (2 for 2%) is read as one, and nothing over half the rent is taken (25 Nov 2026: "2"
    # was read as 200% and signed)
    vac_as_pct = own_vac is not None and 1 < own_vac <= 100
    if vac_as_pct:
        own_vac = own_vac / 100
    if own_vac is not None:
        own_vac = max(0.0, min(own_vac, 0.5))
    vac = own_vac if own_vac is not None else float(rents.get("vacancy_rate") or 0)
    vacancy = round(gross * vac) if gross is not None else None      # a rent of $0 (a shelter) is a figure, not a blank
    own_opx = entered("operating_cost_per_unit_year_cad")
    per_opx = own_opx if own_opx is not None else float(ops.get("operating_cost_per_unit_year_cad") or 0)
    opx = round(n * per_opx) if n else (round(beds_n * own_opx) if beds_only and own_opx is not None else None)
    own_res = entered("replacement_reserve_per_unit_year_cad")
    per_res = own_res if own_res is not None else float(ops.get("replacement_reserve_per_unit_year_cad") or 0)
    reserve = round(n * per_res) if n else None
    # beds beside homes run too (25 Nov 2026: Glen Drive's 80 shelter beds carried no running cost or reserve): at the
    # operator's cost a bed where entered, else at a home's (a placeholder, said); the reserve on their sleeping rooms,
    # four beds a room, each held like a home
    bed_opx = bed_res = None
    own_bed = entered("operating_cost_per_bed_year_cad")
    if n and beds_n:
        bed_opx = round(beds_n * (own_bed if own_bed is not None else per_opx))
        bed_res = round(-(-beds_n // 4) * per_res)
        opx = (opx or 0) + bed_opx
        reserve = (reserve or 0) + bed_res
    # support staffing: the cost that decides whether supportive, transitional or shelter housing can open. Entered or
    # absent, never assumed; where that kind of housing has none entered, the verdict below cannot read "likely".
    staffing = round(entered("support_staffing_cad_year")) if entered("support_staffing_cad_year") is not None and places else None
    from .checks import housing_kind, housing_parts, HOUSING_WORDS
    kind = housing_kind(option)
    # every part of the building that runs on staffing, not only the main kind (24 Nov 2026: Glen Drive's 25 supportive
    # homes and 80-bed shelter read as independent rental needing no subsidy)
    parts = housing_parts(option)
    staffed = {k: c for k, c in parts.items() if k != "independent"}
    staffed_words = HOUSING_WORDS[kind] if kind != "independent" else " and ".join(
        f"the {c} {'shelter beds' if k == 'shelter' else HOUSING_WORDS[k] + ' homes'}" for k, c in staffed.items())
    # A budget per part of a mixed building (26 Nov 2026; the operator and the towers architect on 25 Nov: a shelter,
    # supportive homes and rental homes ran on one budget, so nobody could say what each part needs). Each staffed part
    # takes its own running cost, staffing and subsidy where entered (`operations.parts.<kind>`); the building's own
    # staffing and subsidy stay as the whole building's, unsplit. Rents stay by tier (a supportive home at the shelter
    # component, a shelter bed none).
    pin = opsin.get("parts") if isinstance(opsin.get("parts"), dict) else {}

    def pe(part: str, key: str) -> float | None:
        v = (pin.get(part) or {}).get(key) if isinstance(pin.get(part), dict) else None
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    sup_here = min(sup_n, n) if kind == "independent" else 0
    split = [(k, c) for k, c in (("independent" if kind == "independent" else kind, n - sup_here), ("supportive", sup_here), ("shelter", beds_n if n else 0)) if c > 0]
    mixed = len(split) > 1
    part_costs: dict[str, float] = {}
    if mixed:
        own_sup = pe("supportive", "operating_cost_cad_year")
        if sup_here and own_sup is not None:
            opx = (opx or 0) + round(sup_here * (own_sup - per_opx))
            part_costs["supportive"] = own_sup
        own_shel = pe("shelter", "operating_cost_cad_year")
        if bed_opx is not None and own_shel is not None:
            opx = (opx or 0) + round(beds_n * own_shel) - bed_opx
            bed_opx = round(beds_n * own_shel)
            own_bed = own_shel
            part_costs["shelter"] = own_shel
    part_staff = {k: round(pe(k, "staffing_cad_year")) for k, _ in split if k != "independent" and pe(k, "staffing_cad_year") is not None}
    part_sub = {k: round(pe(k, "operating_subsidy_cad_year")) for k, _ in split if pe(k, "operating_subsidy_cad_year") is not None}
    whole_staff = staffing
    if mixed and part_staff:
        staffing = (staffing or 0) + sum(part_staff.values())
    # a staffed part with no staffing of its own, and none for the whole building, leaves the building's staffing unknown
    unstaffed = [k for k, _ in split if k not in ("independent",) and k not in part_staff] if mixed else []
    staffing_missing = bool(places) and bool(staffed) and (staffing is None or bool(mixed and unstaffed and entered("support_staffing_cad_year") is None and part_staff))
    noi = round(gross - (vacancy or 0) - (opx or 0) - (reserve or 0) - (staffing or 0) + (nr_income or 0)) if gross is not None else None
    if nr_income:
        line("nonres_income", "Income from the floors that are not homes", round(nr_income), "$/yr", None, "entered: rent or a contribution to running costs from the non-residential space (the option's finance block)", False)
    # an operating subsidy, as the manager has it: counted toward what a lender would lend against only once confirmed
    subsidy = round(entered("operating_subsidy_cad_year")) if entered("operating_subsidy_cad_year") is not None and places else None
    subsidy_confirmed = bool(subsidy) and opsin.get("subsidy_confirmed") is True
    if mixed and part_sub:
        # a part's subsidy is confirmed by its own agreement; the building's total is confirmed only where every one is
        each_ok = [(pin.get(k) or {}).get("subsidy_confirmed") is True for k in part_sub] + ([subsidy_confirmed] if subsidy else [])
        subsidy = (subsidy or 0) + sum(part_sub.values())
        subsidy_confirmed = bool(subsidy) and all(each_ok)
    # the subsidy's term (24 Nov 2026, the operator's review: a confirmed 3-year agreement was borrowed against for 40
    # years and the money read "likely"): a loan is sized on it only where the term covers the amortization
    term = entered("subsidy_term_years")
    line("vacancy", "Vacancy", vacancy, "$/yr", None if own_vac is not None else "f.rents",
         (f"entered: {vac * 100:.1f}% of gross rent" + (" (typed as a percent)" if vac_as_pct else "")) if own_vac is not None else f"{vac * 100:.1f}% of gross rent, the CMHC survey's rate", False)
    beds_words = (f"; and {beds_n} beds at ${(own_bed if own_bed is not None else per_opx):,.0f} a bed a year"
                  + (" (entered)" if own_bed is not None else " (a home's figure: enter the operator's cost a bed)")) if bed_opx is not None else ""
    line("opex", "Operating cost", opx, "$/yr", None if own_opx is not None else "f.operating",
         (f"entered: ${per_opx:,.0f} per home a year (the option's operating figures)" if own_opx is not None else f"${ops.get('operating_cost_per_unit_year_cad'):,} per unit") + beds_words
         + (f"; the {sup_here} supportive homes at ${part_costs['supportive']:,.0f} a home a year (entered for that part)" if "supportive" in part_costs else ""),
         (own_opx is None and is_placeholder("f.operating")) or (bed_opx is not None and own_bed is None))
    line("reserve", "Replacement reserve", reserve, "$/yr", None if own_res is not None else "f.operating",
         (f"entered: ${per_res:,.0f} per home a year" if own_res is not None else f"${ops.get('replacement_reserve_per_unit_year_cad'):,} per unit")
         + (f"; and {-(-beds_n // 4)} sleeping rooms of four beds, each held like a home" if bed_res is not None else ""),
         own_res is None and is_placeholder("f.operating"))
    line("staffing", "Support staffing", staffing, "$/yr", None,
         (("entered: " + ", ".join(([f"the whole building ${whole_staff:,.0f}"] if whole_staff else []) + [f"the {k} part ${v:,.0f}" for k, v in part_staff.items()])
           + (f"; not entered for the {' and '.join(unstaffed)} part" if staffing_missing and unstaffed else "")) if mixed and part_staff
          else "entered in the option's operating figures") if staffing is not None else
         (f"not entered: {staffed_words} run on staffing this screen does not estimate" if staffing_missing else "none entered"), False)
    line("noi", "Net operating income", noi, "$/yr", None, "gross rent less vacancy, operating cost, reserve and support staffing, before any operating subsidy", False)
    line("subsidy", "Operating subsidy", subsidy, "$/yr", None,
         (f"entered{': ' + str(opsin.get('subsidy_source')) if opsin.get('subsidy_source') else ''}; "
          + (("confirmed" + (f" for {term:g} years" if term is not None else ", for a term not entered")
              + (", so a lender's loan is sized with it" if term is not None and term >= int(P("f.mortgage").get("amortization_years") or 40)
                 else ", shorter than the loan's amortization, so no loan is sized on it")) if subsidy_confirmed
             else "not yet confirmed, so no loan is sized on it")) if subsidy else "none entered", False)

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
        fy = (chf_res.get("values") or {}).get("grant_fiscal_year") or "2025-26"
        if chf_status in ("fail", "not_applicable") or not tiers:
            # no rent tiers: the fund's mix is untested, and an option that answers less must not read rosier than one
            # that answers more (24 Nov 2026: a 5-home option without tiers counted $890,295; with them it failed the mix)
            reason = ("the option does not meet the fund's criteria (answer 2)" if chf_status == "fail"
                      else "the fund is not the program for this kind of housing (answer 2)" if chf_status == "not_applicable"
                      else "the rent tiers are not entered, so the fund's 30 / 50 / 20 mix is not tested (answer 2)")
            not_counted.append({"program": "bch.chf.eligibility", "label": "Community Housing Fund grant", "value": g, "why": reason})
            line("grant_chf", "Community Housing Fund grant", 0, "$", "bch.chf.eligibility",
                 f"not counted: {reason}; ${per:,.0f} per unit × {n} = ${g:,.0f} is what the {fy} provisional rate would give if it did", False)
        else:
            chf_grant = {"value": g, "confirmed": chf_status == "pass", "intake_open": intake_open}
            cond = "" if chf_status == "pass" else "; counted on the condition that the criteria still to confirm are met (answer 2)"
            closed = "; no intake is open, so no grant is committed or implied" if intake_open is False else ""
            grants.append({"program": "bch.chf.eligibility", "label": "Community Housing Fund grant (illustrative)", "value": g,
                           "illustrative": True, "confirmed": chf_status == "pass", "intake_open": intake_open,
                           "note": f"${per:,.0f} per unit × {n} ({fy} provisional rate, from the 2025 call's slides; that call did not proceed){cond}{closed}"})
            line("grant_chf", "Community Housing Fund grant", g, "$", "bch.chf.eligibility",
                 f"${per:,.0f} per unit × {n}; illustrative, at the {fy} provisional rate{cond}{closed}", False)
    if nr_funding:
        grants.append({"program": None, "label": "Money for the floors that are not homes (entered)", "value": nr_funding, "note": "a capital campaign, a grant or a partner's contribution (the option's finance block)"})
        line("nonres_funding", "Money for the floors that are not homes", nr_funding, "$", None, "entered: a capital campaign, a grant or a partner's contribution toward the non-residential space", False)
    other = fin.get("other_grants_cad")
    if other:
        grants.append({"program": None, "label": "Other grants (entered)", "value": float(other), "note": "the option's finance block"})
        line("grant_other", "Other grants", float(other), "$", None, "entered in the option's finance block", False)
    equity = float(fin.get("equity_cad") or 0)
    line("equity", "Equity", equity, "$", None, "entered in the option's finance block" if fin.get("equity_cad") is not None else "none entered", False)
    # capital sources named with their status (25 Nov 2026, both panels: "named capital sources, each committed, applied
    # for or assumed"): each is counted in the funding and listed in the contributions ledger with its status; a stack
    # that covers the cost only with sources not yet committed is never "likely"
    named = named_sources(fin)
    for i, s in enumerate(named):
        grants.append({"program": None, "label": s["name"], "value": s["amount"], "kind": s["kind"], "status": s["status"], "named": True,
                       "note": f"{SOURCE_KIND_WORDS[s['kind']]}, {SOURCE_STATUS_WORDS[s['status']]}"})
        line(f"source_{i + 1}", s["name"], s["amount"], "$", None, f"named source: {SOURCE_KIND_WORDS[s['kind']]}, {SOURCE_STATUS_WORDS[s['status']]}", False)
    uncommitted = sum(s["amount"] for s in named if s["status"] != "committed")
    # the land owner's contribution: the land's value less what the project pays for it, a contribution in kind (not
    # funding: the capital cost already carries the land at its price)
    land_value = fin.get("land_value_cad")
    land_gift = None
    if land_value is not None and land_cost is not None and float(land_value) > land_cost:
        land_gift = round(float(land_value) - land_cost)
        line("land_contribution", "The land owner's contribution", land_gift, "$", None,
             f"in kind: the land is valued at ${float(land_value):,.0f} and comes in at ${land_cost:,.0f}; not funding, since the capital cost already carries the land at its price", False)

    mtg = P("f.mortgage")
    rate, years, dcr = float(mtg.get("rate_pct") or 0), int(mtg.get("amortization_years") or 40), float(mtg.get("debt_coverage_ratio") or 1.1)
    k = mortgage_constant(rate, years)
    subsidy_lends = subsidy_confirmed and term is not None and term >= years
    noi_for_debt = (noi + (subsidy if subsidy_lends else 0)) if noi is not None else None
    # a named loan is repaid from the same net income (25 Nov 2026, the operator: a $3M loan was counted as a grant with
    # the full mortgage still sized on the same income): its payment, at its own rate and term where given, else this
    # screen's mortgage terms, comes off what the income can carry, and the screen's mortgage shrinks to suit
    loan_service = 0
    for s in named:
        if s["kind"] == "loan":
            r_, y_ = s.get("rate_pct") or rate, s.get("amortization_years") or years
            pay = round(s["amount"] * mortgage_constant(float(r_), int(y_)))
            s["annual_payment"] = pay
            loan_service += pay
            ln = next(x for x in lines if x["key"] == f"source_{named.index(s) + 1}")
            ln["note"] += (f"; repaid at {r_}% over {y_} years" + ("" if s.get("rate_pct") else " (this screen's mortgage terms: enter the loan's own)")
                           + f", ${pay:,.0f} a year, set against the net income before the screen sizes its own mortgage")
    debt = round(max(0.0, noi_for_debt / dcr - loan_service) / k) if noi_for_debt is not None and k else None
    service = round(debt * k) if debt else None
    # the debt in plain words (20 Nov 2026): what the coverage ratio and the amortization mean, not only their figures
    line("debt", "Supportable debt", debt, "$", "f.mortgage",
         (f"the largest loan the net operating income carries: the lender wants net income {dcr:.2f} times the loan payment "
          f"(the debt coverage ratio), at {rate}% repaid over {years} years (the amortization), ${service or 0:,.0f} a year in payments"
          + (f"; after the named loans' ${loan_service:,.0f} a year" if loan_service else ""))
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
    elif beds_only:
        word = "unsure"
        why.append(f"a shelter of {beds_n} beds collects no rent to set against the ${capital:,.0f} capital cost; who pays to build it is the program's question "
                   "(answer 2), and the operating page shows what running it takes")
        unsure.insert(0, "who pays the capital cost (a shelter program funds running a shelter; building it is a separate question for BC Housing or the City)")
    elif not n:
        # no homes entered: no rent, no debt and no grant can be counted, so the gap is the whole capital cost and
        # says nothing about the funders (17 Nov 2026: Expo as permitted read a 100% gap as a verdict)
        word = "unsure"
        if entered_n:
            why.append(f"none of the {entered_n} homes entered fits the first plans, so there is no rent, debt or grant to set against the ${capital:,.0f} capital cost")
            unsure.insert(0, "plans that hold the homes (the architect's, in Edit blocks)")
        else:
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
    # named sources not yet committed: a stack that covers the cost only with them is "unsure", and says how much rests on them
    if uncommitted and gap is not None and gap <= 0 and gap + uncommitted > 0 and word in ("likely", "unsure"):
        said = (f"the funding covers the capital cost only with ${uncommitted:,.0f} from named sources not yet committed "
                f"({_and_words([s['name'] for s in named if s['status'] != 'committed'])}); without them the gap is ${gap + uncommitted:,.0f}")
        if word == "likely":
            why[-1] = said
        else:   # already unsure on an illustrative grant: both are said
            why.append(said)
        word = "unsure"
    # Rents that do not cover the running costs: no capital stack makes that building likely (23 Nov 2026: a shelter
    # entered as built read "Likely, $12.6M to spare" over a net operating income of -$52,880 a year).
    # The operating page (23 Nov 2026): what runs the building each year, the subsidy it needs to break even before any
    # loan, and, as an illustration only, the subsidy it would need if the capital still missing were borrowed on layer
    # F's mortgage terms. A funder's own financing terms differ; the figure is this screen's arithmetic, per home per
    # month, so two options can be compared.
    after_subsidy = (noi + (subsidy or 0)) if noi is not None else None
    # with the staffing a supportive or shelter part runs on not entered, the subsidy it needs is not known: withheld,
    # never printed as a figure (24 Nov 2026: "$110 a home a month" stood beside "a funder compares this figure")
    to_run = (max(0, -noi) if noi is not None else None) if not staffing_missing else None
    financed = None
    # the whole capital gap borrowed is no ask for housing whose program pays the capital (supportive, shelter)
    if noi is not None and gap is not None and gap > 0 and k and n and not staffed:
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
        # the beds beside homes in the operating cost (25 Nov 2026): their count, the figure a bed and whose it is
        "beds_operating_cost": bed_opx, "beds_cost_per_bed": (round(own_bed) if own_bed is not None else round(per_opx)) if bed_opx is not None else None,
        "beds_cost_from": ("entered" if own_bed is not None else "home") if bed_opx is not None else None,
        "reserve": reserve, "support_staffing": staffing, "staffing_missing": staffing_missing, "staffed_parts": staffed if kind == "independent" else {},
        "subsidy_term_years": term, "subsidy_lends": subsidy_lends,
        "own_figures": all(t["from"] == "entered" for t in ([] if beds_only else [{"from": tier_from[x]} for x in TIER_KEYS if tier_homes[x]])) and own_opx is not None,
        "net_before_subsidy": noi, "subsidy": subsidy, "subsidy_confirmed": subsidy_confirmed, "subsidy_source": opsin.get("subsidy_source") or None,
        "net_after_subsidy": after_subsidy, "debt_service": service,
        "after_debt_service": (noi_for_debt - (service or 0)) if noi_for_debt is not None else None,
        "subsidy_to_run": to_run, "subsidy_to_run_per_home_month": round(to_run / n / 12) if to_run is not None and n else None,
        "if_gap_financed": financed,
        # the operating page's own words for its lines (25 Nov 2026: the vacancy row always said "the CMHC survey's
        # rate", the named loans' payments and the non-residential income had no row)
        "vacancy_rate": vac, "vacancy_from": "entered" if own_vac is not None else "rule",
        "named_loan_service": loan_service or None, "nonres_income": round(nr_income) if nr_income else None,
    }
    # the budget by part (26 Nov 2026): each part's rent, its share of vacancy, running cost and reserve, its own staffing
    # and subsidy, and what it leaves; the building's unsplit staffing and subsidy as a row of their own
    if mixed:
        deep_each = (rev["deep_subsidy"] or 0) / tier_homes["deep_subsidy"] if tier_homes.get("deep_subsidy") else 0
        label = {"independent": "Independent homes", "supportive": "Supportive homes", "transitional": "Transitional homes", "shelter": "Shelter beds"}
        rows = []
        for k, c in split:
            if k == "shelter":
                rent, cost, res_ = 0, bed_opx or 0, bed_res or 0
            elif k == "supportive" and kind == "independent":
                rent = round(c * deep_each)
                cost, res_ = round(c * part_costs.get("supportive", per_opx)), round(c * per_res)
            else:     # the homes that are not split out: the rest of the rent, cost and reserve of the homes
                rent = (gross or 0) - round(sup_here * deep_each)
                cost = (opx or 0) - (bed_opx or 0) - (round(sup_here * part_costs.get("supportive", per_opx)) if sup_here else 0)
                res_ = (reserve or 0) - (bed_res or 0) - (round(sup_here * per_res) if sup_here else 0)
            vac_ = round(rent * vac)
            st_, sb_ = part_staff.get(k), part_sub.get(k)
            rows.append({"key": k, "label": label.get(k, k), "places": c, "unit": "beds" if k == "shelter" else "homes", "rent": rent, "vacancy": vac_,
                         "cost": cost, "reserve": res_, "staffing": st_, "subsidy": sb_,
                         "staffing_missing": k != "independent" and st_ is None and whole_staff is None,
                         "net": rent - vac_ - cost - res_ - (st_ or 0) + (sb_ or 0)})
        whole_sub = subsidy - sum(part_sub.values()) if subsidy is not None else None
        if whole_staff or whole_sub:
            rows.append({"key": "whole", "label": "The whole building, not split", "places": None, "unit": "", "rent": 0, "vacancy": 0, "cost": 0, "reserve": 0,
                         "staffing": whole_staff or None, "subsidy": whole_sub or None, "staffing_missing": False,
                         "net": -(whole_staff or 0) + (whole_sub or 0)})
        page["parts"] = rows
    # a shelter counted in beds: the subsidy a bed a month. Beds beside homes: one figure for the building's places, the
    # homes and the beds together (25 Nov 2026: the whole need was divided once per home and again per bed, so a funder
    # read the building's deficit as the shelter's alone)
    beds = option.get("beds")
    if isinstance(beds, (int, float)) and not isinstance(beds, bool) and beds > 0:
        page["beds"] = int(beds)
        if n and kind0 != "shelter":
            page["subsidy_to_run_per_place_month"] = round(to_run / (n + beds) / 12) if to_run is not None else None
            page["subsidy_to_run_per_home_month"] = None
        else:
            page["subsidy_to_run_per_bed_month"] = round(to_run / beds / 12) if to_run is not None else None
    # Rents and subsidy that do not cover the running costs: no capital stack makes that building likely (a shelter
    # entered as built read "Likely, $12.6M to spare" over a net operating income of -$52,880 a year).
    operating_shortfall = -after_subsidy if (after_subsidy is not None and after_subsidy < 0 and places) else None
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
    elif subsidy and subsidy_confirmed and noi is not None and noi < 0 and not subsidy_lends:
        # the building runs only while an agreement shorter than the loan is renewed: said, and never "likely"
        why.append(f"the running costs are met by a ${subsidy:,.0f} a year operating subsidy "
                   + (f"for {term:g} years" if term is not None else "for a term not entered")
                   + f", shorter than the {years}-year loan: no loan is sized on it, and the building depends on its renewal")
        unsure.append("the operating agreement's term and renewal (who funds the running costs after it ends)")
        if word == "likely":
            word = "unsure"
    if staffing_missing:
        unsure.append(f"support staffing and who pays for it ({staffed_words} run on an operating agreement; none is entered)")
        why.append(f"no support staffing is entered for {staffed_words}, so the running costs here are the building's alone and the subsidy it needs is not known")
        if word == "likely":
            word = "unsure"
    for x in not_counted:
        why.append(f"no {x['label']} is counted: {x['why']}")
    if gfa and gfa_from == "the massing":
        why.append(f"the floor area, {gfa:,.0f} m², is the massing's (plate × storeys), not a figure in the option")
    placeholders = [l["label"] for l in lines if l["placeholder"]]
    if placeholders:
        why.append("placeholders in use: " + ", ".join(placeholders))
    if homes_basis == "placed":
        why.append(f"it counts the {n} homes the first plans place, of the {entered_n} entered; the floor area and its cost are the option's")
        line("homes", "Homes counted", n, "homes", None,
             f"the {n} homes the first plans place, of the {entered_n} the option enters (answer 3 names the rest); the rents, running costs, grant and debt count these", False)

    return {
        "grade": "feasibility", "available": True,
        "inputs": {"units": units, "units_total": n, "units_entered": entered_n, "homes_basis": homes_basis,
                   "gfa_m2": gfa or None, "gfa_from": gfa_from if gfa else None, "rent_tiers_units": tiers, "finance": fin},
        "capital": {"hard": hard, "escalation": factor, "soft": soft_cost, "contingency": contingency, "land": land_cost, "total": capital},
        "operating": {"revenue": rev, "gross": gross, "vacancy": vacancy, "operating_cost": opx, "reserve": reserve, "support_staffing": staffing,
                      "noi": noi, "subsidy": subsidy, "page": page},
        "funding": {"grants": grants, "not_counted": not_counted, "equity": equity, "debt": {"supportable": debt, "rate_pct": rate, "amortization_years": years, "dcr": dcr, "annual_service": service}, "total": funding,
                    "sources": contributions(grants, not_counted, equity, fin, debt, land_gift, gap), "uncommitted": uncommitted, "land_contribution": land_gift},
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


def markdown(pf: dict, short: bool = False) -> list[str]:
    """The memo's pro-forma section: four lines, the verdict, where the money comes from, the operating table, then
    every line with its source (left out of the short memo)."""
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
    L.extend(sources_markdown(pf))
    L.extend(operating_markdown(pf))
    if short:
        return L
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


def sources_markdown(pf: dict) -> list[str]:
    """Where the money comes from, each source with its status (the contributions ledger), for memo.md."""
    rows = ((pf or {}).get("funding") or {}).get("sources")
    if not rows:
        return []
    L = ["**Where the money comes from**, each source with its status:", "", "| Source | Amount | Status |", "|---|---|---|"]
    for r in rows:
        out = not r["counted"] and r["status"] not in ("not counted", "to find")
        L.append(f"| {r['label']} | {_money(r['value'])} | {CONTRIBUTION_STATUS_WORDS.get(r['status'], r['status'])}{' (not in the funding total)' if out else ''} |")
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
    vr = p.get("vacancy_rate")
    rows.append({"label": "Vacancy", "value": -(p["vacancy"] or 0),
                 "note": (f"{vr * 100:.1f}%, " if vr is not None else "") + ("entered, on all tiers" if p.get("vacancy_from") == "entered" else "the CMHC survey's rate, on all tiers"), "kind": "cost"})
    rows.append({"label": "Operating cost", "value": -p["operating_cost"] if p["operating_cost"] is not None else None,
                 "note": (f"${p['operating_cost_per_home']:,.0f} a home a year ({FROM_WORDS[p['operating_cost_from']]})" if p.get("operating_cost_per_home") is not None
                          else "not entered: enter the operator's running cost per bed")
                 + (f"; and {p['beds']} beds at ${p['beds_cost_per_bed']:,.0f} a bed a year ({'entered' if p.get('beds_cost_from') == 'entered' else 'a home’s figure'})"
                    if p.get("beds_operating_cost") is not None and p.get("beds") else ""), "kind": "cost"})
    rows.append({"label": "Replacement reserve", "value": -(p["reserve"] or 0),
                 "note": (f"with {-(-int(p['beds']) // 4)} sleeping rooms of four beds, each held like a home" if p.get("beds_operating_cost") is not None and p.get("beds") else ""),
                 "kind": "cost"})
    rows.append({"label": "Support staffing", "value": -p["support_staffing"] if p["support_staffing"] is not None else None,
                 "note": "entered" if p["support_staffing"] is not None else ("not entered, and this kind of housing runs on it" if p["staffing_missing"] else ""), "kind": "cost"})
    if p.get("nonres_income"):
        rows.append({"label": "Income from the floors that are not homes", "value": p["nonres_income"], "note": "entered: rent or a contribution to running costs", "kind": "income"})
    rows.append({"label": "Left after running costs", "value": p["net_before_subsidy"], "note": "before any operating subsidy or loan payment", "kind": "result"})
    if p["subsidy"]:
        rows.append({"label": "Operating subsidy entered", "value": p["subsidy"],
                     "note": (f"{p['subsidy_source']}; " if p.get("subsidy_source") else "") + ("confirmed" if p["subsidy_confirmed"] else "not yet confirmed"), "kind": "income"})
        rows.append({"label": "Left after the subsidy", "value": p.get("net_after_subsidy"), "note": "what the subsidy entered leaves, before any loan payment", "kind": "result"})
    if p.get("named_loan_service"):
        rows.append({"label": "Payments on the named loans", "value": -p["named_loan_service"], "note": "the capital sources entered as loans, each at its own terms", "kind": "cost"})
    rows.append({"label": "Loan payment", "value": -(p["debt_service"] or 0), "note": "on the mortgage the funding counts (the capital figures above)", "kind": "cost"})
    if p["subsidy_to_run"] is None:
        rows.append({"label": "Subsidy needed to run it", "value": None,
                     "note": "not given: the support staffing is not entered, so what running it costs is not known", "kind": "ask"})
    else:
        per = []
        if p.get("subsidy_to_run_per_home_month") is not None and homes:
            per.append(f"${p['subsidy_to_run_per_home_month']:,.0f} a home a month over {homes} homes")
        if p.get("beds") and p.get("subsidy_to_run_per_bed_month") is not None:
            per.append(f"${p['subsidy_to_run_per_bed_month']:,.0f} a bed a month over {p['beds']} beds")
        if p.get("subsidy_to_run_per_place_month") is not None:
            per.append(f"${p['subsidy_to_run_per_place_month']:,.0f} a month for each of its {homes + p['beds']} places ({homes} homes and {p['beds']} beds): "
                       "the building's whole need, shared over its places, not the shelter's alone")
        rows.append({"label": "Subsidy needed to run it", "value": p["subsidy_to_run"],
                     "note": ("; ".join(per) + "; " if p["subsidy_to_run"] and per else "none: the rents cover the running costs; " if not p["subsidy_to_run"] else "")
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
        shown = _money(r["value"]) if r["value"] is not None else ("not entered" if ("runs on it" in r["note"] or r["note"].startswith("not ")) else "none")
        L.append(f"| {bold}{r['label']}{bold} | {bold}{shown}{bold} | {r['note']} |")
    L.append("")
    own = (((pf or {}).get("operating") or {}).get("page") or {}).get("own_figures")
    L.append("> " + ("The rents and the running cost are the operator's own, as entered" if own else
                     "The rents and the running cost are placeholders until the operator's own are entered (the option's operating figures)")
             + "; support staffing and an operating subsidy are never assumed. A funder compares the subsidy a home a month, or a bed a month for a shelter.")
    L.append("")
    L.extend(parts_markdown(pf))
    return L


PART_COLUMNS = (("rent", "Rent"), ("vacancy", "Vacancy"), ("cost", "Running cost"), ("reserve", "Reserve"), ("staffing", "Staffing"), ("subsidy", "Subsidy"), ("net", "Left a year"))


def parts_markdown(pf: dict) -> list[str]:
    """The operating page by part of a mixed building (26 Nov 2026): a row a part, as `page.parts` holds it; the page's
    memo/answers.js partsTable draws the same rows."""
    rows = ((((pf or {}).get("operating") or {}).get("page") or {}).get("parts")) or []
    if not rows:
        return []
    L = ["#### By part of the building", "", "| Part | Places | " + " | ".join(w for _, w in PART_COLUMNS) + " |", "|---|---:|" + "---:|" * len(PART_COLUMNS)]
    for r in rows:
        cell = lambda k: ("not entered" if k == "staffing" and r.get("staffing_missing") else "—") if r.get(k) is None else _money(-r[k] if k in ("vacancy", "cost", "reserve", "staffing") else r[k])
        L.append(f"| {r['label']} | {r['places'] if r.get('places') is not None else ''} {r.get('unit') or ''} | " + " | ".join(cell(k) for k, _ in PART_COLUMNS) + " |")
    L.append("")
    L.append("> Each part's own running cost, staffing and subsidy where the operator entered them; the rents by tier. What a part leaves a year is what it needs, or gives, before any loan payment.")
    L.append("")
    return L


def _money(x: Any) -> str:
    if x is None:
        return "not given"
    x = round(x) or 0                                       # never "$-0"
    return f"-${-x:,.0f}" if x < 0 else f"${x:,.0f}"     # a loss reads -$52,880, never $-52,880
