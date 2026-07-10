Emergency Inspection Patch

Copy this folder contents into your project root, then run:

python backend\scripts\20260710_apply_emergency_inspection_patch.py
docker compose up -d --build api frontend

No DB migration is required. Emergency metadata is stored inside inspections.device_info JSON.
