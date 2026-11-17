/* Runs: the Run button, running the rules, the run list and its revisions (R1, R2â€¦), opening a past run, the
   comparison with another, and the URL that names what is on screen (?run=, ?compare=). */

import { $, h, scrollBehavior, setStatus, toast, todayISO } from "./core/util.js";
import { guide, state, STATIC } from "./core/state.js";
import { api, postJSON } from "./core/api.js";
import { engine, loadEngine } from "./core/engine.js";
import { OPTION_FIELDS, SITE_FIELDS } from "./fields.js";
import { refreshSummary, renderForm, syncCards } from "./schedule.js";
import {
  blankOption, blankSite, loadOptions, onOptionChange, onSiteChange, selectOption, selectSite, tidyOption
} from "./files.js";
import { renderMemo } from "./memo/memo.js";
import { attachCause, compareSummary, setCompareNote } from "./memo/changes.js";
import { renderPreview3D } from "./figures/cards.js";
import { closeExportPanel } from "./revit.js";
import { progress, renderGuide, renderRoute, renderStage, stageShown } from "./route-stage.js";
import { closeIssuePanel } from "./issue.js";
import { setStep, showInputs } from "./modes.js";

/* The top bar's Run. The architect's is the one loud button. The manager runs from the card at 03, so theirs waits
   until there is a memo, then reads Run again, quiet, live only once an edit has left the memo out of date. */
export function syncRunButton() {
  const b = $("#run-btn");
  if (!b) return;
  const p = progress();
  if (state.mode === "manager") {
    b.hidden = !state.run;
    b.classList.add("btn-again");
    b.textContent = state.running ? "Running…" : "Run again";
    const ok = !!(state.runStale && p.site && p.option);
    b.setAttribute("aria-disabled", String(!ok));
    b.title = ok ? `Run the rules again: ${state.runStale} changed (Ctrl+Enter)` : "Nothing has changed since this run";
    return;
  }
  b.hidden = false;
  b.classList.remove("btn-again");
  b.textContent = state.running ? "Running…" : "Run the rules";
  const ok = !!(p.site && state.option);
  b.setAttribute("aria-disabled", String(!ok));
  b.title = ok ? "Run the rules (Ctrl+Enter)" : (!p.site ? "Choose a site first" : "Choose an option first");
}

export async function loadRuns(siteId = null) {
  const sid = siteId || state.siteId || (state.site && state.site.id);
  state.runs = sid ? await api(`/api/runs?site=${encodeURIComponent(sid)}`) : [];
  noteRevisions(state.runs);
  // the route names the memo by its revision: drawn before the revisions were known, it said "a new revision" for R1
  // (17 Nov 2026)
  renderRoute();
}

/* A memo's revision on its site, R1, R2 and so on, the way a drawing numbers its issues. The committed runs come
   first: the base runs, then the runs recorded against another (they carry a diff), each group by its as-of date
   and folder. Then the runs made here, in the order they were made (their folders are timestamps), so a new run
   always takes the next number. On 998 E 19th Ave the as-approved memo is R1 and the funder-ready what-if R2. The
   rules stamp behind a memo appears only as the fingerprint in its Rules fingerprint card. */
const madeHere = r => /^(\d{4}-\d\d-\d\dT|browser-)/.test(r.folder || "");

function noteRevisions(runs) {
  const list = (runs || []).filter(r => r && r.run_id);
  const committed = list.filter(r => !madeHere(r)).sort((a, b) => (a.has_diff ? 1 : 0) - (b.has_diff ? 1 : 0)
    || String(a.as_of).localeCompare(String(b.as_of)) || String(a.folder).localeCompare(String(b.folder)));
  const made = list.filter(madeHere).sort((a, b) => String(a.written || a.folder).localeCompare(String(b.written || b.folder)));
  state.revisions = new Map([...committed, ...made].map((r, i) => [r.run_id, `R${i + 1}`]));
}

/* A run as the reader names it: its revision on the site. */
export const rev = runId => (runId && state.revisions.get(runId)) || "a new revision";

/* Runs in revision order, R1 first. */
export const byRev = runs => runs.slice().sort((a, b) => (Number(String(rev(a.run_id)).slice(1)) || 1e9) - (Number(String(rev(b.run_id)).slice(1)) || 1e9));

