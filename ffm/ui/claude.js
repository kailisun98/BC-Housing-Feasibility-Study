/* Claude in the loop (architect mode): a person's own key, "Ask Claude about this site" and "Read the district
   schedule with Claude"; the model proposes, a person confirms, the engine decides. */

import { $, $$, cap, h, setPath, setStatus, toast, todayISO } from "./core/util.js";
import { guide, state, STATIC } from "./core/state.js";
import { api, CLAUDE_MODEL, postJSON } from "./core/api.js";
import { engine, loadEngine } from "./core/engine.js";
import { districtOf, SITE_FIELDS } from "./fields.js";
import { refreshSummary, renderForm } from "./schedule.js";
import { onSiteChange } from "./files.js";
import { scheduleFor } from "./route-stage.js";

/* Claude proposes, the person confirms; in the architect's Site schedule only (16 Nov 2026: the manager no longer
   meets it at stops 1 and 3). The model is reached with a key: the local server's own (FFM_CLAUDE_KEY on that
   machine) or the person's, typed into the page and kept in this browser only (localStorage), sent with each request
   to the local server (which hands it to the SDK and never stores it) or, on the web, straight to the Messages API
   from the page. The site's public fields go to the model; the proposal comes back with evidence and a confidence,
   and each field enters the site only when its Confirm is pressed, marked with who confirmed it and when. */
const KEY_STORE = "ffm.claude.key";

const CLAUDE_API = "https://api.anthropic.com/v1/messages";

function claudeKey() { try { return localStorage.getItem(KEY_STORE) || ""; } catch (e) { return ""; } }

function setClaudeKey(k) { try { if (k) localStorage.setItem(KEY_STORE, k); else localStorage.removeItem(KEY_STORE); } catch (e) { /* storage off: the key lasts this page only */ guide.sessionKey = k || ""; } }

function keyInHand() { return claudeKey() || guide.sessionKey || ""; }

function hasClaude() { return !!((state.caps && state.caps.claude) || keyInHand()); }

const keyTail = k => (k ? `…${k.slice(-4)}` : "");

/* The key box: typed once, kept in this browser, forgotten with one click. Shown wherever the model is offered. */
function renderKeyBox(id) {
  const serverHas = state.caps && state.caps.claude;
  const mine = keyInHand();
  if (serverHas && !mine) return `<p class="help keybox-note">The local server holds a key (${h(state.caps.model || "")}); your own is not needed.</p>`;
  if (mine) return `<div class="keybox" id="${id}"><span class="help">Your key <code>${h(keyTail(mine))}</code> is kept in this browser only and sent ${STATIC ? "straight to Anthropic from this page" : "to the local server, which passes it on and never stores it"}.</span><button class="btn btn-small" type="button" data-forget-key="1">Forget it</button></div>`;
  return `<div class="keybox" id="${id}">
    <label class="field"><span class="label">Your Anthropic API key</span><input type="password" class="key-input" autocomplete="off" spellcheck="false" placeholder="sk-ant-…" aria-describedby="${id}-help"></label>
    <div class="form-actions"><button class="btn btn-small" type="button" data-save-key="1">Use this key</button><span class="help" id="${id}-help">Kept in this browser only (localStorage), never in a file or the repository; sent ${STATIC ? "straight to Anthropic from this page" : "to the local server with each request, which passes it to the SDK and does not store it"}. A few cents a reading.</span></div>
  </div>`;
}

function wireKeyBoxes(el) {
  $$("[data-save-key]", el).forEach(b => b.addEventListener("click", () => {
    const inp = b.closest(".keybox").querySelector(".key-input");
    const k = (inp.value || "").trim();
    if (k.length < 20) { toast("That does not look like a key.", true); inp.focus(); return; }
    setClaudeKey(k);
    renderClaude();
    setStatus(`Key ${keyTail(k)} kept in this browser. Ask Claude is on.`, "ok");
  }));
  $$("[data-forget-key]", el).forEach(b => b.addEventListener("click", () => { setClaudeKey(""); guide.sessionKey = ""; renderClaude(); setStatus("Key forgotten.", "info"); }));
  $$(".key-input", el).forEach(i => i.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); const b = i.closest(".keybox").querySelector("[data-save-key]"); if (b) b.click(); } }));
}

