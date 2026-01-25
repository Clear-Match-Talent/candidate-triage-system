# Development Workflow - Zero Fuzziness

## 🎯 The Golden Rule
**PROJECT_STATUS.md is the single source of truth.**  
Always read it first. Always update it after changes. Always commit it.

---

## 📋 Starting a New Session

### 1. Run the Pickup Script
```bash
cd ~/clawd/candidate-triage-system
./pickup.sh
```

This will:
- Pull latest from GitHub
- Show recent commits
- Display PROJECT_STATUS.md
- Check Ralph loop status
- Check service health

### 2. Read PROJECT_STATUS.md
Focus on:
- **Current Focus** — What's in progress?
- **What's Next** — What should I work on?
- **Known Issues** — What's broken?

### 3. Sync Your Mental Model
- Check git log if anything looks stale
- Read the current task file if one is active
- Check ralph.log if Ralph was running

---

## 🔧 Working on Tasks

### Option 1: Ralph Loop (Autonomous)
For bug fixes and automated tasks:

```bash
./ralph.sh                  # Run in foreground
# OR
nohup ./ralph.sh > ralph.log 2>&1 &  # Run in background
```

Ralph will:
- Process all tasks in `tasks/*.md`
- Call Codex to fix
- Verify with `verify/NNN-verify.sh`
- Auto-commit when tasks complete
- Move tasks to `completed/` or `failed/`

### Option 2: Manual Work
For new features or complex changes:

```bash
# Make your changes
# Test manually
# When done:
./commit-status.sh "Brief description of change"
```

---

## ✅ Completing Work

### After Any Meaningful Change:
1. **Update PROJECT_STATUS.md** (move items between sections, update "Last Updated", add context)
2. **Commit + Push:**
   ```bash
   ./commit-status.sh "Task NNN: Description - COMPLETE"
   ```

Ralph loop does this automatically for task completions.

---

## 🔄 Handoff Between Sessions

When you finish a session:
1. Update PROJECT_STATUS.md with:
   - What you completed
   - What's in progress
   - What's blocked (if anything)
   - Next steps
2. Commit + push
3. That's it. Next session reads PROJECT_STATUS.md and knows exactly where to start.

---

## 🚨 If Things Look Fuzzy

If you're unsure what's happening:
```bash
./pickup.sh        # Get current state
git log -10        # Recent changes
git status         # Uncommitted changes
tail -50 ralph.log # Ralph loop activity
```

Then read PROJECT_STATUS.md. It should tell you everything you need to know.

---

## 📝 Task Management

### Creating a New Task
1. Write `tasks/NNN-description.md`
2. Write `specs/NNN-spec.md`
3. Write `verify/NNN-verify.sh` (chmod +x)
4. Update PROJECT_STATUS.md (add to "What's Next")
5. Commit + push
6. Run `./ralph.sh` or work manually

### Reviewing Completed Tasks
```bash
ls tasks/completed/    # Successfully finished
ls tasks/failed/       # Couldn't complete (needs manual review)
```

---

## 🎯 One-Command Pickup

```bash
cd ~/clawd/candidate-triage-system && ./pickup.sh
```

Everything you need to know will be displayed.

---

## 🔗 Related Files

- **PROJECT_STATUS.md** — Single source of truth (read this first!)
- **GITHUB_AUTH_SETUP.md** — Setup git push authentication
- **RALPH_README.md** — How the Ralph loop works
- **README.md** — User-facing project documentation
- **DEPLOYMENT_STATUS.md** — Technical deployment details
