/* FIG 01 in plan: the lot, the envelope, the footprints and the context. The boundary editor's handles and toolbar
   are drawn here too, so the plan renders in one pass; the editor's interaction is editors/boundary.js. */

import { fmtNum, h } from "../core/util.js";
import { bnd, state } from "../core/state.js";
import { FIG, HALF, halo, northArrow, NS, polyEl, scaleBar, SVG_OPEN, turnFrame, turnOf, upright } from "./common.js";

export function figPlan(m, ctx, fsIn = null) {
  const W = m.lot.frontage_m, D = m.lot.depth_m;
  // a polygon lot is dimensioned on its own extent; the boundary editor's ring stands in for the lot while open
  const lotRing = bnd.open && bnd.ring ? bnd.ring : m.lot.polygon;
  const bb = m.lot.bbox || bnd.open ? ringBox(lotRing) : [0, 0, W, D];
  const bW = bb[2] - bb[0], bD = bb[3] - bb[1];
  const pad = Math.max(3, W * 0.05);
  const fs = fsIn || Math.max(2.2, W / 34);
  const masses = Object.fromEntries(m.masses.map(x => [x.name, x]));
  // with the boundary editor open the plan zooms to the lot (5 m around it), so the handles are a hand's width apart
  const zoom = bnd.open ? 5 : null;
  const x0 = zoom != null ? bb[0] - zoom : Math.min(ctx.xmin, bb[0]) - pad, x1 = zoom != null ? bb[2] + zoom + fs * 2.6 : Math.max(ctx.xmax + pad, bb[2] + fs * 2.6 + pad);
  const y0 = zoom != null ? bb[1] - zoom : Math.min(ctx.ymin, bb[1]) - pad, y1 = zoom != null ? bb[3] + zoom : Math.max(ctx.ymax, bb[3]) + pad;
  const Y = y => y1 - y;                                // the street (y < 0) drawn at the bottom
  const X = x => x - x0;
  const P = pts => pts.map(([x, y]) => [X(x), Y(y)]);
  const vbW = x1 - x0, vbH = y1 - y0;
  // north up: the drawing below is made in the lot frame (the street along x) and turned as a whole, in a frame
  // large enough to hold it, wherever the context gives the bearing; the scale bar and the north arrow stay level
  const turn = turnOf(ctx.osm && ctx.osm.bearing), frame = turnFrame(vbW, vbH, turn);
  const head = `<svg ${SVG_OPEN} viewBox="0 0 ${frame.W.toFixed(2)} ${frame.H.toFixed(2)}" data-x0="${x0.toFixed(3)}" data-y1="${y1.toFixed(3)}" aria-label="Plan${turn ? ", north up" : ""}: the lot with its streets, buildings and trees in half tone, the setback envelope and the two massing footprints">`
    + `<rect x="0" y="0" width="${frame.W.toFixed(2)}" height="${frame.H.toFixed(2)}" fill="${ctx.osm ? HALF.parcel : "#ffffff"}"/>`;
  let s = `<rect x="0" y="0" width="${vbW.toFixed(2)}" height="${vbH.toFixed(2)}" fill="${ctx.osm ? HALF.parcel : "#ffffff"}"/>`;
  for (const g of ctx.ground) s += polyEl(P(g.ring), g.seam ? `fill="${g.fill}" stroke="${g.fill}" stroke-width="0.6" stroke-linejoin="round"` : `fill="${g.fill}" stroke="${HALF.line}" stroke-width="0.8"${g.dash ? ` stroke-dasharray="3 2"` : ""}`);
  for (const b of ctx.buildings) s += polyEl(P(b.polygon), `fill="${HALF.building}" stroke="${HALF.line}" stroke-width="0.6"`);
  // the frontage's dimension text sits just in front of the lot, where the front street's name is often set: a name
  // that would print under it moves along the street past its end (17 Nov 2026: "E Hastings St" under "extent 58.4 m
  // · equivalent frontage 58.5 m" on 3475 E Hastings St)
  const polyLot = !!(m.lot.bbox || bnd.open);
  const dimText = polyLot ? `extent ${Math.round(bW * 10) / 10} m · equivalent frontage ${W} m` : `frontage ${W} m`;
  const dimX = X((bb[0] + bb[2]) / 2), dimY = Y(bb[1]) + fs * 0.55 + fs * 1.2;
  const dimHalf = dimText.length * fs * 0.27 + fs;
  for (const l of ctx.labels) {
    let [lx, ly] = [X(l.at[0]), Y(l.at[1])];
    const half = String(l.text).length * fs * 0.25;
    if (Math.abs(ly - dimY) < fs * 1.3 && lx + half > dimX - dimHalf && lx - half < dimX + dimHalf) {
      const right = dimX + dimHalf + half + fs * 0.5, left = dimX - dimHalf - half - fs * 0.5;
      lx = right + half < vbW ? right : (left - half > 0 ? left : lx);
    }
    s += `<text x="${lx.toFixed(2)}" y="${(ly + fs * 0.35).toFixed(2)}" font-size="${(fs * 0.9).toFixed(2)}" text-anchor="middle" fill="${l.strong ? FIG.grey : HALF.text}"${l.strong ? ` font-weight="600"` : ""} ${halo(fs)}${l.angle ? ` transform="rotate(${(-l.angle).toFixed(1)} ${lx.toFixed(2)} ${ly.toFixed(2)})"` : ""}>${h(l.text)}</text>`;
  }
  for (const t of ctx.streetTrees.concat(ctx.osmTrees)) s += `<circle cx="${X(t.x).toFixed(2)}" cy="${Y(t.y).toFixed(2)}" r="${t.crown}" fill="${HALF.tree}" fill-opacity="0.35" stroke="${HALF.treeLine}" stroke-width="0.6" ${NS}/>`;
  s += polyEl(P(lotRing), `id="lot-poly" fill="${FIG.paper}" stroke="${FIG.lot}" stroke-width="1.2"`);
  s += polyEl(P(m.envelope.polygon), `fill="none" stroke="${FIG.env}" stroke-width="1" stroke-dasharray="4 3"`);
  if (m.envelope.box && m.lot.bbox) { const b = m.envelope.box; s += polyEl(P([[b.x, b.y], [b.x + b.w, b.y], [b.x + b.w, b.y + b.d], [b.x, b.y + b.d]]), `fill="none" stroke="${FIG.env}" stroke-width="0.6" stroke-dasharray="1.5 1.5"`); }
  // the proposed footprint, then the outright one drawn over it as a heavy dashed outline, so both read in plan
  if (masses.proposed) s += polyEl(P(masses.proposed.footprint), `fill="${FIG.proposedFill}" stroke="${FIG.proposedStroke}" stroke-width="1.2" fill-opacity="0.5"`);
  if (masses.outright) s += polyEl(P(masses.outright.footprint), `fill="${FIG.outrightFill}" fill-opacity="${masses.proposed ? 0.35 : 0.9}" stroke="${FIG.outrightStroke}" stroke-width="2" stroke-dasharray="6 3"`);
  // tree ids only where there is room for them: at the label size, schematic trees along the rear would overprint
  const gap = ctx.trees.reduce((g, t, i) => Math.min(g, ...ctx.trees.slice(i + 1).map(u => Math.hypot(u.x - t.x, u.y - t.y))), Infinity);
  const ids = gap > fs * 2.4;
  for (const t of ctx.trees) {
    const cx = X(t.x).toFixed(2), cy = Y(t.y).toFixed(2);
    if (t.retained) s += `<circle cx="${cx}" cy="${cy}" r="${t.crown}" fill="${HALF.tree}" fill-opacity="0.45" stroke="${HALF.treeLine}" stroke-width="0.8" ${NS}/>`;
    else s += `<circle cx="${cx}" cy="${cy}" r="${t.crown}" fill="none" stroke="${HALF.gone}" stroke-width="0.6" stroke-dasharray="1.5 1.5" ${NS}/>${t.crown > fs * 0.5 ? `<text x="${cx}" y="${(Y(t.y) + fs * 0.35).toFixed(2)}" font-size="${(fs * 0.9).toFixed(2)}" text-anchor="middle" fill="${HALF.gone}">×</text>` : ""}`;
    if (ids) s += `<text x="${(X(t.x) + t.crown + 0.5).toFixed(2)}" y="${(Y(t.y) - t.crown * 0.6).toFixed(2)}" font-size="${(fs * 0.85).toFixed(2)}" fill="${t.retained ? HALF.treeLine : HALF.gone}" ${halo(fs)}>${h(t.id)}</text>`;
  }
  // dimension strings: the frontage along the front line, the depth along the right-hand lot line, each with ticks
  const tick = fs * 0.35;
  const poly = polyLot;
  const [bx0, by0, bx1, by1] = bb;
  const fy = Y(by0) + fs * 0.55;
  s += `<g stroke="${FIG.grey}" stroke-width="0.8" ${NS}><line x1="${X(bx0).toFixed(2)}" y1="${fy.toFixed(2)}" x2="${X(bx1).toFixed(2)}" y2="${fy.toFixed(2)}"/>`
     + `<line x1="${(X(bx0) - tick).toFixed(2)}" y1="${(fy + tick).toFixed(2)}" x2="${(X(bx0) + tick).toFixed(2)}" y2="${(fy - tick).toFixed(2)}"/>`
     + `<line x1="${(X(bx1) - tick).toFixed(2)}" y1="${(fy + tick).toFixed(2)}" x2="${(X(bx1) + tick).toFixed(2)}" y2="${(fy - tick).toFixed(2)}"/></g>`;
  s += `<text x="${dimX.toFixed(2)}" y="${dimY.toFixed(2)}" font-size="${fs.toFixed(2)}" text-anchor="middle" fill="${FIG.grey}" ${halo(fs)}>${h(dimText)}</text>`;
  const dx = X(bx1) + fs * 0.6;
  s += `<g stroke="${FIG.grey}" stroke-width="0.8" ${NS}><line x1="${dx.toFixed(2)}" y1="${Y(by0).toFixed(2)}" x2="${dx.toFixed(2)}" y2="${Y(by1).toFixed(2)}"/>`
     + `<line x1="${(dx - tick).toFixed(2)}" y1="${(Y(by0) + tick).toFixed(2)}" x2="${(dx + tick).toFixed(2)}" y2="${(Y(by0) - tick).toFixed(2)}"/>`
     + `<line x1="${(dx - tick).toFixed(2)}" y1="${(Y(by1) + tick).toFixed(2)}" x2="${(dx + tick).toFixed(2)}" y2="${(Y(by1) - tick).toFixed(2)}"/></g>`;
  const rx = dx + fs * 0.95, ry = Y((by0 + by1) / 2);
  s += `<text x="${rx.toFixed(2)}" y="${ry.toFixed(2)}" font-size="${fs.toFixed(2)}" text-anchor="middle" fill="${FIG.grey}" ${halo(fs)} transform="rotate(90 ${rx.toFixed(2)} ${ry.toFixed(2)})">${poly ? `extent ${h(Math.round(bD * 10) / 10)} m` : `depth ${h(D)} m`}</text>`;
  if (bnd.open && bnd.ring) s += boundaryHandles(bnd.ring, X, Y, fs);
  let out = head + frame.open + upright(s, turn) + `</g>`;
  out += scaleBar(fs * 1.4, frame.H - fs * 0.9, x1 - x0, fs);
  if (ctx.osm && ctx.osm.bearing != null) out += northArrow(frame.W - fs * 2.2, fs * 2.4, 90, fs);   // the page's up is north
  return out + `</svg>`;
}

