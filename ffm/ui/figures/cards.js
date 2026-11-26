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
import { BLOCK_TONE, BLOCK_WORD, fitLabels, northArrow, outrightLimit, projectTurn, siteContext, turnFrame, upright } from "./common.js";
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
      ${ctx.osm && ctx.osm.bearing != null ? `<button type="button" class="btn btn-small btn-quiet fig-toggle" id="fig-shadows" aria-pressed="${!!VIEW3D.shadows}" title="The mass's shadow at the equinox, 10 am, noon and 2 pm daylight time, on flat ground: a first reading, not a shadow study">Shadows</button>` : ""}
      ${state.run && state.run.layout ? `<button type="button" class="btn btn-small btn-quiet fig-toggle" id="fig-program" aria-pressed="${!!VIEW3D.program}" title="Draw the mass as its program: every floor's blocks in their tones in 3D, the ground floor's in plan">Program</button>` : ""}
      ${boundaryTools(m)}
    </div>
    ${massTools(m)}
    <div class="fig-body${three ? " fig3d" : ""}">${three ? fig3d(m, ctx, VIEW3D.az, VIEW3D.el, fs) : figPlan(m, ctx, fs)}</div>
    ${VIEW3D.program && state.run && state.run.layout ? `<p class="fig-legend">${[...new Set(state.run.layout.floors.flatMap(fl => fl.zones.map(z => z.block)))].filter(k => BLOCK_TONE[k]).map(k => `<span><i style="background:${BLOCK_TONE[k]}"></i>${h(BLOCK_WORD[k] || k)}</span>`).join("")}${three ? "" : `<span class="cont">the ground floor; the 3D view stacks every floor</span>`}</p>` : ""}
    ${VIEW3D.shadows && ctx.osm && ctx.osm.bearing != null ? `<p class="fig-hint">Shadows at the equinox at 10 am, noon and 2 pm daylight time, from the mass on flat ground: a first reading, not the shadow study the City asks for.</p>` : ""}
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
  return `<details class="mass-tools"${mass.open ? " open" : ""}><summary>Place the mass and choose the front <span class="cont">· ${h(ANCHOR_NAMES.find(([k]) => k === cur.anchor)?.[1] || cur.anchor)}${cur.dx_m || cur.dy_m ? `, shifted ${h(cur.dx_m)} / ${h(cur.dy_m)} m` : ""}${cur.rotate ? ", turned a quarter" : ""}${cur.angle_deg ? `, turned ${h(cur.angle_deg)}°` : ""}${pl.clamped ? " · held inside the envelope" : ""}</span></summary>
    <div class="mass-row">
      <div class="mass-anchor" role="group" aria-label="Where the mass stands in the plate box">${ANCHOR_NAMES.map(([k, l]) => `<button type="button" class="segbtn" data-anchor="${k}" aria-pressed="${cur.anchor === k}" title="${h(l)}"><span class="sr-only">${h(l)}</span></button>`).join("")}</div>
      <!-- each control is named by its visible label, the longer sense said as its description (24 Nov 2026: the
           aria-labels replaced "Across (m)" with words a voice user could not see to say) -->
      <span class="sr-only" id="mass-dx-d">shifts the mass along the frontage</span><span class="sr-only" id="mass-dy-d">shifts the mass into the lot</span>
      <span class="sr-only" id="mass-angle-d">turns the mass on the lot, counter-clockwise; a corner past the setback envelope is said, not moved back</span><span class="sr-only" id="mass-front-d">which face of the lot is the street side</span>
      <label class="field inline"><span class="label">Across (m)</span><input type="number" step="0.5" id="mass-dx" value="${h(cur.dx_m)}" aria-describedby="mass-dx-d"></label>
      <label class="field inline"><span class="label">Back (m)</span><input type="number" step="0.5" id="mass-dy" value="${h(cur.dy_m)}" aria-describedby="mass-dy-d"></label>
      <label class="ed-acc"><input type="checkbox" id="mass-rotate"${cur.rotate ? " checked" : ""}> turn a quarter</label>
      <label class="field inline"><span class="label">Turn (°)</span><input type="number" step="1" min="-180" max="180" id="mass-angle" value="${h(cur.angle_deg || 0)}" aria-describedby="mass-angle-d" title="Turn the mass on the lot by any angle, counter-clockwise; a corner past the setback envelope is said, not moved back"></label>
      <label class="field inline"><span class="label">Front</span><select id="mass-front" aria-describedby="mass-front-d">
        <option value=""${ffVal === "" ? " selected" : ""}>as found (${h((state.site.context && state.site.context.street && state.site.context.street.name) || "the lookup's street")})</option>
        ${roads.map(r => `<option value="street:${h(r)}"${ffVal === `street:${r}` ? " selected" : ""}>${h(r)}</option>`).join("")}
        ${["front", "rear", "left", "right"].map(s => `<option value="side:${s}"${ffVal === `side:${s}` ? " selected" : ""}>the ${s} side as drawn</option>`).join("")}
        ${corners ? corners.map((c, i) => `<option value="edge:${i}"${ffVal === `edge:${i}` ? " selected" : ""}>lot edge ${i} (${h(Math.round(Math.hypot(corners[(i + 1) % corners.length][0] - c[0], corners[(i + 1) % corners.length][1] - c[1]) * 10) / 10)} m)</option>`).join("") : ""}
      </select></label>
      <button type="button" class="btn btn-small btn-primary" id="mass-apply"${mass.busy ? " disabled" : ""}>${mass.busy ? "Rebuilding…" : "Place it"}</button>
      <span class="help">${(box.w ?? m.envelope.width_m) > 0 && (box.d ?? m.envelope.depth_m) > 0 ? `Inside the plate box, ${h(box.w ?? m.envelope.width_m)} × ${h(box.d ?? m.envelope.depth_m)} m; a shift past it is held back and said so.` : "No plate fits on the lot as fronted: the yards leave nothing to place the mass in."} The front sets the yards and turns the lot; the sheets follow. Run the rules to make the memo from it.</span>
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
    // the plate's own dimensions (set in the block editor) stay; the angle is this control's as well
    const was = state.option.massing || {}, angle = Number($("#mass-angle", box).value) || 0;
    if (was.width_m > 0 && was.depth_m > 0) Object.assign(spec, { width_m: was.width_m, depth_m: was.depth_m });
    if (angle) spec.angle_deg = Math.max(-180, Math.min(180, angle));
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
      const warn = (run.massing.warnings || []).filter(w => /moved|turned plate|front|past the setback/i.test(w));
      setStatus(`The mass stands ${ANCHOR_NAMES.find(([k]) => k === anchor)?.[1].toLowerCase() || anchor}${spec.rotate ? ", turned a quarter" : ""}${spec.angle_deg ? `, turned ${spec.angle_deg}°` : ""}: plate ${pm.plate_width_m} × ${pm.plate_depth_m} m${frontChanged ? `; the front is ${state.site.front_face ? frontFaceWords(state.site.front_face) : "as found"} and the lot is turned to it` : ""}.${warn.length ? ` ${warn[0]}` : ""} The sheets follow; Run the rules makes the memo from it.`, warn.length ? "info" : "ok");
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
    if (sec) fitLabels(sec, fs => figSection(m, fs, ctx));
    wireOrbit();
    if (bnd.open) loaded.boundary.wireBoundaryCanvas(fig, redraw);   // open means its module is in
  };
  const redraw = () => { fig.innerHTML = figOne(m, ctx); wireFigures(run); };
  wireBoundary(fig, run, redraw);
  wireMassTools(fig, run, redraw);
  for (const [id, key] of [["#fig-shadows", "shadows"], ["#fig-program", "program"]]) {
    const t = $(id, fig);
    if (t) t.addEventListener("click", () => { VIEW3D[key] = !VIEW3D[key]; redraw(); const again = $(id, $("#fig-01")); if (again) again.focus(); });
  }
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

/* How a mass's floor area is made, in words: one plate times its storeys, or a tower's podium and tower plates each
   times theirs (25 Nov 2026: "plate 1,750 m² × 18 = 15,000 m²" on a tower whose upper 15 floors are 650 m²). */
export function plateWords(x) {
  if (x.tower && x.podium_storeys) {
    const P = Number(x.podium_storeys), S = Number(x.storeys);
    return `podium ${fmtNum(x.plate_area_m2)} m² × ${P} + tower ${fmtNum(x.tower.area_m2)} m² × ${S - P}`;
  }
  if (x.tower) return `tower plate ${fmtNum(x.tower.area_m2)} m² × ${x.storeys}`;
  return `plate ${fmtNum(x.plate_area_m2)} m² × ${x.storeys}`;
}

/* One mass in words. Where no plate fits it says so instead of "plate 0 m² × 3 = 0 m² (FSR 0.00)" (20 Nov 2026). */
export function massLine(x) {
  if (!(x.plate_area_m2 > 0)) return `<b>${h(x.label)}</b>: no plate fits on the lot as fronted.`;
  return `<b>${h(x.label)}</b>: ${plateWords(x)} = ${fmtNum(x.gfa_m2)} m² (FSR ${Number(x.fsr).toFixed(2)}), ${h(x.height_m)} m high.`;
}

/* FIG 01's caption and FIG 02's, two or three short lines each with the figures that matter in ink (20 Nov 2026: four
   to six grey lines with the numbers buried, and two near-identical notes about the lot's area on 375 Glen Drive). */
const yd = v => (Number(v) || 0).toFixed(1);
const yardWords = sb => sb.front === sb.rear && sb.rear === sb.side ? `yards of ${yd(sb.front)} m all round` : `yards front ${yd(sb.front)}, rear ${yd(sb.rear)}, sides ${yd(sb.side)} m`;

function planCaption(m, ctx) {
  const sb = m.envelope.setbacks_m || {}, lot = m.lot;
  const plate = m.envelope.width_m > 0 && m.envelope.depth_m > 0;
  const room = plate ? `<b>${h(m.envelope.width_m)} × ${h(m.envelope.depth_m)} m</b> ${lot.bbox ? "of plate box, dotted" : "to build on, dashed red"}` : "<b>no plate on the lot as fronted</b>";
  const first = lot.bbox
    ? `<b>Lot ${fmtNum(Math.round(lot.polygon_area_m2 || lot.area_m2))} m²</b>, ${lot.source === "drawn" ? "drawn in the tool" : "the City's parcel"} (${h(String((lot.shape || {}).class || "polygon").replace(/_/g, " "))}, ${h(cornerCount(lot))} corners; equivalent rectangle ${h(lot.frontage_m)} × ${h(lot.depth_m)} m); ${yardWords(sb)} leave ${room}.`
    : `<b>Lot ${h(lot.frontage_m)} × ${h(lot.depth_m)} m, ${fmtNum(lot.area_m2)} m²</b>; ${yardWords(sb)} leave ${room}.`;
  const up = ctx.osm && ctx.osm.bearing != null ? "North up" : "The street at the bottom";
  let context;
  if (ctx.osm) {
    const om = ctx.osm.omitted || [];
    context = `Context: ${h(ctx.osm.attribution)}, fetched ${h(ctx.osm.fetched)}${om.length ? `; ${om.length === 1 ? "the building now on the lot" : `the ${om.length} buildings now on the lot`} left out` : ""}.`;
  } else {
    const around = [ctx.street.name + " in front"];
    if (ctx.lane) around.push("a lane behind");
    for (const x of ctx.cross) around.push(`${x.name} to the ${x.side}`);
    context = `Context schematic: ${h(around.join(", "))}.${state.mode === "architect" ? ` <code>python -m ffm context --site sites/${h(m.site_id)}.json</code> draws it from OpenStreetMap.` : ""}`;
  }
  const kept = ctx.trees.filter(t => t.retained).length, gone = ctx.trees.length - kept, tr = m.trees;
  const trees = ctx.trees.length || tr
    ? ` Trees: ${ctx.trees.length ? `${kept} kept, ${gone} to remove (×)${ctx.schematic ? ", placed schematically" : ""}` : ""}${tr ? `${ctx.trees.length ? "; " : ""}Schedule C asks <b>${h(tr.required)}</b>, the plan leaves <b>${h(tr.after)}</b>` : ""}.`
    : "";
  return `${first} ${up}; A–A is the section, FIG 02. ${context}${trees}`;
}

/* The lot's area against the recorded site area, said once, under the plan (it was a warning under the section as
   well, twice over on 375 Glen Drive). */
const LOT_AREA_WARNING = /not a clean rectangle|lot polygon measures/i;
function lotAreaNote(m) {
  const lot = m.lot, rec = Number(lot.area_m2), poly = Number(lot.polygon_area_m2);
  if (lot.bbox && poly && rec && Math.abs(poly - rec) / rec > 0.05) {
    const noun = lot.source === "drawn" ? "lot as drawn" : "City's parcel";
    return `The ${noun} measures ${fmtNum(Math.round(poly))} m² against the ${fmtNum(rec)} m² recorded: the plan draws the ${lot.source === "drawn" ? "drawn lot" : "parcel"}, the FSR reads the recorded area. Which is the development site is a question for a person.`;
  }
  const w = (m.warnings || []).find(x => LOT_AREA_WARNING.test(x));
  return w ? String(w).replace(/(\d) x (\d)/g, "$1 × $2") : "";
}

function sectionCaption(m) {
  const pm = m.masses.find(x => x.name === "proposed"), om = m.masses.find(x => x.name === "outright");
  const lim = outrightLimit(m), b = m.policy_benchmark;
  const hm = v => { const r = Math.round(Number(v) * 100) / 100; return Math.abs(r * 10 - Math.round(r * 10)) < 1e-6 ? r.toFixed(1) : r.toFixed(2); };
  const parts = [];
  if (pm) parts.push(pm.plate_area_m2 > 0
    ? `<b>Proposed: ${h(pm.storeys)} storeys, ${hm(pm.height_m)} m</b>, ${plateWords(pm)} = ${fmtNum(pm.gfa_m2)} m², FSR ${Number(pm.fsr).toFixed(2)}.`
    : `<b>Proposed: ${h(pm.storeys)} storeys, ${hm(pm.height_m)} m</b>; no plate fits on the lot as fronted.`);
  if (om) parts.push(`<b>Outright: ${h(om.storeys)} storeys, ${hm(om.height_m)} m</b>${lim ? (Math.abs(lim - om.height_m) > 0.05 ? `, whole storeys under the ${hm(lim)} m limit` : `, at the ${hm(lim)} m limit`) : ""}, FSR ${h(om.fsr)}${om.plate_area_m2 > 0 ? "" : "; no plate fits"}.`);
  if (b && b.height_m) parts.push(`Staff benchmark ${hm(b.height_m[0])} to ${hm(b.height_m[1])} m, about FSR ${h(b.fsr)} (<code>${h(b.rule_id)}</code>).`);
  return parts.join(" ");
}

export function renderFigures(run) {
  const m = run.massing;
  const out = [];
  if (m) {
    const ctx = siteContext(run.ledger && run.ledger.inputs && run.ledger.inputs.site, m);
    const lotNote = lotAreaNote(m);
    out.push(`<figure class="card figure">
      <div id="fig-01">${figOne(m, ctx)}</div>
      <div class="legend"><span><i class="fig-proposed"></i>proposed</span><span><i class="fig-outright"></i>outright, dashed over it</span><span><i class="fig-env"></i>setback envelope</span><span><i class="fig-tree"></i>tree</span><span><i class="fig-building"></i>building</span><span><i class="fig-context"></i>road</span></div>
      <figcaption>${planCaption(m, ctx)}</figcaption>
      ${lotNote ? `<p class="note">${h(lotNote)}</p>` : ""}
    </figure>`);
    const bench = m.policy_benchmark;
    // the engine's notes the section bears on; the lot's area is said under the plan, and a height that adds nothing
    // over its storeys ("the extra 0.0 m") is no note
    const notes = (m.warnings || []).filter(w => !LOT_AREA_WARNING.test(w) && !/extra 0\.0 m/.test(w));
    out.push(`<figure class="card figure">
      <div class="eyebrow">FIG 02 · Section A–A through the lot</div>
      <div class="fig-section" id="fig-02">${figSection(m, null, ctx)}</div>
      <div class="legend"><span><i class="fig-proposed"></i>proposed</span><span><i class="fig-outright"></i>outright</span>${outrightLimit(m) ? `<span><i class="fig-limit"></i>outright limit</span>` : ""}${bench && bench.height_m ? `<span><i class="fig-bench"></i>staff benchmark</span>` : ""}<span><i class="fig-env"></i>setback envelope</span></div>
      <figcaption>${sectionCaption(m)}</figcaption>
      ${notes.map(w => `<p class="note">${h(String(w).replace(/(\d) x (\d)/g, "$1 × $2"))}</p>`).join("")}
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
  // a re-rendered memo redraws this figure, so an open editor is put away; in architect mode it comes back on the
  // floor it was on (23 Nov 2026: after Apply and Run the rules the architect had to reopen it and find the floor again)
  editor.resume = editor.open && state.mode === "architect" ? { level: editor.level } : null;
  editor.open = false;
  editor.result = null;  // and the floor picker reads this run's layout until the editor has checked a placement
  if (planFloor != null && !L.floors[planFloor]) planFloor = null;
  const fig = k => `FIG ${String(k).padStart(2, "0")}`;
  const rules = (L.adjacencies || []).filter(c => c.status !== "info");
  const prog = (L.program || []).map(b => `${b.count > 1 ? `${b.count} ` : ""}${b.label.toLowerCase()} ${fmtNum(Math.round(b.area_m2))} m²`).join(", ");
  const short = (L.shortfall || []).length ? ` Did not fit: ${L.shortfall.map(s => `${s.units ? `${s.units} ` : ""}${s.label.toLowerCase()} (${fmtNum(Math.round(s.area_m2))} m²)`).join("; ")}; more storeys, a larger plate or a smaller program.` : "";
  const out = [];
  const broken = (L.geometry || []).map(g => `<li>${pill("fail")}<span><span class="title">broken:</span> <span class="cont">${h(g.note)}.</span></span></li>`).join("");
  // the plans and the stacking are the architect's working drawings. Every layout shows them, stamped as a first layout
  // until the architect marks the memo issued back to the manager (24 Nov 2026: they were hidden from the manager and
  // the reader until then, while answer 3 cited "70 of 105 homes fit the plate" and the PDF printed them; Kai's rule of
  // 15 Nov 2026, that the plans are the architect's to check, is kept by the stamp)
  const stamp = `<span class="layout-stamp">First layout from the rules · not yet checked by the architect</span>`;
  out.push(`<figure class="card figure sheet layout-sheet" data-sheet="plans">
    <div class="fig-head"><div class="eyebrow">${fig(n0)} · Plans by program${L.edited ? ' <span class="cont">· placed by hand</span>' : ""}</div>${stamp}
      <div class="fig-tools"><div class="seg" role="group" aria-label="Plans or axonometric"><button type="button" class="segbtn" data-sheet-view="plans" aria-pressed="true">Plan</button><button type="button" class="segbtn" data-sheet-view="axon" aria-pressed="false">Axon</button></div>
      <button type="button" class="btn btn-small" id="edit-blocks" aria-expanded="false" title="Drag, resize, add or remove the blocks; the engine checks every move">Edit blocks</button></div></div>
    <div class="sheet-body" data-view="plans">
      <div class="seg plans-floors" role="group" aria-label="Which floor plan to show">${planFloorButtons(L)}</div>
      <div class="plans-overview"${planFloor == null ? "" : " hidden"}>${S.plans || ""}</div>
      <div class="plans-floor"${planFloor == null ? " hidden" : ""}>${planFloor == null ? "" : floorPlanHtml(L, planFloor)}</div>
    </div>
    <div class="sheet-body" data-view="axon" hidden>${S.axon || ""}</div>
    <div class="sheet-editor" id="sheet-editor" hidden></div>
    <figcaption><b>${h(L.units_placed)} of ${h(L.units_total)} units</b> on ${h(L.floors.length)} floors of ${h(L.plate.width_m)} × ${h(L.plate.depth_m)} m; ${L.plate.arrangement === "point" ? `a point tower, the homes round a corridor ringing the core, ${h(L.plate.unit_depth_m)} m deep in front and behind and ${h(L.plate.side_depth_m)} m beside` : L.plate.arrangement === "walkup" ? `a walk-up: one stair on the street side and no elevator, every home the plate's full depth (one exit taken for a small floor, a placeholder until the code's own clauses are in the rules)` : `${L.plate.double_loaded ? "a double-loaded corridor" : "single-loaded, the depth is the limit"}, units ${h(L.plate.unit_depth_m)} m deep`}. Program: ${h(prog)}.${h(short)}${L.edited ? " Placed by hand in the block editor and re-checked by the engine; the option carries the placement, so a run reproduces it." : ""}</figcaption>
    <ul class="finding-list sheet-rules">${broken}${rules.map(c => `<li>${pill(c.status)}<span><span class="title">${h(c.block.replace(/_/g, " "))}:</span> <span class="cont">${h(c.rule)}. ${h(c.note ? c.note[0].toUpperCase() + c.note.slice(1) : "")}</span></span></li>`).join("")}</ul>
    ${egressHtml(L.egress)}
  </figure>`);
  out.push(`<figure class="card figure sheet layout-sheet"><div class="fig-head"><div class="eyebrow">${fig(n0 + 1)} · Stacking</div>${stamp}</div><div class="sheet-body">${S.stacking || ""}</div>
    <figcaption>One bar per floor, top first; each segment the share of the plate a block takes. Core and corridor are the same on every floor; what is left after the units is spare, dashed.</figcaption></figure>`);
  out.push(`<figure class="card figure sheet"><div class="eyebrow">${fig(n0 + 2)} · Preliminary elevations</div><div class="sheet-body">${S.elevations || ""}</div>
    <figcaption>Storeys × floor to floor; one window per unit on its side as the rhythm, the ground floor glazed where the non-residential space is; the outright height dashed grey${run.massing && run.massing.policy_benchmark && run.massing.policy_benchmark.height_m ? ", the staff benchmark amber" : ""}. A placeholder for the elevation study, not a design.</figcaption></figure>`);
  out.push(`<figure class="card figure sheet"><div class="eyebrow">${fig(n0 + 3)} · Code site plan</div><div class="sheet-body">${S["site-plan"] || ""}</div>
    <figcaption>The lot, the yards dimensioned, the setback envelope dashed red, the footprint blue, tree protection barriers where the survey gives positions; the table reads FSR, height, coverage and yards against the schedule where the stack has one.</figcaption></figure>`);
  return out;
}

