/* "Clauses applied": proposed, permitted or required, and the ask, one row per clause the run read. */

import { fmtNum, h, paramWords, pill, REV, STATUS_WORD, unverifiedTag } from "../core/util.js";
import { optWord } from "../fields.js";
import { idBreak, refTagOf } from "./memo.js";

const pct = x => (typeof x === "number" ? `${(100 * x).toFixed(x * 100 % 1 ? 1 : 0)}%` : "—");

// non-breaking hyphens: a count reads "70 1‑bed", never "70 1-" at a line's end and "bed" on the next (17 Nov 2026)
export const UNIT_WORD = { studio: "studio", one_bed: "1‑bed", two_bed: "2‑bed", three_bed_plus: "3‑bed+" };

/* Every figure a check carries that is a number, a word or a yes/no, in words. */
const flatWords = v => Object.entries(v || {}).filter(([, x]) => x !== null && x !== undefined && typeof x !== "object").map(([k, x]) => paramWords(k, x));

const num = x => (x === null || x === undefined ? "—" : fmtNum(x));

/* Each check's numbers split three ways: what the option proposes (the simulation's input), what the clause permits
   or requires, and the ask when the two differ. Checks the table does not know fall back to a split by key name. */
export function splitValues(r, L) {
  const v = r.values || {}, opt = (L.inputs && L.inputs.option) || {};
  const ask = r.action || "";
  const path = L.summary && L.summary.answers && L.summary.answers.rezoning_path;
  switch (r.check) {
    case "district_outright_fsr":
      return { proposed: `FSR ${num(v.fsr && Number(v.fsr).toFixed(2))} (${num(v.gfa_m2)} m² on ${num(v.site_area_m2)} m²)`, permitted: `FSR ${num(v.max_fsr_outright)} outright`,
               ask: v.fsr > v.max_fsr_outright ? `Density above the outright limit: ${path ? `relaxation by rezoning (${path})` : "a rezoning"}.` : "" };
    case "district_outright_height":
      return { proposed: `${num(v.height_m)} m, ${num(v.storeys)} storeys`, permitted: `${num(v.max_height_m_outright)} m outright`,
               ask: v.height_m > v.max_height_m_outright ? `Height above the outright limit: ${path ? `relaxation by rezoning (${path})` : "a rezoning"}.` : "" };
    case "rezoning_policy_social_housing": {
      const b = v.benchmark_height_m || [];
      // where the policy is not yet known to apply, the check carries no figures: the option's own, and the condition
      // in words (17 Nov 2026: "— m, FSR —", "staff benchmark — to — m, about FSR —")
      const site = (L.inputs && L.inputs.site) || {};
      const height = v.height_m ?? opt.height_m, fsr = v.fsr ?? (opt.gfa_m2 && site.site_area_m2 ? opt.gfa_m2 / site.site_area_m2 : null);
      return { proposed: height != null || fsr != null ? [height != null ? `${num(height)} m` : "", fsr != null ? `FSR ${num(Number(fsr).toFixed(2))}` : ""].filter(Boolean).join(", ") : "height and floor area not given",
               permitted: b[0] != null ? `staff benchmark ${num(b[0])} to ${num(b[1])} m, about FSR ${num(v.benchmark_fsr)} (negotiated, no maximum)` : "applies inside a former Community Vision area; height and density negotiated, no maximum",
               ask: b[1] && v.height_m > b[1] ? `${(v.height_m - b[1]).toFixed(1)} m above the benchmark: to be negotiated with staff.` : (b[1] && v.fsr > v.benchmark_fsr ? "Density above the benchmark: to be negotiated with staff." : ask) };
    }
    case "parking_minimums": {
      const said = (x, what) => (x == null ? "" : `${num(x)} ${what}`);
      const given = [said(v.parking_spaces ?? opt.parking_spaces, "vehicle"), said(v.bicycle_spaces ?? opt.bicycle_spaces, "bicycle")].filter(Boolean);
      return { proposed: given.length ? `${given.join(", ")} spaces` : "parking not given", permitted: "no minimum (June 2024); bicycle spaces set at development permit", ask: "" };
    }
    case "toa_status":
      return { proposed: v.storeys != null ? `${num(v.storeys)} storeys` : `${num(opt.storeys)} storeys`, permitted: (v.toa_tier || v.tier) ? `tier ${v.toa_tier || v.tier}: at least ${num(v.minimum_allowable_storeys || v.min_storeys || v.floors)} storeys may not be refused` : "SkyTrain tiers 1 to 3: 20, 12, 8 storeys; bus-exchange tiers 4 and 5: 12, 8 storeys minimum allowable", ask };
    case "family_unit_share": {
      const m3 = v.min_three_plus_bed_share;
      return { proposed: v.units_total ? `${num(v.two_plus_bed_units)} of ${num(v.units_total)} units two-bed+ (${pct(v.two_plus_bed_share)}); ${num(v.three_plus_bed_units)} three-bed+ (${pct(v.three_plus_bed_share)})` : "unit mix not given",
               permitted: `at least ${pct(v.min_two_plus_bed_share ?? 0.35)} two-bed+${m3 != null ? `, ${pct(m3)} three-bed+` : ""}`, ask };
    }
    case "social_housing_definition":
      return { proposed: `${pct(v.share_below_hils)} of units below HILs; ${num(v.housing_agreement_years)}‑year agreement; owner ${optWord("option", "owner_type_at_completion", v.owner_type_at_completion) || "—"}`,
               permitted: "at least 30% below HILs at rent of at most 30% of income; 60 years or the life of the building; non-profit, co-op or government owner", ask };
    case "tree_replacement":
      return { proposed: `${num(v.existing)} existing, ${num(v.removed)} removed, ${num(v.replacements_proposed)} replacements, ${num(v.trees_after)} after`, permitted: `Schedule C: at least ${num(v.schedule_c_required)} trees on ${num(v.site_area_m2)} m²`,
               ask: v.shortfall > 0 ? `${num(v.shortfall)} tree${v.shortfall === 1 ? "" : "s"} short: plant more or pay $${num(v.cash_in_lieu_cad)} cash in lieu.` : ask };
    case "code_basis_flags":
      return { proposed: `${num(v.storeys)} storeys`, permitted: `Part ${v.part || "—"} of the BC Building Code (Part 9 up to 3 storeys and 600 m²)`, ask: "" };
    case "unit_area_flags": {
      // the minimum net area is given per unit type: studio 33, one-bed 49, …
      const mins = v.min_net_area_m2 && typeof v.min_net_area_m2 === "object"
        ? Object.entries(v.min_net_area_m2).map(([k, x]) => `${UNIT_WORD[k] || k.replace(/_/g, " ")} ${num(x)}`).join(", ") + " m²"
        : `${num(v.min_net_area_m2)} m²`;
      return { proposed: `average ${num(v.average_gross_area_per_unit_m2)} m² gross per unit`, permitted: `BC Housing minimum net areas: ${mins}`, ask: "" };
    }
    case "chf_fit": {
      const mix = v.mix_shares ? `mix ${pct(v.mix_shares.market)} / ${pct(v.mix_shares.rgi)} / ${pct(v.mix_shares.deep_subsidy)}` : "rent-tier mix not given";
      const req = v.required_mix ? `${pct(v.required_mix.market)} market / ${pct(v.required_mix.rgi)} RGI / ${pct(v.required_mix.deep_subsidy)} deep subsidy (±2 points); 5% accessible; 60-year lease at nominal value; site control` : "";
      const unknown = (v.unknown || []).length ? `Supply: ${v.unknown.join("; ")}.` : "";
      const fails = (v.fails || []).length ? `Fix: ${v.fails.join("; ")}.` : "";
      const access = opt.accessible_units == null ? "accessible units not given" : `${num(opt.accessible_units)} accessible`;
      const control = opt.site_control ? `site control: ${optWord("option", "site_control", opt.site_control)}` : "site control not given";
      return { proposed: `${mix}; ${access}; ${control}`, permitted: req, ask: [fails, unknown].filter(Boolean).join(" ") || ask };
    }
    case "bc_builds_fit": {
      const unknown = (v.unknown || []).length ? `Supply: ${v.unknown.join("; ")}.` : "";
      const fails = (v.fails || []).length ? `Fix: ${v.fails.join("; ")}.` : "";
      // a missing share or discount is said in words, not left as a dash in the middle of a sentence
      const below = opt.below_market_unit_share == null && opt.below_market_discount == null ? "below-market share and discount not given"
        : opt.below_market_unit_share == null ? `below-market share not given, at ${pct(opt.below_market_discount)} below market`
        : opt.below_market_discount == null ? `${pct(opt.below_market_unit_share)} of units below market, discount not given`
        : `${pct(opt.below_market_unit_share)} of units at ${pct(opt.below_market_discount)} below market`;
      return { proposed: `${below}; ${num(opt.non_residential_gfa_m2 || 0)} m² non-residential`, permitted: "at least 20% of units at least 20% below market; non-residential at most 30% of area; a non-profit teamed with a builder", ask: [fails, unknown].filter(Boolean).join(" ") || ask };
    }
    case "dcl_cac":
      return { proposed: "social housing", permitted: `DCL ${v.dcl_exempt ? "exempt" : "payable"}, CAC ${v.cac_exempt ? "exempt" : "payable"}`, ask: "" };
    case "info_only":
      // a rule that informs: its figures in one cell across the row (see renderClauses), each with its unit
      return { info: flatWords(v).join("; ") };
    default: {
      const lim = k => /^(max_|min_|required|benchmark_|schedule_|eligible)/.test(k);
      const flat = Object.entries(v).filter(([, x]) => x !== null && x !== undefined && typeof x !== "object");
      const proposed = flat.filter(([k]) => !lim(k)).map(([k, x]) => paramWords(k, x)).join("; ");
      const permitted = flat.filter(([k]) => lim(k)).map(([k, x]) => paramWords(k, x)).join("; ");
      // a rule with figures and no limit or ask (the cost assumptions) reads in one cell, as the informing rules do
      // (17 Nov 2026: layer F printed its figures under Proposed and "— —" across the rest)
      if (!permitted && !ask) return { info: proposed };
      return { proposed, permitted, ask };
    }
  }
}

