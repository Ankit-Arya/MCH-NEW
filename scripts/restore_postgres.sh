#!/usr/bin/env bash
set -euo pipefail
source .env
LATEST=$(ls -t ./backups/postgres/*.sql.gz | head -n 1)
if [ -z "${LATEST:-}" ]; then
  echo "No backup file found in ./backups/postgres"
  exit 1
fi

echo "Restoring ${LATEST}"
gunzip -c "$LATEST" | docker compose exec -T postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB"
