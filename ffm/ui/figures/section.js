/* FIG 02: section A–A through the lot, across its depth, where FIG 01 marks it (20 Nov 2026: it was an elevation of
   the frontage titled a section, with no ground, no street, no yards and no levels). The street is on the left and
   the lane or the rear neighbour on the right; the ground is hatched, the yards dimensioned under it; the proposed
   mass is cut with its levels and a height chain; the outright limit is a line of its own, apart from the outright
   mass, so "limit 10.7 m" and "outright 3 storeys, 9.9 m" never read as two answers to one question; the staff
   benchmark is a band; mapped neighbours stand at their heights. */

import { h } from "../core/util.js";
import { crossingsAtX, FIG, HALF, halo, NS, outrightLimit, sectionCut, SVG_OPEN } from "./common.js";

const f2 = v => v.toFixed(2);
// a level or a height keeps its second decimal where it has one (3.05 m storeys: 6.1, 9.15, 12.2; 88.45 m), so the
// levels add up and no height is rounded away from the massing's own figure (88.45 read 88.5 here and 88.4 in the
// engine's words)
const lvl = v => { const r = Math.round(v * 100) / 100; return Math.abs(r * 10 - Math.round(r * 10)) < 1e-6 ? r.toFixed(1) : r.toFixed(2); };
const m1 = lvl;
const short = v => (Math.round(v * 10) / 10).toFixed(1);          // a yard measured at the cut: 3.7, 6.0, 27.5
const SKIP = /^(footway|cycleway|path|steps|pedestrian|track|bridleway)$/;
const REACH = 25;                                                 // how far past the lot the section looks, at most

