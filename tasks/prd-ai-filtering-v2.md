# PRD: AI Candidate Filtering System

## Introduction

An intelligent filtering system that processes standardized candidate lists and automatically categorizes candidates into four actionable buckets (Proceed, Human Review, Dismiss, Unable to Enrich) based on customizable, role-specific criteria. The system uses AI to evaluate candidates against must-have requirements and gating parameters, enriching data from LinkedIn profiles and providing clear reasoning for each determination to reduce noise and surface high-signal candidates.

---

## Goals

- **Reduce manual review time** by auto-filtering candidate lists down to high-signal individuals
- **Improve signal-to-noise ratio** from recruiting data sources (LinkedIn, SeekOut, Pin Wrangle)
- **Enable role-specific customization** through structured criteria configuration
- **Provide transparency** with clear reasoning for each candidate determination
- **Validate criteria accuracy** through test runs before processing full lists
- **Track filtering history** to refine criteria over time

---

## User Stories

### US-001: Configure Role Criteria
**Description:** As a recruiter, I want to configure filtering criteria for a specific role so that the AI can evaluate candidates against relevant requirements.

**Acceptance Criteria:**
- [ ] User can create a new role/project
- [ ] User can upload job description, intake form, and calibration candidates (example profiles)
- [ ] AI analyzes uploaded documents and pre-populates structured form with recommended criteria
- [ ] Form includes sections for: Must-Have Requirements, Gating Parameters (auto-reject rules), Nice-to-Haves
- [ ] User can review and edit all pre-populated criteria
- [ ] Gating parameters include checkboxes for common rules:
  - Job hopper detection (>3 roles in 5 years)
  - Bootcamp-only education (no degree)
  - Work authorization issues
  - Location restrictions
  - Custom rule text input
- [ ] User can save criteria configuration
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-002: Run Test Validation (50 Random Candidates)
**Description:** As a recruiter, I want to test filtering criteria on a small sample before running on the full list so I can validate accuracy without wasting compute.

**Acceptance Criteria:**
- [ ] User can initiate a test run from role configuration page
- [ ] System randomly selects 50 candidates from uploaded CSV
- [ ] AI evaluates each candidate against configured criteria
- [ ] Results display in web UI showing:
  - Candidate name/identifier
  - Each criteria evaluated (Pass/Fail/Unsure per criteria)
  - Quick reason for each criteria determination
  - Final bucket: Proceed / Human Review / Dismiss
- [ ] User can export test results to CSV
- [ ] If results are incorrect, user can refine criteria and re-run on same 50 candidates
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-003: Approve and Run Full or Subset Filtering
**Description:** As a recruiter, I want to run validated filtering criteria on the full candidate list or a custom subset so I can process candidates at my chosen scale.

**Acceptance Criteria:**
- [ ] After successful test validation, user can approve criteria
- [ ] User presented with run options:
  - Run on full list (all candidates)
  - Run on custom subset (user inputs number of candidates)
- [ ] System processes selected candidates using approved criteria
- [ ] Progress indicator shows filtering status
- [ ] Final results available in web UI and CSV export
- [ ] Each run logged with timestamp, criteria version, and results summary
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-004: View Filtered Results with Reasoning
**Description:** As a recruiter, I want to see filtered results with clear reasoning so I know why each candidate was categorized and can take appropriate action.

**Acceptance Criteria:**
- [ ] Results page displays all processed candidates
- [ ] Each candidate row shows:
  - Candidate identifier (name, email, LinkedIn)
  - Each criteria evaluation (Pass/Fail/Unsure)
  - Quick reason per criteria (one sentence)
  - Final determination: Proceed / Human Review / Dismiss
- [ ] Results filterable by determination bucket
- [ ] Results sortable by candidate name, determination, date processed
- [ ] User can export filtered results to CSV with all columns
- [ ] Rejected candidates remain visible but clearly marked
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-005: Data Enrichment Integration (Research Phase)
**Description:** As a system, I need to enrich candidate data from public sources and APIs so filtering decisions are based on comprehensive, up-to-date information.

**Acceptance Criteria:**
- [ ] Research and document available enrichment data sources:
  - LinkedIn public profile data (if accessible)
  - Third-party enrichment APIs (Apollo, ZoomInfo, Clearbit, etc.)
  - Public social profiles
- [ ] Define what data points are critical for filtering:
  - Current job title/company
  - Skills list
  - Education history
  - Job history (for tenure calculation)
  - Location
  - Work authorization indicators
