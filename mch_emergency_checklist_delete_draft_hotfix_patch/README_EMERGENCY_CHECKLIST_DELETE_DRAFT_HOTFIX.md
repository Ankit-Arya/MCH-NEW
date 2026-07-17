# Emergency Checklist + Delete Draft Hotfix

This patch fixes two regressions:

1. Emergency inspection starts successfully, but the form fails while loading checklist with `403 Station access not provided`.
2. Delete draft returns 500 because `InspectionAttributeScore` and `InspectionSubAreaObservation` are used but not imported in `backend/app/api/v1/endpoints/inspections.py`.

## Apply

Run from project root in CMD:

```bat
tar -xf mch_emergency_checklist_delete_draft_hotfix_patch.zip
copy /Y mch_emergency_checklist_delete_draft_hotfix_patch\backend\scripts\20260717_apply_emergency_checklist_delete_draft_hotfix.py backend\scripts\
python backend\scripts\20260717_apply_emergency_checklist_delete_draft_hotfix.py
docker compose up -d --build api frontend
```

## What changes

- `InspectionFormView.vue` passes `inspection_id` to `/inspections/checklist`.
- `/inspections/checklist` continues to allow the original submitter to load checklist for their own emergency draft/returned inspection even if station access is not normally mapped.
- Backward-compatible backend fallback is included for cached frontend builds that still omit `inspection_id`.
- Adds missing imports needed by draft deletion.

No DB migration required.
