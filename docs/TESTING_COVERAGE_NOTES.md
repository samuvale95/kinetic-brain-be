# Testing Coverage Notes

## Current Status

Testing infrastructure is in place with pytest and pytest-cov configured in `requirements.txt`.

## Running Coverage Report

To generate a coverage report:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests with coverage
pytest --cov=app --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html
```

## Coverage Target

Target coverage: **≥80%**

## Areas Requiring Test Coverage

### High Priority (Critical Endpoints)

1. **Authentication** (`app/api/auth.py`)
   - Login/register endpoints
   - Token refresh
   - Password reset flow

2. **Workout Generation** (`app/api/workouts.py`)
   - AI workout plan generation
   - Progressive plan generation
   - Plan updates and deletions

3. **Error Handling** (`app/exceptions.py`)
   - Custom exception classes
   - Exception handler responses
   - Error code validation

### Medium Priority

4. **Rate Limiting** (`app/middleware/rate_limit_middleware.py`)
   - Rate limit enforcement
   - Redis fallback behavior
   - Per-user vs per-IP limits

5. **Caching** (`app/utils/cache.py`)
   - Cache hit/miss behavior
   - TTL expiration
   - Cache invalidation

6. **Health Check** (`app/main.py`)
   - Service health verification
   - Degraded state handling

### Low Priority

7. **Backup Scripts** (`scripts/backup_database.py`, `scripts/restore_database.py`)
   - Backup creation
   - Restore functionality
   - Retention policy

## Test Structure Recommendations

```
tests/
├── conftest.py          # Shared fixtures
├── test_auth.py         # Authentication tests
├── test_workouts.py     # Workout endpoint tests
├── test_exceptions.py   # Error handling tests
├── test_rate_limiting.py
├── test_cache.py
└── test_health.py
```

## CI/CD Integration

Add coverage check to CI pipeline:

```yaml
# Example GitHub Actions
- name: Run tests with coverage
  run: |
    pytest --cov=app --cov-report=xml --cov-report=term
    coverage report --fail-under=80
```

## Notes

- Focus on critical business logic first
- Use fixtures for database setup/teardown
- Mock external services (OpenAI, Strava, etc.)
- Test error cases, not just happy paths
