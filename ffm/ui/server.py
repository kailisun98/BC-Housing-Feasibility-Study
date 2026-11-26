"""The web UI's server: standard-library HTTP, JSON endpoints, three static files.

Started with `python -m ffm ui [--port 8765] [--no-browser]`. The page never calculates a rule:
this module loads inputs, calls the engine exactly as the command line does, writes the same run
folder (ledger, memo, massing, diff) and hands the results back as JSON.

    GET  /                                  the site's home page (home.html beside this file; how.html, who.html,
                                            case.html and brand.html are its other pages, on site.css and site.js)
    GET  /app.html                          the tool (index.html, app.css and main.js beside this file)
    GET  /<module>.js, /<dir>/<module>.js   the tool's ES modules: main.js imports the rest, kept beside it and
                                            under core/, memo/, figures/ and editors/ (MODULE_DIRS)
    GET  /brand/<file>.svg                  the brand's mark, wordmark and lockups; brand.css holds the tokens
    GET  /data/runs/<site>/<folder>/<file>  a run file at the path the GitHub Pages build gives it, so the
                                            home page's links work the same here and on the web
    GET  /api/rules?as_of=YYYY-MM-DD        [{id, layer, layer_title, title, version_effective_from}]
    GET  /api/sites                         [{id, address, zoning_district, file}]
    GET  /api/sites/<id>                    site JSON
    POST /api/sites                         save a new site JSON (body: site); refuses to overwrite
    GET  /api/options?site=<id>             that site's options only: [{id, name, file, site, for_site}]
    GET  /api/options/<id>                  option JSON
    POST /api/options                       save a new option JSON (body: option); refuses to overwrite
    POST /api/run                           body {site, option, as_of, previous_run?}; site and option are
                                            ids or whole JSON objects -> {run_id, ledger, massing, svg, diff?}
    GET  /api/runs?site=<id>                past runs: as_of, stamp, verdicts, Revit result present?
    GET  /api/runs/<site>/<folder>          a past run as /api/run returns it (ledger, massing, svg, diff, revit)
    GET  /api/diff?from=<run_id>&to=<run_id>  engine.diff between two existing runs' ledgers
    GET  /api/runs/<site>/<folder>/<file>   memo.html | memo.md | ledger.json | massing.json | massing.svg
                                            | diff.json | proforma.json | layout.json | stacking.svg | plans.svg
                                            | elevations.svg | axon.svg | site-plan.svg | ffm_revit_result.json | ffm_sheet_notes.json
                                            | ffm_sheet.png | ffm_sheet.pdf   (?download=1 to attach)
    POST /api/runs/<site>/<folder>/memo     rewrite memo.md / memo.html for that run (picks up a Revit result)
    GET  /api/lookup?q=<address>            a proposed site file from Nominatim and the City's open data (network)
    POST /api/read-site                     body {site, as_of?}: the site alone against layers A to C, nothing written
    POST /api/suggest                       body {site, programs, as_of?, candidate?, mix_shares?, fixed?}: a rule-derived
                                            option carried on from the manager's fixed figures, every
                                            figure with its rule (ffm/suggest.py)
    POST /api/layout                        body {site, option, as_of?}: the block editor's check; the option's
                                            layout.zones are measured and the rules read back; nothing written
    GET  /api/capabilities                  {claude: bool, model, accepts_key, writes_rules}: whether FFM_CLAUDE_KEY is
                                            set on this machine; a person's own key may come with each request instead
    POST /api/propose/site                  body {site, api_key?, document?}: Claude proposes the site's fields with
                                            evidence and a confidence (ffm/propose.py); logged in proposals/; 503 without a key
    POST /api/propose/rule                  body {district, document: {name, data_b64}, url?, api_key?}: Claude reads a
                                            district schedule the page sent and proposes its clauses; logged, not stored
    POST /api/confirm                       body {file, by, only?}: a named person confirms a logged rule proposal into
                                            rules/a_zoning_district.json
    GET  /api/issues?site=<id>              the issue notes on the site's runs, newest first
    POST /api/runs/<site>/<folder>/issue    body {by, to, note}: hand the run from one reader to another
    POST /api/pdf                           body {html}: the page's paper memo, printed to PDF by a headless Edge
                                            or Chrome found on this machine (FFM_BROWSER names another); 501 when
                                            there is none, and the page falls back to its print dialog

Runs are written to outputs/<site-id>/<timestamp>/, so they are also usable from the command line.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
import webbrowser
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .. import engine, layout, massing, memo, proforma, suggest
from ..rules_loader import RULES_DIR, district_of, load_rules

ROOT = Path(__file__).resolve().parent.parent.parent
SITES_DIR = ROOT / "sites"
OPTIONS_DIR = ROOT / "options"
OUTPUTS_DIR = ROOT / "outputs"
STATIC_DIR = Path(__file__).resolve().parent

SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")
# the static files beside this module: the tool (index.html as /app.html, its ES modules beside it and in
# MODULE_DIRS), the site's pages, their styles and scripts, and the brand's SVGs under brand/. Anything else in
# the folder is not served.
MODULE_DIRS = ("core", "memo", "figures", "editors")
STATIC_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
                ".svg": "image/svg+xml", ".jpg": "image/jpeg", ".png": "image/png"}
STATIC_PATH = re.compile(r"^(?:(?:brand|%s)/)?[A-Za-z0-9][A-Za-z0-9_-]*\.(?:html|js|css|svg|jpg|png)$" % "|".join(MODULE_DIRS))
# text worth compressing (the modules are about 430 KB together, a ledger up to 250 KB; gzip takes them to about a fifth)
GZIP_TYPES = ("text/", "application/json", "image/svg+xml")
_GZIP_CACHE: dict[str, bytes] = {}   # a static file's compressed bytes, by its ETag
SITE_PAGES = ("home.html", "how.html", "who.html", "case.html", "brand.html")
# copied by the static build as they are; the tool's modules are found from main.js by ffm/pages.py
SITE_FILES = ("app.css", "brand.css", "site.css", "site.js")
RUN_FILES = {
    "memo.html": "text/html; charset=utf-8", "memo.md": "text/markdown; charset=utf-8",
    "ledger.json": "application/json; charset=utf-8", "massing.json": "application/json; charset=utf-8",
    "massing.svg": "image/svg+xml", "diff.json": "application/json; charset=utf-8", "proforma.json": "application/json; charset=utf-8",
    "layout.json": "application/json; charset=utf-8", "stacking.svg": "image/svg+xml", "plans.svg": "image/svg+xml",
    "elevations.svg": "image/svg+xml", "axon.svg": "image/svg+xml", "site-plan.svg": "image/svg+xml",
    "ffm_revit_result.json": "application/json; charset=utf-8", "ffm_sheet_notes.json": "application/json; charset=utf-8",
    "ffm_sheet.png": "image/png", "ffm_sheet.pdf": "application/pdf",
}


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _slug_ok(s: Any) -> bool:
    return isinstance(s, str) and bool(SLUG.match(s)) and ".." not in s


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- inputs

def list_sites() -> list[dict]:
    out = []
    for p in sorted(SITES_DIR.glob("*.json")):
        try:
            d = _read(p)
        except Exception:
            continue
        out.append({"id": d.get("id") or p.stem, "address": d.get("address", ""), "zoning_district": district_of(d),
                    "municipality": d.get("municipality", ""), "file": p.name})
    return out


def _find_input(folder: Path, kind: str, ident: str) -> Path:
    if not _slug_ok(ident):
        raise ApiError(400, f"Bad {kind} id.")
    direct = folder / f"{ident}.json"
    if direct.exists():
        return direct
    for p in folder.glob("*.json"):
        try:
            if _read(p).get("id") == ident:
                return p
        except Exception:
            continue
    raise ApiError(404, f"No {kind} called '{ident}' in {folder.name}/.")


def load_site(ident: str) -> dict:
    return _read(_find_input(SITES_DIR, "site", ident))


def load_option(ident: str) -> dict:
    return _read(_find_input(OPTIONS_DIR, "option", ident))


def option_site(option: dict, oid: str, site_ids: list[str]) -> str | None:
    """The site an option belongs to: the one its file names (`site`), else the site whose id begins its own id. The
    longest such site id wins, so a site called "998-e-19th" could never claim the options of "998-e-19th-ave". An
    option that matches no site belongs to none. Pure."""
    if option.get("site"):
        return option["site"]
    hits = [s for s in site_ids if oid == s or oid.startswith(s + "-")]
    return max(hits, key=len) if hits else None


def list_options(site_id: str | None) -> list[dict]:
    """The options of one site (17 Nov 2026: every other site's options were listed too, as "(other site)…", so
    choosing 375 Glen Drive offered 998 E 19th Ave's), or every option with its site when no site is asked for (the
    static build writes them all, and the page filters by `site` in the browser)."""
    site_ids = [s["id"] for s in list_sites()]
    out = []
    for p in sorted(OPTIONS_DIR.glob("*.json")):
        try:
            d = _read(p)
        except Exception:
            continue
        oid = d.get("id") or p.stem
        owner = option_site(d, oid, site_ids)
        if site_id and owner != site_id:
            continue
        out.append({"id": oid, "name": d.get("name", oid), "file": p.name, "site": owner, "for_site": bool(site_id)})
    out.sort(key=lambda o: o["id"])
    return out


def save_new(folder: Path, body: Any, kind: str) -> dict:
    if not isinstance(body, dict):
        raise ApiError(400, f"The body must be the {kind} JSON object.")
    ident = body.get("id")
    if not _slug_ok(ident):
        raise ApiError(400, f"The {kind} needs an 'id' made of letters, digits, dots, hyphens or underscores.")
    path = folder / f"{ident}.json"
    if path.exists():
        raise ApiError(409, f"{folder.name}/{path.name} already exists; choose another id. The shipped files are never overwritten.")
    folder.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"id": ident, "file": path.name, "path": str(path)}


def list_rules(as_of: str | None) -> list[dict]:
    on = date.fromisoformat(as_of) if as_of else date.today()
    out = []
    for r in load_rules(RULES_DIR):
        v = r.version_on(on)
        # the version's parameters and source travel too (without the long BCPI series), so the page can show a
        # program's terms or an assumption's figure and cite it before any run
        params = {k: x for k, x in (v.params if v else {}).items() if k != "observations"}
        out.append({"id": r.id, "layer": r.layer, "layer_title": r.layer_title, "title": r.title, "jurisdiction": r.jurisdiction,
                    "applies_to_districts": r.applies_to_districts, "applies_to_cd1": r.applies_to_cd1, "check": r.check,
                    "version_effective_from": v.effective_from.isoformat() if v else None,
                    "params": params, "source": (v.source if v else {})})
    return out


# ---------------------------------------------------------------- runs

def _run_folder(site_id: str, folder: str) -> Path:
    if not (_slug_ok(site_id) and _slug_ok(folder)):
        raise ApiError(400, "Bad run id.")
    p = OUTPUTS_DIR / site_id / folder
    if not (p / "ledger.json").exists():
        raise ApiError(404, f"No run at outputs/{site_id}/{folder}.")
    return p


def _split_run_id(run_id: Any) -> tuple[str, str]:
    if not isinstance(run_id, str) or run_id.count("/") != 1:
        raise ApiError(400, "A run id looks like <site-id>/<folder>.")
    site_id, folder = run_id.split("/")
    return site_id, folder


def revit_summary(folder: Path, stamp: str) -> dict | None:
    """Whether the Revit script has run on this folder for this stamp, and what it left."""
    r = memo.load_revit_result(folder, stamp)
    if not r:
        return None
    built = r.get("built") or []
    counts = {
        "masses": sum(1 for b in built if b.get("kind") == "mass"),
        "floor_plates": sum(int(b.get("count") or 0) for b in built if b.get("kind") == "floor plates"),
        "model_lines": sum(int(b.get("lot") or 0) + int(b.get("envelope") or 0) for b in built if b.get("kind") == "model lines"),
        "views": sum(1 for b in built if b.get("kind") == "view"),
        "sheets": sum(1 for b in built if b.get("kind") == "sheet"),
        "dimensions": sum(int(b.get("dimensions") or 0) for b in built if b.get("kind") == "annotations"),
        "notes": sum(int(b.get("notes") or 0) for b in built if b.get("kind") == "annotations"),
    }
    sheet = next((b for b in built if b.get("kind") == "sheet"), None)
    return {"ok": bool(r.get("ok")), "mode": r.get("mode"), "stages": r.get("stages") or {}, "counts": counts,
            "sheet_number": sheet.get("number") if sheet else None,
            "exports": [Path(e).name for e in r.get("exports", [])],
            "sheet_png": (folder / "ffm_sheet.png").exists(), "sheet_pdf": (folder / "ffm_sheet.pdf").exists(),
            "saved_as": r.get("saved_as"), "errors": len(r.get("errors") or [])}


def list_runs(site_id: str | None) -> list[dict]:
    if not site_id:
        return []
    if not _slug_ok(site_id):
        raise ApiError(400, "Bad site id.")
    base = OUTPUTS_DIR / site_id
    if not base.exists():
        return []
    runs = []
    for p in base.iterdir():
        lp = p / "ledger.json"
        if not (p.is_dir() and lp.exists()):
            continue
        try:
            L = _read(lp)
            ans = L["summary"]["answers"]
            run = L["run"]
        except Exception:
            continue
        stamp = run["stamp"]["stamp"]
        # when the run was first issued: a run made in the tool takes its revision number then (runs.js noteRevisions)
        issued_at = None
        if (p / "issues.json").exists():
            try:
                issued_at = min((i.get("issued_at") for i in _read(p / "issues.json") if i.get("issued_at")), default=None)
            except Exception:
                issued_at = None
        runs.append({
            "run_id": f"{site_id}/{p.name}", "folder": p.name, "folder_abs": str(p),
            "as_of": run["as_of"], "stamp": stamp, "option_id": run.get("option_id"),
            "option_name": (L.get("inputs", {}).get("option") or {}).get("name"),
            "written": datetime.fromtimestamp(lp.stat().st_mtime).isoformat(timespec="seconds"),
            "verdicts": {"outright": ans["allowed"]["outright"]["verdict"], "by_rezoning": ans["allowed"]["by_rezoning"]["verdict"],
                         "funded": ans["funded"]["verdict"]},
            "has_diff": (p / "diff.json").exists(), "has_massing": (p / "massing.json").exists(),
            "revit": revit_summary(p, stamp), "issued_at": issued_at, "made_by": _made_by(p),
        })
    runs.sort(key=lambda r: r["written"], reverse=True)
    return runs


def run_payload(out: Path, site_id: str, ledger: dict, m: dict | None, svg: str | None, d: dict | None,
                massing_note: str | None = None, pf: dict | None = None) -> dict:
    stamp = ledger["run"]["stamp"]["stamp"]
    if pf is None and (out / "proforma.json").exists():
        try:
            pf = _read(out / "proforma.json")
        except Exception:
            pf = None
    lay = _read(out / "layout.json") if (out / "layout.json").exists() else None
    sheets = {name: (out / f"{name}.svg").read_text(encoding="utf-8") for name in layout.SHEETS if (out / f"{name}.svg").exists()} if lay else None
    issues = []
    if (out / "issues.json").exists():
        try:
            issues = _read(out / "issues.json")
        except Exception:
            issues = []
    return {"run_id": f"{site_id}/{out.name}", "folder": out.name, "folder_abs": str(out),
            "as_of": ledger["run"]["as_of"], "stamp": stamp, "ledger": ledger, "massing": m, "svg": svg, "diff": d, "proforma": pf,
            "layout": lay, "sheets": sheets, "issues": issues, "made_by": _made_by(out),
            "massing_note": massing_note, "revit": revit_summary(out, stamp),
            "files": {"massing_json": str(out / "massing.json") if m else None, "ledger_json": str(out / "ledger.json"),
                      "script": str(ROOT / "revit" / "ffm_massing_pyrevit.py")}}


def do_run(body: Any) -> dict:
    if not isinstance(body, dict):
        raise ApiError(400, "Send a JSON object: {site, option, as_of, previous_run?}.")
    site, option = body.get("site"), body.get("option")
    if isinstance(site, str):
        site = load_site(site)
    if isinstance(option, str):
        option = load_option(option)
    if not isinstance(site, dict) or not isinstance(option, dict):
        raise ApiError(400, "site and option must each be an id or the whole JSON object.")
    as_of = body.get("as_of")
    try:
        on = date.fromisoformat(as_of) if as_of else date.today()
    except ValueError:
        raise ApiError(400, "as_of must be a date written YYYY-MM-DD.")
    site_id = site.get("id") or "site"
    if not _slug_ok(site_id):
        raise ApiError(400, "The site id must be made of letters, digits, dots, hyphens or underscores.")

    ledger = engine.evaluate(site, option, on)

    stamp_folder = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    out = OUTPUTS_DIR / site_id / stamp_folder
    n = 1
    while out.exists():
        out = OUTPUTS_DIR / site_id / f"{stamp_folder}-{n}"
        n += 1
    out.mkdir(parents=True)
    (out / "ledger.json").write_text(json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")

    m = svg = None
    massing_note = None
    try:
        m = massing.build(site, option, ledger)
        _, ps = massing.write(m, out)
        svg = ps.read_text(encoding="utf-8")
    except ValueError as e:
        massing_note = str(e)
    lay = None
    if m is not None:
        try:
            lay = layout.solve(site, option, ledger, m)
            layout.write(lay, site, m, ledger, out)
        except ValueError as e:
            massing_note = (massing_note + " " if massing_note else "") + f"Layout skipped: {e}"

    d = None
    prev = body.get("previous_run")
    if prev:
        ps_id, pf = _split_run_id(prev)
        d = engine.diff(_read(_run_folder(ps_id, pf) / "ledger.json"), ledger)
        (out / "diff.json").write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")

    # the money counts the homes the first plans place (25 Nov 2026); the memo carries the plans' open items, as the
    # command line's does
    pfm = proforma.build(site, option, ledger, m, lay)
    (out / "proforma.json").write_text(json.dumps(pfm, indent=2, ensure_ascii=False), encoding="utf-8")
    memo.write(ledger, out, m, d, svg, proforma=pfm, layout=lay, massing_error=massing_note if m is None else None)
    # who made it, as the page's own name for its person says (26 Nov 2026): a name kept in one browser, not a login,
    # so a run list can say whose draft is whose
    made_by = str(body.get("made_by") or "").strip()[:80]
    if made_by:
        (out / "made.json").write_text(json.dumps({"made_by": made_by}, ensure_ascii=False), encoding="utf-8")
    return run_payload(out, site_id, ledger, m, svg, d, massing_note, pfm)


def _made_by(folder: Path) -> str | None:
    f = folder / "made.json"
    try:
        return (_read(f).get("made_by") or None) if f.exists() else None
    except Exception:
        return None


# ---------------------------------------------------------------- Claude proposes (only with a key on this machine)

def capabilities() -> dict:
    from .. import propose
    return {**propose.available(), "static": False, "accepts_key": True, "writes_rules": True}


def _key_of(body: dict) -> str | None:
    """A person's own key, typed into the page and sent with this request only: passed to the SDK, never logged,
    never written."""
    k = body.get("api_key")
    return k.strip() if isinstance(k, str) and k.strip() else None


def _document_of(body: dict) -> tuple[bytes, str] | None:
    """A document the page read from the person's disk and sent as base64: bytes and name, never written here."""
    import base64
    d = body.get("document")
    if not isinstance(d, dict) or not d.get("data_b64"):
        return None
    name = str(d.get("name") or "document.pdf")
    if "/" in name or "\\" in name:
        name = name.replace("\\", "/").split("/")[-1]
    try:
        return base64.standard_b64decode(d["data_b64"]), name
    except Exception:
        raise ApiError(400, "The document is not valid base64.")


