from datetime import date, datetime, timedelta
from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.models.base import Base
from app.models.all_models import *
from app.services.kpi_calculation_service import calculate_monthly_kpi6


def get_or_create(db, model, defaults=None, **kwargs):
    obj = db.query(model).filter_by(**kwargs).first()
    if obj:
        return obj
    data = dict(kwargs)
    if defaults:
        data.update(defaults)
    obj = model(**data)
    db.add(obj)
    db.flush()
    return obj


def seed_master(db):
    roles = {}
    priority = {
        RoleCode.SUPER_ADMIN: 1, RoleCode.GM_OPS: 2, RoleCode.DGM_LINE: 3, RoleCode.DGM_HK: 3,
        RoleCode.AM_MGR_LINE: 4, RoleCode.AM_MGR_HK: 4, RoleCode.HK_CELL_ADMIN: 4,
        RoleCode.STATION_MANAGER: 5, RoleCode.EIT_MEMBER: 5, RoleCode.AUDITOR: 6,
    }
    for code in RoleCode:
        roles[code] = get_or_create(db, Role, code=code, defaults={"name": code.value.replace("_", " ").title(), "priority_level": priority.get(code, 100)})

    line1 = get_or_create(db, Line, line_code="L1", defaults={"line_name": "Line 1 - Red Line"})
    line2 = get_or_create(db, Line, line_code="L2", defaults={"line_name": "Line 2 - Yellow Line"})
    line3 = get_or_create(db, Line, line_code="L3", defaults={"line_name": "Line 3/4 - Blue Line"})

    stations = [
        ("RKAS", "Rajiv Chowk", line2, 28.6328, 77.2197),
        ("NDLS", "New Delhi", line2, 28.6425, 77.2210),
        ("KB", "Kashmere Gate", line1, 28.6675, 77.2281),
        ("SHD", "Shahdara", line1, 28.6733, 77.2890),
        ("YB", "Yamuna Bank", line3, 28.6233, 77.2679),
        ("MDHS", "Mandi House", line3, 28.6258, 77.2343),
    ]
    station_objs = []
    for code, name, line, lat, lng in stations:
        station_objs.append(get_or_create(db, Station, station_code=code, defaults={"station_name": name, "line_id": line.id, "latitude": lat, "longitude": lng}))

    contractor1 = get_or_create(db, Contractor, contractor_code="CONT-001", defaults={"contractor_name": "Demo Housekeeping Contractor A", "contact_person": "Ravi Kumar", "mobile": "9999999001"})
    contractor2 = get_or_create(db, Contractor, contractor_code="CONT-002", defaults={"contractor_name": "Demo Housekeeping Contractor B", "contact_person": "Neha Sharma", "mobile": "9999999002"})

    scheme = get_or_create(db, GradingScheme, code="G90", defaults={"name": "A100 B90 C80 D70 E60 F50"})
    grades = [("A", 100), ("B", 90), ("C", 80), ("D", 70), ("E", 60), ("F", 50)]
    for idx, (g, pct) in enumerate(grades, start=1):
        get_or_create(db, GradingOption, scheme_id=scheme.id, grade_code=g, defaults={"label": f"{g} = {pct}%", "percentage": pct, "sort_order": idx})

    contract1 = get_or_create(db, Contract, contract_code="MCH-DEMO-001", defaults={
        "tender_no": "DMRC/CHK-Ops-DEMO-01/2026", "contract_name": "Demo Contract - Central Stations",
        "contractor_id": contractor1.id, "start_date": date(2026,1,1), "end_date": date(2030,1,1),
        "monthly_bill_value_default": 1200000, "grading_scheme_id": scheme.id,
    })
    contract2 = get_or_create(db, Contract, contract_code="MCH-DEMO-002", defaults={
        "tender_no": "DMRC/CHK-Ops-DEMO-02/2026", "contract_name": "Demo Contract - East Section",
        "contractor_id": contractor2.id, "start_date": date(2026,1,1), "end_date": date(2030,1,1),
        "monthly_bill_value_default": 950000, "grading_scheme_id": scheme.id,
    })
    for st in station_objs[:3]:
        get_or_create(db, ContractStation, contract_id=contract1.id, station_id=st.id)
    for st in station_objs[3:]:
        get_or_create(db, ContractStation, contract_id=contract2.id, station_id=st.id)

    attrs = [
        ("ATTR_1_CUSTOMER_CONTACT_AREA", "Passenger/customer movement area cleanliness"),
        ("ATTR_2_LIFT_ESCALATOR", "Cleaning and disinfection of Lift and Escalators"),
        ("ATTR_3_GLASS", "Cleaning and disinfection of glass fitted at stations"),
        ("ATTR_4_SS_PVC_MS_HANDRAIL", "Cleaning and disinfection of SS/PVC/MS structures and handrails"),
    ]
    attr_objs = {}
    for idx, (code, name) in enumerate(attrs, start=1):
        attr_objs[code] = get_or_create(db, InspectionAttribute, code=code, defaults={"name": name, "sort_order": idx})

    subareas = [
        ("ATTR_1_CUSTOMER_CONTACT_AREA", "FLOORS", "All types of floors in station building/area"),
        ("ATTR_1_CUSTOMER_CONTACT_AREA", "STAIRCASE", "Staircase in station building/area"),
        ("ATTR_1_CUSTOMER_CONTACT_AREA", "SCR_TOM_CCC_EFO", "SCR/TOM/CCC/EFO"),
        ("ATTR_1_CUSTOMER_CONTACT_AREA", "CONCOURSE", "Concourse"),
        ("ATTR_1_CUSTOMER_CONTACT_AREA", "PASSAGES", "Passages"),
        ("ATTR_1_CUSTOMER_CONTACT_AREA", "PLATFORM", "Platform"),
        ("ATTR_1_CUSTOMER_CONTACT_AREA", "GROUND_LEVEL_COMMON_AREA", "Ground level common area near station entry/exit"),
        ("ATTR_1_CUSTOMER_CONTACT_AREA", "SUBWAY_FOB", "Subway and foot over bridge connected to station"),
        ("ATTR_1_CUSTOMER_CONTACT_AREA", "STATION_SURROUNDING", "Station surrounding area"),
        ("ATTR_1_CUSTOMER_CONTACT_AREA", "KERB_STONES", "Kerb stones"),
        ("ATTR_1_CUSTOMER_CONTACT_AREA", "GREEN_AREA", "General cleaning of green area"),
        ("ATTR_2_LIFT_ESCALATOR", "LIFT", "Lift"),
        ("ATTR_2_LIFT_ESCALATOR", "ESCALATOR", "Escalators"),
        ("ATTR_3_GLASS", "WINDOWS", "Windows"),
        ("ATTR_3_GLASS", "TOM_CCC_SCR", "TOM/CCC/SCR glass"),
        ("ATTR_3_GLASS", "SMOKE_GLASSES", "Smoke glasses"),
        ("ATTR_3_GLASS", "PSD_PLATFORM_SIDE", "PSDs platform side"),
        ("ATTR_3_GLASS", "PARTITION_GLASSES", "Partition glasses"),
        ("ATTR_4_SS_PVC_MS_HANDRAIL", "STAINLESS_STEEL", "Stainless steel"),
        ("ATTR_4_SS_PVC_MS_HANDRAIL", "PVC", "PVC"),
        ("ATTR_4_SS_PVC_MS_HANDRAIL", "MS_STRUCTURE", "MS Structure"),
        ("ATTR_4_SS_PVC_MS_HANDRAIL", "HANDRAILS", "Handrails"),
    ]
    subarea_objs = []
    for idx, (attr_code, code, name) in enumerate(subareas, start=1):
        subarea_objs.append(get_or_create(db, InspectionSubArea, attribute_id=attr_objs[attr_code].id, code=code, defaults={"name": name, "sort_order": idx, "photo_min_required": 1, "photo_max_allowed": 3, "video_required": False, "video_max_seconds": 15, "allow_na": True}))

    user_specs = [
        ("admin", "admin123", "System Admin", RoleCode.SUPER_ADMIN, None),
        ("sm01", "sm123", "Station Manager Rajiv Chowk", RoleCode.STATION_MANAGER, station_objs[0]),
        ("sm02", "sm123", "Station Manager New Delhi", RoleCode.STATION_MANAGER, station_objs[1]),
        ("sm03", "sm123", "Station Manager Yamuna Bank", RoleCode.STATION_MANAGER, station_objs[4]),
        ("eit01", "eit123", "EIT Member North", RoleCode.EIT_MEMBER, station_objs[0]),
        ("eit02", "eit123", "EIT Member East", RoleCode.EIT_MEMBER, station_objs[4]),
        ("lm01", "lm123", "Line Manager Central", RoleCode.AM_MGR_LINE, None),
        ("dgm01", "dgm123", "DGM Line Central", RoleCode.DGM_LINE, None),
        ("gm01", "gm123", "GM Operations", RoleCode.GM_OPS, None),
    ]
    users = {}
    for username, password, name, role_code, station in user_specs:
        u = db.query(User).filter_by(username=username).first()
        if not u:
            u = User(username=username, password_hash=get_password_hash(password), name=name, role_id=roles[role_code].id, emp_number=username.upper())
            db.add(u)
            db.flush()
        users[username] = u
        if station:
            get_or_create(db, UserStationAccess, user_id=u.id, station_id=station.id)
        if role_code in [RoleCode.AM_MGR_LINE, RoleCode.DGM_LINE]:
            for line in [line1, line2, line3]:
                get_or_create(db, UserLineAccess, user_id=u.id, line_id=line.id)
        if role_code in [RoleCode.STATION_MANAGER, RoleCode.EIT_MEMBER] and station:
            get_or_create(db, UserLineAccess, user_id=u.id, line_id=station.line_id)

    return {
        "stations": station_objs,
        "contracts": [contract1, contract2],
        "attrs": list(attr_objs.values()),
        "subareas": subarea_objs,
        "users": users,
    }


