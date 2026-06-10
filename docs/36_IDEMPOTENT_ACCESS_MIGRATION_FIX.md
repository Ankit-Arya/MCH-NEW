# Idempotent Access Hierarchy Migration Fix

## Why this patch is needed

A previous merge-conflict state created the `user_supervisor_access` table in PostgreSQL, but Alembic did not mark revision `0003_access_hierarchy` as applied. When `alembic upgrade head` ran again, PostgreSQL correctly returned:

```text
psycopg2.errors.DuplicateTable: relation "user_supervisor_access" already exists
```

## What this patch changes

It replaces:

```text
backend/alembic/versions/0003_access_hierarchy.py
```

with an idempotent migration. The migration now checks whether the table, unique constraint, and indexes already exist before creating them.

## Apply

Copy this patch into the project root, then run:

```powershell
docker compose exec api alembic upgrade head
docker compose exec api alembic current
docker compose restart api frontend
```

Expected current revision:

```text
0003_access_hierarchy (head)
```

## Do not drop the table

Do not drop `user_supervisor_access` unless this is a disposable development database, because it may already contain mapping data.
