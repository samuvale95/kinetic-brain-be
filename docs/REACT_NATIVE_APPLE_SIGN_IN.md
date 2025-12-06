# Guida Completa: Apple Sign In per React Native - Kinetic Brain

## ⚠️ Nota Importante: Identity Token

Per React Native, Apple Sign In usa **Identity Token** (simile a Google ID token):
- ✅ Non richiede redirect URI
- ✅ Funziona nativamente con Apple Authentication SDK
- ✅ È più sicuro
- ✅ È già implementato e funzionante nel backend

---

## 📋 Setup Completo

### 1. Installazione Dipendenze

```bash
# Installa Apple Authentication SDK
npm install @invertase/react-native-apple-authentication
# oppure
yarn add @invertase/react-native-apple-authentication

# Installa AsyncStorage per salvare i token
npm install @react-native-async-storage/async-storage
# oppure
yarn add @react-native-async-storage/async-storage
```

### 2. Configurazione Apple Developer Console

1. Vai a [Apple Developer Console](https://developer.apple.com/account/)
2. Seleziona **Certificates, Identifiers & Profiles**
3. Vai a **Identifiers** → seleziona il tuo **App ID** (o creane uno nuovo)
4. Spunta **Sign In with Apple** capability
5. Clicca **Save** → **Continue** → **Register**

**Nota**: Per React Native, devi configurare il tuo App ID (non il Service ID). Il Service ID è solo per web.

### 3. Configurazione iOS

#### 3.1 Installa Pods

```bash
cd ios
pod install
cd ..
```

#### 3.2 Abilita Sign In with Apple Capability

1. Apri il progetto in Xcode: `open ios/YourApp.xcworkspace`
2. Seleziona il target dell'app
3. Vai a **Signing & Capabilities**
4. Clicca **+ Capability**
5. Aggiungi **Sign In with Apple**

**Importante**: Assicurati che il Bundle ID corrisponda all'App ID configurato in Apple Developer Console.

#### 3.3 Configura Info.plist (opzionale)

Apri `ios/YourApp/Info.plist` e verifica che il Bundle ID sia corretto:

```xml
<key>CFBundleIdentifier</key>
<string>com.yourcompany.yourapp</string>
```

### 4. Configurazione Android

Apple Sign In è disponibile anche su Android! Segui questi passi:

#### 4.1 Configura build.gradle

Apri `android/app/build.gradle` e verifica che la versione minima di Android sia 5.0+:

```gradle
android {
    defaultConfig {
        minSdkVersion 21  // Android 5.0+
    }
}
```

#### 4.2 Aggiungi dipendenze (se necessario)

Il package `@invertase/react-native-apple-authentication` gestisce automaticamente le dipendenze Android.

### 5. Configurazione Backend

Assicurati che il backend sia configurato seguendo [APPLE_SIGN_IN_SETUP.md](./APPLE_SIGN_IN_SETUP.md).

**Importante**: Per React Native, usa lo stesso `APPLE_CLIENT_ID` (Service ID) del backend. Il backend verifica l'Identity Token usando questo Client ID.

---

## 💻 Implementazione Codice

### 1. Service di Autenticazione

Crea `src/services/appleAuthService.js`:

```javascript
import appleAuth from '@invertase/react-native-apple-authentication';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

// Funzione principale per login con Apple
export const signInWithApple = async (apiBaseUrl) => {
  try {
    // Verifica se Apple Sign In è disponibile (solo iOS 13+)
    if (Platform.OS === 'ios') {
      const isAvailable = await appleAuth.isSupported();
      if (!isAvailable) {
        throw new Error('Apple Sign In non disponibile su questo dispositivo');
      }
    }
    
    // Esegui il login con Apple
    const appleAuthRequestResponse = await appleAuth.performRequest({
      requestedOperation: appleAuth.Operation.LOGIN,
      requestedScopes: [appleAuth.Scope.EMAIL, appleAuth.Scope.FULL_NAME],
    });
    
    // Verifica se l'utente ha annullato
    if (!appleAuthRequestResponse.identityToken) {
      throw new Error('Login annullato dall\'utente');
    }
    
    // Ottieni l'Identity Token
    const { identityToken, user } = appleAuthRequestResponse;
    
    // Invia l'Identity Token al backend per verifica e ottenere JWT tokens
    const response = await fetch(`${apiBaseUrl}/auth/apple/verify-identity-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id_token: identityToken,
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
    
    // Salva anche le credenziali Apple (opzionale, per logout)
    if (user) {
      await AsyncStorage.setItem('apple_user_id', user);
    }
    
    return {
      tokens,
      appleUser: {
        user: user,
        email: appleAuthRequestResponse.email,
        fullName: appleAuthRequestResponse.fullName,
      },
    };
  } catch (error) {
    console.error('[Apple Auth] Error:', error);
    
    // Gestione errori specifici
    if (error.code === appleAuth.Error.CANCELED) {
      throw new Error('Login annullato dall\'utente');
    } else if (error.code === appleAuth.Error.NOT_HANDLED) {
      throw new Error('Apple Sign In non configurato correttamente');
    } else if (error.code === appleAuth.Error.UNKNOWN) {
      throw new Error('Errore sconosciuto durante il login');
    }
    
    throw error;
  }
};

