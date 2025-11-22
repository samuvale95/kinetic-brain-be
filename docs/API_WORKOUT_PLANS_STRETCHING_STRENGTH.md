# Guida Frontend: Flag Stretching/Forza e Vincoli Giorni nei Piani Allenamento

Questa guida descrive le nuove funzionalità aggiunte agli endpoint di generazione piani di allenamento per includere stretching, forza e vincoli sui giorni di allenamento.

## Panoramica delle Modifiche

Sono stati aggiunti 4 nuovi campi opzionali agli endpoint di generazione piani:

1. **`include_stretching`** (boolean): Include sessioni di stretching nel piano
2. **`include_strength`** (boolean): Include sessioni di forza nel piano
3. **`unavailable_days`** (array): Giorni della settimana in cui non è possibile allenarsi
4. **`sport_specific_days`** (object): Giorni della settimana in cui si può fare solo un determinato sport

## Endpoint Modificati

### 1. POST `/api/workouts/plans/generate-progressive`

Genera un piano progressivo completo con data target.

**Schema Request:** `ProgressiveWorkoutPlanRequest`

**Nuovi campi aggiunti:**

```typescript
interface ProgressiveWorkoutPlanRequest {
  // Campi esistenti
  sport_type: string;
  level: "beginner" | "intermediate" | "advanced";
  goal: string;
  target_date: string; // YYYY-MM-DD
  start_date: string; // YYYY-MM-DD
  weekly_hours?: number;
  user_profile?: Record<string, any>;
  preferences?: Record<string, any>;
  
  // NUOVI CAMPI
  include_stretching?: boolean; // default: false
  include_strength?: boolean; // default: false
  unavailable_days?: string[]; // es: ["Monday", "Friday"]
  sport_specific_days?: Record<string, string>; // es: {"Monday": "run", "Wednesday": "bike"}
}
```

### 2. POST `/api/workouts/plans/generate-weekly`

Genera piano per una settimana specifica.

**Schema Request:** `WeeklyPlanRequest`

**Nuovi campi aggiunti:**

```typescript
interface WeeklyPlanRequest {
  // Campi esistenti
  week_number: number;
  target_date: string; // YYYY-MM-DD
  previous_week_data?: Record<string, any>;
  current_fitness_level?: Record<string, any>;
  specific_adaptations?: Record<string, any>;
  
  // NUOVI CAMPI
  include_stretching?: boolean; // default: false
  include_strength?: boolean; // default: false
  unavailable_days?: string[]; // es: ["Monday", "Friday"]
  sport_specific_days?: Record<string, string>; // es: {"Monday": "run", "Wednesday": "bike"}
}
```

### 3. POST `/api/workouts/plans/generate-ai`

Genera piano completo con AI (endpoint legacy).

**Schema Request:** `WorkoutPlanGenerationRequest`

**Nuovi campi aggiunti:**

```typescript
interface WorkoutPlanGenerationRequest {
  // Campi esistenti
  sport_type: string;
  level: "beginner" | "intermediate" | "advanced";
  goal: string;
  duration_weeks?: number;
  start_date?: string;
  target_date?: string;
  weekly_hours?: number;
  user_profile?: Record<string, any>;
  preferences?: Record<string, any>;
  race_distance_km?: number;
  race_type?: "sprint" | "olympic" | "half_ironman" | "ironman";
  
  // NUOVI CAMPI
  include_stretching?: boolean; // default: false
  include_strength?: boolean; // default: false
  unavailable_days?: string[]; // es: ["Monday", "Friday"]
  sport_specific_days?: Record<string, string>; // es: {"Monday": "run", "Wednesday": "bike"}
}
```

## Dettagli dei Nuovi Campi

### `include_stretching: boolean`

Se `true`, il piano includerà sessioni di stretching seguendo le linee guida scientifiche:

**Comportamento:**
- **Frequenza automatica** basata sulla fase del piano:
  - Off-Season/Base: 4-5 giorni/settimana, 15-20 min per sessione
  - Build: 4 giorni/settimana, 10-12 min per sessione
  - Peak: 4 giorni/settimana, 8-10 min per sessione
  - Taper: 2-3 giorni/settimana, 5-8 min per sessione
