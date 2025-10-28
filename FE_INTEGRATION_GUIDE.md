# Frontend Integration Guide - Training Metrics Fix

## Overview

This document describes the backend changes made to fix CTL/ATL/TSB calculation and weekly summary generation. These changes ensure that training metrics are correctly calculated up to the current date, including weeks and days without activities.

## Key Concepts

### CTL/ATL/TSB Metrics

- **CTL (Chronic Training Load)**: Long-term fitness indicator. Calculated using a 42-day exponential moving average of TSS (Training Stress Score).
- **ATL (Acute Training Load)**: Short-term fatigue indicator. Calculated using a 7-day exponential moving average of TSS.
- **TSB (Training Stress Balance)**: Form indicator. Calculated as CTL - ATL.
  - TSB > 10: Fresh (good form, ready for hard efforts)
  - TSB -10 to 10: Optimal (good balance)
  - TSB < -10: Fatigued (needs rest)

### Importance of Rest Days

**Critical**: CTL and ATL decay on days with 0 TSS. This means:
- If an athlete doesn't train for 2 weeks, CTL and ATL will decrease
- The metrics reflect the actual state of fitness/fatigue
- This is the correct TrainingPeaks methodology

### Weekly Summaries

Weekly summaries are now created for **ALL weeks** up to the current week, even if there are no activities. This ensures:
- Continuous time series data for charts
- Accurate CTL/ATL/TSB calculation (including decay on rest weeks)
- Current week is always included (even if partial)

## API Changes

### 1. `/statistics/overview` (GET)

**Purpose**: Get dashboard overview statistics with current CTL/ATL/TSB.

**No Changes Required**: This endpoint already works correctly. It fetches the most recent weekly summary (not necessarily the current week) if the current week summary doesn't exist yet.

**Response Example**:
```json
{
  "total_workouts": 156,
  "total_training_hours": 234.5,
  "current_ctl": 85.3,
  "current_atl": 92.1,
  "current_tsb": -6.8,
  "tsb_status": "optimal",
  "weekly_tss": 450.5,
  "current_week_volume_hours": 12.5,
  "zone_distribution_current_week": {
    "z1": 25.5,
    "z2": 45.2,
    "z3": 20.1,
    "z4": 7.2,
    "z5": 2.0
  },
  "completion_rate_current_week": 85.0
}
```

**Field Descriptions**:
- `current_ctl`: Current chronic training load (fitness level)
- `current_atl`: Current acute training load (fatigue level)
- `current_tsb`: Current training stress balance (form = fitness - fatigue)
- `tsb_status`: Can be "fresh", "optimal", or "fatigued"
- `weekly_tss`: Total training stress score for the most recent complete week
- `current_week_volume_hours`: Training hours for current week
- `zone_distribution_current_week`: Time spent in each HR zone as percentage
- `completion_rate_current_week`: Percentage of planned workouts completed

**Important Note**: All metrics are calculated from Strava activities ONLY. They are independent of workout plans.

---

### 2. `/statistics/performance-chart` (GET)

**Purpose**: Get historical CTL/ATL/TSB trends for performance visualization.

**Changes**:
- Now includes the current week (even if partial)
- Pads missing weeks with zeros/null values to ensure continuous time series
- Always returns exactly the requested number of weeks (default 12)

**Query Parameters**:
- `weeks` (optional, default: 12, min: 1, max: 52): Number of weeks to retrieve

**Response Example**:
```json
{
  "weeks": [
    {
      "week_start": "2024-10-21",
      "week_end": "2024-10-27",
      "ctl": null,
      "atl": null,
      "tsb": null,
      "weekly_tss": 0,
      "volume_hours": 0,
      "workouts_completed": 0,
      "avg_rpe": null
    },
    {
      "week_start": "2024-10-28",
      "week_end": "2024-11-03",
      "ctl": 85.3,
      "atl": 92.1,
      "tsb": -6.8,
      "weekly_tss": 450.5,
      "volume_hours": 12.5,
      "workouts_completed": 5,
      "avg_rpe": 6.8
    },
    // ... more weeks (always up to current week)
    {
      "week_start": "2025-10-20",
      "week_end": "2025-10-26",
      "ctl": 82.1,
      "atl": 75.3,
      "tsb": 6.8,
      "weekly_tss": 380.0,
      "volume_hours": 10.5,
      "workouts_completed": 4,
      "avg_rpe": 7.0
    }
  ],
  "trend_analysis": {
    "ctl_trend": "stable",
    "fitness_change_pct": -3.8,
    "recommended_next_week_tss": 400.0
  }
}
```

**Field Descriptions**:
- `week_start`: Monday of the week (ISO format)
- `week_end`: Sunday of the week (ISO format)
- `ctl`, `atl`, `tsb`: Can be `null` if no summary exists for that week (padded empty weeks)
- `weekly_tss`: Total training stress for the week (0 for rest weeks)
- `volume_hours`: Total training time in hours
- `workouts_completed`: Number of activities completed
- `avg_rpe`: Average Rate of Perceived Exertion (1-10)
- `ctl_trend`: "increasing", "decreasing", or "stable" (±5 point threshold)
- `fitness_change_pct`: Percentage change in CTL over the period
- `recommended_next_week_tss`: Suggested training load for next week (110% of average recent TSS)

