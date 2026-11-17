/* The manager's route and stage. Flow 1 in docs/user-flows.md, laid out by docs/ui-route-and-stage.md (16 Nov 2026;
   before, a seven-stop accordion down the rail with the Site and Option forms under it, while what each stop found
   landed in the other column). The left column is the route: three read-only rows, each a stop with its decision
   once made. The memo pane is the stage: one card, the current stop's input above what it found. 01 The site: an
   address or a saved site, the parcel on the map, then what the open data could not tell. 02 The option: the
   programs, what the site allows, a candidate and its four figures, what the rules leave to the manager. 03 Run:
   the money in, then the rules. After a run the memo takes the pane and the route folds; a route row brings its
   card back over the memo. progress() is the one source for what is decided; `guide` (core/state.js) holds the
   route. The engine does every derivation (ffm/suggest.py); this only asks and shows. The stage's map is Leaflet,
   loaded only when a site is on the stage. The route's actions (look up, read, derive) are guide.js. */

import {
  $, $$, cap, fmtNum, getPath, h, keyWords, pill, scrollBehavior, setPath, setStatus, toast, todayISO
} from "./core/util.js";
import { guide, state } from "./core/state.js";
import { loadScript } from "./core/engine.js";
import {
  ANSWERS, appliesHere, cd1Of, cornerStreets, districtOf, fieldOf, FINANCE_FIELDS, GUIDE_FIELDS, isShare, OPTION_FIELDS,
  optWord, shareFromScreen, shareToScreen, SITE_FIELDS
} from "./fields.js";
import { optionSummary, refNow, renderForm } from "./schedule.js";
import {
  discardDraft, loadDemo, markStale, onOptionChange, onSiteChange, readDraft, resumeDraft, saveDraft, saveNow,
  selectOption, selectSite
} from "./files.js";
import { byRev, openRun, rev, runRules, syncRunButton } from "./runs.js";
import { placeRunTools, renderMemo } from "./memo/memo.js";
import { money } from "./memo/answers.js";
import { tok } from "./figures/common.js";
import { DERIVES, guideLookup, guideReadSite, guideSuggest, guideUseSite, useSuggestion } from "./guide.js";
import { showInputs } from "./modes.js";

/* A parcel's shape in a manager's words, without the classifier's figures. */
const shapeWords = shape => shape.class === "rectangle" ? "a rectangle"
  : String(shape.note || cap(String(shape.class || "").replace(/_/g, " "))).replace(/\s*\([^)]*\)/g, "").replace(/,\s*[\d,.]+ m2\b.*$/, "").replace(/\.$/, "") + (shape.class !== "near_rectangle" ? "; the massing follows the polygon" : "");

/* The programs' published terms, from the rule files themselves (the version in force on the as-of date). */
function stagePrograms(ids) {
  const rules = state.rules.filter(r => r.layer === "E" && ids.includes(r.id));
  if (!rules.length) return `<p class="quiet">No program chosen: the funders' answer will list every program as information.</p>`;
  // the file's keys and codes in words (17 Nov 2026: "non_profit_society, housing_cooperative", "rgi 50%",
  // "Min lease years nominal")
  const human = k => keyWords(k.replace(/_cad(_\d{4}_\d{2})?$/, " ($)").replace(/_m2$/, " (m²)"));
  const val = v => typeof v === "boolean" ? (v ? "yes" : "no") : Array.isArray(v) ? v.map(val).join(", ") : (v && typeof v === "object" ? Object.entries(v).map(([k, x]) => `${keyWords(k)} ${typeof x === "number" && x <= 1 ? Math.round(x * 100) + "%" : fmtNum(x)}`).join(" / ") : (typeof v === "number" ? (v <= 1 && String(v).includes(".") ? Math.round(v * 100) + "%" : fmtNum(v)) : String(v).replace(/_/g, " ")));
  return rules.map(r => {
    const p = r.params || {}, s = r.source || {};
    const rows = Object.entries(p).filter(([k, v]) => !["status", "submission", "criteria_note"].includes(k) && v !== null && v !== undefined && typeof v !== "string").slice(0, 7)
      .map(([k, v]) => `<div><dt>${h(cap(human(k)))}</dt><dd>${h(val(v))}</dd></div>`).join("");
    return `<div class="stage-program">
      <h3>${h(r.title)} <span class="cont">· ${h(r.jurisdiction)} · in force from ${h(r.version_effective_from || "—")}</span></h3>
      <dl class="found-site terms">${rows}${p.status ? `<div><dt>Status</dt><dd class="cont">${h(p.status)}</dd></div>` : ""}</dl>
      <p class="stage-src">${s.url ? `<a href="${h(s.url)}" target="_blank" rel="noopener">${h(s.title || s.url)}</a>` : h(s.title || "")}${s.section ? ` <span class="cont">· ${h(s.section)}</span>` : ""}</p>
    </div>`;
  }).join("");
}

/* The assumptions the pro-forma reads, from layer F as it stands on the as-of date, each with its source. */
function stageMoney() {
  const F = state.rules.filter(r => r.layer === "F");
  const fin = (state.option && state.option.finance) || {};
  return `<dl class="found-site stage-money">
      <div><dt>Yours</dt><dd>land ${fin.land_cost_cad != null ? "$" + fmtNum(fin.land_cost_cad) : "<i>blank</i>"} · equity ${fin.equity_cad != null ? "$" + fmtNum(fin.equity_cad) : "<i>blank</i>"} · other grants ${fin.other_grants_cad != null ? "$" + fmtNum(fin.other_grants_cad) : "<i>blank</i>"}</dd></div>
    </dl>
    <ul class="stage-assumptions">${F.map(r => `<li><b>${h(r.title)}</b>${(r.source || {}).placeholder ? ' <span class="ph-tag">placeholder</span>' : ""}<div class="cont">${h((r.params || {}).summary || "")}</div><div class="stage-src">${(r.source || {}).url ? `<a href="${h(r.source.url)}" target="_blank" rel="noopener">${h(r.source.title)}</a>` : h((r.source || {}).title || "")}</div></li>`).join("")}</ul>`;
}

/* The parcel on an OpenStreetMap map (Leaflet from a CDN, OSM tiles, loaded only when a site is on the stage). */
const LEAFLET_JS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js";

const LEAFLET_CSS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css";

// the files' own hashes (cdnjs publishes the same): a changed file on the CDN is refused, not run
const LEAFLET_JS_SRI = "sha512-puJW3E/qXDqYp9IfhAI54BJEaWIfloJ7JWs7OeD5i6ruC9JZL1gERT1wjtwXFlh7CjE7ZJ+/vcRZRkIYIb6p4g==";

const LEAFLET_CSS_SRI = "sha512-h9FcoyWjHcOcmEVkxOfTLnmZFWIH0iZhZT1H2TbOq55xssQGEJHEaIm+PgoUaZbRvQTNTluNOEfb1ZRy6D3BOw==";

let leafletPromise = null;

function loadLeaflet() {
  if (window.L) return Promise.resolve();
  if (leafletPromise) return leafletPromise;
  leafletPromise = new Promise((resolve, reject) => {
    if (!document.querySelector(`link[href="${LEAFLET_CSS}"]`)) { const l = document.createElement("link"); l.rel = "stylesheet"; l.href = LEAFLET_CSS; l.integrity = LEAFLET_CSS_SRI; l.crossOrigin = "anonymous"; document.head.appendChild(l); }
    loadScript(LEAFLET_JS, LEAFLET_JS_SRI).then(resolve, reject);
  });
  return leafletPromise;
}

async function mountStageMap(site, box = $("#stage-map")) {
  if (!box || !site) return;
  const ring = site.parcel && site.parcel.polygon_lonlat;
  const c = (site.lookup && site.lookup.center) || (site.osm && site.osm.center) || ((site.context || {}).center) || null;
  if (!ring && !c) { box.innerHTML = `<p class="help">No coordinates for this site: look it up by address to place it on the map.</p>`; return; }
  try { await loadLeaflet(); } catch (e) { box.innerHTML = `<p class="help">The map could not load (${h(e.message)}); the plan still draws the lot.</p>`; return; }
  if (!box.isConnected) return;   // the card was drawn again while Leaflet loaded
  box.innerHTML = "";
  const map = L.map(box, { zoomControl: true, attributionControl: true, scrollWheelZoom: false });
  box._map = map;   // the stage keeps this map across re-renders of its card while the parcel is the same
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(map);
  if (ring && ring.length >= 3) {
    const latlngs = ring.map(p => [p[1], p[0]]);
    // the parcel in the signal blue of the proposed mass, the one colour on a half-tone map (brand.css)
    const poly = L.polygon(latlngs, { color: tok("--c-envelope-line", "#2a6fb8"), weight: 1.6, fillColor: tok("--c-envelope", "#3c8cdc"), fillOpacity: 0.28 }).addTo(map);
    poly.bindTooltip(`${site.address || site.id} · ${site.site_area_m2 ? fmtNum(site.site_area_m2) + " m²" : "parcel"}`);
    map.fitBounds(poly.getBounds().pad(0.6));
  } else {
    map.setView([c.lat, c.lon], 17);
    L.circleMarker([c.lat, c.lon], { radius: 6, color: tok("--c-envelope-line", "#2a6fb8"), fillColor: tok("--c-envelope", "#3c8cdc"), fillOpacity: 0.5 }).addTo(map);
  }
  setTimeout(() => map.invalidateSize(), 50);
}

