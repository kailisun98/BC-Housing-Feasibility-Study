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


# What kind of housing the option is (23 Nov 2026, from three simulated user tests: a youth shelter and a supportive
# building were failed against the Community Housing Fund's 30/50/20 mix and the family-unit minimum, and told to "add
# family units"). `option.housing_type` says it (independent, supportive, transitional, shelter); where it is blank, an
# option whose homes are all supportive (`supportive_units` equal to the homes) is read as supportive. Independent
# rental is what the funder and family rules in the stack are written for; for the other three they say so instead of
# failing, and hand the question to a person. Pure; the page's fields.js housingKind is the twin.
HOUSING_TYPES = ("independent", "supportive", "transitional", "shelter")
HOUSING_WORDS = {"supportive": "supportive housing", "transitional": "transitional housing", "shelter": "a shelter"}


def housing_kind(option: Option) -> str:
    kind = str((option or {}).get("housing_type") or "").strip().lower()
    if kind in HOUSING_TYPES:
        return kind
    total = _units_total(option or {})
    supportive = int((option or {}).get("supportive_units") or 0)
    return "supportive" if total and supportive >= total else "independent"


def housing_parts(option: Option) -> dict[str, int]:
    """The kinds of housing in a building, with their counts (24 Nov 2026: Glen Drive's 25 supportive homes and 80-bed
    shelter read as independent rental, so nothing asked who staffs or funds them). The main kind takes the homes not
    counted elsewhere; supportive homes are `supportive_units`; shelter beds are `beds` beside homes, or the whole of a
    shelter. A building of one kind returns one entry."""
    o = option or {}
    kind = housing_kind(o)
    total = _units_total(o)
    sup = int(o.get("supportive_units") or 0)
    beds = o.get("beds")
    beds = int(beds) if isinstance(beds, (int, float)) and not isinstance(beds, bool) and beds > 0 else 0
    parts: dict[str, int] = {}
    if kind == "shelter":
        return {"shelter": beds or total}
    if kind == "supportive":
        parts["supportive"] = total
    else:
        if total - sup > 0:
            parts[kind] = total - sup
        if sup:
            parts["supportive"] = sup
    if beds and kind != "transitional":
        parts["shelter"] = beds
    return parts


def proposes_rezoning(option: Option) -> bool:
    """Whether the option states a rezoning: a `rezoning_path` that is not blank and does not begin "none" (a
    development permit under an official development plan, or an outright scheme, is written "none: …")."""
    route = approval_route(option)
    if route in ("development_permit", "outright"):
        return False
    if route == "rezoning":
        return True
    path = str((option or {}).get("rezoning_path") or "").strip().lower()
    return bool(path) and not path.startswith(("none", "no rezoning", "not a rezoning"))


APPROVAL_ROUTES = ("rezoning", "development_permit", "outright")
ROUTE_WORDS = {"rezoning": "a rezoning", "development_permit": "a development permit under the district's schedule or official development plan",
               "outright": "an outright development permit"}


def approval_route(option: Option) -> str | None:
    """How the option is approved, where a person said (`option.approval_route`, 23 Nov 2026: a development-permit
    building in the Downtown Eastside and two sites already rezoned were read against the rules written for rezonings,
    because the only way to say otherwise was to type "none: …" as the rezoning path). None where it was not said."""
    route = str((option or {}).get("approval_route") or "").strip().lower()
    return route if route in APPROVAL_ROUTES else None


def no_rezoning_stated(option: Option) -> bool:
    """A person said there is no rezoning: by the approval route, or by a rezoning path that begins "none"."""
    return approval_route(option) in ("development_permit", "outright") or (bool(str((option or {}).get("rezoning_path") or "").strip()) and not proposes_rezoning(option))


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
NON_PROFIT_OWNERS = ("non_profit_society", "non_profit", "government", "co_op", "cooperative", "municipality", "province")


def _date_words(v: Any) -> str | None:
    """An ISO date in words ("25 Jul 2024"), other text as typed, or None for a blank. Pure."""
    v = str(v or "").strip()
    m = re.match(r"^(\d{4})-(\d\d)-(\d\d)", v)
    if not m:
        return v or None
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return f"{int(m.group(3))} {months[int(m.group(2)) - 1]} {m.group(1)}"


def rezoning_approved_on(option: Option) -> str | None:
    """The date Council approved the rezoning the option names (`rezoning_approved_on`, an ISO date), in words, or None
    where it is a proposal. Pure."""
    return _date_words((option or {}).get("rezoning_approved_on"))


def permit_issued_on(option: Option) -> str | None:
    """The date the development permit was issued (`permit_issued_on`), in words, or None. Pure."""
    return _date_words((option or {}).get("permit_issued_on"))


def land_signed_on(option: Option) -> str | None:
    """The date the land agreement was signed (`land_agreement_signed_on`), in words, or None. Pure."""
    return _date_words((option or {}).get("land_agreement_signed_on"))


def operator_of(option: Option) -> str:
    """Who operates the homes: the option's operator, else the organization that signed the operating figures, else an
    operator named in the proponent line ("…; operator BC Indigenous Housing Society"). 25 Nov 2026, three reviewers: the
    front sheet said "Not named" beside both. The page's memo/front.js is its twin. Pure."""
    o = option or {}
    op = str(o.get("operator") or "").strip()
    if op:
        return op
    signed = (o.get("operations") or {}).get("signed")
    if isinstance(signed, dict) and str(signed.get("org") or "").strip():
        return str(signed["org"]).strip()
    m = re.search(r"\boperat(?:or|ed by)\s+([^;,()]+)", str(o.get("proponent") or ""), re.I)
    return m.group(1).strip() if m else ""


def non_residential_m2(option: Option) -> float:
    """The option's floor area that is not homes: `non_residential_gfa_m2`, plus the program brief's spaces marked "not
    homes" (`use` "community": a hall, offices, a shop). 25 Nov 2026, the manager: a 450 m² hall and 900 m² of offices in
    the brief were invisible to C-2's non-dwelling floor area, to BC Builds and to the money. Pure."""
    o = option or {}
    brief = sum(float(b.get("area_m2") or 0) for b in (o.get("program_brief") or []) if isinstance(b, dict) and b.get("use") == "community")
    return float(o.get("non_residential_gfa_m2") or 0) + brief


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


def _for_sub_area(site: Site, p: Params) -> tuple[Params, dict | None]:
    """A plan that sets its figures by sub-area (the Downtown-Eastside/Oppenheimer plan, read 23 Nov 2026): the rule's
    params with the site's sub-area's own laid over them, or, where the site does not record one the plan has, the
    params as they are and what is missing ({key, choices, names})."""
    table = p.get("by_sub_area")
    if not table:
        return p, None
    key = p.get("sub_area_key") or "odp_sub_area"
    sub = str((site or {}).get(key) or "").strip()
    names = p.get("sub_area_names") or {}
    if sub not in table:
        return p, {"key": key, "choices": sorted(table), "names": names}
    merged = {k: v for k, v in p.items() if k != "by_sub_area"}
    merged.update(table[sub])
    merged["_sub_area"] = sub
    merged["_sub_area_words"] = f" in sub-area {sub}" + (f" ({names[sub]})" if names.get(sub) else "")
    return merged, None


def _which_sub_area(need: dict) -> Result:
    said = ", ".join(f"{c} {need['names'][c]}" if need["names"].get(c) else c for c in need["choices"])
    return _r(UNSURE, f"The plan sets this limit by sub-area ({said}) and the site does not record which one it is in.", {"sub_area": None},
              action="Manager or architect: find the lot on the plan's sub-area map and record its sub-area on the site.")


