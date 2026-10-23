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
      { key: "share_below_hils", label: "Share below HILs", type: "number", help: "0.30 = 30%" },
      { key: "max_rent_share_of_income", label: "Max rent / income", type: "number", help: "0.30 = 30%" },
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
      { key: "below_market_unit_share", label: "Below-market share", type: "number", help: "of units, 0–1" },
      { key: "below_market_discount", label: "Discount to market", type: "number", help: "0.20 = 20%" },
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

// ---------------------------------------------------------------- form rendering

function renderForm(formEl, schema, obj, onChange) {
  formEl.innerHTML = "";
  for (const group of schema) {
    const g = document.createElement("div");
    g.className = "group";
    g.innerHTML = `<div class="eyebrow">${h(group.group)}</div>`;
    for (const f of group.fields) g.appendChild(renderField(f, obj, onChange));
    formEl.appendChild(g);
  }
}

function renderField(f, obj, onChange) {
  if (f.row) {
    const wrap = document.createElement("div");
    if (f.label) wrap.innerHTML = `<div class="field"><span class="label">${h(f.label)}</span></div>`;
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
    el.innerHTML = `<span class="label">${h(f.label)}</span>`;
    const tri = document.createElement("div");
    tri.className = "tri";
    tri.setAttribute("role", "radiogroup");
    tri.setAttribute("aria-label", f.label);
    for (const [v, lab] of [[true, "Yes"], [false, "No"], [null, "Not sure"]]) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = lab;
      b.className = v === null ? "unsure" : "";
      b.setAttribute("role", "radio");
      b.setAttribute("aria-checked", String((value === undefined ? null : value) === v));
      b.addEventListener("click", () => {
        setPath(obj, f.key, v);
        $$("button", tri).forEach(x => x.setAttribute("aria-checked", "false"));
        b.setAttribute("aria-checked", "true");
        onChange(f.key);
      });
      tri.appendChild(b);
    }
    el.appendChild(tri);
    return el;
  }
  if (f.type === "select") {
    const opts = f.options.map(([v, lab]) => `<option value="${h(v)}"${String(value ?? "") === String(v) ? " selected" : ""}>${h(lab)}</option>`).join("");
    el.innerHTML = `<label for="${id}">${h(f.label)}</label><select id="${id}">${opts}</select>${f.help ? `<span class="help">${h(f.help)}</span>` : ""}`;
    $("select", el).addEventListener("change", e => { setPath(obj, f.key, e.target.value === "" ? null : e.target.value); onChange(f.key); });
    return el;
  }
  if (f.type === "textarea") {
    el.innerHTML = `<label for="${id}">${h(f.label)}</label><textarea id="${id}">${h(value ?? "")}</textarea>`;
    $("textarea", el).addEventListener("input", e => { setPath(obj, f.key, e.target.value || null); onChange(f.key); });
    return el;
  }
  if (f.type === "programs") {
    el.innerHTML = `<span class="label">${h(f.label)}</span>`;
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
    el.innerHTML = `<span class="label">Existing trees on site</span>`;
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
          <button type="button" class="x" title="Remove this row">×</button>`;
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
  // text, slug, number
  const isNum = f.type === "number";
  el.innerHTML = `<label for="${id}">${h(f.label)}</label>
    <input id="${id}" type="${isNum ? "number" : "text"}"${isNum ? ` step="${f.int ? "1" : "any"}"` : ""} value="${h(value ?? "")}">
    ${f.help ? `<span class="help">${h(f.help)}</span>` : ""}`;
  $("input", el).addEventListener("input", e => {
    let v = e.target.value;
    if (isNum) v = v === "" ? null : Number(v);
    else if (f.type === "slug") v = v.trim().toLowerCase().replace(/[^a-z0-9._-]+/g, "-") || null;
    else v = v === "" ? null : v;
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
  await loadOptions();
  await loadRuns();
  fillRunSelects();
}

function onSiteChange() {
  state.siteDirty = true;
  $("#site-dirty").hidden = false;
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
  renderQuiet();
}

function onOptionChange(key) {
  state.optionDirty = true;
  $("#option-dirty").hidden = false;
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
}

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
    renderMemo(run);
    showStamp(run.stamp);
    enableExports(run);
    setStep(3);
    $("#export-panel").hidden = true;
    await loadRuns();
    fillRunSelects();
    $("#compare-note").textContent = run.diff ? `${run.diff.changes.length} change${run.diff.changes.length === 1 ? "" : "s"} · ${run.diff.previous_stamp} → ${run.diff.current_stamp}` : "";
    const ms = Math.round(performance.now() - t0);
    toast(`Ran the rules as of ${run.as_of} in ${ms} ms · stamp ${run.stamp} · ${run.in_browser ? "kept in this browser tab" : `wrote outputs/${run.run_id}/`}`);
    $("#step-run").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    toast(e.message, true);
  } finally {
    btn.classList.remove("busy");
    btn.textContent = "Run the rules";
  }
}

function showStamp(stamp) {
  $("#stamp-text").textContent = stamp || "";
  $("#stamp-box").hidden = !stamp;
}

function enableExports(run) {
  const on = !!run;
  const base = run ? `api/runs/${run.run_id}` : "";
  const urls = on ? (run.downloads || { html: `${base}/memo.html?download=1`, md: `${base}/memo.md?download=1`, massing: run.massing ? `${base}/massing.json?download=1` : null }) : {};
  const stem = run ? run.run_id.replace("/", "_") : "memo";
  const set = (sel, key, name) => {
    const a = $(sel);
    const ok = on && !!urls[key];
    a.href = ok ? urls[key] : "#";
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
  $("#memo").className = "memo";
  $("#memo").innerHTML = `
    <div class="card memo-head">
      <h1>${h(site.address || site.id || "A site")}</h1>
      <div class="memo-meta">
        <div><b>Option</b><span>${h(opt.name || opt.id || "—")}</span></div>
        <div><b>Proponent</b><span>${h(opt.proponent || "—")}</span></div>
        <div><b>Rules as of</b><span>${h($("#as-of").value || todayISO())}</span></div>
      </div>
      <p class="quiet">Run the rules evaluates this site and option against the ${n || "dated"} rules in force on that date, ${STATIC ? "in your browser, with nothing uploaded, and keeps the stamped memo in this tab" : "writes a stamped memo to <code>outputs/</code>"}, and reads it here: three answers first, then the massing and the full ledger.</p>
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

  // 1. header
  parts.push(`<div class="card memo-head">
    <h1>${h(site.address || site.id)}</h1>
    <div class="memo-meta">
      <div><b>Option</b><span>${h(opt.name || opt.id)}</span></div>
      <div><b>Proponent</b><span>${h(opt.proponent || "—")}${opt.proponent_type ? ` <span class="cont">(${h(String(opt.proponent_type).replace(/_/g, " "))})</span>` : ""}</span></div>
      <div><b>Rules as of</b><span>${h(L.run.as_of)}</span></div>
      <div><b>Stamp</b><span><code>${h(L.run.stamp.stamp)}</code> <span class="cont">· engine ${h(L.run.engine_version)}</span></span></div>
    </div>
    <p class="quiet">Deterministic output of the rule stack listed under Sources: same inputs and rule set, same memo. A feasibility screen, not legal, planning or funding advice; every number links to the document it came from.</p>
  </div>`);

  // 2. the three answers; 3. the massing figures beside them at >=1600 px, under them otherwise;
  // 4. what changed; 5. the full ledger; 6. inputs, sources, version stamp
  const rest = [];
  if (run.diff) rest.push(renderChanges(run.diff));
  rest.push(renderLedger(res));
  rest.push(renderInputs(site, opt));
  rest.push(renderSources(res, site, opt));
  rest.push(renderStamp(L.run));
  parts.push(`<div class="memo-body">
    <div class="answers">${answerAllowed(L)}${answerFunders(L)}${answerUnsure(L)}</div>
    ${renderFigures(run)}
    <div class="memo-rest">${rest.join("\n")}</div>
  </div>`);

  const memoEl = $("#memo");
  memoEl.innerHTML = parts.join("\n");
  memoEl.className = "memo";
  void memoEl.offsetWidth;  // restart the fade
  memoEl.classList.add("landed");
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
  let body = `<ul class="finding-list">${rows.map(r => `<li>${pill(r.status)}<span><span class="title">${h(r.title)}:</span> <span class="cont">${h(r.finding)}</span></span></li>`).join("")}</ul>`;
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

function renderLedger(res) {
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
      <td><span class="rule-title">${h(r.title)}</span><code class="rule-id">${h(r.rule_id)} · v ${h(r.version_effective_from || "—")}</code></td>
      <td class="status">${pill(r.status)}</td>
      <td>${h(r.finding)}</td>
      <td class="nums">${h(fmtValues(r.values))}</td>
      <td class="src">${sourceLink(r.source)}</td>
    </tr>`).join("");
    return `<details>
      <summary><span class="layer">Layer ${h(L.layer)}</span><span class="layer-title">${h(L.title)}</span><span class="counts">${countPills}</span></summary>
      <table class="plain"><colgroup><col class="c-rule"><col class="c-status"><col class="c-finding"><col class="c-nums"><col class="c-src"></colgroup><thead><tr><th>Rule</th><th>Status</th><th>Finding</th><th>Numbers used</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table>
    </details>`;
  });
  return `<section class="card section ledger">
    <div class="eyebrow">Full ledger · ${res.length} rules</div>
    <h2>Full ledger</h2>
    <p class="cont" style="color:var(--grey);margin-bottom:6px">Every rule the engine ran, by layer, with the arithmetic it used and the clause it came from. Click a layer to open it.</p>
    ${blocks.join("")}
  </section>`;
}

function renderInputs(site, opt) {
  const u = opt.units || {};
  const units = Object.entries(u).map(([k, v]) => `${k.replace(/_/g, " ")} ${v ?? "—"}`).join(", ");
  const tenure = String(opt.tenure || "").replace(/_/g, " ");
  return `<section class="card section">
    <div class="eyebrow">Inputs</div>
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
    <div class="eyebrow">Sources</div>
    <h2>Sources</h2>
    <ul>${items.join("")}</ul>
  </section>`;
}

function renderStamp(run) {
  const st = run.stamp;
  const files = Object.entries(st.rules_files || {}).map(([f, hsh]) => `<li><code>${h(f)}</code> <span class="hash">${h(hsh.slice(0, 16))}…</span></li>`).join("");
  return `<section class="card section stampbox">
    <div class="eyebrow">Version stamp</div>
    <h2>Version stamp</h2>
    <p>Stamp <code>${h(st.stamp)}</code>: a hash of the rules hash and the rule versions in force on ${h(run.as_of)}. Change one number in one rule and it changes.</p>
    <p class="hash">Rules hash (SHA-256 over all rule files): ${h(st.rules_hash)}</p>
    <ul>${files}</ul>
  </section>`;
}

// ---------------------------------------------------------------- figures: drawn from massing.json, formatting only

/* the drawing colours of the Lotwise sheets: envelope blue, grey streets and lanes, drawing ink, amber for a form line */
const FIG = { proposedFill: "#3c8cdc", proposedStroke: "#2a6fb8", outrightFill: "#bdbdbd", outrightStroke: "#8e8e8e",
              bench: "#c77d14", lot: "#1f2933", env: "#c81e1e", grey: "#5f6672" };
const SVG_OPEN = `xmlns="http://www.w3.org/2000/svg" font-family="IBM Plex Sans, Helvetica, Arial, sans-serif" role="img"`;
const NS = `vector-effect="non-scaling-stroke"`;

function polyEl(pts, attrs) {
  return `<polygon points="${pts.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(" ")}" ${attrs} ${NS}/>`;
}

function figPlan(m) {
  const W = m.lot.frontage_m, D = m.lot.depth_m;
  const pad = Math.max(4, W * 0.07);
  const fs = Math.max(2.2, W / 34);
  const vbW = W + 2 * pad, vbH = D + 2 * pad + fs * 1.6;
  const masses = Object.fromEntries(m.masses.map(x => [x.name, x]));
  const Y = y => pad + (D - y);                       // the street edge (y = 0) drawn at the bottom
  const P = pts => pts.map(([x, y]) => [pad + x, Y(y)]);
  let s = `<svg ${SVG_OPEN} viewBox="0 0 ${vbW.toFixed(2)} ${vbH.toFixed(2)}" aria-label="Plan: lot, setback envelope and the two massing footprints">`;
  s += polyEl(P(m.lot.polygon), `fill="#f4f4f2" stroke="${FIG.lot}" stroke-width="1.2"`);
  s += polyEl(P(m.envelope.polygon), `fill="none" stroke="${FIG.env}" stroke-width="1" stroke-dasharray="4 3"`);
  if (masses.outright) s += polyEl(P(masses.outright.footprint), `fill="${FIG.outrightFill}" stroke="${FIG.outrightStroke}" stroke-width="1.2" fill-opacity="0.9"`);
  if (masses.proposed) s += polyEl(P(masses.proposed.footprint), `fill="${FIG.proposedFill}" stroke="${FIG.proposedStroke}" stroke-width="1.2" fill-opacity="0.5"`);
  s += `<text x="${(pad + W / 2).toFixed(2)}" y="${(Y(0) + fs * 1.35).toFixed(2)}" font-size="${fs}" text-anchor="middle" fill="${FIG.grey}">street · frontage ${W} m</text>`;
  const rx = pad + W + fs * 0.9, ry = Y(D / 2);
  s += `<text x="${rx.toFixed(2)}" y="${ry.toFixed(2)}" font-size="${fs}" text-anchor="middle" fill="${FIG.grey}" transform="rotate(90 ${rx.toFixed(2)} ${ry.toFixed(2)})">depth ${D} m</text>`;
  s += `</svg>`;
  return s;
}

function figSection(m) {
  const W = m.lot.frontage_m;
  const masses = Object.fromEntries(m.masses.map(x => [x.name, x]));
  let hmax = Math.max(...m.masses.map(x => x.height_m), 1);
  const b = m.policy_benchmark;
  if (b && b.height_m) hmax = Math.max(hmax, b.height_m[1]);
  const pad = Math.max(4, W * 0.07);
  const fs = Math.max(2.2, W / 34);
  const labelRoom = Math.max(36, W * 0.5);
  const vbW = W + 2 * pad + labelRoom, vbH = hmax + pad + fs * 2.2;
  const ground = fs * 1.2 + hmax;
  const Yz = z => ground - z;
  const envX = pad + (m.envelope.setbacks_m.side || 0), envW = m.envelope.width_m;
  let s = `<svg ${SVG_OPEN} viewBox="0 0 ${vbW.toFixed(2)} ${vbH.toFixed(2)}" aria-label="Section across the frontage: outright and proposed heights with the staff benchmark">`;
  s += `<line x1="${(pad - 2).toFixed(2)}" y1="${ground.toFixed(2)}" x2="${(pad + W + 2).toFixed(2)}" y2="${ground.toFixed(2)}" stroke="${FIG.lot}" stroke-width="1.2" ${NS}/>`;
  if (masses.outright) {
    const o = masses.outright;
    s += `<rect x="${envX.toFixed(2)}" y="${Yz(o.height_m).toFixed(2)}" width="${envW.toFixed(2)}" height="${o.height_m}" fill="${FIG.outrightFill}" stroke="${FIG.outrightStroke}" stroke-width="1.2" ${NS}/>`;
  }
  if (masses.proposed) {
    const p = masses.proposed;
    s += `<rect x="${envX.toFixed(2)}" y="${Yz(p.height_m).toFixed(2)}" width="${envW.toFixed(2)}" height="${p.height_m}" fill="${FIG.proposedFill}" fill-opacity="0.45" stroke="${FIG.proposedStroke}" stroke-width="1.2" ${NS}/>`;
    for (let k = 1; k < p.storeys; k++) {
      const yk = Yz(k * p.floor_to_floor_m);
      if (yk <= Yz(p.height_m)) break;
      s += `<line x1="${envX.toFixed(2)}" y1="${yk.toFixed(2)}" x2="${(envX + envW).toFixed(2)}" y2="${yk.toFixed(2)}" stroke="${FIG.proposedStroke}" stroke-width="0.6" stroke-opacity="0.6" ${NS}/>`;
    }
  }
  const lx = pad + W + fs * 0.8;
  if (b && b.height_m) {
    for (const z of b.height_m) {
      s += `<line x1="${pad.toFixed(2)}" y1="${Yz(z).toFixed(2)}" x2="${(pad + W).toFixed(2)}" y2="${Yz(z).toFixed(2)}" stroke="${FIG.bench}" stroke-width="1" stroke-dasharray="4 3" ${NS}/>`;
    }
    s += `<text x="${lx.toFixed(2)}" y="${(Yz(b.height_m[0]) + fs * 1.05).toFixed(2)}" font-size="${fs}" fill="${FIG.bench}">${h(b.height_m[0])} to ${h(b.height_m[1])} m · staff benchmark</text>`;
  }
  if (masses.proposed) s += `<text x="${lx.toFixed(2)}" y="${(Yz(masses.proposed.height_m) - fs * 0.35).toFixed(2)}" font-size="${fs}" fill="${FIG.proposedStroke}" font-weight="600">${h(masses.proposed.height_m)} m · proposed</text>`;
  if (masses.outright) s += `<text x="${lx.toFixed(2)}" y="${(Yz(masses.outright.height_m) - fs * 0.35).toFixed(2)}" font-size="${fs}" fill="${FIG.lot}">${h(masses.outright.height_m)} m · outright</text>`;
  s += `<text x="${(pad + W / 2).toFixed(2)}" y="${(ground + fs * 1.3).toFixed(2)}" font-size="${fs}" text-anchor="middle" fill="${FIG.grey}">heights in metres · setback envelope ${h(m.envelope.width_m)} m wide</text>`;
  s += `</svg>`;
  return s;
}

function massLine(x) {
  return `<b>${h(x.label)}</b>: plate ${fmtNum(x.plate_area_m2)} m² × ${x.storeys} = ${fmtNum(x.gfa_m2)} m² (FSR ${Number(x.fsr).toFixed(2)}), ${h(x.height_m)} m high.`;
}

function renderFigures(run) {
  const m = run.massing;
  const out = [];
  if (m) {
    const sb = m.envelope.setbacks_m || {};
    out.push(`<figure class="card figure">
      <div class="eyebrow">FIG 01 · Plan</div>
      ${figPlan(m)}
      <div class="legend"><span><i class="fig-proposed"></i>proposed</span><span><i class="fig-outright"></i>outright</span><span><i class="fig-env"></i>setback envelope</span></div>
      <figcaption>Lot ${h(m.lot.frontage_m)} × ${h(m.lot.depth_m)} m, ${fmtNum(m.lot.area_m2)} m². Setback envelope ${h(m.envelope.width_m)} × ${h(m.envelope.depth_m)} m (front ${h(sb.front)}, rear ${h(sb.rear)}, sides ${h(sb.side)} m). Both masses fill the envelope's width from the front setback back.</figcaption>
    </figure>`);
    const bench = m.policy_benchmark;
    const trees = m.trees;
    out.push(`<figure class="card figure">
      <div class="eyebrow">FIG 02 · Section across the frontage</div>
      ${figSection(m)}
      <div class="legend"><span><i class="fig-proposed"></i>proposed</span><span><i class="fig-outright"></i>outright</span>${bench && bench.height_m ? `<span><i class="fig-bench"></i>staff benchmark</span>` : ""}</div>
      <figcaption>${m.masses.map(massLine).join(" ")}${bench && bench.height_m ? ` Staff benchmark under <code>${h(bench.rule_id)}</code>: ${h(bench.height_m[0])} to ${h(bench.height_m[1])} m, about FSR ${h(bench.fsr)}.` : ""}${trees ? ` Trees: Schedule C requires ${h(trees.required)}, the plan leaves ${h(trees.after)} (shortfall ${h(trees.shortfall)}).` : ""}</figcaption>
      ${(m.warnings || []).map(w => `<p class="note">${h(w)}</p>`).join("")}
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
    <figcaption><b>${c.masses ?? "?"} masses</b>, ${c.floor_plates ?? "?"} floor plates, ${c.model_lines ?? "?"} model lines, ${c.views ?? "?"} views, ${c.dimensions ?? 0} dimensions and ${c.notes ?? 0} notes on sheet ${h(r.sheet_number || "")}; stamp <code>${h(run.stamp)}</code> in every element's Comments. Stages: ${h(stages)}.${r.sheet_pdf ? ` <a href="${base}/ffm_sheet.pdf" target="_blank" rel="noopener">PDF</a>.` : ""}${r.errors ? ` ${r.errors} stage error(s) recorded in the result file.` : ""}</figcaption>
  </figure>`;
}

// ---------------------------------------------------------------- what changed

function renderChanges(d) {
  const rows = (d.changes || []).map(c => {
    const ver = c.from_version && c.from_version !== c.to_version;
    return `<tr>
      <td><code>${h(c.rule_id)}</code></td>
      <td class="change">${h(String(c.change).replace(/_/g, " "))}</td>
      <td>${c.from ? pill(c.from) : "—"}${ver ? `<div class="cont" style="font-size:12px;margin-top:4px">v ${h(c.from_version)}</div>` : ""}</td>
      <td>${c.to ? pill(c.to) : "—"}${ver ? `<div class="cont" style="font-size:12px;margin-top:4px">v ${h(c.to_version)}</div>` : ""}</td>
      <td>${h(c.finding)}</td>
    </tr>`;
  }).join("");
  return `<section class="card section changes">
    <div class="eyebrow">What changed</div>
    <h2>What changed since the previous run</h2>
    <p class="stamps">previous <b>${h(d.previous_stamp)}</b> (as of ${h(d.previous_as_of)}) → current <b>${h(d.current_stamp)}</b> (as of ${h(d.current_as_of)}) · ${d.rules_changed ? "the rule files themselves changed" : "rule files unchanged; differences come from the as-of date or the inputs"}</p>
    ${rows ? `<table class="plain"><thead><tr><th>Rule</th><th>Change</th><th>From</th><th>To</th><th>Now reads</th></tr></thead><tbody>${rows}</tbody></table>` : `<p>No rule changed status.</p>`}
  </section>`;
}

// ---------------------------------------------------------------- past runs: open, compare

function runLabel(r) {
  const v = r.verdicts || {};
  return `${r.as_of} · ${r.stamp} · ${r.folder}${r.revit ? " · Revit" : ""} · outright ${v.outright}, funders ${v.funded}`;
}

function fillRunSelects() {
  const open = $("#open-run"), cmp = $("#compare-run");
  const cur = state.run ? state.run.run_id : "";
  open.innerHTML = `<option value="">${state.run ? "This run" : "Choose a run…"}</option>` +
    state.runs.map(r => `<option value="${h(r.run_id)}"${r.run_id === cur ? " selected" : ""}>${h(runLabel(r))}</option>`).join("");
  cmp.innerHTML = `<option value="">Nothing</option>` +
    state.runs.filter(r => r.run_id !== cur).map(r => `<option value="${h(r.run_id)}"${r.run_id === state.compareRun ? " selected" : ""}>${h(runLabel(r))}</option>`).join("");
}

async function openRun(runId) {
  if (!runId) return;
  const [site, folder] = runId.split("/");
  const run = await api(`/api/runs/${encodeURIComponent(site)}/${encodeURIComponent(folder)}`);
  state.run = run;
  showStamp(run.stamp);
  enableExports(run);
  if (state.compareRun && state.compareRun !== runId) await applyCompare(false);
  renderMemo(run);
  fillRunSelects();
  setStep(3);
  $("#export-panel").hidden = true;
}

async function applyCompare(render = true) {
  const run = state.run;
  const note = $("#compare-note");
  if (!run) { note.textContent = state.compareRun ? "Applies to the next run." : ""; return; }
  if (!state.compareRun || state.compareRun === run.run_id) {
    run.diff = null;
    note.textContent = "";
  } else {
    const d = await api(`/api/diff?from=${encodeURIComponent(state.compareRun)}&to=${encodeURIComponent(run.run_id)}`);
    run.diff = d;
    note.textContent = `${d.changes.length} change${d.changes.length === 1 ? "" : "s"} · ${d.previous_stamp} → ${d.current_stamp}`;
  }
  if (render) renderMemo(run);
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
  $$("[data-copy]", panel).forEach(b => b.addEventListener("click", () => copyText($("#" + b.dataset.copy).textContent)));
  if (!STATIC) {
    $("#check-revit").addEventListener("click", checkRevit);
    if (run.revit) checkRevit();
  }
}

async function checkRevit() {
  const run = state.run;
  if (!run) return;
  const box = $("#revit-result");
  box.innerHTML = `<p class="cont">Reading ffm_revit_result.json…</p>`;
  try {
    const r = await api(`/api/runs/${run.run_id}/ffm_revit_result.json`);
    if (r.stamp !== run.stamp) {
      box.innerHTML = `<p class="err">A result exists in this folder but for stamp ${h(r.stamp)}, not this run's ${h(run.stamp)}. Run the script again on this folder.</p>`;
      return;
    }
    const refreshed = await postJSON(`/api/runs/${run.run_id}/memo`, {});   // memo gains its "Built in Revit" section
    run.revit = refreshed.revit;
    box.innerHTML = revitResultHtml(r, run);
    renderMemo(run);
  } catch (e) {
    box.innerHTML = `<p class="cont">${h(e.message)} Nothing built for this run yet: run the script, then check again.</p>`;
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
    text: "Pick the date the rules should be read on. The engine applies the versions in force that day and stamps the memo with them, so two memos can be told apart." },
  { target: "#step-site", title: "Step 1 · Site",
    text: "Choose a site file or describe a new one: district, lot, policy areas, trees, owner. Where you are not sure, say so. The memo then reads uncertain instead of guessing." },
  { target: "#step-option", title: "Step 2 · Option",
    text: "Describe the building: storeys, floor area, the unit mix, tenure, the funders you aim at, and the rezoning path if there is one. Save it as a file to rerun the same thing from the command line." },
  { target: "#run-btn", title: "Run the rules", action: "run",
    text: "One click. In under a second the engine writes a stamped memo to the outputs folder and reads it here." },
  { target: ".answers", fallback: "#memo", title: "Step 3 · The three answers",
    text: "Is it allowed? Does it fit the funders? What is still unsure, and who resolves it? Every finding prints the numbers it used and links the clause it came from." },
  { target: ".figures", fallback: "#memo", title: "The massing",
    text: "Plan and section drawn from the same numbers as the memo, with the staff benchmark. When the Revit script has run on this folder, the sheet it built appears as a third figure." },
  { target: ".ledger", fallback: "#memo", title: "The full ledger",
    text: "Every rule the engine ran, by layer, collapsed until you open it: status, finding, numbers used and the source link." },
  { target: ".memo-tools", title: "Past runs",
    text: "Open an earlier run, or compare two. When a rule changes version, the table names it and the stamp changes." },
  { target: "#step-export", title: "Step 4 · Export",
    text: "Download the memo as HTML or Markdown, print it, take the massing file, or open Export to Revit for the two lines that build the sheet." },
];
const TOUR_KEY = "ffm.walkthrough.seen";
const tour = { active: false, i: 0, spot: null, card: null, raf: 0, timer: 0 };