// Logout
export const signOut = async () => {
  try {
    // Verifica se l'utente è loggato con Apple
    const appleUserId = await AsyncStorage.getItem('apple_user_id');
    
    if (appleUserId) {
      // Revoca le credenziali Apple (opzionale)
      try {
        await appleAuth.performRequest({
          requestedOperation: appleAuth.Operation.LOGOUT,
        });
      } catch (err) {
        // Ignora errori se l'utente non è più loggato
        console.log('[Apple Auth] Logout error (ignored):', err);
      }
    }
    
    // Rimuovi token e credenziali
    await AsyncStorage.removeItem('access_token');
    await AsyncStorage.removeItem('refresh_token');
    await AsyncStorage.removeItem('apple_user_id');
  } catch (error) {
    console.error('[Apple Auth] Sign out error:', error);
    throw error;
  }
};

// Verifica se l'utente è già loggato
export const isSignedIn = async () => {
  try {
    const accessToken = await AsyncStorage.getItem('access_token');
    return !!accessToken;
  } catch (error) {
    return false;
  }
};

// Ottieni le credenziali Apple correnti (se disponibili)
export const getCurrentAppleUser = async () => {
  try {
    const appleUserId = await AsyncStorage.getItem('apple_user_id');
    return appleUserId;
  } catch (error) {
    return null;
  }
};
```

### 2. Hook React per Autenticazione

Crea `src/hooks/useAppleAuth.js`:

```javascript
import { useState, useEffect } from 'react';
import { signInWithApple, signOut, isSignedIn, getCurrentAppleUser } from '../services/appleAuthService';

// Configurazione API base URL (usa la tua variabile d'ambiente)
const API_BASE_URL = process.env.API_BASE_URL || 'https://your-api.com';

export const useAppleAuth = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Verifica stato autenticazione all'avvio
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const signedIn = await isSignedIn();
      if (signedIn) {
        const appleUserId = await getCurrentAppleUser();
        setUser({ appleUserId });
        setIsAuthenticated(true);
      }
    } catch (err) {
      console.error('[useAppleAuth] Error checking auth status:', err);
    }
  };

  const signIn = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await signInWithApple(API_BASE_URL);
      setUser(result.appleUser);
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
import { View, Button, Text, StyleSheet, ActivityIndicator, Alert, Platform } from 'react-native';
import { useAppleAuth } from '../hooks/useAppleAuth';
import appleAuth from '@invertase/react-native-apple-authentication';

