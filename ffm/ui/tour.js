/* The walkthrough: nine stops over the page, each with an optional `before` that sets the page up for it. */

import { $, $$, h, reducedMotion, toast } from "./core/util.js";
import { guide, state } from "./core/state.js";
import { loadDemo } from "./files.js";
import { openRun } from "./runs.js";
import { backToMemo, enterOption, progress, renderGuide } from "./route-stage.js";
import { useSuggestion } from "./guide.js";
import { setMode, setView, showInputs } from "./modes.js";

/* The walkthrough follows the development manager's flow (docs/user-flows.md, flow 1) from the top bar to an issued
   run, then shows the other two readers. A step's `before` sets the page up for it (a mode, a guide stop, a view) and
   `action: "run"` runs the rules when the reader presses Next; the mode the reader started in comes back at the end. */
const TOUR = [
  { target: ".mode", title: "For the manager, the architect, or a reader", before: () => setMode("manager", false, false),
    text: "One page, three layouts. Manager: three stops, then the memo. Architect: the site and the option as schedules beside the memo, every ledger layer open, Revit at hand. Reader: the memo alone, as on paper. This walkthrough follows the manager; the last stop shows the other two." },
  { target: "#guide", title: "Three stops", before: () => { guide.over = false; if (!state.run) { guide.step = 1; renderGuide(); } },
    text: "The left column is the route: the site, the option, the run. Each row shows its decision once made, and a click brings its card back. Nothing else lives here." },
  { target: "#stage-card", fallback: "#memo", title: "01 The site", before: () => { if (state.run) { guide.step = 1; guide.over = true; } else guide.step = 1; renderGuide(); },
    text: "Type an address: the City's address list gives the point, its open data the zoning district and the parcel, drawn on the map to be checked. Then the card asks only what the open data could not tell, each question with who answers it; 'not sure' is a normal answer and comes back as an open item." },
  { target: "#stage-card", fallback: "#memo", title: "02 The option", before: async () => { if (!progress().site) await loadDemo(); guide.step = 2; guide.over = !!state.run; renderGuide(); enterOption(); },
    text: "The programs in view, what the site allows before any option, and where to start: Funder-ready, Outright, Benchmark or a saved option, derived from the rules. The building is four figures; click one to make it yours. Every other figure, with the rule it rests on, is behind one fold." },
  { target: "#stage-card", fallback: "#memo", title: "03 Money in, then run", action: "run",
    before: async () => { if (!progress().site) await loadDemo(); if (!progress().option && guide.suggestion) useSuggestion(); if (progress().option) { guide.step = 3; guide.over = !!state.run; renderGuide(); } },
    text: "Land, equity and other grants are the three figures only the manager knows; everything else the money counts with is a dated, cited assumption. Then one button runs the rules. A run made here is a draft until it is marked issued. Here the walkthrough opens the demo case's own memo instead, R1, as Council approved it, so it makes no draft." },
  { target: ".answers", fallback: "#memo", title: "The four answers", before: () => { if (guide.over) backToMemo(); },
    text: "Is it allowed? Does it fit the funders? What is still unsure, and who resolves it? Does the money work? Every finding prints the numbers it used and links the clause it came from; the third answer names a person for each open item. Once a memo is in, the route folds to the left edge so the memo has the width." },
  { target: "#memo-actions", fallback: "#step-export", title: "Download PDF, and mark it issued",
    text: "Download PDF is the memo for the board, laid out for paper. Mark issued to the architect gives a draft the site's next revision number and records your name and a note; the architect's layout on this machine shows it, and they mark it issued back when the plans are drawn. To reach someone elsewhere, send the link or the PDF." },
  { target: "#view-switch", title: "Summary, Detailed, 3D preview",
    text: "How much of the memo to show: the title block and the answers; the whole memo with the clauses and the ledger; or the drawings, large, with an axonometric you can turn." },
  { target: ".mode", title: "The architect and the reader",
    text: "Switch to Architect and the left column holds the Site and Option schedules, one row per input, each citing the rules that read it; every ledger layer opens, Edit blocks appears on the plans, and Export to Revit leads. Switch to Reader and the memo stands alone in a reading column. That is the whole page." },
];

/* The reader's walkthrough: the memo as it is on their screen, without switching them to the manager's layout
   (24 Nov 2026: the walkthrough moved a reader into the manager's route and described stops they never use). */
