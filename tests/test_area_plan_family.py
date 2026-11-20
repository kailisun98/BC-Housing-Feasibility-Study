"""An area plan's own family-unit target replaces the city-wide one inside the plan area (17 Nov 2026)."""
import unittest
from datetime import date

from ffm.engine import evaluate

ON = date(2026, 11, 17)
OPTION = {"tenure": "social_housing", "units": {"studio": 51, "one_bed": 72, "two_bed": 35, "three_bed_plus": 5}}


def family(site, option):
    led = evaluate(site, option, ON)
    return {r["rule_id"]: r for r in led["results"] if r["check"] == "family_unit_share"}


class AreaPlanFamilyTarget(unittest.TestCase):
    def test_outside_a_plan_area_the_city_wide_rule_decides(self):
        r = family({"zoning_district": "RM-1"}, OPTION)
        self.assertEqual(r["cov.family_units"]["status"], "fail")
        self.assertEqual(r["cov.dtes.family_units"]["status"], "not_applicable")

    def test_inside_the_plan_area_the_plan_decides(self):
        site = {"zoning_district": "CD-1 (819)", "cd1_bylaw_number": 819, "area_plan": "downtown_eastside"}
        r = family(site, dict(OPTION, supportive_units=25))
        self.assertEqual(r["cov.family_units"]["status"], "not_applicable")
        plan = r["cov.dtes.family_units"]
        self.assertEqual(plan["status"], "pass")
        self.assertEqual(plan["values"]["units_total"], 138)          # 163 less the 25 supportive homes
        self.assertEqual(plan["values"]["two_plus_bed_share"], 0.2899)
        self.assertEqual(plan["values"]["two_plus_bed_share_of_all"], 0.2454)

    def test_without_the_supportive_count_every_home_is_counted(self):
        site = {"zoning_district": "CD-1 (819)", "area_plan": "downtown_eastside"}
        plan = family(site, OPTION)["cov.dtes.family_units"]
        self.assertEqual(plan["status"], "fail")                      # 40 of 163 is 24.5%, under 25%
        self.assertIn("not stated", plan["finding"])


class FsrComparedAtTwoDecimals(unittest.TestCase):
    """An FSR is compared with its maximum at two decimals, as a schedule states it."""
    P = {"max_fsr": 6.9}

    def fsr(self, gfa):
        from ffm.checks import district_outright_fsr
        return district_outright_fsr({"site_area_m2": 2134.4}, {"gfa_m2": gfa, "rezoning_path": "CD-1"}, self.P)

    def test_the_reports_floor_area_is_within_the_maximum(self):
        self.assertEqual(self.fsr(14729.0)["status"], "pass")          # 6.9008, stated as 6.90

    def test_a_hundredth_over_is_still_over(self):
        r = self.fsr(14750.0)                                           # 6.9106, stated as 6.91
        self.assertEqual(r["status"], "fail")                           # outright; the rezoning is required (20 Nov 2026)
        self.assertIn("FSR 6.91 exceeds", r["finding"])
        self.assertIn("rezoning is required (CD-1)", r["finding"])


if __name__ == "__main__":
    unittest.main()
