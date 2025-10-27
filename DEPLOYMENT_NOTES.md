# Deployment Notes - Advanced Training Metrics

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies added:
- `stravalib>=1.0.0` - For metrics calculations
- `numpy>=1.24.0` - For mathematical operations

### 2. Run Database Migrations

Execute the SQL scripts in order:

```bash
psql "$DATABASE_URL" -f database/create_training_metrics_table.sql
psql "$DATABASE_URL" -f database/create_weekly_summary_table.sql
psql "$DATABASE_URL" -f database/add_zone_preference_to_profiles.sql
psql "$DATABASE_URL" -f database/add_metrics_fields_to_strava_activities.sql
```

Or use the setup script:

```bash
./setup_database.sh
```

### 3. Restart the Application

```bash
./stop.sh
./start.sh
```

## 📋 What's New

### New Database Tables

1. **training_metrics** - Stores TSS, IF, TRIMP, and zone distribution for each activity
2. **weekly_performance_summary** - Stores CTL/ATL/TSB snapshots and weekly aggregates
3. **Extended user_profiles** - Added `preferred_zone_type` field (hr/pace/power)
4. **Extended strava_activities** - Added denormalized metrics fields for quick access

### New Services

1. **metrics_calculation_service.py** - Calculates TSS, IF, TRIMP, CTL/ATL/TSB
2. **statistics_service.py** - Aggregates statistics for dashboards and reports

### New API Endpoints

**Statistics API (NEW):**
- `GET /statistics/overview` - Dashboard overview with CTL/ATL/TSB
- `GET /statistics/performance-chart?weeks=12` - Performance trends
- `GET /statistics/weekly-summary?week_start_date=YYYY-MM-DD` - Detailed week data
- `GET /statistics/zone-distribution?period=month&sport_type=run` - Zone analysis
- `GET /statistics/training-load` - Load status and recommendations

**Strava API (EXTENDED):**
- `POST /strava/recalculate-metrics` - Manual metrics recalculation

**Profile API (EXTENDED):**
- `PUT /profile/zone-preference` - Set zone preference (hr/pace/power)

### Modified API Endpoints

**Strava API:**
- `GET /strava/activities` - Now includes TSS, IF, TRIMP, zone distribution
- `POST /strava/sync` - Now returns calculated metrics info
- `GET/POST /strava/auth/callback` - Triggers metrics calculation on first connection

**Profile API:**
- `GET /profile` - Now includes `preferred_zone_type`

**Dashboard API (DEPRECATED):**
- `/dashboard/stats` → Use `/statistics/overview`
- `/dashboard/progress` → Use `/statistics/performance-chart`

## 🔄 Migration Path for Existing Users

### First Time Setup

When an existing user connects Strava for the first time:

1. Call `/strava/sync` - Syncs activities
2. Metrics are automatically calculated
3. Initial CTL/ATL/TSB is calculated from last 42 days
4. Weekly summaries are created for available data

### Recalculating Metrics

To recalculate metrics for all activities:

```bash
curl -X POST http://localhost:8000/strava/recalculate-metrics \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🧪 Testing

### Test Metrics Calculation

```python
from app.services.metrics_calculation_service import MetricsCalculationService

service = MetricsCalculationService()

# Test TSS calculation
tss = service.calculate_tss(
    duration_seconds=3600,  # 1 hour
    intensity_factor=0.75
)
print(f"TSS: {tss}")  # Should be around 100

# Test TRIMP
trimp = service.calculate_trimp(
    duration_seconds=3600,
    avg_hr=150,
    max_hr=190
)
print(f"TRIMP: {trimp}")

# Test CTL/ATL/TSB
daily_tss = [100, 120, 110, 130, 115, 125, 105]
metrics = service.calculate_ctl_atl_tsb(daily_tss)
print(f"CTL: {metrics['ctl']}, ATL: {metrics['atl']}, TSB: {metrics['tsb']}")
```

### Test API Endpoints

```bash
# Get overview
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/statistics/overview

# Get performance chart
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/statistics/performance-chart?weeks=12

# Get weekly summary
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/statistics/weekly-summary

# Get zone distribution
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/statistics/zone-distribution?period=month&sport_type=run"

# Get training load
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/statistics/training-load

# Set zone preference
curl -X PUT -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"preferred_zone_type": "hr"}' \
  http://localhost:8000/profile/zone-preference

# Recalculate metrics
curl -X POST -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/strava/recalculate-metrics
```

## 📊 Data Flow

### Activity Sync Flow

1. User connects Strava → `POST /strava/auth/callback`
2. Sync activities → `POST /strava/sync`
3. For each new activity:
   - Calculate TSS (requires IF from power/HR threshold)
   - Calculate TRIMP (requires HR zones)
   - Calculate time in zones
   - Store in `training_metrics` table
   - Denormalize to `strava_activities` table
4. Create/update weekly summary
5. Recalculate CTL/ATL/TSB

### Weekly Summary Update

Weekly summaries are created/updated:
- On activity sync (if activity is in current week)
- When calling `/strava/recalculate-metrics`
- Automatically at week end (can be implemented as background job)

### Statistics API Flow

1. Request → `GET /statistics/overview`
2. Query `weekly_performance_summary` for current week
3. Aggregate data from `strava_activities` if needed
4. Calculate TSB status and color
5. Return comprehensive statistics

## 🐛 Troubleshooting

### Metrics Not Calculating

**Problem:** Activities synced but no metrics calculated

**Solution:**
1. Check if user has performance thresholds set:
   - Go to `/profile/performance`
   - Set HR threshold or Power threshold
2. Manually recalculate:
   - Call `POST /strava/recalculate-metrics`
3. Check logs for calculation errors

### CTL/ATL/TSB Always Zero

**Problem:** Performance metrics showing as zero

**Solution:**
1. Need at least 7 days of activity for ATL
2. Need at least 42 days for CTL
3. Ensure activities have TSS calculated
4. Call `recalculate_metrics` after new data

### Zone Distribution Empty

**Problem:** Zone distribution shows all zeros

**Solution:**
1. Ensure user has HR zones set in performance metrics
2. Activities need average HR data
3. Check `zone_distribution` field in `strava_activities`

### Preferred Zone Type Not Working

**Problem:** Zone calculations using wrong metric

**Solution:**
1. Call `PUT /profile/zone-preference` with correct type
2. Ensure corresponding performance metrics exist
3. Recalculate metrics after changing preference

## 📝 Notes

- Metrics are calculated synchronously on sync (can be slow for many activities)
- Consider implementing background jobs for large syncs
- Weekly summaries are created on-demand, not automatically
- CTL/ATL/TSB require historical data (minimum 7 days for ATL, 42 for CTL)
- Zone distribution requires HR zones to be set in user profile

## 🔮 Future Enhancements

- Background job for automatic weekly summary creation
- Automatic metrics recalculation on periodic schedule
- Cache statistics for better performance
- WebSocket notifications for TSB alerts
- Export statistics to CSV/PDF
- Integration with external analytics tools

