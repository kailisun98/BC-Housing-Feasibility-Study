/* The operator's desk and the area schedule (24 Nov 2026).

   A second simulated panel's operator: "the operator is not in the flow" — the operating figures sat in a fold the
   development manager filled just before Run, and nothing asked, issued to or recorded the operator. In the Operator
   layout the memo opens on the operator's desk: the building's own operating figures to enter, a signature that makes
   them the operator's (the memo then says whose they are), and what an operator checks on the plans first. The manager
   issues the memo to the operator; the operator sends it back.

   The area schedule (a tower architect's and a cost consultant's first table): homes by type and floor, the floor area
   by use, net to gross, from the layout the run carries; a CSV of the same. Pure HTML out, wired once drawn. */

import { $, $$, h, setPath, setStatus, toast, todayISO } from "../core/util.js";
import { state } from "../core/state.js";
import { OPERATING_FIELDS } from "../fields.js";
import { markStale, saveDraft } from "../files.js";
import { briefEditor, wireBriefEditor } from "../brief.js";
import { renderMemo } from "./memo.js";

const NAME_KEY = "ffm.operator.name";
const ORG_KEY = "ffm.operator.org";
const kept = k => { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } };
const keep = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* the name lasts this visit */ } };
const usd = x => `$${Math.round(x).toLocaleString("en-CA")}`;

/* The help under each operating figure: what a blank uses, in the engine's own words (proforma.build). */
const HELP = {
  "operations.rent_market_monthly_cad": "Blank: the CMHC survey's average.",
  "operations.rent_rgi_monthly_cad": "Blank: BC Housing's estimate, 30% of 70% of the Housing Income Limit.",
  "operations.rent_deep_monthly_cad": "Blank: the shelter allowance by bedrooms. 0 for a shelter.",
  "operations.operating_cost_per_unit_year_cad": "Blank: the $6,500 placeholder (a home a year; a bed a year for a shelter).",
  "operations.support_staffing_cad_year": "Never assumed: supportive, transitional and shelter housing is unsure without it.",
  "operations.operating_subsidy_cad_year": "What you have or are seeking from a funder.",
  "operations.subsidy_term_years": "A loan is sized on the subsidy only where its term covers the 40-year loan.",
  "operations.replacement_reserve_per_unit_year_cad": "Blank: the $600 placeholder.",
  "operations.vacancy_rate": "A percent (2) or a share (0.02), both 2%; at most 50%. Blank: the CMHC market rate, 3.7%.",
  "operations.operating_cost_per_bed_year_cad": "Beds beside homes. Blank: each bed costed as a home, and the memo says so.",
  "operations.subsidy_source": "The funder and the agreement, in a few words.",
};

export function operatorDesk(run) {
  if (state.mode !== "operator") return "";
  const opt = state.option || ((run.ledger || {}).inputs || {}).option || {};
  const ops = opt.operations || {};
  const signed = ops.signed && ops.signed.by ? ops.signed : null;
  const kind = String(opt.housing_type || "independent");
  const ob = (run.layout || {}).operability;
  const fields = OPERATING_FIELDS.map(([k, label, type]) => {
    const sub = k.split(".")[1], id = `op-${sub}`, text = type === "text";
    return `<label class="field"><span class="label">${h(label)}</span><input id="${id}" type="${text ? "text" : "number"}"${text ? "" : ' step="any" min="0" inputmode="decimal"'} data-op="${h(k)}"${text ? ' data-text="1"' : ""} value="${h(ops[sub] ?? "")}" placeholder="blank"><span class="help">${h(HELP[k] || "")}</span></label>`;
  }).join("");
  const items = ob ? `<ul class="op-checks">${ob.items.map(i => `<li data-status="${h(i.status)}"><b>${h(i.label)}</b> <span class="pill-mini">${h(i.status)}</span> <span class="cont">${h(i.note)}</span></li>`).join("")}</ul>` : `<p class="cont">No layout in this run.</p>`;
  return `<section class="card operator-desk" id="operator-desk" aria-labelledby="op-desk-h">
    <h2 id="op-desk-h">The operator's figures <span class="cont">· ${signed ? `signed by ${h(signed.by)}${signed.org ? ` of ${h(signed.org)}` : ""}, ${h(signed.on || "")}` : "not yet signed: the memo reads them as the manager's or the screen's placeholders"}</span></h2>
    <p class="cont">What it takes to run ${h(opt.name ? "this building" : "the building")} for the years after it opens: enter the building's own figures, sign them as yours, then Run again; the memo then says whose they are. ${kind !== "independent" ? "Support staffing is never assumed for this kind of housing." : ""}</p>
    <div class="op-fields">${fields}</div>
    <p class="field"><label><input type="checkbox" id="op-confirmed"${ops.subsidy_confirmed === true ? " checked" : ""}> The operating subsidy is confirmed, with an agreement in hand</label></p>
    <div class="op-sign">
      <label class="field"><span class="label">Your name</span><input type="text" id="op-name" value="${h((signed && signed.by) || kept(NAME_KEY))}" autocomplete="name" maxlength="80"></label>
      <label class="field"><span class="label">Organization</span><input type="text" id="op-org" value="${h((signed && signed.org) || kept(ORG_KEY) || opt.operator || "")}" maxlength="120"></label>
      <button type="button" class="btn btn-primary btn-small" id="op-sign">${signed ? "Sign again" : "Sign these figures"}</button>
      ${signed ? `<button type="button" class="btn btn-quiet btn-small" id="op-unsign">Withdraw the signature</button>` : ""}
    </div>
    <h3>The spaces it runs on</h3>
    ${briefEditor(opt)}
    <h3>What an operator checks first, on the plans</h3>
    ${items}
  </section>`;
}

