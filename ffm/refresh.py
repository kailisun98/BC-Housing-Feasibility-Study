"""Refresh layer F from its public, machine-readable sources, and say what must be checked by hand.

    python -m ffm refresh            fetch and report: what each series says now against the version on file
    python -m ffm refresh --write    append a new dated version to rules/f_assumptions.json where a series moved

Two series are fetched: Statistics Canada's building construction price index for Vancouver residential
buildings (table 18-10-0289-01, through the Web Data Service) and the Bank of Canada's conventional five-year
mortgage rate (Valet series V80691335). Everything else in layer F (the hard-cost base from a PDF, CMHC rents
from the data tables, the placeholders) is listed as "by hand" with what to check. A refresh never edits a
version in place: it appends one dated the day the source published, so the stamp changes and a memo run on an
earlier date still reads the figures in force then. Standard library only (urllib)."""

from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from .rules_loader import RULES_DIR

STATCAN_WDS = "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods"
BOC_VALET = "https://www.bankofcanada.ca/valet/observations/{series}/json?recent=1"
USER_AGENT = "First-Read/0.1 (+https://github.com/kailisun98/BC-Housing-Feasibility-Study)"


def _get_json(url: str, body: Any = None, timeout: float = 30) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_bcpi(product_id: int, coordinate: str, latest_n: int = 12) -> dict[str, Any]:
    """The latest N quarters of one BCPI series: {period: value}, the vector id and the series' release date."""
    res = _get_json(STATCAN_WDS, [{"productId": product_id, "coordinate": coordinate, "latestN": latest_n}])
    obj = res[0]["object"]
    if res[0].get("status") != "SUCCESS":
        raise OSError(f"Statistics Canada returned {res[0].get('status')} for {product_id} {coordinate}")
    points = {p["refPer"]: float(p["value"]) for p in obj.get("vectorDataPoint", []) if p.get("value") not in (None, "")}
    rel = max((p.get("releaseTime") or "" for p in obj.get("vectorDataPoint", [])), default="")
    return {"vector": f"v{obj.get('vectorId')}", "observations": dict(sorted(points.items())), "released": rel[:10]}


def fetch_boc_rate(series: str) -> dict[str, Any]:
    """The latest observation of a Bank of Canada Valet series: {date, value}."""
    res = _get_json(BOC_VALET.format(series=series))
    obs = res.get("observations") or []
    if not obs:
        raise OSError(f"Bank of Canada returned no observations for {series}")
    last = obs[-1]
    return {"date": last["d"], "value": float(last[series]["v"]), "label": (res.get("seriesDetail") or {}).get(series, {}).get("label", series)}


def _latest_version(rule: dict) -> dict:
    return sorted(rule["versions"], key=lambda v: v["effective_from"])[-1]