def _propose(fn, body: dict, **kw) -> dict:
    from .. import propose
    try:
        res = fn(**kw, api_key=_key_of(body))
    except propose.NoKey as e:
        raise ApiError(503, str(e))
    except propose.Refused as e:
        raise ApiError(422, str(e))
    except ValueError as e:
        raise ApiError(400, str(e))
    except OSError as e:
        raise ApiError(502, f"The model could not be reached: {e}")
    except Exception as e:  # the SDK's own errors (a bad key, a rate limit): said plainly
        raise ApiError(502, f"{type(e).__name__}: {str(e)[:300]}")
    out = propose.PROPOSALS_DIR / f"{res['slug']}-{datetime.now().strftime('%H%M%S')}.json"
    propose.save(res, out)
    res["file"] = out.name
    return res


def do_propose_site(body: Any) -> dict:
    """The model reads the site file (its public fields and the context frame) and proposes fields with evidence
    and a confidence; the proposal is logged in proposals/ and handed back for the person to confirm on the page.
    The site's own bytes are the only thing sent; nothing is written to the site here."""
    from .. import propose
    if not isinstance(body, dict) or not isinstance(body.get("site"), dict):
        raise ApiError(400, "Send {site: {...}, api_key?}.")
    return _propose(propose.propose_site, body, site=body["site"], document=_document_of(body))