const GUIDE_STOPS = [
  { n: 1, title: "The site", what: "An address, or a saved site" },
  { n: 2, title: "The option", what: "What goes on the site" },
  { n: 3, title: "Run", what: "The money in, then the rules" },
];

/* A draft or a link from before 16 Nov 2026 counted seven stops; they fold into the three. */
export const stopOf = n => (!n || n <= 1 ? 1 : n <= 4 ? 2 : 3);

const CHECK_SVG = `<svg class="route-check" viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 8.4 6.6 11.3 12.5 4.9"/></svg>`;

/* What is decided so far. The manager's option counts once it is a saved one, a used suggestion, or the option of a
   run; the architect's whenever there is one to run. Run, the route and the status line all read this. */
export function progress() {
  const site = !!(state.site && (state.siteId || state.site.zoning_district || state.site.address));
  const option = !!(state.option && (state.optionId || guide.suggestionUsed || state.run
    || (state.mode !== "manager" && (state.option.storeys != null || state.option.gfa_m2 != null))));
  return { site, option, run: !!state.run };
}

/* The run on screen, the stop on screen, or both: a card brought over a memo by a route row. */
export const stageShown = () => state.mode === "manager" && (!state.run || guide.over);

export function ruleTitle(id) {
  const r = state.rules.find(x => x.id === id);
  return r ? r.title : id;
}

/* The rule stack's outright schedule for a district, or null: RM-1, RT-3, RM-4 read from the schedules; others entered
   unverified; a CD-1 site's own by-law, matched on its CD-1 number (`cd1`, the site's cd1_bylaw_number) and no other. */
export function scheduleFor(district, cd1) {
  const d = String(district || "").toUpperCase();
  if (!d) return null;
  return state.rules.find(r => r.check === "district_outright_fsr" && !(r.applies_to_districts || []).includes("*") && appliesHere(r, d, cd1)) || null;
}

/* What to say beside the district: the schedule in the rules (verified or not), or the CD-1 by-law, or that a rough
   envelope stands in and the architect confirms it. The manager is not asked to read a schedule in. */
function districtWords(site) {
  const d = site.zoning_district; if (!d) return "";
  const cd1 = cd1Of(d, site.cd1_bylaw_number);
  const r = scheduleFor(d, cd1);
  const what = cd1 ? `CD-1 (${h(cd1)})'s by-law` : "its schedule";
  if (r) return r.source && r.source.verified === false ? ` <span class="cont warn-text">· ${what} is in the rules, entered unverified; the architect confirms the figures</span>` : ` <span class="cont">· ${cd1 ? `${what} is in the rules` : "schedule in the rules"}</span>`;
  if (cd1) return ` <span class="cont warn-text">· a site-specific district: ${what} is not in the rules, so a rough envelope stands in; the architect confirms it</span>`;
  if (/^CD-1/i.test(d)) return ` <span class="cont warn-text">· a site-specific district with no CD-1 number recorded, so no by-law can be matched: a rough envelope stands in; the architect confirms it</span>`;
  return ` <span class="cont warn-text">· no ${h(d)} schedule in the rules: a rough envelope stands in; the architect confirms it</span>`;
}

/* The focused control survives a re-render of the card: the thing the reader was on is found again by what it is. */
function focusKeyOf(el, root) {
  if (!el || !root || !root.contains(el)) return null;
  if (el.id) return `#${el.id}`;
  const row = el.closest(".sg-row");
  if (el.dataset.answer) return el.dataset.value !== undefined ? `[data-answer="${el.dataset.answer}"][data-value="${el.dataset.value}"]` : `[data-answer="${el.dataset.answer}"]`;
  if (row && el.dataset.pick) return `.sg-row[data-key="${row.dataset.key}"] [data-pick="${el.dataset.pick}"]`;
  if (row && el.classList.contains("sg-input")) return `.sg-row[data-key="${row.dataset.key}"] .sg-input`;
  if (el.dataset.cand) return `.cands [data-cand="${el.dataset.cand}"]`;
  if (el.dataset.fig) return `[data-fig="${el.dataset.fig}"]`;
  if (el.classList.contains("guide-program")) return `.guide-program[value="${el.value}"]`;
  return null;
}

/* The route and the stage together; every change in the flow comes through here. */
export function renderGuide() {
  renderRoute();
  if (stageShown()) renderStage();
  syncRunButton();
  saveDraft();
}

// ---- the route

function siteLine(s) {
  if (!s) return "";
  const dims = s.frontage_m != null && s.depth_m != null ? `${fmtNum(s.frontage_m)} × ${fmtNum(s.depth_m)} m` : (s.site_area_m2 ? `${fmtNum(s.site_area_m2)} m²` : "");
  return [String(s.address || s.id || "a site").split(",")[0], s.zoning_district, dims].filter(Boolean).join(" · ");
}

function optionLine(o) {
  if (!o) return "";
  const homes = Object.values(o.units || {}).reduce((t, v) => t + (Number(v) || 0), 0);
  const bits = [o.storeys != null ? `${o.storeys} storeys` : "", homes ? `${homes} homes` : "",
    guide.suggestion && !state.optionId ? cap(guide.suggestion.candidate) : (o.name ? String(o.name).split(/[;,]/)[0] : "")];
  return bits.filter(Boolean).join(" · ") || "an option";
}

export function renderRoute() {
  const el = $("#guide");
  if (!el) return;
  if (state.mode !== "manager") { el.hidden = true; return; }
  el.hidden = false;
  const p = progress();
  const cur = stageShown() ? (guide.step || 1) : 0;
  const done = { 1: p.site, 2: p.option, 3: p.run };
  const open = { 1: true, 2: p.site, 3: p.site && p.option };
  const sum = { 1: p.site ? siteLine(state.site) : "", 2: p.option ? optionLine(state.option) : "", 3: p.run ? `${rev(state.run.run_id)} · rules as of ${state.run.as_of}` : "" };
  const rows = GUIDE_STOPS.map(s => {
    const here = cur === s.n;
    return `<li><button type="button" class="route-row${here ? " current" : ""}${done[s.n] ? " done" : ""}" data-stop="${s.n}"${here ? ' aria-current="step"' : ""}${open[s.n] ? "" : " disabled"}>
      <span class="route-n">${done[s.n] && !here ? `${CHECK_SVG}<span class="sr-only">done:</span>` : `0${s.n}`}</span>
      <span class="route-t">${h(s.title)}</span>
      <span class="route-s">${h(sum[s.n] || s.what)}</span>
    </button></li>`;
  }).join("");
  const tail = state.run
    ? `<button type="button" class="route-memo${cur === 0 ? " current" : ""}"${cur === 0 ? ' aria-current="page"' : ""}><span class="route-n">${h(rev(state.run.run_id))}</span><span class="route-t">The memo</span></button>`
    : `<p class="route-then">Then the memo: the four answers, the PDF, issuing.</p>`;
  el.innerHTML = `<ol class="route-list">${rows}</ol>${tail}`;
  $$(".route-row", el).forEach(b => b.addEventListener("click", () => goStop(Number(b.dataset.stop))));
  const m = $(".route-memo", el); if (m) m.addEventListener("click", backToMemo);
}

/* A route row: its card on the stage, over the memo if one is on screen (Back returns to it). */
function goStop(n) {
  const p = progress();
  if ((n === 2 && !p.site) || (n === 3 && !(p.site && p.option))) return;
  if (state.mode !== "manager") return;
  guide.step = n;
  guide.over = !!state.run;
  guide.changing = false;
  if (guide.over) showInputs(true, false);
  renderGuide();
  focusStage();
  if (n === 2) enterOption();
}

export function backToMemo() {
  if (!state.run) return;
  guide.over = false;
  renderMemo(state.run);
  renderRoute();
  syncRunButton();
  const head = $("#memo .memo-head h1");
  if (head) { head.tabIndex = -1; head.focus({ preventScroll: true }); }
  (matchMedia("(max-width: 1100px)").matches ? $("#memo") : $("#step-run")).scrollIntoView({ behavior: scrollBehavior(), block: "start" });
}

/* The new card's question takes the focus, and the stage comes into view under the bars. */
export function focusStage() {
  const q = $("#stage-q");
  if (!q) return;
  q.focus({ preventScroll: true });
  const card = $("#stage-card");
  const top = card.getBoundingClientRect().top;
  const bars = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--bars-h")) || 88;
  if (top < bars || top > innerHeight * 0.6) $("#step-run").scrollIntoView({ behavior: scrollBehavior(), block: "start" });
}

/* Entering 02: the site is read against layers A to C and an option derived, without a button for either. */
export function enterOption() {
  if (!state.site) return;
  if ((!guide.reading || guide.readStale) && !guide.busy.read) guideReadSite();
  if (((!guide.suggestion && !state.optionId && !guide.suggestionUsed) || guide.suggestStale) && !guide.busy.suggest) guideSuggest();
}

// ---- the stage

