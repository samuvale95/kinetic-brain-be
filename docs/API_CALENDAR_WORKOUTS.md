# API Calendar - Documentazione Frontend

## Endpoint: `GET /calendar/{year}/{month}`

Questo endpoint restituisce tutti gli allenamenti (workouts) per un mese specifico, inclusi:
- Gli allenamenti completati che non fanno parte di un piano
- Le attività Strava svolte che non appartengono a nessun piano

### Formato Response

L'endpoint restituisce un array di oggetti `CalendarWorkoutResponse` che estende `WorkoutResponse` con supporto per dati Strava.

### Struttura Response

```typescript
interface StravaActivitySummary {
  id: number;                    // ID attività Strava
  strava_activity_id: number;    // Strava activity ID originale
  distance: number | null;       // Distanza in metri
  moving_time: number | null;    // Tempo in movimento in secondi
  elapsed_time: number | null;   // Tempo totale in secondi
  total_elevation_gain: number | null;  // Dislivello totale in metri
  average_speed: number | null;  // Velocità media in m/s
  max_speed: number | null;      // Velocità massima in m/s
  average_heartrate: number | null;  // FC media in bpm
  max_heartrate: number | null;  // FC massima in bpm
  average_watts: number | null;  // Potenza media in watt (ciclismo)
  max_watts: number | null;      // Potenza massima in watt (ciclismo)
  weighted_average_watts: number | null;  // Potenza normalizzata da Strava (ciclismo)
  average_cadence: number | null; // Cadenza media in rpm
  temperature: number | null;    // Temperatura in celsius
  calories: number | null;       // Calorie bruciate
  start_date: string;            // ISO datetime (UTC)
  start_date_local: string;      // ISO datetime (locale)
  
  // Training metrics (calcolate dall'applicazione)
  tss: number | null;            // Training Stress Score
  normalized_power: number | null;  // Potenza normalizzata (ciclismo)
  intensity_factor: number | null;  // IF (rapporto NP/FTP per ciclismo o basato su FC per running)
  trimp: number | null;          // Training Impulse (basato su FC)
  
  // Time in zones (minuti) - possono essere zone FC o potenza
  time_in_zone_1: number | null;
  time_in_zone_2: number | null;
  time_in_zone_3: number | null;
  time_in_zone_4: number | null;
  time_in_zone_5: number | null;
  
  // Zone distribution (JSON: {"z1": minuti, "z2": minuti, ...})
  // Per running: zone cardiache (basate su FC)
  // Per ciclismo: zone potenza (basate su watt)
  zone_distribution: { [key: string]: number } | null;
  
  // Flag per sapere se le metriche sono state calcolate
  metrics_calculated: boolean | null;
}

interface CalendarWorkoutResponse {
  id: number;                    // ⚠️ Negativo per attività Strava senza workout
  plan_id: number | null;        // ⚠️ NULL per allenamenti standalone e attività Strava
  user_id: number;
  title: string;
  type: string;                  // "run", "ride", "swim", "strength", etc.
  day_number: number | null;     // ⚠️ NULL per allenamenti standalone e attività Strava
  scheduled_date: string | null; // ISO date "YYYY-MM-DD"
  duration_minutes: number;
  intensity: string | null;      // "easy", "moderate", "hard" (null per attività Strava)
  zone: string | null;           // "Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7" (null per attività Strava)
  structure_json: object | null; // Struttura workout (null per attività Strava)
  status: "scheduled" | "completed" | "skipped";
  notes: string | null;
  created_at: string;            // ISO datetime
  updated_at: string | null;     // ISO datetime
  strava_activity: StravaActivitySummary | null;  // ⚠️ Presente solo per attività Strava senza workout
}
```

### Tipi di Allenamenti Restituiti

L'endpoint include **tutti** i seguenti tipi di allenamenti:

1. **Allenamenti del piano con `scheduled_date` nel mese**
   - Hanno `plan_id` non nullo
   - Hanno `day_number` non nullo
   - Status: "scheduled" o "completed"
   - `strava_activity`: `null`

2. **Allenamenti completati nel mese (tramite sessioni)**
   - Possono essere standalone (`plan_id: null`)
   - Possono essere parte di piani attivi
   - Sono inclusi se hanno almeno una `WorkoutSession` con `actual_date` nel mese
   - `strava_activity`: `null`

