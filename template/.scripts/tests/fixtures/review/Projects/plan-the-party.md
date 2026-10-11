---
title: Plan the party
phase: in-progress
area:
  - "[[home-upkeep]]"
---

# Plan the party

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