let stageSig = "";   // kept for older callers; the map is kept across renders by its own signature

let stageDrawn = 0;  // the stop last drawn, so the card fades in only when the stop changes

export function renderStage() {
  if (!stageShown()) return;
  const memo = $("#memo");
  if (!memo) return;
  const keep = $("#stage-map", memo);
  const focusKey = focusKeyOf(document.activeElement, memo);
  placeRunTools(false);
  const pane = $(".memo-pane");
  pane.classList.add("staging");
  pane.classList.remove("has-memo");
  memo.innerHTML = stageHtml();
  memo.className = "memo stage-on" + (stageDrawn !== guide.step ? " landed" : "");
  stageDrawn = guide.step;
  memo.dataset.stage = String(guide.step);
  memo.dataset.issuedManager = "";
  wireStage(memo);
  const slot = $("#stage-map", memo);
  if (slot) {
    if (keep && keep._map && keep.dataset.sig === slot.dataset.sig) { slot.replaceWith(keep); setTimeout(() => keep._map.invalidateSize(), 0); }
    else mountStageMap(state.site || (guide.lookup && guide.lookup.site), slot);
  }
  if (focusKey) { const again = $(focusKey, memo); if (again) again.focus({ preventScroll: true }); }
}

const stageCard = (n, q, body, foot) => `<section class="card stage-card" id="stage-card" data-stop="${n}" aria-labelledby="stage-q">
    <h2 id="stage-q" tabindex="-1"><span class="stage-n" aria-hidden="true">0${n}</span> ${h(q)}</h2>
    <div class="stage-body">${body}</div>
    ${foot ? `<div class="stage-foot">${foot}</div>` : ""}
  </section>`;

export const foot = (quiet, main) => `<div class="foot-quiet">${quiet || ""}</div><div class="foot-main">${main || ""}</div>`;

function stageHtml() {
  const site = state.site;
  const n = guide.step || 1;
  const blank = !site && !guide.lookup;
  const draft = blank ? readDraft() : null;
  const head = `<header class="stage-head">
      <div class="stage-title">
        <h1>${site ? h(site.address || site.id) : "A site, a funder, an option, a memo"}</h1>
        ${state.run && guide.over ? `<button type="button" class="btn btn-quiet btn-small" id="stage-back">Back to ${h(rev(state.run.run_id))}</button>` : ""}
      </div>
      ${blank ? `<p class="quiet">Three stops, one card at a time: the site, the option, the run. Each card asks one thing and shows what it found.</p>` : ""}
      ${draft ? `<div class="form-actions resume"><button type="button" class="btn btn-small" id="stage-resume">Resume where you were</button><button type="button" class="btn btn-quiet btn-small" id="stage-discard">Start fresh</button><span class="help">${h((draft.site && (draft.site.address || draft.site.id)) || ((state.sites || []).find(s => s.id === draft.siteId) || {}).address || draft.siteId ||(draft.guide && draft.guide.lookup && draft.guide.lookup.site && draft.guide.lookup.site.address) || "a site")}, left in this tab ${h(String(draft.saved_at || "").replace("T", " ").slice(0, 16))}.</span></div>` : ""}
    </header>`;
  const card = n === 1 ? cardSite() : n === 2 ? cardOption() : cardRun();
  return head + card + (blank && n === 1 ? ghostHtml() : "");
}

/* What the memo will be, drawn as its title block in outline: labels only, no figures it has not made. */
function ghostHtml() {
  return `<figure class="ghost">
      <div class="ghost-sheet" aria-hidden="true">
        <div class="ghost-h"></div>
        <div class="memo-meta"><div><b>Option</b><span></span></div><div><b>Proponent</b><span></span></div><div><b>Rules as of</b><span></span></div><div><b>Revision</b><span>R1</span></div></div>
        <ol class="ghost-answers"><li><b>01</b> Is it allowed?</li><li><b>02</b> Does it fit the funders?</li><li><b>03</b> What is still unsure, and who resolves it?</li><li><b>04</b> Does the money work?</li></ol>
      </div>
      <figcaption>After the run, the memo takes this pane: four answers, the open items with who resolves each, the drawings, and a PDF for the board.</figcaption>
    </figure>`;
}

// ---- 01 the site

function cardSite() {
  const site = state.site;
  const chosen = progress().site && !guide.changing;
  if (chosen) {
    const runs = byRev((state.runs || []).filter(r => r.run_id.startsWith((state.siteId || site.id || "") + "/")));
    const memos = runs.length ? `<p class="stage-memos"><span class="cont">This site has ${runs.length} memo${runs.length === 1 ? "" : "s"}:</span> ${runs.map(r => `<button type="button" class="linkish" data-open-run="${h(r.run_id)}">${h(rev(r.run_id))}</button>`).join(" ")}</p>` : "";
    const body = `${siteFacts(site)}${memos}${askTable(1)}${saveSiteInline()}`;
    const quiet = `<button type="button" class="btn btn-quiet btn-small" id="guide-change-site">Change the site</button>${!state.siteId || state.siteDirty ? `<button type="button" class="btn btn-quiet btn-small" id="guide-keep-site" aria-expanded="${!!guide.saveOpen}" aria-controls="stage-save">Keep as a site file…</button>` : ""}`;
    return stageCard(1, "What the open data could not tell", body, foot(quiet, `<button type="button" class="btn btn-primary" id="guide-next-1">Continue to the option →</button>`));
  }
  const lk = guide.lookup;
  if (lk && lk.site) {
    const info = lk.site.lookup || {};
    const quiet = `<button type="button" class="btn btn-quiet btn-small" id="guide-lookup-again">Look up another</button>`;
    const main = `<button type="button" class="btn btn-primary" id="guide-use-site"${info.outside_vancouver ? " disabled" : ""}>${info.civic_mismatch ? `Yes, ${h(String(lk.site.address).split(",")[0])} is the site` : "Use this site"}</button>`;
    return stageCard(1, "Is this the parcel?", previewFacts(lk.site), foot(quiet, main));
  }
  const busy = !!guide.busy.lookup;
  const saved = state.sites.map(s => `<option value="${h(s.id)}">${h(s.address || s.id)} · ${h(s.zoning_district || "?")}</option>`).join("");
  const body = `
    <div class="addr-row">
      <label class="sr-only" for="guide-address">Address</label>
      <input type="text" id="guide-address" value="${h(guide.address)}" placeholder="e.g. 609 Heatley Ave" autocomplete="street-address">
      <button class="btn btn-primary" type="button" id="guide-lookup"${busy ? " disabled" : ""}>${busy ? "Looking up…" : "Look up"}</button>
    </div>
    <p class="help">${busy ? "The City's address list, then the district and the parcel; the streets, buildings and trees around it take a few seconds more." : "The City's address list gives the point; its open data the zoning district and the parcel."}</p>
    <div class="addr-alt">
      ${saved ? `<label class="addr-saved"><span class="cont">or a saved site</span><select id="guide-saved-site"><option value="">choose…</option>${saved}</select></label>` : ""}
      <span class="cont">or</span> <button type="button" class="linkish" id="stage-demo">the demo case</button> <span class="cont">(998 E 19th Ave as approved by Council, 25 Jul 2024)</span>
    </div>`;
  return stageCard(1, "Where is the site?", body, "");
}

