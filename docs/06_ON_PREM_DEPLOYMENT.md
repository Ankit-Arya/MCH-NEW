# On-Prem Deployment Guide

## Server Recommendation

Minimum for pilot:

- 8 CPU cores
- 32 GB RAM
- 500 GB SSD storage
- Linux server with Docker and Docker Compose

Production recommendation depends on photo/video volume.

## Deployment Steps

1. Install Docker Engine and Docker Compose plugin.
2. Copy project folder to `/opt/mch-inspection-platform`.
3. Create `.env` from `.env.example`.
4. Update passwords and `SECRET_KEY`.
5. Configure server firewall.
6. Run:

```bash
docker compose up -d --build
```

7. Run migration:

```bash
docker compose exec api alembic upgrade head
```

8. Seed initial admin:

```bash
docker compose exec api python -m app.seeds.seed
```

## SSL

For production, configure HTTPS in Nginx with department-approved certificate.

## Backups

Database backup:

```bash
make backup
```

Media backup:

Backup Docker volume `minio_data` or configure MinIO mirror to NAS.

## Migration to Cloud Later

The selected design keeps migration easy:

| Current On-Prem | Cloud Equivalent Later |
|---|---|
| PostgreSQL Docker | Managed PostgreSQL |
| MinIO | S3-compatible object storage |
| Redis Docker | Managed Redis |
| Nginx | Load balancer / ingress |
| Docker Compose | VM-based Docker / container platform |
