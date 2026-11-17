/* First Read, the page. Vanilla JS, native ES modules, no build step.
   It formats what the engine wrote (ledger.json, massing.json); it never calculates a rule.
   This is the entry point (index.html loads it as a module): it wires the page and decides what opens first.
   CLAUDE.md, "The page as ES modules", says where each part lives. */

import { $, $$, fmtNum, scrollBehavior, setPath, setStatus, toast, todayISO } from "./core/util.js";
import { guide, PRELOAD_OPTION, PRELOAD_SITE, state, STATIC } from "./core/state.js";
import { api } from "./core/api.js";
import { checkForNewerBuild, loadEngine } from "./core/engine.js";
import { OPTION_FIELDS } from "./fields.js";
import { renderForm, setRailTab, syncCards } from "./schedule.js";
import { loadSites, onOptionChange, saveAs, saveNow, selectOption, selectSite } from "./files.js";
import { applyCompare, fillRunSelects, loadRuns, openRun, rev, runRules } from "./runs.js";
import { renderNoMemo, renderQuiet } from "./memo/memo.js";
import { closeExportPanel, renderExportPanel } from "./revit.js";
import { offerTour, startTour } from "./tour.js";
import { enterOption, renderGuide, renderStage } from "./route-stage.js";
import { renderClaude } from "./claude.js";
import { closeIssuePanel, issueButtonLabel, openIssuePanel, startIssuePolling } from "./issue.js";
import {
  firstOpenStep, initialMode, initTheme, MODES, placeModeThumb, RAIL_KEY, setMode, setStep, setView, showInputs, VIEW_KEY,
  watchSteps
} from "./modes.js";
import { loadPaper } from "./core/lazy.js";

