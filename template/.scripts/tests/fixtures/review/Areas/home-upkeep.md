---
title: Home upkeep
---

# Home upkeep

## Projects

```dataview
TABLE status
FROM "Projects"
WHERE contains(area, this.file.link)
```

## Tasks

```dataview
TABLE status
FROM "Tasks"
WHERE contains(area, this.file.link)
```

## Someday/maybe

- Build a shed (revisit 2026-09-01)
- Solar panels (revisit 2026-12-01)
- Learn woodworking
