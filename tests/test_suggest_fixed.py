"""The manager's own figures carry the derivation (17 Nov 2026, found on 3475 E Hastings St): a floor area or unit
counts typed at 02 re-derive the homes, the funders' rent tiers and the accessible units, so the tiers always split
the homes the option holds and the Community Housing Fund is not failed on the suggestion's own, smaller count."""

import math
import unittest
from datetime import date
from pathlib import Path

from ffm import suggest
from ffm.engine import load_json

ROOT = Path(__file__).resolve().parent.parent
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
ON = date(2026, 11, 17)
PROGRAMS = ["bch.chf.eligibility", "bc.bcbuilds.eligibility"]


def homes(o):
    return sum(v or 0 for v in o["units"].values())


class FixedFigures(unittest.TestCase):
    def setUp(self):
        self.base = suggest.suggest(SITE, PROGRAMS, ON, "funder-ready")["option"]

    def test_a_larger_floor_area_derives_more_homes_and_splits_the_tiers_over_them(self):
        S = suggest.suggest(SITE, PROGRAMS, ON, "funder-ready", fixed={"gfa_m2": self.base["gfa_m2"] * 2, "storeys": 12})
        o = S["option"]
        self.assertEqual(o["gfa_m2"], self.base["gfa_m2"] * 2)
        self.assertEqual(o["storeys"], 12)
        self.assertGreater(homes(o), homes(self.base))
        self.assertEqual(sum(o["rent_tiers_units"].values()), homes(o))
        self.assertEqual(o["accessible_units"], math.ceil(0.05 * homes(o)))
        # the suggestion's own figure stays in the fields: what the rules derive, beside the manager's
        self.assertEqual(S["fields"]["gfa_m2"]["value"], self.base["gfa_m2"])

    def test_unit_counts_typed_stand_and_the_tiers_follow_them(self):
        o = suggest.suggest(SITE, PROGRAMS, ON, "funder-ready", fixed={"units": {"studio": 35, "one_bed": 70, "two_bed": 56, "three_bed_plus": 15}})["option"]
        self.assertEqual(o["units"], {"studio": 35, "one_bed": 70, "two_bed": 56, "three_bed_plus": 15})
        self.assertEqual(sum(o["rent_tiers_units"].values()), 176)
        self.assertEqual(o["accessible_units"], 9)

    def test_a_height_typed_is_the_option_height(self):
        o = suggest.suggest(SITE, PROGRAMS, ON, "funder-ready", fixed={"height_m": 61.6})["option"]
        self.assertEqual(o["height_m"], 61.6)

    def test_nothing_fixed_is_the_plain_suggestion(self):
        self.assertEqual(suggest.suggest(SITE, PROGRAMS, ON, "funder-ready", fixed={})["option"], self.base)
        self.assertEqual(suggest.suggest(SITE, PROGRAMS, ON, "funder-ready", fixed=None)["option"], self.base)

    def test_bad_figures_are_refused_in_words(self):
        for bad in ({"storeys": 2.5}, {"gfa_m2": -1}, {"units": {"loft": 3}}, {"units": {"studio": -2}}, {"colour": "red"}, "12"):
            with self.assertRaises(ValueError):
                suggest.suggest(SITE, PROGRAMS, ON, "funder-ready", fixed=bad)


if __name__ == "__main__":
    unittest.main()
