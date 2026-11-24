/* The program brief (24 Nov 2026): the spaces a kind of housing runs on beyond its homes — a staffed desk by the
   entry, a staff office, a program room, dining, laundry, a shelter's sleeping rooms — as one editable list. The default
   for the housing type is layout.BRIEF_DEFAULTS' twin (tests/test_user_tests_2026_11_23.py checks the labels match);
   every figure is a declared placeholder until the operator's own brief replaces it, which is written to
   `option.program_brief` as fixed areas and laid out by the engine (named blocks; "beside the entry" goes next to the
   lobby, "upper floors" starts above the ground floor). Shown at stop 02 and on the operator's desk. */

import { $, $$, h, setPath, setStatus } from "./core/util.js";
import { guide, state } from "./core/state.js";
import { markStale, saveDraft } from "./files.js";

export const BRIEF_DEFAULTS = {
  supportive: [
    { label: "24/7 front desk", area_m2: 12, next_to: "entry" },
    { label: "Staff office", area_m2: 15 },
    { label: "Staff washroom", area_m2: 4 },
    { label: "Program room", area_m2: 40 },
    { label: "Shared kitchen and dining", per_home_m2: 1.0, min_m2: 40, replaces_amenity: true },
    { label: "Laundry", per_home_m2: 0.4, min_m2: 15 },
    { label: "Harm reduction room", area_m2: 10 },
  ],
  transitional: [
    { label: "Front desk", area_m2: 10, next_to: "entry" },
    { label: "Staff office", area_m2: 15 },
    { label: "Program room", area_m2: 30 },
    { label: "Laundry", per_home_m2: 0.4, min_m2: 15 },
  ],
  shelter: [
    { label: "24/7 front desk", area_m2: 12, next_to: "entry" },
    { label: "Staff office", area_m2: 15 },
    { label: "Sleeping rooms", beds_per_room: 4, per_bed_m2: 4.6, where: "upper" },
    { label: "Washrooms and showers", per_bed_m2: 0.6 },
    { label: "Dining", per_bed_m2: 1.0, min_m2: 30, replaces_amenity: true },
    { label: "Laundry", per_bed_m2: 0.25, min_m2: 12 },
    { label: "Lockers and storage", per_bed_m2: 0.3 },
  ],
};

/* The brief in force for an option: its own, or its housing type's default worked out to fixed areas (layout.program_brief). */
export function briefOf(o) {
  const own = (o || {}).program_brief;
  if (Array.isArray(own) && own.length) return { items: own.map(x => ({ ...x })), own: true };
  const kind = String((o || {}).housing_type || "independent");
  const homes = Object.values((o || {}).units || {}).reduce((a, b) => a + (Number(b) || 0), 0);
  const beds = Number((o || {}).beds) > 0 ? Number(o.beds) : 0;
  const items = [];
  // a shelter or supportive part of a mixed building takes the part's own spaces (layout.program_brief)
  let defs = BRIEF_DEFAULTS[kind] || [];
  if (kind === "independent" && beds) defs = [...defs, ...BRIEF_DEFAULTS.shelter.map(i => ({ ...i, label: `Shelter: ${i.label}` }))];
  if (kind === "independent" && Number((o || {}).supportive_units) > 0) defs = [...defs, ...BRIEF_DEFAULTS.supportive.filter(i => !i.replaces_amenity).map(i => ({ ...i, label: `Supportive: ${i.label}` }))];
  for (const it of defs) {
    let area;
    if (it.beds_per_room) area = beds ? Math.ceil(beds / it.beds_per_room) * it.beds_per_room * it.per_bed_m2 * 1.10 : 0;
    else if (it.per_bed_m2) area = beds ? Math.max(it.min_m2 || 0, beds * it.per_bed_m2) : 0;
    else if (it.per_home_m2) { const n = homes || beds; area = n ? Math.max(it.min_m2 || 0, n * it.per_home_m2) : 0; }
    else area = it.area_m2 || 0;
    if (area > 0) items.push({ label: it.label, area_m2: Math.round(area * 10) / 10, next_to: it.next_to || null, where: it.where || "ground", ...(it.replaces_amenity ? { replaces_amenity: true } : {}) });
  }
  return { items, own: false };
}

