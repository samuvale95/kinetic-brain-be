# Configurazione Push Notifications per React Native iOS

Questa guida completa spiega come configurare le push notifications Firebase Cloud Messaging (FCM) per l'app React Native iOS (Xcode).

---

## 📋 Prerequisiti

- Progetto React Native esistente
- Xcode installato (versione 14.0 o superiore)
- Account Apple Developer (per configurare le capability)
- Progetto Firebase configurato (vedi `docs/FIREBASE_SETUP.md`)
- File `GoogleService-Info.plist` scaricato da Firebase Console

---

## 🚀 Passo 1: Installazione Dipendenze

### 1.1 Installa le Librerie Necessarie

```bash
# Installa Firebase Messaging per React Native
npm install @react-native-firebase/app @react-native-firebase/messaging

# Oppure con yarn
yarn add @react-native-firebase/app @react-native-firebase/messaging

# Installa AsyncStorage per salvare il token localmente (opzionale ma consigliato)
npm install @react-native-async-storage/async-storage
```

### 1.2 Installa le Dipendenze iOS

```bash
cd ios
pod install
cd ..
```

---

## 📱 Passo 2: Configurazione Xcode

### 2.1 Aggiungi GoogleService-Info.plist

1. Apri il progetto in Xcode:
   ```bash
   open ios/YourApp.xcworkspace
   ```
   ⚠️ **IMPORTANTE**: Usa `.xcworkspace`, non `.xcodeproj`

2. Trascina il file `GoogleService-Info.plist` nella cartella del progetto iOS
   - Seleziona **"Copy items if needed"**
   - Assicurati che sia aggiunto al target dell'app

3. Verifica che il file sia presente nel progetto:
   - Seleziona il progetto in Xcode
   - Vai alla scheda **"Build Phases"**
   - Espandi **"Copy Bundle Resources"**
   - Verifica che `GoogleService-Info.plist` sia presente

### 2.2 Configura le Capability Push Notifications

1. In Xcode, seleziona il progetto (icona blu in alto)
2. Seleziona il **Target** dell'app
3. Vai alla scheda **"Signing & Capabilities"**
4. Clicca su **"+ Capability"**
5. Aggiungi **"Push Notifications"**
6. Aggiungi **"Background Modes"** e abilita:
   - ✅ **Remote notifications**

### 2.3 Configura l'App ID in Apple Developer

