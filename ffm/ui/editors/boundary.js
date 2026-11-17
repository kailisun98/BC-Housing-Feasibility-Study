/* The boundary editor (architect mode, FIG 01 plan), loaded on first use. On an odd site the City's parcel polygon
   may not be the development site (a consolidated lot, a road closure, a strata of a larger parcel), and outside
   the City there is no polygon at all. "Edit boundary" puts handles on the lot line: drag a corner, click an
   edge's midpoint to add one, Delete removes the selected corner. "Use this boundary" writes the ring into the
   site (`boundary_m`, the lot frame, in metres); the massing, the layout and the sheets are rebuilt from it at
   once, and the next run reproduces it. The handles and the toolbar are drawn by figures/plan.js. */

import { $, $$, fmtNum, h, setStatus, toast, todayISO } from "../core/util.js";
import { bnd, state } from "../core/state.js";
import { postJSON } from "../core/api.js";
import { SITE_FIELDS } from "../fields.js";
import { refreshSummary, renderForm } from "../schedule.js";
import { onSiteChange } from "../files.js";
import { boundaryHandles } from "../figures/plan.js";
import { VIEW3D } from "../figures/fig3d.js";
import { rerenderFigures } from "../figures/cards.js";

/* Edit boundary | Close: handles on the lot line, or put away. */
export function toggleBoundary(run, redraw) {
  const m = run.massing;
  if (bnd.open) { bnd.open = false; bnd.ring = null; bnd.sel = null; }
  else {
    if (VIEW3D.mode !== "plan") VIEW3D.mode = "plan";
    bnd.open = true; bnd.sel = null;
    // a boundary drawn before reopens exactly as it was saved; the City's parcel opens as its simplified corners
    const drawn = state.site && state.site.boundary_m && state.site.boundary_m.length >= 3 ? state.site.boundary_m : null;
    bnd.ring = (drawn || m.lot.corners || m.lot.polygon).map(p => [p[0], p[1]]);
  }
  redraw();
  if (bnd.open) setStatus("Drag a corner of the lot line; click a square on an edge to add a corner; Delete removes the selected one; or type an edge length in the table. Use this boundary rebuilds the massing and the sheets from it.", "info");
}

/* Set the site area to the drawn lot: the recorded area follows the drawn boundary, with one click, never silently. */
export function setAreaToDrawn(run, redraw) {
  const lot = run.massing && run.massing.lot;
  if (!state.site || !lot) return;
  state.site.site_area_m2 = Math.round((lot.polygon_area_m2 || lot.area_m2) * 10) / 10;
  onSiteChange("site_area_m2");
  renderForm($("#site-form"), SITE_FIELDS, state.site, onSiteChange);
  redraw();
  setStatus(`Site area set to ${fmtNum(state.site.site_area_m2)} m², the drawn lot; the FSR and the plate cap now read it. Run the rules to make the memo from it.`, "ok");
}

export function wireBoundary(fig, run, redraw) {
  const on = (sel, fn) => { const b = $(sel, fig); if (b) b.addEventListener("click", fn); };
  on("#edit-boundary", () => toggleBoundary(run, redraw));
  on("#bnd-apply", () => applyBoundary(false, run, redraw));
  on("#bnd-parcel", () => applyBoundary(true, run, redraw));
  on("#bnd-area", () => setAreaToDrawn(run, redraw));
  // the edge table: a typed length moves the edge's far corner along the edge, so a survey can be entered
  $$(".bnd-edge", fig).forEach(inp => inp.addEventListener("change", () => {
    if (!bnd.open || !bnd.ring) return;
    const i = Number(inp.dataset.i), len = Number(inp.value);
    const a = bnd.ring[i], b = bnd.ring[(i + 1) % bnd.ring.length];
    const cur = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (!(len > 0) || !(cur > 0)) return;
    const k = len / cur;
    bnd.ring[(i + 1) % bnd.ring.length] = [Math.round((a[0] + (b[0] - a[0]) * k) * 100) / 100, Math.round((a[1] + (b[1] - a[1]) * k) * 100) / 100];
    bnd.sel = (i + 1) % bnd.ring.length;
    redraw();
  }));
}

