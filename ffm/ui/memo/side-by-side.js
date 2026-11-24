/* The Side by side card when two runs are compared: the pickers, one section with both buildings on one ground line,
   the trade-off in a sentence, the four answers and the money's verdict, the building and the money, the two capital
   stacks at one scale, and the rules whose status differs.

   20 Nov 2026: the earlier revision stands on the left and the later on the right, each named short ("R1 · As approved
   by Council", "R2 · What-if (hypothetical)"); every difference reads right less left ("Change"); numbers and their
   headers are right-aligned in fixed columns; one overlaid section replaces the two separate ones. */

import { $, cap, fmtNum, h, pill, verdictStatus } from "../core/util.js";
import { state } from "../core/state.js";
import { rev } from "../runs.js";
import { briefName, compareKind, dateWords, idBreak, optionName } from "./memo.js";
import { fundedWord, intakeNote, layoutOpenItems, MONEY_STATUS, moneyPhrase, moneyWord } from "./answers.js";
import { splitValues } from "./clauses.js";
import { millionsOf, stackFigure, stackOf } from "./stack.js";
import { FIG, fitLabels, NS, SVG_OPEN } from "../figures/common.js";

/* What the two options trade, in the units a board reads: units, storeys, height and floor area, A against B. */
export function tradeOff(A, B) {
  const a = (A.inputs && A.inputs.option) || {}, b = (B.inputs && B.inputs.option) || {};
  const units = o => { const v = Object.values(o.units || {}).filter(x => typeof x === "number"); return v.length ? v.reduce((s, x) => s + x, 0) : null; };
  const facts = [[units(a), units(b), "units"], [a.storeys, b.storeys, "storeys"], [a.height_m, b.height_m, "m high"], [a.gfa_m2, b.gfa_m2, "m² of floor area"]]
    .filter(([x, y]) => x != null && y != null && x !== y)
    .map(([x, y, unit]) => `${fmtNum(x)} ${unit} against ${fmtNum(y)}`);
  return facts.join(", ");
}

const revNo = r => Number(String(r || "").replace(/^R/, "")) || 1e9;
const unitsOf = o => Object.values((o && o.units) || {}).reduce((t, v) => t + (Number(v) || 0), 0);
const treesAfter = L => { const r = ((L && L.results) || []).find(x => x.check === "tree_replacement" && x.status !== "not_applicable"); return r && r.values && r.values.trees_after != null ? Number(r.values.trees_after) : null; };

/* The two runs in reading order: the earlier revision on the left, the later on the right. Each side knows whether it
   is the memo on screen (its picker is "open", the other's "compare"). */
export function sidesOf(run) {
  const A = run.ledger, B = run.compareLedger;
  if (!A || !B) return null;
  const site = (A.inputs && A.inputs.site) || {};
  const me = { slot: "open", isThis: true, L: A, rev: rev(run.run_id), pf: run.proforma && run.proforma.available ? run.proforma : null, lay: run.layout || null, m: run.massing || null };
  const other = { slot: "compare", isThis: false, L: B, rev: rev(state.compareRun), pf: run.compareProforma && run.compareProforma.available ? run.compareProforma : null, lay: run.compareLayout || null, m: run.compareMassing || null };
  for (const s of [me, other]) { s.name = briefName(optionName(s.L), site); s.label = `${s.rev} · ${s.name}`; s.opt = (s.L.inputs && s.L.inputs.option) || {}; }
  const [left, right] = revNo(other.rev) < revNo(me.rev) ? [other, me] : [me, other];
  return { left, right, me, other, site };
}

/* The rules as the card lists them: every rule that applies to either run, and whether its status differs. */
function ruleRows(A, B) {
  const byId = Object.fromEntries(B.results.map(r => [r.rule_id, r]));
  return A.results.filter(r => r.status !== "not_applicable" || (byId[r.rule_id] && byId[r.rule_id].status !== "not_applicable")).map(r => {
    const b = byId[r.rule_id];
    return { r, b, differs: !b || b.status !== r.status };
  });
}

