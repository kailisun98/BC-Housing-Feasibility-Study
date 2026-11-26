/* The block editor (architect mode, FIG 03), loaded on first use: schematic program plans on the plates.
   The program the manager approved sits beside the plate the whole time, each block with what is placed and what
   is left; the architect drags a block from it onto the plate, or asks for a suggested plan and adjusts it. The
   blocks' walls sit on a structural grid (a 6 m or 8 m bay, wall to wall, and its half or quarter); a core is
   the same on every floor, so moving it on one floor moves it on all. The engine measures every move
   (POST /api/layout, or the engine in the browser) and says what broke and which rules still hold; the other
   sheets redraw from the same check. Apply writes the placement into the option (`layout.zones`, `layout.grid`),
   so Run the rules reproduces it and the memo says it was placed by hand. Rebuilt 17 Nov 2026. */

import { $, $$, fmtNum, h, pill, setStatus, toast, todayISO } from "../core/util.js";
import { runRules } from "../runs.js";
import { editor, state } from "../core/state.js";
import { postJSON } from "../core/api.js";
import { refreshSummary, renderForm } from "../schedule.js";
import { markStale, onOptionChange, tidyOption } from "../files.js";
import { OPTION_FIELDS } from "../fields.js";
import { egressLine } from "../memo/answers.js";
import { refreshPlanFloor } from "../figures/cards.js";
import { HALF, northArrow, projectTurn, siteContext, sunShadows, turnFrame, upright } from "../figures/common.js";

const EDIT_BLOCKS = [["studio", "Studio"], ["one_bed", "One-bedroom"], ["two_bed", "Two-bedroom"], ["three_bed_plus", "Three-bedroom+"], ["non_residential", "Non-residential"], ["amenity", "Amenity"], ["services", "Services, bicycles"], ["core", "Core"], ["corridor", "Corridor"],
  ["design_space", "Design space"], ["commercial", "Commercial"], ["void", "Cut-out"]];

/* the architect's own blocks: no program asks for them, so they are never short; a cut-out is not floor area */
const OPTIONAL = [["design_space", "Design space", "a lobby, an atrium"], ["commercial", "Commercial", "shops, offices, a café · counts as non-residential"]];

const ZONE_TONE = { studio: "#dbe9f8", one_bed: "#b9d4f0", two_bed: "#8fb8e3", three_bed_plus: "#6b9fd4", corridor: "#f4f4f2", core: "#c9c9c5", services: "#e2e2df", amenity: "#f6e7c1", non_residential: "#f0cf9a", other: "#e6dfd0", design_space: "#d9e6d2", commercial: "#f3c9b5", void: "url(#ed-hatch)" };

const ZONE_SHORT = { studio: "st", one_bed: "1b", two_bed: "2b", three_bed_plus: "3b", corridor: "corridor", core: "core", services: "services", amenity: "amenity", non_residential: "non-res", design_space: "design", commercial: "commercial", void: "open" };

const UNIT_KEYS = ["studio", "one_bed", "two_bed", "three_bed_plus"];
const isUnit = k => UNIT_KEYS.includes(k);
const zoneShort = z => z.name ? String(z.name).slice(0, 16) : z.block === "other" ? String(z.label || "other").slice(0, 12).toLowerCase() : (ZONE_SHORT[z.block] || z.block);
const blockName = z => z.name ? String(z.name) : z.block === "other" ? (z.label || "Other") : (EDIT_BLOCKS.find(([k]) => k === z.block)?.[1] || z.block);
const floorName = lv => lv === 0 ? "Ground" : `L${lv + 1}`;
const floorWords = lv => lv === 0 ? "the ground floor" : `L${lv + 1}`;

/* the structural grid: the bay is the wall-to-wall width, the module the bay or its half or quarter; every
   block's walls sit on the module, counted from the plate's left edge */
const BAYS = [6, 7.5, 8];
const DIVIDES = [[1, "whole bays"], [2, "half bays"], [4, "quarter bays"]];
const CORR = 1.8;   // the corridor's width, as the solver's
const CORE_MIN = 7; // a core this wide is read as two stairs (layout.py, core_bay_m)
const M = 20;       // the canvas margin, px
const r2 = v => Math.round(v * 100) / 100;
const mod = () => editor.bay / editor.divide;
const ceilM = v => r2(Math.max(1, Math.ceil(v / mod() - 1e-6)) * mod());
/* a unit's width on the grid, as the solver's: the nearest whole number of modules, as long as that keeps the
   unit at or over the BC Housing minimum with its partitions; otherwise the next module up */
/* and never narrower than the home's minimum width (the program's `min_width_m`), nor more than DEPTH_RATIO times as
   deep as it is wide: the engine's declared placeholders (layout.py, UNIT_MIN_WIDTH_M, UNIT_DEPTH_RATIO_MAX) */
const DEPTH_RATIO = 2.5;
const unitW = (gross, minGross, strip, minW = 0) => {
  const near = Math.max(1, Math.round(gross / strip / mod())) * mod(), least = Math.max(minW || 0, strip / DEPTH_RATIO);
  return near * strip + 0.5 >= (minGross || gross) && near + 1e-6 >= least ? r2(near) : ceilM(Math.max(gross / strip, least));
};

/* What the step-backs take off a level, each side: the deepest of every step that starts at or below it. */
function stepAt(level) {
  const out = { front: 0, rear: 0, left: 0, right: 0 };
  for (const s of editor.steps || []) if (level >= s.from_level) for (const k of Object.keys(out)) out[k] = Math.max(out[k], s[k] || 0);
  return out;
}

/* What the editor says is said twice: in the page's status strip, and in a line over the plate, beside the work
   (25 Nov 2026: the strip is at the top of the page, a screen away from the control that was used). */
function say(text, tone) {
  setStatus(text, tone);
  editor.msg = { text, tone: tone || "info" };
  const el = $("#ed-msg");
  if (el) { el.textContent = text; el.dataset.tone = editor.msg.tone; el.hidden = false; }
}

function zonesFromLayout(L) {
  const out = {};
  for (const fl of L.floors) out[String(fl.level)] = fl.zones.filter(z => z.block !== "spare").map(z => ({ block: z.block, x: z.x, y: z.y, w: z.w, d: z.d, ...(z.accessible ? { accessible: true } : {}), ...(z.block === "other" ? { label: z.label } : {}), ...(z.stairs === "scissor" ? { stairs: "scissor" } : {}), ...(z.name ? { name: z.name } : {}), ...(z.step ? { step: true } : {}),
    ...(z.home != null && z.levels ? { home: z.home, levels: [...z.levels] } : {}) }));
  return out;
}

/* The strips a plate offers: the street strip, the corridor behind it, the lane strip (a double-loaded plate; a
   point tower's lane strip is the plate's back, the ring and the core between). */
function bandsOf(p, level = editor.level) {
  const strip = p.unit_depth_m, corr = r2(p.y + strip);
  // a stepped floor's strips are shallower by what the step-back took off the street and the lane side
  const st = stepAt(level), cutF = Math.min(st.front || 0, Math.max(0, strip - 1)), cutR = Math.min(st.rear || 0, Math.max(0, strip - 1));
  return { strip, front: r2(p.y + cutF), frontD: r2(strip - cutF), rearD: r2(strip - cutR), corr, rear: p.double_loaded ? r2(corr + CORR) : p.arrangement === "point" ? r2(p.y + p.depth_m - strip) : null };
}

/* What the program asks for against what the editor has placed on every floor: one row per block, with what is
   left to place; the architect's own programs (option.layout.extra_programs) are rows too. Pure. */
function programTracker(L, zones) {
  const all = Object.values(zones || {}).flat();
  const rows = (L.program || []).map(b => {
    const unit = isUnit(b.key);
    // commercial space the architect drew is non-residential floor area: it counts toward that program, as the engine's
    const mine = all.filter(z => b.key === "other" ? (z.block === "other" && String(z.label || "").trim().toLowerCase() === String(b.label).trim().toLowerCase())
      : b.key === "non_residential" ? (z.block === "non_residential" || z.block === "commercial") : z.block === b.key);
    const placedArea = mine.reduce((t, z) => t + z.w * z.d, 0);
    return unit ? { key: b.key, label: b.label, unit: true, need: b.count, placed: mine.length, left: b.count - mine.length, each: b.gross_m2_each, min: b.min_gross_m2_each, minW: b.min_width_m }
      : { key: b.key, label: b.label, unit: false, need: b.area_m2, placed: Math.round(placedArea), left: Math.round(b.area_m2 - placedArea) };
  });
  // a use placed in whole modules runs a little over its area: over is said past 15%
  for (const r of rows) r.short = r.left > (r.unit ? 0 : 1), r.over = r.left < (r.unit ? 0 : -Math.max(1, 0.15 * r.need));
  // services that do not fit at grade go below it with the parking (layout.py, 23 Nov 2026): not a block left to place
  for (const r of rows) if (r.key === "services" && r.short) { r.short = false; r.below = r.left; }
  const units = rows.filter(r => r.unit);
  return { rows, unitsNeed: units.reduce((t, r) => t + r.need, 0), unitsLeft: units.reduce((t, r) => t + Math.max(0, r.left), 0),
    areasShort: rows.filter(r => !r.unit && r.short).length, done: rows.every(r => !r.short) };
}

/* The blocks on one floor that share floor area (the corridor may cross a core, as the engine reads it). Pure. */
function clashes(zs) {
  const bad = new Set();
  for (let i = 0; i < zs.length; i++) for (let j = i + 1; j < zs.length; j++) {
    const a = zs[i], b = zs[j];
    if ((a.block === "corridor" && b.block === "core") || (a.block === "core" && b.block === "corridor")) continue;
    if (!(a.x + a.w <= b.x + 0.025 || b.x + b.w <= a.x + 0.025 || a.y + a.d <= b.y + 0.025 || b.y + b.d <= a.y + 0.025)) { bad.add(i); bad.add(j); }
  }
  return bad;
}

export function openEditor(resume) {
  const run = state.run;
  if (!run || !run.layout) return;
  const lay = (state.option && state.option.layout) || {};
  const fromOption = lay.zones;
  const grid = lay.grid || run.layout.plate.grid;
  if (grid && grid.bay_m) { editor.bay = Number(grid.bay_m) || 6; editor.divide = [1, 2, 4].includes(Number(grid.divide)) ? Number(grid.divide) : 4; }
  editor.open = true; editor.level = 0; editor.sel = null; editor.dirty = false; editor.applied = !!fromOption; editor.history = []; editor.dragging = false; editor.coreMoved = !!fromOption;
  // the levels the architect adds here sit on top of the option's own storeys until Apply writes them into it
  editor.added = 0;
  editor.base = { plate: (run.layout.capacity && run.layout.capacity.plate_m2) || Math.round(run.layout.plate.width_m * run.layout.plate.depth_m * 10) / 10, f2f: run.layout.plate.floor_to_floor_m || 0 };
  editor.base.auto = editor.base.plate;   // the plate the floor area and the storeys give: what Auto goes back to
  const st0 = state.option && state.option.massing && state.option.massing.steps;
  editor.steps = Array.isArray(st0) && st0.length ? JSON.parse(JSON.stringify(st0)) : null;
  // the plate's own dimensions, where the option already states them; the site behind the plate, on unless put away
  const ms = state.option && state.option.massing;
  editor.plate = ms && ms.width_m > 0 && ms.depth_m > 0 ? { w: Number(ms.width_m), d: Number(ms.depth_m) } : null;
  editor.angle = Number(ms && ms.angle_deg) || 0;
  editor.anchor = null;   // where the plate stands in the plate box, where the editor moved it (Fit the plate to the turn)
  editor.massing = run.massing || null;
  try { editor.context = localStorage.getItem("ffm.ed.context") !== "0"; } catch (e) { editor.context = true; }
  // the editor opens on the plan the memo drew (the run's own floors, as layout.zones_of gives them), never on another
  // (20 Nov 2026: it opened on a fresh suggestion, 64 of 105 homes placed and the exits passing, beside a memo whose plan
  // placed 69 and failed the exits on every floor: two plans for one option). A grid plan is a separate action.
  editor.zones = JSON.parse(JSON.stringify(fromOption || zonesFromLayout(run.layout)));
  editor.result = run.layout;
  editor.sel = null;
  if (resume && resume.level != null && run.layout.floors[resume.level]) editor.level = resume.level;   // back on the floor it was on
  // and back in view: a run redraws the memo and takes the page to its top, a dozen screens above the editor (25 Nov 2026)
  if (resume) setTimeout(() => { const el = $("#sheet-editor"); if (el && editor.open) { const y = el.getBoundingClientRect().top + scrollY - 130; scrollTo({ top: Math.max(0, y), behavior: "auto" }); } }, 450);
  else editor.msg = null;
  const fig = $('.figure.sheet[data-sheet="plans"]');
  $$(".sheet-body", fig).forEach(x => { x.hidden = true; });
  $("#edit-blocks").setAttribute("aria-expanded", "true");
  $("#edit-blocks").textContent = "Close the editor";
  $("#sheet-editor").hidden = false;
  renderEditor();
  const L = run.layout, left = (L.units_total || 0) - (L.units_placed || 0);
  say(fromOption
    ? "Block editor: your placement, as the option carries it. Drag a block from the program onto the plate, or move one on the plate (or Tab to it and use the arrows); the engine checks every move."
    : `Block editor: the memo's own plan, ${L.units_placed ?? "?"} of ${L.units_total ?? "?"} homes placed${left > 0 ? `, ${left} left to place` : ""}. Move a block (drag it, or Tab to it and use the arrows), or Suggest a grid plan for a different plan laid out afresh on the grid.`, "info");
  checkPlacement();   // a run read from disk may predate what the editor reads (the FSR room)
}

export function closeEditor() {
  editor.open = false;
  const fig = $('.figure.sheet[data-sheet="plans"]');
  if (!fig) return;
  const view = ($('[data-sheet-view][aria-pressed="true"]', fig) || {}).dataset?.sheetView || "plans";
  $$(".sheet-body", fig).forEach(x => { x.hidden = x.dataset.view !== view; });
  $("#sheet-editor").hidden = true;
  const b = $("#edit-blocks"); if (b) { b.setAttribute("aria-expanded", "false"); b.textContent = "Edit blocks"; }
  if (editor.dirty && !editor.applied) say("The editor closed with changes not applied to the option; open it again to apply them.", "info");
}

/* ---------------------------------------------------------------- undo, and the cores that stand on every floor */

function snapshot() {
  (editor.history = editor.history || []).push(JSON.stringify({ z: editor.zones, a: editor.added || 0, p: editor.plate || null, t: editor.angle || 0, s: editor.steps || null, n: editor.anchor || null }));
  if (editor.history.length > 60) editor.history.shift();
}

function undo() {
  const s = (editor.history || []).pop();
  if (!s) return;
  const was = JSON.parse(s);
  editor.zones = was.z; editor.added = was.a; editor.plate = was.p || null; editor.angle = was.t || 0; editor.steps = was.s || null; editor.anchor = was.n || null; editor.sel = null; editor.dirty = true;
  renderEditor(); scheduleCheck();
  say("Undone.", "info");
}

const coresNow = () => (editor.zones[String(editor.level)] || []).filter(z => z.block === "core").map(z => ({ x: z.x, y: z.y, w: z.w, d: z.d }));

/* The stairs do not shift from level to level: the cores of the floor in view replace the cores of every other
   floor. Returns how many blocks on the other floors now share floor area with a core. */
function syncCores() {
  const L = editor.result || state.run.layout;
  const cores = coresNow();
  let hit = 0;
  for (const fl of L.floors) {
    const k = String(fl.level);
    if (fl.level === editor.level) continue;
    const rest = (editor.zones[k] || []).filter(z => z.block !== "core");
    editor.zones[k] = rest.concat(cores.map(c => ({ block: "core", ...c })));
    hit += rest.filter(z => z.block !== "corridor" && cores.some(c => !(z.x + z.w <= c.x + 0.01 || c.x + c.w <= z.x + 0.01 || z.y + z.d <= c.y + 0.01 || c.y + c.d <= z.y + 0.01))).length;
  }
  return hit;
}

/* A ground-oriented home runs through its floors (`home`, `levels`, 25 Nov 2026: it was edited floor by floor): a
   home moved, resized or retyped on the floor in view is the same on every floor it spans, and one removed here is
   removed from them all. Returns how many floors were changed besides this one. */
