/* The memo's four answers: allowed outright and by rezoning, what the funders ask, what is still open, and whether
   the money works. */

import { cap, fmtNum, h, leadCont, pill, VERDICT_OUTRIGHT, verdictStatus, withoutRepeat } from "../core/util.js";
import { state } from "../core/state.js";
import { refOf, refTagOf } from "./memo.js";
import { withPlans } from "./clauses.js";
import { ruleTitle } from "../route-stage.js";
import { districtOf } from "../fields.js";

export function answerAllowed(L) {
  const res = L.results, ans = L.summary.answers, site = L.inputs.site;
  const o = ans.allowed.outright, bz = ans.allowed.by_rezoning, path = ans.allowed.rezoning_path;
  // the district's FSR and height, and its yards where they leave no envelope (as engine.counts_outright)
  const outLines = res.filter(r => ((r.check || "").startsWith("district_outright") || (r.check === "district_setbacks" && (r.values || {}).no_envelope)) && r.status !== "not_applicable");
  const policy = res.filter(r => ["A", "B", "C"].includes(r.layer) && ["fail", "conditional", "uncertain"].includes(r.status) && !(r.check || "").startsWith("district_outright"));
  let verdict = `${h(VERDICT_OUTRIGHT[o.verdict] || cap(o.verdict) + ".")}`;
  if (path) verdict += ` By rezoning: <em>${h(bz.verdict)}</em>.`;
  let body = `<p class="path">Outright under ${h(districtOf(site) || "the district")}${path ? ` · rezoning path: ${h(path)}` : " · no rezoning path stated"}</p>`;
  // nothing was tested: say why, in the words answer 3 repeats with the person who settles it
  if (o.why) body += `<p class="finding"><b>Not assessed:</b> ${h(o.why)}. The storeys, height and floor area in this memo are the option's own figures, not permitted ones; answer 3 names who reads the schedule.</p>`;
  // each finding cites the rule it came from (A1, its title), so a CD-1 site shows its own by-law's rules (17 Nov 2026)
  body += outLines.map(r => `<p class="finding">${refTagOf(r.rule_id)}${leadCont(r.finding)} <span class="cont">(${h(r.title)})</span></p>`).join("");
  if (path && policy.length) {
    body += `<ul class="finding-list">${policy.map(r => `<li>${pill(r.status)}<span><span class="title">${h(r.title)}:</span> <span class="cont">${h(r.finding)}</span></span></li>`).join("")}</ul>`;
  }
  const status = verdictStatus(path ? bz.verdict : o.verdict);   // the operative answer: by rezoning when a path is stated
  return `<section class="card answer" data-verdict="${h(status)}">
    <h2><span class="badge">1</span> Is it allowed?</h2>
    <p class="verdict">${verdict}</p>
    ${body}
  </section>`;
}

export function answerFunders(L) {
  const res = L.results, ans = L.summary.answers, opt = L.inputs.option;
  const targets = new Set(opt.target_programs || []);
  const rows = res.filter(r => r.layer === "E" && (!targets.size || targets.has(r.rule_id)));
  const others = res.filter(r => r.layer === "E" && targets.size && !targets.has(r.rule_id));
  let body = `<ul class="finding-list">${rows.map(r => `<li>${pill(r.status)}<span><span class="title">${h(r.title)}:</span> <span class="cont">${h(withoutRepeat(r.title, r.finding))}</span></span></li>`).join("")}</ul>`;
  if (others.length) body += `<p class="path" style="margin-top:12px">Not targeted, listed in the ledger: ${others.map(r => h(r.title)).join("; ")}.</p>`;
  return `<section class="card answer" data-verdict="${h(verdictStatus(ans.funded.verdict))}">
    <h2><span class="badge">2</span> Does it fit the funders?</h2>
    <p class="verdict"><em>${h(cap(ans.funded.verdict))}.</em></p>
    ${body}
  </section>`;
}

/* What the drawings found that the rules did not: homes that did not fit the plate, and hand-placed blocks that
   overlap or sit outside it. They join answer 3 with the architect named (15 Nov 2026: before, they stayed on FIG 03
   while the answers priced every home). Pure. */
