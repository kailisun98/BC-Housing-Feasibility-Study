"""The page as native ES modules (16 Nov 2026, app.js split up): main.js reaches every module file, every relative
import resolves and names something its source exports, the editors and the paper memo are only ever loaded with
import(), and the static build's import map names each module with a hash of its own contents."""

import re
import unittest

from ffm import pages
from ffm.ui import server

UI = server.STATIC_DIR
LAZY = {"paper.js", "editors/blocks.js", "editors/boundary.js"}
NAMED_IMPORT = re.compile(r"^import\s*\{([^}]*)\}\s*from\s*[\"'](\.{1,2}/[^\"']+)[\"']", re.M)
STATIC_IMPORT = re.compile(r"^import\s[^;]*?from\s*[\"'](\.{1,2}/[^\"']+)[\"']|^import\s*[\"'](\.{1,2}/[^\"']+)[\"']", re.M)
EXPORT = re.compile(r"^export\s+(?:async\s+)?(?:function\*?|const|let|class)\s+([A-Za-z_$][\w$]*)", re.M)


def _resolve(rel: str, spec: str) -> str:
    import posixpath
    return posixpath.normpath(posixpath.join(posixpath.dirname(rel), spec))


class TestModules(unittest.TestCase):
    def setUp(self):
        self.modules = pages.module_graph(UI)
        self.src = {m: (UI / m).read_text(encoding="utf-8") for m in self.modules}

    def test_every_module_file_is_reached_from_main(self):
        on_disk = {p.name for p in UI.glob("*.js")} - {"site.js"}   # site.js is the site pages' classic script
        for d in server.MODULE_DIRS:
            on_disk |= {f"{d}/{p.name}" for p in (UI / d).glob("*.js")}
        self.assertEqual(self.modules[0], "main.js")
        self.assertEqual(on_disk, set(self.modules))
        self.assertFalse((UI / "app.js").exists(), "app.js was split into modules; it should not come back")

    def test_named_imports_are_exported_by_their_source(self):
        exports = {m: set(EXPORT.findall(s)) for m, s in self.src.items()}
        for m, s in self.src.items():
            for names, spec in NAMED_IMPORT.findall(s):
                target = _resolve(m, spec)
                self.assertIn(target, exports, f"{m} imports {spec}, which is not a module")
                for name in filter(None, (n.strip() for n in names.split(","))):
                    self.assertIn(name, exports[target], f"{m} imports {name} from {target}, which does not export it")

    def test_the_editors_and_the_paper_load_on_demand(self):
        for m, s in self.src.items():
            for a, b in STATIC_IMPORT.findall(s):
                self.assertNotIn(_resolve(m, a or b), LAZY, f"{m} imports a lazy module statically")
        self.assertTrue(LAZY <= set(self.modules), "the lazy modules are reached through import()")

    def test_import_map_names_every_module_by_its_own_hash(self):
        imap = pages.import_map(UI, self.modules)["imports"]
        self.assertEqual(set(imap), {f"./{m}" for m in self.modules})
        for key, url in imap.items():
            self.assertRegex(url, r"^\./[\w/-]+\.js\?v=[0-9a-f]{10}$")
            self.assertTrue(url.startswith(key + "?v="))

    def test_page_loads_main_as_a_module(self):
        html = (UI / "index.html").read_text(encoding="utf-8")
        self.assertIn('<script type="module" src="main.js"></script>', html)
        self.assertNotIn("app.js", html)
        self.assertLess(html.index("<!-- static-config -->"), html.index('src="main.js"'),
                        "the import map goes in at the static-config marker, before the module script")

    def test_server_serves_the_module_folders_and_nothing_above(self):
        for ok in ("main.js", "core/util.js", "memo/answers.js", "figures/fig3d.js", "editors/blocks.js", "brand/mark.svg"):
            self.assertTrue(server.STATIC_PATH.match(ok), ok)
        for bad in ("../ffm/engine.py", "core/../server.py", "rules/a.json", "core/x/util.js", "server.py"):
            self.assertFalse(server.STATIC_PATH.match(bad), bad)


if __name__ == "__main__":
    unittest.main()
