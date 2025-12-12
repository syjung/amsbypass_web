#!/bin/bash

# AMS Bypass Web Application Stop Script

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Configuration
PORT=8765
PID_FILE="$SCRIPT_DIR/app.pid"

# Function to kill process by PID
kill_process() {
    local pid=$1
    if ps -p "$pid" > /dev/null 2>&1; then
        echo "Stopping process (PID: $pid)..."
        kill "$pid" 2>/dev/null
        
        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! ps -p "$pid" > /dev/null 2>&1; then
                echo "✓ Process stopped successfully"
                return 0
            fi
            sleep 1
        done
        
        # Force kill if still running
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "Force killing process..."
            kill -9 "$pid" 2>/dev/null
            sleep 1
            if ! ps -p "$pid" > /dev/null 2>&1; then
                echo "✓ Process force killed"
                return 0
            fi
        fi
    fi
    return 1
}

# Stop using PID file
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    kill_process "$PID"
    rm -f "$PID_FILE"
fi

# Also check for processes using the port
if lsof -ti:$PORT > /dev/null 2>&1; then
    echo "Found process using port $PORT, stopping..."
    lsof -ti:$PORT | while read pid; do
        kill_process "$pid"
    done
    echo "✓ Port $PORT is now free"
else
    echo "No process found using port $PORT"
fi

echo "Application stopped."

