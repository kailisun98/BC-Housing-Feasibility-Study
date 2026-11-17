/* The block editor (architect mode, FIG 03), loaded on first use: the same blocks on the same plates, by hand.
   The architect drags the blocks the solver placed, or adds and removes them, one floor at a time, in the plan;
   the engine measures every move (POST /api/layout, or the engine in the browser) and says what broke and
   which rules still hold; the other sheets redraw from the same check. Apply writes the placement into the
   option (`layout.zones`), so Run the rules reproduces it and the memo says it was placed by hand. */

import { $, $$, fmtNum, h, pill, setStatus, toast, todayISO } from "../core/util.js";
import { editor, state } from "../core/state.js";
import { postJSON } from "../core/api.js";
import { refreshSummary } from "../schedule.js";
import { tidyOption } from "../files.js";
import { egressLine } from "../memo/answers.js";

const EDIT_BLOCKS = [["studio", "Studio"], ["one_bed", "One-bedroom"], ["two_bed", "Two-bedroom"], ["three_bed_plus", "Three-bedroom+"], ["non_residential", "Non-residential"], ["amenity", "Amenity"], ["services", "Services, bicycles"], ["core", "Core"], ["corridor", "Corridor"]];

const ZONE_TONE = { studio: "#dbe9f8", one_bed: "#b9d4f0", two_bed: "#8fb8e3", three_bed_plus: "#6b9fd4", corridor: "#f4f4f2", core: "#c9c9c5", services: "#e2e2df", amenity: "#f6e7c1", non_residential: "#f0cf9a", other: "#e6dfd0" };

const ZONE_SHORT = { studio: "st", one_bed: "1b", two_bed: "2b", three_bed_plus: "3b", corridor: "corridor", core: "core", services: "services", amenity: "amenity", non_residential: "non-res" };

const zoneShort = z => z.block === "other" ? String(z.label || "other").slice(0, 12).toLowerCase() : (ZONE_SHORT[z.block] || z.block);

/* the grid the blocks snap to in the editor: fine (0.1 m) or a planning module the architect chooses (16 Nov 2026) */
const GRIDS = [[0.1, "0.1 m (fine)"], [0.5, "0.5 m"], [1, "1 m"], [1.5, "1.5 m"], [3, "3 m"], [6, "6 m"]];

function zonesFromLayout(L) {
  const out = {};
  for (const fl of L.floors) out[String(fl.level)] = fl.zones.filter(z => z.block !== "spare").map(z => ({ block: z.block, x: z.x, y: z.y, w: z.w, d: z.d, ...(z.accessible ? { accessible: true } : {}), ...(z.block === "other" ? { label: z.label } : {}) }));
  return out;
}

/* What the program asks for against what the editor has placed on every floor: one row per block, with what is
   left to place; the architect's own programs (option.layout.extra_programs) are rows too. Pure. */
function programTracker(L, zones) {
  const all = Object.values(zones || {}).flat();
  const rows = (L.program || []).map(b => {
    const unit = ["studio", "one_bed", "two_bed", "three_bed_plus"].includes(b.key);
    const mine = all.filter(z => b.key === "other" ? (z.block === "other" && String(z.label || "").trim().toLowerCase() === String(b.label).trim().toLowerCase()) : z.block === b.key);
    const placedArea = mine.reduce((t, z) => t + z.w * z.d, 0);
    return unit ? { key: b.key, label: b.label, unit: true, need: b.count, placed: mine.length, left: b.count - mine.length, each: b.gross_m2_each }
      : { key: b.key, label: b.label, unit: false, need: b.area_m2, placed: Math.round(placedArea), left: Math.round(b.area_m2 - placedArea) };
  });
  const cores = all.filter(z => z.block === "core").length, corridors = all.filter(z => z.block === "corridor").length;
  return { rows, cores, corridors, done: rows.every(r => r.left <= (r.unit ? 0 : 1)) };
}

