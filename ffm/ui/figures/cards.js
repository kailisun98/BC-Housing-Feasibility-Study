/* The memo's figure cards: FIG 01 (plan | 3D, the mass placement, the boundary editor's button), FIG 02, the
   architect's sheets (plans by program, stacking, elevations, code site plan), the Revit sheet, and the 3D
   preview. The block editor and the boundary editor load on first use (core/lazy.js). */

import { $, $$, fmtNum, h, pill, setStatus, toast, todayISO } from "../core/util.js";
import { bnd, editor, state } from "../core/state.js";
import { postJSON } from "../core/api.js";
import { refreshSummary } from "../schedule.js";
import { markStale } from "../files.js";
import { refOf } from "../memo/memo.js";
import { egressLine } from "../memo/answers.js";
import { fitLabels, siteContext } from "./common.js";
import { boundaryTools, figPlan } from "./plan.js";
import { figSection } from "./section.js";
import { fig3d, VIEW3D } from "./fig3d.js";
import { applyModeToMemo } from "../modes.js";
import { loadBlocks, loadBoundary, loaded } from "../core/lazy.js";

/* The figures and the sheets, redrawn from a run whose massing changed under them (the boundary editor). */
export function rerenderFigures(run) {
  const old = $(".figures");
  if (!old) return;
  const holder = document.createElement("div");
  holder.innerHTML = renderFigures(run);
  old.replaceWith(holder.firstElementChild);
  wireFigures(run);
  applyModeToMemo();
}

function figOne(m, ctx, fs = null) {
  const three = VIEW3D.mode === "3d";
  return `<div class="fig-head">
      <div class="eyebrow">FIG 01 · ${three ? "Axonometric" : "Plan"}${m.lot.source === "drawn" ? ' <span class="cont">· boundary drawn by hand</span>' : ""}${m.lot.front_face ? ` <span class="cont">· front on ${h(frontFaceWords(m.lot.front_face))}</span>` : ""}</div>
      <div class="seg" role="group" aria-label="View of figure 1">
        <button type="button" class="segbtn" data-view="plan" aria-pressed="${!three}">Plan</button>
        <button type="button" class="segbtn" data-view="3d" aria-pressed="${three}">3D</button>
      </div>
      ${boundaryTools(m)}
    </div>
    ${massTools(m)}
    <div class="fig-body${three ? " fig3d" : ""}">${three ? fig3d(m, ctx, VIEW3D.az, VIEW3D.el, fs) : figPlan(m, ctx, fs)}</div>
    ${three ? `<p class="fig-hint">Drag sideways to turn it; the arrow keys turn and tilt it. A straight axonometric of the same massing numbers, with storey lines every ${h(m.masses[0]?.floor_to_floor_m)} m.</p>` : ""}`;
}

const frontFaceWords = ff => ff.street ? ff.street : (ff.side ? `the ${ff.side} side` : (ff.edge != null ? `lot edge ${ff.edge}` : "the chosen face"));

const ANCHOR_NAMES = [["front-left", "Front, left"], ["front", "Front, centred"], ["front-right", "Front, right"], ["left", "Left, middle"], ["centre", "Centred"], ["right", "Right, middle"], ["rear-left", "Rear, left"], ["rear", "Rear, centred"], ["rear-right", "Rear, right"]];

const mass = { open: false, busy: false };

/* The architect's placement of the mass and the choice of front face (16 Nov 2026): a fold under FIG 01's head.
   The mass goes against a side or corner of the plate box (the envelope's largest rectangle), shifted and turned a
   quarter; the front face is one of the streets that adjoin the lot, or a side of it. The engine rebuilds the
   massing and the sheets from the choice; the option (massing) and the site (front_face) carry it. */
