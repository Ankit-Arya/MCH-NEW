# Saved Entry Evidence Preview Patch

## Replace these files

- `backend/app/api/v1/router.py`
- `backend/app/schemas/inspection.py`
- `backend/app/services/inspection_service.py`
- `frontend/src/components/SavedEntriesList.vue`

## Add this file

- `backend/app/api/v1/endpoints/evidence_preview.py`

## Rebuild

```bat
docker compose up -d --build api frontend
```

## What this patch does

- Saved entries now include a `media_files` list in the API response.
- Each saved entry shows a `Preview evidence` button after photo/video upload.
- Preview supports saved photos and saved videos.
- Frontend fetches evidence as authenticated blobs using axios, so protected media still works with bearer-token authentication.
- The backend serves evidence through `GET /api/v1/inspections/media/{media_id}/preview`.
- The preview endpoint checks the logged-in user's inspection visibility before returning the file.
- Stored evidence remains in MinIO.
- No database migration is required.
