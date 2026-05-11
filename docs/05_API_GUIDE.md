# API Guide

Base path:

```text
/api/v1
```

Interactive OpenAPI docs:

```text
/api/docs
```

## Auth

```text
POST /auth/login
POST /auth/refresh
GET  /auth/me
POST /auth/logout
```

## Master Data

```text
GET  /master/bootstrap
GET  /master/stations
POST /master/stations
GET  /master/contracts
POST /master/contracts
GET  /master/inspection-attributes
GET  /master/grading-schemes
```

## Inspections

```text
GET  /inspections
GET  /inspections/{inspection_id}
GET  /inspections/checklist
POST /inspections/start
PUT  /inspections/{inspection_id}/draft
POST /inspections/{inspection_id}/media
POST /inspections/{inspection_id}/submit
```

## Reviews

```text
GET  /reviews/pending
POST /reviews/{inspection_id}/line-manager
POST /reviews/{inspection_id}/dgm
POST /reviews/{inspection_id}/gm
```

## KPI and Penalty

```text
POST /kpi/calculate/monthly
GET  /kpi/station-scores
GET  /kpi/contract-scores
GET  /kpi/penalties
```

## Dashboard

```text
GET /dashboard/summary
GET /dashboard/contract-wise-score
GET /dashboard/station-wise-score
GET /dashboard/pending-reviews
```

## Reports

```text
GET /reports/inspection/{inspection_id}/pdf
GET /reports/monthly-score/excel
```
