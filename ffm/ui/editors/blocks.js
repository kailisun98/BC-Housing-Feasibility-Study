/* The block editor (architect mode, FIG 03), loaded on first use: schematic program plans on the plates.
   The program the manager approved sits beside the plate the whole time, each block with what is placed and what
   is left; the architect drags a block from it onto the plate, or asks for a suggested plan and adjusts it. The
   blocks' walls sit on a structural grid (a 6 m or 8 m bay, wall to wall, and its half or quarter); a core is
   the same on every floor, so moving it on one floor moves it on all. The engine measures every move
   (POST /api/layout, or the engine in the browser) and says what broke and which rules still hold; the other
   sheets redraw from the same check. Apply writes the placement into the option (`layout.zones`, `layout.grid`),
   so Run the rules reproduces it and the memo says it was placed by hand. Rebuilt 17 Nov 2026. */

import { $, $$, fmtNum, h, pill, setStatus, toast, todayISO } from "../core/util.js";
import { editor, state } from "../core/state.js";
import { postJSON } from "../core/api.js";
import { refreshSummary, renderForm } from "../schedule.js";
import { markStale, onOptionChange, tidyOption } from "../files.js";
import { OPTION_FIELDS } from "../fields.js";
import { egressLine } from "../memo/answers.js";

const EDIT_BLOCKS = [["studio", "Studio"], ["one_bed", "One-bedroom"], ["two_bed", "Two-bedroom"], ["three_bed_plus", "Three-bedroom+"], ["non_residential", "Non-residential"], ["amenity", "Amenity"], ["services", "Services, bicycles"], ["core", "Core"], ["corridor", "Corridor"]];

const ZONE_TONE = { studio: "#dbe9f8", one_bed: "#b9d4f0", two_bed: "#8fb8e3", three_bed_plus: "#6b9fd4", corridor: "#f4f4f2", core: "#c9c9c5", services: "#e2e2df", amenity: "#f6e7c1", non_residential: "#f0cf9a", other: "#e6dfd0" };

const ZONE_SHORT = { studio: "st", one_bed: "1b", two_bed: "2b", three_bed_plus: "3b", corridor: "corridor", core: "core", services: "services", amenity: "amenity", non_residential: "non-res" };

const UNIT_KEYS = ["studio", "one_bed", "two_bed", "three_bed_plus"];
const isUnit = k => UNIT_KEYS.includes(k);
const zoneShort = z => z.block === "other" ? String(z.label || "other").slice(0, 12).toLowerCase() : (ZONE_SHORT[z.block] || z.block);
const blockName = z => z.block === "other" ? (z.label || "Other") : (EDIT_BLOCKS.find(([k]) => k === z.block)?.[1] || z.block);
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
const unitW = (gross, minGross, strip) => {
  const near = Math.max(1, Math.round(gross / strip / mod())) * mod();
  return near * strip + 0.5 >= (minGross || gross) ? r2(near) : ceilM(gross / strip);
};

function zonesFromLayout(L) {
  const out = {};
  for (const fl of L.floors) out[String(fl.level)] = fl.zones.filter(z => z.block !== "spare").map(z => ({ block: z.block, x: z.x, y: z.y, w: z.w, d: z.d, ...(z.accessible ? { accessible: true } : {}), ...(z.block === "other" ? { label: z.label } : {}) }));
  return out;
}

/* The strips a plate offers: the street strip, the corridor behind it, the lane strip (a double-loaded plate). */
function bandsOf(p) {
  const strip = p.unit_depth_m, corr = r2(p.y + strip);
  return { strip, front: p.y, corr, rear: p.double_loaded ? r2(corr + CORR) : null };
}

/* What the program asks for against what the editor has placed on every floor: one row per block, with what is
   left to place; the architect's own programs (option.layout.extra_programs) are rows too. Pure. */
function programTracker(L, zones) {
  const all = Object.values(zones || {}).flat();
  const rows = (L.program || []).map(b => {
    const unit = isUnit(b.key);
    const mine = all.filter(z => b.key === "other" ? (z.block === "other" && String(z.label || "").trim().toLowerCase() === String(b.label).trim().toLowerCase()) : z.block === b.key);
    const placedArea = mine.reduce((t, z) => t + z.w * z.d, 0);
    return unit ? { key: b.key, label: b.label, unit: true, need: b.count, placed: mine.length, left: b.count - mine.length, each: b.gross_m2_each, min: b.min_gross_m2_each }
      : { key: b.key, label: b.label, unit: false, need: b.area_m2, placed: Math.round(placedArea), left: Math.round(b.area_m2 - placedArea) };
  });
  // a use placed in whole modules runs a little over its area: over is said past 15%
  for (const r of rows) r.short = r.left > (r.unit ? 0 : 1), r.over = r.left < (r.unit ? 0 : -Math.max(1, 0.15 * r.need));
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
    if (!(a.x + a.w <= b.x + 0.01 || b.x + b.w <= a.x + 0.01 || a.y + a.d <= b.y + 0.01 || b.y + b.d <= a.y + 0.01)) { bad.add(i); bad.add(j); }
  }
  return bad;
}

