# Guida Frontend: Check Attività Strava Non Sincronizzate

Questa guida spiega come utilizzare l'endpoint `GET /strava/check-unsynced` per verificare se ci sono nuove attività Strava da sincronizzare.

## Panoramica

L'endpoint `GET /strava/check-unsynced` è un endpoint **super efficiente** che:
- Trova l'ultima attività già sincronizzata nel database
- Recupera solo le attività più recenti da Strava (non tutte)
- Confronta e conta quante attività non sono ancora state sincronizzate
- Restituisce la data dell'allenamento più vecchio non sincronizzato

**Utilizzo tipico**: Chiamare questo endpoint periodicamente (es. all'apertura dell'app o ogni X minuti) per verificare se ci sono nuove attività da sincronizzare, e poi triggerare il sync solo se necessario.

## Endpoint

```
GET /api/strava/check-unsynced
```

### Autenticazione

Richiede autenticazione Bearer token:

```
Authorization: Bearer <access_token>
```

### Risposta

```typescript
interface StravaUnsyncedCheckResponse {
  unsynced_count: number;           // Numero di attività non sincronizzate
  oldest_unsynced_date: string | null;  // Data dell'allenamento più vecchio non sincronizzato (ISO format)
  last_synced_date: string | null;      // Data dell'ultima attività sincronizzata (ISO format)
}
```

### Esempio di Risposta

```json
{
  "unsynced_count": 5,
  "oldest_unsynced_date": "2024-11-20T10:30:00+00:00",
  "last_synced_date": "2024-11-18T15:20:00+00:00"
}
```

**Casi speciali:**
- Se `unsynced_count` è `0`: tutte le attività sono sincronizzate
- Se `last_synced_date` è `null`: non ci sono attività sincronizzate nel database (primo sync)
- Se `oldest_unsynced_date` è `null`: non ci sono attività non sincronizzate

## Implementazione

### 1. Funzione Base per Chiamare l'Endpoint

```typescript
async function checkUnsyncedActivities(token: string): Promise<StravaUnsyncedCheckResponse> {
  const response = await fetch('/api/strava/check-unsynced', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Nessun account Strava collegato');
    }
    throw new Error(`Errore nel controllo: ${response.statusText}`);
  }

  return await response.json();
}
```

### 2. Calcolare i Giorni da Sincronizzare

Quando ci sono attività non sincronizzate, devi calcolare quanti giorni indietro sincronizzare:

```typescript
function calculateDaysBack(oldestUnsyncedDate: string | null): number {
  if (!oldestUnsyncedDate) {
    return 30; // Default se non c'è data
  }

  const oldestDate = new Date(oldestUnsyncedDate);
  const now = new Date();
  const diffTime = now.getTime() - oldestDate.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  // Aggiungi un buffer di 2 giorni per sicurezza
  return Math.min(diffDays + 2, 365); // Max 365 giorni
}
```

### 3. Triggerare il Sync

Dopo aver verificato che ci sono attività non sincronizzate, puoi triggerare il sync:

```typescript
async function syncStravaActivities(
  token: string, 
  daysBack: number
): Promise<StravaSyncJobResponse> {
  const response = await fetch('/api/strava/sync', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      days_back: daysBack,
    }),
  });

  if (!response.ok) {
    throw new Error(`Errore nella sincronizzazione: ${response.statusText}`);
  }

  return await response.json();
}
```

### 4. Esempio Completo: Check e Sync Automatico

```typescript
async function checkAndSyncStravaActivities(token: string): Promise<void> {
  try {
    // 1. Controlla se ci sono attività non sincronizzate
    const checkResult = await checkUnsyncedActivities(token);

    if (checkResult.unsynced_count === 0) {
      console.log('Tutte le attività sono già sincronizzate');
      return;
    }

    console.log(
      `Trovate ${checkResult.unsynced_count} attività non sincronizzate. ` +
      `La più vecchia è del ${checkResult.oldest_unsynced_date}`
    );

    // 2. Calcola quanti giorni indietro sincronizzare
    const daysBack = calculateDaysBack(checkResult.oldest_unsynced_date);

    // 3. Triggera il sync
    const syncJob = await syncStravaActivities(token, daysBack);
    
    console.log(`Sync avviato. Job ID: ${syncJob.id}`);
    
    // 4. (Opzionale) Monitora il progresso del job
    // Vedi documentazione API_STRAVA_SYNC.md per dettagli

  } catch (error) {
    console.error('Errore nel check/sync:', error);
    throw error;
  }
}
```

## Pattern di Utilizzo

