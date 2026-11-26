"""Write the First Read memo from a ledger (+ massing, + optional diff). Markdown and HTML.

The memo answers three questions in order, then shows its work:

    1. Is it allowed?          layers A to C, outright and by rezoning
    2. Does it fit the funders? layer E, the programs the option targets
    3. What is still unsure, and who resolves it?

Every finding prints the numbers it used and links the source it came from. The version stamp
at the top ties the memo to the exact rule set, so two memos can be compared.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from .engine import counts_outright, takes_ref
from .rules_loader import district_of

STATUS_WORD = {
    "pass": "Pass", "conditional": "Conditional", "fail": "Fail", "uncertain": "Uncertain",
    "not_applicable": "Not applicable", "info": "Info",
}
# the UI's status set (DESIGN.md), deepened where white text sits on it: every pair clears 4.5:1
STATUS_COLOR = {
    "pass": "#2f7d4a", "conditional": "#9a6b00", "fail": "#c81e1e", "uncertain": "#a3640c",
    "not_applicable": "#5f6672", "info": "#2a6fb8",
}


def _src(r: dict) -> str:
    s = r.get("source") or {}
    t, u, sec = s.get("title"), s.get("url"), s.get("section")
    if not t and not u:
        return ""
    label = t or u
    if sec:
        label += f", {sec}"
    return f"[{label}]({u})" if u else label


def _n(x: Any, unit: str = "") -> str:
    """A figure with a thousands separator, or 'not given' where the input left it blank."""
    if x is None or x == "":
        return "not given"
    try:
        return f"{x:,}{unit}"
    except (TypeError, ValueError):
        return f"{x}{unit}"


def _fmt_vals(v: dict) -> str:
    bits = []
    for k, x in v.items():
        if isinstance(x, (dict, list)):
            continue
        if isinstance(x, float):
            x = f"{x:,.3f}".rstrip("0").rstrip(".")
        bits.append(f"{k.replace('_', ' ')} = {x}")
    return "; ".join(bits)


# The terms a reader outside the trade meets in the memo, each in a sentence; printed only where the memo uses the word.
GLOSSARY = [
    ("FSR", r"\bFSR\b", "floor space ratio: the building's floor area divided by the site's area. FSR 3.0 on a 1,000 m² lot is 3,000 m² of floor."),
    ("Outright", r"[Oo]utright", "what the zoning district allows with a permit and no vote of Council."),
    ("Rezoning", r"[Rr]ezoning", "asking Council to change what the land may hold, after a public hearing; what it allows is negotiated, not read from a table."),
    ("CD-1", r"\bCD-1\b", "a zoning district written for one site, with its own by-law."),
    ("RGI", r"\bRGI\b|rent[- ]geared[- ]to[- ]income", "rent geared to income: the tenant pays a share of household income, about 30%, whatever the home would rent for."),
    ("Deep subsidy", r"[Dd]eep[- ]subsidy", "homes for the lowest incomes, such as people on income or disability assistance or a basic pension; the rent is a small fixed amount."),
    ("HILs", r"\bHILs?\b|Housing Income Limits", "Housing Income Limits: the highest household income, set by BC Housing by home size and place, at which a household qualifies for subsidized housing."),
    ("Net operating income", r"[Nn]et operating income", "the rent left each year after vacancy, running costs and the reserve, before any loan payment."),
    ("Debt coverage", r"coverage|\bDCR\b", "how many times the yearly net income covers the yearly loan payment; a lender asks for more than once."),
    ("Plate", r"\bplate\b", "one floor of the building, as an outline."),
    ("Setback", r"[Ss]etback|\byards?\b", "the strip of the lot along each property line that must stay unbuilt."),
    ("Placeholder", r"[Pp]laceholder", "a figure the tool assumes until the project's own replaces it; every one is marked."),
]


def layout_open_items(lay: dict | None) -> list[dict]:
    """What the first layout leaves open, as rows of answer 3: homes that do not fit the plates, blocks placed by hand
    that break the plate, and floors that do not pass the exit clauses. The page's memo/answers.js layoutOpenItems is the
    twin; memo.md lacked them until 23 Nov 2026, so a memo could read "fits the funders" on 123 homes over a plan that
    placed 93 with no row saying so. Pure."""
    if not lay:
        return []
    out: list[dict] = []
    short = [s for s in lay.get("shortfall") or [] if s.get("units") or s.get("area_m2")]
    total, placed = lay.get("units_total"), lay.get("units_placed")
    if short and total:
        words = ", ".join((f"{s['units']} " if s.get("units") else "") + str(s.get("label") or "").lower() for s in short)
        out.append({"title": "Homes that do not fit the plates", "status": "conditional",
                    "action": f"Architect: {placed} of {total} homes fit the plates on {len(lay.get('floors') or [])} floors at the unit sizes assumed; did not fit: {words}. "
                              f"More storeys, a larger plate, smaller homes or a smaller program. The funders' checks and the money count all {total}."})
    broken = lay.get("geometry") or []
    if broken:
        out.append({"title": "Blocks placed by hand that break the plate", "status": "fail",
                    "action": f"Architect: {len(broken)} problem{'' if len(broken) == 1 else 's'} in the hand placement: "
                              + "; ".join(str(g.get("note") or g.get("kind") or "") for g in broken[:3]) + ("; …" if len(broken) > 3 else "") + ". Fix them in Edit blocks before issuing."})
    eg = lay.get("egress") or {}
    if eg.get("status") in ("fail", "conditional", "uncertain"):
        floors = eg.get("floors") or []
        bad = [x for x in floors if x.get("status") != "pass"]
        out.append({"title": "Exits: travel distance, separation and dead ends (BC Building Code)", "status": eg["status"],
                    "action": f"Architect: {len(bad)} of {len(floors)} floors {'does' if len(bad) == 1 else 'do'} not pass the exit clauses. {eg.get('summary') or ''} "
                              "Move or add a stair; the clause figures are unverified against the code text."})
    return out


OPEN_RANK = {"fail": 0, "uncertain": 1, "conditional": 2}
TIER_WORDS = {"market": "at market rent", "rgi": "rent geared to income", "deep_subsidy": "deep subsidy"}


def _cad(x) -> str:
    """Dollars as a board reads them: $45.7M, $890,295."""
    if x is None:
        return "not computed"
    x = float(x)
    return f"${x / 1e6:,.1f}M" if abs(x) >= 1e6 else f"${x:,.0f}"


from .checks import operator_of      # who operates: the option's operator, the signing organization, or the proponent line


def front_sheet(ledger: dict, proforma: dict | None = None, layout: dict | None = None) -> dict:
    """The memo's front sheet, shaped as an ask (25 Nov 2026; all four first-panel reviewers: "who is housed, who
    operates, which program, the amount, the top three risks"). Read from the ledger, the pro-forma and the layout alone,
    so it adds no figure of its own. The page's memo/front.js is its twin. Pure.

    {housed, operator, programs, money: {capital, asked: [{label, value, status}], to_find, share, surplus, verdict} or
    None, decision, verdicts: [{label, verdict}], open_items: [{title, status, action}], open_total}"""
    from .checks import housing_kind, HOUSING_WORDS
    from .engine import program_name
    opt, site = ledger["inputs"]["option"], ledger["inputs"]["site"]
    ans = ledger["summary"]["answers"]
    kind = housing_kind(opt)
    units = opt.get("units") or {}
    homes = sum(int(v or 0) for v in units.values() if isinstance(v, (int, float)))
    beds = opt.get("beds") if isinstance(opt.get("beds"), (int, float)) and not isinstance(opt.get("beds"), bool) and opt.get("beds") > 0 else None
    what = "independent rental" if kind == "independent" else HOUSING_WORDS[kind]
    head = (f"{homes} home{'s' if homes != 1 else ''}" if homes else "") + (f"{' and ' if homes else ''}{int(beds)} beds" if beds else "")
    housed = f"{head or 'No homes entered'}, {what}"
    tenure = str(opt.get("tenure") or "").replace("_", " ")
    if tenure:
        housed += f" ({tenure})"
    sup = int(opt.get("supportive_units") or 0)
    if sup and kind == "independent":
        housed += f", {sup} of them supportive homes"
    tiers = opt.get("rent_tiers_units") or {}
    if any(tiers.get(k) for k in TIER_WORDS):
        housed += ": " + ", ".join(f"{int(tiers[k])} {w}" for k, w in TIER_WORDS.items() if tiers.get(k))
    lay = layout or {}
    if homes and lay.get("units_total") and lay.get("units_placed") is not None and lay["units_placed"] < lay["units_total"]:
        housed += f"; {lay['units_placed']} of the {lay['units_total']} fit the first plans"
    signed = (opt.get("operations") or {}).get("signed") if isinstance((opt.get("operations") or {}).get("signed"), dict) else None
    op = operator_of(opt)
    operator = (op or "Not named") + ("; the operating figures are signed by " + signed["by"] if signed and signed.get("by")
                                      else "; the operating figures are not signed by an operator" if op else "")
    targets = opt.get("target_programs") or []
    res = ledger.get("results") or []
    named = [program_name(r) for r in res if r.get("layer") == "E" and r["rule_id"] in targets]
    fd = ans.get("funded") or {}
    if named:
        programs = ", ".join(named) + (f". {fd['words']}" if fd.get("words") else "")
    else:
        doors = [m["program"] for m in fd.get("matches") or [] if not m.get("ended") and not m.get("if")]
        programs = ("None targeted; written for this kind of housing and not tested: " + ", ".join(doors)) if doors else "None targeted"
    money = None
    if proforma and proforma.get("available"):
        rows = (proforma.get("funding") or {}).get("sources") or []
        asked = [{"label": r["label"], "value": r["value"], "status": r["status"]} for r in rows
                 if r["counted"] and r["status"] in ("illustrative", "applied", "assumed")]
        gap = (proforma.get("gap") or {}).get("value")
        money = {"capital": (proforma.get("capital") or {}).get("total"), "asked": asked,
                 "to_find": gap if gap is not None and gap > 0 else 0 if gap is not None else None,
                 "share": (proforma.get("gap") or {}).get("share_of_capital"),
                 "surplus": -gap if gap is not None and gap < 0 else None,
                 "verdict": proforma["verdict"]["word"]}
    routes = (ans.get("allowed") or {}).get("routes") or {}
    verdicts = [{"label": v["label"], "verdict": v["verdict"]} for v in routes.values()] or [
        {"label": "Outright", "verdict": ans["allowed"]["outright"]["verdict"]}, {"label": "By rezoning", "verdict": ans["allowed"]["by_rezoning"]["verdict"]}]
    verdicts.append({"label": "The funders' criteria", "verdict": fd.get("words") or fd.get("verdict")})
    if money:
        from .proforma import VERDICT_WORDS
        verdicts.append({"label": "The money", "verdict": VERDICT_WORDS.get(money["verdict"], money["verdict"])})
    items = list(ans.get("unsure") or []) + layout_open_items(layout)
    ranked = sorted(range(len(items)), key=lambda i: (OPEN_RANK.get(items[i].get("status"), 3), i))
    top = [{"title": items[i]["title"], "status": items[i]["status"], "action": items[i].get("action") or ""} for i in ranked[:3]]
    return {"housed": housed, "operator": operator, "programs": programs, "money": money,
            "decision": str(opt.get("decision_sought") or "").strip() or None,
            "verdicts": verdicts, "open_items": top, "open_total": len(items)}


def front_markdown(fs: dict) -> list[str]:
    """The front sheet for memo.md: a table a board reads first."""
    m = fs["money"]
    if m:
        ask = "; ".join(f"{a['label']}, {_cad(a['value'])} ({a['status']})" for a in m["asked"]) or "nothing from a program"
        amount = (f"Capital cost {_cad(m['capital'])}. Asked: {ask}. "
                  + (f"Still to find: {_cad(m['to_find'])} ({m['share'] * 100:.0f}% of the cost)." if m.get("to_find") else
                     f"The sources counted cover it, {_cad(m['surplus'])} to spare." if m.get("surplus") else "The sources counted cover it."))
    else:
        amount = "Not computed."
    L = ["## The ask", "", "| | |", "|---|---|",
         f"| Who is housed | {fs['housed']} |", f"| Who operates | {fs['operator']} |", f"| Which program | {fs['programs']} |",
         f"| The amount | {amount} |", f"| The decision wanted | {fs['decision'] or 'not stated'} |",
         "| The answers | " + " · ".join(f"{v['label']}: {v['verdict']}" for v in fs["verdicts"]) + " |"]
    if fs["open_items"]:
        L.append(f"| The top {len(fs['open_items'])} of {fs['open_total']} open items | "
                 + " ".join(f"{i + 1}. {u['title']} ({STATUS_WORD.get(u['status'], u['status']).lower()})." for i, u in enumerate(fs["open_items"])) + " |")
    L.append("")
    return L


def markdown(ledger: dict, massing: dict | None = None, diff: dict | None = None, title: str | None = None,
             revit: dict | None = None, proforma: dict | None = None, layout: dict | None = None, massing_error: str | None = None,
             short: bool = False) -> str:
    """The memo. `short` (25 Nov 2026, the second panel's small-lot architect) keeps the front sheet, the answers, the
    money's summary and the sources the rules that apply cite, and leaves the massing, the layout, the full ledger and
    the stamp's file hashes to the full memo."""
    run, res, summ = ledger["run"], ledger["results"], ledger["summary"]
    site, opt = ledger["inputs"]["site"], ledger["inputs"]["option"]
    ans = summ["answers"]
    L: list[str] = []
    L.append(f"# First Read memo: {site.get('address', site.get('id'))}")
    L.append("")
    # the address as the person typed it, where the City lists the lot under another (23 Nov 2026: a board would not
    # recognise "438 Gore Ave" as 320 East Hastings Street)
    typed = str((site.get("lookup") or {}).get("typed") or "").strip()
    if typed and (site.get("lookup") or {}).get("civic_mismatch"):
        L.append(f"*Looked up as \"{typed}\"; the City lists the lot as {site.get('address')}.*  ")
    if opt.get("as_built") is True:
        L.append("> **A calibration run against a completed project.** The figures are the project's as built or approved; a fail or a \"not assessed\" below shows a limit of the rules in this tool, not of the building.")
        L.append("")
    L.append(f"**Option:** {opt.get('name', opt.get('id'))}  ")
    # a proponent not named is said so (23 Nov 2026: "Proponent: None (non profit society)" on every unnamed memo)
    L.append(f"**Proponent:** {opt.get('proponent') or 'not named'} ({str(opt.get('proponent_type') or 'type not given').replace('_', ' ')})  ")
    if opt.get("operator"):
        L.append(f"**Operator:** {opt['operator']}  ")
    # whose the operating figures are (24 Nov 2026): signed by the operator, or not seen by one
    signed = ((opt.get("operations") or {}).get("signed") or {}) if isinstance((opt.get("operations") or {}).get("signed"), dict) else {}
    if signed.get("by"):
        L.append(f"**Operating figures:** signed by {signed['by']}" + (f" of {signed['org']}" if signed.get("org") else "") + (f", {signed['on']}" if signed.get("on") else "") + "  ")
    elif opt.get("operations") or opt.get("operator"):
        L.append("**Operating figures:** not yet signed by an operator  ")
    L.append(f"**Rules as of:** {run['as_of']} · **version stamp:** `{run['stamp']['stamp']}` · engine {run['engine_version']}  ")
    L.append("")
    L.append("> Deterministic output of the rule stack listed under *Sources*. Same inputs and rule set give the same memo. "
             "It is a feasibility screen, not legal, planning or funding advice; every number links to the document it came from, so check it there. "
             "An independent student tool: not affiliated with, reviewed by or a position of BC Housing, the Province, CMHC or the City of Vancouver.")
    # the first layout's open items belong on page one: a count the plates do not hold changes how answers 2 and 4 read
    lay_items = layout_open_items(layout)
    unplaced = (f" The first layout places {layout.get('units_placed')} of {layout.get('units_total')} homes on the plates as drawn (answer 3); this answer counts all {layout.get('units_total')}."
                if layout and layout.get("units_total") and (layout.get("units_placed") or 0) < layout["units_total"] else "")
    L.append("")
    # the front sheet, shaped as an ask (25 Nov 2026)
    L.extend(front_markdown(front_sheet(ledger, proforma, layout)))
    if short:
        L.append("*The short memo: the full memo (memo.md) adds the massing, the layout, every rule in force and the version stamp's files.*")
        L.append("")

    # ---------------- the three answers
    L.append("## 1. Is it allowed?")
    o, bz = ans["allowed"]["outright"], ans["allowed"]["by_rezoning"]
    # three verdicts, so the Director's discretion is never printed as "outright" (25 Nov 2026)
    rts = ans["allowed"].get("routes")
    if rts:
        L.append(" · ".join(f"**{v['label']}: {v['verdict']}**" + (f" ({v['why']})" if v.get("why") and v["verdict"] not in ("not assessed",) else "") for v in rts.values()))
        L.append("")
    out_lines = [r for r in res if counts_outright(r) and r["status"] != "not_applicable"]
    L.append(f"**Outright, under {district_of(site) or 'the district'}: {o['verdict']}.** " + " ".join(f"{r['finding']} ({r['rule_id']})" for r in out_lines)
             + (f" Not assessed: {o['why']}; the envelope is the option's own figure, not a permitted one." if o.get("why") else ""))
    L.append("")
    from .checks import proposes_rezoning
    if bz.get("verdict") == "approved":
        # a rezoning Council has approved (25 Nov 2026): said as decided; what else the rules read is listed under it
        L.append(f"**By rezoning: approved.** {bz['why'][:1].upper() + bz['why'][1:]}.")
        for r in res:
            if r["layer"] in ("A", "B", "C") and r["status"] in ("fail", "conditional", "uncertain") and not r.get("check", "").startswith("district_outright"):
                L.append(f"- *{STATUS_WORD[r['status']]}* — {r['title']}: {r['finding']}")
        L.append("")
    elif bz.get("verdict") == "needed":
        L.append(f"**By rezoning: needed.** {bz['why'][:1].upper() + bz['why'][1:]}.")
    elif bz.get("verdict") == "not needed":
        L.append(f"**By rezoning: not needed.** {bz['why'][:1].upper() + bz['why'][1:]}.")
        L.append("")
    elif (ans["allowed"].get("rezoning_path") or ans["allowed"].get("approval_route")) and not proposes_rezoning(opt):
        # an approval route that is not a rezoning (a development permit under an official development plan): said as
        # the route, and the open items of layers A to C listed under it without a by-rezoning verdict (23 Nov 2026)
        L.append(f"**Approval route: {ans['allowed'].get('rezoning_path') or ans['allowed'].get('approval_route', '').replace('_', ' ')}.** No rezoning is proposed, so the rules written for rezonings are not read; what else is open in the City's and the Province's rules:")
        for r in res:
            if r["layer"] in ("A", "B", "C") and r["status"] in ("fail", "conditional", "uncertain") and not r.get("check", "").startswith("district_outright"):
                L.append(f"- *{STATUS_WORD[r['status']]}* — {r['title']}: {r['finding']}")
        L.append("")
    elif ans["allowed"].get("rezoning_path") or ans["allowed"].get("approval_route") == "rezoning":
        L.append(f"**By rezoning ({ans['allowed'].get('rezoning_path') or 'path not written'}): {bz['verdict']}.**")
        for r in res:
            if r["layer"] in ("A", "B", "C") and r["status"] in ("fail", "conditional", "uncertain") and not r.get("check", "").startswith("district_outright"):
                L.append(f"- *{STATUS_WORD[r['status']]}* — {r['title']}: {r['finding']}")
        L.append("")
    L.append("## 2. Does it fit the funders?")
    # the criteria in words, and a closed intake beside them (20 Nov 2026: "Yes." over a fund whose call was cancelled);
    # a ledger written before `words` existed falls back to the verdict key
    fd = ans["funded"]
    closed = [i["note"] for i in fd.get("intake") or [] if i.get("open") is False]
    L.append(f"**{fd.get('words') or fd['verdict'].capitalize()}.**" + "".join(f" {c[:1].upper() + c[1:]}." for c in closed) + unplaced)
    for r in res:
        if r["layer"] == "E" and r.get("check") != "program_match" and r["rule_id"] in (opt.get("target_programs") or [r["rule_id"]]):
            L.append(f"- *{STATUS_WORD[r['status']]}* — {r['title']}: {r['finding']}")
    # the programs the rules list without testing them, where they are written for this housing (23 Nov 2026)
    doors = [m for m in fd.get("matches") or [] if not m.get("ended")]
    if doors:
        L.append("")
        L.append("Other programs written for this kind of housing, listed from their own pages and **not tested**:")
        for m in doors:
            cond = f" (if the housing is {' and '.join(m['if'])})" if m.get("if") else ""
            intake = (m.get("intake") or "").rstrip(".")
            L.append(f"- **{m['program'][:1].upper() + m['program'][1:]}**{cond}: {m.get('what') or ''}. A project enters {m.get('enters') or 'in a way its page does not state'}."
                     + (f" {intake[:1].upper() + intake[1:]}." if intake else "")
                     + (f" Its homes are all rent geared to income; this option has {m['differs']['market_units']} at market rent." if m.get("differs") else ""))
    if fd.get("scope"):
        L.append("")
        L.append(f"*{fd['scope']}*")
    L.append("")
    L.append("## 3. What is still unsure, and who resolves it?")
    open_items = list(ans["unsure"]) + lay_items
    if massing_error:
        # a run whose massing could not be drawn says so, with the reason (23 Nov 2026: a memo with no drawings and no word why)
        open_items.append({"title": "No massing or drawings in this memo", "status": "uncertain",
                           "action": f"Architect: the massing could not be drawn from the site as recorded ({massing_error.rstrip('.')}). Correct the site's front street or dimensions and run again."})
    if open_items:
        L.append("| Item | Status | Who / what |")
        L.append("|---|---|---|")
        for u in open_items:
            L.append(f"| {u['title']} | {STATUS_WORD[u['status']]} | {u['action'] or '—'} |")
    else:
        L.append("Nothing outstanding.")
    L.append("")

    # ---------------- the pro-forma, feasibility grade (layer F and layer E)
    if proforma:
        from . import proforma as _pf
        L.extend(_pf.markdown(proforma, short=short))

    # ---------------- massing
    if massing and not short:
        L.append("## Massing derived from the rules")
        for mm in massing["masses"]:
            # a tower's podium and tower plates each times their storeys (25 Nov 2026: "1,750 m² × 18 = 15,000 m²")
            made = (f"podium {mm['plate_area_m2']:,.0f} m² × {mm['podium_storeys']} + tower {mm['tower']['area_m2']:,.0f} m² × {mm['storeys'] - mm['podium_storeys']} storeys"
                    if mm.get("tower") and mm.get("podium_storeys") else f"plate {mm['plate_area_m2']:,.0f} m² × {mm['storeys']} storeys")
            L.append(f"- **{mm['label']}** — {made} = {mm['gfa_m2']:,.0f} m² "
                     f"(FSR {mm['fsr']:.2f}), {mm['height_m']} m high, inside a {massing['envelope']['width_m']} × {massing['envelope']['depth_m']} m setback envelope. "
                     f"Derived from: {', '.join(mm['derived_from'])}.")
        if massing.get("policy_benchmark"):
            b = massing["policy_benchmark"]
            L.append(f"- Staff benchmark under {b['rule_id']}: {b['height_m'][0]} to {b['height_m'][1]} m, about FSR {b['fsr']}.")
        for w in massing.get("warnings", []):
            L.append(f"- Note: {w}")
        L.append("")
        L.append("![Massing plan and section](massing.svg)")
        L.append("")
        L.append("`massing.json` carries the same geometry for the Revit script (`revit/ffm_massing_pyrevit.py`).")
        L.append("")

    # ---------------------------------------------------------------- the architect's first layout, from the option
    if layout and not short:
        from . import layout as _layout
        L.extend(_layout.markdown(layout))

    # ---------------- Revit, when the script has run on this exact stamp
    if revit and not short:
        L.append("## Built in Revit")
        L.append(f"Mode: {revit.get('mode', '—')}. Stages: " + ", ".join(f"{k} {v}" for k, v in (revit.get("stages") or {}).items()) + ".")
        for b in revit.get("built", []):
            kind = b.get("kind")
            if kind == "mass":
                L.append(f"- Mass `{b.get('name')}` (element {b.get('element_id')}): {b.get('storeys')} storeys, {b.get('height_m')} m, plate {b.get('plate_area_m2'):,} m², FSR {b.get('fsr')}.")
            elif kind == "floor plates":
                L.append(f"- Floor plates: {b.get('count')}.")
            elif kind == "model lines":
                L.append(f"- Model lines: lot {b.get('lot')}, setback envelope {b.get('envelope')}.")
            elif kind == "view":
                L.append(f"- View: {b.get('name')} (element {b.get('element_id')}).")
            elif kind == "annotations":
                L.append(f"- Annotations: {b.get('dimensions')} dimensions, {b.get('notes')} text notes, {b.get('section_lines')} benchmark lines.")
            elif kind == "sheet":
                L.append(f"- Sheet {b.get('number')} (element {b.get('element_id')}), title block: {'yes' if b.get('title_block') else 'none in template'}.")
        if revit.get("saved_as"):
            L.append(f"- Saved as `{Path(revit['saved_as']).name}` next to this memo.")
        for e in revit.get("exports", []):
            L.append(f"- Exported `{Path(e).name}`.")
        if revit.get("errors"):
            L.append(f"- {len(revit['errors'])} stage error(s) recorded in `ffm_revit_result.json`; the stages marked ok above still stand.")
        if revit.get("sheet_png"):
            L.append("")
            L.append(f"![Revit sheet]({revit['sheet_png']})")
        notes = revit.get("sheet_notes") or {}
        if notes:
            L.append("")
            L.append("Text placed on the sheet (quotable in the memo):")
            L.append("")
            for key in ("allowed", "funders", "unsure", "massing"):
                for ln in notes.get(key, []):
                    L.append(f"> {ln}")
                L.append(">")
        L.append("")

    # ---------------- change log
    if diff and not short:
        L.append("## What changed since the previous memo")
        L.append(f"Previous stamp `{diff.get('previous_stamp')}` (rules as of {diff.get('previous_as_of')}) → current `{diff.get('current_stamp')}` (as of {diff.get('current_as_of')}). "
                 + ("The rule files themselves changed." if diff.get("rules_changed") else "The rule files are unchanged; differences come from the as-of date or the inputs."))
        if diff["changes"]:
            L.append("")
            L.append("| Rule | Change | From | To | Now reads |")
            L.append("|---|---|---|---|---|")
            for c in diff["changes"]:
                frm = c.get("from") or "—"
                to = c.get("to") or "—"
                if c.get("from_version") and c.get("from_version") != c.get("to_version"):
                    frm += f" (v {c['from_version']})"
                    to += f" (v {c['to_version']})"
                L.append(f"| {c['rule_id']} | {c['change'].replace('_', ' ')} | {frm} | {to} | {c['finding']} |")
        else:
            L.append("")
            L.append("No rule changed status.")
        L.append("")

    # ---------------- the full ledger
    # the rules that apply to this site, as the page and the paper list them; one written for another district or not in
    # force on the date is counted in a line, not printed (23 Nov 2026: 60-odd "Not applicable: written for C-2
    # districts" rows made the memo 95 KB and buried the 20 that applied). ledger.json keeps every one.
    elsewhere = [r for r in res if not takes_ref(r)]
    if not short:
        L.append("## Full ledger")
    if elsewhere and not short:
        L.append("")
        L.append(f"{len(res) - len(elsewhere)} of the {len(res)} rules in force apply to this site and are listed. The other {len(elsewhere)} are written for other districts "
                 "or are not in force on this date; `ledger.json` lists them with their reasons.")
    cur_layer = None
    for r in res:
        if not takes_ref(r) or short:
            continue
        if r["layer"] != cur_layer:
            cur_layer = r["layer"]
            L.append("")
            L.append(f"### Layer {r['layer']}: {r['layer_title']}")
            L.append("")
            L.append("| Rule | Status | Finding | Numbers used | Source |")
            L.append("|---|---|---|---|---|")
        L.append(f"| {r['title']} (`{r['rule_id']}`, v {r.get('version_effective_from') or '—'}) | {STATUS_WORD[r['status']]} | {r['finding']} | {_fmt_vals(r.get('values', {}))} | {_src(r)} |")
    L.append("")

    # ---------------- the words a board will not have (23 Nov 2026: HILs, RGI and deep subsidy stood unexplained in memo.md)
    said = "\n".join(L)
    words = [(k, v) for k, pat, v in GLOSSARY if re.search(pat, said)]
    if words:
        L.append("## Words in this memo")
        for k, v in words:
            L.append(f"- **{k}**: {v}")
        L.append("")

    # ---------------- inputs and sources
    L.append("## Inputs")
    L.append(f"- Site `{site.get('id')}`: {site.get('zoning_district') or 'district not given'}, {_n(site.get('site_area_m2'), ' m²')}, {_n(site.get('frontage_m'))} × {_n(site.get('depth_m'))} m; owner: {site.get('owner') or '—'}.")
    u = opt.get("units") or {}
    units_txt = ", ".join("{0} {1}".format(k.replace("_", " "), "not given" if v is None else v) for k, v in u.items()) or "not given"
    L.append(f"- Option `{opt.get('id')}`: {_n(opt.get('storeys'))} storeys, {_n(opt.get('height_m'))} m, {_n(opt.get('gfa_m2'), ' m²')} GFA; units {units_txt}; tenure {str(opt.get('tenure') or 'not given').replace('_', ' ')}.")
    if site.get("notes"):
        L.append(f"- Site notes: {site['notes']}")
    if opt.get("notes"):
        L.append(f"- Option notes: {opt['notes']}")
    L.append("")
    L.append("## Sources")
    # the sources of the rules that apply here (25 Nov 2026, the second panel: every schedule in the stack was listed)
    seen = set()
    for r in res:
        if not takes_ref(r):
            continue
        s = r.get("source") or {}
        key = (s.get("title"), s.get("url"))
        if key in seen or not any(key):
            continue
        seen.add(key)
        line = f"- {s.get('title') or s.get('url')}"
        if s.get("url"):
            line += f" — {s['url']}"
        if s.get("verify"):
            line += f" *(verify: {s['verify']})*"
        L.append(line)
    for src in (site.get("sources") or []) + (opt.get("sources") or []):
        key = (src.get("title"), src.get("url"))
        if key not in seen:
            seen.add(key)
            L.append(f"- {src.get('title')} — {src.get('url')}")
    L.append("")
    L.append("## Version stamp")
    L.append(f"- Rules hash (SHA-256 over all rule files): `{run['stamp']['rules_hash']}`")
    for f, h in ({} if short else run["stamp"]["rules_files"]).items():
        L.append(f"- `{f}`: `{h[:16]}…`")
    L.append(f"- Stamp (hash of rules hash + rule versions in force on {run['as_of']}): `{run['stamp']['stamp']}`")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- HTML

def _md_inline(s: str) -> str:
    """Tiny inline markdown: **bold**, *italic*, `code`, [text](url). Enough for the memo."""
    import re
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def html_page(md: str, svg_text: str | None = None, svgs: dict[str, str] | None = None) -> str:
    """Render the memo markdown to a self-contained HTML page (headings, paragraphs, lists, tables,
    blockquote, images replaced by the inline SVGs: the massing's, and any sheet in `svgs` keyed by file name).
    No external assets."""
    svgs = dict(svgs or {})
    if svg_text:
        svgs.setdefault("massing.svg", svg_text)
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    in_list = in_table = in_quote = False

    def close():
        nonlocal in_list, in_table, in_quote
        if in_list:
            out.append("</ul>")
            in_list = False
        if in_table:
            out.append("</tbody></table>")
            in_table = False
        if in_quote:
            out.append("</blockquote>")
            in_quote = False

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("#"):
            close()
            level = len(ln) - len(ln.lstrip("#"))
            out.append(f"<h{level}>{_md_inline(ln[level:].strip())}</h{level}>")
        elif ln.startswith("- "):
            if in_table or in_quote:
                close()
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_md_inline(ln[2:])}</li>")
        elif ln.startswith("|"):
            if in_list or in_quote:
                close()
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if not in_table:
                out.append("<table><thead><tr>" + "".join(f"<th>{_md_inline(c)}</th>" for c in cells) + "</tr></thead><tbody>")
                in_table = True
                i += 2  # skip the |---| row
                continue
            tds = []
            for c in cells:
                word = c.strip()
                color = STATUS_COLOR.get(word.lower().replace(" ", "_"))
                tds.append(f'<td><span class="pill" style="background:{color}">{word}</span></td>' if color else f"<td>{_md_inline(c)}</td>")
            out.append("<tr>" + "".join(tds) + "</tr>")
        elif ln.startswith("> "):
            if in_list or in_table:
                close()
            if not in_quote:
                out.append("<blockquote>")
                in_quote = True
            out.append(f"<p>{_md_inline(ln[2:])}</p>")
        elif ln.startswith("!["):
            close()
            import re as _re
            mm = _re.match(r"!\[([^\]]*)\]\(([^)]+)\)", ln)
            alt, src = (mm.group(1), mm.group(2)) if mm else ("", "")
            if src in svgs:
                cap = "Rule-derived massing: plan and section, to scale." if alt.startswith("Massing") else f"{alt}, derived from the option; to scale."
                out.append(f'<figure>{svgs[src]}<figcaption>{html.escape(cap)}</figcaption></figure>')
            else:
                out.append(f'<figure><img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}" style="max-width:100%;border:1px solid #e5e5e5"><figcaption>{html.escape(alt)}</figcaption></figure>')
        elif ln.strip() == "":
            close()
        else:
            if in_list or in_table or in_quote:
                close()
            out.append(f"<p>{_md_inline(ln.rstrip('  '))}</p>")
        i += 1
    close()
    body = "\n".join(out)
    css = """
    :root{--ink:#2c3e50;--muted:#5f6672;--line:#e1e5ea;--bg:#fff;--group:#e9eef4;--field:#f5f6f8;--blue:#2a6fb8}
    body{font-family:"IBM Plex Sans","Helvetica Neue",Helvetica,Arial,sans-serif;font-size:13.5px;color:var(--ink);background:var(--bg);max-width:1100px;margin:32px auto;padding:0 20px;line-height:1.45}
    h1{font-size:22px;font-weight:600;margin:0 0 8px;letter-spacing:-0.01em} h2{font-size:16px;font-weight:600;margin:28px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px} h3{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:18px 0 6px;color:var(--muted)}
    blockquote{border-left:3px solid var(--line);margin:12px 0;padding:4px 14px;color:var(--muted);font-size:12.5px}
    table{border-collapse:collapse;width:100%;font-size:12px;margin:8px 0 16px} th,td{border:1px solid var(--line);padding:6px 8px;vertical-align:top;text-align:left} th{background:var(--group);font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
    code{font-family:"IBM Plex Mono","SF Mono",Menlo,Consolas,monospace;background:var(--field);border:1px solid var(--line);padding:1px 4px;border-radius:3px;font-size:11.5px}
    .pill{color:#fff;border-radius:10px;padding:1px 8px;font-size:11px;font-weight:600;white-space:nowrap}
    figure{margin:12px 0} figure svg{max-width:100%;height:auto;border:1px solid var(--line)} figcaption{font-size:12px;color:var(--muted)}
    li{margin:3px 0} a{color:var(--blue)}
    @media print{body{margin:0;max-width:none} h2{break-after:avoid}}
    """
    return f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>First Read memo</title><style>{css}</style></head><body>{body}</body></html>"