export function openEditor() {
  const run = state.run;
  if (!run || !run.layout) return;
  const fromOption = state.option && state.option.layout && state.option.layout.zones;
  editor.open = true; editor.level = 0; editor.sel = null; editor.dirty = false; editor.applied = !!fromOption;
  editor.zones = JSON.parse(JSON.stringify(fromOption || zonesFromLayout(run.layout)));
  editor.result = run.layout;
  const fig = $('.figure.sheet[data-sheet="plans"]');
  $$(".sheet-body", fig).forEach(x => { x.hidden = true; });
  $("#edit-blocks").setAttribute("aria-expanded", "true");
  $("#edit-blocks").textContent = "Close the editor";
  $("#sheet-editor").hidden = false;
  renderEditor();
  setStatus("Block editor: drag a block, pull its right or bottom edge to resize, add or remove blocks; the engine checks every move. Apply writes the placement into the option.", "info");
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

function renderEditor() {
  const box = $("#sheet-editor");
  const L = editor.result || state.run.layout, p = L.plate;
  const zs = editor.zones[String(editor.level)] || (editor.zones[String(editor.level)] = []);
  const width = Math.max(320, box.clientWidth || 600) - 4;
  const scale = (width - 40) / p.width_m;
  const H = p.depth_m * scale + 40;
  // the street at the bottom, as on every plan in the set: a zone's y runs from the street side, so it is drawn
  // from its far edge down (15 Nov 2026)
  const rect = z => { const x = 20 + (z.x - p.x) * scale, y = 20 + (p.depth_m - (z.y - p.y) - z.d) * scale, w = Math.max(1, z.w * scale), d = Math.max(1, z.d * scale); return { x, y, w, d }; };
  const floorsBtns = L.floors.map(fl => `<button type="button" class="segbtn" data-ed-level="${fl.level}" aria-pressed="${fl.level === editor.level}">${h(fl.level === 0 ? "Ground" : `L${fl.level + 1}`)}</button>`).join("");
  const sel = editor.sel != null ? zs[editor.sel] : null;
  const floorChecks = (L.geometry || []).filter(g => g.level === editor.level);
  const problems = (L.geometry || []).length;
  // a unit drawn well over the area the program carries for it is flagged on the selection line
  const over = (() => {
    if (!sel) return "";
    const prog = (L.program || []).find(b => b.key === sel.block);
    const gross = prog && prog.gross_m2_each;
    if (!gross) return "";
    const a = sel.w * sel.d;
    return a > gross * 1.15 ? ` <span class="warn-text">· ${fmtNum(Math.round(a - gross))} m² over the ${fmtNum(Math.round(gross))} m² the program carries</span>` : (a < gross * 0.95 ? ` <span class="warn-text">· ${fmtNum(Math.round(gross - a))} m² under the ${fmtNum(Math.round(gross))} m² the program carries</span>` : "");
  })();
  const svgZones = zs.map((z, i) => {
    const r = rect(z);
    const isSel = i === editor.sel;
    return `<g class="ed-zone${isSel ? " sel" : ""}" data-i="${i}" tabindex="0" role="button" aria-label="${h(zoneShort(z))} at ${z.x}, ${z.y} m">
      <rect x="${r.x.toFixed(1)}" y="${r.y.toFixed(1)}" width="${r.w.toFixed(1)}" height="${r.d.toFixed(1)}" fill="${ZONE_TONE[z.block] || "#eee"}" stroke="${isSel ? "#245f9c" : "#5f6672"}" stroke-width="${isSel ? 2 : 0.8}"/>
      ${z.accessible ? `<circle cx="${(r.x + 7).toFixed(1)}" cy="${(r.y + 7).toFixed(1)}" r="3.2" fill="#245f9c"/>` : ""}
      ${r.w > 24 && r.d > 12 ? `<text x="${(r.x + r.w / 2).toFixed(1)}" y="${(r.y + r.d / 2 + 3.5).toFixed(1)}" font-size="9.5" text-anchor="middle" fill="#1f2933">${h(zoneShort(z))}</text>` : ""}
      ${isSel ? `<rect class="ed-handle ed-handle-w" x="${(r.x + r.w - 4).toFixed(1)}" y="${(r.y + r.d / 2 - 6).toFixed(1)}" width="8" height="12" fill="#245f9c"/><rect class="ed-handle ed-handle-d" x="${(r.x + r.w / 2 - 6).toFixed(1)}" y="${(r.y - 4).toFixed(1)}" width="12" height="8" fill="#245f9c"/>` : ""}
    </g>`;
  }).join("");
  // the grid, drawn faint when a module is chosen, so the architect sees what the blocks snap to
  const g = editor.grid || 0.1;
  const gridLines = g >= 0.5 ? (() => {
    let s = "";
    for (let x = 0; x <= p.width_m + 1e-6; x += g) s += `<line x1="${(20 + x * scale).toFixed(1)}" y1="20" x2="${(20 + x * scale).toFixed(1)}" y2="${(20 + p.depth_m * scale).toFixed(1)}"/>`;
    for (let y = 0; y <= p.depth_m + 1e-6; y += g) s += `<line x1="20" y1="${(20 + y * scale).toFixed(1)}" x2="${(20 + p.width_m * scale).toFixed(1)}" y2="${(20 + y * scale).toFixed(1)}"/>`;
    return `<g stroke="#c9d1da" stroke-width="0.5" opacity="0.7">${s}</g>`;
  })() : "";
  // the program tracker: what is still to place, each row a button that adds that block to this floor
  const tr = programTracker(L, editor.zones);
  const extras = ((state.option && state.option.layout && state.option.layout.extra_programs) || []);
  const addOpts = EDIT_BLOCKS.map(([k, l]) => `<option value="${k}">${h(l)}</option>`).join("") + extras.map(e => `<option value="other:${h(e.label)}">${h(e.label)} (yours)</option>`).join("");
  const egF = L.egress && (L.egress.floors || []).find(f => f.level === editor.level);
  box.innerHTML = `
    <div class="ed-bar">
      <div class="seg" role="group" aria-label="Floor">${floorsBtns}</div>
      <label class="field inline"><span class="label">Add</span><select id="ed-add"><option value="">a block…</option>${addOpts}</select></label>
      <label class="field inline"><span class="label">Grid</span><select id="ed-grid" title="What the blocks snap to when moved, resized or added">${GRIDS.map(([v, l]) => `<option value="${v}"${Math.abs(v - g) < 1e-9 ? " selected" : ""}>${h(l)}</option>`).join("")}</select></label>
      ${sel ? `<span class="ed-sel">${h(sel.block === "other" ? (sel.label || "Other") : (EDIT_BLOCKS.find(([k]) => k === sel.block)?.[1] || sel.block))} · ${h(sel.w)} × ${h(sel.d)} m, ${h(fmtNum(Math.round(sel.w * sel.d)))} m²${over}
        <label class="field inline"><span class="label">to floor</span><select id="ed-move">${L.floors.map(fl => `<option value="${fl.level}"${fl.level === editor.level ? " selected" : ""}>${h(fl.level === 0 ? "Ground" : `L${fl.level + 1}`)}</option>`).join("")}</select></label>
        ${sel.block in ZONE_TONE && ["studio", "one_bed", "two_bed", "three_bed_plus"].includes(sel.block) ? `<label class="ed-acc"><input type="checkbox" id="ed-acc"${sel.accessible ? " checked" : ""}> accessible</label>` : ""}
        <button type="button" class="btn btn-small btn-quiet" id="ed-del">Remove</button></span>` : `<span class="help">Click a block to select it; drag to move, pull the handles to resize.</span>`}
    </div>
    <svg class="ed-canvas" viewBox="0 0 ${width} ${H}" width="${width}" height="${H}" role="application" aria-label="Block editor, ${h(L.floors[editor.level].name)}">
      <rect x="20" y="20" width="${(p.width_m * scale).toFixed(1)}" height="${(p.depth_m * scale).toFixed(1)}" fill="#f4f4f2" stroke="#1f2933" stroke-width="1.2"/>
      ${gridLines}
      <text x="${(20 + p.width_m * scale / 2).toFixed(1)}" y="${(H - 6).toFixed(1)}" font-size="10" text-anchor="middle" fill="#5f6672">street · ${h(p.width_m)} m · blocks snap to the ${g >= 0.5 ? `${g} m grid, ` : ""}other blocks' edges and the corridor</text>
      ${svgZones}
    </svg>
    <div class="ed-status">
      ${editor.busy ? `<span class="help">Checking…</span>` : ""}
      ${floorChecks.length ? `<ul class="finding-list">${floorChecks.map(g => `<li>${pill("fail")}<span>${h(g.note)}</span></li>`).join("")}</ul>` : `<span class="help">${editor.result ? `Nothing broken on this floor. ${(L.geometry || []).length ? `${L.geometry.length} on other floors.` : ""}` : ""}</span>`}
      ${egF ? `<span class="help">${pill(egF.status)} Exits on this floor: ${h(egressLine(egF))}${egF.notes && egF.notes.length ? ` <span class="cont">· ${h(egF.notes[0])}</span>` : ""}</span>` : ""}
      <span class="help">${h(L.units_placed)} of ${h(L.units_total)} units placed${(L.shortfall || []).length ? `; missing: ${h(L.shortfall.map(s => `${s.units ? `${s.units} ` : ""}${s.label.toLowerCase()}`).join(", "))}` : ""} · ${h((L.adjacencies || []).filter(c => c.status === "pass").length)} rules hold, ${h((L.adjacencies || []).filter(c => c.status === "conditional").length)} conditional</span>
    </div>
    <details class="ed-tracker"${tr.done ? "" : " open"}>
      <summary><b>Program left to place</b> <span class="cont">· ${tr.done ? "everything placed" : `${tr.rows.filter(r => r.left > (r.unit ? 0 : 1)).length} of ${tr.rows.length} blocks short`} · ${tr.cores} core${tr.cores === 1 ? "" : "s"}, ${tr.corridors} corridor${tr.corridors === 1 ? "" : "s"} on all floors</span></summary>
      <table class="plain ed-track"><thead><tr><th>Block</th><th>Program</th><th>Placed</th><th>Left</th><th></th></tr></thead><tbody>
        ${tr.rows.map(r => `<tr class="${r.left > (r.unit ? 0 : 1) ? "short" : (r.left < (r.unit ? 0 : -1) ? "over" : "ok")}"><td>${h(r.label)}</td><td class="num">${r.unit ? `${r.need} × ${h(fmtNum(Math.round(r.each)))} m²` : `${h(fmtNum(Math.round(r.need)))} m²`}</td><td class="num">${r.unit ? r.placed : `${h(fmtNum(r.placed))} m²`}</td><td class="num">${r.unit ? (r.left > 0 ? r.left : (r.left < 0 ? `${-r.left} over` : "—")) : (r.left > 1 ? `${h(fmtNum(r.left))} m²` : (r.left < -1 ? `${h(fmtNum(-r.left))} m² over` : "—"))}</td><td><button type="button" class="btn btn-small btn-quiet" data-ed-track="${h(r.key)}" data-ed-label="${h(r.label)}" title="Add one to this floor">+ here</button></td></tr>`).join("")}
      </tbody></table>
      <div class="ed-newprog"><span class="label">Add a program of your own</span>
        <input type="text" id="ed-prog-label" placeholder="e.g. Childcare" maxlength="40" aria-label="Program name">
        <input type="number" id="ed-prog-area" placeholder="m²" min="1" step="1" aria-label="Program area in square metres">
        <button type="button" class="btn btn-small" id="ed-prog-add">Add to the program</button>
        <span class="help">It joins the tracker and the option (layout.extra_programs); place it with + here.</span>
      </div>
    </details>
    <div class="form-actions">
      <button type="button" class="btn btn-primary btn-small" id="ed-apply"${editor.dirty || !editor.applied ? "" : " disabled"}>${problems ? `Apply with ${problems} problem${problems === 1 ? "" : "s"}` : "Apply to the option"}</button>
      <button type="button" class="btn btn-small btn-quiet" id="ed-reset">Back to the solver's</button>
      <button type="button" class="btn btn-small btn-quiet" id="ed-blank" title="Clear every floor and place the blocks yourself, from the tracker">Start from a blank plate</button>
      <span class="help">${editor.applied && !editor.dirty ? "Applied: Run the rules reproduces this placement; Save option as… keeps it." : (problems ? "The memo will list the problems as open items for the architect until they are fixed." : "Nothing is in the option until you apply.")}</span>
    </div>`;
  wireEditor(box, scale, p);
}

/* A block of this kind sized for the program: units at the plate's unit depth and their gross area, a corridor
   the plate's width, a core a bay wide and the plate deep, anything else about 8 m deep. Pure. */
function newBlock(kind, label, L, p) {
  const strip = L.plate.unit_depth_m;
  const prog = (L.program || []).find(b => kind === "other" ? (b.key === "other" && b.label === label) : b.key === kind);
  const unit = ["studio", "one_bed", "two_bed", "three_bed_plus"].includes(kind);
  const d = unit ? strip : (kind === "corridor" ? 1.8 : (kind === "core" ? p.depth_m : Math.min(8, p.depth_m)));
  const area = prog ? (prog.gross_m2_each || prog.area_m2) : null;
  const w = area ? Math.round(area / d * 10) / 10 : (kind === "corridor" ? p.width_m : (kind === "core" ? 7 : 8));
  const z = { block: kind, x: p.x, y: p.y, w: Math.min(w, p.width_m), d: Math.min(d, p.depth_m) };
  if (kind === "other") z.label = label || "Other";
  return z;
}

function wireEditor(box, scale, p) {
  $$("[data-ed-level]", box).forEach(b => b.addEventListener("click", () => { editor.level = Number(b.dataset.edLevel); editor.sel = null; renderEditor(); }));
  const zs = editor.zones[String(editor.level)];
  const L = editor.result || state.run.layout;
  const strip = L.plate.unit_depth_m;
  // a block added lands in the first free spot on this floor, sized for the program and snapped to the grid
  const addBlock = (kind, label) => {
    const z = newBlock(kind, label, L, p);
    const spot = freeSpot(zs, z, p, strip);
    if (spot) { z.x = spot[0]; z.y = spot[1]; }
    const g = editor.grid || 0.1;
    z.w = Math.max(g, Math.round(z.w / g) * g); z.d = Math.max(g, Math.round(z.d / g) * g);
    z.w = Math.round(Math.min(z.w, p.width_m) * 100) / 100; z.d = Math.round(Math.min(z.d, p.depth_m) * 100) / 100;
    zs.push(z);
    editor.sel = zs.length - 1; editor.dirty = true; renderEditor(); scheduleCheck();
    if (!spot) setStatus(`No free room on this floor for a ${z.w} × ${z.d} m block: it sits at the front-left corner and overlaps; move or remove something.`, "busy");
  };
  $("#ed-add", box).addEventListener("change", e => {
    const v = e.target.value; if (!v) return;
    if (v.startsWith("other:")) addBlock("other", v.slice(6)); else addBlock(v, null);
  });
  $$("[data-ed-track]", box).forEach(b => b.addEventListener("click", () => addBlock(b.dataset.edTrack, b.dataset.edLabel)));
  $("#ed-grid", box).addEventListener("change", e => { editor.grid = Number(e.target.value) || 0.1; renderEditor(); });
  $("#ed-prog-add", box).addEventListener("click", () => {
    const label = ($("#ed-prog-label", box).value || "").trim(), area = Number($("#ed-prog-area", box).value);
    if (!label || !(area > 0)) { toast("A program needs a name and an area in m².", true); return; }
    if (!state.option) return;
    state.option.layout = Object.assign({}, state.option.layout || {});
    const list = (state.option.layout.extra_programs = (state.option.layout.extra_programs || []).filter(x => x.label.toLowerCase() !== label.toLowerCase()));
    list.push({ label, area_m2: area });
    state.optionDirty = true; $("#option-dirty").hidden = false;
    editor.dirty = true;
    setStatus(`${label}, ${fmtNum(area)} m², is in the program (option.layout.extra_programs). Place it with + here; the engine counts it from the next check.`, "ok");
    scheduleCheck();
  });
  // clearing every floor is asked on the page itself (no browser dialog): the first click arms the button, the second clears
  $("#ed-blank", box).addEventListener("click", e => {
    if (!editor.blankArmed) {
      editor.blankArmed = true;
      e.target.textContent = "Clear every floor?"; e.target.classList.add("btn-primary");
      setStatus("Click again to clear every floor; the solver's blocks come back with Back to the solver's.", "busy");
      return;
    }
    editor.blankArmed = false;
    for (const k of Object.keys(editor.zones)) editor.zones[k] = [];
    editor.sel = null; editor.dirty = true; editor.blank = true;
    renderEditor(); scheduleCheck();
    setStatus("A blank plate on every floor. Pick a grid, then add the blocks from the tracker: a corridor and a core on each floor first, then the units; the engine checks each move.", "info");
  });
  const sel = editor.sel != null ? zs[editor.sel] : null;
  if (sel) {
    $("#ed-del", box).addEventListener("click", () => { zs.splice(editor.sel, 1); editor.sel = null; editor.dirty = true; renderEditor(); scheduleCheck(); });
    $("#ed-move", box).addEventListener("change", e => {
      const to = String(e.target.value); if (to === String(editor.level)) return;
      zs.splice(editor.sel, 1);
      const target = (editor.zones[to] = editor.zones[to] || []);
      // the block lands in the first free run on the target floor, not on top of what is there (15 Nov 2026)
      const spot = freeSpot(target, sel, p, strip);
      if (spot) { sel.x = spot[0]; sel.y = spot[1]; }
      target.push(sel);
      editor.level = Number(to); editor.sel = target.length - 1; editor.dirty = true; renderEditor(); scheduleCheck();
      setStatus(spot ? `Moved to ${to === "0" ? "the ground floor" : `L${Number(to) + 1}`} at ${sel.x}, ${sel.y} m, the first free run.` : `No room on ${to === "0" ? "the ground floor" : `L${Number(to) + 1}`} for a ${sel.w} × ${sel.d} m block: it sits where it was and overlaps; move or remove something.`, spot ? "info" : "busy");
    });
    const acc = $("#ed-acc", box);
    if (acc) acc.addEventListener("change", () => { if (acc.checked) sel.accessible = true; else delete sel.accessible; editor.dirty = true; renderEditor(); scheduleCheck(); });
  }
  $("#ed-apply", box).addEventListener("click", applyEditor);
  $("#ed-reset", box).addEventListener("click", () => {
    if (state.option && state.option.layout) { delete state.option.layout.zones; if (!Object.keys(state.option.layout).length) delete state.option.layout; }
    editor.applied = false; editor.dirty = false; editor.sel = null;
    state.optionDirty = true; $("#option-dirty").hidden = false;
    checkPlacement(true);
  });
  // dragging and resizing, by pointer; the plate's edges are the limit; 0.1 m steps, and edges snap to the other
  // blocks' edges and to the corridor faces within 0.4 m, so a hand wobble does not become an overlap
  const svg = $(".ed-canvas", box);
  let drag = null;
  // the grid: 0.1 m, or the module the architect chose; a snap to another block's edge wins within SNAP
  const g = editor.grid || 0.1;
  const snap = v => Math.round(Math.round(v / g) * g * 100) / 100;
  const toM = (dx, dy) => [dx / scale, -dy / scale];   // the screen's down is the plate's toward-the-street
  const SNAP = Math.max(0.4, g / 2);
  const xStops = i => { const s = [p.x, p.x + p.width_m]; zs.forEach((o, j) => { if (j !== i) { s.push(o.x, o.x + o.w); } }); return s; };
  const yStops = i => { const s = [p.y, p.y + p.depth_m, p.y + strip, p.y + p.depth_m - strip]; zs.forEach((o, j) => { if (j !== i) { s.push(o.y, o.y + o.d); } }); return s; };
  const snapTo = (v, stops) => { let best = v; for (const s of stops) if (Math.abs(s - v) < SNAP && Math.abs(s - v) < Math.abs(best - v) + 1e-9) best = s; return best; };
  svg.addEventListener("pointerdown", e => {
    const g = e.target.closest(".ed-zone"); if (!g) { editor.sel = null; renderEditor(); return; }
    const i = Number(g.dataset.i);
    if (editor.sel !== i) { editor.sel = i; renderEditor(); const g2 = $(`.ed-zone[data-i="${i}"]`, $("#sheet-editor")); if (g2) g2.focus({ preventScroll: true }); return; }
    const z = zs[i];
    const mode = e.target.classList.contains("ed-handle-w") ? "w" : e.target.classList.contains("ed-handle-d") ? "d" : "move";
    drag = { i, mode, x0: e.clientX, y0: e.clientY, z0: { ...z } };
    svg.setPointerCapture(e.pointerId); e.preventDefault();
  });
  svg.addEventListener("pointermove", e => {
    if (!drag) return;
    const [dx, dy] = toM(e.clientX - drag.x0, e.clientY - drag.y0);
    const z = zs[drag.i], z0 = drag.z0;
    if (drag.mode === "move") {
      let nx = z0.x + dx, ny = z0.y + dy;
      // snap the left or right edge, the near or far edge, whichever is closest to a stop
      const xs = xStops(drag.i), ys = yStops(drag.i);
      const lx = snapTo(nx, xs), rx = snapTo(nx + z.w, xs) - z.w;
      nx = Math.abs(lx - nx) <= Math.abs(rx - nx) ? lx : rx;
      const ly = snapTo(ny, ys), fy = snapTo(ny + z.d, ys) - z.d;
      ny = Math.abs(ly - ny) <= Math.abs(fy - ny) ? ly : fy;
      z.x = snap(Math.max(p.x, Math.min(p.x + p.width_m - z.w, nx)));
      z.y = snap(Math.max(p.y, Math.min(p.y + p.depth_m - z.d, ny)));
    } else if (drag.mode === "w") {
      z.w = snap(Math.max(1, Math.min(p.x + p.width_m - z.x, snapTo(z.x + z0.w + dx, xStops(drag.i)) - z.x)));
    } else {
      // the depth handle is on the far edge: pulling it away from the street deepens the block
      z.d = snap(Math.max(1, Math.min(p.y + p.depth_m - z.y, snapTo(z.y + z0.d + dy, yStops(drag.i)) - z.y)));
    }
    const g = $(`.ed-zone[data-i="${drag.i}"]`, svg);
    const r = g.querySelector("rect");
    r.setAttribute("x", (20 + (z.x - p.x) * scale).toFixed(1)); r.setAttribute("y", (20 + (p.depth_m - (z.y - p.y) - z.d) * scale).toFixed(1));
    r.setAttribute("width", Math.max(1, z.w * scale).toFixed(1)); r.setAttribute("height", Math.max(1, z.d * scale).toFixed(1));
  });
  const end = () => { if (!drag) return; drag = null; editor.dirty = true; renderEditor(); scheduleCheck(); };
  for (const ev of ["pointerup", "pointercancel", "lostpointercapture"]) svg.addEventListener(ev, end);
  // keyboard: arrows move the selected block 0.5 m; Delete removes it
  svg.addEventListener("keydown", e => {
    if (editor.sel == null) return;
    const z = zs[editor.sel];
    const step = e.shiftKey ? Math.max(2, g * 2) : Math.max(0.5, g);
    const k = e.key;
    if (k === "ArrowLeft") z.x = snap(Math.max(p.x, z.x - step)); else if (k === "ArrowRight") z.x = snap(Math.min(p.x + p.width_m - z.w, z.x + step));
    else if (k === "ArrowUp") z.y = snap(Math.min(p.y + p.depth_m - z.d, z.y + step)); else if (k === "ArrowDown") z.y = snap(Math.max(p.y, z.y - step));   // up on screen is away from the street
    else if (k === "Delete" || k === "Backspace") { zs.splice(editor.sel, 1); editor.sel = null; }
    else return;
    e.preventDefault(); editor.dirty = true; renderEditor(); scheduleCheck();
    const g2 = $(`.ed-zone[data-i="${editor.sel}"]`, $("#sheet-editor")); if (g2) g2.focus({ preventScroll: true });
  });
}

function scheduleCheck() {
  clearTimeout(editor.timer);
  editor.timer = setTimeout(() => checkPlacement(false), 350);
}

/* The first place on a floor where a block of this size overlaps nothing but a corridor: the street strip first,
   then the rear strip, then anywhere, scanned in 0.5 m steps; null when there is none. Pure. */
function freeSpot(zones, z, p, strip) {
  const others = zones.filter(o => o !== z && o.block !== "corridor");
  const clear = (x, y) => others.every(o => x + z.w <= o.x + 1e-6 || o.x + o.w <= x + 1e-6 || y + z.d <= o.y + 1e-6 || o.y + o.d <= y + 1e-6);
  const rows = [p.y, p.y + p.depth_m - z.d];
  for (let y = p.y; y <= p.y + p.depth_m - z.d + 1e-6; y += 0.5) if (!rows.some(r => Math.abs(r - y) < 1e-6)) rows.push(y);
  for (const y of rows) {
    if (y < p.y || y + z.d > p.y + p.depth_m + 1e-6) continue;
    for (let x = p.x; x <= p.x + p.width_m - z.w + 1e-6; x += 0.5) {
      if (clear(x, y)) return [Math.round(x * 10) / 10, Math.round(y * 10) / 10];
    }
  }
  return null;
}

/* The engine measures the placement: the option with these zones is read under the rules exactly as a run would
   read it; the result redraws the editor's status and the other sheets. */
async function checkPlacement(fromSolver) {
  if (!editor.open || !state.site || !state.option) return;
  const opt = JSON.parse(JSON.stringify(tidyOption(JSON.parse(JSON.stringify(state.option)))));
  if (fromSolver) { if (opt.layout) delete opt.layout.zones; }
  else { opt.layout = Object.assign({}, opt.layout || {}, { zones: editor.zones }); }
  editor.busy = true; renderEditor();
  try {
    const res = await postJSON("/api/layout", { site: state.site, option: opt, as_of: $("#as-of").value || todayISO() });
    editor.result = res.layout;
    if (fromSolver) editor.zones = zonesFromLayout(res.layout);
    // the other sheets follow the check
    const fig = $('.figure.sheet[data-sheet="plans"]');
    if (fig && res.sheets) {
      const ax = $('.sheet-body[data-view="axon"]', fig); if (ax) ax.innerHTML = res.sheets.axon || "";
      const pl = $('.sheet-body[data-view="plans"]', fig); if (pl) pl.innerHTML = res.sheets.plans || "";
      const bodies = $$(".figure.sheet .sheet-body");
      for (const b of bodies) {
        const card = b.closest(".figure"); const eb = card && $(".eyebrow", card); const t = eb ? eb.textContent : "";
        if (/Stacking/.test(t)) b.innerHTML = res.sheets.stacking || ""; else if (/elevations/i.test(t)) b.innerHTML = res.sheets.elevations || ""; else if (/site plan/i.test(t)) b.innerHTML = res.sheets["site-plan"] || "";
      }
    }
  } catch (e) {
    toast(`The engine could not check the placement: ${e.message}`, true);
  } finally {
    editor.busy = false; renderEditor();
  }
}

function applyEditor() {
  if (!state.option) return;
  state.option.layout = Object.assign({}, state.option.layout || {}, { zones: JSON.parse(JSON.stringify(editor.zones)) });
  state.optionDirty = true; $("#option-dirty").hidden = false;
  editor.applied = true; editor.dirty = false;
  renderEditor();
  refreshSummary("option");
  const n = Object.values(editor.zones).reduce((t, a) => t + a.length, 0);
  setStatus(`${n} blocks on ${Object.keys(editor.zones).length} floors written into the option as layout.zones. Run the rules to make the memo from them; Save option as… keeps them.`, "ok");
}
