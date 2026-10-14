"""Tests for .scripts/vault-setup with a fake `op` and a fake HOME (1Password, restic and git are never touched).
Run: python3 -m unittest discover -s .scripts/tests."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "vault-setup"

FAKE_OP = r'''#!/usr/bin/env bash
# Fake 1Password CLI. `whoami` succeeds; `item get TITLE --format json` answers only for FAKE_OP_ITEM
# with a Password item JSON; `document create FILE ...` copies FILE to FAKE_OP_STORE. Logs every call.
set -euo pipefail
printf '%s\n' "$*" >> "${FAKE_OP_LOG}"
case "$1 ${2:-}" in
  "whoami ") ;;
  "item get") [[ "$3" == "${FAKE_OP_ITEM:-}" ]] || exit 1
    printf '{"title":"%s","category":"PASSWORD","fields":[{"id":"password","purpose":"PASSWORD","value":"hunter2-test"}]}\n' "$3" ;;
  "document create") cp "$3" "${FAKE_OP_STORE}" ;;
  *) echo "fake op: unknown $*" >&2; exit 1 ;;
esac
'''


class VaultSetup(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name, "vault"); self.root.mkdir()
        self.home = Path(self._tmp.name, "home"); self.home.mkdir()
        self.bin = Path(self._tmp.name, "bin"); self.bin.mkdir()
        op = self.bin / "op"; op.write_text(FAKE_OP); op.chmod(0o755)
        restic = self.bin / "restic"; restic.write_text("#!/usr/bin/env bash\nexit 0\n"); restic.chmod(0o755)
        self.log = Path(self._tmp.name, "op.log")
        self.store = Path(self._tmp.name, "register-in-1password.md")
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}", HOME=str(self.home),
                        VAULT_ROOT=str(self.root), FAKE_OP_LOG=str(self.log), FAKE_OP_STORE=str(self.store))
        self.env.pop("VAULT_RESTIC_CONFIG", None)

    def tearDown(self):
        self._tmp.cleanup()

    def config(self, *modules):
        mods = "".join(f"  - {m}\n" for m in modules)
        (self.root / ".tidyvault.yml").write_text(
            f"modules:\n{mods}owner: Robin\nowner_full: \"Robin Vale\"\nowner_slug: robin-vale\nvault: t\n")

    def run_setup(self, *args, answers=""):
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=answers, capture_output=True, text=True,
                              env=self.env)

    def test_check_reports_every_step_left(self):
        self.config("pii", "backup")
        p = self.run_setup("--check")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("todo      git history", p.stdout)
        self.assertIn("ok        1Password CLI signed in", p.stdout)
        self.assertIn('todo      PII register document in 1Password ("t PII register")', p.stdout)
        self.assertIn("todo      Backblaze B2 settings in t.env", p.stdout)
        self.assertIn("Unset: VAULT_REPOSITORY, B2_ACCOUNT_ID, B2_ACCOUNT_KEY", p.stdout)
        self.assertIn("todo      repository password", p.stdout)
        self.assertIn("todo      restic repositories and nightly jobs", p.stdout)
        self.assertNotIn("Do it now?", p.stdout)  # --check never prompts
        self.assertNotIn("hunter2", p.stdout + p.stderr)

    def test_creates_the_register_document(self):
        self.config("pii")
        p = self.run_setup(answers="n\ny\n")  # git: no; register: yes
        self.assertIn('ok        PII register document in 1Password ("t PII register")', p.stdout, p.stdout + p.stderr)
        self.assertIn("document create", self.log.read_text())
        self.assertIn("--title t PII register --file-name pii-register.md", self.log.read_text())
        self.assertEqual(self.store.read_text(),
                         "# t PII register\n\n## Robin Vale\n\n| Key | Category | Value | Where used | Notes |\n|---|---|---|---|---|\n")
        self.assertEqual(p.returncode, 1)  # git history is still left

    def test_password_file_comes_from_1password(self):
        self.config("backup")
        cfg = self.home / ".config" / "restic"; cfg.mkdir(parents=True)
        (cfg / "t.env").write_text("VAULT_REPOSITORY=b2:bucket:vault\nB2_ACCOUNT_ID=k\nB2_ACCOUNT_KEY=s\nVAULT_BACKUP_PATH=/x\n")
        self.env["FAKE_OP_ITEM"] = "t restic repository"
        p = self.run_setup(answers="n\ny\nn\n")  # git: no; password: yes; install --init: no
        self.assertIn("ok        Backblaze B2 settings in t.env", p.stdout, p.stdout + p.stderr)
        pw = cfg / "t.password"
        self.assertEqual(pw.read_text(), "hunter2-test\n")
        self.assertEqual(pw.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("hunter2", p.stdout + p.stderr)
        self.assertIn("todo      restic repositories and nightly jobs", p.stdout)
        calls = self.log.read_text()
        self.assertIn("item get t restic repository --format json", calls)
        self.assertNotIn("item create", calls)  # the item existed, so it was read, not made


if __name__ == "__main__":
    unittest.main()
