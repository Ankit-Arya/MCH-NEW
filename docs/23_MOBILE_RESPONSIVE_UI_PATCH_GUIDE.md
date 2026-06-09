# Mobile Responsive UI Patch Guide

This patch fixes the frontend horizontal scrolling and mobile layout issues without changing backend APIs.

## What this patch changes

### Global CSS
`frontend/src/assets/styles.css`

Adds safer responsive defaults:

- Prevents page-level horizontal overflow.
- Makes cards, grids, charts and form controls shrink correctly inside mobile width.
- Converts major grids to single-column layouts on mobile.
- Adds a `mobile-cards` table pattern so tables become vertical cards on small screens.
- Makes toolbar buttons full-width on small screens.

### App shell
`frontend/src/components/AppLayout.vue`

Fixes mobile layout:

- Sidebar no longer forces horizontal scroll.
- Navigation becomes compact and mobile-friendly.
- Content area uses `min-width: 0` and `overflow-x: hidden`.
- Topbar stacks cleanly on very small screens.

### Login page
`frontend/src/views/LoginView.vue`

Rebuilds the tweaked login screen into a mobile-first responsive layout:

- Laptop: two-column professional card.
- Tablet/mobile: stacked layout.
- No fixed 60% container width.
- No fixed card width causing overflow.
- No dependency on `MCH-bg.png`, so the build will not break if that image is missing.

If you want to use your own background image later, add it in CSS after confirming the asset exists.

### Charts

Updated:

- `SimpleBarChart.vue`
- `SimpleLineChart.vue`
- `DonutChart.vue`

Fixes:

- Charts stay within card width.
- Bar chart becomes label/value above bar on very small screens.
- Donut chart wraps without forcing page width.
- Line chart uses responsive height.

### Dashboard and report pages

Updated:

- `DashboardView.vue`
- `KpiDashboardView.vue`
- `ReportsView.vue`
- `ReviewQueueView.vue`

Fixes:

- Removes inline grid span issue from dashboard.
- Adds mobile-card tables for KPI, reports and review queue.
- Ensures buttons stack vertically on mobile.

## How to apply

From the extracted patch folder, copy the `frontend` folder into your project root.

Example:

```bash
cp -r frontend/src/assets/styles.css /path/to/mch-inspection-platform/frontend/src/assets/styles.css
cp -r frontend/src/components/AppLayout.vue /path/to/mch-inspection-platform/frontend/src/components/AppLayout.vue
cp -r frontend/src/components/SimpleBarChart.vue /path/to/mch-inspection-platform/frontend/src/components/SimpleBarChart.vue
cp -r frontend/src/components/SimpleLineChart.vue /path/to/mch-inspection-platform/frontend/src/components/SimpleLineChart.vue
cp -r frontend/src/components/DonutChart.vue /path/to/mch-inspection-platform/frontend/src/components/DonutChart.vue
cp -r frontend/src/views/LoginView.vue /path/to/mch-inspection-platform/frontend/src/views/LoginView.vue
cp -r frontend/src/views/DashboardView.vue /path/to/mch-inspection-platform/frontend/src/views/DashboardView.vue
cp -r frontend/src/views/KpiDashboardView.vue /path/to/mch-inspection-platform/frontend/src/views/KpiDashboardView.vue
cp -r frontend/src/views/ReportsView.vue /path/to/mch-inspection-platform/frontend/src/views/ReportsView.vue
cp -r frontend/src/views/ReviewQueueView.vue /path/to/mch-inspection-platform/frontend/src/views/ReviewQueueView.vue
```

Or copy the whole patch content into your project root.

## Restart during development

If you are using the dev Docker override with volume mounts and Vite:

```bash
docker compose restart frontend
```

If frontend is running with Vite HMR, many CSS/Vue changes refresh automatically.

If you are running production-built frontend image, rebuild is still required:

```bash
docker compose up -d --build frontend nginx
```

## Important note about tables

Large data tables cannot always fit 320px width. This patch uses mobile card tables where possible. For any new table you add, use this pattern:

```html
<div class="table-wrap mobile-cards">
  <table class="table">
    <thead>
      <tr><th>Name</th><th>Status</th></tr>
    </thead>
    <tbody>
      <tr>
        <td data-label="Name">Rajiv Chowk</td>
        <td data-label="Status"><span class="badge green">Active</span></td>
      </tr>
    </tbody>
  </table>
</div>
```

On desktop it remains a table. On mobile each row becomes a vertical card.

## What this patch does not change

- Backend APIs
- Database schema
- Docker files
- Master data permissions
- Inspection entry workflow logic

It only improves frontend responsiveness and mobile usability.
