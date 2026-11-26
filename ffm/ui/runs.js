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
import { dateWords, renderMemo } from "./memo/memo.js";
import { attachCause, compareSummary, setCompareNote } from "./memo/changes.js";
import { renderPreview3D } from "./figures/cards.js";
import { closeExportPanel } from "./revit.js";
import { backToMemo, progress, renderGuide, renderRoute, renderStage, stageShown } from "./route-stage.js";
import { closeIssuePanel } from "./issue.js";
import { setMode, setStep, showInputs } from "./modes.js";

/* The top bar's Run. The architect's is the one loud button. The manager runs from the card at 03, so theirs waits
   until there is a memo, then reads Run again, quiet, live only once an edit has left the memo out of date. */
export function syncRunButton() {
  const b = $("#run-btn");
  if (!b) return;
  const p = progress();
  const asOf = $("#as-of").value || todayISO();
  if (state.mode === "manager" || state.mode === "operator") {
    b.hidden = !state.run;
    b.classList.add("btn-again");
    // a date moved off the memo's own is said on the button, where the run will use it (24 Nov 2026)
    const moved = state.run && asOf !== state.run.as_of;
    b.textContent = state.running ? "Running…" : moved ? `Run again as of ${dateWords(asOf)}` : "Run again";
    const ok = !!(state.runStale && p.site && p.option);
    b.setAttribute("aria-disabled", String(!ok));
    b.title = ok ? `Run the rules again as of ${dateWords(asOf)}: ${state.runStale} changed (Ctrl+Enter)` : "Nothing has changed since this run";
    return;
  }
  b.hidden = false;
  b.classList.remove("btn-again");
  b.textContent = state.running ? "Running…" : "Run the rules";
  const ok = !!(p.site && state.option);
  b.setAttribute("aria-disabled", String(!ok));
  b.title = ok ? `Run the rules as of ${dateWords(asOf)} (Ctrl+Enter)` : (!p.site ? "Choose a site first" : "Choose an option first");
}

/* Why a run asked for now would not run, or null. The reader never runs; the manager's memo runs again only once
   something has left it out of date (24 Nov 2026: Ctrl+Enter, or Enter on the aria-disabled Run again, made a second
   revision of the same inputs). The architect may run the same inputs again on purpose. */
function runRefused() {
  if (state.mode === "reader") return "The reader's view reads memos; it does not run the rules.";
  if ((state.mode === "manager" || state.mode === "operator") && state.run && !state.runStale)
    return `Nothing has changed since ${rev(state.run.run_id)}: change a figure, an answer or the rules date to run again.`;
  return null;
}

export async function loadRuns(siteId = null) {
  const sid = siteId || state.siteId || (state.site && state.site.id);
  state.runs = sid ? await api(`/api/runs?site=${encodeURIComponent(sid)}`) : [];
  noteRevisions(state.runs);
  // the route names the memo by its revision: drawn before the revisions were known, it said "a new revision" for R1
  // (17 Nov 2026)
  renderRoute();
}

/* A memo's revision on its site, R1, R2 and so on, the way a drawing numbers its issues: only a memo that has gone
   to someone takes a number (Kai, 24 Nov 2026: every trial run took one, so R7 could be a run nobody saw). The
   committed runs come first: the base runs, then the runs recorded against another (they carry a diff), each group by
   its as-of date and folder. Then the runs made here that have been issued, in the order they were first issued, so
   an issue always takes the next number and never renumbers one before it. A run made here and not issued is a draft,
   named by the time it was made ("Draft 14:03"); on the web build every run made in the page stays one, as issuing
   needs the local server. On 998 E 19th Ave the as-approved memo is R1 and the funder-ready what-if R2. The rules
   stamp behind a memo appears only as the fingerprint in its Rules fingerprint card. */
const madeHere = r => /^(\d{4}-\d\d-\d\dT|browser-)/.test(r.folder || "");

/* When a run made here was made, from its folder (local time, as the server and the page name them). */
function madeAt(r) {
  const f = String(r.folder || "");
  let m = /^(\d{4}-\d\d-\d\d)T(\d\d)-(\d\d)-(\d\d)/.exec(f);
  if (m) return { day: m[1], hm: `${m[2]}:${m[3]}`, hms: `${m[2]}:${m[3]}:${m[4]}` };
  m = /^browser-(\d\d)-(\d\d)-(\d\d)/.exec(f);
  if (m) return { day: todayISO(), hm: `${m[1]}:${m[2]}`, hms: `${m[1]}:${m[2]}:${m[3]}` };
  return null;
}