/* The handles' pointer and key handling, wired to the plan's SVG each time it is drawn (a refit replaces it). */
export function wireBoundaryCanvas(fig, redraw) {
  if (!bnd.open) return;
  const svg = $(".fig-body svg", fig);
  if (!svg || svg.dataset.bnd) return;
  svg.dataset.bnd = "1";
  const toLot = e => {
    const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(svg.getScreenCTM().inverse());
    return [Math.round((pt.x + parseFloat(svg.dataset.x0)) * 10) / 10, Math.round((parseFloat(svg.dataset.y1) - pt.y) * 10) / 10];
  };
  svg.setAttribute("tabindex", "0");
  svg.addEventListener("pointerdown", e => {
    const v = e.target.closest(".bnd-v");
    if (v) { bnd.sel = Number(v.dataset.i); bnd.drag = bnd.sel; svg.setPointerCapture(e.pointerId); svg.focus({ preventScroll: true }); e.preventDefault(); $$(".bnd-v", svg).forEach(c => c.setAttribute("fill", Number(c.dataset.i) === bnd.sel ? "#2a6fb8" : "#ffffff")); return; }
    const mid = e.target.closest(".bnd-mid");
    if (mid) { const i = Number(mid.dataset.i); const a = bnd.ring[i], b = bnd.ring[(i + 1) % bnd.ring.length]; bnd.ring.splice(i + 1, 0, [Math.round((a[0] + b[0]) * 5) / 10, Math.round((a[1] + b[1]) * 5) / 10]); bnd.sel = i + 1; e.preventDefault(); redraw(); }
  });
  svg.addEventListener("pointermove", e => {
    if (bnd.drag == null) return;
    bnd.ring[bnd.drag] = toLot(e);
    // the lot line and the handles follow the pointer in place; the dimensions redraw on release
    const x0 = parseFloat(svg.dataset.x0), y1 = parseFloat(svg.dataset.y1);
    const X = x => x - x0, Y = y => y1 - y;
    const lot = $("#lot-poly", svg); if (lot) lot.setAttribute("points", bnd.ring.map(([x, y]) => `${X(x).toFixed(2)},${Y(y).toFixed(2)}`).join(" "));
    const g = $(".bnd", svg); if (g) g.outerHTML = boundaryHandles(bnd.ring, X, Y, VIEW3D.fs || 3);
  });
  const done = () => { if (bnd.drag == null) return; bnd.drag = null; redraw(); };
  for (const ev of ["pointerup", "pointercancel"]) svg.addEventListener(ev, done);
  svg.addEventListener("keydown", e => {
    if ((e.key === "Delete" || e.key === "Backspace") && bnd.sel != null && bnd.ring.length > 3) { e.preventDefault(); bnd.ring.splice(bnd.sel, 1); bnd.sel = null; redraw(); }
    const k = { ArrowLeft: [-0.5, 0], ArrowRight: [0.5, 0], ArrowUp: [0, 0.5], ArrowDown: [0, -0.5] }[e.key];
    if (k && bnd.sel != null) { e.preventDefault(); const p = bnd.ring[bnd.sel]; bnd.ring[bnd.sel] = [Math.round((p[0] + k[0]) * 10) / 10, Math.round((p[1] + k[1]) * 10) / 10]; redraw(); }
  });
}

async function applyBoundary(backToParcel, run, redraw) {
  const site = state.site;
  if (!site || !state.option || bnd.busy) return;
  if (backToParcel) delete site.boundary_m;
  else site.boundary_m = bnd.ring.map(p => [Math.round(p[0] * 10) / 10, Math.round(p[1] * 10) / 10]);
  state.siteDirty = true; $("#site-dirty").hidden = false;
  bnd.busy = true; redraw();
  try {
    const res = await postJSON("/api/layout", { site, option: state.option, as_of: $("#as-of").value || todayISO() });
    run.massing = res.massing; run.layout = res.layout; run.sheets = res.sheets;
    if (run.ledger && run.ledger.inputs) run.ledger.inputs.site = JSON.parse(JSON.stringify(site));
    bnd.open = false; bnd.ring = null; bnd.sel = null; bnd.busy = false;
    refreshSummary("site");
    rerenderFigures(run);
    const lot = run.massing.lot;
    setStatus(backToParcel ? `Back to the parcel polygon: ${fmtNum(Math.round(lot.polygon_area_m2 || lot.area_m2))} m². Run the rules to make the memo from it.`
      : `The drawn boundary is the lot: ${lot.polygon.length} corners, ${fmtNum(Math.round(lot.polygon_area_m2 || lot.area_m2))} m², shape ${String((lot.shape || {}).class || "polygon").replace(/_/g, " ")}; the masses stand in the ${h(run.massing.envelope.width_m)} × ${h(run.massing.envelope.depth_m)} m plate box. Save site as… keeps it; Run the rules makes the memo from it.`, "ok");
  } catch (e) {
    bnd.busy = false; redraw();
    toast(`Could not rebuild the massing: ${e.message}`, true);
  }
}
