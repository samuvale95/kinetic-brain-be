# Guida alla Configurazione delle Credenziali AWS

Questa guida spiega come ottenere e configurare le credenziali AWS per utilizzare AWS Secrets Manager.

## Come Ottenere le Credenziali AWS

### 1. Dalla Console AWS

1. Accedi alla [Console AWS](https://console.aws.amazon.com/)
2. Vai su **IAM** (Identity and Access Management)
3. Nel menu a sinistra, clicca su **Users** (Utenti)
4. Seleziona il tuo utente o creane uno nuovo
5. Vai alla tab **Security credentials** (Credenziali di sicurezza)
6. Scorri fino a **Access keys** (Chiavi di accesso)
7. Clicca su **Create access key** (Crea chiave di accesso)
8. Scegli il caso d'uso (es. "Application running outside AWS")
9. Scarica o copia:
   - **Access Key ID** (ID chiave di accesso)
   - **Secret Access Key** (Chiave di accesso segreta)

⚠️ **IMPORTANTE**: La Secret Access Key viene mostrata solo una volta. Salvala in un posto sicuro!

### 2. Permessi Richiesti

L'utente AWS deve avere i seguenti permessi per accedere a Secrets Manager:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            "Resource": "arn:aws:secretsmanager:eu-north-1:*:secret:rds!*"
        }
    ]
}
```

## Dove Mettere le Credenziali

Hai **due opzioni** per configurare le credenziali AWS:

### Opzione 1: Variabili d'Ambiente (Consigliata per Sviluppo Locale)

Aggiungi le credenziali al tuo file `.env`:

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=eu-north-1
AWS_SECRET_NAME=rds!db-f609f1db-d7a1-4220-afbc-3679b06248bd
```

**Vantaggi:**
- Facile da configurare
- Funziona bene per sviluppo locale
- Non richiede configurazione aggiuntiva

**Svantaggi:**
- Le credenziali sono nel file `.env` (assicurati che sia nel `.gitignore`)

### Opzione 2: File AWS Credentials (Alternativa)

Crea o modifica il file `~/.aws/credentials`:

```bash
# Su macOS/Linux
mkdir -p ~/.aws
nano ~/.aws/credentials
```

Aggiungi:

```ini
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
region = eu-north-1
```

**Vantaggi:**
- Standard AWS
- Le credenziali non sono nel progetto
- Funziona con tutti i tool AWS CLI

**Svantaggi:**
- Richiede configurazione manuale del file

## Verifica della Configurazione

Dopo aver configurato le credenziali, puoi verificare che funzionino:

```bash
# Se hai installato AWS CLI
aws secretsmanager get-secret-value --secret-id rds!db-f609f1db-d7a1-4220-afbc-3679b06248bd --region eu-north-1
```

Oppure avvia l'applicazione e controlla i log. Se le credenziali sono corrette, vedrai che le credenziali del database vengono recuperate da AWS Secrets Manager.

## Ordine di Ricerca delle Credenziali

boto3 cerca le credenziali in questo ordine:

1. **Variabili d'ambiente**: `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY`
2. **File credentials**: `~/.aws/credentials`
3. **IAM Role**: Se l'applicazione gira su EC2/ECS/Lambda

## Sicurezza

⚠️ **IMPORTANTE**:
- **NON** committare mai le credenziali AWS nel repository Git
- Assicurati che il file `.env` sia nel `.gitignore`
- In produzione, usa IAM Roles invece di access keys quando possibile
- Ruota regolarmente le credenziali

## Troubleshooting

### Errore: "UnrecognizedClientException"
- Verifica che le credenziali siano corrette
- Controlla che la regione (`AWS_REGION`) sia corretta
- Assicurati che l'utente AWS abbia i permessi necessari

### Errore: "NoCredentialsError"
- Verifica che le variabili d'ambiente siano impostate
- Controlla che il file `~/.aws/credentials` esista e sia formattato correttamente

### Errore: "AccessDeniedException"
- Verifica che l'utente AWS abbia i permessi per accedere a Secrets Manager
- Controlla che il secret name sia corretto

