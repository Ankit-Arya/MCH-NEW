Drop-in patch: Access Control interactive hierarchy tree

Replace:
frontend/src/views/AccessControlView.vue

Then rebuild:
docker compose up -d --build frontend

Notes:
- Adds expandable top-down reporting hierarchy tree.
- Adds Map children and Scope actions from tree rows.
- Adds list of users not mapped or mapped incorrectly.
- Adds Download hierarchy PDF button using browser print/save-as-PDF.
- No backend migration required.
