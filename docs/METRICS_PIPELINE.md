## Advanced Metrics Pipeline

### Overview
- Tracks daily readiness (`daily_readiness_metrics`) and weekly training summaries (`weekly_training_summaries`) derived from Strava activities, workout plans, and user feedback.
- Jobs are enqueued in `metrics_pending_jobs` and processed cooperatively within request flows (Strava sync, daily metrics updates, plan generation).
- All calculations are resilient to missing inputs; nullable fields remain empty if telemetry is unavailable.

### Daily Readiness Metrics
- Source: `AdvancedMetricsService.compute_and_store_daily_readiness`.
- Triggered after daily performance metrics update or when new data is provided.
- Inputs considered (when available): HRV, RHR, sleep, EPOC, CTL/ATL/TSB, hydration/nutrition markers.
- Outputs:
  - `recovery_index` (normalized readiness score)
  - `readiness_state` (`ready`, `caution`, `rest`)
  - Hydration/nutrition scores and deltas vs. baselines

### Weekly Training Summary
- Source: `AdvancedMetricsService.compute_and_store_weekly_summary`.
- Triggered after activity syncs or plan generation.
- Aggregates per-week:
  - Total duration, distance, TSS, multi-sport load
  - Sport-specific breakdown, zone distribution, high-intensity ratio
  - Longest workout metrics and progression percentages
  - Compliance score (planned vs. completed sessions)
  - Injury risk score and hydration summary

### Cooperative Job Processing
- New jobs are inserted into `metrics_pending_jobs` via orchestrator helpers:
  - `enqueue_daily_readiness_job`
  - `enqueue_weekly_summary_job`
- `process_metrics_jobs` consumes pending jobs at the end of API requests, avoiding dedicated worker infrastructure.
- Failed jobs back-off for 5 minutes and retain the last error message.

### Validator Integration
- `WorkoutPlanValidator` now accepts an optional `user_state` payload with readiness, recovery, hydration, and injury-risk scores.
- Plans are rejected when:
  - Readiness state is `rest` (insufficient recovery).
  - Recovery index drops below 0.6 while in caution.
  - Injury risk score exceeds 1.50.
  - Hydration score is critically low (<0.4).

### Key Tables
- `daily_readiness_metrics`: per-day readiness signals.
- `weekly_training_summaries`: aggregated weekly load and risk indicators.
- `metrics_pending_jobs`: cooperative queue for metric recalculations.

### Safety Notes
- Missing data never blocks calculations; metrics remain `NULL` until real telemetry arrives.
- All updates log successes and exceptions via Loguru for later debugging.