function syncHomes() {
  const here = editor.zones[String(editor.level)] || [];
  const ids = new Map(here.filter(z => z.home != null).map(z => [z.home, z]));
  let changed = 0;
  for (const [k, zs] of Object.entries(editor.zones)) {
    if (Number(k) === editor.level) continue;
    const kept = [];
    for (const z of zs) {
      if (z.home == null || !z.levels || editor.level < z.levels[0] || editor.level > z.levels[1]) { kept.push(z); continue; }
      const src = ids.get(z.home);
      if (!src) { changed++; continue; }                      // removed on this floor: removed from all of its floors
      if (src.x !== z.x || src.y !== z.y || src.w !== z.w || src.d !== z.d || src.block !== z.block) {
        Object.assign(z, { x: src.x, y: src.y, w: src.w, d: src.d, block: src.block }); changed++;
      }
      kept.push(z);
    }
    editor.zones[k] = kept;
  }
  return changed;
}

/* Every change ends here: the cores follow on every floor when one was touched, the editor redraws, the engine checks. */
function commit(core) {
  if (syncHomes()) say("The home runs through its floors: the change is made on each of them.", "info");
  if (core) {
    editor.coreMoved = true;   // from here a suggested plan keeps the cores where the architect stood them
    const L = editor.result || state.run.layout, hit = syncCores();
    say(`The cores are the same on all ${L.floors.length} floors: the stairs do not shift from level to level.${hit ? ` ${hit} block${hit === 1 ? "" : "s"} on other floors now sit${hit === 1 ? "s" : ""} on a core: move them, or Suggest a grid plan lays the program round the cores.` : ""}`, hit ? "busy" : "info");
  }
  editor.dirty = true;
  renderEditor(); scheduleCheck();
}

/* ---------------------------------------------------------------- the drawing */

/* What the canvas shows, in the lot's metres: the plate alone, or (with the context on) the lot with a margin
   round it, so the property line, the setback envelope, the streets and the neighbours stand behind the plate. */
function viewOf(p, m, width) {
  let v = { x0: p.x, y0: p.y, x1: p.x + p.width_m, y1: p.y + p.depth_m, ctx: false };
  if (editor.context && m && m.lot) {
    const bb = m.lot.bbox || [0, 0, m.lot.frontage_m, m.lot.depth_m], pad = 9;
    // "plate": the plate large, with a margin of the site round it (the lot line and the setbacks where they fall in
    // it); "site": the whole lot and its streets, the plate small in it
    const near = Math.max(5, 0.16 * Math.max(p.width_m, p.depth_m));
    if (editor.zoom !== "site") v = { x0: p.x - near, y0: p.y - near, x1: p.x + p.width_m + near, y1: p.y + p.depth_m + near, ctx: true };
    else v = { x0: Math.min(bb[0], p.x) - pad, y0: Math.min(bb[1], p.y) - pad - 5, x1: Math.max(bb[2], p.x + p.width_m) + pad, y1: Math.max(bb[3], p.y + p.depth_m) + pad, ctx: true };
  }
  // a turned mass reaches past its own rectangle: the view takes the turned outline in
  const t = (editor.angle || 0) * Math.PI / 180;
  if (t) {
    const hw = (Math.abs(p.width_m * Math.cos(t)) + Math.abs(p.depth_m * Math.sin(t))) / 2, hd = (Math.abs(p.width_m * Math.sin(t)) + Math.abs(p.depth_m * Math.cos(t))) / 2;
    const cx = p.x + p.width_m / 2, cy = p.y + p.depth_m / 2, pad = v.ctx ? 2 : 0;
    v.x0 = Math.min(v.x0, cx - hw - pad); v.x1 = Math.max(v.x1, cx + hw + pad); v.y0 = Math.min(v.y0, cy - hd - pad); v.y1 = Math.max(v.y1, cy + hd + pad);
  }
  v.s = (width - 2 * M) / Math.max(1, v.x1 - v.x0);
  v.X = x => M + (x - v.x0) * v.s;
  v.Y = y => M + (v.y1 - y) * v.s;
  // without the site behind it, room under the plate for the grid's distances and the caption (20 Nov 2026)
  v.H = (v.y1 - v.y0) * v.s + 2 * M + 2 + (v.ctx ? 0 : 18);
  return v;
}

const rectOf = (z, v) => ({ x: v.X(z.x), y: v.Y(z.y + z.d), w: Math.max(1, z.w * v.s), d: Math.max(1, z.d * v.s) });

/* The site behind the plate: the streets, the neighbouring buildings and trees in half tone, the lot with its
   property line (long dash, two dots), the setback envelope dashed red. From the same context FIG 01 draws. */
/* The turned plate's outline in the lot frame. */
function massRing(p, angle) {
  const cx = p.x + p.width_m / 2, cy = p.y + p.depth_m / 2, t = (angle || 0) * Math.PI / 180, c = Math.cos(t), s = Math.sin(t), w = p.width_m / 2, d = p.depth_m / 2;
  return [[-w, -d], [w, -d], [w, d], [-w, d]].map(([dx, dy]) => [cx + dx * c - dy * s, cy + dx * s + dy * c]);
}

/* A first reading of the shadows, not a shadow study: the mass as one box of its full height, on flat ground, at
   the equinox at 10 am, noon and 2 pm daylight time (the hours the City asks for), for Vancouver's longitude (the
   sun's hour angles -50, -20 and +10 degrees) at the site's latitude. Each is the outline swept along the shadow's
   direction by height over the tangent of the sun's altitude. `bearing` is the compass bearing of the lot's x axis. */
