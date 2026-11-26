/* The memo's four answers: allowed outright and by rezoning, what the funders ask, what is still open, and whether
   the money works. */

import { cap, fmtNum, h, leadCont, pill, VERDICT_OUTRIGHT, verdictStatus, withoutRepeat } from "../core/util.js";
import { state } from "../core/state.js";
import { refOf, refTagOf } from "./memo.js";
import { withPlans } from "./clauses.js";
import { ruleTitle } from "../route-stage.js";
import { districtOf } from "../fields.js";
import { millionsOf, SCREEN_SHARE, stackFigure, stackOf } from "./stack.js";
import { fewWords, lanesHtml, todoOf, whoOf } from "./lanes.js";
import { envelopeFigure } from "../figures/envelope.js";
import { routesHtml } from "./front.js";

/* The outright answer as a reader says it (20 Nov 2026): where the option is over the district's own FSR or height,
   the engine reads that as fail, "not allowed outright; rezoning is required" (it read uncertain before), and the
   memo says "Not outright: rezoning required." The card's wash still comes from the operative answer, by rezoning
   where a path is stated, so the outright excess does not turn a conditional rezoning red. Pure. */
export const isOutrightLimit = r => String((r && r.check) || "").startsWith("district_outright");
export function outrightWords(o, outLines = []) {
  if (o.verdict === "no") {
    const against = outLines.filter(r => ["fail", "uncertain"].includes(r.status));
    return against.length && against.every(isOutrightLimit) ? "Not outright: rezoning required." : "Not outright.";
  }
  return VERDICT_OUTRIGHT[o.verdict] || `${cap(o.verdict)}.`;
}

/* A rule in an answer's list: its status as a word with its mark, its reference, then the finding (lead in ink, the
   rest muted). The mark and the reference share the first cell, so a finding that wraps never runs under them. */
const ruleItem = (r, text) => `<li><span class="fl-marks">${pill(r.status)}${refTagOf(r.rule_id).trim()}</span><span>${text}</span></li>`;

