# Login Weekly / Review Notification Patch

This is a drop-in file-code patch.

## Replace files

```text
backend/app/api/v1/endpoints/inspections.py
frontend/src/components/AppLayout.vue
```

## Rebuild

```bat
docker compose up -d --build api frontend
```

## What changed

- Adds `GET /api/v1/inspections/login-notification-summary`.
- For Station Manager logins, the notification shows whether 3 inspections have been completed in the current Monday-Sunday week.
- For EIT logins, the notification shows whether 1 inspection has been completed in the current Monday-Sunday week.
- The same notification still shows draft and returned-for-clarification inspections from Action Required.
- For reviewer roles, the login popup continues to show pending Review Queue count, now with clearer text: how many inspections need update.
- The popup still appears once per login session and can be dismissed for that login.

## Weekly count rule

Weekly completed count includes inspections submitted by the logged-in user in the current Monday-Sunday week whose status is no longer draft/returned, including under-review, approved, rejected, sent to GM, reviewed, or closed.

No DB migration is required.
