#!/bin/bash
# Monitor Ralph and send Telegram notification when complete or error
# Usage: ./monitor-ralph.sh &

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
LOG_FILE="$SCRIPT_DIR/ralph-output.log"
MONITOR_LOG="$SCRIPT_DIR/monitor.log"

echo "[$(date)] Ralph monitor started" >> "$MONITOR_LOG"

# Function to send notification via Clawdbot
send_notification() {
    local message="$1"
    echo "[$(date)] Sending notification: $message" >> "$MONITOR_LOG"
    
    # Send via Clawdbot message tool (will go to Telegram)
    # Using the clawdbot command-line interface
    echo "$message" > /tmp/ralph-notification.txt
}

while true; do
    # Check if Ralph process is still running
    if ! pgrep -f "ralph.sh" > /dev/null; then
        # Ralph stopped - check if it was completion or error
        TOTAL_STORIES=$(jq '.userStories | length' "$PRD_FILE" 2>/dev/null || echo "0")
        COMPLETED_STORIES=$(jq '[.userStories[] | select(.passes==true)] | length' "$PRD_FILE" 2>/dev/null || echo "0")
        
        if [ "$COMPLETED_STORIES" -eq "$TOTAL_STORIES" ] && [ "$TOTAL_STORIES" -gt 0 ]; then
            # Success!
            MESSAGE="🎉 Ralph finished! All $TOTAL_STORIES user stories complete!

✅ AI Candidate Filtering System is fully built
📊 View status: cd ~/clawd/candidate-triage-system/scripts/ralph
📁 Check: cat prd.json | jq '.userStories[] | {id, title, passes}'"
            send_notification "$MESSAGE"
            echo "[$(date)] Ralph completed successfully" >> "$MONITOR_LOG"
        else
            # Error or early exit
            LAST_LINES=$(tail -20 "$LOG_FILE" 2>/dev/null | head -10)
            MESSAGE="⚠️ Ralph stopped unexpectedly!

Progress: $COMPLETED_STORIES/$TOTAL_STORIES stories complete

Last output:
\`\`\`
$LAST_LINES
\`\`\`

Check logs: tail -50 ~/clawd/candidate-triage-system/scripts/ralph/ralph-output.log"
            send_notification "$MESSAGE"
            echo "[$(date)] Ralph stopped with error" >> "$MONITOR_LOG"
        fi
        
        # Exit monitor after notification
        echo "[$(date)] Monitor exiting" >> "$MONITOR_LOG"
        exit 0
    fi
    
    # Sleep for 30 seconds before checking again
    sleep 30
done
