#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to get most recent log file
get_most_recent_log() {
    local logs=($(ls -t logs/test_run_*.log 2>/dev/null))
    if [[ ${#logs[@]} -eq 0 ]]; then
        echo "No test logs found"
        return 1
    fi
    echo "${logs[0]}"
}

# Function to check if a test is running
is_test_running() {
    pgrep -f "run_tests.sh" >/dev/null
    return $?
}

# Get most recent log file
log_file=$(get_most_recent_log)
if [[ $? -ne 0 ]]; then
    echo "$log_file"
    exit 1
fi

# Check if test is running
if is_test_running; then
    echo "Test in progress - Monitoring output from: $log_file"
    echo "Press Ctrl+C to stop monitoring"
    echo "----------------------------------------"
    tail -f "$log_file"
else
    echo "No test currently running - Showing results from last test: $log_file"
    echo "----------------------------------------"
    # Show the last few lines which typically contain the test summary
    tail -n 50 "$log_file" | grep -A 5 -B 5 "=.*test session starts.*=" || tail -n 20 "$log_file"
fi 