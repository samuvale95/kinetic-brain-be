# Guida API Diario (Readiness Diary)

Questa guida spiega come implementare l'integrazione con l'API del diario per la gestione dei dati di readiness giornalieri.

## Endpoint Disponibili

### POST `/metrics/diary`
Endpoint per creare o aggiornare una voce di diario giornaliero. **Solo il giorno di oggi può essere modificato**. I giorni passati sono in sola lettura.

### GET `/metrics/diary`
Endpoint per recuperare **tutti i record del diario compilati** (solo giorni con dati inseriti e completati). I record sono ordinati dal più recente al più vecchio per permettere la visualizzazione come lista. Un record è considerato "completato" se ha almeno un dato inserito (es. hrv_value, rhr_value, sleep_hours, notes, ecc.).

### GET `/metrics/diary/{target_date}`
Endpoint per recuperare un singolo record del diario per una data specifica.

---

## POST `/metrics/diary`

Endpoint per creare o aggiornare una voce di diario giornaliero. Se esiste già una voce per la data specificata (o per oggi se non specificata), viene aggiornata; altrimenti viene creata una nuova voce.

**⚠️ IMPORTANTE**: Solo il giorno di oggi può essere modificato. Tentare di modificare un giorno passato restituirà un errore 403 Forbidden.

### Autenticazione

Richiede autenticazione Bearer token. Includere l'header:
```
Authorization: Bearer <token>
```

## Request Body

### Schema

```typescript
interface DiaryEntryRequest {
  date?: string;                    // Data in formato YYYY-MM-DD (opzionale, default: oggi)
  hrv_value?: number;               // Valore HRV (Heart Rate Variability)
  rhr_value?: number;               // Valore RHR (Resting Heart Rate)
  sleep_hours?: number;             // Ore di sonno
  sleep_quality_score?: number;     // Qualità del sonno (0-10)
  epoc?: number;                    // EPOC (Excess Post-Exercise Oxygen Consumption)
  hydration_status?: string;        // Stato di idratazione
  hydration_score?: number;         // Punteggio idratazione
  nutrition_score?: number;         // Punteggio nutrizione
  weight_delta_kg?: number;         // Variazione peso in kg
  perceived_exertion?: number;      // Percezione dello sforzo (1-10)
  notes?: string;                   // Note aggiuntive
}
```

### Campi Dettagliati

| Campo | Tipo | Obbligatorio | Descrizione | Validazione |
|-------|------|--------------|-------------|-------------|
| `date` | string | No | Data del diario in formato ISO (YYYY-MM-DD). Se omesso, usa la data odierna | Formato: YYYY-MM-DD |
| `hrv_value` | number | No | Variabilità della frequenza cardiaca (HRV) | Numero decimale |
| `rhr_value` | number | No | Frequenza cardiaca a riposo (RHR) | Numero decimale |
| `sleep_hours` | number | No | Ore di sonno della notte precedente | Numero decimale (es. 7.5) |
| `sleep_quality_score` | number | No | Punteggio qualità del sonno | 0-10 |
| `epoc` | number | No | EPOC (Excess Post-Exercise Oxygen Consumption) | Numero decimale |
| `hydration_status` | string | No | Stato di idratazione (testo libero) | Stringa |
| `hydration_score` | number | No | Punteggio idratazione | Numero decimale |
| `nutrition_score` | number | No | Punteggio nutrizione | Numero decimale |
| `weight_delta_kg` | number | No | Variazione peso rispetto al giorno precedente | Numero decimale (può essere negativo) |
| `perceived_exertion` | number | No | Percezione dello sforzo (RPE - Rate of Perceived Exertion) | Intero 1-10 |
| `notes` | string | No | Note aggiuntive libere | Stringa |

## Response

### Success Response (200 OK)

```typescript
interface DiaryEntryResponse {
  success: boolean;           // Sempre true in caso di successo
  date: string;              // Data della voce (formato YYYY-MM-DD)
  readiness_state?: string;   // Stato di readiness calcolato
  recovery_index?: number;    // Indice di recupero calcolato (0-100)
}
```

#### Valori Possibili di `readiness_state`

Il campo `readiness_state` può assumere i seguenti valori:
- `"ready"`: Pronto per allenarsi
- `"fatigued"`: Affaticato, necessita recupero
- `"recovering"`: In fase di recupero
- `null`: Stato non ancora calcolato o dati insufficienti

#### `recovery_index`