function massTools(m) {
  if (state.mode !== "architect" || !state.option || !state.site) return "";
  const pm = m.masses.find(x => x.name === "proposed") || {};
  const pl = pm.placement || {};
  const cur = Object.assign({ anchor: pl.anchor || (pm.at_street_corner === "right" ? "front-right" : "front-left"), dx_m: pl.dx_m || 0, dy_m: pl.dy_m || 0, rotate: !!pl.rotate }, state.option.massing || {});
  const roads = [...new Set(((state.site.osm || {}).roads || []).map(r => r.name).filter(Boolean))].sort();
  const ff = state.site.front_face || null;
  const ffVal = ff ? (ff.street ? `street:${ff.street}` : ff.side ? `side:${ff.side}` : ff.edge != null ? `edge:${ff.edge}` : "") : "";
  const corners = m.lot.corners || null;
  const box = m.envelope.box || {};
  return `<details class="mass-tools"${mass.open ? " open" : ""}><summary>Place the mass and choose the front <span class="cont">· ${h(ANCHOR_NAMES.find(([k]) => k === cur.anchor)?.[1] || cur.anchor)}${cur.dx_m || cur.dy_m ? `, shifted ${h(cur.dx_m)} / ${h(cur.dy_m)} m` : ""}${cur.rotate ? ", turned a quarter" : ""}${pl.clamped ? " · held inside the envelope" : ""}</span></summary>
    <div class="mass-row">
      <div class="mass-anchor" role="group" aria-label="Where the mass stands in the plate box">${ANCHOR_NAMES.map(([k, l]) => `<button type="button" class="segbtn" data-anchor="${k}" aria-pressed="${cur.anchor === k}" title="${h(l)}"><span class="sr-only">${h(l)}</span></button>`).join("")}</div>
      <label class="field inline"><span class="label">Across (m)</span><input type="number" step="0.5" id="mass-dx" value="${h(cur.dx_m)}" aria-label="Shift along the frontage in metres"></label>
      <label class="field inline"><span class="label">Back (m)</span><input type="number" step="0.5" id="mass-dy" value="${h(cur.dy_m)}" aria-label="Shift into the lot in metres"></label>
      <label class="ed-acc"><input type="checkbox" id="mass-rotate"${cur.rotate ? " checked" : ""}> turn a quarter</label>
      <label class="field inline"><span class="label">Front</span><select id="mass-front" aria-label="Which face of the lot is the street side">
        <option value=""${ffVal === "" ? " selected" : ""}>as found (${h((state.site.context && state.site.context.street && state.site.context.street.name) || "the lookup's street")})</option>
        ${roads.map(r => `<option value="street:${h(r)}"${ffVal === `street:${r}` ? " selected" : ""}>${h(r)}</option>`).join("")}
        ${["front", "rear", "left", "right"].map(s => `<option value="side:${s}"${ffVal === `side:${s}` ? " selected" : ""}>the ${s} side as drawn</option>`).join("")}
        ${corners ? corners.map((c, i) => `<option value="edge:${i}"${ffVal === `edge:${i}` ? " selected" : ""}>lot edge ${i} (${h(Math.round(Math.hypot(corners[(i + 1) % corners.length][0] - c[0], corners[(i + 1) % corners.length][1] - c[1]) * 10) / 10)} m)</option>`).join("") : ""}
      </select></label>
      <button type="button" class="btn btn-small btn-primary" id="mass-apply"${mass.busy ? " disabled" : ""}>${mass.busy ? "Rebuilding…" : "Place it"}</button>
      <span class="help">Inside the plate box, ${h(box.w ?? m.envelope.width_m)} × ${h(box.d ?? m.envelope.depth_m)} m; a shift past it is held back and said so. The front sets the yards and turns the lot; the sheets follow. Run the rules to make the memo from it.</span>
    </div>
  </details>`;
}

