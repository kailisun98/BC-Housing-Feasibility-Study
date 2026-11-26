/* Issuing a run to the architect or the board, and the chip in the top bar for an issue addressed to the reader
   (polled from the local server while the tab is visible). */

import { $, cap, copyText, h, setStatus, toast } from "./core/util.js";
import { guide, state, STATIC } from "./core/state.js";
import { api, postJSON } from "./core/api.js";
import { afterIssue, isDraft, nextRev, openRun, rev } from "./runs.js";
import { renderGuide } from "./route-stage.js";
import { dateWords } from "./memo/memo.js";

const ISSUES_SEEN_KEY = "ffm.issues.seen";

const ISSUE_NAME_KEY = "ffm.issue.name";

/* who a run goes to: the manager hands it to the architect, the architect hands it back to the manager to review
   (16 Nov 2026; before, the architect could only issue to the board). The board is not offered (24 Nov 2026): it has
   no layout on this machine to see it in, and reads the PDF. */
const ISSUE_TO = { manager: "architect", architect: "manager", reader: null, operator: "manager" };

const ISSUE_WORD = { architect: "the architect", manager: "the development manager", reader: "the board, planner and funder", operator: "the operator" };

/* the manager can also send the memo to the operator (24 Nov 2026): "can you operate this?" with the figures to check */
const ISSUE_ALSO = { manager: ["operator"] };

let issueTimer = 0;

function seenIssues() { try { return new Set(JSON.parse(localStorage.getItem(ISSUES_SEEN_KEY) || "[]")); } catch (e) { return new Set(); } }

function markIssueSeen(id) { const s = seenIssues(); s.add(id); try { localStorage.setItem(ISSUES_SEEN_KEY, JSON.stringify([...s].slice(-200))); } catch (e) { /* fine */ } }

/* The person at this browser, by the name they gave (26 Nov 2026, Kai: "a name per browser"): kept in this browser
   only, never a login. An issue is sent from it and may be addressed to another person's; the top-bar chip shows
   what was addressed to it, and a run made here records it as its maker. The key is the issue form's, so a name given
   there before carries over. */
function issueName() { try { return localStorage.getItem(ISSUE_NAME_KEY) || ""; } catch (e) { return guide.issueName || ""; } }

function setIssueName(n) { try { if (n) localStorage.setItem(ISSUE_NAME_KEY, n); else localStorage.removeItem(ISSUE_NAME_KEY); } catch (e) { guide.issueName = n; } syncMe(); }

export const myName = () => issueName().trim();

const sameName = (a, b) => !!a && !!b && String(a).trim().toLowerCase() === String(b).trim().toLowerCase();

/* The top bar's name button and its small form. */
export function syncMe() {
  const b = $("#me-btn");
  if (!b) return;
  const n = myName();
  b.textContent = n || "Your name";
  b.classList.toggle("unset", !n);
  b.title = n ? `You are ${n} in this browser: issues addressed to ${n} show here. Click to change.` : "Give your name: issues are sent from it, and those addressed to it show here. Kept in this browser only.";
}

export function wireMe() {
  const b = $("#me-btn"), panel = $("#me-panel");
  if (!b || !panel) return;
  syncMe();
  const close = (focusBack = false) => { panel.hidden = true; b.setAttribute("aria-expanded", "false"); if (focusBack) b.focus(); };
  b.addEventListener("click", () => {
    if (!panel.hidden) { close(); return; }
    panel.innerHTML = `<form class="me-form">
        <label class="field"><span class="label">Your name</span><input type="text" name="me" value="${h(myName())}" autocomplete="name" maxlength="80" placeholder="as your colleagues know you"></label>
        <div class="form-actions"><button type="submit" class="btn btn-primary btn-small">Keep it</button>${myName() ? `<button type="button" class="btn btn-quiet btn-small" data-me-clear>Forget it</button>` : ""}</div>
        <p class="help">Kept in this browser only; it is not a login. Issues you send carry it, issues addressed to it show in this bar, and runs you make are marked with it.</p>
      </form>`;
    panel.hidden = false;
    b.setAttribute("aria-expanded", "true");
    const form = $("form", panel), inp = $("input", form);
    inp.focus(); inp.select();
    form.addEventListener("submit", e => { e.preventDefault(); setIssueName(inp.value.trim()); close(true); setStatus(myName() ? `You are ${myName()} in this browser.` : "No name is kept in this browser.", "ok"); showMine(); });
    const clr = $("[data-me-clear]", form);
    if (clr) clr.addEventListener("click", () => { setIssueName(""); close(true); setStatus("No name is kept in this browser.", "info"); showMine(); });
    form.addEventListener("keydown", e => { if (e.key === "Escape") { e.preventDefault(); close(true); } });
  });
}