def do_propose_rule(body: Any) -> dict:
    """The model reads a district schedule the page sent (a PDF from the person's disk) and proposes its clauses;
    logged in proposals/ with the document's name and hash, never its bytes."""
    from .. import propose
    if not isinstance(body, dict) or not body.get("district"):
        raise ApiError(400, "Send {district, document: {name, data_b64}, url?, api_key?}.")
    doc = _document_of(body)
    if doc is None:
        raise ApiError(400, "Send the schedule as document: {name, data_b64}.")
    return _propose(propose.propose_rule, body, document=doc, district=str(body["district"]).strip().upper(), url=body.get("url") or None)


def do_confirm(body: Any) -> dict:
    """A named person confirms a logged proposal: a rule proposal into rules/a_zoning_district.json."""
    from .. import propose
    if not isinstance(body, dict) or not body.get("file") or not str(body.get("by") or "").strip():
        raise ApiError(400, "Send {file, by, only?}.")
    name = str(body["file"])
    if not _slug_ok(name.replace(".json", "")) or not name.endswith(".json"):
        raise ApiError(400, "Bad proposal file name.")
    path = propose.PROPOSALS_DIR / name
    if not path.exists():
        raise ApiError(404, "No such proposal.")
    only = body.get("only") if isinstance(body.get("only"), list) else None
    try:
        rep = propose.confirm(path, str(body["by"]).strip(), only=only)
    except ValueError as e:
        raise ApiError(400, str(e))
    return rep


