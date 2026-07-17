# Inspection Leave Warning Patch

## Purpose

Adds an isolated frontend guard on the inspection entry page.

When a user starts an inspection and remains on an editable inspection page, any attempt to navigate away through browser back, dashboard/menu links, or page refresh will show a warning that progress may be lost.

## Files changed by script

- `frontend/src/views/InspectionFormView.vue`

## What is intentionally not changed

- No backend endpoints
- No database changes
- No inspection workflow/status logic
- No submit/review/approval logic
- No draft deletion logic

## Apply from project root in CMD

```bat
tar -xf mch_inspection_leave_warning_patch.zip
copy /Y mch_inspection_leave_warning_patch\backend\scripts\20260717_apply_inspection_leave_warning_patch.py backend\scripts\
python backend\scripts\20260717_apply_inspection_leave_warning_patch.py
docker compose up -d --build frontend
```

## Behavior

The warning appears only while the inspection page is still editable:

- `DRAFT`
- `RETURNED_FOR_CLARIFICATION`
- currently saving/submitting

After the inspection is submitted and locked, normal navigation is allowed.
