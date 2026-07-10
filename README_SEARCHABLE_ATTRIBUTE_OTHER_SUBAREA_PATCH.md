# Searchable Attribute/Sub-area + Other Sub-area Patch

## Files to replace

- `backend/app/schemas/inspection.py`
- `backend/app/services/inspection_service.py`
- `frontend/src/components/EntryCaptureForm.vue`
- `frontend/src/views/InspectionFormView.vue`

## Rebuild

```bat
docker compose up -d --build api frontend
```

## Behaviour

- Attribute field is now searchable by typed keyword.
- Sub-area field is now searchable by typed keyword.
- Sub-area suggestions are filtered in the dropdown panel itself.
- User can choose `Other sub-area not in list`.
- When Other is selected, user enters the new sub-area name.
- Backend creates or reuses that sub-area under the selected attribute.
- Other sub-area default evidence rule is 1 mandatory photo and max 3 photos.
- No DB migration is required because it reuses the existing `inspection_sub_areas` table.

## Notes

- Newly added Other sub-area becomes available in future inspections because it is saved as an active sub-area under the selected attribute.
- Existing saved-entry media preview support is preserved through `media_files` in entry response.
