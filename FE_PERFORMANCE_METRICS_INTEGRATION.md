# Integrazione Metriche di Performance - Frontend

Questo documento descrive come il frontend deve inviare le metriche di performance nell'endpoint di generazione dei piani di allenamento.

## Endpoint

**POST** `/workouts/plans/generate-ai`

## Schema Request

La request deve seguire lo schema `AIWorkoutPlanRequest`:

```typescript
interface AIWorkoutPlanRequest {
  sport_type: string;           // "running", "cycling", "swimming", "triathlon"
  level: string;                // "beginner", "intermediate", "advanced"
  goal: string;                 // Obiettivo dell'allenamento (es. "Preparazione gara")
  weekly_hours?: number;        // Opzionale: ore settimanali (indicativo)
  user_profile?: {              // Opzionale: profilo utente + metriche di performance
    // Dati base profilo
    age?: number;
    weight?: number;            // kg
    height?: number;            // cm
    experience_years?: number;
    weekly_hours?: number;
    physical_notes?: string;    // Note su limitazioni fisiche, infortuni, etc.
    preferred_zone_type?: string; // "hr", "pace", "power"
    
    // ========== METRICHE DI PERFORMANCE ==========
    // HR Metrics
    hr_max?: number;            // FC massima (bpm)
    hr_rest?: number;           // FC a riposo (bpm)
    threshold_hr?: number;      // FC alla soglia lattacida (bpm)
    hrr?: number;               // Heart Rate Reserve
    custom_threshold_hr?: number;
    
    // Pace Metrics
    threshold_pace?: string;    // Formato: "mm:ss" o "mm.ss" (es. "4:15" o "4.15")
    critical_speed?: number;    // km/h
    vla?: number;
    
    // Power Metrics
    ftp?: number;               // Functional Threshold Power (W)
    wkg?: number;               // Watts per kilogram
    
    // Advanced Metrics
    vo2max?: number;            // ml/kg/min
    
    // Zone strutturate
    hr_zones?: {                // Zone HR: {"z1": "120-135", "z2": "135-150", ...}
      [zone: string]: string;
    };
    hr_zones_source?: string;   // "auto" | "manual"
    hr_threshold_used?: number;
    
    pace_zones?: {              // Zone pace: {"z1": "5:00-4:45", "z2": "4:45-4:30", ...}
      [zone: string]: string;
    };
    pace_zones_source?: string; // "auto" | "manual"
    threshold_pace_used?: string;
    
    power_zones?: {             // Zone power: {"z1": "0-165", "z2": "166-225", ..., "z7": "451-540"}
      [zone: string]: string;
    };
    power_zones_source?: string; // "auto" | "manual"
    ftp_used?: number;
  };
  preferences?: {               // Opzionale: preferenze utente (INDICATIVE ONLY)
    available_days_per_week?: number;
    min_session_duration_minutes?: number;
    equipment?: string[];
    intensity_preference?: string;
    // ... altri campi di preferenza
  };
  
  // Parametri per piani tradizionali
  duration_weeks?: number;      // Obbligatorio per piani tradizionali
  
  // Parametri per piani progressivi
  is_progressive?: boolean;     // true per piano progressivo
  target_date?: string;         // Data obiettivo (YYYY-MM-DD) - obbligatorio per progressivi
  start_date?: string;          // Data inizio (YYYY-MM-DD) - obbligatorio per progressivi
}
```

## Come Recuperare le Metriche di Performance

Le metriche di performance devono essere recuperate dall'endpoint del profilo:

**GET** `/profile/performance`

Questo endpoint ritorna un array di `PerformanceMetricsResponse`. Per il piano di allenamento, utilizzare la metrica più recente (ordinata per `test_date`).

### Esempio di Response

```json
[
  {
    "id": 1,
    "user_id": 123,
    "hr_max": 195,
    "hr_rest": 50,
    "threshold_hr": 175,
    "hrr": 145,
    "threshold_pace": "4:15",
    "ftp": 250,
    "wkg": 3.57,
    "vo2max": 55.2,
    "hr_zones": {
      "z1": "120-135",
      "z2": "135-150",
      "z3": "150-165",
      "z4": "165-180",
      "z5": "180-195"
    },
    "hr_zones_source": "auto",
    "hr_threshold_used": 175,
    "pace_zones": {
      "z1": "5:00-4:45",
      "z2": "4:45-4:30",
      "z3": "4:30-4:15",
      "z4": "4:15-4:00",
      "z5": "4:00-3:45"
    },
    "pace_zones_source": "auto",
    "threshold_pace_used": "4:15",
    "power_zones": {
      "z1": "0-165",
      "z2": "166-225",
      "z3": "226-285",
      "z4": "286-345",
      "z5": "346-405",
      "z6": "406-450",
      "z7": "451-540"
    },
    "power_zones_source": "auto",
    "ftp_used": 250,
    "test_date": "2024-01-15T10:00:00Z",
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z"
  }
]
```

