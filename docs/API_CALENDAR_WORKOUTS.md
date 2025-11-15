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
  average_cadence: number | null; // Cadenza media in rpm
  temperature: number | null;    // Temperatura in celsius
  calories: number | null;       // Calorie bruciate
  start_date: string;            // ISO datetime (UTC)
  start_date_local: string;      // ISO datetime (locale)
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
  
  // Tempo totale
  const totalTimeSeconds = strava.elapsed_time || strava.moving_time || 0;
  const hours = Math.floor(totalTimeSeconds / 3600);
  const minutes = Math.floor((totalTimeSeconds % 3600) / 60);
}
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
        calories: strava.calories 
          ? `${Math.round(strava.calories)} cal` 
          : null,
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
      "average_cadence": 85.0,
      "temperature": 18.5,
      "calories": 450.0,
      "start_date": "2025-11-22T07:00:00Z",
      "start_date_local": "2025-11-22T08:00:00+01:00"
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
}
```

### Compatibilità

Questo endpoint è **compatibile** con:
- `/dashboard/upcoming` - Stessa struttura base, ma `/calendar` include anche `strava_activity`
- `/dashboard/today-workouts` - Stessa struttura base (formattata diversamente)

Il frontend può usare gli stessi componenti/interfacce per visualizzare i workout da tutte queste API, ma deve gestire il caso speciale di `strava_activity` per mostrare i dati appropriati.
