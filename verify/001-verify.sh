#!/bin/bash
# Verification script for pending_action persistence fix
set -e

cd /home/ubuntu/clawd/candidate-triage-system

echo "🔍 Verifying pending_action persistence fix..."

# Test 1: Check that save_run_to_db is called after setting pending_action
echo "  ✓ Checking code fix..."
if ! grep -B 2 -A 6 'st.pending_action = {' webapp/main.py | grep -q "save_run_to_db(st)"; then
    echo "❌ FAILED: save_run_to_db(st) not found after st.pending_action"
    exit 1
fi

# Test 2: Run unit test (when implemented)
# echo "  ✓ Running unit tests..."
# python3 -m pytest tests/test_pending_action.py::test_pending_action_persists -v

# Test 3: Backend health check
echo "  ✓ Checking backend is running..."
if ! curl -sf http://localhost:8000/api/runs > /dev/null; then
    echo "❌ FAILED: Backend not responding"
    exit 1
fi

echo "✅ All pending_action verification checks passed!"
exit 0
