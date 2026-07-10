# MCH Weekly Compliance Report Patch

## Purpose

This patch changes login weekly inspection notification from a single total count into a station-wise compliance model.

It adds a dedicated page for the full list because the report can be large for LM/DGM/GM hierarchy users.

## Replace files

```text
backend/app/api/v1/router.py
frontend/src/components/AppLayout.vue
frontend/src/router/index.js
```

## Add files

```text
backend/app/api/v1/endpoints/weekly_compliance.py
frontend/src/views/WeeklyComplianceView.vue
```

## Rebuild

```bat
docker compose up -d --build api frontend
```

## New API endpoints

```text
GET /api/v1/weekly-compliance/summary
GET /api/v1/weekly-compliance/report
```

## New frontend page

```text
/inspections/weekly-compliance
```

## Logic

- SM target: 3 submitted inspections per assigned station per current week.
- EIT target: 1 submitted inspection per assigned station per current week.
- Week range: Monday to Sunday.
- Counted statuses: submitted/reviewed/approved/rejected/closed workflow statuses.
- Draft and returned inspections are not counted as completed weekly inspections.
- SM/EIT users see their own mapped station rows.
- LM users see their hierarchy's SM/EIT rows.
- DGM users see LM subtree rows.
- GM/Ops/admin scope sees all visible hierarchy rows according to existing scope logic.

## Login popup behavior

- Popup now mentions station-wise weekly compliance.
- Popup shows total required, completed and remaining.
- Popup includes a link/button to the full Weekly Compliance page.
- Existing Action Required and Review Queue notifications continue to work.

## DB migration

No DB migration is required.