/* The comparison folded to one line (the reader's layout folds it; the others open it): who is compared with whom,
   how many rules read differently, and the two gaps. */
export function compareFoldLine(run) {
  const s = sidesOf(run), d = run.diff;
  if (!s) return `<span class="cf-act">The comparison</span> <span class="cont">· ${h(d ? `against ${state.compareRun ? rev(state.compareRun) : "an earlier memo"}, rules as of ${dateWords(d.previous_as_of)}` : "")}</span>`;
  const rows = ruleRows(s.me.L, s.other.L), differ = rows.filter(x => x.differs).length;
  const gaps = s.left.pf && s.right.pf && s.left.pf.gap.value != null && s.right.pf.gap.value != null ? `; gap ${millionsOf(s.right.pf.gap.value)} against ${millionsOf(s.left.pf.gap.value)}` : "";
  return `<span class="cf-act"><span class="cf-closed">Show the comparison</span><span class="cf-open">Fold the comparison</span></span> <span class="cont">· ${h(s.right.label)} against ${h(s.left.label)}: ${differ ? `${differ} of ${rows.length} rules read differently` : "every rule reads the same"}${h(gaps)}</span>`;
}

/* The comparison's result in a line, for the title block's Compared-with cell (24 Nov 2026: the result started some
   4,000 px down the memo at 1366): how many rules read differently, and the two gaps, this memo's first. */
export function compareResult(run) {
  const s = sidesOf(run);
  if (!s) return "";
  const rows = ruleRows(s.me.L, s.other.L), differ = rows.filter(x => x.differs).length;
  const gap = side => side.pf && side.pf.gap && side.pf.gap.value != null ? millionsOf(side.pf.gap.value) : null;
  const gaps = gap(s.me) && gap(s.other) ? `; the gap ${gap(s.me)} here, ${gap(s.other)} in ${s.other.rev}` : "";
  return `${differ ? `${differ} of ${rows.length} rules read differently` : "every rule reads the same"}${gaps}`;
}

/* One section across the frontage with both buildings on one ground line and at one scale (D4, 20 Nov 2026): this
   memo's mass filled, the other's as a ghost outline, the outright limit, the staff benchmark as a band, and the
   height between the two roofs dimensioned. Drawn in metres like FIG 02, its labels refitted to 11.5 px. */
