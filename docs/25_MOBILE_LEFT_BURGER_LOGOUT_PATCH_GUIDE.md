# Mobile Left Burger + Header Logout Patch Guide

## Problem fixed

The previous mobile navigation patch placed the burger button on the right side of the mobile brand header. The logout button also looked visually tied to the user information banner instead of being clearly positioned as the action on the right side of the top header/banner.

## What this patch changes

On desktop/laptop:

- The left sidebar remains visible as before.
- No burger button is shown.
- User information remains in the topbar.
- Logout remains at the far right of the topbar.

On mobile/tablet:

- The burger button is placed on the **left** side of the DMRC/MCH header.
- The menu opens as a **left-side drawer**.
- Tapping outside the drawer closes the menu.
- Tapping any menu link closes the menu.
- The user banner/topbar clearly shows user name/role on the left and **Logout** on the right.

## Files replaced

Copy this file into your project:

```text
frontend/src/components/AppLayout.vue
```

## Apply steps

From your project root:

```bash
docker compose restart frontend
```

If your frontend is running from a production-built image, rebuild frontend and nginx:

```bash
docker compose up -d --build frontend nginx
```

## Expected mobile layout

Closed state:

```text
[ ☰ ] [ DMRC logo | MCH KPI-6 ]
--------------------------------
[ User name / role          Logout ]
--------------------------------
Page content
```

Opened state:

```text
Left drawer:
Dashboard
Start Inspection
Reports & PDFs
Review Queue
KPI & Penalty
Master Data
```

## Quick test widths

Test using browser dev tools:

```text
390px mobile
430px large mobile
768px tablet portrait
1024px laptop/tablet boundary
```

Confirm that:

- Burger button is on the left.
- Drawer opens from the left.
- Logout stays on the right side of the user banner/topbar.
- Page content does not shift horizontally.
- No menu list covers half the page when closed.
