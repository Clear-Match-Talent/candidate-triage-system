# US-000A: Database Schema Design and Implementation

**Type:** Foundation Story  
**Priority:** Blocker (must complete before all other stories)  
**Estimated Effort:** 1-2 days

---

## Description

As a developer, I need a complete database schema to support the AI filtering system so that all subsequent user stories can store and retrieve data correctly.

---

## Acceptance Criteria

### Schema Implementation
- [ ] All 8 tables created with correct columns and types:
  - `roles` - Role/project management
  - `criteria_versions` - Versioned criteria configurations
  - `filter_runs` - Run metadata and status
  - `filter_results` - Per-candidate results
  - `enriched_candidates` - LinkedIn enrichment cache
  - `uploaded_files` - Document storage references
  - `role_documents` - Role document storage references
  - `test_runs` - Test candidate set persistence

### Data Integrity
- [ ] All foreign key relationships defined
- [ ] CHECK constraints added for enum fields:
  - `roles.status` IN ('active', 'archived')
  - `filter_runs.run_type` IN ('test', 'full', 'subset')
  - `filter_runs.status` IN ('running', 'completed', 'failed')
  - `filter_results.final_determination` IN ('Proceed', 'Human Review', 'Dismiss', 'Unable to Enrich')
  - `uploaded_files.file_type` IN ('jd', 'intake', 'calibration')
  - `role_documents.doc_type` IN ('jd', 'intake', 'calibration')

### Performance
- [ ] Indexes created on all foreign keys
- [ ] Indexes created on frequently queried columns:
  - `roles.status`
  - `filter_runs.role_id`, `filter_runs.status`, `filter_runs.created_at`
  - `filter_results.run_id`, `filter_results.final_determination`
  - `enriched_candidates.linkedin_url`, `enriched_candidates.fetched_at`
  - `uploaded_files.role_id`
  - `role_documents.role_id`
  - `test_runs.role_id`

### Documentation
- [ ] JSON structure documented for:
  - `criteria_versions.criteria_data`
  - `filter_results.criteria_evaluations`
  - `enriched_candidates.job_history`
  - `enriched_candidates.education`
  - `enriched_candidates.skills`
- [ ] Migration script created (for future schema changes)

### Testing
- [ ] Schema creation script runs without errors
- [ ] Can insert/update/delete records in all tables
- [ ] Foreign key constraints enforced (orphaned records prevented)
- [ ] CHECK constraints enforced (invalid enum values rejected)
- [ ] Indexes improve query performance (verify with EXPLAIN QUERY PLAN)

### Code Quality
- [ ] Typecheck passes (if using typed ORM like SQLAlchemy)
- [ ] Schema file committed to version control

---

## Implementation Details

### Database File Location
```
/database/schema.sql
```

### Migration Strategy
- SQLite for development/MVP
- PostgreSQL-compatible SQL (for future migration)
- Use parameterized queries to prevent SQL injection

### ID Generation
- Use UUIDs (uuid4) for all primary keys
- Example: `str(uuid.uuid4())`

### Soft Delete Pattern
- Roles are NEVER hard-deleted
- Set `status='archived'` instead of DELETE
- Preserves history and foreign key relationships

### Progress Tracking
- `filter_runs.current_candidate` updated as processing proceeds
- Frontend polls this for "Processing X of Y" display

### Enrichment Cache Expiry
- `enriched_candidates.fetched_at` used to compute expiry
- Cache is fresh if `datetime('now') <= datetime(fetched_at, '+30 days')`
- No need for separate `expires_at` column

---

## Complete Schema SQL

