"""
Deduplication Agent

Detects duplicate candidates by LinkedIn URL and selects the best record.
"""

from typing import Dict, List, Tuple
from ..utils.data_completeness import calculate_completeness_score, compare_records
import re


def normalize_linkedin_url(url: str) -> str:
    """
    Normalize LinkedIn URL for comparison.
    
    Handles variations like:
    - https://linkedin.com/in/username
    - https://www.linkedin.com/in/username
    - linkedin.com/in/username
    - /in/username
    
    Args:
        url: LinkedIn URL string
    
    Returns:
        Normalized username or empty string if invalid
    """
    if not url or not url.strip():
        return ""
    
    url = url.strip()
    
    # Extract username from various URL formats
    patterns = [
        r'linkedin\.com/in/([^/?]+)',
        r'/in/([^/?]+)',
        r'in/([^/?]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1).lower().strip()
    
    # If no pattern matches, return as-is (might be just username)
    return url.lower().strip()


def find_duplicates(records: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Find and merge duplicate records by LinkedIn URL.
    
    Args:
        records: List of standardized candidate records
    
    Returns:
        Tuple of (deduplicated_records, duplicate_records)
        - deduplicated_records: Best record for each unique LinkedIn URL
        - duplicate_records: All duplicate records with metadata
    """
    # Group records by normalized LinkedIn URL
    url_groups: Dict[str, List[Dict[str, str]]] = {}
    
    for record in records:
        linkedin_url = record.get("linkedin_url", "")
        normalized = normalize_linkedin_url(linkedin_url)
        
        if not normalized:
            # No LinkedIn URL - can't deduplicate, keep as-is
            if "no_linkedin" not in url_groups:
                url_groups["no_linkedin"] = []
            url_groups["no_linkedin"].append(record)
            continue
        
        if normalized not in url_groups:
            url_groups[normalized] = []
        url_groups[normalized].append(record)
    
    # Process each group
    deduplicated = []
    duplicates_report = []
    
    for normalized_url, group in url_groups.items():
        if normalized_url == "no_linkedin":
            # Records without LinkedIn URLs - keep all
            deduplicated.extend(group)
            continue
        
        if len(group) == 1:
            # No duplicates, keep as-is
            deduplicated.append(group[0])
        else:
            # Multiple records with same LinkedIn URL
            # Calculate completeness scores
            scored_records = []
            for record in group:
                score = calculate_completeness_score(record)
                scored_records.append((score, record))
            
            # Sort by score (descending)
            scored_records.sort(key=lambda x: x[0], reverse=True)
            
            # Best record goes to deduplicated
            best_record = scored_records[0][1]
            deduplicated.append(best_record)
            
            # All others go to duplicates report with metadata
            for i, (score, record) in enumerate(scored_records):
                if i == 0:
                    continue  # Skip the best one
                
                duplicate_entry = {
                    "linkedin_url": record.get("linkedin_url", ""),
                    "first_name": record.get("first_name", ""),
                    "last_name": record.get("last_name", ""),
                    "title": record.get("title", ""),
                    "company_name": record.get("company_name", ""),
                    "completeness_score": score,
                    "best_record_score": scored_records[0][0],
                    "duplicate_rank": i + 1,
                    "total_duplicates": len(scored_records),
                }
                duplicates_report.append(duplicate_entry)
    
    return deduplicated, duplicates_report
