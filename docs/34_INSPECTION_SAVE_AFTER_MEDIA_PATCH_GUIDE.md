# Inspection Save Button After Evidence Patch

## Purpose

This patch fixes the inspection entry flow so users do not see an active **Save Entry** action before capturing/selecting mandatory photo evidence.

## Files replaced

```text
frontend/src/components/EntryCaptureForm.vue
frontend/src/views/InspectionFormView.vue
```

## Functional changes

- Entry form is now ordered as:
  1. Select attribute/sub-area and grade
  2. Capture/select photo/video evidence
  3. View metadata
  4. Save Entry
- Save Entry button is shown at the bottom of the evidence flow.
- Save Entry remains disabled until a mandatory photo is selected.
- Video remains optional.
- If media upload fails after the entry row is created, the frontend attempts to delete the entry so orphan entries without mandatory photo evidence are not left behind.
- Existing backend submit validation remains useful as a final server-side guard.

## Apply

Copy this patch folder over your project root, then restart frontend:

```bash
docker compose restart frontend
```

For production-built frontend:

```bash
docker compose up -d --build frontend nginx
```