function draftName(r, taken) {
  const t = madeAt(r);
  if (!t) return "Draft";
  const day = t.day === todayISO() ? "" : `${dateWords(t.day).replace(/ \d{4}$/, "")}, `;
  const name = `Draft ${day}${t.hm}`;
  return taken.has(name) ? `Draft ${day}${t.hms}` : name;   // two runs in one minute
}

function noteRevisions(runs) {
  const list = (runs || []).filter(r => r && r.run_id);
  const committed = list.filter(r => !madeHere(r)).sort((a, b) => (a.has_diff ? 1 : 0) - (b.has_diff ? 1 : 0)
    || String(a.as_of).localeCompare(String(b.as_of)) || String(a.folder).localeCompare(String(b.folder)));
  const issued = list.filter(r => madeHere(r) && r.issued_at).sort((a, b) => String(a.issued_at).localeCompare(String(b.issued_at))
    || String(a.folder).localeCompare(String(b.folder)));
  const drafts = list.filter(r => madeHere(r) && !r.issued_at).sort((a, b) => String(a.folder).localeCompare(String(b.folder)));
  const named = [...committed, ...issued].map((r, i) => [r.run_id, `R${i + 1}`]);
  const taken = new Set();
  const draftNames = drafts.map(r => { const n = draftName(r, taken); taken.add(n); return [r.run_id, n]; });
  state.revisions = new Map([...named, ...draftNames]);
  state.revisionCount = named.length;
}

/* A run as the reader names it: its revision on the site, or its draft name. */
export const rev = runId => (runId && state.revisions.get(runId)) || "this run";

/* A run made here and not yet issued. */
export const isDraft = runId => /^Draft\b/.test(rev(runId));

/* The number the next issue on this site takes. */
export const nextRev = () => `R${(state.revisionCount || 0) + 1}`;

/* Runs in revision order, R1 first, then the drafts in the order they were made. */
const revNo = id => { const m = /^R(\d+)$/.exec(rev(id)); return m ? Number(m[1]) : 1e9; };
export const byRev = runs => runs.slice().sort((a, b) => revNo(a.run_id) - revNo(b.run_id) || String(a.folder).localeCompare(String(b.folder)));

export async function runRules() {
  const btn = $("#run-btn");
  if (state.running) return;   // a second click while a run is in flight made a second revision of the same inputs
  const refused = runRefused();
  if (refused) { if (state.mode !== "reader") setStatus(refused, "info"); return; }
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
    if (state.mode === "manager" || state.mode === "operator") showInputs(false, false);
    renderRoute();
    const ms = Math.round(performance.now() - t0);
    toast(`Ran the rules as of ${dateWords(run.as_of)}: ${rev(run.run_id)}, in ${ms} ms${run.diff ? ` · ${compareSummary(run)}` : ""}. Download PDF is under the title.`);
    // the keyboard goes to the memo's heading, where the answers start (20 Nov 2026: it stayed on a Run button the
    // memo had just replaced, so it fell to the page's top)
    const head = $("#memo .memo-head h1");
    if (head) { head.tabIndex = -1; head.focus({ preventScroll: true }); }
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
  $("#pdf-short-btn").disabled = !on;
  $("#revit-btn").disabled = !(on && run.massing);
  $("#issue-btn").disabled = !on || !!STATIC;
  if (!on) closeIssuePanel();
  renderGuide();
  if (state.view === "3d") renderPreview3D();
}

/* A past run, as a reader picks it: its revision (or its draft name, which carries when it was made), the option, and
   the rules date in words. A narrow picker still shows the first two. No folder name: that is the architect's to know,
   and the status line names it when a run opens in architect mode (24 Nov 2026: pickers read "run 2026-11-24 ·
   as-approved-rules-2026-10-27 · …", and a committed run's "run" date was only when the file was checked out). */
function runLabel(r) {
  return `${runName(r)} · rules as of ${dateWords(r.as_of)}${r.revit ? " · Revit" : ""}`;
}

/* A memo named for a link: its revision and its option's name up to the colon ("R1 · As approved by Council, 25 Jul
   2024"). */
export const runName = r => `${rev(r.run_id)} · ${String(r.option_name || r.option_id || "option").split(":")[0].trim()}`;

