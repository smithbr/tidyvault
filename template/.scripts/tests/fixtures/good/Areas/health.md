---
title: Health
people:
  - "[[robin-vale]]"
resources:
  - "[[kettlebell-plan]]"
created: 2026-09-13
---
# Health

Staying well 💪 (emoji are fine in body text).

## Projects

```dataview
TABLE phase, due, priority
FROM "Projects"
WHERE contains(area, this.file.link)
SORT phase ASC
```

## Tasks

~~~dataview
TABLE status, due
FROM "Tasks"
WHERE contains(area, this.file.link) AND status != "done" AND status != "cancelled"
SORT due ASC
~~~

## Someday/maybe

- Try a climbing gym (revisit 2026-11-01) ★ no emoji here, just a star.
- Learn to swim.

## Notes
