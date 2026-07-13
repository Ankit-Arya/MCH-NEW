# Evidence Preview Route 404 Fix

## Problem

Saved entries return preview URLs like:

```text
/inspections/media/{media_id}/preview
```

The actual preview endpoint exists in:

```text
backend/app/api/v1/endpoints/evidence_preview.py
```

but `backend/app/api/v1/router.py` was not importing/registering that router, so FastAPI returned 404 for:

```text
GET /api/v1/inspections/media/{media_id}/preview
```

## Fix

Registers:

```python
api_router.include_router(evidence_preview.router, prefix="/inspections/media", tags=["Inspection Evidence Preview"])
```

before the general inspections router.

## Apply

```bat
xcopy /E /Y mch_evidence_preview_route_404_fix_patch\backend backend\
python backend\scripts\20260713_register_evidence_preview_route.py
docker compose up -d --build api
```

No DB migration required.