/* The parcel the lookup found, over the map, before it is used: the check that catches a wrong lot. */
function previewFacts(found) {
  const info = found.lookup || {};
  const p = found.parcel || {};
  return `<div class="stage-site">
      <div class="stage-map" id="stage-map" data-sig="${h(mapSig(found))}" role="img" aria-label="The parcel the lookup found, on a map"><p class="help">Map loading…</p></div>
      <dl class="found-site">
        <div><dt>Found</dt><dd><b>${h(found.address)}</b><span class="cont"> · from the ${info.geocoded_as && String(info.geocoded_as).includes("property address") ? "City's address list" : "address as geocoded"}</span></dd></div>
        <div><dt>District</dt><dd>${found.zoning_district ? `<b>${h(districtOf(found))}</b>${districtWords(found)}` : "<i>not found</i>"}</dd></div>
        <div><dt>Lot</dt><dd>${found.site_area_m2 ? `<b>${h(fmtNum(found.site_area_m2))} m²</b> · ${h(found.frontage_m)} × ${h(found.depth_m)} m` : "<i>no parcel polygon at the point</i>"}${p.shape && p.shape.class !== "rectangle" ? ` <span class="cont">· ${h(shapeWords(p.shape))}</span>` : ""}</dd></div>
        ${info.civic_mismatch ? `<div><dt>Check</dt><dd class="warn-text">You typed ${h(info.civic_typed)}; the City's list has no such number on this street. This is the nearest parcel: use it only if it is the site.</dd></div>` : ""}
        ${info.outside_vancouver ? `<div><dt>Check</dt><dd class="warn-text">${h(found.municipality)} is outside the City of Vancouver: the rules here cannot read its zoning.</dd></div>` : ""}
      </dl>
    </div>
    <p class="help">If the outline is wrong, look up another address.</p>`;
}

/* The chosen site: the map beside its facts. */
function siteFacts(site) {
  const p = site.parcel || {};
  const m = p.metrics || {};
  const street = ((site.context || {}).street || {}).name || (site.osm && site.osm.frame && site.osm.frame.front_street) || "not known";
  return `<div class="stage-site">
      <div class="stage-map" id="stage-map" data-sig="${h(mapSig(site))}" role="img" aria-label="The parcel on a map"><p class="help">Map loading…</p></div>
      <dl class="found-site">
        <div><dt>District</dt><dd>${site.zoning_district ? `<b>${h(districtOf(site))}</b>${districtWords(site)}` : "<i>not found: the architect enters it</i>"}</dd></div>
        <div><dt>Lot</dt><dd>${site.site_area_m2 ? `<b>${h(fmtNum(site.site_area_m2))} m²</b>${site.frontage_m ? ` · ${h(site.frontage_m)} × ${h(site.depth_m)} m` : ""}` : "<i>no parcel</i>"}${p.shape ? ` <span class="cont">· ${h(shapeWords(p.shape))}</span>` : (m.vertices ? ` <span class="cont">(${h(m.vertices)} corners${m.rectangular ? ", a rectangle" : ", not a rectangle: the massing follows the polygon"})</span>` : "")}${site.boundary_m ? ' <span class="cont">· boundary drawn by hand</span>' : ""}</dd></div>
        <div><dt>Street</dt><dd>${h(street)}${cornerStreets(site).length ? ` <span class="cont">· a corner lot</span>` : ""}</dd></div>
        <div><dt>Owner</dt><dd>${site.owner ? h(site.owner) : site.owner_type ? h(ansWord("owner_type", site.owner_type)) : "<i>not sure</i>"}</dd></div>
      </dl>
    </div>`;
}

const mapSig = s => JSON.stringify(s ? [s.address, s.site_area_m2, s.parcel && s.parcel.polygon_lonlat && s.parcel.polygon_lonlat.length, s.lookup && s.lookup.center] : null);

/* Save as… for the site, under the card: an id, Save, Cancel (no browser prompt). */
function saveSiteInline() {
  if (!guide.saveOpen) return "";
  const id = state.site && state.site.id ? state.site.id : String((state.site && state.site.address) || "site").split(",")[0].toLowerCase().replace(/[^a-z0-9._-]+/g, "-");
  return `<div class="save-inline" id="stage-save">
      <label class="field"><span class="label">Site id</span><input type="text" id="stage-save-id" value="${h(id)}" autocomplete="off"></label>
      <button class="btn btn-small" type="button" id="stage-save-go">Save</button>
      <button class="btn btn-quiet btn-small" type="button" id="stage-save-cancel">Cancel</button>
      <span class="help">Names sites/&lt;id&gt;.json, so the run can be repeated from the command line. An id that exists is not overwritten.</span>
    </div>`;
}

// ---- what the rules leave to a person: one schedule per stop

/* A coded answer in the words its question offered ("municipality" → "The City"); free text as typed. */
const ansWord = (key, v) => {
  const a = ANSWERS[key];
  const o = a && a.options && a.options.find(([x]) => String(x) === String(v));
  return o ? o[1] : String(v);
};

/* The current answer to a question: the site's own, or the option's (the suggestion's until it is used). */
function answerValue(key) {
  const a = ANSWERS[key];
  if (!a) return null;
  if (a.on === "site") return getPath(state.site || {}, key);
  if (guide.suggestion && !guide.suggestionUsed) return key in (guide.answers || {}) ? guide.answers[key] : getPath(guide.suggestion.option || {}, key);
  return getPath(state.option || {}, key);
}

function askControl(key, labelId) {
  const a = ANSWERS[key];
  const cur = answerValue(key);
  if (a.kind === "tri") {
    const v = cur === true ? "yes" : cur === false ? "no" : "";
    return `<span class="tri" role="radiogroup" aria-labelledby="${labelId}">${[["yes", "Yes"], ["no", "No"], ["", "Not sure"]].map(([val, lab]) => `<button type="button" role="radio" class="${val === "" ? "unsure" : ""}" data-answer="${h(key)}" data-value="${val}" aria-checked="${v === val}" tabindex="${v === val ? 0 : -1}">${lab}</button>`).join("")}</span>`;
  }
  if (a.kind === "select") {
    let options = key === "front_street" ? [["", "Not sure"], ...cornerStreets(state.site).map(s => [s, s])] : a.options;
    if (cur != null && cur !== "" && !options.some(([v]) => String(v) === String(cur))) options = [...options, [String(cur), String(cur)]];
    return `<select data-answer="${h(key)}" aria-labelledby="${labelId}">${options.map(([val, lab]) => `<option value="${h(val)}"${String(cur ?? "") === String(val) ? " selected" : ""}>${h(lab)}</option>`).join("")}</select>`;
  }
  return `<input type="text" data-answer="${h(key)}" aria-labelledby="${labelId}" value="${h(cur || "")}" placeholder="${h(a.placeholder || "")}">`;
}

/* The questions a stop asks, as a schedule: the question, the answer, who answers it. */
function askTable(stop) {
  const keys = Object.keys(ANSWERS).filter(k => ANSWERS[k].stop === stop && (!ANSWERS[k].when || ANSWERS[k].when(state.site || {})));
  if (!keys.length) return "";
  const rows = keys.map(k => `<tr><th scope="row" id="ask-${h(k)}">${h(ANSWERS[k].label)}</th><td>${askControl(k, `ask-${k}`)}</td><td class="ask-who">${h(ANSWERS[k].who || "")}</td></tr>`).join("");
  return `<table class="ask-table"><thead><tr><th scope="col">Question</th><th scope="col">Answer</th><th scope="col">Who answers</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function takeAnswer(key, raw) {
  const a = ANSWERS[key];
  if (!a) return;
  const v = a.kind === "tri" ? (raw === "yes" ? true : raw === "no" ? false : null) : (raw === "" ? null : raw);
  const word = v ? ansWord(key, v) : "";
  const said = `${a.label.replace(/\?$/, "")}: ${v === true ? "yes" : v === false ? "no" : v ? word.charAt(0).toLowerCase() + word.slice(1) : "not sure"}`;
  if (a.on === "site") {
    if (!state.site) return;
    if (key === "front_street") {
      // the front decides which side the frontage is. The lookup took the named street (streets[0]); the other one becomes
      // site.front_face {street}, which the engine turns the lot to (boundary.oriented_ring) and the figures follow
      // through lot.orientation. Before 17 Nov 2026 this swapped frontage_m and depth_m, which left a parcel polygon
      // placed in the old frame, 11 m off the envelope drawn for the new front (609 Heatley Ave); a site saved that
      // way is swapped back first.
      const site = state.site, streets = cornerStreets(site);
      const named = (site.context && site.context.street && site.context.street.name) || streets[0];
      if (streets[0] && named && named !== streets[0] && streets.includes(named)) {
        [site.frontage_m, site.depth_m] = [site.depth_m, site.frontage_m];
        site.context.street.name = streets[0];
        if (site.osm && site.osm.frame) site.osm.frame.front_street = streets[0];
        if (site.parcel && site.parcel.metrics) site.parcel.metrics.frontage_from = "the side parallel to the street";
      }
      site.front_street = v;
      if (v && streets.includes(v) && v !== streets[0]) site.front_face = { street: v };
      else if (site.front_face && site.front_face.street) delete site.front_face;
      setStatus(v ? `The front is ${v}${site.front_face ? ": the lot is turned to it" : ""}. The yards, the envelope and the massing follow it.` : "Which street is the front stays not sure: the memo keeps the named street and asks the architect to confirm.", "info");
    } else {
      setPath(state.site, key, key === "toa_tier" && v != null ? Number(v) : v);
      setStatus(`${said}.`, "info");
    }
    onSiteChange(key);
    renderForm($("#site-form"), SITE_FIELDS, state.site, onSiteChange);
    // what the site allows, and so the suggestion, may move with the answer: both are read again at 02
    guide.readStale = true;
    if (guide.suggestion) guide.suggestStale = true;
    return;
  }
  if (guide.suggestion && !guide.suggestionUsed) {
    guide.answers = guide.answers || {};
    guide.answers[key] = v;
    setStatus(`${said}; it travels with the option.`, "info");
  } else if (state.option) {
    setPath(state.option, key, v);
    onOptionChange(key);
    renderForm($("#option-form"), OPTION_FIELDS, state.option, onOptionChange);
    setStatus(`${said}.`, "info");
  }
}

/* What the words in the "left to a person" list mean to the manager. */
const KEY_LABEL = { gfa_m2: "Storeys, height and floor area", rent_tiers_units: "Rent tiers", unit_count_for_the_mix: "Homes for the fund's mix",
  existing_trees_on_site: "Trees on the site", in_former_community_vision_area: "Former Community Vision area", in_transit_oriented_area: "Transit-oriented area",
  frequent_bus_stop_within_400m: "Frequent bus stop within 400 m", land_tenure_plan: "Land tenure", developer_partner: "Developer partner", site_control: "Site control" };

const keyLabel = k => KEY_LABEL[k] || (ANSWERS[k] && ANSWERS[k].label.replace(/\?$/, "")) || cap(k.replace(/_/g, " "));

// ---- 02 the option

/* The option as it stands on the stage: the suggestion with the manager's own figures over it until it is used, then
   the option itself. */
function stageOptionNow() {
  const S = guide.suggestion;
  if (S && !guide.suggestionUsed) {
    const o = JSON.parse(JSON.stringify(S.option));
    for (const [k, , kind] of GUIDE_FIELDS) {
      if (guide.mine[k] === undefined) continue;
      const raw = String(guide.mine[k]).trim();
      if (raw === "") { setPath(o, k, null); continue; }
      const v = kind === "text" ? raw : shareFromScreen(k, Number(raw));
      if (kind === "text" || Number.isFinite(v)) setPath(o, k, v);
    }
    return o;
  }
  return state.option || (S && S.option) || null;
}

function cardOption() {
  const site = state.site || {};
  const S = guide.suggestion;
  const progs = state.rules.filter(r => r.layer === "E");
  const chosen = new Set(guide.programs || (state.option && state.option.target_programs) || defaultPrograms());
  const R = guide.reading;
  const o = stageOptionNow();
  const savedOpts = (state.options || []).filter(x => x.for_site);
  const cands = S ? S.candidates : [{ id: "funder-ready", title: "Funder-ready", what: "the envelope the site gets, with the funder questions answered" }, { id: "outright", title: "Outright", what: "what the district allows as of right" }, { id: "benchmark", title: "Benchmark", what: "the staff benchmark under the rezoning policy" }];
  const fromSaved = !!(state.optionId && !(S && !guide.suggestionUsed));
  const candWhy = cands.filter(c => c.available === false).map(c => `<li><b>${h(c.title)}</b>: ${h(c.why)}.</li>`).join("");
  const reading = guide.busy.read ? `<p class="help">Reading the site against layers A to C…</p>`
    : R ? `<ul class="reading-list">${R.results.map(r => `<li>${pill(r.status)} <span>${h(r.title)}</span></li>`).join("")}</ul>` : `<p class="help">Not read yet.</p>`;
  const dl = `<dl class="stage-dl">
      <div><dt>For</dt><dd>
        <div class="chips" role="group" aria-label="The programs in view">${progs.map(r => `<label class="chip"><input type="checkbox" class="guide-program" value="${h(r.id)}"${chosen.has(r.id) ? " checked" : ""}> <span>${h(r.title)}</span></label>`).join("")}</div>
        <details class="fold"><summary>Their published terms</summary>${stagePrograms([...chosen])}</details>
      </dd></div>
      <div><dt>The site allows</dt><dd>${reading}</dd></div>
      <div><dt>Start from</dt><dd>
        <div class="start-row">
          <div class="seg cands" role="group" aria-label="Start from">${cands.map(c => `<button class="segbtn" type="button" data-cand="${h(c.id)}" aria-pressed="${!fromSaved && guide.candidate === c.id}"${c.available === false ? ` disabled title="${h(c.why)}"` : ` title="${h(c.what)}"`}>${h(c.title)}</button>`).join("")}</div>
          ${savedOpts.length ? `<label class="addr-saved"><span class="cont">or a saved option</span><select id="guide-saved-option"><option value="">choose…</option>${savedOpts.map(x => `<option value="${h(x.id)}"${fromSaved && state.optionId === x.id ? " selected" : ""}>${h(x.name || x.id)}</option>`).join("")}</select></label>` : ""}
        </div>
        ${candWhy ? `<ul class="help cand-why">${candWhy}</ul>` : ""}${S && S.candidate_note && !fromSaved ? `<p class="help warn-text">${h(S.candidate_note)}</p>` : ""}
      </dd></div>
      <div><dt>The building</dt><dd>${guide.busy.suggest ? `<p class="help">Deriving the ${h(guide.candidate)} option from the rules…</p>` : (o ? figureBlock(o, fromSaved ? null : S) : `<p class="help">Choose where to start.</p>`)}</dd></div>
      <div><dt>Left to you</dt><dd>${askTable(2)}${leftToPerson(S, fromSaved)}</dd></div>
    </dl>`;
  // a building the figures cannot make waits here: Continue stays off and says which figure to change (17 Nov 2026:
  // 19 storeys in 19.8 m and a floor larger than the lot both went on to the run)
  const probs = o && !guide.busy.suggest ? figureProblems(o, S) : [];
  const ready = !!(o && !guide.busy.suggest) && !probs.length;
  const quiet = `<button type="button" class="btn btn-quiet btn-small" id="guide-back-1">Back to the site</button>`;
  const blocked = probs.length ? `<p class="help warn-text stage-block" id="stage-block">Continue waits for ${probs.length === 1 ? "one figure" : `${probs.length} figures`}: ${h(probs.join("; "))}.</p>` : "";
  const main = `${blocked}<button type="button" class="btn btn-primary" id="guide-next-2"${ready ? "" : " disabled"}${probs.length ? ' aria-describedby="stage-block"' : ""}>${guide.confirmUse ? "Replace the edited option →" : "Continue to the run →"}</button>`;
  const lot = [site.zoning_district, site.site_area_m2 ? `${fmtNum(site.site_area_m2)} m²` : "", site.frontage_m != null ? `${fmtNum(site.frontage_m)} × ${fmtNum(site.depth_m)} m` : ""].filter(Boolean).join(" · ");
  const context = `<p class="stage-context">${h(lot)}${districtWords(site)}</p>`;
  return stageCard(2, "What goes on it?", context + dl, foot(quiet, main));
}

export const defaultPrograms = () => state.rules.filter(r => r.layer === "E" && /chf|bcbuilds/.test(r.id)).map(r => r.id);

/* The status line's last words after a figure changes: on to the run, or what Continue waits for (17 Nov 2026: it
   said "Continue to the run" while Continue was disabled). */
export function continueWords() {
  const o = stageOptionNow();
  const probs = o ? figureProblems(o, guide.suggestion) : [];
  return probs.length ? `Continue waits for ${probs.length === 1 ? "one figure" : `${probs.length} figures`}: ${probs.map(p => p.split(" (")[0]).join(" and ")}.` : "Continue to the run when it reads right.";
}

/* What the four figures cannot make, in a few words each: storeys taller than the height, a floor larger than the
   plate the setbacks leave. Empty when the building can stand. Pure. */
function figureProblems(o, S) {
  const out = [];
  // impossible, not merely tight: no floor to floor of 2.8 m or more makes the storeys in the height (a height a
  // little under storeys × 3.3 m is a lower floor to floor, which the note above the block offers)
  const MIN_F2F = 2.8;
  if (o.storeys && o.height_m != null && Number(o.height_m) / o.storeys < MIN_F2F)
    out.push(`the height or the storeys (${fmtNum(o.storeys)} storeys in ${fmtNum(o.height_m)} m is ${fmtNum(Math.round(Number(o.height_m) / o.storeys * 100) / 100)} m a floor, under the ${MIN_F2F} m any floor needs)`);
  const E0 = S && S.envelope;
  const lot = Number((state.site || {}).site_area_m2) || 0;
  const box = E0 && E0.plate_w_m && E0.plate_d_m ? E0.plate_w_m * E0.plate_d_m : (lot || null);
  if (o.gfa_m2 && o.storeys && box && o.gfa_m2 / o.storeys > box * 1.01)
    out.push(`the floor area or the storeys (${fmtNum(Math.round(o.gfa_m2 / o.storeys))} m² a floor, more than the ${fmtNum(Math.round(box))} m² the setbacks leave)`);
  return out;
}

/* The building in four figures, each changed in place; the rest of the suggestion behind one fold. */
function figureBlock(o, S) {
  const site = state.site || {};
  const f = k => (S && S.fields && S.fields[k]) || null;
  const tag = k => {
    if (S && guide.mine[k] !== undefined && String(guide.mine[k]).trim() !== "") return `<span class="fig4-tag yours">yours</span>`;
    const x = f(k);
    if (!x) return "";
    if (x.basis === "envelope") return `<span class="fig4-tag rough" title="the plate the setbacks leave × the storeys the code allows; not a permitted figure">rough</span>`;
    if (!x.rule_id) return `<span class="fig4-tag ph">placeholder</span>`;
    return `<span class="fig4-tag" title="${h(ruleTitle(x.rule_id))}">${h(refNow(x.rule_id) || "rule")}</span>`;
  };
  const homes = Object.values(o.units || {}).reduce((t, v) => t + (Number(v) || 0), 0);
  const lot = Number(site.site_area_m2) || 0;
  const fsr = o.gfa_m2 && lot ? (o.gfa_m2 / lot).toFixed(2) : null;
  const cell = (key, k, shown, sub, editable = true) => {
    const editing = guide.editFig === key;
    // the FSR cell takes an FSR and writes the floor area from it (17 Nov 2026: it opened a floor-area field under
    // the word FSR, so 6.01 typed there became 6.01 m²)
    const raw = key === "fsr" ? fsr : getPath(o, key);
    const val = editing
      ? `<input type="number" class="fig4-input" data-fig-input="${h(key)}" value="${h(raw ?? "")}" step="${key === "storeys" ? 1 : "any"}" aria-label="${h(k)}, my figure">`
      : (editable ? `<button type="button" class="fig4-v" data-fig="${h(key)}" aria-label="${h(k)}: ${h(shown)}. Change it">${h(shown)}</button>` : `<span class="fig4-v">${h(shown)}</span>`);
    return `<div class="fig4-cell"><span class="fig4-k">${h(k)}</span>${val}<span class="fig4-sub">${sub || ""}${tag(key === "fsr" ? "gfa_m2" : key)}</span></div>`;
  };
  // the storeys at the option's floor-to-floor need a height; a stated height below that is said here, before the run
  // (17 Nov 2026: 4 storeys at 9.9 m made a memo "within 10.7 m" while the elevations drew 13.2 m)
  const f2f = Number(o.floor_to_floor_m) || 3.0;
  const needs = o.storeys != null ? Math.round(o.storeys * f2f * 10) / 10 : null;
  const short = needs != null && o.height_m != null && Number(o.height_m) < needs - 0.5;
  const heightSub = short ? `<span class="warn-text">needs about ${h(fmtNum(needs))}&nbsp;m</span> ` : "";
  // what the drawings will do about it, and the one figure that changes it, in a line under the four
  // the fix offered is one a building can take: a floor to floor of 2.8 m or more, else a taller height or fewer
  // storeys (17 Nov 2026: 19 storeys in 19.8 m advised a 1.04 m floor to floor)
  const fitF2f = short && o.storeys ? Math.floor(Number(o.height_m) / o.storeys * 100) / 100 : null;
  const fitStoreys = short ? Math.floor(Number(o.height_m) / f2f) : null;
  const heightFix = fitF2f >= 2.8 ? `To draw ${h(fmtNum(o.height_m))}&nbsp;m, set Floor to floor to ${h(fmtNum(fitF2f))}&nbsp;m under All figures.`
    : `Raise the height to about ${h(fmtNum(needs))}&nbsp;m, or plan ${h(fitStoreys)} storeys: that is what ${h(fmtNum(o.height_m))}&nbsp;m holds at ${h(fmtNum(f2f))}&nbsp;m a floor.`;
  // an impossible height is said once, in the note that holds Continue back; a tight one here, with its fix
  const impossible = o.storeys && o.height_m != null && Number(o.height_m) / o.storeys < 2.8;
  const heightLine = short && !impossible ? `<p class="help warn-text fig4-note">The drawings use ${h(fmtNum(needs))}&nbsp;m: ${h(o.storeys)} storeys × ${h(fmtNum(f2f))}&nbsp;m floor to floor. ${heightFix}</p>` : "";
  // a floor area the storeys cannot hold: each floor larger than the plate the setbacks leave (17 Nov 2026: FSR 6.01
  // on 6 storeys asked for 2,178 m² a floor on a 2,174.9 m² lot and passed without a word)
  const E0 = S && S.envelope;
  const boxArea = E0 && E0.plate_w_m && E0.plate_d_m ? E0.plate_w_m * E0.plate_d_m : (lot || null);
  const perFloor = o.gfa_m2 && o.storeys ? o.gfa_m2 / o.storeys : null;
  const floorLine = perFloor && boxArea && perFloor > boxArea * 1.01
    ? `<p class="help warn-text fig4-note">${h(fmtNum(o.gfa_m2))}&nbsp;m² on ${h(o.storeys)} floors is ${h(fmtNum(Math.round(perFloor)))}&nbsp;m² a floor, more than the ${h(fmtNum(Math.round(boxArea)))}&nbsp;m² ${E0 && E0.plate_w_m ? `the setbacks leave (${h(E0.plate_w_m)} × ${h(E0.plate_d_m)}&nbsp;m)` : "of the lot"}: plan ${h(Math.ceil(o.gfa_m2 / boxArea))} storeys or more, or less floor area.</p>` : "";
  const floorCell = lot ? cell("fsr", "FSR", fsr || "—", o.gfa_m2 != null ? `${h(fmtNum(o.gfa_m2))}&nbsp;m² ` : "")
    : cell("gfa_m2", "Floor area", o.gfa_m2 != null ? `${fmtNum(o.gfa_m2)} m²` : "—", "");
  const block = `<div class="fig4">
      ${cell("storeys", "Storeys", o.storeys != null ? String(o.storeys) : "—", "")}
      ${cell("height_m", "Height", o.height_m != null ? `${fmtNum(o.height_m)} m` : "—", heightSub)}
      ${floorCell}
      <div class="fig4-cell"><span class="fig4-k">Homes</span>${S && S.mix ? `<button type="button" class="fig4-v" id="guide-homes" aria-expanded="${!!guide.mixOpen}" aria-controls="guide-mix" aria-label="Homes: ${homes || "none"}. Change the mix">${homes || "—"}</button>` : `<span class="fig4-v">${homes || "—"}</span>`}<span class="fig4-sub">${o.rent_tiers_units ? `${h(o.rent_tiers_units.market || 0)} / ${h(o.rent_tiers_units.rgi || 0)} / ${h(o.rent_tiers_units.deep_subsidy || 0)} tiers` : ""}</span></div>
    </div>`;
  if (!S) return block + heightLine + floorLine + `<p class="help">${h(o.name || o.id || "The saved option")}: its figures are its file's. The architect's schedule holds every field.</p>`;
  // the rough envelope from the lot and the code, offered as the manager's own three figures
  const E = S.envelope;
  const envDiffers = E && E.storeys != null && ["storeys", "height_m", "gfa_m2"].some(k => guide.mine[k] !== undefined || (S.fields[k] || {}).value !== E[k]);
  const envLine = E && E.storeys != null ? `<p class="help env-line"><span class="cont">Rough allowed, from the lot and the code:</span> <b>${h(E.storeys)} storeys · ${h(E.height_m)} m · ${h(fmtNum(E.gfa_m2))} m²</b><span class="cont">${E.plate_w_m != null ? ` (${h(E.storeys)} floors inside a ${h(E.plate_w_m)} × ${h(E.plate_d_m)} m plate box)` : ""}. Not a permission.</span>${envDiffers ? ` <button class="btn btn-quiet btn-small" type="button" id="guide-use-envelope">Use the rough envelope</button>` : ""}</p>` : "";
  return block + heightLine + floorLine + envLine + (guide.mixOpen ? mixPanel(S) : "") + allFigures(S);
}

function mixPanel(S) {
  const M = S.mix;
  if (!M) return "";
  const shares = guide.mixShares || M.shares || { studio: 0.2, one_bed: 0.4, two_bed: 0.32, three_bed_plus: 0.08 };
  return `<div class="sg-mix" id="guide-mix">
      <div class="mix-row">
        <label class="field"><span class="label">The mix</span><select id="guide-mix-preset"><option value="">${M.source === "yours" ? "your shares" : "the starting mix"}</option>${Object.entries(M.presets || {}).map(([k, p]) => `<option value="${h(k)}" title="${h(p.note || "")}">${h(cap(k.replace(/_/g, " ")))} · ${["studio", "one_bed", "two_bed", "three_bed_plus"].map(u => Math.round((p.shares[u] || 0) * 100)).join(" / ")}%</option>`).join("")}</select></label>
        ${[["studio", "Studio"], ["one_bed", "1-bed"], ["two_bed", "2-bed"], ["three_bed_plus", "3-bed+"]].map(([u, l]) => `<label class="field"><span class="label">${l} %</span><input type="number" class="mix-share" data-unit="${u}" min="0" max="100" step="1" value="${h(Math.round((shares[u] || 0) * 100))}" aria-label="${l}, share of homes"></label>`).join("")}
      </div>
      <div class="form-actions"><button class="btn btn-small" type="button" id="guide-mix-apply">Derive with this mix</button><span class="help">Homes sized at the BC Housing minimum net areas (${["studio", "one_bed", "two_bed", "three_bed_plus"].map(u => (M.unit_areas_m2 || {})[u]).join(" / ")} m² + ${Math.round(((M.allowance || 1.1) - 1) * 100)}%); the family-unit minimums still apply.</span></div>
    </div>`;
}

/* A figure as the stage shows it and takes it: a share as a percentage. */
const shareShown = (k, v) => (typeof v === "number" ? shareToScreen(k, v) : v);

/* A row's label in a status sentence. */
const rowLabel = k => { const r = GUIDE_FIELDS.find(([x]) => x === k); return r ? r[1] : (fieldOf("option", k) || {}).label || k; };

/* The suggestion's every figure, each Suggested | Mine with what it rests on: behind one fold. */
function allFigures(S) {
  const CORE = new Set(["storeys", "height_m", "gfa_m2"]);
  const rowOf = ([k, label, kind]) => {
    const f = S.fields[k] || { value: null, rule_id: null, note: `no rule in the stack derives this for ${state.site && state.site.zoning_district ? state.site.zoning_district : "this district"}: enter it, or leave it blank and the memo says the envelope was not assessed` };
    if (guide.mine[k] === undefined && (f.value === null || f.value === undefined) && CORE.has(k)) guide.mine[k] = "";
    const mine = guide.mine[k];
    const isMine = mine !== undefined;
    if (isShare(k)) label = `${label} (%)`;
    // a figure no rule derives says so in words, not a dash (17 Nov 2026: "Rezoning path —")
    const sv = f.value === null || f.value === undefined ? (kind === "text" ? "not derived" : "—")
      : (typeof f.value === "number" ? fmtNum(shareShown(k, f.value)) : String(f.value));
    const rests = f.rule_id ? `<span class="sg-ref" title="${h(ruleTitle(f.rule_id))}">${h(refNow(f.rule_id) || ruleTitle(f.rule_id))}</span>` : (f.basis === "envelope" ? `<span class="sg-ref ph">rough</span>` : `<span class="sg-ref ph">placeholder</span>`);
    return `<div class="sg-row" data-key="${h(k)}">
      <div class="sg-label">${h(label)}${rests}</div>
      <div class="sg-pick seg" role="group" aria-label="${h(label)}: suggested or mine">
        <button class="segbtn" type="button" data-pick="suggested" aria-pressed="${!isMine}">Suggested</button>
        <button class="segbtn" type="button" data-pick="mine" aria-pressed="${isMine}">Mine</button>
      </div>
      <div class="sg-value">${isMine ? `<input type="${kind === "text" ? "text" : "number"}" class="sg-input" value="${h(mine)}"${kind === "int" ? ' step="1"' : (kind === "number" ? ' step="any"' : "")} aria-label="${h(label)}, my figure"${CORE.has(k) && mine === "" ? ' placeholder="yours to enter"' : ""}>` : `<b>${h(sv)}</b>`}</div>
    </div>`;
  };
  const GROUPS = [
    ["The envelope", k => ["rezoning_path", "storeys", "height_m", "gfa_m2"].includes(k)],
    ["The homes", k => k.startsWith("units.") || k.startsWith("rent_tiers_units.") || k === "accessible_units"],
    ["The funders' terms", k => ["share_below_hils", "housing_agreement_years", "below_market_unit_share", "below_market_discount"].includes(k)],
    ["Drawing assumptions", k => ["replacement_trees_proposed", "floor_to_floor_m"].includes(k) || k.startsWith("setbacks_m.")],
  ];
  const n = GUIDE_FIELDS.filter(([k]) => S.fields[k] || CORE.has(k)).length;
  const rows = GROUPS.map(([title, test]) => {
    const fields = GUIDE_FIELDS.filter(([k]) => test(k) && (S.fields[k] || CORE.has(k)));
    return fields.length ? `<div class="sg-group"><h4 class="sg-head">${h(title)}</h4>${fields.map(rowOf).join("")}</div>` : "";
  }).join("");
  return `<details class="fold all-figures" id="all-figures"${guide.allOpen ? " open" : ""}><summary>All ${n} figures, and what each rests on</summary><div class="sg-rows">${rows}</div></details>`;
}

/* What the suggestion leaves to a person that no question above settles: one quiet line each. */
function leftToPerson(S, fromSaved) {
  if (!S || fromSaved || !S.unsure || !S.unsure.length) return "";
  const rest = S.unsure.filter(u => !ANSWERS[u.key]);
  if (!rest.length) return "";
  return `<ul class="left-list">${rest.map(u => `<li><b>${h(keyLabel(u.key))}</b>: ${h(u.why)}. <span class="cont">${h(u.who)}.</span></li>`).join("")}</ul>`;
}

// ---- 03 run

function cardRun() {
  const site = state.site || {};
  const o = state.option || {};
  const fin = o.finance || {};
  const ownerType = String(site.owner_type || "").toLowerCase();
  const nominal = /church|society|non.?profit|co-?op|first.?nation|municipal|city|province|government/.test(ownerType);
  const busy = !!state.running;
  // the owner in the words the question offered ("the City", not "a municipality"; 17 Nov 2026)
  const owner = site.owner_type ? ansWord("owner_type", site.owner_type) : "";
  const ownerIs = /^(the|a|an) /i.test(owner) ? owner.charAt(0).toLowerCase() + owner.slice(1) : `${/^[aeiou]/i.test(owner) ? "an" : "a"} ${owner.toLowerCase()}`;
  const fields = FINANCE_FIELDS.map(([k, label]) => `<label class="field"><span class="label">${h(label)}</span><input type="number" step="any" inputmode="decimal" class="fin-input" data-key="${h(k)}" value="${h(getPath(fin, k.split(".")[1]) ?? "")}" placeholder="${k.endsWith("land_cost_cad") ? (nominal ? "blank: nominal" : "blank: unsure") : "blank: none"}"></label>`).join("");
  const money = `<details class="fold money-fold"${nominal && !Object.values(fin).some(v => v != null) ? "" : " open"}><summary>Land, equity and other grants <span class="cont">${nominal ? `· the land counts at a nominal value: the owner is ${h(ownerIs)}` : "· only you know these"}</span></summary>
      <div class="fin-rows">${fields}</div>
      <p class="help">${nominal ? "A blank land figure carries the land at a nominal value on a long lease." : (site.owner_type ? "Enter the assessed value or the agreed price; a blank leaves the money answer unsure." : "Name the owner at 01, or enter a land price here.")} The Community Housing Fund's provisional grant is counted on its own when the fund is targeted.</p>
    </details>`;
  const dl = `<dl class="stage-dl">
      <div><dt>The option</dt><dd><p class="dd-line">${optionSummary(o, state.site)}</p></dd></div>
      <div><dt>Money in</dt><dd>${money}<details class="fold"><summary>The assumptions the money counts with</summary>${stageMoney()}</details></dd></div>
      <div><dt>Rules as of</dt><dd><p class="dd-line"><code>${h($("#as-of").value || todayISO())}</code> <span class="cont">· the date in the top bar; the rules in force that day are read</span></p></dd></div>
    </dl>`;
  const quiet = `<button type="button" class="btn btn-quiet btn-small" id="guide-back-2">Back to the option</button>`;
  const main = `<span class="help kbd-help">Ctrl+Enter</span><button type="button" class="btn btn-primary" id="guide-run"${busy ? " disabled" : ""}>${busy ? "Running…" : "Run the rules"}</button>`;
  return stageCard(3, "Money in, then run", dl, foot(quiet, main));
}

// ---- wiring the card

function wireStage(el) {
  const on = (sel, fn) => { const b = $(sel, el); if (b) b.addEventListener("click", fn); };
  on("#stage-back", backToMemo);
  on("#stage-resume", () => resumeDraft(readDraft()).catch(e => toast(e.message, true)));
  on("#stage-discard", () => { discardDraft(); renderStage(); });
  on("#stage-demo", () => loadDemo().catch(e => toast(e.message, true)));
  $$("[data-open-run]", el).forEach(b => b.addEventListener("click", () => openRun(b.dataset.openRun).catch(e => toast(e.message, true))));
  // 01
  const addr = $("#guide-address", el);
  if (addr) {
    addr.addEventListener("input", () => { guide.address = addr.value; });
    addr.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); guideLookup(); } });
  }
  on("#guide-lookup", guideLookup);
  on("#guide-lookup-again", () => { guide.lookup = null; renderGuide(); const a = $("#guide-address"); if (a) { a.focus(); a.select(); } });
  on("#guide-use-site", guideUseSite);
  const saved = $("#guide-saved-site", el);
  if (saved) saved.addEventListener("change", () => useSavedSite(saved.value));
  on("#guide-change-site", () => { guide.changing = true; guide.lookup = null; renderGuide(); const a = $("#guide-address"); if (a) a.focus(); });
  on("#guide-keep-site", () => { guide.saveOpen = !guide.saveOpen; renderGuide(); const i = $("#stage-save-id"); if (i) i.focus(); });
  on("#stage-save-cancel", () => { guide.saveOpen = false; renderGuide(); });
  on("#stage-save-go", async () => { const ok = await saveNow("site", { id: ($("#stage-save-id") || {}).value }); if (ok) { guide.saveOpen = false; renderGuide(); } });
  const sid = $("#stage-save-id", el);
  if (sid) sid.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); $("#stage-save-go").click(); } if (e.key === "Escape") { guide.saveOpen = false; renderGuide(); } });
  on("#guide-next-1", () => goStop(2));
  // the questions: a radio group answers on a click and moves with the arrow keys; a select or a text box on change
  $$("[data-answer]", el).forEach(c => {
    if (c.tagName === "BUTTON") {
      c.addEventListener("click", () => { takeAnswer(c.dataset.answer, c.dataset.value); renderGuide(); });
      c.addEventListener("keydown", e => {
        const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
        if (!step) return;
        e.preventDefault();
        const group = $$("button", c.parentElement), i = group.indexOf(c), next = group[(i + step + group.length) % group.length];
        takeAnswer(next.dataset.answer, next.dataset.value); renderGuide();
        const again = $(`[data-answer="${next.dataset.answer}"][data-value="${next.dataset.value}"]`); if (again) again.focus();
      });
    } else c.addEventListener("change", () => { takeAnswer(c.dataset.answer, c.value); renderGuide(); });
  });
  // 02
  on("#guide-back-1", () => goStop(1));
  $$(".guide-program", el).forEach(c => c.addEventListener("change", () => {
    guide.programs = $$(".guide-program:checked", el).map(x => x.value);
    if (state.option && (state.optionId || guide.suggestionUsed)) { state.option.target_programs = guide.programs.slice(); onOptionChange("target_programs"); renderForm($("#option-form"), OPTION_FIELDS, state.option, onOptionChange); }
    setStatus(`The programs in view: ${guide.programs.map(ruleTitle).join("; ") || "none"}.`, "info");
    if (guide.suggestion && !state.optionId) guideSuggest(); else renderGuide();
  }));
  $$(".cands .segbtn", el).forEach(b => b.addEventListener("click", () => { guide.candidate = b.dataset.cand; guide.mine = {}; guideSuggest(); }));
  const savedOpt = $("#guide-saved-option", el);
  if (savedOpt) savedOpt.addEventListener("change", () => useSavedOption(savedOpt.value));
  $$("[data-fig]", el).forEach(b => b.addEventListener("click", () => { guide.editFig = b.dataset.fig; renderGuide(); const i = $(".fig4-input"); if (i) { i.focus(); i.select(); } }));
  const fi = $(".fig4-input", el);
  if (fi) {
    let done = false;
    const commit = keep => {
      if (done) return; done = true;
      const key = fi.dataset.figInput, raw = fi.value.trim();
      guide.editFig = null;
      if (keep) setFigure(key, raw);
      renderGuide();
      const b = $(`[data-fig="${key}"]`); if (b) b.focus();
    };
    fi.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); commit(true); } if (e.key === "Escape") { e.preventDefault(); commit(false); } });
    fi.addEventListener("blur", () => commit(true));
  }
  on("#guide-homes", () => { guide.mixOpen = !guide.mixOpen; renderGuide(); });
  on("#guide-use-envelope", () => {
    const E = guide.suggestion && guide.suggestion.envelope; if (!E) return;
    guide.mine.storeys = String(E.storeys); guide.mine.height_m = String(E.height_m); guide.mine.gfa_m2 = String(E.gfa_m2);
    guide.suggestionUsed = false;
    guideSuggest({ said: `Storeys ${E.storeys}, height ${E.height_m} m and floor area ${fmtNum(E.gfa_m2)} m² are now yours, from the rough envelope: ${E.storeys_from}.` });
  });
  on("#guide-mix-apply", () => {
    const shares = {};
    let total = 0;
    for (const inp of $$(".mix-share", el)) { const v = Math.max(0, Number(inp.value) || 0); shares[inp.dataset.unit] = v / 100; total += v; }
    if (Math.abs(total - 100) > 1) { toast(`The shares add up to ${total}%, not 100%.`, true); return; }
    guide.mixShares = shares; guide.mine = Object.fromEntries(Object.entries(guide.mine).filter(([k]) => !k.startsWith("units.") && !k.startsWith("rent_tiers")));
    guideSuggest();
  });
  const preset = $("#guide-mix-preset", el);
  if (preset) preset.addEventListener("change", () => {
    const p = guide.suggestion && guide.suggestion.mix && guide.suggestion.mix.presets && guide.suggestion.mix.presets[preset.value];
    if (!p) return;
    for (const inp of $$(".mix-share", el)) inp.value = Math.round((p.shares[inp.dataset.unit] || 0) * 100);
  });
  $$(".mix-share", el).forEach(inp => inp.addEventListener("input", () => { const p = $("#guide-mix-preset", el); if (p) p.value = ""; }));
  const all = $("#all-figures", el);
  if (all) all.addEventListener("toggle", () => { guide.allOpen = all.open; });
  $$(".sg-row", el).forEach(row => {
    const key = row.dataset.key;
    $$(".sg-pick .segbtn", row).forEach(b => b.addEventListener("click", () => {
      if (b.dataset.pick === "mine") { if (guide.mine[key] === undefined) guide.mine[key] = shareShown(key, guide.suggestion.fields[key].value) ?? ""; }
      else delete guide.mine[key];
      guide.suggestionUsed = false;
      // back to the suggested figure: a change too, and the figures that follow it are derived again
      if (b.dataset.pick === "suggested") {
        if (DERIVES(key)) { guideSuggest({ said: `${rowLabel(key)}: the suggested figure again.` }); return; }
        applyAfterRun();
      }
      renderGuide();
      const inp = $(`.sg-row[data-key="${CSS.escape(key)}"] .sg-input`);
      if (inp) inp.focus();
    }));
    const inp = $(".sg-input", row);
    if (inp) {
      inp.addEventListener("input", () => { guide.mine[key] = inp.value; guide.suggestionUsed = false; });
      inp.addEventListener("change", () => {
        if (DERIVES(key)) { guideSuggest({ said: `${rowLabel(key)}: ${inp.value.trim() === "" ? "blank" : inp.value.trim()}, yours.` }); return; }
        applyAfterRun(); renderGuide();
      });
    }
  });
  on("#guide-next-2", continueToRun);
  // 03
  on("#guide-back-2", () => goStop(2));
  $$(".fin-input", el).forEach(inp => inp.addEventListener("input", () => {
    if (!state.option) return;
    const raw = inp.value.trim();
    state.option.finance = state.option.finance || {};
    setPath(state.option, inp.dataset.key, raw === "" ? null : Number(raw));
    state.optionDirty = true;
    $("#option-dirty").hidden = false;
    renderForm($("#option-form"), OPTION_FIELDS, state.option, onOptionChange);
    markStale("the money in");
    saveDraft();
  }));
  on("#guide-run", () => runRules());
}

