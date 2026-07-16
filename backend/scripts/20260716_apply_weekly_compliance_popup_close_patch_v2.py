from __future__ import print_function

import re
from pathlib import Path

PATCH_MARKER = "Close both notices before navigation so no modal remains over the destination page."


def find_project_root():
    """Find project root from cwd or this script path. Python 3.8 compatible."""
    candidates = []
    try:
        candidates.append(Path.cwd())
    except Exception:
        pass
    candidates.append(Path(__file__).resolve())

    seen = set()
    for start in candidates:
        for folder in [start] + list(start.parents):
            if folder in seen:
                continue
            seen.add(folder)
            app_layout = folder / "frontend" / "src" / "components" / "AppLayout.vue"
            if app_layout.exists():
                return folder

    raise RuntimeError(
        "Could not find project root. Run this script from the project root folder that contains frontend\\src\\components\\AppLayout.vue."
    )


def read_text(path):
    return path.read_text(encoding="utf-8")


def write_text(path, content):
    # Python 3.8 compatible: pathlib.Path.write_text() has no newline= argument.
    path.write_text(content, encoding="utf-8")


def patch_app_layout():
    root = find_project_root()
    path = root / "frontend" / "src" / "components" / "AppLayout.vue"
    content = read_text(path)

    if PATCH_MARKER in content:
        print("Already patched:", path)
        return

    new_function = """async function goToWeeklyCompliance() {
  // This action can be invoked from either the action-required popup or the pending-review popup.
  // Close both notices before navigation so no modal remains over the destination page.
  dismissActionRequiredNotice()
  dismissPendingReviewNotice()
  closeMobileMenu()
  await router.push('/inspections/weekly-compliance')
}"""

    exact_old = "async function goToWeeklyCompliance() { dismissActionRequiredNotice(); closeMobileMenu(); await router.push('/inspections/weekly-compliance') }"
    if exact_old in content:
        content = content.replace(exact_old, new_function, 1)
        write_text(path, content)
        print("Patched:", path)
        return

    pattern = r"async\s+function\s+goToWeeklyCompliance\s*\(\s*\)\s*\{.*?router\.push\('/inspections/weekly-compliance'\).*?\}"
    content_new, count = re.subn(pattern, new_function, content, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(
            "Could not find goToWeeklyCompliance() in frontend/src/components/AppLayout.vue. "
            "Please confirm the file still contains the Weekly Compliance popup navigation function."
        )

    write_text(path, content_new)
    print("Patched:", path)


def main():
    patch_app_layout()
    print("Done. Rebuild frontend: docker compose up -d --build frontend")


if __name__ == "__main__":
    main()
