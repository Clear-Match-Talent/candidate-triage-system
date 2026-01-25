"""
Main orchestration script for CSV ingestion and standardization.

Usage:
    python -m ingestion.main file1.csv file2.csv --output-dir output/
"""

import argparse
import sys
from pathlib import Path
from typing import List

from .agents.source_detector import detect_source
from .agents.column_mapper import create_column_mapping
from .agents.data_extractor import extract_all_records
from .agents.deduplicator import find_duplicates
from .utils.csv_reader import read_csv, get_csv_headers, get_sample_rows
from .utils.csv_writer import write_csv
from .config.standard_schema import ALL_COLUMNS


def process_csv_file(file_path: str, verbose: bool = False) -> List[dict]:
    """
    Process a single CSV file and return standardized records.
    
    Args:
        file_path: Path to CSV file
        verbose: Whether to print progress messages
    
    Returns:
        List of standardized candidate records
    """
    if verbose:
        print(f"\nProcessing: {file_path}")
    
    # Step 1: Detect source format
    if verbose:
        print("  Detecting source format...")
    headers = get_csv_headers(file_path)
    sample_rows = get_sample_rows(file_path, num_rows=2)
    source_info = detect_source(file_path, headers=headers, sample_rows=sample_rows)
    
    if verbose:
        print(f"  Detected source: {source_info['source_type']} (confidence: {source_info['confidence']:.2f})")
    
    # Step 2: Create column mapping
    if verbose:
        print("  Creating column mapping...")
    column_mapping = create_column_mapping(headers, source_info['source_type'])
    
    if verbose:
        mapped_count = len([k for k, v in column_mapping.items() if v])
        print(f"  Mapped {mapped_count}/{len(headers)} columns")
    
    # Step 3: Read all rows
    if verbose:
        print("  Reading CSV rows...")
    source_rows = read_csv(file_path)
    
    if verbose:
        print(f"  Found {len(source_rows)} candidate records")
    
    # Step 4: Extract standardized records
    if verbose:
        print("  Extracting standardized records...")
    standardized_records = extract_all_records(source_rows, column_mapping, source_info['source_type'])
    
    # Add source file metadata
    for record in standardized_records:
        record['_source_file'] = Path(file_path).name
        record['_source_type'] = source_info['source_type']
    
    return standardized_records


def main():
    """Main entry point for CSV ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest and standardize candidate CSV files from multiple sources"
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="CSV files to process"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory for standardized CSV and duplicate report (default: output/)"
    )
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Skip deduplication (keep all records)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed progress messages"
    )
    
    args = parser.parse_args()
    
    # Validate input files
    for file_path in args.files:
        if not Path(file_path).exists():
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing {len(args.files)} CSV file(s)...")
    
    # Process all files
    all_records = []
    for file_path in args.files:
        try:
            records = process_csv_file(file_path, verbose=args.verbose)
            all_records.extend(records)
        except Exception as e:
            print(f"Error processing {file_path}: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            continue
    
    if not all_records:
        print("No records processed. Exiting.")
        sys.exit(1)
    
    print(f"\nTotal records collected: {len(all_records)}")
    
    # Deduplicate if requested
    if args.no_dedupe:
        deduplicated_records = all_records
        duplicates_report = []
        print("Skipping deduplication (--no-dedupe flag)")
    else:
        print("Deduplicating by LinkedIn URL...")
        deduplicated_records, duplicates_report = find_duplicates(all_records)
        print(f"  Unique candidates: {len(deduplicated_records)}")
        print(f"  Duplicates found: {len(duplicates_report)}")
    
    # Remove metadata columns before writing
    output_records = []
    for record in deduplicated_records:
        clean_record = {k: v for k, v in record.items() if not k.startswith('_')}
        output_records.append(clean_record)
    
    # Write standardized output
    output_file = output_dir / "standardized_candidates.csv"
    write_csv(str(output_file), output_records, ALL_COLUMNS)
    print(f"\n[OK] Standardized output written to: {output_file}")
    
    # Write duplicates report if any
    if duplicates_report:
        duplicates_file = output_dir / "duplicates_report.csv"
        duplicate_columns = [
            "linkedin_url", "first_name", "last_name", "title", "company_name",
            "completeness_score", "best_record_score", "duplicate_rank", "total_duplicates"
        ]
        write_csv(str(duplicates_file), duplicates_report, duplicate_columns)
        print(f"[OK] Duplicates report written to: {duplicates_file}")
    
    print(f"\nDone! Processed {len(all_records)} records, output {len(output_records)} unique candidates.")


if __name__ == "__main__":
    main()