def _rezoning_path(option: Option) -> str | None:
    """The rezoning the option proposes, as the person wrote it, or None where it proposes none (a blank path, one that
    begins "none", or an approval route of a development permit or outright). 24 Nov 2026: a path of "none" printed
    "rezoning is required (none)" beside "By rezoning: not needed"."""
    return str(option.get("rezoning_path")).strip() if proposes_rezoning(option) and option.get("rezoning_path") else ("a rezoning" if proposes_rezoning(option) else None)


def _over_outright(option: Option, subject: str, said: str, vals: dict, what: str) -> Result:
    """An option over a schedule's outright figure, read against the approval route it states: a rezoning (the outright
    test fails and the rezoning is named), a development permit or outright (it fails: a permit cannot approve more than
    the schedule allows), or none stated."""
    path = _rezoning_path(option)
    approved = rezoning_approved_on(option)
    if path and approved:
        # a rezoning Council has approved is not asked for again (25 Nov 2026, the funder-side reader: a scheme approved in
        # July 2024 was told to take the rezoning and make a pre-application enquiry)
        return _r(FAIL, f"{subject} exceeds {said}, so it is not allowed outright; the rezoning ({path}) was approved by Council on {approved}, and it sets the {what} now.",
                  vals, action="")
    if path:
        return _r(FAIL, f"{subject} exceeds {said}, so it is not allowed outright; rezoning is required ({path}), where {what} is negotiated.",
                  vals, action=f"Manager and architect: take the rezoning ({path}) and confirm with City staff the {what} they will support.")
    route = approval_route(option)
    if route in ("development_permit", "outright"):
        return _r(FAIL, f"{subject} exceeds {said}, so it is not allowed outright; the option is to go by {ROUTE_WORDS[route]}, which cannot approve more than the schedule "
                        f"allows, so it needs a rezoning or a smaller building.", vals,
                  action=f"Manager: reduce the {what} to the schedule's figure, or change the approval route to a rezoning and name it.")
    return _r(FAIL, f"{subject} exceeds {said} and no rezoning path is stated.", vals,
              action=f"Reduce the {what} or state a rezoning path.")


def fsr_limit(site: Site, option: Option, p: Params) -> dict[str, Any]:
    """The FSR a schedule's rule allows this site and option: `max` the most allowed without discretion (None where the
    site meets no row of the schedule's table), `words` how the schedule gets there, `discretionary` what the Director
    may allow above it and its clause, `increases` formula increases not computed here, `floor_area_cap` a CD-1's fixed
    floor area in m² (its `max` is then that area over the site), `short` why no figure applies."""
    tenure = option.get("tenure")
    p, need = _for_sub_area(site, p)
    out: dict[str, Any] = {"max": p.get("max_fsr"), "base": p.get("max_fsr"), "words": p.get("_sub_area_words") or "", "discretionary": None, "discretionary_clause": None,
                           "increases": p.get("fsr_increases"), "floor_area_cap": None, "short": None}
    if need:
        out["short"] = "the plan sets it by sub-area and the site's sub-area is not recorded"
        return out
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
        # The rental figure can ask for non-dwelling floor area at the street (C-2 s.3.1.1.1: 0.35 FSR). It is tested, not
        # assumed (23 Nov 2026: an all-residential C-2A option read "outright: yes" at 3.5 beside the clause that asks
        # for the shops); short of it the base figure stands and the words say what the higher one needs.
        need = p.get("rental_min_non_dwelling_fsr")
        area = float(site.get("site_area_m2") or 0)
        have = (non_residential_m2(option) / area) if area else 0.0
        if need and round(have, 2) + 1e-9 < need:
            out.update({"rental_short": {"needs_non_dwelling_fsr": need, "has_non_dwelling_fsr": round(have, 2), "max_fsr_rental": r,
                                         "needs_m2": round(need * area) if area else None},
                        "words": f" ({r} is open to a building with every home rental and {need} FSR of non-dwelling use at the street, "
                                 f"{round(need * area):,.0f} m² on this lot; this option has {non_residential_m2(option):,.0f} m², FSR {have:.2f}; "
                                 f"{p.get('rental_fsr_clause') or 'the schedule'})"})
        else:
            out.update({"max": r, "words": f" for a building with every home secured as rental ({p.get('rental_fsr_clause') or 'the schedule'}; {out['base']} otherwise)"})
    if tenure == SOCIAL and p.get("max_fsr_social_housing") and (out["max"] is None or p["max_fsr_social_housing"] > out["max"]):
        out.update({"max": p["max_fsr_social_housing"], "words": f" for 100% social housing ({p.get('social_housing_fsr_clause') or 'the schedule'}; {out['base']} otherwise)"})
    disc = p.get("max_fsr_discretionary")
    # the Director's increase can be open only to some sites (RR-3 s.3.1.1.4: a corner with 40.2 m and 1,470 m²)
    if disc and p.get("fsr_discretionary_when") and not _row_fits(site, option, p["fsr_discretionary_when"]):
        disc = None
    clause = p.get("fsr_discretionary_clause") or "the schedule"
    # RT-3's reading (16 Nov 2026) names the same two figures otherwise (25 Nov 2026, the small-lot architect: FSR 0.67 was
    # sent to rezoning where s.3.1.1.1 lets the Director allow 0.75, and s.3.1.1.2 1.00 for a non-profit multiple dwelling)
    if not disc and p.get("max_fsr_conditional"):
        disc, clause = p["max_fsr_conditional"], p.get("fsr_conditional_clause") or "s.3.1.1.1"
    aff = p.get("max_fsr_affordable_multiple_dwelling")
    if aff and (tenure == SOCIAL or str(option.get("owner_type_at_completion") or "").lower() in NON_PROFIT_OWNERS) and (not disc or aff > disc):
        disc, clause = aff, ("s.3.1.1.2, a multiple dwelling with at least 25% of its homes held by a non-profit or a government "
                             "for low-income households or people with disabilities")
    if disc:
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


def _other_front_fsr(site: Site, option: Option, p: Params, fsr: float) -> dict | None:
    """On a corner lot, what the other street as the front gives (the lot turned, so its width and a narrow-site cap
    change), where it would allow `fsr` and the front as taken does not. None otherwise."""
    other = other_front(site)
    if not other or not p.get("narrow_site"):
        return None
    turned = dict(site, front_face={"street": other})
    try:
        W2, _ = lot_as_fronted(turned)
        lim2 = fsr_limit(turned, option, p)
    except Exception:
        return None
    best = max(x for x in (lim2["max"], lim2["discretionary"]) if x is not None) if (lim2["max"] is not None or lim2["discretionary"]) else None
    if best is None or round(fsr, 2) > best or not W2:
        return None
    return {"street": other, "front": front_street(site) or "the street taken", "width_m": round(W2, 1), "max_fsr": best,
            "clause": lim2["discretionary_clause"] or "the schedule"}