export function openEditor() {
  const run = state.run;
  if (!run || !run.layout) return;
  const lay = (state.option && state.option.layout) || {};
  const fromOption = lay.zones;
  const grid = lay.grid || run.layout.plate.grid;
  if (grid && grid.bay_m) { editor.bay = Number(grid.bay_m) || 6; editor.divide = [1, 2, 4].includes(Number(grid.divide)) ? Number(grid.divide) : 2; }
  editor.open = true; editor.level = 0; editor.sel = null; editor.dirty = false; editor.applied = !!fromOption; editor.history = []; editor.dragging = false; editor.coreMoved = !!fromOption;
  // the levels the architect adds here sit on top of the option's own storeys until Apply writes them into it
  editor.added = 0;
  editor.base = { plate: (run.layout.capacity && run.layout.capacity.plate_m2) || Math.round(run.layout.plate.width_m * run.layout.plate.depth_m * 10) / 10, f2f: run.layout.plate.floor_to_floor_m || 0 };
  editor.zones = JSON.parse(JSON.stringify(fromOption || zonesFromLayout(run.layout)));
  editor.result = run.layout;
  const fig = $('.figure.sheet[data-sheet="plans"]');
  $$(".sheet-body", fig).forEach(x => { x.hidden = true; });
  $("#edit-blocks").setAttribute("aria-expanded", "true");
  $("#edit-blocks").textContent = "Close the editor";
  $("#sheet-editor").hidden = false;
  renderEditor();
  if (fromOption) setStatus("Block editor: your placement, as the option carries it. Drag a block from the program onto the plate, or drag one on the plate to move it; the engine checks every move.", "info");
  else suggestPlan(true);   // a first plan on the grid, to adjust
  if (fromOption) checkPlacement();   // a run read from disk may predate what the editor reads (the FSR room)
}

export function closeEditor() {
  editor.open = false;
  const fig = $('.figure.sheet[data-sheet="plans"]');
  if (!fig) return;
  const view = ($('[data-sheet-view][aria-pressed="true"]', fig) || {}).dataset?.sheetView || "plans";
  $$(".sheet-body", fig).forEach(x => { x.hidden = x.dataset.view !== view; });
  $("#sheet-editor").hidden = true;
  const b = $("#edit-blocks"); if (b) { b.setAttribute("aria-expanded", "false"); b.textContent = "Edit blocks"; }
  if (editor.dirty && !editor.applied) setStatus("The editor closed with changes not applied to the option; open it again to apply them.", "info");
}

/* ---------------------------------------------------------------- undo, and the cores that stand on every floor */

function snapshot() {
  (editor.history = editor.history || []).push(JSON.stringify({ z: editor.zones, a: editor.added || 0 }));
  if (editor.history.length > 60) editor.history.shift();
}

