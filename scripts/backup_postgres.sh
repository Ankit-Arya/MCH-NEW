#!/usr/bin/env bash
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
mkdir -p ./backups/postgres
source .env

docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "./backups/postgres/mch_${TS}.sql.gz"
echo "Backup created: ./backups/postgres/mch_${TS}.sql.gz"
