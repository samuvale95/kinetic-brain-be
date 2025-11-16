# Integrazione Strava - Kinetic Brain Backend

## 🚀 Panoramica

L'integrazione Strava permette di:
- **Connettere** l'account Strava dell'utente
- **Sincronizzare** automaticamente gli allenamenti da Strava
- **Matcheggiare** intelligentemente gli allenamenti con il piano di allenamento
- **Visualizzare** tutti i dati degli allenamenti Strava nel frontend

## 📋 Configurazione

### 1. Variabili d'Ambiente

Aggiungi al file `.env`:

```env
# Strava OAuth
STRAVA_CLIENT_ID=your-strava-client-id
STRAVA_CLIENT_SECRET=your-strava-client-secret
STRAVA_REDIRECT_URI=http://localhost:8000/auth/strava/callback
STRAVA_WEBHOOK_VERIFY_TOKEN=your-webhook-verify-token
```

### 2. Setup Strava App

1. Vai su [Strava API Settings](https://www.strava.com/settings/api)
2. Crea una nuova applicazione
3. Configura:
   - **Authorization Callback Domain**: `localhost:8000`
   - **Website**: `http://localhost:8080`
   - **Application Description**: `Kinetic Brain Training App`

## 🗄️ Database

### Tabelle Create

```sql
-- Account Strava collegati agli utenti
strava_accounts (
    id, user_id, strava_id, access_token, refresh_token,
    token_expires_at, firstname, lastname, profile_medium,
    city, state, country, sex, premium, summit
)

-- Attività Strava sincronizzate
strava_activities (
    id, strava_account_id, strava_activity_id, workout_id,
    name, type, sport_type, start_date, start_date_local,
    distance, moving_time, elapsed_time, average_speed,
    average_heartrate, calories, is_synced, sync_status,
    raw_data (JSONB)
)

-- Webhook Strava per aggiornamenti real-time
strava_webhooks (
    id, object_type, object_id, aspect_type,
    event_time, owner_id, subscription_id,
    is_processed, raw_data (JSONB)
)
```

## 🔌 API Endpoints

### Autenticazione Strava

```bash
# 1. Ottieni URL di autorizzazione Strava
GET /strava/auth/url
Authorization: Bearer <access_token>

Response:
{
  "auth_url": "https://www.strava.com/oauth/authorize?...",
  "state": "user_id"
}
```

```bash
# 2. Gestisci callback OAuth
POST /strava/auth/callback
{
  "code": "authorization_code_from_strava",
  "state": "user_id"
}

Response:
{
  "success": true,
  "message": "Strava account connected successfully",
  "strava_account_id": 123,
  "athlete": {...}
}
```

### Gestione Account

```bash
# Ottieni account Strava dell'utente
GET /strava/account
Authorization: Bearer <access_token>

# Disconnetti account Strava
DELETE /strava/account
Authorization: Bearer <access_token>
```

### Sincronizzazione Attività

```bash
# Sincronizza attività Strava
POST /strava/sync
Authorization: Bearer <access_token>
{
  "days_back": 30
}

Response:
{
  "total_activities": 45,
  "new_activities": 12,
  "already_synced": 33
}
```

```bash
# Matcheggia attività con allenamenti programmati
POST /strava/match
Authorization: Bearer <access_token>

Response:
{
  "total_unmatched": 15,
  "matched_count": 8,
  "matches": [
    {
      "activity_id": 123,
      "activity_name": "Morning Run",
      "workout_id": 456,
      "workout_title": "Easy Run 5K",
      "date": "2025-10-25"
    }
  ]
}
```

### Visualizzazione Attività

```bash
# Ottieni attività Strava dell'utente
GET /strava/activities?limit=50&offset=0
Authorization: Bearer <access_token>

Response:
[
  {
    "id": 123,
    "strava_activity_id": 987654321,
    "name": "Morning Run",
    "type": "Run",
    "sport_type": "Run",
    "start_date": "2025-10-25T06:00:00Z",
    "start_date_local": "2025-10-25T08:00:00+02:00",
    "distance": 5000.0,
    "moving_time": 1800,
    "elapsed_time": 1900,
    "average_speed": 2.78,
    "average_heartrate": 150.0,
    "calories": 400.0,
    "is_synced": true,
    "sync_status": "matched",
    "workout_match": {
      "id": 456,
      "title": "Easy Run 5K",
      "type": "endurance",
      "scheduled_date": "2025-10-25"
    }
  }
]
```

```bash
# Ottieni attività specifica
GET /strava/activities/{activity_id}
Authorization: Bearer <access_token>

# Aggiorna stato di sincronizzazione
PUT /strava/activities/{activity_id}/sync-status?sync_status=manual
Authorization: Bearer <access_token>
```

### Webhook Strava

```bash
# Endpoint per webhook Strava (pubblico)
POST /strava/webhook
{
  "object_type": "activity",
  "object_id": 987654321,
  "aspect_type": "create",
  "event_time": 1698240000,
  "owner_id": 123456789,
  "subscription_id": 1
}
```

## 🧠 Algoritmo di Matching

Il sistema usa un algoritmo intelligente per matcheggiare le attività Strava con gli allenamenti programmati:

### Criteri di Matching

1. **Data** (peso: 100 punti)
   - Stessa data: +100 punti
   - ±1 giorno: +50 punti
   - ±3 giorni: +25 punti

2. **Tipo di Sport** (peso: 30 punti)
   - Tipo identico: +30 punti
   - Tipo simile: +20 punti

3. **Durata** (peso: 20 punti)
   - Differenza ≤10 min: +20 punti
   - Differenza ≤30 min: +10 punti

### Soglia di Matching

- **Minimo**: 50 punti per considerare un match
- **Priorità**: Match con punteggio più alto

### Tipi di Sport Simili

```python
similar_types = {
    "run": ["running", "jog", "trail"],
    "ride": ["cycling", "bike", "bicycle"],
    "swim": ["swimming", "pool", "open water"],
    "walk": ["walking", "hike", "trek"]
}
```

## 🔄 Flusso di Sincronizzazione

### 1. Connessione Account
```
Frontend → GET /strava/auth/url → Strava OAuth → POST /strava/auth/callback
```

### 2. Sincronizzazione Manuale
```
Frontend → POST /strava/sync → Strava API → Salva nel DB
```

### 3. Matching Automatico
```
Frontend → POST /strava/match → Algoritmo matching → Aggiorna workout status
```

### 4. Sincronizzazione Real-time (Webhook)
```
Strava → POST /strava/webhook → Processa aggiornamento → Notifica frontend
```

## 📊 Dati Salvati

### Informazioni Complete Attività

- **Metadati**: Nome, tipo, data, durata
- **Metriche**: Distanza, velocità, frequenza cardiaca
- **Ambientali**: Temperatura, altitudine
- **Dettagliati**: Split times, segmenti, sforzi migliori
- **Raw Data**: Risposta completa API Strava (JSONB)

### Stati di Sincronizzazione

- `pending`: Attività non ancora processata
- `matched`: Matcheggiata automaticamente con workout
- `manual`: Matcheggiata manualmente dall'utente
- `ignored`: Ignorata dall'utente

## 🎯 Integrazione Frontend

### Componenti Suggeriti

1. **StravaConnect**: Componente per connettere account
2. **StravaSync**: Componente per sincronizzazione manuale
3. **StravaActivities**: Lista attività con filtri
4. **ActivityMatch**: Visualizzazione match con workout
5. **StravaStats**: Statistiche e grafici

### Esempio di Utilizzo

```javascript
// 1. Connetti account Strava
const connectStrava = async () => {
  const response = await fetch('/api/strava/auth/url', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const { auth_url } = await response.json();
  window.location.href = auth_url;
};

// 2. Sincronizza attività
const syncActivities = async () => {
  const response = await fetch('/api/strava/sync', {
    method: 'POST',
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ days_back: 30 })
  });
  const result = await response.json();
  console.log(`Sincronizzate ${result.new_activities} nuove attività`);
};

// 3. Matcheggia con workout
const matchActivities = async () => {
  const response = await fetch('/api/strava/match', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const result = await response.json();
  console.log(`Matcheggiate ${result.matched_count} attività`);
};

// 4. Ottieni attività
const getActivities = async () => {
  const response = await fetch('/api/strava/activities?limit=50', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const activities = await response.json();
  return activities;
};
```

## 🔒 Sicurezza

### Token Management

- **Access Token**: Scadenza automatica, refresh automatico
- **Refresh Token**: Salvato criptato nel database
- **Webhook Verification**: Token di verifica per webhook

### Permessi Strava

- `read`: Lettura profilo atleta
- `activity:read_all`: Lettura tutte le attività
- `activity:write`: Scrittura attività (per future funzionalità)

## 🚀 Prossimi Sviluppi

### Funzionalità Future
1. **Sincronizzazione Automatica**: Cron job per sync periodico
2. **Analisi Performance**: Confronto con obiettivi piano
3. **Notifiche**: Alert per allenamenti mancati
4. **Social Features**: Condivisione risultati
5. **Integrazione Garmin**: Supporto per altri dispositivi

### Ottimizzazioni
1. **Caching**: Cache delle attività per performance
2. **Batch Processing**: Elaborazione batch per grandi volumi
3. **Rate Limiting**: Gestione limiti API Strava
4. **Error Handling**: Gestione robusta degli errori

## 📝 Note Implementative

### Limitazioni API Strava

- **Rate Limit**: 1000 requests/15min, 10000 requests/day
- **Scope**: Alcuni dati richiedono permessi premium
- **Webhook**: Limitati a 5 webhook per applicazione

### Best Practices
1. **Token Refresh**: Refresh automatico prima della scadenza
2. **Error Handling**: Gestione graceful degli errori API
3. **Data Validation**: Validazione dati ricevuti da Strava
4. **Logging**: Log dettagliato per debugging

---

## ✅ Status Implementazione

- ✅ **OAuth Strava**: Configurazione e autenticazione
- ✅ **Database Models**: Tabelle e relazioni
- ✅ **API Endpoints**: Tutti gli endpoint necessari
- ✅ **Sincronizzazione**: Download e salvataggio attività
- ✅ **Matching Algorithm**: Algoritmo intelligente di matching
- ✅ **Webhook Support**: Gestione notifiche real-time
- ✅ **Error Handling**: Gestione errori robusta
- ✅ **Documentation**: Documentazione completa

**L'integrazione Strava è completamente implementata e pronta per l'uso!** 🎉


