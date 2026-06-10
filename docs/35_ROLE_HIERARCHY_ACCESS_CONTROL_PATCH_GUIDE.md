# Role hierarchy and station access-control patch

This patch adds the missing operational-access layer:

- SM/EIT can inspect only mapped stations.
- LM sees and reviews only SM/EIT users mapped under that LM.
- DGM sees and reviews only LMs mapped under that DGM, including those LMs' SM/EIT users.
- Dashboard, Reports, Review Queue, KPI screens and PDF endpoints are backend-scoped.
- Admin/HK Cell can maintain station, line and reporting hierarchy mappings from `/access-control`.

## Files included

```text
backend/alembic/versions/0002_access_hierarchy.py
backend/app/models/access_control.py
backend/app/schemas/access_control.py
backend/app/core/permissions.py
backend/app/api/v1/router.py
backend/app/api/v1/endpoints/access_control.py
backend/app/api/v1/endpoints/master.py
backend/app/api/v1/endpoints/inspections.py
backend/app/api/v1/endpoints/reports.py
backend/app/api/v1/endpoints/reviews.py
backend/app/api/v1/endpoints/dashboard.py
backend/app/api/v1/endpoints/kpi.py
backend/app/services/review_service.py
frontend/src/router/index.js
frontend/src/views/AccessControlView.vue
```

## Apply

Copy the patch files into the project root, then run:

```bash
docker compose restart api frontend
docker compose exec api alembic upgrade head
```

For production-built frontend image:

```bash
docker compose up -d --build api frontend nginx
docker compose exec api alembic upgrade head
```

## Add menu link

If your latest `AppLayout.vue` already has the production mobile/desktop fixes, do not replace it just for this patch. Add this link manually inside the nav area:

```vue
<RouterLink to="/access-control">Access Control</RouterLink>
```

The route works even without the menu link by opening:

```text
/access-control
```

## Mapping workflow

1. Login as `SUPER_ADMIN` or `HK_CELL_ADMIN`.
2. Open `/access-control`.
3. Select each SM/EIT user and map station access.
4. Select each LM and map subordinate SM/EIT users.
5. Select each DGM and map subordinate LM users.
6. Verify with user-specific login:
   - SM station dropdown should show only assigned stations.
   - LM review queue should show only SM requests under that LM.
   - DGM review queue should show only LM-recommended inspections under that DGM.
   - Reports and dashboard should automatically scope to permitted data.

## Backend rule summary

- `SUPER_ADMIN`, `HK_CELL_ADMIN`, `GM_OPS`: all scope.
- Direct station access is stored in existing `user_station_access`.
- Direct line access is stored in existing `user_line_access`.
- Reporting hierarchy is stored in new `user_supervisor_access`.
- Scope is recursive, so DGM -> LM -> SM automatically works.

## Important

This patch is backend-enforced. Even if someone changes frontend filters manually, restricted users cannot access unmapped station/inspection/PDF data from API endpoints.
