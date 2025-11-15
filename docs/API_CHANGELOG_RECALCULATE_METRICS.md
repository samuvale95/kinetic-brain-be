# Changelog API - Recalcolo Metriche Ottimizzato

## 📋 Riassunto Modifiche

L'endpoint `/strava/recalculate-metrics` è stato **ottimizzato per la performance** con l'aggiunta di un nuovo parametro opzionale `months_back` che permette di limitare il ricalcolo agli ultimi N mesi.

## 🔄 Modifiche all'Interfaccia API

### POST `/strava/recalculate-metrics`

#### Prima (vecchia versione)
```typescript
POST /strava/recalculate-metrics
// Nessun parametro - elaborava TUTTE le attività (poteva richiedere ore)
```

#### Ora (nuova versione)
```typescript
POST /strava/recalculate-metrics?months_back={n}

// Query Parameters (opzionali):
- months_back: number (default: 12, min: 1, max: 60)
  Descrizione: Numero di mesi indietro per cui ricalcolare le metriche
```

#### Esempi di Chiamate

**Default (12 mesi - raccomandato)**:
```
POST /strava/recalculate-metrics
```
Equivalente a:
```
POST /strava/recalculate-metrics?months_back=12
```

**Ultimi 3 mesi (veloce per test)**:
```
POST /strava/recalculate-metrics?months_back=3
```

**Ultimo mese (molto veloce)**:
```
POST /strava/recalculate-metrics?months_back=1
```

**Tutti i dati (60 mesi - solo se necessario)**:
```
POST /strava/recalculate-metrics?months_back=60
```

## 📊 Response (invariata)

La response rimane identica:

```typescript
interface StravaSyncJobResponse {
  id: number;
  user_id: number;
  strava_account_id: number;
  job_type: "recalculate_metrics";
  status: "pending" | "running" | "success" | "failed";
  status_message: string;
  total_activities: number;        // Ora riflette solo le attività nel range
  processed_activities: number;
  metrics_phase: number;
  metrics_phases_total: number;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  requested_days_back: number;     // Ora = months_back * 30 (usato per riferimento)
  created_at: string;
  updated_at: string | null;
  result: {
    // ... invariato
  } | null;
}
```

**Nota**: `total_activities` ora riflette solo le attività nel range di date specificato, non tutte le attività dell'utente.

## ⚡ Performance - Tempi Stimati

| `months_back` | Attività Tipiche | Tempo Stimato | Uso Consigliato |
|---------------|------------------|---------------|-----------------|
| 1 mese | ~10-30 | 1-2 minuti | Fix rapidi |
| 3 mesi | ~30-90 | 3-5 minuti | Test, recalcoli frequenti |
| 6 mesi | ~60-180 | 5-10 minuti | Recalcolo trimestrale |
| 12 mesi (default) | ~120-360 | 10-20 minuti | Recalcolo annuale |
| 24 mesi | ~240-720 | 20-40 minuti | Ricalcolo completo recente |
| 60 mesi | ~600-1800 | 1-3 ore | Solo se necessario |

*Tempi basati su ~10-30 attività al mese. Tempi reali possono variare.*

## 🔧 Migrazione Frontend

### Modifica Minima (backward compatible)

Se non modifichi nulla, il comportamento resta identico (12 mesi default):

```typescript
// Funziona ancora - usa default 12 mesi
const response = await fetch('/strava/recalculate-metrics', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### Modifica Raccomandata (aggiungere selettore)

Per dare controllo all'utente e velocizzare i recalcoli:

```typescript
// Funzione aggiornata con parametro opzionale
async function startRecalculateMetrics(
  token: string,
  monthsBack: number = 12  // Default: 12 mesi (backward compatible)
): Promise<StravaSyncJobResponse> {
  const url = monthsBack !== 12 
    ? `/strava/recalculate-metrics?months_back=${monthsBack}`
    : '/strava/recalculate-metrics';
  
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

// Uso:
await startRecalculateMetrics(token, 12);  // Default
await startRecalculateMetrics(token, 3);   // Ultimi 3 mesi (più veloce)
```

### UI Consigliata

Aggiungere un selettore per permettere all'utente di scegliere il range:

```typescript
function RecalculateMetricsComponent() {
  const [monthsBack, setMonthsBack] = useState(12);
  
  return (
    <div>
      <label>
        Periodo da ricalcolare:
        <select 
          value={monthsBack}
          onChange={(e) => setMonthsBack(Number(e.target.value))}
        >
          <option value={1}>Ultimo mese (più veloce)</option>
          <option value={3}>Ultimi 3 mesi</option>
          <option value={6}>Ultimi 6 mesi</option>
          <option value={12}>Ultimo anno (default)</option>
          <option value={24}>Ultimi 2 anni</option>
          <option value={60}>Tutti i dati</option>
        </select>
      </label>
      
      <button onClick={() => startRecalculateMetrics(token, monthsBack)}>
        Ricalcola Metriche
      </button>
    </div>
  );
}
```

## ✅ Backward Compatibility

✅ **COMPLETAMENTE COMPATIBILE**: Se il frontend non passa `months_back`, viene usato il default di 12 mesi, mantenendo lo stesso comportamento della versione precedente.

## 🎯 Vantaggi per l'Utente

1. **Velocità**: Recalcoli molto più rapidi per range brevi
2. **Flessibilità**: L'utente può scegliere quanto ricalcolare
3. **Test**: Facile testare con range brevi (1-3 mesi)
4. **Senso pratico**: Le metriche recenti sono quelle più importanti

## 📝 Note Implementazione

- Il parametro `months_back` è opzionale e ha default `12`
- Se omesso, il comportamento è identico alla versione precedente
- `requested_days_back` nel job response viene calcolato come `months_back * 30`
- Le attività vengono filtrate per `start_date >= (now - months_back * 30 days)`

## 🔗 Documentazione Completa

Per la documentazione completa con esempi React/Vue, vedere:
- `docs/API_RECALCULATE_METRICS.md`

