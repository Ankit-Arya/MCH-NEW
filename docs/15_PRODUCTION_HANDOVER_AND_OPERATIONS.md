# Production Handover and Operations Guide

This document explains how to prepare, deploy, operate and hand over the system for on-prem production use.

---

## 1. Production deployment target

Recommended first deployment:

```text
Linux server or VM
Docker Engine
Docker Compose
Static IP or internal DNS name
Nginx as reverse proxy
PostgreSQL in Docker with persistent volume
MinIO in Docker with persistent volume
Daily backup to separate disk/NAS
```

Minimum recommended server profile for pilot:

```text
CPU: 4 cores
RAM: 16 GB
Disk: SSD, size based on photo/video volume
OS: Ubuntu Server LTS or equivalent
```

For large rollout with many stations and video uploads, increase storage and RAM.

---

## 2. Production folder layout

Recommended path:

```text
/opt/mch-inspection-platform/
├── backend/
├── frontend/
├── nginx/
├── docs/
├── scripts/
├── docker-compose.yml
├── .env
└── backups/
```

Keep backups outside the application folder also:

```text
/mnt/backup/mch/postgres/
/mnt/backup/mch/minio/
```

---

## 3. Production `.env` checklist

Before starting production, change:

```text
SECRET_KEY
POSTGRES_PASSWORD
MINIO_ACCESS_KEY
MINIO_SECRET_KEY
FRONTEND_ORIGIN
```

Recommended:

```text
Use strong random values.
Do not share .env in email.
Keep .env readable only by deployment/admin user.
```

Example permission:

```bash
chmod 600 .env
```

---

## 4. Starting production

From project root:

```bash
docker compose up -d --build
```

Run migrations:

```bash
docker compose exec api alembic upgrade head
```

Run seed only for first deployment:

```bash
docker compose exec api python -m app.seeds.seed
```

Check containers:

```bash
docker compose ps
```

Check health:

```text
http://server-ip/api/health
```

---

## 5. HTTPS setup

For production, use HTTPS because:

```text
login token security
GPS accuracy/browser permission
camera/mobile permissions
media upload security
```

Nginx should terminate HTTPS.

Recommended options:

```text
Internal CA certificate for intranet
Public certificate if publicly accessible
```

After HTTPS setup:

```text
FRONTEND_ORIGIN=https://your-domain
```

---

## 6. Backup strategy

### PostgreSQL backup

Daily backup:

```bash
docker compose exec postgres pg_dump -U mch_user mch_inspection > backups/postgres/mch_$(date +%F).sql
```

Compress:

```bash
gzip backups/postgres/mch_$(date +%F).sql
```

### MinIO backup

Options:

```text
filesystem backup of minio_data volume
or MinIO client mirror command
```

Recommended with MinIO client:

```bash
mc alias set local http://localhost:9000 mch_minio_admin mch_minio_password
mc mirror local/mch-inspections /mnt/backup/mch/minio/mch-inspections
```

### Config backup

Backup:

```text
.env
docker-compose.yml
nginx/default.conf
custom scripts
```

Do not store plain `.env` in insecure location.

---

## 7. Restore strategy

### Restore PostgreSQL

Stop app writes:

```bash
docker compose stop api worker scheduler
```

Restore:

```bash
cat backup.sql | docker compose exec -T postgres psql -U mch_user -d mch_inspection
```

Start services:

```bash
docker compose start api worker scheduler
```

### Restore MinIO

Restore MinIO data from backup to volume or use `mc mirror` back to bucket.

After restore, test:

```text
login
open inspection
view media
run dashboard
```

---

## 8. Monitoring checklist

Daily checks:

```text
All containers running
Disk usage below threshold
PostgreSQL backup successful
MinIO backup successful
API health OK
No repeated API errors
```

Commands:

```bash
docker compose ps
df -h
docker compose logs --tail=100 api
docker compose logs --tail=100 postgres
docker compose logs --tail=100 minio
```

Optional monitoring stack:

```text
Prometheus
Grafana
Loki
Node exporter
cAdvisor
```

---

## 9. Log review

Useful commands:

```bash
docker compose logs -f api
docker compose logs -f nginx
docker compose logs -f worker
docker compose logs -f postgres
docker compose logs -f minio
```

