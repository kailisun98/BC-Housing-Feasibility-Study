/* The paper memo, loaded on first use: a self-contained layout of the memo for a reviewer, used by Download PDF and
   Print. Every rule is referred to as A1…E4. */

import { cap, fmtNum, h, setStatus, STATUS_WORD, todayISO, verdictStatus } from "./core/util.js";
import { state, STATIC } from "./core/state.js";
import { optWord } from "./fields.js";
import { isDraft, rev } from "./runs.js";
import { briefName, compareKind, dateWords, idBreak, issuedWords, memoRefs, optionName, takesRef } from "./memo/memo.js";
import { amountWords, frontOf, routeStatus } from "./memo/front.js";
import { CONTRIBUTION_WORD, outOfTotal, fundedWord, intakeNote, isOutrightLimit, layoutOpenItems, money, MONEY_STATUS, moneyNext, moneyPhrase, moneyWord, moneyWords, operatingRows, outrightWords, unverifiedRules } from "./memo/answers.js";
import { splitValues, withPlans } from "./memo/clauses.js";
import { sidesOf, tradeOff } from "./memo/side-by-side.js";
import { changeWord, naChange } from "./memo/changes.js";
import { stackFigure, stackOf } from "./memo/stack.js";
import { fewWords, lanesHtml } from "./memo/lanes.js";
import { wordsFor } from "./memo/words.js";
import { numberWords, valuesWords } from "./memo/ledger.js";
import { siteContext } from "./figures/common.js";
import { figPlan } from "./figures/plan.js";
import { figSection } from "./figures/section.js";
import { massLine } from "./figures/cards.js";
// the small drawing of outright against proposed that answer 1 carries on screen, on the first page (20 Nov 2026)
import { envelopeFigure } from "./figures/envelope.js";

/* A drawing's labels at a printed size: the font size, in the drawing's metres, that prints `mm` tall when the
   drawing is fitted into a box `boxW` by `boxH` millimetres. The label room in a figure grows with the label size,
   so the width is read back from each pass's viewBox until it settles. */
function paperFit(build, boxW, boxH, mm = 2.3) {
  let fs = null, svg = "";
  for (let pass = 0; pass < 4; pass++) {
    svg = build(fs);
    const vb = (svg.match(/viewBox="([^"]+)"/) || [])[1];
    if (!vb) break;
    const [, , w, hgt] = vb.split(/\s+/).map(Number);
    const scale = Math.min(boxW / w, boxH / hgt);   // mm per metre once fitted
    const next = mm / scale;
    if (fs && Math.abs(next - fs) / fs < 0.02) break;
    fs = next;
  }
  return svg;
}

/* The memo laid out for paper, for whoever reviews it: a title block; the three answers with the rules that decide
   them; the open items and who resolves each; the comparison when there is one; every clause with its numbers; the
   massing; the full ledger with each rule's source; the inputs; the sources with their addresses printed; and how
   to reproduce the memo and check its fingerprint. Every rule is referred to by its layer and place (A1, C4…)
   everywhere, so a reader can follow any answer to its clause and its document. One self-contained HTML document:
   the server prints it to PDF, and Print opens it in the browser's print dialog. */
/* Whose the operating figures are, in a sentence for the paper (24 Nov 2026): signed by the operator, or not yet. */
function signedWords(run) {
  const ops = ((((run.ledger || {}).inputs || {}).option || {}).operations) || {};
  const sg = ops.signed && ops.signed.by ? ops.signed : null;
  return sg ? `Operating figures signed by ${h(sg.by)}${sg.org ? ` of ${h(sg.org)}` : ""}${sg.on ? `, ${h(dateWords(sg.on))}` : ""}. ` : "";
}

/* The area schedule, the program brief and what an operator checks first (24 Nov 2026), for the paper: the same figures
   as the screen's area schedule (memo/operator.js) and the layout's operability list, set as tables that keep together. */
const AREA_SHORT = { homes: "Homes", circulation: "Circulation", core: "Cores", program: "Program", amenity: "Amenity", services: "Services", non_residential: "Non-res.", spare: "Spare" };
const UNIT_ABBR = { three_bed_plus: "3B+", two_bed: "2B", one_bed: "1B", studio: "ST" };
function areasPaper(run) {
  const lay = run.layout || {}, sch = lay.area_schedule, ob = lay.operability;
  const out = [];
  const pct = x => (x == null ? "" : `${Math.round(x * 100)}%`);
  const n = x => Math.round(x).toLocaleString("en-CA");
  if (sch) {
    const used = sch.groups.map(g => g.key).filter(k => sch.totals.m2[k]);
    const homes = r => Object.entries(r.homes || {}).map(([k, c]) => `${c} ${UNIT_ABBR[k] || k}`).join(", ");
    const row = (r, total) => `<tr${total ? ' class="total"' : ""}><td>${h(r.name)}</td><td class="num">${r.homes_total}</td><td>${h(homes(r))}</td>${used.map(k => `<td class="num">${n(r.m2[k])}</td>`).join("")}<td class="num">${n(r.gross_m2)}</td><td class="num">${pct(r.efficiency)}</td></tr>`;
    const tot = { name: "Total", homes_total: sch.totals.homes_total, homes: sch.totals.homes, m2: sch.totals.m2, gross_m2: sch.totals.gross_m2, efficiency: sch.totals.efficiency };
    out.push(`<p class="lead"><b>Area schedule.</b> ${sch.totals.homes_total} homes in ${n(sch.totals.gross_m2)} m² gross, ${pct(sch.totals.efficiency)} of it homes (net to gross)${sch.flag ? `, under the ${pct(sch.efficiency_floor)} this screen flags` : ""}.</p>
      <table class="areas"><thead><tr><th>Floor</th><th class="num">Homes</th><th>By type</th>${used.map(k => `<th class="num">${h(AREA_SHORT[k] || k)} m²</th>`).join("")}<th class="num">Gross m²</th><th class="num">Net to gross</th></tr></thead>
      <tbody>${sch.floors.map(r => row(r, false)).join("")}${row(tot, true)}</tbody></table>
      <p class="note">${h(sch.note)} The same table is area-schedule.csv beside the run.</p>`);
  }
  const brief = (lay.program || []).filter(b => b.brief);
  if (brief.length) {
    out.push(`<p class="lead"><b>What the building runs on.</b> The spaces in the program brief beyond the homes, ${brief.some(b => b.source !== "placeholder") ? "as entered" : "the default for this kind of housing, every figure a placeholder until the operator's brief replaces it"}.</p>
      <table class="brief"><thead><tr><th>Space</th><th class="num">m²</th><th>Where</th></tr></thead><tbody>${brief.map(b => `<tr><td>${h(b.label)}</td><td class="num">${n(b.area_m2)}</td><td>${b.next_to === "entry" ? "beside the entry" : b.where === "upper" ? "upper floors" : "ground floor"}</td></tr>`).join("")}</tbody></table>`);
  }
  if (ob) {
    out.push(`<p class="lead"><b>What an operator checks first, on the plans.</b> ${h(ob.summary)}</p>
      <table class="checks"><thead><tr><th>Item</th><th>Status</th><th>On these plans</th></tr></thead><tbody>${ob.items.map(i => `<tr><td><b>${h(i.label)}</b></td><td><span class="st st-${i.status === "missing" ? "uncertain" : i.status === "pass" ? "pass" : "info"}">${h(i.status)}</span></td><td>${h(i.note)}</td></tr>`).join("")}</tbody></table>
      <p class="note">${signedWords(run) || "The operating figures are not yet signed by an operator. "}The thresholds are this screen's placeholders, not an operator's standard.</p>`);
  }
  return out.join("\n");
}

/* The board memo's own rules over the paper memo's: the decision set large, the page kept to two. */
const BOARD_CSS = `
    body { font-size: 8.1pt; line-height: 1.38; }
    .board-ask .decision { font-size: 12pt; line-height: 1.3; font-weight: 500; margin: 0 0 4pt; }
    .board-ask .decision .muted { font-size: 9pt; font-weight: 400; }
    .sec { break-inside: auto; }
    table.open td, table.open th { padding-top: 2pt; padding-bottom: 2pt; }`;

/* Who issued the memo, to whom and when, under its revision on paper (26 Nov 2026), as the screen's title block says. */
function issuedPaper(run) {
  const list = (run.issues || []).slice().sort((a, b) => String(a.issued_at).localeCompare(String(b.issued_at)));
  if (!list.length) return isDraft(run.run_id) ? `<br><span class="muted">a draft, not issued</span>` : "";
  const first = list[0], last = list[list.length - 1];
  return `<br><span class="muted">${h(cap(issuedWords(first)))}${last !== first ? `; last ${h(issuedWords(last))}` : ""}</span>`;
}

/* `short` (25 Nov 2026, the small-lot architect of the second panel): the front sheet, the answers, the open items, the
   money and the sources of the rules that apply; the clauses, the drawings, the ledger, the inputs and the
   reproduction notes are the full memo's. */
