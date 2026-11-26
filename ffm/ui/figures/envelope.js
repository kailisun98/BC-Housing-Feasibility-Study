/* The envelope drawing in answer 1 (20 Nov 2026): what "outright" and "by rezoning" mean on this lot, for a board
   member. One compact section on white paper, two masses on one ground at one scale: on the left what stands today
   with no vote (the outright mass under its height limit), on the right the proposal (with the staff benchmark band
   where a policy gives one), each named in words under it with its storeys and height. The drawing is laid out in
   pixels down and percent across, so its labels stay 11.5 px at any width and it reads on a phone. Only what the run
   knows is drawn: no outright mass where the outright was not assessed, no band without a benchmark. */

import { h } from "../core/util.js";
import { FIG, HALF, NS, outrightLimit } from "./common.js";

// a height to one decimal, or two where it has them (88.45 m), as the massing records it
const m1 = v => { const r = Math.round(Number(v) * 100) / 100; return Math.abs(r * 10 - Math.round(r * 10)) < 1e-6 ? r.toFixed(1) : r.toFixed(2); };
const fsr = v => Number(v).toFixed(2).replace(/0$/, "");
const H = 172, GROUND = 158, TOP = 18, FS = 11.5, GAP = 14;
// across, in percent of the drawing's width: each mass, and where its labels start
const A = { x: 4, w: 18, lab: 24 }, B = { x: 54, w: 18, lab: 74 };

