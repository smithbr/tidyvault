---
title: Task template
type: template
---
# Task template

Part of the [[README]]. Skeleton for a new Task in `Tasks/`. Rules: [[gtd]], [[schema]], [[body-sections]].

**In Obsidian:** create a new file in `Tasks/` (the default location for new files) and Templater's folder template applies this skeleton, asks for the title, fills the date, and renames the file to its slug; the other folder templates work the same way. Don't also run *Templater: Insert template*, which would add a second skeleton.

**By hand (agents), for every template here:** copy everything after the Templater script (the block that starts with `tR = ""`), starting at its `---`. Replace each Templater title tag (`title` between percent-sign brackets) with the sentence-case title and the `tp.date.now` tag with today's date (`YYYY-MM-DD`). Save as `<folder>/<slug>.md` ([[naming-and-style]]). Then, for a Task:

- Add `project: "[[…]]"` or `area:` ([[schema]]).
- Add `resources:` for every Resource needed to do it, in the same change.
- Optional fields: [[schema]].
- For a waiting-for, set `status: waiting-for`, `waiting_on`, `waiting_since`.
- Delete body sections you don't fill.

<%*
tR = "";
let title = tp.file.title;
if (title.startsWith("Untitled")) title = await tp.system.prompt("Task title (sentence case, verb first, 2–5 words)");
const slug = title.normalize("NFKD").replace(/[^\x00-\x7F]/g, "").toLowerCase().replace(/'/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
await tp.file.move("Tasks/" + slug);
-%>
---
title: <% title %>
status: inbox
created: <% tp.date.now("YYYY-MM-DD") %>
---
# <% title %>

## Details

## Steps

## Log
