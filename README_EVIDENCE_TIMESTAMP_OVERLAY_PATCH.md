# MCH Evidence Timestamp Overlay Patch

## Purpose

This patch makes the evidence file itself carry the captured date/time.

Earlier, MCH was saving `captured_at`, GPS latitude/longitude and accuracy in the database, but the photo/video file in the report could still be inspected without that visible information. This patch stamps the captured timestamp directly on:

- uploaded photos,
- uploaded videos.

The PDF report will then show photo previews with the timestamp already visible on the image, and video links will open videos with the timestamp visible on the video frame.

## Files changed

Replace these files:

```text
backend/app/services/media_service.py
backend/app/api/v1/endpoints/inspections.py
backend/requirements.txt
```

## Rebuild

```bash
docker compose up -d --build api
```

No database migration is required.

## What changed

### Photos

When PHOTO evidence is uploaded, the backend uses Pillow to stamp a dark bottom-left badge on the image:

```text
Captured: DD-MM-YYYY HH:MM:SS IST
GPS: latitude, longitude | Acc: Xm
```

GPS line appears only when GPS coordinates are available.

### Videos

When VIDEO evidence is uploaded, the backend uses ffmpeg to permanently add the same timestamp/GPS badge onto the video. The backend Dockerfile already installs ffmpeg, so only the Python requirement for Pillow is added.

If ffmpeg cannot process a specific video codec/container, upload still succeeds with the original video. This prevents inspectors from getting blocked in the field.

### DB values

The structured DB values are still saved in `inspection_media`:

- `captured_at`
- `captured_latitude`
- `captured_longitude`
- `gps_accuracy`
- `checksum`
- `file_size`

After stamping, `checksum` and `file_size` reflect the stored stamped file, not the original raw upload.

## Notes

- This affects newly uploaded evidence after this patch is deployed.
- Existing media already stored in MinIO is not modified automatically.
- `processing_status` is now saved as `STAMPED` for media handled by this flow.
