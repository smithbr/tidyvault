---
title: Task template
type: template
---

# Task template

Copy from the second `---`. Link a project like [[…]] or [[project-name]].

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

password: <% tp.system.prompt("x") %> https://old-wiki.example/placeholder
