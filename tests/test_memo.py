"""The memo renders from a ledger, in Markdown and HTML, with the three answers and the stamp."""

import unittest
from datetime import date
from pathlib import Path

from ffm import massing, memo
from ffm.engine import diff, evaluate, load_json

ROOT = Path(__file__).resolve().parent.parent
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
OPTION = load_json(ROOT / "options" / "998-e-19th-ave-as-approved.json")


class MemoRenders(unittest.TestCase):
    def test_markdown_and_html_have_the_three_answers_and_the_stamp(self):
        L = evaluate(SITE, OPTION, date(2026, 10, 23))
        m = massing.build(SITE, OPTION, L)
        d = diff(evaluate(SITE, OPTION, date(2026, 10, 22)), L)
        md = memo.markdown(L, m, d)
        for needle in ("## 1. Is it allowed?", "## 2. Does it fit the funders?", "## 3. What is still unsure",
                       L["run"]["stamp"]["stamp"], "## Massing derived from the rules", "## Full ledger", "## Sources"):
            self.assertIn(needle, md)
        html = memo.html_page(md, massing.svg(m))
        self.assertIn("<svg", html)
        self.assertIn("First Read memo", html)
        self.assertNotIn("<?", html)

    def test_revit_section_appears_only_for_a_matching_stamp(self):
        L = evaluate(SITE, OPTION, date(2026, 10, 23))
        fake = {"ok": True, "mode": "test", "stages": {"masses": "ok"}, "built": [{"kind": "floor plates", "count": 5}],
                "errors": [], "stamp": L["run"]["stamp"]["stamp"]}
        self.assertIn("## Built in Revit", memo.markdown(L, revit=fake))
        self.assertNotIn("## Built in Revit", memo.markdown(L))


if __name__ == "__main__":
    unittest.main()
