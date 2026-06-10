# Strict Hierarchy Scope Fix

This patch fixes LM/DGM visibility.

## Correct logic

Example:

```text
aaaaaa = Station Manager
bbbbbb = Line Manager
cccccc = DGM

bbbbbb -> aaaaaa
cccccc -> bbbbbb
```

After this patch:

- `aaaaaa` can start inspections only for mapped stations.
- `bbbbbb` sees inspections submitted by `aaaaaa` and any other SM/EIT mapped under `bbbbbb`.
- `cccccc` sees inspections submitted by all SM/EIT users under LMs mapped below `cccccc`.
- LM/DGM visibility no longer expands to every inspection from the same station.

## Why the old result was wrong

The earlier access function used this kind of logic:

```text
station is under subordinate scope OR submitter is under subordinate scope
```

That leaked extra inspections when multiple users had inspections at the same station.

The new logic is:

```text
If user has subordinates:
    filter by submitted_by in recursive subordinate users
Else if user has station mapping:
    filter by mapped station
Else:
    filter by own submitted inspections
```

## Files replaced

```text
backend/app/core/permissions.py
backend/app/services/review_service.py
backend/app/api/v1/endpoints/reports.py
backend/app/api/v1/endpoints/inspections.py
```

## Apply

```powershell
docker compose restart api frontend
```

## Test

1. Login as `aaaaaa`.
2. Start and submit one inspection.
3. Login as `bbbbbb`.
4. Reports/dashboard/review queue should show `aaaaaa` inspections only, plus any other SM/EIT users mapped below `bbbbbb`.
5. Login as `cccccc`.
6. Reports/dashboard/review queue should show inspections of SM/EIT users below LMs mapped below `cccccc` only.

## Quick database check

```powershell
docker compose exec db psql -U mch_user -d mch_db -c "select supervisor_user_id, subordinate_user_id, is_active from user_supervisor_access order by supervisor_user_id, subordinate_user_id;"
```

Replace DB user/name if your `.env` uses different values.
