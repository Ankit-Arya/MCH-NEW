# KPI & Penalty page insight fix

Drop this file into the repo:

```text
frontend/src/views/KpiDashboardView.vue
```

Then rebuild/restart the frontend:

```bash
docker compose up -d --build frontend
```

## What changed

- Removed raw Billing Cycle ID / Contract ID text boxes from the user flow.
- Added readable selectors for billing month, contract and station.
- Added insight cards for selected period, contracts reviewed, average score, penalty cases and attention stations.
- Added exception list for low-score stations and missing SM/EIT inspection coverage.
- Added readable Contract KPI Register with contract name, contract code, threshold and evidence actions.
- Added readable Penalty Register with bill value, score and penalty amount.
- Added Station score drill-down so users can understand why a penalty was generated.
- Added View/Download monthly evidence report directly from KPI page using existing inspection report API.

No database migration is required.
