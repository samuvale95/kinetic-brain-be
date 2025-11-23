# API Progressive Plans - Data di Inizio Personalizzata

## 📋 Overview

Questa documentazione descrive le modifiche all'API dei piani progressivi per supportare una **data di inizio personalizzata**. Con questa funzionalità, l'utente può specificare qualsiasi giorno della settimana come data di inizio del piano, e la prima settimana sarà generata solo per i giorni disponibili (dalla data di inizio fino alla domenica successiva).

## 🎯 Comportamento

### Prima Settimana Parziale

Quando viene specificata una data di inizio che non è lunedì:
- La **prima settimana** include solo i giorni dalla data di inizio fino alla domenica successiva
- L'AI genera allenamenti **solo** per i giorni disponibili nella prima settimana
- Esempio: se la data di inizio è **mercoledì 5 novembre**, la prima settimana include:
  - Mercoledì 5 novembre
  - Giovedì 6 novembre
  - Venerdì 7 novembre
  - Sabato 8 novembre
  - Domenica 9 novembre

### Settimane Successive

Dalla seconda settimana in poi:
- Le settimane sono sempre **complete** (lunedì-domenica)
- La settimana 2 inizia il lunedì successivo alla domenica della settimana 1
- Esempio: se la settimana 1 finisce domenica 9 novembre, la settimana 2 inizia lunedì 10 novembre

## 📡 Modifiche API

### Endpoint: `POST /workouts/plans/generate-progressive`

Il campo `start_date` è già presente nella richiesta e ora viene utilizzato per:
1. Calcolare i giorni disponibili nella prima settimana
2. Generare allenamenti solo per quei giorni
3. Allineare correttamente le date dei workout

**Request Body (invariato):**
```json
{
  "sport_type": "triathlon",
  "level": "intermediate",
  "goal": "Ironman 70.3",
  "target_date": "2025-12-24",
  "start_date": "2025-11-05",  // ← Può essere qualsiasi giorno della settimana
  "weekly_hours": 8.0,
  "user_profile": { ... },
  "include_stretching": false,
  "include_strength": false,
  "unavailable_days": null,
  "sport_specific_days": null
}
```

**Response (invariata):**
```json
{
  "plan": {
    "id": 25,
    "start_date": "2025-11-05",  // ← Data di inizio effettiva
    "end_date": "2025-12-24",
    ...
  },
  "first_week": {
    "week": 1,
    "focus": "Base Building",
    "workouts": [
      {
        "day": "Wednesday",  // ← Solo giorni dalla data di inizio
        "type": "Swim",
        "duration_minutes": 45,
        "intensity": "Z2"
      },
      {
        "day": "Thursday",
        "type": "Bike",
        "duration_minutes": 60,
        "intensity": "Z2"
      }
      // ... altri workouts solo per mercoledì-domenica
    ],
    "week_start_date": "2025-11-05",
    "week_end_date": "2025-11-09"  // ← Domenica della prima settimana
  }
}
```

## 🔧 Integrazione Frontend

### 1. Selezione Data di Inizio

Il frontend deve permettere all'utente di selezionare una data di inizio. Non ci sono restrizioni sul giorno della settimana.

**Esempio UI:**
```javascript
// Componente di selezione data
<DatePicker
  label="Data di inizio allenamento"
  value={startDate}
  onChange={setStartDate}
  minDate={new Date()} // Non può essere nel passato
  // Non ci sono restrizioni sul giorno della settimana
/>
```

### 2. Visualizzazione Prima Settimana

Quando si visualizza la prima settimana, mostrare chiaramente che è una settimana parziale:

```javascript
// Esempio React component
function WeekView({ week, weekNumber, planStartDate }) {
  const isFirstWeek = weekNumber === 1;
  const startDate = new Date(planStartDate);
  const isPartialWeek = isFirstWeek && startDate.getDay() !== 1; // 1 = lunedì
  
  if (isPartialWeek) {
    const startWeekday = startDate.getDay();
    const dayNames = ['Domenica', 'Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato'];
    const startDayName = dayNames[startWeekday];
    
    return (
      <div className="week-container">
        <div className="week-header">
          <h3>Settimana {weekNumber} - Parziale</h3>
          <p className="info-text">
            Questa settimana inizia {startDayName} e include solo i giorni fino a domenica
          </p>
        </div>
        {/* Render workouts */}
      </div>
    );
  }
  
  // Settimana completa normale
  return (
    <div className="week-container">
      <div className="week-header">
        <h3>Settimana {weekNumber}</h3>
      </div>
      {/* Render workouts */}
    </div>
  );
}
```

