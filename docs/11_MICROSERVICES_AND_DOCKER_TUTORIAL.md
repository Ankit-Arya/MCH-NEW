# Microservices and Docker Tutorial

This project is hosted on-prem using Docker Compose. There is no Kubernetes and no cloud dependency.

The term “microservices” in this project mainly means supporting service containers around the FastAPI application:

```text
Nginx
Vue frontend
FastAPI API
PostgreSQL
Redis
MinIO
Celery worker
Celery scheduler
```

The backend is intentionally a modular monolith. This keeps deployment simple while still keeping modules separated in code.

---

## 1. Docker services overview

From `docker-compose.yml`:

```text
postgres    PostgreSQL database
redis       Queue/cache service
minio       On-prem object storage for photos/videos
api         FastAPI backend
worker      Celery background worker
scheduler   Celery beat scheduler
frontend    Vue static frontend served by Nginx
nginx       Main reverse proxy
```

---

## 2. High-level container data flow

```mermaid
flowchart LR
    Browser[Mobile/Desktop Browser] --> Nginx[nginx container]
    Nginx --> Frontend[frontend container]
    Nginx --> API[api container]
    API --> Postgres[(postgres container)]
    API --> MinIO[(minio container)]
    API --> Redis[(redis container)]
    Redis --> Worker[worker container]
    Scheduler[scheduler container] --> Redis
    Worker --> Postgres
    Worker --> MinIO
```

---

## 3. Nginx service

Container:

```text
nginx
```

Purpose:

```text
Single entry point for users
Serves frontend
Forwards API calls to FastAPI
Can be configured for HTTPS
```

Port exposed:

```text
80:80
```

User opens:

```text
http://server-ip/
```

Nginx decides:

```text
/api/* → FastAPI API
all other routes → Vue frontend
```

Production recommendation:

```text
Enable HTTPS on Nginx.
Use internal CA certificate if the system is only for intranet.
Increase upload size limit for video evidence.
```

---

## 4. Frontend service

Container:

```text
frontend
```

Purpose:

```text
Builds Vue app
Serves static files through internal Nginx
```

It is not directly exposed to the user. Main Nginx proxies traffic to it.

Build context:

```text
./frontend
```

Production note:

```text
The frontend container is rebuilt when frontend source code changes.
```

---

## 5. API service

Container:

```text
api
```

Purpose:

```text
FastAPI backend
Authentication
Inspection APIs
Media APIs
Review APIs
KPI APIs
Dashboard APIs
Report APIs
```

Command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
```

API is internally exposed on:

```text
8000
```

External users access it through:

```text
http://server-ip/api/v1/...
http://server-ip/api/docs
```

Depends on:

```text
postgres
redis
minio
```

---

## 6. PostgreSQL service

Container:

```text
postgres
```

Image:

```text
postgres:16-alpine
```

Purpose:

```text
Stores all structured data
users, roles, contracts, stations
inspection records
review workflow
KPI scores
penalty calculations
audit logs
```

Volume:

```text
postgres_data:/var/lib/postgresql/data
```

This volume must be backed up regularly.

Health check:

```bash
pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}
```

---

## 7. MinIO service

Container:

```text
minio
```

Purpose:

```text
Stores photos/videos as objects
S3-compatible on-prem storage
```

Ports:

```text
9000 API
9001 Console
```

Console URL:

```text
http://server-ip:9001
```

Bucket:

```text
mch-inspections
```

Important: photos/videos should not be stored directly in PostgreSQL. PostgreSQL stores only metadata and MinIO stores actual files.

Production recommendations:

```text
Use strong MinIO credentials.
Do not expose MinIO console publicly.
Back up MinIO data volume.
Consider MinIO distributed mode if storage grows.
```

---

## 8. Redis service

Container:

```text
redis
```

Purpose:

```text
Queue broker for Celery
Cache if needed later
Temporary background job state
```

Redis is used by:

```text
api
worker
scheduler
```

Current configured DBs:

```text
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

---

## 9. Worker service

