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
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
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
  .parcel { background: var(--paper); border: 1px solid var(--line); border-radius: 6px; padding: 14px 16px; margin-bottom: 12px; display: grid; grid-template-columns: 130px 300px minmax(0, 1fr); gap: 12px 18px; }
  .parcel.done { border-color: #8fb8e3; }
  .parcel .thumb svg { width: 130px; height: 130px; border: 1px solid var(--line); border-radius: 4px; background: #fff; }
  .parcel .thumb p { font-size: 11px; color: var(--muted); margin: 4px 0 0; text-align: center; }
  .map { height: 300px; border: 1px solid var(--line); border-radius: 4px; background: #eef0f2; }
  .seg { display: inline-flex; border: 1px solid var(--line); border-radius: 999px; overflow: hidden; }
  .seg button { border: 0; border-radius: 0; padding: 5px 12px; }
  .seg button[aria-pressed="true"] { background: var(--ink); color: #fff; }
  .leaflet-container { font: 11px/1.3 "IBM Plex Sans", Helvetica, Arial, sans-serif; }
  .parcel h2 { font-size: 15px; margin: 0 0 2px; }
  .parcel .meta { font-size: 12.5px; color: var(--muted); margin: 0 0 6px; }
  .parcel .why { font-size: 12.5px; margin: 0 0 6px; }
  .parcel .front-note { font-size: 12.5px; margin: 0 0 8px; color: var(--ink); }
  .parcel .front-note .muted { color: var(--muted); }
  .choices { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 13px; }
  .choices label { display: inline-flex; gap: 5px; align-items: center; cursor: pointer; }
  .choices .guess::after { content: " (its guess)"; color: var(--muted); font-size: 11.5px; }
  .choices .runner::after { content: " (runner-up)"; color: var(--muted); font-size: 11.5px; }
  .note { margin-top: 8px; }
  .note input { font: inherit; font-size: 13px; width: 100%; max-width: 560px; padding: 5px 8px; border: 1px solid var(--line); border-radius: 4px; }
  .nums { font: 11.5px/1.5 ui-monospace, Consolas, monospace; color: var(--muted); margin-top: 6px; }
  a { color: var(--blue); }
  @media (max-width: 900px) { .parcel { grid-template-columns: 130px minmax(0, 1fr); } .parcel .text { grid-column: 1 / -1; } }
  @media (max-width: 600px) { .parcel { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<header>
  <h1>Label the uncertain parcels</h1>
  <label>Initials <input id="by" placeholder="KS"></label>
  <span class="seg" role="group" aria-label="Map underlay"><button type="button" data-base="osm" aria-pressed="true">Map</button><button type="button" data-base="aerial" aria-pressed="false">Aerial</button></span>
  <button id="save" class="primary">Download labels.json</button>
  <button id="clear">Clear the draft</button>
  <span class="count" id="count"></span>
</header>
<main>
  <p class="lead">__N__ parcels the classifier (<code>ffm/parcel_shapes.py</code>) is least sure of, from the City's parcel polygons
  (Open Government Licence – Vancouver). North is up in every thumbnail; beside it the parcel is drawn over the real
  site (OpenStreetMap, or aerial imagery with the switch above; the maps load as you scroll). On the map, click the
  edge that fronts the street: the whole edge between two white corners turns red (a curved frontage is one edge),
  and a second edge marks the cross street on a corner lot (amber). Then tick the shape you would call it; a note helps
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
      <div class="thumb">${p.thumbnail_svg || ""}<p>as published</p></div>
      <div class="map" data-i="${i}" aria-label="The parcel over the map"></div>
      <div class="text">
        <h2>${i + 1}. ${h(p.address || p.site_id)}</h2>
        <p class="meta">${h(p.local_area || "")} · site_id ${h(p.site_id)} · ${h(Math.round(m.area_m2 || 0).toLocaleString("en-CA"))} m² · <a href="https://www.openstreetmap.org/?mlat=${p.center ? p.center[1] : ""}&mlon=${p.center ? p.center[0] : ""}#map=19/${p.center ? p.center[1] : ""}/${p.center ? p.center[0] : ""}" target="_blank" rel="noopener">map</a></p>
        <p class="why">${h(p.why || "")}</p>
        <p class="front-note"><b>Frontage:</b> click the edge on the street (red); a second edge marks the cross street (amber).</p>
        <div class="choices">${CLASSES.map(c => `<label class="${c === p.best_guess ? "guess" : (c === p.runner_up ? "runner" : "")}"><input type="radio" name="l-${h(p.site_id)}" value="${c}"${d.label === c ? " checked" : ""}> ${c.replace(/_/g, " ")}</label>`).join("")}
          <label><input type="radio" name="l-${h(p.site_id)}" value="other"${d.label && !CLASSES.includes(d.label) ? " checked" : ""}> other</label></div>
        <div class="note"><input type="text" class="note-in" placeholder="A note: what it really is, or why the words do not fit" value="${h(d.note || "")}"></div>
        <div class="nums">rectangularity ${h(m.rectangularity)} · convexity ${h(m.convexity)} · corners ${h(m.vertices)} (${h(m.vertices_raw)} published) · narrowest ${h(m.narrowest_cross_section_m)} m · confidence ${h(m.confidence)}</div>
      </div>
    </section>`;
  }).join("");
  count();
  watchMaps();
}

/* The parcel over the real site: one small map per parcel, made only when it scrolls into view, with the ring drawn
   on it. Map = OpenStreetMap tiles; Aerial = Esri World Imagery, which is what the eye needs for a driveway, a shed
   or a fence line. Both carry their attribution. */
const BASES = {
  osm: { url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png", opts: { maxZoom: 19, attribution: "&copy; <a href=\\"https://www.openstreetmap.org/copyright\\">OpenStreetMap</a> contributors" } },
  aerial: { url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", opts: { maxZoom: 19, attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics and the GIS User Community" } },
};
let base = "osm";
const maps = new Map();
function makeMap(el) {
  const p = parcels[Number(el.dataset.i)];
  const ring = (p.ring_lonlat || [[]])[0] || [];
  if (!ring.length || !window.L) { el.textContent = "no ring"; return; }
  const map = L.map(el, { scrollWheelZoom: false, attributionControl: true, zoomControl: false });
  const layer = L.tileLayer(BASES[base].url, BASES[base].opts).addTo(map);
  const latlngs = ring.map(q => [q[1], q[0]]);
  const poly = L.polygon(latlngs, { color: "#1f3a4d", weight: 2, fillColor: "#3c8cdc", fillOpacity: 0.18 }).addTo(map);
  map.fitBounds(poly.getBounds().pad(0.5));
  L.control.zoom({ position: "bottomright" }).addTo(map);
  const fronts = L.layerGroup().addTo(map);
  const rec = { map, layer, fronts, latlngs, id: p.site_id, corners: cornersOf(latlngs) };
  maps.set(el, rec);
  // a draft from the first version of this page marked single published segments; they become the edges they lie on
  const dr = draft[p.site_id];
  if (dr && dr.front && dr.front.length && !dr.front_v2) {
    dr.front = Array.from(new Set(dr.front.map(i => edgeOfSegment(rec.corners, latlngs.length, i))));
    dr.front_v2 = true; store();
  }
  drawFronts(rec);
  // a click near the outline marks the whole edge it falls on, an edge being a run of the published line between
  // two corners (a curve published as many short segments is one edge); the first edge is the frontage, a second
  // the cross street; a click on a marked edge unmarks it
  const pick = e => {
    const pt = map.latLngToLayerPoint(e.latlng);
    let best = null;
    for (let i = 0; i < latlngs.length; i++) {
      const a = map.latLngToLayerPoint(latlngs[i]), b = map.latLngToLayerPoint(latlngs[(i + 1) % latlngs.length]);
      const d = L.LineUtil.pointToSegmentDistance(pt, a, b);
      if (best === null || d < best.d) best = { d, i };
    }
    if (!best || best.d > 18) return;
    const k = edgeOfSegment(rec.corners, latlngs.length, best.i);
    const dr = draft[p.site_id] = draft[p.site_id] || {};
    const list = dr.front || [];
    const at = list.indexOf(k);
    if (at >= 0) list.splice(at, 1); else list.push(k);
    dr.front = list; dr.front_v2 = true;
    store(); drawFronts(rec); frontNote(p.site_id); count();
  };
  poly.on("click", pick);
  map.on("click", pick);
}

/* The corners of a ring: the published points that survive a Douglas-Peucker pass at CORNER_TOL metres, as indices
   into the ring. A gentle curve collapses to its chord; a notch, a jog or an inward corner wider than the tolerance
   stays. The pass starts from the two points farthest apart so the ring closes properly. */
const CORNER_TOL = 1.6;
function cornersOf(latlngs) {
  const kLat = 110540, kLon = 111320 * Math.cos(latlngs[0][0] * Math.PI / 180);
  const pts = latlngs.map(([lat, lon]) => [lon * kLon, lat * kLat]);
  const n = pts.length;
  let a = 0, b = 0, far = -1;
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) { const d = Math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]); if (d > far) { far = d; a = i; b = j; } }
  const keep = new Set([a, b]);
  const dist = (p, s, t) => {
    const dx = t[0] - s[0], dy = t[1] - s[1], L2 = dx * dx + dy * dy;
    const u = L2 ? Math.max(0, Math.min(1, ((p[0] - s[0]) * dx + (p[1] - s[1]) * dy) / L2)) : 0;
    return Math.hypot(p[0] - (s[0] + u * dx), p[1] - (s[1] + u * dy));
  };
  const dp = idx => {   // idx: a run of ring indices from one kept point to the next
    if (idx.length < 3) return;
    const s = pts[idx[0]], t = pts[idx[idx.length - 1]];
    let worst = -1, at = -1;
    for (let k = 1; k < idx.length - 1; k++) { const d = dist(pts[idx[k]], s, t); if (d > worst) { worst = d; at = k; } }
    if (worst > CORNER_TOL) { keep.add(idx[at]); dp(idx.slice(0, at + 1)); dp(idx.slice(at)); }
  };
  const run = (from, to) => { const out = []; for (let i = from; ; i = (i + 1) % n) { out.push(i); if (i === to) break; } return out; };
  dp(run(a, b)); dp(run(b, a));
  return Array.from(keep).sort((x, y) => x - y);
}

/* Which edge (between consecutive corners, cyclic) the published segment i -> i+1 belongs to: the edge's number is
   the position of its first corner in the corners list. */
function edgeOfSegment(corners, n, i) {
  for (let k = 0; k < corners.length; k++) {
    const from = corners[k], to = corners[(k + 1) % corners.length];
    const len = ((to - from) % n + n) % n || n;
    if ((((i - from) % n) + n) % n < len) return k;
  }
  return 0;
}

/* The published points of edge k, from its first corner to its last, in order. */
function edgePoints(rec, k) {
  const n = rec.latlngs.length, from = rec.corners[k], to = rec.corners[(k + 1) % rec.corners.length];
  const out = [];
  for (let i = from; ; i = (i + 1) % n) { out.push(rec.latlngs[i]); if (i === to) break; }
  return out;
}

function edgeInfo(rec, k) {
  const pts = edgePoints(rec, k);
  const a = pts[0], b = pts[pts.length - 1];
  const kLat = 110540, kLon = 111320 * Math.cos(a[0] * Math.PI / 180);
  let length = 0;
  for (let i = 1; i < pts.length; i++) length += Math.hypot((pts[i][1] - pts[i - 1][1]) * kLon, (pts[i][0] - pts[i - 1][0]) * kLat);
  const e = (b[1] - a[1]) * kLon, nn = (b[0] - a[0]) * kLat;
  const bearing = (Math.atan2(e, nn) * 180 / Math.PI + 360) % 360;
  const dirs = ["N–S", "NE–SW", "E–W", "NW–SE"];
  return { edge: k + 1, from_point: rec.corners[k], to_point: rec.corners[(k + 1) % rec.corners.length], from: [a[1], a[0]], to: [b[1], b[0]],
           segments: pts.length - 1, length_m: Math.round(length * 10) / 10, chord_bearing_deg: Math.round(bearing * 10) / 10, runs: dirs[Math.round(((bearing % 180) / 45)) % 4] };
}

function drawFronts(rec) {
  rec.fronts.clearLayers();
  const list = (draft[rec.id] || {}).front || [];
  list.forEach((k, j) => {
    if (k >= rec.corners.length) return;
    L.polyline(edgePoints(rec, k), { color: j === 0 ? "#c81e1e" : "#c77d14", weight: 6, opacity: 0.9 }).addTo(rec.fronts);
  });
  // the corners, so the edges on offer can be seen
  rec.corners.forEach(i => L.circleMarker(rec.latlngs[i], { radius: 3, color: "#1f3a4d", weight: 1, fillColor: "#fff", fillOpacity: 1, interactive: false }).addTo(rec.fronts));
}

function frontNote(id) {
  const el = document.querySelector(`.parcel[data-id="${id}"] .front-note`);
  const rec = Array.from(maps.values()).find(r => r.id === id);
  if (!el || !rec) return;
  const list = ((draft[id] || {}).front || []).filter(k => k < rec.corners.length);
  if (!list.length) { el.innerHTML = `<b>Frontage:</b> click the edge on the street (red); a second edge marks the cross street (amber). ${rec.corners.length} edges between the white corners.`; return; }
  el.innerHTML = `<b>Frontage:</b> ` + list.map((k, j) => { const f = edgeInfo(rec, k); return `${j === 0 ? "edge" : "cross street, edge"} ${f.edge} of ${rec.corners.length}, ${f.length_m} m${f.segments > 1 ? ` (${f.segments} published segments)` : ""}, runs ${f.runs}`; }).join(" · ") + ` <span class="muted">(click an edge again to unmark)</span>`;
}
function watchMaps() {
  const els = Array.from(document.querySelectorAll(".map"));
  if (!("IntersectionObserver" in window)) { els.forEach(makeMap); return; }
  const io = new IntersectionObserver(entries => { for (const e of entries) if (e.isIntersecting && !maps.has(e.target)) { makeMap(e.target); io.unobserve(e.target); } }, { rootMargin: "300px 0px" });
  els.forEach(el => io.observe(el));
}
document.querySelectorAll("[data-base]").forEach(b => b.addEventListener("click", () => {
  base = b.dataset.base;
  document.querySelectorAll("[data-base]").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  for (const { map, layer } of maps.values()) { map.removeLayer(layer); }
  for (const [el, rec] of maps) { rec.layer = L.tileLayer(BASES[base].url, BASES[base].opts).addTo(rec.map); }
}));
function count() {
  const n = parcels.filter(p => (draft[p.site_id] || {}).label).length;
  const f = parcels.filter(p => ((draft[p.site_id] || {}).front || []).length).length;
  document.getElementById("count").textContent = `${n} of ${parcels.length} labelled · ${f} with a frontage`;
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
    labels: parcels.map(p => {
      const d = draft[p.site_id] || {};
      const ll = ((p.ring_lonlat || [[]])[0] || []).map(q => [q[1], q[0]]);
      const rec = Array.from(maps.values()).find(r => r.id === p.site_id) || { latlngs: ll, corners: cornersOf(ll) };
      const fronts = (d.front || []).filter(k => k < rec.corners.length).map((k, j) => Object.assign({ role: j === 0 ? "frontage" : "cross_street" }, edgeInfo(rec, k)));
      return { site_id: p.site_id, address: p.address, best_guess: p.best_guess, runner_up: p.runner_up, label: d.label || null, note: d.note || null,
               frontage_edges: fronts, corners: rec.corners,
               edge_numbering: `edges run between consecutive corners (Douglas-Peucker at ${CORNER_TOL} m on the published ring, cyclic); from_point and to_point are 0-based indices into ring_lonlat` };
    }) };
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
                     "ring_lonlat": p.get("ring_lonlat"),
                     "metrics": {k: m.get(k) for k in ("area_m2", "rectangularity", "convexity", "vertices", "vertices_raw", "narrowest_cross_section_m", "confidence")}})
    data = json.dumps(rows).replace("</", "<\\/")
    html = PAGE.replace("__DATA__", data).replace("__CLASSES__", json.dumps(CLASSES)).replace("__N__", str(len(rows)))
    (HERE / "label.html").write_text(html, encoding="utf-8")
    print(f"wrote {HERE / 'label.html'}: {len(rows)} parcels")


if __name__ == "__main__":
    main()
