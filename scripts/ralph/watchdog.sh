#!/bin/bash
# Ralph Watchdog - Restarts Ralph if it dies
# Usage: ./watchdog.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
LOG_FILE="$SCRIPT_DIR/watchdog.log"
RALPH_LOG="$SCRIPT_DIR/ralph.log"
CHECK_INTERVAL=60  # seconds

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

start_ralph() {
  log "Starting Ralph..."
  cd "$PROJECT_DIR"
  ./scripts/ralph/ralph.sh --tool codex 15 >> "$RALPH_LOG" 2>&1 &
  sleep 5
  if pgrep -f "ralph.sh --tool codex" > /dev/null; then
    log "Ralph started successfully (PID: $(pgrep -f 'ralph.sh --tool codex' | head -1))"
  else
    log "ERROR: Failed to start Ralph"
  fi
}

log "=== Watchdog started ==="
log "Monitoring Ralph every ${CHECK_INTERVAL}s"

while true; do
  # Check if Ralph is running
  if ! pgrep -f "ralph.sh --tool codex" > /dev/null; then
    log "Ralph not running - checking if complete..."
    
    # Check if all stories are done
    INCOMPLETE=$(cat "$SCRIPT_DIR/prd.json" 2>/dev/null | grep '"passes": false' | wc -l)
    
    if [ "$INCOMPLETE" -eq 0 ]; then
      log "All stories complete! Watchdog exiting."
      exit 0
    else
      log "$INCOMPLETE stories remaining - restarting Ralph"
      start_ralph
    fi
  fi
  
  sleep $CHECK_INTERVAL
done
