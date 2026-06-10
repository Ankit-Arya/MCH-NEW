# Patch 33: Review Queue Inspection PDF Viewer and Report PDF Preview

## Purpose

This patch adds an in-app PDF preview workflow so users do not need to download every inspection PDF just to review it.

It also improves the Review Queue page by showing inspection-related information similar to the Reports page and by adding `View PDF` and `Download PDF` actions for each pending inspection.

## Files included

```text
backend/app/api/v1/endpoints/reviews.py
frontend/src/components/PdfPreviewModal.vue
frontend/src/services/api.js
frontend/src/views/ReportsView.vue
frontend/src/views/ReviewQueueView.vue
```

## What changes

### Reports page

- Keeps paginated inspection register.
- Adds `View PDF` beside each inspection.
- Keeps `Download PDF` beside each inspection.
- Adds `View Filtered PDF` for the date/filter register.
- Keeps `Download Filtered PDF` for record keeping.

### Review Queue page

- Shows richer inspection details:
  - inspection number
  - date
  - station
  - contract
  - inspector
  - type
  - status
  - score
  - entry count / media count
- Adds `View PDF` for quick analysis before review.
- Adds `Download PDF` for record keeping.
- Keeps review action buttons.
- Keeps pagination.

### PDF viewer

The new reusable component is:

```text
frontend/src/components/PdfPreviewModal.vue
```

It opens a modal with an iframe-based PDF preview. It uses an authenticated API request to fetch the PDF as a blob, creates a temporary browser object URL, and renders the PDF inside the modal.

This approach is important because a normal iframe link cannot pass the JWT Authorization header reliably.

## Apply patch

Copy the patch contents into your project root.

Then restart:

```bash
docker compose restart api frontend
```

If using production-built frontend image:

```bash
docker compose up -d --build api frontend nginx
```

## Test checklist

1. Open Reports page.
2. Click `View PDF` for an inspection.
3. Confirm PDF opens inside modal.
4. Click `Download` inside modal.
5. Close modal.
6. Click row-level `Download`.
7. Open Review Queue.
8. Confirm each pending inspection shows station/contract/inspector/score/entries/media.
9. Click `View PDF` from Review Queue.
10. Review the PDF and then perform the review action.

## Notes

- The backend reports endpoint still generates the same PDF.
- The frontend now offers both preview and download.
- Blob URLs are revoked when the modal closes to avoid memory leaks.