**Important Notes**:
1. **Null values**: Weeks with `null` CTL/ATL/TSB should be displayed differently (e.g., as gaps in the chart)
2. **Current week**: Always included (even if incomplete or no activities)
3. **Continuous data**: Missing weeks are padded with zeros/null values to ensure continuous time series

**Frontend Handling**:
```javascript
// Example: Handle null values in chart
weeks.forEach(week => {
  if (week.ctl === null) {
    // Display as gap or zero baseline
    chart.addDataPoint(week.week_start, null, 'no-data');
  } else {
    chart.addDataPoint(week.week_start, week.ctl, 'normal');
  }
});
```

---

### 3. `/strava/debug/weekly-summaries` (GET)

**Purpose**: Debug endpoint to inspect CTL/ATL/TSB values in database.

**Response Example**:
```json
{
  "count": 5,
  "summaries": [
    {
      "week_start": "2025-10-20",
      "ctl": 82.1,
      "atl": 75.3,
      "tsb": 6.8,
      "weekly_tss": 380.0
    },
    // ... more weeks
  ]
}
```

**Use**: For debugging. Verify that current week exists and values are non-zero.

---

### 4. `/strava/debug/create-summaries` (POST)

**Purpose**: Manually trigger weekly summary creation.

**Request**: None (authenticated endpoint)

**Response**:
```json
{
  "success": true,
  "weekly_summaries_created": 15,
  "message": "Created 15 weekly summaries"
}
```

**Debug Output** (check server logs):
```
DEBUG: Creating summaries from 2024-08-05 to 2025-10-27
DEBUG: Found 15 summaries to update with CTL/ATL/TSB
DEBUG SUMMARY: Created summaries from 2024-08-05 to 2025-10-27 (15 weeks)
DEBUG SUMMARY: Latest week CTL=82.1, ATL=75.3, TSB=6.8
```

---

## Migration Requirements

### 1. Recalculate Existing Summaries

If the system has existing weekly summaries with incorrect CTL/ATL/TSB values, you need to recalculate them:

**API Call**:
```bash
POST /strava/debug/create-summaries
# Or for authenticated endpoint:
POST /strava/create-weekly-summaries
```

This will:
- Create summaries for ALL weeks up to current week
- Calculate CTL/ATL/TSB for each week based on 42 days of historical data
- Handle missing weeks (pad with zeros)
- Include current week even if incomplete

### 2. Verify Current Week Inclusion

After recalculation, verify that the current week is included:
```bash
GET /statistics/performance-chart?weeks=12
```

Check that the last week in the response is the current week (or very recent).

---

## Frontend Integration Examples

### 1. Display CTL/ATL/TSB Chart

```javascript
async function loadPerformanceChart() {
  const response = await fetch('/statistics/performance-chart?weeks=12');
  const data = await response.json();
  
  // Filter out null values for display
  const validWeeks = data.weeks.filter(w => w.ctl !== null);
  
  const chartData = {
    labels: validWeeks.map(w => w.week_start),
    ctl: validWeeks.map(w => w.ctl),
    atl: validWeeks.map(w => w.atl),
    tsb: validWeeks.map(w => w.tsb)
  };
  
  // Render chart...
}
```

### 2. Display TSB Status

```javascript
async function loadOverview() {
  const response = await fetch('/statistics/overview');
  const data = await response.json();
  
  // Display TSB status with color coding
  const statusColors = {
    fresh: '#4CAF50',    // Green
    optimal: '#2196F3',  // Blue
    fatigued: '#FF9800'  // Orange
  };
  
  document.getElementById('tsb-status').style.color = 
    statusColors[data.tsb_status];
  document.getElementById('tsb-value').textContent = data.current_tsb;
}
```

### 3. Handle Missing Weeks

```javascript
async function renderPerformanceChart() {
  const response = await fetch('/statistics/performance-chart');
  const data = await response.json();
  
  data.weeks.forEach((week, index) => {
    if (week.ctl === null) {
      // Display gap or discontinuation in chart
      chart.addGap(week.week_start);
    } else {
      chart.addDataPoint(week.week_start, week.ctl, week.atl, week.tsb);
    }
  });
}
```

---

## Important Notes for Frontend

1. **Null Values**: Weeks with `null` CTL/ATL/TSB should be displayed as gaps or separate markers in charts
2. **Current Week**: Always present in the data, even if incomplete
3. **Rest Weeks**: Weeks with `weekly_tss = 0` are valid (athlete didn't train)
4. **TSB Status**: Use color coding (green/yellow/orange) for visual feedback
5. **Trend Analysis**: Use `ctl_trend` and `fitness_change_pct` for trend indicators

---

## Testing Checklist

- [ ] Current week appears in performance chart
- [ ] All requested weeks are returned (including current)
- [ ] Null values are handled correctly in UI
- [ ] TSB status changes based on TSB value
- [ ] Trends show correctly (increasing/decreasing/stable)
- [ ] Recommended TSS is reasonable (close to average +10%)

---

## Support

For questions or issues, check server logs for debug output from weekly summary creation process.

