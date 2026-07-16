# LM Transfer Reassignment Patch

## Purpose

Adds a practical transfer workflow for Line Managers.

When an LM is transferred under another DGM:

- only the LM is moved to the new DGM
- SM/EIT users under the previous LM are reassigned to a replacement LM under the old DGM
- this avoids dragging the whole station team along with the transferred LM

## Files patched by script

- backend/app/api/v1/endpoints/access_control.py
- frontend/src/views/AccessControlView.vue

## How to apply in CMD

From project root:

```bat
tar -xf mch_lm_transfer_reassignment_patch.zip
copy /Y mch_lm_transfer_reassignment_patch\backend\scripts\20260716_apply_lm_transfer_reassignment_patch.py backend\scripts\
python backend\scripts\20260716_apply_lm_transfer_reassignment_patch.py
docker compose up -d --build api frontend
```

## New backend endpoint

```text
POST /api/v1/access-control/transfer-line-manager
```

Payload:

```json
{
  "transferred_lm_user_id": 10,
  "new_dgm_user_id": 4,
  "replacement_lm_user_id": 11,
  "relation_type": "REPORTING"
}
```

## Safety rules

- Only Admin/HK Cell can use the endpoint.
- Transferred user must be AM_MGR_LINE or AM_MGR_HK.
- New supervisor must be DGM_LINE or DGM_HK.
- Replacement user must be AM_MGR_LINE or AM_MGR_HK.
- Replacement LM must already be under the old DGM.
- The transferred LM cannot be the replacement LM.
- Existing SM/EIT child links under the transferred LM are disabled and re-created under the replacement LM.
- Audit log is written with old DGM, new DGM, replacement LM and moved SM/EIT users.

## DB migration

No DB migration is required.
