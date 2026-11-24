/* The full ledger, layer by layer (A zoning to F assumptions), each finding with its rule and source. */

import { $, $$, fmtNum, h, keyWords, paramWords, pill, REV, STATUS_WORD, unverifiedTag } from "../core/util.js";
import { refTagOf } from "./memo.js";

/* A figure the rules call a share prints as a percentage wherever the key says share, as the rest of the memo prints
   it (20 Nov 2026: "share below hils: 0.3" in Numbers used beside "30%" in the clauses). Pure. */
export const isShare = (k, x) => typeof x === "number" && /(^|_)shares?(_|$)/.test(String(k)) && x >= 0 && x <= 1;
export const pctWords = x => `${fmtNum(Math.round(x * 1000) / 10)}%`;
export function numberWords(k, x) {
  if (isShare(k, x)) return `${keyWords(k)}: ${pctWords(x)}`;
  return paramWords(k, x);
}
/* Every figure a result carries that is a number, a word or a yes/no, in words; a share as a percentage, and a small
   object of shares (the CHF's mix) as its parts. */
export function valuesWords(v) {
  const bits = [];
  for (const [k, x] of Object.entries(v || {})) {
    if (x === null || x === undefined) continue;
    if (typeof x === "object" && !Array.isArray(x) && /share|mix/.test(k) && Object.values(x).every(y => typeof y === "number" && y >= 0 && y <= 1)) {
      bits.push(`${keyWords(k)}: ${Object.entries(x).map(([a, y]) => `${a.replace(/_/g, " ").replace(/\brgi\b/, "RGI")} ${pctWords(y)}`).join(", ")}`);
      continue;
    }
    if (typeof x === "object") continue;
    bits.push(numberWords(k, x));
  }
  return bits.join("; ");
}

/* The ledger opens one layer at a time, or all at once; printing opens every layer and closes them again after. */
export function wireLedger() {
  const btn = $(".ledger .open-all");
  if (!btn) return;
  const sync = () => { const all = $$(".ledger details.layer").every(x => x.open); btn.textContent = all ? "Close all layers" : "Open all layers"; btn.setAttribute("aria-expanded", String(all)); };
  btn.addEventListener("click", () => { const open = !$$(".ledger details.layer").every(x => x.open); $$(".ledger details.layer").forEach(x => { x.open = open; }); sync(); });
  $$(".ledger details.layer").forEach(x => x.addEventListener("toggle", sync));
  sync();
}

/* The worst first, in every layer's counts (17 Nov 2026: each layer listed its pills in the order its rows came). */
const COUNT_ORDER = ["fail", "conditional", "uncertain", "pass", "info", "not_applicable"];

/* A rule's source: the document as a link, its section in a line, a long section folded under its first words
   (17 Nov 2026: a whole clause in the Source cell made rows 630 px tall and layer A 23,000 px open). */
function sourceCell(src) {
  if (!src || (!src.title && !src.url)) return "";
  const doc = src.url ? `<a href="${h(src.url)}" target="_blank" rel="noopener">${h(src.title || src.url)}</a>` : h(src.title);
  const sec = String(src.section || "");
  const secHtml = !sec ? "" : sec.length <= 140 ? `<span class="rule-sec">${h(sec)}</span>`
    : `<details class="rule-sec-fold"><summary>${h(sec.slice(0, Math.max(40, sec.lastIndexOf(" ", 90))))}…</summary><span class="rule-sec">${h(sec)}</span></details>`;
  return doc + unverifiedTag(src) + secHtml;
}

export function renderLedger(res, changed = new Set()) {
  const layers = [];
  for (const r of res) {
    let L = layers.find(x => x.layer === r.layer);
    if (!L) { L = { layer: r.layer, title: r.layer_title, rows: [] }; layers.push(L); }
    L.rows.push(r);
  }
  const row = r => `<tr>
      <td>${refTagOf(r.rule_id)}<span class="rule-title">${h(r.title)}${changed.has(r.rule_id) ? REV : ""}</span><code class="rule-id">${h(r.rule_id)} · <span class="nw">v ${h(r.version_effective_from || "—")}</span></code></td>
      <td class="status">${pill(r.status)}</td>
      <td data-k="Finding">${h(r.finding)}</td>
      <td class="nums" data-k="Numbers used">${h(valuesWords(r.values))}</td>
      <td class="src" data-k="Source">${sourceCell(r.source)}</td>
    </tr>`;
  const blocks = layers.map(L => {
    const counts = {};
    for (const r of L.rows) counts[r.status] = (counts[r.status] || 0) + 1;
    const countPills = COUNT_ORDER.filter(s => counts[s]).map(s => `<span class="pill pill-${h(s)}">${counts[s]} ${h(STATUS_WORD[s] || s)}</span>`).join("");
    // the rules that did not apply here, folded into one row, the reason for each kept inside (17 Nov 2026: 57 of
    // them made layer A the longest thing in the architect's page)
    const applied = L.rows.filter(r => r.status !== "not_applicable" || changed.has(r.rule_id));
    const na = L.rows.filter(r => !applied.includes(r));
    const naRow = na.length ? `<tr class="na-row"><td colspan="5"><details class="fold na-fold"><summary>${na.length} rule${na.length === 1 ? "" : "s"} not applicable here, for other districts, policies or programs</summary>
        <table class="plain"><tbody>${na.map(row).join("")}</tbody></table></details></td></tr>` : "";
    const rows = applied.map(row).join("") + naRow;
    const revised = L.rows.some(r => changed.has(r.rule_id));
    return `<details class="layer" data-layer="${h(L.layer)}"${revised ? " open" : ""}>
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
