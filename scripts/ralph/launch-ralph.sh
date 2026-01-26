#!/bin/bash
# One-command launch: Sets up autonomous kanban + starts Ralph
# Usage: ./launch-ralph.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🤖 Ralph Launch Sequence"
echo "========================"
echo ""

# Step 1: Setup autonomous kanban board
echo "1️⃣  Setting up autonomous GitHub kanban board..."
"$SCRIPT_DIR/setup-auto-kanban.sh"

echo ""
echo "2️⃣  Starting Ralph in tmux session..."

# Check if tmux session already exists
if tmux has-session -t ralph 2>/dev/null; then
    echo "⚠️  Ralph session already running. Killing old session..."
    tmux kill-session -t ralph
fi

# Start Ralph in new tmux session
tmux new-session -d -s ralph "cd $SCRIPT_DIR && ./ralph.sh"

echo "✅ Ralph is running in tmux session 'ralph'"
echo ""
echo "📺 Monitor Ralph:"
echo "   tmux attach -t ralph     # Watch live (Ctrl+B then D to detach)"
echo "   tail -f $SCRIPT_DIR/progress.txt   # View progress log"
echo ""
echo "📊 View kanban board:"
echo "   https://github.com/orgs/Clear-Match-Talent/projects"
echo ""
echo "🎉 All set! The kanban board will auto-update as Ralph works."
