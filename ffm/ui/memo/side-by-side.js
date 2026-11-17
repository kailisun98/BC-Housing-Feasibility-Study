/* The Side by side card when two runs are compared: the pickers, the one-line trade-off, the four answers, the
   building and the money, and the rules whose status differs. */

import { cap, fmtNum, h, pill, verdictStatus } from "../core/util.js";
import { state } from "../core/state.js";
import { rev } from "../runs.js";
import { compareKind, idBreak, optionName } from "./memo.js";
import { money } from "./answers.js";
import { splitValues } from "./clauses.js";
import { figSection } from "../figures/section.js";

/* What the two options trade, in the units a board reads: units, storeys, height and floor area, A against B. */
export function tradeOff(A, B) {
  const a = (A.inputs && A.inputs.option) || {}, b = (B.inputs && B.inputs.option) || {};
  const units = o => { const v = Object.values(o.units || {}).filter(x => typeof x === "number"); return v.length ? v.reduce((s, x) => s + x, 0) : null; };
  const facts = [[units(a), units(b), "units"], [a.storeys, b.storeys, "storeys"], [a.height_m, b.height_m, "m high"], [a.gfa_m2, b.gfa_m2, "m² of floor area"]]
    .filter(([x, y]) => x != null && y != null && x !== y)
    .map(([x, y, unit]) => `${fmtNum(x)} ${unit} against ${fmtNum(y)}`);
  return facts.join(", ");
}

/* Two runs side by side: the pickers on the A and B columns, the four answers of each, then the rules whose status
   differs; the rules that read the same in both wait behind a disclosure. */
