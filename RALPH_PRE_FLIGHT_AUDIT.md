# Ralph Pre-Flight Audit
**Date:** 2026-01-26  
**Project:** AI Candidate Filtering System  
**Auditor:** Henry (AI Assistant)

---

## Executive Summary

**Status:** 🟡 **NOT READY - 3 Critical Issues + 2 Warnings**

Ralph can NOT run yet. Must fix critical issues before launching.

---

## Critical Issues 🔴 (MUST FIX)

### 1. ❌ prd.json in Wrong Location

**Issue:** prd.json is at project root, but ralph.sh expects it in `scripts/ralph/`

**Current state:**
```
/home/ubuntu/clawd/candidate-triage-system/prd.json
```

**Expected by ralph.sh (line 37):**
```bash
PRD_FILE="$SCRIPT_DIR/prd.json"  # Looks in scripts/ralph/prd.json
```

**Impact:** Ralph will fail immediately with "prd.json not found"

**Fix:**
```bash
cd /home/ubuntu/clawd/candidate-triage-system
mv prd.json scripts/ralph/
```

---

### 2. ❌ Missing Repository Context in prd.json

**Issue:** prd.json doesn't reference the reference documentation (US-000A database schema file)

**Current state:**
- US-000A acceptance criteria says "Schema creation script runs without errors"
- But where is the actual SQL? In `tasks/us-000a-database-schema.md`
- prd.json doesn't tell Ralph where to find this

**Impact:** Ralph might create schema from scratch instead of using documented design

**Fix Option A:** Add to US-000A acceptance criteria:
```json
"acceptanceCriteria": [
  "Read database schema specification from tasks/us-000a-database-schema.md",
  "Implement SQL schema as documented",
  ...
]
```

**Fix Option B:** Add to AGENTS.md:
```markdown
## Database Schema

The complete database schema design is documented in:
- `tasks/us-000a-database-schema.md`

When implementing US-000A, use this as the authoritative source.
```

**Recommendation:** Do BOTH (belt and suspenders)

---

### 3. ❌ Vague "Typecheck passes" Without Test Setup

**Issue:** Every story says "Typecheck passes" but project has no typechecking configured

**Current state:**
- Python project (Flask)
- No `mypy` configuration
- No type hints in existing code
- Acceptance criteria says "Typecheck passes" but no way to verify

**Impact:** Ralph can't verify this acceptance criterion - will either skip it or fail

**Fix Option A:** Remove "Typecheck passes" from all stories (pragmatic)

**Fix Option B:** Add typecheck setup as US-000B:
```json
{
  "id": "US-000B",
  "title": "Setup Python Type Checking",
  "acceptanceCriteria": [
    "Install mypy as dev dependency",
    "Create mypy.ini configuration",
    "Add type hints to existing modules",
    "mypy runs without errors"
  ],
  "priority": 2  // Before other stories
}
```

**Recommendation:** Option A for MVP (remove typecheck requirement), add Option B for Phase 2

---

## Warnings ⚠️ (SHOULD FIX)

### 4. ⚠️ No Clear Testing Strategy for Backend Stories

**Issue:** Backend API stories don't specify how to test endpoints

**Example: US-001A**
```json
"acceptanceCriteria": [
  "API endpoint: POST /api/roles (create new role)",
  ...
  "Typecheck passes"
]
```

**Missing:** How does Ralph verify the endpoint works?
- Manual curl commands?
- Automated tests (pytest)?
- Just check code exists?

**Impact:** Ralph might implement endpoint but not verify it works, or waste time guessing how to test

**Fix:** Add testing guidance to AGENTS.md:
```markdown
## Testing Backend Endpoints

For all API endpoint stories:
1. Implement the endpoint
2. Start Flask dev server: `python webapp/main.py`
3. Test with curl:
   ```bash
   curl -X POST http://localhost:5000/api/roles \
     -H "Content-Type: application/json" \
     -d '{"name":"Test Role"}'
   ```
4. Verify response matches expected format
5. Check database for created record

OR (preferred for production):
1. Write pytest test in tests/test_api.py
2. Run: `pytest tests/test_api.py -v`
```

