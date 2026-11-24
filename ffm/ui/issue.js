/* Issuing a run to the architect or the board, and the chip in the top bar for an issue addressed to the reader
   (polled from the local server while the tab is visible). */

import { $, cap, h, setStatus, toast } from "./core/util.js";
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

function issueName() { try { return localStorage.getItem(ISSUE_NAME_KEY) || ""; } catch (e) { return guide.issueName || ""; } }

function setIssueName(n) { try { localStorage.setItem(ISSUE_NAME_KEY, n); } catch (e) { guide.issueName = n; } }

/* The issue form: the sender's name (kept for next time), who it goes to, a note. Rendered where the button was
   pressed: inside the guide's stop 7 for the manager, under the export bar for anyone. */
function issueFormHtml(scope) {
  const to = ISSUE_TO[state.mode];
  if (!to || !state.run) return "";
  // a draft takes the site's next revision number as it goes (runs.js noteRevisions); an issued memo keeps its own
  const draft = isDraft(state.run.run_id);
  const label = draft ? `Mark issued as ${nextRev()}` : `Mark ${rev(state.run.run_id)} issued again`;
  // what it does, said plainly (24 Nov 2026: "They see it in their top bar" promised a delivery; nothing leaves this
  // machine, and the board was offered a top bar it does not have)
  return `<form class="issue-panel" data-issue="${h(scope)}" aria-label="${h(label)} to ${h(ISSUE_WORD[to])}">
    ${(ISSUE_ALSO[state.mode] || []).length ? "" : `<input type="hidden" name="to" value="${h(to)}">`}
    <div class="issue-row">
      <label class="field"><span class="label">Your name</span><input type="text" name="name" value="${h(issueName())}" placeholder="so they know who sent it" autocomplete="name" maxlength="80"></label>
      ${(ISSUE_ALSO[state.mode] || []).length ? `<label class="field"><span class="label">To</span><select name="to">${[to, ...ISSUE_ALSO[state.mode]].map(t => `<option value="${h(t)}">${h(cap(ISSUE_WORD[t]))}</option>`).join("")}</select></label>`
        : `<p class="field"><span class="label">To</span><span>${h(cap(ISSUE_WORD[to]))}</span></p>`}
    </div>
    <label class="field"><span class="label">A note</span><textarea name="note" rows="2" maxlength="600" placeholder="What changed, and what you want checked"></textarea></label>
    <div class="form-actions"><button class="btn btn-primary btn-small" type="submit">${h(label)}</button><button class="btn btn-quiet btn-small" type="button" data-issue-cancel>Not now</button><span class="help">${draft ? `The draft becomes ${h(nextRev())}. ` : ""}Recorded on this machine: ${h(ISSUE_WORD[to])}'s layout here shows it, with your note under the memo's title. To reach someone elsewhere, send the link or the PDF; for the board, Download PDF.</span></div>
  </form>`;
}

function wireIssueForm(form, onClose) {
  form.addEventListener("submit", e => { e.preventDefault(); sendIssue(form).then(ok => { if (ok && onClose) onClose(); }); });
  const c = $("[data-issue-cancel]", form); if (c) c.addEventListener("click", () => onClose && onClose(true));
  // Esc closes it, as Not now does, and the keyboard goes back to the button that opened it (20 Nov 2026)
  form.addEventListener("keydown", e => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); if (onClose) onClose(true); } });
  const first = $("input[name=name]", form);
  if (first) (first.value ? $("textarea", form) : first).focus({ preventScroll: true });
}

/* the export bar's copy of the form; the guide renders its own at stop 7 */
export function openIssuePanel() {
  const panel = $("#issue-panel");
  if (!state.run || STATIC) return;
  panel.innerHTML = issueFormHtml("bar");
  panel.hidden = false;
  $("#issue-btn").setAttribute("aria-expanded", "true");
  wireIssueForm($("form", panel), closeIssuePanel);
}

export function closeIssuePanel(focusBack = false) {
  const panel = $("#issue-panel");
  const had = !panel.hidden;
  panel.hidden = true; panel.innerHTML = "";
  $("#issue-btn").setAttribute("aria-expanded", "false");
  if (focusBack === true && had) $("#issue-btn").focus();
}

/* Records the issue on the run; true when it went. The page does not scroll: the sender stays where they pressed. */
async function sendIssue(form) {
  const run = state.run;
  if (!run) return false;
  const fd = new FormData(form);
  const to = String(fd.get("to") || ISSUE_TO[state.mode] || "");
  const name = String(fd.get("name") || "").trim();
  const note = String(fd.get("note") || "").trim();
  if (!to) return false;
  const [site, folder] = run.run_id.split("/");
  const btn = $("button[type=submit]", form); if (btn) btn.disabled = true;
  try {
    const it = await postJSON(`/api/runs/${encodeURIComponent(site)}/${encodeURIComponent(folder)}/issue`, { by: state.mode, to, note, name });
    if (name) setIssueName(name);
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
    setStatus(`${was !== now ? `${was} is now ${now}, issued` : `Issued ${now}`} to ${ISSUE_WORD[to]}, ${dateWords(it.issued_at, true)}${name ? `, as ${name}` : ""}. ${cap(ISSUE_WORD[to])}'s layout on this machine shows it; send the link or the PDF to reach them elsewhere.`, "ok");
    return true;
  } catch (e) {
    toast(`Could not record the issue: ${e.message}. Nothing changed; try again, or send the link or the PDF.`, true);
    if (btn) btn.disabled = false;
    return false;
  }
}

export function issueButtonLabel() {
  const to = ISSUE_TO[state.mode];
  const btn = $("#issue-btn");
  btn.hidden = !to;
  btn.textContent = to ? `Mark issued to ${ISSUE_WORD[to]}` : "Mark issued";
  if (!to) closeIssuePanel();
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

function showMine() {
  const seen = seenIssues();
  const mine = (state.issues || []).filter(i => i.to === state.mode && i.by !== state.mode && !seen.has(i.id));
  showIssueChip(mine[0] || null, mine.length);
}

function showIssueChip(issue, count) {
  const chip = $("#issue-chip");
  if (!issue) { chip.hidden = true; return; }
  const ago = (() => { const s = Math.max(0, (Date.now() - new Date(issue.issued_at).getTime()) / 1000); return s < 90 ? "just now" : s < 3600 ? `${Math.round(s / 60)} min ago` : s < 86400 ? `${Math.round(s / 3600)} h ago` : `${Math.round(s / 86400)} d ago`; })();
  chip.hidden = false;
  const siteName = (state.sites.find(s => s.id === issue.site) || {}).address || issue.site || "";
  chip.innerHTML = `<span class="dot"></span>${siteName ? h(String(siteName).split(",")[0]) + " · " : ""}${h(state.revisions.get(issue.run_id) || "a run")} issued to you by the ${h(issue.by)} · ${h(ago)}${count > 1 ? ` · +${count - 1}` : ""}`;
  chip.title = issue.note ? `"${issue.note}" · click to open` : "Click to open the run";
  chip.onclick = async () => {
    markIssueSeen(issue.id);
    chip.hidden = true;
    try { await openRun(issue.run_id); setStatus(`Opened ${rev(issue.run_id)}, issued by the ${issue.by}${issue.note ? `: "${issue.note}"` : ""}.`, "ok"); }
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
