# Master Data UI + CRUD Patch Guide

This patch converts the Master Data page from read-only seeded data into an operational UI where authorised users can create, edit and deactivate master records.

## 1. What this patch changes

### Backend replacement files

```text
backend/app/api/v1/endpoints/master.py
backend/app/schemas/master.py
```

### Frontend replacement file

```text
frontend/src/views/MasterDataView.vue
```

No database migration is required because this patch uses the existing master tables already present in the project.

## 2. Who can edit master data?

Only these roles can create, update or deactivate master data:

```text
SUPER_ADMIN
HK_CELL_ADMIN
```

Other roles can open the Master Data page in read-only mode.

In your UI, `SYSADMIN` means the existing project role:

```text
SUPER_ADMIN
```

## 3. Apply steps

From your project root:

```bash
# 1. Backup current files first
cp backend/app/api/v1/endpoints/master.py backend/app/api/v1/endpoints/master.py.bak
cp backend/app/schemas/master.py backend/app/schemas/master.py.bak
cp frontend/src/views/MasterDataView.vue frontend/src/views/MasterDataView.vue.bak

# 2. Copy patch files into the same relative paths
# 3. Restart services

docker compose restart api frontend
```

If your frontend is running with Vite HMR, it may refresh automatically. If not:

```bash
docker compose restart frontend
```

## 4. Master data managed by UI

The new page has tabs for:

```text
Lines
Stations
Contractors
Contracts
Contract-station mapping
Inspection Attributes
Inspection Sub-areas
Grading Schemes
Grading Options
```

## 5. Why deactivate instead of delete?

Operational systems should not physically delete master records that may already be linked with inspections, reports, KPI calculations or audit history.

For records with `is_active`, this patch performs soft delete:

```text
is_active = false
```

Old records remain available for historical reports, while inactive records should not be selected for new operational work.

For `grading_options`, the current table does not have an `is_active` column. This patch deletes grading options physically. Do this carefully and avoid deleting options already used in submitted inspections.

## 6. Backend endpoint summary

```text
GET    /api/v1/master/bootstrap

GET    /api/v1/master/lines
POST   /api/v1/master/lines
PUT    /api/v1/master/lines/{id}
DELETE /api/v1/master/lines/{id}

GET    /api/v1/master/stations
POST   /api/v1/master/stations
PUT    /api/v1/master/stations/{id}
DELETE /api/v1/master/stations/{id}

GET    /api/v1/master/contractors
POST   /api/v1/master/contractors
PUT    /api/v1/master/contractors/{id}
DELETE /api/v1/master/contractors/{id}

GET    /api/v1/master/contracts
POST   /api/v1/master/contracts
PUT    /api/v1/master/contracts/{id}
DELETE /api/v1/master/contracts/{id}

GET    /api/v1/master/contracts/{contract_id}/stations
POST   /api/v1/master/contracts/{contract_id}/stations
DELETE /api/v1/master/contracts/{contract_id}/stations/{station_id}

GET    /api/v1/master/inspection-attributes
POST   /api/v1/master/inspection-attributes
PUT    /api/v1/master/inspection-attributes/{id}
DELETE /api/v1/master/inspection-attributes/{id}

GET    /api/v1/master/inspection-attributes/{attribute_id}/sub-areas
GET    /api/v1/master/inspection-sub-areas
POST   /api/v1/master/inspection-sub-areas
PUT    /api/v1/master/inspection-sub-areas/{id}
DELETE /api/v1/master/inspection-sub-areas/{id}

GET    /api/v1/master/grading-schemes
POST   /api/v1/master/grading-schemes
PUT    /api/v1/master/grading-schemes/{id}
DELETE /api/v1/master/grading-schemes/{id}

GET    /api/v1/master/grading-options
POST   /api/v1/master/grading-options
PUT    /api/v1/master/grading-options/{id}
DELETE /api/v1/master/grading-options/{id}
```

## 7. How frontend calls backend

`MasterDataView.vue` calls:

```js
api.get('/master/bootstrap')
```

This loads all master lists in one request so dropdowns and tables can be rendered together.

When user saves a new station, frontend calls:

```js
api.post('/master/stations', payload)
```

When user edits existing station, frontend calls:

```js
api.put(`/master/stations/${stationId}`, payload)
```

When user deactivates a station, frontend calls:

```js
api.delete(`/master/stations/${stationId}`)
```

The same pattern is used for lines, contractors, contracts, attributes, sub-areas and grading.

## 8. Validation and audit

Backend validates linked records before save. Example:

```text
Station cannot be created with invalid line_id.
Contract cannot be created with invalid contractor_id or grading_scheme_id.
Sub-area cannot be created with invalid attribute_id.
```

Every create/update/deactivate action is written to `audit_logs` using `audit_service.audit_log()`.

## 9. Testing checklist

Login as admin:

```text
admin / admin123
```

Then test:

```text
1. Open Master Data page.
2. Add a new line.
3. Add a new station under that line.
4. Add a contractor.
5. Add a contract.
6. Map station to contract.
7. Add an attribute.
8. Add a sub-area under that attribute.
9. Add a grading scheme.
10. Add grade options A/B/C etc.
11. Login as SM and verify page is read-only.
```

## 10. Production note

Before production, decide whether `HK_CELL_ADMIN` should be allowed to manage all master data or only contract/EIT/billing-related master data. If stricter access is needed, split permissions by module instead of using only broad roles.