**Recommendation:** Add testing section to AGENTS.md now

---

### 5. ⚠️ Ambiguous Success for LinkedIn Enrichment Stories

**Issue:** US-005A says "Uses Claude browser tool to visit LinkedIn profile page" but doesn't specify HOW or what success looks like

**Example acceptance criteria:**
```
"Uses Claude browser tool to visit LinkedIn profile page"
```

**Questions Ralph will have:**
- What API/tool exactly? `claude browser` command?
- Does browser tool work in headless mode?
- How to handle LinkedIn login walls?
- What if browser tool isn't available?

**Impact:** Ralph might implement a mock/stub instead of real browser integration, or get stuck trying different approaches

**Fix:** Make criteria more specific:
```json
"acceptanceCriteria": [
  "Function uses @anthropic-ai/claude-code browser integration to fetch LinkedIn HTML",
  "If profile requires login, return error status (don't attempt login)",
  "Store raw HTML in enriched_candidates.raw_data column",
  "Return success: {html: string} or error: {error: 'not_found'|'rate_limit'|'requires_login'}",
  "Test with public LinkedIn profile URL and verify HTML contains profile data",
  "Typecheck passes"
]
```

**Recommendation:** Revise US-005A/B/C with specific implementation guidance

---

## Good State ✅ (Ready)

### 6. ✅ AGENTS.md Exists and Has Good Context

**File:** `/home/ubuntu/clawd/candidate-triage-system/AGENTS.md`

**Contents:**
- Project architecture (Python/Flask/SQLite/Claude)
- Tech stack and dependencies
- Conventions (code style, imports, naming)
- Common patterns (database access, CSV processing, LLM calls)
- Known gotchas (CSV encoding, SQLite limits, API rate limits)
- Troubleshooting guide

**Assessment:** Excellent foundation - Ralph will have good context

---

### 7. ✅ Story Ordering is Correct (Dependencies First)

**Sequence:**
1. US-000A: Database Schema (foundation)
2. US-001A-F: Role & Criteria Management (uses database)
3. US-005A-C: LinkedIn Enrichment (independent, can run parallel)
4. US-002A-C: Test Validation (uses criteria + enrichment)
5. US-003: Full Run (uses test validation)
6. US-004A-C: Results (uses run data)
7. US-006-007: Refinement & History (uses everything)

**Assessment:** Dependency order is logical - no story depends on future stories

---

### 8. ✅ Acceptance Criteria Are Mostly Verifiable

**Good examples:**
- "All 7 tables created: roles, criteria_versions, filter_runs..." (checkable)
- "API endpoint: POST /api/roles" (testable)
- "Roles list page displays all active roles" (verifiable in browser)

**Assessment:** Most criteria are concrete and checkable (except the typecheck issue)

---

### 9. ✅ Story Size Looks Reasonable

**Checked several stories:**
- US-000A: Just database schema (1-2 hours)
- US-001A: API CRUD endpoints (2-3 hours)
- US-001B: Simple UI (2-3 hours)
- US-005A: LinkedIn fetch (3-4 hours)

**Assessment:** Stories are atomic and fit within one iteration

---

### 10. ✅ Ralph Script Configuration is Valid

**File:** `scripts/ralph/ralph.sh`