def plan(rules_doc: dict, bcpi: dict | None, boc: dict | None, today: date) -> dict[str, Any]:
    """What a refresh would change, from fetched data (pure: no network, no files), so it can be tested."""
    items: list[dict] = []
    new_versions: dict[str, dict] = {}
    by_id = {r["id"]: r for r in rules_doc["rules"]}

    r = by_id.get("f.escalation_bcpi")
    if r and bcpi:
        cur = _latest_version(r)
        p = cur["params"]
        latest_period = max(bcpi["observations"])
        latest_value = bcpi["observations"][latest_period]
        if latest_period > p.get("latest_period", "") or latest_value != p.get("latest_value"):
            np = dict(p)
            np.update({"latest_period": latest_period, "latest_value": latest_value, "released": bcpi["released"] or today.isoformat(),
                       "observations": {**p.get("observations", {}), **bcpi["observations"]}, "vector": bcpi["vector"]})
            base = np.get("observations", {})
            np["summary"] = (f"Building construction price index, Vancouver, residential buildings, division composite ({p.get('base', '2023=100')}): "
                             f"{latest_value} in {_quarter(latest_period)}, from {base.get('2024-07-01', '?')} in the third quarter of 2024, the hard-cost base period; "
                             f"escalation {round(latest_value / base['2024-07-01'], 3) if base.get('2024-07-01') else '?'}")
            eff = bcpi["released"] or today.isoformat()
            if eff <= cur["effective_from"]:
                eff = today.isoformat()
            src = dict(cur["source"])
            src["title"] = src["title"].split(", released")[0] + f", released {eff}"
            new_versions["f.escalation_bcpi"] = {"effective_from": eff, "params": np, "source": src}
            items.append({"rule_id": "f.escalation_bcpi", "status": "moved", "message": f"{p.get('latest_value')} ({p.get('latest_period')}) → {latest_value} ({latest_period}); new version effective {eff}"})
        else:
            items.append({"rule_id": "f.escalation_bcpi", "status": "current", "message": f"{latest_value} at {latest_period}, as on file"})
    elif r:
        items.append({"rule_id": "f.escalation_bcpi", "status": "unreached", "message": "Statistics Canada not reached"})

    r = by_id.get("f.mortgage")
    if r and boc:
        cur = _latest_version(r)
        p = cur["params"]
        if boc["value"] != p.get("rate_pct") or boc["date"] > p.get("rate_date", ""):
            np = dict(p)
            np.update({"rate_pct": boc["value"], "rate_date": boc["date"]})
            np["summary"] = (f"Conventional 5-year mortgage rate {boc['value']}% (chartered banks, Bank of Canada series {p.get('rate_series')}, {boc['date']}) as the ceiling; "
                             f"CMHC MLI Select terms for the debt test: a {p.get('debt_coverage_ratio')} debt coverage ratio and a {p.get('amortization_years')}-year amortization (50 years is available at 100 affordability points)")
            eff = boc["date"] if boc["date"] > cur["effective_from"] else today.isoformat()
            new_versions["f.mortgage"] = {"effective_from": eff, "params": np, "source": dict(cur["source"])}
            items.append({"rule_id": "f.mortgage", "status": "moved", "message": f"{p.get('rate_pct')}% ({p.get('rate_date')}) → {boc['value']}% ({boc['date']}); new version effective {eff}"})
        else:
            items.append({"rule_id": "f.mortgage", "status": "current", "message": f"{boc['value']}% at {boc['date']}, as on file"})
    elif r:
        items.append({"rule_id": "f.mortgage", "status": "unreached", "message": "Bank of Canada not reached"})

    by_hand = []
    for rid, what in (("f.hard_cost_base", "the BC Housing / Ministry Class D catalogue estimate (a PDF): check for a newer edition and type the figure with its date"),
                      ("f.rents", "the CMHC Rental Market Survey data tables (Vancouver CMA, by bedroom type): type the bachelor, one-bedroom and three-bedroom averages and the vacancy rate from the latest survey"),
                      ("f.soft_costs", "a declared placeholder: replace with the proponent's development budget"),
                      ("f.operating", "a declared placeholder: replace with the operator's budget"),
                      ("f.land", "the BC Assessment value or the agreed price goes in the option's finance block, not here")):
        if rid in by_id:
            v = _latest_version(by_id[rid])
            by_hand.append(f"{rid} (v {v['effective_from']}): {what}")
    return {"items": items, "new_versions": new_versions, "by_hand": by_hand}


def _quarter(period: str) -> str:
    y, m = period[:4], int(period[5:7])
    q = {1: "first", 4: "second", 7: "third", 10: "fourth"}.get(m, "?")
    return f"the {q} quarter of {y}"


def apply(rules_doc: dict, new_versions: dict[str, dict]) -> list[str]:
    """Append the new versions to the rules document (in memory); returns the rule ids written."""
    written = []
    for r in rules_doc["rules"]:
        nv = new_versions.get(r["id"])
        if nv:
            r["versions"].append(nv)
            written.append(r["id"])
    return written


def run(write: bool = False, rules_dir: Path = RULES_DIR, on: date | None = None) -> dict[str, Any]:
    today = on or date.today()
    path = rules_dir / "f_assumptions.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in doc["rules"]}
    bcpi = boc = None
    esc = by_id.get("f.escalation_bcpi")
    if esc:
        p = _latest_version(esc)["params"]
        try:
            bcpi = fetch_bcpi(int(p["product_id"]), p["coordinate"])
        except Exception as e:  # the report says it was not reached; nothing is written for it
            bcpi = None
            print(f"Statistics Canada: {e}")
    mtg = by_id.get("f.mortgage")
    if mtg:
        p = _latest_version(mtg)["params"]
        try:
            boc = fetch_boc_rate(p["rate_series"])
        except Exception as e:
            boc = None
            print(f"Bank of Canada: {e}")
    rep = plan(doc, bcpi, boc, today)
    rep["file"] = str(path)
    rep["written"] = []
    if write and rep["new_versions"]:
        rep["written"] = apply(doc, rep["new_versions"])
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return rep
