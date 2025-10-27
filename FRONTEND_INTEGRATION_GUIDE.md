# Frontend Integration Guide - Advanced Training Metrics

## 🔄 API Changes Summary

### **NEW APIs**

#### 1. `/statistics/overview` (GET)
Sostituisce `/dashboard/stats`

**Query Parameters:** None

**Response:**
```json
{
  "total_workouts": 156,
  "total_training_hours": 234.5,
  "current_ctl": 85.3,
  "current_atl": 92.1,
  "current_tsb": -6.8,
  "tsb_status": "optimal|fatigued|fresh",
  "weekly_tss": 450,
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

#### 2. `/statistics/performance-chart` (GET)
Sostituisce `/dashboard/progress`

**Query Parameters:**
- `weeks` (optional, default: 12) - Number of weeks to retrieve

**Response:**
```json
{
  "weeks": [
    {
      "week_start": "2024-10-01",
      "week_end": "2024-10-07",
      "ctl": 75.2,
      "atl": 68.5,
      "tsb": 6.7,
      "weekly_tss": 420,
      "volume_hours": 11.5,
      "workouts_completed": 5,
      "avg_rpe": 6.8
    },
    // ... more weeks
  ],
  "trend_analysis": {
    "ctl_trend": "increasing",
    "fitness_change_pct": 12.5,
    "recommended_next_week_tss": 450
  }
}
```

#### 3. `/statistics/weekly-summary` (GET)

**Query Parameters:**
- `week_start_date` (optional, format: YYYY-MM-DD) - Default: current week

**Response:**
```json
{
  "week_start": "2024-10-21",
  "week_end": "2024-10-27",
  "total_tss": 450,
  "total_volume_hours": 12.5,
  "avg_rpe": 6.8,
  "completion_rate": 85.0,
  "ctl": 85.3,
  "atl": 92.1,
  "tsb": -6.8,
  "workouts": [
    {
      "id": 123,
      "date": "2024-10-21",
      "title": "Morning Run",
      "type": "run",
      "duration_minutes": 60,
      "distance_km": 10.2,
      "tss": 65,
      "if": 0.75,
      "trimp": 85,
      "avg_hr": 145,
      "time_in_zones": {
        "z1": 5,
        "z2": 45,
        "z3": 10,
        "z4": 0,
        "z5": 0
      },
      "normalized_power": 180,
      "status": "completed"
    }
    // ... more workouts
  ],
  "zone_distribution": {
    "z1": 15.5,
    "z2": 60.2,
    "z3": 20.1,
    "z4": 3.2,
    "z5": 1.0
  }
}
```

#### 4. `/statistics/zone-distribution` (GET)

**Query Parameters:**
- `period` (required): "week" | "month" | "year"
- `sport_type` (optional): "run" | "ride" | "swim" | etc.

**Response:**
```json
{
  "period": "month",
  "start_date": "2024-10-01",
  "end_date": "2024-10-31",
  "sport_type": "run",
  "total_time_minutes": 1250,
  "zone_distribution": {
    "z1": {
      "minutes": 250,
      "percentage": 20.0,
      "description": "Recovery/Easy"
    },
    "z2": {
      "minutes": 625,
      "percentage": 50.0,
      "description": "Endurance"
    },
    "z3": {
      "minutes": 250,
      "percentage": 20.0,
      "description": "Tempo"
    },
    "z4": {
      "minutes": 100,
      "percentage": 8.0,
      "description": "Threshold"
    },
    "z5": {
      "minutes": 25,
      "percentage": 2.0,
      "description": "VO2 Max"
    }
  },
  "zone_balance_assessment": "Polarized training - Good balance",
  "recommendations": [
    "Consider adding more Z1 recovery work",
    "Z3 time is appropriate for current training phase"
  ]
}
```

#### 5. `/statistics/training-load` (GET)

**Query Parameters:** None

**Response:**
```json
{
  "current_ctl": 85.3,
  "current_atl": 92.1,
  "current_tsb": -6.8,
  "tsb_status": "fatigued",
  "tsb_color": "yellow",
  "acute_chronic_ratio": 1.08,
  "load_assessment": "Slightly overreaching - monitor recovery",
  "recommendations": [
    "Consider a recovery week in the next 7 days",
    "Keep intensity low for next 2-3 workouts",
    "Ensure 8+ hours of sleep"
  ],
  "weekly_tss_history": [380, 420, 450, 485],
  "recommended_next_week_tss": 350,
  "days_since_rest": 5,
  "form_trend": "declining"
}
```

#### 6. `/strava/recalculate-metrics` (POST)

**Body:** None

**Response:**
```json
{
  "success": true,
  "activities_processed": 156,
  "metrics_calculated": {
    "tss_calculated": 156,
    "trimp_calculated": 156,
    "if_calculated": 89
  },
  "weekly_summaries_created": 12,
  "initial_ctl": 85.3,
  "initial_atl": 92.1,
  "initial_tsb": -6.8,
  "processing_time_seconds": 3.2
}
```

#### 7. `/profile/zone-preference` (PUT)

**Body:**
```json
{
  "preferred_zone_type": "hr"
}
```

**Valid values:** "hr" | "pace" | "power"

**Response:**
```json
{
  "success": true,
  "preferred_zone_type": "hr",
  "zones_calculated": true,
  "current_zones": {
    "z1": {"min": 0, "max": 142, "description": "Recovery"},
    "z2": {"min": 142, "max": 155, "description": "Endurance"},
    "z3": {"min": 155, "max": 165, "description": "Tempo"},
    "z4": {"min": 165, "max": 175, "description": "Threshold"},
    "z5": {"min": 175, "max": 200, "description": "VO2 Max"}
  }
}
```

### **MODIFIED APIs**

#### 1. `/strava/activities` (GET) - EXTENDED

**ADDED to response:**
```json
{
  "id": 123,
  "name": "Morning Run",
  // ... existing fields ...
  
  // NEW FIELDS:
  "tss": 65,
  "normalized_power": 180,
  "intensity_factor": 0.75,
  "trimp": 85,
  "time_in_zone_1": 5,
  "time_in_zone_2": 45,
  "time_in_zone_3": 10,
  "time_in_zone_4": 0,
  "time_in_zone_5": 0,
  "zone_distribution_pct": {
    "z1": 8.3,
    "z2": 75.0,
    "z3": 16.7,
    "z4": 0,
    "z5": 0
  }
}
```

#### 2. `/strava/sync` (POST) - EXTENDED

**Response MODIFIED:**
```json
{
  "total_activities": 15,
  "new_activities": 3,
  "already_synced": 12,
  
  // NEW FIELDS:
  "metrics_calculated": true,
  "tss_total": 195,
  "weekly_summary_updated": true,
  "new_ctl": 86.1,
  "new_atl": 93.5,
  "new_tsb": -7.4
}
```

#### 3. `/strava/auth/callback` (GET/POST) - EXTENDED

**Comportamento MODIFICATO:**
- Dopo la connessione Strava, automaticamente trigger `recalculate_all_metrics()`
- Response include informazioni sul calcolo iniziale

**Response EXTENDED:**
```json
{
  "success": true,
  "message": "Strava account connected successfully",
  "strava_account_id": 123,
  "athlete": { /* ... */ },
  
  // NEW FIELDS:
  "initial_sync_completed": true,
  "activities_synced": 156,
  "metrics_calculated": true,
  "initial_fitness_metrics": {
    "ctl": 85.3,
    "atl": 92.1,
    "tsb": -6.8
  }
}
```

#### 4. `/profile` (GET) - EXTENDED

**Response ADDED:**
```json
{
  "id": 1,
  "user_id": 1,
  // ... existing fields ...
  
  // NEW FIELD:
  "preferred_zone_type": "hr"
}
```

### **DEPRECATED APIs** (mantieni per backward compatibility)

- ❌ `/dashboard/stats` → ✅ Usa `/statistics/overview`
- ❌ `/dashboard/progress` → ✅ Usa `/statistics/performance-chart`

---

## 📱 Frontend Implementation Tasks

### 1. Dashboard Page Updates

**Replace API calls:**
```javascript
// OLD
const stats = await fetch('/dashboard/stats');

