# Frontend Guide – Structured Workouts

## Why this change?
- `structure_json` now provides full workout choreography (segments/steps/targets) instead of a plain description.
- The payload is validated server-side, so the frontend can rely on a consistent schema for rendering, editing, and exporting (e.g., Garmin/FIT).
- Zones are sport-aware: running/trail use `Z1–Z5`; cycling uses `Z1–Z7`.

## Where to expect it
- `GET /workouts/plans/:id` (`WorkoutPlanDetail`): every workout includes `structure_json`.
- `GET /workouts/:id` (`WorkoutDetail`): same structure.
- Any future AI-generated plan will fill `structure_json`; the text `description` remains for legacy display but should be treated as fallback only.

## Schema Recap

```json
{
  "sport": "run",
  "segments": [
    {
      "segment_type": "warmup",
      "name": "Warm-up",
      "steps": [
        {
          "step_type": "steady",
          "duration": {"type": "time", "seconds": 600},
          "target": {"type": "zone", "zone": "Z2"},
          "notes": "Easy jog"
        }
      ]
    },
    {
      "segment_type": "main",
      "name": "Intervals",
      "steps": [
        {
          "step_type": "repeat",
          "repeat": 6,
          "steps": [
            {
              "step_type": "interval",
              "duration": {"type": "time", "seconds": 120},
              "target": {"type": "zone", "zone": "Z4"},
              "notes": "Uphill sprint"
            },
            {
              "step_type": "recovery",
              "duration": {"type": "time", "seconds": 120},
              "target": {"type": "zone", "zone": "Z2"},
              "notes": "Jog back down"
            }
          ]
        }
      ]
    },
    {
      "segment_type": "cooldown",
      "steps": [
        {
          "step_type": "steady",
          "duration": {"type": "time", "seconds": 600},
          "target": {"type": "zone", "zone": "Z1"},
          "notes": "Relaxed finish"
        }
      ]
    }
  ],
  "metadata": {
    "focus": "Base building with speed introduction",
    "rpe_target": 8,
    "description": "Maintain smooth form through the repeats"
  },
  "equipment": ["treadmill", "tempo shoes"]
}
```

### Field Tips
- `segments`: render sequentially; expect at least one `main` segment, plus optional `warmup`, `cooldown`, `brick`, `technique`, `optional`.
- `step_type`
  - `steady`, `interval`, `recovery`, `rest`, `drill`, `technique`, `strength` → single effort (always has `duration`).
  - `repeat` → nested `steps` array + `repeat` count.
- `duration`
  - `{type: "time", seconds}` → convert to `mm:ss`.
  - `{type: "distance", meters}` → convert to km/miles.
  - `{type: "repetitions", repetitions}` → show `x reps`; nested steps likely specify per-rep details.
- `target`
  - `zone` → show zone badge (respect allowed ranges per sport).
  - `heart_rate`, `power`, `pace`, `cadence`, `rpe` → show ranges + units (included in `units` when applicable).
  - `notes` can highlight cues (e.g., “keep cadence high”).

## UX Checklist
1. **Segment Rendering**
   - Display segment title (`name` fallback to capitalized `segment_type`).
   - Provide visual separators between segments (cards or accordions).

2. **Repeat Blocks**
   - Show `repeat` count (e.g., “x6”).
   - Render nested steps inside a sub-list; indentation or nested cards works well.
   - Duration for repeats can be shown as per-rep + total (repeat × sum of sub-steps).

3. **Duration Formatting**
   ```ts
   function formatDuration(duration) {
     if (duration.type === "time") return formatSeconds(duration.seconds);
     if (duration.type === "distance") return formatDistance(duration.meters);
     if (duration.type === "repetitions") return `${duration.repetitions} reps`;
   }
   ```

4. **Targets**
   - Zones: highlight with color-coded chips.
   - Numeric ranges: handle `min_value`, `max_value`. If one side is missing, treat as `≥` or `≤`.
   - Units: fallback to defaults (`bpm`, `W`, `min/km`, `rpm`) if `units` missing.

5. **Metadata & Notes**
   - Display `metadata.focus` and `metadata.rpe_target` at workout header.
   - Show `metadata.description` as “Coach notes”.
   - Step-level `notes` should be visible (e.g., tooltip or sub-caption).

6. **Legacy Fallback**
   - If `structure_json` is `null`, keep current text description rendering (legacy workouts). Documented migration should gradually eliminate these cases.

## Editing / Export Considerations
- When building an editor, follow the same schema contract so updates can be PUT back unchanged.
- To export to Garmin/others, map:
  - Segment/step structure → warmup/main/cooldown steps.
  - Zones → device-specific range (use user profile thresholds if available).
  - Repeats → nested loops.

## Testing Plan for FE
- [ ] Load a running plan, ensure segments and steps display correctly.
- [ ] Load a cycling plan with `Z6/Z7` targets to confirm zone validation UI.
- [ ] Verify repeat blocks render nested steps and totals.
- [ ] Confirm fallback UI appears for legacy workouts (no structure).
- [ ] Check accessibility: ensure nested lists are keyboard-navigable.
- [ ] Validate export logic by logging transformed payload (mock Garmin export).

## API Reminder
- All responses already validated: if `structure_json` exists, the schema is guaranteed to be consistent.
- Consume `structure_json` verbatim; avoid mutating fields (keep `sport` lowercase).
- For filters: `workout.zone` remains a quick summary zone, but per-step targets may include finer detail—prefer the structured targets for accuracy.

## Support
- Backend schema definitions live in `app/schemas/workout.py`.
- Reach out in `#training-platform` for clarifications or if you hit legacy payloads that slip through validation.


