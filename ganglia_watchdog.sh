#!/bin/bash
#
# GANGLIA Watchdog - Monitors and relaunches terminator when it exits
#
# This script runs in the background and ensures terminator (with GANGLIA)
# is always running. When terminator exits, it waits briefly then relaunches
# everything fresh (simulating a reboot).
#
# Usage: Run at startup via ~/.config/autostart/ganglia.desktop
# Deployed to: ~/ganglia_watchdog.sh on ganglia hardware
#

RESTART_DELAY=5
WATCHDOG_LOG="$HOME/ganglia_watchdog.log"

while true; do
    # Check if terminator with our script is running
    if ! pgrep -f 'terminator.*start_ganglia_monitored' > /dev/null; then
        echo "[$(date)] Terminator not running - launching..." >> "$WATCHDOG_LOG"
        
        # Launch terminator with GANGLIA
        # When the script exits, terminator closes, and watchdog relaunches it
        terminator -f -p LargeFont -e "$HOME/start_ganglia_monitored.sh" &
        
        # Give it time to start
        sleep 2
    fi
    
    # Check every 5 seconds
    sleep $RESTART_DELAY
done