export function wireOperatorDesk() {
  const desk = $("#operator-desk");
  if (!desk) return;
  if (state.option) wireBriefEditor(desk, state.option, () => state.run && renderMemo(state.run));
  const changed = what => {
    if (!state.option) { toast("Open the option first: the figures belong to it.", true); return false; }
    state.optionDirty = true;
    const dirty = $("#option-dirty"); if (dirty) dirty.hidden = false;
    markStale(what);
    saveDraft();
    return true;
  };
  $$("[data-op]", desk).forEach(inp => inp.addEventListener("change", () => {
    if (!state.option) return;
    const raw = inp.value.trim();
    state.option.operations = state.option.operations || {};
    setPath(state.option, inp.dataset.op, raw === "" ? null : inp.dataset.text ? raw : Number(raw));
    // a figure changed after signing is no longer the signed figure, and the desk says so at once (25 Nov 2026: the
    // heading kept "signed by" until the next run, which then came back unsigned without a word)
    const wasSigned = state.option.operations.signed;
    if (wasSigned) state.option.operations.signed = null;
    if (changed("the operating figures") && wasSigned) {
      const head = $("#op-desk-h .cont", desk);
      if (head) head.textContent = "· changed after signing: sign again, or the memo reads them unsigned";
      const btn = $("#op-sign", desk); if (btn) btn.textContent = "Sign these figures";
      setStatus(`A figure changed after ${wasSigned.by} signed: the signature is withdrawn. Sign again before Run again, or the memo reads the figures unsigned.`, "busy");
    }
  }));
  const conf = $("#op-confirmed", desk);
  if (conf) conf.addEventListener("change", () => {
    if (!state.option) return;
    state.option.operations = state.option.operations || {};
    state.option.operations.subsidy_confirmed = conf.checked ? true : null;
    changed("the operating subsidy");
  });
  const sign = $("#op-sign", desk);
  if (sign) sign.addEventListener("click", () => {
    const by = ($("#op-name", desk).value || "").trim(), org = ($("#op-org", desk).value || "").trim();
    if (!by) { toast("Say who signs: your name goes on the memo beside the figures.", true); $("#op-name", desk).focus(); return; }
    if (!state.option) return;
    keep(NAME_KEY, by); keep(ORG_KEY, org);
    state.option.operations = state.option.operations || {};
    state.option.operations.signed = { by, org: org || null, on: todayISO() };
    if (changed("the operator's signature")) setStatus(`Signed by ${by}${org ? ` of ${org}` : ""}. Run again: the memo then reads the operating figures as yours.`, "ok");
  });
  const un = $("#op-unsign", desk);
  if (un) un.addEventListener("click", () => {
    if (!state.option || !state.option.operations) return;
    state.option.operations.signed = null;
    if (changed("the operator's signature")) setStatus("Signature withdrawn. Run again to say so in the memo.", "info");
  });
}

/* ---- the area schedule ---- */

