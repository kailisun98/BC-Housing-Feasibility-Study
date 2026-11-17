/* The paper memo, loaded on first use: a self-contained layout of the memo for a reviewer, used by Download PDF and
   Print. Every rule is referred to as A1â€¦E4. */

import { cap, fmtNum, h, setStatus, STATUS_WORD, todayISO, verdictStatus } from "./core/util.js";
import { state, STATIC } from "./core/state.js";
import { optWord } from "./fields.js";
import { rev } from "./runs.js";
import { compareKind, idBreak, optionName, refOf } from "./memo/memo.js";
import { layoutOpenItems, money, MONEY_STATUS, moneyNext, moneyWord } from "./memo/answers.js";
import { splitValues, withPlans } from "./memo/clauses.js";
import { tradeOff } from "./memo/side-by-side.js";
import { changeWord, shortName } from "./memo/changes.js";
import { siteContext } from "./figures/common.js";
import { figPlan } from "./figures/plan.js";
import { figSection } from "./figures/section.js";
import { massLine } from "./figures/cards.js";

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
export function paperDocument(run) {
  // the exits as the plans found them, the same on paper as on screen (withPlans)
  const L = run.ledger, res = withPlans(L.results, run), ans = L.summary.answers;
  const site = L.inputs.site || {}, opt = L.inputs.option || {};
  const st = L.run.stamp, d = run.diff, B = d && run.compareLedger ? run.compareLedger : null;
  const kind = d ? compareKind(d) : null;
  const revA = rev(run.run_id), revB = state.compareRun ? rev(state.compareRun) : "an earlier memo";
  const address = site.address || site.id || "";
  const issued = todayISO();

  // references: the layer's letter and the rule's place in it, in the ledger's order
  const refOf = {}, titleOf = {}, n = {};
  for (const r of res) { n[r.layer] = (n[r.layer] || 0) + 1; refOf[r.rule_id] = `${r.layer}${n[r.layer]}`; titleOf[r.rule_id] = r.title; }
  const ref = id => refOf[id] || id;
  const refTag = id => `<b class="ref">${h(ref(id))}</b>`;
  // sources, numbered in the order the rules cite them, then the site's and the option's own
  const srcNo = new Map(), sources = [];
  const addSrc = s => {
    if (!s || (!s.title && !s.url)) return null;
    const k = `${s.title || ""}|${s.url || ""}`;
    if (!srcNo.has(k)) { srcNo.set(k, sources.length + 1); sources.push({ ...s, cites: [] }); }
    return srcNo.get(k);
  };
  for (const r of res) { const k = addSrc(r.source); if (k) sources[k - 1].cites.push(r.rule_id); }
  for (const s of (site.sources || []).concat(opt.sources || [])) addSrc(s);

  const mark = s => `<span class="st st-${h(s || "na")}">${h(STATUS_WORD[s] || cap(s) || "—")}</span>`;
  const vmark = w => `<span class="st st-${h(verdictStatus(w) || "na")}">${h(cap(w || "—"))}</span>`;
  const decidedBy = o => {
    const items = ["fail", "conditional", "uncertain"].flatMap(k => (o[k] || []).map(id => `<li>${refTag(id)} ${h(titleOf[id] || id)} <span class="muted">(${h((STATUS_WORD[k] || k).toLowerCase())})</span></li>`));
    return items.length ? `<ul class="refs">${items.join("")}</ul>` : `<span class="muted">No rule stands in the way.</span>`;
  };
  const unsure = [...(ans.unsure || []), ...layoutOpenItems(run).map(u => ({ ...u, rule_id: "layout", finding: "" }))];   // the drawings' open items join the rules'
  const fmtVal = x => (x === null || x === undefined ? "—" : typeof x === "boolean" ? (x ? "yes" : "no")
    : typeof x === "object" ? JSON.stringify(x).replace(/[{}"]/g, "").replace(/,/g, ", ").replace(/:/g, ": ")
    : typeof x === "string" && /^[a-z0-9]+(_[a-z0-9]+)+$/.test(x) ? x.replace(/_/g, " ") : fmtNum(x));
  const human = k => k.replace(/_m2$/, " (m²)").replace(/_m$/, " (m)").replace(/_cad$/, " ($)").replace(/_/g, " ");
  // the sections after the comparison are numbered on from it; massing only when there is one. Numbered here, before
  // the answers table names the money's section (16 Nov 2026: declared below it, `s` threw for every run with money)
  const sn = (k => () => ++k)(d ? 3 : 2);
  const pfOk = !!(run.proforma && run.proforma.available);
  const s = { money: pfOk ? sn() : null, clauses: sn(), massing: run.massing || run.massing_note ? sn() : null, ledger: sn(), inputs: sn(), sources: sn(), verify: sn() };

  // 1. the three answers
  const answers = `<table class="answers">
      <colgroup><col style="width:24%"><col style="width:20%"><col></colgroup>
      <thead><tr><th>Question</th><th>Answer</th><th>Decided by</th></tr></thead>
      <tbody>
        <tr><th scope="row">Is it allowed outright?</th><td>${vmark(ans.allowed.outright.verdict)}</td><td>${decidedBy(ans.allowed.outright)}</td></tr>
        <tr><th scope="row">Is it allowed by rezoning?</th><td>${vmark(ans.allowed.by_rezoning.verdict)}</td><td>${decidedBy(ans.allowed.by_rezoning)}${ans.allowed.rezoning_path ? `<p class="note">Path: ${h(ans.allowed.rezoning_path)}.</p>` : ""}</td></tr>
        <tr><th scope="row">Does it fit the funders?</th><td>${vmark(ans.funded.verdict)}</td><td>${decidedBy(ans.funded)}${(opt.target_programs || []).length ? `<p class="note">Programs the option targets: ${h(opt.target_programs.map(id => titleOf[id] ? `${ref(id)} ${titleOf[id]}` : id).join("; "))}.</p>` : ""}</td></tr>
        <tr><th scope="row">What is still unsure?</th><td>${unsure.length ? `<span class="st st-${unsure.some(u => u.status === "fail") ? "fail" : "uncertain"}">${unsure.length} open item${unsure.length === 1 ? "" : "s"}</span>` : `<span class="st st-pass">Nothing open</span>`}</td><td>${unsure.length ? `Each with the person who resolves it, in section 2: ${unsure.map(u => refTag(u.rule_id)).join(", ")}.` : `<span class="muted">Every rule that applies is settled.</span>`}</td></tr>
        ${run.proforma && run.proforma.available ? `<tr><th scope="row">Does the money work? <span class="muted">(feasibility grade)</span></th><td><span class="st st-${MONEY_STATUS[run.proforma.verdict.word] || "uncertain"}">${h(moneyWord(run.proforma.verdict))}</span></td><td>Capital cost ${h(money(run.proforma.capital.total))}; funding ${h(money(run.proforma.funding.total))}; gap ${h(money(run.proforma.gap.value))}. ${h(run.proforma.verdict.why.map(w => w[0].toUpperCase() + w.slice(1) + ".").join(" "))} Every line, its rule and its source are in section ${s.money}.${moneyNext(run.proforma) ? `<p class="note">For the development manager: ${h(moneyNext(run.proforma))}</p>` : ""}</td></tr>` : ""}
      </tbody></table>`;

  // 2. open items
  const open = unsure.length ? `<table class="open">
      <colgroup><col style="width:5%"><col style="width:27%"><col style="width:13%"><col></colgroup>
      <thead><tr><th>Ref</th><th>Item</th><th>Status</th><th>Who resolves it, and what to do</th></tr></thead>
      <tbody>${unsure.map(u => `<tr><td>${refTag(u.rule_id)}</td><td><b>${h(u.title)}</b><div class="muted">${h(u.finding || "")}</div></td><td>${mark(u.status)}</td><td>${h(u.action || "—")}</td></tr>`).join("")}</tbody></table>`
    : `<p>Nothing is open: every rule that applies is settled for this option.</p>`;

  // 3. the comparison, when there is one
  let compare = "";
  if (d) {
    const changes = (d.changes || []).slice().sort((a, b) => String(ref(a.rule_id)).localeCompare(String(ref(b.rule_id)), "en", { numeric: true }));
    const head = B ? `<table class="ab">
        <colgroup><col style="width:30%"><col style="width:35%"><col></colgroup>
        <thead><tr><th>Answer</th><th>A · ${h(revA)} · this memo</th><th>B · ${h(revB)} · ${h(shortName(optionName(B)))}</th></tr></thead>
        <tbody>
          <tr><th scope="row">Allowed outright</th><td>${vmark(ans.allowed.outright.verdict)}</td><td>${vmark(B.summary.answers.allowed.outright.verdict)}</td></tr>
          <tr><th scope="row">Allowed by rezoning</th><td>${vmark(ans.allowed.by_rezoning.verdict)}</td><td>${vmark(B.summary.answers.allowed.by_rezoning.verdict)}</td></tr>
          <tr><th scope="row">Fits the funders</th><td>${vmark(ans.funded.verdict)}</td><td>${vmark(B.summary.answers.funded.verdict)}</td></tr>
          <tr><th scope="row">Open items</th><td>${unsure.length}</td><td>${(B.summary.answers.unsure || []).length}</td></tr>
        </tbody></table>` : "";
    const trade = B && kind !== "rules" ? tradeOff(L, B) : "";
    const lead = kind === "rules"
      ? `The same site and option read under the rules as of ${h(L.run.as_of)} (${h(revA)}) against ${h(d.previous_as_of)} (${h(revB)}). ${h(d.cause || "")}`
      : `${h(revA)} against ${h(revB)}${B ? `, ${h(optionName(B))}` : ""}${trade ? `: ${h(trade)}` : ""}. Both read the rules as of ${h(L.run.as_of)}.`;
    compare = `<section class="sec" id="p-compare"><h2><span class="no">3</span> Compared with ${h(revB)}</h2>
      <p class="lead">${lead}</p>${head}
      ${changes.length ? `<h3>What changed, rule by rule</h3><table class="changes">
        <colgroup><col style="width:5%"><col style="width:27%"><col style="width:13%"><col style="width:24%"><col></colgroup>
        <thead><tr><th>Ref</th><th>Rule</th><th>What changed</th><th>Status, ${h(revB)} → ${h(revA)}</th><th>Now reads</th></tr></thead>
        <tbody>${changes.map(c => `<tr><td>${refTag(c.rule_id)}</td><td>${h(titleOf[c.rule_id] || c.rule_id)}${c.from_version && c.to_version && c.from_version !== c.to_version ? `<div class="mono muted">v ${h(c.from_version)} → ${h(c.to_version)}</div>` : ""}</td><td>${h(changeWord(c, kind))}</td><td class="trans">${c.from === c.to ? `${mark(c.to)} <span class="muted">same</span>` : `${c.from ? mark(c.from) : "—"} → ${c.to ? mark(c.to) : "—"}`}</td><td>${h(c.finding || "")}</td></tr>`).join("")}</tbody></table>`
        : `<p>No rule changed its version or status between the two memos.</p>`}
    </section>`;
  }
  // the money, line by line, on paper: the board and the funder's officer read the gap here and nowhere else (15 Nov 2026)
  const moneyLines = pfOk ? `<table class="money"><colgroup><col style="width:6%"><col style="width:22%"><col style="width:16%"><col></colgroup>
      <thead><tr><th>Ref</th><th>Line</th><th>Figure</th><th>How, and from what</th></tr></thead><tbody>
      ${run.proforma.lines.map(ln => { const shown = ln.unit === "×" ? (ln.value == null ? "not given" : `×${ln.value}`) : ln.unit && ln.unit.startsWith("$") ? money(ln.value) + (ln.unit === "$/yr" ? " a year" : ln.unit === "$/m²" ? " per m²" : "") : (ln.value == null ? "not given" : fmtNum(ln.value));
        return `<tr><td>${ln.rule_id ? refTag(ln.rule_id) : '<span class="muted">option</span>'}</td><td><b>${h(ln.label)}</b>${ln.placeholder ? ' <span class="st st-uncertain">placeholder</span>' : ""}</td><td class="num">${h(shown)}</td><td>${h(ln.note || "")}${ln.rule_id ? ` <span class="muted">(${h(ref(ln.rule_id))}: ${h(titleOf[ln.rule_id] || ln.rule_id)})</span>` : ""}</td></tr>`; }).join("")}
      </tbody></table>
      <p class="note">Capital cost ${h(money(run.proforma.capital.total))}, less funding ${h(money(run.proforma.funding.total))}, gives the gap ${h(money(run.proforma.gap.value))}${run.proforma.gap.share_of_capital != null ? ` (${h(Math.round(run.proforma.gap.share_of_capital * 100))}% of the capital cost)` : ""}. ${h(run.proforma.verdict.why.map(w => w[0].toUpperCase() + w.slice(1) + ".").join(" "))} A feasibility screen, not a lender's model: hard costs from a Class D catalogue estimate escalated by the Statistics Canada index; rents from the CMHC survey; debt at the posted five-year rate under CMHC's coverage ratio. Placeholders are marked; each rule's source is in section ${s.ledger}.</p>` : "";

  // 4. every clause that applies, in reference order
  const applied = res.filter(r => r.status !== "not_applicable");
  const na = res.filter(r => r.status === "not_applicable");
  const clauses = `<table class="clauses">
      <colgroup><col style="width:5%"><col style="width:24%"><col style="width:11%"><col style="width:19%"><col style="width:20%"><col></colgroup>
      <thead><tr><th>Ref</th><th>Clause and version</th><th>Status</th><th>Proposed</th><th>Permitted or required</th><th>The ask</th></tr></thead>
      <tbody>${applied.map(r => { const s = splitValues(r, L); return `<tr><td>${refTag(r.rule_id)}</td><td><b>${h(r.title)}</b><div class="mono muted">${idBreak(r.rule_id)} · v ${h(r.version_effective_from || "—")}</div></td><td>${mark(r.status)}</td>${s.info !== undefined ? `<td colspan="3">${h(s.info || "no figures")}</td>` : `<td>${h(s.proposed || "—")}</td><td>${h(s.permitted || "—")}</td><td>${s.ask ? h(s.ask) : `<span class="muted">—</span>`}</td>`}</tr>`; }).join("")}</tbody></table>
    ${na.length ? `<p class="note">Not applicable here: ${na.map(r => `${refTag(r.rule_id)} ${h(r.title)}`).join("; ")}.</p>` : ""}`;

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
        <figcaption><b>Figure 3 · Plans by program.</b> ${h(Lay.units_placed)} of ${h(Lay.units_total)} units on ${h(Lay.floors.length)} floors of ${h(Lay.plate.width_m)} × ${h(Lay.plate.depth_m)} m. Adjacency rules read back from the plates: ${h(rules)}.${h(short)}</figcaption></figure>
      <figure class="fig"><div class="draw sheet">${S.stacking || ""}</div><figcaption><b>Figure 4 · Stacking.</b> One bar per floor, top first; each segment the share of the plate a block takes.</figcaption></figure>
      <figure class="fig"><div class="draw sheet">${S.elevations || ""}</div><figcaption><b>Figure 5 · Preliminary elevations.</b> Storeys × floor to floor, one window per unit as the rhythm, the outright height dashed. A placeholder for the elevation study, not a design.</figcaption></figure>
      <figure class="fig"><div class="draw sheet">${S["site-plan"] || ""}</div><figcaption><b>Figure 6 · Code site plan.</b> The yards dimensioned, the setback envelope, the footprint, the tree barriers where surveyed, and the table a plan checker reads.</figcaption></figure>`;
  }

  // 6. the full ledger, layer by layer, each rule with its numbers and its source
  const layers = [];
  for (const r of res) { let g = layers.find(x => x.layer === r.layer); if (!g) layers.push(g = { layer: r.layer, title: r.layer_title, rows: [] }); g.rows.push(r); }
  const numbers = v => Object.entries(v || {}).filter(([, x]) => x !== null && x !== undefined && x !== "")
    .map(([k, x]) => `<div><span class="k">${h(human(k))}</span> ${h(fmtVal(x))}</div>`).join("") || `<span class="muted">—</span>`;
  const ledger = layers.map(g => `<h3>Layer ${h(g.layer)} · ${h(g.title)}</h3>
      <table class="ledger">
        <colgroup><col style="width:5%"><col style="width:21%"><col style="width:14%"><col style="width:28%"><col style="width:18%"><col></colgroup>
        <thead><tr><th>Ref</th><th>Rule and version</th><th>Status</th><th>Finding</th><th>Numbers used</th><th>Source</th></tr></thead>
        <tbody>${g.rows.map(r => { const k = srcNo.get(`${(r.source || {}).title || ""}|${(r.source || {}).url || ""}`); return `<tr><td>${refTag(r.rule_id)}</td><td><b>${h(r.title)}</b><div class="mono muted">${idBreak(r.rule_id)}</div><div class="muted">in force from ${h(r.version_effective_from || "—")}${r.version_effective_to ? ` to ${h(r.version_effective_to)}` : ""}</div></td><td>${mark(r.status)}</td><td>${h(r.finding || "")}${r.action ? `<div class="action">${h(r.action)}</div>` : ""}</td><td class="nums">${numbers(r.values)}</td><td>${k ? `<b class="ref">S${k}</b> ` : ""}${h((r.source && r.source.section) || "")}</td></tr>`; }).join("")}</tbody></table>`).join("");

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
    .slice().sort((a, b) => String(ref(a.rule_id)).localeCompare(String(ref(b.rule_id)), "en", { numeric: true }))
    .map(v => `<tr><td>${refTag(v.rule_id)}</td><td class="mono">${idBreak(v.rule_id)}</td><td>${h(v.version_effective_from || "—")}${v.version_effective_to ? ` to ${h(v.version_effective_to)}` : ""}</td></tr>`).join("");
  const verify = `<p>The memo is deterministic: the same inputs read under the same rules always give the same memo. To check it, run the engine on the same files and compare the fingerprint, which is a hash of the rule files and the rule versions in force on the as-of date.</p>
    <pre class="cmd">${h(cmd)}</pre>
    <table class="kv"><tbody>
      <tr><th scope="row">Fingerprint</th><td class="mono">${h(st.stamp)}</td></tr>
      <tr><th scope="row">Rules hash</th><td class="mono">${h(st.rules_hash)}</td></tr>
      <tr><th scope="row">Rules as of</th><td>${h(L.run.as_of)}</td></tr>
      <tr><th scope="row">Engine</th><td>${h(L.run.engine_version)}</td></tr>
      <tr><th scope="row">Run folder</th><td class="mono">outputs/${h(run.run_id)}</td></tr>
    </tbody></table>
    <h3>Rule files</h3><table class="files"><colgroup><col style="width:30%"><col></colgroup><thead><tr><th>File</th><th>SHA-256</th></tr></thead><tbody>${files}</tbody></table>
    ${versions ? `<h3>Rule versions in force on ${h(L.run.as_of)}</h3><table class="versions"><colgroup><col style="width:6%"><col style="width:52%"><col></colgroup><thead><tr><th>Ref</th><th>Rule</th><th>Version in force</th></tr></thead><tbody>${versions}</tbody></table>` : ""}
    <p class="note">To check one finding: find its reference in section ${s.ledger} (the ledger), open its source in section ${s.sources} at the cited section, and compare the permitted figure; the proposed figure comes from the inputs in section ${s.inputs}.</p>`;

  // the running header and footer, and the document
  const safe = s => String(s).replace(/["\\\n]/g, " ");
  const css = `
    @page { size: letter; margin: 20mm 16mm 18mm;
      @top-left { content: "${safe(`First Read memo · ${address}`)}"; font: 500 7pt "IBM Plex Sans", Arial, sans-serif; color: #5f6672; }
      @top-right { content: "${safe(`${revA} · rules as of ${L.run.as_of}`)}"; font: 600 7pt "IBM Plex Sans", Arial, sans-serif; color: #2c3e50; }
      @bottom-left { content: "${safe(`Fingerprint ${st.stamp} · issued ${issued} · a feasibility screen, not legal, planning or funding advice`)}"; font: 400 6.5pt "IBM Plex Sans", Arial, sans-serif; color: #5f6672; }
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
    .note { font-size: 7.6pt; color: #3d4752; }
    /* tables: ruled rows, headers that repeat on every page, rows that do not split */
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin: 0 0 5pt; font-size: 7.6pt; line-height: 1.38; }
    thead { display: table-header-group; }
    tr { break-inside: avoid; }
    th, td { text-align: left; vertical-align: top; padding: 3.4pt 6pt 3.4pt 0; border-bottom: 0.4pt solid #d5dae0; overflow-wrap: anywhere; }
    thead th { font-size: 6.3pt; font-weight: 600; letter-spacing: .07em; text-transform: uppercase; color: #5f6672; border-bottom: 0.9pt solid #1f2933; padding-top: 0; }
    tbody th { font-weight: 600; }
    .answers td, .answers tbody th { font-size: 8.2pt; padding-top: 5pt; padding-bottom: 5pt; }
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
    @media screen { body { max-width: 190mm; margin: 12mm auto; } }`;
  const titleBlock = `<div class="tb">
      <div style="grid-column: span 2"><b>Option</b>${h(opt.name || opt.id || "—")}</div>
      <div><b>Revision</b><span class="big">${h(revA)}</span></div>
      <div><b>Rules as of</b><span class="big">${h(L.run.as_of)}</span></div>
      <div><b>Proponent</b>${h(opt.proponent || "—")}${opt.proponent_type ? ` <span class="muted">(${h(optWord("option", "proponent_type", opt.proponent_type))})</span>` : ""}</div>
      <div><b>Site</b>${h(site.zoning_district || "—")} · ${h(fmtNum(site.site_area_m2 ?? "—"))} m² · ${h(site.frontage_m ?? "—")} × ${h(site.depth_m ?? "—")} m</div>
      <div><b>${d ? (kind === "rules" ? "Revised from" : "Compared with") : "Issued"}</b>${d ? `${h(revB)}${B ? ` · ${h(shortName(optionName(B)))}` : ""}` : h(issued)}</div>
      <div><b>Fingerprint</b><span class="mono">${h(st.stamp)}</span><br><span class="muted">engine ${h(L.run.engine_version)}</span></div>
    </div>`;
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${h(`First Read memo ${revA} · ${address}`)}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>${css}</style></head><body>
    <h1>${h(address)}</h1>
    <p class="sub">First Read memo · ${h(revA)} · issued ${h(issued)}</p>
    ${titleBlock}
    <p class="howto">Section 1 gives the four answers and the rules that decide them; rules are named by layer and place (A1, C4…) throughout. Section ${s.ledger} gives each rule's finding, numbers and source, and section ${s.verify} says how to reproduce this memo.</p>
    <section class="sec"><h2><span class="no">1</span> The four answers</h2>${answers}</section>
    <section class="sec"><h2><span class="no">2</span> Open items and who resolves them</h2>${open}</section>
    ${compare}
    ${pfOk ? `<section class="sec"><h2><span class="no">${s.money}</span> The money, line by line</h2>${moneyLines}</section>` : ""}
    <section class="sec"><h2><span class="no">${s.clauses}</span> Clauses applied</h2><p class="note">${applied.length} of ${res.length} rules apply. Proposed is what the option puts forward; permitted or required is the clause's own limit; the ask is what stands between them.</p>${clauses}</section>
    ${s.massing ? `<section class="sec"><h2><span class="no">${s.massing}</span> Massing</h2>${figures}</section>` : ""}
    <section class="sec"><h2><span class="no">${s.ledger}</span> The full ledger, by layer</h2><p class="note">Every rule the engine ran, including those that do not apply here, with its finding, every number it used and the section of its source (S numbers, section ${s.sources}).</p>${ledger}</section>
    <section class="sec"><h2><span class="no">${s.inputs}</span> Inputs</h2>${inputs}</section>
    <section class="sec"><h2><span class="no">${s.sources}</span> Sources</h2>${srcList}</section>
    <section class="sec"><h2><span class="no">${s.verify}</span> Reproduce and verify</h2>${verify}</section>
  </body></html>`;
}

/* Download PDF: the server prints the paper memo with a headless Edge or Chrome and the browser saves the file.
   Where there is no server (the web version) or no such browser, the paper memo opens in the print dialog, where
   Save as PDF gives the same document. */
export async function exportPdf() {
  const run = state.run;
  if (!run) return;
  const html = paperDocument(run);
  const name = `${run.run_id.replace("/", "_")}_${rev(run.run_id)}_memo.pdf`;
  if (!STATIC) {
    setStatus("Laying out the PDF…", "busy");
    try {
      const r = await fetch("api/pdf", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ html }) });
      if (r.ok) {
        const url = URL.createObjectURL(await r.blob());
        const a = document.createElement("a"); a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 60000);
        setStatus(`Saved ${name}: ${rev(run.run_id)}, its answers, open items, clauses, massing, full ledger, inputs and sources.`, "ok");
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