```sql
-- =============================================================================
-- ROLES/PROJECTS
-- =============================================================================
CREATE TABLE roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_roles_status ON roles(status);

-- =============================================================================
-- CRITERIA VERSIONS
-- =============================================================================
CREATE TABLE criteria_versions (
    id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    criteria_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);
CREATE INDEX idx_criteria_versions_role_id ON criteria_versions(role_id);

-- =============================================================================
-- FILTER RUNS
-- =============================================================================
CREATE TABLE filter_runs (
    id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    criteria_version_id TEXT NOT NULL,
    run_type TEXT NOT NULL CHECK (run_type IN ('test', 'full', 'subset')),
    input_csv_filename TEXT,
    input_csv_path TEXT,
    total_candidates INTEGER,
    current_candidate INTEGER DEFAULT 0,
    proceed_count INTEGER DEFAULT 0,
    review_count INTEGER DEFAULT 0,
    dismiss_count INTEGER DEFAULT 0,
    unable_to_enrich_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (criteria_version_id) REFERENCES criteria_versions(id)
);
CREATE INDEX idx_filter_runs_role_id ON filter_runs(role_id);
CREATE INDEX idx_filter_runs_status ON filter_runs(status);
CREATE INDEX idx_filter_runs_created_at ON filter_runs(created_at DESC);

-- =============================================================================
-- FILTER RESULTS
-- =============================================================================
CREATE TABLE filter_results (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    candidate_id TEXT,
    candidate_name TEXT,
    candidate_email TEXT,
    candidate_linkedin TEXT,
    criteria_evaluations JSON,
    final_determination TEXT CHECK (final_determination IN ('Proceed', 'Human Review', 'Dismiss', 'Unable to Enrich')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES filter_runs(id)
);
CREATE INDEX idx_filter_results_run_id ON filter_results(run_id);
CREATE INDEX idx_filter_results_determination ON filter_results(final_determination);

-- =============================================================================
-- ENRICHED CANDIDATES (LinkedIn cache)
-- =============================================================================
CREATE TABLE enriched_candidates (
    id TEXT PRIMARY KEY,
    linkedin_url TEXT UNIQUE NOT NULL,
    current_title TEXT,
    current_company TEXT,
    job_history JSON,
    education JSON,
    skills JSON,
    location TEXT,
    raw_data JSON,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_enriched_candidates_linkedin ON enriched_candidates(linkedin_url);
CREATE INDEX idx_enriched_candidates_fetched ON enriched_candidates(fetched_at);

-- =============================================================================
-- UPLOADED FILES
-- =============================================================================
CREATE TABLE uploaded_files (
    id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('jd', 'intake', 'calibration')),
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);
CREATE INDEX idx_uploaded_files_role_id ON uploaded_files(role_id);

-- =============================================================================
-- ROLE DOCUMENTS
-- =============================================================================
CREATE TABLE role_documents (
    id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    doc_type TEXT NOT NULL CHECK (doc_type IN ('jd', 'intake', 'calibration')),
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);
CREATE INDEX idx_role_documents_role_id ON role_documents(role_id);

-- =============================================================================
-- TEST RUNS (persist test candidate sets)
-- =============================================================================
CREATE TABLE test_runs (
    id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    criteria_version_id TEXT NOT NULL,
    candidate_ids JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (criteria_version_id) REFERENCES criteria_versions(id)
);
CREATE INDEX idx_test_runs_role_id ON test_runs(role_id);
```

---

## JSON Structure Documentation

### criteria_data Format

Stored in `criteria_versions.criteria_data`:

```json
{
  "must_haves": [
    {
      "id": "string (unique within criteria, e.g. 'mh_1')",
      "description": "string (human-readable requirement)",
      "type": "string (optional: skill, experience, location, etc.)"
    }
  ],
  "gating_parameters": [
    {
      "id": "string (unique, e.g. 'gp_1')",
      "rule": "string (job_hopper, bootcamp_only, no_authorization, etc.)",
      "threshold": "string ('>3 roles in 5 years', etc.)",
      "enabled": "boolean"
    }
  ],
  "nice_to_haves": [
    {
      "id": "string (unique, e.g. 'nth_1')",
      "description": "string (human-readable preference)"
    }
  ]
}
```

**Example:**
```json
{
  "must_haves": [
    {
      "id": "mh_1",
      "description": "5+ years Python experience",
      "type": "skill"
    },
    {
      "id": "mh_2",
      "description": "Located in California or remote",
      "type": "location"
    }
  ],
  "gating_parameters": [
    {
      "id": "gp_1",
      "rule": "job_hopper",
      "threshold": ">3 roles in 5 years",
      "enabled": true
    },
    {
      "id": "gp_2",
      "rule": "bootcamp_only",
      "threshold": "No bachelor's degree, only bootcamp",
      "enabled": true
    }
  ],
  "nice_to_haves": [
    {
      "id": "nth_1",
      "description": "AWS certification"
    }
  ]
}
```

---

### criteria_evaluations Format

Stored in `filter_results.criteria_evaluations`:

```json
{
  "[criteria_id]": {
    "result": "Pass|Fail|Unsure",
    "reason": "string (one-sentence explanation)"
  }
}
```

**Example:**
```json
{
  "mh_1": {
    "result": "Pass",
    "reason": "Candidate has 7 years Python experience per LinkedIn profile"
  },
  "mh_2": {
    "result": "Pass",
    "reason": "Located in San Francisco, CA"
  },
  "gp_1": {
    "result": "Fail",
    "reason": "Held 4 positions in last 5 years, indicates job hopping"
  },
  "nth_1": {
    "result": "Unsure",
    "reason": "AWS certification not mentioned in profile"
  }
}
```

