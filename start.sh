#!/bin/bash

# Kinetic Brain Backend Startup Script
# Fully automated setup and startup with Python 3.13

set -e  # Exit on error

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
INFO="ℹ"

# Python version to use
PYTHON_VERSION="3.13"
PYTHON_CMD="python${PYTHON_VERSION}"

# Function to print status
print_status() {
    local status=$1
    local message=$2
    case "$status" in
        success)
            echo -e "${GREEN}${CHECKMARK} $message${NC}"
            ;;
        error)
            echo -e "${RED}${CROSS} $message${NC}"
            ;;
        warning)
            echo -e "${YELLOW}${WARNING} $message${NC}"
            ;;
        info)
            echo -e "${BLUE}${INFO} $message${NC}"
            ;;
        *)
            echo -e "${BLUE}${INFO} $message${NC}"
            ;;
    esac
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo -e "${BLUE}🚀 Kinetic Brain Backend - Automated Startup${NC}"
echo "=================================================="

# Step 1: Check Python 3.13 installation
echo -e "\n${BLUE}🐍 Step 1: Checking Python ${PYTHON_VERSION} installation...${NC}"
if ! command_exists "$PYTHON_CMD"; then
    print_status "error" "Python ${PYTHON_VERSION} is not installed!"
    echo -e "${YELLOW}Please install Python ${PYTHON_VERSION} first.${NC}"
    echo -e "${YELLOW}On macOS, you can download it from: https://www.python.org/downloads/${NC}"
    exit 1
fi

PYTHON_VERSION_INSTALLED=$($PYTHON_CMD --version 2>&1)
print_status "success" "Found: $PYTHON_VERSION_INSTALLED"

# Step 2: Check/create .env file
echo -e "\n${BLUE}📋 Step 2: Checking configuration...${NC}"
if [ ! -f .env ]; then
    if [ -f env.example ]; then
        print_status "warning" ".env file not found, creating from env.example..."
        cp env.example .env
        print_status "info" ".env file created. Please edit it with your configuration."
        print_status "warning" "Continuing with default values..."
    else
        print_status "error" ".env file not found and env.example doesn't exist!"
        exit 1
    fi
else
    print_status "success" "Configuration file (.env) found"
fi

# Step 3: Setup virtual environment
echo -e "\n${BLUE}🐍 Step 3: Setting up Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    print_status "info" "Creating virtual environment with Python ${PYTHON_VERSION}..."
    $PYTHON_CMD -m venv venv
    if [ $? -eq 0 ]; then
        print_status "success" "Virtual environment created"
    else
        print_status "error" "Failed to create virtual environment"
        exit 1
    fi
