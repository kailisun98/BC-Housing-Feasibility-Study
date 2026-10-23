"""The web UI's server: standard-library HTTP, JSON endpoints, three static files.

Started with `python -m ffm ui [--port 8765] [--no-browser]`. The page never calculates a rule:
this module loads inputs, calls the engine exactly as the command line does, writes the same run
folder (ledger, memo, massing, diff) and hands the results back as JSON.

    GET  /                                  the home page (home.html, home.css, home.js beside this file)
    GET  /app.html                          the tool (index.html, app.js, app.css beside this file)
    GET  /data/runs/<site>/<folder>/<file>  a run file at the path the GitHub Pages build gives it, so the
                                            home page's links work the same here and on the web
    GET  /api/rules?as_of=YYYY-MM-DD        [{id, layer, layer_title, title, version_effective_from}]
    GET  /api/sites                         [{id, address, zoning_district, file}]
    GET  /api/sites/<id>                    site JSON
    POST /api/sites                         save a new site JSON (body: site); refuses to overwrite
    GET  /api/options?site=<id>             [{id, name, file, for_site}]
    GET  /api/options/<id>                  option JSON
    POST /api/options                       save a new option JSON (body: option); refuses to overwrite
    POST /api/run                           body {site, option, as_of, previous_run?}; site and option are
                                            ids or whole JSON objects -> {run_id, ledger, massing, svg, diff?}
    GET  /api/runs?site=<id>                past runs: as_of, stamp, verdicts, Revit result present?
    GET  /api/runs/<site>/<folder>          a past run as /api/run returns it (ledger, massing, svg, diff, revit)
    GET  /api/diff?from=<run_id>&to=<run_id>  engine.diff between two existing runs' ledgers
    GET  /api/runs/<site>/<folder>/<file>   memo.html | memo.md | ledger.json | massing.json | massing.svg
                                            | diff.json | ffm_revit_result.json | ffm_sheet_notes.json
                                            | ffm_sheet.png | ffm_sheet.pdf   (?download=1 to attach)
    POST /api/runs/<site>/<folder>/memo     rewrite memo.md / memo.html for that run (picks up a Revit result)

Runs are written to outputs/<site-id>/<timestamp>/, so they are also usable from the command line.
"""

from __future__ import annotations

import json
import re
import sys
import threading
import traceback
import webbrowser
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .. import engine, massing, memo
from ..rules_loader import RULES_DIR, load_rules

ROOT = Path(__file__).resolve().parent.parent.parent
SITES_DIR = ROOT / "sites"
OPTIONS_DIR = ROOT / "options"
OUTPUTS_DIR = ROOT / "outputs"
STATIC_DIR = Path(__file__).resolve().parent

SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")
STATIC_FILES = {"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8",
                "app.css": "text/css; charset=utf-8", "home.html": "text/html; charset=utf-8",
                "home.js": "text/javascript; charset=utf-8", "home.css": "text/css; charset=utf-8",
                "hero-memo.jpg": "image/jpeg", "hero-memo-790.jpg": "image/jpeg"}
RUN_FILES = {
    "memo.html": "text/html; charset=utf-8", "memo.md": "text/markdown; charset=utf-8",
    "ledger.json": "application/json; charset=utf-8", "massing.json": "application/json; charset=utf-8",
    "massing.svg": "image/svg+xml", "diff.json": "application/json; charset=utf-8",
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
        out.append({"id": d.get("id") or p.stem, "address": d.get("address", ""), "zoning_district": d.get("zoning_district", ""),
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


def list_options(site_id: str | None) -> list[dict]:
    out = []
    for p in sorted(OPTIONS_DIR.glob("*.json")):
        try:
            d = _read(p)
        except Exception:
            continue
        oid = d.get("id") or p.stem
        for_site = bool(site_id) and (d.get("site") == site_id or oid.startswith(site_id + "-") or oid == site_id)
        out.append({"id": oid, "name": d.get("name", oid), "file": p.name, "for_site": for_site})
    out.sort(key=lambda o: (not o["for_site"], o["id"]))
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
        out.append({"id": r.id, "layer": r.layer, "layer_title": r.layer_title, "title": r.title, "jurisdiction": r.jurisdiction,
                    "applies_to_districts": r.applies_to_districts,
                    "version_effective_from": v.effective_from.isoformat() if v else None})
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
        runs.append({
            "run_id": f"{site_id}/{p.name}", "folder": p.name, "folder_abs": str(p),
            "as_of": run["as_of"], "stamp": stamp, "option_id": run.get("option_id"),
            "option_name": (L.get("inputs", {}).get("option") or {}).get("name"),
            "written": datetime.fromtimestamp(lp.stat().st_mtime).isoformat(timespec="seconds"),
            "verdicts": {"outright": ans["allowed"]["outright"]["verdict"], "by_rezoning": ans["allowed"]["by_rezoning"]["verdict"],
                         "funded": ans["funded"]["verdict"]},
            "has_diff": (p / "diff.json").exists(), "has_massing": (p / "massing.json").exists(),
            "revit": revit_summary(p, stamp),
        })
    runs.sort(key=lambda r: r["written"], reverse=True)
    return runs


def run_payload(out: Path, site_id: str, ledger: dict, m: dict | None, svg: str | None, d: dict | None,
                massing_note: str | None = None) -> dict:
    stamp = ledger["run"]["stamp"]["stamp"]
    return {"run_id": f"{site_id}/{out.name}", "folder": out.name, "folder_abs": str(out),
            "as_of": ledger["run"]["as_of"], "stamp": stamp, "ledger": ledger, "massing": m, "svg": svg, "diff": d,
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

    d = None
    prev = body.get("previous_run")
    if prev:
        ps_id, pf = _split_run_id(prev)
        d = engine.diff(_read(_run_folder(ps_id, pf) / "ledger.json"), ledger)
        (out / "diff.json").write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")

    memo.write(ledger, out, m, d, svg)
    return run_payload(out, site_id, ledger, m, svg, d, massing_note)


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


# ---------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = "ffm-ui/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # one quiet line per request
        sys.stderr.write("%s %s\n" % (self.command, self.path))

    # -- responses
    def _send(self, status: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj: Any, status: int = 200) -> None:
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _static(self, name: str) -> None:
        p = STATIC_DIR / name
        if name not in STATIC_FILES or not p.exists():
            raise ApiError(404, "Not found.")
        self._send(200, p.read_bytes(), STATIC_FILES[name])

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
                if path in ("/", "/index.html"):
                    return self._static("home.html")
                if path in ("/app", "/app.html"):
                    return self._static("index.html")
                if path in ("/app.js", "/app.css", "/home.js", "/home.css", "/hero-memo.jpg", "/hero-memo-790.jpg"):
                    return self._static(path[1:])
                if path == "/favicon.ico":
                    return self._send(204, b"", "image/x-icon")
                if path == "/api/rules":
                    return self._json(list_rules(first("as_of")))
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
            if path == "/api/options":
                return self._json(save_new(OPTIONS_DIR, body, "option"), 201)
            if path == "/api/sites":
                return self._json(save_new(SITES_DIR, body, "site"), 201)
            mm = re.match(r"^/api/runs/([^/]+)/([^/]+)/memo$", path)
            if mm:
                return self._json(rewrite_memo(mm.group(1), mm.group(2)))
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
    print(f"Funding-Fit Memo UI: {url}   (Ctrl+C stops it)")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0
