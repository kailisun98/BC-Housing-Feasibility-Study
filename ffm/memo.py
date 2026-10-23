"""Write the funding-fit memo from a ledger (+ massing, + optional diff). Markdown and HTML.

The memo answers three questions in order, then shows its work:

    1. Is it allowed?          layers A to C, outright and by rezoning
    2. Does it fit the funders? layer E, the programs the option targets
    3. What is still unsure, and who resolves it?

Every finding prints the numbers it used and links the source it came from. The version stamp
at the top ties the memo to the exact rule set, so two memos can be compared.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

STATUS_WORD = {
    "pass": "Pass", "conditional": "Conditional", "fail": "Fail", "uncertain": "Uncertain",
    "not_applicable": "Not applicable", "info": "Info",
}
# the UI's status set (DESIGN.md), deepened where white text sits on it: every pair clears 4.5:1
STATUS_COLOR = {
    "pass": "#2f7d4a", "conditional": "#9a6b00", "fail": "#c81e1e", "uncertain": "#a3640c",
    "not_applicable": "#5f6672", "info": "#2a6fb8",
}


def _src(r: dict) -> str:
    s = r.get("source") or {}
    t, u, sec = s.get("title"), s.get("url"), s.get("section")
    if not t and not u:
        return ""
    label = t or u
    if sec:
        label += f", {sec}"
    return f"[{label}]({u})" if u else label


def _fmt_vals(v: dict) -> str:
    bits = []
    for k, x in v.items():
        if isinstance(x, (dict, list)):
            continue
        if isinstance(x, float):
            x = f"{x:,.3f}".rstrip("0").rstrip(".")
        bits.append(f"{k.replace('_', ' ')} = {x}")
    return "; ".join(bits)


def markdown(ledger: dict, massing: dict | None = None, diff: dict | None = None, title: str | None = None,
             revit: dict | None = None) -> str:
    run, res, summ = ledger["run"], ledger["results"], ledger["summary"]
    site, opt = ledger["inputs"]["site"], ledger["inputs"]["option"]
    ans = summ["answers"]
    L: list[str] = []
    L.append(f"# Funding-fit memo: {site.get('address', site.get('id'))}")
    L.append("")
    L.append(f"**Option:** {opt.get('name', opt.get('id'))}  ")
    L.append(f"**Proponent:** {opt.get('proponent', '—')} ({str(opt.get('proponent_type', '')).replace('_', ' ')})  ")
    L.append(f"**Rules as of:** {run['as_of']} · **version stamp:** `{run['stamp']['stamp']}` · engine {run['engine_version']}  ")
    L.append("")
    L.append("> Deterministic output of the rule stack listed under *Sources*. Same inputs and rule set give the same memo. "
             "It is a feasibility screen, not legal, planning or funding advice; every number links to the document it came from, so check it there.")
    L.append("")

    # ---------------- the three answers
    L.append("## 1. Is it allowed?")
    o, bz = ans["allowed"]["outright"], ans["allowed"]["by_rezoning"]
    out_lines = [r for r in res if r.get("check", "").startswith("district_outright") and r["status"] != "not_applicable"]
    L.append(f"**Outright, under {site.get('zoning_district', 'the district')}: {o['verdict']}.** " + " ".join(r["finding"] for r in out_lines))
    L.append("")
    if ans["allowed"].get("rezoning_path"):
        L.append(f"**By rezoning ({ans['allowed']['rezoning_path']}): {bz['verdict']}.**")
        for r in res:
            if r["layer"] in ("A", "B", "C") and r["status"] in ("fail", "conditional", "uncertain") and not r.get("check", "").startswith("district_outright"):
                L.append(f"- *{STATUS_WORD[r['status']]}* — {r['title']}: {r['finding']}")
        L.append("")
    L.append("## 2. Does it fit the funders?")
    L.append(f"**{ans['funded']['verdict'].capitalize()}.**")
    for r in res:
        if r["layer"] == "E" and r["rule_id"] in (opt.get("target_programs") or [r["rule_id"]]):
            L.append(f"- *{STATUS_WORD[r['status']]}* — {r['title']}: {r['finding']}")
    L.append("")
    L.append("## 3. What is still unsure, and who resolves it?")
    if ans["unsure"]:
        L.append("| Item | Status | Who / what |")
        L.append("|---|---|---|")
        for u in ans["unsure"]:
            L.append(f"| {u['title']} | {STATUS_WORD[u['status']]} | {u['action'] or '—'} |")
    else:
        L.append("Nothing outstanding.")
    L.append("")

    # ---------------- massing
    if massing:
        L.append("## Massing derived from the rules")
        for mm in massing["masses"]:
            L.append(f"- **{mm['label']}** — plate {mm['plate_area_m2']:,.0f} m² × {mm['storeys']} storeys = {mm['gfa_m2']:,.0f} m² "
                     f"(FSR {mm['fsr']:.2f}), {mm['height_m']} m high, inside a {massing['envelope']['width_m']} × {massing['envelope']['depth_m']} m setback envelope. "
                     f"Derived from: {', '.join(mm['derived_from'])}.")
        if massing.get("policy_benchmark"):
            b = massing["policy_benchmark"]
            L.append(f"- Staff benchmark under {b['rule_id']}: {b['height_m'][0]} to {b['height_m'][1]} m, about FSR {b['fsr']}.")
        for w in massing.get("warnings", []):
            L.append(f"- Note: {w}")
        L.append("")
        L.append("![Massing plan and section](massing.svg)")
        L.append("")
        L.append("`massing.json` carries the same geometry for the Revit script (`revit/ffm_massing_pyrevit.py`).")
        L.append("")

    # ---------------- Revit, when the script has run on this exact stamp
    if revit:
        L.append("## Built in Revit")
        L.append(f"Mode: {revit.get('mode', '—')}. Stages: " + ", ".join(f"{k} {v}" for k, v in (revit.get("stages") or {}).items()) + ".")
        for b in revit.get("built", []):
            kind = b.get("kind")
            if kind == "mass":
                L.append(f"- Mass `{b.get('name')}` (element {b.get('element_id')}): {b.get('storeys')} storeys, {b.get('height_m')} m, plate {b.get('plate_area_m2'):,} m², FSR {b.get('fsr')}.")
            elif kind == "floor plates":
                L.append(f"- Floor plates: {b.get('count')}.")
            elif kind == "model lines":
                L.append(f"- Model lines: lot {b.get('lot')}, setback envelope {b.get('envelope')}.")
            elif kind == "view":
                L.append(f"- View: {b.get('name')} (element {b.get('element_id')}).")
            elif kind == "annotations":
                L.append(f"- Annotations: {b.get('dimensions')} dimensions, {b.get('notes')} text notes, {b.get('section_lines')} benchmark lines.")
            elif kind == "sheet":
                L.append(f"- Sheet {b.get('number')} (element {b.get('element_id')}), title block: {'yes' if b.get('title_block') else 'none in template'}.")
        if revit.get("saved_as"):
            L.append(f"- Saved as `{Path(revit['saved_as']).name}` next to this memo.")
        for e in revit.get("exports", []):
            L.append(f"- Exported `{Path(e).name}`.")
        if revit.get("errors"):
            L.append(f"- {len(revit['errors'])} stage error(s) recorded in `ffm_revit_result.json`; the stages marked ok above still stand.")
        if revit.get("sheet_png"):
            L.append("")
            L.append(f"![Revit sheet]({revit['sheet_png']})")
        notes = revit.get("sheet_notes") or {}
        if notes:
            L.append("")
            L.append("Text placed on the sheet (quotable in the memo):")
            L.append("")
            for key in ("allowed", "funders", "unsure", "massing"):
                for ln in notes.get(key, []):
                    L.append(f"> {ln}")
                L.append(">")
        L.append("")

    # ---------------- change log
    if diff:
        L.append("## What changed since the previous memo")
        L.append(f"Previous stamp `{diff.get('previous_stamp')}` (rules as of {diff.get('previous_as_of')}) → current `{diff.get('current_stamp')}` (as of {diff.get('current_as_of')}). "
                 + ("The rule files themselves changed." if diff.get("rules_changed") else "The rule files are unchanged; differences come from the as-of date or the inputs."))
        if diff["changes"]:
            L.append("")
            L.append("| Rule | Change | From | To | Now reads |")
            L.append("|---|---|---|---|---|")
            for c in diff["changes"]:
                frm = c.get("from") or "—"
                to = c.get("to") or "—"
                if c.get("from_version") and c.get("from_version") != c.get("to_version"):
                    frm += f" (v {c['from_version']})"
                    to += f" (v {c['to_version']})"
                L.append(f"| {c['rule_id']} | {c['change'].replace('_', ' ')} | {frm} | {to} | {c['finding']} |")
        else:
            L.append("")
            L.append("No rule changed status.")
        L.append("")

    # ---------------- the full ledger
    L.append("## Full ledger")
    cur_layer = None
    for r in res:
        if r["layer"] != cur_layer:
            cur_layer = r["layer"]
            L.append("")
            L.append(f"### Layer {r['layer']}: {r['layer_title']}")
            L.append("")
            L.append("| Rule | Status | Finding | Numbers used | Source |")
            L.append("|---|---|---|---|---|")
        L.append(f"| {r['title']} (`{r['rule_id']}`, v {r.get('version_effective_from') or '—'}) | {STATUS_WORD[r['status']]} | {r['finding']} | {_fmt_vals(r.get('values', {}))} | {_src(r)} |")
    L.append("")

    # ---------------- inputs and sources
    L.append("## Inputs")
    L.append(f"- Site `{site.get('id')}`: {site.get('zoning_district')}, {site.get('site_area_m2'):,} m², {site.get('frontage_m')} × {site.get('depth_m')} m; owner: {site.get('owner', '—')}.")
    u = opt.get("units") or {}
    units_txt = ", ".join("{0} {1}".format(k.replace("_", " "), v) for k, v in u.items())
    L.append(f"- Option `{opt.get('id')}`: {opt.get('storeys')} storeys, {opt.get('height_m')} m, {opt.get('gfa_m2'):,} m² GFA; units {units_txt}; tenure {str(opt.get('tenure', '')).replace('_', ' ')}.")
    if site.get("notes"):
        L.append(f"- Site notes: {site['notes']}")
    if opt.get("notes"):
        L.append(f"- Option notes: {opt['notes']}")
    L.append("")
    L.append("## Sources")
    seen = set()
    for r in res:
        s = r.get("source") or {}
        key = (s.get("title"), s.get("url"))
        if key in seen or not any(key):
            continue
        seen.add(key)
        line = f"- {s.get('title') or s.get('url')}"
        if s.get("url"):
            line += f" — {s['url']}"
        if s.get("verify"):
            line += f" *(verify: {s['verify']})*"
        L.append(line)
    for src in (site.get("sources") or []) + (opt.get("sources") or []):
        key = (src.get("title"), src.get("url"))
        if key not in seen:
            seen.add(key)
            L.append(f"- {src.get('title')} — {src.get('url')}")
    L.append("")
    L.append("## Version stamp")
    L.append(f"- Rules hash (SHA-256 over all rule files): `{run['stamp']['rules_hash']}`")
    for f, h in run["stamp"]["rules_files"].items():
        L.append(f"- `{f}`: `{h[:16]}…`")
    L.append(f"- Stamp (hash of rules hash + rule versions in force on {run['as_of']}): `{run['stamp']['stamp']}`")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- HTML

def _md_inline(s: str) -> str:
    """Tiny inline markdown: **bold**, *italic*, `code`, [text](url). Enough for the memo."""
    import re
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def html_page(md: str, svg_text: str | None = None) -> str:
    """Render the memo markdown to a self-contained HTML page (headings, paragraphs, lists, tables,
    blockquote, image replaced by the inline SVG). No external assets."""
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    in_list = in_table = in_quote = False

    def close():
        nonlocal in_list, in_table, in_quote
        if in_list:
            out.append("</ul>")
            in_list = False
        if in_table:
            out.append("</tbody></table>")
            in_table = False
        if in_quote:
            out.append("</blockquote>")
            in_quote = False

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("#"):
            close()
            level = len(ln) - len(ln.lstrip("#"))
            out.append(f"<h{level}>{_md_inline(ln[level:].strip())}</h{level}>")
        elif ln.startswith("- "):
            if in_table or in_quote:
                close()
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_md_inline(ln[2:])}</li>")
        elif ln.startswith("|"):
            if in_list or in_quote:
                close()
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if not in_table:
                out.append("<table><thead><tr>" + "".join(f"<th>{_md_inline(c)}</th>" for c in cells) + "</tr></thead><tbody>")
                in_table = True
                i += 2  # skip the |---| row
                continue
            tds = []
            for c in cells:
                word = c.strip()
                color = STATUS_COLOR.get(word.lower().replace(" ", "_"))
                tds.append(f'<td><span class="pill" style="background:{color}">{word}</span></td>' if color else f"<td>{_md_inline(c)}</td>")
            out.append("<tr>" + "".join(tds) + "</tr>")
        elif ln.startswith("> "):
            if in_list or in_table:
                close()
            if not in_quote:
                out.append("<blockquote>")
                in_quote = True
            out.append(f"<p>{_md_inline(ln[2:])}</p>")
        elif ln.startswith("!["):
            close()
            import re as _re
            mm = _re.match(r"!\[([^\]]*)\]\(([^)]+)\)", ln)
            alt, src = (mm.group(1), mm.group(2)) if mm else ("", "")
            if alt.startswith("Massing") and svg_text:
                out.append(f'<figure>{svg_text}<figcaption>Rule-derived massing: plan and section, to scale.</figcaption></figure>')
            else:
                out.append(f'<figure><img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}" style="max-width:100%;border:1px solid #e5e5e5"><figcaption>{html.escape(alt)}</figcaption></figure>')
        elif ln.strip() == "":
            close()
        else:
            if in_list or in_table or in_quote:
                close()
            out.append(f"<p>{_md_inline(ln.rstrip('  '))}</p>")
        i += 1
    close()
    body = "\n".join(out)
    css = """
    :root{--ink:#2c3e50;--muted:#5f6672;--line:#e1e5ea;--bg:#fff;--group:#e9eef4;--field:#f5f6f8;--blue:#2a6fb8}
    body{font-family:"IBM Plex Sans","Helvetica Neue",Helvetica,Arial,sans-serif;font-size:13.5px;color:var(--ink);background:var(--bg);max-width:1100px;margin:32px auto;padding:0 20px;line-height:1.45}
    h1{font-size:22px;font-weight:600;margin:0 0 8px;letter-spacing:-0.01em} h2{font-size:16px;font-weight:600;margin:28px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px} h3{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:18px 0 6px;color:var(--muted)}
    blockquote{border-left:3px solid var(--line);margin:12px 0;padding:4px 14px;color:var(--muted);font-size:12.5px}
    table{border-collapse:collapse;width:100%;font-size:12px;margin:8px 0 16px} th,td{border:1px solid var(--line);padding:6px 8px;vertical-align:top;text-align:left} th{background:var(--group);font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
    code{font-family:"IBM Plex Mono","SF Mono",Menlo,Consolas,monospace;background:var(--field);border:1px solid var(--line);padding:1px 4px;border-radius:3px;font-size:11.5px}
    .pill{color:#fff;border-radius:10px;padding:1px 8px;font-size:11px;font-weight:600;white-space:nowrap}
    figure{margin:12px 0} figure svg{max-width:100%;height:auto;border:1px solid var(--line)} figcaption{font-size:12px;color:var(--muted)}
    li{margin:3px 0} a{color:var(--blue)}
    @media print{body{margin:0;max-width:none} h2{break-after:avoid}}
    """
    return f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Funding-fit memo</title><style>{css}</style></head><body>{body}</body></html>"


def load_revit_result(out_dir: Path, stamp: str) -> dict | None:
    """The Revit script's result for this exact stamp, if it has run on this folder."""
    p = out_dir / "ffm_revit_result.json"
    if not p.exists():
        return None
    try:
        r = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if r.get("stamp") != stamp:
        return None
    if (out_dir / "ffm_sheet.png").exists():
        r["sheet_png"] = "ffm_sheet.png"
    n = out_dir / "ffm_sheet_notes.json"
    if n.exists():
        try:
            r["sheet_notes"] = json.loads(n.read_text(encoding="utf-8"))
        except Exception:
            pass
    return r


def write(ledger: dict, out_dir: Path, massing: dict | None = None, diff: dict | None = None, svg_text: str | None = None,
          revit: dict | None = None) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if revit is None:
        revit = load_revit_result(out_dir, ledger["run"]["stamp"]["stamp"])
    md = markdown(ledger, massing, diff, revit=revit)
    pm = out_dir / "memo.md"
    ph = out_dir / "memo.html"
    pm.write_text(md, encoding="utf-8")
    ph.write_text(html_page(md, svg_text), encoding="utf-8")
    return pm, ph
