# Task 001: Fix Pending Action Not Persisting to Database

## Problem
When the data assistant proposes a modification using the execute_python tool, it sets `st.pending_action` but doesn't call `save_run_to_db(st)` before returning. This means the pending action is only in memory and gets lost when the user replies 'run' (because we reload fresh st from DB).

## Root Cause
Missing database save after setting pending_action in `webapp/main.py` around line 586.

## Solution
Add `save_run_to_db(st)` after setting `st.pending_action` and before returning the explanation.

## Success Criteria (see specs/001-spec.md)
- [ ] User can propose a data modification
- [ ] Data assistant responds with confirmation prompt
- [ ] User replies "run"
- [ ] Modification is applied successfully
- [ ] No "There's no pending action" error

## Verification Command
```bash
./verify/001-verify.sh
```

## Status
✅ **FIXED** by Codex (cool-meadow session) on 2026-01-25
