# New Inspection Entry API Reference

## Start parent inspection

```http
POST /api/v1/inspections/start
```

Creates only the parent inspection header. It does not create checklist rows.

## Get parent inspection

```http
GET /api/v1/inspections/{inspection_id}
```

## Load attribute dropdown

```http
GET /api/v1/master/inspection-attributes
```

## Load dependent sub-area dropdown

```http
GET /api/v1/master/inspection-attributes/{attribute_id}/sub-areas
```

## Load grading options

```http
GET /api/v1/master/contracts/{contract_id}/grading-options
```

The current UI uses `/inspections/checklist` for grades and attributes, and the dedicated sub-area endpoint for dependent dropdown.

## Save selected inspection entry

```http
POST /api/v1/inspections/{inspection_id}/entries
```

Example:

```json
{
  "attribute_id": 1,
  "sub_area_id": 5,
  "grade_code": "B",
  "remarks": "Dust observed near platform end.",
  "captured_latitude": 28.6139,
  "captured_longitude": 77.209,
  "gps_accuracy": 12,
  "captured_at": "2026-06-02T09:42:00"
}
```

## Upload media for entry

```http
POST /api/v1/inspections/{inspection_id}/entries/{entry_id}/media
```

Multipart fields:

```text
media_type = PHOTO or VIDEO
file = selected file
captured_latitude
captured_longitude
gps_accuracy
captured_at
```

## List saved entries

```http
GET /api/v1/inspections/{inspection_id}/entries
```

## Delete draft entry

```http
DELETE /api/v1/inspections/{inspection_id}/entries/{entry_id}
```

Allowed only before submission.

## Submit inspection

```http
POST /api/v1/inspections/{inspection_id}/submit
```

Rules:

```text
At least one entry required.
Every entry must have at least one PHOTO.
Video optional.
Skipped areas are Not Inspected, not failed.
```
