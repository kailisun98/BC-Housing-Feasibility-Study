/* Who resolves what, drawn (20 Nov 2026): the open items as lanes, one per person who acts, read from the start of
   each item's action ("Architect: …", "Manager and architect: …"), each item a node with its reference and a few
   words, left to right in the order the work runs: the site's facts first, then the design, then the funders. The
   table of open items stays under it with the whole sentence. HTML, so it reflows on a phone (the lanes then stack,
   each node naming its stage). Pure: no DOM; the paper memo prints the same markup. */

import { cap, h } from "../core/util.js";

/* The person an action names, the longest name first so "Manager and owner" is not read as "Manager"; an action
   with no name is the manager's, who carries the memo. */
export const WHO = /^(Manager and owner|Manager and architect|Manager or architect|Manager|Architect|Owner|Planner|City|Funder|Developer|Both)\b:?\s*/i;
export const whoOf = u => { const m = WHO.exec((u && u.action) || ""); return m ? cap(m[1].toLowerCase()) : "Manager"; };
export const todoOf = u => cap(((u && u.action) || "").replace(WHO, "")) || "";

/* The lanes, in the order a reader meets the people: the one who carries the memo, the one who draws, then the
   others. A joint action sits in the first person's lane and names the second. */
const LANES = [["Manager", "Development manager"], ["Architect", "Architect"], ["Owner", "Owner"], ["City", "The City"], ["Funder", "The funder"], ["Developer", "Developer"]];
const laneOf = who => {
  const w = String(who).toLowerCase();
  if (w.startsWith("manager")) return "Manager";
  if (w === "planner" || w === "city") return "City";
  if (w === "both") return "Manager";
  return cap(w.split(" ")[0]);
};
const withOf = who => { const m = /^manager (and|or) (\w+)/i.exec(who); return m ? `${m[1] === "or" ? "or" : "with"} the ${m[2].toLowerCase()}` : (/^both$/i.test(who) ? "with the architect" : ""); };

/* The stage an item belongs to: a fact about the site (what the rules could not read: yards, heritage, what stays,
   a schedule), the design (the rules the building answers, the drawings), or the funders (layer E and the money). */
export const STAGES = [["site", "Site facts"], ["design", "Design"], ["funders", "Funders"]];
export function stageOf(u, refOf = () => "") {
  const id = String(u.rule_id || "");
  if (id.startsWith("coverage.")) return "site";
  const layer = (refOf(id) || "").charAt(0);
  if (layer === "E" || layer === "F" || /^(bch|bc\.bcbuilds|cmhc)\./.test(id)) return "funders";
  return "design";
}

/* A title in a few words: up to its first colon or dash, without a closing bracket ("CD-1 (819) maximum floor space ratio
   (1015 E Hastings St)" keeps its CD-1 number), at most seven words. */
export function fewWords(title) {
  const t = String(title || "").split(/:|\s[–—]\s/)[0].replace(/\s*\([^()]*\)\s*$/, "").trim();
  const w = t.split(/\s+/);
  return w.length > 7 ? `${w.slice(0, 6).join(" ")}…` : t;
}

/* The diagram. items: the open items ({rule_id, title, status, action}); refOf: a rule's A1 reference. */
export function lanesHtml(items, refOf = () => "") {
  if (!items || !items.length) return "";
  const rows = new Map();
  for (const u of items) {
    const who = whoOf(u), lane = laneOf(who);
    if (!rows.has(lane)) rows.set(lane, { site: [], design: [], funders: [] });
    rows.get(lane)[stageOf(u, refOf)].push({ u, also: withOf(who) });
  }
  const order = [...LANES.map(([k]) => k).filter(k => rows.has(k)), ...[...rows.keys()].filter(k => !LANES.some(([x]) => x === k))];
  const name = k => (LANES.find(([x]) => x === k) || [k, k])[1];
  const used = STAGES.filter(([s]) => order.some(k => rows.get(k)[s].length));
  const node = ({ u, also }, stage) => {
    const ref = refOf(u.rule_id);
    return `<li class="lane-node" title="${h(u.title)}"><span class="node-stage">${h((STAGES.find(([s]) => s === stage) || [])[1] || "")}</span>${ref ? `<b class="ref">${h(ref)}</b>` : ""}<span class="node-words">${h(fewWords(u.title))}</span>${also ? `<span class="node-also">${h(also)}</span>` : ""}</li>`;
  };
  return `<div class="lanes" role="group" aria-label="Who resolves what: the open items by person, in the order the work runs" style="--stages:${used.length}">
    <div class="lanes-head" aria-hidden="true"><span></span>${used.map(([, w], i) => `<span class="lanes-stage">${i + 1} · ${h(w)}</span>`).join("")}</div>
    ${order.map(k => `<div class="lane">
      <span class="lane-who">${h(name(k))}</span>
      ${used.map(([s]) => `<ul class="lane-cell" data-stage="${s}">${rows.get(k)[s].map(x => node(x, s)).join("")}</ul>`).join("")}
    </div>`).join("")}
  </div>`;
}
