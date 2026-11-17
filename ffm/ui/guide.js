/* The route's actions: look up an address, use a found or saved site, read the site (layers A to C), derive an
   option from the rules and use it. */

import { $, cap, fmtNum, getPath, h, leadCont, pill, setPath, setStatus, toast, todayISO } from "./core/util.js";
import { guide, state } from "./core/state.js";
import { api, postJSON } from "./core/api.js";
import { ANSWERS, GUIDE_FIELDS, OPTION_FIELDS, shareFromScreen, SITE_FIELDS } from "./fields.js";
import { refreshSummary, renderForm } from "./schedule.js";
import { blankOption, blankSite, loadOptions, markStale, onOptionChange, onSiteChange } from "./files.js";
import { fillRunSelects, loadRuns, rev } from "./runs.js";
import { placeRunTools } from "./memo/memo.js";
import { defaultPrograms, focusStage, renderGuide, renderStage } from "./route-stage.js";
import { setStep } from "./modes.js";

// ---- the stops' work: the lookup, the site, the reading, the suggestion, the option

export async function guideLookup() {
  const q = (guide.address || "").trim();
  if (q.length < 4) { toast("Type an address first.", true); const a = $("#guide-address"); if (a) a.focus(); return; }
  guide.busy.lookup = true; renderGuide();
  setStatus(`Looking up ${q}: the point, the district, the parcel, and the streets, buildings and trees around it…`, "busy");
  try {
    guide.lookup = await api(`/api/lookup?q=${encodeURIComponent(q)}`);
    const s = guide.lookup.site;
    setStatus(`Found ${s.address}: ${s.zoning_district || "district not found"}, ${s.site_area_m2 ? `${fmtNum(s.site_area_m2)} m²` : "no parcel"}. Check the parcel on the map, then use it.`, "ok");
  } catch (e) {
    guide.lookup = null;
    toast(`Lookup failed: ${e.message}`, true);
  } finally {
    guide.busy.lookup = false; renderGuide();
    const b = $("#guide-use-site") || $("#guide-address"); if (b) b.focus({ preventScroll: true });
  }
}

/* The found site becomes a new, unsaved site; the card then asks what the open data could not tell. */
export async function guideUseSite() {
  if (!guide.lookup) return;
  // a site that was typed into and never saved is asked about on the page itself: the first click warns
  const touched = state.siteDirty && state.site && (state.siteId || state.site.address) && !guide.changing;
  if (touched && !guide.confirmSite) {
    guide.confirmSite = true;
    const b = $("#guide-use-site");
    if (b) b.textContent = "Replace the edited site";
    setStatus("The site on screen holds edits that were never saved. Click again to replace it with the found site, or keep it as a file first.", "busy");
    return;
  }
  guide.confirmSite = false;
  state.siteId = null;
  state.site = Object.assign(blankSite(), guide.lookup.site);
  state.siteDirty = true;
  $("#site-select").value = "__new__";
  renderForm($("#site-form"), SITE_FIELDS, state.site, onSiteChange);
  $("#site-dirty").hidden = false;
  refreshSummary("site");
  await loadOptions();
  await loadRuns();
  fillRunSelects();
  guide.reading = null; guide.suggestion = null; guide.mine = {}; guide.answers = {}; guide.proposal = null; guide.suggestionUsed = false;
  guide.step = 1; guide.changing = false; guide.lookup = null;
  renderGuide();
  focusStage();
  setStep(1);
  setStatus("The site is set, unsaved. Answer what the open data could not tell, or leave it not sure, then continue to the option.", "ok");
}

export async function guideReadSite() {
  if (!state.site) return;
  guide.busy.read = true; guide.readStale = false; renderGuide();
  try {
    guide.reading = await postJSON("/api/read-site", { site: state.site, as_of: $("#as-of").value || todayISO() });
    renderSiteReading(guide.reading);
  } catch (e) {
    toast(`Could not read the site: ${e.message}`, true);
  } finally {
    guide.busy.read = false; renderGuide();
  }
}

/* The site's reading sits in the memo pane until a run replaces it (the architect's and the reader's page); the
   manager's stage carries it at 02. */
function renderSiteReading(R) {
  if (state.mode === "manager") { renderStage(); return; }
  const site = R.site || state.site || {};
  const rows = R.results.map(r => `<li class="finding-row">${pill(r.status)} <div><b>${h(r.title)}</b> <span class="rule-id">${h(r.rule_id)}</span><p class="finding">${leadCont(r.finding)}</p>${r.action ? `<p class="who">${h(r.action)}</p>` : ""}</div></li>`).join("");
  placeRunTools(false);
  $("#memo").innerHTML = `
    <div class="card memo-head">
      <h1>${h(site.address || site.id || "A site")}</h1>
      <div class="memo-meta">
        <div><b>District</b><span>${h(site.zoning_district || "—")}</span></div>
        <div><b>Lot</b><span>${site.site_area_m2 ? `${h(fmtNum(site.site_area_m2))} m²` : "—"}${site.frontage_m ? ` · ${h(site.frontage_m)} × ${h(site.depth_m)} m` : ""}</span></div>
        <div><b>Rules as of</b><span>${h(R.as_of)}</span></div>
        <div><b>Reading</b><span>the site alone, layers A to C</span></div>
      </div>
      <p class="quiet">What the site allows and asks before any option exists. The option's own answers come with the run.</p>
    </div>
    <section class="card section reading"><h2>What the rules say about the site</h2><ul class="reading-findings">${rows}</ul></section>`;
  $("#memo").className = "memo landed";
}

