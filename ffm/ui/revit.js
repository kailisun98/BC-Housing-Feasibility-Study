/* Export to Revit: the two lines that build sheet FFM-01 for the memo on screen, and Check Revit result. */

import { $, $$, copyText, fmtNum, h, setStatus } from "./core/util.js";
import { state, STATIC } from "./core/state.js";
import { api, postJSON } from "./core/api.js";
import { rev } from "./runs.js";
import { renderMemo } from "./memo/memo.js";

function psLines(run) {
  const f = run.files || {};
  return [
    `$env:FFM_MASSING_JSON = "${f.massing_json || "C:\\path\\to\\the-downloaded\\massing.json"}"`,
    `$env:FFM_SAVE_AS      = "${(run.folder_abs || "C:\\path\\to\\the-downloaded")}\\ffm_massing.rvt"`,
    `# $env:FFM_TEMPLATE   = "C:\\path\\to\\your-office-template.rte"   # optional; default is Revit's metric template`,
    `pyrevit run "${f.script || "revit\\ffm_massing_pyrevit.py"}" --revit=2026   # the year 'pyrevit env' reports`,
  ].join("\n");
}

/* What Revit receives from this run, in one line, as revit/ffm_massing_pyrevit.py builds it: the masses
   (stage_masses, with a floor plate per storey of the proposed one), the lot and setback lines, a level and a block
   per zone from layout.json where it sits beside massing.json (corridors and spare left out), three views and sheet
   FFM-01 with the answers and the open items (20 Nov 2026: the panel never said). */
function revitGets(run) {
  const m = run.massing || {}, L = run.layout || null;
  const masses = (m.masses || []).map(x => x.name).filter(Boolean);
  const prop = (m.masses || []).find(x => x.name === "proposed");
  const massWords = masses.length === 2 ? "the two masses, proposed and outright" : masses.length === 1 ? `one mass, ${masses[0]}` : "the masses";
  const plates = prop && prop.storeys > 1 ? `, ${prop.storeys - 1} floor plate${prop.storeys - 1 === 1 ? "" : "s"} in the proposed one` : "";
  const floors = L && Array.isArray(L.floors) ? L.floors : [];
  const blocks = floors.reduce((t, fl) => t + (fl.zones || []).filter(z => z.block !== "spare" && z.block !== "corridor").length, 0);
  const layout = floors.length ? `, ${floors.length} level${floors.length === 1 ? "" : "s"} with ${blocks} floor blocks from layout.json (corridors left out)` : "";
  return `Revit gets ${massWords}${plates}, the lot line and the setback envelope${layout}, a 3D view, a plan and a section, and sheet FFM-01 with the answers, the open items and the figures, exported as PDF and PNG.`;
}

export function renderExportPanel(run) {
  const f = run.files || {};
  const panel = $("#export-panel");
  panel.innerHTML = `
    <h3>Export to Revit</h3>
    <p class="export-gets">${h(revitGets(run))}</p>
    <div class="block">
      <span class="eyebrow">This run's massing.json</span>
      <div class="codeline"><code class="path" id="exp-path">${h(f.massing_json || (STATIC ? "Download massing.json from the action bar above and save it next to this run's ledger.json on the machine that has Revit." : "This run has no massing.json."))}</code><button class="btn btn-quiet btn-small" type="button" data-copy="exp-path">Copy</button></div>
    </div>
    <div class="block">
      <span class="eyebrow">Headless, through the pyRevit CLI (PowerShell, Revit closed)</span>
      <div class="codeline"><pre id="exp-ps">${h(psLines(run))}</pre><button class="btn btn-quiet btn-small" type="button" data-copy="exp-ps">Copy</button></div>
      <p>About a minute. It creates a project, builds the masses, views, annotations and sheet FFM-01, exports the sheet as PDF and PNG next to the massing.json, saves the .rvt, and writes ffm_revit_result.json.</p>
    </div>
    <div class="block">
      <span class="eyebrow">Inside Revit</span>
      <p>pyRevit › Tools › Run, pick <code>revit/ffm_massing_pyrevit.py</code>, and choose this run's massing.json in the dialog (or set FFM_MASSING_JSON before starting Revit). Open sheet FFM-01 from the Project Browser.</p>
    </div>
    <div class="block">
      <span class="eyebrow">Result</span>
      ${STATIC ? `<p>The Revit step runs on a machine with Revit. Its result and the sheet image appear here when the page is served there with <code>python -m ffm ui</code>.</p>`
               : `<div><button id="check-revit" class="btn" type="button">Check Revit result</button></div><div id="revit-result" class="revit-result"></div>`}
    </div>`;
  panel.hidden = false;
  $("#revit-btn").setAttribute("aria-expanded", "true");
  $$("[data-copy]", panel).forEach(b => b.addEventListener("click", () => copyText($("#" + b.dataset.copy).textContent)));
  if (!STATIC) {
    $("#check-revit").addEventListener("click", checkRevit);
    if (run.revit) checkRevit();
  }
}

