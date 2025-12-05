# Guida Completa: Google OAuth per React Native - Kinetic Brain

## ⚠️ Problema Importante: Redirect URI Custom

**NON usare redirect URI con custom scheme** (es. `kineticbrain://oauth/callback`) per Google OAuth!

Google OAuth **rifiuta** redirect URI con custom scheme perché:
- Non sono domini pubblici validi (`.com`, `.org`, ecc.)
- Google richiede domini verificati per sicurezza
- Errore: "Invalid redirect: Must end with a public top-level domain"

### ✅ Soluzione: Usa ID Token (Metodo Consigliato)

Per React Native, usa **sempre** il metodo `verify-id-token` che:
- ✅ Non richiede redirect URI
- ✅ Funziona nativamente con Google Sign-In SDK
- ✅ È più sicuro
- ✅ È già implementato e funzionante nel backend

---

## 📋 Setup Completo

### 1. Installazione Dipendenze

```bash
# Installa Google Sign-In SDK
npm install @react-native-google-signin/google-signin
# oppure
yarn add @react-native-google-signin/google-signin

# Installa AsyncStorage per salvare i token
npm install @react-native-async-storage/async-storage
# oppure
yarn add @react-native-async-storage/async-storage
```

### 2. Configurazione Google Cloud Console

1. Vai a [Google Cloud Console](https://console.cloud.google.com/)
2. Seleziona il tuo progetto
3. Vai a **"APIs & Services"** → **"Credentials"**
4. Crea o usa un **OAuth 2.0 Client ID** di tipo **"Web application"**
5. **IMPORTANTE**: Usa lo stesso Client ID del backend (quello configurato in `GOOGLE_CLIENT_ID`)
6. **NON aggiungere** redirect URI custom - non servono per questo metodo!

### 3. Configurazione iOS

#### 3.1 Installa Pods
```bash
cd ios
pod install
cd ..
```

#### 3.2 Aggiungi GoogleService-Info.plist
1. Scarica `GoogleService-Info.plist` da Firebase Console
2. Aggiungilo al progetto iOS (drag & drop in Xcode)
3. Assicurati che sia incluso nel target

#### 3.3 Configura Info.plist (opzionale, solo se usi URL schemes)
Apri `ios/YourApp/Info.plist` e aggiungi:
```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>com.googleusercontent.apps.YOUR_CLIENT_ID</string>
    </array>
  </dict>
</array>
```

### 4. Configurazione Android

#### 4.1 Aggiungi google-services.json
1. Scarica `google-services.json` da Firebase Console
2. Aggiungilo in `android/app/google-services.json`

#### 4.2 Configura build.gradle
Apri `android/build.gradle` e aggiungi:
```gradle
buildscript {
    dependencies {
        classpath 'com.google.gms:google-services:4.4.0'
    }
}
```

Apri `android/app/build.gradle` e aggiungi in fondo:
```gradle
apply plugin: 'com.google.gms.google-services'
```

#### 4.3 SHA-1 Fingerprint (IMPORTANTE)
Ottieni il SHA-1 fingerprint:
```bash
# Debug keystore
cd android
./gradlew signingReport
```

Copia il SHA-1 fingerprint e aggiungilo in Google Cloud Console:
1. Vai a **"APIs & Services"** → **"Credentials"**
2. Apri il tuo OAuth 2.0 Client ID
3. Aggiungi il SHA-1 fingerprint nella sezione **"Android"**

---

## 💻 Implementazione Codice

### 1. Service di Autenticazione

Crea `src/services/authService.js`:

```javascript
import { GoogleSignin } from '@react-native-google-signin/google-signin';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

// Configura Google Sign-In (chiama una sola volta all'avvio dell'app)
export const configureGoogleSignIn = () => {
  GoogleSignin.configure({
    webClientId: 'YOUR_GOOGLE_CLIENT_ID', // Sostituisci con il tuo Client ID
    offlineAccess: true, // Richiede refresh token
    forceCodeForRefreshToken: true, // Forza refresh token
  });
};

// Funzione principale per login con Google
export const signInWithGoogle = async (apiBaseUrl) => {
  try {
    // Verifica se Google Play Services è disponibile (solo Android)
    if (Platform.OS === 'android') {
      await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
    }
    
    // Esegui il login con Google
    const userInfo = await GoogleSignin.signIn();
    
    // Ottieni l'ID token
    const idToken = userInfo.data?.idToken;
    
    if (!idToken) {
      throw new Error('ID token non disponibile. Assicurati di aver configurato webClientId correttamente.');
    }
    
    // Invia l'ID token al backend per verifica e ottenere JWT tokens
    const response = await fetch(`${apiBaseUrl}/auth/google/verify-id-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id_token: idToken,
      }),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Errore sconosciuto' }));
      throw new Error(errorData.detail || 'Autenticazione fallita');
    }
    
    const tokens = await response.json();
    
    // Salva i token in modo sicuro
    await AsyncStorage.setItem('access_token', tokens.access_token);
    await AsyncStorage.setItem('refresh_token', tokens.refresh_token);
    
    return {
      tokens,
      user: userInfo.data?.user, // Info utente da Google
    };
  } catch (error) {
    console.error('[Google Auth] Error:', error);
    
    // Gestione errori specifici
    if (error.code === 'SIGN_IN_CANCELLED') {
      throw new Error('Login annullato dall\'utente');
    } else if (error.code === 'IN_PROGRESS') {
      throw new Error('Login già in corso');
    } else if (error.code === 'PLAY_SERVICES_NOT_AVAILABLE') {
      throw new Error('Google Play Services non disponibile');
    }
    
    throw error;
  }
};

