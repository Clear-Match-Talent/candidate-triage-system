# Specification: Database Must Handle Large Datasets Reliably

## Exit Code 0 When:
1. Load test passes: `pytest tests/test_large_dataset.py::test_1000_candidates`
2. Load test passes: `pytest tests/test_large_dataset.py::test_5000_candidates`
3. Manual verification script returns 0: `./verify/002-verify.sh`
4. No silent failures in backend logs

## Test Coverage Required:

### Load Tests
```python
def test_1000_candidates():
    """Test that 1000 candidates save and load from DB"""
    run_id = create_test_run_with_n_candidates(1000)
    
    # Verify data saved
    st = get_run_or_404(run_id)
    assert st.standardized_data is not None
    assert len(st.standardized_data) == 1000
    
    # Verify outputs saved
    assert st.outputs is not None
    assert 'standardized' in st.outputs
    
    # Verify message saved
    assert st.message is not None
    assert '1000 candidates ready' in st.message

def test_5000_candidates():
    """Test that 5000 candidates save and load from DB (stress test)"""
    run_id = create_test_run_with_n_candidates(5000)
    
    st = get_run_or_404(run_id)
    assert st.standardized_data is not None
    assert len(st.standardized_data) == 5000
```

### Error Handling Tests
```python
def test_db_save_errors_are_logged():
    """Ensure DB save failures are logged, not silent"""
    # Create run with impossibly large dataset (>50MB)
    with pytest.raises(Exception) as exc_info:
        create_test_run_with_n_candidates(100000)
    
    # Verify error was logged
    assert "database" in str(exc_info.value).lower()
```

## Performance Requirements
- Save time for 1000 candidates: < 5 seconds
- Save time for 5000 candidates: < 30 seconds
- Database file size growth: < 2x CSV size

## Acceptable Solutions
1. **Pagination**: Store first 100 rows in DB, load rest from CSV on demand
2. **Compression**: Store compressed JSON in DB
3. **External Storage**: Keep standardized_data in CSV, only metadata in DB
4. **Chunking**: Split standardized_data into multiple DB tables

## Failure Mode (Before Fix)
- CSV file created successfully (~507KB)
- Database state='standardized' but standardized_data=NULL
- Frontend shows "Standardizing..." forever
- No error logs
