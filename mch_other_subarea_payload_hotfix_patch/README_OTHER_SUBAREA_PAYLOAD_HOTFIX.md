# Other Sub-area Payload Hotfix

This is an isolated frontend-only hotfix for `InspectionFormView.vue`.

## Problem

When the user selects **Other** sub-area, `EntryCaptureForm.vue` emits:

```js
sub_area_id: null,
custom_sub_area_name: "typed name"
```

The parent page validation was updated earlier, but the final API payload still sent only:

```js
sub_area_id: form.sub_area_id
```

So the backend received `sub_area_id: null` without `custom_sub_area_name` and correctly returned:

```text
422 Select a sub-area or enter Other sub-area name
```

## Fix

The API payload now sends:

```js
sub_area_id: isOther ? null : Number(form.sub_area_id),
custom_sub_area_name: isOther ? String(form.custom_sub_area_name || '').trim() : null,
```

## Apply

From project root in CMD:

```bat
tar -xf mch_other_subarea_payload_hotfix_patch.zip
copy /Y mch_other_subarea_payload_hotfix_patch\backend\scripts\20260717_apply_other_subarea_payload_hotfix.py backend\scripts\
python backend\scripts\20260717_apply_other_subarea_payload_hotfix.py
docker compose up -d --build frontend
```

## Scope

- Frontend only
- No DB migration
- No backend changes
- No workflow/status/emergency/draft-delete logic changes
