"""Claude proposes, a person confirms, the engine decides: the proposal file carries source, confidence and
evidence; nothing enters the rules until confirm; a confirmed RT-9 schedule then drives the suggestion and the
engine for an RT-9 site; without a key the call refuses; the scorer reads the eval case. The model is a stub."""

import json
import os
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from ffm import propose, suggest
from ffm.engine import evaluate
from ffm.rules_loader import load_rules

ROOT = Path(__file__).resolve().parent.parent
CASE = ROOT / "evals" / "propose" / "rule-rt9-synthetic"
EXPECTED = json.loads((CASE / "expected.json").read_text(encoding="utf-8"))["expected"]


def stub_items():
    return [
        {"key": "document_title", "value_text": "RT-9 District Schedule (synthetic)", "value_number": None, "value_bool": None, "confidence": 0.95, "evidence": "RT-9 DISTRICT SCHEDULE", "section": "", "page": 1},
        {"key": "effective_from", "value_text": "2026-03-15", "value_number": None, "value_bool": None, "confidence": 0.9, "evidence": "Consolidated to 15 March 2026.", "section": "", "page": 1},
        {"key": "max_fsr", "value_text": "0.60", "value_number": 0.60, "value_bool": None, "confidence": 0.93, "evidence": "The floor space ratio shall not exceed 0.60.", "section": "4.7.1", "page": 1},
        {"key": "fsr_conditions", "value_text": "up to 0.75 where a character house is retained and renovated; 0.85 where it is also protected heritage property", "value_number": None, "value_bool": None, "confidence": 0.9, "evidence": "The Director of Planning may permit an increase in the floor space ratio to a maximum of 0.75", "section": "4.7.2", "page": 1},
        {"key": "max_height_m", "value_text": "10.7 m", "value_number": 10.7, "value_bool": None, "confidence": 0.94, "evidence": "The maximum height of a building shall be 10.7 m", "section": "4.3.1", "page": 1},
        {"key": "max_storeys", "value_text": "3", "value_number": 3, "value_bool": None, "confidence": 0.9, "evidence": "a building shall not exceed 3 storeys", "section": "4.3.1", "page": 1},
        {"key": "min_front_yard_m", "value_text": "6.1 m", "value_number": 6.1, "value_bool": None, "confidence": 0.9, "evidence": "A front yard with a minimum depth of 6.1 m shall be provided", "section": "4.4.1", "page": 1},
        {"key": "min_side_yard_m", "value_text": "1.5 m", "value_number": 1.5, "value_bool": None, "confidence": 0.9, "evidence": "A side yard with a minimum width of 1.5 m", "section": "4.5.1", "page": 1},
        {"key": "min_rear_yard_m", "value_text": "10.7 m", "value_number": 10.7, "value_bool": None, "confidence": 0.9, "evidence": "A rear yard with a minimum depth of 10.7 m", "section": "4.6.1", "page": 1},
        {"key": "max_site_coverage", "value_text": "45 percent", "value_number": 0.45, "value_bool": None, "confidence": 0.85, "evidence": "The maximum site coverage for buildings shall be 45 percent", "section": "4.8.1", "page": 1},
    ]


def stub_caller(items=None, stop_reason="tool_use"):
    seen = {}

    def call(req):
        seen["request"] = req
        block = SimpleNamespace(type="tool_use", name="propose_rule_clauses" if req["tools"][0]["name"] == "propose_rule_clauses" else "propose_site_facts", input={"items": items if items is not None else stub_items()})
        return SimpleNamespace(content=[block], stop_reason=stop_reason, model="stub-model",
                               usage=SimpleNamespace(input_tokens=1200, output_tokens=300, cache_read_input_tokens=0, cache_creation_input_tokens=900))
    call.seen = seen
    return call


