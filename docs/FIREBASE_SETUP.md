# Configurazione Firebase Cloud Messaging (FCM) per Push Notifications

Questa guida spiega come configurare Firebase Cloud Messaging **API V1** per abilitare le push notifications nell'applicazione Kinetic Brain.

⚠️ **IMPORTANTE**: Questa guida è per FCM API V1. L'API Legacy non è più supportata da Firebase.

---

## 📋 Prerequisiti

- Account Google (per accedere a Firebase Console)
- Progetto Firebase esistente o possibilità di crearne uno nuovo
- Accesso alle variabili d'ambiente del backend (file `.env` o Render)

---

## 🚀 Passo 1: Creare un Progetto Firebase

### 1.1 Accedi a Firebase Console

1. Vai a [Firebase Console](https://console.firebase.google.com/)
2. Accedi con il tuo account Google

### 1.2 Crea un Nuovo Progetto

1. Clicca su **"Aggiungi progetto"** o **"Add project"**
2. Inserisci il nome del progetto (es. "Kinetic Brain")
3. (Opzionale) Disabilita Google Analytics se non necessario
4. Clicca **"Crea progetto"** e attendi la creazione

---

## 🔑 Passo 2: Abilitare FCM API V1

### 2.1 Abilita l'API FCM V1

1. Nel progetto Firebase, clicca sull'icona ⚙️ **Impostazioni** (in alto a sinistra)
2. Seleziona **"Impostazioni progetto"** o **"Project settings"**
3. Vai alla scheda **"Cloud Messaging"** o **"Cloud Messaging"**
4. Verifica che l'**API Firebase Cloud Messaging (V1)** sia abilitata
5. Se non è abilitata:
   - Clicca sui tre punti accanto a "API Firebase Cloud Messaging (V1)"
   - Seleziona **"Gestisci API in Google Cloud Console"**
   - Nella nuova scheda, clicca su **"Abilita"**
   - Torna alla console Firebase e aggiorna la pagina

### 2.2 Ottieni il Project ID

1. Nella pagina delle impostazioni Firebase, vai alla scheda **"Generale"**
2. Trova il **Project ID** (es. `kinetic-brain-123456`)
3. Copia questo ID - ti servirà per la configurazione

---

## 🔐 Passo 3: Creare un Service Account

### 3.1 Accedi alle Impostazioni del Progetto

1. Nel progetto Firebase, vai a **Impostazioni progetto** → **Account di servizio**
2. Oppure vai direttamente a [Google Cloud Console](https://console.cloud.google.com/) → Seleziona il progetto → **IAM & Admin** → **Service Accounts**

### 3.2 Crea o Seleziona un Service Account

1. Se non hai già un service account, clicca su **"Crea account di servizio"**
2. Inserisci un nome (es. "fcm-push-service")
3. Clicca **"Crea e continua"**
4. Assegna il ruolo **"Firebase Cloud Messaging API Admin"** o **"Firebase Cloud Messaging API Service Agent"**
5. Clicca **"Fatto"**

### 3.3 Genera la Chiave Privata

1. Nella lista degli account di servizio, clicca sull'account appena creato
2. Vai alla scheda **"Chiavi"** o **"Keys"**
3. Clicca su **"Aggiungi chiave"** → **"Crea nuova chiave"**
4. Seleziona formato **JSON**
5. Clicca **"Crea"** - il file JSON verrà scaricato automaticamente

⚠️ **IMPORTANTE**: Questo file JSON contiene credenziali sensibili. Non condividerlo pubblicamente o committarlo nel repository.

### 3.4 Prepara il Service Account JSON

Il file JSON scaricato avrà questo formato:

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "...",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

---

## ⚙️ Passo 4: Configurare il Backend

### 4.1 Variabili d'Ambiente

Aggiungi le seguenti variabili al tuo file `.env` o alle variabili d'ambiente di Render:

```env
# Firebase Cloud Messaging (FCM) API V1
# FCM_PROJECT_ID: Il Project ID di Firebase (es. "kinetic-brain-123456")
FCM_PROJECT_ID=your-project-id-123456

# FCM_SERVICE_ACCOUNT_JSON: Il contenuto completo del file JSON del service account
# Come stringa JSON su una singola riga (senza newline)
FCM_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"your-project-id","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n","client_email":"...","client_id":"...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"..."}
```

**Nota per Render/Environment Variables**:
- Se usi variabili d'ambiente, devi convertire il JSON in una singola riga
- Sostituisci i newline (`\n`) con `\\n` (doppio backslash)
- Assicurati che tutte le virgolette siano escape correttamente

**Esempio con Python per convertire il JSON**:
```python
import json

# Leggi il file JSON
with open('service-account-key.json', 'r') as f:
    service_account_data = json.load(f)

# Converti in stringa su una riga
json_string = json.dumps(service_account_data)
print(json_string)  # Copia questo output nella variabile d'ambiente
```

### 4.2 Verifica la Configurazione

Dopo aver impostato le variabili d'ambiente, riavvia l'applicazione. Nei log dovresti vedere:

```
✅ Se configurato correttamente: "FCM credentials initialized successfully"
❌ Se non configurato: "FCM_PROJECT_ID or FCM_SERVICE_ACCOUNT_JSON not configured - push notifications will not work"
```

---

## 📱 Passo 5: Configurare le App Mobile (iOS/Android)

### 5.1 Per Android

1. Vai a Firebase Console → **Impostazioni progetto** → **Le tue app**
2. Clicca su **"Aggiungi app"** → **Android**
3. Inserisci:
   - **Nome pacchetto Android**: Il package name della tua app (es. `com.kineticbrain.app`)
   - **Nickname app**: Nome descrittivo (opzionale)
4. Scarica il file `google-services.json`
5. Aggiungi `google-services.json` alla cartella `app/` del progetto Android
6. Segui le istruzioni per configurare il plugin Gradle

**Nota**: Il backend non ha bisogno del file `google-services.json` - serve solo per l'app mobile.

### 5.2 Per iOS

1. Vai a Firebase Console → **Impostazioni progetto** → **Le tue app**
2. Clicca su **"Aggiungi app"** → **iOS**
3. Inserisci:
   - **Bundle ID iOS**: Il bundle ID della tua app (es. `com.kineticbrain.app`)
   - **Nickname app**: Nome descrittivo (opzionale)
4. Scarica il file `GoogleService-Info.plist`
5. Aggiungi `GoogleService-Info.plist` al progetto Xcode
6. Segui le istruzioni per configurare le capability push notifications

**Nota**: Il backend non ha bisogno del file `GoogleService-Info.plist` - serve solo per l'app mobile.

---

## 🧪 Passo 6: Testare le Push Notifications

### 6.1 Verifica Configurazione Backend

Puoi verificare che il backend sia configurato correttamente controllando i log all'avvio:

```bash
# Avvia il server
uvicorn app.main:app --reload

# Cerca nei log:
# ✅ "PushService initialized" (se tutto ok)
# ❌ "FCM_SERVER_KEY not configured" (se manca la configurazione)
```

### 6.2 Test Manuale via API

Una volta che l'app mobile ha registrato un device token, puoi testare l'invio di una notifica:

```bash
# Endpoint per inviare notifiche (richiede autenticazione)
POST /notifications/send
Authorization: Bearer <your-token>
Content-Type: application/json

{
  "user_id": 1,
  "notification_type": "test",
  "title": "Test Notification",
  "body": "This is a test push notification"
}
```

### 6.3 Verifica Device Token Registrati

```bash
# Verifica i token registrati per un utente
GET /notifications/register-device
Authorization: Bearer <your-token>
```

---

## 🔍 Troubleshooting

### Problema: "FCM_PROJECT_ID or FCM_SERVICE_ACCOUNT_JSON not configured"

**Soluzione**:
1. Verifica che entrambe le variabili `FCM_PROJECT_ID` e `FCM_SERVICE_ACCOUNT_JSON` siano impostate
2. Assicurati di aver riavviato l'applicazione dopo aver aggiunto le variabili
3. Controlla che il JSON del service account sia valido e completo

### Problema: "Failed to initialize FCM credentials"

**Soluzione**:
- Verifica che il JSON del service account sia valido (usa un validatore JSON online)
- Controlla che il JSON sia su una singola riga senza interruzioni
- Assicurati che i newline nel `private_key` siano escape correttamente (`\\n`)
- Verifica che il service account abbia i permessi corretti (Firebase Cloud Messaging API Admin)

### Problema: "Cannot send push notification - failed to get access token"

**Soluzione**:
- Verifica che il service account sia attivo in Google Cloud Console
- Controlla che l'API FCM V1 sia abilitata nel progetto
- Verifica che il service account abbia il ruolo corretto

### Problema: Notifiche non arrivano ai dispositivi

**Possibili cause**:
1. **Token non registrato**: Verifica che l'app mobile abbia registrato correttamente il device token
2. **Token disattivato**: Controlla che il token sia attivo nel database (`device_tokens` table)
3. **Preferenze utente**: Verifica che l'utente abbia abilitato le push notifications nelle preferenze
4. **Token invalido**: Il sistema disattiva automaticamente i token invalidi. Controlla i log per errori FCM

### Problema: Errori FCM API

**Errori comuni FCM V1**:
- `INVALID_ARGUMENT`: Token non valido o formato errato
- `UNREGISTERED`: Token non più valido (dispositivo disinstallato app)
- `PERMISSION_DENIED`: Token da un progetto Firebase diverso o permessi insufficienti
- `UNAVAILABLE`: Servizio temporaneamente non disponibile (riprova più tardi)
- `INTERNAL`: Errore interno di Firebase (riprova più tardi)

**Soluzione**:
- Verifica che il `FCM_PROJECT_ID` corrisponda al progetto Firebase corretto
- Assicurati che l'app mobile usi lo stesso progetto Firebase del backend
- Controlla che i file di configurazione (`google-services.json` o `GoogleService-Info.plist`) siano corretti
- Verifica che il service account abbia i permessi necessari

---

## 📚 Informazioni Tecniche

### API Utilizzata

Il backend usa l'**API V1 di FCM** (`https://fcm.googleapis.com/v1/projects/{project_id}/messages:send`), che:
- ✅ È l'API moderna e raccomandata da Firebase
- ✅ Richiede autenticazione OAuth2 con Service Account
- ✅ Supporta tutte le piattaforme (iOS, Android, Web)
- ✅ Offre migliore sicurezza e controllo degli accessi

### Formato Richiesta FCM V1

Il backend invia richieste nel seguente formato:

```json
{
  "message": {
    "token": "<device-token>",
    "notification": {
      "title": "Notification Title",
      "body": "Notification Body"
    },
    "data": {
      "key": "value"
    },
    "apns": {
      "payload": {
        "aps": {
          "alert": {
            "title": "Notification Title",
            "body": "Notification Body"
          },
          "sound": "default",
          "badge": 1
        }
      }
    },
    "android": {
      "priority": "high",
      "notification": {
        "title": "Notification Title",
        "body": "Notification Body",
        "sound": "default",
        "channel_id": "default"
      }
    }
  }
}
```

### Autenticazione OAuth2

- Il backend usa `google-auth` per ottenere token OAuth2
- I token vengono automaticamente rinnovati quando scadono
- L'autenticazione avviene tramite Service Account JSON

### Gestione Token Invalidi

Il sistema gestisce automaticamente i token invalidi:
- Quando FCM V1 restituisce `INVALID_ARGUMENT`, `UNREGISTERED`, o `PERMISSION_DENIED`
- Il token viene automaticamente disattivato nel database
- I log mostrano quando un token viene disattivato

---

## 🔐 Sicurezza

### Best Practices

1. **Non committare la Server Key**: Aggiungi `FCM_SERVER_KEY` al `.gitignore`
2. **Usa variabili d'ambiente**: Non hardcodare la chiave nel codice
3. **Limita l'accesso**: Solo sviluppatori autorizzati dovrebbero avere accesso alla Server Key
4. **Rotazione chiavi**: Se sospetti che la chiave sia compromessa, rigenerala in Firebase Console

### Rotazione del Service Account Key

Se devi rigenerare la chiave del Service Account:

1. Vai a Google Cloud Console → **IAM & Admin** → **Service Accounts**
2. Seleziona il service account utilizzato per FCM
3. Vai alla scheda **"Keys"** o **"Chiavi"**
4. Elimina la vecchia chiave (opzionale, per sicurezza)
5. Crea una nuova chiave JSON
6. Aggiorna `FCM_SERVICE_ACCOUNT_JSON` nelle variabili d'ambiente con il nuovo JSON
7. Riavvia l'applicazione

⚠️ **Nota**: La vecchia chiave continuerà a funzionare finché non viene eliminata. Per sicurezza, elimina la vecchia chiave dopo aver configurato la nuova.

---

## 📖 Riferimenti

- [Firebase Console](https://console.firebase.google.com/)
- [Documentazione FCM Legacy API](https://firebase.google.com/docs/cloud-messaging/http-server-ref)
- [Documentazione FCM per iOS](https://firebase.google.com/docs/cloud-messaging/ios/client)
- [Documentazione FCM per Android](https://firebase.google.com/docs/cloud-messaging/android/client)

---

## ✅ Checklist Configurazione

- [ ] Progetto Firebase creato
- [ ] API FCM V1 abilitata nel progetto Firebase
- [ ] Service Account creato con ruolo Firebase Cloud Messaging API Admin
- [ ] Chiave privata JSON del Service Account generata e scaricata
- [ ] Variabile `FCM_PROJECT_ID` impostata nel backend
- [ ] Variabile `FCM_SERVICE_ACCOUNT_JSON` impostata nel backend (JSON su singola riga)
- [ ] Applicazione riavviata dopo la configurazione
- [ ] Log verificati: "FCM credentials initialized successfully"
- [ ] App mobile configurata con `google-services.json` (Android) o `GoogleService-Info.plist` (iOS)
- [ ] Device token registrato correttamente
- [ ] Test di invio notifica eseguito con successo

---

## 🆘 Supporto

Se riscontri problemi:

1. Controlla i log dell'applicazione per errori specifici
2. Verifica la configurazione Firebase Console
3. Testa con un device token valido usando l'endpoint `/notifications/send`
4. Controlla la documentazione Firebase ufficiale

