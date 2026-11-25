/* The memo's front sheet, shaped as an ask (25 Nov 2026; all four first-panel reviewers: "who is housed, who operates,
   which program, the amount, the top three risks"), and answer 1's three verdicts. frontOf is the twin of
   memo.front_sheet in the engine; it reads the ledger, the pro-forma and the layout and adds no figure of its own. */

import { cap, h, pill } from "../core/util.js";
import { layoutOpenItems, moneyWord, MONEY_STATUS } from "./answers.js";

const HOUSING = { supportive: "supportive housing", transitional: "transitional housing", shelter: "a shelter" };
const TIERS = [["market", "at market rent"], ["rgi", "rent geared to income"], ["deep_subsidy", "deep subsidy"]];
const RANK = { fail: 0, uncertain: 1, conditional: 2 };

/* Dollars as a board reads them: $45.7M, $890,295. */
export function cad(x) {
  if (x == null) return "not computed";
  return Math.abs(x) >= 1e6 ? `$${(x / 1e6).toLocaleString("en-CA", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}M` : `$${Math.round(x).toLocaleString("en-CA")}`;
}

/* engine.program_name: the rule title before its colon, less "BC Housing" and a bracket. */
function programName(r) {
  let n = String(r.title || r.rule_id || "").split(":")[0].replace(/\s*\(.*?\)\s*/g, " ").trim().replace(/^BC Housing\s+/, "");
  return /(fund|program|programme|initiative)$/i.test(n) ? `the ${n}` : n;
}

/* checks.housing_kind */
function kindOf(o) {
  const k = String(o.housing_type || "").trim().toLowerCase();
  if (["independent", "supportive", "transitional", "shelter"].includes(k)) return k;
  const total = Object.values(o.units || {}).reduce((a, v) => a + (Number(v) || 0), 0);
  return total && Number(o.supportive_units || 0) >= total ? "supportive" : "independent";
}

export function frontOf(run) {
  const L = run.ledger, o = L.inputs.option || {}, ans = L.summary.answers, pf = run.proforma;
  const kind = kindOf(o);
  const homes = Object.values(o.units || {}).reduce((a, v) => a + (typeof v === "number" ? v : 0), 0);
  const beds = typeof o.beds === "number" && o.beds > 0 ? o.beds : null;
  const head = (homes ? `${homes} home${homes === 1 ? "" : "s"}` : "") + (beds ? `${homes ? " and " : ""}${beds} beds` : "");
  let housed = `${head || "No homes entered"}, ${kind === "independent" ? "independent rental" : HOUSING[kind]}`;
  if (o.tenure) housed += ` (${String(o.tenure).replace(/_/g, " ")})`;
  const sup = Number(o.supportive_units || 0);
  if (sup && kind === "independent") housed += `, ${sup} of them supportive homes`;
  const t = o.rent_tiers_units || {};
  if (TIERS.some(([k]) => t[k])) housed += ": " + TIERS.filter(([k]) => t[k]).map(([k, w]) => `${t[k]} ${w}`).join(", ");
  const ops = o.operations || {}, signed = ops.signed && typeof ops.signed === "object" ? ops.signed : null;
  const op = String(o.operator || "").trim();
  const operator = (op || "Not named") + (signed && signed.by ? `; the operating figures are signed by ${signed.by}` : op ? "; the operating figures are not signed by an operator" : "");
  const targets = o.target_programs || [];
  const named = L.results.filter(r => r.layer === "E" && targets.includes(r.rule_id)).map(programName);
  const fd = ans.funded || {};
  let programs;
  if (named.length) programs = named.join(", ") + (fd.words ? `. ${fd.words}` : "");
  else {
    const doors = (fd.matches || []).filter(m => !m.ended && !(m.if || []).length).map(m => m.program);
    programs = doors.length ? `None targeted; written for this kind of housing and not tested: ${doors.join(", ")}` : "None targeted";
  }
  let money = null;
  if (pf && pf.available) {
    const rows = (pf.funding || {}).sources || [];
    const gap = (pf.gap || {}).value;
    money = { capital: (pf.capital || {}).total, asked: rows.filter(r => r.counted && ["illustrative", "applied", "assumed"].includes(r.status)).map(r => ({ label: r.label, value: r.value, status: r.status })),
      to_find: gap != null && gap > 0 ? gap : gap != null ? 0 : null, share: (pf.gap || {}).share_of_capital,
      surplus: gap != null && gap < 0 ? -gap : null, verdict: (pf.verdict || {}).word };
  }
  const rts = (ans.allowed || {}).routes;
  const verdicts = rts ? Object.values(rts).map(v => ({ label: v.label, verdict: v.verdict }))
    : [{ label: "Outright", verdict: ans.allowed.outright.verdict }, { label: "By rezoning", verdict: ans.allowed.by_rezoning.verdict }];
  verdicts.push({ label: "The funders' criteria", verdict: fd.words || fd.verdict });
  if (money) verdicts.push({ label: "The money", verdict: moneyWord(pf.verdict) });
  const items = [...(ans.unsure || []), ...layoutOpenItems(run)];
  const top = items.map((u, i) => [u, i]).sort((a, b) => (RANK[a[0].status] ?? 3) - (RANK[b[0].status] ?? 3) || a[1] - b[1]).slice(0, 3)
    .map(([u]) => ({ title: u.title, status: u.status, action: u.action || "" }));
  return { housed, operator, programs, money, decision: String(o.decision_sought || "").trim() || null, verdicts, open_items: top, open_total: items.length };
}

