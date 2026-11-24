/* FIG 01 in plan: the lot, the envelope, the footprints and the context. The boundary editor's handles and toolbar
   are drawn here too, so the plan renders in one pass; the editor's interaction is editors/boundary.js. */

import { fmtNum, h } from "../core/util.js";
import { bnd, state } from "../core/state.js";
import { BLOCK_TONE, crossingsAtX, FIG, HALF, halo, massParts, northArrow, NS, polyEl, projectTurn, scaleBar, sectionCut, sunShadows, SVG_OPEN, upright } from "./common.js";
import { VIEW3D } from "./fig3d.js";

/* The plan frames the lot and about this much around it (20 Nov 2026: it framed the whole 240 m of context, so the lot
   was 150 px of a 440 px drawing and the context as loud as the subject). */
const MARGIN = 25;
const r1 = v => (Math.round(v * 10) / 10).toFixed(1);
const f2 = v => v.toFixed(2);
const SKIP_NAMES = /^(footway|cycleway|path|steps|pedestrian|track|bridleway)$/;

export function figPlan(m, ctx, fsIn = null) {
  const W = m.lot.frontage_m, D = m.lot.depth_m;
  // a polygon lot is dimensioned on its own extent; the boundary editor's ring stands in for the lot while open
  const lotRing = bnd.open && bnd.ring ? bnd.ring : m.lot.polygon;
  const polyLot = !!(m.lot.bbox || bnd.open);
  const bb = polyLot ? ringBox(lotRing) : [0, 0, W, D];
  const [bx0, by0, bx1, by1] = bb;
  const bW = bx1 - bx0, bD = by1 - by0;
  const fs = fsIn || Math.max(2.2, (Math.max(bW, bD) + 2 * MARGIN) / 38);
  const masses = Object.fromEntries(m.masses.map(x => [x.name, x]));
  const turn = projectTurn(ctx.osm && ctx.osm.bearing);   // project north: the quarter turn nearest true north
  // with the boundary editor open the plan zooms to the lot, so the handles are a hand's width apart
  const margin = bnd.open ? Math.max(5, fs * 2.8) : MARGIN;
  // the drawing's own coordinates: x along the frontage, y down the page with the street at the bottom (the boundary
  // editor reads a pointer back through data-x0 and data-y1); north up turns the whole drawing about the lot's middle
  const x0 = bx0 - MARGIN, y1 = by1 + MARGIN;
  const X = x => x - x0, Y = y => y1 - y;
  const P = pts => pts.map(([x, y]) => [X(x), Y(y)]);
  const cx = X((bx0 + bx1) / 2), cy = Y((by0 + by1) / 2), t = turn * Math.PI / 180, ct = Math.cos(t), st = Math.sin(t);
  const rot = ([x, y]) => [cx + (x - cx) * ct - (y - cy) * st, cy + (x - cx) * st + (y - cy) * ct];
  // the section line's ends: past the lot and past the frontage's dimension text in front, past the lot behind
  const xc = sectionCut(m), cr = crossingsAtX(lotRing, xc);
  const ya = Math.min(cr.length ? cr[0] : by0, by0) - fs * 3.6, yb = Math.max(cr.length ? cr[cr.length - 1] : by1, by1) + fs * 2.2;
  // the frame: the turned lot and the margin round it, and room for the dimension strings and the section marks
  // (a lot much smaller than its extent, 1010 Expo Blvd, has its strings well outside it); a schematic context (no
  // bearing, so no turn) stops at its own edges, keeping room for the dimension strings
  const turned = P(lotRing).map(rot);
  const marks = P([[bx0, by0 - fs * 2.2], [bx1, by0 - fs * 2.2], [bx1 + fs * 2.2, by0], [bx1 + fs * 2.2, by1]].concat(bnd.open ? [] : [[xc, ya - fs], [xc, yb + fs]])).map(rot);
  let fx0 = Math.min(Math.min(...turned.map(p => p[0])) - margin, Math.min(...marks.map(p => p[0])) - fs * 1.5), fx1 = Math.max(Math.max(...turned.map(p => p[0])) + margin, Math.max(...marks.map(p => p[0])) + fs * 1.5);
  let fy0 = Math.min(Math.min(...turned.map(p => p[1])) - margin, Math.min(...marks.map(p => p[1])) - fs * 1.5), fy1 = Math.max(Math.max(...turned.map(p => p[1])) + margin, Math.max(...marks.map(p => p[1])) + fs * 1.5);
  if (!ctx.osm && !bnd.open) {
    fx0 = Math.min(Math.max(fx0, X(ctx.xmin) - 1), X(bx0) - fs * 1.5); fx1 = Math.max(Math.min(fx1, X(ctx.xmax) + 1), X(bx1) + fs * 3);
    fy0 = Math.min(Math.max(fy0, Y(ctx.ymax) - 1), Y(by1) - fs * 1.5); fy1 = Math.max(Math.min(fy1, Y(ctx.ymin) + 1), Y(by0) + fs * 5);
  }
  const FW = fx1 - fx0, FH = fy1 - fy0;
  const toPage = p => { const [u, v] = rot(p); return [u - fx0, v - fy0]; };
  const head = `<svg ${SVG_OPEN} viewBox="0 0 ${f2(FW)} ${f2(FH)}" data-x0="${x0.toFixed(3)}" data-y1="${y1.toFixed(3)}" aria-label="Plan${turn ? ", north up" : ", the street at the bottom"}: the lot and about ${MARGIN} m round it, its streets, buildings and trees in half tone, the yards and the setback envelope, the two massing footprints and the section line A–A">`
    + `<rect x="0" y="0" width="${f2(FW)}" height="${f2(FH)}" fill="${ctx.osm ? HALF.parcel : FIG.paper}"/>`;
  const open = `<g class="plan-turn" transform="translate(${f2(-fx0)} ${f2(-fy0)}) rotate(${turn.toFixed(2)} ${f2(cx)} ${f2(cy)})">`;

  // the context a step quieter than the lot: the roads at their tone, the buildings and trees faded behind them
  let s = "";
  for (const g of ctx.ground) s += polyEl(P(g.ring), g.seam ? `fill="${g.fill}" stroke="${g.fill}" stroke-width="0.6" stroke-linejoin="round"` : `fill="${g.fill}" stroke="${HALF.line}" stroke-width="0.8"${g.dash ? ` stroke-dasharray="3 2"` : ""}`);
  let soft = "";
  for (const b of ctx.buildings) soft += polyEl(P(b.polygon), `fill="${HALF.building}" stroke="${HALF.line}" stroke-width="0.6"`);
  for (const tr of ctx.streetTrees.concat(ctx.osmTrees)) soft += `<circle cx="${f2(X(tr.x))}" cy="${f2(Y(tr.y))}" r="${tr.crown}" fill="${HALF.tree}" fill-opacity="0.35" stroke="${HALF.treeLine}" stroke-width="0.6" ${NS}/>`;
  s += `<g class="plan-context" opacity="0.5">${soft}</g>`;

  s += polyEl(P(lotRing), `id="lot-poly" fill="${FIG.paper}" stroke="${FIG.lot}" stroke-width="1.2"`);
  s += polyEl(P(m.envelope.polygon), `fill="none" stroke="${FIG.env}" stroke-width="1" stroke-dasharray="4 3"`);
  // the plate box, dotted: where it stands turned to the lot's longest side (massing: envelope.box.ring) it is drawn turned
  if (m.envelope.box && m.lot.bbox) { const b = m.envelope.box; s += polyEl(P(b.ring || [[b.x, b.y], [b.x + b.w, b.y], [b.x + b.w, b.y + b.d], [b.x, b.y + b.d]]), `fill="none" stroke="${FIG.env}" stroke-width="0.6" stroke-dasharray="1.5 1.5"`); }
  // the proposed footprint, then the outright one drawn over it as a heavy dashed outline, so both read in plan
  // the shadows at the equinox, where they are asked for and the context gives north: a first reading (common.js)
  if (VIEW3D.shadows && masses.proposed && ctx.osm && ctx.osm.bearing != null) {
    for (const sh of sunShadows(massParts(masses.proposed), ctx.osm.bearing, ctx.osm.lat).sort((a, b) => b.len - a.len)) {
      s += `<g opacity="0.16">${sh.rings.map(r => polyEl(P(r), `fill="#1f2933" stroke="none"`)).join("")}</g>`;
      s += `<text x="${X(sh.tip[0]).toFixed(2)}" y="${Y(sh.tip[1]).toFixed(2)}" font-size="${(fs * 0.8).toFixed(2)}" text-anchor="middle" fill="${FIG.grey}" ${halo(fs)}>${sh.label}</text>`;
    }
  }
  if (masses.proposed) s += polyEl(P(masses.proposed.footprint), `fill="${FIG.proposedFill}" stroke="${FIG.proposedStroke}" stroke-width="1.2" fill-opacity="0.5"`);
  // the program on the ground floor, in its tones, where it is asked for: the layout's blocks, turned with the mass
  const Lp = VIEW3D.program && masses.proposed && state.run && state.run.layout;
  if (Lp && Lp.floors && Lp.floors[0] && Math.abs(Lp.plate.width_m - masses.proposed.plate_width_m) < 0.05) {
    const pl = Lp.plate, a = (pl.angle_deg || 0) * Math.PI / 180, ca = Math.cos(a), sa = Math.sin(a), mx = pl.x + pl.width_m / 2, my = pl.y + pl.depth_m / 2;
    for (const z of Lp.floors[0].zones) {
      if (z.block === "spare" || z.block === "void") continue;
      const ring = [[z.x, z.y], [z.x + z.w, z.y], [z.x + z.w, z.y + z.d], [z.x, z.y + z.d]].map(([x, y]) => [mx + (x - mx) * ca - (y - my) * sa, my + (x - mx) * sa + (y - my) * ca]);
      s += polyEl(P(ring), `fill="${BLOCK_TONE[z.block] || "#eeeeee"}" stroke="#5f6672" stroke-width="0.5"`);
    }
  }
  if (masses.outright) s += polyEl(P(masses.outright.footprint), `fill="${FIG.outrightFill}" fill-opacity="${masses.proposed ? 0.35 : 0.9}" stroke="${FIG.outrightStroke}" stroke-width="2" stroke-dasharray="6 3"`);
  // tree ids only where there is room for them: at the label size, schematic trees along the rear would overprint
  const gap = ctx.trees.reduce((g, tr, i) => Math.min(g, ...ctx.trees.slice(i + 1).map(u => Math.hypot(u.x - tr.x, u.y - tr.y))), Infinity);
  const ids = gap > fs * 2.4;
  for (const tr of ctx.trees) {
    const tx = f2(X(tr.x)), ty = f2(Y(tr.y));
    if (tr.retained) s += `<circle cx="${tx}" cy="${ty}" r="${tr.crown}" fill="${HALF.tree}" fill-opacity="0.45" stroke="${HALF.treeLine}" stroke-width="0.8" ${NS}/>`;
    else s += `<circle cx="${tx}" cy="${ty}" r="${tr.crown}" fill="none" stroke="${HALF.gone}" stroke-width="0.6" stroke-dasharray="1.5 1.5" ${NS}/>${tr.crown > fs * 0.5 ? `<text x="${tx}" y="${f2(Y(tr.y) + fs * 0.35)}" font-size="${f2(fs * 0.9)}" text-anchor="middle" fill="${HALF.gone}">×</text>` : ""}`;
    // the ids are text: the street-name grey, readable at their size (24 Nov 2026: T2 to T9 read at 1.9:1)
    if (ids) s += `<text x="${f2(X(tr.x) + tr.crown + 0.5)}" y="${f2(Y(tr.y) - tr.crown * 0.6)}" font-size="${f2(fs * 0.85)}" fill="${HALF.text}" ${halo(fs)}>${h(tr.id)}</text>`;
  }

  // what the street names must keep clear of, as circles in the drawing's coordinates
  const keep = [];
  const along = (x, y, deg, half, r) => { const a = deg * Math.PI / 180, out = []; for (let d = -half; d <= half + 1e-6; d += r * 1.2) out.push({ x: x + d * Math.cos(a), y: y + d * Math.sin(a), r }); if (!out.length) out.push({ x, y, r }); return out; };
  const textHalf = (text, size) => String(text).length * size * 0.28;

  // dimension strings with ticks: the frontage along the front line, the depth along the right-hand lot line
  const tick = fs * 0.35;
  const fy = Y(by0) + fs * 0.55;
  const dimText = polyLot ? `extent ${r1(bW)} m` : `frontage ${W} m`;
  const dimX = X((bx0 + bx1) / 2), dimY = fy + fs * 1.2;
  s += `<g stroke="${FIG.grey}" stroke-width="0.8" ${NS}>${dimLine(X(bx0), fy, X(bx1), fy, tick)}</g>`;
  s += `<text x="${f2(dimX)}" y="${f2(dimY)}" font-size="${f2(fs)}" text-anchor="middle" fill="${FIG.grey}" ${halo(fs)}>${h(dimText)}</text>`;
  keep.push(...along(dimX, dimY - fs * 0.35, 0, textHalf(dimText, fs), fs * 0.6));
  const dx = X(bx1) + fs * 0.6;
  s += `<g stroke="${FIG.grey}" stroke-width="0.8" ${NS}>${dimLine(dx, Y(by0), dx, Y(by1), tick)}</g>`;
  const rx = dx + fs * 0.95, ry = Y((by0 + by1) / 2), depthText = polyLot ? `extent ${r1(bD)} m` : `depth ${D} m`;
  s += `<text x="${f2(rx)}" y="${f2(ry)}" font-size="${f2(fs)}" text-anchor="middle" fill="${FIG.grey}" ${halo(fs)} transform="rotate(90 ${f2(rx)} ${f2(ry)})">${h(depthText)}</text>`;
  keep.push(...along(rx + fs * 0.35, ry, 90, textHalf(depthText, fs), fs * 0.6));

  if (!bnd.open) {
    s += yardDims(m, lotRing, X, Y, fs);
    s += plateLabel(masses.proposed, X, Y, fs, xc);
    // section A–A, where FIG 02 cuts: across the lot from the street to the rear, looking towards the lot's left
    // (the street on the section's left), lettered at both ends
    s += `<line x1="${f2(X(xc))}" y1="${f2(Y(ya))}" x2="${f2(X(xc))}" y2="${f2(Y(yb))}" stroke="${FIG.lot}" stroke-width="0.9" stroke-dasharray="7 2 1.5 2" ${NS}/>`;
    for (const yy of [ya, yb]) {
      const mx = X(xc), my = Y(yy), r = fs * 0.78;
      s += `<g class="cut-mark"><polygon points="${f2(mx - r * 0.1)},${f2(my - r)} ${f2(mx - r * 0.1)},${f2(my + r)} ${f2(mx - r - fs * 0.8)},${f2(my)}" fill="${FIG.lot}"/>`
        + `<circle cx="${f2(mx)}" cy="${f2(my)}" r="${f2(r)}" fill="${FIG.paper}" stroke="${FIG.lot}" stroke-width="1" ${NS}/>`
        + `<text x="${f2(mx)}" y="${f2(my + fs * 0.33)}" font-size="${f2(fs * 0.9)}" font-weight="600" text-anchor="middle" fill="${FIG.lot}">A</text></g>`;
      keep.push({ x: mx - fs * 0.4, y: my, r: r + fs * 0.6 });
    }
  }

  // the street names last, over everything round the lot, each at the place on its road nearest the lot where it
  // keeps clear of the lot, the dimension strings, the section marks, the scale bar, the north arrow and the other
  // names, inside the frame (20 Nov 2026: on 375 Glen Drive "extent 60.3 m · equivalent frontage 60.25 m" ran over
  // E Hastings St, and on 1010 Expo Blvd the names ran over the trees and the dimension text)
  const lotP = P(lotRing);
  // the scale bar takes the first corner the lot, its strings and the section marks leave clear: bottom left, bottom
  // right, top left (the north arrow has the top right)
  const sbL = [10, 20, 30, 50, 100, 200].find(v => v >= FW / 4) || 200, sbW = sbL + fs * 3.6;
  const busy = [];
  const sample = (pts, closed) => { for (let i = 0; i + (closed ? 0 : 1) < pts.length; i++) { const a = pts[i], b = pts[(i + 1) % pts.length], n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / fs)); for (let j = 0; j <= n; j++) busy.push(toPage([a[0] + (b[0] - a[0]) * j / n, a[1] + (b[1] - a[1]) * j / n])); } };
  sample(lotP, true);
  sample(P([[bx0, by0], [bx1, by0]]).map(([x, y]) => [x, y + fs * 1.6]), false);
  sample(P([[bx1, by0], [bx1, by1]]).map(([x, y]) => [x + fs * 1.6, y]), false);
  if (!bnd.open) sample(P([[xc, ya], [xc, yb]]), false);
  const sbAt = [[fs * 1.4, FH - fs * 0.9], [FW - fs * 2.6 - sbL, FH - fs * 0.9], [fs * 1.4, fs * 2.2]].find(([x, y]) =>
    !busy.some(([u, v]) => u > x - fs * 1.2 && u < x + sbW && v > y - fs * 2.3 && v < y + fs * 0.9)) || [fs * 1.4, FH - fs * 0.9];
  const pageBoxes = [[sbAt[0] - fs * 0.4, sbAt[1] - fs * 1.7, sbAt[0] + sbW, sbAt[1] + fs * 0.8]];
  if (ctx.osm && ctx.osm.bearing != null) pageBoxes.push([FW - fs * 4.4, 0, FW, fs * 4.6]);
  const fits = circles => circles.every(c => {
    const [u, v] = toPage([c.x, c.y]);
    if (u < c.r || v < c.r || u > FW - c.r || v > FH - c.r) return false;
    if (pageBoxes.some(([a, b, cc, d]) => u > a - c.r && u < cc + c.r && v > b - c.r && v < d + c.r)) return false;
    if (inRing(lotP, c.x, c.y)) return false;
    return !keep.some(k => Math.hypot(k.x - c.x, k.y - c.y) < k.r + c.r);
  });
  const lfs = fs * 0.9;
  const nameAt = (text, x, y, deg, strong) => {
    keep.push(...along(x, y, deg, textHalf(text, lfs), lfs * 0.62));
    return `<text x="${f2(x)}" y="${f2(y + lfs * 0.35)}" font-size="${f2(lfs)}" text-anchor="middle" fill="${strong ? FIG.grey : HALF.text}"${strong ? ` font-weight="600"` : ""} ${halo(fs)}${deg ? ` transform="rotate(${deg.toFixed(1)} ${f2(x)} ${f2(y)})"` : ""}>${h(text)}</text>`;
  };
  const lcx = (bx0 + bx1) / 2, lcy = (by0 + by1) / 2;
  if (ctx.osm && ctx.roads && ctx.roads.length) {
    // one label a name, the address street first, then the nearer roads
    const names = new Map();
    for (const rd of ctx.roads) if (rd.name && !SKIP_NAMES.test(rd.kind)) { const e = names.get(rd.name) || { front: false, lines: [] }; e.front = e.front || rd.front; e.lines.push(rd.points); names.set(rd.name, e); }
    const near = pts => Math.min(...pts.map(([x, y]) => Math.hypot(x - lcx, y - lcy)));
    const order = [...names.entries()].sort((a, b) => (b[1].front - a[1].front) || (Math.min(...a[1].lines.map(near)) - Math.min(...b[1].lines.map(near))));
    for (const [name, e] of order) {
      let best = null;
      const half = textHalf(name, lfs), step = Math.max(1, fs * 0.8);
      for (const pts of e.lines) for (let i = 0; i + 1 < pts.length; i++) {
        const [xa, ya2] = pts[i], [xb, yb2] = pts[i + 1], L = Math.hypot(xb - xa, yb2 - ya2);
        if (!L) continue;
        // the angle in the drawing's coordinates (y down), kept within a half turn so the name reads left to right
        let deg = -Math.atan2(yb2 - ya2, xb - xa) * 180 / Math.PI; if (deg > 90) deg -= 180; if (deg <= -90) deg += 180;
        // on the road's line, else a little to either side of it (a narrow phone frame leaves the address street
        // no room on its own line past the frontage's dimension text, 1010 Expo Blvd)
        const nx = -(yb2 - ya2) / L, ny = (xb - xa) / L;
        for (let d = 0; d <= L; d += step) for (const off of [0, 1.2, -1.2, 2.4, -2.4]) {
          const lx = xa + (xb - xa) * d / L + nx * off * lfs, ly = ya2 + (yb2 - ya2) * d / L + ny * off * lfs;
          const score = Math.hypot(lx - lcx, ly - lcy) + Math.abs(off) * lfs * 2;
          if (best && score >= best.score) continue;
          if (fits(along(X(lx), Y(ly), deg, half, lfs * 0.62))) best = { score, x: X(lx), y: Y(ly), deg };
        }
      }
      if (best) s += nameAt(name, best.x, best.y, best.deg, e.front);
    }
  } else {
    // the schematic context: each name at its place, slid along its street until it is clear
    for (const l of ctx.labels) {
      const deg = l.angle ? -l.angle : 0, a = deg * Math.PI / 180, half = textHalf(l.text, lfs);
      let at = null;
      for (let k = 0; k <= 24 && !at; k++) for (const sgn of k ? [1, -1] : [1]) {
        const d = sgn * k * fs, x = X(l.at[0]) + d * Math.cos(a), y = Y(l.at[1]) + d * Math.sin(a);
        if (fits(along(x, y, deg, half, lfs * 0.62))) { at = [x, y]; break; }
      }
      if (at) s += nameAt(l.text, at[0], at[1], deg, l.strong);
    }
  }
  if (bnd.open && bnd.ring) s += boundaryHandles(bnd.ring, X, Y, fs);
  let out = head + open + upright(s, turn) + `</g>`;
  out += scaleBar(sbAt[0], sbAt[1], FW, fs);
  if (ctx.osm && ctx.osm.bearing != null) out += northArrow(FW - fs * 2.2, fs * 2.4, ctx.osm.bearing - turn, fs);   // true north, as it stands on a plan drawn to project north
  return out + `</svg>`;
}

