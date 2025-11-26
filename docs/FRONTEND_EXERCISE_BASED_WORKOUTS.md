# Frontend Integration: Exercise-Based Workouts

Questo documento descrive le modifiche necessarie per integrare il frontend con i nuovi servizi di generazione allenamenti basati sulla tabella `exercises`.

## Panoramica

Il sistema ora genera allenamenti di stretching e forza utilizzando esercizi dalla tabella `exercises` invece dell'LLM. Questo garantisce:
- Consistenza nella struttura degli allenamenti
- Controllo preciso su numero di esercizi, durata e frequenza
- Parametrizzazione per sport, fase e livello

## Nuovi Endpoint API

### GET `/api/exercises/equipment`

Restituisce la lista di attrezzi disponibili dalla tabella exercises.

**Response:**
```json
[
  "body only",
  "dumbbell",
  "barbell",
  "cable",
  "machine",
  "bands",
  "kettlebells",
  "medicine ball",
  "exercise ball",
  "foam roll",
  "e-z curl bar",
  "other"
]
```

**Utilizzo:**
```typescript
const response = await fetch('/api/exercises/equipment', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const equipment = await response.json();
```

### GET `/api/exercises`

Query esercizi con filtri opzionali (per debug/admin).

**Query Parameters:**
- `category`: "strength", "stretching", etc.
- `level`: "beginner", "intermediate", "expert"
- `equipment`: Nome attrezzo specifico
- `limit`: Limite risultati (default: 100)

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Exercise Name",
    "category": "strength",
    "level": "beginner",
    "equipment": "body only",
    "primary_muscles": ["muscle1", "muscle2"],
    "secondary_muscles": ["muscle3"],
    "instructions": ["step1", "step2"]
  }
]
```

## Modifiche agli Schemi di Richiesta

### Nuovo Campo: `available_equipment`

Tutti gli endpoint di generazione piani ora accettano il campo opzionale `available_equipment`:

**Endpoint modificati:**
- `POST /api/workouts/plans/generate-progressive`
- `POST /api/workouts/plans/generate-weekly`
- `POST /api/workouts/plans/generate-ai`

**Schema aggiornato:**
```typescript
interface ProgressiveWorkoutPlanRequest {
  // ... campi esistenti
  include_stretching?: boolean;
  include_strength?: boolean;
  available_equipment?: string[]; // NUOVO CAMPO
  unavailable_days?: string[];
  sport_specific_days?: Record<string, string>;
}
```

**Esempio:**
```typescript
const request = {
  sport_type: "running",
  level: "intermediate",
  goal: "Maratona",
  target_date: "2024-06-15",
  start_date: "2024-03-01",
  include_stretching: true,
  include_strength: true,
  available_equipment: ["body only", "dumbbell", "bands"], // NUOVO
  unavailable_days: ["Monday"],
  sport_specific_days: {
    "Wednesday": "run"
  }
};
```

## Struttura Workout Generati

Gli allenamenti di stretching e forza generati hanno questa struttura:

### Stretching Workout

```json
{
  "day": "Tuesday",
  "type": "stretching",
  "sport": "running",
  "duration_minutes": 18,
  "intensity": "easy",
  "zone": "Z1",
  "rpe_target": 2,
  "description": "Stretching session focusing on hamstrings, calves, hip flexors",
  "structure": {
    "sport": "stretching",
    "segments": [
      {
        "segment_type": "warmup",
        "name": "Warm-up",
        "steps": [
          {
            "step_type": "steady",
            "duration": {"type": "time", "seconds": 180},
            "target": {"type": "zone", "zone": "Z1"},
            "notes": "Gentle warm-up movements"
          }
        ]
      },
      {
        "segment_type": "main",
        "name": "Stretching Exercises",
        "exercises": [
          {
            "exercise_id": "uuid",
            "name": "Hamstring Stretch",
            "sets": 3,
            "reps": "45 seconds",
            "rest_seconds": 10,
            "instructions": ["step1", "step2"],
            "equipment": "body only",
            "primary_muscles": ["hamstrings"],
            "secondary_muscles": ["calves"]
          }
          // ... altri esercizi
        ]
      },
      {
        "segment_type": "cooldown",
        "name": "Cool-down",
        "steps": [
          {
            "step_type": "steady",
            "duration": {"type": "time", "seconds": 120},
            "target": {"type": "zone", "zone": "Z1"},
            "notes": "Relaxation and breathing"
          }
        ]
      }
    ],
    "metadata": {
      "focus": "Flexibility and mobility for running",
      "rpe_target": 2,
      "description": "Stretching session with 8 exercises"
    }
  }
}
```

### Strength Workout

```json
{
  "day": "Thursday",
  "type": "strength",
  "sport": "running",
  "duration_minutes": 50,
  "intensity": "hard",
  "zone": "Z1",
  "rpe_target": 7,
  "description": "Strength training focusing on hamstrings, calves, glutes",
  "structure": {
    "sport": "strength",
    "segments": [
      {
        "segment_type": "warmup",
        "name": "Warm-up",
        "steps": [
          {
            "step_type": "steady",
            "duration": {"type": "time", "seconds": 300},
            "target": {"type": "zone", "zone": "Z1"},
            "notes": "Dynamic warm-up and activation"
          }
        ]
      },
      {
        "segment_type": "main",
        "name": "Strength Exercises",
        "exercises": [
          {
            "exercise_id": "uuid",
            "name": "Squat",
            "sets": 4,
            "reps": "6-8",
            "rest_seconds": 90,
            "instructions": ["step1", "step2"],
            "equipment": "barbell",
            "primary_muscles": ["quadriceps", "glutes"],
            "secondary_muscles": ["hamstrings"],
            "mechanic": "compound"
          }
          // ... altri esercizi
        ]
      },
      {
        "segment_type": "cooldown",
        "name": "Cool-down",
        "steps": [
          {
            "step_type": "steady",
            "duration": {"type": "time", "seconds": 180},
            "target": {"type": "zone", "zone": "Z1"},
            "notes": "Stretching and recovery"
          }
        ]
      }
    ],
    "metadata": {
      "focus": "Strength training for running - BUILD phase",
      "rpe_target": 7,
      "description": "Strength session with 6 exercises, 4 sets each"
    }
  }
}
```

## Integrazione Frontend

### 1. Componente Selezione Attrezzi

Crea un componente per selezionare gli attrezzi disponibili:

```typescript
import { useState, useEffect } from 'react';

