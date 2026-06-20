# Access Control validation + readable error fix

Drop this replacement file into the repo:

```text
frontend/src/views/AccessControlView.vue
```

What it fixes:

1. Adds visible minimum requirement hints on the Access Control user form.
2. Adds inline validation for:
   - Full name: required, minimum 2 characters
   - Username: required, minimum 3 characters
   - Temporary password: required for new users, minimum 6 characters
   - Role: required
3. Converts FastAPI/Pydantic validation JSON errors into readable messages, for example:
   - `Password: String should have at least 6 characters`
   instead of showing raw JSON.
4. Applies the same readable error formatter to create user, edit user, reset password, status, station/line access and hierarchy save actions.

No backend change is required because the existing backend already defines the minimum rules in `backend/app/api/v1/endpoints/users.py`.

After replacing the file, rebuild/restart frontend:

```bash
docker compose up -d --build frontend
```

For dev override/hot reload:

```bash
docker compose up -d frontend
```
