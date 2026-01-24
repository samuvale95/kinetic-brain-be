# Query Optimization Audit

## Summary

This document summarizes the query optimization audit performed as part of production readiness improvements.

## Current State

### ✅ Already Optimized

1. **Calendar API** (`app/api/calendar.py`)
   - Uses `joinedload(Workout.strava_activity)` to prevent N+1 queries
   - Multiple endpoints properly eager load relationships

2. **Dashboard API** (`app/api/dashboard.py`)
   - Uses `joinedload(Workout.strava_activity)` for workout queries
   - Properly loads relationships before accessing them

### ⚠️ Areas for Improvement

1. **Workout Service** (`app/services/workout_service.py`)
   - Review methods that return lists of workouts
   - Consider adding eager loading for `workout_plan` relationship when needed
   - Check methods that access `workout_sessions` relationship

2. **Statistics API** (`app/api/statistics.py`)
   - Review aggregation queries for potential optimization
   - Consider adding indexes on frequently queried columns

3. **Profile Service** (`app/services/profile_service.py`)
   - Review user profile queries
   - Check for N+1 when loading related data (zones, metrics, etc.)

## Recommendations

### 1. Add Eager Loading Where Missing

Use `joinedload` or `selectinload` for relationships that are accessed after query:

```python
from sqlalchemy.orm import joinedload, selectinload

# For one-to-many relationships
query = db.query(WorkoutPlan).options(
    selectinload(WorkoutPlan.workouts)
).filter(...)

# For many-to-one relationships
query = db.query(Workout).options(
    joinedload(Workout.workout_plan)
).filter(...)
```

### 2. Add Database Indexes

Consider adding indexes on frequently queried columns:

```sql
-- Example indexes to consider
CREATE INDEX idx_workout_user_scheduled ON workouts(user_id, scheduled_date);
CREATE INDEX idx_workout_session_workout ON workout_sessions(workout_id);
CREATE INDEX idx_calendar_event_user_date ON calendar_events(user_id, event_date);
```

### 3. Use Pagination for Large Result Sets

For endpoints that return lists, implement pagination:

```python
from fastapi import Query

@router.get("/workouts")
async def get_workouts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    workouts = db.query(Workout).offset(skip).limit(limit).all()
    return workouts
```

### 4. Cache Frequently Accessed Data

Use the Redis cache utility for:
- User profiles (TTL: 5 minutes)
- Performance metrics (TTL: 10 minutes)
- Dashboard statistics (TTL: 5 minutes)

Example:
```python
from app.utils.cache import cache_result

@cache_result(ttl=300, prefix="user_profile")
def get_user_profile(user_id: int):
    return db.query(User).filter(User.id == user_id).first()
```

### 5. Optimize Aggregation Queries

For statistics and dashboard endpoints:
- Use database-level aggregations instead of Python loops
- Consider materialized views for complex aggregations
- Cache results with appropriate TTL

## Implementation Priority

1. **High Priority**: Add eager loading to workout service methods that return lists
2. **High Priority**: Add pagination to list endpoints
3. **Medium Priority**: Add database indexes
4. **Medium Priority**: Implement caching for profile and metrics
5. **Low Priority**: Optimize aggregation queries

## Monitoring

After implementing optimizations:
- Monitor query performance using Prometheus metrics
- Review slow query logs
- Use database query analyzers to identify bottlenecks

## Notes

- The codebase already has good practices in place (eager loading in calendar/dashboard)
- Focus optimization efforts on high-traffic endpoints
- Test performance improvements with realistic data volumes
