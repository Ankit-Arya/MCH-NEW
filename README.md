# MCH KPI-6 Real-Time Inspection Platform

Stack:

- **Backend:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, JWT RBAC
- **Frontend:** Vue 3, Vite, Pinia, Vue Router, PWA-ready responsive UI
- **Storage:** MinIO for geo/time-stamped photos and videos
- **Queue:** Redis + Celery for media/report/background jobs
- **Deployment:** Docker Compose + Nginx on-prem

This project implements the complete workflow reference:

1. Login and role-based access
2. Master data setup for lines, stations, contracts, users, grading, attributes, sub-areas
3. SM/EIT inspection capture with GPS, photos, videos, grading and draft/submission workflow
4. Line Manager review and penalty recommendation
5. DGM review and penalty decision
6. GM/Ops review where required
7. KPI-6 monthly score and penalty calculation
8. Dashboards, audit trail, workflow history and report endpoints


---

## Quick Start

### 1. Copy environment file

```bash
cp .env.example .env
```

### 2. Start all services

```bash
docker compose up -d --build
```

### 3. Run database migration

```bash
docker compose exec api alembic upgrade head
```

If you do not want to use Alembic during first local demo, set `AUTO_CREATE_TABLES=true` in `.env` and restart API.

### 4. Seed demo data

```bash
docker compose exec api python -m app.seeds.seed
```

### 5. Open application

```text
Frontend: http://localhost
Backend API docs: http://localhost/api/docs
MinIO console: http://localhost:9001
```

Demo users after seed:

| Role | Username | Password |
|---|---|---|
| Super Admin | admin | admin123 |
| Station Manager | sm01 | sm123 |
| EIT Member | eit01 | eit123 |
| Line Manager | lm01 | lm123 |
| DGM Line | dgm01 | dgm123 |
| GM/Ops | gm01 | gm123 |

---

## Documentation

Read these files in order:

1. [`docs/01_REQUIREMENT_TRACEABILITY.md`](docs/01_REQUIREMENT_TRACEABILITY.md)
2. [`docs/02_BACKEND_REFERENCE.md`](docs/02_BACKEND_REFERENCE.md)
3. [`docs/03_WORKFLOWS.md`](docs/03_WORKFLOWS.md)
4. [`docs/04_DATABASE_SCHEMA.md`](docs/04_DATABASE_SCHEMA.md)
5. [`docs/05_API_GUIDE.md`](docs/05_API_GUIDE.md)
6. [`docs/06_ON_PREM_DEPLOYMENT.md`](docs/06_ON_PREM_DEPLOYMENT.md)
7. [`docs/07_PRODUCTION_CHECKLIST.md`](docs/07_PRODUCTION_CHECKLIST.md)

---

## Project Structure

```text
mch-inspection-platform/
├── backend/             # FastAPI backend
├── frontend/            # Vue 3 frontend
├── nginx/               # On-prem reverse proxy config
├── scripts/             # Backup/restore/helper scripts
├── docs/                # Reference documentation
├── docker-compose.yml
├── .env.example
└── Makefile
```

---

## Important Production Notes

- Use HTTPS in production.
- Change all default passwords and secrets.
- Keep PostgreSQL and MinIO volumes on reliable storage.
- Schedule daily database and media backups.
- Use department-approved retention period.
- Keep submitted inspections append-only. Corrections should be via workflow addendum, not overwriting evidence.
- Confirm final grading scheme because the requirement contains two grading variants.

## Latest UI + Reports Update


See:

```text
docs/08_UI_REPORTS_DUMMY_DATA_UPDATE.md
```

After starting the stack and running migrations, run the seed command to load demo dashboard/report data:

```bash
docker compose exec api python -m app.seeds.seed
```

Recommended demo range in dashboard/reports:

```text
2026-01-01 to 2026-05-31
```
