# Reports.py Merge Conflict Fix Patch

## File replaced

`backend/app/api/v1/endpoints/reports.py`

## What was fixed

1. Kept your PDF formatting changes:
   - black/white report styling
   - DMRC logo fallback
   - entry-wise PDF register
   - photo preview support
   - video evidence link section

2. Kept pagination support:
   - `GET /api/v1/reports/inspections/search?page=1&size=20`
   - returns `items`, `total`, `page`, `size`, `pages`, `has_previous`, `has_next`

3. Fixed runtime issues caused by the merge:
   - `_paginate_query()` was called but missing.
   - `_media_counts()` was called but missing.
   - `_row()` used `entries` without defining it.
   - metadata table had an invalid `SPAN` row reference after a row was removed/commented.

## Apply

Copy the patch into your project root so this file lands at:

`backend/app/api/v1/endpoints/reports.py`

Then restart API:

```bash
docker compose restart api
```

If API is built into an image without volume mount:

```bash
docker compose up -d --build api
```

## Quick check

```bash
docker compose exec api python -m py_compile app/api/v1/endpoints/reports.py
```

Then open:

- `/api/v1/reports/inspections/search?page=1&size=20`
- `/api/v1/reports/inspection/<inspection_id>/pdf`
- `/api/v1/reports/inspections/pdf`
