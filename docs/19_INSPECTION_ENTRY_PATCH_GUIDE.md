# Inspection Entry UI + Docker Development Patch Guide

This patch changes inspection capture from a full checklist page to a selected-entry page.

## What changes

Old flow:

```text
Open inspection → render all attributes → render all sub-areas → user scrolls a huge checklist → submit only when everything is complete
```

New flow:

```text
Open inspection → select one attribute → select one sub-area → capture mandatory photo → optional video → grade → save entry → repeat if required → submit partial inspection
```

The parent `inspection_id` remains the same. Each saved observation gets its own `inspection_entry_id` and `entry_no`.

## Files in this patch

```text
backend/app/models/all_models.py
backend/app/schemas/inspection.py
backend/app/services/inspection_service.py
backend/app/api/v1/endpoints/inspections.py
backend/app/api/v1/endpoints/master.py
backend/app/api/v1/endpoints/reports.py
backend/alembic/versions/0002_add_inspection_entries.py
frontend/src/views/InspectionFormView.vue
frontend/src/components/EntryCaptureForm.vue
frontend/src/components/MediaCapturePanel.vue
frontend/src/components/EntryMetadataPreview.vue
frontend/src/components/SavedEntriesList.vue
frontend/src/services/api.js
docker-compose.override.yml
nginx/default.dev.conf
```

## Apply steps

1. Backup the current project.
2. Copy files from this patch into the same relative paths in your project.
3. Run database migration:

```bash
docker compose exec api alembic upgrade head
```

4. Restart only required services:

```bash
docker compose restart api
# For frontend dev server, usually hot reload is enough. If needed:
docker compose restart frontend nginx
```

## Important data model

```text
inspections
  id = one parent inspection record

inspection_entries
  id = one selected area observation
  inspection_id = parent inspection
  attribute_id
  sub_area_id
  grade_code
  grade_percentage
  remarks
  captured latitude/longitude/time

inspection_media
  inspection_id
  inspection_entry_id
  media_type PHOTO/VIDEO
  object_path in MinIO
  captured metadata
```

## Submit rule

An inspection may be submitted with partial entries. But every saved entry must have at least one PHOTO. Video remains optional.