/* The architect's two Claude folds in the Site schedule: an odd lot at its head, a missing district schedule under
   the district's row. Drawn again after each schedule render and each step of a reading. */
export function renderClaude() {
  const top = $("#site-claude"), slot = $("#claude-schedule-slot");
  if (top) {
    top.innerHTML = state.site ? `<details class="claude-fold"${guide.proposal || guide.busy.claude ? " open" : ""}><summary>Odd lot? Ask Claude about it <span class="cont">(with a key; optional)</span></summary>
      <p class="help">The model proposes the equivalent rectangle, the frontage street and what is odd, with its evidence; you confirm each field under your name.</p>
      ${renderKeyBox("keybox-site")}
      ${hasClaude() ? `<div class="form-actions"><button class="btn btn-small" type="button" id="guide-ask-claude"${guide.busy.claude ? " disabled" : ""}>${guide.busy.claude ? "Reading…" : "Ask Claude about this site"}</button></div>${renderProposal(guide.proposal)}` : ""}
    </details>` : "";
    wireClaude(top);
  }
  if (slot) {
    const district = districtOf(state.site || {}).toUpperCase();
    const known = scheduleFor(district, (state.site || {}).cd1_bylaw_number);
    slot.innerHTML = district && (!known || guide.ruleProposal) ? `<details class="claude-fold"${hasClaude() || guide.ruleProposal ? " open" : ""}><summary>Read the ${h(district)} schedule with Claude <span class="cont">(the rules have ${known ? "it now" : "none for it"})</span></summary>
      <p class="help">Save the schedule's PDF from the City's by-law site (it refuses scripts), choose it here, and the model proposes its clauses with the quote behind each. You check the quotes against the PDF and confirm under your name; the rules file then cites the schedule, the model and you.</p>
      ${renderKeyBox("keybox-rule")}
      ${hasClaude() ? `<div class="sched-form">
        <label class="field"><span class="label">Schedule PDF</span><input type="file" id="sched-file" accept=".pdf,.png,.jpg,.jpeg,.txt"></label>
        <label class="field"><span class="label">District</span><input type="text" id="sched-district" value="${h(guide.scheduleDistrict || district)}" placeholder="RT-3"></label>
        <label class="field"><span class="label">Its address on the City's site</span><input type="url" id="sched-url" value="${h(guide.scheduleUrl || (/^CD-1 \(/.test(district) ? `https://cd1-bylaws.vancouver.ca/${district.replace(/\s+/g, "").toLowerCase()}.PDF` : `https://bylaws.vancouver.ca/zoning/zoning-by-law-district-schedule-${district.toLowerCase()}.pdf`))}" placeholder="https://bylaws.vancouver.ca/zoning/…"></label>
        <div class="form-actions"><button class="btn btn-small" type="button" id="guide-read-schedule"${guide.busy.schedule ? " disabled" : ""}>${guide.busy.schedule ? "Reading…" : "Read the schedule"}</button><span class="help">The PDF goes to the model and nowhere else; the log keeps its name and hash.</span></div>
      </div>${renderRuleProposal(guide.ruleProposal)}` : ""}
    </details>` : "";
    wireClaude(slot);
  }
}