else
    # Check if existing venv uses correct Python version
    VENV_PYTHON=$(venv/bin/python --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
    if [ "$VENV_PYTHON" != "$PYTHON_VERSION" ]; then
        print_status "warning" "Existing venv uses Python $VENV_PYTHON, recreating with Python ${PYTHON_VERSION}..."
        rm -rf venv
        $PYTHON_CMD -m venv venv
        print_status "success" "Virtual environment recreated"
    else
        print_status "success" "Virtual environment found (Python ${PYTHON_VERSION})"
    fi
fi

# Activate virtual environment
source venv/bin/activate

# Step 4: Upgrade pip
echo -e "\n${BLUE}📦 Step 4: Upgrading pip...${NC}"
python -m pip install --upgrade pip --quiet
print_status "success" "pip upgraded"

# Step 5: Install dependencies
echo -e "\n${BLUE}📦 Step 5: Installing dependencies...${NC}"
if [ -f requirements.txt ]; then
    python -m pip install -r requirements.txt --quiet
    if [ $? -eq 0 ]; then
        print_status "success" "Dependencies installed"
    else
        print_status "error" "Failed to install dependencies"
        exit 1
    fi
else
    print_status "error" "requirements.txt not found!"
    exit 1
fi

# Step 6: Verify installation and check services
echo -e "\n${BLUE}🔍 Step 6: Verifying installation and checking services...${NC}"

python << 'EOF'
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.getcwd(), '.env')
    load_dotenv(env_path)
    
    # Check database connection
    print("🗄️  Checking database connection...")
    try:
        from app.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
            from app.config import settings
            db_url = settings.database_url
            if '://' in db_url:
                protocol, rest = db_url.split('://', 1)
                if '@' in rest:
                    auth, host_db = rest.split('@', 1)
                    if '/' in host_db:
                        host_port, db_name = host_db.split('/', 1)
                        print(f"✓ Database: Connected to {protocol}://***@{host_port}/{db_name}")
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {str(e)}")
        print("⚠ Continuing anyway - ensure database is running")

    # Check Redis connection (optional)
    print("\n🔴 Checking Redis connection...")
    try:
        import redis
        from app.config import settings
        r = redis.from_url(settings.redis_url)
        r.ping()
        print(f"✓ Redis: Connected to {settings.redis_url}")
    except ImportError:
        print("⚠ Redis not installed, skipping (optional)")
    except Exception as e:
        print(f"⚠ Redis connection failed: {str(e)} (optional service)")

    # Check OpenAI configuration
    print("\n🤖 Checking OpenAI configuration...")
    from app.config import settings
    if settings.openai_api_key and settings.openai_api_key != '':
        print(f"✓ OpenAI: Configured (Key: {settings.openai_api_key[:8]}...{settings.openai_api_key[-4:]})")
    else:
        print("⚠ OpenAI: Not configured (AI features disabled)")

    # Check Google OAuth configuration
    print("\n🔐 Checking Google OAuth configuration...")
    if settings.google_client_id and settings.google_client_secret:
        print(f"✓ Google OAuth: Configured (ID: {settings.google_client_id[:8]}...)")
    else:
        print("⚠ Google OAuth: Not configured (Google auth disabled)")

    # Run database migrations
    print("\n🔄 Running database migrations...")
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config('alembic.ini')
        command.upgrade(alembic_cfg, 'head')
        print("✓ Database migrations completed")
    except Exception as e:
        print(f"⚠ Database migrations: {str(e)}")
        print("ℹ Continuing anyway - tables may already exist")

    print("\n" + "="*50)
    print("✓ All checks completed!")
    print("="*50)

except Exception as e:
    print(f"\n✗ Error during verification: {str(e)}")
    print("⚠ Continuing anyway...")
    sys.exit(0)
EOF

# Step 7: Display startup information
echo -e "\n${BLUE}📊 Service Status Summary:${NC}"
echo "=================================================="

python << 'EOF'
import sys
import os
sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv
env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(env_path)

# Database
try:
    from app.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
        print("✓ Database: Connected")
except:
    print("✗ Database: Not connected")

# Redis
try:
    import redis
    from app.config import settings
    r = redis.from_url(settings.redis_url)
    r.ping()
    print("✓ Redis: Connected")
except:
    print("⚠ Redis: Not available (optional)")

# OpenAI
from app.config import settings
if settings.openai_api_key and settings.openai_api_key != '':
    print("✓ OpenAI: Configured")
else:
    print("⚠ OpenAI: Not configured")

# Google OAuth
if settings.google_client_id and settings.google_client_secret:
    print("✓ Google OAuth: Configured")
else:
    print("⚠ Google OAuth: Not configured")

EOF

echo "=================================================="

# Step 8: Start the application
echo -e "\n${GREEN}🚀 Starting FastAPI server...${NC}"
echo "=================================================="
echo -e "${BLUE}📍 Server:     http://localhost:8000${NC}"
echo -e "${BLUE}📍 API Docs:   http://localhost:8000/docs${NC}"
echo -e "${BLUE}📍 Health:     http://localhost:8000/health${NC}"
echo -e "${BLUE}📍 ReDoc:      http://localhost:8000/redoc${NC}"
echo "=================================================="
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}\n"

# Start the application
python run.py
