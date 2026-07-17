from pathlib import Path


def find_project_root():
    cwd = Path.cwd().resolve()
    candidates = [cwd] + list(cwd.parents)
    for base in candidates:
        if (base / "backend" / "app" / "api" / "v1" / "endpoints" / "inspections.py").exists():
            return base
    for base in candidates:
        if (base / "app" / "api" / "v1" / "endpoints" / "inspections.py").exists():
            return base.parent
    raise RuntimeError("Could not find project root containing backend/app/api/v1/endpoints/inspections.py")


ROOT = find_project_root()
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def read_text(path):
    with path.open("r", encoding="utf-8") as f:
        return f.read()


def write_text(path, content):
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(content)


def replace_once(content, old, new, label):
    if old not in content:
        raise RuntimeError("Could not find expected block for " + label)
    return content.replace(old, new, 1)


def ensure_model_imports(content):
    if "InspectionAttributeScore," not in content:
        content = replace_once(
            content,
            "    InspectionAttribute,\n    InspectionEntry,",
            "    InspectionAttribute,\n    InspectionAttributeScore,\n    InspectionEntry,",
            "InspectionAttributeScore import",
        )
    if "InspectionSubAreaObservation," not in content:
        content = replace_once(
            content,
            "    InspectionSubArea,\n    InspectionType,",
            "    InspectionSubArea,\n    InspectionSubAreaObservation,\n    InspectionType,",
            "InspectionSubAreaObservation import",
        )
    return content


def patch_checklist_function(content):
    marker = '@router.get("/checklist")\n'
    next_marker = '@router.post("/start", response_model=InspectionOut)\n'
    start = content.find(marker)
    end = content.find(next_marker, start)
    if start == -1 or end == -1:
        raise RuntimeError("Could not find checklist function block")

    new_block = '''@router.get("/checklist")
def checklist(contract_id: int, station_id: int, inspection_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return checklist for normal station access or an authorised emergency draft.

    Emergency inspections intentionally bypass normal station mapping at start time.
    The same bypass must continue while loading the entry form; otherwise the draft
    opens successfully and then fails on checklist load with 403.
    """

    try:
        require_station_access(db, user, station_id)
    except HTTPException as exc:
        if exc.status_code != 403:
            raise

        inspection = None
        if inspection_id:
            inspection = db.get(Inspection, inspection_id)
            if not inspection or int(inspection.station_id) != int(station_id) or int(inspection.contract_id) != int(contract_id):
                raise
        else:
            # Backward-compatible fallback for older/cached frontend builds that do
            # not pass inspection_id to /checklist. Only the logged-in user's own
            # draft/returned emergency inspection can use this path.
            inspection = (
                db.query(Inspection)
                .filter(
                    Inspection.submitted_by == user.id,
                    Inspection.station_id == station_id,
                    Inspection.contract_id == contract_id,
                    Inspection.status.in_([InspectionStatus.DRAFT, InspectionStatus.RETURNED_FOR_CLARIFICATION]),
                )
                .order_by(Inspection.id.desc())
                .first()
            )
            if not inspection:
                raise

        try:
            require_inspection_station_access_for_edit(db, user, inspection)
        except HTTPException:
            # Preserve the original station-access denial instead of leaking whether
            # another inspection id exists.
            raise exc

    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    grading = db.query(GradingOption).filter_by(scheme_id=contract.grading_scheme_id).order_by(GradingOption.sort_order).all()
    attributes = db.query(InspectionAttribute).filter_by(is_active=True).order_by(InspectionAttribute.sort_order).all()
    sub_areas = db.query(InspectionSubArea).filter_by(is_active=True).order_by(InspectionSubArea.sort_order).all()
    return {
        "contract": contract,
        "station": db.get(Station, station_id),
        "grading_options": grading,
        "grades": grading,
        "attributes": attributes,
        "sub_areas": sub_areas,
    }



'''
    return content[:start] + new_block + content[end:]


def patch_inspections_endpoint():
    path = BACKEND / "app" / "api" / "v1" / "endpoints" / "inspections.py"
    content = read_text(path)
    before = content
    content = ensure_model_imports(content)
    content = patch_checklist_function(content)
    if content != before:
        write_text(path, content)
        print("patched", path.relative_to(ROOT))
    else:
        print("no changes", path.relative_to(ROOT))


def patch_inspection_form_view():
    path = FRONTEND / "src" / "views" / "InspectionFormView.vue"
    if not path.exists():
        print("skipped missing", path.relative_to(ROOT))
        return
    content = read_text(path)
    before = content
    old = "`/inspections/checklist?contract_id=${contractId}&station_id=${stationId}`,"
    new = "`/inspections/checklist?contract_id=${contractId}&station_id=${stationId}&inspection_id=${route.params.id}`,"
    if old in content:
        content = content.replace(old, new, 1)
    elif "inspection_id=${route.params.id}" in content:
        pass
    else:
        raise RuntimeError("Could not find checklist API call in InspectionFormView.vue")
    if content != before:
        write_text(path, content)
        print("patched", path.relative_to(ROOT))
    else:
        print("no changes", path.relative_to(ROOT))


def main():
    print("Project root:", ROOT)
    patch_inspections_endpoint()
    patch_inspection_form_view()
    print("Emergency checklist + delete draft hotfix applied successfully.")


if __name__ == "__main__":
    main()
