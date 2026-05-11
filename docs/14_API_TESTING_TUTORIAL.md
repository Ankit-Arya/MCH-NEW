# API Testing Tutorial

This document explains how to test the backend APIs using Swagger, curl or Postman.

---

## 1. Open Swagger UI

After starting Docker:

```text
http://localhost/api/docs
```

Swagger lets you test all FastAPI endpoints from browser.

---

## 2. Login and get token

Endpoint:

```text
POST /api/v1/auth/login
```

Example curl:

```bash
curl -X POST "http://localhost/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Response:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

Store access token in shell:

```bash
TOKEN="paste_access_token_here"
```

Use token:

```bash
-H "Authorization: Bearer $TOKEN"
```

---

## 3. Check current user

```bash
curl "http://localhost/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

Expected response:

```json
{
  "id": 1,
  "username": "admin",
  "name": "System Admin",
  "role": "SUPER_ADMIN",
  "permissions": ["SUPER_ADMIN"]
}
```

---

## 4. Get bootstrap master data

```bash
curl "http://localhost/api/v1/master/bootstrap" \
  -H "Authorization: Bearer $TOKEN"
```

This returns:

```text
lines
stations
contracts
attributes
grading schemes
```

Use returned IDs for inspection creation.

---

## 5. Start inspection

Endpoint:

```text
POST /api/v1/inspections/start
```

Example:

```bash
curl -X POST "http://localhost/api/v1/inspections/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": 1,
    "station_id": 1,
    "inspection_type": "SM_INSPECTION",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "gps_accuracy": 12.5,
    "device_info": {"browser":"Chrome","platform":"Android"},
    "remarks": "Routine morning inspection"
  }'
```

Response includes:

```text
inspection id
inspection_no
status DRAFT
```

Save inspection id:

```bash
INSPECTION_ID=1
```

---

## 6. Get checklist

```bash
curl "http://localhost/api/v1/inspections/checklist?contract_id=1&station_id=1" \
  -H "Authorization: Bearer $TOKEN"
```

Use returned:

```text
attribute ids
sub-area ids
grade codes
```

---

## 7. Upload photo/video evidence

Endpoint:

```text
POST /api/v1/inspections/{inspection_id}/media
```

Photo upload example:

```bash
curl -X POST "http://localhost/api/v1/inspections/$INSPECTION_ID/media" \
  -H "Authorization: Bearer $TOKEN" \
  -F "attribute_id=1" \
  -F "sub_area_id=1" \
  -F "media_type=PHOTO" \
  -F "captured_latitude=28.6139" \
  -F "captured_longitude=77.2090" \
  -F "gps_accuracy=10" \
  -F "file=@sample-photo.jpg"
```

Video upload example:

```bash
curl -X POST "http://localhost/api/v1/inspections/$INSPECTION_ID/media" \
  -H "Authorization: Bearer $TOKEN" \
  -F "attribute_id=1" \
  -F "sub_area_id=1" \
  -F "media_type=VIDEO" \
  -F "file=@sample-video.mp4"
```

Important: submit will fail until every applicable sub-area has the required photo count.

---

## 8. Save inspection draft

Endpoint:

```text
PUT /api/v1/inspections/{inspection_id}/draft
```

Example:

```bash
curl -X PUT "http://localhost/api/v1/inspections/$INSPECTION_ID/draft" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "attribute_scores": [
      {"attribute_id": 1, "grade_code": "A", "remarks": "Clean"},
      {"attribute_id": 2, "grade_code": "B", "remarks": "Minor dust observed"},
      {"attribute_id": 3, "grade_code": "A", "remarks": "Clean"},
      {"attribute_id": 4, "grade_code": "A", "remarks": "Clean"}
    ],
    "observations": [
      {"attribute_id": 1, "sub_area_id": 1, "is_applicable": true, "na_reason": null, "observation_text": "Floor clean"},
      {"attribute_id": 1, "sub_area_id": 2, "is_applicable": false, "na_reason": "No staircase at this station area", "observation_text": null}
    ],
    "remarks": "Draft saved after inspection"
  }'
```

---

## 9. Submit inspection

Endpoint:

