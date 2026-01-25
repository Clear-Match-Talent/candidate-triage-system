#!/bin/bash
# Pickup Script - Resume work on this project
# Run this at the start of any new session to get current context

set -e

cd "$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Candidate Triage System - Session Pickup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Pull latest changes
echo "⬇️  Pulling latest from GitHub..."
if git pull; then
    echo "✅ Repository up to date"
else
    echo "⚠️  Git pull failed (continuing with local state)"
fi
echo ""

# 2. Show recent commits
echo "📜 Recent commits:"
git log --oneline -5
echo ""

# 3. Display PROJECT_STATUS.md
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Current Project Status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -f PROJECT_STATUS.md ]; then
    cat PROJECT_STATUS.md
else
    echo "⚠️  PROJECT_STATUS.md not found!"
fi
echo ""

# 4. Check Ralph loop status
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤖 Ralph Loop Status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -f ralph.log ]; then
    echo "Last Ralph run: $(stat -c %y ralph.log | cut -d'.' -f1)"
    echo ""
    echo "Recent log tail:"
    tail -20 ralph.log
else
    echo "No ralph.log found (Ralph hasn't run yet)"
fi
echo ""

# 5. Check service health
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏥 Service Health:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check backend
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ Backend (FastAPI) running on :8000"
else
    echo "❌ Backend not responding on :8000"
fi

# Check frontend
if curl -s http://localhost:3000/ > /dev/null 2>&1; then
    echo "✅ Frontend (Next.js) running on :3000"
else
    echo "❌ Frontend not responding on :3000"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Ready to work! Check PROJECT_STATUS.md → What's Next"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
