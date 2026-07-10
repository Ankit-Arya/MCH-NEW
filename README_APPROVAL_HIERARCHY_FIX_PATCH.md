# MCH Approval Hierarchy Fix Patch

Correct approval flow:

```text
SM/EIT inspection -> LM/AM -> DGM -> GM/Ops final approve/reject
```

Rules enforced:

```text
LM/AM: forward to DGM OR return for clarification only.
DGM: forward to GM/Ops OR return for clarification only.
GM/Ops: final approve OR final reject only.
```

## Files replaced

```text
backend/app/services/review_service.py
backend/app/api/v1/endpoints/reviews.py
frontend/src/views/ReviewQueueView.vue
frontend/src/views/ReportsView.vue
```

## Additional script

```text
backend/scripts/20260710_apply_pdf_status_label_fix.py
```

Run this once after copying files. It updates backend PDF/report labels inside `backend/app/api/v1/endpoints/reports.py` without replacing the full large report file.

## Commands

From project root:

```bat
xcopy /E /Y mch_approval_hierarchy_fix_patch\backend backend\
xcopy /E /Y mch_approval_hierarchy_fix_patch\frontend frontend\
python backend\scripts\20260710_apply_pdf_status_label_fix.py
docker compose up -d --build api frontend
```

No DB migration is required.

Note: The existing terminal DB enum values `DGM_APPROVED` and `DGM_REJECTED` are kept for compatibility, but after this patch they are produced only by GM/Ops final action and displayed as final GM/Ops approval/rejection.
