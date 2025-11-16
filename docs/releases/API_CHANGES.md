# Documento: Modifiche API - Migrazione da Weekly Summary a Daily Metrics

## 📋 Riepilogo

Questo documento descrive le modifiche alle API causate dalla migrazione dal sistema di **Weekly Performance Summary** al nuovo sistema di **Daily Performance Metrics**. Il nuovo sistema calcola CTL/ATL/TSB in modo incrementale giorno per giorno, invece che settimana per settimana.

---

## ❌ API Eliminate

### 1. `GET /statistics/weekly-summary`

**Endpoint rimosso**: `/api/statistics/weekly-summary`

**Descrizione**: 
Endpoint che restituiva un riepilogo dettagliato di una settimana specifica, inclusi CTL/ATL/TSB settimanali, workouts completati, e distribuzione delle zone.

**Motivo eliminazione**: 
I dati settimanali vengono ora calcolati come aggregazioni dai dati giornalieri. Non è più necessario mantenere un endpoint dedicato per i riepiloghi settimanali, in quanto i dati possono essere ottenuti aggregando i daily metrics.

**Alternativa**:
- Usare `/statistics/daily-metrics` per ottenere i dati giornalieri e aggregare a livello frontend
- Usare `/statistics/performance-chart` che continua a fornire dati aggregati per settimana

---

## ✅ API Create

### 1. `GET /statistics/daily-metrics`

**Endpoint**: `/api/statistics/daily-metrics`

**Descrizione**: 
Endpoint principale per ottenere le metriche giornaliere di performance (CTL/ATL/TSB) per un periodo specifico. I dati vengono calcolati in modo incrementale giorno per giorno.

**Metodo**: `GET`

**Autenticazione**: Richiesta (token JWT tramite header `Authorization`)

**Query Parameters**:

| Parametro | Tipo | Richiesto | Default | Descrizione |
|-----------|------|-----------|---------|-------------|
| `start_date` | string | No | 84 giorni fa | Data di inizio (formato: `YYYY-MM-DD`) |
| `end_date` | string | No | oggi | Data di fine (formato: `YYYY-MM-DD`) |

**Esempio Request**:
```http
GET /api/statistics/daily-metrics?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer <token>
```

**Response Success (200)**:

```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "metrics": [
    {
      "date": "2024-01-01",
      "daily_tss": 45.5,
      "ctl": 52.3,
      "atl": 48.7,
      "tsb": 3.6,
      "activities_count": 1
    },
    {
      "date": "2024-01-02",
      "daily_tss": 0.0,
      "ctl": 51.8,
      "atl": 45.2,
      "tsb": 6.6,
      "activities_count": 0
    },
    {
      "date": "2024-01-03",
      "daily_tss": 78.2,
      "ctl": 53.1,
      "atl": 52.4,
      "tsb": 0.7,
      "activities_count": 1
    }
    // ... altri giorni
  ]
}
```

**Response Fields**:

- `start_date` (string): Data di inizio del periodo richiesto (ISO format: `YYYY-MM-DD`)
- `end_date` (string): Data di fine del periodo richiesto (ISO format: `YYYY-MM-DD`)
- `metrics` (array): Array di oggetti contenenti le metriche giornaliere, ordinati per data crescente

**Oggetto Metric**:
- `date` (string): Data del record (ISO format: `YYYY-MM-DD`)
- `daily_tss` (float): Training Stress Score totale per quel giorno (somma di tutte le attività)
- `ctl` (float | null): Chronic Training Load (fitness) - media esponenziale a 42 giorni
- `atl` (float | null): Acute Training Load (fatigue) - media esponenziale a 7 giorni
- `tsb` (float | null): Training Stress Balance (form) - calcolato come CTL - ATL
- `activities_count` (integer): Numero di attività Strava registrate per quel giorno

**Error Responses**:

**400 Bad Request** - Formato data non valido:
```json
{
  "detail": "Invalid start_date format. Use YYYY-MM-DD"
}
```

**400 Bad Request** - Date non valide:
```json
{
  "detail": "start_date must be before or equal to end_date"
}
```

**401 Unauthorized** - Token mancante o non valido:
```json
{
  "detail": "Not authenticated"
}
```

**Esempi di Utilizzo**:

1. **Ultimi 30 giorni**:
   ```http
   GET /api/statistics/daily-metrics?start_date=2024-01-01&end_date=2024-01-31
   ```

2. **Ultimi 12 settimane (default)**:
   ```http
   GET /api/statistics/daily-metrics
   ```

3. **Periodo personalizzato**:
   ```http
   GET /api/statistics/daily-metrics?start_date=2023-12-01&end_date=2024-01-31
   ```

**Note Importanti**:

- I valori `ctl`, `atl`, `tsb` possono essere `null` per giorni senza dati storici sufficienti (meno di 42 giorni di storia per CTL, meno di 7 per ATL)
- Il calcolo è incrementale: ogni giorno calcola i propri valori basandosi sul giorno precedente
- I giorni senza attività (rest days) hanno `daily_tss = 0`, ma comunque contribuiscono al calcolo del decay di CTL/ATL
- Se un giorno non ha ancora metriche calcolate, vengono aggiornate automaticamente alla prima chiamata

