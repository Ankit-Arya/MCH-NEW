# Soft Chart Colors Patch

## Purpose

This patch softens dashboard and KPI chart colors. Earlier charts used high-contrast red/blue gradients, which looked too aggressive on mobile and desktop.

The new chart palette uses calmer pastel tones:

- soft blue
- soft teal
- soft violet
- soft amber
- soft pink
- soft green

## Files replaced

```text
frontend/src/components/SimpleBarChart.vue
frontend/src/components/SimpleLineChart.vue
frontend/src/components/DonutChart.vue
```

## What changed

### SimpleBarChart

- Removed harsh red/blue gradient.
- Added a muted rotating palette per bar.
- Added softer track/background.
- Improved mobile spacing.
- Kept the existing `items` and `suffix` props, so existing views should not need changes.

### SimpleLineChart

- Removed red/blue line gradient.
- Added soft blue/teal/violet line gradient.
- Added subtle area fill under the line.
- Replaced dark markers with white markers and soft blue outline.
- Kept existing `items` prop.

### DonutChart

- Removed strong blue stroke.
- Added soft blue/teal/violet gradient stroke.
- Added lighter track color and softer drop shadow.
- Kept existing `value` and `label` props.

## Apply patch

Copy the patch into your project root, then restart frontend:

```bash
docker compose restart frontend
```

If you are running production-built frontend image:

```bash
docker compose up -d --build frontend nginx
```

## Design note

Charts should support decision-making, not dominate the screen. This palette keeps charts readable while making the UI calmer for long-duration inspection/review work.