### 3. Calcolo Date Workout

I workout nella risposta API hanno il campo `day` (es. "Wednesday"), ma le date effettive sono calcolate dal backend. Il frontend può usare i metadati `week_start_date` e `week_end_date` per validare:

```javascript
function calculateWorkoutDate(weekStartDate, dayName) {
  const dayMapping = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
  };
  
  const startDate = new Date(weekStartDate);
  const dayOffset = dayMapping[dayName];
  const workoutDate = new Date(startDate);
  workoutDate.setDate(startDate.getDate() + dayOffset);
  
  return workoutDate;
}
```

### 4. Validazione e Feedback

Quando l'utente seleziona una data di inizio, il frontend può mostrare un messaggio informativo:

```javascript
function StartDateSelector({ startDate, onChange }) {
  const date = new Date(startDate);
  const weekday = date.getDay();
  const dayNames = ['Domenica', 'Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato'];
  
  const isMonday = weekday === 1;
  const dayName = dayNames[weekday];
  
  return (
    <div>
      <DatePicker value={startDate} onChange={onChange} />
      {!isMonday && (
        <div className="info-banner">
          <InfoIcon />
          <p>
            La prima settimana inizierà {dayName} e includerà solo i giorni fino a domenica.
            Le settimane successive saranno complete (lunedì-domenica).
          </p>
        </div>
      )}
    </div>
  );
}
```

## 📊 Esempi Pratici

### Esempio 1: Inizio Mercoledì

**Input:**
- `start_date`: "2025-11-05" (mercoledì)
- `target_date`: "2025-12-24"

**Risultato:**
- **Settimana 1** (parziale): 5-9 novembre (mercoledì-domenica)
  - 4-5 allenamenti generati solo per questi giorni
- **Settimana 2** (completa): 10-16 novembre (lunedì-domenica)
- **Settimana 3** (completa): 17-23 novembre (lunedì-domenica)
- E così via...

### Esempio 2: Inizio Lunedì

**Input:**
- `start_date`: "2025-11-03" (lunedì)
- `target_date`: "2025-12-24"

**Risultato:**
- **Settimana 1** (completa): 3-9 novembre (lunedì-domenica)
- **Settimana 2** (completa): 10-16 novembre (lunedì-domenica)
- Comportamento normale, nessuna differenza

### Esempio 3: Inizio Domenica

**Input:**
- `start_date`: "2025-11-02" (domenica)
- `target_date`: "2025-12-24"

**Risultato:**
- **Settimana 1** (parziale): 2 novembre (solo domenica)
  - 1 allenamento generato per domenica
- **Settimana 2** (completa): 3-9 novembre (lunedì-domenica)

## ⚠️ Note Importanti

1. **Consistenza Date**: Le date effettive dei workout sono sempre calcolate dal backend e salvate nel campo `scheduled_date` del workout. Il campo `day` (es. "Wednesday") è solo indicativo.

2. **Settimane Successive**: Dalla settimana 2 in poi, tutte le settimane sono sempre complete (lunedì-domenica), indipendentemente dalla data di inizio del piano.

3. **Generazione AI**: L'AI riceve istruzioni esplicite per generare allenamenti solo per i giorni disponibili nella prima settimana. Non vengono generati allenamenti per giorni prima della data di inizio.

4. **Compatibilità**: Questa modifica è **retrocompatibile**. Se `start_date` non viene fornito o è lunedì, il comportamento è identico a prima.

## 🔍 Debugging

Se ci sono problemi con le date dei workout:

1. Verifica che `start_date` nella richiesta corrisponda alla data di inizio del piano nel database
2. Controlla i log del backend per vedere quali giorni sono stati calcolati come disponibili
3. Verifica che i workout nella risposta API abbiano solo giorni dalla data di inizio fino a domenica per la settimana 1

**Log Backend:**
```
[PROGRESSIVE] First week partial: start_date=2025-11-05, available_days=['Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
[WORKOUT_SERVICE] Week 1 start date: 2025-11-05, start_weekday: 2
```

## 📝 Changelog

- **2025-11-23**: Aggiunto supporto per data di inizio personalizzata
  - Prima settimana può iniziare da qualsiasi giorno della settimana
  - Prima settimana include solo giorni dalla data di inizio a domenica
  - Settimane successive sempre complete (lunedì-domenica)
  - AI genera allenamenti solo per giorni disponibili nella prima settimana

