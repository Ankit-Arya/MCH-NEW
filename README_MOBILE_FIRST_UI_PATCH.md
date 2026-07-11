# MCH Mobile-first UI Patch

Run from the project root:

```bat
python backend\scripts\20260710_apply_mobile_first_ui_patch.py
docker compose up -d --build frontend api
```

What it changes:

- Makes the hamburger menu a full-screen mobile drawer.
- Keeps the drawer header fixed and makes the navigation list itself scrollable.
- Removes the 700px drawer height cap that was cutting off menu options.
- Adds safe-area support for mobile browser address bars and notches.
- Adds global mobile-first hardening for cards, forms, buttons, modals, tables and overflow.
- Converts Weekly Compliance table into mobile cards using `data-label` fields.
- Hardens Help Forum and Start Inspection layouts on mobile.
- No database migration required.
