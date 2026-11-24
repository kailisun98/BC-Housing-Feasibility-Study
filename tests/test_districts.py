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

    def test_rt4_run_raises_one_unverified_item(self):
        # 24 Nov 2026: the RT schedules were read from their PDFs, and the family rule typed from memory is gone (RT-6
        # and the N variants it was left covering are not districts on the City's map). No RT site is unverified now,
        # and a district that does not exist has no schedule.
        self.assertNotIn("coverage.schedule_unverified", open_ids(evaluate(site("RT-4"), OPTION, AS_OF)))
        L = evaluate(site("RT-6"), OPTION, AS_OF)
        self.assertNotIn("coverage.schedule_unverified", open_ids(L))
        self.assertIn("coverage.district_schedule", open_ids(L))

    def test_rm1_and_the_schedules_read_from_pdfs_have_none(self):
        self.assertNotIn("coverage.schedule_unverified", open_ids(evaluate(site("RM-1", 2810.7), OPTION, AS_OF)))
        for d in ("RM-3", "RM-3A", "RM-4", "RM-5B", "R1-1", "C-2", "C-2A", "RR-2B", "RR-3B"):
            self.assertNotIn("coverage.schedule_unverified", open_ids(evaluate(site(d), OPTION, AS_OF)), d)


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


SH6 = {"id": "o", "tenure": "social_housing", "storeys": 6, "height_m": 19.8, "gfa_m2": 3000,
       "units": {"studio": 10, "one_bed": 15, "two_bed": 10, "three_bed_plus": 5}}


def lot(district, area=1200.0, frontage=30.0, **more):
    return {**site(district, area), "frontage_m": frontage, "depth_m": area / frontage, **more}


def status(ledger, rule_id):
    return by_id(ledger, rule_id)["status"]


