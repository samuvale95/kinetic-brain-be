# Configurazione Railway per Kinetic Brain Backend

Questa guida spiega come configurare e deployare il backend su Railway.

## Prerequisiti

1. Account Railway (https://railway.app)
2. Database PostgreSQL (puoi usare Railway PostgreSQL o esterno)
3. Variabili d'ambiente configurate

## Setup su Railway

### 1. Connessione del Repository

1. Vai su Railway Dashboard
2. Clicca "New Project"
3. Seleziona "Deploy from GitHub repo"
4. Scegli il repository `kinetic-brain-be`

### 2. Configurazione Database

Railway creerà automaticamente un servizio PostgreSQL. Le variabili d'ambiente verranno impostate automaticamente:

- `DATABASE_URL` - URL di connessione PostgreSQL
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - Variabili separate

**IMPORTANTE**: Il backend usa `DATABASE_URL` e `DATABASE_URL_ASYNC`. Se Railway non imposta automaticamente `DATABASE_URL_ASYNC`, aggiungila manualmente:

```
DATABASE_URL_ASYNC=postgresql+asyncpg://[user]:[password]@[host]:[port]/[database]
```

Sostituisci `postgresql://` con `postgresql+asyncpg://` nella `DATABASE_URL`.

### 3. Variabili d'Ambiente Richieste

Configura queste variabili d'ambiente su Railway:

#### Obbligatorie

```bash
# Database (se non usi AWS Secrets Manager)
DATABASE_URL=postgresql://user:password@host:port/database
DATABASE_URL_ASYNC=postgresql+asyncpg://user:password@host:port/database

# Security
SECRET_KEY=your-secret-key-here  # Genera con: openssl rand -hex 32
```

#### Opzionali ma Consigliate

```bash
# CORS - Aggiungi gli URL del tuo frontend
CORS_ORIGINS=["https://your-frontend-domain.com","https://app.kineticbrain.com"]

# Google OAuth (se usi autenticazione Google)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://your-railway-domain.railway.app/auth/google/callback
FRONTEND_CALLBACK_URI=https://your-frontend-domain.com/auth/callback

# OpenAI (se usi generazione piani)
OPENAI_API_KEY=your-openai-api-key

# Application
DEBUG=false
LOG_LEVEL=INFO
DISABLE_OPENAPI=false  # Imposta true in produzione per sicurezza
```

### 4. Porta

Railway assegna automaticamente la porta tramite la variabile `PORT`. Il Dockerfile è già configurato per usarla.

**NON** impostare manualmente `PORT` - Railway lo fa automaticamente.

### 5. Health Check

Railway userà automaticamente l'endpoint `/health` per verificare lo stato dell'applicazione.

### 6. Build e Deploy

Railway rileverà automaticamente il `Dockerfile` e farà il build. Il processo:

1. Build dell'immagine Docker
2. Deploy del container
3. Health check su `/health`
4. App disponibile su `https://your-app.railway.app`

## Troubleshooting

### App non risponde

1. **Verifica i log**: Vai su Railway Dashboard > Deployments > Logs
2. **Verifica DATABASE_URL**: Assicurati che sia corretta
3. **Verifica PORT**: Non impostare manualmente, Railway lo gestisce
4. **Verifica health check**: Controlla che `/health` risponda

### Errori di connessione database

1. Verifica che il servizio PostgreSQL sia attivo
2. Verifica `DATABASE_URL` e `DATABASE_URL_ASYNC`
3. Controlla che il database sia accessibile dalla rete Railway

### Errori CORS

1. Aggiungi il dominio del frontend a `CORS_ORIGINS`
2. Formato: `["https://domain1.com","https://domain2.com"]`
3. Riavvia il servizio dopo aver cambiato CORS_ORIGINS

### Build fallisce

1. Verifica che `requirements.txt` sia presente
2. Controlla i log di build per errori di dipendenze
3. Verifica che Python 3.13 sia supportato (Railway lo supporta)

## Domini Personalizzati

1. Vai su Railway Dashboard > Settings > Domains
2. Aggiungi il tuo dominio personalizzato
3. Configura DNS come indicato da Railway
4. Aggiorna `CORS_ORIGINS` e `GOOGLE_REDIRECT_URI` con il nuovo dominio

## Monitoraggio

Railway fornisce:
- Logs in tempo reale
- Metriche CPU/Memory
- Health check automatico
- Deploy history

## Note Importanti

1. **Non committare `.env`**: Usa sempre variabili d'ambiente su Railway
2. **Secret Key**: Genera sempre una nuova `SECRET_KEY` per produzione
3. **Database**: Railway PostgreSQL è gratuito per tier base, ma con limiti
4. **Porta**: Non impostare mai `PORT` manualmente
5. **CORS**: Aggiungi sempre i domini del frontend a `CORS_ORIGINS`

## Supporto

Per problemi:
1. Controlla i log su Railway Dashboard
2. Verifica le variabili d'ambiente
3. Controlla che il database sia accessibile
4. Verifica che `/health` risponda correttamente

