# Integrazione Metriche di Performance - Frontend

Questo documento descrive come il frontend deve inviare le metriche di performance nell'endpoint di generazione dei piani di allenamento.

## Endpoint

**POST** `/workouts/plans/generate-ai`

## Schema Request

La request deve seguire lo schema `AIWorkoutPlanRequest`:

```typescript
interface AIWorkoutPlanRequest {
  sport_type: string;
  level: string;
  goal: string;
  weekly_hours?: number;
  user_profile?: { ... };
  preferences?: { ... };
  duration_weeks?: number;
  is_progressive?: boolean;
  target_date?: string;
  start_date?: string;
}
```

... (contenuti invariati dal file originale)