export function renderSideBySide(run) {
  const A = run.ledger, B = run.compareLedger, d = run.diff;
  if (!A || !B) return "";
  const kind = d ? compareKind(d) : "options";
  const ans = L => L.summary.answers;
  const verdictCell = w => `<span class="pill pill-${h(verdictStatus(w) || "na")}">${h(cap(w))}</span>`;
  const openCell = L => { const u = ans(L).unsure || []; return u.length ? `<span class="pill pill-${u.some(x => x.status === "fail") ? "fail" : "uncertain"}">${u.length} open</span>` : `<span class="pill pill-pass">Nothing open</span>`; };
  const head = [
    ["Allowed outright", verdictCell(ans(A).allowed.outright.verdict), verdictCell(ans(B).allowed.outright.verdict)],
    ["By rezoning", verdictCell(ans(A).allowed.by_rezoning.verdict), verdictCell(ans(B).allowed.by_rezoning.verdict)],
    ["Fits the funders", verdictCell(ans(A).funded.verdict), verdictCell(ans(B).funded.verdict)],
    ["Open items", openCell(A), openCell(B)],
  ];
  // each run named by its revision on the site: A is this run, B the run compared
  const ra = rev(run.run_id), rb = rev(state.compareRun);
  const trade = tradeOff(A, B);
  // the building and the money, side by side: what a board decides between (15 Nov 2026, from an architect's test)
  const pa = run.proforma && run.proforma.available ? run.proforma : null, pb = run.compareProforma && run.compareProforma.available ? run.compareProforma : null;
  const la = run.layout || null, lb = run.compareLayout || null;
  const oa = A.inputs.option || {}, ob = B.inputs.option || {};
  const unitsOf = o => Object.values(o.units || {}).reduce((t, v) => t + (Number(v) || 0), 0);
  const famOf = o => (Number((o.units || {}).two_bed) || 0) + (Number((o.units || {}).three_bed_plus) || 0);
  const numCell = (v, unit = "", digits = 0) => (v == null || Number.isNaN(v) ? "—" : `${v < 0 ? "−" : ""}${unit === "$" ? "$" : ""}${fmtNum(Math.abs(digits ? Math.round(v * 10 ** digits) / 10 ** digits : Math.round(v)))}${unit && unit !== "$" ? unit : ""}`);
  const delta = (a, b, unit = "", digits = 0) => (a == null || b == null ? "" : `<span class="cont">${a - b > 0 ? "+" : ""}${numCell(a - b, unit, digits)}</span>`);
  const moneyRows = [
    ["Storeys", oa.storeys, ob.storeys, "", 0],
    ["Height", oa.height_m, ob.height_m, " m", 1],
    ["Floor area", oa.gfa_m2, ob.gfa_m2, " m²", 0],
    ["FSR", oa.gfa_m2 && A.inputs.site.site_area_m2 ? oa.gfa_m2 / A.inputs.site.site_area_m2 : null, ob.gfa_m2 && B.inputs.site.site_area_m2 ? ob.gfa_m2 / B.inputs.site.site_area_m2 : null, "", 2],
    ["Yards front / rear / side", null, null, "", 0, `${(oa.setbacks_m || {}).front ?? "—"} / ${(oa.setbacks_m || {}).rear ?? "—"} / ${(oa.setbacks_m || {}).side ?? "—"} m`, `${(ob.setbacks_m || {}).front ?? "—"} / ${(ob.setbacks_m || {}).rear ?? "—"} / ${(ob.setbacks_m || {}).side ?? "—"} m`],
    ["Homes asked", unitsOf(oa) || null, unitsOf(ob) || null, "", 0],
    ["Homes that fit the plate", la ? la.units_placed : null, lb ? lb.units_placed : null, "", 0],
    ["Family homes (2-bed+)", famOf(oa) || null, famOf(ob) || null, "", 0],
    ["Capital cost", pa ? pa.capital.total : null, pb ? pb.capital.total : null, "$", 0],
    ["Funding", pa ? pa.funding.total : null, pb ? pb.funding.total : null, "$", 0],
    ["Gap", pa ? pa.gap.value : null, pb ? pb.gap.value : null, "$", 0],
    ["Gap per home", pa && pa.gap.value != null && unitsOf(oa) ? pa.gap.value / unitsOf(oa) : null, pb && pb.gap.value != null && unitsOf(ob) ? pb.gap.value / unitsOf(ob) : null, "$", 0],
    ["Gap, share of capital", pa && pa.gap.share_of_capital != null ? pa.gap.share_of_capital * 100 : null, pb && pb.gap.share_of_capital != null ? pb.gap.share_of_capital * 100 : null, "%", 0],
  ];
  const moneyTable = kind === "rules" ? "" : `<table class="plain side-money"><colgroup><col class="c-rule"><col class="c-ab"><col class="c-ab"><col class="c-ab"></colgroup>
      <thead><tr><th>Building and money</th><th>A · ${h(ra)}</th><th>B · ${h(rb)}</th><th>A less B</th></tr></thead>
      <tbody>${moneyRows.map(([k, a, b, unit, digits, ta, tb]) => `<tr><th scope="row">${h(k)}</th><td class="num">${ta != null ? h(ta) : numCell(a, unit, digits)}</td><td class="num">${tb != null ? h(tb) : numCell(b, unit, digits)}</td><td class="num">${ta != null ? "" : delta(a, b, unit, digits)}</td></tr>`).join("")}</tbody></table>
      <p class="cont side-note">The money rows are each run's pro-forma (answer 4, with every line's rule and source); the plate fit is each run's plans by program.</p>`;
  const moneyPhrase = pa && pb && pa.gap.value != null && pb.gap.value != null ? ` Gap ${money(pa.gap.value)} against ${money(pb.gap.value)}${unitsOf(oa) && unitsOf(ob) ? ` (${money(pa.gap.value / unitsOf(oa))} against ${money(pb.gap.value / unitsOf(ob))} a home)` : ""}.` : "";
  // the two sections, drawn from each run's massing, one beside the other
  const sections = kind !== "rules" && run.massing && run.compareMassing ? `<div class="side-figs">
      <figure><figcaption>A · ${h(ra)} · section</figcaption><div class="fig-section">${figSection(run.massing)}</div></figure>
      <figure><figcaption>B · ${h(rb)} · section</figcaption><div class="fig-section">${figSection(run.compareMassing)}</div></figure>
    </div>` : "";
  const lead = kind === "rules"
    ? `The same site and option: ${h(ra)} reads the rules as of ${h(A.run.as_of)}, ${h(rb)} as of ${h(B.run.as_of)}.`
    : `${trade ? `A, ${h(ra)}, against B, ${h(rb)}: ${h(trade)}.` : `A, ${h(ra)}, and B, ${h(rb)}, propose the same building.`}${h(moneyPhrase)} Both read the rules as of ${h(A.run.as_of)}.`;
  const byId = Object.fromEntries(B.results.map(r => [r.rule_id, r]));
  const rows = A.results.filter(r => r.status !== "not_applicable" || (byId[r.rule_id] && byId[r.rule_id].status !== "not_applicable")).map(r => {
    const b = byId[r.rule_id];
    return { r, b, differs: !b || b.status !== r.status };
  });
  const differ = rows.filter(x => x.differs), same = rows.filter(x => !x.differs);
  const row = ({ r, b }) => {
    const sa = splitValues(r, A), sb = b ? splitValues(b, B) : { proposed: "" };
    return `<tr>
      <td><span class="rule-title">${h(r.title)}</span><code class="rule-id">${idBreak(r.rule_id)}</code></td>
      <td class="status">${pill(r.status)}<div class="cont">${h(sa.proposed || "")}</div></td>
      <td class="status">${b ? pill(b.status) : "<span class=\"cont\">not run</span>"}<div class="cont">${h(sb.proposed || "")}</div></td>
    </tr>`;
  };
  const table = list => `<table class="plain side-rules"><colgroup><col class="c-rule"><col class="c-ab"><col class="c-ab"></colgroup>
      <thead><tr><th>Rule</th><th>A</th><th>B</th></tr></thead><tbody>${list.map(row).join("")}</tbody></table>`;
  // each run's open items, with the person who resolves them, for the run that still has some
  const openList = [["A", A, ra], ["B", B, rb]].filter(([, L]) => (ans(L).unsure || []).length).map(([k, L, r]) => `<details class="side-open">
      <summary>${k} · ${h(r)} · ${h(optionName(L))}: ${ans(L).unsure.length} open item${ans(L).unsure.length === 1 ? "" : "s"}</summary>
      <ul>${ans(L).unsure.map(u => `<li>${pill(u.status)} <b>${h(u.title)}</b> <span class="cont">${h(u.action || "")}</span></li>`).join("")}</ul>
    </details>`).join("");
  return `<section class="card section side" id="side-by-side" aria-labelledby="side-h">
    <h2 id="side-h">Side by side</h2>
    <div class="pick-row" role="group" aria-label="The two runs compared">
      <span class="pick-key" aria-hidden="true"></span>
      <div class="pick" data-slot="open"><span class="pick-name">A · ${h(ra)} · ${h(optionName(A))} <span class="cont">(as of ${h(A.run.as_of)})</span></span></div>
      <div class="pick" data-slot="compare"><span class="pick-name">B · ${h(rb)} · ${h(optionName(B))} <span class="cont">(as of ${h(B.run.as_of)})</span></span></div>
    </div>
    <p class="side-lead">${lead}</p>
    <table class="plain side-head"><thead><tr><th><span class="sr-only">Answer</span></th><th><span class="sr-only">A, ${h(ra)}, ${h(optionName(A))}</span></th><th><span class="sr-only">B, ${h(rb)}, ${h(optionName(B))}</span></th></tr></thead>
      <tbody>${head.map(([k, a, b]) => `<tr><th scope="row">${h(k)}</th><td>${a}</td><td>${b}</td></tr>`).join("")}</tbody></table>
    ${moneyTable}
    ${sections}
    ${openList}
    <h3 class="side-sub">${differ.length ? `${differ.length} of ${rows.length} rules read differently` : `All ${rows.length} rules read the same in both`}</h3>
    ${differ.length ? table(differ) : ""}
    ${same.length ? `<details class="side-same"><summary>${differ.length ? `The other ${same.length} rules, the same in both` : `Show the ${same.length} rules`}</summary>${table(same)}</details>` : ""}
    <p class="cont side-note">Under each status is what that option proposed.</p>
  </section>`;
}
