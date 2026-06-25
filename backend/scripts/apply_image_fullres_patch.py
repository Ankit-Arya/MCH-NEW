from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "reports.py"

OLD = '''    for media in photo_media:\n        try:\n            thumbnail = _build_thumbnail_flowable(download_bytes(media.object_path))\n            label = media.sub_area.name if media.sub_area else media.original_file_name\n            safe_label = escape(label or "Photo")\n\n            cells.append([\n                thumbnail,\n                Spacer(1, 4),\n                Paragraph(safe_label, styles["BodyText"]),\n            ])\n        except Exception:\n            unavailable_count += 1\n'''

NEW = '''    for media in photo_media:\n        try:\n            thumbnail = _build_thumbnail_flowable(download_bytes(media.object_path))\n            image_url = get_external_object_url(media.object_path)\n            label = media.sub_area.name if media.sub_area else media.original_file_name\n            safe_label = escape(label or "Photo")\n            safe_href = escape(image_url, {'"': "&quot;"})\n\n            cells.append([\n                thumbnail,\n                Spacer(1, 4),\n                Paragraph(f"<b>{safe_label}</b>", styles["BodyText"]),\n                Spacer(1, 2),\n                Paragraph(f'<link href="{safe_href}">Open full-resolution image</link>', styles["BodyText"]),\n            ])\n        except Exception:\n            unavailable_count += 1\n'''

MARKER = 'Open full-resolution image'


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: Target file not found: {TARGET}")
        print("Run this script from the extracted patch folder placed at your project root.")
        return 1

    text = TARGET.read_text(encoding="utf-8")
    if MARKER in text:
        print("Already patched: photo full-resolution links are present in reports.py")
        return 0

    if OLD not in text:
        print("ERROR: Expected photo preview block was not found in reports.py")
        print("This usually means reports.py has been edited manually or is from a different version.")
        print("Search for def _build_photo_preview_table and apply the change manually from README.")
        return 1

    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"Patched successfully: {TARGET}")
    print("Now rebuild API: docker compose up -d --build api")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