function shadowsOf(p, angle, height, bearing, lat) {
  const ring = massRing(p, angle), phi = (lat || 49.26) * Math.PI / 180, beta = bearing * Math.PI / 180;
  const hull = pts => {
    const P = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]), cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]), lo = [], up = [];
    for (const q of P) { while (lo.length >= 2 && cross(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q); }
    for (const q of P.slice().reverse()) { while (up.length >= 2 && cross(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop(); up.push(q); }
    return lo.slice(0, -1).concat(up.slice(0, -1));
  };
  return [["10 am", -50], ["noon", -20], ["2 pm", 10]].map(([label, hd]) => {
    const Hh = hd * Math.PI / 180, alt = Math.asin(Math.cos(phi) * Math.cos(Hh)), az = Math.atan2(Math.sin(Hh), Math.cos(Hh) * Math.sin(phi)) + Math.PI;
    const len = height / Math.tan(alt), th = az + Math.PI - beta, vx = Math.cos(th) * len, vy = -Math.sin(th) * len;   // a compass direction θ is (cos(θ−β), −sin(θ−β)) in the lot frame
    return { label, len, ring: hull(ring.concat(ring.map(([x, y]) => [x + vx, y + vy]))), tip: [ring.reduce((a, q) => a + q[0], 0) / 4 + vx, ring.reduce((a, q) => a + q[1], 0) / 4 + vy] };
  });
}

/* The least distance between two outlines (0 where a corner of one stands inside... is not looked for: they are
   taken not to overlap), and from the mass to the lot line. */
function ringGap(a, b) {
  const seg = (q, u, v) => { const dx = v[0] - u[0], dy = v[1] - u[1], L2 = dx * dx + dy * dy, t = L2 ? Math.max(0, Math.min(1, ((q[0] - u[0]) * dx + (q[1] - u[1]) * dy) / L2)) : 0; return Math.hypot(q[0] - u[0] - t * dx, q[1] - u[1] - t * dy); };
  let best = Infinity;
  for (const [P, Q] of [[a, b], [b, a]]) for (const q of P) for (let i = 0; i < Q.length; i++) best = Math.min(best, seg(q, Q[i], Q[(i + 1) % Q.length]));
  return best;
}

function contextSvg(m, v, sun) {
  const ctx = siteContext(state.site, m), f = n => n.toFixed(1);
  const P = pts => pts.map(([x, y]) => `${f(v.X(x))},${f(v.Y(y))}`).join(" ");
  let s = `<rect x="0" y="0" width="100%" height="100%" fill="${ctx.osm ? HALF.parcel : "#ffffff"}"/>`;
  for (const g of ctx.ground) s += `<polygon points="${P(g.ring)}" fill="${g.fill}" stroke="${g.seam ? g.fill : HALF.line}" stroke-width="0.6"${g.dash ? ` stroke-dasharray="3 2"` : ""}/>`;
  for (const b of ctx.buildings) s += `<polygon points="${P(b.polygon)}" fill="${HALF.building}" stroke="${HALF.line}" stroke-width="0.6"/>`;
  for (const t of ctx.streetTrees.concat(ctx.osmTrees)) s += `<circle cx="${f(v.X(t.x))}" cy="${f(v.Y(t.y))}" r="${f(Math.max(1.5, t.crown * v.s))}" fill="${HALF.tree}" fill-opacity="0.35" stroke="${HALF.treeLine}" stroke-width="0.6"/>`;
  s += `<polygon points="${P(m.lot.polygon)}" fill="#ffffff" stroke="#1f2933" stroke-width="1.2" stroke-dasharray="12 3 2 3 2 3"/>`;
  // the shadows at the equinox, over the ground and the neighbours, under the plate: the longest first
  for (const sh of (sun || []).slice().sort((a, b) => b.len - a.len)) {
    s += `<g opacity="0.16">${sh.rings.map(r => `<polygon points="${P(r)}" fill="#1f2933"/>`).join("")}</g>`;
    s += `<text x="${f(v.X(sh.tip[0]))}" y="${f(v.Y(sh.tip[1]))}" font-size="9" text-anchor="middle" fill="#1f2933">${h(sh.label)}</text>`;
  }
  for (const t of ctx.trees) s += `<circle cx="${f(v.X(t.x))}" cy="${f(v.Y(t.y))}" r="${f(Math.max(1.5, t.crown * v.s))}" fill="${t.retained ? HALF.tree : "none"}" fill-opacity="0.4" stroke="${t.retained ? HALF.treeLine : HALF.gone}" stroke-width="0.6"${t.retained ? "" : ` stroke-dasharray="2 2"`}/>`;
  if (m.envelope && m.envelope.polygon) s += `<polygon points="${P(m.envelope.polygon)}" fill="none" stroke="#c81e1e" stroke-width="0.9" stroke-dasharray="4 3"/>`;
  for (const l of ctx.labels) {
    const x = v.X(l.at[0]), y = v.Y(l.at[1]);
    if (x < 0 || y < 0 || !l.text) continue;
    s += `<text x="${f(x)}" y="${f(y + 3)}" font-size="9.5" text-anchor="middle" fill="${HALF.text}"${l.strong ? ` font-weight="600"` : ""}${l.angle ? ` transform="rotate(${(-l.angle).toFixed(1)} ${f(x)} ${f(y)})"` : ""}>${h(l.text)}</text>`;
  }
  return `<g class="ed-context" pointer-events="none">${s}</g>`;
}

/* one block: its rectangle, the accessible mark, its name and width (at the 11 px floor, where they fit) */
function zoneInner(z, r) {
  const f = v => v.toFixed(1);
  const two = r.w > 40 && r.d > 36 && z.block !== "corridor";
  return `<rect x="${f(r.x)}" y="${f(r.y)}" width="${f(r.w)}" height="${f(r.d)}" fill="${ZONE_TONE[z.block] || "#eee"}" stroke="#5f6672" stroke-width="0.8"${z.block === "void" ? ` stroke-dasharray="5 3"` : ""}/>
    ${z.accessible ? `<circle cx="${f(r.x + 7)}" cy="${f(r.y + 7)}" r="3.2" fill="#245f9c"/>` : ""}
    ${r.w > 26 && r.d > 14 ? `<text x="${f(r.x + r.w / 2)}" y="${f(r.y + r.d / 2 + (two ? -1.5 : 4))}" font-size="11" font-weight="500" text-anchor="middle" fill="#1f2933">${h(zoneShort(z))}</text>` : ""}
    ${two ? `<text x="${f(r.x + r.w / 2)}" y="${f(r.y + r.d / 2 + 12)}" font-size="11" text-anchor="middle" fill="#5f6672">${h(z.w)} m</text>` : ""}`;
}

/* The selected block's ring and its three handles, drawn over every block (20 Nov 2026: the selected block was moved to
   the end of the drawing to stand on top, which moved it in the tab order too, so Tab from it left the plan; the
   blocks now keep their order and the ring stands over them). */
function selOverlay(i, z, V) {
  const r = rectOf(z, V), f = v => v.toFixed(1);
  return `<g class="ed-selover" data-i="${i}">
    <rect class="ed-ring-halo" x="${f(r.x - 2)}" y="${f(r.y - 2)}" width="${f(r.w + 4)}" height="${f(r.d + 4)}" fill="none" pointer-events="none"/>
    <rect class="ed-ring" x="${f(r.x - 2)}" y="${f(r.y - 2)}" width="${f(r.w + 4)}" height="${f(r.d + 4)}" fill="none" pointer-events="none"/>
    <rect class="ed-handle ed-handle-w" x="${f(r.x + r.w - 4)}" y="${f(r.y + r.d / 2 - 7)}" width="8" height="14" rx="2" fill="#245f9c"/>
    <rect class="ed-handle ed-handle-l" x="${f(r.x - 4)}" y="${f(r.y + r.d / 2 - 7)}" width="8" height="14" rx="2" fill="#245f9c"/>
    <rect class="ed-handle ed-handle-d" x="${f(r.x + r.w / 2 - 7)}" y="${f(r.y - 4)}" width="14" height="8" rx="2" fill="#245f9c"/>
  </g>`;
}

/* the line above the plate: what is selected and what can be done with it */
function selBarHtml(L, zs) {
  const sel = editor.sel != null ? zs[editor.sel] : null;
  if (!sel) return `<span class="help">Drag a block from the program onto the plate (or press Enter on its row). On the plate: drag to move, pull an edge to resize; or Tab to a block and the arrows move it, Delete removes it, Ctrl+Z undoes.</span>`;
  const prog = (L.program || []).find(b => b.key === sel.block);
  const gross = prog && prog.gross_m2_each, least = (prog && prog.min_gross_m2_each) || gross, a = sel.w * sel.d;
  const over = !gross ? "" : (a > gross * 1.15 ? ` <span class="warn-text">· ${fmtNum(Math.round(a - gross))} m² over the ${fmtNum(Math.round(gross))} m² the program carries</span>` : (a + 0.5 < least ? ` <span class="warn-text">· ${fmtNum(Math.round(least - a))} m² under its ${fmtNum(Math.round(least))} m² minimum</span>` : ""));
  // a home narrower than its type's minimum, or more than DEPTH_RATIO times as deep as wide (width along the plate)
  const minW = prog && prog.min_width_m;
  const thin = !minW ? "" : (sel.w + 0.05 < minW ? ` <span class="warn-text">· ${h(r2(minW - sel.w))} m under its ${h(minW)} m minimum width</span>`
    : (sel.d / sel.w > DEPTH_RATIO + 0.01 ? ` <span class="warn-text">· ${h((sel.d / sel.w).toFixed(1))} times as deep as wide (${DEPTH_RATIO} at most)</span>` : ""));
  // a program block can be turned into another program where it stands; the cores and corridors are structure
  const structure = sel.block === "core" || sel.block === "corridor";
  const valOf = b => b.key === "other" ? `other:${b.label}` : b.key, mine = sel.block === "other" ? `other:${sel.label || "Other"}` : sel.block;
  const kinds = (L.program || []).map(b => [valOf(b), b.label]).concat(OPTIONAL.map(([k, l]) => [k, l]), [["void", "Cut-out (not floor)"]]);
  if (!structure && !kinds.some(([v]) => v === mine)) kinds.unshift([mine, blockName(sel)]);
  const name = structure ? `<b>${h(blockName(sel))}</b>` : `<select id="ed-kind" class="ed-kind" aria-label="The program of this block" title="Change this block's program">${kinds.map(([v, l]) => `<option value="${h(v)}"${v === mine ? " selected" : ""}>${h(l)}</option>`).join("")}</select>`;
  return `${name}
    ${structure ? "" : `<input type="text" id="ed-name" class="ed-name" maxlength="40" value="${h(sel.name || "")}" placeholder="name it (Lobby, Café…)" aria-label="A name for this block" title="Your own name for this block; it is drawn on the plate and the sheets">`}
    <span class="ed-size"><input type="number" id="ed-w" step="0.1" min="0.5" value="${h(sel.w)}" aria-label="Width in metres" title="Width along the plate, in metres"> × <input type="number" id="ed-d" step="0.1" min="0.5" value="${h(sel.d)}" aria-label="Depth in metres" title="Depth across the plate, in metres"> m, ${h(fmtNum(Math.round(a)))} m²${over}${thin}</span>
    <button type="button" class="btn btn-small btn-quiet" id="ed-dup" title="A copy of this block beside it, or in the first free place on this floor (Ctrl+D)">Duplicate</button>
    ${sel.block === "core" ? `<span class="cont">on all ${L.floors.length} floors</span>` : `<label class="field inline"><span class="label">to floor</span><select id="ed-move">${L.floors.map(fl => `<option value="${fl.level}"${fl.level === editor.level ? " selected" : ""}>${h(floorName(fl.level))}</option>`).join("")}</select></label>`}
    ${isUnit(sel.block) ? `<label class="ed-acc"><input type="checkbox" id="ed-acc"${sel.accessible ? " checked" : ""}> accessible</label>` : ""}
    <button type="button" class="btn btn-small btn-quiet" id="ed-del">Remove</button>`;
}

/* the program beside the plate: every block the manager approved, what is placed, what is left; a row is dragged
   onto the plate, or clicked to land in the first free spot */
function programHtml(L, tr, zs, B) {
  const row = (kind, label, tone, meta, count, cls, pct, aria) => `<li class="ed-prog ${cls}" data-kind="${h(kind)}" data-label="${h(label)}" tabindex="0" role="button" aria-label="${h(aria)}" title="Drag onto the plate, or click to add it in the first free spot">
      <span class="sw" style="background:${tone}"></span>
      <span class="nm">${h(label)}<small>${h(meta)}</small></span>
      <span class="ct">${count}</span>
      ${pct == null ? "" : `<span class="bar"><i style="width:${pct.toFixed(0)}%"></i></span>`}
    </li>`;
  const rows = tr.rows.map(r => {
    const cls = r.short ? "short" : (r.over ? "over" : "done");
    const pct = r.need > 0 ? Math.min(100, r.placed / r.need * 100) : 100;
    if (r.unit) {
      const count = r.short ? `<b>${r.left}</b> to place` : (r.over ? `<b>${-r.left}</b> over` : "placed");
      return row(r.key, r.label, ZONE_TONE[r.key], `${fmtNum(Math.round(r.each))} m² · ${B.strip ? `${unitW(r.each, r.min, B.strip, r.minW)} m wide = ${fmtNum(Math.round(unitW(r.each, r.min, B.strip, r.minW) * B.strip))} m²` : "?"} · ${r.placed} of ${r.need}`, count, cls, pct,
        `${r.label}: ${r.placed} of ${r.need} placed${r.short ? `, ${r.left} to place` : ""}. Enter adds one to this floor.`);
    }
    const count = r.below ? `${fmtNum(r.below)} m² below grade` : r.short ? `<b>${fmtNum(r.left)} m²</b> to place` : (r.over ? `<b>${fmtNum(-r.left)} m²</b> over` : "placed");
    return row(r.key, r.label, ZONE_TONE[r.key] || ZONE_TONE.other, `${fmtNum(r.placed)} of ${fmtNum(Math.round(r.need))} m²`, count, cls, pct,
      `${r.label}: ${r.placed} of ${Math.round(r.need)} square metres placed. Enter adds it to this floor.`);
  }).join("");
  const nCore = zs.filter(z => z.block === "core").length;
  const withCorr = L.floors.filter(fl => (editor.zones[String(fl.level)] || []).some(z => z.block === "corridor")).length;
  const hereCorr = zs.some(z => z.block === "corridor");
  // the count is of blocks, each standing on every floor (20 Nov 2026: "3 on every floor" beside what read as one core)
  const structure = row("core", "Core", ZONE_TONE.core, "stairs, elevator · the same on every floor", nCore ? `${nCore} block${nCore === 1 ? "" : "s"}` : "<b>none</b>", nCore ? "done" : "short", null, `Core: ${nCore} block${nCore === 1 ? "" : "s"}, each the same on every floor. Enter adds one.`)
    + row("corridor", "Corridor", ZONE_TONE.corridor, `${withCorr} of ${L.floors.length} floors have one`, hereCorr ? "on this floor" : "<b>none here</b>", hereCorr ? "done" : "short", null, `Corridor: ${hereCorr ? "on this floor" : "none on this floor"}. Enter adds one.`);
  // the architect's own blocks: placed area only, nothing asked for
  const areaOf = kind => Math.round(Object.values(editor.zones).flat().filter(z => z.block === kind).reduce((t, z) => t + z.w * z.d, 0));
  const optional = OPTIONAL.map(([k, l, what]) => row(k, l, ZONE_TONE[k], what, areaOf(k) ? `${fmtNum(areaOf(k))} m²` : "add", "done", null, `${l}, ${what}: ${areaOf(k)} square metres placed. Enter adds one to this floor.`)).join("");
  const cut = areaOf("void");
  const cutRow = row("void", "Cut-out", "repeating-linear-gradient(45deg, #fff 0 3px, #aab4c0 3px 4px)", "open to below, a notch, a courtyard · not floor area", cut ? `${fmtNum(cut)} m²` : "add", "done", null, `Cut-out, not floor area: ${cut} square metres. Enter adds one to this floor.`);
  const head = tr.unitsLeft ? `<b>${tr.unitsLeft}</b> of ${tr.unitsNeed} units to place` : `All <b>${tr.unitsNeed}</b> units placed`;
  return `<aside class="ed-program" aria-label="The program, placed and left to place">
      <div class="ed-prog-head"><span class="eyebrow">Program</span><span class="ed-left ${tr.done ? "done" : "short"}">${head}${tr.areasShort ? ` · ${tr.areasShort} other block${tr.areasShort === 1 ? "" : "s"} short` : ""}</span></div>
      <ul class="ed-prog-list">${rows}</ul>
      <div class="ed-prog-sub">Yours to add · lobbies, atriums, commercial</div>
      <ul class="ed-prog-list">${optional}</ul>
      <div class="ed-prog-sub">Structure and plate shape</div>
      <ul class="ed-prog-list">${structure}${cutRow}</ul>
      <details class="ed-newprog"><summary>Add a program of your own</summary>
        <input type="text" id="ed-prog-label" placeholder="e.g. Childcare" maxlength="40" aria-label="Program name">
        <input type="number" id="ed-prog-area" placeholder="m²" min="1" step="1" aria-label="Program area in square metres">
        <button type="button" class="btn btn-small" id="ed-prog-add">Add</button>
        <span class="help">It joins the program above and the option (layout.extra_programs).</span>
      </details>
    </aside>`;
}

function renderEditor() {
  const box = $("#sheet-editor");
  if (!box) return;
  editor.pendingRender = false;
  const L = editor.result || state.run.layout, p = L.plate, B = bandsOf(p), m = mod();
  if (!L.floors[editor.level]) editor.level = 0;
  const zs = editor.zones[String(editor.level)] || (editor.zones[String(editor.level)] = []);
  if (editor.sel != null && !zs[editor.sel]) editor.sel = null;
  // what the page holds that a redraw must not lose: the focus on the plate, a program being typed
  const hadFocus = !!(document.activeElement && document.activeElement.closest && document.activeElement.closest(".ed-canvas"));
  const typed = { label: ($("#ed-prog-label", box) || {}).value || "", area: ($("#ed-prog-area", box) || {}).value || "", open: !!($(".ed-newprog", box) || {}).open, focus: (document.activeElement || {}).id };
  const boxW = Math.max(320, box.clientWidth || 600);
  const wide = boxW >= 760;
  const width = (wide ? boxW - 272 : boxW) - 4;
  const V = viewOf(p, editor.massing, width), scale = V.s, H = V.H;
  // north up, as every plan: the canvas is drawn in the lot frame and turned as a whole where the context gives
  // the bearing; the pointer is read back in the turned group's own coordinates (wireEditor)
  const site = editor.massing && editor.massing.lot ? siteContext(state.site, editor.massing) : null;
  const turn = projectTurn(site && site.osm && site.osm.bearing), frame = turnFrame(width, H, turn), U = s => upright(s, turn);
  // the mass turned on the lot (counter-clockwise in the lot frame, so the other way on the canvas, whose y runs
  // down): the plate, its grid and its blocks are one group turned about the plate's centre, over the site
  const ang = editor.angle || 0, UM = s => upright(s, turn - ang);
  // the shadows (where the context gives north), and how far the mass stands from its neighbours and the lot line
  const capH = (L.capacity && L.capacity.height_m) || p.storeys * p.floor_to_floor_m;
  const canSun = !!(site && site.osm && site.osm.bearing != null);
  const sun = V.ctx && editor.shadows && canSun ? sunShadows([{ ring: massRing(p, ang), top: capH }], site.osm.bearing, site.osm.lat) : null;
  const ringNow = massRing(p, ang);
  const nbGap = site && site.buildings && site.buildings.length ? Math.min(...site.buildings.map(b => ringGap(ringNow, b.polygon))) : null;
  const lotGap = editor.massing && editor.massing.lot && editor.massing.lot.polygon ? ringGap(ringNow, editor.massing.lot.polygon) : null;
  const past = ((editor.massing && editor.massing.warnings) || []).find(w => /past the setback envelope/.test(w));
  const px0 = V.X(p.x), py0 = V.Y(p.y + p.depth_m), pw = p.width_m * scale, pd = p.depth_m * scale;   // the plate on the canvas
  const env = editor.massing && editor.massing.envelope, maxW = env ? ((env.box && env.box.w) || env.width_m) : p.width_m, maxD = env ? ((env.box && env.box.d) || env.depth_m) : p.depth_m;
  const bad = clashes(zs);
  // the blocks in their own order, which is the tab order; the selected one's ring and handles stand over them all
  const svgZones = zs.map((z, i) => `<g class="ed-zone${i === editor.sel ? " sel" : ""}${bad.has(i) ? " clash" : ""}" data-i="${i}" tabindex="0" role="button" aria-label="${h(blockName(z))}, ${z.w} by ${z.d} m, at ${z.x}, ${z.y} m${bad.has(i) ? ", overlapping another block" : ""}. Arrows move it, Delete removes it">${zoneInner(z, rectOf(z, V))}</g>`).join("")
    + (editor.sel != null && zs[editor.sel] ? selOverlay(editor.sel, zs[editor.sel], V) : "");
  // the grid: a line at every bay, a fainter one at every module, the bays' distances along the street side, centred
  // 12 px off the plate's edge so they read clear of the wall whichever way the plan is turned (20 Nov 2026: on a plan
  // turned north up they sat on the wall line, and the depth handle covered the middle one)
  let grid = "", ticks = "";
  for (let k = 0; k * m <= p.width_m + 1e-6; k++) {
    const x = (px0 + k * m * scale).toFixed(1), bay = k % editor.divide === 0;
    grid += `<line x1="${x}" y1="${py0.toFixed(1)}" x2="${x}" y2="${(py0 + pd).toFixed(1)}" stroke="${bay ? "#aab4c0" : "#cfd6de"}" stroke-width="${bay ? 0.8 : 0.5}"${bay ? "" : ` stroke-dasharray="2 3"`}/>`;
    if (bay && editor.bay * scale >= 26) ticks += `<text x="${x}" y="${(py0 + pd + 12 + 3.9).toFixed(1)}" font-size="11" text-anchor="middle" fill="#5f6672">${r2(k * m)}</text>`;
  }
  // the grid across the plate as well: a line at every bay from the street face, and a column where the bays meet
  for (let j = 1; j * editor.bay < p.depth_m - 0.05; j++) {
    const y = V.Y(p.y + j * editor.bay).toFixed(1);
    grid += `<line x1="${px0.toFixed(1)}" y1="${y}" x2="${(px0 + pw).toFixed(1)}" y2="${y}" stroke="#cfd6de" stroke-width="0.5" stroke-dasharray="2 3"/>`;
  }
  let columns = "";
  if (editor.bay * scale >= 14) for (let k = 0; k * editor.bay <= p.width_m + 1e-6; k++) for (let j = 0; j * editor.bay <= p.depth_m + 1e-6; j++)
    columns += `<rect x="${(px0 + k * editor.bay * scale - 1.6).toFixed(1)}" y="${(V.Y(p.y + j * editor.bay) - 1.6).toFixed(1)}" width="3.2" height="3.2" fill="#5f6672"/>`;
  // the parkade under it, as a first count (placeholders): the stalls at the layout's area a stall, the levels that
  // takes under what the setbacks leave, the ramp a level, and the stalls a bay holds between columns
  const pk = L.parking && L.parking.spaces ? (() => {
    const under = Math.max(1, maxW * maxD), levels = Math.max(1, Math.ceil(L.parking.area_m2 / under)), perBay = Math.floor(editor.bay / 2.6);
    return `Parkade, a first count: ${L.parking.spaces} stalls take ${fmtNum(Math.round(L.parking.area_m2))} m², ${levels} level${levels === 1 ? "" : "s"} under the ${fmtNum(Math.round(under))} m² the setbacks leave; a ramp about ${Math.round(3 / 0.125)} m long a level at 12.5%; a ${editor.bay} m bay holds ${perBay} stall${perBay === 1 ? "" : "s"} between columns${perBay * 2.6 + 0.4 > editor.bay ? ", tight" : ""}.`;
  })() : "";
  const bandY = v => V.Y(v).toFixed(1);
  const bandLines = [B.corr, B.rear].filter(v => v != null && v < p.y + p.depth_m - 0.05).map(v => `<line x1="${px0.toFixed(1)}" y1="${bandY(v)}" x2="${(px0 + pw).toFixed(1)}" y2="${bandY(v)}" stroke="#aab4c0" stroke-width="0.6" stroke-dasharray="5 4"/>`).join("");
  const floorsBtns = L.floors.map(fl => {
    const n = (editor.zones[String(fl.level)] || []).filter(z => isUnit(z.block)).length;
    const broken = (L.geometry || []).some(g => g.level === fl.level);
    return `<button type="button" class="segbtn" data-ed-level="${fl.level}" aria-pressed="${fl.level === editor.level}" title="${h(floorName(fl.level))}: ${n} unit${n === 1 ? "" : "s"}${broken ? ", something to fix" : ""}">${h(floorName(fl.level))}<small>${n}</small>${broken ? `<i class="ed-flag" aria-label="something to fix"></i>` : ""}</button>`;
  }).join("");
  const floorChecks = (L.geometry || []).filter(g => g.level === editor.level);
  const problems = (L.geometry || []).length;
  const tr = programTracker(L, editor.zones);
  const egF = L.egress && (L.egress.floors || []).find(f => f.level === editor.level);
  const otherBay = !BAYS.includes(editor.bay);
  // another level, where the FSR leaves room for one more plate
  const cap = L.capacity, f3 = v => (Math.round(v * 100) / 100).toFixed(2);
  const canAdd = !!cap && (cap.fsr_limit == null || cap.levels_room >= 1);
  const overs = oversOf(cap);
  const groups = editor.groups || (editor.groups = { plate: false, options: false });
  const steps = editor.steps || [], step = steps[steps.length - 1] || null;
  const stepWords = s => `from ${floorName(s.from_level)} up: ${["front", "rear", "left", "right"].filter(k => s[k] > 0).map(k => `${k} ${s[k]} m`).join(", ")}`;
  const tall = cap && cap.height_limit_m != null && cap.height_with_one_more > cap.height_limit_m + 0.05 ? ` A level more stands ${cap.height_with_one_more} m high, past the ${cap.height_limit_m} m of ${cap.height_from}.` : "";
  const capNote = !cap ? "" : (cap.fsr_limit == null ? `FSR ${f3(cap.fsr)} · the rules carry no FSR limit here`
    : `FSR ${f3(cap.fsr)} of ${f3(cap.fsr_limit)} · ${cap.levels_room >= 1 ? (tall ? `room in the FSR for ${cap.levels_room} more level${cap.levels_room === 1 ? "" : "s"}, none in the height` : `room for ${cap.levels_room} more level${cap.levels_room === 1 ? "" : "s"}`) : `no room for a level (${fmtNum(Math.round(cap.plate_m2))} m² needed, ${fmtNum(Math.max(0, Math.round(cap.room_m2)))} m² left)`}`);
  const capTitle = !cap ? "" : (cap.fsr_limit == null ? `Add a level of ${fmtNum(Math.round(cap.plate_m2))} m²: the FSR goes to ${f3(cap.fsr_with_one_more)}; the rules carry no FSR limit for this district to hold it against`
    : (canAdd ? `Add a level of ${fmtNum(Math.round(cap.plate_m2))} m² for the program left to place: the FSR goes to ${f3(cap.fsr_with_one_more)} of ${f3(cap.fsr_limit)} (${cap.limit_from})` : `A level of ${fmtNum(Math.round(cap.plate_m2))} m² would take the FSR to ${f3(cap.fsr_with_one_more)}, past ${f3(cap.fsr_limit)} (${cap.limit_from})`));
  const levelsCtl = !cap ? "" : `<span class="ed-levels">
        <button type="button" class="btn btn-small" id="ed-addlevel"${canAdd ? "" : " disabled"} title="${h(capTitle + tall)}">+ Level</button>
        ${editor.added ? `<button type="button" class="btn btn-small btn-quiet" id="ed-dellevel" title="Take the top level off again, with its blocks">− Level</button>` : ""}
        <span class="help${cap.fsr_limit != null && !canAdd ? " warn-text" : ""}">${h(capNote)}${cap.height_limit_m != null ? ` · height ${h(cap.height_m)} of ${h(cap.height_limit_m)} m` : ""}</span></span>`;
  box.classList.toggle("ed-wide", wide);
  box.innerHTML = `
    <div class="ed-bar">
      <span class="label" title="The floor shown, and the homes placed on each">Floor · homes</span>
      <div class="seg ed-floors" role="group" aria-label="Floor">${floorsBtns}</div>
      ${levelsCtl}
      <span class="ed-tools">
        <span class="help ed-busy" id="ed-busy"${editor.busy ? "" : " hidden"}>Checking…</span>
        <span class="seg" role="group" aria-label="What the drawing shows"><button type="button" class="segbtn" data-ed-zoom="plate" aria-pressed="${editor.zoom !== "site"}" title="The plate large, with a margin of the site round it">Plate</button><button type="button" class="segbtn" data-ed-zoom="site" aria-pressed="${editor.zoom === "site"}" title="The whole lot with its streets and neighbours">Site</button></span>
        <button type="button" class="btn btn-small btn-quiet" id="ed-undo"${(editor.history || []).length ? "" : " disabled"} title="Undo the last change (Ctrl+Z)">Undo</button>
        <button type="button" class="btn btn-small" id="ed-suggest" title="A different plan from the memo's: the engine lays the whole program out afresh on this grid, round the cores where they stand; Undo brings back what was there">Suggest a grid plan</button>
      </span>
    </div>
    <details class="ed-group" data-group="plate"${groups.plate ? " open" : ""}>
      <summary><b>Plate, grid and turn</b> <span class="cont">· ${h(p.width_m)} × ${h(p.depth_m)} m${editor.plate ? " (set by hand)" : ""}${ang ? `, turned ${ang}°` : ""} · ${h(editor.bay)} m bay · ${editor.context ? "site shown" : "site hidden"}${editor.shadows ? ", shadows" : ""}</span></summary>
      <div class="ed-bar">
      <span class="ed-grid" role="group" aria-label="Structural grid">
        <span class="label">Bay, wall to wall</span>
        <span class="seg">${BAYS.map(v => `<button type="button" class="segbtn" data-ed-bay="${v}" aria-pressed="${editor.bay === v}">${v} m</button>`).join("")}</span>
        <input type="number" id="ed-bay-other" min="3" max="12" step="0.1" placeholder="other" value="${otherBay ? editor.bay : ""}" aria-label="Another bay width in metres" title="Another bay width, 3 to 12 m">
        <select id="ed-divide" aria-label="What the walls sit on" title="What the blocks' walls sit on">${DIVIDES.map(([v, l]) => `<option value="${v}"${v === editor.divide ? " selected" : ""}>walls on ${h(l)}</option>`).join("")}</select>
      </span>
      <span class="ed-plate" role="group" aria-label="Floor plate">
        <span class="label">Plate</span>
        <input type="number" id="ed-plate-w" min="6" max="${h(maxW)}" step="0.5" value="${h(p.width_m)}" aria-label="Plate width in metres" title="Plate width along the street, up to the ${h(maxW)} m the setbacks leave">
        <span class="label">×</span>
        <input type="number" id="ed-plate-d" min="6" max="${h(maxD)}" step="0.5" value="${h(p.depth_m)}" aria-label="Plate depth in metres" title="Plate depth into the lot, up to the ${h(maxD)} m the setbacks leave">
        <span class="label">m</span>
        ${editor.plate ? `<button type="button" class="btn btn-small btn-quiet" id="ed-plate-auto" title="Back to the plate the floor area and the storeys give">Auto</button>` : ""}
        <span class="label">Turn</span>
        <button type="button" class="btn btn-small btn-quiet" data-ed-turn="15" title="Turn the mass 15° counter-clockwise on the lot">⟲</button>
        <input type="number" id="ed-angle" min="-180" max="180" step="1" value="${h(ang)}" aria-label="The angle the mass is turned by, in degrees, counter-clockwise" title="The angle the mass is turned on the lot, in degrees (counter-clockwise); the blocks turn with it">
        <span class="label">°</span>
        <button type="button" class="btn btn-small btn-quiet" data-ed-turn="-15" title="Turn the mass 15° clockwise on the lot">⟳</button>
        <label class="ed-acc" title="The property line, the setback envelope, the streets and the neighbours behind the plate"><input type="checkbox" id="ed-context"${editor.context ? " checked" : ""}> site context</label>
        <label class="ed-acc" title="${canSun ? "Shadows at the equinox, 10 am, noon and 2 pm daylight time: the mass as one box of its full height on flat ground. A first reading, not a shadow study." : "Shadows need the site's context, which gives north"}"><input type="checkbox" id="ed-shadows"${editor.shadows ? " checked" : ""}${canSun && editor.context ? "" : " disabled"}> shadows</label>
      </span>
      </div>
    </details>
    <details class="ed-group" data-group="options"${groups.options ? " open" : ""}>
      <summary><b>Options to compare</b> <span class="cont">· ${variantsHere().length ? `${variantsHere().length} kept` : "none kept: keep this plan, change the massing, keep another"}</span></summary>
      ${variantsHtml(L)}
    </details>
    <details class="ed-step ed-group"${editor.stepOpen ? " open" : ""}>
      <summary><b>Step back the upper floors</b> <span class="cont">· ${steps.length ? h(steps.map(stepWords).join("; ")) : "none: every floor is the full plate"}</span></summary>
      ${steps.length ? `<ul class="ed-step-list">${steps.map(s => `<li>${h(stepWords(s))} <button type="button" class="btn btn-small btn-quiet" data-step-del="${s.from_level}" title="Take this step-back away">Remove</button></li>`).join("")}</ul>` : ""}
      <div class="ed-step-row">
        <label class="field inline"><span class="label">From</span><select id="ed-step-from">${L.floors.filter(fl => fl.level > 0).map(fl => `<option value="${fl.level}"${Math.max(1, Math.round(L.floors.length * 2 / 3)) === fl.level ? " selected" : ""}>${h(floorName(fl.level))} up</option>`).join("")}</select></label>
        ${[["front", "Street side"], ["rear", "Lane side"], ["left", "Left"], ["right", "Right"]].map(([k, l]) => `<label class="field inline"><span class="label">${l} (m)</span><input type="number" id="ed-step-${k}" min="0" step="0.5" value="0" aria-label="Step back on the ${l.toLowerCase()}, metres"></label>`).join("")}
        <button type="button" class="btn btn-small" id="ed-step-apply">${steps.length ? "Add or change a step" : "Step back"}</button>
        ${steps.length > 1 ? `<button type="button" class="btn btn-small btn-quiet" id="ed-step-clear">Remove them all</button>` : ""}
        <span class="help">The floors from there up lose a strip along each side named: a cut-out, so it comes off the floor area and the FSR. The homes on that side stay, shallower and as much wider as their area needs; the ones that no longer fit go back to the program. Left and right are as the plate is drawn before any turn.</span>
      </div>
    </details>
    <div class="ed-main">
      ${programHtml(L, tr, zs, B)}
      <div class="ed-stage">
        <div class="ed-msg" id="ed-msg" role="status" data-tone="${h((editor.msg || {}).tone || "info")}"${editor.msg ? "" : " hidden"}>${h((editor.msg || {}).text || "")}</div>
        <div class="ed-selbar" id="ed-selbar">${selBarHtml(L, zs)}</div>
        <svg class="ed-canvas" viewBox="0 0 ${frame.W.toFixed(1)} ${frame.H.toFixed(1)}" width="${width}" height="${(frame.H * width / frame.W).toFixed(0)}" role="application" tabindex="-1" aria-label="Block editor, ${h(L.floors[editor.level].name)}${turn ? ", north up" : ""}. Tab to a block; the arrows move it, Delete removes it, Ctrl+Z undoes">
          <rect x="0" y="0" width="100%" height="100%" fill="${V.ctx && site && site.osm ? HALF.parcel : "#ffffff"}"/>
          ${frame.open}${U(`
          <defs><pattern id="ed-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#ffffff"/><line x1="0" y1="0" x2="0" y2="6" stroke="#aab4c0" stroke-width="1.4"/></pattern></defs>
          ${V.ctx ? contextSvg(editor.massing, V, sun) : ""}`)}
          <g class="ed-mass-turn" transform="rotate(${(-ang).toFixed(2)} ${(px0 + pw / 2).toFixed(1)} ${(py0 + pd / 2).toFixed(1)})">${UM(`
          <rect x="${px0.toFixed(1)}" y="${py0.toFixed(1)}" width="${pw.toFixed(1)}" height="${pd.toFixed(1)}" fill="#fbfbfa" stroke="#1f2933" stroke-width="1.2"/>
          ${grid}${bandLines}${ticks}
          ${svgZones}
          <g pointer-events="none">${columns}</g>
          <rect class="ed-plate-handle ed-plate-w" x="${(px0 + pw + 3).toFixed(1)}" y="${(py0 + pd / 2 - 11).toFixed(1)}" width="8" height="22" rx="2" fill="#1f2933"><title>Drag to widen or narrow the plate</title></rect>
          <rect class="ed-plate-handle ed-plate-d" x="${(px0 + pw / 2 - 11).toFixed(1)}" y="${(py0 - 11).toFixed(1)}" width="22" height="8" rx="2" fill="#1f2933"><title>Drag to deepen or shallow the plate</title></rect>
          <g id="ed-ghost" pointer-events="none"></g>`)}</g></g>
          <text x="${(frame.W / 2).toFixed(1)}" y="${(frame.H - 6).toFixed(1)}" font-size="11" text-anchor="middle" fill="#5f6672" paint-order="stroke" stroke="#ffffff" stroke-width="3">${site && site.osm && site.osm.bearing != null ? "project north up" : "street at the bottom"} · plate ${h(p.width_m)} × ${h(p.depth_m)} m · walls on the ${h(r2(m))} m module of a ${h(editor.bay)} m bay${V.ctx ? " · property line dash-dot, setbacks red" : ""}</text>
          ${site && site.osm && site.osm.bearing != null ? northArrow(frame.W - 24, 26, site.osm.bearing - turn, 10) : ""}
        </svg>
        <div class="ed-status">
          ${floorChecks.length ? `<ul class="finding-list">${floorChecks.map(g => `<li>${pill("fail")}<span>${h(g.note)}</span></li>`).join("")}</ul>` : `<span class="help">Nothing broken on ${h(floorWords(editor.level))}.${problems ? ` ${problems} on other floors (marked ! above).` : ""}</span>`}
          ${overs.length ? `<span class="help ed-over">${pill("conditional")} <b>Over ${overs.length === 1 ? "a limit" : "two limits"}:</b> ${h(overs.join("; "))}. Nothing stops you; the memo will say so and staff will test the scheme against it. A smaller plate or a level fewer brings it back.</span>` : ""}
          ${L.proportions && L.proportions.status !== "pass" ? `<span class="help">${pill("conditional")} ${h(L.proportions.note)}</span>` : ""}
          ${L.daylight && L.daylight.status !== "pass" ? `<span class="help">${pill("conditional")} ${h(L.daylight.note)}</span>` : ""}
          ${past ? `<span class="help warn-text">${h(past)} <button type="button" class="btn btn-small" id="ed-fit-turn" title="Shrink the plate, keeping its proportions, until the turned mass stands inside the setback envelope">Fit the plate to the turn</button></span>` : ""}
          ${egF ? `<span class="help">${pill(egF.status)} Exits on this floor: ${h(egressLine(egF))}${egF.notes && egF.notes.length ? ` <span class="cont">· ${h(egF.notes[0])}</span>` : ""}</span>` : ""}
          <details class="ed-more"><summary>Separation, parkade and adjacency</summary>
          ${nbGap != null || lotGap != null ? `<span class="help">Separation: ${nbGap != null ? `${h(nbGap.toFixed(1))} m to the nearest neighbouring building` : ""}${nbGap != null && lotGap != null ? "; " : ""}${lotGap != null ? `${h(lotGap.toFixed(1))} m to the nearest lot line` : ""}${sun ? `. Longest shadow at the equinox: ${h(Math.round(Math.max(...sun.map(x => x.len))))} m at 10 am` : ""}.</span>` : ""}
          ${pk ? `<span class="help">${h(pk)}</span>` : ""}
          <span class="help">${h((L.adjacencies || []).filter(c => c.status === "pass").length)} adjacency rules hold, ${h((L.adjacencies || []).filter(c => c.status === "conditional").length)} conditional.</span>
          </details>
        </div>
      </div>
    </div>
    <div class="form-actions">
      <button type="button" class="btn btn-primary btn-small" id="ed-apply-run" title="Write the plan into the option and run the rules on it in one step: the memo, the drawings and the 3D view follow, and the editor stays open on this floor">${problems ? `Apply with ${problems} problem${problems === 1 ? "" : "s"} and run the rules` : "Apply and run the rules"}</button>
      <button type="button" class="btn btn-small" id="ed-apply"${editor.dirty || !editor.applied ? "" : " disabled"}>${problems ? `Apply with ${problems} problem${problems === 1 ? "" : "s"}` : "Apply to the option"}</button>
      <button type="button" class="btn btn-small btn-quiet" id="ed-dxf" title="Download every floor's blocks as a DXF drawing (metres, a layer per block kind) to open in AutoCAD, Rhino or Revit">Export DXF</button>
      <button type="button" class="btn btn-small btn-quiet" id="ed-mirror" title="Flip this floor's blocks left to right about the middle of the plate; the cores stay, as they are the same on every floor">Mirror this floor</button>
      <button type="button" class="btn btn-small btn-quiet" id="ed-repeat" title="Copy this floor's blocks onto every floor above it"${editor.level >= L.floors.length - 1 ? " disabled" : ""}>Repeat this floor above</button>
      <button type="button" class="btn btn-small btn-quiet" id="ed-blank" title="Take every block off every floor, keeping the cores and the corridors; Undo brings them back">Clear the plates</button>
      ${editor.applied ? `<button type="button" class="btn btn-small btn-quiet" id="ed-reset" title="Take the hand placement out of the option">Take it out of the option</button>` : ""}
      <span class="help">${editor.applied && !editor.dirty ? "Applied: Run the rules reproduces this placement; Save option as… keeps it." : (problems ? "The memo will list the problems as open items for the architect until they are fixed." : "Nothing is in the option until you apply.")}</span>
    </div>`;
  if (typed.label || typed.area || typed.open) {
    $(".ed-newprog", box).open = true; $("#ed-prog-label", box).value = typed.label; $("#ed-prog-area", box).value = typed.area;
    if (typed.focus === "ed-prog-label" || typed.focus === "ed-prog-area") $(`#${typed.focus}`, box).focus({ preventScroll: true });
  }
  wireEditor(box, { L, p, B, zs, scale, width, H, V, maxW, maxD, U: UM, rot: turn - ang });
  // the keyboard stays on the plan through a redraw: on the selected block, else on the plan itself, so Ctrl+Z and Tab
  // still work (20 Nov 2026: after Delete the redraw left the focus on the page's body and Ctrl+Z did nothing)
  if (hadFocus || editor.keepFocus) {
    editor.keepFocus = false;
    const g = editor.sel != null ? $(`.ed-zone[data-i="${editor.sel}"]`, box) : null;
    (g || $(".ed-canvas", box)).focus({ preventScroll: true });
  }
}

/* ---------------------------------------------------------------- new blocks and where they land */

/* A block of this kind sized for the program and the grid: a unit as deep as the strip and as many modules wide
   as its gross area needs; another use the strip deep and wide enough for what is left of it to place; a
   corridor the plate's width; a core the plate deep and wide enough for two stairs. Pure. */
function newBlock(kind, label, L, p, B) {
  const tr = programTracker(L, editor.zones);
  const row = tr.rows.find(r => kind === "other" ? (r.key === "other" && r.label === label) : r.key === kind);
  let w, d;
  if (kind === "corridor") { w = p.width_m; d = Math.min(CORR, p.depth_m); }
  else if (kind === "core") { w = ceilM(CORE_MIN); d = p.depth_m; }
  else {
    d = B.strip || Math.min(8, p.depth_m);
    const area = row ? (row.unit ? row.each : (row.left > 1 ? row.left : row.need)) : null;
    w = row && row.unit ? unitW(row.each, row.min, d, row.minW) : (area ? ceilM(area / d) : ceilM(6));
  }
  const z = { block: kind, x: p.x, y: p.y, w: r2(Math.min(w, p.width_m)), d: r2(Math.min(d, p.depth_m)) };
  if (kind === "other") z.label = label || "Other";
  // what the block is sized from, so it can be sized again for a shallower strip on a stepped floor (not kept in the zone)
  Object.defineProperty(z, "_fit", { value: row && row.unit ? { each: row.each, min: row.min, minW: row.minW } : (kind === "corridor" || kind === "core" ? null : { area: z.w * z.d }), enumerable: false });
  return z;
}

/* A new block made for the full strip, sized again for a strip a step-back left shallower: a unit as wide as its
   area needs at that depth, another use keeping its area. */
function fitBand(z, d, B) {
  if (!z._fit || !(d > 0) || d > B.strip - 0.01 || Math.abs(z.d - d) < 0.01) return;
  z.d = r2(d);
  z.w = z._fit.each ? unitW(z._fit.each, z._fit.min, d, z._fit.minW) : ceilM(z._fit.area / d);
}

const clearOf = (z, others) => (x, y) => others.every(o => x + z.w <= o.x + 0.01 || o.x + o.w <= x + 0.01 || y + z.d <= o.y + 0.01 || o.y + o.d <= y + 0.01);

/* The x's on the module where a block of this width stands inside the plate, and flush against its right end. */
function moduleXs(z, p) {
  const m = mod(), xs = [];
  for (let k = 0; p.x + k * m + z.w <= p.x + p.width_m + 1e-6; k++) xs.push(r2(p.x + k * m));
  const flush = r2(p.x + p.width_m - z.w);
  if (flush >= p.x && !xs.some(x => Math.abs(x - flush) < 0.01)) xs.push(flush);
  return xs;
}

/* The first place on a floor where a block overlaps nothing but a corridor: the street strip first, then the
   lane strip, then anywhere in 0.5 m rows, always on the module; null when there is none. Pure. */
function freeSpot(zones, z, p, B) {
  if (z.block === "corridor") return [p.x, B.corr];
  const clear = clearOf(z, zones.filter(o => o !== z && o.block !== "corridor"));
  // the two strips first, the block sized for each where a step-back left it shallower
  if (z.block !== "core") for (const [y, d] of [[B.front, B.frontD], ...(B.rear != null ? [[B.rear, B.rearD]] : [])]) {
    fitBand(z, d, B);
    if (y + z.d > p.y + p.depth_m + 1e-6) continue;
    for (const x of moduleXs(z, p)) if (clear(x, y)) return [x, r2(y)];
  }
  const rows = z.block === "core" ? [p.y] : [];
  if (z.block !== "core") for (let y = p.y; y <= p.y + p.depth_m - z.d + 1e-6; y += 0.5) if (!rows.some(r => Math.abs(r - y) < 1e-6)) rows.push(r2(y));
  for (const y of rows) {
    if (y < p.y - 1e-6 || y + z.d > p.y + p.depth_m + 1e-6) continue;
    for (const x of moduleXs(z, p)) if (clear(x, y)) return [x, r2(y)];
  }
  return null;
}

/* Where a block dragged from the program lands under the pointer: in the strip the pointer is over, on the
   module, at the free place nearest the pointer (where there is none, under the pointer, and it shows red). */
function placeAt(z, pt, zs, p, B) {
  if (z.block === "corridor") { z.x = p.x; z.y = Math.min(B.corr, r2(p.y + p.depth_m - z.d)); return; }
  const lane = z.block !== "core" && B.rear != null && pt[1] > B.corr + CORR / 2;
  if (z.block !== "core") fitBand(z, lane ? B.rearD : B.frontD, B);
  const y = z.block === "core" ? p.y : (lane ? B.rear : B.front);
  const want = pt[0] - z.w / 2;
  const xs = moduleXs(z, p).sort((a, b) => Math.abs(a - want) - Math.abs(b - want));
  const clear = clearOf(z, zs.filter(o => o.block !== "corridor"));
  z.x = xs.find(x => clear(x, y)) ?? xs[0] ?? p.x;
  z.y = r2(Math.min(y, p.y + p.depth_m - z.d));
}

/* ---------------------------------------------------------------- the wiring */

function wireSel(box, ctx) {
  const { L, p, B, zs } = ctx;
  const sel = editor.sel != null ? zs[editor.sel] : null;
  if (!sel) return;
  $("#ed-del", box).addEventListener("click", () => removeSel(zs));
  const nm = $("#ed-name", box);
  if (nm) nm.addEventListener("change", () => { snapshot(); const v = nm.value.trim(); if (v) sel.name = v; else delete sel.name; commit(false); });
  // a typed size: kept inside the plate from the block's own corner
  for (const [id, k] of [["#ed-w", "w"], ["#ed-d", "d"]]) {
    const inp = $(id, box);
    if (inp) inp.addEventListener("change", () => {
      const v = Number(inp.value);
      if (!(v > 0)) { renderEditor(); return; }
      snapshot();
      sel[k] = r2(Math.max(0.5, Math.min(v, k === "w" ? p.x + p.width_m - sel.x : p.y + p.depth_m - sel.y)));
      commit(sel.block === "core");
    });
  }
  const dup = $("#ed-dup", box);
  if (dup) dup.addEventListener("click", () => duplicateSel(ctx));
  const kindSel = $("#ed-kind", box);
  if (kindSel) kindSel.addEventListener("change", e => {
    // the block becomes the chosen program where it stands; a unit takes that unit's width on the grid, its
    // left wall kept (pulled back inside the plate where the new width runs past it)
    const v = e.target.value, other = v.startsWith("other:");
    snapshot();
    sel.block = other ? "other" : v;
    if (other) sel.label = v.slice(6); else delete sel.label;
    if (!isUnit(sel.block)) delete sel.accessible;
    const prog = (L.program || []).find(b => b.key === sel.block);
    if (isUnit(sel.block) && prog && sel.d > 0) {
      sel.w = Math.min(p.width_m, unitW(prog.gross_m2_each, prog.min_gross_m2_each, sel.d, prog.min_width_m));
      sel.x = r2(Math.max(p.x, Math.min(sel.x, p.x + p.width_m - sel.w)));
    }
    commit(false);
    const hit = clashes(zs).has(editor.sel);
    say(`The block is now ${blockName(sel).toLowerCase()}, ${sel.w} × ${sel.d} m.${hit ? " At that width it overlaps its neighbour: move one of them, or pull an edge." : ""}`, hit ? "busy" : "info");
  });
  const mv = $("#ed-move", box);
  if (mv) mv.addEventListener("change", e => {
    const to = String(e.target.value); if (to === String(editor.level)) return;
    snapshot();
    zs.splice(editor.sel, 1);
    const target = (editor.zones[to] = editor.zones[to] || []);
    const spot = freeSpot(target, sel, p, B);   // the first free place on that floor, not on top of what is there
    if (spot) { sel.x = spot[0]; sel.y = spot[1]; }
    target.push(sel);
    editor.level = Number(to); editor.sel = target.length - 1;
    commit(false);
    say(spot ? `Moved to ${floorWords(Number(to))}, the first free place.` : `No room on ${floorWords(Number(to))} for a ${sel.w} × ${sel.d} m block: it sits where it was and overlaps; move or remove something.`, spot ? "info" : "busy");
  });
  const acc = $("#ed-acc", box);
  if (acc) acc.addEventListener("change", () => { snapshot(); if (acc.checked) sel.accessible = true; else delete sel.accessible; commit(false); });
}

/* Delete: the block goes, and the next one (or the plan) takes the selection and the keyboard, so Delete and Ctrl+Z
   go on working from the keys. */
/* The largest plate of the present proportions that, standing at the middle of the plate box and turned by `angle`
   about its own centre, keeps all four corners inside the setback envelope: [width on the module, depth on 0.5 m],
   or null where even a fifth of the plate does not fit. Pure. */
function fitTurned(p, envelope, angle, m) {
  const env = envelope.polygon, xs = env.map(q => q[0]), ys = env.map(q => q[1]);
  const bx = envelope.box || { x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), d: Math.max(...ys) - Math.min(...ys) };
  const mx = bx.x + bx.w / 2, my = bx.y + bx.d / 2;
  const t = angle * Math.PI / 180, c = Math.cos(t), s = Math.sin(t);
  const inPoly = ([x, y]) => { let inside = false; for (let i = 0, j = env.length - 1; i < env.length; j = i++) { const [x1, y1] = env[i], [x2, y2] = env[j]; if ((y1 > y) !== (y2 > y) && x < x1 + (y - y1) * (x2 - x1) / (y2 - y1)) inside = !inside; } return inside; };
  const fits = (w, d) => { const cx = mx, cy = my; return [[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]].every(([dx, dy]) => inPoly([cx + dx * c - dy * s, cy + dx * s + dy * c])); };
  let lo = 0.2, hi = 1;
  if (!fits(p.width_m * lo, p.depth_m * lo)) return null;
  for (let i = 0; i < 24; i++) { const mid = (lo + hi) / 2; if (fits(p.width_m * mid, p.depth_m * mid)) lo = mid; else hi = mid; }
  let w = Math.max(m, Math.floor(p.width_m * lo / m) * m), d = Math.max(3, Math.floor(p.depth_m * lo * 2) / 2);
  for (let i = 0; i < 40 && !fits(w, d) && w > m && d > 3; i++) { w -= m; d = Math.max(3, Math.floor(w * p.depth_m / p.width_m * 2) / 2); }
  return fits(w, d) ? [r2(w), r2(d)] : null;
}

