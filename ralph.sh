#!/bin/bash
# Ralph Wiggum Loop - Autonomous Task Processor
# "I'm helping!" - Ralph Wiggum
set -e

TASK_DIR="tasks"
SPEC_DIR="specs"
PLAN_DIR="plans"
VERIFY_DIR="verify"
MAX_ATTEMPTS=5

echo "🔁 Ralph Loop Starting..."
echo ""

# Process task queue
for task_file in $(ls $TASK_DIR/*.md 2>/dev/null | sort); do
    TASK_ID=$(basename "$task_file" .md)
    TASK_NUM=$(echo $TASK_ID | grep -oP '^\d+' || echo "000")
    
    SPEC="$SPEC_DIR/${TASK_NUM}-spec.md"
    PLAN="$PLAN_DIR/${TASK_NUM}-plan.md"
    VERIFY="$VERIFY_DIR/${TASK_NUM}-verify.sh"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎯 Task: $TASK_ID"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Skip if no verification script
    if [ ! -f "$VERIFY" ]; then
        echo "⚠️  No verification script found: $VERIFY"
        echo "   Skipping task (create $VERIFY to enable)"
        echo ""
        continue
    fi
    
    # Ralph Loop: retry until verification passes
    ATTEMPT=0
    SUCCESS=0
    
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        ATTEMPT=$((ATTEMPT + 1))
        echo "🔄 Attempt $ATTEMPT/$MAX_ATTEMPTS"
        
        # Run verification
        if bash "$VERIFY"; then
            echo ""
            echo "✅ Task $TASK_ID COMPLETE!"
            echo ""
            mv "$task_file" "$TASK_DIR/completed/"
            SUCCESS=1
            
            # Auto-commit task completion
            echo "📝 Committing task completion to git..."
            if ./commit-status.sh "Task $TASK_NUM: Complete - $(date -u +%Y-%m-%d\ %H:%M\ UTC)"; then
                echo "✅ Changes committed and pushed to GitHub"
            else
                echo "⚠️  Git commit/push failed (continuing anyway)"
            fi
            echo ""
            
            break
        else
            echo ""
            echo "❌ Verification failed (attempt $ATTEMPT/$MAX_ATTEMPTS)"
            
            if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
                echo ""
                echo "🤖 Calling Codex to fix..."
                echo ""
                
                # Build Codex prompt from task + spec + error
                PROMPT=$(cat << EOF
Task file: $task_file
Spec file: $SPEC

The verification script failed. Please analyze the issue and fix it.

EOF
)
                # Run Codex (this will spawn interactively, user can approve changes)
                codex "$PROMPT" || true
                
                echo ""
                echo "⏳ Codex finished. Retrying verification..."
                echo ""
            fi
        fi
    done
    
    if [ $SUCCESS -eq 0 ]; then
        echo "🚨 Task $TASK_ID FAILED after $MAX_ATTEMPTS attempts"
        mv "$task_file" "$TASK_DIR/failed/"
        
        # Auto-commit task failure
        echo "📝 Committing task failure to git..."
        if ./commit-status.sh "Task $TASK_NUM: FAILED after $MAX_ATTEMPTS attempts - $(date -u +%Y-%m-%d\ %H:%M\ UTC)"; then
            echo "✅ Failure recorded in git"
        else
            echo "⚠️  Git commit/push failed"
        fi
        
        echo ""
        echo "Check logs and manually investigate."
        echo ""
    fi
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏁 Ralph Loop Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
