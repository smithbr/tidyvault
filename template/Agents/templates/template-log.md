---
title: Log template
type: template
---
# Log template

Part of the [[README]]. Skeleton for an agent's daily run log in `Agents/logs/`. Rules: [[agent-protocol]] (Run log), [[schema]].

**By hand (agents):** write the run's `##` heading when the run starts, before any other change. If today's log for your agent already exists, append the heading at the bottom and skip to the list below. Otherwise copy everything after the Templater script (the block that starts with `tR = ""`), starting at its `---`. Replace each Templater tag: the title with `Log: <agent in words> — YYYY-MM-DD`, the dates with today's date, the time with the start time (`HH:MM`). Save as `Agents/logs/log-<agent>-YYYY-MM-DD.md`. Then:

- Point the first line at your role or job spec, for example `[[role-vault-ops]]`.
- At the end, fill the run section, a few words or one short sentence per item ([[agent-protocol]], Run log, Length): a one-line Summary of what was done or answered, then the report from [[agent-protocol]], its headings as `###`. Omit empty ones except `### Checks`, which ends every run (a run that changed nothing: `read-only; no lint needed`).
- Add `sensitive: true` after `date` if the log holds sensitive detail.

<%*
tR = "";
let title = tp.file.title;
if (title.startsWith("Untitled")) title = "Log: " + (await tp.system.prompt("Agent (role or job, in words)")) + " — " + tp.date.now("YYYY-MM-DD");
const slug = title.normalize("NFKD").replace(/[^\x00-\x7F]/g, "").toLowerCase().replace(/'/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
await tp.file.move("Agents/logs/" + slug);
-%>
---
title: "<% title %>"
type: log
date: <% tp.date.now("YYYY-MM-DD") %>
---
# <% title %>

Part of the [[README]]. Run log for (link the role page or job spec).

## <% tp.date.now("HH:mm") %> — What was asked

### Summary

### Changed

### Destructive

### Waiting on you

### Checks