/* After an issue: the run takes its number, and every place that names it says so. */
export async function afterIssue(run) {
  await loadRuns(run.run_id.split("/")[0]);
  showStamp(run);
  renderMemo(run);
  fillRunSelects();
  setCompareNote(run.diff);
}

/* The address bar names the run on screen (and the run compared), so a memo can be sent as a link. Another run or
   another comparison is a new entry in the browser's history, so Back returns to the memo before it (20 Nov 2026:
   every change replaced the entry, and Back left the tool); anything smaller, and a step Back itself takes, replaces. */
let restoring = false;

function syncUrl() {
  if (STATIC && !state.run) return;
  const q = new URLSearchParams(location.search);
  const was = new URLSearchParams(location.search);
  if (state.run && !state.run.in_browser) q.set("run", state.run.run_id); else q.delete("run");
  if (state.run && state.compareRun) q.set("compare", state.compareRun); else q.delete("compare");
  q.set("mode", state.mode);
  q.delete("tour");   // the walkthrough is a one-time link: an entry made while it runs does not start it again
  const url = `${location.pathname}?${q.toString().replace(/%2F/g, "/")}`;   // run ids read as site/folder, as the site's own links write them
  if (url === location.pathname + location.search) return;
  const moved = (was.get("run") || "") !== (q.get("run") || "") || (was.get("compare") || "") !== (q.get("compare") || "");
  if (moved && !restoring) history.pushState({ ffm: 1 }, "", url);
  else history.replaceState(history.state, "", url);
}

/* Back and Forward: the page opens what the address bar now names, the run and the comparison (and the layout the
   entry was made in), without making a new entry. An entry with no run brings the manager's stops back over the memo. */
export async function followHistory() {
  const q = new URLSearchParams(location.search);
  const run = q.get("run"), cmp = q.get("compare") || null, mode = q.get("mode");
  restoring = true;
  try {
    if (mode && mode !== state.mode && ["manager", "architect", "reader"].includes(mode)) setMode(mode, false, false);
    if (run && (!state.run || state.run.run_id !== run)) {
      state.compareRun = cmp && cmp !== run ? cmp : null;
      await openRun(run);
    } else if (run && (state.compareRun || null) !== cmp) {
      state.compareRun = cmp;
      fillRunSelects();
      await applyCompare();
    } else if (run && guide.over) {
      backToMemo();
    } else if (!run && state.run && state.mode === "manager") {
      // the page before the first run: the stop the manager was on comes back over the memo, which stays a click away
      guide.over = true;
      showInputs(true, false);
      renderGuide();
    }
  } catch (e) {
    toast(`Could not open ${run || "that page"}: ${e.message}`, true);
  } finally {
    restoring = false;
  }
}

export function fillRunSelects() {
  const open = $("#open-run"), cmp = $("#compare-run");
  const cur = state.run ? state.run.run_id : "";
  // the open run is chosen in the list; a blank first entry only while no run, or one the list lacks, is on screen
  const listed = state.runs.some(r => r.run_id === cur);
  const runs = byRev(state.runs);   // R1 first, as the labels read (16 Nov 2026: they listed R4, R2, R1, R3)
  open.innerHTML = (listed ? "" : `<option value="">${state.run ? "This memo" : "Choose a memo…"}</option>`) +
    runs.map(r => `<option value="${h(r.run_id)}"${r.run_id === cur ? " selected" : ""}>${h(runLabel(r))}</option>`).join("");
  cmp.innerHTML = `<option value="">No comparison</option>` +
    runs.filter(r => r.run_id !== cur).map(r => `<option value="${h(r.run_id)}"${r.run_id === state.compareRun ? " selected" : ""}>${h(runLabel(r))}</option>`).join("");
}

