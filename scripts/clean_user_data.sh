#!/bin/bash

# Script per pulire tutti i dati di un utente specifico dal database
# Preserva solo le tabelle di log (ai_response_logs)

set -e  # Exit on error

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directory dello script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Vai alla root del progetto
cd "$PROJECT_ROOT"

# Verifica che Python sia disponibile
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ ERRORE: Python3 non trovato${NC}"
    exit 1
fi

# Verifica che il file Python esista
PYTHON_SCRIPT="$SCRIPT_DIR/clean_user_data.py"
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}❌ ERRORE: Script Python non trovato: $PYTHON_SCRIPT${NC}"
    exit 1
fi

# Verifica e attiva l'ambiente virtuale se esiste
if [ -d "$PROJECT_ROOT/venv" ]; then
    echo -e "${GREEN}✓ Ambiente virtuale trovato${NC}"
    source "$PROJECT_ROOT/venv/bin/activate"
    PYTHON_CMD="python"
else
    echo -e "${YELLOW}⚠ Ambiente virtuale non trovato, uso Python3 di sistema${NC}"
    PYTHON_CMD="python3"
fi

# Esegui lo script Python con tutti gli argomenti passati
echo -e "${GREEN}🚀 Esecuzione script di pulizia dati utente...${NC}"
echo ""

$PYTHON_CMD "$PYTHON_SCRIPT" "$@"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Script completato con successo!${NC}"
else
    echo ""
    echo -e "${RED}❌ Script terminato con errori (exit code: $EXIT_CODE)${NC}"
fi

exit $EXIT_CODE

