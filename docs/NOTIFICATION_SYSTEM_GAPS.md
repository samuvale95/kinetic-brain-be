# Gap Analysis: Sistema di Notifiche

## 📋 Cosa è già implementato ✅

### 1. **Modelli e Database**
- ✅ Tabella `notification_preferences` con preferenze email e push
- ✅ Tabella `device_tokens` per gestione token FCM
- ✅ Preferenze per tutti i tipi di notifica:
  - `workout_reminders`
  - `new_workout`
  - `workout_completed`
  - `plan_updates`
  - `weekly_generation`

### 2. **Servizi**
- ✅ `NotificationService` - gestione preferenze e invio notifiche
- ✅ `PushService` - invio push notifications via FCM
- ✅ `DeviceTokenService` - gestione device tokens
- ✅ `EmailService` - invio email (include `send_notification_email`)

### 3. **API Endpoints**
- ✅ `POST /notifications/register-device` - registrazione device token
- ✅ `DELETE /notifications/register-device/{token_id}` - disattivazione token
- ✅ `POST /notifications/send` - invio notifiche (endpoint interno)
- ✅ `GET /profile/notification-preferences` - lettura preferenze
- ✅ `PUT /profile/notification-preferences` - aggiornamento preferenze

### 4. **Integrazioni Esistenti**
- ✅ Notifica `new_workout` quando viene creato un piano progressivo
- ✅ Notifica `weekly_generation` quando viene generata una settimana automaticamente
- ✅ Notifica `plan_updates` quando un piano viene aggiornato
- ✅ Notifica `workout_completed` quando un workout viene completato

---

## ⚠️ Cosa manca

### 1. **Workout Reminders** ✅ IMPLEMENTATO

**Soluzione implementata**: Usa Render Cron Jobs con endpoint HTTP interno protetto.

**File creati**:
- ✅ `app/services/workout_reminder_service.py` - servizio per gestire i reminder
- ✅ `app/api/notifications.py` - endpoint `/notifications/cron/send-workout-reminders`
- ✅ `docs/RENDER_CRON_SETUP.md` - documentazione completa per setup

**Come funziona**:
- Render Cron Job chiama l'endpoint ogni giorno (es. alle 8:00 UTC)
- L'endpoint è protetto con `INTERNAL_API_SECRET` header
- Il servizio trova tutti i workout programmati per domani
- Invia notifiche push/email agli utenti che hanno abilitato i reminder
- Rispetta le preferenze utente per canale (email/push)

**Configurazione**:
1. Imposta `INTERNAL_API_SECRET` in Render environment variables
2. Crea un Cron Job in Render che chiama l'endpoint
3. Vedi `docs/RENDER_CRON_SETUP.md` per dettagli completi

---

### 2. **Notification History/Log** 🟡 PRIORITÀ MEDIA

**Problema**: Non c'è tracciamento delle notifiche inviate.

**Cosa serve**:
- Tabella `notification_logs` per tracciare tutte le notifiche inviate
- Campi: user_id, notification_type, channel, title, body, status (sent/failed), sent_at, error_message
- Endpoint `GET /notifications/history` per vedere cronologia utente
- Utile per debug, analytics, e potenzialmente ri-invio di notifiche fallite

**File da creare/modificare**:
- Migrazione per tabella `notification_logs`
- Modello `app/models/notification.py` (aggiungere `NotificationLog`)
- Schema `app/schemas/notification.py` (aggiungere `NotificationLogResponse`)
- Servizio per logging (estendere `NotificationService`)
- Endpoint `app/api/notifications.py` (aggiungere GET /history)

---

### 3. **Miglioramento Gestione Token FCM Invalidi** 🟡 PRIORITÀ MEDIA

**Problema**: Il `PushService` ha commenti che indicano che dovrebbe gestire meglio i token invalidi, ma l'implementazione è incompleta.

**Cosa serve**:
- Parsing corretto della risposta FCM per identificare token invalidi
- Mark automatico dei token come `is_active=False` quando FCM restituisce errori specifici:
  - `InvalidRegistration`
  - `NotRegistered`
  - `MismatchSenderId`

**File da modificare**:
- `app/services/push_service.py` - migliorare `_send_fcm_message` per parsare correttamente errori FCM e chiamare `device_token_service.deactivate_device()` quando necessario

---

### 4. **Infrastruttura Task Schedulati** ✅ IMPLEMENTATO

**Soluzione scelta**: **Render Cron Jobs** (endpoint HTTP chiamato su schedule)

**Perché Render Cron Jobs**:
- ✅ Nativo di Render, nessuna dipendenza aggiuntiva
- ✅ Nessun setup complesso (Redis, Celery, etc.)
- ✅ Gestione semplice tramite dashboard Render
- ✅ Affidabile e gratuito per uso base

**File creati/modificati**:
- ✅ `app/services/workout_reminder_service.py` - logica reminder
- ✅ `app/api/notifications.py` - endpoint cron protetto
- ✅ `app/config.py` - aggiunto `internal_api_secret`
- ✅ `env.example` - documentato `INTERNAL_API_SECRET`

**Alternativa (non implementata)**:
Se in futuro serve più controllo, si può usare **APScheduler** nello stesso processo web, ma Render Cron Jobs è sufficiente per le esigenze attuali.

---

## 📊 Priorità di Implementazione

1. **🔴 ALTA**: Workout Reminders - funzionalità core mancante
2. **🟡 MEDIA**: Notification History - utile per debug e UX
3. **🟡 MEDIA**: Gestione token FCM - migliora robustezza
4. **🟡 MEDIA**: Infrastruttura scheduler - necessario per reminder

---

## 🔍 File di Riferimento

- `app/models/notification.py` - modelli esistenti
- `app/services/notification_service.py` - servizio principale
- `app/services/push_service.py` - servizio push
- `app/api/notifications.py` - endpoint API
- `app/api/workouts.py` - integrazioni esistenti (righe 166-182, 330-345, 750-766, 1066-1083)

