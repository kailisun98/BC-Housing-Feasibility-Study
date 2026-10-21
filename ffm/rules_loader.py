"""Load the rule stack from rules/*.json, pick the version in force on a date, and stamp it.

Every rule carries one or more dated versions. The version in force on the run date is the one
whose effective_from <= date and (effective_to is absent or date <= effective_to). The stamp is a
SHA-256 over the canonical JSON of every rule file plus the list of (rule id, version) pairs in
force, so two runs on the same rules produce the same stamp and any edit to a rule changes it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"


@dataclass
class RuleVersion:
    effective_from: date
    effective_to: Optional[date]
    params: dict[str, Any]
    source: dict[str, Any]

    def in_force(self, on: date) -> bool:
        if on < self.effective_from:
            return False
        if self.effective_to is not None and on > self.effective_to:
            return False
        return True


@dataclass
class Rule:
    id: str
    layer: str
    layer_title: str
    title: str
    jurisdiction: str
    applies_to_districts: list[str]
    check: str
    versions: list[RuleVersion] = field(default_factory=list)
    file: str = ""

    def version_on(self, on: date) -> Optional[RuleVersion]:
        hits = [v for v in self.versions if v.in_force(on)]
        if not hits:
            return None
        # If two versions overlap, the later effective_from wins.
        return sorted(hits, key=lambda v: v.effective_from)[-1]

    def applies_to(self, district: str) -> bool:
        """'*' matches every district; 'RM-1' matches exactly; a family code such as 'RS' or 'RT'
        matches any district in that family ('RS-1', 'RT-3')."""
        if "*" in self.applies_to_districts:
            return True
        d = (district or "").upper()
        for x in self.applies_to_districts:
            x = x.upper()
            if d == x:
                return True
            if "-" not in x and d.startswith(x + "-"):
                return True
        return False


def _parse_date(s: Optional[str]) -> Optional[date]:
    return date.fromisoformat(s) if s else None


def load_rules(rules_dir: Path = RULES_DIR) -> list[Rule]:
    rules: list[Rule] = []
    for path in sorted(rules_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for r in data.get("rules", []):
            versions = [
                RuleVersion(
                    effective_from=_parse_date(v["effective_from"]),
                    effective_to=_parse_date(v.get("effective_to")),
                    params=v.get("params", {}),
                    source=v.get("source", {}),
                )
                for v in r.get("versions", [])
            ]
            rules.append(
                Rule(
                    id=r["id"],
                    layer=data.get("layer", "?"),
                    layer_title=data.get("layer_title", ""),
                    title=r["title"],
                    jurisdiction=r.get("jurisdiction", ""),
                    applies_to_districts=r.get("applies_to_districts", ["*"]),
                    check=r["check"],
                    versions=versions,
                    file=path.name,
                )
            )
    return rules


def rules_hash(rules_dir: Path = RULES_DIR) -> dict[str, str]:
    """SHA-256 per rule file and overall, over canonical JSON (sorted keys, no whitespace)."""
    per_file: dict[str, str] = {}
    overall = hashlib.sha256()
    for path in sorted(rules_dir.glob("*.json")):
        canon = json.dumps(json.loads(path.read_text(encoding="utf-8")), sort_keys=True, separators=(",", ":"))
        h = hashlib.sha256(canon.encode("utf-8")).hexdigest()
        per_file[path.name] = h
        overall.update(h.encode("ascii"))
    return {"overall": overall.hexdigest(), "files": per_file}


def stamp(rules: list[Rule], on: date, rules_dir: Path = RULES_DIR) -> dict[str, Any]:
    """The version stamp a memo carries: which rule versions were in force, and the rules hash."""
    in_force = []
    for r in rules:
        v = r.version_on(on)
        in_force.append(
            {
                "rule_id": r.id,
                "layer": r.layer,
                "version_effective_from": v.effective_from.isoformat() if v else None,
                "version_effective_to": v.effective_to.isoformat() if (v and v.effective_to) else None,
                "source_url": (v.source.get("url") if v else None),
            }
        )
    h = rules_hash(rules_dir)
    digest = hashlib.sha256(
        (h["overall"] + json.dumps(in_force, sort_keys=True, separators=(",", ":"))).encode("utf-8")
    ).hexdigest()
    return {
        "as_of": on.isoformat(),
        "rules_hash": h["overall"],
        "rules_files": h["files"],
        "stamp": digest[:16],
        "rule_versions": in_force,
    }