/* The floors as a DXF drawing (R12, text): each floor's plate and blocks as closed polylines on a layer per block
   kind, its name over it, each block's name and area in it; metres, the plate's own frame with the street side down,
   the floors side by side from the ground up. Pure. */
function dxfOf(L, zones) {
  const p = L.plate, out = ["0", "SECTION", "2", "ENTITIES"], gap = Math.max(10, Math.round(p.width_m * 0.15));
  const layer = k => `FR-${String(k).toUpperCase().replace(/[^A-Z0-9]+/g, "_")}`;
  const n = v => (Math.round(v * 1000) / 1000).toString();
  const poly = (lay, pts) => { out.push("0", "POLYLINE", "8", lay, "66", "1", "70", "1"); for (const [x, y] of pts) out.push("0", "VERTEX", "8", lay, "10", n(x), "20", n(y), "30", "0"); out.push("0", "SEQEND", "8", lay); };
  const text = (lay, x, y, hgt, s) => out.push("0", "TEXT", "8", lay, "10", n(x), "20", n(y), "30", "0", "40", n(hgt), "1", String(s).replace(/[\r\n]+/g, " "));
  const rect = (x, y, w, d) => [[x, y], [x + w, y], [x + w, y + d], [x, y + d]];
  L.floors.forEach((fl, i) => {
    const ox = i * (p.width_m + gap) - p.x, oy = -p.y;
    poly("FR-PLATE", rect(p.x + ox, p.y + oy, p.width_m, p.depth_m));
    text("FR-TEXT", p.x + ox, p.y + oy + p.depth_m + 1.2, 1.2, `${fl.name || floorName(fl.level)} - ${p.width_m} x ${p.depth_m} m`);
    for (const z of zones[String(fl.level)] || []) {
      poly(layer(z.block), rect(z.x + ox, z.y + oy, z.w, z.d));
      if (z.w > 2.5 && z.d > 1.5) text("FR-TEXT", z.x + ox + 0.3, z.y + oy + z.d / 2 - 0.2, Math.min(0.6, z.d / 4), `${blockName(z)} ${Math.round(z.w * z.d)} m2`);
    }
  });
  out.push("0", "ENDSEC", "0", "EOF");
  return out.join("\r\n") + "\r\n";
}

