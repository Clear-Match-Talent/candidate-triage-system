# Clay Setup Guide (Future Integration) — Candidate Triage System

> Status: **Not the current workflow.**
> Today, this system runs natively via Python in this repo. This document is kept as a **future option** to run the same evaluation logic inside Clay.

This guide walks you through setting up the candidate triage system in Clay using the provided prompt templates.

---

## Prerequisites

- Clay account with AI credits
- Anthropic API access enabled in Clay
- CSV export from your sourcing tool (SeekOut, LinkedIn Recruiter, etc.)

---

## Step 1: Prepare Your CSV

### Option A: Use Your Existing Export

1. Export candidates from your sourcing tool (SeekOut, LinkedIn Recruiter, etc.)
2. Open the CSV and identify which columns map to our required fields
3. Rename columns to match our template OR note the mapping for later

**Required Columns** (must have these):
- `linkedin_url` (or Profile URL, LinkedIn, etc.)
- `first_name` (or First Name, FirstName)
- `last_name` (or Last Name, LastName)
- `location` (or Location, City)
- `company_name` (or Company, Current Company)
- `title` (or Title, Current Title)

**Optional But Recommended**:
- `experience_text` - Full work history narrative
- `education_text` - Schools attended
- `summary` - LinkedIn bio
- `skills` - Skills list

### Option B: Use Our Template

If you're manually entering candidates or testing:

1. Copy the template from `templates/csv-template.csv`
2. Add your candidate data
3. Save as a new CSV file

---

## Step 2: Import CSV to Clay

1. Log in to Clay
2. Click **"Create New Table"**
3. Select **"Import from CSV"**
4. Upload your CSV file
5. Clay will auto-detect columns - verify they look correct
6. Click **"Import"**

**Result**: You should see a table with your candidate data.

---

## Step 3: Create Criterion Columns (3 Total)

You'll create 3 "Use AI" columns - one for each criterion. Follow this process for EACH criterion.

### 3A: Location Criterion Column

1. Click **"Add Column"** → **"Enrich Data"** → **"Use AI"**
2. Configure the column:
   - **Column Name**: `criterion_location_status`
   - **Model**: Claude 3.5 Sonnet
   - **Temperature**: 0
   - **Max Tokens**: 500

3. In the prompt box, paste the **Location Prompt** from `evaluation-prompts.md`

4. Map the variable:
   - Find `{{location}}` in the prompt
   - Click the variable, select your location column from the dropdown

5. Click **"Run on first row"** to test
   - Verify you get valid JSON output like:
     ```json
     {
       "status": "MET",
       "reason": "Located in Brooklyn, NY which is within NYC metro",
       "evidence": "Brooklyn NY"
     }
     ```

6. If successful, click **"Run on all rows"**

**Troubleshooting**:
- If you see parsing errors, check that the JSON format is exactly correct
- If all candidates return UNKNOWN, check that your location column is properly mapped
- If costs seem high, test with 10 rows first

---

### 3B: Experience Criterion Column

1. Click **"Add Column"** → **"Enrich Data"** → **"Use AI"**
2. Configure:
   - **Column Name**: `criterion_experience_status`
   - **Model**: Claude 3.5 Sonnet
   - **Temperature**: 0
   - **Max Tokens**: 500

3. Paste the **Experience Prompt** from `evaluation-prompts.md`

4. Map the variables:
   - `{{title}}` → your title column
   - `{{experience_text}}` → your experience column
   - `{{tenure_dates}}` → your tenure column (if you have it)

   **Note**: If you don't have a `tenure_dates` column, you can either:
   - Leave it blank (Clay will pass empty string)
   - Remove that variable from the prompt
   - Use the `experience_text` column for both

5. Test on first row, then run on all

---

### 3C: Education/School Criterion Column

1. Click **"Add Column"** → **"Enrich Data"** → **"Use AI"**
2. Configure:
   - **Column Name**: `criterion_school_status`
   - **Model**: Claude 3.5 Sonnet
   - **Temperature**: 0
   - **Max Tokens**: 500

3. Paste the **School Prompt** from `evaluation-prompts.md`

4. Map the variables:
   - `{{education_text}}` → your education column
   - `{{experience_text}}` → your experience column
   - `{{company_name}}` → your company column

5. Test on first row, then run on all

---

## Step 4: Create Overall Decision Column

This column combines the 3 criteria into a final decision.

1. Click **"Add Column"** → **"Formula"**
2. Configure:
   - **Column Name**: `overall_decision`

3. Paste the **Overall Decision Formula** from `evaluation-prompts.md`:

```javascript
// Extract status from each criterion JSON
const location = {{criterion_location_status}};
const experience = {{criterion_experience_status}};
const school = {{criterion_school_status}};

// Parse JSON if needed (Clay may auto-parse)
const locationStatus = typeof location === 'string' ? JSON.parse(location).status : location.status;
const experienceStatus = typeof experience === 'string' ? JSON.parse(experience).status : experience.status;
const schoolStatus = typeof school === 'string' ? JSON.parse(school).status : school.status;

// Decision logic
const statuses = [locationStatus, experienceStatus, schoolStatus];

const hasNotMet = statuses.some(s => s === "NOT_MET");
const hasUnknown = statuses.some(s => s === "UNKNOWN");

if (hasNotMet) {
  return "DISMISS";
} else if (hasUnknown) {
  return "HUMAN_REVIEW";
} else {
  return "PROCEED";
}
```

4. Click the variable placeholders (`{{criterion_location_status}}`, etc.) and map them to your criterion columns

5. Click **"Run"** - should instantly calculate for all rows

---

## Step 5: (Optional) Create Helper Columns