const READER_TOUR = [
  { target: ".memo-head", fallback: "#memo", title: "The title block",
    text: "The site, the option, the date the rules were read as of, and the memo's revision: R1, R2 and so on, numbered as they were issued. A comparison with another memo is named here too, with its result and a link to it." },
  { target: ".answers", fallback: "#memo", title: "The four answers",
    text: "Is it allowed? Does it fit the funders? What is still unsure, and who resolves it? Does the money work? Every finding prints the numbers it used and links the clause it came from; the third answer names a person for each open item." },
  { target: "#memo-index", fallback: "#memo", title: "In this memo",
    text: "The memo's parts, as a drawing set lists its sheets: the answers, the drawings, the clauses, the full ledger, the inputs, the sources and the fingerprint that lets anyone reproduce it." },
  { target: "#memo-actions", fallback: "#memo", title: "Download PDF and Print",
    text: "The PDF is the memo laid out for paper, with the clauses, the ledger and the sources numbered; Print gives the same pages." },
  { target: "#view-switch", title: "Summary, Detailed, 3D preview",
    text: "How much of the memo to show: the title block and the answers; the whole memo; or the drawings, large, with an axonometric you can turn." },
];

const TOUR_KEY = "ffm.walkthrough.seen";

const tour = { active: false, i: 0, list: TOUR, spot: null, card: null, raf: 0, timer: 0, returnTo: null, modeBefore: null, viewBefore: null };

function tourTarget(step) {
  return document.querySelector(step.target) || (step.fallback ? document.querySelector(step.fallback) : null);
}

export function startTour(at = 0) {
  if (tour.active) endTour();
  tour.active = true;
  tour.modeBefore = state.mode;
  tour.viewBefore = state.view;
  // a reader with a memo open is walked through the memo they have; anyone else through the manager's flow
  tour.list = state.mode === "reader" && state.run ? READER_TOUR : TOUR;
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
  // the page goes back to the layout and the view the reader had before the walkthrough set them up
  if (tour.viewBefore && tour.viewBefore !== state.view) setView(tour.viewBefore, false);
  if (tour.modeBefore && tour.modeBefore !== state.mode) setMode(tour.modeBefore, false, false);
  tour.modeBefore = tour.viewBefore = null;
  try { localStorage.setItem(TOUR_KEY, "1"); } catch (e) { /* private window: fine */ }
  // the link that started it no longer names it, so a reload does not start it again (20 Nov 2026)
  try {
    const q = new URLSearchParams(location.search);
    if (q.has("tour")) { q.delete("tour"); const s = q.toString().replace(/%2F/g, "/"); history.replaceState(history.state, "", `${location.pathname}${s ? `?${s}` : ""}`); }
  } catch (e) { /* no history to change */ }
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

/* The run the walkthrough shows: the demo case's committed memo, opened, never made (20 Nov 2026: every walkthrough ran
   the rules, so each wrote an outputs folder and a new revision, R4, R5…). */
const TOUR_RUN = "998-e-19th-ave/as-approved";

async function tourNext() {
  const step = tour.list[tour.i];
  if (step.action === "run" && !state.run) {
    const btn = $(".tour-next", tour.card);
    if (btn) { btn.disabled = true; btn.textContent = "Opening the memo…"; }
    try { await openRun(TOUR_RUN); } catch (e) { toast(`Could not open the demo's memo: ${e.message}`, true); }
    if (!tour.active) return;
    if (!state.run) { showTourStep(tour.i); return; }   // it could not open; the status line says why
  }
  showTourStep(tour.i + 1);
}

async function showTourStep(i) {
  if (!tour.active) return;
  if (i < 0) i = 0;
  if (i >= tour.list.length) { const reader = tour.list === READER_TOUR; endTour(); toast(reader ? "That is the memo. Download PDF keeps a copy." : "That is the whole page. Start from an address whenever you like."); return; }
  tour.i = i;
  const step = tour.list[i];
  // a stop may set the page up for itself, a demo loaded or a card brought forward, and may wait for it
  if (step.before) { try { await step.before(); } catch (e) { toast(e.message, true); } }
  if (!tour.active || tour.i !== i) return;
  // a step that points into the inputs opens a folded rail, without changing the reader's kept choice
  const aim = tourTarget(step);
  if (aim && aim.closest(".inputs-body") && $(".panes").classList.contains("no-inputs")) showInputs(true, false);
  const last = i === tour.list.length - 1;
  const primary = step.action === "run" && !state.run ? "Open the memo and continue" : (last ? "Done" : "Next");
  tour.card.innerHTML = `
    <button class="tour-close" type="button" aria-label="Close the walkthrough">×</button>
    <h3 id="tour-title">${h(step.title)}</h3>
    <p id="tour-text">${h(step.text)}</p>
    <div class="tour-nav">
      <button class="btn btn-quiet btn-small tour-back" type="button"${i === 0 ? " disabled" : ""}>Back</button>
      <span class="spacer"></span>
      <span class="counter">${i + 1} of ${tour.list.length} · Esc closes</span>
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
  const step = tour.list[tour.i];
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

/* The walkthrough is offered by its link at the end of the status line, not by a banner (16 Nov 2026: the banner
   was a fourth bar over a guide that already guides); a first visit marks the link until the walkthrough is seen. */
export function offerTour() {
  let seen = false;
  try { seen = !!localStorage.getItem(TOUR_KEY); } catch (e) { seen = false; }
  const link = $("#tour-link");
  if (link) link.classList.toggle("unseen", !seen && state.mode !== "reader");
}
