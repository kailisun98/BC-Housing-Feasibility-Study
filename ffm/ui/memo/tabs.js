/* The memo's tabs (26 Nov 2026; the owner: "too much scrolling... create tabs which allow the architect to switch
   between the answers, the drawings/schedule, clauses, ledger, inputs", laid out by a UX designer's brief the same day).

   Manager, Architect and Operator read the memo one part at a time under a strip of tabs that sticks under the bars;
   the Reader keeps the long page, the paper on screen. Every panel is in the DOM (renderMemo draws them all), so a tab
   only shows its panel: the WAI-ARIA tabs pattern with automatic activation (arrows, Home, End; roving tabindex), the
   other panels `hidden="until-found"` where the browser has it, so the page's own find still reaches their text and a
   match selects the panel. The tab is kept in the link (?tab=, left out for the layout's default), across a run, a
   comparison and a mode switch where the new layout has it, and each tab keeps its own scroll for the session.
   The PDFs and Print go through paper.js and do not see any of this. */

import { $, $$, h } from "../core/util.js";
import { state } from "../core/state.js";

/* The tabs in order: [id, label, the layouts that have it]. The comparison shows only while two runs are compared,
   the operator's figures only in the Operator layout (renderMemo draws a panel only where there is one). */
export const TABS = [
  { id: "operating", label: "Operating figures" },
  { id: "answers", label: "Answers" },
  { id: "comparison", label: "Comparison" },
  { id: "drawings", label: "Drawings and areas" },
  { id: "clauses", label: "Clauses" },
  { id: "ledger", label: "Ledger" },
  { id: "inputs", label: "Inputs and sources" },
];
const LABEL = Object.fromEntries(TABS.map(t => [t.id, t.label]));

const UNTIL_FOUND = typeof document !== "undefined" && "onbeforematch" in document.documentElement;
let current = (() => { try { return new URLSearchParams(location.search).get("tab") || null; } catch (e) { return null; } })();
const scrollOf = {};          // each tab's own scroll, for the session
const onShow = {};            // what a panel needs the first time it is shown (the drawings refit their labels)

export const tabbed = () => state.mode !== "reader";
export const defaultTab = () => (state.mode === "operator" ? "operating" : "answers");
export const currentTab = () => current;

/* What runs when a tab is shown: `whenShown("drawings", refit)`. Called again on every showing. */
export function whenShown(id, fn) { onShow[id] = fn; }

/* Draws the strip from the panels the memo has, and shows the tab asked for (`want`), else the one on screen, else
   the layout's default. In the Reader every panel shows and the strip is hidden. */
export function renderTabs(memoEl, want = null) {
  const bar = $("#memo-tabs", memoEl);
  const panels = $$(".memo-panel", memoEl);
  if (!bar || !panels.length) return;
  if (!tabbed()) {
    bar.hidden = true;
    for (const p of panels) { p.hidden = false; p.removeAttribute("role"); p.removeAttribute("aria-labelledby"); p.removeAttribute("tabindex"); }
    // the Reader's link names no tab: it has none
    try {
      const q = new URLSearchParams(location.search);
      if (q.has("tab")) { q.delete("tab"); const s = q.toString().replace(/%2F/g, "/"); history.replaceState(history.state, "", `${location.pathname}${s ? `?${s}` : ""}${location.hash}`); }
    } catch (e) { /* no history to change */ }
    return;
  }
  bar.hidden = false;
  const ids = panels.map(p => p.dataset.tab);
  const present = TABS.filter(t => ids.includes(t.id));
  bar.innerHTML = present.map((t, i) => `<button type="button" role="tab" class="memo-tab" id="tab-${t.id}" aria-controls="panel-${t.id}" aria-selected="false" tabindex="-1" data-tab="${t.id}"><span class="mt-n" aria-hidden="true">${String(i + 1).padStart(2, "0")}</span> ${h(t.label)}</button>`).join("");
  for (const p of panels) {
    p.setAttribute("role", "tabpanel");
    p.setAttribute("aria-labelledby", `tab-${p.dataset.tab}`);
    if (UNTIL_FOUND && !p.dataset.found) {
      p.dataset.found = "1";
      p.addEventListener("beforematch", () => selectTab(p.dataset.tab, { scroll: false }));
    }
  }
  if (!bar.dataset.wired) {
    bar.dataset.wired = "1";
    bar.addEventListener("click", e => { const b = e.target.closest(".memo-tab"); if (b) selectTab(b.dataset.tab, { focus: true }); });
    bar.addEventListener("keydown", e => {
      const tabs = $$(".memo-tab", bar), i = tabs.indexOf(document.activeElement);
      if (i < 0) return;
      const to = { ArrowRight: (i + 1) % tabs.length, ArrowLeft: (i - 1 + tabs.length) % tabs.length, Home: 0, End: tabs.length - 1 }[e.key];
      if (to === undefined) return;
      e.preventDefault();
      selectTab(tabs[to].dataset.tab, { focus: true });
    });
  }
  if (!hashWired) {
    // a link whose #hash points inside a panel opens that panel
    hashWired = true;
    window.addEventListener("hashchange", () => {
      const t = location.hash.length > 1 ? document.getElementById(decodeURIComponent(location.hash.slice(1))) : null;
      const tab = tabOf(t);
      if (tab && tabbed()) { selectTab(tab, { scroll: false }); t.scrollIntoView({ block: "start" }); }
    });
  }
  // a new memo, or the same memo laid out again: the tabs' kept scrolls belonged to the page as it was
  for (const k of Object.keys(scrollOf)) delete scrollOf[k];
  const hashTab = location.hash.length > 1 ? tabOf(document.getElementById(decodeURIComponent(location.hash.slice(1)))) : null;
  const pick = [want, hashTab, current, defaultTab()].find(id => id && ids.includes(id)) || present[0].id;
  selectTab(pick, { scroll: false });
}
let hashWired = false;

