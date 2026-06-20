# MCH Multi-Photo Inspection Patch v3

This v3 patch is based on v2 and adds a fix for the log pattern where:

- entry creation succeeds
- first `/media` upload succeeds
- second `/media` upload returns `400 Bad Request`
- frontend deletes the entry to avoid incomplete evidence

## Why v2 may still fail

The API default/photo env limit is 8 MB. A mobile camera photo can easily be above 8 MB, especially the second/third captured photo. Nginx buffering warnings are normal for large multipart uploads and are not the failure.

## What v3 adds

- Frontend keeps multiple photos instead of overwriting one photo.
- Frontend resizes/compresses large selected camera photos before upload.
- Frontend shows which item failed, e.g. `Photo 2: PHOTO file too large...`.
- Backend file-size error now shows actual uploaded size and configured limit.
- Backend still uses unique object names so repeated mobile filenames do not overwrite MinIO files.
- Backend submit validation still checks each entry against `photo_min_required`.

## Drop-in steps

1. Extract this ZIP into the repository root.
2. Let it overwrite the included files.
3. Rebuild/restart:

```bash
docker compose build api frontend
docker compose up -d
```

If you are running the bind-mounted dev setup, also do:

```bash
docker compose restart api frontend nginx
```

4. Hard refresh browser:

```text
Ctrl + F5
```

## Optional

If you still see file-size errors after v3 compression, add/update this in your real `.env`:

```env
MAX_PHOTO_MB=15
```

Then restart:

```bash
docker compose restart api
```
