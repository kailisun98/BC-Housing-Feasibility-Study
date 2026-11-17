"""District schedules in layer A (16 Nov 2026): the engine picks the schedule from the site's zoning district, the
RT-3 figures are the ones read from the schedule PDF, figures typed from recollection raise one open item, and a CD-1
site still reads not assessed with its by-law number carried from the lookup."""

import unittest
from datetime import date

from ffm import lookup
from ffm.engine import evaluate
from ffm.rules_loader import load_rules

AS_OF = date(2026, 11, 16)


def rule(rule_id):
    return next(r for r in load_rules() if r.id == rule_id)


def by_id(ledger, rule_id):
    return next(r for r in ledger["results"] if r["rule_id"] == rule_id)


def open_ids(ledger):
    return [u["rule_id"] for u in ledger["summary"]["answers"]["unsure"]]


def site(district, area=1000.0):
    return {"id": "t", "address": "a lot, Vancouver, BC", "municipality": "City of Vancouver", "zoning_district": district,
            "site_area_m2": area, "frontage_m": 30, "depth_m": area / 30, "keep_existing_buildings": False}


OPTION = {"id": "o", "tenure": "social_housing", "storeys": 3, "height_m": 10.0, "gfa_m2": 500,
          "units": {"studio": 0, "one_bed": 3, "two_bed": 3, "three_bed_plus": 1}}


class Matching(unittest.TestCase):
    def test_rm4_rule_applies_to_rm4n_not_rm1(self):
        r = rule("cov.rm4.outright_fsr")
        self.assertTrue(r.applies_to("RM-4"))
        self.assertTrue(r.applies_to("RM-4N"))
        self.assertFalse(r.applies_to("RM-1"))

    def test_rm4_site_under_its_fsr_passes(self):
        L = evaluate(site("RM-4"), OPTION, AS_OF)   # 500 / 1000 = 0.50
        r = by_id(L, "cov.rm4.outright_fsr")
        self.assertEqual(r["check"], "district_outright_fsr")
        self.assertEqual(r["status"], "pass")
        self.assertEqual(by_id(L, "cov.rm1.outright_fsr")["status"], "not_applicable")


class RT3FromThePdf(unittest.TestCase):
    """inbox/zoning-by-law-district-schedule-rt-3.pdf (June 2026): s.3.1.1.1 "The maximum floor space ratio is 0.60",
    the Director may increase it to 0.75; s.3.1.1.2 1.00 for affordable multiple dwelling; s.3.1.2.3 maximum building
    height "10.7 m and 3 storeys"; s.3.1.2.5 maximum front yard 3.7 m; s.3.1.2.6 side yard 1.5 m on a site over
    15.0 m wide; s.3.1.2.7 minimum rear yard 20.0 m; s.3.1.2.8 site coverage 45%."""

    def test_rt3_figures(self):
        fsr = rule("cov.rt3.outright_fsr").version_on(AS_OF)
        self.assertEqual(fsr.params["max_fsr"], 0.60)
        self.assertEqual(fsr.params["max_fsr_conditional"], 0.75)
        self.assertEqual(fsr.params["max_fsr_affordable_multiple_dwelling"], 1.00)
        h = rule("cov.rt3.outright_height").version_on(AS_OF)
        self.assertEqual(h.params["max_height_m"], 10.7)
        self.assertEqual(h.params["max_storeys"], 3)
        sb = rule("cov.rt3.setbacks").version_on(AS_OF)
        self.assertEqual(sb.params["min_rear_yard_m"], 20.0)
        self.assertEqual(sb.params["min_side_yard_m"], 1.5)
        self.assertEqual(sb.params["max_front_yard_m"], 3.7)
        self.assertNotIn("min_front_yard_m", sb.params)   # the average of the neighbours: no fixed figure
        self.assertEqual(sb.params["max_site_coverage"], 0.45)
        for v in (fsr, h, sb):
            self.assertIs(v.source["verified"], True)
            self.assertIn("rt-3.pdf", v.source["url"])

    def test_rt3_run_has_no_unverified_item(self):
        L = evaluate(site("RT-3"), OPTION, AS_OF)
        self.assertNotIn("coverage.schedule_unverified", open_ids(L))
        self.assertNotIn("coverage.district_schedule", open_ids(L))


class Unverified(unittest.TestCase):
    def test_every_unverified_version_says_so(self):
        for r in load_rules():
            if r.layer != "A":
                continue
            for v in r.versions:
                if v.source.get("verified") is False:
                    self.assertIn("Entered from recollection of the schedule on 16 Nov 2026", v.source["verify"], r.id)
                    self.assertIn(v.source["url"], v.source["verify"], r.id)
                    self.assertTrue(v.source["url"].startswith("https://bylaws.vancouver.ca/zoning/zoning-by-law-district-schedule-"), r.id)

    def test_rm4_run_raises_one_unverified_item(self):
        L = evaluate(site("RM-4"), OPTION, AS_OF)
        items = [u for u in L["summary"]["answers"]["unsure"] if u["rule_id"] == "coverage.schedule_unverified"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "District schedule figures entered unverified (RM-4)")
        self.assertIn("cov.rm4.outright_fsr", items[0]["finding"])
        self.assertIn("cov.rm4.outright_height", items[0]["finding"])
        self.assertEqual(items[0]["status"], "uncertain")
        # the wording names the schedule the figures should be read from (17 Nov 2026); the shape is what is tested
        self.assertTrue(items[0]["action"].startswith("Architect: open "))
        self.assertIn("FSR, height and yards", items[0]["action"])

    def test_rm1_run_has_none(self):
        L = evaluate(site("RM-1", 2810.7), OPTION, AS_OF)
        self.assertNotIn("coverage.schedule_unverified", open_ids(L))


class CD1(unittest.TestCase):
    def test_cd1_site_reads_not_assessed(self):
        s = {**site("CD-1 (324)"), "cd1_bylaw_number": 324}
        L = evaluate(s, OPTION, AS_OF)
        out = L["summary"]["answers"]["allowed"]["outright"]
        self.assertEqual(out["verdict"], "not assessed")
        item = next(u for u in L["summary"]["answers"]["unsure"] if u["rule_id"] == "coverage.district_schedule")
        # the finding names the CD-1 and says its limits are in its own by-law (the wording moved on 17 Nov 2026)
        self.assertIn("CD-1 (324)", item["finding"])
        self.assertIn("by-law", item["finding"])
        self.assertNotIn("coverage.schedule_unverified", open_ids(L))

    def test_assemble_sets_the_bylaw_number(self):
        zoning = [{"zoning_district": "CD-1 (324)", "zoning_category": "CD", "cd_1_number": "324"}]
        res = lookup.assemble("1 Example St, Vancouver, BC", 49.27, -123.10, "1 Example St, Vancouver", zoning, [])
        s = res["site"]
        self.assertEqual(s["zoning_district"], "CD-1 (324)")
        self.assertEqual(s["cd1_bylaw_number"], 324)
        self.assertIn("its limits are in CD-1 by-law No. 324", s["notes"])

    def test_assemble_without_a_cd1_number_adds_no_key(self):
        res = lookup.assemble("1 Example St, Vancouver, BC", 49.27, -123.10, "1 Example St, Vancouver",
                              [{"zoning_district": "RM-4", "cd_1_number": None}], [])
        self.assertNotIn("cd1_bylaw_number", res["site"])


if __name__ == "__main__":
    unittest.main()
