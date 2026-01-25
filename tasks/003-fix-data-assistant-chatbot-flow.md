# Task 003: Fix Data Assistant Chatbot UX Flow

## Problem
The Data Assistant chatbot shows contradictory messages:
- Shows a proposed modification ("column G (experience_text) for all 1129 candidates")
- Asks user to "Reply ***run*** to apply this change"
- But then when user types "run", responds with "There's no pending action to apply"

This creates a confusing loop where the UI promises an action but can't execute it.

## Root Cause
The chatbot is generating responses that mention pending actions, but:
1. The `pending_action` may not be properly saved to the database
2. The UI state may be stale or not refreshing
3. The chatbot response logic doesn't match the actual pending_action state

## Solution Required
Fix the Data Assistant so that:
1. When chatbot proposes a code change, it MUST save `pending_action` to database
2. When user replies "run", the system MUST either:
   - Execute the pending action if it exists, OR
   - Show a clear error if it doesn't exist
3. The chatbot should NEVER promise "reply run" unless `pending_action` is actually saved
4. After executing an action, `pending_action` should be cleared

## Acceptance Criteria
1. User can describe a data change (e.g., "fill column G with experience_text")
2. Chatbot proposes the change with code preview
3. `pending_action` is saved to database immediately
4. User replies "run"
5. System executes the modification successfully
6. Data updates in the UI
7. `pending_action` is cleared
8. No contradictory messages at any step

## Verification Command
./verify/003-verify.sh