function undo() {
  const s = (editor.history || []).pop();
  if (!s) return;
  const was = JSON.parse(s);
  editor.zones = was.z; editor.added = was.a; editor.sel = null; editor.dirty = true;
  renderEditor(); scheduleCheck();
  setStatus("Undone.", "info");
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

/* Every change ends here: the cores follow on every floor when one was touched, the editor redraws, the engine checks. */
function commit(core) {
  if (core) {
    editor.coreMoved = true;   // from here a suggested plan keeps the cores where the architect stood them
    const L = editor.result || state.run.layout, hit = syncCores();
    setStatus(`The cores are the same on all ${L.floors.length} floors: the stairs do not shift from level to level.${hit ? ` ${hit} block${hit === 1 ? "" : "s"} on other floors now sit${hit === 1 ? "s" : ""} on a core: move them, or Suggest a plan lays the program round the cores.` : ""}`, hit ? "busy" : "info");
  }
  editor.dirty = true;
  renderEditor(); scheduleCheck();
}

/* ---------------------------------------------------------------- the drawing */

const rectOf = (z, p, scale) => ({ x: M + (z.x - p.x) * scale, y: M + (p.depth_m - (z.y - p.y) - z.d) * scale, w: Math.max(1, z.w * scale), d: Math.max(1, z.d * scale) });

/* one block: its rectangle, the accessible mark, its name and width, and the three handles (shown when selected) */
function zoneInner(z, r) {
  const f = v => v.toFixed(1);
  const two = r.w > 34 && r.d > 30 && z.block !== "corridor";
  return `<rect x="${f(r.x)}" y="${f(r.y)}" width="${f(r.w)}" height="${f(r.d)}" fill="${ZONE_TONE[z.block] || "#eee"}" stroke="#5f6672" stroke-width="0.8"/>
    ${z.accessible ? `<circle cx="${f(r.x + 7)}" cy="${f(r.y + 7)}" r="3.2" fill="#245f9c"/>` : ""}
    ${r.w > 22 && r.d > 11 ? `<text x="${f(r.x + r.w / 2)}" y="${f(r.y + r.d / 2 + (two ? -1 : 3.5))}" font-size="9.5" font-weight="500" text-anchor="middle" fill="#1f2933">${h(zoneShort(z))}</text>` : ""}
    ${two ? `<text x="${f(r.x + r.w / 2)}" y="${f(r.y + r.d / 2 + 10)}" font-size="8.5" text-anchor="middle" fill="#5f6672">${h(z.w)} m</text>` : ""}
    <rect class="ed-handle ed-handle-w" x="${f(r.x + r.w - 4)}" y="${f(r.y + r.d / 2 - 7)}" width="8" height="14" rx="2" fill="#245f9c"/>
    <rect class="ed-handle ed-handle-l" x="${f(r.x - 4)}" y="${f(r.y + r.d / 2 - 7)}" width="8" height="14" rx="2" fill="#245f9c"/>
    <rect class="ed-handle ed-handle-d" x="${f(r.x + r.w / 2 - 7)}" y="${f(r.y - 4)}" width="14" height="8" rx="2" fill="#245f9c"/>`;
}

/* the line above the plate: what is selected and what can be done with it */
function selBarHtml(L, zs) {
  const sel = editor.sel != null ? zs[editor.sel] : null;
  if (!sel) return `<span class="help">Drag a block from the program onto the plate. On the plate: drag to move, pull an edge to resize, Delete removes, Ctrl+Z undoes.</span>`;
  const prog = (L.program || []).find(b => b.key === sel.block);
  const gross = prog && prog.gross_m2_each, least = (prog && prog.min_gross_m2_each) || gross, a = sel.w * sel.d;
  const over = !gross ? "" : (a > gross * 1.15 ? ` <span class="warn-text">· ${fmtNum(Math.round(a - gross))} m² over the ${fmtNum(Math.round(gross))} m² the program carries</span>` : (a + 0.5 < least ? ` <span class="warn-text">· ${fmtNum(Math.round(least - a))} m² under its ${fmtNum(Math.round(least))} m² minimum</span>` : ""));
  // a program block can be turned into another program where it stands; the cores and corridors are structure
  const structure = sel.block === "core" || sel.block === "corridor";
  const valOf = b => b.key === "other" ? `other:${b.label}` : b.key, mine = sel.block === "other" ? `other:${sel.label || "Other"}` : sel.block;
  const kinds = (L.program || []).map(b => [valOf(b), b.label]);
  if (!structure && !kinds.some(([v]) => v === mine)) kinds.unshift([mine, blockName(sel)]);
  const name = structure ? `<b>${h(blockName(sel))}</b>` : `<select id="ed-kind" class="ed-kind" aria-label="The program of this block" title="Change this block's program">${kinds.map(([v, l]) => `<option value="${h(v)}"${v === mine ? " selected" : ""}>${h(l)}</option>`).join("")}</select>`;
  return `${name} <span>${h(sel.w)} × ${h(sel.d)} m, ${h(fmtNum(Math.round(a)))} m²${over}</span>
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
      return row(r.key, r.label, ZONE_TONE[r.key], `${fmtNum(Math.round(r.each))} m² · ${B.strip ? unitW(r.each, r.min, B.strip) : "?"} m wide · ${r.placed} of ${r.need}`, count, cls, pct,
        `${r.label}: ${r.placed} of ${r.need} placed${r.short ? `, ${r.left} to place` : ""}. Enter adds one to this floor.`);
    }
    const count = r.short ? `<b>${fmtNum(r.left)} m²</b> to place` : (r.over ? `<b>${fmtNum(-r.left)} m²</b> over` : "placed");
    return row(r.key, r.label, ZONE_TONE[r.key] || ZONE_TONE.other, `${fmtNum(r.placed)} of ${fmtNum(Math.round(r.need))} m²`, count, cls, pct,
      `${r.label}: ${r.placed} of ${Math.round(r.need)} square metres placed. Enter adds it to this floor.`);
  }).join("");
  const nCore = zs.filter(z => z.block === "core").length;
  const withCorr = L.floors.filter(fl => (editor.zones[String(fl.level)] || []).some(z => z.block === "corridor")).length;
  const hereCorr = zs.some(z => z.block === "corridor");
  const structure = row("core", "Core", ZONE_TONE.core, "stairs, elevator · the same on every floor", nCore ? `${nCore} on every floor` : "<b>none</b>", nCore ? "done" : "short", null, `Core: ${nCore} on every floor. Enter adds one.`)
    + row("corridor", "Corridor", ZONE_TONE.corridor, `${withCorr} of ${L.floors.length} floors have one`, hereCorr ? "on this floor" : "<b>none here</b>", hereCorr ? "done" : "short", null, `Corridor: ${hereCorr ? "on this floor" : "none on this floor"}. Enter adds one.`);
  const head = tr.unitsLeft ? `<b>${tr.unitsLeft}</b> of ${tr.unitsNeed} units to place` : `All <b>${tr.unitsNeed}</b> units placed`;
  return `<aside class="ed-program" aria-label="The program, placed and left to place">
      <div class="ed-prog-head"><span class="eyebrow">Program</span><span class="ed-left ${tr.done ? "done" : "short"}">${head}${tr.areasShort ? ` · ${tr.areasShort} other block${tr.areasShort === 1 ? "" : "s"} short` : ""}</span></div>
      <ul class="ed-prog-list">${rows}</ul>
      <div class="ed-prog-sub">Structure</div>
      <ul class="ed-prog-list">${structure}</ul>
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
  const scale = (width - 2 * M) / p.width_m;
  const H = p.depth_m * scale + 2 * M + 2;
  const bad = clashes(zs);
  const order = zs.map((z, i) => i).filter(i => i !== editor.sel).concat(editor.sel != null ? [editor.sel] : []);   // the selected block on top
  const svgZones = order.map(i => {
    const z = zs[i];
    return `<g class="ed-zone${i === editor.sel ? " sel" : ""}${bad.has(i) ? " clash" : ""}" data-i="${i}" tabindex="0" role="button" aria-label="${h(blockName(z))}, ${z.w} by ${z.d} m, at ${z.x}, ${z.y} m${bad.has(i) ? ", overlapping another block" : ""}">${zoneInner(z, rectOf(z, p, scale))}</g>`;
  }).join("");
  // the grid: a line at every bay, a fainter one at every module, the bays' distances along the top
  let grid = "", ticks = "";
  for (let k = 0; k * m <= p.width_m + 1e-6; k++) {
    const x = (M + k * m * scale).toFixed(1), bay = k % editor.divide === 0;
    grid += `<line x1="${x}" y1="${M}" x2="${x}" y2="${(M + p.depth_m * scale).toFixed(1)}" stroke="${bay ? "#aab4c0" : "#cfd6de"}" stroke-width="${bay ? 0.8 : 0.5}"${bay ? "" : ` stroke-dasharray="2 3"`}/>`;
    if (bay && editor.bay * scale >= 22) ticks += `<text x="${x}" y="${M - 6}" font-size="8.5" text-anchor="middle" fill="#5f6672">${r2(k * m)}</text>`;
  }
  const bandY = v => (M + (p.depth_m - (v - p.y)) * scale).toFixed(1);
  const bandLines = [B.corr, B.rear].filter(v => v != null && v < p.y + p.depth_m - 0.05).map(v => `<line x1="${M}" y1="${bandY(v)}" x2="${(M + p.width_m * scale).toFixed(1)}" y2="${bandY(v)}" stroke="#aab4c0" stroke-width="0.6" stroke-dasharray="5 4"/>`).join("");
  const floorsBtns = L.floors.map(fl => {
    const n = (editor.zones[String(fl.level)] || []).filter(z => isUnit(z.block)).length;
    const broken = (L.geometry || []).some(g => g.level === fl.level);
    return `<button type="button" class="segbtn" data-ed-level="${fl.level}" aria-pressed="${fl.level === editor.level}" title="${h(floorName(fl.level))}: ${n} unit${n === 1 ? "" : "s"}${broken ? ", something to fix" : ""}">${h(floorName(fl.level))}<small>${n}${broken ? " !" : ""}</small></button>`;
  }).join("");
  const floorChecks = (L.geometry || []).filter(g => g.level === editor.level);
  const problems = (L.geometry || []).length;
  const tr = programTracker(L, editor.zones);
  const egF = L.egress && (L.egress.floors || []).find(f => f.level === editor.level);
  const otherBay = !BAYS.includes(editor.bay);
  // another level, where the FSR leaves room for one more plate
  const cap = L.capacity, f3 = v => (Math.round(v * 100) / 100).toFixed(2);
  const canAdd = !!cap && (cap.fsr_limit == null || cap.levels_room >= 1);
  const capNote = !cap ? "" : (cap.fsr_limit == null ? `FSR ${f3(cap.fsr)} · the rules carry no FSR limit here`
    : `FSR ${f3(cap.fsr)} of ${f3(cap.fsr_limit)} · ${cap.levels_room >= 1 ? `room for ${cap.levels_room} more level${cap.levels_room === 1 ? "" : "s"}` : `no room for a level (${fmtNum(Math.round(cap.plate_m2))} m² needed, ${fmtNum(Math.round(cap.room_m2))} m² left)`}`);
  const capTitle = !cap ? "" : (cap.fsr_limit == null ? `Add a level of ${fmtNum(Math.round(cap.plate_m2))} m²: the FSR goes to ${f3(cap.fsr_with_one_more)}; the rules carry no FSR limit for this district to hold it against`
    : (canAdd ? `Add a level of ${fmtNum(Math.round(cap.plate_m2))} m² for the program left to place: the FSR goes to ${f3(cap.fsr_with_one_more)} of ${f3(cap.fsr_limit)} (${cap.limit_from})` : `A level of ${fmtNum(Math.round(cap.plate_m2))} m² would take the FSR to ${f3(cap.fsr_with_one_more)}, past ${f3(cap.fsr_limit)} (${cap.limit_from})`));
  const levelsCtl = !cap ? "" : `<span class="ed-levels">
        <button type="button" class="btn btn-small" id="ed-addlevel"${canAdd ? "" : " disabled"} title="${h(capTitle)}">+ Level</button>
        ${editor.added ? `<button type="button" class="btn btn-small btn-quiet" id="ed-dellevel" title="Take the top level off again, with its blocks">− Level</button>` : ""}
        <span class="help${cap.fsr_limit != null && !canAdd ? " warn-text" : ""}">${h(capNote)}</span></span>`;
  box.classList.toggle("ed-wide", wide);
  box.innerHTML = `
    <div class="ed-bar">
      <div class="seg ed-floors" role="group" aria-label="Floor">${floorsBtns}</div>
      ${levelsCtl}
      <span class="ed-grid" role="group" aria-label="Structural grid">
        <span class="label">Bay, wall to wall</span>
        <span class="seg">${BAYS.map(v => `<button type="button" class="segbtn" data-ed-bay="${v}" aria-pressed="${editor.bay === v}">${v} m</button>`).join("")}</span>
        <input type="number" id="ed-bay-other" min="3" max="12" step="0.1" placeholder="other" value="${otherBay ? editor.bay : ""}" aria-label="Another bay width in metres" title="Another bay width, 3 to 12 m">
        <select id="ed-divide" aria-label="What the walls sit on" title="What the blocks' walls sit on">${DIVIDES.map(([v, l]) => `<option value="${v}"${v === editor.divide ? " selected" : ""}>walls on ${h(l)}</option>`).join("")}</select>
      </span>
      <span class="ed-tools">
        <span class="help ed-busy" id="ed-busy"${editor.busy ? "" : " hidden"}>Checking…</span>
        <button type="button" class="btn btn-small btn-quiet" id="ed-undo"${(editor.history || []).length ? "" : " disabled"} title="Undo the last change (Ctrl+Z)">Undo</button>
        <button type="button" class="btn btn-small" id="ed-suggest" title="Lay the whole program out on this grid, round the cores where they stand; Undo brings back what was there">Suggest a plan</button>
      </span>
    </div>
    <div class="ed-main">
      ${programHtml(L, tr, zs, B)}
      <div class="ed-stage">
        <div class="ed-selbar" id="ed-selbar">${selBarHtml(L, zs)}</div>
        <svg class="ed-canvas" viewBox="0 0 ${width} ${H.toFixed(0)}" width="${width}" height="${H.toFixed(0)}" role="application" aria-label="Block editor, ${h(L.floors[editor.level].name)}">
          <rect x="${M}" y="${M}" width="${(p.width_m * scale).toFixed(1)}" height="${(p.depth_m * scale).toFixed(1)}" fill="#fbfbfa" stroke="#1f2933" stroke-width="1.2"/>
          ${grid}${bandLines}${ticks}
          <text x="${(M + p.width_m * scale / 2).toFixed(1)}" y="${(H - 6).toFixed(1)}" font-size="10" text-anchor="middle" fill="#5f6672">street · plate ${h(p.width_m)} × ${h(p.depth_m)} m · walls on the ${h(r2(m))} m module of a ${h(editor.bay)} m bay</text>
          ${svgZones}
          <g id="ed-ghost" pointer-events="none"></g>
        </svg>
        <div class="ed-status">
          ${floorChecks.length ? `<ul class="finding-list">${floorChecks.map(g => `<li>${pill("fail")}<span>${h(g.note)}</span></li>`).join("")}</ul>` : `<span class="help">Nothing broken on ${h(floorWords(editor.level))}.${problems ? ` ${problems} on other floors (marked ! above).` : ""}</span>`}
          ${egF ? `<span class="help">${pill(egF.status)} Exits on this floor: ${h(egressLine(egF))}${egF.notes && egF.notes.length ? ` <span class="cont">· ${h(egF.notes[0])}</span>` : ""}</span>` : ""}
          <span class="help">${h((L.adjacencies || []).filter(c => c.status === "pass").length)} adjacency rules hold, ${h((L.adjacencies || []).filter(c => c.status === "conditional").length)} conditional.</span>
        </div>
      </div>
    </div>
    <div class="form-actions">
      <button type="button" class="btn btn-primary btn-small" id="ed-apply"${editor.dirty || !editor.applied ? "" : " disabled"}>${problems ? `Apply with ${problems} problem${problems === 1 ? "" : "s"}` : "Apply to the option"}</button>
      <button type="button" class="btn btn-small btn-quiet" id="ed-repeat" title="Copy this floor's blocks onto every floor above it"${editor.level >= L.floors.length - 1 ? " disabled" : ""}>Repeat this floor above</button>
      <button type="button" class="btn btn-small btn-quiet" id="ed-blank" title="Take every block off every floor, keeping the cores and the corridors; Undo brings them back">Clear the plates</button>
      ${editor.applied ? `<button type="button" class="btn btn-small btn-quiet" id="ed-reset" title="Take the hand placement out of the option">Take it out of the option</button>` : ""}
      <span class="help">${editor.applied && !editor.dirty ? "Applied: Run the rules reproduces this placement; Save option as… keeps it." : (problems ? "The memo will list the problems as open items for the architect until they are fixed." : "Nothing is in the option until you apply.")}</span>
    </div>`;
  if (typed.label || typed.area || typed.open) {
    $(".ed-newprog", box).open = true; $("#ed-prog-label", box).value = typed.label; $("#ed-prog-area", box).value = typed.area;
    if (typed.focus === "ed-prog-label" || typed.focus === "ed-prog-area") $(`#${typed.focus}`, box).focus({ preventScroll: true });
  }
  wireEditor(box, { L, p, B, zs, scale, width, H });
  if (hadFocus && editor.sel != null) { const g = $(`.ed-zone[data-i="${editor.sel}"]`, box); if (g) g.focus({ preventScroll: true }); }
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
    w = row && row.unit ? unitW(row.each, row.min, d) : (area ? ceilM(area / d) : ceilM(6));
  }
  const z = { block: kind, x: p.x, y: p.y, w: r2(Math.min(w, p.width_m)), d: r2(Math.min(d, p.depth_m)) };
  if (kind === "other") z.label = label || "Other";
  return z;
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
  const rows = z.block === "core" ? [p.y] : [B.front, ...(B.rear != null ? [B.rear] : [])];
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
  const y = z.block === "core" ? p.y : (B.rear != null && pt[1] > B.corr + CORR / 2 ? B.rear : B.front);
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
      sel.w = Math.min(p.width_m, unitW(prog.gross_m2_each, prog.min_gross_m2_each, sel.d));
      sel.x = r2(Math.max(p.x, Math.min(sel.x, p.x + p.width_m - sel.w)));
    }
    commit(false);
    const hit = clashes(zs).has(editor.sel);
    setStatus(`The block is now ${blockName(sel).toLowerCase()}, ${sel.w} × ${sel.d} m.${hit ? " At that width it overlaps its neighbour: move one of them, or pull an edge." : ""}`, hit ? "busy" : "info");
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
    setStatus(spot ? `Moved to ${floorWords(Number(to))}, the first free place.` : `No room on ${floorWords(Number(to))} for a ${sel.w} × ${sel.d} m block: it sits where it was and overlaps; move or remove something.`, spot ? "info" : "busy");
  });
  const acc = $("#ed-acc", box);
  if (acc) acc.addEventListener("change", () => { snapshot(); if (acc.checked) sel.accessible = true; else delete sel.accessible; commit(false); });
}

