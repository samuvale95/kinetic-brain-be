# API Recalcolo Metriche Strava - Guida Frontend

## Panoramica

L'endpoint `/strava/recalculate-metrics` permette di ricalcolare le metriche di allenamento (TSS, IF, TRIMP, zone distribution) per tutte le attività Strava dell'utente. L'operazione viene eseguita **asincronamente** tramite un sistema di job che permette di tracciare il progresso in tempo reale.

## Endpoint Principale

### POST `/strava/recalculate-metrics`

Avvia il recalcolo metriche come job in background.

**Autenticazione**: Richiesta (Bearer Token)

**Query Parameters**:
- `months_back` (opzionale, default: 12, min: 1, max: 60): Numero di mesi indietro per cui ricalcolare le metriche. 
  - **Riduce drasticamente i tempi di elaborazione** limitando il range di date
  - Esempio: `months_back=3` elabora solo gli ultimi 3 mesi
  - Default: 12 mesi

**Request Body**: Nessuno

**Response** (200 OK):
```typescript
interface StravaSyncJobResponse {
  id: number;                      // Job ID
  user_id: number;
  strava_account_id: number;
  job_type: "recalculate_metrics"; // Tipo di job
  status: "pending" | "running" | "success" | "failed";
  status_message: string;          // Messaggio di stato corrente
  total_activities: number;        // Numero totale attività da processare
  processed_activities: number;    // Numero attività già processate
  metrics_phase: number;           // Fase corrente (1-3)
  metrics_phases_total: number;    // Totale fasi (3)
  error: string | null;            // Messaggio di errore (se fallito)
  started_at: string | null;       // ISO datetime quando è iniziato
  finished_at: string | null;      // ISO datetime quando è finito
  requested_days_back: number;     // Giorni indietro calcolati (months_back * 30)
  created_at: string;              // ISO datetime creazione job
  updated_at: string | null;       // ISO datetime ultimo aggiornamento
  result: {                        // Risultato finale (solo se success)
    success: boolean;
    activities_processed: number;
    metrics_calculated: {
      tss_calculated: number;
      trimp_calculated: number;
      if_calculated: number;
      zones_calculated: number;
    };
    daily_metrics_updated: number;
    initial_ctl: number;
    initial_atl: number;
    initial_tsb: number;
    processing_time_seconds: number;
    errors: number;
  } | null;
}
```

**Esempio Request** (ultimi 12 mesi - default):
```typescript
const response = await fetch('/strava/recalculate-metrics', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

const job = await response.json();
console.log('Job avviato:', job.id);
```

**Esempio Request** (ultimi 3 mesi - più veloce):
```typescript
const response = await fetch('/strava/recalculate-metrics?months_back=3', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

const job = await response.json();
console.log('Job avviato per ultimi 3 mesi:', job.id);
```

**Esempio Request** (tutti - 60 mesi, più lento):
```typescript
const response = await fetch('/strava/recalculate-metrics?months_back=60', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

const job = await response.json();
console.log('Job avviato per tutti i dati:', job.id);
```

## Endpoint per Tracciare il Job

### GET `/strava/sync/jobs/{job_id}`

Ottiene i dettagli di un job specifico.

**Response** (200 OK):
```typescript
StravaSyncJobResponse  // Stessa struttura di sopra
```

**Esempio**:
```typescript
const response = await fetch(`/strava/sync/jobs/${jobId}`, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const job = await response.json();
console.log('Stato job:', job.status);
console.log('Progresso:', job.processed_activities, '/', job.total_activities);
```

### GET `/strava/sync/jobs/latest?limit={n}`

Ottiene gli ultimi N job dell'utente (utile per mostrare lo storico).

**Query Parameters**:
- `limit` (opzionale, default: 5, min: 1, max: 20)

**Response** (200 OK):
```typescript
interface StravaSyncJobListResponse {
  jobs: StravaSyncJobResponse[];
}
```

## Stati del Job

### `pending`
Job creato ma non ancora avviato. Normalmente transita rapidamente a `running`.

### `running`
Job in esecuzione. Durante questa fase:
- `processed_activities` viene aggiornato ogni 25 attività
- `metrics_phase` indica la fase corrente:
  - **Fase 1**: Processamento attività e calcolo metriche
  - **Fase 2**: Calcolo fitness metrics (CTL/ATL/TSB)
  - **Fase 3**: Aggiornamento daily metrics

### `success`
Job completato con successo. Il campo `result` contiene i dettagli finali.

### `failed`
Job fallito. Il campo `error` contiene il motivo dell'errore.

## Implementazione Frontend

### 1. Funzione per Avviare il Recalcolo

