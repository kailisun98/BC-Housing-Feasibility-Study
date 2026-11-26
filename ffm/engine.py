"""Run every applicable rule against a site + option on a given date and produce the ledger.

The ledger is the machine-readable record the memo is written from:

    {
      "run": {"as_of", "site_id", "option_id", "engine_version", "stamp": {...}},
      "results": [ {rule_id, layer, layer_title, title, jurisdiction, status, finding, values,
                    action, source, version_effective_from}, ... ],
      "summary": {"counts": {...}, "answers": {"allowed": ..., "funded": ..., "unsure": [...]}},
      "inputs": {"site": {...}, "option": {...}}
    }

It is deterministic: no randomness, no model, no clock other than the as-of date passed in.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from . import __version__
from .checks import CHECKS, COND, FAIL, INFO, NA, PASS, UNSURE
from .rules_loader import RULES_DIR, Rule, cd1_number, district_of, load_rules, stamp

LAYER_ORDER = ["A", "B", "C", "D", "E", "F"]
STATUS_ORDER = [FAIL, COND, UNSURE, PASS, INFO, NA]


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate(site: dict, option: dict, on: date, rules: list[Rule] | None = None,
             rules_dir: Path = RULES_DIR) -> dict[str, Any]:
    rules = rules if rules is not None else load_rules(rules_dir)
    district = district_of(site)     # "CD-1 (324)" for a CD-1 site whose number is known
    results: list[dict[str, Any]] = []

    for rule in rules:
        version = rule.version_on(on)
        base = {
            "rule_id": rule.id,
            "layer": rule.layer,
            "layer_title": rule.layer_title,
            "title": rule.title,
            "jurisdiction": rule.jurisdiction,
            "check": rule.check,
            "source": version.source if version else {},
            "version_effective_from": version.effective_from.isoformat() if version else None,
            "version_effective_to": version.effective_to.isoformat() if (version and version.effective_to) else None,
        }
        # a rule not in force on the date, or written for another district, is listed but takes no reference (A1…):
        # `elsewhere` says which (takes_ref)
        if version is None:
            results.append({**base, "status": NA, "finding": f"No version of this rule is in force on {on.isoformat()}.", "values": {}, "action": "",
                            "elsewhere": "date"})
            continue
        if not rule.applies_to_site(site):
            results.append({**base, "status": NA,
                            "finding": f"Written for {rule.written_for()}; this site is zoned {district or 'unknown'}.",
                            "values": {"district": district}, "action": "", "elsewhere": "district"})
            continue
        fn = CHECKS.get(rule.check)
        if fn is None:
            results.append({**base, "status": UNSURE, "finding": f"No check named '{rule.check}' is implemented.", "values": {}, "action": "Developer: implement the check."})
            continue
        params = version.params
        if rule.check == "district_setbacks" and (version.source or {}).get("section"):
            # the yards' finding names its clauses last, read off the source's section (checks.yard_clause)
            params = {**params, "_section": version.source["section"]}
        out = fn(site, option, params)
        results.append({**base, **out})

    results.sort(key=lambda r: (LAYER_ORDER.index(r["layer"]) if r["layer"] in LAYER_ORDER else 99, r["rule_id"]))

    ledger = {
        "run": {
            "as_of": on.isoformat(),
            "site_id": site.get("id"),
            "option_id": option.get("id"),
            "engine_version": __version__,
            "stamp": stamp(rules, on, rules_dir),
        },
        "results": results,
        "summary": summarise(results, option, site),
        "inputs": {"site": site, "option": option},
    }
    return ledger


def takes_ref(r: dict) -> bool:
    """Whether a ledger result takes a reference (A1 … F7): every rule that applies to the site does, whatever its
    status; one written for another district, or with no version in force on the date, does not (20 Nov 2026, Kai:
    with 48 other districts' schedules in the stack, 998 E 19th Ave's rezoning policy had become A20). A ledger written
    before the `elsewhere` mark is read by its finding. The page's memo/memo.js takesRef is the twin."""
    if r.get("elsewhere"):
        return False
    finding = r.get("finding") or ""
    return not (r.get("status") == NA and (finding.startswith("Written for ") or finding.startswith("No version of this rule is in force")))


def memo_refs(results: list[dict]) -> dict[str, str]:
    """The memo's references: the layer's letter and the rule's place among the results that take one, in the ledger's
    order (memo/memo.js memoRefs numbers them the same way on screen and on paper). Pure."""
    out: dict[str, str] = {}
    n: dict[str, int] = {}
    for r in results:
        if not takes_ref(r):
            continue
        n[r.get("layer")] = n.get(r.get("layer"), 0) + 1
        out[r.get("rule_id")] = f"{r.get('layer')}{n[r.get('layer')]}"
    return out


