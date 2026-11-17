/* What every drawing shares: the palette (from brand.css tokens), SVG boilerplate, label fitting, the scale bar and
   north arrow, and the site's context (OpenStreetMap or the City's data, else schematic) in the lot frame. */

import { $ } from "../core/util.js";

/* the drawing colours of the Lotwise sheets, read from app.css's --c-* tokens (the same in both themes, because the
   drawings sit on white paper): envelope blue, grey streets and lanes, drawing ink, amber for a form line */
export const tok = (name, fallback) => (getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback);

export const FIG = { paper: tok("--c-paper", "#ffffff"), proposedFill: tok("--c-envelope", "#3c8cdc"), proposedStroke: tok("--c-envelope-line", "#2a6fb8"),
              outrightFill: tok("--c-lane", "#bdbdbd"), outrightStroke: tok("--c-street", "#8e8e8e"), bench: tok("--c-bench", "#c77d14"), benchText: tok("--c-bench-text", "#8f5a0e"),
              lot: tok("--c-drawink", "#1f2933"), env: tok("--c-env", "#c81e1e"), grey: tok("--c-drawmuted", "#5f6672") };

export const SVG_OPEN = `xmlns="http://www.w3.org/2000/svg" font-family="IBM Plex Sans, Helvetica, Arial, sans-serif" role="img"`;

export const NS = `vector-effect="non-scaling-stroke"`;

/* a label drawn over the half tone keeps a thin paper halo so it reads over roads and buildings */
const HALO = `paint-order="stroke" stroke="#ffffff" stroke-linejoin="round"`;

export const halo = fs => `${HALO} stroke-width="${(fs * 0.28).toFixed(2)}"`;

/* Drawing labels at one size on screen. The figures are drawn in metres and scale with their card, so a label sized
   in metres would read 20 px in a wide card and 9 px in a narrow one; after a first render the label size is set
   again from the drawing's own scale. */
const LABEL_PX = 11.5;

export function fitLabels(box, build) {
  let fs = null;
  for (let pass = 0; pass < 3; pass++) {
    box.innerHTML = build(fs);
    const svg = $("svg", box), ctm = svg && svg.getScreenCTM();
    if (!ctm || !ctm.a) break;
    const next = LABEL_PX / ctm.a;
    if (fs && Math.abs(next - fs) / fs < 0.03) break;
    fs = next;
  }
  return fs;
}

/* A scale bar in the drawing's corner: a round length near a fifth of the frame, in two halves. */
export function scaleBar(x, y, frameW, fs) {
  const L = [5, 10, 20, 25, 50, 100].find(v => v >= frameW / 6) || 100;
  const hgt = fs * 0.4;
  return `<g class="scalebar">
    <rect x="${(x - fs * 0.4).toFixed(2)}" y="${(y - fs * 1.5).toFixed(2)}" width="${(L + fs * 3.6).toFixed(2)}" height="${(fs * 2.1).toFixed(2)}" fill="${FIG.paper}" fill-opacity="0.85"/>
    <rect x="${x.toFixed(2)}" y="${(y - hgt).toFixed(2)}" width="${(L / 2).toFixed(2)}" height="${hgt.toFixed(2)}" fill="${FIG.lot}"/>
    <rect x="${(x + L / 2).toFixed(2)}" y="${(y - hgt).toFixed(2)}" width="${(L / 2).toFixed(2)}" height="${hgt.toFixed(2)}" fill="${FIG.paper}" stroke="${FIG.lot}" stroke-width="0.8" ${NS}/>
    <text x="${x.toFixed(2)}" y="${(y - hgt - fs * 0.35).toFixed(2)}" font-size="${fs.toFixed(2)}" fill="${FIG.lot}" text-anchor="middle">0</text>
    <text x="${(x + L).toFixed(2)}" y="${(y - hgt - fs * 0.35).toFixed(2)}" font-size="${fs.toFixed(2)}" fill="${FIG.lot}" text-anchor="middle">${L} m</text>
  </g>`;
}

/* North up (17 Nov 2026, Kai: "plan needs to show north as up always"). The lot frame has the street along x, so a
   plan drawn in it faces wherever the street does. Where the site's context frame gives the bearing of the x axis,
   the plan's drawing is turned as a whole so north is up the page: `turnOf(bearing)` is the SVG rotation (degrees,
   clockwise), 0 where no bearing is known and the plan stays street-down. `turnFrame` gives the larger frame the
   turned drawing needs and the group that turns it; `upright` keeps every label readable, turning any that the
   rotation leaves upside down half a turn about its own middle. The scale bar and the north arrow stay level. */
export const turnOf = bearing => (typeof bearing === "number" && isFinite(bearing) ? (((bearing - 90) % 360) + 540) % 360 - 180 : 0);

