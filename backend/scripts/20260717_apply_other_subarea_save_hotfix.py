from pathlib import Path


def find_project_root():
    current = Path.cwd().resolve()
    candidates = [current] + list(current.parents)
    for base in candidates:
        if (base / "frontend" / "src" / "views" / "InspectionFormView.vue").exists():
            return base
        if (base / "mch-inspection-platform" / "frontend" / "src" / "views" / "InspectionFormView.vue").exists():
            return base / "mch-inspection-platform"
    raise RuntimeError("Could not find project root containing frontend/src/views/InspectionFormView.vue")


def read_text(path):
    with path.open("r", encoding="utf-8") as handle:
        return handle.read()


def write_text(path, content):
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(content)


def patch_inspection_form_view(root):
    path = root / "frontend" / "src" / "views" / "InspectionFormView.vue"
    content = read_text(path)

    # Idempotent marker: if the helper already exists, skip the patch safely.
    if "function isOtherSubAreaPayload" in content and "const isOther = isOtherSubAreaPayload(form);" in content:
        print("InspectionFormView.vue already contains Other sub-area save hotfix; skipping.")
        return

    old_helper = """function getSubAreaById(id) {
  return subAreas.value.find((s) => Number(s.id) === Number(id)) || null;
}
"""
    new_helper = """function getSubAreaById(id) {
  return subAreas.value.find((s) => Number(s.id) === Number(id)) || null;
}

function isOtherSubAreaPayload(form) {
  return !form.sub_area_id && String(form.custom_sub_area_name || '').trim().length > 0;
}

function customSubAreaDraft(form) {
  const name = String(form.custom_sub_area_name || '').trim();
  return {
    id: null,
    name: name || 'Other sub-area',
    photo_min_required: 1,
    photo_max_allowed: 3,
    is_custom: true,
  };
}
"""
    if old_helper not in content:
        raise RuntimeError("Could not find getSubAreaById block in InspectionFormView.vue")
    content = content.replace(old_helper, new_helper, 1)

    old_block = """  const subArea = getSubAreaById(form.sub_area_id);
  const minRequired = Math.max(1, Number(subArea?.photo_min_required || 1));
  const maxAllowed = Math.max(
    minRequired,
    Number(subArea?.photo_max_allowed || 3),
  );
  const photos = getPhotoFiles();
  const hadVideo = !!media.value.video;

  if (!subArea) {
    error.value = "Please select a valid sub-area before saving";
    return;
  }
"""
    new_block = """  const isOther = isOtherSubAreaPayload(form);
  const subArea = isOther ? customSubAreaDraft(form) : getSubAreaById(form.sub_area_id);
  const minRequired = Math.max(1, Number(subArea?.photo_min_required || 1));
  const maxAllowed = Math.max(
    minRequired,
    Number(subArea?.photo_max_allowed || 3),
  );
  const photos = getPhotoFiles();
  const hadVideo = !!media.value.video;

  if (!subArea) {
    error.value = "Please select a valid sub-area before saving";
    return;
  }
  if (isOther && String(form.custom_sub_area_name || '').trim().length < 2) {
    error.value = "Enter Other sub-area name before saving";
    return;
  }
"""
    if old_block not in content:
        raise RuntimeError("Could not find saveEntry sub-area validation block in InspectionFormView.vue")
    content = content.replace(old_block, new_block, 1)

    write_text(path, content)
    print("Patched frontend/src/views/InspectionFormView.vue")


def main():
    root = find_project_root()
    patch_inspection_form_view(root)
    print("Other sub-area save hotfix applied successfully.")


if __name__ == "__main__":
    main()