function overlaySvg(sides, fsIn = null) {
  const { left, right, me, other } = sides;
  const mm = [me.m, other.m];
  const prop = m => (m.masses || []).find(x => x.name === "proposed");
  const pm = prop(me.m), po = prop(other.m);
  if (!pm || !po) return "";
  const lotW = m => (m.lot.bbox ? m.lot.bbox[2] - m.lot.bbox[0] : m.lot.frontage_m);
  const W = Math.max(...mm.map(lotW));
  const bench = me.m.policy_benchmark || other.m.policy_benchmark;
  const outRule = r => r.check === "district_outright_height" && r.status !== "not_applicable";
  const outR = (me.L.results || []).find(outRule) || (other.L.results || []).find(outRule);
  const outLim = Number(me.m.outright_height_limit_m) || (outR && outR.values && Number(outR.values.max_height_m_outright)) || null;
  let hmax = Math.max(pm.height_m, po.height_m, 1);
  if (bench && bench.height_m) hmax = Math.max(hmax, bench.height_m[1]);
  if (outLim) hmax = Math.max(hmax, outLim);
  const pad = Math.max(4, W * 0.07);
  const fs = fsIn || Math.max(2.2, W / 34);
  const labelRoom = Math.max(W * 0.3, fs * 21);
  const vbW = W + 2 * pad + labelRoom, ground = fs * 1.4 + hmax, vbH = ground + fs * 2.2;
  const Y = z => ground - z;
  const bb0 = m => (m.lot.bbox ? m.lot.bbox[0] : 0);
  const span = (mass, m) => {
    const xs = (mass.footprint || []).map(p => Number(p[0])).filter(Number.isFinite);
    const envX = pad + ((m.envelope.box ? m.envelope.box.x : (m.envelope.setbacks_m.side || 0)) - bb0(m));
    return xs.length ? [pad + (Math.min(...xs) - bb0(m)), Math.max(...xs) - Math.min(...xs)] : [envX, m.envelope.width_m];
  };
  const f2 = x => x.toFixed(2);
  let s = `<svg ${SVG_OPEN} viewBox="0 0 ${f2(vbW)} ${f2(vbH)}" aria-label="One section, both options on one ground line: ${h(me.label)} filled, ${h(other.label)} outlined, with the outright limit and the staff benchmark">`;
  // the benchmark as a band between its two heights
  if (bench && bench.height_m) {
    const [b0, b1] = bench.height_m;
    s += `<rect x="${f2(pad)}" y="${f2(Y(b1))}" width="${f2(W)}" height="${f2(Math.max(0.01, b1 - b0))}" fill="${FIG.bench}" fill-opacity="0.12"/>`;
    for (const z of bench.height_m) s += `<line x1="${f2(pad)}" y1="${f2(Y(z))}" x2="${f2(pad + W)}" y2="${f2(Y(z))}" stroke="${FIG.bench}" stroke-width="1" stroke-dasharray="4 3" ${NS}/>`;
  }
  // this memo's mass, filled, with its floors
  const [px, pw] = span(pm, me.m);
  s += `<rect x="${f2(px)}" y="${f2(Y(pm.height_m))}" width="${f2(pw)}" height="${f2(pm.height_m)}" fill="${FIG.proposedFill}" fill-opacity="0.45" stroke="${FIG.proposedStroke}" stroke-width="1" ${NS}/>`;
  for (let k = 1; k < (pm.storeys || 0); k++) {
    const yk = Y(k * pm.floor_to_floor_m);
    if (yk <= Y(pm.height_m)) break;
    s += `<line x1="${f2(px)}" y1="${f2(yk)}" x2="${f2(px + pw)}" y2="${f2(yk)}" stroke="${FIG.proposedStroke}" stroke-width="0.6" stroke-opacity="0.6" ${NS}/>`;
  }
  // the other run's mass as a ghost: its outline only, dashed, in the drawing's muted ink
  const [ox, ow] = span(po, other.m);
  s += `<rect x="${f2(ox)}" y="${f2(Y(po.height_m))}" width="${f2(ow)}" height="${f2(po.height_m)}" fill="none" stroke="${FIG.lot}" stroke-width="1" stroke-dasharray="5 3" ${NS}/>`;
  // the outright limit across the lot
  if (outLim) s += `<line x1="${f2(pad)}" y1="${f2(Y(outLim))}" x2="${f2(pad + W)}" y2="${f2(Y(outLim))}" stroke="${FIG.outrightStroke}" stroke-width="1.6" stroke-dasharray="7 3" ${NS}/>`;
  s += `<line x1="${f2(pad - 2)}" y1="${f2(ground)}" x2="${f2(pad + W + 2)}" y2="${f2(ground)}" stroke="${FIG.lot}" stroke-width="1.2" ${NS}/>`;
  // the height between the two roofs, dimensioned inside the drawing, right less left
  const dh = right.opt.height_m != null && left.opt.height_m != null ? right.opt.height_m - left.opt.height_m : pm.height_m - po.height_m;
  if (Math.abs(pm.height_m - po.height_m) > 0.05) {
    const xd = Math.min(px + pw, ox + ow) - fs * 3.2, y1 = Y(Math.max(pm.height_m, po.height_m)), y2 = Y(Math.min(pm.height_m, po.height_m));
    const tick = fs * 0.35;
    s += `<line x1="${f2(xd)}" y1="${f2(y1)}" x2="${f2(xd)}" y2="${f2(y2)}" stroke="${FIG.lot}" stroke-width="0.8" ${NS}/>`;
    for (const y of [y1, y2]) s += `<line x1="${f2(xd - tick)}" y1="${f2(y + tick)}" x2="${f2(xd + tick)}" y2="${f2(y - tick)}" stroke="${FIG.lot}" stroke-width="0.8" ${NS}/>`;
    s += `<text x="${f2(xd - fs * 0.5)}" y="${f2((y1 + y2) / 2 + fs * 0.35)}" font-size="${f2(fs)}" fill="${FIG.lot}" text-anchor="end" font-weight="600" paint-order="stroke" stroke="#ffffff" stroke-width="${f2(fs * 0.28)}" stroke-linejoin="round">${h(signed(dh, 1))} m</text>`;
  }
  // the labels beside the frontage at their heights, pushed apart where two would overprint, with a leader to a moved one
  const lx = pad + W + fs * 0.8;
  const tags = [];
  if (bench && bench.height_m) tags.push({ at: Y(bench.height_m[0]), y: Y(bench.height_m[0]) + fs * 1.05, fill: FIG.benchText, text: `${h(bench.height_m[0])} to ${h(bench.height_m[1])} m · staff benchmark` });
  tags.push({ at: Y(pm.height_m), y: Y(pm.height_m) - fs * 0.35, fill: FIG.proposedStroke, weight: 600, text: `${h(pm.height_m)} m · ${h(me.rev)}, this memo` });
  tags.push({ at: Y(po.height_m), y: Y(po.height_m) - fs * 0.35, fill: FIG.lot, text: `${h(po.height_m)} m · ${h(other.rev)}, outlined` });
  if (outLim) tags.push({ at: Y(outLim), y: Y(outLim) - fs * 0.35, fill: FIG.grey, text: `${h(outLim)} m · outright limit` });
  tags.sort((u, v) => u.y - v.y);
  for (let k = 1; k < tags.length; k++) tags[k].y = Math.max(tags[k].y, tags[k - 1].y + fs * 1.4);
  for (const t of tags) {
    const moved = Math.abs(t.y - (t.at - fs * 0.35)) > fs * 0.5 && Math.abs(t.y - (t.at + fs * 1.05)) > fs * 0.5;
    if (moved) s += `<line x1="${f2(pad + W)}" y1="${f2(t.at)}" x2="${f2(lx - fs * 0.25)}" y2="${f2(t.y - fs * 0.35)}" stroke="${t.fill}" stroke-width="0.6" ${NS}/>`;
    s += `<text x="${f2(lx)}" y="${f2(t.y)}" font-size="${f2(fs)}" fill="${t.fill}"${t.weight ? ` font-weight="${t.weight}"` : ""}>${t.text}</text>`;
  }
  s += `<text x="${f2(pad)}" y="${f2(ground + fs * 1.4)}" font-size="${f2(fs)}" fill="${FIG.grey}">heights in metres · one ground line, one scale</text>`;
  return `${s}</svg>`;
}

