# Setup Render Cron Jobs per Workout Reminders

## 📋 Configurazione

### 1. Configurare il Secret Interno

Aggiungi la variabile d'ambiente `INTERNAL_API_SECRET` nel tuo servizio Render:

1. Vai alla dashboard Render del tuo servizio
2. Sezione **Environment**
3. Aggiungi:
   ```
   INTERNAL_API_SECRET=il-tuo-secret-sicuro-qui
   ```
   (Usa un valore sicuro e casuale, tipo: `openssl rand -hex 32`)

### 2. Creare il Cron Job in Render

1. Nella dashboard Render, vai su **Cron Jobs** (o **Scheduled Jobs**)
2. Clicca su **New Cron Job**
3. Configura:

   **Nome**: `Send Workout Reminders - Morning`
   
   **Schedule**: `0 8 * * *` (ogni giorno alle 8:00 AM UTC)
   
   **Command**:
   ```bash
   curl -X POST "https://your-app.onrender.com/notifications/cron/send-workout-reminders" \
     -H "X-Internal-API-Secret: il-tuo-secret-sicuro-qui" \
     -H "Content-Type: application/json"
   ```
   
   ⚠️ **IMPORTANTE**: Sostituisci:
   - `your-app.onrender.com` con il tuo dominio Render
   - `il-tuo-secret-sicuro-qui` con lo stesso valore di `INTERNAL_API_SECRET`

4. (Opzionale) Crea un secondo cron job per reminder serali:
   
   **Nome**: `Send Workout Reminders - Evening`
   
   **Schedule**: `0 18 * * *` (ogni giorno alle 18:00 UTC / 8:00 PM CET)
   
   **Command**: (stesso del primo)

### 3. Verificare il Funzionamento

#### Test Manuale

Puoi testare l'endpoint manualmente:

```bash
curl -X POST "https://your-app.onrender.com/notifications/cron/send-workout-reminders?reminder_date=2024-01-15" \
  -H "X-Internal-API-Secret: il-tuo-secret-sicuro-qui" \
  -H "Content-Type: application/json"
```

#### Verifica Log

Controlla i log di Render per vedere i risultati:

```bash
# Nei log dovresti vedere:
[CRON] Starting workout reminder job for date: 2024-01-15
Found X workouts scheduled for 2024-01-15
Reminder for user Y: sent=True, push=True, email=True
[CRON] Workout reminder job completed: {...}
```

---

## 🔒 Sicurezza

L'endpoint è protetto da:
- **Header `X-Internal-API-Secret`**: Deve corrispondere a `INTERNAL_API_SECRET`
- **Nessuna autenticazione utente richiesta**: Endpoint interno

⚠️ **NOTA**: Non esporre mai `INTERNAL_API_SECRET` pubblicamente o nei log.

---

## 📅 Schedule Suggestions

### Fuso Orario

Render Cron Jobs usa **UTC**. Aggiusta lo schedule in base al tuo fuso orario:

- **8:00 AM UTC** = 9:00 AM CET (inverno) / 10:00 AM CEST (estate)
- **18:00 UTC** = 7:00 PM CET / 8:00 PM CEST

### Timing Consigliati

- **Mattina (8:00 UTC)**: Reminder per workout del giorno dopo (24h prima)
- **Sera (18:00 UTC)**: Reminder per workout del giorno dopo (14h prima)

Puoi anche inviare solo un reminder al giorno, ad esempio alle 8:00 UTC.

---

## 🧪 Testing Locale

Per testare localmente (senza Render):

```bash
# Imposta il secret
export INTERNAL_API_SECRET="test-secret-123"

# Avvia il server
uvicorn app.main:app --reload

# In un altro terminale, testa l'endpoint
curl -X POST "http://localhost:8000/notifications/cron/send-workout-reminders" \
  -H "X-Internal-API-Secret: test-secret-123" \
  -H "Content-Type: application/json"
```

---

## 📊 Parametri Endpoint

### Query Parameters

- `reminder_date` (opzionale): Data in formato `YYYY-MM-DD`. Default: domani.

Esempio:
```
/notifications/cron/send-workout-reminders?reminder_date=2024-01-20
```

### Response

```json
{
  "success": true,
  "reminder_date": "2024-01-20",
  "stats": {
    "total_workouts": 15,
    "notifications_sent": 12,
    "notifications_skipped": 3,
    "errors": 0,
    "unique_users_notified": 8
  }
}
```

---

## ⚠️ Troubleshooting

### Endpoint restituisce 401 Unauthorized

- Verifica che `INTERNAL_API_SECRET` sia impostato nel servizio Render
- Verifica che l'header `X-Internal-API-Secret` nel curl corrisponda esattamente
- Controlla i log per vedere se il secret è configurato

### Endpoint restituisce 503 Service Unavailable

- `INTERNAL_API_SECRET` non è configurato nel servizio
- Aggiungi la variabile d'ambiente in Render

### Nessuna notifica inviata

- Verifica che ci siano workout programmati per la data target
- Verifica che gli utenti abbiano abilitato `workout_reminders` nelle preferenze
- Verifica che gli utenti abbiano device token attivi (per push) o email valida (per email)
- Controlla i log per vedere i dettagli

### Cron Job non viene eseguito

- Verifica che il cron job sia attivo in Render
- Verifica la sintassi dello schedule (usa tool online per validare cron syntax)
- Controlla i log di Render per errori di esecuzione del curl

