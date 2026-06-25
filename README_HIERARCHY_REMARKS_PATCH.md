# Hierarchy review remarks patch

Drop-in replacement files:

- `frontend/src/views/ReviewQueueView.vue`
- `backend/app/api/v1/endpoints/reports.py`

## What it changes

- Review Queue no longer performs immediate hard-coded approval on button click.
- Clicking Review opens a modal with:
  - action selector based on current hierarchy status,
  - remarks field,
  - submit/cancel controls.
- Submitted remarks are sent to existing review APIs as `comments`.
- PDF inspection report now includes an **Approval / Forwarding Remarks** table showing:
  - level,
  - action,
  - reviewer name,
  - reviewer role,
  - reviewed date/time,
  - remarks.
- Keeps the previous app-proxy evidence links for full-resolution photos/videos.
- No DB migration required because remarks already exist in `inspection_reviews.comments` and workflow history remarks.

## Apply

Copy the files into the same paths in your project, then rebuild:

```bash
docker compose up -d --build api frontend
```
