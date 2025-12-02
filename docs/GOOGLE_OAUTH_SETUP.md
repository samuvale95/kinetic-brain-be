# Configurazione Google OAuth per Kinetic Brain

## Passo 1: Configurazione Google Cloud Console

### 1.1 Crea un Progetto
1. Vai a [Google Cloud Console](https://console.cloud.google.com/)
2. Clicca su "Seleziona un progetto" → "Nuovo progetto"
3. Inserisci il nome: "Kinetic Brain"
4. Clicca "Crea"

### 1.2 Abilita le API Necessarie
1. Nel menu laterale, vai a "API e servizi" → "Libreria"
2. Cerca e abilita:
   - **Google+ API** (per informazioni utente)
   - **OAuth2 API** (per autenticazione)

### 1.3 Crea Credenziali OAuth 2.0
1. Vai a "API e servizi" → "Credenziali"
2. Clicca "Crea credenziali" → "ID client OAuth 2.0"
3. Seleziona "Applicazione web" (per backend e React Native)
4. Configura:
   - **Nome**: Kinetic Brain
   - **URI di reindirizzamento autorizzati**:
     - `http://localhost:3000/auth/google/callback` (sviluppo web)
     - `https://yourdomain.com/auth/google/callback` (produzione web)
   - **Per React Native**: Non serve aggiungere redirect URI specifici, usa lo stesso Client ID

**Nota**: Per React Native, puoi usare lo stesso Client ID dell'applicazione web. Google Sign-In SDK gestisce l'autenticazione nativamente senza bisogno di redirect URI.

### 1.4 Ottieni le Credenziali
1. Dopo la creazione, copia:
   - **ID client**
   - **Segreto client**

## Passo 2: Configurazione Backend

### 2.1 Variabili d'Ambiente
Crea/aggiorna il file `.env`:

```env
# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback
```

### 2.2 Test della Configurazione
```bash
# Avvia il server
python run.py

# Testa l'endpoint
curl http://localhost:8000/auth/google/url
```

## Passo 3: Configurazione Frontend

### 3.1 React/Next.js
```javascript
// pages/api/auth/google/url.js
export default async function handler(req, res) {
  const response = await fetch(`${process.env.API_BASE_URL}/auth/google/url`);
  const data = await response.json();
  res.json(data);
}

// pages/auth/google/callback.js
import { useEffect } from 'react';
import { useRouter } from 'next/router';

export default function GoogleCallback() {
  const router = useRouter();
  const { code } = router.query;

  useEffect(() => {
    if (code) {
      handleGoogleCallback(code);
    }
  }, [code]);

  const handleGoogleCallback = async (code) => {
    try {
      const response = await fetch('/api/auth/google/callback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code,
          redirect_uri: `${window.location.origin}/auth/google/callback`
        })
      });

      if (response.ok) {
        const tokens = await response.json();
        // Salva i token
        localStorage.setItem('access_token', tokens.access_token);
        localStorage.setItem('refresh_token', tokens.refresh_token);
        
        // Reindirizza alla dashboard
        router.push('/dashboard');
      }
    } catch (error) {
      console.error('Google auth error:', error);
    }
  };

  return <div>Autenticazione in corso...</div>;
}
```

### 3.2 Vue.js
```javascript
// composables/useGoogleAuth.js
export const useGoogleAuth = () => {
  const loginWithGoogle = async () => {
    try {
      const response = await $fetch('/api/auth/google/url');
      window.location.href = response.auth_url;
    } catch (error) {
      console.error('Error getting Google auth URL:', error);
    }
  };

  const handleGoogleCallback = async (code) => {
    try {
      const response = await $fetch('/api/auth/google/callback', {
        method: 'POST',
        body: {
          code,
          redirect_uri: `${window.location.origin}/auth/google/callback`
        }
      });

      // Salva i token
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('refresh_token', response.refresh_token);

      return response;
    } catch (error) {
      console.error('Google auth callback error:', error);
      throw error;
    }
  };

  return {
    loginWithGoogle,
    handleGoogleCallback
  };
};
```

### 3.3 React Native (Consigliato per App Mobile)

Per le app React Native, usa Google Sign-In SDK nativo che fornisce un ID token invece del flusso OAuth web.

#### Installazione
```bash
npm install @react-native-google-signin/google-signin
# oppure
yarn add @react-native-google-signin/google-signin
```

#### Configurazione iOS
1. Aggiungi il `GoogleService-Info.plist` al progetto iOS
2. Configura l'URL scheme nel `Info.plist`

#### Configurazione Android
1. Aggiungi il `google-services.json` al progetto Android
2. Configura il SHA-1 fingerprint in Google Cloud Console

#### Implementazione
```javascript
// services/authService.js
import { GoogleSignin } from '@react-native-google-signin/google-signin';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Configura Google Sign-In
GoogleSignin.configure({
  webClientId: 'YOUR_GOOGLE_CLIENT_ID', // Dal Google Cloud Console
  offlineAccess: true,
});

export const signInWithGoogle = async () => {
  try {
    // Verifica se Google Play Services è disponibile
    await GoogleSignin.hasPlayServices();
    
    // Ottieni le informazioni utente
    const userInfo = await GoogleSignin.signIn();
    
    // Ottieni l'ID token
    const idToken = userInfo.data?.idToken;
    
    if (!idToken) {
      throw new Error('ID token non disponibile');
    }
    
    // Invia l'ID token al backend
    const response = await fetch('https://your-api.com/auth/google/verify-id-token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id_token: idToken,
      }),
    });
    
    if (!response.ok) {
      throw new Error('Autenticazione fallita');
    }
    
    const tokens = await response.json();
    
    // Salva i token in modo sicuro
    await AsyncStorage.setItem('access_token', tokens.access_token);
    await AsyncStorage.setItem('refresh_token', tokens.refresh_token);
    
    return tokens;
  } catch (error) {
    console.error('Google Sign-In Error:', error);
    throw error;
  }
};

export const signOut = async () => {
  try {
    await GoogleSignin.signOut();
    await AsyncStorage.removeItem('access_token');
    await AsyncStorage.removeItem('refresh_token');
  } catch (error) {
    console.error('Sign out error:', error);
  }
};

// Hook React
import { useState } from 'react';

export const useGoogleAuth = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const signIn = async () => {
    setLoading(true);
    setError(null);
    try {
      const tokens = await signInWithGoogle();
      return tokens;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };
  
  return { signIn, signOut, loading, error };
};
```

#### Uso nel Componente
```javascript
// components/LoginScreen.js
import React from 'react';
import { View, Button, Text } from 'react-native';
import { useGoogleAuth } from '../services/authService';

export const LoginScreen = () => {
  const { signIn, loading, error } = useGoogleAuth();
  
  const handleGoogleSignIn = async () => {
    try {
      await signIn();
      // Naviga alla schermata principale
      navigation.navigate('Home');
    } catch (err) {
      console.error('Login error:', err);
    }
  };
  
  return (
    <View>
      <Button
        title={loading ? 'Caricamento...' : 'Accedi con Google'}
        onPress={handleGoogleSignIn}
        disabled={loading}
      />
      {error && <Text style={{ color: 'red' }}>{error}</Text>}
    </View>
  );
};
```

#### Note Importanti per React Native
1. **Client ID**: Usa lo stesso `GOOGLE_CLIENT_ID` del backend (quello per applicazioni web)
2. **SHA-1 Fingerprint**: Per Android, aggiungi il fingerprint SHA-1 del tuo keystore in Google Cloud Console
3. **Bundle ID/Package Name**: Assicurati che corrispondano a quelli configurati in Google Cloud Console
4. **Sicurezza**: L'ID token viene verificato lato server, quindi è sicuro inviarlo al backend

## Passo 4: Test Completo

### 4.1 Test Manuale (Web)
1. Avvia il backend: `python run.py`
2. Vai a `http://localhost:8000/docs`
3. Testa l'endpoint `GET /auth/google/url`
4. Copia l'URL e aprilo nel browser
5. Autorizza l'applicazione
6. Copia il codice dalla URL di callback
7. Testa `POST /auth/google/callback` con il codice

### 4.2 Test ID Token (React Native)
1. Avvia il backend: `python run.py`
2. Vai a `http://localhost:8000/docs`
3. Testa l'endpoint `POST /auth/google/verify-id-token`
4. Inserisci un ID token valido ottenuto da Google Sign-In SDK
5. Verifica che vengano restituiti i JWT tokens

### 4.3 Test Automatico
```bash
python examples/google_auth_example.py
```

## Passo 5: Produzione

### 5.1 Configurazione Produzione
1. In Google Console, aggiungi il dominio di produzione:
   - `https://yourdomain.com/auth/google/callback`

2. Aggiorna le variabili d'ambiente:
   ```env
   GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback
   CORS_ORIGINS=["https://yourdomain.com"]
   ```

### 5.2 Sicurezza
- Usa HTTPS in produzione
- Configura CORS correttamente
- Monitora i log per tentativi di accesso sospetti
- Implementa rate limiting per gli endpoint OAuth

## Troubleshooting

### Errori Comuni

1. **"redirect_uri_mismatch"**
   - Verifica che l'URI di reindirizzamento corrisponda esattamente
   - Controlla che non ci siano spazi o caratteri extra

2. **"invalid_client"**
   - Verifica che GOOGLE_CLIENT_ID sia corretto
   - Controlla che il progetto Google sia attivo

3. **"access_denied"**
   - L'utente ha negato l'autorizzazione
   - Implementa gestione degli errori nel frontend

4. **"invalid_grant"**
   - Il codice di autorizzazione è scaduto o già utilizzato
   - I codici scadono dopo 10 minuti

5. **"Invalid or expired Google ID token"** (React Native)
   - L'ID token è scaduto o non valido
   - Verifica che il Client ID corrisponda a quello configurato nel backend
   - Assicurati che Google Sign-In SDK sia configurato correttamente

### Debug
```python
# Abilita log dettagliati
import logging
logging.basicConfig(level=logging.DEBUG)

# Nei log vedrai:
# - Richieste a Google OAuth
# - Scambio codice per token
# - Creazione/aggiornamento utenti
```

## Sicurezza

### Best Practices
1. **Non esporre mai il client secret nel frontend**
2. **Usa HTTPS in produzione**
3. **Implementa CSRF protection**
4. **Valida sempre i token ricevuti**
5. **Implementa rate limiting**
6. **Monitora i log per attività sospette**

### Token Management
- I token di accesso scadono dopo 30 minuti
- I refresh token scadono dopo 7 giorni
- Implementa refresh automatico dei token
- Salva i token in modo sicuro (httpOnly cookies in produzione)
