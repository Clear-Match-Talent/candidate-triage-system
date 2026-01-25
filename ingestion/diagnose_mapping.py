"""
Diagnostic tool to compare source CSV data with standardized output.
Shows what data is in source vs what ended up in output.
"""

import sys
from pathlib import Path
from ingestion.utils.csv_reader import read_csv, get_csv_headers
from ingestion.agents.source_detector import detect_source
from ingestion.agents.column_mapper import create_column_mapping
from ingestion.agents.data_extractor import extract_standardized_record

def diagnose_file(file_path: str, num_samples: int = 3):
    """Show source data vs output mapping for sample records."""
    print(f"\n{'='*80}")
    print(f"DIAGNOSING: {Path(file_path).name}")
    print(f"{'='*80}\n")
    
    # Detect source
    headers = get_csv_headers(file_path)
    source_info = detect_source(file_path, headers=headers)
    print(f"Detected source: {source_info['source_type']} (confidence: {source_info['confidence']:.2f})\n")
    
    # Create mapping
    column_mapping = create_column_mapping(headers, source_info['source_type'])
    print(f"Column Mapping ({len(column_mapping)} mappings):")
    for source_col, standard_col in sorted(column_mapping.items()):
        print(f"  {source_col[:50]:<50} -> {standard_col}")
    print()
    
    # Read sample rows
    source_rows = read_csv(file_path)
    sample_rows = source_rows[:num_samples]
    
    for i, source_row in enumerate(sample_rows, 1):
        print(f"\n{'-'*80}")
        print(f"SAMPLE RECORD #{i}")
        print(f"{'-'*80}\n")
        
        # Show key source fields
        print("SOURCE DATA (key fields):")
        key_fields = []
        if source_info['source_type'] == "pin":
            key_fields = [
                "candidate.linkedin", "candidate.firstName", "candidate.lastName",
                "candidate.location", "candidate.experiences.0.title", "candidate.experiences.0.company"
            ]
        elif source_info['source_type'] == "wrangle":
            key_fields = ["Linkedin", "Name", "Title", "Company", "Location"]
        elif source_info['source_type'] == "seekout":
            # Find SeekOut columns by pattern
            for col in headers:
                if col and ("linkedin" in col.lower() or "candidatename" in col.lower() or 
                           "candidatedisplayname" in col.lower() or "candidatedetails" in col.lower()):
                    key_fields.append(col)
                    if len(key_fields) >= 6:
                        break
        
        for field in key_fields:
            if field in source_row:
                value = source_row[field][:100] if source_row[field] else "(empty)"
                print(f"  {field:<40} = {value}")
        print()
        
        # Show what gets extracted
        standardized = extract_standardized_record(source_row, column_mapping, source_info['source_type'])
        print("STANDARDIZED OUTPUT:")
        for col in ["linkedin_url", "first_name", "last_name", "location", "company_name", "title"]:
            value = standardized.get(col, '')[:100] if standardized.get(col, '') else "(empty)"
            print(f"  {col:<20} = {value}")
        print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_mapping.py <csv_file> [num_samples]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    num_samples = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    diagnose_file(file_path, num_samples)
