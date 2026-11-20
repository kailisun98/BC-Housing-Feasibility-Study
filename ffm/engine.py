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
        if version is None:
            results.append({**base, "status": NA, "finding": f"No version of this rule is in force on {on.isoformat()}.", "values": {}, "action": ""})
            continue
        if not rule.applies_to_site(site):
            results.append({**base, "status": NA,
                            "finding": f"Written for {rule.written_for()}; this site is zoned {district or 'unknown'}.",
                            "values": {"district": district}, "action": ""})
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
            action = (f"Architect: save CD-1 ({cd1})'s by-law (cd1-bylaws.vancouver.ca) into inbox/ and have its height, floor area and yards "
                      "entered as rules (or read it with Claude at stop 3 and confirm its clauses).")
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
            action = (f"Architect: save the {district} schedule into inbox/ and have its FSR, height and yards entered as rules "
                      "(or read it with Claude at stop 3 and confirm its clauses).")
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
                           "action": f"Architect: open {written_in} and confirm the FSR, height and yards; or drop its PDF into inbox/ and have the rule confirmed."})
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
                           "action": "Manager: say whether the buildings on the lot stay (stop 1); if they do, the architect draws the footprint that is kept and the massing moves off it."})
    elif keep:
        extra_open.append({"rule_id": "coverage.existing_buildings", "title": "A building kept on the lot", "status": "conditional",
                           "finding": "The existing buildings stay, but the massing is drawn on the whole lot: the floor area and the plate here assume the ground they stand on.",
                           "action": "Architect: draw the kept footprint and reduce the plate (the boundary editor, or a smaller site area); the answers hold for the lot as drawn."})
    if "church" in owner or "parish" in owner or "congregation" in owner:
        extra_open.append({"rule_id": "coverage.heritage", "title": "Heritage register and designation", "status": "uncertain",
                           "finding": "The rules hold no heritage rule, and a church site is where the City's Heritage Register and heritage designations are most likely to apply; a listed building changes what can be demolished and how the rezoning is read.",
                           "action": "Architect: check the Vancouver Heritage Register and any heritage designation or revitalization agreement for this address."})
    allowed = {"outright": outright, "by_rezoning": by_rezoning, "rezoning_path": option.get("rezoning_path")}

    # Question 2: does it fit the funders? Layer E rules the option targets.
    targets = set(option.get("target_programs") or [])
    e = [r for r in results if r["layer"] == "E" and (not targets or r["rule_id"] in targets)]
    funded = _verdict(e)
    funded.update(funders_words(funded, e))

    # Question 3: what is still unsure, and who resolves it?
    # An outright limit the option exceeds is answered by the rezoning path (answer 1 says the rezoning is required), so
    # that fail is not an open item when a path is stated; an outright check that could not be read (a height not
    # entered) still is.
    unsure = extra_open + [
        {"rule_id": r["rule_id"], "title": r["title"], "status": r["status"], "finding": r["finding"], "action": r["action"]}
        for r in results if r["status"] in (UNSURE, COND, FAIL) and not answered_by_rezoning(r, option)
    ]
    return {"counts": counts, "answers": {"allowed": allowed, "funded": funded, "unsure": unsure}}


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
        words = f"Does not meet the criteria of {_and(of((FAIL,)))}"
    elif v == "not yet confirmed":
        words = f"Whether it meets the criteria of {_and(of((UNSURE,)))} is not yet confirmed"
    elif v == "yes, with conditions":
        words = f"Meets the criteria of {_and(of((PASS, COND)))}, with conditions"
    else:
        words = f"Meets the criteria of {_and(of((PASS,)))}"
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
