#!/bin/bash
set -e

echo "🔍 Verifying Data Assistant chatbot flow..."

# 1. Check backend is running
echo "  ✓ Checking backend is running..."
if ! curl -s http://localhost:8000/ > /dev/null; then
    echo "❌ Backend not running on port 8000"
    exit 1
fi

# 2. Run Python test
echo "  ✓ Running chatbot flow test..."
cd "$(dirname "$0")/.."
python3 verify/003-test-chatbot.py

echo "✅ Data Assistant chatbot flow verification passed!"
exit 0
