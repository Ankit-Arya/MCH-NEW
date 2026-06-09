# Production Solid Mobile Navigation Fix

## What this patch fixes

This patch replaces the previous mobile navigation behavior with a single fixed mobile navigation shell.

Earlier issue:

- Header was one layout piece.
- Menu panel was another fixed/sticky piece.
- On scroll, the page moved behind it and the menu looked detached from the banner.
- The menu could visually cover or separate from the header depending on scroll position and mobile browser chrome behavior.

New behavior:

- On mobile, the blue DMRC/MCH header is fixed at the top.
- The menu opens inside the same blue shell below the header, so it looks like an extension of the banner.
- The page behind the menu is locked in place while the menu is open.
- A backdrop is shown behind the menu.
- Menu scroll is internal if the menu becomes tall.
- Desktop sidebar behavior remains unchanged.

## Files replaced

```text
frontend/src/components/AppLayout.vue
```

## Apply

Copy this patch into the project root, then run:

```bash
docker compose restart frontend
```

If your frontend is running from a production-built image:

```bash
docker compose up -d --build frontend nginx
```

## Important browser note

Mobile Chrome changes the viewport height when the address bar collapses or expands. This patch avoids that problem by using one fixed navigation shell and locking the body scroll when the menu opens.
