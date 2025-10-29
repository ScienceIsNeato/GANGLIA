#!/bin/bash
#
# Auto-restart wrapper for GANGLIA
# 
# This script monitors GANGLIA and automatically restarts it on any exit.
# Logs all activity to ganglia_monitor.log for debugging.
#
# Usage: ./start_ganglia_monitored.sh
# Autostart: Configured in ~/.config/autostart/ganglia.desktop
#

# Configuration
LOG_FILE="$HOME/dev/GANGLIA/ganglia_monitor.log"
RESTART_DELAY=5

# Navigate to GANGLIA directory
cd "$HOME/dev/GANGLIA" || exit 1

# Activate virtual environment and load environment variables
source venv/bin/activate
source .envrc

restart_count=0

# Infinite restart loop
while true; do
    restart_count=$((restart_count + 1))
    
    echo "[$(date)] Starting GANGLIA... (restart #$restart_count)" | tee -a "$LOG_FILE"
    
    # Run GANGLIA and capture all output to log
    python ganglia.py --store-logs --device-index 14 --audio-effects 2>&1 | tee -a "$LOG_FILE"
    EXIT_CODE=$?
    
    echo "[$(date)] GANGLIA exited with code $EXIT_CODE" | tee -a "$LOG_FILE"
    echo "[$(date)] Auto-restarting in $RESTART_DELAY seconds..." | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    
    # Always restart after a short delay
    sleep $RESTART_DELAY
done

