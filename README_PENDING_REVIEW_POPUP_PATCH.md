# Pending Review Login Popup Patch

## Replace

```text
frontend/src/components/AppLayout.vue
```

## Rebuild

```bash
docker compose up -d --build frontend
```

## What this patch does

- On authenticated layout load, checks `/reviews/pending?page=1&size=1` for reviewer roles only:
  - `AM_MGR_LINE`
  - `AM_MGR_HK`
  - `DGM_LINE`
  - `DGM_HK`
  - `GM_OPS`
- If pending reviews exist, shows a popup with the pending review count.
- Popup has:
  - `Open Review Queue`
  - `Remind me later`
  - close button
- Adds a small pending-review chip in the desktop topbar.
- Adds a count badge on the Review Queue navigation item.
- Uses `sessionStorage` so the popup does not keep appearing repeatedly in the same browser session after dismissal.

## Backend

No backend change is required. It uses the existing `/reviews/pending` endpoint, which already scopes pending reviews by logged-in reviewer role and hierarchy.