export function briefEditor(o) {
  if (!o) return "";
  const { items, own } = briefOf(o);
  const kind = String(o.housing_type || "independent");
  const row = (it, i) => `<tr data-i="${i}">
      <td><input type="text" class="brief-label" value="${h(it.label)}" aria-label="Space" maxlength="60"></td>
      <td><input type="number" class="brief-area" value="${h(it.area_m2)}" min="0" step="any" inputmode="decimal" aria-label="Area, m²"></td>
      <td><select class="brief-where" aria-label="Where"><option value="ground"${it.where !== "upper" ? " selected" : ""}>ground floor</option><option value="upper"${it.where === "upper" ? " selected" : ""}>upper floors</option></select></td>
      <td><label class="chip"><input type="checkbox" class="brief-entry"${it.next_to === "entry" ? " checked" : ""}> <span>by the entry</span></label></td>
      <td><button type="button" class="btn btn-quiet btn-small brief-remove" aria-label="Remove ${h(it.label)}">Remove</button></td>
    </tr>`;
  return `<details class="fold brief-fold"${kind !== "independent" || own ? " open" : ""}><summary>What it runs on <span class="cont">· ${own ? "the brief entered" : kind === "independent" ? "no brief: the amenity and services only" : `the default brief for ${h(kind)} housing, placeholders`}</span></summary>
    <p class="help">The spaces the building needs beyond its homes. The engine lays each out: "by the entry" beside the lobby, "upper floors" above the ground floor. ${own ? "" : "Change any figure and the brief becomes yours."}</p>
    <div class="table-scroll"><table class="plain brief-table"><thead><tr><th scope="col">Space</th><th scope="col">m²</th><th scope="col">Where</th><th scope="col">Next to</th><th scope="col"><span class="sr-only">Remove</span></th></tr></thead>
      <tbody>${items.map(row).join("")}</tbody></table></div>
    <div class="form-actions"><button type="button" class="btn btn-small" id="brief-add">Add a space</button>${own ? `<button type="button" class="btn btn-quiet btn-small" id="brief-reset">Back to the default brief</button>` : ""}</div>
  </details>`;
}

/* Where the brief is written: the suggestion's answers while it is not yet used (they travel with the option), else the
   option itself, which marks the memo stale. */
function save(list, said, rerender) {
  if (guide.suggestion && !guide.suggestionUsed) {
    guide.answers = guide.answers || {};
    guide.answers.program_brief = list;
  } else if (state.option) {
    setPath(state.option, "program_brief", list);
    state.optionDirty = true;
    const d = $("#option-dirty"); if (d) d.hidden = false;
    markStale("the program brief");
  } else return;
  saveDraft();
  setStatus(said, "info");
  if (rerender) rerender();
}

export function wireBriefEditor(el, o, rerender) {
  const fold = $(".brief-fold", el);
  if (!fold || !o) return;
  const read = () => $$("tbody tr", fold).map(tr => ({
    label: ($(".brief-label", tr).value || "").trim(), area_m2: Number($(".brief-area", tr).value) || 0,
    where: $(".brief-where", tr).value, next_to: $(".brief-entry", tr).checked ? "entry" : null,
    ...(/dining/i.test($(".brief-label", tr).value || "") ? { replaces_amenity: true } : {}),
  })).filter(x => x.label && x.area_m2 > 0);
  $$("input, select", fold).forEach(c => c.addEventListener("change", () => save(read(), "The program brief is yours now; the next run lays it out.")));
  $$(".brief-remove", fold).forEach(b => b.addEventListener("click", () => { b.closest("tr").remove(); save(read(), "Space removed from the brief.", rerender); }));
  const add = $("#brief-add", fold);
  if (add) add.addEventListener("click", () => { save([...read(), { label: "A space", area_m2: 10, where: "ground", next_to: null }], "A space added: name it and give its area.", rerender); });
  const reset = $("#brief-reset", fold);
  if (reset) reset.addEventListener("click", () => save(null, "Back to the default brief for this kind of housing.", rerender));
}
