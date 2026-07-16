# Delete Draft Inspection V2 Patch

This fixes the V1 path detection issue on Windows.

Run from project root in CMD:

```bat
tar -xf mch_delete_draft_inspection_v2_patch.zip
copy /Y mch_delete_draft_inspection_v2_patch\backend\scripts\20260713_apply_delete_draft_inspection_patch_v2.py backend\scripts\
python backend\scripts\20260713_apply_delete_draft_inspection_patch_v2.py
docker compose up -d --build api frontend
```

No DB migration required.
