# Operator Runbook (Jason/Eric)

This is the **go-to place** to run the system end-to-end.

## What you (the operator) touch vs what AI/system touches

### You touch (human systems)
1. **Data sources** (SeekOut / Pin Wrangle / LinkedIn Recruiter / etc.) → export CSV(s)
2. **Role Intake Form (Google Doc)** → read the approved *Operational Sourcing Instructions*
3. **Local folder / repo workspace** (this repo) → drop CSVs + run the commands
4. **Google Sheet (per role)** → HUMAN_REVIEW overrides (final decision + reviewer + date + reason)

### System/AI touches
- Ingestion standardizes and dedupes CSVs
- Evaluator calls the LLM and produces criterion decisions + overall bucket

---

## Folder conventions (no thinking)

Inside this repo, every run goes in its own folder:

```
runs/
  2026-01-24_mandrel_founding-eng_nyc/
    input/          # raw exports from sources
    output/         # standardized + evaluated + buckets
    notes.txt       # optional run notes
```

---

## Prerequisites (one-time per operator machine)

1. Install **Python 3.11+**
2. From repo root:
   ```
   pip install -r requirements.txt
   ```
3. Set Anthropic key:
   - macOS/Linux:
     ```
     export ANTHROPIC_API_KEY="..."
     ```
   - Windows PowerShell:
     ```
     $env:ANTHROPIC_API_KEY = "..."
     ```

---

## Step-by-step: Run the conveyor belt (Operations)

### Step 1 — Broad-net sourcing export (Human)
**Goal:** Export ~500–1000 profiles with cheap gates applied.

Deliverable:
- One or more CSV export files (put them into `runs/<run>/input/`).

### Step 2 — Standardize + dedupe (System)
From repo root:

```powershell
python -m ingestion.main runs/<run>/input/*.csv --output-dir runs/<run>/output
```

Output:
- `runs/<run>/output/standardized_candidates.csv`
- `runs/<run>/output/duplicates_report.csv` (optional)

### Step 3 — (Calibration loop when needed) (Human + System)
If this is a new role or a changed spec, run a smaller cohort first:
- Create a *calibration cohort* CSV (40–60 candidates) in `runs/<run>/input/`
- Run Steps 2–4 on that cohort
- Review PROCEED/DISMISS/HUMAN_REVIEW buckets
- Log errors as: `FALSE_PROCEED`, `FALSE_DISMISS`, `SHOULD_BE_HUMAN_REVIEW`
- Iterate system changes until founders approve

### Step 4 — AI triage / evaluation (System)

```powershell
python evaluate_v3.py runs/<run>/output/standardized_candidates.csv runs/<run>/output/evaluated.csv
```

### Step 5 — Create bucket CSVs (System)

```powershell
python tools/bucket_results.py runs/<run>/output/evaluated.csv --outdir runs/<run>/output
```

Outputs:
- `proceed.csv`
- `human_review.csv`
- `dismiss.csv`

### Step 6 — HUMAN_REVIEW overrides (Human)
1. Create a Google Sheet: `[Client] — [Role] — HUMAN_REVIEW Overrides`
2. Paste/import `human_review.csv`
3. For each row, set:
   - `final_decision` (PROCEED/DISMISS)
   - `reviewer`
   - `review_date`
   - `override_reason` (1–2 lines)

No re-runs in the current version.

### Step 7 — Final handoff to outreach (Human)
Final outreach list =
- `proceed.csv` plus HUMAN_REVIEW rows where `final_decision=PROCEED`.

---

## Troubleshooting

- **Python not found**: install Python 3.x and ensure `python` is on PATH.
- **ANTHROPIC_API_KEY missing**: set it in your shell.
- **Too many HUMAN_REVIEW**: export richer fields (experience/education text) or widen upstream gates.
- **Bad buckets**: run calibration cohort loop before scaling.