Il campo `recovery_index` è un valore numerico tra 0 e 100 che indica il livello di recupero:
- **0-30**: Recupero insufficiente, evitare allenamenti intensi
- **31-60**: Recupero parziale, allenamenti leggeri consigliati
- **61-80**: Recupero buono, allenamenti moderati possibili
- **81-100**: Recupero completo, pronti per allenamenti intensi

### Error Responses

#### 400 Bad Request - Formato data non valido
```json
{
  "detail": "Invalid date format. Use YYYY-MM-DD"
}
```

#### 401 Unauthorized - Token mancante o non valido
```json
{
  "detail": "Missing or invalid authorization header"
}
```

#### 403 Forbidden - Tentativo di modificare un giorno passato
```json
{
  "detail": "Cannot modify diary entries for past dates. Only today (2025-11-17) can be edited."
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Esempi di Utilizzo

### Esempio 1: Inserimento completo

```typescript
// TypeScript/JavaScript
const response = await fetch('http://localhost:8000/metrics/diary', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    date: '2025-11-16',
    hrv_value: 45.5,
    rhr_value: 52,
    sleep_hours: 7.5,
    sleep_quality_score: 8,
    epoc: 120,
    hydration_score: 85,
    nutrition_score: 90,
    weight_delta_kg: -0.2,
    perceived_exertion: 6,
    notes: 'Buona giornata, sonno ristoratore'
  })
});

