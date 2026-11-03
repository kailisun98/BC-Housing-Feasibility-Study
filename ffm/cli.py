"""Command line.

    python -m ffm run --site sites/998-e-19th-ave.json --option options/998-e-19th-ave-as-approved.json --out outputs/run1
    python -m ffm run ... --as-of 2026-10-27 --previous outputs/run1/ledger.json --out outputs/run2
    python -m ffm memo --out outputs/run1   rewrite the memo after the Revit script has run on that folder
    python -m ffm rules [--as-of DATE]      list the rules and the version in force
    python -m ffm stamp [--as-of DATE]      print the version stamp only
    python -m ffm lookup "998 E 19th Ave, Vancouver, BC" [--out sites/x.json]   propose a site from an address
    python -m ffm suggest --site sites/x.json --programs bch.chf.eligibility [--candidate funder-ready] [--out options/x.json]
    python -m ffm proforma --site sites/x.json --option options/x.json [--as-of DATE]   the feasibility pro-forma, printed
    python -m ffm refresh [--write] [--as-of DATE]   fetch the public cost and rate series behind layer F; --write appends versions
    python -m ffm propose rule --from <pdf|txt> --district RT-3 [--url ...] [--out proposals/x.json]   Claude proposes rule clauses (needs FFM_CLAUDE_KEY)
    python -m ffm propose site --site sites/x.json [--from <pdf|png>] [--out proposals/x.json]      Claude proposes site facts
    python -m ffm confirm --proposal proposals/x.json --by "Name" [--only key,key]   a person confirms a proposal into rules/ or sites/
    python -m ffm ui [--port 8765] [--no-browser]   the local web UI (ffm/ui/)
    python -m ffm pages [--out _site]       build the UI as a static site (GitHub Pages; engine runs in Pyodide)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import engine, massing, memo, proforma
from .rules_loader import RULES_DIR, load_rules, stamp


def _date(s: str | None) -> date:
    return date.fromisoformat(s) if s else date.today()


def cmd_run(a: argparse.Namespace) -> int:
    site = engine.load_json(a.site)
    option = engine.load_json(a.option)
    on = _date(a.as_of)
    rules_dir = Path(a.rules) if a.rules else RULES_DIR
    ledger = engine.evaluate(site, option, on, rules_dir=rules_dir)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ledger.json").write_text(json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")

    m = svg_text = None
    if not a.no_massing:
        try:
            m = massing.build(site, option, ledger)
            pj, ps = massing.write(m, out)
            svg_text = ps.read_text(encoding="utf-8")
        except ValueError as e:
            print(f"massing skipped: {e}", file=sys.stderr)

    d = None
    if a.previous:
        d = engine.diff(engine.load_json(a.previous), ledger)
        (out / "diff.json").write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")

    pf = proforma.build(site, option, ledger)
    (out / "proforma.json").write_text(json.dumps(pf, indent=2, ensure_ascii=False), encoding="utf-8")

    pm, ph = memo.write(ledger, out, m, d, svg_text, proforma=pf)

    s = ledger["summary"]
    print(f"as of {ledger['run']['as_of']} · stamp {ledger['run']['stamp']['stamp']}")
    print(f"allowed outright: {s['answers']['allowed']['outright']['verdict']} · by rezoning: {s['answers']['allowed']['by_rezoning']['verdict']} · funders: {s['answers']['funded']['verdict']}"
          + (f" · money: {pf['verdict']['word']}" if pf.get("available") else ""))
    print("counts: " + ", ".join(f"{k} {v}" for k, v in s["counts"].items() if v))
    print(f"wrote {out / 'ledger.json'}, {pm.name}, {ph.name}, proforma.json" + (", massing.json, massing.svg" if m else "") + (", diff.json" if d else ""))
    return 0


def cmd_proforma(a: argparse.Namespace) -> int:
    """The feasibility pro-forma for a site and option, printed line by line with its sources; nothing written."""
    site = engine.load_json(a.site)
    option = engine.load_json(a.option)
    on = _date(a.as_of)
    L = engine.evaluate(site, option, on, rules_dir=Path(a.rules) if a.rules else RULES_DIR)
    pf = proforma.build(site, option, L)
    if a.json:
        print(json.dumps(pf, indent=2, ensure_ascii=False))
        return 0
    if not pf.get("available"):
        print(f"not computed: {pf.get('why')}")
        return 1
    print("\n".join(proforma.markdown(pf)))
    return 0


def cmd_refresh(a: argparse.Namespace) -> int:
    """Fetch the public series behind layer F (Statistics Canada BCPI, Bank of Canada rate) and say what changed;
    --write appends a new dated version to rules/f_assumptions.json for each series that moved."""
    from . import refresh
    rep = refresh.run(write=a.write, rules_dir=Path(a.rules) if a.rules else RULES_DIR, on=_date(a.as_of))
    for item in rep["items"]:
        print(f"{item['rule_id']:22} {item['status']:10} {item['message']}")
    for note in rep["by_hand"]:
        print(f"by hand: {note}")
    if a.write and rep["written"]:
        print(f"wrote {rep['file']}: {', '.join(rep['written'])}")
    return 0


def cmd_memo(a: argparse.Namespace) -> int:
    """Rewrite memo.md / memo.html for an existing run folder, picking up diff.json and the Revit
    result (ffm_revit_result.json, ffm_sheet.png, ffm_sheet_notes.json) if the script has run."""
    out = Path(a.out)
    ledger = engine.load_json(out / "ledger.json")
    m = engine.load_json(out / "massing.json") if (out / "massing.json").exists() else None
    svg_text = (out / "massing.svg").read_text(encoding="utf-8") if (out / "massing.svg").exists() else None
    d = engine.load_json(out / "diff.json") if (out / "diff.json").exists() else None
    pm, ph = memo.write(ledger, out, m, d, svg_text)   # picks up proforma.json beside the ledger
    r = memo.load_revit_result(out, ledger["run"]["stamp"]["stamp"])
    print(f"rewrote {pm.name}, {ph.name}" + (" with the Revit section" if r else " (no Revit result for this stamp yet)"))
    return 0


def cmd_pages(a: argparse.Namespace) -> int:
    """Build the web UI as a static site (GitHub Pages): data files for the runs, the engine for Pyodide."""
    from . import pages
    info = pages.build(Path(a.out), a.pyodide_url) if a.pyodide_url else pages.build(Path(a.out))
    print(f"built {info['files']} files into {info['out']}: {info['sites']} site(s), {info['options']} option(s), {info['runs']} run(s)")
    return 0


def cmd_ui(a: argparse.Namespace) -> int:
    """Serve the web UI on 127.0.0.1 and open it in the default browser."""
    from .ui import server as ui_server  # imported here so the engine commands stay light
    return ui_server.serve(port=a.port, open_browser=not a.no_browser)


def cmd_context(a: argparse.Namespace) -> int:
    """Fetch the OpenStreetMap context around a site (roads, buildings, trees) and store it in the site file."""
    from . import osm
    path = Path(a.site)
    site = engine.load_json(path)
    center = None
    if a.center:
        lat, lon = (float(v) for v in a.center.split(","))
        center = (lat, lon)
    block = osm.fetch_for_site(site, radius_m=float(a.radius), center=center)
    site["osm"] = block
    path.write_text(osm.dumps_site(site), encoding="utf-8")
    c, f = block["counts"], block["frame"]
    print(f"{path}: {c['roads']} roads, {c['buildings']} buildings, {c['trees']} trees within {block['radius_m']:.0f} m of "
          f"{block['center']['lat']}, {block['center']['lon']}; front street {f['front_street']!r} ({'matched by name' if f['front_street_matched_by_name'] else 'nearest road'}), "
          f"x axis bearing {f['x_axis_bearing_deg']}°; {c['buildings_on_site_omitted']} building(s) on the lot omitted. {block['attribution']}.")
    return 0


def cmd_lookup(a: argparse.Namespace) -> int:
    """Propose a site file from an address: Nominatim for the point, the City's open data for the district and
    the parcel. Prints the site JSON, or writes it with --out."""
    from . import lookup
    res = lookup.lookup(a.address)
    text = json.dumps(res["site"], indent=2, ensure_ascii=False) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}: {res['site']['zoning_district'] or 'district not found'}, {res['site']['site_area_m2'] or '?'} m²")
    else:
        print(text, end="")
    return 0


def cmd_suggest(a: argparse.Namespace) -> int:
    """Derive an option from a site and the chosen programs, with the rule behind every figure."""
    from . import suggest
    site = engine.load_json(a.site)
    programs = [p for p in (a.programs or "").split(",") if p]
    res = suggest.suggest(site, programs, _date(a.as_of), a.candidate, rules_dir=Path(a.rules) if a.rules else RULES_DIR)
    if a.out:
        Path(a.out).write_text(json.dumps(res["option"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {a.out}")
    o = res["option"]
    print(f"{res['candidate']}: {o['storeys']} storeys, {o['height_m']} m, {o['gfa_m2']} m² GFA, units {o['units']}, tiers {o['rent_tiers_units']}, trees {o['replacement_trees_proposed']}")
    for u in res["unsure"]:
        print(f"  unsure · {u['key']}: {u['why']} ({u['who']})")
    return 0


def cmd_propose(a: argparse.Namespace) -> int:
    """Claude proposes; nothing enters the rules or a site until `confirm`."""
    from . import propose
    try:
        if a.what == "eval":
            return _propose_eval(a, propose)
        if a.what == "rule":
            if not a.source or not a.district:
                print("propose rule needs --from <document> and --district <code>.", file=sys.stderr)
                return 2
            res = propose.propose_rule(Path(a.source), a.district, url=a.url, model=a.model)
        else:
            if not a.site:
                print("propose site needs --site <site.json>.", file=sys.stderr)
                return 2
            res = propose.propose_site(engine.load_json(a.site), Path(a.source) if a.source else None, model=a.model)
    except propose.NoKey as e:
        print(str(e), file=sys.stderr)
        return 3
    out = Path(a.out) if a.out else propose.PROPOSALS_DIR / f"{res['slug']}.json"
    propose.save(res, out)
    print(f"wrote {out}: {len(res['items'])} proposed item(s) from {res['model']} · confirm with: python -m ffm confirm --proposal \"{out}\" --by \"Your name\"")
    for it in res["items"]:
        print(f"  {it['key']:28} {str(it['value'])[:40]:40} confidence {it['confidence']:.2f}  {it.get('section') or ''}")
    return 0


def _propose_eval(a: argparse.Namespace, propose) -> int:
    """Run every case under evals/propose/ against the model and score it field by field."""
    base = Path(__file__).resolve().parent.parent / "evals" / "propose"
    total = hits = 0
    for case in sorted(p for p in base.iterdir() if p.is_dir() and (p / "expected.json").exists()):
        exp = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        doc = next((p for p in case.iterdir() if p.stem == "document"), None)
        if doc is None and exp.get("document_path"):   # a document saved by hand outside the repository (inbox/)
            doc = base.parent.parent / exp["document_path"]
        if doc is None or not doc.exists():
            print(f"{case.name}: no document" + (f" at {exp.get('document_path')}" if exp.get("document_path") else ""))
            continue
        if exp.get("kind") == "rule":
            res = propose.propose_rule(doc, exp["district"], model=a.model)
        else:
            res = propose.propose_site(engine.load_json(case / "site.json"), doc, model=a.model)
        s = propose.score(res["items"], exp["expected"])
        total += s["of"]
        hits += s["hits"]
        print(f"{case.name}: {s['hits']}/{s['of']} with {res['model']}" + (f" · extra: {', '.join(s['extra'])}" if s["extra"] else ""))
        for r in s["rows"]:
            if not r["ok"]:
                print(f"  miss {r['key']}: expected {r['expected']!r}, got {r['got']!r}")
        propose.save(res, propose.PROPOSALS_DIR / "eval" / f"{case.name}.json")
    print(f"score {hits}/{total}")
    return 0 if hits == total else 1


def cmd_confirm(a: argparse.Namespace) -> int:
    from . import propose
    only = [k for k in (a.only or "").split(",") if k] or None
    rep = propose.confirm(Path(a.proposal), a.by, only=only, rules_dir=Path(a.rules) if a.rules else RULES_DIR)
    print(f"confirmed {len(rep['confirmed'])} item(s) by {a.by} on {rep['on']} into {rep['target']}")
    for k in rep["confirmed"]:
        print(f"  {k}")
    if rep["skipped"]:
        print("skipped: " + ", ".join(rep["skipped"]))
    return 0


def cmd_rules(a: argparse.Namespace) -> int:
    on = _date(a.as_of)
    rules = load_rules(Path(a.rules) if a.rules else RULES_DIR)
    for r in rules:
        v = r.version_on(on)
        print(f"{r.layer} {r.id:40} {r.title[:50]:50} v {v.effective_from if v else '—'}  applies to {','.join(r.applies_to_districts)}")
    return 0


def cmd_stamp(a: argparse.Namespace) -> int:
    on = _date(a.as_of)
    rules_dir = Path(a.rules) if a.rules else RULES_DIR
    print(json.dumps(stamp(load_rules(rules_dir), on, rules_dir), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ffm", description="First Read: a deterministic feasibility screen for BC non-profit housing.")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="evaluate a site + option and write ledger, memo and massing")
    r.add_argument("--site", required=True)
    r.add_argument("--option", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--as-of", dest="as_of", help="rules in force on this date (YYYY-MM-DD); default today")
    r.add_argument("--previous", help="a previous ledger.json to diff against")
    r.add_argument("--rules", help="alternate rules directory")
    r.add_argument("--no-massing", dest="no_massing", action="store_true")
    r.set_defaults(fn=cmd_run)

    mm = sub.add_parser("memo", help="rewrite the memo for an existing run folder (picks up the Revit result)")
    mm.add_argument("--out", required=True)
    mm.set_defaults(fn=cmd_memo)

    c = sub.add_parser("context", help="fetch the OpenStreetMap context around a site into the site file (needs the network once)")
    c.add_argument("--site", required=True)
    c.add_argument("--radius", default=120, help="metres around the address (default 120)")
    c.add_argument("--center", help="lat,lon to use instead of geocoding the address")
    c.set_defaults(fn=cmd_context)

    lk = sub.add_parser("lookup", help="propose a site file from an address (Nominatim + City of Vancouver open data; needs the network)")
    lk.add_argument("address")
    lk.add_argument("--out", help="write the site JSON here instead of printing it")
    lk.set_defaults(fn=cmd_lookup)

    sg = sub.add_parser("suggest", help="derive an option from a site and the chosen programs, every figure citing its rule")
    sg.add_argument("--site", required=True)
    sg.add_argument("--programs", help="comma-separated rule ids, e.g. bch.chf.eligibility,bc.bcbuilds.eligibility")
    sg.add_argument("--candidate", default="funder-ready", choices=["outright", "benchmark", "funder-ready"])
    sg.add_argument("--as-of", dest="as_of")
    sg.add_argument("--rules")
    sg.add_argument("--out", help="write the option JSON here")
    sg.set_defaults(fn=cmd_suggest)

    pf = sub.add_parser("proforma", help="the feasibility pro-forma for a site and option, with its sources; nothing written")
    pf.add_argument("--site", required=True)
    pf.add_argument("--option", required=True)
    pf.add_argument("--as-of", dest="as_of")
    pf.add_argument("--rules")
    pf.add_argument("--json", action="store_true", help="print the pro-forma as JSON")
    pf.set_defaults(fn=cmd_proforma)

    rf = sub.add_parser("refresh", help="fetch the public series behind layer F (StatCan BCPI, Bank of Canada rate); --write appends versions")
    rf.add_argument("--write", action="store_true", help="append a new dated version to rules/f_assumptions.json where a series moved")
    rf.add_argument("--as-of", dest="as_of")
    rf.add_argument("--rules")
    rf.set_defaults(fn=cmd_refresh)

    pp = sub.add_parser("propose", help="Claude proposes rule clauses from a document, or site facts; a person confirms (needs FFM_CLAUDE_KEY)")
    pp.add_argument("what", choices=["rule", "site", "eval"])
    pp.add_argument("--from", dest="source", help="a PDF, image or text file to read (read locally; only the proposal is kept)")
    pp.add_argument("--district", help="rule: the district the schedule is for, e.g. RT-3")
    pp.add_argument("--url", help="rule: the public URL of the document, cited in the rule's source")
    pp.add_argument("--site", help="site: the site JSON to propose fields for")
    pp.add_argument("--out", help="write the proposal JSON here (default proposals/<slug>.json)")
    pp.add_argument("--model", help="model id (default FFM_CLAUDE_MODEL or claude-sonnet-5-5)")
    pp.set_defaults(fn=cmd_propose)

    cf = sub.add_parser("confirm", help="a person confirms a proposal's clauses into rules/ or a site's fields into sites/")
    cf.add_argument("--proposal", required=True)
    cf.add_argument("--by", required=True, help="who confirms, printed in the rule's source")
    cf.add_argument("--only", help="comma-separated keys to confirm; default all")
    cf.add_argument("--rules")
    cf.set_defaults(fn=cmd_confirm)

    l = sub.add_parser("rules", help="list rules and the version in force")
    l.add_argument("--as-of", dest="as_of")
    l.add_argument("--rules")
    l.set_defaults(fn=cmd_rules)

    s = sub.add_parser("stamp", help="print the version stamp")
    s.add_argument("--as-of", dest="as_of")
    s.add_argument("--rules")
    s.set_defaults(fn=cmd_stamp)

    u = sub.add_parser("ui", help="start the local web UI (http://127.0.0.1:8765)")
    u.add_argument("--port", type=int, default=8765)
    u.add_argument("--no-browser", dest="no_browser", action="store_true", help="do not open the browser")
    u.set_defaults(fn=cmd_ui)

    g = sub.add_parser("pages", help="build the web UI as a static site for GitHub Pages")
    g.add_argument("--out", default="_site")
    g.add_argument("--pyodide-url", dest="pyodide_url", help="pyodide.js URL to load the engine with (default: the pinned CDN release)")
    g.set_defaults(fn=cmd_pages)

    a = p.parse_args(argv)
    return a.fn(a)
