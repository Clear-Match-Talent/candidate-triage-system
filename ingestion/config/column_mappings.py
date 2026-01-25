"""
Known column mappings for different CSV source formats.

Maps common column name variations to standard column names.
"""

KNOWN_MAPPINGS = {
    "seekout": {
        "linkedin_url": ["LinkedIn URL", "linkedin_url", "LinkedIn", "linkedin", "profile_url"],
        "first_name": ["First Name", "first_name", "First", "fname", "given_name"],
        "last_name": ["Last Name", "last_name", "Last", "lname", "surname", "family_name"],
        "location": ["Location", "location", "City", "city", "Location (City)", "address"],
        "company_name": ["Company", "company_name", "Current Company", "Employer", "company"],
        "title": ["Title", "title", "Job Title", "Position", "role", "current_title"],
        "experience_text": ["Experience", "experience_text", "Work History", "Employment History", "background"],
        "education_text": ["Education", "education_text", "Education History", "School", "degrees"],
        "summary": ["Summary", "summary", "Bio", "About", "description", "overview"],
        "skills": ["Skills", "skills", "Technologies", "tech_skills", "competencies"],
    },
    "pin_wrangle": {
        "linkedin_url": ["LinkedIn URL", "linkedin_url", "LinkedIn", "linkedin", "profile_url"],
        "first_name": ["First Name", "first_name", "First", "fname"],
        "last_name": ["Last Name", "last_name", "Last", "lname", "surname"],
        "location": ["Location", "location", "City", "city", "Location (City)"],
        "company_name": ["Company", "company_name", "Current Company", "Employer", "company"],
        "title": ["Title", "title", "Job Title", "Position", "role"],
        "experience_text": ["Experience", "experience_text", "Work History", "Employment History"],
        "education_text": ["Education", "education_text", "Education History", "School"],
        "summary": ["Summary", "summary", "Bio", "About", "description"],
        "skills": ["Skills", "skills", "Technologies", "tech_skills"],
    },
    "clay": {
        "linkedin_url": ["linkedin_url", "LinkedIn URL", "linkedin", "profile_url"],
        "first_name": ["first_name", "First Name", "First", "fname"],
        "last_name": ["last_name", "Last Name", "Last", "lname", "surname"],
        "location": ["location", "Location", "City", "city"],
        "company_name": ["company_name", "Company", "Current Company", "Employer"],
        "title": ["title", "Title", "Job Title", "Position", "role"],
        "experience_text": ["experience_text", "Experience", "Work History"],
        "education_text": ["education_text", "Education", "Education History"],
        "summary": ["summary", "Summary", "Bio", "About"],
        "skills": ["skills", "Skills", "Technologies"],
    },
    "recruitcrm": {
        # Based on existing normalize_csv.py
        "linkedin_url": ["linkedin_url"],
        "first_name": ["first_name"],
        "last_name": ["last_name"],
        "location": ["location"],
        "company_name": ["company_name"],
        "title": ["title"],
        "experience_text": ["experience_text"],
        "education_text": ["candidate_educations_degree", "candidate_education_major", "candidate_education_school", "candidate_education_schoolEndDat"],
        "summary": ["summary"],
        "skills": ["skills"],
    },
    "wrangle": {
        # Wrangle has simple, clean column names
        "linkedin_url": ["Linkedin", "LinkedIn"],
        "first_name": ["Name"],  # Full name, will need to split
        "last_name": ["Name"],  # Full name, will need to split - same column, handled in extraction
        "location": ["Location"],
        "company_name": ["Company"],
        "title": ["Title"],
        "experience_text": [],  # Not available
        "education_text": [],  # Not available
        "summary": ["Notes"],  # Notes field could serve as summary
        "skills": [],  # Not available
    },
}

def find_mapping(source_column: str, source_type: str = None) -> str:
    """
    Find the standard column name for a given source column.
    
    Args:
        source_column: The column name from the source CSV
        source_type: Optional source type (seekout, pin_wrangle, etc.)
    
    Returns:
        Standard column name if found, None otherwise
    """
    source_column_lower = source_column.lower().strip()
    
    # If source type is known, check that first
    if source_type and source_type.lower() in KNOWN_MAPPINGS:
        mappings = KNOWN_MAPPINGS[source_type.lower()]
        for standard_col, variations in mappings.items():
            if source_column_lower in [v.lower() for v in variations]:
                return standard_col
    
    # Otherwise, search all known mappings
    for mappings in KNOWN_MAPPINGS.values():
        for standard_col, variations in mappings.items():
            if source_column_lower in [v.lower() for v in variations]:
                return standard_col
    
    # Check if it's already a standard column name
    if source_column_lower in [col.lower() for col in KNOWN_MAPPINGS["clay"].keys()]:
        return source_column_lower
    
    return None

def get_source_patterns():
    """Get column name patterns that help identify source types."""
    return {
        "seekout": ["SeekOut", "seekout", "SO_", "_candidateName_dc5u3_2", "_candidateDisplayName_dc5u3_17"],
        "pin": ["candidate.linkedin", "candidate.firstName", "candidate.experiences.0"],
        "wrangle": ["Name", "Title", "Company", "Linkedin"],  # Simple column names
        "pin_wrangle": ["Pin Wrangle", "pin_wrangle", "PW_", "pwrangle"],
        "clay": ["clay", "Clay"],
        "recruitcrm": ["candidate_", "Candidate_", "recruitcrm"],
    }
