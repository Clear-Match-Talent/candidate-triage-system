# PRD Review: AI Candidate Filtering System
**Document:** prd-ai-filtering.md  
**Reviewer:** Henry (AI Assistant)  
**Date:** 2026-01-26  
**Status:** Critical Issues Identified - Revisions Required Before Implementation

---

## Executive Summary

The PRD provides a solid foundation with clear goals, well-defined user workflows, and appropriate risk awareness. However, **critical technical gaps and unresolved dependencies prevent immediate implementation**. Key blockers include undefined data enrichment strategy, oversized user stories for autonomous coding, and missing technical specifications.

**Recommendation:** Address critical issues before converting to Ralph JSON and beginning implementation.

---

## Strengths ✅

### 1. Clear Problem Definition
- **Goals are specific and measurable:** Reduce manual review time by 50%, achieve >80% filtering accuracy
- **Test validation workflow is well-designed:** 50-candidate test prevents wasted compute on bad criteria
- **Three-bucket output is intuitive:** Proceed/Human Review/Dismiss provides clear action paths
- **User stories follow clear personas:** "As a recruiter, I want..." format maintains focus

### 2. Well-Scoped Non-Goals
- Google Sheets integration, ATS integration, and multi-user access properly deferred to post-MVP
- Realistic distinction between Phase 1 (core filtering) and Phase 2 (enrichment)
- Avoids scope creep by explicitly listing out-of-scope features

### 3. Risk Awareness and Mitigation
- **Data enrichment complexity** identified as high risk with research spike proposed
- **AI evaluation accuracy** addressed through test validation workflow
- **Performance concerns** acknowledged with background job queue suggestion
- Security/privacy considerations documented (PII handling, API keys)

### 4. Comprehensive Success Metrics
- **Quantitative targets:** 50% time savings, 80% accuracy, <3 refinement iterations
- **Qualitative measures:** Confidence, clarity, intuitiveness
- **Processing speed benchmark:** 100 candidates in <5 minutes

---

## Critical Issues ⚠️ (MUST FIX)

### 1. User Stories Are Too Large for Ralph

Several user stories exceed the ~168K token limit for a single Ralph iteration and must be split into atomic pieces.

**US-001: Configure Role Criteria** (Currently too large)

Should be split into:
- **US-001A:** Create role/project management (database schema, CRUD operations)
- **US-001B:** File upload functionality for JD/intake/calibration candidates
- **US-001C:** AI document analysis and criteria extraction
- **US-001D:** Structured criteria configuration form UI

**US-002: Run Test Validation** (Currently too large)

Should be split into:
- **US-002A:** Random candidate selection and test run backend logic
- **US-002B:** Test results display UI with reasoning and export

**US-004: View Filtered Results** (Currently too large)

Should be split into:
- **US-004A:** Results data model and backend API
- **US-004B:** Results UI (table view, filters, sorting)
- **US-004C:** CSV export functionality

**Recommendation:** Break these stories into single-focus tasks before Ralph JSON conversion. Each story should be completable in one autonomous iteration.

---

### 2. Data Enrichment Strategy is a Blocker

The PRD treats data enrichment as both critical and deferred, creating an implementation blocker.

**Current Contradiction:**
- Open Questions section calls enrichment "critical" for filtering decisions
- Architecture section marks enrichment as "Phase 2 - Pending Research"
- US-005 is research-only with note "may be separate project"

**Impact on MVP:**
- CSV data typically includes: name, email, LinkedIn URL, possibly current title
- CSV data typically does NOT include: detailed job history, education, skills list, tenure information
- Without enrichment, many gating parameters cannot be evaluated:
  - "Job hopper detection (>3 roles in 5 years)" - requires job history
  - "Bootcamp-only education" - requires education data
  - Skill matching - requires skills list

**Critical Questions:**
1. Can Phase 1 MVP function with CSV data only (limited criteria)?
2. If yes, which criteria are actually evaluable with CSV-only data?
3. If no enrichment, what's the minimum viable criteria set?

**Recommendations:**

**Option A: CSV-Only MVP**
- Phase 1 works with whatever data is in the CSV
- Criteria limited to: location, current title keywords, basic LinkedIn profile signals
- Gating parameters simplified to what's available in CSV
- Document limitations clearly to users

**Option B: Enrichment-First Approach**
- Complete US-005 research spike BEFORE building filtering
- Select enrichment API and integrate
- Design filtering around confirmed enrichment capabilities
- Delays Phase 1 but ensures full feature set

**Option C: Hybrid Approach**
- Build filtering engine to work with available data
- Design enrichment integration points (abstraction layer)
- Ship Phase 1 with CSV-only, add enrichment in Phase 2
- Requires clear API design between filtering and enrichment modules

**Decision Required:** Choose Option A, B, or C before proceeding.

---

