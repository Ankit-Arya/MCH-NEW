# Requirement Traceability

This project is mapped to the MCH KPI-6 real-time inspection requirement.

## Source Requirement Summary

The application is required for the upcoming Mechanized Cleaning & Housekeeping tenders and should support KPI-6, Level of Cleanliness.

Core requirements implemented in this project:

| Requirement | Implementation Area |
|---|---|
| Real-time inspection submission from stations | Vue PWA + FastAPI `/inspections/start`, `/inspections/{id}/submit` |
| Geo-tagging | GPS fields on inspection and media tables |
| Photo and video evidence | MinIO object storage + `inspection_media` table |
| Up to 3 photos or N/A | `inspection_sub_areas.photo_max_allowed` and frontend validation |
| Grading dropdown | `grading_schemes` and `grading_options` |
| Dashboard for KPI-6 monitoring | Dashboard APIs and Vue dashboard views |
| Audit trail and secure storage | `audit_logs`, workflow history and private MinIO storage |
| Role-based access | JWT + RBAC + user station/line access mapping |
| SM/EIT inspection | `inspection_type = SM_INSPECTION` or `EIT_INSPECTION` |
| Line Manager review | Review workflow endpoints |
| Dy. HoD penalty decision | DGM review endpoint |
| GM/Ops review | GM review workflow state |
| KPI-6 monthly score calculation | `kpi_calculation_service.py` |
| 5% monthly bill penalty below 90% score | penalty calculation module |

## Important Conflict Captured

The requirement contains two grading scales:

1. A=100, B=90, C=80, D=70, E=60, F=50 or below
2. A=100, B=80, C=60, D=40, E=20, F=0

Therefore, the project keeps grading configurable in database instead of hardcoding it in Python code.