function wireClaude(el) {
  const on = (sel, fn) => { const b = $(sel, el); if (b) b.addEventListener("click", fn); };
  on("#guide-ask-claude", guideAskClaude);
  $$("[data-confirm-key]", el).forEach(b => b.addEventListener("click", () => confirmProposal(b.dataset.confirmKey, b.dataset.confirmAll === "1")));
  wireKeyBoxes(el);
  on("#guide-read-schedule", guideReadSchedule);
  on("#confirm-rules", confirmRuleProposal);
  $$(".claude-fold", el).forEach(d => d.addEventListener("toggle", () => { if (d.open) { const i = $(".key-input", d); if (i) i.focus({ preventScroll: true }); } }));
}

/* One call to the model, either way: the local server (its key or the person's) or, on the web, the Messages
   API from the page with the person's key; the engine builds the request and reads the response in both cases. */
async function callClaude(kind, args) {
  const key = keyInHand();
  if (!STATIC) {
    const body = Object.assign({}, args);
    if (key) body.api_key = key;
    return postJSON(kind === "rule" ? "/api/propose/rule" : "/api/propose/site", body);
  }
  if (!key) throw new Error("no key: type your Anthropic key first.");
  await loadEngine();
  const doc = args.document || {};
  const made = JSON.parse(engine.proposeRequest(kind, args.site ? JSON.stringify(args.site) : "", doc.data_b64 || "", doc.name || "", args.district || "", CLAUDE_MODEL));
  const r = await fetch(CLAUDE_API, { method: "POST", headers: { "content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01", "anthropic-dangerous-direct-browser-access": "true" }, body: JSON.stringify(made.request) });
  const j = await r.json().catch(() => null);
  if (!r.ok) throw new Error((j && j.error && j.error.message) || `${r.status} ${r.statusText}`);
  const res = JSON.parse(engine.proposalFromResponse(kind, JSON.stringify(j), made.tool, made.model, made.prompt_sha256, args.site ? JSON.stringify(args.site) : "", args.district || "", args.url || "", made.document ? JSON.stringify(made.document) : ""));
  res.file = null;   // nothing is written on the web; the proposal lives in this tab
  return res;
}

async function guideAskClaude() {
  if (!state.site) { toast("Choose a site first.", true); return; }
  const who = ($("#confirm-by") && $("#confirm-by").value.trim()) || "";
  guide.busy.claude = true; renderClaude();
  setStatus(`Asking ${(state.caps && state.caps.model) || CLAUDE_MODEL} to read the site… nothing enters the site until you confirm it.`, "busy");
  try {
    guide.proposal = await callClaude("site", { site: state.site });
    guide.proposal.by = who;
    setStatus(`${guide.proposal.items.length} proposed item${guide.proposal.items.length === 1 ? "" : "s"} from ${guide.proposal.model}${guide.proposal.file ? `, logged as proposals/${guide.proposal.file}` : ", kept in this tab"}. Confirm the ones that are right.`, "ok");
  } catch (e) {
    guide.proposal = null;
    toast(`The model could not read the site: ${e.message}`, true);
  } finally {
    guide.busy.claude = false; renderClaude();
  }
}

/* Reading a district schedule: a PDF chosen from the person's disk goes to the model (through the local server,
   which neither stores it nor writes it); the clauses come back with their quotes; a named person confirms them into
   the rules, and the site is read again under them. On the web the proposal can be made and read but not
   confirmed, since the rules there are the published files. */
function readFileB64(file) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onload = () => resolve(String(fr.result).split(",")[1] || "");
    fr.onerror = () => reject(new Error("could not read the file"));
    fr.readAsDataURL(file);
  });
}

