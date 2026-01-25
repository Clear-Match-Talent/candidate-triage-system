"""
Data Extraction Agent

Extracts and normalizes data from source CSV rows using column mappings.
"""

import re
from typing import Dict, List, Optional, Tuple
from ..config.standard_schema import ALL_COLUMNS


def split_full_name(full_name: str) -> tuple[str, str]:
    """
    Split a full name into first and last name.
    
    Args:
        full_name: Full name string
    
    Returns:
        Tuple of (first_name, last_name)
    """
    if not full_name or not full_name.strip():
        return ('', '')
    
    parts = full_name.strip().split()
    if len(parts) == 0:
        return ('', '')
    elif len(parts) == 1:
        return (parts[0], '')
    else:
        # First name is first part, last name is everything else
        return (parts[0], ' '.join(parts[1:]))


def parse_title_at_company(text: str) -> Tuple[str, str]:
    """
    Parse "Title at Company" format into title and company.
    
    Args:
        text: String like "Senior Engineer at Google" or "Engineer, Google"
    
    Returns:
        Tuple of (title, company)
    """
    if not text or not text.strip():
        return ('', '')
    
    text = text.strip()
    
    # Pattern: "Title at Company"
    match = re.search(r'^(.+?)\s+at\s+(.+)$', text, re.IGNORECASE)
    if match:
        return (match.group(1).strip(), match.group(2).strip())
    
    # Pattern: "Title, Company"
    match = re.search(r'^(.+?),\s+(.+)$', text)
    if match:
        return (match.group(1).strip(), match.group(2).strip())
    
    # If no pattern matches, assume it's just the title
    return (text, '')


def extract_location_from_text(text: str) -> str:
    """
    Extract location from text that may contain other information.
    
    Args:
        text: Text that may contain location
    
    Returns:
        Location string if found, empty string otherwise
    """
    if not text:
        return ''
    
    # Look for location patterns (City, State or City, State, Country)
    location_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:,\s+[A-Z][a-z]+)*)'
    match = re.search(location_pattern, text)
    if match:
        return match.group(1).strip()
    
    return ''


def combine_pin_experiences(source_row: Dict[str, str]) -> str:
    """
    Combine multiple Pin experience entries into experience_text.
    
    Args:
        source_row: Source CSV row with Pin format
    
    Returns:
        Combined experience text
    """
    experiences = []
    
    # Check up to 10 experience entries (0-9)
    for i in range(10):
        title_key = f"candidate.experiences.{i}.title"
        company_key = f"candidate.experiences.{i}.company"
        start_key = f"candidate.experiences.{i}.startDate"
        end_key = f"candidate.experiences.{i}.endDate"
        
        title = source_row.get(title_key, '').strip()
        company = source_row.get(company_key, '').strip()
        
        if not title and not company:
            continue
        
        start = source_row.get(start_key, '').strip()
        end = source_row.get(end_key, '').strip() or 'Present'
        
        exp_text = f"{title} at {company}"
        if start:
            exp_text += f" ({start} - {end})"
        
        experiences.append(exp_text)
    
    return ". ".join(experiences) if experiences else ''


def combine_pin_educations(source_row: Dict[str, str]) -> str:
    """
    Combine multiple Pin education entries into education_text.
    
    Args:
        source_row: Source CSV row with Pin format
    
    Returns:
        Combined education text
    """
    educations = []
    
    # Check up to 5 education entries (0-4)
    for i in range(5):
        major_key = f"candidate.educations.{i}.major"
        degree_key = f"candidate.educations.{i}.degree"
        school_key = f"candidate.educations.{i}.school"
        end_key = f"candidate.educations.{i}.schoolEndDate"
        
        major = source_row.get(major_key, '').strip()
        degree = source_row.get(degree_key, '').strip()
        school = source_row.get(school_key, '').strip()
        end_date = source_row.get(end_key, '').strip()
        
        if not school:
            continue
        
        parts = []
        if degree:
            parts.append(degree)
        if major:
            parts.append(major)
        if school:
            parts.append(school)
        if end_date:
            parts.append(end_date)
        
        educations.append(" - ".join(parts))
    
    return ". ".join(educations) if educations else ''


def extract_standardized_record(source_row: Dict[str, str], column_mapping: Dict[str, str], source_type: Optional[str] = None) -> Dict[str, str]:
    """
    Extract a standardized record from a source row using column mapping.
    
    Args:
        source_row: Dictionary with source CSV row data
        column_mapping: Dictionary mapping source_column -> standard_column
        source_type: Optional source type for special handling
    
    Returns:
        Standardized record dictionary
    """
    standardized = {}
    
    # Initialize all standard columns as empty
    for col in ALL_COLUMNS:
        standardized[col] = ''
    
    # Special handling for Pin format
    if source_type == "pin":
        # Combine experiences
        standardized["experience_text"] = combine_pin_experiences(source_row)
        # Combine educations
        standardized["education_text"] = combine_pin_educations(source_row)
    
    # Map source columns to standard columns
    for source_col, standard_col in column_mapping.items():
        if source_col in source_row and standard_col in ALL_COLUMNS:
            value = source_row[source_col]
            if not value or not value.strip():
                continue
            
            value = value.strip()
            
            # Special handling for SeekOut
            if source_type == "seekout":
                if standard_col == "linkedin_url":
                    # Extract LinkedIn URL from href field
                    if "linkedin.com" in value.lower():
                        standardized[standard_col] = value
                elif standard_col in ["first_name", "last_name"]:
                    # Parse full name from display name
                    if "_candidateDisplayName" in source_col:
                        first, last = split_full_name(value)
                        if not standardized["first_name"]:
                            standardized["first_name"] = first
                        if not standardized["last_name"]:
                            standardized["last_name"] = last
                elif standard_col in ["title", "company_name"]:
                    # Parse "Title at Company" format
                    if "_candidateDetails" in source_col:
                        title, company = parse_title_at_company(value)
                        if not standardized["title"]:
                            standardized["title"] = title
                        if not standardized["company_name"]:
                            standardized["company_name"] = company
                elif standard_col == "location":
                    # Extract location from details text
                    location = extract_location_from_text(value)
                    if location and not standardized["location"]:
                        standardized["location"] = location
                else:
                    # Default mapping
                    if standard_col in standardized and standardized[standard_col]:
                        standardized[standard_col] += f" {value}"
                    else:
                        standardized[standard_col] = value
            
            # Special handling for Wrangle
            elif source_type == "wrangle":
                # Handle Name column - split into first_name and last_name
                if standard_col == "first_name" and source_col == "Name":
                    first, last = split_full_name(value)
                    standardized["first_name"] = first
                    standardized["last_name"] = last
                else:
                    # Default mapping for all other columns
                    standardized[standard_col] = value
            
            # Default handling for other sources
            else:
                # Handle multiple source columns mapping to same standard column
                if standard_col in standardized and standardized[standard_col]:
                    standardized[standard_col] += f" {value}"
                else:
                    standardized[standard_col] = value
    
    return standardized


def extract_all_records(source_rows: List[Dict[str, str]], column_mapping: Dict[str, str], source_type: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Extract standardized records from all source rows.
    
    Args:
        source_rows: List of source CSV row dictionaries
        column_mapping: Dictionary mapping source_column -> standard_column
        source_type: Optional source type for special handling
    
    Returns:
        List of standardized record dictionaries
    """
    standardized_records = []
    
    for row in source_rows:
        record = extract_standardized_record(row, column_mapping, source_type)
        standardized_records.append(record)
    
    return standardized_records