```typescript
async function startRecalculateMetrics(
  token: string,
  monthsBack: number = 12  // Default: 12 mesi (ultimo anno)
): Promise<StravaSyncJobResponse> {
  const url = `/strava/recalculate-metrics${monthsBack !== 12 ? `?months_back=${monthsBack}` : ''}`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to start recalculation');
  }

  return response.json();
}

// Esempi di utilizzo:
// Ultimi 12 mesi (default) - buon compromesso
await startRecalculateMetrics(token, 12);

// Ultimi 3 mesi - molto più veloce, utile per test o recalcoli frequenti
await startRecalculateMetrics(token, 3);

// Tutto lo storico - solo se necessario
await startRecalculateMetrics(token, 60);
```

### 2. Funzione per Tracciare lo Stato del Job

```typescript
async function getJobStatus(
  jobId: number, 
  token: string
): Promise<StravaSyncJobResponse> {
  const response = await fetch(`/strava/sync/jobs/${jobId}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  if (!response.ok) {
    throw new Error('Failed to get job status');
  }

  return response.json();
}
```

### 3. Hook React per Gestire il Recalcolo

```typescript
import { useState, useEffect, useCallback } from 'react';

interface UseRecalculateMetricsReturn {
  startRecalculation: () => Promise<void>;
  job: StravaSyncJobResponse | null;
  isRunning: boolean;
  progress: number; // 0-100
  error: string | null;
}

function useRecalculateMetrics(token: string): UseRecalculateMetricsReturn {
  const [job, setJob] = useState<StravaSyncJobResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const startRecalculation = useCallback(async (monthsBack: number = 12) => {
    try {
      setError(null);
      setIsRunning(true);
      
      const newJob = await startRecalculateMetrics(token, monthsBack);
      setJob(newJob);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setIsRunning(false);
    }
  }, [token]);

  // Polling dello stato del job ogni 2 secondi se è running
  useEffect(() => {
    if (!job || job.status === 'success' || job.status === 'failed') {
      setIsRunning(false);
      return;
    }

    if (job.status === 'running' || job.status === 'pending') {
      setIsRunning(true);
      
      const interval = setInterval(async () => {
        try {
          const updatedJob = await getJobStatus(job.id, token);
          setJob(updatedJob);

          // Se il job è completato, ferma il polling
          if (updatedJob.status === 'success' || updatedJob.status === 'failed') {
            setIsRunning(false);
            clearInterval(interval);
          }
        } catch (err) {
          console.error('Error polling job status:', err);
          clearInterval(interval);
        }
      }, 2000); // Poll ogni 2 secondi

      return () => clearInterval(interval);
    }
  }, [job, token]);

  // Calcola il progresso percentuale
  const progress = job && job.total_activities > 0
    ? Math.round((job.processed_activities / job.total_activities) * 100)
    : 0;

  return {
    startRecalculation,
    job,
    isRunning,
    progress,
    error
  };
}
```

### 4. Componente React per l'UI

```typescript
import React from 'react';

interface RecalculateMetricsButtonProps {
  token: string;
  monthsBack?: number;  // Default: 12
  onComplete?: (result: any) => void;
}

