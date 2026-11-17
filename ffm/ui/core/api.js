/* Two backends, one call. `api` and `postJSON` talk to the local Python server (python -m ffm ui), or, on a static
   host such as GitHub Pages where `python -m ffm pages` set window.FFM_STATIC, to `staticApi`: the data files
   under data/ plus the engine itself running in the browser through Pyodide (core/engine.js). */

import { blobUrl, downloadJSON, fetchJSON, fetchText, todayISO } from "./util.js";
import { STATIC } from "./state.js";
import { engine, loadEngine } from "./engine.js";

export async function api(path, opts = {}) {
  if (STATIC) return staticApi(path, opts);
  const r = await fetch(path.replace(/^\//, ""), opts);
  let body = null;
  try { body = await r.json(); } catch (e) { body = null; }
  if (!r.ok) throw new Error((body && body.error) || `${r.status} ${r.statusText}`);
  return body;
}

export async function postJSON(path, obj) {
  return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(obj) });
}

const browserRuns = new Map();   // runs made in this tab: run_id -> {payload, summary}

async function ledgerOf(runId) {
  if (browserRuns.has(runId)) return browserRuns.get(runId).payload.ledger;
  return fetchJSON(`data/runs/${runId}/ledger.json`);
}

/* The committed runs' listing (data/runs.json, written by pages.py from server.list_runs), fetched once for
   loadStaticRun: a static host's data does not change under an open page. */
let listing = null;
const runListing = () => listing || (listing = fetchJSON("data/runs.json").catch(e => { listing = null; throw e; }));

async function loadStaticRun(runId) {
  if (browserRuns.has(runId)) return browserRuns.get(runId).payload;
  // a base run has no diff.json: ask for it only when the listing says the run has one, so the console shows no 404
  // (16 Nov 2026); a run the listing does not name is asked for as before
  const listed = (await runListing().catch(() => [])).find(r => r.run_id === runId);
  const wantDiff = !listed || !!listed.has_diff;
  const [ledger, massing, svg, diff, proforma, layout] = await Promise.all([
    fetchJSON(`data/runs/${runId}/ledger.json`), fetchJSON(`data/runs/${runId}/massing.json`, true),
    fetchText(`data/runs/${runId}/massing.svg`, true), wantDiff ? fetchJSON(`data/runs/${runId}/diff.json`, true) : null,
    fetchJSON(`data/runs/${runId}/proforma.json`, true), fetchJSON(`data/runs/${runId}/layout.json`, true),
  ]);
  let sheets = null;
  if (layout) {
    const names = ["stacking", "plans", "elevations", "axon", "site-plan"];
    const texts = await Promise.all(names.map(n => fetchText(`data/runs/${runId}/${n}.svg`, true)));
    sheets = Object.fromEntries(names.map((n, i) => [n, texts[i]]).filter(([, t]) => t));
  }
  const base = `data/runs/${runId}`;
  return { run_id: runId, folder: runId.split("/")[1], folder_abs: null, as_of: ledger.run.as_of, stamp: ledger.run.stamp.stamp,
           ledger, massing, svg, diff, proforma, layout, sheets, massing_note: null, revit: null, files: {},
           downloads: { html: `${base}/memo.html`, md: `${base}/memo.md`, massing: massing ? `${base}/massing.json` : null } };
}

/* On the web the browser fetches the point and the City's records itself (both sources allow it) and the engine
   assembles the site from them, as lookup.py does on the local server. */