function wireMassTools(fig, run, redraw) {
  const box = $(".mass-tools", fig);
  if (!box) return;
  box.addEventListener("toggle", () => { mass.open = box.open; });
  $$("[data-anchor]", box).forEach(b => b.addEventListener("click", () => { $$("[data-anchor]", box).forEach(x => x.setAttribute("aria-pressed", String(x === b))); }));
  $("#mass-apply", box).addEventListener("click", async () => {
    if (mass.busy || !state.option || !state.site) return;
    const anchor = ($('[data-anchor][aria-pressed="true"]', box) || {}).dataset?.anchor || "front-left";
    const spec = { anchor, dx_m: Number($("#mass-dx", box).value) || 0, dy_m: Number($("#mass-dy", box).value) || 0, rotate: $("#mass-rotate", box).checked };
    const fv = $("#mass-front", box).value;
    const before = JSON.stringify(state.site.front_face || null);
    if (!fv) delete state.site.front_face;
    else if (fv.startsWith("street:")) state.site.front_face = { street: fv.slice(7) };
    else if (fv.startsWith("side:")) state.site.front_face = { side: fv.slice(5) };
    else if (fv.startsWith("edge:")) state.site.front_face = { edge: Number(fv.slice(5)) };
    const frontChanged = JSON.stringify(state.site.front_face || null) !== before;
    state.option.massing = spec;
    state.optionDirty = true; $("#option-dirty").hidden = false;
    if (frontChanged) { state.siteDirty = true; $("#site-dirty").hidden = false; }
    mass.busy = true; mass.open = true; redraw();
    try {
      const res = await postJSON("/api/layout", { site: state.site, option: state.option, as_of: $("#as-of").value || todayISO() });
      run.massing = res.massing; run.layout = res.layout; run.sheets = res.sheets;
      if (run.ledger && run.ledger.inputs) { run.ledger.inputs.site = JSON.parse(JSON.stringify(state.site)); run.ledger.inputs.option = JSON.parse(JSON.stringify(state.option)); }
      mass.busy = false;
      refreshSummary("option"); if (frontChanged) refreshSummary("site");
      markStale("the massing placement");
      rerenderFigures(run);
      const pm = run.massing.masses.find(x => x.name === "proposed") || {};
      const warn = (run.massing.warnings || []).filter(w => /moved|turned plate|front/i.test(w));
      setStatus(`The mass stands ${ANCHOR_NAMES.find(([k]) => k === anchor)?.[1].toLowerCase() || anchor}${spec.rotate ? ", turned a quarter" : ""}: plate ${pm.plate_width_m} × ${pm.plate_depth_m} m${frontChanged ? `; the front is ${state.site.front_face ? frontFaceWords(state.site.front_face) : "as found"} and the lot is turned to it` : ""}.${warn.length ? ` ${warn[0]}` : ""} The sheets follow; Run the rules makes the memo from it.`, warn.length ? "info" : "ok");
    } catch (e) {
      mass.busy = false; redraw();
      toast(`Could not place the mass: ${e.message}`, true);
    }
  });
}

let figWatch = null;   // the ResizeObserver that refits the drawings' labels when their cards change width

