# tidyvault

**An Obsidian vault with rules your AI agent actually follows.**

Point Claude Code, Codex, or Cursor at a plain vault and it misfiles notes, invents fields, and forgets what it did. In a tidyvault:

> **You:** Remind me to call the dentist before the trip.
> **Agent:** Created `Tasks/call-the-dentist.md` (next action, area: health). No `due`: not a hard deadline. Lint clean. Logged.
>
> **You:** Delete the old estate notes.
> **Agent:** That's an erasure, which I don't do unasked. Say "erase the estate notes" to confirm, or I can archive them instead.

## Try it

```bash
uvx copier copy --trust gh:smithbr/tidyvault my-vault
```

1. Answer the questions (defaults are fine). Copier then sets the vault up: it installs the Obsidian plugins and makes the first git commit, then offers the 1Password and backup steps. `--trust` is what lets it run that setup.
2. Open `my-vault` in Obsidian and choose "Trust author and enable plugins".
3. Anything left (1Password, backups): rerun `python3 .scripts/vault-setup` from `my-vault` until every line says ok.
4. In Claude Code, from that folder: `/vault-pm`, then "what now?".

Needs git, Python 3.12+, and [uv](https://docs.astral.sh/uv/); 1Password and Backblaze B2 are the only password manager and backup target supported so far. Any agent that reads `AGENTS.md` works; the `/vault-*` commands are Claude Code extras.

## What's inside

- **GTD folders.** `Tasks`, `Projects`, `Areas`, `Resources`, `People`, `Archive`. One file per thing, plus a `Home.md` dashboard.
- **A rulebook the agent reads first.** Where things go, what fields a note has, what the agent may do alone, must report, or must ask about.
- **Six roles.** intake, pm, docs, ask, ops, admin. Each may write only what its page allows.
- **A linter that fixes.** 26 checks (links, fields, tasks with no home, projects with no next step, personal data); `--fix` repairs the safe ones.
- **A log.** Every agent run is recorded. Every question for you lands on the dashboard, not in a chat.
- **Updates.** `copier update --trust` brings new rules and checks without touching your notes or your own rules in `Agents/local/`.
- **Guided setup.** `vault-setup` checks every step below, offers to do the ones it can, and tells you exactly what's left.
- **Git history.** Every version of every note, so any change can be undone. Setup makes the first commit; the Git plugin commits every 15 minutes after that.
- **Personal data in 1Password.** Account numbers, IDs, and addresses live in one 1Password document, the PII register, which no agent can read. Notes hold a key in their place, and the linter catches a value that slips through. Setup checks the [1Password CLI](https://developer.1password.com/docs/cli/) and creates the register. Optional, on by default.
- **Nightly off-site backups.** Encrypted [restic](https://restic.net/) snapshots to a Backblaze B2 bucket, scheduled with launchd or cron, with the repository password kept in 1Password and a restore runbook in the vault. Setup walks through the bucket and key. Optional, off by default.

## Good to know

- Nothing leaves your machine unless you set it up: the Git plugin pushes to a remote only if you add one, and backups go to your B2 bucket already encrypted.

MIT.
