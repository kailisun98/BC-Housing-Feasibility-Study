"""District schedules in layer A (16 Nov 2026, extended 17 Nov 2026): the engine picks the schedule from the site's
zoning district, and a CD-1 site's rules from its own by-law, matched on its CD-1 number (`cd1_bylaw_number`, else the
number in "CD-1 (819)") and never another's. RT-3 and RM-4 are read from the schedule PDFs; figures not read from the
schedule itself raise one open item; a district or a CD-1 by-law not in the stack reads "not assessed" and says which."""

import unittest
from datetime import date

from ffm import lookup, suggest
from ffm.engine import evaluate
from ffm.rules_loader import cd1_number, district_of, load_rules

AS_OF = date(2026, 11, 17)


def rule(rule_id):
    return next(r for r in load_rules() if r.id == rule_id)


def by_id(ledger, rule_id):
    return next(r for r in ledger["results"] if r["rule_id"] == rule_id)


def open_ids(ledger):
    return [u["rule_id"] for u in ledger["summary"]["answers"]["unsure"]]


def open_item(ledger, rule_id):
    return next(u for u in ledger["summary"]["answers"]["unsure"] if u["rule_id"] == rule_id)


def site(district, area=1000.0, **more):
    return {"id": "t", "address": "a lot, Vancouver, BC", "municipality": "City of Vancouver", "zoning_district": district,
            "site_area_m2": area, "frontage_m": 30, "depth_m": area / 30, "keep_existing_buildings": False, **more}


OPTION = {"id": "o", "tenure": "social_housing", "storeys": 3, "height_m": 10.0, "gfa_m2": 500,
          "units": {"studio": 0, "one_bed": 3, "two_bed": 3, "three_bed_plus": 1}}


class Matching(unittest.TestCase):
    def test_rm4_rule_applies_to_rm4_not_rm4n_or_rm1(self):
        r = rule("cov.rm4.outright_fsr")
        self.assertTrue(r.applies_to("RM-4"))
        self.assertFalse(r.applies_to("RM-4N"))     # not in the October 2026 RM-4 schedule: left out until its own is read
        self.assertFalse(r.applies_to("RM-1"))

    def test_rm4_site_under_its_fsr_passes(self):
        L = evaluate(site("RM-4"), OPTION, AS_OF)   # 500 / 1000 = 0.50
        r = by_id(L, "cov.rm4.outright_fsr")
        self.assertEqual(r["check"], "district_outright_fsr")
        self.assertEqual(r["status"], "pass")
        self.assertEqual(by_id(L, "cov.rm1.outright_fsr")["status"], "not_applicable")

    def test_cd1_number_from_the_field_or_the_district(self):
        self.assertEqual(cd1_number("CD-1 (819)"), "819")
        self.assertEqual(cd1_number("CD-1", 324), "324")
        self.assertEqual(cd1_number("CD-1", "324.0"), "324")
        self.assertEqual(cd1_number("CD-1 (819)", 324), "324")       # the lookup's number wins over the label
        self.assertIsNone(cd1_number("CD-1"))
        self.assertIsNone(cd1_number("RM-4", 324))                   # a number on a site that is not a CD-1 is ignored
        self.assertIsNone(cd1_number("CD-10 (5)"))
        self.assertEqual(district_of({"zoning_district": "CD-1", "cd1_bylaw_number": 324}), "CD-1 (324)")
        self.assertEqual(district_of({"zoning_district": "RM-4"}), "RM-4")


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