export function envelopeFigure(run) {
  if (!run || !run.ledger) return "";
  const L = run.ledger, m = run.massing || null;
  const allowedAns = (L.summary && L.summary.answers && L.summary.answers.allowed) || {};
  const o = allowedAns.outright || {}, path = allowedAns.rezoning_path || "";
  const site = (L.inputs && L.inputs.site) || {}, opt = (L.inputs && L.inputs.option) || {};
  const res = L.results || [];
  const val = (check, key) => {
    const r = res.find(x => x.check === check && x.status !== "not_applicable" && x.values && x.values[key] != null);
    return r ? Number(r.values[key]) : null;
  };
  const pm = m && (m.masses || []).find(x => x.name === "proposed"), om = m && (m.masses || []).find(x => x.name === "outright");
  const prop = pm ? { h: pm.height_m, n: pm.storeys, fsr: pm.fsr, none: !(pm.plate_area_m2 > 0) }
    : opt.height_m ? { h: Number(opt.height_m), n: opt.storeys, fsr: val("district_outright_fsr", "fsr") } : null;
  if (!prop || !(prop.h > 0)) return "";
  const notAssessed = o.verdict === "not assessed" || !!o.why;
  const lim = notAssessed ? null : (val("district_outright_height", "max_height_m_outright") ?? (m ? outrightLimit(m) : null));
  const maxFsr = notAssessed ? null : val("district_outright_fsr", "max_fsr_outright");
  const out = notAssessed || !om ? null : { h: om.height_m, n: om.storeys, fsr: om.fsr, none: !(om.plate_area_m2 > 0) };
  const bm = m && m.policy_benchmark && Array.isArray(m.policy_benchmark.height_m) ? m.policy_benchmark.height_m : null;
  const bench = bm && bm.length === 2 ? bm : null;
  const district = site.cd1_bylaw_number && /^CD-1/.test(site.zoning_district || "") ? `CD-1 (${site.cd1_bylaw_number})` : (site.zoning_district || "");
  const cd1 = /^CD-1/.test(district);

  // heights to pixels: the tallest thing drawn reaches the top
  const zMax = Math.max(prop.h, lim || 0, out ? out.h : 0, bench ? bench[1] : 0, 1);
  const k = (GROUND - TOP) / zMax, Y = z => GROUND - z * k;
  const pc = v => `${v}%`;
  let s = `<rect x="0" y="0" width="100%" height="${H}" fill="${FIG.paper}"/>`;
  const hline = (x1, x2, y, attrs) => `<line x1="${pc(x1)}" y1="${y.toFixed(1)}" x2="${pc(x2)}" y2="${y.toFixed(1)}" ${attrs} ${NS}/>`;
  // the staff benchmark, a band on the proposal's side
  if (bench) {
    s += `<rect x="${pc(B.x - 4)}" y="${Y(bench[1]).toFixed(1)}" width="${pc(100 - B.x + 2)}" height="${Math.max(1, (bench[1] - bench[0]) * k).toFixed(1)}" fill="${FIG.bench}" fill-opacity="0.14"/>`;
    for (const z of bench) s += hline(B.x - 4, 98, Y(z), `stroke="${FIG.bench}" stroke-width="1" stroke-dasharray="4 3"`);
  }
  // a mass: its storeys as floor lines where they are at least 3 px apart
  const mass = (col, z, n, fill, stroke, dash, opacity) => {
    let t = `<rect x="${pc(col.x)}" y="${Y(z).toFixed(1)}" width="${pc(col.w)}" height="${(z * k).toFixed(1)}" fill="${fill}" fill-opacity="${opacity}" stroke="${stroke}" stroke-width="${dash ? 2 : 1.2}"${dash ? ` stroke-dasharray="6 3"` : ""} ${NS}/>`;
    const f = n > 0 ? z / n : 0;
    if (n > 1 && f * k >= 3) for (let i = 1; i < n; i++) t += hline(col.x, col.x + col.w, Y(i * f), `stroke="${stroke}" stroke-width="0.6" stroke-opacity="0.55"`);
    return t;
  };
  if (out) s += mass(A, out.h, out.n, FIG.outrightFill, FIG.outrightStroke, true, 0.45);
  s += mass(B, prop.h, prop.n, FIG.proposedFill, FIG.proposedStroke, false, 0.5);
  // the outright height limit, one line across both, so the proposal's height reads against it
  if (lim) s += hline(1, 99, Y(lim), `stroke="${FIG.lot}" stroke-width="1" stroke-dasharray="10 3 2 3"`);
  s += `<rect x="0" y="${GROUND}" width="100%" height="${H - GROUND}" fill="${HALF.street}"/>` + hline(0, 100, GROUND, `stroke="${FIG.lot}" stroke-width="1.4"`);

  // labels beside each mass at their heights, pushed apart where two would overprint
  const place = tags => {
    tags.sort((u, v) => u.y - v.y);
    for (let i = 1; i < tags.length; i++) tags[i].y = Math.max(tags[i].y, tags[i - 1].y + GAP);
    const floor = GROUND - 4;
    if (tags.length && tags[tags.length - 1].y > floor) { tags[tags.length - 1].y = floor; for (let i = tags.length - 2; i >= 0; i--) tags[i].y = Math.min(tags[i].y, tags[i + 1].y - GAP); }
    return tags;
  };
  const left = [], right = [];
  // a line's label sits just above it and the benchmark's just under its band, so no line runs through the words
  if (lim) left.push({ y: Y(lim) - 4, text: `limit ${m1(lim)} m`, fill: FIG.lot });
  if (out && !(lim && Math.abs(lim - out.h) < 0.05)) left.push({ y: Y(out.h) + 4, text: `${m1(out.h)} m`, fill: FIG.lot });
  // the proposal's height beside its top, or just above it where a line runs at that height
  const lines = [lim, ...(bench || [])].filter(z => z != null).map(Y);
  right.push({ y: Y(prop.h) + (lines.some(y => Math.abs(y - Y(prop.h)) < 7) ? -4 : 4), text: `${m1(prop.h)} m`, fill: FIG.proposedStroke, weight: 600 });
  if (bench) right.push({ y: prop.h >= bench[1] ? Y(bench[0]) + 12 : Y(bench[1]) - 4, text: `${m1(bench[0])}–${m1(bench[1])} m`, long: `staff benchmark ${m1(bench[0])}–${m1(bench[1])} m`, fill: FIG.benchText });
  const halo = `paint-order="stroke" stroke="${FIG.paper}" stroke-width="3" stroke-linejoin="round"`;
  for (const [tags, col] of [[place(left), A], [place(right), B]]) {
    for (const t of tags) {
      const attrs = `x="${pc(col.lab)}" y="${t.y.toFixed(1)}" font-size="${FS}" fill="${t.fill}"${t.weight ? ` font-weight="${t.weight}"` : ""} ${halo}`;
      s += t.long ? `<text class="env-long" ${attrs}>${h(t.long)}</text><text class="env-short" ${attrs}>${h(t.text)}</text>` : `<text ${attrs}>${h(t.text)}</text>`;
    }
  }

  // the words under each mass: what it is, and what it takes
  const allowed = o.verdict === "yes" || o.verdict === "yes, with conditions";
  const today = cd1 ? `Allowed today under ${h(district)}` : "Allowed today";
  let aHead, aNum = "", aSub = "";
  if (notAssessed) {
    aHead = `<b>Allowed today:</b> not assessed`;
    aSub = o.why ? `${h(String(o.why).replace(/^./, c => c.toUpperCase()))}.` : "The district's limits were not read for this site.";
  } else {
    aHead = `<b>${today}</b>, no vote needed.`;
    if (out) aNum = `${h(out.n)}&nbsp;storeys, ${m1(out.h)}&nbsp;m${out.none ? "; no plate fits on the lot as fronted" : out.fsr ? ` · FSR&nbsp;${fsr(out.fsr)}` : ""}`;
    else if (maxFsr) aNum = `FSR&nbsp;${fsr(maxFsr)}`;
    const whose = district && !cd1 ? `the ${h(district)}` : "the by-law's";
    if (lim) aSub = out && Math.abs(lim - out.h) < 0.05 ? `At ${whose} height limit of ${m1(lim)} m.` : `Under ${whose} height limit of ${m1(lim)} m.`;
  }
  let bHead;
  // within the Director's discretion is not outright (25 Nov 2026): said as the permit it is
  const byDirector = ((allowedAns.routes || {}).discretion || {}).verdict === "possible";
  if (allowed && byDirector) bHead = `<b>Within what the Director of Planning may allow:</b> no rezoning, a development permit at the Director's discretion.`;
  else if (allowed) bHead = `<b>Within what is allowed today:</b> no rezoning, a development permit${o.verdict === "yes, with conditions" ? ", with conditions" : ""}.`;
  // a rezoning Council approved (25 Nov 2026): said as decided, with its date
  else if (o.verdict === "no" && path && (allowedAns.by_rezoning || {}).verdict === "approved") {
    const on = (String(allowedAns.by_rezoning.why || "").match(/ on (\d{1,2} \w+ \d{4})/) || [])[1];
    bHead = `<b>Rezoned:</b> Council approved it${on ? ` on ${h(on)}` : ""}, after a public hearing.`;
  }
  else if (o.verdict === "no") bHead = path ? `<b>Needs rezoning:</b> a Council decision after a public hearing.` : `<b>Not allowed outright</b>, and no rezoning path is stated.`;
  else if (notAssessed) bHead = `<b>Proposed.</b> Whether it needs a rezoning waits on the outright limits.`;
  else bHead = `<b>Outright not yet confirmed.</b>${path ? " If it is not allowed, a rezoning: a Council decision after a public hearing." : ""}`;
  const bNum = `${h(prop.n)}&nbsp;storeys, ${m1(prop.h)}&nbsp;m${prop.none ? "; no plate fits on the lot as fronted" : prop.fsr ? ` · FSR&nbsp;${fsr(prop.fsr)}` : ""}`;
  let bSub = "";
  if (bench) {
    const over = prop.h - bench[1], under = bench[0] - prop.h;
    bSub = `Staff benchmark ${m1(bench[0])} to ${m1(bench[1])} m, negotiated, not a limit${over > 0.05 ? `; this is ${m1(over)} m above it` : under > 0.05 ? `; this is ${m1(under)} m below it` : "; this is within it"}.`;
  }
  const label = allowed ? "Allowed today and proposed" : (o.verdict === "no" && path ? "Allowed today and by rezoning" : "Allowed today and proposed");
  const aria = `${label}, heights to scale: ${out ? `today ${out.n} storeys, ${m1(out.h)} m` : "today not drawn"}${lim ? `, under a ${m1(lim)} m limit` : ""}; proposed ${prop.n} storeys, ${m1(prop.h)} m${bench ? `; staff benchmark ${m1(bench[0])} to ${m1(bench[1])} m` : ""}.`;
  return `<figure class="figure env-fig">
    <div class="eyebrow">${h(label)} · heights to scale</div>
    <svg xmlns="http://www.w3.org/2000/svg" font-family="IBM Plex Sans, Helvetica, Arial, sans-serif" width="100%" height="${H}" style="height:${H}px" role="img" aria-label="${h(aria)}">${s}</svg>
    <div class="env-cols">
      <div class="env-col"><div class="env-head"><i class="fig-outright"></i>${aHead}</div>${aNum ? `<div class="env-num">${aNum}</div>` : ""}${aSub ? `<div class="env-sub">${aSub}</div>` : ""}</div>
      <div class="env-col"><div class="env-head"><i class="fig-proposed"></i>${bHead}</div><div class="env-num">${bNum}</div>${bSub ? `<div class="env-sub">${bSub}</div>` : ""}</div>
    </div>
  </figure>`;
}
