## Plan Versions – Frontend Integration

New authenticated endpoints expose historical training plan snapshots. They share the same auth pattern as other private APIs (`Authorization: Bearer <token>`).

### GET `/plans/versions/`
Returns paginated versions for the current user. Optional filters:

| Query param | Type | Default | Notes |
|-------------|------|---------|-------|
| `plan_id`   | int  | `null`  | Filter versions linked to a specific stored plan (if available) |
| `limit`     | int  | 20      | Page size, 1–100 |
| `offset`    | int  | 0       | Skip count for pagination |

**Example**
```
GET /plans/versions/?limit=10&offset=0
Authorization: Bearer <token>
```

**Response**
```json
{
  "items": [
    {
      "id": 42,
      "created_at": "2025-11-12T18:40:22.910Z",
      "duration_weeks": 8,
      "sport_type": "running",
      "level": "intermediate",
      "version_label": null,
      "description": null
    }
  ],
  "total": 7,
  "limit": 10,
  "offset": 0
}
```

### GET `/plans/versions/{version_id}`
Returns the stored JSON payload and metadata for a specific snapshot.

**Example**
```
GET /plans/versions/42
Authorization: Bearer <token>
```

**Response**
```json
{
  "id": 42,
  "created_at": "2025-11-12T18:40:22.910Z",
  "duration_weeks": 8,
  "sport_type": "running",
  "level": "intermediate",
  "plan_id": null,
  "version_label": null,
  "description": null,
  "plan_payload": {
    "title": "Half Marathon Builder",
    "duration_weeks": 8,
    "weeks": [
      // ... existing code ...
    ]
  },
  "validator_violations": null
}
```

### UI usage tips
- Use the list endpoint to populate a “Plan history” table (sort order is newest first).
- When displaying a version, render `plan_payload` with the same components used for live plans.
- `validator_violations` is reserved for future use (stores critical warnings if a plan failed validation).