export function closeExportPanel() {
  $("#export-panel").hidden = true;
  $("#revit-btn").setAttribute("aria-expanded", "false");
}

async function checkRevit() {
  const run = state.run;
  if (!run) return;
  const box = $("#revit-result");
  box.innerHTML = `<p class="cont">Reading ffm_revit_result.json…</p>`;
  setStatus("Reading the Revit result for this run…", "busy");
  try {
    const r = await api(`/api/runs/${run.run_id}/ffm_revit_result.json`);
    if (r.stamp !== run.stamp) {
      box.innerHTML = `<p class="err">A result exists in this folder, but it was built from another version of the rules than this memo's. Run the script again on this folder.</p>`;
      setStatus(`The Revit result in this folder was built from another version of the rules than ${rev(run.run_id)}: run the script again on this folder.`, "error");
      return;
    }
    const refreshed = await postJSON(`/api/runs/${run.run_id}/memo`, {});   // memo gains its "Built in Revit" section
    run.revit = refreshed.revit;
    box.innerHTML = revitResultHtml(r, run);
    renderMemo(run);
    const bad = Object.entries(r.stages || {}).filter(([, v]) => v !== "ok").map(([k]) => k);
    setStatus(bad.length ? `Read the Revit result: stages ${bad.join(", ")} did not finish; the others stand.` : `Read the Revit result: every stage ok, and the memo now has its "Built in Revit" section.`, bad.length ? "error" : "ok");
  } catch (e) {
    box.innerHTML = `<p class="cont">${h(e.message)} Nothing built for this run yet: run the script, then check again.</p>`;
    setStatus("No Revit result for this run yet: run the script, then check again.", "info");
  }
}

function revitResultHtml(r, run) {
  const base = `/api/runs/${run.run_id}`;
  const stages = Object.entries(r.stages || {}).map(([k, v]) => `<span class="pill pill-${v === "ok" ? "pass" : "fail"}">${h(k)}</span>`).join("");
  const items = (r.built || []).map(b => {
    switch (b.kind) {
      case "mass": return `Mass <b>${h(b.name)}</b> (element ${h(b.element_id)}): ${h(b.storeys)} storeys, ${h(b.height_m)} m, plate ${fmtNum(b.plate_area_m2)} m², FSR ${h(b.fsr)}.`;
      case "floor plates": return `Floor plates: ${h(b.count)}.`;
      case "model lines": return `Model lines: lot ${h(b.lot)}, setback envelope ${h(b.envelope)}.`;
      case "view": return `View ${h(b.name)} (element ${h(b.element_id)}).`;
      case "annotations": return `Annotations: ${h(b.dimensions)} dimensions, ${h(b.notes)} notes, ${h(b.section_lines)} benchmark lines.`;
      case "sheet": return `Sheet <b>${h(b.number)}</b> (element ${h(b.element_id)}), title block: ${b.title_block ? "yes" : "none in template"}.`;
      case "sheet layout": return `Views placed at 1:${h(b.scale)}.`;
      default: return null;
    }
  }).filter(Boolean);
  const exports = (r.exports || []).map(e => { const n = String(e).split(/[\\/]/).pop(); return `<a href="${base}/${h(n)}" target="_blank" rel="noopener">${h(n)}</a>`; }).join(", ");
  return `
    <div class="stages">${stages}</div>
    <ul>${items.map(i => `<li>${i}</li>`).join("")}${r.removed_links ? `<li>${r.removed_links.length} broken template link(s) removed before building.</li>` : ""}${r.saved_as ? `<li>Saved as <code>${h(r.saved_as)}</code>.</li>` : ""}${exports ? `<li>Exported ${exports}.</li>` : ""}</ul>
    ${r.errors && r.errors.length ? `<p class="err">${r.errors.length} stage error(s): ${r.errors.map(e => h(e.stage)).join(", ")}. The stages marked ok stand; the traceback is in ffm_revit_result.json.</p>` : ""}
    ${run.revit && run.revit.sheet_png ? `<a href="${base}/ffm_sheet.png" target="_blank" rel="noopener"><img src="${base}/ffm_sheet.png?t=${Date.now()}" alt="Revit sheet"></a>` : ""}`;
}
