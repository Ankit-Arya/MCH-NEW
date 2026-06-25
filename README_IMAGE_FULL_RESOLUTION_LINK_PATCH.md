# Image Full-Resolution Link Patch

## Replace this file

Copy this file from the patch into the same path in your project:

```text
backend/app/api/v1/endpoints/reports.py
```

## Rebuild

```bash
docker compose up -d --build api
```

## What changed

- Existing PDF photo thumbnails remain unchanged.
- Each thumbnail now also has a clickable **Open full-resolution image** link.
- The image link uses the same signed MinIO URL mechanism already used for video evidence links.
- No frontend change.
- No DB migration.

## Note

The full-resolution link opens the actual stored image object, including the timestamp/GPS overlay for newly uploaded evidence if the previous evidence timestamp overlay patch is applied.