class Proposal(unittest.TestCase):
    def test_a_rule_proposal_carries_source_confidence_evidence_and_the_log(self):
        call = stub_caller()
        res = propose.propose_rule(CASE / "document.txt", "RT-9", url="https://example.invalid/rt-9.pdf", model="stub-model", caller=call)
        self.assertEqual(res["kind"], "rule")
        self.assertEqual(res["status"], "proposed")
        self.assertTrue(all(it["source"] == "claude" for it in res["items"]))
        fsr = next(it for it in res["items"] if it["key"] == "max_fsr")
        self.assertEqual(fsr["value"], 0.60)
        self.assertEqual(fsr["section"], "4.7.1")
        self.assertIn("shall not exceed 0.60", fsr["evidence"])
        self.assertEqual(res["document"]["name"], "document.txt")
        self.assertEqual(len(res["document"]["sha256"]), 64)
        self.assertEqual(res["usage"]["input_tokens"], 1200)
        self.assertEqual(len(res["prompt_sha256"]), 64)
        req = call.seen["request"]
        self.assertTrue(req["tools"][0]["strict"])
        self.assertEqual(req["tools"][0]["input_schema"]["additionalProperties"], False)
        self.assertIn("RT-9", req["messages"][0]["content"][-1]["text"])
        self.assertIn("4.7.1", req["messages"][0]["content"][0]["text"])   # the document went in as text

    def test_the_scorer_reads_the_eval_case(self):
        res = propose.propose_rule(CASE / "document.txt", "RT-9", caller=stub_caller())
        s = propose.score(res["items"], EXPECTED)
        self.assertEqual(s["hits"], s["of"])
        wrong = [dict(it, value_number=0.75) if it["key"] == "max_fsr" else it for it in stub_items()]
        s2 = propose.score(propose.propose_rule(CASE / "document.txt", "RT-9", caller=stub_caller(wrong))["items"], EXPECTED)
        self.assertEqual(s2["hits"], s2["of"] - 1)

    def test_without_a_key_the_call_refuses(self):
        old = os.environ.pop(propose.KEY_ENV, None)
        try:
            self.assertFalse(propose.available()["claude"])
            with self.assertRaises(propose.NoKey):
                propose.propose_rule(CASE / "document.txt", "RT-9")
        finally:
            if old is not None:
                os.environ[propose.KEY_ENV] = old

    def test_a_refusal_is_said_not_swallowed(self):
        with self.assertRaises(propose.Refused):
            propose.propose_rule(CASE / "document.txt", "RT-9", caller=stub_caller(stop_reason="refusal"))