function tourTarget(step) {
  return document.querySelector(step.target) || (step.fallback ? document.querySelector(step.fallback) : null);
}

function reducedMotion() {
  return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function startTour(at = 0) {
  if (tour.active) endTour();
  tour.active = true;
  tour.spot = document.createElement("div");
  tour.spot.className = "tour-spot";
  tour.card = document.createElement("div");
  tour.card.className = "tour-card";
  tour.card.setAttribute("role", "dialog");
  tour.card.setAttribute("aria-live", "polite");
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
}

function tourKeys(e) {
  if (e.key === "Escape") { e.preventDefault(); endTour(); }
  else if (e.key === "ArrowRight") { e.preventDefault(); tourNext(); }
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
    <div class="eyebrow">Walkthrough · ${i + 1} of ${TOUR.length}</div>
    <h3>${h(step.title)}</h3>
    <p>${h(step.text)}</p>
    <div class="tour-nav">
      <button class="btn btn-quiet btn-small tour-back" type="button"${i === 0 ? " disabled" : ""}>Back</button>
      <span class="spacer"></span>
      <span class="counter">Esc to close</span>
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
  $("#tour-offer").hidden = seen;
}

// ---------------------------------------------------------------- steps

function setStep(n) {
  $$(".steps a[data-step]").forEach(a => {
    const k = Number(a.dataset.step);
    a.classList.toggle("active", k === n);
    a.classList.toggle("done", k < n);
  });
}

function watchSteps() {
  const map = { "step-site": 1, "step-option": 2, "step-run": 3, "step-export": 4 };
  if (!("IntersectionObserver" in window)) return;
  const io = new IntersectionObserver(entries => {
    const vis = entries.filter(e => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (vis) setStep(map[vis.target.id]);
  }, { rootMargin: "-40% 0px -50% 0px", threshold: [0, 0.2, 0.5] });
  for (const id of Object.keys(map)) { const el = document.getElementById(id); if (el) io.observe(el); }
}

// ---------------------------------------------------------------- wiring

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
  $("#copy-stamp").addEventListener("click", () => copyText($("#stamp-text").textContent));
  $("#print-btn").addEventListener("click", () => window.print());
  $("#save-site").addEventListener("click", () => saveAs("site"));
  $("#save-option").addEventListener("click", () => saveAs("option"));
  $("#site-select").addEventListener("change", e => selectSite(e.target.value).catch(err => toast(err.message, true)));
  $("#option-select").addEventListener("change", e => selectOption(e.target.value).catch(err => toast(err.message, true)));
  $("#as-of").addEventListener("change", () => { if (!state.run) renderQuiet(); });
  $$(".steps a[data-step]").forEach(a => a.addEventListener("click", e => {
    e.preventDefault();
    const target = document.querySelector(a.getAttribute("href"));
    if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    setStep(Number(a.dataset.step));
  }));
  $("#revit-btn").addEventListener("click", () => {
    if (!state.run) return;
    const panel = $("#export-panel");
    if (!panel.hidden) { panel.hidden = true; return; }
    renderExportPanel(state.run);
    setStep(4);
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
  });
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
    const first = state.sites.some(s => s.id === PRELOAD_SITE) ? PRELOAD_SITE : (state.sites[0] ? state.sites[0].id : "__new__");
    state.optionId = PRELOAD_OPTION;
    $("#site-select").value = first;
    await selectSite(first);
  } catch (e) {
    toast(`Could not load the inputs: ${e.message}`, true);
  }
  setStep(1);
  watchSteps();
  offerTour();
  if (STATIC) loadEngine().catch(() => { /* the chip says why; past runs still open */ });
}

document.addEventListener("DOMContentLoaded", init);
