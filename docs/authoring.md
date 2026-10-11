# Authoring the kit

How kit files are laid out and rendered. Read before editing `copier.yml` or `template/`.

## Layout

| Path | Holds | On `copier copy` | On `copier update` |
|---|---|---|---|
| `template/` | The vault: manual, roles, `AGENTS.md`, scripts, config | rendered | re-rendered, 3-way merged with the vault |
| `template/` seeds (`_skip_if_exists`) | `Home.md`, `People/*.md`, `Areas/**`, `Resources/**`, `.obsidian/**`, `Agents/changelog.md`, `Agents/pii-allowlist.md`, `Agents/local/**` | rendered | never touched |
| `copier.yml` | Questions, `_exclude` module conditionals, seeds, delimiters | | |
| `tests/kit-check` | Renders every-module-on and every-module-off, lints, runs the vault's tests, greps for leaks | | |

A path under `template/` is the path in the vault. File and folder names may use markers too (`People/[[= owner_slug =]].md.jinja`).

## Syntax

Custom Jinja delimiters, so kit markers clash with neither wikilinks (`[[...]]`) nor Obsidian templates (`{{...}}`):

| Marker | Use |
|---|---|
| `[[= owner =]]` | Print a value |
| `[[% if pii %]]` ... `[[% endif %]]` | Block on its own lines; the line is removed (`trim_blocks`, `lstrip_blocks`) |
| `[[%+ if store +%]]` ... `[[%+ endif +%]]` | Inline block mid-sentence; keeps surrounding whitespace |
| `[[! note !]]` | Comment, not rendered |

A file with markers must end in `.jinja`; Copier renders it and strips the suffix. A `.jinja` file without markers is harmless. Files without the suffix (`.scripts/vault-lint`) are copied as is, markers and all, so scripts read the owner and modules from `.tidyvault.yml` instead of carrying markers.

Blank lines around a block: put the blank line inside the block (right after `[[% if %]]`), never before it, or the rendered page gets a doubled blank line when the module is off. An inline block that ends a line carries its own leading space (`conflict.[[%+ if obsidian +%]] Every…[[%+ endif +%]]`), or the line ends with a trailing space when off. `kit-check` lints both renders, so either slip fails the check.

## Values

| Variable | Value |
|---|---|
| `owner` | Owner's first name as written in agent prose ("Robin") |
| `owner_full` | Full name ("Robin Vale") |
| `owner_slug` | Slug of the owner's Person note (`robin-vale`) |
| `vault` | Vault name (`notes`) |
| `store_path` | File store path, a `~` path (store module only) |
| `store`, `pii`, `false_facts`, `obsidian`, `backup` | Module switches (booleans) |
| `_copier_answers._commit` | Kit version that rendered the vault |

No absolute paths: the vault location isn't a template value.

## Modules

- A whole file belongs to a module: add a `[[% if not <module> %]]<path>*[[% endif %]]` line to `_exclude` in `copier.yml`.
- Part of a file belongs to a module: wrap it in `[[% if <module> %]]`. Never add a second copy of a file to override the first.
- A link to a module's page (`[[sensitive-data]]`, `[[obsidian-settings]]`, `[[false-facts]]`, `[[vault-backup-and-restore]]`, `[[file-store]]`) must sit inside that module's block, or the every-module-off render has a dangling link.
- A check in `vault-lint` that belongs to a module is listed in its `CHECK_MODULES`; `.tidyvault.yml` tells the linter which modules are on.
- A new module: add the question to `copier.yml`, its entry in the `modules:` loop of `template/.tidyvault.yml.jinja`, its `_exclude` lines, and a row in the README table.

## Rule IDs

Strict rules carry stable IDs, never list numbers: invariants `I1`–`I13` (changing one is a major version), heuristics `H1`–`H11` (minor), and one per module: `S1` store, `P1` pii, `F1` false-facts. They live in `template/Agents/strict-rules.md.jinja`, module rules inside their module blocks. Cite them as `[[strict-rules]] I1`. Vault-only rules are `L1`, `L2`, ... in `Agents/local/local-rules.md`, which the kit seeds once and never changes. `.scripts/README.md.jinja`'s coverage matrix is keyed by the same IDs.

## Writing rules

- Prose calls the owner `[[= owner =]]`. No dated "(owner, date)" provenance: state the rule.
- Examples use a fictional cast: owner Robin Vale, Priya Nair (friend), Theo Vale (brother), Lena Ortiz (lawyer), Northwind Dental (a provider), project `renovate-the-kitchen`, trip `lisbon-trip-2027`, document `kitchen-quote`. Example links go in inline code unless the target ships with the kit.
- Every `[[link]]` must resolve in a fresh vault for every module combination: link only to kit files, or wrap the link in the matching module block.
- No real names, hosts, buckets, accounts, or content slugs from any live vault. Tool and product names appear only where the kit depends on the product (Obsidian, Copier, restic, the plugins it ships settings for).
- Anything a vault adds on top (a mode for a role, an outside system, a standing approval) is described as living in `Agents/local/`, never written into a kit page.

## Check

```bash
tests/kit-check [leak-words-file]
```

Renders the `full` (every module on) and `minimal` (every module off) variants, fails on unrendered markers or lint errors and warnings, runs `vault-lint`'s tests and the script tests in the rendered vault, greps the kit for `tests/leak-patterns.txt` (paths, tokens), and, with the optional file, for the words in it (the maintainer's private list of names and hosts that must never ship). Exit 0 means pass. CI runs it on Linux and macOS with the private list in the `LEAK_WORDS` secret.