class SchedulesFromThePdfs(unittest.TestCase):
    """The twelve schedules Kai saved on 17 Nov 2026 (inbox/, October 2026 consolidations; R1-1 June 2026), each read
    from its PDF: the district picks its own rules and no neighbour's, and the figures behave as the clauses say."""
    OWN = {"RM-3": "cov.rm3", "RM-3A": "cov.rm3a", "RM-5": "cov.rm5", "RM-5A": "cov.rm5ac", "RM-5B": "cov.rm5b", "RM-5C": "cov.rm5ac",
           "RM-5D": "cov.rm5d", "R1-1": "cov.r1_1", "C-2": "cov.c2", "C-2A": "cov.c2a", "C-2B": "cov.c2b", "C-2C": "cov.c2c",
           "C-2C1": "cov.c2c1", "RR-1": "cov.rr1", "RR-2A": "cov.rr2a", "RR-2B": "cov.rr2b", "RR-3A": "cov.rr3a", "RR-3B": "cov.rr3bc",
           "RR-3C": "cov.rr3bc"}

    def test_each_district_takes_its_own_rules_read_from_its_pdf(self):
        for d, prefix in self.OWN.items():
            L = evaluate(site(d), SH6, AS_OF)
            tested = {r["rule_id"] for r in L["results"] if r.get("check", "").startswith("district_") and r["status"] != "not_applicable"}
            self.assertIn(f"{prefix}.outright_fsr", tested, d)
            self.assertTrue(all(t.startswith(prefix + ".") or t in ("cov.rm5.outright_height", "cov.rm5.setbacks") for t in tested), (d, tested))
            self.assertNotIn("coverage.district_schedule", open_ids(L), d)
            for r in L["results"]:
                if r["rule_id"] in tested:
                    self.assertIs(r["source"]["verified"], True, r["rule_id"])
                    self.assertTrue(r["source"]["read_from"].startswith("inbox/zoning-by-law-district-schedule-"), r["rule_id"])
                    self.assertRegex(r["source"]["section"], r"s\.\d", r["rule_id"])
        # C-2 never reads C-2A's or C-2B's, nor RR-3A RR-3B's
        L = evaluate(site("C-2"), SH6, AS_OF)
        self.assertEqual(status(L, "cov.c2a.outright_fsr"), "not_applicable")
        self.assertEqual(status(L, "cov.c2b.outright_fsr"), "not_applicable")
        self.assertEqual(status(evaluate(site("RR-3A"), SH6, AS_OF), "cov.rr3bc.outright_fsr"), "not_applicable")

    def test_rm3_and_rm3a(self):
        # RM-3: 1.00 plus formula increases not computed (uncertain, not fail); 36.6 m
        L = evaluate(lot("RM-3"), SH6, AS_OF)
        self.assertEqual(status(L, "cov.rm3.outright_fsr"), "uncertain")
        self.assertIn("increases", by_id(L, "cov.rm3.outright_fsr")["finding"])
        self.assertEqual(status(L, "cov.rm3.outright_height"), "pass")
        # RM-3A: 3.00 for 100% social housing; 19.9 m as the Director's variance
        L = evaluate(lot("RM-3A"), SH6, AS_OF)
        self.assertEqual(status(L, "cov.rm3a.outright_fsr"), "pass")
        self.assertEqual(status(L, "cov.rm3a.outright_height"), "conditional")

    def test_rm5_family(self):
        self.assertEqual(status(evaluate(lot("RM-5"), SH6, AS_OF), "cov.rm5.outright_fsr"), "fail")              # 2.50 over the Director's 1.50
        self.assertEqual(status(evaluate(lot("RM-5B"), SH6, AS_OF), "cov.rm5b.outright_fsr"), "conditional")    # within 2.75 at discretion
        two = dict(SH6, gfa_m2=2400)                                                                             # 2.00
        self.assertEqual(status(evaluate(lot("RM-5A"), two, AS_OF), "cov.rm5ac.outright_fsr"), "conditional")
        narrow = lot("RM-5A", 1200.0, 18.0)                                                                       # 18 m wide: at most 1.50
        r = by_id(evaluate(narrow, two, AS_OF), "cov.rm5ac.outright_fsr")
        self.assertEqual(r["status"], "fail")
        self.assertEqual(status(evaluate(dict(narrow, corner_lot=True), two, AS_OF), "cov.rm5ac.outright_fsr"), "conditional")  # corner of 800 m²: 2.00
        tall = dict(SH6, gfa_m2=8000, height_m=50.0, storeys=15)
        L = evaluate(lot("RM-5D"), tall, AS_OF)                                                                   # 6.67 under 7.00, 50 m under 58.0
        self.assertEqual((status(L, "cov.rm5d.outright_fsr"), status(L, "cov.rm5d.outright_height")), ("pass", "pass"))
        self.assertEqual(status(evaluate(lot("RM-5D"), dict(tall, tenure="secured_market_rental"), AS_OF), "cov.rm5d.outright_fsr"), "fail")

    def test_r1_1_multiplex(self):
        eight = {"id": "o", "tenure": "social_housing", "storeys": 3, "height_m": 10.5, "gfa_m2": 600, "units": {"one_bed": 4, "two_bed": 4}}
        L = evaluate(lot("R1-1", 650.0, 16.0), eight, AS_OF)
        self.assertEqual((status(L, "cov.r1_1.outright_fsr"), status(L, "cov.r1_1.outright_height")), ("pass", "pass"))
        strata = evaluate(lot("R1-1", 650.0, 16.0), dict(eight, tenure="other"), AS_OF)
        self.assertEqual(status(strata, "cov.r1_1.outright_fsr"), "fail")                                       # 8 over the 6 for other tenures
        self.assertIn("s.3.1.1.3", by_id(strata, "cov.r1_1.outright_fsr")["finding"])
        self.assertEqual(status(evaluate(lot("R1-1", 650.0, 16.0), dict(eight, storeys=4), AS_OF), "cov.r1_1.outright_height"), "fail")

    def test_c2_family_takes_the_rental_building_figures(self):
        # the rental figure asks for 0.35 FSR of non-dwelling use at the street (s.3.1.1.1): 420 m² on 1,200 m²
        SH6 = dict(globals()["SH6"], non_residential_gfa_m2=420)
        L = evaluate(lot("C-2"), SH6, AS_OF)
        self.assertEqual(status(L, "cov.c2.outright_fsr"), "pass")
        # without it the base figure stands, and the finding says what the higher one needs (23 Nov 2026)
        bare = by_id(evaluate(lot("C-2A"), dict(globals()["SH6"], gfa_m2=3600), AS_OF), "cov.c2a.outright_fsr")           # 3.00, over the base 2.5
        self.assertNotEqual(bare["status"], "pass")
        self.assertIn("0.35 FSR of non-dwelling use at the street, 420 m² on this lot; this option has 0 m²", bare["finding"])
        self.assertIn("every home secured as rental", by_id(L, "cov.c2.outright_fsr")["finding"])
        self.assertEqual(status(L, "cov.c2.outright_height"), "pass")
        strata = dict(SH6, tenure="other", gfa_m2=2400, height_m=13.0, storeys=4)                                # 2.00: over 0.75, within the Director's 2.50
        self.assertEqual(status(evaluate(lot("C-2"), strata, AS_OF), "cov.c2.outright_fsr"), "conditional")
        self.assertEqual(status(evaluate(lot("C-2B"), strata, AS_OF), "cov.c2b.outright_fsr"), "pass")           # 2.50 outright
        big = dict(SH6, gfa_m2=6100, non_residential_gfa_m2=590)                                                                              # 3.65 on 1,672 m²
        corner = lot("C-2C", 1672.0, 46.0, corner_lot=True)
        self.assertEqual(status(evaluate(corner, big, AS_OF), "cov.c2c.outright_fsr"), "pass")                  # 3.70 on the corner
        self.assertEqual(status(evaluate(dict(corner, corner_lot=False), big, AS_OF), "cov.c2c.outright_fsr"), "fail")
        # C-2A: 23.0 m, 27.5 m in a transit-oriented area
        tall = dict(SH6, height_m=26.0, storeys=8)
        self.assertEqual(status(evaluate(lot("C-2A"), tall, AS_OF), "cov.c2a.outright_height"), "fail")
        self.assertEqual(status(evaluate(lot("C-2A", in_transit_oriented_area=True), tall, AS_OF), "cov.c2a.outright_height"), "pass")

    def test_rr_districts(self):
        # rental only: another tenure fails whatever its size
        r = by_id(evaluate(lot("RR-2A"), dict(SH6, tenure="other", gfa_m2=1000), AS_OF), "cov.rr2a.outright_fsr")
        self.assertEqual(r["status"], "fail")
        self.assertIn("residential rental tenure", r["finding"])
        # RR-1: the largest form the site fits
        four = dict(SH6, gfa_m2=1400, height_m=13.2, storeys=4, units={"one_bed": 6, "two_bed": 6})
        L = evaluate(lot("RR-1", 1000.0, 32.0), four, AS_OF)                                                     # 920 m², 30.1 m: 1.45 and 13.7 m
        self.assertEqual((status(L, "cov.rr1.outright_fsr"), status(L, "cov.rr1.outright_height")), ("pass", "pass"))
        L = evaluate(lot("RR-1", 1000.0, 25.0), four, AS_OF)                                                     # 25 m: the 3-storey row, 1.20
        self.assertEqual((status(L, "cov.rr1.outright_fsr"), status(L, "cov.rr1.outright_height")), ("fail", "fail"))
        tiny = by_id(evaluate(lot("RR-1", 250.0, 9.0), dict(four, gfa_m2=200), AS_OF), "cov.rr1.outright_fsr")
        self.assertEqual(tiny["status"], "uncertain")
        self.assertIn("303 m²", tiny["finding"])
        # RR-2B: 3.00 for social housing on a shallow site of 920 m²; a big corner of 920 to 1,469 m² stays at 2.40
        sh = dict(SH6, gfa_m2=2900)
        self.assertEqual(status(evaluate(lot("RR-2B", 1000.0, 32.0), sh, AS_OF), "cov.rr2b.outright_fsr"), "pass")       # 31.25 m deep
        corner = lot("RR-2B", 1450.0, 41.0, corner_lot=True)                                                    # 35.4 m deep: not shallow
        self.assertEqual(by_id(evaluate(corner, dict(sh, gfa_m2=3400), AS_OF), "cov.rr2b.outright_fsr")["values"]["max_fsr_outright"], 2.4)
        self.assertEqual(status(evaluate(lot("RR-2B"), dict(SH6, height_m=26.0, storeys=8), AS_OF), "cov.rr2b.outright_height"), "pass")  # 27.5 m
        # RR-3A: the Director's 2.50 only on a big corner; under 920 m² no figure applies
        over = dict(SH6, gfa_m2=3600, height_m=15.0, storeys=4)                                                   # 2.40 on 1,500 m²
        self.assertEqual(status(evaluate(lot("RR-3A", 1500.0, 41.0, corner_lot=True), over, AS_OF), "cov.rr3a.outright_fsr"), "pass")
        more = dict(over, gfa_m2=3720)                                                                            # 2.48
        self.assertEqual(status(evaluate(lot("RR-3A", 1500.0, 41.0, corner_lot=True), more, AS_OF), "cov.rr3a.outright_fsr"), "conditional")
        self.assertEqual(status(evaluate(lot("RR-3A", 1500.0, 41.0), more, AS_OF), "cov.rr3a.outright_fsr"), "fail")
        self.assertEqual(status(evaluate(lot("RR-3A", 800.0, 25.0), dict(over, gfa_m2=1500), AS_OF), "cov.rr3a.outright_fsr"), "uncertain")

    def test_the_suggestion_cites_the_district(self):
        s = lot("C-2", 1200.0, 30.0, has_water_and_sewer=True, in_transit_oriented_area=False, existing_trees_on_site=[])
        S = suggest.suggest(s, [], AS_OF, "outright")
        self.assertEqual(S["fields"]["gfa_m2"]["rule_id"], "cov.c2.outright_fsr")
        self.assertEqual(S["fields"]["height_m"]["rule_id"], "cov.c2.outright_height")
        self.assertEqual(S["option"]["gfa_m2"], 4200)                                                            # 3.50 × 1,200 for a rental building
        self.assertEqual(S["option"]["storeys"], 6)
        self.assertEqual(S["fields"]["setbacks_m.rear"]["rule_id"], "cov.c2.setbacks")
        S = suggest.suggest(lot("RR-2B", 1000.0, 32.0, has_water_and_sewer=True, in_transit_oriented_area=False, existing_trees_on_site=[]), [], AS_OF, "outright")
        self.assertEqual(S["fields"]["gfa_m2"]["rule_id"], "cov.rr2b.outright_fsr")
        self.assertEqual(S["option"]["gfa_m2"], 3000)                                                            # 3.00 for social housing


class NotInTheStack(unittest.TestCase):
    def test_an_unlisted_district_reads_not_assessed_with_the_open_item(self):
        L = evaluate(site("I-2"), OPTION, AS_OF)
        out = L["summary"]["answers"]["allowed"]["outright"]
        self.assertEqual(out["verdict"], "not assessed")
        self.assertEqual(out["why"], "the rules have no I-2 schedule")
        item = open_item(L, "coverage.district_schedule")
        self.assertEqual(item["title"], "No I-2 schedule in the rules")
        self.assertEqual(item["status"], "uncertain")
        self.assertTrue(item["action"].startswith("Architect: read the I-2 schedule for its FSR, height and yards, and whether housing is a permitted use"))
        self.assertNotIn("inbox/", item["action"])
        self.assertTrue(all(r["status"] == "not_applicable" for r in L["results"] if r.get("check", "").startswith("district_")))


if __name__ == "__main__":
    unittest.main()