export async function openRun(runId) {
  if (!runId) return;
  const [site, folder] = runId.split("/");
  setStatus(`Opening ${state.revisions.has(runId) ? rev(runId) : "the memo"}…`, "busy");   // a revision, never the folder
  const run = await api(`/api/runs/${encodeURIComponent(site)}/${encodeURIComponent(folder)}`);
  state.run = run;
  state.runStale = null;
  guide.over = false;
  if (state.mode === "manager" || state.mode === "operator") showInputs(false, false);
  // the date in the top bar is the date of the memo on screen, and so of the next run; a date that moves is said in
  // the status line below (24 Nov 2026: it changed under the reader without a word)
  const wasAsOf = $("#as-of").value;
  $("#as-of").value = run.as_of;
  const dateMoved = wasAsOf && wasAsOf !== run.as_of;
  enableExports(run);
  await syncInputsTo(run);
  // the manager's route stands on the run's option, as it was run: 02 shows it, it is not derived again (25 Nov 2026:
  // reopening R1 offered a fresh suggestion of 80 homes where R1 had 74)
  if (state.option && !state.optionDirty) {
    guide.suggestion = null; guide.suggestionUsed = true; guide.appliedOption = state.option; guide.suggestStale = false;
    guide.mine = {}; guide.answers = {}; guide.optionSeen = true; guide.readStale = true;
    guide.programs = (state.option.target_programs || []).slice();
  }
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
  setStatus(`Opened ${rev(run.run_id)}, the memo as of ${dateWords(run.as_of)}${where}${run.diff ? ` · ${compareSummary(run)}` : ""}${selfCompared ? " · A and B were the same run, so the comparison was cleared" : ""}${dateMoved && state.mode !== "reader" ? ` · Rules as of now reads ${dateWords(run.as_of)}, this memo's date (it read ${dateWords(wasAsOf)})` : ""}`, "ok");
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
    // the site's saved options first (none, for a lookup), then the run's own option over the blank that leaves
    // (17 Nov 2026: loadOptions ran last and put a blank "New option…" beside the run's 19-storey memo)
    await loadOptions();
    if (inputs.option) {
      state.optionId = null;
      state.option = Object.assign(blankOption(state.site.id), JSON.parse(JSON.stringify(inputs.option)));
      state.optionDirty = false;
      $("#option-select").value = "__new__";
      renderForm($("#option-form"), OPTION_FIELDS, state.option, onOptionChange);
      $("#option-dirty").hidden = false;
      refreshSummary("option");
    }
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
  // whatever the files say, the inputs are the run's own (25 Nov 2026, three reviewers: a saved option file came back
  // in place of what the run read, so the operator's signed figures, the capital sources and the brief were lost, and
  // the next Run again ran a different project). A saved file the run departs from stays saved; the cards carry the
  // run's inputs, unsaved, and say so.
  if (inputs.option && state.option && differs(inputs.option, state.option)) takeRunOption();
  if (inputs.site && state.site && differs(inputs.site, state.site)) {
    state.site = Object.assign(blankSite(), JSON.parse(JSON.stringify(inputs.site)));
    state.siteDirty = false;
    renderForm($("#site-form"), SITE_FIELDS, state.site, onSiteChange);
    $("#site-dirty").hidden = false;
    refreshSummary("site");
  }
}

/* Two inputs that say different things: a key either sets to a value the other does not (blanks are alike). Pure. */
const blankish = v => v == null || v === "" || (Array.isArray(v) && !v.length) || (typeof v === "object" && !Array.isArray(v) && !Object.keys(v).length);
const stable = v => JSON.stringify(v, (k, x) => (x && typeof x === "object" && !Array.isArray(x) ? Object.fromEntries(Object.keys(x).sort().map(n => [n, x[n]])) : x));
export function differs(a, b) {
  for (const k of new Set([...Object.keys(a || {}), ...Object.keys(b || {})])) {
    const x = (a || {})[k], y = (b || {})[k];
    if (blankish(x) && blankish(y)) continue;
    if (stable(x) !== stable(y)) return true;
  }
  return false;
}

const diffCache = new Map();

export async function applyCompare(render = true) {
  const run = state.run;
  const note = $("#compare-note");
  if (!run) {
    note.textContent = state.compareRun ? "Applies to the next run." : "";
    if (render) setStatus(state.compareRun ? `The next run will be compared with ${rev(state.compareRun)}.` : "No comparison.", "info");
    return;
  }
  // the same run on both sides is no comparison: clear it, so the picker and the memo agree, and say why
  const selfCompared = state.compareRun === run.run_id;
  if (selfCompared) state.compareRun = null;
  if (!state.compareRun) {
    run.diff = null;
    run.compareLedger = null;
  } else {
    if (render) setStatus("Comparing the two memos…", "busy");
    // a run's files never change once written, so a pair compared once is not asked for again (24 Nov 2026: one
    // page load asked /api/diff for the same pair more than once)
    const key = `${state.compareRun}>${run.run_id}`;
    if (!diffCache.has(key)) diffCache.set(key, api(`/api/diff?from=${encodeURIComponent(state.compareRun)}&to=${encodeURIComponent(run.run_id)}`).catch(e => { diffCache.delete(key); throw e; }));
    run.diff = structuredClone(await diffCache.get(key));   // attachCause writes into it
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
