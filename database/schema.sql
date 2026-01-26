-- =============================================================================
-- ROLES/PROJECTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_roles_status ON roles(status);

-- =============================================================================
-- CRITERIA VERSIONS
-- =============================================================================
CREATE TABLE IF NOT EXISTS criteria_versions (
    id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    criteria_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);
CREATE INDEX IF NOT EXISTS idx_criteria_versions_role_id ON criteria_versions(role_id);

-- =============================================================================
-- FILTER RUNS
-- =============================================================================
CREATE TABLE IF NOT EXISTS filter_runs (
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
CREATE INDEX IF NOT EXISTS idx_filter_runs_role_id ON filter_runs(role_id);
CREATE INDEX IF NOT EXISTS idx_filter_runs_status ON filter_runs(status);
CREATE INDEX IF NOT EXISTS idx_filter_runs_created_at ON filter_runs(created_at DESC);

-- =============================================================================
-- FILTER RESULTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS filter_results (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    candidate_id TEXT,
    candidate_name TEXT,
    candidate_email TEXT,
    candidate_linkedin TEXT,
    criteria_evaluations JSON,
    final_determination TEXT CHECK (final_determination IN (
        'Proceed',
        'Human Review',
        'Dismiss',
        'Unable to Enrich'
    )),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES filter_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_filter_results_run_id ON filter_results(run_id);
CREATE INDEX IF NOT EXISTS idx_filter_results_determination ON filter_results(final_determination);

-- =============================================================================
-- ENRICHED CANDIDATES (LinkedIn cache)
-- =============================================================================
CREATE TABLE IF NOT EXISTS enriched_candidates (
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
CREATE INDEX IF NOT EXISTS idx_enriched_candidates_linkedin ON enriched_candidates(linkedin_url);
CREATE INDEX IF NOT EXISTS idx_enriched_candidates_fetched ON enriched_candidates(fetched_at);

-- =============================================================================
-- UPLOADED FILES
-- =============================================================================
CREATE TABLE IF NOT EXISTS uploaded_files (
    id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('jd', 'intake', 'calibration')),
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_role_id ON uploaded_files(role_id);

-- =============================================================================
-- ROLE DOCUMENTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS role_documents (
    id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    doc_type TEXT NOT NULL CHECK (doc_type IN ('jd', 'intake', 'calibration')),
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- =============================================================================
-- ROLE CRITERIA
-- =============================================================================
CREATE TABLE IF NOT EXISTS role_criteria (
    id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    must_haves JSON NOT NULL,
    gating_params JSON NOT NULL,
    nice_to_haves JSON NOT NULL,
    is_locked INTEGER NOT NULL DEFAULT 0 CHECK (is_locked IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);
CREATE INDEX IF NOT EXISTS idx_role_criteria_role_id ON role_criteria(role_id);
CREATE INDEX IF NOT EXISTS idx_role_documents_role_id ON role_documents(role_id);

-- =============================================================================
-- TEST RUNS (persist test candidate sets)
-- =============================================================================
CREATE TABLE IF NOT EXISTS test_runs (
    id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    criteria_version_id TEXT NOT NULL,
    candidate_ids JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (criteria_version_id) REFERENCES criteria_versions(id)
);
CREATE INDEX IF NOT EXISTS idx_test_runs_role_id ON test_runs(role_id);

-- =============================================================================
-- CANDIDATE BATCHES
-- =============================================================================
CREATE TABLE IF NOT EXISTS candidate_batches (
    id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    name TEXT,
    status TEXT NOT NULL CHECK (status IN (
        'pending',
        'mapping',
        'standardizing',
        'standardized',
        'approved'
    )),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);
CREATE INDEX IF NOT EXISTS idx_candidate_batches_role_id ON candidate_batches(role_id);

-- =============================================================================
-- RAW CANDIDATES
-- =============================================================================
CREATE TABLE IF NOT EXISTS raw_candidates (
    id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    role_id TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    linkedin_url TEXT,
    location TEXT,
    current_company TEXT,
    current_title TEXT,
    raw_data JSON,
    standardized_data JSON,
    status TEXT NOT NULL CHECK (status IN ('pending', 'standardized', 'duplicate')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES candidate_batches(id),
    FOREIGN KEY (role_id) REFERENCES roles(id)
);
CREATE INDEX IF NOT EXISTS idx_raw_candidates_linkedin_url ON raw_candidates(linkedin_url);
CREATE INDEX IF NOT EXISTS idx_raw_candidates_batch_id ON raw_candidates(batch_id);

-- =============================================================================
-- BATCH FILE UPLOADS
-- =============================================================================
CREATE TABLE IF NOT EXISTS batch_file_uploads (
    id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    row_count INTEGER,
    headers JSON,
    FOREIGN KEY (batch_id) REFERENCES candidate_batches(id)
);
CREATE INDEX IF NOT EXISTS idx_batch_file_uploads_batch_id ON batch_file_uploads(batch_id);
