# Esempi di Utilizzo API

Questo directory contiene esempi pratici per utilizzare le API di Kinetic Brain.

## Google OAuth Example

### Configurazione

1. **Configura Google OAuth Console:**
   - Vai a [Google Cloud Console](https://console.cloud.google.com/)
   - Crea un nuovo progetto o seleziona uno esistente
   - Abilita l'API Google+ e OAuth2
   - Crea credenziali OAuth 2.0
   - Aggiungi `http://localhost:3000/auth/google/callback` agli URI di reindirizzamento

2. **Configura le variabili d'ambiente:**
   ```bash
   # Nel file .env
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback
   ```

3. **Avvia il server:**
   ```bash
   python run.py
   ```

### Utilizzo

```bash
python examples/google_auth_example.py
```

### Flusso Completo

1. **Ottieni URL di autorizzazione:**
   ```python
   auth_url = await auth_example.get_google_auth_url()
   ```

2. **L'utente autorizza l'applicazione:**
   - Vai all'URL fornito
   - Accedi con il tuo account Google
   - Autorizza l'applicazione
   - Copia il codice dalla URL di callback

3. **Autentica l'utente:**
   ```python
   tokens = await auth_example.authenticate_with_google(code)
   ```

4. **Usa i token per accedere alle API protette:**
   ```python
   user_info = await auth_example.get_user_info(access_token)
   stats = await auth_example.test_protected_endpoint(access_token)
   ```

## Frontend Integration

### React/Next.js Example

```javascript
// 1. Ottieni URL di autorizzazione
const getGoogleAuthUrl = async () => {
  const response = await fetch('/api/auth/google/url');
  const data = await response.json();
  return data.auth_url;
};

// 2. Reindirizza l'utente a Google
const handleGoogleLogin = async () => {
  const authUrl = await getGoogleAuthUrl();
  window.location.href = authUrl;
};

// 3. Gestisci il callback
const handleGoogleCallback = async (code) => {
  const response = await fetch('/api/auth/google/callback', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      code: code,
      redirect_uri: window.location.origin + '/auth/google/callback'
    })
  });
  
  const tokens = await response.json();
  // Salva i token nel localStorage o in un cookie
  localStorage.setItem('access_token', tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
};

// 4. Usa i token per le API protette
const callProtectedAPI = async () => {
  const token = localStorage.getItem('access_token');
  const response = await fetch('/api/dashboard/stats', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
};
```

### Vue.js Example

```javascript
// composables/useAuth.js
export const useAuth = () => {
  const loginWithGoogle = async () => {
    const { data } = await $fetch('/api/auth/google/url');
    window.location.href = data.auth_url;
  };
  
  const handleGoogleCallback = async (code) => {
    const { data } = await $fetch('/api/auth/google/callback', {
      method: 'POST',
      body: {
        code,
        redirect_uri: window.location.origin + '/auth/google/callback'
      }
    });
    
    // Salva i token
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    
    return data;
  };
  
  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return {
      'Authorization': `Bearer ${token}`
    };
  };
  
  return {
    loginWithGoogle,
    handleGoogleCallback,
    getAuthHeaders
  };
};
```

## Testing

### Test con curl

```bash
# 1. Ottieni URL di autorizzazione
curl -X GET "http://localhost:8000/auth/google/url"

# 2. Dopo aver ottenuto il codice da Google, autentica
curl -X POST "http://localhost:8000/auth/google/login" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "4/0AX4XfWh...",
    "redirect_uri": "http://localhost:3000/auth/google/callback"
  }'

# 3. Usa il token per accedere alle API protette
curl -X GET "http://localhost:8000/dashboard/stats" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Test con Postman

1. **Crea una collezione Postman**
2. **Aggiungi le richieste:**
   - `GET /auth/google/url`
   - `POST /auth/google/login` (con body JSON)
   - `GET /auth/me` (con header Authorization)
   - `GET /dashboard/stats` (con header Authorization)

3. **Configura le variabili:**
   - `base_url`: `http://localhost:8000`
   - `access_token`: (impostato automaticamente)

## Troubleshooting

### Errori Comuni

1. **"Invalid redirect_uri"**
   - Verifica che l'URI di reindirizzamento sia configurato correttamente in Google Console
   - Assicurati che corrisponda esattamente a quello nel codice

2. **"Client ID not found"**
   - Verifica che `GOOGLE_CLIENT_ID` sia configurato correttamente
   - Controlla che il progetto Google sia attivo

3. **"Token expired"**
   - I token di accesso scadono dopo 30 minuti
   - Usa il refresh token per ottenere un nuovo access token

4. **"User not found"**
   - L'utente potrebbe non essere stato creato correttamente
   - Controlla i log del server per errori di database

### Debug

Abilita i log di debug:

```python
# In app/config.py
DEBUG = True

# Nei log vedrai:
# - Richieste HTTP a Google
# - Creazione/aggiornamento utenti
# - Gestione token OAuth
```