1. Vai a [Apple Developer Portal](https://developer.apple.com/account/)
2. Vai a **Certificates, Identifiers & Profiles**
3. Seleziona il tuo **App ID**
4. Abilita **Push Notifications**
5. Clicca **Save**

### 2.4 Genera e Scarica i Certificati APNs

#### Opzione A: Certificati APNs (Development)

1. In Apple Developer Portal → **Certificates**
2. Clicca **"+"** per creare un nuovo certificato
3. Seleziona **"Apple Push Notification service SSL (Sandbox)"**
4. Seleziona il tuo App ID
5. Segui le istruzioni per generare un CSR (Certificate Signing Request)
6. Scarica il certificato e installalo nel Keychain

#### Opzione B: Key APNs (Raccomandato per FCM)

Firebase Cloud Messaging può usare le **APNs Auth Key** invece dei certificati:

1. In Apple Developer Portal → **Keys**
2. Clicca **"+"** per creare una nuova chiave
3. Nome: "APNs Auth Key"
4. Abilita **Apple Push Notifications service (APNs)**
5. Clicca **Continue** → **Register**
6. Scarica la chiave (`.p8`) - **puoi scaricarla solo una volta!**
7. In Firebase Console → **Project Settings** → **Cloud Messaging**
8. Nella sezione **Apple app configuration**, carica la chiave `.p8`
9. Inserisci la **Key ID** e il **Team ID**

---

## 🔧 Passo 3: Configurazione Firebase in React Native

### 3.1 Crea un File di Configurazione Firebase

Crea un file `src/services/firebase.js` (o nella cartella che preferisci):

```javascript
import messaging from '@react-native-firebase/messaging';
import { Platform } from 'react-native';

class FirebaseService {
  /**
   * Richiedi permessi per le notifiche push
   * @returns {Promise<boolean>} true se i permessi sono stati concessi
   */
  async requestPermission() {
    try {
      const authStatus = await messaging().requestPermission();
      const enabled =
        authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
        authStatus === messaging.AuthorizationStatus.PROVISIONAL;

      if (enabled) {
        console.log('Authorization status:', authStatus);
        return true;
      } else {
        console.log('Permission denied');
        return false;
      }
    } catch (error) {
      console.error('Error requesting permission:', error);
      return false;
    }
  }

  /**
   * Ottieni il token FCM del dispositivo
   * @returns {Promise<string|null>} FCM token o null se non disponibile
   */
  async getToken() {
    try {
      const token = await messaging().getToken();
      console.log('FCM Token:', token);
      return token;
    } catch (error) {
      console.error('Error getting FCM token:', error);
      return null;
    }
  }

  /**
   * Elimina il token FCM (utile per logout)
   * @returns {Promise<void>}
   */
  async deleteToken() {
    try {
      await messaging().deleteToken();
      console.log('FCM token deleted');
    } catch (error) {
      console.error('Error deleting FCM token:', error);
    }
  }

  /**
   * Ottieni il nuovo token quando viene aggiornato
   * @param {Function} callback Funzione chiamata con il nuovo token
   * @returns {Function} Funzione per rimuovere il listener
   */
  onTokenRefresh(callback) {
    return messaging().onTokenRefresh(callback);
  }

  /**
   * Gestisci notifiche quando l'app è in foreground
   * @param {Function} callback Funzione chiamata quando arriva una notifica
   * @returns {Function} Funzione per rimuovere il listener
   */
  onMessage(callback) {
    return messaging().onMessage(callback);
  }

  /**
   * Gestisci click su notifiche quando l'app è in background/terminata
   * @param {Function} callback Funzione chiamata quando l'utente clicca su una notifica
   * @returns {Function} Funzione per rimuovere il listener
   */
  onNotificationOpenedApp(callback) {
    return messaging().onNotificationOpenedApp(callback);
  }

  /**
   * Controlla se l'app è stata aperta da una notifica
   * @returns {Promise<RemoteMessage|null>} Messaggio della notifica o null
   */
  async getInitialNotification() {
    try {
      const remoteMessage = await messaging().getInitialNotification();
      if (remoteMessage) {
        console.log('Notification caused app to open:', remoteMessage);
        return remoteMessage;
      }
      return null;
    } catch (error) {
      console.error('Error getting initial notification:', error);
      return null;
    }
  }
}

export default new FirebaseService();
```

### 3.2 Crea un Hook per le Notifiche

Crea `src/hooks/usePushNotifications.js`:

```javascript
import { useState, useEffect, useRef } from 'react';
import { Platform, Alert, AppState } from 'react-native';
import FirebaseService from '../services/firebase';
import AsyncStorage from '@react-native-async-storage/async-storage';

const TOKEN_STORAGE_KEY = '@fcm_token';
const DEVICE_ID_STORAGE_KEY = '@device_id';
const APP_VERSION = '1.0.0'; // Sostituisci con la versione reale dell'app

const usePushNotifications = (apiClient) => {
  const [fcmToken, setFcmToken] = useState(null);
  const [deviceId, setDeviceId] = useState(null);
  const [isRegistered, setIsRegistered] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Genera o recupera device ID
  const getOrCreateDeviceId = async () => {
    try {
      let storedDeviceId = await AsyncStorage.getItem(DEVICE_ID_STORAGE_KEY);
      if (!storedDeviceId) {
        // Genera un device ID univoco
        storedDeviceId = `${Platform.OS}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        await AsyncStorage.setItem(DEVICE_ID_STORAGE_KEY, storedDeviceId);
      }
      return storedDeviceId;
    } catch (error) {
      console.error('Error getting device ID:', error);
      return `${Platform.OS}-${Date.now()}`;
    }
  };

  // Registra il token sul backend
  const registerTokenOnBackend = async (token, deviceId) => {
    try {
      const response = await apiClient.post('/notifications/register-device', {
        device_token: token,
        platform: 'ios',
        device_id: deviceId,
        app_version: APP_VERSION,
      });

      console.log('Token registered on backend:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error registering token on backend:', error);
      throw error;
    }
  };

  // Inizializza le notifiche push
  const initializePushNotifications = async () => {
    try {
      setIsLoading(true);

      // 1. Richiedi permessi
      const hasPermission = await FirebaseService.requestPermission();
      if (!hasPermission) {
        Alert.alert(
          'Permessi Notifiche',
          'Le notifiche push sono disabilitate. Abilitalle nelle impostazioni per ricevere notifiche.',
          [{ text: 'OK' }]
        );
        setIsLoading(false);
        return;
      }

      // 2. Ottieni o crea device ID
      const currentDeviceId = await getOrCreateDeviceId();
      setDeviceId(currentDeviceId);

      // 3. Ottieni FCM token
      const token = await FirebaseService.getToken();
      if (!token) {
        console.warn('FCM token not available');
        setIsLoading(false);
        return;
      }

      setFcmToken(token);
      await AsyncStorage.setItem(TOKEN_STORAGE_KEY, token);

      // 4. Registra token sul backend
      try {
        await registerTokenOnBackend(token, currentDeviceId);
        setIsRegistered(true);
      } catch (error) {
        console.error('Failed to register token on backend:', error);
        // Continua comunque, il token è valido
      }

      // 5. Ascolta aggiornamenti del token
      FirebaseService.onTokenRefresh(async (newToken) => {
        console.log('FCM token refreshed:', newToken);
        setFcmToken(newToken);
        await AsyncStorage.setItem(TOKEN_STORAGE_KEY, newToken);
        
        // Re-registra sul backend
        try {
          await registerTokenOnBackend(newToken, currentDeviceId);
        } catch (error) {
          console.error('Failed to re-register token:', error);
        }
      });

      setIsLoading(false);
    } catch (error) {
      console.error('Error initializing push notifications:', error);
      setIsLoading(false);
    }
  };

  // Rimuovi registrazione (per logout)
  const unregisterToken = async () => {
    try {
      await FirebaseService.deleteToken();
      setFcmToken(null);
      await AsyncStorage.removeItem(TOKEN_STORAGE_KEY);
      setIsRegistered(false);
    } catch (error) {
      console.error('Error unregistering token:', error);
    }
  };

  useEffect(() => {
    initializePushNotifications();

    // Cleanup
    return () => {
      // I listener vengono rimossi automaticamente quando il componente viene smontato
    };
  }, []);

  return {
    fcmToken,
    deviceId,
    isRegistered,
    isLoading,
    initializePushNotifications,
    unregisterToken,
  };
};