/* A dimension line with a tick at each end, at 45° to it. */
function dimLine(xa, ya, xb, yb, tick) {
  const L = Math.hypot(xb - xa, yb - ya) || 1, ux = (xb - xa) / L, uy = (yb - ya) / L;
  const tx = (ux - uy) * tick * 0.71, ty = (uy + ux) * tick * 0.71;
  return `<line x1="${f2(xa)}" y1="${f2(ya)}" x2="${f2(xb)}" y2="${f2(yb)}"/>`
    + `<line x1="${f2(xa - tx)}" y1="${f2(ya - ty)}" x2="${f2(xa + tx)}" y2="${f2(ya + ty)}"/>`
    + `<line x1="${f2(xb - tx)}" y1="${f2(yb - ty)}" x2="${f2(xb + tx)}" y2="${f2(yb + ty)}"/>`;
}

/* The yards dimensioned on the lot: from the plate box a line is sent to the front, the rear and one side; where it
   meets the lot line, the yard is measured square to that line, its depth the setback for the way the line faces
   (front towards the street, rear away from it, side otherwise, as boundary.inset reads them). */
function yardDims(m, ring, X, Y, fs) {
  const sb = m.envelope.setbacks_m || {};
  const box = m.envelope.box || (() => { const b = ringBox(m.envelope.polygon || []); return { x: b[0], y: b[1], w: b[2] - b[0], d: b[3] - b[1] }; })();
  if (!(box.w > 0 && box.d > 0) || !ring || ring.length < 3) return "";
  // the front and rear a quarter along, the side halfway back, so no two of their words meet at a corner
  const rays = [[[box.x + box.w * 0.25, box.y + box.d * 0.02], [0, -1]], [[box.x + box.w * 0.25, box.y + box.d * 0.98], [0, 1]], [[box.x + box.w * 0.02, box.y + box.d * 0.5], [-1, 0]]];
  const tfs = fs * 0.85;
  let s = "";
  for (const [o, d] of rays) {
    let hit = null;
    for (let i = 0; i < ring.length; i++) {
      const [ax, ay] = ring[i], [bx, by] = ring[(i + 1) % ring.length], ex = bx - ax, ey = by - ay;
      const den = d[0] * ey - d[1] * ex;
      if (Math.abs(den) < 1e-9) continue;
      const tt = ((ax - o[0]) * ey - (ay - o[1]) * ex) / den, u = ((ax - o[0]) * d[1] - (ay - o[1]) * d[0]) / den;
      if (tt > 0 && u >= 0 && u <= 1 && (!hit || tt < hit.t)) hit = { t: tt, p: [o[0] + d[0] * tt, o[1] + d[1] * tt], e: [ex, ey] };
    }
    if (!hit) continue;
    const L = Math.hypot(...hit.e);
    let n = [-hit.e[1] / L, hit.e[0] / L];
    if (n[0] * d[0] + n[1] * d[1] > 0) n = [-n[0], -n[1]];   // inward, back towards the plate
    const kind = n[1] > 0.707 ? "front" : n[1] < -0.707 ? "rear" : "side";   // the line faces the way -n points
    const v = Number(sb[kind]);
    if (!(v > 0)) continue;
    const q = [hit.p[0] + n[0] * v, hit.p[1] + n[1] * v];
    s += `<g stroke="${FIG.grey}" stroke-width="0.8" ${NS}>${dimLine(X(hit.p[0]), Y(hit.p[1]), X(q[0]), Y(q[1]), fs * 0.28)}</g>`;
    const mx = X((hit.p[0] + q[0]) / 2), my = Y((hit.p[1] + q[1]) / 2), words = `${kind} ${v.toFixed(1)}`;
    // a front or rear yard is labelled beside its line, along the yard; a side yard along its strip
    s += kind === "side"
      ? `<text x="${f2(mx + tfs * 0.35)}" y="${f2(my - fs * 0.6)}" font-size="${f2(tfs)}" fill="${FIG.grey}" ${halo(fs)} transform="rotate(-90 ${f2(mx + tfs * 0.35)} ${f2(my - fs * 0.6)})">${h(words)}</text>`
      : `<text x="${f2(mx + fs * 0.5)}" y="${f2(my + tfs * 0.35)}" font-size="${f2(tfs)}" fill="${FIG.grey}" ${halo(fs)}>${h(words)}</text>`;
  }
  return s;
}

