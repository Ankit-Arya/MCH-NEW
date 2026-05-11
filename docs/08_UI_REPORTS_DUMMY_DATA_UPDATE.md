# UI, Dashboard, Reports and Dummy Data Update

This update addresses the production-demo feedback:

1. The frontend now uses a professional DMRC-themed visual design with a darker operations sidebar, refined cards, better spacing, responsive grids, and a header logo placeholder.
2. Dashboard now supports weekly, monthly and yearly analytics filters.
3. Dashboard includes KPI trend, station-wise score, inspection volume, grade distribution and penalty amount cards.
4. Reports module now supports inspection search by date range, contract, station, inspector, inspection type and status.
5. PDF download is available for:
   - Single inspection report
   - Filtered/ranged inspection register
6. Seed script now generates demonstration data for multiple stations, users, contracts, inspection statuses, KPI scores and penalties.

## Important Logo Note

The file below contains a DMRC-style placeholder SVG for layout demonstration:

```text
frontend/src/assets/dmrc-logo.svg
```

For official production use, replace it with the approved official DMRC logo file after confirming internal branding permission.

## New Frontend Files

```text
frontend/src/views/ReportsView.vue
frontend/src/components/SimpleBarChart.vue
frontend/src/components/SimpleLineChart.vue
frontend/src/components/DonutChart.vue
frontend/src/assets/dmrc-logo.svg
```

## Updated Frontend Files

```text
frontend/src/assets/styles.css
frontend/src/components/AppLayout.vue
frontend/src/components/StatCard.vue
frontend/src/views/DashboardView.vue
frontend/src/views/KpiDashboardView.vue
frontend/src/views/LoginView.vue
frontend/src/router/index.js
frontend/src/services/api.js
```

## New / Updated Backend APIs

### Dashboard Analytics

```http
GET /api/v1/dashboard/analytics?period=monthly&from_date=2026-01-01&to_date=2026-05-31
```

Optional filters:

```text
period=weekly|monthly|yearly
from_date=YYYY-MM-DD
to_date=YYYY-MM-DD
contract_id=<id>
station_id=<id>
```

Returns:

```text
summary
score_trend
inspection_volume
station_scores
grade_distribution
status_distribution
contract_scores
role_view
```

### Inspection Search

```http
GET /api/v1/inspections?from_date=2026-01-01&to_date=2026-05-31&station_id=1&contract_id=1
```

### Report Search

```http
GET /api/v1/reports/inspections/search
```

Optional filters:

```text
from_date
to_date
station_id
contract_id
submitted_by
inspection_type
status
```

### Single Inspection PDF

```http
GET /api/v1/reports/inspection/{inspection_id}/pdf
```

### Date-Ranged / Filtered Register PDF

```http
GET /api/v1/reports/inspections/pdf?from_date=2026-01-01&to_date=2026-05-31
```

## Demo Data

Run:

```bash
docker compose exec api python -m app.seeds.seed
```

The seed script now creates:

```text
Demo users for Admin, SM, EIT, Line Manager, DGM and GM/Ops
Multiple lines and stations
Two demo MCH contracts
Two demo contractors
Billing cycles from January to May 2026
SM and EIT inspections across months
Attribute scores and grades
Mock media metadata
Monthly station scores
Monthly contract scores
Penalty calculations for below-threshold months
```

## Demo Login Users

```text
admin / admin123
sm01 / sm123
sm02 / sm123
sm03 / sm123
eit01 / eit123
eit02 / eit123
lm01 / lm123
dgm01 / dgm123
gm01 / gm123
```

## How to Demonstrate Dashboards

1. Login as `admin/admin123` or `gm01/gm123`.
2. Open Dashboard.
3. Select period: Weekly, Monthly or Yearly.
4. Use date range `2026-01-01` to `2026-05-31`.
5. Apply contract or station filters.
6. Charts will update from seeded inspection records.

## How to Demonstrate PDF Reports

1. Open Reports & PDFs.
2. Select date range `2026-01-01` to `2026-05-31`.
3. Select station, contract or inspector if needed.
4. Click Search.
5. Click PDF against one inspection for a detailed inspection report.
6. Click Download Date Range PDF for a consolidated inspection register.

## Production Notes

Before production:

1. Replace placeholder logo with official approved logo.
2. Replace demo seed credentials and remove default demo users.
3. Use strong `SECRET_KEY` and database passwords.
4. Enable HTTPS in Nginx.
5. Keep MinIO bucket private.
6. Confirm the final grading scale with department before UAT.
7. Confirm whether SM after-10-AM inspections should be blocked or only marked late.
8. Configure backup jobs for PostgreSQL and MinIO.
9. Add organization SSO or LDAP integration if required.
10. Test PDF formats against official record-keeping requirements.