const SHORT = { homes: "Homes", circulation: "Circulation", core: "Cores", program: "Program", amenity: "Amenity", services: "Services", non_residential: "Non-res.", spare: "Spare" };
const UNIT_WORD = { three_bed_plus: "3B+", two_bed: "2B", one_bed: "1B", studio: "ST" };

export function areaScheduleHtml(run) {
  const s = (run.layout || {}).area_schedule;
  if (!s) return "";
  const used = s.groups.map(g => g.key).filter(k => s.totals.m2[k]);
  const homes = r => Object.entries(r.homes || {}).map(([k, n]) => `${n} ${UNIT_WORD[k] || k}`).join(", ");
  const pct = x => (x == null ? "" : `${Math.round(x * 100)}%`);
  const row = (r, total) => `<tr${total ? ' class="total"' : ""}><th scope="row">${h(r.name)}</th><td class="num">${r.homes_total}</td><td class="cont">${h(homes(r))}</td>${used.map(k => `<td class="num">${Math.round(r.m2[k]).toLocaleString("en-CA")}</td>`).join("")}<td class="num">${Math.round(r.gross_m2).toLocaleString("en-CA")}</td><td class="num${total && s.flag ? " warn-text" : ""}">${pct(r.efficiency)}</td></tr>`;
  const total = { name: "Total", homes_total: s.totals.homes_total, homes: s.totals.homes, m2: s.totals.m2, gross_m2: s.totals.gross_m2, efficiency: s.totals.efficiency };
  return `<section class="card area-schedule" id="area-schedule" aria-labelledby="area-h">
    <h2 id="area-h">Area schedule <span class="cont">· ${s.totals.homes_total} homes, ${Math.round(s.totals.gross_m2).toLocaleString("en-CA")} m² gross, ${pct(s.totals.efficiency)} net to gross${s.flag ? `, under the ${pct(s.efficiency_floor)} this screen flags` : ""}</span></h2>
    <div class="table-scroll"><table class="plain area-table"><thead><tr><th scope="col">Floor</th><th scope="col" class="num">Homes</th><th scope="col">By type</th>${used.map(k => `<th scope="col" class="num">${h(SHORT[k] || k)} m²</th>`).join("")}<th scope="col" class="num">Gross m²</th><th scope="col" class="num">Net to gross</th></tr></thead>
      <tbody>${s.floors.map(r => row(r, false)).join("")}${row(total, true)}</tbody></table></div>
    <p class="cont">${h(s.note)}</p>
    <div class="form-actions"><button type="button" class="btn btn-small" id="area-csv">Download the area schedule (CSV)</button></div>
  </section>`;
}

const UNIT_KEYS = ["three_bed_plus", "two_bed", "one_bed", "studio"];
const UNIT_LABEL = { three_bed_plus: "Three-bedroom+", two_bed: "Two-bedroom", one_bed: "One-bedroom", studio: "Studio" };

/* layout.area_schedule_csv's twin: the same columns and rows. */
export function areaScheduleCsv(s) {
  const keys = s.groups.map(g => g.key);
  const head = ["Floor", "Homes", ...UNIT_KEYS.map(k => UNIT_LABEL[k]), ...s.groups.map(g => g.label), "Partitions", "Gross", "Efficiency"];
  const rows = [...s.floors, { name: "Total", homes_total: s.totals.homes_total, homes: s.totals.homes, m2: s.totals.m2, partitions_m2: s.totals.partitions_m2, gross_m2: s.totals.gross_m2, efficiency: s.totals.efficiency }];
  const lines = [head.map(x => `"${x}"`).join(",")];
  for (const r of rows) {
    lines.push([`"${r.name}"`, String(r.homes_total), ...UNIT_KEYS.map(k => String((r.homes || {})[k] || 0)), ...keys.map(k => Number(r.m2[k]).toFixed(1)),
      Number(r.partitions_m2).toFixed(1), Number(r.gross_m2).toFixed(1), r.efficiency == null ? "" : Number(r.efficiency).toFixed(3)].join(","));
  }
  return lines.join("\n") + "\n";
}

export function wireAreaSchedule(run) {
  const b = $("#area-csv");
  const s = (run.layout || {}).area_schedule;
  if (!b || !s) return;
  b.addEventListener("click", () => {
    const blob = new Blob([areaScheduleCsv(s)], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${String(run.run_id || "run").replace(/\//g, "-")}-area-schedule.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });
}
