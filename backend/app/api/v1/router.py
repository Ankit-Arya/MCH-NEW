from fastapi import APIRouter
from app.api.v1.endpoints import auth, master, inspections, reviews, kpi, dashboard, reports, users, access_control, admin_sql, kpi_chemicals, weekly_compliance

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(master.router, prefix="/master", tags=["Master Data"])
api_router.include_router(access_control.router, prefix="/access-control", tags=["Access Control"])
api_router.include_router(inspections.router, prefix="/inspections", tags=["Inspections"])
api_router.include_router(weekly_compliance.router, prefix="/weekly-compliance", tags=["Weekly Compliance"])
api_router.include_router(kpi_chemicals.router, prefix="/kpi-chemicals", tags=["KPI Chemicals"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
api_router.include_router(kpi.router, prefix="/kpi", tags=["KPI"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(admin_sql.router, prefix="/admin-sql", tags=["Admin SQL"])
