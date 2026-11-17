/* The architect's left column: the Site and Option schedules (Item | Value | Ref rows), the live envelope and unit
   counts under them, the card summaries, and the two tabs. */

import { $, $$, fmtNum, getPath, h, setPath } from "./core/util.js";
import { state } from "./core/state.js";
import { appliesHere, districtOf, OPTION_FIELDS, optWord, SITE_FIELDS, TRI } from "./fields.js";
import { syncRunButton } from "./runs.js";
import { memoRefs } from "./memo/memo.js";
import { renderClaude } from "./claude.js";

/* A rule's reference as the memo cites it (A1, C2): the memo's own when a run is on screen, else the same count the
   engine makes, over every rule in force on the date (one that does not apply to the district still takes its place,
   as "not applicable"), each layer in order of rule id (engine.run sorts the results so). */
let refsCache = { key: "", map: {} };

export function refNow(id) {
  if (state.run && state.refOf && state.refOf[id]) return state.refOf[id];
  const key = `${state.rules.length}|${state.rules.map(r => r.id).join(",").length}`;
  if (refsCache.key !== key) {
    const order = { A: 0, B: 1, C: 2, D: 3, E: 4, F: 5 };
    const rules = state.rules.slice().sort((a, b) => ((order[a.layer] ?? 9) - (order[b.layer] ?? 9)) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    refsCache = { key, map: memoRefs(rules.map(r => ({ rule_id: r.id, layer: r.layer }))) };
  }
  return refsCache.map[id] || "";
}

/* What a field's Ref says: the rules that read it, or the word for what else it is for. */
function refsFor(f) {
  const reads = f.reads || [];
  const district = (state.site || {}).zoning_district, cd1 = (state.site || {}).cd1_bylaw_number;
  const list = state.rules.filter(r => reads.includes(r.check) && appliesHere(r, district, cd1)).map(r => ({ id: r.id, title: r.title, ref: refNow(r.id) })).filter(r => r.ref)
    .sort((a, b) => a.ref[0].localeCompare(b.ref[0]) || Number(a.ref.slice(1)) - Number(b.ref.slice(1)));
  if (list.length) {
    const refs = list.map(r => r.ref);
    return { short: refs.length > 2 ? `${refs.slice(0, 2).join(" ")} +${refs.length - 2}` : refs.join(" "), long: refs.join(", "), rules: list };
  }
  const word = f.ref || (f.need === "figure" ? "drawings" : reads.length ? "rule" : "note");
  return { short: word, long: word, rules: [] };
}

/* The schedule (16 Nov 2026; before, a form of labelled fields with an (i) and a mark on each): one row per input,
   Item | Value | Ref, in the file's groups. The Ref names the rules that read the input as the memo cites them, or
   says what else it is for (drawings, file, title, note, money); a click opens the reason under the row. A blank that
   a rule reads says "not sure" in its field and comes back uncertain. The architect's left column holds two of them,
   the Site's and the Option's; the manager's flow asks only what the open data could not tell. */
export function renderForm(formEl, schema, obj, onChange) {
  const on = schema === SITE_FIELDS ? "site" : "option";
  formEl.innerHTML = "";
  formEl.classList.add("schedule");
  const legend = document.createElement("p");
  legend.className = "need-legend";
  formEl.appendChild(legend);
  for (const group of schema) {
    const sec = document.createElement("section");
    const hid = `sch-${on}-${group.group.replace(/\W+/g, "-").toLowerCase()}`;
    sec.className = "sch-group";
    sec.setAttribute("aria-labelledby", hid);
    sec.innerHTML = `<h3 class="sch-head" id="${hid}">${h(group.group)}</h3>`;
    for (const f of group.fields.flatMap(x => (x.row ? x.fields : [x]))) {
      for (const el of scheduleRow(f, obj, onChange, on)) sec.appendChild(el);
      if (on === "site" && f.key === "zoning_district") { const slot = document.createElement("div"); slot.id = "claude-schedule-slot"; slot.className = "sch-slot"; sec.appendChild(slot); }
    }
    formEl.appendChild(sec);
  }
  refreshNeeds(formEl, schema, obj);
  if (on === "site") renderClaude();
}

/* The line over a schedule: how many of the needed inputs and of the rule-read inputs are filled in. */
export function refreshNeeds(formEl, schema, obj) {
  const legend = $(".need-legend", formEl);
  if (!legend) return;
  const counts = { run: [0, 0], rule: [0, 0] };
  const walk = fields => {
    for (const f of fields) {
      if (f.row) { walk(f.fields); continue; }
      const need = f.need;
      if (!need || !counts[need]) continue;
      const v = getPath(obj, f.key);
      const filled = Array.isArray(v) ? v.length > 0 : (f.type === TRI ? v === true || v === false : v !== null && v !== undefined && v !== "");
      counts[need][1]++;
      if (filled) counts[need][0]++;
    }
  };
  for (const g of schema) walk(g.fields);
  const [r0, r1] = counts.run, [u0, u1] = counts.rule;
  legend.innerHTML = `<span><i class="need need-run" aria-hidden="true"></i>Needed to run <b>${r0} of ${r1}</b></span><span>Read by a rule <b>${u0} of ${u1}</b>${u0 < u1 ? ` <span class="cont">· a blank comes back uncertain</span>` : ""}</span>`;
}

/* One row of a schedule, and the reason under it (folded). */
function scheduleRow(f, obj, onChange, on) {
  if (f.type === "units-live" || f.type === "envelope-live") {
    const el = document.createElement("div");
    el.className = "sch-live live";
    el.dataset.live = f.type === "units-live" ? "units" : "envelope";
    el.innerHTML = f.type === "units-live" ? unitsLive(obj) : envelopeLive(obj);
    return [el];
  }
  const id = `f-${on}-${f.key.replace(/\W/g, "-")}`;
  const wide = ["programs", "trees", "textarea"].includes(f.type);
  const asSpan = [TRI, "programs", "trees"].includes(f.type);
  const row = document.createElement("div");
  row.className = `sch-row${wide ? " wide" : ""}${f.need === "run" ? " needed" : ""}`;
  row.dataset.key = f.key;
  row.innerHTML = `<div class="sch-item">${asSpan ? `<span id="${id}-label">${h(f.label)}</span>` : `<label for="${id}">${h(f.label)}</label>`}${f.need === "run" ? `<i class="need need-run" aria-hidden="true" title="needed to run"></i><span class="sr-only">(needed to run)</span>` : ""}${f.ask && f.ask.who ? `<span class="sch-who">${h(f.ask.who)}</span>` : ""}</div><div class="sch-val"></div><div class="sch-ref"></div>`;
  $(".sch-val", row).appendChild(controlFor(f, obj, onChange, id));
  const refs = refsFor(f);
  const note = document.createElement("div");
  note.className = "sch-note";
  note.id = `${id}-why`;
  note.hidden = true;
  const help = f.help && !shortHelp(f) ? `<p class="cont">${h(f.help)}</p>` : "";
  note.innerHTML = `<p>${h(f.info || "")}</p>${help}${refs.rules.length ? `<p class="sch-reads">Read by ${refs.rules.map(r => `<b class="ref">${h(r.ref)}</b>${h(r.title)}`).join("; ")}.</p>` : ""}`;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "ref-btn" + (refs.rules.length ? "" : " word");
  btn.textContent = refs.short;
  btn.setAttribute("aria-expanded", "false");
  btn.setAttribute("aria-controls", note.id);
  btn.setAttribute("aria-label", `${f.label}: ${refs.rules.length ? `read by ${refs.long}` : refs.long}. Why`);
  btn.addEventListener("click", () => { const open = note.hidden; note.hidden = !open; btn.setAttribute("aria-expanded", String(open)); row.classList.toggle("why-open", open); });
  $(".sch-ref", row).appendChild(btn);
  return [row, note];
}

/* A help line short enough to stand in the empty field as its placeholder. */
const shortHelp = f => !!(f.help && f.help.length <= 28);

/* The control for one input, without its label (the schedule's Item cell carries it). */
function controlFor(f, obj, onChange, id) {
  const value = getPath(obj, f.key);
  if (f.type === TRI) {
    const tri = document.createElement("div");
    tri.className = "tri";
    tri.setAttribute("role", "radiogroup");
    tri.setAttribute("aria-labelledby", `${id}-label`);
    // a radio group: one tab stop on the chosen answer, the arrow keys move the choice
    const choices = [[true, "Yes"], [false, "No"], [null, "Not sure"]];
    const current = value === undefined ? null : value;
    const buttons = [];
    const choose = (i, focus) => {
      setPath(obj, f.key, choices[i][0]);
      buttons.forEach((x, k) => { x.setAttribute("aria-checked", String(k === i)); x.tabIndex = k === i ? 0 : -1; });
      if (focus) buttons[i].focus();
      onChange(f.key);
    };
    choices.forEach(([v, lab], i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = lab;
      b.className = v === null ? "unsure" : "";
      b.setAttribute("role", "radio");
      b.setAttribute("aria-checked", String(current === v));
      b.tabIndex = current === v ? 0 : -1;
      b.addEventListener("click", () => choose(i, false));
      b.addEventListener("keydown", e => {
        const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
        if (!step) return;
        e.preventDefault();
        choose((i + step + choices.length) % choices.length, true);
      });
      buttons.push(b);
      tri.appendChild(b);
    });
    if (!buttons.some(b => b.tabIndex === 0)) buttons[2].tabIndex = 0;
    return tri;
  }
  const el = document.createElement("div");
  el.className = "sch-ctl";
  if (f.type === "select") {
    const opts = f.options.map(([v, lab]) => `<option value="${h(v)}"${String(value ?? "") === String(v) ? " selected" : ""}>${h(lab)}</option>`).join("");
    el.innerHTML = `<select id="${id}">${opts}</select>`;
    $("select", el).addEventListener("change", e => { setPath(obj, f.key, e.target.value === "" ? null : e.target.value); onChange(f.key); });
    return el;
  }
  if (f.type === "textarea") {
    el.innerHTML = `<textarea id="${id}" rows="2">${h(value ?? "")}</textarea>`;
    $("textarea", el).addEventListener("input", e => { setPath(obj, f.key, e.target.value || null); onChange(f.key); });
    return el;
  }
  if (f.type === "programs") {
    el.className = "checks";
    el.setAttribute("role", "group");
    el.setAttribute("aria-labelledby", `${id}-label`);
    const chosen = new Set(Array.isArray(value) ? value : []);
    const programs = state.rules.filter(r => r.layer === "E");
    if (!programs.length) el.innerHTML = `<span class="help">Rules not loaded.</span>`;
    for (const r of programs) {
      const lab = document.createElement("label");
      lab.innerHTML = `<input type="checkbox" value="${h(r.id)}"${chosen.has(r.id) ? " checked" : ""}> <span>${h(r.title)}</span>`;
      $("input", lab).addEventListener("change", () => {
        setPath(obj, f.key, $$("input:checked", el).map(x => x.value));
        onChange(f.key);
      });
      el.appendChild(lab);
    }
    return el;
  }
  if (f.type === "trees") {
    el.className = "trees";
    el.setAttribute("role", "group");
    el.setAttribute("aria-labelledby", `${id}-label`);
    const trees = Array.isArray(value) ? value : [];
    if (!Array.isArray(value)) setPath(obj, f.key, trees);
    const draw = () => {
      el.innerHTML = trees.length ? `<div class="tree-row tree-head"><span>id</span><span>species</span><span>DBH cm</span><span>plan</span><span></span></div>` : `<span class="help">No tree survey on file: the trees rule will say so.</span>`;
      trees.forEach((t, i) => {
        const row = document.createElement("div");
        row.className = "tree-row";
        row.innerHTML = `<input type="text" value="${h(t.id ?? "")}" aria-label="Tree id">
          <input type="text" value="${h(t.species ?? "")}" aria-label="Species" placeholder="species">
          <input type="number" step="any" value="${t.dbh_cm ?? ""}" aria-label="DBH in cm" placeholder="not sure">
          <select aria-label="Retain or remove"><option value="retain"${t.status === "retain" ? " selected" : ""}>retain</option><option value="remove"${t.status === "remove" ? " selected" : ""}>remove</option></select>
          <button type="button" class="x" title="Remove this tree" aria-label="Remove tree ${h(t.id || i + 1)}"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4.5 4.5 11.5 11.5M11.5 4.5 4.5 11.5"/></svg></button>`;
        const [idIn, spIn, dbhIn] = $$("input", row);
        idIn.addEventListener("input", e => { t.id = e.target.value || null; onChange(f.key); });
        spIn.addEventListener("input", e => { t.species = e.target.value || null; onChange(f.key); });
        dbhIn.addEventListener("input", e => { t.dbh_cm = e.target.value === "" ? null : Number(e.target.value); onChange(f.key); });
        $("select", row).addEventListener("change", e => { t.status = e.target.value; onChange(f.key); });
        $(".x", row).addEventListener("click", () => { trees.splice(i, 1); draw(); onChange(f.key); });
        el.appendChild(row);
      });
      const add = document.createElement("button");
      add.type = "button";
      add.className = "btn btn-quiet btn-small";
      add.textContent = "Add a tree";
      add.addEventListener("click", () => { trees.push({ id: "T" + (trees.length + 1), species: null, dbh_cm: null, status: "retain" }); draw(); onChange(f.key); });
      el.appendChild(add);
    };
    draw();
    return el;
  }
  // text, slug, number. A blank number is read as "not sure", and the empty field says so.
  const isNum = f.type === "number";
  const warnId = `${id}-warn`;
  const ph = isNum ? (shortHelp(f) ? `not sure · ${f.help}` : "not sure") : (shortHelp(f) ? f.help : "");
  el.innerHTML = `<input id="${id}" type="${isNum ? "number" : "text"}"${isNum ? ` step="${f.int ? "1" : "any"}"` : ""}${ph ? ` placeholder="${h(ph)}"` : ""}${f.share ? ` min="0" max="1" aria-describedby="${warnId}"` : ""} value="${h(value ?? "")}">
    ${f.share ? `<span class="help warn" id="${warnId}" hidden>Write a share as a decimal: 0.30 for 30%.</span>` : ""}`;
  const warn = f.share ? $(".warn", el) : null;
  const checkShare = v => { if (warn) warn.hidden = !(typeof v === "number" && v > 1); };
  checkShare(value);
  $("input", el).addEventListener("input", e => {
    let v = e.target.value;
    if (isNum) v = v === "" ? null : Number(v);
    else if (f.type === "slug") v = v.trim().toLowerCase().replace(/[^a-z0-9._-]+/g, "-") || null;
    else v = v === "" ? null : v;
    checkShare(v);
    setPath(obj, f.key, v);
    onChange(f.key);
  });
  return el;
}

export function unitsLive(option) {
  const u = (option && option.units) || {};
  const n = k => Number(u[k]) || 0;
  const total = n("studio") + n("one_bed") + n("two_bed") + n("three_bed_plus");
  const fam = n("two_bed") + n("three_bed_plus");
  if (!total) return `total <b>0</b> units`;
  return `total <b>${total}</b> units · two-bed or more <b>${fam}</b> (<b>${(100 * fam / total).toFixed(1)}%</b>) · three-bed or more <b>${n("three_bed_plus")}</b> (<b>${(100 * n("three_bed_plus") / total).toFixed(1)}%</b>)`;
}

/* What the storeys and the setbacks imply, so the architect need not multiply by hand: the plate the setbacks leave
   on this site (or the last massing's plate box on a polygon lot), × storeys = a floor area; storeys × floor to floor
   = a height. Each can be taken into the option with one click; what was typed stays until then (15 Nov 2026). */
export function envelopeLive(option) {
  const site = state.site || {};
  const o = option || {};
  const st = Number(o.storeys) || 0, f2f = Number(o.floor_to_floor_m) || 3.0;
  const sb = o.setbacks_m || {};
  const m = state.run && state.run.massing && state.run.run_id.split("/")[0] === (state.siteId || site.id) ? state.run.massing : null;
  let plate = null, how = "";
  if (m && m.envelope && m.envelope.box) { plate = m.envelope.box.w * m.envelope.box.d; how = `the plate box ${m.envelope.box.w} × ${m.envelope.box.d} m inside the setback envelope`; }
  else if (site.frontage_m && site.depth_m) {
    const w = site.frontage_m - 2 * (Number(sb.side) || 0), d = site.depth_m - (Number(sb.front) || 0) - (Number(sb.rear) || 0);
    if (w > 0 && d > 0) { plate = w * d; how = `the envelope the setbacks leave, ${w.toFixed(1)} × ${d.toFixed(1)} m`; }
  }
  if (!st) return `<span class="cont">Give the storeys and the floor area and height can be derived from the plate here.</span>`;
  const gfa = plate ? Math.round(plate * st) : null, hgt = Math.round(st * f2f * 10) / 10;
  const diffG = gfa != null && o.gfa_m2 != null && Math.abs(gfa - o.gfa_m2) > 1;
  const diffH = o.height_m != null && Math.abs(hgt - o.height_m) > 0.05;
  const own = `<span class="cont">· the figure in the option</span>`;
  return `<span class="cont">From ${st} storeys:</span> ${gfa != null ? `floor area up to <b>${fmtNum(gfa)} m²</b> <span class="cont">(${how}, ${fmtNum(Math.round(plate))} m² × ${st}; a plate smaller than the envelope gives less)</span> ${o.gfa_m2 == null || diffG ? `<button type="button" class="btn btn-quiet btn-small" data-use="gfa_m2" data-value="${gfa}">${o.gfa_m2 == null ? "Use it" : "Use it instead of " + fmtNum(o.gfa_m2)}</button>` : own}` : `<span class="cont">no plate known yet: give the site its frontage and depth</span>`}
    · height <b>${hgt} m</b> <span class="cont">(${st} × ${f2f} m)</span> ${o.height_m == null || diffH ? `<button type="button" class="btn btn-quiet btn-small" data-use="height_m" data-value="${hgt}">${o.height_m == null ? "Use it" : "Use it instead of " + o.height_m}</button>` : own}`;
}

/* How many three-state answers in a form are "not sure" (null), for the card's one-line summary. */
function countUnsure(obj, schema) {
  let n = 0;
  const walk = fields => { for (const f of fields) { if (f.row) walk(f.fields); else if (f.type === TRI && getPath(obj, f.key) == null) n++; } };
  for (const g of schema) walk(g.fields);
  return n;
}

function unsureNote(n) { return n ? ` · <span class="unsure-n">${n} answer${n === 1 ? "" : "s"} not sure</span>` : ""; }

function siteSummary(s) {
  if (!s) return "";
  const dims = s.frontage_m != null && s.depth_m != null ? ` · ${h(s.frontage_m)} × ${h(s.depth_m)} m` : "";
  return `<b>${h(s.address || s.id || "A new site")}</b> · ${h(districtOf(s) || "district not set")} · ${s.site_area_m2 != null ? `${h(fmtNum(s.site_area_m2))} m²` : "area not set"}${dims}${unsureNote(countUnsure(s, SITE_FIELDS))}`;
}

export function optionSummary(o) {
  if (!o) return "";
  const u = o.units || {};
  const total = ["studio", "one_bed", "two_bed", "three_bed_plus"].reduce((t, k) => t + (Number(u[k]) || 0), 0);
  const bits = [];
  if (o.storeys != null) bits.push(`${h(o.storeys)} storeys`);
  if (o.height_m != null) bits.push(`${h(o.height_m)} m`);
  if (o.gfa_m2 != null) bits.push(`${h(fmtNum(o.gfa_m2))} m² GFA`);
  if (total) bits.push(`${total} units`);
  if (o.tenure) bits.push(h(optWord("option", "tenure", o.tenure)));
  return `<b>${h(o.name || o.id || "A new option")}</b>${bits.length ? ` · ${bits.join(" · ")}` : ""}${unsureNote(countUnsure(o, OPTION_FIELDS))}`;
}

/* The schedules are always open now (16 Nov 2026: the cards no longer fold to a summary; the architect's column is
   the two schedules, the manager's the route); kept so older callers need no change. */
export function setCollapsed(kind) {
  const card = $(`#step-${kind}`);
  if (card) card.classList.remove("collapsed");
}

export function refreshSummary(kind) {
  const obj = kind === "site" ? state.site : state.option;
  $(`#${kind}-summary`).innerHTML = obj ? (kind === "site" ? siteSummary(obj) : optionSummary(obj)) : "";
  syncCards();
}

/* The architect's left column: the Site and the Option schedules, one at a time under two tabs. The manager's left
   column is the route, the reader's nothing; neither shows the schedules. */
const TAB_KEY = "ffm.rail.tab";

export function syncCards() {
  const siteCard = $("#step-site"), optCard = $("#step-option");
  if (!siteCard || !optCard) return;
  const arch = state.mode === "architect";
  let tab = "site";
  try { tab = localStorage.getItem(TAB_KEY) === "option" ? "option" : "site"; } catch (e) { /* storage off: the site first */ }
  siteCard.hidden = !arch || tab !== "site";
  optCard.hidden = !arch || tab !== "option";
  $$("#rail-tabs .segbtn").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.tab === tab)));
  syncRunButton();
}

export function setRailTab(tab) {
  try { localStorage.setItem(TAB_KEY, tab); } catch (e) { /* the choice lasts this visit */ }
  syncCards();
}