3. **Allenamenti standalone schedulati nel mese**
   - Hanno `plan_id: null`
   - Hanno `day_number: null`
   - Status: "scheduled" o "completed"
   - `strava_activity`: `null`

4. **Attività Strava del mese senza workout associato**
   - Hanno `plan_id: null`
   - Hanno `day_number: null`
   - Hanno `id` **negativo** (per distinguerle dai workout reali)
   - Status: sempre "completed"
   - `intensity`, `zone`, `structure_json`: sempre `null`
   - `title`: nome dell'attività Strava
   - `scheduled_date`: data dell'attività (da `start_date_local` o `start_date`)
   - `duration_minutes`: calcolato da `moving_time` (in secondi) diviso 60
   - `type`: mappato dal tipo Strava (es. "Run" → "run", "Ride" → "ride")
   - **`strava_activity`**: presente con tutti i dati dell'attività Strava (distanza, FC, pace, potenza, etc.)

### Identificazione Allenamenti Standalone

```typescript
function isStandaloneWorkout(workout: CalendarWorkoutResponse): boolean {
  return workout.plan_id === null && !workout.strava_activity;
}
```

### Identificazione Attività Strava

```typescript
function isStravaActivity(workout: CalendarWorkoutResponse): boolean {
  // Metodo 1: Campo strava_activity presente (MIGLIORE)
  return workout.strava_activity !== null;
  
  // Metodo 2: ID negativo (alternativo)
  // return workout.id < 0;
}
```

### Accesso ai Dati Strava

Per le attività Strava, usa il campo `strava_activity` per accedere ai dati completi:

```typescript
if (workout.strava_activity) {
  const strava = workout.strava_activity;
  
  // Distanza in chilometri
  const distanceKm = (strava.distance || 0) / 1000;
  
  // Pace in min/km (se velocità media disponibile)
  const avgPaceMinPerKm = strava.average_speed 
    ? 1000 / (strava.average_speed * 60) 
    : null;
  
  // FC media
  const avgHR = strava.average_heartrate;
  
  // Elevazione in metri
  const elevation = strava.total_elevation_gain || 0;
  
  // Potenza media (ciclismo)
  const avgPower = strava.average_watts;
  const normalizedPower = strava.normalized_power || strava.weighted_average_watts;
  
  // Training metrics
  const tss = strava.tss;  // Training Stress Score
  const if = strava.intensity_factor;  // Intensity Factor
  const trimp = strava.trimp;  // Training Impulse
  
  // Zone distribution
  const zones = strava.zone_distribution;  // {"z1": minuti, "z2": minuti, ...}
  
  // Determina tipo di zone (FC o potenza)
  const isPowerZones = workout.type === "ride" && strava.average_watts !== null;
  const isHeartRateZones = workout.type === "run" && strava.average_heartrate !== null;
  
  // Tempo totale
  const totalTimeSeconds = strava.elapsed_time || strava.moving_time || 0;
  const hours = Math.floor(totalTimeSeconds / 3600);
  const minutes = Math.floor((totalTimeSeconds % 3600) / 60);
}
```

### Training Metrics

Le metriche di allenamento sono **calcolate dall'applicazione** (non vengono direttamente da Strava):

- **TSS (Training Stress Score)**: Indica il carico di allenamento
  - 0-50: Recupero
  - 50-100: Moderato
  - 100-150: Impegnativo
  - 150-200: Molto intenso
  - >200: Estremamente demanding

- **IF (Intensity Factor)**: Intensità relativa
  - Per ciclismo: rapporto tra NP (Normalized Power) e FTP
  - Per running: basato su FC media e soglia FC
  - Range tipico: 0.5 (facile) - 1.2+ (molto intenso)

- **TRIMP (Training Impulse)**: Carico basato su frequenza cardiaca
  - Calcolato usando FC media, FC massima, FC a riposo e durata
  - Più alto = più stress cardiovascolare

- **Normalized Power**: Potenza normalizzata (solo ciclismo)
  - Fornisce una stima più accurata dello sforzo rispetto alla potenza media
  - Calcolata da Strava (`weighted_average_watts`) o dall'applicazione

