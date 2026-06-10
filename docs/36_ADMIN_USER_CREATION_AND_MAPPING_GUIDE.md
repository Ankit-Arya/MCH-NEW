# Admin User Creation and Mapping Patch

This patch makes user creation an admin-controlled activity. There is no public sign-up. Admin/HK Cell creates login credentials, resets passwords, activates/deactivates users, and maps access.

## Files replaced

```text
backend/app/api/v1/endpoints/users.py
frontend/src/views/AccessControlView.vue
```

## Apply

Copy the patch folders into the project root, then restart:

```bash
docker compose restart api frontend
```

For production-built frontend:

```bash
docker compose up -d --build api frontend nginx
```

No new migration is required because the users table already exists.

## Where to create users

Login as admin/HK Cell and open:

```text
/access-control
```

The top section is now **Create user credentials**.

Create actual users like:

- SM: role `STATION_MANAGER`
- EIT: role `EIT_MEMBER`
- LM: role `AM_MGR_LINE` or `AM_MGR_HK`
- DGM: role `DGM_LINE` or `DGM_HK`
- GM/Ops: role `GM_OPS`

Set username and temporary password. Share the temporary password with the user. Passwords are not displayed later.

## How to map after creating users

### SM/EIT to station

1. Go to **User scope**.
2. Select the SM/EIT user.
3. Tick stations.
4. Click **Save station/line access**.

### LM to SM/EIT

1. Go to **Reporting hierarchy**.
2. Select LM as supervisor.
3. Tick SM/EIT users under that LM.
4. Click **Save reporting hierarchy**.

### DGM to LM

1. Select DGM as supervisor.
2. Tick LM users under that DGM.
3. Click **Save reporting hierarchy**.

## Where to see mappings

- Station mapping: select the user again in **User scope**; mapped stations appear checked.
- Reporting mapping: see **Current hierarchy** table at the bottom.

## Password reset

In **Existing users**, click **Reset password** and enter a new temporary password.

## Activate/deactivate

In **Existing users**, click **Deactivate** or **Activate**. Inactive users cannot log in and will not appear in mapping dropdowns.

## Backend API

Admin-only endpoints:

```text
GET    /api/v1/users?include_inactive=true
POST   /api/v1/users
PUT    /api/v1/users/{user_id}
PUT    /api/v1/users/{user_id}/password
PUT    /api/v1/users/{user_id}/status
```

Example create user request:

```json
{
  "emp_number": "12345",
  "name": "Rajesh Kumar",
  "username": "sm.rajesh",
  "password": "Temp@123",
  "role_code": "STATION_MANAGER",
  "mobile": "9999999999",
  "email": "rajesh@example.com",
  "is_active": true
}
```
