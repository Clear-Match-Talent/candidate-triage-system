# Candidate Triage System

A candidate evaluation system that uses LLM-assisted reasoning to triage CSV exports against role specifications.

## Quick Start (Current — Native Python Runner)

This repo currently runs **natively** (from a terminal / Cursor / local machine). Clay is a **future integration**, not the current workflow.

### What You Need
1. A CSV export of candidates (SeekOut, LinkedIn Recruiter, Pin Wrangle, etc.)
2. Python 3.x
3. An Anthropic API key (`ANTHROPIC_API_KEY`)

### Setup

```bash
pip install -r requirements.txt
```

Set your API key:

- macOS/Linux:
```bash
export ANTHROPIC_API_KEY="..."
```

- Windows (PowerShell):
```powershell
$env:ANTHROPIC_API_KEY = "..."
```

### Run (end-to-end)

1) **Standardize/clean your input CSV(s)** into the required schema:

```bash
python -m ingestion.main path/to/export.csv --output-dir output/
```

This writes:
- `output/standardized_candidates.csv`
- `output/duplicates_report.csv` (if duplicates found)

2) **Evaluate candidates against the role spec**:

```bash
python evaluate_v3.py output/standardized_candidates.csv output/evaluated.csv
```

3) **Review outputs**
- `PROCEED` — all criteria met, ready for outreach
- `HUMAN_REVIEW` — at least one criterion unknown/ambiguous; a human must verify
- `DISMISS` — clearly fails at least one must-have

---

## File Structure

```
candidate-triage-system/
├── README.md
├── requirements.txt
├── ingestion/                          # CSV ingestion + standardization (multi-source)
├── evaluate_v3.py                      # Current evaluator runner (native)
├── evaluate_v2.py                      # Older iteration
├── evaluate.py                         # Oldest iteration
├── normalize_csv.py                    # Lightweight normalizer (legacy)
├── templates/
│   └── csv-template.csv                # Sample CSV with required columns
├── role-specs/
│   └── mandrell-senior-staff-engineer.yaml  # Example role specification
├── clay-templates/                     # FUTURE integration docs/templates
│   ├── evaluation-prompts.md
│   └── setup-guide.md
├── test-data/
└── output/                             # Local run outputs (standardized + evaluated)
```

---

## Role Specification

The system evaluates candidates against 3 must-have criteria defined in `role-specs/mandrell-senior-staff-engineer.yaml`:

1. **Location**: Within 50 miles of NYC
2. **Experience**: 5+ years as Senior+ IC Engineer
3. **Education**: Top-tier CS program OR equivalent signals (selective companies, open-source, competitions)

### Decision Logic

- **PROCEED**: All 3 criteria are MET
- **HUMAN_REVIEW**: At least 1 criterion is UNKNOWN (missing data)
- **DISMISS**: At least 1 criterion is NOT_MET (clear contradictory evidence)

**Critical Policy**: "Absence of evidence is NOT evidence of absence"
- Missing data → UNKNOWN (not NOT_MET)
- Only mark NOT_MET if there's clear contradictory evidence

---

## How It Works

### Current: Native Python (This Repo)

1. Ingest/standardize one or more CSV exports into a unified schema (`ingestion/`)
2. Run the evaluator script (currently `evaluate_v3.py`)
3. Write an output CSV with per-criterion JSON + an overall decision

Each criterion produces JSON like:
```json
{
  "status": "MET" | "NOT_MET" | "UNKNOWN",
  "reason": "Brief explanation",
  "evidence": "Quote from candidate data"
}
```

### Future: Clay (Possible Integration)

The `clay-templates/` folder contains templates and a setup guide for running the same evaluation logic inside Clay.

This is **not** the current workflow. It’s a future option if you want a UI-first process or faster operator onboarding.

---

## CSV Template Requirements

### Required Columns (Minimum)
```csv
linkedin_url,first_name,last_name,location,company_name,title
```

### Recommended Columns
```csv
experience_text,education_text,summary,skills
```

More data = better evaluation accuracy. Missing optional columns will result in more UNKNOWN/HUMAN_REVIEW decisions.

---

## Usage Examples

### Example 1: Basic Flow
1. Export 100 candidates from your sourcing tool
2. Import to Clay
3. Run evaluation (3-5 minutes)
4. Results:
   - 45 PROCEED (reach out immediately)
   - 30 HUMAN_REVIEW (check LinkedIn profiles)
   - 25 DISMISS (archive)

### Example 2: Handling HUMAN_REVIEW
1. Filter to `overall_decision = HUMAN_REVIEW`
2. Check `review_focus` column (shows which criteria are UNKNOWN)
3. For each candidate:
   - Visit LinkedIn profile
   - Manually verify missing information
   - Override decision or mark as PROCEED/DISMISS

---

## Customization

### For Different Roles
1. Copy `role-specs/mandrell-senior-staff-engineer.yaml`
2. Modify criteria (location, years of experience, education, etc.)
3. Update Clay prompts in `clay-templates/evaluation-prompts.md`
4. Create new Clay table with updated prompts

### For Different Criteria
Edit the YAML file's `must_haves` section:
- **id**: Internal identifier
- **label**: Human-readable name
- **evidence_fields**: Which CSV columns to examine
- **met_rules**: When to mark as MET
- **not_met_rules**: When to mark as NOT_MET
- **unknown_rules**: When to mark as UNKNOWN

---

## Troubleshooting

### All candidates marked UNKNOWN
- Check that CSV columns are properly mapped to prompt variables
- Verify your CSV actually contains data in those columns

### All candidates marked NOT_MET
- Prompts may be too strict
- Review the NOT_MET rules in `evaluation-prompts.md`
- Ensure UNKNOWN rules come before NOT_MET rules

### JSON parsing errors in Clay
- Verify prompt includes exact JSON format
- Set temperature to 0 for deterministic output
- Use Claude 3.5 Sonnet (not Haiku)

### Too expensive
- Test with 10 candidates first
- Filter CSV to only viable candidates before import
- Check your Clay plan's included AI credits

---

## Cost Notes

Current runs use the **Anthropic API directly** (via Python). Costs depend on:
- how many candidates you run
- how many criteria you evaluate
- which model you choose

If/when we move to Clay, Clay’s credit model will apply and may be cheaper for smaller batches.

---

## Support / Docs

Start here:
1. `ingestion/README.md` — how to ingest + standardize exports
2. `role-specs/mandrell-senior-staff-engineer.yaml` — criterion definitions
3. `templates/csv-template.csv` — example input format

Future Clay integration (not current):
- `clay-templates/setup-guide.md`
- `clay-templates/evaluation-prompts.md`

---

## Next Steps

1. **Test locally with sample data** (`templates/csv-template.csv`)
2. **Run locally on 10 real candidates** to validate decisions
3. **Scale to full list** (broad-net export → standardize → evaluate → human overrides)
4. **Use the operator runbook**: `RUNBOOK_OPERATOR.md`
5. **(Optional) Use the web UI** so operators don’t need a terminal: `webapp/README.md`
6. **Future**: consider Clay integration once the native flow is stable

---

## License

Internal use only.