/* The floor picker on Plans by program (17 Nov 2026): the engine's sheet draws the ground, a typical and the top
   floor; the architect picks any floor and its plan is drawn here from the same layout record (`layout.floors`),
   to the same conventions: metres, the street at the bottom, the blocks in their tones, the exits read beside the
   title. The block editor's checks redraw it (`refreshPlanFloor`). */
let planFloor = null;   // null: the sheet's overview; else the level shown

const PLAN_TONE = { studio: "#dbe9f8", one_bed: "#b9d4f0", two_bed: "#8fb8e3", three_bed_plus: "#6b9fd4", corridor: "#f4f4f2", core: "#c9c9c5", services: "#e2e2df", amenity: "#f6e7c1", non_residential: "#f0cf9a", other: "#e6dfd0", spare: "#ffffff", design_space: "#d9e6d2", commercial: "#f3c9b5", void: "#ffffff" };
const PLAN_SHORT = { studio: "st", one_bed: "1b", two_bed: "2b", three_bed_plus: "3b", corridor: "corridor", core: "core", services: "services", amenity: "amenity", non_residential: "non-res", spare: "", design_space: "design space", commercial: "commercial", void: "open" };
const PLAN_UNITS = [["three_bed_plus", "three-bedroom"], ["two_bed", "two-bedroom"], ["one_bed", "one-bedroom"], ["studio", "studio"]];
const planLayout = run => editor.result || run.layout;
const floorShort = lv => lv === 0 ? "Ground" : `L${lv + 1}`;

