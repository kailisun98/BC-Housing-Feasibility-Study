/* The full ledger, layer by layer (A zoning to F assumptions), each finding with its rule and source. */

import { $, $$, fmtValues, h, pill, REV, sourceLink, STATUS_WORD } from "../core/util.js";
import { refTagOf } from "./memo.js";

/* The ledger opens one layer at a time, or all at once; printing opens every layer and closes them again after. */
export function wireLedger() {
  const btn = $(".ledger .open-all");
  if (!btn) return;
  const sync = () => { const all = $$(".ledger details").every(x => x.open); btn.textContent = all ? "Close all layers" : "Open all layers"; btn.setAttribute("aria-expanded", String(all)); };
  btn.addEventListener("click", () => { const open = !$$(".ledger details").every(x => x.open); $$(".ledger details").forEach(x => { x.open = open; }); sync(); });
  $$(".ledger details").forEach(x => x.addEventListener("toggle", sync));
  sync();
}

export function renderLedger(res, changed = new Set()) {
  const layers = [];
  for (const r of res) {
    let L = layers.find(x => x.layer === r.layer);
    if (!L) { L = { layer: r.layer, title: r.layer_title, rows: [] }; layers.push(L); }
    L.rows.push(r);
  }
  const blocks = layers.map(L => {
    const counts = {};
    for (const r of L.rows) counts[r.status] = (counts[r.status] || 0) + 1;
    const countPills = Object.entries(counts).map(([s, n]) => `<span class="pill pill-${h(s)}">${n} ${h(STATUS_WORD[s] || s)}</span>`).join("");
    const rows = L.rows.map(r => `<tr>
      <td>${refTagOf(r.rule_id)}<span class="rule-title">${h(r.title)}${changed.has(r.rule_id) ? REV : ""}</span><code class="rule-id">${h(r.rule_id)} · v ${h(r.version_effective_from || "—")}</code></td>
      <td class="status">${pill(r.status)}</td>
      <td>${h(r.finding)}</td>
      <td class="nums">${h(fmtValues(r.values))}</td>
      <td class="src">${sourceLink(r.source)}</td>
    </tr>`).join("");
    const revised = L.rows.some(r => changed.has(r.rule_id));
    return `<details${revised ? " open" : ""}>
      <summary><span class="layer">Layer ${h(L.layer)}</span><span class="layer-title">${h(L.title)}</span>${revised ? REV : ""}<span class="counts">${countPills}</span></summary>
      <table class="plain"><colgroup><col class="c-rule"><col class="c-status"><col class="c-finding"><col class="c-nums"><col class="c-src"></colgroup><thead><tr><th>Rule</th><th>Status</th><th>Finding</th><th>Numbers used</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table>
    </details>`;
  });
  return `<section class="card section ledger">
    <h2>Full ledger by layer · ${res.length} rules</h2>
    <p class="intro">The same rules by layer, with the engine's finding, every number it used and the clause it came from, including the rules that did not apply. Open a layer to read its rows.</p>
    <div class="tools"><button class="btn btn-quiet btn-small open-all" type="button" aria-expanded="false">Open all layers</button></div>
    ${blocks.join("")}
  </section>`;
}
