#!/usr/bin/env python3
"""Tests for vault-brief, sort-inbox, pm-check.  Run: python3 .scripts/tests/test_brief_scripts.py

Each test copies fixtures/good (a mini vault) to a temp dir, adds a few files,
and runs the script against it with --root and a fixed --today.
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
GOOD = HERE / "fixtures" / "good"
TODAY = "2026-10-05"


def task(title, status, **kw):
    fm = {"title": title, "status": status, **kw}
    out = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            out.append(f"{k}:")
            out += [f'  - "{x}"' for x in v]
        else:
            out.append(f"{k}: {v}")
    out += ["---", f"# {title}", ""]
    return "\n".join(out)


class Vault(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "vault"
        shutil.copytree(GOOD, self.root)
        self.addCleanup(self.tmp.cleanup)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def run_script(self, name, *args):
        p = subprocess.run([sys.executable, str(SCRIPTS / name), *args, "--root", str(self.root)],
                           capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr

    def snapshot(self):
        return {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}


class BriefTests(Vault):
    def setUp(self):
        super().setUp()
        self.write("Tasks/answer-the-questions.md",
                   "---\ntitle: Answer the questions\nstatus: inbox\narea:\n  - \"[[health]]\"\ncreated: 2026-09-28\n---\n"
                   "# Answer the questions\n\n## Details\n\n**Question**:: what was the charge?\n")
        self.write("Tasks/triage-mail.md",
                   "---\ntitle: Triage mail\nstatus: inbox\narea:\n  - \"[[health]]\"\ncreated: 2026-09-29\n---\n# Triage mail\n")
        self.write("Tasks/fix-the-wording.md",
                   "---\ntitle: Fix the wording\nstatus: next-action\narea:\n  - \"[[health]]\"\ncontexts:\n  - anywhere\n"
                   "assignee:\n  - \"[[role-vault-admin]]\"\ncreated: 2026-09-28\n---\n# Fix the wording\n")
        self.write("Agents/roles/role-vault-admin.md", "---\ntitle: \"Role: vault admin\"\ntype: manual\n---\n# Role: vault admin\n")

    def brief(self, *args):
        code, out, err = self.run_script("vault-brief", "--today", TODAY, *args)
        self.assertEqual(code, 0, err)
        return out

    def test_sections(self):
        out = self.brief()
        self.assertIn("## Overdue (1)", out)
        self.assertIn("[[call-the-lawyer]]", out.split("## Due within 2 days")[0])
        self.assertIn("2 inbox tasks; 1 are question tasks, 1 to clarify.", out)

    def test_question_count_never_prints_question(self):
        out = self.brief()
        self.assertIn("Waiting on you: 1 questions on Home.", out)
        self.assertNotIn("what was the charge", out)

    def test_candidates_ranked(self):
        out = self.brief()
        cand = out.split("## Candidate next actions")[1].split("## Inbox")[0]
        self.assertLess(cand.index("call-the-lawyer"), cand.index("stretch-daily"))  # high before no priority

    def test_stale_waiting_and_agent_tasks(self):
        out = self.brief()
        self.assertIn("[[chase-the-bank]]", out.split("## Stale waiting-for")[1].split("## Agent tasks")[0])
        self.assertIn("[[fix-the-wording]] — Fix the wording (role-vault-admin, 7 days)", out)

    def test_week_ahead_groups_by_day(self):
        self.write("Tasks/pay-the-fee.md", task("Pay the fee", "next-action", due="2026-10-10", contexts=["anywhere"],
                                                 area=["[[health]]"]))
        out = self.brief()
        self.assertIn("### Sat Oct 10", out.split("## Week ahead")[1])
        self.assertIn("[[pay-the-fee]]", out.split("## Week ahead")[1])

    def test_snapshot_facts(self):
        self.write("Tasks/pay-the-fee.md", task("Pay the fee", "next-action", due="2026-10-10", contexts=["anywhere"],
                                                 area=["[[health]]"]))
        code, out, err = self.run_script("vault-brief", "--today", TODAY, "--snapshot-facts")
        self.assertEqual(code, 0, err)
        self.assertIn("Deadline (task): [[pay-the-fee]]", out)
        self.assertIn("Project in focus: [[settle-the-estate]]", out)
        self.assertNotIn("call-the-lawyer", out)  # overdue: not a coming-week fact

    def test_never_writes(self):
        before = self.snapshot()
        self.brief()
        self.run_script("vault-brief", "--today", TODAY, "--snapshot-facts")
        self.assertEqual(before, self.snapshot())


class SortInboxTests(Vault):
    def setUp(self):
        super().setUp()
        self.write("Tasks/book-the-flight.md",
                   "---\ntitle: Book the flight\nstatus: inbox\nproject: \"[[settle-the-estate]]\"\narea:\n  - \"[[health]]\"\ndue: 2026-10-20\ncreated: 2026-09-20\n---\n# Book the flight\n")
        self.write("Tasks/think-about-gym.md", "---\ntitle: Think about gym\nstatus: inbox\ncreated: 2026-09-21\n---\n# Think about gym\n")
        self.write("Tasks/ask-the-doctor.md",
                   "---\ntitle: Ask the doctor\nstatus: inbox\nproject: \"[[ghost-project]]\"\ncreated: 2026-09-22\n---\n# Ask the doctor\n")
        self.write("Tasks/pick-a-plan.md",
                   "---\ntitle: Pick a plan\nstatus: inbox\ncreated: 2026-09-23\n---\n# Pick a plan\n\n**Question**:: which?\n\n**Answer**:: the second\n")

    def test_groups_and_writes_nothing(self):
        before = self.snapshot()
        code, out, err = self.run_script("sort-inbox")
        self.assertEqual(code, 0, err)
        self.assertEqual(before, self.snapshot())
        signals = out.split("## Explicit signals")[1].split("## Needs judgment")[0]
        judge = out.split("## Needs judgment")[1]
        self.assertIn("project [[settle-the-estate]] (in-progress)", signals)
        self.assertIn("due 2026-10-20", signals)
        self.assertIn("delete `area` (project set)", signals)
        self.assertIn("[[think-about-gym]]", judge)
        self.assertIn("project [[ghost-project]] not found", judge)
        self.assertIn("[[pick-a-plan]] — answered", out)
        self.assertIn("List-only", out)

    def test_oldest_first(self):
        _, out, _ = self.run_script("sort-inbox")
        self.assertLess(out.index("book-the-flight"), out.index("think-about-gym"))


class PmCheckTests(Vault):
    def check(self, slug="settle-the-estate"):
        return self.run_script("pm-check", slug, "--today", TODAY)

    def test_status_and_overdue(self):
        code, out, err = self.check()
        self.assertEqual(code, 0, err)
        self.assertIn("Next actions: 1. OK.", out)
        self.assertIn("[[call-the-lawyer]]", out.split("## Overdue")[1])
        self.assertIn("[[send-the-forms]]", out)
        self.assertIn("blocked_by call-the-lawyer", out)

    def test_stale_waiting(self):
        _, out, _ = self.check()
        self.assertIn("[[chase-the-bank]]", out.split("## Stale waiting-for")[1].split("## Overdue")[0])

    def test_missing_next_action(self):
        p = self.root / "Tasks" / "call-the-lawyer.md"
        p.write_text(p.read_text().replace("status: next-action", "status: queued"), encoding="utf-8")
        _, out, _ = self.check()
        self.assertIn("MISSING", out)

    def test_best_queued_to_promote(self):
        p = self.root / "Tasks" / "call-the-lawyer.md"
        p.write_text(p.read_text().replace("status: next-action", "status: done\ncompleted: 2026-10-04"), encoding="utf-8")
        _, out, _ = self.check()
        self.assertIn("[[send-the-forms]]", out.split("## Best queued task to promote")[1].split("## Stale")[0])

    def test_unknown_project(self):
        code, _, err = self.check("nope")
        self.assertEqual(code, 1)
        self.assertIn("Project not found", err)

    def test_never_writes(self):
        before = self.snapshot()
        self.check()
        self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main()
