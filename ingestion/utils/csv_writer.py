"""
CSV writing utilities for standardized output.
"""

import csv
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import tempfile


def write_csv(file_path: str, rows: List[Dict[str, str]], fieldnames: List[str], max_retries: int = 3):
    """
    Write a list of dictionaries to a CSV file with atomic write and retry logic.

    Uses atomic write pattern (write to temp file, then rename) to avoid corruption.
    Retries on PermissionError with exponential backoff (common on Windows when
    files are locked by Excel, antivirus, etc.).

    If file is still locked after retries, writes to a timestamped fallback file.

    Args:
        file_path: Path to output CSV file
        rows: List of dictionaries to write
        fieldnames: Column names in order
        max_retries: Maximum number of retry attempts (default: 3)
    """
    # Ensure output directory exists
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file first (atomic write pattern)
    temp_fd, temp_path = tempfile.mkstemp(
        suffix='.csv.tmp',
        dir=output_path.parent,
        text=True
    )

    try:
        # Write data to temp file
        with os.fdopen(temp_fd, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()

            for row in rows:
                # Ensure all fieldnames are present (fill with empty string if missing)
                complete_row = {field: row.get(field, '') for field in fieldnames}
                writer.writerow(complete_row)

        # Attempt to rename temp file to target with retry logic
        last_error = None
        for attempt in range(max_retries):
            try:
                # On Windows, need to remove target file first if it exists
                if output_path.exists():
                    output_path.unlink()

                # Atomic rename
                os.replace(temp_path, str(output_path))
                return  # Success!

            except PermissionError as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Exponential backoff: 0.1s, 0.2s, 0.4s
                    sleep_time = 0.1 * (2 ** attempt)
                    time.sleep(sleep_time)
                else:
                    # Final attempt failed, use fallback
                    break

        # All retries failed - write to timestamped fallback file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        fallback_path = output_path.parent / f"{output_path.stem}_{timestamp}{output_path.suffix}"

        try:
            os.replace(temp_path, str(fallback_path))
            print(f"\n⚠️  WARNING: Could not write to {output_path.name} (file locked by another process)")
            print(f"    Wrote to fallback file instead: {fallback_path.name}")
            print(f"    Original error: {last_error}")
            print(f"    Tip: Close any programs (like Excel) that may have the file open and try again.\n")
        except Exception as fallback_error:
            # Even fallback failed - clean up and raise
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise RuntimeError(
                f"Failed to write CSV to {output_path} or fallback {fallback_path}. "
                f"Original error: {last_error}. Fallback error: {fallback_error}"
            )

    except Exception:
        # Clean up temp file on any error during writing
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass  # Best effort cleanup
        raise
