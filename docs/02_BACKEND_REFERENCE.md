# Backend Reference Document

## Backend Purpose

The FastAPI backend acts as the central system for:

- Authentication and RBAC
- Master data management
- Inspection capture
- Photo/video metadata persistence
- MinIO object storage integration
- Review and penalty workflow
- Monthly KPI-6 score calculation
- Dashboard data
- Audit logging
- Reports

## Module Structure

```text
app/
├── api/v1/endpoints/     API route handlers
├── core/                 Config, database, security, permissions
├── models/               SQLAlchemy models
├── schemas/              Pydantic request/response schemas
├── services/             Business logic
├── repositories/         Optional query abstraction
├── workers/              Celery worker tasks
└── seeds/                Demo seed data
```

## Design Pattern

The backend follows this flow:

```text
API endpoint → permission check → service → database transaction → audit log → response
```

## Transaction Rule

For business actions such as inspection submit, review and KPI calculation, commit should happen only after:

1. Required validations pass
2. Permission checks pass
3. Workflow state transition is valid
4. Audit log is written

## Role Access Model

Access is not role-only. It is role + line + station + contract.

Example:

```text
Station Manager can create inspection only for assigned station.
Line Manager can review only assigned line/station inspections.
GM/Ops can view all records.
```

## Media Storage Rule

Photos and videos are not stored directly in PostgreSQL. PostgreSQL stores metadata only. Actual files are stored in MinIO.

## Submitted Data Locking

Once an inspection is submitted:

- Grade should not be directly overwritten.
- Media should not be physically deleted.
- Review corrections should be separate records.
- Changes should be traceable through audit logs.
