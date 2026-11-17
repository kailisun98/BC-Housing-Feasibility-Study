/* FIG 01 in 3D: a dependency-free orbitable axonometric drawn from massing.json. VIEW3D holds the view. */

import { h } from "../core/util.js";
import { FIG, HALF, halo, NS, SVG_OPEN } from "./common.js";

/* FIG 01 in three dimensions: an orbitable axonometric of the lot, the setback envelope and the two masses, drawn
   from the same massing.json. The camera turns about the lot's centre; azimuth and elevation live in VIEW3D so the
   view survives a re-render. No library: the boxes are projected and painted far to near. */
export const VIEW3D = { mode: "plan", az: 35, el: 28 };

export function fig3d(m, ctx, az = VIEW3D.az, el = VIEW3D.el, fsIn = null) {
  const W = m.lot.frontage_m, D = m.lot.depth_m;
  const masses = Object.fromEntries(m.masses.map(x => [x.name, x]));
  const a = az * Math.PI / 180, e = el * Math.PI / 180;
  const ca = Math.cos(a), sa = Math.sin(a), ce = Math.cos(e), se = Math.sin(e);
  const cx = W / 2, cy = D / 2;
  const fs = fsIn || Math.max(2.2, Math.max(W, D) / 34);
  // metres to the picture plane; y runs away from the street, z up; the viewer starts on the street side
  const proj = ([x, y, z = 0]) => {
    const rx = (x - cx) * ca - (y - cy) * sa, ry = (x - cx) * sa + (y - cy) * ca;
    return { x: rx, y: -(z * ce + ry * se), d: ry * ce - z * se };
  };
  const poly = (ring, attrs) => {
    const P = ring.map(proj);
    return `<polygon points="${P.map(p => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ")}" ${attrs} ${NS}/>`;
  };
  const line = (p, q, attrs) => {
    const A = proj(p), B = proj(q);
    return `<line x1="${A.x.toFixed(2)}" y1="${A.y.toFixed(2)}" x2="${B.x.toFixed(2)}" y2="${B.y.toFixed(2)}" ${attrs} ${NS}/>`;
  };
  // a tree as a lollipop: a stem and a crown, in the half tone
  const tree = (t, opacity) => {
    const top = (t.crown * 1.4) + 2.5, c = proj([t.x, t.y, top]);
    return line([t.x, t.y, 0], [t.x, t.y, top], `stroke="${HALF.treeLine}" stroke-width="0.8"`) +
      `<circle cx="${c.x.toFixed(2)}" cy="${c.y.toFixed(2)}" r="${t.crown}" fill="${HALF.tree}" fill-opacity="${opacity}" stroke="${HALF.treeLine}" stroke-width="0.6" ${NS}/>`;
  };
  // a box from a footprint ring: the top and the four sides, painted far to near
  const box = (ring, z0, z1, fill, stroke, opacity, floors) => {
    const faces = [];
    const n = ring.length;
    for (let i = 0; i < n; i++) {
      const p = ring[i], q = ring[(i + 1) % n];
      faces.push({ ring: [[p[0], p[1], z0], [q[0], q[1], z0], [q[0], q[1], z1], [p[0], p[1], z1]], side: [p, q] });
    }
    faces.push({ ring: ring.map(([x, y]) => [x, y, z1]), top: true });
    for (const f of faces) f.depth = f.ring.reduce((s, p) => s + proj(p).d, 0) / f.ring.length;
    faces.sort((u, v) => v.depth - u.depth);
    let s = "";
    for (const f of faces) {
      s += poly(f.ring, `fill="${fill}" fill-opacity="${f.top ? Math.min(1, opacity + 0.15) : opacity}" stroke="${stroke}" stroke-width="1" stroke-linejoin="round"`);
      if (floors && f.side) {
        for (let k = 1; k < floors.storeys; k++) {
          const z = z0 + k * floors.f2f;
          if (z >= z1) break;
          s += line([f.side[0][0], f.side[0][1], z], [f.side[1][0], f.side[1][1], z], `stroke="${stroke}" stroke-width="0.6" stroke-opacity="0.5"`);
        }
      }
    }
    return s;
  };
  let body = "";
  // the context on the ground first, in half tone, then the lot, the envelope, the masses and the trees
  if (ctx.osm) body += poly([[ctx.xmin, ctx.ymin], [ctx.xmax, ctx.ymin], [ctx.xmax, ctx.ymax], [ctx.xmin, ctx.ymax]], `fill="${HALF.parcel}" stroke="none"`);
  for (const g of ctx.ground) body += poly(g.ring, g.seam ? `fill="${g.fill}" stroke="${g.fill}" stroke-width="0.6" stroke-linejoin="round"` : `fill="${g.fill}" stroke="${HALF.line}" stroke-width="0.8"${g.dash ? ` stroke-dasharray="3 2"` : ""}`);
  body += poly(m.lot.polygon, `fill="#ffffff" stroke="${FIG.lot}" stroke-width="1.2"`);
  body += poly(m.envelope.polygon, `fill="none" stroke="${FIG.env}" stroke-width="1" stroke-dasharray="4 3"`);
  // the buildings around, the trees and the masses are painted far to near so a tree behind a mass stays behind it
  const items = [];
  for (const b of ctx.buildings) {
    const depth = b.polygon.reduce((s, [x, y]) => s + proj([x, y, 0]).d, 0) / b.polygon.length;
    items.push({ d: depth, s: box(b.polygon, 0, b.height, HALF.building, HALF.line, 0.95, null) });
  }
  for (const t of ctx.streetTrees.concat(ctx.osmTrees)) items.push({ d: proj([t.x, t.y, 0]).d, s: tree(t, 0.35) });
  for (const t of ctx.trees) if (t.retained) items.push({ d: proj([t.x, t.y, 0]).d, s: tree(t, 0.45) });
  if (masses.outright) items.push({ d: -1e9, s: box(masses.outright.footprint, masses.outright.base_z || 0, (masses.outright.base_z || 0) + masses.outright.height_m, FIG.outrightFill, FIG.outrightStroke, 0.9, null) });
  if (masses.proposed) {
    const p = masses.proposed;
    const depth = p.footprint.reduce((s, [x, y]) => s + proj([x, y, 0]).d, 0) / p.footprint.length;
    items.push({ d: depth, s: box(p.footprint, p.base_z || 0, (p.base_z || 0) + p.height_m, FIG.proposedFill, FIG.proposedStroke, 0.45, { storeys: p.storeys, f2f: p.floor_to_floor_m }) });
  }
  // the outright mass sits inside the proposed one: paint it right before the proposed box
  const prop = items.find(i => i.d !== -1e9 && i.s.includes(FIG.proposedFill));
  for (const i of items) if (i.d === -1e9) i.d = prop ? prop.d + 1e-6 : 0;
  items.sort((u, v) => v.d - u.d);
  body += items.map(i => i.s).join("");
  // the street names last, over the buildings around, with a paper halo, so none is hidden behind a block
  for (const l of ctx.labels) {
    const c = proj(l.at);
    body += `<text x="${c.x.toFixed(2)}" y="${(c.y + fs * 0.35).toFixed(2)}" font-size="${(fs * 0.9).toFixed(2)}" text-anchor="middle" fill="${l.strong ? FIG.grey : HALF.text}"${l.strong ? ` font-weight="600"` : ""} ${halo(fs)}>${h(l.text)}</text>`;
  }
  const b = m.policy_benchmark;
  if (b && b.height_m && masses.proposed) {
    for (const z of b.height_m) body += poly(masses.proposed.footprint.map(([x, y]) => [x, y, z]), `fill="none" stroke="${FIG.bench}" stroke-width="1" stroke-dasharray="4 3"`);
  }
  // labels: the heights, led off the near top corner of each mass so they sit beside the building, not on its faces
  const labels = [];
  const nearest = ring => ring.map(([x, y]) => [x, y]).sort((u, v) => proj(u).d - proj(v).d)[0];
  // every corner of every mass on the picture plane, so the labels can stand clear of all of them
  const pts = [];
  for (const x of m.masses) for (const [px, py] of x.footprint) for (const z of [x.base_z || 0, (x.base_z || 0) + x.height_m]) pts.push(proj([px, py, z]));
  const minX = Math.min(...pts.map(p => p.x)), maxX = Math.max(...pts.map(p => p.x));
  let lastY = null;
  for (const [name, colour, weight] of [["proposed", FIG.proposedStroke, 600], ["outright", FIG.lot, 400]]) {
    const x = masses[name]; if (!x) continue;
    const c = nearest(x.footprint); const t = proj([c[0], c[1], (x.base_z || 0) + x.height_m]);
    const side = t.x < 0 ? -1 : 1;                       // out on the side the near corner is on
    const lx = side < 0 ? minX - fs * 0.9 : maxX + fs * 0.9;
    let ly = t.y + fs * 0.35;
    if (lastY != null && Math.abs(ly - lastY) < fs * 1.4) ly = lastY + fs * 1.4;
    lastY = ly;
    labels.push(`<line x1="${t.x.toFixed(2)}" y1="${t.y.toFixed(2)}" x2="${(lx - side * fs * 0.3).toFixed(2)}" y2="${(ly - fs * 0.35).toFixed(2)}" stroke="${colour}" stroke-width="0.8" ${NS}/>`
      + `<circle cx="${t.x.toFixed(2)}" cy="${t.y.toFixed(2)}" r="${(fs * 0.18).toFixed(2)}" fill="${colour}"/>`
      + `<text x="${lx.toFixed(2)}" y="${ly.toFixed(2)}" font-size="${fs.toFixed(2)}" font-weight="${weight}" fill="${colour}" text-anchor="${side < 0 ? "end" : "start"}" ${halo(fs)}>${h(x.height_m)} m · ${name}</text>`);
  }
  // a steady frame: the largest extent the drawing can reach at any azimuth and any tilt the orbit allows (8° to
  // 80°), so neither turning nor tilting ever rescales it; a drag reads as one object turning in a fixed window
  const corners = [[ctx.xmin, ctx.ymin], [ctx.xmax, ctx.ymin], [ctx.xmax, ctx.ymax], [ctx.xmin, ctx.ymax]];
  const R = ctx.frameRadius || Math.max(...corners.map(([x, y]) => Math.hypot(x - cx, y - cy)));
  const zmax = Math.max(...m.masses.map(x => (x.base_z || 0) + x.height_m), 1);
  const tilts = [8, 20, 35, 50, 65, 80].map(t => t * Math.PI / 180);
  const top = Math.max(...tilts.map(t => zmax * Math.cos(t) + R * Math.sin(t))), bottom = R * Math.sin(tilts[tilts.length - 1]);
  const pad = fs * 1.5;
  const x0 = -R - pad - fs * 3, x1 = R + pad + fs * 3, y0 = -top - pad - fs, y1 = bottom + pad;
  return `<svg ${SVG_OPEN} viewBox="${x0.toFixed(2)} ${y0.toFixed(2)} ${(x1 - x0).toFixed(2)} ${(y1 - y0).toFixed(2)}" tabindex="0" aria-label="Axonometric of the lot, its surroundings in half tone, the setback envelope and the two masses; drag or use the arrow keys to turn it">${body}${labels.join("")}</svg>`;
}
