# KPI Chemicals / Consumables Phase-1 Patch

This is a drop-in file-code patch for expanding the existing inspection workflow from KPI-6 only to a first additional KPI: Chemicals & Consumables.

## Files to replace

```text
backend/app/api/v1/router.py
backend/app/api/v1/endpoints/inspections.py
backend/app/api/v1/endpoints/reports.py
backend/app/schemas/inspection.py
frontend/src/router/index.js
frontend/src/components/AppLayout.vue
frontend/src/views/InspectionStartView.vue
frontend/src/views/InspectionFormView.vue
```

## Files to add

```text
backend/app/models/kpi_chemical.py
backend/app/api/v1/endpoints/kpi_chemicals.py
backend/scripts/20260629_kpi_chemicals_phase1.sql
frontend/src/views/ChemicalMasterView.vue
```

## Run DB patch

Windows CMD:

```bat
type backend\scripts\20260629_kpi_chemicals_phase1.sql | docker compose exec -T postgres psql -U mch_user -d mch_inspection
```

PowerShell:

```powershell
Get-Content .\backend\scripts\20260629_kpi_chemicals_phase1.sql | docker compose exec -T postgres psql -U mch_user -d mch_inspection
```

## Rebuild

```bat
docker compose up -d --build api frontend
```

## What is included

- Start Inspection now starts with KPI selection.
- KPI-6 keeps the existing familiar attribute → sub-area → grade → photo workflow.
- Chemicals & Consumables opens a similar inspection page but uses:
  - fixed attribute: Supply & utilization of Chemicals & Consumables,
  - sub-area/item: station-mapped chemical/consumable,
  - required quantity from station master,
  - actual quantity entered during inspection,
  - difference / shortfall / availability percentage.
- New Chemical Mapping page:
  - `/master/chemicals`
  - create/edit chemical master list,
  - map required quantity station-wise.
- PDF report includes chemical required quantity, actual quantity, difference, shortfall, availability percentage and remarks.
- Existing review/approval workflow is reused.

## Note

The attached reference tender shows Chemicals & Consumables as a shortfall-based KPI where score comes from cumulative shortfall and penalty applies below 90% pass percentage. This patch implements that first chemical KPI workflow. If your internal numbering calls this KPI-2 instead of the tender's KPI-3, only the display label needs adjusting; the internal code used here is `KPI_CHEMICALS`.
