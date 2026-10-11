---
title: Garden
tags:
  - next-action
  - gardening
---

# Garden

Growing things 🌱 in the yard.

## Projects

No query here.

## Tasks

```dataview
TABLE status, blocking, due
FROM "Todo"
WHERE contains(area, this.file.link) AND tasks AND length(filter(file.inlinks, (t) => t.status = "done")) > 0
```

## Someday/maybe

- Build a greenhouse (revisit next spring)
- Plant fig trees (revisit 2026-02-30)

## Seeds 🌱

# Second heading