## Esempi di Implementazione

### Esempio 1: Piano Tradizionale con Metriche HR

```typescript
async function generateWorkoutPlanWithMetrics() {
  // 1. Recupera metriche di performance
  const performanceMetricsResponse = await fetch('/api/profile/performance', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const performanceMetrics = await performanceMetricsResponse.json();
  const latestMetrics = performanceMetrics[0]; // Prendi la più recente
  
  // 2. Costruisci user_profile con metriche
  const userProfile = {
    age: 30,
    weight: 70.5,
    height: 175,
    experience_years: 3,
    preferred_zone_type: 'hr',
    
    // Metriche HR
    hr_max: latestMetrics.hr_max,
    hr_rest: latestMetrics.hr_rest,
    threshold_hr: latestMetrics.threshold_hr,
    hr_zones: latestMetrics.hr_zones,
    hr_zones_source: latestMetrics.hr_zones_source,
    hr_threshold_used: latestMetrics.hr_threshold_used
  };
  
  // 3. Costruisci request
  const request = {
    sport_type: "running",
    level: "intermediate",
    goal: "Preparazione gara 10km",
    duration_weeks: 12,
    weekly_hours: 4.0,  // Opzionale - indicativo
    user_profile: userProfile,
    preferences: {
      available_days_per_week: 5,  // Indicativo
      min_session_duration_minutes: 30  // Indicativo
    },
    is_progressive: false
  };
  
  // 4. Invia request
  const response = await fetch('/api/workouts/plans/generate-ai', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(request)
  });
  
  return await response.json();
}
```

### Esempio 2: Piano Progressivo con Metriche Complete (HR + Pace + Power)

```typescript
async function generateProgressivePlanWithAllMetrics() {
  // 1. Recupera metriche di performance
  const performanceMetricsResponse = await fetch('/api/profile/performance', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const performanceMetrics = await performanceMetricsResponse.json();
  const latestMetrics = performanceMetrics[0];
  
  // 2. Costruisci user_profile con tutte le metriche
  const userProfile = {
    age: 35,
    weight: 68,
    height: 178,
    experience_years: 5,
    preferred_zone_type: 'hr',  // O 'pace' o 'power'
    
    // Metriche HR
    hr_max: latestMetrics.hr_max,
    hr_rest: latestMetrics.hr_rest,
    threshold_hr: latestMetrics.threshold_hr,
    hr_zones: latestMetrics.hr_zones,
    
    // Metriche Pace
    threshold_pace: latestMetrics.threshold_pace,
    pace_zones: latestMetrics.pace_zones,
    
    // Metriche Power
    ftp: latestMetrics.ftp,
    wkg: latestMetrics.wkg,
    power_zones: latestMetrics.power_zones,
    
    // Advanced
    vo2max: latestMetrics.vo2max
  };
  
  // 3. Costruisci request per piano progressivo
  const request = {
    sport_type: "triathlon",
    level: "advanced",
    goal: "Ironman 70.3",
    is_progressive: true,
    target_date: "2024-06-15",
    start_date: "2024-03-15",
    // weekly_hours è opzionale - l'AI deciderà il volume ottimale
    user_profile: userProfile,
    preferences: {
      // Preferenze indicative - l'AI ottimizzerà il piano
      equipment: ["bike", "trainer", "pool_access"]
    }
  };
  
  // 4. Invia request
  const response = await fetch('/api/workouts/plans/generate-ai', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(request)
  });
  
  return await response.json();
}
```

### Esempio 3: Piano senza Metriche (Fallback)

```typescript
async function generatePlanWithoutMetrics() {
  // Se l'utente non ha metriche, invia solo i dati base
  const request = {
    sport_type: "running",
    level: "beginner",
    goal: "Prima maratona",
    duration_weeks: 16,
    user_profile: {
      age: 28,
      weight: 75,
      height: 170,
      experience_years: 1,
      physical_notes: "Nessun infortunio recente"
    },
    preferences: {
      available_days_per_week: 4
    },
    is_progressive: false
  };
  
  const response = await fetch('/api/workouts/plans/generate-ai', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(request)
  });
  
  return await response.json();
}
```

## Note Importanti

### 1. Campo `preferences` vs `user_profile`

- **`user_profile`**: Contiene dati anagrafici, metriche di performance, e caratteristiche fisiche. Questi dati vengono utilizzati dall'AI per personalizzare il piano.
- **`preferences`**: Contiene preferenze dell'utente (giorni disponibili, durata minima, attrezzatura). Questi sono **INDICATIVI** - l'AI ha autonomia per ottimizzare il piano.

### 2. Metriche di Performance

