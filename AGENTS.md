# Candidate Triage System

**Purpose:** LLM-assisted candidate evaluation system that processes recruiting CSV exports and scores candidates against role specifications.

---

## Architecture

- **Backend:** Python 3.10 + Flask
- **Database:** SQLite (development/MVP)
- **Frontend:** Flask templates (HTML/Jinja2) + minimal JavaScript
- **LLM:** Anthropic Claude (via API)
- **Hosting:** AWS EC2 (Ubuntu)

---

## Tech Stack

**Languages:**
- Python 3.10

**Frameworks:**
- Flask 3.0 (web server)
- Anthropic SDK (LLM integration)

**Key Dependencies:**
- `anthropic`: Claude API client
- `flask`: Web framework
- `pandas`: CSV processing
- `click`: CLI interface

---

## Project Structure

```
candidate-triage-system/
├── ingestion/            ← CSV ingestion & standardization pipeline
│   ├── agents/           ← LLM agents (column mapping, deduplication)
│   ├── config/           ← Schema definitions, column mappings
│   └── utils/            ← CSV I/O, data completeness checks
├── webapp/               ← Flask web UI + chatbot
│   ├── main.py           ← Flask routes
│   ├── db.py             ← Database helpers
│   └── chatbot_*.py      ← Chatbot context/knowledge
├── evaluate_v3.py        ← Main evaluation script (latest)
├── tools/                ← Utility scripts (bucketing results, etc.)
├── verify/               ← Test scripts
├── scripts/ralph/        ← Ralph autonomous coding loop
└── tasks/                ← PRDs for features
```

---

## Conventions

### Code Style
- Python: Use `black` formatting (88 char line length)
- Indentation: 4 spaces
- Docstrings: Google style

### Imports
```python
# Standard library
import os
import sys

# Third-party
from flask import Flask, jsonify
import pandas as pd

# Local
from ingestion.config import standard_schema
from webapp.db import get_candidates
```

### Naming
- **Files:** `snake_case.py`
- **Classes:** `PascalCase`
- **Functions/variables:** `snake_case`
- **Constants:** `SCREAMING_SNAKE_CASE`

### File Organization
- Routes: `webapp/main.py`
- Database access: `webapp/db.py`
- Business logic: Individual modules (`evaluate_v3.py`, ingestion agents)
- CSV processing: `ingestion/` package
- Tests: `verify/` (ad-hoc test scripts)

---

## Key Locations

- **Main Evaluation:** `evaluate_v3.py` (latest version)
- **Web Routes:** `webapp/main.py`
- **Database:** `webapp/db.py` + `data.db` (SQLite)
- **CSV Ingestion:** `ingestion/main.py`
- **Schema Definitions:** `ingestion/config/standard_schema.py`
- **Column Mappings:** `ingestion/config/column_mappings.py`
- **Static Assets:** `webapp/static/`
- **Templates:** `webapp/templates/`

---

## Architectural Decisions

### CSV-First Approach
**Rationale:** MVP needs to work with existing recruiting exports (SeekOut, LinkedIn Recruiter, etc.) without API integrations
**Impact:** Heavy CSV processing, standardization pipeline required

### LLM for Column Mapping
**Rationale:** Recruiting CSVs have inconsistent column names - LLM can intelligently map them
**Impact:** `ingestion/agents/column_mapper.py` uses Claude to detect and map columns

### SQLite for MVP
**Rationale:** Simple, file-based, no server setup needed
**Impact:** Good for development, will need migration to PostgreSQL for production scale

### Evaluation Versions (v2, v3)
**Rationale:** Iterating on evaluation logic, keeping old versions for reference
**Impact:** Always use `evaluate_v3.py` - it's the latest

---

## Common Patterns

### Database Access
```python
# Use db.py helpers
from webapp.db import get_candidates, insert_candidate

# DON'T write raw SQL in routes
# DO use the helper functions
```

For candidate batch uploads, save files under `uploads/batches/{batch_id}` and
persist metadata with `webapp.db.create_candidate_batch` and
`webapp.db.insert_batch_file_upload`.

Role documents live under `uploads/roles/{role_id}` and are managed through
`/api/roles/{role_id}/documents` using `doc_type` values `jd`, `intake`,
`calibration` (uploads replace the previous document of the same type).