/* After a run, a change at 02 is a change to the option the memo was made from: it is applied at once, so the memo
   is marked out of date, Run again goes live and the route shows the new figures (17 Nov 2026: the change waited for
   Continue, and Back to R1 showed a memo that still read as current). Before a run, Continue applies it. */
function applyAfterRun() {
  if (state.run && guide.suggestion && !state.optionId) useSuggestion({ live: true });
}

/* A figure typed into the four-figure block: the manager's own over the suggestion, or straight into a saved option. */
function setFigure(key, raw) {
  const asked = key;
  let said = null;
  if (key === "fsr") {
    const lot = Number((state.site || {}).site_area_m2) || 0;
    const f = raw === "" ? null : Number(raw);
    if (raw !== "" && !(Number.isFinite(f) && f > 0)) { toast("Not a floor space ratio: enter a number such as 2.5.", true); return; }
    key = "gfa_m2";
    raw = f == null ? "" : String(Math.round(f * lot));
    if (f != null) said = `FSR ${fmtNum(f)}, yours: ${fmtNum(Math.round(f * lot))} m² on the ${fmtNum(lot)} m² lot.`;
  }
  if (guide.suggestion && !state.optionId) {
    if (raw === "" && guide.mine[key] === undefined) return;
    guide.mine[key] = raw;
    guide.suggestionUsed = false;
    // the unit after the figure, as the four figures show it ("Height: 61.6 m", not "Height (m): 61.6")
    const label = fieldOf("option", key).label.replace(/ \((m|m²)\)$/, "");
    const unit = key === "height_m" ? " m" : key === "gfa_m2" ? " m²" : "";
    const msg = raw === "" ? `${label}: blank, so not assessed.` : (said || `${label}: ${Number.isFinite(Number(raw)) ? fmtNum(Number(raw)) : raw}${unit}, yours.`);
    // storeys, height and floor area carry the homes, the tiers and the accessible units: derive them again
    if (DERIVES(key)) { guideSuggest({ said: msg, focus: `[data-fig="${asked}"]` }); return; }
    setStatus(`${msg} ${continueWords()}`, "info");
    applyAfterRun();
    return;
  }
  if (!state.option) return;
  const v = raw === "" ? null : Number(raw);
  if (raw !== "" && !Number.isFinite(v)) { toast("Not a number.", true); return; }
  setPath(state.option, key, v);
  onOptionChange(key);
  renderForm($("#option-form"), OPTION_FIELDS, state.option, onOptionChange);
}