interface EquipmentSelectorProps {
  selectedEquipment: string[];
  onEquipmentChange: (equipment: string[]) => void;
  token: string;
}

export function EquipmentSelector({ 
  selectedEquipment, 
  onEquipmentChange, 
  token 
}: EquipmentSelectorProps) {
  const [availableEquipment, setAvailableEquipment] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchEquipment() {
      try {
        const response = await fetch('/api/exercises/equipment', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        const equipment = await response.json();
        setAvailableEquipment(equipment);
      } catch (error) {
        console.error('Error fetching equipment:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchEquipment();
  }, [token]);

  const handleToggle = (equipment: string) => {
    if (selectedEquipment.includes(equipment)) {
      onEquipmentChange(selectedEquipment.filter(e => e !== equipment));
    } else {
      onEquipmentChange([...selectedEquipment, equipment]);
    }
  };

  if (loading) return <div>Loading equipment...</div>;

  return (
    <div>
      <h3>Available Equipment</h3>
      <div className="equipment-grid">
        {availableEquipment.map(equipment => (
          <label key={equipment}>
            <input
              type="checkbox"
              checked={selectedEquipment.includes(equipment)}
              onChange={() => handleToggle(equipment)}
            />
            {equipment}
          </label>
        ))}
      </div>
    </div>
  );
}
```

### 2. Aggiornamento Form Generazione Piano

Aggiorna il form di generazione piano per includere la selezione attrezzi:

```typescript
interface WorkoutPlanFormData {
  sport_type: string;
  level: string;
  goal: string;
  target_date: string;
  start_date: string;
  include_stretching: boolean;
  include_strength: boolean;
  available_equipment: string[]; // NUOVO
  unavailable_days: string[];
  sport_specific_days: Record<string, string>;
}

export function WorkoutPlanForm() {
  const [formData, setFormData] = useState<WorkoutPlanFormData>({
    sport_type: 'running',
    level: 'intermediate',
    goal: '',
    target_date: '',
    start_date: '',
    include_stretching: false,
    include_strength: false,
    available_equipment: [], // NUOVO
    unavailable_days: [],
    sport_specific_days: {}
  });

  const handleEquipmentChange = (equipment: string[]) => {
    setFormData({ ...formData, available_equipment: equipment });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const request = {
      ...formData,
      // Se include_stretching o include_strength è true, 
      // available_equipment è richiesto (o almeno raccomandato)
      available_equipment: formData.include_stretching || formData.include_strength
        ? formData.available_equipment.length > 0
          ? formData.available_equipment
          : ['body only'] // Default se nessuno selezionato
        : undefined
    };

    // Invia richiesta...
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* ... altri campi ... */}
      
      <div>
        <label>
          <input
            type="checkbox"
            checked={formData.include_stretching}
            onChange={(e) => setFormData({ 
              ...formData, 
              include_stretching: e.target.checked 
            })}
          />
          Include Stretching
        </label>
      </div>

      <div>
        <label>
          <input
            type="checkbox"
            checked={formData.include_strength}
            onChange={(e) => setFormData({ 
              ...formData, 
              include_strength: e.target.checked 
            })}
          />
          Include Strength Training
        </label>
      </div>

      {/* NUOVO: Selezionatore attrezzi */}
      {(formData.include_stretching || formData.include_strength) && (
        <EquipmentSelector
          selectedEquipment={formData.available_equipment}
          onEquipmentChange={handleEquipmentChange}
          token={token}
        />
      )}

      {/* ... resto del form ... */}
    </form>
  );
}
```

### 3. Visualizzazione Workout con Esercizi

Aggiorna il componente di visualizzazione workout per mostrare gli esercizi:

```typescript
interface Exercise {
  exercise_id: string;
  name: string;
  sets: number;
  reps: string;
  rest_seconds: number;
  instructions: string[];
  equipment: string;
  primary_muscles: string[];
  secondary_muscles?: string[];
  mechanic?: string;
}

interface WorkoutStructure {
  sport: string;
  segments: Array<{
    segment_type: string;
    name: string;
    exercises?: Exercise[];
    steps?: any[];
  }>;
  metadata: {
    focus: string;
    rpe_target: number;
    description: string;
  };
}

export function WorkoutDetail({ workout }: { workout: any }) {
  const structure: WorkoutStructure = workout.structure_json;

  return (
    <div className="workout-detail">
      <h2>{workout.title}</h2>
      <p>{workout.description}</p>
      <p>Duration: {workout.duration_minutes} minutes</p>
      <p>Intensity: {workout.intensity}</p>
      <p>RPE Target: {workout.rpe_target}</p>

      {structure.segments.map((segment, idx) => (
        <div key={idx} className={`segment segment-${segment.segment_type}`}>
          <h3>{segment.name}</h3>
          
          {/* Mostra esercizi se presenti */}
          {segment.exercises && segment.exercises.length > 0 && (
            <div className="exercises-list">
              {segment.exercises.map((exercise: Exercise, exIdx: number) => (
                <div key={exIdx} className="exercise-card">
                  <h4>{exercise.name}</h4>
                  <div className="exercise-details">
                    <span>Sets: {exercise.sets}</span>
                    <span>Reps: {exercise.reps}</span>
                    <span>Rest: {exercise.rest_seconds}s</span>
                    <span>Equipment: {exercise.equipment}</span>
                  </div>
                  {exercise.primary_muscles && exercise.primary_muscles.length > 0 && (
                    <div className="muscles">
                      <strong>Target Muscles:</strong>
                      {exercise.primary_muscles.join(', ')}
                    </div>
                  )}
                  {exercise.instructions && exercise.instructions.length > 0 && (
                    <div className="instructions">
                      <strong>Instructions:</strong>
                      <ol>
                        {exercise.instructions.map((instruction, i) => (
                          <li key={i}>{instruction}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Mostra steps se presenti (per warmup/cooldown) */}
          {segment.steps && segment.steps.length > 0 && (
            <div className="steps-list">
              {segment.steps.map((step: any, stepIdx: number) => (
                <div key={stepIdx} className="step">
                  <p>{step.notes}</p>
                  <p>Duration: {step.duration.seconds}s</p>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}

      {structure.metadata && (
        <div className="workout-metadata">
          <p><strong>Focus:</strong> {structure.metadata.focus}</p>
          <p><strong>Description:</strong> {structure.metadata.description}</p>
        </div>
      )}
    </div>
  );
}
```

### 4. Stili CSS Consigliati

```css
.equipment-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
  margin: 10px 0;
}

.equipment-grid label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
}

.equipment-grid label:hover {
  background-color: #f5f5f5;
}

.exercises-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin: 15px 0;
}

.exercise-card {
  padding: 15px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background-color: #fafafa;
}

.exercise-card h4 {
  margin: 0 0 10px 0;
  color: #333;
}

.exercise-details {
  display: flex;
  gap: 15px;
  margin: 10px 0;
  font-size: 0.9em;
  color: #666;
}

.muscles {
  margin: 10px 0;
  font-size: 0.9em;
}

.instructions {
  margin: 10px 0;
}

.instructions ol {
  margin: 5px 0;
  padding-left: 20px;
}

.segment {
  margin: 20px 0;
  padding: 15px;
  border-left: 3px solid #007bff;
}

.segment-warmup {
  border-left-color: #ffc107;
}

.segment-main {
  border-left-color: #28a745;
}

.segment-cooldown {
  border-left-color: #17a2b8;
}
```

## Parametrizzazione Workout

I workout sono generati in base a parametri configurabili per sport, fase e tipo:

### Fasi di Allenamento

- **BASE**: >12 settimane alla gara
- **BUILD**: 8-12 settimane
- **PEAK**: 4-8 settimane
- **TAPER**: ≤4 settimane

### Frequenza e Durata

La frequenza e durata degli allenamenti sono automaticamente calcolate in base a:
- Sport type (running, cycling, swimming, triathlon)
- Fase di allenamento (BASE/BUILD/PEAK/TAPER)
- Giorni disponibili (rispetto a `unavailable_days`)

**Esempio per Running:**
- BASE: Stretching 4-5x/settimana, 15-20min; Strength 2-3x/settimana, 20-30min
- BUILD: Stretching 4x/settimana, 10-12min; Strength 2-3x/settimana, 45-60min
- PEAK: Stretching 4x/settimana, 8-10min; Strength 1-2x/settimana, 45-50min
- TAPER: Stretching 2-3x/settimana, 5-8min; Strength 1x/settimana, 20-40min

## Best Practices

1. **Selezione Attrezzi**: 
   - Mostra sempre il selettore attrezzi quando `include_stretching` o `include_strength` è true
   - Se l'utente non seleziona attrezzi, usa `['body only']` come default
   - Salva la selezione attrezzi nelle preferenze utente

2. **Visualizzazione Esercizi**:
   - Mostra sempre le istruzioni degli esercizi
   - Evidenzia i gruppi muscolari target
   - Mostra equipment necessario per ogni esercizio

3. **Validazione**:
   - Valida che `available_equipment` sia un array se fornito
   - Verifica che gli attrezzi siano validi (confronta con lista da `/api/exercises/equipment`)

4. **UX**:
   - Mostra un indicatore di caricamento quando si caricano gli attrezzi
   - Fornisci feedback quando gli attrezzi selezionati limitano la selezione esercizi
   - Mostra preview degli esercizi prima di generare il piano completo

## Esempio Completo

```typescript
import { useState, useEffect } from 'react';

export function CompleteWorkoutPlanGenerator() {
  const [equipment, setEquipment] = useState<string[]>([]);
  const [availableEquipment, setAvailableEquipment] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Carica attrezzi disponibili
    fetch('/api/exercises/equipment', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(setAvailableEquipment);
  }, []);

  const handleGeneratePlan = async (formData: any) => {
    setLoading(true);
    try {
      const request = {
        ...formData,
        include_stretching: formData.include_stretching,
        include_strength: formData.include_strength,
        available_equipment: (formData.include_stretching || formData.include_strength)
          ? equipment.length > 0 ? equipment : ['body only']
          : undefined
      };

      const response = await fetch('/api/workouts/plans/generate-progressive', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(request)
      });

      const plan = await response.json();
      // Gestisci piano generato...
    } catch (error) {
      console.error('Error generating plan:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Form generazione piano */}
      {/* ... */}
      
      {/* Selettore attrezzi */}
      <EquipmentSelector
        selectedEquipment={equipment}
        onEquipmentChange={setEquipment}
        token={token}
      />
    </div>
  );
}
```

## Note Importanti

1. **Retrocompatibilità**: Il campo `available_equipment` è opzionale. Se non fornito, il sistema usa tutti gli attrezzi disponibili o `['body only']` come fallback.

2. **Validazione Lato Server**: Il server valida che gli attrezzi forniti siano validi. Attrezzi non validi vengono ignorati.

3. **Performance**: La query degli attrezzi è veloce e può essere cachata lato client.

4. **Error Handling**: Gestisci errori quando:
   - La lista attrezzi non può essere caricata
   - La generazione del piano fallisce
   - Gli attrezzi selezionati non permettono di trovare esercizi sufficienti

## Testing

Test consigliati:

1. **Test Selezione Attrezzi**:
   - Seleziona diversi attrezzi e verifica che vengano passati correttamente
   - Verifica che il default `['body only']` funzioni quando nessun attrezzo è selezionato

2. **Test Generazione Workout**:
   - Genera piano con solo stretching
   - Genera piano con solo strength
   - Genera piano con entrambi
   - Verifica che gli esercizi siano presenti nella struttura

3. **Test Visualizzazione**:
   - Verifica che gli esercizi vengano mostrati correttamente
   - Verifica che le istruzioni siano leggibili
   - Verifica che i gruppi muscolari siano evidenziati

## Supporto

Per domande o problemi, consulta:
- `docs/API_WORKOUT_PLANS_STRETCHING_STRENGTH.md` - Documentazione completa API
- `app/config/workout_parameters.py` - Parametri configurazione workout