export function answerAllowed(L, run = null) {
  const res = L.results, ans = L.summary.answers, site = L.inputs.site;
  const o = ans.allowed.outright, bz = ans.allowed.by_rezoning, path = ans.allowed.rezoning_path;
  // the district's FSR and height, and its yards where they leave no envelope (as engine.counts_outright)
  const outLines = res.filter(r => (isOutrightLimit(r) || (r.check === "district_setbacks" && (r.values || {}).no_envelope)) && r.status !== "not_applicable");
  const policy = res.filter(r => ["A", "B", "C"].includes(r.layer) && ["fail", "conditional", "uncertain"].includes(r.status) && !isOutrightLimit(r));
  // the operative words wear the status colour: by rezoning where a path is stated, else the outright answer
  // a path that says there is no rezoning (a development permit under an official development plan, "none: …") is an
  // approval route, not a rezoning; and an outright scheme that proposes none needs none (23 Nov 2026, checks.proposes_rezoning)
  const route = ans.allowed.approval_route || "";
  const proposes = route === "rezoning" || (!["development_permit", "outright"].includes(route) && !!path && !/^(none|no rezoning|not a rezoning)/i.test(String(path).trim()));
  const notNeeded = bz.verdict === "not needed";
  // within the Director's discretion is not outright (25 Nov 2026): the three verdicts under this line say which
  const discretion = ((ans.allowed.routes || {}).discretion || {}).verdict === "possible";
  // a rezoning Council approved (25 Nov 2026): not "rezoning required" beside "approved"; the date from bz.why
  const approved = bz.verdict === "approved";
  const approvedOn = approved ? ((String(bz.why || "").match(/ on (\d{1,2} \w+ \d{4})/) || [])[1] || "") : "";
  const outSaid = approved ? "Not outright." : discretion ? "Not outright: within what the Director of Planning may allow." : outrightWords(o, outLines);
  let verdict = proposes ? h(outSaid) : `<em>${h(outSaid)}</em>`;
  if (proposes) verdict += ` By rezoning: <em>${h(bz.verdict)}${approvedOn ? `, ${h(approvedOn)}` : ""}</em>.`;
  else if (notNeeded) verdict += " No rezoning needed.";
  const district = districtOf(site) || "the district";
  let body = "";
  // nothing was tested: say why, in the words answer 3 repeats with the person who settles it
  if (o.why) body += `<p class="finding"><b>Not assessed:</b> ${h(o.why)}. The storeys, height and floor area in this memo are the option's own figures, not permitted ones; answer 3 names who reads the schedule.</p>`;
  // each finding cites the rule it came from (A1, its title), so a CD-1 site shows its own by-law's rules (17 Nov 2026)
  // a Fail here is against the district's own limits, without a rezoning; on an approved scheme it read as "failed"
  // (24 Nov 2026, critique), so the heading says what the limits are and what replaces them when a rezoning is proposed
  const outSub = `Outright under ${h(district)} <span class="cont">· the limits without a rezoning${approved ? "; the rezoning below, approved, sets them now" : proposes && outLines.some(r => r.status === "fail") ? "; going past them is what the rezoning below is for" : ""}</span>`;
  if (outLines.length) {
    body += `<p class="path ans-sub">${outSub}</p>
      <ul class="finding-list rule-list">${outLines.map(r => ruleItem(r, `${leadCont(r.finding)} <span class="cont">(${h(r.title)})</span>`)).join("")}</ul>`;
  } else if (!o.why) body += `<p class="path ans-sub">${outSub}</p>`;
  if (path) {
    // a rezoning Council has approved is said as decided (25 Nov 2026, the funder-side reader)
    body += `<p class="path ans-sub">${approved ? `By rezoning, approved by Council${approvedOn ? ` on ${h(approvedOn)}` : ""}` : proposes ? "By rezoning" : "Approval route, no rezoning"}: ${h(path)}${approved ? ` <span class="cont">· it sets the limits now${policy.length ? "; what the City's rules still read of the scheme is listed below" : ""}</span>` : ""}</p>`;
    if (policy.length) body += `<ul class="finding-list rule-list">${policy.map(r => ruleItem(r, `<span class="title">${h(r.title)}:</span> <span class="cont">${h(r.finding)}</span>`)).join("")}</ul>`;
  } else {
    // "allowed outright" only where the outright answer says so (25 Nov 2026: a permit route on a lot whose yards leave
    // no plate read "Allowed outright" under "Outright: not yet confirmed"); else the route's own reason
    const outOk = ["yes", "yes, with conditions"].includes(o.verdict);
    const said = !notNeeded ? "No rezoning path stated"
      : discretion ? "Within what the Director of Planning may allow; no rezoning is proposed or needed"
      : outOk ? "Allowed outright; no rezoning is proposed or needed"
      : `No rezoning proposed: ${bz.why || "the option names another approval route"}`;
    body += `<p class="path ans-sub">${h(said)}</p>`;
  }
  const status = verdictStatus(proposes ? bz.verdict : o.verdict);   // the operative answer: by rezoning when a path is stated
  // the figures worker's drawing of outright against proposed (figures/envelope.js, envelopeFigure(run)) goes here
  const drawing = run ? envelopeFigure(run) : "";
  return `<section class="card answer" data-verdict="${h(status)}">
    <h2><span class="badge">1</span> Is it allowed?</h2>
    <p class="verdict">${verdict}</p>
    ${routesHtml(ans.allowed)}
    ${drawing}
    ${body}
  </section>`;
}

/* The funders' answer in words that do not read as money (20 Nov 2026: "Fits the funders: Yes" stood beside a $20.2M
   gap and a cancelled call): the programs' published criteria are met, or not; whether the money closes is answer 4.
   The verdict sentence takes the engine's own words (summary.answers.funded.words, engine.funders_words: "Passes this
   screen's eligibility checks for the Community Housing Fund and BC Builds"); a cell or a mark takes the short form
   below, which keeps the same verb, so the funders' answer has one wording everywhere (24 Nov 2026). */
export const FUNDED_WORD = { yes: "Passes the screen", "yes, with conditions": "Passes the screen, with conditions", no: "Does not pass the screen", "not yet confirmed": "Screen not yet confirmed", "not assessed": "Not assessed" };
export function fundedWord(f, long = false) {
  const own = long && f && typeof f.words === "string" && f.words ? f.words : null;
  return own ? cap(own) : FUNDED_WORD[f && f.verdict] || cap((f && f.verdict) || "");
}
/* Whether the programs targeted are taking proposals (summary.answers.funded.intake, engine.funders_words: one entry per
   program whose rule records it, {program, open, note}): a closed or unknown intake is said beside the verdict, in the
   engine's words; an open one says nothing more. */