/* Options kept in the editor to compare (for this site and option only): what each is, in figures. */
const variantKey = () => `${(state.site && state.site.id) || ""}|${(state.option && state.option.id) || ""}`;
const variantsHere = () => (editor.variants = editor.variants || []).filter(v => v.key === variantKey());

function summaryOf(L) {
  const c = L.capacity || {}, steps = editor.steps || [];
  return { storeys: L.floors.length, plate: `${L.plate.width_m} × ${L.plate.depth_m} m`, turn: editor.angle || 0, steps: steps.length,
    fsr: c.fsr, fsrLimit: c.fsr_limit, height: c.height_m, heightLimit: c.height_limit_m, placed: L.units_placed, total: L.units_total,
    problems: (L.geometry || []).length, deep: L.daylight ? L.daylight.deep_units + L.daylight.no_window_wall : 0 };
}

function variantsHtml(L) {
  const kept = variantsHere(), now = summaryOf(L);
  const cells = s => `<td>${s.storeys}</td><td>${h(s.plate)}${s.turn ? `, turned ${s.turn}°` : ""}${s.steps ? `, ${s.steps} step${s.steps === 1 ? "" : "s"}` : ""}</td>
    <td class="${s.fsrLimit != null && s.fsr > s.fsrLimit + 0.005 ? "warn-text" : ""}">${s.fsr != null ? Number(s.fsr).toFixed(2) : "–"}${s.fsrLimit != null ? ` of ${Number(s.fsrLimit).toFixed(2)}` : ""}</td>
    <td class="${s.heightLimit != null && s.height > s.heightLimit + 0.05 ? "warn-text" : ""}">${s.height != null ? `${s.height} m` : "–"}${s.heightLimit != null ? ` of ${s.heightLimit}` : ""}</td>
    <td>${s.placed} of ${s.total}</td><td>${s.problems || "none"}</td><td>${s.deep || "none"}</td>`;
  return `<div class="ed-variants">
      <button type="button" class="btn btn-small" id="ed-keep"${kept.length >= 6 ? " disabled" : ""} title="Keep this plan, with its plate, turn, steps and levels, as an option to compare with the next one you try">Keep as an option to compare</button>
      ${kept.length ? `<table class="plain ed-var-table"><thead><tr><th>Option</th><th>Storeys</th><th>Plate</th><th>FSR</th><th>Height</th><th>Homes placed</th><th>Problems</th><th title="Homes deeper than 10 m from their window wall, or with no outside wall">Homes short of daylight</th><th></th></tr></thead><tbody>
        ${kept.map((v, i) => `<tr><th>${h(v.name)}</th>${cells(v.sum)}<td><button type="button" class="btn btn-small btn-quiet" data-var-restore="${i}">Restore</button> <button type="button" class="btn btn-small btn-quiet" data-var-drop="${i}" aria-label="Drop option ${h(v.name)}">Drop</button></td></tr>`).join("")}
        <tr class="now"><th>Now</th>${cells(now)}<td></td></tr></tbody></table>` : ""}
    </div>`;
}

/* The step-back as cut-outs: on every floor from `from_level` up, a strip along each side the step names (marked
   `step`, so the tool can take its own strips away again), the corridor shortened to the plate that is left, and the
   blocks that stood in a strip taken off (they go back to the program). Returns how many were taken off. */
