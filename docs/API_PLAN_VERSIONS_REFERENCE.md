## Plan Versions API Reference

### Purpose
Stores immutable snapshots each time a training plan is generated. Useful for audit trails, rollbacks, or comparing iterations.

### Database
- Table: `plan_versions`
- Columns (key fields):
  - `user_id` → owner (CASCADE on delete)
  - `plan_id` → optional link to a persisted `workout_plans` entry
  - `plan_payload` → JSON blob of generated plan
  - `validator_violations` → JSON array of rules violated (reserved)
  - `created_at` → timestamp

### Schema classes
Defined in `app/schemas/plan_version.py`:
- `PlanVersionSummary` – metadata for listings.
- `PlanVersionDetail` – includes `plan_payload` and validator context.
- `PlanVersionListResponse` – wrapper with paging metadata.

### Service layer
`app/services/plan_version_service.py`
- `list_versions(user_id, plan_id=None, limit=20, offset=0)` – returns (items, total) ordered by `created_at` DESC.
- `get_version(user_id, version_id)` – fetch single snapshot scoped to user.

### Routes
File: `app/api/plan_versions.py`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/plans/versions/` | Paginated list of plan versions for the authenticated user. Optional `plan_id`, `limit`, `offset`. |
| GET | `/plans/versions/{version_id}` | Retrieve a specific version (404 if not owned). |

Additions registered in `app/main.py` via `app.include_router(plan_versions.router)`.

### Tests
- `tests/test_plan_version_api.py` – verifies list + detail endpoints and ordering.
- `tests/test_plan_version_storage.py` – ensures generation stores versions (mock mode).
- `tests/test_plan_duration_limit.py` – related safety check for max duration.

### Configuration
- `MAX_PLAN_DURATION_WEEKS` env var controls upper bound before plan generation is rejected (`app/config.py`).

### Extensibility
- `PlanVersion` table includes optional `version_label`/`description` for future manual tagging.
- Attach additional metadata (e.g., plan hash, training block) by extending the model and schemas.

