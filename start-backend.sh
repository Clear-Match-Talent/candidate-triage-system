#!/bin/bash
# Start backend with environment variables from .env

cd "$(dirname "$0")"

# Load environment variables
if [ -f .env ]; then
    set -a  # Export all variables
    source .env
    set +a
else
    echo "⚠️  Warning: .env file not found"
fi

# Check API key is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY not set in .env"
    exit 1
fi

# Kill existing backend
pkill -f "uvicorn webapp.main:app" 2>/dev/null || true
sleep 1

# Start backend
echo "🚀 Starting backend with API key..."
nohup venv/bin/uvicorn webapp.main:app --host 0.0.0.0 --port 8000 > /tmp/fastapi.log 2>&1 &

# Wait and verify
sleep 2
if curl -s http://localhost:8000/ > /dev/null; then
    echo "✅ Backend running on port 8000"
    echo "📋 Logs: tail -f /tmp/fastapi.log"
else
    echo "❌ Backend failed to start"
    exit 1
fi