- [ ] Evaluate cost/rate limits of enrichment options
- [ ] Propose enrichment architecture (when to enrich, caching strategy)
- [ ] Document findings in technical specification
- [ ] **Note:** Implementation may be separate project based on complexity

### US-006: Refine Criteria for Existing Role
**Description:** As a recruiter, I want to refine filtering criteria for a role after seeing results so I can improve accuracy over time.

**Acceptance Criteria:**
- [ ] User can access criteria configuration for existing role/project
- [ ] User can edit must-haves, gating parameters, nice-to-haves
- [ ] Changes create new criteria version (previous version retained)
- [ ] User can re-run test validation (50 random) with updated criteria
- [ ] User can run new batch with updated criteria on full list or subset
- [ ] Run history shows which criteria version was used for each run
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-007: View Run History for Role
**Description:** As a recruiter, I want to see the history of filtering runs for a role so I can track what's been processed and with which criteria.

**Acceptance Criteria:**
- [ ] Role detail page shows list of all runs
- [ ] Each run displays:
  - Date/timestamp
  - Criteria version used
  - Number of candidates processed
  - Results breakdown (# Proceed, # Human Review, # Dismiss)
  - Run type (Test/Full/Subset)
- [ ] User can click run to view detailed results
- [ ] User can export results from any previous run
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

---

## Functional Requirements

### FR-1: Role/Project Management
- System shall support multiple roles/projects, each with independent criteria
- Each role shall have unique identifier and name
- User shall be able to create, edit, archive roles

### FR-2: Criteria Configuration
- System shall accept job description, intake form, calibration candidates (file upload or paste)
- System shall use AI to analyze documents and suggest criteria
- User shall configure:
  - Must-have requirements (text list)
  - Gating parameters (auto-reject rules with checkboxes + custom input)
  - Nice-to-have preferences (text list)
- Criteria shall be versioned (track changes over time)

### FR-3: Candidate Filtering Logic
- System shall evaluate each candidate against all configured criteria
- For each criteria, system shall determine: Pass / Fail / Unsure
- System shall provide one-sentence reasoning per criteria
- System shall enrich candidate data from LinkedIn using Claude browser tool
- Final determination logic (applied in order):
  1. **Unable to Enrich:** If LinkedIn profile inaccessible AND CSV data insufficient to evaluate criteria → Unable to Enrich
  2. **Gating Parameters:** If ANY gating parameter triggered (OR logic) → Dismiss
  3. **Must-Haves - Fail:** If ANY must-have = Fail → Dismiss
  4. **Must-Haves - Pass:** If ALL must-haves = Pass → Proceed
  5. **Must-Haves - Unsure:** If all must-haves are Pass or Unsure (at least one Unsure) → Human Review
- Nice-to-haves are evaluated and displayed but do NOT affect final determination (informational only)

### FR-4: Test Validation Workflow
- System shall randomly select 50 candidates from input CSV
- System shall run filtering on sample
- User shall review results and optionally refine criteria
- System shall re-run on same 50 candidates after refinement
- User shall explicitly approve criteria before full run

### FR-5: Batch Processing
- After approval, user shall choose:
  - Run on full list (all candidates in CSV)
  - Run on custom subset (user specifies number)
- System shall process candidates in batches (handle large CSVs)
- System shall display progress indicator during processing

### FR-6: Results Output
- System shall export results to CSV with columns:
  - Candidate identifier fields (name, email, LinkedIn URL, etc.)
  - Each criteria name + determination (Pass/Fail/Unsure)
  - Reasoning column per criteria
  - Final determination (Proceed / Human Review / Dismiss / Unable to Enrich)
  - Timestamp
  - Criteria version ID
- System shall display results in web UI (filterable by all 4 buckets, sortable)
- All candidates remain visible with clear determination markers

### FR-7: Run History and Logging
- System shall log each run with:
  - Timestamp
  - Role/project ID
  - Criteria version ID
  - Input CSV metadata (filename, row count)
  - Results summary (# Proceed, # Human Review, # Dismiss, # Unable to Enrich)
  - Run type (Test/Full/Subset)
- User shall be able to view and export results from historical runs

### FR-8: Data Enrichment (Phase 2 - Pending Research)
- System shall enrich candidate data from public sources and APIs
- Enrichment strategy to be defined based on US-005 research
- System shall handle rate limits and API costs
- Enriched data shall be cached to avoid redundant API calls

---

## Non-Goals (Out of Scope)

### Not Included in MVP
- **Google Sheets integration** - Future enhancement, CSV export sufficient for MVP
- **Outreach automation** - This tool filters; outreach workflow is separate
- **Comparison of multiple runs** - History logging only, no side-by-side comparison
- **Resume parsing** - Enrichment focuses on public/API data, not uploaded resumes
- **Multi-user role-based access control** - MVP is internal tool (Matt, Sam, Jason, Eric)
- **ATS integration** - Export to Greenhouse/Lever is future feature
- **Real-time LinkedIn scraping** - Enrichment via APIs, not live scraping (legal/TOS issues)

---

## Design Considerations

### UI/UX Requirements

**Role Configuration Page:**
- Clean form layout with sections: Must-Haves, Gating Parameters, Nice-to-Haves
- File upload dropzone for JD, intake form, calibration candidates
- AI-suggested criteria displayed as editable fields (not locked)
- Clear indication when criteria pre-population is complete

**Test Results Page:**
- Table view with candidate rows, criteria columns
- Color coding: Green (Pass), Red (Fail), Yellow (Unsure)
- Expand/collapse reasoning per candidate
- Prominent "Approve & Run Full" or "Refine Criteria" buttons

**Full Results Page:**
- Similar table view with filters (Proceed/Review/Dismiss toggle)
- Export to CSV button
- Link to run history

**Run History Page:**
- List view of past runs with summary stats
- Click run to drill into detailed results

---

## Technical Considerations

### Architecture Components

**Backend (Python/Flask):**
- New module: `filtering/` package
  - `criteria.py` - Criteria configuration and storage
  - `evaluator.py` - AI-based candidate evaluation logic
  - `enrichment.py` - Data enrichment integration (Phase 2)
  - `batch_processor.py` - Handle large CSV processing
- New database tables (SQLite → PostgreSQL later):
  - `roles` - Role/project metadata
  - `criteria_versions` - Versioned criteria configurations
  - `filter_runs` - Run history
  - `filter_results` - Per-candidate results

**AI/LLM Integration:**
- Use Anthropic Claude (existing pattern)
- Prompt engineering for:
  - Criteria extraction from JD/intake form
  - Per-candidate evaluation against criteria
  - Reasoning generation
- Context management (batch candidates to stay within token limits)

**Data Enrichment (Phase 1):**
- LinkedIn profile enrichment using Claude browser tool
- Extract: current role, job history, education, skills, location
- Caching layer (database table) with 30-day expiry
- Fallback strategy: If LinkedIn inaccessible AND CSV insufficient → "Unable to Enrich" bucket

**Data Enrichment (Phase 2 - Future):**
- API integrations: Apollo, ZoomInfo, Clearbit, or similar
- Cross-reference multiple data sources

**CSV Processing:**
- Reuse existing `ingestion/` utilities for reading standardized CSVs
- Batch processing to handle large files (stream, don't load all into memory)
- Progress tracking via database or background job queue (Celery/RQ)

### Dependencies

**Existing:**
- `anthropic` - Claude API
- `pandas` - CSV processing
- `flask` - Web framework
- `sqlite3` - Database (migrate to PostgreSQL for production)

**New (Potential):**
- `redis` - Caching enrichment data (Phase 2)
- `celery` or `rq` - Background job processing for large batches
- Enrichment API SDKs (TBD based on US-005 research)

### Performance Considerations

- Large CSVs (1000+ candidates) may take minutes to process
- Progress indicator required for good UX
- Consider background job queue if processing >1 minute
- Cache enrichment data per candidate (email/LinkedIn URL as key)

### Security/Privacy

- Candidate data contains PII (names, emails, LinkedIn profiles)
- Ensure database encrypted at rest
- API keys for enrichment services stored in environment variables
- Do not log candidate PII in application logs

---

## Success Metrics

### Quantitative
- **Time savings:** Reduce manual review time by 50%+ (measure: avg minutes per candidate before/after)
- **Filtering accuracy:** >80% of "Proceed" candidates advance to outreach (validated by recruiter feedback)
- **Criteria refinement:** <3 test iterations needed to approve criteria on average
- **Processing speed:** Filter 100 candidates in <5 minutes

### Qualitative
- Recruiters report higher confidence in candidate quality
- Reasoning provided is clear and actionable
- Criteria configuration is intuitive (non-technical users can use it)
- Test validation workflow prevents wasted full runs

---

## Strategic Decisions (Resolved)

### 1. Data Enrichment Strategy ✅
**Decision:** LinkedIn-first enrichment using Claude browser tool
- Phase 1: Claude browser tool visits LinkedIn profiles, extracts data
- Extract: current role, job history, education, skills, location
- Cache enriched data for 30 days
- If LinkedIn inaccessible AND CSV data insufficient → "Unable to Enrich" bucket
- Phase 2 (future): Add third-party API enrichment (Apollo, ZoomInfo)

### 2. Gating Parameter Logic ✅
**Decision:** OR logic (any gating parameter = auto-reject)
- If ANY gating parameter is triggered → Dismiss
- Conservative approach to catch all potential issues
- Future: Could make configurable per role

### 3. Must-Have Evaluation Logic ✅
**Decision:** Nuanced handling based on Pass/Fail/Unsure combination
- If ANY must-have = Fail → Dismiss
- If ALL must-haves = Pass → Proceed
- If all must-haves are Pass or Unsure (at least one Unsure) → Human Review

### 4. Final Determination Buckets ✅
**Decision:** Four distinct buckets
1. **Proceed** - All must-haves Pass, no gating params triggered
2. **Human Review** - All must-haves Pass or Unsure, no gating params triggered
3. **Dismiss** - Any must-have Fail OR any gating param triggered
4. **Unable to Enrich** - LinkedIn inaccessible, CSV data insufficient

### 5. Nice-to-Haves Role ✅
**Decision:** Informational only (no impact on determination)
- Nice-to-haves are evaluated and displayed in UI
- Do NOT affect Proceed/Human Review/Dismiss/Unable to Enrich decision
- Provide context for recruiters to manually prioritize

### 6. LinkedIn Inaccessible Handling ✅
**Decision:** Separate "Unable to Enrich" bucket (4th bucket)
- Not a sub-type of Human Review - distinct category
- Easier to filter, bucket, and handle separately
- Falls back to CSV evaluation where possible

### 7. Test Validation Requirement ✅
**Decision:** Test validation is REQUIRED
- Users must run test (50 candidates) before full/subset run
- Cannot skip straight to full list
- Forces validation step to prevent wasted compute on bad criteria

### 8. Enrichment Caching Duration ✅
**Decision:** 30-day cache
- Enriched LinkedIn data cached for 30 days
- After 30 days, data considered stale and re-enriched on next encounter

### Deferred to Implementation

**Criteria Versioning UX** - Ralph will design sensible version management
**Batch Size Limits** - Test and adjust based on performance
**Form Field Design** - Ralph will create appropriate UI based on requirements

---

## Dependencies and Risks

### Dependencies
- Existing CSV standardization pipeline (`ingestion/main.py`) must produce clean input
- Anthropic Claude API availability and performance
- Enrichment API selection and integration (Phase 2)

### Risks

**High Risk:**
- **Data enrichment complexity:** If enrichment is critical and no good API exists, filtering quality suffers
  - **Mitigation:** US-005 research spike upfront; have fallback to CSV-only filtering

**Medium Risk:**
- **AI evaluation accuracy:** LLM may hallucinate or misinterpret criteria
  - **Mitigation:** Test validation workflow catches issues before full run; provide clear reasoning for audit

**Low Risk:**
- **Performance with large CSVs:** Processing 1000+ candidates may be slow
  - **Mitigation:** Background job queue, progress indicators, batch processing

---

## Timeline Estimate (Rough)

**Phase 1: Core Filtering (No Enrichment)**
- US-001: Criteria configuration - 3-5 days
- US-002: Test validation workflow - 2-3 days
- US-003: Full/subset run - 2-3 days
- US-004: Results display/export - 2-3 days
- US-006: Criteria refinement - 1-2 days
- US-007: Run history - 1-2 days

**Total Phase 1:** ~2-3 weeks (assuming full-time work)

**Phase 2: Data Enrichment**
- US-005: Research and architecture - 1 week
- Implementation - 1-2 weeks (depends on API complexity)

**Total Phase 2:** 2-3 weeks

**Overall:** 4-6 weeks for full feature (both phases)

---

## Future Enhancements (Post-MVP)

- Google Sheets integration (auto-push results per run)
- Compare multiple runs side-by-side
- Template library for common roles (pre-built criteria)
- ATS integration (export to Greenhouse, Lever)
- Multi-user access with role-based permissions
- Outreach workflow integration (auto-add "Proceed" candidates to sequence)
- Machine learning feedback loop (learn from recruiter corrections)

---

**Document Version:** 2.0 (Ready for Implementation)  
**Created:** 2026-01-26  
**Last Updated:** 2026-01-26  
**Owner:** Matt Singer / Clear Match Talent  
**Status:** Approved - Ready for Ralph Conversion

**Note:** User stories have been split into 19 atomic stories (see separate story documents) suitable for autonomous implementation via Ralph coding loop.