def height_limit(site: Site, option: Option, p: Params) -> dict[str, Any]:
    """The height a schedule's rule allows: `max` and `storeys` without discretion (tenure, a transit-oriented area and
    the site's row of a table counted), `words`, and `discretionary` with its clause and whether it is for social
    housing only (RM-4 s.3.1.2.11) or for any building (RM-5 s.3.1.2.7)."""
    tenure = option.get("tenure")
    p, _need = _for_sub_area(site, p)
    out: dict[str, Any] = {"max": p.get("max_height_m"), "storeys": p.get("max_storeys"), "base": p.get("max_height_m"), "words": p.get("_sub_area_words") or "",
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
    need = _for_sub_area(site, p)[1]
    if need:
        return _which_sub_area(need)
    # a schedule that does not permit housing as a use (M-1, read 23 Nov 2026: a dwelling unit only where essential to
    # a business): that comes before any floor area, and a schedule in the rules must not read as "allowed"
    if p.get("housing_not_permitted"):
        d, path = site.get("zoning_district") or "this district", option.get("rezoning_path")
        tail = f"so it is not allowed outright; rezoning is required ({path})." if proposes_rezoning(option) else "so it is not allowed outright, and no rezoning path is stated."
        return _r(FAIL, f"{p['housing_not_permitted']} This option is housing, {tail}", {"housing_permitted": False},
                  action=f"Manager: ask a City planner whether housing is permitted in {d} at all, and by what route, before any design work.")
    lim = fsr_limit(site, option, p)
    p = _for_sub_area(site, p)[0]
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
    path = option.get("rezoning_path")
    if cap_units and units > cap_units:
        vals["max_dwelling_units"] = cap_units
        said_cap = f"{units} homes exceed the schedule's {cap_units} for this form ({p.get('dwelling_units_clause') or 'the schedule'})"
        path = _rezoning_path(option)
        if path:
            return _r(FAIL, f"{said_cap}, so it is not allowed outright; rezoning is required ({path}).",
                      vals, action=f"Manager and architect: take the rezoning ({path}) and confirm with City staff the number of homes they will support.")
        return _r(FAIL, f"{said_cap}; a larger building needs another district or a rezoning.",
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
    if lim["increases"] and not path:
        return _r(UNSURE, f"{subject} exceeds the base of {mx}; the schedule's increases ({lim['increases']}) may reach it, and they are not computed here.",
                  vals, action="Architect: work out the schedule's increases for this site's coverage, area and parking, and enter the result as the option's floor area.")
    # over the outright maximum with a rezoning path stated: the outright test fails, and the finding says the rezoning
    # is required (Kai, 20 Nov 2026: "Mention rezoning is required but fail on outright test"; it read uncertain before).
    # The by-rezoning answer reads the policy rules, not this one, so it does not change.
    # the Director's increase this site could have had, and why it stops short here (24 Nov 2026: RM-5B's narrow-site
    # cap held 1130 Jervis to 2.0 and the finding never said so)
    if lim["discretionary"] and round(f, 2) > lim["discretionary"]:
        said += f"; the Director of Planning may allow at most {lim['discretionary']} here ({lim['discretionary_clause']})"
        vals["max_fsr_discretionary"] = lim["discretionary"]
    # on a corner lot the front decides the site's width, and so a narrow-site cap: where the other street as the front
    # would allow this floor area, the answer turns on a choice the City confirms, so it is uncertain, not a fail
    alt = _other_front_fsr(site, option, p, f)
    if alt:
        vals["other_front"] = alt
        return _r(UNSURE, f"{subject} exceeds {said}, with {alt['front']} as the front. With {alt['street']} as the front the site is {alt['width_m']:g} m wide and "
                          f"the Director of Planning may allow up to {alt['max_fsr']} ({alt['clause']}), which this floor area is within. Which street is the front is the City's to say.",
                  vals, action=f"Manager: ask the City which street is the front of this corner lot, then choose it at 01 (the answer changes with it).")
    return _over_outright(option, subject, said, vals, "density")


def district_outright_height(site, option, p) -> Result:
    h = option.get("height_m")
    if h is None:
        return _r(UNSURE, "Height missing.", action="Enter the proposed height to the roof parapet in metres.")
    p, need = _for_sub_area(site, p)
    if need:
        return _which_sub_area(need)
    lim = height_limit(site, option, p)
    mx, ms = lim["max"], lim["storeys"]
    st = option.get("storeys")
    vals = {"height_m": h, "max_height_m_outright": mx, "storeys": st}
    if mx is None:      # a sub-area the plan gives no maximum for (the Oppenheimer plan's sub-area 4): discretion only
        var = lim["discretionary"]
        why = p.get("no_maximum_note") or "the plan states no maximum height here"
        if var and h <= var:
            vals["max_height_m_variance"] = var
            return _r(COND, f"No outright maximum height applies{lim['words']}: {why}. Height {h} m is within that, by discretion, not assumed.", vals,
                      action=f"Architect: confirm the height limit with City staff and ask for the height under {lim['discretionary_clause']}.")
        return _r(UNSURE, f"No outright maximum height applies{lim['words']}: {why}.", vals, action="Architect: confirm the height limit with City staff.")
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
    return _over_outright(option, what, f"the outright maximum of {limit_words}", vals, "height")


def rezoning_policy_social_housing(site, option, p) -> Result:
    if option.get("tenure") != "social_housing":
        return _r(NA, "The interim rezoning policy applies to 100% social housing; this option is not social housing.")
    if no_rezoning_stated(option):
        return _r(NA, "No rezoning is proposed (the option's approval route says so), so the rezoning policy is not read.")
    inside = site.get("in_former_community_vision_area")
    if inside is None:
        return _r(UNSURE, "Whether the site is inside a former Community Vision area (Map 1 of the policy) is not confirmed.",
                  action="Manager: check Map 1 of the policy for this address, and answer it at 01.")
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
                  action="Manager: check the City's transit-oriented areas map for this address and record the tier at 01.")
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
    # The requirement is read in rezonings (its title says so): an option that states no rezoning, or states that there
    # is none (a development permit, an outright scheme), is not tested against it (23 Nov 2026: 320 East Hastings, a
    # development-permit building, and an outright C-2A scheme both read "fail").
    if no_rezoning_stated(option):
        return _r(NA, "No rezoning is proposed (the option's approval route says so), and this requirement is read in rezonings; "
                      "a development permit is read against the district's own schedule or plan.")
    if total == 0:
        return _r(UNSURE, "Unit mix missing.", action="Enter the unit counts by bedroom type.")
    two_plus = int(u.get("two_bed", 0) or 0) + int(u.get("three_bed_plus", 0) or 0)
    three_plus = int(u.get("three_bed_plus", 0) or 0)
    # Supportive, transitional and shelter housing with too few family homes: whether the family minimum applies to that
    # use is the City's to say, so it is an open question for a person, never "add family units" (23 Nov 2026).
    kind = housing_kind(option)
    if kind != "independent" and two_plus / total + 1e-9 < p["min_two_plus_bed_share"]:
        what = HOUSING_WORDS[kind]
        return _r(UNSURE, f"The option is {what} with {two_plus} of {total} homes of two or more bedrooms, under the {_pct(p['min_two_plus_bed_share'])} "
                          f"this requirement asks of family housing; whether it applies to {what} is the City's to say, and it is not assumed here.",
                  {"units_total": total, "two_plus_bed_units": two_plus, "two_plus_bed_share": round(two_plus / total, 4),
                   "min_two_plus_bed_share": p["min_two_plus_bed_share"], "housing_type": kind},
                  action=f"Manager: ask the City's rezoning planner whether the family-unit requirement applies to {what}, and get the answer in writing.")
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
                  vals, action=("Architect: confirm with the City how the by-law's minimum is met on a lot built to its lines (street trees, a roof or courtyard planting, cash in lieu); "
                                "an arborist's survey only if a tree stands on or beside the lot." if site.get("builds_to_lot_lines") is True
                                else "Architect: obtain the arborist report and survey (" + p["survey_scope"] + ")."))
    base = (f"Schedule C requires {required} trees on {area:,.0f} m²; the option keeps {len(retained)} of {len(trees)} and plants {proposed}, "
            f"leaving {after}")
    if shortfall == 0:
        return _r(PASS, base + ", which meets the minimum.", vals)
    return _r(COND, base + f", a shortfall of {shortfall}: plant {shortfall} more at the by-law setbacks or pay ${cash:,.0f} cash in lieu; the final count is set at the development permit.",
              vals, action="Architect: find room for the missing trees (1 m from side lines, 1.5 m from the building, 2.5 m apart) or budget the cash in lieu.")


