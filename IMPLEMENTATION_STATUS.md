# Implementation Status

## Current: Native Python Runner ✅ WORKING

The system currently runs natively via Python scripts in this repo (ingestion + evaluation). Clay is a future integration option.

### Core Components

#### 1) CSV Ingestion + Standardization ✅
**Folder**: `ingestion/`
- Ingests candidate CSVs from multiple sources
- Standardizes to the required schema
- De-dupes by LinkedIn URL
- Outputs `output/standardized_candidates.csv`

#### 2) Evaluator Runner ✅
**File**: `evaluate_v3.py` (current)
- Reads standardized candidates CSV
- Calls Anthropic (requires `ANTHROPIC_API_KEY`)
- Writes evaluated output CSV with per-criterion JSON + an overall decision

#### 3) CSV Template ✅
**File**: `templates/csv-template.csv`
- Example of the standardized schema

#### 4) Role Specification ✅
**File**: `role-specs/mandrell-senior-staff-engineer.yaml`
- Example must-haves + policy

#### 5) Clay Templates (Future) 💤
**Folder**: `clay-templates/`
- Prompt templates + setup guide for a future Clay-based operator flow

#### 6) README ✅
**File**: `README.md`
- Updated to reflect native run as current; Clay as future

---

## What You Can Do Right Now

### Immediate Next Steps (10 minutes)

1. **Export candidates from your sourcing tool** (SeekOut, LinkedIn Recruiter, etc.)
2. **Run ingestion** to standardize the export:
   ```bash
   pip install -r requirements.txt
   python -m ingestion.main path/to/export.csv --output-dir output/
   ```
3. **Run evaluation** on the standardized CSV:
   ```bash
   python evaluate_v3.py output/standardized_candidates.csv output/evaluated.csv
   ```
4. Open `output/evaluated.csv` and sanity-check outcomes + reasons.

---

## Validation Checklist

Before processing your full candidate list, verify:

- [ ] CSV template reviewed and understood
- [ ] Role spec matches your actual requirements
- [ ] Clay account has sufficient AI credits
- [ ] Test run with 10 candidates completed successfully
- [ ] JSON parsing works (no errors)
- [ ] Decisions make sense on spot-check
- [ ] Understand PROCEED vs HUMAN_REVIEW vs DISMISS logic

---

## Future Option: Clay Operator Flow ⏸️ NOT CURRENT

Clay templates exist in `clay-templates/`, but we are not running this workflow in Clay today.

If/when we switch to Clay, we’ll update the docs and SOP to treat Clay as the default operator surface.

### When to Start Phase 2

Consider building the standalone tool when:
- Processing 500+ candidates per batch regularly
- Managing multiple open roles simultaneously
- Clay approach feels too manual/slow
- Need CI/CD integration or scheduled runs

### Phase 2 Architecture (Planned)

```
src/
├── index.ts                    # CLI entry point
├── config/types.ts             # Interfaces
├── parsers/
│   ├── csv-parser.ts           # CSV reading with column normalization
│   ├── role-spec-parser.ts     # YAML parsing
│   └── csv-writer.ts           # Output generation
├── evaluators/
│   ├── criterion-evaluator.ts  # Per-criterion evaluation
│   ├── llm-evaluator.ts        # Claude API integration
│   └── decision-engine.ts      # Decision logic
└── utils/
    ├── evidence-extractor.ts   # Field extraction
    └── logger.ts               # Progress logging
```

**Estimated effort**: 8-12 hours for MVP, +3 hours for optimizations

---

## Current Recommendation

**Start with Phase 1** (Clay templates) because:
1. ✅ Zero additional cost (uses existing Clay subscription)
2. ✅ Faster to deploy (30 min vs 8-12 hours)
3. ✅ Validates evaluation logic before building custom tool
4. ✅ Familiar interface (Clay UI)
5. ✅ All files ready to use immediately

**Graduate to Phase 2** only if:
- Clay approach validated and working
- Processing volume justifies automation
- Need programmatic access or CI/CD integration

---

## Testing Plan

### Test Scenario 1: Happy Path
- **Input**: 10 candidates with complete data (all required + optional fields)
- **Expected**: Mix of PROCEED, HUMAN_REVIEW, DISMISS based on actual fit
- **Validation**: Decisions match manual review

### Test Scenario 2: Missing Data
- **Input**: 5 candidates with only required fields (no experience_text, education_text)
- **Expected**: Mostly HUMAN_REVIEW due to UNKNOWN criteria
- **Validation**: System correctly identifies data gaps

### Test Scenario 3: Edge Cases
- **Input**: 5 candidates with ambiguous data (e.g., "Remote", vague titles)
- **Expected**: UNKNOWN status for ambiguous criteria
- **Validation**: System errs toward HUMAN_REVIEW, not NOT_MET

---

## Known Limitations (Phase 1)

1. **Manual setup per role**: Need to recreate prompts for each new role
2. **No batch API optimization**: Each candidate = 3 separate API calls
3. **Formula limitations**: Clay formulas less elegant than code
4. **Export/import cycles**: Need to manually export results CSV

These are acceptable tradeoffs for MVP validation. Phase 2 addresses all of these.

---

## Success Metrics

### Phase 1 Success Criteria
- [ ] 10 test candidates evaluated successfully
- [ ] Decision distribution is reasonable (not all DISMISS or all PROCEED)
- [ ] Reason snippets are clear and actionable
- [ ] Total setup time < 30 minutes
- [ ] Zero runtime errors
- [ ] Output CSV validates correctly

### Quality Metrics
- [ ] Manual spot-check of 10 PROCEED candidates: 80%+ feel correct
- [ ] Manual spot-check of 10 DISMISS candidates: 90%+ feel correct
- [ ] HUMAN_REVIEW candidates have clear review_focus identified

---

## Questions to Answer During Testing

1. **Accuracy**: Do decisions match your manual judgment?
2. **Data completeness**: What % of candidates lack sufficient data?
3. **Review burden**: How many HUMAN_REVIEW cases need manual work?
4. **Time savings**: How much faster than manual review?
5. **Cost**: What's the actual Clay credit consumption?

Record answers to inform whether Phase 2 is needed.

---

## Timeline

### Today (Phase 1)
- ✅ Create all template files (DONE)
- ⏭️ Export candidate CSV from sourcing tool
- ⏭️ Test with 10 candidates in Clay
- ⏭️ Validate output quality

### This Week (Phase 1 Validation)
- ⏭️ Process full candidate list (50-100 candidates)
- ⏭️ Review PROCEED candidates for outreach
- ⏭️ Manually triage HUMAN_REVIEW candidates
- ⏭️ Measure time savings and accuracy

### Next Week (Decision Point)
- ⏭️ Evaluate if Phase 2 is needed
- ⏭️ If yes, start TypeScript tool development
- ⏭️ If no, continue with Clay approach for future roles

---

## Ready to Start?

All files are created and ready to use. Your next action:

1. Open `clay-templates/setup-guide.md`
2. Follow Step 1 (Prepare Your CSV)
3. Continue through Step 8 (Take Action on Results)

Good luck! 🚀