// NEW
const stats = await fetch('/statistics/overview');
```

**Add new components:**
- **Performance Management Chart (PMC)**: Line chart showing CTL (blue), ATL (orange), TSB (green)
- **TSS Weekly Gauge**: Circular progress showing current week TSS vs target
- **Form Indicator**: Badge showing TSB status with color coding:
  - TSB > 10: Green "Fresh"
  - TSB -10 to 10: Yellow "Optimal"
  - TSB < -10: Red "Fatigued"
- **Zone Distribution Pie Chart**: Current week time in Z1-Z5

### 2. Profile/Settings Page

**Add zone preference selector:**
```vue
<select v-model="zonePreference" @change="updateZonePreference">
  <option value="hr">Heart Rate Zones</option>
  <option value="pace">Pace Zones</option>
  <option value="power">Power Zones (cycling)</option>
</select>
```

**API call:**
```javascript
async updateZonePreference(preference) {
  await fetch('/profile/zone-preference', {
    method: 'PUT',
    body: JSON.stringify({ preferred_zone_type: preference })
  });
}
```

### 3. Workout/Activity Detail Page

**Add metrics display:**
- TSS badge (large, prominent)
- IF (Intensity Factor) badge
- TRIMP badge
- Zone distribution horizontal bar chart
- Time in each zone table

**Example component:**
```vue
<div class="metrics-grid">
  <MetricCard label="TSS" :value="activity.tss" color="blue" />
  <MetricCard label="IF" :value="activity.intensity_factor" color="orange" />
  <MetricCard label="TRIMP" :value="activity.trimp" color="green" />