- **Timing:** Post-workout OPPURE sessione dedicata mattina/sera
- **Integrazione:** Può essere incorporato nei cooldown OPPURE come workout separato
- **Sport-specific:** Focus muscolare adattato allo sport (running: hamstrings/calves, cycling: quads/hip flexors, swimming: shoulders/chest)

**Esempio:**
```json
{
  "include_stretching": true,
  "sport_type": "running"
}
```

### `include_strength: boolean`

Se `true`, il piano includerà sessioni di forza seguendo periodizzazione scientifica:

**Comportamento:**
- **Periodizzazione automatica** basata su settimane alla gara:
  - **Phase 1: ADAPTATION** (>12 settimane): 3 sessioni/settimana, 20-30 min, bassa intensità
  - **Phase 2: MAX STRENGTH** (8-12 settimane): 2-3 sessioni/settimana, 45-60 min, alta intensità
  - **Phase 3: POWER** (4-8 settimane): 1-2 sessioni/settimana, 45-50 min, esplosivo
  - **Phase 4: MAINTENANCE** (≤4 settimane): 1 sessione/settimana, 20-40 min, moderata intensità
- **Timing critico:**
  - Preferenza: giorni separati dall'endurance
  - Se stesso giorno: min 90 min recovery tra (forza PRIMA)
  - NON fare hard endurance + forza stesso giorno
- **TSS incluso:** Il TSS della forza viene calcolato e incluso nel calcolo ACWR totale

**Esempio:**
```json
{
  "include_strength": true,
  "target_date": "2024-06-15" // Se oggi è 2024-03-15 = 13 settimane = Phase 2
}
```

### `unavailable_days: string[]`

Array di giorni della settimana in cui non è possibile allenarsi.

**Formato:**
- Giorni in inglese: `"Monday"`, `"Tuesday"`, `"Wednesday"`, `"Thursday"`, `"Friday"`, `"Saturday"`, `"Sunday"`
- Case-insensitive (ma preferire formato standard)
- Nessun allenamento sarà programmato in questi giorni

**Esempio:**
```json
{
  "unavailable_days": ["Monday", "Friday"]
}
```

**Nota:** Se un giorno è sia in `unavailable_days` che in `sport_specific_days`, il vincolo sport specifico **prevale** (quindi verrà programmato solo quello sport).

### `sport_specific_days: Record<string, string>`

Mapping di giorni della settimana -> sport specifico da fare quel giorno.

**Formato:**
- Chiave: giorno della settimana (es. `"Monday"`)
- Valore: sport (es. `"run"`, `"bike"`, `"swim"`)
- In quel giorno verrà programmato SOLO quello sport, nessun altro

**Sport validi:**
- `"run"` o `"running"` - Corsa
- `"bike"` o `"cycling"` - Ciclismo
- `"swim"` o `"swimming"` - Nuoto
- Altri sport supportati dal sistema

**Esempio:**
```json
{
  "sport_specific_days": {
    "Monday": "run",
    "Wednesday": "bike",
    "Friday": "swim"
  }
}
```

**Nota:** Se un giorno ha vincolo sport specifico, quel vincolo **prevale** su `unavailable_days`.

## Esempi Completi

### Esempio 1: Piano Running con Stretching e Forza

```typescript
const request = {
  sport_type: "running",
  level: "intermediate",
  goal: "Maratona di Roma",
  target_date: "2024-06-15",
  start_date: "2024-03-01",
  weekly_hours: 8,
  include_stretching: true,
  include_strength: true,
  unavailable_days: ["Monday"], // Riposo il lunedì
  sport_specific_days: {
    "Wednesday": "run" // Mercoledì solo corsa
  }
};

const response = await fetch('/api/workouts/plans/generate-progressive', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(request),
});
```

**Risultato atteso:**
- Piano con stretching incorporato nei cooldown (4-5 giorni/settimana, 15-20 min)
- Piano con forza 2-3 volte/settimana (Phase 2: MAX STRENGTH, 8-12 settimane alla gara)
- Nessun allenamento il lunedì
- Mercoledì solo allenamenti di corsa