/* Every clause that applied to this site and option, in one table: its status, the numbers the option proposes,
   what the clause permits or requires, and the ask where they differ. Not-applicable rules are named underneath. */
/* A rule's clause text: a short one in the row, a long one folded under its first words (17 Nov 2026: paragraphs of
   up to 900 characters in the 24% clause column made one row 396 px tall and the table about 3,700 px). The fold
   prints open. */
function secHtml(sec) {
  if (!sec) return "";
  const s = String(sec);
  if (s.length <= 140) return `<span class="rule-sec">${h(s)}</span>`;
  const cut = s.lastIndexOf(" ", 90);
  return `<details class="rule-sec-fold"><summary>${h(s.slice(0, cut > 40 ? cut : 90))}…</summary><span class="rule-sec">${h(s)}</span></details>`;
}

/* A rule the plans test (the exits, bcbc.exits) takes the plans' own status and summary, so the clause row and the open
   item agree (17 Nov 2026: Exits read Fail in answer 3 and Info here). Pure. */
export function withPlans(res, run) {
  const eg = run && run.layout && run.layout.egress;
  if (!eg || !eg.rule_id || !eg.status) return res;
  return res.map(r => r.rule_id === eg.rule_id && r.status !== "not_applicable"
    ? { ...r, status: eg.status, action: eg.summary ? `The plans: ${eg.summary}` : r.action } : r);
}

