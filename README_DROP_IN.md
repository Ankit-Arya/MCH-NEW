# MCH Start Inspection station-scope patch v3

## Problem fixed

A user mapped to one station and one line could still start inspection at other stations because the Start Inspection logic expanded line access into station access.

For Start Inspection, that is too broad. Line access may be useful for dashboard/review/master-data visibility, but it must not permit starting inspection at every station on that line.

## Drop-in files

Copy these files into the same paths in your repo:

```text
backend/app/api/v1/endpoints/inspections.py
backend/app/schemas/inspection.py
backend/app/services/inspection_service.py
frontend/src/views/InspectionStartView.vue
```

## New behavior

1. Start Inspection screen shows only Station selection.
2. Contract and Inspection Type are read-only auto-derived fields.
3. Non-admin users see only stations explicitly mapped in `user_station_access`.
4. `user_line_access` is no longer used for Start Inspection station dropdown.
5. Backend also enforces the same rule during `POST /api/v1/inspections/start`.
6. A stale frontend cannot bypass the rule by posting contract_id / inspection_type.

## Important rule

For Start Inspection, station permission is:

```text
users.id -> user_station_access.user_id -> user_station_access.station_id
```

Not:

```text
users.id -> user_line_access.line_id -> all stations of that line
```

## Rebuild commands

```bash
docker compose build --no-cache api frontend
docker compose up -d api frontend nginx
```

Then hard refresh browser:

```text
Ctrl + F5
```

## Quick verification

After login as the new user, open browser DevTools > Network and call:

```text
GET /api/v1/inspections/start-options
```

The `stations` array should contain only rows from `user_station_access` for that user.