```text
POST /api/v1/inspections/{inspection_id}/submit
```

Payload is same as draft.

```bash
curl -X POST "http://localhost/api/v1/inspections/$INSPECTION_ID/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @inspection_payload.json
```

Expected status after success:

```text
UNDER_LINE_MANAGER_REVIEW
```

If it fails, check error message. Common errors:

```text
Missing grading for attributes
At least 1 photo required
N/A reason is required
```

---

## 10. Get pending reviews

```bash
curl "http://localhost/api/v1/reviews/pending" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 11. Line Manager review

Endpoint:

```text
POST /api/v1/reviews/{inspection_id}/line-manager
```

Recommend penalty:

```bash
curl -X POST "http://localhost/api/v1/reviews/$INSPECTION_ID/line-manager" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "RECOMMEND_PENALTY",
    "comments": "Cleanliness below expected level in passenger area.",
    "recommended_penalty_amount": 5000
  }'
```

Return for clarification:

```bash
curl -X POST "http://localhost/api/v1/reviews/$INSPECTION_ID/line-manager" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "RETURN_FOR_CLARIFICATION",
    "comments": "Photo evidence is not clear. Please resubmit."
  }'
```

---

## 12. DGM review

Endpoint:

```text
POST /api/v1/reviews/{inspection_id}/dgm
```

Approve:

```bash
curl -X POST "http://localhost/api/v1/reviews/$INSPECTION_ID/dgm" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "APPROVE",
    "comments": "Penalty approved.",
    "final_penalty_amount": 5000
  }'
```

Send to GM:

```bash
curl -X POST "http://localhost/api/v1/reviews/$INSPECTION_ID/dgm" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "SEND_TO_GM",
    "comments": "GM review required due to repeated issue."
  }'
```

---

## 13. GM review

Endpoint:

```text
POST /api/v1/reviews/{inspection_id}/gm
```

```bash
curl -X POST "http://localhost/api/v1/reviews/$INSPECTION_ID/gm" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "GM_REVIEW",
    "comments": "Reviewed by GM/Ops."
  }'
```

---

## 14. Monthly KPI calculation

Endpoint:

```text
POST /api/v1/kpi/calculate/monthly
```

```bash
curl -X POST "http://localhost/api/v1/kpi/calculate/monthly" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "billing_cycle_id": 1,
    "contract_id": 1
  }'
```

Expected response:

```json
{
  "contract_id": 1,
  "billing_cycle_id": 1,
  "average_score": 87.5,
  "is_penalty_applicable": true,
  "penalty_amount": 50000
}
```

---

## 15. Check KPI results

Station scores:

```bash
curl "http://localhost/api/v1/kpi/station-scores" \
  -H "Authorization: Bearer $TOKEN"
```

Contract scores:

```bash
curl "http://localhost/api/v1/kpi/contract-scores" \
  -H "Authorization: Bearer $TOKEN"
```

Penalties:

```bash
curl "http://localhost/api/v1/kpi/penalties" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 16. Dashboard API

```bash
curl "http://localhost/api/v1/dashboard/summary" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 17. Report API

```bash
curl "http://localhost/api/v1/reports/inspection/$INSPECTION_ID/pdf" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 18. Postman collection structure

Create folders:

```text
Auth
Master Data
Inspections
Reviews
KPI
Dashboard
Reports
```

Create environment variables:

```text
base_url = http://localhost/api/v1
token = <access_token>
inspection_id = 1
contract_id = 1
station_id = 1
billing_cycle_id = 1
```

Authorization header for all protected APIs:

```text
Authorization: Bearer {{token}}
```

---

## 19. Testing checklist

```text
Login works.
/me returns current user.
Bootstrap returns master data.
Start inspection creates DRAFT.
Media upload creates inspection_media row and MinIO object.
Draft save creates scores and observations.
Submit blocks missing mandatory data.
Submit changes status to UNDER_LINE_MANAGER_REVIEW.
Line Manager review changes status correctly.
DGM review changes status correctly.
GM review changes status correctly.
Monthly KPI calculation creates scores and penalty.
Dashboard counts update.
Audit logs are created.
```
