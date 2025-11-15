# API Calendar - Documentazione Frontend

## Endpoint: `GET /calendar/{year}/{month}`

Questo endpoint restituisce tutti gli allenamenti (workouts) per un mese specifico, inclusi:
- Gli allenamenti completati che non fanno parte di un piano
- Le attività Strava svolte che non appartengono a nessun piano

### Formato Response

L'endpoint restituisce un array di oggetti `Workout` con la stessa struttura di `/dashboard/upcoming` e `/dashboard/today-workouts`.

### Struttura Workout Response

```typescript
interface Workout {
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
}
```

### Tipi di Allenamenti Restituiti

L'endpoint include **tutti** i seguenti tipi di allenamenti:

1. **Allenamenti del piano con `scheduled_date` nel mese**
   - Hanno `plan_id` non nullo
   - Hanno `day_number` non nullo
   - Status: "scheduled" o "completed"

2. **Allenamenti completati nel mese (tramite sessioni)**
   - Possono essere standalone (`plan_id: null`)
   - Possono essere parte di piani attivi
   - Sono inclusi se hanno almeno una `WorkoutSession` con `actual_date` nel mese

3. **Allenamenti standalone schedulati nel mese**
   - Hanno `plan_id: null`
   - Hanno `day_number: null`
   - Status: "scheduled" o "completed"

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

### Esclusi dalla Response

- Allenamenti da piani **non attivi** (status != "active")
- Allenamenti con status "skipped" che non hanno sessioni nel mese

### Identificazione Allenamenti Standalone

Per identificare un allenamento standalone (non parte di un piano):

```typescript
function isStandaloneWorkout(workout: Workout): boolean {
  return workout.plan_id === null;
}
```

### Identificazione Attività Strava

Per identificare un'attività Strava (non associata a nessun workout):

```typescript
function isStravaActivity(workout: Workout): boolean {
  return workout.id < 0; // ID negativo indica attività Strava
}

// Oppure combinato
function isStandaloneOrStrava(workout: Workout): boolean {
  return workout.plan_id === null;
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

const workouts: Workout[] = await response.json();

// Filtra gli allenamenti standalone
const standaloneWorkouts = workouts.filter(w => w.plan_id === null && w.id > 0);

// Filtra le attività Strava (senza workout associato)
const stravaActivities = workouts.filter(w => w.id < 0);

// Filtra gli allenamenti del piano
const planWorkouts = workouts.filter(w => w.plan_id !== null);

// Raggruppa per data
const workoutsByDate = workouts.reduce((acc, workout) => {
  const date = workout.scheduled_date || workout.actual_date;
  if (!acc[date]) acc[date] = [];
  acc[date].push(workout);
  return acc;
}, {} as Record<string, Workout[]>);
```

### Differenze Chiave: Standalone vs Piano

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

### Gestione Data di Visualizzazione

Per gli allenamenti che hanno `scheduled_date` nel mese, usa quella data.
Per gli allenamenti completati via sessione ma con `scheduled_date` diversa o null, il backend usa la data della prima sessione del mese (`actual_date`).

### Note per lo Sviluppo Frontend

1. **Ordinamento**: I workout sono già ordinati per data (prima `scheduled_date`, poi `actual_date` della sessione) e durata
2. **Deduplicazione**: Il backend rimuove automaticamente i duplicati se un workout appare sia come scheduled che come completed
3. **Filtri**: Gli allenamenti da piani inattivi sono già esclusi
4. **Stato**: Controlla sempre `status` per determinare se l'allenamento è completato o schedulato

### Esempio Response

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
    "updated_at": null
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
    "updated_at": "2025-11-20T18:30:00Z"
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
    "updated_at": "2025-11-22T08:00:00Z"
  }
]
```

### Validazione Frontend

Si consiglia di validare:

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
if (workout.id < 0) {
  // È un'attività Strava senza workout associato
  // L'ID negativo è l'opposto dell'ID Strava activity
  const stravaActivityId = -workout.id;
}
```

### Compatibilità

Questo endpoint è **compatibile** con:
- `/dashboard/upcoming` - Stessa struttura response
- `/dashboard/today-workouts` - Stessa struttura response (formattata diversamente)

Il frontend può usare gli stessi componenti/interfacce per visualizzare i workout da tutte queste API.