export function intakeNote(f) {
  const list = f && Array.isArray(f.intake) ? f.intake : [];
  return list.filter(x => x && x.open !== true && x.note).map(x => `${cap(String(x.note).replace(/\.$/, ""))}.`).join(" ");
}

/* The money's verdict in a short phrase, for the funders' answer and the comparison: "Needs more sources: a $20.2M gap,
   44% of the cost". */
export function moneyPhrase(pf) {
  if (!pf || !pf.available) return "";
  const g = pf.gap || {};
  return `${moneyWord(pf.verdict || {})}${g.value != null ? `: ${g.value > 0 ? `a ${millionsOf(g.value)} gap${g.share_of_capital != null ? `, ${Math.round(g.share_of_capital * 100)}% of the cost` : ""}` : g.value < 0 ? `${millionsOf(-g.value)} of headroom` : "no gap"}` : ""}`;
}

export function answerFunders(L, run = null) {
  const res = L.results, ans = L.summary.answers, opt = L.inputs.option;
  const targets = new Set(opt.target_programs || []);
  // the programs whose criteria the rules test; the ones only listed (check program_match) follow as doors to knock on
  const rows = res.filter(r => r.layer === "E" && r.check !== "program_match" && (!targets.size || targets.has(r.rule_id)));
  const others = res.filter(r => r.layer === "E" && r.check !== "program_match" && targets.size && !targets.has(r.rule_id));
  const doors = ((ans.funded || {}).matches || []).filter(m => !m.ended);
  let body = `<ul class="finding-list rule-list">${rows.map(r => ruleItem(r, `<span class="title">${h(r.title)}:</span> <span class="cont">${h(withoutRepeat(r.title, r.finding))}</span>`)).join("")}</ul>`;
  const intake = intakeNote(ans.funded);
  if (intake) body = `<p class="finding intake-note">${leadCont(intake)}</p>` + body;
  // the criteria are not the money: say where the money stands, beside them
  const pf = run && run.proforma && run.proforma.available ? run.proforma : null;
  if (pf) body += `<p class="finding money-link"><span class="lead">The criteria are not the money.</span> <span class="cont">Answer 4: ${h(moneyPhrase(pf))}.</span></p>`;
  if (others.length) body += `<p class="path" style="margin-top:12px">Not targeted, listed in the ledger: ${others.map(r => h(r.title)).join("; ")}.</p>`;
  if (doors.length) {
    const up = s => String(s || "").charAt(0).toUpperCase() + String(s || "").slice(1);
    body += `<p class="path ans-sub">Other programs written for this kind of housing · listed from their own pages, not tested</p>
      <ul class="finding-list door-list">${doors.map(m => `<li><span class="fl-marks">${refTagOf(m.rule_id).trim()}${m.open === false ? ' <span class="ph-tag">no intake open</span>' : ""}</span><span><span class="title">${h(up(m.program))}${m.if && m.if.length ? ` <span class="cont">· if the housing is ${h(m.if.join(" and "))}</span>` : ""}:</span> <span class="cont">${h(m.what || "")}. A project enters ${h(m.enters || "in a way its page does not state")}.${m.intake ? ` ${h(up(String(m.intake).replace(/\.$/, "")))}.` : ""}${m.differs ? ` Its homes are all rent geared to income; this option has ${h(m.differs.market_units)} at market rent.` : ""}</span></span></li>`).join("")}</ul>`;
  }
  // what the answer covers, in the engine's words: a short list of programs is a limit of the tool, not of the project
  if (ans.funded.scope) body += `<p class="path funders-scope">${h(ans.funded.scope)}</p>`;
  // the homes the first layout does not place are counted by the funders' checks all the same: said beside the verdict
  const lay = run && run.layout;
  if (lay && lay.units_total && (lay.units_placed || 0) < lay.units_total) body = `<p class="finding intake-note">${leadCont(`The first layout places ${lay.units_placed} of ${lay.units_total} homes on the plates as drawn (answer 3); this answer counts all ${lay.units_total}.`)}</p>` + body;
  return `<section class="card answer" data-verdict="${h(verdictStatus(ans.funded.verdict))}">
    <h2><span class="badge">2</span> Does it fit the funders?</h2>
    <p class="verdict"><em>${h(fundedWord(ans.funded, true))}.</em></p>
    ${body}
  </section>`;
}