def dcl_cac(site, option, p) -> Result:
    if option.get("tenure") == "social_housing":
        # the owner's kind as a person chose it, not the word "church" in a society's name (23 Nov 2026)
        church = str(site.get("owner_type") or "").strip().lower() == "church"
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
    # what BC Housing's own copy says (read 23 Nov 2026): a four-bedroom area, and that the 2019 edition is archived
    four = f", four-bedroom {p['four_bed_net_area_m2']}" if p.get("four_bed_net_area_m2") else ""
    archived, action = "", None
    if p.get("edition_status") == "archived":
        vals["edition_status"] = "archived"
        archived = " BC Housing has archived the 2019 edition these come from: it is no longer mandatory for new projects, and no replacement is named."
        action = "Architect: ask the BC Housing project team which design standard applies before fixing unit sizes."
    if total and res:
        avg = res / total
        vals["average_gross_area_per_unit_m2"] = round(avg, 1)
        return _r(INFO, f"BC Housing minimum net unit areas are studio {mins['studio']}, one-bedroom {mins['one_bed']}, two-bedroom {mins['two_bed']}, three-bedroom {mins['three_bed_plus']}{four} m²; the option averages {avg:.0f} m² gross per unit, so net areas should be checked at the plan stage.{archived}", vals, action)
    return _r(INFO, f"BC Housing minimum net unit areas apply if BC Housing funds the project.{archived}", vals, action)


def code_basis_flags(site, option, p) -> Result:
    st = option.get("storeys") or 0
    part3 = st > p["part9_max_storeys"]
    vals = {"storeys": st, "part": 3 if part3 else "9 (if building area under 600 m²)"}
    msg = (f"{st} storeys puts the building under Part 3 of the BC Building Code 2024 and the Vancouver Building By-law 2025; "
           if part3 else f"{st} storeys may qualify for Part 9 if the building area is under 600 m²; ")
    msg += f"wood frame is standard to {6} storeys and encapsulated mass timber is permitted to {p['mass_timber_max_storeys_vbbl']} under the VBBL; seismic changes apply to permits from {p['seismic_vbbl_from']}."
    return _r(INFO, msg, vals)


def shelter_beds(site, option, p) -> Result:
    """The sleeping space a shelter's beds need, from BC Housing's Shelter Design Guidelines (read 23 Nov 2026). Not
    applicable to anything but a shelter. With `option.beds`: the floor area the beds alone need and the fewest rooms at
    the recommended four to a room; info, never a verdict, since the guidelines size much more than the sleeping rooms."""
    kind = housing_kind(option)
    if "shelter" not in housing_parts(option):
        return _r(NA, f"Not for this option: this standard is for a shelter's sleeping rooms, and the option is {KIND_WORDS[kind]}.", {"housing_type": kind})
    per, room = float(p["min_floor_area_per_bed_m2"]), int(p["recommended_max_beds_per_room"])
    beds = option.get("beds")
    vals: dict[str, Any] = {"min_floor_area_per_bed_m2": per, "recommended_max_beds_per_room": room, "beds": beds}
    if not isinstance(beds, (int, float)) or isinstance(beds, bool) or beds <= 0:
        return _r(INFO, f"BC Housing's Shelter Design Guidelines ask at least {per:g} m² of floor for each bed space and recommend no more than {room} beds a room; "
                        "enter the number of beds to see what that comes to.", vals)
    beds = int(beds)
    need, rooms = round(beds * per, 1), -(-beds // room)
    vals.update({"beds": beds, "sleeping_area_min_m2": need, "rooms_min": rooms})
    return _r(INFO, f"{beds} beds need at least {need:g} m² of sleeping floor ({per:g} m² a bed space) in at least {rooms} rooms of no more than {room} beds, by BC Housing's "
                    "Shelter Design Guidelines; washrooms, dining, staff and program space come on top and are not sized here.", vals,
              "Architect: size the sleeping rooms from the bed count, then the rest of the shelter from the same guidelines.")


# ---------------------------------------------------------------- Layer E: funding programs

def _chf_grant(p) -> float:
    """The fund's provisional grant a home: the current year's figure where the version names one, else 2025-26's."""
    return p.get("provisional_grant_per_unit_cad") or p["provisional_grant_per_unit_cad_2025_26"]

# Since 23 Nov 2026 the rules list other programs (the Indigenous, Supportive and Women's Transition Housing Funds, HEARTH,
# the shelter program, the City's CHIP, Reaching Home, Build Canada Homes) with who each is for and whether an intake is
# open, read from each program's page; none of their criteria are tested. Answer 2 names the ones written for the option.
OTHER_PROGRAMS = ("answer 2 lists the other programs in the rules written for this housing; their criteria are not tested here, "
                  "and a program not in the rules may fit as well")


def _not_the_program(option: Option, program: str, written_for: str) -> Result | None:
    """A funder rule read against housing it was not written for: not applicable, with the reason and who to ask,
    instead of a fail on a mix the program never asked of that housing (23 Nov 2026)."""
    kind = housing_kind(option)
    if kind == "independent":
        return None
    what = HOUSING_WORDS[kind]
    head = program[4:] if program.startswith("the ") else program     # as the other findings of the rule begin
    return _r(NA, f"{head}: not the test for this option. It is {what}, and {program} is written for {written_for}; "
                  f"{OTHER_PROGRAMS}.", {"housing_type": kind},
              action=f"Manager: ask BC Housing which program is open for {what}, and who funds its operation.")


def chf_fit(site, option, p) -> Result:
    other = _not_the_program(option, "the Community Housing Fund", "independent rental at a 30/50/20 mix of rents")
    if other:
        return other
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
            # a scheme with no market-rent homes is deeper than this fund's mix, not short of it: say which way it
            # misses, so the reader does not take it for "not fundable" (23 Nov 2026)
            if shares.get("market", 0) + 1e-9 < p["mix"].get("market", 0) - p["mix_tolerance"] and shares.get("deep_subsidy", 0) + shares.get("rgi", 0) > 0.9:
                msg += " (deeper affordability than this fund's mix: it points to another program, not to a weaker project)"
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
    # how the land is held: the choice made at 02 (option.land_tenure) is read where there is one; the sentence typed
    # at 01 is the fallback, read as before (23 Nov 2026: a text box decided a funder criterion by the word "confirm")
    held = str(option.get("land_tenure") or "").strip()
    tenure_plan = (option.get("land_tenure_plan") or site.get("land_tenure_plan") or "")
    need_tenure = f"land tenure (lease of at least {p['min_lease_years_nominal']} years at nominal value, or ownership)"
    if held == "lease_shorter":
        fails.append(f"the land is held on a lease shorter than the {p['min_lease_years_nominal']} years at a nominal rent the fund asks for")
    elif held in ("owned", "lease_60_plus", "air_space_parcel"):
        notes.append({"owned": "the land is owned", "lease_60_plus": f"the land is leased for {p['min_lease_years_nominal']} years or more at a nominal rent",
                      "air_space_parcel": "the homes are an air-space parcel or strata lot of their own (confirm the fund's security on it)"}[held])
    elif held == "to_confirm" or (not held and ("confirm" in tenure_plan.lower() or not tenure_plan)):
        unknown.append(need_tenure)
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
                 "provisional_grant_per_unit_cad": _chf_grant(p), "grant_fiscal_year": p.get("grant_fiscal_year") or "2025-26",
                 "indicative_grant_cad": (_chf_grant(p) * total) if total else None})
    head = "Community Housing Fund: "
    # whether the fund is taking proposals, said beside the verdict (20 Nov 2026: the what-if read "fits the funders:
    # yes" while the 2025 call had been cancelled); a closed intake is a sentence of its own, not a note at the end
    intake = program_intake(p.get("status"))
    if intake:
        vals["intake"] = intake
    if intake and intake["open"] is False:
        closed = " " + intake["note"][:1].upper() + intake["note"][1:] + (f"; {intake['more']}" if intake.get("more") else "") + "."
    else:
        closed = ""
        notes.append(f"program status: {p['status']}")
    if fails:
        return _r(FAIL, head + "does not meet the criteria: " + "; ".join(fails) + "." + closed, vals,
                  action=f"Manager: change what fails, or ask BC Housing which program fits the scheme as it is ({OTHER_PROGRAMS}).")
    if unknown:
        said = "; ".join(notes)   # one sentence, capitalised once ("; Construction must…" was each note's capital)
        # the action names what to supply and no dollar figure (23 Nov 2026: a funder-side reader took "the indicative
        # grant … would be $17,634,733" in the open items for an expectation)
        return _r(UNSURE, head + "whether it meets the criteria cannot be confirmed without the " + "; ".join(unknown) + ". "
                  + (said[:1].upper() + said[1:] + "." if said else "") + closed,
                  vals, action="Manager: supply what is missing (" + "; ".join(u.split(" (")[0] for u in unknown) + ").")
    # a pass is a pass of what was checked, and says what was not (23 Nov 2026: "meets the criteria" read as a funding
    # assessment); the rated criteria, need and demand, operator capacity and the budget are a funder's to judge
    return _r(PASS, head + "passes the eligibility items this screen checks: " + "; ".join(notes) + ". "
              "Not assessed here: need and demand, the operator's capacity, the fund's rated criteria and the budget." + closed, vals)