def load_revit_result(out_dir: Path, stamp: str) -> dict | None:
    """The Revit script's result for this exact stamp, if it has run on this folder."""
    p = out_dir / "ffm_revit_result.json"
    if not p.exists():
        return None
    try:
        r = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if r.get("stamp") != stamp:
        return None
    if (out_dir / "ffm_sheet.png").exists():
        r["sheet_png"] = "ffm_sheet.png"
    n = out_dir / "ffm_sheet_notes.json"
    if n.exists():
        try:
            r["sheet_notes"] = json.loads(n.read_text(encoding="utf-8"))
        except Exception:
            pass
    return r


def write(ledger: dict, out_dir: Path, massing: dict | None = None, diff: dict | None = None, svg_text: str | None = None,
          revit: dict | None = None, proforma: dict | None = None, layout: dict | None = None, massing_error: str | None = None) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if revit is None:
        revit = load_revit_result(out_dir, ledger["run"]["stamp"]["stamp"])
    if proforma is None and (out_dir / "proforma.json").exists():
        try:
            proforma = json.loads((out_dir / "proforma.json").read_text(encoding="utf-8"))
        except Exception:
            proforma = None
    if layout is None and (out_dir / "layout.json").exists():
        try:
            layout = json.loads((out_dir / "layout.json").read_text(encoding="utf-8"))
        except Exception:
            layout = None
    # the sheets beside the ledger go inline, so the HTML memo stands alone
    svgs = {}
    for name in ("stacking", "plans", "elevations", "axon", "site-plan"):
        p = out_dir / f"{name}.svg"
        if p.exists():
            svgs[p.name] = p.read_text(encoding="utf-8")
    md = markdown(ledger, massing, diff, revit=revit, proforma=proforma, layout=layout, massing_error=massing_error)
    pm = out_dir / "memo.md"
    ph = out_dir / "memo.html"
    pm.write_text(md, encoding="utf-8")
    # the short memo beside it, for every run: a board reads the ask and the answers (25 Nov 2026)
    (out_dir / "memo-short.md").write_text(markdown(ledger, massing, diff, revit=revit, proforma=proforma, layout=layout,
                                                    massing_error=massing_error, short=True), encoding="utf-8")
    ph.write_text(html_page(md, svg_text, svgs), encoding="utf-8")
    return pm, ph
