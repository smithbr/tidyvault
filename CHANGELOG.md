# Changelog

Versions are git tags `vX.Y.Z`; `VERSION` mirrors the latest. Invariant changes are major.

## Unreleased

- `.scripts/pii-queue`: agents queue PII values with `pii-queue add KEY --where TEXT` (value on stdin) instead of editing the queue file; `count` and `keys` report what's waiting without showing values.
- `.scripts/obsidian-plugins` installs each plugin at the version pinned in `.scripts/obsidian-plugins.lock` and refuses a file whose sha256 doesn't match. `--update` moves installed plugins to the pins; `--latest` keeps the old unchecked latest-release install for when the owner asks; `--lock` re-pins (kit maintainers).
- `pii-queue` escapes backticks in every cell, so a name or note can't pass for a key when `pii-merge-queue` reads the queue.
- Copier validators: the vault name and the owner's slug take only lowercase letters, digits, and hyphens; the file store path only letters, digits, `.`, `_`, `-`, and `/` after `~/`, with no `..`; names leave out quotes, backslashes, colons, `#`, backticks, and `$`. These values are pasted into shell scripts and YAML.
- `copier copy --trust` sets a new vault up: a copy-only task runs `vault-setup --new`, which installs the Obsidian plugins and makes the first git commit without asking, then offers the 1Password and backup steps. `copier update` now needs `--trust` too. Needs Copier 9.6.
- Copier questions: plainer wording, the full name is asked first and suggests the first name, a one-line intro, and validators for empty names, the slug, the vault name, and the file store path.
- `.scripts/vault-setup`: a first-time setup walkthrough (git history, Obsidian plugins, the 1Password CLI and the PII register document, restic backups to Backblaze B2 with the repository password kept in 1Password). Copier prints it as the next step after rendering.
- Backup module: the settings file and `install.sh` now expect Backblaze B2 credentials; the README walks through the bucket and application key.

## 0.1.0 — 2026-10-11

- First public release: Copier template for an Obsidian vault run by agents (PARA folders, GTD task language, `Agents/` manual, six roles, `vault-lint`).
