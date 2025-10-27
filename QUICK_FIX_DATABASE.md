# Quick Database Fix - Run This First!

## 🚨 IMPORTANT: Database Migration Required

You need to run these SQL migrations to fix the errors:

```bash
# Make sure your .env has DATABASE_URL set
source .env

# Run the migrations
psql "$DATABASE_URL" -f database/add_zone_preference_to_profiles.sql
psql "$DATABASE_URL" -f database/add_metrics_fields_to_strava_activities.sql
```

Or if you want to create all the new tables:

```bash
psql "$DATABASE_URL" -f database/create_training_metrics_table.sql
psql "$DATABASE_URL" -f database/create_weekly_summary_table.sql
psql "$DATABASE_URL" -f database/add_zone_preference_to_profiles.sql
psql "$DATABASE_URL" -f database/add_metrics_fields_to_strava_activities.sql
```

## Errors Fixed

1. ✅ Fixed `statistics_service.py` - Method `_get_strava_accounts` → `_get_strava_account_ids`
2. ✅ Recreated `statistics_service.py` with proper error handling
3. ❌ Need to run database migration for `preferred_zone_type` column

## After Running Migrations

1. Restart the server:
```bash
./stop.sh
./start.sh
```

2. Test the endpoints:
```bash
# This should work now
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/statistics/overview
```

## Files Updated

- ✅ `app/services/statistics_service.py` - Fixed
- ⏳ Database migration - Needs to be run (see above)