class RM4FromThePdf(unittest.TestCase):
    """inbox/zoning-by-law-district-schedule-rm-4.pdf (October 2026), multiple dwelling (s.3.1): s.3.1.1.2 "The maximum
    floor space ratio is 1.45"; s.3.1.1.3 "3.00 if 100% of the residential floor area is developed as social housing";
    s.3.1.2.3 maximum building height 10.7 m; s.3.1.2.4 to 3.1.2.6 yards 6.1 / 2.1 / 10.7 m; s.3.1.2.11 the Director may
    vary the height to at most 19.9 m and the yards for 100% social housing."""

    def test_rm4_figures(self):
        fsr = rule("cov.rm4.outright_fsr").version_on(AS_OF)
        self.assertEqual(fsr.params["max_fsr"], 1.45)
        self.assertEqual(fsr.params["max_fsr_social_housing"], 3.0)
        h = rule("cov.rm4.outright_height").version_on(AS_OF)
        self.assertEqual(h.params["max_height_m"], 10.7)
        self.assertEqual(h.params["max_height_m_social_housing_variance"], 19.9)
        sb = rule("cov.rm4.setbacks").version_on(AS_OF)
        self.assertEqual((sb.params["min_front_yard_m"], sb.params["min_side_yard_m"], sb.params["min_rear_yard_m"]), (6.1, 2.1, 10.7))
        self.assertEqual(sb.params["affordable_variance"]["clause"], "s.3.1.2.11")
        for v in (fsr, h, sb):
            self.assertIs(v.source["verified"], True)
            self.assertIn("rm-4.pdf", v.source["url"])
            self.assertIn("inbox/zoning-by-law-district-schedule-rm-4.pdf", v.source["read_from"])
            self.assertEqual(v.effective_from.isoformat(), "2026-10-01")

    def test_social_housing_takes_the_higher_fsr_and_the_height_is_a_variance(self):
        six = dict(OPTION, storeys=6, height_m=19.8, gfa_m2=2800, setbacks_m={"front": 6.1, "rear": 10.7, "side": 2.1})
        L = evaluate(site("RM-4"), six, AS_OF)                      # 2,800 / 1,000 = 2.80
        self.assertEqual(by_id(L, "cov.rm4.outright_fsr")["status"], "pass")
        self.assertIn("100% social housing (s.3.1.1.3", by_id(L, "cov.rm4.outright_fsr")["finding"])
        h = by_id(L, "cov.rm4.outright_height")
        self.assertEqual(h["status"], "conditional")
        self.assertIn("s.3.1.2.11", h["finding"])
        self.assertEqual(L["summary"]["answers"]["allowed"]["outright"]["verdict"], "yes, with conditions")
        self.assertNotIn("coverage.schedule_unverified", open_ids(L))
        rental = dict(six, tenure="secured_market_rental")
        L2 = evaluate(site("RM-4"), rental, AS_OF)
        self.assertEqual(by_id(L2, "cov.rm4.outright_fsr")["status"], "fail")        # 2.80 over 1.45
        self.assertEqual(by_id(L2, "cov.rm4.outright_height")["status"], "fail")     # no variance outside social housing

    def test_the_suggestion_cites_rm4(self):
        S = suggest.suggest(site("RM-4", 1200.0, has_water_and_sewer=True, in_transit_oriented_area=False, existing_trees_on_site=[]),
                            [], AS_OF, "outright")
        self.assertEqual(S["option"]["storeys"], 6)
        self.assertEqual(S["option"]["gfa_m2"], 3600)                                 # 3.00 × 1,200
        self.assertEqual(S["fields"]["gfa_m2"]["rule_id"], "cov.rm4.outright_fsr")
        self.assertEqual(S["fields"]["height_m"]["rule_id"], "cov.rm4.outright_height")
        self.assertIn("variance", S["fields"]["height_m"]["note"])
        self.assertEqual(S["fields"]["setbacks_m.rear"]["rule_id"], "cov.rm4.setbacks")


