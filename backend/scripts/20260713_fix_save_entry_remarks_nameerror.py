from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / 'app' / 'services' / 'inspection_service.py'

if not SERVICE.exists():
    raise SystemExit(f'File not found: {SERVICE}')

text = SERVICE.read_text(encoding='utf-8')
original = text

replacements = [
    ('remarks=remarks,', 'remarks=payload.remarks,'),
]

changed = False
for old, new in replacements:
    if old in text:
        text = text.replace(old, new)
        changed = True

# Defensive cleanup for a broken helper variable sometimes introduced by earlier patch attempts.
# The save_entry() function should use the request payload's remarks directly.
if 'remarks = payload.remarks' not in text and 'payload.remarks' not in text:
    raise SystemExit('Could not confirm payload.remarks usage. Please inspect save_entry() manually.')

if not changed:
    if 'remarks=payload.remarks,' in text:
        print('No change needed: inspection_service.py already uses payload.remarks.')
    else:
        raise SystemExit('Expected pattern remarks=remarks, was not found. Please inspect backend/app/services/inspection_service.py around save_entry().')
else:
    SERVICE.write_text(text, encoding='utf-8')
    print('Fixed NameError in backend/app/services/inspection_service.py: remarks now uses payload.remarks.')
