/* The site and option files: listing, choosing, blank ones, editing, Save asâ€¦, the stale band an edit raises over a
   memo, and the unsaved draft kept in sessionStorage. */

import { $, h, setStatus, toast } from "./core/util.js";
import { guide, PRELOAD_OPTION, PRELOAD_SITE, state, STATIC } from "./core/state.js";
import { api, postJSON } from "./core/api.js";
import { OPTION_FIELDS, SITE_FIELDS } from "./fields.js";
import {
  envelopeLive, refreshNeeds, refreshSummary, renderForm, setCollapsed, syncCards, unitsLive
} from "./schedule.js";
import { fillRunSelects, loadRuns, rev, runRules, syncRunButton } from "./runs.js";
import { renderQuiet } from "./memo/memo.js";
import { setCompareNote } from "./memo/changes.js";
import { enterOption, focusStage, renderGuide, stopOf } from "./route-stage.js";
import { pollIssues } from "./issue.js";
import { setStep } from "./modes.js";

/* Load the demo case: the committed site and its as-approved option, then 02 with the option in place. */
export async function loadDemo() {
  const first = state.sites.some(s => s.id === PRELOAD_SITE) ? PRELOAD_SITE : (state.sites[0] ? state.sites[0].id : null);
  if (!first) { toast("No saved site to load.", true); return; }
  state.optionId = PRELOAD_OPTION;
  $("#site-select").value = first;
  await selectSite(first);
  guide.lookup = null; guide.changing = false;
  guide.programs = state.option && state.option.target_programs ? state.option.target_programs.slice() : null;
  if (state.mode === "manager") { guide.step = 2; renderGuide(); focusStage(); enterOption(); }
  setStatus(`The demo case is loaded: ${state.site.address}, the option as approved by Council. Continue to the run, or start from another candidate.`, "ok");
}

/* rent_tiers_units: all three blank means "not stated" (null), which the engine reads as unsure. */
export function tidyOption(opt) {
  const t = opt.rent_tiers_units;
  if (t && typeof t === "object" && ["market", "rgi", "deep_subsidy"].every(k => t[k] == null)) opt.rent_tiers_units = null;
  if (opt.setbacks_m && typeof opt.setbacks_m === "object") {
    for (const k of ["front", "rear", "side"]) if (opt.setbacks_m[k] == null) opt.setbacks_m[k] = 0;
  }
  return opt;
}

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

export function blankSite() {
  return { id: null, address: null, municipality: "City of Vancouver", zoning_district: null, site_area_m2: null, frontage_m: null, depth_m: null,
    in_former_community_vision_area: null, in_transit_oriented_area: null, toa_tier: null, frequent_bus_stop_within_400m: null,
    has_water_and_sewer: null, owner_type: null, owner: null, land_tenure_plan: null, keep_existing_buildings: null, existing_trees_on_site: [], street_trees: { count: null }, notes: null, sources: [] };
}

export function blankOption(siteId) {
  return { id: siteId ? `${siteId}-option` : null, name: null, proponent: null, proponent_type: "non_profit_society", developer_partner: null,
    tenure: "social_housing", rezoning_path: null, storeys: null, height_m: null, gfa_m2: null, residential_gfa_m2: null, non_residential_gfa_m2: null,
    units: { studio: null, one_bed: null, two_bed: null, three_bed_plus: null }, rent_tiers_units: null, share_below_hils: null, max_rent_share_of_income: null,
    owner_type_at_completion: null, housing_agreement_years: null, accessible_units: null, below_market_unit_share: null, below_market_discount: null,
    site_control: null, parking_spaces: null, bicycle_spaces: null, replacement_trees_proposed: null,
    target_programs: state.rules.filter(r => r.layer === "E" && /chf|bcbuilds/.test(r.id)).map(r => r.id),
    floor_to_floor_m: 3.0, setbacks_m: { front: 0, rear: 0, side: 0 }, notes: null, sources: [] };
}

export async function loadSites() {
  state.sites = await api("/api/sites");
  fillSelect($("#site-select"), state.sites.map(s => ({ value: s.id, label: `${s.address || s.id} · ${s.zoning_district || "?"}` })), state.siteId, "New site…");
}

export async function selectSite(id) {
  if (id === "__new__") {
    state.siteId = null;
    state.site = blankSite();
    state.siteDirty = true;
  } else {
    state.siteId = id;
    state.site = await api(`/api/sites/${encodeURIComponent(id)}`);
    state.siteDirty = false;
  }
  if (state.compareRun && !state.compareRun.startsWith((state.siteId || "") + "/")) { state.compareRun = null; setCompareNote(null); }   // a comparison never crosses sites
  renderForm($("#site-form"), SITE_FIELDS, state.site, onSiteChange);
  $("#site-dirty").hidden = !state.siteDirty;
  refreshSummary("site");
  setCollapsed("site", id !== "__new__" && state.mode !== "architect");
  await loadOptions();
  await loadRuns();
  fillRunSelects();
  setStep(state.step);
  guide.reading = null; guide.suggestion = null; guide.mine = {};
  renderGuide();
  pollIssues();
}

