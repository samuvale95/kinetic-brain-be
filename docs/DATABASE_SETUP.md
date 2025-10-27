# Kinetic Brain Database Setup

Questo documento spiega come configurare il database PostgreSQL per il backend Kinetic Brain.

## 📋 File Disponibili

### 1. `create_tables.sql`
Script SQL completo per creare tutte le tabelle necessarie al backend.

**Contenuto:**
- ✅ **8 tabelle principali**: users, user_profiles, performance_metrics, oauth_accounts, workout_plans, workouts, workout_sessions, calendar_events
- ✅ **Indici ottimizzati** per performance
- ✅ **Vincoli di validazione** per integrità dati
- ✅ **Trigger automatici** per timestamp `updated_at`
- ✅ **Permessi e grants** per l'utente database

### 2. `setup_database.sh`
Script bash automatizzato per eseguire la creazione delle tabelle.

**Funzionalità:**
- 🔍 **Verifica connessione** database
- 🏗️ **Creazione automatica** delle tabelle
- ✅ **Verifica completamento** con statistiche
- 📊 **Mostra informazioni** di connessione

## 🚀 Utilizzo

### Metodo 1: Script Automatico (Raccomandato)
```bash
# Esegui lo script di setup
./setup_database.sh
```

### Metodo 2: Esecuzione Manuale
```bash
# Esegui direttamente lo script SQL
psql "postgresql://user:password@host:port/database" -f database/create_tables.sql
```

## 📊 Struttura Database

### Tabelle Principali

#### 👤 **Users & Authentication**
- `users` - Utenti del sistema
- `user_profiles` - Profili dettagliati utenti
- `performance_metrics` - Metriche di performance
- `oauth_accounts` - Account OAuth (Google, etc.)

#### 🏃 **Workouts**
- `workout_plans` - Piani di allenamento
- `workouts` - Singoli allenamenti
- `workout_sessions` - Sessioni di allenamento completate

#### 📅 **Calendar**
- `calendar_events` - Eventi del calendario

### Relazioni Chiave
```
users (1) ←→ (1) user_profiles
users (1) ←→ (N) workout_plans
users (1) ←→ (N) workouts
users (1) ←→ (N) workout_sessions
users (1) ←→ (N) calendar_events
workout_plans (1) ←→ (N) workouts
workouts (1) ←→ (N) workout_sessions
```

## 🔧 Configurazione

### 1. File `.env`
Assicurati che il file `.env` contenga:
```env
DATABASE_URL="postgresql://user:password@host:port/database"
```

### 2. Permessi Database
L'utente database deve avere i permessi per:
- Creare tabelle
- Creare indici
- Creare trigger
- Inserire/modificare/eliminare dati

## 📈 Performance

### Indici Creati
- **Email lookup**: `idx_users_email`
- **Foreign keys**: Tutte le chiavi esterne hanno indici
- **Date queries**: Indici su date per query temporali
- **Status filtering**: Indici su campi di stato

### Vincoli di Validazione
- **Email format**: Validazione formato email
- **Gender values**: Solo 'male', 'female', 'other'
- **Age range**: 0-150 anni
- **Weight/Height**: Valori realistici
- **Workout zones**: Z1-Z5 validi
- **RPE scale**: 1-10 per sforzo percepito

## 🔄 Trigger Automatici

Tutti i campi `updated_at` vengono aggiornati automaticamente quando un record viene modificato.

## 🧪 Test

Dopo la creazione delle tabelle, puoi testare la connessione:

```bash
# Avvia il backend
./start.sh

# Verifica lo stato
curl http://localhost:8000/health
```

## 🆘 Troubleshooting

### Errore: "relation already exists"
```bash
# Le tabelle esistono già, puoi ignorare l'errore
# oppure eliminare e ricreare:
psql "your_database_url" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
./setup_database.sh
```

### Errore: "permission denied"
```bash
# Verifica i permessi dell'utente database
psql "your_database_url" -c "SELECT current_user, session_user;"
```

### Errore: "connection refused"
```bash
# Verifica la connessione e le credenziali nel .env
psql "your_database_url" -c "SELECT 1;"
```

## 📝 Note

- Lo script è **idempotente**: può essere eseguito più volte senza problemi
- Le tabelle esistenti **non vengono sovrascritte**
- I dati esistenti **non vengono eliminati**
- Gli indici vengono creati solo se non esistono già

## 🎯 Prossimi Passi

1. ✅ Esegui `./setup_database.sh`
2. ✅ Verifica con `./start.sh`
3. ✅ Testa l'API su `http://localhost:8000/docs`
4. 🚀 Inizia a sviluppare!
