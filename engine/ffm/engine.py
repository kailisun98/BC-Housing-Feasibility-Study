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
from datetime import date
from pathlib import Path
from typing import Any

from . import __version__
from .checks import CHECKS, COND, FAIL, INFO, NA, PASS, UNSURE
from .rules_loader import RULES_DIR, Rule, load_rules, stamp

LAYER_ORDER = ["A", "B", "C", "D", "E"]
STATUS_ORDER = [FAIL, COND, UNSURE, PASS, INFO, NA]


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate(site: dict, option: dict, on: date, rules: list[Rule] | None = None,
             rules_dir: Path = RULES_DIR) -> dict[str, Any]:
    rules = rules if rules is not None else load_rules(rules_dir)
    district = site.get("zoning_district", "")
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
        if not rule.applies_to(district):
            results.append({**base, "status": NA,
                            "finding": f"Written for {', '.join(rule.applies_to_districts)} districts; this site is zoned {district or 'unknown'}.",
                            "values": {"district": district}, "action": ""})
            continue
        fn = CHECKS.get(rule.check)
        if fn is None:
            results.append({**base, "status": UNSURE, "finding": f"No check named '{rule.check}' is implemented.", "values": {}, "action": "Developer: implement the check."})
            continue
        out = fn(site, option, version.params)
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
        "summary": summarise(results, option),
        "inputs": {"site": site, "option": option},
    }
    return ledger


def summarise(results: list[dict], option: dict) -> dict[str, Any]:
    counts = {s: 0 for s in STATUS_ORDER}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    # Question 1: is it allowed? Layers A to C decide; D is flags only.
    # Outright = the district schedule alone. By rezoning = everything else in A to C, which is
    # what a rezoning under a City policy is tested against.
    outright_rules = [r for r in results if r["layer"] == "A" and r.get("check", "").startswith("district_outright")]
    policy_rules = [r for r in results if r["layer"] in ("A", "B", "C") and r not in outright_rules]
    outright = _verdict(outright_rules)
    if outright["uncertain"] and option.get("rezoning_path"):
        # 'uncertain' from an outright check means 'exceeds, needs rezoning': say no outright.
        outright["verdict"] = "no"
    allowed = {"outright": outright, "by_rezoning": _verdict(policy_rules), "rezoning_path": option.get("rezoning_path")}

    # Question 2: does it fit the funders? Layer E rules the option targets.
    targets = set(option.get("target_programs") or [])
    e = [r for r in results if r["layer"] == "E" and (not targets or r["rule_id"] in targets)]
    funded = _verdict(e)

    # Question 3: what is still unsure, and who resolves it?
    # Outright-schedule exceedances are already answered by the rezoning path, so they do not
    # reappear as open items when a path is stated.
    unsure = [
        {"rule_id": r["rule_id"], "title": r["title"], "status": r["status"], "finding": r["finding"], "action": r["action"]}
        for r in results if r["status"] in (UNSURE, COND, FAIL)
        and not (option.get("rezoning_path") and r.get("check", "").startswith("district_outright"))
    ]
    return {"counts": counts, "answers": {"allowed": allowed, "funded": funded, "unsure": unsure}}


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