/* A difference with its sign: +3, −4.0. */
const signed = (x, digits = 0) => (x == null || Number.isNaN(x) ? "—" : `${x > 0 ? "+" : x < 0 ? "−" : "±"}${digits ? Math.abs(x).toFixed(digits) : fmtNum(Math.round(Math.abs(x)))}`);

/* The differences the section shows, right less left, from the two ledgers: height, homes, trees. */
function differences(sides) {
  const { left, right } = sides;
  const bits = [];
  if (left.opt.height_m != null && right.opt.height_m != null && left.opt.height_m !== right.opt.height_m) bits.push(`height ${signed(right.opt.height_m - left.opt.height_m, 1)} m`);
  const ul = unitsOf(left.opt), ur = unitsOf(right.opt);
  if (ul && ur && ul !== ur) bits.push(`homes ${signed(ur - ul)} (${fmtNum(ur)} against ${fmtNum(ul)})`);
  const tl = treesAfter(left.L), tr = treesAfter(right.L);
  if (tl != null && tr != null && tl !== tr) bits.push(`trees after planting ${signed(tr - tl)} (${fmtNum(tr)} against ${fmtNum(tl)})`);
  return bits;
}

/* Why one gap is larger than the other, from the two pro-formas: the debt the rents carry, and the cost. */
function whyGap(sides) {
  const { left, right } = sides;
  if (!left.pf || !right.pf || left.pf.gap.value == null || right.pf.gap.value == null || left.pf.gap.value === right.pf.gap.value) return "";
  const [big, small] = right.pf.gap.value > left.pf.gap.value ? [right, left] : [left, right];
  const db = (big.pf.funding.debt || {}).supportable, ds = (small.pf.funding.debt || {}).supportable;
  const nb = (big.pf.operating || {}).noi, ns = (small.pf.operating || {}).noi;
  let s = `${big.rev}'s gap is the larger, ${millionsOf(big.pf.gap.value)} against ${millionsOf(small.pf.gap.value)}`;
  if (db != null && ds != null && db < ds) {
    const t = (big.pf.inputs || {}).rent_tiers_units, n = (big.pf.inputs || {}).units_total;
    const tiers = t && n ? ` (${fmtNum(t.rgi || 0)} of its ${fmtNum(n)} homes rent geared to income, ${fmtNum(t.deep_subsidy || 0)} at the shelter rate)` : "";
    s += `: it borrows ${millionsOf(db)} against ${millionsOf(ds)}, because its rents leave ${millionsOf(nb)} a year after running costs against ${millionsOf(ns)}${tiers}, and at the same ${Number((big.pf.funding.debt || {}).dcr || 1.1).toFixed(2)} coverage less rent carries less debt`;
  }
  const cb = (big.pf.capital || {}).total, cs = (small.pf.capital || {}).total;
  if (cb != null && cs != null && cb !== cs) s += `. ${big.rev} also costs ${cb > cs ? "more" : "less"}, ${millionsOf(cb)} against ${millionsOf(cs)}`;
  return `${s}.`;
}