def ensure_cycle(db, year, month):
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return get_or_create(db, BillingCycle, code=f"{year}-{month:02d}", defaults={"name": start.strftime("%B %Y"), "start_date": start, "end_date": end})


def grade_for_score(score):
    if score >= 95: return "A", 100
    if score >= 85: return "B", 90
    if score >= 75: return "C", 80
    if score >= 65: return "D", 70
    if score >= 55: return "E", 60
    return "F", 50


def seed_demo_inspections(db, ctx):
    contracts = ctx["contracts"]
    attrs = ctx["attrs"]
    subareas = ctx["subareas"]
    users = ctx["users"]
    cycles = [ensure_cycle(db, 2026, m) for m in range(1, 6)]
    for cycle in cycles:
        for contract in contracts:
            get_or_create(db, MonthlyBillValue, billing_cycle_id=cycle.id, contract_id=contract.id, defaults={"bill_value": contract.monthly_bill_value_default})

    sm_users = [users["sm01"], users["sm02"], users["sm03"]]
    eit_users = [users["eit01"], users["eit02"]]
    stations_by_contract = {c.id: [m.station for m in c.station_mappings] for c in contracts}
    score_patterns = [96, 92, 88, 84, 79, 91, 73, 86, 94, 82, 76, 89]
    statuses = [InspectionStatus.CLOSED, InspectionStatus.DGM_APPROVED, InspectionStatus.LINE_MANAGER_RECOMMENDED, InspectionStatus.UNDER_LINE_MANAGER_REVIEW]

    idx = 0
    for month_idx, cycle in enumerate(cycles):
        for contract in contracts:
            for station in stations_by_contract[contract.id]:
                # 3 SM and 1 EIT inspection per month to demonstrate frequency-weighted reports
                inspectors = [sm_users[idx % len(sm_users)]] * 3 + [eit_users[idx % len(eit_users)]]
                types = [InspectionType.SM_INSPECTION] * 3 + [InspectionType.EIT_INSPECTION]
                for n, (inspector, itype) in enumerate(zip(inspectors, types), start=1):
                    inspection_day = min(26, 3 + n * 5 + (station.id % 3))
                    inspection_date = date(cycle.start_date.year, cycle.start_date.month, inspection_day)
                    insp_no = f"DEMO-{cycle.code}-{contract.id}-{station.id}-{itype.value[:3]}-{n}"
                    existing = db.query(Inspection).filter_by(inspection_no=insp_no).first()
                    if existing:
                        idx += 1
                        continue
                    base_score = score_patterns[(idx + month_idx) % len(score_patterns)]
                    if contract.id == contracts[1].id and cycle.start_date.month in [2, 3]:
                        base_score -= 8  # create penalty months for dashboard demo
                    status = statuses[(idx + n) % len(statuses)]
                    inspection = Inspection(
                        inspection_no=insp_no,
                        contract_id=contract.id,
                        station_id=station.id,
                        inspection_type=itype,
                        inspection_date=inspection_date,
                        started_at=datetime.combine(inspection_date, datetime.min.time()).replace(hour=8, minute=20+n),
                        submitted_at=datetime.combine(inspection_date, datetime.min.time()).replace(hour=9, minute=5+n),
                        submitted_by=inspector.id,
                        latitude=station.latitude,
                        longitude=station.longitude,
                        gps_accuracy=8 + (idx % 6),
                        device_info={"demo": True, "device": "PWA Demo Mobile"},
                        status=status,
                        is_before_10am=True,
                        is_late=False,
                        remarks="Demo inspection generated for dashboard and report demonstration.",
                    )
                    db.add(inspection)
                    db.flush()
                    for a_idx, attr in enumerate(attrs):
                        attr_score = max(50, min(100, base_score - (a_idx * 2) + ((idx + a_idx) % 5)))
                        g, pct = grade_for_score(attr_score)
                        db.add(InspectionAttributeScore(inspection_id=inspection.id, attribute_id=attr.id, grade_code=g, grade_percentage=pct, remarks=f"Demo grade {g} for {attr.name}"))
                    # add representative observations and mock media metadata
                    for sub in subareas[:6]:
                        db.add(InspectionSubAreaObservation(inspection_id=inspection.id, attribute_id=sub.attribute_id, sub_area_id=sub.id, is_applicable=True, observation_text="Demo observation: area inspected with geo-tagged evidence."))
                    for sub in subareas[:3]:
                        db.add(InspectionMedia(
                            inspection_id=inspection.id,
                            attribute_id=sub.attribute_id,
                            sub_area_id=sub.id,
                            media_type=MediaType.PHOTO,
                            object_path=f"demo/contract-{contract.id}/station-{station.station_code}/{insp_no}/{sub.code}.jpg",
                            original_file_name=f"{sub.code}.jpg",
                            mime_type="image/jpeg",
                            file_size=245000,
                            checksum=f"demo-checksum-{insp_no}-{sub.code}",
                            captured_latitude=station.latitude,
                            captured_longitude=station.longitude,
                            gps_accuracy=9,
                            captured_at=datetime.combine(inspection_date, datetime.min.time()).replace(hour=8, minute=40),
                            uploaded_by=inspector.id,
                            processing_status="DEMO",
                        ))
                    db.add(InspectionWorkflowHistory(inspection_id=inspection.id, from_status=None, to_status=status.value, action_by=inspector.id, action="DEMO_SEED", remarks="Seeded demo inspection"))
                    idx += 1
    db.commit()
    # calculate scores after all demo inspections exist
    for cycle in cycles:
        for contract in contracts:
            calculate_monthly_kpi6(db, cycle.id, contract.id)


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ctx = seed_master(db)
        db.commit()
        seed_demo_inspections(db, ctx)
        db.commit()
        print("Seed completed with dashboard/report demo data")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