function removeSel(zs) {
  if (editor.sel == null || !zs[editor.sel]) return;
  snapshot();
  const core = zs[editor.sel].block === "core";
  zs.splice(editor.sel, 1); editor.sel = null;
  commit(core);
}

function wireEditor(box, ctx) {
  const { L, p, B, zs, scale, width, H } = ctx;
  const svg = $(".ed-canvas", box);
  const m = mod();
  $$("[data-ed-level]", box).forEach(b => b.addEventListener("click", () => { editor.level = Number(b.dataset.edLevel); editor.sel = null; renderEditor(); }));

  // the grid
  const setBay = v => {
    if (!(v >= 3 && v <= 12)) { toast("A bay is between 3 and 12 m, wall to wall.", true); renderEditor(); return; }
    editor.bay = r2(v); renderEditor();
    setStatus(`The grid is a ${editor.bay} m bay, the walls on its ${r2(mod())} m module. The blocks on the plate stay where they are and take the grid as they are moved; Suggest a plan lays the program out on it.`, "info");
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
    if (spot) { z.x = spot[0]; z.y = spot[1]; }
    snapshot();
    zs.push(z); editor.sel = zs.length - 1;
    commit(kind === "core");
    if (!spot) setStatus(`No free room on ${floorWords(editor.level)} for a ${z.w} × ${z.d} m ${blockName(z).toLowerCase()}: it sits at the front-left corner and overlaps; move or remove something, or try another floor.`, "busy");
  };

  // the pointer in plate metres, or null off the canvas
  const toPlate = e => {
    const bb = svg.getBoundingClientRect(), k = bb.width / width;
    const sx = (e.clientX - bb.left) / k, sy = (e.clientY - bb.top) / k;
    if (sx < 0 || sy < 0 || sx > width || sy > H) return null;
    return [p.x + (sx - M) / scale, p.y + p.depth_m - (sy - M) / scale];
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
      const r = rectOf(pal.z, p, scale), hit = !clearOf(pal.z, zs.filter(o => o.block !== "corridor" && pal.z.block !== "corridor"))(pal.z.x, pal.z.y);
      ghost.innerHTML = `<rect x="${r.x.toFixed(1)}" y="${r.y.toFixed(1)}" width="${r.w.toFixed(1)}" height="${r.d.toFixed(1)}" fill="${ZONE_TONE[kind] || "#eee"}" fill-opacity="0.75" stroke="${hit ? "#c81e1e" : "#245f9c"}" stroke-width="1.6" stroke-dasharray="5 3"/>
        <text x="${(r.x + r.w / 2).toFixed(1)}" y="${(r.y + r.d / 2 + 3.5).toFixed(1)}" font-size="9.5" text-anchor="middle" fill="#1f2933">${h(zoneShort(pal.z))} · ${pal.z.w} m</text>`;
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
    setStatus(`${label}, ${fmtNum(area)} m², is in the program (option.layout.extra_programs); it joins the list once the engine has counted it. Drag it onto the plate from there.`, "ok");
    scheduleCheck();
  });

  $("#ed-blank", box).addEventListener("click", () => {
    snapshot();
    for (const k of Object.keys(editor.zones)) editor.zones[k] = editor.zones[k].filter(z => z.block === "core" || z.block === "corridor");
    editor.sel = null;
    commit(false);
    setStatus("Every block is off the plates; the cores and the corridors stay. Drag the program onto the plate, floor by floor; Undo brings the blocks back.", "info");
  });
  $("#ed-repeat", box).addEventListener("click", () => {
    snapshot();
    const above = L.floors.filter(fl => fl.level > editor.level);
    for (const fl of above) editor.zones[String(fl.level)] = JSON.parse(JSON.stringify(zs));
    commit(false);
    setStatus(`${floorName(editor.level)} is repeated on the ${above.length} floor${above.length === 1 ? "" : "s"} above. The program beside the plate says what that leaves to place, or puts over.`, "info");
  });
  $("#ed-apply", box).addEventListener("click", applyEditor);
  const reset = $("#ed-reset", box);
  if (reset) reset.addEventListener("click", () => {
    if (state.option && state.option.layout) { delete state.option.layout.zones; if (!Object.keys(state.option.layout).length) delete state.option.layout; }
    editor.applied = false;
    state.optionDirty = true; $("#option-dirty").hidden = false;
    refreshSummary("option");
    renderEditor();
    setStatus("The hand placement is out of the option: Run the rules lays the program out by itself again. The blocks stay here until the editor is closed.", "info");
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
  const select = i => {
    editor.sel = i;
    $$(".ed-zone", svg).forEach(g => g.classList.toggle("sel", Number(g.dataset.i) === i));
    if (i != null) { const g = $(`.ed-zone[data-i="${i}"]`, svg); if (g) { svg.insertBefore(g, ghost); g.focus({ preventScroll: true }); } }
    $("#ed-selbar", box).innerHTML = selBarHtml(L, zs);
    wireSel(box, ctx);
  };
  const redraw = i => {
    const bad = clashes(zs);
    $$(".ed-zone", svg).forEach(g => {
      const j = Number(g.dataset.i);
      g.classList.toggle("clash", bad.has(j));
      if (j === i) g.innerHTML = zoneInner(zs[j], rectOf(zs[j], p, scale));
    });
    $("#ed-selbar", box).innerHTML = selBarHtml(L, zs);
  };
  let drag = null;
  svg.addEventListener("pointerdown", e => {
    if (e.button) return;
    const g = e.target.closest(".ed-zone");
    if (!g) { if (editor.sel != null) select(null); return; }
    const i = Number(g.dataset.i);
    const mode = e.target.classList.contains("ed-handle-w") ? "w" : e.target.classList.contains("ed-handle-l") ? "l" : e.target.classList.contains("ed-handle-d") ? "d" : "move";
    if (editor.sel !== i) select(i);
    drag = { i, mode, x0: e.clientX, y0: e.clientY, z0: { ...zs[i] }, moved: false, k: svg.getBoundingClientRect().width / width };
    svg.setPointerCapture(e.pointerId); e.preventDefault();
  });
  svg.addEventListener("pointermove", e => {
    if (!drag) return;
    if (!drag.moved) {
      if (Math.hypot(e.clientX - drag.x0, e.clientY - drag.y0) < 3) return;
      drag.moved = true; editor.dragging = true; snapshot(); svg.classList.add("dragging");
    }
    const dx = (e.clientX - drag.x0) / drag.k / scale, dy = -(e.clientY - drag.y0) / drag.k / scale;   // the screen's down is toward the street
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
    if (!d.moved) { if (editor.pendingRender) renderEditor(); return; }
    const z = zs[d.i], core = z && z.block === "core";
    // a block dropped back on the program leaves the plate
    const under = e.type === "pointerup" && d.mode === "move" ? document.elementFromPoint(e.clientX, e.clientY) : null;
    if (under && under.closest(".ed-program")) { zs.splice(d.i, 1); editor.sel = null; }
    commit(core);
  };
  svg.addEventListener("pointerup", end);
  svg.addEventListener("pointercancel", end);

  // keyboard: the arrows move the selected block a module along the plate and 0.5 m across it (shift: a bay,
  // 2 m); Delete removes it; Ctrl+Z undoes
  svg.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); undo(); return; }
    if (editor.sel == null || !zs[editor.sel]) return;
    const z = zs[editor.sel], k = e.key;
    if (k === "Delete" || k === "Backspace") { e.preventDefault(); removeSel(zs); return; }
    const sx = e.shiftKey ? editor.bay : m, sy = e.shiftKey ? 2 : 0.5;
    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(k)) return;
    e.preventDefault(); snapshot();
    if (k === "ArrowLeft") z.x = r2(Math.max(p.x, gx(z.x - sx)));
    else if (k === "ArrowRight") z.x = r2(Math.min(p.x + p.width_m - z.w, gx(z.x + sx)));
    else if (k === "ArrowUp") z.y = r2(Math.min(p.y + p.depth_m - z.d, z.y + sy));   // up on screen is away from the street
    else z.y = r2(Math.max(p.y, z.y - sy));
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
  return withLevels(opt);
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
   under it, and the program left to place is dragged onto it (or Suggest a plan lays it out again). */