async function guideReadSchedule() {
  const fileIn = $("#sched-file");
  const file = fileIn && fileIn.files && fileIn.files[0];
  const district = (($("#sched-district") || {}).value || "").trim().toUpperCase();
  const url = (($("#sched-url") || {}).value || "").trim();
  if (!file) { toast("Choose the schedule's PDF first.", true); return; }
  if (!district) { toast("Name the district the schedule is for.", true); return; }
  if (file.size > 12 * 1024 * 1024) { toast("The file is over 12 MB; a district schedule is a few hundred KB.", true); return; }
  guide.busy.schedule = true; guide.scheduleDistrict = district; guide.scheduleUrl = url; renderClaude();
  setStatus(`Reading ${file.name} for ${district}… the PDF goes to the model and nowhere else; nothing enters the rules until you confirm.`, "busy");
  try {
    const data_b64 = await readFileB64(file);
    guide.ruleProposal = await callClaude("rule", { district, url, document: { name: file.name, data_b64 } });
    setStatus(`${guide.ruleProposal.items.length} clause item${guide.ruleProposal.items.length === 1 ? "" : "s"} proposed for ${district} from ${guide.ruleProposal.model}${guide.ruleProposal.file ? `, logged as proposals/${guide.ruleProposal.file}` : ""}. Check each quote against the PDF, then confirm under your name.`, "ok");
  } catch (e) {
    guide.ruleProposal = null;
    toast(`The model could not read the schedule: ${e.message}`, true);
  } finally {
    guide.busy.schedule = false; renderClaude();
  }
}

async function confirmRuleProposal() {
  const P = guide.ruleProposal;
  if (!P || !P.file) { toast(STATIC ? "On the web the rules are the published files; confirm on the local server." : "Read a schedule first.", true); return; }
  const by = (($("#confirm-rules-by") || {}).value || "").trim();
  if (!by) { toast("Say who confirms: your name goes on each rule's source.", true); const i = $("#confirm-rules-by"); if (i) i.focus(); return; }
  setStatus("Writing the confirmed clauses into the rules…", "busy");
  try {
    const rep = await postJSON("/api/confirm", { file: P.file, by });
    P.confirmedRules = rep.confirmed;
    P.by = by;
    state.rules = await api(`/api/rules?as_of=${encodeURIComponent($("#as-of").value || todayISO())}`);
    guide.reading = null; guide.suggestion = null;
    renderClaude();
    setStatus(`${rep.confirmed.length} rule${rep.confirmed.length === 1 ? "" : "s"} confirmed by ${by} for ${P.district}: ${rep.confirmed.join(", ")}. Run the rules again: the schedule now applies.`, "ok");
  } catch (e) {
    toast(`Could not confirm: ${e.message}`, true);
  }
}

function renderRuleProposal(P) {
  if (!P) return "";
  const show = it => (it.value == null ? "—" : typeof it.value === "boolean" ? (it.value ? "yes" : "no") : String(it.value));
  const rows = P.items.map(it => `<li class="prop-row">
      <div class="prop-head"><b>${h(cap(it.key.replace(/_/g, " ")))}</b> <span class="prop-val">${h(show(it))}</span> <span class="conf" title="the model's confidence">${h(Math.round(it.confidence * 100))}%</span>${it.section ? ` <span class="rule-id">${h(it.section)}</span>` : ""}${it.page != null ? ` <span class="cont">p. ${h(it.page)}</span>` : ""}</div>
      ${it.evidence ? `<div class="cont prop-ev">“${h(it.evidence)}”</div>` : ""}
    </li>`).join("");
  const done = P.confirmedRules && P.confirmedRules.length;
  return `<div class="proposal" id="guide-rule-proposal">
    <div class="prop-top"><span class="prop-by">${h(P.district)} schedule, proposed by ${h(P.model)}</span><span class="cont">source: claude · ${P.document ? `${h(P.document.name)}, sha256 ${h(String(P.document.sha256).slice(0, 12))}…` : ""}${P.file ? ` · logged as proposals/${h(P.file)}` : " · kept in this tab"} · the base maximums become the outright rules, the Director's increases go in the verify note</span></div>
    <ul class="prop-list">${rows}</ul>
    ${done ? `<p class="help">Confirmed by <b>${h(P.by)}</b>: ${P.confirmedRules.map(id => `<code>${h(id)}</code>`).join(" ")}. Run the rules again; the suggestion now takes its envelope and yards from the schedule.</p>`
      : (P.file ? `<div class="form-actions"><label class="field inline"><span class="label">Confirmed by</span><input type="text" id="confirm-rules-by" value="${h(P.by || "")}" placeholder="your name"></label><button class="btn btn-small btn-primary" type="button" id="confirm-rules">Confirm all into the rules</button><span class="help">Check every quote against the PDF first; the rules file names you.</span></div>`
        : `<p class="help">On the web the rules are the published files: run the local server to confirm a reading into them.</p>`)}
  </div>`;
}