def load_run(site_id: str, folder: str) -> dict:
    out = _run_folder(site_id, folder)
    ledger = _read(out / "ledger.json")
    m = _read(out / "massing.json") if (out / "massing.json").exists() else None
    svg = (out / "massing.svg").read_text(encoding="utf-8") if (out / "massing.svg").exists() else None
    d = _read(out / "diff.json") if (out / "diff.json").exists() else None
    return run_payload(out, site_id, ledger, m, svg, d)


def diff_runs(frm: Any, to: Any) -> dict:
    """What changed between two existing runs, computed by the engine from their ledgers."""
    a_site, a_folder = _split_run_id(frm)
    b_site, b_folder = _split_run_id(to)
    a = _read(_run_folder(a_site, a_folder) / "ledger.json")
    b = _read(_run_folder(b_site, b_folder) / "ledger.json")
    d = engine.diff(a, b)
    d["from_run"], d["to_run"] = frm, to
    return d


def rewrite_memo(site_id: str, folder: str) -> dict:
    out = _run_folder(site_id, folder)
    ledger = _read(out / "ledger.json")
    m = _read(out / "massing.json") if (out / "massing.json").exists() else None
    svg = (out / "massing.svg").read_text(encoding="utf-8") if (out / "massing.svg").exists() else None
    d = _read(out / "diff.json") if (out / "diff.json").exists() else None
    memo.write(ledger, out, m, d, svg)
    stamp = ledger["run"]["stamp"]["stamp"]
    return {"run_id": f"{site_id}/{folder}", "revit": revit_summary(out, stamp)}


