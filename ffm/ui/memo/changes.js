/* What changed between two runs (engine diff.json): a change of rules (a revision) or two options under the same
   rules, rule by rule. */

import { $, h, pill, REV } from "../core/util.js";
import { state } from "../core/state.js";
import { api } from "../core/api.js";
import { rev } from "../runs.js";
import { compareKind, dateWords, idBreak, optionName } from "./memo.js";

/* The engine's words for a change (engine.diff), as a reader would say them. Between two options read under the same
   rules a reworded finding is the option's numbers changing, not the rule. */
export function changeWord(c, kind = "rules") {
  if (c.change === "changed") return c.from_version !== c.to_version ? (c.from === c.to ? "new version" : "new version and status") : "status changed";
  if (c.change === "finding_changed") return kind === "rules" ? "finding reworded" : "numbers changed";
  return { added: "rule added", removed: "rule dropped" }[c.change] || String(c.change).replace(/_/g, " ");
}

/* A change to a rule that applies to neither run: not applicable on both sides, or added or dropped while not
   applicable (17 Nov 2026, Kai: 52 of 61 rows between the two Glen Drive runs were districts added since). A status
   that moves to or from not applicable is a real change and stays in view. */
export const naChange = c => [c.from, c.to].filter(Boolean).every(s => s === "not_applicable");

/* A comparison in a few words for the status strip and the title block: how many statuses and versions moved, without
   the rule ids. */
export function changesPhrase(d) {
  // counted over the rules that apply to either run, as the card lists them; the rest are a count at the end
  const all = d.changes || [], ch = all.filter(c => !naChange(c)), na = all.length - ch.length;
  const tail = na ? `; ${na} more for other districts, policies or programs` : "";
  if (!ch.length) return (all.length ? "no rule that applies to either run changed" : "no rule changed version or status") + tail;
  const st = ch.filter(c => c.from !== c.to).length;
  const ver = ch.filter(c => c.from_version && c.to_version && c.from_version !== c.to_version).length;
  const bits = [st && (st === 1 ? "1 status differs" : `${st} statuses differ`), ver && `${ver} new version${ver === 1 ? "" : "s"}`].filter(Boolean);
  return (bits.length ? bits.join(", ") : `the same statuses, ${ch.length} finding${ch.length === 1 ? "" : "s"} with other numbers`) + tail;
}

/* An option's name up to its colon: "As approved by Council, 25 Jul 2024", not the description after it. */
export const shortName = s => String(s || "").split(":")[0].trim();

/* What a comparison found, for the status strip and the toasts: the rules' dates when the rules moved, the compared
   option's name when two options were read under the same rules. */
export function compareSummary(run) {
  const d = run.diff;
  if (!d) return "";
  return compareKind(d) === "rules"
    ? `${rev(run.run_id)}, rules as of ${dateWords(d.current_as_of)}, against ${state.compareRun ? rev(state.compareRun) : "an earlier memo"}, rules as of ${dateWords(d.previous_as_of)}: ${changesPhrase(d)}`
    : `${rev(run.run_id)} against ${state.compareRun ? `${rev(state.compareRun)}, ` : ""}${run.compareLedger ? shortName(optionName(run.compareLedger)) : `a memo as of ${dateWords(d.previous_as_of)}`}: ${changesPhrase(d)}`;
}

/* The note beside the pickers speaks only when the memo cannot: a comparison waiting for the next run, or a run
   recorded against an earlier one that the list cannot tell apart. Once two runs are compared, the Side by side
   card says it, so the note stays empty. */
export function setCompareNote(d) {
  const run = state.run;
  let note = "";
  if (!run && state.compareRun) note = "Applies to the next run.";
  else if (run && d && !run.compareLedger) note = `This memo was recorded against an earlier one, rules as of ${dateWords(d.previous_as_of)}; choose it under Compare with… to see the two side by side.`;
  $("#compare-note").textContent = note;
}

/* Why two stamps differ, as precisely as the two ledgers allow: the rule files, the as-of date, the site's or the
   option's inputs. The inputs are compared key by key, whatever their order. */
const stable = v => JSON.stringify(v, (k, x) => (x && typeof x === "object" && !Array.isArray(x) ? Object.fromEntries(Object.keys(x).sort().map(key => [key, x[key]])) : x));

export async function attachCause(run) {
  const d = run.diff;
  if (!d || !state.compareRun) return;
  try {
    const [site, folder] = state.compareRun.split("/");
    const prev = await api(`/api/runs/${encodeURIComponent(site)}/${encodeURIComponent(folder)}`);
    run.compareLedger = prev.ledger || null;   // for the side-by-side card
    run.compareProforma = prev.proforma || null;   // its money, its drawings and its fit, for the same card (15 Nov 2026)
    run.compareLayout = prev.layout || null;
    run.compareMassing = prev.massing || null;
    const a = (prev.ledger && prev.ledger.inputs) || {}, b = (run.ledger && run.ledger.inputs) || {};
    const changed = [stable(a.site) !== stable(b.site) && "the site's inputs", stable(a.option) !== stable(b.option) && "the option's inputs"].filter(Boolean);
    const date = d.previous_as_of !== d.current_as_of ? `the rules date (${dateWords(d.previous_as_of)} → ${dateWords(d.current_as_of)})` : null;
    const files = d.rules_changed ? "the rule files changed" : "same rule files";
    const same = changed.length ? "" : ", same site and option";
    const because = [date, ...changed].filter(Boolean);
    d.cause = `${files}${same}; the difference is ${because.length ? because.join(" and ") : (d.rules_changed ? "in the rule files alone" : "not in the inputs or the date")}`;
    d.kind = d.rules_changed || date ? "rules" : changed.length ? "options" : "same";
  } catch (e) {
    d.cause = null;   // the earlier run could not be read: fall back to the general sentence
  }
}