function planFloorButtons(L) {
  return `<button type="button" class="segbtn" data-plan-floor="" aria-pressed="${planFloor == null}" title="The sheet: the ground, a typical and the top floor">Overview</button>`
    + L.floors.map(fl => `<button type="button" class="segbtn" data-plan-floor="${fl.level}" aria-pressed="${planFloor === fl.level}" title="${h(fl.name)}">${h(floorShort(fl.level))}</button>`).join("");
}

function floorPlanHtml(L, lv) {
  const fl = L.floors[lv], p = L.plate;
  if (!fl) return "";
  const W = 760, M = 34, scale = (W - 2 * M) / (p.width_m || 1), H = p.depth_m * scale + 2 * M;
  const f = v => v.toFixed(1);
  const zones = fl.zones.map(z => {
    const x = M + (z.x - p.x) * scale, y = M + (p.depth_m - (z.y - p.y) - z.d) * scale, w = Math.max(1, z.w * scale), d = Math.max(1, z.d * scale);
    const name = z.name ? String(z.name) : z.block === "other" ? String(z.label || "other").toLowerCase() : (PLAN_SHORT[z.block] ?? z.block);
    const two = w > 44 && d > 34 && z.block !== "corridor" && z.block !== "spare";
    return `<rect x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(d)}" fill="${PLAN_TONE[z.block] || "#eee"}" stroke="#5f6672" stroke-width="0.8"${z.block === "spare" || z.block === "void" ? ` stroke-dasharray="4 3"` : ""}/>
      ${z.accessible ? `<circle cx="${f(x + 8)}" cy="${f(y + 8)}" r="3.6" fill="#245f9c"/>` : ""}
      ${name && w > 24 && d > 12 ? `<text x="${f(x + w / 2)}" y="${f(y + d / 2 + (two ? -2 : 4))}" font-size="11" text-anchor="middle" fill="#1f2933">${h(name)}</text>` : ""}
      ${two ? `<text x="${f(x + w / 2)}" y="${f(y + d / 2 + 12)}" font-size="9.5" text-anchor="middle" fill="#5f6672">${h(fmtNum(Math.round(z.area_m2 ?? z.w * z.d)))} m²</text>` : ""}`;
  }).join("");
  const counts = PLAN_UNITS.map(([k, word]) => [fl.zones.filter(z => z.unit === k || (z.unit == null && z.block === k)).length, word]).filter(([c]) => c).map(([c, word]) => `${c} ${word}`).join(", ");
  const eg = L.egress && (L.egress.floors || []).find(e => e.level === lv);
  // north up, as FIG 01 and the editor: the plate is drawn in its own frame and turned by the site's bearing, less
  // the angle the mass itself is turned by, where the context gives a bearing; the labels stay readable
  const ms = (editor.open && editor.massing) || (state.run && state.run.massing);
  const site = ms && ms.lot ? siteContext(state.site, ms) : null, bearing = site && site.osm ? site.osm.bearing : null;
  // project north: the plate square to the page, turned by the quarter turn nearest true north; the arrow is true north
  const plateBearing = bearing == null ? null : bearing - (p.angle_deg || 0);
  const turn = plateBearing == null ? 0 : projectTurn(plateBearing), frame = turnFrame(W, H, turn);
  return `<div class="plans-floor-head"><b>${h(fl.name)}</b><span class="cont">${counts ? ` · ${h(counts)}` : " · no units"}${fl.spare_m2 ? ` · ${h(fmtNum(Math.round(fl.spare_m2)))} m² spare` : ""}</span></div>
    ${eg ? `<div class="help">${pill(eg.status)} Exits: ${h(egressLine(eg))}${eg.notes && eg.notes.length ? ` <span class="cont">· ${h(eg.notes[0])}</span>` : ""}</div>` : ""}
    <svg viewBox="0 0 ${f(frame.W)} ${f(frame.H)}" width="${f(frame.W)}" height="${f(frame.H)}" role="img" aria-label="Plan of ${h(fl.name)}, project north up" font-family="IBM Plex Sans, Helvetica, Arial, sans-serif">
      ${frame.open}${upright(`
      <rect x="${M}" y="${M}" width="${f(p.width_m * scale)}" height="${f(p.depth_m * scale)}" fill="#ffffff" stroke="#1f2933" stroke-width="1.2"/>
      ${zones}
      <rect x="${M}" y="${M}" width="${f(p.width_m * scale)}" height="${f(p.depth_m * scale)}" fill="none" stroke="#1f2933" stroke-width="1.2"/>
      <text x="${f(M + p.width_m * scale / 2)}" y="${f(H - 10)}" font-size="11" text-anchor="middle" fill="#5f6672">${h(p.width_m)} m · street side</text>
      <text x="${M - 12}" y="${f(M + p.depth_m * scale / 2)}" transform="rotate(-90 ${M - 12} ${f(M + p.depth_m * scale / 2)})" font-size="11" text-anchor="middle" fill="#5f6672">${h(p.depth_m)} m</text>`, turn)}</g>
      ${plateBearing != null ? northArrow(frame.W - 26, 28, plateBearing - turn, 11) : ""}
    </svg>`;
}