### 3. Missing Technical Specifications

**Structured Form Schema Not Defined**

The PRD describes a "structured form" for criteria configuration but doesn't specify:
- Exact field types (text input, dropdown, multi-select, checkbox)
- Field validation rules
- How repeating fields work (e.g., multiple required skills)

**Example undefined:**
- "Required skill: [____]" - Single field? Repeating fields? Dropdown from predefined list?
- "Minimum years experience: [____]" - Free text? Number input with min/max? Per-skill or global?
- "Location must be in: [____]" - Multi-select? Free text with comma separation?

**Impact:** Frontend developer cannot build UI without this specification.

**Recommendation:** Add US-000B: Design criteria configuration form schema with field-level specification.

---

**Database Schema Not Specified**

Backend database tables are mentioned but not defined:

**`roles` table - what columns?**
- `id`, `name`, `created_at`?
- Is there a `status` field (active/archived)?
- Is there an `owner_id` for multi-user future?

**`criteria_versions` table - how is criteria stored?**
- JSON blob of entire configuration?
- Structured columns for must-haves/gating-params/nice-to-haves?
- How are versioning relationships tracked?

**`filter_runs` table - what's logged?**
- Run ID, role ID, criteria version ID, timestamp?
- Input CSV metadata (filename, row count)?
- Results summary (proceed count, review count, dismiss count)?

**`filter_results` table - per-candidate results:**
- Candidate identifier fields (replicate from CSV or foreign key)?
- How are per-criteria evaluations stored (JSON? Separate table?)?
- How is reasoning stored?

**Impact:** Ralph cannot implement database-dependent stories without schema definition.

**Recommendation:** Add US-000A: Design and implement database schema for roles/criteria/runs/results.

---

**AI Prompt Templates Not Designed**

The PRD mentions AI functionality but doesn't define how it works:

**Criteria Extraction from JD/Intake (US-001C):**
- What prompt is sent to Claude?
- What output format is expected?
- How does system parse response into structured form fields?

**Per-Candidate Evaluation (US-002, US-003):**
- What prompt template is used?
- How are criteria injected into prompt?
- How is "Pass/Fail/Unsure" consistently extracted from response?
- How is reasoning extracted?

**Example Needed:**
```
Prompt Template:
"Evaluate candidate against the following criteria:
1. [Must-Have 1]: [Description]
2. [Must-Have 2]: [Description]

Candidate Data:
[Candidate fields]

For each criteria, respond with:
- Pass/Fail/Unsure
- One-sentence reasoning

Format your response as JSON:
{
  "criteria_1": {"result": "Pass", "reason": "..."},
  ...
}"
```

**Impact:** AI integration stories cannot be implemented without prompt design.

**Recommendation:** Add US-000C: Design and test AI prompt templates for criteria extraction and candidate evaluation.

---

### 4. "Same 50 Candidates" Persistence Unclear

**Issue:** US-002 states "re-run on same 50 candidates after refinement" but mechanism is undefined.

**Questions:**
- How are the 50 candidates persisted after initial test run?
- When user clicks "Refine Criteria," how does system retrieve the same 50?
- What if user uploads a different CSV - does test set reset?
- Are the 50 candidates stored in database or just their IDs referenced from CSV?

**Impact:** Test validation workflow cannot be implemented without persistence strategy.

**Recommendation:** Add acceptance criteria to US-002:
- "System persists test candidate IDs/data after initial run"
- "Refinement button uses saved test set, not new random selection"
- "New CSV upload resets test set and requires new validation"

---

## Important Gaps 🤔 (SHOULD ADDRESS)

### 1. Gating Parameter Logic Not Resolved

**Current State:**
- FR-3 states: "If any gating parameter triggered → Dismiss"
- Open Question #2 asks: "Should it be OR or AND?"

**Impact:**
- OR logic (any gating param = reject) is conservative - fewer false negatives, more false positives
- AND logic (all gating params = reject) is permissive - more false negatives, fewer false positives
- This fundamentally changes evaluation code logic

**Recommendation:** 
- **Choose OR logic** (any gating param triggers rejection) for MVP
- Conservative approach avoids bad candidates slipping through
- Document in FR-3 as definitive rule, remove from Open Questions

---

### 2. "Unsure" Handling Not Defined

**Current State:**
- Open Question #3: "If must-have returns Unsure, Human Review or Dismiss?"

**Why It Matters:**
- If Unsure → Human Review: May generate too much manual review, defeating purpose of automation
- If Unsure → Dismiss: May reject good candidates where AI simply lacks data
- Different criteria may warrant different handling

**Use Cases:**
- "5+ years Python experience" returns Unsure because resume is vague → Human Review makes sense
- "Located in California" returns Unsure because location field is empty → Dismiss may be appropriate