class Unverified(unittest.TestCase):
    def test_every_unverified_version_says_so_and_names_the_document(self):
        for r in load_rules():
            if r.layer != "A":
                continue
            for v in r.versions:
                if v.source.get("verified") is False:
                    self.assertTrue(v.source.get("verify"), r.id)
                    if r.applies_to_cd1:
                        # a CD-1 rule read from elsewhere names its enacted by-law to confirm against
                        self.assertIn("not from the enacted by-law", v.source["verify"], r.id)
                        self.assertIn(f"https://cd1-bylaws.vancouver.ca/cd-1({r.applies_to_cd1[0]}).PDF", v.source["verify"], r.id)
                    else:
                        self.assertIn("Entered from recollection of the schedule on 16 Nov 2026", v.source["verify"], r.id)
                        self.assertIn(v.source["url"], v.source["verify"], r.id)
                        self.assertTrue(v.source["url"].startswith("https://bylaws.vancouver.ca/zoning/zoning-by-law-district-schedule-"), r.id)

    def test_rm3_run_raises_one_unverified_item(self):
        L = evaluate(site("RM-3"), OPTION, AS_OF)
        items = [u for u in L["summary"]["answers"]["unsure"] if u["rule_id"] == "coverage.schedule_unverified"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "District schedule figures entered unverified (RM-3)")
        self.assertIn("cov.rm3.outright_fsr", items[0]["finding"])
        self.assertIn("cov.rm3.outright_height", items[0]["finding"])
        self.assertIn("entered from recollection of the RM-3 schedule", items[0]["finding"])
        self.assertEqual(items[0]["status"], "uncertain")
        self.assertTrue(items[0]["action"].startswith("Architect: open the RM-3 schedule"))

    def test_rm1_and_rm4_runs_have_none(self):
        self.assertNotIn("coverage.schedule_unverified", open_ids(evaluate(site("RM-1", 2810.7), OPTION, AS_OF)))
        self.assertNotIn("coverage.schedule_unverified", open_ids(evaluate(site("RM-4"), OPTION, AS_OF)))


