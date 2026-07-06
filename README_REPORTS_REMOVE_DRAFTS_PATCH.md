# Reports Remove Drafts Patch

## Replace

```text
backend/app/api/v1/endpoints/reports.py
```

## Rebuild

```bat
docker compose up -d --build api
```

## What changed

- Draft inspections are excluded from `/api/v1/reports/inspections/search`.
- Draft inspections are excluded from filtered report register PDFs.
- Direct single-inspection PDF generation now blocks DRAFT inspections with a clear message.
- Drafts remain available in Action Required only.
- No DB migration required.