/* The issue form: the sender's name (kept for next time), who it goes to, a note. Rendered where the button was
   pressed: inside the guide's stop 7 for the manager, under the export bar for anyone. */
function issueFormHtml(scope) {
  const to = ISSUE_TO[state.mode];
  if (!to || !state.run) return "";
  // a draft takes the site's next revision number as it goes (runs.js noteRevisions); an issued memo keeps its own, and
  // is issued "again" only where it has been issued before (26 Nov 2026: a committed R2 never issued said "again")
  const draft = isDraft(state.run.run_id);
  const label = draft ? `Mark issued as ${nextRev()}` : `Mark ${rev(state.run.run_id)} issued${(state.run.issues || []).length ? " again" : ""}`;
  // what it does, said plainly (24 Nov 2026: "They see it in their top bar" promised a delivery; nothing leaves this
  // machine, and the board was offered a top bar it does not have)
  return `<form class="issue-panel" data-issue="${h(scope)}" aria-label="${h(label)} to ${h(ISSUE_WORD[to])}">
    ${(ISSUE_ALSO[state.mode] || []).length ? "" : `<input type="hidden" name="to" value="${h(to)}">`}
    <div class="issue-row">
      <label class="field"><span class="label">From</span><input type="text" name="name" value="${h(myName())}" placeholder="your name" autocomplete="name" maxlength="80"></label>
      ${(ISSUE_ALSO[state.mode] || []).length ? `<label class="field"><span class="label">To</span><select name="to">${[to, ...ISSUE_ALSO[state.mode]].map(t => `<option value="${h(t)}">${h(cap(ISSUE_WORD[t]))}</option>`).join("")}</select></label>`
        : `<p class="field"><span class="label">To</span><span>${h(cap(ISSUE_WORD[to]))}</span></p>`}
      <label class="field"><span class="label">Their name</span><input type="text" name="to_name" list="issue-names" placeholder="who should open it" autocomplete="off" maxlength="80"></label>
      <datalist id="issue-names">${knownNames().map(n => `<option value="${h(n)}">`).join("")}</datalist>
    </div>
    <label class="field"><span class="label">A note</span><textarea name="note" rows="2" maxlength="600" placeholder="What changed, and what you want checked"></textarea></label>
    <div class="form-actions"><button class="btn btn-primary btn-small" type="submit">${h(label)}</button><button class="btn btn-quiet btn-small" type="button" data-issue-cancel>Not now</button></div>
    <p class="help">${draft ? `The draft becomes ${h(nextRev())}. ` : ""}Recorded on this machine: it shows in the top bar of the browser that gives their name (or, with no name, in ${h(ISSUE_WORD[to])}'s layout), with your note under the memo's title.</p>
    <p class="issue-send">To send it: <button type="button" class="linkish" data-issue-pdf>Download PDF</button> · <button type="button" class="linkish" data-issue-link>Copy the link</button></p>
  </form>`;
}

/* The names seen on issues, senders and receivers, for the Their name list; this browser's own left out. */
function knownNames() {
  const me = myName();
  const seen = new Map();
  for (const i of state.issues || []) for (const n of [i.name, i.to_name]) { const t = String(n || "").trim(); if (t && !sameName(t, me)) seen.set(t.toLowerCase(), t); }
  return [...seen.values()].sort();
}

function wireIssueForm(form, onClose) {
  form.addEventListener("submit", e => { e.preventDefault(); sendIssue(form).then(ok => { if (ok && onClose) onClose(); }); });
  const c = $("[data-issue-cancel]", form); if (c) c.addEventListener("click", () => onClose && onClose(true));
  const pdf = $("[data-issue-pdf]", form); if (pdf) pdf.addEventListener("click", () => { const b = $("#pdf-btn"); if (b && !b.disabled) b.click(); });
  const link = $("[data-issue-link]", form);
  if (link) link.addEventListener("click", () => copyText(location.href).then(() => setStatus(`Copied the link to ${rev(state.run.run_id)}: it opens this memo on this machine's First Read.`, "ok")).catch(() => toast("Could not copy: copy the address bar instead.", true)));
  // Esc closes it, as Not now does, and the keyboard goes back to the button that opened it (20 Nov 2026)
  form.addEventListener("keydown", e => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); if (onClose) onClose(true); } });
  const first = $("input[name=name]", form);
  if (first) (first.value ? $("textarea", form) : first).focus({ preventScroll: true });
}