### Pattern 1: Check all'Apertura dell'App

```typescript
// Quando l'utente apre l'app o naviga alla dashboard
useEffect(() => {
  const checkStravaSync = async () => {
    try {
      const result = await checkUnsyncedActivities(token);
      
      if (result.unsynced_count > 0) {
        // Mostra notifica all'utente
        showNotification({
          type: 'info',
          message: `${result.unsynced_count} nuove attività Strava da sincronizzare`,
          action: {
            label: 'Sincronizza ora',
            onClick: () => triggerSync(result),
          },
        });
      }
    } catch (error) {
      // Gestisci errore (es. account non collegato)
      console.error(error);
    }
  };

  checkStravaSync();
}, [token]);
```

### Pattern 2: Check Periodico (Polling)

```typescript
// Controlla ogni 5 minuti se ci sono nuove attività
useEffect(() => {
  const interval = setInterval(async () => {
    try {
      const result = await checkUnsyncedActivities(token);
      
      if (result.unsynced_count > 0) {
        // Auto-sync in background (opzionale)
        const daysBack = calculateDaysBack(result.oldest_unsynced_date);
        await syncStravaActivities(token, daysBack);
      }
    } catch (error) {
      console.error('Errore nel check periodico:', error);
    }
  }, 5 * 60 * 1000); // 5 minuti

  return () => clearInterval(interval);
}, [token]);
```

### Pattern 3: Check Manuale con UI

```typescript
function StravaSyncButton() {
  const [isChecking, setIsChecking] = useState(false);
  const [unsyncedCount, setUnsyncedCount] = useState<number | null>(null);

  const handleCheck = async () => {
    setIsChecking(true);
    try {
      const result = await checkUnsyncedActivities(token);
      setUnsyncedCount(result.unsynced_count);
      
      if (result.unsynced_count > 0) {
        // Mostra dialog per confermare sync
        const confirmed = await showConfirmDialog({
          title: 'Sincronizza attività Strava',
          message: `Trovate ${result.unsynced_count} nuove attività. Vuoi sincronizzarle ora?`,
        });
        
        if (confirmed) {
          const daysBack = calculateDaysBack(result.oldest_unsynced_date);
          await syncStravaActivities(token, daysBack);
        }
      } else {
        showNotification({
          type: 'success',
          message: 'Tutte le attività sono già sincronizzate',
        });
      }
    } catch (error) {
      showNotification({
        type: 'error',
        message: 'Errore nel controllo delle attività',
      });
    } finally {
      setIsChecking(false);
    }
  };

  return (
    <button onClick={handleCheck} disabled={isChecking}>
      {isChecking ? 'Controllo in corso...' : 'Verifica nuove attività'}
      {unsyncedCount !== null && unsyncedCount > 0 && (
        <Badge count={unsyncedCount} />
      )}
    </button>
  );
}
```

### Pattern 4: Check dopo Connessione Strava

```typescript
// Dopo che l'utente ha collegato il suo account Strava
async function onStravaConnected(token: string) {
  try {
    // Controlla immediatamente se ci sono attività da sincronizzare
    const result = await checkUnsyncedActivities(token);
    
    if (result.unsynced_count > 0) {
      // Auto-sync iniziale
      const daysBack = calculateDaysBack(result.oldest_unsynced_date);
      const syncJob = await syncStravaActivities(token, daysBack);
      
      // Mostra progresso del sync
      monitorSyncJob(syncJob.id);
    }
  } catch (error) {
    console.error('Errore nel check iniziale:', error);
  }
}
```

## Gestione Errori

### Errore 404: Nessun Account Strava

```typescript
try {
  const result = await checkUnsyncedActivities(token);
} catch (error) {
  if (error.message.includes('Nessun account Strava')) {
    // Mostra UI per collegare account Strava
    showStravaConnectPrompt();
  }
}
```

### Errore di Rete

```typescript
try {
  const result = await checkUnsyncedActivities(token);
} catch (error) {
  if (error instanceof TypeError && error.message.includes('fetch')) {
    // Errore di rete
    showNotification({
      type: 'error',
      message: 'Errore di connessione. Riprova più tardi.',
    });
  }
}
```

## Best Practices

### 1. Rate Limiting

Non chiamare l'endpoint troppo frequentemente. Consigliato:
- **Massimo 1 volta ogni 2-3 minuti** per polling automatico
- **All'apertura dell'app** per check iniziale
- **Dopo azioni dell'utente** (es. dopo aver collegato Strava)

### 2. Caching

Puoi cachare il risultato per evitare chiamate ridondanti:

