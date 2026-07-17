# Other Sub-area Save Hotfix

## Purpose

Fixes the frontend validation issue where selecting **Other** sub-area and saving an entry shows:

```text
Please select a valid sub-area before saving
```

## Root cause

`EntryCaptureForm.vue` correctly emits `sub_area_id: null` with `custom_sub_area_name` for Other sub-area.

`InspectionFormView.vue` then tried to validate that `null` sub-area against the normal master sub-area list using `getSubAreaById(form.sub_area_id)`, so the parent page rejected the valid Other entry before it reached the backend.

## Scope

Frontend-only, isolated to:

```text
frontend/src/views/InspectionFormView.vue
```

## What changes

- Detects Other sub-area payload by checking `custom_sub_area_name` with no `sub_area_id`.
- Uses the same default evidence rule already shown in the form: 1 mandatory photo, max 3 photos.
- Keeps existing validation for normal master sub-areas unchanged.
- Keeps backend, DB, workflow, emergency, draft delete and review logic untouched.

## Apply

Run from project root in CMD:

```bat
tar -xf mch_other_subarea_save_hotfix_patch.zip
copy /Y mch_other_subarea_save_hotfix_patch\backend\scripts\20260717_apply_other_subarea_save_hotfix.py backend\scripts\
python backend\scripts\20260717_apply_other_subarea_save_hotfix.py
docker compose up -d --build frontend
```

## Rollback

Use git to revert only the changed frontend file:

```bat
git checkout -- frontend\src\views\InspectionFormView.vue
docker compose up -d --build frontend
```

No DB migration required.