</div>

<ZoneDistributionChart :zones="activity.zone_distribution_pct" />
```

### 4. New Statistics Page (recommended)

Create `/statistics` route with tabs:
- **Overview**: Summary cards (CTL/ATL/TSB, weekly TSS, form status)
- **Performance Chart**: 12-week CTL/ATL/TSB trend line graph
- **Zone Analysis**: Period selector + pie/bar charts
- **Progression**: Metric selector + line chart showing trends

### 5. Strava Connection Flow

**Update connection callback:**
```javascript
async function handleStravaCallback(code) {
  const response = await fetch('/strava/auth/callback', {
    method: 'POST',
    body: JSON.stringify({ code })
  });
  
  const data = await response.json();
  
  if (data.initial_sync_completed) {
    // Show success message with metrics
    showNotification(
      `Connected! ${data.activities_synced} activities synced. ` +
      `Your current fitness: CTL ${data.initial_fitness_metrics.ctl}`
    );
  }
}
```

### 6. Weekly Summary Modal/Page

**Add "View Week Details" button in dashboard:**
```javascript
async function viewWeekDetails(weekStart) {
  const data = await fetch(`/statistics/weekly-summary?week_start_date=${weekStart}`);
  // Show modal with detailed week breakdown
}
```

**Display:**
- Week TSS total
- All workouts with individual TSS
- Zone distribution for the week
- CTL/ATL/TSB at end of week
- Completion rate

---

## 🎨 UI/UX Recommendations

### Color Scheme for Metrics
- **CTL** (Fitness): Blue `#3B82F6`
- **ATL** (Fatigue): Orange `#F59E0B`
- **TSB** (Form): Green/Yellow/Red based on value
- **TSS**: Purple `#8B5CF6`

### TSB Status Colors
```javascript
function getTSBColor(tsb) {
  if (tsb > 10) return 'green';      // Fresh
  if (tsb > -10) return 'yellow';    // Optimal
  return 'red';                       // Fatigued
}
```

### Zone Colors (consistent with standards)
- Z1: Light Blue `#DBEAFE`
- Z2: Green `#86EFAC`
- Z3: Yellow `#FDE047`
- Z4: Orange `#FDBA74`
- Z5: Red `#FCA5A5`

---

## 📊 Example Chart Configurations

### Performance Management Chart (Chart.js)
```javascript
{
  type: 'line',
  data: {
    labels: weeks.map(w => w.week_start),
    datasets: [
      {
        label: 'CTL (Fitness)',
        data: weeks.map(w => w.ctl),
        borderColor: '#3B82F6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
      },
      {
        label: 'ATL (Fatigue)',
        data: weeks.map(w => w.atl),
        borderColor: '#F59E0B',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
      },
      {
        label: 'TSB (Form)',
        data: weeks.map(w => w.tsb),
        borderColor: '#10B981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
      }
    ]
  },
  options: {
    scales: {
      y: { beginAtZero: false }
    }
  }
}
```

---

## 🔔 User Notifications

**Show notifications for:**
1. First Strava connection: "Calculating your training metrics... This may take a moment."
2. After calculation: "Analysis complete! Your fitness (CTL) is 85.3"
3. TSB alerts: "Your form is declining. Consider a recovery day."
4. Weekly summary: "Week complete! You earned 450 TSS this week."

---

## 📝 Testing Checklist for Frontend

- [ ] Verify `/statistics/overview` replaces dashboard stats correctly
- [ ] Test Performance Management Chart renders with 12 weeks data
- [ ] Confirm zone preference selector saves and updates zones
- [ ] Check activity detail shows TSS, IF, TRIMP badges
- [ ] Test Strava connection shows metrics calculation progress
- [ ] Verify zone distribution charts display correctly
- [ ] Test weekly summary modal with all workout details
- [ ] Confirm deprecated endpoints still work (backward compatibility)
- [ ] Test TSB color coding (green/yellow/red)
- [ ] Verify all new API error handling

