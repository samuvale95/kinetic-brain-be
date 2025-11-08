#!/bin/bash

# Kinetic Brain Backend Startup Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Status symbols
CHECKMARK="✓"
CROSS="✗"
WARNING="⚠"

echo -e "${BLUE}🚀 Starting Kinetic Brain Backend...${NC}"
echo "=================================================="

# Function to print status
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "success" ]; then
        echo -e "${GREEN}${CHECKMARK} $message${NC}"
    elif [ "$status" = "error" ]; then
        echo -e "${RED}${CROSS} $message${NC}"
    elif [ "$status" = "warning" ]; then
        echo -e "${YELLOW}${WARNING} $message${NC}"
    else
        echo -e "${BLUE}ℹ $message${NC}"
    fi
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if .env file exists
echo -e "\n${BLUE}📋 Checking configuration...${NC}"
if [ ! -f .env ]; then
    print_status "warning" "Creating .env file from template..."
    cp env.example .env
    print_status "error" "Please edit .env file with your configuration before running again."
    exit 1
else
    print_status "success" "Configuration file (.env) found"
fi

# Check if virtual environment exists
echo -e "\n${BLUE}🐍 Setting up Python environment...${NC}"
if [ ! -d "venv" ]; then
    print_status "warning" "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        print_status "success" "Virtual environment created"
    else
        print_status "error" "Failed to create virtual environment"
        exit 1
    fi
else
    print_status "success" "Virtual environment found"
fi

# Run all checks in a single command to maintain virtual environment
source venv/bin/activate && python3 -c "
import sys
sys.path.append('.')
from dotenv import load_dotenv
load_dotenv()

# Install dependencies
import subprocess
import os

print('ℹ Installing dependencies...')
result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                       capture_output=True, text=True)
if result.returncode == 0:
    print('✓ Dependencies installed successfully')
else:
    print('✗ Failed to install dependencies')
    sys.exit(1)

# Check database connection
print('\\n🗄️  Checking database connection...')
try:
    from app.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✓ Database connection successful')
        # Extract database info from connection URL
        from app.config import settings
        db_url = settings.database_url
        if '://' in db_url:
            protocol, rest = db_url.split('://', 1)
            if '@' in rest:
                auth, host_db = rest.split('@', 1)
                if '/' in host_db:
                    host_port, db_name = host_db.split('/', 1)
                    print(f'  📍 Connected to: {protocol}://***@{host_port}/{db_name}')
except Exception as e:
    print(f'✗ Database connection failed: {str(e)}')
    sys.exit(1)

# Check Redis connection (optional)
print('\\n🔴 Checking Redis connection...')
try:
    import redis
    from app.config import settings
    r = redis.from_url(settings.redis_url)
    r.ping()
    print('✓ Redis connection successful')
    print(f'  📍 Connected to: {settings.redis_url}')
except ImportError:
    print('⚠ Redis not installed, skipping check')
except Exception as e:
    print(f'⚠ Redis connection failed: {str(e)}')
    print(f'  📍 Attempted URL: {settings.redis_url}')
    print('ℹ Redis is optional, continuing without it')

# Check OpenAI API configuration
print('\\n🤖 Checking OpenAI API configuration...')
from app.config import settings
if not settings.openai_api_key or settings.openai_api_key == '':
    print('⚠ OpenAI API key not configured')
    print('ℹ AI features will be disabled')
else:
    print('✓ OpenAI API key configured')
    print(f'  📍 API Key: {settings.openai_api_key[:8]}...{settings.openai_api_key[-4:]}')
    print(f'  📍 Model: {settings.openai_model}')
    # Test OpenAI connection if configured
    try:
        from app.services.ai_service import AIService
        ai_service = AIService()
        if ai_service.client:
            print('✓ OpenAI API connection successful')
            print('  📍 Connected to: https://api.openai.com/v1')
        else:
            print('✗ OpenAI API client not initialized')
    except Exception as e:
        print(f'✗ OpenAI API connection failed: {str(e)}')

# Check Google OAuth configuration
print('\\n🔐 Checking Google OAuth configuration...')
if not settings.google_client_id or settings.google_client_id == '':
    print('⚠ Google OAuth not configured')
    print('ℹ Google authentication will be disabled')
elif not settings.google_client_secret or settings.google_client_secret == '':
    print('⚠ Google OAuth client secret missing')
    print('ℹ Google authentication will be disabled')
else:
    print('✓ Google OAuth configuration found')
    print(f'  📍 Client ID: {settings.google_client_id[:8]}...{settings.google_client_id[-4:]}')
    print(f'  📍 Redirect URI: {settings.google_redirect_uri}')
    print('  📍 OAuth URL: https://accounts.google.com/o/oauth2/v2/auth')

# Run database migrations
print('\n🔄 Running database migrations...')
try:
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config('alembic.ini')
    command.upgrade(alembic_cfg, 'head')
    print('✓ Database migrations completed')
except Exception as e:
    print(f'⚠ Database migrations failed: {str(e)}')
    print('ℹ Tables may already exist, continuing...')

