# Clay Evaluation Prompt Templates

These prompts are designed to be used in Clay's "Use AI" enrichment columns. Each criterion gets its own column.

---

## Criterion 1: Location (NYC Metro)

### Clay Column Setup
- **Column Name**: `criterion_location_status`
- **Column Type**: Use AI
- **Input Variables**: `{{location}}`
- **Model**: Claude 3.5 Sonnet
- **Temperature**: 0
- **Max Tokens**: 500

### Prompt Template

```
You are evaluating whether a candidate meets the location requirement for a role.

CRITERION: Within 50 miles of NYC

CANDIDATE LOCATION: {{location}}

MET RULES (mark as MET if any apply):
- Location indicates within 50 miles of NYC (Manhattan, Brooklyn, Queens, Bronx, Staten Island, Jersey City, Hoboken, Weehawken, Fort Lee, etc.)
- Location mentions NYC boroughs or immediate suburbs

NOT_MET RULES (mark as NOT_MET if any apply):
- Location explicitly outside NYC metro area (e.g., San Francisco, Boston, Seattle, Austin, Remote-only)
- Location is in a different US city or international

UNKNOWN RULES (mark as UNKNOWN if any apply):
- Location field is missing or empty
- Location is too vague (e.g., "United States", "East Coast", "Flexible")

CRITICAL POLICY:
- Absence of evidence = UNKNOWN (not NOT_MET)
- Only mark NOT_MET if there is clear contradictory evidence
- Err on the side of UNKNOWN for ambiguous cases

Respond ONLY in this exact JSON format:
{
  "status": "MET" | "NOT_MET" | "UNKNOWN",
  "reason": "Brief 1-2 sentence explanation",
  "evidence": "Direct quote from location field or 'N/A'"
}
```

---

## Criterion 2: Experience (5+ Years Senior+ IC)

### Clay Column Setup
- **Column Name**: `criterion_experience_status`
- **Column Type**: Use AI
- **Input Variables**: `{{experience_text}}`, `{{title}}`, `{{tenure_dates}}`
- **Model**: Claude 3.5 Sonnet
- **Temperature**: 0
- **Max Tokens**: 500

### Prompt Template

```
You are evaluating whether a candidate meets the experience requirement for a role.

CRITERION: 5+ years as Senior+ IC (Individual Contributor) Engineer

CANDIDATE DATA:
- Current Title: {{title}}
- Experience: {{experience_text}}
- Tenure Dates: {{tenure_dates}}

MET RULES (mark as MET if any apply):
- Current or recent title includes "Senior", "Staff", "Principal", or "Lead" Engineer (not Manager)
- Experience text shows 5+ years in senior IC roles
- Clear progression to senior levels (e.g., Engineer → Senior → Staff)

NOT_MET RULES (mark as NOT_MET if any apply):
- All roles are Junior, Mid-level, or Intern
- Primary experience is as Engineering Manager (not IC)
- Less than 5 years total experience
- Only has 1-2 years of experience even if title says "Senior"

UNKNOWN RULES (mark as UNKNOWN if any apply):
- Experience field is missing or only shows current role without tenure
- Titles are vague (e.g., "Developer", "Programmer") without seniority indicators
- Cannot determine tenure or progression from provided data

CRITICAL POLICY:
- Absence of evidence = UNKNOWN (not NOT_MET)
- Only mark NOT_MET if there is clear contradictory evidence
- Focus on IC (Individual Contributor) roles, not management

Respond ONLY in this exact JSON format:
{
  "status": "MET" | "NOT_MET" | "UNKNOWN",
  "reason": "Brief 1-2 sentence explanation",
  "evidence": "Key evidence excerpt or 'N/A'"
}
```

---

## Criterion 3: Education (Top-tier CS or Equivalent Signal)

### Clay Column Setup
- **Column Name**: `criterion_school_status`
- **Column Type**: Use AI
- **Input Variables**: `{{education_text}}`, `{{experience_text}}`, `{{company_name}}`
- **Model**: Claude 3.5 Sonnet
- **Temperature**: 0
- **Max Tokens**: 500

### Prompt Template

