"""Claude in the loop: the model proposes, a person confirms, the engine decides.

Two jobs, both outside the run (the engine never sees the model):

    propose_rule(document, district)   read a district schedule or a program guide and propose rule clauses
                                       for rules/: the figure, the section, the quote it came from, a confidence
    propose_site(site, document=None)  read a site file (and a survey, a plan or a photo when given) and propose
                                       the site file's fields: the equivalent rectangle, the frontage street,
                                       what is odd about the lot, trees

A proposal is a JSON file in proposals/: every item carries `source: "claude"`, a confidence and the evidence
excerpt, and the call is logged beside it (model id, date, prompt hash, usage). Nothing enters rules/ or sites/
until `confirm(proposal, by)` is run by a person; the rule or site then records who confirmed it and when.

The model is reached only with a key: FFM_CLAUDE_KEY in the environment (never in the repository), or a person's
own key typed into the tool, kept in their browser and sent with each request (the local server passes it
straight to the SDK and never stores it; the static site calls the Messages API from the page itself with
`browser_request` / `browser_proposal`). Without a key every call raises NoKey and the tool offers rule-derived
values only. The official SDK is used when it is installed (uv run --with anthropic python -m ffm propose ...;
it adds the server-side refusal fallback); without it the same request goes over plain HTTPS with urllib, so the
engine, the local server and the tests stay standard-library.

Public-repository rules hold: a practitioner's survey is read locally and only the proposal and, once confirmed,
the site file are kept. The document's bytes are sent to the model and nowhere else.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from .rules_loader import RULES_DIR

ROOT = Path(__file__).resolve().parent.parent
PROPOSALS_DIR = ROOT / "proposals"
SITES_DIR = ROOT / "sites"
KEY_ENV = "FFM_CLAUDE_KEY"
MODEL_ENV = "FFM_CLAUDE_MODEL"
DEFAULT_MODEL = "claude-sonnet-5-5"   # the proposal's choice for extraction; FFM_CLAUDE_MODEL overrides it
MAX_TOKENS = 16000

MEDIA = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
TEXT_EXT = {".txt", ".md", ".html", ".htm", ".json"}


class NoKey(RuntimeError):
    def __init__(self) -> None:
        super().__init__(f"{KEY_ENV} is not set. Set it in your shell (never in the repository): the model is called only with it; without it the tool offers rule-derived values only.")


class Refused(RuntimeError):
    pass


def available() -> dict[str, Any]:
    """What the UI and the CLI may offer: True only with a key in the environment."""
    return {"claude": bool(os.environ.get(KEY_ENV)), "model": os.environ.get(MODEL_ENV) or DEFAULT_MODEL}


# ---------------------------------------------------------------- the tools: one generic item list for both jobs

RULE_KEYS = ["document_title", "effective_from", "max_fsr", "max_height_m", "max_storeys", "min_front_yard_m", "min_rear_yard_m",
             "min_side_yard_m", "max_site_coverage", "fsr_conditions", "height_conditions", "notes"]
SITE_KEYS = ["zoning_district", "site_area_m2", "frontage_m", "depth_m", "frontage_street", "corner_lot", "lane_behind",
             "equivalent_rectangle_note", "easements_note", "existing_buildings_note", "slope_note", "trees_note", "notes"]


def _item_schema(keys: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "key": {"type": "string", "enum": keys},
            "value_text": {"type": "string", "description": "the value in words; for a number, the number as printed in the document"},
            "value_number": {"type": ["number", "null"], "description": "the value as a number where the key is numeric, else null"},
            "value_bool": {"type": ["boolean", "null"], "description": "yes or no where the key is a yes/no, else null"},
            "confidence": {"type": "number", "description": "0 to 1: how sure the document supports this value"},
            "evidence": {"type": "string", "description": "the sentence or table cell quoted from the document, verbatim, that gives the value; empty if inferred"},
            "section": {"type": "string", "description": "the section number or heading the evidence sits under, if any"},
            "page": {"type": ["integer", "null"], "description": "the page number the evidence is on, if known"},
        },
        "required": ["key", "value_text", "value_number", "value_bool", "confidence", "evidence", "section", "page"],
        "additionalProperties": False,
    }


def _tool(name: str, description: str, keys: list[str]) -> dict:
    return {
        "name": name, "description": description, "strict": True,
        "input_schema": {"type": "object", "properties": {"items": {"type": "array", "items": _item_schema(keys)}},
                         "required": ["items"], "additionalProperties": False},
    }


RULE_TOOL = _tool(
    "propose_rule_clauses",
    "Record the clauses of a zoning district schedule or a program guide as proposed rule parameters, one item per key, each with the quote it came from. "
    "Give every key the document supports and no others. Numbers in metres and ratios as printed; a conditional figure goes in its *_conditions item, not in the maximum.",
    RULE_KEYS)
SITE_TOOL = _tool(
    "propose_site_facts",
    "Record what the site file and the document support about the lot, one item per key, each with its evidence. Give only what is supported; say what is odd about the lot in the notes.",
    SITE_KEYS)

RULE_SYSTEM = (
    "You read planning documents for a deterministic feasibility engine. You propose; a person confirms; the engine decides. "
    "Report only what the document says, quoting it; never fill a gap from general knowledge. Where the schedule gives a base maximum "
    "and conditional increases (character retention, a larger site, a rezoning), the base goes in max_fsr or max_height_m and the "
    "conditions go in fsr_conditions or height_conditions as a short list with their figures. Yards: the minimum in metres for a "
    "multiple dwelling or the general case, with any variation noted in notes. Use the propose_rule_clauses tool for the answer.")
SITE_SYSTEM = (
    "You read a site file (public City data: the parcel polygon, the streets and buildings around it) and, when given, a survey, "
    "a site plan or a photo, for a deterministic feasibility engine. You propose; a person confirms; the engine decides. "
    "Report only what the data and the document support, with the evidence; where the lot is not a rectangle, propose the "
    "equivalent rectangle the engine should use (frontage along the street it faces, depth away from it) and say why. "
    "Never invent an easement, a tree or a slope. Use the propose_site_facts tool for the answer.")


# ---------------------------------------------------------------- the call

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


def _key(api_key: str | None) -> str:
    """The key handed in (a person's own, typed into the tool and sent with the request) or the environment's.
    Never read from a file, never written to one."""
    key = api_key or os.environ.get(KEY_ENV)
    if not key:
        raise NoKey()
    return key


def _client(api_key: str | None = None):
    """The SDK client, when the official SDK is installed (uv run --with anthropic …); ImportError otherwise."""
    key = _key(api_key)
    import anthropic  # the official SDK, imported only here
    return anthropic.Anthropic(api_key=key)


def _send_http(req: dict, api_key: str | None = None) -> dict:
    """The same request over plain HTTPS with the standard library, for a local server started without the SDK
    (the engine is standard-library by design). The response is the API's JSON, read by proposal_from_response as
    the browser's is. API errors are raised with the API's own message."""
    import urllib.error
    import urllib.request
    key = _key(api_key)
    data = json.dumps(req).encode("utf-8")
    r = urllib.request.Request(API_URL, data=data, method="POST",
                               headers={"content-type": "application/json", "x-api-key": key, "anthropic-version": API_VERSION})
    try:
        with urllib.request.urlopen(r, timeout=600) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode("utf-8")).get("error") or {}
            msg = f"{err.get('type') or e.code}: {err.get('message') or e.reason}"
        except Exception:
            msg = f"{e.code} {e.reason}"
        raise OSError(msg)


def _document_block(document: Path | tuple[bytes, str]) -> tuple[dict, dict]:
    """A content block for the document (PDF as a document, an image as an image, text inline) and its record:
    the name, size and hash, never the bytes. `document` is a path, or (bytes, name) when the page sent it."""
    if isinstance(document, tuple):
        data, name = document
    else:
        data, name = Path(document).read_bytes(), Path(document).name
    rec = {"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    ext = Path(name).suffix.lower()
    if ext == ".pdf":
        return {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": base64.standard_b64encode(data).decode("ascii")},
                "title": name, "cache_control": {"type": "ephemeral"}}, dict(rec, media_type="application/pdf")
    if ext in MEDIA:
        return {"type": "image", "source": {"type": "base64", "media_type": MEDIA[ext], "data": base64.standard_b64encode(data).decode("ascii")}}, dict(rec, media_type=MEDIA[ext])
    if ext in TEXT_EXT:
        return {"type": "text", "text": f"<document name=\"{name}\">\n{data.decode('utf-8', errors='replace')}\n</document>"}, dict(rec, media_type="text/plain")
    raise ValueError(f"Cannot read {name}: give a PDF, an image (png, jpg, gif, webp) or a text file.")


def _request(system: str, blocks: list[dict], tool: dict, model: str) -> dict:
    return {"model": model, "max_tokens": MAX_TOKENS,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": blocks}], "tools": [tool]}


def _prompt_hash(system: str, blocks: list[dict], tool: dict) -> str:
    return hashlib.sha256(json.dumps({"system": system, "tool": tool["name"], "text": [b.get("text", "") for b in blocks if b.get("type") == "text"]}, sort_keys=True).encode("utf-8")).hexdigest()


def _send(req: dict, client=None, caller: Callable[[dict], Any] | None = None, api_key: str | None = None):
    """One Messages call. `caller` (tests, or another transport) takes the request dict and returns a response with
    .content, .stop_reason, .model, .usage. Otherwise the SDK: the beta endpoint with the server-side fallback on a
    safety refusal where the SDK knows it, else the plain endpoint."""
    if caller is not None:
        return caller(req)
    if client is None:
        try:
            client = _client(api_key)
        except ImportError:   # no SDK on this machine: the standard library speaks to the same endpoint
            return _send_http(req, api_key)
    try:
        return client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **req)
    except TypeError:  # an SDK that predates the fallbacks parameter
        return client.messages.create(**req)


def _as_dict(resp: Any) -> dict:
    """A Messages response as plain data: the SDK's model, a test stub, or a dict the browser passed through."""
    if isinstance(resp, dict):
        return resp
    if hasattr(resp, "to_dict"):
        return resp.to_dict()
    out: dict[str, Any] = {}
    for k in ("content", "stop_reason", "stop_details", "model", "usage"):
        v = getattr(resp, k, None)
        if k == "content" and v is not None:
            v = [c if isinstance(c, dict) else {kk: getattr(c, kk) for kk in ("type", "name", "input", "text") if hasattr(c, kk)} for c in v]
        elif v is not None and not isinstance(v, (str, int, float, dict)):
            v = {kk: getattr(v, kk) for kk in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "category", "explanation") if hasattr(v, kk)}
        out[k] = v
    return out