async function addLevel() {
  const L = editor.result || state.run.layout, cap = L.capacity;
  if (!cap || (cap.fsr_limit != null && cap.levels_room < 1)) return;
  snapshot();
  const top = L.floors.length - 1, lv = top + 1;
  editor.added = (editor.added || 0) + 1;
  editor.zones[String(lv)] = (editor.zones[String(top)] || []).filter(z => z.block === "core" || z.block === "corridor").map(z => ({ ...z }));
  editor.sel = null; editor.dirty = true;
  clearTimeout(editor.timer);
  await checkPlacement();
  const now = editor.result;
  if (now.floors[lv]) { editor.level = lv; renderEditor(); }
  const c = now.capacity || {}, left = programTracker(now, editor.zones).unitsLeft;
  setStatus(`${floorName(lv)} is added: ${now.floors.length} storeys, FSR ${Number(c.fsr).toFixed(2)}${c.fsr_limit != null ? ` of ${Number(c.fsr_limit).toFixed(2)} (${c.limit_from})` : ""}. It has the cores and the corridor of the level under it${left ? `; ${left} units are left to place: drag them on, or Suggest a plan lays the program out over all ${now.floors.length} levels` : ""}. Apply writes the storeys, floor area and height into the option.`, "ok");
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
  setStatus(`${floorName(top)} is taken off again, with its blocks; Undo brings it back.`, "info");
}

