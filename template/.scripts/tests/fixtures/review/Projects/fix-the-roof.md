---
title: Fix the roof
phase: in-progress
area:
  - "[[home-upkeep]]"
---

# Fix the roof

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