Role criteria versions are stored in `role_criteria` and managed via
`/api/roles/{role_id}/criteria` (latest + create) and
`/api/roles/{role_id}/criteria/history` (all versions). Locking is controlled
by `is_locked` to keep the form read-only after approval.

### CSV Processing
```python
# Always use pandas for CSV I/O
import pandas as pd

df = pd.read_csv('input.csv')
# ... process ...
df.to_csv('output.csv', index=False)
```

### UI Components
The workflow stepper lives in `webapp/templates/components/stepper.html` with shared
styles in `webapp/static/stepper.css`. Pass `stepper` context from `webapp/main.py`
using `build_stepper_context(...)` so the active step reflects batch status.

### Review Data
The review UI pulls `/api/batches/{batch_id}/candidates`, which returns `custom_fields`
and includes custom field values alongside standardized fields for table rendering.

### LLM Calls
```python
# Always set API key from environment
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Use structured prompts (see ingestion/agents/*.py for examples)
```

### Error Handling
```python
# Flask routes return JSON with status codes
return jsonify({"error": "Not found"}), 404

# CSV processing catches and reports errors
try:
    df = pd.read_csv(file_path)
except Exception as e:
    print(f"Error reading CSV: {e}")
    return None
```

---

## Common Gotchas

### CSV Encoding Issues
Many recruiting exports use weird encodings. Always try UTF-8 first, fallback to latin1:
```python
try:
    df = pd.read_csv(file_path, encoding='utf-8')
except UnicodeDecodeError:
    df = pd.read_csv(file_path, encoding='latin1')
```

### Column Name Inconsistency
Recruiting platforms export different column names for same data. Use `column_mapper.py` agent to standardize:
- LinkedIn might use "First Name"
- SeekOut might use "first_name"
- Pin Wrangle might use "FirstName"

### SQLite Limitations
- No `ALTER COLUMN` support - use migrations carefully
- File-based locking - not great for concurrent writes
- Plan migration to PostgreSQL before production

### Duplicate Candidates
Same candidate can appear in multiple exports. `ingestion/agents/deduplicator.py` handles this by email/name matching.

### API Rate Limits
Anthropic API has rate limits. For large batches, add delays between calls:
```python
import time
time.sleep(1)  # 1 second between LLM calls
```

---

## Development Workflow

### Setup
```bash
# Clone repo
cd candidate-triage-system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run web app
python webapp/main.py
```

### Processing Candidates
```bash
# 1. Standardize CSV
python -m ingestion.main path/to/export.csv --output-dir output/

# 2. Evaluate candidates
python evaluate_v3.py output/standardized_candidates.csv output/evaluated.csv

# 3. View results in web UI (http://localhost:5000)
```

### Running Tests
```bash
# Ad-hoc tests in verify/
python verify/003-test-chatbot.py
```

### Before Committing
- [ ] Code formatted with `black .`
- [ ] No debug `print()` statements left in
- [ ] API key not hardcoded (use environment variable)
- [ ] CSV outputs in `output/` or `.gitignore`d
- [ ] Update AGENTS.md if new patterns discovered

---

## Database Schema Reference

**The complete database schema design is documented in:**
- `tasks/us-000a-database-schema.md`

This file contains:
- All 7 tables with exact SQL definitions
- All indexes and CHECK constraints
- JSON structure specifications for criteria_data, criteria_evaluations, job_history, education, skills
- Example data formats

**When implementing database stories (US-000A or any schema modifications):**
- Read this document FIRST
- Implement exactly as specified
- Do not deviate from documented structure without updating the spec
- Apply schema changes with `python3 database/migrate.py --sql database/schema.sql` (targets `data.db`).

---

## Testing Backend API Endpoints

For all backend API endpoint stories (US-001A, US-004A, etc.):

### Manual Testing Approach
1. Implement the endpoint in `webapp/main.py` or appropriate module
2. Start Flask dev server: `python webapp/main.py`
3. Test with curl:
   ```bash
   # Example: Create role
   curl -X POST http://localhost:5000/api/roles \
     -H "Content-Type: application/json" \
     -d '{"name":"Test Role","description":"Test"}'
   
   # Example: Get all roles
   curl http://localhost:5000/api/roles
   
   # Example: Get single role
   curl http://localhost:5000/api/roles/{role_id}
   ```