export default usePushNotifications;
```

---

## 📲 Passo 4: Integrazione nell'App

### 4.1 Configura il Componente Root

Nel tuo file principale (es. `App.js` o `App.tsx`):

```javascript
import React, { useEffect, useRef } from 'react';
import { Alert, AppState } from 'react-native';
import messaging from '@react-native-firebase/messaging';
import FirebaseService from './src/services/firebase';
import usePushNotifications from './src/hooks/usePushNotifications';
import { apiClient } from './src/services/api'; // Il tuo client API

function App() {
  const { fcmToken, isRegistered } = usePushNotifications(apiClient);
  const appState = useRef(AppState.currentState);

  useEffect(() => {
    // Gestisci notifiche quando l'app è in foreground
    const unsubscribeForeground = FirebaseService.onMessage(async (remoteMessage) => {
      console.log('Foreground notification:', remoteMessage);
      
      // Mostra un alert o una notifica locale
      Alert.alert(
        remoteMessage.notification?.title || 'Nuova notifica',
        remoteMessage.notification?.body || '',
        [{ text: 'OK' }]
      );
    });

    // Gestisci click su notifiche quando l'app è in background
    const unsubscribeBackground = FirebaseService.onNotificationOpenedApp((remoteMessage) => {
      console.log('Notification opened app:', remoteMessage);
      handleNotificationNavigation(remoteMessage);
    });

    // Controlla se l'app è stata aperta da una notifica
    FirebaseService.getInitialNotification().then((remoteMessage) => {
      if (remoteMessage) {
        console.log('App opened from notification:', remoteMessage);
        handleNotificationNavigation(remoteMessage);
      }
    });

    // Gestisci cambio stato app
    const subscription = AppState.addEventListener('change', (nextAppState) => {
      if (
        appState.current.match(/inactive|background/) &&
        nextAppState === 'active'
      ) {
        // App è tornata in foreground, controlla se ci sono notifiche
        FirebaseService.getInitialNotification().then((remoteMessage) => {
          if (remoteMessage) {
            handleNotificationNavigation(remoteMessage);
          }
        });
      }
      appState.current = nextAppState;
    });

    return () => {
      unsubscribeForeground();
      unsubscribeBackground();
      subscription.remove();
    };
  }, []);

  // Funzione per gestire la navigazione basata sulla notifica
  const handleNotificationNavigation = (remoteMessage) => {
    const data = remoteMessage.data;
    
    // Esempio: naviga a una schermata specifica basata sui dati della notifica
    if (data?.type === 'workout_reminder') {
      // Naviga alla schermata del workout
      // navigation.navigate('Workout', { workoutId: data.workout_id });
    } else if (data?.type === 'new_workout') {
      // Naviga alla schermata del piano
      // navigation.navigate('Plan', { planId: data.plan_id });
    }
    // Aggiungi altri tipi di notifica secondo necessità
  };

  return (
    // Il tuo componente app
  );
}

