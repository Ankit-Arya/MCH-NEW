# Workflow Tracker Modal UI Patch

Drop-in replacement files:

- `frontend/src/views/ReportsView.vue`
- `frontend/src/views/ReviewQueueView.vue`

This is a frontend-only refinement on top of the workflow tracker API patch.
Backend files are not changed in this patch.

## Changes

- Replaces the visible approval tracker text block with a compact `Status / Tracker` button.
- Clicking the button opens a modal popup with the full approval trail.
- Clubs status and tracker into one column/button so the register is cleaner.
- Removes the low-value Entries column from Review Queue.
- Keeps PDF actions and review actions unchanged.

## Rebuild

```bash
docker compose up -d --build frontend
```