const data = await response.json();
console.log('Readiness State:', data.readiness_state);
console.log('Recovery Index:', data.recovery_index);
```

### Esempio 2: Aggiornamento parziale (solo alcuni campi)

```typescript
// Aggiorna solo sonno e HRV per oggi
const response = await fetch('http://localhost:8000/metrics/diary', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    sleep_hours: 8.0,
    sleep_quality_score: 9,
    hrv_value: 50.2
  })
});
```

### Esempio 3: Inserimento minimo

```typescript
// Solo i dati essenziali
const response = await fetch('http://localhost:8000/metrics/diary', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    sleep_hours: 7.0,
    perceived_exertion: 5
  })
});
```

### Esempio 4: Con gestione errori

```typescript
async function saveDiaryEntry(entryData: DiaryEntryRequest): Promise<DiaryEntryResponse> {
  try {
    const response = await fetch('http://localhost:8000/metrics/diary', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getAuthToken()}`
      },
      body: JSON.stringify(entryData)
    });

    if (!response.ok) {
      if (response.status === 400) {
        const error = await response.json();
        throw new Error(`Formato data non valido: ${error.detail}`);
      }
      if (response.status === 401) {
        throw new Error('Token non valido. Effettua il login.');
      }
      throw new Error(`Errore server: ${response.status}`);
    }

    const data: DiaryEntryResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Errore nel salvataggio del diario:', error);
    throw error;
  }
}

// Utilizzo
try {
  const result = await saveDiaryEntry({
    date: '2025-11-16',
    sleep_hours: 7.5,
    hrv_value: 45.0,
    perceived_exertion: 6
  });
  
  console.log('Diario salvato:', result);
  console.log('Stato readiness:', result.readiness_state);
} catch (error) {
  console.error('Errore:', error.message);
}
```

## GET `/metrics/diary`

Endpoint per recuperare tutti i record del diario compilati (solo giorni con dati inseriti e completati). I record sono ordinati dal più recente al più vecchio, permettendo la visualizzazione come lista. 

**⚠️ IMPORTANTE**: Vengono mostrati solo i giorni per i quali è stato completato il diario (almeno un dato inserito). I giorni senza dati non vengono inclusi nella lista.

### Autenticazione

Richiede autenticazione Bearer token. Includere l'header:
```
Authorization: Bearer <token>
```

### Response

```typescript
interface DiaryEntriesResponse {
  entries: DiaryEntryDetailResponse[];
  total_entries: number;  // Numero totale di record compilati
}

interface DiaryEntryDetailResponse {
  date: string;              // YYYY-MM-DD
  day_name: string;          // Nome del giorno (es. "Lunedì 16 Novembre 2025")
  is_editable: boolean;      // True solo se è oggi (modificabile), False per giorni passati (sola lettura)
  hrv_value?: number;
  hrv_baseline?: number;
  hrv_delta?: number;
  rhr_value?: number;
  rhr_baseline?: number;
  rhr_delta?: number;
  sleep_hours?: number;
  sleep_quality_score?: number;
  epoc?: number;
  hydration_status?: string;
  hydration_score?: number;
  nutrition_score?: number;
  weight_delta_kg?: number;
  perceived_exertion?: number;  // 1-10
  notes?: string;
  recovery_index?: number;
  readiness_state?: string;     // "ready", "caution", "rest"
}
```

### Esempio di Utilizzo

```typescript
const response = await fetch('http://localhost:8000/metrics/diary', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const data: DiaryEntriesResponse = await response.json();

// I record sono già ordinati dal più recente al più vecchio
data.entries.forEach(entry => {
  console.log(`${entry.day_name} - ${entry.is_editable ? 'Modificabile' : 'Sola lettura'}`);
  console.log(`Recovery Index: ${entry.recovery_index}`);
  console.log(`Readiness State: ${entry.readiness_state}`);
});
```

### Comportamento

1. **Solo giorni completati**: L'endpoint restituisce solo i giorni in cui è stato completato il diario. Un record è considerato "completato" se ha almeno uno dei seguenti campi compilati:
   - `hrv_value`, `rhr_value`, `sleep_hours`, `sleep_quality_score`, `epoc`
   - `hydration_status`, `hydration_score`, `nutrition_score`, `weight_delta_kg`
   - `notes`
   I giorni senza dati inseriti non vengono inclusi nella lista.

2. **Ordinamento**: I record sono ordinati dal più recente al più vecchio (`metric_date DESC`), permettendo la visualizzazione come lista semplice.

3. **Flag `is_editable`**: 
   - `true` se il record è per il giorno di oggi (modificabile)
   - `false` se il record è per un giorno passato (sola lettura)

4. **Nome del giorno**: Il campo `day_name` contiene il nome completo del giorno in italiano (es. "Lunedì 16 Novembre 2025").

## GET `/metrics/diary/{target_date}`

Endpoint per recuperare un singolo record del diario per una data specifica.

### Autenticazione

Richiede autenticazione Bearer token.

### Parametri Path

- `target_date`: Data in formato `YYYY-MM-DD` (es. `2025-11-17`)

### Response

Restituisce un singolo `DiaryEntryDetailResponse` o un errore 404 se il record non esiste.

### Esempio di Utilizzo

```typescript
const targetDate = '2025-11-17';
const response = await fetch(`http://localhost:8000/metrics/diary/${targetDate}`, {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

if (response.status === 404) {
  console.log('Record non trovato per questa data');
} else {
  const entry: DiaryEntryDetailResponse = await response.json();
  console.log(entry);
}
```

## Comportamento dell'Endpoint POST

1. **Creazione vs Aggiornamento**: L'endpoint crea una nuova voce se non esiste per la data specificata, altrimenti aggiorna quella esistente (upsert).

2. **Data di default**: Se il campo `date` non viene fornito, viene utilizzata la data odierna del server.

3. **Solo oggi modificabile**: Tentare di modificare un giorno passato restituirà un errore 403 Forbidden. Solo il giorno di oggi può essere modificato.

4. **Campi opzionali**: Tutti i campi sono opzionali. Puoi inviare solo i campi che vuoi aggiornare.

5. **Calcolo automatico**: Dopo il salvataggio, il sistema calcola automaticamente:
   - `readiness_state`: Stato di readiness basato sui dati inseriti
   - `recovery_index`: Indice di recupero (0-100)

6. **Validazione**: 
   - Il formato della data deve essere `YYYY-MM-DD`
   - `perceived_exertion` deve essere tra 1 e 10 (se fornito)

## Best Practices per il Frontend

### 1. Form di Input

```typescript
// Esempio form React
const DiaryForm = () => {
  const [formData, setFormData] = useState<DiaryEntryRequest>({
    date: new Date().toISOString().split('T')[0], // Data odierna
    sleep_hours: undefined,
    hrv_value: undefined,
    // ... altri campi
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Rimuovi campi undefined per non inviarli
    const payload = Object.fromEntries(
      Object.entries(formData).filter(([_, v]) => v !== undefined && v !== '')
    );

    try {
      const result = await saveDiaryEntry(payload);
      // Mostra messaggio di successo
      alert(`Diario salvato! Readiness: ${result.readiness_state}`);
    } catch (error) {
      // Gestisci errore
      alert(`Errore: ${error.message}`);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="date"
        value={formData.date}
        onChange={(e) => setFormData({...formData, date: e.target.value})}
      />
      <input
        type="number"
        step="0.1"
        placeholder="Ore di sonno"
        value={formData.sleep_hours || ''}
        onChange={(e) => setFormData({
          ...formData,
          sleep_hours: e.target.value ? parseFloat(e.target.value) : undefined
        })}
      />
      {/* Altri campi... */}
      <button type="submit">Salva</button>
    </form>
  );
};
```

### 2. Validazione Lato Client

```typescript
function validateDiaryEntry(data: DiaryEntryRequest): string[] {
  const errors: string[] = [];

  // Validazione data
  if (data.date) {
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(data.date)) {
      errors.push('Formato data non valido. Usa YYYY-MM-DD');
    }
  }

  // Validazione perceived_exertion
  if (data.perceived_exertion !== undefined) {
    if (data.perceived_exertion < 1 || data.perceived_exertion > 10) {
      errors.push('Percezione dello sforzo deve essere tra 1 e 10');
    }
  }

  // Validazione sleep_quality_score
  if (data.sleep_quality_score !== undefined) {
    if (data.sleep_quality_score < 0 || data.sleep_quality_score > 10) {
      errors.push('Qualità del sonno deve essere tra 0 e 10');
    }
  }

  return errors;
}
```

### 3. Gestione dello Stato

```typescript
// Hook personalizzato per il diario
function useDiaryEntry() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const saveEntry = async (data: DiaryEntryRequest) => {
    setLoading(true);
    setError(null);

    try {
      const validationErrors = validateDiaryEntry(data);
      if (validationErrors.length > 0) {
        throw new Error(validationErrors.join(', '));
      }

      const result = await saveDiaryEntry(data);
      setLoading(false);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore sconosciuto');
      setLoading(false);
      throw err;
    }
  };

  return { saveEntry, loading, error };
}
```

### 4. Aggiornamento in Tempo Reale

```typescript
// Dopo il salvataggio, aggiorna i dati di readiness
const handleSave = async (data: DiaryEntryRequest) => {
  const result = await saveDiaryEntry(data);
  
  // Aggiorna lo stato globale o il context
  updateReadinessData({
    date: result.date,
    readiness_state: result.readiness_state,
    recovery_index: result.recovery_index
  });
  
  // Mostra notifica
  showNotification('Diario salvato con successo!', 'success');
};
```

## Recupero Dati del Diario

Dopo aver salvato una voce nel diario, puoi recuperare i dati di readiness tramite l'endpoint:

**GET** `/metrics/readiness`

### Parametri Query

- `start_date` (opzionale): Data di inizio in formato `YYYY-MM-DD` (default: 28 giorni fa)
- `end_date` (opzionale): Data di fine in formato `YYYY-MM-DD` (default: oggi)
- `grouping` (opzionale): Raggruppamento dei dati - `day`, `week`, `month`, `year` (default: `week`)

### Esempio di Utilizzo

```typescript
// Recupera i dati di readiness degli ultimi 7 giorni
const response = await fetch(
  'http://localhost:8000/metrics/readiness?start_date=2025-11-10&end_date=2025-11-16&grouping=day',
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

const data = await response.json();
// data.series contiene un array di ReadinessSeriesPoint con i dati giornalieri
```

### Response Structure

```typescript
interface ReadinessMetricsResponse {
  metadata: {
    grouping: 'day' | 'week' | 'month' | 'year';
    start_date: string;  // YYYY-MM-DD
    end_date: string;    // YYYY-MM-DD
  };
  series: ReadinessSeriesPoint[];
}

interface ReadinessSeriesPoint {
  period_start: string;        // YYYY-MM-DD
  period_end: string;          // YYYY-MM-DD
  recovery_index?: number;     // 0-100
  readiness_state?: string;     // "ready", "fatigued", "recovering"
  hydration_score?: number;
  nutrition_score?: number;
  hrv?: {
    baseline?: number;
    value?: number;
    delta?: number;
  };
  rhr?: {
    baseline?: number;
    value?: number;
    delta?: number;
  };
  sleep_hours?: number;
  sleep_quality_score?: number;
  epoc?: number;
  injury_risk_score?: number;
}
```

## Integrazione con Altri Endpoint

Il diario è collegato agli endpoint di readiness:

- **GET** `/metrics/readiness`: Ottiene i dati di readiness per un periodo (include i dati del diario)
- **GET** `/metrics/load`: Ottiene i dati di carico di allenamento

Dopo aver salvato una voce nel diario, i dati di readiness vengono ricalcolati automaticamente e saranno disponibili tramite questi endpoint.

## Note Importanti

1. **Formato Data**: Sempre usare il formato `YYYY-MM-DD` (es. `2025-11-16`)

2. **Fuso Orario**: La data viene interpretata nel fuso orario del server. Se non specifichi una data, viene usata la data odierna del server.

3. **Sola Lettura per Giorni Passati**: 
   - Solo il giorno di oggi può essere modificato tramite POST `/metrics/diary`
   - I giorni passati sono visualizzabili in sola lettura tramite GET `/metrics/diary` o GET `/metrics/diary/{date}`
   - Tentare di modificare un giorno passato restituirà un errore 403 Forbidden

4. **Visualizzazione del Diario**:
   - GET `/metrics/diary` restituisce solo i giorni **completati** (con almeno un dato inserito)
   - I giorni senza dati inseriti non vengono mostrati nella lista
   - I record sono ordinati dal più recente al più vecchio per permettere la visualizzazione come lista semplice
   - Ogni record include `day_name` (nome completo del giorno) e `is_editable` (flag per indicare se è modificabile)
   - La lista è semplice, senza frecce o navigazione aggiuntiva

5. **Campi Null vs Undefined**: 
   - I campi `undefined` non vengono inviati al server
   - I campi `null` vengono inviati come `null` (potrebbero sovrascrivere valori esistenti)

6. **Upsert**: L'endpoint POST fa un "upsert" (update or insert), quindi puoi chiamarlo più volte per la stessa data senza creare duplicati (solo se la data è oggi).

## Esempio Completo React

```typescript
import React, { useState } from 'react';

interface DiaryEntryRequest {
  date?: string;
  hrv_value?: number;
  rhr_value?: number;
  sleep_hours?: number;
  sleep_quality_score?: number;
  epoc?: number;
  hydration_status?: string;
  hydration_score?: number;
  nutrition_score?: number;
  weight_delta_kg?: number;
  perceived_exertion?: number;
  notes?: string;
}

interface DiaryEntryResponse {
  success: boolean;
  date: string;
  readiness_state?: string;
  recovery_index?: number;
}

const DiaryEntryForm: React.FC = () => {
  const [formData, setFormData] = useState<DiaryEntryRequest>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DiaryEntryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('http://localhost:8000/metrics/diary', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Errore nel salvataggio');
      }

      const data: DiaryEntryResponse = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore sconosciuto');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Data (YYYY-MM-DD):</label>
          <input
            type="date"
            value={formData.date || ''}
            onChange={(e) => setFormData({...formData, date: e.target.value})}
          />
        </div>

        <div>
          <label>Ore di sonno:</label>
          <input
            type="number"
            step="0.1"
            value={formData.sleep_hours || ''}
            onChange={(e) => setFormData({
              ...formData,
              sleep_hours: e.target.value ? parseFloat(e.target.value) : undefined
            })}
          />
        </div>

        <div>
          <label>Qualità sonno (0-10):</label>
          <input
            type="number"
            min="0"
            max="10"
            step="0.1"
            value={formData.sleep_quality_score || ''}
            onChange={(e) => setFormData({
              ...formData,
              sleep_quality_score: e.target.value ? parseFloat(e.target.value) : undefined
            })}
          />
        </div>

        <div>
          <label>HRV:</label>
          <input
            type="number"
            step="0.1"
            value={formData.hrv_value || ''}
            onChange={(e) => setFormData({
              ...formData,
              hrv_value: e.target.value ? parseFloat(e.target.value) : undefined
            })}
          />
        </div>

        <div>
          <label>RHR:</label>
          <input
            type="number"
            step="0.1"
            value={formData.rhr_value || ''}
            onChange={(e) => setFormData({
              ...formData,
              rhr_value: e.target.value ? parseFloat(e.target.value) : undefined
            })}
          />
        </div>

        <div>
          <label>Percezione sforzo (1-10):</label>
          <input
            type="number"
            min="1"
            max="10"
            value={formData.perceived_exertion || ''}
            onChange={(e) => setFormData({
              ...formData,
              perceived_exertion: e.target.value ? parseInt(e.target.value) : undefined
            })}
          />
        </div>

        <div>
          <label>Note:</label>
          <textarea
            value={formData.notes || ''}
            onChange={(e) => setFormData({...formData, notes: e.target.value})}
          />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? 'Salvataggio...' : 'Salva Diario'}
        </button>
      </form>

      {error && <div style={{color: 'red'}}>Errore: {error}</div>}
      
      {result && (
        <div style={{marginTop: '20px', padding: '10px', background: '#f0f0f0'}}>
          <h3>Risultato:</h3>
          <p>Data: {result.date}</p>
          <p>Stato Readiness: {result.readiness_state || 'N/A'}</p>
          <p>Indice Recupero: {result.recovery_index || 'N/A'}</p>
        </div>
      )}
    </div>
  );
};

export default DiaryEntryForm;
```

## Supporto

Per domande o problemi, consulta:
- Documentazione API completa: `http://localhost:8000/docs`
- Schema OpenAPI: `http://localhost:8000/openapi.json`