class Confirm(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rules = self.tmp / "rules"
        shutil.copytree(ROOT / "rules", self.rules)
        res = propose.propose_rule(CASE / "document.txt", "RT-9", url="https://example.invalid/rt-9.pdf", caller=stub_caller())
        self.proposal = propose.save(res, self.tmp / "proposals" / "rt9.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_nothing_enters_the_rules_before_confirm(self):
        ids = {r.id for r in load_rules(self.rules)}
        self.assertNotIn("cov.rt9.outright_fsr", ids)

    def test_confirm_writes_dated_cited_rules_naming_who_confirmed(self):
        rep = propose.confirm(self.proposal, "Kai Sun", rules_dir=self.rules, on=date(2026, 11, 3))
        self.assertEqual(set(rep["confirmed"]), {"cov.rt9.outright_fsr", "cov.rt9.outright_height", "cov.rt9.setbacks", "cov.rt9.site_coverage"})
        rules = {r.id: r for r in load_rules(self.rules)}
        fsr = rules["cov.rt9.outright_fsr"]
        v = fsr.version_on(date(2026, 11, 3))
        self.assertEqual(v.params, {"max_fsr": 0.6})
        self.assertEqual(v.effective_from.isoformat(), "2026-03-15")
        self.assertIn("confirmed by Kai Sun on 2026-11-03", v.source["title"])
        self.assertIn("0.75", v.source["verify"])   # the conditions travel in the verify note, not in the maximum
        self.assertEqual(v.source["confirmed"]["source"], "claude")
        self.assertEqual(rules["cov.rt9.outright_height"].version_on(date(2026, 11, 3)).params, {"max_height_m": 10.7, "max_storeys": 3})
        self.assertEqual(rules["cov.rt9.setbacks"].check, "district_setbacks")
        saved = json.loads(self.proposal.read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "confirmed")
        self.assertEqual(saved["confirmed"]["by"], "Kai Sun")

    def test_only_confirms_the_named_keys(self):
        rep = propose.confirm(self.proposal, "Kai Sun", only=["max_fsr"], rules_dir=self.rules)
        self.assertEqual(rep["confirmed"], ["cov.rt9.outright_fsr"])
        self.assertIn("cov.rt9.outright_height", rep["skipped"])
        self.assertEqual(json.loads(self.proposal.read_text(encoding="utf-8"))["status"], "partly confirmed")

    def test_a_confirmed_schedule_drives_the_suggestion_and_the_engine(self):
        propose.confirm(self.proposal, "Kai Sun", rules_dir=self.rules, on=date(2026, 11, 3))
        site = {"id": "rt9-lot", "address": "a lot", "zoning_district": "RT-9", "site_area_m2": 560, "frontage_m": 15.2, "depth_m": 37.2,
                "has_water_and_sewer": True, "in_transit_oriented_area": False, "existing_trees_on_site": []}
        S = suggest.suggest(site, [], date(2026, 11, 3), "outright", rules_dir=self.rules)
        o = S["option"]
        self.assertEqual(o["storeys"], 3)
        self.assertEqual(o["gfa_m2"], 336)                       # 0.60 × 560
        self.assertEqual(S["fields"]["gfa_m2"]["rule_id"], "cov.rt9.outright_fsr")
        self.assertEqual(o["setbacks_m"], {"front": 6.1, "rear": 10.7, "side": 1.5})
        self.assertEqual(S["fields"]["setbacks_m.front"]["rule_id"], "cov.rt9.setbacks")
        L = evaluate(site, o, date(2026, 11, 3), rules_dir=self.rules)
        by = {r["rule_id"]: r for r in L["results"]}
        self.assertEqual(by["cov.rt9.outright_fsr"]["status"], "pass")
        self.assertEqual(by["cov.rt9.setbacks"]["status"], "pass")
        self.assertEqual(by["cov.rm1.outright_fsr"]["status"], "not_applicable")
        tight = dict(o, setbacks_m={"front": 3.0, "rear": 10.7, "side": 1.5})
        self.assertEqual(evaluate(site, tight, date(2026, 11, 3), rules_dir=self.rules)["results"][[r["rule_id"] for r in L["results"]].index("cov.rt9.setbacks")]["status"], "conditional")


class SiteProposal(unittest.TestCase):
    def test_site_items_confirm_into_the_site_file(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            sites = tmp / "sites"
            sites.mkdir()
            site = {"id": "odd-lot", "address": "an odd lot", "zoning_district": "RT-3", "site_area_m2": 566.7, "frontage_m": 37.2, "depth_m": 15.2, "osm": {"frame": {"front_street": "Heatley Ave"}, "counts": {"roads": 9}, "source": "City"}}
            (sites / "odd-lot.json").write_text(json.dumps(site), encoding="utf-8")
            items = [
                {"key": "frontage_m", "value_text": "15.2", "value_number": 15.2, "value_bool": None, "confidence": 0.7, "evidence": "the short side faces Heatley Ave", "section": "", "page": None},
                {"key": "depth_m", "value_text": "37.2", "value_number": 37.2, "value_bool": None, "confidence": 0.7, "evidence": "the long side runs along Keefer St", "section": "", "page": None},
                {"key": "corner_lot", "value_text": "yes", "value_number": None, "value_bool": True, "confidence": 0.9, "evidence": "Keefer St on the right", "section": "", "page": None},
                {"key": "equivalent_rectangle_note", "value_text": "the lot is a true rectangle; the frontage is the short side", "value_number": None, "value_bool": None, "confidence": 0.8, "evidence": "", "section": "", "page": None},
            ]
            call = stub_caller(items)
            res = propose.propose_site(site, caller=call)
            self.assertEqual(res["kind"], "site")
            self.assertNotIn("roads", call.seen["request"]["messages"][0]["content"][0]["text"][:200])   # the long context block is not sent, its frame is
            p = propose.save(res, tmp / "p.json")
            rep = propose.confirm(p, "Kai Sun", sites_dir=sites, on=date(2026, 11, 3))
            saved = json.loads((sites / "odd-lot.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["frontage_m"], 15.2)
            self.assertEqual(saved["depth_m"], 37.2)
            self.assertTrue(saved["context"]["corner_lot"])
            self.assertEqual(saved["confirmed"]["frontage_m"]["by"], "Kai Sun")
            self.assertEqual(saved["confirmed"]["frontage_m"]["source"], "claude")
            self.assertIn("Confirmed by Kai Sun", saved["notes"])
            self.assertEqual(set(rep["confirmed"]), {"frontage_m", "depth_m", "corner_lot", "equivalent_rectangle_note"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
