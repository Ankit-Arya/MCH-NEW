# MCH Action Required Workflow Patch

## Purpose

This patch separates unfinished field work from normal completed reports.

It adds an **Action Required** section for the logged-in submitter. It includes:

- inspections saved as `DRAFT`, where the SM/EIT may have saved partial work;
- inspections with status `RETURNED_FOR_CLARIFICATION`, where the Line Manager returned the inspection and the submitter must correct and resubmit.

## Drop-in replacement files

Replace these files in your project:

```text
backend/app/api/v1/endpoints/inspections.py
frontend/src/router/index.js
frontend/src/components/AppLayout.vue
frontend/src/views/InspectionFormView.vue
```

Add this new file:

```text
frontend/src/views/ActionRequiredView.vue
```

## Commands

```bash
docker compose up -d --build api frontend
```

## What changed

### Backend

Added:

```text
GET /api/v1/inspections/action-required
```

It returns only the current user's own inspections where status is:

```text
DRAFT
RETURNED_FOR_CLARIFICATION
```

Each row includes reason, entry/media counts, latest reviewer, latest action time, and latest remarks for returned inspections.

### Frontend

Added:

```text
/inspections/action-required
```

This page shows drafts and returned inspections in a separate list, with direct buttons:

- Continue Draft
- Correct & Resubmit

### Notifications

AppLayout now checks action-required count on login/layout load and shows:

- sidebar badge on **Action Required**
- topbar chip
- modal notification for draft/returned inspections

### Returned inspection editing

InspectionFormView now visibly confirms returned inspections are open for correction and resubmission. Backend already allowed edits for `DRAFT` and `RETURNED_FOR_CLARIFICATION`; this patch makes the workflow visible and reachable.

## DB migration

No DB migration required.
