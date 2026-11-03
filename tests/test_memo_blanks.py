"""A site or option with figures left blank still gets a memo: the writer says 'not given' instead of failing on a
number it cannot format (a looked-up site whose parcel was not found, or one typed by hand without an area)."""

import unittest
from datetime import date

from ffm import memo
from ffm.engine import evaluate

AS_OF = date(2026, 11, 2)


class BlankFigures(unittest.TestCase):
    def test_memo_without_area_or_gfa(self):
        site = {"id": "no-area", "address": "Somewhere, Vancouver, BC", "zoning_district": "RT-3", "site_area_m2": None,
                "frontage_m": None, "depth_m": None, "existing_trees_on_site": []}
        option = {"id": "no-area-option", "name": "Typed by hand", "tenure": "social_housing", "storeys": 3, "height_m": None,
                  "gfa_m2": None, "units": {"studio": 1, "one_bed": 1, "two_bed": 1, "three_bed_plus": 0}, "target_programs": []}
        L = evaluate(site, option, AS_OF)
        md = memo.markdown(L, None, None)
        self.assertIn("not given", md)
        self.assertIn("no-area", md)
        html = memo.html_page(md, None)
        self.assertIn("<html", html.lower())


if __name__ == "__main__":
    unittest.main()