def bc_builds_fit(site, option, p) -> Result:
    other = _not_the_program(option, "BC Builds", "middle-income rental")
    if other:
        return other
    fails, unknown, notes = [], [], []
    if p["non_profit_must_team_with_developer"] and option.get("proponent_type") == "non_profit_society":
        partner = option.get("developer_partner")
        if partner is None or partner == "":
            unknown.append("non-profit's developer or builder partner (the program requires one; say whether there is one)")
        elif not partner:
            fails.append("a non-profit that wants to own and operate must team with a developer or builder, for-profit or non-profit, to propose (the program does not take operators alone)")
    share, disc = option.get("below_market_unit_share"), option.get("below_market_discount")
    if share is None or disc is None:
        unknown.append("share of units at least 20% below market")
    elif share + 1e-9 < p["min_below_market_unit_share"] or disc + 1e-9 < p["min_discount_to_market"]:
        fails.append(f"{_pct(share)} of units at {_pct(disc)} below market does not meet 20% at 20%")
    gfa, nonres = option.get("gfa_m2"), non_residential_m2(option)
    if gfa:
        nr = nonres / gfa
        if nr > p["max_non_residential_share"]:
            fails.append(f"non-residential space is {_pct(nr)} of area, above the 30% cap")
        else:
            notes.append(f"non-residential space is {_pct(nr)} of area, under the 30% cap")
    lo, hi = p["ground_breaking_months_after_land_letter"]
    notes.append(f"ground must break within {lo} to {hi} months of the conditional land contribution letter")
    vals = {"fails": fails, "unknown": unknown, "notes": notes, "tenant_income_limits_cad": p["tenant_income_limits_cad"], "submission": p["submission"]}
    if p.get("takeout_financing"):
        vals["takeout_financing"] = p["takeout_financing"]      # the program's own published loan terms, for the operating page
    if fails:
        return _r(FAIL, "BC Builds: does not meet the criteria: " + "; ".join(fails) + ".", vals, action="Manager: resolve the failing criteria.")
    if unknown:
        # the notes are one sentence, capitalised once (17 Nov 2026: each was, so it read "…under the 30% cap; Ground
        # must break…"), and the action asks for what is actually missing, not always the below-market share
        said = "; ".join(notes)
        asks = (["say whether a developer or builder partner is in place"] if any("partner" in u for u in unknown) else []) \
            + (["state the below-market share and discount"] if any("below market" in u for u in unknown) else [])
        return _r(UNSURE, "BC Builds: whether it meets the criteria cannot be confirmed without the " + "; ".join(unknown) + ". " + (said[:1].upper() + said[1:] + "." if said else ""),
                  vals, action=f"Manager: {' and '.join(asks) or 'supply what is missing'}; BC Builds applies opportunity by opportunity, so check the current Property Opportunity Notices.")
    return _r(PASS, "BC Builds: passes the published items this screen checks: " + "; ".join(notes) + ". "
              "BC Builds works opportunity by opportunity; middle-income rents and the team's capacity are not assessed here.", vals)


_MONTHS = {m[:3].lower(): m for m in ("January", "February", "March", "April", "May", "June", "July", "August", "September",
                                      "October", "November", "December")}


def program_intake(status: Any) -> dict[str, Any] | None:
    """A funding program's intake as its rule records it, in words: the CHF's `status` ("2025 call (RFP …) cancelled
    Feb 2026; program page says it will post when next seeking proposals (as of 22 Sep 2026)"), CMHC's `intake`
    ("continuous"). Returns {open (True, False or None where the words do not say), note (a clause starting "its …" or
    "intake …"), more (what the record adds after its first semicolon), status (the record as written)}, or None where
    the rule records nothing. Pure; `engine.summarise` puts the program's name in place of "its"."""
    if not status or not isinstance(status, str):
        return None
    s = status.strip()
    head, _, more = s.partition(";")
    low = s.lower()
    closed = re.search(r"\b(cancell?ed|closed|paused|suspended|withdrawn)\b", low)
    if closed or re.search(r"\bnot (open|accepting)\b", low):
        m = re.search(r"\b(\d{4})(?:[-/]\d{2,4})?\s+(call|intake|rfp)\b.*?\b(cancell?ed|closed|paused|suspended|withdrawn)\s+(?:in\s+|on\s+)?(\d{1,2}\s+)?([A-Za-z]{3,9})\.?\s+(\d{4})", head, re.I)
        if m:
            month = _MONTHS.get(m.group(5)[:3].lower(), m.group(5))
            # "did not proceed", not "was cancelled" (23 Nov 2026: the Province disputes that the program was cancelled;
            # applicants were told the 2025 call would not proceed), whatever the rule's record calls it
            if m.group(3).lower().startswith("cancel"):
                note = f"its {m.group(1)} {m.group(2).lower()} did not proceed ({month} {m.group(6)}), so no intake is open now"
            else:
                note = f"its {m.group(1)} {m.group(2).lower()} was {m.group(3).lower()} in {month} {m.group(6)}, so no intake is open now"
        else:
            note = f"no intake is open now ({head.strip()})"
        more = more.strip()
        if more.lower().startswith("program page"):
            more = "the " + more
        return {"open": False, "note": note, "more": more or None, "status": s}
    if re.search(r"\b(continuous|ongoing|rolling)\b", low):
        return {"open": True, "note": f"intake is {re.search(r'continuous|ongoing|rolling', low).group(0)}", "more": None, "status": s}
    if re.search(r"\bopen\b", low):
        return {"open": True, "note": f"intake: {s}", "more": None, "status": s}
    return {"open": None, "note": f"intake: {s}", "more": None, "status": s}


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


