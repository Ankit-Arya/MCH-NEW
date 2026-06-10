# Inspection loading + access-control merge fix

## Problem
After access-control/hierarchy changes, the inspection form can remain stuck on `Loading inspection...`.

The cause is usually a merge overwrite: `backend/app/api/v1/endpoints/inspections.py` from the hierarchy patch did not include the newer entry-based endpoints added earlier, especially:

- `GET /api/v1/inspections/{inspection_id}/entries`
- `POST /api/v1/inspections/{inspection_id}/entries`
- `POST /api/v1/inspections/{inspection_id}/entries/{entry_id}/media`
- `DELETE /api/v1/inspections/{inspection_id}/entries/{entry_id}`

The form page calls the entries endpoint while loading. If that endpoint is missing, frontend loading never finishes cleanly.

## Files replaced

- `backend/app/api/v1/endpoints/inspections.py`
- `frontend/src/views/InspectionFormView.vue`

## What this keeps

- Entry-based inspection capture
- Save Entry after mandatory photo
- Optional video
- Access-control station checks
- Scoped inspection listing
- Better frontend error message instead of infinite loading

## Apply

Copy patch files into project root, then run:

```powershell
docker compose restart api frontend
```

## Quick test

```powershell
docker compose logs api --tail=80
```

Then open an inspection form again. If the user has no station access, the page will now show a clear access error instead of loading forever.
