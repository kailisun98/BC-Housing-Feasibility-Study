/* The memo pane: the quiet cards before a run, "No memo is open" for the reader, and the memo itself (title block,
   answers, figures, clauses, ledger, inputs, sources, stamp), with the run tools moved into its title block. */

import { areaScheduleHtml, operatorDesk, wireAreaSchedule, wireOperatorDesk } from "./operator.js";
import { $, $$, cap, fmtNum, h, REV, scrollBehavior, toast, todayISO } from "../core/util.js";
import { state, STATIC } from "../core/state.js";
import { optWord } from "../fields.js";
import { syncStaleBand } from "../files.js";
import { byRev, isDraft, nextRev, openRun, rev, runName } from "../runs.js";
import { answerAllowed, answerFunders, answerMoney, answerUnsure, unverifiedLine, wireMoneyFold } from "./answers.js";
import { renderClauses, UNIT_WORD, withPlans } from "./clauses.js";
import { renderLedger, wireLedger } from "./ledger.js";
import { compareFoldLine, compareResult, renderSideBySide, wireSideBySide } from "./side-by-side.js";
import { changesPhrase, renderChanges } from "./changes.js";
import { wordsHtml } from "./words.js";
import { frontHtml } from "./front.js";

/* A date as a reader writes it, "23 Oct 2026", in the title block, the answers and the paper (20 Nov 2026: ISO dates
   read as machine text); a time, where there is one and it is asked for, follows: "18 Nov 2026, 14:03". The machine's
   own places (shell lines, the fingerprint card's file list) keep ISO. Pure. */
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function dateWords(iso, withTime = false) {
  const m = /^(\d{4})-(\d\d)-(\d\d)(?:[T ](\d\d):(\d\d))?/.exec(String(iso || ""));
  if (!m) return String(iso || "");
  return `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}${withTime && m[4] ? `, ${m[4]}:${m[5]}` : ""}`;
}

/* An option's name as a short title (20 Nov 2026: the Option cell ran six lines in 160 px; Side by side named "R1 · As
   approved"): the part before the colon, the site's own address taken off its front, a bracket kept to its first
   phrase, and a long name cut at its first comma or bracket. Pure. */
export function briefName(name, site = null) {
  let s = String(name || "").trim();
  const colon = s.indexOf(":");
  if (colon >= 6) s = s.slice(0, colon).trim();
  const addr = String((site && site.address) || "").split(",")[0].trim();
  if (addr && s.toLowerCase().startsWith(`${addr.toLowerCase()},`)) s = s.slice(addr.length + 1).trim().replace(/^./, c => c.toUpperCase());
  s = s.replace(/\s*\(([^(),;]+)[,;][^()]*\)/g, " ($1)");
  if (s.length > 34 && s.includes(",")) s = s.split(",")[0].trim();
  if (s.length > 40 && s.includes(" (")) s = s.split(" (")[0].trim();
  return s;
}
import { renderFigures, wireFigures } from "../figures/cards.js";
import { foot, renderStage } from "../route-stage.js";
import { applyModeToMemo, setView } from "../modes.js";
import { myName } from "../issue.js";

export function renderQuiet() {
  if (state.run) return;  // a run is on screen: leave it
  if (state.mode === "manager") { renderStage(); return; }   // the manager's pane answers each stop as it is taken
  if (state.mode === "reader") { renderNoMemo(); return; }
  const site = state.site || {}, opt = state.option || {};
  const n = state.rules.length;
  placeRunTools(false);
  $(".memo-pane").classList.remove("staging", "has-memo");
  $("#memo").className = "memo";
  $("#memo").innerHTML = `
    <div class="card memo-head">
      <h1>${h(site.address || site.id || "A site")}</h1>
      <div class="memo-meta">
        <div><b>Option</b><span>${h(opt.name || opt.id || "—")}</span></div>
        <div><b>Proponent</b><span>${h(opt.proponent || "—")}</span></div>
        <div><b>Rules as of</b><span>${h(dateWords($("#as-of").value || todayISO()))}</span></div>
      </div>
      <p class="quiet">Run the rules evaluates this site and option against the ${n || "dated"} rules in force on that date, ${STATIC ? "in your browser, with nothing uploaded, and keeps the memo in this tab" : "writes the memo to <code>outputs/</code>"}, and reads it here: four answers first, then the massing and the full ledger.</p>
    </div>
    <div class="answers">
      ${quietCard("01 · Is it allowed", "Is it allowed?", "Outright under the district, then by rezoning under the City policy that applies.")}
      ${quietCard("02 · Does it fit the funders", "Does it fit the funders?", "The programs the option targets, tested against their published criteria.")}
      ${quietCard("03 · Still unsure", "What is still unsure, and who resolves it?", "Every open item names the person and the document.")}
      ${quietCard("04 · Does the money work", "Does the money work?", "Capital cost, net operating income, the funding stack and the gap, feasibility grade, every line citing its assumption.")}
    </div>`;
}

