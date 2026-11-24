/* The money drawn (20 Nov 2026, Kai approved "a capital stack"): two columns at one scale on white paper, what it
   costs (hard, soft, contingency, land) and what pays for it (debt, equity, the grants), the gap hatched on top of the
   second column as "not yet found", and an amber line 15% of the cost below the top, the screen's own line. A drawn
   stack in the drawing language, not a chart for its own sake: the pro-forma's own figures, nothing added.

   It is HTML, not SVG text, so its words keep the page's sizes and reflow on a phone (DESIGN.md: explanatory figures
   in HTML); only the leader lines are a small SVG. The same markup prints in the paper memo at its own unit (mm), so
   the screen and the paper draw one stack. Pure: no DOM. */

import { h } from "../core/util.js";

/* The screen's line: a gap within this share of the capital cost is one the screen calls close (proforma.py
   GAP_UNLIKELY_SHARE). */
export const SCREEN_SHARE = 0.15;

/* A figure in millions: $41.3M, $0, "not given". */
export const millionsOf = x => (x == null || Number.isNaN(Number(x)) ? "not given" : Math.abs(x) < 5e4 ? `${x < 0 ? "−" : ""}$${Math.round(Math.abs(x)).toLocaleString("en-CA")}` : `${x < 0 ? "−" : ""}$${(Math.abs(x) / 1e6).toFixed(1)}M`);

/* One run's stack: the segments of each column, bottom first, and the totals. */
export function stackOf(pf, name = "") {
  if (!pf || !pf.available) return null;
  const c = pf.capital || {}, f = pf.funding || {}, g = pf.gap || {}, lines = pf.lines || [];
  const note = key => ((lines.find(l => l.key === key) || {}).note || "");
  const cost = [
    { key: "hard", label: "Hard cost", value: c.hard },
    { key: "soft", label: "Soft costs", value: c.soft },
    { key: "contingency", label: "Contingency", value: c.contingency },
    // land last, on top: $0 where the owner leases it at a nominal value, "not given" where nobody has priced it
    { key: "land", label: "Land", value: c.land, words: c.land == null ? "not given" : c.land === 0 ? "$0, nominal" : null, note: note("land") },
  ];
  const grants = (f.grants || []).map(x => ({ key: x.program ? "grant" : "other", label: x.program === "bch.chf.eligibility" ? "CHF grant" : x.program ? String(x.label || "Grant").replace(/ provisional grant$/i, " grant") : "Other grants", value: x.value }));
  const pay = [
    { key: "debt", label: "Debt", value: (f.debt || {}).supportable },
    { key: "equity", label: "Equity", value: f.equity, words: !f.equity ? "none entered" : null },
    ...grants.filter(x => x.key === "other"),
    ...grants.filter(x => x.key === "grant"),
  ];
  const total = c.total, funding = f.total, gap = g.value;
  return { name, cost, pay, total, funding, gap, share: g.share_of_capital, word: (pf.verdict || {}).word };
}

/* Labels beside a column, each at the middle of its segment, pushed apart where two would overprint (as the section's
   height labels are) and kept inside the drawing's height. y runs from the bottom. */
function spread(tags, H, lh) {
  const t = tags.slice().sort((a, b) => b.at - a.at);   // the highest first
  for (let k = 0; k < t.length; k++) t[k].y = Math.min(t[k].at, H - lh / 2);
  for (let k = 1; k < t.length; k++) t[k].y = Math.min(t[k].y, t[k - 1].y - lh);
  // run off the bottom: push back up from the floor
  const low = lh / 2;
  if (t.length && t[t.length - 1].y < low) {
    t[t.length - 1].y = low;
    for (let k = t.length - 2; k >= 0; k--) t[k].y = Math.max(t[k].y, t[k + 1].y + lh);
  }
  return t;
}

/* The drawing of one or more stacks at one scale. opts: unit ("px" on screen, "mm" on paper), H (the tallest column's
   height in that unit), lh (a label's line height), names (show each stack's name over it). */
