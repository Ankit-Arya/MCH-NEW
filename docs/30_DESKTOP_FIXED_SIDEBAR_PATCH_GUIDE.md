# Desktop Fixed Sidebar Patch

## What this patch fixes

On desktop, the previous sidebar used `position: sticky` inside the page layout. On long pages this could create an awkward blank area below/around the menu and make the sidebar feel as if it is moving with the page.

This patch makes the desktop sidebar a true fixed application shell:

```text
Sidebar: fixed left, full viewport height
Content: starts after sidebar using margin-left
Sidebar scroll: internal only if menu content is taller than viewport
Page scroll: only the main content area scrolls visually
Mobile: existing fixed header + hamburger menu behavior remains unchanged
```

## Files replaced

```text
frontend/src/components/AppLayout.vue
```

## Apply

Copy this patch into the project root, then restart frontend:

```bash
docker compose restart frontend
```

For production-built frontend image:

```bash
docker compose up -d --build frontend nginx
```

## Key CSS change

Desktop sidebar now uses:

```css
.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  height: 100dvh;
  overflow-y: auto;
}

.content {
  margin-left: 292px;
}
```

Mobile override resets content margin:

```css
@media (max-width: 820px) {
  .content {
    margin-left: 0;
  }
}
```
