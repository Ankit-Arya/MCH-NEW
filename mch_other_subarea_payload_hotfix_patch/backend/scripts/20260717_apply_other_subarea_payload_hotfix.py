from pathlib import Path
import shutil


def find_project_root():
    start = Path.cwd().resolve()
    candidates = [start] + list(start.parents)
    for root in candidates:
        if (root / "frontend" / "src" / "views" / "InspectionFormView.vue").exists():
            return root
        if (root / "backend").exists() and (root / "frontend").exists():
            return root
    raise RuntimeError("Could not find project root. Run this script from mch-inspection-platform project root.")


def read_text(path):
    return path.read_text(encoding="utf-8")


def write_text(path, content):
    # Python 3.8 compatible; preserve LF line endings used by the repo.
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(content)


def backup(path):
    backup_path = path.with_suffix(path.suffix + ".bak_other_subarea_payload")
    if not backup_path.exists():
        shutil.copy2(str(path), str(backup_path))


def patch_inspection_form(root):
    path = root / "frontend" / "src" / "views" / "InspectionFormView.vue"
    content = read_text(path)

    old = '''    const payload = {
      attribute_id: form.attribute_id,
      sub_area_id: form.sub_area_id,
      grade_code: form.grade_code,
      remarks: form.remarks,
      captured_latitude: metadata.latitude,
      captured_longitude: metadata.longitude,
      gps_accuracy: metadata.gps_accuracy,
      captured_at: metadata.captured_at || nowIso(),
    };'''

    new = '''    const payload = {
      attribute_id: Number(form.attribute_id),
      sub_area_id: isOther ? null : Number(form.sub_area_id),
      custom_sub_area_name: isOther ? String(form.custom_sub_area_name || '').trim() : null,
      grade_code: form.grade_code,
      remarks: form.remarks,
      captured_latitude: metadata.latitude,
      captured_longitude: metadata.longitude,
      gps_accuracy: metadata.gps_accuracy,
      captured_at: metadata.captured_at || nowIso(),
    };'''

    if new in content:
        print("InspectionFormView.vue already has Other sub-area payload fix. Skipping.")
        return

    if old not in content:
        raise RuntimeError(
            "Could not find expected saveEntry payload block in frontend/src/views/InspectionFormView.vue. "
            "Please confirm the earlier Other sub-area hotfix was applied, then share this file if it still fails."
        )

    backup(path)
    content = content.replace(old, new, 1)
    write_text(path, content)
    print("Patched frontend/src/views/InspectionFormView.vue")


def main():
    root = find_project_root()
    patch_inspection_form(root)
    print("Done. Rebuild frontend: docker compose up -d --build frontend")


if __name__ == "__main__":
    main()
