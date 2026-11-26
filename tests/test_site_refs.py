"""The case page cites the memo it shows: each open item's reference (A1, C5…) is the one the committed R1 run of
998 E 19th Ave gives that rule, counted the way the tool counts (memo/memo.js memoRefs: the layer's letter and the
rule's place in the ledger's order). 17 Nov 2026: the page said A3, C4, E2, E1 and D1 where the memo said A1, C5,
E1, E2 and D2."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASE = ROOT / "ffm" / "ui" / "case.html"
R1 = ROOT / "outputs" / "998-e-19th-ave" / "as-approved" / "ledger.json"
# the words the page uses for a rule, and the rule
WORDS = {"Protection of Trees By-law": "cov.trees.replacement",
         "BC Builds": "bc.bcbuilds.eligibility", "Community Housing Fund": "bch.chf.eligibility"}
# (20 Nov 2026: the exits pass in the regenerated R1, so the page no longer cites them as an open item; 25 Nov 2026: the
# rezoning Council approved is no longer asked, so the Interim Rezoning Policy is not an open item either)


from ffm.engine import memo_refs, takes_ref   # the tool's count: only the rules that apply to the site (20 Nov 2026)


class CaseRefs(unittest.TestCase):
    def test_every_cited_reference_is_the_r1_memos_own(self):
        refs = memo_refs(json.loads(R1.read_text(encoding="utf-8"))["results"])
        cited = re.findall(r'<span class="rid">([A-F]\d+) · ([^<]+)</span>', CASE.read_text(encoding="utf-8"))
        self.assertEqual(len(cited), len(WORDS), cited)
        for ref, words in cited:
            self.assertIn(words, WORDS, words)
            self.assertEqual(ref, refs[WORDS[words]], f"{words}: the page says {ref}, the R1 memo {refs[WORDS[words]]}")

    def test_only_the_rules_that_apply_take_a_reference(self):
        results = json.loads(R1.read_text(encoding="utf-8"))["results"]
        refs = memo_refs(results)
        elsewhere = [r for r in results if not takes_ref(r)]
        self.assertGreater(len(elsewhere), 40)                       # the other districts' schedules
        self.assertTrue(all(r["status"] == "not_applicable" for r in elsewhere))
        self.assertFalse(any(r["rule_id"] in refs for r in elsewhere))
        # each layer numbers from 1 with no gaps over the rules that apply
        for layer in "ABCDEF":
            nums = sorted(int(v[1:]) for v in refs.values() if v[0] == layer)
            self.assertEqual(nums, list(range(1, len(nums) + 1)), layer)
        # a result the engine marks, and one from a ledger written before the mark
        self.assertFalse(takes_ref({"status": "pass", "elsewhere": "district"}))
        self.assertFalse(takes_ref({"status": "not_applicable", "finding": "Written for RT-3 districts; this site is zoned RM-1."}))
        self.assertTrue(takes_ref({"status": "not_applicable", "finding": "Not a CD-1 site."}))

    def test_no_rule_file_id_is_shown_to_the_reader(self):
        ids = re.findall(r'<span class="rid">([^<]+)</span>', CASE.read_text(encoding="utf-8"))
        for s in ids:
            self.assertNotRegex(s, r"\b[a-z]+\.[a-z_]+\.[a-z_]+\b", s)


if __name__ == "__main__":
    unittest.main()
