"""Piece 2 of the plan (25 Nov 2026): the site before an option. What the lot takes when the site is read (the plate,
the outright building and its homes, the provincial small-scale minimum), the uses each district's table allows, the
district read from the parcel, a far "nearest" parcel refused, and the transit tier and a lane suggested from the
City's data, never applied."""

import json
import unittest
from datetime import date
from pathlib import Path

from ffm import lookup
from ffm.checks import district_outright_use, uses_for
from ffm.engine import evaluate, load_json
from ffm.rules_loader import RULES_DIR, load_rules
from ffm.suggest import lot_reading, read_site, ssmuh_homes

ROOT = Path(__file__).resolve().parent.parent
ON = date(2026, 11, 25)
SITE = load_json(ROOT / "sites" / "998-e-19th-ave.json")
RULES = load_rules(RULES_DIR)
PARCEL_998 = [[-123.08489687064771, 49.25321534055158], [-123.0838586301182, 49.25320060903445],
              [-123.08384890432116, 49.25353522932474], [-123.08488645058618, 49.25354970057842], [-123.08489687064771, 49.25321534055158]]


def bare(**more):
    s = {k: v for k, v in SITE.items() if k not in ("parcel", "osm", "front_face", "front_street", "lookup", "boundary_m")}
    s.update(more)
    return s


def rule(rid):
    return next(r for r in RULES if r.id == rid)


class TheUseTables(unittest.TestCase):
    def test_every_schedule_read_from_a_pdf_has_its_use_table(self):
        uses = [r for r in RULES if r.check == "district_outright_use"]
        self.assertEqual(len(uses), 32)
        covered = {d for r in uses for d in r.applies_to_districts}
        for r in RULES:
            v = r.version_on(ON)
            if r.check == "district_outright_fsr" and v and "bylaws.vancouver.ca/zoning/" in str(v.source.get("url")):
                for d in r.applies_to_districts:
                    self.assertIn(d, covered, r.id)
        for r in uses:
            v = r.version_on(ON)
            self.assertTrue(v.source["verified"])
            self.assertIn("pages", v.source["read_from"])
            for u, x in v.params["uses"].items():
                self.assertIn(x["approval"], ("outright", "conditional"), (r.id, u))
                self.assertTrue(x["as"].startswith(u), (r.id, u))

    def test_what_the_tables_say(self):
        p = lambda rid: rule(rid).version_on(ON).params["uses"]
        self.assertEqual(p("cov.r1_1.uses")["Multiple Dwelling"]["as"], "Multiple Dwelling, containing no more than 8 dwelling units")
        self.assertNotIn("Multiple Dwelling", p("cov.rt4.uses"))          # RT-4 lists no apartment building for a new building
        self.assertNotIn("Multiple Dwelling", p("cov.c2a.uses"))          # only one "existing as of May 19, 2026"
        self.assertEqual(p("cov.c2a.uses")["Mixed-Use Residential Building"]["approval"], "conditional")
        self.assertEqual(p("cov.rm10.uses")["Apartment"]["approval"], "conditional")
        self.assertEqual(p("cov.rt4a.uses")["Duplex"]["approval"], "outright")     # "only in the RT-4A district"
        self.assertEqual(p("cov.rt4.uses")["Duplex"]["approval"], "conditional")
        self.assertEqual(p("cov.c2.uses")["Health Care Office"]["approval"], "outright")
        self.assertEqual(set(p("cov.m1.uses")), {"Social Service Centre"})

    def test_the_check_reads_the_option_against_the_table(self):
        uses = lambda rid: rule(rid).version_on(ON).params
        apt = {"tenure": "social_housing"}
        r = district_outright_use({}, apt, uses("cov.rm4.uses"))
        self.assertEqual(r["status"], "conditional")
        self.assertTrue(r["values"]["conditional_use"])
        self.assertEqual(district_outright_use({}, apt, uses("cov.rt4.uses"))["status"], "uncertain")      # only a mixed-use building
        self.assertEqual(district_outright_use({}, dict(apt, non_residential_gfa_m2=200), uses("cov.c2a.uses"))["status"], "conditional")
        self.assertEqual(district_outright_use({}, apt, uses("cov.rr1.uses"))["status"], "fail")            # rental townhouses only
        shelter = district_outright_use({}, {"housing_type": "shelter"}, uses("cov.rm4.uses"))
        self.assertEqual(shelter["status"], "uncertain")
        self.assertIn("Group Residence", shelter["finding"])
        # a rezoning sets the uses
        self.assertEqual(district_outright_use({}, dict(apt, rezoning_path="CD-1"), uses("cov.rt4.uses"))["status"], "info")
        # a ground-oriented building of three homes may be a triplex; of eight, not
        self.assertIn("Triplex", uses_for({"building_type": "ground_oriented", "units": {"studio": 3}})[1])
        self.assertNotIn("Triplex", uses_for({"building_type": "ground_oriented", "units": {"studio": 8}})[1])

    def test_a_conditional_use_is_the_directors_discretion_in_answer_1(self):
        site = bare(zoning_district="RM-4")
        o = {"id": "o", "tenure": "social_housing", "storeys": 3, "height_m": 9.9, "gfa_m2": 3000, "units": {"studio": 30}}
        L = evaluate(site, o, ON)
        a = L["summary"]["answers"]["allowed"]
        r = next(x for x in L["results"] if x["rule_id"] == "cov.rm4.uses")
        self.assertEqual(r["status"], "conditional")
        self.assertEqual(a["routes"]["outright"]["verdict"], "no")
        self.assertEqual(a["routes"]["discretion"]["verdict"], "possible")
        self.assertIn("cov.rm4.uses", a["routes"]["discretion"]["rules"])