async function init() {
  $("#as-of").value = todayISO();
  // what this machine can offer beyond the rules: a model behind a key on the local server, never on the web
  state.caps = { claude: false, model: null };
  api("/api/capabilities").then(c => { state.caps = c || state.caps; if (state.caps.claude) renderClaude(); }).catch(() => { /* an older server: rules only */ });
  checkForNewerBuild();
  $("#run-btn").addEventListener("click", runRules);
  // the paper memo is fetched the first time it is asked for (core/lazy.js)
  $("#print-btn").addEventListener("click", () => { if (state.run) loadPaper().then(p => p.printPaper(p.paperDocument(state.run))).catch(err => toast(err.message, true)); });
  $("#pdf-btn").addEventListener("click", () => loadPaper().then(p => p.exportPdf()).catch(err => toast(err.message, true)));
  $("#save-site").addEventListener("click", () => saveAs("site"));
  $("#save-option").addEventListener("click", () => saveAs("option"));
  $$("[data-save]").forEach(b => b.addEventListener("click", () => saveNow(b.dataset.save)));
  // "Use it" under the Building group: the derived floor area or height goes into the option
  $("#option-form").addEventListener("click", e => {
    const b = e.target.closest("[data-use]");
    if (!b || !state.option) return;
    setPath(state.option, b.dataset.use, Number(b.dataset.value));
    renderForm($("#option-form"), OPTION_FIELDS, state.option, onOptionChange);
    onOptionChange(b.dataset.use);
    setStatus(`${b.dataset.use === "gfa_m2" ? "Floor area" : "Height"} set to ${b.dataset.use === "gfa_m2" ? fmtNum(Number(b.dataset.value)) + " m²" : b.dataset.value + " m"} from the storeys and the plate.`, "info");
  });
  $$("[data-save-cancel]").forEach(b => b.addEventListener("click", () => { $(`#save-${b.dataset.saveCancel}-inline`).hidden = true; $(`#save-${b.dataset.saveCancel}`).setAttribute("aria-expanded", "false"); $(`#save-${b.dataset.saveCancel}`).focus(); }));
  $$(".save-inline input").forEach(i => i.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); saveNow(i.closest(".save-inline").id.includes("site") ? "site" : "option"); } if (e.key === "Escape") { i.closest(".save-inline").hidden = true; } }));
  // leaving the page with unsaved work: the browser asks first
  window.addEventListener("beforeunload", e => {
    const unsaved = (state.siteDirty && state.site) || (state.optionDirty && state.option) || (state.run && state.run.in_browser);
    if (unsaved) { e.preventDefault(); e.returnValue = ""; }
  });
  // switching files discards unsaved edits, so ask first
  $("#site-select").addEventListener("change", e => {
    if ((state.siteDirty || state.optionDirty) && !confirm("Switch the site file? The unsaved edits to the site and option will be lost.")) { e.target.value = state.siteId || "__new__"; return; }
    selectSite(e.target.value).catch(err => toast(err.message, true));
  });
  $("#option-select").addEventListener("change", e => {
    if (state.optionDirty && !confirm("Switch the option file? The unsaved edits to the option will be lost.")) { e.target.value = state.optionId || "__new__"; return; }
    selectOption(e.target.value).catch(err => toast(err.message, true));
  });
  $$("#rail-tabs .segbtn").forEach(b => b.addEventListener("click", () => setRailTab(b.dataset.tab)));
  $("#rail-toggle").addEventListener("click", () => showInputs($(".panes").classList.contains("no-inputs")));
  try { if (localStorage.getItem(RAIL_KEY) === "1") showInputs(false, false); } catch (e) { /* storage off: the rail starts open */ }
  // who is reading: the switch in the top bar; the mode from the link or the last visit applies before the inputs load
  $$("#mode-switch button").forEach(b => b.addEventListener("click", () => setMode(b.dataset.mode)));
  setMode(initialMode(), false, false);
  initTheme();
  // the thumb is measured: again once the web font is in, and whenever the bar re-wraps (the issue chip arriving
  // wraps it without a window resize, which once left the thumb under the wrong reader)
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(placeModeThumb);
  if ("ResizeObserver" in window) new ResizeObserver(() => placeModeThumb()).observe($(".topbar"));
  let thumbFrame = 0;
  window.addEventListener("resize", () => { if (!thumbFrame) thumbFrame = requestAnimationFrame(() => { thumbFrame = 0; placeModeThumb(); }); });
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
    setStatus(`Export to Revit: the two lines that build sheet FFM-01 for this memo, ${rev(state.run.run_id)}.`, "info");
    panel.scrollIntoView({ behavior: scrollBehavior(), block: "start" });
  });
  // printing opens every ledger layer, and closes the ones it opened afterwards
  // the ledger's layers and the clauses' folded text print open
  window.addEventListener("beforeprint", () => $$(".ledger details:not([open]), .rule-sec-fold:not([open])").forEach(d => { d.open = true; d.dataset.printOpened = "1"; }));
  window.addEventListener("afterprint", () => $$("details[data-print-opened]").forEach(d => { d.open = false; delete d.dataset.printOpened; }));
  $("#tour-link").addEventListener("click", e => { e.preventDefault(); $("#tour-link").classList.remove("unseen"); startTour(0); });
  $$("#view-switch .segbtn").forEach(b => b.addEventListener("click", () => { setView(b.dataset.view); setStatus(b.dataset.view === "3d" ? "3D preview: the site plan with its dimensions, the section and the axonometric." : b.dataset.view === "summary" ? "Summary: the title block, the four answers and the figures." : "Detailed: the whole memo.", "info"); }));
  try { setView(localStorage.getItem(VIEW_KEY) || "detailed", false); } catch (e) { setView("detailed", false); }
  $("#issue-btn").addEventListener("click", () => { if ($("#issue-panel").hidden) openIssuePanel(); else closeIssuePanel(); });
  $("#open-run").addEventListener("change", e => openRun(e.target.value).catch(err => toast(err.message, true)));
  $("#compare-run").addEventListener("change", e => { state.compareRun = e.target.value || null; applyCompare().catch(err => toast(err.message, true)); });
  document.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); runRules(); }
  });

  try {
    state.rules = await api(`/api/rules?as_of=${$("#as-of").value}`);
    await loadSites();
    // the manager starts with nothing loaded and the guide's first stop open; the demo case comes only with a
    // link (?run=, ?tour=, ?demo=1) or the "Load the demo case" button. The architect and the reader arrive on
    // a run (an issued revision, a link) and otherwise see the demo, as before.
    const q = new URLSearchParams(location.search);
    const wantsDemo = q.has("run") || q.has("tour") || q.has("demo") || state.mode !== "manager";
    if (wantsDemo) {
      const first = state.sites.some(s => s.id === PRELOAD_SITE) ? PRELOAD_SITE : (state.sites[0] ? state.sites[0].id : "__new__");
      state.optionId = PRELOAD_OPTION;
      $("#site-select").value = first;
      await selectSite(first);
      if (state.mode === "manager" && state.site && !q.has("run")) {
        guide.programs = state.option && state.option.target_programs ? state.option.target_programs.slice() : null;
        guide.step = q.has("tour") ? 1 : 2;
        renderGuide();
        if (guide.step === 2) enterOption();
      }
    } else {
      state.site = null; state.siteId = null; state.option = null; state.optionId = null;
      $("#site-select").value = "__new__";
      await loadRuns();
      fillRunSelects();
      renderStage();
    }
    syncCards();
    if (state.mode === "reader" && !q.has("run")) renderNoMemo();
    setStatus(state.mode === "reader"
      ? "The memo reads here as on paper. Open one from a link, or switch to Manager to make one."
      : state.mode === "manager"
        ? (wantsDemo && state.site ? `The demo case is loaded: ${state.site.address}, the option as approved by Council. Continue to the run, or start from another candidate.` : "Start with the site: look up an address, or choose a saved site.")
        : `Laid out for ${MODES[state.mode].who}. The Site and Option schedules are on the left; set the date the rules are read on, then run the rules.`, "info");
  } catch (e) {
    toast(`Could not load the inputs: ${e.message}`, true);
  }
  setStep(firstOpenStep());
  watchSteps();
  offerTour();
  renderGuide();
  issueButtonLabel();
  startIssuePolling();
  if (STATIC) loadEngine().catch(() => { /* the chip says why; past runs still open */ });
  await followLink();
}

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
      // the reader's pane stops saying "Opening the memo…" and offers what it can
      state.runLinkFailed = true;
      if (state.mode === "reader") renderNoMemo();
    }
  }
  if (q.get("tour")) startTour(0);
}

/* Nothing fails silently: an error the page did not expect is written to the status strip, with what to do. */
window.addEventListener("error", e => {
  const s = $("#status");
  if (s && e.message) setStatus(`Something went wrong: ${e.message}${e.lineno ? ` (${String(e.filename || "").split("/").pop().split("?")[0] || "the page"} line ${e.lineno})` : ""}. Reload the page; saved sites, options and runs are files and are kept.`, "error");
});

window.addEventListener("unhandledrejection", e => {
  const s = $("#status"), msg = e.reason && e.reason.message ? e.reason.message : String(e.reason || "");
  if (s && msg) setStatus(`Something went wrong: ${msg}. Reload the page; saved sites, options and runs are files and are kept.`, "error");
});

// the page's first layout is placed, not animated: until init has opened what the link asks for, the mode thumb and
// the route column take their places without sliding in (17 Nov 2026: both moved on every load)
const settle = () => setTimeout(() => document.documentElement.classList.add("settled"), 300);
// a module runs before DOMContentLoaded; the check keeps init from being missed if this file ever runs after it
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => init().finally(settle));
else init().finally(settle);