For investigation:

```text
Check audit_logs table.
Check inspection_workflow_history table.
Check nginx access logs.
Check API error logs.
```

---

## 10. User management process

Recommended admin workflow:

```text
1. Create user.
2. Assign role.
3. Assign station or line access.
4. User logs in and changes password.
5. Deactivate transferred/retired user.
```

Never delete users who performed inspections/reviews. Deactivate them instead.

---

## 11. Master data management process

Before inspection rollout, configure:

```text
lines
stations
contractors
contracts
contract_station mapping
grading scheme
actionable sub-areas
billing cycles
monthly bill values
users and access
```

Master data should be changed only by:

```text
SUPER_ADMIN
HK_CELL_ADMIN
```

---

## 12. Production UAT checklist

### Login and access

```text
Admin login works.
SM login works.
EIT login works.
Line Manager login works.
DGM login works.
GM login works.
Wrong password is rejected.
Inactive user is rejected.
User cannot access unassigned station.
```

### Inspection

```text
SM can start inspection for assigned station.
EIT can start inspection.
GPS is captured.
Photo upload works from mobile.
Video upload works from mobile.
N/A reason is saved.
Draft save works.
Submit blocks missing mandatory evidence.
Submit routes to Line Manager.
Late SM inspection is flagged.
```

### Review

```text
Line Manager can view assigned pending inspections.
Line Manager can return for clarification.
Line Manager can recommend penalty.
DGM can approve/reject/send to GM.
GM can review GM-marked case.
Workflow history is correct.
Audit logs are created.
```

### KPI

```text
Billing cycle is created.
Monthly bill value is entered.
KPI calculation runs.
Station score is correct.
Contract score is correct.
Penalty is generated only below threshold.
Penalty amount is correct.
```

### Reports and dashboard

```text
Dashboard counts are correct.
Pending review count is correct.
KPI dashboard shows results.
Report endpoint works.
Export format is acceptable.
```

---

## 13. Security checklist

```text
Change all default passwords.
Use HTTPS.
Restrict database port.
Restrict Redis port.
Restrict MinIO console.
Use strong SECRET_KEY.
Keep .env secure.
Ensure backend validates all permissions.
Do not expose direct media links publicly.
Log critical actions in audit_logs.
Deactivate users instead of deleting.
```

---

## 14. Performance checklist

```text
Limit max photo size.
Limit max video size.
Compress photos in worker.
Validate video duration in worker.
Paginate inspection list.
Add filters for dashboards.
Add DB indexes for heavy queries.
Archive old reports if allowed by retention policy.
```

Useful indexes to consider later:

```text
inspections(contract_id, station_id, inspection_date)
inspections(status)
inspection_media(inspection_id)
monthly_station_scores(billing_cycle_id, contract_id)
penalty_calculations(billing_cycle_id, contract_id)
audit_logs(created_at)
```

---

## 15. Release process

Recommended release steps:

```text
1. Take database backup.
2. Take code backup/current image tag.
3. Pull/copy new code.
4. Review .env changes.
5. Build containers.
6. Run migrations.
7. Restart services.
8. Run smoke tests.
9. Monitor logs for 30 minutes.
```

Commands:

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose ps
docker compose logs --tail=100 api
```

---

## 16. Smoke test after every deployment

```text
Open frontend.
Login as admin.
Open dashboard.
Open API docs.
Call /api/health.
Create or view inspection.
Check pending reviews.
Check KPI page.
Upload a small test photo in test environment.
```

---

## 17. Handover contents

Give the operations/development team:

```text
source code zip/repository
.env template
admin credentials through secure channel
deployment guide
backup guide
restore guide
database schema guide
API guide
frontend/backend tutorial docs
UAT checklist
known limitations
future enhancement list
```

---

## 18. Known limitations to validate before live rollout

```text
Final grading scale must be confirmed.
Whether SM inspection after 10 AM is blocked or only flagged must be confirmed.
Video mandatory/optional rules must be confirmed.
Offline inspection support may be required in poor network areas.
Full PDF format may require department-approved template.
User access mapping must match actual hierarchy.
```
