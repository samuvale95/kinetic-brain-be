# Configurazione Apple Sign In per Kinetic Brain (Backend)

## Panoramica

Apple Sign In richiede una configurazione più complessa rispetto a Google OAuth perché:
- Richiede un **JWT client secret** generato dinamicamente (non un secret statico)
- Necessita di chiavi private per firmare il JWT
- Richiede configurazione in Apple Developer Console

## Passo 1: Configurazione Apple Developer Console

### 1.1 Prerequisiti

1. Account Apple Developer attivo (pagamento annuale richiesto)
2. Accesso a [Apple Developer Console](https://developer.apple.com/account/)
3. Un App ID configurato

### 1.2 Crea un Service ID

1. Vai a [Apple Developer Console](https://developer.apple.com/account/)
2. Seleziona **Certificates, Identifiers & Profiles**
3. Vai a **Identifiers** → clicca **+** per creare un nuovo identifier
4. Seleziona **Services IDs** → **Continue**
5. Compila:
   - **Description**: Kinetic Brain Web Auth
   - **Identifier**: `com.kineticbrain.web` (deve essere unico, usa il tuo dominio)
6. Clicca **Continue** → **Register**

### 1.3 Configura il Service ID

1. Seleziona il Service ID appena creato
2. Spunta **Sign In with Apple**
3. Clicca **Configure**
4. Configura:
   - **Primary App ID**: Seleziona il tuo App ID principale
   - **Website URLs**:
     - **Domains and Subdomains**: `yourdomain.com` (senza http/https)
     - **Return URLs**: 
       - `http://localhost:8080/auth/apple/callback` (sviluppo)
       - `https://yourdomain.com/auth/apple/callback` (produzione)
5. Clicca **Save** → **Continue** → **Register**

### 1.4 Crea una Key per JWT Client Secret

1. Vai a **Keys** → clicca **+** per creare una nuova key
2. Compila:
   - **Key Name**: Kinetic Brain Auth Key
   - Spunta **Sign In with Apple**
3. Clicca **Configure** → seleziona il tuo **Primary App ID** → **Save**
4. Clicca **Continue** → **Register**
5. **IMPORTANTE**: Scarica la chiave (file `.p8`) - **non potrai più scaricarla!**
6. Copia il **Key ID** mostrato

### 1.5 Ottieni il Team ID

1. Vai a **Membership** (in alto a destra)
2. Copia il **Team ID** (formato: `ABC123DEF4`)

## Passo 2: Configurazione Backend

### 2.1 Prepara la Chiave Privata

La chiave scaricata (`.p8`) è in formato PEM. Puoi usarla direttamente o convertirla:

```bash
# Se hai il file .p8, è già in formato PEM
cat AuthKey_ABC123DEF4.p8

# Output esempio:
# -----BEGIN PRIVATE KEY-----
# MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQg...
# -----END PRIVATE KEY-----
```

### 2.2 Variabili d'Ambiente

Crea/aggiorna il file `.env`:

```env
# Apple OAuth
APPLE_CLIENT_ID=com.kineticbrain.web  # Il Service ID creato
APPLE_TEAM_ID=ABC123DEF4  # Il tuo Team ID
APPLE_KEY_ID=XYZ789ABC1  # Il Key ID della chiave creata
APPLE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nMIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQg...\n-----END PRIVATE KEY-----
APPLE_REDIRECT_URI=http://localhost:8080/auth/apple/callback
```

**Nota importante**: 
- `APPLE_PRIVATE_KEY` deve contenere `\n` per le newline (non newline reali)
- Oppure puoi usare newline reali se il tuo sistema le gestisce correttamente
- La chiave deve essere completa, inclusi i delimitatori `-----BEGIN PRIVATE KEY-----` e `-----END PRIVATE KEY-----`

### 2.3 Formato Alternativo per Private Key

Se preferisci, puoi salvare la chiave in un file separato e leggerla nel codice:

```python
# In app/config.py (modifica se necessario)
with open("apple_private_key.p8", "r") as f:
    apple_private_key = f.read()
```

Ma il metodo con variabile d'ambiente è più sicuro per deployment.

### 2.4 Installazione Dipendenze

Le dipendenze necessarie sono già in `requirements.txt`:
- `PyJWT[crypto]==2.8.0`
- `cryptography==42.0.0`

Installa con:
```bash
pip install -r requirements.txt
```

## Passo 3: Test della Configurazione

### 3.1 Avvia il Server

```bash
python run.py
```

### 3.2 Test Endpoint

```bash
# Ottieni URL di autorizzazione
curl http://localhost:8000/auth/apple/url

# Dovresti ricevere:
# {
#   "auth_url": "https://appleid.apple.com/auth/authorize?client_id=..."
# }
```

### 3.3 Test Completo (Manuale)

1. Apri l'URL restituito da `/auth/apple/url` nel browser
2. Completa il login con Apple
3. Apple reindirizzerà a `/auth/apple/callback` con un `code`
4. Il backend scambierà il code per un Identity Token
5. Verifica che l'utente sia creato nel database

## Passo 4: Verifica Database

Dopo un login di test, verifica che:

1. Un nuovo utente sia stato creato in `users`:
   ```sql
   SELECT id, email, name, auth_provider FROM users WHERE auth_provider = 'apple';
   ```

2. Un account OAuth sia stato creato in `oauth_accounts`:
   ```sql
   SELECT * FROM oauth_accounts WHERE provider = 'apple';
   ```

## Troubleshooting

### Errore: "Missing required configuration for client secret generation"

**Causa**: Una o più variabili d'ambiente Apple non sono configurate.

**Soluzione**: Verifica che tutte le variabili siano presenti in `.env`:
- `APPLE_CLIENT_ID`
- `APPLE_TEAM_ID`
- `APPLE_KEY_ID`
- `APPLE_PRIVATE_KEY`

### Errore: "Error generating client secret"

**Causa**: La chiave privata non è nel formato corretto o è corrotta.

**Soluzione**:
1. Verifica che la chiave includa `-----BEGIN PRIVATE KEY-----` e `-----END PRIVATE KEY-----`
2. Assicurati che le newline siano `\n` (non newline reali) o che il formato sia corretto
3. Prova a ricaricare la chiave dal file `.p8` originale

### Errore: "Invalid token" durante verifica Identity Token

**Causa**: 
- Il token è scaduto
- Il `client_id` non corrisponde
- Problema con le chiavi pubbliche Apple

**Soluzione**:
1. Verifica che `APPLE_CLIENT_ID` corrisponda al Service ID configurato
2. Assicurati che il token non sia scaduto (sono validi per ~10 minuti)
3. Controlla i log per errori specifici

### Errore: "No matching public key found"

**Causa**: Il `kid` (Key ID) nel token non corrisponde a nessuna chiave pubblica di Apple.

**Soluzione**: Questo è raro, ma può succedere se Apple ha rotato le chiavi. Il codice gestisce automaticamente il refresh delle chiavi pubbliche.

## Note Importanti

1. **JWT Client Secret**: Il backend genera dinamicamente un JWT come client secret. Questo JWT scade dopo 1 ora e viene rigenerato ad ogni richiesta.

2. **Email Privata**: Apple può fornire email relay (`privaterelay.appleid.com`). Il sistema gestisce questo caso creando un email placeholder se necessario.

3. **Name Disclosure**: Il nome utente è disponibile **solo al primo login**. Successivi login non includeranno il nome nel token.

4. **Token Expiration**: Gli Identity Token di Apple scadono dopo ~10 minuti. Assicurati di inviarli al backend immediatamente.

5. **Sicurezza**: La chiave privata è sensibile. Non committarla nel repository. Usa variabili d'ambiente o sistemi di gestione segreti (AWS Secrets Manager, etc.).

## Riferimenti

- [Apple Sign In Documentation](https://developer.apple.com/sign-in-with-apple/)
- [Apple OAuth 2.0 Specification](https://developer.apple.com/documentation/sign_in_with_apple/sign_in_with_apple_rest_api)
- [JWT Client Secret Generation](https://developer.apple.com/documentation/sign_in_with_apple/generate_and_validate_tokens)