export default App;
```

### 4.2 Configura il Background Handler (iOS)

Crea un file `index.js` nella root del progetto (se non esiste già):

```javascript
import { AppRegistry } from 'react-native';
import App from './App';
import { name as appName } from './app.json';

// Importa il background handler per le notifiche
import '@react-native-firebase/messaging';

AppRegistry.registerComponent(appName, () => App);
```

Crea un file `src/services/backgroundNotificationHandler.js`:

```javascript
import messaging from '@react-native-firebase/messaging';

// Handler per notifiche in background (iOS)
messaging().setBackgroundMessageHandler(async (remoteMessage) => {
  console.log('Message handled in the background!', remoteMessage);
  
  // Puoi fare operazioni qui, come aggiornare il database locale
  // o mostrare una notifica locale
});
```

Importa questo handler nel tuo `index.js`:

```javascript
import './src/services/backgroundNotificationHandler';
```

---

## 🔔 Passo 5: Gestione Notifiche e Navigazione

### 5.1 Crea un Servizio di Gestione Notifiche

Crea `src/services/notificationHandler.js`:

```javascript
import { Alert, Linking } from 'react-native';
import messaging from '@react-native-firebase/messaging';

class NotificationHandler {
  /**
   * Gestisci una notifica ricevuta
   * @param {Object} remoteMessage Messaggio FCM
   * @param {Function} navigation Funzione di navigazione (opzionale)
   */
  handleNotification(remoteMessage, navigation = null) {
    const { notification, data } = remoteMessage;

    console.log('Handling notification:', {
      title: notification?.title,
      body: notification?.body,
      data,
    });

    // Mostra alert se l'app è in foreground
    if (notification) {
      Alert.alert(
        notification.title || 'Notifica',
        notification.body || '',
        [
          {
            text: 'Annulla',
            style: 'cancel',
          },
          {
            text: 'Apri',
            onPress: () => this.navigateFromNotification(data, navigation),
          },
        ]
      );
    } else {
      // Se non c'è notification, naviga direttamente
      this.navigateFromNotification(data, navigation);
    }
  }

  /**
   * Naviga basandosi sui dati della notifica
   * @param {Object} data Dati della notifica
   * @param {Function} navigation Funzione di navigazione
   */
  navigateFromNotification(data, navigation) {
    if (!navigation || !data) return;

    const { type, ...params } = data;

    switch (type) {
      case 'workout_reminder':
        if (params.workout_id) {
          navigation.navigate('WorkoutDetail', { workoutId: params.workout_id });
        }
        break;

      case 'new_workout':
        if (params.plan_id) {
          navigation.navigate('PlanDetail', { planId: params.plan_id });
        }
        break;

      case 'workout_completed':
        navigation.navigate('Dashboard');
        break;

      case 'plan_updates':
        if (params.plan_id) {
          navigation.navigate('PlanDetail', { planId: params.plan_id });
        }
        break;

      default:
        console.log('Unknown notification type:', type);
        navigation.navigate('Home');
    }
  }

  /**
   * Formatta i dati della notifica per il display
   * @param {Object} remoteMessage Messaggio FCM
   * @returns {Object} Dati formattati
   */
  formatNotification(remoteMessage) {
    return {
      title: remoteMessage.notification?.title || 'Notifica',
      body: remoteMessage.notification?.body || '',
      data: remoteMessage.data || {},
      timestamp: remoteMessage.sentTime || Date.now(),
    };
  }
}

export default new NotificationHandler();
```

---

## 🧪 Passo 6: Testing

### 6.1 Test Locale con Firebase Console

1. Vai a Firebase Console → **Cloud Messaging**
2. Clicca su **"Send test message"**
3. Inserisci il FCM token del dispositivo (puoi ottenerlo dai log)
4. Compila titolo e messaggio
5. Clicca **"Test"**

### 6.2 Test con cURL

Puoi testare inviando una notifica direttamente dal backend:

```bash
curl -X POST "https://your-api.com/notifications/send" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "notification_type": "test",
    "title": "Test Notification",
    "body": "This is a test push notification",
    "data": {
      "type": "test",
      "test_id": "123"
    }
  }'