### Zone Distribution

Il campo `zone_distribution` contiene il tempo trascorso in ogni zona:

```typescript
// Esempio zone distribution
{
  "z1": 5,   // 5 minuti in Z1
  "z2": 45,  // 45 minuti in Z2
  "z3": 10,  // 10 minuti in Z3
  "z4": 0,   // 0 minuti in Z4
  "z5": 0    // 0 minuti in Z5
}
```

**Per identificare il tipo di zone:**

- **Zone Cardiache** (running): Se `workout.type === "run"` e `strava.average_heartrate !== null`
- **Zone Potenza** (ciclismo): Se `workout.type === "ride"` e `strava.average_watts !== null`

**Esempio di utilizzo:**

```typescript
function getZoneDistribution(workout: CalendarWorkoutResponse) {
  if (!workout.strava_activity?.zone_distribution) return null;
  
  const zones = workout.strava_activity.zone_distribution;
  const isPowerZones = workout.type === "ride" && workout.strava_activity.average_watts !== null;
  
  return {
    type: isPowerZones ? "power" : "heart_rate",
    z1: zones.z1 || 0,
    z2: zones.z2 || 0,
    z3: zones.z3 || 0,
    z4: zones.z4 || 0,
    z5: zones.z5 || 0,
    total: (zones.z1 || 0) + (zones.z2 || 0) + (zones.z3 || 0) + (zones.z4 || 0) + (zones.z5 || 0)
  };
}
```

### Ricalcolo Metriche

Se le metriche non sono ancora state calcolate (`metrics_calculated === false` o `null`), puoi richiamare l'endpoint di ricalcolo:

```typescript
// POST /strava/recalculate-metrics
const response = await fetch('/strava/recalculate-metrics', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const result = await response.json();
// result.activities_processed indica quante attività sono state processate
```

### Esempio di Utilizzo

```typescript
// Fetch workouts for November 2025
const response = await fetch('/calendar/2025/11', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const workouts: CalendarWorkoutResponse[] = await response.json();

// Filtra gli allenamenti standalone (non Strava)
const standaloneWorkouts = workouts.filter(
  w => w.plan_id === null && !w.strava_activity && w.id > 0
);

// Filtra le attività Strava (senza workout associato)
const stravaActivities = workouts.filter(w => w.strava_activity !== null);

// Filtra gli allenamenti del piano
const planWorkouts = workouts.filter(w => w.plan_id !== null);
```

### Gestione Visualizzazione Dati

A seconda del tipo di allenamento, mostra dati diversi:

```typescript
interface WorkoutDisplayData {
  type: 'structured' | 'strava' | 'simple';
  title: string;
  duration?: string;
  details?: {
    zone?: string;
    intensity?: string;
    structure?: any;
  } | {
    distance?: string;
    pace?: string;
    heartRate?: string;
    elevation?: string;
    power?: string;
    calories?: string;
  };
}

function getWorkoutDisplayData(workout: CalendarWorkoutResponse): WorkoutDisplayData {
  if (workout.strava_activity) {
    // Attività Strava: mostra dati performance
    const strava = workout.strava_activity;
    const distanceKm = strava.distance ? (strava.distance / 1000).toFixed(2) : null;
    const avgPace = strava.average_speed 
      ? formatPace(strava.average_speed) 
      : null;
    
    return {
      type: 'strava',
      title: workout.title,
      duration: formatDuration(strava.moving_time || strava.elapsed_time || 0),
      details: {
        distance: distanceKm ? `${distanceKm} km` : null,
        pace: avgPace,
        heartRate: strava.average_heartrate 
          ? `${Math.round(strava.average_heartrate)} bpm` 
          : null,
        elevation: strava.total_elevation_gain 
          ? `${Math.round(strava.total_elevation_gain)} m` 
          : null,
        power: strava.average_watts 
          ? `${Math.round(strava.average_watts)}W` 
          : null,
        normalizedPower: strava.normalized_power || strava.weighted_average_watts
          ? `${Math.round(strava.normalized_power || strava.weighted_average_watts)}W` 
          : null,
        calories: strava.calories 
          ? `${Math.round(strava.calories)} cal` 
          : null,
        // Training metrics
        tss: strava.tss ? Math.round(strava.tss) : null,
        intensityFactor: strava.intensity_factor ? strava.intensity_factor.toFixed(2) : null,
        trimp: strava.trimp ? Math.round(strava.trimp) : null,
        // Zone distribution
        zones: strava.zone_distribution || null,
        zoneType: (workout.type === "ride" && strava.average_watts) ? "power" : 
                  (workout.type === "run" && strava.average_heartrate) ? "heart_rate" : null,
      }
    };
  } else if (workout.structure_json) {
    // Workout strutturato: mostra struttura
    return {
      type: 'structured',
      title: workout.title,
      duration: `${workout.duration_minutes} min`,
      details: {
        structure: workout.structure_json,
        zone: workout.zone,
        intensity: workout.intensity
      }
    };
  } else {
    // Workout semplice: mostra info base
    return {
      type: 'simple',
      title: workout.title,
      duration: `${workout.duration_minutes} min`,
      details: {
        zone: workout.zone,
        intensity: workout.intensity
      }
    };
  }
}

function formatPace(speedMs: number): string {
  // Convert m/s to min/km
  const minPerKm = 1000 / (speedMs * 60);
  const minutes = Math.floor(minPerKm);
  const seconds = Math.round((minPerKm - minutes) * 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')} /km`;
}

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}
```

### Esempio Response Completo

```json
[
  {
    "id": 1,
    "plan_id": 5,
    "user_id": 1,
    "title": "Corsa facile Z2",
    "type": "run",
    "day_number": 1,
    "scheduled_date": "2025-11-15",
    "duration_minutes": 45,
    "intensity": "easy",
    "zone": "Z2",
    "structure_json": {
      "sport": "run",
      "segments": [...]
    },
    "status": "scheduled",
    "notes": null,
    "created_at": "2025-11-01T10:00:00Z",
    "updated_at": null,
    "strava_activity": null
  },
  {
    "id": 10,
    "plan_id": null,
    "user_id": 1,
    "title": "Corsa libera",
    "type": "run",
    "day_number": null,
    "scheduled_date": "2025-11-20",
    "duration_minutes": 30,
    "intensity": "easy",
    "zone": "Z2",
    "structure_json": null,
    "status": "completed",
    "notes": "Bellissima corsa al tramonto",
    "created_at": "2025-11-20T08:00:00Z",
    "updated_at": "2025-11-20T18:30:00Z",
    "strava_activity": null
  },
  {
    "id": -123,
    "plan_id": null,
    "user_id": 1,
    "title": "Morning Run",
    "type": "run",
    "day_number": null,
    "scheduled_date": "2025-11-22",
    "duration_minutes": 45,
    "intensity": null,
    "zone": null,
    "structure_json": null,
    "status": "completed",
    "notes": null,
    "created_at": "2025-11-22T07:00:00Z",
    "updated_at": "2025-11-22T08:00:00Z",
    "strava_activity": {
      "id": 123,
      "strava_activity_id": 987654321,
      "distance": 8500.5,
      "moving_time": 2700,
      "elapsed_time": 2750,
      "total_elevation_gain": 150.0,
      "average_speed": 3.15,
      "max_speed": 4.2,
      "average_heartrate": 145.5,
      "max_heartrate": 168.0,
      "average_watts": null,
      "max_watts": null,
      "weighted_average_watts": null,
      "average_cadence": 85.0,
      "temperature": 18.5,
      "calories": 450.0,
      "start_date": "2025-11-22T07:00:00Z",
      "start_date_local": "2025-11-22T08:00:00+01:00",
      "tss": 65.5,
      "normalized_power": null,
      "intensity_factor": 0.72,
      "trimp": 85.3,
      "time_in_zone_1": 5,
      "time_in_zone_2": 35,
      "time_in_zone_3": 5,
      "time_in_zone_4": 0,
      "time_in_zone_5": 0,
      "zone_distribution": {
        "z1": 5,
        "z2": 35,
        "z3": 5,
        "z4": 0,
        "z5": 0
      },
      "metrics_calculated": true
    }
  }
]
```

### Differenze Chiave: Standalone vs Strava vs Piano

| Campo | Standalone | Strava Activity | Piano |
|-------|-----------|-----------------|-------|
| `id` | Positivo | **Negativo** | Positivo |
| `plan_id` | `null` | `null` | `number` (ID del piano) |
| `day_number` | `null` | `null` | `number` (giorno nel piano) |
| `structure_json` | Può essere `null` o presente | Sempre `null` | Di solito sempre presente |
| `intensity` | Può essere presente | Sempre `null` | Di solito presente |
| `zone` | Può essere presente | Sempre `null` | Di solito presente |
| `scheduled_date` | Opzionale | Sempre presente (data attività) | Di solito sempre presente |
| `status` | "scheduled" o "completed" | Sempre "completed" | "scheduled" o "completed" |
| `type` | Come nel piano | Mappato da tipo Strava | Definito nel piano |
| `duration_minutes` | Come nel piano | Calcolato da `moving_time` | Come nel piano |
| `strava_activity` | Sempre `null` | **Presente con dati completi** | Sempre `null` |

### Note per lo Sviluppo Frontend

1. **Ordinamento**: I workout sono già ordinati per data (prima `scheduled_date`, poi `actual_date` della sessione) e durata
2. **Deduplicazione**: Il backend rimuove automaticamente i duplicati se un workout appare sia come scheduled che come completed
3. **Filtri**: Gli allenamenti da piani inattivi sono già esclusi
4. **Stato**: Controlla sempre `status` per determinare se l'allenamento è completato o schedulato
5. **Dati Strava**: Per attività Strava, usa `strava_activity` per mostrare distanza, FC, pace, potenza, etc. invece di `structure_json`
6. **Visualizzazione**: Distingui tra workout strutturati (`structure_json`) e attività Strava (`strava_activity`) per mostrare i dati appropriati
7. **Training Metrics**: Le metriche (TSS, IF, TRIMP) sono disponibili solo se `metrics_calculated === true`. Se `false` o `null`, chiama `/strava/recalculate-metrics` per calcolarle
8. **Zone Distribution**: Usa `zone_distribution` per mostrare grafici a torta o barre del tempo trascorso in ogni zona. Distingui tra zone FC (running) e zone potenza (ciclismo) in base al tipo di attività

### Validazione Frontend

```typescript
// Validazione base
if (!workout.id || !workout.title || !workout.type) {
  console.error('Invalid workout data:', workout);
  return;
}

