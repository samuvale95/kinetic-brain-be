# Modifiche Backend - Dashboard Integration

## 📋 Riepilogo Modifiche

### 1. Filtro Pian Inattivi nel Calendario ✅
- **File**: `app/services/workout_service.py`
- **Modifica**: Gli eventi di piani `paused` o `completed` NON vengono più mostrati
- **Logica**: Query esclude workout che appartengono a piani non attivi

### 2. Dashboard APIs ✅

#### GET `/dashboard/today-workouts` (NUOVO)
- Restituisce allenamenti previsti per oggi
- Response include: id, title, duration, zone, emoji, type, scheduled_date, completed

#### GET `/dashboard/stats` (ESTESO)
- Aggiunti campi:
  - `completed_workouts` - totale allenamenti completati
  - `avg_heart_rate` - media FC da sessioni
  - `total_distance` - distanza totale da Strava

### 3. Workout Plans APIs ✅

#### POST `/workouts/plans/{id}/archive`
- Archivia un piano (cambia status a "archived")

#### GET `/workouts/plans/{id}/statistics`
- Statistiche del piano: durata, workout completati, distanza totale, media FC/potenza, miglioramenti

#### PATCH `/workouts/{id}/complete` (CAMBIATO)
- Cambiato da POST (marco workout come completato)

#### GET `/workouts/sessions` (SISTEMATO)
- Sistemato ordine route per evitare conflitti con `/{workout_id}`

### 4. Weather API ✅

#### GET `/api/weather` (NUOVO)
- Provider: Open-Meteo (gratuito, nessuna registrazione)
- Fallback: OpenWeatherMap (se API key configurata)
- Cache: 30 minuti
- Coordinate: usa lat/lon se fornite, altrimenti città utente o default Roma

### 5. Profilo Utente - Campo City ✅

#### Modello Database
- **File**: `app/models/user.py`
- Aggiunto campo `city = Column(String(100))` a `UserProfile`

#### Schemas
- **File**: `app/schemas/user.py`
- Aggiunto `city` a `UserProfileCreate`, `UserProfileUpdate`, `UserProfileResponse`

#### Logica Weather
- **File**: `app/api/weather.py`
- Weather endpoint ora usa città dal profilo utente se non ci sono coordinate

## 🗂️ File Modificati

1. `app/services/workout_service.py` - Filtro piani inattivi
2. `app/api/dashboard.py` - Nuove dashboard APIs
3. `app/api/workouts.py` - Nuove workout plan APIs
4. `app/api/weather.py` - NUOVO - Weather endpoint
5. `app/models/user.py` - Campo city
6. `app/schemas/user.py` - Campo city negli schemas
7. `app/main.py` - Integrazione weather router
8. `env.example` - Aggiunto WEATHER_API_KEY (opzionale)

## 🚀 API Endpoints Finali

```
GET  /dashboard/today-workouts          ✅ NUOVO
GET  /dashboard/stats                   ✅ ESTESO
GET  /dashboard/upcoming                ✅ ESISTENTE
GET  /dashboard/progress                 ✅ ESISTENTE

POST /workouts/plans/{id}/archive      ✅ NUOVO
GET  /workouts/plans/{id}/statistics   ✅ NUOVO
PATCH /workouts/{id}/complete           ✅ MODIFICATO
GET  /workouts/sessions                 ✅ SISTEMATO

GET  /api/weather                       ✅ NUOVO
PUT  /profile/                          ✅ MODIFICATO (supporta city)
```

## ⚙️ Configurazione

- **WEATHER_API_KEY** (opzionale nel `.env`):
  - Se non configurato: usa Open-Meteo (gratis)
  - Se configurato: usa OpenWeatherMap

## 🎯 Note Importanti

- Tutti gli endpoint richiedono autenticazione JWT
- I piani inattivi NON vengono più mostrati nel calendario
- Weather usa Open-Meteo di default (gratis, nessuna configurazione)
- Campo `city` opzionale nel profilo utente
