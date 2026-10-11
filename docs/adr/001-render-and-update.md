# ADR 001: render and update vaults with Copier

- Status: Accepted
- Date: 2026-09-28
- Deciders: kit maintainer

## Context

The kit must create new vaults from one source and later push kit changes into them, without clobbering each vault's own rules or content. The first vault built this way is a fork of an existing personal vault whose rules are mixed with vault-specific ones.

## Options

| Option | Verdict | Why |
|---|---|---|
| A. Home-made CLI (`vault-kit init/update`, own placeholder syntax) | Rejected | Rendering is easy; update and merge is the hard part, and we'd be rebuilding it |
| B. Copier template | **Chosen** | Questions, conditional files, answers file, and 3-way merge on update, all built in; versions are git tags |
| C. Git fork per vault with an upstream remote | Rejected | No questions or modules; every vault carries every file; merges mix kit and vault history |

## Decision

Copier, with:

- **Custom delimiters** `[[= =]]`, `[[% %]]`, `[[! !]]`, so markers clash with neither wikilinks nor Obsidian templates.
- **A kernel** of rules in `kernel/` with stable IDs: invariants I1–I13 (major version to change), heuristics H1–H10, module rules S1, P1, F1. Templates include them.
- **A local layer:** `Agents/local/` is seeded once and never touched by the kit. Vault-specific rules live there as L1, L2, ... Kit-managed files aren't edited in a vault; when they are, `copier update` 3-way merges: edits in different regions merge; same-line edits leave Git conflict markers to resolve and commit; no `.rej`.
- **Seeds** (`_skip_if_exists`) for content the vault owns: `Home.md`, `People/`, `Areas/`, `Resources/`, `.obsidian/`, changelog, PII allowlist.
- **No absolute paths** in templates; the store path is a `~` path answer.
- **Modules via conditionals**, not file overrides: whole files through `_exclude`, text through `[[% if %]]`. Profiles (`work`, `personal`) only set module defaults.

## Consequences

- Requires git, python3, and Copier on each machine; `--trust` on copy and update (includes, conditional excludes).
- Rule citations change from list numbers to IDs; renumbering never breaks a citation again.
- A kernel change is a kit release; a vault picks it up with `copier update`.
- Migrating the personal vault onto the kit needs its strict rules 1–27 mapped to kit IDs:

| Personal rule | Short name | Kit ID |
|---|---|---|
| 1 | Top-level list | I1 |
| 2 | Subfolders allowed | I2 |
| 3 | One file per item | I3 |
| 4 | Unique filenames | I4 |
| 5 | Attachments in the file store | S1 |
| 6 | Sentence case | I5 |
| 7 | Filename is title slug | I6 |
| 8 | Task title length | H1 |
| 9 | No emoji | H2 |
| 10 | How agents name the owner | H3 |
| 11 | Frontmatter matches schema | I7; its retired-fields clause → `Agents/local/` |
| 12 | Quoted frontmatter links | I8 |
| 13 | `agent_review` | H4 |
| 14 | Every link resolves | I9 |
| 15 | Tasks link what they need | H5 |
| 16 | Open task has project or area | I10 |
| 17 | Projects have a next action | I11 |
| 18 | `due` for hard deadlines | H6 |
| 19 | Closed items archived | I12 |
| 20 | Search before creating | H7 |
| 21 | PII stays out | P1 |
| 22 | External system is read-only | → `Agents/local/` |
| 23 | `.git/` and `.obsidian/` safeguards | H8 |
| 24 | Act, then report | H9 |
| 25 | Done means lint-clean | I13 |
| 26 | Banned claims | F1 |
| 27 | Fewest words | H10 |

- Page links in the personal vault's rules move too: H8 cites `agent-protocol` where the personal vault cites `obsidian-settings`.

## Amendments (2026-10-11)

- The kit is published as **tidyvault**; `vault-kit` above is its working name.
- The `kernel/` folder and Jinja includes were dropped: the ID'd rules live inline in `template/Agents/strict-rules.md.jinja`, module rules inside their module blocks. One file to review, one fewer concept to explain; the IDs and their stability guarantees are unchanged. Rule 13 of the personal vault (no review stamps) replaced H4 (`agent_review`), rule 22 (an outside system is read-only) moved to the local layer and the `source-urls` lint check, and rule 28 became H11.
- Profiles were dropped. With one optional module (backup) they differed by a single boolean; the five module questions are asked directly, and `tests/kit-check` renders every-module-on and every-module-off instead.
- `--trust` is not needed: the template has no tasks, migrations, or Jinja extensions.
- The local layer grew: `Agents/local/roles/role-<name>-local.md` holds modes a vault adds to a kit role, `Agents/local/access-map-local.md` and `Agents/local/external-systems-local.md` their rows.