# ---------------------------------------------------------------- the guided start: lookup, read the site, suggest

def do_lookup(q: Any) -> dict:
    """A proposed site file for an address, from Nominatim and the City's open data (needs the network)."""
    if not isinstance(q, str) or len(q.strip()) < 4:
        raise ApiError(400, "Give an address to look up.")
    from .. import lookup
    try:
        return lookup.lookup(q.strip())
    except ValueError as e:
        raise ApiError(404, str(e))
    except OSError as e:
        raise ApiError(502, f"The lookup could not reach its sources: {e}")


def _site_and_date(body: Any) -> tuple[dict, date]:
    if not isinstance(body, dict) or not isinstance(body.get("site"), dict):
        raise ApiError(400, "Send {site: {...}, as_of?: 'YYYY-MM-DD'}.")
    try:
        on = date.fromisoformat(body["as_of"]) if body.get("as_of") else date.today()
    except ValueError:
        raise ApiError(400, "as_of must be a date written YYYY-MM-DD.")
    return body["site"], on


def do_read_site(body: Any) -> dict:
    """The site alone against layers A to C; nothing is written."""
    site, on = _site_and_date(body)
    return suggest.read_site(site, on)


def do_layout(body: Any) -> dict:
    """The block editor's check: the site and the option (with `layout.zones` where a person has placed blocks)
    are read under the rules, the massing built, the placement measured and the rules read back; nothing is
    written. Returns the layout record and the five sheets drawn from it."""
    site, on = _site_and_date(body)
    option = body.get("option")
    if not isinstance(option, dict):
        raise ApiError(400, "Send {site, option, as_of?}.")
    ledger = engine.evaluate(site, option, on)
    try:
        m = massing.build(site, option, ledger)
        lay = layout.solve(site, option, ledger, m)
    except ValueError as e:
        raise ApiError(422, str(e))
    return {"layout": lay, "sheets": layout.sheets(lay, site, m, ledger), "massing": m}


