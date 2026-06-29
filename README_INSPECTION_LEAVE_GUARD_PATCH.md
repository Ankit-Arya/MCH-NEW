# MCH Inspection Leave Guard Patch

## Purpose

This patch prevents accidental loss of in-progress inspection work.

When a user is on an editable inspection capture page (`DRAFT` or `RETURNED_FOR_CLARIFICATION`) and tries to leave the page, the app asks for confirmation first.

It covers:

- Browser Back button
- Browser refresh
- Browser tab/window close
- Sidebar/menu navigation to another page
- Any internal Vue route change away from the inspection form

## Files to replace

Copy/replace this file into the same path in your project:

```text
frontend/src/views/InspectionFormView.vue
```

## Rebuild

```bat
docker compose up -d --build frontend
```

If you are running the full stack rebuild:

```bat
docker compose up -d --build api frontend
```

## Behaviour

- The warning is active only while inspection status is editable:
  - `DRAFT`
  - `RETURNED_FOR_CLARIFICATION`

- Once inspection is submitted and status changes to review stage, the warning stops automatically.

- The message clarifies that unsaved selected area, remarks, GPS capture and photo/video selection may be lost. Already saved entries remain saved in DB.

## No backend change

No database migration required.
No backend change required.
