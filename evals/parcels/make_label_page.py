"""Build label.html from uncertain.json: one page, no server, where a person looks at each uncertain parcel and
says what shape it is. The page keeps a draft in the browser and downloads labels.json, which goes next to
uncertain.json for the classifier's thresholds to be checked against.

    python evals/parcels/make_label_page.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLASSES = ["rectangle", "near_rectangle", "trapezoid", "l_shape", "flag_lot", "irregular", "multi_part"]

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Label the uncertain parcels</title>
<style>
  :root { --ink: #1f2933; --muted: #5f6672; --line: #e1e5ea; --paper: #fff; --page: #f6f7f8; --blue: #2a6fb8; }
  body { margin: 0; font: 14px/1.5 "IBM Plex Sans", Helvetica, Arial, sans-serif; color: var(--ink); background: var(--page); }
  header { background: var(--paper); border-bottom: 1px solid var(--line); padding: 14px 20px; position: sticky; top: 0; z-index: 2; display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center; }
  header h1 { font-size: 16px; margin: 0; }
  header label { font-size: 12.5px; color: var(--muted); display: inline-flex; gap: 6px; align-items: center; }
  header input { font: inherit; padding: 4px 8px; border: 1px solid var(--line); border-radius: 4px; width: 90px; }
  button { font: inherit; font-size: 13px; padding: 6px 12px; border: 1px solid var(--line); border-radius: 999px; background: var(--paper); cursor: pointer; }
  button.primary { background: var(--ink); color: #fff; border-color: var(--ink); }
  .count { font-size: 12.5px; color: var(--muted); margin-left: auto; }
  main { max-width: 1100px; margin: 0 auto; padding: 16px 20px 60px; }
  p.lead { color: var(--muted); max-width: 70ch; margin: 6px 0 18px; }
  .parcel { background: var(--paper); border: 1px solid var(--line); border-radius: 6px; padding: 14px 16px; margin-bottom: 12px; display: grid; grid-template-columns: 140px minmax(0, 1fr); gap: 12px 18px; }
  .parcel.done { border-color: #8fb8e3; }
  .parcel svg { width: 130px; height: 130px; border: 1px solid var(--line); border-radius: 4px; background: #fff; }
  .parcel h2 { font-size: 15px; margin: 0 0 2px; }
  .parcel .meta { font-size: 12.5px; color: var(--muted); margin: 0 0 6px; }
  .parcel .why { font-size: 12.5px; margin: 0 0 8px; }
  .choices { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 13px; }
  .choices label { display: inline-flex; gap: 5px; align-items: center; cursor: pointer; }
  .choices .guess::after { content: " (its guess)"; color: var(--muted); font-size: 11.5px; }
  .choices .runner::after { content: " (runner-up)"; color: var(--muted); font-size: 11.5px; }
  .note { margin-top: 8px; }
  .note input { font: inherit; font-size: 13px; width: 100%; max-width: 560px; padding: 5px 8px; border: 1px solid var(--line); border-radius: 4px; }
  .nums { font: 11.5px/1.5 ui-monospace, Consolas, monospace; color: var(--muted); margin-top: 6px; }
  a { color: var(--blue); }
  @media (max-width: 600px) { .parcel { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<header>
  <h1>Label the uncertain parcels</h1>
  <label>Initials <input id="by" placeholder="KS"></label>
  <button id="save" class="primary">Download labels.json</button>
  <button id="clear">Clear the draft</button>
  <span class="count" id="count"></span>
</header>
<main>
  <p class="lead">__N__ parcels the classifier (<code>ffm/parcel_shapes.py</code>) is least sure of, from the City's parcel polygons
  (Open Government Licence – Vancouver). North is up in every thumbnail. Tick the shape you would call it; a note helps
  when none of the words fit, or when the parcel is not what the City draws (a consolidated site, a road closure).
  The draft stays in this browser until you download it. The classes: <b>rectangle</b> (four corners, square-ish),
  <b>near rectangle</b> (a bevelled corner, a slight skew, a short jog), <b>trapezoid</b> (four sides, not
  square-cornered), <b>L shape</b> (six corners, one inward), <b>flag lot</b> (a narrow strip leads to a wider body),
  <b>irregular</b> (anything else: triangles, curves, many sides), <b>multi part</b> (more than one piece).</p>
  <div id="list"></div>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const CLASSES = __CLASSES__;
const parcels = JSON.parse(document.getElementById("data").textContent);
const KEY = "ffm.parcel-labels";
let draft = {};
try { draft = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { draft = {}; }
const h = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
function render() {
  const list = document.getElementById("list");
  list.innerHTML = parcels.map((p, i) => {
    const d = draft[p.site_id] || {};
    const m = p.metrics || {};
    return `<section class="parcel${d.label ? " done" : ""}" data-id="${h(p.site_id)}">
      <div>${p.thumbnail_svg || ""}</div>
      <div>
        <h2>${i + 1}. ${h(p.address || p.site_id)}</h2>
        <p class="meta">${h(p.local_area || "")} · site_id ${h(p.site_id)} · ${h(Math.round(m.area_m2 || 0).toLocaleString("en-CA"))} m² · <a href="https://www.openstreetmap.org/?mlat=${p.center ? p.center[1] : ""}&mlon=${p.center ? p.center[0] : ""}#map=19/${p.center ? p.center[1] : ""}/${p.center ? p.center[0] : ""}" target="_blank" rel="noopener">map</a></p>
        <p class="why">${h(p.why || "")}</p>
        <div class="choices">${CLASSES.map(c => `<label class="${c === p.best_guess ? "guess" : (c === p.runner_up ? "runner" : "")}"><input type="radio" name="l-${h(p.site_id)}" value="${c}"${d.label === c ? " checked" : ""}> ${c.replace(/_/g, " ")}</label>`).join("")}
          <label><input type="radio" name="l-${h(p.site_id)}" value="other"${d.label && !CLASSES.includes(d.label) ? " checked" : ""}> other</label></div>
        <div class="note"><input type="text" class="note-in" placeholder="A note: what it really is, or why the words do not fit" value="${h(d.note || "")}"></div>
        <div class="nums">rectangularity ${h(m.rectangularity)} · convexity ${h(m.convexity)} · corners ${h(m.vertices)} (${h(m.vertices_raw)} published) · narrowest ${h(m.narrowest_cross_section_m)} m · confidence ${h(m.confidence)}</div>
      </div>
    </section>`;
  }).join("");
  count();
}
function count() {
  const n = parcels.filter(p => (draft[p.site_id] || {}).label).length;
  document.getElementById("count").textContent = `${n} of ${parcels.length} labelled`;
}
function store() { try { localStorage.setItem(KEY, JSON.stringify(draft)); } catch (e) {} }
document.getElementById("list").addEventListener("change", e => {
  const sec = e.target.closest(".parcel"); if (!sec) return;
  const id = sec.dataset.id; draft[id] = draft[id] || {};
  if (e.target.type === "radio") { draft[id].label = e.target.value === "other" ? (draft[id].note ? "other: " + draft[id].note : "other") : e.target.value; sec.classList.toggle("done", !!draft[id].label); }
  if (e.target.classList.contains("note-in")) { draft[id].note = e.target.value; if (draft[id].label && draft[id].label.startsWith("other")) draft[id].label = "other: " + e.target.value; }
  store(); count();
});
document.getElementById("list").addEventListener("input", e => { if (e.target.classList.contains("note-in")) { const id = e.target.closest(".parcel").dataset.id; draft[id] = draft[id] || {}; draft[id].note = e.target.value; store(); } });
document.getElementById("save").addEventListener("click", () => {
  const by = document.getElementById("by").value.trim() || null;
  const out = { labelled_by: by, labelled_on: new Date().toISOString().slice(0, 10), source: "evals/parcels/uncertain.json",
    labels: parcels.map(p => ({ site_id: p.site_id, address: p.address, best_guess: p.best_guess, runner_up: p.runner_up, label: (draft[p.site_id] || {}).label || null, note: (draft[p.site_id] || {}).note || null })) };
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 2)], { type: "application/json" })); a.download = "labels.json"; a.click();
});
document.getElementById("clear").addEventListener("click", () => { if (confirm("Clear every label in this browser?")) { draft = {}; store(); render(); } });
try { const by = localStorage.getItem(KEY + ".by"); if (by) document.getElementById("by").value = by; } catch (e) {}
document.getElementById("by").addEventListener("input", e => { try { localStorage.setItem(KEY + ".by", e.target.value); } catch (x) {} });
render();
</script>
</body>
</html>
"""


