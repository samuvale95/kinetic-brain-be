# Integrazione Apple Sign In per Web App

## Panoramica

Questa guida spiega come integrare Apple Sign In nella tua web app. Apple Sign In supporta sia il flusso OAuth standard (per web) che Identity Token (per mobile, ma utilizzabile anche su web).

## Setup Iniziale

### 1. Configurazione Backend

Assicurati che il backend sia configurato correttamente seguendo [APPLE_SIGN_IN_SETUP.md](./APPLE_SIGN_IN_SETUP.md).

### 2. Endpoint Backend Disponibili

- `GET /auth/apple/url`: Ottiene l'URL di autorizzazione Apple
- `POST /auth/apple/callback`: Scambia authorization code per tokens
- `POST /auth/apple/verify-identity-token`: Verifica Identity Token (alternativa)

## Implementazione

### Metodo 1: OAuth Flow Standard (Consigliato per Web)

Questo è il metodo standard per applicazioni web. L'utente viene reindirizzato a Apple, completa il login, e viene reindirizzato di nuovo alla tua app.

#### React/Next.js

```javascript
// services/appleAuth.js
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const getAppleAuthUrl = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/apple/url`);
    const data = await response.json();
    return data.auth_url;
  } catch (error) {
    console.error('Error getting Apple auth URL:', error);
    throw error;
  }
};

export const handleAppleCallback = async (code) => {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/apple/callback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        code: code,
        redirect_uri: window.location.origin + '/auth/apple/callback'
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Authentication failed' }));
      throw new Error(errorData.detail || 'Apple authentication failed');
    }

    const tokens = await response.json();
    
    // Salva i token
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    
    return tokens;
  } catch (error) {
    console.error('Apple auth callback error:', error);
    throw error;
  }
};

// Componente Login
import { useState } from 'react';
import { getAppleAuthUrl, handleAppleCallback } from '../services/appleAuth';

export const AppleSignInButton = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSignIn = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Ottieni URL di autorizzazione
      const authUrl = await getAppleAuthUrl();
      
      // Reindirizza a Apple
      window.location.href = authUrl;
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div>
      <button 
        onClick={handleSignIn} 
        disabled={loading}
        className="apple-sign-in-button"
      >
        {loading ? 'Caricamento...' : 'Accedi con Apple'}
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  );
};

// Pagina Callback (pages/auth/apple/callback.js per Next.js)
import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { handleAppleCallback } from '../../services/appleAuth';