export function onSiteChange() {
  state.siteDirty = true;
  $("#site-dirty").hidden = false;
  refreshSummary("site");
  refreshNeeds($("#site-form"), SITE_FIELDS, state.site);
  markStale("the site");
  saveDraft();
}

export async function loadOptions() {
  const sid = state.siteId || (state.site && state.site.id) || "";
  state.options = await api(`/api/options?site=${encodeURIComponent(sid)}`);
  const forSite = state.options.filter(o => o.for_site);
  const others = state.options.filter(o => !o.for_site);
  const items = forSite.map(o => ({ value: o.id, label: o.name })).concat(others.map(o => ({ value: o.id, label: `(other site) ${o.name}` })));
  // the option stays only if it is the site's own: a site switch takes the new site's first option, not the old site's
  const current = (state.optionId && forSite.some(o => o.id === state.optionId)) ? state.optionId : (forSite[0] ? forSite[0].id : "__new__");
  fillSelect($("#option-select"), items, current, "New option…");
  await selectOption(current);
}

export async function selectOption(id) {
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
  setCollapsed("option", id !== "__new__" && state.mode !== "architect");
  renderQuiet();
  setStep(state.step);
}

export function onOptionChange(key) {
  state.optionDirty = true;
  $("#option-dirty").hidden = false;
  refreshSummary("option");
  refreshNeeds($("#option-form"), OPTION_FIELDS, state.option);
  markStale("the option");
  saveDraft();
  if (key && key.startsWith("units.")) {
    const live = $('[data-live="units"]');
    if (live) live.innerHTML = unitsLive(state.option);
  }
  if (!key || ["storeys", "height_m", "floor_to_floor_m", "gfa_m2"].includes(key) || key.startsWith("setbacks_m.")) {
    const live = $('[data-live="envelope"]');
    if (live) live.innerHTML = envelopeLive(state.option);
  }
}

/* Save as… opens an inline id field under the card (no browser prompt, which some browsers do not have); Save
   writes it, and an id that already exists comes back as a 409 the strip reports (15 Nov 2026). */
export function saveAs(kind) {
  const obj = kind === "site" ? state.site : state.option;
  if (!obj) return;
  const box = $(`#save-${kind}-inline`);
  const open = box.hidden;
  box.hidden = !open;
  $(`#save-${kind}`).setAttribute("aria-expanded", String(open));
  if (open) {
    const idEl = $(`#save-${kind}-id`);
    idEl.value = obj.id && obj.id !== "__new__" ? obj.id : (kind === "option" && state.site ? `${state.site.id || "site"}-${String(obj.name || guide.candidate || "option").toLowerCase().split(/[;,]/)[0].trim().replace(/[^a-z0-9._-]+/g, "-")}` : "");
    if (kind === "option") $("#save-option-name").value = obj.name || "";
    idEl.focus();
  }
}

/* Writes the site or the option as a file; true when it did. The id (and an option's name) come from the inline
   fields under the schedule, or from the caller (the manager's card at 01 has its own). */
