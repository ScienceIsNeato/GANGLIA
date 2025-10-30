#!/bin/bash
#
# Auto-restart wrapper for GANGLIA
# 
# When GANGLIA exits, this script kills the entire terminator process
# to trigger the watchdog to restart everything fresh.
#
# Usage: ./start_ganglia_monitored.sh
# Deployed to: ~/start_ganglia_monitored.sh on ganglia hardware
# Autostart: Launched via ganglia_watchdog.sh
#

# Configuration
LOG_FILE="$HOME/dev/GANGLIA/ganglia_monitor.log"

# Navigate to GANGLIA directory
cd "$HOME/dev/GANGLIA" || exit 1

# Activate virtual environment and load environment variables
source venv/bin/activate
source .envrc

echo "[$(date)] Starting GANGLIA..." | tee -a "$LOG_FILE"

# Run GANGLIA and capture all output to log
python ganglia.py --store-logs --device-index 6 --audio-effects 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=$?

echo "[$(date)] GANGLIA exited with code $EXIT_CODE" | tee -a "$LOG_FILE"
echo "[$(date)] Killing terminator for clean restart..." | tee -a "$LOG_FILE"

# Kill the parent terminator process to trigger watchdog restart
pkill -f '^terminator.*start_ganglia_monitored'

exit $EXIT_CODE
