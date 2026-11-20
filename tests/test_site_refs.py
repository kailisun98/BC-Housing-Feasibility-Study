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
WORDS = {"Interim Rezoning Policy": "cov.irp.social_housing_rezoning", "Protection of Trees By-law": "cov.trees.replacement",
         "BC Builds": "bc.bcbuilds.eligibility", "Community Housing Fund": "bch.chf.eligibility"}
# (20 Nov 2026: the exits pass in the regenerated R1, so the page no longer cites them as an open item)


def memo_refs(results):
    n, ref = {}, {}
    for r in results:
        n[r["layer"]] = n.get(r["layer"], 0) + 1
        ref[r["rule_id"]] = f"{r['layer']}{n[r['layer']]}"
    return ref


class CaseRefs(unittest.TestCase):
    def test_every_cited_reference_is_the_r1_memos_own(self):
        refs = memo_refs(json.loads(R1.read_text(encoding="utf-8"))["results"])
        cited = re.findall(r'<span class="rid">([A-F]\d+) · ([^<]+)</span>', CASE.read_text(encoding="utf-8"))
        self.assertEqual(len(cited), len(WORDS), cited)
        for ref, words in cited:
            self.assertIn(words, WORDS, words)
            self.assertEqual(ref, refs[WORDS[words]], f"{words}: the page says {ref}, the R1 memo {refs[WORDS[words]]}")

    def test_no_rule_file_id_is_shown_to_the_reader(self):
        ids = re.findall(r'<span class="rid">([^<]+)</span>', CASE.read_text(encoding="utf-8"))
        for s in ids:
            self.assertNotRegex(s, r"\b[a-z]+\.[a-z_]+\.[a-z_]+\b", s)


if __name__ == "__main__":
    unittest.main()