---

### enriched_candidates.job_history Format

```json
[
  {
    "title": "string",
    "company": "string",
    "start_date": "YYYY-MM (or string from LinkedIn)",
    "end_date": "YYYY-MM or 'Present'",
    "duration_months": "integer (computed)"
  }
]
```

**Example:**
```json
[
  {
    "title": "Senior Software Engineer",
    "company": "Google",
    "start_date": "2020-03",
    "end_date": "Present",
    "duration_months": 46
  },
  {
    "title": "Software Engineer",
    "company": "Microsoft",
    "start_date": "2018-01",
    "end_date": "2020-02",
    "duration_months": 26
  }
]
```

---

### enriched_candidates.education Format

```json
[
  {
    "school": "string",
    "degree": "string (BS, MS, PhD, Bootcamp, etc.)",
    "field": "string",
    "graduation_year": "integer or null"
  }
]
```

**Example:**
```json
[
  {
    "school": "Stanford University",
    "degree": "BS",
    "field": "Computer Science",
    "graduation_year": 2018
  },
  {
    "school": "App Academy",
    "degree": "Bootcamp",
    "field": "Full-Stack Web Development",
    "graduation_year": 2017
  }
]
```

---

### enriched_candidates.skills Format

```json
["string", "string", ...]
```

**Example:**
```json
["Python", "JavaScript", "React", "AWS", "Docker", "Kubernetes"]
```

---

## Database Helper Functions

### Python Example (using sqlite3)

```python
import sqlite3
import uuid
from datetime import datetime
import json

def get_db():
    """Get database connection"""
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row  # Return rows as dicts
    return conn

def init_db():
    """Initialize database with schema"""
    conn = get_db()
    with open('database/schema.sql', 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

def create_role(name, description=None):
    """Create a new role"""
    conn = get_db()
    role_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO roles (id, name, description) VALUES (?, ?, ?)",
        (role_id, name, description)
    )
    conn.commit()
    conn.close()
    return role_id

def is_enrichment_fresh(fetched_at):
    """Check if enriched data is still fresh (< 30 days old)"""
    from datetime import datetime, timedelta
    if isinstance(fetched_at, str):
        fetched_at = datetime.fromisoformat(fetched_at)
    return datetime.now() < fetched_at + timedelta(days=30)
```

---

## Migration Strategy (Future)

When migrating to PostgreSQL:

1. Replace `TEXT PRIMARY KEY` with `UUID PRIMARY KEY`
2. Replace `JSON` with `JSONB` for better performance
3. Replace `TIMESTAMP` with `TIMESTAMPTZ` for timezone support
4. Add `ON DELETE` clauses to foreign keys if needed

**PostgreSQL-compatible version of schema included in `/database/schema_postgres.sql` (future)**

---

## Testing Checklist

After implementing this story, verify:

- [ ] Run `python init_db.py` successfully
- [ ] Insert a test role: `INSERT INTO roles (id, name) VALUES ('test-123', 'Test Role')`
- [ ] Verify foreign key constraint: Try inserting criteria_version with invalid role_id (should fail)
- [ ] Verify CHECK constraint: Try `INSERT INTO roles (id, name, status) VALUES ('x', 'X', 'invalid')` (should fail)
- [ ] Query performance: Run `EXPLAIN QUERY PLAN SELECT * FROM filter_runs WHERE role_id = 'test-123'` (should use index)
- [ ] JSON parsing: Insert criteria_data, retrieve and parse with `json.loads()`

---

## Dependencies

**Blocks:**
- US-001A (Role CRUD)
- US-001C (Document Upload Backend)
- US-001E (AI Criteria Extraction)
- US-002A (Random Selection)
- US-004A (Results Backend)
- US-005A (LinkedIn Fetching)
- US-005C (Enrichment Caching)

**Essentially all other stories depend on this.**

---

## Notes

- This is a **foundation story** - must be completed first
- Schema designed for SQLite (MVP) but PostgreSQL-compatible
- JSON columns chosen for flexibility; can normalize later if needed
- Soft delete pattern (status='archived') prevents data loss
- All enum values enforced via CHECK constraints
- Indexes ensure queries stay fast even with 1000+ candidates per run

---

**Story Status:** Ready for Implementation  
**Estimated Time:** 1-2 days  
**Complexity:** Medium