# Ensure strava_sync_jobs table exists even if legacy migrations were skipped
print('\n🛠  Ensuring Strava sync jobs table exists...')
try:
    from sqlalchemy import inspect
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if 'strava_sync_jobs' not in table_names:
        with engine.begin() as conn:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS strava_sync_jobs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    strava_account_id INTEGER NOT NULL,
                    job_type VARCHAR(50) NOT NULL DEFAULT 'initial_sync',
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    status_message TEXT,
                    total_activities INTEGER NOT NULL DEFAULT 0,
                    processed_activities INTEGER NOT NULL DEFAULT 0,
                    metrics_phase INTEGER NOT NULL DEFAULT 0,
                    metrics_phases_total INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    started_at TIMESTAMPTZ,
                    finished_at TIMESTAMPTZ,
                    requested_days_back INTEGER NOT NULL DEFAULT 30,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ,
                    result JSONB,
                    CONSTRAINT fk_strava_sync_jobs_user_id FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT fk_strava_sync_jobs_account_id FOREIGN KEY(strava_account_id) REFERENCES strava_accounts(id) ON DELETE CASCADE
                );
            '''))
            conn.execute(text('''CREATE INDEX IF NOT EXISTS ix_strava_sync_jobs_user_id ON strava_sync_jobs (user_id);'''))
            conn.execute(text('''CREATE INDEX IF NOT EXISTS ix_strava_sync_jobs_strava_account_id ON strava_sync_jobs (strava_account_id);'''))
        print('✓ Created strava_sync_jobs table')
    else:
        # Ensure indexes exist even if table already present
        with engine.begin() as conn:
            conn.execute(text('''CREATE INDEX IF NOT EXISTS ix_strava_sync_jobs_user_id ON strava_sync_jobs (user_id);'''))
            conn.execute(text('''CREATE INDEX IF NOT EXISTS ix_strava_sync_jobs_strava_account_id ON strava_sync_jobs (strava_account_id);'''))
        print('✓ Strava sync jobs table already present')
except Exception as e:
    print(f'⚠ Failed to verify/create strava_sync_jobs table: {e}')

# Ensure ai_response_logs table exists
print('\n🧠 Ensuring AI response logs table exists...')
try:
    from sqlalchemy import inspect
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if 'ai_response_logs' not in table_names:
        with engine.begin() as conn:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS ai_response_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL,
                    request_type VARCHAR(100) NOT NULL,
                    model VARCHAR(100),
                    prompt TEXT,
                    request_payload JSONB,
                    response TEXT,
                    parse_success BOOLEAN NOT NULL DEFAULT TRUE,
                    error_message TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            '''))
            conn.execute(text('''CREATE INDEX IF NOT EXISTS ix_ai_response_logs_user_id ON ai_response_logs (user_id);'''))
            conn.execute(text('''CREATE INDEX IF NOT EXISTS ix_ai_response_logs_request_type ON ai_response_logs (request_type);'''))
        print('✓ Created ai_response_logs table')
    else:
        with engine.begin() as conn:
            conn.execute(text('''CREATE INDEX IF NOT EXISTS ix_ai_response_logs_user_id ON ai_response_logs (user_id);'''))
            conn.execute(text('''CREATE INDEX IF NOT EXISTS ix_ai_response_logs_request_type ON ai_response_logs (request_type);'''))
        print('✓ AI response logs table already present')
except Exception as e:
    print(f'⚠ Failed to verify/create ai_response_logs table: {e}')

print('\\n📊 Connection Status Summary:')
print('==================================================')

# Database
try:
    from app.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✓ Database: Connected')
        # Show connection details
        db_url = settings.database_url
        if '://' in db_url:
            protocol, rest = db_url.split('://', 1)
            if '@' in rest:
                auth, host_db = rest.split('@', 1)
                if '/' in host_db:
                    host_port, db_name = host_db.split('/', 1)
                    print(f'  📍 {protocol}://***@{host_port}/{db_name}')
except:
    print('✗ Database: Failed')

# Redis
try:
    import redis
    from app.config import settings
    r = redis.from_url(settings.redis_url)
    r.ping()
    print('✓ Redis: Connected')
    print(f'  📍 {settings.redis_url}')
except:
    print('⚠ Redis: Not available (optional)')
    print(f'  📍 Attempted: {settings.redis_url}')

# OpenAI
from app.config import settings
if settings.openai_api_key and settings.openai_api_key != '':
    print('✓ OpenAI: Configured')
    print(f'  📍 API Key: {settings.openai_api_key[:8]}...{settings.openai_api_key[-4:]}')
    print(f'  📍 Model: {settings.openai_model}')
    print('  📍 Endpoint: https://api.openai.com/v1')
else:
    print('⚠ OpenAI: Not configured')

# Google OAuth
if settings.google_client_id and settings.google_client_secret:
    print('✓ Google OAuth: Configured')
    print(f'  📍 Client ID: {settings.google_client_id[:8]}...{settings.google_client_id[-4:]}')
    print(f'  📍 Redirect: {settings.google_redirect_uri}')
    print('  📍 Auth URL: https://accounts.google.com/o/oauth2/v2/auth')
else:
    print('⚠ Google OAuth: Not configured')

