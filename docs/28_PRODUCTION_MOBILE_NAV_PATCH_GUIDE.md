# Production Mobile Navigation Patch

## What this patch fixes

This patch replaces the earlier mobile side-drawer behavior with a production-style header dropdown panel.

Earlier problems:

- Mobile menu opened as a separate drawer instead of feeling connected to the DMRC/MCH header.
- The drawer covered the banner/header in an awkward way.
- Background page continued scrolling while the menu remained open.
- Menu layering and visual blending felt inconsistent.

New behavior:

- Header remains visible at the top.
- Burger button remains on the left side of the blue header.
- Logout remains on the right side of the blue header.
- Menu opens directly below the same blue header like an extension of the header.
- Menu has a backdrop below the header, not over the header.
- Page background scroll is locked while menu is open.
- Menu itself can scroll if nav items exceed screen height.
- Tapping outside, tapping a link, resizing to desktop, pressing Escape, or logging out closes the menu.

## Files replaced

```text
frontend/src/components/AppLayout.vue
```

## Apply

Copy this patch into your project root and restart frontend:

```bash
docker compose restart frontend
```

If running production-built frontend image:

```bash
docker compose up -d --build frontend nginx
```

## Why this is better

For mobile production apps, navigation should either be:

1. A full drawer with proper scroll-lock and clean layering, or
2. A header-attached dropdown panel.

For this project, the header-attached dropdown is better because:

- It uses less horizontal movement.
- It feels connected to the DMRC/MCH header.
- It keeps the logout visible.
- It avoids the awkward drawer covering the banner.
- It works well for field staff using phones.

## Important implementation notes

The Vue component now locks page scroll when the menu is open:

```js
document.body.style.overflow = 'hidden'
document.body.style.touchAction = 'none'
document.documentElement.style.overscrollBehavior = 'none'
```

It restores the original values when the menu closes.

The mobile menu panel uses:

```css
position: fixed;
top: var(--mobile-panel-top);
left: var(--mobile-header-x);
right: var(--mobile-header-x);
max-height: calc(100dvh - var(--mobile-panel-top) - 12px);
overflow-y: auto;
```

This allows menu content to scroll internally while the page remains fixed.
