# Mobile Burger Icon Visible Fix

## Problem

On mobile, the burger button was present and clickable, but it looked blank.

## Root cause

A mobile CSS rule was hiding every `span` inside `.brand-card`:

```css
.brand-card span {
  display: none;
}
```

The hamburger icon is made from three `span` lines inside the burger button, so that rule also hid the icon lines.

## Fix

The patch changes the mobile rule to hide only the brand subtitle:

```css
.brand-copy > span {
  display: none;
}
```

It also adds a stronger override so hamburger lines always remain visible:

```css
.brand-card .mobile-menu-btn span {
  display: block !important;
  background: #ffffff !important;
}
```

## File replaced

```text
frontend/src/components/AppLayout.vue
```

## Apply

Copy the patch contents into your project root, then restart frontend:

```bash
docker compose restart frontend
```

If using production-built frontend image:

```bash
docker compose up -d --build frontend nginx
```
