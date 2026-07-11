# Mobile sticky header flow fix

This patch fixes the mobile header overlay issue by making the closed mobile header part of the normal document flow with `position: sticky`.

## Apply

From project root:

```bat
xcopy /E /Y mch_mobile_sticky_header_fix_patch\backend backend\
python backend\scripts\20260710_apply_mobile_sticky_header_fix.py
docker compose up -d --build frontend
```

## What it changes

- Closed mobile header is sticky, not a fixed overlay.
- Page content starts below the header automatically.
- Open hamburger drawer is still fixed/full-screen.
- Open drawer menu remains scrollable.
- Safe-area space for phone notches/browser UI is preserved.
- No database migration required.