function ringBox(ring) {
  const xs = ring.map(p => p[0]), ys = ring.map(p => p[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

function ringArea(ring) {
  let s = 0;
  for (let i = 0; i < ring.length; i++) { const [x1, y1] = ring[i], [x2, y2] = ring[(i + 1) % ring.length]; s += x1 * y2 - x2 * y1; }
  return Math.abs(s) / 2;
}

export function boundaryHandles(ring, X, Y, fs) {
  const r = Math.max(1.4, fs * 0.9);    // about a finger's width at the label size, so a corner can be taken hold of
  let s = `<g class="bnd">`;
  s += polyEl(ring.map(([x, y]) => [X(x), Y(y)]), `class="bnd-line" fill="none" stroke="#2a6fb8" stroke-width="1" stroke-dasharray="2.5 1.5" ${NS}`);
  ring.forEach(([x, y], i) => {
    const [nx, ny] = ring[(i + 1) % ring.length];
    const mx = X((x + nx) / 2), my = Y((y + ny) / 2);
    s += `<rect class="bnd-mid" data-i="${i}" x="${(mx - r * 0.55).toFixed(2)}" y="${(my - r * 0.55).toFixed(2)}" width="${(r * 1.1).toFixed(2)}" height="${(r * 1.1).toFixed(2)}" fill="#ffffff" stroke="#2a6fb8" stroke-width="0.6" ${NS}><title>Add a corner here</title></rect>`;
  });
  ring.forEach(([x, y], i) => {
    s += `<circle class="bnd-v${bnd.sel === i ? " sel" : ""}" data-i="${i}" cx="${X(x).toFixed(2)}" cy="${Y(y).toFixed(2)}" r="${r.toFixed(2)}" fill="${bnd.sel === i ? "#2a6fb8" : "#ffffff"}" stroke="#2a6fb8" stroke-width="1" ${NS}><title>${h(x)}, ${h(y)} m</title></circle>`;
  });
  return s + `</g>`;
}

export function boundaryTools(m) {
  const site = state.site || {};
  const drawn = !!(site.boundary_m && site.boundary_m.length >= 3);
  const ring = bnd.open && bnd.ring ? bnd.ring : m.lot.polygon;
  const note = bnd.open ? `${ring.length} corners · ${fmtNum(Math.round(ringArea(ring)))} m²${m.lot.polygon_area_m2 || m.lot.area_m2 ? ` (recorded ${fmtNum(Math.round(m.lot.area_m2))} m²)` : ""}` : "";
  // after a drawn boundary is in use, the recorded site area can be set to it with one click (never silently)
  const drawnArea = drawn && m.lot.source === "drawn" ? Math.round((m.lot.polygon_area_m2 || m.lot.area_m2) * 10) / 10 : null;
  const areaOff = drawnArea != null && site.site_area_m2 != null && Math.abs(drawnArea - site.site_area_m2) > 0.5;
  const edges = bnd.open && bnd.ring ? `<details class="bnd-edges"><summary>Edges: lengths and bearings (type a length to set it)</summary><table class="plain"><thead><tr><th>Edge</th><th>Length (m)</th><th>Bearing</th></tr></thead><tbody>${ringEdges(bnd.ring).map(e => `<tr><td>${e.i + 1}</td><td><input type="number" step="0.01" min="0.1" class="bnd-edge" data-i="${e.i}" value="${e.length}" aria-label="Length of edge ${e.i + 1} in metres"></td><td class="cont">${e.bearing}°</td></tr>`).join("")}</tbody></table></details>` : "";
  return `<div class="fig-tools bnd-tools">
      ${bnd.open ? `<span class="help bnd-note">${h(note)}</span>
      <button type="button" class="btn btn-small btn-primary" id="bnd-apply"${bnd.busy ? " disabled" : ""}>${bnd.busy ? "Rebuilding…" : "Use this boundary"}</button>
      ${drawn ? `<button type="button" class="btn btn-small btn-quiet" id="bnd-parcel"${bnd.busy ? " disabled" : ""}>Back to the parcel</button>` : ""}` : ""}
      ${!bnd.open && areaOff ? `<button type="button" class="btn btn-small btn-quiet" id="bnd-area" title="The recorded site area, ${h(fmtNum(site.site_area_m2))} m², is what the FSR and the plate cap read">Set the site area to the drawn lot, ${h(fmtNum(drawnArea))} m²</button>` : ""}
      <button type="button" class="btn btn-small" id="edit-boundary" aria-expanded="${bnd.open}" title="Drag the corners of the lot line, click a midpoint to add one, Delete removes the selected corner">${bnd.open ? "Close" : "Edit boundary"}</button>
    </div>${edges}`;
}

/* Each edge of the ring: its length and its bearing (degrees from east, anticlockwise, in the lot frame). Pure. */
function ringEdges(ring) {
  return ring.map(([x, y], i) => {
    const [nx, ny] = ring[(i + 1) % ring.length];
    return { i, length: Math.round(Math.hypot(nx - x, ny - y) * 100) / 100, bearing: Math.round(((Math.atan2(ny - y, nx - x) * 180 / Math.PI) + 360) % 360 * 10) / 10 };
  });
}
