#!/usr/bin/env python3
"""Fixture tests for .scripts/vault-lint.  Run: python3 .scripts/tests/run.py

fixtures/good/         a mini vault that must lint completely clean
fixtures/bad/          a mini vault where every check fires (see BAD below)
fixtures/fix/          input for --fix; fixtures/fix-expected/ holds the
                       expected rewrite of the files that change
"""

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
LINT = HERE.parent / "vault-lint"
FIX = HERE / "fixtures"
TODAY = "2026-09-26"
# The real store's disk image must not decide the fixtures' store state; tests that need an image set their own.
os.environ["VAULT_FILES_IMAGE"] = str(Path(tempfile.gettempdir()) / "vault-lint-tests-no-image.sparsebundle")


def lint(root, *args):
    p = subprocess.run([sys.executable, str(LINT), "--root", str(root), "--today", TODAY, *args],
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def lint_json(root, *args):
    code, out, err = lint(root, "--json", *args)
    assert out.strip(), err
    return code, json.loads(out)


def _load_lint_module():
    import importlib.machinery, importlib.util
    loader = importlib.machinery.SourceFileLoader("vault_lint", str(LINT))
    spec = importlib.util.spec_from_loader("vault_lint", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["vault_lint"] = mod
    loader.exec_module(mod)
    return mod


VL = _load_lint_module()


def split_body(text):
    end = text.index("\n---\n", 3) + 5
    return text[:end], text[end:]


# (check, path, severity, message substring) that must appear for fixtures/bad
BAD = [
    ("structure", "Stuff/", "error", "top-level folder"),
    ("structure", "notes.txt", "error", "vault root"),
    ("frontmatter-present", "Resources/nested/deep.md", "error", "line 1 must be"),  # subfolder notes are checked
    ("structure", "Resources/photo.png", "error", "outside _attachments"),
    ("frontmatter-present", "Tasks/no-frontmatter.md", "error", "line 1 must be"),
    ("frontmatter-present", "Tasks/unclosed.md", "error", "never closed"),
    ("frontmatter-syntax", "Tasks/syntax-soup.md", "error", "unquoted wikilink [[busy-project]]"),
    ("frontmatter-syntax", "Tasks/syntax-soup.md", "error", "inline list"),
    ("frontmatter-syntax", "Tasks/syntax-soup.md", "warning", "quoted date"),
    ("frontmatter-syntax", "Tasks/syntax-soup.md", "error", "empty value for 'priority'"),
    ("frontmatter-syntax", "Tasks/syntax-soup.md", "error", "block scalar"),
    ("frontmatter-syntax", "Tasks/syntax-soup.md", "error", "tab character"),
    ("frontmatter-syntax", "Tasks/syntax-soup.md", "error", "single-quoted"),
    ("frontmatter-syntax", "Tasks/syntax-soup.md", "error", "ambiguous boolean"),
    ("frontmatter-syntax", "Tasks/blocked-next.md", "warning", "out of schema order"),
    ("frontmatter-syntax", "Areas/tidy.md", "warning", "expected: title, aliases, tags"),
    ("filename", "Tasks/Bad_Name.md", "error", "not kebab-case"),
    ("manifest", "_attachments/_raw/manifest.tsv", "error", "filed file missing: _attachments/gone/receipt.pdf"),
    ("manifest", "_attachments/_raw/manifest.tsv", "error", "changed since import (size): _attachments/a/scan.pdf"),
    ("manifest", "_attachments/_raw/manifest.tsv", "error", "expected 6 tab-separated columns"),
    ("filename", "Tasks/call-mom-🎉.md", "error", "emoji in filename"),
    ("filename", "Tasks/pay-rent.md", "warning", "differs from slug"),
    ("frontmatter-syntax", "Archive/archived-old-note.md", "warning", "expected: title, type, archived, archived_from"),
    ("filename", "Archive/archived-old-note.md", "warning", "'archived-' prefix"),
    ("unique-names", "Areas/sam.md", "error", "also used by People/sam.md"),
    ("unique-names", "AGENTS.md", "error", "also used by Areas/agents.md"),
    ("unique-names", "_attachments/a/scan.pdf", "error", "also used by _attachments/b/scan.pdf"),
    ("title", "Tasks/Bad_Name.md", "warning", "Title Case"),
    ("title", "Tasks/Bad_Name.md", "error", "does not match title"),
    ("title", "Tasks/call-mom-🎉.md", "error", "emoji in title"),
    ("title", "Archive/old-thing.md", "warning", "prefix"),
    ("schema", "Resources/untitled.md", "error", "required field 'title'"),
    ("schema", "Resources/no-type.md", "error", "required field 'type'"),
    ("schema", "Resources/no-type.md", "error", "must be a block list"),
    ("schema", "Archive/old-thing.md", "error", "required field 'archived'"),
    ("schema", "Archive/old-thing.md", "error", "'status: in-progress' not in"),
    ("schema", "Areas/money.md", "error", "'projects' is not allowed in Areas/"),
    ("schema", "Home.md", "error", "'tags' is not allowed in Home.md"),
    ("schema", "Agents/guide.md", "error", "'type: reference' not in"),
    ("schema", "Agents/guide.md", "error", "'created' is not allowed in Agents/"),
    ("schema", "People/sam.md", "error", "'relationship: cousin'"),
    ("schema", "Resources/lonely-note.md", "error", "must start with http"),
    ("schema", "Resources/lonely-note.md", "error", "only present when true"),
    ("schema", "Resources/lonely-note.md", "error", "kebab-case with no '#'"),
    ("schema", "Resources/lonely-note.md", "error", "retired field 'description'"),
    ("schema", "Tasks/pay-rent.md", "error", "'priority: extreme'"),
    ("schema", "Tasks/pay-rent.md", "error", "retired field 'old_id'"),
    ("schema", "Tasks/pay-rent.md", "error", "retired field 'edited'"),
    ("schema", "Tasks/syntax-soup.md", "error", "'blurb' is not allowed"),
    ("schema", "Areas/agents.md", "error", "'aliases' holds plain text"),
    ("links", "Tasks/pay-rent.md", "error", "unresolved link [[missing-note]]"),
    ("links", "Tasks/pay-rent.md", "error", "unresolved embed [[missing.pdf]]"),
    ("links", "Tasks/blocked-next.md", "error", "must hold only [[links]]"),
    ("relations", "Projects/big-project.md", "error", "'area' → [[paul]] is in People/"),
    ("relations", "Tasks/wrong-target.md", "error", "'project' → [[money]]"),
    ("relations", "Tasks/wrong-target.md", "error", "'people' → [[money]]"),
    ("relations", "Tasks/closed-task.md", "error", "'parent' → [[money]]"),
    ("tasks", "Tasks/Bad_Name.md", "warning", "6 words"),
    ("tasks", "Tasks/loose-capture.md", "error", "neither 'project' nor 'area'"),
    ("tasks", "Tasks/pay-rent.md", "error", "needs 'waiting_on'"),
    ("tasks", "Tasks/pay-rent.md", "error", "needs 'waiting_since'"),
    ("tasks", "Tasks/pay-rent.md", "error", "neither 'project' nor 'area'"),
    ("tasks", "Tasks/pay-rent.md", "warning", "overdue"),
    ("tasks", "Tasks/pay-rent.md", "error", "open task has a 'completed'"),
    ("tasks", "Tasks/closed-task.md", "warning", "archive it"),
    ("tasks", "Tasks/closed-task.md", "warning", "no 'completed' date"),
    ("tasks", "Tasks/blocked-next.md", "warning", "blocked by open task"),
    ("tasks", "Tasks/blocked-next.md", "warning", "'area' is only for tasks without"),
    ("tasks", "Tasks/wrong-target.md", "warning", "inbox task already has a 'project'"),
    ("tasks", "Tasks/file-the-receipts.md", "warning", "queued is for project steps"),
    ("tasks", "Tasks/sort-the-mail.md", "warning", "inbox task has a 'due' date"),
    ("projects", "Projects/big-project.md", "warning", "in-progress project has no next action"),
    ("projects", "Projects/planned-project.md", "warning", "should have none"),
    ("projects", "Projects/waiting-project.md", "warning", "should have none"),
    ("projects", "Projects/waiting-project.md", "warning", "no waiting-for task"),
    ("projects", "Projects/planned-project.md", "warning", "'health' without 'last_sweep'"),
    ("projects", "Projects/waiting-project.md", "warning", "no '## Status' section"),
    ("schema", "Projects/waiting-project.md", "error", "'health: fine' not in"),
    ("projects", "Projects/busy-project.md", "error", "is done but has"),
    ("projects", "Projects/busy-project.md", "warning", "archive it"),
    ("pii", "Tasks/pay-rent.md", "error", "SSN"),
    ("pii", "Tasks/pay-rent.md", "error", "replace it with its key"),
    ("pii", "Tasks/pay-rent.md", "error", "phone number"),
    ("pii", "Tasks/pay-rent.md", "error", "email address"),
    ("pii", "Tasks/pay-rent.md", "error", "street address"),
    ("pii", "Tasks/pay-rent.md", "error", "date of birth"),
    ("sensitive", "Tasks/sort-the-mail.md", "warning", "has PII keys"),
    ("waiting-on", "Tasks/chase-the-shop.md", "error", "not type: organization"),
    ("format", "Tasks/blocked-next.md", "warning", "blank line after the frontmatter"),
    ("format", "Tasks/star-bullets.md", "warning", "list markers to '-'"),
    ("format", "Tasks/doc-style-soup.md", "warning", "heading levels increment by one"),
    ("format", "Tasks/doc-style-soup.md", "warning", "heading trailing punctuation"),
    ("format", "Tasks/doc-style-soup.md", "warning", "straight quotes"),
    ("format", "Tasks/doc-style-soup.md", "warning", "ordered list markers to '.'"),
    ("format", "Tasks/doc-style-soup.md", "warning", "code fence language 'text'"),
    ("pii", "Tasks/pay-rent.md", "error", "long digit run"),
    ("pii", "Tasks/pay-rent.md", "error", "password"),
    ("pii", "Tasks/pay-rent.md", "error", "api key"),
    ("pii", "Tasks/pay-rent.md", "error", "sk-"),
    ("pii", "Tasks/pay-rent.md", "error", "private key"),
    ("orphans", "Resources/no-type.md", "info", "no note links"),
    ("source-urls", "Tasks/closed-task.md", "error", "frontmatter"),
    ("source-urls", "Tasks/pay-rent.md", "info", "body"),
    # file-format (CRLF / BOM / Latin-1 files are real fixture files)
    ("file-format", "Tasks/water-the-plants.md", "warning", "CRLF"),
    ("file-format", "Tasks/feed-the-cat.md", "warning", "byte-order mark"),
    ("file-format", "Tasks/pay-the-cafe.md", "error", "not valid UTF-8"),
    # newer rules folded into existing checks
    ("filename", "Tasks/untitled.md", "warning", "'Untitled' note"),
    ("schema", "Areas/garden.md", "warning", "tag 'next-action' is a status"),
    ("links", "Resources/sweep-log.md", "warning", "bare slugs: [[paul]]"),
    ("links", "Resources/lonely-note.md", "warning", "![[paul]] transcludes a note"),
    ("tasks", "Tasks/misc-rule-breaker.md", "warning", "'waiting_on' on a next-action task"),
    ("tasks", "Tasks/misc-rule-breaker.md", "warning", "'agenda' context needs 'people'"),
    ("tasks", "Tasks/misc-rule-breaker.md", "warning", "'assignee' is for people other than Robin"),
    ("tasks", "Tasks/misc-rule-breaker.md", "error", "blocked by itself"),
    ("tasks", "Tasks/cycle-a.md", "error", "blocked_by cycle: cycle-a → cycle-b → cycle-a"),
    ("tasks", "Tasks/Bad_Name.md", "error", "open task under done project [[busy-project]]"),
    ("projects", "Projects/a-very-long-project-title-that-rambles-on.md", "warning", "8 words"),
    ("pii", "Tasks/pay-rent.md", "error", "PIN"),
    ("pii", "Tasks/pay-rent.md", "error", "card security code"),
    ("pii", "Tasks/pay-rent.md", "error", "recovery code"),
    ("title", "Resources/saved-link.md", "warning", "ends with punctuation"),
    ("links", "Resources/saved-link.md", "warning", "[[sweep-log#No such part]]: no such heading"),
    ("links", "Resources/saved-link.md", "warning", "[[sweep-log#^gone]]"),
    # archive
    ("archive", "Archive/open-archived-task.md", "warning", "archived but status is next-action"),
    ("archive", "Archive/cancelled-undated.md", "info", "no 'completed' date"),
    # attachments
    ("attachments", "_attachments/loose.pdf", "warning", "top of _attachments/"),
    ("attachments", "_attachments/loose.pdf", "info", "orphan"),
    ("attachments", "_attachments/deep/x/y.pdf", "warning", "nested too deep"),
    ("attachments", "_attachments/nobody/Scan One.PDF", "warning", "not kebab-case"),
    ("attachments", "_attachments/nobody/Scan One.PDF", "warning", "matches no note"),
    ("attachments", "_attachments/lonely-note/receipt.pdf", "warning", "not embedded by its note [[lonely-note]]"),
    ("attachments", "_attachments/lonely-note/stray-note.md", "warning", "a note inside _attachments/"),
    # anatomy
    ("anatomy", "Projects/a-very-long-project-title-that-rambles-on.md", "warning", "missing required '## Tasks'"),
    ("anatomy", "Areas/garden.md", "warning", "'## Projects' has no Dataview block"),
    ("anatomy", "Areas/garden.md", "warning", "second '# ' heading"),
    ("anatomy", "Areas/garden.md", "warning", "emoji in heading"),
    ("anatomy", "Areas/garden.md", "warning", "(revisit next spring)"),
    ("anatomy", "Areas/garden.md", "warning", "(revisit 2026-02-30)"),
    ("anatomy", "Agents/guide.md", "warning", "Part of the [[README]]"),
    ("anatomy", "Resources/sweep-log.md", "warning", "log resource has no 'date'"),
    ("schema", "Resources/sweep-log.md", "warning", "run record goes in"),
    ("anatomy", "Resources/sweep-log.md", "warning", "'## Someday/maybe' belongs in Area notes"),
    # dataview
    ("dataview", "Areas/garden.md", "warning", "uses 'blocking'"),
    ("dataviewjs", "Resources/js-widget.md", "error", "dataviewjs block"),
    ("templater", "Agents/templates/template-odd.md", "error", "isn't one the kit ships"),
    ("dataview", "Areas/garden.md", "warning", "uses 'tasks'"),
    ("dataview", "Areas/garden.md", "warning", 'FROM "Todo"'),
    # dates
    ("dates", "Archive/finished-no-date.md", "error", "'completed' 2026-12-01 is in the future"),
    ("dates", "Archive/finished-no-date.md", "warning", "'completed' is before 'created'"),
    ("dates", "Tasks/future-dates.md", "warning", "'created' 2026-12-25 is in the future"),
    ("dates", "Tasks/future-dates.md", "warning", "'waiting_since' 2026-10-10 is in the future"),
    ("dates", "Tasks/future-dates.md", "warning", "looks like a typo"),
    # facts
    ("facts", "People/sam.md", "error", "banned claim ([[false-facts]]): Sam likes durian"),
    ("facts", "Resources/false-facts.md", "info", "no Search pattern"),
    ("facts", "Resources/false-facts.md", "error", "bad Search regex"),
    ("facts", "People/sam.md", "info", "worded as current but dated 2019"),
    ("facts", "People/sam.md", "info", "names Jo Ray but never links [[jo-ray]]"),
]

# Things the bad vault must NOT report (guards against false positives).
NOT_BAD = [
    ("orphans", "Resources/lonely-note.md"),   # linked from no-type.md body
    ("pii", "Tasks/closed-task.md"),
    ("pii", "Tasks/pay-rent.md", "(…7890)"),   # a toll-free number stays
    ("pii", "People/lena-ortiz.md"),          # a professional contact's number stays
    ("pii", "Tasks/pay-rent.md", "(….org)"),   # a role mailbox (support@) stays
    ("attachments", "_attachments/nobody/Scan One.PDF", "orphan"),  # embedded by lonely-note
    ("dataview", "Areas/garden.md", "'t'"),     # lambda parameter
    ("dataview", "Areas/garden.md", "'area'"),  # a real schema field
    ("frontmatter-present", "Tasks/pay-the-cafe.md"),  # still parsed despite bad bytes
    ("tasks", "Tasks/cycle-b.md", "cycle"),     # a cycle is reported once
    ("projects", "Projects/active-project.md", "next-action"),  # several next actions are allowed
    ("links", "Resources/saved-link.md", "Someday/maybe"),  # heading exists
    ("facts", "Resources/false-facts.md", "banned claim"),  # the list itself
]


class GoodVault(unittest.TestCase):
    """Includes a Templater template (Agents/templates/template-task.md) and the root
    AGENTS.md, which must be exempt from note checks."""

    def test_clean(self):
        code, findings = lint_json(FIX / "good")
        self.assertEqual(findings, [], json.dumps(findings, indent=1, ensure_ascii=False))
        self.assertEqual(code, 0)

    def test_human_output_and_summary(self):
        code, out, _ = lint(FIX / "good")
        self.assertEqual(code, 0)
        self.assertIn("Summary", out)

    def test_fix_is_noop_on_clean_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "v"
            shutil.copytree(FIX / "good", root)
            _, out, _ = lint(root, "--fix")
            self.assertIn("--fix: 0 file(s) changed", out)


class BadVault(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code, cls.findings = lint_json(FIX / "bad")

    def test_exit_code(self):
        self.assertEqual(self.code, 1)

    def test_json_shape(self):
        for f in self.findings:
            self.assertEqual(set(f), {"check", "severity", "path", "line", "message", "fixable"})
            self.assertIn(f["severity"], {"error", "warning", "info"})

    def test_expected_findings(self):
        missing = []
        for check, path, sev, sub in BAD:
            if not any(f["check"] == check and f["path"] == path and f["severity"] == sev
                       and sub in f["message"] for f in self.findings):
                missing.append((check, path, sev, sub))
        self.assertEqual(missing, [], "\n" + "\n".join(map(str, missing)))

    def test_every_check_covered(self):
        code, out, _ = lint(FIX / "bad", "--list-checks")
        ids = [line.split()[0] for line in out.splitlines() if line.strip()]
        covered = {c for c, *_ in BAD}
        self.assertEqual(sorted(set(ids) - covered), [])

    def test_no_false_positives(self):
        for check, path, *sub in NOT_BAD:
            hits = [f for f in self.findings if f["check"] == check and f["path"] == path
                    and (not sub or sub[0] in f["message"])]
            self.assertEqual(hits, [], (check, path, sub))

    def test_only_and_paths(self):
        _, findings = lint_json(FIX / "bad", "--only", "tasks", "Tasks/pay-rent.md")
        self.assertTrue(findings)
        self.assertTrue(all(f["check"] == "tasks" and f["path"] == "Tasks/pay-rent.md" for f in findings))

    def test_unknown_check(self):
        code, _, err = lint(FIX / "bad", "--only", "nope")
        self.assertEqual(code, 2)

    def test_quiet_shows_errors_only(self):
        _, out, _ = lint(FIX / "bad", "--quiet")
        body = out.split("Summary")[0]
        self.assertNotIn(": warning:", body)
        self.assertIn(": error:", body)


class Fix(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "v"
        shutil.copytree(FIX / "fix", self.root)
        self.before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*.md")}

    def tearDown(self):
        self.tmp.cleanup()

    def test_fix_matches_expected(self):
        _, out, _ = lint(self.root, "--fix")
        self.assertIn("fixed Tasks/messy-task.md", out)
        expected = FIX / "fix-expected"
        for want in expected.rglob("*.md"):
            rel = want.relative_to(expected)
            got = (self.root / rel).read_bytes()
            self.assertEqual(got.decode(), want.read_bytes().decode(), str(rel))

    def test_idempotent(self):
        lint(self.root, "--fix")
        snap = {p: p.read_bytes() for p in self.root.rglob("*.md")}
        _, out, _ = lint(self.root, "--fix")
        self.assertIn("--fix: 0 file(s) changed", out)
        self.assertEqual(snap, {p: p.read_bytes() for p in self.root.rglob("*.md")})

    def test_body_preserved(self):
        lint(self.root, "--fix")
        for rel, old in self.before.items():
            new = (self.root / rel).read_bytes()
            # the body changes only through the formatter (the `format` check)
            old_body = split_body(old.decode())[1]
            want = VL.format_body(old_body)[0] if not rel.name.startswith("unsafe") else old_body
            self.assertEqual(want, split_body(new.decode())[1], str(rel))

    def test_unsafe_and_meaningful_left_alone(self):
        lint(self.root, "--fix")
        rel = "Tasks/unsafe-task.md"   # unsafe frontmatter: file untouched
        self.assertEqual(self.before[Path(rel)], (self.root / rel).read_bytes(), rel)
        rel = "Resources/tidy-note.md"  # meaningful retired field: frontmatter untouched
        self.assertEqual(split_body(self.before[Path(rel)].decode())[0],
                         split_body((self.root / rel).read_text())[0], rel)

    def test_no_temp_files_left(self):
        lint(self.root, "--fix")
        self.assertEqual([p for p in self.root.rglob(".vault-lint-*")], [])

    def test_fixed_file_has_no_fixable_findings(self):
        lint(self.root, "--fix")
        _, findings = lint_json(self.root, "Tasks/messy-task.md")
        self.assertEqual([f for f in findings if f["fixable"]], [])


def load_module():
    """Import vault-lint (no .py suffix) for unit-level tests."""
    import importlib.machinery
    import importlib.util
    sys.dont_write_bytecode = True  # no __pycache__ inside the vault
    loader = importlib.machinery.SourceFileLoader("vault_lint", str(LINT))
    spec = importlib.util.spec_from_loader("vault_lint", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["vault_lint"] = mod
    loader.exec_module(mod)
    return mod


class Formatter(unittest.TestCase):
    """format_body mirrors the Obsidian Linter rules enabled for the vault."""

    def test_doc_style_soup(self):
        body = (FIX / "bad/Tasks/doc-style-soup.md").read_text().split("---\n", 2)[2]
        new, _ = VL.format_body(body)
        self.assertIn("## Skipped a level\n", new)
        self.assertIn("Robin's \"quoted\" note, but `keep \u2018code\u2019` as is.", new)
        self.assertIn("1. first\n2. second", new)
        self.assertIn("```text\nplain fence\n```\n", new)
        self.assertEqual(VL.format_body(new)[0], new)  # idempotent

    def test_list_start_preserved(self):
        new, _ = VL.format_body("# T\n\n13. thirteen\n15. fifteen\n")
        self.assertIn("13. thirteen\n14. fifteen", new)


class Robustness(unittest.TestCase):
    """Odd files must be reported, never crash the run, and never be damaged by --fix."""

    MESSY_FM = '---\nstatus: inbox\ntitle: {t}\narea:\n  - "[[health]]"\n---\n'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "v"
        shutil.copytree(FIX / "good", self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, data: bytes):
        p = self.root / rel
        p.write_bytes(data)
        return p

    def fix_twice(self):
        _, out1, _ = lint(self.root, "--fix")
        snap = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file() and not p.is_symlink()}
        _, out2, _ = lint(self.root, "--fix")
        self.assertIn("--fix: 0 file(s) changed", out2)
        self.assertEqual(snap, {p: p.read_bytes() for p in self.root.rglob("*")
                                if p.is_file() and not p.is_symlink()})
        return out1

    def test_crlf_fix_keeps_crlf_body(self):
        body = "\r\n# Crlf task\r\n\r\nLine one\r\nLine two\r\n"
        p = self.write("Tasks/crlf-task.md",
                       (self.MESSY_FM.format(t="Crlf task").replace("\n", "\r\n") + body).encode())
        out = self.fix_twice()
        self.assertIn("fixed Tasks/crlf-task.md", out)
        data = p.read_bytes().decode()
        self.assertTrue(data.startswith("---\r\ntitle: Crlf task\r\nstatus: inbox\r\n"), data)
        self.assertTrue(data.endswith(body))
        self.assertNotIn("\n", data.replace("\r\n", ""))
        _, findings = lint_json(self.root, "Tasks/crlf-task.md")
        self.assertEqual({f["check"] for f in findings}, {"file-format"})

    def test_bom_removed_by_fix(self):
        p = self.write("Tasks/bom-task.md", "\ufeff---\ntitle: Bom task\nstatus: inbox\narea:\n"
                       "  - \"[[health]]\"\n---\n\n# Bom task\n".encode())
        _, findings = lint_json(self.root)
        self.assertTrue(any(f["check"] == "file-format" and f["fixable"] for f in findings))
        self.assertFalse(any(f["check"] == "frontmatter-present" for f in findings))
        out = self.fix_twice()
        self.assertIn("removed UTF-8 byte-order mark", out)
        self.assertTrue(p.read_bytes().startswith(b"---\ntitle: Bom task\n"))

    def test_no_trailing_newline(self):
        p = self.write("Tasks/eof-task.md", self.MESSY_FM.format(t="Eof task").encode()[:-1])
        self.fix_twice()
        self.assertEqual(p.read_bytes(), b'---\ntitle: Eof task\nstatus: inbox\narea:\n  - "[[health]]"\n---')
        p2 = self.write("Tasks/eof-body.md", (self.MESSY_FM.format(t="Eof body") + "\n# Eof body").encode())
        self.fix_twice()
        self.assertTrue(p2.read_bytes().endswith(b"---\n# Eof body\n"))

    def test_non_utf8_reported_and_untouched(self):
        raw = (self.MESSY_FM.format(t="Caf\xe9 run") + "\n# Caf\xe9 run\n").encode("latin-1")
        p = self.write("Tasks/cafe-run.md", raw)
        code, findings = lint_json(self.root)
        self.assertEqual(code, 1)
        self.assertTrue(any(f["check"] == "file-format" and "UTF-8" in f["message"] for f in findings))
        lint(self.root, "--fix")
        self.assertEqual(p.read_bytes(), raw)

    def test_symlinks_reported_not_followed(self):
        target = self.root / "Tasks" / "call-the-lawyer.md"
        before = target.read_bytes()
        os.symlink(target, self.root / "Tasks" / "linked-task.md")
        os.symlink(self.root / "Tasks", self.root / "Resources" / "tasks-dir")
        os.symlink(self.root / "nowhere.md", self.root / "Tasks" / "broken-link.md")
        code, findings = lint_json(self.root)
        sym = {f["path"] for f in findings if f["check"] == "file-format" and "symlink" in f["message"]}
        self.assertEqual(sym, {"Tasks/linked-task.md", "Resources/tasks-dir", "Tasks/broken-link.md"})
        lint(self.root, "--fix")
        self.assertTrue((self.root / "Tasks" / "linked-task.md").is_symlink())
        self.assertEqual(target.read_bytes(), before)

    def test_very_large_file(self):
        import time
        big = self.MESSY_FM.format(t="Big log") + "\n# Big log\n" + ("x" * 120 + " 123456789012\n") * 20000
        self.write("Resources/big-log.md", big.encode())
        t = time.time()
        code, findings = lint_json(self.root)
        self.assertLess(time.time() - t, 3.0)
        mine = [f for f in findings if f["path"] == "Resources/big-log.md"]
        self.assertEqual({f["check"] for f in mine} - {"orphans"}, {"file-format"})
        self.assertIn("content checks skipped", mine[0]["message"])

    def test_atomic_write_refuses_concurrent_change(self):
        mod = load_module()
        p = self.write("Tasks/race.md", b"old")
        ok = mod.atomic_write(p, "new", expect=b"something else")
        self.assertFalse(ok)
        self.assertEqual(p.read_bytes(), b"old")
        self.assertTrue(mod.atomic_write(p, "new", expect=b"old"))
        self.assertEqual(p.read_bytes(), b"new")
        self.assertEqual(list(p.parent.glob(".vault-lint-*")), [])

    def test_bad_today(self):
        code, _, err = lint(self.root, "--today", "2026-13-40")
        self.assertEqual(code, 2)


class Citations(unittest.TestCase):
    """Key facts added after the baseline commit need a citation; older lines are legacy (Agents/linking.md)."""

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@t",
                               *args], capture_output=True, text=True, check=True).stdout.strip()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "v"
        shutil.copytree(FIX / "good", self.root)
        self.person = self.root / "People/lena-ortiz.md"
        self.person.write_text(self.person.read_text() + "\n## Key facts\n\n- Legacy fact, never cited\n")
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.old_env = os.environ.get("VAULT_LINT_CITE_BASELINE")
        os.environ["VAULT_LINT_CITE_BASELINE"] = self.git("rev-parse", "HEAD")

    def tearDown(self):
        if self.old_env is None:
            os.environ.pop("VAULT_LINT_CITE_BASELINE", None)
        else:
            os.environ["VAULT_LINT_CITE_BASELINE"] = self.old_env
        self.tmp.cleanup()

    def cite_findings(self):
        _, data = lint_json(self.root, "--only", "facts")
        return sorted((f["path"], f["line"]) for f in data if "citation" in f["message"])

    def test_only_new_uncited_lines_flagged(self):
        text = self.person.read_text()
        self.person.write_text(text + "- Cited to a file ([[estate-plan]])\n"
                               "- Cited to a capture (Mail, 2026-10-12, [[log-x]]).\n"
                               "- Told directly (Robin, 2026-10-12)\n"
                               "- New and uncited\n")
        line = len(text.split("\n")) + 3
        self.assertEqual(self.cite_findings(), [("People/lena-ortiz.md", line)])

    def test_new_file_lines_flagged(self):
        (self.root / "People/new-person.md").write_text(
            "---\ntitle: New person\n---\n# New person\n\n## Key facts\n\n- Uncited\n")
        self.assertEqual(self.cite_findings(), [("People/new-person.md", 8)])

    def test_no_git_no_findings(self):
        shutil.rmtree(self.root / ".git")
        self.person.write_text(self.person.read_text() + "- New and uncited\n")
        self.assertEqual(self.cite_findings(), [])


class Review(unittest.TestCase):
    ROOT = FIX / "review"

    def review(self, root=None, *args):
        code, out, err = lint(root or self.ROOT, "--review", *args)
        self.assertEqual(code, 0, err)
        return out

    def test_json_sections(self):
        r = json.loads(self.review(None, "--json", "--no-git"))
        self.assertEqual(r["today"], TODAY)
        due = [(d["slug"], d["days_left"], d["overdue"]) for d in r["due"]]
        self.assertEqual(due, [("call-the-roofer", -6, True), ("buy-balloons", 5, False)])
        self.assertEqual(list(r["next_actions_by_project"]), ["fix-the-roof", "plan-the-party", ""])
        self.assertEqual([b["slug"] for b in r["next_actions_by_project"]["plan-the-party"]],
                         ["buy-balloons", "send-invites"])
        self.assertEqual(sorted(r["next_actions_by_context"]), ["", "calls", "errands", "home"])
        self.assertEqual([b["slug"] for b in r["inbox"]], ["clean-the-gutters"])
        self.assertEqual(r["queued_steps"], 3)
        self.assertEqual([(w["slug"], w["age_days"], w["stale"]) for w in r["waiting"]],
                         [("chase-the-refund", 16, True), ("hear-back-from-sam", 2, False)])
        rule = {x["slug"]: x for x in r["project_rule"]}
        self.assertEqual(sorted(rule), ["write-the-book"])
        self.assertEqual(rule["write-the-book"].get("promote"), "draft-chapter-one")
        self.assertEqual([b["slug"] for b in r["promote"]], ["paint-the-fence"])  # sand-the-deck still blocked
        self.assertEqual([x["path"] for x in r["closed_not_archived"]],
                         ["Projects/old-project.md", "Tasks/pay-the-deposit.md"])
        self.assertEqual([(x["area"], x["revisit"]) for x in r["revisit"]], [("home-upkeep", "2026-09-01")])
        self.assertEqual(r["lint"]["errors"], 0)

    def test_days_window(self):
        r = json.loads(self.review(None, "--json", "--no-git", "--days", "0"))
        self.assertEqual([d["slug"] for d in r["due"]], ["call-the-roofer"])

    def test_markdown(self):
        out = self.review(None, "--no-git")
        for s in ("# GTD review, 2026-09-26", "## Overdue and due within 7 days", "**OVERDUE 6d**",
                  "### [[plan-the-party]]", "### No project (area only)", "### No context set",
                  "## Inbox captures to clarify (1)", "16d: [[chase-the-refund]]", "chase, wait, or drop?",
                  "Promote [[draft-chapter-one]]", "[[paint-the-fence]]", "Tasks/pay-the-deposit.md (done",
                  "(revisit 2026-09-01): Build a shed"):
            self.assertIn(s, out)

    def test_stale_from_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "v"
            shutil.copytree(self.ROOT, root)
            old = datetime.datetime(2026, 9, 1, 12).timestamp()
            new = datetime.datetime(2026, 9, 25, 12).timestamp()
            for p in root.rglob("*.md"):
                os.utime(p, (old, old))
            for rel in ("Tasks/buy-balloons.md",):  # plan-the-party stays fresh
                os.utime(root / rel, (new, new))
            r = json.loads(self.review(root, "--json", "--no-git"))
            st = r["stale_projects"]
            self.assertEqual(st["source"], "mtime")
            self.assertEqual([(x["slug"], x["age_days"]) for x in st["items"]], [("fix-the-roof", 25)])

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_stale_from_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "v"
            shutil.copytree(self.ROOT, root)
            env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com",
                       GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

            def git(*a, date=None):
                e = dict(env, GIT_AUTHOR_DATE=date or "", GIT_COMMITTER_DATE=date or "") if date else env
                subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True, env=e)
            git("init", "-q")
            git("add", "-A")
            git("commit", "-q", "-m", "old", date="2026-09-01T12:00:00")
            (root / "Tasks/send-invites.md").write_text((root / "Tasks/send-invites.md").read_text() + "\nMore.\n")
            git("commit", "-q", "-am", "new", date="2026-09-24T12:00:00")
            r = json.loads(self.review(root, "--json"))
            st = r["stale_projects"]
            self.assertEqual(st["source"], "git")
            self.assertEqual([(x["slug"], x["last_change"]) for x in st["items"]], [("fix-the-roof", "2026-09-01")])
            # an uncommitted edit counts as a change today
            p = root / "Tasks/call-the-roofer.md"
            p.write_text(p.read_text() + "\nCalled.\n")
            r = json.loads(self.review(root, "--json"))
            self.assertEqual(r["stale_projects"]["items"], [])

    def test_review_rejects_fix(self):
        code, _, _ = lint(self.ROOT, "--review", "--fix")
        self.assertEqual(code, 2)


class ArchiveAndPromote(unittest.TestCase):
    """--archive-closed and --promote work on a copy of the review fixture."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "v"
        shutil.copytree(FIX / "review", self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def put(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def task(self, slug, status, **fm):
        extra = "".join(f"{k}: {v}\n" for k, v in fm.items() if not isinstance(v, list))
        for k, v in fm.items():
            if isinstance(v, list):
                extra += f"{k}:\n" + "".join(f'  - "{i}"\n' for i in v)
        title = slug.replace("-", " ").capitalize()
        self.put(f"Tasks/{slug}.md", f"---\ntitle: {title}\nstatus: {status}\n{extra}---\n\n# {title}\n")

    def run_flags(self, *flags):
        code, out, err = lint(self.root, *flags)
        self.assertEqual(code, 0, out + err)
        return out

    def test_dry_run_changes_nothing(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        out = self.run_flags("--archive-closed", "--promote", "--dry-run")
        self.assertIn("would archive Tasks/pay-the-deposit.md -> Archive/pay-the-deposit.md", out)
        self.assertIn("would promote Tasks/draft-chapter-one.md", out)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_archive_moves_closed_tasks_in_schema_order(self):
        self.task("zz-done-no-date", "done", project="\"[[plan-the-party]]\"", created="2026-09-01")
        self.task("zz-cancelled", "cancelled", completed="2026-09-10", area=["[[home-upkeep]]"], tags=["a-tag"])
        out = self.run_flags("--archive-closed")
        self.assertIn("left for an agent: Projects/old-project.md", out)  # closed project: never moved
        self.assertTrue((self.root / "Projects/old-project.md").exists())
        for slug in ("pay-the-deposit", "zz-done-no-date", "zz-cancelled"):
            self.assertFalse((self.root / f"Tasks/{slug}.md").exists(), slug)
        kept = (self.root / "Archive/pay-the-deposit.md").read_text()
        self.assertIn("completed: 2026-09-15\narchived: true\narchived_from: Tasks\n---", kept)  # date kept
        added = (self.root / "Archive/zz-done-no-date.md").read_text()
        self.assertIn("completed: 2026-09-26\narchived: true\narchived_from: Tasks\ncreated: 2026-09-01\n", added)
        tagged = (self.root / "Archive/zz-cancelled.md").read_text()
        self.assertIn("completed: 2026-09-10\narchived: true\narchived_from: Tasks\ntags:", tagged)
        self.assertIn("(completed set to today)", out)
        findings = lint_json(self.root, "--only", "schema,archive,frontmatter-syntax",
                             "Archive/pay-the-deposit.md", "Archive/zz-done-no-date.md", "Archive/zz-cancelled.md")[1]
        self.assertEqual(findings, [])

    def test_archive_is_idempotent_and_leaves_no_temp_files(self):
        self.run_flags("--archive-closed")
        out = self.run_flags("--archive-closed")
        self.assertIn("--archive-closed: 0 task(s) archived", out)
        self.assertEqual([p.name for p in self.root.rglob(".vault-lint-*")], [])

    def test_archive_never_overwrites_a_taken_name(self):
        self.put("Archive/pay-the-deposit.md", "---\ntitle: Pay the deposit\n---\n")
        code, out, _ = lint(self.root, "--archive-closed")
        self.assertEqual(code, 1)  # the duplicate name is a lint error, left for a person
        self.assertIn("skipped Tasks/pay-the-deposit.md: Archive/ or another folder already holds that filename", out)
        self.assertTrue((self.root / "Tasks/pay-the-deposit.md").exists())

    def test_archive_paths_limit_it(self):
        self.task("zz-cancelled", "cancelled", completed="2026-09-10", project="\"[[plan-the-party]]\"")
        self.run_flags("--archive-closed", "Tasks/zz-cancelled.md")
        self.assertTrue((self.root / "Archive/zz-cancelled.md").exists())
        self.assertTrue((self.root / "Tasks/pay-the-deposit.md").exists())

    def test_archive_keeps_crlf(self):
        p = self.root / "Tasks/pay-the-deposit.md"
        p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        self.run_flags("--archive-closed")
        data = (self.root / "Archive/pay-the-deposit.md").read_bytes()
        self.assertIn(b"archived: true\r\narchived_from: Tasks\r\n", data)
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))

    def test_promote_picks_priority_then_due_then_created(self):
        for slug in ("zz-med-early", "zz-high-nodue", "zz-high-blocked", "zz-high-due", "zz-low"):
            self.assertFalse((self.root / f"Tasks/{slug}.md").exists())
        proj = "\"[[write-the-book]]\""
        self.task("zz-open-blocker", "waiting-for", waiting_on="\"[[sam]]\"", waiting_since="2026-09-20",
                  project=proj)
        self.task("zz-med-early", "queued", priority="med", due="2026-09-27", project=proj)
        self.task("zz-high-nodue", "queued", priority="high", project=proj, created="2026-09-01")
        self.task("zz-high-blocked", "queued", priority="urgent", due="2026-09-27", project=proj,
                  blocked_by=["[[zz-open-blocker]]"])
        self.task("zz-high-due", "queued", priority="high", due="2026-10-05", project=proj)
        self.task("zz-low", "queued", priority="low", project=proj)
        (self.root / "Tasks/draft-chapter-one.md").unlink()  # the fixture's own candidate
        out = self.run_flags("--promote")
        self.assertIn("promoted Tasks/zz-high-due.md to next-action, project write-the-book", out)
        self.assertIn("--promote: 1 task(s) promoted", out)
        self.assertIn("status: next-action", (self.root / "Tasks/zz-high-due.md").read_text())
        for slug in ("zz-high-nodue", "zz-high-blocked", "zz-med-early", "zz-low"):
            self.assertIn("status: queued", (self.root / f"Tasks/{slug}.md").read_text(), slug)

    def test_promote_reports_missing_contexts_and_keeps_existing(self):
        out = self.run_flags("--promote")
        self.assertIn("promoted Tasks/draft-chapter-one.md to next-action, project write-the-book; "
                      "needs contexts (agent)", out)
        self.assertNotIn("contexts", (self.root / "Tasks/draft-chapter-one.md").read_text())
        self.task("zz-next", "queued", project="\"[[write-the-book]]\"")
        (self.root / "Tasks/draft-chapter-one.md").unlink()
        self.put("Tasks/zz-next.md", (self.root / "Tasks/zz-next.md").read_text().replace(
            "project:", "contexts:\n  - computer\nproject:"))
        self.run_flags("--promote")  # write-the-book already has none: zz-next is promoted, contexts kept
        text = (self.root / "Tasks/zz-next.md").read_text()
        self.assertIn("status: next-action", text)
        self.assertIn("contexts:\n  - computer", text)

    def test_promote_lists_projects_with_nothing_ready(self):
        (self.root / "Tasks/draft-chapter-one.md").unlink()
        out = self.run_flags("--promote")
        self.assertIn("left for an agent: write-the-book has no next action and no queued task ready", out)
        self.assertIn("--promote: 0 task(s) promoted", out)

    def test_promote_ignores_inbox_and_projects_that_have_a_next_action(self):
        self.task("zz-inbox", "inbox", project="\"[[plan-the-party]]\"")  # plan-the-party has next actions
        self.task("zz-queued", "queued", project="\"[[plan-the-party]]\"")
        self.run_flags("--promote")
        self.assertIn("status: queued", (self.root / "Tasks/zz-queued.md").read_text())
        self.assertIn("status: inbox", (self.root / "Tasks/zz-inbox.md").read_text())

    def test_both_flags_together_leave_the_review_clean(self):
        self.run_flags("--archive-closed", "--promote")
        r = json.loads(self.run_flags("--review", "--json", "--no-git"))
        self.assertEqual(r["project_rule"], [])
        self.assertEqual([x["path"] for x in r["closed_not_archived"]], ["Projects/old-project.md"])

    def test_flag_combinations(self):
        for args in (["--dry-run"], ["--archive-closed", "--review"], ["--promote", "--only", "tasks"]):
            code, _, err = lint(self.root, *args)
            self.assertEqual(code, 2, args)


class AuditRegressions(unittest.TestCase):
    """Doc/linter disagreements found by the 2026-09-26 consistency audit.
    Each test copies the good vault, adds or edits files, and expects one finding."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "v"
        shutil.copytree(FIX / "good", self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def findings(self, check):
        _, found = lint_json(self.root, "--only", check)
        return found

    def assertFinding(self, check, path, sev, sub):
        found = self.findings(check)
        self.assertTrue(any(f["path"] == path and f["severity"] == sev and sub in f["message"]
                            for f in found), json.dumps(found, indent=1, ensure_ascii=False))

    def test_tmp_is_allowed_and_never_indexed(self):
        # Duplicate basename, stray file, broken note: none of it may surface.
        self.put("_tmp/audit/Tasks/call-the-lawyer.md", "no frontmatter [[nowhere]]\n")
        self.put("_tmp/notes.txt", "scratch\n")
        code, found = lint_json(self.root)
        self.assertEqual(found, [], json.dumps(found, indent=1))
        self.assertEqual(code, 0)

    def test_imports_is_allowed_and_never_indexed(self):
        # Foreign files awaiting import, including exported Markdown that may collide with note names.
        self.put("_imports/call-the-lawyer.md", "no frontmatter [[nowhere]]\n")
        self.put("_imports/scans/Receipt 2026.pdf", "%PDF-1.4\n")
        code, found = lint_json(self.root)
        self.assertEqual(found, [], json.dumps(found, indent=1))
        self.assertEqual(code, 0)

    def test_manifest_rechecks_checksums_only_with_only_manifest(self):
        import hashlib
        self.put("_attachments/receipt/receipt-2026.pdf", "%PDF-1.4 real\n")
        good = hashlib.sha256(b"%PDF-1.4 real\n").hexdigest()
        size = len(b"%PDF-1.4 real\n")
        header = "sha256\tsize\tfiled_path\toriginal_path\toriginal_name\timported\n"
        self.put("_attachments/_raw/manifest.tsv", header +
                 f"{good}\t{size}\t_attachments/receipt/receipt-2026.pdf\t~/Downloads/Receipt.pdf\tReceipt.pdf\t2026-09-27\n")
        _, found = lint_json(self.root, "--only", "manifest")
        self.assertEqual(found, [], json.dumps(found, indent=1))
        # Same size, different bytes: only the full re-hash notices.
        self.put("_attachments/receipt/receipt-2026.pdf", "%PDF-1.4 edit\n")
        _, found = lint_json(self.root, "--only", "attachments,manifest")
        self.assertFalse([f for f in found if f["check"] == "manifest"], json.dumps(found, indent=1))
        self.assertFinding("manifest", "_attachments/_raw/manifest.tsv", "error", "changed since import (checksum)")

    def test_captures_is_allowed_and_never_indexed(self):
        # Capture notes awaiting filing: loose frontmatter, links to things that don't exist yet.
        self.put("_captures/sweep-2026-09-27-2000/call-the-lawyer.md", "Kind: task [[nowhere]]\n")
        self.put("_captures/sweep-2026-09-27-2000/receipt.pdf", "%PDF-1.4\n")
        code, found = lint_json(self.root)
        self.assertEqual(found, [], json.dumps(found, indent=1))
        self.assertEqual(code, 0)

    def test_archived_from_required(self):
        self.put("Archive/old-guide.md", "---\ntitle: Old guide\ntype: reference\narchived: true\n---\n\n# Old guide\n")
        self.assertFinding("schema", "Archive/old-guide.md", "error", "required field 'archived_from'")

    def test_archive_keeps_only_origin_fields(self):
        self.put("Archive/old-guide.md", "---\ntitle: Old guide\ntype: reference\nstatus: done\n"
                 "archived: true\narchived_from: Resources\n---\n\n# Old guide\n")
        self.assertFinding("schema", "Archive/old-guide.md", "error", "'status' is not allowed")

    def test_project_takes_phase_not_status(self):
        # Projects use `phase` so Obsidian suggests task and project values apart.
        self.put("Projects/old-key.md", "---\ntitle: Old key project\nstatus: planned\narea:\n  - \"[[health]]\"\n"
                 "---\n# Old key project\n")
        self.put("Archive/old-key-done.md", "---\ntitle: Old key done\nstatus: done\ncompleted: 2026-09-01\n"
                 "archived: true\narchived_from: Projects\n---\n# Old key done\n")
        self.put("Tasks/phase-task.md", "---\ntitle: Use the phase\nphase: planned\narea:\n  - \"[[health]]\"\n"
                 "---\n# Use the phase\n")
        for rel in ("Projects/old-key.md", "Archive/old-key-done.md"):
            self.assertFinding("schema", rel, "error", "projects take 'phase', not 'status'")
        self.assertFinding("schema", "Projects/old-key.md", "error", "required field 'phase'")
        self.assertFinding("schema", "Tasks/phase-task.md", "error", "'phase' is not allowed in Tasks/")
        lint(self.root, "--fix", "Projects/old-key.md", "Archive/old-key-done.md")
        self.assertIn("\nphase: planned\n", (self.root / "Projects/old-key.md").read_text())
        self.assertIn("\nphase: done\n", (self.root / "Archive/old-key-done.md").read_text())
        _, found = lint_json(self.root)
        self.assertEqual([f for f in found if f["check"] == "schema" and f["path"] != "Tasks/phase-task.md"],
                         [], json.dumps(found, indent=1))

    def test_template_type_matches_filename(self):
        self.put("Agents/templates/template-note.md", "---\ntitle: Note template\ntype: manual\n---\n\n# Note template\n")
        self.put("Agents/cheat-sheet.md", "---\ntitle: Cheat sheet\ntype: template\n---\n\n# Cheat sheet\n")
        self.assertFinding("schema", "Agents/templates/template-note.md", "error", "type: template")
        self.assertFinding("schema", "Agents/cheat-sheet.md", "error", "type: template")

    def test_subfolders_allowed_in_content_folders(self):
        (self.root / "Resources/fitness").mkdir()
        shutil.move(self.root / "Resources/kettlebell-plan.md", self.root / "Resources/fitness/kettlebell-plan.md")
        code, found = lint_json(self.root)
        self.assertEqual(found, [], json.dumps(found, indent=1, ensure_ascii=False))
        self.assertEqual(code, 0)

    def test_subfolder_note_keeps_top_folder_schema(self):
        self.put("Resources/fitness/stretch-plan.md",
                 "---\ntitle: Stretch plan\ntype: reference\nstatus: done\n---\n# Stretch plan\n")
        self.assertFinding("schema", "Resources/fitness/stretch-plan.md", "error", "'status' is not allowed")

    def test_unique_names_across_subfolders(self):
        self.put("Resources/fitness/kettlebell-plan.md", "---\ntitle: Kettlebell plan\ntype: reference\n---\n# Kettlebell plan\n")
        self.assertFinding("unique-names", "Resources/fitness/kettlebell-plan.md", "error", "also used by")

    def test_review_and_edit_stamps_are_retired(self):
        # agent_review and edited are retired (2026-10-06); --fix deletes both
        self.put("Tasks/old.md", "---\ntitle: Old\nstatus: inbox\narea:\n  - \"[[health]]\"\ncreated: 2026-09-20\n"
                 "agent_review: needs-review\nedited: 2026-09-20T10:00\n---\n# Old\n")
        self.assertFinding("schema", "Tasks/old.md", "error", "retired field 'agent_review'")
        self.assertFinding("schema", "Tasks/old.md", "error", "retired field 'edited'")
        lint(self.root, "--fix")
        text = (self.root / "Tasks/old.md").read_text()
        self.assertNotIn("agent_review", text)
        self.assertNotIn("edited", text)

    def test_templates_and_roles_live_in_their_subfolders(self):
        self.put("Agents/template-note.md", "---\ntitle: Note template\ntype: template\n---\n# Note template\n")
        self.put("Agents/role-filer.md", "---\ntitle: Filer\ntype: manual\n---\n# Filer\n\nPart of the [[README]].\n")
        self.assertFinding("structure", "Agents/template-note.md", "error", "Agents/templates/")
        self.assertFinding("structure", "Agents/role-filer.md", "error", "Agents/roles/")

    def test_agent_logs(self):
        ok = ("---\ntitle: \"Log: vault ops — 2026-09-27\"\ntype: log\ndate: 2026-09-27\n---\n"
              "# Log: vault ops — 2026-09-27\n\nPart of the [[README]]. Run log for [[README]].\n")
        self.put("Agents/logs/log-vault-ops-2026-09-27.md", ok)
        self.put("Agents/log-vault-intake-2026-09-27.md", ok.replace("vault ops", "vault intake"))
        self.put("Agents/logs/log-vault-docs-2026-09-27.md",
                 ok.replace("vault ops", "vault docs").replace("date: 2026-09-27\n", "agent_review: needs-review\n"))
        self.put("Agents/logs/log-vault-pm-2026-09-27.md",
                 ok.replace("vault ops", "vault pm") + "\nSSN 123-45-6789\n")
        self.assertFalse([f for f in self.findings("schema") + self.findings("anatomy")
                          + self.findings("filename") + self.findings("title")
                          if f["path"] == "Agents/logs/log-vault-ops-2026-09-27.md"])
        self.assertFinding("structure", "Agents/log-vault-intake-2026-09-27.md", "error", "Agents/logs/")
        self.assertFinding("schema", "Agents/log-vault-intake-2026-09-27.md", "error", "take 'type: log'")
        self.assertFinding("schema", "Agents/logs/log-vault-docs-2026-09-27.md", "error", "retired field 'agent_review'")
        self.assertFinding("schema", "Agents/logs/log-vault-docs-2026-09-27.md", "error", "'date' missing")
        self.assertFinding("pii", "Agents/logs/log-vault-pm-2026-09-27.md", "error", "SSN")

    def test_legacy_documents_folder_not_exempt(self):
        self.put("_attachments/documents/old-scan.pdf", "pdf")
        self.assertFinding("attachments", "_attachments/documents/old-scan.pdf", "warning", "matches no note")

    def test_one_word_project_title(self):
        p = self.root / "Projects/settle-the-estate.md"
        s = p.read_text().replace("title: Settle the estate", "title: Estate").replace("# Settle the estate", "# Estate")
        p.write_text(s)
        self.assertFinding("projects", "Projects/settle-the-estate.md", "warning", "2–6")

    def _store_note(self):
        self.put("Resources/store-view.md", "---\ntitle: Store view\ntype: reference\n---\n\n# Store view\n\n"
                 "![[_files/some-note/scan.pdf]]\n")

    def test_store_link_resolves(self):
        store = self.root.parent / (self.root.name + "-store")
        (store / "some-note").mkdir(parents=True)
        (store / "some-note/scan.pdf").write_bytes(b"pdf")
        os.symlink(store, self.root / "_files")
        self._store_note()
        found = [f for f in self.findings("links") if f["path"] == "Resources/store-view.md"]
        self.assertEqual(found, [], json.dumps(found, indent=1, ensure_ascii=False))

    def test_store_link_missing_file(self):
        store = self.root.parent / (self.root.name + "-store")
        store.mkdir()
        os.symlink(store, self.root / "_files")
        self._store_note()
        self.assertFinding("links", "Resources/store-view.md", "error", "not found in the file store")

    def test_store_not_attached(self):
        (self.root / "_files").mkdir()  # an empty real folder, as Sync leaves on other devices
        self._store_note()
        self.assertFinding("links", "_files/", "info", "not attached here; 1 link(s) in 1 note(s) not checked")

    def _locked_store(self):
        """An image exists but isn't mounted: the store's folder is the bare mount point."""
        image = self.root.parent / (self.root.name + "-image.sparsebundle")
        image.mkdir()
        self.addCleanup(os.environ.__setitem__, "VAULT_FILES_IMAGE", os.environ["VAULT_FILES_IMAGE"])
        os.environ["VAULT_FILES_IMAGE"] = str(image)
        return self._attach_store()

    def test_store_locked(self):
        self._locked_store()
        self._store_note()
        self.assertFinding("links", "_files/", "info", "locked")

    def test_store_move_refuses_locked_store(self):
        self._locked_store()
        (self.root / ".scripts").mkdir()
        for name in ("vault-lint", "store-move"):
            shutil.copy2(HERE.parent / name, self.root / ".scripts" / name)
        res = subprocess.run([sys.executable, str(self.root / ".scripts/store-move"), "--dry-run"],
                             cwd=self.root, capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("locked", res.stderr)

    def _attach_store(self):
        store = self.root.parent / (self.root.name + "-store")
        store.mkdir(exist_ok=True)
        os.symlink(store, self.root / "_files")
        return store

    def _store_manifest(self, filed, data=b"%PDF-1.4 real\n"):
        import hashlib
        header = "sha256\tsize\tfiled_path\toriginal_path\toriginal_name\timported\n"
        self.put("_attachments/_raw/manifest.tsv", header +
                 f"{hashlib.sha256(data).hexdigest()}\t{len(data)}\t{filed}\t~/Downloads/Receipt.pdf\tReceipt.pdf\t2026-09-27\n")

    def test_store_manifest_row_checked_when_attached(self):
        store = self._attach_store()
        (store / "kettlebell-plan").mkdir()
        (store / "kettlebell-plan/receipt-2026.pdf").write_bytes(b"%PDF-1.4 real\n")
        self._store_manifest("_files/kettlebell-plan/receipt-2026.pdf")
        _, found = lint_json(self.root, "--only", "manifest")
        self.assertEqual(found, [], json.dumps(found, indent=1))
        (store / "kettlebell-plan/receipt-2026.pdf").unlink()
        self.assertFinding("manifest", "_attachments/_raw/manifest.tsv", "error", "filed file missing: _files/")

    def test_store_manifest_row_skipped_when_not_attached(self):
        self._store_manifest("_files/kettlebell-plan/receipt-2026.pdf")
        self.assertFinding("manifest", "_attachments/_raw/manifest.tsv", "info", "store isn't attached")

    def test_store_file_follows_attachment_rules(self):
        store = self._attach_store()
        (store / "no-such-note").mkdir()
        (store / "no-such-note/scan.pdf").write_bytes(b"pdf")
        self.assertFinding("attachments", "_files/no-such-note/scan.pdf", "warning", "matches no note")

    def test_document_in_attachments_belongs_in_store(self):
        self._attach_store()
        self.assertFinding("attachments", "_attachments/kettlebell-plan/", "info", "belong in the file store")

    def test_no_store_hint_without_store(self):
        found = [f for f in self.findings("attachments") if "file store" in f["message"]]
        self.assertEqual(found, [], json.dumps(found, indent=1))

    def test_store_move_moves_verifies_and_relinks(self):
        import hashlib
        store = self._attach_store()
        (self.root / ".scripts").mkdir()
        for name in ("vault-lint", "store-move"):
            shutil.copy2(HERE.parent / name, self.root / ".scripts" / name)
        data = (self.root / "_attachments/kettlebell-plan/scan.pdf").read_bytes()
        self._store_manifest("_attachments/kettlebell-plan/scan.pdf", data)
        self.put("_attachments/kettlebell-plan/photo.png", "small image")
        log = "Agents/logs/log-vault-intake-2026-09-26.md"
        if (self.root / log).exists():
            before_log = (self.root / log).read_text()
        res = subprocess.run([sys.executable, str(self.root / ".scripts/store-move")],
                             cwd=self.root, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertEqual((store / "kettlebell-plan/scan.pdf").read_bytes(), data)
        self.assertFalse((self.root / "_attachments/kettlebell-plan/scan.pdf").exists())
        self.assertTrue((store / "kettlebell-plan/photo.png").exists())  # small images move too
        note = (self.root / "Resources/kettlebell-plan.md").read_text()
        self.assertIn("![[_files/kettlebell-plan/scan.pdf]] and ![[_files/kettlebell-plan/scan.pdf]]", note)
        self.assertIn("\t_files/kettlebell-plan/scan.pdf\t", (self.root / "_attachments/_raw/manifest.tsv").read_text())
        self.assertIn(hashlib.sha256(data).hexdigest(), (self.root / "_attachments/_raw/manifest.tsv").read_text())
        if (self.root / log).exists():
            self.assertEqual((self.root / log).read_text(), before_log)
        # A second run finds nothing to do.
        res = subprocess.run([sys.executable, str(self.root / ".scripts/store-move"), "--dry-run"],
                             cwd=self.root, capture_output=True, text=True)
        self.assertIn("Would move 0 file(s)", res.stdout)

    def test_agent_task_assigned_to_a_role(self):
        self.put("Agents/roles/role-vault-ops.md", "---\ntitle: \"Role: vault ops\"\ntype: manual\n---\n# Role: vault ops\n")
        self.put("Tasks/refresh-the-budget.md", "---\ntitle: Refresh the budget\nstatus: waiting-for\narea:\n  - \"[[money]]\"\n"
                 "assignee:\n  - \"[[role-vault-ops]]\"\nwaiting_on: \"[[role-vault-ops]]\"\n"
                 "waiting_since: 2026-09-26\ncreated: 2026-09-26\n---\n# Refresh the budget\n")
        found = [f for f in self.findings("relations,waiting-on") if f["path"] == "Tasks/refresh-the-budget.md"]
        self.assertEqual(found, [], json.dumps(found, indent=1))

    def test_assignee_other_manual_page_rejected(self):
        self.put("Tasks/read-the-rules.md", "---\ntitle: Read the rules\nstatus: inbox\nassignee:\n  - \"[[style-guide]]\"\n"
                 "created: 2026-09-26\n---\n# Read the rules\n")
        self.assertFinding("relations", "Tasks/read-the-rules.md", "error", "'assignee'")

    def test_store_private_folder_skipped(self):
        store = self._attach_store()
        (store / "_private").mkdir()
        (store / "_private/pii-register-draft.md").write_text("# Draft\n")
        (store / "_private/scan.pdf").write_bytes(b"pdf")
        found = [f for f in self.findings("attachments,links,manifest") if "_private" in f["path"]]
        self.assertEqual(found, [], json.dumps(found, indent=1))

    def test_public_places_skips_addresses_and_phones_only(self):
        body = "| Dream Inn | 175 W Cliff Dr, Santa Cruz | 831-555-0199 |\nOwner email jane.doe@gmail.com\n"
        self.put("Resources/saved-places.md", "---\ntitle: Saved places\ntype: list\npublic_places: true\n---\n# Saved places\n\n" + body)
        found = [f for f in self.findings("pii") if f["path"] == "Resources/saved-places.md"]
        self.assertEqual([f["message"].split(" (")[0] for f in found], ["email address"], json.dumps(found, indent=1))

    def test_pii_business_exemptions(self):
        self.put("Agents/pii-allowlist.md", "---\ntitle: PII allowlist\ntype: manual\n---\n# PII allowlist\n\n- `acmelaw.com` — Acme Law\n")
        self.put("Resources/case-notes.md", "---\ntitle: Case notes\ntype: reference\n---\n# Case notes\n\n"
                 "Tim at the firm: tim@acmelaw.com. Write to paralegal@otherfirm.com.\n"
                 "Billed by Hand Surgery Group, NPI 1234567893.\n"
                 "Our cat Chloe, born May 3, 1995.\n"
                 "Jane's email jane@acme-mail.net. Tom, DOB 03/05/1985.\n")
        found = sorted(f["message"].split(" (")[0] for f in self.findings("pii") if f["path"] == "Resources/case-notes.md")
        self.assertEqual(found, ["date of birth", "email address"], found)

    def test_dataviewjs_block(self):
        self.put("Resources/js-view.md", "---\ntitle: JS view\ntype: reference\n---\n\n# JS view\n\n"
                 "```dataviewjs\ndv.list([])\n```\n")
        self.assertFinding("dataviewjs", "Resources/js-view.md", "error", "dataviewjs block")

    def test_dataviewjs_inline_query(self):
        self.put("Resources/js-inline.md", "---\ntitle: JS inline\ntype: reference\n---\n\n# JS inline\n\n"
                 "Count: `$= dv.pages().length`\n")
        self.assertFinding("dataviewjs", "Resources/js-inline.md", "error", "inline DataviewJS")

    def test_dataviewjs_on_home_only_view_calls(self):
        home = self.root / "Home.md"
        home.write_text(home.read_text() + "\n" + self.VIEW_CALL)
        found = [f for f in self.findings("dataviewjs") if f["path"] == "Home.md"]
        self.assertEqual(found, [], json.dumps(found, indent=1))
        home.write_text(home.read_text() + "\n```dataviewjs\ndv.list([])\n```\n")
        self.assertFinding("dataviewjs", "Home.md", "error", "dataviewjs block")

    TEMPLATE_HEAD = "---\ntitle: Odd template\ntype: template\n---\n\n# Odd template\n\nPart of the [[README]].\n\n"

    def test_templater_shipped_templates_pass(self):
        found = self.findings("templater")
        self.assertEqual(found, [], json.dumps(found, indent=1))

    def test_templater_foreign_script_block(self):
        self.put("Agents/templates/template-odd.md", self.TEMPLATE_HEAD +
                 "<%*\ntR = \"\";\nawait app.vault.adapter.write(\"x.md\", \"y\");\n-%>\n")
        self.assertFinding("templater", "Agents/templates/template-odd.md", "error", "script block")

    def test_templater_foreign_commands(self):
        self.put("Agents/templates/template-odd.md", self.TEMPLATE_HEAD +
                 "<% tp.user.run() %>\n<%+ tp.file.content %>\n"
                 "<% tp.system.prompt(\"a\" + require(\"child_process\")) %>\n<% title ")
        msgs = [f["message"] for f in self.findings("templater") if f["path"] == "Agents/templates/template-odd.md"]
        self.assertEqual(len(msgs), 4, msgs)
        self.assertTrue(any("unclosed" in m for m in msgs), msgs)

    def test_templater_kit_script_with_other_prompt_passes(self):
        self.put("Agents/templates/template-odd.md", self.TEMPLATE_HEAD +
                 "<%*\ntR = \"\";\nlet title = tp.file.title;\n"
                 "if (title.startsWith(\"Untitled\")) title = await tp.system.prompt(\"Recipe name\");\n"
                 + VL._TP_SLUG + "\nawait tp.file.move(\"Resources/\" + slug);\n-%>\n<% title %>\n")
        found = [f for f in self.findings("templater") if f["path"] == "Agents/templates/template-odd.md"]
        self.assertEqual(found, [], json.dumps(found, indent=1))

    VIEW_CALL = "```dataviewjs\nawait dv.view(\"Agents/views/task-status\", {status: \"next-action\", columns: \"due\"})\n```\n"

    def test_dataviewjs_view_call_allowed_anywhere(self):
        self.put("Resources/js-view-call.md", "---\ntitle: JS view call\ntype: reference\n---\n\n# JS view call\n\n"
                 "## Tasks\n\n" + self.VIEW_CALL + "\n```dataviewjs\nawait dv.view(\"Agents/views/task-status\")\n```\n"
                 "\n```dataviewjs\nawait dv.view(\"Agents/views/week-ahead\", {days: \"7\"})\n```\n")
        found = [f for f in self.findings("dataviewjs") if f["path"] == "Resources/js-view-call.md"]
        self.assertEqual(found, [], json.dumps(found, indent=1))

    def test_dataviewjs_view_call_with_extra_code(self):
        for body in ("await dv.view(\"Agents/views/task-status\")\napp.vault.getFiles()",
                     "await dv.view(\"Resources/other\")",
                     "await dv.view(\"Agents/views/../x\")",
                     "await dv.view(\"Agents/views/task-status\", {status: dv.pages()})",
                     "await dv.view(\"Agents/views/task-status\", {status: \"a\" + x})"):
            self.put("Resources/js-bad-call.md", "---\ntitle: JS bad call\ntype: reference\n---\n\n# JS bad call\n\n"
                     "```dataviewjs\n" + body + "\n```\n")
            self.assertFinding("dataviewjs", "Resources/js-bad-call.md", "error", "dataviewjs block")

    def test_view_call_counts_as_tasks_block(self):
        self.put("Projects/view-tasks.md", "---\ntitle: View tasks\nphase: not-started\ncreated: 2026-09-20\n"
                 "area:\n  - \"[[health]]\"\n---\n# View tasks\n\nDone when: it renders.\n\n"
                 "## Tasks\n\n" + self.VIEW_CALL)
        found = [f for f in self.findings("anatomy") if f["path"] == "Projects/view-tasks.md"]
        self.assertEqual(found, [], json.dumps(found, indent=1))

    def test_view_scripts_allowed_in_agents_views(self):
        self.put("Agents/views/task-status/view.js", "dv.table([], [])\n")
        self.put("Agents/views/task-status/view.css", ".task-status {}\n")
        self.put("Agents/views/stray.js", "// wrong place\n")
        found = [f for f in self.findings("structure") if f["path"].startswith("Agents/views/")]
        self.assertEqual([f["path"] for f in found], ["Agents/views/stray.js"], json.dumps(found, indent=1))

    def test_dataviewjs_in_drop_folder(self):
        self.put("_captures/pasted.md", "Looks harmless\n\n```dataviewjs\napp.vault.getFiles()\n```\n")
        self.assertFinding("dataviewjs", "_captures/pasted.md", "warning", "drop-folder")

    def test_title_ending_in_question_mark(self):
        self.put("Resources/why-bother.md", "---\ntitle: Why bother?\ntype: reference\n---\n\n# Why bother?\n")
        self.assertFinding("title", "Resources/why-bother.md", "warning", "ends with punctuation")

    def test_templater_tag_outside_templates(self):
        self.put("Resources/half-made.md", "---\ntitle: Half made\ntype: reference\n---\n\n# Half made\n\n"
                 "Made <% tp.date.now() %>.\n")
        self.assertFinding("templater", "Resources/half-made.md", "error", "outside Agents/templates/")

    def test_templater_tag_in_code_fence_and_log(self):
        # Templater runs tags inside code fences too, and run logs are new files an agent writes.
        self.put("Resources/fenced.md", "---\ntitle: Fenced\ntype: reference\n---\n\n# Fenced\n\n"
                 "```js\n<%* require(\"child_process\") %>\n```\n")
        self.assertFinding("templater", "Resources/fenced.md", "error", "outside Agents/templates/")
        self.put("Agents/logs/log-vault-intake-2026-10-01.md", "---\ntitle: \"Log: vault intake — 2026-10-01\"\n"
                 "type: log\n---\n\n# Log\n\nQuoted: <%+ tp.file.content %>\n")
        self.assertFinding("templater", "Agents/logs/log-vault-intake-2026-10-01.md", "error", "outside Agents/templates/")

    def test_templater_neutralized_tag_passes(self):
        self.put("Resources/safe.md", "---\ntitle: Safe\ntype: reference\n---\n\n# Safe\n\nShown: &lt;% x %>\n")
        found = [f for f in self.findings("templater") if f["path"] == "Resources/safe.md"]
        self.assertEqual(found, [], json.dumps(found, indent=1))

    def test_templater_in_drop_folder(self):
        self.put("_imports/downloaded.md", "Notes\n\n<%* await app.vault.adapter.write(\"x\", \"y\") %>\n")
        self.assertFinding("templater", "_imports/downloaded.md", "warning", "drop-folder")


class Config(unittest.TestCase):
    """.tidyvault.yml: the restricted YAML parser, module switches, and owner-aware messages."""

    def test_parser(self):
        cfg = VL.parse_config(
            "# comment\nkit_version: 0.1.0\nowner: \"Robin: R\"\nmodules:\n  - store\n  - pii\n"
            "empty: []\n\nlint:\n  proper_nouns:\n    - Acme\n    - \"Big Co\"\n  disabled_checks: []\n"
            "  mode: strict\n")
        self.assertEqual(cfg["kit_version"], "0.1.0")
        self.assertEqual(cfg["owner"], "Robin: R")
        self.assertEqual(cfg["modules"], ["store", "pii"])
        self.assertEqual(cfg["empty"], [])
        self.assertEqual(cfg["lint"], {"proper_nouns": ["Acme", "Big Co"], "disabled_checks": [], "mode": "strict"})

    def test_parser_rejects_bad_lines(self):
        for bad in ("- orphan item\n", "no colon here\n", "a:\n      deep: x\n"):
            with self.assertRaises(ValueError, msg=bad):
                VL.parse_config(bad)

    def test_defaults_without_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = VL.load_config(tmp)
        self.assertEqual(cfg["modules"], set(VL.MODULES))
        self.assertEqual(cfg["owner"], "the owner")
        self.assertEqual(cfg["read_only_url_patterns"], [])

    def _vault(self, modules, extra=""):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "v"
        shutil.copytree(FIX / "good", root)
        lines = "".join(f"  - {m}\n" for m in modules)
        (root / VL.CONFIG_FILE).write_text(f"owner: Robin\nowner_full: Robin Vale\nowner_slug: robin-vale\n"
                                           f"modules:\n{lines}{extra}")
        return root

    def test_store_and_pii_off(self):
        root = self._vault(["obsidian"])
        (root / "_files").mkdir()
        (root / "Tasks/call-the-lawyer.md").write_text(
            (root / "Tasks/call-the-lawyer.md").read_text() + "\nSSN 123-45-6789\n")
        _, found = lint_json(root)
        self.assertFalse([f for f in found if f["check"] in ("pii", "sensitive", "manifest", "attachments")],
                         json.dumps(found, indent=1))

    def test_disabled_checks(self):
        root = self._vault(["store", "pii"], "lint:\n  disabled_checks:\n    - orphans\n")
        (root / "Resources/nobody-links-me.md").write_text(
            "---\ntitle: Nobody links me\ntype: reference\n---\n\n# Nobody links me\n")
        _, found = lint_json(root)
        self.assertFalse([f for f in found if f["check"] == "orphans"], json.dumps(found, indent=1))

    def test_list_checks_marks_modules(self):
        root = self._vault(["store"], "lint:\n  disabled_checks:\n    - orphans\n")
        _, out, _ = lint(root, "--list-checks")
        rows = {line.split()[0]: line for line in out.splitlines() if line.strip()}
        self.assertIn("(off: module pii is off)", rows["pii"])
        self.assertIn("(off: module pii is off)", rows["sensitive"])
        self.assertIn("(off: module false-facts is off)", rows["facts"])
        self.assertIn("(off: lint.disabled_checks)", rows["orphans"])
        self.assertNotIn("(off", rows["manifest"])

    def test_owner_name_in_messages(self):
        root = self._vault(["store", "pii"])
        (root / "Tasks/ask-myself.md").write_text(
            "---\ntitle: Ask myself\nstatus: inbox\nassignee:\n  - \"[[robin-vale]]\"\n---\n\n# Ask myself\n")
        _, found = lint_json(root, "--only", "tasks")
        self.assertTrue(any("other than Robin" in f["message"] for f in found), json.dumps(found, indent=1))

    def test_proper_nouns_from_config(self):
        root = self._vault(["store", "pii"], "lint:\n  proper_nouns:\n    - Northwind\n    - Lisbon\n")
        (root / "Resources/visit-northwind-in-lisbon-soon.md").write_text(
            "---\ntitle: Visit Northwind in Lisbon soon\ntype: reference\n---\n\n# Visit Northwind in Lisbon soon\n")
        _, found = lint_json(root, "--only", "title")
        self.assertFalse([f for f in found if "Title Case" in f["message"]], json.dumps(found, indent=1))

    def test_proper_phrases_from_config(self):
        root = self._vault(["store", "pii"], "lint:\n  proper_phrases:\n    - Big Blue Widget Co\n")
        (root / "Resources/visit-big-blue-widget-co-labs.md").write_text(
            "---\ntitle: Visit Big Blue Widget Co labs\ntype: reference\n---\n\n# Visit Big Blue Widget Co labs\n")
        _, found = lint_json(root, "--only", "title")
        self.assertFalse([f for f in found if "Title Case" in f["message"]], json.dumps(found, indent=1))

    def test_read_only_url_patterns(self):
        root = self._vault(["store", "pii"], "lint:\n  read_only_url_patterns:\n    - old-wiki\\.example\n")
        (root / "Resources/imported-page.md").write_text(
            "---\ntitle: Imported page\ntype: reference\nsource: https://old-wiki.example/p/1\n---\n\n"
            "# Imported page\n\nWas https://old-wiki.example/p/1.\n")
        _, found = lint_json(root, "--only", "source-urls")
        sev = sorted(f["severity"] for f in found if f["path"] == "Resources/imported-page.md")
        self.assertEqual(sev, ["error", "info"], json.dumps(found, indent=1))

    def test_retired_fields_from_config(self):
        root = self._vault(["store", "pii"], "lint:\n  retired_fields:\n    - old_id\n")
        (root / "Tasks/old-import.md").write_text(
            "---\ntitle: Old import\nstatus: inbox\narea:\n  - \"[[health]]\"\nold_id: abc\n---\n\n# Old import\n")
        _, found = lint_json(root, "--only", "schema")
        self.assertTrue(any("retired field 'old_id'" in f["message"] for f in found), json.dumps(found, indent=1))
        lint(root, "--fix", "Tasks/old-import.md")
        self.assertNotIn("old_id", (root / "Tasks/old-import.md").read_text())



class Migration(unittest.TestCase):
    """What a vault that adopts the kit will carry: a local layer, retired fields, read-only sources."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "v"
        shutil.copytree(FIX / "good", self.root)
        (self.root / VL.CONFIG_FILE).write_text(
            "owner: Robin\nowner_full: Robin Vale\nowner_slug: robin-vale\nmodules:\n  - store\n  - pii\n  - false-facts\n  - obsidian\n"
            "lint:\n  proper_nouns:\n    - Northwind\n    - Dental\n    - Labs\n  retired_fields:\n    - old_id\n    - old_db\n"
            "  read_only_url_patterns:\n    - old-wiki\\.example\n")

    def put(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def errors(self, *args):
        _, found = lint_json(self.root, *args)
        return [f for f in found if f["severity"] == "error"]

    def test_local_layer_lints_clean(self):
        self.put("Agents/local/local-rules.md", "---\ntitle: Local rules\ntype: manual\n---\n# Local rules\n\n"
                 "Part of the [[README]]. This vault's own rules.\n\n## Rules\n\n- **L1. The old wiki is read-only.**\n")
        self.put("Agents/local/roles/role-vault-ops-local.md", "---\ntitle: \"Role: vault ops (local)\"\ntype: manual\n---\n"
                 "# Role: vault ops (local)\n\nPart of the [[README]]. Modes this vault adds.\n\n## Mode: Mail\n\nTriage the inbox.\n")
        self.put("Agents/local/external-systems-local.md", "---\ntitle: External systems (local)\ntype: manual\n---\n"
                 "# External systems (local)\n\nPart of the [[README]]. This vault's systems.\n\n| System | Owns |\n|---|---|\n| Old wiki | nothing |\n")
        self.assertEqual(self.errors(), [], json.dumps(self.errors(), indent=1))

    def test_role_pages_outside_their_homes_are_errors(self):
        self.put("Agents/local/role-stray.md", "---\ntitle: \"Role: stray\"\ntype: manual\n---\n# Role: stray\n\nPart of the [[README]].\n")
        self.put("Agents/local/roles/role-vault-ops.md", "---\ntitle: \"Role: vault ops\"\ntype: manual\n---\n# Role: vault ops\n\nPart of the [[README]].\n")
        paths = sorted(f["path"] for f in self.errors("--only", "structure"))
        self.assertEqual(paths, ["Agents/local/role-stray.md", "Agents/local/roles/role-vault-ops.md"], paths)

    def test_retired_fields_from_old_system_are_fixed(self):
        self.put("Tasks/answer-the-wiki-question.md", "---\ntitle: Answer the wiki question\nstatus: inbox\narea:\n  - \"[[health]]\"\n"
                 "old_id: abc123\nold_db: Tasks\ncreated: 2026-10-01\n---\n# Answer the wiki question\n\n## Details\n\n"
                 "**Question**:: keep the old page? Source https://old-wiki.example/p/9\n")
        msgs = sorted(f["message"] for f in self.errors("--only", "schema"))
        self.assertEqual(msgs, ["retired field 'old_db'", "retired field 'old_id'"], msgs)
        _, found = lint_json(self.root, "--only", "source-urls")
        self.assertEqual([f["severity"] for f in found], ["info"], found)
        lint(self.root, "--fix", "Tasks/answer-the-wiki-question.md")
        text = (self.root / "Tasks/answer-the-wiki-question.md").read_text()
        self.assertNotIn("old_id", text); self.assertNotIn("old_db", text)
        self.assertIn("**Question**:: keep the old page?", text)
        self.assertEqual(self.errors(), [], json.dumps(self.errors(), indent=1))

    def test_read_only_source_in_frontmatter_is_an_error(self):
        self.put("Resources/imported-page.md", "---\ntitle: Imported page\ntype: reference\nsource: https://old-wiki.example/p/1\n---\n"
                 "# Imported page\n\nWas elsewhere.\n")
        self.assertEqual([f["check"] for f in self.errors("--only", "source-urls")], ["source-urls"])

    def test_proper_nouns_from_config(self):
        self.put("Resources/visit-northwind-dental-labs.md", "---\ntitle: Visit Northwind Dental Labs\ntype: reference\n---\n"
                 "# Visit Northwind Dental Labs\n")
        _, found = lint_json(self.root, "--only", "title")
        self.assertFalse([f for f in found if "Title Case" in f["message"]], json.dumps(found, indent=1))
        (self.root / VL.CONFIG_FILE).write_text("owner: Robin\nlint:\n  proper_nouns: []\n")
        _, found = lint_json(self.root, "--only", "title")
        self.assertTrue([f for f in found if "Title Case" in f["message"]], "without the config the title reads as Title Case")


class LocalLayerAndMigration(unittest.TestCase):
    """What a vault adds on top of the kit (Agents/local/), and the shape a migrated vault takes:
    retired fields from an old system, read-only source URLs, a question task, local role modes."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "v"
        shutil.copytree(FIX / "good", self.root)
        (self.root / VL.CONFIG_FILE).write_text(
            "owner: Robin\nowner_full: Robin Vale\nowner_slug: robin-vale\nvault: v\n"
            "modules:\n  - store\n  - pii\n  - false-facts\n  - obsidian\n"
            "lint:\n  read_only_url_patterns:\n    - old-wiki\\.example\n  retired_fields:\n    - old_id\n    - old_db\n")

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def lint(self, *args):
        return lint_json(self.root, *args)

    def test_local_layer_lints_clean(self):
        self.put("Agents/local/local-rules.md",
                 "---\ntitle: Local rules\ntype: manual\n---\n# Local rules\n\nPart of the [[README]].\n\n## Rules\n\n"
                 "- **L1. The old wiki is read-only.** Its URLs are in the lint config.\n")
        self.put("Agents/local/roles/role-vault-ops-local.md",
                 "---\ntitle: \"Role: vault ops (local)\"\ntype: manual\n---\n# Role: vault ops (local)\n\n"
                 "Part of the [[README]]. Modes this vault adds.\n\n## Mode: Mail\n\nTriage the inbox.\n")
        self.put("Agents/local/external-systems-local.md",
                 "---\ntitle: External systems (local)\ntype: manual\n---\n# External systems (local)\n\n"
                 "Part of the [[README]].\n\n| System | Owns | Agents may | Agents may not |\n|---|---|---|---|\n| Old wiki | Nothing | Read | Write |\n")
        code, found = self.lint()
        self.assertEqual([f for f in found if f["severity"] != "info"], [], json.dumps(found, indent=1))

    def test_role_page_outside_roles_or_local_roles_is_an_error(self):
        self.put("Agents/local/role-stray.md", "---\ntitle: \"Role: stray\"\ntype: manual\n---\n# Role: stray\n\nPart of the [[README]].\n")
        _, found = self.lint("--only", "structure")
        self.assertTrue(any(f["path"] == "Agents/local/role-stray.md" and "role-<name>-local.md" in f["message"] for f in found),
                        json.dumps(found, indent=1))

    def test_migrated_task_shape(self):
        self.put("Tasks/answer-the-wiki-question.md",
                 "---\ntitle: Answer the wiki question\nstatus: inbox\narea:\n  - \"[[health]]\"\nold_id: abc123\nold_db: Tasks\ncreated: 2026-10-01\n---\n"
                 "# Answer the wiki question\n\n## Details\n\n**Question**:: keep the old wiki page? Source https://old-wiki.example/p/9\n")
        _, found = self.lint("--only", "schema,source-urls")
        msgs = [(f["check"], f["severity"]) for f in found if f["path"] == "Tasks/answer-the-wiki-question.md"]
        self.assertIn(("schema", "error"), msgs, json.dumps(found, indent=1))      # the old system's fields
        self.assertIn(("source-urls", "info"), msgs, json.dumps(found, indent=1))  # its URL in the body: info only
        lint(self.root, "--fix", "Tasks/answer-the-wiki-question.md")
        text = (self.root / "Tasks/answer-the-wiki-question.md").read_text()
        self.assertNotIn("old_id", text); self.assertNotIn("old_db", text)
        self.assertIn("**Question**:: keep", text)
        _, found = self.lint("--only", "schema")
        self.assertFalse([f for f in found if f["path"] == "Tasks/answer-the-wiki-question.md"], json.dumps(found, indent=1))

    def test_source_url_in_frontmatter_is_an_error(self):
        self.put("Resources/imported-page.md",
                 "---\ntitle: Imported page\ntype: reference\nurl: https://old-wiki.example/p/1\n---\n\n# Imported page\n\nText.\n")
        _, found = self.lint("--only", "source-urls")
        self.assertTrue(any(f["path"] == "Resources/imported-page.md" and f["severity"] == "error" for f in found), json.dumps(found, indent=1))


class RealVault(unittest.TestCase):
    def test_runs_fast_and_emits_json(self):
        import time
        root = HERE.parent.parent
        t = time.time()
        code, findings = lint_json(root)
        self.assertLess(time.time() - t, 5.0)
        self.assertIn(code, (0, 1))
        self.assertIsInstance(findings, list)

    def test_review_runs(self):
        root = HERE.parent.parent
        p = subprocess.run([sys.executable, str(LINT), "--root", str(root), "--review", "--json"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("project_rule", json.loads(p.stdout))



class TaskStatusView(unittest.TestCase):
    """Agents/views/task-status/view.js writes task frontmatter in schema order (body-sections, Task status view)."""

    def test_key_order_matches_schema(self):
        mod = load_module()
        js = (HERE.parent.parent / "Agents" / "views" / "task-status" / "view.js").read_text()
        m = re.search(r"const KEY_ORDER = \[(.*?)\];", js, re.S)
        self.assertIsNotNone(m, "view.js has no KEY_ORDER")
        in_js = re.findall(r'"([a-z_]+)"', m.group(1))
        expected = [k for k, _ in mod.COMMON_HEAD + mod.FOLDER_FIELDS["Tasks"] + mod.COMMON_TAIL]
        self.assertEqual(in_js, expected)
        self.assertIn("reorder(fm);", js)


if __name__ == "__main__":
    unittest.main(verbosity=1)
