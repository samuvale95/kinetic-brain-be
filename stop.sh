#!/bin/bash

# Kinetic Brain Backend Stop Script

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

echo -e "${BLUE}🛑 Stopping Kinetic Brain Backend...${NC}"
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

# Find and kill the server process
echo -e "\n${BLUE}🔍 Looking for running server processes...${NC}"

# Find processes running on port 8000
PID=$(lsof -ti:8000 2>/dev/null)

if [ -z "$PID" ]; then
    print_status "warning" "No server process found on port 8000"
    echo -e "${BLUE}ℹ The server may not be running${NC}"
else
    print_status "info" "Found server process (PID: $PID)"
    
    # Try graceful shutdown first
    echo -e "\n${BLUE}🔄 Attempting graceful shutdown...${NC}"
    kill -TERM $PID 2>/dev/null
    
    # Wait a bit for graceful shutdown
    sleep 3
    
    # Check if process is still running
    if kill -0 $PID 2>/dev/null; then
        print_status "warning" "Graceful shutdown failed, forcing termination..."
        kill -9 $PID 2>/dev/null
        sleep 1
        
        if kill -0 $PID 2>/dev/null; then
            print_status "error" "Failed to stop server process"
            exit 1
        else
            print_status "success" "Server process terminated forcefully"
        fi
    else
        print_status "success" "Server stopped gracefully"
    fi
fi

# Check for any remaining Python processes related to the app
echo -e "\n${BLUE}🔍 Checking for remaining app processes...${NC}"
REMAINING_PIDS=$(pgrep -f "python.*run.py\|python.*app.main\|uvicorn.*app.main" 2>/dev/null)

if [ ! -z "$REMAINING_PIDS" ]; then
    print_status "warning" "Found remaining app processes: $REMAINING_PIDS"
    echo -e "${BLUE}ℹ Terminating remaining processes...${NC}"
    echo $REMAINING_PIDS | xargs kill -TERM 2>/dev/null
    sleep 2
    
    # Force kill if still running
    REMAINING_PIDS=$(pgrep -f "python.*run.py\|python.*app.main\|uvicorn.*app.main" 2>/dev/null)
    if [ ! -z "$REMAINING_PIDS" ]; then
        echo $REMAINING_PIDS | xargs kill -9 2>/dev/null
        print_status "success" "Remaining processes terminated"
    fi
else
    print_status "success" "No remaining app processes found"
fi

# Verify port is free
echo -e "\n${BLUE}🔍 Verifying port 8000 is free...${NC}"
if lsof -ti:8000 >/dev/null 2>&1; then
    print_status "error" "Port 8000 is still in use"
    echo -e "${BLUE}ℹ You may need to manually kill the process using:${NC}"
    echo -e "${BLUE}   sudo lsof -ti:8000 | xargs kill -9${NC}"
    exit 1
else
    print_status "success" "Port 8000 is now free"
fi

# Final status
echo -e "\n${GREEN}✅ Kinetic Brain Backend stopped successfully!${NC}"
echo "=================================================="
echo -e "${BLUE}ℹ Server is no longer running on http://localhost:8000${NC}"
echo -e "${BLUE}ℹ To start the server again, run: ./start.sh${NC}"
echo "=================================================="