function RecalculateMetricsButton({ token, monthsBack: initialMonthsBack = 12, onComplete }: RecalculateMetricsButtonProps) {
  const [monthsBack, setMonthsBack] = useState(initialMonthsBack);
  const { 
    startRecalculation, 
    job, 
    isRunning, 
    progress, 
    error 
  } = useRecalculateMetrics(token);

  const handleStart = async () => {
    await startRecalculation(monthsBack);
  };

  // Mostra il risultato quando completato
  React.useEffect(() => {
    if (job?.status === 'success' && job.result && onComplete) {
      onComplete(job.result);
    }
  }, [job, onComplete]);

  // Mostra messaggio di errore se fallito
  React.useEffect(() => {
    if (job?.status === 'failed') {
      console.error('Recalculation failed:', job.error);
    }
  }, [job]);

  const getStatusMessage = () => {
    if (!job) return null;
    
    switch (job.status) {
      case 'pending':
        return 'Job in attesa di avvio...';
      case 'running':
        const phaseMessages = [
          null,
          'Processamento attività...',
          'Calcolo fitness metrics (CTL/ATL/TSB)...',
          'Aggiornamento daily metrics...'
        ];
        const phaseMessage = phaseMessages[job.metrics_phase] || 'In elaborazione...';
        return `${phaseMessage} (${job.processed_activities}/${job.total_activities} attività)`;
      case 'success':
        return 'Recalcolo completato con successo!';
      case 'failed':
        return `Errore: ${job.error || 'Errore sconosciuto'}`;
      default:
        return null;
    }
  };

  return (
    <div className="recalculate-metrics">
      <div className="controls">
        <select 
          value={monthsBack} 
          onChange={(e) => setMonthsBack(parseInt(e.target.value))}
          disabled={isRunning}
          className="months-select"
        >
          <option value={1}>Ultimo mese (più veloce)</option>
          <option value={3}>Ultimi 3 mesi</option>
          <option value={6}>Ultimi 6 mesi</option>
          <option value={12}>Ultimo anno (default)</option>
          <option value={24}>Ultimi 2 anni</option>
          <option value={60}>Tutti i dati</option>
        </select>
        
        <button 
          onClick={handleStart} 
          disabled={isRunning}
          className="btn btn-primary"
        >
          {isRunning ? 'Recalcolo in corso...' : 'Ricalcola Metriche'}
        </button>
      </div>

      {job && (
        <div className="job-status">
          <div className="status-message">{getStatusMessage()}</div>
          
          {job.status === 'running' && (
            <>
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="progress-text">
                {progress}% - Fase {job.metrics_phase}/{job.metrics_phases_total}
              </div>
            </>
          )}

          {job.status === 'success' && job.result && (
            <div className="result-summary">
              <p>Attività processate: {job.result.activities_processed}</p>
              <p>TSS calcolati: {job.result.metrics_calculated.tss_calculated}</p>
              <p>TRIMP calcolati: {job.result.metrics_calculated.trimp_calculated}</p>
              <p>Zone calcolate: {job.result.metrics_calculated.zones_calculated}</p>
              <p>Tempo elaborazione: {job.result.processing_time_seconds}s</p>
              {job.result.errors > 0 && (
                <p className="warning">Errori: {job.result.errors}</p>
              )}
            </div>
          )}

          {error && (
            <div className="error-message">{error}</div>
          )}
        </div>
      )}
    </div>
  );
}
```

### 5. Stili CSS (Opzionale)

```css
.recalculate-metrics {
  padding: 1rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.controls {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-bottom: 1rem;
}

.months-select {
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 1rem;
}

.months-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.job-status {
  margin-top: 1rem;
}

.status-message {
  font-weight: bold;
  margin-bottom: 0.5rem;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background-color: #e0e0e0;
  border-radius: 10px;
  overflow: hidden;
  margin: 0.5rem 0;
}

.progress-fill {
  height: 100%;
  background-color: #28a745;
  transition: width 0.3s ease;
}

.progress-text {
  text-align: center;
  font-size: 0.9rem;
  color: #666;
}

.result-summary {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.result-summary p {
  margin: 0.25rem 0;
}

.warning {
  color: #ffc107;
  font-weight: bold;
}

.error-message {
  color: #dc3545;
  margin-top: 0.5rem;
  padding: 0.5rem;
  background-color: #f8d7da;
  border-radius: 4px;
}
```

## Best Practices

### 1. Polling Intelligente
- **Frequenza**: Poll ogni 2-3 secondi quando il job è `running`
- **Ferma il polling**: Quando lo stato è `success` o `failed`
- **Limita i tentativi**: Dopo N errori consecutivi, ferma il polling

### 2. Feedback Utente
- Mostra sempre lo stato corrente (`status_message`)
- Mostra il progresso percentuale se disponibile
- Mostra la fase corrente (`metrics_phase`)
- Notifica quando completato con successo o errore

### 3. Gestione Errori
- Gestisci errori di rete (retry con backoff)
- Mostra messaggi di errore user-friendly
- Log degli errori per debugging

### 4. Performance
- Non avviare più di un job alla volta per utente
- Disabilita il pulsante durante l'esecuzione
- Salva il job ID in localStorage per recuperare lo stato dopo refresh

### 5. Persistenza (Opzionale)

```typescript
// Salva job ID in localStorage
localStorage.setItem('lastRecalcJobId', job.id.toString());

// Recupera job dopo refresh pagina
const lastJobId = localStorage.getItem('lastRecalcJobId');
if (lastJobId) {
  const job = await getJobStatus(parseInt(lastJobId), token);
  if (job.status === 'running' || job.status === 'pending') {
    // Riprendi il polling
    setJob(job);
  } else {
    localStorage.removeItem('lastRecalcJobId');
  }
}
```

## Esempio Completo Vue.js (Alternative)

```vue
<template>
  <div class="recalculate-metrics">
    <button 
      @click="startRecalculation" 
      :disabled="isRunning"
      class="btn btn-primary"
    >
      {{ isRunning ? 'Recalcolo in corso...' : 'Ricalcola Metriche' }}
    </button>

    <div v-if="job" class="job-status">
      <p class="status-message">{{ statusMessage }}</p>
      
      <div v-if="job.status === 'running'" class="progress">
        <div class="progress-bar">
          <div 
            class="progress-fill" 
            :style="{ width: `${progress}%` }"
          />
        </div>
        <p class="progress-text">
          {{ progress }}% - Fase {{ job.metrics_phase }}/{{ job.metrics_phases_total }}
        </p>
      </div>

      <div v-if="job.status === 'success' && job.result" class="result">
        <p>✅ Completato!</p>
        <p>Attività processate: {{ job.result.activities_processed }}</p>
      </div>

      <div v-if="job.status === 'failed'" class="error">
        ❌ Errore: {{ job.error }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue';

const props = defineProps<{
  token: string;
}>();

const job = ref<StravaSyncJobResponse | null>(null);
const isRunning = ref(false);
const pollingInterval = ref<number | null>(null);

const progress = computed(() => {
  if (!job.value || !job.value.total_activities) return 0;
  return Math.round((job.value.processed_activities / job.value.total_activities) * 100);
});

const statusMessage = computed(() => {
  if (!job.value) return '';
  
  switch (job.value.status) {
    case 'pending': return 'In attesa di avvio...';
    case 'running': return job.value.status_message || 'In elaborazione...';
    case 'success': return 'Recalcolo completato!';
    case 'failed': return `Errore: ${job.value.error}`;
    default: return '';
  }
});

const startRecalculation = async () => {
  try {
    const response = await fetch('/strava/recalculate-metrics', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${props.token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) throw new Error('Failed to start');
    
    job.value = await response.json();
    isRunning.value = true;
    startPolling();
  } catch (error) {
    console.error('Error starting recalculation:', error);
  }
};

const startPolling = () => {
  if (pollingInterval.value) return;
  
  pollingInterval.value = window.setInterval(async () => {
    if (!job.value) return;
    
    try {
      const response = await fetch(`/strava/sync/jobs/${job.value.id}`, {
        headers: {
          'Authorization': `Bearer ${props.token}`
        }
      });
      
      if (!response.ok) throw new Error('Failed to get status');
      
      const updatedJob = await response.json();
      job.value = updatedJob;
      
      if (updatedJob.status === 'success' || updatedJob.status === 'failed') {
        stopPolling();
        isRunning.value = false;
      }
    } catch (error) {
      console.error('Error polling:', error);
      stopPolling();
    }
  }, 2000);
};

const stopPolling = () => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value);
    pollingInterval.value = null;
  }
};

onUnmounted(() => {
  stopPolling();
});
</script>
```

## Note Importanti

1. **Autenticazione**: Tutti gli endpoint richiedono un token Bearer valido
2. **Rate Limiting**: Evita di fare polling troppo frequente (max 1 richiesta ogni 2 secondi)
3. **Timeout**: I job possono richiedere diversi minuti se ci sono molte attività
4. **Idempotenza**: Chiamare più volte `/recalculate-metrics` crea job separati (evita questo nel frontend)
5. **Job History**: Usa `/strava/sync/jobs/latest` per mostrare lo storico dei job
6. **Performance**: Usa `months_back` per velocizzare il recalcolo:
   - 1-3 mesi: molto veloce (minuti)
   - 6-12 mesi: veloce (decine di minuti)
   - 24+ mesi: può richiedere ore

## 🆕 Modifiche Recenti - Ottimizzazioni Performance

### Nuovo Parametro: `months_back`

**Prima**: Il recalcolo elaborava TUTTE le attività, indipendentemente dalla data. Questo poteva richiedere ore per utenti con molti anni di dati.

**Ora**: È possibile limitare il ricalcolo agli ultimi N mesi tramite il parametro `months_back`.

**Vantaggi**:
- ⚡ **Performance**: Riduzione drastica dei tempi di elaborazione
- 🎯 **Flessibilità**: L'utente può scegliere il range di date
- 💡 **Senso pratico**: Le metriche più recenti sono quelle più importanti

**Raccomandazioni**:
- **Default (12 mesi)**: Buon compromesso per la maggior parte degli utenti
- **3-6 mesi**: Per recalcoli frequenti o test
- **1 mese**: Per fix rapidi su dati recenti
- **60 mesi**: Solo se necessario ricalcolare tutto lo storico

### Ottimizzazioni Backend

1. **Batch Update Daily Metrics**: Invece di aggiornare i daily metrics per ogni attività, ora viene fatto in batch alla fine
2. **Skip Daily Update durante loop**: I daily metrics non vengono aggiornati durante il loop delle attività (più veloce)
3. **Filtro per data**: Query ottimizzata per filtrare attività per data prima di elaborarle

## Troubleshooting

### Job rimane in "pending" per troppo tempo
- Verifica che il server sia attivo
- Controlla i log del server per errori
- Il job potrebbe essere in coda

### Errore "No Strava account connected"
- L'utente deve prima collegare il proprio account Strava
- Verifica che `strava_account_id` esista

### Progresso non si aggiorna
- Il job aggiorna ogni 25 attività, potrebbe sembrare "bloccato"
- Verifica che il polling stia funzionando
- Controlla la console per errori di rete