/* A route's verdict as a status, for its mark. */
const ROUTE_STATUS = { yes: "pass", "yes, with conditions": "conditional", no: "fail", "not yet confirmed": "uncertain", "not assessed": "uncertain",
  possible: "conditional", "not needed": "na", "none in the schedule": "na", needed: "conditional" };
export const routeStatus = v => ROUTE_STATUS[v] || "";

export function amountWords(m) {
  if (!m) return "Not computed.";
  const ask = m.asked.map(a => `${a.label}, ${cad(a.value)} (${a.status})`).join("; ") || "nothing from a program";
  return `Capital cost ${cad(m.capital)}. Asked: ${ask}. ` + (m.to_find ? `Still to find: ${cad(m.to_find)}${m.share != null ? ` (${Math.round(m.share * 100)}% of the cost)` : ""}.`
    : m.surplus ? `The sources counted cover it, ${cad(m.surplus)} to spare.` : "The sources counted cover it.");
}

/* The front sheet on screen: the first card of the memo in every layout. */
export function frontHtml(run) {
  const f = frontOf(run);
  const row = (k, v) => `<div><dt>${h(k)}</dt><dd>${v}</dd></div>`;
  const marks = f.verdicts.map(v => `<li><span class="ask-k">${h(v.label)}</span> <b class="ask-v" data-st="${h(routeStatus(v.verdict) || (v.label === "The money" ? MONEY_STATUS[(run.proforma.verdict || {}).word] || "" : ""))}">${h(cap(String(v.verdict || "")))}</b></li>`).join("");
  const open = f.open_items.length ? `<ol class="ask-open">${f.open_items.map(u => `<li>${pill(u.status)} <span>${h(u.title)}</span></li>`).join("")}</ol>${f.open_total > f.open_items.length ? `<p class="cont">${f.open_total - f.open_items.length} more in answer 3.</p>` : ""}` : `<p class="cont">Nothing open.</p>`;
  return `<section class="card memo-ask" aria-labelledby="ask-h">
    <h2 id="ask-h">The ask</h2>
    <dl class="ask-dl">
      ${row("Who is housed", h(f.housed))}
      ${row("Who operates", h(f.operator))}
      ${row("Which program", h(f.programs))}
      ${row("The amount", h(amountWords(f.money)))}
      ${row("The decision wanted", f.decision ? h(f.decision) : `<i>not stated</i> <span class="cont">· at 03, "What are you asking for?"</span>`)}
      ${row("The answers", `<ul class="ask-verdicts">${marks}</ul>`)}
      ${row(f.open_items.length ? `The top ${f.open_items.length} of ${f.open_total} open items` : "Open items", open)}
    </dl>
  </section>`;
}

/* Answer 1's three verdicts, under its verdict line. */
export function routesHtml(allowed) {
  const r = allowed && allowed.routes;
  if (!r) return "";
  return `<ul class="routes">${Object.values(r).map(v => `<li data-st="${h(routeStatus(v.verdict))}"><span class="ask-k">${h(v.label)}</span> <b>${h(cap(v.verdict))}</b>${v.why ? ` <span class="cont">· ${h(v.why)}</span>` : ""}</li>`).join("")}</ul>`;
}
