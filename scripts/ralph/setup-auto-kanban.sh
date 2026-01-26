#!/bin/bash
# Fully autonomous GitHub Project board setup and sync
# No manual steps required

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
REPO="Clear-Match-Talent/candidate-triage-system"
PROJECT_NAME="AI Filtering System - Ralph"

echo "🚀 Setting up autonomous GitHub Project board..."

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "📦 Installing GitHub CLI..."
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    sudo apt update -qq && sudo apt install gh -y -qq
    echo "✅ GitHub CLI installed"
fi

# Check authentication
if ! gh auth status &>/dev/null; then
    echo "🔐 Authenticating with GitHub..."
    gh auth login
fi

echo ""
echo "📋 Step 1: Creating GitHub Project board..."

# Create project using GraphQL API
PROJECT_ID=$(gh api graphql -f query='
  mutation($owner: String!, $title: String!) {
    createProjectV2(input: {
      ownerId: $owner
      title: $title
    }) {
      projectV2 {
        id
        number
      }
    }
  }
' -f owner="$(gh api /repos/$REPO --jq '.owner.node_id')" -f title="$PROJECT_NAME" --jq '.data.createProjectV2.projectV2.id' 2>/dev/null || echo "")

if [[ -z "$PROJECT_ID" ]]; then
    echo "⚠️  Project might already exist. Fetching existing project..."
    PROJECT_ID=$(gh api graphql -f query='
      query($owner: String!, $repo: String!) {
        repository(owner: $owner, name: $repo) {
          projectsV2(first: 20) {
            nodes {
              id
              title
            }
          }
        }
      }
    ' -f owner="Clear-Match-Talent" -f repo="candidate-triage-system" --jq ".data.repository.projectsV2.nodes[] | select(.title == \"$PROJECT_NAME\") | .id" 2>/dev/null || echo "")
fi

if [[ -z "$PROJECT_ID" ]]; then
    echo "❌ Failed to create or find project"
    exit 1
fi

echo "✅ Project ready: $PROJECT_NAME (ID: $PROJECT_ID)"

echo ""
echo "📝 Step 2: Creating issues from PRD..."

# Parse PRD and create issues, adding them to the project
jq -c '.userStories[]' "$PRD_FILE" | while IFS= read -r story; do
    ID=$(echo "$story" | jq -r '.id')
    TITLE=$(echo "$story" | jq -r '.title')
    DESC=$(echo "$story" | jq -r '.description')
    PRIORITY=$(echo "$story" | jq -r '.priority')
    PASSES=$(echo "$story" | jq -r '.passes')
    
    # Build acceptance criteria
    CRITERIA=$(echo "$story" | jq -r '.acceptanceCriteria | map("- " + .) | join("\n")')
    
    # Check if issue already exists
    EXISTING_ISSUE=$(gh issue list --repo "$REPO" --label "ralph" --search "[$ID]" --json number --jq '.[0].number' 2>/dev/null || echo "")
    
    if [[ -n "$EXISTING_ISSUE" ]]; then
        echo "ℹ️  Issue #$EXISTING_ISSUE already exists for $ID"
        ISSUE_NUM="$EXISTING_ISSUE"
    else
        # Create the issue
        BODY="**Description:** $DESC

**Acceptance Criteria:**
$CRITERIA

**Priority:** $PRIORITY

---
*Auto-managed by Ralph*"
        
        ISSUE_NUM=$(gh issue create \
            --repo "$REPO" \
            --title "[$ID] $TITLE" \
            --body "$BODY" \
            --label "ralph,user-story,priority-$PRIORITY" \
            --json number --jq '.number' 2>/dev/null)
        
        echo "✅ Created issue #$ISSUE_NUM: $ID"
    fi
    
    # Add issue to project
    ISSUE_NODE_ID=$(gh api "/repos/$REPO/issues/$ISSUE_NUM" --jq '.node_id')
    gh api graphql -f query='
      mutation($project: ID!, $contentId: ID!) {
        addProjectV2ItemById(input: {
          projectId: $project
          contentId: $contentId
        }) {
          item {
            id
          }
        }
      }
    ' -f project="$PROJECT_ID" -f contentId="$ISSUE_NODE_ID" &>/dev/null || true
    
    # Close if already passed
    if [[ "$PASSES" == "true" ]]; then
        gh issue close "$ISSUE_NUM" --repo "$REPO" --comment "✅ Already completed" &>/dev/null || true
        echo "  → Marked as complete"
    fi
done

echo ""
echo "✅ All issues created and added to project board!"

echo ""
echo "⚙️  Step 3: Setting up auto-sync watcher..."

# Create systemd service for continuous monitoring (if running as a service)
# Or use a background process

cat > "$SCRIPT_DIR/.auto-sync-daemon.sh" << 'EOFSCRIPT'
#!/bin/bash
# Background daemon to watch PRD changes and sync to GitHub

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
REPO="Clear-Match-Talent/candidate-triage-system"

while true; do
    # Check every 60 seconds
    sleep 60
    
    # Sync progress
    jq -c '.userStories[]' "$PRD_FILE" | while IFS= read -r story; do
        ID=$(echo "$story" | jq -r '.id')
        PASSES=$(echo "$story" | jq -r '.passes')
        
        # Find issue
        ISSUE_NUM=$(gh issue list --repo "$REPO" --label "ralph" --search "[$ID]" --json number --jq '.[0].number' 2>/dev/null || echo "")
        
        if [[ -n "$ISSUE_NUM" ]] && [[ "$PASSES" == "true" ]]; then
            # Get current state
            STATE=$(gh issue view "$ISSUE_NUM" --repo "$REPO" --json state --jq '.state')
            
            if [[ "$STATE" == "OPEN" ]]; then
                gh issue close "$ISSUE_NUM" --repo "$REPO" --comment "✅ Completed by Ralph" &>/dev/null
                echo "[$(date)] Closed issue #$ISSUE_NUM ($ID)"
            fi
        fi
    done
done
EOFSCRIPT

chmod +x "$SCRIPT_DIR/.auto-sync-daemon.sh"

# Start the daemon in background
nohup "$SCRIPT_DIR/.auto-sync-daemon.sh" > "$SCRIPT_DIR/auto-sync.log" 2>&1 &
DAEMON_PID=$!
echo $DAEMON_PID > "$SCRIPT_DIR/.auto-sync.pid"

echo "✅ Auto-sync daemon started (PID: $DAEMON_PID)"
echo "   Log: $SCRIPT_DIR/auto-sync.log"

echo ""
echo "🎉 SETUP COMPLETE!"
echo ""
echo "📊 View your kanban board:"
echo "   https://github.com/orgs/Clear-Match-Talent/projects"
echo ""
echo "✨ The board will auto-update as Ralph completes tasks"
echo ""
echo "To stop auto-sync: kill \$(cat $SCRIPT_DIR/.auto-sync.pid)"
