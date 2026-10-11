#!/usr/bin/env python3
"""Tests for tidy-check and run-log.  Run: python3 .scripts/tests/test_tidy_scripts.py

Fixture vaults are built in temp dirs.
"""
import importlib.machinery
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
TODAY = "2026-10-07"


def load(name, path):
    spec = importlib.util.spec_from_loader(name, importlib.machinery.SourceFileLoader(name, str(path)))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def note(root, rel, title, body="", created="2026-09-01", aliases=()):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    al = "".join(f'\n  - "{a}"' for a in aliases)
    fm = f'---\ntitle: {title}\n' + (f"aliases:{al}\n" if al else "") + f"created: {created}\n---\n"
    p.write_text(f"{fm}# {title}\n\n{body}\n")


class TidyCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        r = self.root
        note(r, "Areas/health.md", "Health", "[[linked-one]] and [[only-logged]] [[tax-records-2013]] [[tax-records-2014]]")
        note(r, "Resources/linked-one.md", "Linked one")
        note(r, "Resources/lonely.md", "Lonely")
        note(r, "Resources/only-logged.md", "Only logged")
        note(r, "Agents/logs/log-x-2026-10-06.md", "Log x", "[[only-logged]] [[lonely-2]]")
        note(r, "Resources/kettlebell-plan.md", "Kettlebell plan", aliases=["Home kettlebell training"])
        note(r, "Resources/kettlebell-training.md", "Home kettlebell training")
        note(r, "Resources/tax-records-2013.md", "Tax records 2013")
        note(r, "Resources/tax-records-2014.md", "Tax records 2014")
        note(r, "Resources/fresh.md", "Fresh", "See [[linked-one]], [[missing-target]], ![[pic.png]].", created=TODAY)
        self.mod = load("tidy_check", SCRIPTS / "tidy-check")
        self.out = self.mod.report(r, TODAY)

    def tearDown(self):
        self.tmp.cleanup()

    def test_orphans(self):
        self.assertIn("- [[lonely]]\n", self.out)
        self.assertNotIn("[[only-logged]]", self.out.split("## Duplicate")[0])  # linked from Health
        self.assertIn("- [[kettlebell-plan]]\n", self.out)
        self.assertIn("- [[fresh]]\n", self.out)
        self.assertNotIn("[[linked-one]]\n", self.out.split("## Duplicate")[0])

    def test_orphan_linked_only_from_logs(self):
        r = self.root
        (r / "Areas/health.md").unlink()
        out = self.mod.report(r, TODAY)
        self.assertIn("- [[only-logged]] (linked only from run logs)", out)

    def test_duplicates_by_alias_but_not_year_series(self):
        dup = self.out.split("## Duplicate-looking")[1].split("## Created")[0]
        self.assertIn("[[kettlebell-plan]] ~ [[kettlebell-training]]", dup)
        self.assertNotIn("tax-records", dup)

    def test_created_today_and_broken_links(self):
        new = self.out.split("## Created")[1]
        self.assertIn("Tidy Oct 7 imports", new)
        self.assertIn("- [ ] [[fresh]] (Resources; 0 inbound)", new)
        self.assertIn("- [[fresh]]: [[missing-target]]", new)
        self.assertNotIn("pic.png", new)
        self.assertNotIn("linked-one]]: ", new)

    def test_cli_read_only(self):
        before = sorted(p.name for p in self.root.rglob("*"))
        p = subprocess.run([sys.executable, str(SCRIPTS / "tidy-check"), "--root", str(self.root), "--today", TODAY],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        self.assertIn("## Orphans", p.stdout)
        self.assertEqual(before, sorted(p.name for p in self.root.rglob("*")))


class RunLog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "Agents/roles").mkdir(parents=True)
        (self.root / "Agents/roles/role-vault-ops.md").write_text("---\ntitle: Role\n---\n# Role\n")
        self.log = self.root / "Agents/logs/log-vault-ops-2026-10-07.md"

    def tearDown(self):
        self.tmp.cleanup()

    def rl(self, *args):
        p = subprocess.run([sys.executable, str(SCRIPTS / "run-log"), "--root", str(self.root), "--date", TODAY, *args],
                           capture_output=True, text=True)
        return p

    def test_start_creates_per_template(self):
        p = self.rl("--time", "09:05", "start", "vault-ops", "Triage my inbox")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.log.read_text(), (
            '---\ntitle: "Log: vault ops — 2026-10-07"\ntype: log\ndate: 2026-10-07\n---\n'
            "# Log: vault ops — 2026-10-07\n\n"
            "Part of the [[README]]. Run log for [[role-vault-ops]].\n\n"
            "## 09:05 — Triage my inbox\n"))

    def test_second_start_appends_and_keeps_first(self):
        self.rl("--time", "09:05", "start", "vault-ops", "First")
        self.rl("end", "vault-ops", "--read-only")
        first = self.log.read_text()
        self.rl("--time", "14:30", "start", "vault-ops", "Second")
        text = self.log.read_text()
        self.assertTrue(text.startswith(first.rstrip("\n")))
        self.assertTrue(text.endswith("\n\n## 14:30 — Second\n"))
        self.assertEqual(text.count("---\ntitle:"), 1)

    def test_end_checks_with_lint_counts_and_new_findings(self):
        self.rl("--time", "09:05", "start", "vault-ops", "Triage")
        p = self.rl("end", "vault-ops", "--summary", "Triaged.", "--changed", "Moved 3.")
        self.assertEqual(p.returncode, 0, p.stderr)
        tail = self.log.read_text().split("## 09:05 — Triage\n")[1]
        self.assertTrue(tail.startswith("\n### Summary\nTriaged.\n\n### Changed\n- Moved 3.\n\n### Checks\n- vault-lint: "))
        self.assertRegex(tail, r"before, \d+ errors, \d+ warnings after; 0 new\.\n$")

    def test_end_read_only(self):
        self.rl("start", "vault-ops", "Q")
        self.rl("end", "vault-ops", "--read-only")
        self.assertTrue(self.log.read_text().endswith("### Summary\n\n### Checks\n- read-only; no lint needed.\n"))

    def test_end_refuses_without_open_section(self):
        self.assertNotEqual(self.rl("end", "vault-ops", "--read-only").returncode, 0)
        self.rl("start", "vault-ops", "Q")
        self.rl("end", "vault-ops", "--read-only")
        self.assertNotEqual(self.rl("end", "vault-ops", "--read-only").returncode, 0)

    def test_unknown_role_gets_placeholder(self):
        self.rl("start", "morning-brief", "Brief")
        text = (self.root / "Agents/logs/log-morning-brief-2026-10-07.md").read_text()
        self.assertIn("Run log for (link the role page or job spec).", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
