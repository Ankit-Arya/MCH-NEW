# MCH PDF Evidence App Proxy Link Patch

## Changed file

- `backend/app/api/v1/endpoints/reports.py`

## Why

The earlier PDF full-resolution photo link used a direct MinIO signed URL. In local/on-prem deployments that can generate links like `http://localhost:9200/...`, which fail when MinIO is not exposed on that host/port.

## What changed

- PDF photo links now point to the MCH API instead of MinIO directly.
- PDF video links also point to the MCH API, so both evidence types behave consistently.
- The API validates a short signed evidence token before streaming the object from MinIO.
- Existing thumbnails remain unchanged.
- No DB migration.
- No frontend change.

## Apply

Copy the replacement file into the same path in your project, then rebuild API:

```bash
docker compose up -d --build api
```

## Notes

Links generated inside PDFs are valid for 7 days. Generate a fresh PDF if a link expires.
