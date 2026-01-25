"""
Source Detection Agent

Identifies the source format of a CSV file (SeekOut, Pin Wrangle, Clay, etc.)
"""

from typing import Dict, List, Optional
from ..config.column_mappings import get_source_patterns, KNOWN_MAPPINGS
from ..utils.csv_reader import get_csv_headers, get_sample_rows

try:
    from crewai import Agent
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    Agent = None


def create_source_detector_agent(llm=None):
    """
    Create a CrewAI agent for detecting CSV source format.
    
    Args:
        llm: Optional LLM instance (uses default if not provided)
    
    Returns:
        Configured CrewAI Agent (if crewai is available)
    """
    if not CREWAI_AVAILABLE:
        raise ImportError("crewai is not installed. Install it with: pip install crewai")
    
    return Agent(
        role="Source Format Detector",
        goal="Identify the source format of CSV files (SeekOut, Pin Wrangle, Clay, RecruitCRM, or Unknown) by analyzing column names and patterns",
        backstory="""You are an expert at analyzing CSV file structures and identifying 
        their source systems. You recognize patterns in column naming conventions and 
        can quickly determine which tool or system generated a CSV file.""",
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )


def detect_source(file_path: str, headers: Optional[List[str]] = None, sample_rows: Optional[List[Dict]] = None) -> Dict[str, any]:
    """Detect the source format of a CSV file.

    Important: Many sources share “standard-like” column names. If the CSV already
    matches the standard schema (linkedin_url, first_name, last_name, etc.), we
    MUST treat it as standardized (clay-like) to avoid applying source-specific
    parsing rules (e.g., SeekOut obfuscated field handling).

    Returns:
      Dict with:
        - source_type: str
        - confidence: float (0.0..1.0)
        - evidence: List[str]
        - headers: original headers
    """
    if headers is None:
        headers = get_csv_headers(file_path)

    if sample_rows is None:
        sample_rows = get_sample_rows(file_path, num_rows=2)

    headers_lower = [h.lower() for h in headers]

    # --- Fast-path: already standardized schema ---
    standard_required = {"linkedin_url", "first_name", "last_name", "location", "company_name", "title"}
    if standard_required.issubset(set(headers_lower)):
        return {
            "source_type": "clay",  # treat as standard/Clay-like
            "confidence": 1.0,
            "evidence": ["Detected standard schema columns; treating as already standardized"],
            "headers": headers,
        }

    patterns = get_source_patterns()

    # Check for explicit source indicators in column names
    source_scores = {}
    for source_type, indicators in patterns.items():
        score = 0
        evidence = []
        
        for indicator in indicators:
            if any(indicator.lower() in h for h in headers_lower):
                score += 1
                evidence.append(f"Found '{indicator}' in column names")
        
        # Check for known column mappings
        if source_type in KNOWN_MAPPINGS:
            known_cols = set()
            for standard_col, variations in KNOWN_MAPPINGS[source_type].items():
                known_cols.update([v.lower() for v in variations])
            
            matches = sum(1 for h in headers_lower if h in [c.lower() for c in known_cols])
            if matches > 0:
                score += matches * 0.5
                evidence.append(f"Matched {matches} known column patterns")
        
        if score > 0:
            source_scores[source_type] = {"score": score, "evidence": evidence}
    
    # Special detection for Pin format (has candidate.linkedin, candidate.firstName, etc.)
    # Check this BEFORE wrangle to avoid false positives
    if any("candidate.linkedin" in h.lower() or "candidate.firstname" in h.lower() or "candidate.experiences.0" in h.lower() for h in headers):
        source_scores["pin"] = {"score": 10.0, "evidence": ["Detected Pin format with candidate.* nested columns"]}
    
    # Special detection for Wrangle format (simple columns: Name, Title, Company, Linkedin)
    wrangle_cols = ["name", "title", "company", "linkedin", "location"]
    if all(any(wc in h.lower() for h in headers_lower) for wc in wrangle_cols[:4]):
        if "wrangle" not in source_scores or source_scores.get("wrangle", {}).get("score", 0) < 3:
            source_scores["wrangle"] = {"score": 4.0, "evidence": ["Detected Wrangle format with simple column names"]}
    
    # Determine best match
    if source_scores:
        best_source = max(source_scores.items(), key=lambda x: x[1]["score"])
        source_type = best_source[0]
        confidence = min(1.0, best_source[1]["score"] / 5.0)  # Normalize to 0-1
        evidence = best_source[1]["evidence"]
    else:
        # Check if it matches standard format (likely Clay or already normalized)
        standard_cols = set(KNOWN_MAPPINGS["clay"].keys())
        if all(h.lower() in [c.lower() for c in standard_cols] for h in headers_lower[:6]):
            source_type = "clay"
            confidence = 0.7
            evidence = ["Matches standard column format"]
        else:
            source_type = "unknown"
            confidence = 0.0
            evidence = ["No known patterns detected"]
    
    return {
        "source_type": source_type,
        "confidence": confidence,
        "evidence": evidence,
        "headers": headers,
    }
