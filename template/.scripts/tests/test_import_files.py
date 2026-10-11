"""Tests for .scripts/import-files, on a temp mini vault (never the real one). Run: python3 -m unittest discover .scripts/tests"""
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "import-files"
LINT = HERE.parent / "vault-lint"
HEADER = "sha256\tsize\tfiled_path\toriginal_path\toriginal_name\timported\n"


class ImportFiles(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for d in ("_imports", "_captures", "_attachments/_raw", "_files"):
            (self.root / d).mkdir(parents=True)
        (self.root / "_attachments/_raw/manifest.tsv").write_text(HEADER)
        self.env = dict(os.environ, VAULT_FILES=str(self.root / "_files"),
                        VAULT_FILES_IMAGE=str(self.root / "no-image.sparsebundle"))

    def tearDown(self):
        self._tmp.cleanup()

    def run_cmd(self, *args, ok=True):
        p = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), "--today", "2026-10-07", *args],
                           capture_output=True, text=True, env=self.env)
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr)
        return p

    def manifest_rows(self):
        return (self.root / "_attachments/_raw/manifest.tsv").read_text().splitlines()[1:]

    def test_inventory(self):
        (self.root / "_imports/.gitkeep").write_text("")
        (self.root / "_imports/sub").mkdir()
        (self.root / "_imports/sub/a.pdf").write_bytes(b"pdf")
        (self.root / "_imports/.hidden").write_bytes(b"h")
        (self.root / "_captures/n.md").write_text("x `$=dv.current()` y\n```dataviewjs\n1\n```\n")
        out = self.run_cmd("inventory").stdout
        self.assertIn("_imports/sub/a.pdf", out)
        self.assertIn("_imports/.hidden", out)
        self.assertNotIn(".gitkeep", out)
        self.assertIn("note", out)
        self.assertIn("CODE: dataviewjs,inline-$=", out)

    def test_inventory_duplicate_and_empty(self):
        self.assertIn("empty", self.run_cmd("inventory").stdout)
        data = b"same"
        (self.root / "_imports/a.pdf").write_bytes(data)
        h = hashlib.sha256(data).hexdigest()
        with (self.root / "_attachments/_raw/manifest.tsv").open("a") as f:
            f.write(f"{h}\t4\t_files/x/a.pdf\t_imports/old.pdf\told.pdf\t2026-01-01\n")
        self.assertIn("DUPLICATE of _files/x/a.pdf", self.run_cmd("inventory").stdout)

    def test_file_moves_and_records(self):
        src = self.root / "_imports/Weird\tName.pdf"
        src.write_bytes(b"hello")
        out = self.run_cmd("file", "--src", "_imports/Weird\tName.pdf", "--slug", "my-note", "--name", "my-doc-2026-10-07").stdout
        dest = self.root / "_files/my-note/my-doc-2026-10-07.pdf"
        self.assertEqual(dest.read_bytes(), b"hello")
        self.assertFalse(src.exists())
        self.assertIn("![[_files/my-note/my-doc-2026-10-07.pdf]]", out)
        cols = self.manifest_rows()[0].split("\t")
        self.assertEqual(cols, [hashlib.sha256(b"hello").hexdigest(), "5", "_files/my-note/my-doc-2026-10-07.pdf",
                                "_imports/Weird\\tName.pdf", "Weird\\tName.pdf", "2026-10-07"])

    def test_file_dry_run(self):
        src = self.root / "_imports/a.pdf"
        src.write_bytes(b"x")
        self.run_cmd("file", "--src", "_imports/a.pdf", "--slug", "s", "--name", "a.pdf", "--dry-run")
        self.assertTrue(src.exists())
        self.assertEqual(self.manifest_rows(), [])

    def test_file_falls_back_without_store(self):
        (self.root / "_files").rmdir()
        (self.root / "_imports/a.pdf").write_bytes(b"x")
        self.run_cmd("file", "--src", "_imports/a.pdf", "--slug", "s", "--name", "a.pdf")
        self.assertTrue((self.root / "_attachments/s/a.pdf").is_file())
        self.assertIn("_attachments/s/a.pdf", self.manifest_rows()[0])

    def test_file_duplicate(self):
        (self.root / "_imports/a.pdf").write_bytes(b"dup")
        self.run_cmd("file", "--src", "_imports/a.pdf", "--slug", "s", "--name", "a.pdf")
        (self.root / "_imports/b.pdf").write_bytes(b"dup")
        out = self.run_cmd("file", "--src", "_imports/b.pdf", "--slug", "t", "--name", "b.pdf").stdout
        self.assertIn("duplicate", out)
        self.assertTrue((self.root / "_imports/b.pdf").exists())
        self.assertFalse((self.root / "_files/t").exists())
        rows = [r.split("\t") for r in self.manifest_rows()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][2], rows[0][2])
        self.assertEqual(rows[1][3], "_imports/b.pdf")

    def test_file_rejects_note_and_outside(self):
        (self.root / "_captures/n.md").write_text("n")
        self.assertNotEqual(self.run_cmd("file", "--src", "_captures/n.md", "--slug", "s", "--name", "n.md", ok=False).returncode, 0)
        (self.root / "other.pdf").write_bytes(b"o")
        self.assertNotEqual(self.run_cmd("file", "--src", "other.pdf", "--slug", "s", "--name", "o.pdf", ok=False).returncode, 0)

    def test_done_capture(self):
        (self.root / "_captures/sweep-1").mkdir()
        for _ in range(3):
            (self.root / "_captures/sweep-1/note.md").write_text("n")
            self.run_cmd("done-capture", "_captures/sweep-1/note.md")
        base = self.root / "_attachments/_raw/_captures/2026-10-07/sweep-1"
        self.assertEqual(sorted(p.name for p in base.iterdir()), ["note-2.md.txt", "note-3.md.txt", "note.md.txt"])

    def test_fence_fix(self):
        p = self.root / "_captures/n.md"
        p.write_text("a `$=1+1` b\n```dataviewjs\ncode\n```\n")
        out = self.run_cmd("fence-fix", "_captures/n.md").stdout
        self.assertEqual(p.read_text(), "a $=1+1 b\n```text\ncode\n```\n")
        self.assertIn("fence", out)
        self.assertIn("inline", out)
        self.assertIn("nothing", self.run_cmd("fence-fix", "_captures/n.md").stdout)

    def test_manifest_lint_passes(self):
        (self.root / "_imports/a.pdf").write_bytes(b"lint me")
        self.run_cmd("file", "--src", "_imports/a.pdf", "--slug", "s", "--name", "a-2026-10-07.pdf")
        p = subprocess.run([sys.executable, str(LINT), "--root", str(self.root), "--only", "manifest"],
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
