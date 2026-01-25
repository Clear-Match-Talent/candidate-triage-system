"""
Standard schema definition for candidate data.

Defines the required and optional columns for standardized candidate CSV output.
"""

# Required columns (must be present in output)
REQUIRED_COLUMNS = [
    "linkedin_url",
    "first_name",
    "last_name",
    "location",
    "company_name",
    "title",
]

# Optional columns (nice to have, can be empty)
OPTIONAL_COLUMNS = [
    "experience_text",
    "education_text",
    "summary",
    "skills",
]

# All standard columns in order
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

# Column descriptions for LLM context
COLUMN_DESCRIPTIONS = {
    "linkedin_url": "LinkedIn profile URL (e.g., https://linkedin.com/in/username)",
    "first_name": "Candidate's first name",
    "last_name": "Candidate's last name",
    "location": "Geographic location (city, state, country format preferred)",
    "company_name": "Current or most recent company name",
    "title": "Current or most recent job title",
    "experience_text": "Text description of work experience, including roles and companies",
    "education_text": "Text description of education, including degree, major, school, and graduation year",
    "summary": "Professional summary or bio text",
    "skills": "Comma-separated list of skills or technologies",
}

# Data type expectations
COLUMN_TYPES = {
    "linkedin_url": "url",
    "first_name": "string",
    "last_name": "string",
    "location": "string",
    "company_name": "string",
    "title": "string",
    "experience_text": "text",
    "education_text": "text",
    "summary": "text",
    "skills": "string",
}

def get_schema_description():
    """Get a formatted description of the standard schema for LLM context."""
    required_desc = "\n".join([f"- {col}: {COLUMN_DESCRIPTIONS[col]}" for col in REQUIRED_COLUMNS])
    optional_desc = "\n".join([f"- {col}: {COLUMN_DESCRIPTIONS[col]}" for col in OPTIONAL_COLUMNS])
    
    return f"""Standard Candidate Schema:

REQUIRED COLUMNS (must be present):
{required_desc}

OPTIONAL COLUMNS (can be empty):
{optional_desc}
"""