```

### 6.3 Verifica Log

Controlla i log dell'app per verificare:
- ✅ Token FCM ottenuto correttamente
- ✅ Token registrato sul backend
- ✅ Notifiche ricevute
- ✅ Navigazione funzionante

---

## 🔍 Troubleshooting

### Problema: "No token available"

**Soluzioni**:
1. Verifica che `GoogleService-Info.plist` sia presente nel progetto
2. Controlla che le capability Push Notifications siano abilitate
3. Assicurati che l'app abbia i permessi per le notifiche
4. Verifica che il progetto Firebase sia configurato correttamente

### Problema: "Permission denied"

**Soluzioni**:
1. Vai alle Impostazioni iOS → [Nome App] → Notifiche
2. Abilita le notifiche manualmente
3. Oppure reinstallare l'app e riprovare

### Problema: "Token registration failed"

**Soluzioni**:
1. Verifica che l'utente sia autenticato (token JWT valido)
2. Controlla che l'endpoint `/notifications/register-device` sia raggiungibile
3. Verifica il formato della richiesta (device_token, platform, device_id, app_version)

### Problema: "Notifiche non arrivano"

**Soluzioni**:
1. Verifica che il token sia registrato sul backend
2. Controlla che l'utente abbia le notifiche abilitate nelle preferenze
3. Verifica che il backend abbia FCM configurato correttamente
4. Controlla i log del backend per errori FCM

### Problema: "App crasha quando riceve notifica"

**Soluzioni**:
1. Verifica che tutti i listener siano configurati correttamente
2. Controlla che la navigazione sia disponibile quando viene chiamata
3. Aggiungi try-catch intorno alle funzioni di gestione notifiche

---

## 📚 Riferimenti API Backend

### Endpoint: POST /notifications/register-device

Registra o aggiorna un device token.

**Headers**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body**:
```json
{
  "device_token": "fcm-token-here",
  "platform": "ios",
  "device_id": "unique-device-id",
  "app_version": "1.0.0"
}
```

**Response**:
```json
{
  "id": 123,
  "device_token": "fcm-token-here",
  "platform": "ios",
  "device_id": "unique-device-id",
  "app_version": "1.0.0",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Endpoint: DELETE /notifications/register-device/{token_id}

Disattiva un device token (utile per logout).

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "message": "Device token disattivato"
}
```

---

## ✅ Checklist Implementazione

- [ ] Dipendenze installate (`@react-native-firebase/app`, `@react-native-firebase/messaging`)
- [ ] `GoogleService-Info.plist` aggiunto al progetto Xcode
- [ ] Capability "Push Notifications" abilitata
- [ ] Capability "Background Modes" → "Remote notifications" abilitata
- [ ] App ID configurato in Apple Developer con Push Notifications
- [ ] Certificati APNs o APNs Auth Key configurati in Firebase
- [ ] FirebaseService creato e configurato
- [ ] Hook `usePushNotifications` implementato
- [ ] Token registrato sul backend all'avvio dell'app
- [ ] Listener per notifiche foreground configurati
- [ ] Listener per notifiche background configurati
- [ ] Background handler configurato
- [ ] Navigazione da notifiche implementata
- [ ] Test di invio notifica eseguito con successo
- [ ] Gestione errori implementata
- [ ] Log di debug aggiunti

---

## 🔐 Best Practices

1. **Sicurezza**:
   - Non loggare mai il token FCM in produzione
   - Usa HTTPS per tutte le chiamate API
   - Valida sempre i dati delle notifiche prima di usarli

2. **Performance**:
   - Registra il token solo quando necessario (dopo login)
   - Rimuovi il token quando l'utente fa logout
   - Gestisci il refresh del token automaticamente

3. **UX**:
   - Richiedi permessi notifiche al momento giusto (non subito all'avvio)
   - Mostra un messaggio chiaro se i permessi sono negati
   - Gestisci gracefully le notifiche quando l'app è chiusa

4. **Debug**:
   - Usa console.log per tracciare il flusso delle notifiche
   - Testa sia in foreground che in background
   - Verifica che la navigazione funzioni correttamente

---

## 🆘 Supporto

Per problemi o domande:
1. Controlla i log dell'app e del backend
2. Verifica la configurazione Firebase Console
3. Consulta la documentazione ufficiale:
   - [React Native Firebase Messaging](https://rnfirebase.io/messaging/usage)
   - [Firebase Cloud Messaging iOS](https://firebase.google.com/docs/cloud-messaging/ios/client)

---

## 📝 Note Importanti

- ⚠️ Le notifiche push funzionano solo su dispositivi fisici, non sul simulatore iOS
- ⚠️ Assicurati di testare su un dispositivo reale
- ⚠️ Il token FCM può cambiare, gestisci sempre il refresh
- ⚠️ Le notifiche in background richiedono Background Modes abilitati