class CD1(unittest.TestCase):
    """Each CD-1 is its own by-law: its rules are keyed by the CD-1 number and match that site and no other."""
    TOWER = {"id": "o", "tenure": "social_housing", "storeys": 15, "height_m": 51.0, "gfa_m2": 14700,
             "units": {"studio": 40, "one_bed": 60, "two_bed": 50, "three_bed_plus": 13}}

    def test_a_cd1_site_matches_its_own_bylaw(self):
        L = evaluate(site("CD-1 (819)", 1942.0, cd1_bylaw_number=819), self.TOWER, AS_OF)
        fsr = by_id(L, "cov.cd1_819.outright_fsr")
        self.assertEqual(fsr["status"], "pass")
        self.assertEqual(fsr["values"]["site_area_m2"], 2134.4)         # s.5.1: the FSR is on the site before dedications
        self.assertAlmostEqual(fsr["values"]["fsr"], 6.887, places=3)   # 14,700 / 2,134.4 (the report's 14,729 m² is 6.9008, over 6.90)
        self.assertEqual(by_id(L, "cov.cd1_819.outright_height")["status"], "pass")
        out = L["summary"]["answers"]["allowed"]["outright"]
        self.assertNotEqual(out["verdict"], "not assessed")
        self.assertNotIn("coverage.district_schedule", open_ids(L))
        # read from the referral report's draft provisions, not the enacted by-law: one open item says so
        item = open_item(L, "coverage.schedule_unverified")
        self.assertEqual(item["title"], "District schedule figures entered unverified (CD-1 (819))")
        self.assertIn("draft by-law provisions in the referral report", item["finding"])
        self.assertIn("CD-1 (819)'s by-law", item["action"])

    def test_the_number_alone_or_the_label_alone_selects_it(self):
        for s in (site("CD-1", 1942.0, cd1_bylaw_number="819"), site("CD-1 (819)", 1942.0)):
            self.assertEqual(by_id(evaluate(s, self.TOWER, AS_OF), "cov.cd1_819.outright_fsr")["status"], "pass")

    def test_another_cd1_does_not_take_its_rules(self):
        L = evaluate(site("CD-1 (9999)", 1000.0, cd1_bylaw_number=9999), self.TOWER, AS_OF)
        r = by_id(L, "cov.cd1_819.outright_fsr")
        self.assertEqual(r["status"], "not_applicable")
        self.assertEqual(r["finding"], "Written for CD-1 (819); this site is zoned CD-1 (9999).")
        out = L["summary"]["answers"]["allowed"]["outright"]
        self.assertEqual(out["verdict"], "not assessed")
        self.assertEqual(out["why"], "CD-1 (9999)'s by-law is not in the rules")
        item = open_item(L, "coverage.district_schedule")
        self.assertEqual(item["title"], "CD-1 (9999) is not in the rules")
        self.assertIn("holds no rules from that by-law", item["finding"])
        self.assertIn("cd1-bylaws.vancouver.ca", item["action"])
        self.assertNotIn("coverage.schedule_unverified", open_ids(L))

    def test_a_cd1_with_no_number_matches_no_bylaw(self):
        L = evaluate(site("CD-1", 1942.0), self.TOWER, AS_OF)
        self.assertEqual(by_id(L, "cov.cd1_819.outright_fsr")["status"], "not_applicable")
        self.assertEqual(L["summary"]["answers"]["allowed"]["outright"]["verdict"], "not assessed")
        self.assertEqual(open_item(L, "coverage.district_schedule")["title"], "A CD-1 site with no CD-1 number")

    def test_a_cd1_rule_never_reaches_a_district_site(self):
        L = evaluate(site("RM-4", cd1_bylaw_number=819), OPTION, AS_OF)
        self.assertEqual(by_id(L, "cov.cd1_819.outright_fsr")["status"], "not_applicable")
        self.assertEqual(by_id(L, "cov.rm4.outright_fsr")["status"], "pass")

    def test_the_suggestion_cites_the_cd1_bylaw(self):
        s = site("CD-1 (819)", 1942.0, cd1_bylaw_number=819, has_water_and_sewer=True, in_transit_oriented_area=False, existing_trees_on_site=[])
        S = suggest.suggest(s, [], AS_OF, "outright")
        self.assertEqual(S["fields"]["gfa_m2"]["rule_id"], "cov.cd1_819.outright_fsr")
        self.assertEqual(S["option"]["gfa_m2"], round(6.9 * 2134.4))
        self.assertIn("the by-law fixes for its FSR", S["fields"]["gfa_m2"]["note"])
        self.assertEqual(S["fields"]["height_m"]["rule_id"], "cov.cd1_819.outright_height")
        self.assertTrue(next(c for c in S["candidates"] if c["id"] == "outright")["available"])
        self.assertNotIn("zoning_district", {u["key"] for u in S["unsure"]})
        other = suggest.suggest(dict(s, zoning_district="CD-1 (9999)", cd1_bylaw_number=9999), [], AS_OF, "outright")
        self.assertIsNone(other["fields"]["gfa_m2"]["rule_id"])
        self.assertIn("CD-1 (9999)'s by-law is not in the rules", next(u for u in other["unsure"] if u["key"] == "zoning_district")["why"])

    def test_expo_takes_cd1_324_by_its_sub_area(self):
        """CD-1 (324), By-law No. 7248 consolidated to No. 14009 (inbox/cd-1(324).PDF): s.6.2 Table 1a caps the residential
        floor area at 19,300 m² in sub-area A and 23,600 m² in sub-area B; s.7.1 the height at 91 m."""
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        expo = json.loads((root / "sites" / "1010-expo-blvd.json").read_text(encoding="utf-8"))
        permitted = json.loads((root / "options" / "1010-expo-blvd-as-permitted.json").read_text(encoding="utf-8"))
        self.assertEqual((expo["cd1_bylaw_number"], expo["cd1_sub_area"]), (324, "B"))
        L = evaluate(expo, permitted, AS_OF)
        fa = by_id(L, "cov.cd1_324.floor_area")
        self.assertEqual(fa["status"], "pass")                             # 23,215 m² under sub-area B's 23,600 m²
        self.assertEqual(fa["values"]["max_floor_area_m2"], 23600)
        self.assertEqual(fa["finding"], "Residential floor area 23,215 m² is within sub-area B's 23,600 m², the most the by-law allows there (FSR 5.94 on 3,908.0 m²).")
        self.assertEqual(by_id(L, "cov.cd1_324.outright_height")["status"], "pass")   # 88.4 m under 91 m
        self.assertEqual(by_id(L, "cov.cd1_819.outright_fsr")["status"], "not_applicable")
        self.assertNotIn("coverage.district_schedule", open_ids(L))
        self.assertNotIn("coverage.schedule_unverified", open_ids(L))      # read from the by-law itself
        for rid in ("cov.cd1_324.floor_area", "cov.cd1_324.outright_height"):
            src = rule(rid).version_on(AS_OF).source
            self.assertIs(src["verified"], True)
            self.assertIn("No. 14009", src["title"])
        # another CD-1's site never takes CD-1 (324)'s rules
        L819 = evaluate(site("CD-1 (819)", 1942.0, cd1_bylaw_number=819), self.TOWER, AS_OF)
        self.assertEqual(by_id(L819, "cov.cd1_324.floor_area")["status"], "not_applicable")

    def test_cd1_324_over_its_floor_area_or_without_a_sub_area(self):
        s = site("CD-1 (324)", 2711.6, cd1_bylaw_number=324, cd1_sub_area="A")
        big = dict(self.TOWER, gfa_m2=23215, height_m=88.4, storeys=29)
        r = by_id(evaluate(s, big, AS_OF), "cov.cd1_324.floor_area")
        self.assertEqual(r["status"], "fail")                                # sub-area A's 19,300 m²
        no_sub = dict(s)
        no_sub.pop("cd1_sub_area")
        r2 = by_id(evaluate(no_sub, big, AS_OF), "cov.cd1_324.floor_area")
        self.assertEqual(r2["status"], "uncertain")
        self.assertIn("sub-area", r2["finding"])

    def test_the_suggestion_takes_sub_area_b(self):
        import json
        from pathlib import Path
        expo = json.loads((Path(__file__).resolve().parent.parent / "sites" / "1010-expo-blvd.json").read_text(encoding="utf-8"))
        S = suggest.suggest(expo, [], AS_OF, "outright")
        self.assertEqual(S["fields"]["gfa_m2"]["rule_id"], "cov.cd1_324.floor_area")
        self.assertEqual(S["fields"]["height_m"]["rule_id"], "cov.cd1_324.outright_height")
        self.assertLessEqual(S["option"]["gfa_m2"], 23600)
        self.assertIn("sub-area B", S["fields"]["gfa_m2"]["note"])
        self.assertTrue(next(c for c in S["candidates"] if c["id"] == "outright")["available"])

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


class NotInTheStack(unittest.TestCase):
    def test_an_unlisted_district_reads_not_assessed_with_the_open_item(self):
        L = evaluate(site("I-2"), OPTION, AS_OF)
        out = L["summary"]["answers"]["allowed"]["outright"]
        self.assertEqual(out["verdict"], "not assessed")
        self.assertEqual(out["why"], "the rules have no I-2 schedule")
        item = open_item(L, "coverage.district_schedule")
        self.assertEqual(item["title"], "No I-2 schedule in the rules")
        self.assertEqual(item["status"], "uncertain")
        self.assertTrue(item["action"].startswith("Architect: save the I-2 schedule into inbox/"))
        self.assertTrue(all(r["status"] == "not_applicable" for r in L["results"] if r.get("check", "").startswith("district_")))


if __name__ == "__main__":
    unittest.main()