export function stackDrawing(stacks, opts = {}) {
  const list = stacks.filter(Boolean);
  if (!list.length) return "";
  const u = opts.unit || "px", H = opts.H || 220, lh = opts.lh || 15;
  const top = Math.max(...list.flatMap(s => [s.total || 0, s.funding || 0]), 1);
  const k = H / top;
  const len = x => `${(Math.max(0, x) * k).toFixed(2)}${u}`;
  const at = x => `${(x).toFixed(2)}${u}`;
  const fig = (s, x) => `<b>${h(x.words || millionsOf(x.value))}</b>`;
  const one = s => {
    const outside = { cost: [], pay: [] };
    const column = (side, segs) => {
      let base = 0;
      const out = [];
      for (const x of segs) {
        const v = Math.max(0, Number(x.value) || 0), hgt = v * k;
        const mid = (base + v / 2) * k;
        if (hgt >= 2 * lh + 2) out.push(`<div class="ms-seg s-${h(x.key)}" style="bottom:${at(base * k)};height:${at(hgt)}"><span class="ms-in">${h(x.label)}<br>${fig(s, x)}</span></div>`);
        else {
          if (hgt > 0) out.push(`<div class="ms-seg s-${h(x.key)}" style="bottom:${at(base * k)};height:${at(hgt)}"></div>`);
          if (v > 0 || x.words) outside[side].push({ at: mid, text: `${h(x.label)} ${fig(s, x)}` });
        }
        base += v;
      }
      return { html: out.join(""), top: base };
    };
    const cost = column("cost", s.cost);
    const pay = column("pay", s.pay);
    // the gap on top of what pays, up to the cost: hatched, "not yet found"; a negative gap is headroom over the cost
    let gapHtml = "";
    const found = pay.top, total = s.total || cost.top;
    if (s.gap != null && s.gap > 0) {
      const g = s.gap * k, words = `${s.share != null ? `${Math.round(s.share * 100)}% of the cost` : ""}`;
      // the gap's label sits on a paper patch with 2 px above and below, inside a 1 px border: n lines need n × lh + 6
      // (24 Nov 2026: the threshold counted the lines alone, and at 1366 the third line was cut off in a 46 px box)
      const fits = n => g >= n * lh + 6;
      gapHtml = fits(2)
        ? `<div class="ms-seg s-gap" style="bottom:${at(found * k)};height:${at(g)}"><span class="ms-in"><span class="ms-ink">Not yet found</span><br><b>${h(millionsOf(s.gap))}</b>${fits(3) && words ? `<br><span class="ms-ink">${h(words)}</span>` : ""}</span></div>`
        : `<div class="ms-seg s-gap" style="bottom:${at(found * k)};height:${at(g)}"></div>`;
      if (!fits(2)) outside.pay.push({ at: (found + s.gap / 2) * k, text: `Not yet found <b>${h(millionsOf(s.gap))}</b>` });
    } else if (s.gap != null && s.gap < 0) {
      outside.pay.push({ at: total * k, text: `Headroom <b>${h(millionsOf(-s.gap))}</b> over the cost` });
    }
    // the screen's line: 15% of the cost below the top; a gap that runs below it is past what the screen calls close
    const lineAt = total * (1 - SCREEN_SHARE) * k;
    outside.pay.push({ at: lineAt, text: `15% screening line`, cls: "ms-bench" });
    const leaders = (side, tags) => {
      const t = spread(tags, H, lh);
      // the leaders in a small SVG across the label column: from the column's edge at the segment to the label
      const x0 = side === "cost" ? 100 : 0, x1 = side === "cost" ? 88 : 12;
      const lines = t.map(x => `<polyline points="${x0},${(H - x.at).toFixed(2)} ${x1},${(H - x.y).toFixed(2)} ${side === "cost" ? 80 : 20},${(H - x.y).toFixed(2)}" class="${x.cls === "ms-bench" ? "ms-lead-bench" : "ms-lead"}" vector-effect="non-scaling-stroke"/>`).join("");
      return `<div class="ms-lab ms-lab-${side}"><svg class="ms-leaders" viewBox="0 0 100 ${H}" preserveAspectRatio="none" aria-hidden="true">${lines}</svg>${t.map(x => `<span class="ms-out${x.cls ? ` ${x.cls}` : ""}" style="bottom:${at(x.y - lh / 2)}">${x.text}</span>`).join("")}</div>`;
    };
    const heightTotal = Math.max(total, found + Math.max(0, s.gap || 0));
    // where the drawing is too narrow for labels beside its columns (a phone), the same labels follow it as a list
    const list = [...outside.cost.map(x => ({ ...x, side: "what it costs" })), ...outside.pay.map(x => ({ ...x, side: x.cls ? "amber dashes" : "what pays for it" }))];
    return `<div class="ms-one">
      ${opts.names && s.name ? `<p class="ms-name">${h(s.name)}</p>` : ""}
      <div class="ms-draw" style="height:${at(H)}">
        ${leaders("cost", outside.cost)}
        <div class="ms-col ms-cost" style="height:${len(total)}">${cost.html}</div>
        <div class="ms-col ms-pay" style="height:${len(heightTotal)}">${pay.html}${gapHtml}</div>
        <div class="ms-screen" style="bottom:${at(lineAt)}" aria-hidden="true"></div>
        ${leaders("pay", outside.pay)}
      </div>
      <div class="ms-keys"><span></span><span>What it costs<br><b>${h(millionsOf(total))}</b></span><span>What pays for it<br><b>${h(millionsOf(s.funding))}</b> <span class="ms-muted">found</span></span><span></span></div>
      ${list.length ? `<ul class="ms-list">${list.map(x => `<li${x.cls ? ` class="${x.cls}"` : ""}>${x.text} <span class="ms-muted">(${h(x.side)})</span></li>`).join("")}</ul>` : ""}
    </div>`;
  };
  return `<div class="ms-row">${list.map(one).join("")}</div>`;
}

/* The stack as a figure: the drawing, then a caption in sentences. */
export function stackFigure(stacks, opts = {}, caption = "") {
  const draw = stackDrawing(stacks, opts);
  if (!draw) return "";
  return `<figure class="money-stack${opts.cls ? ` ${opts.cls}` : ""}" aria-label="${h(opts.label || "The capital stack: what it costs against what pays for it, at one scale")}">
    <div class="ms-paper">${draw}</div>
    ${caption ? `<figcaption>${caption}</figcaption>` : ""}
  </figure>`;
}
