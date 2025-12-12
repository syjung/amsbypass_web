#!/bin/bash

# AMS Bypass Web Application Restart Script

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Restarting AMS Bypass Web Application..."
echo ""

# Stop the application
if [ -f "stop.sh" ]; then
    ./stop.sh
else
    echo "stop.sh not found. Trying to stop manually..."
    lsof -ti:8765 | xargs kill -9 2>/dev/null
fi

sleep 2

# Start the application
if [ -f "start.sh" ]; then
    ./start.sh
else
    echo "start.sh not found. Please run start.sh manually."
    exit 1
fi