class WhatTheLotTakes(unittest.TestCase):
    def test_the_reading_carries_the_lot(self):
        R = read_site(bare(), ON, rules=RULES)
        lot = R["lot"]
        self.assertEqual(lot["yield"]["storeys"], 3)          # RM-1 outright: 10.7 m, three storeys of 3.3 m
        self.assertEqual(lot["yield"]["fsr"], 1.2)
        self.assertTrue(lot["yield"]["homes"])
        self.assertTrue(lot["yield"]["outright"])
        self.assertTrue(lot["plate"]["area_m2"])
        self.assertFalse(lot["ssmuh"]["applies"])              # RM-1 is not a restricted zone
        self.assertIsNone(lot["uses"])                         # no RM-1 schedule PDF read, so no use table

    def test_a_small_lot_beside_the_provincial_minimum(self):
        site = bare(zoning_district="RT-4", site_area_m2=560.0, frontage_m=15.2, depth_m=36.8)
        lot = lot_reading(site, ON, RULES)
        self.assertEqual(lot["plate"]["yards_from"], "cov.rt4.setbacks")
        self.assertEqual(lot["yield"]["fsr"], 0.6)
        self.assertEqual(lot["ssmuh"], {"applies": True, "homes": 4, "rule_id": "bc.ssmuh.minimum_units",
                                        "why": "at least 4 homes on a lot of 560 m²; 6 if a prescribed frequent bus stop is within 400 m (not answered)"})
        kinds = {k["kind"]: k["status"] for k in lot["uses"]["kinds"]}
        self.assertEqual(kinds, {"An apartment building": "uncertain", "Ground-oriented homes": "uncertain", "A shelter": "uncertain", "A clinic": "fail"})

    def test_the_minimum_reads_its_exemptions(self):
        self.assertEqual(ssmuh_homes(bare(zoning_district="RT-4", site_area_m2=250.0), RULES, ON)["homes"], 3)
        self.assertFalse(ssmuh_homes(bare(zoning_district="RT-4", site_area_m2=5000.0), RULES, ON)["applies"])
        self.assertFalse(ssmuh_homes(bare(zoning_district="RT-4", site_area_m2=560.0, in_transit_oriented_area=True), RULES, ON)["applies"])
        self.assertEqual(ssmuh_homes(bare(zoning_district="RT-4", site_area_m2=560.0, frequent_bus_stop_within_400m=True), RULES, ON)["homes"], 6)


