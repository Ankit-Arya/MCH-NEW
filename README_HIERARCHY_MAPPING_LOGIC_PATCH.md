# MCH Hierarchy Mapping Logic Patch

## Purpose

This patch fixes operational hierarchy and station mapping logic.

The enforced model is now:

```text
Station(s) -> one SM
SM/EIT -> one LM
LM -> one DGM
DGM -> one GM/Ops
```

A higher officer can still have multiple children:

```text
One SM can have many stations.
One LM can have many SM/EIT users.
One DGM can have many LMs.
One GM/Ops can have many DGMs.
```

## Replace

```text
backend/app/api/v1/endpoints/access_control.py
```

## Add and run

```text
backend/scripts/20260707_hierarchy_mapping_logic_fix.sql
```

## Run DB patch

CMD:

```bat
type backend\scripts\20260707_hierarchy_mapping_logic_fix.sql | docker compose exec -T postgres psql -U mch_user -d mch_inspection
```

PowerShell:

```powershell
Get-Content .\backend\scripts\20260707_hierarchy_mapping_logic_fix.sql | docker compose exec -T postgres psql -U mch_user -d mch_inspection
```

Then rebuild API:

```bat
docker compose up -d --build api
```

## Backend enforcement added

1. Same station cannot be actively allotted to multiple Station Managers.
2. One Station Manager can have multiple stations.
3. SM/EIT users are station-wise users; line access is blocked for SM/EIT to avoid broad accidental scope.
4. A subordinate can have only one active supervisor.
5. When an SM/LM/DGM is remapped to a new supervisor, old active parent links are automatically deactivated.
6. Invalid role chain is blocked:
   - GM/Ops can supervise DGM only.
   - DGM can supervise LM only.
   - LM can supervise SM/EIT only.
   - Super Admin/HK Cell can manage mappings but is not part of the operational reporting chain.
7. SQL cleanup deactivates existing duplicate/invalid active mappings before adding database guards.

## No frontend rebuild required unless you want to refresh frontend assets

The existing Access Control UI will show backend validation messages in the error card.
