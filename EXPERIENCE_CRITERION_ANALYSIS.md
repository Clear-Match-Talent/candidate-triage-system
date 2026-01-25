# Experience Criterion Analysis

## Problem: All 34 Candidates Returned UNKNOWN

### Current Criterion Requirements

**What it's checking**: "5+ years as Senior+ IC Engineer"

**What it needs**:
- `experience_text` - Full work history narrative showing:
  - Previous companies and roles
  - Tenure at each role (dates)
  - Career progression (Junior → Mid → Senior → Staff)

**Why it's failing**:
- Your CSV has `experience_text` = EMPTY for all candidates
- System correctly marks as UNKNOWN (can't verify without data)

---

## What Data You DO Have

From your CSV export (`test 1.csv`):

✅ **Available**:
- `title` - Current job title (e.g., "Staff Software Engineer", "Senior Software Engineer")
- `Candidate_start_date` - When they started at current company (e.g., "8/1/2022")
- `company_name` - Current company (e.g., "Modal Labs")

❌ **Missing**:
- Previous companies/roles
- Total years of experience
- Career progression history

---

## Sample Data Analysis

Let me show you what we can infer from the data you DO have:

| Name | Title | Company | Start Date | Tenure at Current | Inference |
|------|-------|---------|------------|-------------------|-----------|
| Bradley Whitlock | **Staff** Software Engineer | Abnormal Security | 9/1/2024 | 4 months | **Staff title = likely 5+ YOE** (must have prior experience to be Staff) |
| Amy Resnik | **Senior** Software Engineer | Codecademy | 9/1/2022 | 2.3 years | **Senior title = likely 3-5+ YOE** |
| Jeremy Wei | Software Engineer | Sei Labs | 10/1/2023 | 1.2 years | **No senior title** = unclear, need history |
| Rob Martorano | Software Engineer | Pomelo Care | 11/1/2021 | 3.2 years | **3+ years tenure** but no senior title = mid-level? |
| Jonathon Belotti | **Member Of Technical Staff** | Modal Labs | 8/1/2022 | 2.4 years | **MTS** can mean senior-level at some companies |

---

## Proposed Solution: Revised Experience Criterion

Instead of requiring full work history, we can make **educated inferences** based on:

1. **Title seniority** (Senior/Staff/Principal/Lead = strong signal)
2. **Current tenure** (3+ years at current company = experience signal)
3. **Company selectivity** (Stripe Staff Engineer > Small Startup Staff Engineer)

### Revised Logic

**MET** (High confidence they have 5+ years):
- Title contains "Staff", "Principal", or "Distinguished"
- Title contains "Senior" AND (tenure at current company > 2 years OR company is top-tier)
- Title is "Lead Engineer" or "Architect" (not Lead Manager)

**NOT_MET** (Clear junior/mid-level):
- Title contains "Junior", "Intern", "Associate"
- Title is "Software Engineer" AND tenure < 2 years AND company is not top-tier
- Recent graduate (graduated < 3 years ago) without senior title

**UNKNOWN** (Need manual review):
- Title is "Software Engineer" without seniority indicator
- Title has "Engineer II" or "Engineer III" (level systems vary by company)
- Ambiguous titles like "Member of Technical Staff" (varies by company)

---

## Comparison: Old vs New Criterion

### Old Criterion (Current)
```
Requires: experience_text with 5+ years at Senior+ roles
Result: 34/34 = UNKNOWN (no data available)
```

### New Criterion (Proposed)
```
Uses: title + tenure at current company
Expected Result:
- ~8-10 MET (Staff/Principal/Senior with tenure)
- ~5-8 NOT_MET (clearly junior)
- ~16-20 UNKNOWN (ambiguous cases)
```

---

## Example Evaluations with New Criterion

**Bradley Whitlock** - Staff Software Engineer @ Abnormal Security (9/2024)
- Title: "Staff" = strong seniority signal
- Inference: Must have 5+ years to reach Staff level
- **NEW RESULT: MET** ✅

**Amy Resnik** - Senior Software Engineer @ Codecademy (9/2022)
- Title: "Senior"
- Tenure: 2.3 years
- **NEW RESULT: MET** ✅ (Senior + decent tenure)

**Jeremy Wei** - Software Engineer @ Sei Labs (10/2023)
- Title: No seniority indicator
- Tenure: 1.2 years
- School: CMU (top-tier, graduated 2019 = 6 YOE likely)
- **NEW RESULT: MET** ✅ (CMU grad 2019 = likely 6 years experience)

**Rob Martorano** - Software Engineer @ Pomelo Care (11/2021)
- Title: No seniority indicator
- Tenure: 3.2 years
- School: Duke 2018 (graduated 7 years ago)
- **NEW RESULT: MET** ✅ (Graduated 2018 = likely 7 years experience)

**Nadia Alamgir** - Software Engineer @ Lunchbox (5/2020)
- Title: No seniority indicator
- Education: Bootcamp (2022)
- **NEW RESULT: NOT_MET** ❌ (Bootcamp grad 2022 = only ~3 years experience)

---

## Recommendation

**Use a hybrid approach**:

1. **Title-based heuristics** (primary signal)
   - Staff/Principal/Distinguished → Likely 7+ years → MET
   - Senior → Likely 4-7 years → MET if tenure > 2 years
   - No title + recent grad → NOT_MET

2. **Tenure calculation** (secondary signal)
   - Calculate years since graduation
   - Calculate years at current company
   - Combine with title to make inference

3. **Company tier** (tiebreaker)
   - Top-tier company + Senior title → Higher confidence MET
   - Unknown startup + generic title → UNKNOWN

---

## Would You Like Me To:

**Option 1**: Update the evaluation script to use the new criterion
- Uses title keywords + tenure + graduation date
- Will give you ~10 PROCEED instead of 0

**Option 2**: Keep current criterion but add "fallback logic"
- Try full criterion first
- If UNKNOWN due to missing data, fall back to title-based inference

**Option 3**: Create two versions
- "Strict" mode (current - requires full history)
- "Inferred" mode (new - uses available data)

Which would you prefer?