export async function runRules() {
  const btn = $("#run-btn");
  if (state.running) return;   // a second click while a run is in flight made a second revision of the same inputs
  const p = progress();
  if (!p.site || !state.option || (state.mode === "manager" && !p.option)) {
    toast(!p.site ? "Nothing to run yet: choose a site at 01." : "Nothing to run yet: choose the option at 02.", true);
    return;
  }
  state.running = true;
  btn.classList.add("busy");
  syncRunButton();
  const cardBtn = $("#guide-run"); if (cardBtn) { cardBtn.disabled = true; cardBtn.textContent = "Running…"; }
  setStatus("Running the rules…", "busy");
  try {
    if (STATIC && !engine) { setStatus("Loading the rules engine in your browser…", "busy"); await loadEngine(); }
    const body = { site: state.site, option: tidyOption(state.option), as_of: $("#as-of").value || todayISO(), previous_run: state.compareRun || null };
    const t0 = performance.now();
    const run = await postJSON("/api/run", body);
    state.run = run;
    state.runStale = null;
    guide.over = false;
    await loadRuns();   // the new run joins the list first, so it takes the next revision number
    await attachCause(run);
    renderMemo(run);
    showStamp(run);
    enableExports(run);
    setStep(3);
    closeExportPanel();
    fillRunSelects();
    setCompareNote(run.diff);
    syncUrl();
    // the manager's route folds once the memo is in: the memo takes the width (the reader's own choice is not changed)
    if (state.mode === "manager") showInputs(false, false);
    renderRoute();
    const ms = Math.round(performance.now() - t0);
    toast(`Ran the rules as of ${run.as_of}: ${rev(run.run_id)}, in ${ms} ms${run.diff ? ` · ${compareSummary(run)}` : ""}. Download PDF is under the title.`);
    // where the answers are: beside the rail on a wide window, below it on a narrow one, where the memo is what to scroll to
    const stacked = matchMedia("(max-width: 1100px)").matches;
    (stacked ? $("#memo") : $("#step-run")).scrollIntoView({ behavior: scrollBehavior(), block: "start" });
  } catch (e) {
    toast(e.message, true);
    if (stageShown()) renderStage();
  } finally {
    state.running = false;
    btn.classList.remove("busy");
    syncRunButton();
  }
}

/* The top bar names the memo's revision on its site, R1, R2…. */
function showStamp(run) {
  $("#stamp-text").textContent = run ? rev(run.run_id) : "";
  $("#stamp-box").hidden = !run;
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
  $("#pdf-btn").disabled = !on;
  $("#revit-btn").disabled = !(on && run.massing);
  $("#issue-btn").disabled = !on || !!STATIC;
  if (!on) closeIssuePanel();
  renderGuide();
  if (state.view === "3d") renderPreview3D();
}

/* A past run, as a reader picks it: its revision first, then the date, a named folder (as-approved, what-if-…) where
   there is one, the option, and a timestamped folder last. A narrow picker still shows the first three. */
function runLabel(r) {
  const option = r.option_name || r.option_id || "option";
  const named = r.folder && r.folder !== r.as_of && !/^\d{4}-\d\d-\d\d/.test(r.folder);
  const stamped = r.folder && r.folder !== r.as_of && !named;
  // the day it was run leads (a timestamped folder says it; a committed run has none), then the rules date
  const ranOn = r.written ? String(r.written).slice(0, 10) : (stamped ? r.folder.slice(0, 10) : null);
  const ranAt = stamped && /T\d\d-\d\d/.test(r.folder) ? ` ${r.folder.slice(11, 16).replace("-", ":")}` : "";
  return `${rev(r.run_id)} · ${ranOn ? `run ${ranOn}${ranAt} · rules as of ${r.as_of}` : `rules as of ${r.as_of}`} · ${named ? `${r.folder} · ` : ""}${option}${r.revit ? " · Revit" : ""}`;
}

/* The address bar names the run on screen (and the run compared), so a memo can be sent as a link. */
function syncUrl() {
  if (STATIC && !state.run) return;
  const q = new URLSearchParams(location.search);
  if (state.run && !state.run.in_browser) q.set("run", state.run.run_id); else q.delete("run");
  if (state.run && state.compareRun) q.set("compare", state.compareRun); else q.delete("compare");
  q.set("mode", state.mode);
  const url = `${location.pathname}?${q.toString().replace(/%2F/g, "/")}`;   // run ids read as site/folder, as the site's own links write them
  if (url !== location.pathname + location.search) history.replaceState(null, "", url);
}

export function fillRunSelects() {
  const open = $("#open-run"), cmp = $("#compare-run");
  const cur = state.run ? state.run.run_id : "";
  // the open run is chosen in the list; a blank first entry only while no run, or one the list lacks, is on screen
  const listed = state.runs.some(r => r.run_id === cur);
  const runs = byRev(state.runs);   // R1 first, as the labels read (16 Nov 2026: they listed R4, R2, R1, R3)
  open.innerHTML = (listed ? "" : `<option value="">${state.run ? "This run" : "Choose a run…"}</option>`) +
    runs.map(r => `<option value="${h(r.run_id)}"${r.run_id === cur ? " selected" : ""}>${h(runLabel(r))}</option>`).join("");
  cmp.innerHTML = `<option value="">Nothing</option>` +
    runs.filter(r => r.run_id !== cur).map(r => `<option value="${h(r.run_id)}"${r.run_id === state.compareRun ? " selected" : ""}>${h(runLabel(r))}</option>`).join("");
}