async function staticLookup(q) {
  if (!q || q.trim().length < 4) throw new Error("Give an address to look up.");
  await loadEngine();
  const cov = (ds, params) => fetch(`https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/${ds}/records?${new URLSearchParams(params)}`).then(r => r.ok ? r.json() : { results: [] }).then(j => j.results || []);
  // the point: the City's own address list first (exact, and it names the parcel), Nominatim within Metro Vancouver
  // otherwise, preferring a building over a street
  let lat, lon, display, parcels;
  const parsed = JSON.parse(engine.parseAddress(q.trim()));
  let found = null;
  if (parsed.civic_number && parsed.like) {
    const rows = await cov("property-addresses", { where: `civic_number=${parsed.civic_number} AND std_street like "${parsed.like.replace(/"/g, "")}%"`, limit: "10" });
    const exact = parsed.suffix ? rows.filter(r => String(r.std_street || "").toUpperCase() === parsed.street) : [];
    found = (exact.length ? exact : rows)[0] || null;
  }
  if (found && found.geo_point_2d && found.geo_point_2d.lat != null) {
    lat = Number(found.geo_point_2d.lat); lon = Number(found.geo_point_2d.lon);
    display = `${JSON.parse(engine.civicAddress(String(found.civic_number), String(found.std_street)))}, Vancouver, BC (City of Vancouver property address${found.geo_local_area ? `, ${found.geo_local_area}` : ""})`;
    parcels = found.site_id ? await cov("property-parcel-polygons", { where: `site_id="${found.site_id}"`, limit: "3" }) : [];
    if (!parcels.length) parcels = await cov("property-parcel-polygons", { where: `within_distance(geom, geom'POINT(${lon} ${lat})', 15m)`, limit: "5" });
  } else {
    const tries = /vancouver/i.test(q) ? [q.trim()] : [q.trim(), q.trim().replace(/[ ,]+$/, "") + ", Vancouver, BC"];
    let geo = [];
    for (const t of tries) {
      geo = await (await fetch(`https://nominatim.openstreetmap.org/search?${new URLSearchParams({ q: t, format: "jsonv2", limit: "5", countrycodes: "ca", viewbox: "-123.45,49.00,-122.40,49.45", bounded: "1" })}`, { headers: { Accept: "application/json" } })).json();
      if (geo.length) break;
    }
    if (!geo.length) throw new Error(`Nothing in Metro Vancouver matched "${q}"; try the civic number, the street and its suffix (998 E 19th Ave).`);
    const best = (parsed.civic_number && geo.find(r => String(r.display_name || "").startsWith(`${parsed.civic_number},`))) || geo[0];
    lat = Number(best.lat); lon = Number(best.lon); display = best.display_name || "";
    parcels = await cov("property-parcel-polygons", { where: `within_distance(geom, geom'POINT(${lon} ${lat})', 15m)`, limit: "5" });
  }
  const zoning = await cov("zoning-districts-and-labels", { where: `within_distance(geom, geom'POINT(${lon} ${lat})', 3m)`, limit: "3" });
  // the surroundings around the parcel's centre: the City's streets, 2009 building footprints and public trees
  // (three quick requests, paged by a hundred), else the Overpass API as python -m ffm context queries it; if
  // neither answers, the site still comes back, without its context
  const radius = 120;
  const c = JSON.parse(engine.parcelCenter(JSON.stringify(parcels), q.trim())) || [lat, lon];
  const within = async ds => {
    const out = [];
    for (let page = 0; page < 4; page++) {
      const r = await fetch(`https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/${ds}/records?${new URLSearchParams({ where: `within_distance(geom, geom'POINT(${c[1]} ${c[0]})', ${radius}m)`, limit: "100", offset: String(page * 100) })}`);
      if (!r.ok) break;
      const j = await r.json();
      out.push(...(j.results || []));
      if ((j.results || []).length < 100 || out.length >= (j.total_count || 0)) break;
    }
    return out;
  };
  let elements = null, source = "osm", query = "";
  try {
    const [streets, buildings, trees] = await Promise.all([within("public-streets"), within("building-footprints-2009"), within("public-trees")]);
    if (streets.length) {
      elements = JSON.parse(engine.cityElements(JSON.stringify(streets), JSON.stringify(buildings), JSON.stringify(trees)));
      source = "city";
      query = `City of Vancouver Open Data within ${radius} m: ${streets.length} streets, ${buildings.length} buildings, ${trees.length} trees`;
    }
  } catch (e) { elements = null; }
  if (!elements) {
    const ov = `[out:json][timeout:60];(way(around:${radius},${c[0].toFixed(6)},${c[1].toFixed(6)})["highway"];way(around:${radius},${c[0].toFixed(6)},${c[1].toFixed(6)})["building"];node(around:${radius},${c[0].toFixed(6)},${c[1].toFixed(6)})["natural"="tree"];);out tags geom;`;
    try {
      const r = await fetch("https://overpass-api.de/api/interpreter", { method: "POST", body: "data=" + encodeURIComponent(ov), headers: { "Content-Type": "application/x-www-form-urlencoded" } });
      if (r.ok) { elements = (await r.json()).elements || []; query = ov; }
    } catch (e) { elements = null; }
  }
  const res = JSON.parse(engine.lookupAssembleFrom(q.trim(), lat, lon, display, JSON.stringify(zoning), JSON.stringify(parcels), elements ? JSON.stringify(elements) : "", radius, query, source));
  if (!elements) res.site.notes += " The context could not be fetched in the browser; the plan draws a schematic context.";
  return res;
}

async function staticRun(body) {
  await loadEngine();
  let site = body.site, option = body.option;
  if (typeof site === "string") site = await fetchJSON(`data/sites/${site}.json`);
  if (typeof option === "string") option = await fetchJSON(`data/options/${option}.json`);
  const prev = body.previous_run ? await ledgerOf(body.previous_run) : null;
  const out = JSON.parse(engine.run(JSON.stringify(site), JSON.stringify(option), body.as_of || todayISO(), prev ? JSON.stringify(prev) : ""));
  const now = new Date();
  const folder = `browser-${now.toTimeString().slice(0, 8).replace(/:/g, "-")}`;
  const siteId = site.id || "site";
  const runId = `${siteId}/${folder}`;
  const L = out.ledger, ans = L.summary.answers;
  const payload = { run_id: runId, folder, folder_abs: null, as_of: L.run.as_of, stamp: L.run.stamp.stamp,
    ledger: L, massing: out.massing, svg: out.svg, diff: out.diff, proforma: out.proforma, layout: out.layout, sheets: out.sheets, massing_note: out.massing_note, revit: null, files: {}, in_browser: true,
    downloads: { html: blobUrl(out.memo_html, "text/html"), md: blobUrl(out.memo_md, "text/markdown"),
                 massing: out.massing ? blobUrl(JSON.stringify(out.massing, null, 2), "application/json") : null } };
  const summary = { run_id: runId, folder, folder_abs: null, as_of: L.run.as_of, stamp: L.run.stamp.stamp, option_id: L.run.option_id,
    option_name: (L.inputs.option || {}).name, written: now.toISOString().slice(0, 19),
    verdicts: { outright: ans.allowed.outright.verdict, by_rezoning: ans.allowed.by_rezoning.verdict, funded: ans.funded.verdict },
    has_diff: !!out.diff, has_massing: !!out.massing, revit: null };
  browserRuns.set(runId, { payload, summary });
  return payload;
}

