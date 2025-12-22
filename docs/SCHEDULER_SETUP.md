# Setup Scheduled Tasks (Workout Reminders)

Il sistema supporta due modalità per i task schedulati:

1. **Render Cron Jobs** (default) - endpoint HTTP chiamato esternamente
2. **APScheduler** - scheduler in-process, nessun setup esterno necessario

## 🎯 Quale scegliere?

### Render Cron Jobs (`scheduled_tasks_provider=render_cron`)
✅ **Vantaggi:**
- Nessuna dipendenza aggiuntiva nel processo
- Gestione tramite dashboard Render
- Separazione tra web server e job scheduler
- Non consuma risorse quando non esegue job

❌ **Svantaggi:**
- Richiede configurazione manuale in Render dashboard
- Dipende dalla disponibilità del servizio web per gli endpoint
- Meno controllo programmatico

**Quando usarlo**: Se preferisci gestire i cron job dalla dashboard Render e non vuoi dipendenze aggiuntive.

### APScheduler (`scheduled_tasks_provider=apscheduler`)
✅ **Vantaggi:**
- Setup immediato, nessuna configurazione esterna
- Controllo completo dal codice
- Puoi vedere/modificare job via API
- Funziona anche in sviluppo locale senza setup

❌ **Svantaggi:**
- Consuma risorse del processo web
- Se il processo si riavvia, i job vengono persi (ma si reinizializzano)
- Dipendenza aggiuntiva (`apscheduler`)

**Quando usarlo**: Se vuoi controllo immediato e setup automatico, o se non hai accesso immediato alla dashboard Render.

---

## 📋 Configurazione

### 1. Render Cron Jobs (Default)

#### Step 1: Imposta variabili d'ambiente

```bash
SCHEDULED_TASKS_PROVIDER=render_cron
INTERNAL_API_SECRET=il-tuo-secret-sicuro-qui
```

#### Step 2: Configura Cron Job in Render

1. Vai alla dashboard Render → **Cron Jobs** → **New Cron Job**
2. Configura:
   - **Nome**: `Send Workout Reminders - Morning`
   - **Schedule**: `0 8 * * *` (ogni giorno alle 8:00 UTC)
   - **Command**:
     ```bash
     curl -X POST "https://your-app.onrender.com/notifications/cron/send-workout-reminders" \
       -H "X-Internal-API-Secret: il-tuo-secret-sicuro-qui" \
       -H "Content-Type: application/json"
     ```

Vedi `docs/RENDER_CRON_SETUP.md` per dettagli completi.

---

### 2. APScheduler

#### Step 1: Installa dipendenza

La dipendenza `apscheduler==3.10.4` è già in `requirements.txt`.

#### Step 2: Imposta variabili d'ambiente

```bash
SCHEDULED_TASKS_PROVIDER=apscheduler
WORKOUT_REMINDER_MORNING_CRON=0 8 * * *
WORKOUT_REMINDER_EVENING_CRON=0 18 * * *
```

**Formato cron**: `minute hour day month day_of_week`
- `0 8 * * *` = Ogni giorno alle 8:00 UTC
- `0 18 * * *` = Ogni giorno alle 18:00 UTC
- Per disabilitare un reminder, lascia vuoto: `WORKOUT_REMINDER_EVENING_CRON=`

#### Step 3: Riavvia l'applicazione

APScheduler si inizializza automaticamente all'avvio dell'app.

#### Step 4: Verifica status

Chiama l'endpoint per verificare:

```bash
GET /notifications/scheduler/status
```

Risposta:
```json
{
  "provider": "apscheduler",
  "apscheduler_enabled": true,
  "jobs": [
    {
      "id": "workout_reminder_morning",
      "name": "Send workout reminders (morning)",
      "next_run_time": "2024-01-15T08:00:00+00:00",
      "trigger": "cron[minute='0', hour='8', ...]"
    },
    {
      "id": "workout_reminder_evening",
      "name": "Send workout reminders (evening)",
      "next_run_time": "2024-01-15T18:00:00+00:00",
      "trigger": "cron[minute='0', hour='18', ...]"
    }
  ]
}
```

---

## 🔄 Cambiare Provider

Puoi cambiare provider in qualsiasi momento:

1. Cambia `SCHEDULED_TASKS_PROVIDER` nel file `.env` o in Render
2. Riavvia l'applicazione
3. Se passi da APScheduler a Render Cron, assicurati di configurare i cron job in Render
4. Se passi da Render Cron a APScheduler, puoi rimuovere i cron job da Render (ma non è necessario)

---

## 🧪 Testing Locale

### Con APScheduler

```bash
# .env
SCHEDULED_TASKS_PROVIDER=apscheduler
WORKOUT_REMINDER_MORNING_CRON=*/5 * * * *  # Ogni 5 minuti per test

# Avvia il server
uvicorn app.main:app --reload

# I reminder partiranno automaticamente ogni 5 minuti
```

### Con Render Cron Jobs (simulazione)

```bash
# .env
SCHEDULED_TASKS_PROVIDER=render_cron
INTERNAL_API_SECRET=test-secret-123

# Avvia il server
uvicorn app.main:app --reload

# In un altro terminale, testa manualmente
curl -X POST "http://localhost:8000/notifications/cron/send-workout-reminders" \
  -H "X-Internal-API-Secret: test-secret-123"
```

---

## 📊 Monitoraggio

### Verifica Log

I log mostrano quale provider è attivo:

**Con APScheduler:**
```
Initializing APScheduler for scheduled tasks...
APScheduler started successfully
Workout reminder jobs scheduled: morning=0 8 * * *, evening=0 18 * * *
```

**Con Render Cron Jobs:**
```
Using Render Cron Jobs for scheduled tasks (external HTTP calls)
```

### Endpoint Status

```bash
GET /notifications/scheduler/status
```

Mostra:
- Provider attivo
- Se APScheduler è abilitato
- Lista dei job schedulati (se APScheduler)

---

## ⚠️ Note Importanti

### APScheduler

- I job vengono eseguiti nel processo web principale
- Se il processo si riavvia, i job vengono persi ma si reinizializzano automaticamente
- I job non vengono persi in caso di riavvio pianificato
- Consuma risorse del processo (minimo, ma presente)

### Render Cron Jobs

- Richiede che il servizio web sia sempre disponibile
- Se il servizio è in sleep (free tier), il cron job potrebbe fallire
- Nessun consumo di risorse quando non esegue job

---

## 🔍 Troubleshooting

### APScheduler non parte

1. Verifica che `apscheduler` sia installato: `pip list | grep apscheduler`
2. Controlla i log per errori di inizializzazione
3. Verifica che `SCHEDULED_TASKS_PROVIDER=apscheduler`
4. Controlla il formato delle espressioni cron

### Render Cron Jobs non funzionano

1. Verifica che il cron job sia configurato in Render dashboard
2. Controlla che `INTERNAL_API_SECRET` corrisponda
3. Verifica i log di Render per errori del curl
4. Testa manualmente l'endpoint con curl

### Nessuna notifica inviata

- Verifica che ci siano workout programmati per domani
- Controlla le preferenze utente (devono avere `workout_reminders` abilitato)
- Verifica device tokens attivi (per push) o email valida (per email)
- Controlla i log per dettagli specifici