def operator_items(option: dict, kind: str, staffed: dict) -> list[dict]:
    """The open items an operator resolves, addressed "Operator: …" so the page's lanes give them a lane of their own.
    Only where an operator is in play: a building with a staffed part, an operator named, or operating figures entered."""
    ops = option.get("operations") or {}
    entered = [k for k, v in ops.items() if k not in ("signed", "subsidy_confirmed", "subsidy_source") and v not in (None, "")]
    who = str(option.get("operator") or "").strip()
    if not (staffed or kind != "independent" or who or entered):
        return []
    to = f"Operator{' (' + who + ')' if who else ''}: "
    out: list[dict] = []
    signed = ops.get("signed") if isinstance(ops.get("signed"), dict) else None
    if not (signed and signed.get("by")):
        out.append({"rule_id": "operator.figures", "title": "Operating figures not yet signed by the operator", "status": "uncertain",
                    "finding": ("The rents, running costs and staffing here are " + ("the figures entered on the option" if entered else "the screen's placeholders")
                                + ", and no operator has signed them as theirs; a funder and a board read the operating page as the operator's."),
                    "action": to + "review the operating page, enter the building's own rents, running costs, staffing, reserve and vacancy, and sign them (the Operator layout)."})
    sub = ops.get("operating_subsidy_cad_year")
    if isinstance(sub, (int, float)) and sub > 0 and ops.get("subsidy_confirmed") is not True:
        out.append({"rule_id": "operator.subsidy", "title": "The operating subsidy is not confirmed", "status": "uncertain",
                    "finding": f"An operating subsidy of ${sub:,.0f} a year is entered" + (f" from {ops['subsidy_source']}" if ops.get("subsidy_source") else "") + " but not confirmed; until it is, no loan is sized on it and the money cannot read likely.",
                    "action": to + "confirm the subsidy with its funder, in writing, with its term."})
    term = ops.get("subsidy_term_years")
    if isinstance(sub, (int, float)) and sub > 0 and ops.get("subsidy_confirmed") is True and not (isinstance(term, (int, float)) and term >= 40):
        out.append({"rule_id": "operator.term", "title": "The operating agreement's term and renewal", "status": "uncertain",
                    "finding": "The subsidy is confirmed " + (f"for {term:g} years" if isinstance(term, (int, float)) else "for a term not entered") + ", shorter than the loan: the building runs only while it is renewed.",
                    "action": to + "state the agreement's term, and what funds the running costs if it is not renewed."})
    staffing = ops.get("support_staffing_cad_year")
    if (staffed or kind != "independent") and not (isinstance(staffing, (int, float)) and staffing >= 0):
        out.append({"rule_id": "operator.staffing", "title": "The staffing model and its cost", "status": "uncertain",
                    "finding": "Supportive, transitional and shelter housing runs on staffing this screen never assumes; none is entered, so the subsidy it needs is not known.",
                    "action": to + "give the staffing model (who is on site, by shift) and its yearly cost."})
    return out


def counts_outright(r: dict) -> bool:
    """A result the outright answer reads: the district's FSR and height, and its yards where they leave no envelope."""
    check = r.get("check") or ""
    return check.startswith("district_outright") or (check == "district_setbacks" and bool((r.get("values") or {}).get("no_envelope")))


def answered_by_rezoning(r: dict, option: dict) -> bool:
    """An outright limit the option exceeds while it states a rezoning path: a fail on the outright test whose finding
    says the rezoning is required. Answer 1 carries it; it is not an open item and not a blocker of the by-rezoning
    answer."""
    return bool(option.get("rezoning_path")) and r.get("status") == FAIL and (r.get("check") or "").startswith("district_outright")


