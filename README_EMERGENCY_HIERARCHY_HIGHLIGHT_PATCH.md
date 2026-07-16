# Emergency inspection hierarchy highlight patch

Run from project root:

```bat
xcopy /E /Y mch_emergency_hierarchy_highlight_patch\backend backend\
python backend\scripts\20260713_apply_emergency_hierarchy_highlight_patch.py
docker compose up -d --build api frontend
```

Adds:
- Emergency badge/reason in Review Queue desktop and mobile cards.
- Emergency reason in review tracker modal.
- Emergency warning in review action modal so LM/AM, DGM and GM/Ops see it before forwarding/final decision.
- Emergency fields in backend review/report payloads.
- Emergency banner in the individual inspection PDF.
- Emergency label in filtered PDF register status column.
- No DB migration required.
