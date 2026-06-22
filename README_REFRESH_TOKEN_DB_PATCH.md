# MCH Refresh Token DB Session Patch

This patch turns refresh tokens into real server-side sessions instead of a frontend-only stored token.

## Files included

Replace/add these files in your latest repo:

```text
backend/app/api/v1/endpoints/auth.py
backend/app/core/deps.py
backend/app/core/security.py
backend/app/models/__init__.py
backend/app/models/auth_session.py
backend/app/schemas/auth.py
backend/alembic/env.py
backend/scripts/20260622_create_user_refresh_sessions.sql
frontend/src/services/api.js
frontend/src/stores/auth.js
```

## Apply database table first

Run this once after copying the SQL file into the project. From the project root:

### Linux / macOS / Git Bash

```bash
docker compose exec -T postgres psql -U mch_user -d mch_inspection < backend/scripts/20260622_create_user_refresh_sessions.sql
```

### Windows PowerShell

```powershell
Get-Content backend/scripts/20260622_create_user_refresh_sessions.sql | docker compose exec -T postgres psql -U mch_user -d mch_inspection
```

Then rebuild:

```bash
docker compose up -d --build api frontend
```

## What changes

### 1. New table: `user_refresh_sessions`

Stores refresh token sessions with:

- user id
- refresh token `jti`
- SHA-256 hash of refresh token
- expiry
- revoked time
- replacement session id
- reuse detection time
- IP and user agent

Raw refresh tokens are never stored in the database.

### 2. Login now creates a server-side refresh session

Login returns:

- access token
- refresh token

And also inserts one active row in `user_refresh_sessions`.

### 3. Access token type is enforced

Protected routes now reject any JWT where:

```text
type != access
```

So a refresh token can no longer be sent as a Bearer token to access protected APIs.

### 4. Refresh token rotation is real

When `/auth/refresh` is called:

1. Backend verifies the refresh JWT.
2. Backend checks the matching row in `user_refresh_sessions`.
3. Old refresh session is revoked.
4. New access token is issued.
5. New refresh token is issued.
6. New refresh session row is inserted.
7. Old session points to the new session through `replaced_by_session_id`.

### 5. Refresh token reuse detection

If an already-rotated refresh token is used again, backend marks reuse detected and revokes all active refresh sessions for that user.

This protects against stolen refresh token replay.

### 6. Frontend auto-refresh

The Axios response interceptor now catches `401` responses, calls `/auth/refresh`, stores the new tokens, and retries the original request once.

If refresh fails, frontend clears tokens and sends user to `/login`.

### 7. Logout revokes refresh session

Frontend logout sends the refresh token to `/auth/logout`. Backend revokes the matching refresh session. The browser still clears both tokens immediately.

## Useful testing SQL

See active sessions:

```sql
SELECT id, user_id, refresh_token_jti, issued_at, expires_at, revoked_at, replaced_by_session_id, reuse_detected_at
FROM user_refresh_sessions
ORDER BY id DESC;
```

Expire all refresh sessions for a user manually:

```sql
UPDATE user_refresh_sessions
SET expires_at = NOW() - INTERVAL '1 minute'
WHERE user_id = (SELECT id FROM users WHERE username = 'lm01');
```

Revoke all sessions for a user manually:

```sql
UPDATE user_refresh_sessions
SET revoked_at = NOW()
WHERE user_id = (SELECT id FROM users WHERE username = 'lm01')
  AND revoked_at IS NULL;
```

## Important deployment note

Run the SQL table script before testing login on the rebuilt API. Login now creates a refresh-session row, so the table must exist.
