# Reports hierarchy scope fix

Drop-in replacement:

```text
backend/app/core/permissions.py
```

## Issue fixed

Reports were calling `apply_inspection_scope()`, but that function allowed a station-scope fallback for users without subordinates.

That meant an SM mapped to Station A could see every inspection for Station A, including inspections submitted by another SM/EIT.

## New rules

Reports and single-report PDF download are now submitter/hierarchy scoped:

- Super Admin / HK Cell / GM Ops: all inspections.
- DGM / LM / supervisor: inspections submitted by self and all recursive subordinates only.
- SM / EIT / users without subordinates: inspections submitted by self only.

Station and line mappings are still used for station access, dropdowns and master-data scoping, but not for report visibility.

## Rebuild

```bash
docker compose up -d --build api worker
```

If only the API container serves this code in your compose file, rebuilding `api` is enough:

```bash
docker compose up -d --build api
```
