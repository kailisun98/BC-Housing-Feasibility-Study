/* The engine in the browser (static build only): Pyodide from its CDN, the engine's Python files from engine/, and
   a small shim that exposes run, diff, suggest, read-site, layout and the Claude request builders. Loaded once. */

import { $, setStatus } from "./util.js";
import { STATIC } from "./state.js";

export let engine = null;               // {pyodide, run, diff} once loaded

let enginePromise = null;

function setEngineChip(text, kind) {
  const chip = $("#engine-chip");
  chip.hidden = false;
  chip.textContent = text;
  chip.className = "engine-chip " + (kind || "");
}

/* On the web the page itself can come from a cache that predates the last deploy (GitHub Pages keeps HTML for
   ten minutes, browsers longer), while its data is already new. The page asks for the build's own record with
   the cache bypassed; a newer build reloads the page once (a session mark stops a loop), and if that still
   shows the old page a chip says so and offers the reload. */
export async function checkForNewerBuild() {
  if (!STATIC || !STATIC.built_at) return;
  let fresh = null;
  try { fresh = await (await fetch("data/build.json", { cache: "no-store" })).json(); } catch (e) { return; }
  if (!fresh || !fresh.built_at || fresh.built_at <= STATIC.built_at) return;
  const key = "ffm.reloaded-for";
  let done = "";
  try { done = sessionStorage.getItem(key) || ""; } catch (e) { /* storage off */ }
  if (done !== fresh.built_at) {
    try { sessionStorage.setItem(key, fresh.built_at); } catch (e) { /* storage off */ }
    location.reload();
    return;
  }
  setStatus(`A newer version of this page was published ${fresh.built_at.replace("T", " ")}; the one on screen is from ${STATIC.built_at.replace("T", " ")}. Press Ctrl+F5 (Cmd+Shift+R) to load it.`, "busy");
}

export function loadScript(src, integrity = "") {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src; s.async = true;
    if (integrity) { s.integrity = integrity; s.crossOrigin = "anonymous"; }
    s.onload = resolve;
    s.onerror = () => reject(new Error(`could not load ${src}`));
    document.head.appendChild(s);
  });
}

const ENGINE_SHIM = `
import json, sys
from datetime import date
sys.path.insert(0, ".")
from ffm import engine, layout, massing, memo, proforma

def ffm_run(site_json, option_json, as_of, previous_json):
    site, option = json.loads(site_json), json.loads(option_json)
    L = engine.evaluate(site, option, date.fromisoformat(as_of))
    m = svg = note = lay = sheets = None
    try:
        m = massing.build(site, option, L)
        svg = massing.svg(m)
    except ValueError as e:
        note = str(e)
    if m is not None:
        try:
            lay = layout.solve(site, option, L, m)
            sheets = layout.sheets(lay, site, m, L)
        except ValueError as e:
            note = (note + " " if note else "") + "Layout skipped: " + str(e)
    d = engine.diff(json.loads(previous_json), L) if previous_json else None
    pf = proforma.build(site, option, L, m, lay)
    md = memo.markdown(L, m, d, proforma=pf, layout=lay)
    return json.dumps({"ledger": L, "massing": m, "svg": svg, "diff": d, "massing_note": note, "proforma": pf, "layout": lay, "sheets": sheets,
                       "memo_md": md, "memo_html": memo.html_page(md, svg, {k + ".svg": v for k, v in (sheets or {}).items()})})

def ffm_diff(a_json, b_json):
    return json.dumps(engine.diff(json.loads(a_json), json.loads(b_json)))

def ffm_layout(site_json, option_json, as_of):
    site, option = json.loads(site_json), json.loads(option_json)
    L = engine.evaluate(site, option, date.fromisoformat(as_of))
    m = massing.build(site, option, L)
    lay = layout.solve(site, option, L, m)
    return json.dumps({"layout": lay, "sheets": layout.sheets(lay, site, m, L), "massing": m})

from ffm import suggest, lookup

def ffm_suggest(site_json, programs_json, as_of, candidate, mix_json=None, fixed_json=None):
    mix = json.loads(mix_json) if mix_json else None
    fixed = json.loads(fixed_json) if fixed_json else None
    return json.dumps(suggest.suggest(json.loads(site_json), json.loads(programs_json), date.fromisoformat(as_of), candidate, mix_shares=mix, fixed=fixed))

def ffm_read_site(site_json, as_of):
    return json.dumps(suggest.read_site(json.loads(site_json), date.fromisoformat(as_of)))

def ffm_lookup_assemble(address, lat, lon, display, zoning_json, parcels_json, elements_json, radius_m, query):
    elements = json.loads(elements_json) if elements_json else None
    return json.dumps(lookup.assemble(address, lat, lon, display, json.loads(zoning_json), json.loads(parcels_json), elements, radius_m, query))

def ffm_parcel_center(parcels_json, address=""):
    c = lookup._parcel_center(json.loads(parcels_json), address)
    return json.dumps(list(c) if c else None)

def ffm_parse_address(address):
    return json.dumps(lookup.parse_address(address))

def ffm_civic_address(number, street):
    return json.dumps(lookup.civic_address(number, street))

def ffm_city_elements(streets_json, buildings_json, trees_json, lanes_json="[]"):
    return json.dumps(lookup.city_elements(json.loads(streets_json), json.loads(buildings_json), json.loads(trees_json), json.loads(lanes_json or "[]")))

def ffm_lookup_assemble_from(address, lat, lon, display, zoning_json, parcels_json, elements_json, radius_m, query, source, extra_json="{}"):
    elements = json.loads(elements_json) if elements_json else None
    return json.dumps(lookup.assemble(address, lat, lon, display, json.loads(zoning_json), json.loads(parcels_json), elements, radius_m, query, source,
                                      extra=json.loads(extra_json or "{}")))

def ffm_nearest_where(address):
    return json.dumps(lookup.nearest_where(address))

from ffm import propose

def ffm_propose_request(kind, site_json, document_b64, document_name, district, model):
    site = json.loads(site_json) if site_json else None
    return json.dumps(propose.browser_request(kind, site, document_b64 or None, document_name or None, district or None, model or None))

def ffm_proposal_from_response(kind, response_json, tool, model, prompt_sha256, site_json, district, url, document_json):
    site = json.loads(site_json) if site_json else None
    doc = json.loads(document_json) if document_json else None
    return json.dumps(propose.browser_proposal(kind, json.loads(response_json), tool, model, prompt_sha256, site, district or None, url or None, doc))
`;

