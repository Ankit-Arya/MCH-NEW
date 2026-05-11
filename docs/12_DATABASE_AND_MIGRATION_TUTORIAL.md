# Database and Migration Tutorial

This document explains the PostgreSQL schema, SQLAlchemy models, Alembic migrations and seed data.

---

## 1. Database technology

The project uses:

```text
PostgreSQL 16
SQLAlchemy ORM
Alembic migrations
Pydantic schemas for API validation
```

PostgreSQL runs in Docker using the `postgres` service.

---

## 2. Database connection

The backend reads this from `.env`:

```text
DATABASE_URL=postgresql+psycopg2://mch_user:mch_password@postgres:5432/mch_inspection
```

Inside Docker, hostname is:

```text
postgres
```

Do not use `localhost` in `DATABASE_URL` inside Docker containers.

---

## 3. Main model file

Models are defined in:

```text
backend/app/models/all_models.py
```

The file contains all tables and relationships.

---

## 4. Table groups

### 4.1 User and security tables

```text
roles
users
user_station_access
user_line_access
```

Purpose:

```text
Store users, roles and where each user is allowed to work/review.
```

Important relation:

```text
users.role_id → roles.id
user_station_access.user_id → users.id
user_station_access.station_id → stations.id
user_line_access.user_id → users.id
user_line_access.line_id → lines.id
```

---

### 4.2 Station and contract master tables

```text
lines
stations
contractors
contracts
contract_stations
```

Purpose:

```text
Store metro lines, stations, contractors, contracts and mapping between contracts and stations.
```

Important relation:

```text
stations.line_id → lines.id
contracts.contractor_id → contractors.id
contract_stations.contract_id → contracts.id
contract_stations.station_id → stations.id
```

The backend validates that station is mapped to contract before allowing inspection.

---

### 4.3 Grading and checklist tables

```text
grading_schemes
grading_options
inspection_attributes
inspection_sub_areas
```

Purpose:

```text
Store configurable grading scale and checklist structure.
```

This is important because the requirement had two possible grading scales. The system should not hardcode grade values in code.

Example grading options:

```text
A = 100
B = 90
C = 80
D = 70
E = 60
F = 50
```

or:

```text
A = 100
B = 80
C = 60
D = 40
E = 20
F = 0
```

A contract points to one grading scheme:

```text
contracts.grading_scheme_id → grading_schemes.id
```

---

### 4.4 Inspection transaction tables

```text
inspections
inspection_attribute_scores
inspection_sub_area_observations
inspection_media
```

Purpose:

```text
Store every inspection, its grading, sub-area observation and photo/video metadata.
```

Important relation:

```text
inspection_attribute_scores.inspection_id → inspections.id
inspection_sub_area_observations.inspection_id → inspections.id
inspection_media.inspection_id → inspections.id
```

Important unique constraints:

```text
one score per inspection per attribute
one observation per inspection per sub-area
```

This prevents duplicate accidental scores.

---

### 4.5 Workflow tables

```text
inspection_reviews
inspection_workflow_history
```

Purpose:

```text
Store review comments/actions and full status movement history.
```

`inspection_reviews` stores actual review entries.

`inspection_workflow_history` stores status transitions:

```text
DRAFT → UNDER_LINE_MANAGER_REVIEW
UNDER_LINE_MANAGER_REVIEW → LINE_MANAGER_RECOMMENDED
LINE_MANAGER_RECOMMENDED → DGM_APPROVED
```

---

### 4.6 KPI and penalty tables

```text
billing_cycles
monthly_bill_values
monthly_station_scores
monthly_contract_scores
penalty_calculations
```

Purpose:

```text
Store monthly billing period, bill value, station score, contract score and penalty.
```

Important relation:

```text
monthly_station_scores.billing_cycle_id → billing_cycles.id
monthly_station_scores.contract_id → contracts.id
monthly_station_scores.station_id → stations.id
penalty_calculations.billing_cycle_id → billing_cycles.id
penalty_calculations.contract_id → contracts.id
```

---

### 4.7 Audit and notification tables

```text
audit_logs
notifications
```

Purpose:

```text
Store traceability and in-app user notifications.
```

Audit logs should be append-only.

---

## 5. Entity relationship overview