```
You are evaluating whether a candidate meets the education/signal requirement for a role.

CRITERION: Top-tier CS program OR equivalent compensating signals

CANDIDATE DATA:
- Education: {{education_text}}
- Experience: {{experience_text}}
- Current Company: {{company_name}}

MET RULES (mark as MET if any apply):
- Attended MIT, Stanford, CMU, UC Berkeley, Caltech, Princeton, Harvard, Cornell, UIUC, UWashington for CS/Engineering
- Attended top international CS programs (e.g., Waterloo, ETH Zurich, IIT, Tsinghua, Oxford, Cambridge)
- No degree BUT worked at highly selective companies (e.g., Jane Street, Citadel, OpenAI, DeepMind, Google Brain, Meta FAIR)
- Strong open-source contributions mentioned or competitive programming background (e.g., ICPC finalist, top Kaggle contributor)

NOT_MET RULES (mark as NOT_MET if any apply):
- Education is from non-target school AND no compensating signals (selective company, OSS, competitions)
- Bootcamp background without subsequent work at top-tier company
- Only has experience at non-selective companies with non-target education

UNKNOWN RULES (mark as UNKNOWN if any apply):
- Education field is missing or empty
- School name is present but cannot determine if it's a top-tier program
- Self-taught with insufficient work history to assess
- Cannot verify if company experience is sufficiently selective

CRITICAL POLICY:
- Absence of evidence = UNKNOWN (not NOT_MET)
- Only mark NOT_MET if there is clear evidence of non-target education AND no compensating signals
- Compensating signals (selective companies, OSS, competitions) can substitute for education

TOP-TIER SCHOOLS (US):
MIT, Stanford, CMU, UC Berkeley, Caltech, Princeton, Harvard, Cornell, UIUC, University of Washington, Georgia Tech, UT Austin

TOP-TIER SCHOOLS (International):
Waterloo, ETH Zurich, IIT (India), Tsinghua, Peking University, Oxford, Cambridge, Imperial College

HIGHLY SELECTIVE COMPANIES:
FAANG research labs (Google Brain, Meta FAIR, Apple ML), OpenAI, Anthropic, DeepMind, Jane Street, Citadel, Two Sigma, HRT, Stripe (early), Databricks (early)

Respond ONLY in this exact JSON format:
{
  "status": "MET" | "NOT_MET" | "UNKNOWN",
  "reason": "Brief 1-2 sentence explanation",
  "evidence": "School name or company name or 'N/A'"
}
```

---

## Formula Column: Overall Decision

After creating the three criterion columns above, create a **Formula** column to calculate the overall decision.

### Clay Column Setup
- **Column Name**: `overall_decision`
- **Column Type**: Formula
- **Formula Code**:

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

---

## Additional Helper Columns (Optional)

### Review Focus Column
Shows which criteria need human review (only for HUMAN_REVIEW candidates).

**Column Name**: `review_focus`
**Column Type**: Formula

```javascript
const location = {{criterion_location_status}};
const experience = {{criterion_experience_status}};
const school = {{criterion_school_status}};

const locationStatus = typeof location === 'string' ? JSON.parse(location).status : location.status;
const experienceStatus = typeof experience === 'string' ? JSON.parse(experience).status : experience.status;
const schoolStatus = typeof school === 'string' ? JSON.parse(school).status : school.status;

const unknowns = [];

if (locationStatus === "UNKNOWN") unknowns.push("location_nyc");
if (experienceStatus === "UNKNOWN") unknowns.push("experience_senior_plus");
if (schoolStatus === "UNKNOWN") unknowns.push("school_top_tier");

return unknowns.join("; ");
```

### Dismiss Reason Column
Shows which criterion caused dismissal.

**Column Name**: `dismiss_reason`
**Column Type**: Formula

```javascript
const location = {{criterion_location_status}};
const experience = {{criterion_experience_status}};
const school = {{criterion_school_status}};

const locationStatus = typeof location === 'string' ? JSON.parse(location).status : location.status;
const experienceStatus = typeof experience === 'string' ? JSON.parse(experience).status : experience.status;
const schoolStatus = typeof school === 'string' ? JSON.parse(school).status : school.status;

if (locationStatus === "NOT_MET") return "location_nyc";
if (experienceStatus === "NOT_MET") return "experience_senior_plus";
if (schoolStatus === "NOT_MET") return "school_top_tier";

return "";
```

---

## Tips for Using These Prompts

1. **Test with 5 candidates first** - Verify JSON parsing works correctly
2. **Check for parsing errors** - If Clay shows errors, the JSON format may need adjustment
3. **Monitor costs** - Each row = 1 API call per criterion (3 calls total)
4. **Temperature = 0** - Ensures deterministic, consistent results
5. **Use Sonnet for accuracy** - Haiku may be too aggressive on NOT_MET
6. **Review UNKNOWN cases** - These are candidates worth manually checking

---

## Expected Output Format

Each criterion column will contain JSON like:

```json
{
  "status": "MET",
  "reason": "Located in Brooklyn, NY which is within NYC metro area",
  "evidence": "Brooklyn NY"
}
```

The overall_decision column will show: `PROCEED`, `HUMAN_REVIEW`, or `DISMISS`.
