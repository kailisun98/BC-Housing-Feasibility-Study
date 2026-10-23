"""Command line.

    python -m ffm run --site sites/998-e-19th-ave.json --option options/998-e-19th-ave-as-approved.json --out outputs/run1
    python -m ffm run ... --as-of 2026-10-27 --previous outputs/run1/ledger.json --out outputs/run2
    python -m ffm memo --out outputs/run1   rewrite the memo after the Revit script has run on that folder
    python -m ffm rules [--as-of DATE]      list the rules and the version in force
    python -m ffm stamp [--as-of DATE]      print the version stamp only
    python -m ffm ui [--port 8765] [--no-browser]   the local web UI (ffm/ui/)
    python -m ffm pages [--out _site]       build the UI as a static site (GitHub Pages; engine runs in Pyodide)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import engine, massing, memo
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

    pm, ph = memo.write(ledger, out, m, d, svg_text)

    s = ledger["summary"]
    print(f"as of {ledger['run']['as_of']} · stamp {ledger['run']['stamp']['stamp']}")
    print(f"allowed outright: {s['answers']['allowed']['outright']['verdict']} · by rezoning: {s['answers']['allowed']['by_rezoning']['verdict']} · funders: {s['answers']['funded']['verdict']}")
    print("counts: " + ", ".join(f"{k} {v}" for k, v in s["counts"].items() if v))
    print(f"wrote {out / 'ledger.json'}, {pm.name}, {ph.name}" + (", massing.json, massing.svg" if m else "") + (", diff.json" if d else ""))
    return 0


def cmd_memo(a: argparse.Namespace) -> int:
    """Rewrite memo.md / memo.html for an existing run folder, picking up diff.json and the Revit
    result (ffm_revit_result.json, ffm_sheet.png, ffm_sheet_notes.json) if the script has run."""
    out = Path(a.out)
    ledger = engine.load_json(out / "ledger.json")
    m = engine.load_json(out / "massing.json") if (out / "massing.json").exists() else None
    svg_text = (out / "massing.svg").read_text(encoding="utf-8") if (out / "massing.svg").exists() else None
    d = engine.load_json(out / "diff.json") if (out / "diff.json").exists() else None
    pm, ph = memo.write(ledger, out, m, d, svg_text)
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
    p = argparse.ArgumentParser(prog="ffm", description="Funding-fit memo: deterministic feasibility screen for BC non-profit housing.")
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
