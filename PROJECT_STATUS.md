# Candidate Triage System - Project Status

**Last Updated:** 2026-01-25 11:22 UTC by Henry  
**Phase:** Development & Bug Fixes  
**Overall Status:** 🟢 All Tasks Complete - Ready for Testing

---

## 🎯 Current Focus

**Ready for User Testing**
- All known bugs fixed
- Services running and healthy
- Ready for Jason/Eric to test with real candidate data

---

## ✅ Completed Tasks

### Task 001: Fix Pending Action Persistence ✅
- **Completed:** 2026-01-25 10:32 UTC
- **Fixed by:** Codex (cool-meadow session)
- **What:** Added `save_run_to_db(st)` after setting pending_action
- **Verification:** `./verify/001-verify.sh` passes

### Task 002: Fix Large Dataset DB Save ✅
- **Completed:** 2026-01-25 10:32 UTC
- **Fixed by:** Codex (glow-canyon session)
- **What:** Added error logging and verified 1129-row dataset saves correctly
- **Verification:** `./verify/002-verify.sh` passes

### Task 003: Fix Data Assistant Chatbot Flow ✅
- **Completed:** 2026-01-25 11:22 UTC
- **Fixed by:** Henry (manual debug + test fix)
- **What:** Fixed ambiguous test prompt, verified pending_action save/load/execute cycle works correctly
- **Verification:** `./verify/003-verify.sh` passes

### Phase 1: Web UI & Pipeline ✅
- **Completed:** 2026-01-24
- **Features:**
  - Role creation interface
  - Multi-file CSV upload with drag & drop
  - Auto-detection of source (SeekOut/Pin Wrangle/LinkedIn)
  - Standardization & deduplication
  - Human review gate (spreadsheet view + approval)
  - AI evaluation pipeline integration
  - Results export (all buckets)

---

## 🔴 Known Issues

### Active
(None - all known bugs fixed!)

### Recently Fixed
- ✅ Data Assistant chatbot flow (Task 003)
- ✅ Pending action not persisting to DB (Task 001)
- ✅ Large datasets not saving to DB (Task 002)

---

## 🚀 What's Next

### Immediate (Priority 1)
1. ✅ ~~Setup GitHub Authentication~~ - **DONE** (SSH key configured, push working)
2. ✅ ~~Resolve Task 003~~ - **DONE** (test fixed, verification passing)
3. **User Testing** - Jason/Eric test with small real dataset (10-20 candidates)

### Testing Phase (Priority 2)
1. **Small Dataset Test** - Jason/Eric test with 10-20 real candidates
2. **Verify Export/Import Flow** - Upload → Standardize → Review → Approve → Evaluate → Export
3. **Document Any Issues** - Create new tasks for bugs found

### Phase 0 Calibration (Priority 3)
1. Run 40-60 real candidates through full pipeline
2. Label evaluation errors
3. Iterate on prompts/criteria
4. Get Matt/Sam approval to go live

### Production Hardening (Future)
- Systemd services for auto-restart
- Nginx reverse proxy
- Database persistence (SQLite → PostgreSQL)
- Error recovery & logging
- Domain + HTTPS

---

## 📦 Deployment Info

### Live Services
- **Frontend:** http://34.219.151.160:3000 (Next.js)
- **Backend:** http://34.219.151.160:8000 (FastAPI)
- **Server:** AWS EC2 (clawdbot-prod, us-west-2)
- **Process Management:** nohup (temporary, systemd planned)

### Quick Health Check
```bash
curl http://localhost:8000/      # Backend
curl http://localhost:3000/      # Frontend
ps aux | grep -E 'uvicorn|next'  # Processes
```

### Logs
```bash
tail -f /tmp/fastapi.log    # Backend
tail -f /tmp/nextjs.log     # Frontend
tail -f ralph.log           # Ralph loop
```

---

## 🗂️ Repository Structure

```
candidate-triage-system/
├── PROJECT_STATUS.md       # ← YOU ARE HERE
├── README.md               # User-facing documentation
├── DEPLOYMENT_STATUS.md    # Technical deployment details
├── SOP.md                  # Human-in-the-loop workflow
├── RUNBOOK_OPERATOR.md     # Jason/Eric step-by-step guide
├── tasks/                  # Ralph loop task queue
│   ├── 003-fix-data-assistant-chatbot-flow.md
│   ├── completed/          # ✅ Done
│   └── failed/             # ❌ Couldn't complete
├── specs/                  # Success criteria for tasks
├── verify/                 # Verification scripts (exit 0 = pass)
├── ralph.sh                # Autonomous task loop orchestrator
├── webapp/                 # FastAPI backend
├── frontend/               # Next.js UI
├── ingestion/              # CSV standardization pipeline
├── evaluate_v3.py          # AI evaluation logic
└── role-specs/             # Role criteria definitions
```

---

## 📝 Task Management Process

### Creating a New Task
1. Write `tasks/NNN-description.md` (problem + solution)
2. Write `specs/NNN-spec.md` (success criteria)
3. Write `verify/NNN-verify.sh` (automated verification, exit 0 = success)
4. Run `./ralph.sh` to process

### When Task Completes
1. Ralph moves task to `tasks/completed/`
2. Update this file (PROJECT_STATUS.md)
3. Commit + push to GitHub

### Manual Override
If Ralph can't complete a task:
- Fix it manually
- Move task to `tasks/completed/` or `tasks/failed/`
- Update PROJECT_STATUS.md
- Commit + push

---

## 🔗 Key Links

- **Master Tracker:** https://docs.google.com/spreadsheets/d/1i5gVkM47uXNSmKJbm_8foqzQs3ehoUiIqieisBnKOKk/
- **Intake Form:** https://docs.google.com/document/d/19Tannpa53szCIg79-WH1Rs8x2oBsH3bQEnNFUiZtfl0/
- **GitHub Repo:** https://github.com/Clear-Match-Talent/candidate-triage-system

---

## 💡 Decisions & Context

### Why Ralph Loop?
Autonomous task processing while humans sleep. AI loops until tests pass.

### Why Human Review Gate?
Matt/Sam requirement: Jason/Eric must see and approve standardized data before burning API credits on evaluation.

### Why Separate Specs from Tasks?
- Tasks describe the problem (for humans)
- Specs describe success (for verification scripts)
- Keeps both focused and readable

---

## 🎯 Success Metrics

Not yet defined. Consider tracking:
- Time from upload → results
- % of candidates that hit HUMAN_REVIEW
- Evaluation accuracy (Phase 0 calibration)
- Operator time savings

---

**End of Status** — Read this file first when picking back up!
