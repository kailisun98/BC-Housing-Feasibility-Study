/* How the page is laid out for who is reading (manager, architect, reader, operator), the left column folding, and the
   step a reader is working in. The memo's tabs are memo/tabs.js. */

import { $, $$, setStatus } from "./core/util.js";
import { editor, guide, state } from "./core/state.js";
import { syncCards } from "./schedule.js";
import { renderClaude } from "./claude.js";
import { renderMemo, renderQuiet } from "./memo/memo.js";
import { closeExportPanel } from "./revit.js";
import { renderGuide } from "./route-stage.js";
import { closeIssuePanel, issueButtonLabel, pollIssues } from "./issue.js";
import { loaded } from "./core/lazy.js";
import { architectMoneyOpen } from "./memo/answers.js";

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
export function firstOpenStep() {
  const done = stepsDone();
  return [1, 2, 3, 4].find(k => !done[k]) || 4;
}

export function setStep(n) {
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

export function watchSteps() {
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

/* The left column folds to a strip with its own arrow and opens again on another click. The reader's own choice is
   kept for their next visit, where the browser allows it; the manager's folds by itself once a memo is on screen. */
export const RAIL_KEY = "ffm.inputs.collapsed";

export function showInputs(show, remember = true) {
  $(".panes").classList.toggle("no-inputs", !show);
  const btn = $("#rail-toggle");
  btn.setAttribute("aria-expanded", String(show));
  const word = state.mode === "manager" ? "the stops" : "the inputs";
  btn.title = show ? `Fold ${word}` : `Show ${word}`;
  if (remember) { try { localStorage.setItem(RAIL_KEY, show ? "0" : "1"); } catch (e) { /* storage off: the choice lasts this visit */ } }
}

/* Who is reading. The three flows in docs/user-flows.md each lay the same page out differently; the switch in the
   top bar picks one, ?mode= in a link from the site picks it for a visitor, and the choice is kept for the next visit.
     manager   the route of three stops on the left, one card at a time on the stage, then the memo with Download PDF
     architect the Site and Option schedules on the left; every ledger layer open; Build it in Revit leads
     reader    no inputs, no run controls: the memo alone in a reading column, Download PDF and Print
   The engine and the memo are the same in every mode; only what is shown first changes (app.css does the rest). */
const MODE_KEY = "ffm.mode";

export const MODES = {
  manager: { who: "the development manager", line: "three stops, the site, the option and the run, then the memo with Download PDF for the board." },
  architect: { who: "the architect", line: "the Site and Option schedules beside the memo, every ledger layer open but the money's (Show the pro-forma on answer 4 opens it), two runs compared, the block editor on FIG 03, and the massing to Revit." },
  reader: { who: "a reader", line: "the memo alone, as on paper, with Download PDF and Print. Switch to Manager or Architect to change anything." },
  operator: { who: "the operator", line: "the operating figures to enter and sign, what an operator checks on the plans, then the memo; Run again carries the figures in." },
};

/* The switch's paper thumb slides under the pressed reader; it is measured, so it follows the fonts and the window. */
export function placeModeThumb() {
  const sw = $("#mode-switch"), thumb = $(".seg-thumb", sw), on = $('button[aria-pressed="true"]', sw);
  if (!thumb || !on) return;
  thumb.style.width = `${on.offsetWidth}px`;
  thumb.style.transform = `translateX(${on.offsetLeft}px)`;
  sw.classList.add("placed");
}

export function setMode(mode, remember = true, announce = true) {
  if (!MODES[mode]) mode = "manager";
  state.mode = mode;
  document.documentElement.dataset.mode = mode;
  $$("#mode-switch button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.mode === mode)));
  placeModeThumb();
  document.title = `First Read · for ${MODES[mode].who}`;
  guide.over = false;
  const railWord = mode === "manager" ? "Stops" : "Inputs";
  $(".rail-label").textContent = railWord;
  if (mode === "reader" || mode === "operator") {
    showInputs(false, false);
    closeExportPanel();
  } else {
    // the manager's route folds once a memo is on screen; the architect works from the schedules beside it
    showInputs(!(mode === "manager" && state.run), false);
  }
  if (editor.open && mode !== "architect") loaded.blocks.closeEditor();   // the editor is the architect's; leaving the mode closes it
  // the memo is laid out for its reader (the note addressed to them, the architect's mass tools), so it is drawn again
  if (state.run && state.run.ledger) renderMemo(state.run); else applyModeToMemo();
  syncCards();
  renderClaude();      // the schedule form sits on the manager's site card for a CD-1 lot, under the architect's district row otherwise
  renderGuide();
  if (!state.run) renderQuiet();   // the manager's stage, the reader's empty page, or the quiet cards for the architect
  issueButtonLabel();
  closeIssuePanel();
  // the architect's Revit button leads the actions in the DOM, so the tab order is the order on screen; the others have
  // it after Print (24 Nov 2026: a CSS order moved it on screen only)
  const bar = $("#export-actions"), revitBtn = $("#revit-btn");
  if (bar && revitBtn) { if (mode === "architect") bar.prepend(revitBtn); else { const pr = $("#print-btn", bar); if (pr) pr.after(revitBtn); } }
  if (remember) { try { localStorage.setItem(MODE_KEY, mode); } catch (e) { /* storage off: the choice lasts this visit */ } }
  // a link that names the layout names the one on screen, so Back and a reload come back to it (20 Nov 2026: Back
  // restores each entry's layout, and an entry still saying ?mode=manager would have undone the switch)
  try {
    const q = new URLSearchParams(location.search);
    if (q.has("mode") && q.get("mode") !== mode) { q.set("mode", mode); history.replaceState(history.state, "", `${location.pathname}?${q.toString().replace(/%2F/g, "/")}`); }
  } catch (e) { /* a page without history (a file): the link keeps its own */ }
  if (announce) { setStatus(`Laid out for ${MODES[mode].who}: ${MODES[mode].line}`, "info"); pollIssues(); }
}

/* What a mode does to the memo on screen: the architect reads every ledger layer open, the others start closed.
   Layer F, the pro-forma's assumptions, opens for the architect only with the money (17 Nov 2026). */
export function applyModeToMemo() {
  const arch = state.mode === "architect";
  $$(".ledger details.layer").forEach(d => {
    const open = arch && (d.dataset.layer !== "F" || architectMoneyOpen());
    if (d.open !== open) d.open = open;
  });
}

/* Day or night (17 Nov 2026, Kai: "add toggle for light/dark mode"). With no choice made the page follows the OS,
   and the button follows the OS with it; a press sets data-theme on <html> and keeps the choice for the next visit
   (index.html's head applies a kept choice before the first paint, so the page never flashes the other theme). */
export const THEME_KEY = "ffm.theme";
const darkOS = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
const isDark = () => { const t = document.documentElement.dataset.theme; return t ? t === "dark" : !!(darkOS && darkOS.matches); };

function syncThemeButton() {
  const b = $("#theme-btn");
  if (!b) return;
  const dark = isDark();
  b.setAttribute("aria-pressed", String(dark));
  b.title = dark ? "Switch to the light page" : "Switch to the dark page";
}

export function setTheme(theme, remember = true) {
  document.documentElement.dataset.theme = theme;
  syncThemeButton();
  if (remember) { try { localStorage.setItem(THEME_KEY, theme); } catch (e) { /* the choice lasts this visit */ } }
}

export function initTheme() {
  const b = $("#theme-btn");
  if (b) b.addEventListener("click", () => { setTheme(isDark() ? "light" : "dark"); setStatus(`The ${isDark() ? "dark" : "light"} page; the drawings stay on white paper.`, "info"); });
  if (darkOS && darkOS.addEventListener) darkOS.addEventListener("change", syncThemeButton);
  syncThemeButton();
}

export function initialMode() {
  const q = new URLSearchParams(location.search).get("mode");
  if (q && MODES[q]) return q;
  try { const m = localStorage.getItem(MODE_KEY); if (m && MODES[m]) return m; } catch (e) { /* fine */ }
  return "manager";
}