const SITE_PROPOSAL_KEYS = { zoning_district: "zoning_district", site_area_m2: "site_area_m2", frontage_m: "frontage_m", depth_m: "depth_m",
                             frontage_street: "context.street.name", corner_lot: "context.corner_lot", lane_behind: "context.lane_behind" };

function confirmProposal(key, all) {
  const P = guide.proposal;
  if (!P || !state.site) return;
  const by = ($("#confirm-by") && $("#confirm-by").value.trim()) || "";
  if (!by) { toast("Say who confirms: your name goes on the site file beside each confirmed field.", true); const i = $("#confirm-by"); if (i) i.focus(); return; }
  const items = all ? P.items : P.items.filter(it => it.key === key);
  const today = todayISO();
  state.site.confirmed = state.site.confirmed || {};
  const notes = [];
  for (const it of items) {
    if (SITE_PROPOSAL_KEYS[it.key]) setPath(state.site, SITE_PROPOSAL_KEYS[it.key], it.value);
    else if (it.value) notes.push(`${it.key.replace(/_note$/, "").replace(/_/g, " ")}: ${it.value}`);
    state.site.confirmed[it.key] = { by, on: today, source: "claude", proposal: P.file, confidence: it.confidence, evidence: String(it.evidence || "").slice(0, 300) };
    it.confirmed = true;
  }
  if (notes.length) state.site.notes = `${state.site.notes || ""} Confirmed by ${by} on ${today} from a model reading: ${notes.join("; ")}.`.trim();
  state.siteDirty = true;
  $("#site-dirty").hidden = false;
  renderForm($("#site-form"), SITE_FIELDS, state.site, onSiteChange);
  refreshSummary("site");
  setStatus(`${items.length} field${items.length === 1 ? "" : "s"} confirmed by ${by}; the site file records it. Save site as… keeps it.`, "ok");
}

function renderProposal(P) {
  if (!P) return "";
  const rows = P.items.map(it => `<li class="prop-row${it.confirmed ? " confirmed" : ""}">
      <div class="prop-head"><b>${h(cap(it.key.replace(/_/g, " ")))}</b> <span class="prop-val">${h(typeof it.value === "boolean" ? (it.value ? "yes" : "no") : (it.value == null ? "—" : String(it.value)))}</span> <span class="conf" title="the model's confidence">${h(Math.round(it.confidence * 100))}%</span></div>
      ${it.evidence ? `<div class="cont prop-ev">“${h(it.evidence)}”${it.section ? ` <span class="rule-id">${h(it.section)}</span>` : ""}</div>` : ""}
      ${it.confirmed ? `<span class="cont">confirmed</span>` : `<button class="btn btn-small" type="button" data-confirm-key="${h(it.key)}">Confirm</button>`}
    </li>`).join("");
  return `<div class="proposal" id="guide-proposal">
    <div class="prop-top"><span class="prop-by">Proposed by ${h(P.model)}</span><span class="cont">source: claude · logged as proposals/${h(P.file || "")} · nothing is in the site until confirmed</span></div>
    <ul class="prop-list">${rows}</ul>
    <div class="form-actions"><label class="field inline"><span class="label">Confirmed by</span><input type="text" id="confirm-by" value="${h(P.by || "")}" placeholder="your name"></label><button class="btn btn-small" type="button" data-confirm-key="*" data-confirm-all="1">Confirm all</button></div>
  </div>`;
}
