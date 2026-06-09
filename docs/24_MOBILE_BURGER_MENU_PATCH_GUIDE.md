# Mobile Burger Menu Patch Guide

## Problem fixed

On mobile screens the sidebar navigation was being rendered as a visible list at the top of the page. This consumed too much vertical space and made the app feel cluttered before the user even reached the actual screen content.

## What this patch changes

This patch replaces the mobile navigation list with a compact burger menu.

On desktop/laptop:

- The existing left sidebar remains visible.
- Navigation links remain available as before.

On mobile/tablet:

- Only a compact DMRC/MCH header is shown at the top.
- A burger button is shown on the right side of the header.
- Navigation links stay hidden until the user taps the burger button.
- The menu opens as a mobile drawer overlay.
- Selecting any navigation link automatically closes the drawer.
- Tapping outside the drawer also closes it.

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

If you are not using the dev override / Vite hot reload setup and your frontend is production-built inside Docker, rebuild the frontend image:

```bash
docker compose up -d --build frontend nginx
```

## Why only AppLayout.vue changed

The issue was caused by the layout component rendering all navigation links on mobile. The chart/card/mobile page fixes from the previous responsive patch can remain unchanged. This patch only changes the shell/navigation behavior.

## Expected mobile behavior

Mobile closed state:

```text
[ DMRC logo | MCH KPI-6 | ☰ ]
--------------------------------
[ page content starts here ]
```

Mobile opened state:

```text
[ DMRC logo | MCH KPI-6 | X ]
--------------------------------
Dashboard
Start Inspection
Reports & PDFs
Review Queue
KPI & Penalty
Master Data
```

## Quick test checklist

Test at browser widths around:

```text
390px  - common mobile width
430px  - larger mobile width
768px  - tablet portrait
1024px - tablet/laptop boundary
```

Confirm:

- Menu is hidden by default on mobile.
- Burger button opens the menu.
- Menu closes after clicking any page link.
- Menu closes when tapping the backdrop.
- Desktop sidebar remains visible at laptop size.
- Page content no longer starts halfway down the screen because of navigation links.