def do_suggest(body: Any) -> dict:
    """A rule-derived option for the site and the chosen programs, every figure with its rule."""
    site, on = _site_and_date(body)
    programs = body.get("programs") or []
    if not isinstance(programs, list):
        raise ApiError(400, "programs must be a list of rule ids.")
    mix = body.get("mix_shares")
    if mix is not None and not isinstance(mix, dict):
        raise ApiError(400, "mix_shares must be a set of shares (studio, one_bed, two_bed, three_bed_plus) or left out.")
    try:
        return suggest.suggest(site, programs, on, body.get("candidate") or "funder-ready", mix_shares=mix, fixed=body.get("fixed"))
    except ValueError as e:
        raise ApiError(400, str(e))


# ---------------------------------------------------------------- issues: a run handed from one reader to the next

ROLES = ("manager", "architect", "reader", "operator")


def list_issues(site_id: str | None) -> list[dict]:
    """Every issue note on the site's runs, newest first; with no site, on every site's runs (since 15 Nov 2026: the
    architect's chip must find a run issued on a site that is not on their screen, or not saved at all)."""
    if site_id and not _slug_ok(site_id):
        raise ApiError(400, "Bad site id.")
    bases = [OUTPUTS_DIR / site_id] if site_id else ([p for p in OUTPUTS_DIR.iterdir() if p.is_dir()] if OUTPUTS_DIR.exists() else [])
    out = []
    for base in bases:
        if not base.exists():
            continue
        for p in base.iterdir():
            f = p / "issues.json"
            if p.is_dir() and f.exists():
                try:
                    for it in _read(f):
                        out.append({**it, "run_id": f"{base.name}/{p.name}", "folder": p.name, "site": base.name})
                except Exception:
                    continue
    out.sort(key=lambda i: i.get("issued_at", ""), reverse=True)
    return out