```typescript
let lastCheckTime: number | null = null;
let cachedResult: StravaUnsyncedCheckResponse | null = null;
const CACHE_DURATION = 2 * 60 * 1000; // 2 minuti

async function checkUnsyncedActivitiesCached(
  token: string
): Promise<StravaUnsyncedCheckResponse> {
  const now = Date.now();
  
  // Usa cache se ancora valida
  if (
    cachedResult &&
    lastCheckTime &&
    now - lastCheckTime < CACHE_DURATION
  ) {
    return cachedResult;
  }

  // Altrimenti fai la chiamata
  const result = await checkUnsyncedActivities(token);
  cachedResult = result;
  lastCheckTime = now;
  
  return result;
}
```

### 3. Loading States

Mostra sempre uno stato di caricamento durante il check:

```typescript
const [isChecking, setIsChecking] = useState(false);

const handleCheck = async () => {
  setIsChecking(true);
  try {
    const result = await checkUnsyncedActivities(token);
    // ... gestisci risultato
  } finally {
    setIsChecking(false);
  }
};
```

### 4. Ottimizzazione: Check Solo se Strava Collegato

Prima di chiamare l'endpoint, verifica se l'utente ha un account Strava collegato:

```typescript
async function checkIfStravaConnected(token: string): Promise<boolean> {
  try {
    const response = await fetch('/api/strava/account', {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    return response.ok;
  } catch {
    return false;
  }
}

// Usa così:
if (await checkIfStravaConnected(token)) {
  const result = await checkUnsyncedActivities(token);
}
```

## Esempio Completo React Hook

```typescript
import { useState, useEffect, useCallback } from 'react';

interface UseStravaSyncCheckOptions {
  token: string;
  autoCheck?: boolean;
  checkInterval?: number; // in millisecondi
}

export function useStravaSyncCheck({
  token,
  autoCheck = false,
  checkInterval = 5 * 60 * 1000, // 5 minuti default
}: UseStravaSyncCheckOptions) {
  const [unsyncedCount, setUnsyncedCount] = useState<number | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastSyncedDate, setLastSyncedDate] = useState<string | null>(null);

  const check = useCallback(async () => {
    if (!token) return;

    setIsChecking(true);
    setError(null);

    try {
      const result = await checkUnsyncedActivities(token);
      setUnsyncedCount(result.unsynced_count);
      setLastSyncedDate(result.last_synced_date);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      setUnsyncedCount(null);
    } finally {
      setIsChecking(false);
    }
  }, [token]);

  useEffect(() => {
    if (autoCheck) {
      // Check immediato
      check();

      // Check periodico
      const interval = setInterval(check, checkInterval);
      return () => clearInterval(interval);
    }
  }, [autoCheck, checkInterval, check]);

  const triggerSync = useCallback(async () => {
    if (!token || unsyncedCount === null || unsyncedCount === 0) {
      return;
    }

    try {
      const result = await checkUnsyncedActivities(token);
      const daysBack = calculateDaysBack(result.oldest_unsynced_date);
      await syncStravaActivities(token, daysBack);
      
      // Ricontrolla dopo il sync
      setTimeout(check, 2000);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Sync failed'));
    }
  }, [token, unsyncedCount, check]);

  return {
    unsyncedCount,
    isChecking,
    error,
    lastSyncedDate,
    check,
    triggerSync,
  };
}

// Utilizzo:
function MyComponent() {
  const { token } = useAuth();
  const {
    unsyncedCount,
    isChecking,
    triggerSync,
  } = useStravaSyncCheck({
    token,
    autoCheck: true,
    checkInterval: 5 * 60 * 1000,
  });

  return (
    <div>
      {isChecking ? (
        <span>Controllo in corso...</span>
      ) : unsyncedCount !== null && unsyncedCount > 0 ? (
        <button onClick={triggerSync}>
          Sincronizza {unsyncedCount} nuove attività
        </button>
      ) : (
        <span>Tutte le attività sono sincronizzate</span>
      )}
    </div>
  );
}
```

## Riepilogo

1. **Chiama** `GET /api/strava/check-unsynced` per verificare attività non sincronizzate
2. **Controlla** `unsynced_count` - se > 0, ci sono attività da sincronizzare
3. **Calcola** `days_back` usando `oldest_unsynced_date`
4. **Triggera** `POST /api/strava/sync` con `days_back` calcolato
5. **Monitora** il job di sync (opzionale, vedi documentazione sync jobs)

L'endpoint è ottimizzato per essere chiamato frequentemente senza impattare le performance!

