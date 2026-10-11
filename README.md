# tidyvault

**An Obsidian vault with rules your AI agent actually follows.**

Point Claude Code, Codex, or Cursor at a plain vault and it misfiles notes, invents fields, and forgets what it did. In a tidyvault:

> **You:** Remind me to call the dentist before the trip.
> **Agent:** Created `Tasks/call-the-dentist.md` (next action, area: health). No `due`: not a hard deadline. Lint clean. Logged.
>
> **You:** Delete the old estate notes.
> **Agent:** That's an erasure, which I don't do unasked. Say "erase the estate notes" to confirm, or I can archive them instead.

![A terminal rendering a vault, linting it, dropping a capture note, and running the GTD review](docs/demo.gif)

## Try it

```bash
uvx copier copy gh:smithbr/tidyvault my-vault
```

1. Answer the questions (defaults are fine) and open `my-vault` in Obsidian.
2. Install the plugins it asks for.
3. In Claude Code, from that folder: `/vault-pm`, then "what now?".

Needs git, Python 3.12+, and [uv](https://docs.astral.sh/uv/). Any agent that reads `AGENTS.md` works; the `/vault-*` commands are Claude Code extras.

## What's inside

- **GTD folders.** `Tasks`, `Projects`, `Areas`, `Resources`, `People`, `Archive`. One file per thing, plus a `Home.md` dashboard.
- **A rulebook the agent reads first.** Where things go, what fields a note has, what the agent may do alone, must report, or must ask about.
- **Six roles.** intake, pm, docs, ask, ops, admin. Each may write only what its page allows.
- **A linter that fixes.** 26 checks (links, fields, tasks with no home, projects with no next step, personal data); `--fix` repairs the safe ones.
- **A log.** Every agent run is recorded. Every question for you lands on the dashboard, not in a chat.
- **Updates.** `copier update` brings new rules and checks without touching your notes or your own rules in `Agents/local/`.

## Good to know

- It creates a new vault and never edits an existing one. Moving a vault in is on the roadmap.
- Nothing leaves your machine: folders, Markdown, and one standard-library Python script.
- Personal data stays in your password manager; notes hold a key, and the linter catches a value that slips through. Optional, on by default.
- Version 0.1: one person's vault system, generalized and tested daily on a real vault. Rough edges likely; open an issue.

## Development

`tests/kit-check` renders every option on and off, lints both, runs the tests, and greps for leaks. Design notes are in `docs/`.

MIT.