**Recommendations:**
- **Default rule for MVP:** Unsure → Human Review (conservative approach)
- Document in FR-3 as definitive rule
- **Future enhancement:** Criteria-specific Unsure handling (some criteria have different thresholds)

---

### 3. Nice-to-Haves Are Underspecified

**Current State:**
- FR-3 mentions: "Nice-to-haves influence prioritization but not final bucket"

**Questions:**
- What prioritization? There's no ranking/scoring system defined in the PRD
- If Nice-to-Haves don't affect Proceed/Review/Dismiss decision, what do they actually do?
- Are they just informational (show in reasoning) or do they affect something?

**Recommendations:**

**Option A: Remove Nice-to-Haves from MVP**
- Simplify to just Must-Haves and Gating Parameters
- Add Nice-to-Haves in future when prioritization/ranking is added

**Option B: Define Nice-to-Haves as Informational Only**
- Nice-to-Haves are evaluated (Pass/Fail/Unsure)
- Results displayed in UI but don't affect final determination
- Help recruiter prioritize within "Proceed" bucket manually

**Option C: Add Scoring/Ranking System**
- Nice-to-Haves contribute to a score (0-100)
- Candidates in "Proceed" bucket ranked by score
- Adds complexity, may not be MVP

**Decision Required:** Choose Option A (simplest), B, or C.

---

### 4. CSV Input Validation Missing

**Current State:**
- PRD assumes clean, standardized CSV input
- No error handling for invalid inputs defined

**What If:**
- User uploads non-standardized CSV (wrong/missing columns)?
- User uploads empty CSV or CSV with 0 rows?
- User uploads CSV with candidates already filtered (duplicate run)?
- CSV has malformed data (missing required fields like email)?

**Recommendation:** Add US-008: CSV Validation and Error Handling
- Validate CSV has required columns (name, email, LinkedIn at minimum)
- Check CSV has >0 rows, <max_allowed rows
- Detect duplicate uploads (warn user if same filename/row count/hash)
- Display clear error messages for invalid CSVs
- Allow user to correct and re-upload

---

### 5. Criteria Approval UX Undefined

**Current State:**
- US-003 says "After successful test validation, user can approve criteria"
- Exact approval mechanism not specified

**Questions:**
- Is there a big "Approve Criteria" button on test results page?
- Does user need to check a confirmation box ("I verify these results look correct")?
- Or is approval implicit (user just clicks "Run Full List" from test results)?
- Can user skip approval and run full list without testing? (Should this be prevented?)

**Recommendation:** Define exact UX flow:
- Add "Approve Criteria" button to test results page (explicit approval step)
- Button is only enabled after successful test run
- Approval unlocks "Run Full List" and "Run Subset" options
- Document in US-003 acceptance criteria

---

## Minor Issues 📝 (CAN DEFER)

### 1. Timeline Estimate May Be Optimistic

**Current Estimate:** "Phase 1: 2-3 weeks (full-time work)"

