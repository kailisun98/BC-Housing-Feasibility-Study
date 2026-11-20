/* Words in this memo (20 Nov 2026, from a board reader who listed the terms they did not understand): one plain
   sentence for each term this memo uses, and only those, folded after the four answers and printed before the
   ledger on paper. Each term says when the memo uses it, from the run itself. Pure. */

import { h } from "../core/util.js";

const results = run => ((run && run.ledger && run.ledger.results) || []).filter(r => r.status !== "not_applicable");
const checks = run => new Set(results(run).map(r => r.check));
const statuses = run => new Set([...results(run).map(r => r.status), ...(((run && run.ledger && run.ledger.summary && run.ledger.summary.answers) || {}).unsure || []).map(u => u.status)]);
const opt = run => (run && run.ledger && run.ledger.inputs && run.ledger.inputs.option) || {};
const site = run => (run && run.ledger && run.ledger.inputs && run.ledger.inputs.site) || {};
const ans = run => (run && run.ledger && run.ledger.summary && run.ledger.summary.answers) || {};
const pf = run => (run && run.proforma && run.proforma.available ? run.proforma : null);
const said = (run, re) => re.test(JSON.stringify(((run && run.ledger) || {}).results || []) + JSON.stringify(ans(run)));

/* [term, sentence, used by this memo?] */
export const WORDS = [
  ["FSR", "Floor space ratio: the building's floor area divided by the lot's area, so FSR 2.0 on a 1,000 m² lot is 2,000 m² of floor.",
    run => !!(opt(run).gfa_m2 && site(run).site_area_m2) || said(run, /\bFSR\b/)],
  ["Outright", "What the site's zoning already allows, with a development permit and no change to the zoning.",
    run => !!(ans(run).allowed && ans(run).allowed.outright)],
  ["By rezoning", "What Council could allow by changing the site's zoning for this project, under the City policy named in answer 1.",
    run => !!(ans(run).allowed && ans(run).allowed.rezoning_path)],
  ["CD-1", "Comprehensive Development: a zoning district written for one site, its own by-law setting the height, floor area and uses.",
    run => /CD-1/.test(`${site(run).zoning_district || ""} ${(ans(run).allowed || {}).rezoning_path || ""}`)],
  ["Plate", "One floor of the building as drawn, its width by its depth; the homes are laid out on it.",
    run => !!run.massing || !!run.layout],
  ["Setbacks, yards and the envelope", "Yards (setbacks) are the distances the building keeps from the front, side and rear lot lines; what is left inside them is the envelope the building can stand in.",
    run => !!run.massing || !!opt(run).setbacks_m],
  ["Staff benchmark", "The height and density City staff start from when they assess a rezoning under the policy: negotiated, not a limit.",
    run => checks(run).has("rezoning_policy_social_housing") || !!(run.massing && run.massing.policy_benchmark)],
  ["RGI", "Rent geared to income: a home whose rent is set at 30% of the household's income.",
    run => !!opt(run).rent_tiers_units || checks(run).has("chf_fit") || !!pf(run)],
  ["HILs", "Housing Income Limits: BC Housing's income ceilings, by size of home, under which a household qualifies for subsidised rent.",
    run => checks(run).has("social_housing_definition") || said(run, /\bHILs?\b/)],
  ["The 30/50/20 mix", "The Community Housing Fund's split of homes: 30% at moderate (near-market) rents, 50% rent geared to income, 20% deep subsidy at the income-assistance shelter rate.",
    run => checks(run).has("chf_fit")],
  ["Conditional", "Allowed or met only if something named beside it is done or agreed.",
    run => statuses(run).has("conditional")],
  ["Uncertain", "Not known yet: a figure is missing or the judgement belongs to a person, and the open items say who.",
    run => statuses(run).has("uncertain")],
  ["Not applicable", "The rule is for another district, policy or program and does not apply to this site or option.",
    run => ((run && run.ledger && run.ledger.results) || []).some(r => r.status === "not_applicable")],
  ["Revision (R1, R2…)", "Each memo on a site is numbered in the order it was written, the way a drawing numbers its issues.",
    () => true],
  ["Rules as of", "The date the rules were read at: each rule is applied in the version that was in force that day.",
    () => true],
  ["References (A3, C5…)", "A rule's place in the memo: its layer's letter (A zoning, B the Province, C City policy, D design standards, E funders, F cost assumptions) and its number in that layer, the same on screen and on paper.",
    () => true],
  ["Capital cost: hard, soft, contingency", "Everything it takes to build: hard costs are the construction, soft costs the design, permits, financing and legal fees, and the contingency a sum held for what is not yet known; land is added where it is bought.",
    run => !!pf(run)],
  ["Gap and the 15% line", "The gap is the capital cost less the funding found; this tool calls a gap within 15% of the cost close, and above that the project needs more sources. The 15% is the screen's own line, not a funder's rule.",
    run => !!pf(run)],
  ["The 1.10 coverage", "Lenders ask that the yearly rent left after running costs cover the mortgage payment 1.10 times; that ratio sets how much the project can borrow.",
    run => !!pf(run)],
];

/* The terms this memo uses, in the order above. */
export const wordsFor = run => WORDS.filter(([, , used]) => { try { return used(run); } catch (e) { return false; } });

/* On screen: folded after the four answers. */
export function wordsHtml(run) {
  const w = wordsFor(run);
  if (!w.length) return "";
  return `<details class="card words">
    <summary><span class="words-act">Words in this memo</span> <span class="cont">· ${w.length} terms in one sentence each</span></summary>
    <dl class="words-list">${w.map(([t, s]) => `<div><dt>${h(t)}</dt><dd>${h(s)}</dd></div>`).join("")}</dl>
  </details>`;
}
