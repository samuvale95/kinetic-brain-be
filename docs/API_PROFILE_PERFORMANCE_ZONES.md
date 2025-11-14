# Profile, Performance & Zone API Reference

This document collects everything the frontend needs to work with the profile and performance endpoints, including structured zone handling and ready-to-send request examples.

- Base path: `/profile`
- Authentication: all endpoints below require the standard bearer token, except for the CORS `OPTIONS` handlers.
- Response dates/timestamps are ISO 8601 strings (UTC).

## Data Models

### User Profile (`GET/POST/PUT /profile`)

Fields:

- `age`: integer 13–100  
- `gender`: `"male" | "female" | "other"`  
- `weight`: float kg (used for auto-calculating `wkg`)  
- `height`: float cm  
- `sports`: array of strings  
- `experience_years`: integer ≥ 0  
- `weekly_hours`: float ≥ 0  
- `main_goal`, `physical_notes`: strings  
- `city`, `latitude`, `longitude`: optional location metadata  
- `preferred_zone_type`: `"hr" | "pace" | "power"` (defaults to `"hr"`)  
- `created_at`, `updated_at`: timestamps

### Performance Metrics Record

Each `PerformanceMetrics` entry represents a snapshot for a user. `GET /profile/performance` returns a list ordered by `test_date` descending.

- `test_date`: optional date; defaults to creation timestamp when omitted
- HR metrics: `hr_max`, `hr_rest`, `threshold_hr`, `hrr`, `custom_threshold_hr`
- Pace metrics: `threshold_pace` (`"mm:ss"` or `"mm.ss"`), `critical_speed`, `vla`
- Power metrics: `ftp`, `wkg`
- Advanced metric: `vo2max`
- Structured zones: `hr_zones`, `pace_zones`, `power_zones` (maps `z1`… with string ranges), corresponding `*_zones_source` (`"auto"` or `"manual"`), and `hr_threshold_used`, `threshold_pace_used`, `ftp_used`
- Metadata: `id`, `user_id`, `created_at`, `updated_at`

Auto-calculated helpers:

- `hrr = hr_max - hr_rest` when both values are provided and zones are recalculated.
- `wkg` is recomputed on `POST/PUT` when `ftp` is present and the profile has a `weight`.
- When a `*_zones_source` is `"auto"` (or left unset while the required threshold value is provided), the backend recalculates the relevant zones and fills `*_threshold_used`.

## Endpoint Details

### GET `/profile`

Returns the current user profile. If `preferred_zone_type` was never set, it is defaulted to `"hr"` on read.

Sample response:

```json
{
  "id": 4,
  "user_id": 7,
  "age": 35,
  "gender": "male",
  "weight": 70.5,
  "height": 178.0,
  "sports": ["run", "bike"],
  "experience_years": 6,
  "weekly_hours": 8.5,
  "main_goal": "Improve marathon time",
  "physical_notes": "Knee rehab ongoing",
  "city": "Milano",
  "latitude": 45.46,
  "longitude": 9.19,
  "created_at": "2025-02-04T10:12:55.182314+00:00",
  "updated_at": "2025-02-04T10:12:55.182314+00:00"
}
```

### POST `/profile`

Creates the profile for the authenticated user. Error `400` if a profile already exists.

```http
POST /profile
Authorization: Bearer <token>
Content-Type: application/json

{
  "age": 35,
  "gender": "male",
  "weight": 70.5,
  "height": 178,
  "sports": ["run", "bike"],
  "experience_years": 6,
  "weekly_hours": 8.5,
  "main_goal": "Improve marathon time",
  "physical_notes": "Knee rehab ongoing",
  "city": "Milano",
  "latitude": 45.46,
  "longitude": 9.19
}
```

### PUT `/profile`

Partial updates are supported; send only the fields that change.

```http
PUT /profile
Authorization: Bearer <token>

{
  "weekly_hours": 10,
  "main_goal": "Sub-3 marathon",
  "preferred_zone_type": "pace"
}
```

### GET `/profile/performance`

Returns a list of performance metric records for the user, newest first.

```http
GET /profile/performance
Authorization: Bearer <token>
```

Sample response (single record for brevity):

```json
[
  {
    "id": 18,
    "user_id": 7,
    "hr_max": 190,
    "hr_rest": 50,
    "threshold_hr": 170,
    "hrr": 140,
    "custom_threshold_hr": null,
    "threshold_pace": "4:15",
    "critical_speed": 14.2,
    "vla": 13.8,
    "ftp": 300,
    "wkg": 4.29,
    "vo2max": 55,
    "hr_zones": {
      "z1": "120-135",
      "z2": "135-150",
      "z3": "150-165",
      "z4": "165-180",
      "z5": "180-195"
    },
    "hr_zones_source": "auto",
    "hr_threshold_used": 170,
    "pace_zones": {
      "z1": "5:30-5:00",
      "z2": "5:00-4:45",
      "z3": "4:45-4:30",
      "z4": "4:30-4:15",
      "z5": "4:15-4:00"
    },
    "pace_zones_source": "auto",
    "threshold_pace_used": "4:15",
    "power_zones": {
      "z1": "0-165",
      "z2": "166-225",
      "z3": "226-270",
      "z4": "271-315",
      "z5": "316-360",
      "z6": "361-450",
      "z7": "451-540"
    },
    "power_zones_source": "auto",
    "ftp_used": 300,
    "test_date": "2025-02-03T00:00:00+00:00",
    "created_at": "2025-02-03T17:22:15.813949+00:00",
    "updated_at": "2025-02-03T17:22:15.813949+00:00"
  }
]
```