function rebuildSteps() {
  const L = editor.result || state.run.layout, p = L.plate;
  const hits = (a, b) => !(a.x + a.w <= b.x + 0.01 || b.x + b.w <= a.x + 0.01 || a.y + a.d <= b.y + 0.01 || b.y + b.d <= a.y + 0.01);
  let moved = 0;
  for (const fl of L.floors) {
    const k = String(fl.level);
    let zs = (editor.zones[k] || []).filter(z => !z.step);
    for (const z of zs) if (z.block === "corridor" && z.full) { z.x = z.full[0]; z.w = z.full[1]; delete z.full; }   // the corridor at its own length again
    for (const z of zs) if (z.pre) { [z.x, z.y, z.w, z.d] = z.pre; delete z.pre; }   // and a home a step-back made shallower, as it was
    const st = stepAt(fl.level);
    if (st.front || st.rear || st.left || st.right) {
      const f = st.front || 0, r = st.rear || 0, l = st.left || 0, rt = st.right || 0, W = p.width_m, D = p.depth_m;
      const strips = [f && { x: p.x, y: p.y, w: W, d: f }, r && { x: p.x, y: r2(p.y + D - r), w: W, d: r },
        l && { x: p.x, y: r2(p.y + f), w: l, d: r2(D - f - r) }, rt && { x: r2(p.x + W - rt), y: r2(p.y + f), w: rt, d: r2(D - f - r) }].filter(Boolean);
      for (const z of zs) if (z.block === "corridor" && z.w >= z.d && (l || rt)) {
        const a = Math.max(z.x, p.x + l), b = Math.min(z.x + z.w, p.x + W - rt);
        if (b - a > 1 && (a > z.x + 0.01 || b < z.x + z.w - 0.01)) { z.full = [z.x, z.w]; z.x = r2(a); z.w = r2(b - a); }
      }
      // The homes and rooms standing on a stepped face stay (25 Nov 2026: a 3 m step-back emptied the whole street side
      // of six floors): each is made shallower by the step and as much wider as it needs (a home by its type's area and
      // minimum width at the new depth, a room to keep its area), and they close up along the strip from its start,
      // past the cores; the ones the strip no longer holds go back to the program. `pre` keeps what each was.
      const cores = zs.filter(z => z.block === "core"), gone = new Set();
      const refit = (band, yOf, dOf) => {
        let cursor = p.x + l;
        for (const z of band.sort((a, b) => a.x - b.x)) {
          const y = yOf(z), d = dOf(z);
          if (d < 2.5) { gone.add(z); continue; }
          const pr = isUnit(z.block) ? (L.program || []).find(b => b.key === z.block) : null;
          const w = pr ? unitW(pr.gross_m2_each, pr.min_gross_m2_each, d, pr.min_width_m) : r2(z.w * z.d / d);
          let x = Math.max(z.x, cursor);
          for (let n = 0, hit; n < 8 && (hit = cores.find(c => !(x + w <= c.x + 0.01 || c.x + c.w <= x + 0.01 || y + d <= c.y + 0.01 || c.y + c.d <= y + 0.01))); n++) x = hit.x + hit.w;
          if (x + w > p.x + W - rt + 0.01) { gone.add(z); continue; }
          z.pre = [z.x, z.y, z.w, z.d];
          z.x = r2(x); z.y = r2(y); z.w = r2(w); z.d = r2(d);
          cursor = x + w;
        }
      };
      const loose = z => z.block !== "core" && z.block !== "corridor" && z.block !== "void";
      if (f) refit(zs.filter(z => loose(z) && Math.abs(z.y - p.y) < 0.03), z => z.y + f, z => z.d - f);
      if (r) refit(zs.filter(z => loose(z) && Math.abs(z.y + z.d - (p.y + D)) < 0.03), z => z.y, z => z.d - r);
      zs = zs.filter(z => !gone.has(z));
      moved += gone.size;
      const keep = zs.filter(z => z.block === "core" || z.block === "corridor" || !strips.some(s => hits(z, s)));
      moved += zs.length - keep.length;
      zs = keep.concat(strips.map(s => ({ block: "void", step: true, name: "step-back", x: s.x, y: s.y, w: r2(s.w), d: r2(s.d) })));
    }
    editor.zones[k] = zs;
  }
  return moved;
}

/* A copy of the selected block: beside it where that is free, else in the first free place on the floor; nothing
   where there is none. */
function duplicateSel(ctx) {
  const { p, B, zs } = ctx, sel = editor.sel != null ? zs[editor.sel] : null;
  if (!sel) return;
  const z = JSON.parse(JSON.stringify(sel));
  const clear = clearOf(z, zs.filter(o => o.block !== "corridor"));
  const beside = [[r2(sel.x + sel.w), sel.y], [r2(sel.x - sel.w), sel.y]].find(([x, y]) => x >= p.x - 0.01 && x + z.w <= p.x + p.width_m + 0.01 && (z.block === "corridor" || clear(x, y)));
  const spot = beside || freeSpot(zs, z, p, B);
  if (!spot) { say(`No free room on ${floorWords(editor.level)} for another ${blockName(sel).toLowerCase()} of ${sel.w} × ${sel.d} m, so nothing was added.`, "busy"); return; }
  z.x = spot[0]; z.y = spot[1];
  snapshot();
  zs.push(z); editor.sel = zs.length - 1;
  commit(z.block === "core");
}

function removeSel(zs) {
  if (editor.sel == null || !zs[editor.sel]) return;
  snapshot();
  const i = editor.sel, gone = zs[i], core = gone.block === "core";
  zs.splice(i, 1);
  editor.sel = zs.length ? Math.min(i, zs.length - 1) : null;
  editor.keepFocus = true;
  commit(core);
  say(`${blockName(gone)} removed${editor.sel != null ? `; ${blockName(zs[editor.sel]).toLowerCase()} is selected` : ""}. Ctrl+Z brings it back.`, "info");
}