export const LoginScreen = ({ navigation }) => {
  const { signIn, loading, error } = useAppleAuth();
  const [isAppleAvailable, setIsAppleAvailable] = React.useState(false);

  // Verifica disponibilità Apple Sign In
  React.useEffect(() => {
    const checkAvailability = async () => {
      if (Platform.OS === 'ios') {
        const available = await appleAuth.isSupported();
        setIsAppleAvailable(available);
      } else {
        // Android supporta Apple Sign In dalla versione 1.1.0+
        setIsAppleAvailable(true);
      }
    };
    checkAvailability();
  }, []);

  const handleAppleSignIn = async () => {
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
      
      {isAppleAvailable && (
        <Button
          title={loading ? 'Caricamento...' : 'Accedi con Apple'}
          onPress={handleAppleSignIn}
          disabled={loading}
        />
      )}
      
      {!isAppleAvailable && Platform.OS === 'ios' && (
        <Text style={styles.warning}>
          Apple Sign In richiede iOS 13 o superiore
        </Text>
      )}
      
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
  warning: {
    color: 'orange',
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
    const refreshToken = await AsyncStorage.getItem('refresh_token');
    if (refreshToken) {
      try {
        const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        
        if (refreshResponse.ok) {
          const newTokens = await refreshResponse.json();
          await AsyncStorage.setItem('access_token', newTokens.access_token);
          await AsyncStorage.setItem('refresh_token', newTokens.refresh_token);
          
          // Riprova la richiesta originale
          headers['Authorization'] = `Bearer ${newTokens.access_token}`;
          return fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers,
          });
        } else {
          // Refresh fallito, logout
          await AsyncStorage.removeItem('access_token');
          await AsyncStorage.removeItem('refresh_token');
          throw new Error('Session expired. Please login again.');
        }
      } catch (err) {
        await AsyncStorage.removeItem('access_token');
        await AsyncStorage.removeItem('refresh_token');
        throw err;
      }
    }
  }
  
  return response;
};
```

---

## 🔍 Troubleshooting

### Errore: "Apple Sign In non disponibile su questo dispositivo"

**Causa**: iOS versione < 13 o dispositivo non supportato.

**Soluzione**:
- Verifica che il dispositivo sia iOS 13+
- Su Android, assicurati di usare la versione più recente della libreria

### Errore: "Apple Sign In non configurato correttamente"

**Causa**: Capability non abilitata in Xcode o Bundle ID non corrisponde.

**Soluzione**:
1. Verifica che "Sign In with Apple" sia abilitata in Xcode → Signing & Capabilities
2. Verifica che il Bundle ID corrisponda all'App ID configurato in Apple Developer Console
3. Riavvia Xcode e ricompila l'app

### Errore: "Invalid or expired Apple Identity Token" (Backend)

**Causa**: Identity Token scaduto o Client ID non corrisponde.

**Soluzione**:
1. Verifica che `APPLE_CLIENT_ID` nel backend corrisponda al Service ID configurato
2. Assicurati che l'Identity Token venga inviato immediatamente dopo il login (non salvarlo)
3. Verifica che il backend abbia le chiavi pubbliche Apple configurate correttamente

### Errore: "Login annullato dall'utente"

**Causa**: L'utente ha annullato il login.

**Soluzione**: Gestisci questo caso mostrando un messaggio appropriato all'utente. Non è un errore critico.

### Errore: Build iOS fallisce

**Causa**: Pods non installati o capability non configurata.

**Soluzione**:
```bash
cd ios
pod install
cd ..
# Poi ricompila in Xcode
```

---

## ✅ Checklist Implementazione

- [ ] Installato `@invertase/react-native-apple-authentication`
- [ ] Installato `@react-native-async-storage/async-storage`
- [ ] Configurato App ID in Apple Developer Console con Sign In with Apple
- [ ] Abilitata "Sign In with Apple" capability in Xcode
- [ ] Verificato che Bundle ID corrisponda all'App ID
- [ ] Configurato `APPLE_CLIENT_ID` nel backend (Service ID)
- [ ] Implementato `signInWithApple()` che chiama `/auth/apple/verify-identity-token`
- [ ] Gestito salvataggio token in AsyncStorage
- [ ] Implementato logout che pulisce token e disconnette Apple
- [ ] Aggiunto interceptor per token nelle richieste API
- [ ] Testato login su dispositivo reale iOS (non solo simulatore)
- [ ] Testato su Android (se supportato)

---

## 📝 Note Importanti

1. **Identity Token**: L'Identity Token viene verificato lato server, quindi è sicuro inviarlo al backend.

2. **Token Storage**: Usa AsyncStorage per sviluppo, considera soluzioni più sicure per produzione (es. Keychain/Keystore).

3. **Name Disclosure**: Il nome utente è disponibile **solo al primo login**. Successivi login non includeranno il nome.

4. **Email Privata**: Apple può fornire email relay. Il backend gestisce questo caso automaticamente.

5. **Testing**: Testa sempre su dispositivo reale, non solo simulatore/emulatore.

6. **iOS 13+**: Apple Sign In richiede iOS 13 o superiore su iOS. Su Android è disponibile dalla versione 1.1.0+ della libreria.

---

## 🚀 Flusso Completo

1. Utente clicca "Accedi con Apple"
2. Apple Authentication SDK mostra schermata Apple nativa
3. Utente autorizza l'app
4. SDK restituisce Identity Token
5. App invia Identity Token a `POST /auth/apple/verify-identity-token`
6. Backend verifica Identity Token e crea/aggiorna utente
7. Backend restituisce JWT tokens (access_token, refresh_token)
8. App salva token in AsyncStorage
9. App usa token per tutte le richieste API successive

---

## 📚 Riferimenti

- [React Native Apple Authentication](https://github.com/invertase/react-native-apple-authentication)
- [Backend API: POST /auth/apple/verify-identity-token](./API_DOCUMENTATION.md#apple-oauth)
- [Apple Developer Console](https://developer.apple.com/account/)
- [Apple Sign In Documentation](https://developer.apple.com/sign-in-with-apple/)