KIND_WORDS = {"independent": "independent rental", **HOUSING_WORDS}


def program_match(site, option, p) -> Result:
    """A funding program the rules list without testing its criteria (23 Nov 2026: the simulated reviewers' housing,
    supportive, transitional, shelter and Indigenous-led, had no program in the stack, and the funders answer could only
    say so). The rule records who the program is for, what it funds, how a project enters it and whether an intake is
    open, each from the page cited; this check says whether the option is the kind of housing it is written for.

    Not applicable where it is not (the kind of housing, a requirement the option answers no to, another municipality,
    a proponent the program does not take). Otherwise info, with `values.match` true where everything it asks about the
    option is known, or "if" where one answer is missing (`values.asks` names it). Info never moves a verdict: a match
    is a door to knock on, and the finding says its criteria are not tested here. Where the program fixes something the
    option states (the Indigenous Housing Fund's homes are all rent geared to income), the finding says how they differ."""
    kind = housing_kind(option)
    for_types = p.get("for_housing_types") or list(HOUSING_TYPES)
    parts = housing_parts(option)
    hit = [k for k in parts if k in for_types]
    if not hit:
        return _r(NA, f"Not for this option: the program is for {_or([KIND_WORDS[k] for k in for_types])}, and the option is {KIND_WORDS[kind]}.",
                  {"match": False, "housing_type": kind})
    if kind not in for_types:      # a part of the building (24 Nov 2026: Glen Drive's supportive homes and shelter beds)
        kind = hit[0]
    where = str(p.get("municipality") or "").lower()
    town = str((site or {}).get("municipality") or "City of Vancouver").lower()
    if where and where not in town:
        return _r(NA, f"Not for this option: the program is for sites in {where.title()}, and this one is in {(site or {}).get('municipality')}.", {"match": False})
    takes = p.get("eligible_proponent_types")
    who = option.get("proponent_type")
    if takes and who and who not in takes:
        return _r(NA, f"Not for this option: the program takes {_or([t.replace('_', ' ') for t in takes])} proponents, and this one is a {str(who).replace('_', ' ')}.", {"match": False})
    asks: list[str] = []
    for key, flag, said in (("requires_indigenous_led", "indigenous_led", "Indigenous-led, or partnered with an Indigenous housing provider or Nation"),
                            ("requires_women_leaving_violence", "women_leaving_violence", "for women, gender-diverse people and children leaving violence")):
        if not p.get(key):
            continue
        if option.get(flag) is False:
            return _r(NA, f"Not for this option: the program is for housing that is {said}, and the option says it is not.", {"match": False})
        if option.get(flag) is None:
            asks.append(said)
    vals: dict[str, Any] = {"match": "if" if asks else True, "ended": bool(p.get("ended")), "asks": asks, "housing_type": kind, "for_housing_types": for_types,
                            "what": p.get("what"), "funds": p.get("funds"), "how_a_project_enters": p.get("how_a_project_enters")}
    intake = program_intake(p.get("intake"))
    if intake:
        vals["intake"] = intake
    lead = (f"Would be a program for this housing if it is {' and '.join(asks)} (not said on the option)" if asks
            else f"A program for this kind of housing ({KIND_WORDS[kind]})")
    bits = [f"{lead}: {p.get('what')}."]
    if p.get("funds"):
        bits.append(f"It funds {p['funds']}.")
    if p.get("how_a_project_enters"):
        bits.append(f"A project enters {p['how_a_project_enters']}.")
    # who owns the building and what residents pay, where the program's framework says (read 23 Nov 2026): a society
    # planning to build on its own land needs to know the Province owns what the Supportive Housing Fund builds
    for key, lead_in in (("owner", "The building is owned by"), ("rents", "Rents:")):
        if p.get(key):
            vals[key] = p[key]
            bits.append(f"{lead_in} {p[key]}.")
    if intake:
        note = intake["note"]
        bits.append((note[:1].upper() + note[1:] if not note.startswith("its ") else "Its " + note[4:]) + ".")
    # the one thing some programs fix that an option states: every home rent geared to income
    tiers, total = option.get("rent_tiers_units") or {}, _units_total(option)
    if p.get("all_units_rgi") and tiers and total:
        market = int(tiers.get("market") or 0)
        if market:
            vals["differs"] = {"market_units": market}
            bits.append(f"Its homes are all rent geared to income; this option has {market} market-rent home{'s' if market != 1 else ''}, which it would not carry.")
    bits.append("Its criteria are not tested here.")
    for k in ("proponents_unverified", "amounts_unverified", "community_entity_unverified"):
        if p.get(k):
            vals[k] = p[k]
    return _r(INFO, " ".join(bits), vals)


def _or(words: list[str]) -> str:
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " or " + words[-1]


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
    # a side yard the schedule sets as a share of a narrow site's width (RT-3, RT-4, RT-5, RT-8: 10% where the site is
    # 15.0 m wide or less; RT-10: 12.0 m). 24 Nov 2026: RT-5 tested 1.5 m on a 7.6 m lot, where the schedule asks 0.76 m.
    narrow = p.get("side_yard_narrow")
    if narrow and mins["side"] is not None:
        W, _ = lot_as_fronted(site)
        if W and W <= float(narrow["max_width_m"]) + 1e-9:
            mins["side"] = round(float(narrow["share"]) * W, 2)
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


def front_street(site: Site) -> str | None:
    """The street the lot is fronted on as the site records it (`front_face {street}`, else the site's or the context's
    street, else the first of a corner lot's two), or None: a front named by side or edge, or no street recorded."""
    ff = site.get("front_face")
    if ff:
        return ff.get("street") if isinstance(ff, dict) else None
    streets = corner_streets(site)
    return (site.get("front_street") or ((site.get("context") or {}).get("street") or {}).get("name")
            or ((site.get("parcel") or {}).get("street") or {}).get("name") or (streets[0] if streets else None)
            or ((site.get("osm") or {}).get("frame") or {}).get("front_street"))


def yard_clause(p: Params, which: str) -> str | None:
    """The clause a schedule's yard is in: the rule's `<which>_yard_clause` where it names one, else read off the rule
    source's section ("s.3.1.2.7 and 3.1.2.17 (rear yard 20.0 m, …" gives s.3.1.2.7; the engine hands the section to
    district_setbacks as `_section`). None where neither says."""
    if p.get(f"{which}_yard_clause"):
        return str(p[f"{which}_yard_clause"])
    m = re.search(rf"(s\.\d+(?:\.\d+)+(?:\([a-z]\))?)[^;()]*?\({which} yard", str(p.get("_section") or ""))
    return m.group(1) if m else None


# The narrowest envelope this screen reads as room for a home (24 Nov 2026, a declared placeholder): a BC Housing
# studio of 33 m² at about 6 m deep needs about 5.5 m of width; below 5.0 m no home of the minimum areas lays out.
MIN_ENVELOPE_M = 5.0


