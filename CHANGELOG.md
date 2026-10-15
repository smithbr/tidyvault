# Changelog

Versions are git tags `vX.Y.Z`; `VERSION` mirrors the latest. Invariant changes are major.

## Unreleased

- `.scripts/pii-queue`: agents queue PII values with `pii-queue add KEY --where TEXT` (value on stdin) instead of editing the queue file; `count` and `keys` report what's waiting without showing values.
- Templater: with "Trigger on new file creation" on, Templater runs every tag in a new file that isn't empty (a Sync arrival, a git pull, an agent's write, a dropped-in file), code fences included; the settings page said the opposite and is corrected. New `vault-lint` check `templater`: templates in `Agents/templates/` may hold only the kit's own Templater commands, any tag elsewhere is an error (it was an `anatomy` warning), and a tag in `_imports/` or `_captures/` is a warning. `import-files fence-fix` turns each `<%` into `&lt;%`, and the inventory flags it. Templater now ignores `_imports`, `_captures`, `_attachments`, `_files`, and `_tmp` on creation; `.obsidian/` is written once, so an existing vault adds those five folders by hand (Settings → Templater → File creation → Excluded folders).
- Templater's "Trigger Templater on new file creation" is on in every kit vault, set by hand: Templater 2.25 keeps it per device, outside `data.json`, so the kit can't ship it. Copier's closing message, `vault-setup`, and the README say to turn it on on each device; the settings page lists it.
- `.scripts/obsidian-plugins` installs each plugin at the version pinned in `.scripts/obsidian-plugins.lock` and refuses a file whose sha256 doesn't match. `--update` moves installed plugins to the pins; `--latest` keeps the old unchecked latest-release install for when the owner asks; `--lock` re-pins (kit maintainers).
- `vault-lint` check `dataviewjs`: `Home.md` is no longer exempt; like every note it may hold only one-line calls to a view in `Agents/views/`, which is all the shipped Home has. Agents rewrite Home's snapshot daily, so an ask rule there would fire every day; the lint catches any other code instead. A vault whose Home has its own DataviewJS moves that code into a view.
- `pii-queue` escapes backticks in every cell, so a name or note can't pass for a key when `pii-merge-queue` reads the queue.
- Copier validators: the vault name and the owner's slug take only lowercase letters, digits, and hyphens; the file store path only letters, digits, `.`, `_`, `-`, and `/` after `~/`, with no `..`; names leave out quotes, backslashes, colons, `#`, backticks, and `$`. These values are pasted into shell scripts and YAML.
- `copier copy --trust` sets a new vault up: a copy-only task runs `vault-setup --new`, which installs the Obsidian plugins and makes the first git commit without asking, then offers the 1Password and backup steps. `copier update` now needs `--trust` too. Needs Copier 9.6.
- Copier questions: plainer wording, the full name is asked first and suggests the first name, a one-line intro, and validators for empty names, the slug, the vault name, and the file store path.
- `.scripts/vault-setup`: a first-time setup walkthrough (git history, Obsidian plugins, the 1Password CLI and the PII register document, restic backups to Backblaze B2 with the repository password kept in 1Password). Copier prints it as the next step after rendering.
- Backup module: the settings file and `install.sh` now expect Backblaze B2 credentials; the README walks through the bucket and application key.

## 0.1.0 — 2026-10-11

- First public release: Copier template for an Obsidian vault run by agents (PARA folders, GTD task language, `Agents/` manual, six roles, `vault-lint`).
