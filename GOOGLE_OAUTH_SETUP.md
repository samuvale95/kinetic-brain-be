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
3. Seleziona "Applicazione web"
4. Configura:
   - **Nome**: Kinetic Brain
   - **URI di reindirizzamento autorizzati**:
     - `http://localhost:3000/auth/google/callback` (sviluppo)
     - `https://yourdomain.com/auth/google/callback` (produzione)

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

## Passo 4: Test Completo

### 4.1 Test Manuale
1. Avvia il backend: `python run.py`
2. Vai a `http://localhost:8000/docs`
3. Testa l'endpoint `GET /auth/google/url`
4. Copia l'URL e aprilo nel browser
5. Autorizza l'applicazione
6. Copia il codice dalla URL di callback
7. Testa `POST /auth/google/callback` con il codice

### 4.2 Test Automatico
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