def _no_envelope(site, option, p, mins, lane, eff, W, D, short, vals) -> Result:
    """The yards the option keeps (at least the schedule's) leave no plate on the lot as fronted. Uncertain, never a
    fail: the other street as the front of a corner lot, a lane behind, or the Director's variance may leave one (decided
    with Kai, 17 Nov 2026, on 609 Heatley Ave).

    The finding reads in three parts (20 Nov 2026, a reviewer: "a clause essay"): the plain consequence first ("On
    Heatley Ave as the front, the RT-3 yards leave no room to build: the rear yard is 20.0 m on a lot 15.2 m deep."),
    then the way out with its numbers ("With Keefer St as the front, a plate of about 12.2 × 13.5 m (165 m²) fits."), then
    the task with the person named, the clause numbers last ("Manager: ask the City which street is the front (s.3.1.2.7
    rear yard; s.3.1.2.17 a lane behind; s.3.1.2.21 the Director's variance for affordable housing).")."""
    district = site.get("zoning_district") or "the district's"
    w_left, d_left = W - 2 * eff["side"], D - eff["front"] - eff["rear"]
    front = front_street(site)
    # the consequence, in plain words
    why = []
    if 0 < d_left < MIN_ENVELOPE_M:
        why.append(f"the front and rear yards leave {d_left:.1f} m of a lot {D:.1f} m deep, less than the {MIN_ENVELOPE_M:g} m a home needs")
    if 0 < w_left < MIN_ENVELOPE_M:
        why.append(f"two side yards of {eff['side']:.1f} m leave {w_left:.1f} m of a lot {W:.1f} m wide, less than the {MIN_ENVELOPE_M:g} m a home needs")
    if d_left <= 0:
        rear = f"{eff['rear']:.1f} m" + (f" ({lane['rear_yard_m']:.1f} m less {lane['to_centre_line_m']:g} m to the lane's centre line)" if lane else "")
        if eff["front"] <= 0 or eff["rear"] >= D - 1e-9:
            why.append(f"the rear yard is {rear} on a lot {D:.1f} m deep")
        else:
            why.append(f"a front yard of {eff['front']:.1f} m and a rear yard of {rear} take more than the lot's {D:.1f} m depth")
    if w_left <= 0:
        why.append(f"two side yards of {eff['side']:.1f} m take the whole of a lot {W:.1f} m wide")
    lead = (f"On {front} as the front" if front else "As the lot is fronted") + f", the {district} yards leave no room to build: " + " and ".join(why) + "."
    ways: list[str] = []          # the way out, with its numbers
    tasks: list[str] = []         # the short task the finding names
    asks: list[str] = []          # the action, in full
    lane_said = bool(lane)
    vals.update({"no_envelope": True, "lot_as_fronted_m": {"frontage": round(W, 2), "depth": round(D, 2)},
                 "envelope_m": {"width": round(max(0.0, w_left), 2), "depth": round(max(0.0, d_left), 2)}})
    if front:
        vals["front_street"] = front
    # the option's own yards larger than the schedule asks, where the schedule's would leave room (24 Nov 2026: a 7.6 m
    # RT-5 lot kept 1.5 m side yards where the schedule asks 10% of the width, 0.76 m)
    sb = option.get("setbacks_m") or {}
    wider = [k for k in mins if mins[k] is not None and sb.get(k) is not None and float(sb[k]) > float(mins[k]) + 1e-9]
    if wider:
        w_s = W - 2 * float(mins["side"] or 0)
        d_s = D - float(mins["front"] or 0) - float(mins["rear"] or 0)
        if w_s >= MIN_ENVELOPE_M and d_s >= MIN_ENVELOPE_M:
            ways.append(f"The schedule asks less than the option keeps ({'; '.join(f'{k} {mins[k]:g} m against {float(sb[k]):g} m' for k in wider)}): "
                        f"with its minimums a plate of about {_m(w_s)} × {_m(d_s)} m ({w_s * d_s:,.0f} m²) fits.")
            tasks.append("set the option's yards to the schedule's minimums")
            asks.append("set the option's yards to the schedule's minimums, which leave a plate")
            vals["with_schedule_yards_m"] = {"width": round(w_s, 2), "depth": round(d_s, 2)}
    # the other street as the front: the lot turned a quarter, the same yards (a front yard the schedule fixes, else the
    # most it can ask)
    other = other_front(site)
    if other:
        f_alt = mins["front"] if mins["front"] is not None else (p.get("max_front_yard_m") if p.get("max_front_yard_m") is not None else eff["front"])
        rear_base = lane["rear_yard_m"] if lane else mins["rear"] or 0
        w2, d2 = D - 2 * eff["side"], W - float(f_alt) - float(rear_base)
        alt = {"street": other, "frontage_m": round(D, 2), "depth_m": round(W, 2), "front_yard_m": f_alt,
               "envelope_m": {"width": round(max(0.0, w2), 2), "depth": round(max(0.0, d2), 2)}}
        if w2 >= MIN_ENVELOPE_M and d2 >= MIN_ENVELOPE_M:
            words = f"With {other} as the front, a plate of about {_m(w2)} × {_m(d2)} m ({w2 * d2:,.0f} m²) fits"
            if mins["front"] is None and p.get("max_front_yard_m") is not None:
                words += f" behind a front yard of up to {f_alt:g} m"
            if p.get("rear_yard_lane_reduction"):
                d3 = d2 + LANE_TO_CENTRE_LINE_M
                alt["envelope_with_lane_m"] = {"width": round(w2, 2), "depth": round(d3, 2)}
                words += f", or {_m(w2)} × {_m(d3)} m ({w2 * d3:,.0f} m²) if a lane runs behind it"
                lane_said = True
            ways.append(words + ".")
            tasks.append("ask the City which street is the front")
            asks.append(f"ask the City which street is the front of the corner lot (the schedule does not say) and choose it at 01; {other} as the front leaves a plate"
                        + (f", so if it is the front, say whether a lane runs behind it" if p.get("rear_yard_lane_reduction") else ""))
        else:
            ways.append(f"With {other} as the front the yards leave no room either ({_m(max(0.0, w2))} × {_m(max(0.0, d2))} m).")
        vals["other_front"] = alt
    # a lane behind the lot as fronted, where the site has not said and it would leave a plate
    ctx = site.get("context") or {}
    if p.get("rear_yard_lane_reduction") and not lane and ctx.get("lane_behind") is None and mins["rear"] is not None:
        d_lane = D - eff["front"] - (float(mins["rear"]) - LANE_TO_CENTRE_LINE_M)   # the schedule's rear yard, reduced
        if d_lane >= MIN_ENVELOPE_M and w_left >= MIN_ENVELOPE_M:
            ways.append(f"If a lane runs behind the lot, a plate of about {_m(w_left)} × {_m(d_lane)} m fits.")
            tasks.append("say whether a lane runs behind the lot")
            asks.append("say whether a lane runs behind the lot")
            lane_said = True
    # the Director of Planning's variance for affordable housing, a question for the City, never assumed
    var = p.get("affordable_variance")
    clause = None
    if var:
        clause = var.get("clause") if isinstance(var, dict) else str(var)
        needs = var.get("needs") if isinstance(var, dict) else ""
        words = ("Or the" if ways else "The") + " Director of Planning may vary the yards for affordable housing" + (
            " (this option is social housing, which can qualify)" if option.get("tenure") == "social_housing" else "")
        from .massing import PLATE_MIN_DEPTH_M
        room = D - eff["front"]
        if d_left <= 0 < room and w_left > 0:
            depth = min(PLATE_MIN_DEPTH_M, room)
            rear_max = room - depth
            words += f": a rear yard of at most {rear_max:.1f} m (against {mins['rear']:g} m) leaves a plate {depth:.1f} m deep on this front"
            vals["variance"] = {"clause": clause, "rear_yard_for_plate_m": round(rear_max, 2), "plate_depth_m": round(depth, 2)}
        else:
            vals["variance"] = {"clause": clause}
        if needs:
            vals["variance"]["needs"] = needs
        ways.append(words + "; that is the City's to grant, not assumed here.")
        tasks.append("ask the Director of Planning about a variance")
        asks.append(f"or ask the Director of Planning about a variance under {clause}")
    # the clause numbers, last
    clauses = []
    if d_left <= 0 and yard_clause(p, "rear"):
        clauses.append(f"{yard_clause(p, 'rear')} rear yard")
    if w_left <= 0 and yard_clause(p, "side"):
        clauses.append(f"{yard_clause(p, 'side')} side yards")
    if lane_said and p.get("rear_yard_lane_reduction"):
        clauses.append(f"{p['rear_yard_lane_reduction']} a lane behind")
    if clause:
        clauses.append(f"{clause} the Director's variance for affordable housing")
    cited = f" ({'; '.join(clauses)})" if clauses else ""
    own = f" The option's own setbacks are under the schedule's minimums too ({'; '.join(short)})." if short else ""
    if tasks:
        task = f" Manager: {tasks[0]}{cited}."
    else:
        task = f" Architect: the yards must change before a building fits; state the relaxation to ask for{cited}."
    finding = lead + (" " + " ".join(ways) if ways else "") + own + task
    action = ("Manager: " + "; ".join(asks) + ".") if asks else "Architect: the yards must change before a building fits; state the relaxation to ask for."
    return _r(UNSURE, finding, vals, action=action)


