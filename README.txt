Access Control PDF download hotfix

Replace:
frontend/src/views/AccessControlView.vue

Then rebuild:
docker compose up -d --build frontend

Fix:
- Replaces browser print-window based hierarchy PDF export with a lightweight client-side PDF Blob download.
- No popup window, no window.print(), no automatic print dialog.
- Keeps interactive hierarchy tree and mapping issue lists.
