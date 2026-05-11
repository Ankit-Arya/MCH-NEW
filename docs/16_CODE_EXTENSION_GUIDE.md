# Code Extension Guide

This document explains how to safely add new features to the project.

---

## 1. General rule for adding features

Follow this order:

```text
1. Understand business rule.
2. Update database model if needed.
3. Create migration.
4. Update Pydantic schema.
5. Add service logic.
6. Add endpoint.
7. Add frontend API call.
8. Add frontend screen/component.
9. Add tests.
10. Update docs.
```

Do not put complex business rules directly inside Vue components or FastAPI endpoint functions.

---

## 2. How to add a new master data field

Example: add `zone` to station.

### Backend model

Edit:

```text
backend/app/models/all_models.py
```

Add to `Station`:

```python
zone: Mapped[str | None] = mapped_column(String(80))
```

### Schema

Edit:

```text
backend/app/schemas/master.py
```

Add:

```python
zone: str | None = None
```

### Migration

```bash
docker compose exec api alembic revision --autogenerate -m "add zone to station"
docker compose exec api alembic upgrade head
```

### Frontend

Update forms/tables in:

```text
frontend/src/views/MasterDataView.vue
```

---

## 3. How to add a new inspection sub-area

Preferred way: insert into `inspection_sub_areas` through admin/master data UI or seed script.

Sub-area fields:

```text
attribute_id
code
name
photo_min_required
photo_max_allowed
video_required
video_max_seconds
allow_na
sort_order
is_active
```

No frontend code change is required if the checklist API returns it, because `InspectionFormView.vue` renders checklist dynamically.

---

## 4. How to change grading scale

Do not change KPI code.

Update:

```text
grading_schemes
grading_options
contracts.grading_scheme_id
```

Example:

```text
A = 100
B = 80
C = 60
D = 40
E = 20
F = 0
```

The backend reads grading percentage from database when saving draft.

---

## 5. How to add a new review action

Example: add `ESCALATE_TO_HK_CELL`.

### Step 1: Add enum

File:

```text
backend/app/models/all_models.py
```

Update `ReviewAction`:

```python
ESCALATE_TO_HK_CELL = "ESCALATE_TO_HK_CELL"
```

### Step 2: Add status if needed

Update `InspectionStatus` if this action has a new workflow state.

### Step 3: Update service

File:

```text
backend/app/services/review_service.py
```

Add allowed role and transition.

### Step 4: Update frontend

Add action button/dropdown in review screen.

### Step 5: Test workflow history

Ensure new action creates:

```text
inspection_reviews
inspection_workflow_history
audit_logs
```

---

## 6. How to add offline inspection support

Recommended approach:

```text
1. Use PWA service worker.
2. Store draft inspection in IndexedDB.
3. Store media temporarily in browser storage.
4. Add sync queue.
5. When network returns, upload media first.
6. Then save draft/submit.
7. Resolve conflicts using inspection status.
```

Frontend files likely involved:

```text
frontend/public/manifest.webmanifest
frontend/src/views/InspectionFormView.vue
frontend/src/services/api.js
new file: frontend/src/services/offlineQueue.js
```

Backend should support idempotency key to avoid duplicate submissions.

Add field:

```text
client_request_id
```

in inspection/media tables if offline mode is required.

---

## 7. How to add PDF report generation

Recommended production design:

```text
FastAPI endpoint receives report request.
Worker generates PDF.
PDF stored in MinIO.
API returns download URL or report job id.
```

Backend additions:

```text
services/report_service.py
workers/report_tasks.py
api/v1/endpoints/reports.py
models: generated_reports table optional
```

PDF libraries:

```text
WeasyPrint
ReportLab
wkhtmltopdf
```

Recommended flow:

```text
HTML template → PDF → MinIO → signed URL
```

---

## 8. How to add Excel export

Backend endpoint:

```text
GET /api/v1/reports/monthly-score/excel
```

Use:

```text
openpyxl
```

Flow:

```text
query monthly_station_scores/monthly_contract_scores
create workbook
write headers
write rows
return StreamingResponse
```

---

## 9. How to add notifications

Existing table:

```text
notifications
```

Recommended service:

```text
backend/app/services/notification_service.py
```

Function:

```python
def notify_user(db, user_id, title, message, entity_type=None, entity_id=None):
    ...
```

Trigger notifications on:

```text
inspection submitted
inspection returned
penalty recommended
DGM approval required
GM review required
monthly KPI calculated
```

Frontend:

```text
Add notification icon in AppLayout.vue
Add NotificationsView.vue
Add API endpoint /notifications
```

---

## 10. How to add email/SMS later

Do not send email/SMS directly inside request cycle.

Recommended:

```text
1. Insert notification row.
2. Queue Celery task.
3. Worker sends email/SMS.
4. Store delivery status.
```

Tables to add:

```text
notification_deliveries
```

Fields:

```text
notification_id
channel
recipient
status
provider_response
sent_at
```

---

## 11. How to add role-based side menu

Frontend:

```text
src/components/AppLayout.vue
src/stores/auth.js
```

Create menu config:

```javascript
const menu = [
  { label: 'Dashboard', to: '/', roles: ['SUPER_ADMIN','GM_OPS','STATION_MANAGER'] },
  { label: 'Start Inspection', to: '/inspections/start', roles: ['STATION_MANAGER','EIT_MEMBER'] },
  { label: 'Reviews', to: '/reviews', roles: ['AM_MGR_LINE','DGM_LINE','GM_OPS'] },
  { label: 'KPI', to: '/kpi', roles: ['HK_CELL_ADMIN','DGM_HK','GM_OPS'] }
]
```

Render only allowed links.

Backend still remains final authority.

---

## 12. How to add tests

Backend tests location:

```text
backend/tests/
```

Add tests for:

```text
login
start inspection
station access denied
submit validation
review transitions
KPI calculation
```

Run tests:

```bash
docker compose exec api pytest
```

Example test idea:

```text
Create inspection with missing photo.
Call submit.
Expect 400 error.
```

---

## 13. How to split into real microservices later

Current design is modular monolith. If scale requires, split carefully.

Possible future services:

```text
Auth service
Inspection service
Media service
KPI service
Report service
Notification service
```

Do not split too early. First make modules stable.

When splitting:

```text
Define API contracts.
Avoid shared database writes from multiple services.
Use message queue for events.
Keep audit centralized.
```

---

## 14. Safe coding checklist

Before committing code:

```text
No hardcoded passwords.
No direct DB credentials in code.
All protected endpoints use get_current_user.
All station-specific actions check require_station_access.
All role-specific actions check require_roles.
Migrations generated and reviewed.
Frontend uses common api.js.
Errors are user-friendly.
Audit log added for important actions.
Docs updated.
```

---

## 15. Suggested next development improvements

Recommended next features:

```text
1. Full review detail page with media viewer.
2. Production PDF report template.
3. Excel export for monthly scores and penalties.
4. User assignment UI.
5. Contract-station mapping UI.
6. Billing cycle and bill value UI.
7. Notification center.
8. Offline draft mode.
9. Media compression and duration validation worker.
10. Dashboard charts and filters.
```