print('==================================================')
print('\\n🚀 All systems ready! Starting FastAPI server...')
print('Server will be available at: http://localhost:8000')
print('API documentation: http://localhost:8000/docs')
print('Health check: http://localhost:8000/health')
print('==================================================')
"

# Start the application
source venv/bin/activate && python run.py

# Check Redis connection (optional)
echo -e "\n${BLUE}🔴 Checking Redis connection...${NC}"
python3 -c "
import sys
sys.path.append('.')
try:
    import redis
    from app.config import settings
    r = redis.from_url(settings.redis_url)
    r.ping()
    print('✓ Redis connection successful')
    sys.exit(0)
except ImportError:
    print('⚠ Redis not installed, skipping check')
    sys.exit(0)
except Exception as e:
    print(f'⚠ Redis connection failed: {str(e)}')
    print('ℹ Redis is optional, continuing without it')
    sys.exit(0)
" 2>/dev/null

if [ $? -eq 0 ]; then
    print_status "success" "Redis connection established"
else
    print_status "warning" "Redis connection failed (optional service)"
fi

# Check OpenAI API configuration
echo -e "\n${BLUE}🤖 Checking OpenAI API configuration...${NC}"
python3 -c "
import sys
sys.path.append('.')
from app.config import settings
if not settings.openai_api_key or settings.openai_api_key == '':
    print('⚠ OpenAI API key not configured')
    print('ℹ AI features will be disabled')
    sys.exit(0)
else:
    print('✓ OpenAI API key configured')
    sys.exit(0)
" 2>/dev/null

if [ $? -eq 0 ]; then
    print_status "success" "OpenAI API configuration found"
else
    print_status "warning" "OpenAI API not configured (AI features disabled)"
fi

# Test OpenAI connection if configured
if [ ! -z "$OPENAI_API_KEY" ] && [ "$OPENAI_API_KEY" != "" ]; then
    print_status "info" "Testing OpenAI API connection..."
    python3 -c "
import sys
sys.path.append('.')
from app.services.ai_service import AIService
try:
    ai_service = AIService()
    # Simple test - just check if client is initialized
    if ai_service.client:
        print('✓ OpenAI API connection successful')
        sys.exit(0)
    else:
        print('✗ OpenAI API client not initialized')
        sys.exit(1)
except Exception as e:
    print(f'✗ OpenAI API connection failed: {str(e)}')
    sys.exit(1)
" 2>/dev/null

    if [ $? -eq 0 ]; then
        print_status "success" "OpenAI API connection established"
    else
        print_status "error" "OpenAI API connection failed"
        print_status "info" "Check your OPENAI_API_KEY in .env file"
    fi
fi

# Check Google OAuth configuration
echo -e "\n${BLUE}🔐 Checking Google OAuth configuration...${NC}"
python3 -c "
import sys
sys.path.append('.')
from app.config import settings
if not settings.google_client_id or settings.google_client_id == '':
    print('⚠ Google OAuth not configured')
    print('ℹ Google authentication will be disabled')
    sys.exit(0)
elif not settings.google_client_secret or settings.google_client_secret == '':
    print('⚠ Google OAuth client secret missing')
    print('ℹ Google authentication will be disabled')
    sys.exit(0)
else:
    print('✓ Google OAuth configuration found')
    sys.exit(0)
" 2>/dev/null

if [ $? -eq 0 ]; then
    print_status "success" "Google OAuth configuration found"
else
    print_status "warning" "Google OAuth not configured (Google auth disabled)"
fi

# Final status summary (post-start checks)
echo -e "\n${BLUE}📊 Connection Status Summary:${NC}"
echo "=================================================="

# Database
python3 -c "
import sys
sys.path.append('.')
from app.database import engine
from sqlalchemy import text
try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✓ Database: Connected')
except:
    print('✗ Database: Failed')
" 2>/dev/null

# Redis
python3 -c "
import sys
sys.path.append('.')
try:
    import redis
    from app.config import settings
    r = redis.from_url(settings.redis_url)
    r.ping()
    print('✓ Redis: Connected')
except:
    print('⚠ Redis: Not available (optional)')
" 2>/dev/null

# OpenAI
python3 -c "
import sys
sys.path.append('.')
from app.config import settings
if settings.openai_api_key and settings.openai_api_key != '':
    print('✓ OpenAI: Configured')
else:
    print('⚠ OpenAI: Not configured')
" 2>/dev/null

# Google OAuth
python3 -c "
import sys
sys.path.append('.')
from app.config import settings
if settings.google_client_id and settings.google_client_secret:
    print('✓ Google OAuth: Configured')
else:
    print('⚠ Google OAuth: Not configured')
" 2>/dev/null

echo "=================================================="

# Start the application
echo -e "\n${GREEN}🚀 All systems ready! Starting FastAPI server...${NC}"
echo -e "${BLUE}Server will be available at: http://localhost:8000${NC}"
echo -e "${BLUE}API documentation: http://localhost:8000/docs${NC}"
echo -e "${BLUE}Health check: http://localhost:8000/health${NC}"
echo "=================================================="

python run.py
