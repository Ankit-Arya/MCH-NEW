# MCH Video 15-second Trim Patch

This patch enforces the inspection video duration rule on the backend.

## Replace files

- `backend/app/services/media_service.py`
- `backend/app/api/v1/endpoints/inspections.py`

## Rebuild

```bat
docker compose up -d --build api
```

## Behaviour

- Every uploaded inspection video is processed through ffmpeg before storage.
- The stored evidence video is converted to MP4 and clipped to the first 15 seconds.
- Date/time and GPS evidence stamp remains overlaid on the stored video.
- The original full-length video is not stored in MinIO.
- If ffmpeg cannot process the video, upload is rejected instead of saving an untrimmed file.
- No database migration is required.