def summarise(results: list[dict], option: dict, site: dict | None = None) -> dict[str, Any]:
    counts = {s: 0 for s in STATUS_ORDER}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    site = site or {}
    district = district_of(site) or "this district"
    cd1 = cd1_number(site.get("zoning_district"), site.get("cd1_bylaw_number"))
    is_cd1 = cd1 is not None or district.upper().startswith("CD-1")
    # what the district's limits are written in: a district schedule, or a CD-1's own by-law (17 Nov 2026)
    written_in = f"CD-1 ({cd1})'s by-law" if cd1 else ("the site's CD-1 by-law" if is_cd1 else f"the {district} schedule")
    municipality = (site.get("municipality") or "").strip()
    outside = bool(municipality) and "vancouver" not in municipality.lower()

    # Question 1: is it allowed? Layers A to C decide; D is flags only.
    # Outright = the district schedule alone. By rezoning = everything else in A to C, which is
    # what a rezoning under a City policy is tested against.
    # The district's yards count here only when they leave no envelope on the lot as fronted (17 Nov 2026, Kai: 609
    # Heatley Ave read "yes" at FSR 0.60 with no plate): then the answer is "not yet confirmed", and the open item names
    # the other front, the lane and the variance.
    outright_rules = [r for r in results if r["layer"] == "A" and counts_outright(r)]
    policy_rules = [r for r in results if r["layer"] in ("A", "B", "C") and r not in outright_rules]
    # An option over the district's outright maximum fails the outright test, rezoning path or not (20 Nov 2026, Kai:
    # "Mention rezoning is required but fail on outright test"); the check says the rezoning is required. Before, it read
    # uncertain and a special case here turned the verdict to "no", which also turned a missing height into "no".
    outright = _verdict(outright_rules)
    # No schedule in the stack for the district is not a pass: nothing was tested (15 Nov 2026, after two architects
    # read "Allowed outright" on a DD, an R1-1 and a Burnaby site). The verdict says so, and answer 3 carries it.
    tested = [r for r in outright_rules if r["status"] != "not_applicable"]
    extra_open: list[dict] = []
    if outside:
        why = f"the rules are written for the City of Vancouver and the Province; this site is in {municipality}"
        outright = {"verdict": "not assessed", "fail": [], "conditional": [], "uncertain": [], "why": why}
        by_rezoning = {"verdict": "not assessed", "fail": [], "conditional": [], "uncertain": [], "why": why}
        extra_open.append({"rule_id": "coverage.municipality", "title": f"A site outside the City of Vancouver ({municipality})", "status": "uncertain",
                           "finding": f"The rule stack reads the City of Vancouver's by-laws and policies and the Province's; {municipality}'s zoning is not in it, so nothing below tests this site's zoning.",
                           "action": f"Architect: read {municipality}'s zoning by-law for the district and enter its outright FSR, height and yards; the provincial and funder rules still apply."})
    elif not tested:
        # said plainly which is missing (17 Nov 2026): the district's schedule, this CD-1's by-law, or the CD-1 number itself
        envelope_words = "so the envelope (storeys, height, floor area, yards) is the option's own figure, not a permitted one."
        if cd1:
            why = f"CD-1 ({cd1})'s by-law is not in the rules"
            title = f"CD-1 ({cd1}) is not in the rules"
            finding = (f"The site is zoned CD-1 ({cd1}), a district of its own whose limits are in its by-law and whatever its rezoning set; "
                       f"the rule stack holds no rules from that by-law, {envelope_words}")
            action = (f"Architect: read CD-1 ({cd1})'s by-law (cd1-bylaws.vancouver.ca) for its height, floor area and yards, and enter them for this option; "
                      "to have them tested, the by-law is added to the rules (in the tool: on the site card, give a key and the by-law's PDF and have the tool read it, then confirm its clauses).")
        elif is_cd1:
            why = "the site's CD-1 number is not recorded, so no CD-1 by-law in the rules can be matched to it"
            title = "A CD-1 site with no CD-1 number"
            finding = (f"The site is zoned CD-1 but its CD-1 number is not recorded, so no CD-1 by-law in the rules can be matched to it, {envelope_words}")
            action = ("Manager or architect: find the address again (the lookup records the CD-1 number from the City's zoning data) or enter "
                      "the site's cd1_bylaw_number; the rules from that by-law then apply where the stack holds them.")
        else:
            why = f"the rules have no {district} schedule"
            title = f"No {district} schedule in the rules"
            finding = f"The rule stack has no {district} district schedule, {envelope_words}"
            action = (f"Architect: read the {district} schedule for its FSR, height and yards, and whether housing is a permitted use, and enter them for this option; "
                      "to have them tested, the schedule is added to the rules (in the tool: the architect's Site schedule, read the schedule with Claude, then confirm its clauses).")
        # a district the City classes as industrial: whether homes are a permitted use at all comes before any envelope
        # (23 Nov 2026: an M-1 lot read "not assessed" beside a six-storey suggestion, which reads as "probably fine")
        cls = str(((site.get("lookup") or {}).get("zoning_record") or {}).get("zoning_classification") or "")
        if "industrial" in cls.lower():
            why += f"; the City classes {district} as {cls.lower()}, where housing may not be a permitted use"
            finding += f" The City's zoning data classes {district} as {cls.lower()}: whether housing is a permitted use there is the first question, before any building is sized."
            action = (f"Manager: ask a City planner whether housing is permitted in {district}, and by what route (a rezoning is likely), before any offer on the land. " + action)
        outright = {"verdict": "not assessed", "fail": [], "conditional": [], "uncertain": [], "why": why}
        by_rezoning = _verdict(policy_rules)
        extra_open.append({"rule_id": "coverage.district_schedule", "title": title, "status": "uncertain", "finding": finding, "action": action})
    else:
        by_rezoning = _verdict(policy_rules)
    # schedule figures typed from recollection, not read from the schedule PDF (16 Nov 2026): a rule version whose
    # source says verified false and that was tested on this site is one open item for the run, not one per rule
    unverified = [r["rule_id"] for r in results
                  if r["status"] != NA and r["layer"] == "A" and r.get("check", "").startswith("district_")
                  and (r.get("source") or {}).get("verified") is False]
    if unverified and not outside:
        why_unverified = sorted({(r.get("source") or {}).get("unverified_because") or f"entered from recollection of {written_in}" for r in results
                                 if r["rule_id"] in unverified})
        extra_open.append({"rule_id": "coverage.schedule_unverified", "title": f"District schedule figures entered unverified ({district})", "status": "uncertain",
                           "finding": f"The figures in {', '.join(unverified)} were {'; '.join(why_unverified)}, and not read from {written_in} itself; "
                                      "until they are confirmed, a pass against them is not a permission.",
                           "action": f"Architect: open {written_in} and confirm the FSR, height and yards; or have the rule confirmed against its PDF."})
    # the yards: where no district yard rule tested them, the option's setbacks are its own figures, and a reader of the
    # site plan should know that nothing checked them (15 Nov 2026, from an architect's test)
    sb = option.get("setbacks_m") or {}
    yards_tested = [r for r in results if r.get("check") == "district_setbacks" and r["status"] != "not_applicable"]
    if not outside and not yards_tested and any(v is not None for v in sb.values()):
        extra_open.append({"rule_id": "coverage.yards", "title": f"Yards not checked: no {district} yard rule in the rules", "status": "uncertain",
                           "finding": f"The setbacks on the site plan (front {sb.get('front')}, rear {sb.get('rear')}, side {sb.get('side')} m) are the option's own figures; no rule in the stack tested them against {district}'s minimum yards.",
                           "action": f"Architect: read the yard clauses in {written_in} and set the setbacks to them, or confirm the figures drawn are a relaxation to ask for."})
    # what stands on the lot, and heritage: the massing draws a clear lot; a church site or a kept building is a question
    # with a person (15 Nov 2026, from an architect's test of a West End church site)
    owner = f"{site.get('owner_type') or ''} {site.get('owner') or ''}".lower()
    keep = site.get("keep_existing_buildings")
    if keep is None:
        extra_open.append({"rule_id": "coverage.existing_buildings", "title": "What stays on the lot", "status": "uncertain",
                           "finding": "The massing stands on a clear lot; whether the existing buildings (or part of them) stay is not stated.",
                           "action": "Manager: say whether the buildings on the lot stay; if they do, the architect draws the footprint that is kept and the massing moves off it."})
    elif keep:
        extra_open.append({"rule_id": "coverage.existing_buildings", "title": "A building kept on the lot", "status": "conditional",
                           "finding": "The existing buildings stay, but the massing is drawn on the whole lot: the floor area and the plate here assume the ground they stand on.",
                           "action": "Architect: draw the kept footprint and reduce the plate (the boundary editor, or a smaller site area); the answers hold for the lot as drawn."})
    if "church" in owner or "parish" in owner or "congregation" in owner:
        extra_open.append({"rule_id": "coverage.heritage", "title": "Heritage register and designation", "status": "uncertain",
                           "finding": "The rules hold no heritage rule, and a church site is where the City's Heritage Register and heritage designations are most likely to apply; a listed building changes what can be demolished and how the rezoning is read.",
                           "action": "Architect: check the Vancouver Heritage Register and any heritage designation or revitalization agreement for this address."})
    # An option allowed outright that proposes no rezoning is not read against the rules written for rezonings (23 Nov
    # 2026: an outright C-2A scheme listed the Community Vision map and the family-unit minimum as open items, and the
    # command line printed "by rezoning: no"). The by-rezoning answer says it is not needed.
    from .checks import proposes_rezoning, housing_kind, HOUSING_WORDS, approval_route, ROUTE_WORDS
    rezoning_only = lambda r: r.get("check") in ("family_unit_share", "rezoning_policy_social_housing")
    route = approval_route(option)
    no_rezoning_needed = not outside and tested and outright["verdict"] in ("yes", "yes, with conditions") and not proposes_rezoning(option)
    if no_rezoning_needed:
        by_rezoning = {"verdict": "not needed", "fail": [], "conditional": [], "uncertain": [],
                       "why": "the option is allowed outright and proposes no rezoning"}
    elif route in ("development_permit", "outright") and not outside and outright["verdict"] == "no":
        # the option says a permit, but it exceeds what the schedule allows outright: a permit cannot approve that
        # (24 Nov 2026: "rezoning is required (none)" stood beside "By rezoning: not needed")
        no_rezoning_needed = True
        by_rezoning = {"verdict": "needed", "fail": [], "conditional": [], "uncertain": [],
                       "why": f"the option is to go by {ROUTE_WORDS[route]}, but it exceeds what the schedule allows outright, which a permit cannot approve: "
                              "it needs a rezoning or a smaller building"}
    elif route in ("development_permit", "outright") and not outside:
        # a person said the option goes by permit (a site already rezoned to its CD-1, a building under an official
        # development plan): there is no rezoning to answer for, whatever the rules could test of the district
        no_rezoning_needed = True
        by_rezoning = {"verdict": "not needed", "fail": [], "conditional": [], "uncertain": [],
                       "why": f"the option is approved by {ROUTE_WORDS[route]}, not by a rezoning"}
    allowed = {"outright": outright, "by_rezoning": by_rezoning, "rezoning_path": option.get("rezoning_path"), "approval_route": route}
    allowed["routes"] = routes(allowed, outright_rules)

    # Question 2: does it fit the funders? Layer E rules the option targets.
    targets = set(option.get("target_programs") or [])
    e = [r for r in results if r["layer"] == "E" and (not targets or r["rule_id"] in targets)]
    funded = _verdict(e)
    funded.update(funders_words(funded, e))
    # Supportive, transitional and shelter housing: the programs in the stack are not written for it, so the answer is
    # "not assessed" with the reason and one open item for the manager, never a pass by default (23 Nov 2026).
    kind = housing_kind(option)
    # The programs the rules list without testing them (check program_match): the ones written for this option's kind of
    # housing are named in answer 2 with whether each is taking proposals, whatever the option targets. A match is a
    # door to knock on, never a verdict; "if" is a match that waits on one answer (Indigenous-led? leaving violence?).
    listed = [r for r in results if r["layer"] == "E" and r.get("check") == "program_match"]
    matches = []
    for r in listed:
        v = r.get("values") or {}
        if v.get("match") in (True, "if"):
            note = (v.get("intake") or {}).get("note") or ""
            matches.append({"rule_id": r["rule_id"], "program": program_name(r), "if": v.get("asks") or [], "open": (v.get("intake") or {}).get("open"),
                            "intake": note[4:] if note.startswith("its ") else note, "enters": v.get("how_a_project_enters"), "differs": v.get("differs"),
                            "ended": bool(v.get("ended")), "what": v.get("what"), "funds": v.get("funds")})
    funded["matches"] = matches
    # a program that has ended (Rapid Response to Homelessness: all its homes are built) is listed in the ledger, not named as a door
    sure = [m["program"] for m in matches if not m["if"] and not m["ended"]]
    maybe = [m["program"] for m in matches if m["if"] and not m["ended"]]
    tested_e = [r for r in e if r["status"] in (PASS, COND, UNSURE, FAIL)]
    if kind != "independent" and not tested_e:
        what = HOUSING_WORDS[kind]
        named = sure or maybe
        funded.update({"verdict": "not assessed",
                       "words": (f"Not assessed: the rules list {len(named)} program{'s' if len(named) != 1 else ''} for {what} ({_and(named)}) and test none of their criteria" if named
                                 else f"Not assessed: the rules hold no funding program for {what}"),
                       "why": f"the option is {what}; the Community Housing Fund and BC Builds, whose criteria the rules test, are written for independent rental"})
        closed = [m["program"] for m in matches if m["open"] is False and not m["ended"]]
        extra_open.append({"rule_id": "coverage.funders", "title": (f"Programs for {what}: listed, not tested" if named else f"No funding program for {what} in the rules"), "status": "uncertain",
                           "finding": (f"The option is {what}. The rules list {_and(named)} as written for it, each from its program page, and test none of their criteria"
                                       + (f"; {_and(closed)} {'has' if len(closed) == 1 else 'have'} no intake open" if closed else "") + "." if named
                                       else f"The option is {what}; the programs whose criteria the rules test are written for independent rental."),
                           "action": (f"Manager: ask BC Housing's development staff which of these is taking proposals for {what} and how a project enters it, and settle who funds its operation (staffing and support) before the capital."
                                      if named else f"Manager: ask BC Housing which program is open for {what}, and settle who funds its operation before the capital.")})
    # Parts of the building that run on staffing beside independent homes (24 Nov 2026: Glen Drive's 25 supportive homes
    # and 80-bed shelter): the funders answer tests the independent homes' programs only, and says so.
    from .checks import housing_parts
    parts = housing_parts(option)
    staffed = {k: c for k, c in parts.items() if k != "independent"}
    said = ""
    if kind == "independent" and staffed:
        said = _and([f"{c} {'shelter beds' if k == 'shelter' else HOUSING_WORDS[k] + ' homes'}" for k, c in staffed.items()])
        extra_open.append({"rule_id": "coverage.funders_parts", "title": "Parts of the building the funders answer does not test", "status": "uncertain",
                           "finding": f"The building has {said} beside its independent homes. The funders answer tests the programs written for independent rental; "
                                      f"the programs for the rest are listed in answer 2 and not tested, and those parts run on staffing and an operating agreement of their own.",
                           "action": f"Manager: settle who funds and operates the {said} (BC Housing's development staff for the programs, the operator for the staffing), "
                                     "and enter their staffing and subsidy in the option's operating figures."})
    # Who runs the building (23 Nov 2026: a funder-side reader asks it first, and no memo said): an open item where the
    # housing runs on its operator (supportive, transitional, a shelter) and none is named; and, where the operator is
    # not the proponent, the agreement between them until the land tenure is chosen.
    operator, proponent = str(option.get("operator") or "").strip(), str(option.get("proponent") or "").strip()
    if (kind != "independent" or staffed) and not operator:
        extra_open.append({"rule_id": "coverage.operator", "title": "Who operates the homes", "status": "uncertain",
                           "finding": f"The option {'is ' + HOUSING_WORDS[kind] if kind != 'independent' else 'has ' + said} and names no operator; the operator's experience with the people housed, its staffing and its budget are what a funder reads first.",
                           "action": "Manager: name the operator, and get its operating budget (rents, staffing, the subsidy it needs) into the option's operating figures."})
    elif operator and proponent and operator.lower() != proponent.lower() and not str(option.get("land_tenure") or "").strip():
        extra_open.append({"rule_id": "coverage.operator_agreement", "title": "The agreement between the owner and the operator", "status": "uncertain",
                           "finding": f"The proponent is {proponent} and the homes are operated by {operator}; how the operator holds the homes (a lease, an air-space parcel, an operating agreement) is not stated.",
                           "action": "Manager, with both boards: settle who owns the homes at completion and the instrument between owner and operator, then choose how the land is held; a funder takes its security against it."})
    # The operator's lane (24 Nov 2026, the second panel's operator: "open items never name the operator"). What only the
    # operator settles: the operating figures signed as theirs, an operating subsidy confirmed and its term, and the
    # staffing a supportive, transitional or shelter part runs on. Read from the option alone, so the memo, the page and
    # the paper carry the same items.
    extra_open += operator_items(option, kind, staffed)
    # what the answer covers, said with it: which programs' criteria were tested, and which are only listed
    tested_names = [program_name(r) for r in e if r.get("check") != "program_match" and r["status"] != INFO]
    funded["scope"] = ((f"This screen tests the criteria of {_and(tested_names)}." if tested_names else "This screen tests no program's criteria for this option.")
                       + (f" Also written for this housing, listed and not tested: {_and(sure)}." if sure else "")
                       + (f" Would be, depending on an answer not given: {_and(maybe)}." if maybe else "")
                       + " A program not in the rules may fit as well.")

    # Question 3: what is still unsure, and who resolves it?
    # An outright limit the option exceeds is answered by the rezoning path (answer 1 says the rezoning is required), so
    # that fail is not an open item when a path is stated; an outright check that could not be read (a height not
    # entered) still is.
    unsure = extra_open + [
        {"rule_id": r["rule_id"], "title": r["title"], "status": r["status"], "finding": r["finding"], "action": r["action"]}
        for r in results if r["status"] in (UNSURE, COND, FAIL) and not answered_by_rezoning(r, option)
        and not (no_rezoning_needed and rezoning_only(r))
        # a program the option does not target is not an open item of the option (23 Nov 2026: BC Builds listed as a
        # fail on an option that targeted the Community Housing Fund alone)
        and not (r["layer"] == "E" and targets and r["rule_id"] not in targets)
    ]
    # who to ask, by organisation and role (23 Nov 2026: every item named "Manager" or "Architect" and nobody outside
    # the project). The role is the kind of person who settles the item; no name or phone number is invented.
    for u in unsure:
        who = contact_for(u["rule_id"], next((r.get("check") for r in results if r["rule_id"] == u["rule_id"]), None))
        if who:
            u["contact"] = who
            u["action"] = (u["action"].rstrip() + (" " if u["action"] else "") + f"Ask: {who}.").strip()
    return {"counts": counts, "answers": {"allowed": allowed, "funded": funded, "unsure": unsure}}


