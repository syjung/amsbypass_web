#!/bin/bash

# AMS Bypass Web Application Start Script

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Configuration
PORT=8765
PID_FILE="$SCRIPT_DIR/app.pid"
LOG_FILE="$SCRIPT_DIR/app.log"

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "Application is already running (PID: $OLD_PID)"
        echo "To stop it, run: ./stop.sh"
        exit 1
    else
        echo "Removing stale PID file..."
        rm -f "$PID_FILE"
    fi
fi

# Check if port is already in use
if lsof -ti:$PORT > /dev/null 2>&1; then
    echo "Port $PORT is already in use. Trying to kill the process..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null
    sleep 1
fi

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
fi

source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import flask" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the application
echo "Starting AMS Bypass Web Application on port $PORT..."
echo "Logs will be written to: $LOG_FILE"
echo "To view logs in real-time: tail -f $LOG_FILE"
echo ""

nohup python app.py > "$LOG_FILE" 2>&1 &
APP_PID=$!

# Save PID
echo $APP_PID > "$PID_FILE"

# Wait a moment and check if process is still running
sleep 2
if ps -p "$APP_PID" > /dev/null 2>&1; then
    echo "✓ Application started successfully!"
    echo "  PID: $APP_PID"
    echo "  URL: http://localhost:$PORT"
    echo "  To stop: ./stop.sh"
else
    echo "✗ Failed to start application. Check $LOG_FILE for details."
    rm -f "$PID_FILE"
    exit 1
fi

