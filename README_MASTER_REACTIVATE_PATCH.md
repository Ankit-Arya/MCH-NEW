# Master Data Reactivation Patch

Adds activation/restore support for master data records that were previously deactivated, and improves the Access Control user list filter.

## Apply

From project root:

```bat
xcopy /E /Y mch_master_reactivate_patch\backend backend\
python backend\scripts\20260713_apply_master_reactivate_patch.py
docker compose up -d --build api frontend
```

## What changes

- Adds backend activate endpoints for:
  - lines
  - stations
  - contractors
  - contracts
  - inspection attributes
  - inspection sub-areas
  - grading schemes
- Adds Activate button in Master Data table when a row is inactive.
- Adds status filter in Master Data: All / Active / Inactive.
- Adds user status filter in Access Control: All / Active / Inactive.
- Users already had activate/deactivate support; this makes inactive users easier to find.

## No DB migration

No table changes are required.