async function useSavedSite(id) {
  if (!id) return;
  if ((state.siteDirty || state.optionDirty) && state.site && !confirm("Switch the site? Unsaved edits to the site and option will be lost.")) { renderGuide(); return; }
  try {
    $("#site-select").value = id;
    await selectSite(id);
    guide.changing = false; guide.lookup = null; guide.step = 1;
    renderGuide();
    focusStage();
    setStatus(`${state.site.address || id} is the site. Check what the open data could not tell, then continue to the option.`, "ok");
  } catch (e) { toast(e.message, true); }
}

async function useSavedOption(id) {
  const target = id || "__new__";
  if (state.optionDirty && state.option && target !== "__new__" && state.optionId !== target && !confirm("Switch the option? Unsaved edits to the option will be lost.")) { renderGuide(); return; }
  try {
    $("#option-select").value = target;
    await selectOption(target);
    if (target === "__new__") { guideSuggest(); return; }
    guide.mine = {}; guide.suggestionUsed = false; guide.editFig = null;
    guide.programs = (state.option.target_programs || []).slice();
    renderGuide();
    setStatus(`${state.option.name || id} is the option. Continue to the run when it reads right.`, "ok");
  } catch (e) { toast(e.message, true); }
}

function continueToRun() {
  if (guide.suggestion && !state.optionId && !guide.suggestionUsed) { if (!useSuggestion()) return; }
  if (!progress().option) { toast("Choose where to start first: a candidate or a saved option.", true); return; }
  goStop(3);
}
