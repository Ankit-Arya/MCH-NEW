# KPI Chemicals Reports Import Hotfix

This hotfix fixes API startup failure after applying the KPI Chemicals Phase-1 patch.

Error fixed:

```text
NameError: name 'ChemicalInspectionEntry' is not defined
```

Replace:

```text
backend/app/api/v1/endpoints/reports.py
```

Then rebuild/restart API:

```bat
docker compose up -d --build api
```

Then check:

```bat
docker compose logs api --tail=100
```