### Esempio 2: Piano Triathlon con Vincoli Giorni

```typescript
const request = {
  sport_type: "triathlon",
  level: "advanced",
  goal: "Ironman",
  target_date: "2024-09-01",
  start_date: "2024-06-01",
  weekly_hours: 15,
  include_stretching: true,
  include_strength: true,
  unavailable_days: ["Friday"], // Venerdì riposo
  sport_specific_days: {
    "Monday": "swim", // Lunedì solo nuoto
    "Wednesday": "bike", // Mercoledì solo bici
    "Saturday": "run" // Sabato solo corsa
  }
};

const response = await fetch('/api/workouts/plans/generate-progressive', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(request),
});
```

**Risultato atteso:**
- Piano triathlon con stretching (10-12 min, focus combinato)
- Piano con forza 1-2 volte/settimana (Phase 3: POWER, 4-8 settimane alla gara)
- Venerdì completamente libero
- Lunedì: solo nuoto (+ stretching se incluso)
- Mercoledì: solo bici (+ stretching se incluso)
- Sabato: solo corsa (+ stretching se incluso)

### Esempio 3: Generazione Settimana con Vincoli

```typescript
const request = {
  week_number: 5,
  target_date: "2024-06-15",
  include_stretching: true,
  include_strength: true,
  unavailable_days: ["Monday", "Friday"],
  sport_specific_days: {
    "Wednesday": "run"
  },
  previous_week_data: {
    week: 4,
    completion_rate: 100,
    avg_rpe: 6.5
  }
};

const response = await fetch('/api/workouts/plans/generate-weekly', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(request),
});
```

## Validazione e Errori

### Errori di Validazione

**Giorni non validi in `unavailable_days`:**
```json
{
  "detail": "Invalid day in unavailable_days: 'Mon'. Valid days are: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday"
}
```

**Sport non valido in `sport_specific_days`:**
```json
{
  "detail": "Invalid sport 'skating' in sport_specific_days. Valid sports: run, running, bike, cycling, swim, swimming, ..."
}
```

**Conflitto giorni (risolto automaticamente):**
Se un giorno è sia in `unavailable_days` che in `sport_specific_days`, il sistema:
- Accetta la richiesta senza errore
- Applica il vincolo sport specifico (prevale)
- Ignora il vincolo unavailable per quel giorno

## Comportamento del Sistema

### Periodizzazione Automatica

Il sistema calcola automaticamente la fase di forza e stretching basandosi su:

1. **Forza:**
   - Settimane rimanenti alla `target_date`
   - Fase del piano (base/build/peak/taper)

2. **Stretching:**
   - Fase del piano (base/build/peak/taper)
   - Sport type (per focus muscolare)

### Integrazione nei Workout

**Stretching:**
- Può apparire come:
  - Parte del cooldown (incorporato)
  - Workout separato dedicato
  - Entrambi (a seconda della fase)

**Forza:**
- Appare sempre come workout separato
- Timing ottimizzato (giorni separati preferiti)
- TSS incluso nel calcolo ACWR

### Vincoli Giorni

**Priorità:**
1. `sport_specific_days` (più alta)
2. `unavailable_days` (più bassa)

**Esempio:**
```json
{
  "unavailable_days": ["Monday"],
  "sport_specific_days": {"Monday": "run"}
}
```
Risultato: Lunedì avrà solo corsa (vincolo sport specifico prevale).

## Best Practices Frontend

### 1. UI per Selezione Giorni

```typescript
// Componente per selezionare giorni non disponibili
const [unavailableDays, setUnavailableDays] = useState<string[]>([]);

const daysOfWeek = [
  "Monday", "Tuesday", "Wednesday", "Thursday", 
  "Friday", "Saturday", "Sunday"
];

// Checkbox per ogni giorno
{daysOfWeek.map(day => (
  <Checkbox
    key={day}
    label={day}
    checked={unavailableDays.includes(day)}
    onChange={(checked) => {
      if (checked) {
        setUnavailableDays([...unavailableDays, day]);
      } else {
        setUnavailableDays(unavailableDays.filter(d => d !== day));
      }
    }}
  />
))}
```

### 2. UI per Sport Specifici

