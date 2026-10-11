---
title: Task template
type: template
---

# Task template

Copy from the second `---`. Link a project like [[…]] or [[project-name]].

<%*
tR = "";
let title = tp.file.title;
-%>
---
title: <% title %>
status: inbox
created: <% tp.date.now("YYYY-MM-DD") %>
---

# <% title %>

password: <% tp.system.prompt("x") %> https://old-wiki.example/placeholder
