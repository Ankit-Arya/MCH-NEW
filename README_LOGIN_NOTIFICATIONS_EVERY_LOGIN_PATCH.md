# MCH Login Notification Repeat Patch

This patch fixes notification popups that were showing only once on the same device/browser session.

## Replace files

Copy these files into the same paths in your project:

- `frontend/src/components/AppLayout.vue`
- `frontend/src/stores/auth.js`

## Rebuild

```bat
docker compose up -d --build frontend
```

## What changed

- Notification suppression is now tied to a fresh login-session id.
- On every successful login, a new login-session id is created.
- Pending Review and Action Required popups can appear once per login when counts are greater than zero.
- Dismissing a popup hides it only for the current login session, not permanently for that device.
- Page navigation during the same login will not repeatedly show the same dismissed popup.
- Logout clears the login-session id.

## Expected behaviour

- Login with pending reviews or action-required drafts/returned inspections: popup appears.
- Dismiss popup and navigate around: popup does not keep reappearing during same login.
- Logout and login again: popup appears again if action is still pending.
