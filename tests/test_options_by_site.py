"""Options belong to sites (17 Nov 2026): /api/options?site=<id> lists that site's options and no other site's, so
choosing 375 Glen Drive no longer offers 998 E 19th Ave's options as "(other site)…"."""

import unittest

from ffm.ui import server


class TestOptionSite(unittest.TestCase):
    SITES = ["998-e-19th", "998-e-19th-ave", "375-glen-drive"]

    def test_the_file_naming_its_site_wins(self):
        self.assertEqual(server.option_site({"site": "375-glen-drive"}, "a-renamed-option", self.SITES), "375-glen-drive")

    def test_the_longest_site_id_that_begins_the_option_id(self):
        self.assertEqual(server.option_site({}, "998-e-19th-ave-as-approved", self.SITES), "998-e-19th-ave")
        self.assertEqual(server.option_site({}, "998-e-19th-tower", self.SITES), "998-e-19th")

    def test_a_site_id_only_claims_a_whole_word(self):
        self.assertIsNone(server.option_site({}, "375-glen-driveway", self.SITES))
        self.assertIsNone(server.option_site({}, "an-option", self.SITES))


class TestListOptions(unittest.TestCase):
    def test_each_site_lists_only_its_own_options(self):
        sites = [s["id"] for s in server.list_sites()]
        everything = server.list_options(None)
        for sid in sites:
            mine = server.list_options(sid)
            self.assertTrue(all(o["site"] == sid and o["for_site"] for o in mine), sid)
            self.assertEqual({o["id"] for o in mine}, {o["id"] for o in everything if o["site"] == sid}, sid)

    def test_every_shipped_option_has_a_site(self):
        sites = {s["id"] for s in server.list_sites()}
        for o in server.list_options(None):
            self.assertIn(o["site"], sites, f"{o['file']} matches no site: name its site or begin its id with one")


if __name__ == "__main__":
    unittest.main()
