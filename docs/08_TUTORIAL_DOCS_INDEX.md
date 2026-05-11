# Tutorial Documentation Index

These tutorial documents are meant to be copied into the existing project `docs/` folder of the MCH KPI-6 Inspection Platform.

The earlier documents explain the requirement, schema, API and deployment at reference level. This tutorial set explains how the actual code is organised, how each backend/frontend/microservice part works, and how a developer should extend or debug the system.

## Recommended reading order

1. `08_TUTORIAL_DOCS_INDEX.md` — this file.
2. `09_BACKEND_CODE_TUTORIAL.md` — FastAPI backend file-by-file walkthrough.
3. `10_FRONTEND_CODE_TUTORIAL.md` — Vue frontend file-by-file walkthrough.
4. `11_MICROSERVICES_AND_DOCKER_TUTORIAL.md` — Docker Compose services, on-prem data flow, ports, logs.
5. `12_DATABASE_AND_MIGRATION_TUTORIAL.md` — PostgreSQL models, migrations, seed data, common DB changes.
6. `13_END_TO_END_WORKFLOW_TUTORIAL.md` — complete user and backend workflow from login to penalty.
7. `14_API_TESTING_TUTORIAL.md` — how to test API endpoints using Swagger, curl or Postman.
8. `15_PRODUCTION_HANDOVER_AND_OPERATIONS.md` — deployment, backup, restore, security and UAT checklist.
9. `16_CODE_EXTENSION_GUIDE.md` — how to add new features safely.

## How to use these docs

Copy the whole `docs/` folder from this package into your downloaded project and keep the same numbering:

```bash
cp -r mch-tutorial-docs/docs/* mch-inspection-platform/docs/
```

Then open them in VS Code or any Markdown viewer.

## Important development principle

The project is designed as a modular monolith backend with supporting on-prem services. That means the FastAPI backend is one deployable application, but internally it is separated into modules:

- Auth and RBAC
- Master data
- Inspection capture
- Media handling
- Review workflow
- KPI calculation
- Dashboard
- Reports
- Audit logging

This gives simple on-prem deployment now and allows service extraction later if the system grows.