def proposal_from_response(kind: str, resp: Any, tool_name: str, model: str, prompt_hash: str) -> dict[str, Any]:
    """The proposal record from a response: the items normalised, the call logged. A refusal is raised, never
    an empty proposal; so is a response without the tool call."""
    r = _as_dict(resp)
    if r.get("stop_reason") == "refusal":
        det = r.get("stop_details") or {}
        raise Refused(f"The model declined this document ({det.get('category') or 'no category'}): {det.get('explanation') or ''}".strip())
    content = r.get("content") or []
    tool_use = next((b for b in content if b.get("type") == "tool_use" and b.get("name") == tool_name), None)
    if tool_use is None:
        text = " ".join(b.get("text", "") for b in content if b.get("type") == "text").strip()
        raise RuntimeError("The model returned no proposal" + (f": {text[:300]}" if text else "."))
    inp = tool_use.get("input")
    if not isinstance(inp, dict):
        inp = json.loads(inp or "{}")
    items = [_norm_item(it) for it in (inp.get("items") or [])]
    usage = r.get("usage") or {}
    return {
        "kind": kind, "model": r.get("model") or model, "requested_at": datetime.now().isoformat(timespec="seconds"),
        "prompt_sha256": prompt_hash, "stop_reason": r.get("stop_reason"),
        "usage": {k: usage.get(k) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")} if usage else None,
        "items": items, "status": "proposed",
    }


def _run(kind: str, system: str, blocks: list[dict], tool: dict, model: str | None, client=None, caller=None, api_key: str | None = None) -> dict[str, Any]:
    model = model or os.environ.get(MODEL_ENV) or DEFAULT_MODEL
    req = _request(system, blocks, tool, model)
    resp = _send(req, client, caller, api_key)
    return proposal_from_response(kind, resp, tool["name"], model, _prompt_hash(system, blocks, tool))


def _norm_item(it: dict) -> dict:
    """One proposed item as the proposal file keeps it: a single `value`, the evidence, the confidence, the source."""
    num, txt, flag = it.get("value_number"), it.get("value_text"), it.get("value_bool")
    value: Any = num if num is not None else (flag if flag is not None else txt)
    conf = it.get("confidence")
    try:
        conf = max(0.0, min(1.0, float(conf)))
    except (TypeError, ValueError):
        conf = 0.0
    return {"key": it.get("key"), "value": value, "text": txt, "confidence": round(conf, 2), "evidence": it.get("evidence") or "",
            "section": it.get("section") or "", "page": it.get("page"), "source": "claude"}


# ---------------------------------------------------------------- the two jobs

def _rule_blocks(document: Path | tuple[bytes, str], district: str) -> tuple[list[dict], dict]:
    block, rec = _document_block(document)
    ask = {"type": "text", "text": f"This is the City of Vancouver district schedule for {district} (or a program guide). Propose its clauses for the {district} district: "
           f"the outright maximum floor space ratio and height, the minimum yards, site coverage, the effective date printed on it, and the conditions attached to any increase."}
    return [block, ask], rec


def _site_blocks(site: dict, document: Path | tuple[bytes, str] | None) -> tuple[list[dict], dict | None]:
    public = {k: v for k, v in site.items() if k not in ("osm",)}   # the context block is long; its frame and counts go instead
    osm = site.get("osm") or {}
    if osm:
        public["context_frame"] = osm.get("frame")
        public["context_counts"] = osm.get("counts")
        public["context_source"] = osm.get("source")
    blocks: list[dict] = [{"type": "text", "text": "<site_file>\n" + json.dumps(public, indent=1, ensure_ascii=False) + "\n</site_file>"}]
    rec = None
    if document:
        block, rec = _document_block(document)
        blocks.append(block)
    blocks.append({"type": "text", "text": "Propose the site file's fields from this evidence: confirm or correct the district, the area, the frontage and depth (the equivalent rectangle for an odd lot, and why), the street it fronts, whether it is a corner lot with a lane behind, and what is odd about it. Trees and easements only where the document shows them."})
    return blocks, rec


def propose_rule(document: Path | tuple[bytes, str], district: str, url: str | None = None, model: str | None = None, client=None, caller=None,
                 api_key: str | None = None) -> dict[str, Any]:
    blocks, rec = _rule_blocks(document, district)
    res = _run("rule", RULE_SYSTEM, blocks, RULE_TOOL, model, client, caller, api_key)
    res.update({"district": district, "slug": f"rule-{_slug(district)}-{date.today().isoformat()}", "document": rec, "url": url or ""})
    return res


def propose_site(site: dict, document: Path | tuple[bytes, str] | None = None, model: str | None = None, client=None, caller=None,
                 api_key: str | None = None) -> dict[str, Any]:
    blocks, rec = _site_blocks(site, document)
    res = _run("site", SITE_SYSTEM, blocks, SITE_TOOL, model, client, caller, api_key)
    res.update({"site_id": site.get("id"), "slug": f"site-{_slug(str(site.get('id') or 'site'))}-{date.today().isoformat()}", "document": rec})
    return res


# ---------------------------------------------------------------- the browser's path: the page holds the key and calls the API itself

def browser_request(kind: str, site: dict | None = None, document_b64: str | None = None, document_name: str | None = None,
                    district: str | None = None, model: str | None = None) -> dict[str, Any]:
    """The request body the page sends to the Messages API with the person's own key (the static site has no
    server to hold one), and what the page needs to log it: the tool name, the prompt hash, the document record."""
    model = model or DEFAULT_MODEL
    doc = (base64.standard_b64decode(document_b64), document_name or "document.pdf") if document_b64 else None
    if kind == "rule":
        if not district or doc is None:
            raise ValueError("A rule reading needs the district and the document.")
        blocks, rec = _rule_blocks(doc, district)
        system, tool = RULE_SYSTEM, RULE_TOOL
    else:
        blocks, rec = _site_blocks(site or {}, doc)
        system, tool = SITE_SYSTEM, SITE_TOOL
    return {"request": _request(system, blocks, tool, model), "tool": tool["name"], "prompt_sha256": _prompt_hash(system, blocks, tool),
            "document": rec, "model": model}


def browser_proposal(kind: str, response: dict, tool: str, model: str, prompt_sha256: str, site: dict | None = None,
                     district: str | None = None, url: str | None = None, document: dict | None = None) -> dict[str, Any]:
    """The proposal record from the API's JSON response, as propose_rule / propose_site would have made it."""
    res = proposal_from_response(kind, response, tool, model, prompt_sha256)
    if kind == "rule":
        res.update({"district": district, "slug": f"rule-{_slug(district or 'x')}-{date.today().isoformat()}", "document": document, "url": url or ""})
    else:
        res.update({"site_id": (site or {}).get("id"), "slug": f"site-{_slug(str((site or {}).get('id') or 'site'))}-{date.today().isoformat()}", "document": document})
    res["in_browser"] = True
    return res


def save(res: dict, out: Path) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------- confirming: a person moves a proposal into the data

def clauses_from(items: list[dict], district: str) -> list[dict]:
    """The rule entries a rule proposal becomes, in the engine's own shape (id, check, params); a person confirms
    them. The base maximum is the outright figure; conditions travel in the source's verify note."""
    by = {it["key"]: it for it in items if it.get("key")}
    slug = _slug(district).replace("-", "")
    out: list[dict] = []

    def num(k: str) -> float | None:
        v = (by.get(k) or {}).get("value")
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    def ev(*keys: str) -> str:
        return " · ".join(f"{by[k]['section']}: “{by[k]['evidence']}”".strip(": ") for k in keys if k in by and by[k].get("evidence"))

    if num("max_fsr") is not None:
        out.append({"id": f"cov.{slug}.outright_fsr", "title": f"{district} outright floor space ratio", "check": "district_outright_fsr",
                    "params": {"max_fsr": num("max_fsr")}, "evidence": ev("max_fsr"), "conditions": (by.get("fsr_conditions") or {}).get("text") or "",
                    "confidence": by["max_fsr"]["confidence"], "keys": ["max_fsr", "fsr_conditions"]})
    if num("max_height_m") is not None:
        p: dict[str, Any] = {"max_height_m": num("max_height_m")}
        if num("max_storeys") is not None:
            p["max_storeys"] = int(num("max_storeys"))
        out.append({"id": f"cov.{slug}.outright_height", "title": f"{district} outright maximum height", "check": "district_outright_height",
                    "params": p, "evidence": ev("max_height_m", "max_storeys"), "conditions": (by.get("height_conditions") or {}).get("text") or "",
                    "confidence": by["max_height_m"]["confidence"], "keys": ["max_height_m", "max_storeys", "height_conditions"]})
    yards = {f"min_{k}_yard_m": num(f"min_{k}_yard_m") for k in ("front", "rear", "side")}
    if any(v is not None for v in yards.values()):
        out.append({"id": f"cov.{slug}.setbacks", "title": f"{district} minimum yards", "check": "district_setbacks",
                    "params": {k: v for k, v in yards.items() if v is not None}, "evidence": ev("min_front_yard_m", "min_rear_yard_m", "min_side_yard_m"),
                    "conditions": "", "confidence": min(by[k]["confidence"] for k in ("min_front_yard_m", "min_rear_yard_m", "min_side_yard_m") if k in by),
                    "keys": ["min_front_yard_m", "min_rear_yard_m", "min_side_yard_m"]})
    if num("max_site_coverage") is not None:
        out.append({"id": f"cov.{slug}.site_coverage", "title": f"{district} maximum site coverage", "check": "info_only",
                    "params": {"max_site_coverage": num("max_site_coverage")}, "evidence": ev("max_site_coverage"), "conditions": "",
                    "confidence": by["max_site_coverage"]["confidence"], "keys": ["max_site_coverage"]})
    return out


def confirm(proposal: Path, by: str, only: list[str] | None = None, rules_dir: Path = RULES_DIR, sites_dir: Path = SITES_DIR,
            on: date | None = None) -> dict[str, Any]:
    """A person confirms a proposal: a rule proposal's clauses go into rules/a_zoning_district.json as new rules (or
    a new version of an existing rule), a site proposal's fields into the site file, each marked with who confirmed
    it and when. `only` limits the keys; everything else stays proposed."""
    proposal = Path(proposal)
    res = json.loads(proposal.read_text(encoding="utf-8"))
    on = on or date.today()
    if not by.strip():
        raise ValueError("Say who confirms (--by).")
    confirmed: list[str] = []
    skipped: list[str] = []

    if res["kind"] == "rule":
        district = res["district"]
        eff = next((it["value"] for it in res["items"] if it["key"] == "effective_from" and isinstance(it.get("value"), str) and re.match(r"^\d{4}-\d{2}-\d{2}$", it["value"])), None)
        title = next((it["text"] for it in res["items"] if it["key"] == "document_title"), None) or f"{district} District Schedule"
        path = rules_dir / "a_zoning_district.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        for c in clauses_from(res["items"], district):
            if only and not (set(c["keys"]) & set(only)) and c["id"] not in only:
                skipped.append(c["id"])
                continue
            source = {
                "title": f"{title} (read by {res['model']}, confirmed by {by} on {on.isoformat()})",
                "url": res.get("url") or "", "section": next((it["section"] for it in res["items"] if it["key"] in c["keys"] and it.get("section")), ""),
                "verify": (("Conditional increases: " + c["conditions"] + ". ") if c["conditions"] else "") + f"Evidence: {c['evidence']}" if c["evidence"] else "No quote was given: read the schedule.",
                "confirmed": {"by": by, "on": on.isoformat(), "proposal": proposal.name, "model": res["model"], "confidence": c["confidence"], "source": "claude"},
            }
            version = {"effective_from": eff or on.isoformat(), "params": c["params"], "source": source}
            existing = next((r for r in doc["rules"] if r["id"] == c["id"]), None)
            if existing:
                existing["versions"].append(version)
            else:
                doc["rules"].append({"id": c["id"], "title": c["title"], "jurisdiction": "City of Vancouver", "applies_to_districts": [district],
                                     "check": c["check"], "versions": [version]})
            confirmed.append(c["id"])
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        target = str(path)
    elif res["kind"] == "site":
        sid = res.get("site_id")
        path = next((p for p in sites_dir.glob("*.json") if json.loads(p.read_text(encoding="utf-8")).get("id") == sid), None) if sid else None
        if path is None:
            raise ValueError(f"No site file with id {sid!r} in {sites_dir}: save the site first, then confirm.")
        site = json.loads(path.read_text(encoding="utf-8"))
        site.setdefault("confirmed", {})
        notes = []
        for it in res["items"]:
            k = it["key"]
            if only and k not in only:
                skipped.append(k)
                continue
            if k in ("zoning_district", "site_area_m2", "frontage_m", "depth_m"):
                site[k] = it["value"]
            elif k == "corner_lot" and isinstance(it["value"], bool):
                site.setdefault("context", {})["corner_lot"] = it["value"]
            elif k == "lane_behind" and isinstance(it["value"], bool):
                site.setdefault("context", {})["lane_behind"] = it["value"]
            elif k == "frontage_street" and it["value"]:
                site.setdefault("context", {}).setdefault("street", {})["name"] = str(it["value"])
            elif k.endswith("_note") or k == "notes":
                if it["value"]:
                    notes.append(f"{k.replace('_note', '').replace('_', ' ')}: {it['value']}")
            else:
                skipped.append(k)
                continue
            site["confirmed"][k] = {"by": by, "on": on.isoformat(), "source": "claude", "proposal": proposal.name, "confidence": it["confidence"], "evidence": it["evidence"][:300]}
            confirmed.append(k)
        if notes:
            site["notes"] = ((site.get("notes") or "") + " " + f"Confirmed by {by} on {on.isoformat()} from a model reading: " + "; ".join(notes)).strip()
        path.write_text(json.dumps(site, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        target = str(path)
    else:
        raise ValueError(f"Unknown proposal kind {res.get('kind')!r}.")

    res["status"] = "confirmed" if not skipped else "partly confirmed"
    res["confirmed"] = {"by": by, "on": on.isoformat(), "keys": confirmed, "skipped": skipped}
    proposal.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"confirmed": confirmed, "skipped": skipped, "target": target, "on": on.isoformat()}


# ---------------------------------------------------------------- the eval set: hand-made cases, scored field by field

def score(items: list[dict], expected: dict[str, Any], tolerance: float = 0.01) -> dict[str, Any]:
    """Field-by-field: a number within the tolerance (relative), a string equal ignoring case and spacing, a bool
    equal. Missing expected keys count as misses; extra proposed keys are listed, not penalised."""
    got = {it["key"]: it.get("value") for it in items}
    rows = []
    hits = 0
    for k, want in expected.items():
        have = got.get(k)
        if isinstance(want, (int, float)) and not isinstance(want, bool):
            ok = isinstance(have, (int, float)) and not isinstance(have, bool) and abs(float(have) - float(want)) <= tolerance * max(1.0, abs(float(want)))
        elif isinstance(want, bool):
            ok = have is want
        else:
            ok = _norm_text(have) == _norm_text(want)
        hits += ok
        rows.append({"key": k, "expected": want, "got": have, "ok": ok})
    return {"hits": hits, "of": len(expected), "rows": rows, "extra": sorted(set(got) - set(expected))}


def _norm_text(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "x"