/* The reader with no memo open (16 Nov 2026; before, four placeholder verdicts and an instruction to run, with the
   run controls hidden): where a memo comes from, and this site's memos to open. */
export function renderNoMemo() {
  placeRunTools(false);
  $(".memo-pane").classList.remove("staging", "has-memo");
  const runs = byRev(state.runs || []).filter(r => !isDraft(r.run_id));   // the reader is offered issued memos only
  const memo = $("#memo");
  memo.className = "memo landed";
  // a link that names a run is opening one: say so, not "No memo is open" (17 Nov 2026: it flashed while the run loaded)
  const asked = new URLSearchParams(location.search).get("run");
  if (asked && !state.run && !state.runLinkFailed) {
    memo.innerHTML = `<div class="card memo-head no-memo"><h1>Opening the memo…</h1><p class="quiet">${h(asked.split("/")[0].replace(/-/g, " "))}, ${h(asked.split("/")[1] || "")}</p></div>`;
    return;
  }
  memo.innerHTML = `<div class="card memo-head no-memo">
      <h1>No memo is open</h1>
      <p class="quiet">A memo opens here from the link the development manager or the architect sends you (it ends in <code>?run=…</code>); a PDF they attach is the same memo on paper. To make one, switch to Manager in the top bar.</p>
      ${runs.length ? `<p class="stage-memos"><span class="cont">Or open one of ${h(String((state.site && state.site.address) || "this site's").split(",")[0])}'s memos:</span> ${runs.map(r => `<button type="button" class="linkish" data-open-run="${h(r.run_id)}">${h(runName(r))}</button>`).join(`<span class="cont"> · </span>`)}</p>` : ""}
    </div>`;
  $$("[data-open-run]", memo).forEach(b => b.addEventListener("click", () => openRun(b.dataset.openRun).catch(e => toast(e.message, true))));
}

function quietCard(eyebrow, title, line) {
  const n = String(eyebrow).trim().charAt(1);   // "01 · …" → 1
  return `<section class="card answer">
    <h2><span class="badge">${h(n)}</span> ${h(title)}</h2>
    <p class="verdict quiet">${h(line)}</p>
  </section>`;
}

export function renderMemo(run) {
  const L = run.ledger, res = L.results, ans = L.summary.answers;
  const site = L.inputs.site, opt = L.inputs.option;
  const parts = [];

  // 1. header: the memo's title block. A comparison adds a cell: Revision (with the delta) when the rules moved, or
  // Compared with when two options are read under the same rules
  const d = run.diff;
  const kind = d ? compareKind(d) : null;
  const B = d && run.compareLedger ? run.compareLedger : null;
  const prevRev = state.compareRun ? rev(state.compareRun) : "an earlier memo";
  // the comparison's result where the title block names it, with a jump to the card that shows it (24 Nov 2026)
  const cmpTo = kind === "options" && B ? "side-by-side" : "changes";
  const cmpWhat = !d ? "" : cmpTo === "side-by-side" ? compareResult(run) : changesPhrase(d);
  const cmpLine = cmpWhat ? `<span class="cmp-result">${h(cap(cmpWhat))}. <a href="#${cmpTo}" class="jump">${cmpTo === "side-by-side" ? "Side by side" : "What changed"}</a></span>` : "";
  const cmpCell = !d ? "" : kind === "rules"
    ? `<div class="rev-cell"><b>Revised from</b><span>${REV} ${h(prevRev)} <span class="cont">(rules as of ${h(dateWords(d.previous_as_of))})</span>${cmpLine}</span></div>`
    : `<div class="cmp-cell"><b>Compared with</b><span><b class="rev-no">${h(prevRev)}</b> ${B ? h(briefName(optionName(B), site)) : "a run"} <span class="cont">(as of ${h(dateWords(d.previous_as_of))})</span>${cmpLine}</span></div>`;
  // the option's short name in the cell, its whole name beneath in a quieter line (20 Nov 2026: 375 Glen Drive's name
  // ran six lines in a 160 px cell); the engine's version leaves the reading path for the fingerprint card
  const fullName = String(opt.name || opt.id || "");
  const shortOpt = briefName(fullName, site);
  parts.push(`<div class="card memo-head">
    <h1>${h(site.address || site.id)}</h1>
    <div class="memo-meta">
      <div class="opt-cell${fullName.length > 90 ? " long" : ""}"><b>Option</b><span>${h(shortOpt)}${shortOpt !== fullName ? `<span class="opt-full">${h(fullName)}</span>` : ""}</span></div>
      <div><b>Proponent</b><span>${opt.proponent ? h(opt.proponent) : "<i>not named</i>"}${opt.proponent_type ? ` <span class="cont">· ${h(optWord("option", "proponent_type", opt.proponent_type))}</span>` : ""}</span></div>
      <div><b>Rules as of</b><span>${h(dateWords(L.run.as_of))}<span class="cont next-asof" id="memo-next-asof">${nextAsOfWords(L.run.as_of)}</span></span></div>
      <div><b>Revision</b><span><b class="rev-no">${h(rev(run.run_id))}</b>${isDraft(run.run_id) ? ` <span class="cont">· not issued; ${STATIC ? "a draft in this tab" : `issuing makes it ${h(nextRev())}`}${run.made_by ? `; made by ${h(run.made_by)}` : ""}</span>` : ""}${issuedLine(run)}</span></div>
      ${cmpCell}
    </div>
    ${optionFiguresHtml(site, opt, run)}
    <div class="memo-actions" id="memo-actions"></div>
    <nav class="memo-index" id="memo-index" aria-label="In this memo"></nav>
    <p class="quiet memo-disclaimer">A feasibility screen, not legal, planning or funding advice. Deterministic output of the rule stack listed under Sources: same inputs and rule set, same memo; every number links to the document it came from. An independent student tool: not affiliated with, reviewed by or a position of BC Housing, the Province, CMHC or the City of Vancouver.</p>
  </div>`);
  // a run handed to this reader carries the sender's note, where the reader can see it (15 Nov 2026)
  // the note addressed to this browser's name, else to the layout on screen where it named no one (26 Nov 2026)
  const me = myName().toLowerCase();
  const note = (run.issues || []).filter(i => (i.to_name ? me && String(i.to_name).trim().toLowerCase() === me : i.to === state.mode)).slice(-1)[0];
  if (note) parts.push(`<div class="card issue-note"><b>From ${note.name ? `${h(note.name)} (the ${h(note.by)})` : `the ${h(note.by)}`}, ${h(dateWords(note.issued_at, true))}:</b> ${note.note ? h(note.note) : "<i>no note</i>"}</div>`);

  // 2. the four answers come first in every layout (20 Nov 2026: a manager read ~1,200 px of comparison tables before
  // answer 01, and on a phone the first answer moved from 1,236 px to 4,279 px), with the words they use and the rules
  // not yet checked; 3. the comparison: the two runs side by side, their pickers heading the columns, then What
  // changed, folded to one line for the reader; 4. the massing figures beside the answers at >=1600 px, under them
  // otherwise; 5. the clauses; 6. the full ledger, inputs, sources, version stamp. Only a change in the rules carries
  // the delta into the clauses and the ledger (the Revision Rule); two options differ in their numbers, not their rules.
  state.refOf = memoRefs(res);   // the paper's A1, C4 references, the same on screen (15 Nov 2026)
  const compareParts = [B ? renderSideBySide(run) : "", d ? renderChanges(d, L, run) : ""].filter(Boolean).join("\n");
  const compare = !compareParts ? "" : `<details class="compare-fold"${state.mode === "reader" ? "" : " open"}>
      <summary>${compareFoldLine(run)}</summary>
      ${compareParts}
    </details>`;
  const changed = new Set(kind === "rules" ? (d.changes || []).map(c => c.rule_id) : []);
  const rest = [];
  // the ledger reads the exits as the plans found them, as the clauses and answer 3 do (17 Nov 2026: Pass in the
  // clauses, Info in the ledger)
  rest.push(renderLedger(withPlans(res, run), changed));
  rest.push(renderInputs(site, opt));
  rest.push(renderSources(res, site, opt));
  rest.push(renderStamp(L.run, run.run_id));
  // the clauses stand on their own so the reader's order can be the paper's: answers, comparison, clauses, massing, ledger
  const figures = renderFigures(run);
  // the operator's desk leads the operator's layout; the area schedule follows the drawings in every layout (24 Nov 2026)
  const desk = operatorDesk(run);
  if (desk) parts.push(desk);
  // the front sheet, shaped as an ask, before the answers in every layout (25 Nov 2026)
  parts.push(frontHtml(run));
  parts.push(`<div class="memo-body">
    <div class="answers">${answerAllowed(L, run)}${answerFunders(L, run)}${answerUnsure(L, run)}${answerMoney(run)}${unverifiedLine(L)}${wordsHtml(run)}</div>
    ${compare ? `<div class="memo-compare">${compare}</div>` : ""}
    ${figures}
    ${areaScheduleHtml(run) ? `<div class="memo-areas">${areaScheduleHtml(run)}</div>` : ""}
    <div class="memo-clauses">${renderClauses(res, L, changed, run)}</div>
    <div class="memo-rest">${rest.join("\n")}</div>
  </div>`);

  // the run pickers leave the memo before it is replaced and come back after; a picker that had focus keeps it
  const memoEl = $("#memo");
  const focused = document.activeElement && ["open-run", "compare-run"].includes(document.activeElement.id) ? document.activeElement : null;
  placeRunTools(false);
  memoEl.innerHTML = parts.join("\n");
  memoEl.className = "memo";
  memoEl.dataset.issuedManager = (run.issues || []).some(i => i.to === "manager") ? "1" : "";
  $(".memo-pane").classList.remove("no-run", "staging");
  $(".memo-pane").classList.add("has-memo");
  void memoEl.offsetWidth;  // restart the fade
  memoEl.classList.add("landed");
  placeRunTools(true);
  indexMemo(memoEl);
  wireJumps(memoEl);
  if (focused && document.activeElement !== focused) focused.focus({ preventScroll: !!focused.closest("#side-by-side") });
  wireSideBySide(run);
  wireFigures(run);
  wireLedger();
  applyModeToMemo();
  wireMoneyFold();
  wireOperatorDesk();
  wireAreaSchedule(run);
  setPrintFooter(run);
  syncStaleBand();
}

/* The memo's sheet index, in its title block, as a drawing set lists its sheets (24 Nov 2026: 11,000 to 19,000 px of
   memo with no way across it but the scroll bar). Only the parts this memo has; the layouts that leave a part out hide
   its link (app.css), and a jump opens any fold the part sits in. */
const MEMO_INDEX = [
  ["ask", ".memo-ask", "The ask"],
  ["answers", ".memo-body > .answers", "The four answers"],
  ["compare", ".memo-compare", "The comparison"],
  ["figures", ".memo-body > .figures", "Drawings"],
  ["areas", ".memo-areas", "Area schedule"],
  ["clauses", ".memo-clauses", "Clauses"],
  ["ledger", ".memo-rest .ledger", "Ledger"],
  ["inputs", ".memo-rest .inputs-used", "Inputs"],
  ["sources", ".memo-rest .sources", "Sources"],
  ["stamp", ".memo-rest .stampbox", "Fingerprint"],
];

function indexMemo(memoEl) {
  const nav = $("#memo-index", memoEl);
  if (!nav) return;
  const links = [];
  for (const [k, sel, word] of MEMO_INDEX) {
    const el = $(sel, memoEl);
    if (!el) continue;
    if (!el.id) el.id = `memo-${k}`;
    links.push(`<li><a href="#${el.id}" class="jump" data-k="${k}">${h(word)}</a></li>`);
  }
  nav.innerHTML = `<span class="mi-key" aria-hidden="true">In this memo</span><ol>${links.join("")}</ol>`;
}

/* A jump inside the memo (the index, the title block's comparison): opens the folds the target sits in, brings the
   layout that shows it when this one leaves it out, scrolls to it and moves the keyboard there. Wired once on #memo. */
function wireJumps(memoEl) {
  if (memoEl.dataset.jumps) return;
  memoEl.dataset.jumps = "1";
  memoEl.addEventListener("click", e => {
    const a = e.target.closest("a.jump[href^='#']");
    if (!a) return;
    const t = document.getElementById(a.getAttribute("href").slice(1));
    if (!t) return;
    e.preventDefault();
    for (let d = t.closest("details"); d; d = d.parentElement ? d.parentElement.closest("details") : null) d.open = true;
    if (!t.getClientRects().length) setView("detailed");
    t.scrollIntoView({ behavior: scrollBehavior(), block: "start" });
    if (!t.hasAttribute("tabindex")) t.tabIndex = -1;
    t.focus({ preventScroll: true });
  });
}

/* Who issued the memo, to whom and when: the first issue, which gave it its number, and the latest where there is
   another (26 Nov 2026, the third panel: the title block and the paper had no issued-by). The paper prints the same. */
const ROLE_WORD = { architect: "the architect", manager: "the development manager", operator: "the operator", reader: "the board" };

export function issuedWords(i) {
  if (!i) return "";
  const from = i.name ? `${i.name} (${ROLE_WORD[i.by] || i.by})` : (ROLE_WORD[i.by] || i.by);
  const to = i.to_name ? `${i.to_name} (${ROLE_WORD[i.to] || i.to})` : (ROLE_WORD[i.to] || i.to);
  return `issued by ${from} to ${to}, ${dateWords(i.issued_at, true)}`;
}

function issuedLine(run) {
  const list = (run.issues || []).slice().sort((a, b) => String(a.issued_at).localeCompare(String(b.issued_at)));
  if (!list.length) return "";
  const first = list[0], last = list[list.length - 1];
  return `<span class="cont issued-by">${h(cap(issuedWords(first)))}${last !== first ? `; last ${h(issuedWords(last))}` : ""}</span>`;
}

/* Beside the memo's own rules date, the next run's where the top bar's differs (26 Nov 2026, Kai: opening a memo no
   longer resets the top bar's date). The reader runs nothing, so the line is not theirs (app.css hides it). */
const nextAsOfWords = memoAsOf => {
  const next = $("#as-of").value || todayISO();
  return next !== memoAsOf ? ` · the next run reads ${h(dateWords(next))}` : "";
};

export function syncNextAsOf() {
  const el = $("#memo-next-asof");
  if (el && state.run) el.innerHTML = nextAsOfWords(state.run.as_of);
}

/* An option's name as the reader knows it. */
export const optionName = L => (L && L.inputs && L.inputs.option && (L.inputs.option.name || L.inputs.option.id)) || "option";

/* The option in figures, under the title block, in every view (16 Nov 2026: after a run the stage's figures left
   the screen and only the folded Option card still had them): the envelope, the homes, the tiers, the tenure. */
function optionFiguresHtml(site, opt, run) {
  const units = opt.units || {};
  const n = Object.values(units).reduce((t, v) => t + (v || 0), 0);
  const fsr = opt.gfa_m2 && site.site_area_m2 ? (opt.gfa_m2 / site.site_area_m2).toFixed(2) : null;
  const tiers = opt.rent_tiers_units;
  const pm = run && run.massing && run.massing.masses && run.massing.masses.find(x => x.name === "proposed");
  // the interpunct that opens a cell's second part is tied to what follows it, so it never hangs at a line's end
  const cell = (k, v, sub) => `<div><b>${h(k)}</b><span>${v}${sub ? ` <span class="cont">${String(sub).replace(/^· /, "·&nbsp;")}</span>` : ""}</span></div>`;
  // the homes the plans place, beside the count the money and the funders read (17 Nov 2026: the title block said 170
  // while answer 3 said 114 fit, and nothing near the 170 said so)
  const lay = run && run.layout;
  const placed = lay && lay.units_total && lay.units_placed != null && lay.units_placed < lay.units_total ? lay.units_placed : null;
  // the homes' count in its cell and the mix on a line of its own across two cells' width (20 Nov 2026: "105 · 30
  // studio, 37 1-bed, 26 2-bed, 12 3-bed+ · 69 fit the plate (answer 3)" wrapped to four lines beside one-line cells)
  const mix = Object.entries(units).filter(([, v]) => v).map(([k, v]) => `<span class="nw">${v} ${UNIT_WORD[k] || k}</span>`).join(", ");
  return `<div class="memo-figures">
    ${cell("Storeys", opt.storeys != null ? h(opt.storeys) : "<i>not given</i>", opt.height_m != null ? `· ${h(opt.height_m)}&nbsp;m` : "")}
    ${cell("Floor area", opt.gfa_m2 != null ? `${h(fmtNum(opt.gfa_m2))}&nbsp;m²` : "<i>not given</i>", fsr ? `· FSR&nbsp;${h(fsr)}` : "")}
    ${cell("Homes", n ? h(n) : "<i>not given</i>", placed != null ? `<span class="warn-text">·&nbsp;<span class="nw">${h(placed)} fit</span> the floors in the first plans (answer 3)</span>` : "")}
    ${mix ? `<div class="mix-cell"><b>Mix</b><span>${mix}</span></div>` : ""}
    ${cell("Rent tiers", tiers ? tierWords(tiers, n) : "<i>not split</i>", "")}
    ${cell("Tenure", h(optWord("option", "tenure", opt.tenure) || "not set"), opt.housing_agreement_years ? `· <span class="nw">${h(opt.housing_agreement_years)}‑year agreement</span>` : "")}
    ${plateCell(cell, pm)}
  </div>`;
}

/* The plate, or why there is none: a dimension at or below zero means the yards leave no room on the lot, and the
   memo says so in words instead of printing a negative width (17 Nov 2026: 609 Heatley Ave read "34.2 × -6.6 m ·
   -225.7 m² a floor" under "Allowed outright"). */
function plateCell(cell, pm) {
  if (!pm) return cell("Plate", "<i>no massing</i>", "");
  const w = Number(pm.plate_width_m), d = Number(pm.plate_depth_m), a = Number(pm.plate_area_m2);
  if (!(w > 0) || !(d > 0) || !(a > 0)) return cell("Plate", `<span class="warn-text">no plate fits</span>`, "· the yards leave no room on the lot; the architect checks the setbacks");
  return cell("Plate", `${h(pm.plate_width_m)} × ${h(pm.plate_depth_m)}&nbsp;m`, `· <span class="nw">${h(fmtNum(pm.plate_area_m2))} m²</span> a floor`);
}

/* The rent tiers, and a warning where they do not add up to the homes (17 Nov 2026: 30 / 49 / 20 printed under 176
   homes, the split of an earlier 99, and the fund's check failed on it without the title block saying why). */
function tierWords(t, n) {
  const sum = (t.market || 0) + (t.rgi || 0) + (t.deep_subsidy || 0);
  const words = `${h(t.market || 0)} market · ${h(t.rgi || 0)} RGI · ${h(t.deep_subsidy || 0)} deep subsidy`;
  return n && sum !== n ? `${words} <span class="warn-text">· ${h(sum)} of ${h(n)} homes</span>` : words;
}

/* Whether a ledger result takes a reference: every rule that applies to this site does, whatever its status; one
   written for another district, or with no version in force on the date, is listed but not numbered (20 Nov 2026,
   Kai: with 48 other districts' schedules in the stack, 998 E 19th Ave's rezoning policy had become A20). The engine
   marks those results `elsewhere`; a ledger written before that says so in its finding. engine.takes_ref is the twin. */
export const takesRef = r => !(r && (r.elsewhere || (r.status === "not_applicable" && /^(Written for |No version of this rule is in force)/.test(r.finding || ""))));

/* The paper memo's references, A1 to F7: the layer's letter and the rule's place among the rules that apply here, in
   the ledger's order. The screen cites the same, so a planner's "re C5" means the same thing in both renderings. Pure. */
export function memoRefs(res) {
  const refOf = {}, n = {};
  for (const r of res || []) {
    if (!takesRef(r)) continue;
    n[r.layer] = (n[r.layer] || 0) + 1;
    refOf[r.rule_id] = `${r.layer}${n[r.layer]}`;
  }
  return refOf;
}

export const refOf = id => (state.refOf && state.refOf[id]) || "";

export const refTagOf = id => (refOf(id) ? `<b class="ref">${h(refOf(id))}</b> ` : "");

/* A rule id with a break allowed after each dot and underscore, so a narrow column wraps it between its words. */
export const idBreak = id => h(id).replace(/([._])/g, "$1<wbr>");

/* What kind of comparison this is: the rules moved (another as-of date or other rule files), two options were read
   under the same rules, or the two runs are the same. attachCause decides it from the two ledgers when it can. */
export function compareKind(d) {
  if (d.kind) return d.kind;
  return d.rules_changed || d.previous_as_of !== d.current_as_of ? "rules" : "options";
}

/* Every printed page carries the address, the date and the memo's revision in its footer, and its page number. */
function setPrintFooter(run) {
  let st = $("#print-page");
  if (!st) { st = document.createElement("style"); st.id = "print-page"; document.head.appendChild(st); }
  const site = (run.ledger && run.ledger.inputs && run.ledger.inputs.site) || {};
  const text = `First Read · ${site.address || site.id || ""} · rules as of ${dateWords(run.as_of)} · ${rev(run.run_id)}`.replace(/["\\\n]/g, " ");
  st.textContent = `@media print { @page { margin: 14mm 14mm 16mm;
    @bottom-left { content: "${text}"; font: 7.5pt "IBM Plex Mono", monospace; color: #444; }
    @bottom-right { content: counter(page) " / " counter(pages); font: 7.5pt "IBM Plex Sans", sans-serif; color: #444; } } }`;
}

/* The two run pickers. With two runs compared they head the Side by side card's A and B columns, so the choice
   sits above what it changes; otherwise, and whenever the memo is about to be replaced, they sit above the memo.
   In the card their keys name the column; a hidden phrase keeps what each one does in its accessible name. */
const RUN_TOOLS = [["open", "#tool-open", "This memo", " (open another memo)"], ["compare", "#tool-compare", "Compared with", " (choose the memo to compare with)"]];

export function placeRunTools(intoMemo) {
  placeActions(intoMemo);
  const tools = $(".memo-tools");
  for (const [slot, id, word, purpose] of RUN_TOOLS) {
    const label = $(id), eyebrow = $(".eyebrow", label);
    if (!eyebrow.dataset.text) eyebrow.dataset.text = eyebrow.textContent;
    let hint = $(".tool-purpose", label);
    if (!hint) { hint = document.createElement("span"); hint.className = "sr-only tool-purpose"; eyebrow.after(hint); }
    const cell = intoMemo ? $(`#side-by-side [data-slot="${slot}"]`) : null;
    if (cell) { cell.prepend(label); eyebrow.textContent = word; hint.textContent = purpose; }
    else { tools.insertBefore(label, $("#compare-note")); eyebrow.textContent = eyebrow.dataset.text; hint.textContent = ""; }
  }
  // the view switch stays when both pickers have moved into the Side by side card (24 Nov 2026: comparing hid
  // Summary, Detailed and 3D preview with the row they shared)
  tools.hidden = !$(".tool, #view-switch", tools);
}

/* The memo's actions, Download PDF first, sit in its title block (16 Nov 2026; before, at the foot of a page some
   9,000 px long), with the issue form and the Export to Revit panel opening under them (24 Nov 2026: the Revit panel
   opened some 17,900 px below its button). Whenever the memo is about to be replaced they go back to the export
   footer, so they are never thrown away with it; the footer shows only while it holds them. */
function placeActions(intoMemo) {
  const bar = $("#export-actions"), issue = $("#issue-panel"), board = $("#board-panel"), revit = $("#export-panel"), foot = $("#step-export");
  if (!bar || !foot) return;
  const slot = intoMemo ? $("#memo-actions") : null;
  if (slot) { slot.append(bar, issue, board, revit); foot.hidden = true; return; }
  if (bar.parentElement !== foot) { $("h2", foot).after(bar); bar.after(issue); issue.after(board); foot.append(revit); }
  foot.hidden = false;
}

function renderInputs(site, opt) {
  const u = opt.units || {};
  // the counts as the title block gives them, and what is not given said in words (17 Nov 2026: "owner: —.",
  // "units studio 35, one bed 70")
  const units = Object.entries(u).filter(([, v]) => v != null).map(([k, v]) => `${v} ${UNIT_WORD[k] || k.replace(/_/g, " ")}`).join(", ");
  const tenure = optWord("option", "tenure", opt.tenure);
  const owner = site.owner || optWord("site", "owner_type", site.owner_type);
  const given = (x, unit) => (x == null ? null : `${fmtNum(x)}${unit}`);
  const figs = [given(opt.storeys, " storeys"), given(opt.height_m, " m"), given(opt.gfa_m2, " m² of floor area")].filter(Boolean).join(", ") || "storeys, height and floor area not given";
  return `<section class="card section inputs-used">
    <h2>Inputs</h2>
    <ul>
      <li>Site <code>${h(site.id)}</code>: ${h(site.zoning_district || "district not given")}, ${site.site_area_m2 != null ? `${h(fmtNum(site.site_area_m2))} m²` : "lot area not given"}${site.frontage_m != null ? `, ${h(site.frontage_m)} × ${h(site.depth_m)} m` : ""}; ${owner ? `owner ${h(owner)}` : "owner not given"}.</li>
      <li>Option <code>${h(opt.id)}</code>: ${h(figs)}; ${units ? `homes ${h(units)}` : "homes not given"}; ${tenure ? `tenure ${h(tenure)}` : "tenure not given"}.</li>
      ${site.notes ? `<li>Site notes: <span class="cont">${h(site.notes)}</span></li>` : ""}
      ${opt.notes ? `<li>Option notes: <span class="cont">${h(opt.notes)}</span></li>` : ""}
    </ul>
  </section>`;
}

function renderSources(res, site, opt) {
  const seen = new Set();
  const items = [];
  // the documents behind the rules that applied here; a rule for another district or program is named under Clauses,
  // its document is not this memo's source (17 Nov 2026: a C-2 memo listed the RM-1, RT-4 and CD-1 sources)
  for (const r of res) {
    if (r.status === "not_applicable") continue;
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
    <h2>Sources</h2>
    <ul>${items.join("")}</ul>
  </section>`;
}

/* The rules this memo read, and their fingerprint: the one place the stamp's hash is shown. */
function renderStamp(run, runId) {
  const st = run.stamp;
  const files = Object.entries(st.rules_files || {}).map(([f, hsh]) => `<li><code>${h(f)}</code> <span class="hash">${h(hsh.slice(0, 16))}…</span></li>`).join("");
  return `<section class="card section stampbox">
    <h2>Rules fingerprint</h2>
    <p>This memo, ${h(rev(runId))} on this site, read the rule files below and the versions in force on ${h(dateWords(run.as_of))}, with engine ${h(run.engine_version || "")}. Together they are fingerprinted, so the same inputs under the same fingerprint always give the same memo; change one number in one rule and the fingerprint changes. A site's memos are numbered as revisions, R1, R2 and so on, in the order they were issued; a run not yet issued is a draft, named by the time it was made.</p>
    <p class="hash">Fingerprint ${h(st.stamp)} · rules hash (SHA-256 over all rule files) ${h(st.rules_hash)}</p>
    <ul>${files}</ul>
  </section>`;
}