export function turnFrame(w, h, a) {
  const t = a * Math.PI / 180, W = Math.abs(w * Math.cos(t)) + Math.abs(h * Math.sin(t)), H = Math.abs(w * Math.sin(t)) + Math.abs(h * Math.cos(t));
  return { W, H, open: `<g class="plan-turn" transform="translate(${((W - w) / 2).toFixed(2)} ${((H - h) / 2).toFixed(2)}) rotate(${a.toFixed(2)} ${(w / 2).toFixed(2)} ${(h / 2).toFixed(2)})">` };
}

export function upright(s, a) {
  if (!a) return s;
  return s.replace(/<text\b([^>]*)>/g, (all, attrs) => {
    const num = k => { const m = attrs.match(new RegExp(`(?:^|\\s)${k}="(-?[\\d.]+)"`)); return m ? parseFloat(m[1]) : 0; };
    const tm = attrs.match(/transform="rotate\((-?[\d.]+)/);
    const total = (((a + (tm ? parseFloat(tm[1]) : 0)) % 360) + 540) % 360 - 180;
    if (total <= 90 && total > -90) return all;
    const flip = `rotate(180 ${num("x").toFixed(2)} ${(num("y") - 0.35 * (num("font-size") || 10)).toFixed(2)})`;
    return /transform="/.test(attrs) ? `<text${attrs.replace(/transform="([^"]*)"/, (m, v) => `transform="${v} ${flip}"`)}>` : `<text${attrs} transform="${flip}">`;
  });
}

/* A north arrow, only where the site's OpenStreetMap frame says which way the lot faces; the plan is drawn with the
   street at the bottom, so north is wherever the frame puts it. x_axis_bearing_deg is the bearing of the lot's x axis
   (along the frontage); the plan's up is the y axis, 90 degrees anticlockwise of it. */
export function northArrow(cx, cy, bearing, fs) {
  const rot = 90 - bearing;          // north, measured clockwise from the drawing's up
  const r = fs * 1.15, t = rot * Math.PI / 180, d = r + fs * 0.8;
  const nx = cx + d * Math.sin(t), ny = cy - d * Math.cos(t) + fs * 0.35;   // the N stays upright, beyond the tip
  return `<g class="north"><g transform="rotate(${rot.toFixed(1)} ${cx.toFixed(2)} ${cy.toFixed(2)})">
    <circle cx="${cx.toFixed(2)}" cy="${cy.toFixed(2)}" r="${r.toFixed(2)}" fill="${FIG.paper}" fill-opacity="0.85" stroke="${FIG.lot}" stroke-width="0.8" ${NS}/>
    <polygon points="${cx.toFixed(2)},${(cy - r * 0.92).toFixed(2)} ${(cx + r * 0.42).toFixed(2)},${(cy + r * 0.55).toFixed(2)} ${cx.toFixed(2)},${(cy + r * 0.2).toFixed(2)} ${(cx - r * 0.42).toFixed(2)},${(cy + r * 0.55).toFixed(2)}" fill="${FIG.lot}"/>
    </g><text x="${nx.toFixed(2)}" y="${ny.toFixed(2)}" font-size="${(fs * 0.95).toFixed(2)}" font-weight="600" text-anchor="middle" fill="${FIG.lot}" ${halo(fs)}>N</text></g>`;
}

export function polyEl(pts, attrs) {
  return `<polygon points="${pts.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(" ")}" ${attrs} ${NS}/>`;
}

/* The context around the lot, in half tone: the street in front, the lane behind, cross streets, the neighbouring
   parcels, street trees and the trees on site. Real figures come from site.context when the site file has them;
   otherwise typical defaults stand in (a 20 m street, a 6 m lane, neighbours of the lot's own depth) and the
   on-site trees, whose positions are rarely public, are placed schematically along the rear. */
export const HALF = { street: tok("--c-half-road", "#e9e9e6"), parcel: tok("--c-bldg", "#f4f4f2"), building: tok("--c-half-building", "#e2e2df"),
               line: tok("--c-half-line", "#c9c9c5"), text: tok("--c-street-text", "#63635f"), tree: tok("--c-tree", "#9fb07f"),
               treeLine: tok("--c-tree-line", "#7f9664"), gone: tok("--c-lane", "#bdbdbd") };

export function siteContext(site, m) {
  const W = m.lot.frontage_m, D = m.lot.depth_m;
  const c = (site && site.context) || {};
  const street = { name: (c.street && c.street.name) || (site && site.street_trees && site.street_trees.street) || "street", width: (c.street && c.street.width_m) || 20 };
  const lane = c.lane === false || c.lane === null ? null : { width: (c.lane && c.lane.width_m) || 6 };
  const cross = [];
  for (const k of ["left", "right"]) {
    const x = c[`${k}_street`] || (c.cross_street && c.cross_street.side === k ? c.cross_street : null);
    if (x) cross.push({ side: k, name: x.name || "street", width: x.width_m || 20 });
  }
  const neighbours = [];
  for (const k of ["left", "right"]) {
    if (c.neighbours === false || cross.some(x => x.side === k)) continue;
    const n = (c.neighbours && c.neighbours[k]) || {};
    neighbours.push({ side: k, width: n.frontage_m || Math.max(12, Math.round(W * 0.6)) });
  }
  const streetTrees = (c.street_trees_count != null ? c.street_trees_count : (site && site.street_trees && site.street_trees.count)) || 0;
  const list = (site && site.existing_trees_on_site) || [];
  const pos = Object.fromEntries((c.trees || []).map(t => [t.id, t]));
  let schematic = false;
  const trees = list.map((t, i) => {
    const p = pos[t.id];
    if (!p) schematic = true;
    const crown = (p && p.crown_m) || Math.min(6, Math.max(2, (t.dbh_cm || 20) / 10));
    const x = p ? p.x : 6 + (W - 12) * (list.length > 1 ? i / (list.length - 1) : 0.5);
    const y = p ? p.y : D - 7;
    return { id: t.id, x, y, crown, retained: t.status === "retain" };
  });
  const left = cross.find(x => x.side === "left"), right = cross.find(x => x.side === "right");
  const nl = neighbours.find(n => n.side === "left"), nr = neighbours.find(n => n.side === "right");
  const ext = { left: left ? left.width : nl ? nl.width : 0, right: right ? right.width : nr ? nr.width : 0 };
  const bbL = m.lot.bbox || [0, 0, W, D];     // a polygon lot may run past the equivalent rectangle
  const xmin = Math.min(0, bbL[0]) - ext.left, xmax = Math.max(W, bbL[2]) + ext.right, ymin = Math.min(0, bbL[1]) - street.width, ymax = Math.max(D, bbL[3]) + (lane ? lane.width : 0);
  // the ground shapes, in lot coordinates (x along the frontage, y into the lot; the street is y < 0)
  const ground = [];
  ground.push({ ring: [[xmin, ymin], [xmax, ymin], [xmax, 0], [xmin, 0]], fill: HALF.street, label: street.name, at: [W / 2, -street.width / 2] });
  if (lane) ground.push({ ring: [[xmin, D], [xmax, D], [xmax, ymax], [xmin, ymax]], fill: HALF.street, label: "lane", at: [W / 2, D + lane.width / 2] });
  for (const x of cross) {
    const ring = x.side === "left" ? [[xmin, 0], [0, 0], [0, ymax], [xmin, ymax]] : [[W, 0], [xmax, 0], [xmax, ymax], [W, ymax]];
    ground.push({ ring, fill: HALF.street, label: x.name, at: [x.side === "left" ? -x.width / 2 : W + x.width / 2, D / 2], rotate: true });
  }
  for (const n of neighbours) {
    const ring = n.side === "left" ? [[-n.width, 0], [0, 0], [0, D], [-n.width, D]] : [[W, 0], [W + n.width, 0], [W + n.width, D], [W, D]];
    ground.push({ ring, fill: HALF.parcel, dash: true, label: "neighbour", at: [n.side === "left" ? -n.width / 2 : W + n.width / 2, D * 0.85] });
  }
  const streetTreeList = [];
  for (let i = 0; i < streetTrees; i++) streetTreeList.push({ x: W * (i + 0.5) / streetTrees, y: -3, crown: 2.5 });
  const labels = ground.map(g => ({ text: g.label, at: g.at, angle: g.rotate ? 90 : 0 }));
  const base = { W, D, street, lane, cross, neighbours, streetTrees: streetTreeList, trees, schematic, ground, labels, buildings: [], osmTrees: [], xmin, xmax, ymin, ymax, osm: null };
  return site && site.osm ? osmContext(site, m, base) : base;
}

/* The same context from OpenStreetMap when `python -m ffm context` has stored it in the site file: roads as
   strips of their width, building footprints (extruded in 3D by their tagged height or storeys), mapped trees,
   all already in the lot's metres. The lot's own trees from the site file stay as they are. */
function osmContext(site, m, base) {
  const o0 = site.osm, W = m.lot.frontage_m, D = m.lot.depth_m;
  // the lot turned to a chosen front face (massing's lot.orientation: new = R(θ)·old + t) turns the stored context
  // with it, so the streets and buildings still stand where they do around the lot (16 Nov 2026)
  const o = m.lot.orientation ? orientedOsm(o0, m.lot.orientation) : o0;
  const r = (o.radius_m || 120) * 0.92;
  const ground = [], labels = [], seen = new Set();
  // the address street is always named, beside the lot and clear of the frontage dimension along its front
  const front = (m.lot.front_face && m.lot.front_face.street) || (o.frame && o.frame.front_street);
  if (front) {
    let best = null;
    for (const road of (o.roads || []).filter(x => x.name === front)) {
      const pts = road.points || [], T = [W + Math.max(18, W * 0.35), -(road.width_m || 8) / 2];
      for (let i = 0; i + 1 < pts.length; i++) {
        const [x1, y1] = pts[i], [x2, y2] = pts[i + 1], dx = x2 - x1, dy = y2 - y1, L2 = dx * dx + dy * dy;
        if (!L2) continue;
        const t = Math.max(0, Math.min(1, ((T[0] - x1) * dx + (T[1] - y1) * dy) / L2));
        const q = [x1 + t * dx, y1 + t * dy], dist = Math.hypot(q[0] - T[0], q[1] - T[1]);
        if (!best || dist < best.dist) best = { dist, at: q, angle: Math.atan2(dy, dx) * 180 / Math.PI };
      }
    }
    if (best) {
      let angle = best.angle; if (angle > 90) angle -= 180; if (angle < -90) angle += 180;
      labels.push({ text: front, at: best.at, angle, strong: true });
      seen.add(front);
    }
  }
  for (const road of o.roads || []) {
    const w = road.width_m || 8, pts = road.points || [];
    for (let i = 0; i + 1 < pts.length; i++) {
      const [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
      const L = Math.hypot(x2 - x1, y2 - y1); if (!L) continue;
      const nx = -(y2 - y1) / L * w / 2, ny = (x2 - x1) / L * w / 2;
      ground.push({ ring: [[x1 + nx, y1 + ny], [x2 + nx, y2 + ny], [x2 - nx, y2 - ny], [x1 - nx, y1 - ny]], fill: HALF.street, seam: true });
    }
    if (road.name && !seen.has(road.name) && pts.length > 1) {
      // label the longest segment of each named road, once, if it falls inside the frame
      let best = null;
      for (let i = 0; i + 1 < pts.length; i++) {
        const L = Math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]);
        if (!best || L > best.L) best = { L, i };
      }
      const [x1, y1] = pts[best.i], [x2, y2] = pts[best.i + 1];
      const at = [(x1 + x2) / 2, (y1 + y2) / 2];
      if (Math.abs(at[0] - W / 2) < r && Math.abs(at[1] - D / 2) < r) {
        let angle = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
        if (angle > 90) angle -= 180; if (angle < -90) angle += 180;
        labels.push({ text: road.name, at, angle });
        seen.add(road.name);
      }
    }
  }
  const buildings = (o.buildings || []).map(b => ({ polygon: b.polygon, height: b.height_m || 7, name: b.name }));
  const osmTrees = (o.trees || []).map(t => ({ x: t.x, y: t.y, crown: t.crown_m || 3 }));
  return Object.assign({}, base, {
    ground, labels, buildings, osmTrees, streetTrees: [],
    xmin: W / 2 - r, xmax: W / 2 + r, ymin: D / 2 - r, ymax: D / 2 + r, frameRadius: r * 0.75,
    osm: { attribution: o.attribution, fetched: (o.fetched_at || "").slice(0, 10), radius: o.radius_m, counts: o.counts || {}, omitted: o.buildings_on_site_omitted || [], frontStreet: front || (o.frame && o.frame.front_street),
           bearing: o.frame && typeof o.frame.x_axis_bearing_deg === "number" ? (o.frame.x_axis_bearing_deg - (m.lot.orientation ? m.lot.orientation.rotate_deg : 0) + 360) % 360 : null },
  });
}

/* The stored context with the lot's orientation applied to every point (roads, buildings, trees). Pure. */
function orientedOsm(o, or) {
  const th = (or.rotate_deg || 0) * Math.PI / 180, c = Math.cos(th), s = Math.sin(th);
  const T = ([x, y]) => [c * x - s * y + (or.tx || 0), s * x + c * y + (or.ty || 0)];
  return Object.assign({}, o, {
    roads: (o.roads || []).map(rd => Object.assign({}, rd, { points: (rd.points || []).map(T) })),
    buildings: (o.buildings || []).map(b => Object.assign({}, b, { polygon: (b.polygon || []).map(T) })),
    trees: (o.trees || []).map(t => { const [x, y] = T([t.x, t.y]); return Object.assign({}, t, { x, y }); }),
  });
}