/* Issue, in the top bar beside the Revision it numbers (26 Nov 2026, a UX designer's brief: it sat fourth in the
   title block's action row, out of reach once the memo scrolled, and disabled with its reason in a title no keyboard or
   touch reached). Its form drops under it as the name form does: the keyboard goes to the first empty field, Esc and
   Not now close it and give the keyboard back, a click outside closes it. Where it cannot issue it says why, in the
   same place: the button stays reachable (aria-disabled), and a press opens the reason. */
const BTN_WORD = { architect: "the architect", manager: "the manager", operator: "the operator" };

/* What the button can do now: null where it is hidden, else {ok, why, note}. */
function issueState() {
  const to = ISSUE_TO[state.mode];
  if (!to || !state.run) return null;
  const r = rev(state.run.run_id);
  if (STATIC) return { ok: false, why: "Issuing is recorded on the machine running First Read; on the web, send the link or the PDF." };
  if (state.running) return { ok: false, why: "Running the rules…" };
  if (state.runStale) return { ok: false, why: `Run again first: ${state.runStale} changed after ${r}.`, stale: true };
  if (isDraft(state.run.run_id)) return { ok: true, draft: true, note: `Makes it ${nextRev()}.` };
  const mine = (state.run.issues || []).filter(i => i.by === state.mode).sort((a, b) => String(a.issued_at).localeCompare(String(b.issued_at))).slice(-1)[0];
  if (mine) return { ok: true, note: `Last issued to ${mine.to_name ? `${mine.to_name} (${ISSUE_WORD[mine.to] || mine.to})` : ISSUE_WORD[mine.to] || mine.to}, ${dateWords(mine.issued_at, true)}.` };
  return { ok: true, note: `${r}, not yet issued from this layout.` };
}

/* The one place the button's state is set: called by renderMemo, syncRunButton (so a run starting and ending, and the
   memo going stale, reach it), setMode and an issue. */
export function syncIssueButton() {
  const wrap = $("#issue-top"), btn = $("#issue-btn");
  if (!wrap || !btn) return;
  const to = ISSUE_TO[state.mode];
  const s = issueState();
  wrap.hidden = !s;
  if (!s) { closeIssuePanel(); return; }
  btn.textContent = `Mark issued to ${BTN_WORD[to] || ISSUE_WORD[to]}`;
  btn.setAttribute("aria-disabled", String(!s.ok));
  btn.classList.toggle("draft", !!s.draft);
  const why = s.ok ? s.note : s.why;
  $("#issue-why").textContent = why || "";
  btn.title = why || "";
  // a reason on screen goes stale with the state: an open reason is redrawn, an open form that can no longer send closes
  const pop = $("#issue-pop");
  if (!pop.hidden && pop.dataset.kind === "why") showWhy(s);
  else if (!pop.hidden && !s.ok) closeIssuePanel();
}

/* Kept for the callers that named it before the button moved (modes.js, main.js). */
export const issueButtonLabel = syncIssueButton;

function showWhy(s) {
  const pop = $("#issue-pop");
  pop.dataset.kind = "why";
  pop.setAttribute("aria-label", "Why it cannot be marked issued now");
  pop.innerHTML = `<p class="issue-why-line">${h(s.why)}</p>${s.stale ? `<div class="form-actions"><button type="button" class="btn btn-primary btn-small" data-issue-run>Run the rules again</button><button type="button" class="btn btn-quiet btn-small" data-issue-cancel>Not now</button></div>` : `<div class="form-actions"><button type="button" class="btn btn-quiet btn-small" data-issue-cancel>Close</button></div>`}`;
  const run = $("[data-issue-run]", pop);
  if (run) run.addEventListener("click", () => { closeIssuePanel(); const b = $("#run-btn"); if (b) b.click(); });
  $("[data-issue-cancel]", pop).addEventListener("click", () => closeIssuePanel(true));
  ($("button", pop) || pop).focus({ preventScroll: true });
}