/* What changed. When the rules moved it is a revision: the delta in its heading, the version in force on each row.
   Between two options read under the same rules it is the options' numbers, so the version column goes. Rows are
   named by the rule's title, the status read from the compared run (B) to this one (A). */
export function renderChanges(d, L, run) {
  const kind = compareKind(d), rules = kind === "rules";
  const titles = Object.fromEntries(((L && L.results) || []).map(r => [r.rule_id, r.title]));
  const changes = d.changes || [];
  // the status reads from the run compared to this one, each named by its revision (20 Nov 2026: "B → A")
  const fromRev = state.compareRun ? rev(state.compareRun) : "earlier", toRev = rev(run && run.run_id);
  const statusHead = rules ? "Status" : `Status, ${fromRev} → ${toRev}`;
  const row = c => {
    const ver = c.from_version && c.to_version && c.from_version !== c.to_version;
    const status = c.from && c.to ? (c.from === c.to ? `${pill(c.to)} <span class="cont">unchanged</span>` : `${pill(c.from)} → ${pill(c.to)}`) : (c.to ? pill(c.to) : c.from ? pill(c.from) : "—");
    return `<tr>
      <td data-label="Rule"><span class="rule-title">${h(titles[c.rule_id] || c.rule_id)}</span><code class="rule-id">${idBreak(c.rule_id)}</code><div class="cont">${h(changeWord(c, kind))}</div></td>
      ${rules ? `<td class="ver" data-label="Version in force">${ver ? `<span class="was">${h(c.from_version)}</span> → ${h(c.to_version)}` : h(c.to_version || c.from_version || "—")}</td>` : ""}
      <td class="trans" data-label="${h(statusHead)}">${status}</td>
      <td data-label="Now reads"><span class="measure">${h(c.finding)}</span></td>
    </tr>`;
  };
  // the rules that apply to neither run fold into one row at the foot, as the ledger folds its own
  const shown = changes.filter(c => !naChange(c)), na = changes.filter(naChange);
  const cols = rules ? 4 : 3;
  const naRow = na.length ? `<tr class="na-row"><td colspan="${cols}"><details class="fold na-fold"><summary>${na.length} rule${na.length === 1 ? "" : "s"} not applicable to either run, for other districts, policies or programs</summary>
      <table class="plain"><tbody>${na.map(row).join("")}</tbody></table></details></td></tr>` : "";
  const rows = shown.map(row).join("") + naRow;
  const sameVerdict = shown.length && shown.every(c => c.from === c.to && c.from_version && c.from_version !== c.to_version);
  const cause = d.cause || (d.rules_changed ? "the rule files themselves changed" : "the rule files are the same; the difference comes from the as-of date or the inputs");
  // dates as a reader writes them; the cause sentence's own dates too (attachCause writes them ISO)
  const cause2 = cause.replace(/\d{4}-\d\d-\d\d/g, x => dateWords(x));
  const lead = rules
    ? `<b>${h(state.compareRun ? rev(state.compareRun) : "The earlier memo")}</b> → <b>${h(toRev)}</b> · ${h(cause2)}.`
    : `<b>${h(state.compareRun ? rev(state.compareRun) : "The other run")}</b> → <b>${h(toRev)}</b> · same rules, as of ${h(dateWords(d.current_as_of))}; ${h(cause2.replace(/^same rule files(, same site and option)?; /, ""))}.`;
  return `<section class="card section changes" id="changes">
    <h2>${rules ? `${REV} What changed: rules as of ${h(dateWords(d.current_as_of))} against ${h(dateWords(d.previous_as_of))}` : "What changed between the two options"}</h2>
    <p class="stamps">${lead}</p>
    ${changes.length ? `${sameVerdict ? `<p class="same">Same verdict${shown.length === 1 ? "" : "s"}, new version${shown.length === 1 ? "" : "s"}: the memo names the version it used.</p>` : ""}${!shown.length ? `<p>No rule that applies to either run changed version or status.</p>` : ""}
    <table class="plain"><thead><tr><th>Rule</th>${rules ? "<th>Version in force</th><th>Status</th>" : `<th>${h(statusHead)}</th>`}<th>Now reads</th></tr></thead><tbody>${rows}</tbody></table>`
    : `<p>No rule changed version or status between the two runs.</p>`}
  </section>`;
}
