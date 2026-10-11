---
title: Settle the estate
phase: in-progress
health: at-risk
last_sweep: 2026-09-25
priority: high
due: 2026-12-31
area:
  - "[[health]]"
people:
  - "[[lena-ortiz]]"
created: 2026-09-13
---
# Settle the estate

Done when the estate is closed. Start with [[call-the-lawyer]].

## Status

As of Sep 25, 2026 (project manager): **at risk**. The lawyer hasn't called back.

- **Next:** [[call-the-lawyer]]
- **Decisions for Robin:** None.

## Next step

```dataview
LIST
FROM "Tasks"
WHERE project = this.file.link AND status = "next-action"
```

## Tasks

```dataview
TABLE status, due, priority
FROM "Tasks"
WHERE project = this.file.link AND status != "done" AND status != "cancelled"
SORT status ASC, due ASC
```

## Done

```dataview
TABLE WITHOUT ID file.link AS "Task", completed AS "Completed"
FROM "Archive" OR "Tasks"
WHERE (status = "done" OR status = "cancelled") AND completed >= date(today) - dur(7 days)
  AND length(filter(file.inlinks, (t) => startswith(meta(t).path, "Tasks/") AND t.status = "next-action")) != 1
GROUP BY default(project, "No project") AS Project
SORT rows.completed DESC
```
