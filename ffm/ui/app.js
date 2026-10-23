/* Funding-Fit Memo, the page. Vanilla JS, no build step.
   It formats what the engine wrote (ledger.json, massing.json); it never calculates a rule. */

"use strict";

// ---------------------------------------------------------------- small helpers

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function h(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

const STATUS_WORD = { pass: "Pass", conditional: "Conditional", fail: "Fail", uncertain: "Uncertain", not_applicable: "Not applicable", info: "Info" };
const VERDICT_OUTRIGHT = { no: "Not outright.", yes: "Allowed outright.", "yes, with conditions": "Outright, with conditions.", "not yet confirmed": "Outright: not yet confirmed." };

function pill(status) {
  return `<span class="pill pill-${h(status)}">${h(STATUS_WORD[status] || status)}</span>`;
}

/* A revision mark, the drafting way: a delta with its letter, beside whatever a comparison changed. */
const REV = `<svg class="rev" viewBox="0 0 16 14" aria-hidden="true"><path d="M8 1.2 15 12.8H1Z"/><text x="8" y="11.2" text-anchor="middle">A</text></svg><span class="sr-only">(revised)</span>`;

/* Scrolls follow the reader's motion setting. */
function scrollBehavior() { return reducedMotion() ? "auto" : "smooth"; }

function cap(s) { s = String(s || ""); return s.charAt(0).toUpperCase() + s.slice(1); }

/* The status a verdict word stands for, so a card can wear its colour. */
const VERDICT_STATUS = { no: "fail", yes: "pass", "yes, with conditions": "conditional", "not yet confirmed": "uncertain" };
function verdictStatus(word) { return VERDICT_STATUS[word] || ""; }

function fmtNum(x) {
  if (typeof x === "number") {
    if (Number.isInteger(x)) return x.toLocaleString("en-CA");
    return x.toLocaleString("en-CA", { maximumFractionDigits: 3 });
  }
  return String(x);
}

function fmtValues(v) {
  const bits = [];
  for (const [k, x] of Object.entries(v || {})) {
    if (x === null || x === undefined || typeof x === "object") continue;
    bits.push(`${k.replace(/_/g, " ")} = ${fmtNum(x)}`);
  }
  return bits.join("; ");
}

/* Lead sentence in ink, the rest in grey. */
function leadCont(text) {
  const t = String(text || "");
  const m = t.match(/^(.+?[.;:])\s+(.+)$/s);
  if (!m) return `<span class="lead">${h(t)}</span>`;
  return `<span class="lead">${h(m[1])}</span> <span class="cont">${h(m[2])}</span>`;
}

/* A finding that opens with the program's name already printed in its title ("BC Builds: fit cannot…" under
   "BC Builds: eligibility…") drops the repeat. */
function withoutRepeat(title, finding) {
  const m = String(finding || "").match(/^([^:;.]{3,60}):\s+(.+)$/s);
  if (!m || !String(title || "").toLowerCase().includes(m[1].toLowerCase())) return finding;
  return cap(m[2]);
}

function sourceLink(src) {
  if (!src || (!src.title && !src.url)) return "";
  const label = (src.title || src.url) + (src.section ? `, ${src.section}` : "");
  if (src.url) return `<a href="${h(src.url)}" target="_blank" rel="noopener">${h(label)}</a>`;
  return h(label);
}

/* Two backends, one call: the local Python server (python -m ffm ui), or, on a static host such as
   GitHub Pages where `python -m ffm pages` set window.FFM_STATIC, data files plus the engine itself
   running in the browser through Pyodide. Paths are relative so the page works under a sub-path. */
const STATIC = window.FFM_STATIC || null;

async function api(path, opts = {}) {
  if (STATIC) return staticApi(path, opts);
  const r = await fetch(path.replace(/^\//, ""), opts);
  let body = null;
  try { body = await r.json(); } catch (e) { body = null; }
  if (!r.ok) throw new Error((body && body.error) || `${r.status} ${r.statusText}`);
  return body;
}

async function postJSON(path, obj) {
  return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(obj) });
}

/* One line of feedback for every action, in the status strip under the steps: info, ok, error or busy. */
function setStatus(msg, kind = "info") {
  const s = $("#status");
  $("#status-text", s).textContent = msg;
  s.className = "strip " + (kind === "info" ? "" : kind);
}
function toast(msg, isError = false) { setStatus(msg, isError ? "error" : "ok"); }

function getPath(obj, path) {
  return path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), obj);
}

function setPath(obj, path, value) {
  const keys = path.split(".");
  let o = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    if (o[keys[i]] == null || typeof o[keys[i]] !== "object") o[keys[i]] = {};
    o = o[keys[i]];
  }
  o[keys[keys.length - 1]] = value;
}

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// ---------------------------------------------------------------- static backend (GitHub Pages): data files + the engine in Pyodide

const browserRuns = new Map();   // runs made in this tab: run_id -> {payload, summary}
let engine = null;               // {pyodide, run, diff} once loaded
let enginePromise = null;

function setEngineChip(text, kind) {
  const chip = $("#engine-chip");
  chip.hidden = false;
  chip.textContent = text;
  chip.className = "engine-chip " + (kind || "");
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src; s.async = true;
    s.onload = resolve;
    s.onerror = () => reject(new Error(`could not load ${src}`));
    document.head.appendChild(s);
  });
}

const ENGINE_SHIM = `
import json, sys
from datetime import date
sys.path.insert(0, ".")
from ffm import engine, massing, memo

def ffm_run(site_json, option_json, as_of, previous_json):
    site, option = json.loads(site_json), json.loads(option_json)
    L = engine.evaluate(site, option, date.fromisoformat(as_of))
    m = svg = note = None
    try:
        m = massing.build(site, option, L)
        svg = massing.svg(m)
    except ValueError as e:
        note = str(e)
    d = engine.diff(json.loads(previous_json), L) if previous_json else None
    md = memo.markdown(L, m, d)
    return json.dumps({"ledger": L, "massing": m, "svg": svg, "diff": d, "massing_note": note,
                       "memo_md": md, "memo_html": memo.html_page(md, svg)})

def ffm_diff(a_json, b_json):
    return json.dumps(engine.diff(json.loads(a_json), json.loads(b_json)))
`;

function loadEngine() {
  if (!STATIC) return Promise.resolve(null);
  if (enginePromise) return enginePromise;
  enginePromise = (async () => {
    setEngineChip("Loading the rules engine, about 10 MB, once", "loading");
    await loadScript(STATIC.pyodide_url);
    const pyodide = await window.loadPyodide({ indexURL: STATIC.pyodide_url.replace(/pyodide\.js(\?.*)?$/, "") });
    const files = await (await fetch("data/engine-files.json")).json();
    for (const f of files) {
      const r = await fetch(`engine/${f}`);
      if (!r.ok) throw new Error(`engine file ${f}: ${r.status}`);
      const dir = f.split("/").slice(0, -1).join("/");
      if (dir) pyodide.FS.mkdirTree(dir);
      pyodide.FS.writeFile(f, await r.text());
    }
    pyodide.runPython(ENGINE_SHIM);
    engine = { pyodide, run: pyodide.globals.get("ffm_run"), diff: pyodide.globals.get("ffm_diff") };
    setEngineChip(`Engine ready in your browser · Python ${pyodide.runPython("import sys; '%d.%d' % sys.version_info[:2]")}`, "ready");
    return engine;
  })().catch(e => {
    setEngineChip(`Engine did not load: ${e.message}. Past runs still open.`, "error");
    enginePromise = null;
    throw e;
  });
  return enginePromise;
}

async function fetchJSON(rel, optional = false) {
  const r = await fetch(rel, { cache: "no-cache" });
  if (!r.ok) { if (optional && r.status === 404) return null; throw new Error(`${r.status} for ${rel}`); }
  return r.json();
}

async function fetchText(rel, optional = false) {
  const r = await fetch(rel, { cache: "no-cache" });
  if (!r.ok) { if (optional && r.status === 404) return null; throw new Error(`${r.status} for ${rel}`); }
  return r.text();
}

function blobUrl(text, type) {
  return URL.createObjectURL(new Blob([text], { type }));
}

function downloadJSON(obj, name) {
  const a = document.createElement("a");
  a.href = blobUrl(JSON.stringify(obj, null, 2) + "\n", "application/json");
  a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
}

async function ledgerOf(runId) {
  if (browserRuns.has(runId)) return browserRuns.get(runId).payload.ledger;
  return fetchJSON(`data/runs/${runId}/ledger.json`);
}

async function loadStaticRun(runId) {
  if (browserRuns.has(runId)) return browserRuns.get(runId).payload;
  const [ledger, massing, svg, diff] = await Promise.all([
    fetchJSON(`data/runs/${runId}/ledger.json`), fetchJSON(`data/runs/${runId}/massing.json`, true),
    fetchText(`data/runs/${runId}/massing.svg`, true), fetchJSON(`data/runs/${runId}/diff.json`, true),
  ]);
  const base = `data/runs/${runId}`;
  return { run_id: runId, folder: runId.split("/")[1], folder_abs: null, as_of: ledger.run.as_of, stamp: ledger.run.stamp.stamp,
           ledger, massing, svg, diff, massing_note: null, revit: null, files: {},
           downloads: { html: `${base}/memo.html`, md: `${base}/memo.md`, massing: massing ? `${base}/massing.json` : null } };
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
    ledger: L, massing: out.massing, svg: out.svg, diff: out.diff, massing_note: out.massing_note, revit: null, files: {}, in_browser: true,
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
    if (p === "/api/sites") return fetchJSON("data/sites.json");
    if ((m = p.match(/^\/api\/sites\/([^/]+)$/))) return fetchJSON(`data/sites/${decodeURIComponent(m[1])}.json`);
    if (p === "/api/options") {
      const site = q.get("site") || "";
      const all = await fetchJSON("data/options.json");
      return all.map(o => ({ ...o, for_site: !!site && (o.id === site || o.id.startsWith(site + "-")) }))
                .sort((a, b) => (a.for_site === b.for_site ? a.id.localeCompare(b.id) : (a.for_site ? -1 : 1)));
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
    throw new Error(`The web version has no route for ${p}.`);
  }
  if (p === "/api/run") return staticRun(body);
  if (p === "/api/options" || p === "/api/sites") { downloadJSON(body, `${body.id}.json`); return { id: body.id, file: `${body.id}.json`, downloaded: true }; }
  if (/^\/api\/runs\/[^/]+\/[^/]+\/memo$/.test(p)) return { revit: null };
  throw new Error(`The web version has no route for ${method} ${p}.`);
}

// ---------------------------------------------------------------- state

const state = {
  sites: [], options: [], rules: [],
  siteId: null, optionId: null,
  site: null, option: null,
  siteDirty: false, optionDirty: false,
  run: null,            // the last /api/run response
  runs: [],             // past runs for the site
  compareRun: null,     // run_id to diff against on the next run
  step: 1,              // the step the reader is on, for the step bar
  revSeen: new Map(),   // rules stamp -> the earliest as-of date it was read on
  revisions: new Map(), // rules stamp -> "R1", "R2"…
};

const PRELOAD_SITE = "998-e-19th-ave";
const PRELOAD_OPTION = "998-e-19th-ave-as-approved";

// ---------------------------------------------------------------- form schemas

const TRI = "tri";

const SITE_FIELDS = [
  { group: "Identity", fields: [
    { key: "id", label: "Site id", type: "slug", help: "Letters, digits and hyphens; names the file and the outputs folder." },
    { key: "address", label: "Address", type: "text" },
    { key: "municipality", label: "Municipality", type: "text" },
    { key: "zoning_district", label: "Zoning district", type: "text", help: "As written in the by-law: RM-1, RS-1, RT-3, R1-1 …" },
  ]},
  { group: "Lot", fields: [
    { row: true, fields: [
      { key: "site_area_m2", label: "Area (m²)", type: "number" },
      { key: "frontage_m", label: "Frontage (m)", type: "number" },
      { key: "depth_m", label: "Depth (m)", type: "number" },
    ]},
  ]},
  { group: "Policy areas", fields: [
    { key: "in_former_community_vision_area", label: "In a former Community Vision area", type: TRI },
    { key: "in_transit_oriented_area", label: "In a transit-oriented area", type: TRI },
    { key: "toa_tier", label: "Transit-oriented area tier", type: "select", options: [["", "Not sure"], ["1", "Tier 1"], ["2", "Tier 2"], ["3", "Tier 3"]] },
    { key: "frequent_bus_stop_within_400m", label: "Frequent bus stop within 400 m", type: TRI },
    { key: "has_water_and_sewer", label: "Water and sewer service", type: TRI },
  ]},
  { group: "Trees", fields: [
    { key: "existing_trees_on_site", type: "trees" },
    { key: "street_trees.count", label: "Street trees (count)", type: "number", int: true },
  ]},
  { group: "Owner", fields: [
    { key: "owner", label: "Owner", type: "text" },
    { key: "owner_type", label: "Owner type", type: "text", help: "church, society, municipality, private …" },
    { key: "land_tenure_plan", label: "Land tenure plan", type: "text", help: "Write “to confirm” if it is not settled; the funders' checks read that honestly." },
    { key: "notes", label: "Notes", type: "textarea" },
  ]},
];

const OPTION_FIELDS = [
  { group: "Option", fields: [
    { key: "id", label: "Option id", type: "slug", help: "Start it with the site id so it lists under the site." },
    { key: "name", label: "Name", type: "text" },
    { key: "proponent", label: "Proponent", type: "text" },
    { key: "proponent_type", label: "Proponent type", type: "select", options: [
      ["non_profit_society", "Non-profit society"], ["housing_cooperative", "Housing co-operative"],
      ["municipal_housing_provider", "Municipal housing provider"], ["first_nation", "First Nation"],
      ["private", "Private"], ["other", "Other"]] },
    { key: "developer_partner", label: "Teamed with a developer or builder", type: TRI },
  ]},
  { group: "Building", fields: [
    { row: true, fields: [
      { key: "storeys", label: "Storeys", type: "number", int: true },
      { key: "height_m", label: "Height (m)", type: "number" },
      { key: "floor_to_floor_m", label: "Floor to floor (m)", type: "number" },
    ]},
    { row: true, fields: [
      { key: "gfa_m2", label: "GFA (m²)", type: "number" },
      { key: "residential_gfa_m2", label: "Residential GFA", type: "number" },
      { key: "non_residential_gfa_m2", label: "Non-residential GFA", type: "number" },
    ]},
    { row: true, label: "Setbacks (m)", fields: [
      { key: "setbacks_m.front", label: "Front", type: "number" },
      { key: "setbacks_m.rear", label: "Rear", type: "number" },
      { key: "setbacks_m.side", label: "Side", type: "number" },
    ]},
  ]},
  { group: "Units", fields: [
    { row: true, fields: [
      { key: "units.studio", label: "Studio", type: "number", int: true },
      { key: "units.one_bed", label: "1-bed", type: "number", int: true },
      { key: "units.two_bed", label: "2-bed", type: "number", int: true },
      { key: "units.three_bed_plus", label: "3-bed+", type: "number", int: true },
    ]},
    { type: "units-live" },
  ]},
  { group: "Tenure", fields: [
    { key: "tenure", label: "Tenure", type: "select", options: [["social_housing", "Social housing"], ["secured_market_rental", "Secured market rental"], ["other", "Other"]] },
    { row: true, fields: [
      { key: "share_below_hils", label: "Share below HILs", type: "number", share: true, help: "0.30 = 30%" },
      { key: "max_rent_share_of_income", label: "Max rent / income", type: "number", share: true, help: "0.30 = 30%" },
      { key: "housing_agreement_years", label: "Agreement (years)", type: "number", int: true },
    ]},
    { key: "owner_type_at_completion", label: "Owner at completion", type: "select", options: [
      ["", "Not sure"], ["non_profit_society", "Non-profit society"], ["housing_cooperative", "Housing co-operative"],
      ["city", "City"], ["province", "Province"], ["canada", "Canada"], ["private", "Private"]] },
  ]},
  { group: "Funding", fields: [
    { key: "target_programs", label: "Target programs", type: "programs" },
    { row: true, label: "Rent tiers (units)", fields: [
      { key: "rent_tiers_units.market", label: "Market", type: "number", int: true },
      { key: "rent_tiers_units.rgi", label: "RGI", type: "number", int: true },
      { key: "rent_tiers_units.deep_subsidy", label: "Deep subsidy", type: "number", int: true },
    ]},
    { row: true, fields: [
      { key: "accessible_units", label: "Accessible units", type: "number", int: true },
      { key: "below_market_unit_share", label: "Below-market share", type: "number", share: true, help: "of units, 0–1" },
      { key: "below_market_discount", label: "Discount to market", type: "number", share: true, help: "0.20 = 20%" },
    ]},
    { key: "site_control", label: "Site control", type: "select", options: [
      ["", "Not sure"], ["letter_of_intent", "Letter of intent"], ["purchase_agreement", "Purchase agreement"],
      ["council_resolution", "Council resolution"], ["finalized", "Finalized"], ["none", "None yet"]] },
    { key: "land_tenure_plan", label: "Land tenure plan", type: "text", help: "Leave blank to use the site's; write “to confirm” if unsettled." },
  ]},
  { group: "Trees", fields: [
    { key: "replacement_trees_proposed", label: "Replacement trees proposed", type: "number", int: true },
  ]},
  { group: "Rezoning path", fields: [
    { key: "rezoning_path", label: "Rezoning path", type: "text", help: "Empty means outright only." },
  ]},
  { group: "Notes", fields: [
    { key: "notes", label: "Notes", type: "textarea" },
  ]},
];

/* What each input is for. `need` says who reads it: "run" means the engine cannot build the memo and the massing
   without it; "rule" means a rule reads it and a blank comes back as "uncertain" (never guessed); "figure" means
   only the drawings use it; nothing means it is a note for people. `info` is the explanation behind the (i). */