/* Show the picked floor (or the overview) in the plans figure; called by the picker and after an editor check. */
export function refreshPlanFloor(run = state.run) {
  const fig = $('.figure.sheet[data-sheet="plans"]');
  if (!fig || !run || !run.layout) return;
  const L = planLayout(run);
  if (planFloor != null && !L.floors[planFloor]) planFloor = null;
  const bar = $(".plans-floors", fig), over = $(".plans-overview", fig), one = $(".plans-floor", fig);
  if (!bar || !over || !one) return;
  bar.innerHTML = planFloorButtons(L);
  $$("[data-plan-floor]", bar).forEach(b => b.addEventListener("click", () => { planFloor = b.dataset.planFloor === "" ? null : Number(b.dataset.planFloor); refreshPlanFloor(run); }));
  over.hidden = planFloor != null; one.hidden = planFloor == null;
  one.innerHTML = planFloor == null ? "" : floorPlanHtml(L, planFloor);
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
  // the way in from the top of the memo: the title block's "Massing and plans" goes to FIG 03 and opens the editor
  const go = $("#open-editor-btn");
  if (go) go.onclick = () => {
    const fig = $('.figure.sheet[data-sheet="plans"]');
    if (!fig) { toast("Run the rules first: the plans are drawn from a run.", true); return; }
    const y = fig.getBoundingClientRect().top + scrollY - 120;
    scrollTo({ top: Math.max(0, y), behavior: "auto" });
    loadBlocks().then(b => { if (!editor.open) b.openEditor(); }).catch(e => toast(`Could not load the block editor: ${e.message}`, true));
  };
  refreshPlanFloor();
  if (editor.resume) {
    const back = editor.resume; editor.resume = null;
    loadBlocks().then(b => { if (!editor.open && $("#sheet-editor")) b.openEditor(back); }).catch(() => {});
  }
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
    <figure class="figure p3-section"><div class="fig-head"><span class="eyebrow">Section A–A · through the lot</span></div><div class="fig-section"></div><figcaption>${outr ? massLine(outr) : ""}</figcaption></figure>
    <figure class="figure p3-axon"><div class="fig-head"><span class="eyebrow">Axonometric · drag to turn</span></div><div class="fig-body fig3d"></div><figcaption>The proposed mass over the outright envelope, from the same numbers as the plan and the section.</figcaption></figure>`;
  fitLabels($(".p3-plan .fig-body", box), fs => figPlan(m, ctx, fs));
  fitLabels($(".p3-section .fig-section", box), fs => figSection(m, fs, ctx));
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

/* A lot's corners as a hand counts them: the simplified corners where the massing records them, else the ring less the
   point that closes it (17 Nov 2026: a rectangle was captioned with 5 corners). Pure. */
function cornerCount(lot) {
  if (Array.isArray(lot.corners) && lot.corners.length) return lot.corners.length;
  const r = lot.polygon || [];
  const closed = r.length > 1 && r[0][0] === r[r.length - 1][0] && r[0][1] === r[r.length - 1][1];
  return closed ? r.length - 1 : r.length;
}
