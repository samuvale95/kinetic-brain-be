# Guida Completa Integrazione Apple Sign In

Questa guida fornisce una panoramica completa per integrare Apple Sign In sia per web app che per app React Native.

## 📋 Indice

1. [Panoramica](#panoramica)
2. [Checklist Pre-Implementazione](#checklist-pre-implementazione)
3. [Step-by-Step Backend](#step-by-step-backend)
4. [Step-by-Step Frontend Web](#step-by-step-frontend-web)
5. [Step-by-Step Frontend Mobile](#step-by-step-frontend-mobile)
6. [Testing End-to-End](#testing-end-to-end)
7. [Deployment Checklist](#deployment-checklist)
8. [Troubleshooting Integrato](#troubleshooting-integrato)
9. [FAQ](#faq)

---

## Panoramica

Apple Sign In supporta due flussi principali:

1. **Web App**: OAuth 2.0 flow standard con authorization code
2. **Mobile App (React Native)**: Identity Token verification (simile a Google ID token)

Entrambi i flussi sono supportati dal backend e utilizzano lo stesso Service ID configurato in Apple Developer Console.

### Architettura

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  Web App    │────────▶│   Backend    │────────▶│   Apple     │
│  (Browser)  │         │   (FastAPI)  │         │   Servers   │
└─────────────┘         └──────────────┘         └─────────────┘
                              ▲
┌─────────────┐                │
│ Mobile App │────────────────┘
│ (React     │
│  Native)   │
└─────────────┘
```

---

## Checklist Pre-Implementazione

Prima di iniziare, assicurati di avere:

### Requisiti Account
- [ ] Account Apple Developer attivo (pagamento annuale richiesto)
- [ ] Accesso a [Apple Developer Console](https://developer.apple.com/account/)
- [ ] App ID configurato per la tua app

### Requisiti Tecnici
- [ ] Backend FastAPI configurato e funzionante
- [ ] Database PostgreSQL configurato
- [ ] Accesso SSH/terminale al server backend
- [ ] Node.js e npm/yarn installati (per React Native)
- [ ] Xcode installato (per iOS, se sviluppi mobile)

### Informazioni Necessarie
- [ ] Team ID Apple (formato: `ABC123DEF4`)
- [ ] Bundle ID dell'app (es: `com.kineticbrain.app`)
- [ ] Domini web per redirect URIs (sviluppo e produzione)

---

## Step-by-Step Backend

### 1. Configurazione Apple Developer Console

Segui la guida dettagliata in [APPLE_SIGN_IN_SETUP.md](./APPLE_SIGN_IN_SETUP.md):

1. Crea un **Service ID** per web authentication
2. Configura **Sign In with Apple** capability
3. Aggiungi **Return URLs** (redirect URIs)
4. Crea una **Key** per JWT client secret
5. Scarica la chiave privata (`.p8`) - **non potrai più scaricarla!**
6. Copia **Team ID**, **Key ID**, e **Service ID**

### 2. Configurazione Backend

#### 2.1 Installa Dipendenze

```bash
cd /path/to/kinetic-brain-be
pip install -r requirements.txt
```

Le dipendenze necessarie (`PyJWT[crypto]` e `cryptography`) sono già incluse.

#### 2.2 Configura Variabili d'Ambiente

Crea/aggiorna il file `.env`:

```env
# Apple OAuth
APPLE_CLIENT_ID=com.kineticbrain.web  # Il Service ID creato
APPLE_TEAM_ID=ABC123DEF4  # Il tuo Team ID
APPLE_KEY_ID=XYZ789ABC1  # Il Key ID della chiave creata
APPLE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nMIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQg...\n-----END PRIVATE KEY-----
APPLE_REDIRECT_URI=http://localhost:8080/auth/apple/callback
```

**Nota**: Per produzione, usa variabili d'ambiente del server o un sistema di gestione segreti (AWS Secrets Manager, etc.).

#### 2.3 Verifica Configurazione

```bash
# Avvia il server
python run.py

# In un altro terminale, testa l'endpoint
curl http://localhost:8000/auth/apple/url

# Dovresti ricevere:
# {"auth_url": "https://appleid.apple.com/auth/authorize?..."}
```

### 3. Test Backend

```bash
# Test completo (manuale)
# 1. Ottieni URL
curl http://localhost:8000/auth/apple/url

# 2. Apri l'URL nel browser e completa il login

# 3. Verifica che l'utente sia stato creato
# (controlla il database o i log del server)
```

---

## Step-by-Step Frontend Web

### 1. Leggi la Documentazione

Segui la guida dettagliata in [FRONTEND_APPLE_SIGN_IN_WEB.md](./FRONTEND_APPLE_SIGN_IN_WEB.md).

### 2. Implementazione Base

#### 2.1 Crea Service di Autenticazione

```javascript
// services/appleAuth.js
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const getAppleAuthUrl = async () => {
  const response = await fetch(`${API_BASE_URL}/auth/apple/url`);
  const data = await response.json();
  return data.auth_url;
};

export const handleAppleCallback = async (code) => {
  const response = await fetch(`${API_BASE_URL}/auth/apple/callback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      code: code,
      redirect_uri: window.location.origin + '/auth/apple/callback'
    }),
  });
  
  if (!response.ok) {
    throw new Error('Apple authentication failed');
  }
  
  const tokens = await response.json();
  localStorage.setItem('access_token', tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
  return tokens;
};
```

#### 2.2 Crea Componente Login

```javascript
// components/AppleSignInButton.js
import { useState } from 'react';
import { getAppleAuthUrl } from '../services/appleAuth';

export const AppleSignInButton = () => {
  const [loading, setLoading] = useState(false);

  const handleSignIn = async () => {
    setLoading(true);
    try {
      const authUrl = await getAppleAuthUrl();
      window.location.href = authUrl;
    } catch (err) {
      console.error('Error:', err);
      setLoading(false);
    }
  };

  return (
    <button onClick={handleSignIn} disabled={loading}>
      {loading ? 'Caricamento...' : 'Accedi con Apple'}
    </button>
  );
};
```

#### 2.3 Crea Pagina Callback

```javascript
// pages/auth/apple/callback.js (Next.js)
import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { handleAppleCallback } from '../../services/appleAuth';

export default function AppleCallback() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const code = searchParams.get('code');
    if (code) {
      handleAppleCallback(code)
        .then(() => router.push('/'))
        .catch((err) => console.error('Error:', err));
    }
  }, [searchParams, router]);

  return <div>Autenticazione in corso...</div>;
}
```

### 3. Test Frontend Web

1. Avvia l'app web
2. Clicca "Accedi con Apple"
3. Completa il login con Apple
4. Verifica che vieni reindirizzato alla home e che i token siano salvati

---

## Step-by-Step Frontend Mobile

### 1. Leggi la Documentazione

Segui la guida dettagliata in [REACT_NATIVE_APPLE_SIGN_IN.md](./REACT_NATIVE_APPLE_SIGN_IN.md).

### 2. Configurazione Apple Developer

1. Vai a **Identifiers** → seleziona il tuo **App ID**
2. Spunta **Sign In with Apple** capability
3. Salva

### 3. Configurazione iOS

#### 3.1 Installa Dipendenze

```bash
npm install @invertase/react-native-apple-authentication
npm install @react-native-async-storage/async-storage

cd ios
pod install
cd ..
```

#### 3.2 Configura Xcode

1. Apri `ios/YourApp.xcworkspace` in Xcode
2. Seleziona il target → **Signing & Capabilities**
3. Clicca **+ Capability** → aggiungi **Sign In with Apple**
4. Verifica che il Bundle ID corrisponda all'App ID configurato

### 4. Implementazione Codice

#### 4.1 Crea Service

```javascript
// src/services/appleAuthService.js
import appleAuth from '@invertase/react-native-apple-authentication';
import AsyncStorage from '@react-native-async-storage/async-storage';

export const signInWithApple = async (apiBaseUrl) => {
  const response = await appleAuth.performRequest({
    requestedOperation: appleAuth.Operation.LOGIN,
    requestedScopes: [appleAuth.Scope.EMAIL, appleAuth.Scope.FULL_NAME],
  });
  
  if (!response.identityToken) {
    throw new Error('Login annullato');
  }
  
  const backendResponse = await fetch(`${apiBaseUrl}/auth/apple/verify-identity-token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id_token: response.identityToken }),
  });
  
  if (!backendResponse.ok) {
    throw new Error('Autenticazione fallita');
  }
  
  const tokens = await backendResponse.json();
  await AsyncStorage.setItem('access_token', tokens.access_token);
  await AsyncStorage.setItem('refresh_token', tokens.refresh_token);
  
  return tokens;
};
```

#### 4.2 Crea Componente

```javascript
// src/components/AppleSignInButton.js
import { Button } from 'react-native';
import { signInWithApple } from '../services/appleAuthService';

export const AppleSignInButton = () => {
  const handlePress = async () => {
    try {
      await signInWithApple('https://your-api.com');
      // Naviga alla home
    } catch (err) {
      console.error('Error:', err);
    }
  };
  
  return <Button title="Accedi con Apple" onPress={handlePress} />;
};
```

### 5. Test Frontend Mobile

1. Compila l'app su dispositivo reale (non simulatore)
2. Clicca "Accedi con Apple"
3. Completa il login
4. Verifica che i token siano salvati e che l'app funzioni

---

## Testing End-to-End

### Test Scenario 1: Web App - Nuovo Utente

1. Apri web app in browser
2. Clicca "Accedi con Apple"
3. Completa login (prima volta)
4. Verifica:
   - [ ] Utente creato nel database
   - [ ] Token salvati in localStorage
   - [ ] Redirect alla home funziona
   - [ ] Richieste API funzionano con token

### Test Scenario 2: Web App - Utente Esistente

1. Login con stesso account Apple
2. Verifica:
   - [ ] Utente esistente viene riconosciuto
   - [ ] Token aggiornati
   - [ ] Nessun duplicato nel database

### Test Scenario 3: Mobile App - Nuovo Utente

1. Apri app mobile
2. Clicca "Accedi con Apple"
3. Completa login
4. Verifica:
   - [ ] Utente creato nel database
   - [ ] Token salvati in AsyncStorage
   - [ ] App naviga alla home
   - [ ] Richieste API funzionano

### Test Scenario 4: Cross-Platform

1. Login su web app
2. Login su mobile app con stesso account Apple
3. Verifica:
   - [ ] Stesso utente nel database (stesso email o OAuth account)
   - [ ] Entrambe le app funzionano indipendentemente

---

## Deployment Checklist

### Backend

- [ ] Variabili d'ambiente configurate su server di produzione
- [ ] `APPLE_REDIRECT_URI` punta a URL di produzione
- [ ] Chiave privata salvata in modo sicuro (non in repository)
- [ ] CORS configurato per domini di produzione
- [ ] Test endpoint `/auth/apple/url` funziona
- [ ] Log verificati per errori

### Frontend Web

- [ ] `API_BASE_URL` punta a backend di produzione
- [ ] Redirect URI corrisponde a quello configurato in Apple Developer Console
- [ ] Test completo del flusso OAuth
- [ ] Gestione errori implementata
- [ ] Token storage sicuro (considera httpOnly cookies in produzione)

### Frontend Mobile

- [ ] App ID configurato in Apple Developer Console
- [ ] Capability abilitata in Xcode
- [ ] Bundle ID corrisponde
- [ ] `API_BASE_URL` punta a backend di produzione
- [ ] Test su dispositivo reale iOS
- [ ] Test su Android (se supportato)
- [ ] App compilata e testata in produzione

### Apple Developer Console

- [ ] Service ID configurato con Return URLs di produzione
- [ ] App ID configurato con Sign In with Apple capability
- [ ] Key creata e scaricata (backup della chiave privata)

---

## Troubleshooting Integrato

### Problema: "Missing required configuration"

**Backend**: Verifica tutte le variabili d'ambiente Apple in `.env`
**Sintomo**: Errore nel log: "Missing required configuration for client secret generation"

**Soluzione**: 
```bash
# Verifica .env
cat .env | grep APPLE
```

### Problema: "Invalid token" su mobile

**Mobile**: Identity Token non valido
**Backend**: Client ID non corrisponde

**Soluzione**:
1. Verifica che `APPLE_CLIENT_ID` nel backend corrisponda al Service ID
2. Verifica che l'Identity Token venga inviato immediatamente (non salvato)

### Problema: CORS errors su web

**Web**: Richieste bloccate dal browser

**Soluzione**:
1. Verifica `CORS_ORIGINS` nel backend include il dominio web
2. Verifica che le richieste usino il dominio corretto

### Problema: "Apple Sign In non disponibile"

**Mobile iOS**: Versione iOS < 13

**Soluzione**: 
- Verifica versione iOS: `Platform.Version >= 13`
- Mostra messaggio all'utente se non supportato

### Problema: Redirect non funziona su web

**Web**: Callback non raggiunto

**Soluzione**:
1. Verifica che Return URL in Apple Developer Console corrisponda esattamente
2. Verifica che `APPLE_REDIRECT_URI` nel backend corrisponda
3. Controlla i log del server per errori

---

## FAQ

### Q: Posso usare lo stesso Service ID per web e mobile?

**A**: Sì! Il Service ID è usato per verificare l'Identity Token. Sia web che mobile possono usare lo stesso Service ID.

### Q: Devo creare un App ID separato per mobile?

**A**: Sì, per mobile devi configurare l'App ID (non il Service ID) con Sign In with Apple capability. Il Service ID è solo per web.

### Q: Come gestisco email privata di Apple?

**A**: Il backend gestisce automaticamente email relay (`privaterelay.appleid.com`). Crea un email placeholder se necessario.

### Q: Il nome utente è sempre disponibile?

**A**: No, il nome è disponibile **solo al primo login**. Successivi login non includeranno il nome nel token.

### Q: Posso usare Apple Sign In su Android?

**A**: Sì! La libreria `@invertase/react-native-apple-authentication` supporta Android dalla versione 1.1.0+.

### Q: Come gestisco il logout?

**A**: Per web, rimuovi i token da localStorage. Per mobile, puoi chiamare `appleAuth.performRequest({ requestedOperation: appleAuth.Operation.LOGOUT })` prima di rimuovere i token.

### Q: Devo rigenerare il client secret JWT?

**A**: No, il backend genera automaticamente un nuovo JWT client secret ad ogni richiesta. Il JWT scade dopo 1 ora.

### Q: Come testo in sviluppo?

**A**: 
- Backend: Usa `http://localhost:8000`
- Web: Usa `http://localhost:8080` (o la tua porta)
- Mobile: Usa URL del backend locale o tunnel (ngrok, etc.)

---

## Riferimenti

- [Backend Setup Guide](./APPLE_SIGN_IN_SETUP.md)
- [Web Integration Guide](./FRONTEND_APPLE_SIGN_IN_WEB.md)
- [Mobile Integration Guide](./REACT_NATIVE_APPLE_SIGN_IN.md)
- [Apple Developer Documentation](https://developer.apple.com/sign-in-with-apple/)
- [API Documentation](./API_DOCUMENTATION.md)

---

## Supporto

Se incontri problemi:

1. Controlla i log del backend per errori specifici
2. Verifica la configurazione in Apple Developer Console
3. Consulta le guide specifiche per web o mobile
4. Verifica che tutte le variabili d'ambiente siano configurate correttamente