**Assumes:**
- Database schema is already defined (it's not)
- AI prompts are designed and tested (they're not)
- No enrichment blockers (decision pending)
- No unexpected technical challenges
- Full-time focus (no context-switching)

**Reality Check:**
- With current unknowns, Phase 1 likely 4-6 weeks
- Add 1-2 weeks for US-005 enrichment research if needed
- Total: 5-8 weeks more realistic

**Recommendation:** Update timeline after critical issues are resolved.

---

### 2. Security Considerations Are Light

**Current Coverage:**
- PII encryption mentioned
- API key storage in environment variables mentioned

**Missing:**
- **Input sanitization:** File uploads could contain malicious content (CSV injection, path traversal)
- **Rate limiting:** Prevent API abuse (user spamming runs to burn credits)
- **Audit logging:** Who ran what filter when (compliance, debugging)
- **Output sanitization:** Ensure AI-generated reasoning doesn't contain sensitive data leakage

**Recommendation:** Add to FR-9 or expand Technical Considerations section with:
- File upload validation (scan for malicious payloads)
- API rate limiting per user/role
- Audit log table (`audit_log`: user, action, timestamp, metadata)
- Output review before displaying AI-generated text

---

### 3. Success Metrics Need Baseline

**Current Metric:** "Reduce manual review time by 50%"

**Problem:**
- Baseline (current manual review time) not documented
- No way to measure success without starting point

**Questions:**
- How long does it currently take to manually review 100 candidates?
- How many candidates do you manually review per week/month?
- What's the current accuracy rate (candidates that advance vs don't)?

**Recommendation:**
- Document current manual workflow time (e.g., "Currently 5 minutes per candidate")
- Track metrics before and after AI filtering launch
- Add baseline documentation to PRD Introduction or Success Metrics section

---

### 4. Run History Features Could Be More Detailed

**Current:** US-007 shows list of runs with basic metadata

**Potential Enhancements (for future):**
- Run comparison (side-by-side diff of two runs)
- Re-run with same criteria on new CSV
- Export run summary to PDF/email
- Downloadable audit report

**Recommendation:** Document in Future Enhancements, don't add to MVP.

---

### 5. Progress Indicator Details Not Specified

**Current:** "Progress indicator shows filtering status" (FR-5)

**Questions:**
- What does progress indicator show? (Percentage? "Processing candidate 50 of 200"?)
- Is it real-time (WebSocket/SSE) or polling?
- Does it show which candidate is currently being evaluated?
- Can user cancel a running job?

**Recommendation:** Add technical specification for progress tracking:
- Backend updates progress in database (current_candidate, total_candidates)
- Frontend polls /api/runs/{run_id}/status every 2 seconds
- Display: "Processing: 50/200 candidates (25%)"
- Add "Cancel Run" button (nice-to-have, not critical for MVP)

---

## Recommendations Summary

### MUST DO Before Ralph Conversion

1. ✅ **Resolve Data Enrichment Decision**
   - Choose Option A (CSV-only MVP), B (enrichment-first), or C (hybrid)
   - Document chosen approach in PRD

2. ✅ **Break Large Stories Into Atomic Pieces**
   - US-001 → 4 stories (role mgmt, file upload, AI extraction, form UI)
   - US-002 → 2 stories (backend, UI)
   - US-004 → 3 stories (data model, UI, export)

3. ✅ **Define Database Schema**
   - Add US-000A: Design and implement database schema
   - Specify tables, columns, types, relationships

4. ✅ **Define Structured Form Fields**
   - Add US-000B: Design criteria configuration form schema
   - Specify field types, validation, labels

5. ✅ **Design AI Prompt Templates**
   - Add US-000C: Design and test AI prompts
   - Include example prompts for criteria extraction and evaluation

6. ✅ **Decide Open Questions**
   - Gating logic: OR (any param = reject)
   - Unsure handling: Human Review (conservative)
   - Nice-to-Haves: Remove from MVP or define clearly

### SHOULD DO Before Implementation

7. ⚠️ Add CSV validation story (US-008)
8. ⚠️ Define criteria approval UX flow
9. ⚠️ Add security requirements (input sanitization, audit logs)
10. ⚠️ Baseline current manual workflow time

### CAN DEFER to Implementation Phase

11. 📋 Criteria versioning UX details (handle during development)
12. 📋 Batch size limits (test and adjust based on performance)
13. 📋 Enrichment caching duration (Phase 2 concern)
14. 📋 Progress indicator technical details (can start simple, enhance later)

---

## Overall Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Structure** | ⭐⭐⭐⭐⭐ | Follows PRD template excellently |
| **Clarity** | ⭐⭐⭐⭐☆ | Goals and workflows clear; technical details vague |
| **Completeness** | ⭐⭐⭐☆☆ | Missing critical technical specifications |
| **Feasibility** | ⭐⭐☆☆☆ | Blocked by data enrichment decision and oversized stories |

### Final Recommendation

**DO NOT convert to Ralph JSON yet.**

**Action Plan:**
1. **Resolve data enrichment strategy** (Option A, B, or C)
2. **Break large stories into atomic pieces** (US-001 → 001A/B/C/D, etc.)
3. **Add foundational stories** (US-000A: schema, US-000B: form design, US-000C: AI prompts)
4. **Decide open questions** (gating logic, Unsure handling, Nice-to-Haves)
5. **Re-review PRD** after revisions
6. **Then convert to Ralph JSON** and begin implementation

**Timeline:**
- PRD revisions: 2-3 days
- Foundational design (schema, forms, prompts): 3-5 days
- Re-review and approval: 1 day
- **Total before Ralph:** ~1 week of preparation work

This preparation will save significant time during implementation by preventing blocker discoveries mid-development.

---

## Next Steps

**Immediate Actions:**

1. **Schedule PRD revision session** with Matt/Sam to:
   - Decide data enrichment approach
   - Review and approve story splits
   - Answer open questions

2. **Create foundational design stories:**
   - US-000A: Database schema design
   - US-000B: Criteria form schema design
   - US-000C: AI prompt template design

3. **Update PRD with decisions** and new stories

4. **Re-review** updated PRD (quick pass, should be straightforward after changes)

5. **Convert to Ralph JSON** using the ralph skill

6. **Run Ralph** on validated, atomic user stories

**Want help with any of these steps?** I can:
- Draft database schema proposals
- Design form field specifications
- Create AI prompt templates
- Split large stories into atomic pieces
- Update the PRD with revisions

---

**Review Completed By:** Henry (AI Assistant)  
**Contact:** Available via Telegram (@MattDS345)  
**Review Date:** 2026-01-26  
**PRD Version Reviewed:** 1.0 (Draft)
