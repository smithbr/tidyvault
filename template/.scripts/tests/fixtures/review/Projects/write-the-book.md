---
title: Write the book
phase: not-started
area:
  - "[[home-upkeep]]"
---

# Write the book

## Next step

```dataview
LIST
FROM "Tasks"
WHERE project = this.file.link AND status = "next-action"
```

## Tasks

```dataview
TABLE status
FROM "Tasks"
WHERE project = this.file.link
```