CONTACTS = {      # by coverage item or check: the organisation and the role that settles it
    "coverage.district_schedule": "the City of Vancouver's Development and Building Services Centre, an enquiry officer or the district's planner",
    "coverage.schedule_unverified": "the City of Vancouver's Development and Building Services Centre, for the consolidated by-law",
    "coverage.yards": "the City of Vancouver's Development and Building Services Centre, a project facilitator",
    "coverage.municipality": "the municipality's planning department",
    "coverage.heritage": "the City of Vancouver's heritage planners (the Heritage Register and designations)",
    "coverage.funders": "BC Housing, a development manager in Development and Asset Strategies",
    "coverage.operator": "the operating society's executive director and board",
    "coverage.operator_agreement": "the two societies' boards and their lawyers; then BC Housing's development manager for the security it takes",
    "coverage.existing_buildings": "the land owner, then the architect",
    "district_setbacks": "the City of Vancouver's Development and Building Services Centre, a project facilitator",
    "district_outright_fsr": "the City of Vancouver's planning staff for the district (a pre-application enquiry)",
    "district_outright_height": "the City of Vancouver's planning staff for the district (a pre-application enquiry)",
    "district_outright_use": "the City of Vancouver's Development and Building Services Centre, an enquiry officer (which use the building is)",
    "rezoning_policy_social_housing": "the City of Vancouver's rezoning centre, a rezoning planner (a pre-application enquiry)",
    "family_unit_share": "the City of Vancouver's rezoning centre, the rezoning planner on the file",
    "toa_status": "the City of Vancouver's planning staff, or the Province's transit-oriented areas map",
    "tree_replacement": "a certified arborist, then the City staff who review trees with the development permit",
    "social_housing_definition": "the City of Vancouver's housing policy staff, who draft the Housing Agreement",
    "chf_fit": "BC Housing, a development manager in Development and Asset Strategies",
    "bc_builds_fit": "BC Builds, through the address on each Property Opportunity Notice",
    "ssmuh_minimum_units": "the City of Vancouver's Development and Building Services Centre",
    "below_market_rental_policy": "the City of Vancouver's rezoning centre, a rezoning planner",
}