export function wireFigures(run) {
  wireSheets();
  const fig = $("#fig-01");
  if (!fig || !run.massing) return;
  const m = run.massing;
  const ctx = siteContext(run.ledger && run.ledger.inputs && run.ledger.inputs.site, m);
  const fit = () => {
    const body = $(".fig-body", fig);
    if (body) VIEW3D.fs = fitLabels(body, fs => (VIEW3D.mode === "3d" ? fig3d(m, ctx, VIEW3D.az, VIEW3D.el, fs) : figPlan(m, ctx, fs)));
    const sec = $("#fig-02");
    if (sec) fitLabels(sec, fs => figSection(m, fs));
    wireOrbit();
    if (bnd.open) loaded.boundary.wireBoundaryCanvas(fig, redraw);   // open means its module is in
  };
  const redraw = () => { fig.innerHTML = figOne(m, ctx); wireFigures(run); };
  wireBoundary(fig, run, redraw);
  wireMassTools(fig, run, redraw);
  $$(".segbtn", fig).forEach(b => b.addEventListener("click", () => {
    if (VIEW3D.mode === b.dataset.view) return;
    VIEW3D.mode = b.dataset.view;
    if (bnd.open) { bnd.open = false; bnd.ring = null; bnd.sel = null; }   // the editor is a plan tool
    redraw();
    const now = $(`.segbtn[data-view="${VIEW3D.mode}"]`, fig);
    if (now) now.focus();
  }));

  // the axonometric turns under a drag (one redraw per frame) or the arrow keys. Its box keeps the size it was first
  // drawn at: a turn or a tilt changes only the viewBox, which the box fits by scaling (meet), so the figure and the
  // page below it never move. A change of the card's width redraws it and measures the box again.
  function wireOrbit() {
    const svg = $(".fig3d svg", fig);
    if (!svg) return;
    const boxH = Math.round(svg.getBoundingClientRect().height);
    if (boxH > 0) { svg.style.width = "100%"; svg.style.height = `${boxH}px`; }
    const turn = (daz, del) => {
      VIEW3D.az = (VIEW3D.az + daz) % 360;
      VIEW3D.el = Math.max(8, Math.min(80, VIEW3D.el + del));
      const fresh = document.createElement("div"); fresh.innerHTML = fig3d(m, ctx, VIEW3D.az, VIEW3D.el, VIEW3D.fs);
      svg.innerHTML = fresh.firstElementChild.innerHTML;
      svg.setAttribute("viewBox", fresh.firstElementChild.getAttribute("viewBox"));
    };
    let drag = null, pending = [0, 0], raf = 0;
    const flush = () => { raf = 0; if (pending[0] || pending[1]) { turn(pending[0], pending[1]); pending = [0, 0]; } };
    const stop = () => { drag = null; };
    svg.addEventListener("pointerdown", e => {
      if (e.button > 0) return;
      drag = { x: e.clientX, y: e.clientY };
      svg.setPointerCapture(e.pointerId);
      svg.focus({ preventScroll: true });
      e.preventDefault();
    });
    svg.addEventListener("pointermove", e => {
      if (!drag) return;
      pending[0] += (e.clientX - drag.x) * 0.5;
      pending[1] += (e.clientY - drag.y) * 0.4;
      drag = { x: e.clientX, y: e.clientY };
      if (!raf) raf = requestAnimationFrame(flush);
    });
    for (const ev of ["pointerup", "pointercancel", "lostpointercapture"]) svg.addEventListener(ev, stop);
    window.addEventListener("blur", stop, { once: true });
    svg.addEventListener("keydown", e => {
      const k = { ArrowLeft: [-6, 0], ArrowRight: [6, 0], ArrowUp: [0, 4], ArrowDown: [0, -4] }[e.key];
      if (k) { e.preventDefault(); turn(k[0], k[1]); }
    });
  }

  fit();
  // refit when the cards change width: a window resize, the inputs hidden or shown, the wide two-column layout
  if (figWatch) figWatch.disconnect();
  const figures = $(".figures");
  if (figures && "ResizeObserver" in window) {
    let w = Math.round(figures.getBoundingClientRect().width), raf = 0;
    figWatch = new ResizeObserver(entries => {
      const nw = Math.round(entries[0].contentRect.width);
      if (Math.abs(nw - w) < 4) return;
      w = nw;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(fit);
    });
    figWatch.observe(figures);
  }
}

export function massLine(x) {
  return `<b>${h(x.label)}</b>: plate ${fmtNum(x.plate_area_m2)} m² × ${x.storeys} = ${fmtNum(x.gfa_m2)} m² (FSR ${Number(x.fsr).toFixed(2)}), ${h(x.height_m)} m high.`;
}

