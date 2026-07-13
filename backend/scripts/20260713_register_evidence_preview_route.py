from pathlib import Path

router_path = Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "router.py"
text = router_path.read_text(encoding="utf-8")

if "evidence_preview" not in text:
    text = text.replace(
        "from app.api.v1.endpoints import auth, master, inspections, reviews, kpi, dashboard, reports, users, access_control, admin_sql, kpi_chemicals, weekly_compliance, help",
        "from app.api.v1.endpoints import auth, master, inspections, reviews, kpi, dashboard, reports, users, access_control, admin_sql, kpi_chemicals, weekly_compliance, help, evidence_preview",
    )

route_line = 'api_router.include_router(evidence_preview.router, prefix="/inspections/media", tags=["Inspection Evidence Preview"])'
if route_line not in text:
    marker = 'api_router.include_router(inspections.router, prefix="/inspections", tags=["Inspections"])'
    text = text.replace(marker, f'{route_line}\n{marker}')

router_path.write_text(text, encoding="utf-8")
print("Evidence preview route registered in backend/app/api/v1/router.py")