export function figSection(m, fsIn = null, ctx = null) {
  const masses = Object.fromEntries(m.masses.map(x => [x.name, x]));
  const p = masses.proposed, o = masses.outright;
  const xc = sectionCut(m);
  const ring = m.lot.polygon || [[0, 0], [m.lot.frontage_m, 0], [m.lot.frontage_m, m.lot.depth_m], [0, m.lot.depth_m]];
  const span = (poly, fb) => { const c = crossingsAtX(poly || [], xc); return c.length >= 2 ? [c[0], c[c.length - 1]] : fb; };
  const [L0, L1] = span(ring, [0, m.lot.depth_m]);
  const env = m.envelope && m.envelope.width_m > 0 && m.envelope.depth_m > 0 ? span(m.envelope.polygon, null) : null;
  const massSpan = x => {
    if (!x || !(x.plate_area_m2 > 0) || !(x.footprint || []).length) return null;
    const c = crossingsAtX(x.footprint, xc);
    if (c.length >= 2) return [c[0], c[c.length - 1]];
    const ys = x.footprint.map(q => q[1]);
    return [Math.min(...ys), Math.max(...ys)];
  };
  const pS = massSpan(p), oS = massSpan(o);

  // what the line crosses beyond the lot: streets and lanes, and the neighbours whose height is mapped
  const roads = [];
  if (ctx && ctx.osm && ctx.roads) {
    for (const rd of ctx.roads) {
      if (SKIP.test(rd.kind)) continue;
      const pts = rd.points;
      for (let i = 0; i + 1 < pts.length; i++) {
        const [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
        if (!((x1 <= xc && x2 > xc) || (x2 <= xc && x1 > xc))) continue;
        const c = y1 + (xc - x1) / (x2 - x1) * (y2 - y1), sin = Math.abs(x2 - x1) / Math.hypot(x2 - x1, y2 - y1);
        if (c > L0 - REACH - 10 && c < L1 + REACH + 10 && (c < L0 || c > L1)) roads.push({ c, hw: (rd.width / 2) / Math.max(0.35, sin), name: rd.name || (rd.kind === "service" ? "lane" : null) });
      }
    }
  } else if (ctx) {
    roads.push({ c: L0 - ctx.street.width / 2, hw: ctx.street.width / 2, name: ctx.street.name });
    if (ctx.lane) roads.push({ c: L1 + ctx.lane.width / 2, hw: ctx.lane.width / 2, name: "lane" });
  } else {
    roads.push({ c: L0 - 10, hw: 10, name: (m.lot.front_face && m.lot.front_face.street) || "street" });
  }
  const nbs = [];
  for (const b of (ctx && ctx.osm ? ctx.buildings : [])) {
    if (!b.known) continue;
    const c = crossingsAtX(b.polygon, xc);
    for (let i = 0; i + 1 < c.length; i += 2) {
      const a = Math.max(c[i], L0 - REACH), z = Math.min(c[i + 1], L1 + REACH);
      if (z - a > 0.5 && (z <= L0 + 0.5 || a >= L1 - 0.5)) nbs.push({ a, z, h: b.height });
    }
  }
  // the window: the nearest street in front and the nearest lane behind, with a little beyond, and the neighbours
  const front = roads.filter(r => r.c < L0).sort((u, v) => v.c - u.c)[0], back = roads.filter(r => r.c > L1).sort((u, v) => u.c - v.c)[0];
  let s0 = front ? front.c - front.hw - 3 : L0 - 12, s1 = back ? back.c + back.hw + 3 : L1 + 10;
  for (const n of nbs) { if (n.z <= L0 + 0.5) s0 = Math.min(s0, n.a - 1); else s1 = Math.max(s1, n.z + 1); }
  s0 = Math.min(L0 - 8, Math.max(L0 - REACH - 2, s0)); s1 = Math.max(L1 + 6, Math.min(L1 + REACH + 2, s1));

  const lim = outrightLimit(m);
  const b = m.policy_benchmark && Array.isArray(m.policy_benchmark.height_m) && m.policy_benchmark.height_m.length === 2 ? m.policy_benchmark.height_m : null;
  const zTop = Math.max(3, p ? p.height_m : 0, o ? o.height_m : 0, lim || 0, b ? b[1] : 0, ...nbs.map(n => n.h));
  const fs = fsIn || Math.max(1.6, (s1 - s0) * 1.5 / 42);

  // the labels at the right, each at its height, pushed apart where two would overprint
  const tags = [];
  if (p && pS) tags.push({ z: p.height_m, ax: pS[1], fill: FIG.proposedStroke, weight: 600, text: `proposed ${p.storeys} storeys, ${m1(p.height_m)} m` });
  else if (p) tags.push({ z: 0, ax: L1, fill: FIG.proposedStroke, weight: 600, text: "proposed: no plate fits on the lot as fronted" });
  if (b) tags.push({ z: (b[0] + b[1]) / 2, ax: s1, fill: FIG.benchText, text: `staff benchmark ${m1(b[0])}–${m1(b[1])} m` });
  const atLimit = o && lim && Math.abs(lim - o.height_m) < 0.05;
  if (lim) tags.push({ z: lim, ax: s1, fill: FIG.lot, text: atLimit ? `limit ${m1(lim)} m, the outright mass at it (${o.storeys} storeys)` : `limit ${m1(lim)} m` });
  if (o && oS && !atLimit) tags.push({ z: o.height_m, ax: oS[1], fill: FIG.lot, text: `outright ${o.storeys} storeys, ${m1(o.height_m)} m` });
  const labelW = Math.max(8, ...tags.map(t => t.text.length)) * fs * 0.56;

  // drawing coordinates: x = the depth coordinate from the window's front edge, z up from the ground
  const P0 = pS ? pS[0] : L0;
  const padL = Math.max(fs * 0.6, fs * 2.8 - (P0 - s0));
  const X = s => s - s0 + padL;
  const colX = X(s1) + fs * 0.8;
  const top = zTop + fs * 1.6;
  const Yz = z => top - z;
  const hb = fs * 0.7, chainZ = -hb - fs * 1.35;
  const step = fs * 1.35;
  for (const t of tags) t.y = Yz(t.z) + fs * 0.35;
  tags.sort((u, v) => u.y - v.y);
  for (let k = 1; k < tags.length; k++) tags[k].y = Math.max(tags[k].y, tags[k - 1].y + step);
  const floor = Yz(0) - fs * 0.2;
  if (tags.length && tags[tags.length - 1].y > floor) {
    tags[tags.length - 1].y = floor;
    for (let k = tags.length - 2; k >= 0; k--) tags[k].y = Math.min(tags[k].y, tags[k + 1].y - step);
  }
  const yMin = Math.min(0, ...tags.map(t => t.y - fs * 1.1));
  const vbW = colX + labelW + fs * 0.4, yMax = Yz(chainZ) + fs * 1.55;

  let s = `<svg ${SVG_OPEN} viewBox="0 ${f2(yMin)} ${f2(vbW)} ${f2(yMax - yMin)}" aria-label="Section A–A through the lot, across its depth: the street at the front, ${back ? h(back.name || "the road") : "the rear"} behind, the yards, the proposed mass cut with its levels, the outright height limit and the outright mass${b ? ", the staff benchmark" : ""}">`;
  s += `<rect x="0" y="${f2(yMin)}" width="${f2(vbW)}" height="${f2(yMax - yMin)}" fill="${FIG.paper}"/>`;
  const line = (xa, ya, xb, yb, attrs) => `<line x1="${f2(xa)}" y1="${f2(ya)}" x2="${f2(xb)}" y2="${f2(yb)}" ${attrs} ${NS}/>`;

  // the staff benchmark band over the lot, out to the labels
  if (b) {
    s += `<rect x="${f2(X(L0))}" y="${f2(Yz(b[1]))}" width="${f2(X(s1) - X(L0))}" height="${f2(b[1] - b[0])}" fill="${FIG.bench}" fill-opacity="0.12"/>`;
    for (const z of b) s += line(X(L0), Yz(z), X(s1), Yz(z), `stroke="${FIG.bench}" stroke-width="1" stroke-dasharray="4 3"`);
  }
  // the neighbours the line cuts, at their mapped heights, a step quieter than the lot
  for (const n of nbs) {
    s += `<rect x="${f2(X(n.a))}" y="${f2(Yz(n.h))}" width="${f2(n.z - n.a)}" height="${f2(n.h)}" fill="${HALF.building}" stroke="${HALF.line}" stroke-width="0.8" ${NS}/>`;
    const cx = X((n.a + n.z) / 2);
    s += `<text x="${f2(cx)}" y="${f2(Yz(n.h) - fs * 0.3)}" font-size="${f2(fs * 0.85)}" text-anchor="middle" fill="${HALF.text}" ${halo(fs)}>${h(m1(n.h))} m</text>`;
  }
  // the setback envelope at the cut, red dashed, from the ground to the top of the drawing
  if (env) for (const e of env) s += line(X(e), Yz(0), X(e), Yz(zTop + fs * 0.6), `stroke="${FIG.env}" stroke-width="1" stroke-dasharray="4 3"`);
  // the proposed mass, cut: its floors, then the outright mass over it as a heavy dashed outline, as in plan
  if (p && pS) {
    const H = p.height_m, f = p.floor_to_floor_m || 3;
    // a stepped mass (massing's `tiers`) is cut tier by tier, each at its own depth; else the one box
    const parts = (p.tiers && p.tiers.length > 1 ? p.tiers : [{ footprint: p.footprint, base_z: 0, height_m: H }]).map(t => {
      const c = crossingsAtX(t.footprint, xc);
      return c.length >= 2 ? { a: c[0], z: c[c.length - 1], z0: t.base_z, z1: t.base_z + t.height_m } : null;
    }).filter(Boolean);
    if (!parts.length) parts.push({ a: pS[0], z: pS[1], z0: 0, z1: H });
    for (const t of parts) {
      s += `<rect x="${f2(X(t.a))}" y="${f2(Yz(t.z1))}" width="${f2(t.z - t.a)}" height="${f2(t.z1 - t.z0)}" fill="${FIG.proposedFill}" fill-opacity="0.45" stroke="${FIG.proposedStroke}" stroke-width="1.4" ${NS}/>`;
      for (let k = 1; k <= p.storeys && k * f < H - 0.05; k++) if (k * f > t.z0 + 0.05 && k * f < t.z1 - 0.05) s += line(X(t.a), Yz(k * f), X(t.z), Yz(k * f), `stroke="${FIG.proposedStroke}" stroke-width="0.6" stroke-opacity="0.6"`);
    }
  }
  if (o && oS) s += `<rect x="${f2(X(oS[0]))}" y="${f2(Yz(o.height_m))}" width="${f2(oS[1] - oS[0])}" height="${f2(o.height_m)}" fill="${FIG.outrightFill}" fill-opacity="${pS ? 0.3 : 0.9}" stroke="${FIG.outrightStroke}" stroke-width="2" stroke-dasharray="6 3" ${NS}/>`;
  // the outright limit: a line of its own over the lot, out to its label
  if (lim) s += line(X(L0), Yz(lim), X(s1), Yz(lim), `stroke="${FIG.lot}" stroke-width="1" stroke-dasharray="10 3 2 3"`);

  // the ground: roads at the cut in their tone, the rest hatched; the property lines; the road names under it
  const gy = Yz(0);
  const cutRoads = roads.filter(r => r.c + r.hw > s0 && r.c - r.hw < s1).map(r => Object.assign({}, r, { a: Math.max(s0, r.c - r.hw), z: Math.min(s1, r.c + r.hw) }));
  for (const r of cutRoads) s += `<rect x="${f2(X(r.a))}" y="${f2(gy)}" width="${f2(r.z - r.a)}" height="${f2(hb)}" fill="${HALF.street}" stroke="${HALF.line}" stroke-width="0.6" ${NS}/>`;
  let hatch = "";
  for (let x = s0; x < s1; x += fs * 0.45) {
    if (cutRoads.some(r => x + hb >= r.a && x <= r.z)) continue;
    hatch += `<line x1="${f2(X(x))}" y1="${f2(gy + hb)}" x2="${f2(X(x) + hb)}" y2="${f2(gy)}"/>`;
  }
  s += `<g stroke="${FIG.grey}" stroke-width="0.5" ${NS}>${hatch}</g>`;
  s += line(X(s0), gy, X(s1), gy, `stroke="${FIG.lot}" stroke-width="1.4"`);
  for (const L of [L0, L1]) s += line(X(L), gy + hb, X(L), gy - fs * 1.2, `stroke="${FIG.grey}" stroke-width="0.8" stroke-dasharray="5 2 1.5 2"`);
  for (const r of cutRoads) {
    if (!r.name) continue;
    const half = r.name.length * fs * 0.85 * 0.28;
    const cx = Math.max(s0 + half, Math.min(s1 - half, (r.a + r.z) / 2));
    s += `<text x="${f2(X(cx))}" y="${f2(gy + hb + fs * 0.8)}" font-size="${f2(fs * 0.85)}" text-anchor="middle" fill="${HALF.text}" ${halo(fs)}>${h(r.name)}</text>`;
  }

  // the yards and the envelope at the cut, dimensioned under the ground
  const cy = Yz(chainZ), tk = fs * 0.28;
  const ticks = env ? [L0, env[0], env[1], L1] : [L0, L1];
  s += `<g stroke="${FIG.grey}" stroke-width="0.8" ${NS}>${line(X(L0), cy, X(L1), cy, "")}${ticks.map(t => line(X(t) - tk, cy + tk, X(t) + tk, cy - tk, "")).join("")}</g>`;
  const ty = cy + fs * 1.05, tfs = fs * 0.85;
  const chainText = (a, z, words, value, side) => {
    const len = (w) => w.length * tfs * 0.55;
    let text = `${words} ${value}`;
    if (len(text) < z - a - fs * 0.3) return `<text x="${f2(X((a + z) / 2))}" y="${f2(ty)}" font-size="${f2(tfs)}" text-anchor="middle" fill="${FIG.grey}">${h(text)}</text>`;
    if (side === "mid") { text = value; if (len(text) > z - a) return ""; return `<text x="${f2(X((a + z) / 2))}" y="${f2(ty)}" font-size="${f2(tfs)}" text-anchor="middle" fill="${FIG.grey}">${h(text)}</text>`; }
    return `<text x="${f2(X(side === "front" ? z : a))}" y="${f2(ty)}" font-size="${f2(tfs)}" text-anchor="${side === "front" ? "end" : "start"}" fill="${FIG.grey}">${h(text)}</text>`;
  };
  if (env) {
    if (env[0] - L0 > 0.05) s += chainText(L0, env[0], "front", short(env[0] - L0), "front");
    s += chainText(env[0], env[1], "envelope", short(env[1] - env[0]), "mid");
    if (L1 - env[1] > 0.05) s += chainText(env[1], L1, "rear", short(L1 - env[1]), "rear");
  } else {
    s += chainText(L0, L1, "lot", `${short(L1 - L0)} m`, "mid");
  }

  // the levels on the proposed mass's street face, every one ticked, labelled as often as they can be read; the
  // height chain on its rear face: the storeys, then what the stated height adds over them
  if (p && pS) {
    const [a, z] = pS, H = p.height_m, f = p.floor_to_floor_m || 3, n = p.storeys;
    const every = Math.max(1, Math.ceil(fs * 1.15 / f));
    const levels = [];
    for (let k = 0; k <= n && k * f <= H + 0.01; k++) levels.push({ z: k * f, label: k % every === 0 });
    const extra = H - n * f;
    if (extra > 0.05) levels.push({ z: H, label: true });
    else levels[levels.length - 1].label = true;
    // a labelled level too near the one above it gives way, the roof never
    for (let k = levels.length - 2; k >= 0; k--) {
      const next = levels.slice(k + 1).find(l => l.label);
      if (levels[k].label && next && next.z - levels[k].z < fs * 1.05 && k > 0) levels[k].label = false;
    }
    let lv = "";
    for (const l of levels) {
      lv += line(X(a) - fs * 0.4, Yz(l.z), X(a), Yz(l.z), "");
      if (l.label) s += `<text x="${f2(X(a) - fs * 0.55)}" y="${f2(Yz(l.z) + fs * 0.3)}" font-size="${f2(fs * 0.85)}" text-anchor="end" fill="${FIG.lot}" ${halo(fs)}>${lvl(l.z)}</text>`;
    }
    s += `<g stroke="${FIG.lot}" stroke-width="0.8">${lv}</g>`;
    const hx = X(z) + fs * 0.6, body = n * f;
    const cuts = extra > 0.05 ? [0, body, H] : [0, H];
    s += `<g stroke="${FIG.lot}" stroke-width="0.8" ${NS}>${line(hx, Yz(0), hx, Yz(H), "")}${cuts.map(c => line(hx - tk, Yz(c) + tk, hx + tk, Yz(c) - tk, "")).join("")}</g>`;
    const words = `${n} × ${lvl(f)} m`;
    if (words.length * fs * 0.85 * 0.55 < body - fs * 0.4) {
      const tx = hx + fs * 0.95, tyy = Yz(body / 2);
      s += `<text x="${f2(tx)}" y="${f2(tyy)}" font-size="${f2(fs * 0.85)}" text-anchor="middle" fill="${FIG.lot}" ${halo(fs)} transform="rotate(-90 ${f2(tx)} ${f2(tyy)})">${h(words)}</text>`;
    }
    if (extra > 0.05) s += `<text x="${f2(hx + fs * 0.4)}" y="${f2(Yz(body + extra / 2) + fs * 0.3 - (extra < fs ? fs * 0.6 : 0))}" font-size="${f2(fs * 0.85)}" fill="${FIG.lot}" ${halo(fs)}>+${lvl(extra)}</text>`;
  }

  // the labels, a thin leader joining any that moved to what it names
  for (const t of tags) {
    const at = Yz(t.z), moved = Math.abs(t.y - (at + fs * 0.35)) > fs * 0.4;
    if (moved || t.ax < s1) s += line(X(t.ax), at, colX - fs * 0.25, t.y - fs * 0.35, `stroke="${t.fill}" stroke-width="0.6"`);
    s += `<text x="${f2(colX)}" y="${f2(t.y)}" font-size="${f2(fs)}" fill="${t.fill}"${t.weight ? ` font-weight="${t.weight}"` : ""} ${halo(fs)}>${h(t.text)}</text>`;
  }
  return s + `</svg>`;
}
