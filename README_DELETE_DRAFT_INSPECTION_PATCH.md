# Delete Draft Inspection Patch

Adds a self-service **Delete Draft** button in Action Required for unsubmitted draft inspections.

## Apply

Run from project root in CMD:

```bat
tar -xf mch_delete_draft_inspection_patch.zip
copy /Y mch_delete_draft_inspection_patch\backend\scripts\20260713_apply_delete_draft_inspection_patch.py backend\scripts\
python backend\scripts\20260713_apply_delete_draft_inspection_patch.py
docker compose up -d --build api frontend
```

## Behavior

- Only `DRAFT` inspections can be deleted.
- Only the original submitter can delete the draft.
- Only SM/EIT field users can use the endpoint.
- Returned / submitted / forwarded inspections cannot be deleted.
- Removes child DB rows for entries, evidence references, workflow history and KPI context before deleting the draft inspection.
- Adds an audit log entry before deletion.

No DB migration required.
