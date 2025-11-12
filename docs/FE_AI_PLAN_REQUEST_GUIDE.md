# Frontend Guide – AI Plan Generation Request

## Overview
The endpoint `POST /ai/generate-plan` now accepts additional race metadata so the AI can tailor training plans toward a specific event. This guide explains how to shape the request payload and when each field is required.

## Endpoint
- **URL**: `/ai/generate-plan`
- **Method**: `POST`
- **Auth**: Bearer token (same as altre rotte protette)
- **Success response**: `{ "plan": { ... } }`
- **Error response**: `{"detail": "...", "violations": [...]}` per violazioni del validator (status `500`)

## Request Schema
```json
{
  "sport_type": "running",
  "level": "intermediate",
  "goal": "Migliorare il tempo sulla mezza maratona",
  "duration_weeks": 16,
  "start_date": "2025-01-06",
  "target_date": "2025-05-04",
  "weekly_hours": 6.5,
  "user_profile": { "...": "..." },
  "preferences": { "...": "..." },
  "race_distance_km": 21.097,
  "race_type": null
}
```

### Core Fields (unchanged)
- `sport_type` (`string`, required): e.g. `"running"`, `"trail"`, `"triathlon"`, `"cycling"`.
- `level` (`string`, required): `"beginner" | "intermediate" | "advanced"`.
- `goal` (`string`, required): free text goal (<= 200 char).
- `duration_weeks` (`int`, optional): 1–52; required if `start_date`/`target_date` missing.
- `start_date` / `target_date` (`YYYY-MM-DD`, optional): define plan window; at least one of `duration_weeks` or date range must be provided.
- `weekly_hours` (`float`, optional): indicative availability >0 and ≤168.
- `user_profile` (`object`, optional): training metrics, thresholds, injuries etc. (no schema changes).
- `preferences` (`object`, optional): training-day preferences, equipment constraints, etc. (unchanged).

### New Race Fields
| Field | Type | When to use | Notes |
|-------|------|-------------|-------|
| `race_distance_km` | `float` (>0) | **Running/Trail plans** when goal is a race | Examples: `5`, `10`, `21.097`, `42.195`, `120`. Ignored for non running/trail sports. |
| `race_type` | `string` | **Triathlon plans** with race goal | Allowed values: `"sprint"`, `"olympic"`, `"half_ironman"`, `"ironman"`. Ignored for other sports. |

Validation rules (enforced server-side):
- If `race_type` is provided for a non-triathlon `sport_type`, the API rejects the request.
- If `race_distance_km` is provided for non running/trail sports, the API rejects the request.
- Fields are optional if the plan is not race-focused (e.g., generic base building).

## Frontend Requirements
1. **Form updates**
   - When the user selects a race-oriented training type:
     - If sport is running or trail, capture numeric distance in km (allow decimal input).
     - If sport is triathlon, expose a dropdown with the allowed race types.
   - Send these values in the request payload alongside existing fields.

2. **Validation UX**
   - Ensure UI only shows inputs relevant to the selected sport.
   - Client-side validation: distance must be >0; race type must match the enum list.
   - Optional: auto-set `goal` text based on race selection to guide user copy.

3. **API call example (TypeScript)**
   ```ts
   type RaceType = "sprint" | "olympic" | "half_ironman" | "ironman";

   interface GeneratePlanPayload {
     sport_type: string;
     level: "beginner" | "intermediate" | "advanced";
     goal: string;
     duration_weeks?: number;
     start_date?: string;
     target_date?: string;
     weekly_hours?: number;
     user_profile?: Record<string, unknown>;
     preferences?: Record<string, unknown>;
     race_distance_km?: number;
     race_type?: RaceType;
   }

   async function generatePlan(payload: GeneratePlanPayload) {
     const response = await fetch("/ai/generate-plan", {
       method: "POST",
       headers: {
         "Content-Type": "application/json",
         Authorization: `Bearer ${authToken}`,
       },
       body: JSON.stringify(payload),
     });
     if (!response.ok) throw new Error("Plan generation failed");
     return response.json();
   }
   ```

4. **Error handling**
   - Backend returns 422 if validation fails (e.g., race_type with sport ≠ triathlon). Surface error to the user.
   - For 500 errors, show a generic retry message.

5. **Testing Checklist**
   - [ ] Running plan with `race_distance_km` sent; response includes tailored messaging.
   - [ ] Trail plan with ultra distance; ensure no validation errors.
   - [ ] Triathlon plan with each race type.
   - [ ] Non-race plan (fields omitted) still succeeds.
   - [ ] UI prevents invalid combinations (e.g., race type set while sport is cycling).

## Notes
- Backend prompt already incorporates the extra race data to guide the LLM.
- Mock mode echoes the new fields in logs and sample plan metadata; use it to verify end-to-end integration without consuming tokens.
- No changes are required for plan ingestion endpoints; structured workouts are delivered as before.

## Response Examples

### Success
```json
{
  "plan": {
    "title": "Running Training Plan - Intermediate",
    "description": "16-week progression toward a half marathon PB.",
    "sport_type": "running",
    "level": "intermediate",
    "goal": "PB Half Marathon (21.097 km)",
    "duration_weeks": 16,
    "weekly_hours": 6.5,
    "start_date": "2025-01-06",
    "end_date": "2025-05-04",
    "phases": [
      {"name": "Base", "weeks": "1-4"},
      {"name": "Build", "weeks": "5-10"},
      {"name": "Peak", "weeks": "11-14"},
      {"name": "Taper", "weeks": "15-16"}
    ],
    "weeks": [
      {
        "week": 1,
        "focus": "Aerobic base + drills",
        "workouts": [
          {
            "day": "Monday",
            "type": "Endurance",
            "sport": "run",
            "duration_minutes": 55,
            "intensity": "Z2",
            "rpe_target": 4,
            "structure": {
              "sport": "run",
              "segments": [
                {"segment_type": "warmup", "steps": [...]},
                {"segment_type": "main", "steps": [...]},
                {"segment_type": "cooldown", "steps": [...]}
              ],
              "metadata": {
                "focus": "Easy aerobic volume, cadence drills",
                "rpe_target": 4
              }
            }
          },
          "... other workouts ..."
        ]
      },
      "... weeks 2-16 ..."
    ]
  }
}
```

### Validation failure (readiness / injury risk)
Il validator ora usa i dati più recenti di readiness (`daily_readiness_metrics`) e carico settimanale (`weekly_training_summaries`). Se l’atleta risulta non pronto, il piano viene bloccato:

```json
{
  "detail": "AI plan generation error: Plan validation failed",
  "violations": [
    "Athlete readiness state requires rest before new plan",
    "Athlete injury risk score 1.72 exceeds safe threshold 1.50"
  ]
}
```

### Validation failure (schema)
Restano valide le regole precedenti (es. combinazioni di sport e campi gara non consentite):

```json
{
  "detail": "AI plan generation error: sport_type 'cycling' does not accept race_type",
  "violations": [
    "sport_type 'cycling' does not accept race_type"
  ]
}
```

In tutti i casi di errore, il frontend deve intercettare la risposta `500`, mostrare il messaggio principale (`detail`) e, quando presenti, le singole violazioni per aiutare l’utente a capire cosa correggere.