export function layoutOpenItems(run) {
  const lay = run && run.layout;
  if (!lay) return [];
  const out = [];
  const short = (lay.shortfall || []).filter(s => s.units || s.area_m2);
  if (short.length && lay.units_total) {
    const words = short.map(s => `${s.units ? s.units + " " : ""}${String(s.label || "").toLowerCase()}`).join(", ");
    out.push({ title: "Homes that do not fit the plate", status: "conditional",
      action: `Architect: ${lay.units_placed} of ${lay.units_total} homes fit the plate on ${(lay.floors || []).length} floors; did not fit: ${words}. More storeys, a larger plate or a smaller program. The money and the funders' checks count all ${lay.units_total}.` });
  }
  const broken = lay.geometry || [];
  if (broken.length) {
    out.push({ title: "Blocks placed by hand that break the plate", status: "fail",
      action: `Architect: ${broken.length} problem${broken.length === 1 ? "" : "s"} in the hand placement: ${broken.slice(0, 3).map(g => g.note || g.kind || "").join("; ")}${broken.length > 3 ? "; …" : ""}. Fix them in Edit blocks before issuing.` });
  }
  // the exits, from the building code (bcbc.exits): a floor over the travel distance, with its stairs too close
  // together, or a corridor running past the last exit is the architect's to fix in the block editor (16 Nov 2026)
  const eg = lay.egress;
  if (eg && ["fail", "conditional", "uncertain"].includes(eg.status)) {
    const bad = (eg.floors || []).filter(f => f.status !== "pass");
    const first = bad[0];
    out.push({ rule_id: eg.rule_id, title: "Exits: travel distance, separation and dead ends (BC Building Code)", status: eg.status,
      action: `Architect: ${bad.length} of ${(eg.floors || []).length} floors ${bad.length === 1 ? "does" : "do"} not pass the exit clauses${first ? ` (${first.name}: ${egressLine(first)})` : ""}. ${eg.summary || ""} Move or add a core in Edit blocks; the sprinkler assumption${eg.sprinklered_is_placeholder ? " is a placeholder" : ""} and the clause figures are unverified against the code text.` });
  }
  return out;
}

/* One floor's egress in a line, as the plans sheet prints it. Pure. */
export function egressLine(f) {
  // as layout.egress_line words it: each figure with its unit and which side of it the limit is
  const parts = [`${f.exits} exit${f.exits === 1 ? "" : "s"}, ${f.exits_required} required`];
  if (f.farthest_travel_m != null) parts.push(`travel ${f.farthest_travel_m.toFixed(1)} m, limit ${f.travel_limit_m} m`);
  if (f.separation_min_m != null && f.separation_m != null) parts.push(`separation ${f.separation_m.toFixed(1)} m, at least ${f.separation_min_m} m`);
  if (f.dead_end_m != null) parts.push(`dead end ${f.dead_end_m.toFixed(1)} m, limit ${f.dead_end_limit_m} m`);
  return parts.join(" · ");
}