function wireEditor(box, ctx) {
  const { L, p, B, zs, scale, width, H, V, maxW, maxD, U } = ctx;
  const svg = $(".ed-canvas", box);
  // the pointer in the canvas's own coordinates, inside the group that turns the plan north up
  const turned = $(".ed-mass-turn", svg);
  const loc = e => { const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(turned.getScreenCTM().inverse()); return [pt.x, pt.y]; };
  const m = mod();

  // the plate's own dimensions: typed, or pulled by the two dark handles on its right and far edges; the width goes
  // to the module, the depth to 0.5 m, neither past what the setbacks leave; the program is laid out again on it
  const fitW = w => r2(Math.max(Math.min(6, maxW), Math.min(maxW, Math.round(w / m) * m > maxW ? maxW : Math.round(w / m) * m)));
  const fitD = d => r2(Math.max(Math.min(6, maxD), Math.min(maxD, Math.round(d * 2) / 2)));
  const plateFromInputs = () => {
    const w = Number($("#ed-plate-w", box).value), d = Number($("#ed-plate-d", box).value);
    if (!(w > 0) || !(d > 0)) { toast("The plate needs a width and a depth in metres.", true); renderEditor(); return; }
    setPlate(Math.max(Math.min(6, maxW), Math.min(maxW, r2(w))), Math.max(Math.min(6, maxD), Math.min(maxD, r2(d))));
  };
  $("#ed-plate-w", box).addEventListener("change", plateFromInputs);
  $("#ed-plate-d", box).addEventListener("change", plateFromInputs);
  const auto = $("#ed-plate-auto", box); if (auto) auto.addEventListener("click", () => setPlate(null));
  // turning the mass on the lot: the blocks stay where they are on the plate, the plate turns about its centre
  const setAngle = a => {
    if (!isFinite(a)) return;
    a = Math.round((((a + 180) % 360) + 360) % 360 - 180); if (a === -180) a = 180;
    if (a === (editor.angle || 0)) { renderEditor(); return; }
    snapshot();
    editor.angle = a; editor.dirty = true;
    renderEditor(); scheduleCheck();
    say(a ? `The mass is turned ${a}° on the lot${editor.context ? "" : " (turn the site context on to see it against the property line)"}; its blocks turn with it. The engine says if a corner passes the setback envelope. Apply writes the angle into the option.` : "The mass is square to the lot again.", "info");
  };
  $("#ed-angle", box).addEventListener("change", e => setAngle(Number(e.target.value)));
  $$("[data-ed-turn]", box).forEach(b => b.addEventListener("click", () => setAngle((editor.angle || 0) + Number(b.dataset.edTurn))));
  $("#ed-shadows", box).addEventListener("change", e => {
    editor.shadows = e.target.checked; renderEditor();
    if (editor.shadows) say("Shadows at the equinox, 10 am, noon and 2 pm daylight time, from the mass as one box of its full height on flat ground: a first reading for placing and turning the mass, not the shadow study the City asks for.", "info");
  });
  $("#ed-context", box).addEventListener("change", e => {
    editor.context = e.target.checked;
    try { localStorage.setItem("ffm.ed.context", editor.context ? "1" : "0"); } catch (err) { /* a private window: the choice lasts the session */ }
    renderEditor();
  });
  $$("[data-ed-level]", box).forEach(b => b.addEventListener("click", () => { editor.level = Number(b.dataset.edLevel); editor.sel = null; renderEditor(); }));

  // the grid
  const setBay = v => {
    if (!(v >= 3 && v <= 12)) { toast("A bay is between 3 and 12 m, wall to wall.", true); renderEditor(); return; }
    editor.bay = r2(v); renderEditor();
    say(`The grid is a ${editor.bay} m bay, the walls on its ${r2(mod())} m module. The blocks on the plate stay where they are and take the grid as they are moved; Suggest a grid plan lays the program out on it.`, "info");
  };
  $$("[data-ed-bay]", box).forEach(b => b.addEventListener("click", () => setBay(Number(b.dataset.edBay))));
  $("#ed-bay-other", box).addEventListener("change", e => { if (e.target.value !== "") setBay(Number(e.target.value)); });
  $("#ed-divide", box).addEventListener("change", e => { editor.divide = Number(e.target.value) || 2; setBay(editor.bay); });
  $("#ed-suggest", box).addEventListener("click", () => suggestPlan(false));
  const addL = $("#ed-addlevel", box); if (addL) addL.addEventListener("click", addLevel);
  const delL = $("#ed-dellevel", box); if (delL) delL.addEventListener("click", removeLevel);
  $("#ed-undo", box).addEventListener("click", undo);

  // a block added without a drag lands in the first free place on this floor
  const addBlock = (kind, label) => {
    const z = newBlock(kind, label, L, p, B);
    const spot = freeSpot(zs, z, p, B);
    // no free place: nothing is added (before 23 Nov 2026 the block was dropped on the front-left corner, on top of
    // what stood there, and a cut-out dropped that way came off the floor area while the home under it still counted)
    if (!spot) {
      say(`No free room on ${floorWords(editor.level)} for a ${z.w} × ${z.d} m ${blockName(z).toLowerCase()}, so nothing was added. Clear a space or try another floor; or drag it from the program onto the plate to stand it exactly where you want it, and resize it there.`, "busy");
      return;
    }
    z.x = spot[0]; z.y = spot[1];
    snapshot();
    zs.push(z); editor.sel = zs.length - 1;
    commit(kind === "core");
  };

  // the pointer in plate metres, or null off the canvas
  const toPlate = e => {
    const [sx, sy] = loc(e);
    if (sx < 0 || sy < 0 || sx > width || sy > H) return null;
    return [V.x0 + (sx - M) / scale, V.y1 - (sy - M) / scale];
  };
  const ghost = $("#ed-ghost", box);

  // the program rows: drag one onto the plate, or click (Enter) to add it in the first free place
  $$(".ed-prog", box).forEach(row => {
    const kind = row.dataset.kind, label = row.dataset.label;
    let pal = null;
    row.addEventListener("pointerdown", e => {
      if (e.button) return;
      pal = { x0: e.clientX, y0: e.clientY, started: false, over: false, z: null };
      row.setPointerCapture(e.pointerId); e.preventDefault();
    });
    row.addEventListener("pointermove", e => {
      if (!pal) return;
      if (!pal.started) {
        if (Math.hypot(e.clientX - pal.x0, e.clientY - pal.y0) < 5) return;
        pal.started = true; editor.dragging = true;
        pal.z = newBlock(kind, label, L, p, B);
        row.classList.add("dragging"); box.classList.add("ed-dragging");
      }
      const pt = toPlate(e);
      pal.over = !!pt;
      if (!pt) { ghost.innerHTML = ""; return; }
      placeAt(pal.z, pt, zs, p, B);
      const r = rectOf(pal.z, V), hit = !clearOf(pal.z, zs.filter(o => o.block !== "corridor" && pal.z.block !== "corridor"))(pal.z.x, pal.z.y);
      ghost.innerHTML = U(`<rect x="${r.x.toFixed(1)}" y="${r.y.toFixed(1)}" width="${r.w.toFixed(1)}" height="${r.d.toFixed(1)}" fill="${ZONE_TONE[kind] || "#eee"}" fill-opacity="0.75" stroke="${hit ? "#c81e1e" : "#245f9c"}" stroke-width="1.6" stroke-dasharray="5 3"/>
        <text x="${(r.x + r.w / 2).toFixed(1)}" y="${(r.y + r.d / 2 + 3.5).toFixed(1)}" font-size="9.5" text-anchor="middle" fill="#1f2933">${h(zoneShort(pal.z))} · ${pal.z.w} m</text>`);
    });
    const done = e => {
      if (!pal) return;
      const q = pal; pal = null;
      row.classList.remove("dragging"); box.classList.remove("ed-dragging"); editor.dragging = false;
      if (!q.started) { if (e.type === "pointerup") addBlock(kind, label); return; }
      ghost.innerHTML = "";
      if (q.over && e.type === "pointerup") { snapshot(); zs.push(q.z); editor.sel = zs.length - 1; commit(kind === "core"); }
      else if (editor.pendingRender) renderEditor();
    };
    row.addEventListener("pointerup", done);
    row.addEventListener("pointercancel", done);
    row.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); addBlock(kind, label); } });
  });

  $("#ed-prog-add", box).addEventListener("click", () => {
    const label = ($("#ed-prog-label", box).value || "").trim(), area = Number($("#ed-prog-area", box).value);
    if (!label || !(area > 0)) { toast("A program needs a name and an area in m².", true); return; }
    if (!state.option) return;
    state.option.layout = Object.assign({}, state.option.layout || {});
    const list = (state.option.layout.extra_programs = (state.option.layout.extra_programs || []).filter(x => x.label.toLowerCase() !== label.toLowerCase()));
    list.push({ label, area_m2: area });
    state.optionDirty = true; $("#option-dirty").hidden = false;
    editor.dirty = true;
    $("#ed-prog-label", box).value = ""; $("#ed-prog-area", box).value = "";
    say(`${label}, ${fmtNum(area)} m², is in the program (option.layout.extra_programs); it joins the list once the engine has counted it. Drag it onto the plate from there.`, "ok");
    scheduleCheck();
  });

  $("#ed-blank", box).addEventListener("click", () => {
    snapshot();
    for (const k of Object.keys(editor.zones)) editor.zones[k] = editor.zones[k].filter(z => z.block === "core" || z.block === "corridor");
    editor.sel = null;
    commit(false);
    say("Every block is off the plates; the cores and the corridors stay. Drag the program onto the plate, floor by floor; Undo brings the blocks back.", "info");
  });
  $("#ed-repeat", box).addEventListener("click", () => {
    snapshot();
    const above = L.floors.filter(fl => fl.level > editor.level);
    for (const fl of above) editor.zones[String(fl.level)] = JSON.parse(JSON.stringify(zs));
    commit(false);
    say(`${floorName(editor.level)} is repeated on the ${above.length} floor${above.length === 1 ? "" : "s"} above. The program beside the plate says what that leaves to place, or puts over.`, "info");
  });
  // options kept to compare: this plan as it stands, with its plate, turn, steps and levels
  const keepBtn = $("#ed-keep", box);
  if (keepBtn) keepBtn.addEventListener("click", () => {
    const mine = variantsHere(), name = "ABCDEF"[mine.length] || String(mine.length + 1);
    editor.variants.push({ key: variantKey(), name, sum: summaryOf(L), state: JSON.stringify({ z: editor.zones, a: editor.added || 0, p: editor.plate || null, t: editor.angle || 0, s: editor.steps || null, n: editor.anchor || null }) });
    renderEditor();
    say(`Kept as option ${name}. Change the plate, the turn, the steps or the plan and keep another; the table compares them, and Restore brings one back onto the plate.`, "ok");
  });
  $$("[data-var-restore]", box).forEach(b => b.addEventListener("click", () => {
    const v = variantsHere()[Number(b.dataset.varRestore)]; if (!v) return;
    snapshot();
    const was = JSON.parse(v.state);
    editor.zones = was.z; editor.added = was.a; editor.plate = was.p; editor.angle = was.t; editor.steps = was.s; editor.anchor = was.n; editor.sel = null; editor.dirty = true;
    if (!editor.zones[String(editor.level)]) editor.level = 0;
    renderEditor(); scheduleCheck();
    say(`Option ${v.name} is back on the plate; Undo returns to what was there. Apply makes it the option's.`, "info");
  }));
  $$("[data-var-drop]", box).forEach(b => b.addEventListener("click", () => {
    const v = variantsHere()[Number(b.dataset.varDrop)];
    editor.variants = editor.variants.filter(x => x !== v); renderEditor();
  }));
  const fitBtn = $("#ed-fit-turn", box);
  if (fitBtn) fitBtn.addEventListener("click", () => {
    const env = editor.massing && editor.massing.envelope;
    const fit = env && env.polygon && fitTurned(p, env, editor.angle || 0, m);
    if (!fit) { say(`No plate of these proportions fits inside the setback envelope turned ${editor.angle}°: turn it less, or change the plate's proportions by hand.`, "busy"); return; }
    // a plate against a corner of the envelope puts a corner out at any turn: it stands at the middle to turn
    setPlate(fit[0], fit[1], "centre");
  });
  const stepBox = $(".ed-step", box);
  stepBox.addEventListener("toggle", () => { editor.stepOpen = stepBox.open; });
  const setStep = spec => {
    snapshot();
    // one step-back a level: a new one at a level that has one replaces it; null takes them all away
    editor.steps = spec ? (editor.steps || []).filter(s => s.from_level !== spec.from_level).concat([spec]).sort((a, b) => a.from_level - b.from_level) : null;
    editor.stepOpen = true;
    const moved = rebuildSteps();
    editor.sel = null;
    commit(false);
    say(spec ? `${floorName(spec.from_level)} and up step back: ${["front", "rear", "left", "right"].filter(k => spec[k] > 0).map(k => `${k} ${spec[k]} m`).join(", ")}. The homes on a stepped side are shallower and wider now.${moved ? ` ${moved} block${moved === 1 ? "" : "s"} no longer fit and went back to the program.` : ""} The 3D view, the section and the elevations show the steps after Apply and Run the rules.` : "The step-backs are removed: every floor is the full plate again.", moved ? "busy" : "info");
  };
  $("#ed-step-apply", box).addEventListener("click", () => {
    const num = k => Math.max(0, Number($(`#ed-step-${k}`, box).value) || 0);
    const spec = { from_level: Number($("#ed-step-from", box).value) || 1, front: num("front"), rear: num("rear"), left: num("left"), right: num("right") };
    if (!(spec.front || spec.rear || spec.left || spec.right)) { toast("Give the step-back a depth on at least one side, in metres.", true); return; }
    if (spec.left + spec.right > p.width_m - 6 || spec.front + spec.rear > p.depth_m - 6) { toast("That step-back leaves less than 6 m of plate.", true); return; }
    setStep(spec);
  });
  const stepClear = $("#ed-step-clear", box); if (stepClear) stepClear.addEventListener("click", () => setStep(null));
  $$("[data-step-del]", box).forEach(b => b.addEventListener("click", () => {
    snapshot();
    editor.steps = (editor.steps || []).filter(s => s.from_level !== Number(b.dataset.stepDel)); if (!editor.steps.length) editor.steps = null;
    rebuildSteps(); editor.sel = null; commit(false);
    say("That step-back is removed; the blocks it took off stay in the program to place again.", "info");
  }));
  $("#ed-apply-run", box).addEventListener("click", () => { applyEditor(); runRules(); });
  $$("[data-ed-zoom]", box).forEach(b => b.addEventListener("click", () => { editor.zoom = b.dataset.edZoom; if (editor.zoom === "site" && !editor.context) editor.context = true; renderEditor(); }));
  $$("details.ed-group[data-group]", box).forEach(d => d.addEventListener("toggle", () => { (editor.groups = editor.groups || {})[d.dataset.group] = d.open; }));
  $("#ed-mirror", box).addEventListener("click", () => {
    snapshot();
    for (const z of zs) if (z.block !== "core") z.x = r2(p.x + (p.x + p.width_m - (z.x + z.w)));
    editor.sel = null;
    commit(false);
    const hit = clashes(zs).size;
    say(`${floorName(editor.level)} is mirrored left to right; the cores stay where they are on every floor.${hit ? ` ${hit} block${hit === 1 ? "" : "s"} now overlap a core or each other: move them.` : ""}`, hit ? "busy" : "info");
  });
  $("#ed-apply", box).addEventListener("click", applyEditor);
  $("#ed-dxf", box).addEventListener("click", () => {
    const name = `${(state.site && state.site.id) || "site"}-${(state.option && state.option.id) || "option"}-plans.dxf`;
    const blob = new Blob([dxfOf(L, editor.zones)], { type: "application/dxf" }), a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    say(`${name}: every floor's blocks as closed polylines, a layer per block kind, in metres, the floors side by side with the street side down. It opens in AutoCAD, Rhino or Revit (Link CAD).`, "ok");
  });
  const reset = $("#ed-reset", box);
  if (reset) reset.addEventListener("click", () => {
    if (state.option && state.option.layout) { delete state.option.layout.zones; if (!Object.keys(state.option.layout).length) delete state.option.layout; }
    editor.applied = false;
    state.optionDirty = true; $("#option-dirty").hidden = false;
    refreshSummary("option");
    renderEditor();
    say("The hand placement is out of the option: Run the rules lays the program out by itself again. The blocks stay here until the editor is closed.", "info");
  });
  wireSel(box, ctx);

  /* moving and resizing on the plate. A press selects and starts the drag in one gesture. A wall goes to the
     nearest other block's wall within 0.4 m, else to the module; the near and far edges go to the strips' edges
     within 1.2 m, else to 0.5 m; the plate's edges are the limit. */
  const gx = v => p.x + Math.round((v - p.x) / m) * m;
  const xEdges = i => { const s = [p.x, p.x + p.width_m]; zs.forEach((o, j) => { if (j !== i) s.push(o.x, o.x + o.w); }); return s; };
  const yEdges = i => { const s = [p.y, p.y + p.depth_m, B.corr, ...(B.rear != null ? [B.rear] : [])]; zs.forEach((o, j) => { if (j !== i) s.push(o.y, o.y + o.d); }); return s; };
  const near = (v, stops, tol) => { let best = null; for (const s of stops) if (Math.abs(s - v) <= tol && (best == null || Math.abs(s - v) < Math.abs(best - v))) best = s; return best; };
  const wallX = (v, i) => near(v, xEdges(i), 0.4) ?? gx(v);
  const edgeY = (v, i) => near(v, yEdges(i), 1.2) ?? Math.round(v * 2) / 2;
  // the ring and handles over the selected block, drawn again where it is
  const overlay = i => {
    const old = $(".ed-selover", svg); if (old) old.remove();
    if (i != null && zs[i]) ghost.insertAdjacentHTML("beforebegin", U(selOverlay(i, zs[i], V)));
  };
  // a block is selected by a press, by Tab landing on it, or by Enter; the drawing order (and so the tab order) stays
  const select = (i, focus = true) => {
    editor.sel = i;
    $$(".ed-zone", svg).forEach(g => g.classList.toggle("sel", Number(g.dataset.i) === i));
    overlay(i);
    if (i != null && focus) { const g = $(`.ed-zone[data-i="${i}"]`, svg); if (g && document.activeElement !== g) g.focus({ preventScroll: true }); }
    $("#ed-selbar", box).innerHTML = selBarHtml(L, zs);
    wireSel(box, ctx);
  };
  const redraw = i => {
    const bad = clashes(zs);
    $$(".ed-zone", svg).forEach(g => {
      const j = Number(g.dataset.i);
      g.classList.toggle("clash", bad.has(j));
      if (j === i) g.innerHTML = U(zoneInner(zs[j], rectOf(zs[j], V)));
    });
    if (i === editor.sel) overlay(i);
    $("#ed-selbar", box).innerHTML = selBarHtml(L, zs);
  };
  $$(".ed-zone", svg).forEach(g => g.addEventListener("focus", () => { const i = Number(g.dataset.i); if (editor.sel !== i) select(i, false); }));
  let drag = null;
  svg.addEventListener("pointerdown", e => {
    if (e.button) return;
    if (e.target.classList.contains("ed-plate-handle")) {
      drag = { plate: e.target.classList.contains("ed-plate-w") ? "w" : "d", x0: e.clientX, y0: e.clientY, p0: loc(e), w: p.width_m, d: p.depth_m, moved: false };
      svg.setPointerCapture(e.pointerId); e.preventDefault(); return;
    }
    const g = e.target.closest(".ed-zone, .ed-selover");   // a block, or the selected one's handles over it
    if (!g) { if (editor.sel != null) select(null); return; }
    const i = Number(g.dataset.i);
    const mode = e.target.classList.contains("ed-handle-w") ? "w" : e.target.classList.contains("ed-handle-l") ? "l" : e.target.classList.contains("ed-handle-d") ? "d" : "move";
    if (editor.sel !== i) select(i);
    drag = { i, mode, x0: e.clientX, y0: e.clientY, p0: loc(e), z0: { ...zs[i] }, moved: false };
    svg.setPointerCapture(e.pointerId); e.preventDefault();
  });
  svg.addEventListener("pointermove", e => {
    if (!drag) return;
    const at = loc(e);
    if (drag.plate) {
      // the plate as it would be, dashed, from its front-left corner, with its size and floor area
      drag.moved = true; editor.dragging = true;
      if (drag.plate === "w") drag.w = fitW(p.width_m + (at[0] - drag.p0[0]) / scale);
      else drag.d = fitD(p.depth_m - (at[1] - drag.p0[1]) / scale);
      const x = V.X(p.x), y = V.Y(p.y + drag.d);
      ghost.innerHTML = U(`<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${(drag.w * scale).toFixed(1)}" height="${(drag.d * scale).toFixed(1)}" fill="#245f9c" fill-opacity="0.08" stroke="#245f9c" stroke-width="1.6" stroke-dasharray="6 3"/>
        <text x="${(x + drag.w * scale / 2).toFixed(1)}" y="${(y + drag.d * scale / 2).toFixed(1)}" font-size="12" font-weight="600" text-anchor="middle" fill="#245f9c" stroke="#ffffff" stroke-width="3" paint-order="stroke">${drag.w} × ${drag.d} m · ${fmtNum(Math.round(drag.w * drag.d))} m² a floor</text>`);
      return;
    }
    if (!drag.moved) {
      if (Math.hypot(e.clientX - drag.x0, e.clientY - drag.y0) < 3) return;
      drag.moved = true; editor.dragging = true; snapshot(); svg.classList.add("dragging");
    }
    const dx = (at[0] - drag.p0[0]) / scale, dy = -(at[1] - drag.p0[1]) / scale;   // the canvas's down is toward the street
    const z = zs[drag.i], z0 = drag.z0, right = p.x + p.width_m, far = p.y + p.depth_m;
    if (drag.mode === "move") {
      // the left or the right wall, the near or the far edge, whichever finds another block's wall first
      const nx = z0.x + dx, ny = z0.y + dy;
      const lx = near(nx, xEdges(drag.i), 0.4), rx = near(nx + z.w, xEdges(drag.i), 0.4);
      const x = lx != null && (rx == null || Math.abs(lx - nx) <= Math.abs(rx - z.w - nx)) ? lx : (rx != null ? rx - z.w : gx(nx));
      const ly = near(ny, yEdges(drag.i), 1.2), fy = near(ny + z.d, yEdges(drag.i), 1.2);
      const y = ly != null && (fy == null || Math.abs(ly - ny) <= Math.abs(fy - z.d - ny)) ? ly : (fy != null ? fy - z.d : Math.round(ny * 2) / 2);
      z.x = r2(Math.max(p.x, Math.min(right - z.w, x)));
      z.y = r2(Math.max(p.y, Math.min(far - z.d, y)));
    } else if (drag.mode === "w") {
      z.w = r2(Math.max(Math.min(m, 1), Math.min(right, wallX(z0.x + z0.w + dx, drag.i)) - z.x));
    } else if (drag.mode === "l") {
      const x = Math.max(p.x, Math.min(z0.x + z0.w - Math.min(m, 1), wallX(z0.x + dx, drag.i)));
      z.x = r2(x); z.w = r2(z0.x + z0.w - x);
    } else {
      // the handle is on the far edge: pulling it away from the street deepens the block
      z.d = r2(Math.max(1, Math.min(far, edgeY(z0.y + z0.d + dy, drag.i)) - z.y));
    }
    redraw(drag.i);
  });
  const end = e => {
    if (!drag) return;
    const d = drag; drag = null;
    svg.classList.remove("dragging"); editor.dragging = false;
    if (d.plate) {
      ghost.innerHTML = "";
      if (d.moved && e.type === "pointerup" && (d.w !== p.width_m || d.d !== p.depth_m)) setPlate(d.w, d.d);
      else if (editor.pendingRender) renderEditor();
      return;
    }
    if (!d.moved) { if (editor.pendingRender) renderEditor(); return; }
    const z = zs[d.i], core = z && z.block === "core";
    // a block dropped back on the program leaves the plate
    const under = e.type === "pointerup" && d.mode === "move" ? document.elementFromPoint(e.clientX, e.clientY) : null;
    if (under && under.closest(".ed-program")) { zs.splice(d.i, 1); editor.sel = null; }
    commit(core);
  };
  svg.addEventListener("pointerup", end);
  svg.addEventListener("pointercancel", end);

  // keyboard: Tab lands on a block and selects it (Enter or Space does too); the arrows move the selected block a
  // module along the plate and 0.5 m across it (shift: a bay, 2 m); Delete removes it; Esc lets it go; Ctrl+Z undoes
  // from anywhere in the editor but a field (20 Nov 2026: nothing worked from the keys until a pointer had pressed)
  if (!box.dataset.undoKeys) {
    box.dataset.undoKeys = "1";
    box.addEventListener("keydown", e => {
      if (!(e.ctrlKey || e.metaKey) || e.shiftKey || String(e.key).toLowerCase() !== "z") return;
      if (e.target.closest && e.target.closest("input, select, textarea")) return;   // a field keeps its own undo
      e.preventDefault();
      editor.keepFocus = !!(e.target.closest && e.target.closest(".ed-canvas"));
      undo();
    });
  }
  svg.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && String(e.key).toLowerCase() === "d") { e.preventDefault(); duplicateSel(ctx); return; }
    const k = e.key, g = e.target.closest && e.target.closest(".ed-zone");
    if ((k === "Enter" || k === " ") && g) {
      e.preventDefault();
      const i = Number(g.dataset.i);
      select(i, false);
      say(`${blockName(zs[i])} selected, ${zs[i].w} × ${zs[i].d} m: the arrows move it a module (Shift: a bay), Delete removes it, Ctrl+Z undoes.`, "info");
      return;
    }
    if (k === "Escape" && editor.sel != null) { e.preventDefault(); select(null); svg.focus({ preventScroll: true }); return; }
    if (editor.sel == null || !zs[editor.sel]) return;
    const z = zs[editor.sel];
    if (k === "Delete" || k === "Backspace") { e.preventDefault(); removeSel(zs); return; }
    const sx = e.shiftKey ? editor.bay : m, sy = e.shiftKey ? 2 : 0.5;
    const arrow = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[k];
    if (!arrow) return;
    e.preventDefault(); snapshot();
    // the arrow as the plan is seen: turned back through the plan's turn (north up) and the mass's, into the plate's
    // own frame, where y runs away from the street (20 Nov 2026: on a plan turned 180° Up moved the block down)
    const t = -(ctx.rot || 0) * Math.PI / 180;
    const lx = arrow[0] * Math.cos(t) - arrow[1] * Math.sin(t), ly = -(arrow[0] * Math.sin(t) + arrow[1] * Math.cos(t));
    if (Math.abs(lx) >= Math.abs(ly)) z.x = r2(lx < 0 ? Math.max(p.x, gx(z.x - sx)) : Math.min(p.x + p.width_m - z.w, gx(z.x + sx)));
    else z.y = r2(ly > 0 ? Math.min(p.y + p.depth_m - z.d, z.y + sy) : Math.max(p.y, z.y - sy));
    commit(z.block === "core");
  });
}

/* ---------------------------------------------------------------- the engine */

function scheduleCheck() {
  clearTimeout(editor.timer);
  editor.timer = setTimeout(checkPlacement, 350);
}

function setBusy(on) {
  editor.busy = on;
  const b = $("#ed-busy"); if (b) b.hidden = !on;
}

/* the option as the engine reads it for the editor: the grid always, and the zones or the cores it is given */
function optionFor(extra) {
  const opt = JSON.parse(JSON.stringify(tidyOption(JSON.parse(JSON.stringify(state.option)))));
  opt.layout = Object.assign({}, opt.layout || {}, { grid: { bay_m: editor.bay, divide: editor.divide } });
  delete opt.layout.zones; delete opt.layout.cores;
  Object.assign(opt.layout, extra);
  return withLevels(withPlate(opt));
}

