# Candidate Triage System

A candidate evaluation system that uses LLM-assisted reasoning to triage CSV exports against role specifications.

## Quick Start (Phase 1 - Clay Templates)

**Fastest path to get started** - leverages your existing Clay subscription.

### What You Need
1. A CSV export of candidates (from RecruitCRM, SeekOut, LinkedIn Recruiter, etc.)
2. Clay account with AI credits
3. 30 minutes for initial setup

### Setup Steps

1. **Prepare your CSV** using the template in `templates/csv-template.csv`
   - Required columns: `linkedin_url`, `first_name`, `last_name`, `location`, `company_name`, `title`
   - Optional: `experience_text`, `education_text`, `summary`, `skills`

2. **Follow the Clay setup guide**: `clay-templates/setup-guide.md`
   - Import CSV to Clay
   - Create 3 AI enrichment columns using prompts from `clay-templates/evaluation-prompts.md`
   - Create decision formula column
   - Export results

3. **Review outputs**
   - `PROCEED` - All criteria met, ready for outreach
   - `HUMAN_REVIEW` - Missing data, needs manual check
   - `DISMISS` - Failed at least one criterion

### Cost
- **Clay**: ~$0 marginal cost (included in subscription)
- For 100 candidates: ~$1-2 in AI credits

---

## File Structure

```
candidate-triage-system/
├── README.md                           # This file
├── templates/
│   └── csv-template.csv                # Sample CSV with required columns
├── role-specs/
│   └── mandrell-senior-staff-engineer.yaml  # Role specification
├── clay-templates/
│   ├── evaluation-prompts.md           # AI prompts for Clay columns
│   └── setup-guide.md                  # Step-by-step Clay setup
├── test-data/                          # (empty - add your test CSVs here)
└── output/                             # (empty - exported results go here)
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

### Phase 1: Clay (Current Implementation)

1. Import CSV to Clay table
2. Create AI enrichment columns (one per criterion)
3. Each column evaluates one criterion and returns JSON:
   ```json
   {
     "status": "MET" | "NOT_MET" | "UNKNOWN",
     "reason": "Brief explanation",
     "evidence": "Quote from candidate data"
   }
   ```
4. Formula column combines results into overall decision
5. Export results CSV

**Pros**: Fast setup, uses existing subscription, familiar UI
**Cons**: Manual setup per role, slower for large batches

### Phase 2: Standalone Tool (Future)

Build a TypeScript CLI tool for automation at scale.

**When to build Phase 2**:
- Processing 500+ candidates per batch regularly
- Managing multiple open roles
- Need CI/CD integration

See the original plan document for Phase 2 architecture.

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
1. Export 100 candidates from RecruitCRM
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

## Cost Comparison

| Batch Size | Clay Cost | Direct API (est.) |
|------------|-----------|-------------------|
| 100 candidates | ~$1-2 | ~$2-3 |
| 500 candidates | ~$5-10 | ~$12-15 |
| 1000 candidates | ~$10-20 | ~$25-30 |

Clay is cost-effective for batches under 500. Consider Phase 2 for larger scale.

---

## Support

Questions or issues? Check:
1. `clay-templates/setup-guide.md` - detailed Clay instructions
2. `clay-templates/evaluation-prompts.md` - exact prompts and formulas
3. `role-specs/mandrell-senior-staff-engineer.yaml` - criterion definitions
4. `templates/csv-template.csv` - example data format

---

## Next Steps

1. **Test with sample data**: Use `templates/csv-template.csv` to verify setup
2. **Run on 10 real candidates**: Validate decisions make sense
3. **Scale to full list**: Process your entire candidate pool
4. **Review and iterate**: Adjust prompts based on results
5. **Consider Phase 2**: If processing 500+ candidates/week, build standalone tool

---

## License

Internal use only.