/* the other sheets follow the check */
function updateSheets(res) {
  const fig = $('.figure.sheet[data-sheet="plans"]');
  if (!fig || !res.sheets) return;
  const ax = $('.sheet-body[data-view="axon"]', fig); if (ax) ax.innerHTML = res.sheets.axon || "";
  const pl = $('.sheet-body[data-view="plans"]', fig); if (pl) pl.innerHTML = res.sheets.plans || "";
  for (const b of $$(".figure.sheet .sheet-body")) {
    const card = b.closest(".figure"); const eb = card && $(".eyebrow", card); const t = eb ? eb.textContent : "";
    if (/Stacking/.test(t)) b.innerHTML = res.sheets.stacking || ""; else if (/elevations/i.test(t)) b.innerHTML = res.sheets.elevations || ""; else if (/site plan/i.test(t)) b.innerHTML = res.sheets["site-plan"] || "";
  }
}

async function ask(opt) {
  const res = await postJSON("/api/layout", { site: state.site, option: opt, as_of: $("#as-of").value || todayISO() });
  // the plate a level adds, as the engine has it (a run read from disk may predate the figure)
  if (!editor.added && res.layout && res.layout.capacity) editor.base.plate = res.layout.capacity.plate_m2;
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
async function suggestPlan(first) {
  if (!editor.open || !state.site || !state.option) return;
  const cores = editor.coreMoved ? coresNow() : [];   // the solver's own core, on the grid, until one is moved by hand
  const seq = editor.seq = (editor.seq || 0) + 1;
  clearTimeout(editor.timer);
  setBusy(true);
  try {
    const res = await ask(optionFor(cores.length ? { cores } : {}));
    if (seq !== editor.seq) return;
    if (!first) snapshot();
    editor.result = res.layout; editor.zones = zonesFromLayout(res.layout); editor.sel = null; editor.dirty = true;
    updateSheets(res);
    const L = res.layout, left = L.units_total - L.units_placed;
    setStatus(`${first ? "A suggested plan to start from" : "Suggested plan"}, on a ${editor.bay} m bay${cores.length ? ` round your core${cores.length === 1 ? "" : "s"}` : ""}: ${L.units_placed} of ${L.units_total} units placed${left > 0 ? `; ${left} did not fit and stay in the program as left to place` : ""}. Drag to adjust${first ? "" : "; Undo brings back what was there"}.`, left > 0 ? "busy" : "ok");
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
  state.option.layout = Object.assign({}, state.option.layout || {}, { zones: JSON.parse(JSON.stringify(editor.zones)), grid: { bay_m: editor.bay, divide: editor.divide } });
  state.optionDirty = true; $("#option-dirty").hidden = false;
  editor.applied = true; editor.dirty = false;
  renderEditor();
  refreshSummary("option");
  const n = Object.values(editor.zones).reduce((t, a) => t + a.length, 0);
  setStatus(`${n} blocks on ${Object.keys(editor.zones).length} floors written into the option as layout.zones, with the ${editor.bay} m grid. ${added ? `The option is now ${state.option.storeys} storeys${state.option.gfa_m2 != null ? `, ${fmtNum(state.option.gfa_m2)} m²` : ""}: the memo on screen is from before, so run the rules again.` : "Run the rules to make the memo from them;"} Save option as… keeps them.`, "ok");
}
