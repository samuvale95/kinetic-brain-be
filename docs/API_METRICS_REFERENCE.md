## Metrics API Reference

This document describes the backend architecture powering `/metrics/load` and `/metrics/readiness`.

### Service stack
- `MetricsApiService` (new):
  - `get_load_series(...)` → returns list of period dictionaries with aggregated training load.
  - `get_readiness_series(...)` → returns readiness/recovery indicators per period.
  - Accepts `GroupingGranularity` enum (`day`, `week`, `month`, `year`). Additional granularities can be plugged in by extending `_generate_periods`.
- Data sources:
  - `StravaActivity` (raw sessions, including time in zones).
  - `DailyPerformanceMetrics` (daily CTL/ATL/TSB).
  - `DailyReadinessMetrics` (HRV/RHR/sleep/hydration).
  - `WeeklyTrainingSummary` (compliance, injury risk, sport breakdown).

### Aggregation logic
| Grouping | Load strategy | Readiness strategy | Notes |
|----------|---------------|--------------------|-------|
| `day` | Aggregate raw Strava activities + daily CTL/ATL/TSB | Direct rows from `daily_readiness_metrics` | `plan_adherence` not populated |
| `week` | Use `weekly_training_summaries` (one row per week) | Average of daily records + weekly injury risk | Highest fidelity (compliance, progression) |
| `month` | Summation over activities; compliance averaged from underlying weekly summaries | Average daily readiness; injury risk averaged across overlapping weeks | Does not require precomputed monthly table |
| `year` | Same as month, but buckets per calendar year | Same as month | Handles cross-year ranges |

### Serialization
- Responses are validated against `LoadMetricsResponse` and `ReadinessMetricsResponse` (`app/schemas/metrics.py`).
- Dates are returned as ISO-8601 strings by FastAPI (Pydantic handles conversion).
- All numeric fields are optional (`null`) when data is missing.

### New modules
| File | Description |
|------|-------------|
| `app/services/metrics_api_service.py` | Aggregation service (grouping, averaging, breakdown) |
| `app/api/metrics.py` | FastAPI router exposing `/metrics/load` and `/metrics/readiness` |
| `app/schemas/metrics.py` | Pydantic schemas for grouping enum, metadata, series points |

### FastAPI routes
| Method | Path | Query params | Response |
|--------|------|--------------|----------|
| `GET` | `/metrics/load` | `start_date`, `end_date`, `grouping`, `sport` | `LoadMetricsResponse` |
| `GET` | `/metrics/readiness` | `start_date`, `end_date`, `grouping` | `ReadinessMetricsResponse` |

All routes require bearer authentication (`Authorization: Bearer <token>`).

### Extending grouping
To add a new granularity (e.g. quarter):
1. Add enum entry in `GroupingGranularity`.
2. Update `_generate_periods` to compute bucket boundaries.
3. (Optional) adjust aggregation helpers if quarter-specific logic is needed.
4. No Pydantic or response changes required—`period_start` / `period_end` handle any ranges.

### Fallback behaviour
- When no data exists for a period, the service returns `null` values but preserves the bucket to keep charts aligned.
- `sport` filter (`/metrics/load`) defaults to `all`; pass `sport=run`/`cycling`/`swim` to narrow breakdown.
- Compliance fields (`compliance_score`, `plan_adherence`) are only populated for buckets derived from weekly summaries.

### Testing
- `tests/test_metrics_api.py` covers:
  - `/metrics/load` weekly grouping (ensures compliance fields are returned).
  - `/metrics/readiness` daily grouping (readiness state preserved day-by-day).
  - Access token creation via `AuthService` to authenticate requests during testing.

### Versioning
- API version is implicitly tied to backend release. When introducing breaking changes, bump the contract and update this reference.