# The uses a building of each kind is read under, in a district schedule's use table (s.2.1), in the order tried
# (25 Nov 2026, the second panel: "use permissibility, a shelter or a clinic, is never asked"). Which use a building is
# stays the City's to say from Section 2's definitions; a shelter, above all, may be read as any of three.
APARTMENT_USES = ("Multiple Dwelling", "Apartment")
GROUND_USES = ("Townhouse", "Freehold Rowhouse", "Rowhouse", "Multiplex", "Multiple Dwelling", "Apartment")   # a Triplex or a Duplex only at three or two homes
SHELTER_USES = ("Group Residence", "Social Service Centre", "Community Care or Assisted Living Facility - Class B")
CLINIC_USES = ("Health Care Office", "Health Enhancement Centre")
APPROVAL_WORDS = {"outright": "an outright approval use", "conditional": "a conditional approval use, which the Director of Planning may approve"}


def uses_for(option: Option) -> tuple[str, tuple[str, ...]]:
    """What the option is, in a few words, and the uses in a schedule's table it can be read under. Pure."""
    o = option or {}
    kind = housing_kind(o)
    if kind == "shelter":
        return "a shelter", SHELTER_USES
    bt = str(o.get("building_type") or "").strip().lower()
    nonres = non_residential_m2(o) > 0
    if bt == "ground_oriented":
        n = _units_total(o)
        few = (("Triplex",) if 0 < n <= 3 else ()) + (("Duplex",) if 0 < n <= 2 else ())
        return "ground-oriented homes", GROUND_USES + few + (("Mixed-Use Residential Building",) if nonres else ())
    what = "an apartment building" + (" with floors that are not homes" if nonres else "")
    return what, APARTMENT_USES + (("Mixed-Use Residential Building",) if nonres else ())


def district_outright_use(site, option, p) -> Result:
    """Whether the schedule's use table lists the use the option is: pass where it is an outright approval use,
    conditional where it is a conditional approval use (the Director of Planning's discretion, values
    `conditional_use`), fail where an apartment building's uses are not in the table at all, uncertain where a shelter
    or ground-oriented homes may be read under a use the table lacks. A rezoning sets the uses, so an option that
    proposes one reads info. Every row is quoted with its page."""
    uses = p.get("uses") or {}
    what, want = uses_for(option)
    found = [(u, uses[u]) for u in want if u in uses]
    best = next((x for x in found if x[1]["approval"] == "outright"), found[0] if found else None)
    rows = "; ".join(f"{v['as']}: {v['approval']} (p. {v['page']})" for _, v in found)
    vals = {"building": what, "uses_tried": list(want), "uses_listed": {u: v["approval"] for u, v in found}}
    parts = housing_parts(option or {})
    if "shelter" in parts and housing_kind(option or {}) != "shelter":
        sh = [(u, uses[u]) for u in SHELTER_USES if u in uses]
        vals["shelter_uses_listed"] = {u: v["approval"] for u, v in sh}
    path = _rezoning_path(option or {})
    if path:
        return _r(INFO, f"The rezoning ({path}) sets the uses. The schedule as it stands lists, for {what}: " + (rows or "none of " + ", ".join(want)) + ".", vals)
    if housing_kind(option or {}) == "shelter":
        vals["conditional_use"] = bool(found) and all(v["approval"] == "conditional" for _, v in found)
        return _r(UNSURE, f"Which use a shelter is, the City says from the by-law's definitions; the schedule lists " + (rows if rows else f"none of {', '.join(want)}") + ".",
                  vals, action="Manager: ask a City planner which use the shelter is (a group residence, a social service centre or a care facility) and whether this district allows it.")
    if not best:
        listed_mu = "Mixed-Use Residential Building" in uses and "Mixed-Use Residential Building" not in want
        if listed_mu:
            return _r(UNSURE, f"The schedule lists none of {', '.join(want)} for a new building; it lists homes as a Mixed-Use Residential Building ({uses['Mixed-Use Residential Building']['approval']}), "
                              "which needs floors that are not homes.", vals,
                      action="Manager and architect: add the floors that are not homes the schedule asks of a mixed-use building, or take a rezoning for an apartment building.")
        if want[:len(GROUND_USES)] == GROUND_USES:
            return _r(UNSURE, f"The schedule lists none of {', '.join(want)} for a new building, so which use these homes are is a question for the City.", vals,
                      action="Architect: ask a City planner which use the homes are, and whether this district allows it.")
        return _r(FAIL, f"The schedule lists none of {', '.join(want)} for a new building: {what} is not a use this district allows outright or conditionally, so it needs a rezoning.",
                  vals, action="Manager: a rezoning (or another site) is the path; ask a City planner before any offer on the land.")
    u, v = best
    vals["use"] = v["as"]
    if v["approval"] == "outright":
        return _r(PASS, f"{v['as']} is {APPROVAL_WORDS['outright']} here (p. {v['page']}).", vals)
    vals["conditional_use"] = True
    are = "are" if what.endswith("homes") else "is"
    return _r(COND, f"{v['as']} is {APPROVAL_WORDS['conditional']} (p. {v['page']}): {what} here {are} not allowed outright; {'they are' if are == 'are' else 'it is'} approved at the Director's discretion.",
              vals, action="Architect: make the case for the conditional use with the development permit application.")


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
    if W > 0 and D > 0 and (D - eff["front"] - eff["rear"] < MIN_ENVELOPE_M or W - 2 * eff["side"] < MIN_ENVELOPE_M):
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
    "district_outright_use": district_outright_use,
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
    "program_match": program_match,
    "shelter_beds": shelter_beds,
}
