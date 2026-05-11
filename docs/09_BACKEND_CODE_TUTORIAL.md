# Backend Code Tutorial — FastAPI

This document explains how the backend code works file by file and how a request flows through the backend.

Backend location:

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── workers/
│   └── seeds/
├── alembic/
├── Dockerfile
└── requirements.txt
```

---

## 1. Backend design pattern

The backend follows this layered pattern:

```text
HTTP Request
    ↓
FastAPI endpoint file in app/api/v1/endpoints/
    ↓
Pydantic schema in app/schemas/
    ↓
Permission checks in app/core/permissions.py
    ↓
Business logic in app/services/
    ↓
SQLAlchemy model in app/models/all_models.py
    ↓
PostgreSQL database
```

This separation is important because controllers/endpoints should stay thin. Business rules like inspection validation, review status transition and KPI calculation should be inside service files.

---

## 2. `app/main.py`

This is the backend entry point.

Main responsibilities:

- Creates the FastAPI app.
- Adds CORS middleware so Vue can call the API.
- Registers the API router under `/api/v1`.
- Exposes health endpoint `/api/health`.
- Optionally creates tables on startup if `AUTO_CREATE_TABLES=true`.

Important code flow:

```text
app = FastAPI(...)
app.add_middleware(CORSMiddleware, ...)
app.include_router(api_router, prefix=settings.API_PREFIX)
```

When Docker starts the backend, it runs:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
```

So `app/main.py` is the first file loaded by the API container.

---

## 3. `app/api/v1/router.py`

This file combines all endpoint modules.

It registers:

```text
/auth
/users
/master
/inspections
/reviews
/kpi
/dashboard
/reports
```

Example:

```python
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(inspections.router, prefix="/inspections", tags=["Inspections"])
```

So the endpoint in `auth.py`:

```text
POST /login
```

becomes:

```text
POST /api/v1/auth/login
```

because `main.py` adds `/api/v1` and `router.py` adds `/auth`.

---

## 4. `app/core/config.py`

This file reads application settings from `.env`.

Important settings:

```text
DATABASE_URL
SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES
MINIO_ENDPOINT
MINIO_ACCESS_KEY
MINIO_SECRET_KEY
REDIS_URL
CELERY_BROKER_URL
KPI6_SM_WEIGHT
KPI6_EIT_WEIGHT
KPI6_THRESHOLD_PERCENT
KPI6_PENALTY_PERCENT
```

The backend uses `pydantic-settings`, so every variable can be controlled through environment variables.

Example:

```python
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://..."
    MINIO_ENDPOINT: str = "minio:9000"
```

Production rule: never keep the default `SECRET_KEY` or database passwords.

---

## 5. `app/core/database.py`

This file creates the SQLAlchemy database engine and session.

Important flow:

```python
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(...)
```

The `get_db()` function is used as a FastAPI dependency:

```python
def some_endpoint(db: Session = Depends(get_db)):
    ...
```

FastAPI opens a database session for the request and closes it after the request finishes.

---

## 6. `app/core/security.py`

This file handles password hashing and JWT tokens.

Functions:

```text
verify_password()
get_password_hash()
create_access_token()
create_refresh_token()
decode_token()
```

Login flow:

```text
User enters username/password
    ↓
backend checks password hash
    ↓
backend returns access token and refresh token
    ↓
frontend sends access token in Authorization header
```

Frontend header format:

```text
Authorization: Bearer <access_token>
```

---

## 7. `app/core/deps.py`

This file contains reusable FastAPI dependencies.

Main dependency:

```python
get_current_user()
```

It does this:

```text
Read bearer token
Decode JWT
Find user in PostgreSQL
Reject if user is inactive or missing
Return User object
```

Use it in endpoints like this:

```python
def my_endpoint(user: User = Depends(get_current_user)):
    ...
```

This ensures only logged-in users can access protected APIs.

---

## 8. `app/core/permissions.py`

This file handles role and station access validation.

Important functions:

```text
has_role(user, roles)
require_roles(user, roles)
can_access_station(db, user, station_id)
require_station_access(db, user, station_id)
```

