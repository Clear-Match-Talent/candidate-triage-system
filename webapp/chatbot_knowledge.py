"""Domain knowledge for recruiting data chat assistant."""

RECRUITING_FIELD_GLOSSARY = {
    "linkedin_url": {
        "description": "Candidate's LinkedIn profile URL.",
        "common_issues": [
            "Missing or empty",
            "Invalid format (not a linkedin.com/in URL)",
            "Company page or search URL instead of profile",
            "Duplicate URLs across candidates",
        ],
        "importance": "critical",
        "validation": {
            "rule": "Must start with https://linkedin.com/in/ or https://www.linkedin.com/in/",
            "pattern": "^https?://(www\\.)?linkedin\\.com/in/",
        },
    },
    "first_name": {
        "description": "Candidate's first/given name.",
        "common_issues": [
            "Missing despite full name present",
            "Initials only",
            "Lower/upper casing inconsistencies",
        ],
        "importance": "high",
    },
    "last_name": {
        "description": "Candidate's last/family name.",
        "common_issues": [
            "Missing despite full name present",
            "Suffixes included (Jr., III) in last name field",
            "Lower/upper casing inconsistencies",
        ],
        "importance": "high",
    },
    "full_name": {
        "description": "Candidate's full name (if provided by source).",
        "common_issues": [
            "Single token only",
            "All caps or all lowercase",
            "Includes non-name tokens (e.g., job title)",
        ],
        "importance": "medium",
        "validation": {
            "rule": "Prefer at least two name parts when available.",
        },
    },
    "email": {
        "description": "Primary candidate email address.",
        "common_issues": [
            "Missing contact info",
            "Invalid format",
            "Company group inboxes (info@, careers@)",
        ],
        "importance": "high",
        "validation": {
            "rule": "Must be a valid email format (local@domain.tld).",
            "pattern": "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$",
        },
    },
    "phone": {
        "description": "Candidate phone number.",
        "common_issues": [
            "Missing or placeholder values",
            "Mixed formatting",
            "Too short to be valid",
        ],
        "importance": "medium",
        "validation": {
            "rule": "Should contain at least 7 digits.",
        },
    },
    "location": {
        "description": "Candidate location (city, state/region, country).",
        "common_issues": [
            "Missing",
            "Only country provided",
            "Non-standard abbreviations",
        ],
        "importance": "high",
    },
    "company_name": {
        "description": "Current or most recent employer.",
        "common_issues": [
            "Out of date",
            "Freelance/self-employed placeholders",
            "Company and title swapped",
        ],
        "importance": "high",
    },
    "current_company": {
        "description": "Alias for current employer (often same as company_name).",
        "common_issues": [
            "Out of date",
            "Missing while experience_text exists",
        ],
        "importance": "high",
    },
    "title": {
        "description": "Current or most recent job title.",
        "common_issues": [
            "Missing",
            "Inflated or generic titles (e.g., 'Consultant')",
            "Company and title swapped",
        ],
        "importance": "high",
    },
    "current_title": {
        "description": "Alias for current title (often same as title).",
        "common_issues": [
            "Missing while experience_text exists",
            "Non-standard capitalization",
        ],
        "importance": "high",
    },
    "experience_text": {
        "description": "Raw text of work experience (roles, companies, dates).",
        "common_issues": [
            "Empty despite LinkedIn URL",
            "Mixed with education content",
            "Duplicate or repeated roles",
        ],
        "importance": "critical",
    },
    "education_text": {
        "description": "Raw text of education history (schools, degrees, dates).",
        "common_issues": [
            "Missing even when LinkedIn URL exists",
            "Mixed with experience content",
            "Incomplete degree/school info",
        ],
        "importance": "medium",
    },
    "summary": {
        "description": "Professional summary or bio text.",
        "common_issues": [
            "Too long or unstructured",
            "Contains unrelated marketing copy",
        ],
        "importance": "low",
    },
    "skills": {
        "description": "List of skills/technologies (comma-separated preferred).",
        "common_issues": [
            "Unstructured blob text",
            "Duplicates or inconsistent casing",
            "Missing separators",
        ],
        "importance": "medium",
        "validation": {
            "rule": "Prefer comma-separated list; avoid sentences.",
        },
    },
}

COMMON_DATA_QUALITY_ISSUES = [
    {
        "issue": "LinkedIn URL without experience_text",
        "impact": "Limits ability to evaluate seniority and role history.",
        "detection_hint": "linkedin_url present AND experience_text empty",
    },
    {
        "issue": "Invalid email format",
        "impact": "Breaks outreach and deduplication.",
        "detection_hint": "email does not match basic local@domain.tld pattern",
    },
    {
        "issue": "Missing contact info",
        "impact": "Cannot contact candidates; reduces pipeline quality.",
        "detection_hint": "email and linkedin_url both missing",
    },
    {
        "issue": "Duplicate LinkedIn profiles",
        "impact": "Duplicate candidates; noisy analytics.",
        "detection_hint": "linkedin_url appears more than once",
    },
    {
        "issue": "Company/title swapped",
        "impact": "Misleads recruiter about current role.",
        "detection_hint": "company_name looks like job title or title looks like company",
    },
]

SUCCESSFUL_TRANSFORMATIONS = [
    {
        "user_intent": "Clear experience-related fields",
        "code": "df['experience_text'] = ''; df['company_name'] = ''; df['title'] = ''",
        "explanation": "Resets experience fields so they can be re-enriched cleanly.",
    },
    {
        "user_intent": "Copy field A to field B",
        "code": "df['target_field'] = df['source_field']",
        "explanation": "Copies values from one column to another for all candidates.",
    },
    {
        "user_intent": "Fill missing LinkedIn URLs with a placeholder",
        "code": "df.loc[df['linkedin_url'] == '', 'linkedin_url'] = 'MISSING'",
        "explanation": "Flags missing LinkedIn URLs for follow-up or filtering.",
    },
    {
        "user_intent": "Normalize skills to lowercase",
        "code": "df['skills'] = df['skills'].str.lower()",
        "explanation": "Standardizes skills for consistent searching.",
    },
    {
        "user_intent": "Split full_name into first_name/last_name",
        "code": "parts = df['full_name'].str.split(' ', n=1, expand=True); df['first_name'] = parts[0]; df['last_name'] = parts[1].fillna('')",
        "explanation": "Creates structured name fields from full_name.",
    },
    {
        "user_intent": "Clear empty strings to None for analysis",
        "code": "df.replace({'': None}, inplace=True)",
        "explanation": "Makes missing values consistent for quality checks.",
    },
]
