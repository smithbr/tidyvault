---
title: Old project
phase: done
area:
  - "[[home-upkeep]]"
---

# Old project

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
