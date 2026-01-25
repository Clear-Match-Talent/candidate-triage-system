# Specification: Pending Action Must Persist Across Requests

## Exit Code 0 When:
1. Integration test passes: `pytest tests/test_pending_action.py::test_pending_action_persists`
2. Manual verification script returns 0: `./verify/001-verify.sh`

## Test Coverage Required:

### Unit Test
```python
def test_pending_action_persists():
    """Test that pending_action survives database round-trip"""
    run_id = "test_run_001"
    
    # Create run with pending action
    st = RunStatus(
        run_id=run_id,
        created_at=time.time(),
        run_name="test_pending",
        role_label="Engineer",
        state="standardized",
        pending_action={
            "code": "df['column_a'] = ''",
            "explanation": "Clear column A",
            "timestamp": time.time()
        }
    )
    save_run_to_db(st)
    
    # Reload from DB
    loaded = get_run_or_404(run_id)
    
    # Verify pending_action persists
    assert loaded.pending_action is not None
    assert loaded.pending_action['code'] == "df['column_a'] = ''"
    assert loaded.pending_action['explanation'] == "Clear column A"
```

### Integration Test
Manual flow should work:
1. Upload small CSV to create run
2. Use data assistant to request modification: "clear column A"
3. Assistant responds with explanation + "Reply 'run' to apply"
4. Reply "run"
5. **Expected**: Modification applied successfully
6. **Failure mode (before fix)**: "There's no pending action to apply"

## Edge Cases
- Multiple pending actions (should only keep latest)
- Pending action with large code payload (>10KB)
- Concurrent requests to same run
