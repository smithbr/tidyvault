#!/usr/bin/env python3
"""Tests for .scripts/obsidian-plugins: pinned installs checked by sha256, with downloads faked (no network).
Run: python3 -m unittest discover -s .scripts/tests"""
import contextlib
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "obsidian-plugins"

RELEASE = {"main.js": b"console.log('dv')", "manifest.json": b'{"version": "1.0.0"}', "styles.css": b".dv {}"}
LIST = [{"id": "dataview", "repo": "owner/dataview"}, {"id": "loose", "repo": "owner/loose"}]


def sha(b):
    return hashlib.sha256(b).hexdigest()


@unittest.skipUnless(SCRIPT.exists(), "obsidian module is off")
class ObsidianPlugins(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / ".obsidian").mkdir()
        self.want(["dataview"])
        loader = importlib.machinery.SourceFileLoader("obsidian_plugins", str(SCRIPT))
        self.mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("obsidian_plugins", loader))
        loader.exec_module(self.mod)
        self.mod.LOCK = self.root / "obsidian-plugins.lock"
        self.lock({"dataview": {"repo": "owner/dataview", "tag": "1.0.0",
                                "sha256": {n: sha(b) for n, b in RELEASE.items()}}})
        self.served = dict(RELEASE)  # what the fake GitHub release holds
        self.fetched = []
        self.mod.fetch = self.fake_fetch

    def want(self, ids):
        (self.root / ".obsidian/community-plugins.json").write_text(json.dumps(ids))

    def lock(self, data):
        (self.root / "obsidian-plugins.lock").write_text(json.dumps(data))

    def fake_fetch(self, url):
        self.fetched.append(url)
        if url == self.mod.LIST_URL:
            return json.dumps(LIST).encode()
        if url.startswith("https://api.github.com/"):
            return json.dumps({"tag_name": "2.0.0"}).encode()
        name = url.rsplit("/", 1)[1]
        if name not in self.served:
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
        return self.served[name]

    def run_it(self, *args):
        out, err = io.StringIO(), io.StringIO()
        argv, sys.argv = sys.argv, ["obsidian-plugins", "--root", str(self.root), *args]
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = self.mod.main()
        finally:
            sys.argv = argv
        return code, out.getvalue() + err.getvalue()

    def plugin(self, name):
        return self.root / ".obsidian/plugins/dataview" / name

    def test_pinned_install_from_the_pinned_tag(self):
        code, out = self.run_it()
        self.assertEqual(code, 0, out)
        self.assertIn("got        dataview 1.0.0", out)
        self.assertEqual(self.plugin("main.js").read_bytes(), RELEASE["main.js"])
        self.assertTrue(all("/releases/download/1.0.0/" in u for u in self.fetched), self.fetched)

    def test_mismatch_installs_nothing(self):
        self.served["main.js"] = b"console.log('tampered')"
        code, out = self.run_it()
        self.assertEqual(code, 1)
        self.assertIn("MISMATCH   dataview 1.0.0: main.js", out)
        self.assertFalse(self.plugin("main.js").exists())

    def test_missing_or_extra_file_is_a_mismatch(self):
        del self.served["styles.css"]  # the lock pins one
        code, out = self.run_it()
        self.assertEqual(code, 1); self.assertIn("styles.css", out)
        self.assertFalse(self.plugin("manifest.json").exists())

    def test_optional_styles_absent_from_release_and_lock(self):
        del self.served["styles.css"]
        self.lock({"dataview": {"repo": "owner/dataview", "tag": "1.0.0",
                                "sha256": {n: sha(RELEASE[n]) for n in ("main.js", "manifest.json")}}})
        code, out = self.run_it()
        self.assertEqual(code, 0, out)
        self.assertFalse(self.plugin("styles.css").exists())

    def test_installed_is_left_alone_and_update_skips_a_matching_pin(self):
        self.run_it()
        self.fetched.clear()
        self.assertIn("installed  dataview", self.run_it()[1])
        code, out = self.run_it("--update")
        self.assertEqual(code, 0); self.assertIn("pinned     dataview 1.0.0", out)
        self.assertEqual(self.fetched, [])

    def test_update_replaces_a_plugin_off_its_pin(self):
        self.plugin("main.js").parent.mkdir(parents=True)
        self.plugin("main.js").write_bytes(b"old")
        code, out = self.run_it("--update")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.plugin("main.js").read_bytes(), RELEASE["main.js"])

    def test_unpinned_plugin_needs_latest(self):
        self.want(["loose"])
        code, out = self.run_it()
        self.assertEqual(code, 1); self.assertIn("UNPINNED   loose", out)
        self.assertEqual(self.fetched, [])
        code, out = self.run_it("--latest")
        self.assertEqual(code, 0, out)
        self.assertIn("got        loose 2.0.0 (latest, unchecked)", out)

    def test_dry_run_downloads_nothing(self):
        code, out = self.run_it("--dry-run")
        self.assertEqual(code, 0); self.assertIn("would get  dataview 1.0.0", out)
        self.assertEqual(self.fetched, [])
        self.assertFalse(self.plugin("main.js").exists())

    def test_shipped_lock_pins_every_shipped_plugin(self):
        lock = SCRIPT.parent / "obsidian-plugins.lock"
        shipped = HERE.parents[1] / ".obsidian/community-plugins.json"
        if not shipped.exists():
            self.skipTest("no .obsidian/ beside .scripts/")
        pins = json.loads(lock.read_text())
        for plugin in json.loads(shipped.read_text()):
            self.assertIn(plugin, pins)
            self.assertTrue({"main.js", "manifest.json"} <= set(pins[plugin]["sha256"]), plugin)


if __name__ == "__main__":
    unittest.main()