```typescript
// Componente per mappare giorni -> sport
const [sportSpecificDays, setSportSpecificDays] = useState<Record<string, string>>({});

const sports = ["run", "bike", "swim"];

{daysOfWeek.map(day => (
  <Select
    key={day}
    label={`${day} - Sport specifico (opzionale)`}
    value={sportSpecificDays[day] || ""}
    onChange={(sport) => {
      if (sport) {
        setSportSpecificDays({...sportSpecificDays, [day]: sport});
      } else {
        const {[day]: _, ...rest} = sportSpecificDays;
        setSportSpecificDays(rest);
      }
    }}
  >
    <option value="">Nessun vincolo</option>
    {sports.map(sport => (
      <option key={sport} value={sport}>{sport}</option>
    ))}
  </Select>
))}
```

### 3. Validazione Client-Side

```typescript
function validateRequest(request: ProgressiveWorkoutPlanRequest): string[] {
  const errors: string[] = [];
  
  // Validare giorni
  const validDays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  if (request.unavailable_days) {
    const invalidDays = request.unavailable_days.filter(
      day => !validDays.includes(day)
    );
    if (invalidDays.length > 0) {
      errors.push(`Giorni non validi: ${invalidDays.join(", ")}`);
    }
  }
  
  // Validare sport
  const validSports = ["run", "running", "bike", "cycling", "swim", "swimming"];
  if (request.sport_specific_days) {
    const invalidSports = Object.entries(request.sport_specific_days)
      .filter(([_, sport]) => !validSports.includes(sport))
      .map(([day, _]) => day);
    if (invalidSports.length > 0) {
      errors.push(`Sport non validi per giorni: ${invalidSports.join(", ")}`);
    }
  }
  
  return errors;
}
```

### 4. Gestione Conflitti

```typescript
// Mostra warning se ci sono conflitti
function checkConflicts(
  unavailableDays: string[],
  sportSpecificDays: Record<string, string>
): string[] {
  const conflicts: string[] = [];
  
  Object.keys(sportSpecificDays).forEach(day => {
    if (unavailableDays.includes(day)) {
      conflicts.push(
        `${day}: Vincolo sport specifico prevarrà su 'non disponibile'`
      );
    }
  });
  
  return conflicts;
}
```

## Esempio Completo React Hook

```typescript
import { useState } from 'react';

interface UseWorkoutPlanGenerationOptions {
  token: string;
  onSuccess?: (plan: any) => void;
  onError?: (error: Error) => void;
}

export function useWorkoutPlanGeneration({
  token,
  onSuccess,
  onError,
}: UseWorkoutPlanGenerationOptions) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const generateProgressivePlan = async (request: ProgressiveWorkoutPlanRequest) => {
    setIsGenerating(true);
    setError(null);

    try {
      // Validazione client-side
      const validationErrors = validateRequest(request);
      if (validationErrors.length > 0) {
        throw new Error(validationErrors.join(", "));
      }

      // Check conflitti
      const conflicts = checkConflicts(
        request.unavailable_days || [],
        request.sport_specific_days || {}
      );
      if (conflicts.length > 0) {
        console.warn("Conflitti rilevati:", conflicts);
        // Mostra warning all'utente ma procedi
      }

      const response = await fetch('/api/workouts/plans/generate-progressive', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Errore nella generazione del piano');
      }

      const plan = await response.json();
      onSuccess?.(plan);
      return plan;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      onError?.(error);
      throw error;
    } finally {
      setIsGenerating(false);
    }
  };

  return {
    generateProgressivePlan,
    isGenerating,
    error,
  };
}
```

## Riepilogo

1. **Flag stretching/forza**: Booleani semplici, default `false`
2. **Vincoli giorni**: Array per giorni non disponibili, object per sport specifici
3. **Priorità**: Sport specifici prevale su giorni non disponibili
4. **Periodizzazione**: Automatica basata su settimane alla gara e fase
5. **Validazione**: Giorni e sport vengono validati lato server
6. **Integrazione**: Stretching può essere incorporato o separato, forza sempre separato

Tutti i campi sono opzionali e retrocompatibili con le richieste esistenti.

