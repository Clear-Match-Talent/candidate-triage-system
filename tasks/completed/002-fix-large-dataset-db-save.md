# Task 002: Fix Database Save for Large Datasets

## Problem
Background thread in `webapp/main.py` successfully creates `standardized_candidates.csv` (1,129 rows, 507KB) but fails to update the SQLite database with the `standardized_data` JSON. The state stays 'standardized' but `standardized_data`, `outputs`, and `message` fields don't get saved.

## Root Cause
Large JSON payload (1,129 candidate rows) likely hitting SQLite size limits, transaction timeouts, or silent failure in background thread.

## Possible Solutions
1. **Pagination**: Store only subset of data in DB, load from CSV on demand
2. **Chunking**: Split standardized_data into multiple DB rows
3. **External Storage**: Keep large datasets in CSV files, store only metadata in DB
4. **Error Logging**: Add try/catch with logging to identify exact failure point

## Success Criteria (see specs/002-spec.md)
- [ ] Upload 1000+ candidate CSV
- [ ] Standardization completes successfully
- [ ] Database updated with all necessary data
- [ ] Frontend displays standardized data table
- [ ] No silent failures in background thread
- [ ] Error logs capture any failures

## Verification Command
```bash
./verify/002-verify.sh
```

## Status
🔄 **IN PROGRESS** - Codex (glow-canyon session) is working on this