/* A click outside, or the keyboard leaving it, puts the popover away and keeps what was typed (a review the same
   evening: a note typed, a click elsewhere, and the note was gone); Not now, Esc and a sent issue clear it. */
function outsideClose(e) {
  const wrap = $("#issue-top");
  if (wrap && !wrap.contains(e.target)) hideIssuePanel();
}

function hideIssuePanel() {
  const pop = $("#issue-pop"), btn = $("#issue-btn");
  if (!pop || pop.hidden) return;
  pop.hidden = true;
  btn.setAttribute("aria-expanded", "false");
  document.removeEventListener("pointerdown", outsideClose, true);
}

/* The popover's own keys and focus, wired once: Esc closes whichever it holds (the form's own handler closes the form
   first), and Tab past its last control puts it away. */
function wirePop(pop) {
  if (pop.dataset.wired) return;
  pop.dataset.wired = "1";
  pop.addEventListener("keydown", e => { if (e.key === "Escape") { e.preventDefault(); closeIssuePanel(true); } });
  $("#issue-top").addEventListener("focusout", e => { if (e.relatedTarget && !$("#issue-top").contains(e.relatedTarget)) hideIssuePanel(); });
}

export function openIssuePanel() {
  const pop = $("#issue-pop"), btn = $("#issue-btn");
  const s = issueState();
  if (!s) return;
  wirePop(pop);
  pop.setAttribute("role", "dialog");
  pop.hidden = false;
  btn.setAttribute("aria-expanded", "true");
  if (!s.ok) showWhy(s);
  else if (pop.dataset.kind === "form" && pop.dataset.run === state.run.run_id && $("form", pop)) {
    // the form put away by a click outside comes back as it was left
    const first = $("textarea", pop) || $("input", pop);
    if (first) first.focus({ preventScroll: true });
  } else {
    pop.dataset.kind = "form";
    pop.dataset.run = state.run.run_id;
    pop.innerHTML = issueFormHtml("bar");
    const form = $("form", pop);
    pop.setAttribute("aria-label", form ? form.getAttribute("aria-label") : "Mark issued");
    wireIssueForm(form, closeIssuePanel);
  }
  document.addEventListener("pointerdown", outsideClose, true);
}

export function closeIssuePanel(focusBack = false) {
  const pop = $("#issue-pop"), btn = $("#issue-btn");
  if (!pop || !btn) return;
  const had = !pop.hidden;
  pop.hidden = true; pop.innerHTML = ""; delete pop.dataset.kind; delete pop.dataset.run;
  btn.setAttribute("aria-expanded", "false");
  document.removeEventListener("pointerdown", outsideClose, true);
  if (focusBack === true && had) btn.focus();
}

/* Records the issue on the run; true when it went. The page does not scroll: the sender stays where they pressed. */
async function sendIssue(form) {
  const run = state.run;
  if (!run) return false;
  const fd = new FormData(form);
  const to = String(fd.get("to") || ISSUE_TO[state.mode] || "");
  const name = String(fd.get("name") || "").trim();
  const toName = String(fd.get("to_name") || "").trim();
  const note = String(fd.get("note") || "").trim();
  if (!to) return false;
  const [site, folder] = run.run_id.split("/");
  const btn = $("button[type=submit]", form); if (btn) btn.disabled = true;
  try {
    const it = await postJSON(`/api/runs/${encodeURIComponent(site)}/${encodeURIComponent(folder)}/issue`, { by: state.mode, to, note, name, to_name: toName });
    if (name && !sameName(name, myName())) setIssueName(name);
    run.issued = it;
    run.issues = [...(run.issues || []), it];
    const memoEl = $("#memo"); if (memoEl) memoEl.dataset.issuedManager = run.issues.some(i => i.to === "manager") ? "1" : "";
    markIssueSeen(it.id);
    guide.issueOpen = false;
    closeIssuePanel();
    const was = rev(run.run_id);
    await afterIssue(run);   // a draft takes its number now, and the title block, the top bar and the pickers say it
    renderGuide();
    const now = rev(run.run_id);
    setStatus(`${was !== now ? `${was} is now ${now}, issued` : `Issued ${now}`} to ${toName ? `${toName} (${ISSUE_WORD[to]})` : ISSUE_WORD[to]}, ${dateWords(it.issued_at, true)}${name ? `, from ${name}` : ""}. ${toName ? `${toName}'s top bar shows it on this machine` : `${cap(ISSUE_WORD[to])}'s layout on this machine shows it`}; send the link or the PDF to reach them elsewhere.`, "ok");
    return true;
  } catch (e) {
    toast(`Could not record the issue: ${e.message}. Nothing changed; try again, or send the link or the PDF.`, true);
    if (btn) btn.disabled = false;
    return false;
  }
}

