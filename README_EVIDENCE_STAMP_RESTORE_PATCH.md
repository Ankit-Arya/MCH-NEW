# Evidence Date-Time + GPS Stamp Restore Patch

This patch restores backend evidence stamping for new inspection media uploads.

## Replace files

- `backend/app/api/v1/endpoints/inspections.py`
- `backend/app/services/media_service.py`

## Rebuild

```bat
docker compose up -d --build api
```

## What it fixes

- Every new PHOTO upload is stamped before being stored in MinIO.
- Every new VIDEO upload is stamped before being stored in MinIO when ffmpeg can process the uploaded codec/container.
- Stamp includes:
  - `MCH INSPECTION EVIDENCE`
  - captured date-time
  - GPS latitude/longitude and accuracy if captured
  - visible warning line if GPS was not available/permission was denied
- DB checksum/file size now reflects the stamped stored file, not the raw uploaded bytes.
- No DB migration required.

## Note

This applies to newly uploaded evidence only. Already stored photos/videos are not modified automatically.
