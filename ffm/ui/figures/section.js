/* FIG 02: the section across the frontage, with the outright and the benchmark heights. */

import { h } from "../core/util.js";
import { FIG, NS, SVG_OPEN } from "./common.js";

export function figSection(m, fsIn = null) {
  const W = m.lot.bbox ? m.lot.bbox[2] - m.lot.bbox[0] : m.lot.frontage_m;
  const masses = Object.fromEntries(m.masses.map(x => [x.name, x]));
  let hmax = Math.max(...m.masses.map(x => x.height_m), 1);
  const b = m.policy_benchmark;
  if (b && b.height_m) hmax = Math.max(hmax, b.height_m[1]);
  const pad = Math.max(4, W * 0.07);
  const fs = fsIn || Math.max(2.2, W / 34);
  const labelRoom = Math.max(W * 0.25, fs * 19);   // room for "19.9 to 21.3 m · staff benchmark" at the label size
  const vbW = W + 2 * pad + labelRoom, vbH = hmax + pad + fs * 2.2;
  const ground = fs * 1.2 + hmax;
  const Yz = z => ground - z;
  const bb0 = m.lot.bbox ? m.lot.bbox[0] : 0;
  const envX = pad + ((m.envelope.box ? m.envelope.box.x : (m.envelope.setbacks_m.side || 0)) - bb0), envW = m.envelope.width_m;
  let s = `<svg ${SVG_OPEN} viewBox="0 0 ${vbW.toFixed(2)} ${vbH.toFixed(2)}" aria-label="Section across the frontage: outright and proposed heights with the staff benchmark">`;
  s += `<line x1="${(pad - 2).toFixed(2)}" y1="${ground.toFixed(2)}" x2="${(pad + W + 2).toFixed(2)}" y2="${ground.toFixed(2)}" stroke="${FIG.lot}" stroke-width="1.2" ${NS}/>`;
  // as in plan: the proposed mass, then the outright one over it as a heavy dashed outline, so both read
  if (masses.proposed) {
    const p = masses.proposed;
    s += `<rect x="${envX.toFixed(2)}" y="${Yz(p.height_m).toFixed(2)}" width="${envW.toFixed(2)}" height="${p.height_m}" fill="${FIG.proposedFill}" fill-opacity="0.45" stroke="${FIG.proposedStroke}" stroke-width="1.2" ${NS}/>`;
    for (let k = 1; k < p.storeys; k++) {
      const yk = Yz(k * p.floor_to_floor_m);
      if (yk <= Yz(p.height_m)) break;
      s += `<line x1="${envX.toFixed(2)}" y1="${yk.toFixed(2)}" x2="${(envX + envW).toFixed(2)}" y2="${yk.toFixed(2)}" stroke="${FIG.proposedStroke}" stroke-width="0.6" stroke-opacity="0.6" ${NS}/>`;
    }
  }
  if (masses.outright) {
    const o = masses.outright;
    s += `<rect x="${envX.toFixed(2)}" y="${Yz(o.height_m).toFixed(2)}" width="${envW.toFixed(2)}" height="${o.height_m}" fill="${FIG.outrightFill}" fill-opacity="${masses.proposed ? 0.35 : 0.9}" stroke="${FIG.outrightStroke}" stroke-width="2" stroke-dasharray="6 3" ${NS}/>`;
  }
  const lx = pad + W + fs * 0.8;
  if (b && b.height_m) {
    for (const z of b.height_m) {
      s += `<line x1="${pad.toFixed(2)}" y1="${Yz(z).toFixed(2)}" x2="${(pad + W).toFixed(2)}" y2="${Yz(z).toFixed(2)}" stroke="${FIG.bench}" stroke-width="1" stroke-dasharray="4 3" ${NS}/>`;
    }
  }
  // the height labels beside the frontage, each at its own height, then pushed down where two would overprint, so
  // a proposed height just under the benchmark still reads; a short leader joins a moved label to its line
  const tags = [];
  if (b && b.height_m) tags.push({ at: Yz(b.height_m[0]), y: Yz(b.height_m[0]) + fs * 1.05, fill: FIG.benchText, text: `${h(b.height_m[0])} to ${h(b.height_m[1])} m · staff benchmark` });
  if (masses.proposed) tags.push({ at: Yz(masses.proposed.height_m), y: Yz(masses.proposed.height_m) - fs * 0.35, fill: FIG.proposedStroke, weight: 600, text: `${h(masses.proposed.height_m)} m · proposed` });
  if (masses.outright) tags.push({ at: Yz(masses.outright.height_m), y: Yz(masses.outright.height_m) - fs * 0.35, fill: FIG.lot, text: `${h(masses.outright.height_m)} m · outright` });
  tags.sort((u, v) => u.y - v.y);
  for (let k = 1; k < tags.length; k++) tags[k].y = Math.max(tags[k].y, tags[k - 1].y + fs * 1.5);
  for (const t of tags) {
    const moved = Math.abs(t.y - (t.at - fs * 0.35)) > fs * 0.5 && Math.abs(t.y - (t.at + fs * 1.05)) > fs * 0.5;
    if (moved) s += `<line x1="${(pad + W).toFixed(2)}" y1="${t.at.toFixed(2)}" x2="${(lx - fs * 0.25).toFixed(2)}" y2="${(t.y - fs * 0.35).toFixed(2)}" stroke="${t.fill}" stroke-width="0.6" ${NS}/>`;
    s += `<text x="${lx.toFixed(2)}" y="${t.y.toFixed(2)}" font-size="${fs}" fill="${t.fill}"${t.weight ? ` font-weight="${t.weight}"` : ""}>${t.text}</text>`;
  }
  // the note under the ground line starts at the lot's edge, so a narrow figure runs it into the label room instead
  // of cutting it off on the left
  s += `<text x="${pad.toFixed(2)}" y="${(ground + fs * 1.3).toFixed(2)}" font-size="${fs}" fill="${FIG.grey}">heights in metres · setback envelope ${h(m.envelope.width_m)} m wide</text>`;
  s += `</svg>`;
  return s;
}
