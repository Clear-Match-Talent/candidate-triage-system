#!/bin/bash
# Create GitHub issues from PRD user stories
# Requires: gh CLI (GitHub CLI)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed."
    echo "Install with: curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg"
    echo "Then: echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\" | sudo tee /etc/apt/sources.list.d/github-cli.list"
    echo "Finally: sudo apt update && sudo apt install gh"
    exit 1
fi

# Parse PRD and create issues
jq -r '.userStories[] | 
  "---\n" +
  "ID: \(.id)\n" +
  "Title: \(.title)\n" +
  "Description: \(.description)\n" +
  "Priority: \(.priority)\n" +
  "Acceptance Criteria:\n" +
  (.acceptanceCriteria | map("- " + .) | join("\n"))
' "$PRD_FILE" | while IFS= read -r line; do
    if [[ "$line" == "---" ]]; then
        # New user story block
        ID=""
        TITLE=""
        DESC=""
        PRIORITY=""
        CRITERIA=""
        READING_CRITERIA=false
    elif [[ "$line" =~ ^ID:\ (.+)$ ]]; then
        ID="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^Title:\ (.+)$ ]]; then
        TITLE="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^Description:\ (.+)$ ]]; then
        DESC="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^Priority:\ (.+)$ ]]; then
        PRIORITY="${BASH_REMATCH[1]}"
    elif [[ "$line" == "Acceptance Criteria:" ]]; then
        READING_CRITERIA=true
    elif [[ $READING_CRITERIA == true ]] && [[ -n "$line" ]]; then
        CRITERIA="$CRITERIA$line\n"
    fi
    
    # When we hit the next separator or EOF, create the issue
    if [[ -n "$ID" && -n "$TITLE" && "$line" == "" ]]; then
        BODY="**Description:** $DESC\n\n**Acceptance Criteria:**\n$CRITERIA\n\n**Priority:** $PRIORITY\n\n---\n*Auto-generated from PRD (Ralph AI Filtering System)*"
        
        echo "Creating issue: [$ID] $TITLE"
        gh issue create \
            --title "[$ID] $TITLE" \
            --body "$BODY" \
            --label "ralph,user-story,priority-$PRIORITY" \
            --repo Clear-Match-Talent/candidate-triage-system
        
        # Reset
        ID=""
        TITLE=""
        DESC=""
        PRIORITY=""
        CRITERIA=""
        READING_CRITERIA=false
    fi
done

echo ""
echo "✅ Issues created! Now create a GitHub Project board:"
echo "1. Go to: https://github.com/Clear-Match-Talent/candidate-triage-system/projects"
echo "2. Click 'New project' → Choose 'Board' template"
echo "3. Name it 'AI Filtering System - Ralph'"
echo "4. Add all issues with label 'ralph' to the board"
echo "5. Organize columns: Backlog | In Progress | Complete"
