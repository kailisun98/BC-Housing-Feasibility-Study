"""The page's own path to the model: a key handed in per request reaches the client, the request body the browser
sends is the same one the SDK would, and the API's plain JSON response becomes the same proposal record."""

import base64
import json
import os
import unittest
from pathlib import Path

from ffm import propose

ROOT = Path(__file__).resolve().parent.parent
CASE = ROOT / "evals" / "propose" / "rule-rt9-synthetic"


class BrowserPath(unittest.TestCase):
    def test_the_request_the_page_sends_matches_the_sdk_request(self):
        b64 = base64.standard_b64encode((CASE / "document.txt").read_bytes()).decode("ascii")
        made = propose.browser_request("rule", None, b64, "document.txt", "RT-9", None)
        req = made["request"]
        self.assertEqual(req["model"], propose.DEFAULT_MODEL)
        self.assertEqual(req["tools"][0]["name"], "propose_rule_clauses")
        self.assertTrue(req["tools"][0]["strict"])
        self.assertIn("4.7.1", req["messages"][0]["content"][0]["text"])
        self.assertEqual(made["document"]["name"], "document.txt")
        self.assertEqual(len(made["prompt_sha256"]), 64)
        # the same document through the SDK path gives the same prompt hash: one prompt, two transports
        seen = {}
        def caller(r):
            seen["req"] = r
            from types import SimpleNamespace
            return SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="propose_rule_clauses", input={"items": []})], stop_reason="tool_use", model="m", usage=None)
        res = propose.propose_rule(CASE / "document.txt", "RT-9", caller=caller)
        self.assertEqual(res["prompt_sha256"], made["prompt_sha256"])
        self.assertEqual(seen["req"]["messages"], req["messages"])

    def test_a_plain_json_response_becomes_the_same_proposal(self):
        response = {"model": "claude-sonnet-5-5", "stop_reason": "tool_use", "usage": {"input_tokens": 900, "output_tokens": 120},
                    "content": [{"type": "text", "text": "Reading the schedule."},
                                {"type": "tool_use", "id": "toolu_1", "name": "propose_rule_clauses", "input": {"items": [
                                    {"key": "max_fsr", "value_text": "0.60", "value_number": 0.6, "value_bool": None, "confidence": 0.9, "evidence": "shall not exceed 0.60", "section": "4.7.1", "page": 1}]}}]}
        res = propose.browser_proposal("rule", response, "propose_rule_clauses", "claude-sonnet-5-5", "a" * 64, district="RT-9", url="https://example.invalid/x.pdf", document={"name": "x.pdf", "sha256": "b" * 64, "bytes": 10})
        self.assertEqual(res["kind"], "rule")
        self.assertEqual(res["items"][0]["value"], 0.6)
        self.assertEqual(res["items"][0]["source"], "claude")
        self.assertEqual(res["usage"]["input_tokens"], 900)
        self.assertTrue(res["in_browser"])
        self.assertEqual(res["url"], "https://example.invalid/x.pdf")
        clauses = propose.clauses_from(res["items"], "RT-9")
        self.assertEqual(clauses[0]["id"], "cov.rt9.outright_fsr")

    def test_a_refusal_in_plain_json_is_raised(self):
        response = {"model": "m", "stop_reason": "refusal", "stop_details": {"type": "refusal", "category": "general_harms", "explanation": "no"}, "content": []}
        with self.assertRaises(propose.Refused):
            propose.browser_proposal("site", response, "propose_site_facts", "m", "a" * 64, site={"id": "s"})

    def test_a_key_handed_in_reaches_the_client_and_the_environment_is_not_needed(self):
        old = os.environ.pop(propose.KEY_ENV, None)
        try:
            with self.assertRaises(propose.NoKey):
                propose._client(None)
            # a fake SDK module, so the handed-in key is seen without the real package
            import sys, types
            fake = types.ModuleType("anthropic")
            seen = {}
            class Anthropic:
                def __init__(self, api_key=None):
                    seen["key"] = api_key
            fake.Anthropic = Anthropic
            sys.modules["anthropic"] = fake
            try:
                propose._client("sk-ant-test-not-a-real-key-0000")
            finally:
                del sys.modules["anthropic"]
            self.assertEqual(seen["key"], "sk-ant-test-not-a-real-key-0000")
        finally:
            if old is not None:
                os.environ[propose.KEY_ENV] = old

    def test_without_the_sdk_the_request_goes_over_plain_https(self):
        import sys, types
        import urllib.request
        # no SDK importable, a key in hand: _send must build the HTTPS request itself with the key in its header
        blocked = types.ModuleType("anthropic")
        def no(*a, **k):
            raise ImportError("no sdk here")
        blocked.__getattr__ = no
        sys.modules["anthropic"] = blocked
        seen = {}
        class FakeResp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return json.dumps({"model": "m", "stop_reason": "tool_use", "content": [{"type": "tool_use", "name": "propose_rule_clauses", "input": {"items": []}}]}).encode("utf-8")
        def fake_open(req, timeout=0):
            seen["url"] = req.full_url
            seen["key"] = req.get_header("X-api-key")
            seen["version"] = req.get_header("Anthropic-version")
            seen["body"] = json.loads(req.data.decode("utf-8"))
            return FakeResp()
        real = urllib.request.urlopen
        urllib.request.urlopen = fake_open
        try:
            res = propose.propose_rule(CASE / "document.txt", "RT-9", api_key="sk-ant-test-not-a-real-key-0000")
        finally:
            urllib.request.urlopen = real
            del sys.modules["anthropic"]
        self.assertEqual(seen["url"], propose.API_URL)
        self.assertEqual(seen["key"], "sk-ant-test-not-a-real-key-0000")
        self.assertEqual(seen["version"], propose.API_VERSION)
        self.assertEqual(seen["body"]["tools"][0]["name"], "propose_rule_clauses")
        self.assertEqual(res["status"], "proposed")

    def test_the_site_request_leaves_the_long_context_out(self):
        site = {"id": "s", "zoning_district": "RT-3", "osm": {"frame": {"front_street": "Heatley Ave"}, "counts": {"roads": 9}, "roads": [{"id": 1}] * 50}}
        made = propose.browser_request("site", site, None, None, None, None)
        text = made["request"]["messages"][0]["content"][0]["text"]
        self.assertIn("Heatley Ave", text)
        self.assertNotIn('"roads": [', text)


if __name__ == "__main__":
    unittest.main()