const FIELD_META = {
  "id": { need: "run", info: "Names the file (sites/<id>.json or options/<id>.json) and the outputs folder. Letters, digits and hyphens." },
  "zoning_district": { need: "run", info: "The district schedule that applies without a rezoning, as the by-law writes it. The rule stack has outright limits for RM-1 and RM-1N (FSR 1.2, 10.7 m) and the SSMUH rule for R1-1, RS and RT; any other district, such as CD-1, gets 'not applicable' for those rules, so 'outright: yes' there means no coded limit was tested." },
  "site_area_m2": { need: "run", info: "Divides the option's floor area into an FSR, sets Schedule C's minimum tree count (2,551 to 2,900 m² needs 20 trees) and sizes the outright mass." },
  "frontage_m": { need: "run", info: "With the depth, the rectangle the massing is drawn in. For an irregular lot use the rectangle with the same area and say so in the notes; the FSR still uses the recorded area." },
  "depth_m": { need: "run", info: "With the frontage, the rectangle the massing is drawn in; the street is along the frontage, the lane behind the depth." },
  "in_former_community_vision_area": { need: "rule", info: "Map 1 of the Interim Rezoning Policy for Social Housing (1 Nov 2023, amended 31 Mar 2026). Inside the map, 100% social housing can rezone to CD-1 against a staff benchmark (here about 19.9 to 21.3 m and FSR 3.0). Outside it, the Affordable Housing Policies (1989) or an area plan apply and this rule reads 'not applicable'." },
  "in_transit_oriented_area": { need: "rule", info: "Bill 47 (2023): inside a provincially designated transit-oriented area the City may not refuse the minimum height and density for the tier. Vancouver designated 29 such areas in June 2024, around SkyTrain stations and bus exchanges. Check the City's TOA map; 'Not sure' comes back as uncertain." },
  "toa_tier": { need: "rule", info: "Distance bands around a SkyTrain station: Tier 1 within 200 m, minimum allowable 20 storeys; Tier 2 200 to 400 m, 12 storeys; Tier 3 400 to 800 m, 8 storeys. Bus-exchange areas use lower tiers the stack does not code yet. The tier comes from the City's TOA map, which the tool does not read." },
  "frequent_bus_stop_within_400m": { need: "", info: "Recorded for the record: no rule in the stack reads it yet. It will matter when frequent-transit policies are coded." },
  "has_water_and_sewer": { need: "rule", info: "The Small-Scale Multi-Unit Housing minimums (Bill 44) apply only where the lot has water and sewer service; 'No' switches that rule off." },
  "existing_trees_on_site": { need: "rule", info: "Protection of Trees By-law 9958. The survey must cover every tree of 20 cm DBH or more on the site, within 2 m of the boundary and on the adjoining street. Schedule A sets the protection barrier by trunk diameter (40 cm: 2.4 m, which the massing must leave clear); Schedule C sets how many trees the site must have after development, by area; each missing tree is $1,000 cash in lieu. No survey on file: the rule says so and returns uncertain." },
  "street_trees.count": { need: "figure", info: "Drawn along the frontage in the figures; no rule reads it." },
  "land_tenure_plan": { need: "rule", info: "Who will hold the land. The Community Housing Fund needs a lease of at least 60 years at nominal value, or ownership. Write 'to confirm' while it is unsettled: the check then returns uncertain instead of guessing. The option's own tenure plan overrides this one." },
  "owner_type": { need: "", info: "A note for the memo: church, society, municipality, private. The DCL exemption for church use is read from the referral report, not from this field." },
  "proponent_type": { need: "rule", info: "The Community Housing Fund takes non-profit societies, housing co-operatives, municipal housing providers and First Nations; private or other proponents fail that check. BC Builds takes any proponent that meets its below-market terms." },
  "developer_partner": { need: "rule", info: "BC Builds asks a non-profit to team with a developer or builder; a 'No' here fails that check for a non-profit." },
  "tenure": { need: "run", info: "Social housing, as the DCL By-law defines it, is exempt from development cost levies and community amenity contributions and rezones under the social housing policy. Secured market rental answers to the below-market rental policy instead (20% of floor area at 20% below the CMHC average)." },
  "storeys": { need: "run", info: "Tested against the transit-oriented minimum for the tier and the code basis (Part 9 up to three storeys and 600 m², Part 3 above). Storeys × floor to floor should land near the height; where the stated height is taller, the massing uses the stated height and says the extra is parapet or a taller ground floor." },
  "height_m": { need: "run", info: "Tested against the district's outright maximum (RM-1: 10.7 m) and, in a rezoning, the staff benchmark (here 19.9 to 21.3 m). Over the outright limit means a rezoning is needed; over the benchmark means a bigger ask of staff." },
  "floor_to_floor_m": { need: "figure", info: "Sizes the storeys in the section and the Revit floor plates. 3.0 to 3.3 m is usual for wood-frame residential." },
  "gfa_m2": { need: "run", info: "Gross floor area over all storeys. Divided by the site area it is the FSR, tested against the outright maximum (RM-1: 1.2) and the benchmark (about 3.0). The massing spreads it evenly over the storeys." },
  "residential_gfa_m2": { need: "rule", info: "With the non-residential area, BC Builds' cap of 30% non-residential floor area." },
  "non_residential_gfa_m2": { need: "rule", info: "Childcare, a hall, a church, shops. BC Builds caps non-residential space at 30% of the floor area." },
  "setbacks_m.front": { need: "figure", info: "Setbacks size the envelope the masses are drawn in; they are not read from the by-law here, so say in the notes when they are placeholders." },
  "setbacks_m.rear": { need: "figure", info: "The rear yard, usually the lane side; it also leaves room for the retained trees' barriers." },
  "setbacks_m.side": { need: "figure", info: "Applied on both sides; the envelope's width is the frontage less twice this." },
  "units.studio": { need: "rule", info: "The bedroom mix. In a rezoning at least 35% of units must have two or more bedrooms, and from 27 Oct 2026 at least 5% three or more. Leave the mix blank and the family-unit rule returns uncertain." },
  "units.one_bed": { need: "rule", info: "Counted toward the total; the family share is two-bedroom-plus over all units." },
  "units.two_bed": { need: "rule", info: "Counts as a family unit: at least 35% of units must have two or more bedrooms in a rezoning." },
  "units.three_bed_plus": { need: "rule", info: "Counts as a family unit, and from 27 Oct 2026 at least 5% of units must have three or more bedrooms." },
  "share_below_hils": { need: "rule", info: "Housing Income Limits are BC Housing's yearly income ceilings by unit size. The City's social housing definition needs at least 30% of the units for households below the HILs, at rents of at most 30% of income. 0.30 means 30%." },
  "max_rent_share_of_income": { need: "rule", info: "The rent ceiling for the HILs units: at most 30% of household income under the City's definition." },
  "housing_agreement_years": { need: "rule", info: "The City secures social housing by a housing agreement for the longer of 60 years and the life of the building; BC Builds' leases run 60 to 99 years." },
  "owner_type_at_completion": { need: "rule", info: "The social housing definition needs the building owned by a non-profit society, a housing co-operative, the City, the Province or Canada. A private owner fails it." },
  "target_programs": { need: "rule", info: "The funders whose fit decides the memo's second answer. Programs left unticked are still run and listed in the ledger as information." },
  "rent_tiers_units.market": { need: "rule", info: "The Community Housing Fund's mix: 30% of units at market-ish rents for low to moderate incomes (2025 limits $85,870 under two bedrooms, $138,770 two bedrooms and up), 50% rent-geared-to-income, 20% deep subsidy, each within 2 points. Blank tiers leave the fund's check uncertain." },
  "rent_tiers_units.rgi": { need: "rule", info: "Rent-geared-to-income units: 50% of the total under the Community Housing Fund's 30/50/20 mix." },
  "rent_tiers_units.deep_subsidy": { need: "rule", info: "Deep-subsidy (shelter-rate) units: 20% of the total under the Community Housing Fund's 30/50/20 mix." },
  "accessible_units": { need: "rule", info: "The Community Housing Fund needs at least 5% of units accessible (adaptable units are counted separately by the design guidelines)." },
  "below_market_unit_share": { need: "rule", info: "BC Builds: at least 20% of the units at least 20% below market rent; 1.0 means every unit. The City's below-market rental policy for secured market rental counts floor area instead." },
  "below_market_discount": { need: "rule", info: "The discount of those units to market: at least 20% for BC Builds (0.20)." },
  "site_control": { need: "rule", info: "Readiness for a funding call. The Community Housing Fund accepts a finalized deal, a purchase agreement, a letter of intent or a council resolution; 'none yet' fails the readiness bar. Construction must also be able to start within 18 months of an award." },
  "replacement_trees_proposed": { need: "rule", info: "Trees planted after construction. Retained plus replacement trees must reach Schedule C's minimum for the site area; each tree short is $1,000 cash in lieu." },
  "parking_spaces": { need: "", info: "No minimum off-street parking applies in Vancouver since June 2024; the count is reported as information. Bicycle spaces are set by the Parking By-law at the development permit stage." },
  "bicycle_spaces": { need: "", info: "Reported as information; the Parking By-law sets the minimum at the development permit stage." },
  "rezoning_path": { need: "rule", info: "Blank means the option must fit outright. Name a path (CD-1 under the Interim Rezoning Policy for Social Housing, an ODP amendment) and the memo answers 'by rezoning' through that policy; the outright rules then read as the ask, not as a fail." },
  "proponent": { need: "", info: "The society, co-operative or body that will own and run the housing; printed in the memo's title block." },
  "name": { need: "", info: "How the option is listed and printed; say when it is hypothetical." },
  "address": { need: "", info: "Printed as the memo's title; python -m ffm context geocodes it to draw the surroundings." },
  "municipality": { need: "", info: "A note: the rule stack is written for the City of Vancouver." },
  "owner": { need: "", info: "Printed in the memo's inputs." },
  "notes": { need: "", info: "Placeholders, assumptions and what still needs checking. The memo prints them." },
};

const NEED_WORD = { run: "needed to run", rule: "read by a rule; blank means uncertain", figure: "drawings only" };

/* The label of a field: its text, the mark that says who reads it, and the (i) that opens the explanation. */
function labelHtml(f, id, opts = {}) {
  const meta = FIELD_META[f.key] || {};
  const need = meta.need || "";
  const tag = opts.tag || "label";
  const attrs = tag === "label" ? ` for="${id}"` : ` id="${id}-label"`;
  const mark = need ? `<i class="need need-${need}" title="${h(NEED_WORD[need])}" aria-hidden="true"></i><span class="sr-only">(${h(NEED_WORD[need])})</span>` : "";
  const text = opts.hideLabel ? `<span class="sr-only">${h(f.label)}</span>` : h(f.label);
  const info = meta.info ? `<button type="button" class="info-btn" aria-label="About ${h(f.label)}" aria-expanded="false" data-info="${h(meta.info)}">i</button>` : "";
  return `<span class="label-line"><${tag}${attrs} class="${opts.hideLabel ? "sr-only" : ""}">${mark}${text}</${tag}>${info}</span>`;
}

// ---------------------------------------------------------------- form rendering

function renderForm(formEl, schema, obj, onChange) {
  formEl.innerHTML = "";
  const legend = document.createElement("p");
  legend.className = "need-legend";
  formEl.appendChild(legend);
  for (const group of schema) {
    const g = document.createElement("div");
    g.className = "group";
    g.innerHTML = `<div class="eyebrow">${h(group.group)}</div>`;
    // a group of one field named like the group ("Notes / Notes") shows the name once; the label stays for screen readers
    const single = group.fields.length === 1 && group.fields[0].label === group.group;
    for (const f of group.fields) g.appendChild(renderField(single ? { ...f, hideLabel: true } : f, obj, onChange));
    formEl.appendChild(g);
  }
  refreshNeeds(formEl, schema, obj);
}

/* The legend over a form: how many of the needed fields and of the rule-read fields are filled in. */
function refreshNeeds(formEl, schema, obj) {
  const legend = $(".need-legend", formEl);
  if (!legend) return;
  const counts = { run: [0, 0], rule: [0, 0] };
  const walk = fields => {
    for (const f of fields) {
      if (f.row) { walk(f.fields); continue; }
      const need = (FIELD_META[f.key] || {}).need;
      if (!need || !counts[need]) continue;
      const v = getPath(obj, f.key);
      const filled = Array.isArray(v) ? v.length > 0 : (f.type === TRI ? v === true || v === false : v !== null && v !== undefined && v !== "");
      counts[need][1]++;
      if (filled) counts[need][0]++;
    }
  };
  for (const g of schema) walk(g.fields);
  const [r0, r1] = counts.run, [u0, u1] = counts.rule;
  legend.innerHTML = `<span><i class="need need-run" aria-hidden="true"></i> needed to run: <b>${r0} of ${r1}</b></span>
    <span><i class="need need-rule" aria-hidden="true"></i> read by a rule: <b>${u0} of ${u1}</b>${u0 < u1 ? ` <span class="cont">(a blank comes back as uncertain)</span>` : ""}</span>
    <span><i class="need need-figure" aria-hidden="true"></i> drawings only</span>`;
}

/* The (i) beside a label opens a small note floating over the page, beside the button, so nothing below it moves.
   Any click, a scroll, Esc or the same (i) closes it. */
function closeInfo() {
  $$(".pop").forEach(p => p.remove());
  $$(".info-btn[aria-expanded='true']").forEach(b => b.setAttribute("aria-expanded", "false"));
}
function openInfo(btn) {
  const pop = document.createElement("div");
  pop.className = "pop";
  pop.setAttribute("role", "note");
  pop.innerHTML = `<p>${h(btn.dataset.info)}</p>`;
  document.body.appendChild(pop);
  const r = btn.getBoundingClientRect(), w = Math.min(300, window.innerWidth - 24);
  pop.style.width = `${w}px`;
  // to the right of the (i) when there is room, else under it; never past the window's edges
  let left = r.right + 8, top = r.top - 6;
  if (left + w > window.innerWidth - 12) { left = Math.max(12, Math.min(r.left, window.innerWidth - w - 12)); top = r.bottom + 6; }
  const ph = pop.offsetHeight;
  if (top + ph > window.innerHeight - 12) top = Math.max(12, window.innerHeight - ph - 12);
  pop.style.left = `${left}px`;
  pop.style.top = `${top}px`;
  btn.setAttribute("aria-expanded", "true");
}
document.addEventListener("click", e => {
  const btn = e.target.closest(".info-btn");
  const open = btn && btn.getAttribute("aria-expanded") === "true";
  closeInfo();
  if (btn && !open) openInfo(btn);
});
document.addEventListener("keydown", e => { if (e.key === "Escape" && $(".pop")) closeInfo(); });
window.addEventListener("scroll", () => { if ($(".pop")) closeInfo(); }, { capture: true, passive: true });

function renderField(f, obj, onChange) {
  if (f.row) {
    const wrap = document.createElement("div");
    if (f.label) wrap.innerHTML = `<div class="field"><span class="label">${h(f.label)}</span></div>`;
    if (f.label) { const first = f.fields[0]; const m = FIELD_META[first.key]; if (m && m.need) $(".label", wrap).insertAdjacentHTML("afterbegin", `<i class="need need-${m.need}" title="${h(NEED_WORD[m.need])}" aria-hidden="true"></i>`); }
    const row = document.createElement("div");
    row.className = "field-row";
    for (const sub of f.fields) row.appendChild(renderField(sub, obj, onChange));
    wrap.appendChild(row);
    return wrap;
  }
  const el = document.createElement("div");
  el.className = "field";
  const id = "f-" + (f.key || f.type).replace(/\W/g, "-") + "-" + Math.random().toString(36).slice(2, 7);
  const value = f.key ? getPath(obj, f.key) : undefined;

  if (f.type === "units-live") {
    el.className = "live";
    el.dataset.live = "units";
    el.innerHTML = unitsLive(obj);
    return el;
  }
  if (f.type === TRI) {
    el.innerHTML = labelHtml(f, id, { tag: "span" });
    $("span[id]", el).classList.add("label");
    const tri = document.createElement("div");
    tri.className = "tri";
    tri.setAttribute("role", "radiogroup");
    tri.setAttribute("aria-labelledby", `${id}-label`);
    // a radio group: one tab stop on the chosen answer, the arrow keys move the choice
    const choices = [[true, "Yes"], [false, "No"], [null, "Not sure"]];
    const current = value === undefined ? null : value;
    const buttons = [];
    const choose = (i, focus) => {
      setPath(obj, f.key, choices[i][0]);
      buttons.forEach((x, k) => { x.setAttribute("aria-checked", String(k === i)); x.tabIndex = k === i ? 0 : -1; });
      if (focus) buttons[i].focus();
      onChange(f.key);
    };
    choices.forEach(([v, lab], i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = lab;
      b.className = v === null ? "unsure" : "";
      b.setAttribute("role", "radio");
      b.setAttribute("aria-checked", String(current === v));
      b.tabIndex = current === v ? 0 : -1;
      b.addEventListener("click", () => choose(i, false));
      b.addEventListener("keydown", e => {
        const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
        if (!step) return;
        e.preventDefault();
        choose((i + step + choices.length) % choices.length, true);
      });
      buttons.push(b);
      tri.appendChild(b);
    });
    if (!buttons.some(b => b.tabIndex === 0)) buttons[2].tabIndex = 0;
    el.appendChild(tri);
    return el;
  }
  if (f.type === "select") {
    const opts = f.options.map(([v, lab]) => `<option value="${h(v)}"${String(value ?? "") === String(v) ? " selected" : ""}>${h(lab)}</option>`).join("");
    el.innerHTML = `${labelHtml(f, id)}<select id="${id}">${opts}</select>${f.help ? `<span class="help">${h(f.help)}</span>` : ""}`;
    $("select", el).addEventListener("change", e => { setPath(obj, f.key, e.target.value === "" ? null : e.target.value); onChange(f.key); });
    return el;
  }
  if (f.type === "textarea") {
    el.innerHTML = `${labelHtml(f, id, { hideLabel: f.hideLabel })}<textarea id="${id}">${h(value ?? "")}</textarea>`;
    $("textarea", el).addEventListener("input", e => { setPath(obj, f.key, e.target.value || null); onChange(f.key); });
    return el;
  }
  if (f.type === "programs") {
    el.innerHTML = labelHtml(f, id, { tag: "span" });
    $("span[id]", el).classList.add("label");
    const box = document.createElement("div");
    box.className = "checks";
    const chosen = new Set(Array.isArray(value) ? value : []);
    const programs = state.rules.filter(r => r.layer === "E");
    if (!programs.length) box.innerHTML = `<span class="help">Rules not loaded.</span>`;
    for (const r of programs) {
      const lab = document.createElement("label");
      lab.innerHTML = `<input type="checkbox" value="${h(r.id)}"${chosen.has(r.id) ? " checked" : ""}> <span>${h(r.title)} <code>${h(r.id)}</code></span>`;
      $("input", lab).addEventListener("change", () => {
        const now = $$("input:checked", box).map(x => x.value);
        setPath(obj, f.key, now);
        onChange(f.key);
      });
      box.appendChild(lab);
    }
    el.appendChild(box);
    el.insertAdjacentHTML("beforeend", `<span class="help">Unticked programs are still listed in the ledger; only ticked ones decide the funders' answer.</span>`);
    return el;
  }
  if (f.type === "trees") {
    el.innerHTML = labelHtml({ ...f, label: "Existing trees on site" }, id, { tag: "span" });
    $("span[id]", el).classList.add("label");
    const list = document.createElement("div");
    list.className = "trees";
    const trees = Array.isArray(value) ? value : [];
    if (!Array.isArray(value)) setPath(obj, f.key, trees);
    const draw = () => {
      list.innerHTML = trees.length ? `<div class="tree-row tree-head"><span>id</span><span>species</span><span>DBH cm</span><span>plan</span><span></span></div>` : `<span class="help">No tree survey on file: the trees rule will say so.</span>`;
      trees.forEach((t, i) => {
        const row = document.createElement("div");
        row.className = "tree-row";
        row.innerHTML = `<input type="text" value="${h(t.id ?? "")}" aria-label="Tree id">
          <input type="text" value="${h(t.species ?? "")}" aria-label="Species" placeholder="species">
          <input type="number" step="any" value="${t.dbh_cm ?? ""}" aria-label="DBH in cm" placeholder="DBH">
          <select aria-label="Retain or remove"><option value="retain"${t.status === "retain" ? " selected" : ""}>retain</option><option value="remove"${t.status === "remove" ? " selected" : ""}>remove</option></select>
          <button type="button" class="x" title="Remove this tree" aria-label="Remove tree ${h(t.id || i + 1)}">×</button>`;
        const [idIn, spIn, dbhIn] = $$("input", row);
        idIn.addEventListener("input", e => { t.id = e.target.value || null; onChange(f.key); });
        spIn.addEventListener("input", e => { t.species = e.target.value || null; onChange(f.key); });
        dbhIn.addEventListener("input", e => { t.dbh_cm = e.target.value === "" ? null : Number(e.target.value); onChange(f.key); });
        $("select", row).addEventListener("change", e => { t.status = e.target.value; onChange(f.key); });
        $(".x", row).addEventListener("click", () => { trees.splice(i, 1); draw(); onChange(f.key); });
        list.appendChild(row);
      });
      const add = document.createElement("button");
      add.type = "button";
      add.className = "btn btn-quiet btn-small";
      add.textContent = "+ Add a tree";
      add.addEventListener("click", () => { trees.push({ id: "T" + (trees.length + 1), species: null, dbh_cm: null, status: "retain" }); draw(); onChange(f.key); });
      list.appendChild(add);
    };
    draw();
    el.appendChild(list);
    return el;
  }
  // text, slug, number. A blank number is read as "not sure", and the empty field says so.
  const isNum = f.type === "number";
  const warnId = `${id}-warn`;
  el.innerHTML = `${labelHtml(f, id, { hideLabel: f.hideLabel })}
    <input id="${id}" type="${isNum ? "number" : "text"}"${isNum ? ` step="${f.int ? "1" : "any"}" placeholder="not sure"` : ""}${f.share ? ` min="0" max="1" aria-describedby="${warnId}"` : ""} value="${h(value ?? "")}">
    ${f.help ? `<span class="help">${h(f.help)}</span>` : ""}
    ${f.share ? `<span class="help warn" id="${warnId}" hidden>Write a share as a decimal: 0.30 for 30%.</span>` : ""}`;
  const warn = f.share ? $(".warn", el) : null;
  const checkShare = v => { if (warn) warn.hidden = !(typeof v === "number" && v > 1); };
  checkShare(value);
  $("input", el).addEventListener("input", e => {
    let v = e.target.value;
    if (isNum) v = v === "" ? null : Number(v);
    else if (f.type === "slug") v = v.trim().toLowerCase().replace(/[^a-z0-9._-]+/g, "-") || null;
    else v = v === "" ? null : v;
    checkShare(v);
    setPath(obj, f.key, v);
    onChange(f.key);
  });
  return el;
}

function unitsLive(option) {
  const u = (option && option.units) || {};
  const n = k => Number(u[k]) || 0;
  const total = n("studio") + n("one_bed") + n("two_bed") + n("three_bed_plus");
  const fam = n("two_bed") + n("three_bed_plus");
  if (!total) return `total <b>0</b> units`;
  return `total <b>${total}</b> units · two-bed or more <b>${fam}</b> (<b>${(100 * fam / total).toFixed(1)}%</b>) · three-bed or more <b>${n("three_bed_plus")}</b> (<b>${(100 * n("three_bed_plus") / total).toFixed(1)}%</b>)`;
}

/* How many three-state answers in a form are "not sure" (null), for the card's one-line summary. */
function countUnsure(obj, schema) {
  let n = 0;
  const walk = fields => { for (const f of fields) { if (f.row) walk(f.fields); else if (f.type === TRI && getPath(obj, f.key) == null) n++; } };
  for (const g of schema) walk(g.fields);
  return n;
}

function unsureNote(n) { return n ? ` · <span class="unsure-n">${n} answer${n === 1 ? "" : "s"} not sure</span>` : ""; }

function siteSummary(s) {
  if (!s) return "";
  const dims = s.frontage_m != null && s.depth_m != null ? ` · ${h(s.frontage_m)} × ${h(s.depth_m)} m` : "";
  return `<b>${h(s.address || s.id || "A new site")}</b> · ${h(s.zoning_district || "district not set")} · ${s.site_area_m2 != null ? `${h(fmtNum(s.site_area_m2))} m²` : "area not set"}${dims}${unsureNote(countUnsure(s, SITE_FIELDS))}`;
}

function optionSummary(o) {
  if (!o) return "";
  const u = o.units || {};
  const total = ["studio", "one_bed", "two_bed", "three_bed_plus"].reduce((t, k) => t + (Number(u[k]) || 0), 0);
  const bits = [];
  if (o.storeys != null) bits.push(`${h(o.storeys)} storeys`);
  if (o.height_m != null) bits.push(`${h(o.height_m)} m`);
  if (o.gfa_m2 != null) bits.push(`${h(fmtNum(o.gfa_m2))} m² GFA`);
  if (total) bits.push(`${total} units`);
  if (o.tenure) bits.push(h(String(o.tenure).replace(/_/g, " ")));
  return `<b>${h(o.name || o.id || "A new option")}</b>${bits.length ? ` · ${bits.join(" · ")}` : ""}${unsureNote(countUnsure(o, OPTION_FIELDS))}`;
}

/* An input card collapses to its file and a summary once a file is chosen, so the memo leads; Edit opens the form. */
function setCollapsed(kind, collapsed) {
  const card = $(`#step-${kind}`), btn = $(`#edit-${kind}`);
  card.classList.toggle("collapsed", collapsed);
  btn.textContent = collapsed ? "Edit" : "Done";
  btn.setAttribute("aria-expanded", String(!collapsed));
  btn.setAttribute("aria-label", collapsed ? `Edit the ${kind}` : `Close the ${kind} form`);
}