**Key settings:**
- TOOL="amp" (default, but we'll override with `--tool claude`)
- MAX_ITERATIONS=10 (correct)
- Auto-initializes progress.txt
- Supports both AMP and Claude Code
- Has archiving logic for previous runs

**Assessment:** Script is properly configured

---

### 11. ✅ Claude Code is Installed and Authenticated

**Checked:**
```bash
$ claude --version
2.1.19 (Claude Code)

$ echo "test" | claude --print --dangerously-skip-permissions
[works]
```

**API Key:** Set in `~/.bashrc` and `~/.claude/settings.json`

**Assessment:** Claude Code is ready to use

---

### 12. ✅ PRD Documentation is Complete

**Files:**
- `tasks/prd-ai-filtering-v2.md` - Final approved PRD
- `tasks/us-000a-database-schema.md` - Complete database design
- All strategic decisions documented

**Assessment:** Excellent reference material for Ralph

---

## Missing Elements 📋

### 13. 📋 No progress.txt Yet

**Status:** Not a blocker - ralph.sh auto-creates it

**Expected location:** `scripts/ralph/progress.txt` (created on first run)

**Assessment:** OK - will be created automatically

---

### 14. 📋 No Git Branch Created Yet

**Current:** On `main` branch

**Expected:** Ralph creates `ralph/ai-filtering` branch (per prd.json branchName)

**Assessment:** OK - Ralph handles this

---

## Recommendations Summary

### MUST DO Before Running Ralph:

1. **Move prd.json**
   ```bash
   cd /home/ubuntu/clawd/candidate-triage-system
   mv prd.json scripts/ralph/
   git add scripts/ralph/prd.json
   git rm prd.json
   git commit -m "Move prd.json to scripts/ralph/ for Ralph execution"
   git push
   ```

2. **Link US-000A to schema documentation**
   
   Add to US-000A acceptanceCriteria in prd.json (after moving it):
   ```json
   "Read database schema from tasks/us-000a-database-schema.md before implementing",
   ```
   
   AND add to AGENTS.md:
   ```markdown
   ## Database Schema Reference
   
   The complete database schema design with all tables, indexes, constraints, and JSON formats is documented in:
   - `tasks/us-000a-database-schema.md`
   
   When implementing database stories (US-000A and any that modify schema), treat this document as the authoritative specification.
   ```

3. **Fix Typecheck Requirement**
   
   Option A (Quick Fix): Remove "Typecheck passes" from all 19 stories in prd.json
   
   Option B (Better): Add US-000B for typecheck setup, then keep "Typecheck passes" in later stories

   **Recommendation:** Option A for now

### SHOULD DO (Strongly Recommended):

4. **Add Testing Guidance to AGENTS.md**
   
   Add section on how to test backend endpoints (curl commands or pytest)

5. **Clarify LinkedIn Enrichment Implementation**
   
   Update US-005A/B/C with specific API calls and error handling

### NICE TO HAVE:

6. Update methodology/PROJECT_STRUCTURE.md to match actual Ralph pattern (prd.json in scripts/ralph/, not root)

---

## Pre-Flight Checklist

Before running `./scripts/ralph/ralph.sh --tool claude 10`:

- [ ] Move prd.json to scripts/ralph/
- [ ] Add database schema reference to US-000A in prd.json
- [ ] Add database schema guidance to AGENTS.md
- [ ] Remove or fix "Typecheck passes" in prd.json
- [ ] Add backend testing guidance to AGENTS.md
- [ ] Commit and push all changes
- [ ] Verify: `ls scripts/ralph/prd.json` (should exist)
- [ ] Verify: `cat scripts/ralph/prd.json | jq '.project'` (should return project name)
- [ ] Verify: Claude Code works: `echo "test" | claude --print --dangerously-skip-permissions`

**Then and only then:** Launch Ralph

---

## Expected Ralph Behavior After Fixes

1. Ralph reads `scripts/ralph/prd.json`
2. Finds US-000A (priority 1, passes=false)
3. Reads project AGENTS.md (gets context about Python/Flask/SQLite)
4. Reads tasks/us-000a-database-schema.md (gets schema design)
5. Creates `database/schema.sql` with all tables/indexes
6. Tests schema creation (runs SQL, checks tables exist)
7. Commits changes
8. Updates `scripts/ralph/prd.json` (sets US-000A passes=true)
9. Appends to `scripts/ralph/progress.txt` (logs what was done)
10. Moves to US-001A...

**Total time:** ~10 iterations × 5-10 min each = 1-2 hours
**Cost:** ~$30 (10 iterations × $3 each)

---

## Audit Conclusion

**Current Status:** 🔴 NOT READY

**After fixes:** 🟢 READY TO LAUNCH

**Estimated fix time:** 20-30 minutes

**Risk level after fixes:** LOW - stories are well-defined, dependencies correct, acceptance criteria mostly clear

---

**Next Step:** Address the 3 critical issues, then re-audit before launching.