export function renderClauses(res, L, changed = new Set(), run = null) {
  res = withPlans(res, run);
  const applied = res.filter(r => r.status !== "not_applicable");
  const na = res.filter(r => r.status === "not_applicable");
  const order = { fail: 0, conditional: 1, uncertain: 2, pass: 3, info: 4 };
  const rows = applied.slice().sort((a, b) => (order[a.status] ?? 9) - (order[b.status] ?? 9) || a.layer.localeCompare(b.layer)).map(r => {
    const s = splitValues(r, L);
    return `<tr class="st-${h(r.status)}">
      <td>${refTagOf(r.rule_id)}<span class="rule-title">${h(r.title)}${changed.has(r.rule_id) ? REV : ""}${unverifiedTag(r.source)}</span><code class="rule-id">${idBreak(r.rule_id)} · <span class="nw">v ${h(r.version_effective_from || "—")}</span></code>${secHtml(r.source && r.source.section)}</td>
      <td class="status">${pill(r.status)}</td>
      ${s.info !== undefined ? `<td class="nums info-span" colspan="3">${h(s.info || "no figures")}${r.status !== "info" && r.action ? `<span class="ask info-ask">${h(r.action)}</span>` : ""}</td>` : `<td class="nums">${h(s.proposed || "—")}</td>
      <td class="nums">${h(s.permitted || "—")}</td>
      <td class="ask">${s.ask ? h(s.ask) : `<span class="cont">—</span>`}</td>`}
    </tr>`;
  }).join("");
  const counts = {};
  for (const r of applied) counts[r.status] = (counts[r.status] || 0) + 1;
  const countPills = ["fail", "conditional", "uncertain", "pass", "info"].filter(s => counts[s]).map(s => `<span class="pill pill-${s}">${counts[s]} ${h(STATUS_WORD[s])}</span>`).join("");
  return `<section class="card section clauses">
    <h2>Clauses applied · ${applied.length} of ${res.length} rules</h2>
    <p class="intro">Every clause that applies to this site and option, worst first. <b>Proposed</b> is what the option puts forward and the simulation used; <b>permitted or required</b> is the clause's own limit; <b>the ask</b> is the relaxation, negotiation or missing figure that stands between them.</p>
    <div class="counts">${countPills}</div>
    <table class="plain"><colgroup><col class="c-rule"><col class="c-status"><col class="c-prop"><col class="c-perm"><col class="c-ask"></colgroup>
      <thead><tr><th>Clause</th><th>Status</th><th>Proposed (simulated)</th><th>Permitted or required</th><th>The ask</th></tr></thead><tbody>${rows}</tbody></table>
    ${na.length ? `<details class="fold na"><summary>Not applicable here: ${na.length} rule${na.length === 1 ? "" : "s"}, for other districts, policies or programs</summary><ul class="na-list">${na.map(r => `<li>${h(r.title)} <code class="rule-id">${idBreak(r.rule_id)}</code></li>`).join("")}</ul></details>` : ""}
  </section>`;
}
