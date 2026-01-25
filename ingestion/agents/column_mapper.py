"""
Column Mapping Agent

Maps source CSV columns to standard column names.
"""

from typing import Dict, List, Optional
from ..config.standard_schema import get_schema_description, ALL_COLUMNS
from ..config.column_mappings import find_mapping, KNOWN_MAPPINGS

try:
    from crewai import Agent, Task
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    Agent = None
    Task = None


def create_column_mapper_agent(llm=None):
    """
    Create a CrewAI agent for mapping source columns to standard columns.
    
    Args:
        llm: Optional LLM instance (uses default if not provided)
    
    Returns:
        Configured CrewAI Agent
    """
    return Agent(
        role="Column Mapping Specialist",
        goal="Map source CSV column names to standard column names by understanding semantic meaning and common variations",
        backstory="""You are an expert at understanding data schemas and mapping 
        columns between different formats. You recognize that the same data can 
        be represented with different column names (e.g., 'First Name' vs 'first_name' 
        vs 'fname') and can accurately map them to a standard format.""",
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )


def create_mapping_task(agent: Agent, source_headers: List[str], source_type: str, sample_data: List[Dict]) -> Task:
    """
    Create a CrewAI task for column mapping.
    
    Args:
        agent: The column mapper agent
        source_headers: List of source column names
        source_type: Detected source type
        sample_data: Sample rows for context
    
    Returns:
        Configured CrewAI Task
    """
    schema_desc = get_schema_description()
    sample_text = "\n".join([str(row) for row in sample_data[:2]])
    
    prompt = f"""Analyze the following CSV file and create a column mapping from source columns to standard columns.

SOURCE COLUMNS:
{', '.join(source_headers)}

SOURCE TYPE: {source_type}

SAMPLE DATA (first 2 rows):
{sample_text}

{schema_desc}

Create a JSON mapping in this format:
{{
  "source_column_name": "standard_column_name",
  ...
}}

For columns that don't map to any standard column, use null.
Only map columns that have semantic meaning matching the standard columns.
Return ONLY valid JSON, no other text."""

    return Task(
        description=prompt,
        agent=agent,
        expected_output="JSON object mapping source columns to standard columns",
    )


def map_columns(source_headers: List[str], source_type: Optional[str] = None, use_llm: bool = False, llm_agent=None) -> Dict[str, str]:
    """
    Map source columns to standard columns.
    
    Args:
        source_headers: List of source column names
        source_type: Optional detected source type
        use_llm: Whether to use LLM for unknown mappings
        llm_agent: Optional LLM agent for mapping
    
    Returns:
        Dictionary mapping source_column -> standard_column
    """
    mapping = {}
    
    # First, try known mappings
    for source_col in source_headers:
        standard_col = find_mapping(source_col, source_type)
        if standard_col:
            mapping[source_col] = standard_col
    
    # For unmapped columns, try LLM if requested
    if use_llm and llm_agent:
        unmapped = [col for col in source_headers if col not in mapping]
        if unmapped:
            # This would use the CrewAI task, but for now we'll do simple matching
            # In full implementation, this would execute the task
            pass
    
    return mapping


def create_column_mapping(source_headers: List[str], source_type: Optional[str] = None) -> Dict[str, str]:
    """
    Create column mapping using rule-based approach first, LLM fallback if needed.
    
    Args:
        source_headers: List of source column names
        source_type: Optional detected source type
    
    Returns:
        Dictionary mapping source_column -> standard_column
    """
    mapping = map_columns(source_headers, source_type, use_llm=False)
    
    # Special handling for Pin format - map nested columns
    if source_type == "pin":
        for header in source_headers:
            if header is None:
                continue
            header_lower = header.lower()
            
            if header == "candidate.linkedin":
                mapping[header] = "linkedin_url"
            elif header == "candidate.firstName":
                mapping[header] = "first_name"
            elif header == "candidate.lastName":
                mapping[header] = "last_name"
            elif header == "candidate.location":
                mapping[header] = "location"
            elif header == "candidate.experiences.0.title":
                mapping[header] = "title"
            elif header == "candidate.experiences.0.company":
                mapping[header] = "company_name"
    
    # Special handling for SeekOut obfuscated columns
    if source_type == "seekout":
        for header in source_headers:
            if header is None:
                continue
            header_lower = header.lower()
            
            # LinkedIn URL - _candidateName_dc5u3_2 href or _profileLinkText with href
            if ("candidatename" in header_lower and "href" in header_lower) or \
               ("profilelinktext" in header_lower and "href" in header_lower and "linkedin" in str(source_headers).lower()):
                if not any("linkedin_url" == v for v in mapping.values()):
                    mapping[header] = "linkedin_url"
            
            # Display name - _candidateDisplayName_dc5u3_17
            elif "candidatedisplayname" in header_lower and "href" not in header_lower:
                if not any("first_name" == v for v in mapping.values()):
                    mapping[header] = "first_name"  # Will be split later
            
            # Details - _candidateDetails_dc5u3_42 contains "Title at Company"
            elif "candidatedetails" in header_lower and "href" not in header_lower:
                # Map to title, will be parsed to extract both title and company
                if not any("title" == v for v in mapping.values()):
                    mapping[header] = "title"
            
            # Experience content - _content_rn39w_34 fields in Experience section
            elif "content" in header_lower and "_rn39w_34" in header:
                if not any("experience_text" == v for v in mapping.values()):
                    mapping[header] = "experience_text"
            
            # Education - look for education-related content
            elif "education" in header_lower or ("content" in header_lower and any("education" in str(h).lower() for h in source_headers if h)):
                if not any("education_text" == v for v in mapping.values()):
                    mapping[header] = "education_text"
    
    return mapping
