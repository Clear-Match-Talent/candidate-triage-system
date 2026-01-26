# ✅ READY TO LAUNCH - Ralph AI Filtering System

**Date:** 2026-01-26  
**Status:** 🟢 ALL SYSTEMS GO

---

## Pre-Flight Audit: PASSED ✅

All critical issues identified and resolved:

1. ✅ **prd.json moved to scripts/ralph/**
2. ✅ **Typecheck requirements removed** (no mypy configured)
3. ✅ **US-000A references schema doc** (tasks/us-000a-database-schema.md)
4. ✅ **AGENTS.md has database schema reference**
5. ✅ **AGENTS.md has backend API testing guidance**
6. ✅ **US-005A/B/C LinkedIn enrichment clarified** (detailed implementation steps)
7. ✅ **Ralph script validates ANTHROPIC_API_KEY**
8. ✅ **Ralph script sources ~/.bashrc for environment variables**

---

## What Ralph Will Build

**Project:** AI Candidate Filtering System  
**Stories:** 19 atomic user stories  
**Estimated time:** 1-2 hours (10 iterations)  
**Estimated cost:** ~$30 ($3/iteration)

### Story Execution Order:

1. **US-000A:** Database Schema (7 tables, indexes, constraints) - FOUNDATION
2. **US-001A-F:** Role & Criteria Management (backend APIs + UI forms)
3. **US-005A-C:** LinkedIn Enrichment (fetch, extract, cache)
4. **US-002A-C:** Test Validation (50-candidate testing workflow)
5. **US-003:** Full/Subset Run (batch processing with progress)
6. **US-004A-C:** Results Display & Export (UI + CSV export)
7. **US-006-007:** Refinement & History (iterate on criteria)

---

## Launch Command

```bash
cd /home/ubuntu/clawd/candidate-triage-system
./scripts/ralph/ralph.sh --tool claude 10
```

**What happens:**
1. Ralph reads `scripts/ralph/prd.json`
2. Picks first incomplete story (US-000A, priority 1)
3. Reads `AGENTS.md` for project context
4. Reads `tasks/us-000a-database-schema.md` for schema design
5. Implements database schema
6. Tests against acceptance criteria
7. Commits if successful
8. Updates `prd.json` (sets passes=true)
9. Logs progress to `scripts/ralph/progress.txt`
10. Repeats for next story...

**Ralph runs on branch:** `ralph/ai-filtering` (created automatically)

---

## Monitoring Progress

### Check Current Story
```bash
cd /home/ubuntu/clawd/candidate-triage-system
cat scripts/ralph/prd.json | jq '.userStories[] | select(.passes==false) | {id, title}' | head -20
```

### View Progress Log
```bash
cat scripts/ralph/progress.txt
```

### Check Git Commits
```bash
git log --oneline --author="ralph" -10
```

### See Which Stories Are Complete
```bash
cat scripts/ralph/prd.json | jq '.userStories[] | {id, title, passes}'
```

---

## Ralph Will Stop When:

1. **All 19 stories pass** - Outputs `<promise>COMPLETE</promise>`
2. **Reaches 10 iterations** - Check progress.txt for status
3. **Encounters fatal error** - Check logs for details

---

## If Ralph Gets Stuck:

### Story Fails Multiple Times
1. Check what it's trying to do: `cat scripts/ralph/progress.txt`
2. Look at the attempted commits: `git log ralph/ai-filtering`
3. If acceptance criteria are unclear, update `scripts/ralph/prd.json` and restart

### Out of Context / Token Limit
- Story might be too large
- Split story into 2 smaller stories in `prd.json`
- Restart Ralph

### API Rate Limits
- Wait 60 seconds
- Restart Ralph (it will resume from last incomplete story)

---

## After Ralph Completes:

### 1. Review the Code
```bash
git checkout ralph/ai-filtering
git diff main..ralph/ai-filtering
```

### 2. Test the Feature
```bash
# Start the app
python webapp/main.py

# Open browser
http://localhost:5000

# Test key workflows:
- Create a role
- Upload documents (JD, intake, calibration)
- Configure criteria
- Run test validation (50 candidates)
- Review results
```

### 3. Merge to Main
```bash
git checkout main
git merge ralph/ai-filtering
git push origin main
```

### 4. Update Documentation
- Add any discovered patterns to `AGENTS.md`
- Document deployment steps if needed
- Update README with new feature

---

## Success Criteria

**✅ Ralph succeeded if:**
- All 19 stories marked as `passes: true` in `prd.json`
- Database schema exists with all 7 tables
- Flask routes respond correctly
- Web UI is functional (pages load, forms work)
- LinkedIn enrichment fetches and parses profiles
- Test validation workflow completes
- Results display and export work

**⚠️ Manual work still needed:**
- CSS/styling refinement
- Error message polish
- Edge case testing with real candidate CSVs
- Production deployment setup

---

## Configuration Files Reference

**Location:** `/home/ubuntu/clawd/candidate-triage-system`

```
├── AGENTS.md                          ← Project context for Ralph
├── scripts/ralph/
│   ├── ralph.sh                       ← Main loop script
│   ├── prd.json                       ← 19 user stories
│   ├── progress.txt                   ← Created during run
│   ├── CLAUDE.md                      ← System prompt for Claude
│   └── .last-branch                   ← Created during run
├── tasks/
│   ├── prd-ai-filtering-v2.md         ← Full PRD
│   └── us-000a-database-schema.md     ← Database spec
├── RALPH_PRE_FLIGHT_AUDIT.md          ← Pre-flight audit results
└── READY_TO_LAUNCH.md                 ← This file
```

---

## Environment Check

Before launching, verify:

```bash
# 1. Claude Code works
echo "test" | claude --print --dangerously-skip-permissions
# Should output: "Hello! I'm ready..."

# 2. API key is set
echo $ANTHROPIC_API_KEY | head -c 20
# Should output: sk-ant-api03-xZy95Hf

# 3. prd.json exists
ls -lh scripts/ralph/prd.json
# Should show: ~19K file

# 4. Git is clean
git status
# Should show: "On branch main, nothing to commit" (or only build artifacts)
```

---

## Estimated Timeline

**Total:** 1-2 hours (assuming smooth execution)

- US-000A (Database): 5-10 min
- US-001A-F (Role/Criteria): 30-45 min
- US-005A-C (LinkedIn): 15-20 min
- US-002A-C (Test): 15-20 min
- US-003 (Full Run): 5-10 min
- US-004A-C (Results): 15-20 min
- US-006-007 (Refine/History): 10-15 min

**If you're going to bed:** Perfect time to launch Ralph!

---

## Launch Checklist

- [x] All critical issues resolved
- [x] prd.json in correct location
- [x] AGENTS.md updated with schema reference and testing guidance
- [x] LinkedIn enrichment stories clarified
- [x] API key configured
- [x] Ralph script has environment validation
- [x] Git committed and pushed
- [ ] **LAUNCH RALPH** ← You are here

---

## READY TO LAUNCH 🚀

**Command:**
```bash
cd /home/ubuntu/clawd/candidate-triage-system && ./scripts/ralph/ralph.sh --tool claude 10
```

**Wake up to:** A working AI candidate filtering system with 4-bucket categorization, LinkedIn enrichment, test validation, and results export.

Good luck! 🍀
