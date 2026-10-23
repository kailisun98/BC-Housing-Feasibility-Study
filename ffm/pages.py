"""Build the web UI as a static site, for GitHub Pages: `python -m ffm pages --out _site`.

GitHub Pages serves files only, so the page cannot call the Python server. The static build gives it
two things instead:

  data/     the inputs (sites, options, the rule list) and every committed run (ledger, massing,
            memo, diff) as plain files, so the page opens past runs the moment it loads
  engine/   the engine's own source files (ffm/*.py and rules/*.json), which the page loads into
            Pyodide, the WebAssembly build of CPython, so *Run the rules* runs the same code in the
            browser. Nothing is uploaded; a browser run is kept in the tab and can be downloaded.

The engine stays dependency-free; Pyodide is fetched by the page from a CDN at run time and only in
this build. Files built from an office template (the Revit result, the sheet exports) are never
copied, whatever is on disk.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from . import __version__
from .ui import server as ui

PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.js"
ENGINE_FILES = ["ffm/__init__.py", "ffm/rules_loader.py", "ffm/checks.py", "ffm/engine.py", "ffm/massing.py", "ffm/memo.py"]
RUN_FILES_PUBLIC = ["ledger.json", "massing.json", "massing.svg", "diff.json", "memo.md", "memo.html", "ffm_sheet_notes.json"]


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def _clear(out: Path) -> None:
    """Empty the output folder but keep a .git inside it, so a checkout of the gh-pages branch can
    be rebuilt in place and pushed."""
    for child in out.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def build(out: Path, pyodide_url: str = PYODIDE_URL) -> dict:
    out = Path(out)
    if out.exists():
        _clear(out)
    (out / "data").mkdir(parents=True, exist_ok=True)
    n = 0

    # the tool as app.html, with the static configuration injected where index.html leaves a marker; the
    # home page as index.html, so the site opens on it (the local server routes them the same way)
    html = (ui.STATIC_DIR / "index.html").read_text(encoding="utf-8")
    config = {"pyodide_url": pyodide_url, "built_at": datetime.now().isoformat(timespec="seconds"), "engine_version": __version__}
    marker = "<!-- static-config -->"
    if marker not in html:
        raise RuntimeError("index.html has no <!-- static-config --> marker")
    html = html.replace(marker, f"<script>window.FFM_STATIC = {json.dumps(config)};</script>")
    (out / "app.html").write_text(html, encoding="utf-8")
    shutil.copy(ui.STATIC_DIR / "home.html", out / "index.html")
    for name in ("app.js", "app.css", "home.js", "home.css"):
        shutil.copy(ui.STATIC_DIR / name, out / name)
    (out / ".nojekyll").write_text("", encoding="utf-8")
    n += 7

    # inputs
    sites = ui.list_sites()
    _write_json(out / "data" / "sites.json", sites)
    (out / "data" / "sites").mkdir(exist_ok=True)
    for s in sites:
        shutil.copy(ui.SITES_DIR / s["file"], out / "data" / "sites" / f"{s['id']}.json")
        n += 1
    options = [{k: v for k, v in o.items() if k != "for_site"} for o in ui.list_options(None)]
    _write_json(out / "data" / "options.json", options)
    (out / "data" / "options").mkdir(exist_ok=True)
    for o in options:
        shutil.copy(ui.OPTIONS_DIR / o["file"], out / "data" / "options" / f"{o['id']}.json")
        n += 1
    _write_json(out / "data" / "rules.json", ui.list_rules(None))
    n += 3

    # runs: everything committed, nothing from an office template
    runs = []
    for s in sites:
        for r in ui.list_runs(s["id"]):
            r = dict(r)
            r["folder_abs"] = None
            r["revit"] = None
            src = ui.OUTPUTS_DIR / s["id"] / r["folder"]
            dst = out / "data" / "runs" / s["id"] / r["folder"]
            dst.mkdir(parents=True, exist_ok=True)
            for name in RUN_FILES_PUBLIC:
                if (src / name).exists():
                    shutil.copy(src / name, dst / name)
                    n += 1
            runs.append(r)
    runs.sort(key=lambda r: r["written"], reverse=True)
    _write_json(out / "data" / "runs.json", runs)

    # the engine, for Pyodide
    files = list(ENGINE_FILES) + [f"rules/{p.name}" for p in sorted((ui.ROOT / "rules").glob("*.json"))]
    for f in files:
        dst = out / "engine" / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ui.ROOT / f, dst)
        n += 1
    _write_json(out / "data" / "engine-files.json", files)
    return {"out": str(out), "files": n, "sites": len(sites), "options": len(options), "runs": len(runs)}
