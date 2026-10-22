# tidyvault

**An Obsidian vault with rules your AI agent actually follows.**

Point Claude Code, Codex, or Cursor at a plain vault and it misfiles notes, invents fields, and forgets what it did. In a tidyvault:

> **You:** Remind me to call the dentist before the trip.
> **Agent:** Created `Tasks/call-the-dentist.md` (next action, area: health). No `due`: not a hard deadline. Lint clean. Logged.
>
> **You:** Delete the old estate notes.
> **Agent:** That's an erasure, which I don't do unasked. Say "erase the estate notes" to confirm, or I can archive them instead.

## Setup

```bash
uvx copier copy --trust gh:smithbr/tidyvault my-vault
```

1. Answer the questions. Copier installs the Obsidian plugins, makes the first git commit, and offers the 1Password and backup steps.
2. Open `my-vault` in Obsidian, choose "Trust author and enable plugins", then turn on Settings → Templater → "Trigger Templater on new file creation" (Templater keeps it per device, so once on each device).
3. From `my-vault`, rerun `python3 .scripts/vault-setup` until it prints "done".

Needs git, Python 3.9+, and [uv](https://docs.astral.sh/uv/).

## What's inside

- **GTD folders.** `Tasks`, `Projects`, `Areas`, `Resources`, `People`, `Archive`, one file per thing, and a `Home` dashboard.
- **A rulebook the agent reads first.** Where things go, which fields a note has, and what the agent may do alone, must report, or must ask about.
- **Six roles.** intake, pm, docs, ask, ops, admin. Each writes only what its page allows.
- **A linter that fixes.** 27 checks (links, fields, tasks with no home, projects with no next step, personal data); `--fix` repairs the safe ones.
- **A log.** Every agent run is recorded; every question for you lands on the dashboard.
- **Updates.** `copier update --trust` brings new rules and checks without touching your notes or your rules in `Agents/local/`.
- **Guided setup.** `vault-setup` checks each step, does the ones it can, and says what's left.
- **Git history.** Every version of every note. Setup makes the first commit; the Git plugin commits every 15 minutes after that.
- **Personal data in 1Password.** Account numbers, IDs, and addresses live in one 1Password document that no agent can read; notes hold a key instead, and the linter catches a value that slips through. Optional, on by default.
- **Nightly off-site backups.** Encrypted [restic](https://restic.net/) snapshots to Backblaze B2, with the password in 1Password and a restore runbook in the vault. Optional, off by default.

## Privacy

Nothing leaves your machine unless you set it up: the Git plugin pushes only to a remote you add, and backups reach B2 already encrypted.

MIT.