/* Two runs side by side: the pickers over their columns, the section, the four answers and the money of each, then
   the rules whose status differs; the rules that read the same in both wait behind a disclosure. */
export function renderSideBySide(run) {
  const sides = sidesOf(run), d = run.diff;
  if (!sides) return "";
  const { left, right, me, other } = sides;
  const kind = d ? compareKind(d) : "options";
  const ans = L => L.summary.answers;
  // a verdict is a word in its status colour, not a status pill: the pills carry the six statuses and nothing else
  // (24 Nov 2026, critique: "Yes", "No" and "6 open" sat in pills beside the memo's Pass and Fail)
  const vword = (status, words) => `<span class="vword vw-${h(status || "na")}">${h(words)}</span>`;
  const verdictCell = w => vword(verdictStatus(w), cap(w));
  const fundCell = L => { const f = ans(L).funded, note = intakeNote(f); return `${vword(verdictStatus(f.verdict), fundedWord(f))}${note ? `<div class="cont side-cellnote">${h(note)}</div>` : ""}`; };
  const moneyCell = pf => (pf ? `${vword(MONEY_STATUS[pf.verdict.word] || "uncertain", moneyWord(pf.verdict))}<div class="cont side-cellnote">${h(moneyPhrase(pf).replace(/^[^:]*:\s*/, ""))}</div>` : `<span class="cont">not computed</span>`);
  // the open items as answer 3 counts them: the rules' and the drawings' (answers.layoutOpenItems), so the two agree
  const openOf = s => [...(ans(s.L).unsure || []), ...layoutOpenItems({ layout: s.lay })];
  const openCell = s => { const u = openOf(s); return u.length ? vword(u.some(x => x.status === "fail") ? "fail" : "uncertain", `${u.length} open item${u.length === 1 ? "" : "s"}`) : vword("pass", "Nothing open"); };
  const head = [
    ["Allowed outright", verdictCell(ans(left.L).allowed.outright.verdict), verdictCell(ans(right.L).allowed.outright.verdict)],
    ["By rezoning", verdictCell(ans(left.L).allowed.by_rezoning.verdict), verdictCell(ans(right.L).allowed.by_rezoning.verdict)],
    // the funders' criteria and the money beside each other, so passing the screen never reads as funded
    ["Funders' criteria", fundCell(left.L), fundCell(right.L)],
    ...(left.pf || right.pf ? [["The money", moneyCell(left.pf), moneyCell(right.pf)]] : []),
    ["Open items", openCell(left), openCell(right)],
  ];
  // the building and the money, side by side: what a board decides between (15 Nov 2026, from an architect's test);
  // numbers right-aligned under right-aligned headers, the change read right less left
  // money in millions here, so a column of figures fits a phone; answer 4 and the paper carry every dollar
  const numCell = (v, unit = "", digits = 0) => (v == null || Number.isNaN(v) ? "—" : unit === "$" && Math.abs(v) >= 1e6 ? millionsOf(v)
    : `${v < -1e-9 ? "−" : ""}${unit === "$" ? "$" : ""}${digits ? Math.abs(v).toFixed(digits) : fmtNum(Math.round(Math.abs(v)))}${unit && unit !== "$" ? unit : ""}`);
  // the change is read off the figures as printed, so the column adds up (24 Nov 2026: "22%" and "45%" printed a
  // change of "+24%", from the unrounded shares); a change of percentages is in points
  const asShown = (v, unit, digits) => (unit === "$" && Math.abs(v) >= 1e6 ? Math.round(v / 1e5) * 1e5 : Math.round(v * 10 ** digits) / 10 ** digits);
  const delta = (a, b, unit = "", digits = 0) => {
    if (a == null || b == null || Number.isNaN(a - b)) return "";
    const dv = asShown(a, unit, digits) - asShown(b, unit, digits);
    if (Math.abs(dv) < 1e-9) return `<span class="cont">same</span>`;
    return unit === "%" ? `${dv > 0 ? "+" : "−"}${Math.abs(dv).toFixed(digits)} points` : `${dv > 0 ? "+" : ""}${numCell(dv, unit, digits)}`;
  };
  const fsr = s => (s.opt.gfa_m2 && s.L.inputs.site.site_area_m2 ? s.opt.gfa_m2 / s.L.inputs.site.site_area_m2 : null);
  const fam = o => (Number((o.units || {}).two_bed) || 0) + (Number((o.units || {}).three_bed_plus) || 0);
  const yards = o => `${(o.setbacks_m || {}).front ?? "—"} / ${(o.setbacks_m || {}).rear ?? "—"} / ${(o.setbacks_m || {}).side ?? "—"} m`;
  const pfv = (s, f) => (s.pf ? f(s.pf) : null);
  const moneyRows = [
    ["Storeys", s => s.opt.storeys, "", 0],
    ["Height", s => s.opt.height_m, " m", 1],
    ["Floor area", s => s.opt.gfa_m2, " m²", 0],
    ["FSR", fsr, "", 2],
    ["Yards front / rear / side", null, "", 0, s => yards(s.opt)],
    ["Homes asked", s => unitsOf(s.opt) || null, "", 0],
    ["Homes that fit the plate", s => (s.lay ? s.lay.units_placed : null), "", 0],
    ["Family homes (2-bed+)", s => fam(s.opt) || null, "", 0],
    ["Trees after planting", s => treesAfter(s.L), "", 0],
    ["Capital cost", s => pfv(s, p => p.capital.total), "$", 0],
    ["Debt the rents carry", s => pfv(s, p => (p.funding.debt || {}).supportable), "$", 0],
    ["Funding", s => pfv(s, p => p.funding.total), "$", 0],
    ["Gap", s => pfv(s, p => p.gap.value), "$", 0],
    ["Gap per home", s => (s.pf && s.pf.gap.value != null && unitsOf(s.opt) ? s.pf.gap.value / unitsOf(s.opt) : null), "$", 0],
    ["Gap, share of capital", s => pfv(s, p => (p.gap.share_of_capital != null ? p.gap.share_of_capital * 100 : null)), "%", 0],
  ];
  const colHead = s => `<th class="num" scope="col">${h(s.rev)}<span class="th-name">${h(s.name)}</span></th>`;
  const moneyTable = kind === "rules" ? "" : `<table class="plain side-money"><colgroup><col class="c-label"><col class="c-num"><col class="c-num"><col class="c-num"></colgroup>
      <thead><tr><th scope="col">Building and money</th>${colHead(left)}${colHead(right)}<th class="num" scope="col">Change<span class="th-name">${h(right.rev)} less ${h(left.rev)}</span></th></tr></thead>
      <tbody>${moneyRows.map(([k, f, unit, digits, text]) => {
        if (text) return `<tr><th scope="row">${h(k)}</th><td class="num">${h(text(left))}</td><td class="num">${h(text(right))}</td><td class="num"></td></tr>`;
        const a = f(left), b = f(right);
        if (a == null && b == null) return "";
        return `<tr><th scope="row">${h(k)}</th><td class="num">${numCell(a, unit, digits)}</td><td class="num">${numCell(b, unit, digits)}</td><td class="num">${delta(b, a, unit, digits)}</td></tr>`;
      }).join("")}</tbody></table>`;
  // the two capital stacks at one scale: why one gap is larger than the other is in the drawing
  const stacks = kind === "rules" || !(left.pf && right.pf) ? "" : stackFigure([stackOf(left.pf, left.label), stackOf(right.pf, right.label)], { H: 200, lh: 15, names: true, cls: "side-stacks", label: "The two capital stacks at one scale" }, h(whyGap(sides)));
  // one section, both buildings on one ground line
  const diffs = kind === "rules" ? [] : differences(sides);
  const section = kind !== "rules" && me.m && other.m ? `<figure class="side-overlay">
      <div class="fig-section side-overlay-draw" data-overlay="1">${overlaySvg(sides)}</div>
      <figcaption>${h(me.label)} filled, ${h(other.label)} outlined, on one ground line at one scale${diffs.length ? `. ${h(right.rev)} against ${h(left.rev)}: ${h(diffs.join(", "))}` : ""}.</figcaption>
    </figure>` : "";
  const trade = tradeOff(right.L, left.L);
  const lead = kind === "rules"
    ? `${left.L.run.option_id === right.L.run.option_id ? "The same site and option" : `Two options under two readings of the rules (${h(right.name)} against ${h(left.name)})`}: ${h(left.rev)} reads the rules as of ${h(dateWords(left.L.run.as_of))}, ${h(right.rev)} as of ${h(dateWords(right.L.run.as_of))}.`
    : `${trade ? `${h(right.label)} against ${h(left.label)}: ${h(trade)}.` : `${h(left.rev)} and ${h(right.rev)} propose the same building.`} Both read the rules as of ${h(dateWords(right.L.run.as_of))}.`;
  const rows = ruleRows(me.L, other.L);
  const differ = rows.filter(x => x.differs), same = rows.filter(x => !x.differs);
  const cellOf = (r, L) => (r ? `${pill(r.status)}<div class="cont">${h(splitValues(r, L).proposed || "")}</div>` : `<span class="cont">not run</span>`);
  const row = ({ r, b }) => {
    const byL = left.isThis ? r : b, byR = left.isThis ? b : r;
    return `<tr>
      <td><span class="rule-title">${h(r.title)}</span><code class="rule-id">${idBreak(r.rule_id)}</code></td>
      <td class="status">${cellOf(byL, left.L)}</td>
      <td class="status">${cellOf(byR, right.L)}</td>
    </tr>`;
  };
  const table = list => `<table class="plain side-rules"><colgroup><col class="c-rule"><col class="c-ab"><col class="c-ab"></colgroup>
      <thead><tr><th scope="col">Rule</th><th scope="col">${h(left.label)}</th><th scope="col">${h(right.label)}</th></tr></thead><tbody>${list.map(row).join("")}</tbody></table>`;
  // each run's open items, with the person who resolves them, for the run that still has some
  const openList = [left, right].filter(s => openOf(s).length).map(s => `<details class="side-open">
      <summary>${h(s.label)}: ${openOf(s).length} open item${openOf(s).length === 1 ? "" : "s"}</summary>
      <ul>${openOf(s).map(u => `<li>${pill(u.status)} <b>${h(u.title)}</b> <span class="cont">${h(u.action || "")}</span></li>`).join("")}</ul>
    </details>`).join("");
  const pick = s => `<div class="pick" data-slot="${s.slot}"><span class="pick-name">${h(s.label)}${s.isThis ? " <span class=\"cont\">(this memo)</span>" : ""} <span class="cont">(as of ${h(dateWords(s.L.run.as_of))})</span></span></div>`;
  return `<section class="card section side" id="side-by-side" aria-labelledby="side-h">
    <h2 id="side-h">Side by side</h2>
    <div class="pick-row" role="group" aria-label="The two runs compared">
      <span class="pick-key" aria-hidden="true"></span>
      ${pick(left)}
      ${pick(right)}
    </div>
    ${section}
    <p class="side-lead">${lead}</p>
    <table class="plain side-head"><thead><tr><th><span class="sr-only">Answer</span></th><th><span class="sr-only">${h(left.label)}</span></th><th><span class="sr-only">${h(right.label)}</span></th></tr></thead>
      <tbody>${head.map(([k, a, b]) => `<tr><th scope="row">${h(k)}</th><td>${a}</td><td>${b}</td></tr>`).join("")}</tbody></table>
    ${moneyTable}
    ${stacks}
    ${moneyTable ? `<p class="cont side-note">The money rows are each run's pro-forma (answer 4 has every line, its rule and its source); the plate fit is each run's plans by program. "Passes the screen" means the funders' published criteria are met, not that the money is found.</p>` : ""}
    ${openList}
    <h3 class="side-sub">${differ.length ? `${differ.length} of ${rows.length} rules read differently` : `All ${rows.length} rules read the same in both`}</h3>
    ${differ.length ? table(differ) : ""}
    ${same.length ? `<details class="side-same"><summary>${differ.length ? `The other ${same.length} rules, the same in both` : `Show the ${same.length} rules`}</summary>${table(same)}</details>` : ""}
    <p class="cont side-note">Under each status is what that option proposed.</p>
  </section>`;
}

/* The overlaid section's labels at the drawing size (11.5 px), as the memo's figures are, refitted when the card
   changes width. */
let overlayObserver = null;
export function wireSideBySide(run) {
  if (overlayObserver) { overlayObserver.disconnect(); overlayObserver = null; }
  const box = $("#side-by-side [data-overlay]");
  if (!box) return;
  const sides = sidesOf(run);
  if (!sides) return;
  const fit = () => { if (box.isConnected && box.offsetWidth) fitLabels(box, fs => overlaySvg(sides, fs)); };
  fit();
  if (typeof ResizeObserver === "function") {
    let w = box.offsetWidth, t = null;
    overlayObserver = new ResizeObserver(() => { if (Math.abs(box.offsetWidth - w) < 2) return; w = box.offsetWidth; clearTimeout(t); t = setTimeout(fit, 120); });
    overlayObserver.observe(box);
  }
  // a fold opened later (the reader's) lays the drawing out then
  const fold = box.closest("details");
  if (fold) fold.addEventListener("toggle", () => { if (fold.open) fit(); });
}