export default function AppleCallback() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState('processing');

  useEffect(() => {
    const code = searchParams.get('code');
    const error = searchParams.get('error');

    if (error) {
      setStatus('error');
      return;
    }

    if (code) {
      handleAppleCallback(code)
        .then(() => {
          setStatus('success');
          // Reindirizza alla home dopo 1 secondo
          setTimeout(() => {
            router.push('/');
          }, 1000);
        })
        .catch((err) => {
          console.error('Apple callback error:', err);
          setStatus('error');
        });
    }
  }, [searchParams, router]);

  return (
    <div className="callback-container">
      {status === 'processing' && <p>Autenticazione in corso...</p>}
      {status === 'success' && <p>Login riuscito! Reindirizzamento...</p>}
      {status === 'error' && <p>Errore durante l'autenticazione. Riprova.</p>}
    </div>
  );
}
```

#### Vue.js

```javascript
// composables/useAppleAuth.js
import { ref } from 'vue';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useAppleAuth = () => {
  const loading = ref(false);
  const error = ref(null);

  const getAppleAuthUrl = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/apple/url`);
      const data = await response.json();
      return data.auth_url;
    } catch (err) {
      console.error('Error getting Apple auth URL:', err);
      throw err;
    }
  };

  const handleAppleCallback = async (code) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/apple/callback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code: code,
          redirect_uri: window.location.origin + '/auth/apple/callback'
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Authentication failed' }));
        throw new Error(errorData.detail || 'Apple authentication failed');
      }

      const tokens = await response.json();
      
      // Salva i token
      localStorage.setItem('access_token', tokens.access_token);
      localStorage.setItem('refresh_token', tokens.refresh_token);
      
      return tokens;
    } catch (err) {
      console.error('Apple auth callback error:', err);
      throw err;
    }
  };

  const signInWithApple = async () => {
    loading.value = true;
    error.value = null;
    
    try {
      const authUrl = await getAppleAuthUrl();
      window.location.href = authUrl;
    } catch (err) {
      error.value = err.message;
      loading.value = false;
    }
  };

  return {
    signInWithApple,
    handleAppleCallback,
    loading,
    error
  };
};

// Componente
<template>
  <div>
    <button 
      @click="signInWithApple" 
      :disabled="loading"
      class="apple-sign-in-button"
    >
      {{ loading ? 'Caricamento...' : 'Accedi con Apple' }}
    </button>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup>
import { useAppleAuth } from '@/composables/useAppleAuth';

const { signInWithApple, loading, error } = useAppleAuth();
</script>
```

### Metodo 2: Identity Token (Alternativa)

Se preferisci usare Identity Token direttamente nel browser (simile a mobile), puoi usare la libreria `@invertase/react-native-apple-authentication` anche su web, oppure implementare un flusso custom.

**Nota**: Questo metodo è più complesso su web e generalmente non è raccomandato. Il metodo OAuth standard è preferibile.

## Gestione Token e Stato

### Salvataggio Token

```javascript
// services/tokenStorage.js
export const saveTokens = (accessToken, refreshToken) => {
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
};

export const getAccessToken = () => {
  return localStorage.getItem('access_token');
};

export const getRefreshToken = () => {
  return localStorage.getItem('refresh_token');
};

export const clearTokens = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
};
```

### Interceptor per Richieste API

```javascript
// services/apiClient.js
import { getAccessToken, getRefreshToken, clearTokens } from './tokenStorage';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiRequest = async (endpoint, options = {}) => {
  const accessToken = getAccessToken();
  
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
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        
        if (refreshResponse.ok) {
          const newTokens = await refreshResponse.json();
          saveTokens(newTokens.access_token, newTokens.refresh_token);
          
          // Riprova la richiesta originale
          headers['Authorization'] = `Bearer ${newTokens.access_token}`;
          return fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers,
          });
        } else {
          // Refresh fallito, logout
          clearTokens();
          window.location.href = '/login';
          throw new Error('Session expired');
        }
      } catch (err) {
        clearTokens();
        window.location.href = '/login';
        throw err;
      }
    }
  }
  
  return response;
};
```

## Gestione Errori

### Errori Comuni

1. **"Apple authentication failed"**
   - Verifica che il backend sia configurato correttamente
   - Controlla che il `redirect_uri` corrisponda a quello configurato in Apple Developer Console

2. **"Invalid or expired code"**
   - Il code di Apple scade rapidamente (~10 minuti)
   - Assicurati di scambiarlo immediatamente dopo il redirect

3. **CORS Errors**
   - Verifica che il backend abbia configurato i CORS correttamente
   - Controlla `CORS_ORIGINS` nel backend

### Gestione Errori nel Componente

```javascript
const handleSignIn = async () => {
  setLoading(true);
  setError(null);
  
  try {
    const authUrl = await getAppleAuthUrl();
    window.location.href = authUrl;
  } catch (err) {
    // Gestione errori specifici
    if (err.message.includes('network')) {
      setError('Errore di connessione. Verifica la tua connessione internet.');
    } else if (err.message.includes('CORS')) {
      setError('Errore di configurazione. Contatta il supporto.');
    } else {
      setError(err.message || 'Errore durante il login. Riprova.');
    }
    setLoading(false);
  }
};
```

## Best Practices

1. **Sicurezza Token**:
   - Non esporre mai i token nella console o nei log
   - Usa `httpOnly` cookies in produzione (se possibile)
   - Considera l'uso di session storage invece di local storage per token sensibili

2. **UX**:
   - Mostra uno stato di caricamento durante l'autenticazione
   - Gestisci gli errori in modo user-friendly
   - Fornisci feedback chiaro all'utente

3. **Error Handling**:
   - Gestisci tutti i possibili errori
   - Logga gli errori lato server (non lato client)
   - Fornisci messaggi di errore chiari all'utente

4. **Testing**:
   - Testa il flusso completo end-to-end
   - Testa la gestione degli errori
   - Verifica il refresh token automatico

## Styling Apple Sign In Button

Apple fornisce linee guida specifiche per il design del bottone. Ecco un esempio:

```css
.apple-sign-in-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: #000;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 12px 24px;
  font-size: 17px;
  font-weight: 400;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  cursor: pointer;
  transition: background-color 0.2s;
}

.apple-sign-in-button:hover {
  background-color: #333;
}

.apple-sign-in-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.apple-sign-in-button::before {
  content: '🍎';
  margin-right: 8px;
  font-size: 20px;
}
```

## Riferimenti

- [Apple Human Interface Guidelines - Sign In with Apple](https://developer.apple.com/design/human-interface-guidelines/sign-in-with-apple)
- [Backend API Documentation](./API_DOCUMENTATION.md)
- [Apple Sign In Setup Guide](./APPLE_SIGN_IN_SETUP.md)
