#!/bin/bash
# Sync Ralph progress to GitHub issues
# Run this periodically or after Ralph completes a story

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed."
    exit 1
fi

echo "Syncing progress from PRD to GitHub issues..."

# Read user stories and check their pass status
jq -r '.userStories[] | "\(.id)|\(.passes)"' "$PRD_FILE" | while IFS='|' read -r id passes; do
    # Find the GitHub issue number for this user story ID
    ISSUE_NUM=$(gh issue list --repo Clear-Match-Talent/candidate-triage-system --label "ralph" --search "[$id]" --json number --jq '.[0].number' 2>/dev/null || echo "")
    
    if [[ -z "$ISSUE_NUM" ]]; then
        echo "⚠️  No issue found for $id"
        continue
    fi
    
    # Get current issue state
    CURRENT_STATE=$(gh issue view "$ISSUE_NUM" --repo Clear-Match-Talent/candidate-triage-system --json state --jq '.state')
    
    if [[ "$passes" == "true" ]]; then
        if [[ "$CURRENT_STATE" == "OPEN" ]]; then
            echo "✅ Closing issue #$ISSUE_NUM ($id) - COMPLETED"
            gh issue close "$ISSUE_NUM" \
                --repo Clear-Match-Talent/candidate-triage-system \
                --comment "✅ Completed by Ralph. All acceptance criteria passed."
        else
            echo "ℹ️  Issue #$ISSUE_NUM ($id) already closed"
        fi
    else
        echo "⏳ Issue #$ISSUE_NUM ($id) - In progress or pending"
    fi
done

echo ""
echo "✅ Sync complete!"
