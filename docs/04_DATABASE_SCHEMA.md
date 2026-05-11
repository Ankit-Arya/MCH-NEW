# Database Schema Reference

## Important Tables

### Identity and Access

- `roles`
- `users`
- `user_station_access`
- `user_line_access`

### Master Data

- `lines`
- `stations`
- `contractors`
- `contracts`
- `contract_stations`
- `grading_schemes`
- `grading_options`
- `inspection_attributes`
- `inspection_sub_areas`

### Inspection Transactions

- `inspections`
- `inspection_attribute_scores`
- `inspection_sub_area_observations`
- `inspection_media`
- `inspection_reviews`
- `inspection_workflow_history`

### KPI and Penalty

- `billing_cycles`
- `monthly_bill_values`
- `monthly_station_scores`
- `monthly_contract_scores`
- `penalty_calculations`

### Audit and Notification

- `audit_logs`
- `notifications`

## ER Diagram

```mermaid
erDiagram
    roles ||--o{ users : assigned
    users ||--o{ inspections : creates
    users ||--o{ inspection_reviews : reviews
    lines ||--o{ stations : contains
    contractors ||--o{ contracts : owns
    contracts ||--o{ contract_stations : includes
    stations ||--o{ contract_stations : mapped
    contracts ||--o{ inspections : has
    stations ||--o{ inspections : has
    inspections ||--o{ inspection_attribute_scores : contains
    inspections ||--o{ inspection_sub_area_observations : contains
    inspections ||--o{ inspection_media : stores
    inspections ||--o{ inspection_reviews : reviewed
    inspections ||--o{ inspection_workflow_history : tracks
    grading_schemes ||--o{ grading_options : contains
    inspection_attributes ||--o{ inspection_sub_areas : contains
```