/* The plate's dimensions on the proposed footprint, along its first edge, left of the section line where there is
   room; nothing where no plate fits (20 Nov 2026: the figures printed "plate 0 m²"). */
function plateLabel(p, X, Y, fs, xc) {
  if (!p || !(p.plate_area_m2 > 0) || !(p.footprint || []).length) return "";
  const fp = p.footprint, [ax, ay] = fp[0], [bx, by] = fp[1 % fp.length];
  const along = Math.hypot(bx - ax, by - ay), tfs = fs * 0.9;
  // the longest of three wordings that fits along the plate's first edge
  // the plate's own figures, to the second decimal where they have one (69.6 × 19.87, as the memo's head prints it)
  const dm = v => { const r = Math.round(Number(v) * 100) / 100; return Math.abs(r * 10 - Math.round(r * 10)) < 1e-6 ? r.toFixed(1) : r.toFixed(2); };
  const dims = `${dm(p.plate_width_m)} × ${dm(p.plate_depth_m)}`;
  // a plate in two parts (massing: the plate box and a wing) is named by its floor area: the rectangle round it is not its size
  const area = `${Math.round(p.plate_area_m2).toLocaleString("en-CA")} m²`;
  const text = (p.parts ? [`plate in two parts, ${area}`, `two parts, ${area}`, area] : [`plate ${dims} m`, `${dims} m`, dims]).find(t => t.length * tfs * 0.55 <= along - fs * 0.6);
  if (!text) return "";
  const len = text.length * tfs * 0.55;
  const xs = fp.map(q => q[0]), ys = fp.map(q => q[1]);
  let x = xs.reduce((a, b) => a + b, 0) / xs.length;
  const y = ys.reduce((a, b) => a + b, 0) / ys.length;
  const deg = -Math.atan2(by - ay, bx - ax) * 180 / Math.PI;
  if (Math.abs(deg) < 1 && Math.abs(x - xc) < len / 2 + fs * 0.4) {
    const left = (Math.min(...xs) + xc) / 2;
    if (xc - Math.min(...xs) > len + fs * 0.8) x = left;
  }
  return `<text x="${f2(X(x))}" y="${f2(Y(y) + tfs * 0.35)}" font-size="${f2(tfs)}" text-anchor="middle" fill="${FIG.lot}" ${halo(fs)}${Math.abs(deg) > 0.5 ? ` transform="rotate(${deg.toFixed(1)} ${f2(X(x))} ${f2(Y(y))})"` : ""}>${h(text)}</text>`;
}

function inRing(ring, x, y) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
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
