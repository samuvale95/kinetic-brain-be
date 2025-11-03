# Guida Integrazione Frontend - Piani di Allenamento Progressivi

## 📋 Indice

1. [Overview](#overview)
2. [API Endpoints](#api-endpoints)
3. [Struttura Dati](#struttura-dati)
4. [Workflow UI](#workflow-ui)
5. [Esempi di Implementazione](#esempi-di-implementazione)
6. [Gestione Stati](#gestione-stati)

---

## Overview

I **piani di allenamento progressivi** sono piani che si adattano settimana per settimana in base alle performance dell'utente. A differenza dei piani tradizionali (generati tutti in una volta), i piani progressivi vengono generati settimana per settimana, permettendo adattamenti basati sui dati reali.

### Caratteristiche Principali

- ✅ Generazione settimana per settimana (non tutti gli workouts all'inizio)
- ✅ Adattamento automatico basato su performance
- ✅ Controllo se la prossima settimana può essere generata
- ✅ Workouts raggruppati per settimana nella risposta API
- ✅ Supporto per mock mode (senza chiamate AI)

---

## API Endpoints

### 1. Creare un Piano Progressivo

**Endpoint:** `POST /workouts/plans/generate-progressive`

**Request Body:**
```json
{
  "sport_type": "triathlon",
  "level": "intermediate",
  "goal": "Ironman 70.3",
  "target_date": "2025-12-24",
  "start_date": "2025-11-02",
  "weekly_hours": 8.0,
  "user_profile": {
    "age": 30,
    "experience_years": 3,
    "weekly_hours": 8.0,
    "weight": 70,
    "height": 175
  }
}
```

**Response:**
```json
{
  "plan": {
    "id": 25,
    "user_id": 1,
    "title": "Triathlon - Ironman 70.3",
    "description": "Piano progressivo per Ironman 70.3 - Target: 2025-12-24",
    "start_date": "2025-11-02",
    "end_date": "2025-12-24",
    "total_weeks": 7,
    "goal": "Ironman 70.3",
    "sport_type": "triathlon",
    "level": "intermediate",
    "status": "active",
    "is_progressive": true,
    "created_at": "2025-11-02T22:32:29.380084+00:00",
    "updated_at": null
  },
  "first_week": {
    "week": 1,
    "focus": "Base Building",
    "adaptations": {
      "intensity_change": "0%",
      "volume_change": "0%",
      "rationale": "First week - establishing baseline"
    },
    "workouts": [
      {
        "type": "Swim",
        "duration_minutes": 45,
        "intensity": "Z2",
        "description": "Easy swim technique work",
        "day": "Monday",
        "rpe_target": 6
      }
      // ... altri workouts
    ],
    "recovery_notes": "Focus on sleep and nutrition for base building",
    "next_week_preview": "Continue base building with slight volume increase"
  },
  "target_date": "2025-12-24",
  "total_weeks": 7,
  "workouts_created": 4,
  "calendar_events_created": 4
}
```

---

### 2. Ottenere Dettagli di un Piano

**Endpoint:** `GET /workouts/plans/{plan_id}`

**Response:**
```json
{
  "id": 25,
  "user_id": 1,
  "title": "Triathlon - Ironman 70.3",
  "description": "Piano progressivo per Ironman 70.3 - Target: 2025-12-24",
  "start_date": "2025-11-02",
  "end_date": "2025-12-24",
  "total_weeks": 7,
  "goal": "Ironman 70.3",
  "sport_type": "triathlon",
  "level": "intermediate",
  "status": "active",
  "is_progressive": true,
  "created_at": "2025-11-02T22:32:29.380084+00:00",
  "updated_at": null,
  
  // Array piatto - tutti i workouts (compatibilità)
  "workouts": [
    {
      "id": 189,
      "plan_id": 25,
      "title": "Swim",
      "type": "Swim",
      "scheduled_date": "2025-11-02",
      "duration_minutes": 45,
      "intensity": "Z2",
      "zone": "Z2",
      "status": "scheduled",
      "sessions": [],
      "strava_activity": null
    }
    // ... altri workouts
  ],
  
  // Array raggruppato per settimana (NUOVO)
  "workouts_by_week": [
    {
      "week_number": 1,
      "week_start_date": "2025-11-02",
      "week_end_date": "2025-11-08",
      "workouts": [
        {
          "id": 189,
          "title": "Swim",
          "type": "Swim",
          "scheduled_date": "2025-11-02",
          "duration_minutes": 45,
          "intensity": "Z2",
          "status": "scheduled",
          "sessions": [],
          "strava_activity": null
        }
        // ... altri workouts della settimana 1
      ]
    },
    {
      "week_number": 2,
      "week_start_date": "2025-11-09",
      "week_end_date": "2025-11-15",
      "workouts": [
        // ... workouts della settimana 2
      ]
    }
  ],
  
  "total_workouts": 8,
  "completed_workouts": 0,
  "skipped_workouts": 0,
  "scheduled_workouts": 8,
  "workouts_with_strava": 0
}
```

**Nota Importante:** 
- `workouts`: Array piatto con tutti i workouts (per compatibilità con codice esistente)
- `workouts_by_week`: Array raggruppato per settimana (usa questo per visualizzazioni settimanali)

---

### 3. Generare la Prossima Settimana

**Endpoint:** `POST /workouts/plans/adapt-next-week`

**Request Body:**
```json
{
  "target_date": "2025-12-24"
}
```

**Response:**
```json
{
  "week": 2,
  "focus": "Base Building",
  "adaptations": {
    "intensity_change": "+5%",
    "volume_change": "+10%",
    "rationale": "Previous week completed successfully, ready for progression"
  },
  "workouts": [
    {
      "type": "Swim",
      "duration_minutes": 45,
      "intensity": "Z2",
      "description": "Easy swim technique work",
      "day": "Monday",
      "rpe_target": 6
    }
    // ... altri workouts
  ],
  "recovery_notes": "Maintain consistent sleep schedule",
  "next_week_preview": "Introduce brick training sessions",
  "generated_at": "2025-11-03T16:17:07.539938",
  "adaptation_rationale": "User completed previous week successfully, ready for progression",
  "week_start_date": "2025-11-09",
  "week_end_date": "2025-11-15"
}
```

**Quando chiamarlo:**
- Tipicamente la **domenica** per preparare la settimana successiva
- Dopo aver completato tutti gli allenamenti della settimana corrente
- Quando l'utente preme il bottone "Genera Prossima Settimana"

---

### 4. Verificare se si può Generare la Prossima Settimana

**Endpoint:** `GET /workouts/plans/can-generate-next-week`

**Response:**
```json
{
  "can_generate": false,
  "reason": "Next week already generated",
  "current_week": 1,
  "next_week": 2,
  "next_week_already_generated": true,
  "next_week_workouts_count": 4,
  "next_week_start_date": "2025-11-09",
  "next_week_end_date": "2025-11-15"
}
```

**Quando `can_generate: false`:**
- La prossima settimana è già stata generata
- Disabilita il bottone "Genera Prossima Settimana"

**Quando `can_generate: true`:**
- La prossima settimana non è ancora stata generata
- Abilita il bottone "Genera Prossima Settimana"

---

### 5. Ottenere Dati della Settimana Corrente

**Endpoint:** `GET /workouts/plans/current-week`

**Response:**
```json
{
  "current_week": {
    "week_number": 1,
    "workouts": [
      {
        "id": 189,
        "title": "Swim",
        "type": "Swim",
        "scheduled_date": "2025-11-02",
        "duration_minutes": 45,
        "intensity": "Z2",
        "status": "scheduled"
      }
      // ... altri workouts
    ],
    "performance": {
      "total_sessions": 0,
      "avg_rpe": 0,
      "total_duration": 0
    },
    "week_start": "2025-11-02",
    "week_end": "2025-11-08"
  },
  "fitness_level": {
    "completion_rate": 100,
    "avg_intensity": 5.0,
    "consistency": 80,
    "fatigue_level": "low",
    "performance_trend": "stable",
    "last_week_rpe": 6.0
  }
}
```

---

### 6. Analisi Performance

**Endpoint:** `GET /workouts/plans/performance-analysis?weeks_back=4`

**Response:**
```json
{
  "completion_rate": 95.0,
  "intensity_trend": "increasing",
  "recovery_indicators": {
    "avg_sleep_quality": 7.5,
    "fatigue_score": 3.2,
    "recovery_time": "normal"
  },
  "performance_improvement": 8.5,
  "fatigue_level": "low",
  "avg_rpe": 6.2,
  "consistency_score": 90.0
}
```

---

## Struttura Dati

### Piano Progressivo vs Non Progressivo

**Identificazione:**
- Campo `is_progressive: true/false` presente in tutti gli endpoint che restituiscono piani

**Differenze nella struttura:**
- **Piani Progressivi**: I workouts vengono generati settimana per settimana
- **Piani Non Progressivi**: Tutti i workouts vengono generati all'inizio

**Entrambi i tipi di piano** hanno:
- `workouts`: Array piatto (compatibilità)
- `workouts_by_week`: Array raggruppato per settimana

---

## Workflow UI

### 1. Creazione Piano Progressivo

```
[Schermata Creazione Piano]
┌─────────────────────────────────────┐
│ Tipo Piano: [ ] Tradizionale       │
│          [✓] Progressivo            │
│                                     │
│ Data Obiettivo: [2025-12-24]       │
│ Data Inizio:    [2025-11-02]       │
│ Ore Settimanali: [8.0]             │
│                                     │
│ [Crea Piano]                        │
└─────────────────────────────────────┘
```

**Dopo la creazione:**
- Mostra la prima settimana generata
- Mostra il bottone "Genera Prossima Settimana" (disabilitato fino a domenica)

---

### 2. Visualizzazione Piano Progressivo

```
[Pagina Dettaglio Piano]
┌─────────────────────────────────────┐
│ Triathlon - Ironman 70.3            │
│ Progressivo • Settimana 1 di 7      │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ SETTIMANA 1                      │ │
│ │ 2-8 Nov 2025                     │ │
│ │ Focus: Base Building             │ │
│ │                                   │ │
│ │ [Lun] Swim - 45min - Z2          │ │
│ │ [Mar] Bike - 60min - Z2          │ │
│ │ [Mer] Run - 30min - Z2           │ │
│ │ [Gio] Recovery - 30min - Z1     │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ SETTIMANA 2                      │ │
│ │ 9-15 Nov 2025                    │ │
│ │ [Generata]                       │ │
│ │                                   │ │
│ │ [Lun] Swim - 45min - Z2          │ │
│ │ [Mar] Bike - 60min - Z2          │ │
│ │ ...                               │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ SETTIMANA 3                      │ │
│ │ 16-22 Nov 2025                   │ │
│ │ [Non ancora generata]            │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [Genera Prossima Settimana]         │
│ (Abilitato/Disabilitato)            │
└─────────────────────────────────────┘
```

---

### 3. Gestione Bottone "Genera Prossima Settimana"

**Logica:**
```javascript
// 1. Chiama endpoint per verificare stato
const canGenerate = await fetch('/workouts/plans/can-generate-next-week');

// 2. Se can_generate: true
if (canGenerate.can_generate) {
  // Mostra bottone abilitato
  button.disabled = false;
  button.textContent = "Genera Prossima Settimana";
}

// 3. Se can_generate: false
else {
  // Mostra bottone disabilitato con messaggio
  button.disabled = true;
  button.textContent = `Settimana ${canGenerate.next_week} già generata`;
}
```

**Quando chiamare `adapt-next-week`:**
```javascript
async function generateNextWeek() {
  try {
    const response = await fetch('/workouts/plans/adapt-next-week', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_date: plan.target_date  // Dal piano attivo
      })
    });
    
    const nextWeek = await response.json();
    
    // Mostra notifica
    showNotification(`Settimana ${nextWeek.week} generata! Focus: ${nextWeek.focus}`);
    
    // Ricarica i dettagli del piano per vedere i nuovi workouts
    await refreshPlanDetails();
    
    // Aggiorna lo stato del bottone
    await updateGenerateButtonState();
    
  } catch (error) {
    showError('Errore nella generazione della settimana');
  }
}
```

---

## Esempi di Implementazione

### React/Vue Component: Piano Progressivo

```jsx
// ProgressivePlanView.jsx
import { useState, useEffect } from 'react';

function ProgressivePlanView({ planId }) {
  const [plan, setPlan] = useState(null);
  const [canGenerate, setCanGenerate] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPlanDetails();
    checkCanGenerate();
  }, [planId]);

  async function loadPlanDetails() {
    const response = await fetch(`/workouts/plans/${planId}`);
    const data = await response.json();
    setPlan(data);
    setLoading(false);
  }

  async function checkCanGenerate() {
    const response = await fetch('/workouts/plans/can-generate-next-week');
    const data = await response.json();
    setCanGenerate(data.can_generate);
  }

  async function handleGenerateNextWeek() {
    const response = await fetch('/workouts/plans/adapt-next-week', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_date: plan.end_date
      })
    });
    
    if (response.ok) {
      await loadPlanDetails();
      await checkCanGenerate();
      alert('Prossima settimana generata con successo!');
    }
  }

  if (loading) return <div>Caricamento...</div>;
  if (!plan) return <div>Piano non trovato</div>;

  return (
    <div>
      <h1>{plan.title}</h1>
      <p>Piano {plan.is_progressive ? 'Progressivo' : 'Tradizionale'}</p>
      
      {/* Visualizza workouts raggruppati per settimana */}
      {plan.workouts_by_week.map(week => (
        <WeekCard key={week.week_number} week={week} />
      ))}
      
      {/* Bottone genera prossima settimana (solo per piani progressivi) */}
      {plan.is_progressive && (
        <button 
          onClick={handleGenerateNextWeek}
          disabled={!canGenerate}
        >
          {canGenerate 
            ? 'Genera Prossima Settimana' 
            : 'Prossima Settimana Già Generata'
          }
        </button>
      )}
    </div>
  );
}

function WeekCard({ week }) {
  return (
    <div className="week-card">
      <h3>
        Settimana {week.week_number}
        {week.week_start_date && (
          <span>
            {' '}• {formatDate(week.week_start_date)} - {formatDate(week.week_end_date)}
          </span>
        )}
      </h3>
      <div className="workouts-list">
        {week.workouts.map(workout => (
          <WorkoutItem key={workout.id} workout={workout} />
        ))}
      </div>
    </div>
  );
}
```

---

### Vue.js Component

```vue
<template>
  <div class="progressive-plan">
    <div class="plan-header">
      <h1>{{ plan.title }}</h1>
      <span class="badge" :class="plan.is_progressive ? 'progressive' : 'traditional'">
        {{ plan.is_progressive ? 'Progressivo' : 'Tradizionale' }}
      </span>
    </div>

    <!-- Workouts raggruppati per settimana -->
    <div v-for="week in plan.workouts_by_week" :key="week.week_number" class="week-section">
      <div class="week-header">
        <h2>Settimana {{ week.week_number }}</h2>
        <span v-if="week.week_start_date" class="week-dates">
          {{ formatDate(week.week_start_date) }} - {{ formatDate(week.week_end_date) }}
        </span>
      </div>
      
      <div class="workouts-grid">
        <WorkoutCard 
          v-for="workout in week.workouts" 
          :key="workout.id"
          :workout="workout"
        />
      </div>
    </div>

    <!-- Bottone genera prossima settimana -->
    <button 
      v-if="plan.is_progressive"
      @click="generateNextWeek"
      :disabled="!canGenerateNextWeek"
      class="generate-button"
    >
      {{ canGenerateNextWeek ? 'Genera Prossima Settimana' : 'Settimana Già Generata' }}
    </button>
  </div>
</template>

<script>
export default {
  data() {
    return {
      plan: null,
      canGenerateNextWeek: false,
      loading: true
    }
  },
  
  async mounted() {
    await this.loadPlan();
    await this.checkCanGenerate();
  },
  
  methods: {
    async loadPlan() {
      const response = await this.$axios.get(`/workouts/plans/${this.$route.params.id}`);
      this.plan = response.data;
      this.loading = false;
    },
    
    async checkCanGenerate() {
      const response = await this.$axios.get('/workouts/plans/can-generate-next-week');
      this.canGenerateNextWeek = response.data.can_generate;
    },
    
    async generateNextWeek() {
      try {
        await this.$axios.post('/workouts/plans/adapt-next-week', {
          target_date: this.plan.end_date
        });
        
        this.$toast.success('Prossima settimana generata!');
        await this.loadPlan();
        await this.checkCanGenerate();
      } catch (error) {
        this.$toast.error('Errore nella generazione');
      }
    },
    
    formatDate(dateString) {
      return new Date(dateString).toLocaleDateString('it-IT');
    }
  }
}
</script>
```

---

## Gestione Stati

### Stato del Bottone "Genera Prossima Settimana"

```javascript
// Hook personalizzato per gestire lo stato
function useNextWeekGeneration(plan) {
  const [canGenerate, setCanGenerate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [nextWeekInfo, setNextWeekInfo] = useState(null);

  useEffect(() => {
    if (!plan || !plan.is_progressive) {
      setLoading(false);
      return;
    }

    async function checkStatus() {
      try {
        const response = await fetch('/workouts/plans/can-generate-next-week');
        const data = await response.json();
        
        setCanGenerate(data.can_generate);
        setNextWeekInfo({
          currentWeek: data.current_week,
          nextWeek: data.next_week,
          nextWeekStart: data.next_week_start_date,
          nextWeekEnd: data.next_week_end_date,
          alreadyGenerated: data.next_week_already_generated
        });
      } catch (error) {
        console.error('Error checking next week status:', error);
      } finally {
        setLoading(false);
      }
    }

    checkStatus();
    
    // Ricontrolla ogni minuto (opzionale)
    const interval = setInterval(checkStatus, 60000);
    return () => clearInterval(interval);
  }, [plan]);

  return { canGenerate, loading, nextWeekInfo };
}
```

---

### Polling Automatico (Opzionale)

Se vuoi aggiornare automaticamente lo stato del bottone:

```javascript
// Aggiorna ogni 30 secondi
useEffect(() => {
  const interval = setInterval(() => {
    checkCanGenerate();
  }, 30000);
  
  return () => clearInterval(interval);
}, []);
```

---

## Best Practices Frontend

### 1. Visualizzazione Workouts

**Usa `workouts_by_week` per:**
- Vista a settimana (tabs, accordion, ecc.)
- Calendario settimanale
- Statistiche per settimana

**Usa `workouts` per:**
- Lista completa piana
- Ricerca/filtri
- Compatibilità con componenti esistenti

### 2. Gestione Errori

```javascript
async function generateNextWeek() {
  try {
    const response = await fetch('/workouts/plans/adapt-next-week', {
      method: 'POST',
      body: JSON.stringify({ target_date })
    });
    
    if (!response.ok) {
      const error = await response.json();
      
      if (response.status === 404) {
        // Nessun piano attivo
        showError('Nessun piano attivo trovato');
      } else {
        showError(error.detail || 'Errore nella generazione');
      }
      return;
    }
    
    // Successo
    const nextWeek = await response.json();
    showSuccess(`Settimana ${nextWeek.week} generata!`);
    
  } catch (error) {
    showError('Errore di connessione');
  }
}
```

### 3. Loading States

```javascript
const [generating, setGenerating] = useState(false);

async function generateNextWeek() {
  setGenerating(true);
  try {
    // ... chiamata API
  } finally {
    setGenerating(false);
  }
}

// Nel bottone
<button disabled={!canGenerate || generating}>
  {generating ? 'Generazione...' : 'Genera Prossima Settimana'}
</button>
```

---

## Esempio Completo: Flusso Utente

### Scenario: Utente con Piano Progressivo

1. **Domenica Sera** - Utente completa l'ultimo allenamento della settimana 1
2. **Lunedì** - Utente apre l'app
   - Chiama `GET /workouts/plans/can-generate-next-week`
   - Risposta: `can_generate: true`
   - Bottone "Genera Prossima Settimana" è **abilitato**
3. **Lunedì** - Utente preme il bottone
   - Chiama `POST /workouts/plans/adapt-next-week`
   - Risposta: Settimana 2 generata con 4 workouts
   - Workouts salvati nel database
   - Ricarica dettagli piano: `GET /workouts/plans/{id}`
   - Ora `workouts_by_week` contiene settimana 1 e settimana 2
4. **Martedì** - Utente apre l'app
   - Chiama `GET /workouts/plans/can-generate-next-week`
   - Risposta: `can_generate: false` (settimana 2 già generata)
   - Bottone "Genera Prossima Settimana" è **disabilitato**
5. **Domenica Sera** - Utente completa settimana 2
6. **Lunedì** - Bottone si riabilita automaticamente

---

## Checklist Integrazione Frontend

- [ ] Implementare visualizzazione `workouts_by_week` per piani progressivi
- [ ] Aggiungere bottone "Genera Prossima Settimana" (solo per piani progressivi)
- [ ] Implementare chiamata a `/workouts/plans/can-generate-next-week`
- [ ] Gestire stati abilitato/disabilitato del bottone
- [ ] Implementare chiamata a `/workouts/plans/adapt-next-week`
- [ ] Gestire loading states durante la generazione
- [ ] Mostrare notifiche di successo/errore
- [ ] Ricaricare i dettagli del piano dopo la generazione
- [ ] Aggiornare lo stato del bottone dopo la generazione
- [ ] Gestire errori (piano non trovato, nessun piano attivo, ecc.)
- [ ] Mostrare differenza visiva tra settimane generate e non generate
- [ ] Implementare refresh automatico (opzionale)

---

## Note Importanti

1. **Il campo `is_progressive`** è sempre presente nelle risposte dei piani
2. **Entrambi i formati** (`workouts` e `workouts_by_week`) sono sempre presenti
3. **Il bottone "Genera Prossima Settimana"** deve essere mostrato solo per piani progressivi
4. **Verifica sempre** lo stato con `can-generate-next-week` prima di mostrare il bottone
5. **Dopo la generazione**, ricarica sempre i dettagli del piano per vedere i nuovi workouts

---

## Supporto

Per domande o problemi, consulta:
- `/docs/API_DOCUMENTATION.md` - Documentazione completa API
- `/examples/progressive_workout_example.py` - Esempi di utilizzo Python