// Per allenamenti del piano
if (workout.plan_id !== null && workout.day_number === null) {
  console.warn('Plan workout without day_number:', workout);
}

// Per attività Strava
if (workout.strava_activity) {
  // Verifica che i dati Strava siano presenti
  if (!workout.strava_activity.strava_activity_id) {
    console.warn('Strava activity without strava_activity_id:', workout);
  }
  
  // Verifica se le metriche sono state calcolate
  if (workout.strava_activity.metrics_calculated === false || 
      workout.strava_activity.metrics_calculated === null) {
    console.info('Strava activity metrics not calculated. Call /strava/recalculate-metrics');
  }
  
  // Verifica presenza zone distribution
  if (workout.strava_activity.zone_distribution) {
    const zones = workout.strava_activity.zone_distribution;
    const totalZones = (zones.z1 || 0) + (zones.z2 || 0) + (zones.z3 || 0) + 
                       (zones.z4 || 0) + (zones.z5 || 0);
    if (totalZones > 0 && workout.strava_activity.moving_time) {
      const durationMinutes = workout.strava_activity.moving_time / 60;
      // Zone time dovrebbe essere simile alla durata totale (con margine)
      if (Math.abs(totalZones - durationMinutes) > durationMinutes * 0.2) {
        console.warn('Zone distribution time mismatch with activity duration:', {
          totalZones,
          durationMinutes,
          activity: workout.strava_activity.id
        });
      }
    }
  }
}
```

### Compatibilità

Questo endpoint è **compatibile** con:
- `/dashboard/upcoming` - Stessa struttura base, ma `/calendar` include anche `strava_activity`
- `/dashboard/today-workouts` - Stessa struttura base (formattata diversamente)

Il frontend può usare gli stessi componenti/interfacce per visualizzare i workout da tutte queste API, ma deve gestire il caso speciale di `strava_activity` per mostrare i dati appropriati.
