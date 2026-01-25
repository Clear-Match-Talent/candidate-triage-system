# Ralph Loop - Autonomous Task Processing

**"I'm helping!" - Ralph Wiggum**

## Overview
The Ralph Loop is an autonomous task processing system based on the **Ralph Wiggum Loop** methodology. It transforms AI coding assistance from interactive chat into autonomous work-while-you-sleep mode.

## Core Principles

### 1. External Verification (The "Boss")
The AI never decides if it's finished. A verification script (`verify/NNN-verify.sh`) must return exit code 0.

### 2. Deterministic Context Management
Fresh context on each loop iteration. No "context rot" from accumulated mistakes.

### 3. Naive Persistence
If verification fails → loop again. No intelligence, just determination.

## Directory Structure

```
candidate-triage-system/
├── tasks/              # Task queue (*.md files)
│   ├── 001-fix-pending-action.md
│   ├── 002-fix-large-dataset.md
│   ├── completed/      # Successful tasks moved here
│   └── failed/         # Failed tasks moved here
├── specs/              # Success criteria
│   ├── 001-spec.md
│   └── 002-spec.md
├── verify/             # Verification scripts (exit 0 = success)
│   ├── 001-verify.sh
│   └── 002-verify.sh
├── plans/              # Implementation plans (Codex generates)
│   └── (auto-generated)
└── ralph.sh            # Main orchestrator loop
```

## Usage

### Run the Loop
```bash
./ralph.sh
```

This will:
1. Process all tasks in `tasks/` directory (sorted by filename)
2. For each task:
   - Run verification script
   - If fails: Call Codex to fix
   - Retry up to 5 times
   - Move to `completed/` or `failed/`

### Create a New Task

1. **Create task file** (`tasks/003-my-task.md`):
```markdown
# Task 003: Brief Description

## Problem
What's broken?

## Solution
What needs to happen?

## Verification Command
./verify/003-verify.sh
```

2. **Create spec** (`specs/003-spec.md`):
```markdown
# Specification: What Success Looks Like

## Exit Code 0 When:
1. Test X passes
2. Verification Y returns 0

## Test Coverage Required:
[Python/bash test code]
```

3. **Create verification script** (`verify/003-verify.sh`):
```bash
#!/bin/bash
set -e

# Run tests
pytest tests/test_my_feature.py

# Check code changes
grep -q "expected_fix" webapp/main.py

echo "✅ Verification passed!"
exit 0
```

4. **Make it executable**:
```bash
chmod +x verify/003-verify.sh
```

5. **Run Ralph Loop**:
```bash
./ralph.sh
```

## Current Tasks

### ✅ Task 001: Fix Pending Action Persistence
**Status:** COMPLETE  
**Fixed by:** Codex (cool-meadow session)  
**Verification:** `./verify/001-verify.sh`

### 🔄 Task 002: Fix Large Dataset DB Save
**Status:** IN PROGRESS  
**Working:** Codex (glow-canyon session)  
**Verification:** `./verify/002-verify.sh`

## Verification Best Practices

### Good Verification Scripts
- **Fast**: Run in < 30 seconds
- **Deterministic**: Same input = same output
- **Atomic**: Test one thing
- **Clear**: Output shows what passed/failed

### Example Structure
```bash
#!/bin/bash
set -e  # Exit on first failure

echo "🔍 Verifying feature X..."

# Test 1
echo "  ✓ Checking Y..."
[test command]

# Test 2
echo "  ✓ Running Z..."
[test command]

echo "✅ All checks passed!"
exit 0
```

## Integration with Codex

The Ralph Loop calls Codex CLI directly:
```bash
codex "$(cat tasks/NNN-task.md) \n\n$(cat specs/NNN-spec.md)"
```

Codex:
- Reads the task description
- Checks the spec for success criteria
- Makes changes
- Asks for approval (interactive)
- Commits changes

Then Ralph re-runs verification.

## Overnight Operation

To run Ralph overnight:
```bash
nohup ./ralph.sh > ralph.log 2>&1 &
```

Check progress:
```bash
tail -f ralph.log
```

Kill if needed:
```bash
pkill -f ralph.sh
```

## Configuration

Edit `ralph.sh` to change:
- `MAX_ATTEMPTS=5` - How many times to retry
- Codex command options
- Timeout behavior

## Tips

1. **Start small** - Test with 1-2 simple tasks first
2. **Write good specs** - Clear success criteria = better AI fixes
3. **Check `failed/`** - Review why tasks failed
4. **Incremental** - Add tasks one at a time
5. **Version control** - Commit before running Ralph

## Troubleshooting

### Ralph gets stuck
- Check which task is running: `ps aux | grep codex`
- Kill stuck Codex: `pkill codex`
- Check logs in task's plan file

### Verification always fails
- Run verification manually: `bash verify/NNN-verify.sh`
- Check exit code: `echo $?`
- Debug with `set -x` in verify script

### Codex makes wrong changes
- Improve task description in `tasks/NNN-*.md`
- Add more specific criteria in `specs/NNN-*.md`
- Add example code to spec

## Philosophy

> "The AI doesn't need to be smart. It just needs to keep trying until the tests pass."  
> — Geoffrey Huntley

The Ralph Loop embraces **naive persistence** over clever prompting. Write good tests, let the AI loop until they pass.
