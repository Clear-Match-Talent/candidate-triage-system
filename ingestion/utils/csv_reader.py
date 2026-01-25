"""
CSV reading utilities with encoding detection and error handling.
"""

import csv
import chardet
from pathlib import Path
from typing import List, Dict, Optional


def detect_encoding(file_path: str) -> str:
    """
    Detect the encoding of a CSV file.
    
    Args:
        file_path: Path to the CSV file
    
    Returns:
        Detected encoding (default: 'utf-8')
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Read first 10KB
            result = chardet.detect(raw_data)
            return result.get('encoding', 'utf-8')
    except Exception:
        return 'utf-8'


def read_csv(file_path: str, encoding: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Read a CSV file and return list of dictionaries.
    
    Args:
        file_path: Path to the CSV file
        encoding: Optional encoding (auto-detected if not provided)
    
    Returns:
        List of dictionaries, one per row
    """
    if encoding is None:
        encoding = detect_encoding(file_path)
    
    # Try multiple encodings
    encodings_to_try = [encoding, 'utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    
    for enc in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=enc, newline='') as f:
                # Try to detect if there's a BOM
                if enc == 'utf-8':
                    first_bytes = f.read(3)
                    if first_bytes == '\ufeff':
                        # BOM found, file pointer is already at correct position
                        pass
                    else:
                        # No BOM, seek back to start
                        f.seek(0)
                else:
                    f.seek(0)
                
                reader = csv.DictReader(f)
                rows = list(reader)
                
                # Clean up column names (strip whitespace)
                if rows:
                    cleaned_rows = []
                    for row in rows:
                        cleaned_row = {k.strip() if k else '': (v.strip() if v else '') for k, v in row.items() if k is not None}
                        cleaned_rows.append(cleaned_row)
                    return cleaned_rows
                
                return rows
        except (UnicodeDecodeError, csv.Error) as e:
            continue
    
    raise ValueError(f"Could not read CSV file {file_path} with any encoding")


def get_csv_headers(file_path: str) -> List[str]:
    """
    Get column headers from a CSV file.
    
    Args:
        file_path: Path to the CSV file
    
    Returns:
        List of column names
    """
    encoding = detect_encoding(file_path)
    
    for enc in [encoding, 'utf-8', 'utf-8-sig', 'latin-1']:
        try:
            with open(file_path, 'r', encoding=enc, newline='') as f:
                reader = csv.DictReader(f)
                return [col.strip() for col in reader.fieldnames or []]
        except (UnicodeDecodeError, csv.Error):
            continue
    
    raise ValueError(f"Could not read headers from {file_path}")


def get_sample_rows(file_path: str, num_rows: int = 3) -> List[Dict[str, str]]:
    """
    Get a sample of rows from a CSV file for analysis.
    
    Args:
        file_path: Path to the CSV file
        num_rows: Number of sample rows to return
    
    Returns:
        List of sample row dictionaries
    """
    rows = read_csv(file_path)
    return rows[:num_rows] if len(rows) > num_rows else rows