export async function saveNow(kind, given = null) {
  const obj = kind === "site" ? state.site : tidyOption(state.option);
  if (!obj) return false;
  const idEl = $(`#save-${kind}-id`);
  const id = given ? given.id : idEl.value;
  if (!id || !id.trim()) { toast("Give the file an id first.", true); if (!given) idEl.focus(); return false; }
  const clean = id.trim().toLowerCase().replace(/[^a-z0-9._-]+/g, "-");
  const body = Object.assign({}, obj, { id: clean });
  if (kind === "option") body.name = ((given ? given.name : $("#save-option-name").value) || "").trim() || obj.name || clean;
  try {
    const r = await postJSON(kind === "site" ? "/api/sites" : "/api/options", body);
    if (r.downloaded) {
      obj.id = clean;
      toast(`Downloaded ${r.file}. Put it in the ${kind}s/ folder of the repository to keep it.`);
      return true;
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
    $(`#save-${kind}-inline`).hidden = true;
    $(`#save-${kind}`).setAttribute("aria-expanded", "false");
    saveDraft();
    return true;
  } catch (e) {
    toast(e.message, true);
    return false;
  }
}

/* An edit to the site, the option or the money after a run leaves the answers on screen out of date: a band over the
   memo says so, and Issue waits for a new run. runRules and openRun clear it. */
export function markStale(what) {
  if (!state.run || state.runStale) { if (state.run) syncStaleBand(); return; }
  state.runStale = what || "the inputs";
  syncStaleBand();
}

export function syncStaleBand() {
  const memo = $("#memo");
  if (!memo) return;
  let band = $("#stale-band", memo);
  const stale = !!(state.run && state.runStale);
  syncRunButton();   // the manager's Run again is live exactly while the memo is out of date
  if (!stale) { if (band) band.remove(); $("#issue-btn").disabled = !state.run || !!STATIC; $("#issue-btn").title = ""; return; }
  $("#issue-btn").disabled = true;
  $("#issue-btn").title = "The inputs changed after this run: run the rules again before issuing it.";
  // a card brought over the memo (the manager's route) holds the pane: the band waits for the memo, which draws it
  if (memo.classList.contains("stage-on")) return;
  if (!band) { band = document.createElement("div"); band.id = "stale-band"; band.className = "card stale-band"; band.setAttribute("role", "status"); memo.prepend(band); }
  band.innerHTML = `<b>${h(state.runStale[0].toUpperCase() + state.runStale.slice(1))} changed after ${h(rev(state.run.run_id))}.</b> The answers and the drawings below are ${h(rev(state.run.run_id))}'s. <button type="button" class="btn btn-primary btn-small" id="stale-run">Run the rules again</button>`;
  $("#stale-run", band).addEventListener("click", runRules);
  $("#issue-btn").disabled = true;
  $("#issue-btn").title = "The inputs changed after this run: run the rules again before issuing it.";
}

/* The guide's state and the unsaved site and option are kept in this tab's session storage, so a refresh offers to
   resume rather than starting from nothing. */
const DRAFT_KEY = "ffm.draft";

let draftTimer = null;

export function saveDraft() {
  clearTimeout(draftTimer);
  draftTimer = setTimeout(() => {
    try {
      if (state.mode !== "manager" || (!state.site && !guide.lookup)) { sessionStorage.removeItem(DRAFT_KEY); return; }
      const d = { version: 3, saved_at: new Date().toISOString(), as_of: $("#as-of").value, siteId: state.siteId, site: state.siteId ? null : state.site, siteDirty: state.siteDirty,
        optionId: state.optionId, option: state.optionId ? null : state.option, optionDirty: state.optionDirty,
        guide: { step: guide.step, address: guide.address, way: guide.way, programs: guide.programs, candidate: guide.candidate, mine: guide.mine, answers: guide.answers,
                 lookup: guide.lookup, suggestion: guide.suggestion, suggestionUsed: guide.suggestionUsed, reading: guide.reading } };
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify(d));
    } catch (e) { /* storage off or full: the draft is not kept */ }
  }, 400);
}

export function readDraft() {
  try { const d = JSON.parse(sessionStorage.getItem(DRAFT_KEY) || "null"); return d && (d.site || d.siteId || (d.guide && d.guide.lookup)) ? d : null; } catch (e) { return null; }
}

export async function resumeDraft(d) {
  if (d.as_of) $("#as-of").value = d.as_of;
  if (d.siteId && state.sites.some(s => s.id === d.siteId)) { $("#site-select").value = d.siteId; await selectSite(d.siteId); }
  else if (d.site) {
    state.siteId = null; state.site = d.site; state.siteDirty = !!d.siteDirty;
    $("#site-select").value = "__new__";
    renderForm($("#site-form"), SITE_FIELDS, state.site, onSiteChange);
    $("#site-dirty").hidden = !state.siteDirty;
    refreshSummary("site");
    await loadOptions(); await loadRuns(); fillRunSelects();
  }
  if (d.optionId && state.options.some(o => o.id === d.optionId)) { $("#option-select").value = d.optionId; await selectOption(d.optionId); }
  else if (d.option) {
    state.optionId = null; state.option = d.option; state.optionDirty = !!d.optionDirty;
    $("#option-select").value = "__new__";
    renderForm($("#option-form"), OPTION_FIELDS, state.option, onOptionChange);
    $("#option-dirty").hidden = !state.optionDirty;
    refreshSummary("option");
  }
  Object.assign(guide, d.guide || {});
  guide.busy = {};
  guide.step = d.version === 3 ? (guide.step || 1) : stopOf(guide.step);   // a draft from the seven-stop guide
  if (!guide.mine) guide.mine = {};
  syncCards();
  renderGuide();
  focusStage();
  setStatus(`Resumed where you were: ${state.site ? (state.site.address || state.site.id) : "a lookup"}, at 0${guide.step || 1}.`, "ok");
}

export function discardDraft() {
  try { sessionStorage.removeItem(DRAFT_KEY); } catch (e) { /* fine */ }
}