def main() -> None:
    src = json.loads((HERE / "uncertain.json").read_text(encoding="utf-8"))
    rows = []
    for p in src["parcels"]:
        ring = (p.get("ring_lonlat") or [[]])[0] or []
        center = None
        if ring:
            center = [round(sum(q[0] for q in ring) / len(ring), 6), round(sum(q[1] for q in ring) / len(ring), 6)]
        m = p.get("metrics") or {}
        rows.append({"site_id": p["site_id"], "address": p.get("address"), "local_area": p.get("local_area"), "best_guess": p.get("best_guess"),
                     "runner_up": p.get("runner_up"), "why": p.get("why"), "thumbnail_svg": p.get("thumbnail_svg"), "center": center,
                     "metrics": {k: m.get(k) for k in ("area_m2", "rectangularity", "convexity", "vertices", "vertices_raw", "narrowest_cross_section_m", "confidence")}})
    data = json.dumps(rows).replace("</", "<\\/")
    html = PAGE.replace("__DATA__", data).replace("__CLASSES__", json.dumps(CLASSES)).replace("__N__", str(len(rows)))
    (HERE / "label.html").write_text(html, encoding="utf-8")
    print(f"wrote {HERE / 'label.html'}: {len(rows)} parcels")


if __name__ == "__main__":
    main()
