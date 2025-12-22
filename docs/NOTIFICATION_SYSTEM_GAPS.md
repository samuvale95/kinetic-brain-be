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

### 2. **Notification History/Log** ✅ IMPLEMENTATO

**Soluzione implementata**: Tabella `notification_logs` con logging automatico.

**File creati/modificati**:
- ✅ Migrazione `migrations/versions/add_notification_logs_table.py` - crea tabella con indici
- ✅ Modello `app/models/notification.py` - aggiunto `NotificationLog`
- ✅ Schema `app/schemas/notification.py` - aggiunto `NotificationLogResponse` e `NotificationLogListResponse`
- ✅ Servizio `app/services/notification_service.py` - aggiunto `_log_notification()` e `get_notification_history()`
- ✅ Endpoint `app/api/notifications.py` - aggiunto `GET /notifications/history`

**Come funziona**:
- Ogni notifica inviata viene automaticamente loggata in `notification_logs`
- Include: user_id, notification_type, channel, title, body, data, status (sent/failed/skipped), error_message, sent_at
- Endpoint `/notifications/history` permette di vedere la cronologia con filtri e paginazione
- Utile per debug, analytics, e tracciamento delle notifiche

---

### 3. **Miglioramento Gestione Token FCM Invalidi** ✅ IMPLEMENTATO

**Soluzione implementata**: Parsing completo della risposta FCM con disattivazione automatica dei token invalidi.

**File modificati**:
- ✅ `app/services/push_service.py` - migliorato `_send_fcm_message()` per restituire error_code
- ✅ `app/services/push_service.py` - `send_push()` ora disattiva automaticamente token invalidi

**Come funziona**:
- `_send_fcm_message()` ora restituisce `Tuple[bool, Optional[str]]` con success e error_code
- Identifica errori di token invalido: `InvalidRegistration`, `NotRegistered`, `MismatchSenderId`
- Quando viene rilevato un token invalido, viene automaticamente disattivato chiamando `device_token_service.deactivate_device()`
- I token disattivati vengono aggiunti a `results["invalid_tokens"]` per reporting
- Migliora la robustezza del sistema evitando di tentare di inviare a token non più validi

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

## 📊 Stato Implementazione

1. **✅ COMPLETATO**: Workout Reminders - funzionalità core implementata
2. **✅ COMPLETATO**: Notification History - logging e endpoint implementati
3. **✅ COMPLETATO**: Gestione token FCM - disattivazione automatica token invalidi
4. **✅ COMPLETATO**: Infrastruttura scheduler - Render Cron Jobs e APScheduler supportati

**🎉 Tutte le funzionalità mancanti sono state implementate!**

---

## 🔍 File di Riferimento

- `app/models/notification.py` - modelli esistenti
- `app/services/notification_service.py` - servizio principale
- `app/services/push_service.py` - servizio push
- `app/api/notifications.py` - endpoint API
- `app/api/workouts.py` - integrazioni esistenti (righe 166-182, 330-345, 750-766, 1066-1083)

