# Reports and Review Queue Pagination Patch

## Why this patch is needed

Reports and review queues will grow continuously in production. Loading every record in one API call causes:

- slow page load
- high database memory usage
- long JSON responses
- mobile browser lag
- poor user experience when thousands of inspections exist

This patch changes reports and review queue screens to use server-side pagination.

## Files included

```text
backend/app/api/v1/endpoints/reports.py
backend/app/api/v1/endpoints/reviews.py
frontend/src/views/ReportsView.vue
frontend/src/views/ReviewQueueView.vue
docs/32_REPORTS_REVIEW_PAGINATION_PATCH_GUIDE.md
```

No database migration is required.

## Backend API changes

### Reports search

Old response:

```json
[
  { "id": 1, "inspection_no": "INS-..." }
]
```

New response:

```json
{
  "items": [
    { "id": 1, "inspection_no": "INS-..." }
  ],
  "total": 142,
  "page": 1,
  "size": 20,
  "pages": 8,
  "has_next": true,
  "has_prev": false,
  "from_record": 1,
  "to_record": 20
}
```

Endpoint:

```http
GET /api/v1/reports/inspections/search?page=1&size=20
```

Filters still work:

```http
GET /api/v1/reports/inspections/search?from_date=2026-01-01&to_date=2026-05-31&station_id=1&page=1&size=20
```

### Review queue

Endpoint:

```http
GET /api/v1/reviews/pending?page=1&size=20
```

It now returns the same pagination envelope.

## Frontend UI changes

### Reports page

The reports page now shows:

- total record count
- current visible range, for example `Showing 1–20 of 142 records`
- page size selector: 10 / 20 / 50 / 100
- First / Previous / Next / Last buttons
- mobile card layout instead of forcing a wide table on phones

### Review queue page

The review queue page now shows:

- total pending review count
- page size selector
- pagination controls
- mobile card layout
- automatic refresh after recommend/approve action

## Important behavior

The visible list is paginated, but PDF register download still uses the full selected filter range. This is intentional.

Example:

- Screen shows page 1 with 20 records
- Filtered result has 300 records
- `Download Filtered PDF` downloads the PDF for all 300 filtered records, not only current page

## Apply instructions

Copy this patch into the project root:

```bash
cp -r mch-pagination-patch/* /path/to/mch-inspection-platform/
```

Restart backend and frontend:

```bash
docker compose restart api frontend
```

If using production-built frontend image:

```bash
docker compose up -d --build api frontend nginx
```

## Quick test

Open Reports page and verify:

1. Records show as paginated.
2. Change rows per page to 10/20/50.
3. Click Next/Previous.
4. Apply filters and verify page resets to 1.
5. Download single PDF.
6. Download filtered PDF.

Open Review Queue and verify:

1. Pending records show as paginated.
2. Click action button.
3. Queue refreshes without loading all records.
4. Mobile view shows cards instead of a wide table.

## Production note

For very large production databases, add indexes on:

```sql
inspections (inspection_date)
inspections (station_id)
inspections (contract_id)
inspections (submitted_by)
inspections (status)
inspections (created_at)
```

These indexes will keep filtered reports and review queue fast.
