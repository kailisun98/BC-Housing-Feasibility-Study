"""Evaluation cases from the ARCH 540 brief: typical, boundary, out-of-scope, repeated runs,
plus the rule-version switch and the version stamp. Run: python -m unittest -v"""

import copy
import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from ffm import massing
from ffm.engine import diff, evaluate, load_json
from ffm.rules_loader import RULES_DIR, load_rules, stamp

ROOT = Path(__file__).resolve().parent.parent
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
OPTION = load_json(ROOT / "options" / "998-e-19th-ave-as-approved.json")
AS_OF = date(2026, 10, 23)


def by_id(ledger, rule_id):
    return next(r for r in ledger["results"] if r["rule_id"] == rule_id)


class TypicalCase(unittest.TestCase):
    """998 E 19th Ave as approved: the numbers the City's referral report states."""

    def setUp(self):
        self.L = evaluate(SITE, OPTION, AS_OF)

    def test_fsr_and_height_exceed_outright_and_route_to_rezoning(self):
        f = by_id(self.L, "cov.rm1.outright_fsr")
        self.assertEqual(f["status"], "uncertain")
        self.assertAlmostEqual(f["values"]["fsr"], 2.953, places=3)
        h = by_id(self.L, "cov.rm1.outright_height")
        self.assertEqual(h["status"], "uncertain")
        self.assertEqual(self.L["summary"]["answers"]["allowed"]["outright"]["verdict"], "no")

    def test_family_units_pass_at_36_percent(self):
        r = by_id(self.L, "cov.family_units")
        self.assertEqual(r["status"], "pass")
        self.assertEqual(r["values"]["two_plus_bed_units"], 38)
        self.assertAlmostEqual(r["values"]["two_plus_bed_share"], 38 / 105, places=4)
        self.assertEqual(r["version_effective_from"], "1992-01-01")

    def test_tree_shortfall_three_and_cash_in_lieu(self):
        r = by_id(self.L, "cov.trees.replacement")
        self.assertEqual(r["status"], "conditional")
        self.assertEqual(r["values"]["schedule_c_required"], 20)
        self.assertEqual(r["values"]["trees_after"], 17)
        self.assertEqual(r["values"]["shortfall"], 3)
        self.assertEqual(r["values"]["cash_in_lieu_cad"], 3000)
        self.assertEqual(r["values"]["protection_barriers"][0]["barrier_m"], 2.4)

    def test_social_housing_definition_passes(self):
        self.assertEqual(by_id(self.L, "cov.social_housing_definition")["status"], "pass")

    def test_irp_conditional_above_benchmark(self):
        r = by_id(self.L, "cov.irp.social_housing_rezoning")
        self.assertEqual(r["status"], "conditional")
        self.assertIn("22.3 m is above the staff benchmark", r["finding"])

    def test_funders_uncertain_not_fail(self):
        self.assertEqual(by_id(self.L, "bch.chf.eligibility")["status"], "uncertain")
        self.assertEqual(by_id(self.L, "bc.bcbuilds.eligibility")["status"], "uncertain")
        self.assertEqual(self.L["summary"]["answers"]["funded"]["verdict"], "not yet confirmed")

    def test_every_result_has_a_source(self):
        for r in self.L["results"]:
            self.assertTrue(r["source"].get("url") or r["source"].get("title"), r["rule_id"])


