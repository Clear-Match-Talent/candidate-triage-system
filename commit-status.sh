#!/bin/bash
# Commit and push project status after task completion

set -e

cd "$(dirname "$0")"

# Check if PROJECT_STATUS.md exists
if [ ! -f PROJECT_STATUS.md ]; then
    echo "❌ PROJECT_STATUS.md not found"
    exit 1
fi

# Get commit message (default or from arg)
COMMIT_MSG="${1:-Update PROJECT_STATUS.md}"

echo "📝 Committing project status..."

# Add PROJECT_STATUS.md (and any task movements)
git add PROJECT_STATUS.md
git add tasks/completed/ tasks/failed/ tasks/*.md 2>/dev/null || true

# Commit
if git diff --cached --quiet; then
    echo "ℹ️  No changes to commit"
else
    git commit -m "$COMMIT_MSG"
    echo "✅ Committed: $COMMIT_MSG"
fi

# Push to origin
echo "⬆️  Pushing to GitHub..."
if git push; then
    echo "✅ Pushed to GitHub"
else
    echo "⚠️  Push failed (check git remote/auth)"
    exit 1
fi