4. Verify response format matches acceptance criteria
5. Check database to confirm data was created/updated:
   ```bash
   sqlite3 data.db "SELECT * FROM roles;"
   ```

### Success Criteria for API Stories
- Endpoint returns expected HTTP status codes (200, 201, 404, 400, 500)
- Response JSON matches specified format
- Database changes persist correctly
- Error cases handled gracefully (invalid input, missing resources, etc.)

---

## Ralph Workflow

This project uses Ralph for autonomous feature development.

### Creating a Feature
1. Write PRD: `Load the prd skill and create a PRD for [feature]`
2. Convert: `Load the ralph skill and convert tasks/prd-[name].md to prd.json`
3. Run: `./scripts/ralph/ralph.sh --tool claude 10` (or `--tool amp`)

### After Ralph Completes
- Test with real CSV exports (SeekOut, LinkedIn)
- Check database changes (`data.db`)
- Update this AGENTS.md with new patterns
- Commit and push

---

## Integration Points

### Anthropic Claude API
- **Purpose:** LLM for evaluation, column mapping, deduplication
- **Auth:** API key in `ANTHROPIC_API_KEY` environment variable
- **Models Used:** `claude-sonnet-4-5` (default), `claude-opus-4-5` (complex reasoning)
- **Key Files:** All `ingestion/agents/*.py`, `evaluate_v3.py`

---

## Testing Strategy

### Manual Testing
- Use sample CSVs in `uploads/` (gitignored)
- Test with exports from: SeekOut, LinkedIn Recruiter, Pin Wrangle
- Verify column mapping works for new export formats

### Key Test Scenarios
- [ ] CSV with missing columns
- [ ] CSV with duplicate candidates
- [ ] CSV from unseen recruiting platform
- [ ] Large CSV (500+ candidates)
- [ ] Evaluation against multiple role specs

---

## Deployment

### Environments
- **Development:** Local machine / localhost:5000
- **Production:** AWS EC2 (Ubuntu) - http://[ec2-ip]:5000

### Environment Variables
- `ANTHROPIC_API_KEY`: Required for LLM calls
- `FLASK_ENV`: `development` or `production`
- `DATABASE_URL`: (future) PostgreSQL connection string

### Deploy Process
```bash
# SSH to EC2
ssh ubuntu@[ec2-ip]

# Pull latest
cd candidate-triage-system
git pull

# Restart Flask (using supervisor/systemd - TBD)
sudo systemctl restart candidate-triage
```

---

## Current Limitations & TODOs

### Known Issues
- SQLite not suitable for concurrent users → Migrate to PostgreSQL
- No authentication/authorization → Add user auth before multi-user
- CSV uploads stored on disk → Move to S3 for production
- Evaluation is synchronous (blocks web UI) → Add background job queue

### Planned Features
- User authentication (login/logout)
- Role spec management UI
- Batch evaluation queue
- Export results to ATS (Greenhouse, Lever)
- Candidate communication tracking

---

## Troubleshooting

### "Invalid API Key" Error
**Symptom:** `anthropic.AuthenticationError: Invalid API key`
**Cause:** `ANTHROPIC_API_KEY` not set or incorrect
**Fix:** `export ANTHROPIC_API_KEY="sk-ant-..."`

### "Column not found" during CSV processing
**Symptom:** `KeyError: 'email'` when processing CSV
**Cause:** CSV columns don't match expected schema
**Fix:** Run through `ingestion/main.py` first to standardize columns

### Database locked
**Symptom:** `sqlite3.OperationalError: database is locked`
**Cause:** Multiple processes trying to write to SQLite
**Fix:** Close other connections, or migrate to PostgreSQL for multi-user

### Flask app won't start
**Symptom:** `Address already in use`
**Cause:** Port 5000 already taken
**Fix:** `pkill -f "python webapp/main.py"` or change port in `main.py`

---

## Resources

- **Main Repo:** https://github.com/mattds34/candidate-triage-system (if applicable)
- **Anthropic Docs:** https://docs.anthropic.com
- **Flask Docs:** https://flask.palletsprojects.com

---

**Last Updated:** 2026-01-25
**Maintained By:** Matt Singer / Clear Match Talent