Important concept:

```text
Role alone is not enough.
A user must also have station or line access unless they are admin-level.
```

Admin-level roles:

```text
SUPER_ADMIN
GM_OPS
HK_CELL_ADMIN
```

Example:

```python
require_station_access(db, user, payload.station_id)
```

This prevents a Station Manager from submitting an inspection for a station outside his/her access.

---

## 9. `app/models/base.py`

This file defines the SQLAlchemy declarative base:

```python
class Base(DeclarativeBase):
    pass
```

All model classes inherit from this base.

---

## 10. `app/models/all_models.py`

This is the main database model file.

It includes:

### User and access models

```text
Role
User
UserStationAccess
UserLineAccess
```

### Metro and contract master models

```text
Line
Station
Contractor
Contract
ContractStation
```

### Grading and checklist models

```text
GradingScheme
GradingOption
InspectionAttribute
InspectionSubArea
```

### Inspection transaction models

```text
Inspection
InspectionAttributeScore
InspectionSubAreaObservation
InspectionMedia
```

### Workflow models

```text
InspectionReview
InspectionWorkflowHistory
```

### KPI and penalty models

```text
BillingCycle
MonthlyBillValue
MonthlyStationScore
MonthlyContractScore
PenaltyCalculation
```

### Support models

```text
Notification
AuditLog
```

### Important enums

```text
RoleCode
InspectionType
InspectionStatus
ReviewAction
MediaType
```

These enums are used to avoid random status strings in the system.

---

## 11. `app/schemas/`

Schemas define API request and response formats using Pydantic.

### `schemas/auth.py`

Used by login and `/me` APIs.

```text
LoginRequest
TokenResponse
UserMe
```

### `schemas/master.py`

Used for creating and returning master data.

```text
StationCreate
StationOut
ContractCreate
ContractOut
```

### `schemas/inspection.py`

Used by inspection APIs.

```text
InspectionStartIn
AttributeScoreIn
SubAreaObservationIn
InspectionDraftIn
InspectionOut
MediaOut
```

### `schemas/review.py`

Used by review APIs.

```text
ReviewIn
ReviewOut
```

### `schemas/kpi.py`

Used by monthly KPI calculation.

```text
MonthlyCalculationRequest
MonthlyCalculationResponse
```

Rule: every endpoint should accept and return schema objects instead of raw dictionaries whenever possible.

---

## 12. Auth endpoints — `endpoints/auth.py`

Base path:

```text
/api/v1/auth
```

Endpoints:

```text
POST /login
POST /refresh
GET  /me
POST /logout
```

### Login process

```text
1. Find user by username.
2. Verify password using bcrypt hash.
3. Reject if inactive.
4. Update last_login_at.
5. Insert audit log LOGIN_SUCCESS or LOGIN_FAILED.
6. Return JWT access and refresh token.
```

### `/me`

Returns current logged-in user information:

```json
{
  "id": 1,
  "username": "admin",
  "name": "System Admin",
  "role": "SUPER_ADMIN",
  "permissions": ["SUPER_ADMIN"]
}
```

---

## 13. Master data endpoints — `endpoints/master.py`

Base path:

```text
/api/v1/master
```

Important endpoints:

```text
GET  /bootstrap
GET  /stations
POST /stations
GET  /contracts
POST /contracts
GET  /inspection-attributes
GET  /grading-schemes
```

### `/bootstrap`

This endpoint is useful for frontend dropdowns. It returns:

```text
lines
stations
contracts
attributes
grading_schemes
```

Frontend uses it in `InspectionStartView.vue` and master data screens.

---

## 14. Inspection endpoints — `endpoints/inspections.py`

Base path:

```text
/api/v1/inspections
```

Endpoints:

```text
GET    /
GET    /checklist
GET    /{inspection_id}
POST   /start
PUT    /{inspection_id}/draft
POST   /{inspection_id}/submit
POST   /{inspection_id}/media
```

### Start inspection

Endpoint:

```text
POST /api/v1/inspections/start
```

Calls service function:

```python
create_inspection(db, payload, user)
```

What it does:

```text
1. Checks station access.
2. Checks station is mapped to selected contract.
3. Creates inspection number.
4. Saves GPS and device details.
5. Marks whether inspection is before 10 AM.
6. Sets status as DRAFT.
7. Inserts workflow history START.
8. Inserts audit log INSPECTION_STARTED.
```

### Save draft

Endpoint:

```text
PUT /api/v1/inspections/{id}/draft
```

Calls:

```python
save_draft(db, inspection, payload, user)
```

It saves:

```text
attribute scores
sub-area observations
remarks
```

It does not submit the inspection.

### Submit inspection

Endpoint:

```text
POST /api/v1/inspections/{id}/submit
```

Calls:

```python
submit_inspection(db, inspection, payload, user)
```

Validation before submit:

```text
All active attributes must have grading.
Each applicable sub-area must have minimum required photos.
N/A sub-area must have reason.
```

After successful submit:

```text
status changes from DRAFT to UNDER_LINE_MANAGER_REVIEW
submitted_at is set
workflow history is inserted
audit log is inserted
```

---

## 15. Media upload endpoint

Endpoint:

```text
POST /api/v1/inspections/{id}/media
```

Request type:

```text
multipart/form-data
```

Fields:

```text
attribute_id
sub_area_id
media_type = PHOTO or VIDEO
file
captured_latitude optional
captured_longitude optional
gps_accuracy optional
captured_at optional
```

Flow:

```text
Vue selects photo/video
    ↓
FastAPI reads file bytes
    ↓
SHA256 checksum generated
    ↓
object path created
    ↓
file uploaded to MinIO
    ↓
metadata saved in inspection_media table
```

Important: PostgreSQL stores only metadata. Actual binary media is stored in MinIO.

---

## 16. Review endpoints — `endpoints/reviews.py`

Base path:

```text
/api/v1/reviews
```

Endpoints:

```text
GET  /pending
POST /{inspection_id}/line-manager
POST /{inspection_id}/dgm
POST /{inspection_id}/gm
```

Review service file:

```text
app/services/review_service.py
```

### Line Manager review

Allowed roles:

```text
AM_MGR_LINE
DGM_LINE
SUPER_ADMIN
```

Allowed actions:

```text
RETURN_FOR_CLARIFICATION
RECOMMEND_PENALTY
```

Status transition:

```text
UNDER_LINE_MANAGER_REVIEW
    → RETURNED_FOR_CLARIFICATION
or
UNDER_LINE_MANAGER_REVIEW
    → LINE_MANAGER_RECOMMENDED
```

### DGM review

Allowed roles:

```text
DGM_LINE
DGM_HK
SUPER_ADMIN
```

Allowed actions:

```text
APPROVE
REJECT
SEND_TO_GM
```

Status transition:

```text
LINE_MANAGER_RECOMMENDED → DGM_APPROVED
LINE_MANAGER_RECOMMENDED → DGM_REJECTED
LINE_MANAGER_RECOMMENDED → GM_REVIEW_REQUIRED
```

### GM review

Allowed roles:

```text
GM_OPS
SUPER_ADMIN
```

Status transition:

```text
GM_REVIEW_REQUIRED → GM_REVIEWED
```

---

## 17. KPI endpoints — `endpoints/kpi.py`

Base path:

```text
/api/v1/kpi
```

Endpoints:

```text
POST /calculate/monthly
GET  /station-scores
GET  /contract-scores
GET  /penalties
```

Monthly calculation calls:

```python
calculate_monthly_kpi6(db, billing_cycle_id, contract_id)
```

Allowed roles for monthly calculation:

```text
SUPER_ADMIN
HK_CELL_ADMIN
DGM_HK
GM_OPS
```

---

## 18. KPI calculation service — `services/kpi_calculation_service.py`

This file calculates monthly KPI-6 score and penalty.

### Internal function `_inspection_score()`

Calculates the average of attribute grading percentages for one inspection.

```text
inspection score = average of all attribute grade percentages
```

### Internal function `_average_for_type()`