/* The plate the architect set, on an option: its width and depth for the massing (`massing.width_m`, `depth_m`),
   and the floor area that plate gives at the option's storeys, so the rules and the FSR read the plate drawn. */
function withPlate(opt) {
  if (editor.anchor) opt.massing = Object.assign({}, opt.massing || {}, { anchor: editor.anchor });
  if (editor.steps || (opt.massing && opt.massing.steps)) { opt.massing = Object.assign({}, opt.massing || {}, { steps: editor.steps || [] }); if (!editor.steps) delete opt.massing.steps; }
  if (editor.angle || (opt.massing && opt.massing.angle_deg)) opt.massing = Object.assign({}, opt.massing || {}, { angle_deg: editor.angle || 0 });
  const pl = editor.plate;
  if (!pl) return opt;
  opt.massing = Object.assign({}, opt.massing || {}, { width_m: pl.w, depth_m: pl.d });
  if (opt.gfa_m2 != null) {
    const g = Math.round(pl.w * pl.d * (Number(opt.storeys) || 1) * 10) / 10;
    if (opt.residential_gfa_m2 != null) opt.residential_gfa_m2 = Math.max(0, Math.round((g - (Number(opt.non_residential_gfa_m2) || 0)) * 10) / 10);
    opt.gfa_m2 = g;
  }
  return opt;
}

/* What the scheme stands over, in words: the FSR and the height against the limits `layout.capacity` reads (the
   rezoning policy's benchmark where it fired, else the outright maximum). Empty when it stands within both. Pure. */
function oversOf(cap) {
  const out = [];
  if (!cap) return out;
  if (cap.fsr_limit != null && cap.fsr > cap.fsr_limit + 0.005) out.push(`FSR ${Number(cap.fsr).toFixed(2)} against ${Number(cap.fsr_limit).toFixed(2)} (${cap.limit_from})`);
  if (cap.height_limit_m != null && cap.height_m > cap.height_limit_m + 0.05) out.push(`height ${cap.height_m} m against ${cap.height_limit_m} m (${cap.height_from})`);
  return out;
}

/* A new plate (or, with null, the plate the floor area and the storeys give again): the program is laid out on
   it afresh, the cut-outs that still fit kept; Undo brings back the plate and the blocks as they were. */
async function setPlate(w, d, anchor) {
  snapshot();
  if (anchor) editor.anchor = anchor;
  editor.plate = w == null ? null : { w, d };
  // a level added in the editor carries a plate of floor area: the plate as set, or (Auto) the plate there was
  // before one was set (23 Nov 2026: Auto after a set plate and an added level left the floor area on the set plate)
  editor.base.plate = editor.plate ? Math.round(w * d * 10) / 10 : (editor.base.auto || editor.base.plate);
  editor.dirty = true;
  await suggestPlan(false, true);
  // the homes on the plates now, after the step-backs have taken theirs off (25 Nov 2026: the message counted before that)
  const L = editor.result, c = L.capacity || {}, trk = programTracker(L, editor.zones), left = trk.unitsLeft, onPlate = trk.unitsNeed - trk.unitsLeft;
  say(`The plate is ${L.plate.width_m} × ${L.plate.depth_m} m, ${fmtNum(Math.round(L.plate.width_m * L.plate.depth_m))} m² a floor${w == null ? ", as the floor area and the storeys give it" : ""}${c.fsr != null ? `: FSR ${Number(c.fsr).toFixed(2)}${c.fsr_limit != null ? ` of ${Number(c.fsr_limit).toFixed(2)}` : ""}` : ""}. The program is laid out on it again: ${onPlate} of ${trk.unitsNeed} homes placed${left > 0 ? `, ${left} left to place` : ""}. ${oversOf(c).length ? `Over a limit: ${oversOf(c).join("; ")}. ` : ""}Undo brings back the plate as it was; Apply writes it into the option.`, left > 0 || oversOf(c).length ? "busy" : "ok");
}

/* The levels added in the editor, on an option: a storey each, and (where the option states them) a plate more of
   floor area and a floor more of height, so the plate stays as it is and the rules read the taller building. */
function withLevels(opt) {
  const n = editor.added || 0, b = editor.base || {};
  if (!n) return opt;
  opt.storeys = (Number(opt.storeys) || 1) + n;
  for (const k of ["gfa_m2", "residential_gfa_m2"]) if (opt[k] != null) opt[k] = Math.round((Number(opt[k]) + n * b.plate) * 10) / 10;
  if (opt.height_m != null) opt.height_m = r2(Number(opt.height_m) + n * b.f2f);
  return opt;
}

/* One more level, where the FSR leaves room for another plate: it takes the cores and the corridor of the level
   under it, and the program left to place is dragged onto it (or Suggest a grid plan lays it out again). */
async function addLevel() {
  const L = editor.result || state.run.layout, cap = L.capacity;
  if (!cap || (cap.fsr_limit != null && cap.levels_room < 1)) return;
  snapshot();
  const top = L.floors.length - 1, lv = top + 1;
  editor.added = (editor.added || 0) + 1;
  editor.zones[String(lv)] = (editor.zones[String(top)] || []).filter(z => z.block === "core" || z.block === "corridor").map(z => ({ ...z }));
  if (editor.steps) { editor.result = Object.assign({}, L, { floors: L.floors.concat([{ level: lv }]) }); rebuildSteps(); editor.result = L; }   // the new level steps back with the ones under it
  editor.sel = null; editor.dirty = true;
  clearTimeout(editor.timer);
  await checkPlacement();
  const now = editor.result;
  if (now.floors[lv]) { editor.level = lv; renderEditor(); }
  const c = now.capacity || {}, left = programTracker(now, editor.zones).unitsLeft;
  say(`${floorName(lv)} is added: ${now.floors.length} storeys, FSR ${Number(c.fsr).toFixed(2)}${c.fsr_limit != null ? ` of ${Number(c.fsr_limit).toFixed(2)} (${c.limit_from})` : ""}. It has the cores and the corridor of the level under it${left ? `; ${left} units are left to place: drag them on, or Suggest a grid plan lays the program out over all ${now.floors.length} levels` : ""}. ${oversOf(c).length ? `Over a limit: ${oversOf(c).join("; ")}. ` : ""}Apply writes the storeys, floor area and height into the option.`, oversOf(c).length ? "busy" : "ok");
}

async function removeLevel() {
  if (!editor.added) return;
  const L = editor.result || state.run.layout, top = L.floors.length - 1;
  snapshot();
  delete editor.zones[String(top)];
  editor.added -= 1; editor.sel = null; editor.dirty = true;
  if (editor.level >= top) editor.level = top - 1;
  clearTimeout(editor.timer);
  await checkPlacement();
  say(`${floorName(top)} is taken off again, with its blocks; Undo brings it back.`, "info");
}

/* the other sheets follow the check */
function updateSheets(res) {
  const fig = $('.figure.sheet[data-sheet="plans"]');
  if (!fig || !res.sheets) return;
  const ax = $('.sheet-body[data-view="axon"]', fig); if (ax) ax.innerHTML = res.sheets.axon || "";
  const pl = $('.sheet-body[data-view="plans"] .plans-overview', fig); if (pl) pl.innerHTML = res.sheets.plans || "";
  refreshPlanFloor();   // the floor picked on Plans by program follows the check
  for (const b of $$(".figure.sheet .sheet-body")) {
    const card = b.closest(".figure"); const eb = card && $(".eyebrow", card); const t = eb ? eb.textContent : "";
    if (/Stacking/.test(t)) b.innerHTML = res.sheets.stacking || ""; else if (/elevations/i.test(t)) b.innerHTML = res.sheets.elevations || ""; else if (/site plan/i.test(t)) b.innerHTML = res.sheets["site-plan"] || "";
  }
}

async function ask(opt) {
  const res = await postJSON("/api/layout", { site: state.site, option: opt, as_of: $("#as-of").value || todayISO() });
  // the plate a level adds, as the engine has it (a run read from disk may predate the figure)
  if (!editor.added && res.layout && res.layout.capacity) { editor.base.plate = res.layout.capacity.plate_m2; if (!editor.plate) editor.base.auto = editor.base.plate; }
  if (res.massing) editor.massing = res.massing;   // the lot, the envelope and the context the canvas draws behind the plate
  return res;
}

/* The engine measures the placement: the option with these zones is read under the rules exactly as a run would
   read it; the result redraws the editor's status and the other sheets. A redraw waits for a drag to end. */
async function checkPlacement() {
  if (!editor.open || !state.site || !state.option) return;
  const seq = editor.seq = (editor.seq || 0) + 1;
  setBusy(true);
  try {
    const res = await ask(optionFor({ zones: editor.zones }));
    if (seq !== editor.seq) return;
    editor.result = res.layout;
    updateSheets(res);
  } catch (e) {
    toast(`The engine could not check the placement: ${e.message}`, true);
  } finally {
    if (seq === editor.seq) { setBusy(false); if (editor.dragging) editor.pendingRender = true; else renderEditor(); }
  }
}

/* The suggested plan: the engine lays the whole program out on the grid, round the cores where the architect
   stood them (the solver's own core without one); what does not fit stays in the program as left to place. */
async function suggestPlan(first, noSnapshot) {
  if (!editor.open || !state.site || !state.option) return;
  // the cut-outs are the architect's shape of the plate: they stay where they are, and the program goes round them
  // the names the architect gave blocks: carried onto the fresh plan's nearest block of the same kind on the same floor
  const named = Object.entries(editor.zones || {}).flatMap(([k, zs]) => zs.filter(z => z.name && !z.step).map(z => ({ k, block: z.block, name: z.name, cx: z.x + z.w / 2, cy: z.y + z.d / 2 })));
  const cuts = Object.fromEntries(Object.entries(editor.zones || {}).map(([k, zs]) => [k, zs.filter(z => z.block === "void" && !z.step)]).filter(([, v]) => v.length));
  const cores = editor.coreMoved ? coresNow() : [];   // the solver's own core, on the grid, until one is moved by hand
  const seq = editor.seq = (editor.seq || 0) + 1;
  clearTimeout(editor.timer);
  setBusy(true);
  try {
    const res = await ask(optionFor(cores.length ? { cores } : {}));
    if (seq !== editor.seq) return;
    if (!first && !noSnapshot) snapshot();
    editor.result = res.layout; editor.zones = zonesFromLayout(res.layout); editor.sel = null; editor.dirty = true;
    const P = res.layout.plate, hits = (a, b) => !(a.x + a.w <= b.x + 0.01 || b.x + b.w <= a.x + 0.01 || a.y + a.d <= b.y + 0.01 || b.y + b.d <= a.y + 0.01);
    let kept = 0;
    for (const [k, vs] of Object.entries(cuts)) {
      const inside = vs.filter(v => v.x >= P.x - 0.01 && v.y >= P.y - 0.01 && v.x + v.w <= P.x + P.width_m + 0.01 && v.y + v.d <= P.y + P.depth_m + 0.01);
      if (!editor.zones[k] || !inside.length) continue;
      editor.zones[k] = editor.zones[k].filter(z => z.block === "core" || z.block === "corridor" || !inside.some(v => hits(z, v))).concat(inside.map(v => ({ ...v })));
      kept += inside.length;
    }
    for (const n of named) {
      const cand = (editor.zones[n.k] || []).filter(z => z.block === n.block && !z.name);
      if (!cand.length) continue;
      cand.sort((a, b) => Math.hypot(a.x + a.w / 2 - n.cx, a.y + a.d / 2 - n.cy) - Math.hypot(b.x + b.w / 2 - n.cx, b.y + b.d / 2 - n.cy));
      cand[0].name = n.name;
    }
    if (editor.steps) rebuildSteps();   // the step-back's strips again, and the blocks the fresh plan stood in them taken off
    if (kept || editor.steps) scheduleCheck();   // the engine counts again what the cut-outs displaced
    updateSheets(res);
    const L = res.layout, trk = programTracker(L, editor.zones), left = trk.unitsLeft;   // counted after the step-backs
    say(`A grid plan, not the memo's: laid out afresh on a ${editor.bay} m bay${cores.length ? ` round your core${cores.length === 1 ? "" : "s"}` : ""}, ${trk.unitsNeed - trk.unitsLeft} of ${trk.unitsNeed} homes placed${left > 0 ? `; ${left} did not fit and stay in the program as left to place` : ""}. Drag to adjust; Undo brings back the plan that was there; Apply makes it the option's.`, left > 0 ? "busy" : "ok");
  } catch (e) {
    toast(`The engine could not suggest a plan: ${e.message}`, true);
  } finally {
    if (seq === editor.seq) { setBusy(false); renderEditor(); }
  }
}

function applyEditor() {
  if (!state.option) return;
  const added = editor.added || 0;
  if (added) {
    // the levels added here become the option's own: storeys, floor area and height, which the rules read
    withLevels(state.option);
    editor.added = 0;
    renderForm($("#option-form"), OPTION_FIELDS, state.option, onOptionChange);
    markStale("the option");
  }
  // the plate as drawn: its dimensions for the massing, and the floor area it gives less the cut-outs, which are
  // not floor; a cut-out on a plate the floor area still sizes pins the plate first, so it does not shrink
  const Lr = editor.result || state.run.layout, storeys = Number(state.option.storeys) || Lr.floors.length;
  const cut = Object.entries(editor.zones).filter(([k]) => Number(k) < storeys).reduce((t, [, zs]) => t + zs.filter(z => z.block === "void").reduce((a, z) => a + z.w * z.d, 0), 0);
  if (cut > 0 && !editor.plate) editor.plate = { w: Lr.plate.width_m, d: Lr.plate.depth_m };
  // the angle the mass is turned by, where it changed
  if (editor.anchor && (state.option.massing || {}).anchor !== editor.anchor) { state.option.massing = Object.assign({}, state.option.massing || {}, { anchor: editor.anchor }); markStale("the option"); }
  const wasAngle = Number((state.option.massing || {}).angle_deg) || 0, nowAngle = editor.angle || 0;
  if (nowAngle !== wasAngle) {
    state.option.massing = Object.assign({}, state.option.massing || {}, { angle_deg: nowAngle });
    if (!nowAngle) delete state.option.massing.angle_deg;
    markStale("the option");
  }
  // the step-back, for the massing's tiers (the 3D view); its floor area is the cut-outs', counted below
  const wasSteps = JSON.stringify((state.option.massing || {}).steps || null), nowSteps = JSON.stringify(editor.steps || null);
  if (wasSteps !== nowSteps) {
    state.option.massing = Object.assign({}, state.option.massing || {});
    if (editor.steps) state.option.massing.steps = JSON.parse(nowSteps); else delete state.option.massing.steps;
    markStale("the option");
  }
  const shaped = !!editor.plate;
  if (shaped) {
    const o = state.option, g = Math.round((editor.plate.w * editor.plate.d * storeys - cut) * 10) / 10;
    o.massing = Object.assign({}, o.massing || {}, { width_m: editor.plate.w, depth_m: editor.plate.d });
    if (o.residential_gfa_m2 != null) o.residential_gfa_m2 = Math.max(0, Math.round((g - (Number(o.non_residential_gfa_m2) || 0)) * 10) / 10);
    o.gfa_m2 = g;
    renderForm($("#option-form"), OPTION_FIELDS, state.option, onOptionChange);
    markStale("the option");
  }
  state.option.layout = Object.assign({}, state.option.layout || {}, { zones: JSON.parse(JSON.stringify(editor.zones)), grid: { bay_m: editor.bay, divide: editor.divide } });
  state.optionDirty = true; $("#option-dirty").hidden = false;
  editor.applied = true; editor.dirty = false;
  renderEditor();
  refreshSummary("option");
  const n = Object.values(editor.zones).reduce((t, a) => t + a.length, 0);
  say(`${n} blocks on ${Object.keys(editor.zones).length} floors written into the option as layout.zones, with the ${editor.bay} m grid. ${nowAngle !== wasAngle ? `The mass is turned ${nowAngle}° on the lot. ` : ""}${shaped ? `The plate is ${editor.plate.w} × ${editor.plate.d} m${cut ? `, ${fmtNum(Math.round(cut))} m² of it cut out` : ""}: the option's floor area is ${fmtNum(state.option.gfa_m2)} m². ` : ""}${added ? `The option is now ${state.option.storeys} storeys${state.option.gfa_m2 != null ? `, ${fmtNum(state.option.gfa_m2)} m²` : ""}: the memo on screen is from before, so run the rules again.` : (shaped || nowAngle !== wasAngle ? "The memo on screen is from before, so run the rules again." : "Run the rules to make the memo from them;")} Save option as… keeps them.`, "ok");
}
