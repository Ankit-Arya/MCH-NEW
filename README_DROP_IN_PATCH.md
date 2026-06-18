# MCH Admin SQL Tool - Drop-in Patch

This package is tailored for `Ankit-Arya/MCH-NEW`.

## What this adds

- Backend admin-only SQL API: `/api/v1/admin-sql/*`
- Frontend page: `/admin/sql`
- Read-only query execution with:
  - only `SELECT`, `WITH`, `SHOW`, safe `EXPLAIN`
  - blocked write/admin keywords
  - transaction read-only mode
  - PostgreSQL statement timeout
  - row limit
  - existing `audit_logs` entry for success/failure

## Drop-in steps

1. Extract this ZIP into the repository root.
2. Let it overwrite these existing files:
   - `backend/app/api/v1/router.py`
   - `frontend/src/router/index.js`
3. Add the env lines from `_patch_notes/02_ENV_ADDITIONS.txt` to your real `.env`.
4. Run `_patch_notes/01_CREATE_READONLY_USER.sql` in PostgreSQL.
5. Restart/rebuild:

```bash
docker compose build api frontend
docker compose up -d
```

6. Open:

```text
/admin/sql
```

## Optional sidebar menu

The route works without changing the sidebar. To show it in the sidebar, apply the one-line change in:

```text
_patch_notes/03_OPTIONAL_SIDEBAR_LINK.txt
```

## Important

Do not point `READONLY_DATABASE_URL` to the main application DB user. Create and use the `mch_readonly` PostgreSQL user.