export function paperDocument(run, { short = false, board = false, decision = null } = {}) {
  // the exits as the plans found them, the same on paper as on screen (withPlans)
  const L = run.ledger, res = withPlans(L.results, run), ans = L.summary.answers;
  const site = L.inputs.site || {}, opt = L.inputs.option || {};
  const st = L.run.stamp, d = run.diff, B = d && run.compareLedger ? run.compareLedger : null;
  const kind = d ? compareKind(d) : null;
  const revA = rev(run.run_id), revB = state.compareRun ? rev(state.compareRun) : "an earlier memo";
  const address = site.address || site.id || "";
  // the memo's own date (the day its ledger was written) and the day it was printed, never one for the other (20 Nov
  // 2026: "issued" was the print date, so an old memo's issue date changed every time it was printed)
  const listed = (state.runs || []).find(r => r.run_id === run.run_id) || {};
  const folder = String(run.folder || run.run_id || "").split("/").pop();
  const ranISO = listed.written || (/^\d{4}-\d\d-\d\d/.test(folder) ? folder.slice(0, 10) : null);
  const ran = ranISO ? dateWords(ranISO) : null;
  const printed = dateWords(todayISO());
  const asOf = dateWords(L.run.as_of);

  // references: the layer's letter and the rule's place among the rules that apply here, as the screen counts them
  const refOf = memoRefs(res), titleOf = {}, checkOf = {};
  for (const r of res) { titleOf[r.rule_id] = r.title; checkOf[r.rule_id] = r.check; }
  // the rules in the stack written for other districts (or not in force on the date): counted once, never listed
  const elsewhere = res.filter(r => !takesRef(r));
  const elsewhereLine = elsewhere.length ? `${elsewhere.length} more rule${elsewhere.length === 1 ? "" : "s"} in the stack ${elsewhere.length === 1 ? "is" : "are"} written for other districts or not in force on ${asOf}, and take no reference here.` : "";
  const ref = id => refOf[id] || id;
  const refTag = id => `<b class="ref">${h(ref(id))}</b>`;
  // an item with no rule of its own (the coverage notes, the plans) has no reference: a dash, never its id
  const refCell = id => (refOf[id] ? refTag(id) : `<span class="muted">—</span>`);
  // an open item by name: its reference where it has one, then a few words of its title
  const itemName = u => `${refOf[u.rule_id] ? `${refOf[u.rule_id]} ` : ""}${fewWords(u.title)}`;
  // sources, numbered in the order the rules cite them, then the site's and the option's own
  const srcNo = new Map(), sources = [];
  const addSrc = s => {
    if (!s || (!s.title && !s.url)) return null;
    const k = `${s.title || ""}|${s.url || ""}`;
    if (!srcNo.has(k)) { srcNo.set(k, sources.length + 1); sources.push({ ...s, cites: [] }); }
    return srcNo.get(k);
  };
  // the sources of the rules that apply here; another district's schedule is not this memo's source
  for (const r of res) { if (!takesRef(r)) continue; const k = addSrc(r.source); if (k) sources[k - 1].cites.push(r.rule_id); }
  for (const s of (site.sources || []).concat(opt.sources || [])) addSrc(s);

  const mark = s => `<span class="st st-${h(s || "na")}">${h(STATUS_WORD[s] || cap(s) || "—")}</span>`;
  const vmark = w => `<span class="st st-${h(verdictStatus(w) || "na")}">${h(cap(w || "—"))}</span>`;
  const approvedRz = ans.allowed.by_rezoning.verdict === "approved";     // a rezoning Council approved (25 Nov 2026)
  // each rule that decides an answer, with its status; an option over the district's own FSR or height reads "not
  // allowed outright: rezoning required" (20 Nov 2026: the engine reads that as fail now)
  const decidedBy = (o, outright = false) => {
    const items = ["fail", "conditional", "uncertain"].flatMap(k => (o[k] || []).map(id => {
      // the use table is not a limit to exceed (25 Nov 2026: a shelter's use read "over the outright limit: rezoning required")
      const use = checkOf[id] === "district_outright_use";
      const why = use ? (k === "fail" ? "not a use the district allows: a rezoning" : k === "conditional" ? "a conditional approval use, the Director's discretion" : "which use it is: a question for the City")
        : outright && isOutrightLimit({ check: checkOf[id] }) && k !== "conditional" ? (approvedRz ? "over the outright limit: the approved rezoning sets it" : "over the outright limit: rezoning required") : (STATUS_WORD[k] || k).toLowerCase();
      return `<li>${refTag(id)} ${h(titleOf[id] || id)} <span class="muted">(${h(why)})</span></li>`;
    }));
    // a verdict nothing was tested for says why, never that nothing stands in the way (25 Nov 2026); an approved
    // rezoning says who approved it and when
    if (!items.length && o.verdict === "approved") return `<span class="muted">${h(cap(o.why || "approved"))}.</span>`;
    if (!items.length && o.verdict === "not assessed") return `<span class="muted">Not assessed: ${h(o.why || "the rules hold nothing to test here")}.</span>`;
    // the board memo names three, the full memo every one (26 Nov 2026: the board memo keeps to two pages)
    const shown = board && items.length > 3 ? [...items.slice(0, 3), `<li class="muted">and ${items.length - 3} more, in the full memo</li>`] : items;
    return items.length ? `<ul class="refs">${shown.join("")}</ul>` : `<span class="muted">No rule stands in the way.</span>`;
  };
  const unsure = [...(ans.unsure || []), ...layoutOpenItems(run).map(u => ({ ...u, rule_id: u.rule_id || "layout", finding: "" }))];   // the drawings' open items join the rules'
  // the outright answer in the words the screen uses
  const outLines = res.filter(r => isOutrightLimit(r) && r.status !== "not_applicable");
  const routes = ans.allowed.routes || null;
  const outWords = (approvedRz ? "Not outright: the rezoning Council approved sets the limits, below"
    : routes && routes.discretion.verdict === "possible" ? "Not outright: within what the Director of Planning may allow, below"
    : outrightWords(ans.allowed.outright, outLines)).replace(/\.$/, "");
  const rmark = w => `<span class="st st-${h(routeStatus(w) || "na")}">${h(cap(w || "—"))}</span>`;
  // on paper the outright row says the district's limits as written, so the Director's discretion is never read as outright
  const outV = routes ? routes.outright.verdict : ans.allowed.outright.verdict;
  const outMark = `<span class="st st-${h((routes ? routeStatus(outV) : verdictStatus(outV)) || "na")}">${h(outWords.split(":")[0])}</span>${outWords.includes(":") ? `<div class="note">${h(outWords.split(":").slice(1).join(":").trim())}</div>` : ""}`;
  const f = ans.funded, intake = intakeNote(f);
  const fundMark = `<span class="st st-${h(verdictStatus(f.verdict) || "na")}">${h(fundedWord(f))}</span>`;
  const fmtVal = x => (x === null || x === undefined ? "—" : typeof x === "boolean" ? (x ? "yes" : "no")
    : typeof x === "object" ? JSON.stringify(x).replace(/[{}"]/g, "").replace(/,/g, ", ").replace(/:/g, ": ")
    : typeof x === "string" && /^[a-z0-9]+(_[a-z0-9]+)+$/.test(x) ? x.replace(/_/g, " ") : fmtNum(x));
  const human = k => k.replace(/_m2$/, " (m²)").replace(/_m$/, " (m)").replace(/_cad$/, " ($)").replace(/_/g, " ");
  // the sections after the comparison are numbered on from it; massing only when there is one. Numbered here, before
  // the answers table names the money's section (16 Nov 2026: declared below it, `s` threw for every run with money)
  const sn = (k => () => ++k)(d ? 3 : 2);
  const pfOk = !!(run.proforma && run.proforma.available);
  const terms = wordsFor(run);
  const lay = run.layout || {};
  const s = { money: pfOk ? sn() : null, clauses: short ? null : sn(), massing: !short && (run.massing || run.massing_note) ? sn() : null,
              areas: !short && (lay.area_schedule || lay.operability) ? sn() : null,
              words: terms.length ? sn() : null, ledger: short ? null : sn(), inputs: short ? null : sn(), sources: sn(), verify: short ? null : sn() };
  const ledgerAt = s.ledger ? `section ${s.ledger}` : "the full memo";

  // 1. the three answers
  const answers = `<table class="answers">
      <colgroup><col style="width:24%"><col style="width:20%"><col></colgroup>
      <thead><tr><th>Question</th><th>Answer</th><th>Decided by</th></tr></thead>
      <tbody>
        <tr><th scope="row">Is it allowed outright?</th><td>${outMark}</td><td>${decidedBy(ans.allowed.outright, true)}</td></tr>
        ${routes ? `<tr><th scope="row">By the Director's discretion?</th><td>${rmark(routes.discretion.verdict)}</td><td>${routes.discretion.rules.length ? `<ul class="refs">${routes.discretion.rules.map(id => `<li>${refTag(id)} ${h(titleOf[id] || id)} <span class="muted">(a discretionary approval, never assumed)</span></li>`).join("")}</ul>` : `<span class="muted">${h(cap(routes.discretion.why || ""))}.</span>`}</td></tr>` : ""}
        <tr><th scope="row">Is it allowed by rezoning?</th><td>${vmark(ans.allowed.by_rezoning.verdict)}</td><td>${decidedBy(ans.allowed.by_rezoning)}${ans.allowed.rezoning_path ? `<p class="note">Path: ${h(ans.allowed.rezoning_path)}.</p>` : ""}</td></tr>
        <tr><th scope="row">Does it fit the funders?</th><td>${fundMark}</td><td>${intake ? `<p class="note intake">${h(intake)}</p>` : ""}${decidedBy(ans.funded)}${pfOk ? `<p class="note">The criteria are not the money: ${h(moneyPhrase(run.proforma))} (below).</p>` : ""}</td></tr>
        ${board ? "" : `<tr><th scope="row">What is still unsure?</th><td>${unsure.length ? `<span class="st st-${unsure.some(u => u.status === "fail") ? "fail" : "uncertain"}">${unsure.length} open item${unsure.length === 1 ? "" : "s"}</span>` : `<span class="st st-pass">Nothing open</span>`}</td><td>${unsure.length ? `Each with the person who resolves it, in section 2: ${h(unsure.map(itemName).join("; "))}.` : `<span class="muted">Every rule that applies is settled.</span>`}</td></tr>`}
        ${run.proforma && run.proforma.available ? `<tr><th scope="row">Does the money work? <span class="muted">(feasibility grade)</span></th><td><span class="st st-${MONEY_STATUS[run.proforma.verdict.word] || "uncertain"}">${h(moneyWord(run.proforma.verdict))}</span></td><td>Capital cost ${h(money(run.proforma.capital.total))}; funding ${h(money(run.proforma.funding.total))}; gap ${h(money(run.proforma.gap.value))}${run.proforma.gap.share_of_capital != null ? ` (${h(Math.round(run.proforma.gap.share_of_capital * 100))}% of the cost, against this tool's 15% screening line)` : ""}. ${h((run.proforma.verdict.why || []).slice(run.proforma.gap.share_of_capital != null ? 1 : 0, run.proforma.gap.share_of_capital != null ? 1 : 2).map(w => w[0].toUpperCase() + w.slice(1) + ".").join(" "))} Drawn below; every line and its source in ${board ? "the full memo" : `section ${s.money}`}.${moneyNext(run.proforma) ? `<p class="note">For the development manager: ${h(moneyNext(run.proforma))}</p>` : ""}</td></tr>` : ""}
      </tbody></table>`;

  // 2. open items
  // who resolves what, drawn as on screen (a lane per person; site facts, then design, then funders), then the table
  const open = unsure.length ? `${lanesHtml(unsure, id => refOf[id] || "")}<table class="open">
      <colgroup><col style="width:5%"><col style="width:27%"><col style="width:13%"><col></colgroup>
      <thead><tr><th>Ref</th><th>Item</th><th>Status</th><th>Who resolves it, and what to do</th></tr></thead>
      <tbody>${unsure.map(u => `<tr><td>${refCell(u.rule_id)}</td><td><b>${h(u.title)}</b><div class="muted">${h(u.finding || "")}</div></td><td>${mark(u.status)}</td><td>${h(u.action || "—")}</td></tr>`).join("")}</tbody></table>`
    : `<p>Nothing is open: every rule that applies is settled for this option.</p>`;

  // 3. the comparison, when there is one
  let compare = "";
  if (d) {
    // the rules that apply to neither memo are counted, not listed (17 Nov 2026), as the screen folds them
    const naCount = (d.changes || []).filter(naChange).length;
    const changes = (d.changes || []).filter(c => !naChange(c)).sort((a, b) => String(ref(a.rule_id)).localeCompare(String(ref(b.rule_id)), "en", { numeric: true }));
    const naNote = naCount ? `<p class="note">${naCount} more rule${naCount === 1 ? "" : "s"} changed that ${naCount === 1 ? "applies" : "apply"} to neither memo, for other districts, policies or programs; the ledger in section ${s.ledger} lists every rule.</p>` : "";
    // the earlier revision on the left, the later on the right, as on screen; the funders' criteria beside the money
    const sides = B ? sidesOf(run) : null;
    const fundCell = Lx => { const fx = Lx.summary.answers.funded, nx = intakeNote(fx); return `<span class="st st-${h(verdictStatus(fx.verdict) || "na")}">${h(fundedWord(fx))}</span>${nx ? `<div class="note">${h(nx)}</div>` : ""}`; };
    const moneyCell = p => (p ? `<span class="st st-${h(MONEY_STATUS[p.verdict.word] || "uncertain")}">${h(moneyWord(p.verdict))}</span><div class="note">${h(moneyPhrase(p).replace(/^[^:]*:\s*/, ""))}</div>` : `<span class="muted">not computed</span>`);
    const head = sides ? `<table class="ab">
        <colgroup><col style="width:30%"><col style="width:35%"><col></colgroup>
        <thead><tr><th>Answer</th><th>${h(sides.left.label)}${sides.left.isThis ? " · this memo" : ""}</th><th>${h(sides.right.label)}${sides.right.isThis ? " · this memo" : ""}</th></tr></thead>
        <tbody>
          <tr><th scope="row">Allowed outright</th><td>${vmark(sides.left.L.summary.answers.allowed.outright.verdict)}</td><td>${vmark(sides.right.L.summary.answers.allowed.outright.verdict)}</td></tr>
          <tr><th scope="row">Allowed by rezoning</th><td>${vmark(sides.left.L.summary.answers.allowed.by_rezoning.verdict)}</td><td>${vmark(sides.right.L.summary.answers.allowed.by_rezoning.verdict)}</td></tr>
          <tr><th scope="row">Funders' criteria</th><td>${fundCell(sides.left.L)}</td><td>${fundCell(sides.right.L)}</td></tr>
          ${sides.left.pf || sides.right.pf ? `<tr><th scope="row">The money</th><td>${moneyCell(sides.left.pf)}</td><td>${moneyCell(sides.right.pf)}</td></tr>` : ""}
          <tr><th scope="row">Open items</th><td>${(sides.left.L.summary.answers.unsure || []).length}</td><td>${(sides.right.L.summary.answers.unsure || []).length}</td></tr>
        </tbody></table>
        ${kind !== "rules" && sides.left.pf && sides.right.pf ? stackFigure([stackOf(sides.left.pf, sides.left.label), stackOf(sides.right.pf, sides.right.label)], { unit: "mm", H: 40, lh: 3.3, names: true, cls: "pair" }, "The two capital stacks at one scale: what each costs against what pays for it; the hatched part is the gap, not yet found; the amber line is 15% of the cost below the top.") : ""}` : "";
    const trade = sides && kind !== "rules" ? tradeOff(sides.right.L, sides.left.L) : "";
    const lead = kind === "rules"
      ? `The same site and option read under the rules as of ${h(asOf)} (${h(revA)}) against ${h(dateWords(d.previous_as_of))} (${h(revB)}). ${h(String(d.cause || "").replace(/\d{4}-\d\d-\d\d/g, x => dateWords(x)))}`
      : `${sides ? `${h(sides.right.label)} against ${h(sides.left.label)}` : `${h(revA)} against ${h(revB)}`}${trade ? `: ${h(trade)}` : ""}. Both read the rules as of ${h(asOf)}.`;
    compare = `<section class="sec" id="p-compare"><h2><span class="no">3</span> Compared with ${h(revB)}</h2>
      <p class="lead">${lead}</p>${head}
      ${changes.length ? `<h3>What changed, rule by rule</h3><table class="changes">
        <colgroup><col style="width:5%"><col style="width:27%"><col style="width:13%"><col style="width:24%"><col></colgroup>
        <thead><tr><th>Ref</th><th>Rule</th><th>What changed</th><th>Status, ${h(revB)} → ${h(revA)}</th><th>Now reads</th></tr></thead>
        <tbody>${changes.map(c => `<tr><td>${refCell(c.rule_id)}</td><td>${h(titleOf[c.rule_id] || c.rule_id)}${c.from_version && c.to_version && c.from_version !== c.to_version ? `<div class="mono muted">v ${h(c.from_version)} → ${h(c.to_version)}</div>` : ""}</td><td>${h(changeWord(c, kind))}</td><td class="trans">${c.from === c.to ? `${mark(c.to)} <span class="muted">same</span>` : `${c.from ? mark(c.from) : "—"} → ${c.to ? mark(c.to) : "—"}`}</td><td>${h(c.finding || "")}</td></tr>`).join("")}</tbody></table>${naNote}`
        : naCount ? `<p>No rule that applies to either memo changed its version or status.</p>${naNote}` : `<p>No rule changed its version or status between the two memos.</p>`}
    </section>`;
  }
  // the money, line by line, on paper: the board and the funder's officer read the gap here and nowhere else (15 Nov 2026);
  // first, land at $0, the 15% line and the 1.10 coverage in plain words (20 Nov 2026)
  // what it takes to run, a year (23 Nov 2026): the operating page on paper, as answer 4 shows it on screen; the funder's
  // officer reads the subsidy a home a month here. Rows from memo/answers.js operatingRows, the twin of proforma.operating_rows.
  const opRows = pfOk ? operatingRows(run.proforma) : [];
  // where the money comes from, each source with its status (25 Nov 2026), as answer 4 shows it
  const srcRows = pfOk ? ((run.proforma.funding || {}).sources || []) : [];
  const srcPaper = srcRows.length ? `<p class="lead op-head"><b>Where the money comes from.</b> Each source with its status; a stack that closes only with sources not yet committed reads Unsure.</p>
      <table class="money op"><colgroup><col style="width:44%"><col style="width:18%"><col></colgroup>
      <thead><tr><th>Source</th><th>Amount</th><th>Status</th></tr></thead><tbody>
      ${srcRows.map(r => `<tr><td>${r.counted ? `<b>${h(r.label)}</b>` : h(r.label)}</td><td class="num">${h(money(r.value))}</td><td>${h(CONTRIBUTION_WORD[r.status] || r.status)}${outOfTotal(r) ? ' <span class="muted">· not in the funding total</span>' : ""}</td></tr>`).join("")}
      </tbody></table>` : "";
  const opMoney = x => (x < 0 ? `−${money(-x)}` : money(x));
  const opTable = opRows.length ? `<p class="lead op-head"><b>What it takes to run, a year.</b> The rents, the running costs, what is left, and the subsidy needed.</p>
      <table class="money op"><colgroup><col style="width:34%"><col style="width:16%"><col></colgroup>
      <thead><tr><th>Line</th><th>A year</th><th>Note</th></tr></thead><tbody>
      ${opRows.map(r => { const strong = r.kind === "result" || r.kind === "ask"; const lab = strong ? `<b>${h(r.label)}</b>` : h(r.label);
        return `<tr><td>${lab}${r.ph ? ' <span class="st st-uncertain">placeholder</span>' : ""}${r.warn ? ' <span class="st st-uncertain">open</span>' : ""}</td><td class="num">${r.value == null ? (r.warn ? "not entered" : "none") : (strong ? `<b>${h(opMoney(r.value))}</b>` : h(opMoney(r.value)))}</td><td>${h(r.note || "")}</td></tr>`; }).join("")}
      </tbody></table>
      <p class="note">${signedWords(run)}${((run.proforma.operating || {}).page || {}).own_figures ? "The rents and the running cost are the operator's own, as entered" : "The rents and the running cost are placeholders until the operator's own are entered"}; support staffing and an operating subsidy are never assumed. The last line is an illustration on this screen's mortgage terms, not a funder's financing.</p>` : "";
  const moneyLines = pfOk ? `${moneyWords(run.proforma, run, "text") ? `<p class="lead">${h(moneyWords(run.proforma, run, "text"))}</p>` : ""}<table class="money"><colgroup><col style="width:6%"><col style="width:22%"><col style="width:16%"><col></colgroup>
      <thead><tr><th>Ref</th><th>Line</th><th>Figure</th><th>How, and from what</th></tr></thead><tbody>
      ${run.proforma.lines.map(ln => { const shown = ln.unit === "×" ? (ln.value == null ? "not given" : `×${ln.value}`) : ln.unit && ln.unit.startsWith("$") ? money(ln.value) + (ln.unit === "$/yr" ? " a year" : ln.unit === "$/m²" ? " per m²" : "") : (ln.value == null ? "not given" : fmtNum(ln.value));
        return `<tr><td>${ln.rule_id ? refTag(ln.rule_id) : '<span class="muted">option</span>'}</td><td><b>${h(ln.label)}</b>${ln.placeholder ? ' <span class="st st-uncertain">placeholder</span>' : ""}</td><td class="num">${h(shown)}</td><td>${h(ln.note || "")}${ln.rule_id ? ` <span class="muted">(${h(ref(ln.rule_id))}: ${h(titleOf[ln.rule_id] || ln.rule_id)})</span>` : ""}</td></tr>`; }).join("")}
      </tbody></table>
      <p class="note">Capital cost ${h(money(run.proforma.capital.total))}, less funding ${h(money(run.proforma.funding.total))}, gives the gap ${h(money(run.proforma.gap.value))}${run.proforma.gap.share_of_capital != null ? ` (${h(Math.round(run.proforma.gap.share_of_capital * 100))}% of the capital cost)` : ""}. ${h(run.proforma.verdict.why.map(w => w[0].toUpperCase() + w.slice(1) + ".").join(" "))} A feasibility screen, not a lender's model: hard costs from a Class D catalogue estimate escalated by the Statistics Canada index; rents from the CMHC survey; debt at the posted five-year rate under CMHC's coverage ratio. Placeholders are marked; each rule's source is in ${ledgerAt}.</p>${srcPaper}${opTable}` : "";

  // 4. every clause that applies, in reference order
  const applied = res.filter(r => r.status !== "not_applicable");
  const na = res.filter(r => r.status === "not_applicable" && takesRef(r));
  const clauses = `<table class="clauses">
      <colgroup><col style="width:5%"><col style="width:24%"><col style="width:11%"><col style="width:19%"><col style="width:20%"><col></colgroup>
      <thead><tr><th>Ref</th><th>Clause and version</th><th>Status</th><th>Proposed</th><th>Permitted or required</th><th>The ask</th></tr></thead>
      <tbody>${applied.map(r => { const s = splitValues(r, L); return `<tr><td>${refTag(r.rule_id)}</td><td><b>${h(r.title)}</b><div class="mono muted">${idBreak(r.rule_id)} · v ${h(r.version_effective_from || "—")}</div></td><td>${mark(r.status)}</td>${s.info !== undefined ? `<td colspan="3">${h(s.info || "no figures")}</td>` : `<td>${h(s.proposed || "—")}</td><td>${h(s.permitted || "—")}</td><td>${s.ask ? h(s.ask) : `<span class="muted">—</span>`}</td>`}</tr>`; }).join("")}</tbody></table>
    ${na.length ? `<p class="note">Not applicable here: ${na.map(r => `${refTag(r.rule_id)} ${h(r.title)}`).join("; ")}.</p>` : ""}
    ${elsewhereLine ? `<p class="note">${h(elsewhereLine)}</p>` : ""}`;

  // 5. the massing, drawn from the same numbers
  let figures = "";
  const m = run.massing;
  if (m) {
    const ctx = siteContext(site, m);
    // on paper the street names sit on the light road tone without the screen's white halo, which PDF renderers
    // can paint over the letters
    const plan = paperFit(fs => figPlan(m, ctx, fs), 183, 112).replace(/ paint-order="stroke" stroke="#ffffff" stroke-linejoin="round" stroke-width="[\d.]+"/g, "");
    const section = paperFit(fs => figSection(m, fs), 183, 52);
    const sb = m.envelope.setbacks_m || {}, bench = m.policy_benchmark, trees = m.trees;
    figures = `<figure class="fig"><div class="draw plan">${plan}</div>
        <figcaption><b>Figure 1 · Plan.</b> Lot ${h(m.lot.frontage_m)} × ${h(m.lot.depth_m)} m, ${fmtNum(m.lot.area_m2)} m². Setback envelope ${h(m.envelope.width_m)} × ${h(m.envelope.depth_m)} m (front ${h(sb.front)}, rear ${h(sb.rear)}, sides ${h(sb.side)} m). The outright mass is dashed over the proposed one. ${ctx.osm ? `Context in half tone from OpenStreetMap (${h(ctx.osm.attribution)}).` : "Context in half tone, schematic."}</figcaption></figure>
      <figure class="fig"><div class="draw section">${section}</div>
        <figcaption><b>Figure 2 · Section across the frontage.</b> ${m.masses.map(massLine).join(" ")}${bench && bench.height_m ? ` Staff benchmark under ${refTag(bench.rule_id)}: ${h(bench.height_m[0])} to ${h(bench.height_m[1])} m, about FSR ${h(bench.fsr)}.` : ""}${trees ? ` Trees: Schedule C requires ${h(trees.required)}, the plan leaves ${h(trees.after)} (shortfall ${h(trees.shortfall)}).` : ""}</figcaption></figure>
      ${(m.warnings || []).map(w => `<p class="note">${h(String(w).replace(/(\d) x (\d)/g, "$1 × $2"))}</p>`).join("")}`;
  } else if (run.massing_note) {
    figures = `<p class="note">${h(run.massing_note)}</p>`;
  }
  // the architect's sheets follow the massing figures: plans by program, stacking, elevations, the code site plan
  if (run.layout && run.sheets) {
    const Lay = run.layout, S = run.sheets;
    const rules = (Lay.adjacencies || []).filter(c => c.status !== "info").map(c => `${c.block.replace(/_/g, " ")}: ${c.rule} (${c.status}${c.note ? `, ${c.note}` : ""})`).join("; ");
    const short = (Lay.shortfall || []).length ? ` Did not fit: ${Lay.shortfall.map(s => `${s.units ? `${s.units} ` : ""}${s.label.toLowerCase()} (${fmtNum(Math.round(s.area_m2))} m²)`).join("; ")}.` : "";
    figures += `
      <figure class="fig"><div class="draw sheet">${S.plans || ""}</div>
        <figcaption>${(run.issues || []).some(i => i.to === "manager") ? "" : `<b class="unv">FIRST LAYOUT FROM THE RULES · NOT YET CHECKED BY THE ARCHITECT</b> `}<b>Figure 3 · Plans by program.</b> ${h(Lay.units_placed)} of ${h(Lay.units_total)} units on ${h(Lay.floors.length)} floors of ${h(Lay.plate.width_m)} × ${h(Lay.plate.depth_m)} m. Adjacency rules read back from the plates: ${h(rules)}.${h(short)}</figcaption></figure>
      <figure class="fig"><div class="draw sheet">${S.stacking || ""}</div><figcaption><b>Figure 4 · Stacking.</b> One bar per floor, top first; each segment the share of the plate a block takes.</figcaption></figure>
      <figure class="fig"><div class="draw sheet">${S.elevations || ""}</div><figcaption><b>Figure 5 · Preliminary elevations.</b> Storeys × floor to floor, one window per unit as the rhythm, the outright height dashed. A placeholder for the elevation study, not a design.</figcaption></figure>
      <figure class="fig"><div class="draw sheet">${S["site-plan"] || ""}</div><figcaption><b>Figure 6 · Code site plan.</b> The yards dimensioned, the setback envelope, the footprint, the tree barriers where surveyed, and the table a plan checker reads.</figcaption></figure>`;
  }

  // 6. the full ledger, layer by layer, each rule with its numbers and its source
  const layers = [];
  for (const r of res) { if (!takesRef(r)) continue; let g = layers.find(x => x.layer === r.layer); if (!g) layers.push(g = { layer: r.layer, title: r.layer_title, rows: [] }); g.rows.push(r); }
  // a share prints as a percentage, as everywhere else in the memo (20 Nov 2026: "share below hils 0.3")
  const shareVal = (k, x) => {
    if (typeof x === "number" && /(^|_)shares?(_|$)/.test(k) && x >= 0 && x <= 1) return numberWords(k, x).split(": ").slice(1).join(": ");
    if (x && typeof x === "object" && !Array.isArray(x) && /share|mix/.test(k)) return valuesWords({ [k]: x }).split(": ").slice(1).join(": ") || fmtVal(x);
    return fmtVal(x);
  };
  const numbers = v => Object.entries(v || {}).filter(([, x]) => x !== null && x !== undefined && x !== "")
    .map(([k, x]) => `<div><span class="k">${h(human(k))}</span> ${h(shareVal(k, x))}</div>`).join("") || `<span class="muted">—</span>`;
  const ledger = layers.map(g => `<h3>Layer ${h(g.layer)} · ${h(g.title)}</h3>
      <table class="ledger">
        <colgroup><col style="width:5%"><col style="width:21%"><col style="width:14%"><col style="width:28%"><col style="width:18%"><col></colgroup>
        <thead><tr><th>Ref</th><th>Rule and version</th><th>Status</th><th>Finding</th><th>Numbers used</th><th>Source</th></tr></thead>
        <tbody>${g.rows.map(r => { const k = srcNo.get(`${(r.source || {}).title || ""}|${(r.source || {}).url || ""}`); return `<tr><td>${refTag(r.rule_id)}</td><td><b>${h(r.title)}</b><div class="mono muted">${idBreak(r.rule_id)}</div><div class="muted">in force from ${h(r.version_effective_from || "—")}${r.version_effective_to ? ` to ${h(r.version_effective_to)}` : ""}</div></td><td>${mark(r.status)}</td><td>${h(r.finding || "")}${r.action ? `<div class="action">${h(r.action)}</div>` : ""}</td><td class="nums">${numbers(r.values)}</td><td>${k ? `<b class="ref">S${k}</b> ` : ""}${h((r.source && r.source.section) || "")}</td></tr>`; }).join("")}</tbody></table>`).join("")
    + (elsewhereLine ? `<p class="note">${h(elsewhereLine)}</p>` : "");

  // 7. the inputs the memo read
  const describe = x => {
    if (Array.isArray(x)) return x.length ? `${x.length}: ${x.map(t => (t && typeof t === "object") ? [t.id, t.species, t.dbh_cm != null ? `${t.dbh_cm} cm` : null, t.status].filter(Boolean).join(" ") || JSON.stringify(t) : fmtVal(t)).join("; ")}` : "none";
    if (x && typeof x === "object") return Object.entries(x).filter(([, y]) => y !== null && y !== undefined).map(([k, y]) => `${k.replace(/_/g, " ")} ${fmtVal(y)}`).join(", ") || "—";
    return fmtVal(x);
  };
  const inputTable = (obj, skip) => `<table class="kv"><tbody>${Object.entries(obj)
    .filter(([k, x]) => !skip.includes(k) && x !== null && x !== undefined && x !== "")
    .map(([k, x]) => `<tr><th scope="row">${h(human(k))}</th><td>${h(describe(x))}</td></tr>`).join("")}</tbody></table>`;
  const inputs = `<h3>Site · <span class="mono">${h(site.id || "")}</span></h3>${inputTable(site, ["osm", "sources", "context", "notes", "id"])}
    <h3>Option · <span class="mono">${h(opt.id || "")}</span></h3>${inputTable(opt, ["sources", "notes", "id"])}
    ${site.notes ? `<p class="note"><b>Site notes.</b> ${h(site.notes)}</p>` : ""}
    ${opt.notes ? `<p class="note"><b>Option notes.</b> ${h(opt.notes)}</p>` : ""}`;

  // 8. sources, with their addresses printed for paper
  const srcList = `<ol class="sources">${sources.map((s, i) => `<li><b class="ref">S${i + 1}</b> <span>${h(s.title || s.url)}${s.section ? `<span class="muted">, ${h(s.section)}</span>` : ""}${s.cites.length ? ` <span class="muted">· cited by ${s.cites.map(ref).join(", ")}</span>` : ""}${s.url ? `<br><a class="mono url" href="${h(s.url)}">${h(s.url)}</a>` : ""}${s.verify ? `<br><span class="muted">Verify: ${h(s.verify)}</span>` : ""}</span></li>`).join("")}</ol>`;

  // 9. how to reproduce it and check the fingerprint
  const cmd = `python -m ffm run --site sites/${L.run.site_id}.json --option options/${L.run.option_id}.json --as-of ${L.run.as_of} --out outputs/${run.run_id}${state.compareRun && d ? ` --previous outputs/${state.compareRun}/ledger.json` : ""}`;
  const files = Object.entries(st.rules_files || {}).map(([f, hsh]) => `<tr><td class="mono">${h(f)}</td><td class="mono">${h(hsh)}</td></tr>`).join("");
  // the versions the fingerprint is built from, in reference order
  const versions = (Array.isArray(st.rule_versions) ? st.rule_versions : [])
    // the numbered rules first, in reference order; the stack's others (they still make the fingerprint) after, by id
    .slice().sort((a, b) => (refOf[a.rule_id] ? 0 : 1) - (refOf[b.rule_id] ? 0 : 1) || String(ref(a.rule_id)).localeCompare(String(ref(b.rule_id)), "en", { numeric: true }))
    .map(v => `<tr><td>${refCell(v.rule_id)}</td><td class="mono">${idBreak(v.rule_id)}</td><td>${h(v.version_effective_from || "—")}${v.version_effective_to ? ` to ${h(v.version_effective_to)}` : ""}</td></tr>`).join("");
  const verify = `<p>The memo is deterministic: the same inputs read under the same rules always give the same memo. To check it, run the engine on the same files and compare the fingerprint, which is a hash of the rule files and the rule versions in force on the as-of date.</p>
    <pre class="cmd">${h(cmd)}</pre>
    <table class="kv"><tbody>
      <tr><th scope="row">Fingerprint</th><td class="mono">${h(st.stamp)}</td></tr>
      <tr><th scope="row">Rules hash</th><td class="mono">${h(st.rules_hash)}</td></tr>
      <tr><th scope="row">Rules as of</th><td>${h(asOf)} <span class="mono muted">(--as-of ${h(L.run.as_of)})</span></td></tr>
      <tr><th scope="row">Engine</th><td>${h(L.run.engine_version)}</td></tr>
      <tr><th scope="row">Run folder</th><td class="mono">outputs/${h(run.run_id)}</td></tr>
    </tbody></table>
    <h3>Rule files</h3><table class="files"><colgroup><col style="width:30%"><col></colgroup><thead><tr><th>File</th><th>SHA-256</th></tr></thead><tbody>${files}</tbody></table>
    ${versions ? `<h3>Rule versions in force on ${h(asOf)}</h3><table class="versions"><colgroup><col style="width:6%"><col style="width:52%"><col></colgroup><thead><tr><th>Ref</th><th>Rule</th><th>Version in force</th></tr></thead><tbody>${versions}</tbody></table>` : ""}
    <p class="note">To check one finding: find its reference in section ${s.ledger} (the ledger), open its source in section ${s.sources} at the cited section, and compare the permitted figure; the proposed figure comes from the inputs in section ${s.inputs}.</p>`;

  // the running header and footer, and the document
  const safe = s => String(s).replace(/["\\\n]/g, " ");
  const css = `
    @page { size: letter; margin: 20mm 16mm 18mm;
      @top-left { content: "${safe(`First Read memo · ${address}`)}"; font: 500 7pt "IBM Plex Sans", Arial, sans-serif; color: #5f6672; }
      @top-right { content: "${safe(`${revA} · rules as of ${asOf}`)}"; font: 600 7pt "IBM Plex Sans", Arial, sans-serif; color: #2c3e50; }
      @bottom-left { content: "${safe(`Fingerprint ${st.stamp} · ${ran ? `run ${ran} · ` : ""}printed ${printed} · a feasibility screen, not legal, planning or funding advice`)}"; font: 400 6.5pt "IBM Plex Sans", Arial, sans-serif; color: #5f6672; }
      @bottom-right { content: "Page " counter(page) " of " counter(pages); font: 600 7pt "IBM Plex Sans", Arial, sans-serif; color: #2c3e50; } }
    @page :first { @top-left { content: none; } @top-right { content: none; } }
    * { box-sizing: border-box; }
    html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    body { margin: 0; font: 8.6pt/1.42 "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif; color: #1f2933; font-variant-numeric: tabular-nums; }
    .mono, code, pre { font-family: "IBM Plex Mono", Consolas, Menlo, monospace; }
    .muted { color: #5f6672; }
    .nowrap { white-space: nowrap; }
    a { color: #1f4f8a; text-decoration: none; }
    h1 { font-size: 17pt; line-height: 1.2; margin: 0 0 2pt; letter-spacing: -0.01em; }
    .sub { margin: 0 0 8pt; color: #5f6672; font-size: 8.4pt; }
    /* the title block: ruled cells under a heavy rule, as a drawing's */
    .tb { display: grid; grid-template-columns: 2fr 1fr 1fr 1.3fr; border-top: 1.6pt solid #1f2933; border-bottom: 0.6pt solid #1f2933; margin: 0 0 6pt; }
    .tb > div { padding: 4pt 6pt 5pt 0; border-bottom: 0.4pt solid #c9d1da; }
    .tb > div + div { padding-left: 6pt; border-left: 0.4pt solid #c9d1da; }
    .tb > div:nth-child(5) { border-left: 0; padding-left: 0; }
    .tb b { display: block; font-size: 6.4pt; letter-spacing: .07em; text-transform: uppercase; color: #5f6672; font-weight: 600; margin-bottom: 1pt; }
    .tb .big { font-size: 13pt; font-weight: 600; color: #1f2933; }
    .howto { font-size: 7.8pt; color: #3d4752; margin: 0 0 4pt; }
    /* sections */
    .sec { margin-top: 12pt; }
    h2 { font-size: 11pt; margin: 0 0 5pt; padding-top: 5pt; border-top: 1.2pt solid #1f2933; break-after: avoid; display: flex; gap: 8pt; align-items: baseline; }
    h2 .no { font-size: 9pt; color: #5f6672; min-width: 12pt; }
    h3 { font-size: 8.8pt; margin: 9pt 0 3pt; break-after: avoid; }
    p { margin: 0 0 5pt; }
    .lead { font-size: 9pt; }
    .op-head { margin-top: 10pt; break-after: avoid; }
    table.op { break-inside: avoid; }
    table.areas td.num, table.areas th.num { text-align: right; font-variant-numeric: tabular-nums; }
    table.areas tr.total td, table.areas tr.total th { font-weight: 600; border-top: 1px solid #222; }
    table.areas, table.checks, table.brief { break-inside: avoid; font-size: 8.5pt; }
    .note { font-size: 7.6pt; color: #3d4752; }
    /* tables: ruled rows, headers that repeat on every page, rows that do not split */
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin: 0 0 5pt; font-size: 7.6pt; line-height: 1.38; }
    thead { display: table-header-group; }
    tr { break-inside: avoid; }
    th, td { text-align: left; vertical-align: top; padding: 3.4pt 6pt 3.4pt 0; border-bottom: 0.4pt solid #d5dae0; overflow-wrap: anywhere; }
    thead th { font-size: 6.3pt; font-weight: 600; letter-spacing: .07em; text-transform: uppercase; color: #5f6672; border-bottom: 0.9pt solid #1f2933; padding-top: 0; }
    tbody th { font-weight: 600; }
    .answers td, .answers tbody th { font-size: 8.2pt; padding-top: 4pt; padding-bottom: 4pt; }
    .answers .note { margin: 2pt 0 0; }
    .refs { margin: 0; padding: 0; list-style: none; }
    .refs li { margin: 0 0 1.5pt; }
    .ref { font-weight: 600; color: #1f2933; font-family: "IBM Plex Mono", Consolas, monospace; font-size: 0.95em; }
    .refs .ref, .sources .ref { display: inline-block; min-width: 15pt; }
    /* a rule id wraps between its words, at the dots and underscores, never mid-word */
    td .mono { overflow-wrap: break-word; word-break: normal; }
    td.trans { white-space: normal; }
    td.trans .st { margin: 0 1pt; }
    .action { margin-top: 2pt; color: #7a5a00; }
    .nums { font-family: "IBM Plex Mono", Consolas, monospace; font-size: 6.6pt; line-height: 1.35; }
    .nums .k { color: #5f6672; }
    .kv th { width: 30%; font-weight: 500; color: #3d4752; }
    .sec.ask { margin-top: 6pt; } .sec.ask h2 { font-size: 10pt; }
    table.kv.ask { font-size: 8.4pt; break-inside: avoid; } table.kv.ask th { width: 22%; }
    .sources { margin: 0; padding: 0; list-style: none; font-size: 7.6pt; }
    .sources li { display: grid; grid-template-columns: 18pt 1fr; padding: 3pt 0; border-bottom: 0.4pt solid #d5dae0; break-inside: avoid; }
    .url { font-size: 6.8pt; overflow-wrap: anywhere; }
    .cmd { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 7.2pt; background: #f1f4f7; border: 0.4pt solid #d5dae0; padding: 5pt 6pt; margin: 4pt 0 6pt; }
    .files td { font-size: 6.6pt; }
    .files td + td { white-space: nowrap; overflow-wrap: normal; }
    /* figures on white, fitted to the measure, labels printed at about 6.5pt */
    .fig { margin: 0 0 8pt; break-inside: avoid; }
    .draw { border: 0.4pt solid #d5dae0; padding: 4pt; text-align: center; }
    .draw svg { width: 100%; height: auto; display: block; margin: 0 auto; }
    .plan svg { max-height: 112mm; }
    .section svg { max-height: 52mm; }
    figcaption { font-size: 7.4pt; color: #3d4752; margin-top: 3pt; }
    figcaption b { color: #1f2933; }
    /* a status: a mark and its word, readable in grey on paper */
    .st { display: inline-flex; align-items: center; gap: 3pt; font-weight: 600; font-size: 7.4pt; white-space: nowrap; }
    .st::before { content: "–"; display: inline-flex; align-items: center; justify-content: center; width: 9pt; height: 9pt; border-radius: 50%; font-size: 6.4pt; font-weight: 700; color: #fff; background: #8a93a0; }
    .st-pass { color: #246a3d; } .st-pass::before { content: "✓"; background: #2f7d4a; }
    .st-conditional { color: #7a5a00; } .st-conditional::before { content: "!"; background: #d9a520; color: #1f2933; }
    .st-uncertain { color: #8f5a0e; } .st-uncertain::before { content: "?"; background: #fff; color: #8f5a0e; border: 0.8pt dashed #c77d14; }
    .st-fail { color: #a81a1a; } .st-fail::before { content: "✗"; background: #c81e1e; }
    .st-info { color: #245f9c; } .st-info::before { content: "i"; background: #2a6fb8; }
    .st-na { color: #5f6672; }
    /* the first page: the disclaimer, the rules not yet checked, and the drawings beside the answers (20 Nov 2026) */
    .disclaimer { color: #1f2933; font-weight: 600; }
    .unv-line { font-size: 7.6pt; color: #3d4752; margin: 2pt 0 0; }
    .unv { font: 600 6.4pt "IBM Plex Mono", Consolas, monospace; letter-spacing: .04em; color: #8f5a0e; border: 0.6pt solid #c77d14; border-radius: 2pt; padding: 0.4pt 2.5pt; margin-right: 3pt; }
    .note.intake { color: #1f2933; }
    .p1-figs { display: grid; grid-template-columns: 1fr; gap: 6pt; margin: 4pt 0 0; break-inside: avoid; align-items: start; }
    .p1-figs.two { grid-template-columns: 1.15fr 1fr; }
    /* answer 1's drawing (figures/envelope.js), on paper: its SVG at its own 168 px, its words under it */
    .env-paper .env-fig { margin: 0; border: 0.4pt solid #d5dae0; padding: 3pt 3pt 4pt; break-inside: avoid; }
    .env-paper .eyebrow { font-size: 6.3pt; font-weight: 600; letter-spacing: .07em; text-transform: uppercase; color: #5f6672; margin: 0 0 2pt; }
    /* drawn in pixels for the screen: at 0.7 its 11.5 px labels print at about 6pt, as the other figures' do */
    .env-paper svg { display: block; width: 100%; zoom: .7; }
    /* the page's own copies of app.css's .env-* rules (the paper loads no app.css): the short height labels, since the
       figure is narrower than the screen's 520 px switch; two columns of words, each under its mass */
    .env-paper .env-long { display: none; }
    .env-paper .env-short { display: inline; }
    .env-paper .env-cols { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 0 6pt; margin-top: 3pt; font-size: 6.8pt; line-height: 1.35; color: #5f6672; }
    .env-paper .env-col { padding-left: 4%; min-width: 0; }
    .env-paper .env-head { color: #1f2933; } .env-paper .env-head b { font-weight: 600; }
    .env-paper .env-head i { display: inline-block; width: 9pt; height: 5pt; margin-right: 3pt; vertical-align: middle; border: 0.6pt solid transparent; }
    .env-paper .fig-proposed { background: #9dc5ed; } .env-paper .fig-outright { background: #e5e5e5; border: 0.8pt dashed #8e8e8e; }
    .env-paper .env-num { color: #1f2933; font-variant-numeric: tabular-nums; margin-top: 1pt; }
    /* the first page has room for the heads and figures under each mass; the limits are in the answers above */
    .env-paper .env-sub { display: none; }
    .ms-list { display: none; }
    /* the capital stack, drawn as on screen: HTML on white, its columns at one scale in mm */
    .money-stack { margin: 0; break-inside: avoid; }
    .ms-paper { border: 0.4pt solid #d5dae0; padding: 4pt 4pt 3pt; }
    .ms-row { display: flex; gap: 8pt; }
    .ms-one { flex: 1 1 0; min-width: 0; }
    .ms-name { font-size: 7pt; font-weight: 600; margin: 0 0 2pt; }
    .ms-draw, .ms-keys { display: grid; grid-template-columns: minmax(0, 1fr) 21mm 21mm minmax(0, 1.25fr); column-gap: 1.6mm; position: relative; }
    .pair .ms-draw, .pair .ms-keys { grid-template-columns: minmax(0, 1fr) 17mm 17mm minmax(0, 1.3fr); }
    .ms-col { position: relative; align-self: end; grid-row: 1; }
    .ms-cost { grid-column: 2; } .ms-pay { grid-column: 3; }
    .ms-seg { position: absolute; left: 0; right: 0; border: 0.5pt solid #8e8e8e; display: flex; align-items: center; overflow: hidden; }
    .ms-seg + .ms-seg { border-bottom-width: 0; }
    .s-hard { background: #d7d7d7; } .s-soft { background: #e5e5e5; } .s-contingency { background: #efefef; } .s-land { background: #f6f6f6; }
    .ms-pay .ms-seg { border-color: #2a6fb8; }
    .s-debt { background: #d8e8f8; } .s-equity { background: #c5dcf4; } .s-other { background: #b1d1f1; } .s-grant { background: #9dc5ed; }
    .s-gap { background: repeating-linear-gradient(135deg, #5f6672 0 0.35pt, #fff 0.35pt 1.6mm); border: 0.6pt solid #1f2933 !important; }
    .ms-in { position: relative; z-index: 1; background: inherit; padding: 0 1.2mm; font-size: 6.6pt; line-height: 1.25; color: #1f2933; }
    .s-gap .ms-in { background: #fff; padding: 0.4mm 1.2mm; margin-left: 0.8mm; }
    .ms-in b, .ms-out b, .ms-keys b { font-weight: 600; }
    .ms-screen { position: absolute; grid-column: 2 / 4; grid-row: 1; left: -1mm; right: -1mm; border-top: 0.8pt dashed #c77d14; height: 0; }
    .ms-lab { position: relative; grid-row: 1; }
    .ms-lab-cost { grid-column: 1; } .ms-lab-pay { grid-column: 4; }
    .ms-leaders { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
    .ms-lead { fill: none; stroke: #5f6672; stroke-width: 0.5; } .ms-lead-bench { fill: none; stroke: #c77d14; stroke-width: 0.5; }
    .ms-out { position: absolute; font-size: 6.4pt; line-height: 3.3mm; white-space: nowrap; color: #1f2933; }
    .ms-lab-pay .ms-out { left: 22%; } .ms-lab-cost .ms-out { right: 22%; text-align: right; }
    .ms-out.ms-bench { color: #8f5a0e; }
    .ms-keys { margin-top: 1mm; font-size: 6.2pt; line-height: 1.3; color: #5f6672; text-transform: uppercase; letter-spacing: .05em; }
    .ms-keys > span:nth-child(2) { grid-column: 2; } .ms-keys > span:nth-child(3) { grid-column: 3; }
    .ms-keys b { color: #1f2933; text-transform: none; letter-spacing: 0; font-size: 7pt; }
    .ms-muted { color: #5f6672; text-transform: none; letter-spacing: 0; }
    .money-stack figcaption { font-size: 7pt; }
    /* who resolves what: a lane per person, the stages left to right */
    .lanes { display: grid; grid-template-columns: 24mm repeat(var(--stages, 3), minmax(0, 1fr)); margin: 0 0 6pt; font-size: 7pt; break-inside: avoid; }
    .lanes-head, .lane { display: contents; }
    .lanes-stage { font-size: 6.2pt; letter-spacing: .06em; text-transform: uppercase; color: #5f6672; font-weight: 600; padding: 0 0 2pt 2mm; border-bottom: 0.9pt solid #1f2933; }
    .lanes-head > span:first-child { border-bottom: 0.9pt solid #1f2933; }
    .lane-who { font-weight: 600; padding: 2pt 2mm 2pt 0; border-bottom: 0.4pt solid #d5dae0; }
    .lane-cell { list-style: none; margin: 0; padding: 2pt 0 2pt 2mm; border-bottom: 0.4pt solid #d5dae0; border-left: 0.4pt dashed #d5dae0; display: flex; flex-direction: column; gap: 1.5pt; }
    .lane-node { border: 0.5pt solid #9aa3ad; border-radius: 2pt; padding: 1pt 2pt; line-height: 1.3; }
    .lane-node .ref { margin-right: 2pt; }
    .node-stage { display: none; }
    .node-also { display: block; color: #5f6672; font-size: 6.4pt; }
    /* words in this memo */
    .words dl { margin: 0; columns: 2; column-gap: 8mm; font-size: 7.6pt; }
    .words dl > div { break-inside: avoid; margin: 0 0 3pt; }
    .words dt { font-weight: 600; } .words dd { margin: 0; color: #3d4752; }
    @media screen { body { max-width: 190mm; margin: 12mm auto; } }`;
  // the option's short name, the whole name beneath (as on screen)
  const optFull = String(opt.name || opt.id || "—"), optShort = briefName(optFull, site);
  const titleBlock = `<div class="tb">
      <div style="grid-column: span 2"><b>Option</b>${h(optShort)}${optShort !== optFull ? `<div class="muted" style="font-size:7.2pt">${h(optFull)}</div>` : ""}</div>
      <div><b>Revision</b><span class="big">${h(revA)}</span>${issuedPaper(run)}</div>
      <div><b>Rules as of</b><span class="big">${h(asOf)}</span></div>
      <div><b>Proponent</b>${h(opt.proponent || "—")}${opt.proponent_type ? ` <span class="muted">(${h(optWord("option", "proponent_type", opt.proponent_type))})</span>` : ""}</div>
      <div><b>Site</b>${h(site.zoning_district || "—")} · ${h(fmtNum(site.site_area_m2 ?? "—"))} m² · ${h(site.frontage_m ?? "—")} × ${h(site.depth_m ?? "—")} m</div>
      <div><b>${d && !board ? (kind === "rules" ? "Revised from" : "Compared with") : "Run"}</b>${d && !board ? `${h(revB)}${B ? ` · ${h(briefName(optionName(B), site))}` : ""}` : h(ran || "not recorded")}<br><span class="muted">printed ${h(printed)}</span></div>
      <div><b>Fingerprint</b><span class="mono">${h(st.stamp)}</span><br><span class="muted">engine ${h(L.run.engine_version)}</span></div>
    </div>`;
  // the first page: the answers with the money drawn beside them, and the outright-against-proposed drawing where the
  // figures module gives one
  // the drawing is the screen's own (figures/envelope.js), laid out for paper by the .env-* rules above
  let env = "";
  try { const fig = String(envelopeFigure(run) || ""); if (/<svg/.test(fig)) env = `<div class="env-paper">${fig}</div>`; } catch (e) { env = ""; }
  const stackP1 = pfOk ? stackFigure([stackOf(run.proforma)], { unit: "mm", H: 29, lh: 3.3 }, `<b>The money to one scale.</b> ${run.proforma.gap.value > 0 ? "Hatched: the gap. " : ""}Amber: the 15% screening line.`) : "";
  const p1figs = stackP1 || env ? `<div class="p1-figs${stackP1 && env ? " two" : ""}">${stackP1}${env}</div>` : "";
  const unv = unverifiedRules(L);
  const unvLine = unv.length ? `<p class="unv-line"><span class="unv">UNVERIFIED</span>${unv.length === 1 ? "1 rule in this memo is" : `${unv.length} rules in this memo are`} not yet checked against ${unv.length === 1 ? "its" : "their"} source (marked UNVERIFIED in the ledger): ${h(unv.map(r => `${ref(r.rule_id)} ${fewWords(r.title)}`).join("; "))}.</p>` : "";
  // the front sheet, shaped as an ask (25 Nov 2026): the first thing on page one, after the title block
  const fs = frontOf(run);
  const askPaper = `<section class="sec ask"><h2>The ask</h2><table class="kv ask"><tbody>
      <tr><th scope="row">Who is housed</th><td>${h(fs.housed)}</td></tr>
      <tr><th scope="row">Who operates</th><td>${h(fs.operator)}</td></tr>
      <tr><th scope="row">Which program</th><td>${h(fs.programs)}</td></tr>
      <tr><th scope="row">The amount</th><td>${h(amountWords(fs.money))}</td></tr>
      <tr><th scope="row">The decision wanted</th><td>${fs.decision ? h(fs.decision) : '<span class="muted">not stated</span>'}</td></tr>
      <tr><th scope="row">The answers</th><td>${fs.verdicts.map(v => `${h(v.label)}: <b>${h(cap(String(v.verdict || "")))}</b>`).join(" · ")}</td></tr>
      ${fs.open_items.length ? `<tr><th scope="row">The top ${fs.open_items.length} of ${fs.open_total} open items</th><td>${fs.open_items.map((u, i) => `${i + 1}. ${h(u.title)} ${mark(u.status)}`).join("<br>")}</td></tr>` : ""}
    </tbody></table></section>`;
  const words = s.words ? `<section class="sec words"><h2><span class="no">${s.words}</span> Words in this memo</h2><dl>${terms.map(([t, w]) => `<div><dt>${h(t)}</dt><dd>${h(w)}</dd></div>`).join("")}</dl></section>` : "";
  const head = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${h(`First Read ${board ? "board memo" : "memo"} ${revA} · ${address}`)}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>${css}${board ? BOARD_CSS : ""}</style></head><body>`;
  if (board) {
    // the board memo (26 Nov 2026, Kai): two pages a board reads before it votes. The decision first, then the four
    // answers with the money drawn, the five open items that matter most with who resolves each, and only the sources
    // those pages cite; the full memo keeps everything else
    const decisionText = String(decision || fs.decision || "").trim();
    const RANKS = { fail: 0, uncertain: 1, conditional: 2 };
    const top5 = unsure.map((u, i) => [u, i]).sort((a, b) => (RANKS[a[0].status] ?? 3) - (RANKS[b[0].status] ?? 3) || a[1] - b[1]).slice(0, 5).map(([u]) => u);
    const cited = new Set();
    // the rules these pages name: the three each answer shows (as decidedBy), the discretion's, the five open items'
    const citeFrom = o => ["fail", "conditional", "uncertain"].flatMap(k => (o && o[k]) || []).slice(0, 3).forEach(id => cited.add(id));
    citeFrom(ans.allowed.outright); citeFrom(ans.allowed.by_rezoning); citeFrom(ans.funded);
    if (routes) (routes.discretion.rules || []).forEach(id => cited.add(id));
    top5.forEach(u => { if (u.rule_id) cited.add(u.rule_id); });
    const boardSources = sources.filter(x => x.cites.some(id => cited.has(id)));
    // each source in a line: its title, section, the refs it stands behind here and the site it is on (the full memo
    // prints the addresses)
    const host = u => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch (e) { return ""; } };
    const boardSrc = boardSources.length ? `<ol class="sources">${boardSources.map((x, i) => `<li><b class="ref">S${i + 1}</b> <span>${h(x.title || x.url)}${x.section ? `<span class="muted">, ${h(x.section)}</span>` : ""} <span class="muted">· for ${x.cites.filter(id => cited.has(id)).map(ref).join(", ")}${x.url && host(x.url) ? ` · ${h(host(x.url))}` : ""}</span></span></li>`).join("")}</ol>` : `<p class="note">No rule on these pages rests on a source the memo cites.</p>`;
    const openTop = top5.length ? `<table class="open">
        <colgroup><col style="width:6%"><col style="width:34%"><col style="width:13%"><col></colgroup>
        <thead><tr><th>Ref</th><th>Item</th><th>Status</th><th>Who resolves it</th></tr></thead>
        <tbody>${top5.map(u => `<tr><td>${refCell(u.rule_id)}</td><td><b>${h(u.title)}</b></td><td>${mark(u.status)}</td><td>${h(u.action || "—")}</td></tr>`).join("")}</tbody></table>${unsure.length > top5.length ? `<p class="note">${unsure.length - top5.length} more in the full memo, each with who resolves it.</p>` : ""}`
      : `<p>Nothing is open: every rule that applies is settled for this option.</p>`;
    return `${head}
    <h1>${h(address)}</h1>
    <p class="sub">First Read board memo · ${h(revA)} · rules as of ${h(asOf)} · printed ${h(printed)}</p>
    ${titleBlock}
    <section class="sec ask board-ask"><h2>The decision wanted</h2>
      <p class="decision">${decisionText ? h(decisionText) : '<span class="muted">Not stated by the development manager.</span>'}</p>
      <table class="kv ask"><tbody>
        <tr><th scope="row">Who is housed</th><td>${h(fs.housed)}</td></tr>
        <tr><th scope="row">Who operates</th><td>${h(fs.operator)}</td></tr>
        <tr><th scope="row">Which program</th><td>${h(fs.programs)}</td></tr>
        <tr><th scope="row">The amount</th><td>${h(amountWords(fs.money))}</td></tr>
      </tbody></table></section>
    <section class="sec"><h2><span class="no">1</span> The four answers</h2>${answers}${unvLine}${stackP1 ? `<div class="p1-figs">${stackP1}</div>` : ""}</section>
    <section class="sec"><h2><span class="no">2</span> ${top5.length ? `The top ${top5.length} of ${unsure.length} open items` : "Open items"}</h2>${openTop}</section>
    <section class="sec"><h2><span class="no">3</span> Sources for these pages</h2>${boardSrc}
      <p class="note"><b>A feasibility screen, not legal, planning or funding advice; an independent student tool, not affiliated with BC Housing, the Province, CMHC or the City of Vancouver.</b> The full memo, ${h(revA)}, has the clauses, the drawings, every rule with its numbers and source, the money line by line and how to reproduce it.</p></section>
  </body></html>`;
  }
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${h(`First Read memo ${revA} · ${address}`)}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>${css}</style></head><body>
    <h1>${h(address)}</h1>
    <p class="sub">First Read memo · ${h(revA)}${ran ? ` · run ${h(ran)}` : ""} · printed ${h(printed)}</p>
    ${titleBlock}
    <p class="howto"><b class="disclaimer">A feasibility screen, not legal, planning or funding advice; an independent student tool, not affiliated with, reviewed by or a position of BC Housing, the Province, CMHC or the City of Vancouver.</b> Rules are named by layer and place (A1, C4…) throughout.${s.words ? ` Section ${s.words} explains the words;` : ""} ${short ? "this is the short memo: the full memo adds the clauses, the drawings, every rule with its numbers, the inputs and how to reproduce it." : `section ${s.ledger} gives each rule's finding, numbers and source; section ${s.verify} says how to reproduce the memo.`}</p>
    ${askPaper}
    <section class="sec"><h2><span class="no">1</span> The four answers</h2>${answers}${unvLine}${p1figs}</section>
    <section class="sec"><h2><span class="no">2</span> Open items and who resolves them</h2>${open}</section>
    ${compare}
    ${pfOk ? `<section class="sec"><h2><span class="no">${s.money}</span> The money, line by line</h2>${moneyLines}</section>` : ""}
    ${s.clauses ? `<section class="sec"><h2><span class="no">${s.clauses}</span> Clauses applied</h2><p class="note">${applied.length} of ${res.length} rules apply. Proposed is what the option puts forward; permitted or required is the clause's own limit; the ask is what stands between them.</p>${clauses}</section>` : ""}
    ${s.massing ? `<section class="sec"><h2><span class="no">${s.massing}</span> Massing</h2>${figures}</section>` : ""}
    ${s.areas ? `<section class="sec"><h2><span class="no">${s.areas}</span> Area schedule, and what an operator checks</h2>${areasPaper(run)}</section>` : ""}
    ${words}
    ${s.ledger ? `<section class="sec"><h2><span class="no">${s.ledger}</span> The full ledger, by layer</h2><p class="note">Every rule the engine ran, including those that do not apply here, with its finding, every number it used and the section of its source (S numbers, section ${s.sources}).</p>${ledger}</section>` : ""}
    ${s.inputs ? `<section class="sec"><h2><span class="no">${s.inputs}</span> Inputs</h2>${inputs}</section>` : ""}
    <section class="sec"><h2><span class="no">${s.sources}</span> Sources</h2>${srcList}</section>
    ${s.verify ? `<section class="sec"><h2><span class="no">${s.verify}</span> Reproduce and verify, for the architect</h2>${verify}</section>` : ""}
  </body></html>`;
}

/* Download PDF: the server prints the paper memo with a headless Edge or Chrome and the browser saves the file.
   Where there is no server (the web version) or no such browser, the paper memo opens in the print dialog, where
   Save as PDF gives the same document. */
/* `mode`: false the full memo, true the short one, "board" the two-page board memo (with `decision` where one was
   typed at the download). */
export async function exportPdf(mode = false, { decision = null } = {}) {
  const run = state.run;
  if (!run) return;
  const board = mode === "board", short = mode === true;
  const html = paperDocument(run, { short, board, decision });
  const name = `${run.run_id.replace("/", "_")}_${rev(run.run_id)}_${board ? "board-memo" : `memo${short ? "-short" : ""}`}.pdf`;
  if (!STATIC) {
    setStatus("Laying out the PDF…", "busy");
    try {
      const r = await fetch("api/pdf", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ html }) });
      if (r.ok) {
        const url = URL.createObjectURL(await r.blob());
        const a = document.createElement("a"); a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 60000);
        setStatus(board ? `Saved ${name}: the decision wanted, the four answers, the top open items and the sources they cite, for the board.`
          : short ? `Saved ${name}: ${rev(run.run_id)}'s ask, answers, open items, money and sources.` : `Saved ${name}: ${rev(run.run_id)}, its answers, open items, clauses, massing, full ledger, inputs and sources.`, "ok");
        return;
      }
    } catch (e) { /* no server answer: print instead */ }
  }
  printPaper(html, "In the print dialog, choose Save as PDF.");
}

/* The paper memo in the browser's print dialog, from a hidden frame, once its fonts have loaded. */
export function printPaper(html, note = "") {
  const f = document.createElement("iframe");
  f.title = "The memo for printing";
  f.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0;visibility:hidden";
  f.srcdoc = html;
  f.addEventListener("load", async () => {
    try { await f.contentDocument.fonts.ready; } catch (e) { /* print with what has loaded */ }
    f.contentWindow.focus();
    f.contentWindow.print();
    setTimeout(() => f.remove(), 60000);
  }, { once: true });
  document.body.appendChild(f);
  setStatus(`Opened the memo for printing.${note ? ` ${note}` : ""}`, "info");
}