function refreshSummary(kind) {
  $(`#${kind}-summary`).innerHTML = kind === "site" ? siteSummary(state.site) : optionSummary(state.option);
}

/* rent_tiers_units: all three blank means "not stated" (null), which the engine reads as unsure. */
function tidyOption(opt) {
  const t = opt.rent_tiers_units;
  if (t && typeof t === "object" && ["market", "rgi", "deep_subsidy"].every(k => t[k] == null)) opt.rent_tiers_units = null;
  if (opt.setbacks_m && typeof opt.setbacks_m === "object") {
    for (const k of ["front", "rear", "side"]) if (opt.setbacks_m[k] == null) opt.setbacks_m[k] = 0;
  }
  return opt;
}

// ---------------------------------------------------------------- site and option loading

function fillSelect(sel, items, current, extraLabel) {
  sel.innerHTML = "";
  for (const it of items) {
    const o = document.createElement("option");
    o.value = it.value; o.textContent = it.label;
    if (it.group) o.dataset.group = it.group;
    sel.appendChild(o);
  }
  const n = document.createElement("option");
  n.value = "__new__"; n.textContent = extraLabel;
  sel.appendChild(n);
  sel.value = current ?? "";
}

function blankSite() {
  return { id: null, address: null, municipality: "City of Vancouver", zoning_district: null, site_area_m2: null, frontage_m: null, depth_m: null,
    in_former_community_vision_area: null, in_transit_oriented_area: null, toa_tier: null, frequent_bus_stop_within_400m: null,
    has_water_and_sewer: null, owner_type: null, owner: null, land_tenure_plan: null, existing_trees_on_site: [], street_trees: { count: null }, notes: null, sources: [] };
}

function blankOption(siteId) {
  return { id: siteId ? `${siteId}-option` : null, name: null, proponent: null, proponent_type: "non_profit_society", developer_partner: null,
    tenure: "social_housing", rezoning_path: null, storeys: null, height_m: null, gfa_m2: null, residential_gfa_m2: null, non_residential_gfa_m2: null,
    units: { studio: null, one_bed: null, two_bed: null, three_bed_plus: null }, rent_tiers_units: null, share_below_hils: null, max_rent_share_of_income: null,
    owner_type_at_completion: null, housing_agreement_years: null, accessible_units: null, below_market_unit_share: null, below_market_discount: null,
    site_control: null, parking_spaces: null, bicycle_spaces: null, replacement_trees_proposed: null,
    target_programs: state.rules.filter(r => r.layer === "E" && /chf|bcbuilds/.test(r.id)).map(r => r.id),
    floor_to_floor_m: 3.0, setbacks_m: { front: 0, rear: 0, side: 0 }, notes: null, sources: [] };
}

async function loadSites() {
  state.sites = await api("/api/sites");
  fillSelect($("#site-select"), state.sites.map(s => ({ value: s.id, label: `${s.address || s.id} · ${s.zoning_district || "?"}` })), state.siteId, "New site…");
}

async function selectSite(id) {
  if (id === "__new__") {
    state.siteId = null;
    state.site = blankSite();
    state.siteDirty = true;
  } else {
    state.siteId = id;
    state.site = await api(`/api/sites/${encodeURIComponent(id)}`);
    state.siteDirty = false;
  }
  renderForm($("#site-form"), SITE_FIELDS, state.site, onSiteChange);
  $("#site-dirty").hidden = !state.siteDirty;
  refreshSummary("site");
  setCollapsed("site", id !== "__new__");
  await loadOptions();
  await loadRuns();
  fillRunSelects();
  setStep(state.step);
}

function onSiteChange() {
  state.siteDirty = true;
  $("#site-dirty").hidden = false;
  refreshSummary("site");
  refreshNeeds($("#site-form"), SITE_FIELDS, state.site);
}

async function loadOptions() {
  const sid = state.siteId || (state.site && state.site.id) || "";
  state.options = await api(`/api/options?site=${encodeURIComponent(sid)}`);
  const forSite = state.options.filter(o => o.for_site);
  const others = state.options.filter(o => !o.for_site);
  const items = forSite.map(o => ({ value: o.id, label: o.name })).concat(others.map(o => ({ value: o.id, label: `(other site) ${o.name}` })));
  const current = (state.optionId && state.options.some(o => o.id === state.optionId)) ? state.optionId : (forSite[0] ? forSite[0].id : "__new__");
  fillSelect($("#option-select"), items, current, "New option…");
  await selectOption(current);
}

async function selectOption(id) {
  if (id === "__new__") {
    state.optionId = null;
    state.option = blankOption(state.site && state.site.id);
    state.optionDirty = true;
  } else {
    state.optionId = id;
    state.option = await api(`/api/options/${encodeURIComponent(id)}`);
    state.optionDirty = false;
  }
  renderForm($("#option-form"), OPTION_FIELDS, state.option, onOptionChange);
  $("#option-dirty").hidden = !state.optionDirty;
  refreshSummary("option");
  setCollapsed("option", id !== "__new__");
  renderQuiet();
  setStep(state.step);
}

function onOptionChange(key) {
  state.optionDirty = true;
  $("#option-dirty").hidden = false;
  refreshSummary("option");
  refreshNeeds($("#option-form"), OPTION_FIELDS, state.option);
  if (key && key.startsWith("units.")) {
    const live = $('[data-live="units"]');
    if (live) live.innerHTML = unitsLive(state.option);
  }
}

async function saveAs(kind) {
  const obj = kind === "site" ? state.site : tidyOption(state.option);
  const current = obj.id || "";
  const id = prompt(`Save this ${kind} as ${kind}s/<id>.json. Id:`, current);
  if (!id) return;
  const clean = id.trim().toLowerCase().replace(/[^a-z0-9._-]+/g, "-");
  const body = Object.assign({}, obj, { id: clean });
  if (kind === "option" && !body.name) body.name = prompt("A name for the option:", clean) || clean;
  try {
    const r = await postJSON(kind === "site" ? "/api/sites" : "/api/options", body);
    if (r.downloaded) {
      obj.id = clean;
      toast(`Downloaded ${r.file}. Put it in the ${kind}s/ folder of the repository to keep it.`);
      return;
    }
    toast(`Saved ${kind}s/${r.file}`);
    obj.id = clean;
    if (kind === "site") {
      state.siteDirty = false; $("#site-dirty").hidden = true;
      await loadSites(); state.siteId = clean; $("#site-select").value = clean;
      renderForm($("#site-form"), SITE_FIELDS, state.site, onSiteChange);
    } else {
      state.optionDirty = false; $("#option-dirty").hidden = true;
      state.optionId = clean;
      const sid = state.siteId || (state.site && state.site.id) || "";
      state.options = await api(`/api/options?site=${encodeURIComponent(sid)}`);
      const forSite = state.options.filter(o => o.for_site), others = state.options.filter(o => !o.for_site);
      fillSelect($("#option-select"), forSite.map(o => ({ value: o.id, label: o.name })).concat(others.map(o => ({ value: o.id, label: `(other site) ${o.name}` }))), clean, "New option…");
      renderForm($("#option-form"), OPTION_FIELDS, state.option, onOptionChange);
    }
  } catch (e) {
    toast(e.message, true);
  }
}

// ---------------------------------------------------------------- runs

async function loadRuns() {
  const sid = state.siteId || (state.site && state.site.id);
  state.runs = sid ? await api(`/api/runs?site=${encodeURIComponent(sid)}`) : [];
  noteRevisions(state.runs);
}

/* The rules' revisions. A memo's stamp is a hash of the rule files and the versions in force on its as-of date;
   the reader sees it as R1, R2 and so on: the distinct stamps on file, across every site, numbered by the earliest
   date each was read on (ties by the stamp itself, so every machine numbers them alike). The hash itself stays in
   the Rules revision card at the foot of the memo, and in the Revit elements' Comments. */
async function loadRevisions() {
  const lists = await Promise.all((state.sites || []).map(s => api(`/api/runs?site=${encodeURIComponent(s.id)}`).catch(() => [])));
  noteRevisions(lists.flat());
}

function noteRevisions(runs) {
  for (const r of runs || []) {
    if (!r || !r.stamp) continue;
    const seen = state.revSeen.get(r.stamp);
    if (!seen || (r.as_of && r.as_of < seen)) state.revSeen.set(r.stamp, r.as_of || "9999");
  }
  const order = [...state.revSeen.entries()].sort((a, b) => a[1].localeCompare(b[1]) || a[0].localeCompare(b[0]));
  state.revisions = new Map(order.map(([stamp], i) => [stamp, `R${i + 1}`]));
}

/* A rules stamp as the reader sees it: its revision number. */
const rev = stamp => (stamp && state.revisions.get(stamp)) || "an unlisted revision";

async function runRules() {
  const btn = $("#run-btn");
  if (!state.site || !state.option) return;
  btn.classList.add("busy");
  btn.textContent = "Running…";
  setStatus("Running the rules…", "busy");
  try {
    if (STATIC && !engine) { btn.textContent = "Loading the engine…"; setStatus("Loading the rules engine in your browser…", "busy"); await loadEngine(); btn.textContent = "Running…"; }
    const body = { site: state.site, option: tidyOption(state.option), as_of: $("#as-of").value || todayISO(), previous_run: state.compareRun || null };
    const t0 = performance.now();
    const run = await postJSON("/api/run", body);
    state.run = run;
    noteRevisions([run]);
    await attachCause(run);
    renderMemo(run);
    showStamp(run.stamp);
    enableExports(run);
    setStep(3);
    closeExportPanel();
    await loadRuns();
    fillRunSelects();
    setCompareNote(run.diff);
    const ms = Math.round(performance.now() - t0);
    toast(`Ran the rules as of ${run.as_of} (${rev(run.stamp)}) in ${ms} ms · ${run.in_browser ? "kept in this browser tab" : `wrote outputs/${run.run_id}/`}${run.diff ? ` · ${compareSummary(run)}` : ""}`);
    $("#step-run").scrollIntoView({ behavior: scrollBehavior(), block: "start" });
  } catch (e) {
    toast(e.message, true);
  } finally {
    btn.classList.remove("busy");
    btn.textContent = "Run the rules";
  }
}

/* The top bar names the memo's rules revision, R1, R2…; the stamp behind it is in the memo's Rules revision card. */
function showStamp(stamp) {
  $("#stamp-text").textContent = stamp ? rev(stamp) : "";
  $("#stamp-box").hidden = !stamp;
}

function enableExports(run) {
  const on = !!run;
  const base = run ? `api/runs/${run.run_id}` : "";
  const urls = on ? (run.downloads || { html: `${base}/memo.html?download=1`, md: `${base}/memo.md?download=1`, massing: run.massing ? `${base}/massing.json?download=1` : null }) : {};
  const stem = run ? run.run_id.replace("/", "_") : "memo";
  // a disabled download has no href, so it is neither clickable nor in the tab order
  const set = (sel, key, name) => {
    const a = $(sel);
    const ok = on && !!urls[key];
    if (ok) a.href = urls[key]; else a.removeAttribute("href");
    a.setAttribute("download", name);
    a.setAttribute("aria-disabled", String(!ok));
  };
  set("#dl-html", "html", `${stem}_memo.html`);
  set("#dl-md", "md", `${stem}_memo.md`);
  set("#dl-massing", "massing", `${stem}_massing.json`);
  $("#print-btn").disabled = !on;
  $("#revit-btn").disabled = !(on && run.massing);
}

// ---------------------------------------------------------------- the memo

function renderQuiet() {
  if (state.run) return;  // a run is on screen: leave it
  const site = state.site || {}, opt = state.option || {};
  const n = state.rules.length;
  placeRunTools(false);
  $("#memo").className = "memo";
  $("#memo").innerHTML = `
    <div class="card memo-head">
      <h1>${h(site.address || site.id || "A site")}</h1>
      <div class="memo-meta">
        <div><b>Option</b><span>${h(opt.name || opt.id || "—")}</span></div>
        <div><b>Proponent</b><span>${h(opt.proponent || "—")}</span></div>
        <div><b>Rules as of</b><span>${h($("#as-of").value || todayISO())}</span></div>
      </div>
      <p class="quiet">Run the rules evaluates this site and option against the ${n || "dated"} rules in force on that date, ${STATIC ? "in your browser, with nothing uploaded, and keeps the memo in this tab" : "writes the memo to <code>outputs/</code>"}, and reads it here: three answers first, then the massing and the full ledger.</p>
    </div>
    <div class="answers">
      ${quietCard("01 · Is it allowed", "Is it allowed?", "Outright under the district, then by rezoning under the City policy that applies.")}
      ${quietCard("02 · Does it fit the funders", "Does it fit the funders?", "The programs the option targets, tested against their published criteria.")}
      ${quietCard("03 · Still unsure", "What is still unsure, and who resolves it?", "Every open item names the person and the document.")}
    </div>`;
}

function quietCard(eyebrow, title, line) {
  const n = String(eyebrow).trim().charAt(1);   // "01 · …" → 1
  return `<section class="card answer">
    <h2><span class="badge">${h(n)}</span> ${h(title)}</h2>
    <p class="verdict quiet">${h(line)}</p>
  </section>`;
}

function renderMemo(run) {
  const L = run.ledger, res = L.results, ans = L.summary.answers;
  const site = L.inputs.site, opt = L.inputs.option;
  const parts = [];

  // 1. header: the memo's title block. A comparison adds a cell: Revision (with the delta) when the rules moved, or
  // Compared with when two options are read under the same rules
  const d = run.diff;
  const kind = d ? compareKind(d) : null;
  const B = d && run.compareLedger ? run.compareLedger : null;
  const cmpCell = !d ? "" : kind === "rules"
    ? `<div class="rev-cell"><b>Revised from</b><span>${REV} ${h(rev(d.previous_stamp))} <span class="cont">(rules as of ${h(d.previous_as_of)})</span></span></div>`
    : `<div><b>Compared with</b><span>${B ? h(optionName(B)) : "a run"} <span class="cont">(as of ${h(d.previous_as_of)})</span></span></div>`;
  parts.push(`<div class="card memo-head">
    <h1>${h(site.address || site.id)}</h1>
    <div class="memo-meta">
      <div><b>Option</b><span>${h(opt.name || opt.id)}</span></div>
      <div><b>Proponent</b><span>${h(opt.proponent || "—")}${opt.proponent_type ? ` <span class="cont">(${h(String(opt.proponent_type).replace(/_/g, " "))})</span>` : ""}</span></div>
      <div><b>Rules as of</b><span>${h(L.run.as_of)}</span></div>
      <div><b>Rules revision</b><span><b class="rev-no">${h(rev(L.run.stamp.stamp))}</b> <span class="cont">· engine ${h(L.run.engine_version)}</span></span></div>
      ${cmpCell}
    </div>
    <p class="quiet">Deterministic output of the rule stack listed under Sources: same inputs and rule set, same memo. A feasibility screen, not legal, planning or funding advice; every number links to the document it came from.</p>
  </div>`);

  // 2. a comparison comes straight after the title block: the two runs side by side, their pickers heading the A
  // and B columns, then What changed; 3. the three answers; 4. the massing figures beside them at >=1600 px, under
  // them otherwise; 5. the full ledger; 6. inputs, sources, version stamp. Only a change in the rules carries the
  // delta into the clauses and the ledger (the Revision Rule); two options differ in their numbers, not their rules.
  if (B) parts.push(renderSideBySide(run));
  if (d) parts.push(renderChanges(d, L));
  const changed = new Set(kind === "rules" ? (d.changes || []).map(c => c.rule_id) : []);
  const rest = [];
  rest.push(renderClauses(res, L, changed));
  rest.push(renderLedger(res, changed));
  rest.push(renderInputs(site, opt));
  rest.push(renderSources(res, site, opt));
  rest.push(renderStamp(L.run));
  parts.push(`<div class="memo-body">
    <div class="answers">${answerAllowed(L)}${answerFunders(L)}${answerUnsure(L)}</div>
    ${renderFigures(run)}
    <div class="memo-rest">${rest.join("\n")}</div>
  </div>`);

  // the run pickers leave the memo before it is replaced and come back after; a picker that had focus keeps it
  const memoEl = $("#memo");
  const focused = document.activeElement && ["open-run", "compare-run"].includes(document.activeElement.id) ? document.activeElement : null;
  placeRunTools(false);
  memoEl.innerHTML = parts.join("\n");
  memoEl.className = "memo";
  void memoEl.offsetWidth;  // restart the fade
  memoEl.classList.add("landed");
  placeRunTools(true);
  if (focused && document.activeElement !== focused) focused.focus({ preventScroll: !!focused.closest("#side-by-side") });
  wireFigures(run);
  wireLedger();
  setPrintFooter(run);
}

/* An option's name as the reader knows it. */
const optionName = L => (L && L.inputs && L.inputs.option && (L.inputs.option.name || L.inputs.option.id)) || "option";

/* A rule id with a break allowed after each dot and underscore, so a narrow column wraps it between its words. */
const idBreak = id => h(id).replace(/([._])/g, "$1<wbr>");

/* What kind of comparison this is: the rules moved (another as-of date or other rule files), two options were read
   under the same rules, or the two runs are the same. attachCause decides it from the two ledgers when it can. */
function compareKind(d) {
  if (d.kind) return d.kind;
  return d.rules_changed || d.previous_as_of !== d.current_as_of ? "rules" : "options";
}