class BoundaryCases(unittest.TestCase):
    def small_lot(self, area, bus=None, district="R1-1", toa=False):
        site = {"id": "t", "zoning_district": district, "site_area_m2": area, "frontage_m": 10, "depth_m": area / 10,
                "has_water_and_sewer": True, "frequent_bus_stop_within_400m": bus, "in_transit_oriented_area": toa}
        opt = {"id": "o", "tenure": "secured_market_rental", "storeys": 3, "height_m": 10, "gfa_m2": area * 0.7,
               "units": {"studio": 0, "one_bed": 1, "two_bed": 1, "three_bed_plus": 1}}
        return evaluate(site, opt, AS_OF)

    def test_ssmuh_280_m2_is_three_units_and_281_is_four(self):
        self.assertEqual(by_id(self.small_lot(280, bus=False), "bc.ssmuh.minimum_units")["values"]["minimum_units"], 3)
        self.assertEqual(by_id(self.small_lot(281, bus=False), "bc.ssmuh.minimum_units")["values"]["minimum_units"], 4)

    def test_ssmuh_bus_stop_within_400m_gives_six(self):
        r = by_id(self.small_lot(300, bus=True), "bc.ssmuh.minimum_units")
        self.assertEqual(r["values"]["minimum_units"], 6)
        self.assertEqual(r["status"], "info")

    def test_ssmuh_unknown_bus_distance_is_uncertain(self):
        self.assertEqual(by_id(self.small_lot(300, bus=None), "bc.ssmuh.minimum_units")["status"], "uncertain")

    def test_family_share_exactly_35_percent_passes_and_below_fails(self):
        base = {"id": "o", "tenure": "social_housing", "storeys": 4, "height_m": 13, "gfa_m2": 2000}
        site = {"id": "s", "zoning_district": "RM-4", "site_area_m2": 1000, "frontage_m": 30, "depth_m": 33.3}
        ok = evaluate(site, {**base, "units": {"studio": 0, "one_bed": 13, "two_bed": 7, "three_bed_plus": 0}}, AS_OF)
        self.assertEqual(by_id(ok, "cov.family_units")["status"], "pass")  # 7/20 = 35.0%
        bad = evaluate(site, {**base, "units": {"studio": 0, "one_bed": 14, "two_bed": 7, "three_bed_plus": 0}}, AS_OF)
        self.assertEqual(by_id(bad, "cov.family_units")["status"], "fail")  # 7/21 = 33.3%

    def test_tree_schedule_bands(self):
        from ffm.checks import _schedule_c_required
        p = next(r for r in load_rules() if r.id == "cov.trees.replacement").version_on(AS_OF).params
        self.assertEqual(_schedule_c_required(365, p), 2)
        self.assertEqual(_schedule_c_required(366, p), 3)
        self.assertEqual(_schedule_c_required(2810.7, p), 20)
        self.assertEqual(_schedule_c_required(3300, p), 31)


class OutOfScopeCases(unittest.TestCase):
    def test_ssmuh_not_applicable_to_rm1(self):
        r = by_id(evaluate(SITE, OPTION, AS_OF), "bc.ssmuh.minimum_units")
        self.assertEqual(r["status"], "not_applicable")
        self.assertIn("RM-1", r["finding"])

    def test_ssmuh_not_applicable_inside_toa(self):
        site = {"id": "t", "zoning_district": "R1-1", "site_area_m2": 300, "frontage_m": 10, "depth_m": 30,
                "has_water_and_sewer": True, "in_transit_oriented_area": True, "toa_tier": "2"}
        opt = {"id": "o", "tenure": "secured_market_rental", "storeys": 3, "height_m": 10, "gfa_m2": 200,
               "units": {"two_bed": 2}}
        L = evaluate(site, opt, AS_OF)
        self.assertEqual(by_id(L, "bc.ssmuh.minimum_units")["status"], "not_applicable")
        self.assertEqual(by_id(L, "bc.toa.minimum_density")["values"]["minimum_allowable_storeys"], 12)

    def test_irp_not_applicable_outside_vision_areas(self):
        site = {**SITE, "in_former_community_vision_area": False}
        self.assertEqual(by_id(evaluate(site, OPTION, AS_OF), "cov.irp.social_housing_rezoning")["status"], "not_applicable")

    def test_missing_inputs_become_uncertain_not_errors(self):
        opt = {k: v for k, v in OPTION.items() if k not in ("units", "height_m")}
        L = evaluate(SITE, opt, AS_OF)
        self.assertEqual(by_id(L, "cov.family_units")["status"], "uncertain")
        self.assertEqual(by_id(L, "cov.rm1.outright_height")["status"], "uncertain")