/* The manager's own storeys, height, floor area and unit counts, as the derivation takes them: the homes, the rent
   tiers and the accessible units then follow what the manager typed, not the suggestion's own envelope (17 Nov 2026). */
function fixedFigures() {
  const num = k => {
    const raw = guide.mine[k];
    if (raw === undefined || String(raw).trim() === "") return null;
    const v = Number(String(raw).trim());
    return Number.isFinite(v) && v > 0 ? v : null;
  };
  const out = {};
  for (const k of ["storeys", "height_m", "gfa_m2"]) { const v = num(k); if (v != null) out[k] = k === "storeys" ? Math.round(v) : v; }
  const units = {};
  for (const u of ["studio", "one_bed", "two_bed", "three_bed_plus"]) {
    const raw = guide.mine[`units.${u}`];
    if (raw === undefined || String(raw).trim() === "") continue;
    const v = Number(String(raw).trim());
    if (Number.isFinite(v) && v >= 0) units[u] = Math.round(v);
  }
  if (Object.keys(units).length) out.units = units;
  return Object.keys(out).length ? out : null;
}

/* The figures that other figures follow: a change to one re-derives the option. */
export const DERIVES = k => ["storeys", "height_m", "gfa_m2"].includes(k) || k.startsWith("units.");

/* `said`: the sentence for the status line when a figure of the manager's caused the derivation; the derived homes
   follow it, rather than the suggestion's own summary, which would contradict the figure just typed. */
export async function guideSuggest(opts = {}) {
  if (!state.site) return;
  guide.busy.suggest = true; guide.suggestStale = false; guide.editFig = null; renderGuide();
  setStatus(opts.said ? `${opts.said} Deriving the homes and the funders' figures from it…` : `Deriving the ${guide.candidate} option from the rules…`, "busy");
  try {
    const programs = guide.programs || (state.option && state.optionId && state.option.target_programs) || defaultPrograms();
    guide.suggestion = await postJSON("/api/suggest", { site: state.site, programs, as_of: $("#as-of").value || todayISO(), candidate: guide.candidate, mix_shares: guide.mixShares || null, fixed: fixedFigures() });
    guide.suggestionUsed = false;   // a fresh suggestion waits for Continue; the stage shows it as such
    if (state.optionId) { state.optionId = null; $("#option-select").value = "__new__"; }   // a derived option replaces the saved one on the stage until Continue
    // a blank Mine row that stood in for a figure no rule gave gives way once the derivation has one (16 Nov 2026)
    for (const k of ["storeys", "height_m", "gfa_m2"]) if (guide.mine[k] === "" && (guide.suggestion.fields[k] || {}).value != null) delete guide.mine[k];
    const asked = guide.candidate;
    guide.candidate = guide.suggestion.candidate;
    const o = guide.suggestion.option;
    const cv = guide.suggestion.unsure.some(u => u.key === "in_former_community_vision_area") && guide.candidate !== "outright";
    const rough = ["storeys", "height_m", "gfa_m2"].some(k => (guide.suggestion.fields[k] || {}).basis === "envelope");
    const swapped = guide.suggestion.candidate_note && asked !== guide.candidate;
    const homes = Object.values(o.units || {}).reduce((t, v) => t + (v || 0), 0);
    if (opts.said) setStatus(`${opts.said} ${homes ? `${homes} homes follow from the figures, the rent tiers and accessible units with them.` : "No homes follow yet: enter a floor area."} Continue to the run when it reads right.`, "info");
    else setStatus(`Suggested, ${guide.candidate}: ${o.storeys ?? "?"} storeys, ${o.gfa_m2 ? `${fmtNum(o.gfa_m2)} m²` : "no floor area"}, ${Object.values(o.units || {}).reduce((t, v) => t + (v || 0), 0) || "no"} homes.${rough ? " The envelope is rough, from the lot and the code, not a permitted figure." : ""}${cv ? " The benchmark needs the Community Vision answer at 01; until then this is the outright envelope." : ""}${swapped ? ` ${guide.suggestion.candidate_note}` : ""}`, cv || swapped ? "info" : "ok");
    // after a run, a new derivation (another candidate, a mix, the programs) is a change to the memo's option
    if (state.run) useSuggestion({ live: true });
  } catch (e) {
    toast(`Could not derive the option: ${e.message}`, true);
  } finally {
    guide.busy.suggest = false; renderGuide();
    // the figure just typed keeps the keyboard's place once the card is drawn again
    if (opts.focus) { const b = $(opts.focus); if (b) b.focus(); }
  }
}

