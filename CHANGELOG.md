# Changelog

Versions are git tags `vX.Y.Z`; `VERSION` mirrors the latest. Invariant changes are major.

## Unreleased

- Copier questions: plainer wording, the full name is asked first and suggests the first name, a one-line intro, and validators for empty names, the slug, the vault name, and the file store path.
- `.scripts/vault-setup`: a first-time setup walkthrough (git history, Obsidian plugins, the 1Password CLI and the PII register document, restic backups to Backblaze B2 with the repository password kept in 1Password). Copier prints it as the next step after rendering.
- Backup module: the settings file and `install.sh` now expect Backblaze B2 credentials; the README walks through the bucket and application key.

## 0.1.0 — 2026-10-11

- First public release: Copier template for an Obsidian vault run by agents (PARA folders, GTD task language, `Agents/` manual, six roles, `vault-lint`).
