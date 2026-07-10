# MCH Help Forum Patch

Adds a Help Forum tab similar to a simple Discord/forum flow.

## Files added

- `backend/app/api/v1/endpoints/help.py`
- `backend/scripts/20260710_help_forum.sql`
- `backend/scripts/20260710_apply_help_forum_patch.py`
- `frontend/src/views/HelpForumView.vue`

## Files patched by script

- `backend/app/models/all_models.py`
- `backend/app/api/v1/router.py`
- `frontend/src/router/index.js`
- `frontend/src/components/AppLayout.vue`

## Install commands

From project root after extracting the zip:

```bat
xcopy /E /Y mch_help_forum_patch\backend backend\
xcopy /E /Y mch_help_forum_patch\frontend frontend\
python backend\scripts\20260710_apply_help_forum_patch.py
type backend\scripts\20260710_help_forum.sql | docker compose exec -T postgres psql -U mch_user -d mch_inspection
docker compose up -d --build api frontend
```

PowerShell SQL command:

```powershell
Get-Content .\backend\scripts\20260710_help_forum.sql | docker compose exec -T postgres psql -U mch_user -d mch_inspection
```

## Feature summary

- Adds `/help` page and Help Forum sidebar tab.
- Users can create questions with title/details.
- Users can upload image, video or PDF attachments with questions.
- Users can view all questions and search by question, answer or comment text.
- Users can add comments and comment attachments.
- Admin roles can post an official answer.
- Admin answer marks the topic as `ANSWERED`.
- Admin roles can close topics.
- All authenticated users can view forum questions, comments and media.

## Admin answer roles

- `SUPER_ADMIN`
- `HK_CELL_ADMIN`
- `GM_OPS`

## DB migration

Required. Run `20260710_help_forum.sql` once per actual database environment.