/* The suggestion, with the manager's own figures where they chose Mine, becomes the option; true when it did.
   `live`: a change made at 02 after a run, applied at once so the memo on screen is marked out of date (17 Nov
   2026: the figure waited for Continue, and the memo kept reading as current). */
export function useSuggestion(opts = {}) {
  try { return useSuggestionNow(opts); }
  catch (e) { toast(`Could not use the option: ${e.message}`, true); console.error(e); return false; }
}

function useSuggestionNow({ live = false } = {}) {
  const S = guide.suggestion;
  if (!S) return false;
  // an option edited some other way and never saved (a saved option changed in the architect's schedule) is asked
  // about on the page itself: the first click warns and marks the button, the second goes ahead. The option this
  // suggestion wrote itself is the manager's own and is replaced without asking (17 Nov 2026: it was mistaken for
  // "edits that were never saved", so every change after a run needed a second Continue).
  const touched = !live && state.optionDirty && state.option && state.option !== guide.appliedOption
    && (state.optionId || state.option.storeys != null);
  if (touched && !guide.confirmUse) {
    guide.confirmUse = true;
    renderGuide();
    setStatus("The option on screen holds edits that were never saved. Continue again to replace them with this one.", "busy");
    return false;
  }
  guide.confirmUse = false;
  const opt = Object.assign(blankOption(state.site && state.site.id), JSON.parse(JSON.stringify(S.option)));
  for (const [k, label, kind] of GUIDE_FIELDS) {
    if (guide.mine[k] === undefined) continue;
    const raw = String(guide.mine[k]).trim();
    const v = kind === "text" ? (raw || null) : (raw === "" ? null : (kind === "int" ? parseInt(raw, 10) : shareFromScreen(k, Number(raw))));
    if (kind !== "text" && raw !== "" && !Number.isFinite(v)) { toast(`${label}: not a number.`, true); return false; }
    setPath(opt, k, v);
  }
  for (const [k, v] of Object.entries(guide.answers || {})) if (ANSWERS[k] && ANSWERS[k].on === "option") setPath(opt, k, v);
  if (guide.programs) opt.target_programs = guide.programs.slice();
  if (state.option && state.option.finance) opt.finance = Object.assign({}, state.option.finance);   // the money in survives a change of option
  if (!opt.rent_tiers_units || Object.values(opt.rent_tiers_units).every(v => v == null)) opt.rent_tiers_units = null;
  // only a figure actually typed counts as the manager's own; a blank Mine row is a blank, and the strip says what it costs
  const typed = GUIDE_FIELDS.filter(([k]) => guide.mine[k] !== undefined && String(guide.mine[k]).trim() !== "");
  const blank = GUIDE_FIELDS.filter(([k]) => ["storeys", "height_m", "gfa_m2"].includes(k) && getPath(opt, k) == null).map(([, label]) => label);
  const chosen = typed.length;
  opt.notes = (opt.notes || "") + (chosen ? ` ${chosen} figure${chosen === 1 ? "" : "s"} entered by the manager: ${typed.map(([, label]) => label).join(", ")}.` : "");
  // the name is a name: the candidate and how much of it is the manager's; the figures typed are listed in the notes
  // (17 Nov 2026: the name ran "…; rezoning path, storeys, height (m), floor area (m²), studios… entered by the
  // manager" across ten lines of the title block and cut off every run picker)
  const base = `${cap(guide.candidate)} option`;
  if (blank.length) opt.name = `${base}, ${blank.join(", ").toLowerCase()} not given`;
  else if (chosen) opt.name = `${base} with ${chosen === 1 ? "one figure" : `${chosen} figures`} of the manager's`;
  state.optionId = null;
  state.option = opt;
  state.optionDirty = true;
  guide.suggestionUsed = true;
  guide.appliedOption = opt;
  $("#option-select").value = "__new__";
  renderForm($("#option-form"), OPTION_FIELDS, state.option, onOptionChange);
  $("#option-dirty").hidden = false;
  refreshSummary("option");
  markStale("the option");
  setStep(2);
  if (live) {
    setStatus(`The option changed after ${rev(state.run.run_id)}: the memo on screen is ${rev(state.run.run_id)}'s until the rules run again.${blank.length ? ` ${blank.join(", ")} ${blank.length === 1 ? "is" : "are"} blank.` : ""}`, "busy");
    return true;
  }
  if (blank.length) setStatus(`The ${guide.candidate} option is set${chosen ? ` with ${chosen} of your own figures` : ""}, but ${blank.join(", ").toLowerCase()} ${blank.length === 1 ? "is" : "are"} blank: the run will answer allowed and funders, say the money is unsure and draw the plate the setbacks leave. Enter ${blank.length === 1 ? "it" : "them"} at 02 for all four answers, or run as it stands.`, "busy");
  else setStatus(`The ${guide.candidate} option is set${chosen ? `, with ${chosen} of your own figures` : ""}. Enter the money only you know, then run the rules.`, "ok");
  return true;
}
