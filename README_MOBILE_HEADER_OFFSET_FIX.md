# Mobile Header Offset Fix

This patch fixes the mobile fixed header covering the first one or two lines of page content.

## Apply

From project root:

```bat
xcopy /E /Y mch_mobile_header_offset_fix_patch\backend backend\
python backend\scripts\20260710_apply_mobile_header_offset_fix.py
docker compose up -d --build frontend
```

## What changes

- Keeps mobile menu/header fixed at the top.
- Moves page content below the real mobile header height.
- Uses the same shared CSS variable for both header and page content offset.
- Adds safe-area support for mobile browser bars/notches.
- Keeps full-screen drawer scrollable when opened.

No DB migration required.