// Logout
export const signOut = async () => {
  try {
    await GoogleSignin.signOut();
    await AsyncStorage.removeItem('access_token');
    await AsyncStorage.removeItem('refresh_token');
  } catch (error) {
    console.error('[Google Auth] Sign out error:', error);
    throw error;
  }
};

// Verifica se l'utente è già loggato
export const isSignedIn = async () => {
  try {
    const isSignedIn = await GoogleSignin.isSignedIn();
    const accessToken = await AsyncStorage.getItem('access_token');
    return isSignedIn && !!accessToken;
  } catch (error) {
    return false;
  }
};

// Ottieni l'utente corrente (se loggato)
export const getCurrentUser = async () => {
  try {
    const user = await GoogleSignin.getCurrentUser();
    return user;
  } catch (error) {
    return null;
  }
};
```

### 2. Hook React per Autenticazione

Crea `src/hooks/useGoogleAuth.js`:

```javascript
import { useState, useEffect } from 'react';
import { signInWithGoogle, signOut, isSignedIn, getCurrentUser } from '../services/authService';
import { configureGoogleSignIn } from '../services/authService';

// Configurazione API base URL (usa la tua variabile d'ambiente)
const API_BASE_URL = process.env.API_BASE_URL || 'https://your-api.com';

export const useGoogleAuth = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Configura Google Sign-In all'avvio
  useEffect(() => {
    configureGoogleSignIn();
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const signedIn = await isSignedIn();
      if (signedIn) {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
        setIsAuthenticated(true);
      }
    } catch (err) {
      console.error('[useGoogleAuth] Error checking auth status:', err);
    }
  };

  const signIn = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await signInWithGoogle(API_BASE_URL);
      setUser(result.user);
      setIsAuthenticated(true);
      return result;
    } catch (err) {
      const errorMessage = err.message || 'Errore durante il login';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = async () => {
    setLoading(true);
    try {
      await signOut();
      setUser(null);
      setIsAuthenticated(false);
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return {
    signIn,
    signOut: handleSignOut,
    loading,
    error,
    user,
    isAuthenticated,
  };
};
```

### 3. Componente Login Screen

Crea `src/screens/LoginScreen.js`:

```javascript
import React from 'react';
import { View, Button, Text, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import { useGoogleAuth } from '../hooks/useGoogleAuth';

export const LoginScreen = ({ navigation }) => {
  const { signIn, loading, error } = useGoogleAuth();

  const handleGoogleSignIn = async () => {
    try {
      await signIn();
      // Naviga alla schermata principale dopo login riuscito
      navigation.replace('Home');
    } catch (err) {
      // Mostra alert con errore
      Alert.alert(
        'Errore Login',
        err.message || 'Si è verificato un errore durante il login',
        [{ text: 'OK' }]
      );
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Kinetic Brain</Text>
      
      {error && (
        <Text style={styles.error}>{error}</Text>
      )}
      
      <Button
        title={loading ? 'Caricamento...' : 'Accedi con Google'}
        onPress={handleGoogleSignIn}
        disabled={loading}
      />
      
      {loading && <ActivityIndicator style={styles.loader} />}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 40,
  },
  error: {
    color: 'red',
    marginBottom: 20,
    textAlign: 'center',
  },
  loader: {
    marginTop: 20,
  },
});
```

### 4. Interceptor per Token nelle Richieste API

Crea `src/services/apiClient.js`:

```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE_URL = process.env.API_BASE_URL || 'https://your-api.com';

// Interceptor per aggiungere token a tutte le richieste
export const apiRequest = async (endpoint, options = {}) => {
  const accessToken = await AsyncStorage.getItem('access_token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });
  
  // Se token scaduto, prova refresh
  if (response.status === 401 && accessToken) {
    // Implementa refresh token logic qui
    // Per ora, reindirizza al login
    throw new Error('Token scaduto. Effettua nuovamente il login.');
  }
  
  return response;
};
```

---

## 🔍 Troubleshooting

### Errore: "ID token non disponibile"
**Causa**: `webClientId` non configurato correttamente o non corrisponde al backend.

**Soluzione**:
1. Verifica che `webClientId` sia lo stesso `GOOGLE_CLIENT_ID` del backend
2. Assicurati che sia il Client ID per "Web application" (non Android/iOS)
3. Riavvia l'app dopo aver cambiato la configurazione

### Errore: "PLAY_SERVICES_NOT_AVAILABLE" (Android)
**Causa**: Google Play Services non installato o non aggiornato.

**Soluzione**:
- L'SDK mostra automaticamente un dialog per aggiornare Google Play Services
- Oppure installa/aggiorna Google Play Services manualmente

### Errore: "SIGN_IN_CANCELLED"
**Causa**: L'utente ha annullato il login.

**Soluzione**: Gestisci questo caso mostrando un messaggio appropriato all'utente.

### Errore: "Invalid or expired Google ID token" (Backend)
**Causa**: ID token scaduto o Client ID non corrisponde.

**Soluzione**:
1. Verifica che il `webClientId` nell'app corrisponda a `GOOGLE_CLIENT_ID` nel backend
2. Assicurati che l'ID token venga inviato immediatamente dopo il login (non salvarlo)

---

## ✅ Checklist Implementazione

- [ ] Installato `@react-native-google-signin/google-signin`
- [ ] Installato `@react-native-async-storage/async-storage`
- [ ] Configurato `GoogleService-Info.plist` (iOS)
- [ ] Configurato `google-services.json` (Android)
- [ ] Aggiunto SHA-1 fingerprint in Google Cloud Console (Android)
- [ ] Configurato `webClientId` con lo stesso Client ID del backend
- [ ] Implementato `signInWithGoogle()` che chiama `/auth/google/verify-id-token`
- [ ] Gestito salvataggio token in AsyncStorage
- [ ] Implementato logout che pulisce token e disconnette Google
- [ ] Aggiunto interceptor per token nelle richieste API
- [ ] Testato login su dispositivo reale (non solo emulatore)

---

## 📝 Note Importanti

1. **NON usare redirect URI custom**: Google non li accetta. Usa sempre `verify-id-token`.

2. **Client ID**: Deve essere lo stesso del backend (quello per "Web application").

3. **Testing**: Testa sempre su dispositivo reale, non solo emulatore.

4. **Sicurezza**: L'ID token viene verificato lato server, quindi è sicuro inviarlo al backend.

5. **Token Storage**: Usa AsyncStorage per sviluppo, considera soluzioni più sicure per produzione (es. Keychain/Keystore).

---

## 🚀 Flusso Completo

1. Utente clicca "Accedi con Google"
2. Google Sign-In SDK mostra schermata Google nativa
3. Utente autorizza l'app
4. SDK restituisce ID token
5. App invia ID token a `POST /auth/google/verify-id-token`
6. Backend verifica ID token e crea/aggiorna utente
7. Backend restituisce JWT tokens (access_token, refresh_token)
8. App salva token in AsyncStorage
9. App usa token per tutte le richieste API successive

---

## 📚 Riferimenti

- [Google Sign-In SDK Documentation](https://github.com/react-native-google-signin/google-signin)
- [Backend API: POST /auth/google/verify-id-token](./API_DOCUMENTATION.md#google-oauth)
- [Google Cloud Console](https://console.cloud.google.com/)