/* Every 15 s the page asks the local server for the site's issue notes; a new one addressed to this reader becomes a
   chip in the top bar, and a click opens that run. Nothing polls on the web build. */
/* One request at a time, and none within 3 s of the last: the chip is redrawn from the notes already in hand
   (24 Nov 2026: a page load asked /api/issues two to five times, from the site, the mode and the poller at once). */
let issuesAt = 0, issuesAsk = null;

export async function pollIssues() {
  if (STATIC) return;
  if (issuesAsk) return issuesAsk;
  if (Date.now() - issuesAt < 3000) { showMine(); return; }
  issuesAsk = (async () => {
    try {
      // every site's issues: a run handed over on a site that is not on this screen, or never saved, still arrives
      state.issues = await api("/api/issues");
      issuesAt = Date.now();
      showMine();
    } catch (e) { /* the server is away: the chip simply stays as it was */ }
    finally { issuesAsk = null; }
  })();
  return issuesAsk;
}

/* What the chip offers this browser: an issue addressed to its name; one addressed to no name, to the layout on
   screen, said as such ("issued to the architect", never "to you"); never one this browser's name sent (26 Nov 2026,
   the third panel: "issued to you" reached whoever opened the page). */
function showMine() {
  const seen = seenIssues(), me = myName();
  const forMe = i => (i.to_name ? sameName(i.to_name, me) : i.to === state.mode);
  const fromMe = i => (me ? sameName(i.name, me) : i.by === state.mode);
  const mine = (state.issues || []).filter(i => forMe(i) && !fromMe(i) && !seen.has(i.id));
  showIssueChip(mine[0] || null, mine.length);
}

/* Who sent an issue, in words: their name and role, or the role alone. */
const senderWords = i => (i.name ? `${i.name} (the ${i.by})` : `the ${i.by}`);

function showIssueChip(issue, count) {
  const chip = $("#issue-chip");
  if (!issue) { chip.hidden = true; return; }
  const ago = (() => { const s = Math.max(0, (Date.now() - new Date(issue.issued_at).getTime()) / 1000); return s < 90 ? "just now" : s < 3600 ? `${Math.round(s / 60)} min ago` : s < 86400 ? `${Math.round(s / 3600)} h ago` : `${Math.round(s / 86400)} d ago`; })();
  chip.hidden = false;
  const siteName = (state.sites.find(s => s.id === issue.site) || {}).address || issue.site || "";
  const toWhom = issue.to_name ? "you" : (ISSUE_WORD[issue.to] || `the ${issue.to}`);
  const words = `${siteName ? String(siteName).split(",")[0] + " · " : ""}${state.revisions.get(issue.run_id) || "a run"} issued to ${toWhom} by ${senderWords(issue)} · ${ago}${count > 1 ? ` · +${count - 1}` : ""}`;
  // the text is cut to the chip's width under 1500 px (app.css), so the whole of it is the chip's name and title
  chip.innerHTML = `<span class="dot"></span><span class="chip-text">${h(words)}</span>`;
  chip.setAttribute("aria-label", `${words}. Open it`);
  chip.title = `${words}${issue.note ? ` · "${issue.note}"` : ""} · click to open`;
  chip.onclick = async () => {
    markIssueSeen(issue.id);
    chip.hidden = true;
    try { await openRun(issue.run_id); setStatus(`Opened ${rev(issue.run_id)}, issued by ${senderWords(issue)}${issue.note ? `: "${issue.note}"` : ""}.`, "ok"); }
    catch (e) { toast(e.message, true); }
    pollIssues();
  };
}

/* The page asks only while it is looked at (16 Nov 2026: a tab left open in the background asked every 15 s all
   day); coming back to the tab asks at once. */
export function startIssuePolling() {
  clearInterval(issueTimer);
  if (STATIC) return;
  pollIssues();
  issueTimer = setInterval(() => { if (!document.hidden) pollIssues(); }, 15000);
  if (!startIssuePolling.wired) {
    startIssuePolling.wired = true;
    document.addEventListener("visibilitychange", () => { if (!document.hidden) pollIssues(); });
  }
}
