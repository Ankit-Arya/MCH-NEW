from pathlib import Path
import re


PATCH_MARKER = "LEAVE_INSPECTION_WARNING"


def find_project_root():
    candidates = []
    cwd = Path.cwd().resolve()
    candidates.append(cwd)
    script_path = Path(__file__).resolve()
    candidates.extend(script_path.parents)

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        target = candidate / "frontend" / "src" / "views" / "InspectionFormView.vue"
        if target.exists():
            return candidate

    raise RuntimeError(
        "Could not find project root. Run this script from the repository root "
        "or keep it under backend/scripts inside the project."
    )


def read_text(path):
    with path.open("r", encoding="utf-8") as handle:
        return handle.read()


def write_text(path, content):
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(content)


def ensure_vue_import(content):
    pattern = re.compile(r'import\s*\{([^}]+)\}\s*from\s*["\']vue["\'];?')
    match = pattern.search(content)
    if not match:
        raise RuntimeError("Could not find Vue import in InspectionFormView.vue")

    names = [name.strip() for name in match.group(1).split(",") if name.strip()]
    if "onBeforeUnmount" not in names:
        # Keep existing order stable and add only what this patch needs.
        insert_at = names.index("onMounted") if "onMounted" in names else len(names)
        names.insert(insert_at, "onBeforeUnmount")
    replacement = 'import { ' + ', '.join(names) + ' } from "vue";'
    return content[:match.start()] + replacement + content[match.end():]


def ensure_router_import(content):
    pattern = re.compile(r'import\s*\{([^}]+)\}\s*from\s*["\']vue-router["\'];?')
    match = pattern.search(content)
    if not match:
        raise RuntimeError("Could not find vue-router import in InspectionFormView.vue")

    names = [name.strip() for name in match.group(1).split(",") if name.strip()]
    if "onBeforeRouteLeave" not in names:
        names.insert(0, "onBeforeRouteLeave")
    replacement = 'import { ' + ', '.join(names) + ' } from "vue-router";'
    return content[:match.start()] + replacement + content[match.end():]


def ensure_guard_block(content):
    if PATCH_MARKER in content:
        return content

    anchor = '''function reloadPage() {
  window.location.reload();
}
'''
    if anchor not in content:
        raise RuntimeError("Could not find reloadPage block for safe insertion")

    block = '''function reloadPage() {
  window.location.reload();
}

const LEAVE_INSPECTION_WARNING =
  "Your inspection is still in progress. If you leave this page, unsaved progress will be lost. Continue?";

const shouldWarnBeforeLeaving = computed(() => {
  if (!inspection.value) return false;
  if (saving.value || submitting.value) return true;
  return canEdit.value;
});

function confirmLeaveInspection() {
  if (!shouldWarnBeforeLeaving.value) return true;
  return window.confirm(LEAVE_INSPECTION_WARNING);
}

function handleBeforeUnload(event) {
  if (!shouldWarnBeforeLeaving.value) return;
  event.preventDefault();
  event.returnValue = "";
}

onBeforeRouteLeave((_to, _from, next) => {
  if (confirmLeaveInspection()) next();
  else next(false);
});
'''
    return content.replace(anchor, block, 1)


def ensure_beforeunload_mount(content):
    if 'window.addEventListener("beforeunload", handleBeforeUnload);' not in content:
        anchor = '''onMounted(async () => {
  loading.value = true;
'''
        if anchor not in content:
            raise RuntimeError("Could not find onMounted block for beforeunload listener")
        content = content.replace(
            anchor,
            '''onMounted(async () => {
  window.addEventListener("beforeunload", handleBeforeUnload);
  loading.value = true;
''',
            1,
        )

    if 'window.removeEventListener("beforeunload", handleBeforeUnload);' not in content:
        anchor = '''});
</script>
'''
        if anchor not in content:
            raise RuntimeError("Could not find script closing block for beforeunload cleanup")
        content = content.replace(
            anchor,
            '''});

onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", handleBeforeUnload);
});
</script>
''',
            1,
        )

    return content


def patch_inspection_form():
    root = find_project_root()
    path = root / "frontend" / "src" / "views" / "InspectionFormView.vue"
    original = read_text(path)
    content = original
    content = ensure_vue_import(content)
    content = ensure_router_import(content)
    content = ensure_guard_block(content)
    content = ensure_beforeunload_mount(content)

    if content != original:
        write_text(path, content)
        print("Patched", path)
    else:
        print("Already patched", path)


def main():
    patch_inspection_form()
    print("Inspection leave-warning patch applied successfully.")


if __name__ == "__main__":
    main()
