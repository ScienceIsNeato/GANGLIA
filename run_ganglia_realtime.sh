#!/bin/bash

# GANGLIA Realtime API Wrapper Script

# Start the Python process in the background
python3 realtime_api_working.py &
PYTHON_PID=$!

# Function to kill the Python process
cleanup() {
    echo "Cleaning up..."
    kill -9 $PYTHON_PID
    exit 0
}

# Trap signals and call cleanup
trap cleanup SIGINT SIGTERM

# Wait for the Python process to finish
wait $PYTHON_PID