---

## 🔄 API Modificate (comportamento aggiornato)

### 1. `GET /statistics/performance-chart`

**Endpoint**: `/api/statistics/performance-chart`

**Modifiche**:
- Ora utilizza i dati giornalieri aggregati per settimana, invece di leggere direttamente dai weekly summaries
- Il comportamento dell'API rimane identico dal punto di vista del frontend
- I dati sono più accurati e sempre aggiornati fino a oggi

**Input**: Invariato
- `weeks` (query param): Numero di settimane da recuperare (default: 12, min: 1, max: 52)

**Output**: Invariato (stesso formato, dati più accurati)

### 2. `GET /statistics/overview`

**Endpoint**: `/api/statistics/overview`

**Modifiche**:
- Ora legge CTL/ATL/TSB dai daily metrics di oggi, invece che dal weekly summary
- I dati sono sempre aggiornati al momento corrente

**Input**: Invariato (nessun parametro)

**Output**: Invariato (stesso formato, dati più accurati)

### 3. `GET /strava/debug/daily-metrics` (precedentemente `/strava/debug/weekly-summaries`)

**Endpoint**: `/api/strava/debug/daily-metrics`

**Modifiche**:
- Endpoint di debug rinominato e aggiornato per mostrare daily metrics invece di weekly summaries
- Mostra gli ultimi 30 giorni di metriche giornaliere

**Input**: Invariato (nessun parametro)

**Output**: Modificato

**Response**:
```json
{
  "count": 30,
  "metrics": [
    {
      "date": "2024-01-31",
      "ctl": 52.3,
      "atl": 48.7,
      "tsb": 3.6,
      "daily_tss": 45.5,
      "activities_count": 1
    }
    // ... altri giorni
  ]
}
```

---

## 📊 Calcolo Incrementale: Come Funziona

Il nuovo sistema calcola CTL/ATL/TSB in modo incrementale usando la formula:

```
CTL_today = CTL_yesterday + (TSS_today - CTL_yesterday) × λ_ctl
ATL_today = ATL_yesterday + (TSS_today - ATL_yesterday) × λ_atl
TSB_today = CTL_today - ATL_today
```

Dove:
- `λ_ctl ≈ 0.153` (costante per smoothing a 42 giorni)
- `λ_atl ≈ 0.632` (costante per smoothing a 7 giorni)

**Vantaggi**:
- Calcolo veloce: solo una operazione matematica per giorno
- Aggiornamento in tempo reale: quando si aggiunge un'attività, vengono aggiornati solo i giorni necessari
- Dati sempre accurati: ogni giorno ha il suo valore esatto, non una media settimanale

---

## 🔧 Endpoint di Ricostruzione Dati

### `POST /strava/recalculate-metrics`

**Modifiche al Response**:

Il campo `weekly_summaries_created` è stato sostituito con `daily_metrics_updated`:

**Response** (modificato):
```json
{
  "success": true,
  "activities_processed": 150,
  "metrics_calculated": {
    "tss": 150,
    "trimp": 150,
    "zones": 150
  },
  "daily_metrics_updated": 85,  // ← Modificato da weekly_summaries_created
  "initial_ctl": 52.3,
  "initial_atl": 48.7,
  "initial_tsb": 3.6,
  "processing_time_seconds": 12.45
}
```

---

## 📝 Schema Response Eliminato

Il seguente schema Pydantic è stato rimosso:

- `WeeklySummaryResponse` da `app/schemas/statistics.py`
- `WeeklySummaryResponse` da `app/schemas/metrics.py`

Questi schemi non sono più necessari in quanto l'endpoint `/statistics/weekly-summary` è stato eliminato.

---

## 🔄 Migrazione Frontend

Per migrare il frontend al nuovo sistema:

1. **Sostituire chiamate a `/statistics/weekly-summary`**:
   - Usare `/statistics/daily-metrics` per ottenere dati giornalieri
   - Aggregare i dati per settimana se necessario
   - Oppure continuare a usare `/statistics/performance-chart` che già fornisce dati aggregati

2. **Aggiornare response handling**:
   - Il campo `daily_metrics_updated` invece di `weekly_summaries_created` in `/strava/recalculate-metrics`
   - I dati giornalieri hanno struttura diversa ma più ricca

3. **Ottimizzazioni possibili**:
   - Richiedere solo i giorni necessari con `start_date` e `end_date`
   - Cache lato client per evitare richieste multiple
   - Aggregare a livello frontend solo se necessario (il backend può già fornire aggregazioni settimanali)

---

## 📌 Note Finali

- Tutti gli endpoint esistenti (`/overview`, `/performance-chart`, `/zone-distribution`, `/training-load`) continuano a funzionare normalmente
- I dati sono retrocompatibili: il formato delle response non è cambiato per gli endpoint esistenti
- Il sistema è più performante: calcolo incrementale invece di ricalcolo completo settimanale
- I dati sono più accurati: valori giornalieri invece di medie settimanali

---

**Data documento**: 2024  
**Versione API**: dopo migrazione a Daily Metrics