/* The rules in this memo whose figures were not read from their document (source.verified false), counted over the
   rules that apply here; one line near the answers says so (20 Nov 2026). Pure. */
export const unverifiedRules = L => ((L && L.results) || []).filter(r => r.status !== "not_applicable" && r.source && r.source.verified === false);
export function unverifiedLine(L) {
  const u = unverifiedRules(L);
  if (!u.length) return "";
  return `<p class="unverified-line"><span class="unverified">unverified</span> ${u.length === 1 ? "1 rule in this memo is" : `${u.length} rules in this memo are`} not yet checked against ${u.length === 1 ? "its" : "their"} source (marked UNVERIFIED): ${h(u.map(r => `${refOf(r.rule_id) ? `${refOf(r.rule_id)} ` : ""}${fewWords(r.title)}`).join("; "))}.</p>`;
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
  // the floor area the rules test against the floor area the plans draw (25 Nov 2026; twin of memo.layout_open_items)
  const tot = lay.totals || {}, tested = Number(tot.gfa_tested_m2), drawn = ((lay.area_schedule || {}).totals || {}).gross_m2;
  if (tested && drawn != null && tested - drawn > Math.max(10, 0.05 * tested)) {
    const why = [];
    if (tot.plates_m2 != null && tested - tot.plates_m2 > 1) why.push(`the plates the yards leave hold ${fmtNum(Math.round(tot.plates_m2))} m²`);
    if (tot.void_m2) why.push(`${fmtNum(Math.round(tot.void_m2))} m² of the plates is open: a yard, a courtyard or a cut-out`);
    out.push({ title: "Floor area drawn under the floor area tested", status: "conditional",
      action: `Architect: the rules test ${fmtNum(Math.round(tested))} m² of floor area; the first plans draw ${fmtNum(Math.round(drawn))} m²${why.length ? ` (${why.join("; ")})` : ""}. Draw the plan to the floor area tested, or lower the floor area the option states: the FSR test, the hard cost and the funders read the option's figure.` });
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
    if (eg.ground_oriented) {
      // homes with their own doors have no core to move (25 Nov 2026: "Move or add a core" on a plan with none)
      out.push({ rule_id: eg.rule_id, title: "Exits: the upper homes' own stairs (BC Building Code, Part 9)", status: eg.status,
        action: `Architect: on ${bad.length} of ${(eg.floors || []).length} floors a home is reached by its own stair above the ground floor. ${eg.summary || ""} Draw each stair and its exit and confirm them against Part 9 (9.9.9, egress from dwelling units), which the rules do not hold.` });
    } else out.push({ rule_id: eg.rule_id, title: "Exits: travel distance, separation and dead ends (BC Building Code)", status: eg.status,
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
  // manager's, who carries the memo (17 Nov 2026: a "—" under Who beside "Each names who resolves it"); lanes.js
  // reads the same names for the drawing above the table
  const who = whoOf;
  const todo = u => todoOf(u) || "—";
  // who resolves what, drawn: a lane per person, the site's facts, then the design, then the funders (20 Nov 2026)
  const lanes = n ? lanesHtml(items, refOf) : "";
  const table = n ? `${lanes}<table class="plain open-items"><thead><tr><th>Ref</th><th>Item</th><th>Status</th><th>Who</th><th>What to do</th></tr></thead><tbody>
    ${items.map(u => `<tr><td data-k="Ref">${refOf(u.rule_id) ? `<b class="ref" title="${h(u.title)}">${h(refOf(u.rule_id))}</b>` : "—"}</td><td data-k="Item">${h(u.title)}</td><td class="status" data-k="Status">${pill(u.status)}</td><td class="who" data-k="Who">${h(who(u))}</td><td class="todo" data-k="What to do"><span class="measure">${h(todo(u))}</span></td></tr>`).join("")}
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
// a loss reads −$52,880 and nothing reads $-0 (25 Nov 2026: "$-2,753,356" and "$-0" on the operating table)
export const money = x => { if (x === null || x === undefined) return "not given"; const r = Math.round(x) || 0; return r < 0 ? `−$${fmtNum(-r)}` : `$${fmtNum(r)}`; };

/* A source's short name for a table cell: the publisher and the document up to the first comma or semicolon. */
const shortSource = s => { const t = String((s && s.title) || (s && s.url) || ""); const cut = t.split(/[;(]/)[0]; return (cut.length > 72 ? cut.slice(0, 70).replace(/\s+\S*$/, "") + "…" : cut).trim(); };

/* How a verdict is worded and what it asks of the development manager (17 Nov 2026, Kai: "Unlikely" read as "will not
   be funded"; a gap past the screen's line is the cue to look for more sources, so it reads Conditional, not Fail).
   The key stays the engine's; proforma.VERDICT_WORDS and proforma.next_step say the same in the memo file. */
export const MONEY_STATUS = { likely: "pass", unlikely: "conditional", unsure: "uncertain" };
// checks.HOUSING_WORDS, for the money's next step
const HOUSING_WORD = { supportive: "supportive housing", transitional: "transitional housing", shelter: "a shelter", independent: "independent rental housing" };
export const MONEY_WORD = { likely: "Likely", unlikely: "Needs more sources", unsure: "Unsure" };
export const moneyWord = v => MONEY_WORD[v.word] || cap(v.word);
export function moneyNext(pf) {
  const v = pf.verdict || {}, gap = (pf.gap || {}).value, c = pf.capital || {}, homes = (pf.inputs || {}).units_total;
  // rents that do not cover the running costs: the operating funder comes before the capital (proforma.OPERATING_FUNDER)
  // written for whoever reads the memo, on screen or on paper (24 Nov 2026: "run again" spoke to a board as an operator)
  const page = (pf.operating || {}).page || {};
  if (v.operating_shortfall) return "Find who pays to run it before the capital: an operating agreement or subsidy (for supportive, transitional or shelter housing, the staffing as well), then a revised memo with the project's own rents, running costs and subsidy." + (page.own_figures ? "" : " Until they are entered, the rents and the running cost are placeholders.");
  // supportive, transitional and shelter housing reach capital by a program's own route (proforma.PROGRAM_ROUTE)
  if (page.housing_type && page.housing_type !== "independent" && (v.word === "unlikely" || v.word === "unsure")) return `For ${HOUSING_WORD[page.housing_type] || page.housing_type}, the capital comes by the program's own route (answer 2 says how a project enters each, and what each pays for): settle that route, who operates the building and the operating agreement first. The gap here is what a society would face outside that route.`;
  if (v.word === "unlikely") return "Look for more sources as well: other grants (answer 2 lists the programs and whether each is taking proposals; a municipal grant, a capital campaign or a foundation), more equity, a land contribution or a partner. A revised memo counts what is found as other grants or equity.";
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

/* The stack's caption: what the drawing is, in a sentence. */
export function moneyCaption(pf) {
  const g = pf.gap || {};
  return `What it costs against what pays for it, drawn to one scale. ${g.value > 0 ? `The hatched part is the gap, ${h(millionsOf(g.value))} not yet found; ` : ""}the amber line is 15% of the cost below the top.`;
}

/* Land at $0, the 15% line and the 1.10 coverage, each in a plain sentence with this memo's figures (20 Nov 2026: a
   board reader listed all three as words they did not understand). */
export function moneyWords(pf, run = null, tag = "p") {
  const c = pf.capital || {}, f = pf.funding || {}, d = f.debt || {}, o = pf.operating || {}, g = pf.gap || {};
  const line = key => (pf.lines || []).find(l => l.key === key) || {};
  const ref = id => (id && refOf(id) ? ` (${refOf(id)})` : "");
  const out = [];
  const land = line("land");
  if (c.land === 0) {
    const why = String(land.note || "").replace(/^\$?0?\s*,?\s*nominal\s*[:,;]?\s*/i, "").trim();
    out.push(`Land is carried at $0${ref(land.rule_id)}: ${why ? `${why.replace(/\.$/, "")}, so` : "the owner leases or transfers it at a nominal value, so"} it adds nothing to the cost.`);
  } else if (c.land == null) out.push("Land is not priced: no figure was entered and the owner is not one that leases at a nominal value, so the cost leaves it out until it is entered.");
  if (c.total) {
    const share = g.share_of_capital != null ? Math.round(g.share_of_capital * 100) : null;
    // said by size, not by up and down (24 Nov 2026: "stays above it" read as "more than" beside a verdict that said
    // the gap was more than the line)
    out.push(`The amber line is this tool's screening line, drawn 15% of the cost (${millionsOf(c.total * SCREEN_SHARE)} here) down from the top: a gap no larger than that is one the screen calls close${g.value > 0 && share != null ? `; this gap is ${share}% of the cost, ${share > 15 ? "larger, so the project needs more sources before design money is spent" : "within it"}` : g.value != null && g.value <= 0 ? "; there is no gap" : ""}. It is the screen's own line, not a funder's rule.`);
  }
  if (d.supportable != null && d.dcr != null) {
    out.push(`Debt is what the rent can carry: a lender asks that the rent left after running costs cover the yearly mortgage payment ${Number(d.dcr).toFixed(2)} times (CMHC's coverage ratio), so ${money(o.noi)} a year carries ${money(d.supportable)} at ${d.rate_pct}% over ${d.amortization_years} years${ref((line("debt") || {}).rule_id)}.`);
  }
  if (!out.length) return "";
  return tag === "p" ? `<p class="path money-words">${h(out.join(" "))}</p>` : out.join(" ");
}

/* The operating page: what runs the building a year, and the subsidy it needs (proforma.operating_rows is the twin;
   both read proforma.operating.page). Income, costs, what is left, then the two figures a funder reads. Pure. */
const FROM_WORD = { entered: "entered", placeholder: "placeholder", rule: "the rules' figure" };
export function operatingRows(pf) {
  const p = pf && pf.operating && pf.operating.page;
  if (!p || p.gross == null) return [];
  const homes = (pf.inputs || {}).units_total || 0, usd = x => `$${Math.round(x).toLocaleString("en-CA")}`;
  const rows = [];
  for (const t of p.tiers || []) {
    if (!t.homes) continue;
    rows.push({ label: `${t.label}, ${t.homes} homes`, value: t.rent_year, note: `${t.rent_month_per_home != null ? `${usd(t.rent_month_per_home)} a month a home` : "no rent figure"} (${FROM_WORD[t.from] || t.from})`, kind: "income", ph: t.from === "placeholder" });
  }
  // the twin of proforma.operating_rows (25 Nov 2026: the vacancy's own basis, the non-residential income, what the
  // subsidy leaves, the named loans' payments, one figure per place where beds stand beside homes)
  rows.push({ label: "Vacancy", value: -(p.vacancy || 0), note: `${p.vacancy_rate != null ? `${(p.vacancy_rate * 100).toFixed(1)}%, ` : ""}${p.vacancy_from === "entered" ? "entered, on all tiers" : "the CMHC survey's rate, on all tiers"}`, kind: "cost" });
  // the beds beside homes are in the figure, and the note says so (25 Nov 2026; twin of proforma.operating_rows)
  const bedsNote = p.beds_operating_cost != null && p.beds ? `; and ${p.beds} beds at ${usd(p.beds_cost_per_bed)} a bed a year (${p.beds_cost_from === "entered" ? "entered" : "a home’s figure"})` : "";
  rows.push({ label: "Operating cost", value: p.operating_cost != null ? -p.operating_cost : null, note: (p.operating_cost_per_home != null ? `${usd(p.operating_cost_per_home)} a home a year (${FROM_WORD[p.operating_cost_from] || ""})` : "not entered: enter the operator's running cost per bed") + bedsNote, kind: "cost", ph: p.operating_cost_from === "placeholder", warn: p.operating_cost == null });
  rows.push({ label: "Replacement reserve", value: -(p.reserve || 0), note: p.beds_operating_cost != null && p.beds ? `with ${Math.ceil(p.beds / 4)} sleeping rooms of four beds, each held like a home` : "", kind: "cost" });
  rows.push({ label: "Support staffing", value: p.support_staffing != null ? -p.support_staffing : null, note: p.support_staffing != null ? "entered" : (p.staffing_missing ? "not entered, and this kind of housing runs on it" : ""), kind: "cost", warn: !!p.staffing_missing });
  if (p.nonres_income) rows.push({ label: "Income from the floors that are not homes", value: p.nonres_income, note: "entered: rent or a contribution to running costs", kind: "income" });
  rows.push({ label: "Left after running costs", value: p.net_before_subsidy, note: "before any operating subsidy or loan payment", kind: "result" });
  if (p.subsidy) {
    rows.push({ label: "Operating subsidy entered", value: p.subsidy, note: `${p.subsidy_source ? `${p.subsidy_source}; ` : ""}${p.subsidy_confirmed ? "confirmed" : "not yet confirmed"}`, kind: "income", warn: !p.subsidy_confirmed });
    rows.push({ label: "Left after the subsidy", value: p.net_after_subsidy, note: "what the subsidy entered leaves, before any loan payment", kind: "result" });
  }
  if (p.named_loan_service) rows.push({ label: "Payments on the named loans", value: -p.named_loan_service, note: "the capital sources entered as loans, each at its own terms", kind: "cost" });
  rows.push({ label: "Loan payment", value: -(p.debt_service || 0), note: "on the mortgage the funding counts", kind: "cost" });
  if (p.subsidy_to_run == null) rows.push({ label: "Subsidy needed to run it", value: null, note: "not given: the support staffing is not entered, so what running it costs is not known", kind: "ask", warn: true });
  else {
    const per = [];
    if (p.subsidy_to_run_per_home_month != null && homes) per.push(`${usd(p.subsidy_to_run_per_home_month)} a home a month over ${homes} homes`);
    if (p.beds && p.subsidy_to_run_per_bed_month != null) per.push(`${usd(p.subsidy_to_run_per_bed_month)} a bed a month over ${p.beds} beds`);
    if (p.subsidy_to_run_per_place_month != null) per.push(`${usd(p.subsidy_to_run_per_place_month)} a month for each of its ${homes + p.beds} places (${homes} homes and ${p.beds} beds): the building's whole need, shared over its places, not the shelter's alone`);
    rows.push({ label: "Subsidy needed to run it", value: p.subsidy_to_run, note: `${p.subsidy_to_run ? (per.length ? per.join("; ") + "; " : "") : "none: the rents cover the running costs; "}before any loan payment`, kind: "ask" });
  }
  const f = p.if_gap_financed;
  if (f) rows.push({ label: "Subsidy needed if the capital still missing were borrowed", value: f.subsidy_year, note: `${usd(f.per_home_month)} a home a month: the payment on ${usd(f.loan)} at ${f.rate_pct}% over ${f.amortization_years} years is ${usd(f.annual_payment)} a year. An illustration on this screen's mortgage terms, not a funder's financing`, kind: "ask" });
  const t = f && f.on_program_terms;
  if (t) rows.push({ label: `The same, on ${t.program}' published take-out terms`, value: t.subsidy_year, note: `${usd(t.per_home_month)} a home a month: ${t.rate_pct}% over ${t.amortization_years} years is ${usd(t.annual_payment)} a year. The program's page gives the rate; whether this project gets that loan is the program's to say`, kind: "ask" });
  return rows;
}
export function operatingTable(pf) {
  const rows = operatingRows(pf);
  if (!rows.length) return "";
  const body = rows.map(r => `<tr class="op-${h(r.kind)}"><th scope="row">${h(r.label)}</th><td class="num">${r.value == null ? (r.warn ? "not entered" : "none") : h(r.value < 0 ? `−${money(-r.value)}` : money(r.value))}</td><td class="cont"><span class="measure">${h(r.note)}${r.ph ? ' <span class="ph-tag">placeholder</span>' : ""}${r.warn ? ' <span class="ph-tag">open</span>' : ""}</span></td></tr>`).join("");
  return `<details class="pf-lines op-page" open><summary>What it takes to run, a year <span class="cont">· the rents, the running costs and the subsidy needed</span></summary>
      <table class="plain op-table"><thead><tr><th scope="col">Line</th><th scope="col" class="num">A year</th><th scope="col">Note</th></tr></thead><tbody>${body}</tbody></table>
      <p class="cont">${(pf.operating.page || {}).own_figures ? "The rents and the running cost are the operator's own, as entered" : "The rents and the running cost are placeholders until the operator's own are entered"}; support staffing and an operating subsidy are never assumed. A funder compares the subsidy a home a month, or a bed a month for a shelter.</p>
    </details>`;
}

/* Where the money comes from, each source with its status (25 Nov 2026): the contributions ledger the engine writes in
   proforma.funding.sources; the words are proforma.CONTRIBUTION_STATUS_WORDS. */
export const CONTRIBUTION_WORD = { committed: "committed", applied: "applied for", assumed: "assumed", illustrative: "illustrative: nobody has offered it",
  entered: "entered, status not given", sized: "sized by this screen", "in kind": "in kind", "not counted": "not counted", "to find": "to find" };
// a row outside the funding total says so, unless its status already does
export const outOfTotal = r => !r.counted && !["not counted", "to find"].includes(r.status);
const CONTRIBUTION_ST = { committed: "pass", applied: "conditional", assumed: "uncertain", illustrative: "uncertain", entered: "info", sized: "info", "in kind": "info", "not counted": "na", "to find": "fail" };
export function sourcesTable(pf) {
  const rows = ((pf || {}).funding || {}).sources || [];
  if (!rows.length) return "";
  return `<details class="pf-lines src-page" open><summary>Where the money comes from <span class="cont">· each source with its status</span></summary>
      <table class="plain src-table"><thead><tr><th scope="col">Source</th><th scope="col" class="num">Amount</th><th scope="col">Status</th></tr></thead><tbody>
      ${rows.map(r => `<tr class="src-${h(r.kind)}${r.counted ? "" : " src-out"}"><th scope="row">${h(r.label)}</th><td class="num">${h(money(r.value))}</td><td><span class="src-st" data-st="${h(CONTRIBUTION_ST[r.status] || "")}">${h(CONTRIBUTION_WORD[r.status] || r.status)}</span>${outOfTotal(r) ? ' <span class="cont">· not in the funding total</span>' : ""}</td></tr>`).join("")}
      </tbody></table>
      <p class="cont">Name a source and its status at 03 ("Capital sources"); a stack that closes only with sources not yet committed reads Unsure.</p>
    </details>`;
}

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
    return `<tr><td>${h(ln.label)}</td><td class="num">${h(shown(ln))}</td><td>${from}${ln.placeholder ? ' <span class="ph-tag">placeholder</span>' : ""}</td><td class="cont"><span class="measure">${h(ln.note || "")}</span></td></tr>`;
  }).join("");
  // the stack drawn beside the four figures, then the three things a board reader asked about, in plain words
  const stack = stackFigure([stackOf(pf)], { H: 220, lh: 15 }, moneyCaption(pf));
  const body = `${next ? `<p class="finding money-next"><span class="cont">For the development manager:</span> ${leadCont(next)}</p>` : ""}
    <div class="money-draw">${stack}
    <dl class="pf-four">
      <div><dt>Capital cost</dt><dd><b>${h(money(c.total))}</b><span class="cont">hard ${h(money(c.hard))} (escalated ×${h(c.escalation)}), soft ${h(money(c.soft))}, contingency ${h(money(c.contingency))}, land ${h(money(c.land))}</span></dd></div>
      <div><dt>Net operating income</dt><dd><b>${h(money(o.noi))} a year</b><span class="cont">rent ${h(money(o.gross))} less vacancy, operating cost and reserve</span></dd></div>
      <div><dt>Funding</dt><dd><b>${h(money(f.total))}</b><span class="cont">grants ${h(money(grants))}, equity ${h(money(f.equity))}, debt ${h(money(f.debt.supportable))} at ${h(f.debt.rate_pct)}% over ${h(f.debt.amortization_years)} years, ${h(Number(f.debt.dcr).toFixed(2))} coverage${pf.inputs && pf.inputs.units_total ? `; ${h(pf.inputs.units_total)} homes as entered${run.layout && run.layout.units_placed != null && run.layout.units_placed < pf.inputs.units_total ? ` (${h(run.layout.units_placed)} fit the plate: answer 3)` : ""}` : ""}</span></dd></div>
      <div><dt>Gap</dt><dd><b>${h(money(g.value))}</b><span class="cont">${g.share_of_capital != null ? `${h(Math.round(g.share_of_capital * 100))}% of the capital cost; a negative gap is headroom` : ""}</span></dd></div>
    </dl></div>
    ${moneyWords(pf, run)}
    ${v.unsure && v.unsure.length ? `<p class="path">Left to a person: ${h(v.unsure.join("; "))}.</p>` : ""}
    ${v.why.length > 1 ? `<p class="path">${h(v.why.slice(1).map(w => w[0].toUpperCase() + w.slice(1) + ".").join(" "))}</p>` : ""}
    ${sourcesTable(pf)}
    ${operatingTable(pf)}
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