/* Shows one tab's panel. `focus` puts the keyboard on the tab; `scroll` brings the panel's top just under the strip
   where the strip is stuck, and restores the tab's own scroll otherwise; `sync` writes the link. */
export function selectTab(id, { focus = false, scroll = true, sync = true } = {}) {
  const memoEl = $("#memo");
  const bar = memoEl && $("#memo-tabs", memoEl);
  if (!bar || bar.hidden) return false;
  const panel = $(`#panel-${id}`, memoEl);
  if (!panel) return false;
  const was = current;
  if (was && was !== id) scrollOf[was] = window.scrollY;
  current = id;
  for (const b of $$(".memo-tab", bar)) {
    const on = b.dataset.tab === id;
    b.setAttribute("aria-selected", String(on));
    b.tabIndex = on ? 0 : -1;
    if (on && focus) b.focus({ preventScroll: true });
    if (on) b.scrollIntoView({ block: "nearest", inline: "nearest" });
  }
  for (const p of $$(".memo-panel", memoEl)) {
    const on = p.id === panel.id;
    p.tabIndex = on ? 0 : -1;   // a panel hidden until found still has a box: keep it out of the tab order
    if (on) {
      p.removeAttribute("hidden");
      if (was && was !== id) { p.classList.remove("panel-in"); void p.offsetWidth; p.classList.add("panel-in"); }
    } else if (UNTIL_FOUND) p.setAttribute("hidden", "until-found");
    else p.hidden = true;
  }
  if (onShow[id]) onShow[id]();
  if (scroll && was !== id) {
    const stuck = bar.getBoundingClientRect().top <= parseFloat(getComputedStyle(bar).top || "0") + 1;
    if (scrollOf[id] != null) window.scrollTo({ top: scrollOf[id], behavior: "instant" });
    else if (stuck) window.scrollTo({ top: window.scrollY + panel.getBoundingClientRect().top - bar.getBoundingClientRect().bottom - 8, behavior: "instant" });
  }
  if (sync) {
    try {
      const q = new URLSearchParams(location.search);
      if (id === defaultTab()) q.delete("tab"); else q.set("tab", id);
      const s = q.toString().replace(/%2F/g, "/");
      history.replaceState(history.state, "", `${location.pathname}${s ? `?${s}` : ""}${location.hash}`);
    } catch (e) { /* a page without history: the link keeps its own */ }
  }
  return true;
}

/* The tab a part of the memo is in, for a jump to it: the panel around it. */
export function tabOf(el) {
  const p = el && el.closest && el.closest(".memo-panel");
  return p ? p.dataset.tab : null;
}

/* A tab's label, for the status line and the walkthrough. */
export const tabLabel = id => LABEL[id] || id;
