/* Small helpers every part of the page uses: DOM lookups, escaping, number formats, the status strip, paths
   into a JSON object, and a few file and clipboard chores. Nothing here knows about sites, options or runs. */

export const $ = (sel, root = document) => root.querySelector(sel);

export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

export function h(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export const STATUS_WORD = { pass: "Pass", conditional: "Conditional", fail: "Fail", uncertain: "Uncertain", not_applicable: "Not applicable", info: "Info" };

export const VERDICT_OUTRIGHT = { no: "Not outright.", yes: "Allowed outright.", "yes, with conditions": "Outright, with conditions.", "not yet confirmed": "Outright: not yet confirmed.", "not assessed": "Outright: not assessed." };

export function pill(status) {
  return `<span class="pill pill-${h(status)}">${h(STATUS_WORD[status] || status)}</span>`;
}

/* A revision mark, the drafting way: a delta with its letter, beside whatever a comparison changed. */
export const REV = `<svg class="rev" viewBox="0 0 16 14" aria-hidden="true"><path d="M8 1.2 15 12.8H1Z"/><text x="8" y="11.2" text-anchor="middle">A</text></svg><span class="sr-only">(revised)</span>`;

/* Scrolls follow the reader's motion setting. */
export function scrollBehavior() { return reducedMotion() ? "auto" : "smooth"; }

export function cap(s) { s = String(s || ""); return s.charAt(0).toUpperCase() + s.slice(1); }

/* The status a verdict word stands for, so a card can wear its colour. */
const VERDICT_STATUS = { no: "fail", yes: "pass", "yes, with conditions": "conditional", "not yet confirmed": "uncertain", "not assessed": "uncertain" };

export function verdictStatus(word) { return VERDICT_STATUS[word] || ""; }

export function fmtNum(x) {
  if (typeof x === "number") {
    if (Number.isInteger(x)) return x.toLocaleString("en-CA");
    return x.toLocaleString("en-CA", { maximumFractionDigits: 3 });
  }
  return String(x);
}

export function fmtValues(v) {
  const bits = [];
  for (const [k, x] of Object.entries(v || {})) {
    if (x === null || x === undefined || typeof x === "object") continue;
    bits.push(`${k.replace(/_/g, " ")} = ${fmtNum(x)}`);
  }
  return bits.join("; ");
}

/* Lead sentence in ink, the rest in grey. */
export function leadCont(text) {
  const t = String(text || "");
  const m = t.match(/^(.+?[.;:])\s+(.+)$/s);
  if (!m) return `<span class="lead">${h(t)}</span>`;
  return `<span class="lead">${h(m[1])}</span> <span class="cont">${h(m[2])}</span>`;
}

/* A finding that opens with the program's name already printed in its title ("BC Builds: fit cannot…" under
   "BC Builds: eligibility…") drops the repeat. */
export function withoutRepeat(title, finding) {
  const m = String(finding || "").match(/^([^:;.]{3,60}):\s+(.+)$/s);
  if (!m || !String(title || "").toLowerCase().includes(m[1].toLowerCase())) return finding;
  return cap(m[2]);
}

export function sourceLink(src) {
  if (!src || (!src.title && !src.url)) return "";
  const label = (src.title || src.url) + (src.section ? `, ${src.section}` : "");
  if (src.url) return `<a href="${h(src.url)}" target="_blank" rel="noopener">${h(label)}</a>${unverifiedTag(src)}`;
  return h(label) + unverifiedTag(src);
}

/* A rule whose figures were entered from recollection and not read from the document says so wherever it is cited
   (16 Nov 2026: the district schedules seeded that day, the building code's exit clauses). */
export function unverifiedTag(src) {
  return src && src.verified === false ? ` <span class="unverified" title="${h(src.verify || "Entered from recollection, not read from the document; confirm before relying on it")}">unverified</span>` : "";
}

/* One line of feedback for every action, in the status strip under the steps: info, ok, error or busy. */
export function setStatus(msg, kind = "info") {
  const s = $("#status");
  $("#status-text", s).textContent = msg;
  s.className = "strip " + (kind === "info" ? "" : kind);
}

export function toast(msg, isError = false) { setStatus(msg, isError ? "error" : "ok"); }

export function getPath(obj, path) {
  return path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), obj);
}

export function setPath(obj, path, value) {
  const keys = path.split(".");
  let o = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    if (o[keys[i]] == null || typeof o[keys[i]] !== "object") o[keys[i]] = {};
    o = o[keys[i]];
  }
  o[keys[keys.length - 1]] = value;
}

export function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export async function fetchJSON(rel, optional = false) {
  const r = await fetch(rel, { cache: "no-cache" });
  if (!r.ok) { if (optional && r.status === 404) return null; throw new Error(`${r.status} for ${rel}`); }
  return r.json();
}

export async function fetchText(rel, optional = false) {
  const r = await fetch(rel, { cache: "no-cache" });
  if (!r.ok) { if (optional && r.status === 404) return null; throw new Error(`${r.status} for ${rel}`); }
  return r.text();
}

export function blobUrl(text, type) {
  return URL.createObjectURL(new Blob([text], { type }));
}

export function downloadJSON(obj, name) {
  const a = document.createElement("a");
  a.href = blobUrl(JSON.stringify(obj, null, 2) + "\n", "application/json");
  a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
}

export function reducedMotion() {
  return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast("Copied."); }
  catch (e) {
    const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); toast("Copied."); } catch (e2) { toast("Could not copy; select it by hand.", true); }
    ta.remove();
  }
}
