#!/usr/bin/env python3
"""Tests for .scripts/pii-queue. Run: python3 -m unittest discover -s .scripts/tests"""
import importlib.machinery
import importlib.util
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "pii-queue"
MERGE = next(p for p in (HERE.parent / "pii-merge-queue", HERE.parent / "pii-merge-queue.jinja") if p.exists())


def load(path, name):
    os.environ.setdefault("VAULT_ROOT", tempfile.gettempdir())  # its root check runs at import
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(mod)
    return mod


class PiiQueue(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "_files").mkdir()
        self.queue = self.root / "_files" / "_private" / "pii-register-queue.md"

    def run_it(self, *args, value=""):
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), *args],
                              input=value, capture_output=True, text=True)

    def test_add_writes_a_private_row_and_never_prints_the_value(self):
        p = self.run_it("add", "theo-vale.id.ssn", "--where", "Resources/kitchen-quote.md", "--person", "Theo Vale",
                        value="000-00-0000\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("queued: theo-vale.id.ssn (1 rows waiting)", p.stdout)
        self.assertNotIn("000-00-0000", p.stdout + p.stderr)
        self.assertIn("- Theo Vale | `theo-vale.id.ssn` | id | 000-00-0000 | Resources/kitchen-quote.md |  |\n",
                      self.queue.read_text())
        self.assertEqual(stat.S_IMODE(self.queue.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.queue.parent.stat().st_mode), 0o700)

    def test_one_key_one_value(self):
        self.run_it("add", "robin-vale.contact.phone", "--where", "x", value="555-0100")
        same = self.run_it("add", "robin-vale.contact.phone", "--where", "x", value="555-0100")
        self.assertEqual(same.returncode, 0); self.assertIn("already queued", same.stdout)
        other = self.run_it("add", "robin-vale.contact.phone", "--where", "x", value="555-0199")
        self.assertEqual(other.returncode, 1); self.assertNotIn("555-01", other.stdout + other.stderr)
        self.assertEqual(self.run_it("count").stdout.strip(), "1")

    def test_pipes_and_newlines_stay_in_one_cell(self):
        self.run_it("add", "priya-nair.legal.statement", "--where", "x", value="line one | two\nline three")
        self.run_it("add", "priya-nair.dob.birthday", "--where", "x", value="1990-01-01")
        rows = load(MERGE, "pii_merge_queue").parse_queue(self.queue.read_text())
        self.assertEqual([r[0] for r in rows], ["priya-nair.legal.statement", "priya-nair.dob.birthday"])
        self.assertEqual(rows[0][2][2], "line one &#124; two<br>line three")
        self.assertEqual(self.run_it("keys").stdout.split(), ["priya-nair.legal.statement", "priya-nair.dob.birthday"])

    def test_backticked_key_in_another_cell_cant_take_over(self):
        self.run_it("add", "theo-vale.id.ssn", "--where", "`robin-vale.id.ssn`", "--person", "`robin-vale.id.ssn`",
                    value="`robin-vale.id.ssn`")
        rows = load(MERGE, "pii_merge_queue").parse_queue(self.queue.read_text())
        self.assertEqual([r[0] for r in rows], ["theo-vale.id.ssn"])
        self.assertEqual(self.run_it("keys").stdout.split(), ["theo-vale.id.ssn"])

    def test_bad_key_and_empty_value_refused(self):
        self.assertEqual(self.run_it("add", "theo-vale.secret.x", "--where", "x", value="v").returncode, 2)
        self.assertEqual(self.run_it("add", "theo-vale.id.ssn", "--where", "x", value="  \n").returncode, 2)
        self.assertFalse(self.queue.exists())

    def test_no_store_is_refused(self):
        (self.root / "_files").rmdir()
        p = self.run_it("add", "theo-vale.id.ssn", "--where", "x", value="v")
        self.assertEqual(p.returncode, 2); self.assertIn("isn't attached", p.stderr)


if __name__ == "__main__":
    unittest.main()
