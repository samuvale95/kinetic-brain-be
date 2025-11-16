## Metrics API – Frontend Integration Guide

Two new authenticated endpoints expose training load and readiness metrics with flexible grouping (`day`, `week`, `month`, `year`). Use them for dashboard widgets, charts, and analytics.

### Common parameters
| Query param | Type | Default | Notes |
|-------------|------|---------|-------|
| `start_date` | `YYYY-MM-DD` | 27 days ago | Inclusive range start |
| `end_date` | `YYYY-MM-DD` | today | Inclusive range end |
| `grouping` | `day\|week\|month\|year` | varies per endpoint | Controls aggregation granularity |
| `sport` | `string` (optional) | `all` | Only for `/metrics/load`; values e.g. `run`, `cycling`, `swim` |

Include bearer token (`Authorization: Bearer <access_token>`) like other protected routes.

---

### GET `/metrics/load`
Aggregated training load for the requested period.

**Example**
```
GET /metrics/load?start_date=2025-01-01&end_date=2025-03-31&grouping=week&sport=run
Authorization: Bearer <token>
```

**Response**
```json
{
  "metadata": {
    "grouping": "week",
    "start_date": "2025-01-01",
    "end_date": "2025-03-31",
    "sport": "run"
  },
  "series": [
    {
      "period_start": "2025-01-06",
      "period_end": "2025-01-12",
      "total_duration_minutes": 360.0,
      "total_distance_km": 72.0,
      "total_tss": 420.0,
      "multi_sport_load": 420.0,
      "ct_load": 78.1,
      "acute_load": 83.5,
      "training_stress_balance": -5.4,
      "sport_breakdown": {
        "running": {
          "sessions": 5,
          "duration_minutes": 360.0,
          "distance_km": 72.0,
          "tss": 420.0,
          "max_duration_minutes": 120.0,
          "max_distance_km": 26.0
        }
      },
      "high_intensity_ratio": 0.18,
      "high_intensity_sessions": 2,
      "long_workout": {
        "duration_minutes": 120.0,
        "distance_km": 26.0,
        "progression_pct": 8.4
      },
      "compliance_score": 0.86,
      "plan_adherence": {
        "planned": 6,
        "completed_sessions": 5,
        "scheduled_completed": 5,
        "scheduled_skipped": 1
      }
    }
  ]
}
```

**Front-end usage**
- Use `series[*].period_start` / `period_end` as x-axis.
- Combine `total_tss` or `multi_sport_load` for bar charts.
- Feed `sport_breakdown` to stacked charts (per sport).
- Show compliance widget from `compliance_score` and `plan_adherence`.
- For `grouping=day`, `compliance_score`/`plan_adherence` are usually `null`.
- For `grouping=month|year`, multiple weekly summaries are aggregated (sums for duration/distance/TSS, average for compliance/high_intensity_ratio).

---

### GET `/metrics/readiness`
Daily or aggregated readiness & recovery metrics.

**Example**
```
GET /metrics/readiness?start_date=2025-02-01&end_date=2025-02-28&grouping=day
Authorization: Bearer <token>
```

**Response**
```json
{
  "metadata": {
    "grouping": "day",
    "start_date": "2025-02-01",
    "end_date": "2025-02-28"
  },
  "series": [
    {
      "period_start": "2025-02-03",
      "period_end": "2025-02-03",
      "recovery_index": 1.02,
      "readiness_state": "ready",
      "hydration_score": 0.75,
      "nutrition_score": 0.8,
      "hrv": {
        "baseline": 72.0,
        "value": 74.5,
        "delta": 2.5
      },
      "rhr": {
        "baseline": 50.0,
        "value": 48.0,
        "delta": -2.0
      },
      "sleep_hours": 7.2,
      "sleep_quality_score": 0.82,
      "epoc": 18.0,
      "injury_risk_score": 0.58
    }
  ]
}
```

**Notes**
- `grouping=day`: direct values from `daily_readiness_metrics`.
- `grouping=week|month|year`: averages over the days in the bucket; `injury_risk_score` pulled from weekly summaries (mean of overlapping weeks).
- Use `readiness_state` to color code cards (`ready`, `caution`, `rest`).
- Chart HRV/RHR trends via `hrv.value`, `rhr.value`; highlight deltas.

---

### POST `/metrics/diary`
Crea/aggiorna la voce di diario giornaliera (readiness) e calcola l'indice di recupero.

Body (qualsiasi campo è opzionale; `date` default oggi):
```json
{
  "date": "2025-02-03",
  "hrv_value": 74.5,
  "rhr_value": 48,
  "sleep_hours": 7.2,
  "sleep_quality_score": 0.82,
  "epoc": 18,
  "hydration_status": "ok",
  "hydration_score": 0.75,
  "nutrition_score": 0.8,
  "weight_delta_kg": -0.2,
  "perceived_exertion": 6,
  "notes": "Leggera corsa serale"
}
```

Response:
```json
{
  "success": true,
  "date": "2025-02-03",
  "readiness_state": "ready",
  "recovery_index": 1.02
}
```

---

### POST `/metrics/recompute-today`
Enqueue non bloccante del calcolo CTL/ATL/TSB per oggi (o per la data indicata).

Query opzionale:
- `target_date=YYYY-MM-DD` (default: oggi)

Response:
```json
{
  "success": true,
  "job_id": 123,
  "job_type": "daily_performance",
  "status": "pending",
  "metric_date": "2025-02-03"
}
```

---

### Lazy compute (non bloccante)
- Alla prima chiamata a `GET /metrics/load` o `GET /metrics/readiness` della giornata, se non esiste un record `daily_performance_metrics` per oggi, il backend crea automaticamente un job `daily_performance` e restituisce subito la risposta (senza attendere il calcolo).
- Il frontend può:
  - riprovare dopo pochi secondi (polling), oppure
  - chiamare esplicitamente `POST /metrics/recompute-today` e osservare lo stato del job in UI.

---

### Handling grouping extensibility
The backend accepts additional grouping enum values transparently:
- existing responses always include `period_start` / `period_end` → charts can plot any granularity.
- when new grouping is introduced (e.g. `quarter`), only update filters/enum on the client; response schema stays identical.

---

### Error handling
- Validation errors (invalid grouping, `start_date > end_date`) return `400` with detail message.
- Auth errors result in `401`.
- Unexpected issues return `500`.

Always surface backend messages to help the athlete fix filters quickly.

