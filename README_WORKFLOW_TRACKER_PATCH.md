# Workflow Tracker Patch

## Files to replace

- `backend/app/api/v1/endpoints/reviews.py`
- `frontend/src/views/ReportsView.vue`
- `frontend/src/views/ReviewQueueView.vue`

## What this adds

- Adds backend workflow tracker data for each visible inspection.
- Adds a reusable `/reviews/workflow-trackers` endpoint used by Reports and Review Queue.
- Shows approval stages in Reports and Review Queue:
  - Inspection done
  - Submitted to Line Manager
  - Line Manager decision
  - DGM decision
  - GM/Ops review
- Shows reviewer name, date/time, and action where available.
- Keeps existing report PDF generation unchanged.

## Rebuild

```bash
docker compose up -d --build api frontend
```

## Notes

The tracker uses existing `inspection_reviews.reviewed_at`, `review_level`, `reviewer_id`, and inspection submission fields. No database migration is required.