/* Every printed page carries the address, the date and the rules revision in its footer, and its page number. */
function setPrintFooter(run) {
  let st = $("#print-page");
  if (!st) { st = document.createElement("style"); st.id = "print-page"; document.head.appendChild(st); }
  const site = (run.ledger && run.ledger.inputs && run.ledger.inputs.site) || {};
  const text = `Funding-Fit Memo · ${site.address || site.id || ""} · rules as of ${run.as_of} · ${rev(run.stamp)}`.replace(/["\\\n]/g, " ");
  st.textContent = `@media print { @page { margin: 14mm 14mm 16mm;
    @bottom-left { content: "${text}"; font: 7.5pt "IBM Plex Mono", monospace; color: #444; }
    @bottom-right { content: counter(page) " / " counter(pages); font: 7.5pt "IBM Plex Sans", sans-serif; color: #444; } } }`;
}

/* The ledger opens one layer at a time, or all at once; printing opens every layer and closes them again after. */
function wireLedger() {
  const btn = $(".ledger .open-all");
  if (!btn) return;
  const sync = () => { const all = $$(".ledger details").every(x => x.open); btn.textContent = all ? "Close all layers" : "Open all layers"; btn.setAttribute("aria-expanded", String(all)); };
  btn.addEventListener("click", () => { const open = !$$(".ledger details").every(x => x.open); $$(".ledger details").forEach(x => { x.open = open; }); sync(); });
  $$(".ledger details").forEach(x => x.addEventListener("toggle", sync));
  sync();
}

function answerAllowed(L) {
  const res = L.results, ans = L.summary.answers, site = L.inputs.site;
  const o = ans.allowed.outright, bz = ans.allowed.by_rezoning, path = ans.allowed.rezoning_path;
  const outLines = res.filter(r => (r.check || "").startsWith("district_outright") && r.status !== "not_applicable");
  const policy = res.filter(r => ["A", "B", "C"].includes(r.layer) && ["fail", "conditional", "uncertain"].includes(r.status) && !(r.check || "").startsWith("district_outright"));
  let verdict = `${h(VERDICT_OUTRIGHT[o.verdict] || cap(o.verdict) + ".")}`;
  if (path) verdict += ` By rezoning: <em>${h(bz.verdict)}</em>.`;
  let body = `<p class="path">Outright under ${h(site.zoning_district || "the district")}${path ? ` · rezoning path: ${h(path)}` : " · no rezoning path stated"}</p>`;
  body += outLines.map(r => `<p class="finding">${leadCont(r.finding)}</p>`).join("");
  if (path && policy.length) {
    body += `<ul class="finding-list">${policy.map(r => `<li>${pill(r.status)}<span><span class="title">${h(r.title)}:</span> <span class="cont">${h(r.finding)}</span></span></li>`).join("")}</ul>`;
  }
  const status = verdictStatus(path ? bz.verdict : o.verdict);   // the operative answer: by rezoning when a path is stated
  return `<section class="card answer" data-verdict="${h(status)}">
    <h2><span class="badge">1</span> Is it allowed?</h2>
    <p class="verdict">${verdict}</p>
    ${body}
  </section>`;
}

function answerFunders(L) {
  const res = L.results, ans = L.summary.answers, opt = L.inputs.option;
  const targets = new Set(opt.target_programs || []);
  const rows = res.filter(r => r.layer === "E" && (!targets.size || targets.has(r.rule_id)));
  const others = res.filter(r => r.layer === "E" && targets.size && !targets.has(r.rule_id));
  let body = `<ul class="finding-list">${rows.map(r => `<li>${pill(r.status)}<span><span class="title">${h(r.title)}:</span> <span class="cont">${h(withoutRepeat(r.title, r.finding))}</span></span></li>`).join("")}</ul>`;
  if (others.length) body += `<p class="path" style="margin-top:12px">Not targeted, listed in the ledger: ${others.map(r => h(r.title)).join("; ")}.</p>`;
  return `<section class="card answer" data-verdict="${h(verdictStatus(ans.funded.verdict))}">
    <h2><span class="badge">2</span> Does it fit the funders?</h2>
    <p class="verdict"><em>${h(cap(ans.funded.verdict))}.</em></p>
    ${body}
  </section>`;
}

function answerUnsure(L) {
  const items = L.summary.answers.unsure || [];
  const n = items.length;
  const verdict = n ? `${n === 1 ? "One open item" : `${["", "", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"][n] || n} open items`}, each with <em>a named person</em>.` : "<em>Nothing outstanding.</em>";
  const table = n ? `<table class="plain"><thead><tr><th>Item</th><th>Status</th><th>Who / what</th></tr></thead><tbody>
    ${items.map(u => `<tr><td>${h(u.title)}</td><td class="status">${pill(u.status)}</td><td class="who">${h(u.action || "—")}</td></tr>`).join("")}
  </tbody></table>` : "";
  const worst = items.some(u => u.status === "fail") ? "fail" : (n ? "uncertain" : "pass");   // the card wears the heaviest open status
  return `<section class="card answer" data-verdict="${worst}">
    <h2><span class="badge">3</span> What is still unsure, and who resolves it?</h2>
    <p class="verdict">${verdict}</p>
    ${table}
  </section>`;
}

// ---------------------------------------------------------------- the clauses applied: proposed, permitted, the ask

const pct = x => (typeof x === "number" ? `${(100 * x).toFixed(x * 100 % 1 ? 1 : 0)}%` : "—");
const UNIT_WORD = { studio: "studio", one_bed: "1-bed", two_bed: "2-bed", three_bed_plus: "3-bed+" };
const num = x => (x === null || x === undefined ? "—" : fmtNum(x));

/* Each check's numbers split three ways: what the option proposes (the simulation's input), what the clause permits
   or requires, and the ask when the two differ. Checks the table does not know fall back to a split by key name. */
function splitValues(r, L) {
  const v = r.values || {}, opt = (L.inputs && L.inputs.option) || {};
  const ask = r.action || "";
  const path = L.summary && L.summary.answers && L.summary.answers.rezoning_path;
  switch (r.check) {
    case "district_outright_fsr":
      return { proposed: `FSR ${num(v.fsr && Number(v.fsr).toFixed(2))} (${num(v.gfa_m2)} m² on ${num(v.site_area_m2)} m²)`, permitted: `FSR ${num(v.max_fsr_outright)} outright`,
               ask: v.fsr > v.max_fsr_outright ? `Density above the outright limit: ${path ? `relaxation by rezoning (${path})` : "a rezoning"}.` : "" };
    case "district_outright_height":
      return { proposed: `${num(v.height_m)} m, ${num(v.storeys)} storeys`, permitted: `${num(v.max_height_m_outright)} m outright`,
               ask: v.height_m > v.max_height_m_outright ? `Height above the outright limit: ${path ? `relaxation by rezoning (${path})` : "a rezoning"}.` : "" };
    case "rezoning_policy_social_housing": {
      const b = v.benchmark_height_m || [];
      return { proposed: `${num(v.height_m)} m, FSR ${num(v.fsr && Number(v.fsr).toFixed(2))}`, permitted: `staff benchmark ${num(b[0])} to ${num(b[1])} m, about FSR ${num(v.benchmark_fsr)} (negotiated, no maximum)`,
               ask: b[1] && v.height_m > b[1] ? `${(v.height_m - b[1]).toFixed(1)} m above the benchmark: to be negotiated with staff.` : (b[1] && v.fsr > v.benchmark_fsr ? "Density above the benchmark: to be negotiated with staff." : "") };
    }
    case "parking_minimums":
      return { proposed: `${num(v.parking_spaces)} vehicle, ${num(v.bicycle_spaces)} bicycle spaces`, permitted: "no minimum (June 2024); bicycle spaces set at development permit", ask: "" };
    case "toa_status":
      return { proposed: v.storeys != null ? `${num(v.storeys)} storeys` : `${num(opt.storeys)} storeys`, permitted: v.tier ? `tier ${v.tier}: at least ${num(v.min_storeys || v.floors)} storeys may not be refused` : "tier 1: 20, tier 2: 12, tier 3: 8 storeys minimum allowable", ask };
    case "family_unit_share": {
      const m3 = v.min_three_plus_bed_share;
      return { proposed: v.units_total ? `${num(v.two_plus_bed_units)} of ${num(v.units_total)} units two-bed+ (${pct(v.two_plus_bed_share)}); ${num(v.three_plus_bed_units)} three-bed+ (${pct(v.three_plus_bed_share)})` : "unit mix not given",
               permitted: `at least ${pct(v.min_two_plus_bed_share ?? 0.35)} two-bed+${m3 != null ? `, ${pct(m3)} three-bed+` : ""}`, ask };
    }
    case "social_housing_definition":
      return { proposed: `${pct(v.share_below_hils)} of units below HILs; ${num(v.housing_agreement_years)}-year agreement; owner ${String(v.owner_type_at_completion || "—").replace(/_/g, " ")}`,
               permitted: "at least 30% below HILs at rent of at most 30% of income; 60 years or the life of the building; non-profit, co-op or government owner", ask };
    case "tree_replacement":
      return { proposed: `${num(v.existing)} existing, ${num(v.removed)} removed, ${num(v.replacements_proposed)} replacements, ${num(v.trees_after)} after`, permitted: `Schedule C: at least ${num(v.schedule_c_required)} trees on ${num(v.site_area_m2)} m²`,
               ask: v.shortfall > 0 ? `${num(v.shortfall)} tree${v.shortfall === 1 ? "" : "s"} short: plant more or pay $${num(v.cash_in_lieu_cad)} cash in lieu.` : ask };
    case "code_basis_flags":
      return { proposed: `${num(v.storeys)} storeys`, permitted: `Part ${v.part || "—"} of the BC Building Code (Part 9 up to 3 storeys and 600 m²)`, ask: "" };
    case "unit_area_flags": {
      // the minimum net area is given per unit type: studio 33, one-bed 49, …
      const mins = v.min_net_area_m2 && typeof v.min_net_area_m2 === "object"
        ? Object.entries(v.min_net_area_m2).map(([k, x]) => `${UNIT_WORD[k] || k.replace(/_/g, " ")} ${num(x)}`).join(", ") + " m²"
        : `${num(v.min_net_area_m2)} m²`;
      return { proposed: `average ${num(v.average_gross_area_per_unit_m2)} m² gross per unit`, permitted: `BC Housing minimum net areas: ${mins}`, ask: "" };
    }
    case "chf_fit": {
      const mix = v.mix_shares ? `mix ${pct(v.mix_shares.market)} / ${pct(v.mix_shares.rgi)} / ${pct(v.mix_shares.deep_subsidy)}` : "rent-tier mix not given";
      const req = v.required_mix ? `${pct(v.required_mix.market)} market / ${pct(v.required_mix.rgi)} RGI / ${pct(v.required_mix.deep_subsidy)} deep subsidy (±2 points); 5% accessible; 60-year lease at nominal value; site control` : "";
      const unknown = (v.unknown || []).length ? `Supply: ${v.unknown.join("; ")}.` : "";
      const fails = (v.fails || []).length ? `Fix: ${v.fails.join("; ")}.` : "";
      const access = opt.accessible_units == null ? "accessible units not given" : `${num(opt.accessible_units)} accessible`;
      const control = opt.site_control ? `site control ${String(opt.site_control).replace(/_/g, " ")}` : "site control not given";
      return { proposed: `${mix}; ${access}; ${control}`, permitted: req, ask: [fails, unknown].filter(Boolean).join(" ") || ask };
    }
    case "bc_builds_fit": {
      const unknown = (v.unknown || []).length ? `Supply: ${v.unknown.join("; ")}.` : "";
      const fails = (v.fails || []).length ? `Fix: ${v.fails.join("; ")}.` : "";
      // a missing share or discount is said in words, not left as a dash in the middle of a sentence
      const below = opt.below_market_unit_share == null && opt.below_market_discount == null ? "below-market share and discount not given"
        : opt.below_market_unit_share == null ? `below-market share not given, at ${pct(opt.below_market_discount)} below market`
        : opt.below_market_discount == null ? `${pct(opt.below_market_unit_share)} of units below market, discount not given`
        : `${pct(opt.below_market_unit_share)} of units at ${pct(opt.below_market_discount)} below market`;
      return { proposed: `${below}; ${num(opt.non_residential_gfa_m2 || 0)} m² non-residential`, permitted: "at least 20% of units at least 20% below market; non-residential at most 30% of area; a non-profit teamed with a builder", ask: [fails, unknown].filter(Boolean).join(" ") || ask };
    }
    case "dcl_cac":
      return { proposed: "social housing", permitted: `DCL ${v.dcl_exempt ? "exempt" : "payable"}, CAC ${v.cac_exempt ? "exempt" : "payable"}`, ask: "" };
    case "info_only":
      return { proposed: "", permitted: Object.entries(v).filter(([, x]) => x !== null && typeof x !== "object").map(([k, x]) => `${k.replace(/_/g, " ")}: ${fmtNum(x)}`).join("; "), ask: "" };
    default: {
      const lim = k => /^(max_|min_|required|benchmark_|schedule_|eligible)/.test(k);
      const flat = Object.entries(v).filter(([, x]) => x !== null && x !== undefined && typeof x !== "object");
      return { proposed: flat.filter(([k]) => !lim(k)).map(([k, x]) => `${k.replace(/_/g, " ")} ${fmtNum(x)}`).join("; "), permitted: flat.filter(([k]) => lim(k)).map(([k, x]) => `${k.replace(/_/g, " ")} ${fmtNum(x)}`).join("; "), ask };
    }
  }
}

/* Every clause that applied to this site and option, in one table: its status, the numbers the option proposes,
   what the clause permits or requires, and the ask where they differ. Not-applicable rules are named underneath. */
function renderClauses(res, L, changed = new Set()) {
  const applied = res.filter(r => r.status !== "not_applicable");
  const na = res.filter(r => r.status === "not_applicable");
  const order = { fail: 0, conditional: 1, uncertain: 2, pass: 3, info: 4 };
  const rows = applied.slice().sort((a, b) => (order[a.status] ?? 9) - (order[b.status] ?? 9) || a.layer.localeCompare(b.layer)).map(r => {
    const s = splitValues(r, L);
    return `<tr class="st-${h(r.status)}">
      <td><span class="rule-title">${h(r.title)}${changed.has(r.rule_id) ? REV : ""}</span><code class="rule-id">${idBreak(r.rule_id)} · v ${h(r.version_effective_from || "—")}</code>${r.source && r.source.section ? `<span class="rule-sec">${h(r.source.section)}</span>` : ""}</td>
      <td class="status">${pill(r.status)}</td>
      <td class="nums">${h(s.proposed || "—")}</td>
      <td class="nums">${h(s.permitted || "—")}</td>
      <td class="ask">${s.ask ? h(s.ask) : `<span class="cont">—</span>`}</td>
    </tr>`;
  }).join("");
  const counts = {};
  for (const r of applied) counts[r.status] = (counts[r.status] || 0) + 1;
  const countPills = ["fail", "conditional", "uncertain", "pass", "info"].filter(s => counts[s]).map(s => `<span class="pill pill-${s}">${counts[s]} ${h(STATUS_WORD[s])}</span>`).join("");
  return `<section class="card section clauses">
    <h2>Clauses applied · ${applied.length} of ${res.length} rules</h2>
    <p class="intro">Every clause that applies to this site and option, worst first. <b>Proposed</b> is what the option puts forward and the simulation used; <b>permitted or required</b> is the clause's own limit; <b>the ask</b> is the relaxation, negotiation or missing figure that stands between them.</p>
    <div class="counts">${countPills}</div>
    <table class="plain"><colgroup><col class="c-rule"><col class="c-status"><col class="c-prop"><col class="c-perm"><col class="c-ask"></colgroup>
      <thead><tr><th>Clause</th><th>Status</th><th>Proposed (simulated)</th><th>Permitted or required</th><th>The ask</th></tr></thead><tbody>${rows}</tbody></table>
    ${na.length ? `<p class="na">Not applicable here: ${na.map(r => `${h(r.title)} <code>${h(r.rule_id)}</code>`).join("; ")}.</p>` : ""}
  </section>`;
}

/* The two run pickers. With two runs compared they head the Side by side card's A and B columns, so the choice
   sits above what it changes; otherwise, and whenever the memo is about to be replaced, they sit above the memo.
   In the card their keys name the column; a hidden phrase keeps what each one does in its accessible name. */
const RUN_TOOLS = [["open", "#tool-open", "A · This run", " (open a past run)"], ["compare", "#tool-compare", "B · Compared", " (choose the run to compare with)"]];

function placeRunTools(intoMemo) {
  const tools = $(".memo-tools");
  for (const [slot, id, word, purpose] of RUN_TOOLS) {
    const label = $(id), eyebrow = $(".eyebrow", label);
    if (!eyebrow.dataset.text) eyebrow.dataset.text = eyebrow.textContent;
    let hint = $(".tool-purpose", label);
    if (!hint) { hint = document.createElement("span"); hint.className = "sr-only tool-purpose"; eyebrow.after(hint); }
    const cell = intoMemo ? $(`#side-by-side [data-slot="${slot}"]`) : null;
    if (cell) { cell.prepend(label); eyebrow.textContent = word; hint.textContent = purpose; }
    else { tools.insertBefore(label, $("#compare-note")); eyebrow.textContent = eyebrow.dataset.text; hint.textContent = ""; }
  }
  tools.hidden = !$(".tool", tools);
}

/* What the two options trade, in the units a board reads: units, storeys, height and floor area, A against B. */
function tradeOff(A, B) {
  const a = (A.inputs && A.inputs.option) || {}, b = (B.inputs && B.inputs.option) || {};
  const units = o => { const v = Object.values(o.units || {}).filter(x => typeof x === "number"); return v.length ? v.reduce((s, x) => s + x, 0) : null; };
  const facts = [[units(a), units(b), "units"], [a.storeys, b.storeys, "storeys"], [a.height_m, b.height_m, "m high"], [a.gfa_m2, b.gfa_m2, "m² of floor area"]]
    .filter(([x, y]) => x != null && y != null && x !== y)
    .map(([x, y, unit]) => `${fmtNum(x)} ${unit} against ${fmtNum(y)}`);
  return facts.length ? `A against B: ${facts.join(", ")}.` : "The two runs propose the same building.";
}

/* Two runs side by side: the pickers on the A and B columns, the four answers of each, then the rules whose status
   differs; the rules that read the same in both wait behind a disclosure. */
function renderSideBySide(run) {
  const A = run.ledger, B = run.compareLedger, d = run.diff;
  if (!A || !B) return "";
  const kind = d ? compareKind(d) : "options";
  const ans = L => L.summary.answers;
  const verdictCell = w => `<span class="pill pill-${h(verdictStatus(w) || "na")}">${h(cap(w))}</span>`;
  const openCell = L => { const u = ans(L).unsure || []; return u.length ? `<span class="pill pill-${u.some(x => x.status === "fail") ? "fail" : "uncertain"}">${u.length} open</span>` : `<span class="pill pill-pass">Nothing open</span>`; };
  const head = [
    ["Allowed outright", verdictCell(ans(A).allowed.outright.verdict), verdictCell(ans(B).allowed.outright.verdict)],
    ["By rezoning", verdictCell(ans(A).allowed.by_rezoning.verdict), verdictCell(ans(B).allowed.by_rezoning.verdict)],
    ["Fits the funders", verdictCell(ans(A).funded.verdict), verdictCell(ans(B).funded.verdict)],
    ["Open items", openCell(A), openCell(B)],
  ];
  const lead = kind === "rules"
    ? `The same site and option read under the rules as of ${h(A.run.as_of)} (${h(rev(A.run.stamp.stamp))}) against ${h(B.run.as_of)} (${h(rev(B.run.stamp.stamp))}).`
    : `${h(tradeOff(A, B))} Both read under the same rules, ${h(rev(A.run.stamp.stamp))}.`;
  const byId = Object.fromEntries(B.results.map(r => [r.rule_id, r]));
  const rows = A.results.filter(r => r.status !== "not_applicable" || (byId[r.rule_id] && byId[r.rule_id].status !== "not_applicable")).map(r => {
    const b = byId[r.rule_id];
    return { r, b, differs: !b || b.status !== r.status };
  });
  const differ = rows.filter(x => x.differs), same = rows.filter(x => !x.differs);
  const row = ({ r, b }) => {
    const sa = splitValues(r, A), sb = b ? splitValues(b, B) : { proposed: "" };
    return `<tr>
      <td><span class="rule-title">${h(r.title)}</span><code class="rule-id">${idBreak(r.rule_id)}</code></td>
      <td class="status">${pill(r.status)}<div class="cont">${h(sa.proposed || "")}</div></td>
      <td class="status">${b ? pill(b.status) : "<span class=\"cont\">not run</span>"}<div class="cont">${h(sb.proposed || "")}</div></td>
    </tr>`;
  };
  const table = list => `<table class="plain side-rules"><colgroup><col class="c-rule"><col class="c-ab"><col class="c-ab"></colgroup>
      <thead><tr><th>Rule</th><th>A</th><th>B</th></tr></thead><tbody>${list.map(row).join("")}</tbody></table>`;
  // each run's open items, with the person who resolves them, for the run that still has some
  const openList = [["A", A], ["B", B]].filter(([, L]) => (ans(L).unsure || []).length).map(([k, L]) => `<details class="side-open">
      <summary>${k} · ${h(optionName(L))}: ${ans(L).unsure.length} open item${ans(L).unsure.length === 1 ? "" : "s"}</summary>
      <ul>${ans(L).unsure.map(u => `<li>${pill(u.status)} <b>${h(u.title)}</b> <span class="cont">${h(u.action || "")}</span></li>`).join("")}</ul>
    </details>`).join("");
  return `<section class="card section side" id="side-by-side" aria-labelledby="side-h">
    <h2 id="side-h">Side by side</h2>
    <div class="pick-row" role="group" aria-label="The two runs compared">
      <span class="pick-key" aria-hidden="true"></span>
      <div class="pick" data-slot="open"><span class="pick-name">A · ${h(optionName(A))} <span class="cont">(as of ${h(A.run.as_of)})</span></span></div>
      <div class="pick" data-slot="compare"><span class="pick-name">B · ${h(optionName(B))} <span class="cont">(as of ${h(B.run.as_of)})</span></span></div>
    </div>
    <p class="side-lead">${lead}</p>
    <table class="plain side-head"><thead><tr><th><span class="sr-only">Answer</span></th><th><span class="sr-only">A, ${h(optionName(A))}</span></th><th><span class="sr-only">B, ${h(optionName(B))}</span></th></tr></thead>
      <tbody>${head.map(([k, a, b]) => `<tr><th scope="row">${h(k)}</th><td>${a}</td><td>${b}</td></tr>`).join("")}</tbody></table>
    ${openList}
    <h3 class="side-sub">${differ.length ? `${differ.length} of ${rows.length} rules read differently` : `All ${rows.length} rules read the same in both`}</h3>
    ${differ.length ? table(differ) : ""}
    ${same.length ? `<details class="side-same"><summary>${differ.length ? `The other ${same.length} rules, the same in both` : `Show the ${same.length} rules`}</summary>${table(same)}</details>` : ""}
    <p class="cont side-note">Under each status is what that option proposed.</p>
  </section>`;
}

function renderLedger(res, changed = new Set()) {
  const layers = [];
  for (const r of res) {
    let L = layers.find(x => x.layer === r.layer);
    if (!L) { L = { layer: r.layer, title: r.layer_title, rows: [] }; layers.push(L); }
    L.rows.push(r);
  }
  const blocks = layers.map(L => {
    const counts = {};
    for (const r of L.rows) counts[r.status] = (counts[r.status] || 0) + 1;
    const countPills = Object.entries(counts).map(([s, n]) => `<span class="pill pill-${h(s)}">${n} ${h(STATUS_WORD[s] || s)}</span>`).join("");
    const rows = L.rows.map(r => `<tr>
      <td><span class="rule-title">${h(r.title)}${changed.has(r.rule_id) ? REV : ""}</span><code class="rule-id">${h(r.rule_id)} · v ${h(r.version_effective_from || "—")}</code></td>
      <td class="status">${pill(r.status)}</td>
      <td>${h(r.finding)}</td>
      <td class="nums">${h(fmtValues(r.values))}</td>
      <td class="src">${sourceLink(r.source)}</td>
    </tr>`).join("");
    const revised = L.rows.some(r => changed.has(r.rule_id));
    return `<details${revised ? " open" : ""}>
      <summary><span class="layer">Layer ${h(L.layer)}</span><span class="layer-title">${h(L.title)}</span>${revised ? REV : ""}<span class="counts">${countPills}</span></summary>
      <table class="plain"><colgroup><col class="c-rule"><col class="c-status"><col class="c-finding"><col class="c-nums"><col class="c-src"></colgroup><thead><tr><th>Rule</th><th>Status</th><th>Finding</th><th>Numbers used</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table>
    </details>`;
  });
  return `<section class="card section ledger">
    <h2>Full ledger by layer · ${res.length} rules</h2>
    <p class="intro">The same rules by layer, with the engine's finding, every number it used and the clause it came from, including the rules that did not apply. Open a layer to read its rows.</p>
    <div class="tools"><button class="btn btn-quiet btn-small open-all" type="button" aria-expanded="false">Open all layers</button></div>
    ${blocks.join("")}
  </section>`;
}

function renderInputs(site, opt) {
  const u = opt.units || {};
  const units = Object.entries(u).map(([k, v]) => `${k.replace(/_/g, " ")} ${v ?? "—"}`).join(", ");
  const tenure = String(opt.tenure || "").replace(/_/g, " ");
  return `<section class="card section inputs-used">
    <h2>Inputs</h2>
    <ul>
      <li>Site <code>${h(site.id)}</code>: ${h(site.zoning_district || "—")}, ${h(fmtNum(site.site_area_m2 ?? "—"))} m², ${h(site.frontage_m ?? "—")} × ${h(site.depth_m ?? "—")} m; owner: ${h(site.owner || "—")}.</li>
      <li>Option <code>${h(opt.id)}</code>: ${h(opt.storeys ?? "—")} storeys, ${h(opt.height_m ?? "—")} m, ${h(fmtNum(opt.gfa_m2 ?? "—"))} m² GFA; units ${h(units || "—")}; tenure ${h(tenure || "—")}.</li>
      ${site.notes ? `<li>Site notes: <span class="cont">${h(site.notes)}</span></li>` : ""}
      ${opt.notes ? `<li>Option notes: <span class="cont">${h(opt.notes)}</span></li>` : ""}
    </ul>
  </section>`;
}

function renderSources(res, site, opt) {
  const seen = new Set();
  const items = [];
  for (const r of res) {
    const s = r.source || {};
    const key = `${s.title || ""}|${s.url || ""}`;
    if (!s.title && !s.url) continue;
    if (seen.has(key)) continue;
    seen.add(key);
    items.push(`<li>${s.url ? `<a href="${h(s.url)}" target="_blank" rel="noopener">${h(s.title || s.url)}</a>` : h(s.title)}${s.verify ? ` <span class="verify">(verify: ${h(s.verify)})</span>` : ""}</li>`);
  }
  for (const s of (site.sources || []).concat(opt.sources || [])) {
    const key = `${s.title || ""}|${s.url || ""}`;
    if (seen.has(key)) continue;
    seen.add(key);
    items.push(`<li>${s.url ? `<a href="${h(s.url)}" target="_blank" rel="noopener">${h(s.title || s.url)}</a>` : h(s.title)}</li>`);
  }
  return `<section class="card section sources">
    <h2>Sources</h2>
    <ul>${items.join("")}</ul>
  </section>`;
}

/* The memo's rules revision, and the fingerprint behind it: the one place the stamp's hash is shown. */
function renderStamp(run) {
  const st = run.stamp;
  const files = Object.entries(st.rules_files || {}).map(([f, hsh]) => `<li><code>${h(f)}</code> <span class="hash">${h(hsh.slice(0, 16))}…</span></li>`).join("");
  return `<section class="card section stampbox">
    <h2>Rules revision ${h(rev(st.stamp))}</h2>
    <p>${h(rev(st.stamp))} is this reading of the rules: the rule files below and the versions in force on ${h(run.as_of)}. Change one number in one rule, or read the rules on a date when a version changes, and the memo is on a new revision. Revisions are numbered R1, R2 and so on by the earliest date each was read on, across the runs on file.</p>
    <p class="hash">Fingerprint ${h(st.stamp)} · rules hash (SHA-256 over all rule files) ${h(st.rules_hash)}</p>
    <ul>${files}</ul>
  </section>`;
}

// ---------------------------------------------------------------- figures: drawn from massing.json, formatting only

/* the drawing colours of the Lotwise sheets, read from app.css's --c-* tokens (the same in both themes, because the
   drawings sit on white paper): envelope blue, grey streets and lanes, drawing ink, amber for a form line */
const tok = (name, fallback) => (getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback);
const FIG = { paper: tok("--c-paper", "#ffffff"), proposedFill: tok("--c-envelope", "#3c8cdc"), proposedStroke: tok("--c-envelope-line", "#2a6fb8"),
              outrightFill: tok("--c-lane", "#bdbdbd"), outrightStroke: tok("--c-street", "#8e8e8e"), bench: tok("--c-bench", "#c77d14"), benchText: tok("--c-bench-text", "#8f5a0e"),
              lot: tok("--c-drawink", "#1f2933"), env: tok("--c-env", "#c81e1e"), grey: tok("--c-drawmuted", "#5f6672") };
const SVG_OPEN = `xmlns="http://www.w3.org/2000/svg" font-family="IBM Plex Sans, Helvetica, Arial, sans-serif" role="img"`;
const NS = `vector-effect="non-scaling-stroke"`;
/* a label drawn over the half tone keeps a thin paper halo so it reads over roads and buildings */
const HALO = `paint-order="stroke" stroke="#ffffff" stroke-linejoin="round"`;
const halo = fs => `${HALO} stroke-width="${(fs * 0.28).toFixed(2)}"`;

/* Drawing labels at one size on screen. The figures are drawn in metres and scale with their card, so a label sized
   in metres would read 20 px in a wide card and 9 px in a narrow one; after a first render the label size is set
   again from the drawing's own scale. */
const LABEL_PX = 11.5;
function fitLabels(box, build) {
  let fs = null;
  for (let pass = 0; pass < 3; pass++) {
    box.innerHTML = build(fs);
    const svg = $("svg", box), ctm = svg && svg.getScreenCTM();
    if (!ctm || !ctm.a) break;
    const next = LABEL_PX / ctm.a;
    if (fs && Math.abs(next - fs) / fs < 0.03) break;
    fs = next;
  }
  return fs;
}

/* A scale bar in the drawing's corner: a round length near a fifth of the frame, in two halves. */
function scaleBar(x, y, frameW, fs) {
  const L = [5, 10, 20, 25, 50, 100].find(v => v >= frameW / 6) || 100;
  const hgt = fs * 0.4;
  return `<g class="scalebar">
    <rect x="${(x - fs * 0.4).toFixed(2)}" y="${(y - fs * 1.5).toFixed(2)}" width="${(L + fs * 3.6).toFixed(2)}" height="${(fs * 2.1).toFixed(2)}" fill="${FIG.paper}" fill-opacity="0.85"/>
    <rect x="${x.toFixed(2)}" y="${(y - hgt).toFixed(2)}" width="${(L / 2).toFixed(2)}" height="${hgt.toFixed(2)}" fill="${FIG.lot}"/>
    <rect x="${(x + L / 2).toFixed(2)}" y="${(y - hgt).toFixed(2)}" width="${(L / 2).toFixed(2)}" height="${hgt.toFixed(2)}" fill="${FIG.paper}" stroke="${FIG.lot}" stroke-width="0.8" ${NS}/>
    <text x="${x.toFixed(2)}" y="${(y - hgt - fs * 0.35).toFixed(2)}" font-size="${fs.toFixed(2)}" fill="${FIG.lot}" text-anchor="middle">0</text>
    <text x="${(x + L).toFixed(2)}" y="${(y - hgt - fs * 0.35).toFixed(2)}" font-size="${fs.toFixed(2)}" fill="${FIG.lot}" text-anchor="middle">${L} m</text>
  </g>`;
}

/* A north arrow, only where the site's OpenStreetMap frame says which way the lot faces; the plan is drawn with the
   street at the bottom, so north is wherever the frame puts it. x_axis_bearing_deg is the bearing of the lot's x axis
   (along the frontage); the plan's up is the y axis, 90 degrees anticlockwise of it. */
function northArrow(cx, cy, bearing, fs) {
  const rot = 90 - bearing;          // north, measured clockwise from the drawing's up
  const r = fs * 1.15, t = rot * Math.PI / 180, d = r + fs * 0.8;
  const nx = cx + d * Math.sin(t), ny = cy - d * Math.cos(t) + fs * 0.35;   // the N stays upright, beyond the tip
  return `<g class="north"><g transform="rotate(${rot.toFixed(1)} ${cx.toFixed(2)} ${cy.toFixed(2)})">
    <circle cx="${cx.toFixed(2)}" cy="${cy.toFixed(2)}" r="${r.toFixed(2)}" fill="${FIG.paper}" fill-opacity="0.85" stroke="${FIG.lot}" stroke-width="0.8" ${NS}/>
    <polygon points="${cx.toFixed(2)},${(cy - r * 0.92).toFixed(2)} ${(cx + r * 0.42).toFixed(2)},${(cy + r * 0.55).toFixed(2)} ${cx.toFixed(2)},${(cy + r * 0.2).toFixed(2)} ${(cx - r * 0.42).toFixed(2)},${(cy + r * 0.55).toFixed(2)}" fill="${FIG.lot}"/>
    </g><text x="${nx.toFixed(2)}" y="${ny.toFixed(2)}" font-size="${(fs * 0.95).toFixed(2)}" font-weight="600" text-anchor="middle" fill="${FIG.lot}" ${halo(fs)}>N</text></g>`;
}

function polyEl(pts, attrs) {
  return `<polygon points="${pts.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(" ")}" ${attrs} ${NS}/>`;
}

/* The context around the lot, in half tone: the street in front, the lane behind, cross streets, the neighbouring
   parcels, street trees and the trees on site. Real figures come from site.context when the site file has them;
   otherwise typical defaults stand in (a 20 m street, a 6 m lane, neighbours of the lot's own depth) and the
   on-site trees, whose positions are rarely public, are placed schematically along the rear. */
const HALF = { street: tok("--c-half-road", "#e9e9e6"), parcel: tok("--c-bldg", "#f4f4f2"), building: tok("--c-half-building", "#e2e2df"),
               line: tok("--c-half-line", "#c9c9c5"), text: tok("--c-street-text", "#63635f"), tree: tok("--c-tree", "#9fb07f"),
               treeLine: tok("--c-tree-line", "#7f9664"), gone: tok("--c-lane", "#bdbdbd") };

function siteContext(site, m) {
  const W = m.lot.frontage_m, D = m.lot.depth_m;
  const c = (site && site.context) || {};
  const street = { name: (c.street && c.street.name) || (site && site.street_trees && site.street_trees.street) || "street", width: (c.street && c.street.width_m) || 20 };
  const lane = c.lane === false || c.lane === null ? null : { width: (c.lane && c.lane.width_m) || 6 };
  const cross = [];
  for (const k of ["left", "right"]) {
    const x = c[`${k}_street`] || (c.cross_street && c.cross_street.side === k ? c.cross_street : null);
    if (x) cross.push({ side: k, name: x.name || "street", width: x.width_m || 20 });
  }
  const neighbours = [];
  for (const k of ["left", "right"]) {
    if (c.neighbours === false || cross.some(x => x.side === k)) continue;
    const n = (c.neighbours && c.neighbours[k]) || {};
    neighbours.push({ side: k, width: n.frontage_m || Math.max(12, Math.round(W * 0.6)) });
  }
  const streetTrees = (c.street_trees_count != null ? c.street_trees_count : (site && site.street_trees && site.street_trees.count)) || 0;
  const list = (site && site.existing_trees_on_site) || [];
  const pos = Object.fromEntries((c.trees || []).map(t => [t.id, t]));
  let schematic = false;
  const trees = list.map((t, i) => {
    const p = pos[t.id];
    if (!p) schematic = true;
    const crown = (p && p.crown_m) || Math.min(6, Math.max(2, (t.dbh_cm || 20) / 10));
    const x = p ? p.x : 6 + (W - 12) * (list.length > 1 ? i / (list.length - 1) : 0.5);
    const y = p ? p.y : D - 7;
    return { id: t.id, x, y, crown, retained: t.status === "retain" };
  });
  const left = cross.find(x => x.side === "left"), right = cross.find(x => x.side === "right");
  const nl = neighbours.find(n => n.side === "left"), nr = neighbours.find(n => n.side === "right");
  const ext = { left: left ? left.width : nl ? nl.width : 0, right: right ? right.width : nr ? nr.width : 0 };
  const xmin = -ext.left, xmax = W + ext.right, ymin = -street.width, ymax = D + (lane ? lane.width : 0);
  // the ground shapes, in lot coordinates (x along the frontage, y into the lot; the street is y < 0)
  const ground = [];
  ground.push({ ring: [[xmin, ymin], [xmax, ymin], [xmax, 0], [xmin, 0]], fill: HALF.street, label: street.name, at: [W / 2, -street.width / 2] });
  if (lane) ground.push({ ring: [[xmin, D], [xmax, D], [xmax, ymax], [xmin, ymax]], fill: HALF.street, label: "lane", at: [W / 2, D + lane.width / 2] });
  for (const x of cross) {
    const ring = x.side === "left" ? [[xmin, 0], [0, 0], [0, ymax], [xmin, ymax]] : [[W, 0], [xmax, 0], [xmax, ymax], [W, ymax]];
    ground.push({ ring, fill: HALF.street, label: x.name, at: [x.side === "left" ? -x.width / 2 : W + x.width / 2, D / 2], rotate: true });
  }
  for (const n of neighbours) {
    const ring = n.side === "left" ? [[-n.width, 0], [0, 0], [0, D], [-n.width, D]] : [[W, 0], [W + n.width, 0], [W + n.width, D], [W, D]];
    ground.push({ ring, fill: HALF.parcel, dash: true, label: "neighbour", at: [n.side === "left" ? -n.width / 2 : W + n.width / 2, D * 0.85] });
  }
  const streetTreeList = [];
  for (let i = 0; i < streetTrees; i++) streetTreeList.push({ x: W * (i + 0.5) / streetTrees, y: -3, crown: 2.5 });
  const labels = ground.map(g => ({ text: g.label, at: g.at, angle: g.rotate ? 90 : 0 }));
  const base = { W, D, street, lane, cross, neighbours, streetTrees: streetTreeList, trees, schematic, ground, labels, buildings: [], osmTrees: [], xmin, xmax, ymin, ymax, osm: null };
  return site && site.osm ? osmContext(site, m, base) : base;
}

/* The same context from OpenStreetMap when `python -m ffm context` has stored it in the site file: roads as
   strips of their width, building footprints (extruded in 3D by their tagged height or storeys), mapped trees,
   all already in the lot's metres. The lot's own trees from the site file stay as they are. */
function osmContext(site, m, base) {
  const o = site.osm, W = m.lot.frontage_m, D = m.lot.depth_m;
  const r = (o.radius_m || 120) * 0.92;
  const ground = [], labels = [], seen = new Set();
  // the address street is always named, beside the lot and clear of the frontage dimension along its front
  const front = o.frame && o.frame.front_street;
  if (front) {
    let best = null;
    for (const road of (o.roads || []).filter(x => x.name === front)) {
      const pts = road.points || [], T = [W + Math.max(18, W * 0.35), -(road.width_m || 8) / 2];
      for (let i = 0; i + 1 < pts.length; i++) {
        const [x1, y1] = pts[i], [x2, y2] = pts[i + 1], dx = x2 - x1, dy = y2 - y1, L2 = dx * dx + dy * dy;
        if (!L2) continue;
        const t = Math.max(0, Math.min(1, ((T[0] - x1) * dx + (T[1] - y1) * dy) / L2));
        const q = [x1 + t * dx, y1 + t * dy], dist = Math.hypot(q[0] - T[0], q[1] - T[1]);
        if (!best || dist < best.dist) best = { dist, at: q, angle: Math.atan2(dy, dx) * 180 / Math.PI };
      }
    }
    if (best) {
      let angle = best.angle; if (angle > 90) angle -= 180; if (angle < -90) angle += 180;
      labels.push({ text: front, at: best.at, angle, strong: true });
      seen.add(front);
    }
  }
  for (const road of o.roads || []) {
    const w = road.width_m || 8, pts = road.points || [];
    for (let i = 0; i + 1 < pts.length; i++) {
      const [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
      const L = Math.hypot(x2 - x1, y2 - y1); if (!L) continue;
      const nx = -(y2 - y1) / L * w / 2, ny = (x2 - x1) / L * w / 2;
      ground.push({ ring: [[x1 + nx, y1 + ny], [x2 + nx, y2 + ny], [x2 - nx, y2 - ny], [x1 - nx, y1 - ny]], fill: HALF.street, seam: true });
    }
    if (road.name && !seen.has(road.name) && pts.length > 1) {
      // label the longest segment of each named road, once, if it falls inside the frame
      let best = null;
      for (let i = 0; i + 1 < pts.length; i++) {
        const L = Math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]);
        if (!best || L > best.L) best = { L, i };
      }
      const [x1, y1] = pts[best.i], [x2, y2] = pts[best.i + 1];
      const at = [(x1 + x2) / 2, (y1 + y2) / 2];
      if (Math.abs(at[0] - W / 2) < r && Math.abs(at[1] - D / 2) < r) {
        let angle = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
        if (angle > 90) angle -= 180; if (angle < -90) angle += 180;
        labels.push({ text: road.name, at, angle });
        seen.add(road.name);
      }
    }
  }
  const buildings = (o.buildings || []).map(b => ({ polygon: b.polygon, height: b.height_m || 7, name: b.name }));
  const osmTrees = (o.trees || []).map(t => ({ x: t.x, y: t.y, crown: t.crown_m || 3 }));
  return Object.assign({}, base, {
    ground, labels, buildings, osmTrees, streetTrees: [],
    xmin: W / 2 - r, xmax: W / 2 + r, ymin: D / 2 - r, ymax: D / 2 + r, frameRadius: r * 0.75,
    osm: { attribution: o.attribution, fetched: (o.fetched_at || "").slice(0, 10), radius: o.radius_m, counts: o.counts || {}, omitted: o.buildings_on_site_omitted || [], frontStreet: o.frame && o.frame.front_street,
           bearing: o.frame && typeof o.frame.x_axis_bearing_deg === "number" ? o.frame.x_axis_bearing_deg : null },
  });
}

function figPlan(m, ctx, fsIn = null) {
  const W = m.lot.frontage_m, D = m.lot.depth_m;
  const pad = Math.max(3, W * 0.05);
  const fs = fsIn || Math.max(2.2, W / 34);
  const masses = Object.fromEntries(m.masses.map(x => [x.name, x]));
  const x0 = ctx.xmin - pad, x1 = Math.max(ctx.xmax + pad, W + fs * 2.6 + pad), y0 = ctx.ymin - pad, y1 = ctx.ymax + pad;
  const Y = y => y1 - y;                                // the street (y < 0) drawn at the bottom
  const X = x => x - x0;
  const P = pts => pts.map(([x, y]) => [X(x), Y(y)]);
  const vbW = x1 - x0, vbH = y1 - y0;
  let s = `<svg ${SVG_OPEN} viewBox="0 0 ${vbW.toFixed(2)} ${vbH.toFixed(2)}" aria-label="Plan: the lot with its streets, buildings and trees in half tone, the setback envelope and the two massing footprints">`;
  s += `<rect x="0" y="0" width="${vbW.toFixed(2)}" height="${vbH.toFixed(2)}" fill="${ctx.osm ? HALF.parcel : "#ffffff"}"/>`;
  for (const g of ctx.ground) s += polyEl(P(g.ring), g.seam ? `fill="${g.fill}" stroke="${g.fill}" stroke-width="0.6" stroke-linejoin="round"` : `fill="${g.fill}" stroke="${HALF.line}" stroke-width="0.8"${g.dash ? ` stroke-dasharray="3 2"` : ""}`);
  for (const b of ctx.buildings) s += polyEl(P(b.polygon), `fill="${HALF.building}" stroke="${HALF.line}" stroke-width="0.6"`);
  for (const l of ctx.labels) {
    const [lx, ly] = [X(l.at[0]), Y(l.at[1])];
    s += `<text x="${lx.toFixed(2)}" y="${(ly + fs * 0.35).toFixed(2)}" font-size="${(fs * 0.9).toFixed(2)}" text-anchor="middle" fill="${l.strong ? FIG.grey : HALF.text}"${l.strong ? ` font-weight="600"` : ""} ${halo(fs)}${l.angle ? ` transform="rotate(${(-l.angle).toFixed(1)} ${lx.toFixed(2)} ${ly.toFixed(2)})"` : ""}>${h(l.text)}</text>`;
  }
  for (const t of ctx.streetTrees.concat(ctx.osmTrees)) s += `<circle cx="${X(t.x).toFixed(2)}" cy="${Y(t.y).toFixed(2)}" r="${t.crown}" fill="${HALF.tree}" fill-opacity="0.35" stroke="${HALF.treeLine}" stroke-width="0.6" ${NS}/>`;
  s += polyEl(P(m.lot.polygon), `fill="${FIG.paper}" stroke="${FIG.lot}" stroke-width="1.2"`);
  s += polyEl(P(m.envelope.polygon), `fill="none" stroke="${FIG.env}" stroke-width="1" stroke-dasharray="4 3"`);
  // the proposed footprint, then the outright one drawn over it as a heavy dashed outline, so both read in plan
  if (masses.proposed) s += polyEl(P(masses.proposed.footprint), `fill="${FIG.proposedFill}" stroke="${FIG.proposedStroke}" stroke-width="1.2" fill-opacity="0.5"`);
  if (masses.outright) s += polyEl(P(masses.outright.footprint), `fill="${FIG.outrightFill}" fill-opacity="${masses.proposed ? 0.35 : 0.9}" stroke="${FIG.outrightStroke}" stroke-width="2" stroke-dasharray="6 3"`);
  // tree ids only where there is room for them: at the label size, schematic trees along the rear would overprint
  const gap = ctx.trees.reduce((g, t, i) => Math.min(g, ...ctx.trees.slice(i + 1).map(u => Math.hypot(u.x - t.x, u.y - t.y))), Infinity);
  const ids = gap > fs * 2.4;
  for (const t of ctx.trees) {
    const cx = X(t.x).toFixed(2), cy = Y(t.y).toFixed(2);
    if (t.retained) s += `<circle cx="${cx}" cy="${cy}" r="${t.crown}" fill="${HALF.tree}" fill-opacity="0.45" stroke="${HALF.treeLine}" stroke-width="0.8" ${NS}/>`;
    else s += `<circle cx="${cx}" cy="${cy}" r="${t.crown}" fill="none" stroke="${HALF.gone}" stroke-width="0.6" stroke-dasharray="1.5 1.5" ${NS}/>${t.crown > fs * 0.5 ? `<text x="${cx}" y="${(Y(t.y) + fs * 0.35).toFixed(2)}" font-size="${(fs * 0.9).toFixed(2)}" text-anchor="middle" fill="${HALF.gone}">×</text>` : ""}`;
    if (ids) s += `<text x="${(X(t.x) + t.crown + 0.5).toFixed(2)}" y="${(Y(t.y) - t.crown * 0.6).toFixed(2)}" font-size="${(fs * 0.85).toFixed(2)}" fill="${t.retained ? HALF.treeLine : HALF.gone}" ${halo(fs)}>${h(t.id)}</text>`;
  }
  // dimension strings: the frontage along the front line, the depth along the right-hand lot line, each with ticks
  const tick = fs * 0.35;
  const fy = Y(0) + fs * 0.55;
  s += `<g stroke="${FIG.grey}" stroke-width="0.8" ${NS}><line x1="${X(0).toFixed(2)}" y1="${fy.toFixed(2)}" x2="${X(W).toFixed(2)}" y2="${fy.toFixed(2)}"/>`
     + `<line x1="${(X(0) - tick).toFixed(2)}" y1="${(fy + tick).toFixed(2)}" x2="${(X(0) + tick).toFixed(2)}" y2="${(fy - tick).toFixed(2)}"/>`
     + `<line x1="${(X(W) - tick).toFixed(2)}" y1="${(fy + tick).toFixed(2)}" x2="${(X(W) + tick).toFixed(2)}" y2="${(fy - tick).toFixed(2)}"/></g>`;
  s += `<text x="${X(W / 2).toFixed(2)}" y="${(fy + fs * 1.2).toFixed(2)}" font-size="${fs.toFixed(2)}" text-anchor="middle" fill="${FIG.grey}" ${halo(fs)}>frontage ${h(W)} m</text>`;
  const dx = X(W) + fs * 0.6;
  s += `<g stroke="${FIG.grey}" stroke-width="0.8" ${NS}><line x1="${dx.toFixed(2)}" y1="${Y(0).toFixed(2)}" x2="${dx.toFixed(2)}" y2="${Y(D).toFixed(2)}"/>`
     + `<line x1="${(dx - tick).toFixed(2)}" y1="${(Y(0) + tick).toFixed(2)}" x2="${(dx + tick).toFixed(2)}" y2="${(Y(0) - tick).toFixed(2)}"/>`
     + `<line x1="${(dx - tick).toFixed(2)}" y1="${(Y(D) + tick).toFixed(2)}" x2="${(dx + tick).toFixed(2)}" y2="${(Y(D) - tick).toFixed(2)}"/></g>`;
  const rx = dx + fs * 0.95, ry = Y(D / 2);
  s += `<text x="${rx.toFixed(2)}" y="${ry.toFixed(2)}" font-size="${fs.toFixed(2)}" text-anchor="middle" fill="${FIG.grey}" ${halo(fs)} transform="rotate(90 ${rx.toFixed(2)} ${ry.toFixed(2)})">depth ${h(D)} m</text>`;
  s += scaleBar(fs * 1.4, vbH - fs * 0.9, x1 - x0, fs);
  if (ctx.osm && ctx.osm.bearing != null) s += northArrow(vbW - fs * 2.2, fs * 2.4, ctx.osm.bearing, fs);
  s += `</svg>`;
  return s;
}

function figSection(m, fsIn = null) {
  const W = m.lot.frontage_m;
  const masses = Object.fromEntries(m.masses.map(x => [x.name, x]));
  let hmax = Math.max(...m.masses.map(x => x.height_m), 1);
  const b = m.policy_benchmark;
  if (b && b.height_m) hmax = Math.max(hmax, b.height_m[1]);
  const pad = Math.max(4, W * 0.07);
  const fs = fsIn || Math.max(2.2, W / 34);
  const labelRoom = Math.max(W * 0.25, fs * 19);   // room for "19.9 to 21.3 m · staff benchmark" at the label size
  const vbW = W + 2 * pad + labelRoom, vbH = hmax + pad + fs * 2.2;
  const ground = fs * 1.2 + hmax;
  const Yz = z => ground - z;
  const envX = pad + (m.envelope.setbacks_m.side || 0), envW = m.envelope.width_m;
  let s = `<svg ${SVG_OPEN} viewBox="0 0 ${vbW.toFixed(2)} ${vbH.toFixed(2)}" aria-label="Section across the frontage: outright and proposed heights with the staff benchmark">`;
  s += `<line x1="${(pad - 2).toFixed(2)}" y1="${ground.toFixed(2)}" x2="${(pad + W + 2).toFixed(2)}" y2="${ground.toFixed(2)}" stroke="${FIG.lot}" stroke-width="1.2" ${NS}/>`;
  // as in plan: the proposed mass, then the outright one over it as a heavy dashed outline, so both read
  if (masses.proposed) {
    const p = masses.proposed;
    s += `<rect x="${envX.toFixed(2)}" y="${Yz(p.height_m).toFixed(2)}" width="${envW.toFixed(2)}" height="${p.height_m}" fill="${FIG.proposedFill}" fill-opacity="0.45" stroke="${FIG.proposedStroke}" stroke-width="1.2" ${NS}/>`;
    for (let k = 1; k < p.storeys; k++) {
      const yk = Yz(k * p.floor_to_floor_m);
      if (yk <= Yz(p.height_m)) break;
      s += `<line x1="${envX.toFixed(2)}" y1="${yk.toFixed(2)}" x2="${(envX + envW).toFixed(2)}" y2="${yk.toFixed(2)}" stroke="${FIG.proposedStroke}" stroke-width="0.6" stroke-opacity="0.6" ${NS}/>`;
    }
  }
  if (masses.outright) {
    const o = masses.outright;
    s += `<rect x="${envX.toFixed(2)}" y="${Yz(o.height_m).toFixed(2)}" width="${envW.toFixed(2)}" height="${o.height_m}" fill="${FIG.outrightFill}" fill-opacity="${masses.proposed ? 0.35 : 0.9}" stroke="${FIG.outrightStroke}" stroke-width="2" stroke-dasharray="6 3" ${NS}/>`;
  }
  const lx = pad + W + fs * 0.8;
  if (b && b.height_m) {
    for (const z of b.height_m) {
      s += `<line x1="${pad.toFixed(2)}" y1="${Yz(z).toFixed(2)}" x2="${(pad + W).toFixed(2)}" y2="${Yz(z).toFixed(2)}" stroke="${FIG.bench}" stroke-width="1" stroke-dasharray="4 3" ${NS}/>`;
    }
  }
  // the height labels beside the frontage, each at its own height, then pushed down where two would overprint, so
  // a proposed height just under the benchmark still reads; a short leader joins a moved label to its line
  const tags = [];
  if (b && b.height_m) tags.push({ at: Yz(b.height_m[0]), y: Yz(b.height_m[0]) + fs * 1.05, fill: FIG.benchText, text: `${h(b.height_m[0])} to ${h(b.height_m[1])} m · staff benchmark` });
  if (masses.proposed) tags.push({ at: Yz(masses.proposed.height_m), y: Yz(masses.proposed.height_m) - fs * 0.35, fill: FIG.proposedStroke, weight: 600, text: `${h(masses.proposed.height_m)} m · proposed` });
  if (masses.outright) tags.push({ at: Yz(masses.outright.height_m), y: Yz(masses.outright.height_m) - fs * 0.35, fill: FIG.lot, text: `${h(masses.outright.height_m)} m · outright` });
  tags.sort((u, v) => u.y - v.y);
  for (let k = 1; k < tags.length; k++) tags[k].y = Math.max(tags[k].y, tags[k - 1].y + fs * 1.5);
  for (const t of tags) {
    const moved = Math.abs(t.y - (t.at - fs * 0.35)) > fs * 0.5 && Math.abs(t.y - (t.at + fs * 1.05)) > fs * 0.5;
    if (moved) s += `<line x1="${(pad + W).toFixed(2)}" y1="${t.at.toFixed(2)}" x2="${(lx - fs * 0.25).toFixed(2)}" y2="${(t.y - fs * 0.35).toFixed(2)}" stroke="${t.fill}" stroke-width="0.6" ${NS}/>`;
    s += `<text x="${lx.toFixed(2)}" y="${t.y.toFixed(2)}" font-size="${fs}" fill="${t.fill}"${t.weight ? ` font-weight="${t.weight}"` : ""}>${t.text}</text>`;
  }
  // the note under the ground line starts at the lot's edge, so a narrow figure runs it into the label room instead
  // of cutting it off on the left
  s += `<text x="${pad.toFixed(2)}" y="${(ground + fs * 1.3).toFixed(2)}" font-size="${fs}" fill="${FIG.grey}">heights in metres · setback envelope ${h(m.envelope.width_m)} m wide</text>`;
  s += `</svg>`;
  return s;
}

/* FIG 01 in three dimensions: an orbitable axonometric of the lot, the setback envelope and the two masses, drawn
   from the same massing.json. The camera turns about the lot's centre; azimuth and elevation live in VIEW3D so the
   view survives a re-render. No library: the boxes are projected and painted far to near. */
const VIEW3D = { mode: "plan", az: 35, el: 28 };

function fig3d(m, ctx, az = VIEW3D.az, el = VIEW3D.el, fsIn = null) {
  const W = m.lot.frontage_m, D = m.lot.depth_m;
  const masses = Object.fromEntries(m.masses.map(x => [x.name, x]));
  const a = az * Math.PI / 180, e = el * Math.PI / 180;
  const ca = Math.cos(a), sa = Math.sin(a), ce = Math.cos(e), se = Math.sin(e);
  const cx = W / 2, cy = D / 2;
  const fs = fsIn || Math.max(2.2, Math.max(W, D) / 34);
  // metres to the picture plane; y runs away from the street, z up; the viewer starts on the street side
  const proj = ([x, y, z = 0]) => {
    const rx = (x - cx) * ca - (y - cy) * sa, ry = (x - cx) * sa + (y - cy) * ca;
    return { x: rx, y: -(z * ce + ry * se), d: ry * ce - z * se };
  };
  const poly = (ring, attrs) => {
    const P = ring.map(proj);
    return `<polygon points="${P.map(p => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ")}" ${attrs} ${NS}/>`;
  };
  const line = (p, q, attrs) => {
    const A = proj(p), B = proj(q);
    return `<line x1="${A.x.toFixed(2)}" y1="${A.y.toFixed(2)}" x2="${B.x.toFixed(2)}" y2="${B.y.toFixed(2)}" ${attrs} ${NS}/>`;
  };
  // a tree as a lollipop: a stem and a crown, in the half tone
  const tree = (t, opacity) => {
    const top = (t.crown * 1.4) + 2.5, c = proj([t.x, t.y, top]);
    return line([t.x, t.y, 0], [t.x, t.y, top], `stroke="${HALF.treeLine}" stroke-width="0.8"`) +
      `<circle cx="${c.x.toFixed(2)}" cy="${c.y.toFixed(2)}" r="${t.crown}" fill="${HALF.tree}" fill-opacity="${opacity}" stroke="${HALF.treeLine}" stroke-width="0.6" ${NS}/>`;
  };
  // a box from a footprint ring: the top and the four sides, painted far to near
  const box = (ring, z0, z1, fill, stroke, opacity, floors) => {
    const faces = [];
    const n = ring.length;
    for (let i = 0; i < n; i++) {
      const p = ring[i], q = ring[(i + 1) % n];
      faces.push({ ring: [[p[0], p[1], z0], [q[0], q[1], z0], [q[0], q[1], z1], [p[0], p[1], z1]], side: [p, q] });
    }
    faces.push({ ring: ring.map(([x, y]) => [x, y, z1]), top: true });
    for (const f of faces) f.depth = f.ring.reduce((s, p) => s + proj(p).d, 0) / f.ring.length;
    faces.sort((u, v) => v.depth - u.depth);
    let s = "";
    for (const f of faces) {
      s += poly(f.ring, `fill="${fill}" fill-opacity="${f.top ? Math.min(1, opacity + 0.15) : opacity}" stroke="${stroke}" stroke-width="1" stroke-linejoin="round"`);
      if (floors && f.side) {
        for (let k = 1; k < floors.storeys; k++) {
          const z = z0 + k * floors.f2f;
          if (z >= z1) break;
          s += line([f.side[0][0], f.side[0][1], z], [f.side[1][0], f.side[1][1], z], `stroke="${stroke}" stroke-width="0.6" stroke-opacity="0.5"`);
        }
      }
    }
    return s;
  };
  let body = "";
  // the context on the ground first, in half tone, then the lot, the envelope, the masses and the trees
  if (ctx.osm) body += poly([[ctx.xmin, ctx.ymin], [ctx.xmax, ctx.ymin], [ctx.xmax, ctx.ymax], [ctx.xmin, ctx.ymax]], `fill="${HALF.parcel}" stroke="none"`);
  for (const g of ctx.ground) body += poly(g.ring, g.seam ? `fill="${g.fill}" stroke="${g.fill}" stroke-width="0.6" stroke-linejoin="round"` : `fill="${g.fill}" stroke="${HALF.line}" stroke-width="0.8"${g.dash ? ` stroke-dasharray="3 2"` : ""}`);
  body += poly(m.lot.polygon, `fill="#ffffff" stroke="${FIG.lot}" stroke-width="1.2"`);
  body += poly(m.envelope.polygon, `fill="none" stroke="${FIG.env}" stroke-width="1" stroke-dasharray="4 3"`);
  // the buildings around, the trees and the masses are painted far to near so a tree behind a mass stays behind it
  const items = [];
  for (const b of ctx.buildings) {
    const depth = b.polygon.reduce((s, [x, y]) => s + proj([x, y, 0]).d, 0) / b.polygon.length;
    items.push({ d: depth, s: box(b.polygon, 0, b.height, HALF.building, HALF.line, 0.95, null) });
  }
  for (const t of ctx.streetTrees.concat(ctx.osmTrees)) items.push({ d: proj([t.x, t.y, 0]).d, s: tree(t, 0.35) });
  for (const t of ctx.trees) if (t.retained) items.push({ d: proj([t.x, t.y, 0]).d, s: tree(t, 0.45) });
  if (masses.outright) items.push({ d: -1e9, s: box(masses.outright.footprint, masses.outright.base_z || 0, (masses.outright.base_z || 0) + masses.outright.height_m, FIG.outrightFill, FIG.outrightStroke, 0.9, null) });
  if (masses.proposed) {
    const p = masses.proposed;
    const depth = p.footprint.reduce((s, [x, y]) => s + proj([x, y, 0]).d, 0) / p.footprint.length;
    items.push({ d: depth, s: box(p.footprint, p.base_z || 0, (p.base_z || 0) + p.height_m, FIG.proposedFill, FIG.proposedStroke, 0.45, { storeys: p.storeys, f2f: p.floor_to_floor_m }) });
  }
  // the outright mass sits inside the proposed one: paint it right before the proposed box
  const prop = items.find(i => i.d !== -1e9 && i.s.includes(FIG.proposedFill));
  for (const i of items) if (i.d === -1e9) i.d = prop ? prop.d + 1e-6 : 0;
  items.sort((u, v) => v.d - u.d);
  body += items.map(i => i.s).join("");
  // the street names last, over the buildings around, with a paper halo, so none is hidden behind a block
  for (const l of ctx.labels) {
    const c = proj(l.at);
    body += `<text x="${c.x.toFixed(2)}" y="${(c.y + fs * 0.35).toFixed(2)}" font-size="${(fs * 0.9).toFixed(2)}" text-anchor="middle" fill="${l.strong ? FIG.grey : HALF.text}"${l.strong ? ` font-weight="600"` : ""} ${halo(fs)}>${h(l.text)}</text>`;
  }
  const b = m.policy_benchmark;
  if (b && b.height_m && masses.proposed) {
    for (const z of b.height_m) body += poly(masses.proposed.footprint.map(([x, y]) => [x, y, z]), `fill="none" stroke="${FIG.bench}" stroke-width="1" stroke-dasharray="4 3"`);
  }
  // labels: the heights, led off the near top corner of each mass so they sit beside the building, not on its faces
  const labels = [];
  const nearest = ring => ring.map(([x, y]) => [x, y]).sort((u, v) => proj(u).d - proj(v).d)[0];
  // every corner of every mass on the picture plane, so the labels can stand clear of all of them
  const pts = [];
  for (const x of m.masses) for (const [px, py] of x.footprint) for (const z of [x.base_z || 0, (x.base_z || 0) + x.height_m]) pts.push(proj([px, py, z]));
  const minX = Math.min(...pts.map(p => p.x)), maxX = Math.max(...pts.map(p => p.x));
  let lastY = null;
  for (const [name, colour, weight] of [["proposed", FIG.proposedStroke, 600], ["outright", FIG.lot, 400]]) {
    const x = masses[name]; if (!x) continue;
    const c = nearest(x.footprint); const t = proj([c[0], c[1], (x.base_z || 0) + x.height_m]);
    const side = t.x < 0 ? -1 : 1;                       // out on the side the near corner is on
    const lx = side < 0 ? minX - fs * 0.9 : maxX + fs * 0.9;
    let ly = t.y + fs * 0.35;
    if (lastY != null && Math.abs(ly - lastY) < fs * 1.4) ly = lastY + fs * 1.4;
    lastY = ly;
    labels.push(`<line x1="${t.x.toFixed(2)}" y1="${t.y.toFixed(2)}" x2="${(lx - side * fs * 0.3).toFixed(2)}" y2="${(ly - fs * 0.35).toFixed(2)}" stroke="${colour}" stroke-width="0.8" ${NS}/>`
      + `<circle cx="${t.x.toFixed(2)}" cy="${t.y.toFixed(2)}" r="${(fs * 0.18).toFixed(2)}" fill="${colour}"/>`
      + `<text x="${lx.toFixed(2)}" y="${ly.toFixed(2)}" font-size="${fs.toFixed(2)}" font-weight="${weight}" fill="${colour}" text-anchor="${side < 0 ? "end" : "start"}" ${halo(fs)}>${h(x.height_m)} m · ${name}</text>`);
  }
  // a steady frame: the largest extent the drawing can reach at any azimuth for this tilt, so turning never
  // rescales it (only a change of tilt re-frames, and gently)
  const corners = [[ctx.xmin, ctx.ymin], [ctx.xmax, ctx.ymin], [ctx.xmax, ctx.ymax], [ctx.xmin, ctx.ymax]];
  const R = ctx.frameRadius || Math.max(...corners.map(([x, y]) => Math.hypot(x - cx, y - cy)));
  const zmax = Math.max(...m.masses.map(x => (x.base_z || 0) + x.height_m), 1);
  const top = zmax * ce + R * se, bottom = R * se;
  const pad = fs * 1.5;
  const x0 = -R - pad - fs * 3, x1 = R + pad + fs * 3, y0 = -top - pad - fs, y1 = bottom + pad;
  return `<svg ${SVG_OPEN} viewBox="${x0.toFixed(2)} ${y0.toFixed(2)} ${(x1 - x0).toFixed(2)} ${(y1 - y0).toFixed(2)}" tabindex="0" aria-label="Axonometric of the lot, its surroundings in half tone, the setback envelope and the two masses; drag or use the arrow keys to turn it">${body}${labels.join("")}</svg>`;
}

function figOne(m, ctx, fs = null) {
  const three = VIEW3D.mode === "3d";
  return `<div class="fig-head">
      <div class="eyebrow">FIG 01 · ${three ? "Axonometric" : "Plan"}</div>
      <div class="seg" role="group" aria-label="View of figure 1">
        <button type="button" class="segbtn" data-view="plan" aria-pressed="${!three}">Plan</button>
        <button type="button" class="segbtn" data-view="3d" aria-pressed="${three}">3D</button>
      </div>
    </div>
    <div class="fig-body${three ? " fig3d" : ""}">${three ? fig3d(m, ctx, VIEW3D.az, VIEW3D.el, fs) : figPlan(m, ctx, fs)}</div>
    ${three ? `<p class="fig-hint">Drag sideways to turn it; the arrow keys turn and tilt it. A straight axonometric of the same massing numbers, with storey lines every ${h(m.masses[0]?.floor_to_floor_m)} m.</p>` : ""}`;
}

let figWatch = null;   // the ResizeObserver that refits the drawings' labels when their cards change width

function wireFigures(run) {
  const fig = $("#fig-01");
  if (!fig || !run.massing) return;
  const m = run.massing;
  const ctx = siteContext(run.ledger && run.ledger.inputs && run.ledger.inputs.site, m);
  const fit = () => {
    const body = $(".fig-body", fig);
    if (body) VIEW3D.fs = fitLabels(body, fs => (VIEW3D.mode === "3d" ? fig3d(m, ctx, VIEW3D.az, VIEW3D.el, fs) : figPlan(m, ctx, fs)));
    const sec = $("#fig-02");
    if (sec) fitLabels(sec, fs => figSection(m, fs));
    wireOrbit();
  };
  const redraw = () => { fig.innerHTML = figOne(m, ctx); wireFigures(run); };
  $$(".segbtn", fig).forEach(b => b.addEventListener("click", () => {
    if (VIEW3D.mode === b.dataset.view) return;
    VIEW3D.mode = b.dataset.view;
    redraw();
    const now = $(`.segbtn[data-view="${VIEW3D.mode}"]`, fig);
    if (now) now.focus();
  }));

  // the axonometric turns under a drag (one redraw per frame) or the arrow keys
  function wireOrbit() {
    const svg = $(".fig3d svg", fig);
    if (!svg) return;
    const turn = (daz, del) => {
      VIEW3D.az = (VIEW3D.az + daz) % 360;
      VIEW3D.el = Math.max(8, Math.min(80, VIEW3D.el + del));
      const fresh = document.createElement("div"); fresh.innerHTML = fig3d(m, ctx, VIEW3D.az, VIEW3D.el, VIEW3D.fs);
      svg.innerHTML = fresh.firstElementChild.innerHTML;
      svg.setAttribute("viewBox", fresh.firstElementChild.getAttribute("viewBox"));
    };
    let drag = null, pending = [0, 0], raf = 0;
    const flush = () => { raf = 0; if (pending[0] || pending[1]) { turn(pending[0], pending[1]); pending = [0, 0]; } };
    const stop = () => { drag = null; };
    svg.addEventListener("pointerdown", e => {
      if (e.button > 0) return;
      drag = { x: e.clientX, y: e.clientY };
      svg.setPointerCapture(e.pointerId);
      svg.focus({ preventScroll: true });
      e.preventDefault();
    });
    svg.addEventListener("pointermove", e => {
      if (!drag) return;
      pending[0] += (e.clientX - drag.x) * 0.5;
      pending[1] += (e.clientY - drag.y) * 0.4;
      drag = { x: e.clientX, y: e.clientY };
      if (!raf) raf = requestAnimationFrame(flush);
    });
    for (const ev of ["pointerup", "pointercancel", "lostpointercapture"]) svg.addEventListener(ev, stop);
    window.addEventListener("blur", stop, { once: true });
    svg.addEventListener("keydown", e => {
      const k = { ArrowLeft: [-6, 0], ArrowRight: [6, 0], ArrowUp: [0, 4], ArrowDown: [0, -4] }[e.key];
      if (k) { e.preventDefault(); turn(k[0], k[1]); }
    });
  }

  fit();
  // refit when the cards change width: a window resize, the inputs hidden or shown, the wide two-column layout
  if (figWatch) figWatch.disconnect();
  const figures = $(".figures");
  if (figures && "ResizeObserver" in window) {
    let w = Math.round(figures.getBoundingClientRect().width), raf = 0;
    figWatch = new ResizeObserver(entries => {
      const nw = Math.round(entries[0].contentRect.width);
      if (Math.abs(nw - w) < 4) return;
      w = nw;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(fit);
    });
    figWatch.observe(figures);
  }
}

function massLine(x) {
  return `<b>${h(x.label)}</b>: plate ${fmtNum(x.plate_area_m2)} m² × ${x.storeys} = ${fmtNum(x.gfa_m2)} m² (FSR ${Number(x.fsr).toFixed(2)}), ${h(x.height_m)} m high.`;
}

function renderFigures(run) {
  const m = run.massing;
  const out = [];
  if (m) {
    const sb = m.envelope.setbacks_m || {};
    const ctx = siteContext(run.ledger && run.ledger.inputs && run.ledger.inputs.site, m);
    let contextNote;
    if (ctx.osm) {
      const c = ctx.osm.counts, om = ctx.osm.omitted;
      contextNote = `Context in half tone from OpenStreetMap (${h(ctx.osm.attribution)}; fetched ${h(ctx.osm.fetched)}, ${h(ctx.osm.radius)} m around the address): ${c.roads ?? 0} roads, ${c.buildings ?? 0} buildings and ${c.trees ?? 0} mapped trees, with ${h(ctx.osm.frontStreet || "the nearest road")} taken as the front street.${om.length ? ` ${om.length === 1 ? "The building now on the lot is" : `${om.length} buildings now on the lot are`} left out${om[0] && om[0].name ? ` (${h(om.map(b => b.name).filter(Boolean).join(", "))})` : ""}.` : ""}`;
    } else {
      const around = [ctx.street.name + " in front"];
      if (ctx.lane) around.push("a lane behind");
      for (const x of ctx.cross) around.push(`${x.name} to the ${x.side}`);
      if (ctx.neighbours.length) around.push(ctx.neighbours.length === 2 ? "neighbouring parcels either side" : "a neighbouring parcel");
      if (ctx.streetTrees.length) around.push(`${ctx.streetTrees.length} street trees`);
      contextNote = `Context in half tone, schematic: ${h(around.join(", "))}. Run <code>python -m ffm context --site sites/${h(m.site_id)}.json</code> to draw it from OpenStreetMap instead.`;
    }
    const retained = ctx.trees.filter(t => t.retained).length, removed = ctx.trees.length - retained;
    const treeNote = ctx.trees.length ? ` On site, ${retained} tree${retained === 1 ? "" : "s"} retained and ${removed} to be removed (×)${ctx.schematic ? ", placed schematically because the survey is not on file" : ""}.` : "";
    out.push(`<figure class="card figure">
      <div id="fig-01">${figOne(m, ctx)}</div>
      <div class="legend"><span><i class="fig-proposed"></i>proposed</span><span><i class="fig-outright"></i>outright</span><span><i class="fig-env"></i>setback envelope</span><span><i class="fig-tree"></i>tree</span><span><i class="fig-building"></i>building</span><span><i class="fig-context"></i>road</span></div>
      <figcaption>Lot ${h(m.lot.frontage_m)} × ${h(m.lot.depth_m)} m, ${fmtNum(m.lot.area_m2)} m². Setback envelope ${h(m.envelope.width_m)} × ${h(m.envelope.depth_m)} m (front ${h(sb.front)}, rear ${h(sb.rear)}, sides ${h(sb.side)} m). Both masses fill the envelope's width from the front setback back, so the outright mass is drawn dashed over the proposed one, here and in the section. ${contextNote}${treeNote}${ctx.osm && ctx.osm.bearing != null ? " The north arrow follows the OpenStreetMap frame; the plan is drawn with the street at the bottom." : ""}</figcaption>
    </figure>`);
    const bench = m.policy_benchmark;
    const trees = m.trees;
    out.push(`<figure class="card figure">
      <div class="eyebrow">FIG 02 · Section across the frontage</div>
      <div class="fig-section" id="fig-02">${figSection(m)}</div>
      <div class="legend"><span><i class="fig-proposed"></i>proposed</span><span><i class="fig-outright"></i>outright</span>${bench && bench.height_m ? `<span><i class="fig-bench"></i>staff benchmark</span>` : ""}</div>
      <figcaption>${m.masses.map(massLine).join(" ")}${bench && bench.height_m ? ` Staff benchmark under <code>${h(bench.rule_id)}</code>: ${h(bench.height_m[0])} to ${h(bench.height_m[1])} m, about FSR ${h(bench.fsr)}.` : ""}${trees ? ` Trees: Schedule C requires ${h(trees.required)}, the plan leaves ${h(trees.after)} (shortfall ${h(trees.shortfall)}).` : ""}</figcaption>
      ${(m.warnings || []).map(w => `<p class="note">${h(String(w).replace(/(\d) x (\d)/g, "$1 × $2"))}</p>`).join("")}
    </figure>`);
  } else if (run.massing_note) {
    out.push(`<div class="card figure"><div class="eyebrow">Massing</div><p class="note">${h(run.massing_note)}</p></div>`);
  }
  const r = run.revit;
  if (r && r.sheet_png) out.push(figSheet(run));
  return `<aside class="figures">${out.join("")}</aside>`;
}

function figSheet(run) {
  const r = run.revit, c = r.counts || {};
  const base = `/api/runs/${run.run_id}`;
  const stages = Object.entries(r.stages || {}).map(([k, v]) => `${k} ${v}`).join(", ");
  return `<figure class="card figure">
    <div class="eyebrow">FIG 03 · Revit sheet ${h(r.sheet_number || "")}</div>
    <a href="${base}/ffm_sheet.png" target="_blank" rel="noopener"><img src="${base}/ffm_sheet.png" alt="The Revit sheet exported by the massing script"></a>
    <figcaption><b>${c.masses ?? "?"} masses</b>, ${c.floor_plates ?? "?"} floor plates, ${c.model_lines ?? "?"} model lines, ${c.views ?? "?"} views, ${c.dimensions ?? 0} dimensions and ${c.notes ?? 0} notes on sheet ${h(r.sheet_number || "")}; the fingerprint of rules ${h(rev(run.stamp))} in every element's Comments. Stages: ${h(stages)}.${r.sheet_pdf ? ` <a href="${base}/ffm_sheet.pdf" target="_blank" rel="noopener">PDF</a>.` : ""}${r.errors ? ` ${r.errors} stage error(s) recorded in the result file.` : ""}</figcaption>
  </figure>`;
}

// ---------------------------------------------------------------- what changed

/* The engine's words for a change (engine.diff), as a reader would say them. Between two options read under the same
   rules a reworded finding is the option's numbers changing, not the rule. */
function changeWord(c, kind = "rules") {
  if (c.change === "changed") return c.from_version !== c.to_version ? (c.from === c.to ? "new version" : "new version and status") : "status changed";
  if (c.change === "finding_changed") return kind === "rules" ? "finding reworded" : "numbers changed";
  return { added: "rule added", removed: "rule dropped" }[c.change] || String(c.change).replace(/_/g, " ");
}

/* A comparison in a few words for the status strip: how many statuses and versions moved, without the rule ids. */
function changesPhrase(d) {
  const ch = d.changes || [];
  if (!ch.length) return "no rule changed version or status";
  const st = ch.filter(c => c.from !== c.to).length;
  const ver = ch.filter(c => c.from_version && c.to_version && c.from_version !== c.to_version).length;
  const bits = [st && (st === 1 ? "1 status differs" : `${st} statuses differ`), ver && `${ver} new version${ver === 1 ? "" : "s"}`].filter(Boolean);
  return bits.length ? bits.join(", ") : `the same statuses, ${ch.length} finding${ch.length === 1 ? "" : "s"} with other numbers`;
}

/* An option's name up to its colon: "As approved by Council, 25 Jul 2024", not the description after it. */
const shortName = s => String(s || "").split(":")[0].trim();

/* What a comparison found, for the status strip and the toasts: the rules' dates when the rules moved, the compared
   option's name when two options were read under the same rules. */
function compareSummary(run) {
  const d = run.diff;
  if (!d) return "";
  return compareKind(d) === "rules"
    ? `rules as of ${d.current_as_of} against ${d.previous_as_of}: ${changesPhrase(d)} · ${rev(d.previous_stamp)} → ${rev(d.current_stamp)}`
    : `against ${run.compareLedger ? shortName(optionName(run.compareLedger)) : `a run as of ${d.previous_as_of}`}: ${changesPhrase(d)}`;
}

/* The note beside the pickers speaks only when the memo cannot: a comparison waiting for the next run, or a run
   recorded against an earlier one that the list cannot tell apart. Once two runs are compared, the Side by side
   card says it, so the note stays empty. */
function setCompareNote(d) {
  const run = state.run;
  let note = "";
  if (!run && state.compareRun) note = "Applies to the next run.";
  else if (run && d && !run.compareLedger) note = `This run was recorded against a run as of ${d.previous_as_of} (rules ${rev(d.previous_stamp)}); choose it under Compare with… to see the two side by side.`;
  $("#compare-note").textContent = note;
}

/* Why two stamps differ, as precisely as the two ledgers allow: the rule files, the as-of date, the site's or the
   option's inputs. The inputs are compared key by key, whatever their order. */
const stable = v => JSON.stringify(v, (k, x) => (x && typeof x === "object" && !Array.isArray(x) ? Object.fromEntries(Object.keys(x).sort().map(key => [key, x[key]])) : x));

async function attachCause(run) {
  const d = run.diff;
  if (!d || !state.compareRun) return;
  try {
    const [site, folder] = state.compareRun.split("/");
    const prev = await api(`/api/runs/${encodeURIComponent(site)}/${encodeURIComponent(folder)}`);
    run.compareLedger = prev.ledger || null;   // for the side-by-side card
    const a = (prev.ledger && prev.ledger.inputs) || {}, b = (run.ledger && run.ledger.inputs) || {};
    const changed = [stable(a.site) !== stable(b.site) && "the site's inputs", stable(a.option) !== stable(b.option) && "the option's inputs"].filter(Boolean);
    const date = d.previous_as_of !== d.current_as_of ? `the as-of date (${d.previous_as_of} → ${d.current_as_of})` : null;
    const files = d.rules_changed ? "the rule files changed" : "same rule files";
    const same = changed.length ? "" : ", same site and option";
    const because = [date, ...changed].filter(Boolean);
    d.cause = `${files}${same}; the difference is ${because.length ? because.join(" and ") : (d.rules_changed ? "in the rule files alone" : "not in the inputs or the date")}`;
    d.kind = d.rules_changed || date ? "rules" : changed.length ? "options" : "same";
  } catch (e) {
    d.cause = null;   // the earlier run could not be read: fall back to the general sentence
  }
}

/* What changed. When the rules moved it is a revision: the delta in its heading, the version in force on each row.
   Between two options read under the same rules it is the options' numbers, so the version column goes. Rows are
   named by the rule's title, the status read from the compared run (B) to this one (A). */
function renderChanges(d, L) {
  const kind = compareKind(d), rules = kind === "rules";
  const titles = Object.fromEntries(((L && L.results) || []).map(r => [r.rule_id, r.title]));
  const changes = d.changes || [];
  const rows = changes.map(c => {
    const ver = c.from_version && c.to_version && c.from_version !== c.to_version;
    const status = c.from && c.to ? (c.from === c.to ? `${pill(c.to)} <span class="cont">unchanged</span>` : `${pill(c.from)} → ${pill(c.to)}`) : (c.to ? pill(c.to) : c.from ? pill(c.from) : "—");
    return `<tr>
      <td data-label="Rule"><span class="rule-title">${h(titles[c.rule_id] || c.rule_id)}</span><code class="rule-id">${idBreak(c.rule_id)}</code><div class="cont">${h(changeWord(c, kind))}</div></td>
      ${rules ? `<td class="ver" data-label="Version in force">${ver ? `<span class="was">${h(c.from_version)}</span> → ${h(c.to_version)}` : h(c.to_version || c.from_version || "—")}</td>` : ""}
      <td class="trans" data-label="${rules ? "Status" : "Status, B → A"}">${status}</td>
      <td data-label="Now reads">${h(c.finding)}</td>
    </tr>`;
  }).join("");
  const sameVerdict = changes.length && changes.every(c => c.from === c.to && c.from_version && c.from_version !== c.to_version);
  const cause = d.cause || (d.rules_changed ? "the rule files themselves changed" : "the rule files are the same; the difference comes from the as-of date or the inputs");
  const lead = rules
    ? `Rules <b>${h(rev(d.previous_stamp))}</b> → <b>${h(rev(d.current_stamp))}</b> · ${h(cause)}.`
    : `Same rules, ${h(rev(d.current_stamp))}; ${h(cause.replace(/^same rule files(, same site and option)?; /, ""))}.`;
  return `<section class="card section changes" id="changes">
    <h2>${rules ? `${REV} What changed: rules as of ${h(d.current_as_of)} against ${h(d.previous_as_of)}` : "What changed between the two options"}</h2>
    <p class="stamps">${lead}</p>
    ${changes.length ? `${sameVerdict ? `<p class="same">Same verdict${changes.length === 1 ? "" : "s"}, new version${changes.length === 1 ? "" : "s"}: the memo names the version it used.</p>` : ""}
    <table class="plain"><thead><tr><th>Rule</th>${rules ? "<th>Version in force</th><th>Status</th>" : "<th>Status, B → A</th>"}<th>Now reads</th></tr></thead><tbody>${rows}</tbody></table>`
    : `<p>No rule changed version or status between the two runs.</p>`}
  </section>`;
}

// ---------------------------------------------------------------- past runs: open, compare

/* A past run, as a reader picks it: the date, then a named folder (as-approved, what-if-…) where there is one, the
   option, the rules revision, and a timestamped folder last. A narrow picker still shows the first two. */
function runLabel(r) {
  const option = r.option_name || r.option_id || "option";
  const named = r.folder && r.folder !== r.as_of && !/^\d{4}-\d\d-\d\d/.test(r.folder);
  const stamped = r.folder && r.folder !== r.as_of && !named;
  return `${r.as_of} · ${named ? `${r.folder} · ` : ""}${option} · ${rev(r.stamp)}${stamped ? ` · ${r.folder}` : ""}${r.revit ? " · Revit" : ""}`;
}

function fillRunSelects() {
  const open = $("#open-run"), cmp = $("#compare-run");
  const cur = state.run ? state.run.run_id : "";
  // the open run is chosen in the list; a blank first entry only while no run, or one the list lacks, is on screen
  const listed = state.runs.some(r => r.run_id === cur);
  open.innerHTML = (listed ? "" : `<option value="">${state.run ? "This run" : "Choose a run…"}</option>`) +
    state.runs.map(r => `<option value="${h(r.run_id)}"${r.run_id === cur ? " selected" : ""}>${h(runLabel(r))}</option>`).join("");
  cmp.innerHTML = `<option value="">Nothing</option>` +
    state.runs.filter(r => r.run_id !== cur).map(r => `<option value="${h(r.run_id)}"${r.run_id === state.compareRun ? " selected" : ""}>${h(runLabel(r))}</option>`).join("");
}

async function openRun(runId) {
  if (!runId) return;
  const [site, folder] = runId.split("/");
  setStatus(`Opening the run ${runId}…`, "busy");
  const run = await api(`/api/runs/${encodeURIComponent(site)}/${encodeURIComponent(folder)}`);
  state.run = run;
  noteRevisions([run]);
  // the date in the top bar is the date of the memo on screen, and so of the next run
  $("#as-of").value = run.as_of;
  showStamp(run.stamp);
  enableExports(run);
  await syncInputsTo(run);
  // a run cannot be compared with itself; a run recorded against an earlier one opens compared with it, when the
  // list can tell which run that was
  const selfCompared = state.compareRun === runId;
  if (selfCompared) state.compareRun = null;
  if (!state.compareRun && run.diff) state.compareRun = recordedAgainst(run);
  if (state.compareRun) await applyCompare(false);
  renderMemo(run);
  fillRunSelects();
  setCompareNote(run.diff);
  setStep(3);
  closeExportPanel();
  setStatus(`Opened the run as of ${run.as_of} (${rev(run.stamp)}) · ${run.in_browser ? "kept in this browser tab" : `outputs/${run.run_id}/`}${run.diff ? ` · ${compareSummary(run)}` : ""}${selfCompared ? " · A and B were the same run, so the comparison was cleared" : ""}`, "ok");
}

/* The run a stored comparison (diff.json) was made against. The diff names only that run's date and rules stamp,
   and several runs can share both, so: the runs with that date and stamp, narrowed to one option (this run's own
   option first, as in a change of rules), then the named folder among them. Same option, date and rules give the
   same memo, so any of them is the run compared. Ambiguous between options: none, and the note says so. */
function recordedAgainst(run) {
  const d = run.diff;
  const hits = state.runs.filter(r => r.run_id !== run.run_id && r.as_of === d.previous_as_of && r.stamp === d.previous_stamp);
  const own = run.ledger && run.ledger.run && run.ledger.run.option_id;
  const options = [...new Set(hits.map(r => r.option_id))];
  const pick = options.length === 1 ? hits : hits.filter(r => r.option_id === own);
  if (!pick.length || new Set(pick.map(r => r.option_id)).size !== 1) return null;
  return (pick.find(r => !/^\d{4}-\d\d-\d\d/.test(r.folder || "")) || pick[0]).run_id;
}

/* An opened run shows its own site and option in the inputs, unless the reader has unsaved edits there. */
async function syncInputsTo(run) {
  if (state.siteDirty || state.optionDirty) return;
  const siteId = run.run_id.split("/")[0];
  const optId = run.ledger && run.ledger.run && run.ledger.run.option_id;
  if (optId) state.optionId = optId;
  if (state.siteId !== siteId && state.sites.some(s => s.id === siteId)) {
    $("#site-select").value = siteId;
    await selectSite(siteId);
  } else if (optId && state.options.some(o => o.id === optId) && $("#option-select").value !== optId) {
    $("#option-select").value = optId;
    await selectOption(optId);
  }
}

async function applyCompare(render = true) {
  const run = state.run;
  const note = $("#compare-note");
  if (!run) {
    note.textContent = state.compareRun ? "Applies to the next run." : "";
    if (render) setStatus(state.compareRun ? `The next run will be compared with ${state.compareRun}.` : "No comparison.", "info");
    return;
  }
  // the same run on both sides is no comparison: clear it, so the picker and the memo agree, and say why
  const selfCompared = state.compareRun === run.run_id;
  if (selfCompared) state.compareRun = null;
  if (!state.compareRun) {
    run.diff = null;
    run.compareLedger = null;
  } else {
    if (render) setStatus("Comparing the two runs…", "busy");
    run.diff = await api(`/api/diff?from=${encodeURIComponent(state.compareRun)}&to=${encodeURIComponent(run.run_id)}`);
    await attachCause(run);
  }
  setCompareNote(run.diff);
  if (render) {
    renderMemo(run);
    if (run.diff) {
      setStatus(`Compared ${compareSummary(run)}`, "ok");
      const box = $("#side-by-side") || $("#changes");
      if (box) box.scrollIntoView({ behavior: scrollBehavior(), block: "start" });
    } else {
      fillRunSelects();
      setStatus(selfCompared ? "A and B were the same run, so the comparison was cleared; the run pickers are back above the memo."
        : "Comparison cleared; the run pickers are back above the memo.", "info");
    }
  }
}

// ---------------------------------------------------------------- export to Revit

function psLines(run) {
  const f = run.files || {};
  return [
    `$env:FFM_MASSING_JSON = "${f.massing_json || "C:\\path\\to\\the-downloaded\\massing.json"}"`,
    `$env:FFM_SAVE_AS      = "${(run.folder_abs || "C:\\path\\to\\the-downloaded")}\\ffm_massing.rvt"`,
    `# $env:FFM_TEMPLATE   = "C:\\path\\to\\your-office-template.rte"   # optional; default is Revit's metric template`,
    `pyrevit run "${f.script || "revit\\ffm_massing_pyrevit.py"}" --revit=2026   # the year 'pyrevit env' reports`,
  ].join("\n");
}

function renderExportPanel(run) {
  const f = run.files || {};
  const panel = $("#export-panel");
  panel.innerHTML = `
    <h3>Export to Revit</h3>
    <div class="block">
      <span class="eyebrow">This run's massing.json</span>
      <div class="codeline"><code class="path" id="exp-path">${h(f.massing_json || (STATIC ? "Download massing.json from the action bar above and save it next to this run's ledger.json on the machine that has Revit." : "This run has no massing.json."))}</code><button class="btn btn-quiet btn-small" type="button" data-copy="exp-path">Copy</button></div>
    </div>
    <div class="block">
      <span class="eyebrow">Headless, through the pyRevit CLI (PowerShell, Revit closed)</span>
      <div class="codeline"><pre id="exp-ps">${h(psLines(run))}</pre><button class="btn btn-quiet btn-small" type="button" data-copy="exp-ps">Copy</button></div>
      <p>About a minute. It creates a project, builds the masses, views, annotations and sheet FFM-01, exports the sheet as PDF and PNG next to the massing.json, saves the .rvt, and writes ffm_revit_result.json.</p>
    </div>
    <div class="block">
      <span class="eyebrow">Inside Revit</span>
      <p>pyRevit › Tools › Run, pick <code>revit/ffm_massing_pyrevit.py</code>, and choose this run's massing.json in the dialog (or set FFM_MASSING_JSON before starting Revit). Open sheet FFM-01 from the Project Browser.</p>
    </div>
    <div class="block">
      <span class="eyebrow">Result</span>
      ${STATIC ? `<p>The Revit step runs on a machine with Revit. Its result and the sheet image appear here when the page is served there with <code>python -m ffm ui</code>.</p>`
               : `<div><button id="check-revit" class="btn" type="button">Check Revit result</button></div><div id="revit-result" class="revit-result"></div>`}
    </div>`;
  panel.hidden = false;
  $("#revit-btn").setAttribute("aria-expanded", "true");
  $$("[data-copy]", panel).forEach(b => b.addEventListener("click", () => copyText($("#" + b.dataset.copy).textContent)));
  if (!STATIC) {
    $("#check-revit").addEventListener("click", checkRevit);
    if (run.revit) checkRevit();
  }
}

function closeExportPanel() {
  $("#export-panel").hidden = true;
  $("#revit-btn").setAttribute("aria-expanded", "false");
}

async function checkRevit() {
  const run = state.run;
  if (!run) return;
  const box = $("#revit-result");
  box.innerHTML = `<p class="cont">Reading ffm_revit_result.json…</p>`;
  setStatus("Reading the Revit result for this run…", "busy");
  try {
    const r = await api(`/api/runs/${run.run_id}/ffm_revit_result.json`);
    if (r.stamp !== run.stamp) {
      box.innerHTML = `<p class="err">A result exists in this folder but for rules ${h(rev(r.stamp))}, not this run's ${h(rev(run.stamp))}. Run the script again on this folder.</p>`;
      setStatus(`The Revit result in this folder is for rules ${rev(r.stamp)}, not ${rev(run.stamp)}: run the script again on this folder.`, "error");
      return;
    }
    const refreshed = await postJSON(`/api/runs/${run.run_id}/memo`, {});   // memo gains its "Built in Revit" section
    run.revit = refreshed.revit;
    box.innerHTML = revitResultHtml(r, run);
    renderMemo(run);
    const bad = Object.entries(r.stages || {}).filter(([, v]) => v !== "ok").map(([k]) => k);
    setStatus(bad.length ? `Read the Revit result: stages ${bad.join(", ")} did not finish; the others stand.` : `Read the Revit result: every stage ok, and the memo now has its "Built in Revit" section.`, bad.length ? "error" : "ok");
  } catch (e) {
    box.innerHTML = `<p class="cont">${h(e.message)} Nothing built for this run yet: run the script, then check again.</p>`;
    setStatus("No Revit result for this run yet: run the script, then check again.", "info");
  }
}

function revitResultHtml(r, run) {
  const base = `/api/runs/${run.run_id}`;
  const stages = Object.entries(r.stages || {}).map(([k, v]) => `<span class="pill pill-${v === "ok" ? "pass" : "fail"}">${h(k)}</span>`).join("");
  const items = (r.built || []).map(b => {
    switch (b.kind) {
      case "mass": return `Mass <b>${h(b.name)}</b> (element ${h(b.element_id)}): ${h(b.storeys)} storeys, ${h(b.height_m)} m, plate ${fmtNum(b.plate_area_m2)} m², FSR ${h(b.fsr)}.`;
      case "floor plates": return `Floor plates: ${h(b.count)}.`;
      case "model lines": return `Model lines: lot ${h(b.lot)}, setback envelope ${h(b.envelope)}.`;
      case "view": return `View ${h(b.name)} (element ${h(b.element_id)}).`;
      case "annotations": return `Annotations: ${h(b.dimensions)} dimensions, ${h(b.notes)} notes, ${h(b.section_lines)} benchmark lines.`;
      case "sheet": return `Sheet <b>${h(b.number)}</b> (element ${h(b.element_id)}), title block: ${b.title_block ? "yes" : "none in template"}.`;
      case "sheet layout": return `Views placed at 1:${h(b.scale)}.`;
      default: return null;
    }
  }).filter(Boolean);
  const exports = (r.exports || []).map(e => { const n = String(e).split(/[\\/]/).pop(); return `<a href="${base}/${h(n)}" target="_blank" rel="noopener">${h(n)}</a>`; }).join(", ");
  return `
    <div class="stages">${stages}</div>
    <ul>${items.map(i => `<li>${i}</li>`).join("")}${r.removed_links ? `<li>${r.removed_links.length} broken template link(s) removed before building.</li>` : ""}${r.saved_as ? `<li>Saved as <code>${h(r.saved_as)}</code>.</li>` : ""}${exports ? `<li>Exported ${exports}.</li>` : ""}</ul>
    ${r.errors && r.errors.length ? `<p class="err">${r.errors.length} stage error(s): ${r.errors.map(e => h(e.stage)).join(", ")}. The stages marked ok stand; the traceback is in ffm_revit_result.json.</p>` : ""}
    ${run.revit && run.revit.sheet_png ? `<a href="${base}/ffm_sheet.png" target="_blank" rel="noopener"><img src="${base}/ffm_sheet.png?t=${Date.now()}" alt="Revit sheet"></a>` : ""}`;
}

// ---------------------------------------------------------------- walkthrough: a spotlight over each step, in order

const TOUR = [
  { target: ".topbar-controls", title: "Rules as of",
    text: "Pick the date the rules should be read on. The engine applies the versions in force that day, and the memo names that reading of the rules as a revision, R1, R2 and so on, so two memos can be told apart." },
  { target: "#step-site", title: "Step 1 · Site",
    text: "Choose a site file; the card sums it up in a line. Edit opens the form: district, lot, policy areas, trees, owner. Where you are not sure, say so. The memo then reads uncertain instead of guessing." },
  { target: "#step-option", title: "Step 2 · Option",
    text: "The building: storeys, floor area, the unit mix, tenure, the funders you aim at, and the rezoning path if there is one. Edit to change it; save it as a file to rerun the same thing from the command line." },
  { target: "#run-btn", title: "Run the rules", action: "run",
    text: "One click, or Ctrl+Enter. In under a second the engine writes the memo to the outputs folder and reads it here." },
  { target: ".answers", fallback: "#memo", title: "Step 3 · The three answers",
    text: "Is it allowed? Does it fit the funders? What is still unsure, and who resolves it? Every finding prints the numbers it used and links the clause it came from." },
  { target: ".figures", fallback: "#memo", title: "The massing",
    text: "Plan and section drawn from the same numbers as the memo, with the staff benchmark. When the Revit script has run on this folder, the sheet it built appears as a third figure." },
  { target: ".ledger", fallback: "#memo", title: "The full ledger",
    text: "Every rule the engine ran, by layer, collapsed until you open it: status, finding, numbers used and the source link." },
  { target: ".memo-tools:not([hidden]), #side-by-side .pick-row", title: "Past runs",
    text: "Open an earlier run, or compare two. The two runs then sit side by side under the title block, these pickers heading their columns, and What changed follows with a revision mark: the rule, its old and new version, and the new rules revision." },
  { target: "#step-export", title: "Step 4 · Export",
    text: "Download the memo as HTML or Markdown, print it, take the massing file, or open Export to Revit for the two lines that build the sheet." },
];
const TOUR_KEY = "ffm.walkthrough.seen";
const tour = { active: false, i: 0, spot: null, card: null, raf: 0, timer: 0, returnTo: null };

function tourTarget(step) {
  return document.querySelector(step.target) || (step.fallback ? document.querySelector(step.fallback) : null);
}

function reducedMotion() {
  return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function startTour(at = 0) {
  if (tour.active) endTour();
  tour.active = true;
  tour.returnTo = document.activeElement && document.activeElement !== document.body ? document.activeElement : $("#tour-link");
  tour.spot = document.createElement("div");
  tour.spot.className = "tour-spot";
  tour.card = document.createElement("div");
  tour.card.className = "tour-card";
  tour.card.setAttribute("role", "dialog");
  tour.card.setAttribute("aria-modal", "true");
  tour.card.setAttribute("aria-labelledby", "tour-title");
  tour.card.setAttribute("aria-describedby", "tour-text");
  document.body.append(tour.spot, tour.card);
  $("#tour-offer").hidden = true;
  showTourStep(at);
  window.addEventListener("resize", positionTourSoon);
  window.addEventListener("scroll", positionTourSoon, { passive: true });
  document.addEventListener("keydown", tourKeys);
}

function endTour() {
  if (!tour.active) return;
  tour.active = false;
  tour.spot.remove(); tour.card.remove();
  tour.spot = tour.card = null;
  cancelAnimationFrame(tour.raf);
  clearTimeout(tour.timer);
  window.removeEventListener("resize", positionTourSoon);
  window.removeEventListener("scroll", positionTourSoon);
  document.removeEventListener("keydown", tourKeys);
  try { localStorage.setItem(TOUR_KEY, "1"); } catch (e) { /* private window: fine */ }
  // focus goes back where it was before the walkthrough
  const back = tour.returnTo;
  tour.returnTo = null;
  if (back && document.contains(back) && typeof back.focus === "function") back.focus({ preventScroll: true });
}

function tourKeys(e) {
  if (e.key === "Escape") { e.preventDefault(); endTour(); return; }
  if (e.key === "Tab") {             // the walkthrough holds the keyboard: Tab cycles inside its card
    const f = $$("button:not([disabled])", tour.card);
    if (!f.length) return;
    const first = f[0], last = f[f.length - 1];
    if (!tour.card.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
    else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    return;
  }
  // the arrows page through the walkthrough, except where they belong to a field or the 3D view
  if (e.target && e.target.closest && e.target.closest("input, select, textarea, [contenteditable], .fig3d, [role='radio']")) return;
  if (e.key === "ArrowRight") { e.preventDefault(); tourNext(); }
  else if (e.key === "ArrowLeft") { e.preventDefault(); showTourStep(tour.i - 1); }
}

async function tourNext() {
  const step = TOUR[tour.i];
  if (step.action === "run" && !state.run) {
    const btn = $(".tour-next", tour.card);
    if (btn) { btn.disabled = true; btn.textContent = "Running…"; }
    await runRules();
    if (!tour.active) return;
    if (!state.run) { showTourStep(tour.i); return; }   // the run failed; the toast says why
  }
  showTourStep(tour.i + 1);
}

function showTourStep(i) {
  if (!tour.active) return;
  if (i < 0) i = 0;
  if (i >= TOUR.length) { endTour(); toast("That is the whole page. Run the rules whenever you like."); return; }
  tour.i = i;
  const step = TOUR[i];
  const last = i === TOUR.length - 1;
  const primary = step.action === "run" && !state.run ? "Run and continue" : (last ? "Done" : "Next");
  tour.card.innerHTML = `
    <button class="tour-close" type="button" aria-label="Close the walkthrough">×</button>
    <h3 id="tour-title">${h(step.title)}</h3>
    <p id="tour-text">${h(step.text)}</p>
    <div class="tour-nav">
      <button class="btn btn-quiet btn-small tour-back" type="button"${i === 0 ? " disabled" : ""}>Back</button>
      <span class="spacer"></span>
      <span class="counter">${i + 1} of ${TOUR.length} · Esc closes</span>
      <button class="btn btn-primary btn-small tour-next" type="button">${h(primary)}</button>
    </div>`;
  $(".tour-close", tour.card).addEventListener("click", endTour);
  $(".tour-back", tour.card).addEventListener("click", () => showTourStep(tour.i - 1));
  $(".tour-next", tour.card).addEventListener("click", tourNext);
  const el = tourTarget(step);
  if (el) {
    const r = el.getBoundingClientRect();
    const tall = r.height > innerHeight * 0.6;
    const top = r.top + scrollY - (tall ? 120 : Math.max(16, (innerHeight - r.height) / 2));
    window.scrollTo({ top: Math.max(0, top), behavior: reducedMotion() ? "auto" : "smooth" });
  }
  positionTour();
  setTimeout(positionTour, 350);
  $(".tour-next", tour.card).focus({ preventScroll: true });
}

function positionTour() {
  if (!tour.active) return;
  const step = TOUR[tour.i];
  const el = tourTarget(step);
  if (!el) return;
  const r = el.getBoundingClientRect();
  const pad = 8;
  const maxH = innerHeight * 0.62;
  const top = r.top + scrollY - pad, left = r.left + scrollX - pad;
  const w = r.width + 2 * pad, hgt = Math.min(r.height, maxH) + 2 * pad;
  Object.assign(tour.spot.style, { top: `${top}px`, left: `${left}px`, width: `${w}px`, height: `${hgt}px` });
  const cw = tour.card.offsetWidth, ch = tour.card.offsetHeight;
  const cx = Math.min(Math.max(left, scrollX + 16), scrollX + innerWidth - cw - 16);
  let cy = top + hgt + 14;
  if (cy - scrollY + ch > innerHeight - 12 && (top - scrollY) - ch - 14 > 110) cy = top - ch - 14;
  if (cy - scrollY + ch > innerHeight - 12) cy = scrollY + innerHeight - ch - 12;
  Object.assign(tour.card.style, { top: `${cy}px`, left: `${cx}px` });
}

function positionTourSoon() {   // scroll and resize: one update per frame, with a fallback when frames do not run
  if (!tour.active) return;
  cancelAnimationFrame(tour.raf);
  clearTimeout(tour.timer);
  tour.raf = requestAnimationFrame(positionTour);
  tour.timer = setTimeout(positionTour, 120);
}

function offerTour() {
  let seen = false;
  try { seen = !!localStorage.getItem(TOUR_KEY); } catch (e) { seen = false; }
  // a reader who arrived on a link to a run or to the walkthrough already knows where they are going
  const q = new URLSearchParams(location.search);
  $("#tour-offer").hidden = seen || q.has("run") || q.has("tour");
}

// ---------------------------------------------------------------- steps

/* The step bar: the current step is the one the reader is working in (aria-current); a step is done when its work is
   done (a site and an option chosen, a memo on screen), not when the page has scrolled past it. */
function stepsDone() {
  return {
    1: !!(state.site && (state.siteId || state.site.address)),
    2: !!(state.option && (state.optionId || state.option.storeys != null)),
    3: !!state.run,
    4: false,
  };
}

/* The first step whose work is not done yet: with the case preloaded, that is Run and read. */
function firstOpenStep() {
  const done = stepsDone();
  return [1, 2, 3, 4].find(k => !done[k]) || 4;
}

function setStep(n) {
  state.step = n;
  const done = stepsDone();
  $$(".steps a[data-step]").forEach(a => {
    const k = Number(a.dataset.step);
    a.classList.toggle("active", k === n);
    a.classList.toggle("done", k !== n && done[k]);
    if (k === n) a.setAttribute("aria-current", "step"); else a.removeAttribute("aria-current");
  });
}

const STEP_OF = { "step-site": 1, "step-option": 2, "step-run": 3, "step-export": 4 };

function watchSteps() {
  // where the reader is working: focus or a click inside a step's panel
  const follow = e => {
    const sec = e.target && e.target.closest && e.target.closest("#step-site, #step-option, #step-export, #step-run");
    if (sec) setStep(STEP_OF[sec.id]);
  };
  document.addEventListener("focusin", follow);
  document.addEventListener("pointerdown", follow);
  // and scrolling: side by side, the inputs and the memo are both on screen, so only the memo pane's scroll counts
  if (!("IntersectionObserver" in window)) return;
  const stacked = window.matchMedia("(max-width: 1100px)");
  const io = new IntersectionObserver(entries => {
    const vis = entries.filter(e => e.isIntersecting && (stacked.matches || e.target.id === "step-run" || e.target.id === "step-export"))
                       .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (vis) setStep(STEP_OF[vis.target.id]);
  }, { rootMargin: "-40% 0px -50% 0px", threshold: [0, 0.2, 0.5] });
  for (const id of Object.keys(STEP_OF)) { const el = document.getElementById(id); if (el) io.observe(el); }
}

// ---------------------------------------------------------------- wiring

/* Presenting: the inputs step aside and the memo takes the width; the steps to Site or Option bring them back. */
function showInputs(show) {
  $(".panes").classList.toggle("no-inputs", !show);
  document.body.classList.toggle("presenting", !show);
  const btn = $("#hide-inputs");
  btn.textContent = show ? "Hide inputs" : "Show inputs";
  btn.setAttribute("aria-expanded", String(show));
}

async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast("Copied."); }
  catch (e) {
    const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); toast("Copied."); } catch (e2) { toast("Could not copy; select it by hand.", true); }
    ta.remove();
  }
}

async function init() {
  $("#as-of").value = todayISO();
  $("#run-btn").addEventListener("click", runRules);
  $("#print-btn").addEventListener("click", () => window.print());
  $("#save-site").addEventListener("click", () => saveAs("site"));
  $("#save-option").addEventListener("click", () => saveAs("option"));
  // switching files discards unsaved edits, so ask first
  $("#site-select").addEventListener("change", e => {
    if ((state.siteDirty || state.optionDirty) && !confirm("Switch the site file? The unsaved edits to the site and option will be lost.")) { e.target.value = state.siteId || "__new__"; return; }
    selectSite(e.target.value).catch(err => toast(err.message, true));
  });
  $("#option-select").addEventListener("change", e => {
    if (state.optionDirty && !confirm("Switch the option file? The unsaved edits to the option will be lost.")) { e.target.value = state.optionId || "__new__"; return; }
    selectOption(e.target.value).catch(err => toast(err.message, true));
  });
  for (const kind of ["site", "option"]) {
    $(`#edit-${kind}`).addEventListener("click", () => {
      const open = $(`#step-${kind}`).classList.contains("collapsed");
      setCollapsed(kind, !open);
      if (open) { const first = $(`#${kind}-form input, #${kind}-form select, #${kind}-form textarea, #${kind}-form button`); if (first) first.focus(); }
    });
  }
  $("#hide-inputs").addEventListener("click", e => showInputs($(".panes").classList.contains("no-inputs")));
  $("#as-of").addEventListener("change", () => {
    if (!state.run) renderQuiet();
    else setStatus(`The next run will read the rules as of ${$("#as-of").value}; the memo on screen is as of ${state.run.as_of}.`, "info");
  });
  $$(".steps a[data-step]").forEach(a => a.addEventListener("click", e => {
    e.preventDefault();
    const target = document.querySelector(a.getAttribute("href"));
    if (target && target.closest(".inputs")) showInputs(true);
    if (target) {
      target.scrollIntoView({ behavior: scrollBehavior(), block: "start" });
      target.focus({ preventScroll: true });
    }
    setStep(Number(a.dataset.step));
  }));
  $("#revit-btn").addEventListener("click", () => {
    if (!state.run) return;
    const panel = $("#export-panel");
    if (!panel.hidden) { closeExportPanel(); return; }
    renderExportPanel(state.run);
    setStep(4);
    setStatus(`Export to Revit: the two lines that build sheet FFM-01 for this memo (rules ${rev(state.run.stamp)}).`, "info");
    panel.scrollIntoView({ behavior: scrollBehavior(), block: "start" });
  });
  // printing opens every ledger layer, and closes the ones it opened afterwards
  window.addEventListener("beforeprint", () => $$(".ledger details:not([open])").forEach(d => { d.open = true; d.dataset.printOpened = "1"; }));
  window.addEventListener("afterprint", () => $$(".ledger details[data-print-opened]").forEach(d => { d.open = false; delete d.dataset.printOpened; }));
  $("#tour-link").addEventListener("click", e => { e.preventDefault(); startTour(0); });
  $("#tour-start").addEventListener("click", () => startTour(0));
  $("#tour-dismiss").addEventListener("click", () => { $("#tour-offer").hidden = true; try { localStorage.setItem(TOUR_KEY, "1"); } catch (e) { /* fine */ } });
  $("#open-run").addEventListener("change", e => openRun(e.target.value).catch(err => toast(err.message, true)));
  $("#compare-run").addEventListener("change", e => { state.compareRun = e.target.value || null; applyCompare().catch(err => toast(err.message, true)); });
  document.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); runRules(); }
  });

  try {
    state.rules = await api(`/api/rules?as_of=${$("#as-of").value}`);
    await loadSites();
    await loadRevisions();
    const first = state.sites.some(s => s.id === PRELOAD_SITE) ? PRELOAD_SITE : (state.sites[0] ? state.sites[0].id : "__new__");
    state.optionId = PRELOAD_OPTION;
    $("#site-select").value = first;
    await selectSite(first);
    setStatus("Pick a site and an option, set the date the rules should be read on, then run the rules.", "info");
  } catch (e) {
    toast(`Could not load the inputs: ${e.message}`, true);
  }
  setStep(firstOpenStep());
  watchSteps();
  offerTour();
  if (STATIC) loadEngine().catch(() => { /* the chip says why; past runs still open */ });
  await followLink();
}

// ---------------------------------------------------------------- links from the home page

// ?tour=1 starts the walkthrough; ?run=<site>/<folder>&compare=<site>/<folder> opens a past run and compares it
// with another. The run renders first, so on the web it shows while the engine loads for the comparison.
async function followLink() {
  const q = new URLSearchParams(location.search);
  const run = q.get("run"), cmp = q.get("compare");
  if (run) {
    try {
      await openRun(run);
      if (cmp && cmp !== run) { state.compareRun = cmp; fillRunSelects(); await applyCompare(); }
      $("#step-run").scrollIntoView({ block: "start" });
    } catch (e) {
      toast(`Could not open run ${run}: ${e.message}`, true);
    }
  }
  if (q.get("tour")) startTour(0);
}

document.addEventListener("DOMContentLoaded", init);
