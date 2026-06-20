Hotfix for Access Control blank page.

Drop-in file:
frontend/src/views/AccessControlView.vue

Then rebuild frontend:
docker compose up -d --build frontend

This replaces the previous risky hierarchy patch with a safer non-recursive tree rendering.