Calculates average score for one station, one contract, one billing cycle and one inspection type.

Inspection types:

```text
SM_INSPECTION
EIT_INSPECTION
```

### Main function `calculate_monthly_kpi6()`

Flow:

```text
1. Load billing cycle.
2. Load contract.
3. Fetch active stations mapped to contract.
4. For each station:
   - calculate SM average
   - calculate EIT average
   - final score = SM avg × 0.6 + EIT avg × 0.4
   - save monthly_station_scores
5. Average all station scores.
6. If contract average < threshold, penalty applies.
7. Penalty = monthly bill value × penalty percent / 100.
8. Save monthly_contract_scores.
9. Save penalty_calculations.
```

---

## 19. Dashboard endpoints — `endpoints/dashboard.py`

Base path:

```text
/api/v1/dashboard
```

Endpoints:

```text
GET /summary
GET /contract-wise-score
GET /pending-reviews
```

The Vue dashboard uses `/dashboard/summary` to show quick cards.

---

## 20. Reports endpoint — `endpoints/reports.py`

Base path:

```text
/api/v1/reports
```

Endpoint:

```text
GET /inspection/{inspection_id}/pdf
```

Current implementation returns a basic PDF-style response structure. In production, this can be extended using:

```text
WeasyPrint
ReportLab
HTML templates
PDF generation worker
```

Recommended production approach:

```text
1. Create HTML report template.
2. Fill inspection data.
3. Convert to PDF.
4. Store generated PDF in MinIO.
5. Return signed download URL.
```

---

## 21. Audit service — `services/audit_service.py`

This service inserts rows into `audit_logs`.

Every important action should call:

```python
audit_log(db, actor=user, action="ACTION_NAME", entity_type="Inspection", entity_id=inspection.id)
```

Examples already used:

```text
LOGIN_SUCCESS
LOGIN_FAILED
INSPECTION_STARTED
INSPECTION_DRAFT_SAVED
INSPECTION_SUBMITTED
LINE_MANAGER_REVIEW
DGM_REVIEW
GM_REVIEW
```

Production rule: audit logs should be append-only. Do not update or delete audit logs from normal application code.

---

## 22. Worker files — `app/workers/`

### `celery_app.py`

Creates the Celery application using Redis as broker and backend.

### `tasks.py`

Contains placeholder background tasks.

Use workers for tasks that should not block HTTP request:

```text
video duration validation
image compression
PDF generation
monthly scheduled KPI calculation
email/SMS notifications
backup notification
```

---

## 23. Seed file — `app/seeds/seed.py`

This file inserts default master data.

It should create data such as:

```text
roles
admin user
lines
stations
contractor
contract
grading scheme
KPI attributes
sub-areas
billing cycle
```

Run it after migrations:

```bash
docker compose exec api python -m app.seeds.seed
```

---

## 24. How to add a new backend endpoint

Example: add endpoint to list penalties by contract.

### Step 1: Add schema if needed

Create or update a file in:

```text
app/schemas/kpi.py
```

### Step 2: Add service logic

Add reusable logic in:

```text
app/services/kpi_calculation_service.py
```

### Step 3: Add endpoint

Edit:

```text
app/api/v1/endpoints/kpi.py
```

Example:

```python
@router.get("/penalties/contract/{contract_id}")
def penalties_by_contract(contract_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(PenaltyCalculation).filter_by(contract_id=contract_id).all()
```

### Step 4: Test in Swagger

Open:

```text
http://localhost/api/docs
```

---

## 25. Backend debugging checklist

### API not opening

Check:

```bash
docker compose logs api
```

### Database connection error

Check:

```bash
docker compose ps
docker compose logs postgres
cat .env
```

### Login not working

Check:

```text
seed data was run
user exists
password hash exists
SECRET_KEY did not change after login token was generated
```

### Permission denied

Check:

```text
user role
user_station_access
user_line_access
station_id passed by frontend
```

### Inspection submit failing

Check:

```text
all attributes have grade
all applicable sub-areas have required photo
N/A reason entered
media uploaded before submit
```