def add_issue(site_id: str, folder: str, body: Any) -> dict:
    """Record that a reader issued this run to another: who, to whom, a note, when."""
    out = _run_folder(site_id, folder)
    if not isinstance(body, dict):
        raise ApiError(400, "Send {by, to, note, name?}.")
    by, to = body.get("by"), body.get("to")
    if by not in ROLES or to not in ROLES:
        raise ApiError(400, f"by and to must be one of {', '.join(ROLES)}.")
    f = out / "issues.json"
    items = _read(f) if f.exists() else []
    # the sender's name travels with the note (16 Nov 2026), so the chip and the memo say who, not only which role; and
    # the person it is for (26 Nov 2026), so "issued to you" means that person and not whoever opens the page
    item = {"id": datetime.now().strftime("%Y%m%dT%H%M%S%f"), "issued_at": datetime.now().isoformat(timespec="seconds"),
            "by": by, "to": to, "name": str(body.get("name") or "").strip()[:80], "to_name": str(body.get("to_name") or "").strip()[:80],
            "note": str(body.get("note") or "")[:600]}
    items.append(item)
    f.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    return {**item, "run_id": f"{site_id}/{folder}", "folder": folder}


# ---------------------------------------------------------------- PDF

def find_browser() -> str | None:
    """A Chromium browser that can print to PDF headlessly: FFM_BROWSER if set, else Edge (on every Windows
    machine) or Chrome or Chromium in their usual places or on PATH."""
    cands = [os.environ.get("FFM_BROWSER")]
    if sys.platform == "win32":
        for base in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES"), os.environ.get("LOCALAPPDATA")):
            if base:
                cands += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                          os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    elif sys.platform == "darwin":
        cands += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                  "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge", "chrome"):
        cands.append(shutil.which(name))
    return next((c for c in cands if c and os.path.isfile(c)), None)


def render_pdf(body: Any) -> bytes:
    """The page's paper memo (a whole HTML document) printed to PDF by a headless browser. The page builds the
    document, so the PDF is exactly what it shows in the print dialog; this only does the printing. The
    browser's own header and footer are off: the document carries its own on every page."""
    html = body.get("html") if isinstance(body, dict) else None
    if not isinstance(html, str) or "<html" not in html[:400].lower():
        raise ApiError(400, "Send the memo as {html: '<!doctype html>…'}.")
    browser = find_browser()
    if not browser:
        raise ApiError(501, "No Edge or Chrome was found to print the PDF; use Print and choose Save as PDF.")
    with tempfile.TemporaryDirectory(prefix="first-read-pdf-") as tmp:
        src, out = Path(tmp) / "memo.html", Path(tmp) / "memo.pdf"
        src.write_text(html, encoding="utf-8")
        cmd = [browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
               "--no-pdf-header-footer", f"--user-data-dir={Path(tmp) / 'profile'}", "--virtual-time-budget=8000",
               f"--print-to-pdf={out}", src.as_uri()]
        try:
            subprocess.run(cmd, capture_output=True, timeout=90, check=False)
        except subprocess.TimeoutExpired:
            raise ApiError(504, "The browser took too long to print the PDF.")
        if not out.exists() or out.stat().st_size == 0:
            raise ApiError(500, "The browser did not write the PDF.")
        return out.read_bytes()


