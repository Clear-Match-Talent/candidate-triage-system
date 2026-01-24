"""
Data completeness scoring utilities.

Calculates how complete a candidate record is to help select the best duplicate.
"""

from typing import Dict, List
from ..config.standard_schema import REQUIRED_COLUMNS, OPTIONAL_COLUMNS


def calculate_completeness_score(record: Dict[str, str]) -> float:
    """
    Calculate a completeness score for a candidate record.
    
    Scoring:
    - Required fields: 2 points each (max 12 points for 6 required fields)
    - Optional fields: 1 point each (max 4 points for 4 optional fields)
    - Total max: 16 points
    
    Args:
        record: Dictionary with candidate data
    
    Returns:
        Completeness score (0.0 to 16.0)
    """
    score = 0.0
    
    # Count required fields (weight: 2x)
    for field in REQUIRED_COLUMNS:
        value = record.get(field, '').strip()
        if value:
            score += 2.0
    
    # Count optional fields (weight: 1x)
    for field in OPTIONAL_COLUMNS:
        value = record.get(field, '').strip()
        if value:
            score += 1.0
    
    return score


def get_missing_fields(record: Dict[str, str]) -> List[str]:
    """
    Get list of missing required fields.
    
    Args:
        record: Dictionary with candidate data
    
    Returns:
        List of missing required field names
    """
    missing = []
    for field in REQUIRED_COLUMNS:
        value = record.get(field, '').strip()
        if not value:
            missing.append(field)
    return missing


def compare_records(record1: Dict[str, str], record2: Dict[str, str]) -> Dict[str, str]:
    """
    Compare two records and return the one with higher completeness score.
    
    Args:
        record1: First candidate record
        record2: Second candidate record
    
    Returns:
        The record with higher completeness score (or record1 if tied)
    """
    score1 = calculate_completeness_score(record1)
    score2 = calculate_completeness_score(record2)
    
    if score2 > score1:
        return record2
    return record1
