# Emergency hierarchy highlight V2 patch

This corrected patch fixes the earlier failure:

`RuntimeError: Could not find expected block for review emergency styles`

It is idempotent for backend changes, so it can run safely even if the previous script already applied part of the backend patch.

Run from project root in CMD:

```bat
tar -xf mch_emergency_hierarchy_highlight_v2_patch.zip
copy /Y mch_emergency_hierarchy_highlight_v2_patch\backend\scripts\20260713_apply_emergency_hierarchy_highlight_v2.py backend\scripts\
python backend\scripts\20260713_apply_emergency_hierarchy_highlight_v2.py
docker compose up -d --build api frontend
```

No DB migration required.