# ---------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = "ffm-ui/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # one quiet line per request
        sys.stderr.write("%s %s\n" % (self.command, self.path))

    # -- responses
    def _send(self, status: int, body: bytes, ctype: str, extra: dict | None = None, cache: str = "no-store",
              gz: bytes | None = None) -> None:
        """Text is sent gzipped where the browser takes it (16 Nov 2026: app.js, before it was split into modules,
        went over the wire as 413 KB on every load). `gz` is the body already compressed, for a static file kept compressed by its ETag."""
        extra = dict(extra or {})
        if len(body) > 1024 and ctype.startswith(GZIP_TYPES) and "gzip" in (self.headers.get("Accept-Encoding") or ""):
            body = gz if gz is not None else gzip.compress(body, compresslevel=6)
            extra["Content-Encoding"] = "gzip"
            extra["Vary"] = "Accept-Encoding"
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj: Any, status: int = 200) -> None:
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _static(self, name: str) -> None:
        """The page's own files carry an ETag and are revalidated on every load (no-cache, not no-store): an edit
        shows at once, an unchanged module comes back as a 304 with no body."""
        p = STATIC_DIR / name
        if not STATIC_PATH.match(name) or not p.is_file():
            raise ApiError(404, "Not found.")
        data = p.read_bytes()
        tag = '"%s"' % hashlib.sha1(data).hexdigest()[:20]
        if self.headers.get("If-None-Match") == tag:
            self.send_response(304)
            self.send_header("ETag", tag)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            return
        ctype = STATIC_TYPES[p.suffix]
        gz = None
        if ctype.startswith(GZIP_TYPES) and len(data) > 1024:
            gz = _GZIP_CACHE.get(tag)
            if gz is None:
                gz = _GZIP_CACHE[tag] = gzip.compress(data, compresslevel=6)
        self._send(200, data, ctype, {"ETag": tag}, cache="no-cache", gz=gz)

    def _run_file(self, site_id: str, folder: str, name: str, download: bool) -> None:
        if name not in RUN_FILES:
            raise ApiError(404, "That file is not served.")
        p = _run_folder(site_id, folder) / name
        if not p.exists():
            raise ApiError(404, f"{name} does not exist for this run yet.")
        extra = {}
        if download:
            stem, ext = name.rsplit(".", 1)
            extra["Content-Disposition"] = f'attachment; filename="{site_id}_{folder}_{stem}.{ext}"'
        self._send(200, p.read_bytes(), RUN_FILES[name], extra)

    def _body(self) -> Any:
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except ValueError:
            raise ApiError(400, "The request body is not JSON.")

    # -- routing
    def do_GET(self) -> None:
        self._route("GET")

    def do_HEAD(self) -> None:
        self._route("GET")

    def do_POST(self) -> None:
        self._route("POST")

    def _route(self, method: str) -> None:
        u = urlparse(self.path)
        path, q = u.path, parse_qs(u.query)
        first = lambda key: (q.get(key) or [None])[0]  # noqa: E731
        try:
            if method == "GET":
                if path in ("/", "/index.html", "/home.html"):
                    return self._static("home.html")
                if path in ("/app", "/app.html"):
                    return self._static("index.html")
                if path == "/favicon.ico":
                    return self._static("brand/mark-tile.svg")
                if STATIC_PATH.match(path[1:]):
                    return self._static(path[1:])
                if path == "/api/rules":
                    return self._json(list_rules(first("as_of")))
                if path == "/api/capabilities":
                    return self._json(capabilities())
                if path == "/api/sites":
                    return self._json(list_sites())
                mm = re.match(r"^/api/sites/([^/]+)$", path)
                if mm:
                    return self._json(load_site(mm.group(1)))
                if path == "/api/options":
                    return self._json(list_options(first("site")))
                mm = re.match(r"^/api/options/([^/]+)$", path)
                if mm:
                    return self._json(load_option(mm.group(1)))
                if path == "/api/runs":
                    return self._json(list_runs(first("site")))
                if path == "/api/diff":
                    return self._json(diff_runs(first("from"), first("to")))
                if path == "/api/lookup":
                    return self._json(do_lookup(first("q")))
                if path == "/api/issues":
                    return self._json(list_issues(first("site")))
                mm = re.match(r"^/api/runs/([^/]+)/([^/]+)$", path)
                if mm:
                    return self._json(load_run(mm.group(1), mm.group(2)))
                mm = re.match(r"^/(?:api|data)/runs/([^/]+)/([^/]+)/([^/]+)$", path)
                if mm:
                    return self._run_file(mm.group(1), mm.group(2), mm.group(3), first("download") is not None)
                raise ApiError(404, "Not found.")
            body = self._body()
            if path == "/api/run":
                return self._json(do_run(body))
            if path == "/api/read-site":
                return self._json(do_read_site(body))
            if path == "/api/suggest":
                return self._json(do_suggest(body))
            if path == "/api/layout":
                return self._json(do_layout(body))
            if path == "/api/propose/site":
                return self._json(do_propose_site(body))
            if path == "/api/propose/rule":
                return self._json(do_propose_rule(body))
            if path == "/api/confirm":
                return self._json(do_confirm(body))
            mm = re.match(r"^/api/runs/([^/]+)/([^/]+)/issue$", path)
            if mm:
                return self._json(add_issue(mm.group(1), mm.group(2), body), 201)
            if path == "/api/options":
                return self._json(save_new(OPTIONS_DIR, body, "option"), 201)
            if path == "/api/sites":
                return self._json(save_new(SITES_DIR, body, "site"), 201)
            mm = re.match(r"^/api/runs/([^/]+)/([^/]+)/memo$", path)
            if mm:
                return self._json(rewrite_memo(mm.group(1), mm.group(2)))
            if path == "/api/pdf":
                return self._send(200, render_pdf(body), "application/pdf")
            raise ApiError(404, "Not found.")
        except ApiError as e:
            self._json({"error": str(e)}, e.status)
        except Exception as e:  # a bug: say so, with the traceback, rather than hang the page
            self._json({"error": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()}, 500)


def serve(port: int = 8765, open_browser: bool = True) -> int:
    url = f"http://127.0.0.1:{port}"
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError as e:
        print(f"Could not listen on {url}: {e}. Try --port with another number.", file=sys.stderr)
        return 1
    print(f"First Read UI: {url}   (Ctrl+C stops it)")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0