class TheLookup(unittest.TestCase):
    def parcel(self, civic="998", street="E 19TH AV"):
        return [{"civic_number": civic, "streetname": street, "site_id": "x", "geom": {"geometry": {"type": "Polygon", "coordinates": [PARCEL_998]}}}]

    def test_the_district_is_read_at_the_parcels_centre(self):
        c = lookup.parcel_metrics(PARCEL_998)["center"]
        res = lookup.assemble("998 E 19th Ave", c["lat"], c["lon"], "998 E 19TH AV (City of Vancouver property address)", [{"zoning_district": "CD-1", "cd_1_number": 852}],
                              self.parcel(), extra={"zoning_centre": [{"zoning_district": "RM-1"}]})
        s = res["site"]
        self.assertEqual(s["zoning_district"], "RM-1")
        self.assertEqual(s["lookup"]["district_at_point"], "CD-1")
        self.assertEqual(s["lookup"]["zoning_at"], "the parcel's centre")
        self.assertIn("the parcel itself is in RM-1, which is the district used", s["notes"])

    def test_a_far_nearest_is_refused(self):
        self.assertIn("more than a block", lookup.refuse_nearest(3680, 117, "E HASTINGS", "E HASTINGS ST", None))
        self.assertIn("not on the street typed", lookup.refuse_nearest(5050, 3250, "JOYCE", "KINGSWAY", None))
        self.assertIn("m from the City's nearest number", lookup.refuse_nearest(1065, 1055, "HARWOOD", "HARWOOD ST", 72))
        self.assertIsNone(lookup.refuse_nearest(1065, 1055, "HARWOOD", "HARWOOD ST", 4))
        self.assertIsNone(lookup.refuse_nearest(998, 998, "E 19TH", "E 19TH AV", None))
        c = lookup.parcel_metrics(PARCEL_998)["center"]
        res = lookup.assemble("3680 E 19th Ave", c["lat"], c["lon"], "a point (Nominatim)", [{"zoning_district": "RM-1"}], self.parcel())
        self.assertIn("more than a block", res["refused"])
        self.assertEqual(res["site"]["lookup"]["refused"], res["refused"])

    def test_the_nearest_on_the_same_side(self):
        rows = [{"civic_number": "1066", "std_street": "HARWOOD ST", "geo_point_2d": {"lat": 49.28, "lon": -123.13}},
                {"civic_number": "1055", "std_street": "HARWOOD ST", "geo_point_2d": {"lat": 49.281, "lon": -123.131}}]
        self.assertEqual(lookup.nearest_from_rows(rows, "1065 Harwood St")["civic_number"], "1066")
        self.assertEqual(lookup.nearest_from_rows(rows, "1065 Harwood St", same_side=True)["civic_number"], "1055")

    def test_a_transit_tier_from_the_nearest_station(self):
        c = lookup.parcel_metrics(PARCEL_998)["center"]
        near = [{"station": "Test", "geo_point_2d": {"lat": c["lat"] + 0.0027, "lon": c["lon"]}}]       # about 300 m north of the centre
        t = lookup.toa_from_stations(near, PARCEL_998, (c["lat"], c["lon"]))
        self.assertEqual(t["tier"], "2")
        self.assertLess(t["distance_m"], 300)                     # to the lot's nearest edge, not its centre
        far = [{"station": "Far", "geo_point_2d": {"lat": c["lat"] + 0.02, "lon": c["lon"]}}]
        self.assertIsNone(lookup.toa_from_stations(far, PARCEL_998, (c["lat"], c["lon"]))["tier"])
        res = lookup.assemble("998 E 19th Ave", c["lat"], c["lon"], "998 E 19TH AV (City of Vancouver property address)", [{"zoning_district": "RM-1"}],
                              self.parcel(), extra={"stations": near})
        sug = res["site"]["suggested"]
        self.assertEqual(sug["toa_tier"]["value"], 2)
        self.assertIs(sug["in_transit_oriented_area"]["value"], True)
        self.assertIsNone(res["site"]["in_transit_oriented_area"])        # offered, never applied
        # past 800 m nothing is suggested (a bus exchange's tiers are not in the station data); the distance is kept
        res = lookup.assemble("998 E 19th Ave", c["lat"], c["lon"], "998 E 19TH AV (City of Vancouver property address)", [{"zoning_district": "RM-1"}],
                              self.parcel(), extra={"stations": far})
        self.assertNotIn("suggested", res["site"])
        self.assertEqual(res["site"]["lookup"]["nearest_station"]["station"], "Far")

    def test_the_bands_are_the_rules(self):
        where = rule("bc.toa.minimum_density").version_on(ON).params["tiers_where"]
        for limit, tier in lookup.TOA_SKYTRAIN_BANDS:
            self.assertIn(lookup.TOA_BAND_WORDS[tier], where[tier])
            self.assertIn(f"{limit} m", where[tier])

    def test_a_lane_behind_the_lot(self):
        c = lookup.parcel_metrics(PARCEL_998)["center"]
        dlat = 1 / 111200
        street = {"hblock": "900 E 19TH AV", "streetuse": "Residential", "geom": {"geometry": {"type": "LineString", "coordinates": [[c["lon"] - 0.002, c["lat"] - 30 * dlat], [c["lon"] + 0.002, c["lat"] - 30 * dlat]]}}}
        lane = {"std_street": "E 19TH AV", "geom": {"geometry": {"type": "LineString", "coordinates": [[c["lon"] - 0.002, c["lat"] + 22 * dlat], [c["lon"] + 0.002, c["lat"] + 22 * dlat]]}}}
        els = lookup.city_elements([street], [], [], [lane])
        found = lookup.lane_behind(els, (c["lat"], c["lon"]), "E 19th Ave", 37.2)
        self.assertAlmostEqual(found["to_centre_line_m"], 22 - 37.2 / 2, delta=0.3)
        # a lane on the street's side is not behind
        front_lane = {"geom": {"geometry": {"type": "LineString", "coordinates": [[c["lon"] - 0.002, c["lat"] - 22 * dlat], [c["lon"] + 0.002, c["lat"] - 22 * dlat]]}}}
        self.assertIsNone(lookup.lane_behind(lookup.city_elements([street], [], [], [front_lane]), (c["lat"], c["lon"]), "E 19th Ave", 37.2))
        res = lookup.assemble("998 E 19th Ave", c["lat"], c["lon"], "998 E 19TH AV (City of Vancouver property address)", [{"zoning_district": "RM-1"}],
                              self.parcel(), els, 120, "city", "city")
        s = res["site"]["suggested"]["context.lane_behind"]
        self.assertIs(s["value"], True)
        self.assertIn("context.lane_to_centre_line_m", s["also"])


class ThePage(unittest.TestCase):
    UI = ROOT / "ffm" / "ui"

    def test_the_page_offers_and_shows(self):
        rs = (self.UI / "route-stage.js").read_text(encoding="utf-8")
        self.assertIn("function siteOffer(k)", rs)
        self.assertIn("function lotTakes(lot)", rs)
        self.assertIn('id="guide-lookup-nearest"', rs)
        api = (self.UI / "core" / "api.js").read_text(encoding="utf-8")
        for ds in ("rapid-transit-stations", 'within("lanes")', "extra.zoning_centre", "extra.nearest_rows"):
            self.assertIn(ds, api)


if __name__ == "__main__":
    unittest.main()