### Review Focus Column

Shows which criteria need review (for HUMAN_REVIEW candidates).

1. Click **"Add Column"** → **"Formula"**
2. Name: `review_focus`
3. Paste the **Review Focus Formula** from `evaluation-prompts.md`
4. Map variables and run

### Dismiss Reason Column

Shows which criterion caused dismissal.

1. Click **"Add Column"** → **"Formula"**
2. Name: `dismiss_reason`
3. Paste the **Dismiss Reason Formula** from `evaluation-prompts.md`
4. Map variables and run

---

## Step 6: Review and Filter Results

### Filter by Decision

1. Click the filter icon on the `overall_decision` column
2. Filter to show only:
   - `PROCEED` - candidates who passed all criteria
   - `HUMAN_REVIEW` - candidates with missing data
   - `DISMISS` - candidates who failed at least one criterion

### Review HUMAN_REVIEW Cases

1. Filter to `overall_decision = HUMAN_REVIEW`
2. Look at the `review_focus` column to see which criteria are UNKNOWN
3. Manually review these candidates:
   - Check their LinkedIn profiles
   - Add missing information to the CSV
   - Re-run the evaluation OR manually override decision

### Sample Candidates for Quality Check

1. Randomly select 10 candidates
2. Read the criterion reasons and evidence
3. Verify decisions make sense
4. Adjust prompts if you see patterns of errors

---

## Step 7: Export Results

1. Click **"Export"** → **"Export to CSV"**
2. Select columns to include:
   - All original columns (linkedin_url, first_name, etc.)
   - `criterion_location_status`
   - `criterion_experience_status`
   - `criterion_school_status`
   - `overall_decision`
   - `review_focus` (if created)
   - `dismiss_reason` (if created)

3. Download the CSV
4. Open in Excel/Google Sheets for further review

---

## Step 8: Take Action on Results

### PROCEED Candidates
- These are your top priority outreach targets
- All criteria met with clear evidence
- Send personalized outreach immediately

### HUMAN_REVIEW Candidates
- Check the `review_focus` column
- Manually investigate missing information:
  - Visit LinkedIn profile
  - Google the candidate
  - Check company websites
- Make a manual decision or gather more data

### DISMISS Candidates
- Check the `dismiss_reason` column
- These candidates clearly don't meet requirements
- Archive or remove from active pipeline
- (Optional) Send a polite rejection if they've already applied

---

## Cost Estimation

**For 100 candidates with 3 criteria:**

- 100 candidates × 3 criteria = 300 API calls
- Each call: ~200 tokens input + ~100 tokens output
- Using Claude 3.5 Sonnet: ~$0.90 - $1.50 total

**Clay Pricing Note**:
- Most Clay plans include AI credits
- Check your plan's included credits
- Additional credits: typically $1 per 1,000 credits
- This workflow uses ~3 credits per candidate

---

## Troubleshooting

### Issue: "JSON parsing error"

**Cause**: LLM returned invalid JSON
**Fix**:
- Add more explicit JSON formatting instructions to prompt
- Use a code block in the prompt: ````json`
- Lower temperature to 0 (more deterministic)

### Issue: "All candidates marked as UNKNOWN"

**Cause**: Column mapping is wrong or data is missing
**Fix**:
- Verify variable mappings in the AI column settings
- Check that your CSV actually has data in those columns
- Test with a single row that definitely has data

### Issue: "All candidates marked as NOT_MET"

**Cause**: Prompts are too strict
**Fix**:
- Review the NOT_MET rules in the prompt
- Make sure UNKNOWN rules come before NOT_MET rules
- Emphasize "absence of evidence ≠ NOT_MET" in the prompt

### Issue: "Too expensive"

**Cause**: Running on too many candidates at once
**Fix**:
- Test with 10-20 candidates first
- Filter your CSV to only viable candidates before import
- Consider using Claude Haiku for simple criteria (location)

---

## Tips for Success

1. **Start small**: Test with 10 candidates before running on full list
2. **Check JSON parsing**: Make sure criterion columns return valid JSON
3. **Review edge cases**: Manually check candidates with UNKNOWN status
4. **Iterate on prompts**: If you see patterns of errors, refine the prompts
5. **Use filters**: Clay's filter features make it easy to segment results
6. **Save as template**: Once it works, save the Clay table as a template for future roles

---

## Next Steps After Clay Validation

Once you've successfully evaluated 50-100 candidates in Clay:

1. **Assess manual effort**: How much time did setup + review take?
2. **Check accuracy**: What % of decisions felt correct?
3. **Consider automation**: If processing 100+ candidates/week, consider Phase 2 (standalone tool)

**When to build Phase 2**:
- Processing 500+ candidates per batch
- Running evaluations weekly
- Managing multiple open roles simultaneously
- Need CI/CD integration or scheduled runs

---

## Support

If you encounter issues:

1. Check the `evaluation-prompts.md` file for exact prompt text
2. Review the `role-specs/mandrell-senior-staff-engineer.yaml` for criterion definitions
3. Test with the sample data in `templates/csv-template.csv`
4. Verify your Clay AI credits and API access

---

## Checklist

- [ ] CSV imported to Clay
- [ ] `criterion_location_status` column created and tested
- [ ] `criterion_experience_status` column created and tested
- [ ] `criterion_school_status` column created and tested
- [ ] `overall_decision` formula column created
- [ ] (Optional) `review_focus` column created
- [ ] (Optional) `dismiss_reason` column created
- [ ] Results reviewed for quality
- [ ] CSV exported with all columns
- [ ] Decisions make sense on manual spot-check

Once all boxes are checked, you're ready to process candidates at scale!