def contact_for(rule_id: str, check: str | None) -> str | None:
    """The organisation and role to ask about an open item, from its coverage id or its rule's check; None where the
    item is the project's own to settle. Pure."""
    return CONTACTS.get(rule_id) or CONTACTS.get(check or "")


def program_name(r: dict) -> str:
    """A funding rule's program as a sentence names it: "the Community Housing Fund", "BC Builds", "the CMHC Affordable
    Housing Fund" (the rule title before its colon, less "BC Housing" and a parenthesis)."""
    name = str(r.get("title") or r.get("rule_id") or "").split(":")[0]
    name = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()
    name = re.sub(r"^BC Housing\s+", "", name)
    return f"the {name}" if name.lower().endswith(("fund", "program", "programme", "initiative")) else name


def _possessive(name: str) -> str:
    return name + ("'" if name.endswith("s") else "'s")


def _and(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def funders_words(funded: dict, e: list[dict]) -> dict[str, Any]:
    """Answer 2 in words, and whether each program it targets is taking proposals (20 Nov 2026: the funder-ready
    what-if read "fits the funders: yes" while the Community Housing Fund's 2025 call had been cancelled).

    `words`: the verdict as criteria met or not ("Meets the criteria of the Community Housing Fund and BC Builds"), no
    full stop; the key `verdict` (yes / yes, with conditions / not yet confirmed / no) is unchanged.
    `intake`: one entry per targeted program whose rule records its intake, [{rule_id, program, open (true, false or
    null), note ("the Community Housing Fund's 2025 call was cancelled in February 2026, so no intake is open now"),
    more (what the record adds, or null), status (the record as written)}]. A closed intake is said beside the
    verdict; it does not change it."""
    from .checks import program_intake
    tested = [r for r in e if r["status"] in (PASS, COND, UNSURE, FAIL)]
    names = {r["rule_id"]: program_name(r) for r in e}
    of = lambda st: [names[r["rule_id"]] for r in tested if r["status"] in st]
    v = funded["verdict"]
    if not tested:
        words = "No program the option targets has criteria the rules test" if e else "The option targets no program in the rules"
    elif v == "no":
        words = f"Does not pass this screen's eligibility checks for {_and(of((FAIL,)))}"
    elif v == "not yet confirmed":
        words = f"Whether it passes this screen's eligibility checks for {_and(of((UNSURE,)))} is not yet confirmed"
    elif v == "yes, with conditions":
        words = f"Passes this screen's eligibility checks for {_and(of((PASS, COND)))}, with conditions"
    else:
        words = f"Passes this screen's eligibility checks for {_and(of((PASS,)))}"
    # two programs are two separate tests: said so, so "A and B" is not read as one stack of money (23 Nov 2026)
    if len(tested) > 1 and v != "not yet confirmed":
        words += ", each read on its own"
    intake = []
    for r in e:
        vals = r.get("values") or {}
        x = vals.get("intake")
        rec = x if isinstance(x, dict) else program_intake(x if isinstance(x, str) else vals.get("status"))
        if not rec:
            continue
        name = names[r["rule_id"]]
        note = rec["note"]
        if note.startswith("its "):
            note = f"{_possessive(name)} {note[4:]}"
        elif note.startswith("intake"):
            note = f"{_possessive(name)} {note}"
        else:
            note = f"{name}: {note}"
        intake.append({"rule_id": r["rule_id"], "program": name, "open": rec["open"], "note": note, "more": rec.get("more"), "status": rec["status"]})
    return {"words": words, "intake": intake}


def by_discretion(r: dict) -> bool:
    """An outright limit the option exceeds within what the Director of Planning may allow: conditional, with the
    discretionary figure in its values (checks.district_outright_fsr / _height)."""
    v = r.get("values") or {}
    return r.get("status") == COND and ("max_fsr_discretionary" in v or "max_height_m_variance" in v or v.get("conditional_use") is True)


ROUTE_LABELS = {"outright": "Outright", "discretion": "By the Director's discretion", "rezoning": "By rezoning"}


def routes(allowed: dict, outright_rules: list[dict]) -> dict[str, dict]:
    """Answer 1 as three verdicts (25 Nov 2026, the second panel: "Outright" was printed over the Director's
    discretion): outright, the district's limits as written; by the Director's discretion, the increases the schedule
    lets the Director of Planning allow, never assumed; by rezoning, as `by_rezoning`. Each {label, verdict, why, rules}.
    The keys `outright` and `by_rezoning` are unchanged; this reads them. Pure."""
    o, bz = allowed["outright"], allowed["by_rezoning"]
    tested = [r for r in outright_rules if r.get("status") != NA]
    disc = [r for r in tested if by_discretion(r)]
    others = [r for r in tested if r not in disc]
    rest = _verdict(others)["verdict"]
    if o["verdict"] == "not assessed":
        out = {"verdict": "not assessed", "why": o.get("why")}
        dsc = {"verdict": "not assessed", "why": o.get("why")}
    elif disc:
        uses_only = all((r.get("values") or {}).get("conditional_use") for r in disc)
        limits = [r for r in disc if not (r.get("values") or {}).get("conditional_use")]
        out = {"verdict": "no", "why": ("the building is a conditional approval use in this district" if uses_only else
                                        "over the schedule's outright limits" + (", and a conditional approval use" if len(limits) < len(disc) else ""))}
        if rest == "no":
            dsc = {"verdict": "no", "why": "another limit is exceeded beyond what the Director may allow"}
        elif rest == "not yet confirmed":
            dsc = {"verdict": "not yet confirmed", "why": "another limit is not yet confirmed"}
        else:
            dsc = {"verdict": "possible", "why": "within what the Director of Planning may allow; a discretionary approval, never assumed"}
    else:
        out = {"verdict": o["verdict"], "why": o.get("why")}
        if o["verdict"] in ("yes", "yes, with conditions"):
            dsc = {"verdict": "not needed", "why": "within the outright limits"}
        elif o["verdict"] == "no":
            over = any("max_fsr_discretionary" in (r.get("values") or {}) or "max_height_m_variance" in (r.get("values") or {}) for r in others if r.get("status") == FAIL)
            dsc = ({"verdict": "no", "why": "over what the Director may allow too"} if over
                   else {"verdict": "none in the schedule", "why": "the schedule gives the Director no increase for this"})
        else:
            dsc = {"verdict": o["verdict"], "why": "the outright limits are not yet confirmed"}
    rz = {"verdict": bz["verdict"], "why": bz.get("why")}
    out["rules"], dsc["rules"] = [r["rule_id"] for r in others if r.get("status") in (FAIL, UNSURE, COND)], [r["rule_id"] for r in disc]
    rz["rules"] = list(bz.get("fail") or []) + list(bz.get("conditional") or []) + list(bz.get("uncertain") or [])
    return {k: {"label": ROUTE_LABELS[k], **v} for k, v in (("outright", out), ("discretion", dsc), ("rezoning", rz))}


def _verdict(rs: list[dict]) -> dict[str, Any]:
    fails = [r["rule_id"] for r in rs if r["status"] == FAIL]
    conds = [r["rule_id"] for r in rs if r["status"] == COND]
    unsure = [r["rule_id"] for r in rs if r["status"] == UNSURE]
    if fails:
        word = "no"
    elif unsure:
        word = "not yet confirmed"
    elif conds:
        word = "yes, with conditions"
    else:
        word = "yes"
    return {"verdict": word, "fail": fails, "conditional": conds, "uncertain": unsure}


def diff(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """What changed between two ledgers: new, dropped or changed-status rules, and stamp change."""
    prev = {r["rule_id"]: r for r in previous.get("results", [])}
    cur = {r["rule_id"]: r for r in current.get("results", [])}
    changes: list[dict[str, Any]] = []
    for rid in sorted(set(prev) | set(cur)):
        a, b = prev.get(rid), cur.get(rid)
        if a is None:
            changes.append({"rule_id": rid, "change": "added", "from": None, "to": b["status"], "finding": b["finding"]})
        elif b is None:
            changes.append({"rule_id": rid, "change": "removed", "from": a["status"], "to": None, "finding": a["finding"]})
        elif a["status"] != b["status"] or a.get("version_effective_from") != b.get("version_effective_from"):
            changes.append({"rule_id": rid, "change": "changed", "from": a["status"], "to": b["status"],
                            "from_version": a.get("version_effective_from"), "to_version": b.get("version_effective_from"),
                            "finding": b["finding"]})
        elif a["finding"] != b["finding"]:
            changes.append({"rule_id": rid, "change": "finding_changed", "from": a["status"], "to": b["status"], "finding": b["finding"]})
    ps, cs = previous.get("run", {}).get("stamp", {}), current.get("run", {}).get("stamp", {})
    return {
        "previous_stamp": ps.get("stamp"), "current_stamp": cs.get("stamp"),
        "previous_as_of": previous.get("run", {}).get("as_of"), "current_as_of": current.get("run", {}).get("as_of"),
        "rules_changed": ps.get("rules_hash") != cs.get("rules_hash"),
        "changes": changes,
    }