export function answerUnsure(L, run) {
  const items = [...(L.summary.answers.unsure || []), ...layoutOpenItems(run)];
  const n = items.length;
  const verdict = n ? `${n === 1 ? "One open item" : `${["", "", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"][n] || n} open items`}. Each names who resolves it.` : "Nothing outstanding.";
  // the longest name first, so "Manager and owner" is not read as "Manager"; an action with no name is the
  // manager's, who carries the memo (17 Nov 2026: a "—" under Who beside "Each names who resolves it")
  const WHO = /^(Manager and owner|Manager and architect|Manager|Architect|Owner|Planner|Both)\b:?\s*/i;
  const who = u => { const m = WHO.exec(u.action || ""); return m ? cap(m[1]) : "Manager"; };
  const todo = u => cap((u.action || "").replace(WHO, "")) || "—";
  const table = n ? `<table class="plain open-items"><thead><tr><th>Ref</th><th>Item</th><th>Status</th><th>Who</th><th>What to do</th></tr></thead><tbody>
    ${items.map(u => `<tr><td data-k="Ref">${refOf(u.rule_id) ? `<b class="ref" title="${h(u.title)}">${h(refOf(u.rule_id))}</b>` : "—"}</td><td data-k="Item">${h(u.title)}</td><td class="status" data-k="Status">${pill(u.status)}</td><td class="who" data-k="Who">${h(who(u))}</td><td class="todo" data-k="What to do">${h(todo(u))}</td></tr>`).join("")}
  </tbody></table>` : "";
  // the clauses also marked uncertain that are not open items here, named, so the two counts reconcile (17 Nov 2026:
  // "Four open items" over a clause table counting 6 Uncertain); the outright limits are answered by the rezoning
  const covered = new Set(items.map(u => u.rule_id).filter(Boolean));
  const also = withPlans(L.results, run).filter(r => r.status === "uncertain" && !covered.has(r.rule_id));
  const outright = also.filter(r => String(r.check || "").startsWith("district_outright"));
  const rest = also.filter(r => !outright.includes(r));
  const refList = rs => rs.map(r => `${refOf(r.rule_id) ? `${refOf(r.rule_id)} ` : ""}${r.title}`).join("; ");
  const alsoLine = also.length ? `<p class="cont also-uncertain">Also uncertain in Clauses applied, with no open item of their own: ${h(refList(also))}.${outright.length && L.summary.answers.allowed.rezoning_path ? ` ${outright.length === 1 ? "The outright limit is" : "The outright limits are"} answered in 1: the rezoning decides ${outright.length === 1 ? "it" : "them"}.` : ""}${rest.length ? " The clause rows say what each needs." : ""}</p>` : "";
  // a count of open items is not a verdict: the card carries no status wash; each row wears its own
  return `<section class="card answer" data-verdict="${n ? "plain" : "pass"}">
    <h2><span class="badge">3</span> What is still unsure, and who resolves it?</h2>
    <p class="verdict">${verdict}</p>
    ${table}
    ${alsoLine}
  </section>`;
}

/* The fourth answer: the feasibility-grade pro-forma from layer F and layer E, four lines and the verdict; the
   line-by-line table with every source opens under it. */
export const money = x => (x === null || x === undefined ? "not given" : `$${fmtNum(Math.round(x))}`);

/* A source's short name for a table cell: the publisher and the document up to the first comma or semicolon. */
const shortSource = s => { const t = String((s && s.title) || (s && s.url) || ""); const cut = t.split(/[;(]/)[0]; return (cut.length > 72 ? cut.slice(0, 70).replace(/\s+\S*$/, "") + "…" : cut).trim(); };

/* How a verdict is worded and what it asks of the development manager (17 Nov 2026, Kai: "Unlikely" read as "will not
   be funded"; a gap past the screen's line is the cue to look for more sources, so it reads Conditional, not Fail).
   The key stays the engine's; proforma.VERDICT_WORDS and proforma.next_step say the same in the memo file. */
export const MONEY_STATUS = { likely: "pass", unlikely: "conditional", unsure: "uncertain" };
export const MONEY_WORD = { likely: "Likely", unlikely: "Needs more sources", unsure: "Unsure" };
export const moneyWord = v => MONEY_WORD[v.word] || cap(v.word);
export function moneyNext(pf) {
  const v = pf.verdict || {}, gap = (pf.gap || {}).value, c = pf.capital || {}, homes = (pf.inputs || {}).units_total;
  if (v.word === "unlikely") return "Look for more sources as well: other grants (CMHC's Affordable Housing Fund among them), more equity, a land contribution or a partner. Enter what is found as Other grants or Equity and run again.";
  if (v.word === "unsure" && homes && gap != null && gap > 0 && c.total != null && c.land != null) return "Another source, or firmer figures for the placeholders, would settle it.";
  return "";
}

/* The architect reads the money folded (17 Nov 2026, Kai: "the financials are too long … more of a developer's
   thing"): the verdict stays on the card; the figures, the reasons and the line table wait behind one disclosure,
   and ledger layer F follows it. The architect's choice is kept for the next visit. */
export const MONEY_FOLD_KEY = "ffm.architect.money";
export function architectMoneyOpen() { try { return localStorage.getItem(MONEY_FOLD_KEY) === "open"; } catch (e) { return false; } }
export function rememberArchitectMoney(open) { try { localStorage.setItem(MONEY_FOLD_KEY, open ? "open" : "folded"); } catch (e) { /* the choice lasts this visit */ } }

/* A figure in millions for the folded line: $54.1M. */
const millions = x => (x == null ? "not given" : `${x < 0 ? "−" : ""}$${(Math.abs(x) / 1e6).toFixed(1)}M`);

export function answerMoney(run) {
  const pf = run.proforma;
  if (!pf) return "";
  if (!pf.available) {
    return `<section class="card answer" data-verdict="uncertain">
      <h2><span class="badge">4</span> Does the money work?</h2>
      <p class="verdict"><em>Not computed.</em></p><p class="finding">${h(pf.why || "")}</p></section>`;
  }
  const v = pf.verdict, c = pf.capital, o = pf.operating, f = pf.funding, g = pf.gap;
  const next = moneyNext(pf);
  const grants = (f.grants || []).reduce((t, x) => t + (x.value || 0), 0);
  const unit = u => (u === "$/yr" ? " a year" : u === "$/m²" ? " per m²" : "");
  const shown = ln => (ln.unit === "×" ? (ln.value == null ? "not given" : `×${ln.value}`) : ln.unit && ln.unit.startsWith("$") ? money(ln.value) + unit(ln.unit) : (ln.value == null ? "not given" : fmtNum(ln.value)));
  // every line names the rule it came from and links the rule's source, as the ledger carries it
  const srcOf = id => { const r = (run.ledger && run.ledger.results || []).find(x => x.rule_id === id); return r && r.source ? r.source : null; };
  const rows = (pf.lines || []).map(ln => {
    const s = ln.rule_id ? srcOf(ln.rule_id) : null;
    // the rule by its reference, the source as a short link (its full title in the link's title): the ledger carries the rest
    const from = ln.rule_id ? `${refTagOf(ln.rule_id)}<code title="${h(ruleTitle(ln.rule_id))}">${h(ln.rule_id)}</code>${s ? `<div class="cont">${s.url ? `<a href="${h(s.url)}" target="_blank" rel="noopener" title="${h(s.title || s.url)}">${h(shortSource(s))}</a>` : h(shortSource(s))}</div>` : ""}` : `<span class="cont">the option's own figures</span>`;
    return `<tr><td>${h(ln.label)}</td><td class="num">${h(shown(ln))}</td><td>${from}${ln.placeholder ? ' <span class="ph-tag">placeholder</span>' : ""}</td><td class="cont">${h(ln.note || "")}</td></tr>`;
  }).join("");
  const body = `${next ? `<p class="finding money-next"><span class="cont">For the development manager:</span> ${leadCont(next)}</p>` : ""}
    <dl class="pf-four">
      <div><dt>Capital cost</dt><dd><b>${h(money(c.total))}</b><span class="cont">hard ${h(money(c.hard))} (escalated ×${h(c.escalation)}), soft ${h(money(c.soft))}, contingency ${h(money(c.contingency))}, land ${h(money(c.land))}</span></dd></div>
      <div><dt>Net operating income</dt><dd><b>${h(money(o.noi))} a year</b><span class="cont">rent ${h(money(o.gross))} less vacancy, operating cost and reserve</span></dd></div>
      <div><dt>Funding</dt><dd><b>${h(money(f.total))}</b><span class="cont">grants ${h(money(grants))}, equity ${h(money(f.equity))}, debt ${h(money(f.debt.supportable))} at ${h(f.debt.rate_pct)}% over ${h(f.debt.amortization_years)} years, ${h(Number(f.debt.dcr).toFixed(2))} coverage${pf.inputs && pf.inputs.units_total ? `; ${h(pf.inputs.units_total)} homes as entered${run.layout && run.layout.units_placed != null && run.layout.units_placed < pf.inputs.units_total ? ` (${h(run.layout.units_placed)} fit the plate: answer 3)` : ""}` : ""}</span></dd></div>
      <div><dt>Gap</dt><dd><b>${h(money(g.value))}</b><span class="cont">${g.share_of_capital != null ? `${h(Math.round(g.share_of_capital * 100))}% of the capital cost; a negative gap is headroom` : ""}</span></dd></div>
    </dl>
    ${v.unsure && v.unsure.length ? `<p class="path">Left to a person: ${h(v.unsure.join("; "))}.</p>` : ""}
    ${v.why.length > 1 ? `<p class="path">${h(v.why.slice(1).map(w => w[0].toUpperCase() + w.slice(1) + ".").join(" "))}</p>` : ""}
    <details class="pf-lines"><summary>Every line, where it came from, and its source <span class="cont">(${(pf.lines || []).length} lines)</span></summary>
      <table class="plain"><thead><tr><th>Line</th><th>Figure</th><th>From</th><th>Note</th></tr></thead><tbody>${rows}</tbody></table>
      <p class="cont">A feasibility screen, not a lender's model. Hard costs from a Class D catalogue estimate escalated by the Statistics Canada index; rents from the CMHC survey; debt at the posted five-year rate under CMHC's coverage ratio. Placeholders are marked.</p>
    </details>`;
  // the architect's card: the verdict, then the pro-forma behind one line that carries its three figures
  const fold = state.mode === "architect"
    ? `<details class="money-more"${architectMoneyOpen() ? " open" : ""}>
        <summary><span class="mm-closed"><span class="mm-act">Show the pro-forma</span> <span class="cont">· capital ${h(millions(c.total))}, funding ${h(millions(f.total))}, gap ${h(millions(g.value))} · the development manager's figures</span></span><span class="mm-open"><span class="mm-act">Fold the pro-forma</span></span></summary>
        <div class="money-body">${body}</div>
      </details>`
    : body;
  return `<section class="card answer money" data-verdict="${MONEY_STATUS[v.word] || "uncertain"}">
    <h2><span class="badge">4</span> Does the money work?</h2>
    <p class="verdict"><em>${h(moneyWord(v))}.</em> ${h(v.why[0] ? v.why[0][0].toUpperCase() + v.why[0].slice(1) + "." : "")}</p>
    ${fold}
  </section>`;
}

/* The architect's fold on the money card is one switch for the financials: it is remembered, and ledger layer F
   (the pro-forma's assumptions) opens and folds with it. */
export function wireMoneyFold() {
  const d = document.querySelector(".answer.money details.money-more");
  if (!d) return;
  d.addEventListener("toggle", () => {
    rememberArchitectMoney(d.open);
    const f = document.querySelector('.ledger details.layer[data-layer="F"]');
    if (f && f.open !== d.open) f.open = d.open;
  });
}