- Le metriche di performance sono **opzionali** ma **altamente consigliate** per piani personalizzati.
- Se presenti, l'AI utilizzerà le zone esatte fornite per prescrivere intensità.
- Il campo `preferred_zone_type` indica quale tipo di zona privilegiare (HR, pace, o power).

### 3. Zone

- Le zone devono essere nel formato stringa con range (es. `"120-135"` per HR, `"4:15-4:00"` per pace, `"200-250"` per power).
- Se sono presenti zone, l'AI utilizzerà **esattamente** quei valori - non stima o approssimazione.

### 4. Piano Progressivo

- Per i piani progressivi (`is_progressive: true`), le metriche vengono passate nel campo `user_profile` che viene mappato a `current_fitness_level`.
- L'AI adatterà il piano settimana per settimana basandosi sulle performance, ma sempre all'interno delle zone definite.

### 5. Campo `weekly_hours`

- **Opzionale**: Se non fornito, l'AI deciderà il volume ottimale.
- Se fornito, è **indicativo** - l'AI può adattarlo per ottimizzare il piano (specialmente per triathlon).

## Struttura Completa del Form

Quando l'utente compila il form per generare un piano:

1. **Dati del Form (modalità guidata)**:
   - `goal`: Obiettivo
   - `endDate`: Data fine
   - `sport`: Sport selezionato
   - `level`: Livello
   - `daysPerWeek`: Giorni disponibili (opzionale, indicativo)
   - `sessionDuration`: Durata sessione (opzionale, indicativo)
   - `equipment`: Attrezzatura (opzionale)
   - `additionalNotes`: Note aggiuntive (opzionale)
   - `isProgressive`: Flag per piano progressivo

2. **Dati del Profilo Utente**:
   - Recuperati da `/profile` (GET)
   - Contengono: `age`, `weight`, `height`, `experience_years`, etc.

3. **Metriche di Performance**:
   - Recuperate da `/profile/performance` (GET) se l'utente ha un checkbox per includerle
   - Se incluse, aggiungere tutti i campi delle metriche a `user_profile`

4. **Mapping Finale**:
   ```typescript
   const apiRequest = {
     sport_type: mapSportToEnglish(formData.sport),  // "running", "cycling", etc.
     level: mapLevelToEnglish(formData.level),       // "beginner", "intermediate", etc.
     goal: formData.goal,
     weekly_hours: formData.daysPerWeek && formData.sessionDuration 
       ? (formData.daysPerWeek * formData.sessionDuration) / 60 
       : undefined,  // Opzionale
     user_profile: {
       ...userProfileData,
       ...(includeMetrics ? performanceMetricsData : {})  // Aggiungi metriche se incluse
     },
     preferences: {
       available_days_per_week: formData.daysPerWeek,  // Indicativo
       min_session_duration_minutes: formData.sessionDuration,  // Indicativo
       equipment: formData.equipment,
       additionalNotes: formData.additionalNotes
     },
     ...(formData.isProgressive ? {
       is_progressive: true,
       target_date: formData.endDate,
       start_date: calculateStartDate(formData.endDate)
     } : {
       duration_weeks: calculateWeeks(formData.startDate, formData.endDate)
     })
   };
   ```

## Checklist per l'Implementazione Frontend

- [ ] Aggiungere checkbox per includere metriche di performance nel form
- [ ] Recuperare metriche da `/profile/performance` quando il checkbox è attivo
- [ ] Mappare correttamente le metriche nel campo `user_profile` della request
- [ ] Gestire il caso in cui l'utente non abbia metriche (fallback)
- [ ] Verificare che `preferred_zone_type` sia incluso se presente nel profilo
- [ ] Assicurarsi che `weekly_hours` sia opzionale (non obbligatorio)
- [ ] Includere `preferences` nella request con i dati del form
- [ ] Testare con e senza metriche di performance
- [ ] Testare con piani tradizionali e progressivi
- [ ] Verificare che le zone siano nel formato corretto (stringa con range)

## Errori Comuni da Evitare

1. ❌ **Non inviare `weekly_hours` come obbligatorio** - è opzionale
2. ❌ **Non confondere `user_profile` con `preferences`** - sono separati
3. ❌ **Non dimenticare `preferences`** - aggiungere sempre nella request
4. ❌ **Non inviare metriche incomplete** - se si includono, includere almeno le zone del tipo preferito
5. ❌ **Non inviare `duration_weeks` per piani progressivi** - usare `target_date` e `start_date`
6. ❌ **Non inviare `target_date` e `start_date` per piani tradizionali** - usare `duration_weeks`

## Supporto

Per domande o problemi, consultare:
- Documentazione API: `/docs` (Swagger UI)
- Schema completo: `app/schemas/workout.py` (AIWorkoutPlanRequest)
- Schema metriche: `app/schemas/user.py` (PerformanceMetricsResponse)

