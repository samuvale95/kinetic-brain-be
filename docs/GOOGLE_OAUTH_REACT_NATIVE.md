# Google OAuth per React Native con Custom URL Scheme

Questa guida spiega come configurare Google OAuth per React Native usando un custom URL scheme (es. `kineticbrain://oauth/callback`).

## Soluzione: Endpoint Web Intermedio

**Non puoi registrare custom URL schemes in Google Cloud Console** perché Google accetta solo URL HTTP/HTTPS validi.

La soluzione è usare un **endpoint web intermedio** che:
1. Riceve il callback da Google (URL web valido, registrato in Google Console)
2. Autentica l'utente
3. Reindirizza al tuo custom URL scheme con i token

### Passo 1: Registra l'Endpoint Web in Google Cloud Console

1. Vai a [Google Cloud Console](https://console.cloud.google.com/)
2. Seleziona il tuo progetto
3. Vai a **API e servizi** → **Credenziali**
4. Trova il tuo **OAuth 2.0 Client ID** (quello che usi per l'app web)
5. Clicca per modificarlo
6. Nella sezione **URI di reindirizzamento autorizzati**, aggiungi:
   ```
   http://localhost:8000/auth/google/mobile-callback  (sviluppo)
   https://yourdomain.com/auth/google/mobile-callback  (produzione)
   ```
   (Questo è l'endpoint intermedio che gestisce i callback mobile)
7. Clicca **Salva**

### Passo 2: Verifica l'App (se necessario)

Se Google continua a rifiutare le richieste:

1. Vai a **OAuth consent screen** in Google Cloud Console
2. Assicurati che l'app sia configurata correttamente:
   - **User Type**: Seleziona "External" (per app in sviluppo) o "Internal" (per Google Workspace)
   - **App name**: Nome della tua app
   - **Support email**: La tua email
   - **Developer contact information**: La tua email
3. Aggiungi gli **Scopes** necessari:
   - `openid`
   - `email`
   - `profile`
4. Aggiungi **Test users** (se l'app è in testing mode):
   - Vai a **Test users**
   - Aggiungi gli indirizzi email degli utenti che possono testare l'app
5. Se necessario, **Pubblica l'app**:
   - Clicca su **Publish App**
   - Nota: Questo richiede la verifica di Google se hai più di 100 utenti

### Passo 3: Usa l'API nel Frontend React Native

#### 1. Ottieni l'URL di autorizzazione con mobile_redirect_uri

```javascript
// Ottieni l'URL di autorizzazione
const getGoogleAuthUrl = async () => {
  const mobileRedirectUri = 'kineticbrain://oauth/callback'; // Il tuo custom URL scheme
  const response = await fetch(
    `${API_BASE_URL}/auth/google/url?mobile_redirect_uri=${encodeURIComponent(mobileRedirectUri)}`
  );
  const data = await response.json();
  return data.auth_url;
};
```

#### 2. Apri l'URL nel browser/WebView

```javascript
import { Linking } from 'react-native';

const handleGoogleLogin = async () => {
  const authUrl = await getGoogleAuthUrl();
  
  // Apri l'URL nel browser
  await Linking.openURL(authUrl);
  
  // Il browser reindirizzerà a kineticbrain://oauth/callback?code=...
  // La tua app React Native intercetterà questo URL
};
```

#### 3. Configura il Deep Linking nella tua app

**Android** (`android/app/src/main/AndroidManifest.xml`):
```xml
<activity
  android:name=".MainActivity"
  android:launchMode="singleTask">
  <intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="kineticbrain" />
  </intent-filter>
</activity>
```

**iOS** (`ios/YourApp/Info.plist`):
```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>kineticbrain</string>
    </array>
  </dict>
</array>
```

#### 4. Intercetta il callback - I token sono già nella URL!

```javascript
import { useEffect } from 'react';
import { Linking } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

useEffect(() => {
  // Gestisci il deep link quando l'app è già aperta
  const handleDeepLink = (event) => {
    const url = event.url || event;
    const parsedUrl = new URL(url);
    
    // Controlla se c'è un errore
    const error = parsedUrl.searchParams.get('error');
    if (error) {
      console.error('Google auth error:', error);
      // Mostra un messaggio di errore all'utente
      return;
    }
    
    // I token sono già nella URL (il backend li ha aggiunti)
    const accessToken = parsedUrl.searchParams.get('access_token');
    const refreshToken = parsedUrl.searchParams.get('refresh_token');
    const success = parsedUrl.searchParams.get('success');
    
    if (success === 'true' && accessToken && refreshToken) {
      // Salva i token
      AsyncStorage.setItem('access_token', accessToken);
      AsyncStorage.setItem('refresh_token', refreshToken);
      
      // Naviga alla schermata principale
      // navigation.navigate('Home');
    }
  };

  // Listener per quando l'app è già aperta
  Linking.addEventListener('url', handleDeepLink);

  // Controlla se l'app è stata aperta da un deep link
  Linking.getInitialURL().then((url) => {
    if (url) {
      handleDeepLink(url);
    }
  });

  return () => {
    Linking.removeEventListener('url', handleDeepLink);
  };
}, []);
```

**Nota**: Non devi più chiamare il backend! Il backend ha già autenticato l'utente e ha aggiunto i token alla URL del deep link.

## Flusso Completo

1. **Utente clicca "Login with Google"**
   - App chiama `/auth/google/url?mobile_redirect_uri=kineticbrain://oauth/callback`
   - Backend genera URL con endpoint web intermedio (`/auth/google/mobile-callback`)
   - Backend codifica `mobile_redirect_uri` nello `state` parameter

2. **Utente autorizza l'app**
   - Browser/WebView apre l'URL di Google
   - Utente fa login e autorizza l'app
   - Google reindirizza all'endpoint web: `/auth/google/mobile-callback?code=ABC123&state=...`

3. **Backend gestisce il callback**
   - Backend riceve il callback dall'endpoint web
   - Backend decodifica lo `state` per ottenere `mobile_redirect_uri`
   - Backend scambia il code con Google usando l'endpoint web come redirect_uri
   - Backend autentica l'utente e genera i JWT tokens

4. **Backend reindirizza all'app mobile**
   - Backend reindirizza a `kineticbrain://oauth/callback?access_token=...&refresh_token=...&success=true`

5. **App intercetta il deep link**
   - React Native intercetta il custom URL scheme
   - Estrae i token dalla URL (già autenticati!)
   - App salva i token e naviga alla schermata principale

## Troubleshooting

### Errore: "App doesn't comply with Google's OAuth 2.0 policy"

**Soluzioni:**
1. Verifica che l'endpoint web `/auth/google/mobile-callback` sia registrato in Google Cloud Console
2. Verifica che l'URL sia completo (es. `https://yourdomain.com/auth/google/mobile-callback`, non solo `/auth/google/mobile-callback`)
3. Se l'app è in testing mode, aggiungi l'email dell'utente come "Test user"
4. Verifica che gli scopes richiesti siano corretti

### Errore: "redirect_uri_mismatch"

**Soluzioni:**
1. Verifica che l'endpoint `/auth/google/mobile-callback` sia registrato in Google Cloud Console
2. Assicurati che l'URL sia esattamente quello che Google reindirizza (controlla i log del backend)
3. Controlla che non ci siano spazi o caratteri speciali non codificati nell'URL

### Il deep link non contiene i token

**Soluzioni:**
1. Verifica che il `mobile_redirect_uri` passato a `/auth/google/url` sia corretto
2. Controlla i log del backend per vedere se l'autenticazione è andata a buon fine
3. Verifica che il deep link sia configurato correttamente in AndroidManifest.xml e Info.plist

### Il deep link non funziona

**Soluzioni:**
1. Verifica la configurazione del deep linking in AndroidManifest.xml e Info.plist
2. Testa il deep link con: `adb shell am start -W -a android.intent.action.VIEW -d "kineticbrain://oauth/callback?code=test" com.yourapp`
3. Assicurati che l'app sia configurata per gestire il custom URL scheme

## Note Importanti

- **Non devi registrare il custom URL scheme in Google Cloud Console** - usa solo l'endpoint web `/auth/google/mobile-callback`
- Il `mobile_redirect_uri` passato a `/auth/google/url` è quello che riceverà i token (il tuo deep link)
- L'endpoint web `/auth/google/mobile-callback` deve essere registrato in Google Cloud Console
- Per app in testing, gli utenti devono essere aggiunti come "Test users"
- Per produzione, considera di pubblicare l'app in Google Cloud Console
- I token vengono passati direttamente nel deep link, non serve chiamare il backend dopo il callback