export function loadEngine() {
  if (!STATIC) return Promise.resolve(null);
  if (enginePromise) return enginePromise;
  enginePromise = (async () => {
    setEngineChip("Loading the rules engine, about 10 MB, once", "loading");
    await loadScript(STATIC.pyodide_url);
    const pyodide = await window.loadPyodide({ indexURL: STATIC.pyodide_url.replace(/pyodide\.js(\?.*)?$/, "") });
    // the engine's files are named with the build's time, so a browser never pairs this page with the last deploy's
    // engine out of its cache (Pages serves them with max-age=600)
    const v = encodeURIComponent((STATIC && STATIC.built_at) || "");
    const files = await (await fetch(`data/engine-files.json?v=${v}`)).json();
    for (const f of files) {
      const r = await fetch(`engine/${f}?v=${v}`);
      if (!r.ok) throw new Error(`engine file ${f}: ${r.status}`);
      const dir = f.split("/").slice(0, -1).join("/");
      if (dir) pyodide.FS.mkdirTree(dir);
      pyodide.FS.writeFile(f, await r.text());
    }
    pyodide.runPython(ENGINE_SHIM);
    engine = { pyodide, run: pyodide.globals.get("ffm_run"), diff: pyodide.globals.get("ffm_diff"),
               suggest: pyodide.globals.get("ffm_suggest"), readSite: pyodide.globals.get("ffm_read_site"), lookupAssemble: pyodide.globals.get("ffm_lookup_assemble"),
               parcelCenter: pyodide.globals.get("ffm_parcel_center"), cityElements: pyodide.globals.get("ffm_city_elements"),
               parseAddress: pyodide.globals.get("ffm_parse_address"), civicAddress: pyodide.globals.get("ffm_civic_address"),
               lookupAssembleFrom: pyodide.globals.get("ffm_lookup_assemble_from"), nearestWhere: pyodide.globals.get("ffm_nearest_where"),
               proposeRequest: pyodide.globals.get("ffm_propose_request"), proposalFromResponse: pyodide.globals.get("ffm_proposal_from_response"),
               layout: pyodide.globals.get("ffm_layout") };
    setEngineChip(`Engine ready in your browser · Python ${pyodide.runPython("import sys; '%d.%d' % sys.version_info[:2]")}`, "ready");
    return engine;
  })().catch(e => {
    setEngineChip(`Engine did not load: ${e.message}. Past runs still open.`, "error");
    enginePromise = null;
    throw e;
  });
  return enginePromise;
}
