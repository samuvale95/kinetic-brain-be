#!/bin/bash

# Kinetic Brain Database Setup Script
# This script creates all necessary tables in the PostgreSQL database

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

echo -e "${BLUE}🗄️  Kinetic Brain Database Setup${NC}"
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

# Check if .env file exists
if [ ! -f .env ]; then
    print_status "error" ".env file not found"
    print_status "info" "Please create .env file with your database configuration first"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    print_status "error" "DATABASE_URL not found in .env file"
    exit 1
fi

print_status "success" "Database configuration loaded"

# Extract database connection details
DB_URL="$DATABASE_URL"

# Check if psql is available
if ! command -v psql &> /dev/null; then
    print_status "error" "psql command not found"
    print_status "info" "Please install PostgreSQL client tools"
    exit 1
fi

print_status "success" "PostgreSQL client found"

# Test database connection
echo -e "\n${BLUE}🔍 Testing database connection...${NC}"
if psql "$DB_URL" -c "SELECT 1;" > /dev/null 2>&1; then
    print_status "success" "Database connection successful"
else
    print_status "error" "Database connection failed"
    print_status "info" "Please check your DATABASE_URL in .env file"
    exit 1
fi

# Create tables
echo -e "\n${BLUE}🏗️  Creating database tables...${NC}"
if psql "$DB_URL" -f database/create_tables.sql; then
    print_status "success" "Database tables created successfully"
else
    print_status "error" "Failed to create database tables"
    exit 1
fi

# Verify tables were created
echo -e "\n${BLUE}🔍 Verifying table creation...${NC}"
TABLES=$(psql "$DB_URL" -t -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;" 2>/dev/null)

if [ $? -eq 0 ]; then
    print_status "success" "Tables verification successful"
    echo -e "\n${BLUE}📋 Created tables:${NC}"
    echo "$TABLES" | while read table; do
        if [ ! -z "$table" ]; then
            echo -e "  ${GREEN}✓${NC} $table"
        fi
    done
else
    print_status "warning" "Could not verify table creation"
fi

# Show database info
echo -e "\n${BLUE}📊 Database Information:${NC}"
echo "=================================================="

# Extract and show connection info
if [[ $DB_URL == postgresql://* ]]; then
    # Parse PostgreSQL URL
    PROTOCOL="postgresql"
    REST=${DB_URL#postgresql://}
    if [[ $REST == *@* ]]; then
        AUTH=${REST%%@*}
        HOST_DB=${REST#*@}
        if [[ $HOST_DB == */* ]]; then
            HOST_PORT=${HOST_DB%%/*}
            DB_NAME=${HOST_DB#*/}
            echo -e "📍 ${BLUE}Host:${NC} $HOST_PORT"
            echo -e "📍 ${BLUE}Database:${NC} $DB_NAME"
            echo -e "📍 ${BLUE}Protocol:${NC} $PROTOCOL"
        fi
    fi
fi

# Count records in each table
echo -e "\n${BLUE}📈 Table Statistics:${NC}"
for table in users user_profiles performance_metrics oauth_accounts workout_plans workouts workout_sessions calendar_events; do
    count=$(psql "$DB_URL" -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null | tr -d ' ')
    if [ $? -eq 0 ] && [ ! -z "$count" ]; then
        echo -e "  ${GREEN}✓${NC} $table: $count records"
    else
        echo -e "  ${YELLOW}⚠${NC} $table: Could not count records"
    fi
done

echo -e "\n${GREEN}✅ Database setup completed successfully!${NC}"
echo "=================================================="
echo -e "${BLUE}ℹ Your Kinetic Brain database is ready to use${NC}"
echo -e "${BLUE}ℹ You can now run: ./start.sh${NC}"
echo "=================================================="
