#!/usr/bin/env python3
"""Tests for .scripts/pii-merge-queue against a fake `op` (1Password CLI) on PATH.
Run: python3 -m unittest discover -s .scripts/tests. No real password manager is touched."""
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = next(p for p in (HERE.parent / "pii-merge-queue", HERE.parent / "pii-merge-queue.jinja") if p.exists())
FAKE_OP = r'''#!/usr/bin/env bash
# fake op: `op document get ITEM --out-file F [--force]` and `op document edit ITEM FILE`, over one file
set -e; store="${FAKE_OP_STORE:?}"
case "$1 $2" in
  "document get") out=""; while [ $# -gt 0 ]; do [ "$1" = --out-file ] && out="$2"; shift; done; cp "$store" "$out" ;;
  "document edit") cp "$4" "$store" ;;
  *) echo "fake op: unsupported $*" >&2; exit 1 ;;
esac
'''
REGISTER = "# PII register\n\n## Robin Vale\n\n| Key | Category | Value | Where used | Notes |\n|---|---|---|---|---|\n| `robin-vale.id.passport` | id | P123 | travel | |\n"
QUEUE = ("- Robin Vale | `robin-vale.id.ssn` | id | 000-00-0000 | tax | |\n"
         "- Priya Nair | `priya-nair.contact.phone` | contact | 555-0100 | | |\n"
         "- Robin Vale | `robin-vale.id.passport` | id | P123 | travel | |\n")  # already in the register: skipped


class PiiMergeQueue(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root / "bin").mkdir(); op = root / "bin" / "op"; op.write_text(FAKE_OP); op.chmod(op.stat().st_mode | stat.S_IEXEC)
        (root / "vault" / "Resources").mkdir(parents=True); (root / "vault" / "Resources" / "pii-register.md").write_text("# stub\n")
        self.store = root / "register.md"; self.store.write_text(REGISTER)
        self.queue = root / "queue.md"; self.queue.write_text(QUEUE)
        self.env = dict(os.environ, PATH=f"{root / 'bin'}:{os.environ['PATH']}", FAKE_OP_STORE=str(self.store),
                        PII_QUEUE=str(self.queue), PII_REGISTER_ITEM="test register", VAULT_ROOT=str(root / "vault"))

    def run_it(self, *args, answers=""):
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=answers, capture_output=True, text=True, env=self.env)

    def test_dry_run_changes_nothing(self):
        p = self.run_it("--dry-run")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("To add: 2", p.stdout); self.assertIn("skipped (already there): robin-vale.id.passport", p.stdout)
        self.assertNotIn("000-00-0000", p.stdout, "a value leaked into the output")
        self.assertEqual(self.store.read_text(), REGISTER); self.assertEqual(self.queue.read_text(), QUEUE)

    def test_merge_uploads_checks_and_empties_queue(self):
        p = self.run_it(answers="y\ny\n")
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        reg = self.store.read_text()
        self.assertIn("`robin-vale.id.ssn`", reg); self.assertIn("## Priya Nair", reg); self.assertIn("`priya-nair.contact.phone`", reg)
        self.assertEqual(reg.count("`robin-vale.id.passport`"), 1, "no duplicate row for a key already there")
        self.assertIn("all 2 new keys", p.stdout); self.assertNotIn("000-00-0000", p.stdout)
        self.assertEqual(self.queue.read_text(), "", "queue emptied after the check")

    def test_declining_upload_changes_nothing(self):
        p = self.run_it(answers="n\n")
        self.assertEqual(p.returncode, 0, p.stderr); self.assertIn("Nothing uploaded", p.stdout)
        self.assertEqual(self.store.read_text(), REGISTER); self.assertEqual(self.queue.read_text(), QUEUE)

    def test_failed_check_keeps_queue(self):
        # an upload that doesn't stick (the fake drops every edit): the check fails and the queue is left alone
        op = Path(self.tmp.name) / "bin" / "op"
        op.write_text(FAKE_OP.replace('"document edit") cp "$4" "$store"', '"document edit") true'))
        p = self.run_it(answers="y\ny\n")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("Check FAILED", p.stdout)
        self.assertEqual(self.queue.read_text(), QUEUE, "queue kept when keys didn't land")

    def test_without_op_it_refuses(self):
        env = dict(self.env, PATH=str(Path(self.tmp.name) / "nowhere"))
        p = subprocess.run([sys.executable, str(SCRIPT), "--dry-run"], capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 2); self.assertIn("op", p.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=1)