export function renderFigures(run) {
  const m = run.massing;
  const out = [];
  if (m) {
    const sb = m.envelope.setbacks_m || {};
    const ctx = siteContext(run.ledger && run.ledger.inputs && run.ledger.inputs.site, m);
    let contextNote;
    if (ctx.osm) {
      const c = ctx.osm.counts, om = ctx.osm.omitted;
      contextNote = `Context in half tone from OpenStreetMap (${h(ctx.osm.attribution)}; fetched ${h(ctx.osm.fetched)}, ${h(ctx.osm.radius)} m around the address): ${c.roads ?? 0} roads, ${c.buildings ?? 0} buildings and ${c.trees ?? 0} mapped trees, with ${h(ctx.osm.frontStreet || "the nearest road")} taken as the front street.${om.length ? ` ${om.length === 1 ? "The building now on the lot is" : `${om.length} buildings now on the lot are`} left out${om[0] && om[0].name ? ` (${h(om.map(b => b.name).filter(Boolean).join(", "))})` : ""}.` : ""}`;
    } else {
      const around = [ctx.street.name + " in front"];
      if (ctx.lane) around.push("a lane behind");
      for (const x of ctx.cross) around.push(`${x.name} to the ${x.side}`);
      if (ctx.neighbours.length) around.push(ctx.neighbours.length === 2 ? "neighbouring parcels either side" : "a neighbouring parcel");
      if (ctx.streetTrees.length) around.push(`${ctx.streetTrees.length} street trees`);
      contextNote = `Context in half tone, schematic: ${h(around.join(", "))}. Run <code>python -m ffm context --site sites/${h(m.site_id)}.json</code> to draw it from OpenStreetMap instead.`;
    }
    const retained = ctx.trees.filter(t => t.retained).length, removed = ctx.trees.length - retained;
    const treeNote = ctx.trees.length ? ` On site, ${retained} tree${retained === 1 ? "" : "s"} retained and ${removed} to be removed (×)${ctx.schematic ? ", placed schematically because the survey is not on file" : ""}.` : "";
    out.push(`<figure class="card figure">
      <div id="fig-01">${figOne(m, ctx)}</div>
      <div class="legend"><span><i class="fig-proposed"></i>proposed</span><span><i class="fig-outright"></i>outright</span><span><i class="fig-env"></i>setback envelope</span><span><i class="fig-tree"></i>tree</span><span><i class="fig-building"></i>building</span><span><i class="fig-context"></i>road</span></div>
      <figcaption>${m.lot.bbox
        ? `Lot ${m.lot.source === "drawn" ? "as drawn in the tool" : "from the City's parcel polygon"}: ${h(String((m.lot.shape || {}).class || "polygon").replace(/_/g, " "))}, ${h(m.lot.polygon.length)} corners, ${fmtNum(Math.round(m.lot.polygon_area_m2 || m.lot.area_m2))} m² (recorded site area ${fmtNum(m.lot.area_m2)} m²; equivalent rectangle ${h(m.lot.frontage_m)} × ${h(m.lot.depth_m)} m). The setback envelope follows the lot lines (front ${h(sb.front)}, rear ${h(sb.rear)}, sides ${h(sb.side)} m) and the masses stand in the plate box, the largest rectangle inside it, ${h(m.envelope.width_m)} × ${h(m.envelope.depth_m)} m, dotted.`
        : `Lot ${h(m.lot.frontage_m)} × ${h(m.lot.depth_m)} m, ${fmtNum(m.lot.area_m2)} m². Setback envelope ${h(m.envelope.width_m)} × ${h(m.envelope.depth_m)} m (front ${h(sb.front)}, rear ${h(sb.rear)}, sides ${h(sb.side)} m). Both masses fill the envelope's width from the front setback back, so the outright mass is drawn dashed over the proposed one, here and in the section.`} ${contextNote}${treeNote}${ctx.osm && ctx.osm.bearing != null ? " The north arrow follows the OpenStreetMap frame; the plan is drawn with the street at the bottom." : ""}</figcaption>
    </figure>`);
    const bench = m.policy_benchmark;
    const trees = m.trees;
    out.push(`<figure class="card figure">
      <div class="eyebrow">FIG 02 · Section across the frontage</div>
      <div class="fig-section" id="fig-02">${figSection(m)}</div>
      <div class="legend"><span><i class="fig-proposed"></i>proposed</span><span><i class="fig-outright"></i>outright</span>${bench && bench.height_m ? `<span><i class="fig-bench"></i>staff benchmark</span>` : ""}</div>
      <figcaption>${m.masses.map(massLine).join(" ")}${bench && bench.height_m ? ` Staff benchmark under <code>${h(bench.rule_id)}</code>: ${h(bench.height_m[0])} to ${h(bench.height_m[1])} m, about FSR ${h(bench.fsr)}.` : ""}${trees ? ` Trees: Schedule C requires ${h(trees.required)}, the plan leaves ${h(trees.after)} (shortfall ${h(trees.shortfall)}).` : ""}</figcaption>
      ${(m.warnings || []).map(w => `<p class="note">${h(String(w).replace(/(\d) x (\d)/g, "$1 × $2"))}</p>`).join("")}
    </figure>`);
  } else if (run.massing_note) {
    out.push(`<div class="card figure"><div class="eyebrow">Massing</div><p class="note">${h(run.massing_note)}</p></div>`);
  }
  let n = m ? 3 : 1;
  if (run.layout && run.sheets) { out.push(...renderSheets(run, n)); n += 4; }
  const r = run.revit;
  if (r && r.sheet_png) out.push(figSheet(run, n));
  return `<aside class="figures">${out.join("")}</aside>`;
}

/* The architect's sheets, drawn by the engine from the option: the plans by program with an axon of the same
   floors on a tab, the stacking, the elevations and the code site plan. Every one carries the stamp. */
function renderSheets(run, n0) {
  const L = run.layout, S = run.sheets;
  editor.open = false;   // a re-rendered memo starts with the editor closed; its state lives in the option once applied
  const fig = k => `FIG ${String(k).padStart(2, "0")}`;
  const rules = (L.adjacencies || []).filter(c => c.status !== "info");
  const prog = (L.program || []).map(b => `${b.count > 1 ? `${b.count} ` : ""}${b.label.toLowerCase()} ${fmtNum(Math.round(b.area_m2))} m²`).join(", ");
  const short = (L.shortfall || []).length ? ` Did not fit: ${L.shortfall.map(s => `${s.units ? `${s.units} ` : ""}${s.label.toLowerCase()} (${fmtNum(Math.round(s.area_m2))} m²)`).join("; ")}; more storeys, a larger plate or a smaller program.` : "";
  const out = [];
  const broken = (L.geometry || []).map(g => `<li>${pill("fail")}<span><span class="title">broken:</span> <span class="cont">${h(g.note)}.</span></span></li>`).join("");
  // the plans and the stacking are the architect's working drawings: the manager sees them once the architect has
  // issued the run to them (Kai, 15 Nov 2026); until then a quiet card holds their place
  out.push(`<div class="card figure layout-wait"><div class="eyebrow">${fig(n0)} and ${fig(n0 + 1)} · Plans by program and stacking</div>
    <p class="note">The schematic plans are the architect's to draw and check. They appear here once the architect issues this run back to you; the massing above and the elevations and site plan below are the rule-derived envelope.</p></div>`);
  out.push(`<figure class="card figure sheet layout-sheet" data-sheet="plans">
    <div class="fig-head"><div class="eyebrow">${fig(n0)} · Plans by program${L.edited ? ' <span class="cont">· placed by hand</span>' : ""}</div>
      <div class="fig-tools"><div class="seg" role="group" aria-label="Plans or axonometric"><button type="button" class="segbtn" data-sheet-view="plans" aria-pressed="true">Plan</button><button type="button" class="segbtn" data-sheet-view="axon" aria-pressed="false">Axon</button></div>
      <button type="button" class="btn btn-small" id="edit-blocks" aria-expanded="false" title="Drag, resize, add or remove the blocks; the engine checks every move">Edit blocks</button></div></div>
    <div class="sheet-body" data-view="plans">${S.plans || ""}</div>
    <div class="sheet-body" data-view="axon" hidden>${S.axon || ""}</div>
    <div class="sheet-editor" id="sheet-editor" hidden></div>
    <figcaption><b>${h(L.units_placed)} of ${h(L.units_total)} units</b> on ${h(L.floors.length)} floors of ${h(L.plate.width_m)} × ${h(L.plate.depth_m)} m; ${L.plate.double_loaded ? "a double-loaded corridor" : "single-loaded, the depth is the limit"}, units ${h(L.plate.unit_depth_m)} m deep. Program: ${h(prog)}.${h(short)}${L.edited ? " Placed by hand in the block editor and re-checked by the engine; the option carries the placement, so a run reproduces it." : ""}</figcaption>
    <ul class="finding-list sheet-rules">${broken}${rules.map(c => `<li>${pill(c.status)}<span><span class="title">${h(c.block.replace(/_/g, " "))}:</span> <span class="cont">${h(c.rule)}. ${h(c.note ? c.note[0].toUpperCase() + c.note.slice(1) : "")}</span></span></li>`).join("")}</ul>
    ${egressHtml(L.egress)}
  </figure>`);
  out.push(`<figure class="card figure sheet layout-sheet"><div class="eyebrow">${fig(n0 + 1)} · Stacking</div><div class="sheet-body">${S.stacking || ""}</div>
    <figcaption>One bar per floor, top first; each segment the share of the plate a block takes. Core and corridor are the same on every floor; what is left after the units is spare, dashed.</figcaption></figure>`);
  out.push(`<figure class="card figure sheet"><div class="eyebrow">${fig(n0 + 2)} · Preliminary elevations</div><div class="sheet-body">${S.elevations || ""}</div>
    <figcaption>Storeys × floor to floor; one window per unit on its side as the rhythm, the ground floor glazed where the non-residential space is; the outright height dashed grey${run.massing && run.massing.policy_benchmark && run.massing.policy_benchmark.height_m ? ", the staff benchmark amber" : ""}. A placeholder for the elevation study, not a design.</figcaption></figure>`);
  out.push(`<figure class="card figure sheet"><div class="eyebrow">${fig(n0 + 3)} · Code site plan</div><div class="sheet-body">${S["site-plan"] || ""}</div>
    <figcaption>The lot, the yards dimensioned, the setback envelope dashed red, the footprint blue, tree protection barriers where the survey gives positions; the table reads FSR, height, coverage and yards against the schedule where the stack has one.</figcaption></figure>`);
  return out;
}

/* The exits on every floor, from the building code: under the plans, each floor a line with its status; the
   limits and the assumptions behind them named once. */
function egressHtml(eg) {
  if (!eg) return "";
  const floors = eg.floors || [];
  const lim = eg.limits || {};
  return `<details class="egress"${eg.status === "pass" ? "" : " open"}>
    <summary>${pill(eg.status)} <b>Exits</b> <span class="cont">· ${refOf(eg.rule_id) ? `<b class="ref">${h(refOf(eg.rule_id))}</b> ` : ""}BC Building Code 2024, Part 3 · ${h(eg.summary || "")}</span></summary>
    <ul class="finding-list">${floors.map(f => `<li>${pill(f.status)}<span><span class="title">${h(f.name)}:</span> <span class="cont">${h(egressLine(f))}${f.notes && f.notes.length ? `. ${h(f.notes.join(" "))}` : ""}</span></span></li>`).join("")}</ul>
    <p class="help">Two exits over ${h(lim.two_exits_over_floor_area_m2)} m² or ${h(lim.two_exits_over_occupant_load)} persons; travel at most ${h(lim.travel_limit_m)} m (${eg.sprinklered ? "sprinklered" : "not sprinklered"}${eg.sprinklered_is_placeholder ? ", assumed" : ""}); stairs at least the lesser of ${h(lim.separation_min_m)} m and half the diagonal apart; a dead end at most ${h(lim.dead_end_max_m)} m. A core ${h(lim.core_bay_m)} m wide holds two stairs of ${h(lim.stair_width_m)} m. The clause figures are entered from recollection and unverified against the code text.</p>
  </details>`;
}

function wireSheets() {
  $$(".figure.sheet [data-sheet-view]").forEach(b => b.addEventListener("click", () => {
    const fig = b.closest(".figure");
    $$("[data-sheet-view]", fig).forEach(x => x.setAttribute("aria-pressed", String(x === b)));
    if (editor.open) loaded.blocks.closeEditor();   // open means its module is in
    $$(".sheet-body", fig).forEach(x => { x.hidden = x.dataset.view !== b.dataset.sheetView; });
  }));
  const eb = $("#edit-blocks");
  if (eb) eb.addEventListener("click", () => loadBlocks()
    .then(b => (editor.open ? b.closeEditor() : b.openEditor()))
    .catch(e => toast(`Could not load the block editor: ${e.message}`, true)));
}

/* FIG 01's boundary editor: once its module is in, it wires the head itself; until then the two buttons a closed
   editor shows (Edit boundary, Set the site area) fetch it on a click and hand the click on. Either action redraws
   the figure, and the redraw wires it in full. */
function wireBoundary(fig, run, redraw) {
  if (loaded.boundary) { loaded.boundary.wireBoundary(fig, run, redraw); return; }
  const on = (sel, act) => {
    const b = $(sel, fig);
    if (b) b.addEventListener("click", () => loadBoundary()
      .then(mod => mod[act](run, redraw))
      .catch(e => toast(`Could not load the boundary editor: ${e.message}`, true)));
  };
  on("#edit-boundary", "toggleBoundary");
  on("#bnd-area", "setAreaToDrawn");
}

function figSheet(run, n = 3) {
  const r = run.revit, c = r.counts || {};
  const base = `/api/runs/${run.run_id}`;
  const stages = Object.entries(r.stages || {}).map(([k, v]) => `${k} ${v}`).join(", ");
  return `<figure class="card figure">
    <div class="eyebrow">FIG ${String(n).padStart(2, "0")} · Revit sheet ${h(r.sheet_number || "")}</div>
    <a href="${base}/ffm_sheet.png" target="_blank" rel="noopener"><img src="${base}/ffm_sheet.png" alt="The Revit sheet exported by the massing script"></a>
    <figcaption><b>${c.masses ?? "?"} masses</b>, ${c.floor_plates ?? "?"} floor plates, ${c.model_lines ?? "?"} model lines, ${c.views ?? "?"} views, ${c.dimensions ?? 0} dimensions and ${c.notes ?? 0} notes on sheet ${h(r.sheet_number || "")}; the rules fingerprint in every element's Comments. Stages: ${h(stages)}.${r.sheet_pdf ? ` <a href="${base}/ffm_sheet.pdf" target="_blank" rel="noopener">PDF</a>.` : ""}${r.errors ? ` ${r.errors} stage error(s) recorded in the result file.` : ""}</figcaption>
  </figure>`;
}

/* The 3D preview: the site plan with its dimension strings, the section, and the axonometric, each at full width,
   drawn by the same functions as the memo's figures from the same massing.json. */
export function renderPreview3D() {
  let box = $("#preview3d");
  const run = state.run;
  const memo = $("#memo");
  if (!box) { box = document.createElement("div"); box.id = "preview3d"; box.className = "preview3d"; memo.parentNode.insertBefore(box, memo); }
  if (!run || !run.massing) { box.innerHTML = `<div class="card figure"><p class="help">Run the rules, or open a run with a massing, to preview it.</p></div>`; return; }
  const m = run.massing, ctx = siteContext(run.ledger && run.ledger.inputs && run.ledger.inputs.site, m);
  const [prop, outr] = [m.masses.find(x => x.name === "proposed"), m.masses.find(x => x.name === "outright")];
  box.innerHTML = `
    <figure class="figure p3-plan"><div class="fig-head"><span class="eyebrow">Site plan · dimensions in metres</span></div><div class="fig-body"></div><figcaption>Lot ${h(m.lot.frontage_m)} × ${h(m.lot.depth_m)} m, ${h(fmtNum(m.lot.area_m2))} m²; setback envelope ${h(m.envelope.width_m)} × ${h(m.envelope.depth_m)} m. ${prop ? massLine(prop) : ""}</figcaption></figure>
    <figure class="figure p3-section"><div class="fig-head"><span class="eyebrow">Section · through the depth</span></div><div class="fig-section"></div><figcaption>${outr ? massLine(outr) : ""}</figcaption></figure>
    <figure class="figure p3-axon"><div class="fig-head"><span class="eyebrow">Axonometric · drag to turn</span></div><div class="fig-body fig3d"></div><figcaption>The proposed mass over the outright envelope, from the same numbers as the plan and the section.</figcaption></figure>`;
  fitLabels($(".p3-plan .fig-body", box), fs => figPlan(m, ctx, fs));
  fitLabels($(".p3-section .fig-section", box), fs => figSection(m, fs));
  const fs3 = fitLabels($(".p3-axon .fig-body", box), fs => fig3d(m, ctx, 35, 28, fs));
  // a light orbit for the preview's axon: a drag turns it, as in the memo
  const svg = $(".p3-axon svg", box);
  if (svg) {
    let az = 35, el = 28, drag = null;
    const turn = (dx, dy) => { az = (az + dx) % 360; el = Math.max(8, Math.min(80, el + dy)); const fresh = document.createElement("div"); fresh.innerHTML = fig3d(m, ctx, az, el, fs3); svg.innerHTML = fresh.firstElementChild.innerHTML; svg.setAttribute("viewBox", fresh.firstElementChild.getAttribute("viewBox")); };
    const boxH = Math.round(svg.getBoundingClientRect().height); if (boxH > 0) { svg.style.width = "100%"; svg.style.height = `${boxH}px`; }
    svg.addEventListener("pointerdown", e => { if (e.button > 0) return; drag = { x: e.clientX, y: e.clientY }; svg.setPointerCapture(e.pointerId); e.preventDefault(); });
    svg.addEventListener("pointermove", e => { if (!drag) return; turn((e.clientX - drag.x) * 0.5, (e.clientY - drag.y) * 0.4); drag = { x: e.clientX, y: e.clientY }; });
    for (const ev of ["pointerup", "pointercancel", "lostpointercapture"]) svg.addEventListener(ev, () => { drag = null; });
  }
}