Container:

```text
worker
```

Purpose:

```text
Run background jobs outside API request cycle
```

Command:

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

Use worker for:

```text
photo compression
video duration validation
PDF generation
Excel generation
notification processing
long-running KPI recalculation
```

Why separate worker?

```text
API should respond quickly.
Heavy media/report tasks should run in background.
```

---

## 10. Scheduler service

Container:

```text
scheduler
```

Purpose:

```text
Run scheduled jobs using Celery Beat
```

Command:

```bash
celery -A app.workers.celery_app.celery_app beat --loglevel=INFO
```

Use scheduler for:

```text
daily cleanup checks
monthly KPI calculation reminders
scheduled report generation
backup status checks
notification retries
```

Current project includes scheduler wiring. Add periodic tasks when required.

---

## 11. Starting the full system

From project root:

```bash
cp .env.example .env
docker compose up -d --build
```

Then run migrations and seed:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seeds.seed
```

Open:

```text
Frontend: http://localhost
API docs: http://localhost/api/docs
MinIO console: http://localhost:9001
```

---

## 12. Stopping the system

```bash
docker compose down
```

This stops containers but keeps data volumes.

To remove everything including database/media data:

```bash
docker compose down -v
```

Use `down -v` carefully because it deletes volumes.

---

## 13. Viewing logs

All logs:

```bash
docker compose logs -f
```

API logs:

```bash
docker compose logs -f api
```

PostgreSQL logs:

```bash
docker compose logs -f postgres
```

Nginx logs:

```bash
docker compose logs -f nginx
```

Worker logs:

```bash
docker compose logs -f worker
```

---

## 14. Rebuilding after code changes

Backend changed:

```bash
docker compose up -d --build api worker scheduler
```

Frontend changed:

```bash
docker compose up -d --build frontend nginx
```

Everything changed:

```bash
docker compose up -d --build
```

---

## 15. Docker volumes

Defined volumes:

```text
postgres_data
redis_data
minio_data
```

Meaning:

```text
postgres_data: database files
redis_data: redis persistence
minio_data: uploaded photos/videos
```

Backup priority:

```text
1. postgres_data
2. minio_data
3. .env and source code
```

---

## 16. Production port recommendations

For intranet deployment:

```text
80  HTTP, redirect to HTTPS
443 HTTPS
```

Do not expose these externally unless required:

```text
5432 PostgreSQL
6379 Redis
9000 MinIO API
9001 MinIO Console
8000 FastAPI direct port
```

Only Nginx should be exposed to users.

---

## 17. Common Docker problems

### PostgreSQL unhealthy

Check `.env`:

```text
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
DATABASE_URL
```

Check logs:

```bash
docker compose logs postgres
```

### API cannot connect to database

Inside Docker, host is service name:

```text
postgres
```

Correct format:

```text
postgresql+psycopg2://mch_user:mch_password@postgres:5432/mch_inspection
```

Do not use `localhost` inside containers for PostgreSQL.

### Frontend opens but API fails

Check Nginx config:

```text
/api/ route should proxy to api:8000
```

Check:

```bash
docker compose logs nginx
```

### Media upload fails

Check MinIO:

```bash
docker compose logs minio
```

Check bucket credentials in `.env`.

---

## 18. Recommended on-prem production topology

Minimum deployment:

```text
One Linux VM/Server
Docker Engine
Docker Compose
Mounted disk for volumes
Nightly backup to separate disk/NAS
```

Better deployment:

```text
App server: nginx/api/frontend/worker/scheduler
Database server: PostgreSQL
Storage server: MinIO/NAS
```

For first version, one good server is acceptable if backups are strict.

---

## 19. Cloud migration readiness

Even though the app is on-prem now, this design is migration-friendly:

```text
PostgreSQL → managed PostgreSQL later
MinIO S3 API → cloud object storage later
Docker Compose → container service later
Nginx → load balancer/reverse proxy later
```

Avoid hardcoding local paths. Keep all connection values in `.env`.
