# Mobile Header Logout Alignment Patch

This patch fixes the mobile header/navigation layout after the burger menu update.

## Problem fixed

On mobile, the previous layout showed:

- blue DMRC/MCH header at the top,
- then a large separate white user/topbar card,
- and only the Logout button inside that white card.

This wasted screen height and made the logout button look detached from the navigation/header.

## New behaviour

### Mobile

- Burger menu remains on the left.
- DMRC/MCH title remains in the blue header.
- Logout button is now on the right side of the same blue header.
- The separate white topbar is hidden on mobile.
- Drawer opens from the left.
- Drawer shows a small logged-in user card at the top.

### Desktop

- Existing left sidebar remains.
- Existing topbar with user details and logout remains.

## File replaced

```text
frontend/src/components/AppLayout.vue
```

## Apply

Copy the patch contents into the project root, then restart frontend:

```bash
docker compose restart frontend
```

If using production-built frontend image:

```bash
docker compose up -d --build frontend nginx
```

## Result

Mobile screen now uses one compact blue header only:

```text
[☰] [DMRC logo + MCH KPI-6]                         [Logout]
```

The user/role information is available inside the drawer instead of taking a full white banner on every page.