export async function openRun(runId) {
  if (!runId) return;
  const [site, folder] = runId.split("/");
  setStatus(`Opening the run ${runId}…`, "busy");
  const run = await api(`/api/runs/${encodeURIComponent(site)}/${encodeURIComponent(folder)}`);
  state.run = run;
  state.runStale = null;
  guide.over = false;
  if (state.mode === "manager") showInputs(false, false);
  // the date in the top bar is the date of the memo on screen, and so of the next run
  $("#as-of").value = run.as_of;
  enableExports(run);
  await syncInputsTo(run);
  // the run's own site names its revisions, whether or not the inputs followed it (unsaved edits keep them where they are)
  const runSite = run.run_id.split("/")[0];
  if (!state.revisions.has(run.run_id)) await loadRuns(runSite);
  if (state.compareRun && !state.compareRun.startsWith(runSite + "/")) state.compareRun = null;   // a comparison never crosses sites
  showStamp(run);   // after the inputs follow the run, so its site's runs, and their revisions, are loaded
  // a run cannot be compared with itself; a run recorded against an earlier one opens compared with it, when the
  // list can tell which run that was
  const selfCompared = state.compareRun === runId;
  if (selfCompared) state.compareRun = null;
  if (!state.compareRun && run.diff) state.compareRun = recordedAgainst(run);
  if (state.compareRun) await applyCompare(false);
  renderMemo(run);
  fillRunSelects();
  setCompareNote(run.diff);
  syncUrl();
  setStep(3);
  closeExportPanel();
  // the folder is the architect's to know; the manager and the reader are told the revision and its date
  const where = state.mode === "architect" ? ` · ${run.in_browser ? "kept in this browser tab" : `outputs/${run.run_id}/`}` : "";
  setStatus(`Opened ${rev(run.run_id)}, the memo as of ${run.as_of}${where}${run.diff ? ` · ${compareSummary(run)}` : ""}${selfCompared ? " · A and B were the same run, so the comparison was cleared" : ""}`, "ok");
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
  const inputs = (run.ledger && run.ledger.inputs) || {};
  if (optId) state.optionId = optId;
  // the run's option as the card's, unsaved, where no saved option is the run's (16 Nov 2026)
  const takeRunOption = () => {
    state.optionId = null;
    state.option = Object.assign(blankOption(state.site && state.site.id), JSON.parse(JSON.stringify(inputs.option)));
    state.optionDirty = false;
    $("#option-select").value = "__new__";
    renderForm($("#option-form"), OPTION_FIELDS, state.option, onOptionChange);
    $("#option-dirty").hidden = false;
    refreshSummary("option");
    syncCards();
  };
  if (state.siteId !== siteId && state.sites.some(s => s.id === siteId)) {
    $("#site-select").value = siteId;
    await selectSite(siteId);
    if (inputs.option && (!optId || !state.options.some(o => o.id === optId))) takeRunOption();
  } else if (!state.sites.some(s => s.id === siteId) && inputs.site && (state.siteId !== null || !state.site || state.site.id !== siteId)) {
    // a run on a site that was never saved (the manager's lookup, issued as it stood): the cards take the run's own
    // inputs, unsaved, so the memo and the cards never show two different sites (15 Nov 2026)
    state.siteId = null;
    state.site = Object.assign(blankSite(), JSON.parse(JSON.stringify(inputs.site)));
    state.siteDirty = false;
    $("#site-select").value = "__new__";
    renderForm($("#site-form"), SITE_FIELDS, state.site, onSiteChange);
    $("#site-dirty").hidden = false;
    refreshSummary("site");
    if (inputs.option) {
      state.optionId = null;
      state.option = Object.assign(blankOption(state.site.id), JSON.parse(JSON.stringify(inputs.option)));
      state.optionDirty = false;
      $("#option-select").value = "__new__";
      renderForm($("#option-form"), OPTION_FIELDS, state.option, onOptionChange);
      $("#option-dirty").hidden = false;
      refreshSummary("option");
    }
    await loadOptions();
    syncCards();
    setStatus(`${state.site.address || siteId} was never saved: its facts and the option are in the cards from the run itself; Save site as… keeps them.`, "info");
  } else if (optId && state.options.some(o => o.id === optId) && $("#option-select").value !== optId) {
    $("#option-select").value = optId;
    await selectOption(optId);
  } else if (inputs.option && (!optId || !state.options.some(o => o.id === optId)) && (!state.option || state.option.id !== inputs.option.id)) {
    // a saved site but an option that was never saved (the manager's suggestion, run as it stood): the card takes the
    // run's own option, so the drawings and the card never describe two different buildings
    takeRunOption();
  }
}

export async function applyCompare(render = true) {
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
  syncUrl();
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