async function staticApi(path, opts) {
  const u = new URL(path, "http://static.local/");
  const p = u.pathname, q = u.searchParams;
  const method = (opts.method || "GET").toUpperCase();
  const body = opts.body ? JSON.parse(opts.body) : null;
  let m;
  if (method === "GET") {
    if (p === "/api/rules") return fetchJSON("data/rules.json");
    // no server holds a key on the web; a person's own key, kept in this browser, calls the API from the page
    if (p === "/api/capabilities") return { claude: false, model: CLAUDE_MODEL, static: true, accepts_key: true, writes_rules: false };
    if (p === "/api/sites") return fetchJSON("data/sites.json");
    if ((m = p.match(/^\/api\/sites\/([^/]+)$/))) return fetchJSON(`data/sites/${decodeURIComponent(m[1])}.json`);
    if (p === "/api/options") {
      // only the asked site's options, as the local server answers (17 Nov 2026); pages.py writes each option's site
      const site = q.get("site") || "";
      const all = await fetchJSON("data/options.json");
      const ownerOf = o => o.site !== undefined ? o.site : (o.id === site || o.id.startsWith(site + "-") ? site : null);
      return all.filter(o => site && ownerOf(o) === site).map(o => ({ ...o, for_site: true })).sort((a, b) => a.id.localeCompare(b.id));
    }
    if ((m = p.match(/^\/api\/options\/([^/]+)$/))) return fetchJSON(`data/options/${decodeURIComponent(m[1])}.json`);
    if (p === "/api/runs") {
      const site = q.get("site");
      const mine = [...browserRuns.values()].map(r => r.summary).reverse();
      const all = await fetchJSON("data/runs.json");
      return mine.concat(all).filter(r => !site || r.run_id.startsWith(site + "/"));
    }
    if (p === "/api/diff") {
      const [a, b] = await Promise.all([ledgerOf(q.get("from")), ledgerOf(q.get("to"))]);
      await loadEngine();
      return { ...JSON.parse(engine.diff(JSON.stringify(a), JSON.stringify(b))), from_run: q.get("from"), to_run: q.get("to") };
    }
    if ((m = p.match(/^\/api\/runs\/([^/]+)\/([^/]+)$/))) return loadStaticRun(`${decodeURIComponent(m[1])}/${decodeURIComponent(m[2])}`);
    if ((m = p.match(/^\/api\/runs\/([^/]+)\/([^/]+)\/([^/]+)$/))) {
      const id = `${m[1]}/${m[2]}`;
      if (browserRuns.has(id)) throw new Error("A browser run keeps no files on disk.");
      return fetchJSON(`data/runs/${id}/${m[3]}`);
    }
    if (p === "/api/issues") return [];   // issues live beside the runs on the local server
    if (p === "/api/lookup") return staticLookup(q.get("q") || "");
    throw new Error(`The web version has no route for ${p}.`);
  }
  if (p === "/api/run") return staticRun(body);
  if (p === "/api/suggest") { await loadEngine(); return JSON.parse(engine.suggest(JSON.stringify(body.site), JSON.stringify(body.programs || []), body.as_of || todayISO(), body.candidate || "funder-ready", body.mix_shares ? JSON.stringify(body.mix_shares) : "", body.fixed ? JSON.stringify(body.fixed) : "")); }
  if (p === "/api/layout") { await loadEngine(); return JSON.parse(engine.layout(JSON.stringify(body.site), JSON.stringify(body.option), body.as_of || todayISO())); }
  if (p === "/api/read-site") { await loadEngine(); return JSON.parse(engine.readSite(JSON.stringify(body.site), body.as_of || todayISO())); }
  if (/^\/api\/runs\/[^/]+\/[^/]+\/issue$/.test(p)) throw new Error("Issuing a run to another reader needs the local server (python -m ffm ui).");
  if (p === "/api/options" || p === "/api/sites") { downloadJSON(body, `${body.id}.json`); return { id: body.id, file: `${body.id}.json`, downloaded: true }; }
  if (/^\/api\/runs\/[^/]+\/[^/]+\/memo$/.test(p)) return { revit: null };
  throw new Error(`The web version has no route for ${method} ${p}.`);
}

/* The model the page asks for when it calls Claude itself (claude.js, on the web); the web version's capabilities
   answer names it too. */
export const CLAUDE_MODEL = "claude-sonnet-5-5";
