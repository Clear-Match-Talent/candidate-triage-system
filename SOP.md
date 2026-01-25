# SOP — Candidate Triage System (Native Runner, Human-in-the-Loop)

**Goal:** Convert raw candidate exports into a prioritized list (`PROCEED`, `HUMAN_REVIEW`, `DISMISS`) using the native Python system in this repo.

**Outputs you get:**
- `PROCEED` = ready for outreach
- `HUMAN_REVIEW` = missing/ambiguous info; human must verify
- `DISMISS` = clearly fails at least one must-have

**Critical policy (always):**
- *Absence of evidence is NOT evidence of absence.*
- Missing data → `UNKNOWN` → `HUMAN_REVIEW` (not `NOT_MET`).

---

## Who does what

- **Sourcer / Ops (Runner):** exports CSV(s), runs ingestion + evaluation, exports/share results.
- **Reviewer:** processes `HUMAN_REVIEW` candidates, verifies missing info (LinkedIn, etc.), decides proceed/dismiss.
- **Hiring lead (optional):** spot-checks decisions and calibrates criteria.

---

## Inputs (what humans must provide)

You start with one or more candidate CSV exports.

Minimum required fields (the system standardizes to these columns):
- `linkedin_url`
- `first_name`
- `last_name`
- `location`
- `company_name`
- `title`

Recommended (reduces HUMAN_REVIEW):
- `experience_text`
- `education_text`
- `summary`
- `skills`

---

## One-time setup (per machine)

1) Install dependencies:
```bash
pip install -r requirements.txt
```

2) Set your Anthropic API key:
- macOS/Linux:
```bash
export ANTHROPIC_API_KEY="..."
```
- Windows PowerShell:
```powershell
$env:ANTHROPIC_API_KEY = "..."
```

---

## SOP A — Run a batch (end-to-end)

### Step 1 — Export candidates
1. Export candidates from your sourcing tool (SeekOut / LinkedIn Recruiter / Pin Wrangle / etc.)
2. Save CSV(s) somewhere local.

### Step 2 — Standardize + dedupe (ingestion)
Run ingestion to convert any source format into the standard schema and dedupe by LinkedIn URL:

```bash
python -m ingestion.main path/to/export.csv --output-dir output/
```

Deliverables:
- `output/standardized_candidates.csv`
- `output/duplicates_report.csv` (if duplicates found)

### Step 3 — Evaluate candidates (LLM)
Run the evaluator (current runner: `evaluate_v3.py`):

```bash
python evaluate_v3.py output/standardized_candidates.csv output/evaluated.csv
```

Deliverable:
- `output/evaluated.csv`

### Step 4 — Quality check (must do before outreach)
Before acting on results:
1. Pick ~10 random rows across the file.
2. Check that:
   - obvious passes are `PROCEED`
   - obvious fails are `DISMISS`
   - missing/ambiguous cases are `HUMAN_REVIEW`
3. Verify the reasons/evidence look sane and not hallucinated.

If QC fails, stop and calibrate prompts/logic (see SOP C).

### Step 5 — Take action by decision bucket

#### PROCEED
Action:
- Add to outreach queue immediately.

#### HUMAN_REVIEW
Action (human-in-the-loop):
- Open LinkedIn profile and verify missing criterion.
- Decide:
  - **upgrade to PROCEED**, or
  - **move to DISMISS**, or
  - **leave as HUMAN_REVIEW** and request more info / a better export.

#### DISMISS
Action:
- Archive from active sourcing list.

### Step 6 — Save/share artifacts
Save:
- original export CSV
- `output/standardized_candidates.csv`
- `output/evaluated.csv`

---

## SOP B — Human review workflow (HUMAN_REVIEW)

1. Filter rows where `overall_decision == HUMAN_REVIEW`
2. For each candidate:
   - verify location, seniority/tenure, education/signal
   - document what you found (ideally in CRM notes)
3. Update decision:
   - PROCEED if confirmed
   - DISMISS if clearly fails

Tip: If >30–40% are HUMAN_REVIEW, the export likely lacks `experience_text`/`education_text`. Improve the export or enrich the CSV.

---

## SOP C — When results look wrong (calibration)

### Symptom: lots of errors / no output
- Confirm `ANTHROPIC_API_KEY` is set.
- Confirm `pip install -r requirements.txt` succeeded.

### Symptom: everything is DISMISS
- Criteria might be too strict.
- Ensure the logic follows the policy: missing data should become UNKNOWN/HUMAN_REVIEW.

### Symptom: everything is HUMAN_REVIEW
- Input data is too thin (missing experience/education text).
- Improve export fields.

---

## Future: Clay integration (not current)

We may later run this workflow inside Clay using templates in `clay-templates/`.
If/when we do, we’ll publish a Clay-specific SOP as the operator default.