```mermaid
erDiagram
    roles ||--o{ users : has
    users ||--o{ user_station_access : has
    users ||--o{ user_line_access : has

    lines ||--o{ stations : contains
    contractors ||--o{ contracts : owns
    contracts ||--o{ contract_stations : maps
    stations ||--o{ contract_stations : belongs

    grading_schemes ||--o{ grading_options : has
    grading_schemes ||--o{ contracts : used_by

    inspection_attributes ||--o{ inspection_sub_areas : contains
    inspections ||--o{ inspection_attribute_scores : has
    inspections ||--o{ inspection_sub_area_observations : has
    inspections ||--o{ inspection_media : has
    inspections ||--o{ inspection_reviews : reviewed_by
    inspections ||--o{ inspection_workflow_history : tracks

    billing_cycles ||--o{ monthly_station_scores : has
    billing_cycles ||--o{ monthly_contract_scores : has
    billing_cycles ||--o{ penalty_calculations : has
```

---

## 6. Alembic migration files

Location:

```text
backend/alembic/
```

Important files:

```text
alembic.ini
alembic/env.py
alembic/versions/0001_initial_schema.py
```

Run migrations:

```bash
docker compose exec api alembic upgrade head
```

Check current migration:

```bash
docker compose exec api alembic current
```

Create new migration after model change:

```bash
docker compose exec api alembic revision --autogenerate -m "add new column"
```

Then apply:

```bash
docker compose exec api alembic upgrade head
```

---

## 7. Important migration rule

Do not edit old migration files after production deployment.

Correct process:

```text
1. Change SQLAlchemy model.
2. Generate new migration.
3. Review generated migration.
4. Apply on development.
5. Test.
6. Apply on production during maintenance window.
```

---

## 8. Seed data

Seed file:

```text
backend/app/seeds/seed.py
```

Run:

```bash
docker compose exec api python -m app.seeds.seed
```

Seed data usually creates:

```text
roles
admin user
sample line
sample stations
sample contractor
sample contract
grading scheme
KPI-6 attributes
sub-areas
billing cycle
```

After running seed, login with the seeded admin user defined in the seed file.

Production rule: change seeded admin password immediately after first login.

---

## 9. How inspection data is stored

### Step 1: start inspection

Insert into:

```text
inspections
inspection_workflow_history
audit_logs
```

Status:

```text
DRAFT
```

### Step 2: save grading

Insert/update:

```text
inspection_attribute_scores
inspection_sub_area_observations
```

### Step 3: upload media

Insert into:

```text
inspection_media
```

Actual file goes to MinIO.

### Step 4: submit inspection

Update:

```text
inspections.status = UNDER_LINE_MANAGER_REVIEW
inspections.submitted_at = current time
```

Insert:

```text
inspection_workflow_history
audit_logs
```

---

## 10. How monthly KPI data is stored

When monthly calculation runs:

```text
monthly_station_scores
monthly_contract_scores
penalty_calculations
```

are inserted or updated.

The calculation is idempotent for the same billing cycle and contract because unique constraints prevent duplicate rows.

---

## 11. Useful database commands

Open psql inside container:

```bash
docker compose exec postgres psql -U mch_user -d mch_inspection
```

List tables:

```sql
\dt
```

Describe table:

```sql
\d inspections
```

Check users:

```sql
select id, username, name, is_active from users;
```

Check inspections:

```sql
select id, inspection_no, station_id, inspection_type, status, submitted_at from inspections order by id desc;
```

Check workflow history:

```sql
select inspection_id, from_status, to_status, action, created_at from inspection_workflow_history order by id desc;
```

Check audit logs:

```sql
select actor_user_id, action, entity_type, entity_id, created_at from audit_logs order by id desc limit 50;
```

---

## 12. How to add a new column

Example: add `contract_reference_no` to contracts.

### Step 1: edit model

File:

```text
backend/app/models/all_models.py
```

Add:

```python
contract_reference_no: Mapped[str | None] = mapped_column(String(100))
```

### Step 2: update schema

File:

```text
backend/app/schemas/master.py
```

Add field in create/out schema if required.

### Step 3: generate migration

```bash
docker compose exec api alembic revision --autogenerate -m "add contract reference no"
```

### Step 4: review migration

Open generated file under:

```text
backend/alembic/versions/
```

### Step 5: apply migration

```bash
docker compose exec api alembic upgrade head
```

---

## 13. Backup and restore basics

Backup script included:

```text
scripts/backup_postgres.sh
```

Manual backup:

```bash
docker compose exec postgres pg_dump -U mch_user mch_inspection > backup.sql
```

Restore:

```bash
cat backup.sql | docker compose exec -T postgres psql -U mch_user -d mch_inspection
```

Production recommendation:

```text
Take daily PostgreSQL backups.
Take daily MinIO backup.
Keep at least one backup outside the application server.
Test restore every week/month.
```

---

## 14. Database production checklist

Before production:

```text
Change database password.
Do not expose port 5432 to users.
Enable regular backups.
Test restore.
Create indexes after observing slow queries.
Keep migrations under version control.
Do not allow direct DB edits except controlled admin operations.
```