### POST `/profile/performance`

Creates a new performance record. Use this when you need to retain historical snapshots (e.g., multiple lab tests). If you only need a single active record, prefer the `PUT` endpoint below.

- Fields not included are left `null`.
- When `*_zones_source` is `"auto"` or omitted, the backend recalculates the relevant zones based on supplied thresholds.
- If `hr_zones_source` is `"manual"`, the zones provided are stored as-is.

Example: save an automatically calculated HR profile with manual pace zones.

```http
POST /profile/performance
Authorization: Bearer <token>

{
  "test_date": "2025-01-31",
  "hr_max": 190,
  "hr_rest": 50,
  "threshold_hr": 170,
  "pace_zones": {
    "z1": "5:20-5:00",
    "z2": "5:00-4:45",
    "z3": "4:45-4:25",
    "z4": "4:25-4:10",
    "z5": "4:10-3:55"
  },
  "pace_zones_source": "manual"
}
```

### PUT `/profile/performance`

Upserts the “current” performance metrics for a user:

- If a record exists, it updates the latest by `test_date`; otherwise it creates a new one.
- Auto zone recalculation rules match the `POST` endpoint.
- `hrr` and `wkg` are recomputed whenever inputs change.
- Useful for “Save” actions from the settings screen where only the newest record matters.

Example with full payload (auto zones everywhere):

```http
PUT /profile/performance
Authorization: Bearer <token>

{
  "test_date": "2025-02-03",
  "hr_max": 190,
  "hr_rest": 50,
  "threshold_hr": 170,
  "threshold_pace": "4:15",
  "ftp": 300,
  "vo2max": 55,
  "hr_zones_source": "auto",
  "pace_zones_source": "auto",
  "power_zones_source": "auto"
}
```

Example switching to manual HR zones while keeping auto power zones:

```http
PUT /profile/performance
Authorization: Bearer <token>

{
  "hr_zones": {
    "z1": "115-130",
    "z2": "130-145",
    "z3": "145-160",
    "z4": "160-175",
    "z5": "175-190"
  },
  "hr_zones_source": "manual",
  "power_zones_source": "auto",
  "ftp": 310
}
```

### PUT `/profile/zone-preference`

Updates the user’s preferred zone type and returns the structured zones for the latest performance record if available.

```http
PUT /profile/zone-preference
Authorization: Bearer <token>

{
  "preferred_zone_type": "power"
}
```

Sample response:

```json
{
  "success": true,
  "preferred_zone_type": "power",
  "zones_calculated": true,
  "current_zones": {
    "z1": {"min": 0.0, "max": 165.0, "description": "Recovery"},
    "z2": {"min": 165.0, "max": 225.0, "description": "Aerobic Base"},
    "z3": {"min": 225.0, "max": 270.0, "description": "Aerobic Threshold"},
    "z4": {"min": 270.0, "max": 315.0, "description": "Lactate Threshold"},
    "z5": {"min": 315.0, "max": 360.0, "description": "VO2 Max"},
    "z6": {"min": 360.0, "max": 450.0},
    "z7": {"min": 450.0, "max": 540.0}
  }
}
```

> Note: `current_zones` is derived by converting the stored strings to numeric min/max ranges for convenience.

## Zone Formats & Validation Rules

- `threshold_pace` must match `^\d{1,2}[:.]\d{2}$` and seconds must be 0–59.
- Zone ranges:
  - HR/Power: `"min-max"` using integers.
  - Pace: `"mm:ss-mm:ss"` (descending pace, e.g., faster pace on the right).
- `*_zones_source` must be `"auto"` or `"manual"`. When omitted, `"auto"` behaviour kicks in if the required threshold is present; otherwise existing zones remain unchanged.
- `ftp`, `threshold_hr`, `hr_max`, `hr_rest` must be positive values within sensible bounds (enforced at schema level).
- To trigger `wkg` calculation, ensure the profile has `weight` set before sending FTP data.

## Typical Frontend Flows

1. **Initial load**
   - `GET /profile` to render athlete data and preferred zone type.
   - `GET /profile/performance` to fetch the latest metrics (use the first element of the list).

2. **Save changes with auto zones**
   - Build a payload with thresholds and set `*_zones_source` to `"auto"`.
   - Send `PUT /profile/performance`.
   - Optionally call `PUT /profile/zone-preference` to track the active view.

3. **Manual overrides**
   - Present editable zone fields in `"min-max"` format.
   - Set the relevant `*_zones_source` to `"manual"` to prevent recalculation.

## Notes & Compatibility

- Legacy fields (`metric_type`, `threshold_value`, `max_value`, `rest_value`, `zones_json`) have been removed by migrations `ad1103fc82e7` and `e54decaaad15`. Use only the structures described above.
- There is currently no standalone `/profile/zones` endpoint; all zone information is managed through the performance endpoints and the zone preference helper.
- Errors follow FastAPI defaults (`422` validation errors for bad payloads, `404` when the profile is missing, `400` for duplicate profile creation).