class RepeatedRuns(unittest.TestCase):
    def test_same_inputs_same_ledger_and_stamp(self):
        a = json.dumps(evaluate(SITE, OPTION, AS_OF), sort_keys=True)
        b = json.dumps(evaluate(copy.deepcopy(SITE), copy.deepcopy(OPTION), AS_OF), sort_keys=True)
        self.assertEqual(a, b)

    def test_massing_is_reproducible_and_matches_the_ledger(self):
        L = evaluate(SITE, OPTION, AS_OF)
        m1, m2 = massing.build(SITE, OPTION, L), massing.build(SITE, OPTION, L)
        self.assertEqual(json.dumps(m1, sort_keys=True), json.dumps(m2, sort_keys=True))
        prop = next(x for x in m1["masses"] if x["name"] == "proposed")
        self.assertAlmostEqual(prop["gfa_m2"], OPTION["gfa_m2"], places=0)
        self.assertAlmostEqual(prop["plate_area_m2"], OPTION["gfa_m2"] / OPTION["storeys"], places=0)
        out = next(x for x in m1["masses"] if x["name"] == "outright")
        self.assertAlmostEqual(out["fsr"], 1.2, places=2)
        self.assertLessEqual(out["height_m"], 10.7)


class RuleVersionSwitch(unittest.TestCase):
    def test_family_rule_version_changes_on_27_oct_2026(self):
        before = by_id(evaluate(SITE, OPTION, date(2026, 10, 26)), "cov.family_units")
        after = by_id(evaluate(SITE, OPTION, date(2026, 10, 27)), "cov.family_units")
        self.assertEqual(before["version_effective_from"], "1992-01-01")
        self.assertEqual(after["version_effective_from"], "2026-10-27")
        self.assertIsNone(before["values"]["min_three_plus_bed_share"])
        self.assertEqual(after["values"]["min_three_plus_bed_share"], 0.05)

    def test_option_with_four_percent_three_beds_passes_before_and_fails_after(self):
        opt = {**OPTION, "units": {"studio": 30, "one_bed": 37, "two_bed": 34, "three_bed_plus": 4}}  # 38/105 two+, 4/105 = 3.8% three+
        self.assertEqual(by_id(evaluate(SITE, opt, date(2026, 10, 26)), "cov.family_units")["status"], "pass")
        self.assertEqual(by_id(evaluate(SITE, opt, date(2026, 10, 27)), "cov.family_units")["status"], "fail")

    def test_diff_reports_the_version_change_and_stamp_change(self):
        a = evaluate(SITE, OPTION, date(2026, 10, 26))
        b = evaluate(SITE, OPTION, date(2026, 10, 27))
        d = diff(a, b)
        self.assertNotEqual(d["previous_stamp"], d["current_stamp"])
        self.assertFalse(d["rules_changed"])
        self.assertEqual([c["rule_id"] for c in d["changes"]], ["cov.family_units"])


class VersionStamp(unittest.TestCase):
    def test_stamp_changes_when_a_rule_parameter_changes(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copytree(RULES_DIR, tmp / "rules")
            s1 = stamp(load_rules(tmp / "rules"), AS_OF, tmp / "rules")
            f = tmp / "rules" / "a_zoning_district.json"
            data = json.loads(f.read_text())
            for r in data["rules"]:
                if r["id"] == "cov.rm1.outright_fsr":
                    r["versions"][0]["params"]["max_fsr"] = 1.45
            f.write_text(json.dumps(data))
            s2 = stamp(load_rules(tmp / "rules"), AS_OF, tmp / "rules")
            self.assertNotEqual(s1["stamp"], s2["stamp"])
            self.assertNotEqual(s1["rules_hash"], s2["rules_hash"])
            self.assertEqual(s1["rules_files"]["b_provincial.json"], s2["rules_files"]["b_provincial.json"])
        finally:
            shutil.rmtree(tmp)

    def test_stamp_is_stable_across_calls(self):
        rules = load_rules()
        self.assertEqual(stamp(rules, AS_OF)["stamp"], stamp(rules, AS_OF)["stamp"])


if __name__ == "__main__":
    unittest.main()
